import numpy as np
import pandas as pd

def momentum_signals_simple(data):
    """
    Generate momentum signals based on %K and %D.
    
    :param data: DataFrame with columns '%K' and '%D'
    :return: DataFrame with momentum signals and conditions
    """
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



def momentum_signals(data_ori, weights=None, rsi_overbought=70, rsi_oversold=30, rsi_midline=50, buy_threshold=2.0, sell_threshold=-2.0):
    """
    Generate momentum signals in one place:
      - K/D crossover signals + states
      - RSI (Wilder) + signals + states
      - Optional: Bollinger & MACD signals if columns already exist
      - Composite score/signal across KD/RSI/BB/MACD
    
    Returns a DataFrame with new columns:
      MA_Signal, Solid_Buy, Solid_Sell, Overbought, Oversold, Divergence
      RSI, RSI_State, RSI_Buy_Signal, RSI_Sell_Signal, RSI_Mid_Cross_Up/Down
      Composite_Score, Composite_Signal
    """


    data = data_ori.copy()
    # Initialize signal columns
    data['MA_Signal'] = np.nan
    data['Solid_Buy'] = np.nan
    data['Solid_Sell'] = np.nan
    data['Overbought'] = np.nan
    data['Oversold'] = np.nan
    data['Divergence'] = np.nan

    # -----------------------------
    # 1) K/D signals 
    # -----------------------------
    
    # Generate signals based on %K and %D crossovers
    data['MA_Signal'] = np.where((data['%K'] > data['%D']) & (data['%K'].shift(1) <= data['%D'].shift(1)), 'Buy', 
                    np.where((data['%K'] < data['%D']) & (data['%K'].shift(1) >= data['%D'].shift(1)), 'Sell', np.nan))
    
     # Overbought condition: %K and %D values above 80
    data['Overbought'] = np.where((data['%K'] > 80) & (data['%D'] > 80), 'Overbought', np.nan)

    # Oversold condition: %K and %D values below 20
    data['Oversold'] = np.where((data['%K'] < 20) & (data['%D'] < 20), 'Oversold', np.nan)

    # Solid Buy: %K crosses above %D while both are below 20
    data['Solid_Buy'] = np.where((data['MA_Signal'] == 'Buy') & (data['%K'] < 20) & (data['%D'] < 20), 'Solid Buy', np.nan)

    # Solid Sell: %K crosses below %D while both are above 80
    data['Solid_Sell'] = np.where((data['MA_Signal'] == 'Sell') & (data['%K'] > 80) & (data['%D'] > 80), 'Solid Sell', np.nan)
   
    # Divergence (Simple approach): Look for price making new highs/lows but %K and %D not following
    # Here, we're using a basic approach where if the price is increasing but %K and %D are decreasing, we flag divergence
    data['Divergence'] = np.where((data['Close'] > data['Close'].shift(1)) & (data['%K'] < data['%K'].shift(1)) & (data['%D'] < data['%D'].shift(1)), 'Bearish Divergence',
                         np.where((data['Close'] < data['Close'].shift(1)) & (data['%K'] > data['%K'].shift(1)) & (data['%D'] > data['%D'].shift(1)), 'Bullish Divergence', np.nan))

    # -----------------------------
    # 2) RSI (Wilder) + signals
    # -----------------------------

    if 'RSI' in data.columns:
        r = data['RSI']
        data['RSI_State'] = np.where(r > rsi_overbought, 'Overbought',
                              np.where(r < rsi_oversold,  'Oversold', np.nan))
        data['RSI_Buy_Signal']  = np.where((r.shift(1) <= rsi_oversold)  & (r > rsi_oversold), 1, 0)
        data['RSI_Sell_Signal'] = np.where((r.shift(1) >= rsi_overbought) & (r < rsi_overbought), -1, 0)
        data['RSI_Mid_Cross_Up']   = np.where((r.shift(1) <= rsi_midline) & (r > rsi_midline), 1, 0)
        data['RSI_Mid_Cross_Down'] = np.where((r.shift(1) >= rsi_midline) & (r < rsi_midline), -1, 0)

    # ---------------------------------
    # 3) Component scores
    # ---------------------------------
    if weights is None:
        weights = {
            'kd': 1.0,        # KD Buy/Sell
            'kd_solid': 0.5,  # Solid_Buy/Sell bonus
            'rsi': 1.0,       # RSI Buy/Sell
            'rsi_mid': 0.5,   # RSI midline crosses
            'bb': 1.0,        # Bollinger Buy/Sell
            'macd': 1.0       # MACD crossovers
        }
    # KD score
    kd_score = pd.Series(0.0, index=data.index)
    if 'MA_Signal' in data.columns:
        kd_score += weights['kd'] * np.where(data['MA_Signal'].eq('Buy'), 1,
                                      np.where(data['MA_Signal'].eq('Sell'), -1, 0)).astype(float)
        if 'Solid_Buy' in data.columns:
            kd_score += weights['kd_solid'] * (data['Solid_Buy'].notna()).astype(float)
        if 'Solid_Sell' in data.columns:
            kd_score -= weights['kd_solid'] * (data['Solid_Sell'].notna()).astype(float)
    data['KD_Score'] = kd_score.fillna(0.0)

    # RSI score
    rsi_score = pd.Series(0.0, index=data.index)
    if 'RSI_Buy_Signal' in data.columns:
        rsi_score += weights['rsi'] * data['RSI_Buy_Signal'].astype(float)
    if 'RSI_Sell_Signal' in data.columns:
        rsi_score += weights['rsi'] * data['RSI_Sell_Signal'].astype(float)  # already -1/0
    if 'RSI_Mid_Cross_Up' in data.columns:
        rsi_score += weights['rsi_mid'] * data['RSI_Mid_Cross_Up'].astype(float)
    if 'RSI_Mid_Cross_Down' in data.columns:
        rsi_score += weights['rsi_mid'] * data['RSI_Mid_Cross_Down'].astype(float)
    data['RSI_Score'] = rsi_score.fillna(0.0)

    # Bollinger score (expects your BB_Buy_Signal=1, BB_Sell_Signal=-1)
    bb_score = pd.Series(0.0, index=data.index)
    if 'BB_Buy_Signal' in data.columns:
        bb_score += weights['bb'] * data['BB_Buy_Signal'].astype(float)
    if 'BB_Sell_Signal' in data.columns:
        bb_score += weights['bb'] * data['BB_Sell_Signal'].astype(float)
    data['BB_Score'] = bb_score.fillna(0.0)

    # MACD score (uses MACD_Signal if exists, else compute 1/-1 crosses)
    macd_score = pd.Series(0.0, index=data.index)
    if 'MACD_Signal' in data.columns:
        macd_score += weights['macd'] * data['MACD_Signal'].astype(float)
    elif {'macd','macd_signal'}.issubset(data.columns):
        macd_up   = ((data['macd'] > data['macd_signal']) & (data['macd'].shift(1) <= data['macd_signal'].shift(1))).astype(int)
        macd_down = -((data['macd'] < data['macd_signal']) & (data['macd'].shift(1) >= data['macd_signal'].shift(1))).astype(int)
        macd_score += weights['macd'] * (macd_up + macd_down).astype(float)
    data['MACD_Score'] = macd_score.fillna(0.0)

    # ---------------------------------
    # 4) Composite score & signal
    # ---------------------------------
    data['Composite_Score'] = (
        data['KD_Score'].fillna(0) +
        data['RSI_Score'].fillna(0) +
        data['BB_Score'].fillna(0) +
        data['MACD_Score'].fillna(0)
    )

    # data['Composite_Score'] = data['KD_Score'] + data['RSI_Score'] + data['BB_Score'] + data['MACD_Score']
    data['Composite_Signal'] = np.where(
        data['Composite_Score'] >= buy_threshold, 'Buy',
        np.where(data['Composite_Score'] <= sell_threshold, 'Sell', 'Neutral')
    )
        
    data['Score'] = data['Composite_Score']
    
    return data


