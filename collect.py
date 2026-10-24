"""Collect many keywords from Tiki in one go: more pages than the web app, slower.

Usage:
    python collect.py                          # keywords from keywords.txt
    python collect.py "bàn phím cơ" --pages 40

Every run is saved as a new snapshot. Run it once a day (schedule_daily.ps1)
and the history page shows how prices and sales change over time.
A log is written to logs/collect.log.
"""
import argparse
import logging
import sys
import time

import config
from run_crawl import run_pipeline

KEYWORDS_FILE = config.BASE_DIR / "keywords.txt"
LOG_FILE = config.BASE_DIR / "logs" / "collect.log"


def read_keywords(path):
    """One keyword per line; empty lines and lines starting with # are skipped."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def setup_logging():
    LOG_FILE.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )


def main():
    parser = argparse.ArgumentParser(description="Collect several keywords from Tiki.")
    parser.add_argument("keywords", nargs="*", help="default: the keywords in keywords.txt")
    parser.add_argument("--pages", type=int, default=config.BATCH_PAGES, help="pages of 40 products per keyword")
    parser.add_argument("--delay", type=float, default=config.BATCH_DELAY, help="seconds between two pages")
    parser.add_argument("--pause", type=float, default=config.BATCH_PAUSE, help="seconds between two keywords")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    setup_logging()
    config.REQUEST_DELAY = args.delay
    keywords = args.keywords or read_keywords(KEYWORDS_FILE)
    logging.info("Start: %d keywords, up to %d pages each", len(keywords), args.pages)

    saved = 0
    for i, keyword in enumerate(keywords):
        if i > 0:
            time.sleep(args.pause)  # be polite between two keywords
        try:
            if run_pipeline(keyword, max_pages=args.pages) is not None:
                saved += 1
        except Exception as error:  # one failing keyword must not stop the others
            logging.error("[Tiki] %s: %s", keyword, error)

    logging.info("Done: %d of %d keywords saved", saved, len(keywords))


if __name__ == "__main__":
    main()
