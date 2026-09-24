import calendar
import concurrent.futures as cf
import datetime
import re
import socket
import time

import feedparser
import requests
from bs4 import BeautifulSoup

socket.setdefaulttimeout(12)  # feedparser uses urllib internally

MAX_AGE_HOURS = 12  # older articles are never sent (stops old-news replay)

# Every feed below was probed live on 2026-09-24 and returned fresh articles.
# Browser UA: several Nepali sites (NepalPress, BeemaKaKura) block bot UAs.
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'}

RSS_FEEDS = {
    # ── General / National ────────────────────────────────────────────────────
    "OnlineKhabar":      "https://www.onlinekhabar.com/feed",
    "Setopati":          "https://www.setopati.com/feed",
    "Ratopati":          "https://ratopati.com/feed",
    "Baahrakhari":       "https://baahrakhari.com/feed",
    "NagarikNews":       "https://nagariknews.nagariknetwork.com/feed",
    "AnnapurnaPost":     "https://annapurnapost.com/rss",
    "NepalPress":        "https://nepalpress.com/feed/",
    "GorkhapatraOnline": "https://gorkhapatraonline.com/rss",
    "KhabarHub":         "https://www.khabarhub.com/feed",
    "NepalNews":         "https://nepalnews.com/feed",
    "Himalpress":        "https://himalpress.com/feed",
    "Kathmandupress":    "https://kathmandupress.com/feed",
    "HimalKhabar":       "https://www.himalkhabar.com/feed",
    "NepalKhabar":       "https://nepalkhabar.com/feed",
    "Ukeraa":            "https://ukeraa.com/feed",
    "NepalSamaya":       "https://nepalsamaya.com/feed",
    "NewsOfNepal":       "https://newsofnepal.com/feed/",
    "OSNepal":           "https://www.osnepal.com/feed",
    "RajdhaniDaily":     "https://rajdhanidaily.com/feed/",
    "ThahaKhabar":       "https://thahakhabar.com/feed",
    "OnlineTVNepal":     "https://onlinetvnepal.com/feed/",
    "EadarshaSamaj":     "https://www.eadarsha.com/feed",
    "UjyaaloOnline":     "https://ujyaaloonline.com/feed",
    "Lokantar":          "https://lokaantar.com/feed",
    "CorporateNepal":    "https://corporatenepal.com/rss",
    "BBCNepali":         "https://feeds.bbci.co.uk/nepali/rss.xml",
    # ── Tech / Telecom (NTC is listed) ────────────────────────────────────────
    "Techpana":          "https://techpana.com/feed",
    "Clickmandu":        "https://clickmandu.com/feed",
    "ICTSamachar":       "https://ictsamachar.com/rss",
    # ── English-Language ──────────────────────────────────────────────────────
    "KathmanduPost":     "https://kathmandupost.com/rss",
    "MyRepublica":       "https://myrepublica.nagariknetwork.com/feeds",
    "OnlinekhabarEN":    "https://english.onlinekhabar.com/feed",
    "RatopatiEN":        "https://english.ratopati.com/feed",
    "RisingNepal":       "https://risingnepaldaily.com/rss",
    "AnnapurnaExpress":  "https://theannapurnaexpress.com/rss",
    "NepaliTimes":       "https://www.nepalitimes.com/feed/",
    "SpotlightNepal":    "https://www.spotlightnepal.com/feed",
    "PeoplesReview":     "https://www.peoplesreview.com.np/feed/",
    "NewBusinessAge":    "https://www.newbusinessage.com/rss",
    # ── Finance / Economy / Stock Market ──────────────────────────────────────
    "ArthaKhabar":       "https://arthakhabar.com/feed",
    "Arthasarokar":      "https://arthasarokar.com/feed",
    "BankingSamachar":   "https://bankingsamachar.com/feed",
    "Bankingkhabar":     "https://bankingkhabar.com/feed",
    "Bizmandu":          "https://bizmandu.com/feed",
    "Bizkhabar":         "https://bizkhabar.com/feed",
    "Bizpati":           "https://bizpati.com/feed",
    "CapitalNepal":      "https://capitalnepal.com/feed",
    "KarobarDaily":      "https://karobardaily.com/feed",
    "AarthikNews":       "https://aarthiknews.com/rss",
    "Aarthiksansar":     "https://aarthiksansar.com/feed",
    "Arthadabali":       "https://arthadabali.com/feed",
    "Arthapath":         "https://arthapath.com/feed",
    "BajarKoChirfar":    "https://bajarkochirfar.com/feed",
    "BeemaKaKura":       "https://beemakakura.com/?feed=rss2",
}

