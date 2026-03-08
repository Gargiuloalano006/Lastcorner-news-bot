import requests
import os

TOKEN = os.environ['8433209125:AAHLqmdjUxvKX8W_WysgzxdtD5P5z9WLQgs']
CHAT_ID = os.environ['-1003723380516']

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

message = "Bot avviato correttamente ✅"

data = {
    "chat_id": -1003723380516,
    "text": message
}

requests.post(url, data=data)
