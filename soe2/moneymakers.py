"""Money Makers (2.28.0): farming strats from the community, in one standard layout, and a simple run tracker.

Where strats come from (newest wins, by "revision"):
  1. moneymakers.json bundled with the app (built from the strats/ folder by tools/build_strats.py)
  2. the same file on GitHub main - fetched when the window opens (at most every 12 h) or with "Check for new strats",
     so a strat merged into the repo reaches everyone without a new release
  3. your own strats (my_strats.json in the data folder)
  4. 2.30.0: the Community board (board.py <-> board/, a Cloudflare Worker): players post, upvote and report;
     admins promote the best posts, which then join the Official list

The layout (SCHEMA 1) is documented in strats/README.md; validate() is the one place that checks it (the build tool
and the app use the same function). Nothing here touches the game or the trade site."""
import json
import os
import re
import time
import urllib.parse
from datetime import date

from .config import APP_DIR, RESOURCE_DIR, P, load_json, save_json

SCHEMA = 2          # 2.29.0: category + type, tag groups, effort words (2.28.0 wrote 1 - migrate() converts it)
FILE = "moneymakers.json"
MINE = "my_strats.json"
RUNS = "money_runs.json"
REPO = "tiwomm/StashOfExile2"
LIVE_URL = f"https://raw.githubusercontent.com/{REPO}/main/{FILE}"
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
# 2.78.0: what a strat farms in the endgame - pinnacles, bosses, map content - tags too (one tag system), ticked in the
# Strat Tracker's Atlas step and filtered by in the Content row. The lists ship in the shared strats file
# (strats/content.json -> moneymakers.json "content"), so a new league's content arrives without an app update.
CONTENT = {
    "Pinnacle & bosses": ("Arbiter of Ash", "Xesht (Breach)", "King in the Mists / Bodach", "Olroth (Expedition)",
                          "Simulacrum", "Vessel of Kulemak", "Atziri (Vaal Temple)", "Citadel bosses", "Map bosses",
                          "Trials (Sekhemas / Chaos)"),
    "Map content": ("Azmerian Wisps", "Viridian Wildwood", "Towers", "Unique maps", "Abyssal Fractures",
                    "Expedition logbooks"),
}
_CONTENT = {"key": None, "groups": None}


def content_groups():
    """-> {group: (tags)} - the shared file's (newest), else CONTENT."""
    paths = (P(FILE), os.path.join(RESOURCE_DIR, FILE), os.path.join(APP_DIR, FILE))
    key = tuple((p, os.path.getmtime(p)) for p in paths if os.path.isfile(p))
    if _CONTENT["key"] != key or _CONTENT["groups"] is None:
        c = shared().get("content")
        ok = isinstance(c, dict) and c and all(isinstance(v, list) and all(isinstance(x, str) for x in v)
                                               for v in c.values())
        _CONTENT.update(key=key, groups={g: tuple(v) for g, v in c.items()} if ok else dict(CONTENT))
    return _CONTENT["groups"]


def tag_groups():
    """Every tag group: TAG_GROUPS, then the content groups."""
    return {**TAG_GROUPS, **content_groups()}


def content_tags():
    return tuple(t for g in content_groups().values() for t in g)


