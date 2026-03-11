import requests
import os
import feedparser
import subprocess
import time
import logging
import re
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Setup logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("f1-bot")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TOKEN   = os.environ.get("TELEGRAM_TOKE")
CHAT_ID = os.environ.get("CHAT_ID")

if not TOKEN or not CHAT_ID:
    log.error("TELEGRAM_TOKEN or CHAT_ID not set - aborting.")
    raise SystemExit(1)

BOT_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

MAX_SENT_ENTRIES = 1500   # trim sent_news.txt to this many entries
MAX_AGE_HOURS    = 48     # skip articles older than this
SEND_DELAY       = 1.2    # seconds between Telegram sends (avoid rate limit)
ENTRIES_PER_FEED = 15     # how many entries to read per feed

# ---------------------------------------------------------------------------
# RSS Feeds
# ---------------------------------------------------------------------------
feeds = {
    "FIA": {
        "url":  "https://www.fia.com/news/rss",
        "icon": "🚨",
    },
    "F1.com": {
        "url":  "https://www.formula1.com/en/latest/all.xml",
        "icon": "🟢",
    },
    "Motorsport": {
        "url":  "https://www.motorsport.com/rss/f1/news/",
        "icon": "🔵",
    },
    "FormulaPassion": {
        "url":  "https://www.formulapassion.it/feed",
        "icon": "🟡",
    },
    "Autosport": {
        "url":  "https://www.autosport.com/rss/f1/news/",
        "icon": "🟠",
    },
    "RaceFans": {
        "url":  "https://www.racefans.net/feed/",
        "icon": "⚪",
    },
    "GPblog": {
        "url":  "https://www.gpblog.com/en/rss.xml",
        "icon": "🔴",
    },
    "PlanetF1": {
        "url":  "https://www.planetf1.com/feed/",
        "icon": "🟣",
    },
    "TheRace": {
        "url":  "https://the-race.com/feed/",
        "icon": "🏁",
    },
    "SkySportF1": {
        "url":  "https://sport.sky.it/xml/rss/sport/motorsport/f1.xml",
        "icon": "🔷",
    },
    "CorriereSport": {
        "url":  "https://www.corrieredellosport.it/rss/formula-1",
        "icon": "📰",
    },
}

# ---------------------------------------------------------------------------
# Sent-news persistence
# ---------------------------------------------------------------------------
sent_file = "sent_news.txt"

try:
    with open(sent_file, "r", encoding="utf-8") as f:
        sent_links: list = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    sent_links = []

sent_news: set = set(sent_links)

# Se il file era vuoto siamo al primo avvio: non inviamo nulla,
# segniamo tutto come già visto (bootstrap).
BOOTSTRAP_MODE: bool = len(sent_links) == 0
if BOOTSTRAP_MODE:
    log.info("Bootstrap mode: prima esecuzione, marco tutti gli articoli senza inviare.")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_link(link: str) -> str:
    """Strip query params & trailing slashes for deduplication."""
    link = link.split("?")[0].split("#")[0].rstrip("/")
    return link.lower()


def detect_type(title: str, summary: str = "") -> str:
    text = (title + " " + summary).lower()

    interview_markers = [
        '"', "\u201c", "\u201d", "\u00ab", "\u00bb",
        "interview", "intervista", "exclusive", "esclusiva",
        "parla", "dice", "dichiara", "ha detto", "afferma",
        "spiega", "racconta",
    ]
    if any(m in text for m in interview_markers):
        return "INTERVISTA"

    analysis_markers = [
        "analisi", "analysis", "analizziamo", "breakdown",
        "come funziona", "how it works", "tecnica", "technical",
        "perche", "why", "spiegato", "explained",
    ]
    if any(m in text for m in analysis_markers):
        return "ANALISI"

    report_markers = [
        "gara", "race", "qualifiche", "qualifying", "prove libere",
        "practice", "sprint", "risultati", "results", "highlights",
    ]
    if any(m in text for m in report_markers):
        return "REPORT"

    return "NEWS"


def detect_series(title: str, link: str) -> str:
    text = (title + " " + link).lower()

    if re.search(r"\bf2\b|formula[\s_-]?2", text):
        return "F2"
    if re.search(r"\bf3\b|formula[\s_-]?3", text):
        return "F3"
    if re.search(r"\bfe\b|formula[\s_-]?e", text):
        return "FE"
    if re.search(r"\bindycar\b|indy\s?500", text):
        return "IndyCar"
    if re.search(r"\bwec\b|le[\s_-]?mans", text):
        return "WEC"
    if re.search(r"f1[\s_-]?academy", text):
        return "F1 Academy"

    return "F1"


def is_too_old(entry) -> bool:
    published = getattr(entry, "published_parsed", None)
    if published is None:
        return False
    try:
        pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - pub_dt) > timedelta(hours=MAX_AGE_HOURS)
    except Exception:
        return False


