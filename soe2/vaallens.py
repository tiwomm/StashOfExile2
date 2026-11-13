"""2.140.0 Vaal Lens (BETA): reads the Temple Console's board from a picture of the game - each tile's kind (empty,
path, room, reward room, Architect, key room, Atziri), a room's family and tier, the tiles the game lights green for
the picked card. Looks only: a picture of the screen, nothing sent to the game (GGG ToS).

Made from the player's own board pictures (local only); room icons matched to shipped prototypes
(templates/vaallens_icons.json - board icons only, no names of players). Coordinates are those of a 2560x1440 frame;
vaallens.frame(img) maps any game picture (another size, ultrawide) onto it.
"""
import json, os
import numpy as np
from PIL import Image

def _templates():
    import sys
    base = getattr(sys, "_MEIPASS", None)                 # (the built app: its files sit under _MEIPASS)
    return os.path.join(base, "soe2", "templates") if base else os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


HERE = _templates()
FULL = (2560, 1440)
CROP = (0.79, 0.85)                       # the watcher's crop of the frame
CELLS = [(i, j) for i in range(-4, 5) for j in range(1, 10)] + [(0, 10)]     # i -4..4, j 1..9, plus Atziri (0, 10)
EDGE = {c for c in CELLS if abs(c[0]) == 4 or c[1] in (1, 9)}     # the outer ring (reward rooms go here)

# ---------------------------------------------------------------- frame -> 2560x1440 canvas

def scale_of(w, h):
    """Picture size -> its scale against 2560x1440."""
    asp = w / h
    if abs(asp - 16 / 9) < 0.02:
        return w / FULL[0]                                     # full frame, maybe scaled
    if abs(asp - (16 * CROP[0]) / (9 * CROP[1])) < 0.02:
        return w / (FULL[0] * CROP[0])                         # watcher crop, maybe scaled
    return 1.0                                                 # some other crop of a 2560x1440 frame (top-left)


MIN_TIER_SCALE = 0.7     # below this the numerals blur together (tested at 0.75: some unread, none wrong; 0.5: wrong)


def to_canvas(img):
    """-> (rgb float array HxWx3 at 2560x1440, valid mask HxW). Pixels the picture does not cover are invalid."""
    if isinstance(img, np.ndarray):
        img = Image.fromarray(img.astype(np.uint8))
    img = img.convert("RGB")
    w, h = img.size
    s = scale_of(w, h)
    if abs(s - 1) > 1e-3:
        img = img.resize((round(w / s), round(h / s)), Image.BILINEAR)
        w, h = img.size
    a = np.zeros((FULL[1], FULL[0], 3), np.float32)
    v = np.zeros(FULL[::-1], bool)
    ww, hh = min(w, FULL[0]), min(h, FULL[1])
    a[:hh, :ww] = np.asarray(img, np.float32)[:hh, :ww]
    v[:hh, :ww] = True
    return a, v

# ---------------------------------------------------------------- overlays (tooltips, other windows)

def _components(m):
    """4-connected components of a small 2-D mask -> list of (rows, cols) index arrays."""
    seen = np.zeros_like(m, bool)
    out = []
    H, W = m.shape
    for r0, c0 in zip(*np.nonzero(m)):
        if seen[r0, c0]:
            continue
        stack, rr, cc = [(r0, c0)], [], []
        seen[r0, c0] = True
        while stack:
            r, c = stack.pop()
            rr.append(r); cc.append(c)
            for r2, c2 in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if 0 <= r2 < H and 0 <= c2 < W and m[r2, c2] and not seen[r2, c2]:
                    seen[r2, c2] = True
                    stack.append((r2, c2))
        out.append((np.array(rr), np.array(cc)))
    return out


BLK = 8
TT_HEAD = 122            # a tooltip's title banner sits above its flat black body; this much is masked above it


