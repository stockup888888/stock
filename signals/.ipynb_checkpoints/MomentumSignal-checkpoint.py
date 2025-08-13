import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def momentum_signals(data):
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