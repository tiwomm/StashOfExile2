"""2.60.0 Theme packs: the whole app's look as data (themes/*.json), swapped live from Settings > Appearance.

GGG ToS: looks only. Nothing here reads or touches the game.

How it fits the app (no module had to change its colors):
  * style.C stays the app's palette dict. apply() rewrites it IN PLACE from the pack's roles (LEGACY below), so
    every C["panel"] read after a swap gets the new color.
  * Every color handed to Tk already goes through style.theme_color() (hooked into tk / ttk since 2.0.0). That is
    tone() now: a color that was a C value maps to the pack's value; the app's other built-in steel blues are moved
    onto the pack by lightness (nearest palette anchor); everything else (rarity colors, greens, reds) is kept.
  * Swapping while the app runs: walk() visits every widget, canvas item, text / tree tag and menu entry and
    re-tones its colors; ttk styles are rebuilt (style.setup_style) and every other style call is replayed.
  * Pack chrome (gradients, textures, bevelled button faces, meters) is drawn from the pack's own keys.
A pack lists only what it changes; the rest comes from "extends" (another pack) and then DEFAULTS.
Drop a .json into %APPDATA%/StashOfExile2/themes to add your own.
"""

import colorsys
import copy
import json
import math
import os
import random
import re
from . import buglog

DEFAULT = "emberforge"            # the default look (2.60.0)
IDENTITY = "midnight"             # the look the app shipped with until 2.59.0 - no remapping at all

# old C key -> pack role (or a callable on the pack's colors for keys packs rarely set)
LEGACY = {
    "bg": "chassis", "panel": "surface", "panel2": "surface_raised", "line": "border", "gold_dim": "border_light",
    "steel": "text_soft", "text": "text", "muted": "text_muted", "accent": "accent", "good": "money",
    "green": "good", "red": "bad", "blue": "link", "purple": "purple", "orange": "orange", "rare": "rare",
    "magic": "magic", "sel": "selection", "odd": "surface_sunken", "stripe": "stripe", "key": "surface_high",
    "warn_bg": "warn_bg", "bad_bg": "bad_bg", "ok_bg": "ok_bg",
}
# the app's chrome colors: unknown blues are placed by lightness between these
ANCHOR_KEYS = ("bg", "odd", "panel", "stripe", "panel2", "key", "line", "sel", "gold_dim", "muted", "steel", "text")

DEFAULTS = {
    "schema": 1, "id": "base", "name": "Base", "description": "", "light": False,
    "colors": {
        "chassis": "#090e17", "surface": "#0e1522", "surface_raised": "#131c2e", "surface_sunken": "#0b111c",
        "surface_high": "#26354f", "border": "#2b3d5f", "border_light": "#3d5582", "border_dark": "#070b13",
        "shadow": "#000000", "text": "#dbe4f2", "text_muted": "#7d8da8", "text_strong": "#ffffff",
        "accent": "#ffa63d", "accent_2": "#6aa6ff", "selection": "#1b4a96", "stripe": "#16213a",
        "good": "#5fd38a", "warn": "#f2b33d", "bad": "#ff6b5e", "money": "#ffd25a", "link": "#6aa6ff",
        "purple": "#b794f6", "orange": "#ff9d3a", "rare": "#ffff77", "magic": "#8f9bff", "unique": "#af6025",
    },
    "fonts": {"head": ["Segoe UI Semibold", "Segoe UI", "DejaVu Sans"], "num": ["Consolas", "DejaVu Sans Mono"]},
    "bars": {
        "title": {"fill": [[0, "#2a4a7c"], [1, "#1c3360"]], "top": "#86a9de", "bottom": "#070b13",
                  "text": "#ffffff", "texture": "none"},
        "title_off": {"fill": [[0, "#1a2a4c"], [1, "#111b30"]], "top": "#2b3d5f", "bottom": "#070b13",
                      "text": "#aab6cc", "texture": "none"},
        # 2.63.0: the header strip over a section (the list, the item panel)
        "section": {"fill": [[0, "#1c2c4a"], [1, "#131f36"]], "top": "#2b3d5f", "bottom": "#070b13",
                    "text": "accent", "texture": "none"},
    },
    # 2.63.0: the sunken frame around a list - [top-left, bottom-right] colors, outside in
    "panels": {"viewport": {"edges": [["#070b13", "#2b3d5f"], ["#000000", "#0b111c"]]}},
    "buttons": {
        "normal": {"fill": [[0, "#2f4a7c"], [1, "#1f3256"]], "hover": [[0, "#3a5a94"], [1, "#25395f"]],
                   "pressed": [[0, "#16233f"], [1, "#25395f"]], "border": "#0b1424", "hover_border": "#6c90cc",
                   "inner": "#5578b4", "radius": 0, "text": "#e6eeff", "text_hover": "#ffffff"},
        "heading": {"fill": [[0, "#2a4270"], [1, "#1c2f52"]], "hover": [[0, "#33508a"], [1, "#22365a"]],
                    "pressed": [[0, "#16233f"], [1, "#22365a"]], "border": "#0b1424", "hover_border": "#0b1424",
                    "inner": "#4f6c9e", "radius": 0, "text": "#cfe0ff", "text_hover": "#ffffff"},
    },
    "card": {"header": "plate", "border": "border_light", "sep": "border"},
    "meter": {"style": "bar", "on": "good", "off": "surface_high"},
}


# ------------------------------------------------------------------ color helpers
def _rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _hex(r, g, b):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in (r, g, b))


def mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    t = max(0.0, min(1.0, t))
    return _hex(*(x + (y - x) * t for x, y in zip(ra, rb)))


