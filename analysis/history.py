"""Analyse how the market of one keyword changes between snapshots.

collect.py saves a new snapshot every day. Comparing them shows:
- how the reference prices move over time;
- which products changed price;
- real sales between two snapshots: Tiki's "sold" is cumulative, so
  sold(latest) - sold(first) = units sold in between;
- discounts whose "original price" was never actually charged.
"""
import pandas as pd

from analysis.pricing import price_band, records

MIN_DAYS_FOR_DISCOUNT_CHECK = 7
KEY = ["source", "product_id"]


def main_category(history):
    """Biggest category of the latest snapshot."""
    latest = history[history["run_id"] == history["run_id"].max()]
    return latest["category"].value_counts().idxmax()


def snapshot_table(history):
    """Reference prices of every snapshot, oldest first."""
    rows = []
    for run_id, snapshot in history.groupby("run_id"):
        rows.append({"run_id": run_id, "created_at": snapshot["created_at"].iloc[0],
                     "products": len(snapshot), **price_band(snapshot)})
    return pd.DataFrame(rows)


def product_changes(history):
    """Each product present in both the first and the latest snapshot."""
    first = history[history["run_id"] == history["run_id"].min()].set_index(KEY)
    latest = history[history["run_id"] == history["run_id"].max()].set_index(KEY)
    both = latest.join(first[["price", "sold"]], rsuffix="_before", how="inner")
    both["price_change_pct"] = 100 * (both["price"] / both["price_before"] - 1)
    both["sold_between"] = (both["sold"] - both["sold_before"]).clip(lower=0)
    return both.reset_index()


def unseen_original_prices(history):
    """Discounted products whose "original price" was never seen as a real price.

    If a product is always "on sale" from a price it was never sold at during
    the whole period, the advertised discount is probably inflated.
    """
    highest_seen = history.groupby(KEY)["price"].max().rename("highest_price_seen")
    latest = history[history["run_id"] == history["run_id"].max()]
    latest = latest[latest["discount_pct"] > 0].join(highest_seen, on=KEY)
    return latest[latest["original_price"] > latest["highest_price_seen"]]


def build_history(history, category):
    """Everything the history page needs, for one category of one keyword.

    Only Tiki is collected every day, so imported Lazada/Shopee rows are left out
    to keep the snapshots comparable.
    """
    data = history[(history["category"] == category) & (history["source"] == "Tiki")]
    snapshots = snapshot_table(data)
    times = pd.to_datetime(snapshots["created_at"])
    days = (times.iloc[-1] - times.iloc[0]).days

    result = {"snapshots": records(snapshots), "days": days, "changes": None, "unseen": None}
    if len(snapshots) >= 2:
        changes = product_changes(data)
        result["changes"] = {
            "matched": len(changes),
            # like-for-like: the same products, so a different product mix cannot fake a change
            "median_change_pct": changes["price_change_pct"].median() if len(changes) else 0,
            "top_sellers": records(changes[changes["sold_between"] > 0].nlargest(5, "sold_between")),
            "price_drops": records(changes[changes["price_change_pct"] < 0].nsmallest(5, "price_change_pct")),
            "price_rises": records(changes[changes["price_change_pct"] > 0].nlargest(5, "price_change_pct")),
            "changed_share": 100 * (changes["price_change_pct"] != 0).mean() if len(changes) else 0,
        }
    if days >= MIN_DAYS_FOR_DISCOUNT_CHECK:
        result["unseen"] = records(unseen_original_prices(data).nlargest(10, "discount_pct"))
    return result
