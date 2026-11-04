"""2.86.0: Global leaderboards - your best times, from the game's log, and everyone's (opt-in).

Four boards:
  * Campaign - each act's split and the whole campaign (the Campaign Helper's act times; the total once every act of
    the guide pack has one).
  * Maps - fastest clear per map (time inside the map; maps, towers, unique maps, citadels).
  * Bosses & pinnacles - the Map library's pinnacle fights.
  * Trials - Trial of the Sekhemas, Trial of Chaos (and other trial areas the tracker learns); pinnacle fights such
    as Simulacrum of Delusion are on Bosses & pinnacles.
Mine is worked out on this PC. Everyone comes from the community board: with Community data sharing on, each
account's best per board / league / class is sent (its community name, never an account or character name). Times are
self-reported (from the log), so the board refuses impossible ones and reports / reviewers / admins can hide entries.
GGG ToS: reads Client.txt only; nothing is sent to the game."""
import re
import time

from .config import SETTINGS

CATS = (("campaign", "Campaign"), ("map", "Maps"), ("boss", "Bosses & pinnacles"), ("trial", "Trials"))
CAT_NAMES = dict(CATS)
TOTAL = "Whole campaign"
# the fastest a time can honestly be (seconds) - the board checks the same
FLOOR = {"campaign": 120, "map": 30, "boss": 10, "trial": 60}
CEIL = {"campaign": 48 * 3600, "map": 3 * 3600, "boss": 3600, "trial": 3 * 3600}
TRIAL = re.compile(r"trial|sekhema|simulacrum|sanctum|ultimatum|chaos", re.I)
SEND_EVERY = 15 * 60


def cat_of(name):
    """A map-run name -> "map", "boss" or "trial" (the Map library's kind; trials by name)."""
    from .maplib import library
    e = library().get(name) or {}
    kind = e.get("kind")
    ids = " ".join(e.get("ids") or [])
    if kind == "Pinnacle":                     # 2.87.0 (feedback): first - Simulacrum of Delusion is a pinnacle fight
        return "boss"
    if TRIAL.search(name or "") or TRIAL.search(ids):
        return "trial"
    return "map"


def classes():
    """Character -> class / ascendancy, as the log said at a level-up."""
    from . import focus as F
    return dict((F.cfg().get("state") or {}).get("classes") or {})


def learn_classes(path, max_bytes=64 * 1024 * 1024):
    """2.87.0 (feedback: "we don't have a way to read the class"): the game's log says it at every level-up
    ("ExampleWitch (Invoker) is now level 24"); the overlay only noted it from 2.86.0 on. Read the last part of Client.txt
    (64 MB at most) for each character's newest class. -> {character: class} (also saved). Thread-safe (no Tk)."""
    import os
    from .gamelog import parse
    from . import focus as F
    found = {}
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - max_bytes))
            for raw in f:
                if b"is now level" not in raw:
                    continue
                ev = parse(raw.decode("utf-8", "replace"))
                if ev and ev[0] == "level" and ev[2].get("cls"):
                    found[ev[2]["who"]] = ev[2]["cls"]
    except OSError:
        return {}
    if found:
        st = F.cfg().setdefault("state", {})
        cl = st.setdefault("classes", {})
        for who, c in found.items():
            cl.setdefault(who, c)
    return found


def best(entries):
    """[(cat, key, secs, ...)] -> only the fastest per (cat, key, league, class)."""
    out = {}
    for e in entries:
        k = (e["cat"], e["key"], e["league"], e.get("cls") or "")
        if k not in out or e["secs"] < out[k]["secs"]:
            out[k] = e
    return sorted(out.values(), key=lambda e: (e["cat"], e["key"], e["secs"]))


