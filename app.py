"""Bước 5 - Hiển thị: một web app Flask nhỏ, đặt trên 4 bước trước.

python app.py      rồi mở http://127.0.0.1:5000

Luồng chạy khi người dùng tìm kiếm:
    trang chủ (/) -> gửi form tới /search -> thu thập + làm sạch + lưu CSV
    -> chuyển hướng tới /result/<số> -> đọc CSV + phân tích -> hiện trang kết quả
"""

import os  # đọc biến môi trường (os.environ)

import requests  # chỉ dùng để bắt lỗi mạng của requests (requests.RequestException)
from flask import (
    Flask,  # lớp tạo ra web app
    abort,  # dừng và trả về một mã lỗi HTTP, vd abort(404)
    flash,  # lưu một thông báo để hiện ở trang tiếp theo
    redirect,  # bảo trình duyệt chuyển sang một địa chỉ khác
    render_template,  # ghép dữ liệu vào file HTML trong thư mục templates/
    request,  # thông tin yêu cầu người dùng gửi lên (vd dữ liệu form)
    send_file,  # gửi một file về trình duyệt (để tải xuống)
    url_for,  # tạo đường link từ tên hàm, vd url_for("index") -> "/"
)

# 4 bước của dự án
import scraper  # bước 1: thu thập
import storage  # bước 3: lưu / đọc CSV
from analysis import analyze, short_price  # bước 4: phân tích
from cleaning import clean_products, normalize_text  # bước 2: làm sạch

# Tạo web app. __name__ giúp Flask biết tìm thư mục templates/ và static/ ở đâu.
app = Flask(__name__)
# flash() lưu thông báo trong cookie, và Flask cần secret_key để "ký" cookie đó
# (chống người khác sửa cookie). Lấy từ biến môi trường SECRET_KEY nếu có,
# không có thì dùng "dev-only" (chỉ đủ cho lúc chạy thử trên máy mình).
app.secret_key = os.environ.get("SECRET_KEY", "dev-only")


# ---- Bộ lọc cho template ----
# Decorator @app.template_filter("number") đăng ký hàm bên dưới thành một bộ lọc
# tên "number". Trong file HTML viết {{ gia_tri | number }} là gọi hàm này.
@app.template_filter("number")
def format_number(value):
    """1234567 -> "1.234.567" (Việt Nam dùng dấu chấm để ngăn cách hàng nghìn)."""
    # ":,.0f" = thêm dấu phẩy ngăn hàng nghìn, không lấy số lẻ -> "1,234,567"
    # rồi đổi dấu phẩy thành dấu chấm -> "1.234.567"
    return f"{value:,.0f}".replace(",", ".")


@app.template_filter("vnd")
def format_vnd(value):
    """Số tiền có đơn vị: 305000 -> "305.000 ₫" (dùng {{ gia | vnd }} trong HTML)."""
    return format_number(value) + " ₫"


# Cách đăng ký bộ lọc thứ hai (không dùng decorator), vì short_price được viết
# trong analysis.py: {{ gia | short_price }} -> "85K", "1.5Tr"
app.add_template_filter(short_price, "short_price")


# ---- Các trang (route) ----
# @app.route("/") nghĩa là: khi trình duyệt mở địa chỉ "/" (trang chủ),
# Flask gọi hàm index() và gửi về trình duyệt những gì hàm trả về.
@app.route("/")
def index():
    """Trang chủ: ô tìm kiếm + lịch sử các lượt tìm gần đây."""
    # render_template ghép dữ liệu vào templates/index.html.
    # searches=... tạo biến `searches` dùng được bên trong file HTML.
    return render_template("index.html", searches=storage.recent_searches())


