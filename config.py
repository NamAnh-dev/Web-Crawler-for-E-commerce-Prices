"""Project settings.

Every value can be overridden with an environment variable or a `.env` file
(see `.env.example`), so nothing secret ever needs to be written in the code.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --- Storage ---------------------------------------------------------------
DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "data" / "ecomcheck.db"))

# --- Crawler (be polite: few pages, a pause between requests) ---------------
MAX_PAGES = int(os.getenv("MAX_PAGES", 5))              # web search; Tiki returns 40 products per page
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", 1.0))  # seconds to wait between two requests
REQUEST_TIMEOUT = 15                                    # seconds before giving up on a request
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
)

# Daily batch collection (collect.py): more pages, slower
BATCH_PAGES = int(os.getenv("BATCH_PAGES", 20))
BATCH_DELAY = float(os.getenv("BATCH_DELAY", 3.0))      # seconds between two pages
BATCH_PAUSE = float(os.getenv("BATCH_PAUSE", 60))       # seconds between two keywords

# Re-use a search made in the last N minutes instead of crawling again.
CACHE_MINUTES = int(os.getenv("CACHE_MINUTES", 30))

# --- Web app ----------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
