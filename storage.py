"""Step 3 - Save: every search is kept as one CSV file in data/searches/.

The file name is the number of the search: data/searches/3.csv is the search
shown by the page /result/3. Each file holds the clean products plus two
columns: `keyword` (what was searched) and `crawled_at` (when).
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

FOLDER = Path(__file__).parent / "data" / "searches"


def search_path(search_id):
    return FOLDER / f"{search_id}.csv"


def save_search(keyword, products):
    """Save the products of one search. Returns the number of the new search."""
    FOLDER.mkdir(parents=True, exist_ok=True)
    numbers = [int(path.stem) for path in FOLDER.glob("*.csv")]
    search_id = max(numbers, default=0) + 1

    table = products.copy()
    table.insert(0, "keyword", keyword)
    table["crawled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    # utf-8-sig: Excel shows Vietnamese correctly
    table.to_csv(search_path(search_id), index=False, encoding="utf-8-sig")
    return search_id


def load_search(search_id):
    """The products of one search as a DataFrame, or None if it does not exist."""
    if not search_path(search_id).exists():
        return None
    return pd.read_csv(search_path(search_id), dtype={"product_id": str})


def search_info(search_id, products):
    """A few facts about one search, for the page header and the history list."""
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
    """The latest searches, newest first."""
    numbers = [int(path.stem) for path in FOLDER.glob("*.csv")]
    numbers.sort(reverse=True)

    searches = []
    for search_id in numbers[:limit]:
        searches.append(search_info(search_id, load_search(search_id)))
    return searches
