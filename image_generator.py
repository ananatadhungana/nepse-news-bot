import os
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# ── PATHS ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))

# Devanagari (Nepali text)
FONT_DEV_BOLD = os.path.join(SCRIPT_DIR, 'NotoSansDevanagari-Bold.ttf')
FONT_DEV_REG  = os.path.join(SCRIPT_DIR, 'NotoSansDevanagari-Regular.ttf')

# Latin (English — Poppins ships with the GitHub Actions runner)
FONT_LAT_BOLD = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
FONT_LAT_REG  = '/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf'

LOGO_PATH     = os.path.join(SCRIPT_DIR, 'logo.png')

# ── BRAND COLORS — from NEPSE ALERT logo (amber/gold theme) ───────────────────
AMBER         = (240, 165,   0)   # golden amber (logo bg color)
AMBER_DARK    = (180, 120,   0)   # darker amber for last headline line
DARK_BG       = ( 18,  15,   8)   # near-black content zone
WHITE         = (255, 255, 255)
PILL_BG       = (240, 165,   0)   # amber pill button
PILL_TEXT     = ( 18,  15,   8)   # dark text on pill

# ── CANVAS ─────────────────────────────────────────────────────────────────────
W             = 1080
H             = 1080
PHOTO_H       = 555   # top zone height
SEP_H         = 10    # separator thickness
CONTENT_TOP   = PHOTO_H + SEP_H
PAD           = 60


def _load_fonts():
    def ttf(path, size):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()
    return {
        'headline': ttf(FONT_DEV_BOLD, 66),
        'pill':     ttf(FONT_DEV_BOLD, 40),
        'brand_en': ttf(FONT_LAT_BOLD, 32),
        'tag_en':   ttf(FONT_LAT_BOLD, 28),
        'big_en':   ttf(FONT_LAT_BOLD, 80),
    }


def _get_photo(url):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        return Image.open(BytesIO(r.content)).convert('RGB')
    except Exception as e:
        print(f"[WARN] Photo: {e}")
        return None


def _cover_crop(img, tw, th):
    s      = max(tw / img.width, th / img.height)
    nw, nh = int(img.width * s), int(img.height * s)
    img    = img.resize((nw, nh), Image.LANCZOS)
    l, t   = (nw - tw) // 2, (nh - th) // 2
    return img.crop((l, t, l + tw, t + th))


def _wrap(text, font, max_w, draw):
    if not text:
        return []
    words, lines, cur = text.split(), [], []
    for w in words:
        cur.append(w)
        if draw.textbbox((0, 0), ' '.join(cur), font=font)[2] > max_w:
            if len(cur) > 1:
                cur.pop(); lines.append(' '.join(cur)); cur = [w]
            else:
                lines.append(' '.join(cur)); cur = []
    if cur:
        lines.append(' '.join(cur))
    return lines


