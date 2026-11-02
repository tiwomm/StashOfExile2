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


# ---------------------------------------------------------------- 2.66.2: the Panel
# Deep charcoal / dark wood / near-black leather; a heavy dark-metal frame with filigree corners; a header banner with
# its own decorative frame; the stats (and the switches) in a 2 x 2 grid split by thin divider lines; antique gold.
LEATHER_TOP, LEATHER_BOT = (24, 21, 19), (13, 11, 10)
WOOD_TOP, WOOD_BOT = (40, 29, 21), (22, 15, 11)
IRON_HI, IRON, IRON_MID, IRON_LO = (120, 104, 84), (78, 66, 52), (52, 43, 34), (20, 16, 12)
AGOLD_HI, AGOLD, AGOLD_LO = (236, 208, 140), (176, 146, 86), (104, 84, 48)


def card_palette(base):
    """The Panel's text colors: antique gold / cream title and numbers, cream icons."""
    P = dict(base)
    P.update(bg="#14110f", field="#14110f", text="#e9dfc8", muted="#9c8d74", big="#e6c77e", head="#ecdcae",
             sub="#a8925f", icon="#f1e8d4", line="#3d3226", on="#e6c77e", off="#857660", warn="#e0a352",
             cell_bg="#14110f", cell_line="#3d3226", rim="#6a5a46", rim_hi="#9c8a70", rim_lo="#241c14",
             bg_top="#211c18", on_icon="\u25c6", off_icon="\u25c7", font="Palatino Linotype",
             hfont="Palatino Linotype", poe=True)
    return P


def _filigree(d, x, y, sx, sy, n, t):
    """A corner ornament: a metal L with a leaf curl at each arm's end and a gold stud in the corner."""
    for lw, col in ((4 * t, K), (t * 2, AGOLD_LO), (t, AGOLD)):
        d.line((x, y, x + sx * n, y), fill=col, width=lw)
        d.line((x, y, x, y + sy * n), fill=col, width=lw)
    for (ex, ey, ang) in ((x + sx * n, y, 0), (x, y + sy * n, 1)):
        r = n * 0.22
        if ang == 0:
            box = (ex - r, ey, ex + r, ey + sy * 2 * r) if sy > 0 else (ex - r, ey + sy * 2 * r, ex + r, ey)
        else:
            box = (ex, ey - r, ex + sx * 2 * r, ey + r) if sx > 0 else (ex + sx * 2 * r, ey - r, ex, ey + r)
        box = (min(box[0], box[2]), min(box[1], box[3]), max(box[0], box[2]), max(box[1], box[3]))
        d.ellipse(box, outline=AGOLD_LO, width=t)
        d.ellipse((ex - t * 1.4, ey - t * 1.4, ex + t * 1.4, ey + t * 1.4), fill=AGOLD)
    leaf = [(x + sx * n * 0.18, y + sy * n * 0.18), (x + sx * n * 0.5, y + sy * n * 0.28),
            (x + sx * n * 0.28, y + sy * n * 0.5)]
    d.polygon(leaf, fill=IRON, outline=IRON_LO)
    d.ellipse((x - 2.2 * t, y - 2.2 * t, x + 2.2 * t, y + 2.2 * t), fill=AGOLD, outline=K)
    d.ellipse((x - 1 * t, y - 1.4 * t, x + 0.4 * t, y - 0.2 * t), fill=AGOLD_HI)


