import os
import requests
import pandas as pd
from datetime import datetime

# ===== CONFIG =====
api_key = "G8pIh74emmo5nmzmzsSlZBFrz8uji1cf"  # Replace with your Polygon.io API key
symbols = ["AAPL", "GOOGL", "NVDA"]  # Symbols you want
start_date = "2025-01-01"
end_date = datetime.today().strftime("%Y-%m-%d")  # Today's date
output_dir = "polygon"

# ===== Ensure output folder exists =====
os.makedirs(output_dir, exist_ok=True)

# ===== Download Data =====
for ticker in symbols:
    print(f"Fetching {ticker}...")

    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 50000,
        "apiKey": api_key
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "results" not in data:
        print(f"No data for {ticker}: {data}")
        continue

    # Convert to DataFrame
    df = pd.DataFrame(data["results"])
    df["Date"] = pd.to_datetime(df["t"], unit="ms")
    df.rename(columns={
    'Open': 'o',
    'High': 'h',
    'Low': 'l',
    'Close': 'c',
    'Volume': 'v'}, inplace=True)

    # Save to CSV
    filepath = os.path.join(output_dir, f"{ticker}.csv")
    df.to_csv(filepath, index=False)
    
