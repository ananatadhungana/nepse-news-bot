import feedparser
import requests
from bs4 import BeautifulSoup
import time

# List of known RSS feeds for Nepali news portals
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
}

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ").strip()

def get_latest_news_from_rss():
    """Fetches the latest news from a list of RSS feeds."""
    all_news = []
    
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                # Get top 2 latest news from each feed
                for entry in feed.entries[:2]:
                    headline = clean_html(entry.get('title', ''))
                    link = entry.get('link', '')
                    summary = clean_html(entry.get('summary', '') or entry.get('description', ''))
                    
                    if headline and link:
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
    """Custom scraper example for Merolagani which might not have RSS"""
    url = "https://merolagani.com/NewsList.aspx"
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        news_items = soup.select(".media-body h4.media-heading a")
        
        results = []
        for item in news_items[:2]:
            headline = item.text.strip()
            link = "https://merolagani.com" + item['href']
            
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
    print("Testing scraper...")
    news = get_all_latest_news()
    for n in news:
        print(f"[{n['source']}] {n['headline']}")
