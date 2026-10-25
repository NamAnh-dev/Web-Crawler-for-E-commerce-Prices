import pandas as pd

from cleaning import clean_products, main_category, matches_keyword, normalize_text


def product(product_id, name, price, category="Chuột Chơi Game", **changes):
    row = {
        "product_id": product_id, "name": name, "brand": "Logitech", "category": category,
        "price": price, "original_price": price, "sold": 10, "rating": 4.5, "review_count": 3,
        "image_url": None, "product_url": f"https://tiki.vn/p{product_id}.html",
    }
    row.update(changes)
    return row


def test_normalize_text_removes_accents_and_punctuation():
    assert normalize_text("Chuột Gaming-Pro!") == "chuot gaming pro"
    assert normalize_text("Đèn LED") == "den led"


def test_matches_keyword_uses_whole_words():
    assert matches_keyword("Tai Nghe Bluetooth Sony", "tai nghe")
    assert not matches_keyword("Detail nghe thử", "tai nghe")  # "tai" is inside "detail"
    assert matches_keyword("Chuột Gaming Logitech", "chuot gaming")


def test_main_category_is_the_category_of_most_matching_names():
    df = pd.DataFrame([
        product("1", "Chuột Gaming A", 200_000),
        product("2", "Chuột Gaming B", 300_000),
        product("3", "Lót Chuột Gaming", 50_000, category="Miếng Lót Chuột"),
    ])
    assert main_category(df, "chuột gaming") == "Chuột Chơi Game"


def test_clean_products_rules():
    raw = pd.DataFrame([
        product("1", "Chuột Gaming A", 200_000, rating=0),                   # not rated yet
        product("1", "Chuột Gaming A", 200_000),                             # duplicate
        product("2", "Chuột Gaming B", 300_000, original_price=400_000),     # 25 % off
        product("3", "Chuột Gaming C", None),                                # no price
        product("4", "Chuột chơi game D", 250_000, brand="OEM"),             # same category, kept
        product("5", "Lót Chuột Gaming", 50_000, category="Miếng Lót Chuột"),  # other category
    ])
    df = clean_products(raw, "chuột gaming")

    assert df["product_id"].tolist() == ["1", "2", "4"]
    assert pd.isna(df.loc[0, "rating"])
    assert df.loc[1, "discount_pct"] == 25
    assert df.loc[0, "original_price"] == 200_000
    assert df.loc[2, "brand"] is None


def test_clean_products_with_no_results():
    assert clean_products(pd.DataFrame(), "chuột gaming").empty
