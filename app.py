"""EcomCheck web app (Flask).

Run:
    python app.py
then open http://127.0.0.1:5000
"""
import math
from datetime import datetime

from flask import Flask, Response, abort, flash, redirect, render_template, request, url_for

import config
from analysis.cleaning import normalize_text
from analysis.history import build_history, main_category
from analysis.pricing import build_dashboard
from database import db
from run_crawl import import_files, run_pipeline

PER_PAGE = 20

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024  # HAR files can be large
db.init_db()


# --- Number formats used in Vietnam (1.234.567 ₫, 4,8) ---------------------------

def is_missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


@app.template_filter("number")
def format_number(value, decimals=0):
    if is_missing(value):
        return "–"
    text = f"{value:,.{decimals}f}"                       # 1,234.5
    return text.replace(",", " ").replace(".", ",").replace(" ", ".")  # 1.234,5


@app.template_filter("vnd")
def format_vnd(value):
    return "–" if is_missing(value) else f"{format_number(value)} ₫"


@app.template_filter("compact_vnd")
def format_compact_vnd(value):
    """Short price for tight spaces: 85K, 1,5Tr."""
    if is_missing(value):
        return "–"
    if value >= 1_000_000:
        return f"{format_number(value / 1_000_000, 1).removesuffix(',0')}Tr"
    return f"{format_number(value / 1_000)}K"


@app.template_filter("datetime_vn")
def format_datetime(value):
    moment = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return moment.strftime("%H:%M · %d/%m/%Y")


@app.template_global()
def url_with(**changes):
    """The current URL with some query parameters changed (used by pagination)."""
    args = request.args.to_dict()
    args.update(changes)
    return url_for(request.endpoint, **request.view_args, **args)


def run_context(run):
    """What the shared header of every run page needs."""
    return {"run": run, "sources": db.run_sources(run["id"]), "snapshots": db.count_runs(run["keyword"])}


def get_run_or_404(run_id):
    run = db.get_run(run_id)
    if run is None:
        abort(404)
    return run


# --- Pages -----------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("home.html", runs=db.recent_runs())


@app.route("/search", methods=["POST"])
def search():
    keyword = " ".join(request.form.get("keyword", "").split())  # trim extra spaces
    if len(keyword) < 2:
        flash("Hãy nhập tên sản phẩm (ít nhất 2 ký tự).")
        return redirect(url_for("home"))

    # Re-use a fresh search for the same keyword instead of crawling again.
    recent = db.find_recent_run(keyword, config.CACHE_MINUTES)
    try:
        run_id = recent["id"] if recent else run_pipeline(keyword)
    except Exception as error:  # network problem or rate limit
        flash(f"Không lấy được dữ liệu từ Tiki: {error}")
        return redirect(url_for("home"))

    if run_id is None:
        flash(f"Không tìm thấy sản phẩm phù hợp với “{keyword}”. Hãy thử từ khóa khác.")
        return redirect(url_for("home"))
    return redirect(url_for("products", run_id=run_id))


@app.route("/run/<int:run_id>")
def products(run_id):
    run = get_run_or_404(run_id)
    categories = db.run_categories(run_id)
    filters = {
        "q": request.args.get("q", "").strip(),
        # biggest category by default (same as the dashboard); "" = all categories
        "category": request.args.get("category", categories[0]["category"]),
        "source": request.args.get("source", ""),
        "min_price": request.args.get("min_price", type=int),
        "max_price": request.args.get("max_price", type=int),
        "min_sold": request.args.get("min_sold", type=int),
        "min_rating": request.args.get("min_rating", type=float),
        "sort": request.args.get("sort", "deal"),
    }
    page = max(request.args.get("page", 1, type=int), 1)
    rows, total = db.search_products(run_id, **filters, page=page, per_page=PER_PAGE)

    return render_template(
        "results.html",
        **run_context(run),
        products=rows,
        total=total,
        page=page,
        pages=max(math.ceil(total / PER_PAGE), 1),
        filters=filters,
        categories=categories,
    )


