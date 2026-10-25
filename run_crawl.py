"""ETL pipeline for one keyword:  crawl -> clean -> analyse -> save.

Usage:
    python run_crawl.py "chuột gaming"
    python run_crawl.py "chuột gaming" --pages 20

The web app and collect.py call the same functions, so all give the same result.
"""
import argparse
import logging
import sys

import pandas as pd

import config
from analysis.cleaning import COLUMNS, clean_products
from analysis.pricing import add_analysis_columns, main_category
from crawler import browser_import, tiki
from database import db

log = logging.getLogger("ecomcheck")


def run_pipeline(keyword, max_pages=None):
    """Crawl Tiki and store the result as one search run (a snapshot).

    Returns the new run id, or None when no product was found.
    Network problems raise an exception with a readable message.
    """
    db.init_db()
    raw = tiki.crawl(keyword, max_pages)                 # Extract
    products = clean_products(raw, keyword)              # Transform
    log.info("[Tiki] %s: %d raw rows -> %d clean rows", keyword, len(raw), len(products))
    if products.empty:
        return None

    products = add_analysis_columns(products)            # Analyse
    run_id = db.save_run(keyword, products)              # Load
    log.info("Saved run #%d with %d products", run_id, len(products))
    return run_id


def import_files(run_id, files):
    """Add Lazada/Shopee products saved from the browser to an existing run.

    files: list of (filename, file content as bytes).
    Returns the number of products added per marketplace, e.g. {"Shopee": 120}.
    """
    run = db.get_run(run_id)
    raw = pd.concat([browser_import.read_file(name, data) for name, data in files], ignore_index=True)
    imported = clean_products(raw, run["keyword"])  # keeps names that contain the keyword
    if imported.empty:
        return {}

    # Lazada and Shopee send no category name, so their products go into the
    # main category of this search (the one the dashboard shows by default).
    current = db.load_products(run_id)
    imported["category"] = main_category(current)

    # merge, then recompute flags and scores: products are now compared across marketplaces
    combined = pd.concat([current[COLUMNS], imported], ignore_index=True)
    combined = combined.drop_duplicates(subset=["source", "product_id"], keep="last")
    db.replace_products(run_id, add_analysis_columns(combined))
    return imported["source"].value_counts().to_dict()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # show Vietnamese correctly in the Windows console
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)  # default is stderr
    parser = argparse.ArgumentParser(description="Collect one keyword from Tiki.")
    parser.add_argument("keyword", nargs="+")
    parser.add_argument("--pages", type=int, default=config.MAX_PAGES, help="pages of 40 products")
    args = parser.parse_args()
    run_pipeline(" ".join(args.keyword), args.pages)
