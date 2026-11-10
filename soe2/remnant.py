"""Expedition Remnant Price Checker (2.37.0): prices the reward list a remnant shows you, right next to each line.

How (2.119.0: always - the Auto switch and the Ctrl+Alt+R key are gone): the app looks at the spot where the reward
book opens (AREA, scaled to the game window like the Delirium / Ritual watchers) about every 0.7 s while the game is in
front. Only when that spot looks like the book's parchment, and changed, is its text read with Windows' own OCR
(Windows.Media.Ocr - part of Windows, nothing to install); the lines that are items (a name, often with an amount like
"Orb of Alchemy x3") get a price tag from poe.ninja (the same prices as Wealth), the best one marked ★. The tags come
and go by themselves as the book opens and closes. Nothing is sent to the game. The game's log (Client.txt) says
nothing when a remnant is opened, so the screen is the only way.

Credit: the idea comes from PoE Ancients Price Helper by Pedro Quitério
(https://github.com/pedro-quiterio/PoeAncientsPriceHelper). That project isn't open source, so none of its code, text
or images are used here - this is our own implementation of the idea.

ToS (TOS.md): this only LOOKS at the screen (a capture, like a screenshot) and SHOWS something; it never presses,
clicks, types or sends anything to the game, and never reads the game's memory or traffic."""
import difflib
import os
import re
import sys
import time
from . import buglog

CREDIT_NAME = "PoE Ancients Price Helper (Pedro Quitério)"
CREDIT_URL = "https://github.com/pedro-quiterio/PoeAncientsPriceHelper"
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
    ("C", "Stone", "armored, hard to stun"),
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
    ("C", "Cyclonic", "exposure, armor break, wither"),
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
ONE_X = re.compile(r"^[lI|i!]\s?[x×х](?=\s)")     # 2.129.0 (its log: 3 of 5 lines unread): OCR reads "1x" as "lx"


def split_qty(text):
    """'Orb of Alchemy x3' / '3x Orb of Alchemy' / 'Orb of Alchemy' -> ('Orb of Alchemy', 3 / 1)."""
    t = ONE_X.sub("1x", " ".join(str(text).split()))
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
    return bool(QTY.search(ONE_X.sub("1x", " ".join(str(text).split()))))


GEM_LINE = re.compile(r"^(Skill|Support|Spirit)(?:\s+Level\s+(\d+))?\s*:\s*(.{3,})$", re.I)


def gem_line(text):
    """2.130.0 (feedback: gems in a remnant's book showed nothing): "Skill Level 20: Repulsion" / "Support: Concussive
    Runes" -> ("skill" | "support" | "spirit", level or None, gem name), or None."""
    m = GEM_LINE.match(" ".join(str(text).split()))
    if not m:
        return None
    return m.group(1).lower(), (int(m.group(2)) if m.group(2) else None), m.group(3).strip()


UNIQUE_LINE = re.compile(r"^Unique\s+([A-Za-z][A-Za-z ]{2,30})$")


def unique_line(text):
    """2.130.0 (feedback: "Unique Ring" showed nothing): "Unique Ring" -> "ring" (the kind of item), or None."""
    m = UNIQUE_LINE.match(" ".join(str(text).split()))
    return m.group(1).strip().lower() if m else None


def price_lines(lines, names, value_of, gem_value=None, unique_pool=None):
    """[(text, box)] from OCR -> [{"text", "name", "qty", "each", "total", "box"}] for the lines that are items
    (value_of(name) -> divines each, or None when poe.ninja has no price). A reward line poe.ninja doesn't know at
    all is kept too, with "unknown": True and no price. 2.130.0: a gem line ("Skill Level 20: Repulsion") is priced
    on the trade site - gem_value(kind, level, name) -> (divines or None, still looking)."""
    out = []
    for text, box in lines:
        ul = unique_line(text) if unique_pool else None
        if ul:                                        # 2.130.0: a random unique of a kind - which ones it could be
            pool = unique_pool(ul)
            out.append({"text": text, "name": text, "qty": 1, "each": None, "total": None, "box": box,
                        "could_be": pool, "unknown": not pool})
            continue
        gl = gem_line(text) if gem_value else None
        if gl:
            each, pending = gem_value(*gl)
            out.append({"text": text, "name": gl[2] + (f" (level {gl[1]})" if gl[1] else ""), "qty": 1,
                        "each": each, "total": each, "box": box, "gem": True, "pending": pending,
                        "unknown": each is None and not pending})
            continue
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
RETRY_SECS = 1.0                  # 2.126.0: the book open, no tags yet, the picture still: read again this often
SETTLE_READS = 5                  # 2.79.0: reads right after the book appears, while it settles (~1.75 s)
AUTO_GONE = 2                     # looks without the book = it was closed: tags off (~0.7 s)
PARCHMENT = 0.35                  # share of the area that must look like the book's light parchment before reading
TITLE_MIN = 0.65                  # 2.129.0: the "Runeshape Combinations" title's match (the book 1.0, other screens <0.45)
TITLE_AREA = (0.05, 0.04, 0.55, 0.22)   # 2.129.1: where the title is looked for (game heights from the top-left) - its
#                                         own place: a learned reading area may start inside the title (the log)
_TITLE = [None]


def has_title(img, game_h):
    """2.129.0 (feedback: a map's sandy ground showed the runeshape list): the book's own title, "Runeshape
    Combinations" (templates/remnant_title.png, cut from a 1440p game), is in the picture (PIL, TITLE_AREA's grab).
    No OpenCV or no template: True (as before - the parchment alone decides)."""
    return title_score(img, game_h) >= TITLE_MIN


