"""Extract: collect products from Lazada's catalog endpoint (optional source).

Lazada replies to automated requests with an anti-bot verification page, so
this source is only used when LAZADA_COOKIE is set in `.env`. If Lazada still
returns the verification page, the source is skipped with a clear message.
"""
import time

import pandas as pd
import requests

import config
from analysis.cleaning import parse_sold

SEARCH_URL = "https://www.lazada.vn/catalog/"


def fetch_pages(keyword, max_pages=config.MAX_PAGES):
    if not config.LAZADA_COOKIE:
        raise RuntimeError("Lazada is not configured (LAZADA_COOKIE is empty).")

    headers = {
        "User-Agent": config.USER_AGENT,
        "Referer": "https://www.lazada.vn/",
        "Cookie": config.LAZADA_COOKIE,
    }
    items = []
    for page in range(1, max_pages + 1):
        params = {"ajax": "true", "page": page, "q": keyword}
        response = requests.get(SEARCH_URL, params=params, headers=headers,
                                timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        if "json" not in response.headers.get("Content-Type", ""):
            raise RuntimeError("Lazada returned a verification page instead of data "
                               "(the cookie in .env has probably expired).")

        page_items = response.json().get("mods", {}).get("listItems", [])
        if not page_items:
            break
        items.extend(page_items)
        time.sleep(config.REQUEST_DELAY)
    return items


def to_number(value):
    """Lazada sends numbers as text, e.g. "399000" or "4.93"."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def full_url(url):
    """Item URLs come as "//www.lazada.vn/..." or "/products/..."."""
    if not url:
        return None
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://www.lazada.vn" + url
    return url


def parse_item(item):
    return {
        "source": "Lazada",
        "product_id": str(item.get("itemId")),
        "name": item.get("name"),
        "brand": item.get("brandName"),
        "seller": item.get("sellerName"),
        "category": None,  # not included in Lazada's search results
        "price": to_number(item.get("price")),
        "original_price": to_number(item.get("originalPrice")),
        "sold": parse_sold(item.get("itemSoldCntShow")),  # "1.2K sold" -> 1200
        "rating": to_number(item.get("ratingScore")),
        "review_count": to_number(item.get("review")) or 0,
        "image_url": item.get("image"),
        "product_url": full_url(item.get("itemUrl")),
    }


def crawl(keyword):
    items = fetch_pages(keyword)
    return pd.DataFrame([parse_item(item) for item in items])
