"""The session tracker (2.0 beta 9): how long you play, how many maps, time per map, and what it earned.

Pure logic, no windows (tracker_page.py draws it). Fed with events from the game's log (gamelog.py) and with
Wealth totals at the start and the end of a session. Sessions are kept in sessions.json in the data folder.

Map counting: a map is an endgame area (its id starts with "Map") with its own seed. Going back into it from your
hideout logs the same area with the same seed, so it is not counted again; a new map has a new seed."""
import time

from .config import load_json, save_json
from .gamelog import area_kind

FILE = "sessions.json"


def fmt_time(secs):
    secs = int(max(0, secs or 0))
    h, m, s = secs // 3600, secs % 3600 // 60, secs % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def pretty_area(area):
    """'MapSunTemple' -> 'Sun Temple' (when the game didn't tell us the name)."""
    import re
    a = area[3:] if area.startswith("Map") else area
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", a).strip() or area


class Session:
    def __init__(self, now=None, start_value=None, start_items=None):
        now = time.time() if now is None else now
        self.started = now
        self.ended = None
        self.paused_at = None
        self.paused_total = 0.0
        self.maps = []                      # {area, name, level, seed, first, time, entries, deaths}
        self.where = None                   # {"kind", "area", "seed", "since", "map": index or None}
        self.hideout_time = 0.0
        self.other_time = 0.0
        self.gold = 0
        self.deaths = 0
        self.start_value = start_value      # divines (Wealth total at the start)
        self.start_items = start_items or []
        self.end_value = None
        self.profit = None
        self.note = ""
        self.last_event = now

    # ---- time
    def running(self):
        return self.ended is None and self.paused_at is None

    def elapsed(self, now=None):
        now = now or time.time()
        end = self.ended or (self.paused_at or now)
        return max(0.0, end - self.started - self.paused_total)

    def pause(self, now=None):
        if self.ended is None and self.paused_at is None:
            self.paused_at = now or time.time()
            self._close_stretch(self.paused_at)

    def resume(self, now=None):
        if self.paused_at is not None:
            now = now or time.time()
            self.paused_total += now - self.paused_at
            self.paused_at = None
            if self.where:
                self.where["since"] = now

    def _close_stretch(self, now):
        """Add the time since you entered the current area to that area's total."""
        w = self.where
        if not w or w.get("since") is None:
            return
        dt = max(0.0, now - w["since"])
        if w["kind"] == "map" and w.get("map") is not None:
            self.maps[w["map"]]["time"] += dt
        elif w["kind"] in ("hideout", "town"):
            self.hideout_time += dt
        else:
            self.other_time += dt
        w["since"] = now

    def current_map_time(self, now=None):
        now = now or time.time()
        w = self.where
        if not w or w["kind"] != "map" or w.get("map") is None:
            return None
        live = (now - w["since"]) if (self.running() and w.get("since") is not None) else 0
        return self.maps[w["map"]]["time"] + live

    # ---- events from the log
    def feed(self, kind, ts, data):
        """One event (gamelog.parse) -> True if it changed something worth redrawing."""
        if self.ended is not None:
            return False
        if ts < self.started - 1:
            return False
        self.last_event = ts
        if kind == "area":
            if self.running():
                self._close_stretch(ts)
            k = area_kind(data["area"], data["seed"])
            idx = None
            if k == "map":
                idx = next((i for i, m in enumerate(self.maps) if m["area"] == data["area"] and m["seed"] == data["seed"]), None)
                if idx is None:
                    self.maps.append({"area": data["area"], "name": pretty_area(data["area"]), "level": data["level"],
                                      "seed": data["seed"], "first": ts, "time": 0.0, "entries": 1, "deaths": 0})
                    idx = len(self.maps) - 1
                else:
                    self.maps[idx]["entries"] += 1
            self.where = {"kind": k, "area": data["area"], "seed": data["seed"], "since": ts if self.running() else None,
                          "map": idx, "named": False}
            return True
        if kind == "scene" and self.where and not self.where.get("named") and data["name"] not in ("Atlas",):
            self.where["named"] = True
            self.where["name"] = data["name"]
            if self.where.get("map") is not None:
                self.maps[self.where["map"]]["name"] = data["name"]
            return True
        if kind == "gold":
            self.gold += data["amount"]
            return True
        if kind == "death":
            self.deaths += 1
            if self.where and self.where.get("map") is not None:
                self.maps[self.where["map"]]["deaths"] += 1
            return True
        return False

    def map_count(self):
        return len(self.maps)

    def avg_map_time(self, now=None):
        if not self.maps:
            return None
        times = [m["time"] for m in self.maps]
        cur = self.current_map_time(now)
        if cur is not None and self.where and self.where.get("map") is not None:
            times[self.where["map"]] = cur
        return sum(times) / len(times)

    def location(self):
        w = self.where
        if not w:
            return "-"
        return w.get("name") or (pretty_area(w["area"]) if w["kind"] == "map" else w["area"])

    # ---- the end
    def stop(self, now=None, end_value=None, profit=None):
        now = now or time.time()
        if self.paused_at is not None:
            self.resume(now)
        self._close_stretch(now)
        self.ended = now
        self.end_value = end_value
        self.profit = profit

    def per_hour(self):
        h = self.elapsed() / 3600
        return self.profit / h if (self.profit is not None and h > 0.01) else None

    def to_json(self):
        d = {k: v for k, v in self.__dict__.items() if k not in ("start_items",)}
        return d

    @classmethod
    def from_json(cls, d):
        s = cls(now=d.get("started"))
        s.__dict__.update({k: v for k, v in d.items() if k in s.__dict__})
        return s


