import numpy as np
import pandas as pd

def func1():
    print("here")
    return 1
    
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
    # Calculate rolling minimum of the Low prices and maximum of the High prices over the window
    data['rollingMin'] = data['Low'].rolling(window=window).min()
    data['rollingMax'] = data['High'].rolling(window=window).max()

    # Calculate %K as the current close price's position relative to the rolling high-low range
    data['%K'+name] = (data['Close'] - data['rollingMin']) / (data['rollingMax'] - data['rollingMin']) * 100

    # Smooth %K over the k_period using a Simple Moving Average (SMA)
    data['%K'+name] = data['%K'+name].rolling(window=k_period).mean()

    # Calculate %D as the SMA of %K over the d_period
    data['%D'+name] = data['%K'+name].rolling(window=d_period).mean()

    # Drop intermediate columns if necessary
    data = data.drop(columns=['rollingMin', 'rollingMax'])

    return data











# To generate buy or sell signals, you can use a combination of the following criteria:

# Buy Signals:

# A bullish candlestick pattern (e.g., Morning Star) appears.
# [This might be a delayed signal] The MACD crosses above the signal line, indicating upward momentum.
# The differene between the MACD and the MACD signal line is the local minima for 5 days period.
# The close price is near the lower Bollinger Band, suggesting oversold conditions.
# There is a spike in volume, which may confirm the strength of the move.

# Sell Signals:

# A bearish candlestick pattern (e.g., Evening Star, Shooting Star, Hanging Man) appears.
# The MACD crosses below the signal line, indicating downward momentum.
# The differene between the MACD and the MACD signal line is the local maxima for 5 days period.
# The close price is near the upper Bollinger Band, suggesting overbought conditions.
# There is a spike in volume, which may confirm the strength of the move.