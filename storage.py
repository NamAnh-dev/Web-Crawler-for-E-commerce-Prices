from datetime import datetime
from pathlib import Path

import pandas as pd

FOLDER = Path(__file__).parent / "data" / "searches"


def search_path(search_id):
    return FOLDER / f"{search_id}.csv"


def save_search(keyword, products):

    FOLDER.mkdir(parents=True, exist_ok=True)

    numbers = [int(path.stem) for path in FOLDER.glob("*.csv")]
    search_id = max(numbers, default=0) + 1

    table = products.copy()
    table.insert(0, "keyword", keyword)

    table["crawled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # utf-8-sig: Excel hiện đúng tiếng Việt. index=False: không ghi cột số thứ tự dòng.
    table.to_csv(search_path(search_id), index=False, encoding="utf-8-sig")

    return search_id


def load_search(search_id):
    if not search_path(search_id).exists():
        return None

    return pd.read_csv(search_path(search_id), dtype={"product_id": str})


def search_info(search_id, products):

    return {
        "id": search_id,
        "keyword": products["keyword"].iloc[0],
        "category": products["category"].iloc[0],
        "created_at": products["crawled_at"].iloc[0],
        "products": len(products),
        "min_price": int(products["price"].min()),
        "max_price": int(products["price"].max()),
        "median_price": int(products["price"].median()),
    }


def recent_searches(limit=6):

    numbers = [int(path.stem) for path in FOLDER.glob("*.csv")]
    # Sắp xếp giảm dần: số lớn = lượt tìm mới hơn -> đứng đầu
    numbers.sort(reverse=True)

    searches = []

    for search_id in numbers[:limit]:
        searches.append(search_info(search_id, load_search(search_id)))

    return searches
