"""2.128.0 Favours prices (the Ritual helper): poe.ninja's price over each reward in the Ritual altar's Favours window,
like the Expedition helper's tags on a remnant's book. Idea and approach looked at in poe2pricer by saxe78 (MIT): the
window is found by a piece of its own art, items by their pictures - this is our own code.

How it reads (pure functions here; the watcher and the tags are in favours_page.py):
  1. The window: the word FAVOURS on its title plate (templates/favours_title.png, from a 1440p game) is looked for in
     the top-left of the game, scaled to the game's height. Not there = the window isn't open.
  2. The grid: 12 x 10 cells of 70 px (at 1440p), at a fixed offset from the title. A cell holds an item when its
     blue (or red) backing shows.
  3. Each 1-cell item is compared with the pictures learned on this PC of what poe.ninja's exchange prices (omens,
     currency, runes ...): Scan stash keeps each slot's picture of your Ritual, Currency ... tabs, and your price
     check key on a reward while the window is open keeps that one. Picture, outline and colors are compared, the
     stack number's corner left out (the game dims rewards you can't afford yet); the best one counts only when
     it's sure and clearly better than the next. 2.129.0: no official art (it was never sure), no uniques - only
     Mageblood and Headhunter get a ★ (their pictures ship in templates/). Each picture is compared two ways: the
     cell's top part as it is, and cropped to the item's art (so a stash slot and a Favours cell, which draw it at
     different sizes, line up). Every omen of the Ritual stash tab ships too (templates/favours_omens.png, slot
     pictures in the tab's order - favours_omens.json names them), so none has to be in your stash first.
Only looks at the screen: no keys, no clicks, nothing sent to the game. Nothing about you is saved: the pictures are
of items, and the log (ritual/favours_log.txt) says which item was found where and how sure."""
import base64
import os

BASE_H = 1440
TITLE_SEARCH = (0.0, 0.0, 0.62, 0.42)      # where the title can be: x0, y0, x1, y1 as parts of the game's size
TITLE_MIN = 0.62                           # template score that counts as "the window is open" (other screens ~0.3)
GRID_DX, GRID_DY = -330, 169               # the grid's top-left from the title word's top-left (1440p px)
CELL = 70
COLS, ROWS = 12, 10
EDGE = 5                                   # px left off each side of a cell when comparing (the cell's frame)
SIDE = 48                                  # cells are compared at this size
MATCH_MIN = {"learned": 0.72, "shipped": 0.72}  # 2.129.0 (feedback: a junk unique, Sacred Bloom and an omen all priced
MATCH_BY = 0.10                            # 4.6d): a picture must score this and beat the next-best item by this.
MATCH_SURE, MATCH_BY_SURE = 0.80, 0.06      # (a very close match may beat the next by less: Greater Exaltation and
                                           # Refreshment are the same hand in gold / teal)
CLEAR = (0.50, 0.25)                       # 2.129.1: or far ahead of every other item (a gray, sealed reward - the
                                           # log: Sanctification 0.51, next 0.23; wrong ones were never 0.15 ahead)
CLEAR_ITEMS = 10                           # (only among many items - with two, "far ahead" says nothing)
#                                            Tried on the user's own windows with his Ritual tab's pictures (Scan
#                                            stash): the right omen 0.74-0.88 (by 0.14-0.34), items it doesn't know up
#                                            to 0.70 (by 0.06); official art reached 0.64 for the wrong item
PER_NAME = 6                               # pictures kept per item (a stash slot gives 3: its size varies a little)
BELTS = {"Mageblood": "favours_mageblood.png", "Headhunter": "favours_headhunter.png"}   # 2.129.0: a ★, no price
BELT_MIN = 0.70
LEARN_FILE = "favour_icons_v2.json"
BOX_FILE = "favour_boxes.json"             # 2.129.0: the same items cropped to their art (art_box)
ART_DIFF = 40                              # a pixel this far from the cell's own backing color is the item's art           # (2.128.1: the cell's top part - v1 held whole cells)
TOP = 0.64                                 # 2.128.1: only a cell's top part is read - the price tag sits at its
#                                            foot and shows in screenshots and streams (the watcher sees it too)


def _cv():
    import cv2
    import numpy as np
    return cv2, np


def title_template():
    cv2, _np = _cv()
    import sys
    from pathlib import Path
    base = getattr(sys, "_MEIPASS", None)
    d = Path(base) / "soe2" / "templates" if base else Path(__file__).resolve().parent / "templates"
    return cv2.imread(str(d / "favours_title.png"), cv2.IMREAD_GRAYSCALE)


