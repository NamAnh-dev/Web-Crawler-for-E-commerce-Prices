"""Bước 2 - Làm sạch: biến các dòng thô từ scraper.py thành một bảng sẵn sàng để phân tích."""

import re  # biểu thức chính quy (regex): tìm / thay thế chữ theo mẫu
import unicodedata  # tách chữ có dấu thành chữ gốc + dấu (để bỏ dấu tiếng Việt)

import pandas as pd

# Các cột của bảng sạch, theo đúng thứ tự này.
# "discount_pct" (phần trăm giảm giá) không có trong dữ liệu thô: ta tự tính ở bước 2.
COLUMNS = [
    "product_id",
    "name",
    "brand",
    "category",
    "price",
    "original_price",
    "discount_pct",
    "sold",
    "rating",
    "review_count",
    "image_url",
    "product_url",
]

# Những giá trị thương hiệu thật ra có nghĩa là "không có thương hiệu"
# (viết ở dạng đã qua normalize_text: chữ thường, không dấu).
# Dùng set {...} thay vì list vì kiểm tra "x in set" nhanh và rõ nghĩa.
NO_BRAND = {"oem", "no brand", "nobrand", "khong thuong hieu"}


def normalize_text(text):
    """Chuyển về chữ thường, bỏ dấu tiếng Việt và bỏ dấu câu.

    "Chuột Gaming-Pro!" -> "chuot gaming pro", nhờ vậy "chuot gaming" khớp với "Chuột Gaming".
    """
    # str(): đề phòng giá trị không phải chuỗi (vd số, NaN).
    # Chữ "đ" không tách được thành "d" + dấu như các chữ khác, nên phải thay tay.
    text = str(text).lower().replace("đ", "d")
    # NFD tách mỗi chữ có dấu thành chữ gốc + các dấu riêng:
    # "ộ" -> "o" + dấu mũ + dấu nặng
    text = unicodedata.normalize("NFD", text)
    # Category "Mn" = loại ký tự "dấu" (dấu mũ, dấu nặng, dấu sắc...).
    # Chỉ giữ lại những ký tự KHÔNG phải dấu, rồi nối lại thành chuỗi.
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    # Mọi chuỗi ký tự không phải a-z hoặc 0-9 (dấu gạch, chấm than, nhiều khoảng
    # trắng...) đều được thay bằng MỘT khoảng trắng: "gaming-pro!" -> "gaming pro "
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()  # bỏ khoảng trắng thừa ở đầu và cuối


def matches_keyword(name, keyword):
    """True nếu MỌI từ của từ khóa đều là một từ trong tên sản phẩm.

    So sánh nguyên từ, không phải một đoạn chữ: "tai" (trong "tai nghe")
    không được khớp với "detail" (dù "detail" có chứa chữ "tai").
    """
    # .split() cắt chuỗi thành list các từ: "chuot gaming pro" -> ["chuot", "gaming", "pro"]
    name_words = normalize_text(name).split()
    for word in normalize_text(keyword).split():
        if word not in name_words:  # chỉ cần thiếu 1 từ là không khớp
            return False
    return True  # đi hết vòng lặp mà không thiếu từ nào -> khớp


def main_category(df, keyword):
    """Danh mục xuất hiện nhiều nhất trong các sản phẩm có tên khớp từ khóa.

    Tìm "chuột gaming" thì Tiki còn trả về cả lót chuột và bàn phím. Chỉ giữ
    danh mục này nghĩa là một mức giá chỉ được so với các sản phẩm tương tự.
    """
    # .apply() gọi matches_keyword(tên, keyword=keyword) cho TỪNG tên trong cột "name"
    # -> ra một cột True/False. df[cột True/False] chỉ giữ những dòng True.
    matches = df[df["name"].apply(matches_keyword, keyword=keyword)]
    if matches.empty:  # không có sản phẩm nào khớp từ khóa
        return None
    # value_counts() đếm mỗi danh mục xuất hiện bao nhiêu lần (nhiều nhất xếp đầu),
    # idxmax() lấy tên của danh mục có số lần lớn nhất.
    return matches["category"].value_counts().idxmax()


