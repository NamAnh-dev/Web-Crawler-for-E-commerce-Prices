"""Bước 4 - Phân tích: vài con số đơn giản về các sản phẩm của một lượt tìm kiếm.

Một lượt tìm kiếm = một từ khóa, một danh mục, một thời điểm.
"""

from itertools import pairwise

import pandas as pd

# Các mốc giá tròn, giống bộ lọc giá trên các trang mua sắm (đơn vị VND).
# Hai mốc liền nhau tạo thành một khoảng giá: 0-50K, 50K-100K, 100K-200K...
# Dấu "_" trong số chỉ để dễ đọc: 50_000 chính là 50000.
PRICE_RANGES = [
    0,
    50_000,
    100_000,
    200_000,
    300_000,
    500_000,
    1_000_000,
    2_000_000,
    3_000_000,
    5_000_000,
    10_000_000,
    20_000_000,
    50_000_000,
    100_000_000,
]


def short_price(value):
    """Giá viết gọn cho biểu đồ và thẻ: 85000 -> "85K", 1500000 -> "1.5Tr"."""
    # Từ 1 triệu trở lên: chia cho 1 triệu, giữ 1 chữ số thập phân (":.1f")
    if value >= 1_000_000:
        # 1500000 -> "1.5" -> "1.5Tr".  2000000 -> "2.0" -> bỏ đuôi ".0" -> "2Tr"
        return f"{value / 1_000_000:.1f}".removesuffix(".0") + "Tr"
    # Dưới 1 triệu: chia cho 1 nghìn, không lấy số lẻ (":.0f"): 85000 -> "85K"
    return f"{value / 1_000:.0f}K"


def price_summary(prices):
    """Giá thấp nhất, cao nhất, trung bình (mean) và trung vị (median).

    Vào:  prices = một cột giá (pandas Series).
    Ra:   dict {"min", "max", "mean", "median"}.

    Mean và median được làm tròn đến hàng nghìn VND. Median là mức giá ở giữa:
    một nửa sản phẩm rẻ hơn, một nửa đắt hơn. Median ít bị kéo lệch bởi vài
    sản phẩm rất đắt, còn mean thì bị kéo lên (vì cộng tất cả giá rồi chia đều).
    """
    return {
        "min": int(prices.min()),
        "max": int(prices.max()),
        # round(x, -3): làm tròn đến hàng nghìn (số âm = làm tròn về bên trái dấu phẩy).
        # Ví dụ: round(321_400, -3) = 321_000
        "mean": int(round(prices.mean(), -3)),
        # Số sản phẩm chẵn thì median = trung bình của 2 giá ở giữa
        "median": int(round(prices.median(), -3)),
    }


def price_ranges(df):
    """Phân khúc giá: số sản phẩm và số lượng đã bán trong mỗi khoảng giá tròn.

    `product_share` và `sold_share` là phần trăm so với cả lượt tìm kiếm, nên
    có thể so hai cột với nhau: một khoảng giá chiếm 10 % số sản phẩm nhưng
    40 % số lượng bán ra là nơi người mua tập trung.
    """
    rows = []  # mỗi khoảng giá sẽ thành một dict trong list này
    # pairwise() ghép từng cặp mốc liền nhau: (0, 50K), (50K, 100K), (100K, 200K), ...
    for start, end in pairwise(PRICE_RANGES):
        # Bỏ qua khoảng giá nằm ngoài các sản phẩm của lượt tìm kiếm này:
        # khoảng kết thúc trước sản phẩm rẻ nhất, hoặc bắt đầu sau sản phẩm đắt nhất.
        # (Nhờ vậy biểu đồ không có một loạt cột trống ở hai đầu.)
        if end <= df["price"].min() or start > df["price"].max():
            continue  # không sản phẩm nào có thể nằm trong khoảng này -> sang khoảng tiếp
        # Lọc sản phẩm có start <= giá < end (tính mốc đầu, không tính mốc cuối).
        # Mỗi điều kiện trong ngoặc là một cột True/False, dấu & nghĩa là "VÀ".
        in_range = df[(df["price"] >= start) & (df["price"] < end)]
        # Tên hiển thị của khoảng giá
        if start == 0:
            label = f"Dưới {short_price(end)}"  # "Dưới 50K" dễ đọc hơn "0K–50K"
        else:
            label = f"{short_price(start)}–{short_price(end)}"  # vd "200K–300K"
        rows.append(
            {
                "label": label,
                "products": len(in_range),  # số sản phẩm trong khoảng
                "sold": int(in_range["sold"].sum()),  # tổng số lượng đã bán trong khoảng
            }
        )

    table = pd.DataFrame(rows)  # list các dict -> bảng, mỗi dòng là một khoảng giá
    total_products = table["products"].sum()  # tổng số sản phẩm
    # Tổng số lượng bán. max(..., 1): nếu chưa sản phẩm nào bán được (tổng = 0)
    # thì dùng 1, để phép chia bên dưới không bị chia cho 0.
    total_sold = max(table["sold"].sum(), 1)
    # Phần trăm của mỗi khoảng, làm tròn 1 chữ số thập phân (vd 40.0)
    # Đặt cột (Series) lên trước số 100 để Pylance hiểu đúng kiểu dữ liệu
    table["product_share"] = (table["products"] * 100 / total_products).round(1)
    table["sold_share"] = (table["sold"] * 100 / total_sold).round(1)
    return table


