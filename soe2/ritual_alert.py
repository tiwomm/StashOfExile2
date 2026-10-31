"""Ritual watcher (2.14.0): reads the game's Ritual counter ("0/3", "2/4" ...) from your screen.

Path of Exile 2 doesn't write Ritual progress to Client.txt, so - like the Delirium alert - this looks at a small part
of the screen: the Ritual icon (horned skull in a red ring) at the bottom, right of centre, with the counter in a black
box next to it. Only that corner is captured, twice a second; nothing is sent to the game.

It runs as its own helper process (StashOfExile2.exe --ritual <data folder>, see utilities.RITUAL), so screen capture
never slows the app, and talks to the app over its stdin / stdout:
    app -> helper: quit, capture
    helper -> app: "state watching" / "state nogame" / "state error", "count 2/3", "count none", "captured <path>",
                   or a message line.
How the counter is read: find the icon by template matching (soe2/templates/ritual_icon.png, scaled to the game's
height), take the black box right of it, keep the bright text pixels and cut them into glyphs at the empty columns;
the middle one is "/", and each digit (0 - 4) is recognised from its shape (holes, width, which edges are filled).
A reading counts only when it's seen twice in a row and makes sense (total 3 or 4, done <= total)."""
import os
import sys
import threading
import time
from pathlib import Path

BASE_H = 1440                    # the templates and offsets are measured on a 2560x1440 game
# where to look for the icon, from the bottom centre of the game (1440p pixels): x from, x to, up from bottom (from, to)
SEARCH = (240, 620, 170, 0)
TEXT_BOX = (50, 120, 6, 44)      # the counter's box, relative to the icon's top-left: x from, x to, y from, y to
ICON_MIN = 0.62                  # template-match score that counts as "the icon is there"
POLL = 0.5


# ================================================================ reading a counter (pure functions: tested offline)
def bright_mask(gray, thr):
    return gray > thr


def glyph_spans(mask):
    """Column ranges (x0, x1) that hold bright pixels, split at empty columns."""
    cols = mask.any(axis=0)
    spans, start = [], None
    for x, on in enumerate(list(cols) + [False]):
        if on and start is None:
            start = x
        elif not on and start is not None:
            spans.append((start, x - 1))
            start = None
    return spans


GRID = (12, 8)                   # a glyph is compared as a 12 x 8 grid of how much ink each cell holds
_REFS = {"list": None}


def glyph_vector(g):
    """A binary glyph -> (grid of ink 0..1, width / height), cut to its ink."""
    import numpy as np
    ys, xs = np.nonzero(g)
    g = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(float)
    h, w = g.shape
    gh, gw = GRID
    out = np.zeros(GRID)
    for r in range(gh):                                # area-average into the grid (no OpenCV needed)
        y0, y1 = r * h / gh, (r + 1) * h / gh
        for c in range(gw):
            x0, x1 = c * w / gw, (c + 1) * w / gw
            cell = g[int(y0):max(int(y0) + 1, int(np.ceil(y1))), int(x0):max(int(x0) + 1, int(np.ceil(x1)))]
            out[r, c] = cell.mean() if cell.size else 0
    return out, w / h


def references():
    """[(digit, grid, aspect)]: shapes of 0 - 4 from the game itself (ritual_glyphs.json, shipped) plus any the app
    learned on this PC (data folder / ritual / learned.json)."""
    import json
    import numpy as np
    if _REFS["list"] is None:
        refs = []
        base = getattr(sys, "_MEIPASS", None)
        here = Path(base) / "soe2" if base else Path(__file__).resolve().parent
        for p in (here / "ritual_glyphs.json", Path(os.environ.get("SOE2_RITUAL_LEARNED", "")) if
                  os.environ.get("SOE2_RITUAL_LEARNED") else None):
            try:
                for d, grid, asp in json.loads(Path(p).read_text())["glyphs"]:
                    refs.append((int(d), np.array(grid, float).reshape(GRID), float(asp)))
            except Exception:
                pass
        _REFS["list"] = refs
    return _REFS["list"]


def classify_digit(g):
    """A binary glyph (rows x cols, True = ink) -> 0..4, or None: the nearest reference shape."""
    import numpy as np
    if g.sum() < 6 or g.shape[0] < 6:
        return None
    vec, asp = glyph_vector(g)
    best, best_d = None, 1e9
    for d, grid, a in references():
        dist = float(((vec - grid) ** 2).sum()) + 8.0 * abs(asp - a)
        if dist < best_d:
            best, best_d = d, dist
    return best if best_d < 14.0 else None


