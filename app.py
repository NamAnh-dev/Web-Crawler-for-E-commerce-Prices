"""Step 5 - Show: a small Flask web app on top of the four steps.

python app.py      then open http://127.0.0.1:5000
"""

import os

import requests
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

import scraper
import storage
from analysis import analyze, short_price
from cleaning import clean_products, normalize_text

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only")  # needed by flash() messages


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
    return render_template("index.html", searches=storage.recent_searches())


@app.route("/search", methods=["POST"])
def search():
    """Collect -> clean -> save, then show the result page."""
    keyword = request.form.get("keyword", "").strip()
    if len(keyword) < 2:
        flash("Hãy nhập tên sản phẩm (ít nhất 2 ký tự).")
        return redirect(url_for("index"))

    try:
        raw = scraper.crawl(keyword)
    except (requests.RequestException, RuntimeError) as error:  # no internet, Tiki busy
        flash(f"Không lấy được dữ liệu từ Tiki: {error}")
        return redirect(url_for("index"))

    products = clean_products(raw, keyword)
    if products.empty:
        flash(f"Không tìm thấy sản phẩm phù hợp với “{keyword}”. Hãy thử từ khóa khác.")
        return redirect(url_for("index"))

    search_id = storage.save_search(keyword, products)
    return redirect(url_for("result", search_id=search_id))


@app.route("/result/<int:search_id>")
def result(search_id):
    products = storage.load_search(search_id)
    if products is None:
        abort(404)
    return render_template(
        "result.html",
        search=storage.search_info(search_id, products),
        report=analyze(products),
    )


@app.route("/result/<int:search_id>/csv")
def download_csv(search_id):
    products = storage.load_search(search_id)
    if products is None:
        abort(404)
    keyword = normalize_text(products["keyword"].iloc[0]).replace(" ", "_")
    return send_file(
        storage.search_path(search_id),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"tiki_{keyword}_{search_id}.csv",
    )


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run()
