"""Web app tests on a temporary database (no internet needed)."""
import pandas as pd
import pytest

import app as web
import config
from analysis.cleaning import clean_products
from analysis.pricing import add_analysis_columns
from database import db


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    prices = [100_000, 120_000, 150_000, 180_000, 200_000, 220_000, 250_000, 300_000, 5_000]
    raw = pd.DataFrame({
        "source": "Tiki",
        "product_id": [str(i) for i in range(len(prices))],
        "name": [f"Chuột Gaming {i}" for i in range(len(prices))],
        "brand": "Logitech",
        "seller": "Shop",
        "category": "Chuột Chơi Game",
        "price": prices,
        "original_price": [p * 1.2 for p in prices],
        "sold": range(len(prices)),
        "rating": 4.5,
        "review_count": 5,
        "image_url": "https://img",
        "product_url": "https://tiki.vn/p",
    })
    products = add_analysis_columns(clean_products(raw, "chuột gaming"))
    db.save_run("chuột gaming", products)
    return web.app.test_client()


@pytest.mark.parametrize("url", [
    "/",
    "/about",
    "/run/1",
    "/run/1?sort=price_asc&min_price=110000&q=gaming&page=1",
    "/run/1?min_price=not-a-number",
    "/run/1/dashboard",
    "/run/1/dashboard?category=all",
])
def test_pages_load(client, url):
    assert client.get(url).status_code == 200


def test_unknown_run_is_404(client):
    assert client.get("/run/999").status_code == 404


def test_filters_are_applied_in_sql(client):
    rows, total = db.search_products(1, min_price=200_000, sort="price_asc")
    assert total == 4
    assert [row["price"] for row in rows] == [200_000, 220_000, 250_000, 300_000]


def test_csv_export(client):
    response = client.get("/run/1/export.csv")
    assert response.status_code == 200
    header = response.data.decode("utf-8-sig").splitlines()[0]
    assert header.startswith("source,product_id,name")


def test_search_reuses_a_recent_run(client, monkeypatch):
    def crawl_should_not_run(keyword):
        raise AssertionError("the recent run should have been re-used")

    monkeypatch.setattr(web, "run_pipeline", crawl_should_not_run)
    response = client.post("/search", data={"keyword": "Chuột  Gaming"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/run/1")


def test_search_rejects_too_short_keyword(client):
    response = client.post("/search", data={"keyword": "a"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
