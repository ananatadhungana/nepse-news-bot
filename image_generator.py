import os
from html2image import Html2Image

def generate_news_image(headline, summary, output_filename="news_update.jpg", logo_path=None):
    """
    Generates a professional news image with a white box layout, 
    logo integration, and high-quality Devanagari rendering.
    """
    hti = Html2Image(
        size=(1080, 1080),
        custom_flags=['--no-sandbox', '--disable-gpu', '--hide-scrollbars']
    )
    
    # Handle logo path
    logo_html = ""
    if logo_path and os.path.exists(logo_path):
        # In a real scenario, we'd use a base64 encoded image or a local file path
        # For this environment, we'll assume the logo is accessible
        logo_html = f'<img src="file://{logo_path}" class="logo">'
    else:
        # Fallback if logo is missing
        logo_html = '<div class="logo-placeholder">NEPSE ALERT</div>'

    # HTML Template with white box layout
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
                background-color: #f4f4f4; /* Light gray background */
                font-family: 'Mukta', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                box-sizing: border-box;
            }}
            .container {{
                width: 960px;
                height: 960px;
                background-color: #ffffff; /* Plain white box */
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                display: flex;
                flex-direction: column;
                padding: 60px;
                box-sizing: border-box;
                position: relative;
                border: 1px solid #e0e0e0;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 40px;
                border-bottom: 2px solid #f0f0f0;
                padding-bottom: 20px;
            }}
            .logo {{
                max-height: 80px;
                max-width: 300px;
                object-fit: contain;
            }}
            .logo-placeholder {{
                font-size: 32px;
                font-weight: 700;
                color: #B87333;
                letter-spacing: 1px;
            }}
            .news-tag {{
                background-color: #B87333;
                color: white;
                padding: 8px 20px;
                border-radius: 50px;
                font-size: 24px;
                font-weight: 600;
                text-transform: uppercase;
            }}
            .content {{
                flex-grow: 1;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}
            .headline {{
                font-size: 60px;
                font-weight: 700;
                line-height: 1.3;
                color: #1a1a1a;
                margin-bottom: 40px;
            }}
            .summary {{
                background-color: #f9f9f9;
                padding: 30px;
                border-radius: 12px;
                border-left: 6px solid #B87333;
            }}
            .summary p {{
                font-size: 36px;
                font-weight: 400;
                line-height: 1.5;
                color: #444;
                margin: 0;
            }}
            .footer {{
                margin-top: 40px;
                text-align: center;
                border-top: 1px solid #f0f0f0;
                padding-top: 20px;
            }}
            .footer-text {{
                font-size: 28px;
                color: #888;
                font-weight: 600;
            }}
            .comment-tag {{
                display: inline-block;
                margin-top: 15px;
                background-color: #e8f0fe;
                color: #1a73e8;
                padding: 5px 15px;
                border-radius: 4px;
                font-size: 22px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                {logo_html}
                <div class="news-tag">NEWS UPDATE</div>
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
                <div class="footer-text">NEPSE Alert News</div>
                <div class="comment-tag">समाचारको लिंक कमेन्टमा</div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Render the image
    hti.screenshot(html_str=html_content, save_as=output_filename)
    
    return output_filename

if __name__ == "__main__":
    # Test render
    generate_news_image(
        "कुष्ठरोगका कारण विवाह बदर हुने कानुनी व्यवस्था खारेज", 
        "सर्वोच्च अदालतको संवैधानिक इजलासले मुलुकी देवानी संहिता ऐन, २०७४ को दफा ७१(२)(ग) मा रहेको कुष्ठरोगसम्बन्धी व्यवस्था खारेज गरेको छ ।", 
        "test_render_new.jpg"
    )
    print("Test image created as test_render_new.jpg")
