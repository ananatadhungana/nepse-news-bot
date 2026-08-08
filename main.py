import os
import json
import requests
import difflib
import re
import datetime
import html as _html
from scraper import get_all_latest_news
import time

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
SENT_NEWS_FILE      = "sent_news.json"
MAX_PER_RUN         = 4     # max articles sent per 15-min run (stops news floods)
HISTORY_MAX_ENTRIES = 500   # dedup memory size — NOT time-based anymore.
                            # (old 6h time-expiry caused same article to be
                            # re-sent every 6h if nothing new was published)

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

# All NEPSE-listed companies (commercial banks, dev banks, finance, hotels,
# hydropower, investment, life insurance, manufacturing, microfinance).
# Full legal names only — no bare ticker symbols (things like "API", "CITY",
# "SBI" would substring-match ordinary words with no word-boundary regex).
# Source: merolagani.com/CompanyList.aspx, pulled 2026-08-08.
LISTED_COMPANIES = [
    # Commercial Banks
    "Agriculture Development Bank Limited", "Citizen Bank International Limited",
    "Everest Bank Limited", "Global IME Bank Limited", "Himalayan Bank Limited",
    "Kumari Bank Limited", "Machhapuchchhre Bank Limited", "Nabil Bank Limited",
    "Nepal Bank Limited", "NIC Asia Bank Ltd.", "NMB Bank Limited",
    "Prime Commercial Bank Ltd.", "Sanima Bank Limited", "Nepal SBI Bank Limited",
    "Siddhartha Bank Limited", "Standard Chartered Bank Limited",
    "Prabhu Bank Limited", "Nepal Investment Mega Bank Limited",
    "Laxmi Sunrise Bank Limited",
    # Development Banks
    "Corporate Development Bank Limited", "Excel Development Bank Ltd.",
    "Garima Bikas Bank Limited", "Jyoti Bikas Bank Limited",
    "Miteri Development Bank Limited", "Muktinath Bikas Bank Ltd.",
    "Narayani Development Bank Limited", "Shangrila Development Bank Ltd.",
    "Shine Resunga Development Bank Ltd.", "Sindhu Bikash Bank Ltd",
    "Green Development Bank Ltd.", "Salapa Bikas Bank Limited",
    "Mahalaxmi Bikas Bank Ltd.", "Lumbini Bikas Bank Ltd.",
    "Kamana Sewa Bikas Bank Limited", "Saptakoshi Development Bank Ltd",
    # Finance
    "Central Finance Co. Ltd.", "Goodwill Finance Co. Ltd.",
    "Guheshowori Merchant Bank & Finance Co. Ltd.", "ICFC Finance Limited",
    "Janaki Finance Ltd.", "Manjushree Finance Ltd.",
    "Multipurpose Finance Company Limited", "Nepal Finance Ltd.",
    "Pokhara Finance Ltd.", "Progressive Finance Limited",
    "Shree Investment Finance Co. Ltd.", "Reliance Finance Ltd.",
    "Gurkhas Finance Ltd.", "Best Finance Company Ltd.",
    "Samriddhi Finance Company Limited",
    # Hotels & Tourism
    "Oriental Hotels Limited", "Soaltee Hotel Limited",
    "Taragaon Regency Hotel Limited", "Chandragiri Hills Limited",
    "Kalinchowk Darshan Limited", "City Hotel Limited",
    "Bandipur Cablecar and Tourism Limited", "Hotel Forest Inn Limited",
    # Investment
    "Citizen Investment Trust", "Hathway Investment Nepal Limited",
    "Hydorelectricity Investment and Development Company Ltd",
    "Nepal Infrastructure Bank Limited", "Emerging Nepal Limited",
    "NRN Infrastructure and Development Limited", "CEDB Holdings Limited",
    # Life Insurance
    "Asian Life Insurance Co. Limited", "Life Insurance Co. Nepal",
    "Nepal Life Insurance Co. Ltd.", "National Life Insurance Co. Ltd.",
    "Citizen Life Insurance Company Limited", "Reliable Nepal Life Insurance Limited",
    "IME Life Insurance Company Limited", "Sun Nepal Life Insurance Company Limited",
    "SuryaJyoti Life Insurance Company Limited", "Sanima Reliance Life Insurance Limited",
    "Himalayan Life Insurance Limited", "Prabhu Mahalaxmi Life Insurance Limited",
    "Guardian Micro-Life Insurance Limited", "Crest Micro Life Insurance Ltd.",
    # Manufacturing & Processing
    "Bottlers Nepal (Balaju) Limited", "Bottlers Nepal (Terai) Limited",
    "Himalayan Distillery Limited", "Nepal Lube Oil Limited",
    "Unilever Nepal Limited", "Shivam Cements Ltd", "Sarbottam Cement Limited",
    "Reliance Spinning Mills Limited", "Sonapur Minerals and Oil Limited",
    "Om Megashree Pharmaceuticals Limited", "Ghorahi Cement Industry Limited",
    "Sagar Distillery Limited", "Shreenagar Agritech Industries Limited",
    "SY Panel Nepal Limited", "Everest Colour Limited",
    "Sopan Pharmaceuticals Limited", "Palpa Cement Industries Limited",
    # Hydropower
    "Arun Valley Hydropower Development Co. Ltd.", "Butwal Power Company Limited",
    "Chilime Hydropower Company Limited", "National Hydro Power Company Limited",
    "Sanima Mai Hydropower Ltd.", "Himalaya Urja Bikas Company Limited",
    "Arun Kabeli Power Ltd.", "Barun Hydropower Co. Ltd.", "Api Power Company Ltd.",
    "Ngadi Group Power Ltd.", "Mandakini Hydropower Limited", "Nyadi Hydropower Limited",
    "Sanjen Jalavidhyut Company Limited", "Rasuwagadhi Hydropower Company Limited",
    "United Modi Hydropower Ltd.", "Dordi Khola Jal Bidyut Company Limited",
    "Peoples Hydropower Company Limited", "People's Power Limited",
    "Universal Power Company Ltd", "Shuvam Power Company Limited",
    "Synergy Power Development Ltd.", "Mailung Khola Jal Vidhyut Company Limited",
    "Sahas Urja Limited", "Khanikhola Hydropower Co. Ltd.",
    "Himalayan Power Partner Ltd.", "Dibyashwori Hydropower Ltd.",
    "Barahi Hydropower Public Limited", "Mountain Hydro Nepal Limited",
    "Chhyangdi Hydropower Ltd.", "Upper Syange Hydropower Limited",
    "Sayapatri Hydropower Limited", "Nepal Hydro Developers Ltd.",
    "Radhi Bidyut Company Ltd", "Buddhabhumi Nepal Hydropower Company Limited",
    "Rapti Hydro and General Construction Limited", "Kalika power Company Ltd",
    "Sanima Middle Tamor Hydropower Limited", "Ghalemdi Hydro Limited",
    "Eastern Hydropower Limited", "Maya Khola Hydropower Company Limited",
    "Bhugol Energy Development Company Limited", "Panchakanya Mai Hydropower Ltd",
    "Kutheli Bukhari Small Hydropower Limited", "Madhya Bhotekoshi Jalavidyut Company Limited",
    "Greenlife Hydropower Limited", "Upper Solu Hydro Electric Company Limited",
    "Ankhu Khola Jalvidhyut Company Ltd", "Liberty Energy Company Limited",
    "Terhathum Power Company Limited", "Singati Hydro Energy Limited",
    "Panchthar Power Company Limited", "Three Star Hydropower Limited",
    "Shiva Shree Hydropower Limited", "Joshi Hydropower Development Company Ltd",
    "Upper Tamakoshi Hydropower Ltd", "Trishuli Jal Vidhyut Company Limited",
    "Union Hydropower Limited", "Samling Power Company Limited",
    "Swet-Ganga Hydropower & Construction Limited", "Asian Hydropower Limited",
    "Bindyabasini Hydropower Development Company Limited",
    "Himal Dolakha Hydropower Company Limited", "Molung Hydropower Company Limited",
    "Super Mai Hydropower Limited", "River Falls Power Limited",
    "Mountain Energy Nepal Limited", "Upper Hewakhola Hydropower Company Limited",
    "Himalayan Hydropower Limited", "United IDI Mardi RB Hydropower Limited",
    "Sikles Hydropower Limited", "Modi Energy Limited", "Ru Ru Jalbidhyut Pariyojana Limited",
    "Makar Jitumaya Suri Hydropower Limited", "Daramkhola Hydro Energy Limited",
    "Sagarmatha Jalabidhyut Company Limited", "Mai Khola Hydropower Limited",
    "Chirkhwa Hydropower Limited", "Mathillo Mailun Khola Jalvidhyut Limited",
    "Dolti Power Company Limited", "Balephi Hydropower Limited", "Green Ventures Limited",
    "Mid-Solu Hydropower Limited", "Bungal Hydro Limited", "Sanigad Hydro Limited",
    "Kalanga Hydro Limited", "Taksar Pikhuwa Khola Hydropower Limited",
    "Ridi Power Company Limited", "Him Star Urja Company Limited",
    "Manakamana Engineering Hydropower Limited", "Appolo Hydropower Limited",
    "Ingwa Hydropower Limited", "Super Madi Hydropower Limited",
    "Menchhiyam Hydropower Limited", "Kalinchock Hydropower Limited",
    "Bikash Hydropower Company Limited", "Sanvi Energy Limited",
    "Yambaling Hydropower Limited", "Rawa Energy Development Limited",
    "Upper Lohore Khola Hydropower Company Limited",
    "Bhagawati Hydropower Development Company Ltd.", "Mandu Hydropower Ltd.",
    "Mabilung Energy Limited", "Shikhar Power Development Limited",
    "Snow Rivers Limited", "Vision Lumbini Urja Company Limited",
    "Super Khudi Hydropower Limited", "Bhujung Hydropower Limited",
    "Suryakunda Hydro Electric Limited", "Ridge Line Energy Limited",
    "Solu Hydropower Limited",
    # Microfinance
    "Chhimek Laghubitta Bittiya Sanstha Limited", "Deprosc Laghubitta Bittiya Sanstha Limited",
    "First Micro Finance Laghubitta Bittiya Sanstha Limited",
    "Kalika Laghubitta Bittiya Sanstha Limited", "Nirdhan Utthan Laghubitta Bittiya Sanstha Limited",
    "Sana Kisan Bikas Laghubitta Bittiya Sanstha Limited",
    "Swarojgar Laghubitta Bittiya Sanstha Ltd.", "Swabalamban Laghubitta Bittiya Sanstha Limited",
    "Mithila Laghubitta Bittiya Sanstha Ltd.", "Laxmi Laghubitta Bittiya Sanstha Ltd.",
    "Janautthan Samudayic Laghubitta Bittiya Sanstha Limited",
    "Vijaya laghubitta Bittiya Sanstha Ltd.", "RSDC Laghubitta Bittiya Sanstha Ltd.",
    "NMB Laghubitta Bittiya Sanstha Ltd.", "Meromicrofinance Laghubitta Bittiya Sanstha Ltd.",
    "Nadep Laghubitta Bittiya Sanstha Ltd.", "Asha Laghubitta Bittiya Sanstha Limited",
    "National Laghubitta Bittiya Sanstha Limited", "Ganapati Microfinance Bittiya Sanstha Ltd",
    "Himalayan Laghubitta Bittiya Sanstha Limited", "Infinity Laghubitta Bittiya Sanstha Limited",
    "Forward Microfinance Laghubitta Bittiya Sanstha Ltd.",
    "Samata Gharelu Laghubitta Bittiya Sanstha Limited", "Mahuli Laghubitta Bittiya Sanstha Ltd.",
    "Global IME Laghubitta Bittiya Sanstha Ltd.", "Support Laghubitta Bittiya Sanstha Limited",
    "Grameen Bikas Laghubitta Bittiya Sanstha Ltd.",
    "NESDO Sambridha Laghubitta Bittiye Sanstha Limited",
    "Mahila Laghubitta Bittiya Sanstha Limited", "Gurans Laghubitta Bittiya Sanstha Limited",
    "NIC Asia Laghubitta Biitiya Sanstha Limited", "Samudayik Laghubitta Bittiya Sanstha Limited",
    "Unique Nepal Laghubitta Bittiya Sanstha Limited", "Swastik Laghubitta Bittiya Sanstha Limited",
    "Jeevan Bikas Laghubitta Bittiya Sanstha Limited", "Shrijanshil Laghubitta Bittiya Sanstha Limited",
    "Upakar Laghubitta Bittiya Sanstha Limited", "Swabhimaan Laghubitta Bittiya Sanstha Ltd",
    "WEAN Nepal Laghubitta Bittiya Sanstha Limited", "Dhaulagiri Laghubitta Bittiya Sanstha Limited",
    "Aatmanirbhar Laghubitta Bittiya Sanstha Limited", "Manushi Laghubitta Bittiya Sanstha Limited",
    "Aviyan Laghubitta Bittiya Sanstha Limited", "Aarambha Chautari Laghubitta Bittiya Sanstha Limited",
    "Unnati Sahakarya Laghubitta Bittiya Sanstha Limited", "CYC Nepal Laghubitta Bittiya Sanstha Limited",
    "Suryodaya Womi Laghubitta Bittiya Sanstha Limited", "Nerude Mirmire Laghubitta Bittiya Sanstha Limited",
    "Matribhumi Laghubitta Bittiya Sanstha Limited", "Sampada Laghubitta Bittiya Sanstha Limited",
]

