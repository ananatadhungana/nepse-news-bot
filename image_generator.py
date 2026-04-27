import os
from html2image import Html2Image

def generate_news_image(headline, summary, output_filename="news_update.jpg"):
    """
    Generates a high-quality JPG image using HTML and CSS for perfect 
    Devanagari rendering and attractive styling.
    """
    hti = Html2Image(size=(1080, 1080))
    # In some environments, we might need to specify browser path, 
    # but html2image is usually good at finding the default browser.
    
    # HTML Template with embedded CSS
    # Pure copper color is #B87333. Let's use a nice gradient of it for premium feel.
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Mukta:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            body {{
                margin: 0;
                padding: 0;
                width: 1080px;
                height: 1080px;
                background: linear-gradient(135deg, #B87333 0%, #8a5322 100%);
                font-family: 'Mukta', sans-serif; /* Excellent font for Devanagari */
                display: flex;
                flex-direction: column;
                box-sizing: border-box;
                padding: 60px;
                color: #ffffff;
            }}
            .header {{
                text-align: center;
                margin-bottom: 50px;
                border-bottom: 3px solid rgba(255, 255, 255, 0.4);
                padding-bottom: 20px;
            }}
            .header span {{
                background-color: rgba(0, 0, 0, 0.2);
                padding: 10px 40px;
                border-radius: 8px;
                font-size: 38px;
                font-weight: 700;
                letter-spacing: 2px;
                text-transform: uppercase;
            }}
            .content {{
                flex-grow: 1;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}
            .headline {{
                font-size: 65px;
                font-weight: 700;
                line-height: 1.4;
                margin-bottom: 50px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }}
            .summary {{
                background-color: rgba(0, 0, 0, 0.15);
                padding: 40px;
                border-radius: 16px;
                border-left: 8px solid #ffffff;
                box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            }}
            .summary p {{
                font-size: 42px;
                font-weight: 400;
                line-height: 1.6;
                margin: 0;
            }}
            .footer {{
                text-align: center;
                font-size: 28px;
                color: rgba(255, 255, 255, 0.7);
                margin-top: auto;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <span>NEWS UPDATE</span>
        </div>
        
        <div class="content">
            <div class="headline">
                {headline}
            </div>
            
            <div class="summary">
                <p>{summary}</p>
            </div>
        </div>
        
        <div class="footer">
            NEPSE Alert News
        </div>
    </body>
    </html>
    """
    
    # Render the image
    hti.screenshot(html_str=html_content, save_as=output_filename)
    
    return output_filename

if __name__ == "__main__":
    generate_news_image("कुष्ठरोगका कारण विवाह बदर हुने कानुनी व्यवस्था खारेज", "सर्वोच्च अदालतको संवैधानिक इजलासले मुलुकी देवानी संहिता ऐन, २०७४ को दफा ७१(२)(ग) मा रहेको कुष्ठरोगसम्बन्धी व्यवस्था खारेज गरेको सर्वोच्च अदालतका प्रवक्ता अर्जुन कोइरालाले जानकारी दिए ।", "test_render.jpg")
    print("Test image created as test_render.jpg")
