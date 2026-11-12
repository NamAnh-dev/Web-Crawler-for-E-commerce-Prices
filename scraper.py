"""Bước 1 - Thu thập: tải về các sản phẩm mà Tiki liệt kê cho một từ khóa.

Tiki trả về cùng một danh sách sản phẩm theo hai cách, file này viết cả hai:

- get_api_page(): gọi API tìm kiếm dạng JSON, chính là API mà trang tìm kiếm
  tiki.vn tự gọi (tìm thấy trong Chrome DevTools > tab Network). Dữ liệu gọn,
  tải nhanh, nên web app dùng cách này.
- get_html_page(): tải chính trang tìm kiếm (HTML) rồi đọc bằng BeautifulSoup.
  Dùng trong notebook 01 để so sánh hai cách với nhau.

Chạy trực tiếp từ terminal để lưu một file CSV đã làm sạch vào thư mục data/:
    python scraper.py "chuột gaming" --pages 5
"""
# ---- Thư viện ----
import argparse  # đọc tham số gõ trên terminal (từ khóa, --pages)
import json  # chuyển chuỗi JSON thành dict / list của Python
import time  # time.sleep(): tạm dừng vài giây giữa các lần gọi

import pandas as pd  # bảng dữ liệu (DataFrame)
import requests  # gửi yêu cầu HTTP (giống trình duyệt mở một đường link)
from bs4 import BeautifulSoup  # đọc và tìm thẻ trong HTML

# Dùng lại 2 hàm của bước 2 (làm sạch) khi chạy file này từ terminal
from cleaning import clean_products, normalize_text

# ---- Hằng số (viết HOA = giá trị cố định, không đổi khi chạy) ----
API_URL = "https://tiki.vn/api/v2/products"  # địa chỉ API tìm kiếm của Tiki
SEARCH_PAGE_URL = "https://tiki.vn/search"  # địa chỉ trang tìm kiếm (HTML)
# User-Agent cho Tiki biết "ai" đang gửi yêu cầu. Giả làm trình duyệt Chrome,
# vì một số trang chặn hoặc trả về khác khi thấy yêu cầu đến từ script.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
}
PAGE_SIZE = 40   # mỗi trang Tiki trả tối đa 40 sản phẩm
DELAY = 1        # số giây chờ giữa hai trang, để không làm phiền server của Tiki
TIMEOUT = 15     # chờ tối đa 15 giây cho một yêu cầu, quá thì bỏ cuộc (báo lỗi)
MAX_TRIES = 3    # thử tối đa 3 lần khi Tiki đang bận


def get_api_page(keyword, page):
    """Lấy MỘT trang kết quả tìm kiếm từ API JSON.

    Vào:  keyword = từ khóa (vd "chuột gaming"), page = số trang (1, 2, 3...).
    Ra:   dict Python đọc từ JSON, có 2 phần chính:
          data["data"]   = danh sách sản phẩm của trang này
          data["paging"] = thông tin phân trang (vd "last_page" = trang cuối)

    Khi bị gọi quá nhiều, Tiki trả mã HTTP 429 ("quá nhiều yêu cầu") hoặc
    503 ("server đang bận"), hoặc gửi một trang HTML thay vì JSON.
    Khi đó ta chờ (lần 1 chờ 10 giây, lần 2 chờ 20 giây) rồi thử lại.
    Phải kiểm tra mã trạng thái TRƯỚC raise_for_status(), nếu không thì
    một lỗi 429 sẽ làm dừng việc thu thập ngay lập tức, không kịp thử lại.
    """
    # Tham số gắn vào đường link: ...products?q=chuột gaming&page=1&limit=40
    params = {"q": keyword, "page": page, "limit": PAGE_SIZE}

    # Vòng lặp thử lại: attempt chạy 1, 2, 3
    for attempt in range(1, MAX_TRIES + 1):
        # Gửi yêu cầu GET, giống như mở đường link trên trình duyệt
        response = requests.get(API_URL, params=params, headers=HEADERS, timeout=TIMEOUT)

        # Nếu KHÔNG phải lỗi "bận" (429 / 503) thì xử lý câu trả lời ngay
        if response.status_code not in (429, 503):
            # Lỗi khác (404 không tìm thấy, 500 lỗi server...) -> báo lỗi luôn,
            # không thử lại. Nếu mã là 200 (thành công) thì dòng này không làm gì.
            response.raise_for_status()
            # Chỉ nhận khi Tiki thật sự trả JSON (xem header Content-Type).
            # Nếu Tiki trả HTML thì không return, chạy xuống dưới để thử lại.
            if "json" in response.headers.get("Content-Type", ""):
                return response.json()  # chuyển JSON thành dict rồi trả về

        # Đến đây nghĩa là lần này thất bại. Còn lượt thì chờ rồi thử lại:
        # lần 1 thất bại chờ 10 giây, lần 2 chờ 20 giây (chờ lâu dần).
        if attempt < MAX_TRIES:
            time.sleep(10 * attempt)

    # Hết cả 3 lần vẫn không được -> báo lỗi để app.py hiện thông báo cho người dùng
    raise RuntimeError("Tiki is limiting requests right now. Try again in a few minutes.")


