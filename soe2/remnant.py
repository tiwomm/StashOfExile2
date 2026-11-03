"""Expedition Remnant Price Checker (2.37.0): prices the reward list a remnant shows you, right next to each line.

How: with a remnant's list open, press its key (Session tracker > Alerts, default Ctrl+Alt+R). The app takes ONE picture
of the game window, reads the text in it with Windows' own OCR (Windows.Media.Ocr - part of Windows, nothing to
install), finds the lines that are items (an item name, often with an amount like "Orb of Alchemy x3"), and puts a
price tag next to each from poe.ninja (the same prices as Wealth), the best one marked ★. One action per key press:
nothing is sent to the game; the tags go away after a while or with the key again.

Auto (on by default - like the original, but without drawing a box): the app looks at the spot where the reward book
opens (AREA, scaled to the game window like the Delirium / Ritual watchers) about every 0.7 s while the game is in
front. Only when that spot looks like the book's parchment, and changed, is its text read; the tags come and go by
themselves as the book opens and closes. If a key press finds the list somewhere else (another UI scale), that spot is
learned instead. The game's log (Client.txt) says nothing when a remnant is opened, so the screen is the only way.

Credit: the idea comes from PoE Ancients Price Helper by Pedro Quitério
(https://github.com/pedro-quiterio/PoeAncientsPriceHelper). That project isn't open source, so none of its code, text
or images are used here - this is our own implementation of the idea.

ToS (TOS.md): this only LOOKS at the screen (a capture, like a screenshot) and SHOWS something; it never presses,
clicks, types or sends anything to the game, and never reads the game's memory or traffic."""
import difflib
import re
import sys

CREDIT_NAME = "PoE Ancients Price Helper by Pedro Quitério"
CREDIT_URL = "https://github.com/pedro-quiterio/PoeAncientsPriceHelper"
DEFAULT_KEY = "Ctrl+Alt+R"
SHOW_SECS = 12                    # 2.56.2 (feedback: "on screen too long"): was 30
MATCH = 0.84                      # how close an OCR'd line must be to an item name (difflib ratio)
LAST_WORD = 0.75                  # ... and its last word to the name's last word (2.40.0)

QTY = re.compile(r"(?:^|\s)(?:[x×х]\s?(\d{1,4})|(\d{1,4})\s?[x×х])(?=\s|$)", re.I)
JUNK = re.compile(r"[^\w' ()\-:,.]+")


# ================================================================ runeshape tips (2.40.0)
# A small cheat sheet shown next to the price tags while a remnant's book is open. Runeshapes are SYMBOLS in game
# (their names only show when you hover one), so the app can't tell which ones a remnant has - this lists how players
# rate them for loot. Sources gathered Nov 2026:
#   epoe.io Expedition guide (Larky's farming priorities: S Opulent, Oath, Power; A Death, Soul, Time; skip Bond;
#   "danger" runes Moon, Toxic, Bloodletting; arena hazards Earth; Life flagged for poor loot; Protective awkward),
#   timesaver.gg Aldur's Saga guide (Power, Death, Bond; Opulent and Oath community picks), game8 (all 33 effects).
# S and A are the guides' picks. B-D are grouped from those notes and each rune's effect: B = some upside (more
# kills, XP), C = only makes monsters tougher, D = hazards / dangerous. Bond: reports differ, so it's marked.
RUNE_TIPS_UPDATED = "Nov 2026"
RUNE_TIERS = [
    ("S", "Opulent", "rarer monsters - more loot"),
    ("S", "Power", "stronger runic mods (harder)"),
    ("S", "Oath", "monsters summon allies"),
    ("A", "Time", "slain monsters may return rarer"),
    ("A", "Death", "slain monsters merge, stronger"),
    ("A", "Soul", "union of souls"),
    ("A", "Bond", "rares pass on mods - mixed reports"),
    ("B", "Rebirth", "monsters may rebirth - more kills"),
    ("B", "Wisdom", "more experience"),
    ("B", "Ward", "monsters get runic ward"),
    ("C", "Life", "shared life - poor loot reported"),
    ("C", "Protective", "Verisium shields - awkward"),
    ("C", "Stone", "armoured, hard to stun"),
    ("C", "Rage", "monsters enrage"),
    ("C", "Momentum", "faster monsters"),
    ("C", "Adaptive", "adaptation"),
    ("C", "Arcane", "energy shield, nova"),
    ("C", "Vision", "reflects curses / shock / chill"),
    ("C", "Fire", "extra fire damage"),
    ("C", "Cold", "extra cold damage"),
    ("C", "Lightning", "extra lightning damage"),
    ("C", "Electrocuting", "electrocute, shocked ground"),
    ("C", "Volcanic", "ignite, burning ground"),
    ("C", "Tempest", "shock / chill on all damage"),
    ("C", "Prismatic", "always shock, random element"),
    ("C", "Cyclonic", "exposure, armour break, wither"),
    ("C", "Celestial", "elemental explosions on death"),
    ("D", "Bloodletting", "life leech, corrupted blood"),
    ("D", "Toxic", "poison, toxic volatiles"),
    ("D", "Earth", "earthen spires (hazard)"),
    ("D", "Moon", "moon beams (hazard)"),
    ("D", "Sky", "elemental tornados (hazard)"),
    ("D", "Tidal", "tidal waves (hazard)"),
]
TIER_LOOK = {"S": ("#2a2108", "#ffd25a"), "A": ("#16213a", "#9fc2ff"), "B": ("#13241a", "#7fd9a0"),
             "C": ("#1c1c24", "#b4bccb"), "D": ("#2a1012", "#ff8a80")}


