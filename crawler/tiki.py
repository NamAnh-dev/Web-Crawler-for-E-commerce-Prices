"""Extract: collect products from Tiki's public search API.

This is the same JSON endpoint the tiki.vn search page calls in the browser
(found in DevTools > Network). It needs no login or cookie.
"""
import time

import pandas as pd
import requests

import config

SEARCH_URL = "https://tiki.vn/api/v2/products"
PAGE_SIZE = 40  # the API ignores larger values
HEADERS = {"User-Agent": config.USER_AGENT, "Referer": "https://tiki.vn/"}


def get_page(keyword, page, retries=2):
    """One page of search results as JSON.

    When too many requests are sent, Tiki answers with an HTML page instead of
    JSON for a short while. We respect that: wait (15 s, then 30 s) and retry.
    """
    params = {"q": keyword, "page": page, "limit": PAGE_SIZE}
    for attempt in range(retries + 1):
        response = requests.get(SEARCH_URL, params=params, headers=HEADERS,
                                timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        if "json" in response.headers.get("Content-Type", ""):
            return response.json()
        if attempt < retries:
            time.sleep(15 * (attempt + 1))
    raise RuntimeError("Tiki is limiting requests right now. Try again in a few minutes.")


def fetch_pages(keyword, max_pages=config.MAX_PAGES):
    """Download the raw product list for a keyword, one page at a time."""
    items = []
    for page in range(1, max_pages + 1):
        data = get_page(keyword, page)
        items.extend(data.get("data", []))

        last_page = data.get("paging", {}).get("last_page", 1)
        if page >= last_page:
            break
        time.sleep(config.REQUEST_DELAY)
    return items


def parse_item(item):
    """Keep only the fields we analyse, with the same names for every source."""
    url_path = item.get("url_path")
    return {
        "source": "Tiki",
        "product_id": str(item.get("id")),
        "name": item.get("name"),
        "brand": item.get("brand_name"),
        "seller": item.get("seller_name"),
        "category": item.get("primary_category_name"),
        "price": item.get("price"),
        "original_price": item.get("original_price"),
        "sold": (item.get("quantity_sold") or {}).get("value", 0),
        "rating": item.get("rating_average"),
        "review_count": item.get("review_count", 0),
        "image_url": item.get("thumbnail_url"),
        "product_url": f"https://tiki.vn/{url_path}" if url_path else None,
    }


def crawl(keyword):
    """Return a raw (not yet cleaned) DataFrame of Tiki products."""
    items = fetch_pages(keyword)
    return pd.DataFrame([parse_item(item) for item in items])
