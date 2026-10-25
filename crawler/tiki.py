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
RATE_LIMIT_STATUS = (429, 503)  # "too many requests" / "service busy": wait and try again
MAX_WAIT = 60                    # seconds; a web search should not hang for minutes


def wait_seconds(response, attempt):
    """How long to wait before trying again.

    If the server says how long (the Retry-After header, in seconds), we follow
    it, up to MAX_WAIT. Otherwise we wait 15 s, then 30 s.
    """
    retry_after = response.headers.get("Retry-After", "")
    if retry_after.isdigit():
        return min(int(retry_after), MAX_WAIT)
    return 15 * (attempt + 1)


def get_page(keyword, page, retries=2):
    """One page of search results as JSON.

    When too many requests are sent, Tiki answers with HTTP 429 (or 503), or
    with an HTML page instead of JSON. We respect that: wait and retry.
    The status is checked before raise_for_status(), otherwise a 429 would
    stop the crawl at once instead of backing off.
    """
    params = {"q": keyword, "page": page, "limit": PAGE_SIZE}
    for attempt in range(retries + 1):
        response = requests.get(SEARCH_URL, params=params, headers=HEADERS,
                                timeout=config.REQUEST_TIMEOUT)
        if response.status_code not in RATE_LIMIT_STATUS:
            response.raise_for_status()  # other errors (404, 500...) are not retried
            if "json" in response.headers.get("Content-Type", ""):
                return response.json()
        if attempt < retries:
            time.sleep(wait_seconds(response, attempt))
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


def crawl(keyword, max_pages=None):
    """Return a raw (not yet cleaned) DataFrame of Tiki products."""
    items = fetch_pages(keyword, max_pages or config.MAX_PAGES)
    return pd.DataFrame([parse_item(item) for item in items])
