import sys
print(sys.executable)
print(sys.version)

import yfinance as yf
import numpy as np
import pandas as pd
import datetime
import base64
import io
import os
from utils.symbols import *
from utils.email_utils import *
from utils.corepath import *
from utils.formats import *
from data.dataLoader import *
from signals.KlineSignal import *
from signals.RsiSignal import *
from signals.VolumeSignal import *
from signals.MomentumSignal import *



def main():

    start_date = "2023-01-01"
    # today_date = datetime.datetime.today().date() + datetime.timedelta(days=1)
    today_date = datetime.datetime.today().date()
    # today_date = datetime(2024, 9, 16).date()
    end_date = today_date.strftime("%Y-%m-%d")
    print(end_date)

    signal_cols = ['BB_Buy_Signal','BB_Sell_Signal','Signal','Solid_Buy','Solid_Sell','Overbought','Oversold','Divergence']
    email_result = ""

    df_data = load_all_data()
    email_rows = []

    VOL_WIN = 20  # lookback window for volume stats
    VOL_SHORT = 5         # short-term avg window
    VOL_LONG  = 20        # long-term avg window
    VOL_ZWIN  = 60        # window for z-score of volume
    SURGE_X = 1.3      # was 1.5
    DRYUP_X = 0.7      # was 0.5 (dry-up less rare)
    ZSURGE  = 1.5      # was 2.0
    CONF_WIN  = 5   # lookback for OBV/A/D slope confirmation

    for ticker in TICKERS:
        data = df_data[ticker]
        data = data[['Date', 'Close', 'High', 'Low', 'Open', 'Volume']]

       # --- Extra Stats ---
        last_close = data['Close'].iloc[-1]
        prev_close = data['Close'].iloc[-2] if len(data) > 1 else last_close
        daily_change = last_close - prev_close
        pct_change = (daily_change / prev_close) * 100 if prev_close != 0 else 0

        # --- Daily volume Δ ---
        last_vol = data['Volume'].iloc[-1]
        prev_vol = data['Volume'].iloc[-2] if len(data) > 1 else last_vol
        vol_delta = last_vol - prev_vol
        pct_vol_delta = (vol_delta / prev_vol) * 100 if prev_vol > 0 else 0

        avg_volume_20d = data['Volume'].iloc[-20:].mean() if len(data) >= 20 else data['Volume'].mean()
        
        # --- YTD return ---
        import pandas as pd
        ytd_return = (
            ((last_close / data.loc[data['Date'].dt.year == pd.Timestamp.today().year, 'Close'].iloc[0]) - 1) * 100
            if any(data['Date'].dt.year == pd.Timestamp.today().year)
            else None
        )

         # --- Net Volume calculations (last VOL_WIN days) ---
        # Define up/down days by close-to-close change
        data['chg'] = data['Close'].diff()
        window = data.tail(VOL_WIN) if len(data) >= VOL_WIN else data
        up_vol   = window.loc[window['chg'] > 0, 'Volume'].sum()
        down_vol = window.loc[window['chg'] < 0, 'Volume'].sum()
        net_vol  = up_vol - down_vol
        tot_vol  = up_vol + down_vol
        vol_bias = (up_vol / tot_vol) * 100 if tot_vol > 0 else np.nan  # % of volume on up days

        # --- Short/Long avg volume, ratios ---
        avg_vol_short = data['Volume'].tail(VOL_SHORT).mean() if len(data) >= VOL_SHORT else data['Volume'].mean()
        avg_vol_long  = data['Volume'].tail(VOL_LONG).mean()  if len(data) >= VOL_LONG  else data['Volume'].mean()
        vol_ratio_5   = last_vol / avg_vol_short if avg_vol_short > 0 else np.nan
        vol_ratio_20  = last_vol / avg_vol_long  if avg_vol_long  > 0 else np.nan

        # --- Volume z-score (60d) ---
        if len(data) >= VOL_ZWIN:
            vwin = data['Volume'].tail(VOL_ZWIN)
            vmu, vsd = vwin.mean(), vwin.std(ddof=0)
            vol_z = (last_vol - vmu) / vsd if vsd > 0 else np.nan
        else:
            vol_z = np.nan


       # --- OBV & A/D confirmation ---
        # OBV
        obv = (np.sign(data['chg']).fillna(0) * data['Volume']).cumsum()
        obv_slope = obv.iloc[-1] - obv.iloc[max(len(obv)-CONF_WIN-1, 0)]

        # A/D
        hl = (data['High'] - data['Low']).replace(0, np.nan)
        mfm = (((data['Close'] - data['Low']) - (data['High'] - data['Close'])) / hl).fillna(0)
        adl = (mfm * data['Volume']).cumsum()
        adl_slope = adl.iloc[-1] - adl.iloc[max(len(adl)-CONF_WIN-1, 0)]

        # --- Indicator Calculations ---
        kd_data = calcKD(data)
        kd_data = kd_data.dropna()
        # Detect momentum based on %K and %D crossovers
        bb_data = bollinger_bands(kd_data)
        rsi_data = calcRSI(bb_data, period=14, price_col="Close", out_col="RSI")
        momentum_data = momentum_signals(rsi_data)
        

        if (len(momentum_data)==0):
            continue
        
        # --- Labels shown in "Signals" column (kept for texture) ---
        vol_labels = []
        if not np.isnan(vol_ratio_5):
            if vol_ratio_5 >= SURGE_X: vol_labels.append("Volume Surge")
            elif vol_ratio_5 <= DRYUP_X: vol_labels.append("Volume Dry-up")
        if obv_slope > 0 and daily_change > 0: vol_labels.append("OBV↑")
        if adl_slope > 0 and daily_change > 0: vol_labels.append("A/D↑")
        if obv_slope < 0 and daily_change < 0: vol_labels.append("OBV↓")
        if adl_slope < 0 and daily_change < 0: vol_labels.append("A/D↓")

        volume_signal = genVolumeSignal(daily_change, obv_slope, adl_slope, vol_ratio_5, vol_z, ZSURGE, SURGE_X, DRYUP_X)

        result_parts = []
        last = momentum_data.iloc[-1]
        momentum_signal = last.get("Composite_Signal", np.nan)
        momentum_score  = last.get("Composite_Score", np.nan)

        # Default label
        momentum_str = "Neutral"

        if pd.notna(momentum_signal):
            # If it's Buy or Sell
            if pd.notna(momentum_score):
                momentum_str = f"{momentum_signal} ({momentum_score:.1f})"
            else:
                momentum_str = str(momentum_signal)
        else:
            # Neutral case (no clear Buy/Sell)
            if pd.notna(momentum_score):
                momentum_str = f"Neutral ({momentum_score:.1f})"

        result_parts = format_signal_row(last) 
        result_parts += vol_labels

        if result_parts:
            email_rows.append({
                "Ticker": ticker,
                "MomentumSignal": momentum_badge(" | ".join(result_parts)) if result_parts else "—",
                "VolumeSignal": badge(volume_signal),
                "Close": f"{last_close:,.2f}",
                "DailyChg": colorize(f"{daily_change:,.2f}"),
                "% Chg": colorize(f"{pct_change:.2f}%", is_percent=True),
                "Vol": highlight_vol(last_vol, avg_vol_short),   # new highlighting
                "Vol Δ": highlight_vol(vol_delta, avg_vol_short),# compare delta to 5d avg too
                "% Vol Δ": colorize(f"{pct_vol_delta:.1f}%", is_percent=True),
                "Vol x5": f"{vol_ratio_5:.2f}" if pd.notna(vol_ratio_5) else "N/A",
                "Vol z(60)": f"{vol_z:.2f}" if pd.notna(vol_z) else "N/A",
                # "AvgVol(5d)": dollar_format(avg_vol_short),
                # "AvgVol(20d)": dollar_format(avg_vol_long),
                # "Vol x20": f"{vol_ratio_20:.2f}" if pd.notna(vol_ratio_20) else "N/A",
                
                # "Net Vol (20d)": dollar_format(net_vol),
                # "Vol Up (20d)": dollar_format(up_vol),
                # "Vol Down (20d)": dollar_format(down_vol),
                # "Vol Bias (20d)": (f"{vol_bias:.1f}%" if not np.isnan(vol_bias) else "N/A"),
                "YTD Return": colorize(f"{ytd_return:.2f}%", is_percent=True) if ytd_return is not None else "N/A",
                
            })
        # for c in signal_cols:
        #     if (momentum_data.iloc[-1][c] !='nan') & (momentum_data.iloc[-1][c] !=0):
        #         result = result + c + ": " + str(momentum_data.iloc[-1][c]) + "    "
        #         signal_result = str(momentum_data.iloc[-1][c])
        # if result != "":
        #     print(f'{ticker}: {result}')
        #     email_result += f"{ticker}: {result}\n "
