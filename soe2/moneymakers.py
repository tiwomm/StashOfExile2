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

# ---- what a strat IS: one category and one type inside it (2.28.0: "Mapping > Breach" - the strat is Breach farming,
# done while mapping). Fixed lists, so every guide uses the same words and the browser can group them.
TAXONOMY = {
    "Mapping": ("Breach", "Delirium", "Ritual", "Expedition", "Abyss", "Essence", "Strongbox", "Rogue Exiles",
                "Shrines", "Overseer", "Temple", "Juiced mapping", "Alch & go"),
    "Bossing": ("Pinnacle bosses", "Map bosses", "Simulacrum", "Trial of the Sekhemas", "Trial of Chaos"),
    "Crafting": ("Tablet crafting", "Waystone crafting", "Gear crafting", "Jewel crafting", "Flask & charm crafting"),
    "Trading": ("Currency flipping", "Bulk selling", "Buy low, sell high", "Services"),
    "Other": ("Vendor recipes", "Gold", "Other"),
}
CATEGORIES = tuple(TAXONOMY)
# ---- tags: everything else about it, in groups (checkboxes). The type above is the main thing; "Also uses" are the
# other mechanics in the same maps. Searching a tag finds both (Breach finds Mapping > Breach and strats that also
# use Breach).
TAG_GROUPS = {
    "Also uses": ("Abyss", "Breach", "Delirium", "Ritual", "Expedition", "Essence", "Strongbox", "Rogue Exiles",
                  "Shrines", "Overseer", "Temple"),
    "Farm type": ("City area farm", "Sacred Bloom farm", "Juiced maps", "Low-tier maps", "Campaign zones"),
    "Budget": ("League start", "Low budget", "Mid budget", "High budget"),
    "Play style": ("SSF friendly", "Trade league", "Party play", "Hardcore safe"),
}
ALL_TAGS = tuple(t for g in TAG_GROUPS.values() for t in g) + ("example",)
UNITS = ("div", "ex", "chaos")
# ---- effort: two words, picked from a list (no numbers to type)
THINKING = {1: ("Autopilot", "the same every map, no decisions"),
            2: ("Easy", "a few simple choices"),
            3: ("Moderate", "some planning, a few mechanics at once"),
            4: ("Hard", "constant decisions, crafting or trading know-how"),
            5: ("Big brain", "deep mechanics, market timing, risky calls")}
THOUGHTS = {k: f"{w} - {d}" for k, (w, d) in THINKING.items()}
CLICKS = {"Chill": "slow pace, few pickups - easy on the hands",
          "Steady": "normal mapping: loot, a few stashes",
          "Busy": "lots of looting, opening and selling",
          "Frantic": "non-stop clicking: bulk crafting, juiced loot explosions"}
CLICK_BANDS = ((300, "Chill"), (900, "Steady"), (1800, "Busy"), (10 ** 9, "Frantic"))

REQUIRED = ("id", "name", "author", "updated", "patch", "category", "type", "summary", "thoughts_per_click",
            "clicks_per_hour", "steps")
LISTS = ("tags", "requirements", "tablets", "waystones", "atlas", "craft_steps", "setup", "steps", "loot", "tips",
         "risks")
ORDER = ("id", "name", "author", "updated", "patch", "category", "type", "summary", "thoughts_per_click",
         "clicks_per_hour", "tags", "waystone_tiers", "est_cost", "est_profit",
         "requirements", "tablets", "waystones", "atlas", "craft_steps", "setup", "steps", "loot", "tips", "risks",
         "regex", "sources")
# Lucrative Strats: one-liners
ONE_ORDER = ("id", "text", "author", "updated", "category", "type", "tags")


def thinking_word(n):
    return THINKING.get(n, ("?", ""))[0]


def type_text(s):
    """"Mapping > Breach"."""
    return f"{s.get('category', '')} › {s['type']}" if s.get("type") else s.get("category", "")


