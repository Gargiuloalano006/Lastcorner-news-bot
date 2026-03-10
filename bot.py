import requests
import os
import feedparser
import subprocess

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

sent_file = "sent_news.txt"

# carica link già inviati
try:
    with open(sent_file, "r") as f:
        sent_news = set(f.read().splitlines())
except:
    sent_news = set()


def detect_type(title):

    if '"' in title or "“" in title or "”" in title or "«" in title or "»" in title:
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


updated = False

for source, info in feeds.items():

    feed = feedparser.parse(info["url"])

    for entry in feed.entries[:10]:

        title = entry.title
        link = entry.link
        icon = info["icon"]

        if link in sent_news:
            continue

        # filtro formulapassion
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

        sent_news.add(link)
        updated = True


# salva file aggiornato
if updated:

    with open(sent_file, "w") as f:
        for link in sent_news:
            f.write(link + "\n")

    subprocess.run(["git", "config", "--global", "user.email", "bot@example.com"])
    subprocess.run(["git", "config", "--global", "user.name", "telegram-bot"])

    subprocess.run(["git", "add", sent_file])
    subprocess.run(["git", "commit", "-m", "update sent news"])
    subprocess.run(["git", "push"])
