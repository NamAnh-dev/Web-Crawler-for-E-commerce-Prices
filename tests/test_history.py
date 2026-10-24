import pandas as pd

from analysis.history import build_history, product_changes, unseen_original_prices


def snapshot(run_id, created_at, prices, sold, original=None):
    n = len(prices)
    return pd.DataFrame({
        "run_id": run_id, "created_at": created_at, "source": "Tiki",
        "product_id": [str(i) for i in range(n)], "name": [f"P{i}" for i in range(n)],
        "category": "Chuột Chơi Game", "price": prices, "original_price": original or prices,
        "discount_pct": [round(100 * (1 - p / o)) for p, o in zip(prices, original or prices)],
        "sold": sold, "price_flag": "normal",
    })


PRICES = [100_000, 150_000, 200_000, 250_000, 300_000]


def test_product_changes_uses_cumulative_sold():
    history = pd.concat([
        snapshot(1, "2026-10-01 08:00:00", PRICES, [10, 0, 5, 5, 5]),
        snapshot(2, "2026-10-08 08:00:00", [90_000] + PRICES[1:], [25, 3, 5, 5, 5]),
    ])
    changes = product_changes(history).set_index("product_id")
    assert changes.loc["0", "sold_between"] == 15
    assert round(changes.loc["0", "price_change_pct"]) == -10
    assert changes.loc["2", "price_change_pct"] == 0


def test_unseen_original_price_is_flagged():
    history = pd.concat([
        snapshot(1, "2026-10-01 08:00:00", PRICES, [1] * 5),
        # product 4 is now "on sale" from 400 000, a price never seen before
        snapshot(2, "2026-10-08 08:00:00", PRICES, [1] * 5, original=PRICES[:4] + [400_000]),
    ])
    assert list(unseen_original_prices(history)["product_id"]) == ["4"]


def test_build_history_waits_for_seven_days_before_checking_discounts():
    short = pd.concat([snapshot(1, "2026-10-01 08:00:00", PRICES, [1] * 5),
                       snapshot(2, "2026-10-03 08:00:00", PRICES, [2] * 5)])
    result = build_history(short, "Chuột Chơi Game")
    assert result["days"] == 2
    assert result["unseen"] is None
    assert result["changes"]["matched"] == 5


def test_like_for_like_change_ignores_a_different_product_mix():
    # the second snapshot has 3 extra expensive products but no price changed
    history = pd.concat([snapshot(1, "2026-10-01 08:00:00", PRICES, [1] * 5),
                         snapshot(2, "2026-10-02 08:00:00", PRICES + [900_000] * 3, [1] * 8)])
    result = build_history(history, "Chuột Chơi Game")
    first, last = result["snapshots"][0], result["snapshots"][-1]
    assert last["median"] > first["median"]               # the market median moved...
    assert result["changes"]["median_change_pct"] == 0    # ...but no product changed price
