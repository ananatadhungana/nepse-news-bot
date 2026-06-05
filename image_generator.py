import os
import base64
from html2image import Html2Image
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

def get_news_image_url(news_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(news_url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]
    except:
        pass
    return "https://images.unsplash.com/photo-1611974714014-40f6950c9a2e?q=80&w=1080&auto=format&fit=crop"

def generate_news_image(headline, summary, output_filename, news_url=None, logo_path="logo.png", accent_color="#E69603"):
    print(f"  [ImageGen] Starting generation for: {headline[:30]}...")
    try:
        # Try html2image first
        print("  [ImageGen] Initializing Html2Image...")
        hti = Html2Image(size=(1080, 1350), custom_flags=['--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--disable-dev-shm-usage'])
        print("  [ImageGen] Html2Image initialized.")
        bg_image_url = get_news_image_url(news_url) if news_url else "https://images.unsplash.com/photo-1611974714014-40f6950c9a2e?q=80&w=1080&auto=format&fit=crop"
        
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
            <style>
                body {{ margin: 0; padding: 0; width: 1080px; height: 1350px; font-family: 'Noto Sans Devanagari', sans-serif; background: #fff; overflow: hidden; }}
                .container {{ position: relative; width: 1080px; height: 1350px; display: flex; flex-direction: column; }}
                .image-section {{ position: relative; width: 1080px; height: 750px; overflow: hidden; }}
                .bg-image {{ width: 100%; height: 100%; object-fit: cover; }}
                .logo-container {{ position: absolute; top: 30px; left: 30px; background: rgba(255,255,255,0.9); padding: 10px 20px; border-radius: 8px; display: flex; align-items: center; }}
                .logo {{ height: 60px; max-width: 300px; object-fit: contain; }}
                .content-section {{ flex: 1; background: #fff; padding: 40px 50px; display: flex; flex-direction: column; position: relative; border-top: 6px solid {accent_color}; }}
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
        print(f"  [ImageGen] Attempting to take screenshot with html2image for {output_filename}...")
        hti.screenshot(html_str=html_content, save_as=output_filename)
        print(f"  [ImageGen] html2image screenshot command executed.")
        print(f"  [ImageGen] Successfully generated image: {output_filename}")
        return output_filename
    except Exception as e:
        print(f"  [ImageGen] html2image failed with exception: {e}")
        import traceback
        traceback.print_exc()

        print(f"  [ImageGen] html2image failed: {e}. Falling back to PIL.")
        try:
            # Fallback to PIL (no browser needed)
            img = Image.new('RGB', (1080, 1350), color=(255, 255, 255))
            d = ImageDraw.Draw(img)
            d.rectangle([0, 0, 1080, 750], fill=(240, 240, 240))
            d.text((50, 800), headline[:50] + "...", fill=(0, 0, 0))
            img.save(output_filename)
            return output_filename
        except Exception as pil_e:
            print(f"  [ImageGen] PIL fallback also failed: {pil_e}")
            return None
