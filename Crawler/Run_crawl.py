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


