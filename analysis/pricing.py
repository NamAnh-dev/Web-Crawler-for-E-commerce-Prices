"""Analyze: reference prices, unusual prices and a simple deal score.

All numbers are computed inside one search (one keyword, one moment in time)
and inside one category, so a product is only compared with similar products.
"""
import numpy as np
import pandas as pd

MIN_PRODUCTS_TO_FLAG = 8                              # too few products -> do not judge prices
PRIOR_REVIEWS = 10                                    # weight of the average in adjusted_rating
DEAL_WEIGHTS = {"price": 0.3, "sold": 0.4, "rating": 0.3}


# --- 1. Unusual prices ----------------------------------------------------------

def price_fences(prices):
    """Lower/upper fence of Tukey's IQR rule, applied on a log scale.

    E-commerce prices are right-skewed (a few very expensive items), so the
    rule works much better on log10(price), where the shape is closer to
    symmetric. The fences are converted back to VND.
    """
    log_price = np.log10(prices)
    q1, q3 = log_price.quantile([0.25, 0.75])
    iqr = q3 - q1
    return 10 ** (q1 - 1.5 * iqr), 10 ** (q3 + 1.5 * iqr)


def flag_prices(prices):
    """Label every price as "low", "normal" or "high"."""
    if len(prices) < MIN_PRODUCTS_TO_FLAG:
        return pd.Series("normal", index=prices.index)
    low, high = price_fences(prices)
    labels = np.select([prices < low, prices > high], ["low", "high"], default="normal")
    return pd.Series(labels, index=prices.index)


# --- 2. Deal score --------------------------------------------------------------

def adjusted_rating(df):
    """Bayesian average: pull ratings with few reviews toward the category average.

    5.0 stars from 1 review is less convincing than 4.8 stars from 1 000
    reviews. Formula (also used for IMDb's Top 250): (v*R + m*C) / (v + m)
    v = number of reviews, R = product rating, m = PRIOR_REVIEWS,
    C = average rating of the product's category, because every other part
    of the deal score also compares a product only with its own category.
    A product without reviews simply gets C.
    """
    average = df.groupby("category")["rating"].transform("mean")   # C, one value per category
    rating = df["rating"].fillna(average)
    return (df["review_count"] * rating + PRIOR_REVIEWS * average) / (df["review_count"] + PRIOR_REVIEWS)


def deal_scores(df):
    """Score from 0 to 100: cheaper, more sold and better rated = higher.

    Each criterion is turned into a percentile rank (0-1) inside its category,
    so VND, units sold and stars can be added together. Products with an
    unusual price (often accessories or wrong listings) get no score.
    """
    normal = df[df["price_flag"] == "normal"].copy()
    normal["rating_adj"] = adjusted_rating(normal)
    by_category = normal.groupby("category")

    price_score = 1 - by_category["price"].rank(pct=True)    # cheapest -> close to 1
    sold_score = by_category["sold"].rank(pct=True)           # best seller -> 1
    rating_score = by_category["rating_adj"].rank(pct=True)   # best adjusted rating -> 1
    rating_score = rating_score.fillna(0.5)                   # nobody rated yet -> neutral

    score = 100 * (DEAL_WEIGHTS["price"] * price_score
                   + DEAL_WEIGHTS["sold"] * sold_score
                   + DEAL_WEIGHTS["rating"] * rating_score)
    return score.round(1).reindex(df.index)


def main_category(df):
    """The category with the most products: the one analysed by default."""
    return df["category"].value_counts().idxmax()


def add_analysis_columns(df):
    """Add `price_flag` and `deal_score` before the products are saved."""
    df = df.copy()
    df["price_flag"] = df.groupby("category")["price"].transform(flag_prices)
    df["deal_score"] = deal_scores(df)
    return df


# --- 3. Reference prices --------------------------------------------------------

def weighted_median(values, weights):
    """The value below which half of the total weight lies (None if no weight)."""
    values, weights = np.asarray(values), np.asarray(weights)
    order = np.argsort(values)
    cumulative = np.cumsum(weights[order])
    if len(cumulative) == 0 or cumulative[-1] == 0:
        return None
    return float(values[order][np.searchsorted(cumulative, cumulative[-1] / 2)])


def price_band(df):
    """Reference prices, computed on products with a normal price only.

    floor   = 10th percentile -> "giá sàn tham khảo": 90% of normal listings cost more
    q1..q3  = the middle 50% of listings ("common price range")
    sales_weighted_median = the price buyers actually pay most (weighted by units sold)

    Values are rounded to 1 000 VND: a reference price needs no more precision.
    """
    normal = df[df["price_flag"] == "normal"]
    prices = normal["price"].astype(float)
    band = {
        "min": prices.min(),
        "floor": prices.quantile(0.10),
        "q1": prices.quantile(0.25),
        "median": prices.median(),
        "q3": prices.quantile(0.75),
        "ceiling": prices.quantile(0.90),
        "sales_weighted_median": weighted_median(prices, normal["sold"]),
    }
    return {key: None if value is None else round(value, -3) for key, value in band.items()}


# --- 4. Summaries for the dashboard ----------------------------------------------

def log_position(value, start, end):
    """Where `value` sits (0-100 %) between `start` and `end` on a log scale.

    A log scale keeps the cheap end of a price line from being squeezed
    into a few pixels.
    """
    span = (np.log10(end) - np.log10(start)) or 1
    return float(np.clip(100 * (np.log10(value) - np.log10(start)) / span, 0, 100))


def band_positions(band):
    """Positions of the reference prices on the dashboard's price line,
    which runs from the cheapest normal product to the 90th percentile."""
    return {key: log_position(band[key], band["min"], band["ceiling"])
            for key in ("floor", "q1", "median", "q3")}


