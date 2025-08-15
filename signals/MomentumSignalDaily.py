import sys
print(sys.executable)
print(sys.version)

import yfinance as yf
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import io
import os
import plotly.express as px
from utils.symbols import *
from utils.email_utils import *
from utils.corepath import *
from utils.formats import *


# Load historical data for each ticker
def load_all_data():
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


def bollinger_bands(data, window=20, no_of_std=2):
    """
    Calculate Bollinger Bands.
    
    :param data: DataFrame with a 'Close' column
    :param window: The number of periods for the moving average (default is 20)
    :param no_of_std: The number of standard deviations to use for the bands (default is 2)
    :return: DataFrame with Bollinger Bands columns 'upper_band', 'lower_band', and 'middle_band'
    """
    rolling_mean = data['Close'].rolling(window).mean()
    rolling_std = data['Close'].rolling(window).std()

    data['middle_band'] = rolling_mean
    data['upper_band'] = rolling_mean + (rolling_std * no_of_std)
    data['lower_band'] = rolling_mean - (rolling_std * no_of_std)

    data['BB_Buy_Signal'] = np.where((data['Close'].shift(1) < data['lower_band'].shift(1)) & (data['Close'] > data['lower_band']),1,0)
    data['BB_Sell_Signal'] = np.where((data['Close'].shift(1) > data['upper_band'].shift(1)) & (data['Close'] < data['upper_band']),-1,0)
    

    return data

# MACD (Moving Average Convergence Divergence)
def MACD(data, span_long=26, span_short=12, span_signal=9):
    """Calculate MACD indicator."""
    data['macd'] = data['Close'].ewm(span=span_short, adjust=False).mean() \
                 - data['Close'].ewm(span=span_long, adjust=False).mean()
    data['macd_signal'] = data['macd'].ewm(span=span_signal, adjust=False).mean()
    data['MACD_Diff'] = data['macd'] - data['macd_signal'] #DIF-DEA


def calcKD(data, name='', window=3, k_period=3, d_period=3):
    """
    Calculate the %K and %D for the KDJ indicator using a momentum approach.
    
    :param data: DataFrame with columns 'High', 'Low', 'Close'
    :param window: The lookback period to calculate rolling min and max (default is 3)
    :param k_period: The period for smoothing %K using SMA (default is 3)
    :param d_period: The period for smoothing %D using SMA (default is 3)
    :return: DataFrame with columns '%K', '%D'
    """
    # Ensure rolling calculations return a single-column Series
    data['rollingMin'] = data['Low'].rolling(window=window).min()
    data['rollingMax'] = data['High'].rolling(window=window).max()

    # Fix the %K calculation (proper syntax)
    data['%K' + name] = ((data['Close'] - data['rollingMin']) / (data['rollingMax'] - data['rollingMin'])) * 100
    # Smooth %K over the k_period using a Simple Moving Average (SMA)
    data['%K'+name] = data['%K'+name].rolling(window=k_period).mean()

    # Calculate %D as the SMA of %K over the d_period
    data['%D'+name] = data['%K'+name].rolling(window=d_period).mean()

    # Drop intermediate columns if necessary
    data = data.drop(columns=['rollingMin', 'rollingMax'])

    return data


def momentum_signals(data_ori):
    """
    Generate momentum signals based on %K and %D.
    
    :param data: DataFrame with columns '%K' and '%D'
    :return: DataFrame with momentum signals and conditions
    """

    data = data_ori.copy()
    # Initialize signal columns
    data['Signal'] = np.nan
    data['Solid_Buy'] = np.nan
    data['Solid_Sell'] = np.nan
    data['Overbought'] = np.nan
    data['Oversold'] = np.nan
    data['Divergence'] = np.nan
    
    # Generate signals based on %K and %D crossovers
    data['Signal'] = np.where((data['%K'] > data['%D']) & (data['%K'].shift(1) <= data['%D'].shift(1)), 'Buy', 
                    np.where((data['%K'] < data['%D']) & (data['%K'].shift(1) >= data['%D'].shift(1)), 'Sell', np.nan))
    
     # Overbought condition: %K and %D values above 80
    data['Overbought'] = np.where((data['%K'] > 80) & (data['%D'] > 80), 'Overbought', np.nan)

    # Oversold condition: %K and %D values below 20
    data['Oversold'] = np.where((data['%K'] < 20) & (data['%D'] < 20), 'Oversold', np.nan)

    # Solid Buy: %K crosses above %D while both are below 20
    data['Solid_Buy'] = np.where((data['Signal'] == 'Buy') & (data['%K'] < 20) & (data['%D'] < 20), 'Solid Buy', np.nan)

    # Solid Sell: %K crosses below %D while both are above 80
    data['Solid_Sell'] = np.where((data['Signal'] == 'Sell') & (data['%K'] > 80) & (data['%D'] > 80), 'Solid Sell', np.nan)
   
    # Divergence (Simple approach): Look for price making new highs/lows but %K and %D not following
    # Here, we're using a basic approach where if the price is increasing but %K and %D are decreasing, we flag divergence
    data['Divergence'] = np.where((data['Close'] > data['Close'].shift(1)) & (data['%K'] < data['%K'].shift(1)) & (data['%D'] < data['%D'].shift(1)), 'Bearish Divergence',
                         np.where((data['Close'] < data['Close'].shift(1)) & (data['%K'] > data['%K'].shift(1)) & (data['%D'] > data['%D'].shift(1)), 'Bullish Divergence', np.nan))

    return data


