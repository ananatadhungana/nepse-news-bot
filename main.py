import os
import json
import requests
import difflib
import re
import datetime
import html as _html
from scraper import get_all_latest_news, get_listed_symbols
import time

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
SENT_NEWS_FILE      = "sent_news.json"
MAX_PER_RUN         = 6     # max articles per 5-min run; the rest go next run
HISTORY_MAX_ENTRIES = 1500  # dedup memory size — NOT time-based anymore.
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
    "म्युचुअल फन्ड", "mutual fund",
    "किताब बन्द", "book close",
    "मर्जर", "merger", "acquisition",
    "जलविद्युत", "hydropower", "नेपाल विद्युत प्राधिकरण", "NEA",
    "सुनचाँदी", "सुनको मूल्य", "विदेशी मुद्रा सञ्चिति", "forex reserve",
    "कर्जा", "loan", "खुद नाफा", "net profit",
    # ── Banking / Monetary ──
    "बैंक", "bank", "banking", "बैंकिङ",
    "राष्ट्र बैंक", "नेपाल राष्ट्र बैंक", "nrb",
    "ब्याजदर", "बेस रेट", "interest rate",
    "तरलता", "liquidity",
    "निक्षेप", "deposit",
    "मौद्रिक नीति", "monetary policy",
    "लघुवित्त", "microfinance",
    "वित्त कम्पनी", "development bank", "डेभलपमेन्ट बैंक",
    # ── Insurance ──
    "बीमा", "बीमा कम्पनी", "जीवन बीमा", "insurance",
    # ── Economy / Budget ──
    "बजेट वक्तव्य", "बजेट भाषण", "बजेट कार्यान्वयन", "बजेटको आकार", "budget speech",
    "जिडिपी", "gdp",
    "मुद्रास्फीति", "महँगी", "inflation",
    "विप्रेषण", "रेमिट्यान्स", "remittance",
    "व्यापार घाटा", "trade deficit",
    # bare "आयात"/"निर्यात"/"import"/"export" removed: matched ANY country's
    # trade news globally (e.g. "US import ban on Canadian alcohol"). The
    # Nepal-specific compound "व्यापार घाटा"/"trade deficit" above still covers it.
    "fiscal policy", "राजकोषीय",
    # ── Key political roles (only when economy-impacting) ──
    "बजेट अधिवेशन", "बजेट पेश",
    # "अध्यादेश"/"ordinance" removed: matched ANY government-ordinance story,
    # political or not (e.g. an MP's dissatisfaction with ordinance policy).
    # ── Hydro / Energy (major NEPSE sector) ──
    # ── Telecom (NEPSE listed) ──
    "नेपाल टेलिकम", "nepal telecom", "ntc",
    # ── Cement / Manufacturing (NEPSE listed) ──
    "सिमेन्ट कम्पनी", "cement company",
    # ── Broad business stems ──
    # "होटल"/"व्यवसाय"/"व्यापार" removed: too generic, matched any hotel or
    # "business" story anywhere (a Nepali opening a hotel in the US, a Dashain
    # idol-decoration "business" writeup) with no NEPSE/company connection.
]


