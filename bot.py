import requests
import os

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

message = "Bot avviato correttamente ✅"

data = {
    "chat_id": CHAT_ID,
    "text": message
}

requests.post(url, data=data)
