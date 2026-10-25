"""Extract (learning version): scrape the rendered Tiki search page with Selenium + BeautifulSoup.

This is how I first collected Tiki data: open the search page in a real
browser, wait for the product cards, then read them from the HTML. Later I
saw in DevTools > Network that the page itself loads the products from a
JSON API, and switched the pipeline to that API (crawler/tiki.py): it is
faster, gives more fields and does not break when the page design changes.
This module is kept to compare both methods (notebooks/00_scraping_methods.ipynb).
"""
import json
import re
import time
from urllib.parse import quote, urljoin

import pandas as pd
from bs4 import BeautifulSoup

from analysis.cleaning import parse_sold

SEARCH_PAGE = "https://tiki.vn/search?q="
PRODUCT_CARD = 'a[data-view-id="product_list_item"]'  # one card per product in the result list


def fetch_rendered_html(keyword, max_scrolls=3):
    """HTML of the Tiki search page after its JavaScript has run.

    The product cards are not in the HTML that requests.get() receives: the
    browser draws them after the page loads. So we open the page in headless
    Chrome, wait until the first card appears, scroll a few times (pausing
    between scrolls) so the rest of the page loads, and return the page source.
    Selenium is imported here, so the tests and the web app do not need Chrome.
    """
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1366,900")  # desktop layout
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(SEARCH_PAGE + quote(keyword))
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, PRODUCT_CARD)))
        for _ in range(max_scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        return driver.page_source
    finally:
        driver.quit()  # always close Chrome, even after an error


def text_of(card, selector):
    """Text of the first element matching `selector` inside the card ("" if none)."""
    tag = card.select_one(selector)
    return tag.get_text(" ", strip=True) if tag else ""


def parse_rating(card):
    """Stars are drawn as a bar: a bar 96% wide means 4.8 out of 5 (None = not rated)."""
    for div in card.select(".info div[style*='position: absolute']"):
        match = re.search(r"width:\s*([\d.]+)%", div["style"])
        if match:
            return round(float(match.group(1)) / 20, 1)
    return None


def parse_card(card):
    """One product card -> the same fields as crawler.tiki.parse_item.

    Only class names that describe the content (price-discount__price,
    quantity...) are used: the random-looking ones (sc-68e86366-8) change
    every time Tiki rebuilds its website.
    """
    click_data = json.loads(card["data-view-content"])["click_data"]
    image = card.select_one(".thumbnail img")
    return {
        "source": "Tiki",
        "product_id": str(click_data["id"]),
        "name": text_of(card, "h3"),
        "brand": text_of(card, ".above-product-name-info") or None,  # in capitals, e.g. "LOGITECH"
        "seller": None,          # not shown on the card
        "category": None,        # not shown on the card
        "price": int(re.sub(r"\D", "", text_of(card, ".price-discount__price"))),  # "471.900 ₫"
        "original_price": None,  # the card shows only the discount %, not the old price
        "sold": parse_sold(text_of(card, ".quantity")),  # "Đã bán 4757" -> 4757
        "rating": parse_rating(card),
        "review_count": None,    # not shown on the card
        "image_url": image["srcset"].split(" ")[0] if image and image.get("srcset") else None,
        "product_url": urljoin("https://tiki.vn/", card["href"]),
    }


def parse_search_html(html):
    """Products of a rendered (or saved) search page, as a raw DataFrame.

    Sponsored cards (marked "AD") are skipped: they are paid placements, not
    search results, and their link goes through an ad tracker.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for card in soup.select(PRODUCT_CARD):
        if card.select_one(".ads-badge"):
            continue
        rows.append(parse_card(card))
    return pd.DataFrame(rows)
