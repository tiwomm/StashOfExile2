"""The Game bar's artwork (2.65.1, 2.66.0): drawn here with Pillow, no image files, in Path of Exile 2's own HUD style
so it sits in the game's bottom bar like part of it - charcoal stone, an aged pewter frame with a thin gold inner
line, corner brackets with rivets, end caps with a gothic arch holding a gem (crimson on the life side, sapphire on
the mana side), a small crest on top, switches in square sockets like the flask and skill slots (a warm gold glow
when on) and thin double dividers. Drawn 3x and scaled down, so edges and curves are smooth. Cached per size.
The Game bar keeps this look in every theme - it is part of the game's bar; the other layouts use the theme.

GGG ToS: looks only - nothing here touches the game."""
import random

SS = 3                                   # supersampling
_CACHE = {}

K = (0, 0, 0)
PEWTER_HI, PEWTER, PEWTER_MID, PEWTER_LO, PEWTER_DK = (178, 170, 152), (128, 121, 107), (92, 87, 77), (58, 54, 48), (28, 26, 23)
GOLD_LINE, GOLD, GOLD_HI = (112, 92, 54), (196, 160, 92), (240, 214, 150)
STONE_TOP, STONE_BOT = (30, 28, 25), (12, 11, 10)
WELL_TOP, WELL_BOT = (8, 8, 7), (17, 16, 14)
CRIMSON = ((60, 6, 6), (120, 14, 12), (190, 32, 24), (255, 150, 130))
SAPPHIRE = ((6, 14, 50), (14, 40, 110), (40, 96, 200), (170, 210, 255))
AMBER = ((70, 34, 6), (150, 80, 16), (220, 150, 50), (255, 226, 160))


def palette(base):
    """The Game bar's text and switch colors (drawn over the artwork): cream text, gold headings, a gold "on"."""
    P = dict(base)
    P.update(bg="#100f0d", field="#0d0c0b", text="#d9cfb5", muted="#9a8f78", big="#efe4c6", head="#c4a05c",
             line="#3a362f", on="#e3b961", off="#7d735f", warn="#e0a352", cell_bg="#0d0c0b", cell_line="#3a3630",
             rim="#807969", rim_hi="#b2aa98", rim_lo="#3a3630", bg_top="#1e1c19", on_icon="◆", off_icon="◇",
             font="Palatino Linotype", hfont="Palatino Linotype", poe=True)
    return P


def cap_width(h):
    """How wide each end cap is for a plate h px high."""
    return max(16, min(30, int(h * 0.46)))


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _photo(img, root, key):
    from PIL import ImageTk
    ph = ImageTk.PhotoImage(img, master=root)
    _CACHE[key] = ph
    return ph


