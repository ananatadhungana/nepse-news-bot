import os
import json
import hashlib
import requests
import difflib
import re
import datetime
import html as _html
from scraper import get_all_latest_news
from image_generator import generate_news_image
import time

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
SENT_NEWS_FILE      = "sent_news.json"
MAX_PER_RUN         = 4     # max articles sent per 15-min run (stops news floods)
HISTORY_EXPIRE_HRS  = 6     # forget sent articles after 6 hours → fresh again

# ── RELEVANCE FILTER ────────────────────────────────────────────────────────────
# INCLUDE: news must match at least one of these topics
RELEVANT_KEYWORDS = [
    # ── NEPSE / Stock market (core) ──
    "नेप्से", "nepse", "शेयर", "सेयर", "शेयरबजार", "सेयरबजार",
    "पुँजीबजार", "पुंजीबजार",
    "आईपीओ", "एफपीओ", "ipo", "fpo",
    "हकप्रद", "बोनस सेयर", "बोनस शेयर", "right share",
    "लाभांश", "dividend",
    "डिम्याट", "demat",
    "दलाल", "broker",
    "म्युचुअल फन्ड", "mutual fund",
    "किताब बन्द", "book close",
    "लिस्टिङ", "listing",
    "कारोबार", "trade volume",
    "मर्जर", "merger", "acquisition",
    "सूचकांक", "index",
    # ── Banking / Monetary ──
    "बैंक", "bank", "बैंकिङ",
    "राष्ट्र बैंक", "नेपाल राष्ट्र बैंक", "nrb",
    "ब्याजदर", "बेस रेट", "interest rate",
    "तरलता", "liquidity",
    "कर्जा", "ऋण", "loan", "credit",
    "निक्षेप", "deposit",
    "मौद्रिक नीति", "monetary policy",
    "लघुवित्त", "microfinance",
    "वित्त कम्पनी", "development bank", "डेभलपमेन्ट बैंक",
    # ── Insurance ──
    "बीमा", "बीमा कम्पनी", "जीवन बीमा", "insurance",
    # ── Economy / Budget ──
    "बजेट", "budget",
    "राजस्व", "revenue",
    "जिडिपी", "gdp",
    "मुद्रास्फीति", "महँगी", "inflation",
    "विप्रेषण", "रेमिट्यान्स", "remittance",
    "व्यापार घाटा", "trade deficit",
    "विदेशी मुद्रा", "foreign exchange", "forex",
    "आयात", "निर्यात", "import", "export",
    "अर्थतन्त्र", "economic",
    "fiscal policy", "राजकोषीय",
    # ── Key political roles (only when economy-impacting) ──
    "बजेट अधिवेशन", "बजेट पेश",
    "अध्यादेश", "ordinance",
    "सरकार गठन", "नयाँ सरकार",
    # ── Hydro / Energy (major NEPSE sector) ──
    "जलविद्युत", "hydropower", "विद्युत",
    "नेपाल विद्युत प्राधिकरण", "nea",
    # ── Telecom (NEPSE listed) ──
    "नेपाल टेलिकम", "nepal telecom", "ntc",
    # ── Cement / Manufacturing (NEPSE listed) ──
    "सिमेन्ट कम्पनी", "cement company",
]

