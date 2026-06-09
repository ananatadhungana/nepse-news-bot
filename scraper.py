import feedparser
import requests
from bs4 import BeautifulSoup
import re
import socket

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
}

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; NEPSEBot/1.0)'}


def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(str(raw_html), "html.parser")
    return soup.get_text(separator=" ").strip()


def get_og_image(article_url):
    """Scrape og:image from article page as last-resort photo source."""
    try:
        r    = requests.get(article_url, timeout=7, headers=HEADERS)
        soup = BeautifulSoup(r.content, 'html.parser')
        og   = soup.find('meta', property='og:image') or \
               soup.find('meta', attrs={'name': 'og:image'})
        if og:
            src = og.get('content', '').strip()
            if src and src.startswith('http'):
                return src
    except Exception:
        pass
    return None


def extract_image_from_entry(entry):
    """Try multiple locations in an RSS entry to find a photo URL."""

    # 1. media:content (e.g. OnlineKhabar, Setopati)
    media = getattr(entry, 'media_content', None)
    if media and isinstance(media, list):
        for m in media:
            url = m.get('url', '')
            if url and re.search(r'\.(jpg|jpeg|png|webp)', url, re.I):
                return url

    # 2. enclosure
    enclosures = getattr(entry, 'enclosures', [])
    for enc in enclosures:
        url = enc.get('url', '')
        if url and re.search(r'\.(jpg|jpeg|png|webp)', url, re.I):
            return url

    # 3. First <img> inside summary / content HTML
    for field in ('summary', 'content', 'description'):
        raw = ''
        val = getattr(entry, field, None)
        if isinstance(val, list):          # content is a list of dicts
            raw = val[0].get('value', '') if val else ''
        elif isinstance(val, str):
            raw = val
        if raw:
            soup = BeautifulSoup(raw, 'html.parser')
            img = soup.find('img')
            if img:
                src = img.get('src', '')
                if src and not src.endswith('.gif'):
                    return src

    return None


def get_latest_news_from_rss():
    all_news = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                print(f"[WARN] No entries from {source}")
                continue
            for entry in feed.entries[:2]:
                headline = clean_html(entry.get('title', ''))
                link     = entry.get('link', '')
                summary  = clean_html(
                    entry.get('summary', '') or entry.get('description', '')
                )
                photo    = extract_image_from_entry(entry)

                if headline and link:
                    all_news.append({
                        "source":   source,
                        "headline": headline,
                        "link":     link,
                        "summary":  summary or "थप जानकारीको लागि लिंकमा क्लिक गर्नुहोस्।",
                        "photo":    photo,  # None → logo bg used; no per-article HTTP call
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
                # Try to grab thumbnail
                parent  = item.find_parent('.media')
                photo   = None
                if parent:
                    img = parent.find('img')
                    if img:
                        src = img.get('src', '') or img.get('data-src', '')
                        if src and not src.startswith('data:'):
                            photo = ('https://merolagani.com' + src
                                     if src.startswith('/') else src)
                results.append({
                    "source":   "MeroLagani",
                    "headline": headline,
                    "link":     link,
                    "summary":  "थप जानकारीको लागि लिंकमा क्लिक गर्नुहोस्।",
                    "photo":    photo,
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
                # Try sibling/parent img
                photo = None
                parent = a.find_parent()
                if parent:
                    img = parent.find('img')
                    if img:
                        src = img.get('src', '') or img.get('data-src', '')
                        if src and not src.startswith('data:'):
                            photo = ('https://bikashnews.com' + src
                                     if src.startswith('/') else src)
                results.append({
                    "source":   "BikashNews",
                    "headline": headline,
                    "link":     "https://bikashnews.com" + href,
                    "summary":  "थप जानकारीको लागि लिंकमा क्लिक गर्नुहोस्।",
                    "photo":    photo,
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
        print(f"[{n['source']}] {n['headline']} | photo={n['photo']}")
