import pandas as pd
import yfinance as yf


if __name__ == "__main__":
    ticker_symbols = ["AAPL"]  
    start_date = "2025-02-28"  # Adjust the start date as needed
    end_date = pd.Timestamp.today().strftime('%Y-%m-%d')  # Latest date

    for ticker in ticker_symbols:
      try:
        filename = f"data/{ticker}.csv"
        csv_data = pd.read_csv(filename)
        yahoo_data = yf.download(ticker, start=start_date, end=end_date)
        combined_data = pd.concat([csv_data, yahoo_data], ignore_index=True)
        print(f"Data saved for {ticker}")
      except Exception as e:
        print(f"Error downloading data for {ticker}: {e}")


