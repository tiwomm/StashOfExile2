"""2.131.0 Top Up Reminders (plan: "tells you what's running low in your inventory - reads only while your inventory is
open"): you teach it an item by hovering it in your inventory and pressing your price check key (its name comes from
the game's own item text); you set how many to keep. When you open your inventory in your hideout or a town and you
have fewer, one calm card says so ("Exalted Orb 7 / 20").

How it reads (pixels of your screen, like any capture tool):
- the inventory is open when its "Inventory" title is at the top right (templates/topup_banner.png, cut from a 1440p
  game; other screens score under 0.25),
- the 12 x 5 grid sits at a fixed place for the game's height (GRID, measured on 1440p),
- each cell is compared by its picture (a small color thumbnail, the stack count's corner left out, the cell's own
  backing subtracted so a hover's glow doesn't matter) - the same item scores under SAME, others over 25,
- a stack's count is read from its top-left digits (templates/topup_digit_N.png; digits the shipped set lacks are
  learned from the game's own "Stack Size:" line when you teach an item; Windows' OCR if a digit is still unknown).
Nothing is sent anywhere; only item pictures and names are kept (topup.json).
GGG ToS: a screenshot and your own key press's item text - nothing is sent to the game."""
import base64
import re
import sys

from . import buglog
from .config import SETTINGS, load_json, save_json

ROWS, COLS = 5, 12
GRID = (0.04875, 0.016, 0.5465)         # cell size, right margin, top - in game heights (1440p: 70.2, 23, 787 px)
BANNER = (0.45, 0.0, 0.12)              # where the title is looked for: width from the right, top, bottom (heights)
BANNER_MIN = 0.60
SIG = 20                                # cells are compared as SIG x SIG color thumbnails
COUNT_BOX = (0.55, 0.36)                # the stack count's corner (width, height) - left out of the picture
SAME = 14.0                             # mean color difference that is still the same item
DIGIT_MIN = 0.62
DIGIT_BAND = (0.0, 0.0, 0.62, 0.36)   # x0, y0, x1, y1 of a cell where its count's digits are
LEARN_FILE = "topup.json"
PICS = 4                                # pictures kept per item
DEFAULTS = {"on": False, "items": [], "below": 0.3}   # items: [{"name", "keep"}] - their pictures are in topup.json
# 2.131.2 (feedback: "it's asking me every single map, I only want it to ask when I am below a 70% threshold ... same
# way we handle the % variances on price checks"): a reminder only once you hold less than Keep minus this share
BELOW_STEPS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
# 2.131.4: + Add more's suggestions (the game's names; any other can be typed)
SUGGEST = ("Scroll of Wisdom", "Exalted Orb", "Regal Orb", "Chaos Orb", "Orb of Alchemy", "Orb of Augmentation",
           "Orb of Transmutation", "Vaal Orb", "Divine Orb", "Omen of Amelioration", "Cryptic Key",
           "Simulacrum Splinter", "Greater Exalted Orb", "Greater Regal Orb")


def below_text(b):
    p = int(round(float(b) * 100))
    return "0% (at Keep)" if p == 0 else f"{p}% below"


def remind_at(keep, below=None):
    """Keep 40, 30% below -> remind under 28 (always at least 1 below Keep's rounding: never at 0 needed)."""
    b = cfg().get("below", DEFAULTS["below"]) if below is None else below
    return max(0.0, float(keep) * (1 - float(b)))


def cfg():
    c = SETTINGS.setdefault("topup", {})
    for k, v in DEFAULTS.items():
        c.setdefault(k, list(v) if isinstance(v, list) else v)
    return c


def _cv():
    import cv2
    import numpy as np
    return cv2, np


def _templates():
    from pathlib import Path
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) / "soe2" / "templates" if base else Path(__file__).resolve().parent / "templates"


# ---------------------------------------------------------------- where things are
def grid_rect(game):
    """Game (x, y, w, h) on screen -> the inventory grid's (left, top, right, bottom) on screen."""
    x, y, w, h = game
    cell, right, top = (v * h for v in GRID)
    gx1 = x + w - right
    return (int(round(gx1 - COLS * cell)), int(round(y + top)), int(round(gx1)), int(round(y + top + ROWS * cell)))


def banner_rect(game):
    x, y, w, h = game
    return (int(x + w - BANNER[0] * h), int(y + BANNER[1] * h), int(x + w), int(y + BANNER[2] * h))


_TPL = {}


def _tpl(name, flag=None):
    if name not in _TPL:
        cv2, _np = _cv()
        _TPL[name] = cv2.imread(str(_templates() / name), cv2.IMREAD_GRAYSCALE if flag is None else flag)
    return _TPL[name]


