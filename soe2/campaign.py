"""The Campaign Helper (2.77.0): where you are in the campaign, what's next and what it's worth - from the game's log.

  * It follows you. Entering a zone jumps to that zone's step; steps you went past without entering are "passed".
    It never forces a route: click a step (or ◀ ▶, or their keys) to say "I'm here".
  * Rewards (passive points, spirit, resistances ...): only what the log can prove ticks by itself (a reward's
    "proof" zones). Leaving an act, a reward whose zone you never entered is "Missed"; one whose zone you entered
    asks "Did you get it?" - Got it, Remind me in town, Skip it. A tick you set by hand always wins.
  * Zones the guide doesn't know (a new act) are added to your route in the order you went, with their level, and
    (with Community data sharing on) pooled so the next guide pack has them.
  * Act splits: time in each act (pauses for AFK and long gaps), and your best per league.

The guide pack is campaign.json: bundled with the app, and updated from GitHub without an app update ("Check for a
newer one"). Stored in SETTINGS["campaign"]. Reads only Client.txt; nothing is sent to the game."""
import copy
import json
import os
import re
import time

from .config import APP_UA, APP_DIR, RESOURCE_DIR, P, SETTINGS, load_json, save_json

FILE = "campaign.json"
SCHEMA = 1
REPO = "tiwomm/StashOfExile2"
LIVE_URL = f"https://raw.githubusercontent.com/{REPO}/main/{FILE}"
GAP = 15 * 60                     # a longer gap between two log lines isn't counted in a split (away, or closed)
ROUTES = (("full", "Full"), ("speed", "Speedrun"), ("rush", "Rush (carry)"), ("mine", "My Own"))   # (2.125.3 names)
# 2.125.0 (feedback: "a rush/carry helper ... in the perspective of the person giving the carry"): each route in one line
ROUTE_LINES = {"full": "Every passive point, spirit and resistance, with the side zones that give them.",
               "speed": "The main story. Skips side zones and most extras; keeps the rewards worth the time.",
               "rush": "You're carrying someone: what to clear, when to bring them in, what they pick up and who they "
                       "talk to.",
               "mine": "The zones in the order you went last time."}
KIND_NAMES = {"points": "passive points", "spirit": "spirit", "res_cold": "cold res", "res_fire": "fire res",
              "res_lightning": "lightning res", "life": "life", "mana": "mana", "other": "other"}
SHORT_GIVES = {"points": "+{n} points", "spirit": "+{n} spirit", "res_cold": "+{n}% cold", "res_fire": "+{n}% fire",
               "res_lightning": "+{n}% lightning", "life": "+{n} life", "mana": "+{n}% mana"}
DEFAULTS = {
    "on": True,                   # the feature (Overlay › Options › On the overlay, and the Campaign switch on the bar)
    "line": True,                 # its line on the goal bar (2.97.0: always - on means it shows)
    "vendor": True,               # Vendor search, in town
    "route": "full",              # the default guide (2.89.0: each character's run keeps its own, run["route"])
    "ask_route": True,            # 2.89.0: a new campaign asks which route
    "optional": False,            # show optional zones
    "tips": True,
    "warn": True,                 # leaving an act with a reward missed or not ticked: ask
    "splits": True,
    "off_at_maps": True,          # turn itself off once you reach maps
    "chars": {},                  # character -> its run (see char())
    "best": {},                   # league -> {act key: seconds}
    "mine": {},                   # act key -> [zone] (My Own route: your last finished act)
    "learned": {},                # act key -> [{zone, after, level}] zones the guide didn't know
    "notes": {},                  # zone (norm) -> your note
    "optional_zones": [],         # zones you marked optional
    "sent": [],                   # learned zones already pooled ("act|zone")
    "pack_checked": 0,
}
CAMP_ID = re.compile(r"^(G|P)(\d+)(?:_|$)")


def cfg():
    c = SETTINGS.setdefault("campaign", {})
    for k, v in DEFAULTS.items():
        if k not in c:                                   # 2.125.4: copied only when missing (it ran on every call)
            c[k] = copy.deepcopy(v)
    return c


def save():
    save_json("settings.json", SETTINGS)