def card(root, w, h, banner, grids, foot_y):
    """The Panel's background, drawn whole: wood under a heavy dark-metal frame with filigree corners; the header
    banner (banner = (y0, y1)) in its own gold-lined frame with pointed ends; each grid (x0, y0, x1, y1, rows,
    cols) a near-black leather panel split by thin divider lines; a rule over the footer. -> PhotoImage."""
    key = ("card3", w, h, tuple(banner or ()), tuple(map(tuple, grids)), foot_y)
    if key in _CACHE:
        return _CACHE[key]
    old = [k_ for k_ in _CACHE if k_[0] == "card3"]
    if len(old) > 12:                                        # (a note being resized makes many sizes)
        for k_ in old[:-6]:
            _CACHE.pop(k_, None)
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    W, H, t = w * SS, h * SS, SS
    img = _stone(W, H, w * 5 + h, WOOD_TOP, WOOD_BOT)
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(w + h)
    for _ in range(H // (2 * t)):                            # wood grain
        y = rnd.randint(0, H)
        d.line((0, y, W, y + rnd.randint(-2 * t, 2 * t)), fill=(0, 0, 0, rnd.randint(16, 40)), width=t)
    # the heavy frame: black, a wide dark-metal band lit at the top-left, black, a thin antique-gold line
    fw = 9 * t
    d.rectangle((0, 0, W - 1, H - 1), outline=K, width=t)
    for i in range(1, fw // t):
        f = i / (fw / t)
        lit = _lerp(IRON_HI, IRON_MID, f)
        shade = _lerp(IRON_MID, IRON_LO, f)
        o = i * t
        d.line((o, o, W - o, o), fill=lit, width=t)
        d.line((o, o, o, H - o), fill=lit, width=t)
        d.line((o, H - o - t, W - o, H - o - t), fill=shade, width=t)
        d.line((W - o - t, o, W - o - t, H - o), fill=shade, width=t)
    d.rectangle((fw, fw, W - fw - 1, H - fw - 1), outline=K, width=t)
    d.rectangle((fw + t, fw + t, W - fw - t - 1, H - fw - t - 1), outline=AGOLD_LO, width=t)
    # the header banner: leather, a double gold frame, pointed ends, small lozenges at the points
    by0, by1 = (banner[0] * SS, banner[1] * SS) if banner else (0, 0)
    bx0, bx1 = fw + 6 * t, W - fw - 6 * t
    tip = (by1 - by0) * 0.45
    shape = [(bx0 + tip, by0), (bx1 - tip, by0), (bx1, (by0 + by1) / 2), (bx1 - tip, by1), (bx0 + tip, by1),
             (bx0, (by0 + by1) / 2)]
    mask = Image.new("L", (W, H), 0)
    if banner:
        ImageDraw.Draw(mask).polygon(shape, fill=255)
    lea = Image.new("RGB", (W, H))
    ld = ImageDraw.Draw(lea)
    for y in range(int(by0), int(by1) + 1):
        ld.line((0, y, W, y), fill=_lerp((40, 34, 30), LEATHER_BOT, (y - by0) / max(1, by1 - by0)))
    img.paste(lea, (0, 0), mask)
    d = ImageDraw.Draw(img, "RGBA")
    for _x in ([] if banner else [0]):                      # no banner: the whole inside is one leather panel
        ix0, iy0, ix1, iy1 = fw + 2 * t, fw + 2 * t, W - fw - 2 * t, H - fw - 2 * t
        for y in range(int(iy0), int(iy1)):
            d.line((ix0, y, ix1, y), fill=_lerp(LEATHER_TOP, LEATHER_BOT, (y - iy0) / max(1, iy1 - iy0)))
    if not banner:
        shape = []
    if shape:
        d.line(shape + [shape[0]], fill=K, width=3 * t)
    if shape:
        d.line(shape + [shape[0]], fill=AGOLD, width=t)
    ins = 3 * t
    inner = [(bx0 + tip + ins * 0.4, by0 + ins), (bx1 - tip - ins * 0.4, by0 + ins), (bx1 - ins * 1.6, (by0 + by1) / 2),
             (bx1 - tip - ins * 0.4, by1 - ins), (bx0 + tip + ins * 0.4, by1 - ins), (bx0 + ins * 1.6, (by0 + by1) / 2)]
    if shape:
        d.line(inner + [inner[0]], fill=AGOLD_LO, width=t)
    for x in ((bx0, bx1) if shape else ()):
        s = 3 * t
        cy = (by0 + by1) / 2
        d.polygon([(x, cy - s), (x + s, cy), (x, cy + s), (x - s, cy)], fill=AGOLD, outline=K)
    # the grids: leather panels with thin dividers (a dark line and a faint lit one beside it)
    for (gx0, gy0, gx1, gy1, rows, cols) in grids:
        gx0, gy0, gx1, gy1 = gx0 * SS, gy0 * SS, gx1 * SS, gy1 * SS
        for y in range(int(gy0), int(gy1)):
            d.line((gx0, y, gx1, y), fill=_lerp(LEATHER_TOP, LEATHER_BOT, (y - gy0) / max(1, gy1 - gy0)))
        for i in range(2 * t):                               # sunk: a shadow under the top edge
            d.line((gx0, gy0 + i, gx1, gy0 + i), fill=(0, 0, 0, int(160 * (1 - i / (2 * t)))))
        d.rectangle((gx0 - t, gy0 - t, gx1 + t, gy1 + t), outline=K, width=t)
        d.rectangle((gx0 - 2 * t, gy0 - 2 * t, gx1 + 2 * t, gy1 + 2 * t), outline=IRON, width=t)
        for c in range(1, cols):
            x = gx0 + (gx1 - gx0) * c / cols
            d.line((x, gy0 + 2 * t, x, gy1 - 2 * t), fill=K, width=t)
            d.line((x + t, gy0 + 2 * t, x + t, gy1 - 2 * t), fill=IRON_MID, width=t)
        for r in range(1, rows):
            y = gy0 + (gy1 - gy0) * r / rows
            d.line((gx0 + 2 * t, y, gx1 - 2 * t, y), fill=K, width=t)
            d.line((gx0 + 2 * t, y + t, gx1 - 2 * t, y + t), fill=IRON_MID, width=t)
        if rows > 1 and cols > 1:                            # a small stud where the dividers cross
            cx, cy = gx0 + (gx1 - gx0) / cols, gy0 + (gy1 - gy0) / rows
            d.ellipse((cx - 2 * t, cy - 2 * t, cx + 3 * t, cy + 3 * t), fill=IRON, outline=K)
    if foot_y:                                               # a rule over the footer
        fy = foot_y * SS
        for i in range(int(fw + 8 * t), int(W - fw - 8 * t)):
            a = int(200 * (1 - abs(i - W / 2) / (W / 2 - fw - 8 * t)) ** 0.7)
            d.point((i, fy), fill=AGOLD_LO + (a,))
    n = 22 * t                                               # filigree corners on the frame
    for (x, y, sx, sy) in ((fw // 2 + t, fw // 2 + t, 1, 1), (W - fw // 2 - t, fw // 2 + t, -1, 1),
                           (fw // 2 + t, H - fw // 2 - t, 1, -1), (W - fw // 2 - t, H - fw // 2 - t, -1, -1)):
        _filigree(d, x, y, sx, sy, n, t)
    img = img.resize((w, h), Image.LANCZOS)
    return _photo(img, root, key)


def glow(root, w, h):
    """A soft antique-gold glow for a switch's cell while it's on (laid over the leather)."""
    key = ("glow", w, h)
    if key in _CACHE:
        return _CACHE[key]
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except Exception:
        return None
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((w * 0.08, h * 0.25, w * 0.92, h * 1.3), fill=AGOLD + (70,))
    img = img.filter(ImageFilter.GaussianBlur(max(2, h * 0.3)))
    ImageDraw.Draw(img).line((3, h - 2, w - 4, h - 2), fill=AGOLD + (150,))
    return _photo(img, root, key)
