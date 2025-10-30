import unicodedata
import re
import mysql.connector

# CÁI NÀY LÀ CẤU HÌNH KẾT NỐI VỚI DB CỦA MYSQL, CHƯA CÓ THÌ TẠO GIỐNG NHƯ BÊN DƯỚI, CÒN CÓ RỒI THÌ THAY CÁI PASS VỚI TÊN DB VÀO

DB_Config = {
    "host": "localhost",
    "user": "root",
    "password": "111111111",
    "database": "ecommerce_db"
}

def Connect_to_database():
    conn = mysql.connector.connect(**DB_Config)
    return conn

# CÁI NÀY LÀ HÀM CHUẨN HÓA BỎ KÍ TỰ, ĐỪNG HỎI T, T CŨNG KHÔNG BIẾT SO T DÙNG CHATGPT

def Convert_text(text):
    text = unicodedata.normalize('NFD', text)   # Chuẩn hóa Unicode và loại bỏ dấu tiếng Việt
    text = ''.join([char for char in text if unicodedata.category(char) != 'Mn'])
    text = re.sub(r'[^a-zA-Z0-9]', '', text)    # Loại bỏ ký tự đặc biệt và khoảng trắng
    
    return text.lower()

# NHỚ LÀ TRONG KHI TẠO BD PHẢI ĐẶT ĐÚNG TÊN VỚI KIỂU DỮ LIỆU NHÁ, KHÔNG LẠI THẮC MẮC SAO K CHẠY ĐƯỢC

def Save_to_database(df):
    conn = Connect_to_database()
    cursor = conn.cursor()

    for index, row in df.iterrows():
        cursor.execute("""
            INSERT INTO products (source_productID, ProductName, price, original_price, discount, quantity_sold, rating, review_count, url_image, url_product, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            row['Source_productID'],
            row['ProductName'],
            row['Price'],
            row['Original_Price'],
            row['Discount'],
            row['Quantity_Sold'],
            row['Rating'],
            row['Review_Count'],
            row['URL_Image'],
            row['URL_Product'],
            row['Source']
        ))
        
    conn.commit()
    cursor.close()
    conn.close()