def click_band(n):
    """A number (older files, typed text) -> its band word; a band word stays as it is."""
    if n in CLICKS:
        return n
    try:
        n = int(float(str(n).replace(",", "")))
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
    elif s.get("type") and s["type"] not in TAXONOMY[s["category"]]:
        out.append(f"type for {s['category']} must be one of {', '.join(TAXONOMY[s['category']])}")
    tpc = s.get("thoughts_per_click")
    if tpc is not None and (not isinstance(tpc, int) or not 1 <= tpc <= 5):
        out.append("thoughts_per_click must be 1-5 (" + ", ".join(f"{k} {w}" for k, (w, _d) in THINKING.items()) + ")")
    cph = s.get("clicks_per_hour")
    if cph is not None and cph not in CLICKS:
        out.append(f"clicks_per_hour must be one of {', '.join(CLICKS)}")
    if s.get("updated") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s["updated"])):
        out.append("updated must be YYYY-MM-DD")
    for k in LISTS:
        v = s.get(k)
        if v is not None and (not isinstance(v, list) or not all(isinstance(x, str) for x in v)):
            out.append(f"{k} must be a list of text lines")
    for k in ("est_profit", "est_cost"):
        out += [f"{k}: {p}" for p in _amount(s.get(k))]
    if isinstance(s.get("tags"), list):
        out += [f"tags: \"{x}\" is not in the tag list" for x in s["tags"] if x not in ALL_TAGS]
    wt = s.get("waystone_tiers")
    if wt is not None:
        lo, hi = (wt.get("min"), wt.get("max")) if isinstance(wt, dict) else (None, None)
        if not all(isinstance(x, int) and 1 <= x <= 16 for x in (lo, hi)) or lo > hi:
            out.append("waystone_tiers must be {\"min\": 1-16, \"max\": 1-16} with min <= max")
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


MINE_ONE = "my_lucrative.json"


def oneliners():
    out = [dict(o, origin="community") for o in shared().get("oneliners") or [] if not validate_one(o)]
    d = load_json(MINE_ONE, [])
    out += [dict(o, origin="mine") for o in (d if isinstance(d, list) else []) if isinstance(o, dict)]
    return out


def mine_one():
    d = load_json(MINE_ONE, [])
    return [o for o in d if isinstance(o, dict)] if isinstance(d, list) else []


def save_mine_one(items):
    save_json(MINE_ONE, [tidy_one(o) for o in items])


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
    return "new", len(d["strats"]) + len(d.get("oneliners") or [])


def validate_one(o):
    """A Lucrative Strats one-liner -> problems."""
    if not isinstance(o, dict):
        return ["must be an object"]
    out = [f"missing \"{k}\"" for k in ("id", "text", "author") if not o.get(k)]
    if o.get("id") and o["id"] != slug(o["id"]):
        out.append("id: lower-case letters, digits and dashes only")
    if len(str(o.get("text", ""))) > 300:
        out.append("text: keep it to one line (300 characters at most)")
    out += [f"tags: \"{x}\" is not in the tag list" for x in o.get("tags") or [] if x not in ALL_TAGS]
    if o.get("category") and o["category"] not in CATEGORIES:
        out.append("category is not in the list")
    elif o.get("type") and o["type"] not in TAXONOMY.get(o.get("category"), ()):
        out.append("type does not belong to that category")
    unknown = set(o) - set(ONE_ORDER) - {"origin"}
    if unknown:
        out.append("unknown field(s): " + ", ".join(sorted(unknown)))
    return out


def tidy_one(o):
    return {k: o[k] for k in ONE_ORDER if k in o and o[k] not in (None, "", [])}


def tiers_text(wt):
    if not wt:
        return ""
    return f"T{wt['min']}" if wt["min"] == wt["max"] else f"T{wt['min']}-{wt['max']}"


