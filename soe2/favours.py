"""2.128.0 Favours prices (the Ritual helper): poe.ninja's price over each reward in the Ritual altar's Favours window,
like the Expedition helper's tags on a remnant's book. Idea and approach looked at in poe2pricer by saxe78 (MIT): the
window is found by a piece of its own art, items by their pictures - this is our own code.

How it reads (pure functions here; the watcher and the tags are in favours_page.py):
  1. The window: the word FAVOURS on its title plate (templates/favours_title.png, from a 1440p game) is looked for in
     the top-left of the game, scaled to the game's height. Not there = the window isn't open.
  2. The grid: 12 x 10 cells of 70 px (at 1440p), at a fixed offset from the title. A cell holds an item when its
     blue (or red) backing shows.
  3. Each 1-cell item (omens, currency, runes ...) is compared with the pictures of everything poe.ninja's exchange
     prices: the official art (downloaded once to art/ninja in the data folder, laid on the cell's backing) and the
     pictures it learned on this PC (you price checked that item while the window was open). Picture and outline
     are both compared (the game dims rewards you can't afford yet); the best one counts only when it's clearly
     better than the next.
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
MATCH_MIN = 0.55                           # a picture must score this ...
MATCH_BY = 0.06                            # ... and beat the next-best item by this
LEARN_FILE = "favour_icons_v2.json"           # (2.128.1: the cell's top part - v1 held whole cells)
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
    """A cell's picture -> (gray, outline) at SIDE x SIDE, each with mean 0 and length 1 (so a dot product = the
    normalized correlation)."""
    cv2, np = _cv()
    im = cv2.resize(bgr, (SIDE, SIDE), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    out = []
    for a in (g, np.sqrt(gx * gx + gy * gy)):
        a = a - a.mean()
        n = float(np.sqrt((a * a).sum())) or 1.0
        out.append((a / n).ravel())
    return tuple(out)


def score(fa, fb):
    """How alike two cells are (-1 .. 1): the better of picture and outline (outline survives the dimming)."""
    return max(float((fa[0] * fb[0]).sum()), float((fa[1] * fb[1]).sum()))


def cell_crop(img, grid, r, c):
    """A cell's picture without its frame - its top part only (TOP: under it, a price tag may be showing)."""
    x, y, w, h = cell_rect(grid, r, c)
    e = max(1, int(round(EDGE * w / CELL)))
    return img[y + e:y + int(h * TOP), x + e:x + w - e]


def top_part(bgr):
    """A whole cell's picture (official art laid on the backing) -> the same part cell_crop takes."""
    h, w = bgr.shape[:2]
    e = max(1, int(round(EDGE * w / CELL)))
    return bgr[e:int(h * TOP), e:w - e]


def on_backing(rgba, kind="blue", dim=0.0):
    """Official art (RGBA, any size) laid on a Favours cell's backing, as the game draws it -> BGR. dim: 0 = as is,
    0.6 = as dim as a reward you can't afford."""
    cv2, np = _cv()
    a = rgba.astype(np.float32)
    if a.shape[2] == 3:
        a = np.dstack([a, np.full(a.shape[:2], 255, np.float32)])
    back = np.array((52, 14, 10) if kind == "blue" else (12, 12, 80), np.float32)      # BGR
    alpha = a[..., 3:4] / 255.0
    rgb = a[..., :3][..., ::-1]                                # RGBA -> BGR
    out = rgb * alpha + back * (1 - alpha)
    if dim:
        out = out * (1 - dim) + back * dim
    return np.clip(out, 0, 255).astype(np.uint8)


