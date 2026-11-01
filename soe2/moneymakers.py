"""Money Makers (2.28.0): farming strats from the community, in one standard layout, and a simple run tracker.

Where strats come from (newest wins, by "revision"):
  1. moneymakers.json bundled with the app (built from the strats/ folder by tools/build_strats.py)
  2. the same file on GitHub main - fetched when the window opens (at most every 12 h) or with "Check for new strats",
     so a strat merged into the repo reaches everyone without a new release
  3. your own strats (my_strats.json in the data folder) - share one with "Share" (a GitHub issue form, filled in)

The layout (SCHEMA 1) is documented in strats/README.md; validate() is the one place that checks it (the build tool
and the app use the same function). Nothing here touches the game or the trade site."""
import json
import os
import re
import time
import urllib.parse
from datetime import date

from .config import APP_DIR, RESOURCE_DIR, P, load_json, save_json

SCHEMA = 1
FILE = "moneymakers.json"
MINE = "my_strats.json"
RUNS = "money_runs.json"
REPO = "tiwomm/StashOfExile2"
LIVE_URL = f"https://raw.githubusercontent.com/{REPO}/main/{FILE}"
ISSUE_URL = f"https://github.com/{REPO}/issues/new"
LIVE_EVERY = 12 * 3600

CATEGORIES = ("Mapping", "Breach", "Delirium", "Ritual", "Expedition", "Abyss", "Bossing", "Crafting", "Trading",
              "Other")
UNITS = ("div", "ex", "chaos")
# Thoughts per Click: how much thinking the strat asks for (fewer = easier).
THOUGHTS = {1: "Autopilot - the same every map, no decisions",
            2: "Light - a few simple choices",
            3: "Moderate - some planning, a few mechanics at once",
            4: "Heavy - constant decisions, crafting or trading know-how",
            5: "Big brain - deep mechanics, market timing, risky calls"}
# Clicks per hour: every click and key press an hour of it takes (looting, opening, trading, crafting).
CLICK_BANDS = ((300, "Chill"), (900, "Steady"), (1800, "Busy"), (10 ** 9, "Frantic"))

REQUIRED = ("id", "name", "author", "updated", "patch", "category", "summary", "thoughts_per_click",
            "clicks_per_hour", "steps")
LISTS = ("tags", "requirements", "setup", "steps", "loot", "tips", "risks")
ORDER = ("id", "name", "author", "updated", "patch", "category", "summary", "thoughts_per_click", "clicks_per_hour",
         "profit_per_hour", "investment", "league_start", "tags", "requirements", "setup", "steps", "loot", "tips",
         "risks", "regex", "sources")


def click_band(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return next(name for top, name in CLICK_BANDS if n < top)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:60] or "strat"


def _amount(d):
    """{"low", "high", "unit"} / {"amount", "unit"} -> problems (empty = fine)."""
    out = []
    if d is None:
        return out
    if not isinstance(d, dict):
        return ["must be an object"]
    if d.get("unit", "div") not in UNITS:
        out.append(f"unit must be one of {', '.join(UNITS)}")
    for k in ("low", "high", "amount"):
        if k in d and d[k] is not None and not isinstance(d[k], (int, float)):
            out.append(f"{k} must be a number")
    if isinstance(d.get("low"), (int, float)) and isinstance(d.get("high"), (int, float)) and d["low"] > d["high"]:
        out.append("low is bigger than high")
    return out


def validate(s):
    """-> list of problems with one strat (empty = it follows the layout)."""
    if not isinstance(s, dict):
        return ["a strat must be an object"]
    out = [f"missing \"{k}\"" for k in REQUIRED if s.get(k) in (None, "", [])]
    if s.get("id") and s["id"] != slug(s["id"]):
        out.append("id: lower-case letters, digits and dashes only")
    if s.get("category") and s["category"] not in CATEGORIES:
        out.append(f"category must be one of {', '.join(CATEGORIES)}")
    tpc = s.get("thoughts_per_click")
    if tpc is not None and (not isinstance(tpc, int) or not 1 <= tpc <= 5):
        out.append("thoughts_per_click must be a whole number 1-5")
    cph = s.get("clicks_per_hour")
    if cph is not None and (not isinstance(cph, int) or cph < 0):
        out.append("clicks_per_hour must be a whole number")
    if s.get("updated") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s["updated"])):
        out.append("updated must be YYYY-MM-DD")
    for k in LISTS:
        v = s.get(k)
        if v is not None and (not isinstance(v, list) or not all(isinstance(x, str) for x in v)):
            out.append(f"{k} must be a list of text lines")
    for k in ("profit_per_hour", "investment"):
        out += [f"{k}: {p}" for p in _amount(s.get(k))]
    src = s.get("sources")
    if src is not None and (not isinstance(src, list) or not all(isinstance(x, dict) and x.get("url") for x in src)):
        out.append("sources must be a list of {\"title\", \"url\"}")
    unknown = set(s) - set(ORDER) - {"origin"}
    if unknown:
        out.append("unknown field(s): " + ", ".join(sorted(unknown)))
    return out


def tidy(s):
    """The fields in the standard order (for files people read and diff)."""
    return {k: s[k] for k in ORDER if k in s and s[k] not in (None, "", [])}


