import numpy as np
import pandas as pd

def calcRSI(data, period=14, price_col="Close", out_col="RSI"):
    """
    Wilder's RSI using EMA-style smoothing.
    Adds a column `out_col` to the DataFrame and returns it.
    """
    d = data.copy()
    delta = d[price_col].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's smoothing via EMA with alpha=1/period
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()

    rs = avg_gain / (avg_loss.replace(0, np.nan))  # avoid div/0
    d[out_col] = 100 - (100 / (1 + rs))
    d[out_col] = d[out_col].fillna(50)  # neutralize the very early rows if needed
    return d
