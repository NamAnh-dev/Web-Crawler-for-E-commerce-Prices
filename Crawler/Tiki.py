import urllib.parse
import numpy as np
import pandas as pd
import requests
import json
from headers import TIKI_HEADERS
from utils import Save_to_database, Convert_text


def Get_data(keyword):
    encoded = urllib.parse.quote(keyword)
    data_sp = []
    for i in range(1, 2):
        url = f'https://tiki.vn/api/v2/products?limit=82&include=advertisement&aggregations=2&trackity_id=06861abb-5fa7-dbfb-e863-8ce9c5b0178b&q={encoded}&page={i}'
        response = requests.get(url, headers=TIKI_HEADERS)
        data_json = response.json()
        data_sp.extend(data_json['data'])

    return data_sp

def Build_dataframe(data):
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

    for sp in data:
        dataframe['Source_productID'].append(int(sp['id']))
        dataframe['ProductName'].append(sp['name'])
        dataframe['Source'].append('Tiki')
        dataframe['Price'].append(int(sp['price']))
        dataframe['Original_Price'].append(int(sp['original_price']) if int(sp['original_price']) > 0 else "")
        dataframe['Quantity_Sold'].append(int(sp.get('quantity_sold', {'value': 0}).get('value', 0)))
        dataframe['Discount'].append(int(sp['discount_rate']))
        dataframe['Rating'].append(float(sp['rating_average']) if float(sp['rating_average']) > 0 else "")
        dataframe['Review_Count'].append(int(sp['review_count']))
        if 'advertisement' in sp and 'ad' in sp['advertisement'] and len(sp['advertisement']['ad']) > 0:
            url = sp['advertisement']['ad'][0]['properties'].get('url', np.nan)
        else:
            url = np.nan
        dataframe['URL_Product'].append(url)
        dataframe['URL_Image'].append(sp.get('thumbnail_url', np.nan))


    return pd.DataFrame(dataframe)

def Cleaning_dataframe(df, keyword):
    df.dropna(subset=['URL_Product', "URL_Image"], inplace=True)
    df.drop_duplicates(subset='Source_productID', keep = 'first', inplace=True)
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

def Tiki_crawler(keyword):
    try:
        data = Get_data(keyword)
    except Exception as e:
        print(f"Can't call API to get Tiki data: {e}")
        return
    
    df = Build_dataframe(data)
    
    try:
        df_cleaned = Cleaning_dataframe(df, keyword)
    except Exception as e:
        print(f"Error cleaning dataframe of Tiki: {e}")
        return


    Save_to_database(df_cleaned)

    print("Tiki: Data saved to database successfully.")


# Tiki_crawler("bút chì")

