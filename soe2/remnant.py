"""Expedition Remnant Price Checker (2.37.0): prices the reward list a remnant shows you, right next to each line.

How: with a remnant's list open, press its key (Session tracker > Alerts, default Ctrl+Alt+R). The app takes ONE picture
of the game window, reads the text in it with Windows' own OCR (Windows.Media.Ocr - part of Windows, nothing to
install), finds the lines that are items (an item name, often with an amount like "Orb of Alchemy x3"), and puts a
price tag next to each from poe.ninja (the same prices as Wealth), the best one marked ★. One action per key press:
nothing is sent to the game and nothing runs in the background; the tags go away after a while or with the key again.

Credit: the idea comes from PoE Ancients Price Helper by Pedro Quitério
(https://github.com/pedro-quiterio/PoeAncientsPriceHelper). That project isn't open source, so none of its code, text
or images are used here - this is our own implementation of the idea."""
import difflib
import re
import sys

CREDIT_NAME = "PoE Ancients Price Helper by Pedro Quitério"
CREDIT_URL = "https://github.com/pedro-quiterio/PoeAncientsPriceHelper"
DEFAULT_KEY = "Ctrl+Alt+R"
SHOW_SECS = 30
MATCH = 0.84                      # how close an OCR'd line must be to an item name (difflib ratio)

QTY = re.compile(r"(?:^|\s)(?:[x×х]\s?(\d{1,4})|(\d{1,4})\s?[x×х])(?=\s|$)", re.I)
JUNK = re.compile(r"[^\w' ()\-:,.]+")


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
        hit = difflib.get_close_matches(low, pool, n=1, cutoff=MATCH)
        if not hit and pool is not self.keys:
            hit = difflib.get_close_matches(low, self.keys, n=1, cutoff=MATCH)
        return self.exact[hit[0]] if hit else None


def price_lines(lines, names, value_of):
    """[(text, box)] from OCR -> [{"text", "name", "qty", "each", "total", "box"}] for the lines that are items
    (value_of(name) -> divines each, or None when poe.ninja has no price)."""
    out = []
    for text, box in lines:
        base, qty = split_qty(text)
        name = names.match(base)
        if not name:
            continue
        each = value_of(name)
        out.append({"text": text, "name": name, "qty": qty, "each": each,
                    "total": each * qty if each is not None else None, "box": box})
    best = max((r for r in out if r["total"] is not None), key=lambda r: r["total"], default=None)
    for r in out:
        r["best"] = r is best
    return out


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