def norm(name):
    s = re.sub(r"[^a-z0-9 ]", "", str(name or "").lower()).strip()
    return s[4:] if s.startswith("the ") else s


# ---------------------------------------------------------------- the guide pack
_PACK = {"key": None, "data": None}


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) and isinstance(d.get("acts"), list) else None
    except (OSError, ValueError):
        return None


def _newness(d):
    return d.get("schema", 1), d.get("revision", 0)


def pack():
    """-> the newest guide pack (fetched or bundled)."""
    paths = (P(FILE), os.path.join(RESOURCE_DIR, FILE), os.path.join(APP_DIR, FILE))
    key = tuple((p, os.path.getmtime(p)) for p in paths if os.path.isfile(p))
    if _PACK["key"] == key and _PACK["data"] is not None:
        return _PACK["data"]
    best = None
    for p in paths:
        d = _read(p)
        if d and d.get("schema", 1) <= SCHEMA and (best is None or _newness(d) > _newness(best)):
            best = d
    best = best or {"schema": SCHEMA, "revision": 0, "patch": "?", "name": "none", "acts": [], "rewards": [], "vendor": []}
    _PACK.update(key=key, data=best)
    return best


def fetch_live(get=None):
    """Check GitHub for a newer guide pack. -> ("new", name) / ("same", name) / ("error", why)."""
    if get is None:
        import requests
        get = requests.get
    try:
        r = get(LIVE_URL, headers={"User-Agent": APP_UA}, timeout=15)
        if r.status_code != 200:
            return "error", f"GitHub answered {r.status_code}."
        d = r.json()
    except Exception as e:
        return "error", f"Could not reach GitHub ({e.__class__.__name__})."
    cfg()["pack_checked"] = time.time()
    if not isinstance(d, dict) or not isinstance(d.get("acts"), list):
        return "error", "The guide pack on GitHub could not be read."
    if d.get("schema", 1) > SCHEMA:
        return "error", "The newest guide pack needs a newer version of the app - update it."
    if _newness(d) <= _newness(pack()):
        return "same", pack().get("name", "")
    save_json(FILE, d)
    _PACK["key"] = None
    return "new", d.get("name", "")


def acts():
    return pack().get("acts") or []


def act(key):
    return next((a for a in acts() if a.get("key") == key), None)


def act_order(key):
    keys = [a.get("key") for a in acts()]
    return keys.index(key) if key in keys else len(keys)


def act_name(key):
    a = act(key)
    if a:
        return a.get("name", key)
    if str(key).startswith("i"):
        return f"Interlude {key[1:]}"
    return f"Act {key}?"


def act_of_id(area_id):
    """'G2_4_1' -> '2', 'P1_x' -> 'i1', else None."""
    m = CAMP_ID.match(str(area_id or ""))
    if not m:
        return None
    return m.group(2) if m.group(1) == "G" else "i" + m.group(2)


def find_zone(name):
    """-> (act key, step index) for a zone the guide knows, or (None, None)."""
    n = norm(name)
    for a in acts():
        for i, s in enumerate(a.get("steps") or []):
            if norm(s.get("zone")) == n:
                return a.get("key"), i
    return None, None


def rewards(act_key=None):
    return [r for r in pack().get("rewards") or [] if act_key is None or r.get("act") == act_key]


def short_gives(r):
    f = SHORT_GIVES.get(r.get("kind"))
    return f.format(n=r.get("amount", "")) if f else r.get("gives", "")


# ---------------------------------------------------------------- a character's run
def char(name=None):
    c = cfg()
    name = current_char() if name is None else name
    run = c["chars"].setdefault(name or "", {})
    if not run.get("league"):                             # 2.86.0: a new run - its league (for the leaderboards)
        run["league"] = SETTINGS.get("league") or ""      # (2.124.1: and an older run that had none)
    for k, v in (("act", None), ("zone", None), ("here", None), ("seen", {}), ("levels", {}), ("rewards", {}),
                 ("ask", []), ("secs", {}), ("last_ts", None), ("afk", False), ("done", False), ("zone_level", 0),
                 ("pending", None), ("unknown", None), ("visit", False)):
        run.setdefault(k, copy.deepcopy(v))
    return run


def current_char():
    from . import focus as F
    st = F.cfg().get("state") or {}
    return st.get("last_char") or (SETTINGS.get("tracker") or {}).get("character") or ""


