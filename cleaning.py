import re
import unicodedata

import pandas as pd

COLUMNS = [
    "product_id",
    "name",
    "brand",
    "category",
    "price",
    "original_price",
    "discount_pct",
    "sold",
    "rating",
    "review_count",
    "image_url",
    "product_url",
]

NO_BRAND = {"oem", "no brand", "nobrand", "khong thuong hieu"}


def normalize_text(text):

    text = str(text).lower().replace("đ", "d")

    text = unicodedata.normalize("NFD", text)

    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")

    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def matches_keyword(name, keyword):

    name_words = normalize_text(name).split()
    for word in normalize_text(keyword).split():
        if word not in name_words:
            return False
    return True


def main_category(df, keyword):

    matches = df[df["name"].apply(matches_keyword, keyword=keyword)]
    if matches.empty:
        return None
    return matches["category"].value_counts().idxmax()


def clean_brand(brand):

    if pd.isna(brand) or normalize_text(brand) in NO_BRAND:
        return None
    return brand


def clean_products(raw, keyword):

    if raw.empty:
        return raw

    df = raw.dropna(subset=["name", "product_url", "price"])
    df = df[df["price"] > 0]
    df = df.drop_duplicates(subset="product_id").copy()

    no_discount = df["original_price"].isna() | (df["original_price"] < df["price"])

    # gán giá gốc = giá bán (không giảm giá)
    df.loc[no_discount, "original_price"] = df.loc[no_discount, "price"]

    # Đổi sang số nguyên (vd 200000.0 -> 200000)
    df["price"] = df["price"].astype(int)
    df["original_price"] = df["original_price"].astype(int)

    # Phần trăm giảm = 100 x (1 - giá bán / giá gốc), làm tròn thành số nguyên.
    df["discount_pct"] = (
        (100 * (1 - df["price"] / df["original_price"])).round().astype(int)
    )

    # rating == 0 thì gán None
    df.loc[df["rating"] == 0, "rating"] = None

    df["brand"] = df["brand"].apply(clean_brand)

    # Chỉ giữ một danh mục: những dòng có category bằng danh mục chính.
    df = df[df["category"] == main_category(df, keyword)]

    return df[COLUMNS].reset_index(drop=True)