def text_band(m):
    """The rows of the text itself: the tallest run of rows with ink (gaps of one row allowed). 2.14.1: the box also
    catches the icon's edge above and the frame's ornament below, which used to glue the glyphs together."""
    import numpy as np
    rows = m.any(axis=1)
    best, start, gap = None, None, 0
    for y, on in enumerate(list(rows) + [False, False]):
        if on:
            if start is None:
                start = y
            gap, end = 0, y
        elif start is not None:
            gap += 1
            if gap > 1:
                if best is None or end - start > best[1] - best[0]:
                    best = (start, end)
                start, gap = None, 0
    return best


def read_text(gray):
    """The counter's box (grayscale array, white text on black) -> (done, total) or None."""
    import numpy as np
    for thr in (150, 175, 200, 125):
        m = bright_mask(gray, thr)
        band = text_band(m)
        if band is None:
            return None
        m = m[band[0]:band[1] + 1, :]
        spans = [s for s in glyph_spans(m) if m[:, s[0]:s[1] + 1].sum() >= 4]
        if len(spans) != 3:
            continue
        a, slash, b = (m[:, s[0]:s[1] + 1] for s in spans)
        if not _is_slash(slash):
            continue
        done, total = classify_digit(a), classify_digit(b)
        if done is None or total is None:
            continue
        if total in (3, 4) and 0 <= done <= total:
            return done, total
    return None