def char_level():
    from . import focus as F
    st = F.cfg().get("state") or {}
    return int((st.get("levels") or {}).get(current_char(), 0) or 0)


def route_of(run=None):
    """2.89.0: this run's guide - the one picked when its campaign started, else the default."""
    run = run or char()
    r = run.get("route") or cfg()["route"]
    return r if r in dict(ROUTES) else "full"


def needs_route(run=None):
    """2.89.0 (feedback): a run in the campaign that hasn't picked its guide yet."""
    c = cfg()
    run = run or char()
    return bool(c["on"] and c["ask_route"] and run.get("act") is not None and not run.get("done")
                and not run.get("route"))


def set_route(route, run=None, remember=False):
    """Pick this run's guide. remember: it's the default and new campaigns stop asking."""
    c = cfg()
    run = run or char()
    run["route"] = route if route in dict(ROUTES) else "full"
    if remember:
        c["route"], c["ask_route"] = run["route"], False
    save()


def speed_reward(r):
    """A reward a speedrun still takes (the pack marks it "speed": true)."""
    return bool(r.get("speed"))


def steps(act_key, run=None, route=None, optional=None):
    """The route for an act -> [{zone, do, side, optional, tip, learned, state}] (state: done / here / passed / todo).
    2.89.0: Speedrun leaves out steps the pack marks "speed": {"skip": true} (and side zones), and shows a step's
    "speed": {"do": ...} instead of its usual "do". 2.125.0: Rush (carry) the same with "rush" (side zones with a
    rush line stay)."""
    c = cfg()
    run = run or char()
    route = route or route_of(run)
    optional = c["optional"] if optional is None else optional
    a = act(act_key) or {"steps": []}
    rows = [dict(s) for s in a.get("steps") or []]
    known = {norm(s["zone"]) for s in rows}
    for lz in c["learned"].get(act_key) or []:                 # zones the guide didn't know: after the one before
        if norm(lz["zone"]) in known:
            continue
        at = next((i for i, s in enumerate(rows) if norm(s["zone"]) == norm(lz.get("after"))), len(rows) - 1)
        rows.insert(at + 1, {"zone": lz["zone"], "do": "", "learned": True, "level": lz.get("level")})
        known.add(norm(lz["zone"]))
    marked = set(c["optional_zones"])
    for s in rows:
        if norm(s["zone"]) in marked:
            s["optional"] = True
    if route == "mine" and c["mine"].get(act_key):
        order = [norm(z) for z in c["mine"][act_key]]
        pos = {z: i for i, z in enumerate(order)}
        rows = [s for _k, s in sorted(((pos.get(norm(s["zone"]), len(order) + j), s) for j, s in enumerate(rows)),
                                      key=lambda t: t[0])]
    if route == "speed":
        rows = [s for s in rows if not s.get("side") and not (s.get("speed") or {}).get("skip")]
        for s in rows:
            if (s.get("speed") or {}).get("do"):
                s["do"] = s["speed"]["do"]
    if route == "rush":                                       # 2.125.0: the carrier's guide ("rush" in the pack); a
        def rush(s):                                          # step without one follows Speedrun
            return s.get("rush") or s.get("speed") or {}
        rows = [s for s in rows if not rush(s).get("skip") and (not s.get("side") or (s.get("rush") or {}).get("do"))]
        for s in rows:
            if rush(s).get("do"):
                s["do"] = rush(s)["do"]
    if not optional:
        rows = [s for s in rows if not s.get("optional") or norm(s["zone"]) in _seen(run, act_key)]
    seen = _seen(run, act_key)
    cur = _here_index(run, act_key, rows)
    for i, s in enumerate(rows):
        z = norm(s["zone"])
        s["state"] = "here" if i == cur else ("done" if z in seen and (cur is None or i < cur) else
                                              ("passed" if cur is not None and i < cur else "todo"))
        if z in seen and s["state"] == "todo":
            s["state"] = "done"
        s["note"] = c["notes"].get(z, "")
    return rows


def _seen(run, act_key):
    return [norm(z) for z in (run["seen"].get(act_key) or [])]


