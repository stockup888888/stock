import plotly.graph_objects as go
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import io

def plotly_to_base64(fig):
    buffer = io.BytesIO()
    fig.write_image(buffer, format='png')  # Save Plotly figure to buffer
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')  # Encode to Base64
    return img_base64

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
#     buffer = io.BytesIO()
#     fig.write_image(buffer, format='png')  # Save as PNG to a buffer
#     buffer.seek(0)
#     img_base64 = base64.b64encode(buffer.read()).decode('utf-8')  # Convert to Base64