def all_tags():
    return ALL_TAGS + content_tags()
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
         "regex", "sources", "items", "ledger", "atlas_image")
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
        out += [f"tags: \"{x}\" is not in the tag list" for x in s["tags"] if x not in all_tags()]
    wt = s.get("waystone_tiers")
    if wt is not None:
        lo, hi = (wt.get("min"), wt.get("max")) if isinstance(wt, dict) else (None, None)
        if not all(isinstance(x, int) and 1 <= x <= 16 for x in (lo, hi)) or lo > hi:
            out.append("waystone_tiers must be {\"min\": 1-16, \"max\": 1-16} with min <= max")
    src = s.get("sources")
    if src is not None and (not isinstance(src, list) or not all(isinstance(x, dict) and x.get("url") for x in src)):
        out.append("sources must be a list of {\"title\", \"url\"}")
    it = s.get("items")                       # 2.46.0: what the strat runs, with the mods that matter (cost check)
    def _item_ok(x):                          # 2.85.0: the same checks as the board (a bad one broke the view)
        return (isinstance(x, dict) and isinstance(x.get("base"), str) and x["base"]
                and all(x.get(k) is None or (isinstance(x[k], int) and not isinstance(x[k], bool) and 1 <= x[k] <= lim)
                        for k, lim in (("count", 1000), ("lasts", 100)))
                and (x.get("key_mods") is None or (isinstance(x["key_mods"], list)
                                                   and all(isinstance(m, str) for m in x["key_mods"]))))
    if it is not None and (not isinstance(it, list) or not all(_item_ok(x) for x in it)):
        out.append("items must be a list of {\"kind\", \"base\", \"count\", \"lasts\", \"key_mods\"}")
    img = s.get("atlas_image")                # 2.78.0: a screenshot of the atlas (l: on this PC, b: on the board)
    if img is not None and not (isinstance(img, str) and re.fullmatch(r"(l:[A-Za-z0-9._-]{1,80}|b:[0-9a-f]{32})", img)):
        out.append("atlas_image must be \"b:<board image id>\" (or \"l:<file>\" on your PC)")
    lg = s.get("ledger")
    if lg is not None and (not isinstance(lg, dict) or not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                                                and k in LEDGER_FIELDS for k, v in lg.items())):
        out.append("ledger must be numbers: " + ", ".join(LEDGER_FIELDS))
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


def _newness(d):
    return d.get("schema", 1), d.get("revision", 0)


def shared():
    """-> the newest copy of the community file (bundled or fetched), or an empty one. Strats in an older layout
    are converted (migrate)."""
    best = None
    for path in (P(FILE), os.path.join(RESOURCE_DIR, FILE), os.path.join(APP_DIR, FILE)):
        d = _read(path)
        if d and d.get("schema", 1) <= SCHEMA and (best is None or _newness(d) > _newness(best)):
            best = d
    best = best or {"schema": SCHEMA, "revision": 0, "strats": []}
    if best.get("schema", 1) < SCHEMA:
        best = dict(best, strats=[migrate(x) for x in best["strats"]])
    return best


# ---- 2.28.0 (schema 1) -> 2.29.0
_OLD_MECH_CATS = ("Breach", "Delirium", "Ritual", "Expedition", "Abyss")
_OLD_FARM = {"City area farm": "City area farm", "Sacred Bloom farm": "Sacred Bloom farm", "League start": "League start",
             "Juiced mapping": "Juiced maps", "Low-tier mapping": "Low-tier maps"}


def migrate(s):
    """A strat written by 2.28.0 -> the 2.29.0 layout: a mechanic category becomes Mapping > that mechanic,
    typed clicks become a band, profit / investment get their new names, free tags that match the tag list stay
    (others move into Tips so nothing is lost)."""
    if not isinstance(s, dict) or ("type" in s and isinstance(s.get("clicks_per_hour"), str)):
        return s
    s = dict(s)
    cat = s.get("category")
    if cat in _OLD_MECH_CATS:
        s["category"], s["type"] = "Mapping", cat
    elif cat in TAXONOMY:
        s.setdefault("type", {"Mapping": "Juiced mapping", "Bossing": "Map bosses", "Crafting": "Gear crafting",
                              "Trading": "Buy low, sell high"}.get(cat, "Other"))
    else:
        s["category"], s["type"] = "Other", "Other"
    if not isinstance(s.get("clicks_per_hour"), str) or s["clicks_per_hour"] not in CLICKS:
        s["clicks_per_hour"] = click_band(s.get("clicks_per_hour", 600)) or "Steady"
    for old, new in (("profit_per_hour", "est_profit"), ("investment", "est_cost")):
        if old in s:
            s.setdefault(new, s.pop(old))
    tags, extra = [], []
    for t in list(s.get("tags") or []) + list(s.pop("mechanics", None) or []):
        (tags if t in all_tags() else extra).append(t)
    tags += [_OLD_FARM[f] for f in s.pop("farm_types", None) or [] if f in _OLD_FARM]
    if s.pop("league_start", False):
        tags.append("League start")
    s["tags"] = list(dict.fromkeys(t for t in tags if t != s.get("type") or t == "example"))
    if extra:
        s["tips"] = list(s.get("tips") or []) + ["Tags: " + ", ".join(extra)]
    return {k: v for k, v in s.items() if k in ORDER or k == "origin"}