def clean_brand(brand):
    """Trả về None khi thiếu thương hiệu, hoặc khi thương hiệu là "OEM" / "No Brand"."""
    # pd.isna(): True khi giá trị bị thiếu (None hoặc NaN)
    if pd.isna(brand) or normalize_text(brand) in NO_BRAND:
        return None
    return brand  # thương hiệu thật thì giữ nguyên


def clean_products(raw, keyword):
    """Áp dụng các quy tắc làm sạch, theo thứ tự:

    1. bỏ dòng thiếu tên, link hoặc giá, và bỏ sản phẩm bị trùng
    2. không có giá gốc (hoặc giá gốc thấp hơn giá bán) nghĩa là không giảm giá
    3. điểm đánh giá 0 nghĩa là "chưa ai đánh giá": đổi thành rỗng (NaN), không phải 0 sao
    4. "OEM" / "No Brand" đổi thành thương hiệu rỗng
    5. chỉ giữ danh mục chính của lượt tìm kiếm (xem main_category)

    Vào:  raw = bảng thô từ scraper.crawl(), keyword = từ khóa đã tìm.
    Ra:   bảng sạch, có đúng các cột trong COLUMNS.
    """
    if raw.empty:  # Tiki không trả sản phẩm nào -> không có gì để làm sạch
        return raw

    # 1. Dòng không dùng được và dòng bị trùng
    # dropna(subset=...): bỏ dòng bị thiếu (NaN/None) ở MỘT TRONG các cột này
    df = raw.dropna(subset=["name", "product_url", "price"])
    df = df[df["price"] > 0]  # giữ dòng có giá lớn hơn 0 (giá 0 là dữ liệu lỗi)
    # Cùng product_id xuất hiện nhiều lần (vd ở 2 trang khác nhau) -> chỉ giữ lần đầu.
    # .copy() tạo bảng mới hẳn, để các lệnh gán bên dưới không bị pandas cảnh báo
    # (SettingWithCopyWarning) và không ảnh hưởng tới bảng raw ban đầu.
    df = df.drop_duplicates(subset="product_id").copy()

    # 2. Giá và phần trăm giảm giá
    # no_discount là một cột True/False: True khi thiếu giá gốc HOẶC (dấu |)
    # giá gốc nhỏ hơn giá bán (dữ liệu vô lý)
    no_discount = df["original_price"].isna() | (df["original_price"] < df["price"])
    # .loc[dòng, cột]: ở những dòng True, gán giá gốc = giá bán (tức là không giảm giá)
    df.loc[no_discount, "original_price"] = df.loc[no_discount, "price"]
    # Đổi sang số nguyên (vd 200000.0 -> 200000), vì tiền VND không có số lẻ
    df["price"] = df["price"].astype(int)
    df["original_price"] = df["original_price"].astype(int)
    # Phần trăm giảm = 100 x (1 - giá bán / giá gốc), làm tròn thành số nguyên.
    # Ví dụ: giá 300.000, giá gốc 400.000 -> 100 x (1 - 0.75) = 25 (%).
    # Phép tính chạy trên cả cột cùng lúc, không cần vòng lặp for.
    df["discount_pct"] = (
        (100 * (1 - df["price"] / df["original_price"])).round().astype(int)
    )

    # 3-4. Điểm đánh giá và thương hiệu
    # Dòng nào có rating == 0 thì gán None (trong cột số, None tự thành NaN = "rỗng")
    df.loc[df["rating"] == 0, "rating"] = None
    # Gọi clean_brand() cho từng giá trị của cột "brand", ghi đè lại cột đó
    df["brand"] = df["brand"].apply(clean_brand)

    # 5. Chỉ giữ một danh mục: những dòng có category bằng danh mục chính.
    # (Nếu main_category trả về None thì không dòng nào khớp -> bảng rỗng,
    # app.py sẽ báo "không tìm thấy sản phẩm phù hợp".)
    df = df[df["category"] == main_category(df, keyword)]
    # df[COLUMNS]: chọn các cột theo đúng thứ tự trong COLUMNS.
    # reset_index(drop=True): đánh lại số thứ tự dòng 0, 1, 2... sau khi đã bỏ bớt dòng.
    return df[COLUMNS].reset_index(drop=True)