def _stone(W, H, seed, top=STONE_TOP, bot=STONE_BOT):
    from PIL import Image, ImageDraw, ImageFilter
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(H):
        d.line((0, y, W, y), fill=_lerp(top, bot, y / max(1, H - 1)))
    for _ in range(max(16, W * H // 1800)):                  # mottling
        cx, cy, r = rnd.randint(0, W), rnd.randint(0, H), rnd.randint(2 * SS, 10 * SS)
        c = (0, 0, 0, rnd.randint(18, 40)) if rnd.random() < .6 else (80, 74, 64, rnd.randint(8, 16))
        d.ellipse((cx - r, cy - r * 0.5, cx + r, cy + r * 0.5), fill=c)
    for _ in range(W // (2 * SS)):                           # faint brushed streaks
        y0 = rnd.randint(0, H)
        d.line((rnd.randint(0, W), y0, rnd.randint(0, W), y0 + rnd.randint(-SS, SS)), fill=(255, 255, 255, 5))
    img = img.filter(ImageFilter.GaussianBlur(SS * 0.8))
    px = img.load()
    for _ in range(W * H // 12):                             # grain
        x, y = rnd.randrange(W), rnd.randrange(H)
        r, g, b = px[x, y]
        n = rnd.randint(-10, 10)
        px[x, y] = (max(0, r + n), max(0, g + n), max(0, b + n))
    return img


def _bevel_frame(d, x0, y0, x1, y1, t):
    """An aged pewter frame: black outline, a two-step bevel (lit top-left, shaded bottom-right), a black gap and a
    thin gold line inside."""
    d.rectangle((x0, y0, x1 - 1, y1 - 1), outline=K, width=t)
    for i, (lit, shade) in enumerate(((PEWTER_HI, PEWTER_LO), (PEWTER_MID, PEWTER_DK))):
        o = (i + 1) * t
        d.line((x0 + o, y0 + o, x1 - o, y0 + o), fill=lit, width=t)
        d.line((x0 + o, y0 + o, x0 + o, y1 - o), fill=lit, width=t)
        d.line((x0 + o, y1 - o - t, x1 - o, y1 - o - t), fill=shade, width=t)
        d.line((x1 - o - t, y0 + o, x1 - o - t, y1 - o), fill=shade, width=t)
    o = 3 * t
    d.rectangle((x0 + o, y0 + o, x1 - o - 1, y1 - o - 1), outline=K, width=t)
    o = 4 * t
    d.rectangle((x0 + o, y0 + o, x1 - o - 1, y1 - o - 1), outline=GOLD_LINE, width=t)


def _rivet(d, cx, cy, r):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PEWTER_LO, outline=K)
    d.ellipse((cx - r * .55, cy - r * .7, cx + r * .2, cy - r * .05), fill=PEWTER_HI)


def _gem(d, cx, cy, r, ramp, t):
    for i, col in enumerate(ramp[:3]):
        rr = r * (1 - i * 0.24)
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col)
    d.ellipse((cx - r * .5, cy - r * .62, cx - r * .05, cy - r * .2), fill=ramp[3] + (210,))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=K, width=t)
    d.ellipse((cx - r - t, cy - r - t, cx + r + t, cy + r + t), outline=GOLD, width=t)


def _cap(d, cx, H, cw, t, ramp, side):
    """An end cap: a raised pewter pillar with a gothic arch, a gem in it, and a spike pointing outward."""
    x0, x1 = cx - cw // 2, cx + cw // 2
    pad = 2 * t
    for y in range(pad, H - pad):                            # the pillar: pewter, lighter in the middle
        f = 1 - abs((y - H / 2) / (H / 2))
        d.line((x0, y, x1, y), fill=_lerp(PEWTER_DK, PEWTER_MID, f * 0.9))
    d.line((x0, pad, x0, H - pad), fill=PEWTER_HI, width=t)
    d.line((x1, pad, x1, H - pad), fill=K, width=t)
    ah = min(H * 0.72, cw * 1.3)                             # the arch: pointed top, flat bottom
    aw = cw * 0.66
    ay0, ay1 = H / 2 - ah / 2, H / 2 + ah / 2
    arch = [(cx - aw / 2, ay1), (cx - aw / 2, ay0 + ah * 0.42), (cx - aw * 0.28, ay0 + ah * 0.12), (cx, ay0),
            (cx + aw * 0.28, ay0 + ah * 0.12), (cx + aw / 2, ay0 + ah * 0.42), (cx + aw / 2, ay1)]
    d.polygon(arch, fill=(10, 9, 8), outline=PEWTER_HI)
    d.line(arch[3:], fill=PEWTER_LO, width=t)
    d.line(arch[:4], fill=PEWTER_HI, width=t)
    _gem(d, cx, ay0 + ah * 0.58, min(aw * 0.33, ah * 0.22), ramp, t)
    tip = x0 - 2 * t if side < 0 else x1 + 2 * t            # a small spike on the outer face
    base = x0 if side < 0 else x1
    d.polygon([(base, H / 2 - 3 * t), (tip, H / 2), (base, H / 2 + 3 * t)], fill=PEWTER, outline=K)


def _bracket(d, x, y, sx, sy, n, t):
    """A corner bracket: an L of pewter with a curl and a rivet."""
    d.line((x, y, x + sx * n, y), fill=PEWTER_HI, width=t * 2)
    d.line((x, y, x, y + sy * n), fill=PEWTER_HI, width=t * 2)
    d.line((x + sx * t, y + sy * t * 2, x + sx * n, y + sy * t * 2), fill=PEWTER_DK, width=t)
    r = n * 0.28
    cx, cy = x + sx * n, y + sy * r
    d.arc((cx - r, cy - r, cx + r, cy + r), 0, 360, fill=PEWTER, width=t)
    _rivet(d, x + sx * n * 0.45, y + sy * n * 0.45, t * 1.3)


def plate(root, w, h, P=None, ends=("crimson", "sapphire")):
    """The whole bar: stone, pewter frame with a gold inner line, corner brackets, end caps with gems, a crest on top,
    the recessed well between the caps. -> PhotoImage (None without Pillow)."""
    key = ("plate", w, h, ends)
    if key in _CACHE:
        return _CACHE[key]
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    W, H, t = w * SS, h * SS, SS
    img = _stone(W, H, w * 7 + h)
    d = ImageDraw.Draw(img, "RGBA")
    cw = cap_width(h) * SS
    _bevel_frame(d, 0, 0, W, H, t)
    x0, x1, y0, y1 = cw + 6 * t, W - cw - 6 * t, 6 * t, H - 6 * t
    if x1 - x0 > 4 * t and y1 - y0 > 3 * t:                 # the well: recessed, a shadow under its top edge
        for y in range(y0, y1):
            d.line((x0, y, x1, y), fill=_lerp(WELL_TOP, WELL_BOT, (y - y0) / max(1, y1 - y0)) + (225,))
        for i in range(3 * t):
            d.line((x0, y0 + i, x1, y0 + i), fill=(0, 0, 0, int(170 * (1 - i / (3 * t)))))
        d.line((x0, y1, x1, y1), fill=PEWTER_LO + (220,), width=t)
        d.line((x0 - t, y0, x0 - t, y1), fill=K + (220,), width=t)
        d.line((x1, y0, x1, y1), fill=PEWTER_LO + (200,), width=t)
    ramps = {"crimson": CRIMSON, "sapphire": SAPPHIRE, "amber": AMBER}
    _cap(d, 5 * t + cw // 2, H, cw, t, ramps[ends[0]], -1)
    _cap(d, W - 5 * t - cw // 2, H, cw, t, ramps[ends[1]], 1)
    n = min(H * 0.22, 7 * t)
    if H > 18 * t:                                           # corner brackets where there's room for them
        for (x, y, sx, sy) in ((cw + 7 * t, 5 * t, 1, 1), (W - cw - 7 * t, 5 * t, -1, 1),
                               (cw + 7 * t, H - 5 * t, 1, -1), (W - cw - 7 * t, H - 5 * t, -1, -1)):
            _bracket(d, x, y, sx, sy, n, t)
    mx = W // 2                                              # the crest: a small pointed arch with a gold gem
    if x1 - x0 > 70 * t:
        cr = 5 * t
        crest = [(mx - 3 * cr, 0), (mx - 1.6 * cr, 1.3 * cr), (mx, 1.9 * cr), (mx + 1.6 * cr, 1.3 * cr), (mx + 3 * cr, 0)]
        d.polygon(crest, fill=PEWTER_MID, outline=K)
        d.line(crest[:3], fill=PEWTER_HI, width=t)
        _gem(d, mx, cr * 0.85, cr * 0.55, AMBER, t)
    img = img.resize((w, h), Image.LANCZOS)
    return _photo(img, root, key)


def socket(root, w, h, P=None, on=False):
    """A square-cornered socket like the flask and skill slots: a dark inset in a pewter frame; a warm gold glow
    and a gold frame when on."""
    key = ("sock", w, h, bool(on))
    if key in _CACHE:
        return _CACHE[key]
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except Exception:
        return None
    W, H, t = w * SS, h * SS, SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top, bot = ((34, 26, 12), (52, 38, 16)) if on else (WELL_TOP, WELL_BOT)
    for y in range(H):
        d.line((0, y, W, y), fill=_lerp(top, bot, y / max(1, H - 1)) + (255,))
    if on:                                                   # a warm glow rising from the bottom
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((W * 0.05, H * 0.35, W * 0.95, H * 1.5), fill=GOLD + (110,))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(H * 0.28)))
        d = ImageDraw.Draw(img)
    for i in range(2 * t):                                   # inner shadow under the top edge
        d.line((t, i + t, W - t, i + t), fill=(0, 0, 0, int(190 * (1 - i / (2 * t)))))
    d.rectangle((0, 0, W - 1, H - 1), outline=K, width=t)
    edge, lit = (GOLD, GOLD_HI) if on else (PEWTER_LO, PEWTER_MID)
    d.rectangle((t, t, W - t - 1, H - t - 1), outline=edge, width=t)
    d.line((t, H - 2 * t, W - t, H - 2 * t), fill=lit + (200,), width=t)
    for x, y in ((t, t), (W - 3 * t, t), (t, H - 3 * t), (W - 3 * t, H - 3 * t)):      # notched corners
        d.rectangle((x, y, x + 2 * t, y + 2 * t), fill=lit if on else PEWTER_MID)
    img = img.resize((w, h), Image.LANCZOS)
    return _photo(img, root, key)


def divider(root, h, P=None):
    """Two thin pewter lines with a small lozenge between them."""
    key = ("div", h)
    if key in _CACHE:
        return _CACHE[key]
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    w = 11
    W, H, t = w * SS, h * SS, SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2
    for y in range(H):
        a = int(235 * (1 - abs(y - cy) / max(1, cy)) ** 0.5)
        for k in range(t):
            d.point((cx - 2 * t + k, y), fill=PEWTER_MID + (a,))
            d.point((cx + 2 * t + k, y), fill=PEWTER_LO + (a,))
    s = 3 * t
    d.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill=PEWTER, outline=K)
    d.line([(cx - s, cy), (cx, cy - s), (cx + s, cy)], fill=GOLD, width=t)
    img = img.resize((w, h), Image.LANCZOS)
    return _photo(img, root, key)