def mine():
    d = load_json(MINE, [])
    return [migrate(s) for s in d if isinstance(s, dict)] if isinstance(d, list) else []


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
    if _newness(d) <= _newness(have):
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
    out += [f"tags: \"{x}\" is not in the tag list" for x in o.get("tags") or [] if x not in all_tags()]
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


_NUM = r"-?\d+(?:\.\d+)?"
_RANGE = re.compile(rf"^({_NUM})(?:(?:-|to|–)({_NUM}))?$")


def _num_range(text):
    """"5-10", "-3.2", "-3 - -1", "5 to 10" -> (low, high); "" -> None. 2.85.0: negative numbers work (a losing
    setup's profit) - "-3.2" used to fail."""
    t = str(text).replace(" ", "").replace(",", ".").lower()
    for u in UNITS + ("divine", "divines", "exalted", "exalts", "chaos"):
        t = t.replace(u, "") if t.endswith(u) else t
    t = t.replace("/h", "").replace("/run", "")
    if not t:
        return None
    m = _RANGE.match(t)
    if not m:
        raise ValueError(text)
    lo, hi = float(m.group(1)), float(m.group(2) if m.group(2) is not None else m.group(1))
    return (lo, hi) if lo <= hi else (hi, lo)


def _unit_of(text, default="div"):
    t = str(text).lower()
    for word, u in (("chaos", "chaos"), ("ex", "ex"), ("div", "div")):
        if re.search(rf"\d\s*{word}|\b{word}", t):
            return u
    return default


LEDGER_WORDS = {"runs": "runs", "minutes": "minutes", "cost_per_run_div": "div cost / run", "loot_per_run_div": "div loot / run",
                "profit_per_run_div": "div profit / run", "div_per_hour": "div / hour"}


def ledger_text(lg):
    """2.85.0: the author's Strat Tracker numbers in words (they read "cost per rund")."""
    out = []
    for k, w in LEDGER_WORDS.items():
        v = lg.get(k) if isinstance(lg, dict) else None
        if isinstance(v, (int, float)):
            out.append(f"{v:g} {w}")
    return ", ".join(out)


def div_value(d):
    """A cost / profit -> divines (its middle for a range; ex and chaos at today's rates), or None."""
    if not isinstance(d, dict):
        return None
    nums = [d.get(k) for k in ("amount", "low", "high") if isinstance(d.get(k), (int, float))]
    if not nums:
        return None
    v = d["amount"] if isinstance(d.get("amount"), (int, float)) else sum(n for n in nums) / len(nums)
    unit = d.get("unit", "div")
    if unit == "div":
        return v
    try:
        from .rates import RATES
        per = RATES.value({"ex": "exalted", "chaos": "chaos"}.get(unit, unit))     # (no fetch: the rates in hand)
    except Exception:
        per = None
    if per is None:
        per = {"ex": 1 / 100, "chaos": 1 / 200}.get(unit, 1)      # (rough, until the rates are in)
    return v * per


def money_parse(text, single=False):
    """2.85.0: what you typed for a cost / profit -> the layout's object with its unit kept ("50 ex" stays ex - it
    used to become 50 div). single: one number becomes {"amount"} (a cost)."""
    rng = _num_range(text)
    if rng is None:
        return None
    unit = _unit_of(text)
    if single and rng[0] == rng[1]:
        return {"amount": rng[0], "unit": unit}
    return {"low": rng[0], "high": rng[1], "unit": unit}


def money_edit(d):
    """The layout's object -> what the editor / text / CSV show ("5-10 ex", "0.5 div"); "" for nothing."""
    if not isinstance(d, dict):
        return ""
    t = money_text(d)
    return "" if t == "?" else t


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
            for group, tags in tag_groups().items():
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
            elif key in ("est_cost", "est_profit"):
                v = money_edit(v)
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
        elif key in ("est_cost", "est_profit"):
            try:
                s[key] = money_parse(val, single=key == "est_cost")
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


# ---------------------------------------------------------------- Tablet Craft Helper quick reference
TABLET_TYPES = ("All", "Breach", "Delirium", "Ritual", "Expedition", "Abyss", "Overseer", "Temple")
# The crafting flow, as the guide gives it (shown on the Tablet Craft Helper tab, and used by tablet_advice).
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


