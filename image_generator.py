import os
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# ── PATHS ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
FONT_DEV_BOLD = os.path.join(SCRIPT_DIR, 'NotoSansDevanagari-Bold.ttf')
FONT_LAT_BOLD = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
LOGO_PATH     = os.path.join(SCRIPT_DIR, 'logo.png')

# ── BRAND COLORS ───────────────────────────────────────────────────────────────
AMBER      = (240, 165,   0)   # brand orange / amber
AMBER_DARK = (190, 120,   0)   # darker amber for last headline line
WHITE      = (255, 255, 255)
DARK       = ( 25,  20,  10)   # near-black headline text
CARD_BG    = (255, 255, 255)   # white card

# ── CANVAS ─────────────────────────────────────────────────────────────────────
W, H = 1080, 1080


def _load_fonts():
    def ttf(path, size):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()
    return {
        'header':   ttf(FONT_LAT_BOLD, 90),   # "NEPSE ALERT"
        'headline': ttf(FONT_DEV_BOLD, 64),    # Nepali news headline
        'pill':     ttf(FONT_DEV_BOLD, 40),    # bottom pill
        'source':   ttf(FONT_LAT_BOLD, 28),    # source name tag
    }


def _get_photo(url):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        return Image.open(BytesIO(r.content)).convert('RGB')
    except Exception as e:
        print(f"[WARN] Photo fetch: {e}")
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


def _paste_logo_watermark(img, card_left, card_top, card_w, card_h, opacity=0.10):
    """Paste logo.png as a faint centered watermark inside the card."""
    if not os.path.exists(LOGO_PATH):
        return
    try:
        wm      = Image.open(LOGO_PATH).convert('RGBA')
        wm_size = int(card_w * 0.80)
        wm      = wm.resize((wm_size, wm_size), Image.LANCZOS)
        r, g, b, a = wm.split()
        a = a.point(lambda x: int(x * opacity))
        wm.putalpha(a)
        wm_x = card_left + (card_w - wm_size) // 2
        wm_y = card_top  + (card_h - wm_size) // 2
        img.paste(wm, (wm_x, wm_y), wm)
    except Exception as e:
        print(f"[WARN] Watermark: {e}")


