import os
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH  = os.path.join(SCRIPT_DIR, 'logo.png')

_DEV_PATHS = [
    os.path.join(SCRIPT_DIR, 'NotoSansDevanagari-Bold.ttf'),
    os.path.join(SCRIPT_DIR, 'NotoSansDevanagari-Regular.ttf'),
    '/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf',
    '/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf',
    '/usr/share/fonts/truetype/noto/NotoSansDevanagari[wdth,wght].ttf',
    '/usr/share/fonts/noto/NotoSansDevanagari-Bold.ttf',
    '/usr/share/fonts/noto/NotoSansDevanagari-Regular.ttf',
    '/usr/share/fonts/truetype/fonts-noto-core/NotoSansDevanagari-Bold.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansDevanagari-Bold.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf',
]
_LAT_PATHS = [
    os.path.join(SCRIPT_DIR, 'Poppins-Bold.ttf'),
    '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf',
    '/usr/share/fonts/truetype/poppins/Poppins-Bold.ttf',
]

# ── Palette ───────────────────────────────────────────────────────────────────
AMBER_TOP  = (248, 175,  10)   # bright warm amber
AMBER_BOT  = (165,  90,   0)   # deep bronze
AMBER_PILL = (155,  90,   0)   # dark amber bar
AMBER_GLOW = (255, 190,  30)   # bright glow amber
WHITE      = (255, 255, 255)
CARD_WHITE = (255, 254, 252)   # near-white card
GREEN_DARK = ( 15,  52,  15)
RED_ACCENT = (130,  10,  10)

W, H = 1080, 1080


def _ttf(candidates, size):
    import glob
    # Bold first, then any Devanagari (Regular beats load_default for Devanagari glyphs)
    extra = (
        glob.glob('/usr/share/fonts/**/*Devanagari*Bold*.ttf', recursive=True) +
        glob.glob('/usr/share/fonts/**/*Devanagari*Bold*.otf', recursive=True) +
        glob.glob('/usr/share/fonts/**/*Devanagari*.ttf',      recursive=True) +
        glob.glob('/usr/share/fonts/**/*Devanagari*.otf',      recursive=True)
    )
    all_paths = candidates + [p for p in extra if p not in candidates]
    for path in all_paths:
        if os.path.exists(path):
            try:
                f = ImageFont.truetype(path, size)
                print(f"[FONT] {path} @ {size}pt")
                return f
            except Exception:
                continue
    print(f"[WARN] Font not found — fallback to default (Devanagari will not render)")
    return ImageFont.load_default(size)


def _load_fonts():
    return {
        'header':   _ttf(_LAT_PATHS, 90),
        'headline': _ttf(_DEV_PATHS, 74),
        'pill':     _ttf(_DEV_PATHS, 38),
        'badge':    _ttf(_LAT_PATHS, 32),   # Latin font for source badge
    }


def _wrap(text, font, max_w, draw):
    if not text:
        return []
    words, lines, cur = text.split(), [], []
    for w in words:
        cur.append(w)
        bb = draw.textbbox((0, 0), ' '.join(cur), font=font)
        # Use bb[2]-bb[0] (visual width) — Devanagari has non-zero left bearing
        # so bb[2] alone overestimates width → premature wrapping → card too tall
        if bb[2] - bb[0] > max_w:
            if len(cur) > 1:
                cur.pop(); lines.append(' '.join(cur)); cur = [w]
            else:
                lines.append(' '.join(cur)); cur = []
    if cur:
        lines.append(' '.join(cur))
    # Merge orphaned last line only if:
    #   1. last line is visually short (< 30% of max_w), AND
    #   2. the merged line still fits within max_w
    # NOTE: never use len() for Devanagari — "निषेध" = 5 code points but is a full word
    if len(lines) >= 2:
        bb_last   = draw.textbbox((0, 0), lines[-1], font=font)
        last_w    = bb_last[2] - bb_last[0]
        if last_w < max_w * 0.35:
            merged  = lines[-2] + ' ' + lines[-1]
            bb_m    = draw.textbbox((0, 0), merged, font=font)
            if bb_m[2] - bb_m[0] <= max_w:
                lines[-2] = merged
                lines.pop()
    return lines


