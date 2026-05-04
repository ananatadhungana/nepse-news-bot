import feedparser
import requests
from bs4 import BeautifulSoup
import time
import re

# List of RSS feeds for Nepali news portals
RSS_FEEDS = {
    "OnlineKhabar": "https://www.onlinekhabar.com/feed",
    "Setopati": "https://www.setopati.com/feed",
    "Ratopati": "https://ratopati.com/feed",
    "Bizmandu": "https://bizmandu.com/feed",
    "Ekantipur": "https://ekantipur.com/feed",
    "Arthasarokar": "https://arthasarokar.com/feed",
    "AbhiyanDaily": "https://www.abhiyandaily.com/abhiyanrss",
    "KathmanduPost": "https://kathmandupost.com/rss",
    "TheHimalayanTimes": "https://thehimalayantimes.com/rss",
    "NewsOfNepal": "https://newsofnepal.com/feed",
    "TechPana": "https://techpana.com/feed",
    "BimaPost": "https://bimapost.com/feed",
    "BajarkoChirfar": "https://bajarkochirfar.com/feed",
    "NepalSamacharpatra": "https://newsofnepal.com/category/nepal-samacharpatra/feed",
    "Samaypost": "https://samaypost.com/feed",
    "Diyopost": "https://diyopost.com/feed",
    "Sharesansar": "https://www.sharesansar.com/rss",
    "Nepalipaisa": "https://nepalipaisa.com/feed",
    "Nepsealpha": "https://nepsealpha.com/feed",
    "ArthaSanjal": "https://arthasanjal.com/feed",
    "ArthaSarsar": "https://arthasansar.com/feed",
    "ArthaToday": "https://arthatoday.com/feed",
    "ArthaDainik": "https://arthadainik.com/feed",
    "ArthaBazar": "https://arthabazar.com/feed",
    "Arthatantra": "https://arthatantra.com/feed",
    "AjakoArtha": "https://ajakoartha.com/feed",
}

# Keywords for strict finance/economy filtering
FINANCE_KEYWORDS = [
    "नेप्से", "सेयर", "बजार", "लगानी", "बैंक", "बीमा", "अर्थतन्त्र", "बजेट", "लाभांश", "बोनस", 
    "आईपीओ", "धितोपत्र", "मुद्रा", "ऋण", "ब्याज", "कारोबार", "कम्पनी", "म्युचुअल फण्ड", 
    "NEPSE", "Stock", "Market", "Investment", "Bank", "Insurance", "Economy", "Budget", 
    "Dividend", "Bonus", "IPO", "Securities", "Currency", "Loan", "Interest", "Trading", 
    "Company", "Mutual Fund", "Finance", "Banking", "Fiscal", "Monetary", "Revenue"
]

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ").strip()

def is_finance_related(text):
    """Checks if the text contains any finance-related keywords."""
    if not text:
        return False
    for keyword in FINANCE_KEYWORDS:
        if re.search(rf"\b{keyword}\b", text, re.IGNORECASE) or keyword in text:
            return True
    return False

def get_latest_news_from_rss():
    """Fetches the latest news from a list of RSS feeds with strict filtering."""
    all_news = []
    
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                for entry in feed.entries[:5]: # Check top 5 entries
                    headline = clean_html(entry.get('title', ''))
                    link = entry.get('link', '')
                    summary = clean_html(entry.get('summary', '') or entry.get('description', ''))
                    
                    # Strict filtering: headline or summary must be finance-related
                    if headline and link and (is_finance_related(headline) or is_finance_related(summary)):
                        all_news.append({
                            "source": source,
                            "headline": headline,
                            "link": link,
                            "summary": summary
                        })
        except Exception as e:
            print(f"Error fetching RSS for {source}: {e}")
            
    return all_news

def get_latest_news_from_merolagani():
    """Custom scraper for Merolagani."""
    url = "https://merolagani.com/NewsList.aspx"
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        news_items = soup.select(".media-body h4.media-heading a")
        
        results = []
        for item in news_items[:5]:
            headline = item.text.strip()
            link = "https://merolagani.com" + item['href']
            
            if is_finance_related(headline):
                results.append({
                    "source": "MeroLagani",
                    "headline": headline,
                    "link": link,
                    "summary": "थप जानकारीको लागि लिंकमा क्लिक गर्नुहोस्।"
                })
        return results
    except Exception as e:
        print(f"Error scraping MeroLagani: {e}")
        return []

def get_all_latest_news():
    news = get_latest_news_from_rss()
    news.extend(get_latest_news_from_merolagani())
    return news

if __name__ == "__main__":
    print("Testing scraper with strict filtering...")
    news = get_all_latest_news()
    for n in news:
        print(f"[{n['source']}] {n['headline']}")
