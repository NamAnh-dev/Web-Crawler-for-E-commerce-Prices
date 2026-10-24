"""ETL pipeline for one keyword:  crawl -> clean -> analyse -> save.

Usage:
    python run_crawl.py "chuột gaming"

The web app calls `run_pipeline()` too, so both give exactly the same result.
"""
import sys

import pandas as pd

import config
from analysis.cleaning import COLUMNS, clean_products
from analysis.pricing import add_analysis_columns
from crawler import lazada, tiki
from database import db


def available_sources():
    """Tiki always works; Lazada only when a browser cookie is configured."""
    sources = {"Tiki": tiki.crawl}
    if config.LAZADA_COOKIE:
        sources["Lazada"] = lazada.crawl
    return sources


def run_pipeline(keyword):
    """Crawl every source and store the result as one search run.

    Returns the new run id, or None when no product was found.
    """
    db.init_db()
    frames, problems = [], []

    for name, crawl in available_sources().items():
        try:
            raw = crawl(keyword)                         # Extract
            clean = clean_products(raw, keyword)         # Transform
            print(f"[{name}] {len(raw)} raw rows -> {len(clean)} clean rows")
            frames.append(clean)
        except Exception as error:  # one broken source must not stop the others
            print(f"[{name}] skipped: {error}")
            problems.append(f"{name}: {error}")

    products = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    if products.empty:
        print("No products found.")
        return None

    products = add_analysis_columns(products)            # Analyse
    run_id = db.save_run(keyword, products, notes="; ".join(problems) or None)  # Load
    print(f"Saved run #{run_id} with {len(products)} products to {config.DB_PATH}")
    return run_id


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # show Vietnamese correctly in the Windows console
    if len(sys.argv) < 2:
        print('Usage: python run_crawl.py "chuột gaming"')
        sys.exit(1)
    run_pipeline(" ".join(sys.argv[1:]))