def hls(c):
    return colorsys.rgb_to_hls(*(v / 255 for v in _rgb(c)))


def from_hls(h, l_, s):
    return _hex(*(v * 255 for v in colorsys.hls_to_rgb(h, max(0.0, min(1.0, l_)), max(0.0, min(1.0, s)))))


def grad_at(stops, t):
    """Color at t (0..1) on [(pos, color)] stops; the same pos twice = a hard edge (gloss)."""
    if t <= stops[0][0]:
        return stops[0][1]
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if p0 <= t <= p1:
            return c0 if p1 == p0 else mix(c0, c1, (t - p0) / (p1 - p0))
    return stops[-1][1]


_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def is_hex(v):
    return isinstance(v, str) and bool(_HEX.match(v))


# ------------------------------------------------------------------ packs
def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


class Theme:
    """One resolved pack. c(role) -> '#rrggbb'; a role may name another role."""

    def __init__(self, data, source=None):
        self.data, self.source = data, source
        self.id, self.name = data["id"], data.get("name", data["id"])
        self.light = bool(data.get("light"))

    def c(self, key, fallback="#ff00ff"):
        cols, n = self.data["colors"], 0
        while isinstance(key, str) and not key.startswith("#") and n < 8:
            key, n = cols.get(key, fallback), n + 1
        return key if is_hex(key) else fallback

    def grad(self, stops):
        return [(float(p), self.c(col)) for p, col in stops]

    def part(self, *path, default=None):
        node = self.data
        for p in path:
            if not isinstance(node, dict) or p not in node:
                return default
            node = node[p]
        return node

    def legacy(self):
        """The pack as the app's C palette."""
        c = self.c
        cols = self.data["colors"]
        out = {}
        for key, role in LEGACY.items():
            if role in cols:
                out[key] = c(role)
        out.setdefault("steel", mix(c("text"), c("text_muted"), 0.45))
        out.setdefault("warn_bg", mix(c("surface"), c("warn"), 0.14))
        out.setdefault("bad_bg", mix(c("surface"), c("bad"), 0.14))
        out.setdefault("ok_bg", mix(c("surface"), c("good"), 0.12))
        return out


def pack_dirs():
    from .config import DATA_DIR, RESOURCE_DIR
    return [os.path.join(RESOURCE_DIR, "themes"), os.path.join(str(DATA_DIR), "themes")]


def load_packs(dirs=None):
    raw = {}
    for d in dirs or pack_dirs():
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(d, fn), encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("schema", 1) == 1 and data.get("id"):
                        raw[data["id"]] = (data, os.path.join(d, fn))
                except Exception as e:           # a broken pack never breaks the app
                    print("theme pack skipped:", fn, e)

    def resolve(tid, depth=0):
        data, src = raw[tid]
        parent = data.get("extends")
        base = resolve(parent, depth + 1).data if parent in raw and parent != tid and depth < 6 else DEFAULTS
        return Theme(_merge(base, data), src)
    packs = {tid: resolve(tid) for tid in raw}
    if not packs:
        packs[IDENTITY] = Theme(_merge(DEFAULTS, {"id": IDENTITY, "name": "Midnight Steel"}))
    return packs


PACKS = {}


def packs():
    if not PACKS:
        PACKS.update(load_packs())
    return PACKS


def ordered():
    p = packs()
    return sorted(p.values(), key=lambda t: (t.data.get("order", 99), t.name))


def pick_id(tid):
    p = packs()
    return tid if tid in p else (DEFAULT if DEFAULT in p else next(iter(p)))


# ------------------------------------------------------------------ the running look
class _State:
    def __init__(self):
        self.base = {}            # C as shipped (style._BASE)
        self.base_rev = {}        # shipped value -> C key
        self.C = None             # style.C (rewritten in place)
        self.theme = None
        self.identity = True
        self.rev = {}             # current C value -> key
        self.src = {}             # every color handed out -> its shipped (base) color (all packs)
        self.cur_src = {}         # the same, for the running pack only
        self.cache = {}
        self.anchors = []         # (L, base hex, key) sorted
        self.flip = 1             # -1 when the pack is light (text darker than the surface)
        self.subs = []
        self.skip = set()         # canvases that repaint themselves


ST = _State()


def init(C, base):
    ST.C, ST.base = C, dict(base)
    ST.base_rev = {}
    for k, v in base.items():
        ST.base_rev.setdefault(v.lower(), k)
    ST.anchors = sorted((hls(base[k])[1], base[k].lower(), k) for k in ANCHOR_KEYS if k in base)


def set_theme(theme, accent=None):
    """Make theme the running look: C rewritten, tone() follows it. (style.relook() also repaints the app.)"""
    ST.theme = theme
    ST.identity = theme.id == IDENTITY and not accent
    pal = dict(ST.base)
    if theme.id != IDENTITY:
        pal.update(theme.legacy())
    if accent:
        pal["accent"] = accent if not theme.light else mix(accent, "#000000", 0.5)   # (a bright accent on a light pack
    ST.C.clear()                                                                      #  is darkened to stay readable)
    for k, v in pal.items():                 # pure white / black in a pack would be taken for the app's own
        if v.lower() in _NEUTRAL:            # literal white / black text - nudge them one step
            pal[k] = "#fefefe" if v.lower() == "#ffffff" else "#010101"
    ST.C.update(pal)
    ST.rev = {}
    for k, v in pal.items():
        ST.rev.setdefault(v.lower(), k)
    ST.cache, ST.cur_src = {}, {}
    lt, lb = hls(pal["text"])[1], hls(pal["bg"])[1]
    ST.flip = -1 if lt < lb else 1


