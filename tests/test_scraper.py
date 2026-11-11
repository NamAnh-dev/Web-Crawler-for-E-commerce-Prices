"""Tests for scraper.py on a saved example: no internet needed."""

import json

import scraper

# One product, copied from a real answer of the Tiki search API
ITEM = {
    "id": 56196502,
    "name": "Chuột Gaming Logitech G102 Gen 2 Lightsync - Hàng Chính Hãng",
    "brand_name": "Logitech",
    "primary_category_name": "Chuột Chơi Game",
    "price": 471900,
    "original_price": 471900,
    "quantity_sold": {"text": "Đã bán 4757", "value": 4757},
    "rating_average": 4.8,
    "review_count": 1392,
    "thumbnail_url": "https://salt.tikicdn.com/cache/280x280/ts/product/f8/39/2b/e7f5.jpg",
    "url_path": "chuot-gaming-logitech-g102-p56196502.html?spid=73161623",
}


def test_parse_item_keeps_the_fields_we_need():
    row = scraper.parse_item(ITEM)
    assert row["product_id"] == "56196502"
    assert row["category"] == "Chuột Chơi Game"
    assert row["price"] == 471900
    assert row["sold"] == 4757
    assert row["product_url"].startswith("https://tiki.vn/chuot-gaming-logitech")


def test_parse_item_without_sales_or_link():
    item = ITEM.copy()
    item["quantity_sold"] = None  # nothing sold yet
    item["url_path"] = None
    row = scraper.parse_item(item)
    assert row["sold"] == 0
    assert row["product_url"] is None


def test_parse_search_page_reads_next_data_and_skips_ads():
    ad = ITEM.copy()
    ad["id"] = 1
    ad["advertisement"] = {"ad_id": 99}
    page_data = {"props": {"initialState": {"catalog": {"data": [ad, ITEM]}}}}
    html = (
        "<html><body>"
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(page_data)
        + "</script></body></html>"
    )

    items = scraper.parse_search_page(html)
    assert len(items) == 1
    assert items[0]["id"] == 56196502