def plot_signals(data, ticker, date):

    from datetime import timedelta
    
    """
    Plot OHLC candlestick chart with buy, sell, overbought, oversold, and divergence signals using Plotly.
    
    :param data: DataFrame with OHLC and signal data
    :param ticker: Ticker symbol for the plot title
    """
    fig = go.Figure()

    # Add OHLC candlestick data
    fig.add_trace(go.Candlestick(x=data.index,
                                 open=data['Open'],
                                 high=data['High'],
                                 low=data['Low'],
                                 close=data['Close'],
                                 name='OHLC'))
    
    # Add Bollinger Bands
#     fig.add_trace(go.Scatter(x=data.index, y=data['upper_band'], line=dict(color='rgba(255, 0, 0, 0.5)'), name='Upper Band'))
#     fig.add_trace(go.Scatter(x=data.index, y=data['lower_band'], line=dict(color='rgba(0, 0, 255, 0.5)'), name='Lower Band'))
#     fig.add_trace(go.Scatter(x=data.index, y=data['middle_band'], line=dict(color='rgba(0, 255, 0, 0.5)'), name='Middle Band'))

    # Add Bollinger Bands to the price plot for direct price comparison
    fig.add_trace(go.Scatter(x=data.index, y=data['upper_band'], line=dict(color='rgba(250,0,0,0.4)'), name='Upper Band'))
    fig.add_trace(go.Scatter(x=data.index, y=data['middle_band'], line=dict(color='rgba(0,0,250,0.4)'), name='Middle Band'))
    fig.add_trace(go.Scatter(x=data.index, y=data['lower_band'], line=dict(color='rgba(250,0,0,0.4)'), name='Lower Band'))

    # Add BB Buy and Sell Signals
    fig.add_trace(go.Scatter(x=data[data['BB_Buy_Signal']==1].index, y=data[data['BB_Buy_Signal']==1]['Low'], mode='markers', marker_symbol='circle', marker_color='blue', marker_size=15, name='BB Buy Signal'))
    fig.add_trace(go.Scatter(x=data[data['BB_Sell_Signal']==-1].index, y=data[data['BB_Sell_Signal']==-1]['High'], mode='markers', marker_symbol='circle', marker_color='orange', marker_size=15, name='BB Sell Signal'))
    

    # Add buy signals
    buy_signals = data[data['Signal'] == 'Buy']
    fig.add_trace(go.Scatter(x=buy_signals.index, 
                             y=buy_signals['Open'], 
                             mode='markers', 
                             marker=dict(color='black', size=15, symbol='triangle-up'),
                             name='Buy Signal'))

    # Add sell signals
    sell_signals = data[data['Signal'] == 'Sell']
    fig.add_trace(go.Scatter(x=sell_signals.index, 
                             y=sell_signals['Open'], 
                             mode='markers', 
                             marker=dict(color='orange', size=15, symbol='triangle-down'),
                             name='Sell Signal'))

    # Add solid buy signals
    solid_buy_signals = data[data['Solid_Buy'] == 'Solid Buy']
    fig.add_trace(go.Scatter(x=solid_buy_signals.index, 
                             y=solid_buy_signals['Open'], 
                             mode='markers', 
                             marker=dict(color='darkgreen', size=20, symbol='star'),
                             name='Solid Buy Signal'))

    # Add solid sell signals
    solid_sell_signals = data[data['Solid_Sell'] == 'Solid Sell']
    fig.add_trace(go.Scatter(x=solid_sell_signals.index, 
                             y=solid_sell_signals['Open'], 
                             mode='markers', 
                             marker=dict(color='darkred', size=20, symbol='star'),
                             name='Solid Sell Signal'))

    # Add overbought signals
    overbought = data[data['Overbought'] == 'Overbought']
    fig.add_trace(go.Scatter(x=overbought.index, 
                             y=overbought['Open'], 
                             mode='markers', 
                             marker=dict(color='orange', size=10, symbol='circle'),
                             name='Overbought'))

    # Add oversold signals
    oversold = data[data['Oversold'] == 'Oversold']
    fig.add_trace(go.Scatter(x=oversold.index, 
                             y=oversold['Open'], 
                             mode='markers', 
                             marker=dict(color='blue', size=10, symbol='circle'),
                             name='Oversold'))

    # Add divergence signals
    bearish_divergence = data[data['Divergence'] == 'Bearish Divergence']
    bullish_divergence = data[data['Divergence'] == 'Bullish Divergence']

    fig.add_trace(go.Scatter(x=bearish_divergence.index, 
                             y=bearish_divergence['Open'], 
                             mode='markers', 
                             marker=dict(color='purple', size=10, symbol='x'),
                             name='Bearish Divergence'))

    fig.add_trace(go.Scatter(x=bullish_divergence.index, 
                             y=bullish_divergence['Open'], 
                             mode='markers', 
                             marker=dict(color='cyan', size=10, symbol='x'),
                             name='Bullish Divergence'))

    # Get the current local time
    current_local_time = datetime.now()

    # Subtract 5 hours to adjust to EST
    est_time = current_local_time - timedelta(hours=5)

    # Format the adjusted time
    formatted_est_time = est_time.strftime("%Y-%m-%d-%H:%M:%S")

    # Update layout
    fig.update_layout(title=f'{ticker} Price with Momentum {formatted_est_time}',
                      xaxis_title='Date',
                      yaxis_title='Price',
                      xaxis_rangeslider_visible=False)

    fig.show()
    # Save the figure as an HTML file
    # fig.write_html(f'{ticker} Momentum {endDate}.html')
    # Save the figure as a Base64 string for embedding in an email
    buffer = io.BytesIO()
    fig.write_image(buffer, format='png')  # Save as PNG to a buffer
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')  # Convert to Base64
    return fig, img_base64

    
