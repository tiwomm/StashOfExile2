"""2.102.0 Stash scan (beta) - count currency by looking at the open stash tab, instead of Ctrl+C on every stack.

Wealth › Scan stash (beta) opens a small card over the game: "Open your Currency tab" - [Start reading]. The app
takes one picture of the game, finds the stash panel, checks it's that tab, then reads each fixed slot: empty or
not, and the stack number in its top-left corner. You check the numbers before they're saved (Wealth › Counted by
hand), tab by tab.
  * Only looks: no keys, no clicks, nothing sent to the game (like the Expedition and Ritual watchers).
  * The picture stays in memory for the read and is dropped. Nothing is saved, logged or sent - counts stay on this PC
    like every Wealth number.
  * Layouts: stashlayouts.py (Currency, Abyss, Delirium, Breach › Catalysts, Expedition, Ritual, Essence, Fragments › Fragments). Wildcard slots, shards and the
    crafting hole are skipped.
How it reads:
  1. The panel: the slot frames of each known tab, drawn as boxes, are matched against the picture's edges (left 60%
     of the game, at ~720 px high so every size costs the same). The best tab + spot + size wins.
  2. A slot is filled when its dark-blue backing shows (an empty slot is gray with a faint ghost icon).
  3. The number: digit shapes (GLYPHS, white with a black outline, taken from 1440p shots) are matched along the
     slot's top edge; the longest run of well-matched digits side by side, on one baseline, is the stack size.
Needs OpenCV + numpy (the app ships both for the Expedition watcher)."""
import base64

from .stashlayouts import ORDER, PANEL, TABS

WORK_H = 720            # match the panel at this height (any game size costs the same)
SIZES = (0.94, 0.97, 1.0, 1.03, 1.06)      # UI scale wiggle around game height / 1440
FOUND_SCORE = 0.12      # a panel's edge match: real tabs ~0.2-0.28; no stash open ~0.0-0.08
OTHER_TAB_BY = 0.01     # another tab must beat the one you were asked to open by this much to say "that's X"
DIGIT_CUT, DIGIT_BASE = 0.45, 0.60      # a digit's match must reach CUT; each one adds (score - BASE) to a run
SURE = 0.2              # 2.114.2: a slot with no backing showing counts only with a number this clear (a digit 0.8+)
TIE = 0.0               # 2.114.2: a longer run this close to the best wins (a faint second digit)
FILLED_SHARE = 0.06     # share of a slot's inside that is the dark-blue backing -> it holds something

