"""Step 4 - Save: keep every search in a small SQLite database.

Two tables: `searches` (one row per search) and `products` (the products
found by that search, linked by search_id). SQLite needs no server: the
database is a single file, created automatically.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "data" / "searches.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS searches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword     TEXT NOT NULL,
    category    TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    search_id       INTEGER NOT NULL REFERENCES searches(id),
    product_id      TEXT    NOT NULL,
    name            TEXT    NOT NULL,
    brand           TEXT,              -- NULL = no brand
    category        TEXT    NOT NULL,
    price           INTEGER NOT NULL,  -- VND
    original_price  INTEGER NOT NULL,  -- VND, equal to price when there is no discount
    discount_pct    INTEGER NOT NULL,
    sold            INTEGER NOT NULL,
    rating          REAL,              -- 1 to 5, NULL = not rated yet
    review_count    INTEGER NOT NULL,
    image_url       TEXT,
    product_url     TEXT    NOT NULL
);
"""


def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create the tables if they do not exist yet."""
    conn = connect()
    conn.executescript(SCHEMA)
    conn.close()


def save_search(keyword, products):
    """Insert one search and its products. Returns the id of the new search."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = connect()
    cursor = conn.execute(
        "INSERT INTO searches (keyword, category, created_at) VALUES (?, ?, ?)",
        (keyword, products["category"].iloc[0], created_at),
    )
    search_id = cursor.lastrowid
    products.assign(search_id=search_id).to_sql("products", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()
    return search_id


def get_search(search_id):
    """One search as a dict, or None if it does not exist."""
    conn = connect()
    conn.row_factory = sqlite3.Row  # rows can be read like dicts: row["keyword"]
    row = conn.execute("SELECT * FROM searches WHERE id = ?", (search_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def load_products(search_id):
    """All products of one search as a DataFrame."""
    conn = connect()
    df = pd.read_sql_query("SELECT * FROM products WHERE search_id = ?", conn, params=(search_id,))
    conn.close()
    return df


def recent_searches(limit=6):
    """The latest searches, with a few numbers about their products."""
    conn = connect()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT s.id, s.keyword, s.category, s.created_at,
               COUNT(*)     AS products,
               MIN(p.price) AS min_price,
               MAX(p.price) AS max_price,
               SUM(p.sold)  AS sold
        FROM searches s
        JOIN products p ON p.search_id = s.id
        GROUP BY s.id
        ORDER BY s.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
