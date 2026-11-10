"""Paths, settings and the files in the data folder (settings.json, the mod book).

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import json
import os
import sys
import threading


# ------------------------------------------------------------------ paths / settings
from . import buglog
from . import __version__ as APP_VERSION      # set in soe2/__init__.py; the launcher's file name must match
from .names import PAGES                       # 2.126.0: one name per feature


def pretty_version(v=None):
    """'2.0.0-beta.1' -> '2.0.0 beta 1', '2.0.1' -> '2.0.1', '2.10.0' -> '2.10.0' (2.10.0: always in full, SemVer)."""
    import re as _re
    m = _re.match(r"v?(\d+)\.(\d+)(?:\.(\d+))?\s*[-_. ]?\s*(?:(beta|b|rc)\s*[-_. ]?\s*(\d+))?", str(v or APP_VERSION).strip(),
                  _re.I)
    if not m:
        return str(v or APP_VERSION)
    major, minor, patch, kind, n = m.groups()
    out = f"{major}.{minor}.{patch or 0}"
    if kind:
        out += (" RC " if kind.lower() == "rc" else " beta ") + n
    return out


TAGLINE = "One tool to rule them all."          # 2.73.2
APP_TITLE = f"StashOfExile2 v{pretty_version()}  -  {TAGLINE}"


APP_DIR = os.path.dirname(sys.executable if getattr(sys, "frozen", False)     # the folder with the exe / launcher:
                          else os.path.dirname(os.path.abspath(__file__)))        # the one above soe2/


RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)      # inside the .exe: where PyInstaller unpacks the bundled files


# Data lives in one fixed folder, NOT next to the app, so moving or updating the app never loses it.
if sys.platform == "win32":
    DEFAULT_DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "StashOfExile2")
else:
    DEFAULT_DATA_DIR = os.path.join(os.path.expanduser("~"), ".stashofexile2")
# 2.131.0 (request: a "portable" option - choose where the data lives): a one-line file naming the folder you picked,
# next to the app (portable) or in the usual folder - read before anything else is
POINTER = "data_location.txt"


def chosen_data_dir():
    for d in (APP_DIR, DEFAULT_DATA_DIR):
        try:
            with open(os.path.join(d, POINTER), encoding="utf-8") as f:
                p = f.read().strip()
            if p and os.path.isabs(p):
                os.makedirs(p, exist_ok=True)
                return p
        except OSError:
            continue
    return None


DATA_DIR = chosen_data_dir() or DEFAULT_DATA_DIR


def move_data(new_dir):
    """2.131.0: your data copied to new_dir, then the app uses it from the next start (the old folder is kept, so
    nothing is lost if something goes wrong). -> (True, note) or (False, why)."""
    import shutil
    new_dir = os.path.abspath(new_dir)
    if os.path.normcase(new_dir) == os.path.normcase(os.path.abspath(DATA_DIR)):
        return False, "That's the folder in use."
    try:
        os.makedirs(new_dir, exist_ok=True)
        shutil.copytree(DATA_DIR, new_dir, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(POINTER, "*.lock", "__pycache__"))
    except OSError as e:
        return False, f"Couldn't copy your data there ({e.__class__.__name__}) - nothing was changed."
    reset = os.path.normcase(new_dir) == os.path.normcase(os.path.abspath(DEFAULT_DATA_DIR))
    # a folder inside the app's own folder (portable): the pointer goes with the app; anywhere else it lives in the
    # usual folder, so an update that replaces the app's folder can't lose it. The other pointer goes (one place).
    app_dir = os.path.normcase(os.path.abspath(APP_DIR))
    portable = os.path.normcase(new_dir).startswith(app_dir + os.sep) or os.path.normcase(new_dir) == app_dir
    order = (APP_DIR, DEFAULT_DATA_DIR) if portable else (DEFAULT_DATA_DIR, APP_DIR)
    wrote = None
    for d in order:
        if reset:
            break
        try:
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, POINTER), "w", encoding="utf-8") as f:
                f.write(new_dir)
            wrote = d
            break
        except OSError:
            continue
    for d in (APP_DIR, DEFAULT_DATA_DIR):
        if d == wrote:
            continue
        try:
            os.remove(os.path.join(d, POINTER))
        except FileNotFoundError:
            pass
        except OSError:
            if d == APP_DIR:                       # (a pointer left next to the app would still win)
                return False, "Couldn't change the folder next to the app - nothing was changed."
    wrote = wrote or reset
    if not wrote:
        return False, "Couldn't save the new place - nothing was changed."
    return True, "Copied. Restart the app to use the new folder (the old one is kept)."


DATA_FILES = ["settings.json", "session.json", "modbook.json", "modbook.backup.json", "mod_rules.json", "community_rules.json",
              "tabs.txt", "jewels.txt", "history.csv", "wealth.json"]


MIGRATED = []


def P(name):
    return os.path.join(DATA_DIR, name)


def import_old_data():
    """Copy data files found next to the app into the data folder - only files the data folder does not have yet."""
    import shutil
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        return
    for name in DATA_FILES:
        dst = os.path.join(DATA_DIR, name)
        for folder in (APP_DIR, RESOURCE_DIR):                # next to the app first, then the files packed inside the .exe
            src = os.path.join(folder, name)
            try:
                if os.path.isfile(src) and not os.path.exists(dst) and os.path.abspath(src) != os.path.abspath(dst):
                    shutil.copyfile(src, dst)
                    MIGRATED.append(name)
                    break
            except Exception:
                buglog.caught()


import_old_data()


# ---- bundled reference data (1.37): tabs.txt and jewels.txt come inside the app. A newer copy in a new version
# replaces the one in the data folder (the old one is kept as a .bak); your own files (settings, rules, lists) are
# never touched. Bump a number here when you ship a changed file.
BUNDLED_DATA = {"tabs.txt": 2, "jewels.txt": 2, "gamedata.json": 1, "regexdata.json": 2, "default_rules.json": 3, "searchdata.json": 1, "anointdata.json": 1, "cxnames.json": 1}   # gamedata 1.38, regexdata 1.44
DATA_UPDATED = []


def refresh_bundled_data():
    import shutil
    seen = load_json("data_versions.json", None)
    if seen is None:                                     # first start of 1.37+: what you have counts as current
        seen = {name: ver for name, ver in BUNDLED_DATA.items() if os.path.exists(P(name))}
    for name, ver in BUNDLED_DATA.items():
        if seen.get(name, 0) >= ver:
            continue
        src = next((os.path.join(d, name) for d in (RESOURCE_DIR, APP_DIR)
                    if os.path.isfile(os.path.join(d, name)) and os.path.abspath(os.path.join(d, name)) != os.path.abspath(P(name))), None)
        if not src:
            continue
        try:
            existed = os.path.exists(P(name))
            if existed:
                shutil.copyfile(P(name), P(f"{name}.v{seen.get(name, 0)}.bak"))
            shutil.copyfile(src, P(name))
            seen[name] = ver
            if existed:                                  # a file new in this version isn't an "update" (1.44)
                DATA_UPDATED.append(name)
        except Exception:
            buglog.caught()
    save_json("data_versions.json", seen)


BASE = os.environ.get("SOE2_TRADE_API") or "https://www.pathofexile.com/api/trade2"


# 2.92.0: every request says honestly which app is asking and where to find it (GGG asks apps to identify themselves);
# no name, account or email of the user
APP_UA = f"StashOfExile2/{APP_VERSION} (+https://github.com/tiwomm/StashOfExile2)"
HEADERS = {"User-Agent": APP_UA, "Content-Type": "application/json"}


DEFAULTS = {
    "league": "",
    "good_div": 0.5,       # a mod is "good" if the cheapest listings with it cost at least this many divines
    "learn": True,         # look up every new mod in the background
    "popups": True,
    "sound": True,         # beep when a batch finishes
    "toast_secs": 6,
    "range_factor": 0.9,   # search for rolls >= 90% of yours
    "min_results": 3,
    "tray": False,         # minimize to the system tray (needs pystray + pillow) - 2.116.0: off for new installs
    "spread_warn": 20,     # warn when the highest listing costs this many times the lowest (0 = off)
    "pc_ctrl_c": True,     # 2.80.0: your price check key on an item in game opens it on Price Checks
    "pc_key": "Ctrl+D",    # 2.83.1 (feedback): the price check key (was the game's plain Ctrl+C)
    "pc_front": True,      # ...and brings the app to the front
    "pc_popup": False,     # 2.113.0: ...or shows it in a card over the game instead (pcpop.py)
    "pc_both": False,      # 2.123.2: ...and the app shows it too (Here | Overlay | Both)
    "pc_close_key": "Esc",  # 2.121.1: closes that card (only while it's open and the game is in front)
    "pc_art": True,        # ...with the items' pictures from the trade site's image server
    "memory_hours": 24,
    "market_league": "",        # the league market.db's current data belongs to (1.23)
    "rates_auto": True,    # check the exchange rates once an hour (poe.ninja) so prices in other currencies can be converted
    "stale_days": 3,       # re-check a learned mod after this many days
    "status": "Instant Buyout",   # which listings count: the trade site's own "listing status" choices
    "age": "2 days",              # ignore listings older than this (stale / banned-account / outdated prices)
    "view": "All",                # which items the list shows (2.105.0: always All - listing marks are gone)
    "auto_copy": True,            # copy the item's name to the clipboard when you click it
    "listen": True,               # watch the clipboard for copied items (always on)
    "col_widths": {},             # remembered column widths of the item list (not Item's: it fills the rest)
    "bulk_cols_off": [],          # 2.125.3: Bulk Pricing columns turned off in Columns ▾ (all show by default)
    "panel_w": 430,               # remembered width of the side panel
    "uses": "10",                 # tablets: only compare with tablets that have at least this many uses left
    "wealth_account": "",         # Wealth page: your account name as the trade site shows it, e.g. Name#1234 (1.33)
    "on_top": False,              # keep the window in front of other windows, and undo minimizes you didn't ask for (1.35)
                                  # (2.116.0, feedback: off for new installs - a saved setting is kept)
    "auto_check_updates": False,  # 2.0 beta 7: look for a new version on GitHub when the app starts (tells you, asks first)
    "auto_update": False,         # 2.0 beta 7: ...and install it straight away, without asking
}


USES_OPTIONS = [str(i) for i in range(10, 0, -1)] + ["Match item", "Off"]


# The trade site's "listing status" dropdown -> the value the API wants.
STATUS_OPTIONS = [("Instant Buyout", "securable"), ("Instant Buyout and In Person", "available"),
                  ("In Person (Online in League)", "onlineleague"), ("In Person (Online)", "online"),
                  ("Any", "any")]


# "Listed within": label, value the API wants, hours (we also double-check the age of every listing ourselves)
AGE_OPTIONS = [("1 hour", "1hour", 1), ("3 hours", "3hours", 3), ("12 hours", "12hours", 12),
               ("1 day", "1day", 24), ("2 days", "3days", 48), ("3 days", "3days", 72),
               ("1 week", "1week", 168), ("Any time", None, None)]


VIEWS = ["Not yet listed", "Listed", "Sold", "Removed", "All"]


def load_json(name, default):
    try:
        with open(P(name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


SAVE_ERRORS = []                          # 2.4.0: (file, problem) - saving no longer fails without a trace


def save_json(name, data):
    """-> True when the file was written. A failure (file in use, folder not writable...) is noted in SAVE_ERRORS and
    the app's log (buglog) instead of passing silently."""
    try:
        tmp = P(name) + ".tmp"
        text = json.dumps(data)           # 2.25.1: dumps (one go, the fast C encoder) - json.dump streams through
        with open(tmp, "w", encoding="utf-8") as f:   # the slow pure-Python one: a long Price checks list took
            f.write(text)                 # seconds and froze the app
        os.replace(tmp, P(name))          # all-or-nothing: never leaves a half-written file behind
        return True
    except Exception as e:
        SAVE_ERRORS.append((name, str(e)[:200]))
        del SAVE_ERRORS[:-20]
        try:
            from . import buglog                              # 2.115.0: the one log (paths and names cleaned)
            buglog.record("error", f"saving {name}", detail=str(e))
        except Exception:
            buglog.caught()
        return False


