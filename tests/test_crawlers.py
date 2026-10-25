"""Parsers of the two sources, tested on saved examples (no internet needed)."""
from unittest.mock import Mock, call, patch

import pytest
import requests

from crawler import lazada, tiki

TIKI_ITEM = {
    "id": 56196502,
    "name": "Chuột Gaming Logitech G102 Gen 2 Lightsync - Hàng Chính Hãng",
    "brand_name": "Logitech",
    "seller_name": "Tiki Trading",
    "primary_category_name": "Chuột Chơi Game",
    "price": 471900,
    "original_price": 471900,
    "quantity_sold": {"text": "Đã bán 4757", "value": 4757},
    "rating_average": 4.8,
    "review_count": 1392,
    "thumbnail_url": "https://salt.tikicdn.com/cache/280x280/ts/product/f8/39/2b/e7f5.jpg",
    "url_path": "chuot-gaming-logitech-g102-p56196502.html?spid=73161623",
}

# Lazada sends every number as text (example taken from a real response)
LAZADA_ITEM = {
    "itemId": "2657269897",
    "name": "Chuột không dây XSmart",
    "brandName": "XSmart",
    "sellerName": "XSmart Store",
    "price": "399000",
    "originalPrice": "640000",
    "itemSoldCntShow": "1.0K sold",
    "ratingScore": "4.938461538461539",
    "review": "65",
    "image": "https://vn-live-01.slatic.net/p/ed44c09e.jpg",
    "itemUrl": "//www.lazada.vn/products/pdp-i2657269897.html",
}


def test_tiki_parse_item():
    row = tiki.parse_item(TIKI_ITEM)
    assert row["product_id"] == "56196502"
    assert row["sold"] == 4757
    assert row["category"] == "Chuột Chơi Game"
    assert row["product_url"] == "https://tiki.vn/chuot-gaming-logitech-g102-p56196502.html?spid=73161623"


def test_tiki_parse_item_without_sales():
    row = tiki.parse_item({**TIKI_ITEM, "quantity_sold": None})
    assert row["sold"] == 0


def test_lazada_parse_item_converts_text_to_numbers():
    row = lazada.parse_item(LAZADA_ITEM)
    assert row["price"] == 399_000
    assert row["original_price"] == 640_000
    assert row["sold"] == 1000              # "1.0K sold"
    assert round(row["rating"], 2) == 4.94
    assert row["review_count"] == 65
    assert row["product_url"] == "https://www.lazada.vn/products/pdp-i2657269897.html"


def test_lazada_full_url():
    assert lazada.full_url("/products/a.html") == "https://www.lazada.vn/products/a.html"
    assert lazada.full_url("https://www.lazada.vn/a") == "https://www.lazada.vn/a"
    assert lazada.full_url(None) is None


# --- Tiki rate limit: requests.get and time.sleep are replaced by fakes ---

def fake_response(status, content_type="application/json", retry_after=None):
    """A stand-in for requests.Response with only what get_page() reads."""
    response = Mock(status_code=status, headers={"Content-Type": content_type})
    if retry_after:
        response.headers["Retry-After"] = retry_after
    response.json.return_value = {"data": [], "paging": {"last_page": 1}}
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}")
    return response


@patch("crawler.tiki.time.sleep")
@patch("crawler.tiki.requests.get")
def test_get_page_waits_and_retries_after_429(fake_get, fake_sleep):
    fake_get.side_effect = [fake_response(429, "text/html", retry_after="5"), fake_response(200)]
    data = tiki.get_page("chuột gaming", 1)
    assert data["paging"]["last_page"] == 1
    fake_sleep.assert_called_once_with(5)                 # follows the Retry-After header


@patch("crawler.tiki.time.sleep")
@patch("crawler.tiki.requests.get")
def test_get_page_gives_up_after_the_last_retry(fake_get, fake_sleep):
    fake_get.return_value = fake_response(503)
    with pytest.raises(RuntimeError):
        tiki.get_page("chuột gaming", 1)
    assert fake_sleep.call_args_list == [call(15), call(30)]   # no Retry-After: 15 s, then 30 s


@patch("crawler.tiki.time.sleep")
@patch("crawler.tiki.requests.get")
def test_get_page_does_not_retry_other_errors(fake_get, fake_sleep):
    fake_get.return_value = fake_response(404)
    with pytest.raises(requests.HTTPError):
        tiki.get_page("chuột gaming", 1)
    fake_sleep.assert_not_called()
