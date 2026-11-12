"""Kiểm thử các trang web, với một thư mục dữ liệu tạm và không gọi tới Tiki."""

import pandas as pd
import pytest

import app as web  # đặt tên khác là "web" cho dễ phân biệt với biến app bên trong
import storage

PRICES = [200_000, 250_000, 300_000, 310_000, 400_000, 500_000]


def make_products():
    """Các sản phẩm sạch của một lượt tìm kiếm, đúng dạng mà clean_products() trả về."""
    return pd.DataFrame(
        {
            "product_id": ["1", "2", "3", "4", "5", "6"],
            "name": [f"Chuột Gaming {i}" for i in range(6)],
            "brand": "Logitech",
            "category": "Chuột Chơi Game",
            "price": PRICES,
            "original_price": PRICES,
            "discount_pct": 0,
            "sold": [5, 0, 12, 3, 8, 1],
            "rating": 4.8,
            "review_count": 10,
            "image_url": None,
            "product_url": [f"https://tiki.vn/p{i}.html" for i in range(6)],
        }
    )


# ---- Fixture ----
# @pytest.fixture: hàm chuẩn bị sẵn một thứ cho các test dùng chung.
# Test nào có tham số tên "client" thì pytest tự gọi hàm này trước, rồi
# truyền kết quả vào test. Mỗi test nhận một client mới, sạch sẽ.
# tmp_path và monkeypatch là 2 fixture có sẵn của pytest:
# - tmp_path: một thư mục tạm, mới cho mỗi test (pytest tự dọn)
# - monkeypatch: tạm thay một giá trị trong lúc chạy test, xong test thì trả lại
@pytest.fixture
def client(tmp_path, monkeypatch):
    """Một trình duyệt giả để test. Lượt tìm kiếm được lưu vào thư mục tạm, không phải data/."""
    # Tạm đổi storage.FOLDER thành thư mục tạm: test không ghi file rác vào
    # data/searches/ thật, và không thấy các lượt tìm kiếm cũ trên máy.
    monkeypatch.setattr(storage, "FOLDER", tmp_path)
    # test_client() của Flask: gửi yêu cầu tới app mà không cần chạy server thật
    return web.app.test_client()


def test_home_page(client):
    """Trang chủ mở được (mã 200 = thành công) và có tên dự án."""
    response = client.get("/")  # giống như mở http://127.0.0.1:5000/
    assert response.status_code == 200
    assert "EcomCheck" in response.text  # response.text = HTML trả về


def test_result_page_shows_a_saved_search(client):
    """Lưu một lượt tìm kiếm, rồi kiểm tra trang kết quả và lịch sử ở trang chủ."""
    # Lưu thẳng bằng storage, bỏ qua bước gọi Tiki (không cần mạng)
    search_id = storage.save_search("chuột gaming", make_products())

    page = client.get(f"/result/{search_id}")
    assert page.status_code == 200
    # Median của 6 giá = trung bình của 300.000 và 310.000, hiện qua bộ lọc "vnd"
    assert "305.000 ₫" in page.text

    home = client.get("/")
    assert "chuột gaming" in home.text  # có trong danh sách lịch sử tìm kiếm


def test_csv_download(client):
    """Tải file CSV được, và file có dòng tiêu đề cột."""
    search_id = storage.save_search("chuột gaming", make_products())
    response = client.get(f"/result/{search_id}/csv")
    assert response.status_code == 200
    # response.data là dữ liệu dạng bytes; decode() đổi thành chuỗi để tìm chữ
    assert "product_id" in response.data.decode("utf-8-sig")


def test_unknown_search_is_404(client):
    """Lượt tìm kiếm không tồn tại -> lỗi 404, ở cả trang kết quả lẫn link tải CSV."""
    assert client.get("/result/999").status_code == 404
    assert client.get("/result/999/csv").status_code == 404
