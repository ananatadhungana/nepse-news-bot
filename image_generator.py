import os
import base64
from html2image import Html2Image

def generate_news_image(headline, summary, output_filename="news_update.jpg", logo_path="logo.png"):
    """
    Generates a professional news image with a white box layout, 
    logo integration, and high-quality Devanagari rendering.
    """
    hti = Html2Image(
        size=(1080, 1080),
        custom_flags=['--no-sandbox', '--disable-gpu', '--hide-scrollbars']
    )
    
    # Encode logo to base64 for embedding in HTML
    logo_base64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="logo">'
    else:
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
                background-color: #f4f4f4;
                font-family: 'Mukta', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                box-sizing: border-box;
            }}
            .container {{
                width: 1000px;
                height: 1000px;
                background-color: #ffffff;
                border-radius: 0;
                display: flex;
                flex-direction: column;
                padding: 40px;
                box-sizing: border-box;
                position: relative;
                border: 1px solid #ddd;
            }}
            .header {{
                display: flex;
                flex-direction: column;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #f0f0f0;
            }}
            .logo {{
                max-height: 250px;
                max-width: 800px;
                object-fit: contain;
                margin-bottom: 10px;
            }}
            .logo-placeholder {{
                font-size: 48px;
                font-weight: 700;
                color: #B87333;
            }}
            .content {{
                flex-grow: 1;
                display: flex;
                flex-direction: column;
                justify-content: center;
                text-align: center;
            }}
            .headline {{
                font-size: 64px;
                font-weight: 700;
                line-height: 1.2;
                color: #000;
                margin-bottom: 30px;
            }}
            .summary {{
                background-color: #f9f9f9;
                padding: 30px;
                border-radius: 10px;
                border: 1px solid #eee;
            }}
            .summary p {{
                font-size: 38px;
                font-weight: 400;
                line-height: 1.4;
                color: #333;
                margin: 0;
            }}
            .footer {{
                margin-top: 30px;
                text-align: center;
                padding-top: 20px;
            }}
            .comment-tag {{
                display: inline-block;
                background-color: #f0f0f0;
                color: #555;
                padding: 10px 30px;
                border-radius: 50px;
                font-size: 32px;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                {logo_html}
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
                <div class="comment-tag">समाचारको लिंक कमेन्टमा</div>
            </div>
        </div>
    </body>
    </html>
    """
    
    hti.screenshot(html_str=html_content, save_as=output_filename)
    return output_filename

if __name__ == "__main__":
    generate_news_image(
        "कुष्ठरोगका कारण विवाह बदर हुने कानुनी व्यवस्था खारेज", 
        "सर्वोच्च अदालतको संवैधानिक इजलासले मुलुकी देवानी संहिता ऐन, २०७४ को दफा ७१(२)(ग) मा रहेको कुष्ठरोगसम्बन्धी व्यवस्था खारेज गरेको छ ।", 
        "test_render_logo.jpg"
    )
    print("Test image created as test_render_logo.jpg")
