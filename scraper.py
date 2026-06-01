import feedparser
import requests
from bs4 import BeautifulSoup
import time
import re
from openai import OpenAI
import os

# Initialize OpenAI client
client = OpenAI()

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
    "Baahrakhari": "https://baahrakhari.com/feed",
    "Bikashnews": "https://bikashnews.com/feed",
    "Deshsanchar": "https://deshsanchar.com/feed",
    "Beemakakura": "https://beemakakura.com/feed",
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

def extract_full_text(url):
    """Extracts the main text content from a news article URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        content_div = soup.find('div', class_=re.compile(r'content|article|post-content|entry-content|story-content', re.I))
        if content_div:
            return content_div.get_text(separator=' ', strip=True)
        paragraphs = soup.find_all('p')
        return ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30])
    except:
        return ""

def get_ai_summary(text, headline):
    """Generates a very short, to-the-point summary using AI."""
    if not text or len(text) < 100:
        return text[:200]
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a financial news assistant. Summarize the following Nepali news article into a single, very short, and impactful sentence in Nepali. Focus only on the core fact related to economy, finance, or the stock market."},
                {"role": "user", "content": f"Headline: {headline}\n\nContent: {text[:2000]}"}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI Summarization error: {e}")
        return text[:200] + "..."

def get_all_latest_news():
    """Fetches the latest news from a list of RSS feeds with strict filtering and AI summarization."""
    all_news = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                for entry in feed.entries[:3]: # Check top 3 entries per source
                    headline = clean_html(entry.get('title', ''))
                    link = entry.get('link', '')
                    if headline and link and is_finance_related(headline):
                        print(f"Processing: {headline}")
                        full_text = extract_full_text(link)
                        summary = get_ai_summary(full_text, headline)
                        all_news.append({
                            "source": source,
                            "headline": headline,
                            "link": link,
                            "summary": summary
                        })
        except Exception as e:
            print(f"Error fetching RSS for {source}: {e}")
    return all_news

if __name__ == "__main__":
    print("Testing scraper with AI summarization...")
    news = get_all_latest_news()
    for n in news:
        print(f"[{n['source']}] {n['headline']}\nSummary: {n['summary']}\n")
