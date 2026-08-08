import feedparser
import requests
from bs4 import BeautifulSoup
import re
import socket
import time as _time

# Global timeout for all network calls (feedparser uses urllib internally)
socket.setdefaulttimeout(10)

# --- RSS FEEDS ---
# 55+ Nepali news & finance portals (2 latest articles each)
RSS_FEEDS = {
    # ── General / National ────────────────────────────────────────────────────
    "OnlineKhabar":      "https://www.onlinekhabar.com/feed",
    "Setopati":          "https://www.setopati.com/feed",
    "Ratopati":          "https://ratopati.com/feed",
    "Ekantipur":         "https://ekantipur.com/feed",
    "Baahrakhari":       "https://baahrakhari.com/feed",
    "DeshSanchar":       "https://deshsanchar.com/feed",
    "NagarikNews":       "https://nagariknews.nagariknetwork.com/feed",
    "MyRepublica":       "https://myrepublica.nagariknetwork.com/feed",
    "AnnapurnaPost":     "https://annapurnapost.com/feed",
    "NepalLiveToday":    "https://nepallivetoday.com/feed",
    "SpotlightNepal":    "https://www.spotlightnepal.com/feed",
    "NepalPress":        "https://nepalpress.com/feed",
    "SajhaPost":         "https://sajhapost.com/feed",
    "KhojKhabar":        "https://www.khojkhabar.com/feed",
    "NepalSandesh":      "https://www.nepalsandesh.com/feed",
    "NayaPatrika":       "https://nayapatrikadaily.com/feed",
    "Lokantar":          "https://lokaantar.com/feed",
    "ThahaKhabar":       "https://thahakhabar.com/feed",
    "NepalSamaya":       "https://nepalsamaya.com/feed",
    "NewsOfNepal":       "https://newsofnepal.com/feed/",
    "NayaPage":          "https://nayapage.com/feed",
    "OSNepal":           "https://www.osnepal.com/feed",
    "RajdhaniDaily":     "https://rajdhanidaily.com/feed/",
    "JanaAastha":        "https://www.janaaastha.com/feed",
    "HamraKura":         "https://hamrakura.com/feed",
    "NepalPress24":      "https://nepalpress24.com/feed",
    "GorkhapatraOnline": "https://gorkhapatraonline.com/feed",
    "News24Nepal":       "https://news24nepal.tv/feed/",
    "OnlineTVNepal":     "https://onlinetvnepal.com/feed/",
    "TelegraphNepal":    "https://www.telegraphnepal.com/feed/",
    "EadarshaSamaj":     "https://www.eadarsha.com/feed",

    # ── English-Language ──────────────────────────────────────────────────────
    "BBCNepali":         "https://feeds.bbci.co.uk/nepali/rss.xml",
    "KathmanduPost":     "https://kathmandupost.com/rss",
    "HimalayanTimes":    "https://thehimalayantimes.com/rss",
    "NepaliTimes":       "https://www.nepalitimes.com/feed/",
    "RisingNepal":       "https://risingnepaldaily.com/feed",
    "AnnapurnaExpress":  "https://theannapurnaexpress.com/feed",
    "KathmanduTribune":  "https://kathmandutribune.com/feed/",
    "PeoplesReview":     "https://www.peoplesreview.com.np/feed/",
    "NewBusinessAge":    "https://www.newbusinessage.com/feed",

    # ── Finance / Economy / Stock Market ──────────────────────────────────────
    "BankingSamachar":   "https://bankingsamachar.com/feed",
    "Bizmandu":          "https://bizmandu.com/feed",
    "BeemaKaKura":       "https://beemakakura.com/?feed=rss2",
    "Arthasarokar":      "https://arthasarokar.com/feed",
    "ArthoSansar":       "https://arthosansar.com/feed",
    "ArthikAbhiyan":     "https://arthikabhiyan.com/feed",
    "AbhiyanDaily":      "https://abhiyandaily.com/abhiyanrss",
    "KarobarDaily":      "https://karobardaily.com/feed",
    "ShareSansar":       "https://www.sharesansar.com/rss",
    "NepalEconomyNews":  "https://nepalecon.net/feed",
    "FinanceNepal":      "https://financenepal.com/feed",
    "CapitalNepal":      "https://capitalnepal.com/feed",
    "InvestmentNepal":   "https://investmentnepal.com/feed",
    "MoneyMandu":        "https://moneymandu.com/feed",
    "NepseTech":         "https://nepsetech.com/feed",
    "BusinessAge":       "https://businessage.com.np/feed",
    "BusinessHimalaya":  "https://businesshimalaya.com/feed",
    "AarthikNews":       "https://aarthiknews.com/feed",
    "Techmandu":         "https://techmandu.com/feed/",
    "UjyaaloOnline":     "https://ujyaaloonline.com/feed",
    "BajarKoChirfar":    "https://bajarkochirfar.com/feed",
}

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; NEPSEBot/1.0)'}