def should_skip(source: str, title: str, link: str) -> bool:
    url_lower = link.lower()
    text      = (title + " " + link).lower()

    if source == "FormulaPassion":
        if not any(x in url_lower for x in ["f1", "f2", "f3"]):
            return True
        if any(p in url_lower for p in ["classifica", "classifiche", "calendario"]):
            return True

    if source == "GPblog":
        if not any(x in text for x in ["f1", "formula 1", "formula1", "f2", "f3"]):
            return True

    if source == "RaceFans":
        motorsport_kw = ["f1", "formula 1", "formula one", "grand prix", "gp ", "f2", "f3"]
        if not any(k in text for k in motorsport_kw):
            return True

    if source == "TheRace":
        f1_kw = ["f1", "formula 1", "formula one", "grand prix", "f2", "f3"]
        if not any(k in text for k in f1_kw):
            return True

    if source == "SkySportF1":
        f1_kw = ["f1", "formula 1", "formula one", "grand prix", "motogp", "f2", "f3"]
        # keep only motorsport content from Sky
        motorsport_kw = ["formula", "grand prix", "moto", "f1", "f2", "f3"]
        if not any(k in text for k in motorsport_kw):
            return True
        # exclude non-F1 Sky sport sections
        if any(p in url_lower for p in ["/calcio/", "/basket/", "/tennis/", "/nba/", "/nfl/"]):
            return True

    if source == "CorriereSport":
        f1_kw = ["f1", "formula 1", "formula one", "grand prix", "gp"]
        if not any(k in text for k in f1_kw):
            return True

    return False


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_message(icon: str, source: str, article_type: str,
                  series: str, title: str, link: str) -> str:
    safe_title  = escape_html(title)
    safe_source = escape_html(source)
    badge = f"[{article_type} - {series}]"
    return (
        f"{icon} <b>{safe_source}</b>  <i>{badge}</i>\n\n"
        f"<b>{safe_title}</b>\n"
        f'<a href="{link}">Leggi l\'articolo</a>'
    )


def send_message(text: str) -> bool:
    payload = {
        "chat_id":                  CHAT_ID,
        "text":                     text,
        "parse_mode":               "HTML",
        "disable_web_page_preview": "false",
    }
    try:
        resp = requests.post(BOT_URL, data=payload, timeout=15)
        if not resp.ok:
            log.warning("Telegram error %s: %s", resp.status_code, resp.text[:200])
            return False
        return True
    except requests.RequestException as exc:
        log.error("Request failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
new_links: list  = []
sent_count: int  = 0

for source, info in feeds.items():
    log.info("Fetching %s ...", source)
    try:
        feed = feedparser.parse(
            info["url"],
            request_headers={"User-Agent": "Mozilla/5.0 (compatible; F1Bot/2.0)"},
        )
    except Exception as exc:
        log.error("Failed to parse %s: %s", source, exc)
        continue

    if feed.bozo and not feed.entries:
        log.warning("Malformed or empty feed for %s", source)
        continue

    for entry in feed.entries[:ENTRIES_PER_FEED]:
        title = getattr(entry, "title", "").strip()
        link  = getattr(entry, "link",  "").strip()
        if not title or not link:
            continue

        canonical = normalize_link(link)
        if canonical in sent_news or link in sent_news:
            continue

        if is_too_old(entry):
            log.info("Skipping old article: %s", title[:70])
            continue

        if should_skip(source, title, link):
            continue

        # Bootstrap: segna come visto senza inviare
        if BOOTSTRAP_MODE:
            sent_news.add(link)
            sent_news.add(canonical)
            new_links.append(link)
            continue

        summary      = getattr(entry, "summary", "")
        article_type = detect_type(title, summary)
        series       = detect_series(title, link)
        icon         = info["icon"]

        message = build_message(icon, source, article_type, series, title, link)

        log.info("Sending [%s - %s] %s", source, series, title[:70])
        if send_message(message):
            sent_news.add(link)
            sent_news.add(canonical)
            new_links.append(link)
            sent_count += 1
            time.sleep(SEND_DELAY)

if BOOTSTRAP_MODE:
    log.info("Bootstrap completato - marcati %d articoli. Prossima esecuzione inviera' solo le novita'.", len(new_links))
else:
    log.info("Done - sent %d new article(s).", sent_count)

# ---------------------------------------------------------------------------
# Persist updated sent-news list (trimmed to MAX_SENT_ENTRIES)
# ---------------------------------------------------------------------------
if new_links:
    combined = sent_links + new_links
    trimmed  = combined[-MAX_SENT_ENTRIES:]

    with open(sent_file, "w", encoding="utf-8") as f:
        for lnk in trimmed:
            f.write(lnk + "\n")

    subprocess.run(["git", "config", "--global", "user.email", "bot@example.com"], check=False)
    subprocess.run(["git", "config", "--global", "user.name",  "telegram-bot"],    check=False)
    subprocess.run(["git", "add", sent_file],                                       check=False)
    msg = "bot: bootstrap - mark existing articles" if BOOTSTRAP_MODE else f"bot: track {sent_count} new article(s)"
    subprocess.run(["git", "commit", "-m", msg], check=False)
    subprocess.run(["git", "push"],                                                 check=False)
