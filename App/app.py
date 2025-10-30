import sys
import subprocess
import mysql.connector
from flask import Flask, Blueprint, request, render_template, jsonify

app = Flask(__name__)
bp = Blueprint("routes", __name__)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "111111111",
    "database": "ecommerce_db"
}


@bp.route("/dashboard", methods=["GET"])
def dashboard():
    keyword = request.args.get("keyword", "")
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT Source, 
            AVG(CAST(Price AS UNSIGNED)) AS avg_price, 
            AVG(CAST(Quantity_Sold AS UNSIGNED)) AS avg_sold,
            AVG(CAST(Rating AS UNSIGNED)) as avg_rating,
            COUNT(Source_ProductID) AS count_product
        FROM products
        WHERE ProductName LIKE %s
        GROUP BY Source;
    """, ('%' + keyword.replace(" ", "%") + '%',))
    summary_data = cursor.fetchall()

    cursor.execute("""
        SELECT ProductName, Price, Quantity_Sold, Source, URL_Image, URL_Product
        FROM products
        WHERE ProductName LIKE %s
        ORDER BY CAST(Quantity_Sold AS UNSIGNED) DESC
        LIMIT 5;
    """, ('%' + keyword.replace(" ", "%") + '%',))
    top_sold = cursor.fetchall()

    cursor.close()
    conn.close()

    best_deal = None
    if summary_data:
        max_price = max(d["avg_price"] for d in summary_data)
        max_sold = max(d["avg_sold"] for d in summary_data)
        max_rating = max(d["avg_rating"] for d in summary_data)

        w_price = 0.3
        w_sold = 0.4
        w_rating = 0.3

        for d in summary_data:
            norm_price = 1 - (d["avg_price"] / max_price)
            norm_sold = d["avg_sold"] / max_sold
            norm_rating = d["avg_rating"] / max_rating

            d["deal_score"] = round(w_price * float(norm_price) + w_sold * float(norm_sold) + w_rating * float(norm_rating), 4)

        best_source = max(summary_data, key=lambda x: x["deal_score"])

        target_price = float(best_source["avg_price"])
        min_range = target_price * 0.8
        max_range = target_price * 1.2


        best_deal = {
            "source": best_source["Source"], 
            "avg_price": round(best_source["avg_price"], 0),
            "avg_rating": round(best_source["avg_rating"], 2),
            "avg_sold": int(best_source["avg_sold"]),
            "deal_score": best_source["deal_score"]
        }

    if request.headers.get("Accept") == "application/json":
        return jsonify({
            "summary": summary_data,
            "top_sold": top_sold,
            "best_deal": best_deal
        })
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT ProductName, Price, Quantity_Sold, URL_Image, URL_Product, Source
        FROM products
        WHERE Source = %s
        AND ProductName LIKE %s
        AND CAST(Price AS UNSIGNED) BETWEEN %s AND %s
        ORDER BY CAST(Quantity_Sold AS UNSIGNED) DESC, CAST(Price AS UNSIGNED) ASC, CAST(Rating AS UNSIGNED) DESC
        LIMIT 1;
    """, (best_deal["source"], '%' + keyword.replace(" ", "%") + '%', min_range, max_range))

    best_price_products = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("dashboard.html", keyword=keyword, bestDeal=best_deal, summary=summary_data, topSold=top_sold, similarProducts=best_price_products)



@bp.route("/", methods=["GET", "POST"])
def home():
    products = []

    if request.method == "POST":
        keyword = request.form.get("keyword")
        CRAWLER_PATH = "D:\\Programming\\Project DS\\E-commerce floor price prediction\\Crawler\\Run_crawl.py"

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products")
        conn.commit()
        cursor.close()
        conn.close()

        subprocess.run(
            [sys.executable, CRAWLER_PATH, keyword],
            capture_output=True,
            text=True,
            cwd=r"D:\Programming\Project DS\E-commerce floor price prediction\Crawler",
        )

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.close()
        conn.close()

        page = 1
        per_page = 20
        total_products = len(products)
        paginated_products = products[:per_page]

        return render_template("index.html",
                            products=paginated_products,
                            keyword=keyword,
                            page=page,
                            per_page=per_page,
                            total_products=total_products)


    if any(param in request.args for param in ["min_price", "max_price", "min_sold", "source", "sort"]):
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.close()
        conn.close()

        keyword = request.args.get("keyword") or request.form.get("keyword") or ""

        min_price = request.args.get("min_price", type=float)
        max_price = request.args.get("max_price", type=float)
        min_sold = request.args.get("min_sold", type=int)
        source = request.args.get("source", "all")
        sort = request.args.get("sort", "none")

        filtered = []
        for p in products:
            price_ok = True
            sold_ok = True
            source_ok = True

            if min_price is not None and p["Price"] is not None:
                price_ok = int(p["Price"]) >= min_price
            if max_price is not None and p["Price"] is not None:
                price_ok = price_ok and int(p["Price"]) <= max_price
            if min_sold is not None and p["Quantity_Sold"] is not None:
                sold_ok = int(p["Quantity_Sold"]) >= min_sold
            if source != "all":
                source_ok = p["Source"] == source

            if price_ok and sold_ok and source_ok:
                filtered.append(p)

        if sort == "asc":
            filtered.sort(key=lambda x: int(x["Price"]) or 0)
        elif sort == "desc":
            filtered.sort(key=lambda x: int(x["Price"]) or 0, reverse=True)
            
        page = request.args.get("page", default=1, type=int)
        per_page = request.args.get("per_page", default=20, type=int)
        start = (page - 1) * per_page
        end = start + per_page

        total_products = len(filtered)
        paginated_products = filtered[start:end]

        return render_template("index.html", products=paginated_products, keyword=keyword, page=page, per_page=per_page, total_products=total_products)

    keyword = request.args.get("keyword")
    if keyword:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE ProductName LIKE %s", ('%' + keyword + '%',))
        products = cursor.fetchall()
        cursor.close()
        conn.close()

        page = request.args.get("page", default=1, type=int)
        per_page = request.args.get("per_page", default=20, type=int)
        start = (page - 1) * per_page
        end = start + per_page
        total_products = len(products)
        paginated_products = products[start:end]

        return render_template("index.html",
                            products=paginated_products,
                            keyword=keyword,
                            page=page,
                            per_page=per_page,
                            total_products=total_products)


    return render_template("home.html")



app.register_blueprint(bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
