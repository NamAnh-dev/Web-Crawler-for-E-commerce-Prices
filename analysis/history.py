"""Compare the snapshots of one keyword (collect.py saves one every day).

- Reference prices of each snapshot, to see the market move over time.
- Like-for-like price change: only products present in the first AND the
  latest snapshot, so new or removed products cannot fake a price change.
- Units sold in between: Tiki's "sold" is cumulative, so latest - first.
"""
import pandas as pd

from analysis.pricing import price_band, records

KEY = ["source", "product_id"]


def snapshot_table(history):
    """Reference prices of every snapshot, oldest first."""
    rows = []
    for run_id, snapshot in history.groupby("run_id"):
        rows.append({"run_id": run_id, "created_at": snapshot["created_at"].iloc[0],
                     "products": len(snapshot), **price_band(snapshot)})
    return pd.DataFrame(rows)


def product_changes(history):
    """Each product present in both the first and the latest snapshot."""
    first = history[history["run_id"] == history["run_id"].min()]
    latest = history[history["run_id"] == history["run_id"].max()]
    # inner merge on (source, product_id): only products found in both snapshots
    both = latest.merge(first[KEY + ["price", "sold"]], on=KEY, suffixes=("", "_before"))
    both["price_change_pct"] = 100 * (both["price"] / both["price_before"] - 1)
    both["sold_between"] = (both["sold"] - both["sold_before"]).clip(lower=0)
    return both


def build_history(history, category):
    """Everything the history page needs, for one category of one keyword.

    Only Tiki is collected every day, so imported Lazada/Shopee products are
    left out to keep the snapshots comparable.
    """
    data = history[(history["category"] == category) & (history["source"] == "Tiki")]
    snapshots = snapshot_table(data)
    times = pd.to_datetime(snapshots["created_at"])
    result = {"snapshots": records(snapshots), "days": (times.iloc[-1] - times.iloc[0]).days, "changes": None}

    if len(snapshots) >= 2:
        changes = product_changes(data)
        result["changes"] = {
            "matched": len(changes),
            "median_change_pct": changes["price_change_pct"].median() if len(changes) else 0,
            "changed_share": 100 * (changes["price_change_pct"] != 0).mean() if len(changes) else 0,
            "top_sellers": records(changes[changes["sold_between"] > 0].nlargest(5, "sold_between")),
            "price_drops": records(changes[changes["price_change_pct"] < 0].nsmallest(5, "price_change_pct")),
            "price_rises": records(changes[changes["price_change_pct"] > 0].nlargest(5, "price_change_pct")),
        }
    return result
