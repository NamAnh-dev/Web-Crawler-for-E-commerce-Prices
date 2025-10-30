import urllib.parse
import numpy as np
import pandas as pd
import requests
import re
from headers import LAZADA_HEADERS
from utils import Save_to_database, Convert_text

def Get_data(keyword):
    data_sp = []
    encoded = urllib.parse.quote(keyword)
    for i in range(1, 2):
        url = f"https://www.lazada.vn/catalog/?ajax=true&isFirstRequest=true&page={i}&q={encoded}"
        # url = f"https://www.lazada.vn/tag/{encoded}/?ajax=true&isFirstRequest=true&page={i}&catalog_redirect_tag=true&q={encoded}"
        response = requests.get(url, headers = LAZADA_HEADERS)
        response_json = response.json()
        list_items = response_json['mods']['listItems']
        data_sp.extend(list_items)

    return data_sp


def Build_dataframe(list_items):
    dataframe = {
        'Source_productID': [],
        'ProductName': [],
        'Price': [],
        'Original_Price': [],
        'Discount': [],
        'Quantity_Sold': [],
        'Rating': [],
        'Review_Count': [],
        'URL_Image': [],
        'URL_Product': [],
        'Source': []
    }

    for sp in list_items:   
        sp_price = int(sp.get('price', 0))
        sp_original_price = int(sp.get('originalPrice', 0))
        dataframe['Source_productID'].append(sp.get('itemId', ''))
        dataframe['ProductName'].append(sp.get('name', ''))
        dataframe['Price'].append(sp_price)
        dataframe['Original_Price'].append(sp_original_price if sp_original_price != 0 else "")
        dataframe['Quantity_Sold'].append(sp.get('itemSoldCntShow', 0))
        dataframe['Discount'].append(int((sp_original_price - sp_price) / sp_original_price * 100 if sp_original_price != 0 else  0))
        dataframe['Rating'].append(sp.get('ratingScore', ""))
        dataframe['Review_Count'].append(sp.get('review') if sp.get('review') else 0)
        dataframe['URL_Product'].append(sp.get('itemUrl', np.nan))
        dataframe['URL_Image'].append(sp.get('image', np.nan))
        dataframe['Source'].append('Lazada')
    return pd.DataFrame(dataframe)

def Cleaning_dataframe(df, keyword):
    df.dropna(subset=['URL_Product', 'URL_Image'], inplace=True)
    df.drop_duplicates(subset=['Source_productID'], keep='first', inplace=True)
    df['Quantity_Sold'] = df['Quantity_Sold'].apply(
    lambda x: int(float(re.sub(r'[^\d\.]', '', x.lower().replace('k', 'e3').replace('m', 'e6'))))
    if isinstance(x, str) and any(ch.isdigit() for ch in x)
    else 0)
    df.reset_index(drop=True, inplace=True)
   
    x = [Convert_text(word) for word in keyword.split()]
    y = []
    for item in df['ProductName']:
        y.append(Convert_text(item))

    #------------> for item, index in zip(y, range(len(y))):
    #------------>     if x not in item:
    #------------>         df.drop(index = index, inplace = True)
    indexes_to_drop = [i for i, item in enumerate(y) if not all(word in item for word in x)]
    df.drop(index=indexes_to_drop, inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df

def Lazada_crawler(keyword):
    try:
        data = Get_data(keyword)
    except Exception as e:
        print(f"Can't call API to get Lazada data: {e}")
        return
    
    df = Build_dataframe(data)

    try:
        df_cleaned = Cleaning_dataframe(df, keyword)
    except Exception as e:
        print(f"Error cleaning dataframe of Lazada: {e}")
        return

    Save_to_database(df_cleaned)

    print("Lazada: Data saved to database successfully.")


# Lazada_crawler("Chuột gaming")