def overlays(a, v, box=(560, 100, 1960, 1260)):
    """Windows over the board: tooltips (flat 0-black body under a title banner), a cmd window (flat 12-gray),
    any other flat-colored app window. The game draws no perfectly flat areas on the board, so 8x8 blocks with
    no variation, in groups, are a window. -> list of (x0, y0, x1, y1) in 2560x1440 coordinates."""
    x0, y0, x1, y1 = box
    sub = a[y0:y1, x0:x1]
    vv = v[y0:y1, x0:x1]
    H, W = sub.shape[0] // BLK, sub.shape[1] // BLK
    b = sub[:H * BLK, :W * BLK].reshape(H, BLK, W, BLK, 3)
    flat = (b.std(axis=(1, 3)).max(axis=-1) < 0.8) & vv[:H * BLK:BLK, :W * BLK:BLK]
    level = b.mean(axis=(1, 3, 4))
    boxes = []
    for rr, cc in _components(flat):
        if len(rr) < 25 or cc.max() - cc.min() < 8:
            continue
        # a window's border and the block it cuts through are not flat: pad big ones by most of a block
        pd = 6 if len(rr) >= 150 else 0
        bx = [x0 + cc.min() * BLK - pd, y0 + rr.min() * BLK - pd, x0 + (cc.max() + 1) * BLK + pd,
              y0 + (rr.max() + 1) * BLK + pd]
        if np.median(level[rr, cc]) < 4:                # a tooltip body: add its title banner above
            bx[1] -= TT_HEAD
        boxes.append(tuple(int(t) for t in bx))
    return boxes


# ---------------------------------------------------------------- per-cell pixels

# Tile centers, fitted to the gold room frames of 126 rooms on 4 full frames (max error < 1 px). cells.center()
# is the older, rounder guess (about 8 px up-left of the true center).
X0, Y0, XI, YI, XJ, YJ = 932.74, 990.61, 69.30, 59.37, 69.32, -59.40


def xy(i, j):
    return X0 + XI * i + XJ * j, Y0 + YI * i + YJ * j


HW, HH = 70, 60                                            # patch half-size (one tile step)
_YY, _XX = np.mgrid[-HH:HH, -HW:HW]
D = np.abs(_XX) / 69.3 + np.abs(_YY) / 59.4                # 0 at the center, 1 on the tile edge
TILE = D < 0.95
CORE = D < 0.5                                             # where a room's icon sits
FRAME = (D > 0.75) & (D < 0.87)                            # a room's gold diamond frame (at D = 0.81)
# the four sides of the frame ring (NE, SE, SW, NW quadrants)
QUAD = [FRAME & (_XX > 0) & (_YY < 0), FRAME & (_XX > 0) & (_YY > 0),
        FRAME & (_XX < 0) & (_YY > 0), FRAME & (_XX < 0) & (_YY < 0)]


def patch(a, c, pad=0):
    x, y = (round(t) for t in xy(*c))
    return a[y - HH - pad:y + HH + pad, x - HW - pad:x + HW + pad]


def masks(p):
    r, g, b = p[..., 0], p[..., 1], p[..., 2]
    mx, mn = p.max(axis=2), p.min(axis=2)
    gold = (r > 80) & (r - b > 35) & (g > 0.55 * r) & (g < 1.02 * r)         # gold lines and frames
    red = (r > 90) & (r > 1.8 * g) & (r > 1.8 * b)                             # a powered (red) corridor
    green = (g - np.maximum(r, b) > 6)                                          # the lit overlay / green icons
    bright = mx > 120
    return gold, red, green, bright, (mx - mn) / (mx + 1)


def _ring_samples(n=24, ds=(0.76, 0.78, 0.80, 0.82, 0.84, 0.86)):
    """Points along the four sides of a room frame (D = 0.81), several radial offsets each.
    -> int arrays (side, sample, offset) of y, x in patch coordinates."""
    t = np.linspace(0.12, 0.88, n)                          # skip the corners
    vx = [(0, -1), (1, 0), (0, 1), (-1, 0)]                 # top, right, bottom, left vertices (unit)
    ys, xs = [], []
    for k in range(4):                                      # sides: NE (top->right), SE, SW, NW
        (ax, ay), (bx, by) = vx[k], vx[(k + 1) % 4]
        px, py = ax + (bx - ax) * t, ay + (by - ay) * t
        yy = np.stack([py * d * 59.4 for d in ds], 1) + HH
        xx = np.stack([px * d * 69.3 for d in ds], 1) + HW
        ys.append(yy); xs.append(xx)
    return np.round(ys).astype(int), np.round(xs).astype(int)


_RY, _RX = _ring_samples()