def _here_index(run, act_key, rows):
    if run.get("act") != act_key:
        return None
    if run.get("here") is not None:
        return max(0, min(int(run["here"]), len(rows) - 1)) if rows else None
    z = norm(run.get("zone"))
    return next((i for i, s in enumerate(rows) if norm(s["zone"]) == z), None)


def set_here(i, run=None):
    """'I'm here': step i of the current act (a manual pick; the next zone you enter moves it again)."""
    run = run or char()
    if run.get("act") is None:
        return
    rows = steps(run["act"], run)
    if rows:
        run["here"] = max(0, min(int(i), len(rows) - 1))
    save()


def step_by(delta, run=None):
    """◀ / ▶: one step back or on."""
    run = run or char()
    if run.get("act") is None:
        return None
    rows = steps(run["act"], run)
    cur = _here_index(run, run["act"], rows)
    set_here((0 if cur is None else cur) + delta, run)
    return run["here"]


def start_here(act_key, i, run=None):
    """'Start from here' (a character that's partway through): this act, this step; earlier acts count as done."""
    run = run or char()
    run["act"], run["here"] = act_key, int(i)
    rows = steps(act_key, run)
    run["zone"] = rows[int(i)]["zone"] if rows and 0 <= int(i) < len(rows) else None
    save()


# ---------------------------------------------------------------- rewards
def reward_state(r, run=None):
    """'got' / 'skip' / 'remind' / 'missed' / 'ask' / 'open'."""
    run = run or char()
    have = run["rewards"].get(r["id"])
    if have:
        return have
    return "open"


def set_reward(rid, state, run=None):
    """A tick by hand (or an answer: got / skip / remind / None to clear) - always wins over the log."""
    run = run or char()
    if state is None:
        run["rewards"].pop(rid, None)
    else:
        run["rewards"][rid] = state
    if state in ("got", "skip", None):
        run["ask"] = [x for x in run["ask"] if x != rid]
    save()


def totals(run=None):
    """-> {kind: (have, of)} over the whole pack."""
    run = run or char()
    out = {}
    for r in rewards():
        k = r.get("kind", "other")
        have, of = out.get(k, (0, 0))
        n = int(r.get("amount") or 0) if k != "other" else 1
        out[k] = (have + (n if run["rewards"].get(r["id"]) == "got" else 0), of + n)
    return out


def asks(run=None):
    """Rewards waiting for an answer -> [(reward, 'missed' / 'ask' / 'remind')]."""
    run = run or char()
    by = {r["id"]: r for r in rewards()}
    return [(by[x], run["rewards"].get(x) or "ask") for x in run["ask"] if x in by]


def _close_act(run, key, now):
    """Leaving an act for a later one: its split, My Own route, and the rewards to ask about."""
    c = cfg()
    secs = run["secs"].get(key)
    if secs:
        league = SETTINGS.get("league") or ""
        b = c["best"].setdefault(league, {})
        if key not in b or secs < b[key]:
            b[key] = round(secs)
    if run["seen"].get(key):
        c["mine"][key] = list(run["seen"][key])
    seen = set(_seen(run, key))
    speed = route_of(run) in ("speed", "rush")
    for r in rewards(key):
        st = run["rewards"].get(r["id"])
        if st in ("got", "skip"):
            continue
        if speed and not speed_reward(r):                   # 2.89.0: a speedrun leaves it - no "missed" nag
            continue
        if norm(r["zone"]) not in seen:
            run["rewards"][r["id"]] = "missed"
        if c["warn"] and r["id"] not in run["ask"]:
            run["ask"].append(r["id"])


