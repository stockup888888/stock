import numpy as np
import pandas as pd
from datetime import datetime, timedelta

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