import os
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH  = os.path.join(SCRIPT_DIR, 'logo.png')

_DEV_PATHS = [
    os.path.join(SCRIPT_DIR, 'NotoSansDevanagari-Bold.ttf'),
    '/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf',
    '/usr/share/fonts/truetype/noto/NotoSansDevanagari[wdth,wght].ttf',
    '/usr/share/fonts/noto/NotoSansDevanagari-Bold.ttf',
    '/usr/share/fonts/truetype/fonts-noto-core/NotoSansDevanagari-Bold.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansDevanagari-Bold.ttf',
]
_LAT_PATHS = [
    os.path.join(SCRIPT_DIR, 'Poppins-Bold.ttf'),
    '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf',
    '/usr/share/fonts/truetype/poppins/Poppins-Bold.ttf',
]

AMBER_TOP  = (240, 165,   0)
AMBER_BOT  = (185, 110,   0)
AMBER_PILL = (170, 105,   0)
WHITE      = (255, 255, 255)
GREEN_DARK = ( 15,  55,  15)
RED_ACCENT = (145,  15,  15)

W, H = 1080, 1080


def _ttf(candidates, size):
    # Also search system font dirs dynamically
    import glob
    extra = glob.glob('/usr/share/fonts/**/*Devanagari*Bold*.ttf', recursive=True) + \
            glob.glob('/usr/share/fonts/**/*Devanagari*Bold*.otf', recursive=True)
    all_paths = candidates + [p for p in extra if p not in candidates]
    for path in all_paths:
        if os.path.exists(path):
            try:
                f = ImageFont.truetype(path, size)
                print(f"[FONT] {path} @ {size}pt")
                return f
            except Exception:
                continue
    print(f"[WARN] Font not found — fallback")
    return ImageFont.load_default(size)


def _load_fonts():
    return {
        'header':   _ttf(_LAT_PATHS, 90),
        'headline': _ttf(_DEV_PATHS, 72),
        'pill':     _ttf(_DEV_PATHS, 38),
    }


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