# ---------------------------------------------------------------- the .txt layout (opens in Notepad on any PC)
TXT_HEAD = "STASHOFEXILE2 STRAT 1"
TXT_FIELDS = (("name", "Name"), ("id", "ID (empty = made from the name)"), ("author", "Author"),
              ("updated", "Updated (YYYY-MM-DD)"), ("patch", "Game version"), ("summary", "Summary"),
              ("category", "Category"), ("type", "Type"), ("thoughts_per_click", "Thinking"),
              ("clicks_per_hour", "Clicks per hour"), ("waystone_tiers", "Waystone tiers (1-16, e.g. 14-16)"),
              ("est_cost", "Est. cost (div)"), ("est_profit", "Est. profit per hour (div, e.g. 5-10)"),
              ("regex", "Stash regex"), ("tags", "Tags"),
              ("requirements", "Requirements"), ("tablets", "Tablets"), ("waystones", "Waystones"),
              ("atlas", "Atlas / master setup"), ("craft_steps", "Craft steps"), ("setup", "Other setup"),
              ("steps", "Steps"), ("loot", "Loot to sell"), ("tips", "Tips"), ("risks", "Risks"),
              ("sources", "Sources (links)"))
_LABEL2KEY = {re.sub(r"\s*\(.*\)$", "", lab).lower(): k for k, lab in TXT_FIELDS}


def _num_range(text):
    t = str(text).replace(" ", "").replace(",", ".").lower().replace("div", "")
    if not t:
        return None
    lo, _, hi = t.partition("-")
    return float(lo), float(hi or lo)


def to_text(s=None):
    """A strat (or, with None, the blank template) in the plain-text layout."""
    s = s or {}
    out = [TXT_HEAD,
           "# Money Makers strat - the standard layout. Lines starting with # are help: leave them or delete them.",
           "# One field per line (\"Field: value\"). Lists: one \"- item\" line per item under the field.",
           "# Checkboxes: put an x in the box, [x], for each one that applies (one in each [ ] group of Type,",
           "# Thinking and Clicks per hour; as many Tags as fit).",
           "# Needed: Name, Author, Summary, Category + Type, Thinking, Clicks per hour, Steps.", ""]
    for key, label in TXT_FIELDS:
        v = s.get(key)
        if key == "category":
            continue                                         # (picked with its Type, below)
        if key == "type":
            out.append("Type (Category › Type):")
            for cat, types in TAXONOMY.items():
                for t in types:
                    on = s.get("category") == cat and v == t
                    out.append(f"[{'x' if on else ' '}] {cat} › {t}")
            out.append("")
        elif key == "thoughts_per_click":
            out.append(f"{label}:")
            out += [f"[{'x' if v == k else ' '}] {w} - {d}" for k, (w, d) in THINKING.items()]
            out.append("")
        elif key == "clicks_per_hour":
            out.append(f"{label}:")
            out += [f"[{'x' if v == w else ' '}] {w} - {d}" for w, d in CLICKS.items()]
            out.append("")
        elif key == "tags":
            for group, tags in TAG_GROUPS.items():
                out.append(f"Tags - {group}:")
                out += [f"[{'x' if t in (v or []) else ' '}] {t}" for t in tags]
                out.append("")
        elif key in LISTS or key == "sources":
            out.append(f"{label}:")
            items = [x.get("url", "") for x in v or []] if key == "sources" else v or []
            out += [f"- {x}" for x in items] or ["- "]
            out.append("")
        else:
            if key == "waystone_tiers":
                v = "" if not v else f"{v['min']}" if v["min"] == v["max"] else f"{v['min']}-{v['max']}"
            elif key == "est_cost":
                v = "" if not v else f"{v.get('amount', ''):g}"
            elif key == "est_profit":
                v = "" if not v else money_text(v).replace(" div", "")
            elif key == "updated" and not v:
                v = date.today().isoformat()
            out.append(f"{label}: {'' if v is None else v}")
    return "\n".join(out) + "\n"


_WORD2THINK = {w.lower(): k for k, (w, _d) in THINKING.items()}