# WEAK: generic economy words. ONE alone is not enough — they appear in crime
# ("गाँजा कारोबार"), foreign news ("Trump ... investment"), politics ("सरकार
# गठन") etc. Need 2 DIFFERENT weak hits (or any CORE/STRONG hit) to send.
WEAK_KEYWORDS = [
    "कारोबार", "लगानी", "पुँजी", "कम्पनी", "उद्योग", "नाफा", "मुनाफा",
    "भन्सार", "राजस्व", "विदेशी मुद्रा", "अर्थतन्त्र", "आर्थिक", "ऋण",
    "विद्युत", "हाइड्रो", "टेलिकम", "फाइनान्स", "सिमेन्ट", "सूचकांक", "दलाल",
    "लिस्टिङ", "निजी क्षेत्र", "उद्योगी", "बजेट", "budget",
    "company", "investment", "profit", "industry", "revenue", "economic",
    "economy", "credit", "index", "broker", "listing", "forex", "market",
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
    "पक्राउ", "ठगी", "फरार", "गाँजा", "लागुऔषध", "तस्करी", "प्रहरी",
    "पीडित", "victims", "survivors",
    # Foreign politics / leaders (no direct Nepal-market link)
    "ट्रम्प", "trump", "अलास्का", "alaska",
    # Party politics
    "महामन्त्री", "general secretary", "महाधिवेशन", "कांग्रेस", "एमाले", "माओवादी",
    "राशिफल", "horoscope",
    "रसिया", "युक्रेन", "russia", "ukraine", "इजरायल", "israel", "भारतीय बजार",
    "party", "पार्टी",
    # Weather forecast chatter (routine "today's weather" — no economic signal).
    # Earthquake/flood/landslide EVENTS moved to DISASTER_KEYWORDS below: a
    # national disaster disrupting highways/hydropower/trade is economic news,
    # not noise, and blanket-excluding these words was hiding exactly that.
    "मौसम", "हिमपात",
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

def _kw_re(words):
    """Latin words get word boundaries (+ optional plural) so "nea" can't hit
    "Nearly"; Devanagari stays substring (suffixes like -को/-मा attach)."""
    parts = []
    for k in words:
        e = re.escape(k.strip())
        parts.append(rf'(?<![A-Za-z]){e}(?:s|es)?(?![A-Za-z])' if re.search('[A-Za-z]', k) else e)
    return re.compile('|'.join(parts), re.IGNORECASE)


_INCLUDE_RE = _kw_re(RELEVANT_KEYWORDS)
_WEAK_RE    = _kw_re(WEAK_KEYWORDS)
_EXCLUDE_RE = _kw_re(EXCLUDE_KEYWORDS)

# Short names people actually write in headlines (Nepali + English brands),
# plus market-infrastructure terms. Any hit = always send (overrides exclude).
COMPANY_KEYWORDS = [
    # Banks
    "नबिल", "एनआईसी एशिया", "एनआईसी एसिया", "सिटिजन्स", "ग्लोबल आईएमई", "ग्लोबल आइएमई",
    "प्रभु बैंक", "कुमारी बैंक", "लक्ष्मी सनराइज", "सिद्धार्थ बैंक", "सानिमा", "एनएमबी",
    "नेपाल बैंक", "कृषि विकास बैंक", "एभरेष्ट बैंक", "एभरेस्ट बैंक", "हिमालयन बैंक",
    "माछापुच्छ्रे", "प्राइम कमर्सियल", "स्ट्यान्डर्ड चार्टर्ड", "स्ट्याण्डर्ड चार्टर्ड",
    "एसबीआई बैंक", "इन्भेष्टमेन्ट मेगा", "इन्भेस्टमेन्ट मेगा", "पूर्वाधार बैंक",
    "मुक्तिनाथ", "गरिमा विकास", "ज्योति विकास", "कामना सेवा", "महालक्ष्मी", "लुम्बिनी विकास",
    "शाइन रेसुंगा", "सांग्रिला",
    # Telecom / hydro / insurance / others
    "टेलिकम", "टेलिकमको", "एनटीसी", "telecom",
    "चिलिमे", "तामाकोशी", "बुटवल पावर", "अरुण भ्याली", "सान्जेन", "रसुवागढी", "भोटेकोशी",
    "हाइड्रोइलेक्ट्रिसिटी इन्भेस्टमेन्ट", "नेपाल लाइफ", "नेसनल लाइफ", "रिइन्स्योरेन्स",
    "पुनर्बीमा", "नागरिक लगानी कोष", "युनिलिभर", "सोल्टी", "शिवम सिमेन्ट", "साल्ट ट्रेडिङ",
    # Market infrastructure & corporate actions
    "सेबोन", "धितोपत्र", "सीडीएससी", "मेरोसेयर", "मेरो सेयर", "स्टक एक्सचेन्ज",
    "मर्चेन्ट बैंकर", "ब्रोकर", "सूचीकरण", "साधारण सभा", "बुक क्लोज", "ऋणपत्र", "डिबेन्चर",
    "चुक्ता पुँजी", "बोनस", "नगद लाभांश", "प्राथमिक सेयर", "सर्वसाधारण", "खुद नाफा", "त्रैमासिक",
    "sebon", "cdsc", "debenture", "bonus share", "stock exchange",
]

# National disasters with real economic/infrastructure impact — earthquake,
# flood, landslide cutting highways, damaging hydropower or bridges. These
# override EXCLUDE (see note above) because "national disaster affecting the
# economy" is explicitly in scope, not filler weather chatter.
# Bare "बाढी"/"पहिरो"/"flood"/"landslide" removed: Nepal gets dozens of routine,
# single-house-scale landslide/flood reports every monsoon week (e.g. "One
# injured as dry landslide buries house in Parbat") — not national disasters.
# भूकम्प/earthquake stays bare since it's rare enough to always be significant.
# Everything else here requires an actual INFRASTRUCTURE/ECONOMY-disruption
# phrase, which is what distinguishes a national event from a local one.
DISASTER_KEYWORDS = [
    "भूकम्प गयो", "भूकम्पको धक्का", "शक्तिशाली भूकम्प", "रेक्टर स्केल",
    "earthquake hits", "earthquake strikes", "earthquake jolts", "magnitude",
    "राजमार्ग अवरुद्ध", "सडक अवरुद्ध", "यातायात अवरुद्ध", "यातायात बन्द",
    "यातायात आवागमन बन्द", "सवारी आवागमन बन्द",
    "पुल भत्कियो", "पुल बगियो", "पुल क्षतिग्रस्त", "पुल डुब्यो", "पुल भासियो",
    "राष्ट्रिय विपद्", "विपद् व्यवस्थापन", "प्राकृतिक प्रकोप",
    "highway blocked", "highways blocked", "highways closed", "highway closed",
    "roads blocked", "road blocked", "bridge collapsed", "bridge washed away",
    "traffic disrupted", "national disaster", "remain closed", "remain blocked",
    "obstructed",
]

# Strong financial signals — checked FIRST, override exclude list
STRONG_KEYWORDS = [
    "नेप्से", "nepse", "शेयर", "सेयर", "आईपीओ", "एफपीओ", "ipo", "fpo",
    "लाभांश", "dividend", "डिम्याट", "हकप्रद", "राष्ट्र बैंक", "nrb",
    "बजेट वक्तव्य", "बजेट पेश", "budget speech", "मर्जर", "merger",
    # Finance/Energy ministers moved here so "मन्त्री" exclude doesn't block them
    "अर्थमन्त्री", "ऊर्जामन्त्री",
] + COMPANY_KEYWORDS + DISASTER_KEYWORDS
_STRONG_RE = _kw_re(STRONG_KEYWORDS)

# NEPSE tickers (NTC, NABIL, CHCL...) — fetched live, matched case-sensitive as
# whole words. Lookarounds instead of \b: Devanagari counts as \w, so "NTCको"
# would fail \b. Denylist = tickers that are also common English words/acronyms.
TICKER_DENYLIST = {"API", "CITY", "MEN", "UPPER", "MEL", "BBC", "PURE", "NIL", "TTL"}


def build_ticker_re(symbols):
    symbols = sorted(set(symbols) - TICKER_DENYLIST, key=len, reverse=True)
    if not symbols:
        return None
    return re.compile(r'(?<![A-Za-z0-9])(?:' + '|'.join(map(re.escape, symbols)) + r')(?![A-Za-z0-9])')


# Corporate PR/CSR donation announcements ("Uber pledges Rs 50 lakh for flood
# relief") — checked BEFORE STRONG, because bare disaster words like "flood"
# are in DISASTER_KEYWORDS/STRONG and would otherwise wave these through.
# A company doing a marketing campaign around a disaster isn't NEPSE news.
PRE_EXCLUDE_KEYWORDS = [
    "pledges rs", "pledges npr", "donates rs", "donates npr", " csr ",
    "launches campaign", "launches ride for",
    # Hard never-market topics — even if a STRONG word appears (horoscope
    # mentions "शेयर", party "merger", Ukraine "पुल क्षतिग्रस्त").
    "राशिफल", "horoscope",
    "रसिया", "युक्रेन", "russia", "ukraine", "इजरायल", "israel", "ट्रम्प", "trump",
    "गाँजा", "लागुऔषध", "ठगी",
    "कांग्रेस", "एमाले", "माओवादी", "samajwadi", "समाजवादी", "political party",
    "महाधिवेशन", "general secretary",
]
_PRE_EXCLUDE_RE = _kw_re(PRE_EXCLUDE_KEYWORDS)


def is_relevant(news, ticker_re=None):
    """
    Send if (headline only — summaries are too noisy):
      0. CSR/PR pattern (e.g. brand "pledges Rs X" for a cause) → never
      1. STRONG keyword or a NEPSE ticker → always
      2. EXCLUDE keyword → never
      3. CORE keyword → yes; or 2+ different WEAK keywords → yes
      (no blanket "finance-only source" bypass — see note on FINANCE_SOURCES
      removal above; STRONG/INCLUDE already give full "every penny" coverage)
    """
    headline = news.get('headline', '')
    if _PRE_EXCLUDE_RE.search(headline):
        print(f"[FILTER] Excluded (hard): {headline[:70]}")
        return False
    if _STRONG_RE.search(headline) or (ticker_re and ticker_re.search(headline)):
        return True
    if _EXCLUDE_RE.search(headline):
        print(f"[FILTER] Excluded (off-topic): {headline[:70]}")
        return False
    if _INCLUDE_RE.search(headline):
        return True
    if len({m.group(0).lower() for m in _WEAK_RE.finditer(headline)}) >= 2:
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


_SUFFIXES = ("हरूलाई", "हरूको", "हरू", "द्वारा", "लाई", "बाट", "सँग", "मा", "को", "का", "की", "ले", "ने")
_STOP = {"र", "तथा", "पनि", "गर्न", "गर्दै", "गर्ने", "भयो", "छ", "हो", "लागि", "the", "and", "for", "of", "in", "to", "a", "on",
         # finance words present in nearly every headline — sharing them proves nothing
         "बैंक", "राष्ट्र", "नेप्से", "nepse", "nrb", "bank", "सुन", "मूल्य", "तोला", "तोलामा", "सेयर", "शेयर",
         "कम्पनी", "अर्ब", "करोड", "लाख", "प्रतिशत", "percent", "billion", "million", "points", "अंक", "अंकले",
         "बढ्यो", "घट्यो", "rises", "falls", "price", "rate"}
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def _numbers(h):
    return set(re.findall(r'\d+(?:\.\d+)?', h.translate(_DEV_DIGITS)))


def _diff_numbers(h1, h2):
    """Both carry figures and share none → different reports (today's vs yesterday's
    gold price / NEPSE close), even if the wording is nearly identical."""
    n1, n2 = _numbers(h1), _numbers(h2)
    return bool(n1 and n2 and not (n1 & n2))


def _tokens(h):
    """Content words with Nepali case suffixes stripped, so 'व्यवसायीले' == 'व्यवसायी'."""
    out = set()
    for w in re.findall(r'[\w\u0900-\u097F]+', h.lower()):
        for suf in _SUFFIXES:
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[:-len(suf)]
                break
        if len(w) >= 3 and w not in _STOP:
            out.add(w)
    return out


def _token_dup(h1, h2):
    """Same story, reworded by another portal: 3+ shared content words making up
    ≥50% of the shorter headline. Catches 'चितवनका व्यवसायीले भेटे रवि लामिछाने,
    नारायणगढ बजार जोगाउन माग' vs 'नारायणगढ बजार जोगाउन माग गर्दै चितवनका व्यवसायी…'."""
    a, b = _tokens(h1), _tokens(h2)
    if not a or not b:
        return False
    if _diff_numbers(h1, h2):
        return False
    shared = len(a & b)
    return shared >= 3 and shared / min(len(a), len(b)) >= 0.5


DUP_WINDOW_HOURS = 48  # token-overlap only vs recent news — old stories on same place/topic are new events


def is_duplicate(headline, link, history):
    """
    Exact link match → duplicate.
    Fuzzy headline ≥0.65 → duplicate (catches cross-portal reposts).
    Longest common block ≥12 chars + ratio ≥0.45 → same event (different wording).
    """
    if link in {s.get('link') for s in history}:  # cheap exact check before fuzzy loop
        return True
    for sent in history:
        sent_h = sent.get('headline', '')
        if sent_h and headline:
            if _diff_numbers(headline, sent_h):
                continue
            m = difflib.SequenceMatcher(None, headline, sent_h)
            ratio = m.ratio()
            if ratio > 0.65:
                print(f"[SKIP] Near-duplicate: '{headline[:60]}…'")
                return True
            longest = max((b.size for b in m.get_matching_blocks()), default=0)
            if longest >= 12 and ratio > 0.45:
                print(f"[SKIP] Same-event (cross-run): '{headline[:60]}…'")
                return True
            if _recent(sent) and _token_dup(headline, sent_h):
                print(f"[SKIP] Same-story (word overlap): '{headline[:60]}…'")
                return True
    return False


def _recent(sent):
    try:
        t = datetime.datetime.fromisoformat(sent.get('sent_at', ''))
    except ValueError:
        return True
    return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() < DUP_WINDOW_HOURS * 3600


def _same_event(h1, h2):
    """
    True if two headlines describe the same event.
    Uses fuzzy match AND checks for shared key person/entity name (first 6 chars).
    Catches: 'महावीर पुन मन्त्री' vs 'महावीर पुनलाई मन्त्री' from different portals.
    """
    # Reuse one SequenceMatcher for both ratio() and get_matching_blocks()
    if _diff_numbers(h1, h2):
        return False
    matcher = difflib.SequenceMatcher(None, h1, h2)
    ratio   = matcher.ratio()
    if ratio > 0.72:
        return True
    # Moderate similarity: check shared long substring (12+ chars = same subject)
    blocks  = matcher.get_matching_blocks()
    longest = max((b.size for b in blocks), default=0)
    if longest >= 12 and ratio > 0.50:
        return True
    return _token_dup(h1, h2)


def main():
    print("=== NEPSE News Agent starting ===")

    sent_history   = load_sent_news()
    ticker_re      = build_ticker_re(get_listed_symbols())
    all_news       = get_all_latest_news()
    new_found      = False
    sent_this_run  = []   # headlines sent THIS run (for same-event cross-portal dedup)
    run_count      = 0    # articles sent this run

    for news in all_news:
        if run_count >= MAX_PER_RUN:
            print(f"[INFO] MAX_PER_RUN ({MAX_PER_RUN}) reached — stopping.")
            break
        # ── Relevance gate ──
        if not is_relevant(news, ticker_re):
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
