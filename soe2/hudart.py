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


# ---------------------------------------------------------------- 2.67.0: the Panel, like the game's vendor windows
# (the Treasurer's ledger: a dark oxblood frame with bronze edges and scrollwork, a raised header plate with the title
# in pale small caps and a red subtitle, stats in dark boxes with gold numbers)
OX_TOP, OX_BOT = (46, 20, 16), (20, 8, 6)
PLATE_TOP, PLATE_BOT = (78, 30, 24), (36, 12, 9)
BOX_TOP, BOX_BOT = (14, 8, 7), (24, 13, 11)
BRONZE_HI, BRONZE, BRONZE_LO = (214, 176, 120), (150, 112, 70), (78, 52, 30)
MAROON, MAROON_LO = (104, 40, 32), (52, 20, 15)


def card_palette(base):
    """The Panel's text colors: pale title, red subtitle, gold numbers."""
    P = dict(base)
    P.update(bg="#170a08", field="#120908", text="#ead9b0", muted="#a8927a", big="#f2d77a", head="#f1e6cc",
             sub="#e0574f", line="#5a2a20", on="#f0c860", off="#8a7460", warn="#e0a352", cell_bg="#120908",
             cell_line="#5a2a20", rim="#966f46", rim_hi="#d6b078", rim_lo="#4e341e", bg_top="#2e1410",
             on_icon="◆", off_icon="◇", font="Palatino Linotype", hfont="Palatino Linotype", poe=True)
    return P


def _curl(d, cx, cy, r, sx, t, col):
    """A scroll curl: a spiral-ish pair of arcs ending in a small ball."""
    a0, a1 = (90, 360) if sx > 0 else (180, 450)
    d.arc((cx - r, cy - r, cx + r, cy + r), a0, a1, fill=col, width=t)
    r2 = r * 0.55
    d.arc((cx - r2, cy - r2 * 1.1, cx + r2, cy + r2 * 0.9), a0 + 90, a1, fill=col, width=t)
    d.ellipse((cx - t * 1.3, cy - t * 1.3, cx + t * 1.3, cy + t * 1.3), fill=col)


def card(root, w, h, hh):
    """The Panel: frame, header plate (hh px high) with scrollwork at both ends, a rule under it. -> PhotoImage."""
    key = ("card", w, h, hh)
    if key in _CACHE:
        return _CACHE[key]
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    W, H, t = w * SS, h * SS, SS
    img = _stone(W, H, w * 3 + h, OX_TOP, OX_BOT)
    d = ImageDraw.Draw(img, "RGBA")
    # frame: black, bronze bevel, black, a maroon inner line
    d.rectangle((0, 0, W - 1, H - 1), outline=K, width=t)
    d.rectangle((t, t, W - t - 1, H - t - 1), outline=BRONZE, width=t)
    d.line((t, t, W - t, t), fill=BRONZE_HI, width=t)
    d.line((t, t, t, H - t), fill=BRONZE_HI, width=t)
    d.rectangle((2 * t, 2 * t, W - 2 * t - 1, H - 2 * t - 1), outline=BRONZE_LO, width=t)
    d.rectangle((3 * t, 3 * t, W - 3 * t - 1, H - 3 * t - 1), outline=K, width=t)
    d.rectangle((4 * t, 4 * t, W - 4 * t - 1, H - 4 * t - 1), outline=MAROON, width=t)
    # header plate
    HH = hh * SS
    px0, px1, py0, py1 = 9 * t, W - 9 * t, 6 * t, HH
    for y in range(py0, py1):
        d.line((px0, y, px1, y), fill=_lerp(PLATE_TOP, PLATE_BOT, (y - py0) / max(1, py1 - py0)))
    d.rectangle((px0, py0, px1, py1), outline=BRONZE, width=t)
    d.line((px0 + t, py0 + t, px1 - t, py0 + t), fill=BRONZE_HI, width=t)
    d.line((px0 + t, py1 - t, px1 - t, py1 - t), fill=K, width=t)
    d.rectangle((px0 + 2 * t, py0 + 2 * t, px1 - 2 * t, py1 - 2 * t), outline=MAROON_LO, width=t)
    # scrollwork at both ends of the plate, and small spikes on the frame beside it
    my = (py0 + py1) / 2
    for sx, x in ((1, px0 + 7 * t), (-1, px1 - 7 * t)):
        r = (py1 - py0) * 0.24
        _curl(d, x, my - r * 0.25, r, sx, t, BRONZE_HI)
        d.line((x + sx * r * 0.2, my + r * 0.9, x + sx * r * 2.4, my + r * 0.9), fill=BRONZE, width=t)
        d.ellipse((x + sx * r * 2.4 - t * 1.4, my + r * 0.9 - t * 1.4, x + sx * r * 2.4 + t * 1.4, my + r * 0.9 + t * 1.4),
                  fill=BRONZE_HI)
    for x in (2 * t, W - 2 * t):
        s = -1 if x < W / 2 else 1
        d.polygon([(x, my - 4 * t), (x + s * 3 * t, my), (x, my + 4 * t)], fill=BRONZE, outline=K)
    # a rule under the plate with a lozenge in the middle
    ry = py1 + 4 * t
    for i in range(W // 2):
        a = int(220 * (1 - abs(i - W / 4) / (W / 4)) ** 0.6) if W > 0 else 0
        d.point((W / 4 + i, ry), fill=BRONZE + (a,))
    cx = W / 2
    s = 3 * t
    d.polygon([(cx, ry - s), (cx + s, ry), (cx, ry + s), (cx - s, ry)], fill=BRONZE, outline=K)
    # bottom corner curls
    for sx, x in ((1, 8 * t), (-1, W - 8 * t)):
        _curl(d, x + sx * 3 * t, H - 9 * t, 4 * t, sx, t, BRONZE)
    img = img.resize((w, h), Image.LANCZOS)
    return _photo(img, root, key)


def box(root, w, h, on=False):
    """A stat / switch box: dark, a maroon edge, a thin bronze lip; a warm glow and a gold edge when on."""
    key = ("box", w, h, bool(on))
    if key in _CACHE:
        return _CACHE[key]
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except Exception:
        return None
    W, H, t = w * SS, h * SS, SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top, bot = ((40, 26, 10), (60, 38, 14)) if on else (BOX_TOP, BOX_BOT)
    for y in range(H):
        d.line((0, y, W, y), fill=_lerp(top, bot, y / max(1, H - 1)) + (255,))
    if on:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((W * 0.05, H * 0.3, W * 0.95, H * 1.5), fill=GOLD + (100,))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(H * 0.3)))
        d = ImageDraw.Draw(img)
    for i in range(2 * t):
        d.line((t, i + t, W - t, i + t), fill=(0, 0, 0, int(200 * (1 - i / (2 * t)))))
    d.rectangle((0, 0, W - 1, H - 1), outline=K, width=t)
    d.rectangle((t, t, W - t - 1, H - t - 1), outline=GOLD if on else MAROON, width=t)
    d.line((2 * t, H - 2 * t, W - 2 * t, H - 2 * t), fill=(GOLD_HI if on else BRONZE_LO) + (190,), width=t)
    img = img.resize((w, h), Image.LANCZOS)
    return _photo(img, root, key)