def parse_search_page(html):
    """Lấy danh sách sản phẩm nằm bên trong HTML của trang tiki.vn/search.

    Vào:  html = toàn bộ nội dung HTML của trang (một chuỗi rất dài).
    Ra:   list các dict, mỗi dict là một sản phẩm (cùng dạng với API).

    Các thẻ sản phẩm trên trang được JavaScript vẽ ra trong trình duyệt, nên
    chúng KHÔNG có trong HTML mà requests tải về. Nhưng trang web (làm bằng
    Next.js) còn ghi sẵn dữ liệu của trang dưới dạng JSON trong thẻ
    <script id="__NEXT_DATA__">: BeautifulSoup tìm thẻ đó, json.loads() đọc nó.
    Bỏ qua sản phẩm được tài trợ (quảng cáo), vì đó là vị trí trả tiền để hiện.
    """
    # Biến chuỗi HTML thành một "cây" thẻ để tìm kiếm cho dễ
    soup = BeautifulSoup(html, "html.parser")
    # Tìm thẻ <script> có id="__NEXT_DATA__"
    script = soup.find("script", id="__NEXT_DATA__")
    # script.string = chữ nằm giữa <script> và </script>, là một chuỗi JSON
    data = json.loads(script.string)
    # Đi sâu vào từng tầng của dict để lấy ra danh sách sản phẩm
    items = data["props"]["initialState"]["catalog"]["data"]
    # List comprehension: chỉ giữ sản phẩm KHÔNG có trường "advertisement"
    return [item for item in items if not item.get("advertisement")]


def get_html_page(keyword, page):
    """Cùng một trang kết quả, nhưng lấy từ trang tìm kiếm HTML thay vì từ API."""
    params = {"q": keyword, "page": page}  # ...search?q=chuột gaming&page=1
    response = requests.get(SEARCH_PAGE_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()  # lỗi HTTP (404, 500...) -> dừng và báo lỗi
    return parse_search_page(response.text)  # response.text = HTML dạng chuỗi


def parse_item(item):
    """Chỉ giữ những trường ta cần phân tích, đặt lại tên cột cho dễ hiểu.

    Vào:  item = một sản phẩm thô từ Tiki (dict có rất nhiều trường).
    Ra:   dict gọn hơn, mỗi khóa sẽ thành một cột của bảng.

    item.get("ten") khác item["ten"]: nếu thiếu trường thì .get() trả về None
    (hoặc giá trị mặc định ghi ở tham số thứ 2) thay vì báo lỗi KeyError.
    """
    # "quantity_sold" có dạng {"text": "Đã bán 4757", "value": 4757}.
    # Sản phẩm chưa bán được cái nào thì trường này bị thiếu hoặc là None,
    # khi đó "or {}" thay bằng dict rỗng để dòng sold.get(...) bên dưới không lỗi.
    sold = item.get("quantity_sold") or {}
    return {
        "product_id": str(item.get("id")),  # đổi sang chuỗi: mã là "tên", không phải số để cộng trừ
        "name": item.get("name"),  # tên sản phẩm
        "brand": item.get("brand_name"),  # thương hiệu
        "category": item.get("primary_category_name"),  # danh mục chính
        "price": item.get("price"),  # giá bán hiện tại (VND)
        "original_price": item.get("original_price"),  # giá gốc trước khi giảm
        "sold": sold.get("value", 0),  # số lượng đã bán, thiếu thì là 0
        "rating": item.get("rating_average"),  # điểm đánh giá trung bình (0 - 5 sao)
        "review_count": item.get("review_count", 0),  # số lượt đánh giá
        "image_url": item.get("thumbnail_url"),  # link ảnh nhỏ
        # Biểu thức if/else trên một dòng: có url_path thì ghép thành link đầy đủ,
        # không có thì để None (bước làm sạch sẽ bỏ dòng thiếu link)
        "product_url": "https://tiki.vn/" + item["url_path"] if item.get("url_path") else None,
    }


def crawl(keyword, pages=5):
    """Tải tối đa `pages` trang kết quả (mỗi trang 40 sản phẩm) thành một bảng thô.

    Vào:  keyword = từ khóa, pages = số trang muốn tải (mặc định 5 -> tối đa 200 sản phẩm).
    Ra:   DataFrame, mỗi dòng là một sản phẩm (chưa làm sạch).
    """
    rows = []  # gom các sản phẩm của mọi trang vào đây
    for page in range(1, pages + 1):  # page = 1, 2, ..., pages
        data = get_api_page(keyword, page)  # gọi API lấy một trang
        for item in data["data"]:  # duyệt từng sản phẩm của trang
            rows.append(parse_item(item))  # giữ các trường cần, thêm vào list

        # Nếu đã tới trang cuối mà Tiki có thì dừng sớm, không gọi thêm trang trống
        if page >= data["paging"]["last_page"]:
            break
        time.sleep(DELAY)  # nghỉ 1 giây rồi mới gọi trang tiếp theo
    # Biến list các dict thành bảng: mỗi khóa của dict thành một cột
    return pd.DataFrame(rows)


# Khối này CHỈ chạy khi gõ "python scraper.py ..." trên terminal.
# Khi file khác "import scraper" (như app.py) thì khối này bị bỏ qua.
if __name__ == "__main__":
    # Khai báo các tham số mà terminal nhận
    parser = argparse.ArgumentParser(description="Collect one keyword from Tiki and save it as CSV.")
    parser.add_argument("keyword")  # tham số bắt buộc: từ khóa
    parser.add_argument("--pages", type=int, default=5, help="pages of 40 products")  # tùy chọn
    args = parser.parse_args()  # đọc những gì người dùng đã gõ

    raw = crawl(args.keyword, args.pages)  # bước 1: thu thập
    products = clean_products(raw, args.keyword)  # bước 2: làm sạch
    # Tên file từ từ khóa: "chuột gaming" -> "data/chuot_gaming.csv"
    path = f"data/{normalize_text(args.keyword).replace(' ', '_')}.csv"
    # index=False: không ghi cột số thứ tự 0, 1, 2... của pandas vào file.
    # utf-8-sig: mở bằng Excel vẫn hiện đúng tiếng Việt có dấu.
    products.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"{len(raw)} products downloaded, {len(products)} kept after cleaning -> {path}")
