"""2.142.0 Vaal Lens (BETA): medallions - what each one does, how good it is, the ones in your hand (the Medallions
panel, V) and whether one on the ground is worth a slot.

Names and effects are the game's (9 medallions). How good each is: lock and upgrade first, Zantipi's last (told by
the player); a capacity medallion is worth nothing once that capacity is full. Uromoti's adds a room - worth more
when that room pays at tier 3 (Corruption Chamber, Sacrificial Chamber, Thaumaturge, Alchemy Lab, Smithy).

The hand is learned, not guessed: hover a medallion in the panel and its tooltip's name is read with the slot under
the mouse; that slot's picture is kept (medallion_icons.json in your data folder: pictures of icons, nothing else),
so the next time the panel opens each slot is known by its picture. Two are known from the start (the lock and the
upgrade arrow)."""
import json
import os
import re

import numpy as np

# name -> (short name, what it does, worth 0-10)
MEDALLIONS = {
    "Juatalotli's Medallion": ("Lock", "Keeps a room through the next destabilization", 10),
    "Quipolatl's Medallion": ("Upgrade", "Raises a room's tier", 9),
    "Estazunti's Medallion": ("Extra restricted room", "One more restricted room card after the Architect", 8),
    "Uromoti's Medallion": ("Add room", "Adds a room card", 5),
    "Hayoxi's Medallion": ("Reroll restricted", "Rerolls a restricted room", 5),
    "Puhuarte's Medallion": ("Reroll cards", "Rerolls the room cards on offer", 4),
    "Xopec's Medallion": ("Crystal capacity", "Crystal capacity +6 (up to 60)", 6),
    "Azcapa's Medallion": ("Medallion slot", "Medallion capacity +1 (up to 6)", 7),
    "Zantipi's Medallion": ("Waystone modifier", "Adds a random waystone modifier to the temple", 1),
}
HIGH_ROOMS = ("Corruption Chamber", "Sacrificial Chamber", "Thaumaturge", "Alchemy Lab", "Smithy")
_KEYS = {re.sub(r"[^A-Z]", "", n.upper()): n for n in MEDALLIONS}
_ROOM = re.compile(r"ADD\s*ROOM\s*[:;]?\s*(.+)", re.I)
_COUNT = re.compile(r"MEDALLIONS?\s*\(?\s*(\d)\s*[/|l]\s*(\d)\s*\)?", re.I)


def letters(t):
    return re.sub(r"[^A-Z]", "", str(t).upper())


def name_of(text):
    """An OCR line -> the medallion's name in it, or None (letters only, so "Zantipi's Medallion" and
    "ZANTIPIS MEDALLION" both match; a near miss of one letter too)."""
    L = letters(text)
    if "MEDALLION" not in L:
        return None
    for k, n in _KEYS.items():
        if k in L:
            return n
    import difflib
    m = difflib.get_close_matches(L[:len(L)], list(_KEYS), 1, 0.88)
    return _KEYS[m[0]] if m else None


def parse(lines):
    """OCR lines -> {"names": [(name, box)], "count": (have, most) or None, "head": box of "Medallions (n/m)",
    "room": the room an Uromoti's adds (its tooltip) or None}."""
    out = {"names": [], "count": None, "head": None, "room": None}
    for text, box in lines or []:
        t = " ".join(str(text).split())
        m = _COUNT.search(t)
        if m and "MEDALLIONS" in letters(t) and len(letters(t)) <= 12:
            have, most = int(m.group(1)), int(m.group(2))
            if 0 <= have <= most <= 6:
                out["count"], out["head"] = (have, most), box
            continue
        n = name_of(t)
        if n:
            out["names"].append((n, box))
            continue
        r = _ROOM.search(t)
        if r:
            out["room"] = room_family(r.group(1))
    return out


def room_family(text):
    from . import vaallens_plan as VP
    what = VP.card(text)
    if what and what[0] == "room":
        return what[1]
    low = " ".join(str(text).lower().split())
    for fam in VP.ROOMS:
        if fam.lower() in low:
            return fam
    return None


def base(name):
    """ "Uromoti's Medallion: Corruption Chamber" -> ("Uromoti's Medallion", "Corruption Chamber")."""
    n, _, room = str(name or "").partition(": ")
    return n, (room or None)


def worth(name, room=None, crystals_most=None, slots_most=None):
    """-> (0-10, why). Capacity ones are 0 once full; Uromoti's follows its room."""
    name, r = base(name)
    room = room or r
    short, _what, w = MEDALLIONS[name]
    if name == "Xopec's Medallion" and crystals_most is not None and crystals_most >= 60:
        return 0, "crystals already at 60"
    if name == "Azcapa's Medallion" and slots_most is not None and slots_most >= 6:
        return 0, "already 6 slots"
    if name == "Uromoti's Medallion" and room:
        if room in HIGH_ROOMS:
            return 8, f"adds {room} (pays at tier 3)"
        return 5, f"adds {room}"
    return w, short.lower()