# Portals that publish only market/economy news → send everything they post
# (still passes the exclude filter). Tighten this set if the channel gets noisy.
FINANCE_SOURCES = {
    "ArthaKhabar", "Arthasarokar", "BankingSamachar", "Bankingkhabar", "Bizmandu",
    "Bizkhabar", "Bizpati", "CapitalNepal", "KarobarDaily", "AarthikNews",
    "Aarthiksansar", "Arthadabali", "Arthapath", "BajarKoChirfar", "BeemaKaKura",
    "NewBusinessAge", "MeroLagani", "BikashNews",
    # ShareSansar deliberately excluded: /category/latest is general site news
    # (world affairs, CSR), not finance-only — it passes the keyword filter instead.
}

UNDATED_MAX = 5  # feeds without pub dates: only trust the newest few entries


def clean_html(raw_html):
    if not raw_html:
        return ""
    return BeautifulSoup(str(raw_html), "html.parser").get_text(separator=" ").strip()


def _entry_ts(entry):
    """UTC epoch seconds of an RSS entry, or None if the feed has no dates."""
    for field in ('published_parsed', 'updated_parsed'):
        t = entry.get(field)
        if t:
            return calendar.timegm(t)  # feedparser structs are UTC; mktime would add local offset
    return None


def _fetch_feed(source, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        feed = feedparser.parse(r.content)
    except Exception as e:
        print(f"[ERROR] RSS {source}: {e}")
        return []
    if not feed.entries:
        print(f"[WARN] No entries from {source}")
        return []
    now, items = time.time(), []
    for i, entry in enumerate(feed.entries):
        ts = _entry_ts(entry)
        if ts is None and i >= UNDATED_MAX:
            break
        if ts is not None and now - ts > MAX_AGE_HOURS * 3600:
            continue
        headline, link = clean_html(entry.get('title', '')), entry.get('link', '')
        if headline and link:
            items.append({"source": source, "headline": headline, "link": link, "ts": ts})
    return items


def get_latest_news_from_rss():
    with cf.ThreadPoolExecutor(16) as ex:
        results = ex.map(lambda kv: _fetch_feed(*kv), RSS_FEEDS.items())
    return [item for batch in results for item in batch]


def _get(url):
    return BeautifulSoup(requests.get(url, headers=HEADERS, timeout=12).content, 'html.parser')


def get_latest_news_from_sharesansar():
    """ShareSansar has no RSS. Article slugs end in -YYYY-MM-DD, used for freshness."""
    try:
        soup, out, seen = _get("https://www.sharesansar.com/category/latest"), [], set()
        cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        for a in soup.select('a[href*="/newsdetail/"]'):
            href, text = a['href'], a.get_text(' ', strip=True)
            m = re.search(r'-(\d{4}-\d{2}-\d{2})$', href)
            if not m or m.group(1) < cutoff or href in seen or len(text) < 20:
                continue
            seen.add(href)
            out.append({"source": "ShareSansar", "headline": text, "link": href, "ts": None})
        return out
    except Exception as e:
        print(f"[ERROR] ShareSansar: {e}")
        return []


def get_latest_news_from_merolagani():
    try:
        soup = _get("https://merolagani.com/NewsList.aspx")
        return [{"source": "MeroLagani", "headline": a.get_text(strip=True),
                 "link": "https://merolagani.com" + a['href'], "ts": None}
                for a in soup.select("h4.media-title a")[:10] if a.get_text(strip=True)]
    except Exception as e:
        print(f"[ERROR] MeroLagani: {e}")
        return []


def get_latest_news_from_bikashnews():
    try:
        soup, results, seen = _get("https://bikashnews.com/"), [], set()
        for a in soup.find_all('a', href=True):
            href, headline = a['href'], a.get_text(strip=True)
            if href.startswith('/story/') and href not in seen and headline:
                seen.add(href)
                results.append({"source": "BikashNews", "headline": headline,
                                "link": "https://bikashnews.com" + href, "ts": None})
                if len(results) >= 10:
                    break
        return results
    except Exception as e:
        print(f"[ERROR] BikashNews: {e}")
        return []


def get_listed_symbols():
    """All NEPSE ticker symbols, fetched live so new listings are covered automatically."""
    try:
        soup = _get("https://merolagani.com/CompanyList.aspx")
        return {a.get_text(strip=True) for a in soup.select('a[href*="CompanyDetail.aspx?symbol="]')
                if re.fullmatch(r'[A-Z]{2,8}', a.get_text(strip=True))}
    except Exception as e:
        print(f"[WARN] Could not fetch NEPSE symbol list: {e}")
        return set()


def get_all_latest_news():
    news = (get_latest_news_from_rss() + get_latest_news_from_sharesansar()
            + get_latest_news_from_merolagani() + get_latest_news_from_bikashnews())
    # Newest first; undated (HTML-scraped) items count as "now".
    now = time.time()
    news.sort(key=lambda n: n['ts'] or now, reverse=True)
    print(f"[INFO] Total articles fetched: {len(news)}")
    return news


if __name__ == "__main__":
    for n in get_all_latest_news():
        print(f"[{n['source']}] {n['headline']}")
