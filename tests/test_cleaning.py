import pandas as pd
import pytest

from analysis.cleaning import COLUMNS, clean_products, matches_keyword, normalize_text, parse_sold


def make_raw(**changes):
    """One raw product row; override only what a test cares about."""
    row = {
        "source": "Tiki", "product_id": "1", "name": "Chuột Gaming A", "brand": "OEM",
        "seller": "Shop", "category": "Chuột Chơi Game", "price": 100_000,
        "original_price": 120_000, "sold": 10, "rating": 4.5, "review_count": 3,
        "image_url": "https://img", "product_url": "https://tiki.vn/a",
    }
    row.update(changes)
    return row


def test_normalize_text_removes_accents_and_punctuation():
    assert normalize_text("Chuột Gaming-Pro!") == "chuot gaming pro"
    assert normalize_text("Điện thoại") == "dien thoai"  # "đ" is not split by Unicode NFD


def test_matches_keyword_needs_every_word():
    assert matches_keyword("Chuột Gaming Logitech G102", "chuot gaming")
    assert not matches_keyword("Chuột văn phòng Logitech", "chuột gaming")


def test_matches_keyword_uses_whole_words():
    assert matches_keyword("Tai Nghe Bluetooth Sony", "tai nghe")
    assert not matches_keyword("Detail nghe nhạc", "tai nghe")    # "tai" is only inside "detail"
    assert not matches_keyword("Cáp tail light", "tai nghe")


@pytest.mark.parametrize("value, expected", [
    (4757, 4757),
    ("1.2K sold", 1200),    # was parsed as 1 in version 1
    ("2.7K sold", 2700),
    ("3,5k", 3500),
    ("206 sold", 206),
    ("Đã bán 1.234", 1234),
    ("1tr", 1_000_000),
    (None, 0),
    ("", 0),
    (float("nan"), 0),
])
def test_parse_sold(value, expected):
    assert parse_sold(value) == expected


def test_clean_products_applies_every_rule():
    raw = pd.DataFrame([
        make_raw(product_id="1"),
        make_raw(product_id="1"),                                          # duplicate
        make_raw(product_id="2", price=0),                                 # invalid price
        make_raw(product_id="3", product_url=None),                        # no link
        make_raw(product_id="4", name="Chuột chơi game B"),                # kept by the category rule
        make_raw(product_id="5", name="Lót chuột", category="Lót Chuột"),  # not relevant
        make_raw(product_id="6", original_price=90_000, rating=0),         # no real discount, not rated
    ])
    clean = clean_products(raw, "chuột gaming").set_index("product_id")

    assert list(clean.index) == ["1", "4", "6"]
    assert clean.loc["1", "discount_pct"] == 17           # 100k instead of 120k
    assert pd.isna(clean.loc["1", "brand"])               # "OEM" means no brand
    assert clean.loc["6", "original_price"] == 100_000
    assert clean.loc["6", "discount_pct"] == 0
    assert pd.isna(clean.loc["6", "rating"])              # 0 stars = not rated yet


def test_clean_products_handles_empty_input():
    clean = clean_products(pd.DataFrame(), "anything")
    assert clean.empty
    assert list(clean.columns) == COLUMNS