def find_window(gray, tpl, game_h=None, game_w=None):
    """The game's picture (grayscale; its top-left part will do - give the whole game's size then) -> (x, y, scale,
    score) of the title word, or None."""
    cv2, _np = _cv()
    h, w = game_h or gray.shape[0], game_w or gray.shape[1]
    s = h / BASE_H
    t = cv2.resize(tpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if abs(s - 1) > 0.01 else tpl
    x0, y0 = int(w * TITLE_SEARCH[0]), int(h * TITLE_SEARCH[1])
    area = gray[y0:min(gray.shape[0], int(h * TITLE_SEARCH[3])), x0:min(gray.shape[1], int(w * TITLE_SEARCH[2]))]
    if area.shape[0] < t.shape[0] or area.shape[1] < t.shape[1]:
        return None
    r = cv2.matchTemplate(area, t, cv2.TM_CCOEFF_NORMED)
    _mn, mx, _l, loc = cv2.minMaxLoc(r)
    if mx < TITLE_MIN:
        return None
    return loc[0] + x0, loc[1] + y0, s, float(mx)


def grid_box(win):
    """-> (x, y, cell) of the grid's top-left in the game's pixels."""
    x, y, s, _sc = win
    return int(round(x + GRID_DX * s)), int(round(y + GRID_DY * s)), CELL * s


def cell_rect(grid, r, c):
    gx, gy, cs = grid
    return int(round(gx + c * cs)), int(round(gy + r * cs)), int(round(cs)), int(round(cs))


def backing(img_bgr):
    """'blue' / 'red' / None: a cell's backing (an item is there) - the share of bluish or reddish pixels."""
    _cv2, np = _cv()
    a = img_bgr.astype(np.int16)
    b, g, r = a[..., 0], a[..., 1], a[..., 2]
    if ((b > g + 12) & (b > r + 8)).mean() > 0.25:
        return "blue"
    if ((r > g + 25) & (r > b + 15)).mean() > 0.25:
        return "red"
    return None


def occupied(img, grid):
    """-> {(r, c): 'blue' / 'red'} for every cell of the grid that holds (part of) an item."""
    out = {}
    for r in range(ROWS):
        for c in range(COLS):
            x, y, w, h = cell_rect(grid, r, c)
            m = max(2, int(w * 0.09))
            cut = img[y + m:y + int(h * TOP), x + m:x + w - m]
            if cut.size:
                k = backing(cut)
                if k:
                    out[(r, c)] = k
    return out


def feats(bgr):
    """A cell's picture -> (gray, outline, color) at SIDE x SIDE, each with mean 0 and length 1 (so a dot product =
    the normalized correlation). 2.129.0: the stack number's corner (top-left) is left out - "1" here, "30" in a
    stash slot - and the colors count too (omens differ most by color)."""
    cv2, np = _cv()
    im = cv2.resize(bgr, (SIDE, SIDE), interpolation=cv2.INTER_AREA).copy()
    im[:int(SIDE * 0.42), :int(SIDE * 0.5)] = im[int(SIDE * 0.42):, :].reshape(-1, 3).mean(0)
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    col = cv2.resize(im, (12, 12), interpolation=cv2.INTER_AREA).astype(np.float32)
    col = col - col.reshape(-1, 3).mean(0)
    out = []
    for a in (g, np.sqrt(gx * gx + gy * gy), col):
        a = a - a.mean() if a is not col else a
        n = float(np.sqrt((a * a).sum())) or 1.0
        out.append((a / n).ravel())
    return tuple(out)


def score(fa, fb):
    """How alike two cells are (-1 .. 1): half the better of picture and outline (outline survives the dimming),
    half the colors."""
    shape = max(float((fa[0] * fb[0]).sum()), float((fa[1] * fb[1]).sum()))
    return 0.5 * shape + 0.5 * float((fa[2] * fb[2]).sum())


def scaled(bgr, k):
    """A picture zoomed by k about its middle, the same size (a stash slot draws an item a little bigger or smaller
    than a Favours cell)."""
    cv2, np = _cv()
    h, w = bgr.shape[:2]
    nb = cv2.resize(bgr, None, fx=k, fy=k, interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_LINEAR)
    H, W = nb.shape[:2]
    if k >= 1:
        y, x = (H - h) // 2, (W - w) // 2
        return nb[y:y + h, x:x + w]
    out = np.empty_like(bgr)
    out[:] = bgr.reshape(-1, 3).mean(0)
    y, x = (h - H) // 2, (w - W) // 2
    out[y:y + H, x:x + W] = nb
    return out


def cell_crop(img, grid, r, c):
    """A cell's picture without its frame - its top part only (TOP: under it, a price tag may be showing)."""
    x, y, w, h = cell_rect(grid, r, c)
    e = max(1, int(round(EDGE * w / CELL)))
    return img[y + e:y + int(h * TOP), x + e:x + w - e]


def art_box(bgr, corner=True):
    """2.129.0: a cell's (or stash slot's) inside -> a square around the item's art: the pixels unlike the backing
    (its color = the median of the edge), the stack number's corner left out. A stash slot draws an item bigger or
    smaller than a Favours cell - cropped to the art, both line up."""
    cv2, np = _cv()
    h, w = bgr.shape[:2]
    if h < 12 or w < 12:
        return bgr
    a = bgr.astype(np.float32)
    ring = np.concatenate([a[:2].reshape(-1, 3), a[-2:].reshape(-1, 3), a[:, :2].reshape(-1, 3), a[:, -2:].reshape(-1, 3)])
    d = np.sqrt(((a - np.median(ring, 0)) ** 2).sum(-1))
    m = (d > ART_DIFF).astype(np.uint8)
    if corner:
        m[:int(h * 0.35), :int(w * 0.45)] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    ys, xs = np.nonzero(m)
    if len(xs) < 30:
        return bgr
    x0, x1 = np.percentile(xs, [3, 97]).astype(int)
    y0, y1 = np.percentile(ys, [3, 97]).astype(int)
    s = max(10, int(x1 - x0), int(y1 - y0))
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    x0, y0 = max(0, cx - s // 2), max(0, cy - s // 2)
    return bgr[y0:min(h, y0 + s), x0:min(w, x0 + s)]


def cell_inside(img, grid, r, c):
    """A whole cell without its frame (for art_box)."""
    x, y, w, h = cell_rect(grid, r, c)
    e = max(1, int(round(EDGE * w / CELL)))
    return img[y + e:y + h - e, x + e:x + w - e]


def cell_feats(img, grid, r, c):
    """-> {"top": feats of the cell's top part, "box": feats of its art} (None if the cell is off the picture)."""
    cv2, _np = _cv()
    top = cell_crop(img, grid, r, c)
    if not top.size:
        return None
    return {"top": feats(top), "box": feats(art_box(cell_inside(img, grid, r, c)))}


def slot_sides(bgr):
    """A stash slot's inside (a whole cell) -> [(mode, SIDE x SIDE picture)]: its top part at 3 sizes, and its art."""
    cv2, _np = _cv()
    out = [("top", cv2.resize(top_part(scaled(bgr, k)), (SIDE, SIDE), interpolation=cv2.INTER_AREA))
           for k in (0.88, 1.0, 1.12)]
    e = max(1, int(round(4 * bgr.shape[1] / CELL)))
    out.append(("box", cv2.resize(art_box(bgr[e:-e, e:-e]), (SIDE, SIDE), interpolation=cv2.INTER_AREA)))
    return out


def top_part(bgr):
    """A whole cell's picture (official art laid on the backing) -> the same part cell_crop takes."""
    h, w = bgr.shape[:2]
    e = max(1, int(round(EDGE * w / CELL)))
    return bgr[e:int(h * TOP), e:w - e]


class Refs:
    """The pictures to compare with: {name: [feats, ...]} - official art (normal and dimmed) and learned ones."""

    def __init__(self):
        self.items = {}

    def add(self, name, bgr, src="art", mode="top"):
        self.items.setdefault(name, []).append((feats(bgr), src, mode))

    def ranked(self, f, n=3):
        """f: cell_feats() (both ways) or feats() (the top part only) -> [(score, name, kind of picture)] best first:
        each item's best picture, each compared the same way it was taken."""
        both = f if isinstance(f, dict) else {"top": f}
        out = []
        for name, lst in self.items.items():
            got = [(score(both[m], rf), s) for rf, s, m in lst if both.get(m) is not None]
            if got:
                sc, src = max(got, key=lambda x: x[0])
                out.append((sc, name, src))
        out.sort(reverse=True)
        return out[:n]

    def best(self, f):
        """-> (name, score, margin over the next item) or (None, best score, margin)."""
        top3 = self.ranked(f, 2)
        if not top3:
            return None, 0.0, 0.0
        top, name, src = top3[0]
        nxt = top3[1][0] if len(top3) > 1 else -1.0
        by = MATCH_BY_SURE if top >= MATCH_SURE else MATCH_BY
        sure = top >= MATCH_MIN.get(src, 0.72) and top - nxt >= by
        clear = top >= CLEAR[0] and top - nxt >= CLEAR[1] and len(self.items) >= CLEAR_ITEMS
        if sure or clear:
            return name, top, top - nxt
        return None, top, top - nxt


def rerolls_left(img, win):
    """2.129.0: the reroll button (the dice) is red while you have rerolls, gray at 0. -> True / False (None: can't
    tell)."""
    _cv2, np = _cv()
    x, y, s, _sc = win
    cut = img[int(y + 64 * s):int(y + 154 * s), int(x - 265 * s):int(x - 180 * s)]
    if not cut.size:
        return None
    a = cut.astype(np.int16)
    red = ((a[..., 2] > a[..., 1] + 40) & (a[..., 2] > a[..., 0] + 40)).mean()
    return bool(red > 0.12)


def tribute_box(img, win):
    """The "4,749 TRIBUTE" line (BGR), for reading the number."""
    x, y, s, _sc = win
    return img[int(y + 95 * s):int(y + 143 * s), int(x + 15 * s):int(x + 250 * s)]


def tribute_of(lines):
    """OCR lines of tribute_box -> the number (4749), or None."""
    import re
    for text, _b in lines or []:
        m = re.search(r"(\d[\d,.\s]*\d|\d)\s*T", str(text), re.I)
        if m:
            try:
                return int(re.sub(r"[^\d]", "", m.group(1)))
            except ValueError:
                continue
    return None


def single_cells(occ):
    """Cells that could be a 1-cell item. The grid fills column by column from the top-left, so a big item's cells
    can't be told apart from small ones here - every occupied cell is tried; a big item's pieces match nothing."""
    return sorted(occ)


def read(img, refs, tpl):
    """The game's picture (BGR) -> (window found, [(r, c, name or None, score, (x, y, w, h))]) for every occupied cell."""
    cv2, _np = _cv()
    win = find_window(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), tpl)
    if win is None:
        return None, []
    grid = grid_box(win)
    occ = occupied(img, grid)
    out = []
    for r, c in single_cells(occ):
        f = cell_feats(img, grid, r, c)
        if f is None:
            continue
        name, sc, _m = refs.best(f)
        out.append((r, c, name, sc, cell_rect(grid, r, c)))
    return win, out


# ---- pictures learned on this PC (you price checked a reward while the window was open)
def learned(file=LEARN_FILE):
    """{name: [SIDE x SIDE pictures]} - LEARN_FILE: top parts, BOX_FILE: cropped to the art."""
    _cv2, np = _cv()
    from .config import load_json
    out = {}
    for name, pics in (load_json(file, {}) or {}).items():
        for b in pics if isinstance(pics, list) else [pics]:
            try:
                out.setdefault(name, []).append(np.frombuffer(base64.b64decode(b), np.uint8).reshape(SIDE, SIDE, 3))
            except Exception:
                continue
    return out


def learn_many(pics):
    """{name: a stash slot's picture (its inside, a whole cell)} -> remembered like learn() (the top part, as a
    Favours cell is read), in one write. -> how many."""
    cv2, np = _cv()
    from .config import load_json, save_json
    d = load_json(LEARN_FILE, {}) or {}
    bx = load_json(BOX_FILE, {}) or {}
    n = 0
    for name, bgr in (pics or {}).items():
        if bgr is None or not bgr.size or not name:
            continue
        sides = slot_sides(bgr)
        new = [_b64(p) for m, p in sides if m == "top"]
        lst = [x for x in (d.get(name) or []) if isinstance(x, str) and x not in new]
        d[name] = (lst + new)[-PER_NAME:]
        _keep(bx, name, [_b64(p) for m, p in sides if m == "box"])
        n += 1
    if n:
        save_json(LEARN_FILE, d)
        save_json(BOX_FILE, bx)
    return n


def _b64(small):
    _cv2, np = _cv()
    return base64.b64encode(np.ascontiguousarray(small).tobytes()).decode()


def _keep(d, name, new, most=3):
    lst = [x for x in (d.get(name) or []) if isinstance(x, str) and x not in new]
    d[name] = (lst + new)[-most:]


def learn(name, bgr, inside=None):
    """Remember what this reward looks like in the Favours window: bgr = its cell's top part (cell_crop), inside = the
    whole cell without its frame (cell_inside: kept cropped to its art too)."""
    cv2, np = _cv()
    from .config import load_json, save_json
    if bgr is None or not bgr.size or not name:
        return False
    small = cv2.resize(bgr, (SIDE, SIDE), interpolation=cv2.INTER_AREA)
    d = load_json(LEARN_FILE, {}) or {}
    lst = [x for x in (d.get(name) or []) if isinstance(x, str)]
    d[name] = (lst + [_b64(small)])[-PER_NAME:]
    save_json(LEARN_FILE, d)
    if inside is not None and inside.size:
        bx = load_json(BOX_FILE, {}) or {}
        _keep(bx, name, [_b64(cv2.resize(art_box(inside), (SIDE, SIDE), interpolation=cv2.INTER_AREA))])
        save_json(BOX_FILE, bx)
    return True


# ---- what poe.ninja's exchange prices (only those are priced here)
def ninja_items(parts):
    """poe.ninja's exchange answers (WPRICES.parts) -> {id: (name, picture path)} for every exchange item - never a
    unique."""
    out = {}
    for typ, p in (parts or {}).items():
        if str(typ).startswith("Unique"):
            continue
        names = (p or {}).get("names") or {}
        for nid, name in names.items():
            out[nid] = (name or nid, ((p or {}).get("images") or {}).get(nid))
    return out


def build_refs(items):
    """{id: (name, path)} -> Refs from the pictures learned on this PC: Scan stash (each slot of your Ritual,
    Currency ... tabs) and your price check key on a reward. 2.129.0: poe.ninja's official art is no longer used - on
    the user's own windows it scored up to 0.64 for the wrong item and never sure for the right one."""
    refs = Refs()
    known = {name for name, _p in items.values()}
    for name, pics in learned().items():
        if known and name not in known:                   # 2.129.0: an exchange item only (a learned unique
            continue                                      # - Coat of Red - is never priced)
        for p in pics:
            refs.add(name, p, "learned")
    for name, pics in learned(BOX_FILE).items():
        if known and name not in known:
            continue
        for p in pics:
            refs.add(name, p, "learned", "box")
    for name, bgr in shipped_omens().items():             # every omen of the Ritual tab, from the app itself
        if known and name not in known:
            continue
        for mode, p in slot_sides(bgr):
            refs.add(name, p, "shipped", mode)
    return refs


def _templates():
    import sys
    from pathlib import Path
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) / "soe2" / "templates" if base else Path(__file__).resolve().parent / "templates"