# Logic 
# When %K crosses above %D, it indicates that the current price momentum is upward ->  a buy signal because it suggests that the price is gaining strength.
# When %K crosses below %D, it indicates that the current price momentum is downward -> a sell signal because it suggests that the price is losing strength.

# Overbought and Oversold Conditions:

# %K and %D  >= 80 => overbought, might be due for a downward correction.
# %K and %D  <= 20 => oversold, might be due for an upward correction.

# Divergences:

# A divergence occurs when the price is making new highs or lows, but %K and %D are not. This can indicate that the momentum is weakening, and a reversal may be imminent.
# 1. %K and %D Crossovers:
# Buy Signal: When %K crosses above %D,  suggesting that the short-term momentum is turning upward, indicating potential price strength. Action: buying the asset or entering a long position.
# Sell Signal: When %K crosses below %D, suggesting that the short-term momentum is turning downward, indicating potential price weakness.
# Action: selling the asset or entering a short position.

# 2. Overbought and Oversold Conditions:
# Overbought Condition:
# Condition: When both %K and %D are above 80 -> rise significantly and could be due for a correction.
# Action: Be cautious about buying; consider selling or taking profits if already in a position. Look for a confirmation signal, such as a %K crossing below %D, to execute a sell.
# Oversold Condition:
# Condition: When both %K and %D are below 20 -> fall significantly and could be due for a rebound.
# Action: Be cautious about selling; consider buying if other indicators support the idea of a reversal. Look for a confirmation signal, such as a %K crossing above %D, to execute a buy.

# 3. Divergences:
# Bullish Divergence:  price makes a new low, but %K and %D do not make new lows (i.e., they show higher lows).
# -> suggests that the downward momentum is weakening, and a reversal to the upside may be imminent.
# Action: Consider buying the asset, especially if confirmed by a %K crossing above %D or if the price breaks above a key resistance level.

# Bearish Divergence:
# Condition: The price makes a new high, but %K and %D do not make new highs (i.e., they show lower highs). -> upward momentum is weakening, and a reversal to the downside
# -> sell the asset, especially if confirmed by a %K crossing below %D or if the price breaks below a key support level.

# Check for Overbought/Oversold Conditions:
   
# Scenario 1: %K > %D and both %K and %D are below 20 (oversold condition) -> buy, as this indicates a potential upward momentum shift in an oversold market.

# Scenario 2: %K < %D while both %K and %D are above 80 (overbought condition) -> sell since a potential downward momentum shift in an overbought market.

# Scenario 3: The price makes a new high, but %K and %D make lower highs (bearish divergence) -> not sure,  consider selling but need other indicators confirm the divergence. (not sure)