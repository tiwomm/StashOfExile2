"""League Focus (2.73.0): a set-and-forget game plan for the league - goals by phase, a stockpile to buy while it's
cheap, the farms you planned, a build lock - and (2.73.1) pokes over the game that remind you of it. Built for players
who get sidetracked (ADHD-friendly): everything is optional, quiet by default, and says why it showed up.

Stored in SETTINGS["focus"]. Reads only what the app already knows - the game's log (Client.txt: zones, levels),
poe.ninja prices, your Wealth counts and Strat Tracker numbers. Nothing touches the game.

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
    "lock": {"on": False, "character": "", "build": "", "until": "I reach maps and have 10 div"},
    "pokes": {"per_hour": 2, "checkin_min": 45, "snooze_min": 60, "town_only": True, "session_only": True,
              "milestones": True, "prices": True, "quiet_on": False, "quiet": [23, 8], "tone": "Gentle",
              "sound": True, "why": True, "quieter": True, "windows": False},
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
    """(have, target) in divines for a goal with a target, or None. worth: your net worth (Wealth)."""
    if not g or not g.get("target_div") or worth is None:
        return None
    return max(0.0, float(worth)), float(g["target_div"])


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
    row = {"name": name.strip(), "goal": int(goal_qty or 0), "under": under, "paid": None}
    cfg()["stockpile"].append(row)
    save()
    return row


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