def map_entries(sessions, current=None, now=None):
    """Every counted run in the tracker's sessions -> entries {cat, key, secs, league, cls, char, level, deaths, at}.
    Sessions from before 2.86.0 don't know their league and are left out."""
    from .tracker import MIN_RUN_SECS
    cls = classes()
    pool = list(sessions) + ([current] if current is not None and current not in sessions else [])
    out = []
    for s in pool:
        league = getattr(s, "league", None)
        if not league:
            continue
        live = s.where.get("map") if (s.ended is None and s.where) else None
        for i, m in enumerate(s.maps):
            if live == i:
                continue                                   # still running: not a clear yet
            t = m.get("time")
            if not t or t < MIN_RUN_SECS:
                continue
            cat = cat_of(m["name"])
            if not FLOOR[cat] <= t <= CEIL[cat]:
                continue
            ch = m.get("char") or getattr(s, "char", "") or ""
            out.append({"cat": cat, "key": m["name"], "secs": round(float(t), 1), "league": league,
                        "cls": cls.get(ch, ""), "char": ch, "level": m.get("level") or 0,
                        "deaths": int(m.get("deaths") or 0), "at": int(m.get("first") or s.started)})
    return out


def campaign_entries():
    """Each character's act splits (and the whole campaign, once every act has a time)."""
    from . import campaign as CP
    cls = classes()
    acts = CP.acts()
    names = {a["key"]: a.get("name") or a["key"] for a in acts}
    out = []
    for ch, run in (CP.cfg().get("chars") or {}).items():
        league = run.get("league")
        if not league or not isinstance(run.get("secs"), dict):
            continue
        secs = {k: v for k, v in run["secs"].items() if isinstance(v, (int, float)) and v > 0}
        done = [k for k in secs if k != run.get("act")]      # the act you're in isn't finished
        for k in done:
            if FLOOR["campaign"] <= secs[k] <= CEIL["campaign"] and k in names:
                out.append({"cat": "campaign", "key": names[k], "secs": round(float(secs[k]), 1), "league": league,
                            "cls": cls.get(ch, ""), "char": ch, "level": 0, "deaths": 0, "at": int(time.time())})
        if acts and run.get("done") and all(a["key"] in secs for a in acts):
            tot = sum(secs[a["key"]] for a in acts)
            out.append({"cat": "campaign", "key": TOTAL, "secs": round(float(tot), 1), "league": league,
                        "cls": cls.get(ch, ""), "char": ch, "level": 0, "deaths": 0, "at": int(time.time())})
    return out


def mine(sessions, current=None):
    return map_entries(sessions, current) + campaign_entries()


def keys_of(entries, cat, league=None, cls=None):
    """[(key, my best secs, runs)] for one board - the list on the left."""
    agg = {}
    for e in entries:
        if e["cat"] != cat or (league and e["league"] != league) or (cls and e.get("cls") != cls):
            continue
        a = agg.setdefault(e["key"], [None, 0])
        a[0] = e["secs"] if a[0] is None else min(a[0], e["secs"])
        a[1] += 1
    order = {}
    if cat == "campaign":
        from . import campaign as CP
        order = {a.get("name") or a["key"]: i for i, a in enumerate(CP.acts())}
        order[TOTAL] = -1
    return sorted(((k, v[0], v[1]) for k, v in agg.items()), key=lambda r: (order.get(r[0], 999), r[0].lower()))


def payload(entries):
    """What goes to the board: the best per board / key / league / class, no character names."""
    from .privacy import is_private_league                 # 2.89.3: private leagues stay off the board; only the day
    out = []
    for e in best(entries):
        if is_private_league(e.get("league")):
            continue
        d = {k: e[k] for k in ("cat", "key", "secs", "league", "cls", "level", "deaths", "at")}
        d["at"] = int(d.get("at") or 0) // 86400 * 86400
        out.append(d)
    return out[:400]


def fmt(secs):
    if secs is None:
        return "-"
    s = int(round(secs))
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def sharing_on():
    from . import communitymods as CM
    return CM.sharing() and SETTINGS.get("lb_share", True)