def _glow_rect(canvas_ref, rect, radius, color, layers=12, max_spread=28):
    """Simulate glow by drawing multiple expanding semi-transparent rounded rects.
    canvas_ref is a list [image] so we can reassign in-place."""
    x1, y1, x2, y2 = rect
    for i in range(layers, 0, -1):
        spread = int(max_spread * (i / layers))
        alpha  = int(55 * ((layers - i + 1) / layers) ** 1.6)
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ov).rounded_rectangle(
            [(x1 - spread, y1 - spread), (x2 + spread, y2 + spread)],
            radius=radius + spread,
            fill=(*color, alpha)
        )
        canvas_ref[0] = Image.alpha_composite(canvas_ref[0], ov)


def _text_shadow(draw, pos, text, font, shadow_col, offset=(3, 4), alpha_img=None):
    """Draw a drop-shadow for text."""
    if alpha_img is None:
        draw.text((pos[0]+offset[0], pos[1]+offset[1]), text, font=font, fill=(*shadow_col, 90))
        return
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pos[0]+offset[0], pos[1]+offset[1]), text, font=font,
                             fill=(*shadow_col, 80))
    alpha_img[:] = Image.alpha_composite(alpha_img, sh)


def generate_news_image(headline, summary, output_filename,
                        photo_url=None, news_url=None, logo_path=None,
                        accent_color=None, source=None):
    global LOGO_PATH, H
    if logo_path:
        LOGO_PATH = logo_path

    fnt = _load_fonts()

    # ── Pre-compute dynamic image height from headline line count ─────────────
    # Card top is fixed: HDR_Y(26) + LOGO_SM(82) + gap(46) = 154
    _H_C_TOP  = 26 + 82 + 46
    _H_C_W    = W - 36 * 2            # 1008 (card width with margins)
    _H_max_w  = _H_C_W - 40 * 2       # 928  (headline wrap width)
    _H_draw   = ImageDraw.Draw(Image.new('RGBA', (W, 1080)))
    _H_lines  = _wrap(headline, fnt['headline'], _H_max_w, _H_draw)[:4]
    _H_lh     = int(fnt['headline'].size * 1.42)
    _H_htotal = len(_H_lines) * _H_lh
    # 18=accent strip, 48=zone_pad, 4+22=top rule, h_total, 22+4=bot rule, 30=bot_pad, 110=pill
    _H_needed = 18 + 48 + 4 + 22 + _H_htotal + 22 + 4 + 30 + 110
    _H_cardh  = max(420, _H_needed)
    H = max(800, min(1080, _H_C_TOP + _H_cardh + 80))
    # ─────────────────────────────────────────────────────────────────────────

    # ── Step 1: Amber gradient background ────────────────────────────────────
    bg = Image.new('RGB', (W, H))
    draw = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / (H - 1)
        t2 = t * t * (3 - 2 * t)   # smooth-step
        r = int(AMBER_TOP[0] + (AMBER_BOT[0] - AMBER_TOP[0]) * t2)
        g = int(AMBER_TOP[1] + (AMBER_BOT[1] - AMBER_TOP[1]) * t2)
        b = int(AMBER_TOP[2] + (AMBER_BOT[2] - AMBER_TOP[2]) * t2)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Subtle radial highlight in upper-center (adds 3D depth to background)
    for i in range(30, 0, -1):
        rr = i * 14
        alpha = int(18 * (i / 30))
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ov).ellipse(
            [(W//2 - rr, -rr//2), (W//2 + rr, rr)],
            fill=(255, 220, 80, alpha)
        )
        bg = Image.alpha_composite(bg.convert('RGBA'), ov).convert('RGB')

    # ── Step 2: Header "NEPSE [logo] ALERT" with glow ────────────────────────
    HDR_Y   = 26
    LOGO_SM = 82
    GAP     = 12

    nb = draw.textbbox((0, 0), "NEPSE", font=fnt['header'])
    ab = draw.textbbox((0, 0), "ALERT", font=fnt['header'])
    nw, aw = nb[2] - nb[0], ab[2] - ab[0]
    total_hdr = nw + GAP + LOGO_SM + GAP + aw
    hdr_x     = (W - total_hdr) // 2
    t_off     = (LOGO_SM - (nb[3] - nb[1])) // 2

    # Glow behind header text (amber halo)
    bg_rgba = bg.convert('RGBA')
    for gi in range(8, 0, -1):
        gsh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(gsh)
        gdraw.text((hdr_x - gi, HDR_Y + t_off - gi//2), "NEPSE",
                   font=fnt['header'], fill=(255, 200, 50, int(35*(gi/8))))
        gdraw.text((hdr_x + nw + GAP + LOGO_SM + GAP - gi,
                    HDR_Y + t_off - gi//2), "ALERT",
                   font=fnt['header'], fill=(255, 200, 50, int(35*(gi/8))))
        bg_rgba = Image.alpha_composite(bg_rgba, gsh)

    # Draw crisp white header text
    draw2 = ImageDraw.Draw(bg_rgba)
    draw2.text((hdr_x, HDR_Y + t_off), "NEPSE", font=fnt['header'], fill=WHITE)
    draw2.text((hdr_x + nw + GAP + LOGO_SM + GAP, HDR_Y + t_off),
               "ALERT", font=fnt['header'], fill=WHITE)

    # Header logo (crop center 66% to remove text ring)
    if os.path.exists(LOGO_PATH):
        try:
            lg_src = Image.open(LOGO_PATH).convert('RGBA')
            sz = lg_src.width
            trim = int(sz * 0.17)
            lg_src = lg_src.crop((trim, trim, sz - trim, sz - trim))
            lg   = lg_src.resize((LOGO_SM, LOGO_SM), Image.LANCZOS)
            mask = Image.new('L', (LOGO_SM, LOGO_SM), 0)
            ImageDraw.Draw(mask).ellipse([(0, 0), (LOGO_SM, LOGO_SM)], fill=255)
            bg_rgba.paste(lg.convert('RGB'), (hdr_x + nw + GAP, HDR_Y), mask)
        except Exception as e:
            print(f"[WARN] Header logo: {e}")

    # ── Step 3: Card geometry — C_BOT is content-driven ─────────────────────
    CM    = 36
    C_TOP = HDR_Y + LOGO_SM + 46
    C_L   = CM
    C_R   = W - CM
    C_W   = C_R - C_L

    # Pre-compute headline block height to size the card
    _PAD_PRE  = 40
    _max_w    = C_W - _PAD_PRE * 2
    _lines    = _wrap(headline, fnt['headline'], _max_w, ImageDraw.Draw(Image.new('RGBA', (W, H))))[:4]
    _lh       = int(fnt['headline'].size * 1.42)
    _h_total  = len(_lines) * _lh
    _RULE_H   = 4
    _RULE_GAP = 22
    _PILL_H   = 110
    _ZONE_PAD = 48   # fixed top pad inside card before top rule
    _BOT_PAD  = 30   # bottom pad between bottom rule and bar
    _MIN_CARD = 420  # minimum card height regardless of content

    _needed = 18 + _ZONE_PAD + _RULE_H + _RULE_GAP + _h_total + _RULE_GAP + _RULE_H + _BOT_PAD + _PILL_H
    C_BOT = C_TOP + max(_MIN_CARD, _needed)
    C_H   = C_BOT - C_TOP

    # ── Step 3a: Amber glow ring around card (3D illumination effect) ─────────
    ref = [bg_rgba]
    _glow_rect(ref, (C_L, C_TOP, C_R, C_BOT),
               radius=36, color=AMBER_GLOW, layers=14, max_spread=32)
    bg_rgba = ref[0]

    # ── Step 3b: 3D layered shadow (warm bottom-right shadow) ─────────────────
    for i in range(10, 0, -1):
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            [(C_L + i*2, C_TOP + i*2 + 4), (C_R + i*2, C_BOT + i*2 + 4)],
            radius=36, fill=(80, 40, 0, int(28 * (i / 10)))
        )
        bg_rgba = Image.alpha_composite(bg_rgba, sh)

    # ── Step 3c: Solid white card ─────────────────────────────────────────────
    card_ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(card_ov).rounded_rectangle(
        [(C_L, C_TOP), (C_R, C_BOT)],
        radius=36,
        fill=(*CARD_WHITE, 252)
    )
    bg_rgba = Image.alpha_composite(bg_rgba, card_ov)

    # ── Step 3d: Top highlight edge (simulates 3D light from above) ───────────
    hl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # Bright white line at very top of card
    ImageDraw.Draw(hl).rounded_rectangle(
        [(C_L + 2, C_TOP), (C_R - 2, C_TOP + 5)],
        radius=3, fill=(255, 255, 255, 220)
    )
    # Softer secondary highlight below
    ImageDraw.Draw(hl).rounded_rectangle(
        [(C_L + 8, C_TOP + 5), (C_R - 8, C_TOP + 12)],
        radius=2, fill=(255, 255, 255, 80)
    )
    bg_rgba = Image.alpha_composite(bg_rgba, hl)

    # Thin amber accent top strip (just below highlight)
    acc = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(acc).rectangle(
        [(C_L + 3, C_TOP + 13), (C_R - 3, C_TOP + 17)],
        fill=(*AMBER_GLOW, 160)
    )
    bg_rgba = Image.alpha_composite(bg_rgba, acc)

    # ── Step 4: Logo watermark ────────────────────────────────────────────────
    if os.path.exists(LOGO_PATH):
        try:
            wm      = Image.open(LOGO_PATH).convert('RGBA')
            wm_size = int(C_W * 0.78)
            wm      = wm.resize((wm_size, wm_size), Image.LANCZOS)
            pixels  = wm.load()
            for py in range(wm.height):
                for px in range(wm.width):
                    r2, g2, b2, a2 = pixels[px, py]
                    if r2 > 180 and g2 > 100 and b2 < 80 and g2 < r2:
                        pixels[px, py] = (r2, g2, b2, 0)
            r, g, b, a = wm.split()
            a = a.point(lambda x: int(x * 0.07))
            wm.putalpha(a)
            wm_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            wx = C_L + (C_W - wm_size) // 2
            wy = C_TOP + (C_H - wm_size) // 2
            wm_layer.paste(wm, (wx, wy), wm)
            bg_rgba = Image.alpha_composite(bg_rgba, wm_layer)
        except Exception as e:
            print(f"[WARN] Watermark: {e}")

    img = bg_rgba
    draw = ImageDraw.Draw(img)

    # ── Step 5a: Source badge — overlaps top edge of card ────────────────────
    BADGE_H   = 46
    BADGE_Y   = C_TOP - BADGE_H // 2   # straddles the card top border
    src_label = (source or "NEPSE ALERT").upper()
    f_src     = fnt['badge']   # Latin font — handles source names correctly
    sb        = draw.textbbox((0, 0), src_label, font=f_src)
    sw, sh_h  = sb[2] - sb[0], sb[3] - sb[1]
    badge_pad = 28
    badge_w   = sw + badge_pad * 2
    badge_x   = C_L + (C_W - badge_w) // 2

    # Badge glow
    for gi in range(5, 0, -1):
        bg_bdg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(bg_bdg).rounded_rectangle(
            [(badge_x - gi*2, BADGE_Y - gi), (badge_x + badge_w + gi*2, BADGE_Y + BADGE_H + gi)],
            radius=BADGE_H//2 + gi, fill=(*AMBER_GLOW, int(18*(gi/5)))
        )
        img = Image.alpha_composite(img, bg_bdg)

    draw = ImageDraw.Draw(img)
    # Badge fill
    draw.rounded_rectangle(
        [(badge_x, BADGE_Y), (badge_x + badge_w, BADGE_Y + BADGE_H)],
        radius=BADGE_H // 2, fill=AMBER_PILL
    )
    # Badge text
    draw.text(
        (badge_x + badge_pad, BADGE_Y + (BADGE_H - sh_h) // 2),
        src_label, font=f_src, fill=WHITE
    )

    # ── Step 5b: Headline text — always amber-framed, no summary ─────────────
    PILL_H   = 76
    PILL_GAP = 20
    PAD      = 40
    RULE_GAP = 22
    RULE_H   = 4

    # Available zone: just inside card top (badge straddles C_TOP)
    zone_top = C_TOP + 18
    zone_bot = C_BOT - PILL_H - PILL_GAP
    zone_h   = zone_bot - zone_top

    max_w   = C_W - PAD * 2
    h_font  = fnt['headline']   # 74pt — typical NEPSE headline wraps to 3-4 lines
    lines   = _wrap(headline, h_font, max_w, draw)[:4]
    lh      = int(h_font.size * 1.42)
    h_total = len(lines) * lh

    rule_x0 = C_L + PAD * 2
    rule_x1 = C_L + C_W - PAD * 2
    block_h = (RULE_H + RULE_GAP) * 2 + h_total
    # Small fixed top pad — all extra space falls to bottom
    ty = zone_top + 48

    # Top amber rule
    draw.rectangle([rule_x0, ty, rule_x1, ty + RULE_H], fill=(*AMBER_TOP, 200))
    ty += RULE_H + RULE_GAP

    for i, line in enumerate(lines):
        bb  = draw.textbbox((0, 0), line, font=h_font)
        lw  = bb[2] - bb[0]
        col = RED_ACCENT if i == len(lines) - 1 else GREEN_DARK
        tx  = C_L + (C_W - lw) // 2

        # Drop shadow
        sh_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh_layer).text((tx + 3, ty + 4), line,
                                       font=h_font, fill=(0, 0, 0, 60))
        img = Image.alpha_composite(img, sh_layer)
        draw = ImageDraw.Draw(img)

        draw.text((tx, ty), line, font=h_font, fill=col)
        ty += lh

    # Bottom amber rule
    draw.rectangle([rule_x0, ty + RULE_GAP, rule_x1, ty + RULE_GAP + RULE_H],
                   fill=(*AMBER_TOP, 200))

    # ── Step 6: Amber bottom bar with glow ───────────────────────────────────
    pill_text = "समाचारको लिंक कमेन्टमा"
    pb  = draw.textbbox((0, 0), pill_text, font=fnt['pill'])
    ph  = 110
    bar_y = C_BOT - ph

    # Bar glow (amber halo under bar)
    for gi in range(6, 0, -1):
        bg_sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(bg_sh).rounded_rectangle(
            [(C_L + 2, bar_y - gi*2), (C_R - 2, C_BOT + gi)],
            radius=34, fill=(*AMBER_GLOW, int(20*(gi/6)))
        )
        img = Image.alpha_composite(img, bg_sh)

    draw = ImageDraw.Draw(img)

    # Bar fill
    bar_ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(bar_ov).rounded_rectangle(
        [(C_L + 2, bar_y), (C_R - 2, C_BOT - 2)],
        radius=34, fill=(*AMBER_PILL, 255)
    )
    # Square off top corners
    ImageDraw.Draw(bar_ov).rectangle(
        [(C_L + 2, bar_y), (C_R - 2, bar_y + 34)],
        fill=(*AMBER_PILL, 255)
    )
    img = Image.alpha_composite(img, bar_ov)

    # Bright top highlight on bar (3D raised look)
    bar_hl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(bar_hl).rectangle(
        [(C_L + 3, bar_y), (C_R - 3, bar_y + 3)],
        fill=(255, 210, 80, 140)
    )
    img = Image.alpha_composite(img, bar_hl)

    draw = ImageDraw.Draw(img)
    tw = pb[2] - pb[0]
    th = pb[3] - pb[1]
    # Bar text shadow
    draw.text(((W - tw) // 2 + 2, bar_y + (ph - th) // 2 + 2),
              pill_text, font=fnt['pill'], fill=(0, 0, 0, 60))
    # Bar text
    draw.text(((W - tw) // 2, bar_y + (ph - th) // 2),
              pill_text, font=fnt['pill'], fill=WHITE)

    # ── Save ──────────────────────────────────────────────────────────────────
    img.convert('RGB').save(output_filename, 'JPEG', quality=93, optimize=True)
    print(f"[OK] {output_filename}")
    return output_filename


if __name__ == "__main__":
    generate_news_image(
        headline="मोबाइल बैंकिङबाटै बिना धितो १० लाखसम्म ऋण लिन सिकने !",
        summary="",
        output_filename="test_render.jpg",
    )
    print("Done → test_render.jpg")