# EXCLUDE: if headline contains ANY of these → skip (entertainment/sports/crime/etc.)
EXCLUDE_KEYWORDS = [
    # Entertainment
    "कलाकार", "गायक", "गायिका", "अभिनेता", "अभिनेत्री",
    "चलचित्र", "फिल्म", "नाटक", "संगीत", "गीत", "एल्बम", "कन्सर्ट",
    "टेलिसिरियल", "वेबसिरिज",
    # Sports (consumer / results — not financial)
    "खेलकुद", "क्रिकेट", "फुटबल", "भलिबल", "ब्याडमिन्टन",
    "विश्वकप", "एसिया कप", "खेलाडी", "प्रशिक्षक",
    # Consumer telecom/internet offers
    "टिभी प्याकेज", "इन्टरनेट प्याकेज", "डाटा प्याकेज",
    "रिचार्ज अफर",
    # Crime / accident
    "हत्या", "दुर्घटना", "बलात्कार", "चोरी", "लुट", "अपहरण",
    # Weather / disaster
    "मौसम", "भूकम्प", "बाढी", "पहिरो", "हिमपात",
    # Religious / cultural (non-financial)
    "तीर्थ", "धार्मिक", "पूजा", "जात्रा", "पर्व",
    # Health (unless economic)
    "अस्पताल", "रोग", "भाइरस",
    # Traffic
    "सवारी साधन", "ट्राफिक",
    # Parliament disruption (not NEPSE-relevant unless budget session)
    "अवरोध",
    # Election results for sports/local bodies (non-financial)
    "निर्वाचित",
    # Political / cabinet (non-financial minister news)
    # Note: अर्थमन्त्री / ऊर्जामन्त्री are in STRONG so they win before this exclude fires
    "मन्त्री",               # cabinet/minister appointment/statement news
    "मन्त्रिपरिषद",          # cabinet formation
    "प्रधानमन्त्री",          # PM news (non-economic)
    "सांसद", "सभासद",        # parliamentarian news
    "राजनीतिक दल",           # political party
    "विपक्ष", "सत्तापक्ष",
]

_INCLUDE_RE = re.compile(
    '|'.join(re.escape(k) for k in RELEVANT_KEYWORDS),
    re.IGNORECASE
)
_EXCLUDE_RE = re.compile(
    '|'.join(re.escape(k) for k in EXCLUDE_KEYWORDS),
    re.IGNORECASE
)

# Strong financial signals — checked FIRST, override exclude list
STRONG_KEYWORDS = [
    "नेप्से", "nepse", "शेयर", "सेयर", "आईपीओ", "एफपीओ", "ipo", "fpo",
    "लाभांश", "dividend", "डिम्याट", "हकप्रद", "राष्ट्र बैंक", "nrb",
    "बजेट", "budget", "मर्जर", "merger",
    # Finance/Energy ministers moved here so "मन्त्री" exclude doesn't block them
    "अर्थमन्त्री", "ऊर्जामन्त्री",
]
_STRONG_RE = re.compile(
    '|'.join(re.escape(k) for k in STRONG_KEYWORDS),
    re.IGNORECASE
)


def is_relevant(news):
    """
    Send if:
      - STRONG financial keyword in HEADLINE (always send), OR
      - INCLUDE keyword in HEADLINE AND no EXCLUDE keyword in headline
    Summary intentionally excluded from all checks — too noisy (political articles
    often mention financial terms in their summary).
    """
    headline = news.get('headline', '')

    # Strong signal in headline → always send (overrides exclude list)
    if _STRONG_RE.search(headline):
        return True

    # Exclude check on headline
    if _EXCLUDE_RE.search(headline):
        print(f"[FILTER] Excluded (off-topic): {headline[:70]}")
        return False

    # Include check on headline only
    if _INCLUDE_RE.search(headline):
        return True

    print(f"[FILTER] Skipped (no match): {headline[:70]}")
    return False


def load_sent_news():
    """Load history and drop entries older than HISTORY_EXPIRE_HRS."""
    if not os.path.exists(SENT_NEWS_FILE):
        return []
    try:
        with open(SENT_NEWS_FILE, 'r') as f:
            data = json.load(f)
        # Legacy: list of plain URL strings
        if data and isinstance(data[0], str):
            data = [{"link": l, "headline": ""} for l in data]
        # Time-based expiry: drop entries with sent_at older than threshold
        now     = datetime.datetime.now(datetime.timezone.utc)
        cutoff  = now - datetime.timedelta(hours=HISTORY_EXPIRE_HRS)
        fresh, expired = [], 0
        for entry in data:
            ts_str = entry.get('sent_at', '')
            if ts_str:
                try:
                    ts = datetime.datetime.fromisoformat(ts_str)
                    # Make naive timestamps timezone-aware (UTC)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=datetime.timezone.utc)
                    if ts < cutoff:
                        expired += 1
                        continue
                except Exception:
                    pass  # malformed timestamp: keep entry
            fresh.append(entry)
        if expired:
            print(f"[INFO] Expired {expired} old history entries (>{HISTORY_EXPIRE_HRS}h old).")
        return fresh
    except Exception:
        return []


