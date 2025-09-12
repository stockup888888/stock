import os
import sys
from datetime import date, timedelta
import time

import pandas as pd
import yfinance as yf
from curl_cffi import requests  # pip3 install curl_cffi

from utils.symbols import *
from utils.corepath import *


# -------------------- CONFIG -------------------- 
SAVE_DIR    = "Data/yahoo"                        # folder under cwd
START_DATE  = "2020-01-01"                        # first-time full download start
AUTO_ADJUST = False                               # True -> adjusted OHLCV
# ------------------------------------------------

def get_data_yfinance(tickerList, start_date, end_date):
    """
    Legacy
    """
    data = {}
    for ticker in tickerList:
        result = yf.download(ticker, start=start_date, end=end_date)
        # If MultiIndex, flatten it
        if isinstance(result.columns, pd.MultiIndex):
            result.columns = result.columns.get_level_values(0)  # Get the first level (Price Type)

        result['next_close'] = result['Close'].shift(-1).ffill()
        result['next_open'] = result['Open'].shift(-1).ffill()
        data[ticker] = result
    return data

def _paths(ticker, base_dir):
    csv_path = os.path.join(base_dir, f"{ticker}.csv")
    pkl_path = os.path.join(base_dir, f"{ticker}.pkl")
    return csv_path, pkl_path

def _read_existing(csv_path):
    if not os.path.exists(csv_path):
        return None
    try:
        df = pd.read_csv(csv_path)
        # Parse Date safely, drop bad rows, make tz-naive, set index
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).set_index("Date")
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        print(f"[WARN] Failed to read existing CSV {csv_path}: {e}")
        return None

def _download_history_archive(ticker, start, end):
    """
    Download daily OHLCV data using yfinance directly (no curl_cffi).
    Returns a flat DataFrame with Date index and tidy columns.
    """
    df = yf.download(
        tickers=ticker,
        start=start,
        end=end,               # None = fetch latest available
        auto_adjust=AUTO_ADJUST,
        interval="1d",
        progress=False
    )

    if df is None or df.empty:
        return pd.DataFrame()

    # Flatten MultiIndex if present
    if isinstance(df.columns, pd.MultiIndex):
        if len(df.columns.get_level_values(1).unique()) == 1:
            df.columns = df.columns.get_level_values(0)
        else:
            df.columns = ['_'.join([str(x) for x in col if x]) for col in df.columns]

    # Make index tz-naive, name it Date
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index.name = "Date"

    return df


def _download_history(ticker, start=None, end=None, save=True, save_dir=None):
    """
    Used in Google Colab

    Download daily OHLCV via yfinance and return a tidy DataFrame (Date index).
    Save behavior:
      - If start is None: save the latest available single daily bar as <TICKER>_YYYY-MM-DD.{csv,pkl}
      - If start is provided (end optional): save the requested range as <TICKER>_YYYY-MM-DD_to_YYYY-MM-DD.{csv,pkl}
        (if end is None, uses the latest available date from the download)
    """
    # ---------- Download ----------
    if start is None:
        # grab a small recent window to ensure the latest bar is present
        df = yf.download(
            tickers=ticker,
            period="1d",
            interval="1d",
            auto_adjust=AUTO_ADJUST,
            progress=False,
            group_by="ticker",
        )
    else:
        df = yf.download(
            tickers=ticker,
            start=start,
            end=end,  # None -> latest available
            interval="1d",
            auto_adjust=AUTO_ADJUST,
            progress=False,
            group_by="ticker",
        )

    if df is None or df.empty:
        return pd.DataFrame()

    # ---------- Normalize (flatten & index) ----------
    # Flatten MultiIndex if present — keep only the first level (e.g., 'Open', 'Close')
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(1)

    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    df.index.name = "Date"

    # ---------- Save ----------
    if save:
        base_dir = save_dir if save_dir is not None else data_path  
        os.makedirs(base_dir, exist_ok=True)

        if start is None:
            # Save the latest single bar
            last_ts = df.index.max()
            latest_row = df.loc[[last_ts]]
            fname = f"{ticker}_{last_ts.date().isoformat()}"
            latest_row.to_csv(os.path.join(base_dir, f"{fname}.csv"), index=True)
            latest_row.to_pickle(os.path.join(base_dir, f"{fname}.pkl"))
            print(f"[SAVED] {ticker}: {fname}.csv/.pkl")
        else:
            # Save requested range [start, end_or_latest]
            start_date = pd.to_datetime(start).date()
            end_date = (pd.to_datetime(end).date()
                        if end is not None else df.index.max().date())
            # slice defensively in case extra rows are included
            mask = (df.index.date >= start_date) & (df.index.date <= end_date)
            df_range = df.loc[mask]
            if not df_range.empty:
                fname = f"{ticker}_{start_date.isoformat()}_to_{end_date.isoformat()}"
                df_range.to_csv(os.path.join(base_dir, f"{fname}.csv"), index=True)
                df_range.to_pickle(os.path.join(base_dir, f"{fname}.pkl"))
                print(f"[SAVED] {ticker}: {fname}.csv/.pkl")
            else:
                print(f"[SKIP] {ticker}: no rows in requested range {start_date} → {end_date}")

    return df


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


