# save_daily_prices.py
import os
import sys
from datetime import date, timedelta

import pandas as pd
import yfinance as yf
from curl_cffi import requests  # pip3 install curl_cffi

# -------------------- CONFIG --------------------
TICKERS     = ["AAPL", "MSFT", "NVDA", "AMZN"]   
SAVE_DIR    = "Data/yahoo"                        # folder under cwd
START_DATE  = "2025-01-01"                        # first-time full download start
AUTO_ADJUST = False                               # True -> adjusted OHLCV
# ------------------------------------------------

# One browser-impersonated session reused for all yfinance calls
_YF_SESSION = requests.Session(impersonate="chrome")

def _paths(ticker, base_dir):
    csv_path = os.path.join(base_dir, f"{ticker}.csv")
    pkl_path = os.path.join(base_dir, f"{ticker}.pkl")
    return csv_path, pkl_path

def _ensure_dir():
    base_dir = os.path.join(os.getcwd(), SAVE_DIR)
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def _read_existing(csv_path):
    if not os.path.exists(csv_path):
        return None
    try:
        df = pd.read_csv(csv_path, parse_dates=["Date"])
        df.set_index("Date", inplace=True)
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        print(f"[WARN] Failed to read existing CSV {csv_path}: {e}")
        return None

def _download_history(ticker, start, end):
    """
    end is exclusive per yfinance when using history(start=..., end=...).
    """
    tk = yf.Ticker(ticker, session=_YF_SESSION)
    df = tk.history(start=start, end=end, auto_adjust=AUTO_ADJUST, interval="1d")
    # Ensure consistent columns & index
    if df is None or df.empty:
        return pd.DataFrame()
    # yfinance returns a DatetimeIndex named 'Date' when saved; align now:
    df.index.name = "Date"
    return df[["Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits"]].copy()

def _append_and_save(ticker, existing, new_df, base_dir):
    if existing is None:
        combined = new_df.copy()
    else:
        combined = pd.concat([existing, new_df], axis=0)
        combined = combined[~combined.index.duplicated(keep="last")]
        combined.sort_index(inplace=True)

    csv_path, pkl_path = _paths(ticker, base_dir)
    combined.to_csv(csv_path, index=True)
    combined.to_pickle(pkl_path)
    print(f"[OK] Saved {ticker}: {csv_path} and {pkl_path} | rows={len(combined)}")

def update_or_init_ticker(ticker, base_dir, start_date):
    csv_path, _ = _paths(ticker, base_dir)
    existing = _read_existing(csv_path)

    if existing is None or existing.empty:
        # First-time full history
        print(f"[INIT] {ticker}: downloading from {start_date}…")
        df = _download_history(ticker, start=start_date, end=None)
        if df.empty:
            print(f"[SKIP] {ticker}: no data returned.")
            return
        _append_and_save(ticker, None, df, base_dir)
        return

    # Incremental update: fetch from the day *after* last saved date to tomorrow (exclusive)
    last_dt = existing.index.max().date()
    fetch_from = (last_dt + timedelta(days=1)).isoformat()
    today_plus_1 = (date.today() + timedelta(days=1)).isoformat()

    # If already up-to-date, skip
    if last_dt >= date.today():
        print(f"[UP-TO-DATE] {ticker}: last saved {last_dt}")
        return

    print(f"[UPDATE] {ticker}: fetching {fetch_from} → {today_plus_1}…")
    df_new = _download_history(ticker, start=fetch_from, end=today_plus_1)
    if df_new.empty:
        print(f"[NO-NEW] {ticker}: no new rows.")
        return

    _append_and_save(ticker, existing, df_new, base_dir)

def main():
    base_dir = _ensure_dir()
    for t in TICKERS:
        try:
            update_or_init_ticker(t, base_dir, START_DATE)
        except Exception as e:
            print(f"[ERR] {t}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
