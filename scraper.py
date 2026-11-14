import argparse
import json
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from cleaning import clean_products, normalize_text

API_URL = "https://tiki.vn/api/v2/products"
SEARCH_PAGE_URL = "https://tiki.vn/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
}
PAGE_SIZE = 40
DELAY = 1
TIMEOUT = 15
MAX_TRIES = 3


def get_api_page(keyword, page):

    params = {"q": keyword, "page": page, "limit": PAGE_SIZE}

    for attempt in range(1, MAX_TRIES + 1):
        response = requests.get(
            API_URL, params=params, headers=HEADERS, timeout=TIMEOUT
        )

        if response.status_code not in (429, 503):
            response.raise_for_status()
            if "json" in response.headers.get("Content-Type", ""):
                return response.json()
        if attempt < MAX_TRIES:
            time.sleep(10 * attempt)

    raise RuntimeError(
        "Tiki is limiting requests right now. Try again in a few minutes."
    )


def parse_search_page(html):

    soup = BeautifulSoup(html, "html.parser")

    script = soup.select_one("script#__NEXT_DATA__")

    if script is None:
        raise RuntimeError("Could not find the __NEXT_DATA__ script on the Tiki page.")
    data = json.loads(script.get_text())

    items = data["props"]["initialState"]["catalog"]["data"]

    return [item for item in items if not item.get("advertisement")]


def parse_item(item):

    sold = item.get("quantity_sold") or {}
    return {
        "product_id": str(item.get("id")),  # đổi sang chuỗi: mã là "tên"
        "name": item.get("name"),  # tên sản phẩm
        "brand": item.get("brand_name"),  # thương hiệu
        "category": item.get("primary_category_name"),  # danh mục chính
        "price": item.get("price"),  # giá bán hiện tại (VND)
        "original_price": item.get("original_price"),  # giá gốc trước khi giảm
        "sold": sold.get("value", 0),  # số lượng đã bán, thiếu thì là 0
        "rating": item.get("rating_average"),  # điểm đánh giá trung bình (0 - 5 sao)
        "review_count": item.get("review_count", 0),  # số lượt đánh giá
        "image_url": item.get("thumbnail_url"),  # link ảnh nhỏ
        "product_url": "https://tiki.vn/" + item["url_path"]
        if item.get("url_path")
        else None,
    }


def crawl(keyword, pages=5):

    rows = []
    for page in range(1, pages + 1):
        data = get_api_page(keyword, page)
        for item in data["data"]:
            rows.append(parse_item(item))

        if page >= data["paging"]["last_page"]:
            break
        time.sleep(DELAY)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Collect one keyword from Tiki and save it as CSV."
    )
    parser.add_argument("keyword")
    parser.add_argument("--pages", type=int, default=5, help="pages of 40 products")
    args = parser.parse_args()

    raw = crawl(args.keyword, args.pages)
    products = clean_products(raw, args.keyword)

    path = f"data/{normalize_text(args.keyword).replace(' ', '_')}.csv"

    products.to_csv(path, index=False, encoding="utf-8-sig")
    print(
        f"{len(raw)} products downloaded, {len(products)} kept after cleaning -> {path}"
    )