def _save_incremental_data_old(ticker, base_dir=data_path, daily_dir=data_path, date_obj=None):
    """
    Load today's temp file(s) for this ticker, append to master CSV/PKL, de-dup, save, then delete temp files.
    `date_obj` can override which date to append; defaults to today.
    """
    if date_obj is None:
        date_obj = date.today()
    date_str = date_obj.strftime("%Y%m%d")

    if not os.path.isdir(daily_dir):
        print(f"[TEMP] No daily dir: {daily_dir}")
        return

    # Match exact file name pattern: tickerYYYYMMDD.csv
    target_name = f"{ticker}{date_str}.csv"
    target_csv = os.path.join(daily_dir, target_name)
    target_pkl = target_csv.replace(".csv", ".pkl")

    if not os.path.exists(target_csv):
        print(f"[TEMP] No temp CSV found for {ticker} on {date_str}")
        return

    # Read today's data
    try:
        new_df = pd.read_csv(target_csv, parse_dates=["Date"]).set_index("Date")
        if getattr(new_df.index, "tz", None) is not None:
            new_df.index = new_df.index.tz_localize(None)
        new_df.sort_index(inplace=True)
    except Exception as e:
        print(f"[ERR] Reading temp CSV {target_csv}: {e}")
        return

    # Load existing master
    csv_path, pkl_path = _paths(ticker, base_dir)
    existing = _read_existing(csv_path)

    # Append + de-dup + save
    _append_and_save(ticker, existing, new_df, base_dir)

    # Cleanup temp files
    try:
        os.remove(target_csv)
        if os.path.exists(target_pkl):
            os.remove(target_pkl)
        print(f"[CLEANED] Deleted temp files for {ticker} {date_str}")
    except Exception as e:
        print(f"[WARN] Could not delete temp files for {ticker}: {e}")

def _save_incremental_data(ticker, base_dir=data_path, daily_dir=data_path, date_obj=None):
    """
    If <daily_dir>/<ticker><YYYYMMDD>.csv exists and master CSV doesn't have that date,
    append it, save, and delete the daily file(s).
    Returns True if an append happened, False otherwise.
    """
    if date_obj is None:
        date_obj = date.today()
    date_str = date_obj.strftime("%Y%m%d")
    target_csv = os.path.join(daily_dir, f"{ticker}{date_str}.csv")
    target_pkl = target_csv.replace(".csv", ".pkl")

    if not os.path.isdir(daily_dir):
        print(f"[TEMP] No daily dir: {daily_dir}")
        return False

    if not os.path.exists(target_csv):
        print(f"[TEMP] No temp CSV found for {ticker} on {date_str}")
        return False

    # Read incremental DF
    try:
        new_df = pd.read_csv(target_csv, parse_dates=["Date"]).set_index("Date")
        if getattr(new_df.index, "tz", None) is not None:
            new_df.index = new_df.index.tz_localize(None)
        new_df.sort_index(inplace=True)
        if new_df.empty:
            print(f"[TEMP] Empty temp CSV for {ticker} on {date_str}")
            # still clean up
            os.remove(target_csv)
            if os.path.exists(target_pkl):
                os.remove(target_pkl)
            return False
    except Exception as e:
        print(f"[ERR] Reading temp CSV {target_csv}: {e}")
        return False

    # Load existing master
    csv_path, pkl_path = _paths(ticker, base_dir)
    existing = _read_existing(csv_path)

    # Determine the temp row's date
    temp_dt = new_df.index.max().date()

    # If master already has this date, just clean up temp and exit
    if existing is not None and not existing.empty and temp_dt in existing.index.date:
        print(f"[SKIP] {ticker}: master already has {temp_dt}. Cleaning up temp.")
        try:
            os.remove(target_csv)
            if os.path.exists(target_pkl):
                os.remove(target_pkl)
        except Exception as e:
            print(f"[WARN] Could not delete temp files for {ticker}: {e}")
        return False

    # Append + de-dup + save
    _append_and_save(ticker, existing, new_df, base_dir)

    # Cleanup temp files
    try:
        os.remove(target_csv)
        if os.path.exists(target_pkl):
            os.remove(target_pkl)
        print(f"[CLEANED] Deleted temp files for {ticker} {date_str}")
    except Exception as e:
        print(f"[WARN] Could not delete temp files for {ticker}: {e}")

    return True

