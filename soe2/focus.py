"""League Focus (2.73.0): a set-and-forget game plan for the league - goals by phase, a stockpile to buy while it's
cheap, the farms you planned, a build lock - and (2.73.1) pokes over the game that remind you of it. Built for players
who get sidetracked (ADHD-friendly): everything is optional, quiet by default, and says why it showed up.

Stored in SETTINGS["focus"]. Reads only what the app already knows - the game's log (Client.txt: zones, levels),
poe.ninja prices; counts and progress are what you type (2.73.2: not Wealth - it doesn't track live and is a beta).
Nothing touches the game.

Phases: "start" (league start / campaign), "maps" (once you reach maps), "long" (long term). The current phase moves
to "maps" by itself the first time the log shows you in a waystone map (2.73.1), or by hand."""
import copy
import time
import uuid

from .config import SETTINGS, save_json

PHASES = (("start", "League start"), ("maps", "When I reach maps"), ("long", "Long term"))
TRIGGERS = (("town", "in town or my hideout"), ("phase", "when I reach this phase"), ("weekly", "once a week"),
            ("never", "never - just keep it on the plan"))
TONES = ("Gentle", "Firm", "Drill sergeant")
DEFAULTS = {
    "on": False,                    # the whole feature (Overlay › Options › On the overlay, and the Focus switch)
    "line": True,                   # the focus line on the overlay (I)
    "phase": "start",
    "now": None,                    # the goal shown on the focus line (None: the first open one of this phase)
    "goals": [],                    # [{id, text, phase, done, trigger, target_div, created, snooze, stopped}]
    "stockpile": [],                # [{name, goal, under, paid}]
    "farms": [],                    # [{strat, name, until}]
    "supplies": [],                 # 2.73.3: [{id, name, rule: maps|minutes, every, at_maps, at_secs, snooze}]
    "lock": {"on": False, "character": "", "build": "", "until": "I reach maps and have 10 div"},
    "pokes": {"per_hour": 2, "checkin_min": 45, "snooze_min": 60, "town_only": True, "session_only": True,
              "milestones": True, "prices": True, "quiet_on": False, "quiet": [23, 8], "tone": "Gentle",
              "sound": True, "why": True, "quieter": True, "windows": False,
              "supplies": True},           # 2.73.3: map supply pokes (their own switch)
    "history": [],
}


def cfg():
    f = SETTINGS.setdefault("focus", {})
    for k, v in DEFAULTS.items():
        f.setdefault(k, copy.deepcopy(v))
    for k, v in DEFAULTS["pokes"].items():
        f["pokes"].setdefault(k, v)
    for k, v in DEFAULTS["lock"].items():
        f["lock"].setdefault(k, v)
    return f


def save():
    save_json("settings.json", SETTINGS)


def phase_name(key):
    return dict(PHASES).get(key, key)


# ---------------------------------------------------------------- goals
def add_goal(text, phase="start", trigger="town", target_div=None):
    g = {"id": uuid.uuid4().hex[:10], "text": text.strip(), "phase": phase if phase in dict(PHASES) else "start",
         "done": False, "trigger": trigger if trigger in dict(TRIGGERS) else "town", "target_div": target_div,
         "created": time.time(), "snooze": 0, "stopped": False}
    cfg()["goals"].append(g)
    save()
    return g


def goal(gid):
    return next((g for g in cfg()["goals"] if g["id"] == gid), None)


def remove_goal(gid):
    f = cfg()
    f["goals"] = [g for g in f["goals"] if g["id"] != gid]
    if f.get("now") == gid:
        f["now"] = None
    save()


def set_done(gid, done=True):
    g = goal(gid)
    if g:
        g["done"] = bool(done)
        f = cfg()
        if done and f.get("now") == gid:
            f["now"] = None
        save()
    return g


def goals_of(phase):
    return [g for g in cfg()["goals"] if g["phase"] == phase]


def current():
    """The goal on the focus line: the one you picked, else the first open one of the current phase (then the
    phases after it)."""
    f = cfg()
    g = goal(f.get("now")) if f.get("now") else None
    if g and not g["done"]:
        return g
    order = [p for p, _n in PHASES]
    start = order.index(f["phase"]) if f["phase"] in order else 0
    for p in order[start:]:
        for g in goals_of(p):
            if not g["done"]:
                return g
    return None


