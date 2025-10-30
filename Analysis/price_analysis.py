# xử lý price_history để vẽ chart
import pandas as pd
import matplotlib.pyplot as plt

def plot_price_history(df):
    df.plot(x="date", y="price", marker="o")
    plt.title("Price History")
    plt.show()
