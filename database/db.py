"""Load + query: every function that talks to the SQLite database."""
import sqlite3
from pathlib import Path

import pandas as pd

import config
from analysis.cleaning import normalize_text

SCHEMA_FILE = Path(__file__).with_name("schema.sql")

# Sort options shown on the results page. Only these fixed strings are ever
# put into the SQL text, so user input cannot change the query.
SORT_OPTIONS = {
    "deal": "deal_score IS NULL, deal_score DESC",
    "price_asc": "price ASC",
    "price_desc": "price DESC",
    "sold": "sold DESC",
    "rating": "rating IS NULL, rating DESC, review_count DESC",
    "discount": "discount_pct DESC, price ASC",
}


def get_connection():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row                         # rows work like dicts: row["price"]
    conn.execute("PRAGMA foreign_keys = ON")
    conn.create_function("normalize", 1, normalize_text)   # accent-insensitive search in SQL
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
    conn.close()


def save_run(keyword, products, notes=None):
    """Insert one search run and all its products. Returns the new run id."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO search_runs (keyword, product_count, notes) VALUES (?, ?, ?)",
            (keyword, len(products), notes),
        )
        run_id = cursor.lastrowid
        products.assign(run_id=run_id).to_sql("products", conn, if_exists="append", index=False)
        conn.commit()
        return run_id
    finally:
        conn.close()


def replace_products(run_id, products):
    """Replace all products of a run (used after importing Lazada/Shopee data)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM products WHERE run_id = ?", (run_id,))
        products.assign(run_id=run_id).to_sql("products", conn, if_exists="append", index=False)
        conn.execute("UPDATE search_runs SET product_count = ? WHERE id = ?", (len(products), run_id))
        conn.commit()
    finally:
        conn.close()


def fetch_all(sql, params=()):
    conn = get_connection()
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def get_run(run_id):
    rows = fetch_all("SELECT * FROM search_runs WHERE id = ?", (run_id,))
    return rows[0] if rows else None


def totals():
    """Numbers shown on the home page."""
    return fetch_all(
        """
        SELECT COUNT(*) AS runs,
               COALESCE(SUM(product_count), 0) AS products,
               COUNT(DISTINCT keyword) AS keywords
        FROM search_runs
        WHERE product_count > 0
        """
    )[0]


def recent_runs(limit=8):
    return fetch_all(
        "SELECT * FROM search_runs WHERE product_count > 0 ORDER BY id DESC LIMIT ?", (limit,)
    )


def find_recent_run(keyword, minutes):
    """A run for the same keyword made in the last `minutes` minutes, if any."""
    rows = fetch_all(
        """
        SELECT * FROM search_runs
        WHERE normalize(keyword) = ?
          AND product_count > 0
          AND created_at >= datetime('now', 'localtime', ?)
        ORDER BY id DESC LIMIT 1
        """,
        (normalize_text(keyword), f"-{minutes} minutes"),
    )
    return rows[0] if rows else None


def load_products(run_id):
    """All products of a run as a DataFrame (used by the dashboard and CSV export)."""
    conn = get_connection()
    try:
        return pd.read_sql_query(
            "SELECT * FROM products WHERE run_id = ? ORDER BY id", conn, params=(run_id,)
        )
    finally:
        conn.close()


def count_runs(keyword):
    """How many snapshots exist for a keyword (accent-insensitive)."""
    rows = fetch_all("SELECT COUNT(*) AS n FROM search_runs WHERE normalize(keyword) = ?",
                     (normalize_text(keyword),))
    return rows[0]["n"]


def load_history(keyword):
    """Products of every snapshot of a keyword, with the time of each snapshot."""
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT p.*, r.created_at
            FROM products p
            JOIN search_runs r ON r.id = p.run_id
            WHERE normalize(r.keyword) = ?
            ORDER BY r.id, p.id
            """,
            conn,
            params=(normalize_text(keyword),),
        )
    finally:
        conn.close()


def run_sources(run_id):
    rows = fetch_all(
        """
        SELECT DISTINCT source FROM products WHERE run_id = ?
        ORDER BY source != 'Tiki', source
        """,
        (run_id,),
    )
    return [row["source"] for row in rows]


def run_categories(run_id):
    """Categories of a run with their product count, biggest first."""
    return fetch_all(
        """
        SELECT category, COUNT(*) AS products
        FROM products
        WHERE run_id = ?
        GROUP BY category
        ORDER BY products DESC, category
        """,
        (run_id,),
    )


def search_products(run_id, q="", min_price=None, max_price=None, min_sold=None,
                    min_rating=None, source="", category="", sort="deal", page=1, per_page=20):
    """Filter, sort and paginate the products of one run. Returns (rows, total)."""
    filters = [
        ("normalize(name) LIKE ?", f"%{normalize_text(q)}%" if q else None),
        ("price >= ?", min_price),
        ("price <= ?", max_price),
        ("sold >= ?", min_sold),
        ("rating >= ?", min_rating),
        ("source = ?", source or None),
        ("category = ?", category or None),
    ]
    active = [(sql, value) for sql, value in filters if value is not None]
    where = " AND ".join(["run_id = ?"] + [sql for sql, _ in active])
    params = [run_id] + [value for _, value in active]
    order_by = SORT_OPTIONS.get(sort, SORT_OPTIONS["deal"])

    conn = get_connection()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM products WHERE {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM products WHERE {where} ORDER BY {order_by} LIMIT ? OFFSET ?",
            params + [per_page, (page - 1) * per_page],
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows], total
