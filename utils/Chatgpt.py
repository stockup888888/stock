import requests
import sys
import os
sys.path.append(os.path.join(os.getcwd(),".."))
from utils.credential import *

def getSentiment(text, model="gpt-5-mini"):
    # input is a string, outout is also a string
    prompt = f"Please analyze the sentiment of the following text and return only 'positive', 'neutral', or 'negative', score from  1 (most negative) - 10 (most positive): {text}"
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {GPT_Key}", "Content-Type": "application/json"},
        json=data,
        # proxies=Proxies,
        timeout=60
    )
    
    if r.status_code == 200:
        sentiment = r.json()["choices"][0]["message"]["content"].strip()
        return sentiment
    return "ERROR"