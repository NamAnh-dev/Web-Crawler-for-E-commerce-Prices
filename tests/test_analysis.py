"""Kiểm thử analysis.py trên 10 sản phẩm mẫu, kết quả có thể tự tính tay để so."""

import json

import pandas as pd

from analysis import analyze, good_deals, price_ranges, price_summary, short_price

# Giá của 10 sản phẩm mẫu, đã xếp từ rẻ đến đắt
PRICES = [
    200_000,
    220_000,
    250_000,
    260_000,
    300_000,
    310_000,
    350_000,
    400_000,
    420_000,
    500_000,
]


def make_products():
    """Mười sản phẩm sạch: sản phẩm 0 bán 0 cái, sản phẩm 9 bán 9 cái.
    Sản phẩm 0, 2, 4, 6, 8 được đánh giá 4.8 sao; các sản phẩm còn lại chưa có đánh giá.

    Một giá trị đơn (vd "category": "Chuột Chơi Game") được pandas lặp lại cho
    cả 10 dòng. ["Logitech", "Razer"] * 5 = list 10 phần tử xen kẽ hai thương hiệu.
    """
    return pd.DataFrame(
        {
            "product_id": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
            "name": [f"Chuột Gaming {i}" for i in range(10)],
            "brand": ["Logitech", "Razer"] * 5,
            "category": "Chuột Chơi Game",
            "price": PRICES,
            "original_price": PRICES,
            "discount_pct": 0,
            "sold": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "rating": [4.8, None] * 5,
            "review_count": 10,
            "image_url": None,
            "product_url": [f"https://tiki.vn/p{i}.html" for i in range(10)],
        }
    )


def test_short_price():
    """Giá viết gọn: nghìn -> K, triệu -> Tr, bỏ đuôi ".0"."""
    assert short_price(85_000) == "85K"
    assert short_price(1_500_000) == "1.5Tr"
    assert short_price(2_000_000) == "2Tr"  # không phải "2.0Tr"


def test_price_summary():
    """Min, max, mean, median của PRICES (có thể tự tính tay để kiểm tra)."""
    prices = price_summary(pd.Series(PRICES))  # pd.Series = một cột dữ liệu
    assert prices["min"] == 200_000
    assert prices["max"] == 500_000
    # Tổng 10 giá = 3.210.000, chia 10 = 321.000
    assert prices["mean"] == 321_000
    # 10 giá (số chẵn) -> median = trung bình của giá thứ 5 và thứ 6
    assert prices["median"] == 305_000  # nằm giữa 300 000 và 310 000


def test_price_ranges_count_products_and_units_sold():
    """Đếm sản phẩm và cộng số lượng bán theo từng khoảng giá."""
    table = price_ranges(make_products())
    # Giá từ 200K đến 500K nên chỉ có 3 khoảng (các khoảng khác bị bỏ qua).
    # 500K thuộc khoảng 500K–1Tr, vì mỗi khoảng tính mốc đầu, không tính mốc cuối.
    assert table["label"].tolist() == ["200K–300K", "300K–500K", "500K–1Tr"]
    # 200K–300K: sản phẩm 0-3 | 300K–500K: sản phẩm 4-8 | 500K–1Tr: sản phẩm 9
    assert table["products"].tolist() == [4, 5, 1]
    # Số bán: 0+1+2+3 = 6 | 4+5+6+7+8 = 30 | 9
    assert table["sold"].tolist() == [6, 30, 9]
    # Phần trăm số sản phẩm: 4/10, 5/10, 1/10
    assert table["product_share"].tolist() == [40.0, 50.0, 10.0]


def test_good_deals_are_cheap_well_rated_and_sorted_by_sales():
    """Đáng mua = giá <= median, 4.5 sao trở lên, ít nhất 5 đánh giá; bán chạy đứng đầu."""
    picks = good_deals(make_products(), median=305_000)
    # Giá <= 305K: sản phẩm 0-4. Có 4.8 sao: 0, 2, 4 (1 và 3 chưa có đánh giá).
    # Xếp theo số bán giảm dần: 4 (bán 4), 2 (bán 2), 0 (bán 0).
    assert picks["product_id"].tolist() == ["4", "2", "0"]


def test_analyze_returns_everything_the_page_needs():
    """analyze() trả về đủ các phần mà trang kết quả cần."""
    report = analyze(make_products())
    assert report["summary"]["products"] == 10
    assert report["summary"]["total_sold"] == 45  # 0 + 1 + ... + 9
    assert report["top_range"]["label"] == "300K–500K"  # khoảng bán nhiều nhất (30)
    assert report["best_sellers"][0]["sold"] == 9  # sản phẩm bán chạy nhất đứng đầu
    # Dữ liệu cho biểu đồ phải là JSON hợp lệ (không có NaN).
    # Test này không cần assert: nếu json.dumps() gặp lỗi thì test tự FAILED.
    json.dumps({"ranges": report["ranges"], "brands": report["brands"]})
