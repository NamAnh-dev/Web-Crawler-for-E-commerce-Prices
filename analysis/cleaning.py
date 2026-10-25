"""Transform: clean raw product data so every source looks the same."""
import re
import unicodedata

import pandas as pd

# Final columns stored in the database, in this order.
COLUMNS = [
    "source", "product_id", "name", "brand", "seller", "category",
    "price", "original_price", "discount_pct", "sold",
    "rating", "review_count", "image_url", "product_url",
]

# Brand values that actually mean "unknown brand".
NO_BRAND = {"", "oem", "no brand", "nobrand", "khong thuong hieu", "none"}
UNKNOWN_CATEGORY = "Chưa phân loại"


def normalize_text(text):
    """Lowercase, remove Vietnamese accents and punctuation.

    "Chuột Gaming-Pro!" -> "chuot gaming pro"
    """
    text = str(text).lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")  # drop accent marks
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def matches_keyword(name, keyword):
    """True if every word of the keyword is a whole word of the product name.

    Whole words, not substrings: the keyword "tai nghe" must not match a name
    containing "detail" just because "tai" is inside it.
    """
    name_words = set(normalize_text(name).split())
    return all(word in name_words for word in normalize_text(keyword).split())


def parse_sold(value):
    """Turn a sold count into an int.

    1234 -> 1234,  "1.2K sold" -> 1200,  "3,5k" -> 3500,  "1.234" -> 1234
    """
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return 0 if pd.isna(value) else int(value)

    match = re.search(r"(\d[\d.,]*)\s*(k|m|tr)?", str(value).lower())
    if not match:
        return 0
    number, unit = match.groups()
    if unit:  # "1,2k" -> 1.2 * 1000
        multiplier = 1_000 if unit == "k" else 1_000_000
        return int(float(number.replace(",", ".")) * multiplier)
    return int(re.sub(r"\D", "", number))  # "1.234" -> 1234 (dot = thousands separator)


def clean_brand(brand):
    if brand is None or pd.isna(brand) or normalize_text(brand) in NO_BRAND:
        return None
    return str(brand).strip()


def is_relevant(df, keyword):
    """Which rows are really the product the user searched for?

    Search APIs also return loosely related items, so we keep a product when
    - its name contains every word of the keyword, OR
    - it belongs to the main category of those exact matches.
    The second rule keeps "Chuột chơi game Logitech" for the keyword
    "chuột gaming", even though the word "gaming" is missing from its name.
    """
    exact = df["name"].apply(matches_keyword, keyword=keyword)
    main_category = df.loc[exact, "category"].mode()[:1]   # empty if no category data
    return exact | df["category"].isin(main_category)


def clean_products(raw, keyword):
    """Apply the same cleaning rules to products from any source.

    1. drop rows without a name, link or valid price
    2. drop duplicated products
    3. fix prices: no original price (or lower than price) = no discount
    4. rating 0 means "not rated yet" -> empty
    5. keep only products relevant to the keyword (see is_relevant)
    """
    if raw.empty:
        return pd.DataFrame(columns=COLUMNS)

    df = raw.copy()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["original_price"] = pd.to_numeric(df["original_price"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    # 1-2. remove unusable and duplicated rows
    df = df.dropna(subset=["name", "product_url", "price"])
    df = df[df["price"] > 0]
    df = df.drop_duplicates(subset=["source", "product_id"])

    # 3. prices and discount
    df["price"] = df["price"].round().astype(int)
    has_discount = df["original_price"] > df["price"]
    df["original_price"] = df["original_price"].where(has_discount, df["price"]).round().astype(int)
    df["discount_pct"] = (100 * (1 - df["price"] / df["original_price"])).round().astype(int)

    # 4. ratings, counts and brand
    df["rating"] = df["rating"].where(df["rating"] > 0).round(1)
    df["sold"] = df["sold"].apply(parse_sold)
    df["review_count"] = pd.to_numeric(df["review_count"], errors="coerce").fillna(0).astype(int)
    df["brand"] = df["brand"].apply(clean_brand)

    # 5. relevance filter
    df = df[is_relevant(df, keyword)]
    df["category"] = df["category"].fillna(UNKNOWN_CATEGORY)

    return df[COLUMNS].reset_index(drop=True)