def title_score(img, game_h):
    """How well the title matches anywhere in the picture (0 .. 1; 1.0 = no OpenCV / no template)."""
    try:
        import cv2
        import numpy as np
        if _TITLE[0] is None:
            from pathlib import Path
            base = getattr(sys, "_MEIPASS", None)
            d = Path(base) / "soe2" / "templates" if base else Path(__file__).resolve().parent / "templates"
            _TITLE[0] = cv2.imread(str(d / "remnant_title.png"), cv2.IMREAD_GRAYSCALE)
        tpl = _TITLE[0]
        if tpl is None:
            return 1.0
        a = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
        s = game_h / 1440.0
        t = cv2.resize(tpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if abs(s - 1) > 0.01 else tpl
        if a.shape[0] < t.shape[0] or a.shape[1] < t.shape[1]:
            return 0.0
        return float(cv2.minMaxLoc(cv2.matchTemplate(a, t, cv2.TM_CCOEFF_NORMED))[1])
    except Exception:
        buglog.caught()
        return 1.0


def reading_area(learned):
    """2.130.0 (feedback: "no price on greater charging rune or greater ward rune" - the book's last two lines): an
    area learned by the old key (before 2.119.0) can be shorter than a long book - the area read is now the learned
    one and AREA together, so every line of the book is read."""
    if not learned or len(learned) != 4:
        return AREA
    return (min(learned[0], AREA[0]), min(learned[1], AREA[1]), max(learned[2], AREA[2]), max(learned[3], AREA[3]))


def area_rect(area, rect):
    """Area in game heights from the top-left -> screen pixels (left, top, right, bottom), kept inside the game."""
    l_, t, r, b = rect
    h = b - t
    return (int(l_ + area[0] * h), int(t + area[1] * h), min(r, int(l_ + area[2] * h)), min(b, int(t + area[3] * h)))


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


_ENGINE = [None]

# 2.128.1 (feedback: the tags should show in screenshots, screen share and streams, like the overlay): the tags and
# the runeshape list are no longer left out of captures, so the watchers would see them - they paint over where
# their own windows are before reading. OWN[key] = [(left, top, right, bottom) on screen] (set by the app's thread).
OWN = {}


def mask_own(img, origin, keys=("remnant",)):
    """A PIL picture of the screen whose top-left is `origin` -> the same with the helper's own windows painted over
    in the picture's middle color (so they read as nothing: no text, the parchment's share about the same)."""
    rects = [r for k in keys for r in list(OWN.get(k) or ())]
    if not rects:
        return img
    from PIL import ImageDraw, ImageStat
    img = img.copy()
    col = tuple(int(v) for v in ImageStat.Stat(img.convert("RGB")).median)
    d = ImageDraw.Draw(img)
    ox, oy = origin
    for l_, t, r, b in rects:
        if r > ox and b > oy and l_ < ox + img.width and t < oy + img.height:
            d.rectangle((l_ - ox - 2, t - oy - 2, r - ox + 2, b - oy + 2), fill=col)
    return img


def log(line):
    """2.127.0 (feedback: tags 10 s late, twice): the watcher's own log - when a book shows, each read (how long,
    how many lines and priced rewards) and when the tags go up - in remnant/remnant_log.txt in the data folder.
    Only what's on the reward list; nothing about you."""
    try:
        from .config import P
        d = P("remnant")
        os.makedirs(d, exist_ok=True)
        f = os.path.join(d, "remnant_log.txt")
        if os.path.exists(f) and os.path.getsize(f) > 300_000:
            os.replace(f, os.path.join(d, "remnant_log.old.txt"))
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {line}\n")
    except Exception:
        buglog.caught()


def _engine():
    if _ENGINE[0] is not None:                  # 2.127.0: made once (it was made for every read)
        return _ENGINE[0]
    _ENGINE[0] = _engine_new()
    return _ENGINE[0]


def _engine_new():
    from winrt.windows.media.ocr import OcrEngine
    try:
        from winrt.windows.globalization import Language
        eng = OcrEngine.try_create_from_language(Language("en-US"))
        if eng is not None:
            return eng
    except Exception:
        buglog.caught()
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
MARKER2_B64 = ("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")              # the other Expedition mark (the crystal; feedback)
MARKER_SCORE = 0.78              # its best match on the screenshots: ~1.0; with no Expedition: at most ~0.63 (2.98.6: 0.85)
UNSURE_ROWS = 2                  # 2.98.6: a map whose mark wasn't seen - rewards a book must list before tags show
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
    if "t" not in _MARK:                          # the swirl and the crystal: a map can have either, or both
        _MARK["t"] = [Image.open(io.BytesIO(base64.b64decode(b))).convert("RGB") for b in (MARKER_B64, MARKER2_B64)]
    hay = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    for base in _MARK["t"]:
        for s in (k, k * 0.8, k * 0.9, k * 1.1, k * 1.25):          # 2.98.6: UI scale varies - a wider range
            t = base.resize((max(6, round(base.width * s)), max(6, round(base.height * s))))
            tt = cv2.cvtColor(np.asarray(t), cv2.COLOR_RGB2BGR)
            if tt.shape[0] >= hay.shape[0] or tt.shape[1] >= hay.shape[1]:
                continue
            if float(cv2.matchTemplate(hay, tt, cv2.TM_CCOEFF_NORMED).max()) >= MARKER_SCORE:
                return True
    return False

