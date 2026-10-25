"""HTML scraping of a saved Tiki search page (offline: no Chrome, no internet needed)."""
from pathlib import Path

from analysis.cleaning import COLUMNS, clean_products
from crawler import tiki_html

FIXTURE = Path(__file__).parent / "fixtures" / "tiki_search_sample.html"


def saved_page():
    return FIXTURE.read_text(encoding="utf-8")


def test_parse_search_html_reads_the_product_cards():
    products = tiki_html.parse_search_html(saved_page())
    assert len(products) > 0
    assert (products["price"] > 0).all()
    assert products["product_url"].str.startswith("https://tiki.vn/").all()
    assert (products["name"].str.len() > 0).all()


def test_sponsored_cards_are_skipped():
    html = saved_page()
    assert 'class="ads-badge"' in html                    # the saved page does contain ads...
    products = tiki_html.parse_search_html(html)
    assert not products["product_url"].str.contains("pixel").any()   # ...but none is kept


def test_one_card():
    card = """
    <a data-view-id="product_list_item" data-view-content='{"click_data": {"id": 123, "spid": 456}}'
       href="/chuot-gaming-abc-p123.html?spid=456">
      <div class="thumbnail"><img srcset="https://salt.tikicdn.com/a.jpg 1x, https://salt.tikicdn.com/b.jpg 2x"></div>
      <div class="info">
        <div class="price-discount__price">185.000<sup>₫</sup></div>
        <div class="above-product-name-info"><span>TECH77</span></div>
        <h3>Chuột Gaming ABC</h3>
        <div><div style="position: absolute; left: 0px; width: 96%;"></div></div>
        <span class="quantity">Đã bán 1,2k</span>
      </div>
    </a>"""
    row = tiki_html.parse_search_html(card).iloc[0]
    assert row["product_id"] == "123"
    assert row["price"] == 185_000
    assert row["rating"] == 4.8                    # a star bar 96 % wide
    assert row["sold"] == 1200
    assert row["image_url"] == "https://salt.tikicdn.com/a.jpg"
    assert row["product_url"] == "https://tiki.vn/chuot-gaming-abc-p123.html?spid=456"


def test_scraped_products_go_through_the_same_cleaning():
    clean = clean_products(tiki_html.parse_search_html(saved_page()), "chuột gaming")
    assert list(clean.columns) == COLUMNS
    assert len(clean) > 0