def summarize(df):
    """Reference prices of the main category (cards on the home page)."""
    category = main_category(df)
    band = price_band(df[df["category"] == category])
    return {"category": category, "band": band, "pos": band_positions(band)}


def source_comparison(df):
    """Reference prices and sales per marketplace, drawn on one shared price line."""
    sources = sorted(df["source"].unique())
    if "Tiki" in sources:  # Tiki first: it is the main source
        sources.remove("Tiki")
        sources.insert(0, "Tiki")

    rows = []
    for source in sources:
        group = df[df["source"] == source]
        if not (group["price_flag"] == "normal").any():
            continue  # no normal price: no reference prices to show
        rows.append({"source": source, "products": len(group), "sold": int(group["sold"].sum()),
                     "rated_share": 100 * group["rating"].notna().mean(), **price_band(group)})
    if not rows:
        return []  # no marketplace has a normal price: nothing to compare (min() of nothing fails)

    start = min(row["floor"] for row in rows)
    end = max(row["ceiling"] for row in rows)
    for row in rows:
        row["pos"] = {key: log_position(row[key], start, end) for key in ("floor", "q1", "median", "q3")}
    return rows


def nice_step(raw_step):
    """Round a bin width up to 1, 2 or 5 x 10^n (e.g. 37 000 -> 50 000)."""
    magnitude = 10 ** np.floor(np.log10(raw_step))
    for factor in (1, 2, 5, 10):
        if raw_step <= factor * magnitude:
            return factor * magnitude


def price_histogram(prices, target_bins=12):
    """Counts per price bin, with round bin edges so the labels are readable.

    Regular bins cover prices up to the 90th percentile; the long tail of
    expensive products is grouped into one extra bar ("tail").
    """
    cap = prices.quantile(0.90)
    step = nice_step((cap - prices.min()) / target_bins or 1)
    start = np.floor(prices.min() / step) * step
    edges = np.arange(start, cap + step, step)
    if len(edges) < 2:  # (almost) all prices are identical
        edges = np.array([start, start + step])
    counts, _ = np.histogram(prices[prices < edges[-1]], bins=edges)
    tail = int((prices >= edges[-1]).sum())
    return {"edges": edges.tolist(), "counts": counts.tolist(), "tail": tail}


def segment_table(df, band):
    """Split normal products into 3 price segments; compare listings vs units sold."""
    normal = df[df["price_flag"] == "normal"]
    segment = pd.cut(normal["price"], bins=[0, band["q1"], band["q3"], np.inf],
                     labels=["budget", "mid", "premium"])
    table = (normal.groupby(segment, observed=False)
                   .agg(listings=("price", "size"), sold=("sold", "sum"),
                        min_price=("price", "min"), max_price=("price", "max")))
    table["listing_share"] = 100 * table["listings"] / max(table["listings"].sum(), 1)
    table["sales_share"] = 100 * table["sold"] / max(table["sold"].sum(), 1)
    table["gap"] = table["sales_share"] - table["listing_share"]  # > 0: sells more than its share
    return table.reset_index(names="segment")


def group_summary(df, column, top=8):
    """Products, median price, units sold and average rating per brand/seller/source."""
    data = df[df[column].notna()]
    summary = data.groupby(column).agg(products=("product_id", "size"), median_price=("price", "median"),
                                       sold=("sold", "sum"), avg_rating=("rating", "mean"))
    summary = summary.sort_values(["sold", "products"], ascending=False).head(top)
    return summary.reset_index().rename(columns={column: "name"})


def records(df):
    """DataFrame -> list of dicts, with None instead of NaN (easier in templates)."""
    data = df.astype(object)             # object columns can hold None
    data = data.where(df.notna(), None)  # NaN -> None
    return data.to_dict("records")


def build_dashboard(df):
    """Everything the dashboard page needs, in one dictionary.

    `df` should contain products of one category (see app.py).
    """
    normal = df[df["price_flag"] == "normal"]
    band = price_band(df)
    low_fence, high_fence = price_fences(df["price"])
    discounted = df[df["discount_pct"] > 0]

    segments = pd.DataFrame()
    best_segment = worst_segment = None
    if band["q1"] < band["q3"]:  # segments need at least two different prices
        segments = segment_table(df, band)
        best_segment = segments.loc[segments["gap"].idxmax()].to_dict()
        worst_segment = segments.loc[segments["gap"].idxmin()].to_dict()

    return {
        "kpis": {
            "products": len(df),
            "sellers": df["seller"].nunique(),
            "brands": df["brand"].nunique(),
            "total_sold": int(df["sold"].sum()),
            "avg_rating": df["rating"].mean(),
            "rated_share": 100 * df["rating"].notna().mean(),
            "discount_share": 100 * len(discounted) / len(df),
            "avg_discount": discounted["discount_pct"].mean() if len(discounted) else 0,
            "unusual": int((df["price_flag"] != "normal").sum()),
        },
        "band": band,
        "band_pos": band_positions(band),
        "fences": {"low": low_fence, "high": high_fence},
        "histogram": price_histogram(normal["price"]),
        "segments": records(segments),
        "best_segment": best_segment,
        "worst_segment": worst_segment,
        "brands": records(group_summary(df, "brand")),
        "sources": source_comparison(df) if df["source"].nunique() > 1 else [],
        "top_deals": records(df.nlargest(5, "deal_score")),
        "best_sellers": records(df.nlargest(5, "sold")),
        "unusual": records(df[df["price_flag"] != "normal"].sort_values("price")),
    }
