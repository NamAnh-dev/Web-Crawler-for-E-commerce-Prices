"""Import Lazada/Shopee search results that you saved from your own browser.

Supported files:
- .har   DevTools > Network > Export HAR. Every Lazada or Shopee search
         response inside it is read; everything else is ignored.
- .json  one saved search response
- .html  a saved Lazada search page
"""
import base64
import json

import pandas as pd

from analysis.cleaning import COLUMNS
from crawler import lazada, shopee

PARSERS = {"Lazada": lazada, "Shopee": shopee}
RAW_COLUMNS = [c for c in COLUMNS if c != "discount_pct"]  # discount is computed when cleaning


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
    if '"item_basic"' in text:
        return "Shopee"
    return None


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


def read_file(filename, data):
    """Raw products found in one saved file (an empty table if none)."""
    text = data.decode("utf-8-sig", errors="replace")
    if filename.lower().endswith(".har"):
        responses = [(source_of_url(url), body) for url, body in har_responses(text)]
    else:
        responses = [(source_of_text(text), text)]

    rows = []
    for source, body in responses:
        if source is None:
            continue
        parser = PARSERS[source]
        try:
            rows += [parser.parse_item(item) for item in parser.items_from_response(body)]
        except (ValueError, AttributeError):  # not the data we expect: skip this response
            continue
    return pd.DataFrame(rows, columns=RAW_COLUMNS)