def top_brands(df, n=8):
    """Số lượng đã bán theo từng thương hiệu, bán nhiều nhất đứng đầu.

    Sản phẩm không có thương hiệu bị bỏ ra (groupby tự bỏ các giá trị rỗng).
    """
    # groupby("brand"): gom các dòng cùng thương hiệu thành một nhóm
    # ["sold"].sum(): cộng cột "sold" trong từng nhóm
    # sort_values(ascending=False): sắp xếp giảm dần; head(n): lấy n thương hiệu đầu
    sold = df.groupby("brand")["sold"].sum().sort_values(ascending=False).head(n)
    # Kết quả là một Series: index = tên thương hiệu, giá trị = số lượng bán.
    # Đổi thành 2 list thường để biểu đồ trên web (JavaScript) đọc được.
    return {"labels": sold.index.tolist(), "sold": sold.tolist()}


def good_deals(df, median, n=4):
    """Một quy tắc đơn giản, không phải điểm số: giá không quá giá trung vị, được
    đánh giá từ 4.5 sao trở lên với ít nhất 5 lượt đánh giá. Trong số đó, sản
    phẩm bán chạy nhất đứng đầu."""
    # Giữ dòng thỏa CẢ BA điều kiện (dấu & = "VÀ").
    # Sản phẩm chưa có đánh giá (rating là NaN) sẽ cho False ở điều kiện thứ hai.
    picks = df[
        (df["price"] <= median) & (df["rating"] >= 4.5) & (df["review_count"] >= 5)
    ]
    # Sắp xếp theo số lượng bán giảm dần, lấy n sản phẩm đầu
    return picks.sort_values("sold", ascending=False).head(n)


def records(df):
    """DataFrame -> list các dict (mỗi dòng một dict), dùng None thay cho NaN (cho trang web).

    Lý do: NaN không hợp lệ trong JSON (dữ liệu cho biểu đồ). Trong template,
    NaN còn bị coi là "có giá trị", nên {% if item.rating %} sẽ hiện "★ nan".
    Còn None bị coi là "không có", nên template hiện chữ "chưa có" đúng ý.
    """
    # Đổi mọi cột sang kiểu object (kiểu "chung" của Python) để chứa được None.
    # Nếu vẫn là cột số thì pandas sẽ đổi None trở lại thành NaN.
    data = df.astype(object)
    # where(điều_kiện, giá_trị): chỗ nào điều kiện True thì giữ nguyên,
    # chỗ nào False (tức là ô rỗng / NaN) thì thay bằng None
    data = data.where(df.notna(), None)
    # "records": mỗi dòng thành một dict {tên cột: giá trị}
    return data.to_dict("records")


def analyze(products):
    """Mọi thứ mà trang kết quả hiển thị, cho các sản phẩm của một lượt tìm kiếm.

    Đây là hàm "tổng": gọi các hàm ở trên rồi gom kết quả vào một dict lớn,
    app.py truyền dict này cho template result.html.
    """
    prices = price_summary(products["price"])  # min / max / mean / median
    # Bảng khoảng giá -> list các dict (mỗi khoảng một dict)
    ranges = price_ranges(products).to_dict("records")

    total_sold = int(products["sold"].sum())  # tổng số lượng đã bán của cả lượt tìm
    # idxmax() trả về chỉ số (index) của dòng có "sold" lớn nhất,
    # .loc[chỉ số] lấy ra cả dòng đó -> sản phẩm bán chạy nhất
    best_seller = products.loc[products["sold"].idxmax()]
    summary = {
        "products": len(products),  # số sản phẩm
        "brands": int(products["brand"].nunique()),  # số thương hiệu khác nhau (không tính rỗng)
        "total_sold": total_sold,
        "best_seller": best_seller["name"],
        # Sản phẩm bán chạy nhất chiếm bao nhiêu % tổng số lượng bán.
        # max(total_sold, 1) để không chia cho 0.
        "best_seller_share": round(100 * best_seller["sold"] / max(total_sold, 1)),
        # (sold == 0) là cột True/False; .mean() của True/False = tỉ lệ True
        # (True tính là 1, False là 0) -> % sản phẩm chưa bán được cái nào
        "never_sold_share": round(100 * (products["sold"] == 0).mean()),
        # Tương tự: % sản phẩm đã có điểm đánh giá (rating không rỗng)
        "rated_share": round(100 * products["rating"].notna().mean()),
    }

    # Tìm khoảng giá có số lượng bán nhiều nhất: bắt đầu từ khoảng đầu tiên,
    # gặp khoảng nào bán nhiều hơn thì giữ khoảng đó (cách tìm max bằng vòng lặp)
    top_range = ranges[0]
    for row in ranges:
        if row["sold"] > top_range["sold"]:
            top_range = row

    # Toàn bộ sản phẩm, bán chạy nhất đứng đầu (dùng cho 3 mục bên dưới)
    by_sold = products.sort_values("sold", ascending=False)
    return {
        "summary": summary,
        "prices": prices,
        "ranges": ranges,
        "top_range": top_range,
        "brands": top_brands(products),
        "best_sellers": records(by_sold.head(4)),  # 4 sản phẩm bán chạy nhất
        # Giá trị "đáng mua", so với giá trung vị của chính lượt tìm này
        "good_deals": records(good_deals(products, prices["median"])),
        "products": records(by_sold),  # bảng đầy đủ mọi sản phẩm
    }
