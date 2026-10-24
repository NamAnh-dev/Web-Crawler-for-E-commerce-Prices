"""Import search results that you saved from your own browser (Lazada, Shopee).

Supported files:
- .har   DevTools > Network > Export HAR (sanitized). Every Lazada or Shopee
         search response inside the log is read; everything else is ignored.
- .json  one saved search response
- .html  a saved Lazada search page
Files are only read, never stored by the app.
"""
import base64
import json
from urllib.parse import parse_qs, urlparse

import pandas as pd

from analysis.cleaning import COLUMNS
from crawler import lazada, shopee

PARSERS = {"Lazada": lazada, "Shopee": shopee}


def source_of_url(url):
    """Which marketplace search returned this response (None = not a search)."""
    if "lazada.vn" in url and ("/catalog/" in url or "/tag/" in url):
        return "Lazada"
    if "shopee.vn" in url and "/search/search_items" in url:
        return "Shopee"
    return None


def source_of_text(text):
    """Guess the marketplace of a single saved response from its content."""
    if "listItems" in text:
        return "Lazada"
    if '"item_basic"' in text or '"itemid"' in text:
        return "Shopee"
    return None


def search_keyword(url):
    query = parse_qs(urlparse(url).query)
    return (query.get("q") or query.get("keyword") or [""])[0]


def har_responses(text):
    """(url, response body) of every request stored in a HAR file."""
    for entry in json.loads(text).get("log", {}).get("entries", []):
        content = entry.get("response", {}).get("content", {})
        body = content.get("text")
        if not body:
            continue
        if content.get("encoding") == "base64":
            body = base64.b64decode(body).decode("utf-8", errors="replace")
        yield entry["request"]["url"], body


def parse_response(source, body):
    """Rows of one search response; an unexpected format gives no rows."""
    parser = PARSERS[source]
    try:
        items = parser.items_from_response(body)
    except (ValueError, AttributeError):
        return []
    return [parser.parse_item(item) for item in items]


def read_file(filename, data):
    """Products found in one saved file.

    Returns (raw DataFrame, set of search keywords seen in the file).
    """
    text = data.decode("utf-8-sig", errors="replace")
    rows, keywords = [], set()

    if filename.lower().endswith(".har"):
        for url, body in har_responses(text):
            source = source_of_url(url)
            if source:
                rows += parse_response(source, body)
                keywords.add(search_keyword(url))
    else:
        source = source_of_text(text)
        if source:
            rows = parse_response(source, text)

    return pd.DataFrame(rows, columns=[c for c in COLUMNS if c != "discount_pct"]), keywords - {""}
