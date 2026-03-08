import requests
import os
import feedparser

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

BOT_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

feeds = [
    "https://www.motorsport.com/rss/f1/news/",
    "https://www.fia.com/news/rss",
    "https://www.formulapassion.it/feed",
    "https://www.formula1.com/en/latest/all.xml"
]

for feed_url in feeds:
    feed = feedparser.parse(feed_url)

    for entry in feed.entries[:2]:
        title = entry.title
        link = entry.link

        message = f"🏁 F1 NEWS\n\n{title}\n{link}"

        data = {
            "chat_id": CHAT_ID,
            "text": message
        }

        requests.post(BOT_URL, data=data)
