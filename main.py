import os
import json
import requests
from scraper import get_all_latest_news
from image_generator import generate_news_image

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "6510168150:AAGuvludhACVN9tzCALs8ijp0dwI4FA4nQU")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@nepsealertnews")

SENT_NEWS_FILE = "sent_news.json"

def load_sent_news():
    if os.path.exists(SENT_NEWS_FILE):
        try:
            with open(SENT_NEWS_FILE, 'r') as f:
                return json.load(f)
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

def main():
    print("Starting NEPSE News Agent...")
    
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("WARNING: Telegram Bot Token is not set. The bot will generate images but won't send them.")
    
    sent_links = load_sent_news()
    all_news = get_all_latest_news()
    
    new_news_found = False
    
    for news in all_news:
        if news['link'] not in sent_links:
            print(f"New article found: {news['headline']}")
            new_news_found = True
            
            image_filename = f"news_{int(os.path.getmtime('.'))}.jpg"
            generate_news_image(news['headline'], news['summary'], image_filename)
            
            caption = f"<b>{news['headline']}</b>\n\nस्रोत: {news['source']}\n{news['link']}"
            
            if send_to_telegram(image_filename, caption) or TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
                sent_links.append(news['link'])
                if TELEGRAM_BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
                    try:
                        os.remove(image_filename)
                    except:
                        pass
                break 
    
    if len(sent_links) > 100:
        sent_links = sent_links[-100:]
        
    save_sent_news(sent_links)
    
    if not new_news_found:
        print("No new articles found.")

if __name__ == "__main__":
    main()
