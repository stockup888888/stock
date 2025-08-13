import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def download_stock_data(ticker, start_date, end_date, filename):
    """
    Downloads historical stock data from Yahoo Finance and saves it as a CSV file.
    
    :param ticker: Stock ticker symbol (e.g., 'AAPL')
    :param start_date: Start date in 'YYYY-MM-DD' format
    :param end_date: End date in 'YYYY-MM-DD' format
    :param filename: Name of the file to save the data (e.g., 'data.csv')
    """
    try:
        stock_data = yf.download(ticker, start=start_date, end=end_date)
        stock_data.reset_index(inplace=True)
        stock_data.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
    except Exception as e:
        print(f"Error downloading data for {ticker}: {e}")

if __name__ == "__main__":
    tickers = ['SMR', 'INTC','JNJ','SFM','ALK', 'JBLU', 'UPS', 'FDX', 'DJT','TMV', 'TMF', 'SPY', 'XLP', 'XLF', 'TLT', 'QQQ', 'SQQQ', 'USO', 
                'XLY', 'NVDA', 'SMCI', 'QCOM', 'SOXS', 'SOXL', 'TSM', 'AMD', 
                'XOM', 'UBER', 'TSLA', 'META','GOOGL','GE', 'BABA','HSBC',  'EBAY', 
                'MARA','AAPL', 'PDD', 'MSFT', 'WMT', 'NKE', 'SOFI', 'SBUX', 'COIN', 
                'MCD', 'PLTR', 'MSTR', 'C', 'COST', 'TGT']
    start_date = "2025-01-01"
    today_date = datetime.today().date()  + timedelta(days=1)
    end_date = today_date.strftime("%Y-%m-%d")
    
    for ticker in tickers:
        filename = f"data/{ticker}.csv"
        download_stock_data(ticker, start_date, end_date, filename)