# ---------------------------------------------------------------- 2.66.1: the Panel, like the game's Treasurer window
# A dark wood frame; a charcoal title band with a pale metal top edge; a maroon band under it for the red subtitle;
# stats in charcoal boxes with a soft rim, cream icons and gold numbers.
WOOD_TOP, WOOD_BOT = (52, 30, 22), (30, 17, 12)
TITLE_TOP, TITLE_BOT = (64, 58, 54), (28, 25, 23)
SUB_TOP, SUB_BOT = (62, 17, 14), (34, 9, 8)
BOX_TOP, BOX_BOT = (36, 31, 29), (24, 20, 19)
RIDGE_HI, RIDGE, RIDGE_LO = (150, 132, 112), (96, 78, 64), (40, 28, 22)


def card_palette(base):
    """The Panel's text colors: pale small-caps title, red subtitle, cream icons, gold numbers."""
    P = dict(base)
    P.update(bg="#24150f", field="#1c1715", text="#e6dcc6", muted="#a89a86", big="#f2d77e", head="#efe8da",
             sub="#d9473c", icon="#e8dcc0", line="#4a3a30", on="#f2d77e", off="#8f8270", warn="#e0a352",
             cell_bg="#1c1715", cell_line="#4a3a30", rim="#7a6250", rim_hi="#a89070", rim_lo="#2c1c14",
             bg_top="#341e16", on_icon="\u25c6", off_icon="\u25c7", font="Palatino Linotype",
             hfont="Palatino Linotype", poe=True)
    return P