def base_of(c):
    """The shipped color a color on screen stands for (this pack's own mapping first)."""
    c = c.lower()
    k = ST.rev.get(c)                       # a palette value first: it IS that palette color
    if k:
        return ST.base[k].lower()
    return ST.cur_src.get(c) or ST.src.get(c, c)


def from_base(b):
    k = ST.base_rev.get(b)
    if k and k in ST.C:
        return ST.C[k].lower()
    if ST.identity:
        return b
    h, l_, s = hls(b)
    if 0.50 <= h <= 0.72 and s > 0.06:                  # the app's steel blues -> the pack, by lightness
        la, ahex, key = min(ST.anchors, key=lambda a: abs(a[0] - l_))
        tgt = ST.C[key]
        th, tl, ts = hls(tgt)
        sa = hls(ahex)[2]
        sat = ts * (min(1.6, s / sa) if sa > 0.02 else 1)
        return from_hls(th, max(0.03, min(0.97, tl + (l_ - la) * ST.flip)), sat)   # (never pure white / black)
    if ST.theme is not None and ST.theme.light:
        if l_ > 0.55:                         # light / bright text (white, gold, amber ...) on a light pack -> a dark
            return from_hls(h, max(0.1, min(0.36, 0.08 + (1 - l_) * 0.6)), min(s, 0.75))   # shade of the same hue
        if l_ < 0.22:                         # dark leftovers (near-black browns / greys) -> the pack's surfaces
            la, ahex, key = min(ST.anchors, key=lambda a: abs(a[0] - l_))
            th, tl, ts = hls(ST.C[key])
            return from_hls(th, max(0.03, min(0.97, tl + (l_ - la) * ST.flip)), ts)
    return b


class raw:
    """with raw(): colors drawn from a pack itself (title bars, meters, previews) go to Tk as they are."""
    depth = 0

    def __enter__(self):
        raw.depth += 1

    def __exit__(self, *a):
        raw.depth -= 1


def self_painted(widget):
    """A canvas that redraws itself from the pack after a swap (walk() leaves it alone)."""
    ST.skip.add(str(widget))
    return widget


_NEUTRAL = {"#ffffff", "#000000"}


def _remember(out, b):
    """out is on screen standing for base color b. Plain white / black and the shipped palette values are never
    taken over for good - they are much more often meant literally."""
    if out == b:
        return
    ST.cur_src[out] = b
    if out not in _NEUTRAL and out not in ST.base_rev:
        ST.src.setdefault(out, b)


KEEP = {"#010203"}         # the see-through key of the banners over the game - never re-colored (2.40.0)


def tone(c):
    """Every color the app hands to Tk passes here (style.theme_color)."""
    if raw.depth or not is_hex(c):
        return c
    lo = c.lower()
    if lo in KEEP:
        return lo
    hit = ST.cache.get(lo)
    if hit:
        return hit
    b = base_of(lo)
    out = from_base(b)
    _remember(out, b)
    ST.cache[lo] = out
    return out


def subscribe(cb, owner=None):
    """cb(theme) after every live swap (things that draw themselves: title bars, the dock, meters ...).
    owner: a widget - forgotten once it is destroyed."""
    ST.subs.append((cb, owner))
    return cb


def notify():
    keep = []
    for cb, owner in ST.subs:
        try:
            if owner is not None and not owner.winfo_exists():
                continue
        except Exception:
            continue
        keep.append((cb, owner))
        try:
            cb(ST.theme)
        except Exception:
            buglog.caught()
    ST.subs[:] = keep


# ------------------------------------------------------------------ live swap
OPTS = {"-background", "-foreground", "-activebackground", "-activeforeground", "-highlightbackground",
        "-highlightcolor", "-selectbackground", "-selectforeground", "-insertbackground", "-disabledforeground",
        "-troughcolor", "-readonlybackground", "-selectcolor", "-disabledbackground", "-inactiveselectbackground",
        "-fill", "-outline", "-activefill", "-activeoutline", "-disabledfill", "-disabledoutline"}
TAG_OPTS = ("-foreground", "-background", "-selectbackground", "-selectforeground")
MENU_OPTS = ("-background", "-foreground", "-activebackground", "-activeforeground", "-selectcolor")
MEM = {}          # (widget, what, item, option) -> (color we put there, what it stands for) - so swaps never drift


def snapshot():
    """The running mapping, taken just before a swap."""
    return {"cur_src": dict(ST.cur_src), "rev": dict(ST.rev), "C": dict(ST.C)}


def _translator(old):
    """tr(key, color on screen) -> the color under the NEW pack (old = snapshot() from before set_theme)."""
    near = [(v.lower(), k) for k, v in old["C"].items()]

    def recipe_of(lo):
        k = old["rev"].get(lo)
        if k:
            return ("b", ST.base[k].lower())
        b = old["cur_src"].get(lo)
        if b:
            return ("b", b)
        b = ST.src.get(lo)
        if b:
            return ("b", b)
        r = _rgb(lo)                              # a shade the app mixed itself: follow its nearest palette color
        hexv, key = min(near, key=lambda kv: sum((x - y) ** 2 for x, y in zip(_rgb(kv[0]), r)))
        if sum((x - y) ** 2 for x, y in zip(_rgb(hexv), r)) < 45 ** 2:
            return ("n", key, hls(lo)[1] - hls(hexv)[1])
        return ("b", lo)

    def resolve(rc):
        if rc[0] == "b":
            return from_base(rc[1])
        _, key, dl = rc
        if key not in ST.C:
            return None
        th, tl, ts = hls(ST.C[key])
        return from_hls(th, max(0.03, min(0.97, tl + dl * ST.flip)), ts)

    def tr(key, v):
        lo = v.lower()
        if lo in KEEP:
            return lo
        m = MEM.get(key)
        rc = m[1] if m and m[0] == lo else recipe_of(lo)    # the app changed it since the last swap: read it again
        out = resolve(rc) or lo
        MEM[key] = (out, rc)
        if rc[0] == "b":
            _remember(out, rc[1])
        return out
    return tr


