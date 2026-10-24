"""Web app tests on a temporary database (no internet needed)."""
import io

import pandas as pd
import pytest

import app as web
import config
from analysis.cleaning import clean_products
from analysis.pricing import add_analysis_columns
from database import db
from samples import make_har

MICE = [100_000, 120_000, 150_000, 180_000, 200_000, 220_000, 250_000, 300_000, 5_000]
PADS = [50_000, 60_000, 70_000, 80_000]


def tiki_products(price_change=0):
    """A snapshot with 9 gaming mice and 4 mouse pads."""
    rows = [{"product_id": f"m{i}", "name": f"Chuột Gaming {i}", "category": "Chuột Chơi Game",
             "price": price + price_change, "sold": 10 * i} for i, price in enumerate(MICE)]
    rows += [{"product_id": f"p{i}", "name": f"Lót Chuột Gaming {i}", "category": "Bàn Di Chuột",
              "price": price, "sold": i} for i, price in enumerate(PADS)]
    raw = pd.DataFrame(rows).assign(
        source="Tiki", brand="Logitech", seller="Shop", original_price=lambda d: d["price"] * 1.2,
        rating=4.5, review_count=5, image_url="https://img", product_url="https://tiki.vn/p",
    )
    return add_analysis_columns(clean_products(raw, "chuột gaming"))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.save_run("chuột gaming", tiki_products())
    return web.app.test_client()


@pytest.mark.parametrize("url", [
    "/",
    "/about",
    "/run/1",
    "/run/1?sort=price_asc&min_price=110000&q=gaming&page=1",
    "/run/1?min_price=not-a-number",
    "/run/1?category=",
    "/run/1/dashboard",
    "/run/1/dashboard?category=all",
    "/run/1/import",
    "/history?keyword=chuột gaming",
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


def test_search_reports_network_errors(client, monkeypatch):
    def rate_limited(keyword):
        raise RuntimeError("Tiki is limiting requests right now.")

    monkeypatch.setattr(web, "run_pipeline", rate_limited)
    response = client.post("/search", data={"keyword": "bàn phím cơ"}, follow_redirects=True)
    assert "Tiki is limiting requests" in response.data.decode()


def test_import_har_adds_lazada_and_shopee(client):
    har = (io.BytesIO(make_har()), "lazada_shopee.har")
    response = client.post("/run/1/import", data={"files": har}, content_type="multipart/form-data")
    assert response.status_code == 302

    products = db.load_products(1)
    imported = products[products["source"] != "Tiki"]
    assert sorted(imported["source"]) == ["Lazada", "Lazada", "Shopee"]
    assert (imported["category_predicted"] == 1).all()
    assert db.get_run(1)["product_count"] == len(products)
    assert client.get("/run/1/dashboard").status_code == 200   # marketplace comparison renders


def test_import_without_search_results(client):
    empty = (io.BytesIO(b'{"log": {"entries": []}}'), "empty.har")
    response = client.post("/run/1/import", data={"files": empty}, content_type="multipart/form-data",
                           follow_redirects=True)
    assert "Không có kết quả tìm kiếm" in response.data.decode()


def test_history_compares_two_snapshots(client):
    db.save_run("Chuột Gaming", tiki_products(price_change=-10_000))
    page = client.get("/history?keyword=chuột gaming").data.decode()
    assert "Bán được nhiều nhất" in page
    assert "Giảm giá nhiều nhất" in page
