CREATE DATABASE ecommerce_db;
USE ecommerce_db;

CREATE TABLE products (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Source_ProductID VARCHAR(255),
    ProductName VARCHAR(255) NOT NULL,
	Price VARCHAR(255),
    Original_Price VARCHAR(255),
    Discount TINYINT, 
    Quantity_Sold VARCHAR(255),
    Rating VARCHAR(255),
    Review_Count INT,
	URL_Image TEXT,
    URL_Product TEXT,
    Source VARCHAR(50) NOT NULL,
    Created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE price_history (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    ProductID INT,
    Fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ProductID) REFERENCES Products(ID)
);
