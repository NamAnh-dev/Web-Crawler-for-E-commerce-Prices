"""Read Shopee search results that you saved from your own browser.

Shopee's search API only answers logged-in browsers (it returns 403 to scripts),
so, as for Lazada, the data comes from a HAR file you export yourself.
The response of `/api/v4/search/search_items` is a list of `items`; most
fields are inside `item_basic`.
"""
import json

PRICE_UNIT = 100_000  # Shopee stores 199 000 VND as 19 900 000 000
IMAGE_URL = "https://down-vn.img.susercontent.com/file/{}"


def items_from_response(text):
    return json.loads(text).get("items") or []


def parse_item(item):
    basic = item.get("item_basic") or item
    rating = basic.get("item_rating") or {}
    item_id = basic.get("itemid") or item.get("itemid")
    shop_id = basic.get("shopid") or item.get("shopid")
    price = basic.get("price") or (item.get("item_card_display_price") or {}).get("price") or 0
    price_before = basic.get("price_before_discount") or 0

    return {
        "source": "Shopee",
        "product_id": str(item_id),
        "name": basic.get("name"),
        "brand": basic.get("brand"),
        "seller": basic.get("shop_name"),
        "category": None,  # only a category id is sent, see analysis/categories.py
        "price": price / PRICE_UNIT,
        "original_price": price_before / PRICE_UNIT or None,
        "sold": basic.get("historical_sold") or basic.get("sold") or 0,  # cumulative, like Tiki
        "rating": rating.get("rating_star"),
        "review_count": (rating.get("rating_count") or [0])[0],
        "image_url": IMAGE_URL.format(basic["image"]) if basic.get("image") else None,
        "product_url": f"https://shopee.vn/product/{shop_id}/{item_id}" if item_id and shop_id else None,
    }