refresh_bundled_data()                       # needs load_json / save_json above
SETTINGS = {**DEFAULTS, **load_json("settings.json", {})}


if SETTINGS["status"] not in dict(STATUS_OPTIONS):
    SETTINGS["status"] = DEFAULTS["status"]
from . import migrations as _migrations          # 2.117.0: one-time changes, one list (soe2/migrations.py)
_migrations.run(SETTINGS, "settings", lambda: save_json("settings.json", SETTINGS))


if SETTINGS["age"] not in [a[0] for a in AGE_OPTIONS]:
    SETTINGS["age"] = DEFAULTS["age"]


SETTINGS["view"] = "All"          # 2.105.0: the Show box is gone - every item shows


if SETTINGS["uses"] not in USES_OPTIONS:
    SETTINGS["uses"] = DEFAULTS["uses"]


SETTINGS["listen"] = True


# v2 = prices converted with poe.ninja rates, raw prices kept
# v3 = prices only count Instant Buyout listings from the last day or two (older entries are re-learned)
# v4 = tablet prices also require the 'uses remaining' minimum
MODBOOK_VERSION = 4


def load_modbook():
    """Returns (mod book, note for the status bar). Never silently throws data away."""
    path = P("modbook.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("not a mod book")
    except FileNotFoundError:
        return {}, "No mod book yet - it builds up as you copy items."
    except Exception:
        try:
            os.replace(path, P("modbook.broken.json"))
        except Exception:
            buglog.caught()
        return {}, "modbook.json couldn't be read - kept as modbook.broken.json and started a fresh one."
    old = 0
    for e in data.values():
        if e.get("v") != MODBOOK_VERSION:  # written by an older version: its prices may be wrong, so re-learn them
            e["floor"], e["ts"], e["legacy"] = None, 0, True
            old += 1
    note = f"Loaded {len(data)} learned mods" + (f" - {old} from an older version will be re-checked in the background." if old else ".")
    return data, note


MODBOOK, MODBOOK_NOTE = load_modbook()      # "Base|stat_id" -> info about that mod


_modbook_lock = threading.Lock()


def save_modbook():
    """Save the mod book safely: one writer at a time, all-or-nothing, and never replace a populated
    file with an empty one."""
    with _modbook_lock:
        if not MODBOOK:
            try:
                if os.path.getsize(P("modbook.json")) > 4:     # file has content, we hold nothing: don't wipe it
                    return
            except OSError:
                pass
        save_json("modbook.json", dict(MODBOOK))


def backup_modbook():
    """Keep a copy of the last good mod book from the previous session (modbook.backup.json)."""
    try:
        if MODBOOK:
            import shutil
            shutil.copyfile(P("modbook.json"), P("modbook.backup.json"))
    except Exception:
        buglog.caught()


backup_modbook()

PAGE_CHECKS = PAGES["checks"]       # the list page (1.40: was "Items"; 2.80.0: was "Price checks")
PAGE_PC = PAGES["pricecheck"]       # 2.80.0: one item at a time, with the trade site's listings
