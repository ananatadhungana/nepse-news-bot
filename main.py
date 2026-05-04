import os
import json
import requests
import difflib
from scraper import get_all_latest_news
from image_generator import generate_news_image
import time
import subprocess

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8794685716:AAEohtA4mOm1qdKHRhKdrilhrL9r6QWWmf8")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@nepsealertnews")
LOGO_PATH = "logo.png"

SENT_NEWS_FILE = "sent_news.json"

def load_sent_news():
    if os.path.exists(SENT_NEWS_FILE):
        try:
            with open(SENT_NEWS_FILE, 'r') as f:
                data = json.load(f)
                # Ensure data is a list of dictionaries
                if isinstance(data, list):
                    if all(isinstance(item, str) for item in data):
                        return [{"link": link, "headline": ""} for link in data]
                    return data
                return []
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error loading sent_news.json: {e}. Starting with empty history.")
            return []
    return []

def save_sent_news(news_list):
    # Keep only the last 200 items to prevent file from growing too large
    if len(news_list) > 200:
        news_list = news_list[-200:]
    with open(SENT_NEWS_FILE, 'w') as f:
        json.dump(news_list, f, indent=4)

def send_to_telegram(image_path, caption):
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
    Sends the news to Facebook Page using Zapier MCP.
    """
    print(f"Attempting to post to Facebook: {headline}")
    try:
        # Upload image to get a public URL
        upload_cmd = f"manus-upload-file {image_path}"
        result = subprocess.check_output(upload_cmd, shell=True).decode('utf-8')
        image_url = result.strip()
        
        # Prepare Zapier action with explicit parameters
        zapier_input = {
            "app": "Facebook Pages",
            "action": "page_stream",
            "instructions": f"Post this news to my Facebook Page. Message: {headline}. Photo URL: {image_url}. Link: {link_url}",
            "output": "Post ID"
        }
        
        zapier_cmd = f"manus-mcp-cli tool call execute_zapier_write_action --server zapier --input '{json.dumps(zapier_input)}'"
        subprocess.run(zapier_cmd, shell=True, check=True)
        print("Successfully triggered Facebook post via Zapier!")
        return True
    except Exception as e:
        print(f"Error posting to Facebook: {e}")
        return False

def is_duplicate(new_headline, new_link, sent_history):
    for sent in sent_history:
        # Check link match
        if new_link == sent.get('link'):
            return True
        # Check headline similarity
        sent_headline = sent.get('headline', '')
        if sent_headline and new_headline:
            similarity = difflib.SequenceMatcher(None, new_headline, sent_headline).ratio()
            if similarity > 0.8: # Slightly lower threshold for better deduplication
                print(f"Skipping duplicate news: '{new_headline}' (Similarity: {similarity:.2f})")
                return True
    return False

def main():
    print("Starting NEPSE News Agent...")
    sent_history = load_sent_news()
    all_news = get_all_latest_news()
    new_news_found = False
    
    # Process news in reverse order (oldest first) to maintain chronological order in channel
    for news in reversed(all_news):
        if not is_duplicate(news['headline'], news['link'], sent_history):
            print(f"New unique article found: {news['headline']}")
            new_news_found = True
            try:
                image_filename = f"news_{int(time.time())}.jpg"
                logo = LOGO_PATH if os.path.exists(LOGO_PATH) else None
                generate_news_image(news['headline'], news['summary'], image_filename, logo_path=logo)
                
                caption = f"<b>{news['headline']}</b>\n\nस्रोत: {news['source']}\n{news['link']}"
                
                telegram_success = send_to_telegram(image_filename, caption)
                facebook_success = send_to_facebook(image_filename, news['headline'], news['link'])
                
                if telegram_success or facebook_success:
                    sent_history.append({"link": news['link'], "headline": news['headline']})
                    # Save state immediately after each successful post
                    save_sent_news(sent_history)
                    
                    if os.path.exists(image_filename):
                        os.remove(image_filename)
                    time.sleep(5) # Slightly longer delay between posts
            except Exception as e:
                print(f"Error processing news: {e}")
    
    if not new_news_found:
        print("No new articles found.")

if __name__ == "__main__":
    main()
