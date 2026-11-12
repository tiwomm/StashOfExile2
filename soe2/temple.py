"""2.132.1 Temple Helper (feedback: "show how many crystals I am currently at when running maps"; "temple helper will
flash a red text card too when crystals are full"): your Energised Beacons - the Vaal Beacon's tooltip says
"Energised Beacons: 55/60" when you hover one in a map. The helper reads that line (Windows' text reader, a part of the
screen round the mouse, in maps only) and keeps the number; the bar shows it, and when it's full an alert card says so.

Nothing else on screen is kept - only the two numbers. ToS: it only looks at the screen and shows something."""
import re
import time

from .config import SETTINGS, load_json, save_json

STATE_FILE = "temple.json"
DEFAULTS = {"on": False, "notepad": True, "notes": "", "pad_x": None, "pad_y": None}
TEMPLE_AREAS = ("IncursionTemple",)   # 2.136.0: Atziri's Temple, as Client.txt names the area
LINE = re.compile(r"energi[sz]ed\s+beacons?\s*[:;.]?\s*(\d{1,3})\s*[/|l1]\s*(\d{2,3})", re.I)
AROUND = (0.25, 0.38, 0.06)        # the part looked at: half its width, up and down from the mouse (parts of the game)


def cfg():
    c = SETTINGS.setdefault("temple", {})
    for k, v in DEFAULTS.items():
        c.setdefault(k, v)
    return c


def parse(lines):
    """OCR lines -> (have, most) from "Energised Beacons: 55/60", or None. A misread "/" (l, 1, |) is allowed; the
    numbers must make sense (most 10-200, have <= most)."""
    for text, _box in lines or []:
        m = LINE.search(" ".join(str(text).split()))
        if not m:
            continue
        have, most = int(m.group(1)), int(m.group(2))
        if 10 <= most <= 200 and 0 <= have <= most:
            return have, most
    return None


def region(pointer, game):
    """The mouse (x, y) and the game (x, y, w, h) -> (left, top, right, bottom) round the mouse, inside the game."""
    gx, gy, gw, gh = game
    px, py = pointer
    hw = int(AROUND[0] * gw)
    left, right = max(gx, px - hw), min(gx + gw, px + hw)
    top, bottom = max(gy, py - int(AROUND[1] * gh)), min(gy + gh, py + int(AROUND[2] * gh))
    return left, top, right, bottom


def state():
    d = load_json(STATE_FILE, {}) or {}
    try:
        return {"have": int(d["have"]), "most": int(d["most"]), "t": float(d.get("t", 0))}
    except (KeyError, TypeError, ValueError):
        return None


def state_set(have, most, t=None):
    d = {"have": int(have), "most": int(most), "t": t if t is not None else time.time()}
    save_json(STATE_FILE, d)
    return d


# 2.132.4 (feedback: "Temple helper says Crystals ? without even having temple in the map ... the red/gold triangle map
# content icon"): the Temple icon under Map Content (templates/temple_content.png, from a 1440p game) says the map has
# a Temple; the crystals show only then. Measured: 0.999+ with it there, 0.72 at most without (every saved shot).
CONTENT_AREA = (0.64, 0.14, 1.0, 0.49)      # where Map Content's icons are (as the Ritual watcher's)
CONTENT_MIN = 0.85
BASE_H = 1440
_TPL = []


def content_box(game):
    gx, gy, gw, gh = game
    a = CONTENT_AREA
    return gx + int(gw * a[0]), gy + int(gh * a[1]), gx + int(gw * a[2]), gy + int(gh * a[3])


def content_has(img, game_h):
    """A picture of Map Content's area (PIL) and the game's height -> True if the Temple icon is there."""
    import cv2
    import numpy as np
    if not _TPL:
        import sys
        from pathlib import Path
        base = getattr(sys, "_MEIPASS", None)
        d = Path(base) / "soe2" / "templates" if base else Path(__file__).resolve().parent / "templates"
        _TPL.append(cv2.imread(str(d / "temple_content.png"), cv2.IMREAD_GRAYSCALE))
    tpl = _TPL[0]
    if tpl is None or img is None:
        return False
    g = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    s = game_h / BASE_H
    t = cv2.resize(tpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if abs(s - 1) > 0.01 else tpl
    if g.shape[0] < t.shape[0] or g.shape[1] < t.shape[1]:
        return False
    return float(cv2.minMaxLoc(cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED))[1]) >= CONTENT_MIN


RUN = 6                 # 2.135.0: crystals one temple run uses (the console takes 6, you get 6 room cards)


def runs(st):
    return (st["have"] // RUN) if st else 0


def full(st):
    return bool(st) and st["have"] >= st["most"]


def bar_text(st):
    """Its part of the Helpers line (2.132.6: no ◆): "Crystals 55/60 (9 runs)" (2.135.0: how many runs that is - 6
    crystals each), or "Crystals ?" before the first read."""
    if not st:
        return "Crystals ?"
    n = runs(st)
    return f"Crystals {st['have']}/{st['most']} ({n} run{'' if n == 1 else 's'})"
