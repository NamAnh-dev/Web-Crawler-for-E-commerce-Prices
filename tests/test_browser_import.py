"""Importing Lazada/Shopee results saved from a browser (synthetic HAR files)."""
import json

from crawler import browser_import, lazada, shopee
from samples import make_har, shopee_item


def test_read_har_finds_both_marketplaces():
    raw = browser_import.read_file("search.har", make_har())
    assert sorted(raw["source"]) == ["Lazada", "Lazada", "Shopee"]


def test_read_single_saved_response():
    body = json.dumps({"items": [shopee_item(11, "Chuột Gaming A")]}).encode()
    raw = browser_import.read_file("response.json", body)
    assert list(raw["source"]) == ["Shopee"]


def test_unknown_file_gives_no_rows():
    assert browser_import.read_file("notes.json", b'{"hello": "world"}').empty


def test_shopee_parse_item_converts_units():
    row = shopee.parse_item(shopee_item(10, "Chuột Gaming Logitech G102"))
    assert row["price"] == 199_000            # Shopee stores price x 100 000
    assert row["original_price"] is None      # 0 = no discount
    assert row["sold"] == 1234
    assert row["review_count"] == 321
    assert row["product_url"] == "https://shopee.vn/product/7/10"
    assert row["image_url"].endswith("/abc123")


def test_lazada_items_from_html_page():
    html = '<script>window.pageData = {"mods": {"listItems": [{"itemId": "5"}]}};</script>'
    assert lazada.items_from_response(html) == [{"itemId": "5"}]
    assert lazada.items_from_response("<html>no data</html>") == []
