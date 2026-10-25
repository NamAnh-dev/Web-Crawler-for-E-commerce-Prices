"""Step 1 - Collect: download the products Tiki lists for a keyword.

Tiki gives the same products in two ways, and both are written here:

- get_api_page(): the JSON search API that the tiki.vn search page calls
  (found in Chrome DevTools > Network). Small and fast, so the web app uses it.
- get_html_page(): the search page itself, read with BeautifulSoup. Used in
  notebook 01 to compare both ways.

Run from the terminal to save a clean CSV in data/:
    python scraper.py "chuột gaming" --pages 5
"""
import argparse
import json
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from cleaning import clean_products, normalize_text

API_URL = "https://tiki.vn/api/v2/products"
SEARCH_PAGE_URL = "https://tiki.vn/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
}
PAGE_SIZE = 40   # Tiki sends at most 40 products per page
DELAY = 1        # seconds to wait between two pages, to be polite
TIMEOUT = 15     # seconds before giving up on a request
MAX_TRIES = 3


def get_api_page(keyword, page):
    """One page of search results from the JSON API.

    When it gets too many requests, Tiki answers HTTP 429 ("too many
    requests") or 503 ("busy"), or sends an HTML page instead of JSON.
    Then we wait (10 s, then 20 s) and try again. The status is checked
    before raise_for_status(), otherwise a 429 would stop the crawl at once.
    """
    params = {"q": keyword, "page": page, "limit": PAGE_SIZE}
    for attempt in range(1, MAX_TRIES + 1):
        response = requests.get(API_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
        if response.status_code not in (429, 503):
            response.raise_for_status()  # other errors (404, 500...) are not retried
            if "json" in response.headers.get("Content-Type", ""):
                return response.json()
        if attempt < MAX_TRIES:
            time.sleep(10 * attempt)
    raise RuntimeError("Tiki is limiting requests right now. Try again in a few minutes.")


def parse_search_page(html):
    """The products inside the HTML of a tiki.vn/search page.

    The product cards are drawn by JavaScript in the browser, so they are not
    in the HTML that requests downloads. But the website (built with Next.js)
    also writes the data of the page as JSON in a <script id="__NEXT_DATA__">
    tag: BeautifulSoup finds that tag and json.loads() reads it.
    Sponsored products (ads) are skipped: they are paid placements.
    """
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    data = json.loads(script.string)
    items = data["props"]["initialState"]["catalog"]["data"]
    return [item for item in items if not item.get("advertisement")]


def get_html_page(keyword, page):
    """The same page of results, taken from the search page instead of the API."""
    params = {"q": keyword, "page": page}
    response = requests.get(SEARCH_PAGE_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return parse_search_page(response.text)


def parse_item(item):
    """Keep only the fields we analyse, with clear column names."""
    sold = item.get("quantity_sold") or {}  # missing when nothing was sold yet
    return {
        "product_id": str(item.get("id")),
        "name": item.get("name"),
        "brand": item.get("brand_name"),
        "category": item.get("primary_category_name"),
        "price": item.get("price"),
        "original_price": item.get("original_price"),
        "sold": sold.get("value", 0),
        "rating": item.get("rating_average"),
        "review_count": item.get("review_count", 0),
        "image_url": item.get("thumbnail_url"),
        "product_url": "https://tiki.vn/" + item["url_path"] if item.get("url_path") else None,
    }


def crawl(keyword, pages=5):
    """Download up to `pages` pages of results (40 products each) as a raw table."""
    rows = []
    for page in range(1, pages + 1):
        data = get_api_page(keyword, page)
        for item in data["data"]:
            rows.append(parse_item(item))

        if page >= data["paging"]["last_page"]:  # no more results
            break
        time.sleep(DELAY)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect one keyword from Tiki and save it as CSV.")
    parser.add_argument("keyword")
    parser.add_argument("--pages", type=int, default=5, help="pages of 40 products")
    args = parser.parse_args()

    raw = crawl(args.keyword, args.pages)
    products = clean_products(raw, args.keyword)
    path = f"data/{normalize_text(args.keyword).replace(' ', '_')}.csv"
    products.to_csv(path, index=False, encoding="utf-8-sig")  # utf-8-sig: Excel shows Vietnamese
    print(f"{len(raw)} products downloaded, {len(products)} kept after cleaning -> {path}")
