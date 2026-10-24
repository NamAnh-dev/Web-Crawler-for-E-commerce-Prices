"""Synthetic Lazada/Shopee search responses and HAR files used by several tests."""
import base64
import json


def lazada_item(item_id, name, price="399000"):
    return {"itemId": item_id, "name": name, "brandName": "XSmart", "sellerName": "XSmart Store",
            "price": price, "originalPrice": "640000", "itemSoldCntShow": "1.0K sold",
            "ratingScore": "4.9", "review": "65", "image": "https://img/1.jpg",
            "itemUrl": f"//www.lazada.vn/products/pdp-i{item_id}.html"}


def shopee_item(item_id, name, price=199_000):
    return {"item_basic": {"itemid": item_id, "shopid": 7, "name": name, "brand": "Logitech",
                           "shop_name": "Gear Shop", "price": price * 100_000,
                           "price_before_discount": 0, "historical_sold": 1234,
                           "item_rating": {"rating_star": 4.8, "rating_count": [321, 1, 2, 3, 4, 311]},
                           "image": "abc123"}}


def entry(url, body, base64_encoded=False):
    content = {"mimeType": "application/json", "text": body}
    if base64_encoded:
        content = {"mimeType": "application/json", "encoding": "base64",
                   "text": base64.b64encode(body.encode()).decode()}
    return {"request": {"method": "GET", "url": url}, "response": {"status": 200, "content": content}}


def make_har():
    lazada_page_1 = ("<html><script>window.pageData = "
                     + json.dumps({"mods": {"listItems": [lazada_item("1", "Chuột Gaming XSmart")]}})
                     + ";</script></html>")
    lazada_page_2 = json.dumps({"mods": {"listItems": [lazada_item("2", "Chuột Gaming Pro", "250000")]}})
    shopee_page = json.dumps({"items": [shopee_item(10, "Chuột Gaming Logitech G102")]})
    entries = [
        entry("https://www.lazada.vn/catalog/?q=chu%E1%BB%99t%20gaming", lazada_page_1),
        entry("https://www.lazada.vn/catalog/?ajax=true&page=2&q=chu%E1%BB%99t%20gaming", lazada_page_2),
        entry("https://shopee.vn/api/v4/search/search_items?keyword=chu%E1%BB%99t%20gaming&limit=60",
              shopee_page, base64_encoded=True),
        entry("https://shopee.vn/api/v4/account/basic/get_account_info", '{"data": {}}'),  # ignored
        entry("https://img.lazcdn.com/logo.png", "not json"),                              # ignored
    ]
    return json.dumps({"log": {"entries": entries}}).encode()