# ---------------------------------------------------------------- the log
def log_event(kind, ts, data, area_kind=None):
    """A game-log event. -> 'zone' (moved), 'unknown' (a zone the guide doesn't know), 'ask' (left an act with
    rewards to answer), 'maps' or None."""
    c = cfg()
    if not c["on"]:
        return None
    run = char()
    out = None
    if kind == "afk":
        _tick(run, ts)
        run["afk"] = bool(data.get("on"))
        return None
    if kind == "level":
        return None
    if kind == "area":
        if run["pending"]:                                        # (its scene line never came)
            out = _enter(run, run["pending"]["id"], run["pending"]["id"], run["pending"]["level"], ts)
        run["pending"] = None
        aid = data.get("area", "")
        ak = act_of_id(aid)
        if area_kind == "map":
            run["visit"] = False
            _tick(run, ts)
            if not run["done"]:
                run["done"] = True
                if run.get("act"):
                    _close_act(run, run["act"], ts)
                save()
                return "maps"
            return out
        if ak is None:
            run["visit"] = False                                  # 2.97.0: left the campaign zones
            _tick(run, ts)
            _zone_done(run)                                       # (2.124.0: a hideout ends the zone's time)
            run["away"] = True
            run["last_ts"] = ts                                   # (a hideout: time there isn't the act's)
            return out
        run["pending"] = {"id": aid, "level": int(data.get("level") or 0), "act": ak}
        return out
    if kind == "scene" and run["pending"]:
        p, run["pending"] = run["pending"], None
        return _enter(run, data.get("name") or p["id"], p["id"], p["level"], ts, p["act"])
    return out


def _tick(run, ts):
    last, run["last_ts"] = run.get("last_ts"), ts
    if last is None or run.get("act") is None or run.get("afk") or run.get("done"):
        return
    dt = ts - last
    if 0 < dt < GAP:
        run["secs"][run["act"]] = run["secs"].get(run["act"], 0) + dt
        if run.get("zone") and not run.get("away"):          # 2.124.0: the zone's own time too
            run["zone_secs"] = run.get("zone_secs", 0) + dt


def _zone_done(run):
    """2.124.0: leaving a campaign zone - its time is kept, the best per zone (for the Campaign zones leaderboard)."""
    z, secs = run.get("zone"), run.get("zone_secs") or 0
    if z and secs > 0 and not run.get("away"):
        b = run.setdefault("zone_best", {})
        if z not in b or secs < b[z]:
            b[z] = round(secs, 1)
    run["zone_secs"] = 0


def zone_time(run=None, now=None):
    """The time since you came into the campaign zone you're in -> secs, or None (a hideout, or not known since the
    app started - 2.124.1: it showed 0:00 then). The leaderboard's time is zone_secs (AFK left out, campaign runs
    only)."""
    import time as _t
    run = run or char()
    if not active(run) or not run.get("zone") or run.get("away"):
        return None
    t0 = run.get("zone_t0")
    if not t0:
        return None
    dt = (now or _t.time()) - t0
    return dt if 0 <= dt < 3 * 3600 else None


def _enter(run, name, area_id, level, ts, id_act=None):
    c = cfg()
    _tick(run, ts)
    key, _i = find_zone(name)
    key = key or id_act or act_of_id(area_id)
    if key is None:
        return None
    _zone_done(run)                                           # 2.124.0: the zone you left, timed; this one starts
    run["away"] = False
    run["zone_t0"] = ts                                       # 2.124.1: when you came in (the overlay's Zone time)
    if run.get("done"):                                       # 2.97.0: back in a campaign zone after maps - the line
        run["visit"] = True                                   # (and Vendor ▾) show here; the finished run is kept
        run["act"], run["zone"], run["here"], run["zone_level"] = key, name, None, int(level or 0)
        run["unknown"] = None
        save()
        return "zone"
    out = "zone"
    prev = run.get("act")
    if prev is not None and prev != key and act_order(key) > act_order(prev):
        _close_act(run, prev, ts)
        if run["ask"]:
            out = "ask"
    came_from = run.get("zone") if prev == key else None
    run["act"], run["zone"], run["here"], run["zone_level"] = key, name, None, int(level or 0)
    seen = run["seen"].setdefault(key, [])
    if norm(name) not in [norm(z) for z in seen]:
        seen.append(name)
    run["levels"][norm(name)] = int(level or 0)
    for r in rewards(key):                                    # rewards a zone proves
        if any(norm(z) == norm(name) for z in r.get("proof") or []) and r["id"] not in run["rewards"]:
            run["rewards"][r["id"]] = "got"
    if _i is None:                                            # a zone the guide doesn't know (P)
        lz = c["learned"].setdefault(key, [])
        if norm(name) not in [norm(x["zone"]) for x in lz]:
            lz.append({"zone": name, "after": came_from, "level": int(level or 0)})
        run["unknown"] = name
        out = "unknown" if out == "zone" else out
    else:
        run["unknown"] = None
    save()
    return out