class OcrUnavailable(Exception):
    pass


# ================================================================ reading lines (pure: tested offline)
def split_qty(text):
    """'Orb of Alchemy x3' / '3x Orb of Alchemy' / 'Orb of Alchemy' -> ('Orb of Alchemy', 3 / 1)."""
    t = " ".join(str(text).split())
    m = QTY.search(t)
    qty = 1
    if m:
        qty = int(m.group(1) or m.group(2))
        t = (t[:m.start()] + " " + t[m.end():]).strip()
    t = JUNK.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip(" -:,.")
    return t, max(1, qty)


class Names:
    """The item names poe.ninja prices, for matching what OCR read (lower case -> as written)."""

    def __init__(self, names):
        self.exact = {n.lower(): n for n in names if n}
        self.keys = list(self.exact)
        self.by_first = {}
        for k in self.keys:
            self.by_first.setdefault(k[:1], []).append(k)

    def match(self, text):
        low = text.lower()
        if len(low) < 4:
            return None
        if low in self.exact:
            return self.exact[low]
        pool = self.by_first.get(low[:1], []) or self.keys       # OCR rarely gets the first letter wrong
        hits = difflib.get_close_matches(low, pool, n=5, cutoff=MATCH)
        if not hits and pool is not self.keys:
            hits = difflib.get_close_matches(low, self.keys, n=5, cutoff=MATCH)
        for h in hits:
            if same_ending(low, h):
                return self.exact[h]
        return None


def same_ending(a, b):
    """2.40.0: the last word must match too. Many names share a long start ("Warding Rune of ..."), so the whole
    name scores high even when the part that matters differs: "Warding Rune of Obsession" vs "... of Protection"
    is 0.82 overall. An OCR slip in the last word is still fine (Alchemv / Alchemy)."""
    wa, wb = a.split()[-1:], b.split()[-1:]
    if not wa or not wb:
        return False
    return difflib.SequenceMatcher(None, wa[0], wb[0]).ratio() >= LAST_WORD


def explicit_qty(text):
    """The line has an amount ("6x ...", "... x3") - remnant reward lines always do."""
    return bool(QTY.search(" ".join(str(text).split())))


def price_lines(lines, names, value_of):
    """[(text, box)] from OCR -> [{"text", "name", "qty", "each", "total", "box"}] for the lines that are items
    (value_of(name) -> divines each, or None when poe.ninja has no price). A reward line poe.ninja doesn't know at
    all is kept too, with "unknown": True and no price."""
    out = []
    for text, box in lines:
        base, qty = split_qty(text)
        name = names.match(base)
        if not name:
            # 2.40.0: a reward line poe.ninja doesn't list (e.g. Warding Rune of Obsession) - still tagged, as
            # "no price", so you can see it was read (only lines with an amount: junk never has one)
            if explicit_qty(text) and len(base) >= 6 and len(base.split()) >= 2 and re.search(r"[a-z]{3}", base):
                out.append({"text": text, "name": base, "qty": qty, "each": None, "total": None, "box": box,
                            "unknown": True})
            continue
        each = value_of(name)
        out.append({"text": text, "name": name, "qty": qty, "each": each,
                    "total": each * qty if each is not None else None, "box": box})
    best = max((r for r in out if r["total"] is not None), key=lambda r: r["total"], default=None)
    for r in out:
        r["best"] = r is best
    return out


