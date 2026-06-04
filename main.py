import os
import json
import requests
import difflib
import time
import traceback
import sys

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
        except Exception as e:
            print(f"Error loading sent news: {e}")
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
            print(f"  [Telegram] Sending photo to {TELEGRAM_CHANNEL_ID}...")
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            with open(image_path, "rb") as image_file:
                files = {"photo": image_file}
                data = {"chat_id": TELEGRAM_CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}
                response = requests.post(url, files=files, data=data, timeout=30)
        else:
            print(f"  [Telegram] Sending text message to {TELEGRAM_CHANNEL_ID}...")
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHANNEL_ID, "text": caption, "parse_mode": "HTML"}
            response = requests.post(url, data=data, timeout=30)
            
        if response.status_code != 200:
            print(f"  [Telegram] API Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"  [Telegram] Request Error: {e}")
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
    print("--- NEPSE News Bot Starting ---")
    print(f"Time: {time.ctime()}")
    
    if not TELEGRAM_BOT_TOKEN:
        print("CRITICAL ERROR: TELEGRAM_BOT_TOKEN is not set.")
        sys.exit(1)
    if not TELEGRAM_CHANNEL_ID:
        print("CRITICAL ERROR: TELEGRAM_CHANNEL_ID is not set.")
        sys.exit(1)

    try:
        # Import scraper here to catch import errors
        from scraper import get_all_latest_news
        from image_generator import generate_news_image
        
        sent_history = load_sent_news()
        print(f"Loaded {len(sent_history)} items from history.")
        
        all_news = get_all_latest_news()
        
        if not all_news:
            print("No news items found by scraper.")
            return

        new_items_count = 0
        for news in reversed(all_news):
            if not is_duplicate(news['headline'], news['link'], sent_history):
                print(f"\n[+] New Item: {news['headline'][:60]}...")
                try:
                    image_filename = f"news_{int(time.time())}.jpg"
                    
                    # Try to generate image
                    image_path = None
                    try:
                        image_path = generate_news_image(
                            headline=news['headline'],
                            summary=news['summary'],
                            output_filename=image_filename,
                            news_url=news['link'],
                            logo_path=LOGO_PATH
                        )
                    except Exception as img_e:
                        print(f"  [!] Image generation failed: {img_e}")
                    
                    caption = f"<b>{news['headline']}</b>\n\n{news['link']}"
                    
                    if send_to_telegram(image_path, caption):
                        sent_history.append({"link": news['link'], "headline": news['headline']})
                        save_sent_news(sent_history)
                        new_items_count += 1
                        print(f"  [✓] Successfully sent.")
                    
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)
                    
                    time.sleep(2) # Avoid hitting rate limits
                except Exception as e:
                    print(f"  [!] Error processing item: {e}")
                    traceback.print_exc()
        
        print(f"\n--- Run Finished. Sent {new_items_count} new items. ---")
        
    except ImportError as ie:
        print(f"CRITICAL ERROR: Missing dependency or module: {ie}")
        sys.exit(1)
    except Exception as e:
        print(f"CRITICAL ERROR in main loop: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