def money_text(d, per=""):
    if not d:
        return "?"
    unit = d.get("unit", "div")
    if "amount" in d:
        return f"{d['amount']:g} {unit}" if isinstance(d.get("amount"), (int, float)) else "?"
    lo, hi = d.get("low"), d.get("high")
    if lo is None and hi is None:
        return "?"
    if lo is None or hi is None or lo == hi:
        return f"{(lo if hi is None else hi):g} {unit}{per}"
    return f"{lo:g}-{hi:g} {unit}{per}"


# ---------------------------------------------------------------- the strats
def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) and isinstance(d.get("strats"), list) else None
    except Exception:
        return None


def shared():
    """-> the newest copy of the community file (bundled or fetched), or an empty one."""
    best = None
    for path in (P(FILE), os.path.join(RESOURCE_DIR, FILE), os.path.join(APP_DIR, FILE)):
        d = _read(path)
        if d and d.get("schema", 1) <= SCHEMA and (best is None or d.get("revision", 0) > best.get("revision", 0)):
            best = d
    return best or {"schema": SCHEMA, "revision": 0, "strats": []}


def mine():
    d = load_json(MINE, [])
    return [s for s in d if isinstance(s, dict)] if isinstance(d, list) else []


def save_mine(items):
    save_json(MINE, [tidy(s) for s in items])


def all_strats():
    out = []
    for s in shared()["strats"]:
        if not validate(s):
            out.append(dict(s, origin="example" if "example" in (s.get("tags") or []) else "community"))
    for s in mine():
        out.append(dict(s, origin="mine"))
    return out


def fetch_live(get=None, force=False, now=None):
    """Fetch the community file from GitHub. -> ("new", n strats) / ("same", n) / ("skip", "") / ("error", why).
    One small public download; nothing is sent about you."""
    from .config import SETTINGS
    now = now or time.time()
    if not force and now - float(SETTINGS.get("mm_checked", 0) or 0) < LIVE_EVERY:
        return "skip", ""
    if get is None:
        import requests
        get = requests.get
    try:
        r = get(LIVE_URL, headers={"User-Agent": "StashOfExile2-moneymakers"}, timeout=15)
        if r.status_code != 200:
            return "error", f"GitHub answered {r.status_code}."
        d = r.json()
    except Exception as e:
        return "error", f"Could not reach GitHub ({e.__class__.__name__})."
    SETTINGS["mm_checked"] = now
    if not isinstance(d, dict) or not isinstance(d.get("strats"), list):
        return "error", "The strats file on GitHub could not be read."
    if d.get("schema", 1) > SCHEMA:
        return "error", "New strats need a newer version of the app - update it (Settings > About)."
    have = shared()
    if d.get("revision", 0) <= have.get("revision", 0):
        return "same", len(have["strats"])
    save_json(FILE, d)
    return "new", len(d["strats"])


def issue_link(s):
    """A GitHub issue (form strategy.yml) filled in with this strat, to share it with everyone."""
    lines = lambda k: "\n".join(s.get(k) or [])
    p = s.get("profit_per_hour") or {}
    inv = s.get("investment") or {}
    q = {"template": "strategy.yml", "title": f"[Strat] {s.get('name', '')}",
         "name": s.get("name", ""), "category": s.get("category", ""), "summary": s.get("summary", ""),
         "patch": s.get("patch", ""), "thoughts": str(s.get("thoughts_per_click", "")),
         "clicks": str(s.get("clicks_per_hour", "")),
         "profit": f"{p.get('low', '')}-{p.get('high', '')} {p.get('unit', 'div')}" if p else "",
         "investment": f"{inv.get('amount', '')} {inv.get('unit', 'div')}" if inv else "",
         "requirements": lines("requirements"), "setup": lines("setup"), "steps": lines("steps"),
         "loot": lines("loot"), "tips": lines("tips"), "risks": lines("risks"), "regex": s.get("regex", ""),
         "sources": "\n".join(x.get("url", "") for x in s.get("sources") or []),
         "json": "```json\n" + json.dumps(tidy(s), indent=2, ensure_ascii=False) + "\n```"}
    return ISSUE_URL + "?" + urllib.parse.urlencode({k: v for k, v in q.items() if v})


def new_strat(**kw):
    s = {"id": "", "name": "", "author": "me", "updated": date.today().isoformat(), "patch": "", "category": "Mapping",
         "summary": "", "thoughts_per_click": 2, "clicks_per_hour": 600, "steps": []}
    s.update(kw)
    s["id"] = slug(s["id"] or ("my-" + s["name"]))
    return s


# ---------------------------------------------------------------- the run tracker
def runs():
    d = load_json(RUNS, [])
    return [r for r in d if isinstance(r, dict) and "start" in r and "end" in r] if isinstance(d, list) else []


def save_runs(items):
    save_json(RUNS, items[-2000:])


def stats(items, strat=None):
    """-> {"runs", "avg_secs", "per_hour", "profit", "profit_known", "profit_per_hour"} for one strat (or all)."""
    rs = [r for r in items if strat is None or r.get("strat") == strat]
    secs = sum(max(0.0, r["end"] - r["start"]) for r in rs)
    priced = [r for r in rs if isinstance(r.get("profit"), (int, float))]
    psecs = sum(max(0.0, r["end"] - r["start"]) for r in priced)
    profit = sum(r["profit"] for r in priced)
    return {"runs": len(rs), "secs": secs, "avg_secs": secs / len(rs) if rs else 0,
            "per_hour": len(rs) * 3600 / secs if secs else 0, "profit": profit, "profit_known": len(priced),
            "profit_per_hour": profit * 3600 / psecs if psecs else None}
