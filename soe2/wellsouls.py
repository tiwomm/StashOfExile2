"""2.81.0: Desecration Helper - the tier of each option the Well of Souls offers (feedback: "read desecration mods from
the desecration window, compare them against tier database and show the tier ... as a small overlaid helper").

How it works:
  * Client.txt says you entered The Well of Souls (area Abyss_Hub) -> the helper is on while you're there (no
    always-on watcher; feedback). A small notice over the game says so.
  * While there, a light look at where the window opens (screen center, or the space left of the inventory): its
    title plate is the warm parchment color. Only then is the option box read (Windows' own text reader).
  * Each option -> its wording with the numbers taken out -> tierdata.json (built by tools/build_tierdata.py from
    the game data, RePoE): every tier of that mod per item type, with its value ranges. The item type comes from
    the options themselves (Movement Speed only rolls on boots ...) and from the item's picture in the slot (matched
    against the game's own item art). T1 = the best tier for that item type.
  * The three Abyss lords' own mods (Kurgal, Amanamu, Ulaman) have one range: they show as Abyss with where the roll
    sits in it.
GGG ToS: it only looks at your screen and draws tags on top; nothing is sent to the game."""
import base64
import difflib
import json
import os
import re

from .config import APP_DIR, RESOURCE_DIR, P

FILE = "tierdata.json"
AREAS = ("Abyss_Hub",)                    # The Well of Souls (the hub with the Well; the pinnacle arena shares the name)
WELL_NAMES = ("the well of souls", "well of souls")     # 2.125.7: the scene's name, as the Session tracker shows it


def is_well_name(name):
    """The game's scene name is The Well of Souls (2.125.7: a new area id still wakes the helper)."""
    return str(name or "").strip().lower() in WELL_NAMES
LORDS = ("kurgal_mod", "amanamu_mod", "ulaman_mod")
FP = 16                                   # item-art fingerprint size (FP x FP gray + mask)

# Where the window is, in game heights (measured at 2560x1440, the same at any 16:9 size): the option box's center is
# the screen's center, or the center of the space left of the open inventory (INV wide).
INV = 0.613
TITLE = (-0.095, 0.188, 0.095, 0.222)     # the title plate, around the center x (x0, y0, x1, y1)
BOX = (-0.24, 0.452, 0.24, 0.682)         # the three options
SLOT = (-0.055, 0.236, 0.055, 0.441)      # the item's picture
ROWS = 3
PARCH = 0.45                              # share of the title plate that must look like parchment


def clean(text):
    t = re.sub(r"\[([^\]|]*\|)?([^\]]*)\]", r"\2", str(text or ""))
    return re.sub(r"\s+", " ", t.replace("\n", " / ")).strip()


NUM = re.compile(r"\((-?\d+(?:\.\d+)?)[-–](-?\d+(?:\.\d+)?)\)|(-?\d+(?:\.\d+)?)")


