"""Step 3 - Analyse: what is a normal price for this product, and what sells?

One search = one keyword, one category, one moment in time.
"""
import numpy as np
import pandas as pd

MIN_PRODUCTS = 8  # with fewer products, no price is called unusual

# Round price ranges for the chart, like the price filter of a shop (VND)
PRICE_RANGES = [0, 50_000, 100_000, 200_000, 300_000, 500_000, 1_000_000, 2_000_000,
                3_000_000, 5_000_000, 10_000_000, 20_000_000, 50_000_000, 100_000_000]


def short_price(value):
    """Short price for charts and cards: 85000 -> "85K", 1500000 -> "1.5Tr"."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}".removesuffix(".0") + "Tr"
    return f"{value / 1_000:.0f}K"


# --- 1. Unusual prices --------------------------------------------------------

def price_fences(prices):
    """Lowest and highest normal price, with Tukey's IQR rule on log10(price).

    Prices are right-skewed (many cheap products, a few very expensive ones).
    On log10(price) the shape is closer to symmetric, so the usual rule
    "more than 1.5 IQR outside Q1-Q3" works better there.
    """
    log_price = np.log10(prices)
    q1 = log_price.quantile(0.25)
    q3 = log_price.quantile(0.75)
    iqr = q3 - q1
    return 10 ** (q1 - 1.5 * iqr), 10 ** (q3 + 1.5 * iqr)


def flag_prices(prices):
    """Label every price "low", "normal" or "high"."""
    flags = pd.Series("normal", index=prices.index)
    if len(prices) < MIN_PRODUCTS:
        return flags
    low, high = price_fences(prices)
    flags[prices < low] = "low"
    flags[prices > high] = "high"
    return flags


# --- 2. Reference prices ------------------------------------------------------

def reference_prices(prices):
    """Reference prices from the normal prices, rounded to 1 000 VND.

    floor = 10th percentile: 90 % of listings cost more ("giá sàn tham khảo")
    q1-q3 = the middle 50 % of listings ("khoảng giá phổ biến")
    """
    result = {
        "min": prices.min(),
        "floor": prices.quantile(0.10),
        "q1": prices.quantile(0.25),
        "median": prices.median(),
        "q3": prices.quantile(0.75),
        "max": prices.max(),
    }
    for name, value in result.items():
        result[name] = int(round(value, -3))
    return result


# --- 3. What sells? -----------------------------------------------------------

def price_segments(normal, prices):
    """Budget (up to Q1), mid (Q1-Q3), premium (above Q3): share of listings vs units sold.

    If buyers did not care about price, both shares would be the same.
    """
    if prices["q1"] >= prices["q3"]:  # (almost) one price only: no segments
        return pd.DataFrame()

    segment = pd.cut(normal["price"], bins=[0, prices["q1"], prices["q3"], np.inf],
                     labels=["budget", "mid", "premium"])
    table = normal.groupby(segment, observed=False).agg(listings=("price", "size"), sold=("sold", "sum"))
    table["listing_share"] = 100 * table["listings"] / table["listings"].sum()
    table["sold_share"] = 100 * table["sold"] / max(table["sold"].sum(), 1)
    return table.reset_index(names="segment")


def price_histogram(prices):
    """Number of products in each round price range, from the cheapest to the most expensive."""
    lowest = max(edge for edge in PRICE_RANGES if edge <= prices.min())
    highest = min((edge for edge in PRICE_RANGES if edge > prices.max()), default=PRICE_RANGES[-1])
    edges = [edge for edge in PRICE_RANGES if lowest <= edge <= highest]

    counts = pd.cut(prices, bins=edges, right=False).value_counts(sort=False)
    labels = []
    for start, end in zip(edges[:-1], edges[1:]):
        labels.append(f"{short_price(start)}–{short_price(end)}")
    return {"labels": labels, "counts": counts.tolist()}


def top_brands(df, n=8):
    """Units sold per brand, best first (products without a brand are left out)."""
    sold = df.groupby("brand")["sold"].sum().sort_values(ascending=False).head(n)
    return {"labels": sold.index.tolist(), "sold": sold.tolist()}


def good_deals(normal, median, n=4):
    """A simple rule, no score: price at most the median, rated 4.5+ by at least
    5 reviews, and among those, the most sold first."""
    picks = normal[(normal["price"] <= median)
                   & (normal["rating"] >= 4.5)
                   & (normal["review_count"] >= 5)]
    return picks.sort_values("sold", ascending=False).head(n)


# --- 4. Everything the result page needs ---------------------------------------

def records(df):
    """DataFrame -> list of dicts, with None instead of NaN (for templates and JSON)."""
    data = df.astype(object)
    data = data.where(df.notna(), None)
    return data.to_dict("records")


def analyze(products):
    """Run every step above on the products of one search."""
    df = products.copy()
    df["price_flag"] = flag_prices(df["price"])
    normal = df[df["price_flag"] == "normal"]
    prices = reference_prices(normal["price"])
    segments = price_segments(normal, prices)

    total_sold = int(df["sold"].sum())
    best_seller = df.loc[df["sold"].idxmax()]
    summary = {
        "products": len(df),
        "brands": df["brand"].nunique(),
        "total_sold": total_sold,
        "best_seller": best_seller["name"],
        "best_seller_share": 100 * best_seller["sold"] / total_sold if total_sold else 0,
        "never_sold_share": 100 * (df["sold"] == 0).mean(),
        "rated_share": 100 * df["rating"].notna().mean(),
        "discount_share": 100 * (df["discount_pct"] > 0).mean(),
        "unusual": len(df) - len(normal),
    }
    if total_sold and not segments.empty:  # the segment that sells more than its share of listings
        gap = segments["sold_share"] - segments["listing_share"]
        summary["top_segment"] = segments.loc[gap.idxmax()].to_dict()

    return {
        "summary": summary,
        "prices": prices,
        "histogram": price_histogram(normal["price"]),
        "segments": records(segments),
        "brands": top_brands(df),
        "best_sellers": records(df.nlargest(4, "sold")),
        "good_deals": records(good_deals(normal, prices["median"])),
        "unusual": records(df[df["price_flag"] != "normal"].sort_values("price")),
        "products": records(df.sort_values("sold", ascending=False)),
    }
