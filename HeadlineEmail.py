import sys
print(sys.path)
print(sys.executable)
print(sys.version)
import schedule
import time
from utils.credential import *
from utils.symbols import *
from utils.email_utils import *
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import datetime
import finnhub
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("market_job.log"),
        logging.StreamHandler()
    ]
)


def main(runDate):
    
    logging.info(f"Running job for {runDate}")
    
    runDateStr = runDate.strftime('%Y-%m-%d')
    finnhub_client = finnhub.Client(api_key=API_KEY)

    NEWS_COUNT = 10

    # Get top 10 general market headlines
    headlines = finnhub_client.general_news('general', min_id=0)[:NEWS_COUNT]
    email_body = ""
    for i, item in enumerate(headlines):
        email_body += f"{i+1}. {item['headline']}<br><br>"
    
    email_subject = "Market Headline Update " + runDateStr
    send_email(email_subject, email_body)
    

def job():
    runDate = datetime.date.today()
    now = datetime.datetime.now()
    # Define market hours (adjust timezone as needed)
    market_open = now.replace(hour=8, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if market_open <= now <= market_close:
        logging.info("Within market hours.")
        main(runDate)
    else:
        logging.info(f"Not in market hours: {now}")


if __name__ == "__main__":

    # Run job immediately if within market hours
    job()  # Optionally run once at start
    schedule.every(30).minutes.do(job)
    logging.info("Scheduler started. Waiting for jobs...")
    while True:
        schedule.run_pending()
        time.sleep(1)