# ================================================================ Auto: where the list is (like the other watchers)
# The remnant's reward book opens at the left of the game (seen on a 2000x1125 screenshot, Nov 2026:
# reward lines at x 44-560, y 110-740). The game scales its UI with the window's HEIGHT and anchors this panel to the
# left, so the area is kept in units of the game's height from its top-left corner - right for any resolution or
# aspect ratio (16:9, 21:9 ...), the same way the Delirium and Ritual watchers find their spot.
AREA = (0.02, 0.10, 0.53, 0.66)   # x0, y0, x1, y1 in game heights
AUTO_POLL = 0.35                  # seconds between looks (only while the game is in front; 2.56.2: was 0.7)
SETTLE_READS = 5                  # 2.79.0: reads right after the book appears, while it settles (~1.75 s)
AUTO_GONE = 2                     # looks without the book = it was closed: tags off (~0.7 s)
PARCHMENT = 0.35                  # share of the area that must look like the book's light parchment before reading


def area_rect(area, rect):
    """Area in game heights from the top-left -> screen pixels (left, top, right, bottom), kept inside the game."""
    l_, t, r, b = rect
    h = b - t
    return (int(l_ + area[0] * h), int(t + area[1] * h), min(r, int(l_ + area[2] * h)), min(b, int(t + area[3] * h)))


def learn_area(rows, rect):
    """A key press found reward lines outside the usual spot (UI scale, another layout) -> an area that covers them,
    in game heights (a little bigger than what was seen, since a list can be longer)."""
    if not rows:
        return None
    h = rect[3] - rect[1]
    x0 = min(r["box"][0] for r in rows) / h
    y0 = min(r["box"][1] for r in rows) / h
    x1 = max(r["box"][2] for r in rows) / h
    y1 = max(r["box"][3] for r in rows) / h
    return (round(max(0.0, x0 - 0.05), 4), round(max(0.0, y0 - 0.06), 4), round(x1 + 0.05, 4), round(y1 + 0.2, 4))


def inside(rows, area, rect):
    """Every line a key press found is within the area (then nothing needs learning)."""
    ar = area_rect(area, (0, 0, rect[2] - rect[0], rect[3] - rect[1]))
    return all(ar[0] <= r["box"][0] and r["box"][2] <= ar[2] and ar[1] <= r["box"][1] and r["box"][3] <= ar[3]
               for r in rows)


def shift(lines, dx, dy):
    """OCR lines of a cut-out -> the same lines in the whole game window's pixels."""
    return [(t, (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy)) for t, b in lines]


def parchment_share(img):
    """How much of the area looks like the reward book's light, warm parchment (0-1), from a tiny thumbnail - cheap
    enough to check every look, so text is only read when the book is likely open."""
    px = list(img.convert("RGB").resize((40, 40)).getdata())
    hit = sum(1 for r, g, b in px if r > 150 and g > 135 and b > 100 and 0 <= r - b < 80)
    return hit / len(px)


def thumb(img):
    return img.convert("L").resize((48, 32)).tobytes()


def changed(a, b, tol=6.0):
    """Two small gray thumbnails (bytes) differ enough to read again."""
    if a is None or b is None or len(a) != len(b):
        return True
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a) > tol


# ================================================================ the picture and the OCR (Windows)
def grab(rect):
    """(left, top, right, bottom) of the screen -> PIL image."""
    import mss
    from PIL import Image
    l_, t, r, b = rect
    with mss.mss() as sct:
        shot = sct.grab({"left": int(l_), "top": int(t), "width": int(r - l_), "height": int(b - t)})
    return Image.frombytes("RGB", shot.size, shot.rgb)


def ocr_available():
    """'' when Windows' OCR can be used, else why not."""
    if sys.platform != "win32":
        return "needs Windows (its built-in text reader)"
    try:
        from winrt.windows.media.ocr import OcrEngine  # noqa: F401
    except Exception:
        return "Windows' text reader (OCR) isn't part of this build"
    try:
        return "" if _engine() is not None else "no OCR language: add English in Windows Settings > Language"
    except Exception as e:
        return f"Windows' text reader didn't start ({e.__class__.__name__})"