def advice(new, hand, have, most, room=None, crystals_most=None):
    """A medallion seen on the ground -> (verdict, line) or None.
    verdict: "take" (room for it, or better than your weakest), "skip" (weaker than all you hold), "learn" (full, and
    not every slot is known yet). hand: names (None = not learned) of the slots you hold."""
    w, why = worth(new, room, crystals_most, most)
    if w == 0:
        return "skip", f"{new}: {why}."
    if have is None or most is None:
        return None
    if have < most:
        return "take", f"{new}: {why}. {most - have} slot{'s' if most - have != 1 else ''} free."
    known = [h for h in (hand or [])[:have] if h]
    if len(known) < have:
        if known and w <= min(worth(h, None, crystals_most, most)[0] for h in known) and w <= 1:
            return "skip", f"{new}: {why}. Weaker than what you hold."
        return "learn", f"{new}: {why}. Medallions full: press V and hover each so Vaal Lens knows them."
    worst = min(known, key=lambda h: worth(h, None, crystals_most, most)[0])
    ww, wwhy = worth(worst, None, crystals_most, most)
    if w > ww:
        return "take", f"{new}: {why}. Use or destroy {worst} ({wwhy}) to make room."
    return "skip", f"{new}: {why}. Weaker than all you hold."


# ---------------------------------------------------------------- the panel (V): where the slots are
# measured on a 2560x1440 game: the "Medallions (6/6)" title's right end, then 2 columns x 3 rows of 120x125 slots
HEAD_TO_SLOT = (-232, 38)        # the first slot's top-left from the title's (right, middle)
SLOT = (120, 125)
STEP = (144, 144)
ICON = (32, 22, 88, 82)          # the picture inside the slot's gold diamond (frame and pedestal left out)


def slots(head_screen, scale, n=6):
    """The title's box on screen (l, t, r, b) and the game's scale (height / 1440) -> n slot boxes on screen."""
    r, mid = head_screen[2], (head_screen[1] + head_screen[3]) / 2
    x0, y0 = r + HEAD_TO_SLOT[0] * scale, mid + HEAD_TO_SLOT[1] * scale
    out = []
    for k in range(n):
        c, row = k % 2, k // 2
        x, y = x0 + c * STEP[0] * scale, y0 + row * STEP[1] * scale
        out.append((int(x), int(y), int(x + SLOT[0] * scale), int(y + SLOT[1] * scale)))
    return out


def icon_box(slot):
    l, t, r, b = slot
    sx, sy = (r - l) / SLOT[0], (b - t) / SLOT[1]
    return int(l + ICON[0] * sx), int(t + ICON[1] * sy), int(l + ICON[2] * sx), int(t + ICON[3] * sy)


def feat(img):
    """A slot's icon (PIL) -> a unit vector: a 20x20 z-scored gray picture plus a coarse color share."""
    from PIL import Image
    a = np.asarray(img.convert("RGB").resize((20, 20), Image.BILINEAR)).astype(np.float32)
    g = a.mean(axis=2)
    gx, gy = np.abs(np.diff(g, axis=1))[:-1, :], np.abs(np.diff(g, axis=0))[:, :-1]
    g = np.concatenate([g.ravel(), (gx + gy).ravel()])
    g = (g - g.mean()) / (g.std() + 1e-6)
    tot = a.sum(axis=2) + 1e-6
    col = np.array([(a[..., 0] / tot).mean(), (a[..., 1] / tot).mean(), (a[..., 2] / tot).mean()]) * 40
    v = np.concatenate([g, col])
    return v / (np.linalg.norm(v) + 1e-9)


SEEDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "medallion_icons.json")
MATCH = 0.93


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return {k: [np.array(v, dtype=np.float32) for v in vs] for k, vs in json.load(f).items()
                    if base(k)[0] in MEDALLIONS}
    except (OSError, ValueError):
        return {}


def known_icons(user_path=None):
    out = _load(SEEDS)
    for k, vs in (_load(user_path) if user_path else {}).items():
        out.setdefault(k, []).extend(vs)
    return out


def learn(user_path, name, vec, keep=4):
    """A hovered slot's icon -> kept for that name (the newest few). An Uromoti's is kept with its room."""
    if base(name)[0] not in MEDALLIONS:
        return
    try:
        with open(user_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    vs = data.get(name) or []
    vs = (vs + [[round(float(x), 4) for x in vec]])[-keep:]
    data[name] = vs
    os.makedirs(os.path.dirname(user_path) or ".", exist_ok=True)
    with open(user_path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def identify(vec, icons):
    """-> the name whose icon matches best (MATCH or closer), or None."""
    best, who = MATCH, None
    for name, vs in icons.items():
        for v in vs:
            s = float(np.dot(vec, v))
            if s > best:
                best, who = s, name
    return who
