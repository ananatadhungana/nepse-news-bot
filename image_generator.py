import os
import base64
from html2image import Html2Image

def generate_news_image(headline, summary, output_filename="news_update.jpg", logo_path="logo.png", accent_color="#E69603"):
    """
    Generates a professional news image with a white box layout, 
    logo integration, and high-quality Devanagari rendering.
    """
    hti = Html2Image(
        size=(1080, 1080),
        custom_flags=[
            '--no-sandbox',
            '--disable-gpu',
            '--hide-scrollbars',
            '--virtual-time-budget=5000' # Give more time for rendering
        ]
    )
    
    # Encode logo to base64 for embedding in HTML
    logo_base64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="logo">'
    else:
        logo_html = '<div class="logo-placeholder">NEPSE ALERT</div>'

    # Shorten summary to be very concise
    short_summary = summary.split(". ")[0] + "..." if len(summary) > 100 else summary
    if len(short_summary) > 150:
        short_summary = short_summary[:150] + "..."

    # HTML Template with white box layout and dynamic accent color
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
                width: 1000px;
                height: 1000px;
                background-color: #ffffff; /* Plain white box */
                border-radius: 0;
                box-shadow: 0 10px 20px rgba(0,0,0,0.05);
                display: flex;
                flex-direction: column;
                padding: 40px;
                box-sizing: border-box;
                position: relative;
                border: 1px solid #e0e0e0;
            }}
            .header {{
                display: flex;
                flex-direction: column;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid {accent_color};
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
                color: {accent_color};
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
                border-left: 6px solid {accent_color};
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
                background-color: {accent_color};
                color: white;
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
                    <p>{short_summary}</p>
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
    # Test render with a sample headline and summary
    generate_news_image(
        "नेपाल राष्ट्र बैंकले मौद्रिक नीति सार्वजनिक गर्दै, शेयर बजारमा कस्तो प्रभाव पर्ला?", 
        "नेपाल राष्ट्र बैंकले आगामी आर्थिक वर्षको मौद्रिक नीति सार्वजनिक गर्ने तयारी गरिरहेको छ। यसले शेयर बजार, बैंक तथा वित्तीय संस्था र समग्र अर्थतन्त्रमा महत्वपूर्ण प्रभाव पार्ने अपेक्षा गरिएको छ।", 
        "test_render_logo_new.jpg"
    )
    print("Test image created as test_render_logo_new.jpg")
