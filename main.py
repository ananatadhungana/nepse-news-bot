import os
import json
import requests
import difflib
from scraper import get_all_latest_news
from image_generator import generate_news_image
import time

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")

SENT_NEWS_FILE = "sent_news.json"

def load_sent_news():
    if os.path.exists(SENT_NEWS_FILE):
        try:
            with open(SENT_NEWS_FILE, 'r') as f:
                data = json.load(f)
                # Handle old format (list of strings) and new format (list of dicts)
                if data and isinstance(data[0], str):
                    return [{"link": link, "headline": ""} for link in data]
                return data
        except Exception:
            return []
    return []

def save_sent_news(news_list):
    with open(SENT_NEWS_FILE, 'w') as f:
        json.dump(news_list, f)

def send_to_telegram(image_path, caption):
    """Sends the generated image and caption to the Telegram Channel."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    with open(image_path, "rb") as image_file:
        files = {"photo": image_file}
        data = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "caption": caption,
            "parse_mode": "HTML"
        }
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            print("Successfully sent to Telegram!")
            return True
        else:
            print(f"Failed to send to Telegram: {response.text}")
            return False

def is_duplicate(new_headline, new_link, sent_history):
    """Checks if the news was already sent using exact link match or fuzzy headline match."""
    for sent in sent_history:
        # Check exact link
        if new_link == sent.get('link'):
            return True
        
        # Check fuzzy headline match (cross-portal duplicate detection)
        sent_headline = sent.get('headline', '')
        if sent_headline and new_headline:
            similarity = difflib.SequenceMatcher(None, new_headline, sent_headline).ratio()
            if similarity > 0.65: # 65% similarity is usually the same news story
                print(f"Skipping duplicate news: '{new_headline}' is too similar to '{sent_headline}'")
                return True
    return False

def main():
    print("Starting NEPSE News Agent...")
    
    if not TELEGRAM_BOT_TOKEN:
        print("WARNING: Telegram Bot Token is not set. The bot will generate images but won't send them.")
    
    sent_history = load_sent_news()
    all_news = get_all_latest_news()
    
    new_news_found = False
    
    # Process ALL news in the batch, not just the first one
    for news in all_news:
        if not is_duplicate(news['headline'], news['link'], sent_history):
            print(f"New unique article found: {news['headline']}")
            new_news_found = True
            
            try:
                image_filename = f"news_{int(os.path.getmtime('.'))}.jpg"
                generate_news_image(news['headline'], news['summary'], image_filename)
                
                caption = f"<b>{news['headline']}</b>\n\nस्रोत: {news['source']}\n{news['link']}"
                
                if send_to_telegram(image_filename, caption) or not TELEGRAM_BOT_TOKEN:
                    # Add to history so we don't send it again
                    sent_history.append({"link": news['link'], "headline": news['headline']})
                    
                    if TELEGRAM_BOT_TOKEN:
                        try:
                            os.remove(image_filename)
                        except:
                            pass
                    
                    # Sleep briefly to avoid hitting Telegram rate limits if sending multiple files
                    time.sleep(3)
            except Exception as e:
                print(f"Error processing news '{news['headline']}': {e}")
    
    # Keep only the last 150 sent records to prevent the file from growing infinitely
    if len(sent_history) > 150:
        sent_history = sent_history[-150:]
        
    save_sent_news(sent_history)
    
    if not new_news_found:
        print("No new articles found.")

if __name__ == "__main__":
    main()