def from_text(text):
    """The plain-text layout -> a strat (check it with validate)."""
    s, cur = {}, None
    for raw in str(text).replace("\r", "").split("\n"):
        line = raw.strip()
        if not line or line.startswith("#") or line == TXT_HEAD:
            continue
        m = re.match(r"^\[( |x|X)\]\s*(.+)$", line)
        if m and cur:
            if m.group(1).lower() != "x":
                continue
            opt = m.group(2).strip()
            word = opt.split(" - ")[0].strip()
            if cur == "type" and "›" in opt:
                s["category"], s["type"] = [x.strip() for x in opt.split("›", 1)]
            elif cur == "thoughts_per_click":
                s[cur] = _WORD2THINK.get(word.lower(), word)
            elif cur == "clicks_per_hour":
                s[cur] = word
            else:
                s.setdefault(cur, []).append(opt)
            continue
        if line.startswith("- ") or line == "-":
            item = line[1:].strip()
            if cur and item:
                s.setdefault(cur, []).append(item)
            continue
        m = re.match(r"^([^:]{2,60}):\s*(.*)$", line)
        if not m:
            continue
        label, val = re.sub(r"\s*\(.*\)$", "", m.group(1).strip()).lower(), m.group(2).strip()
        key = "tags" if label.startswith("tags") else _LABEL2KEY.get(label)
        cur = key
        if not key or not val:
            continue
        if key == "thoughts_per_click":
            s[key] = _WORD2THINK.get(val.split(" - ")[0].strip().lower()) or (int(val) if val.isdigit() else val)
        elif key == "clicks_per_hour":
            s[key] = click_band(val.split(" - ")[0].strip()) or val
        elif key == "type" and "›" in val:
            s["category"], s["type"] = [x.strip() for x in val.split("›", 1)]
        elif key == "waystone_tiers":
            try:
                lo, hi = _num_range(val.lower().replace("t", ""))
                s[key] = {"min": int(lo), "max": int(hi)}
            except (TypeError, ValueError):
                s[key] = val
        elif key == "est_cost":
            try:
                s[key] = {"amount": _num_range(val)[0], "unit": "div"}
            except (TypeError, ValueError):
                s[key] = val
        elif key == "est_profit":
            try:
                lo, hi = _num_range(val)
                s[key] = {"low": lo, "high": hi, "unit": "div"}
            except (TypeError, ValueError):
                s[key] = val
        elif key in LISTS or key == "sources":
            s.setdefault(key, []).append(val)
        else:
            s[key] = val
    if s.get("sources"):
        s["sources"] = [{"title": u, "url": u} for u in s["sources"] if u.startswith("http")]
    if s.get("name") and not s.get("id"):
        s["id"] = slug(s["name"])
    return {k: v for k, v in s.items() if v not in (None, "", [])}


def issue_link(s):
    """A GitHub issue (form strategy.yml) filled in with this strat, to share it with everyone."""
    lines = lambda k: "\n".join(s.get(k) or [])
    p = s.get("est_profit") or {}
    inv = s.get("est_cost") or {}
    q = {"template": "strategy.yml", "title": f"[Strat] {s.get('name', '')}",
         "name": s.get("name", ""), "type": type_text(s),
         "summary": s.get("summary", ""), "patch": s.get("patch", ""),
         "thoughts": thinking_word(s.get("thoughts_per_click")), "clicks": str(s.get("clicks_per_hour", "")),
         "profit": f"{p.get('low', '')}-{p.get('high', '')} {p.get('unit', 'div')}" if p else "",
         "investment": f"{inv.get('amount', '')} {inv.get('unit', 'div')}" if inv else "",
         "tiers": tiers_text(s.get("waystone_tiers")), "tags": ", ".join(s.get("tags") or []),
         "requirements": lines("requirements"),
         "tablets": lines("tablets"), "waystones": lines("waystones"), "atlas": lines("atlas"),
         "craft_steps": lines("craft_steps"), "setup": lines("setup"), "steps": lines("steps"),
         "loot": lines("loot"), "tips": lines("tips"), "risks": lines("risks"), "regex": s.get("regex", ""),
         "sources": "\n".join(x.get("url", "") for x in s.get("sources") or []),
         "json": "```json\n" + json.dumps(tidy(s), indent=2, ensure_ascii=False) + "\n```"}
    return ISSUE_URL + "?" + urllib.parse.urlencode({k: v for k, v in q.items() if v})


