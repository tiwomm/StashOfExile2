"""The Game bar's artwork (2.65.1): drawn here with Pillow, no image files - a carved plate in a bevelled metal
frame with ornate end caps and a gem in each, recessed sockets for the mechanic switches, and small dividers. Drawn
3x and scaled down, so edges and curves are smooth. Cached per size and theme.
2.66.0: every color comes from the overlay palette (the app's theme): the plate from its surfaces, the metal from
its border and accent, the gem in the accent, a lit socket in its "good" color.

GGG ToS: looks only - nothing here touches the game."""
import random

SS = 3                                   # supersampling
_CACHE = {}



def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mx(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def colors(P):
    """The artwork's colors from an overlay palette."""
    K, Wt = (0, 0, 0), (255, 255, 255)
    metal = _rgb(P["rim"])
    acc, good, field = _rgb(P.get("accent") or P["head"]), _rgb(P["on"]), _rgb(P["field"])
    bg, top = _rgb(P["bg"]), _rgb(P.get("bg_top") or P["bg"])
    light = bool(P.get("light"))
    return {
        "hi": _rgb(P["rim_hi"]), "metal": metal, "mid": _mx(metal, K, .25), "lo": _mx(metal, K, .5),
        "dk": _mx(metal, K, .75),
        "stone_top": top if light else _mx(top, Wt, .04), "stone_bot": _mx(bg, K, .12 if light else .35),
        "well_top": _mx(field, K, .08 if light else .45), "well_bot": field,
        "gem": (_mx(acc, K, .65), _mx(acc, K, .35), acc, _mx(acc, Wt, .55)),
        "on_top": _mx(good, field, .82), "on_bot": _mx(good, field, .68), "on_edge": _mx(good, Wt, .15),
        "on_glow": good, "key": (P.get("theme"), P["rim"], P.get("accent"), P["field"]),
    }


def cap_width(h):
    """How wide each end cap is for a plate h px high."""
    return max(18, min(34, int(h * 0.5)))


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _photo(img, root, key):
    from PIL import ImageTk
    ph = ImageTk.PhotoImage(img, master=root)
    _CACHE[key] = ph
    return ph


def plate(root, w, h, P):
    """The whole bar: stone, frame, end caps, the recessed well in between. -> PhotoImage (None without Pillow)."""
    k = colors(P)
    BRONZE_HI, BRONZE, BRONZE_MID, BRONZE_LO, BRONZE_DK = k["hi"], k["metal"], k["mid"], k["lo"], k["dk"]
    STONE_TOP, STONE_BOT, WELL_TOP, WELL_BOT, AMBER = k["stone_top"], k["stone_bot"], k["well_top"], k["well_bot"], k["gem"]
    key = ("plate", w, h, k["key"])
    if key in _CACHE:
        return _CACHE[key]
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except Exception:
        return None
    W, H = w * SS, h * SS
    rnd = random.Random(w * 7 + h)
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(H):                                       # stone, lighter at the top
        d.line((0, y, W, y), fill=_lerp(STONE_TOP, STONE_BOT, y / max(1, H - 1)))
    for _ in range(max(20, w * h // 40)):                    # mottling
        cx, cy, r = rnd.randint(0, W), rnd.randint(0, H), rnd.randint(2 * SS, 9 * SS)
        c = rnd.choice(((0, 0, 0, rnd.randint(14, 34)), (90, 80, 64, rnd.randint(8, 18))))
        d.ellipse((cx - r, cy - r * 0.6, cx + r, cy + r * 0.6), fill=c)
    img = img.filter(ImageFilter.GaussianBlur(SS * 0.9))
    px = img.load()
    for _ in range(W * H // 14):                             # grain
        x, y = rnd.randrange(W), rnd.randrange(H)
        r, g, b = px[x, y]
        n = rnd.randint(-12, 12)
        px[x, y] = (max(0, r + n), max(0, g + n), max(0, b + n))
    d = ImageDraw.Draw(img, "RGBA")
    cw = cap_width(h) * SS
    t = SS                                                  # one screen pixel
    # ---- the well between the caps: recessed, darker, with a shadow under its top edge
    x0, x1, y0, y1 = cw + 2 * t, W - cw - 2 * t, 5 * t, H - 5 * t
    if x1 - x0 > 4 * t and y1 - y0 > 4 * t:
        for y in range(y0, y1):
            d.line((x0, y, x1, y), fill=_lerp(WELL_TOP, WELL_BOT, (y - y0) / max(1, y1 - y0)) + (235,))
        for i in range(3 * t):
            d.line((x0, y0 + i, x1, y0 + i), fill=(0, 0, 0, int(150 * (1 - i / (3 * t)))))
        d.line((x0, y1 - t, x1, y1 - t), fill=BRONZE_LO + (200,), width=t)
        d.line((x0, y0, x0, y1), fill=(0, 0, 0, 200), width=t)
        d.line((x1 - t, y0, x1 - t, y1), fill=BRONZE_DK + (220,), width=t)
        d.line((x0, y0 - t, x1, y0 - t), fill=BRONZE_MID + (230,), width=t)
    # ---- the bronze frame: dark outer line, a bevel (light on top, dark under), an inner dark line
    rim = [(0, (0, 0, 0)), (1, BRONZE_HI), (2, BRONZE), (3, BRONZE_MID), (4, BRONZE_DK)]
    for i, col in rim:
        d.line((i * t, i * t + t // 2, W - i * t, i * t + t // 2), fill=col, width=t)          # top
    for i, col in ((0, (0, 0, 0)), (1, BRONZE_LO), (2, BRONZE_MID), (3, BRONZE_DK)):
        d.line((i * t, H - i * t - t // 2 - 1, W - i * t, H - i * t - t // 2 - 1), fill=col, width=t)   # bottom
    for i, col in ((0, (0, 0, 0)), (1, BRONZE), (2, BRONZE_LO)):
        for x in (i * t + t // 2, W - i * t - t // 2 - 1):
            d.line((x, i * t, x, H - i * t), fill=col, width=t)
    # ---- the end caps: a carved bronze lozenge with an amber gem, flourishes reaching into the frame
    for side in (0, 1):
        cx = cw // 2 + 2 * t if side == 0 else W - cw // 2 - 2 * t
        cy = H // 2
        rx, ry = cw * 0.42, min(H * 0.40, cw * 0.55)
        # flourishes: two thin curves from the lozenge toward the well
        sgn = 1 if side == 0 else -1
        for dy in (-1, 1):
            bx = cx + sgn * rx * 0.6
            ex = cx + sgn * (cw * 0.62)
            d.line((bx, cy + dy * ry * 0.35, ex, cy + dy * ry * 0.85), fill=BRONZE_MID, width=max(1, t))
            d.ellipse((ex - 1.5 * t, cy + dy * ry * 0.85 - 1.5 * t, ex + 1.5 * t, cy + dy * ry * 0.85 + 1.5 * t),
                      fill=BRONZE)
        lozenge = [(cx, cy - ry), (cx + rx, cy), (cx, cy + ry), (cx - rx, cy)]
        d.polygon(lozenge, fill=BRONZE_DK)
        for k in range(6, 0, -1):                            # bevelled bronze, lighter toward the top-left
            f = k / 6
            pts = [(cx, cy - ry * f), (cx + rx * f, cy), (cx, cy + ry * f), (cx - rx * f, cy)]
            d.polygon(pts, fill=_lerp(BRONZE_LO, BRONZE, 1 - abs(f - 0.55)))
        d.line(lozenge[3:] + lozenge[:2], fill=BRONZE_HI, width=t)                 # lit upper edges
        d.line(lozenge[1:4], fill=(0, 0, 0), width=t)                            # shaded lower edges
        gr = min(rx, ry) * 0.42                              # the gem: dark rim, glowing core, a highlight
        for i, col in enumerate(AMBER):
            r = gr * (1 - i * 0.22)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
        d.ellipse((cx - gr * 0.45, cy - gr * 0.62, cx - gr * 0.05, cy - gr * 0.22), fill=(255, 240, 210, 200))
        d.ellipse((cx - gr, cy - gr, cx + gr, cy + gr), outline=(20, 10, 4), width=t)
    # ---- a small crest in the middle of the top edge
    mx = W // 2
    if x1 - x0 > 60 * t:
        cr = 4 * t
        d.polygon([(mx - 3 * cr, 0), (mx + 3 * cr, 0), (mx + cr, 2 * cr), (mx - cr, 2 * cr)], fill=BRONZE_MID)
        d.line([(mx - 3 * cr, 0), (mx - cr, 2 * cr), (mx + cr, 2 * cr), (mx + 3 * cr, 0)], fill=BRONZE_DK, width=t)
        d.polygon([(mx, cr * 0.3), (mx + cr * 0.8, cr), (mx, cr * 1.7), (mx - cr * 0.8, cr)], fill=AMBER[2])
    img = img.resize((w, h), Image.LANCZOS)
    return _photo(img, root, key)


def socket(root, w, h, P, on=False):
    """A recessed socket for one switch; lit (green-gold glow, bright rim) when on."""
    k = colors(P)
    BRONZE_LO, BRONZE_MID = k["lo"], k["mid"]
    key = ("sock", w, h, bool(on), k["key"])
    if key in _CACHE:
        return _CACHE[key]
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except Exception:
        return None
    W, H, t = w * SS, h * SS, SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = 3 * t
    top, bot = (k["on_top"], k["on_bot"]) if on else (k["well_top"], k["well_bot"])
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W - 1, H - 1), r, fill=255)
    fill = Image.new("RGBA", (W, H))
    fd = ImageDraw.Draw(fill)
    for y in range(H):
        fd.line((0, y, W, y), fill=_lerp(top, bot, y / max(1, H - 1)) + (255,))
    if on:                                                 # a soft glow from below
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((W * 0.1, H * 0.45, W * 0.9, H * 1.4), fill=k["on_glow"] + (90,))
        fill = Image.alpha_composite(fill, glow.filter(ImageFilter.GaussianBlur(H * 0.25)))
    img.paste(fill, (0, 0), mask)
    d = ImageDraw.Draw(img)
    for i in range(2 * t):                                 # inner shadow under the top edge
        d.line((r, i + t, W - r, i + t), fill=(0, 0, 0, int(170 * (1 - i / (2 * t)))))
    d.rounded_rectangle((0, 0, W - 1, H - 1), r, outline=k["on_edge"] if on else BRONZE_LO, width=t)
    d.line((r, H - t, W - r, H - t), fill=(k["on_edge"] if on else BRONZE_MID) + (170,), width=t)
    img = img.resize((w, h), Image.LANCZOS)
    return _photo(img, root, key)


def divider(root, h, P):
    """A thin bronze divider with a small lozenge in the middle."""
    k = colors(P)
    BRONZE_HI, BRONZE, BRONZE_MID, BRONZE_DK = k["hi"], k["metal"], k["mid"], k["dk"]
    key = ("div", h, k["key"])
    if key in _CACHE:
        return _CACHE[key]
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    w = 9
    W, H, t = w * SS, h * SS, SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2
    for y in range(H):
        a = int(230 * (1 - abs(y - cy) / max(1, cy)) ** 0.6)
        d.line((cx - t // 2, y, cx + t // 2, y), fill=BRONZE_MID + (a,))
    s = 3 * t
    d.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill=BRONZE, outline=BRONZE_DK)
    d.line([(cx - s, cy), (cx, cy - s), (cx + s, cy)], fill=BRONZE_HI, width=t)
    img = img.resize((w, h), Image.LANCZOS)
    return _photo(img, root, key)