def _engine():
    from winrt.windows.media.ocr import OcrEngine
    try:
        from winrt.windows.globalization import Language
        eng = OcrEngine.try_create_from_language(Language("en-US"))
        if eng is not None:
            return eng
    except Exception:
        pass
    return OcrEngine.try_create_from_user_profile_languages()


def ocr(img):
    """PIL image -> [(line text, (x0, y0, x1, y1) in the image's pixels)] with Windows.Media.Ocr."""
    if sys.platform != "win32":
        raise OcrUnavailable(ocr_available())
    try:
        import asyncio
        from winrt.windows.graphics.imaging import BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.storage.streams import DataWriter
    except Exception as e:
        raise OcrUnavailable(f"Windows' text reader isn't part of this build ({e.__class__.__name__})")
    eng = _engine()
    if eng is None:
        raise OcrUnavailable("no OCR language: add English in Windows Settings > Language")
    # game text is small and light on dark: bigger reads better, within what the engine takes
    try:
        cap = int(OcrEngine.max_image_dimension)
    except Exception:
        cap = 2600
    scale = min(2.0, cap / max(img.size))
    if abs(scale - 1) > 0.05:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
    r, g, b = img.convert("RGB").split()
    from PIL import Image
    bgra = Image.merge("RGBA", (b, g, r, Image.new("L", img.size, 255))).tobytes()
    dw = DataWriter()
    dw.write_bytes(bgra)
    bmp = SoftwareBitmap.create_copy_from_buffer(dw.detach_buffer(), BitmapPixelFormat.BGRA8, img.width, img.height,
                                                 BitmapAlphaMode.PREMULTIPLIED)

    async def run():
        return await eng.recognize_async(bmp)
    res = asyncio.run(run())
    out = []
    for line in res.lines:
        rects = [w.bounding_rect for w in line.words]
        if not rects:
            continue
        x0, y0 = min(q.x for q in rects), min(q.y for q in rects)
        x1, y1 = max(q.x + q.width for q in rects), max(q.y + q.height for q in rects)
        out.append((line.text, tuple(int(v / scale) for v in (x0, y0, x1, y1))))
    return out


def selftest():
    """For CI on Windows: draw a line of text, read it back. -> what was read (or why it couldn't)."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (900, 120), (12, 10, 8))
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        font = ImageFont.load_default()
    ImageDraw.Draw(img).text((20, 30), "Orb of Alchemy x3", fill=(220, 210, 190), font=font)
    try:
        return " | ".join(t for t, _b in ocr(img))
    except OcrUnavailable as e:
        return f"unavailable: {e}"


# ================================================================ 2.83.0: is there an Expedition in this map?
# The Expedition mark under MAP CONTENT on the right (its swirl), as the game draws it at 1440p (the middle of the
# round icon). Feedback: "check a fixed area on the screen for the indicator of expedition being present".
MARKER_B64 = ("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")
MARKER_SCORE = 0.85              # its best match on the screenshots: ~1.0; with no Expedition: at most ~0.63
MARKER_STRIP = (0.30, 0.12, 0.85)    # the right edge: width, top, bottom - in game heights (the row moves up / down)
_MARK = {}


def marker_rect(rect):
    l_, t, r, b = rect
    h = b - t
    return (int(r - MARKER_STRIP[0] * h), int(t + MARKER_STRIP[1] * h), int(r), int(t + MARKER_STRIP[2] * h))


def has_marker(img, game_h):
    """A picture of the right edge -> True when the Expedition mark is there (None: can't tell - no OpenCV)."""
    try:
        import base64
        import io
        import cv2
        import numpy as np
        from PIL import Image
    except Exception:
        return None
    k = max(0.5, min(3.0, game_h / 1440.0))
    if "t" not in _MARK:
        _MARK["t"] = Image.open(io.BytesIO(base64.b64decode(MARKER_B64))).convert("RGB")
    hay = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    for s in (k, k * 0.9, k * 1.1):
        t = _MARK["t"].resize((max(6, round(_MARK["t"].width * s)), max(6, round(_MARK["t"].height * s))))
        tt = cv2.cvtColor(np.asarray(t), cv2.COLOR_RGB2BGR)
        if tt.shape[0] >= hay.shape[0] or tt.shape[1] >= hay.shape[1]:
            continue
        if float(cv2.matchTemplate(hay, tt, cv2.TM_CCOEFF_NORMED).max()) >= MARKER_SCORE:
            return True
    return False

