import os
import json
import hashlib
import requests
import difflib
import re
from scraper import get_all_latest_news
from image_generator import generate_news_image
import time

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
SENT_NEWS_FILE      = "sent_news.json"

# ── RELEVANCE FILTER ────────────────────────────────────────────────────────────
# Only send news touching these topics (Nepali + English)
RELEVANT_KEYWORDS = [
    # Stock / capital market
    "शेयर", "सेयर", "nepse", "नेप्से", "शेयरबजार", "सेयरबजार",
    "पुँजीबजार", "capital market", "stock", "ipo", "fpo",
    "आईपीओ", "एफपीओ", "बोनस", "हकप्रद", "right share",
    "dividend", "लाभांश", "demat", "डिम्याट", "broker", "दलाल",
    "mutual fund", "म्युचुअल फन्ड", "index", "सूचकांक", "listing",
    # Economy / finance
    "अर्थतन्त्र", "economy", "economic", "आर्थिक", "gdp", "जिडिपी",
    "inflation", "मुद्रास्फीति", "महँगी", "महंगाई",
    "budget", "बजेट", "fiscal", "राजस्व", "revenue", "tax", "कर",
    "remittance", "रेमिट्यान्स", "विप्रेषण",
    "trade deficit", "व्यापार घाटा", "export", "import", "निर्यात", "आयात",
    # Banking / monetary
    "बैंक", "bank", "ब्याजदर", "interest rate", "राष्ट्र बैंक", "nrb",
    "nepal rastra bank", "monetary", "मौद्रिक", "liquidity", "तरलता",
    "loan", "ऋण", "credit", "कर्जा", "deposit", "निक्षेप",
    "microfinance", "लघुवित्त", "insurance", "बीमा",
    # Government / policy (economy-related)
    "प्रधानमन्त्री", "prime minister", "cabinet", "मन्त्रिपरिशद",
    "मन्त्री", "minister", "सरकार", "government", "policy", "नीति",
    "राष्ट्रपति", "president", "parliament", "संसद",
    "ordinance", "अध्यादेश", "बजेट अधिवेशन",
    # Major political
    "राजनीति", "political", "election", "निर्वाचन",
    "coalition", "गठबन्धन", "राजनीतिक",
    # Companies / corporates
    "कम्पनी", "company", "corporation", "उद्योग", "industry",
    "merger", "acquisition", "ceo", "प्रमुख कार्यकारी",
]

_RELEVANT_RE = re.compile(
    '|'.join(re.escape(k) for k in RELEVANT_KEYWORDS),
    re.IGNORECASE
)


def is_relevant(news):
    """Return True if headline or summary touches relevant topics."""
    text = news.get('headline', '') + ' ' + news.get('summary', '')
    result = bool(_RELEVANT_RE.search(text))
    if not result:
        print(f"[FILTER] Skipped (off-topic): {news['headline'][:70]}")
    return result


def load_sent_news():
    if os.path.exists(SENT_NEWS_FILE):
        try:
            with open(SENT_NEWS_FILE, 'r') as f:
                data = json.load(f)
                # Handle legacy format (list of plain strings)
                if data and isinstance(data[0], str):
                    return [{"link": l, "headline": ""} for l in data]
                return data
        except Exception:
            return []
    return []


def save_sent_news(news_list):
    with open(SENT_NEWS_FILE, 'w') as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)


def send_to_telegram(image_path, caption):
    """Send the generated image + caption to the Telegram channel."""
    if not TELEGRAM_BOT_TOKEN:
        print("[SKIP] No bot token — image generated but not sent.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(image_path, "rb") as f:
        resp = requests.post(
            url,
            files={"photo": f},
            data={
                "chat_id":    TELEGRAM_CHANNEL_ID,
                "caption":    caption,
                "parse_mode": "HTML",
            },
            timeout=30,
        )
    if resp.status_code == 200:
        print("[OK] Sent to Telegram.")
        return True
    else:
        print(f"[ERROR] Telegram: {resp.text}")
        return False


def is_duplicate(headline, link, history):
    """
    Exact link match → duplicate.
    Fuzzy headline match (≥65%) → duplicate (catches cross-portal reposts).
    """
    for sent in history:
        if link == sent.get('link'):
            return True
        sent_h = sent.get('headline', '')
        if sent_h and headline:
            if difflib.SequenceMatcher(None, headline, sent_h).ratio() > 0.65:
                print(f"[SKIP] Near-duplicate: '{headline[:60]}…'")
                return True
    return False


def unique_filename(link):
    """Derive a stable temp filename from the article URL."""
    h = hashlib.md5(link.encode()).hexdigest()[:8]
    return f"news_{h}.jpg"


def main():
    print("=== NEPSE News Agent starting ===")

    sent_history = load_sent_news()
    all_news     = get_all_latest_news()
    new_found    = False

    for news in all_news:
        # ── Relevance gate ──
        if not is_relevant(news):
            continue

        # ── Duplicate gate ──
        if is_duplicate(news['headline'], news['link'], sent_history):
            continue

        print(f"[NEW] {news['source']}: {news['headline'][:80]}")
        new_found = True
        img_path  = unique_filename(news['link'])

        try:
            generate_news_image(
                headline        = news['headline'],
                summary         = news['summary'],
                output_filename = img_path,
                photo_url       = news.get('photo'),
            )

            caption = (
                f"<b>{news['headline']}</b>\n\n"
                f"📰 स्रोत: {news['source']}\n\n"
                f"🔗 समाचारको लिंक कमेन्टमा 👇\n"
                f"{news['link']}"
            )

            sent = send_to_telegram(img_path, caption)

            if sent or not TELEGRAM_BOT_TOKEN:
                sent_history.append({
                    "link":     news['link'],
                    "headline": news['headline'],
                })

            # Clean up temp file
            try:
                os.remove(img_path)
            except Exception:
                pass

            # Rate-limit: don't flood Telegram
            time.sleep(3)

        except Exception as e:
            print(f"[ERROR] Processing '{news['headline'][:60]}': {e}")
            import traceback
            traceback.print_exc()

    # Keep history capped at 200 entries
    if len(sent_history) > 200:
        sent_history = sent_history[-200:]

    save_sent_news(sent_history)

    if not new_found:
        print("[INFO] No new relevant articles this run.")
    else:
        print(f"[INFO] Done. History now has {len(sent_history)} entries.")


if __name__ == "__main__":
    main()