def _status():
    """2.84.0 (feedback: "ALL price checks should ONLY be checking Instant Buyout unless the user selects in-person"):
    the seller setting from Settings (Instant Buyout by default)."""
    from .trade import listing_rules
    return listing_rules()[0]


def trade_link(league, sid=None, base=None):
    """A trade-site search for tablets with this mod (to check its price), cheapest first."""
    q = {"query": {"status": {"option": _status()}}, "sort": {"price": "asc"}}
    if base:
        q["query"]["type"] = base
    if sid:
        q["query"]["stats"] = [{"type": "and", "filters": [{"id": sid}]}]
    return (f"https://www.pathofexile.com/trade2/search/poe2/{urllib.parse.quote(league or 'Standard')}?q="
            + urllib.parse.quote(json.dumps(q, separators=(",", ":"))))


def item_trade_link(league, item):
    """2.78.0: a strat's item (its base and ★ mods) -> a trade-site search for it, cheapest first: the base, and each
    ★ mod the trade site knows (with its number as the minimum). 2.84.0: a waystone's numbers (Monster Rarity: +103%)
    are the trade site's Endgame filters, with its tier."""
    q = {"query": {"status": {"option": _status()}}, "sort": {"price": "asc"}}
    if item.get("base"):
        q["query"]["type"] = item["base"]
    filters = []
    wp = waystone_props(item)
    if wp is not None:
        tier, props = wp
        mp = {fid: {"min": v} for fid, _ro, v in props}
        if tier:
            mp["map_tier"] = {"min": tier, "max": tier}
        if mp:
            q["query"]["filters"] = {"map_filters": {"filters": mp}}
    for line in ([] if wp is not None else item.get("key_mods") or []):
        sid = stat_id(line)
        if not sid or any(f["id"] == sid for f in filters):
            continue
        f = {"id": sid}
        n = re.search(r"[-+]?\d+(?:\.\d+)?", line)
        if n:
            f["value"] = {"min": float(n.group(0)) if "." in n.group(0) else int(n.group(0))}
        filters.append(f)
    if filters:
        q["query"]["stats"] = [{"type": "and", "filters": filters}]
    return (f"https://www.pathofexile.com/trade2/search/poe2/{urllib.parse.quote(league or 'Standard')}?q="
            + urllib.parse.quote(json.dumps(q, separators=(",", ":"))))


WAYSTONE_REGEX = {"map_iir": "item_rarity", "map_bonus": "drop_chance", "map_packsize": "pack_size",
                  "map_rare_monsters": "monster_rarity", "map_magic_monsters": "effectiveness"}


def waystone_props(item):
    """2.84.0: a waystone item -> (tier or None, [(trade filter id, regex option or None, value)]) from its ★ lines
    ("Monster Rarity: +103%"); None for anything else."""
    from .waystone import PROPS
    base = str(item.get("base") or "")
    if item.get("kind") != "waystone" and "waystone" not in base.lower():
        return None
    m = re.search(r"Tier (\d+)", base)
    tier = int(m.group(1)) if m else None
    out = []
    for line in item.get("key_mods") or []:
        mm = re.match(r"^\s*([A-Za-z ]+?)\s*:?\s*([+-]?\d+(?:\.\d+)?)%?", str(line).replace("★", "").strip())
        if not mm:
            continue
        hit = PROPS.get(mm.group(1).strip().lower())
        if hit:
            v = float(mm.group(2))
            out.append((hit[0], WAYSTONE_REGEX.get(hit[0]), int(v) if v.is_integer() else v))
    return tier, out