# methods=["POST"]: trang này chỉ nhận dữ liệu gửi từ form (nút "Tìm kiếm").
# Gõ thẳng địa chỉ /search trên trình duyệt là kiểu GET -> Flask trả lỗi 405.
@app.route("/search", methods=["POST"])
def search():
    """Thu thập -> làm sạch -> lưu, rồi chuyển sang trang kết quả."""
    # request.form chứa dữ liệu của form; "keyword" là name của ô nhập trong HTML.
    # .get(..., ""): không có thì lấy chuỗi rỗng; .strip(): bỏ khoảng trắng hai đầu.
    keyword = request.form.get("keyword", "").strip()
    if len(keyword) < 2:  # từ khóa quá ngắn -> báo lỗi rồi quay lại trang chủ
        flash("Hãy nhập tên sản phẩm (ít nhất 2 ký tự).")
        return redirect(url_for("index"))

    # try / except: thử chạy, nếu gặp lỗi thì không làm sập app mà xử lý nhẹ nhàng
    try:
        raw = scraper.crawl(keyword)  # bước 1: tải sản phẩm từ Tiki
    # RequestException: lỗi mạng (mất internet, quá thời gian chờ, lỗi HTTP...).
    # RuntimeError: lỗi do get_api_page() tự báo khi Tiki bận cả 3 lần.
    except (requests.RequestException, RuntimeError) as error:
        flash(f"Không lấy được dữ liệu từ Tiki: {error}")  # hiện lỗi cho người dùng
        return redirect(url_for("index"))

    products = clean_products(raw, keyword)  # bước 2: làm sạch
    if products.empty:  # làm sạch xong không còn sản phẩm nào phù hợp
        flash(f"Không tìm thấy sản phẩm phù hợp với “{keyword}”. Hãy thử từ khóa khác.")
        return redirect(url_for("index"))

    search_id = storage.save_search(keyword, products)  # bước 3: lưu CSV, nhận số thứ tự
    # Chuyển hướng (redirect) sang /result/<số> thay vì hiện kết quả ngay tại đây:
    # nhờ vậy khi người dùng bấm F5 (tải lại), trình duyệt chỉ mở lại trang kết quả
    # chứ không gửi lại form và tải lại Tiki thêm một lần nữa.
    return redirect(url_for("result", search_id=search_id))


# <int:search_id>: phần này của địa chỉ là một số nguyên, Flask lấy ra và truyền
# vào hàm. Ví dụ /result/3 -> result(search_id=3). Không phải số -> lỗi 404.
@app.route("/result/<int:search_id>")
def result(search_id):
    """Trang kết quả của một lượt tìm kiếm đã lưu."""
    products = storage.load_search(search_id)  # đọc file CSV
    if products is None:  # không có file -> trang "không tìm thấy"
        abort(404)
    return render_template(
        "result.html",
        search=storage.search_info(search_id, products),  # thông tin đầu trang
        report=analyze(products),  # bước 4: mọi con số và bảng của trang
    )


@app.route("/result/<int:search_id>/csv")
def download_csv(search_id):
    """Tải file CSV của một lượt tìm kiếm về máy."""
    products = storage.load_search(search_id)
    if products is None:
        abort(404)
    # Tên file tải về lấy từ từ khóa: "chuột gaming" -> "chuot_gaming"
    keyword = normalize_text(products["keyword"].iloc[0]).replace(" ", "_")
    return send_file(
        storage.search_path(search_id),  # file nào trên máy chủ
        mimetype="text/csv",  # báo cho trình duyệt đây là file CSV
        as_attachment=True,  # tải xuống, thay vì mở ngay trong trình duyệt
        download_name=f"tiki_{keyword}_{search_id}.csv",  # tên file người dùng nhận được
    )


# Mỗi khi có lỗi 404 (gọi abort(404) hoặc mở địa chỉ không tồn tại),
# Flask gọi hàm này để hiện trang 404 riêng của dự án thay cho trang mặc định.
@app.errorhandler(404)
def not_found(error):
    """Trang "không tìm thấy". Trả về 2 giá trị: nội dung HTML và mã lỗi 404."""
    return render_template("404.html"), 404


# Chỉ chạy server khi gõ "python app.py" (không chạy khi file test import app)
if __name__ == "__main__":
    app.run()  # mặc định chạy ở http://127.0.0.1:5000
