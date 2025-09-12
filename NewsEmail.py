import sys
print(sys.path)
print(sys.executable)
print(sys.version)

from utils import *
from utils.credential import *
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import time
import datetime
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import io
import plotly.express as px
import finnhub

def main(runDate):
    
    runDateStr = runDate.strftime('%Y-%m-%d')
    finnhub_client = finnhub.Client(api_key=API_KEY)
    
    # Constructing the Email Body
    email_subject = "Daily Stock News Updates" + runDateStr

    email_body = ""

    for ticker in TICKERS:
        print(ticker)
        import time
        newsDict = finnhub_client.company_news(ticker, _from=runDateStr, to=runDateStr)
        if not newsDict:  # Skip if empty list
            continue

        email_body += f"<h3> News for {ticker}:</h3><ul>"
        for news in newsDict[:5]:  # Up to 3 articles per ticker
            sentiment = "Sentiment: " + getSentiment(news['headline']+news['summary'])
            email_body += f"""
            <li>
                <b>{news['headline']}</b>
                <br>{news['summary']}<br>
                <br>{sentiment}<br>
                <a href="{news['url']}">Read more</a>
            </li><br>
            """
        email_body += "</ul>"

        time.sleep(2)

    # Only send email if there is at least one news item
    if email_body:
        send_email(email_subject, email_body)
    else:
        print("No news found for any ticker. No email sent.")


if __name__ == "__main__":

    runDate = datetime.datetime.today().date()

    main(runDate)
