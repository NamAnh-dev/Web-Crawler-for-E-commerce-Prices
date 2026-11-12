"""Kiểm thử cleaning.py: bỏ dấu, khớp từ khóa và các quy tắc làm sạch."""

import pandas as pd

from cleaning import clean_products, matches_keyword, normalize_text


def product(product_id, name, price, category="Chuột Chơi Game", **changes):
    """Tạo một dòng thô, giống dạng mà scraper.parse_item() trả về.

    Hàm phụ trợ (không phải test, vì tên không bắt đầu bằng test_) giúp tạo
    dữ liệu mẫu cho gọn. Mọi trường có sẵn giá trị mặc định; chỉ cần ghi
    những trường muốn khác đi.
    **changes gom mọi tham số có tên còn lại thành một dict, vd
    product("1", "A", 200_000, rating=0) -> changes = {"rating": 0}.
    """
    row = {
        "product_id": product_id,
        "name": name,
        "brand": "Logitech",
        "category": category,
        "price": price,
        "original_price": price,
        "sold": 10,
        "rating": 4.5,
        "review_count": 3,
        "image_url": None,
        "product_url": f"https://tiki.vn/p{product_id}.html",
    }
    row.update(changes)  # ghi đè các trường trong changes lên giá trị mặc định
    return row


def test_normalize_text_removes_accents_and_punctuation():
    """Bỏ dấu tiếng Việt (kể cả chữ "Đ"), chữ thường, dấu câu thành khoảng trắng."""
    assert normalize_text("Chuột Gaming-Pro!") == "chuot gaming pro"
    assert normalize_text("Đèn LED") == "den led"


def test_matches_keyword_uses_whole_words():
    """Khớp theo nguyên từ, không phân biệt có dấu hay không dấu."""
    assert matches_keyword("Tai Nghe Bluetooth Sony", "tai nghe")
    assert matches_keyword("Chuột Gaming Logitech", "chuot gaming")  # gõ không dấu vẫn khớp
    # "assert not ...": điều kiện phải SAI. "tai" chỉ nằm bên trong chữ "detail"
    # chứ không phải một từ riêng, nên không được khớp.
    assert not matches_keyword("Detail nghe thử", "tai nghe")


def test_clean_products_rules():
    """Mỗi dòng mẫu kiểm tra một quy tắc làm sạch (xem chú thích cuối mỗi dòng)."""
    raw = pd.DataFrame(
        [
            product("1", "Chuột Gaming A", 200_000, rating=0),  # chưa có đánh giá
            product("1", "Chuột Gaming A", 200_000),  # trùng mã "1" -> bị bỏ
            product("2", "Chuột Gaming B", 300_000, original_price=400_000),  # giảm 25 %
            product("3", "Chuột Gaming C", None),  # không có giá -> bị bỏ
            product("4", "Chuột chơi game D", 250_000, brand="OEM"),  # không có thương hiệu
            # khác danh mục (lót chuột) -> bị bỏ ở quy tắc 5
            product("5", "Lót Chuột Gaming", 50_000, category="Miếng Lót Chuột"),
        ]
    )
    df = clean_products(raw, "chuột gaming")

    # Còn lại 1, 2, 4. Bỏ: dòng "1" thứ hai (trùng), 3 (không giá), 5 (khác danh mục)
    assert df["product_id"].tolist() == ["1", "2", "4"]
    # Sau reset_index, dòng 0 = sản phẩm "1": rating 0 đã thành rỗng (NaN)
    assert pd.isna(df.loc[0, "rating"])
    # Dòng 1 = sản phẩm "2": 300.000 so với giá gốc 400.000 -> giảm 25 %
    assert df.loc[1, "discount_pct"] == 25
    # Dòng 2 = sản phẩm "4": thương hiệu "OEM" đã thành rỗng.
    # Dùng pd.isna() thay vì "is None": từ pandas 3.0, None trong cột chữ
    # được pandas tự đổi thành NaN, nên "is None" sẽ sai dù dữ liệu vẫn đúng.
    assert pd.isna(df.loc[2, "brand"])
