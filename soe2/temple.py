"""2.132.1 Temple Helper (feedback: "show how many crystals I am currently at when running maps"; "temple helper will
flash a red text card too when crystals are full"): your Energised Beacons - the Vaal Beacon's tooltip says
"Energised Beacons: 55/60" when you hover one in a map. The helper reads that line (Windows' text reader, a part of the
screen round the mouse, in maps only) and keeps the number; the bar shows it, and when it's full an alert card says so.

Nothing else on screen is kept - only the two numbers. ToS: it only looks at the screen and shows something."""
import re
import time

from .config import SETTINGS, load_json, save_json

STATE_FILE = "temple.json"
DEFAULTS = {"on": False}
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


def full(st):
    return bool(st) and st["have"] >= st["most"]


def bar_text(st):
    """"◆ Crystals 55/60" - or "◆ Crystals ?" before the first read."""
    if not st:
        return "◆ Crystals ?"
    return f"◆ Crystals {st['have']}/{st['most']}" + (" FULL" if full(st) else "")