def backtest(data, initial_cash=10000):


    """
    Backtest strategy based on buy/sell signals.
    
    :param data: DataFrame containing the signals and OHLC data
    :param initial_cash: The initial cash amount for the portfolio
    :return: A DataFrame with the trade log and performance metrics
    """
    cash = initial_cash
    shares = 0
    portfolio_value = initial_cash
    trade_log = []
    max_drawdown = 0
    peak_value = portfolio_value

    for index, row in data.iterrows():
        signal = row['Signal']
        solid_buy = row['Solid_Buy']
        solid_sell = row['Solid_Sell']
        price = row['Open']  # Trade at the open price of each period

        if signal == 'Buy' or solid_buy == 'Solid Buy':
            if cash > 0:
                shares = cash // price
                cash -= shares * price
                trade_log.append((index, 'Buy', shares, price, cash))
        
        if signal == 'Sell' or solid_sell == 'Solid Sell':
            if shares > 0:
                cash += shares * price
                trade_log.append((index, 'Sell', shares, price, cash))
                shares = 0

        portfolio_value = cash + shares * price
        peak_value = max(peak_value, portfolio_value)
        drawdown = (peak_value - portfolio_value) / peak_value
        max_drawdown = max(max_drawdown, drawdown)

    trade_df = pd.DataFrame(trade_log, columns=['Date', 'Action', 'Shares', 'Price', 'Cash'])
    # Calculate final return percentage
    final_return_percentage = ((portfolio_value - initial_cash) / initial_cash) * 100

    return trade_df, portfolio_value, max_drawdown, final_return_percentage


# Convert Plotly figures to Base64-encoded images
def plotly_to_base64(fig):
    buffer = io.BytesIO()
    fig.write_image(buffer, format='png')  # Save Plotly figure to buffer
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')  # Encode to Base64
    return img_base64


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

    for ticker in TICKERS:
        data = df_data[ticker]
        data = data[['Date', 'Close', 'High', 'Low', 'Open', 'Volume']]

        # --- Extra Stats ---
        last_close = data['Close'].iloc[-1]
        prev_close = data['Close'].iloc[-2] if len(data) > 1 else last_close
        daily_change = last_close - prev_close
        pct_change = (daily_change / prev_close) * 100 if prev_close != 0 else 0
        avg_volume_20d = data['Volume'].iloc[-20:].mean() if len(data) >= 20 else data['Volume'].mean()
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


        # --- Indicator Calculations ---
        kd_data = calcKD(data)
        kd_data = kd_data.dropna()
        # Detect momentum based on %K and %D crossovers
        bb_data = bollinger_bands(kd_data)
        momentum_data = momentum_signals(bb_data)
        
        if (len(momentum_data)==0):
            continue
        
        result_parts = []
        for c in signal_cols:
            if (momentum_data.iloc[-1][c] !='nan') and momentum_data.iloc[-1][c] != 0:
                result_parts.append(f"{c}: {momentum_data.iloc[-1][c]}")

        if result_parts:
            email_rows.append({
                "Ticker": ticker,
                "Signals": " | ".join(result_parts),
                "Close": f"{last_close:,.2f}",
                "DailyChg": colorize(f"{daily_change:,.2f}"),
                "% Chg": colorize(f"{pct_change:.2f}%", is_percent=True),
                "20D Avg Vol": dollar_format(avg_volume_20d),
                "Net Vol (20d)": dollar_format(net_vol),
                "Vol Up (20d)": dollar_format(up_vol),
                "Vol Down (20d)": dollar_format(down_vol),
                "Vol Bias (20d)": (f"{vol_bias:.1f}%" if not np.isnan(vol_bias) else "N/A"),
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
    email_subject = "Signal Result: " + str(datetime.datetime.now())
    send_email(email_subject, email_result)

   
# def is_market_open():
#     """Check if the current time is within 9:00 AM - 4:15 PM on a weekday."""
#     now = datetime.datetime.now()
#     current_time = now.time()
#     current_day = now.weekday()  # Monday = 0, Sunday = 6
    
#     return (current_day in range(0, 5)) and (START_TIME <= current_time <= END_TIME)


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

 