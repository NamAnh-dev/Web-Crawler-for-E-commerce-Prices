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
from analysis import categories
from analysis.cleaning import COLUMNS, UNKNOWN_CATEGORY, clean_products
from analysis.pricing import add_analysis_columns
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
    Returns a summary for the user.
    """
    run = db.get_run(run_id)
    frames, keywords = [], set()
    for filename, data in files:
        raw, found = browser_import.read_file(filename, data)
        frames.append(raw)
        keywords |= found
    raw = pd.concat(frames, ignore_index=True)
    imported = clean_products(raw, run["keyword"])
    summary = {"found": len(raw), "kept": len(imported), "keywords": sorted(keywords),
               "per_source": imported["source"].value_counts().to_dict(), "accuracy": None}
    if imported.empty:
        return summary

    # Lazada and Shopee send no category name: learn it from Tiki's products
    current = db.load_products(run_id)
    labelled = current[(current["category_predicted"] == 0) & (current["category"] != UNKNOWN_CATEGORY)]
    model, summary["accuracy"] = categories.train(labelled)
    if model is not None:
        imported["category"] = categories.predict(model, imported["name"])
    elif labelled["category"].nunique() == 1:  # only one category: nothing to choose
        imported["category"] = labelled["category"].iloc[0]
    imported["category_predicted"] = 1
    summary["unknown"] = int((imported["category"] == UNKNOWN_CATEGORY).sum())

    # merge, then recompute flags and scores: products are now compared across sources
    combined = pd.concat([current[COLUMNS + ["category_predicted"]], imported], ignore_index=True)
    combined = combined.drop_duplicates(subset=["source", "product_id"], keep="last")
    db.replace_products(run_id, add_analysis_columns(combined), notes=run["notes"])
    return summary


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # show Vietnamese correctly in the Windows console
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Collect one keyword from Tiki.")
    parser.add_argument("keyword", nargs="+")
    parser.add_argument("--pages", type=int, default=config.MAX_PAGES, help="pages of 40 products")
    args = parser.parse_args()
    run_pipeline(" ".join(args.keyword), args.pages)
