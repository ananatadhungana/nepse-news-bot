import os
import base64
from html2image import Html2Image
import requests
from bs4 import BeautifulSoup

def get_news_image_url(news_url):
    """Attempts to find a representative image from the news article URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(news_url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try OpenGraph image first
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]
            
        # Try Twitter image
        twitter_image = soup.find("meta", name="twitter:image")
        if twitter_image and twitter_image.get("content"):
            return twitter_image["content"]
            
        # Fallback to first large image
        for img in soup.find_all("img"):
            if img.get("src") and ("jpg" in img["src"] or "png" in img["src"]):
                return img["src"]
    except:
        pass
    return "https://images.unsplash.com/photo-1611974714014-40f6950c9a2e?q=80&w=1080&auto=format&fit=crop" # Default finance background

def generate_news_image(headline, summary, output_filename, news_url=None, logo_path="logo.png", accent_color="#E69603"):
    """
    Generates a professional news image inspired by user samples.
    Features: Large background image, white headline area, logo integration.
    """
    hti = Html2Image(size=(1080, 1350), custom_flags=['--no-sandbox', '--disable-gpu', '--hide-scrollbars'])
    
    # Get news image
    bg_image_url = get_news_image_url(news_url) if news_url else "https://images.unsplash.com/photo-1611974714014-40f6950c9a2e?q=80&w=1080&auto=format&fit=crop"
    
    # Encode logo
    logo_base64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="logo">'
    else:
        logo_html = f'<div class="logo-text" style="color:{accent_color}">NEPSE ALERT</div>'

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Mukta:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            body {{ margin: 0; padding: 0; width: 1080px; height: 1350px; font-family: 'Mukta', sans-serif; background: #fff; overflow: hidden; }}
            .container {{ position: relative; width: 1080px; height: 1350px; display: flex; flex-direction: column; }}
            
            .image-section {{ position: relative; width: 1080px; height: 750px; overflow: hidden; }}
            .bg-image {{ width: 100%; height: 100%; object-fit: cover; }}
            .overlay-top {{ position: absolute; top: 0; left: 0; width: 100%; height: 150px; background: linear-gradient(to bottom, rgba(0,0,0,0.5), transparent); }}
            
            .logo-container {{ position: absolute; top: 30px; left: 30px; background: rgba(255,255,255,0.9); padding: 10px 20px; border-radius: 8px; display: flex; align-items: center; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }}
            .logo {{ height: 60px; max-width: 300px; object-fit: contain; }}
            
            .content-section {{ flex: 1; background: #fff; padding: 40px 50px; display: flex; flex-direction: column; position: relative; }}
            .content-section::before {{ content: ''; position: absolute; top: 0; left: 50px; right: 50px; height: 6px; background: {accent_color}; border-radius: 3px; transform: translateY(-50%); }}
            
            .headline {{ font-size: 68px; font-weight: 700; line-height: 1.2; color: #1a1a1a; margin-bottom: 30px; }}
            .summary {{ font-size: 36px; font-weight: 400; line-height: 1.5; color: #444; margin-bottom: 40px; flex-grow: 1; }}
            
            .footer {{ display: flex; justify-content: space-between; align-items: center; padding-top: 20px; border-top: 1px solid #eee; }}
            .link-tag {{ background: {accent_color}; color: #fff; padding: 12px 35px; border-radius: 50px; font-size: 32px; font-weight: 600; }}
            .brand-name {{ font-size: 28px; color: #888; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="image-section">
                <img src="{bg_image_url}" class="bg-image">
                <div class="overlay-top"></div>
                <div class="logo-container">{logo_html}</div>
            </div>
            <div class="content-section">
                <div class="headline">{headline}</div>
                <div class="summary">{summary[:200] + "..." if len(summary) > 200 else summary}</div>
                <div class="footer">
                    <div class="link-tag">समाचारको लिंक कमेन्टमा</div>
                    <div class="brand-name">NEPSE ALERT NEWS</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    hti.screenshot(html_str=html_content, save_as=output_filename)
    return output_filename