def progress(g, worth=None):
    """(have, target) for a goal with a target, or None. 2.73.2: "have" is what you type on the goal (Wealth isn't
    used: it doesn't track live). worth is ignored (kept for older callers)."""
    if not g or not g.get("target_div"):
        return None
    return max(0.0, float(g.get("have") or 0)), float(g["target_div"])


def set_have(gid, have):
    g = goal(gid)
    if g is not None:
        g["have"] = max(0.0, float(have or 0))
        save()
    return g


def set_phase(phase):
    f = cfg()
    if phase in dict(PHASES) and f["phase"] != phase:
        f["phase"] = phase
        f["now"] = None
        save()
        return True
    return False


# ---------------------------------------------------------------- stockpile, farms, build lock
def add_stock(name, goal_qty=0, under=None):
    row = {"name": name.strip(), "goal": int(goal_qty or 0), "under": under, "paid": None, "have": 0}
    cfg()["stockpile"].append(row)
    save()
    return row


def set_stock_have(name, have):
    row = next((r for r in cfg()["stockpile"] if r["name"] == name), None)
    if row is not None:
        row["have"] = max(0, int(have or 0))
        save()
    return row


def stock_have(name):
    row = next((r for r in cfg()["stockpile"] if r["name"] == name), None)
    return None if row is None else int(row.get("have") or 0)


def remove_stock(name):
    f = cfg()
    f["stockpile"] = [r for r in f["stockpile"] if r["name"] != name]
    save()


def stock_status(row, have=None, each=None):
    """-> "cheap" (under your price), "ok", "done" (you have enough) or "?" (no price)."""
    if have is not None and row.get("goal") and have >= row["goal"]:
        return "done"
    if each is None:
        return "?"
    under = row.get("under")
    return "cheap" if under is not None and each <= float(under) else "ok"


def add_farm(strat_id, name, until=""):
    f = cfg()
    if any(x["strat"] == strat_id for x in f["farms"]):
        return None
    row = {"strat": strat_id, "name": name, "until": until}
    f["farms"].append(row)
    save()
    return row


def move_farm(i, step):
    farms = cfg()["farms"]
    j = i + step
    if 0 <= i < len(farms) and 0 <= j < len(farms):
        farms[i], farms[j] = farms[j], farms[i]
        save()
        return True
    return False


def remove_farm(i):
    farms = cfg()["farms"]
    if 0 <= i < len(farms):
        del farms[i]
        save()


def line_text(worth=None):
    """The overlay's focus line: "NOW  <goal>" (+ progress), or "" when there is nothing to show."""
    f = cfg()
    if not (f["on"] and f["line"]):
        return "", None
    g = current()
    if not g:
        return "", None
    p = progress(g, worth)
    return g["text"], (p[0] / p[1] if p and p[1] else None)


# ---------------------------------------------------------------- 2.73.3: map supplies
# Things you use up in maps (wisdom scrolls, omens, a currency) and when to refill them: every N maps, or every N
# minutes spent in maps. Both come from the game's log (a new waystone map = one map; time from entering a map to
# leaving it). Not from Wealth: it doesn't track live.
SUPPLY_RULES = (("maps", "maps"), ("minutes", "min in maps"))
SUPPLY_PRESETS = ("Scroll of Wisdom", "Omen of Amelioration", "Exalted Orb", "Regal Orb", "Chaos Orb",
                  "Orb of Alchemy", "Distilled Emotion", "Simulacrum Splinter")


def add_supply(name, rule="maps", every=10):
    st = state()
    row = {"id": uuid.uuid4().hex[:10], "name": name.strip(), "rule": rule if rule in dict(SUPPLY_RULES) else "maps",
           "every": max(1, int(every or 1)), "at_maps": st["maps"], "at_secs": st["map_secs"], "snooze": 0}
    cfg()["supplies"].append(row)
    save()
    return row


def supply(sid):
    return next((r for r in cfg()["supplies"] if r["id"] == sid), None)


def remove_supply(sid):
    f = cfg()
    f["supplies"] = [r for r in f["supplies"] if r["id"] != sid]
    save()


def set_supply(sid, rule=None, every=None):
    r = supply(sid)
    if r is not None:
        if rule in dict(SUPPLY_RULES):
            r["rule"] = rule
        if every is not None:
            r["every"] = max(1, int(every))
        save()
    return r


