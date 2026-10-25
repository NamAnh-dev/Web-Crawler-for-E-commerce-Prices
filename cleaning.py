"""Step 2 - Clean: turn the raw rows from scraper.py into a table ready for analysis."""
import re
import unicodedata

import pandas as pd

# Columns of the clean table, in this order (the same as the database table)
COLUMNS = ["product_id", "name", "brand", "category", "price", "original_price", "discount_pct",
           "sold", "rating", "review_count", "image_url", "product_url"]

# Brand values that actually mean "no brand" (after normalize_text)
NO_BRAND = {"oem", "no brand", "nobrand", "khong thuong hieu"}


def normalize_text(text):
    """Lowercase, without Vietnamese accents or punctuation.

    "Chuột Gaming-Pro!" -> "chuot gaming pro", so "chuot gaming" matches "Chuột Gaming".
    """
    text = str(text).lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)  # "ộ" -> "o" + two accent marks
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")  # drop the marks
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def matches_keyword(name, keyword):
    """True if every word of the keyword is a word of the product name.

    Whole words, not substrings: "tai" (from "tai nghe") must not match "detail".
    """
    name_words = normalize_text(name).split()
    for word in normalize_text(keyword).split():
        if word not in name_words:
            return False
    return True


def main_category(df, keyword):
    """The category of most products whose name matches the keyword.

    A search for "chuột gaming" also returns mouse pads and keyboards. Keeping
    only this category means a price is only compared with similar products.
    """
    matches = df[df["name"].apply(matches_keyword, keyword=keyword)]
    if matches.empty:
        return None
    return matches["category"].value_counts().idxmax()


def clean_brand(brand):
    """None for a missing brand and for "OEM" / "No Brand"."""
    if pd.isna(brand) or normalize_text(brand) in NO_BRAND:
        return None
    return brand


def clean_products(raw, keyword):
    """Apply the cleaning rules, in this order:

    1. drop rows without a name, link or price, and duplicated products
    2. no original price (or one lower than the price) means no discount
    3. a rating of 0 means "not rated yet": it becomes empty (NaN), not 0 stars
    4. "OEM" / "No Brand" become an empty brand
    5. keep only the main category of the search (see main_category)
    """
    if raw.empty:
        return raw

    # 1. unusable and duplicated rows
    df = raw.dropna(subset=["name", "product_url", "price"])
    df = df[df["price"] > 0]
    df = df.drop_duplicates(subset="product_id").copy()

    # 2. prices and discount
    no_discount = df["original_price"].isna() | (df["original_price"] < df["price"])
    df.loc[no_discount, "original_price"] = df.loc[no_discount, "price"]
    df["price"] = df["price"].astype(int)
    df["original_price"] = df["original_price"].astype(int)
    df["discount_pct"] = (100 * (1 - df["price"] / df["original_price"])).round().astype(int)

    # 3-4. ratings and brands
    df["rating"] = df["rating"].where(df["rating"] > 0)
    df["brand"] = df["brand"].apply(clean_brand)

    # 5. one category
    df = df[df["category"] == main_category(df, keyword)]
    return df[COLUMNS].reset_index(drop=True)