# Strong financial signals — checked FIRST, override exclude list
STRONG_KEYWORDS = [
    "नेप्से", "nepse", "शेयर", "सेयर", "आईपीओ", "एफपीओ", "ipo", "fpo",
    "लाभांश", "dividend", "डिम्याट", "हकप्रद", "राष्ट्र बैंक", "nrb",
    "बजेट", "budget", "मर्जर", "merger",
    # Finance/Energy ministers moved here so "मन्त्री" exclude doesn't block them
    "अर्थमन्त्री", "ऊर्जामन्त्री",
] + LISTED_COMPANIES
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
    """Load dedup history. No time-based expiry — an article stays 'seen'
    until it rolls off the HISTORY_MAX_ENTRIES cap (see save_sent_news)."""
    if not os.path.exists(SENT_NEWS_FILE):
        return []
    try:
        with open(SENT_NEWS_FILE, 'r') as f:
            data = json.load(f)
        # Legacy: list of plain URL strings
        if data and isinstance(data[0], str):
            data = [{"link": l, "headline": ""} for l in data]
        return data
    except Exception:
        return []


def save_sent_news(news_list):
    # Cap: never store more than HISTORY_MAX_ENTRIES (oldest fall off first)
    if len(news_list) > HISTORY_MAX_ENTRIES:
        news_list = news_list[-HISTORY_MAX_ENTRIES:]
    with open(SENT_NEWS_FILE, 'w') as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)


def send_to_telegram(text):
    """Send a plain text message (with link) to the Telegram channel.
    Telegram auto-generates a link preview + thumbnail from the article's
    own og:image — no need to build a custom image card."""
    if not TELEGRAM_BOT_TOKEN:
        print("[SKIP] No bot token — message not sent.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        data={
            "chat_id":    TELEGRAM_CHANNEL_ID,
            "text":       text,
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

        try:
            text = (
                f"<b>{_html.escape(news['headline'])}</b>\n\n"
                f"📰 स्रोत: {_html.escape(news['source'])}\n\n"
                f"🔗 {news['link']}"
            )

            sent = send_to_telegram(text)

            if sent or not TELEGRAM_BOT_TOKEN:
                sent_history.append({
                    "link":     news['link'],
                    "headline": news['headline'],
                    "sent_at":  datetime.datetime.now(datetime.timezone.utc).isoformat(),
                })
                sent_this_run.append(news['headline'])
                run_count += 1

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