#         fig, img_base64 = plot_signals(momentum_data, ticker, endDate)
#         images_embedded.append((ticker, img_base64))
        
#         file_path = f"{ticker}_signal_plot.png"
#         fig.write_image(file_path)
#         attached_files.append(file_path)

        # Convert all figures to Base64
        # if signal_result in ['Buy', 'Sell', 'Solid_Buy', 'Solid_Sell', 'Overbought', 'Oversold']:
            # images_embedded.append(img_base64)
    # Build HTML table
    if email_rows:
        import pandas as pd
        df_email = pd.DataFrame(email_rows)
        email_result = df_email.to_html(index=False, escape=False, border=0, justify="center") 
    else:
        email_result = "<p>No active signals today.</p>"

    # Create the email
    email_subject = "Signal Result: " + str(datetime.datetime.now().date())
    send_email(email_subject, email_result)


if __name__ == "__main__":

    main()

    # Define start and end time
    # START_TIME = datetime.time(8, 55)   # 9:00 AM
    # END_TIME = datetime.time(21, 15)   # 4:15 PM

    # while True:
    #     now = datetime.datetime.now()
    #     current_time = now.time()

    #     if current_time < START_TIME:
    #         # Sleep until 9:15 AM if started early
    #         seconds_until_start = (datetime.datetime.combine(now.date(), START_TIME) - now).total_seconds()
    #         print(f"Waiting until 9:15 AM... Sleeping for {seconds_until_start:.0f} seconds.")
    #         import time
    #         time.sleep(seconds_until_start)
        
    #     elif START_TIME <= current_time <= END_TIME:
    #         print(f"Running MomSig.py at {now.strftime('%Y-%m-%d %H:%M:%S')}")
            
    #         # Run the script
    #         main()
    #         import time
    #         # Wait 10 minutes before the next run
    #         print("Sleep for 10 min")
    #         time.sleep(60*15)  # 600 seconds = 10 minutes
            
    #     else:
    #         print(f"Market closed. Exiting at {now.strftime('%H:%M:%S')}.")
    #         break  # Exit the loop when it's past 16:15

 