"""Tests for scraper.py, on saved examples: no internet needed."""
import json
from unittest.mock import Mock, patch

import pytest

import scraper

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
    assert row["sold"] == 4757
    assert row["product_url"] == "https://tiki.vn/chuot-gaming-logitech-g102-p56196502.html?spid=73161623"


def test_parse_item_without_sales_or_link():
    row = scraper.parse_item({**ITEM, "quantity_sold": None, "url_path": None})
    assert row["sold"] == 0
    assert row["product_url"] is None


def test_parse_search_page_reads_next_data_and_skips_ads():
    ad = {**ITEM, "id": 1, "advertisement": {"ad_id": 99}}
    page_data = {"props": {"initialState": {"catalog": {"data": [ad, ITEM]}}}}
    html = ('<html><body><div id="__next"></div>'
            f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(page_data)}</script>'
            '</body></html>')

    items = scraper.parse_search_page(html)
    assert [item["id"] for item in items] == [56196502]


def fake_response(status, data=None, content_type="application/json"):
    response = Mock(status_code=status, headers={"Content-Type": content_type})
    response.json.return_value = data
    return response


def test_get_api_page_waits_and_retries_after_http_429():
    data = {"data": [ITEM], "paging": {"last_page": 1}}
    responses = [fake_response(429), fake_response(200, data)]
    with patch("scraper.requests.get", side_effect=responses), patch("scraper.time.sleep") as sleep:
        assert scraper.get_api_page("chuột gaming", 1) == data
    sleep.assert_called_once_with(10)


def test_get_api_page_retries_when_tiki_sends_html_instead_of_json():
    data = {"data": [ITEM], "paging": {"last_page": 1}}
    responses = [fake_response(200, content_type="text/html"), fake_response(200, data)]
    with patch("scraper.requests.get", side_effect=responses), patch("scraper.time.sleep"):
        assert scraper.get_api_page("chuột gaming", 1) == data


def test_get_api_page_gives_up_after_three_tries():
    responses = [fake_response(429)] * 3
    with patch("scraper.requests.get", side_effect=responses), patch("scraper.time.sleep") as sleep:
        with pytest.raises(RuntimeError):
            scraper.get_api_page("chuột gaming", 1)
    assert sleep.call_count == 2  # no useless wait after the last try


def test_crawl_stops_at_the_last_page():
    data = {"data": [ITEM], "paging": {"last_page": 1}}
    with patch("scraper.get_api_page", return_value=data) as get_page:
        raw = scraper.crawl("chuột gaming", pages=5)
    assert get_page.call_count == 1
    assert len(raw) == 1
