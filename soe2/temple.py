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
# 2.136.0: Atziri's Temple, as Client.txt names the area. 2.137.0 (feedback: "should open in Vaal Ruins as well as
# inside Atziri's Temple"): the endgame Vaal Ruins (IncursionHubEndgame, not the campaign's IncursionHub) and Atziri's
# own area too.
TEMPLE_AREAS = ("IncursionHubEndgame", "IncursionTemple", "IncursionTemplePresent")
RUN_AREA = "IncursionTemple"            # entering it = a temple run started, so its crystals are spent
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


# 2.136.1 (feedback: "when I'm in the Vaal ruins, it should be able to see through the overlay (the same way ritual
# does) and read the crystal count at the bottom of the screen"): the Temple Console prints "18/60" under its Run
# Temple button. Read there (parts of the game; measured on 1080p and 1440p shots) while you're in a temple area.
CONSOLE_BOX = (0.465, 0.942, 0.555, 0.978)
CONSOLE_LINE = re.compile(r"(?<!\d)(\d{1,3})\s*[/|l]\s*(\d{2,3})(?!\d)")
CONSOLE_EVERY = 2000                    # ms between looks


def console_box(game):
    gx, gy, gw, gh = game
    a = CONSOLE_BOX
    return gx + int(gw * a[0]), gy + int(gh * a[1]), gx + int(gw * a[2]), gy + int(gh * a[3])


def parse_console(lines, most=None):
    """OCR lines of the console's count -> (have, most) from "18/60", or None. The most must make sense (10-200,
    and the same as the last read when there is one) and have <= most."""
    for text, _box in lines or []:
        m = CONSOLE_LINE.search(" ".join(str(text).split()).replace(" / ", "/"))
        if not m:
            continue
        have, top = int(m.group(1)), int(m.group(2))
        if 10 <= top <= 200 and 0 <= have <= top and (most is None or top == most):
            return have, top
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
        return {"have": int(d["have"]), "most": int(d["most"]), "t": float(d.get("t", 0)), "old": bool(d.get("old"))}
    except (KeyError, TypeError, ValueError):
        return None


def state_set(have, most, t=None):
    d = {"have": int(have), "most": int(most), "t": t if t is not None else time.time(), "old": False}
    save_json(STATE_FILE, d)
    return d


def mark_old():
    """2.137.0 (feedback: "I have 54/60 it says 58/60"): a temple run spends crystals, and the number is only read
    from a Vaal Beacon. So once a run starts the kept number is marked as from before it, until the next read."""
    st = state()
    if st and not st["old"]:
        d = dict(st, old=True)
        save_json(STATE_FILE, d)
        return d
    return st


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
    if st.get("old"):
        return f"Crystals {st['have']}/{st['most']}? (before your last run)"
    n = runs(st)
    return f"Crystals {st['have']}/{st['most']} ({n} run{'' if n == 1 else 's'})"