def frame_cover(gm):
    """Share of each frame side where a gold line runs (any radial offset). A room's frame covers ~all of every
    side; a corridor only crosses the frame line at a few points."""
    hit = gm[_RY, _RX].any(axis=2)                         # (side, sample)
    return hit.mean(axis=1)


def feats(p, hid=None):
    """A few numbers that tell empty / path / room-like apart. hid: pixels under a window (not counted)."""
    gold, red, green, bright, sat = masks(p)
    gm = gold | red
    if hid is not None and hid.any():
        T = TILE & ~hid
        seen = ~hid[_RY, _RX].any(axis=2)                   # ring samples not under the window
        hit = gm[_RY, _RX].any(axis=2)
        cov = [hit[k][seen[k]].mean() for k in range(4) if seen[k].mean() >= 0.5]
        frame = float(np.sort(cov)[1]) if len(cov) >= 3 else (float(min(cov)) if len(cov) == 2 else -1.0)
        return dict(gold=float(gm[T].mean()), frame=frame, red=float(red[T & ~CORE].mean()),
                    green=float(green[T].mean()), partial=float(hid[TILE].mean()))
    q = [float(gm[m].mean()) for m in QUAD]
    cov = frame_cover(gm)
    gray = p.mean(axis=2)
    return dict(
        gold=float(gm[TILE].mean()),
        gold_core=float(gm[CORE].mean()),
        frame=float(np.sort(cov)[1]), frame_min=float(cov.min()), frame_mean=float(cov.mean()),
        red=float(red[TILE & ~CORE].mean()),
        green=float(green[TILE].mean()),
        bright_core=float(bright[CORE].mean()),
        std_core=float(gray[CORE].std()),
        mean_tile=float(gray[TILE].mean()),
        mean_core=float(gray[CORE].mean()),
        sat_core=float(sat[CORE & bright].mean()) if (CORE & bright).any() else 0.0,
    )


# ---------------------------------------------------------------- tier numeral

def _vruns(m):
    """Longest vertical run of True per column, and where it starts."""
    H, W = m.shape
    best, start = np.zeros(W, int), np.zeros(W, int)
    cur = np.zeros(W, int)
    for y in range(H):
        cur = np.where(m[y], cur + 1, 0)
        better = cur > best
        best = np.where(better, cur, best)
        start = np.where(better, y - cur + 1, start)
    return best, start


