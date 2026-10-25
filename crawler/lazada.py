"""Read Lazada search results that you saved from your own browser.

Lazada answers automated requests with an anti-bot page, so this project never
requests Lazada itself. You search on lazada.vn as usual, export the network
log (HAR) and `crawler/browser_import.py` passes the search responses here.
"""
import json
import re

from analysis.cleaning import parse_sold


def items_from_response(text):
    """Product list of one search response.

    Pages 2, 3... arrive as JSON (`?ajax=true`); the first page is HTML with
    the same data inside `window.pageData = {...}`.
    """
    text = text.strip()
    if not text.startswith("{"):
        match = re.search(r"window\.pageData\s*=\s*(\{.*?\})\s*;?\s*</script>", text, re.S)
        if not match:
            return []
        text = match.group(1)
    data = json.loads(text)
    return data.get("mods", {}).get("listItems") or []


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
        "category": None,  # only category ids are sent; set to the main category on import
        "price": to_number(item.get("price")),
        "original_price": to_number(item.get("originalPrice")),
        "sold": parse_sold(item.get("itemSoldCntShow")),  # "1.2K sold" -> 1200
        "rating": to_number(item.get("ratingScore")),
        "review_count": to_number(item.get("review")) or 0,
        "image_url": item.get("image"),
        "product_url": full_url(item.get("itemUrl")),
    }
