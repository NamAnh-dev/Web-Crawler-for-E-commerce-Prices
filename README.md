# E-commerce Price Comparison: Tiki & Lazada

A small end-to-end data project: crawl product listings from **Tiki** and **Lazada** by keyword, clean and store them in **MySQL**, then explore and compare prices through a **Flask** web app with a dashboard.

<!-- Add 2-3 screenshots here, e.g. docs/screenshots/home.png, results.png, dashboard.png -->

## What it does

1. **Search** a product keyword (e.g. `chuột gaming`) on the web UI.
2. **Crawl** Tiki (product search API, up to 10 pages) and Lazada (catalog endpoint, up to 7 pages).
3. **Clean** the data with pandas:
   - drop rows without product/image URL and remove duplicate product IDs,
   - parse Lazada sold counts written as text (`"1.2k"`, `"3m"`) into numbers,
   - keep only products whose name contains all search words (accent- and punctuation-insensitive, so `chuot gaming` matches `Chuột Gaming`).
4. **Store** results in MySQL (`products` table).
5. **Explore** in the browser:
   - Results page with filters (price range, minimum sold, source), sorting by price, and pagination.
   - Dashboard with per-source summary (average price, total/average sold, average rating, product count), top 5 best-selling products, and Chart.js charts.
   - A simple **"best deal" score** per source: `0.3 × (1 − normalized avg price) + 0.4 × normalized avg sold + 0.3 × normalized avg rating`, which then suggests a representative product in that source's typical price range (±20%).

## Project structure

```
Crawler/    Tiki.py, Lazada.py (fetch + clean), Run_crawl.py (CLI entry), utils.py (DB + text helpers),
            headers.py (request headers), Get_Data_*.ipynb (exploration notebooks, incl. Shopee)
DB/         DB.sql (schema: products, price_history)
App/        app.py (Flask routes) + templates/ (home, index, dashboard)
```

## Tech stack

Python · requests · pandas · MySQL (`mysql-connector-python`) · Flask · Chart.js · HTML/CSS

## Getting started

**Prerequisites:** Python 3.9+, MySQL server.

```bash
git clone https://github.com/NamAnh-dev/Web-Crawler-for-E-commerce-Prices.git
cd Web-Crawler-for-E-commerce-Prices
pip install -r requirements.txt
```

1. **Create the database:** run `DB/DB.sql` in MySQL (creates `ecommerce_db` with the `products` and `price_history` tables).
2. **Configure credentials:** set your MySQL user/password in `Crawler/utils.py` and `App/app.py`.
3. **Set request headers:** in `Crawler/headers.py`, put your own `User-Agent`/`cookie` values copied from your browser DevTools (Network tab). Never commit real cookies or tokens.
4. **Set the crawler path:** in `App/app.py`, update `CRAWLER_PATH` and `cwd` so they point to your local `Crawler/` folder.

**Run the crawler from the command line:**

```bash
cd Crawler
python Run_crawl.py "chuột gaming"
```

**Run the web app:**

```bash
cd App
python app.py
# open http://localhost:5000
```

Type a keyword on the home page; the app runs the crawler, then shows the results. Open `/dashboard?keyword=...` for the comparison dashboard.

## Database schema

| Table             | Columns                                                                                                                                             |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `products`      | ID, Source_ProductID, ProductName, Price, Original_Price, Discount, Quantity_Sold, Rating, Review_Count, URL_Image, URL_Product, Source, Created_at |
| `price_history` | ID, ProductID (FK → products), Fetched_at                                                                                                          |

## limitations

- Each new search **clears the `products` table**, so the app holds one search at a time and is not multi-user.
- `price_history` exists in the schema but is not populated yet, so there is no price-over-time analysis.
- Price, sold count and rating are stored as `VARCHAR` and cast in SQL queries; proper numeric types would be cleaner and faster.
- The crawlers rely on unofficial endpoints with browser headers/cookies, and have no retry or rate limiting yet.
- Shopee was explored in a notebook (`Get_Data_Shoppe.ipynb`) but is not part of the pipeline.
