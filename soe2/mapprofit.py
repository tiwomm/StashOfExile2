"""2.132.0 Map profit (feedback: "use the same data from wealth stash scan to read inventory for currency/omens/etc
and track the profit per map ... using the same mechanism as top-up reminders"; "should only be locally, never
published or sent to the cloudflare database"; "would not count waystones, only currency exchange items"; "track
per session/map/hour/day and log somewhere locally that only the user can see").

How: Top Up's quick inventory read (the inventory panel only, never the stash side) is taken in your hideout or a
town. The last clear read before a map is "before"; the first clear read after it is "after". What changed is that
map's loot. Each cell is named by its picture - the ones you taught with Ctrl+C (Top Up) or the ones Scan stash
learned - and only items with a Currency Exchange price (poe.ninja's exchange: currency, omens, runes, ...) count;
waystones and gear never do. Prices: Exchange Rates (poe.ninja, in divines).

Privacy: map_profit.jsonl in your data folder, on your PC only - never uploaded, shared or sent to the board."""
import json
import os
import time

from . import buglog
from .config import SETTINGS, P

LOG_FILE = "map_profit.jsonl"
DEFAULTS = {"on": False}
KEEP_DAYS = 90                      # the log keeps this many days (older lines are dropped when it's tidied)
BEFORE_SECS = 3 * 3600              # a "before" older than this isn't this map's (you left the game in between)
ARRIVE_SECS = 8                     # 2.132.2: back home, what you came back with = the most seen in this long
DONE_SECS = 15 * 60                 # 2.132.1: out of a map this long (not back through its portal): it's done


def cfg():
    c = SETTINGS.setdefault("map_profit", {})
    for k, v in DEFAULTS.items():
        c.setdefault(k, v)
    return c


# ---------------------------------------------------------------- naming what the inventory holds
def fv_match(cell, refs):
    """A Top Up cell (PIL) -> the exchange item Scan stash learned it to be, or None (the Favours pictures, cut to
    the item's art so a stash slot and an inventory cell line up)."""
    try:
        import numpy as np
        from . import favours as FV
        bgr = np.asarray(cell.convert("RGB"))[:, :, ::-1].copy()
        h, w = bgr.shape[:2]
        e = max(1, int(round(FV.EDGE * w / FV.CELL)))
        name, _score, _margin = refs.best({"box": FV.feats(FV.art_box(bgr[e:h - e, e:w - e]))})
        return name
    except Exception:
        buglog.caught()
        return None


def identify(cells, taught, refs=None):
    """Top Up's cells -> ({name: count}, how many cells it couldn't name). Taught pictures first, then Scan stash's."""
    from . import topup as TU
    out, unknown = {}, 0
    for c in cells or []:
        name = TU.which(c["sig"], taught) if taught else None
        if name is None and refs is not None and c.get("img") is not None:
            name = fv_match(c["img"], refs)
        if name is None:
            unknown += 1
            continue
        out[name] = out.get(name, 0) + (c["count"] if c.get("count") is not None else 1)
    return out, unknown


def exchange_only(counts, price):
    """Only Currency Exchange items (price(name) -> divines each, or None: not on the exchange - never counted)."""
    return {n: k for n, k in counts.items() if price(n) is not None}


# ---------------------------------------------------------------- one map
def rows(before, after, price):
    """-> [(name, before, after, divines each, worth)] for what a map gained, most worth first. 2.132.2 (feedback:
    "why is it marking as -div if I didn't actually lose anything"): fewer of an item is never counted - it was used,
    stashed or covered, not lost to the map."""
    out = []
    for name in set(before) | set(after):
        b, a = before.get(name, 0), after.get(name, 0)
        if a <= b:
            continue
        each = price(name)
        if each is None:
            continue
        out.append((name, b, a, each, (a - b) * each))
    out.sort(key=lambda r: -r[4])
    return out


def entry(map_name, secs, before, after, price, t=None, unknown=0):
    """One map's line for the log."""
    rs = rows(before, after, price)
    return {"t": round(t if t is not None else time.time()), "map": map_name or "", "secs": int(secs or 0),
            "div": round(sum(r[4] for r in rs), 4), "unknown": int(unknown),
            "rows": [[r[0], r[1], r[2], round(r[3], 6)] for r in rs]}


