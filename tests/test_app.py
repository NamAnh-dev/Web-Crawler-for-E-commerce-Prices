"""Web pages, with a temporary data folder and without calling Tiki."""

import pandas as pd
import pytest

import app as web
import storage

PRICES = [200_000, 250_000, 300_000, 310_000, 400_000, 500_000]


def make_products():
    """Clean products of one search, as clean_products() returns them."""
    return pd.DataFrame(
        {
            "product_id": ["1", "2", "3", "4", "5", "6"],
            "name": [f"Chuột Gaming {i}" for i in range(6)],
            "brand": "Logitech",
            "category": "Chuột Chơi Game",
            "price": PRICES,
            "original_price": PRICES,
            "discount_pct": 0,
            "sold": [5, 0, 12, 3, 8, 1],
            "rating": 4.8,
            "review_count": 10,
            "image_url": None,
            "product_url": [f"https://tiki.vn/p{i}.html" for i in range(6)],
        }
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A test browser. Searches are saved in a temporary folder, not in data/."""
    monkeypatch.setattr(storage, "FOLDER", tmp_path)
    return web.app.test_client()


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "EcomCheck" in response.text


def test_result_page_shows_a_saved_search(client):
    search_id = storage.save_search("chuột gaming", make_products())

    page = client.get(f"/result/{search_id}")
    assert page.status_code == 200
    assert "305.000 ₫" in page.text  # median of PRICES

    home = client.get("/")
    assert "chuột gaming" in home.text  # listed in the search history


def test_csv_download(client):
    search_id = storage.save_search("chuột gaming", make_products())
    response = client.get(f"/result/{search_id}/csv")
    assert response.status_code == 200
    assert "product_id" in response.data.decode("utf-8-sig")


def test_unknown_search_is_404(client):
    assert client.get("/result/999").status_code == 404
    assert client.get("/result/999/csv").status_code == 404