def generate_news_image(headline, summary, output_filename,
                        photo_url=None, news_url=None, logo_path=None,
                        accent_color=None, source=None):
    """
    NEPSE ALERT card — 1080×1080

    Layout:
      ┌──────────────────────────────────┐  ← AMBER background
      │  NEPSE [●] ALERT  (white bold)  │  ← header
      │  ┌────────────────────────────┐  │
      │  │  [logo watermark faint]    │  │  ← white card
      │  │                            │  │
      │  │     headline text dark     │  │
      │  │                            │  │
      │  │  [AMBER pill — link text]  │  │
      │  └────────────────────────────┘  │
      └──────────────────────────────────┘
    """
    global LOGO_PATH
    if logo_path:
        LOGO_PATH = logo_path

    fnt  = _load_fonts()

    # ── Full amber background ──────────────────────────────────────────────────
    img  = Image.new('RGB', (W, H), AMBER)
    draw = ImageDraw.Draw(img)

    # ── Header: "NEPSE [logo] ALERT" ──────────────────────────────────────────
    HDR_Y      = 24
    LOGO_SM_SZ = 88
    GAP        = 16

    nb = draw.textbbox((0, 0), "NEPSE", font=fnt['header'])
    ab = draw.textbbox((0, 0), "ALERT", font=fnt['header'])
    nw = nb[2] - nb[0]
    aw = ab[2] - ab[0]
    total_hdr  = nw + GAP + LOGO_SM_SZ + GAP + aw
    hdr_start  = (W - total_hdr) // 2

    # Text vertical centering with logo
    txt_offset = (LOGO_SM_SZ - (nb[3] - nb[1])) // 2

    draw.text((hdr_start, HDR_Y + txt_offset), "NEPSE",
              font=fnt['header'], fill=WHITE)
    draw.text((hdr_start + nw + GAP + LOGO_SM_SZ + GAP, HDR_Y + txt_offset),
              "ALERT", font=fnt['header'], fill=WHITE)

    # Small circular logo between words
    logo_hdr_x = hdr_start + nw + GAP
    if os.path.exists(LOGO_PATH):
        try:
            lg = Image.open(LOGO_PATH).convert('RGBA')
            lg = lg.resize((LOGO_SM_SZ, LOGO_SM_SZ), Image.LANCZOS)
            mask = Image.new('L', (LOGO_SM_SZ, LOGO_SM_SZ), 0)
            ImageDraw.Draw(mask).ellipse(
                [(0, 0), (LOGO_SM_SZ, LOGO_SM_SZ)], fill=255)
            img.paste(lg, (logo_hdr_x, HDR_Y), mask)
        except Exception as e:
            print(f"[WARN] Header logo: {e}")

    # ── White card ─────────────────────────────────────────────────────────────
    CARD_MARGIN = 36
    CARD_TOP    = HDR_Y + LOGO_SM_SZ + 22
    CARD_BOTTOM = H - 36
    CARD_LEFT   = CARD_MARGIN
    CARD_RIGHT  = W - CARD_MARGIN
    CARD_W      = CARD_RIGHT - CARD_LEFT
    CARD_H      = CARD_BOTTOM - CARD_TOP
    RADIUS      = 36

    draw.rounded_rectangle(
        [(CARD_LEFT, CARD_TOP), (CARD_RIGHT, CARD_BOTTOM)],
        radius=RADIUS, fill=CARD_BG
    )

    # ── Logo watermark inside card (always) ────────────────────────────────────
    _paste_logo_watermark(img, CARD_LEFT, CARD_TOP, CARD_W, CARD_H, opacity=0.10)
    draw = ImageDraw.Draw(img)

    # ── News photo (optional) — top portion of card ───────────────────────────
    photo = _get_photo(photo_url)
    photo_zone_h = 0
    if photo:
        photo_zone_h = int(CARD_H * 0.46)
        ph_w         = CARD_W - 16
        ph_h         = photo_zone_h - 10
        photo        = _cover_crop(photo, ph_w, ph_h)
        # Rounded-top clipping mask
        pmask = Image.new('L', (ph_w, ph_h), 0)
        pd    = ImageDraw.Draw(pmask)
        pd.rounded_rectangle([(0, 0), (ph_w, ph_h)], radius=26, fill=255)
        pd.rectangle([(0, ph_h - 30), (ph_w, ph_h)], fill=255)  # straight bottom
        img.paste(photo, (CARD_LEFT + 8, CARD_TOP + 8), pmask)
        draw = ImageDraw.Draw(img)

    # ── Headline text ──────────────────────────────────────────────────────────
    PILL_H       = 70
    PILL_MARGIN  = 24
    TEXT_PAD     = 52

    text_top  = CARD_TOP + photo_zone_h + 20
    text_bot  = CARD_BOTTOM - PILL_H - PILL_MARGIN - 18
    text_zone = text_bot - text_top

    max_w  = CARD_W - TEXT_PAD * 2
    lines  = _wrap(headline, fnt['headline'], max_w, draw)[:4]
    line_h = 84
    total  = len(lines) * line_h

    ty = text_top + max(0, (text_zone - total) // 2)

    for i, line in enumerate(lines):
        bb  = draw.textbbox((0, 0), line, font=fnt['headline'])
        lw  = bb[2] - bb[0]
        col = DARK if i < len(lines) - 1 else AMBER_DARK
        draw.text((CARD_LEFT + (CARD_W - lw) // 2, ty),
                  line, font=fnt['headline'], fill=col)
        ty += line_h

    # ── Source tag (top-left of card) ──────────────────────────────────────────
    if source:
        src_text = f"📰 {source}"
        sb = draw.textbbox((0, 0), src_text, font=fnt['source'])
        draw.text(
            (CARD_LEFT + 22, CARD_TOP + 14 + (photo_zone_h if photo else 0)),
            src_text, font=fnt['source'], fill=(140, 100, 0)
        )

    # ── Bottom pill inside card ─────────────────────────────────────────────────
    pill_text = "समाचारको लिंक कमेन्टमा"
    pb = draw.textbbox((0, 0), pill_text, font=fnt['pill'])
    pw = pb[2] - pb[0] + 80
    ph = PILL_H
    px = CARD_LEFT + (CARD_W - pw) // 2
    py = CARD_BOTTOM - ph - PILL_MARGIN

    draw.rounded_rectangle(
        [(px, py), (px + pw, py + ph)],
        radius=35, fill=AMBER
    )
    draw.text(
        (px + 40, py + (ph - (pb[3] - pb[1])) // 2),
        pill_text, font=fnt['pill'], fill=DARK
    )

    # ── Save ───────────────────────────────────────────────────────────────────
    img.save(output_filename, 'JPEG', quality=92, optimize=True)
    print(f"[OK] Saved: {output_filename}")
    return output_filename


def _draw_brand_header(img, draw, fnt):
    """Fallback header — not used in main flow but kept for import compat."""
    pass


if __name__ == "__main__":
    generate_news_image(
        headline="गृहमन्त्रीमा फेरि सुधन गुरुङ फर्कदै, आजै ३बजे शपथ",
        summary="थप जानकारीको लागि लिंकमा क्लिक गर्नुहोस्।",
        output_filename="test_render.jpg",
        photo_url=None,
        source="OnlineKhabar",
    )
    print("Done → test_render.jpg")