def one_issue_link(o):
    q = {"template": "lucrative.yml", "title": f"[Lucrative] {o.get('text', '')[:60]}", "text": o.get("text", ""),
         "type": type_text(o), "tags": ", ".join(o.get("tags") or [])}
    return ISSUE_URL + "?" + urllib.parse.urlencode({k: v for k, v in q.items() if v})


def new_strat(**kw):
    s = {"id": "", "name": "", "author": "me", "updated": date.today().isoformat(), "patch": "", "category": "Mapping",
         "type": "Breach", "summary": "", "thoughts_per_click": 2, "clicks_per_hour": "Steady", "steps": []}
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


# ---------------------------------------------------------------- Tablet Crafting quick reference
TABLET_TYPES = ("All", "Breach", "Delirium", "Ritual", "Expedition", "Abyss", "Overseer", "Temple")
# The crafting flow, as the guide gives it (shown on the Tablet Crafting tab, and used by tablet_advice).
TABLET_FLOW = (("White tablet", "Orb of Transmutation, then Orb of Augmentation: 2 mods."),
               ("2 bad mods", "Orb of Alchemy."),
               ("2 good mods", "Regal Orb, then Exalted Orb."),
               ("4 junk mods", "Don't sell it - keep it to reforge."),
               ("Good mods", "Price it (Ctrl+Alt+C, or the trade link next to the mod) and list it."))


def tablet_rarity(text):
    m = re.search(r"^Rarity:\s*(\w+)", str(text), re.M)
    return (m.group(1) if m else "").capitalize()


def tablet_advice(rarity, n_mods, n_good):
    """What to do next with a tablet, following TABLET_FLOW."""
    rarity = (rarity or "").capitalize()
    if rarity == "Normal" or (not rarity and n_mods == 0):
        return "White tablet: Orb of Transmutation, then Orb of Augmentation."
    if rarity == "Magic":
        if n_mods < 2:
            return "One mod so far: Orb of Augmentation for the second."
        if n_good >= 2:
            return "Both mods are good: Regal Orb, then Exalted Orb."
        if n_good == 1:
            return ("One good mod: your call - Regal + Exalt if that mod is worth a lot (see its price below), "
                    "otherwise treat it as 2 bad mods: Orb of Alchemy.")
        return "Both mods are bad: Orb of Alchemy."
    if rarity == "Rare":
        if n_good == 0 and n_mods >= 4:
            return "4 junk mods: don't sell it - keep it to reforge."
        if n_good == 0:
            return "No good mods yet: Exalted Orb for another, or keep it to reforge."
        if n_mods < 4:
            return f"{n_good} good mod{'s' if n_good > 1 else ''}: Exalted Orb to fill it, then price it."
        return f"{n_good} good mod{'s' if n_good > 1 else ''}: price it (Ctrl+Alt+C) and list it."
    return "Copy a tablet in game (Ctrl+C), then press Check my tablet."


def trade_link(league, sid=None, base=None):
    """A trade-site search for tablets with this mod (to check its price), cheapest first."""
    q = {"query": {"status": {"option": "online"}}, "sort": {"price": "asc"}}
    if base:
        q["query"]["type"] = base
    if sid:
        q["query"]["stats"] = [{"type": "and", "filters": [{"id": sid}]}]
    return (f"https://www.pathofexile.com/trade2/search/poe2/{urllib.parse.quote(league or 'Standard')}?q="
            + urllib.parse.quote(json.dumps(q, separators=(",", ":"))))


def stat_id(line):
    """A tablet mod line -> the trade site's stat id (from the trade data the app downloaded), or None."""
    import difflib
    from .mods import TEXT2SID, norm
    if not TEXT2SID:
        return None
    key = norm(line)
    for k in (key, re.sub(r"\s+in (your )?maps?$", "", key), key + " in your maps", key + " found in map"):
        if k in TEXT2SID:
            return TEXT2SID[k]
    close = difflib.get_close_matches(key, list(TEXT2SID), n=1, cutoff=0.92)
    return TEXT2SID[close[0]] if close else None