# def update_or_init_ticker(ticker, base_dir, start_date):
#     """
#     Initialize or incrementally update a ticker's historical file(s).
#     - If no CSV exists -> download full history from `start_date` to latest and save.
#     - If CSV exists     -> fetch from last saved day to latest, then append + de-dup + save.
#     """
#     csv_path, _ = _paths(ticker, base_dir)
#     existing = _read_existing(csv_path)

#     # ----- First-time init -----
#     if existing is None or existing.empty:
#         print(f"[INIT] {ticker}: downloading from {start_date}…")
#         df_full = _download_history(ticker, start=start_date, end=None, save=False)
#         if df_full is None or df_full.empty:
#             print(f"[SKIP] {ticker}: no data returned.")
#             return
#         _append_and_save(ticker, None, df_full, base_dir)
#         return

#     # ----- Incremental update -----
#     last_dt = existing.index.max().date()

#     # Overlap 1 day: request from last saved date to latest available (end=None)
#     fetch_from = last_dt.isoformat()
#     print(f"[UPDATE] {ticker}: fetching {fetch_from} → latest…")
#     if data_path == colab_path:  
#         df_new = _download_history(ticker, start=fetch_from, end=None, save=False)
#         if df_new is None or df_new.empty:
#             print(f"[NO-NEW] {ticker}: no new rows.")
#             return
#     _save_incremental_data(ticker, existing, df_new, base_dir)
    # (ticker, base_dir=data_path, daily_dir=data_path, date_obj=None)

def get_trade_date(date_obj=None):
    today_dt = (date_obj or date.today())
    # weekday(): Mon=0, ..., Sun=6
    while today_dt.weekday() > 4:  # Sat=5, Sun=6
        today_dt -= timedelta(days=1)
    return today_dt.strftime("%Y%m%d")

def update_or_init_ticker(ticker, base_dir, start_date, daily_dir=data_path, date_obj=None):
    """
    Init or incrementally update a ticker.

    - First-time: full history from `start_date`.
    - Incremental:
        1) If daily file <ticker><YYYYMMDD>.csv exists and master lacks that date -> append & delete (your Case 1).
        2) If daily file not there and master already has the latest date -> do nothing (your Case 2).
        3) (Optional fallback) If daily file not there and master is behind -> fetch via _download_history and append.
    """
    csv_path, _ = _paths(ticker, base_dir)
    existing = _read_existing(csv_path)

    # ----- First-time init -----
    if existing is None or existing.empty:
        print(f"[INIT] {ticker}: downloading from {start_date}…")
        df_full = _download_history(ticker, start=start_date, end=None, save=False)
        if df_full is None or df_full.empty:
            print(f"[SKIP] {ticker}: no data returned.")
            return
        _append_and_save(ticker, None, df_full, base_dir)
        existing = _read_existing(csv_path)  # refresh
        return

    # ----- Incremental path -----
    today_dt = (date_obj or date.today())
    today_str = today_dt.strftime("%Y%m%d")

    # 1) Try to append today's temp file if present (Case 1)
    appended = _save_incremental_data(
        ticker=ticker,
        base_dir=base_dir,
        daily_dir=daily_dir,
        date_obj=today_dt
    )

    # Reload after potential append
    existing = _read_existing(csv_path) 
    last_dt = existing.index.max().date()

    # 2) If no temp file appended and existing already has today's date -> do nothing (Case 2)
    if not appended and last_dt == today_dt:
        print(f"[UP-TO-DATE] {ticker}: master already has {today_dt}.")
        return

    # 3) OPTIONAL FALLBACK: If no temp file and master is behind, fetch & append
    # Comment this block out if you truly want to *only* follow the two cases.
    if not appended and last_dt < today_dt:
        fetch_from = last_dt.isoformat()  # overlap 1 day; de-dup keeps latest
        print(f"[FALLBACK] {ticker}: fetching {fetch_from} → latest…")
        if data_path == colab_path:  
            df_new = _download_history(ticker, start=fetch_from, end=None, save=False)
            if df_new is None or df_new.empty:
                print(f"[NO-NEW] {ticker}: nothing beyond {last_dt}.")
                return
            _append_and_save(ticker, existing, df_new, base_dir)

def main():
    base_dir = data_path

    for ticker in TICKERS:
        try:
            # update_or_init_ticker(ticker, base_dir, START_DATE)
            update_or_init_ticker(ticker, base_dir, START_DATE, data_path, date_obj=None)
            # update_or_init_ticker(ticker, base_dir, START_DATE, data_path, date_obj=date(2025, 9, 5))
        except Exception as e:
            print(f"[ERR] {ticker}: {e}", file=sys.stderr)
        time.sleep(1)

if __name__ == "__main__":
    main()