@app.route("/run/<int:run_id>/dashboard")
def dashboard(run_id):
    run = get_run_or_404(run_id)
    categories = db.run_categories(run_id)
    # Analyse one category at a time (the biggest one by default), so that
    # e.g. mouse pads do not pull down the price of gaming mice.
    category = request.args.get("category") or categories[0]["category"]

    df = db.load_products(run_id)
    if category != "all":
        df = df[df["category"] == category]
    if df.empty:
        abort(404)

    return render_template("dashboard.html", **run_context(run), data=build_dashboard(df),
                           categories=categories, category=category)


@app.route("/run/<int:run_id>/import", methods=["GET", "POST"])
def import_data(run_id):
    """Add Lazada/Shopee results that the user saved from their own browser."""
    run = get_run_or_404(run_id)
    if request.method == "GET":
        return render_template("import.html", **run_context(run))

    files = [(f.filename, f.read()) for f in request.files.getlist("files") if f.filename]
    if not files:
        flash("Hãy chọn ít nhất một file.")
        return redirect(url_for("import_data", run_id=run_id))
    try:
        summary = import_files(run_id, files)
    except ValueError:
        flash("Không đọc được file. Hãy dùng file .har xuất từ DevTools, hoặc file .json/.html đã lưu.")
        return redirect(url_for("import_data", run_id=run_id))

    if summary["found"] == 0:
        flash("Không có kết quả tìm kiếm Lazada hoặc Shopee nào trong file. "
              "Hãy mở DevTools trước khi tìm kiếm rồi xuất lại file HAR.")
        return redirect(url_for("import_data", run_id=run_id))

    added = ", ".join(f"{source} {count}" for source, count in summary["per_source"].items())
    flash(f"Đã đọc {summary['found']} sản phẩm, giữ {summary['kept']} sản phẩm liên quan ({added or 'không có'}).")
    if summary["accuracy"] is not None:
        flash(f"Danh mục được dự đoán từ tên sản phẩm (độ chính xác khi kiểm tra trên Tiki: "
              f"{summary['accuracy'] * 100:.0f}%); {summary['unknown']} sản phẩm chưa phân loại được.")
    other = [k for k in summary["keywords"] if normalize_text(k) != normalize_text(run["keyword"])]
    if other:
        flash(f"Lưu ý: file chứa kết quả của từ khóa khác ({', '.join(other)}); "
              f"chỉ sản phẩm liên quan đến “{run['keyword']}” được giữ lại.")
    return redirect(url_for("products", run_id=run_id))


@app.route("/history")
def history():
    keyword = request.args.get("keyword", "")
    data = db.load_history(keyword)
    data = data[data["source"] == "Tiki"]
    if data.empty:
        abort(404)
    category = request.args.get("category") or main_category(data)
    if not (data["category"] == category).any():
        abort(404)
    latest_run = db.get_run(int(data["run_id"].max()))
    categories = data[data["run_id"] == latest_run["id"]]["category"].value_counts()

    return render_template("history.html", **run_context(latest_run), category=category,
                           categories=categories[categories >= 3].index.tolist(),
                           history=build_history(data, category))


@app.route("/run/<int:run_id>/export.csv")
def export_csv(run_id):
    run = get_run_or_404(run_id)
    df = db.load_products(run_id).drop(columns=["id", "run_id"])
    filename = f"ecomcheck_{normalize_text(run['keyword']).replace(' ', '-')}_{run_id}.csv"
    return Response(
        df.to_csv(index=False).encode("utf-8-sig"),  # BOM so Excel shows Vietnamese correctly
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(413)
def file_too_large(error):
    flash("File quá lớn (tối đa 300 MB). Khi xuất HAR, hãy lọc tab Network theo Fetch/XHR và Doc.")
    return redirect(request.referrer or url_for("home"))


if __name__ == "__main__":
    app.run(debug=config.DEBUG)