def walk(root, tr):
    """Re-color everything on screen with tr(key, old) -> new."""
    tkc = root.tk
    stack = ["."]
    n = 0
    while stack:
        w = stack.pop()
        try:
            stack.extend(str(k) for k in tkc.splitlist(tkc.call("winfo", "children", w)))
            cls = tkc.call("winfo", "class", w)
        except Exception:
            continue
        n += 1
        if w in ST.skip:
            continue
        _retone_options(tkc, (w, "configure"), (w, "configure"), tr, (w, "o"))
        try:
            if cls == "Canvas":
                for item in tkc.splitlist(tkc.call(w, "find", "all")):
                    _retone_options(tkc, (w, "itemconfigure", item), (w, "itemconfigure", item), tr, (w, "i", item))
            elif cls in ("Text", "Treeview"):
                get = "cget" if cls == "Text" else "configure"
                for tag in tkc.splitlist(tkc.call(w, "tag", "names")):
                    for o in TAG_OPTS:
                        try:
                            v = str(tkc.call(w, "tag", get, tag, o))
                        except Exception:
                            continue
                        if is_hex(v):
                            nv = tr((w, "t", tag, o), v)
                            if nv != v.lower():
                                tkc.call(w, "tag", "configure", tag, o, nv)
            elif cls == "Menu":
                last = tkc.call(w, "index", "end")
                if str(last) != "none":
                    for i in range(int(last) + 1):
                        for o in MENU_OPTS:
                            try:
                                v = str(tkc.call(w, "entrycget", i, o))
                            except Exception:
                                continue
                            if is_hex(v):
                                nv = tr((w, "m", i, o), v)
                                if nv != v.lower():
                                    tkc.call(w, "entryconfigure", i, o, nv)
        except Exception:
            buglog.caught()
    alive = _alive_cache(tkc)
    for k in [k for k in MEM if k[0] not in alive and k[0] != "style"]:
        MEM.pop(k, None)
    return n


def _alive_cache(tkc):
    """(the widgets that still exist - MEM forgets the rest)"""
    out, stack = {"."}, ["."]
    while stack:
        w = stack.pop()
        try:
            kids = [str(k) for k in tkc.splitlist(tkc.call("winfo", "children", w))]
        except Exception:
            continue
        out.update(kids)
        stack.extend(kids)
    return out


def _retone_options(tkc, get, put, tr, key):
    try:
        res = tkc.splitlist(tkc.call(*get))
    except Exception:
        return
    new = []
    for spec in res:
        spec = tkc.splitlist(spec)
        if len(spec) != 5 or spec[0] not in OPTS:
            continue
        v = str(spec[4])
        if v == str(spec[3]):                # Tk's own default (never set by the app): leave it
            continue
        if is_hex(v):
            nv = tr(key + (spec[0],), v)
            if nv != v.lower():
                new += [spec[0], nv]
    if new:
        try:
            tkc.call(*put, *new)
        except Exception:
            buglog.caught()


# ------------------------------------------------------------------ chrome drawing (canvas)
def _seeded(t, salt):
    return random.Random("%s-%s" % (t.id, salt))


