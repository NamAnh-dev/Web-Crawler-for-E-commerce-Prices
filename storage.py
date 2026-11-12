"""Bước 3 - Lưu: mỗi lượt tìm kiếm được lưu thành một file CSV trong data/searches/.

Tên file là số thứ tự của lượt tìm kiếm: data/searches/3.csv là lượt tìm kiếm
hiện ở trang /result/3. Mỗi file chứa các sản phẩm đã làm sạch, cộng thêm hai
cột: `keyword` (đã tìm từ gì) và `crawled_at` (tìm lúc nào).
"""

from datetime import datetime  # lấy ngày giờ hiện tại
from pathlib import Path  # làm việc với đường dẫn file/thư mục (chạy được cả Windows lẫn Mac)

import pandas as pd

# Thư mục lưu các lượt tìm kiếm.
# __file__ = đường dẫn của chính file storage.py; .parent = thư mục chứa nó.
# Toán tử "/" của Path ghép đường dẫn: <thư mục dự án>/data/searches
# Nhờ vậy chạy app từ thư mục nào cũng lưu đúng chỗ.
FOLDER = Path(__file__).parent / "data" / "searches"


def search_path(search_id):
    """Đường dẫn file CSV của một lượt tìm kiếm: 3 -> data/searches/3.csv"""
    return FOLDER / f"{search_id}.csv"


def save_search(keyword, products):
    """Lưu các sản phẩm của một lượt tìm kiếm. Trả về số thứ tự của lượt tìm kiếm mới."""
    # Tạo thư mục nếu chưa có. parents=True: tạo luôn cả thư mục cha (data/).
    # exist_ok=True: thư mục đã có rồi thì không báo lỗi.
    FOLDER.mkdir(parents=True, exist_ok=True)
    # Lấy số thứ tự của các file đã có: glob("*.csv") tìm mọi file .csv,
    # path.stem là tên file không có đuôi ("3.csv" -> "3"), int() đổi thành số 3.
    numbers = [int(path.stem) for path in FOLDER.glob("*.csv")]
    # Số mới = số lớn nhất + 1. default=0: thư mục còn trống thì max() trả 0 -> số mới là 1.
    search_id = max(numbers, default=0) + 1

    # Sao chép bảng để thêm cột mà không làm thay đổi bảng `products` của người gọi
    table = products.copy()
    table.insert(0, "keyword", keyword)  # chèn cột "keyword" vào vị trí đầu tiên (cột 0)
    # Cột "crawled_at": ngày giờ hiện tại dạng chữ, vd "2026-11-12 14:30"
    table["crawled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    # utf-8-sig: Excel hiện đúng tiếng Việt. index=False: không ghi cột số thứ tự dòng.
    table.to_csv(search_path(search_id), index=False, encoding="utf-8-sig")
    return search_id


def load_search(search_id):
    """Đọc các sản phẩm của một lượt tìm kiếm thành DataFrame, hoặc None nếu không có file."""
    if not search_path(search_id).exists():  # không có file (vd /result/999) -> None
        return None
    # dtype={"product_id": str}: đọc product_id là chuỗi, đúng như lúc lưu.
    # Nếu không ghi, pandas sẽ tự đoán đó là số.
    return pd.read_csv(search_path(search_id), dtype={"product_id": str})


def search_info(search_id, products):
    """Vài thông tin về một lượt tìm kiếm, cho phần đầu trang kết quả và danh sách lịch sử."""
    # .iloc[0] = giá trị ở dòng đầu tiên. Mọi dòng có cùng keyword, category
    # và crawled_at, nên chỉ cần đọc dòng đầu.
    # int(): đổi số của pandas/numpy thành số int bình thường của Python.
    return {
        "id": search_id,
        "keyword": products["keyword"].iloc[0],
        "category": products["category"].iloc[0],
        "created_at": products["crawled_at"].iloc[0],
        "products": len(products),  # số sản phẩm = số dòng của bảng
        "min_price": int(products["price"].min()),  # giá thấp nhất
        "max_price": int(products["price"].max()),  # giá cao nhất
        "median_price": int(products["price"].median()),  # giá trung vị (giá ở giữa)
    }


def recent_searches(limit=6):
    """Các lượt tìm kiếm gần nhất, mới nhất đứng đầu (tối đa `limit` lượt)."""
    # Số thứ tự của mọi file đã lưu (giống trong save_search)
    numbers = [int(path.stem) for path in FOLDER.glob("*.csv")]
    # Sắp xếp giảm dần: số lớn = lượt tìm mới hơn -> đứng đầu
    numbers.sort(reverse=True)

    searches = []
    # numbers[:limit]: chỉ lấy `limit` phần tử đầu (6 lượt mới nhất)
    for search_id in numbers[:limit]:
        # Đọc file rồi tóm tắt thành dict, thêm vào danh sách
        searches.append(search_info(search_id, load_search(search_id)))
    return searches