def tier(p):
    """Roman numeral at the icon's lower right -> (tier 1-4 or None, how). No numeral = tier I.
    Numerals are pale (white, pale yellow or pale green) upright strokes ~3 px wide, 13-20 px tall, side by side."""
    box = p[HH + 2:HH + 32, HW + 6:HW + 58]                 # rel y +2..+32, x +6..+58
    mn, mx = box.min(axis=2), box.max(axis=2)
    m = (mn > 105) & (mx > 165)
    run, st = _vruns(m)
    cols = (run >= 11) & (run <= 24)
    strokes, x = [], 0
    while x < len(cols):
        if cols[x]:
            s = x
            while x < len(cols) and cols[x]:
                x += 1
            strokes.append((s, x - s, int(np.median(st[s:x])), int(run[s:x].max())))
        x += 1
    strokes = [s for s in strokes if 1 <= s[1] <= 6]
    if not strokes:
        # pale pixels in a row, numeral-high, but no clean strokes: a blurred (scaled-down) numeral, not tier I
        rows = m.any(axis=1).sum()
        cols = m.any(axis=0).sum()
        if 9 <= rows and 6 <= cols and m.sum() >= 25:
            return None, "blurred"
        return 1, "none"
    # the numeral: strokes 3-12 px apart with matching tops; take the rightmost such group
    groups, cur = [], [strokes[0]]
    for s in strokes[1:]:
        prev = cur[-1]
        if s[0] - (prev[0] + prev[1]) <= 9 and abs(s[2] - prev[2]) <= 4:
            cur.append(s)
        else:
            groups.append(cur); cur = [s]
    groups.append(cur)
    g = max(groups, key=lambda g: (len(g), g[-1][0]))
    n = len(g)
    # a V right after the strokes (IV): a pale blob as tall as the strokes, with no upright run
    end = g[-1][0] + g[-1][1]
    top, h = g[0][2], g[0][3]
    v = m[top:top + h, end + 1:end + 14]
    if v.size and v[:h // 2].sum(axis=0).astype(bool).sum() >= 6 and v.mean() > 0.12 and n == 1:
        return 4, "IV"
    if n > 3:
        return None, "strokes:%d" % n
    return (n if n >= 2 else (None if g[0][3] >= 13 else 1)), "strokes:%d" % n


# ---------------------------------------------------------------- occupancy

GOLD_EMPTY = 0.02        # an empty tile has no gold at all (measured 0.000-0.005); a path 0.08+, a room 0.15+
FRAME_ROOM = 0.55        # frame sides covered (2nd lowest of 4): rooms 0.75-1.0, paths 0.0-0.33
LIT_GREEN = 0.15         # green share of the tile: lit 0.27 (dim) / 0.65 (bright), a green icon < 0.08
LIT_BRIGHT = 0.45
POWERED = 0.01           # red corridor share of the tile outside the icon


def hidden(c, ov):
    x, y = (round(t) for t in xy(*c))
    return ov[y - HH:y + HH, x - HW:x + HW]


def visible(c, v, ov):
    """False when the tile is off the picture or under a window."""
    x, y = (round(t) for t in xy(*c))
    if x - HW < 0 or y - HH < 0 or x + HW > FULL[0] or y + HH > FULL[1]:
        return False
    vv, oo = v[y - HH:y + HH, x - HW:x + HW], ov[y - HH:y + HH, x - HW:x + HW]
    return vv[TILE].mean() >= 0.97 and oo[CORE].mean() <= 0.01 and oo[TILE].mean() <= 0.15


def occupancy(p, hid=None):
    """-> ("empty" | "path" | "roomlike" | "unknown", feats)."""
    f = feats(p, hid)
    if f["gold"] < GOLD_EMPTY:
        return "empty", f
    if f.get("partial") and f["frame"] < 0:
        return "unknown", f                                 # too little of the frame line to tell
    if f.get("partial", 0) > 0.03 and FRAME_ROOM > f["frame"] > 0.3:
        return "unknown", f
    if f["frame"] >= FRAME_ROOM:
        return "roomlike", f
    if f["gold"] >= 0.05 and f["frame"] <= 0.45:
        return "path", f
    return "unknown", f


def overlay_mask(a, v):
    ov = np.zeros(v.shape, bool)
    boxes = overlays(a, v)
    for x0, y0, x1, y1 in boxes:
        ov[max(0, y0):y1, max(0, x0):x1] = True
    return ov, boxes


# ---------------------------------------------------------------- icon features

IR = 38                                                    # icon crop half-size
_iy, _ix = np.mgrid[-IR:IR, -IR:IR]
ICON_MASK = ((np.abs(_ix) / 69.3 + np.abs(_iy) / 59.4) < 0.66) & ~((_ix > 8) & (_iy > 2))   # no frame, no numeral
_G = 16                                                    # shape grid


def icon_crop(a, c):
    x, y = (round(t) for t in xy(*c))
    return a[y - IR:y + IR, x - IR:x + IR]


def icon_vec(q):
    """Icon -> unit vector. Gray-level only (rooms can be drawn grayed out, lit green, or in color), so: a
    gradient-orientation histogram on a 4x4 grid plus a coarse z-scored gray picture, inside the frame and away
    from the tier numeral."""
    g = q.mean(axis=2)
    m = ICON_MASK
    gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy) * m
    ang = (np.arctan2(gy, gx) % np.pi) / np.pi * 8         # 8 unsigned orientations
    bins = np.minimum(ang.astype(int), 7)
    cell = (2 * IR) // 4
    hog = np.zeros((4, 4, 8))
    for r in range(4):
        for k in range(4):
            sl = (slice(r * cell, (r + 1) * cell), slice(k * cell, (k + 1) * cell))
            hog[r, k] = np.bincount(bins[sl].ravel(), mag[sl].ravel(), minlength=8)[:8]
    hog = hog.ravel()
    hog = hog / (np.linalg.norm(hog) + 1e-6)
    vals = g[m]
    z = np.where(m, (g - vals.mean()) / (vals.std() + 1e-6), 0)
    small = z.reshape(_G, (2 * IR) // _G, _G, (2 * IR) // _G).mean(axis=(1, 3)).ravel() if (2 * IR) % _G == 0 else \
        np.asarray(Image.fromarray(z.astype(np.float32)).resize((_G, _G), Image.BILINEAR)).ravel()
    small = small / (np.linalg.norm(small) + 1e-6)
    v = np.concatenate([hog, 0.8 * small])
    return v / np.linalg.norm(v)


def icon_color(q):
    """Icon color -> unit vector: a 4x4 histogram of opponent color (red-green, yellow-blue) over the icon's lit
    pixels. Tells a gold medallion from a silver one, an orange emblem from a gray one."""
    p = q.astype(np.float32)[ICON_MASK]
    p = p[p.max(axis=1) > 60]
    if len(p) < 20:
        return np.zeros(16)
    s = p.sum(axis=1) + 1
    o1 = (p[:, 0] - p[:, 1]) / s
    o2 = (p[:, 0] + p[:, 1] - 2 * p[:, 2]) / s
    h = np.histogram2d(np.clip(o1, -0.3, 0.3), np.clip(o2, -0.4, 0.8), bins=(4, 4),
                       range=((-0.3, 0.3), (-0.4, 0.8)))[0].ravel()
    return h / (np.linalg.norm(h) + 1e-6)


COLOR_W = 0.5


def icon_feat(q):
    v = np.concatenate([icon_vec(q), COLOR_W * icon_color(q)])
    return v / np.linalg.norm(v)


# ---------------------------------------------------------------- icon clusters -> names

ICONS = os.path.join(HERE, "vaallens_icons.json")
ICON_MIN = 0.90          # best prototype similarity to accept a cluster (members sit at 0.94-1.0 of their cluster)
ICON_MARGIN = 0.015      # a cluster with another name this close -> the icon is not sure
KIND_MIN = 0.82          # 2.142.0: below ICON_MIN (or not sure of the name), the kind still counts when the two
                         # nearest named clusters are the same kind (a reward room drawn silver: "a reward room")
_icons = None


def load_icons(path=ICONS):
    global _icons
    if _icons is None or path != ICONS:
        with open(path) as fh:
            js = json.load(fh)
        cl = js["clusters"]
        P = np.array([p for c in cl for p in c["protos"]], np.float32)
        owner = np.array([k for k, c in enumerate(cl) for _ in c["protos"]])
        res = (cl, P, owner)
        if path != ICONS:
            return res
        _icons = res
    return _icons


def match_icon(vec, icons):
    """-> (cluster dict or None, similarity, sure)."""
    cl, P, owner = icons
    sims = P @ vec
    best = np.full(len(cl), -1.0)
    np.maximum.at(best, owner, sims)
    order = np.argsort(-best)
    k = order[0]
    if best[k] < ICON_MIN:
        return None, float(best[k]), False
    name = cl[k].get("name") or cl[k]["id"]
    rival = next((o for o in order[1:] if (cl[o].get("name") or cl[o]["id"]) != name), None)
    sure = rival is None or best[k] - best[rival] >= ICON_MARGIN
    return cl[k], float(best[k]), sure


def match_kind(vec, icons):
    """-> the kind the nearest icons agree on (KIND_MIN or closer), or None."""
    cl, P, owner = icons
    sims = P @ vec
    best = np.full(len(cl), -1.0)
    np.maximum.at(best, owner, sims)
    order = [k for k in np.argsort(-best) if cl[k].get("kind")]
    if not order or best[order[0]] < KIND_MIN:
        return None
    k = order[0]
    name = cl[k].get("name") or cl[k]["id"]
    rival = next((o for o in order[1:] if (cl[o].get("name") or cl[o]["id"]) != name), None)
    if rival is None or cl[rival]["kind"] == cl[k]["kind"] or best[k] - best[rival] >= 0.04:
        return cl[k]["kind"]
    return None


# ---------------------------------------------------------------- the board

ATZIRI = (0, 10)


def read(img, icons=None):
    """img: PIL image or array, 2560x1440 coordinates (full frame or the watcher crop, maybe scaled).
    -> {(i, j): {"kind", "icon", "name", "tier", "powered"}, "lit": [(i, j)...], "windows": [boxes]}.
    kind: empty | path | room | reward | architect | key | atziri | unknown. icon: cluster id (rooms and other
    room-like cells), name: room family or special room when the cluster is named. Covered cells are unknown."""
    if isinstance(img, np.ndarray):
        img = Image.fromarray(img.astype(np.uint8))
    read_tiers = scale_of(*img.size) >= MIN_TIER_SCALE
    a, v = to_canvas(img)
    ov, boxes = overlay_mask(a, v)
    icons = icons or (load_icons() if os.path.exists(ICONS) else None)
    out, lit, bright = {}, [], []
    for c in CELLS:
        cell = dict(kind="unknown", icon=None, name=None, tier=None, powered=False)
        out[c] = cell
        if not visible(c, v, ov):
            continue
        p, hid = patch(a, c), hidden(c, ov)
        occ, f = occupancy(p, hid)
        cell["powered"] = bool(f["red"] > POWERED)
        if f["green"] > LIT_GREEN and occ != "roomlike":
            lit.append(c)
            if f["green"] > LIT_BRIGHT:
                bright.append(c)
        if occ != "roomlike":
            cell["kind"] = occ
            continue
        cell["occupied"] = True
        vec = icon_feat(icon_crop(a, c)) if icons else None
        m, sim, sure = (match_icon(vec, icons) if icons else (None, 0.0, False))
        cell["match"] = round(sim, 3)
        if c == ATZIRI:
            cell["kind"], cell["name"] = "atziri", "Atziri"
            cell["icon"] = m["id"] if m else None
            continue
        if m is None or not sure or m.get("kind") in (None, "atziri"):
            cell["icon"] = m["id"] if m else None       # a room-like cell we can't name: kind stays unknown
            k = match_kind(vec, icons) if icons else None
            if k in ("reward", "architect", "key"):    # (a room needs its name; these count by kind alone)
                cell["kind"] = k
            continue
        cell["kind"], cell["icon"], cell["name"] = m["kind"], m["id"], m.get("name")
        if m["kind"] == "room" and read_tiers and not hid[HH + 2:HH + 32, HW + 6:HW + 58].any():     # numeral box in view
            cell["tier"] = tier(p)[0]
    out["lit"] = lit                  # every green tile the game lights for the picked card
    out["lit_bright"] = bright        # the brightly lit ones (the rest are dim green)
    out["windows"] = boxes
    return out


def frame(img):
    """A picture of the whole game (any size) -> the part the console is drawn in, as a 16:9 picture: an ultrawide
    game draws the console in its middle 16:9 (the board's size follows the game's height)."""
    w, h = img.size
    want = round(h * 16 / 9)
    if w > want + 2:
        x0 = (w - want) // 2
        img = img.crop((x0, 0, x0 + want, h))
    elif w < want - 2:                                   # (narrower than 16:9: the board follows the width)
        hh = round(w * 9 / 16)
        img = img.crop((0, (h - hh) // 2, w, (h - hh) // 2 + hh))
    return img


def summary(board):
    """-> {kind: count} of the read tiles (what Vaal Lens shows while it's being tested)."""
    out = {}
    for c in CELLS:
        k = (board.get(c) or {}).get("kind", "unknown")
        out[k] = out.get(k, 0) + 1
    return out


GOLD = [(0, j) for j in range(1, 10)]                     # the gold path: entrance (0, 1) up the middle to Atziri


def seen(board):
    """The console is open when Atziri's tile reads as Atziri (any other picture of the game doesn't)."""
    return bool(board) and (board.get((0, 10)) or {}).get("kind") == "atziri"


def lines(board):
    """A read board -> the card's lines, each with a mark and a word: [(done, text)...], then the counts line."""
    if not seen(board):
        return [], ""
    kind = {c: (board.get(c) or {}).get("kind") for c in CELLS}
    gold = sum(1 for c in GOLD if kind[c] not in (None, "empty", "unknown"))
    key = any(k == "key" for k in kind.values())
    arch = any(k == "architect" for k in kind.values())
    n = summary(board)
    marks = [(gold == len(GOLD), f"Gold path · {gold} of {len(GOLD)}"),
             (key, "Key room placed" if key else "Key room not placed"),
             (arch, "Architect found" if arch else "Architect not found")]
    count = " · ".join(f"{n.get(k, 0)} {w}" for k, w in (("room", "rooms"), ("path", "paths"), ("reward", "reward rooms")))
    return marks, count


def placing(game):
    """2.141.0: the game window (left, top, width, height) -> (scale, left, top) of the 2560x1440 console frame on
    screen (frame() in reverse): a board point (x, y) is at (left + x * scale, top + y * scale)."""
    gx, gy, gw, gh = game
    want = round(gh * 16 / 9)
    if gw > want + 2:
        return gh / FULL[1], gx + (gw - want) // 2, gy
    if gw < want - 2:
        hh = round(gw * 9 / 16)
        return gw / FULL[0], gx, gy + (gh - hh) // 2
    return gh / FULL[1], gx, gy


def on_screen(game, x, y):
    s, left, top = placing(game)
    return left + x * s, top + y * s


# 2.142.0: the side panels keep to the game window's edges (the board keeps to the middle 16:9): the card list
# (Room Cards) on the left, the Medallions panel on the right. Boxes in 2560x1440 frame coordinates.
CARD_BOX = (40, 200, 480, 1150)
MEDAL_BOX = (1700, 560, 2560, 1110)      # the panel and where a hovered medallion's tooltip shows (left of it)
DIAMOND_X = (250, 440)                   # a card's diamond, from the card list box's left


def side_box(game, box, right=False):
    """A frame box -> on screen, kept to the game's left (or right) edge."""
    s, _left, top = placing(game)
    gx, gy, gw, gh = game
    x0, y0, x1, y1 = box
    if right:
        return (int(gx + gw - (FULL[0] - x0) * s), int(top + y0 * s), int(gx + gw - (FULL[0] - x1) * s),
                int(top + y1 * s))
    return int(gx + x0 * s), int(top + y0 * s), int(gx + x1 * s), int(top + y1 * s)


def card_box(game):
    return side_box(game, CARD_BOX)


def card_name(lines):
    """OCR lines of the card list -> the one card's name, or None (none, or more than one)."""
    names = card_names(lines)
    return names[0][0] if len(names) == 1 else None


def card_names(lines):
    """-> [(name, y middle in the picture)] of the cards read, top to bottom (a two-line name joined)."""
    from . import vaallens_plan as VP
    rows = [(" ".join(str(t).split()), b or (0, k * 100, 0, k * 100 + 20)) for k, (t, b) in enumerate(lines or [])]
    rows.sort(key=lambda r: r[1][1])
    out, k = [], 0
    while k < len(rows):
        t, b = rows[k]
        if k + 1 < len(rows) and not VP.card(t):
            t2, b2 = rows[k + 1]
            if b2[1] - b[3] < (b[3] - b[1]) * 1.2 and VP.card(t + " " + t2):
                out.append((t + " " + t2, (b[1] + b2[3]) / 2))
                k += 2
                continue
        if VP.card(t):
            out.append((t, (b[1] + b[3]) / 2))
        k += 1
    return out


def card_pick(img, lines, up=1.0):
    """The card list's picture and its OCR lines (read at `up` times its size) -> the picked card's name: the one
    whose diamond glows (gold share well above the others), or the only card. None: not known."""
    names = card_names(lines)
    if not names:
        return None
    if len(names) == 1:
        return names[0][0]
    a = np.asarray(img.convert("RGB")).astype(np.int32)
    s = img.height / (CARD_BOX[3] - CARD_BOX[1])
    x0, x1 = int(DIAMOND_X[0] * s), int(DIAMOND_X[1] * s)
    glow = []
    for name, y in names:
        y = int(y / up)
        p = a[max(0, y - int(75 * s)):y + int(75 * s), x0:x1]
        if not p.size:
            glow.append(0.0)
            continue
        r, g, b = p[..., 0], p[..., 1], p[..., 2]
        glow.append(float(((r > 170) & (g > 140) & (b < 140)).mean()))
    best = max(range(len(names)), key=lambda k: glow[k])
    rest = sorted(glow[:best] + glow[best + 1:])
    mid = rest[len(rest) // 2] if rest else 0.0
    return names[best][0] if glow[best] >= 0.04 and glow[best] > 3 * mid else None
