# import os
# import sys
# import argparse
# import logging
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from typing import Callable

# from Lazada import Lazada_crawler
# from Tiki import Tiki_crawler

# if hasattr(sys.stdout, "reconfigure"):
#     sys.stdout.reconfigure(encoding="utf-8")

# logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


# def run_crawler(func: Callable[[str], None], keyword: str) -> bool:
#     try:
#         func(keyword)
#         logging.info("%s finished for keyword=%s", func.__name__, keyword)
#         return True
#     except Exception:
#         logging.exception("Error running %s for keyword=%s", func.__name__, keyword)
#         return False


# def parse_args() -> str:
#     parser = argparse.ArgumentParser(description="Run crawlers for a keyword")
#     parser.add_argument("keyword", nargs="?", default=os.environ.get("keyword"), help="Search keyword (or set env var 'keyword')")
#     args = parser.parse_args()
#     if not args.keyword:
#         parser.error("keyword is required (positional or environment variable 'keyword')")
#     return args.keyword


# def main() -> None:
#     keyword = parse_args()
#     logging.info("Starting crawlers for keyword=%s", keyword)

#     crawlers = [Lazada_crawler, Tiki_crawler]
#     results = []

#     # Run in parallel threads; change to ProcessPoolExecutor if CPU-bound
#     with ThreadPoolExecutor(max_workers=len(crawlers)) as ex:
#         futures = {ex.submit(run_crawler, c, keyword): c for c in crawlers}
#         for fut in as_completed(futures):
#             results.append(fut.result())

#     if all(results):
#         logging.info("All crawlers finished successfully.")
#         sys.exit(0)
#     else:
#         logging.warning("Some crawlers failed.")
#         sys.exit(1)


# if __name__ == "__main__":
#     main()

import os
import sys
from Lazada import Lazada_crawler
from Tiki import Tiki_crawler
sys.stdout.reconfigure(encoding='utf-8')

def main():
    if len(sys.argv) < 2:
        keyword = os.environ.get("keyword")
        if not keyword:
            print("Insert keyword: ")
            return
    else:
        keyword = sys.argv[1]
    print(f"RELOADING DATA: {keyword}")

    try:
        Lazada_crawler(keyword)
    except Exception as e:
        print(f"ERROR crawling Lazada: {e}")
    try:
        Tiki_crawler(keyword)
    except Exception as e:
        print(f"ERROR crawling Tiki: {e}")

    print("Finished crawling.")

if __name__ == "__main__":
    main()


