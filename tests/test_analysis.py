import json

import numpy as np
import pandas as pd

from analysis import analyze, flag_prices, price_histogram, price_segments, reference_prices, short_price


def make_products(prices, sold=None):
    n = len(prices)
    return pd.DataFrame({
        "product_id": [str(i) for i in range(n)],
        "name": [f"Chuột Gaming {i}" for i in range(n)],
        "brand": ["Logitech", "Razer", None, "DareU"] * (n // 4) + [None] * (n % 4),
        "category": "Chuột Chơi Game",
        "price": prices,
        "original_price": prices,
        "discount_pct": 0,
        "sold": sold if sold is not None else list(range(n)),
        "rating": [4.8, np.nan] * (n // 2) + [np.nan] * (n % 2),
        "review_count": 10,
        "image_url": None,
        "product_url": [f"https://tiki.vn/p{i}.html" for i in range(n)],
    })


PRICES = [200_000, 220_000, 250_000, 260_000, 300_000, 310_000, 350_000, 400_000, 420_000, 500_000]


def test_flag_prices_finds_unusual_prices_on_both_sides():
    prices = pd.Series(PRICES + [5_000, 50_000_000])
    flags = flag_prices(prices)
    assert flags.iloc[-2] == "low"
    assert flags.iloc[-1] == "high"
    assert (flags.iloc[:-2] == "normal").all()


def test_flag_prices_does_not_judge_small_groups():
    assert (flag_prices(pd.Series([1_000, 200_000, 50_000_000])) == "normal").all()


def test_reference_prices_are_percentiles_rounded_to_1000():
    prices = reference_prices(pd.Series(PRICES))
    assert prices["median"] == 305_000
    assert prices["floor"] == 218_000   # 10th percentile: 218 000
    assert prices["q1"] <= prices["median"] <= prices["q3"]


def test_price_segments_shares_add_up_to_100():
    df = make_products(PRICES)
    table = price_segments(df, reference_prices(df["price"]))
    assert table["segment"].tolist() == ["budget", "mid", "premium"]
    assert round(table["listing_share"].sum()) == 100
    assert round(table["sold_share"].sum()) == 100


def test_price_segments_needs_at_least_two_prices():
    df = make_products([100_000] * 8)
    assert price_segments(df, reference_prices(df["price"])).empty


def test_price_histogram_uses_round_ranges():
    histogram = price_histogram(pd.Series(PRICES))
    assert histogram["labels"] == ["200K–300K", "300K–500K", "500K–1Tr"]
    assert histogram["counts"] == [4, 5, 1]


def test_short_price():
    assert short_price(85_000) == "85K"
    assert short_price(1_500_000) == "1.5Tr"
    assert short_price(2_000_000) == "2Tr"


def test_analyze_returns_everything_the_page_needs():
    report = analyze(make_products(PRICES + [5_000]))
    assert report["summary"]["products"] == 11
    assert report["summary"]["unusual"] == 1
    assert len(report["products"]) == 11
    assert report["best_sellers"][0]["sold"] == 10
    # the chart data must be valid JSON (no NaN, no numpy types)
    json.dumps({"histogram": report["histogram"], "segments": report["segments"], "brands": report["brands"]})