def texture(cv, t, kind, x0, y0, x1, y1, base, glow=None, tag="tex"):
    """Procedural textures as canvas items - no image files."""
    w, h = x1 - x0, y1 - y0
    glow = glow or mix(base, "#ffffff", 0.3)
    if kind == "brushed":
        rnd = _seeded(t, "b%d" % w)
        for _ in range(min(220, w * h // 90)):
            y, x = y0 + rnd.randrange(max(1, h)), x0 + rnd.randrange(max(1, w))
            cv.create_line(x, y, min(x1, x + rnd.randrange(12, 70)), y, tags=tag,
                           fill=mix(base, "#ffffff" if rnd.random() < .6 else "#000000", rnd.uniform(.03, .07)))
    elif kind == "scanline":
        for y in range(y0, y1, 3):
            cv.create_line(x0, y, x1, y, fill=mix(base, "#000000", .28), tags=tag)
    elif kind in ("stone", "ash"):
        rnd = _seeded(t, "s%dx%d" % (w, h))
        for _ in range(min(700, w * h // 50)):
            x, y = x0 + rnd.randrange(max(1, w)), y0 + rnd.randrange(max(1, h))
            if kind == "ash" and rnd.random() < .08:
                col = mix(base, glow, rnd.uniform(.2, .4))
            else:
                col = mix(base, "#000000" if rnd.random() < .55 else "#ffffff", rnd.uniform(.08, .16))
            cv.create_rectangle(x, y, x + 1, y + 1, outline="", fill=col, tags=tag)
    elif kind == "fronds":
        rnd = _seeded(t, "f%dx%d" % (w, h))
        for _ in range(min(360, w * h // 70)):
            x, y = x0 + rnd.randrange(max(1, w)), y0 + rnd.randrange(max(1, h))
            cv.create_line(x, y, x + rnd.uniform(-5, 5), y - rnd.uniform(4, 11), tags=tag,
                           fill=mix(base, glow if rnd.random() < .35 else "#000000", rnd.uniform(.08, .2)))
    elif kind == "veins":
        rnd = _seeded(t, "v%dx%d" % (w, h))
        for _ in range(max(1, w * h // 14000)):
            x, y = x0 + rnd.randrange(max(1, w)), y0 + rnd.randrange(max(1, h))
            pts = [x, y]
            for _ in range(rnd.randrange(5, 12)):
                x, y = x + rnd.uniform(-14, 22), y + rnd.uniform(-9, 9)
                pts += [x, y]
            cv.create_line(*pts, fill=mix(base, glow, .10), width=3, tags=tag)
            cv.create_line(*pts, fill=mix(base, glow, .38), width=1, tags=tag)
    elif kind == "embers":
        rnd = _seeded(t, "e%dx%d" % (w, h))
        for _ in range(min(200, w * h // 140)):
            x, y, r = x0 + rnd.randrange(max(1, w)), y0 + rnd.randrange(max(1, h)), rnd.randrange(3, 8)
            cv.create_arc(x - r, y - r, x + r, y + r, start=200, extent=140, style="arc", tags=tag,
                          outline=mix(base, "#000000", .35))
            cv.create_arc(x - r, y - r, x + r, y + r, start=20, extent=140, style="arc", tags=tag,
                          outline=mix(base, "#ffffff", .07))
        for _ in range(max(3, w * h // 3000)):
            x, y = x0 + rnd.randrange(max(1, w)), y0 + rnd.randrange(max(1, h))
            cv.create_rectangle(x, y, x + 1, y + 1, outline="", fill=mix(base, glow, rnd.uniform(.4, .9)), tags=tag)
    elif kind == "glyphs":
        step = 26
        for gy in range(y0 + 6, y1, step):
            for gx in range(x0 + 6 + (gy // step % 2) * 13, x1, step):
                pts = (gx, gy + 8, gx, gy + 4, gx + 4, gy + 4, gx + 4, gy, gx + 10, gy, gx + 10, gy + 4,
                       gx + 14, gy + 4, gx + 14, gy + 8)
                cv.create_line(*pts, fill=mix(base, "#000000", .3), tags=tag)
                cv.create_line(*[v + 1 for v in pts], fill=mix(base, glow, .12), tags=tag)


def _paint_bar(cv, kind="title", tag="grad"):
    """A title bar from the running pack: gradient, texture, top / bottom lines. No icons - every pack keeps the
    app's own icons (2.60.0)."""
    t = ST.theme
    cv.delete(tag)
    w, h = max(cv.winfo_width(), 2), max(cv.winfo_height(), 2)
    spec = t.part("bars", kind) or t.part("bars", "title")
    stops = t.grad(spec["fill"])
    for y in range(h):
        cv.create_line(0, y, w, y, fill=grad_at(stops, y / max(1, h - 1)), tags=tag)
    tex = spec.get("texture", "none")
    if tex and tex != "none":
        texture(cv, t, tex, 0, 0, w, h, grad_at(stops, .5),
                glow=t.c(spec["texture_color"]) if spec.get("texture_color") else None, tag=tag)
    for key, y in (("top", 0), ("top2", 2), ("bottom", h - 1), ("bottom2", h - 3)):
        if spec.get(key):
            cv.create_line(0, y, w, y, fill=t.c(spec[key]), tags=tag)
    cv.tag_lower(tag)
    return t.c(spec.get("text", "#ffffff"))


def paint_bar(cv, kind="title", tag="grad"):
    with raw():
        return _paint_bar(cv, kind, tag)

def window_colors():
    """(caption, text, border) for the app window's own title bar (2.61.0). A pack may set "window":
    {"caption", "text", "border"}; otherwise the bottom of its title-bar gradient, its bar text, its light border."""
    t = ST.theme
    w = t.part("window") or {}
    spec = t.part("bars", "title")
    stops = t.grad(spec["fill"])
    cap = t.c(w["caption"]) if w.get("caption") else grad_at(stops, 0.85)
    txt = t.c(w["text"]) if w.get("text") else t.c(spec.get("text", "#ffffff"))
    edge = t.c(w["border"]) if w.get("border") else t.c("border_light")
    return cap, txt, edge


def bar_text(kind="title"):
    t = ST.theme
    spec = t.part("bars", kind) or t.part("bars", "title")
    return t.c(spec.get("text", "#ffffff"))


_FAMILIES = {}
_HEAD = {}


def head_font():
    """The pack's heading family (first one installed). 2.112.2: the PC's font list is read ONCE and the answer
    kept per theme - every title bar asked Windows for the whole list on every redraw (about 100 bars), which
    froze a theme change for minutes (worse once the overlay styles' own fonts were loaded)."""
    import tkinter.font as tkfont
    fams = tuple((ST.theme.part("fonts", "head") if ST.theme else None) or ["Segoe UI"])
    if fams in _HEAD:
        return _HEAD[fams]
    if not _FAMILIES:
        try:
            _FAMILIES.update({f.lower(): f for f in tkfont.families()})
        except Exception:
            return fams[0]
    _HEAD[fams] = next((_FAMILIES[f.lower()] for f in fams if f.lower() in _FAMILIES), "Segoe UI")
    return _HEAD[fams]


def round_rect(cv, x0, y0, x1, y1, r, **kw):
    if r <= 0:
        return cv.create_rectangle(x0, y0, x1, y1, **kw)
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1, x0, y1,
           x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


def _draw_meter(cv, value, w, h, on=None, style=None, tag="meter"):
    """The pack's meter (segments / bar / runes / ticks / orbs). value 0..1; on = color override."""
    t = ST.theme
    cv.delete(tag)
    ms = t.part("meter") or {}
    st = style or ms.get("style", "bar")
    on = on or t.c(ms.get("on", "good"))
    off = t.c(ms.get("off", "surface_high"))
    value = max(0.0, min(1.0, value))
    if st == "segments":
        lcd = t.c(ms.get("lcd_bg", "surface_sunken"))
        cv.create_rectangle(0, 0, w - 1, h - 1, fill=lcd, outline=t.c("border_dark"), tags=tag)
        n = max(6, w // 8)
        seg = (w - 6) / n
        for i in range(n):
            x = 3 + i * seg
            col = on if i < n * .7 else t.c("warn") if i < n * .9 else t.c("bad")
            lit = i < round(value * n)
            cv.create_rectangle(x, 3, x + seg - 2, h - 4, outline="", tags=tag,
                                fill=col if lit else mix(col, lcd, .82))
    elif st == "runes":
        n = max(5, w // 14)
        step = w / n
        r = min(5, h // 2 - 1)
        for i in range(n):
            cx, cy = step * i + step / 2, h / 2
            lit = i < round(value * n)
            cv.create_polygon(cx, cy - r - 1, cx + r, cy, cx, cy + r + 1, cx - r, cy, tags=tag,
                              fill=on if lit else off, outline=mix(on, "#000000", .5))
    elif st == "ticks":
        n = max(8, w // 6)
        step = (w - 2) / n
        for i in range(n):
            x = 1 + i * step
            lit = i < round(value * n)
            cv.create_line(x, 2 if i % 4 == 0 else 5, x, h - 2, fill=on if lit else off, width=2, tags=tag)
    elif st == "orbs":
        n = max(5, w // 14)
        step = w / n
        r = min(5, h // 2 - 1)
        for i in range(n):
            cx, cy = step * i + step / 2, h / 2
            lit = i < round(value * n)
            cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=on if lit else off, tags=tag,
                           outline=mix(on, "#000000", .55))
            if lit and r >= 4:
                cv.create_oval(cx - r / 2, cy - r * .7, cx + r * .2, cy - r * .2, outline="", tags=tag,
                               fill=mix(on, "#ffffff", .55))
    else:                                                     # bar
        round_rect(cv, 0, 1, w - 1, h - 2, 3 if h >= 10 else 0, fill=off, outline=t.c("border"), tags=tag)
        fw = max(3, int((w - 3) * value))
        for i in range(max(1, h - 5)):
            cv.create_line(2, 3 + i, fw, 3 + i, fill=mix(mix(on, "#ffffff", .4), on, i / max(1, h - 6)), tags=tag)


def draw_meter(cv, value, w, h, on=None, style=None, tag="meter"):
    with raw():
        return _draw_meter(cv, value, w, h, on, style, tag)

def _card_header(cv, x0, y0, x1, y1, rarity_col, bg):
    """The item card's name band in the pack's style (plate / glass / ornate / notch / stepped / rite)."""
    t = ST.theme
    hdr = t.part("card", "header", default="plate")
    rc = rarity_col
    if hdr == "glass":
        mid = (y0 + y1) // 2
        top, bot = mix(rc, "#ffffff", .82), mix(rc, "#ffffff", .62)
        for y in range(y0, y1):
            cv.create_line(x0, y, x1, y, fill=top if y < mid else mix(bot, mix(rc, "#ffffff", .75),
                                                                       (y - mid) / max(1, y1 - mid)))
        round_rect(cv, x0, y0, x1, y1, 3, fill="", outline=mix(rc, "#ffffff", .35))
        return mix(rc, "#000000", .35)
    if hdr == "ornate":
        cv.create_rectangle(x0, y0, x1, y1, fill=mix(bg, "#000000", .3), outline="")
        for yy in (y0, y0 + 3, y1 - 3, y1):
            cv.create_line(x0 + 10, yy, x1 - 10, yy, fill=mix(rc, bg, .25 if yy in (y0, y1) else .65))
    elif hdr == "notch":
        cv.create_rectangle(x0, y0, x1, y1, fill=mix(rc, bg, .86), outline="")
        for yy in range(y0, y1, 3):
            cv.create_line(x0, yy, x1, yy, fill=mix(rc, bg, .8))
        cv.create_line(x0, y1, x1, y1, fill=rc, width=2)
        cv.create_rectangle(x0, y0, x0 + 3, y1, fill=rc, outline="")
    elif hdr == "stepped":
        cv.create_rectangle(x0 + 12, y0, x1 - 12, y1, fill=mix(rc, bg, .82), outline="")
        for x, d in ((x0, 1), (x1, -1)):
            pts = [x + 12 * d, y0, x + 8 * d, y0, x + 8 * d, y0 + 8, x + 4 * d, y0 + 8, x + 4 * d, y0 + 16,
                   x, y0 + 16, x, y1 - 16, x + 4 * d, y1 - 16, x + 4 * d, y1 - 8, x + 8 * d, y1 - 8,
                   x + 8 * d, y1, x + 12 * d, y1]
            cv.create_polygon(*pts, fill=mix(rc, bg, .82), outline="")
            cv.create_line(*pts, fill=mix(rc, bg, .3))
        cv.create_line(x0 + 12, y0, x1 - 12, y0, fill=mix(rc, bg, .3))
        cv.create_line(x0 + 12, y1, x1 - 12, y1, fill=mix(rc, bg, .3))
    elif hdr == "rite":
        base = mix(bg, "#000000", .35)
        cv.create_rectangle(x0, y0, x1, y1, fill=base, outline="")
        for i in range(10):
            cv.create_line(x0, y1 - i, x1, y1 - i, fill=mix(base, rc, .12 * (1 - i / 10)))
        cv.create_line(x0 + 16, y1, x1 - 16, y1, fill=t.c("accent"), width=2)
    else:                                                     # plate
        for i in range(y1 - y0):
            cv.create_line(x0, y0 + i, x1, y0 + i, fill=mix(mix(rc, bg, .72), bg, i / max(1, y1 - y0)))
        cv.create_line(x0, y1, x1, y1, fill=mix(rc, bg, .4))
    return rc


def card_header(cv, x0, y0, x1, y1, rarity_col, bg):
    with raw():
        return _card_header(cv, x0, y0, x1, y1, rarity_col, bg)

def _preview(cv, t, w=168, h=92):
    """A small picture of a pack for the Appearance gallery (drawn from the pack itself, not the running look)."""
    cv.delete("all")
    c = t.c
    cv.create_rectangle(0, 0, w, h, fill=c("chassis"), outline=c("border"))
    spec = t.part("bars", "title")
    stops = t.grad(spec["fill"])
    for y in range(18):
        cv.create_line(1, 1 + y, w - 1, 1 + y, fill=grad_at(stops, y / 17))
    if spec.get("bottom"):
        cv.create_line(1, 18, w - 1, 18, fill=t.c(spec["bottom"]))
    cv.create_rectangle(8, 26, w - 8, h - 8, fill=c("surface"), outline=c("border"))
    for i, (col, ln) in enumerate(((c("text"), 70), (c("text_muted"), 52), (c("rare"), 60))):
        cv.create_line(16, 36 + i * 9, 16 + ln, 36 + i * 9, fill=col, width=3)
    bs = t.part("buttons", "primary") or t.part("buttons", "normal")
    bst = t.grad(bs["fill"])
    for y in range(12):
        cv.create_line(w - 62, 32 + y, w - 16, 32 + y, fill=grad_at(bst, y / 11))
    cv.create_rectangle(w - 62, 32, w - 16, 44, outline=t.c(bs["border"]))
    ms = t.part("meter") or {}
    on, off, st = t.c(ms.get("on", "good")), t.c(ms.get("off", "surface_high")), ms.get("style", "bar")
    n = 8
    for i in range(n):
        x = 16 + i * 9
        col = on if i < 5 else off
        if st in ("runes", "orbs"):
            if st == "runes":
                cv.create_polygon(x + 3, 66, x + 7, 70, x + 3, 74, x - 1, 70, fill=col, outline="")
            else:
                cv.create_oval(x, 66, x + 7, 73, fill=col, outline="")
        elif st == "ticks":
            cv.create_line(x + 3, 65, x + 3, 75, fill=col, width=2)
        else:
            cv.create_rectangle(x, 66, x + 7, 74, fill=col, outline="")
    cv.create_rectangle(w - 62, 62, w - 16, 76, fill=c("selection"), outline="")
    cv.create_line(w - 58, 69, w - 26, 69, fill=c("text_strong") if not t.light else c("text"), width=3)


# ------------------------------------------------------------------ ttk faces (bevelled image elements)
_IMAGES = {}
_ELEMENTS = set()


def preview(cv, t, w=168, h=92):
    with raw():
        return _preview(cv, t, w, h)

def bevel_image(root, key, w, h, stops, border, inner=None, radius=0, top_line=None, bottom_shade=None):
    import tkinter as tk
    if key in _IMAGES:
        return _IMAGES[key]
    img = tk.PhotoImage(master=root, width=w, height=h)
    clear, rows = [], []
    for y in range(h):
        base = grad_at(stops, y / max(1, h - 1))
        row = []
        for x in range(w):
            col, edge = base, False
            if radius:
                cx = radius if x < radius else (w - 1 - radius if x > w - 1 - radius else None)
                cy = radius if y < radius else (h - 1 - radius if y > h - 1 - radius else None)
                if cx is not None and cy is not None:
                    d = math.hypot(x - cx, y - cy)
                    if d > radius + 0.3:
                        clear.append((x, y))
                    elif d > radius - 0.7:
                        edge = True
            if x in (0, w - 1) or y in (0, h - 1):
                edge = True
            if edge:
                col = border
            elif inner and y == 1:
                col = inner
            elif inner and x == 1 and y < h - 2:
                col = mix(base, inner, 0.45)
            elif bottom_shade and y == h - 2:
                col = bottom_shade
            if top_line and y in (1, 2) and not edge:
                col = top_line
            row.append(col)
        rows.append("{" + " ".join(row) + "}")
    img.put(" ".join(rows), to=(0, 0))
    for x, y in clear:
        img.tk.call(img.name, "transparency", "set", x, y, 1)
    _IMAGES[key] = img
    return img


def flat_spec(t, name):
    """P2.5 (2.107.0, feedback: "the buttons feel very amateur"): one flat look in every theme - 2 px corners, no
    gradient or bevel; the theme still gives the colors. Normal: a raised face; primary: the accent; danger: an
    outline in the theme's danger color; heading: list column heads."""
    c = t.c
    if name == "primary":
        a = ST.C.get("accent") or c("accent")
        hv = mix(a, "#000000", .12) if t.data.get("light") else mix(a, "#ffffff", .15)   # (light themes: darker)
        return {"fill": [[0, a], [1, a]], "hover": [[0, hv], [1, hv]],
                "pressed": [[0, mix(a, "#000000", .2)], [1, mix(a, "#000000", .2)]], "border": a,
                "hover_border": mix(a, "#ffffff", .35), "inner": None, "radius": 2, "text": None, "text_hover": None}
    if name == "danger":
        b, bg = c("bad"), c("surface")
        return {"fill": [[0, bg], [1, bg]], "hover": [[0, mix(bg, b, .08)], [1, mix(bg, b, .08)]],
                "pressed": [[0, mix(bg, b, .16)], [1, mix(bg, b, .16)]], "border": b, "hover_border": b, "inner": None,
                "radius": 2, "text": b, "text_hover": c("text_strong")}
    if name == "heading":
        f = c("surface_raised")
        return {"fill": [[0, f], [1, f]], "hover": [[0, c("surface_high")], [1, c("surface_high")]],
                "pressed": [[0, c("surface_sunken")], [1, c("surface_sunken")]], "border": c("border"),
                "hover_border": c("border"), "inner": None, "radius": 0, "text": c("text_muted"),
                "text_hover": c("text")}
    f = c("surface_high")
    return {"fill": [[0, f], [1, f]], "hover": [[0, mix(f, c("accent"), .14)], [1, mix(f, c("accent"), .14)]],
            "pressed": [[0, c("surface_sunken")], [1, c("surface_sunken")]], "border": c("border_light"),
            "hover_border": c("accent"), "inner": None, "radius": 2, "text": c("text"), "text_hover": c("text_strong")}


def button_spec(t, name):
    """A button face spec from the pack; primary / danger are made from the accent / danger color when a pack
    doesn't draw them itself. P2.5 (2.107.0): flat in every theme unless a pack says "buttons": {"flat": false}."""
    if name in ("normal", "primary", "danger", "heading") and (t.part("buttons", "flat") is not False):
        return flat_spec(t, name)
    spec = t.part("buttons", name)
    if spec:
        return spec
    if name in ("primary", "danger"):
        a = ST.C["accent"] if name == "primary" else ST.C["red"]
        if name == "danger":
            a = mix(a, "#000000", 0.45)
        return {"fill": [[0, mix(a, "#ffffff", .25)], [0.5, a], [1, mix(a, "#000000", .25)]],
                "hover": [[0, mix(a, "#ffffff", .38)], [0.5, mix(a, "#ffffff", .1)], [1, mix(a, "#000000", .15)]],
                "pressed": [[0, mix(a, "#000000", .35)], [1, mix(a, "#000000", .15)]],
                "border": mix(a, "#000000", .65), "hover_border": mix(a, "#000000", .65),
                "inner": mix(a, "#ffffff", .5), "radius": (t.part("buttons", "normal") or {}).get("radius", 0),
                "text": None, "text_hover": None}
    return t.part("buttons", "normal")


def make_element(root, style, name, t, spec_name, h, states, w=16, selected_line=None):
    """One image element for a ttk layout: normal / hover / pressed / disabled (+ selected) faces."""
    if name in _ELEMENTS:
        return
    spec = button_spec(t, spec_name)
    r = int(spec.get("radius", 0) or 0)
    tag = "%s|%s|%d|%d" % (name, spec_name, w, h)
    inner = t.c(spec["inner"]) if spec.get("inner") else None
    border = t.c(spec["border"])
    faces = {
        "n": bevel_image(root, tag + "n", w, h, t.grad(spec["fill"]), border, inner, r),
        "h": bevel_image(root, tag + "h", w, h, t.grad(spec["hover"]), t.c(spec.get("hover_border", spec["border"])),
                         inner, r),
        "p": bevel_image(root, tag + "p", w, h, t.grad(spec["pressed"]), border, None, r, bottom_shade=inner),
        "d": bevel_image(root, tag + "d", w, h, [(0, mix(grad_at(t.grad(spec["fill"]), .5), ST.C["panel"], .6))] * 2,
                         mix(border, ST.C["panel"], .5), None, r),
    }
    if selected_line is not None:
        faces["s"] = bevel_image(root, tag + "s", w, h, t.grad(spec["pressed"]), border, inner, r,
                                 top_line=selected_line or None)
    args = [faces["n"]] + [(st, faces[k]) for st, k in states]
    style.element_create(name, "image", *args, border=(r + 3, h // 2 - 1, r + 3, h // 2 - 1), padding=(2, 1),
                         sticky="nsew")
    _ELEMENTS.add(name)


def text_of(t, spec_name, key, fallback):
    spec = button_spec(t, spec_name)
    v = spec.get(key)
    return t.c(v) if v else fallback


def Meter(parent, value=0.0, width=90, height=14, on=None, bg=None):
    """A canvas showing value (0..1) as the pack's meter - the trade-limit bars, mod rolls (2.60.0).
    m.set(value, on=None) changes it; it repaints itself after a theme swap."""
    import tkinter as tk

    class _Meter(tk.Canvas):
        def __init__(self):
            super().__init__(parent, width=width, height=height, highlightthickness=0, bd=0,
                             bg=bg or ST.C["panel"])
            self.value, self.on, self.w, self.h = value, on, width, height
            self_painted(self)
            subscribe(self._relook, owner=self)
            self.bind("<Destroy>", lambda e: ST.skip.discard(str(self)) if e.widget is self else None, add="+")
            self.draw()

        def _relook(self, _t=None):
            try:
                if self.winfo_exists():
                    with raw():
                        self.configure(bg=ST.C["panel"] if not bg else tone(bg))
                    self.draw()
            except tk.TclError:
                pass

        def set(self, value, on=None):
            self.value, self.on = value, on
            self.draw()

        def draw(self):
            draw_meter(self, self.value, self.w, self.h, on=self.on)
    return _Meter()