def supply_used(row):
    """-> (used so far, every) in the row's unit: maps run, or whole minutes in maps, since the last refill."""
    st = state()
    if row["rule"] == "minutes":
        return int((st["map_secs"] - row.get("at_secs", 0)) // 60), row["every"]
    return st["maps"] - row.get("at_maps", 0), row["every"]


def refilled(row):
    st = state()
    row["at_maps"], row["at_secs"], row["snooze"] = st["maps"], st["map_secs"], 0


def supplies_due(now=None):
    now = now or time.time()
    out = []
    for r in cfg()["supplies"]:
        used, every = supply_used(r)
        if used >= every and (r.get("snooze") or 0) <= now:
            out.append(r)
    return out


# ---------------------------------------------------------------- 2.73.1: pokes
# What each poke is, in the order they win when several are due. "urgent" ones (milestones, the build-lock guard)
# don't count toward the per-hour limit; every poke still waits for town / hideout when "Only in town" is on.
KINDS = {"milestone": "urgent", "guard": "urgent", "price": "normal", "supply": "normal", "checkin": "normal",
         "nudge": "normal"}
TONE_WORDS = {"Gentle": ("A nudge from your plan", "Still on plan?"),
              "Firm": ("Your plan says", "On plan? Be honest."),
              "Drill sergeant": ("Eyes on the plan, exile", "Report: on plan?")}


def state():
    """The pokes' own bookkeeping (kept with the plan)."""
    f = cfg()
    st = f.setdefault("state", {})
    st.setdefault("pending", [])           # urgent pokes waiting for town: [{kind, ...}]
    st.setdefault("sent", [])              # timestamps of normal pokes (per-hour limit)
    st.setdefault("chars", [])             # characters the log has shown
    st.setdefault("reached_maps", False)
    st.setdefault("price_day", {})         # stockpile name -> the day it was poked
    st.setdefault("notoday", {})           # goal id -> the day you said "Not today"
    st.setdefault("notoday_streak", 0)
    st.setdefault("played", 0.0)           # seconds of play since the last check-in
    st.setdefault("checkin_snooze", 0.0)
    st.setdefault("maps", 0)               # 2.73.3: waystone maps the log has shown
    st.setdefault("map_secs", 0.0)         # seconds spent in maps
    st.setdefault("map_in", None)          # when the current map was entered
    st.setdefault("map_seed", None)
    return st


def today(now=None):
    return time.strftime("%Y-%m-%d", time.localtime(now or time.time()))


def log_event(kind, data, area_kind=None, now=None):
    """A game-log event -> may queue an urgent poke. area_kind: the tracker's 'map' / 'town' / 'hideout' / 'other'."""
    f, st = cfg(), state()
    if not f["on"]:
        return None
    now = now or time.time()
    if kind == "area":                                     # 2.73.3: count maps and time in maps (map supplies)
        if st["map_in"] is not None:
            st["map_secs"] += max(0.0, min(now - st["map_in"], 3 * 3600))
            st["map_in"] = None
        if area_kind == "map":
            st["map_in"] = now
            key = f"{data.get('area')}|{data.get('seed')}"
            if key != st["map_seed"]:                      # back into the same map (a portal) isn't a new one
                st["maps"] += 1
                st["map_seed"] = key
    if kind == "area" and area_kind == "map" and not st["reached_maps"]:
        st["reached_maps"] = True
        moved = set_phase("maps")
        if f["pokes"].get("milestones") and (moved or goals_of("maps")):
            st["pending"].append({"kind": "milestone", "id": "maps", "at": now})
        save()
        return "milestone"
    if kind == "area":
        save()
    if kind == "level":
        who, lvl = data.get("who", ""), int(data.get("level") or 0)
        known = who in st["chars"]
        if not known:
            st["chars"] = (st["chars"] + [who])[-30:]
        lk = f["lock"]
        mine = (lk.get("character") or "").strip().lower()
        if not known and lvl <= 2 and lk.get("on") and mine and who.lower() != mine:
            st["pending"].append({"kind": "guard", "who": who, "cls": data.get("cls", ""), "at": now})
            save()
            return "guard"
        save()
    return None


def _quiet(pk, now):
    if not pk.get("quiet_on"):
        return False
    a, b = (pk.get("quiet") or [23, 8])[:2]
    h = time.localtime(now).tm_hour
    return (a <= h or h < b) if a > b else (a <= h < b)


def _room(pk, st, now):
    per = int(pk.get("per_hour") or 0)
    if pk.get("quieter") and st["notoday_streak"] >= 3:
        per = per // 2
    st["sent"] = [t for t in st["sent"] if now - t < 3600]
    return per > 0 and len(st["sent"]) < per


def due(now=None, in_town=True, session=True, played=0.0, prices=None, have=None):
    """The poke to show now, or None. prices(name) -> divines each or None; have(name) -> count or None.
    played: seconds of play since the last call (for the check-in)."""
    f, st = cfg(), state()
    if not f["on"]:
        return None
    now = now or time.time()
    pk = f["pokes"]
    st["played"] += max(0.0, played)
    if pk.get("session_only") and not session:
        return None
    if _quiet(pk, now) or (pk.get("town_only") and not in_town):
        return None
    if st["pending"]:
        return st["pending"].pop(0)
    if not _room(pk, st, now):
        return None
    if pk.get("prices") and prices:
        for row in f["stockpile"]:
            if st["price_day"].get(row["name"]) == today(now):
                continue
            each = prices(row["name"])
            h = have(row["name"]) if have else None
            if stock_status(row, h, each) == "cheap":
                st["price_day"][row["name"]] = today(now)
                return {"kind": "price", "name": row["name"], "each": each, "have": h, "goal": row.get("goal"),
                        "under": row.get("under")}
    if pk.get("supplies", True) and in_town:               # 2.73.3: always between maps, never in one
        rows = supplies_due(now)
        if rows:
            return {"kind": "supply", "ids": [r["id"] for r in rows]}
    cm = int(pk.get("checkin_min") or 0)
    if cm and st["played"] >= cm * 60 and now >= st["checkin_snooze"] and current():
        st["played"] = 0.0
        return {"kind": "checkin", "goal": current()["id"]}
    for g in _nudgeable(now):
        g["poked"] = now
        return {"kind": "nudge", "goal": g["id"]}
    return None


def _nudgeable(now):
    st = state()
    out = []
    for g in cfg()["goals"]:
        if g["done"] or g.get("stopped") or (g.get("snooze") or 0) > now or st["notoday"].get(g["id"]) == today(now):
            continue
        last = g.get("poked") or 0
        if g["trigger"] == "town" and now - last >= 3 * 3600:
            out.append(g)
        elif g["trigger"] == "weekly" and now - last >= 7 * 86400:
            out.append(g)
    return sorted(out, key=lambda g: g.get("poked") or 0)


def sent(poke, now=None):
    """A poke was shown: count it (urgent ones don't) and keep it in the history."""
    st, f = state(), cfg()
    now = now or time.time()
    if KINDS.get(poke["kind"]) == "normal":
        st["sent"].append(now)
    f["history"] = (f["history"] + [{"ts": now, "kind": poke["kind"], "text": poke_text(poke)[1][:200],
                                     "answer": None}])[-60:]
    save()


def answer(poke, what, now=None):
    """Your answer to a poke -> what it changes. what: done / snooze / nottoday / stop / unlock / ontrack /
    sidetracked / break / ok."""
    st, f = state(), cfg()
    now = now or time.time()
    g = goal(poke.get("goal")) if poke.get("goal") else None
    if what == "done" and g:
        set_done(g["id"])
    elif what == "snooze" and g:
        g["snooze"] = now + int(f["pokes"].get("snooze_min") or 60) * 60
    elif what == "nottoday" and g:
        st["notoday"][g["id"]] = today(now)
        st["notoday_streak"] += 1
    elif what == "stop" and g:
        g["stopped"] = True
    elif what == "unlock":
        f["lock"]["on"] = False
    elif what in ("refilled", "skip") and poke["kind"] == "supply":   # 2.73.3: count again from now
        for sid in poke.get("ids") or []:
            r = supply(sid)
            if r is not None:
                refilled(r)
    elif what == "snooze" and poke["kind"] == "supply":
        for sid in poke.get("ids") or []:
            r = supply(sid)
            if r is not None:
                r["snooze"] = now + int(f["pokes"].get("snooze_min") or 60) * 60
    elif what == "break":
        st["checkin_snooze"] = now + 30 * 60
    if what not in ("nottoday",):
        st["notoday_streak"] = 0
    if f["history"] and f["history"][-1]["kind"] == poke["kind"] and f["history"][-1]["answer"] is None:
        f["history"][-1]["answer"] = what
    save()


def poke_text(poke):
    """-> (title, text, why, [(answer, label)]) for a poke, in the tone you picked."""
    f = cfg()
    tone = f["pokes"].get("tone", "Gentle")
    head, ask = TONE_WORDS.get(tone, TONE_WORDS["Gentle"])
    k = poke["kind"]
    if k == "nudge":
        g = goal(poke["goal"]) or {"text": "?", "created": time.time(), "phase": "start", "trigger": "town"}
        when = time.strftime("%b %d", time.localtime(g.get("created") or time.time()))
        return (head.upper(), f"You set this on {when}:\n\"{g['text']}\"",
                ("Why now: a weekly reminder you asked for" if g["trigger"] == "weekly" else
                 "Why now: you're in town, where you asked to be reminded") + f" ({phase_name(g['phase'])} goal).",
                [("done", "Done"), ("snooze", f"Snooze {int(f['pokes'].get('snooze_min') or 60)} min"),
                 ("nottoday", "Not today"), ("stop", "Stop this one")])
    if k == "milestone":
        lines = [g["text"] for g in goals_of("maps") if not g["done"]][:5]
        farms = [x["name"] for x in f["farms"]][:2]
        body = "Your first waystone map - here's what you planned for this moment:"
        body += "".join(f"\n{i}. {t}" for i, t in enumerate(lines, 1)) or "\n(no goals for maps yet)"
        if farms:
            body += "\nFarm plan: " + ", then ".join(farms)
        return ("YOU REACHED MAPS", body, "Why now: the log shows you in your first waystone map.",
                [("plan", "Open Game Plan"), ("ok", "Got it")])
    if k == "price":
        under = poke.get("under")
        body = f"{poke['name']} is {poke['each']:.3g} div" + (f" (you buy under {under:g})." if under is not None else ".")
        if poke.get("goal"):
            body += f"\nYou have {poke.get('have') if poke.get('have') is not None else '?'} of {poke['goal']}."
        return ("CHEAP NOW - YOUR STOCKPILE", body, "Why now: poe.ninja's price is under the one you set.",
                [("exchange", "Open the exchange"), ("ok", "Snooze today")])
    if k == "supply":
        rows = [r for r in (supply(i) for i in poke.get("ids") or []) if r]
        lines = []
        for r in rows:
            used, every = supply_used(r)
            unit = "maps" if r["rule"] == "maps" else "min in maps"
            lines.append(f"{r['name']} - {used} {unit} since you last refilled (you said every {every}).")
        body = "Time to restock before the next map:\n" + "\n".join(lines or ["(removed)"])
        return ("REFILL YOUR MAP SUPPLIES", body, "Why now: you're between maps and a refill rule you set is up.",
                [("refilled", "Refilled"), ("snooze", f"Snooze {int(f['pokes'].get('snooze_min') or 60)} min"),
                 ("skip", "Skip this time")])
    if k == "guard":
        lk = f["lock"]
        body = (f"The log shows a new level 1 character ({poke.get('who', '?')}).\nYour build lock says: finish "
                f"{lk.get('build') or 'your starter'} until {lk.get('until') or 'you reach your goal'}.")
        return ("NEW CHARACTER?", body, "Why now: your build lock is on.",
                [("plan", "Back to the plan"), ("unlock", "I'm sure - unlock")])
    if k == "checkin":
        g = goal(poke.get("goal"))
        body = ask + (f"\nNow: {g['text']}" if g else "")
        hist = [h for h in f["history"] if h["kind"] == "checkin" and h.get("answer")][-5:]
        if hist:
            body += f"\nOn plan {sum(1 for h in hist if h['answer'] == 'ontrack')} of your last {len(hist)} check-ins."
        return ("CHECK-IN", body, f"Why now: {int(f['pokes'].get('checkin_min') or 45)} min of play since the last one.",
                [("ontrack", "On track"), ("sidetracked", "Got sidetracked"), ("break", "Taking a break")])
    return ("", "", "", [("ok", "OK")])