def shipped_omens():
    """{name: 70 x 70 stash slot picture} - the Ritual tab's omens (templates/favours_omens.png, a strip in the order
    favours_omens.json names them). Pictures of items only."""
    cv2, _np = _cv()
    import json
    d = _templates()
    try:
        names = json.loads((d / "favours_omens.json").read_text(encoding="utf-8"))
        strip = cv2.imread(str(d / "favours_omens.png"))
    except (OSError, ValueError):
        return {}
    if strip is None or not names:
        return {}
    w = strip.shape[1] // len(names)
    return {n: strip[:, i * w:(i + 1) * w] for i, n in enumerate(names)}


def belt_refs():
    """{name: feats} of Mageblood and Headhunter (2 x 1 belts; their trade-site pictures, templates/)."""
    cv2, _np = _cv()
    import sys
    from pathlib import Path
    base = getattr(sys, "_MEIPASS", None)
    d = Path(base) / "soe2" / "templates" if base else Path(__file__).resolve().parent / "templates"
    out = {}
    for name, fn in BELTS.items():
        im = cv2.imread(str(d / fn))
        if im is not None:
            h = im.shape[0]
            out[name] = feats(im[:int(h * TOP)])
    return out


def find_belts(img, grid, occ, refs):
    """2.129.0 (feedback: "if a Headhunter or Mageblood appears in the favour window ... a star over the item"):
    every two side-by-side cells that hold an item, compared with the belts -> [(name, score, (x, y, w, h))]."""
    out = []
    for r, c in sorted(occ):
        if (r, c + 1) not in occ:
            continue
        x, y, w, h = cell_rect(grid, r, c)
        x2, _y, w2, _h = cell_rect(grid, r, c + 1)
        e = max(1, int(round(EDGE * w / CELL)))
        cut = img[y + e:y + int(h * TOP), x + e:x2 + w2 - e]
        if not cut.size:
            continue
        f = feats(cut)
        for name, rf in refs.items():
            sc = score(f, rf)
            if sc >= BELT_MIN:
                out.append((name, sc, (x, y, x2 + w2 - x, h)))
    out.sort(key=lambda t: -t[1])
    seen, keep = set(), []
    for name, sc, box in out:
        if name not in seen:
            seen.add(name)
            keep.append((name, sc, box))
    return keep