def item_regex(items):
    """2.78.0: a stash / vendor search for these items' ★ mods (one item: all of its mods; several: any of them).
    Mods the Regex tool knows use its short terms; others are searched by their words. -> text or ''."""
    from . import regex as R
    if not items:
        return ""
    kind = "waystone" if all(i.get("kind") == "waystone" for i in items) else "tablet"
    lines = [l for i in items for l in i.get("key_mods") or []]
    if not lines:
        return ""
    if kind == "waystone" and len(items) == 1:                 # 2.84.0: its numbers and tier (not their words)
        tier, props = waystone_props(items[0]) or (None, [])
        opts = {ro: int(v) for _f, ro, v in props if ro}
        if tier:
            opts.update(tier_min=tier, tier_max=tier)
        if opts:
            try:
                out, _notes = R.build("waystone", [], [], options=opts)
            except Exception:
                out = ""
            if out:
                return out
    want = {}                                                   # 2.84.0: each mod at least the item's number
    for line in lines:
        n = re.search(r"\d+(?:\.\d+)?", str(line))
        for x in R.matching_mods(kind, line):
            v = int(float(n.group(0))) if n and len(items) == 1 else None
            want.setdefault(x, v)
    ids = list(want)
    if ids:
        try:
            out, _notes = R.build(kind, [(x, want[x]) for x in ids], [], len(items) == 1, {})
        except Exception:
            out = ""
        if out:
            return out
    words = []
    for l in lines:
        w = re.sub(r"[-+]?\d+(\.\d+)?%?", "", l).strip(" :").lower()
        w = re.sub(r"\s+", " ", w)[:40].strip()
        if w and w not in words:
            words.append(w)
    if not words:
        return ""
    return " ".join(f'"{w}"' for w in words) if len(items) == 1 else '"' + "|".join(words) + '"'


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


# ---------------------------------------------------------------- 2.46.0: strat guides as CSV
# One layout for every Money Makers CSV: a strat guide is "section, field, value, note" rows - opens in Excel / Google
# Sheets, diffs well, and its numbers use the Strat Tracker's CSV column names (ledger.CSV_LOG_HEAD), so a guide made
# from your Strat Tracker and your Ledger's CSV say the same thing the same way.
CSV_HEAD = ("section", "field", "value", "note")
CSV_MAGIC = "stashofexile2 strat"
LEDGER_FIELDS = ("runs", "minutes", "cost_per_run_div", "loot_per_run_div", "profit_per_run_div", "div_per_hour")
_CSV_STRAT = (("name", "Name - needed"), ("id", "lower-case-with-dashes; empty = made from the name"),
              ("author", "needed"), ("updated", "YYYY-MM-DD"), ("patch", "game version, e.g. 0.4"),
              ("summary", "one line - needed"), ("category", " | ".join(CATEGORIES)),
              ("type", "a type of the category (strats/README.md)"),
              ("thinking", " | ".join(w for w, _d in THINKING.values())), ("clicks_per_hour", " | ".join(CLICKS)),
              ("waystone_tiers", "e.g. 14-16"), ("est_cost_div", "a run, e.g. 2 div or 50 ex"),
              ("est_profit_div", "an hour, e.g. 5-10 div"), ("regex", "a stash search"))
_CSV_LISTS = ("requirements", "tablets", "waystones", "atlas", "craft_steps", "setup", "steps", "loot", "tips", "risks")
_ITEM_FIELDS = ("kind", "base", "name", "count", "lasts", "key_mod")


def to_csv(s=None):
    """A strat (or, with None, the blank template) as CSV rows."""
    import csv
    import io
    s = s or {}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_HEAD)
    w.writerow(("#", CSV_MAGIC, str(SCHEMA), "one row per value; lists: one row each, numbered"))
    for key, note in _CSV_STRAT:
        if key == "thinking":
            v = s.get("thoughts_per_click")
            v = THINKING[v][0] if v in THINKING else (v or "")
        elif key == "waystone_tiers":
            wt = s.get("waystone_tiers")
            v = "" if not isinstance(wt, dict) else str(wt["min"]) if wt["min"] == wt["max"] else f"{wt['min']}-{wt['max']}"
        elif key == "est_cost_div":
            v = money_edit(s.get("est_cost"))
        elif key == "est_profit_div":
            v = money_edit(s.get("est_profit"))
        elif key == "updated":
            v = s.get("updated") or date.today().isoformat()
        else:
            v = s.get(key, "")
        w.writerow(("strat", key, "" if v is None else v, note if not s else ""))
    tags = s.get("tags") or []
    for group, opts in tag_groups().items():
        mine = [t for t in tags if t in opts]
        for t in mine:
            w.writerow(("tag", group, t, ""))
        if not s:
            w.writerow(("tag", group, "", " | ".join(opts)))
    for key in _CSV_LISTS:
        for n, line in enumerate(s.get(key) or ([""] if not s and key in ("steps", "tablets") else []), 1):
            w.writerow((key, n, line, ""))
    for n, src in enumerate(s.get("sources") or [], 1):
        w.writerow(("source", n, src.get("url", ""), src.get("title", "")))
    for n, it in enumerate(s.get("items") or [], 1):
        for f in _ITEM_FIELDS[:-1]:
            if it.get(f) not in (None, ""):
                w.writerow(("item", f"{n}:{f}", it[f], ""))
        for m in it.get("key_mods") or []:
            w.writerow(("item", f"{n}:key_mod", m, ""))
    for k in LEDGER_FIELDS:
        if k in (s.get("ledger") or {}):
            w.writerow(("ledger", k, f"{s['ledger'][k]:g}", "from the Strat Tracker"))
    return buf.getvalue()