def _band(d, x0, y0, x1, y1, top, bot, t, cut):
    """A horizontal band with cut (bevelled) end corners, shaded top to bottom."""
    for y in range(int(y0), int(y1)):
        f = (y - y0) / max(1, y1 - y0)
        inset = cut * (1 - min(1, (y - y0) / max(1, cut))) if y - y0 < cut else (cut * (1 - min(1, (y1 - y) / max(1, cut)))
                                                                                if y1 - y < cut else 0)
        d.line((x0 + inset, y, x1 - inset, y), fill=_lerp(top, bot, f))


def card(root, w, h, bands):
    """The Panel's background: wood frame, title band (bands[0]..bands[1]), maroon subtitle band (..bands[2]).
    -> PhotoImage (None without Pillow)."""
    key = ("card2", w, h, tuple(bands))
    if key in _CACHE:
        return _CACHE[key]
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    W, H, t = w * SS, h * SS, SS
    img = _stone(W, H, w * 5 + h, WOOD_TOP, WOOD_BOT)
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(w + h)
    for _ in range(H // (2 * t)):                            # wood grain: long faint streaks
        y = rnd.randint(0, H)
        d.line((0, y, W, y + rnd.randint(-2 * t, 2 * t)), fill=(0, 0, 0, rnd.randint(14, 34)), width=t)
    # outer frame: black, a raised ridge (lit top-left), black
    d.rectangle((0, 0, W - 1, H - 1), outline=K, width=t)
    d.line((t, t, W - t, t), fill=RIDGE_HI, width=t)
    d.line((t, t, t, H - t), fill=RIDGE, width=t)
    d.line((t, H - 2 * t, W - t, H - 2 * t), fill=RIDGE_LO, width=t)
    d.line((W - 2 * t, t, W - 2 * t, H - t), fill=RIDGE_LO, width=t)
    d.rectangle((2 * t, 2 * t, W - 3 * t, H - 3 * t), outline=K, width=t)
    b0, b1, b2 = (b * SS for b in bands)
    m = 4 * t
    cut = 5 * t
    # title band: charcoal, a pale metal molding along the top, dark under it
    d.rectangle((m - t, b0 - t, W - m + t, b2 + t), fill=K)
    _band(d, m, b0, W - m, b1, TITLE_TOP, TITLE_BOT, t, cut)
    d.line((m + cut, b0, W - m - cut, b0), fill=(196, 182, 160), width=t)
    d.line((m + cut, b0 + t, W - m - cut, b0 + t), fill=(110, 100, 90), width=t)
    for x, s in ((m, 1), (W - m, -1)):                       # the cut corners' lit edges
        d.line((x, b0 + cut, x + s * cut, b0), fill=(150, 138, 120), width=t)
    d.line((m, b1 - t, W - m, b1 - t), fill=K, width=t)
    # subtitle band: maroon, darker at the bottom, a thin light line on top
    _band(d, m, b1, W - m, b2, SUB_TOP, SUB_BOT, t, 0)
    d.line((m, b1, W - m, b1), fill=(98, 40, 34), width=t)
    d.line((m, b2, W - m, b2), fill=K, width=t)
    for x in (m, W - m - t):                                 # small metal studs at the band's ends
        d.ellipse((x - t, (b1 + b2) / 2 - 2 * t, x + 3 * t, (b1 + b2) / 2 + 2 * t), fill=RIDGE, outline=K)
    img = img.resize((w, h), Image.LANCZOS)
    return _photo(img, root, key)


def box(root, w, h, on=False):
    """A stat / switch box: charcoal, rounded a little, a soft rim (lit top-left); gold rim and glow when on."""
    key = ("box2", w, h, bool(on))
    if key in _CACHE:
        return _CACHE[key]
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except Exception:
        return None
    W, H, t = w * SS, h * SS, SS
    r = 3 * t
    fill = Image.new("RGBA", (W, H))
    fd = ImageDraw.Draw(fill)
    top, bot = ((58, 46, 26), (40, 31, 18)) if on else (BOX_TOP, BOX_BOT)
    for y in range(H):
        fd.line((0, y, W, y), fill=_lerp(top, bot, y / max(1, H - 1)) + (255,))
    if on:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((W * 0.05, H * 0.2, W * 0.95, H * 1.4), fill=GOLD + (80,))
        fill = Image.alpha_composite(fill, glow.filter(ImageFilter.GaussianBlur(H * 0.3)))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W - 1, H - 1), r, fill=255)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.paste(fill, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, W - 1, H - 1), r, outline=K, width=t)
    hi, lo = ((214, 180, 110), (120, 92, 46)) if on else ((88, 76, 68), (14, 11, 10))
    d.arc((t, t, 2 * r + t, 2 * r + t), 180, 270, fill=hi, width=t)
    d.line((r + t, t, W - r - t, t), fill=hi, width=t)
    d.line((t, r + t, t, H - r - t), fill=hi, width=t)
    d.line((r + t, H - 2 * t, W - r - t, H - 2 * t), fill=lo, width=t)
    d.line((W - 2 * t, r + t, W - 2 * t, H - r - t), fill=lo, width=t)
    img = img.resize((w, h), Image.LANCZOS)
    return _photo(img, root, key)
