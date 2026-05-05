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
                if isinstance(data, list):
                    return data
                return []
        except:
            return []
    return []

def save_sent_news(news_list):
    if len(news_list) > 300: # Keep a bit more history for better deduplication
        news_list = news_list[-300:]
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
            return response.status_code == 200
    except:
        return False

def send_to_facebook(image_path, headline, link_url):
    """Posts to Facebook Page via Zapier."""
    try:
        # Upload image to get a public URL
        upload_cmd = f"manus-upload-file {image_path}"
        result = subprocess.check_output(upload_cmd, shell=True).decode('utf-8')
        image_url = result.strip()
        
        # Zapier instructions for the agent to handle the tool call
        zapier_input = {
            "app": "Facebook Pages",
            "action": "page_photo",
            "instructions": f"Post this news to my Facebook Page. Message: {headline}. Photo URL: {image_url}. Please also add the link in a comment: {link_url}",
            "output": "Post ID"
        }
        
        zapier_cmd = f"manus-mcp-cli tool call execute_zapier_write_action --server zapier --input '{json.dumps(zapier_input)}'"
        subprocess.run(zapier_cmd, shell=True, check=True)
        return True
    except:
        return False

def is_duplicate(new_headline, new_link, sent_history):
    for sent in sent_history:
        if new_link == sent.get('link'):
            return True
        sent_headline = sent.get('headline', '')
        if sent_headline and new_headline:
            similarity = difflib.SequenceMatcher(None, new_headline, sent_headline).ratio()
            if similarity > 0.75: # Strict deduplication
                return True
    return False

def main():
    print("Starting NEPSE News Agent...")
    sent_history = load_sent_news()
    all_news = get_all_latest_news()
    
    # Process news in reverse (oldest first)
    for news in reversed(all_news):
        if not is_duplicate(news['headline'], news['link'], sent_history):
            print(f"Processing: {news['headline']}")
            try:
                image_filename = f"news_{int(time.time())}.jpg"
                
                # Generate image with professional layout
                generate_news_image(
                    headline=news['headline'],
                    summary=news['summary'],
                    output_filename=image_filename,
                    news_url=news['link'],
                    logo_path=LOGO_PATH
                )
                
                caption = f"<b>{news['headline']}</b>\n\n{news['link']}"
                
                # Send to platforms
                telegram_success = send_to_telegram(image_filename, caption)
                facebook_success = send_to_facebook(image_filename, news['headline'], news['link'])
                
                if telegram_success or facebook_success:
                    sent_history.append({"link": news['link'], "headline": news['headline']})
                    save_sent_news(sent_history)
                    
                    if os.path.exists(image_filename):
                        os.remove(image_filename)
                    time.sleep(10) # Delay to avoid rate limits
            except Exception as e:
                print(f"Error: {e}")
    
    print("Run complete.")

if __name__ == "__main__":
    main()