def is_open(img, game_h):
    """The banner area (PIL) -> the inventory's title is there."""
    return open_score(img, game_h) >= BANNER_MIN


def open_score(img, game_h):
    try:
        cv2, np = _cv()
        tpl = _tpl("topup_banner.png")
        if tpl is None:
            return 0.0
        a = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
        s = game_h / 1440.0
        t = cv2.resize(tpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if abs(s - 1) > 0.01 else tpl
        if a.shape[0] < t.shape[0] or a.shape[1] < t.shape[1]:
            return 0.0
        return float(cv2.minMaxLoc(cv2.matchTemplate(a, t, cv2.TM_CCOEFF_NORMED))[1])
    except Exception:
        buglog.caught()
        return 0.0


def split(grid_img):
    """The grid (PIL) -> {(row, col): cell (PIL)}."""
    cw, ch = grid_img.width / COLS, grid_img.height / ROWS
    return {(r, c): grid_img.crop((int(round(c * cw)), int(round(r * ch)), int(round((c + 1) * cw)),
                                   int(round((r + 1) * ch))))
            for r in range(ROWS) for c in range(COLS)}


def empty(cell):
    _cv2, np = _cv()
    a = np.asarray(cell.convert("RGB").resize((24, 24))).astype(float)[3:21, 3:21]
    return a.mean() < 18 and a.std() < 8


# ---------------------------------------------------------------- what a cell holds
def _mask():
    _cv2, np = _cv()
    m = np.ones((SIG, SIG), bool)
    m[:int(SIG * COUNT_BOX[1]), :int(SIG * COUNT_BOX[0])] = False
    m[0, :] = m[-1, :] = m[:, 0] = m[:, -1] = False
    return m


def sig(cell):
    """A cell (PIL) -> its picture: SIG x SIG x 3 floats, the cell's backing (its edge ring's median) subtracted."""
    _cv2, np = _cv()
    from PIL import Image
    a = np.asarray(cell.convert("RGB").resize((SIG, SIG), Image.BILINEAR)).astype(float)
    ring = np.concatenate([a[1, 1:-1], a[-2, 1:-1], a[1:-1, 1], a[1:-1, -2]])
    return a - np.median(ring, axis=0)


def dist(a, b):
    _cv2, np = _cv()
    m = _mask()
    return float(np.abs(a - b)[m].mean())


def sig_b64(s):
    _cv2, np = _cv()
    return base64.b64encode(np.clip(s + 128, 0, 255).astype(np.uint8).tobytes()).decode()


def sig_from(b):
    _cv2, np = _cv()
    return np.frombuffer(base64.b64decode(b), np.uint8).reshape(SIG, SIG, 3).astype(float) - 128


# ---------------------------------------------------------------- the stack count
def _white(cell):
    _cv2, np = _cv()
    a = np.asarray(cell.convert("RGB")).astype(int)
    return (((a.min(2) > 165) & ((a.max(2) - a.min(2)) < 50)) * 255).astype(np.uint8)


def digit_templates():
    """{digit: binary picture at 1440p} - shipped ones, plus those learned on this PC."""
    cv2, np = _cv()
    out = {}
    for d in "0123456789":
        t = _tpl(f"topup_digit_{d}.png")
        if t is not None:
            out[d] = [t]
    for d, pics in ((load_json(LEARN_FILE, {}) or {}).get("digits") or {}).items():
        for p in pics:
            try:
                h, w, b = p
                out.setdefault(d, []).append(np.frombuffer(base64.b64decode(b), np.uint8).reshape(h, w))
            except Exception:
                continue
    return out


def _band(cell):
    n = cell.width
    x0, y0, x1, y1 = (int(v * n) for v in DIGIT_BAND)
    return _white(cell)[y0:y1, x0:x1], x0, y0


def _blobs(band, n):
    """Digit-sized white shapes near the count's place (a count the templates don't know)."""
    cv2, np = _cv()
    k, _lab, st, _c = cv2.connectedComponentsWithStats((band > 0).astype(np.uint8), 8)
    return [tuple(int(v) for v in st[i][:4]) for i in range(1, k)
            if 0.15 * n <= st[i][3] <= 0.27 * n and st[i][0] <= 0.22 * n and 0.04 * n <= st[i][1] <= 0.16 * n
            and 0.04 * n <= st[i][2] <= 0.2 * n]


def read_count(cell, tpls=None):
    """A cell -> (count, sure). No count shown: (1, True). A count it can't read: (None, False)."""
    cv2, np = _cv()
    band, _x0, _y0 = _band(cell)
    n = cell.width
    tpls = digit_templates() if tpls is None else tpls
    k = n / 70.2
    hits = []                                      # (score, x, y, w, digit)
    for d, pics in tpls.items():
        for t in pics:
            tt = cv2.resize(t, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if abs(k - 1) > 0.02 else t
            if tt.shape[0] > band.shape[0] or tt.shape[1] > band.shape[1]:
                continue
            res = cv2.matchTemplate(band, tt, cv2.TM_CCOEFF_NORMED)
            ys, xs = np.where(res >= DIGIT_MIN)
            for yy, xx in zip(ys, xs):
                hits.append((float(res[yy, xx]), int(xx), int(yy), tt.shape[1], d))
    hits.sort(reverse=True)
    picked = []
    for h in hits:                                 # best first; no two digits overlap much (a 1 inside a 0's side)
        if all(min(h[1] + h[3], p[1] + p[3]) - max(h[1], p[1]) <= 0.3 * min(h[3], p[3]) for p in picked):
            picked.append(h)
    picked.sort(key=lambda p: p[1])
    if not picked or picked[0][1] > 0.16 * n:      # nothing that starts where a count does
        return (None, False) if _blobs(band, n) else (1, True)
    run = [picked[0]]
    for p in picked[1:]:                           # side by side, on one line - a hit further on is the icon
        last = run[-1]
        if p[1] - (last[1] + last[3]) <= 0.04 * n and abs(p[2] - run[0][2]) <= max(2, 0.04 * n):
            run.append(p)
        else:
            break
    end = run[-1][1] + run[-1][3]
    rest = [b for b in _blobs(band, n) if b[0] >= end - 1 and b[0] - end <= 0.04 * n]
    if rest:                                       # a digit right after them the templates don't know: unsure
        return None, False
    return int("".join(p[4] for p in run)), True


def learn_digits(cell, count):
    """The game said this stack holds `count` (its "Stack Size:" line): keep any digit not yet known from the cell."""
    cv2, np = _cv()
    want = str(int(count))
    have = digit_templates()
    if all(d in have for d in want):
        return []
    band, _x0, _y0 = _band(cell)
    n, lab, st, _c = cv2.connectedComponentsWithStats((band > 0).astype(np.uint8), 8)
    boxes = sorted((tuple(int(v) for v in st[i][:4]) for i in range(1, n)
                    if 0.14 * cell.width <= st[i][3] <= 0.36 * cell.width and st[i][4] >= 6),
                   key=lambda b: b[0])
    if len(boxes) != len(want):
        return []
    k = 70.2 / cell.width
    d = load_json(LEARN_FILE, {}) or {}
    dg = d.setdefault("digits", {})
    new = []
    for ch, (x, y, w, h) in zip(want, boxes):
        if ch in have:
            continue
        pic = band[max(0, y - 1):y + h + 1, max(0, x - 1):x + w + 1]
        if abs(k - 1) > 0.02:
            pic = cv2.resize(pic, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        dg.setdefault(ch, []).append([pic.shape[0], pic.shape[1], base64.b64encode(pic.tobytes()).decode()])
        new.append(ch)
    if new:
        save_json(LEARN_FILE, d)
    return new


def ocr_count(cell):
    """Windows' OCR on the count's corner (a digit no template knows) -> count or None."""
    try:
        from PIL import Image
        from . import remnant as _R
        band, _x, _y = _band(cell)
        img = Image.fromarray(255 - band).resize((band.shape[1] * 3, band.shape[0] * 3))
        canvas = Image.new("L", (img.width + 40, img.height + 40), 255)
        canvas.paste(img, (20, 20))
        for text, _box in _R.ocr(canvas.convert("RGB")):
            m = re.fullmatch(r"\s*(\d{1,4})\s*", text.replace("O", "0").replace("o", "0").replace("l", "1"))
            if m:
                return int(m.group(1))
    except Exception:
        return None
    return None


# ---------------------------------------------------------------- reading the whole grid
def scan(grid_img, tpls=None, ocr=None):
    """The grid (PIL) -> [{"cell": (r, c), "sig", "count", "sure"}] for every cell that holds something."""
    tpls = digit_templates() if tpls is None else tpls
    out = []
    for rc, cell in split(grid_img).items():
        if empty(cell):
            continue
        n, sure = read_count(cell, tpls)
        if not sure and ocr is not False:
            n2 = (ocr or ocr_count)(cell)
            if n2 is not None:
                n, sure = n2, True
        out.append({"cell": rc, "sig": sig(cell), "count": n, "sure": sure, "img": cell})
    return out


def learned():
    """{name: [picture, ...]} taught on this PC."""
    out = {}
    for name, pics in ((load_json(LEARN_FILE, {}) or {}).get("items") or {}).items():
        for p in pics:
            try:
                out.setdefault(name, []).append(sig_from(p))
            except Exception:
                continue
    return out


def icon_b64(name):
    """The item's last taught cell as a small PNG (base64) for the list, or None."""
    return ((load_json(LEARN_FILE, {}) or {}).get("icons") or {}).get(name)


def learn(name, cell):
    """Your price check key on an item in your inventory: remember its picture (and a small icon for the list)."""
    if not name or cell is None or empty(cell):
        return False
    import io
    d = load_json(LEARN_FILE, {}) or {}
    items = d.setdefault("items", {})
    items[name] = ((items.get(name) or []) + [sig_b64(sig(cell))])[-PICS:]
    buf = io.BytesIO()
    cell.convert("RGB").resize((40, 40)).save(buf, "PNG")
    d.setdefault("icons", {})[name] = base64.b64encode(buf.getvalue()).decode()
    save_json(LEARN_FILE, d)
    return True


def pending():
    """2.131.2: taught cells still to learn again without the hover glow -> {name: ((row, col), sig)}. Kept in
    topup.json, so closing the inventory (or the app) right after teaching doesn't lose it."""
    out = {}
    for name, v in ((load_json(LEARN_FILE, {}) or {}).get("pending") or {}).items():
        try:
            out[name] = ((int(v[0]), int(v[1])), sig_from(v[2]))
        except (TypeError, ValueError, IndexError):
            pass
    return out


def pending_set(name, rc=None, s=None):
    """Remember (rc + sig) or drop (rc None) one taught cell to learn again."""
    d = load_json(LEARN_FILE, {}) or {}
    p = d.setdefault("pending", {})
    if rc is None:
        if p.pop(name, None) is None:
            return
    else:
        p[name] = [int(rc[0]), int(rc[1]), sig_b64(s)]
    save_json(LEARN_FILE, d)


def forget(name):
    d = load_json(LEARN_FILE, {}) or {}
    for k in ("items", "icons"):
        (d.get(k) or {}).pop(name, None)
    save_json(LEARN_FILE, d)


def which(s, refs):
    """A cell's picture -> the taught item it is (or None)."""
    best, bd = None, SAME
    for name, pics in refs.items():
        for p in pics:
            dd = dist(s, p)
            if dd < bd:
                best, bd = name, dd
    return best


def totals(cells, refs):
    """-> {name: (count, sure)} for every taught item (0 when none is in the inventory)."""
    out = {name: [0, True] for name in refs}
    for c in cells:
        name = which(c["sig"], refs)
        if name is None:
            continue
        if c["count"] is None:
            out[name][1] = False
        else:
            out[name][0] += c["count"]
    return {k: (v[0], v[1]) for k, v in out.items()}


def low(tot, items, below=None):
    """Totals and your list ([{"name", "keep"}]) -> [(name, have, keep)] under their keep less `below` (2.131.2: the
    Remind when setting, 30% below by default; sure counts only)."""
    out = []
    for it in items:
        name, keep = it.get("name"), int(it.get("keep") or 0)
        have, sure = tot.get(name, (0, True))
        if keep > 0 and sure and have < remind_at(keep, below):
            out.append((name, have, keep))
    return out


def card_text(lows, most=3):
    parts = [f"{n} {h} / {k}" for n, h, k in lows[:most]]
    more = f" · +{len(lows) - most} more" if len(lows) > most else ""
    return " · ".join(parts) + more


# ---------------------------------------------------------------- the item text (your price check key)
STACK = re.compile(r"^Stack Size:\s*([\d,.\s]+)/", re.M)


def full_stack(text):
    """The "Stack Size: 7/20" line's 20, or None."""
    m = re.search(r"^Stack Size:\s*[\d,.\s]+/\s*([\d,.]+)", str(text or ""), re.M)
    return int(re.sub(r"[^\d]", "", m.group(1))) if m else None


def item_name(text):
    """The game's item text -> (name, stack count or None) for a stackable item - or (2.131.4, feedback: "things
    like cryptic keys that do not stack") a normal one: each cell holding it counts 1. Else None (magic / rare /
    unique gear)."""
    lines = [ln.strip() for ln in str(text or "").splitlines()]
    i = next((k for k, ln in enumerate(lines) if ln.startswith("Rarity:")), None)
    if i is None or i + 1 >= len(lines):
        return None
    m = STACK.search(str(text))
    n = int(re.sub(r"[^\d]", "", m.group(1))) if m else None
    rarity = lines[i][7:].strip()
    if rarity not in ("Currency", "Normal") and m is None:     # (a currency, a stack or a plain item - not gear)
        return None
    return lines[i + 1], n