class Refs:
    """The pictures to compare with: {name: [feats, ...]} - official art (normal and dimmed) and learned ones."""

    def __init__(self):
        self.items = {}

    def add(self, name, bgr, src="art"):
        self.items.setdefault(name, []).append((feats(bgr), src))

    def add_art(self, name, rgba):
        for dim in (0.0, 0.55):
            self.add(name, top_part(on_backing(rgba, "blue", dim)), "art")

    def best(self, f):
        """-> (name, score, margin over the next item) or (None, best score, 0)."""
        scored = []
        for name, lst in self.items.items():
            scored.append((max(score(f, rf) for rf, _s in lst), name))
        if not scored:
            return None, 0.0, 0.0
        scored.sort(reverse=True)
        top, name = scored[0]
        nxt = scored[1][0] if len(scored) > 1 else -1.0
        if top >= MATCH_MIN and top - nxt >= MATCH_BY:
            return name, top, top - nxt
        return None, top, top - nxt


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
        cut = cell_crop(img, grid, r, c)
        if not cut.size:
            continue
        name, sc, _m = refs.best(feats(cut))
        out.append((r, c, name, sc, cell_rect(grid, r, c)))
    return win, out


# ---- pictures learned on this PC (you price checked a reward while the window was open)
def learned():
    _cv2, np = _cv()
    from .config import load_json
    out = {}
    for name, pics in (load_json(LEARN_FILE, {}) or {}).items():
        for b in pics if isinstance(pics, list) else [pics]:
            try:
                out.setdefault(name, []).append(np.frombuffer(base64.b64decode(b), np.uint8).reshape(SIDE, SIDE, 3))
            except Exception:
                continue
    return out


def learn(name, bgr):
    """Remember what this reward looks like in the Favours window (at most 3 pictures per item)."""
    cv2, np = _cv()
    from .config import load_json, save_json
    if bgr is None or not bgr.size or not name:
        return False
    small = cv2.resize(bgr, (SIDE, SIDE), interpolation=cv2.INTER_AREA)
    d = load_json(LEARN_FILE, {}) or {}
    lst = [x for x in (d.get(name) or []) if isinstance(x, str)]
    lst = (lst + [base64.b64encode(np.ascontiguousarray(small).tobytes()).decode()])[-3:]
    d[name] = lst
    save_json(LEARN_FILE, d)
    return True


# ---- the official art (poe.ninja's exchange items: their picture paths are in its answer)
ART_HOST = "https://web.poecdn.com"


def art_dir():
    from .config import P
    d = os.path.join(P("art"), "ninja")
    os.makedirs(d, exist_ok=True)
    return d


def art_path(nid):
    import re
    return os.path.join(art_dir(), re.sub(r"[^a-z0-9_-]+", "_", str(nid).lower()) + ".png")


def ninja_items(parts):
    """poe.ninja's exchange answers (WPRICES.parts) -> {id: (name, picture path)} for every item with a picture."""
    out = {}
    for typ, p in (parts or {}).items():
        imgs, names = (p or {}).get("images") or {}, (p or {}).get("names") or {}
        for nid, path in imgs.items():
            if path:
                out[nid] = (names.get(nid) or nid, path)
    return out


def fetch_art(items, ua, limit=400):
    """Download the pictures not on this PC yet (a background thread; a few hundred small PNGs, once). -> how many."""
    import requests
    n = 0
    for nid, (_name, path) in list(items.items())[:limit]:
        dst = art_path(nid)
        if os.path.exists(dst):
            continue
        url = path if str(path).startswith("http") else ART_HOST + str(path)
        try:
            r = requests.get(url, headers={"User-Agent": ua}, timeout=10)
            if r.status_code == 200 and r.content[:4] == b"\x89PNG":
                with open(dst + ".tmp", "wb") as fh:
                    fh.write(r.content)
                os.replace(dst + ".tmp", dst)
                n += 1
        except Exception:
            continue
    return n


def build_refs(items):
    """{id: (name, path)} -> Refs from the pictures on this PC (art/ninja) and the learned ones. Only 1-cell items
    (a square picture)."""
    cv2, _np = _cv()
    refs = Refs()
    for nid, (name, _p) in items.items():
        f = art_path(nid)
        if not os.path.exists(f):
            continue
        im = cv2.imread(f, cv2.IMREAD_UNCHANGED)
        if im is None or im.ndim != 3:
            continue
        h, w = im.shape[:2]
        if abs(w - h) > max(w, h) * 0.15:                 # (2.128.0: 1-cell items only - bigger ones later)
            continue
        if im.shape[2] == 4:
            im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA)
        else:
            im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        refs.add_art(name, im)
    for name, pics in learned().items():
        for p in pics:
            refs.add(name, p, "learned")
    return refs