def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(str(raw_html), "html.parser")
    return soup.get_text(separator=" ").strip()


def _entry_age_hours(entry):
    """Return age of RSS entry in hours. Returns 0 (include) if pub_date unparseable."""
    for field in ('published_parsed', 'updated_parsed'):
        t = getattr(entry, field, None)
        if t:
            try:
                return (_time.time() - _time.mktime(t)) / 3600
            except Exception:
                pass
    return 0  # unknown age → include by default (safe)


def get_latest_news_from_rss():
    all_news = []
    for source, url in RSS_FEEDS.items():
        try:
            # Pass User-Agent — some Nepali news sites block the default feedparser UA
            feed = feedparser.parse(url, request_headers=HEADERS)
            if not feed.entries:
                print(f"[WARN] No entries from {source}")
                continue
            for entry in feed.entries[:2]:
                headline = clean_html(entry.get('title', ''))
                link     = entry.get('link', '')

                # Skip articles older than 36 hours (prevents old news replay)
                age_h = _entry_age_hours(entry)
                if age_h > 36:
                    print(f"[SKIP] Old article ({age_h:.0f}h) [{source}]: {headline[:60]}")
                    continue

                summary  = clean_html(
                    entry.get('summary', '') or entry.get('description', '')
                )

                if headline and link:
                    all_news.append({
                        "source":   source,
                        "headline": headline,
                        "link":     link,
                        "summary":  summary or "थप जानकारीको लागि लिंकमा क्लिक गर्नुहोस्।",
                    })
        except Exception as e:
            print(f"[ERROR] RSS {source}: {e}")

    return all_news


def get_latest_news_from_merolagani():
    url = "https://merolagani.com/NewsList.aspx"
    try:
        r = requests.get(url, timeout=10, headers=HEADERS)
        soup = BeautifulSoup(r.content, 'html.parser')
        results = []
        for item in soup.select(".media-body h4.media-heading a")[:2]:
            headline = item.text.strip()
            link     = "https://merolagani.com" + item['href']
            if headline:
                results.append({
                    "source":   "MeroLagani",
                    "headline": headline,
                    "link":     link,
                    "summary":  "थप जानकारीको लागि लिंकमा क्लिक गर्नुहोस्।",
                })
        return results
    except Exception as e:
        print(f"[ERROR] MeroLagani: {e}")
        return []


def get_latest_news_from_bikashnews():
    url = "https://bikashnews.com/"
    try:
        r = requests.get(url, timeout=10, headers=HEADERS)
        soup = BeautifulSoup(r.content, 'html.parser')
        results, seen = [], set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/story/') and href not in seen:
                seen.add(href)
                headline = a.text.strip()
                if not headline:
                    continue
                results.append({
                    "source":   "BikashNews",
                    "headline": headline,
                    "link":     "https://bikashnews.com" + href,
                    "summary":  "थप जानकारीको लागि लिंकमा क्लिक गर्नुहोस्।",
                })
                if len(results) >= 2:
                    break
        return results
    except Exception as e:
        print(f"[ERROR] BikashNews: {e}")
        return []


def get_all_latest_news():
    news = get_latest_news_from_rss()
    news.extend(get_latest_news_from_merolagani())
    news.extend(get_latest_news_from_bikashnews())
    print(f"[INFO] Total articles fetched: {len(news)}")
    return news


if __name__ == "__main__":
    print("Testing scraper...")
    for n in get_all_latest_news():
        print(f"[{n['source']}] {n['headline']}")