def _draw_logo_tag(img, draw, fnt):
    """Logo in top-right corner."""
    lx, ly = W - 120, 16
    if os.path.exists(LOGO_PATH):
        try:
            logo = Image.open(LOGO_PATH).convert('RGBA')
            logo = logo.resize((104, 104), Image.LANCZOS)
            bg   = Image.new('RGBA', (112, 112), (0, 0, 0, 140))
            img.paste(bg,   (lx - 4, ly - 4), bg)
            img.paste(logo, (lx, ly), logo)
            return
        except Exception as e:
            print(f"[WARN] Logo tag: {e}")
    # Fallback amber text tag
    tw, th = 108, 72
    tx, ty = W - tw - 16, 16
    draw.rounded_rectangle([(tx, ty), (tx+tw, ty+th)], radius=10, fill=AMBER)
    for i, line in enumerate(["NEPSE", "ALERT"]):
        bb = draw.textbbox((0, 0), line, font=fnt['tag_en'])
        lw = bb[2] - bb[0]
        draw.text((tx + (tw - lw) // 2, ty + 6 + i * 30),
                  line, font=fnt['tag_en'], fill=DARK_BG)


def generate_news_image(headline, summary, output_filename,
                        photo_url=None, news_url=None, logo_path=None,
                        accent_color=None):
    """
    NEPSE ALERT NEWS — amber-gold branded card  1080x1080

    WITH photo:  news photo fills top half
    NO photo:    logo.png fills entire canvas as background (dark overlay added)
    Both cases:  amber separator bar, dark content zone, no website URL
    """
    global LOGO_PATH
    if logo_path:
        LOGO_PATH = logo_path

    fnt  = _load_fonts()
    img  = Image.new('RGB', (W, H), DARK_BG)
    draw = ImageDraw.Draw(img)

    # ── TOP ZONE (photo or logo background) ───────────────────────────────────
    photo = _get_photo(photo_url)
    if photo:
        # News photo — cover-crop into top half only
        photo = _cover_crop(photo, W, PHOTO_H)
        img.paste(photo, (0, 0))
    else:
        # No photo → use logo.png as full-canvas background + dark overlay
        if os.path.exists(LOGO_PATH):
            try:
                bg = Image.open(LOGO_PATH).convert('RGBA')
                bg = _cover_crop(bg, W, H)
                # Convert to RGB and paste as base
                img.paste(bg.convert('RGB'), (0, 0))
                # Dark overlay so text is readable
                overlay     = Image.new('RGBA', (W, H), (18, 15, 8, 195))
                overlay_rgb = Image.new('RGB',  (W, H), (18, 15, 8))
                overlay_msk = Image.new('L',    (W, H), 195)
                img.paste(overlay_rgb, (0, 0), overlay_msk)
            except Exception as e:
                print(f"[WARN] Logo BG: {e}")
                _draw_brand_header(img, draw, fnt)
        else:
            _draw_brand_header(img, draw, fnt)

    # ── LOGO TAG top-right ─────────────────────────────────────────────────────
    _draw_logo_tag(img, draw, fnt)

    # ── AMBER SEPARATOR ────────────────────────────────────────────────────────
    draw = ImageDraw.Draw(img)   # refresh after pastes
    draw.rectangle([(0, PHOTO_H), (W, PHOTO_H + SEP_H)], fill=AMBER)

    # ── CONTENT ZONE dark fill ─────────────────────────────────────────────────
    content_rgb = Image.new('RGB', (W, H - CONTENT_TOP), (18, 15, 8))
    content_msk = Image.new('L',   (W, H - CONTENT_TOP), 225)
    img.paste(content_rgb, (0, CONTENT_TOP), content_msk)
    draw = ImageDraw.Draw(img)

    # ── HEADLINE ───────────────────────────────────────────────────────────────
    max_w     = W - PAD * 2
    lines     = _wrap(headline, fnt['headline'], max_w, draw)[:4]
    line_h    = 82
    total_txt = len(lines) * line_h
    avail     = (H - CONTENT_TOP) - 170
    y         = CONTENT_TOP + (avail - total_txt) // 2 - 10

    for i, line in enumerate(lines):
        bb  = draw.textbbox((0, 0), line, font=fnt['headline'])
        lw  = bb[2] - bb[0]
        col = AMBER if i < len(lines) - 1 else AMBER_DARK
        draw.text(((W - lw) // 2, y), line, font=fnt['headline'], fill=col)
        y  += line_h

    # ── "समाचारको लिंक कमेन्टमा" PILL ─────────────────────────────────────────
    pill_text = "समाचारको लिंक कमेन्टमा"
    pb   = draw.textbbox((0, 0), pill_text, font=fnt['pill'])
    pw   = pb[2] - pb[0] + 80
    ph   = 66
    px   = (W - pw) // 2
    py   = y + 36

    draw.rounded_rectangle([(px, py), (px + pw, py + ph)],
                            radius=33, fill=PILL_BG)
    draw.text((px + 40, py + (ph - (pb[3] - pb[1])) // 2),
              pill_text, font=fnt['pill'], fill=PILL_TEXT)

    # ── BOTTOM BAR — brand name only (no website URL) ─────────────────────────
    bar_y = H - 52
    draw.line([(PAD, bar_y - 14), (W - PAD, bar_y - 14)],
              fill=(60, 48, 10), width=1)
    draw.text((PAD, bar_y), "NEPSE ALERT NEWS",
              font=fnt['brand_en'], fill=WHITE)

    # ── SAVE ───────────────────────────────────────────────────────────────────
    img.save(output_filename, 'JPEG', quality=92, optimize=True)
    print(f"[OK] Saved: {output_filename}")
    return output_filename


def _draw_brand_header(img, draw, fnt):
    """Fallback no-logo header with amber accents."""
    draw.rectangle([(0, 0), (W, 6)], fill=AMBER)
    for txt, ypos, col in [("NEPSE ALERT", 150, AMBER), ("NEWS", 250, WHITE)]:
        bb = draw.textbbox((0, 0), txt, font=fnt['big_en'])
        lw = bb[2] - bb[0]
        draw.text(((W - lw) // 2, ypos), txt, font=fnt['big_en'], fill=col)
    draw.rectangle([(PAD, PHOTO_H - 40), (W//2 - 160, PHOTO_H - 34)], fill=AMBER)
    draw.rectangle([(W//2 + 160, PHOTO_H - 40), (W - PAD, PHOTO_H - 34)], fill=AMBER)


if __name__ == "__main__":
    generate_news_image(
        headline="नेप्से परिसूचक ३ सय बिन्दुले घट्यो, लगानीकर्ता चिन्तित",
        summary="थप जानकारीको लागि लिंकमा क्लिक गर्नुहोस्।",
        output_filename="test_render.jpg",
        photo_url=None,
    )
    print("Done → test_render.jpg")
