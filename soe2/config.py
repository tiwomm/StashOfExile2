"""Paths, settings and the files in the data folder (settings.json, the mod book).

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import json
import os
import sys
import threading


# ------------------------------------------------------------------ paths / settings
from . import __version__ as APP_VERSION      # set in soe2/__init__.py; the launcher's file name must match


def pretty_version(v=None):
    """'2.0.0-beta.1' -> '2.0 beta 1', '2.0.1' -> '2.0.1', '2.1.0' -> '2.1' (what people read)."""
    import re as _re
    m = _re.match(r"v?(\d+)\.(\d+)(?:\.(\d+))?\s*[-_. ]?\s*(?:(beta|b|rc)\s*[-_. ]?\s*(\d+))?", str(v or APP_VERSION).strip(),
                  _re.I)
    if not m:
        return str(v or APP_VERSION)
    major, minor, patch, kind, n = m.groups()
    out = f"{major}.{minor}" + (f".{patch}" if patch and patch != "0" else "")
    if kind:
        out += (" RC " if kind.lower() == "rc" else " beta ") + n
    return out


APP_TITLE = f"StashOfExile2 v{pretty_version()}"


APP_DIR = os.path.dirname(sys.executable if getattr(sys, "frozen", False)     # the folder with the exe / launcher:
                          else os.path.dirname(os.path.abspath(__file__)))        # the one above soe2/


RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)      # inside the .exe: where PyInstaller unpacks the bundled files


# Data lives in one fixed folder, NOT next to the app, so moving or updating the app never loses it.
if sys.platform == "win32":
    DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "StashOfExile2")
else:
    DATA_DIR = os.path.join(os.path.expanduser("~"), ".stashofexile2")


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
                pass


import_old_data()


# ---- bundled reference data (1.37): tabs.txt and jewels.txt come inside the app. A newer copy in a new version
# replaces the one in the data folder (the old one is kept as a .bak); your own files (settings, rules, lists) are
# never touched. Bump a number here when you ship a changed file.
BUNDLED_DATA = {"tabs.txt": 2, "jewels.txt": 2, "gamedata.json": 1, "regexdata.json": 1, "default_rules.json": 2, "searchdata.json": 1}   # gamedata 1.38, regexdata 1.44
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
            pass
    save_json("data_versions.json", seen)


BASE = os.environ.get("SOE2_TRADE_API") or "https://www.pathofexile.com/api/trade2"


HEADERS = {"User-Agent": "personal-stash-pricer/1.0", "Content-Type": "application/json"}


DEFAULTS = {
    "league": "",
    "good_div": 0.5,       # a mod is "good" if the cheapest listings with it cost at least this many divines
    "learn": True,         # look up every new mod in the background
    "popups": True,
    "sound": True,         # beep when a batch finishes
    "toast_secs": 6,
    "range_factor": 0.9,   # search for rolls >= 90% of yours
    "min_results": 3,
    "tray": True,          # minimize to the system tray (needs pystray + pillow)
    "spread_warn": 20,     # warn when the cheapest and dearest listing are this many times apart (0 = off)
    "hotkey_only": True,   # only accept items copied while YOU press Ctrl+Alt+C (ignores Sidekick Ctrl+D copies)
    "memory_shortcut": False,   # True: skip searching when 5+ identical searches in the last memory_hours agree (see 1.21)
    "memory_hours": 24,
    "model_shortcut": False,    # True: the model may set a price itself, but only after 100 checked guesses at 99 percent (1.23)
    "market_league": "",        # the league market.db's current data belongs to (1.23)
    "rates_auto": True,    # check the exchange rates once an hour (poe.ninja) so prices in other currencies can be converted
    "pace": "Balanced",    # Fast / Balanced / Gentle - how carefully we stay under the trade site's limits
    "stale_days": 3,       # re-check a learned mod after this many days
    "status": "Instant Buyout",   # which listings count: the trade site's own "listing status" choices
    "age": "2 days",              # ignore listings older than this (stale / banned-account / outdated prices)
    "view": "Not yet listed",     # which items the list shows
    "auto_copy": True,            # copy the item's name to the clipboard when you click it
    "listen": True,               # watch the clipboard for copied items (always on)
    "col_widths": {},             # remembered column widths of the item list
    "panel_w": 430,               # remembered width of the side panel
    "uses": "10",                 # tablets: only compare with tablets that have at least this many uses left
    "wealth_account": "",         # Wealth page: your account name as the trade site shows it, e.g. Name#1234 (1.33)
    "on_top": True,               # keep the window in front of other windows, and undo minimizes you didn't ask for (1.35)
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


VIEWS = ["Not yet listed", "Listed", "Removed", "All"]


def load_json(name, default):
    try:
        with open(P(name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(name, data):
    try:
        tmp = P(name) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, P(name))          # all-or-nothing: never leaves a half-written file behind
    except Exception:
        pass


refresh_bundled_data()                       # needs load_json / save_json above
SETTINGS = {**DEFAULTS, **load_json("settings.json", {})}


if SETTINGS["status"] not in dict(STATUS_OPTIONS):
    SETTINGS["status"] = DEFAULTS["status"]


if SETTINGS["age"] not in [a[0] for a in AGE_OPTIONS]:
    SETTINGS["age"] = DEFAULTS["age"]


if SETTINGS["view"] not in VIEWS:
    SETTINGS["view"] = DEFAULTS["view"]


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
            pass
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
        pass


backup_modbook()

PAGE_CHECKS = "Price checks"        # the price-check page (1.40: was "Items")