class Sessions:
    """sessions.json: past sessions, newest last."""

    def __init__(self):
        self.items = [Session.from_json(d) for d in (load_json(FILE, {}) or {}).get("sessions", [])]

    def add(self, s):
        self.items.append(s)
        self.save()

    def save(self):
        save_json(FILE, {"sessions": [s.to_json() for s in self.items[-500:]]})


MIN_RUN_SECS = 30          # shorter visits (walked in and straight out again) don't count as runs


def daily_maps(sessions, current=None, days=14, now=None, min_secs=MIN_RUN_SECS):
    """2.7.0: maps run per day, the last `days` days (today last): [(date, maps, deaths, seconds in maps)].
    A map counts on the day you first entered it; visits under min_secs don't count (like Map stats)."""
    import datetime as _dt
    now = now or time.time()
    today = _dt.date.fromtimestamp(now)
    out = {today - _dt.timedelta(days=i): [0, 0, 0.0] for i in range(days)}
    every = list(sessions) + ([current] if current is not None and current not in sessions else [])
    for s in every:
        for m in s.maps:
            if m.get("time", 0) < min_secs:
                continue
            d = _dt.date.fromtimestamp(m.get("first") or s.started)
            if d in out:
                out[d][0] += 1
                out[d][1] += m.get("deaths", 0)
                out[d][2] += m.get("time", 0)
    return [(d, *out[d]) for d in sorted(out)]


def map_stats(sessions, current=None, now=None, min_secs=MIN_RUN_SECS):
    """Every map you ran, over all sessions (2.1.0): {map name: {"runs", "best", "avg", "median", "total", "deaths",
    "last", "levels", "list": [run, ...] fastest first}} - a run is {"time", "when", "level", "deaths"}.
    The time is the time spent inside the map (time in your hideout in between isn't counted)."""
    import statistics
    out = {}
    pool = list(sessions)
    if current is not None and current not in pool:
        pool.append(current)
    for s in pool:
        live = s.where.get("map") if (s.ended is None and s.where) else None
        for i, m in enumerate(s.maps):
            t = s.current_map_time(now) if live == i else m["time"]
            if t is None or t < min_secs:
                continue
            d = out.setdefault(m["name"], {"list": []})
            d["list"].append({"time": t, "when": m.get("first") or s.started, "level": m.get("level"),
                              "deaths": m.get("deaths", 0), "live": live == i})
    for name, d in out.items():
        times = [r["time"] for r in d["list"]]
        d["list"].sort(key=lambda r: r["time"])
        d.update(runs=len(times), best=min(times), avg=sum(times) / len(times), median=statistics.median(times),
                 total=sum(times), deaths=sum(r["deaths"] for r in d["list"]),
                 last=max(r["when"] for r in d["list"]),
                 levels=sorted({r["level"] for r in d["list"] if r["level"]}))
    return out


def value_at(items, prices, overrides, wealth_key, value_fn=None):
    """What a list of Wealth items is worth at today's prices (used for both ends of a session, so a price change
    in between doesn't count as profit)."""
    total = 0.0
    for it in items:
        ov = overrides.get(wealth_key(it))
        each = float(ov) if ov is not None else (value_fn or prices.value)(it)[0]
        if each is not None:
            total += each * (it.get("qty") or 1)
    return total
