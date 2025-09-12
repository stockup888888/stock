import os
import numpy as np
import pandas as pd
import yfinance as yf
from utils.symbols import *
from utils.corepath import *


def load_data(startdate, enddate, tickers, col=None):

    # Load historical data for each ticker
    
    start_ts = pd.to_datetime(startdate)
    end_ts = pd.to_datetime(enddate)

    data = {}

    for t in tickers:
        csv_path = os.path.join(data_path, f"{t}.csv")
        if not os.path.exists(csv_path):
            print(f"[MISSING] {t}: CSV not found at {csv_path}")
            continue
        try:
            df = pd.read_csv(csv_path, parse_dates=["Date"])
            mask = (df["Date"] >= start_ts) & (df["Date"] <= end_ts)
            df = df.loc[mask].copy()
            if col:
                df = df[col]
                df = df.rename(columns = {df.columns[0]: t})
            data[t] = df
            print(f"[LOADED] {t}: {len(df)} rows")
        except Exception as e:
            print(f"[ERR] {t}: failed to read {csv_path} ({e})")

    return data


def load_all_data():

    # Load historical data for all
    all_data = {}

    for t in TICKERS:
        csv_path = os.path.join(data_path, f"{t}.csv")
        if not os.path.exists(csv_path):
            print(f"[MISSING] {t}: CSV not found at {csv_path}")
            continue
        try:
            df = pd.read_csv(csv_path, parse_dates=["Date"])
            # df.set_index("Date", inplace=True)
            # df.sort_index(inplace=True)
            all_data[t] = df
            print(f"[LOADED] {t}: {len(df)} rows")
        except Exception as e:
            print(f"[ERR] {t}: failed to read {csv_path} ({e})")

    return all_data


if __name__ == "__main__":
    pass
