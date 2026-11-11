"""Step 4 - Analyse: simple numbers about the products of one search.

One search = one keyword, one category, one moment in time.
"""

import pandas as pd

# Round price ranges, like the price filter of a shop (VND)
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
    """Short price for charts and cards: 85000 -> "85K", 1500000 -> "1.5Tr"."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}".removesuffix(".0") + "Tr"
    return f"{value / 1_000:.0f}K"


def price_summary(prices):
    """Lowest, highest, mean and median price.

    The mean and the median are rounded to 1 000 VND. The median is the price
    in the middle: half of the products are cheaper, half are more expensive.
    """
    return {
        "min": int(prices.min()),
        "max": int(prices.max()),
        "mean": int(round(prices.mean(), -3)),
        "median": int(round(prices.median(), -3)),
    }


def price_ranges(df):
    """Price segments: products and units sold in each round price range.

    `product_share` and `sold_share` are percentages of the whole search, so
    the two can be compared: a range with 10 % of the products and 40 % of the
    units sold is where the buyers are.
    """
    rows = []
    # pairs of neighbours: (0, 50K), (50K, 100K), ...
    for start, end in zip(PRICE_RANGES[:-1], PRICE_RANGES[1:]):
        if end <= df["price"].min() or start > df["price"].max():
            continue  # no product of this search can be in this range
        in_range = df[(df["price"] >= start) & (df["price"] < end)]
        if start == 0:
            label = f"Dưới {short_price(end)}"  # "Dưới 50K" reads better than "0K–50K"
        else:
            label = f"{short_price(start)}–{short_price(end)}"
        rows.append(
            {
                "label": label,
                "products": len(in_range),
                "sold": int(in_range["sold"].sum()),
            }
        )

    table = pd.DataFrame(rows)
    total_products = table["products"].sum()
    total_sold = max(table["sold"].sum(), 1)  # 1 avoids dividing by zero
    table["product_share"] = (100 * table["products"] / total_products).round(1)
    table["sold_share"] = (100 * table["sold"] / total_sold).round(1)
    return table


def top_brands(df, n=8):
    """Units sold per brand, best first (products without a brand are left out)."""
    sold = df.groupby("brand")["sold"].sum().sort_values(ascending=False).head(n)
    return {"labels": sold.index.tolist(), "sold": sold.tolist()}


def good_deals(df, median, n=4):
    """A simple rule, not a score: price at most the median, rated 4.5 or more
    by at least 5 reviews. Among those, the most sold first."""
    picks = df[
        (df["price"] <= median) & (df["rating"] >= 4.5) & (df["review_count"] >= 5)
    ]
    return picks.sort_values("sold", ascending=False).head(n)


def records(df):
    """DataFrame -> list of dicts, with None instead of NaN (for the web page)."""
    data = df.astype(object)
    data = data.where(df.notna(), None)
    return data.to_dict("records")


def analyze(products):
    """Everything the result page shows, for the products of one search."""
    prices = price_summary(products["price"])
    ranges = price_ranges(products).to_dict("records")

    total_sold = int(products["sold"].sum())
    best_seller = products.loc[products["sold"].idxmax()]
    summary = {
        "products": len(products),
        "brands": int(products["brand"].nunique()),
        "total_sold": total_sold,
        "best_seller": best_seller["name"],
        "best_seller_share": round(100 * best_seller["sold"] / max(total_sold, 1)),
        "never_sold_share": round(100 * (products["sold"] == 0).mean()),
        "rated_share": round(100 * products["rating"].notna().mean()),
    }

    # the price range with the most units sold
    top_range = ranges[0]
    for row in ranges:
        if row["sold"] > top_range["sold"]:
            top_range = row

    by_sold = products.sort_values("sold", ascending=False)
    return {
        "summary": summary,
        "prices": prices,
        "ranges": ranges,
        "top_range": top_range,
        "brands": top_brands(products),
        "best_sellers": records(by_sold.head(4)),
        "good_deals": records(good_deals(products, prices["median"])),
        "products": records(by_sold),
    }