# ---------------------------------------------------------------- the log (your PC only)
def log_add(e):
    try:
        with open(P(LOG_FILE), "a", encoding="utf-8") as f:
            f.write(json.dumps(e) + "\n")
        return True
    except OSError:
        buglog.caught()
        return False


def log_read(since=0):
    out = []
    try:
        with open(P(LOG_FILE), encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if isinstance(e, dict) and e.get("t", 0) >= since:
                    out.append(e)
    except FileNotFoundError:
        pass
    except OSError:
        buglog.caught()
    return out


def log_tidy(now=None):
    """Drop lines older than KEEP_DAYS (once a day is plenty)."""
    now = now or time.time()
    keep = log_read(now - KEEP_DAYS * 86400)
    try:
        if os.path.exists(P(LOG_FILE)) and len(keep) < sum(1 for _ in open(P(LOG_FILE), encoding="utf-8")):
            tmp = P(LOG_FILE) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.writelines(json.dumps(e) + "\n" for e in keep)
            os.replace(tmp, P(LOG_FILE))
    except OSError:
        buglog.caught()


def log_write(entries):
    """Rewrite the log with these lines (2.132.6: deleting maps)."""
    try:
        tmp = P(LOG_FILE) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(e) + "\n" for e in entries)
        os.replace(tmp, P(LOG_FILE))
        return True
    except OSError:
        buglog.caught()
        return False


def log_delete(run_ids):
    """Drop every line of these maps (their run ids). -> the dropped lines (for Undo)."""
    ids = set(run_ids)
    keep, gone = [], []
    for e in log_read():
        (gone if (e.get("run") or str(e.get("t"))) in ids else keep).append(e)
    if gone:
        log_write(keep)
    return gone


def log_restore(lines):
    """Undo a delete: the lines back, in time order."""
    log_write(sorted(log_read() + list(lines), key=lambda e: e.get("t", 0)))


def buckets(runs, kind, now=None):
    """2.132.6 (feedback: "a log by date ... with graphs and bars ... All Time, Daily, Hourly"): maps -> [(label,
    start time, maps, div, secs)], oldest first. kind: "day" (each day with maps) or "hour" (the last 48 hours, each
    hour)."""
    now = now or time.time()
    out = {}
    for r in runs:
        lt = time.localtime(r["t"])
        if kind == "hour":
            if r["t"] < now - 48 * 3600:
                continue
            start = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour, 0, 0, 0, 0, -1))
            label = time.strftime("%a %H:00", lt)
        else:
            start = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
            label = time.strftime("%a %d %b", lt)
        b = out.setdefault(start, [label, start, 0, 0.0, 0])
        b[2] += 1
        b[3] += r["div"]
        b[4] += r["secs"]
    return [tuple(b) for _s, b in sorted(out.items())]


def day_start(now=None):
    lt = time.localtime(now or time.time())
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))


def totals(entries, now=None, session_start=None):
    """-> {"map": last map's div, "session": (div, maps), "hour": div in the last hour, "day": (div, maps) today,
    "per_map": session average, "per_hour": session div per hour of maps}."""
    now = now or time.time()
    es = sorted(entries, key=lambda e: e.get("t", 0))
    ses = [e for e in es if session_start is None or e.get("t", 0) >= session_start]
    today = [e for e in es if e.get("t", 0) >= day_start(now)]
    s_div = sum(e.get("div", 0) for e in ses)
    s_secs = sum(e.get("secs", 0) for e in ses)
    return {"map": es[-1].get("div") if es else None,
            "session": (s_div, len(ses)),
            "hour": sum(e.get("div", 0) for e in es if e.get("t", 0) >= now - 3600),
            "day": (sum(e.get("div", 0) for e in today), len(today)),
            "per_map": s_div / len(ses) if ses else None,
            "per_hour": s_div * 3600 / s_secs if s_secs >= 60 else None}


def signed(v, fmt):
    """+3.8 div / −0.4 div (fmt: pricefmt.fmt_div)."""
    if v is None:
        return "–"
    return ("+" if v >= 0 else "−") + fmt(abs(v))
