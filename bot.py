import requests
import os
import feedparser

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

for source, info in feeds.items():
    feed = feedparser.parse(info["url"])

    for entry in feed.entries[:2]:
        title = entry.title
        link = entry.link
        icon = info["icon"]

        # FILTRO SOLO PER FORMULAPASSION
        if source == "FormulaPassion":
            url_lower = link.lower()

            if not any(x in url_lower for x in ["f1", "f2", "f3"]):
                continue

            if "classifica" in url_lower or "classifiche" in url_lower:
                continue

        message = f"{icon} {source}\n\n{title}\n{link}"

        data = {
            "chat_id": CHAT_ID,
            "text": message
        }

        requests.post(BOT_URL, data=data)