def template(text):
    """'+(13-17)% to Cold and Chaos Resistances' / '+17% TO COLD AND CHAOS RESISTANCES' -> '#% to cold and chaos
    resistances' (lower case, numbers and + signs out - the reader often drops a +)."""
    t = clean(text).lower().replace("+", "")
    t = NUM.sub("#", t)
    t = re.sub(r"[^a-z0-9#%/ ,.'-]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def numbers(text):
    """The numbers in a line, in order: a range '(13-17)' counts as one (its min, max); a plain number (n, n)."""
    out = []
    for m in NUM.finditer(clean(text).replace("+", "")):
        if m.group(1) is not None:
            out.append((float(m.group(1)), float(m.group(2))))
        else:
            v = float(m.group(3))
            out.append((v, v))
    return out


# ================================================================ the data
_DATA = {}


def data():
    if _DATA.get("d") is None:
        d = None
        for path in (P(FILE), os.path.join(RESOURCE_DIR, FILE), os.path.join(APP_DIR, FILE)):
            try:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
                break
            except (OSError, ValueError):
                continue
        _DATA["d"] = d or {"mods": {}, "bases": [], "arts": {}}
    return _DATA["d"]


def weight(spawn, tags):
    """The game's rule: the first spawn tag the item has decides (0 = never). The lords' tags count as present (an
    omen picks the lord)."""
    for tag, w in spawn:
        if tag in tags or tag in LORDS:
            return w
    return 0


def find(tpl):
    """A read line's template -> the data's template (exact, else the closest one that's close enough)."""
    mods = data()["mods"]
    if tpl in mods:
        return tpl
    hit = difflib.get_close_matches(tpl, list(mods), n=1, cutoff=0.86)
    return hit[0] if hit else None


def tiers_for(tpl, tags):
    """[(entry, tier, of)] for this template on an item with these tags. Entries: {g, k, l, r, s, a}."""
    out = []
    by_group = {}
    for e in data()["mods"].get(tpl) or []:
        if weight(e["s"], tags) > 0:
            by_group.setdefault(e["g"], []).append(e)
    for g, es in by_group.items():
        es = sorted(es, key=lambda e: -e["l"])
        for i, e in enumerate(es):
            out.append((e, i + 1, len(es)))
    return out


def fits(e, vals):
    rs = e["r"]
    if len(vals) < len(rs) or not rs:
        return False
    return all(lo - 0.05 <= v[0] <= hi + 0.05 for v, (lo, hi) in zip(vals, rs))


def classes_for(tpls):
    """Item classes (and their bases' tag sets) on which every one of these options can roll."""
    out = {}
    for b in data()["bases"]:
        tags = set(b["t"])
        if all(any(weight(e["s"], tags) > 0 for e in data()["mods"].get(t) or []) for t in tpls if t):
            out.setdefault(b["c"], []).append(b)
    return out


def resolve(text):
    """An option's text -> (data template, the text in the data's line order) or (None, text). 2.81.2 (feedback: "+35
    to Accuracy Rating / 10% increased Light Radius" wasn't read): the game can show a hybrid's two lines in another
    order than the data lists them - every order is tried, exact matches before close ones."""
    import itertools
    parts = [p.strip() for p in clean(text).split(" / ") if p.strip()]
    orders = [" / ".join(p) for p in itertools.permutations(parts)] if 1 < len(parts) <= 3 else [clean(text)]
    mods = data()["mods"]
    for t in orders:
        if template(t) in mods:
            return template(t), t
    for t in orders:
        tpl = find(template(t))
        if tpl:
            return tpl, t
    return None, text


def rate(text, bases):
    """One option's text -> {"tpl", "tier", "tier_hi", "of", "abyss", "range", "roll"} for the given candidate bases
    (several tag sets: the tier shows as a range when they disagree), or None when the wording isn't known."""
    tpl, text = resolve(text)
    if tpl is None:
        return None
    vals = numbers(text)
    seen, res = set(), []
    for b in bases or [{"t": ["default"]}]:
        key = tuple(sorted(b["t"]))
        if key in seen:
            continue
        seen.add(key)
        for e, tier, of in tiers_for(tpl, set(b["t"])):
            if fits(e, vals):
                res.append((e, tier, of))
    if not res:
        return {"tpl": tpl, "tier": None}
    if any(not r[0].get("a") for r in res):              # the item pool first; a lord's mod only when nothing else fits
        res = [r for r in res if not r[0].get("a")]
    e, tier, of = min(res, key=lambda x: x[1])
    hi = max(r[1] for r in res)
    lo_r, hi_r = e["r"][0] if e["r"] else (None, None)
    roll = None
    if vals and lo_r is not None and hi_r != lo_r:
        roll = max(0.0, min(1.0, (vals[0][0] - lo_r) / (hi_r - lo_r)))
    return {"tpl": tpl, "tier": tier, "tier_hi": hi, "of": max(r[2] for r in res), "abyss": bool(e.get("a")),
            "range": (lo_r, hi_r), "roll": roll}


# ================================================================ the item's picture
def fingerprint(rgba):
    """An RGBA picture (transparent around the item) -> (gray, mask, aspect) at FP x FP, or None."""
    import numpy as np
    from PIL import Image
    a = np.asarray(rgba.split()[-1])
    ys, xs = np.nonzero(a > 40)
    if len(xs) < 20:
        return None
    im = rgba.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    w, h = im.size
    s = FP / max(w, h)
    im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    c = Image.new("RGBA", (FP, FP), (0, 0, 0, 0))
    c.paste(im, ((FP - im.width) // 2, (FP - im.height) // 2))
    g = np.asarray(c.convert("L"), dtype=np.float32)
    m = np.asarray(c.split()[-1], dtype=np.float32) / 255.0
    return g, m, w / h


def fp_pack(fp):
    import numpy as np
    g, m, r = fp
    raw = np.concatenate([g.astype(np.uint8).ravel(), (m * 255).astype(np.uint8).ravel()]).tobytes()
    return [base64.b64encode(raw).decode(), round(float(r), 3)]


def fp_unpack(p):
    import numpy as np
    raw = np.frombuffer(base64.b64decode(p[0]), dtype=np.uint8).astype(np.float32)
    n = FP * FP
    return raw[:n].reshape(FP, FP), raw[n:].reshape(FP, FP) / 255.0, p[1]


def slot_item(img):
    """The slot's picture (a flat dark red / blue panel with the item on it) -> RGBA with the panel made clear."""
    import numpy as np
    from PIL import Image
    rgb = np.asarray(img.convert("RGB"), dtype=np.int32)
    h, w, _ = rgb.shape
    core = rgb[int(h * .06):int(h * .94), int(w * .12):int(w * .88)]
    edge = np.concatenate([core[:6].reshape(-1, 3), core[-6:].reshape(-1, 3)])
    bg = np.median(edge, axis=0)
    alpha = ((np.abs(core - bg).sum(axis=2) > 60) * 255).astype(np.uint8)
    return Image.fromarray(np.dstack([core.astype(np.uint8), alpha]), "RGBA")


def art_score(a, b):
    import numpy as np
    ga, ma, ra = a
    gb, mb, rb = b
    iou = np.minimum(ma, mb).sum() / max(1e-6, np.maximum(ma, mb).sum())
    m = np.minimum(ma, mb) > 0.5
    if m.sum() < 8:
        return 0.0
    x, y = ga[m] - ga[m].mean(), gb[m] - gb[m].mean()
    ncc = float((x * y).sum() / (np.sqrt((x * x).sum() * (y * y).sum()) + 1e-6))
    return float(0.5 * iou + 0.5 * ncc - 0.3 * abs(np.log(max(1e-3, ra) / max(1e-3, rb))))


def match_art(img, candidates):
    """The slot's picture -> the candidate bases whose art matches best (all of them when it can't tell)."""
    try:
        fp = fingerprint(slot_item(img))
    except Exception:
        fp = None
    arts = data().get("arts") or {}
    if fp is None or not candidates:
        return candidates
    scored = []
    cache = _DATA.setdefault("fp", {})
    for b in candidates:
        a = b.get("a")
        if a not in arts:
            continue
        if a not in cache:
            cache[a] = fp_unpack(arts[a])
        scored.append((art_score(fp, cache[a]), b))
    if not scored:
        return candidates
    best = max(s for s, _b in scored)
    if best < 0.35:                                       # nothing really looks like it
        return candidates
    return [b for s, b in scored if s >= best - 0.02]


# ================================================================ the window on screen
def centre_xs(rect):
    """Where the window's center can be (pixels, game-relative): the screen's center (inventory closed) and the
    center of the space left of the inventory."""
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    return [w / 2, (w - INV * h) / 2]


def part(rect, cx, box):
    """A part of the window (in game heights around the center x) -> screen pixels (l, t, r, b)."""
    h = rect[3] - rect[1]
    return (int(rect[0] + cx + box[0] * h), int(rect[1] + box[1] * h), int(rect[0] + cx + box[2] * h),
            int(rect[1] + box[3] * h))


def plate_share(img):
    """How much of the title area looks like its light warm parchment plate (0-1)."""
    px = list(img.convert("RGB").resize((40, 10)).getdata())
    hit = sum(1 for r, g, b in px if r > 150 and g > 120 and b > 70 and 15 <= r - b <= 120)
    return hit / len(px)


def rows_from_lines(lines, box_h):
    """OCR lines inside the option box -> up to ROWS texts (a two-line option is one row: a hybrid mod)."""
    rows = [[] for _ in range(ROWS)]
    for text, b in lines:
        mid = (b[1] + b[3]) / 2
        i = int(mid / (box_h / ROWS))
        if 0 <= i < ROWS and text.strip():
            rows[i].append((b[1], text.strip()))
    return [" / ".join(t for _y, t in sorted(r)) for r in rows]


def label(r):
    """A rating -> the tag's text."""
    if r is None:
        return "?"
    if r.get("tier") is None:
        return "not a known roll"
    if r.get("abyss"):
        lo, hi = r["range"]
        fmt = (lambda v: f"{v:g}")
        return f"Abyss  {fmt(lo)}–{fmt(hi)}" + (f"  ·  {round(r['roll'] * 100)}%" if r.get("roll") is not None else "")
    return f"T{r['tier']}" if r["tier"] == r["tier_hi"] else f"T{r['tier']}–{r['tier_hi']}"   # 2.81.1: no "of N"
