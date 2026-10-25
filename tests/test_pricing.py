import numpy as np
import pandas as pd

from analysis.pricing import (add_analysis_columns, adjusted_rating, build_dashboard,
                              flag_prices, price_band, weighted_median)

NORMAL_PRICES = [100_000, 120_000, 150_000, 180_000, 200_000, 220_000, 250_000, 300_000]


def make_products(prices, category="Chuột Chơi Game"):
    n = len(prices)
    return pd.DataFrame({
        "source": "Tiki",
        "product_id": [str(i) for i in range(n)],
        "name": [f"Product {i}" for i in range(n)],
        "brand": "Brand",
        "seller": "Shop",
        "category": category,
        "price": prices,
        "original_price": prices,
        "discount_pct": 0,
        "sold": [10 * i for i in range(n)],
        "rating": 4.5,
        "review_count": 20,
    })


def test_flag_prices_finds_extremes_on_a_log_scale():
    prices = pd.Series(NORMAL_PRICES + [5_000, 20_000_000])
    flags = flag_prices(prices)
    assert (flags.iloc[:8] == "normal").all()
    assert flags.iloc[8] == "low"
    assert flags.iloc[9] == "high"


def test_flag_prices_does_not_judge_tiny_groups():
    prices = pd.Series([1_000, 100_000, 10_000_000])
    assert (flag_prices(prices) == "normal").all()


def test_weighted_median():
    assert weighted_median([100, 200, 300], [1, 1, 10]) == 300
    assert weighted_median([100, 200, 300], [0, 0, 0]) is None


def test_adjusted_rating_prefers_many_reviews():
    df = pd.DataFrame({"category": "Chuột Chơi Game", "rating": [5.0, 4.8, 4.0, 4.2, np.nan],
                       "review_count": [1, 1000, 50, 50, 0]})
    adjusted = adjusted_rating(df)
    assert adjusted[1] > adjusted[0]                      # 4.8 from 1000 reviews beats 5.0 from 1
    assert adjusted[4] == df["rating"].mean()             # no reviews -> the average


def test_adjusted_rating_uses_the_average_of_each_category():
    df = pd.DataFrame({"category": ["Chuột", "Chuột", "Lót chuột", "Lót chuột"],
                       "rating": [5.0, np.nan, 3.0, np.nan], "review_count": [10, 0, 10, 0]})
    adjusted = adjusted_rating(df)
    assert adjusted[1] == 5.0      # not rated yet: gets the average of its own category...
    assert adjusted[3] == 3.0      # ...not the overall average (4.0)


def test_deal_score_range_and_unusual_prices():
    df = add_analysis_columns(make_products(NORMAL_PRICES + [5_000]))
    scored = df["deal_score"].dropna()
    assert len(scored) == 8                               # the 5 000 VND listing is not scored
    assert df.loc[8, "price_flag"] == "low"
    assert scored.between(0, 100).all()


def test_deal_score_works_when_nobody_has_rated_yet():
    df = add_analysis_columns(make_products(NORMAL_PRICES).assign(rating=np.nan, review_count=0))
    assert df["deal_score"].notna().all()


def test_deal_score_is_computed_inside_each_category():
    mice = make_products(NORMAL_PRICES)
    pads = make_products([10_000] * 30, category="Lót Chuột")
    df = add_analysis_columns(pd.concat([mice, pads], ignore_index=True))
    # 30 cheap mouse pads must not make every mouse look "unusually expensive"
    assert (df["price_flag"] == "normal").all()

    pooled = flag_prices(df["price"])  # what happens without the per-category rule
    assert (pooled[df["category"] == "Chuột Chơi Game"] == "high").all()


def test_price_band_is_ordered_and_rounded():
    df = add_analysis_columns(make_products(NORMAL_PRICES))
    band = price_band(df)
    assert band["floor"] <= band["q1"] <= band["median"] <= band["q3"] <= band["ceiling"]
    assert all(value % 1000 == 0 for value in band.values() if value is not None)


def test_build_dashboard_runs_on_a_normal_category():
    df = add_analysis_columns(make_products(NORMAL_PRICES))
    data = build_dashboard(df)
    assert data["kpis"]["products"] == 8
    assert len(data["segments"]) == 3
    assert sum(data["histogram"]["counts"]) + data["histogram"]["tail"] == 8
