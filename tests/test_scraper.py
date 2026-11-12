"""Kiểm thử scraper.py trên một mẫu dữ liệu đã lưu sẵn: không cần internet.

Cách pytest hoạt động (áp dụng cho mọi file test):
- Gõ "python -m pytest" ở thư mục dự án. pytest tự tìm các file tên test_*.py
  trong thư mục tests/, rồi chạy mọi hàm có tên bắt đầu bằng test_.
- Trong hàm test, "assert <điều kiện>" nghĩa là "điều kiện này PHẢI đúng".
  Điều kiện sai -> test đó FAILED, pytest in ra giá trị thật để ta so sánh.
- Hàm test chạy hết mà không có assert nào sai -> test đó PASSED.
"""

import json

import scraper

# Một sản phẩm, chép từ một câu trả lời thật của API tìm kiếm Tiki
# (đã bỏ bớt các trường không dùng). Dùng dữ liệu cố định thay vì gọi Tiki
# thật, để test chạy nhanh, không cần mạng và lần nào cũng cho cùng kết quả.
ITEM = {
    "id": 56196502,
    "name": "Chuột Gaming Logitech G102 Gen 2 Lightsync - Hàng Chính Hãng",
    "brand_name": "Logitech",
    "primary_category_name": "Chuột Chơi Game",
    "price": 471900,
    "original_price": 471900,
    "quantity_sold": {"text": "Đã bán 4757", "value": 4757},
    "rating_average": 4.8,
    "review_count": 1392,
    "thumbnail_url": "https://salt.tikicdn.com/cache/280x280/ts/product/f8/39/2b/e7f5.jpg",
    "url_path": "chuot-gaming-logitech-g102-p56196502.html?spid=73161623",
}


def test_parse_item_keeps_the_fields_we_need():
    """parse_item() đổi tên trường đúng và lấy đúng giá trị."""
    row = scraper.parse_item(ITEM)
    assert row["product_id"] == "56196502"  # mã sản phẩm đã đổi thành chuỗi
    assert row["category"] == "Chuột Chơi Game"  # "primary_category_name" -> "category"
    assert row["price"] == 471900
    assert row["sold"] == 4757  # lấy "value" bên trong "quantity_sold"
    # url_path đã được ghép thêm "https://tiki.vn/" ở đầu
    assert row["product_url"].startswith("https://tiki.vn/chuot-gaming-logitech")


def test_parse_item_without_sales_or_link():
    """Trường hợp đặc biệt: sản phẩm chưa bán được cái nào và không có link."""
    # .copy(): tạo bản sao để sửa, không làm hỏng ITEM mà các test khác cũng dùng
    item = ITEM.copy()
    item["quantity_sold"] = None  # chưa bán được cái nào
    item["url_path"] = None  # không có link
    row = scraper.parse_item(item)
    assert row["sold"] == 0  # thiếu số lượng bán -> 0, không bị lỗi
    assert row["product_url"] is None  # thiếu link -> None


def test_parse_search_page_reads_next_data_and_skips_ads():
    """parse_search_page() đọc được JSON trong thẻ __NEXT_DATA__ và bỏ quảng cáo."""
    # Tạo một sản phẩm quảng cáo: giống ITEM nhưng khác id và có "advertisement"
    ad = ITEM.copy()
    ad["id"] = 1
    ad["advertisement"] = {"ad_id": 99}
    # Dữ liệu có cùng các tầng như trang thật của Tiki:
    # props -> initialState -> catalog -> data (danh sách sản phẩm)
    page_data = {"props": {"initialState": {"catalog": {"data": [ad, ITEM]}}}}
    # Tự viết một trang HTML nhỏ, có thẻ <script id="__NEXT_DATA__"> chứa
    # page_data. json.dumps() biến dict thành chuỗi JSON để chèn vào HTML.
    html = (
        "<html><body>"
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(page_data)
        + "</script></body></html>"
    )

    items = scraper.parse_search_page(html)
    assert len(items) == 1  # có 2 sản phẩm, quảng cáo đã bị bỏ -> còn 1
    assert items[0]["id"] == 56196502  # sản phẩm còn lại chính là ITEM
