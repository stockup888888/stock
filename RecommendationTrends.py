# Recommendation Trends
# Get latest analyst recommendation trends for a company.

import finnhub
import pandas as pd
import datetime
from utils.symbols import *
from utils.credential import *
from utils.corepath import *
from utils.email_utils import *

finnhub_client = finnhub.Client(api_key=API_KEY)

def get_latest_recommendation(ticker):
    """
    Fetch the latest recommendation trend for a ticker.
    """
    try:
        recs = finnhub_client.recommendation_trends(ticker)
        if not recs:
            return None
        # Convert to DataFrame for easier handling
        df = pd.DataFrame(recs)
        # Finnhub returns newest first; ensure sorted just in case
        df = df.sort_values("period", ascending=False)
        latest = df.iloc[0]
        return {
            "period": latest["period"],
            "strongBuy": latest["strongBuy"],
            "buy": latest["buy"],
            "hold": latest["hold"],
            "sell": latest["sell"],
            "strongSell": latest["strongSell"]
        }
    except Exception as e:
        print(f"[ERROR] {ticker}: {e}")
        return None

def build_html_table(data):
    df = pd.DataFrame(data)
    if df.empty:
        return "<p>No recommendation data available.</p>"
    # Generate HTML table with styling
    html_table = df.to_html(index=False, border=0, justify="center")
    return f"""
    <html>
    <head>
        <style>
            table {{
                border-collapse: collapse;
                font-family: Arial, sans-serif;
                font-size: 14px;
            }}
            th, td {{
                border: 1px solid #dddddd;
                padding: 8px 12px;
                text-align: center;
            }}
            th {{
                background-color: #f2f2f2;
            }}
        </style>
    </head>
    <body>
        <h3>Analyst Recommendation Trends</h3>
        {html_table}
    </body>
    </html>
    """

def main(runDate):

    runDateStr = runDate.strftime('%Y%m%d')

    results = []
    for ticker in TICKERS:
        import time
        rec = get_latest_recommendation(ticker)
        if rec:
            print(f"{ticker} ({rec['period']}): "
                  f"Strong Buy={rec['strongBuy']}, Buy={rec['buy']}, "
                  f"Hold={rec['hold']}, Sell={rec['sell']}, Strong Sell={rec['strongSell']}")
            results.append({"Ticker": ticker, **rec})
        else:
            print(f"{ticker}: No recommendation data found.")
        time.sleep(5)
   
    if results:
        pd.DataFrame(results).to_csv(f"{stock_recommandation_path}StockRec{runDateStr}.csv", index=False)
        print("Saved recommendations.csv")

    email_body = build_html_table(results)

    email_subject = "Monthly Stock Recommandation " + runDateStr

    # Only send email if there is at least one news item
    if email_body:
        send_email(email_subject, email_body)
    else:
        print("No news found for any ticker. No email sent.")



if __name__ == "__main__":

    runDate = datetime.datetime.today().date()

    main(runDate)