def save_sent_news(news_list):
    # Safety cap: never store more than 200 entries
    if len(news_list) > 200:
        news_list = news_list[-200:]
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
    Fuzzy headline ≥0.65 → duplicate (catches cross-portal reposts).
    Longest common block ≥12 chars + ratio ≥0.45 → same event (different wording).
    """
    for sent in history:
        if link == sent.get('link'):
            return True
        sent_h = sent.get('headline', '')
        if sent_h and headline:
            m = difflib.SequenceMatcher(None, headline, sent_h)
            ratio = m.ratio()
            if ratio > 0.65:
                print(f"[SKIP] Near-duplicate: '{headline[:60]}…'")
                return True
            longest = max((b.size for b in m.get_matching_blocks()), default=0)
            if longest >= 12 and ratio > 0.45:
                print(f"[SKIP] Same-event (cross-run): '{headline[:60]}…'")
                return True
    return False


def unique_filename(link):
    """Derive a stable temp filename from the article URL."""
    h = hashlib.md5(link.encode()).hexdigest()[:8]
    return f"news_{h}.jpg"


def _same_event(h1, h2):
    """
    True if two headlines describe the same event.
    Uses fuzzy match AND checks for shared key person/entity name (first 6 chars).
    Catches: 'महावीर पुन मन्त्री' vs 'महावीर पुनलाई मन्त्री' from different portals.
    """
    # Reuse one SequenceMatcher for both ratio() and get_matching_blocks()
    matcher = difflib.SequenceMatcher(None, h1, h2)
    ratio   = matcher.ratio()
    if ratio > 0.72:
        return True
    # Moderate similarity: check shared long substring (12+ chars = same subject)
    blocks  = matcher.get_matching_blocks()
    longest = max((b.size for b in blocks), default=0)
    if longest >= 12 and ratio > 0.50:
        return True
    return False


def main():
    print("=== NEPSE News Agent starting ===")

    sent_history   = load_sent_news()
    all_news       = get_all_latest_news()
    new_found      = False
    sent_this_run  = []   # headlines sent THIS run (for same-event cross-portal dedup)
    run_count      = 0    # articles sent this run

    for news in all_news:
        if run_count >= MAX_PER_RUN:
            print(f"[INFO] MAX_PER_RUN ({MAX_PER_RUN}) reached — stopping.")
            break
        # ── Relevance gate ──
        if not is_relevant(news):
            continue

        # ── Duplicate gate (history) ──
        if is_duplicate(news['headline'], news['link'], sent_history):
            continue

        # ── Same-event gate (within this run — catches cross-portal reposts) ──
        same = False
        for prev_h in sent_this_run:
            if _same_event(news['headline'], prev_h):
                print(f"[SKIP] Same event this run: '{news['headline'][:60]}…'")
                same = True
                break
        if same:
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
                source          = news.get('source'),
            )

            caption = (
                f"<b>{_html.escape(news['headline'])}</b>\n\n"
                f"📰 स्रोत: {_html.escape(news['source'])}\n\n"
                f"🔗 समाचारको लिंक कमेन्टमा 👇\n"
                f"{news['link']}"
            )

            sent = send_to_telegram(img_path, caption)

            if sent or not TELEGRAM_BOT_TOKEN:
                sent_history.append({
                    "link":     news['link'],
                    "headline": news['headline'],
                    "sent_at":  datetime.datetime.now(datetime.timezone.utc).isoformat(),
                })
                sent_this_run.append(news['headline'])
                run_count += 1

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

    save_sent_news(sent_history)

    if not new_found:
        print("[INFO] No new relevant articles this run.")
    else:
        print(f"[INFO] Done. History now has {len(sent_history)} entries.")


if __name__ == "__main__":
    main()
