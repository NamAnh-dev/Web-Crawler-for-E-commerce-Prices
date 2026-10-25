"""Web pages, with a temporary database and without calling Tiki."""
from unittest.mock import patch

import pandas as pd
import pytest
import requests

import app as web
import database

PRICES = [200_000, 220_000, 250_000, 260_000, 300_000, 310_000, 350_000, 400_000, 420_000, 500_000]


def make_products(prices):
    """Clean products of one search, as clean_products() would return them."""
    n = len(prices)
    return pd.DataFrame({
        "product_id": [str(i) for i in range(n)],
        "name": [f"Chuột Gaming {i}" for i in range(n)],
        "brand": "Logitech",
        "category": "Chuột Chơi Game",
        "price": prices,
        "original_price": prices,
        "discount_pct": 0,
        "sold": list(range(n)),
        "rating": 4.8,
        "review_count": 10,
        "image_url": None,
        "product_url": [f"https://tiki.vn/p{i}.html" for i in range(n)],
    })


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    return web.app.test_client()


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Giá bao nhiêu là" in response.text


def test_search_saves_and_shows_the_result(client):
    raw = make_products(PRICES).drop(columns="discount_pct")
    with patch("app.scraper.crawl", return_value=raw):
        response = client.post("/search", data={"keyword": "chuột gaming"})
    assert response.status_code == 302

    page = client.get(response.headers["Location"])
    assert page.status_code == 200
    assert "Giá sàn tham khảo" in page.text
    assert "305.000 ₫" in page.text  # median price

    home = client.get("/")
    assert "chuột gaming" in home.text  # listed in recent searches


def test_search_needs_a_keyword(client):
    response = client.post("/search", data={"keyword": " "}, follow_redirects=True)
    assert "ít nhất 2 ký tự" in response.text


def test_search_shows_a_message_when_tiki_fails(client):
    with patch("app.scraper.crawl", side_effect=requests.ConnectionError("no internet")):
        response = client.post("/search", data={"keyword": "chuột gaming"}, follow_redirects=True)
    assert "Không lấy được dữ liệu từ Tiki" in response.text


def test_search_without_results(client):
    with patch("app.scraper.crawl", return_value=pd.DataFrame()):
        response = client.post("/search", data={"keyword": "zzqxv"}, follow_redirects=True)
    assert "Không tìm thấy sản phẩm" in response.text


def test_csv_download(client):
    search_id = database.save_search("chuột gaming", make_products(PRICES))
    response = client.get(f"/result/{search_id}/csv")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    assert "product_id,name" in response.data.decode("utf-8-sig")


def test_unknown_search_is_404(client):
    assert client.get("/result/999").status_code == 404
    assert client.get("/result/999/csv").status_code == 404
