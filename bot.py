import requests
import os
import feedparser
import json

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

BOT_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

feeds = {
    "FIA": {
        "url": "https://www.fia.com/news/rss",
        "icon": "🚨‼️"
    },
    "FormulaPassion": {
        "url": "https://www.formulapassion.it/feed",
        "icon": "🟡"
    },
    "Motorsport": {
        "url": "https://www.motorsport.com/rss/f1/news/",
        "icon": "🔵"
    },
    "F1.com": {
        "url": "https://www.formula1.com/en/latest/all.xml",
        "icon": "🟢"
    }
}

# FILE CHE SALVA LE NEWS GIÀ INVIATE
sent_file = "sent_news.json"

try:
    with open(sent_file, "r") as f:
        sent_news = json.load(f)
except:
    sent_news = []

def detect_type(title):
    title_lower = title.lower()

    if '"' in title or '“' in title or '”' in title or '«' in title or '»' in title:
        return "INTERVISTA"

    if ":" in title:
        return "INTERVISTA"

    return "NEWS"

def detect_series(link):
    link = link.lower()

    if "f2" in link:
        return "F2"
    if "f3" in link:
        return "F3"

    return "F1"


for source, info in feeds.items():

    feed = feedparser.parse(info["url"])

    for entry in feed.entries[:3]:

        title = entry.title
        link = entry.link
        icon = info["icon"]

        # BLOCCA NEWS DUPLICATE
        if link in sent_news:
            continue

        # FILTRO FORMULAPASSION
        if source == "FormulaPassion":
            url_lower = link.lower()

            if not any(x in url_lower for x in ["f1", "f2", "f3"]):
                continue

            if "classifica" in url_lower or "classifiche" in url_lower:
                continue

        article_type = detect_type(title)
        series = detect_series(link)

        message = f"{icon} {source}\n{article_type} {series}\n\n{title}\n{link}"

        data = {
            "chat_id": CHAT_ID,
            "text": message
        }

        requests.post(BOT_URL, data=data)

        sent_news.append(link)

# SALVA LE NEWS GIÀ INVIATE
with open(sent_file, "w") as f:
    json.dump(sent_news, f)