# ---------------------------------------------------------------- the line on the overlay
MAPS_LEVEL = 65                   # 2.90.0: a character this level is past the campaign (maps start at 65)


def active(run=None):
    c = cfg()
    run = run or char()
    if not run.get("done") and run.get("act") is not None and char_level() >= MAPS_LEVEL:
        run["done"] = True              # 2.90.0: maps were reached while the log wasn't being read (it showed in the
                                        # hideout, post-campaign)
    return bool(c["on"]) and run.get("act") is not None and not (run.get("done") and c["off_at_maps"]
                                                                 and not run.get("visit"))


def line(run=None):
    """-> {head, do, gives, next, levels, step} for the overlay's campaign line, or None."""
    run = run or char()
    if not active(run):
        return None
    key = run["act"]
    rows = steps(key, run)
    cur = _here_index(run, key, rows)
    here = rows[cur] if cur is not None else None
    zone = (here or {}).get("zone") or run.get("zone") or "?"
    nxt = next((s for s in rows[(cur + 1 if cur is not None else 0):] if s["state"] == "todo"), None)
    gives = [short_gives(r) for r in rewards(key) if norm(r["zone"]) == norm(zone)
             and run["rewards"].get(r["id"]) not in ("got", "skip")]
    do = (here or {}).get("do") or ("Not in the guide yet" if run.get("unknown") else "")
    you, zl = char_level(), int(run.get("zone_level") or 0)
    lv = " · ".join(x for x in (f"You {you}" if you else "", f"zone {zl}" if zl else "") if x)
    return {"head": f"{act_name(key).upper()} · {zone.upper()}", "do": do, "gives": ", ".join(gives),
            "next": (nxt or {}).get("zone", ""), "levels": lv,
            "step": f"step {cur + 1} of {len(rows)}" if cur is not None and rows else "",
            "unknown": bool(run.get("unknown")), "in_town": bool((here or {}).get("town"))}


def line_text(run=None):
    d = line(run)
    if not d:
        return ""
    t = (d["do"] or "On you go").rstrip(" .")             # 2.124.1: no "Burrow., then" (feedback screenshot)
    if d["gives"]:
        t += f" ({d['gives']})"
    if d["next"]:
        nx = d["next"]
        t += f", then {nx[0].lower() + nx[1:] if nx.startswith('The ') else nx}"
    return t


def vendor_searches(act_key=None):
    """-> [(name, regex)] for this act (the guide pack's)."""
    act_key = act_key if act_key is not None else char().get("act")
    return [(v["name"], v["regex"]) for v in pack().get("vendor") or [] if v.get("act") in ("*", act_key)]


def splits(run=None):
    """-> [(act name, this run's secs or None, best or None, here?)] for every act in the pack."""
    run = run or char()
    best = cfg()["best"].get(SETTINGS.get("league") or "", {})
    return [(a.get("name"), run["secs"].get(a["key"]), best.get(a["key"]), run.get("act") == a["key"])
            for a in acts()]


def fmt(secs):
    if secs is None:
        return "-"
    s = int(secs)
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}"


def mark_optional(zone):
    c = cfg()
    if norm(zone) not in c["optional_zones"]:
        c["optional_zones"].append(norm(zone))
    save()


def set_note(zone, text):
    c = cfg()
    if text.strip():
        c["notes"][norm(zone)] = text.strip()[:200]
    else:
        c["notes"].pop(norm(zone), None)
    save()


def to_pool():
    """Learned zones not pooled yet -> [{act, zone, after, level}] (Community data sharing)."""
    c = cfg()
    out = []
    for key, rows in c["learned"].items():
        for lz in rows:
            k = f"{key}|{norm(lz['zone'])}"
            if k not in c["sent"]:
                out.append({"act": key, "zone": lz["zone"][:80], "after": (lz.get("after") or "")[:80],
                            "level": int(lz.get("level") or 0)})
    return out[:100]


def pooled(rows):
    c = cfg()
    for r in rows:
        k = f"{r['act']}|{norm(r['zone'])}"
        if k not in c["sent"]:
            c["sent"].append(k)
    c["sent"] = c["sent"][-500:]
    save()