def is_csv(text):
    return str(text).lstrip("\ufeff").startswith("section,field,value")


def from_csv(text):
    """CSV rows -> a strat (check it with validate)."""
    import csv
    import io
    s, items = {}, {}
    for r in csv.DictReader(io.StringIO(str(text).lstrip("\ufeff"))):
        sec, field, val = (r.get("section") or "").strip(), (r.get("field") or "").strip(), (r.get("value") or "").strip()
        if not sec or sec == "#" or val == "":
            continue
        if sec == "strat":
            if field == "thinking":
                s["thoughts_per_click"] = _WORD2THINK.get(val.split(" - ")[0].lower()) or (int(val) if val.isdigit() else val)
            elif field == "clicks_per_hour":
                s[field] = click_band(val) or val
            elif field == "waystone_tiers":
                try:
                    lo, hi = _num_range(val.lower().replace("t", ""))
                    s[field] = {"min": int(lo), "max": int(hi)}
                except (TypeError, ValueError):
                    s[field] = val
            elif field in ("est_cost_div", "est_profit_div"):
                key2 = field[:-4]
                try:
                    s[key2] = money_parse(val, single=key2 == "est_cost")
                except (TypeError, ValueError):
                    s[key2] = val
            elif field in ("name", "id", "author", "updated", "patch", "summary", "category", "type", "regex"):
                s[field] = val
        elif sec == "tag":
            s.setdefault("tags", []).append(val)
        elif sec in _CSV_LISTS:
            s.setdefault(sec, []).append(val)
        elif sec == "source":
            s.setdefault("sources", []).append({"title": (r.get("note") or val).strip(), "url": val})
        elif sec == "item" and ":" in field:
            n, f = field.split(":", 1)
            it = items.setdefault(n, {})
            if f == "key_mod":
                it.setdefault("key_mods", []).append(val)
            elif f in ("count", "lasts"):
                try:
                    it[f] = int(float(val))
                except ValueError:
                    pass
            elif f in _ITEM_FIELDS:
                it[f] = val
        elif sec == "ledger" and field in LEDGER_FIELDS:
            try:
                s.setdefault("ledger", {})[field] = float(val)
            except ValueError:
                pass
    if items:
        s["items"] = [dict(items[k], key_mods=items[k].get("key_mods", []))
                      for k in sorted(items, key=lambda x: int(x) if x.isdigit() else 0)]
    if s.get("name") and not s.get("id"):
        s["id"] = slug(s["name"])
    return {k: v for k, v in s.items() if v not in (None, "", [])}


def read_any(raw):
    """A strat file's text (CSV, the older .txt layout, or JSON) -> what's in it."""
    if is_csv(raw):
        return from_csv(raw)
    if raw.lstrip().startswith(("{", "[")):
        return json.loads(raw)
    return from_text(raw)


def cost_now(s, costs):
    """2.46.0: what a run of this strat costs today, from the daily check -> (divines, parts, checked at) or None."""
    c = (costs or {}).get(s.get("id"))
    if not c or not s.get("items"):
        return None
    total, parts = 0.0, []
    for i, it in enumerate(s["items"]):
        p = (c.get("prices") or {}).get(str(i))
        if p is None:
            continue
        per = p * max(1, int(it.get("count") or 1)) / max(1, int(it.get("lasts") or 1))
        total += per
        parts.append((it.get("name") or it["base"], p, per))
    return (total, parts, c.get("at")) if parts else None
