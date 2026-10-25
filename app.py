"""Step 5 - Show: a small Flask web app on top of the four steps.

    python app.py      then open http://127.0.0.1:5000
"""
import os

import requests
from flask import Flask, Response, abort, flash, redirect, render_template, request, url_for

import database
import scraper
from analysis import analyze, short_price
from cleaning import clean_products, normalize_text

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only")  # needed by flash() messages
database.init_db()


@app.template_filter("number")
def format_number(value):
    """1234567 -> "1.234.567" (Vietnam uses dots between thousands)."""
    return f"{value:,.0f}".replace(",", ".")


@app.template_filter("vnd")
def format_vnd(value):
    return format_number(value) + " ₫"


app.add_template_filter(short_price, "short_price")


@app.route("/")
def index():
    return render_template("index.html", searches=database.recent_searches())


@app.route("/search", methods=["POST"])
def search():
    """Collect -> clean -> save, then show the result page."""
    keyword = request.form.get("keyword", "").strip()
    if len(keyword) < 2:
        flash("Hãy nhập tên sản phẩm (ít nhất 2 ký tự).")
        return redirect(url_for("index"))

    try:
        raw = scraper.crawl(keyword)
    except (requests.RequestException, RuntimeError) as error:  # no internet, Tiki busy...
        flash(f"Không lấy được dữ liệu từ Tiki: {error}")
        return redirect(url_for("index"))

    products = clean_products(raw, keyword)
    if products.empty:
        flash(f"Không tìm thấy sản phẩm phù hợp với “{keyword}”. Hãy thử từ khóa khác.")
        return redirect(url_for("index"))

    search_id = database.save_search(keyword, products)
    return redirect(url_for("result", search_id=search_id))


@app.route("/result/<int:search_id>")
def result(search_id):
    search = database.get_search(search_id)
    if search is None:
        abort(404)
    report = analyze(database.load_products(search_id))
    return render_template("result.html", search=search, report=report)


@app.route("/result/<int:search_id>/csv")
def download_csv(search_id):
    search = database.get_search(search_id)
    if search is None:
        abort(404)
    products = database.load_products(search_id).drop(columns="search_id")
    filename = f"tiki_{normalize_text(search['keyword']).replace(' ', '_')}_{search_id}.csv"
    return Response(
        products.to_csv(index=False).encode("utf-8-sig"),  # utf-8-sig: Excel shows Vietnamese correctly
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run()