def _is_slash(g):
    """Ink goes from bottom-left to top-right."""
    import numpy as np
    ys, xs = np.nonzero(g)
    if len(ys) < 4:
        return False
    h = ys.max() - ys.min() + 1
    w = xs.max() - xs.min() + 1
    if w > h:
        return False
    top = xs[ys <= ys.min() + h // 3].mean()
    low = xs[ys >= ys.max() - h // 3].mean()
    return top > low


def find_icon(gray, tpl_gray, ui):
    """-> (x, y, score) of the Ritual icon's top-left in `gray`, or None."""
    import cv2
    import numpy as np
    size = max(12, int(round(tpl_gray.shape[0] * ui)))
    t = cv2.resize(tpl_gray, (size, size), interpolation=cv2.INTER_AREA)
    if gray.shape[0] < t.shape[0] or gray.shape[1] < t.shape[1]:
        return None
    res = cv2.matchTemplate(gray.astype(np.uint8), t.astype(np.uint8), cv2.TM_CCOEFF_NORMED)
    _mn, score, _ml, (x, y) = cv2.minMaxLoc(res)
    return (x, y, score) if score >= ICON_MIN else None


def find_icon_score(gray, tpl_gray, ui):
    """The best icon match score anywhere in the area (for the log)."""
    try:
        import cv2
        import numpy as np
        size = max(12, int(round(tpl_gray.shape[0] * ui)))
        t = cv2.resize(tpl_gray, (size, size), interpolation=cv2.INTER_AREA)
        return float(cv2.matchTemplate(gray.astype(np.uint8), t.astype(np.uint8), cv2.TM_CCOEFF_NORMED).max())
    except Exception:
        return -1.0


def search_rect(sw, sh, ox, oy):
    """The part of the screen to capture: (left, top, width, height)."""
    ui = sh / BASE_H
    cx = ox + sw // 2
    x0, x1 = cx + int(SEARCH[0] * ui), cx + int(SEARCH[1] * ui)
    y0, y1 = oy + sh - int(SEARCH[2] * ui), oy + sh - int(SEARCH[3] * ui)
    return x0, y0, x1 - x0, y1 - y0


def read_counter(gray, tpl_gray, ui):
    """The captured search area (grayscale) -> ("ok", (done, total)), ("unread", None) when the icon is there but the
    numbers can't be read, or ("none", None) when there's no Ritual counter on screen."""
    hit = find_icon(gray, tpl_gray, ui)
    if hit is None:
        return "none", None
    x, y, _s = hit
    bx0, bx1 = x + int(TEXT_BOX[0] * ui), x + int(TEXT_BOX[1] * ui)
    by0, by1 = y + int(TEXT_BOX[2] * ui), y + int(TEXT_BOX[3] * ui)
    box = gray[max(0, by0):by1, max(0, bx0):bx1]
    got = read_text(box) if box.size else None
    return ("ok", got) if got else ("unread", None)


# ================================================================ the helper process
def main(argv):
    """StashOfExile2.exe --ritual <data folder>"""
    from .delirium_runner import _reopen_std
    _reopen_std()           # 2.14.1: the windowed exe has no stdin / stdout until they're opened from the OS handles -
    #                         without this the helper quit at once and the app never heard a count
    folder = Path(argv[0]) if argv else Path.home() / ".stashofexile2"
    folder = folder / "ritual"
    folder.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    logf = folder / "ritual_log.txt"
    try:
        if logf.exists() and logf.stat().st_size > 300_000:
            logf.replace(folder / "ritual_log.old.txt")
    except OSError:
        pass

    def log(line):
        try:
            with open(logf, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {line}\n")
        except OSError:
            pass

    def say(line):
        log(line)
        with lock:
            try:
                sys.stdout.write(str(line).rstrip("\n") + "\n")
                sys.stdout.flush()
            except Exception:
                pass

    cmds = []

    def read_stdin():
        try:
            for line in sys.stdin:
                if line.strip():
                    cmds.append(line.strip())
        except Exception:
            pass
        cmds.append("quit")
    threading.Thread(target=read_stdin, daemon=True).start()
    try:
        import cv2
        import mss
        import numpy as np
        from . import delirium_alert as D
        D.make_dpi_aware()
        base = getattr(sys, "_MEIPASS", None)
        tdir = Path(base) / "soe2" / "templates" if base else Path(__file__).resolve().parent / "templates"
        tpl = cv2.imread(str(tdir / "ritual_icon.png"), cv2.IMREAD_GRAYSCALE)
        if tpl is None:
            raise RuntimeError("ritual_icon.png is missing from the app")
    except Exception as e:
        say(f"state error")
        say(f"error {type(e).__name__}: {e}")
        return 1
    log(f"started: {len(references())} digit shapes, icon template {tpl.shape}")
    say("state watching")
    last, pending, shown, state = None, None, None, "watching"
    rect_seen, best_log = None, 0.0
    with mss.mss() as sct:
        while True:
            while cmds:
                c = cmds.pop(0)
                if c == "quit":
                    say("state stopped")
                    return 0
                if c == "capture":
                    try:
                        g = D.find_game_rect()
                        sw, sh, ox, oy = g if g else (sct.monitors[1]["width"], sct.monitors[1]["height"],
                                                     sct.monitors[1]["left"], sct.monitors[1]["top"])
                        x, y, w, h = search_rect(sw, sh, ox, oy)
                        shot = np.asarray(sct.grab({"left": x, "top": y, "width": w, "height": h}))
                        p = folder / f"capture_{time.strftime('%Y%m%d_%H%M%S')}.png"
                        cv2.imwrite(str(p), shot[:, :, :3])
                        say(f"captured {p}")
                    except Exception as e:
                        say(f"capture failed: {e}")
            try:
                g = D.find_game_rect()
                if g is None:
                    if state != "nogame":
                        state = "nogame"
                        say("state nogame")
                    time.sleep(1.0)
                    continue
                if state != "watching":
                    state = "watching"
                    say("state watching")
                sw, sh, ox, oy = g
                x, y, w, h = search_rect(sw, sh, ox, oy)
                if (g, (x, y, w, h)) != rect_seen:
                    rect_seen = (g, (x, y, w, h))
                    log(f"game {sw}x{sh} at {ox},{oy}; looking at {w}x{h} at {x},{y}")
                shot = np.asarray(sct.grab({"left": x, "top": y, "width": w, "height": h}))
                gray = cv2.cvtColor(shot, cv2.COLOR_BGRA2GRAY)
                kind, val = read_counter(gray, tpl, sh / BASE_H)
                if kind != "ok" and time.time() - best_log > 60:        # once a minute: how close it got
                    best_log = time.time()
                    hit = find_icon_score(gray, tpl, sh / BASE_H)
                    log(f"{kind}: best icon match {hit:.2f} (needs {ICON_MIN})")
                now = (kind, val)
                if now == pending and now != shown:     # the same twice in a row
                    shown = now
                    say("count none" if kind == "none" else "count unread" if kind == "unread"
                        else f"count {val[0]}/{val[1]}")
                pending = now
            except Exception as e:
                if state != "error":
                    state = "error"
                    say("state error")
                    say(f"error {type(e).__name__}: {e}")
                time.sleep(2.0)
            time.sleep(POLL)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
