import os
import json
import requests
import difflib
from scraper import get_all_latest_news
from image_generator import generate_news_image
import time
import subprocess

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "") 
LOGO_PATH = "logo.png" # User should upload this to the repo

SENT_NEWS_FILE = "sent_news.json"

def load_sent_news():
    if os.path.exists(SENT_NEWS_FILE):
        try:
            with open(SENT_NEWS_FILE, 'r') as f:
                data = json.load(f)
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
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("Telegram configuration missing. Skipping Telegram.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    try:
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
    except Exception as e:
        print(f"Error sending to Telegram: {e}")
        return False

def send_to_facebook(image_path, headline, link_url):
    """
    Sends the news to Facebook Page.
    Note: This logic is designed for the Manus environment to execute via Zapier.
    In GitHub Actions, this would require Facebook Graph API setup.
    """
    print(f"Facebook posting triggered for: {headline[:50]}...")
    # The actual posting is handled by the scheduled Manus task using Zapier.
    return True

def is_duplicate(new_headline, new_link, sent_history):
    """Checks if the news was already sent using exact link match or fuzzy headline match."""
    for sent in sent_history:
        if new_link == sent.get('link'):
            return True
        
        sent_headline = sent.get('headline', '')
        if sent_headline and new_headline:
            similarity = difflib.SequenceMatcher(None, new_headline, sent_headline).ratio()
            if similarity > 0.85: 
                print(f"Skipping duplicate news: '{new_headline}' is too similar to '{sent_headline}'")
                return True
    return False

def main():
    print("Starting NEPSE News Agent...")
    
    if not TELEGRAM_BOT_TOKEN:
        print("WARNING: TELEGRAM_BOT_TOKEN is not set.")
    if not TELEGRAM_CHANNEL_ID:
        print("WARNING: TELEGRAM_CHANNEL_ID is not set.")
    
    sent_history = load_sent_news()
    all_news = get_all_latest_news()
    
    new_news_found = False
    
    for news in all_news:
        if not is_duplicate(news['headline'], news['link'], sent_history):
            print(f"New unique article found: {news['headline']}")
            new_news_found = True
            
            try:
                image_filename = f"news_{int(time.time())}.jpg"
                # Use logo if it exists
                logo = LOGO_PATH if os.path.exists(LOGO_PATH) else None
                generate_news_image(news['headline'], news['summary'], image_filename, logo_path=logo)
                
                caption = f"<b>{news['headline']}</b>\n\nस्रोत: {news['source']}\n{news['link']}"
                
                telegram_success = send_to_telegram(image_filename, caption)
                
                # Facebook posting logic
                send_to_facebook(image_filename, news['headline'], news['link'])
                
                if telegram_success or not TELEGRAM_BOT_TOKEN:
                    sent_history.append({"link": news['link'], "headline": news['headline']})
                    
                    # Keep the image if we need it for Facebook posting in this session
                    # Otherwise, cleanup
                    if not os.environ.get("KEEP_IMAGES"):
                        try:
                            if os.path.exists(image_filename):
                                os.remove(image_filename)
                        except:
                            pass
                    
                    time.sleep(3)
            except Exception as e:
                print(f"Error processing news '{news['headline']}': {e}")
    
    if len(sent_history) > 200: # Increased history size
        sent_history = sent_history[-200:]
        
    save_sent_news(sent_history)
    
    if not new_news_found:
        print("No new articles found.")

if __name__ == "__main__":
    main()
