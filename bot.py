import requests
import os
import feedparser

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

BOT_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

RSS_URL = "https://feeds.bbci.co.uk/news/technology/rss.xml"

feed = feedparser.parse(RSS_URL)

for entry in feed.entries[:3]:
    title = entry.title
    link = entry.link

    message = f"📰 {title}\n{link}"

    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    requests.post(BOT_URL, data=data)