# Digit shapes at 1440p: (width, height, bytes) - a "white minus outline" map, 0..255 = -1..1. Made from the stack
# numbers of the four reference tabs (tools/stash_glyphs.py); no picture of a stash ships with the app.
GLYPHS = {
    "0": (13, 19, ("GyAgIBoWDAsLCxYPCTY7JiEgHBMNEBkpHyAsMioWAAAAAAAXOi4oJTUFAP//////AAxSMCoQAP////////8AJF8gAP//lQAA"
               "AP///wBcAL///wA7TQDm//8ALwD//5UASlAxAP//vwAA//8AQUE+TwD///8AAP//ADpARkoA////AAD//4AAQlNdAP///wAA"
               "///mAFpWUwD//5UAAP///wBOXz8A//8AXwC///+AAFMA5v//AJFBAP///wAAlf//ADVsciEA////////ACx2d1ZUNACAv78A"
               "AEF3bntWZ21aAAAAXYBpdn1rWWNoZ4R8clNucHWIhg==")),
    "1": (7, 19, ("AAAAAAAAAAAAAAABBQUAAAEZISEDABkhx///AAC///f//wADp96n//8AAwAAAP//AAUFBwD//wAJBwcA//8ADQoKAP//ABAN"
               "DQD//wASDQsA//8AFA8eAP//ABAYLAD//wAGHCgA//8QCyItAN7ebxcgMw0MDQ4VHDY6S0BREyc8QktWTg==")),
    "2": (10, 19, ("AAYGBgEAAAABCwAGBgYBAAABCwsACxYWFhYWBgsDAIv//fn//xYBBAD//9Kv6f//FAwA6ekAAAD//+gAAAAACRsA///2AA4Q"
               "ERocC///iAINDBciAIv/+QAiDRQfGA3//68AMxYeFgCe/+kALjMXGggW/+kAHjIrEQoW/+kADDwvLQ0W//8WFhYWFhsA////"
               "//////8AAOnp6enp6enpAAcLCwkKDRANCx4xSkhHRUU+S1JVPjxCSzpGSlBaZw==")),
    "3": (10, 19, ("AAABBQYFCQUTEwMFBQcHCwkIERMEBgkJCQkJDhMcBZn//v3//wkRHoD//924+v//ABd79vYAAHv//wAlAAAAEwAJ//8AJg8S"
               "Ew8J///2AC0LFgoI////BQAhEBUS3fb//4QFIRgbGAUC9v//hAAaIywwHAD///8AEicpLCwA////AB4zMjQnBf//+gAfOScs"
               "AIT//3sFJR0HCQn///YDQQYJwv//9vYFKGeQ9vb29gUIJ2NjCQkJCQkrR1BeWg==")),
    "4": (12, 19, ("CgsKCgIAAAAAAAAACgsLCgIAAAAAAAUKCgsRCgUAFBQPCx8WChQaCgoU//+/ACANDBQUDgr///+/ACcnGhQbAIn///+/ADwt"
               "HRooEv/r//+/AFIOECQA5/8A//+/AEkfExkU/+sA//+/AFMqEAD//wAA//+/AExBCxT/6wAA//+/AFNAAP//FBQU///EFBQ1"
               "C/////////////cAievr6+vr///664kKCAoKFAoA//+/AApONUI1T14A//+/AG1JKShJVGYA//+/AFAzLTVRWmwA6+uxAFlG"
               "OU9lgGQcAAAAMlxE")),
    "5": (10, 19, ("DhERCg8MEAsGCAgIDQ0RCAsUHRkGESIiIiIiIiIRAIj////////dEAC//93d3d3dBxoAyP8ADwkLCCBBAP//AC0nJEhISwD/"
               "/yIiIh8rVVMR3d3x///pIilcLhERgd3///8RQDNIOREH3f//kAAgQEA8LQD///8AFEc+Uj8A////ACE9Vl0aGf//3QwvTkxH"
               "AMj//wBJOjgUIiL//90GUScio///7t0DNWIc3d3d3W4IO2x5IQADAwEIQWByaw==")),
    "6": (12, 19, ("AAABAwAAAAAAAAAAGCMbBwD/////vwANJhkHAP///////+YAHRMA////AAAAAOYAGQD///8AHD4qIgAkEgD//5UAJiozLkA9"
               "AYD//wAAAAAAACA/AL//////////5gA6AP///+YAAP///5UAAP///wAQBQD///8AAP///wAhOgD///8AAP///wAmRgC///8A"
               "AID//wAjOQD///8AEgD///8AAAD//4AAMADm//+VAJX//wBZTCEA////////ADOGSyooAAC/vwAASGN4MzpZTxsAABdeTEhm"
               "Uz5SPT1FOSk2OD+F")),
    "7": (11, 19, ("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAL///////////wAAAP//////////AAAAAIC/v7///4AAAAAAAAAA"
               "AP//AA8AAAcKCgD//5UAHQcMFBQGAP//ACInChAUCgDm//8AMDEPGRIiAP//ACY7MB0PFgCA//8ALyoiERUxAP//ABAnNjEJ"
               "JRoA//8ALTpVUAooAP//lQBMZndRChAA//8ARmpeSEQbAP///wBWTEVBUSQA//8AJ087NVNRPQ4AAB9LNzc6RU4=")),
    "8": (12, 19, ("AAAAAAAAAAAACw4XAAAAgP////8AAg4QDgDm////////AAIYGAD//wAAAP///wAOAJX//wAcAL///wAjCID//78AAOb/gAAo"
               "DgD////mAP//ACYOHhAA/////+YAJi4qJB8AgP////8AAD8cHACV////////gAAvAQD//wAAv////wAxAP//lQA0AL///5UA"
               "AP//AAA+IAD//78AAP//5gAxCQD//wA8AID//4AAAP///wBMDgDm////////ADFMOTUAAL+/lQAANkw8NUE2IwAAADdocWpB"
               "OD8xMElMQjtTb01T")),
    "9": (12, 19, ("AAAAAAAAABQQHUU6AAAAAAAAECYmQVg3AAAAAAAAAAAAMFtQAAAAgP////+VADRdAQCV//+/////lQBQEAD//wAAAP///wA+"
               "AP///wAzAID//4AAAP///wBJPgD//+YAAP///wA0MwD///8AAP///wAfJwD///8AAL///5UAAAD///8AGgD///////////8A"
               "NBAAlf//lQD//78AMEAyAAAAAID//wA+OzYpUFs6AP///wAwAIAAAAAAlf//gAA3AP///7//////ADA9IQD//////5UALT5I"
               "MCQAAAAAAAA/Sj05")),
    # 2.114.2: stacks over 9,999 show as "12.2K" (the user's Expedition tab: 12,239 Verisium)
    "K": (13, 19, "AP///wAcSAD///8AAAD///8AAACA//8AAAAA////AAAA//8AAAAAAP///wAA//8AAAAAAAD///8A//8AAAAAAAAA//////8AABcAAAAAAP//////gAAXgCAAAAD///////8AAByAAAAA////gP///wATV4ANAP///wDm///mAFVbgAD///8AAP///4AAUQQA////AAAA////AAAvAP///wAAAL////8AAAD///8AAAAA/////wYAAAAAAAAAAAAAAAAAAAAAAAAAACJmNS8iSAAAAAAAAAaAdwBPgIAAAAAAAAAiU2qAZCpkAAAACABMYmaAgCQAAA=="),
    ".": (5, 19, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASAAAAAL44AABWkgAARhJCAM4CAgIDIgHWAgCQAAABCAP//vwAA////AAAAvwAAgFMAgICAgICAgKqAgICAioCAgIA="),
}
_G = {}


def available():
    """'' when the scan can run here, else why not."""
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
    except Exception:
        return "needs OpenCV (pip install opencv-python numpy)"
    return ""


def _np():
    import cv2
    import numpy as np
    return cv2, np


def _glyphs():
    if not _G:
        cv2, np = _np()
        for d, (w, h, b) in GLYPHS.items():
            a = np.frombuffer(base64.b64decode(b), np.uint8).reshape(h, w).astype(np.float32)
            _G[d] = a / 127.5 - 1.0
    return _G


def feature(bgr):
    """White strokes -> +1, the dark outline -> -1, everything else ~0 (so a bright icon behind barely matters)."""
    cv2, np = _np()
    f = bgr.astype(np.float32)
    lo, hi = f.min(axis=2), f.max(axis=2)
    white = np.clip((lo - 150) / 60, 0, 1) * np.clip(1 - (hi - lo - 30) / 40, 0, 1)   # 2.114.2: neutral white only -
    return white - np.clip((110 - hi) / 60, 0, 1)            # an essence's pink / red glow behind the number isn't ink


def _outline(tab, k, w):
    """The tab's slot boxes drawn as thin outlines, at size k (game h / 1440) times work scale w."""
    cv2, np = _np()
    n = max(8, round(PANEL * k * w))
    t = np.zeros((n, n), np.float32)
    for _name, (x, y, sw, sh) in TABS[tab]["slots"]:
        cv2.rectangle(t, (round(x * k * w), round(y * k * w)), (round((x + sw) * k * w), round((y + sh) * k * w)),
                      1.0, 1)
    return t


def _edges(bgr, w):
    cv2, np = _np()
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if w != 1.0:
        g = cv2.resize(g, None, fx=w, fy=w, interpolation=cv2.INTER_AREA)
    e = cv2.Canny(g, 40, 120).astype(np.float32) / 255.0
    return cv2.dilate(e, np.ones((2, 2), np.uint8))


def locate(bgr, game_h, tabs=None):
    """The stash panel in a game picture -> {"tab", "score", "scores": {tab: best}, "k", "x", "y"} or None.
    2.114.2: a tab's edge match is weighed by how many of its slots hold something at that spot - the Essence tab's
    dense grid of 82 slots matched every panel's edges a little, so the edges alone took Expedition for Essence.
    "score" stays the plain edge match (is a stash there at all); "scores" are the weighed ones (which tab)."""
    cv2, np = _np()
    w = WORK_H / float(game_h)
    left = bgr[:, :max(1, int(bgr.shape[1] * 0.6))]
    e = _edges(left, w)
    k0 = game_h / 1440.0
    per = {}
    for tab in (tabs or ORDER):
        for f in SIZES:
            k = k0 * f
            t = _outline(tab, k, w)
            if t.shape[0] >= e.shape[0] or t.shape[1] >= e.shape[1]:
                continue
            m = cv2.matchTemplate(e, t, cv2.TM_CCORR_NORMED)
            _mn, v, _l, loc = cv2.minMaxLoc(m)
            v = float(v)
            if tab not in per or v > per[tab]["score"]:
                per[tab] = {"tab": tab, "score": v, "k": k, "x": round(loc[0] / w), "y": round(loc[1] / w)}
    if not per:
        return None
    scores = {}
    for tab, p in per.items():
        slots = TABS[tab]["slots"]
        n = sum(1 for _n, (x, y, sw, sh) in slots
                if filled(bgr, (p["x"] + round(x * p["k"]), p["y"] + round(y * p["k"]), round(sw * p["k"]),
                                round(sh * p["k"]))))
        scores[tab] = p["score"] * (0.5 + 0.5 * n / max(1, len(slots)))
    best = dict(per[max(scores, key=scores.get)])
    best["scores"] = scores
    best["weighed"] = scores[best["tab"]]
    return best


def filled(bgr, rect):
    """Does this slot hold something? (its dark-blue backing shows)"""
    cv2, np = _np()
    x, y, w, h = rect
    p = max(2, w // 10)
    sub = bgr[y + p:y + h - p, x + p:x + w - p].astype(np.int16)
    if sub.size == 0:
        return False
    b, g, r = sub[..., 0], sub[..., 1], sub[..., 2]
    navy = (b > r + 12) & (b > g + 8) & (b < 140) & (r < 70)
    return float(navy.mean()) >= FILLED_SHARE


def read_number(bgr, rect, k, sure=0.0):
    """The stack number in a slot's top-left corner -> int or None. sure: the run must score at least this (2.114.2:
    for a slot whose backing doesn't show)."""
    cv2, np = _np()
    x, y, w, _h = rect
    pad = max(2, round(4 * k))
    x0, y0 = max(0, x - pad), max(0, y - pad)
    band = feature(bgr[y0:y + round(26 * k), x0:x + round(64 * k)])
    cands = []
    for d, g in _glyphs().items():
        gw, gh = max(3, round(g.shape[1] * k)), max(5, round(g.shape[0] * k))
        if gh > band.shape[0] or gw > band.shape[1]:
            return None
        t = cv2.resize(g, (gw, gh), interpolation=cv2.INTER_AREA)
        m = cv2.matchTemplate(band, t, cv2.TM_CCOEFF_NORMED)
        col, ys = m.max(axis=0), m.argmax(axis=0)
        for i in range(len(col)):
            if col[i] >= DIGIT_CUT and col[i] == col[max(0, i - 2):i + 3].max():
                cands.append((i, d, float(col[i]), gw, int(ys[i]) + gh))
    cands.sort()
    first = round(14 * k) + (x - x0)
    run = {}
    for i, (cx, d, s, gw, base) in enumerate(cands):
        here = (s - DIGIT_BASE, d) if cx <= first and _could_be(d) else None
        for j in range(i):
            px, _pd, _ps, pw, pb = cands[j]
            near = pw - round(4 * k) <= cx - px <= pw + round(2 * k)
            if j in run and near and abs(pb - base) <= max(1, round(1.5 * k)) and _could_be(run[j][1] + d):
                v = run[j][0] + s - DIGIT_BASE
                if here is None or v > here[0]:
                    here = (v, run[j][1] + d)
        if here:
            run[i] = here
    return _value(best_valid(run, sure))


def _could_be(txt):
    """2.114.2: can a stack size start like this? (digits, or "12.2K" on its way) - so a stray "." or "K" match
    never takes a run over."""
    import re
    return bool(re.fullmatch(r"\d+|\d{1,3}(\.\d?)?K?|\d{1,3}\.", txt))


def best_valid(run, sure=0.0):
    """The best-scoring run that reads as a stack size: digits, or (2.114.2) "12.2K" - a "." only before a K."""
    best = (sure, "")
    for v, txt in run.values():
        longer = len(txt) > len(best[1]) and v >= best[0] - TIE        # (about a tie: the longer one - "11"
        if (v > best[0] or longer) and _value(txt) is not None:            # whose second 1 scores just under par)
            best = (v, txt)
    return best[1]


def _value(txt):
    """'4685' -> 4685, '12.2K' -> 12200 (the game rounds stacks over 9,999), else None."""
    import re
    if not txt:
        return None
    if re.fullmatch(r"\d+", txt):
        return int(txt)
    m = re.fullmatch(r"(\d{1,3})(?:\.(\d))?K", txt)
    if m:
        return int(m.group(1)) * 1000 + int(m.group(2) or 0) * 100
    return None


def read_tab(bgr, game_h, want):
    """Read one tab you were asked to open. -> {"ok", "tab", "seen" (tab it looks like), "items": [(name, qty)],
    "unread": [names: filled but the number couldn't be read], "why"}"""
    spot = locate(bgr, game_h)
    if not spot or spot["score"] < FOUND_SCORE:
        return {"ok": False, "tab": want, "seen": None, "items": [], "unread": [],
                "why": "Couldn't find the stash. Open it in game, on this tab, and try again."}
    mine = spot["scores"].get(want, 0.0)
    if spot["tab"] != want and spot["weighed"] - mine > OTHER_TAB_BY:
        return {"ok": False, "tab": want, "seen": spot["tab"], "items": [], "unread": [],
                "why": f"That looks like the {TABS[spot['tab']]['label']} tab. Open the {TABS[want]['label']} tab."}
    if spot["tab"] != want:                       # close call: redo the spot for the tab you named
        spot = locate(bgr, game_h, tabs=(want,))
    k, ox, oy = spot["k"], spot["x"], spot["y"]
    items, unread, icons, pics = [], [], {}, {}
    for name, (x, y, w, h) in TABS[want]["slots"]:
        r = (ox + round(x * k), oy + round(y * k), round(w * k), round(h * k))
        if filled(bgr, r) and w == h:              # 2.129.0: an item's look, for Favours prices (one-cell slots)
            pics[name] = bgr[r[1]:r[1] + r[3], r[0]:r[0] + r[2]].copy()
        if not filled(bgr, r):
            n = read_number(bgr, r, k, sure=SURE)    # 2.114.2: an item that covers its whole slot (a Weathered
            if n:                                    # Crisis Fragment) hides the backing - a clear number still counts
                items.append((name, n))
            continue
        n = read_number(bgr, r, k)
        if n:
            items.append((name, n))
        else:
            unread.append(name)
        icons[name] = _icon(bgr, r)
    # 2.114.3 (feedback: "it didn't count the divs in the wildcard slot, the 1193"): a wildcard slot holds anything -
    # what it holds is told by its picture, matched with the tab's own fixed slots in the same shot (Divine Orb's
    # overflow looks just like the Divine Orb slot); the rest are kept for the end of the scan (match_wild: every
    # tab read). The pictures stay in memory only.
    wild = []
    for x, y, w, h in TABS[want].get("wild") or ():
        r = (ox + round(x * k), oy + round(y * k), round(w * k), round(h * k))
        if not filled(bgr, r):
            continue
        n = read_number(bgr, r, k)
        ic = _icon(bgr, r)
        name, _sc = _same_item(ic, icons)
        if n and name is not None:
            items.append((name, n))
        else:
            wild.append((n, ic))
    return {"ok": True, "tab": want, "seen": want, "items": items, "unread": unread, "why": "",
            "icons": icons, "wild": wild, "pics": pics}


def match_wild(wild, icons, keep=False):
    """Wildcard slots their own tab didn't match -> ([(name, count)], how many still unknown - or with keep, the
    unknown [(count, picture)] themselves, to be named), matched with every tab read in the scan."""
    got, unknown = [], []
    for n, ic in wild:
        name, _sc = _same_item(ic, icons)
        if n and name is not None:
            got.append((name, n))
        else:
            unknown.append((n, ic))
    return got, (unknown if keep else len(unknown))


ICONS_FILE = "stash_icons.json"     # 2.114.3: pictures of items you named in a wildcard slot (40 x 26, on this PC)


def learned_icons():
    """{name: picture} you've named before (Sacred Bloom ...) - an item's look, nothing about your stash."""
    cv2, np = _np()
    from .config import load_json
    out = {}
    for name, b in (load_json(ICONS_FILE, {}) or {}).items():
        try:
            out[name] = np.frombuffer(base64.b64decode(b), np.uint8).reshape(26, 40, 3).astype(np.float32)
        except Exception:
            continue
    return out


def learn_icon(name, icon):
    """Remember what this item looks like (the wildcard you just named)."""
    if icon is None or not name:
        return
    cv2, np = _np()
    from .config import load_json, save_json
    d = load_json(ICONS_FILE, {}) or {}
    d[name] = base64.b64encode(np.clip(icon, 0, 255).astype(np.uint8).tobytes()).decode()
    save_json(ICONS_FILE, d)


WILD_MATCH = 0.75       # 2.114.3: a wildcard's picture must look this much like a fixed slot's (and clearly most)


def _icon(bgr, rect):
    """A slot's picture without its number (the top third) - small, in color, for matching."""
    cv2, np = _np()
    x, y, w, h = rect
    sub = bgr[y + h // 3:y + h - max(2, h // 12), x + max(2, w // 12):x + w - max(2, w // 12)]
    if sub.size == 0:
        return None
    return cv2.resize(sub, (40, 26), interpolation=cv2.INTER_AREA).astype(np.float32)


def _same_item(icon, icons):
    """-> (the fixed slot's name it looks like, score) or (None, score). The other slot's middle is slid a few pixels
    over this one's picture (slots never line up to the pixel)."""
    cv2, np = _np()
    if icon is None:
        return None, 0.0
    scores = []
    for name, ic in icons.items():
        if ic is None:
            continue
        v = float(cv2.matchTemplate(icon, ic[3:-3, 4:-4], cv2.TM_CCOEFF_NORMED).max())
        scores.append((v, name))
    if not scores:
        return None, 0.0
    scores.sort(reverse=True)
    best = scores[0]
    lead = best[0] - (scores[1][0] if len(scores) > 1 else 0.0)
    return (best[1], best[0]) if best[0] >= WILD_MATCH and lead >= 0.05 else (None, best[0])


def grab_bgr(rect):
    """(l, t, r, b) of the game -> a BGR picture (numpy), kept in memory only."""
    cv2, np = _np()
    from .screengrab import screen
    l_, t, r, b = rect
    with screen() as sct:                         # mss; Wayland: grim (2.103.0 linux branch)
        shot = sct.grab({"left": int(l_), "top": int(t), "width": int(r - l_), "height": int(b - t)})
        a = np.asarray(shot)                       # BGRA
    return np.ascontiguousarray(a[..., :3])


def scan(rect, want):
    """Take one picture of the game and read the tab `want`."""
    bgr = grab_bgr(rect)
    try:
        return read_tab(bgr, rect[3] - rect[1], want)
    finally:
        del bgr