def generate_news_image(headline, summary, output_filename,
                        photo_url=None, news_url=None, logo_path=None,
                        accent_color=None, source=None):
    global LOGO_PATH
    if logo_path:
        LOGO_PATH = logo_path

    fnt = _load_fonts()

    # ── Step 1: Amber gradient background (flat RGB) ───────────────────────────
    bg = Image.new('RGB', (W, H))
    draw = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / (H - 1)
        r = int(AMBER_TOP[0] + (AMBER_BOT[0] - AMBER_TOP[0]) * t)
        g = int(AMBER_TOP[1] + (AMBER_BOT[1] - AMBER_TOP[1]) * t)
        b = int(AMBER_TOP[2] + (AMBER_BOT[2] - AMBER_TOP[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ── Step 2: Header "NEPSE [logo] ALERT" ───────────────────────────────────
    HDR_Y   = 26
    LOGO_SM = 82
    GAP     = 12

    nb = draw.textbbox((0, 0), "NEPSE", font=fnt['header'])
    ab = draw.textbbox((0, 0), "ALERT", font=fnt['header'])
    nw, aw = nb[2] - nb[0], ab[2] - ab[0]
    total_hdr = nw + GAP + LOGO_SM + GAP + aw
    hdr_x     = (W - total_hdr) // 2
    t_off     = (LOGO_SM - (nb[3] - nb[1])) // 2

    draw.text((hdr_x, HDR_Y + t_off), "NEPSE", font=fnt['header'], fill=WHITE)
    draw.text((hdr_x + nw + GAP + LOGO_SM + GAP, HDR_Y + t_off),
              "ALERT", font=fnt['header'], fill=WHITE)

    if os.path.exists(LOGO_PATH):
        try:
            lg   = Image.open(LOGO_PATH).convert('RGBA')
            lg   = lg.resize((LOGO_SM, LOGO_SM), Image.LANCZOS)
            mask = Image.new('L', (LOGO_SM, LOGO_SM), 0)
            ImageDraw.Draw(mask).ellipse([(0, 0), (LOGO_SM, LOGO_SM)], fill=255)
            bg.paste(lg.convert('RGB'), (hdr_x + nw + GAP, HDR_Y), mask)
        except Exception as e:
            print(f"[WARN] Header logo: {e}")

    # ── Step 3: White semi-transparent card via RGBA composite ─────────────────
    CM    = 38
    C_TOP = HDR_Y + LOGO_SM + 50    # clear gap below header
    C_BOT = H - 40
    C_L   = CM
    C_R   = W - CM
    C_W   = C_R - C_L
    C_H   = C_BOT - C_TOP

    # Convert bg to RGBA, draw card as semi-transparent white
    img = bg.convert('RGBA')
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle(
        [(C_L, C_TOP), (C_R, C_BOT)],
        radius=36,
        fill=(255, 255, 255, 165)   # ~65% opacity
    )
    img = Image.alpha_composite(img, overlay)

    # ── Step 4: Logo watermark centered inside card ────────────────────────────
    # Logo has solid amber bg → must remove it before use as watermark.
    # Strategy: any pixel close to amber (#F0A500 ±40) → set alpha=0 (transparent).
    if os.path.exists(LOGO_PATH):
        try:
            wm      = Image.open(LOGO_PATH).convert('RGBA')
            wm_size = int(C_W * 0.78)
            wm      = wm.resize((wm_size, wm_size), Image.LANCZOS)
            pixels  = wm.load()
            for py in range(wm.height):
                for px in range(wm.width):
                    r2, g2, b2, a2 = pixels[px, py]
                    # Detect amber/orange background (high R, mid G, low B)
                    if r2 > 180 and g2 > 100 and b2 < 80 and g2 < r2:
                        pixels[px, py] = (r2, g2, b2, 0)   # transparent
            r, g, b, a = wm.split()
            a = a.point(lambda x: int(x * 0.14))   # 14% opacity — subtle watermark
            wm.putalpha(a)
            wm_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            wx = C_L + (C_W - wm_size) // 2
            wy = C_TOP + (C_H - wm_size) // 2
            wm_layer.paste(wm, (wx, wy), wm)
            img = Image.alpha_composite(img, wm_layer)
        except Exception as e:
            print(f"[WARN] Watermark: {e}")

    draw = ImageDraw.Draw(img)

    # ── Step 5: Headline text (vertically centered in card above pill) ─────────
    PILL_H   = 70
    PILL_GAP = 30
    PAD      = 46

    text_top  = C_TOP + 30
    text_bot  = C_BOT - PILL_H - PILL_GAP - 16
    text_zone = text_bot - text_top

    max_w = C_W - PAD * 2
    lines = _wrap(headline, fnt['headline'], max_w, draw)[:4]
    lh    = int(fnt['headline'].size * 1.38)
    total = len(lines) * lh
    ty    = text_top + max(0, (text_zone - total) // 2)

    for i, line in enumerate(lines):
        bb  = draw.textbbox((0, 0), line, font=fnt['headline'])
        lw  = bb[2] - bb[0]
        col = RED_ACCENT if i == len(lines) - 1 else GREEN_DARK
        draw.text((C_L + (C_W - lw) // 2, ty), line, font=fnt['headline'], fill=col)
        ty += lh

    # ── Step 6: Amber bottom bar (full width inside card) covers TRADE THE TREND
    pill_text = "समाचारको लिंक कमेन्टमा"
    pb  = draw.textbbox((0, 0), pill_text, font=fnt['pill'])
    ph  = 110                       # tall enough to fully cover TRADE THE TREND
    # Full card width bar with rounded bottom corners only
    bar_y = C_BOT - ph
    # Draw amber rectangle covering bottom of card
    draw.rectangle([(C_L + 2, bar_y), (C_R - 2, C_BOT - 2)], fill=AMBER_PILL)
    # Round only the bottom corners by overdrawing rounded rect
    draw.rounded_rectangle([(C_L + 2, bar_y), (C_R - 2, C_BOT - 2)],
                            radius=34, fill=AMBER_PILL)
    # Center text in bar
    tw = pb[2] - pb[0]
    th = pb[3] - pb[1]
    draw.text(((W - tw) // 2, bar_y + (ph - th) // 2),
              pill_text, font=fnt['pill'], fill=WHITE)

    # ── Save ───────────────────────────────────────────────────────────────────
    img.convert('RGB').save(output_filename, 'JPEG', quality=92, optimize=True)
    print(f"[OK] {output_filename}")
    return output_filename


if __name__ == "__main__":
    generate_news_image(
        headline="मोबाइल बैंकिङबाटै बिना धितो १० लाखसम्म ऋण लिन सिकने !",
        summary="",
        output_filename="test_render.jpg",
    )
    print("Done → test_render.jpg")
