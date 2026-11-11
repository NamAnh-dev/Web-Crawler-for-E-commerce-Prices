import json

import pandas as pd

from analysis import analyze, good_deals, price_ranges, price_summary, short_price

PRICES = [
    200_000,
    220_000,
    250_000,
    260_000,
    300_000,
    310_000,
    350_000,
    400_000,
    420_000,
    500_000,
]


def make_products():
    """Ten clean products: product 0 sold 0 units, product 9 sold 9 units.
    Products 0, 2, 4, 6, 8 are rated 4.8; the others are not rated yet."""
    return pd.DataFrame(
        {
            "product_id": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
            "name": [f"Chuột Gaming {i}" for i in range(10)],
            "brand": ["Logitech", "Razer"] * 5,
            "category": "Chuột Chơi Game",
            "price": PRICES,
            "original_price": PRICES,
            "discount_pct": 0,
            "sold": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "rating": [4.8, None] * 5,
            "review_count": 10,
            "image_url": None,
            "product_url": [f"https://tiki.vn/p{i}.html" for i in range(10)],
        }
    )


def test_short_price():
    assert short_price(85_000) == "85K"
    assert short_price(1_500_000) == "1.5Tr"
    assert short_price(2_000_000) == "2Tr"


def test_price_summary():
    prices = price_summary(pd.Series(PRICES))
    assert prices["min"] == 200_000
    assert prices["max"] == 500_000
    assert prices["mean"] == 321_000
    assert prices["median"] == 305_000  # between 300 000 and 310 000


def test_price_ranges_count_products_and_units_sold():
    table = price_ranges(make_products())
    assert table["label"].tolist() == ["200K–300K", "300K–500K", "500K–1Tr"]
    assert table["products"].tolist() == [4, 5, 1]
    assert table["sold"].tolist() == [6, 30, 9]
    assert table["product_share"].tolist() == [40.0, 50.0, 10.0]


def test_good_deals_are_cheap_well_rated_and_sorted_by_sales():
    picks = good_deals(make_products(), median=305_000)
    assert picks["product_id"].tolist() == ["4", "2", "0"]


def test_analyze_returns_everything_the_page_needs():
    report = analyze(make_products())
    assert report["summary"]["products"] == 10
    assert report["summary"]["total_sold"] == 45
    assert report["top_range"]["label"] == "300K–500K"
    assert report["best_sellers"][0]["sold"] == 9
    # the chart data must be valid JSON (no NaN)
    json.dumps({"ranges": report["ranges"], "brands": report["brands"]})
