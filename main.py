import os
import json
import requests
import difflib
from scraper import get_all_latest_news
from image_generator import generate_news_image
import time
import traceback

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")

if TELEGRAM_CHANNEL_ID and not TELEGRAM_CHANNEL_ID.startswith("@") and not TELEGRAM_CHANNEL_ID.startswith("-"):
    TELEGRAM_CHANNEL_ID = f"@{TELEGRAM_CHANNEL_ID}"

LOGO_PATH = "logo.png"
SENT_NEWS_FILE = "sent_news.json"

def load_sent_news():
    if os.path.exists(SENT_NEWS_FILE):
        try:
            with open(SENT_NEWS_FILE, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            return []
    return []

def save_sent_news(news_list):
    try:
        if len(news_list) > 300:
            news_list = news_list[-300:]
        with open(SENT_NEWS_FILE, 'w') as f:
            json.dump(news_list, f, indent=4)
    except Exception as e:
        print(f"Error saving sent news: {e}")

def send_to_telegram(image_path, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("Error: Telegram credentials missing.")
        return False
        
    try:
        if image_path and os.path.exists(image_path):
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            with open(image_path, "rb") as image_file:
                files = {"photo": image_file}
                data = {"chat_id": TELEGRAM_CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}
                response = requests.post(url, files=files, data=data)
        else:
            # Fallback to text-only if image generation failed
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHANNEL_ID, "text": caption, "parse_mode": "HTML"}
            response = requests.post(url, data=data)
            
        if response.status_code != 200:
            print(f"Telegram API Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram Request Error: {e}")
        return False

def is_duplicate(new_headline, new_link, sent_history):
    for sent in sent_history:
        if new_link == sent.get('link'):
            return True
        sent_headline = sent.get('headline', '')
        if sent_headline and new_headline:
            similarity = difflib.SequenceMatcher(None, new_headline, sent_headline).ratio()
            if similarity > 0.8:
                return True
    return False

def main():
    print("Starting NEPSE News Agent...")
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("CRITICAL ERROR: Missing Telegram credentials.")
        return

    try:
        sent_history = load_sent_news()
        all_news = get_all_latest_news()
        
        if not all_news:
            print("No new news found.")
            return

        for news in reversed(all_news):
            if not is_duplicate(news['headline'], news['link'], sent_history):
                print(f"Processing: {news['headline']}")
                try:
                    image_filename = f"news_{int(time.time())}.jpg"
                    
                    # Try to generate image, but don't crash if it fails
                    image_path = generate_news_image(
                        headline=news['headline'],
                        summary=news['summary'],
                        output_filename=image_filename,
                        news_url=news['link'],
                        logo_path=LOGO_PATH
                    )
                    
                    caption = f"<b>{news['headline']}</b>\n\n{news['link']}"
                    
                    if send_to_telegram(image_path, caption):
                        sent_history.append({"link": news['link'], "headline": news['headline']})
                        save_sent_news(sent_history)
                        print(f"Successfully sent: {news['headline']}")
                    
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)
                    time.sleep(2)
                except Exception as e:
                    print(f"Error processing item: {e}")
                    traceback.print_exc()
    except Exception as e:
        print(f"Main loop error: {e}")
        traceback.print_exc()
    
    print("Run complete.")

if __name__ == "__main__":
    main()
