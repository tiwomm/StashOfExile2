"""The main window: Price checks page (was Items), Mod book (with the mod rules inside), side panel, hotkeys, updates.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import collections
import csv
import json
import os
import queue
import random
import re
import sys
import threading
import time
import types
import tkinter as tk
import traceback
import types
import webbrowser
from datetime import datetime
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from . import buglog
from .settings_page import SettingsPage      # 2.117.0: split out of this file
from .config import (
    AGE_OPTIONS, DATA_UPDATED, APP_DIR, APP_TITLE, APP_VERSION, pretty_version, DATA_DIR, load_json, MIGRATED, MODBOOK, MODBOOK_NOTE, P,
    save_json, save_modbook, SETTINGS, STATUS_OPTIONS, VIEWS, DEFAULTS,
)
from .clipboard import clip_seq, read_clipboard_text
from .util import _amt, _num, mmss
from .net import _STATUS_HOOK, fmt_stamp, LIMITER, per_text
from .updates import clean_env, cleanup_update, download_asset, FROZEN, latest_release, pick_asset, REPO, is_newer, vtuple
from .rates import RATES
from .mods import (
    auto_impact, COMMUNITY, COMMUNITY_ACTIVE, COMMUNITY_DISAGREE, default_impact, impact_key, IMPACT_LABEL,
    IMPACTS, JEWEL_KINDS, JEWELS, LEARNED, learned_info, mod_cat, norm, parse_item, pretty, rebuild_community,
    RULES, SHARE_MAX_HIGH, SIDTEXT, TAB_KINDS, TABS, TEXT2SID, vfilter, rule_key, SCOPED_CATS, migrate_scoped_rules,
    default_tier, scoped, tier_key, TIER_ORDER, TIERS, SHOWN_TIERS, TIER_F, F_TIP,
)
from .mods import DUPS, find_stat, current_key
from .trade import ago, mod_impact, CURRENCY_CHOICES, STATUS_CHOICES
from .market import MARKET
from .pricefmt import fmt_div, fmt_price, parse_price
from .wealth import WEALTH, parse_stack, WPRICES
from .engine import Engine
from . import gear, waystone
from .toasts import Toasts
from .style import C, MOD_COL, FLAG_COLORS, FONT_TITLE, hotkey_blocked, MONO, Plate, SegBook, SegBar, setup_style, Toast, KeyCapture, Tooltip
from .chrome import BarNote, SectionBar, Viewport, section as chrome_section
from .communitymods import WHAT as CM_WHAT
from .winsys import ICON_B64, KeyWatch, Tray
from .wealth_page import WealthPage
from .listkeys import ListKeys
from .alerts_page import AlertsPage
from .about_page import AboutPage
from .tabreader_page import TabReaderPage
from .searchopts_page import SearchOptsPage
from .valuelog import VALUE_LOG
from .exchange_page import ExchangePage
from .library_page import LibraryPage
from .regex_page import RegexPage
from .calc import CalcOverlay
from .ovparts import OverlayParts
from .campaign_ui import CampaignUI
from .insights_page import InsightsPage
from .moneymakers_page import MoneyMakersPage
from .maplib_page import MapLibraryPage
from .ovhelp import OverlayHelp
from .plan_page import FocusPokes, GamePlanPage
from .stashscan_page import StashScanPage      # 2.102.0: Wealth › Scan stash (beta)
from .remnant_page import RemnantPage         # 2.37.0: Expedition Remnant Price Checker
from .ledger_page import LedgerPage           # 2.45.0: Money Makers > Strat Tracker
from .feedback_page import FeedbackPage       # 2.48.0: the update badge and Report a bug (taskbar)
from .feed_page import FeedPage               # 2.51.0: Mod book › Manual feed
from .merged_page import MergedOverlay        # 2.55.0: one overlay window for timer, Mechanic Helper and Notes
from .ovlight import LightOverlay             # 2.101.0: the light looks (Hairline, Slate, Flanks, Micro)
from .utilities_page import UtilitiesPage
from .tracker_page import TrackerPage
from .search_page import SearchPage
from .pricecheck_page import PriceCheckPage    # 2.80.0: Price Checks (one item, the trade site's listings)
from .pcpop import PricePopup                  # 2.113.0: the price check in a card over the game
from .ovrates import OverlayRates              # 2.91.0: exchange rates over the game
from .ovquick import OverlayQuick              # P4 (2.108.0): right-click the cog - Quick settings
from .community_page import CommunityPage      # 2.94.0: Settings › Privacy & community
from .ratemods_page import RateModsPage
from .ovrecap import OverlayRecap        # 2.96.0: Help rate mods, the Bulk Pricing floor
from .wellsouls_page import WellSoulsPage      # 2.81.0: Desecration Helper (tiers at The Well of Souls)
from .rumours_page import RumoursPage          # 2.83.0: Island Rumours; where the Remnant watcher looks
from .favorites_page import FavoritesPage      # 2.84.0: Price Checks ↳ Favorites
from .boardmod_page import BoardModPage        # 2.85.0: your community name, Suggest an edit, History, reviewers
from .gearbook_page import GearBookPage  # 2.99.0: Mod book › Gear rules, Unique rules, Learned per tab
from .leaderboard_page import LeaderboardPage  # 2.86.0: Overlay ↳ Leaderboards
from . import gamedata
from . import modules
from .shell import Shell


from .config import PAGE_CHECKS       # 1.40: was "Items"


CARD_BOX = 46                 # 2.78.3: a Min / Max / item level box on the item card (px)
REQ_NAMES = {"lvl": "Level", "str": "Str", "dex": "Dex", "int": "Int"}         # 2.79.0
MISC_ROWS = (("corrupted", "Corrupted"), ("fractured", "Fractured"), ("desecrated", "Desecrated"),
             ("sanctified", "Sanctified"), ("mirrored", "Mirrored"), ("unidentified", "Unidentified"))


def plain_notes(md):
    """2.112.3: the release notes as plain lines for the update question - GitHub's markdown (## headings, **bold**,
    the download / not-affiliated footer) showed as raw symbols in the Windows dialog."""
    out = []
    for line in md.replace("\r", "").split("\n"):
        t = line.strip()
        if not t or t.startswith(("**Download:**", "This product isn't affiliated")):
            continue
        if t.startswith("#"):
            t = t.lstrip("#").strip()
            if t.lower().startswith("what's new in"):
                continue                                  # (the dialog already says which version)
            t = t + ":"
        t = re.sub(r"\*\*(.+?)\*\*", r"\1", t).replace("`", "")
        t = "• " + t[2:] if t.startswith(("- ", "* ")) else t
        out.append(t)
    return "\n".join(out).strip()



class App(SettingsPage, GearBookPage, PriceCheckPage, PricePopup, FavoritesPage, BoardModPage, LeaderboardPage, WellSoulsPage, RumoursPage, ListKeys, AlertsPage, AboutPage, TabReaderPage, SearchOptsPage, ExchangePage, WealthPage, LibraryPage, RegexPage, UtilitiesPage, TrackerPage, SearchPage, CalcOverlay, InsightsPage, MoneyMakersPage, MapLibraryPage, RemnantPage, LedgerPage, FeedbackPage, FeedPage, MergedOverlay, LightOverlay, GamePlanPage, FocusPokes, OverlayHelp, OverlayParts, CampaignUI, OverlayRates, CommunityPage, RateModsPage, OverlayRecap, StashScanPage, OverlayQuick):
    COLS = [("added", "#", 46, "e"), ("name", "Item", 220, "w"), ("type", "Type", 110, "w"), ("mark", "Status", 90, "center"),
            ("est", "Est. value", 110, "e"), ("conf", "Confidence", 95, "center"), ("listings", "Listings", 70, "e"), ("priced", "Priced at", 130, "w"),
            ("match", "How it was priced", 300, "w"), ("vmods", "★", 60, "center"),
            ("ilvl", "iLvl", 50, "e")]              # 2.73.2: item level (last in the data, shown after Type)
    # 2.24.0: "★ Valuable" (how many of the item's mods your Mod book rates High) is the last column in the data, so
    # older code reading values by position keeps working, but it's shown right after the item's name
    SHOW_COLS = ("added", "name", "vmods", "type", "ilvl", "mark", "est", "conf", "listings", "priced", "match")
    MARK_TEXT = {"new": "", "listed": "✔ listed", "sold": "💰 sold", "removed": "✖ removed"}
    VIEW_MARK = {"Not yet listed": "new", "Listed": "listed", "Sold": "sold", "Removed": "removed"}

    def __init__(self, root):
        self.root = root
        from . import overlaywin as _ow
        _ow.OV_PAL[0] = self.ov_palette                   # 2.109.0: everything over the game in the overlay's style
        self._fresh_install = not SETTINGS.get("seen_version")   # 2.90.0: a new install starts with a clean bar
        if self._fresh_install:                          # 2.118.0: every helper starts on (each can go off in
            SETTINGS.setdefault("util_delirium_autostart", True)      # Overlay ↳ Settings › Helpers)
        root.title(APP_TITLE)
        if sys.platform == "win32":      # own taskbar entry with our icon (not python's)
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("StashOfExile2.App")
            except Exception:
                buglog.caught()
        try:
            self.icon_img = tk.PhotoImage(data="".join(ICON_B64.split()))     # keep on self or tk drops it
            root.iconphoto(True, self.icon_img)
        except Exception:
            buglog.caught()
        root.geometry(self.saved_geometry() or "1280x800")      # 2.23.1: where you left it last time
        root.minsize(1000, 560)
        root.bind("<Configure>", self._note_window, add="+")
        from .style import apply_look                   # 2.0.0: Settings > Appearance (the theme)
        apply_look(look_settings(), root)
        root.configure(bg=C["bg"])
        self.paint_titlebar()                            # 2.61.0: Windows' own title bar in the theme's colors
        root.after(1500, self.paint_titlebar)            # (again once the window is really on screen)
        setup_style(root)
        from .style import responsive
        responsive(root)                                   # 2.98.0: wrapped labels follow their width
        from .motion import install as motion_install
        motion_install(root)                               # 2.100.0: hover on list rows and clickable icons
        self.records, self.next_id = {}, 1
        self.ui_q = queue.Queue()
        _STATUS_HOOK[0] = lambda s: self.ui_q.put(("status", s))
        self.engine = Engine(self.records, self.ui_q)
        gamedata.set_fallback(self.trade_stat_lookup)          # 1.40: learn unknown mod wordings from the trade site
        gamedata.load_trade_items()                            # 2.121.0: the trade site's item list (yesterday's copy)
        self.toast = Toast(root)
        self.toasts = Toasts(root)                 # 2.35.0: the app's toasts (in-app); self.toast = over the game
        self.sort_col, self.sort_rev = None, False
        self.last_clip = ""
        self.status_text, self.status_until = MODBOOK_NOTE, time.time() + 25
        if MIGRATED:
            self.status_text = "Copied into your data folder: " + ", ".join(MIGRATED) + ".   " + self.status_text
        if DATA_UPDATED:
            self.status_text = ("Updated from this version: " + ", ".join(DATA_UPDATED)
                                + " (old copies kept as .bak).   " + self.status_text)
        self.status_text = f"Data folder: {DATA_DIR}   " + self.status_text
        self.done_times = collections.deque(maxlen=6)
        self.was_busy, self.batch_ids = False, set()
        self.limit_win = None
        self.price_var = None
        self.detail_vars = []
        self.shown_rec, self._dwidth, self._dafter = None, 0, None
        self.seen_texts = {}
        self._err_seen = {}
        self.dirty, self.last_save = False, 0.0
        self.rt = {}                                # per rules page ("tablet" / "jewel"): its widgets and row -> mod key
        self.run_migrations()                        # 2.117.0: every one-time change, in order (soe2/migrations.py)
        self.keys = KeyWatch()                       # made before the windows (the utility windows ask about it); started below
        from . import listkit                        # 2.12.0: keys, right-click menus and striped rows everywhere
        listkit.install(self)
        SETTINGS.setdefault("poe2db_key", "Ctrl+Shift+D")
        SETTINGS.setdefault("copy_marker", True)            # 2.19.0: a mark where you pressed Ctrl+Alt+C
        SETTINGS.setdefault("copy_marker_secs", 10)         # 2.24.0: how long it stays
        SETTINGS.setdefault("copy_marker_hold", False)      # 2.24.0: or until Esc is tapped twice (2.25.0)
        SETTINGS.setdefault("copy_marker_colour", "Gold")    # 2.25.0
        self.build()
        self.engine.start()
        self.engine.add(0, "init")
        self.load_session()
        try:
            self.last_clip = root.clipboard_get()
        except tk.TclError:
            self.last_clip = ""
        self.last_seq, self.last_heard = clip_seq(), None
        self.poll_gen, self.last_poll = 0, time.time()
        root.after(150, self.poll_clipboard, 0)
        root.after(100, self.poll_events)
        self._rates_busy = False
        root.after(1500, self.rates_tick)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.keys.start()
        self.root.after(5 * 60 * 1000, self.keys_refresh)   # 2.88.2: a fresh key watcher every 5 minutes
        self.start_utilities()                       # 2.0: chat commands & notes listen to the same keyboard watcher
        root.after(15000, self.cm_start)             # 2.31.0: the community Mod book (hourly)
        root.after(2500, self.calc_ov_restore)       # 2.74.0: the calculator over the game, if it was up
        # (2.92.2: which switches go on the bar is asked when you enable the overlay, not at start)
        root.after(3000, self.ovr_restore)           # 2.91.0: the exchange rates window, if it's on
        root.after(10 * 60 * 1000, self.rm_ask_tick)  # 2.96.0: Help rate mods? (once; Not now = once more, later)
        self.dup_pending, self.dup_win, self.own_clip = [], None, ""
        self.tray = Tray(lambda what: self.ui_q.put(("tray", what)))
        self.in_tray = False
        root.bind("<Unmap>", self.on_unmap)
        root.bind("<Map>", self.on_map, add="+")          # 1.35: always (also guards against minimizes you didn't ask for)
        root.bind("<Configure>", self._remember_rect, add="+")   # 1.42: where the title bar was BEFORE a minimize
        self._last_rect = None
        self.apply_topmost()
        root.after(800, self.apply_topmost)
        root.after(6000, self.startup_update_check)          # 2.0 beta 7: only if turned on in Settings            # again once the window is on screen (some systems drop it before)
        if SETTINGS.get("tray", True):
            if not self.tray.available:
                self.status_text = ("System tray is off: run  py -m pip install pystray pillow  and restart to minimize "
                                    "to the tray.  ") + self.status_text

    # ---------------- system tray
    def on_map(self, e):
        """The app's window is back: so are its windows (2.0 beta 13: they are real windows of their own)."""
        if e.widget is self.root and hasattr(self, "shell"):
            self.root.after(30, self.shell.show_all)
            self.root.after(60, self.shell.check_owners)      # 2.10.2: maximise / restore / snap

    def on_unmap(self, e):
        if e.widget is not self.root or self.in_tray:
            return
        if self.root.state() != "iconic":
            return
        if hasattr(self, "shell") and sys.platform != "win32":
            self.shell.hide_all()        # (Windows hides and brings back a minimised window's own windows itself)
        if SETTINGS.get("on_top", True) and not self.user_minimized():
            self.root.after(80, self.unminimize)    # minimized without you asking: bring it straight back
            return
        if SETTINGS.get("tray", True) and self.tray.available:
            self.root.after(50, self.go_tray)

    def user_minimized(self):
        """Did YOU minimize the window? Esc, its minimize button or taskbar button (the mouse is there), or a Win-key
        shortcut (Win+D / Win+M / Win+Down) count. Anything else (another program, a game going fullscreen) doesn't."""
        if time.time() < getattr(self, "min_ok_until", 0):
            return True
        if time.time() - getattr(self, "last_unmin", 0) < 8:
            return True                                              # minimized again right after a bring-back: that's you
        if sys.platform != "win32":
            return True
        try:
            import ctypes
            from ctypes import wintypes
            u = ctypes.windll.user32
            if u.GetAsyncKeyState(0x5B) & 0x8000 or u.GetAsyncKeyState(0x5C) & 0x8000:
                return True                                          # a Win key is held
            pt = wintypes.POINT()
            u.GetCursorPos(ctypes.byref(pt))
            # 1.42: a minimized window has already moved off screen (-32000), so use where it was just before
            left, top, right = self._last_rect or (0, 0, -1)
            if left <= pt.x <= right and top - 10 <= pt.y <= top + 60:
                return True                                          # on our title bar: the minimize button
            u.WindowFromPoint.argtypes = [wintypes.POINT]
            u.WindowFromPoint.restype = wintypes.HWND
            u.GetAncestor.restype = wintypes.HWND
            top = u.GetAncestor(u.WindowFromPoint(pt), 2)            # GA_ROOT
            buf = ctypes.create_unicode_buffer(64)
            u.GetClassNameW(top, buf, 64)
            return buf.value in ("Shell_TrayWnd", "Shell_SecondaryTrayWnd")    # the taskbar
        except Exception:
            return True                                              # can't tell: never fight you

    def _remember_rect(self, e=None):
        if e is not None and e.widget is not self.root:
            return
        try:
            if self.root.state() == "iconic":
                return
            if sys.platform == "win32":
                import ctypes
                from ctypes import wintypes
                rc = wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(self._hwnd(), ctypes.byref(rc))
                if rc.left > -30000:
                    self._last_rect = (rc.left, rc.top, rc.right)
            else:
                x, y = self.root.winfo_rootx(), self.root.winfo_rooty()
                self._last_rect = (x, y - 30, x + self.root.winfo_width())
        except Exception:
            buglog.caught()

    def _hwnd(self):
        try:
            return int(self.root.wm_frame(), 16)
        except Exception:
            import ctypes
            return ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()

    def unminimize(self):
        """Show the window again WITHOUT taking the keyboard away from whatever you are doing (the game)."""
        if self.in_tray or self.root.state() != "iconic":
            return
        try:
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.ShowWindow(self._hwnd(), 4)    # SW_SHOWNOACTIVATE
            else:
                self.root.deiconify()
        except Exception:
            self.root.deiconify()
        self.apply_topmost()
        self.last_unmin = time.time()
        self.unmin_count = getattr(self, "unmin_count", 0) + 1
        self._say("The window was minimized without you asking, so it was brought back. Minimize it again (or press "
                  "Esc) and it will stay minimized.", 10)

    def apply_topmost(self):
        on = bool(SETTINGS.get("on_top", True))
        try:
            self.root.attributes("-topmost", on)
            from .overlaywin import OverlayWindow
            from .shell import DeskWindow
            for w in self.root.winfo_children():                     # our own pop-up windows stay above it
                # (2.0 beta 17: not the desktop's windows - they belong to the app's window and stay with it - and not
                # the note / timer, which are always over the game)
                if isinstance(w, tk.Toplevel) and not isinstance(w, (DeskWindow, OverlayWindow)) and w.winfo_exists():
                    w.attributes("-topmost", on)
            if hasattr(self, "shell"):                   # 2.7.1: the desktop's windows follow, and stay above it
                self.shell.restack()
                if not getattr(self, "_restack_bound", False):
                    self._restack_bound = True          # clicking the app's own window mustn't bury them again
                    self.root.bind("<FocusIn>", self._restack_soon, add="+")
        except Exception:
            buglog.caught()

    def _restack_soon(self, e=None):
        if e is not None and e.widget is not self.root:
            return
        if getattr(self, "_restack_job", None):          # (2.7.2: with Always on top off too)
            return

        def go():
            self._restack_job = None
            try:
                self.shell.restack()
            except Exception:
                buglog.caught()
        self._restack_job = self.root.after(30, go)

    def _top_label(self):
        on = bool(self.top_var.get())
        if getattr(self, "pin_lbl", None) is not None:
            self.pin_lbl.config(fg=C["accent"] if on else "#4a5a78")

    def on_top_toggle(self):
        SETTINGS["on_top"] = bool(self.top_var.get())
        save_json("settings.json", SETTINGS)
        self._top_label()
        self.hdr_layout()
        self.apply_topmost()
        self._say("Always on top is " + ("on: the window stays in front and comes back if something minimizes it."
                                         if SETTINGS["on_top"] else "off."), 8)

    def go_tray(self):
        if self.in_tray or self.root.state() != "iconic":
            return
        if self.tray.show_icon():
            self.in_tray = True
            if hasattr(self, "shell"):
                self.shell.hide_all()
            self.root.withdraw()

    def ev_tray(self, what):
        if what == "show":
            self.in_tray = False
            self.tray.hide_icon()
            self.root.deiconify()
            self.root.state("normal")
            self.root.lift()
            self.root.focus_force()
            if hasattr(self, "shell"):
                self.root.after(30, self.shell.show_all)
        elif what == "updates":                         # 2.100.0: the tray's Check for updates - the app comes back
            self.ev_tray("show")                         # first, so the answer shows over it
            self.root.after(300, lambda: self.check_updates("ask"))
        elif what == "quit":
            self.tray.hide_icon()
            self.on_close()

    # ---------------- layout (2.0 beta 7: a desktop with a window per module, see shell.py and modules/)
    def build(self):
        r = self.root
        r.configure(bg=C["bg"])
        self.PAGES = [PAGE_CHECKS, "Wealth", "Mod Book", "Regex", "Notes",
                      "Settings"]
        self.page_var = tk.StringVar(value=PAGE_CHECKS)           # the window in front (kept for older code)
        self.top_var = tk.BooleanVar(value=SETTINGS.get("on_top", True))
        self.league_var = tk.StringVar(value=SETTINGS["league"])
        self.total_txt = ""
        if "labs" not in SETTINGS:                   # 2.0 beta 10: Labs on for whoever already uses Wealth / the tracker
            SETTINGS["labs"] = bool(WEALTH.tabs or WEALTH.holdings or WEALTH.snapshots or os.path.exists(P("sessions.json")))
        self.shell = Shell(self, r, SETTINGS, lambda: save_json("settings.json", SETTINGS))
        self.parent_dialogs()
        self.mods = modules.load(self)
        self.page_key = {m.title: m.key for m in self.mods}
        self.page_key["Utilities"] = "notes"                      # 2.0 beta 6 name
        self.page_key["Item library"] = "library"                 # its names before 2.0 beta 13
        self.page_key["Item inspector"] = "library"
        self.page_key["Price breakdown"] = "library"
        for old, key in (("Mod book", "modbook"), ("Map library", "maps"), ("Exchange rates", "rates"),
                         ("Game search", "search"), ("Under the hood", "library")):
            self.page_key.setdefault(old, key)                    # 2.120.0: their names before Title Case
        for m in self.mods:
            m.body = self.shell.register(m)
        self.shell.link_children()                                # 2.32.0: child tools under their parent
        _splash_step(i=1)
        for m in self.mods:
            _splash_step(f"Building {m.title}", i=1)
            try:
                m.build(m.body)
            except Exception:
                self.log_error(f"building {m.title}")
                raise

        # ---- status line (above the taskbar): messages, exchange rates, trade-site limits
        strip = self.shell.strip
        from . import themes as _th
        self.limit_lbl = tk.Label(strip, text="", bg=C["bg"], fg=C["muted"], padx=16, cursor="hand2", font=(MONO, 9))
        self.limit_lbl.bind("<Button-1>", self.open_limits)      # (2.60.0: the meters below say it; kept for code)
        # 2.120.0 (UX pass 2: "Search ◇◇◇◇◇ 0/5 (10s)" was jargon): one pill - Trade site: ready / wait 8s /
        # paused 2:30 - with the numbers when you point at it (2.60.0 - 2.119.0 had two meters, Search and Fetch)
        _meter_ws = [tk.Frame(strip, bg=C["bg"], width=8)]
        _meter_ws[0].pack(side="right")
        self.limit_pill = tk.Label(strip, text="● Trade site: ready", bg=C["bg"], fg=C["muted"], cursor="hand2",
                                   font=("Segoe UI", 9), padx=8)
        self.limit_pill.pack(side="right", padx=(16, 0))
        self.limit_pill.bind("<Button-1>", self.open_limits)
        self.limit_tip = Tooltip(self.limit_pill, "")
        _meter_ws.append(self.limit_pill)
        self.rates_lbl = tk.Label(strip, text="Rates: …", bg=C["bg"], fg=C["muted"], padx=8, cursor="hand2", font=("Segoe UI", 9))   # P1: one font in the bar
        self.rates_lbl.pack(side="right")
        self.rates_lbl.bind("<Button-1>", self.open_rates)
        self.status = tk.Label(strip, text="Starting...", anchor="w", bg=C["bg"], fg=C["muted"], padx=16, pady=4)
        self.status.pack(side="left", fill="x", expand=True)
        self._strip_all = [w for w in strip.pack_slaves() if w in _meter_ws or w is self.rates_lbl]   # (pack order;
        # only the meters and Rates - the taskbar's own pieces are never touched)
        self._strip_pk = {w: {k: v for k, v in w.pack_info().items() if k != "in"} for w in self._strip_all}

        def strip_fit():                                       # 2.98.0: the status message keeps its room - the
            narrow = strip.winfo_width() < 1250               # trade-limit meters step aside in a narrow window
            hide = [w for w in self._strip_all if w is not self.rates_lbl]   # (a click on Rates / the limits
            shown = any(w.winfo_manager() for w in hide)                       # window still has them)
            if narrow and shown:
                for w in hide:
                    w.pack_forget()
            elif not narrow and not shown:
                for w in self._strip_all:
                    w.pack_forget()
                for w in self._strip_all:
                    w.pack(**self._strip_pk[w], before=self.status)
        strip.bind("<Configure>", lambda e: e.widget is strip and strip_fit(), add="+")

        # ---- taskbar, right side: league (opens Settings), clock (2.97.3: no utility dots, no 📌)
        tb = "#111b30"
        self.league_chip = tk.Label(self.shell.task_right, text="", bg="#162544", fg=C["good"], padx=8, pady=4,
                                    cursor="hand2", font=("Segoe UI", 9, "bold"), highlightthickness=1,
                                    highlightbackground="#3d5582")
        self.shell.add_status(self.league_chip)
        self.league_chip.bind("<Button-1>", lambda e: self.shell.open("settings"))
        self.league_var.trace_add("write", lambda *a: self._league_chip())
        self._league_chip()
        self.build_feedback()                                  # 2.48.0: ⬆ Update badge, 🐞 Report a bug
        self.shell.make_task_dots()
        # (2.97.3, feedback: no 📌 on the status bar - Always on top is in Settings › General › Window)
        self._top_label()
        from . import shell as _shell
        _shell.CLOCK["format"] = SETTINGS.get("clock_format", "auto")
        _splash_step(i=2)
        self.shell.finish()
        self.shell.set_launcher(self.shell.cfg.get("launcher", "dock"))
        self.root.after(60, self.restore_zoom)                 # 2.23.1: maximised last time -> maximised again
        self.root.after(1500, self.show_whatsnew)              # 2.0 beta 12: once per new version
        self.root.after(4000, self.board_name_check)           # 2.85.0: your community name, asked once (2.86.1: or again if reset)
        if SPLASH[0] is not None:                              # 2.0.0: the start-up screen waits for the mod list,
            _splash_step(i=3)                                  # but never more than 3 seconds
            self.root.after(3000, self.close_splash)
        self.bind_hotkeys()
        self.refresh_total_header()

    # ---------------- welcome / what's new (once per version)
    def show_whatsnew(self, force=False):
        from .whatsnew import INTRO, notes_between, split_notes
        if SPLASH[0] is not None and not force:            # after the start-up screen
            self.root.after(500, self.show_whatsnew)
            return
        seen = SETTINGS.get("seen_version")
        if not force and seen == APP_VERSION:
            return
        if not seen and not force and self.show_quickstart():     # 2.10.0: a fresh install gets the quick start
            return
        notes = notes_between(None if force or not seen else seen, APP_VERSION)
        self._wn_h = None
        old = getattr(self, "_whatsnew", None)
        if old is not None and old.winfo_exists():
            old.destroy()
        P1, P2 = C["panel"], C["panel2"]
        card = tk.Toplevel(self.root, bg=C["accent"], padx=2, pady=2)      # a real window: always above the others
        card.overrideredirect(True)
        try:
            card.transient(self.root)
        except tk.TclError:
            pass
        self._whatsnew = card
        self.whatsnew_follow()
        inner = tk.Frame(card, bg=P1)
        inner.pack(fill="both", expand=True)
        # 2.111.0: the card follows the app theme (C tokens only); big changes are hero rows, the rest fold away
        head = tk.Frame(inner, bg=P2, padx=16, pady=12)
        head.pack(fill="x")
        welcome = not seen and not force
        # 2.116.0 (P10): the version once - "What's new · 2.116.0", then what you had and how many updates
        tk.Label(head, text="Welcome to StashOfExile2" if welcome else f"What's new  ·  {pretty_version()}",
                 bg=P2, fg=C["text"], font=(FONT_TITLE, 16, "bold"), anchor="w").pack(fill="x")
        ups = f"  ·  {len(notes)} updates" if len(notes) > 1 else ""
        tk.Label(head, text=f"version {pretty_version()}" if welcome or not seen or force else
                 f"you had {pretty_version(seen)}{ups}", bg=P2, fg=C["muted"], anchor="w").pack(fill="x")
        tk.Frame(inner, bg=C["accent"], height=2).pack(fill="x")
        if welcome:                                             # first start: pick your league right away
            lrow = tk.Frame(inner, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["accent"])
            lrow.pack(fill="x", padx=12, pady=(8, 0))
            tk.Label(lrow, text="Which league do you play?", bg=P2, fg=C["accent"],
                     font=("Segoe UI", 12, "bold")).pack(side="left")
            self.wn_league = self.league_link(lrow, P2)     # 2.59.0: set in one place - Settings › General
            self.wn_league.pack(side="left", padx=8)
            tk.Label(inner, text="The newest league is picked for you. Prices come from this league; click it to "
                                 "change it in Settings › General.", bg=P1, fg=C["muted"], font=("Segoe UI", 9),
                     anchor="w", padx=16).pack(fill="x", pady=(4, 0))
        foot = tk.Frame(inner, bg=P1, padx=16, pady=8)
        foot.pack(fill="x", side="bottom")
        ttk.Button(foot, text="Got it", style="Primary.TButton", command=self.close_whatsnew).pack(side="right")
        tk.Label(foot, text="Shows once per version. Toolkit menu > What's new brings it back.", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9)).pack(side="left")
        t = tk.Text(inner, bg=P1, fg=C["text"], relief="flat", wrap="word", padx=12, pady=8, highlightthickness=0,
                    font=("Segoe UI", 10), cursor="arrow")
        t.pack(fill="both", expand=True, padx=0, pady=(4, 0))
        self.wn_text = t
        t.tag_configure("h", foreground=C["accent"], font=("Segoe UI", 12, "bold"), spacing1=8, spacing3=4)
        t.tag_configure("p", spacing3=8, lmargin1=4, lmargin2=4)
        t.tag_configure("li", spacing3=4, lmargin1=12, lmargin2=26, foreground=C["text"])
        t.tag_configure("area", foreground=C["muted"])
        t.tag_configure("fold", foreground=C["text"], font=("Segoe UI", 10, "bold"), spacing1=8, spacing3=4)
        t.tag_configure("foldhint", foreground=C["muted"], font=("Segoe UI", 9))
        if welcome or force:
            t.insert("end", "What it is\n", "h")
            for line in INTRO:
                t.insert("end", line + "\n", "p")
        big, small = split_notes(notes)
        self.wn_heroes = []
        self.wn_small = small
        t.bind("<Configure>", lambda e: self.wn_fit(e.width))
        for icon, title, text, go in big:
            t.window_create("end", window=self._wn_hero(t, icon, title, text, go), padx=4, pady=4)
            t.insert("end", "\n")
        if small:
            self.wn_small_open = False
            areas = ", ".join(dict.fromkeys(a for a, _ in small if a))
            t.mark_set("wn_fold", "end-1c")
            t.mark_gravity("wn_fold", "left")
            t.insert("end", f"▸  {len(small)} smaller change{'s' if len(small) != 1 else ''}", ("fold", "foldbtn"))
            t.insert("end", f"   {areas}\n" if areas else "\n", ("foldhint", "foldbtn"))
            t.mark_set("wn_small", "end-1c")
            t.mark_gravity("wn_small", "left")
            t.tag_bind("foldbtn", "<Button-1>", lambda _e: self.wn_toggle_small())
            t.tag_bind("foldbtn", "<Enter>", lambda _e: t.config(cursor="hand2"))
            t.tag_bind("foldbtn", "<Leave>", lambda _e: t.config(cursor="arrow"))
            if not big:                                     # (nothing big: the small ones show at once)
                self.wn_toggle_small()
        # (2.4.0: "Coming next" is no longer shown here - the plan lives in ROADMAP.md)
        t.config(state="disabled")
        card.lift()

    def _wn_hero(self, t, icon, title, text, go):
        """2.111.0: one big change on the What's new card - an icon, a bold title, a line, and a link to it."""
        P2 = C["panel2"]
        row = tk.Frame(t, bg=P2, highlightthickness=1, highlightbackground=C["line"])
        tk.Frame(row, bg=C["accent"], width=4).pack(side="left", fill="y")
        tk.Label(row, text=icon, bg=P2, fg=C["accent"], font=("Segoe UI Symbol", 16), width=2).pack(
            side="left", padx=(8, 4), pady=8, anchor="n")
        body = tk.Frame(row, bg=P2)
        body.pack(side="left", fill="both", expand=True, padx=(4, 12), pady=8)
        tk.Label(body, text=title, bg=P2, fg=C["text"], font=("Segoe UI", 12, "bold"), anchor="w",
                 justify="left").pack(fill="x")
        msg = tk.Label(body, text=text, bg=P2, fg=C["muted"], font=("Segoe UI", 10), anchor="w", justify="left",
                       wraplength=520)
        msg.pack(fill="x")
        strut = tk.Frame(body, bg=P2, height=1, width=max(300, t.winfo_width() - 90))   # (the row fills the card)
        strut.pack(anchor="w")
        strut._wn_strut = True
        if go:
            label, target = go
            link = tk.Label(body, text=label + "  ›", bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold"),
                            cursor="hand2", anchor="w")
            link.pack(fill="x", pady=(2, 0))
            link.bind("<Button-1>", lambda _e, g=target: self.wn_go(g))
        msg._wn_wrap = True
        self.wn_heroes.append(row)
        return row

    def wn_fit(self, width):
        """The hero rows fill the card's width and wrap their line to it."""
        for r in getattr(self, "wn_heroes", []):
            if not r.winfo_exists():
                continue
            for b in r.winfo_children():
                for w in b.winfo_children():
                    if getattr(w, "_wn_wrap", False):
                        w.config(wraplength=max(200, width - 110))
                    elif getattr(w, "_wn_strut", False):
                        w.config(width=max(300, width - 90))

    def wn_go(self, target):
        """A hero row's link: 'settings:<tab>' opens that Settings tab, anything else is a page key."""
        if target.startswith("settings:"):
            self.open_settings_tab(target.split(":", 1)[1])
        else:
            self.shell.open(target)

    def wn_toggle_small(self):
        """▸ N smaller changes: unfolds into one line each (area · what changed); click again to fold."""
        t, small = self.wn_text, self.wn_small
        t.config(state="normal")
        self.wn_small_open = not self.wn_small_open
        t.delete("wn_fold", "wn_fold +1c")
        t.insert("wn_fold", "▾" if self.wn_small_open else "▸", ("fold", "foldbtn"))
        if self.wn_small_open:
            for area, line in small:
                if area:
                    t.insert("end", "•  ", "li")
                    t.insert("end", area + " · ", ("li", "area"))
                    t.insert("end", line + "\n", "li")
                else:
                    t.insert("end", "•  " + line + "\n", "li")
        else:
            t.delete("wn_small", "end-1c")
        t.config(state="disabled")

    def whatsnew_follow(self):
        w = getattr(self, "_whatsnew", None)
        if w is None or not w.winfo_exists():
            return
        ox, oy = self.shell.desk_origin()
        dw, dh = max(300, self.shell.desk.winfo_width()), max(300, self.shell.desk.winfo_height())
        ww, hh = min(660, dw - 20), min(getattr(self, "_wn_h", None) or 600, dh - 20)
        w.geometry(f"{ww}x{hh}+{ox + (dw - ww) // 2}+{oy + (dh - hh) // 2}")

    def keep_on_top(self):
        """The welcome / what's new card stays above the windows until you press Got it."""
        w = getattr(self, "_whatsnew", None)
        if w is not None and w.winfo_exists():
            w.lift()

    def close_whatsnew(self):
        SETTINGS["seen_version"] = APP_VERSION
        save_json("settings.json", SETTINGS)
        w = getattr(self, "_whatsnew", None)
        if w is not None:
            w.destroy()
            self._whatsnew = None

    def _league_chip(self):
        self.league_chip.config(text="⚑ " + (self.league_var.get() or "pick a league"))

    def menu_subtitle(self):
        from .config import TAGLINE                    # 2.73.2
        return f"{TAGLINE}  ·  v{pretty_version()}  ·  {self.league_var.get() or 'no league picked'}"

    def on_focus_module(self, key):
        """A window came to the front (shell.py calls this)."""
        mod = next((m for m in self.mods if m.key == key), None) if hasattr(self, "mods") else None
        if mod is not None:
            self.page_var.set(mod.title)
        if key == "regex" and hasattr(self, "rx_refresh_values"):       # 2.0 beta 20: Mod book changes show there
            self.rx_refresh_values()

    def page_open(self, title):
        """Is that module's window open (on the desktop, not minimised)?"""
        sh = getattr(self, "shell", None)
        return sh is None or sh.is_open(self.page_key.get(title, title))

    # ---------------- the Price checks window
    def build_checks(self, body):
        self.checks_body = body
        # ---- the summary line: total value of the list + priced / needs review
        summ = tk.Frame(body, bg=C["panel2"], padx=12, pady=4)      # 2.74.5: lighter padding all over the page
        summ.pack(fill="x")
        self.tot_lbl = tk.Label(summ, text="", bg=C["panel2"], fg="#9fb6dd", font=("Segoe UI", 9, "bold"))
        self.tot_val = tk.Label(summ, text="", bg=C["panel2"], fg=C["good"], font=("Segoe UI", 16, "bold"))
        self.chip_priced = tk.Label(summ, text="", bg=C["panel2"], fg=C["green"], font=("Segoe UI", 9, "bold"), padx=8, pady=4,
                                    highlightthickness=1, highlightbackground=C["green"])
        self.chip_review = tk.Label(summ, text="", bg=C["warn_bg"], fg=C["good"], font=("Segoe UI", 9, "bold"), padx=8, pady=4,
                                    highlightthickness=1, highlightbackground=C["accent"])
        # 2.26.0: "pricing 12 items - about 1:30 left", next to the other two (was only in the status line)
        self.chip_eta = tk.Label(summ, text="", bg="#10203a", fg="#8fc4ff", font=("Segoe UI", 9, "bold"), padx=8,
                                 pady=4, highlightthickness=1, highlightbackground="#3f5f8f")
        self.tot_lbl.pack(side="left")
        self.tot_val.pack(side="left", padx=(8, 0))
        self.chip_review.pack(side="right")
        self.chip_priced.pack(side="right", padx=(0, 8))
        # 2.74.5: the Valuable mods legend chip is gone (clutter) - the column's ★ explains itself on hover
        # 2.31.0: how much the community Mod book knows (shown once there is something)
        self.cm_chip = tk.Label(summ, text="", bg="#10203a", fg="#8fc4ff", font=("Segoe UI", 9), padx=8, pady=4,
                                highlightthickness=1, highlightbackground="#3f5f8f")
        self.root.after(3000, self.cm_paint)

        # ---- the toolbar (2.63.0: row 1 = what to do, row 2 = what to show; the mode row comes first)
        tb = tk.Frame(body, bg=C["panel"], highlightthickness=1, highlightbackground=C["line"])
        tb.pack(fill="x", padx=8, pady=4)
        self.price_tb = tb
        bar = tk.Frame(tb, bg=C["panel"], height=1)          # (the first row's place: Add items from goes before it)
        bar.pack(fill="x")
        bar2 = tk.Frame(tb, bg=C["panel"], padx=8, pady=4)
        bar2.pack(fill="x")
        lab = dict(bg=C["panel2"], fg=C["muted"])
        # 2.74.5: the actions share the filters' row (one row less), right side first: never squeezed out
        ttk.Button(bar2, text="Export CSV", command=self.export, style="Quiet.TButton").pack(side="right")
        self.pause_btn = ttk.Button(bar2, text="Pause", command=self.toggle_pause, width=8)
        self.pause_btn.pack(side="right", padx=8)
        ttk.Button(bar2, text="⟳ Re-price all", style="Primary.TButton", command=self.reprice_all).pack(side="right")
        # 2.59.0: Valuable mod, Popups, Sound, Copy name, Listings, Listed within, Prices in and the account live in
        # Settings › Price checking - the toolbar only links there (one home for each setting). 2.74.5: on the top
        # strip, after the total
        self.pc_vars()
        self.pc_rules_lbl = tk.Label(summ, text="", **lab)
        self.pc_rules_lbl.pack(side="left", padx=(16, 0))
        self.pc_set_link = tk.Label(summ, text="⚙", bg=C["panel2"], fg=C["accent"], cursor="hand2",
                                    font=("Segoe UI Symbol", 10))
        self.pc_set_link.pack(side="left", padx=(8, 0))
        self.pc_set_link.bind("<Button-1>", lambda e: self.settings_open("Price checking"))
        Tooltip(self.pc_set_link, "Settings › Price checking")
        self.pc_rules_text()
        self.view_var = tk.StringVar(value=SETTINGS["view"])
        self.build_tab_reader(tb)                                # 2.8.0: Add items from Ctrl+Alt+C | Stash tab

        # ---- row 2: the list filters (2.0 beta 3) + 2.63.0 search and "only ★"
        frow = bar2                                         # (2.103.1, feedback: always on screen, as before)
        flab = dict(bg=C["panel"], fg=C["muted"])
        # 2.105.0: no "Show: Not yet listed / Listed / Sold / Removed" (listing marks are gone) - every item shows
        self.cat_var, self.rar_var, self.type_var = tk.StringVar(value=self.ALL_CATS), tk.StringVar(value="All"), tk.StringVar(value="All")
        self.cat_box = ttk.Combobox(frow, textvariable=self.cat_var, state="readonly", width=13)
        self.rar_box = ttk.Combobox(frow, textvariable=self.rar_var, state="readonly", width=8)
        self.type_box = ttk.Combobox(frow, textvariable=self.type_var, state="readonly", width=11)
        for label, box, pad in (("Category", self.cat_box, 14), ("Rarity", self.rar_box, 10), ("Type", self.type_box, 10)):
            tk.Label(frow, text=label, **flab).pack(side="left", padx=(pad, 6))
            box.pack(side="left")
        self.cat_box.bind("<<ComboboxSelected>>", lambda e: self.on_cat(changed="cat"))
        self.rar_box.bind("<<ComboboxSelected>>", lambda e: self.on_cat(changed="rar"))
        self.type_box.bind("<<ComboboxSelected>>", lambda e: self.on_cat(changed="type"))
        for cb in (self.cat_box, self.rar_box, self.type_box):
            cb.bind("<<ComboboxSelected>>", lambda e: self.root.after(20, self.root.focus_set), add="+")
        self.star_var = tk.BooleanVar(value=False)          # 2.74.5: the "Only ★" switch is gone (kept off)
        # 2.26.4: was "Show all" - it clears Category / Rarity / Type / search / ★, and only lights up when one is set
        self.clear_btn = ttk.Button(frow, text="✕ Clear filters", command=self.cat_reset, state="disabled")
        self.clear_btn.pack(side="left", padx=(12, 0))
        ttk.Button(frow, text="↕ Order added", command=self.sort_added).pack(side="left", padx=(16, 0))   # 2.103.2: room   # 2.0 beta 22
        self.search_var = tk.StringVar()                    # 2.63.0: find by name, base, type or mod text
        srow = self.pc_mode.master                          # (on the first row, right of "Add items from")
        self.search_box = ttk.Entry(srow, textvariable=self.search_var, width=26)
        self.search_box.pack(side="right")
        tk.Label(srow, text="🔍 Search", **flab).pack(side="right", padx=(12, 8))
        self.search_var.trace_add("write", lambda *a: self.on_filter_text(soon=True))
        self.search_box.bind("<Escape>", lambda e: (self.search_var.set(""), "break")[1])
        from .style import flowify                          # 2.98.0: these rows wrap in a narrow window
        flowify(srow)
        flowify(bar2)

        # ---- the key bar, at the bottom of this window (claims its space first)
        kbf = tk.Frame(body, bg=C["panel"])
        kbf.pack(fill="x", side="bottom")
        self.build_keybar(kbf)
        self.banner = tk.Label(body, text="", anchor="w", padx=12, pady=2, font=("Segoe UI", 9), justify="left")

        # ---- the list (left) and the item (right), each under its own header strip
        items_tab = tk.Frame(body, bg=C["panel"])
        items_tab.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self.checks_area = items_tab                       # cards and banners go just above it
        self.pane = ttk.PanedWindow(items_tab, orient="horizontal")        # drag the divider to resize
        self.pane.pack(fill="both", expand=True)
        lcol = tk.Frame(self.pane, bg=C["panel"])
        self.pane.add(lcol, weight=1)
        self.list_head = SectionBar(lcol, "Items")
        self.list_head.pack(fill="x")
        self.cat_count = tk.Label(lcol, text="")             # (not shown - its text is the strip's note)
        # under the list: what to do with the picked rows
        acts = tk.Frame(lcol, bg=C["panel"], pady=4)
        acts.pack(fill="x", side="bottom")
        ttk.Button(acts, text="Clear list", command=self.clear, style="Danger.TButton").pack(side="right")  # (2.103.1: back)
        self.delete_btn = ttk.Button(acts, text="🗑 Delete", command=self.remove_selected, style="Danger.TButton", state="disabled")      # 2.0 beta 19
        self.delete_btn.pack(side="right", padx=8)
        self.remove_btn = ttk.Button(acts, text="✖ Mark removed", command=lambda: self.mark_selected("removed"), state="disabled")
        self.mark_btn = ttk.Button(acts, text="✔ Mark listed", command=lambda: self.mark_selected("listed"), state="disabled")
        # 2.105.0 (feedback: nobody marks items listed / sold / removed): those buttons aren't shown any more
        self.undo_btn = ttk.Button(acts, text="↺ Undo", command=self.undo_mark, state="disabled", width=7, style="Quiet.TButton")
        self.undo_btn.pack(side="right")
        self.undo = []                                   # [(record id, previous mark, previous listed-at)] of the last mark
        flowify(acts)
        vp = Viewport(lcol)
        vp.pack(fill="both", expand=True)
        left = vp.body
        self.tree = ttk.Treeview(left, columns=[c[0] for c in self.COLS], show="headings", selectmode="extended")
        self.tree.menu_actions = self.checks_menu_actions          # 2.36.0: right-click / Menu key
        for cid, title, w, anchor in self.COLS:
            self.tree.heading(cid, text=title, command=lambda c=cid: self.sort_by(c))
            self.tree.column(cid, width=max(int(SETTINGS.get("col_widths", {}).get(cid, w)), 95 if cid == "conf" else 0), minwidth=50,
                             anchor=anchor, stretch=(cid == "match"))
        self.tree["displaycolumns"] = self.SHOW_COLS
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("good", foreground=C["good"])
        self.tree.tag_configure("pending", foreground=C["muted"])
        self.tree.tag_configure("error", foreground=C["red"])
        self.tree.tag_configure("nomatch", foreground=C["red"], font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("even", background=C["panel"])
        self.tree.tag_configure("odd", background=C["odd"])
        self.tree.tag_configure("listed", foreground=C["green"])
        self.tree.tag_configure("removed", foreground=C["muted"])
        self.tree.tag_configure("sold", foreground="#7fe0c0")              # 2.21.0
        self.tree.bind("<<TreeviewSelect>>", self._on_select_soon)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.update_mark_buttons(), add="+")   # 2.103.1: lit at once
        self.tree.bind("<Double-1>", lambda e: self.open_trade())
        # 2.63.0: the item shows in the panel on the right - no more pop-up box over the list
        from .chrome import EmptyState                    # 2.120.0: one empty look everywhere
        self.empty_lbl = EmptyState(left, "⚖", self.empty_text)
        self.empty_lbl.place(relx=0.5, rely=0.45, anchor="center")
        left.bind("<Configure>", lambda e: self.empty_lbl.config(wraplength=max(200, min(420, e.width - 80))),
                  add="+")   # 2.98.0

        pw = int(SETTINGS.get("panel_w", 430) or 430)
        if pw < 250:                   # 2.0 beta 22: bring back an item panel that was saved squeezed to nothing
            pw = SETTINGS["panel_w"] = 430
        outer = tk.Frame(self.pane, bg=C["panel2"], width=min(pw, 900))
        outer.pack_propagate(False)
        self.pane.add(outer, weight=0)

        def keep_panel(_e=None):                       # 2.0 beta 22: the item panel can't be dragged out of sight
            try:
                w = self.pane.winfo_width()
                if w > 500 and w - self.pane.sashpos(0) < 260:
                    self.pane.sashpos(0, w - 300)
            except tk.TclError:
                pass
        self.pane.bind("<ButtonRelease-1>", keep_panel, add="+")
        self.outer = outer
        self.item_head = SectionBar(outer, "Item")
        self.item_head.pack(fill="x", padx=(8, 0))
        # 2.63.0: the picked item's own buttons, at the foot of its panel
        ifoot = tk.Frame(outer, bg=C["panel2"], pady=8)       # 2.79.0: not shown - the card has these (no duplicates)
        self.item_trade_btn = ttk.Button(ifoot, text="Trade Site", command=self.open_trade, state="disabled")
        self.item_trade_btn.pack(side="left", padx=(8, 0))
        self.item_mark_btn = ttk.Button(ifoot, text="✔ Mark listed", command=lambda: self.mark_selected("listed"),
                                        state="disabled")
        self.item_mark_btn.pack(side="right", padx=(0, 8))
        ivp = Viewport(outer, bg_key="panel2")
        ivp.pack(fill="both", expand=True, padx=(8, 0))
        dsb = ttk.Scrollbar(ivp.body, orient="vertical")
        dsb.pack(side="right", fill="y")
        self.dcanvas = tk.Canvas(ivp.body, bg=C["panel2"], highlightthickness=0, yscrollcommand=dsb.set)
        self.dcanvas.pack(side="left", fill="both", expand=True)
        dsb.config(command=self.dcanvas.yview)
        self.detail = tk.Frame(self.dcanvas, bg=C["panel2"], padx=16, pady=12)
        win = self.dcanvas.create_window((0, 0), window=self.detail, anchor="nw")
        self._dwin = win
        self.dcanvas.bind("<Configure>", self._canvas_resized)
        self.detail.bind("<Configure>", lambda e: self.dcanvas.configure(scrollregion=self.dcanvas.bbox("all")))

        def wheel(e):
            d = -1 if (getattr(e, "delta", 0) > 0 or e.num == 4) else 1
            if self.detail.winfo_reqheight() > self.dcanvas.winfo_height():
                self.dcanvas.yview_scroll(d * 2, "units")
        outer.bind("<Enter>", lambda e: (outer.bind_all("<MouseWheel>", wheel), outer.bind_all("<Button-4>", wheel),
                                         outer.bind_all("<Button-5>", wheel)))
        outer.bind("<Leave>", lambda e: (outer.unbind_all("<MouseWheel>"), outer.unbind_all("<Button-4>"),
                                         outer.unbind_all("<Button-5>")))
        self.show_detail(None)

    # ---------------- the Mod book window: what the app learned + your mod rules
    def build_modbook(self, book_tab):
        """2.99.0: one tab per rule set - Tablets, Jewels, Waystones, Relics, Gear (by item class), Uniques - each with
        its own "What the app learned" view (that tab is gone: its rows sit with the rules they belong to)."""
        self.mb_nb = SegBook(book_tab)                         # real buttons, not notebook tabs (2.0 beta 7)
        self.mb_nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.MEM_VIEWS = ["Mod priority", "Single mods", "Mod combinations", "Old mod book"]
        self.mem_view = tk.StringVar(value=self.MEM_VIEWS[0])
        self.mem_filter = tk.StringVar()
        self.mem_filter.trace_add("write", lambda *a: self.refresh_memory(True))
        self.mem_tv = None
        self.mb_show = {}
        tabs = {}
        for cat, title in self.MB_TABS:
            tabs[cat] = tk.Frame(self.mb_nb, bg=C["panel"])
            self.mb_nb.add(tabs[cat], text=title)
        feed_tab = tk.Frame(self.mb_nb, bg=C["panel"])                 # 2.51.0
        self.mb_nb.add(feed_tab, text="Manual feed")
        self.mb_nb.bind("<<NotebookTabChanged>>", lambda e: (self.refresh_rules(), self.refresh_memory()))
        if getattr(self, "shell", None) is not None:          # 2.64.0: its tabs are listed in the sidebar
            self.shell.register_tabs("modbook", self.mb_nb)
        for cat, _title in self.MB_TABS:
            rf, lf, show, _v = self.mb_split(tabs[cat], cat)
            if cat in ("gear", "unique"):
                self.build_picker_rules(rf, cat)
            else:
                self.build_rules_page(rf, cat)
            self.mb_learned(lf, self.rt[cat])
            self.mb_show[cat] = show
        self.build_feed(feed_tab)


    # (key, name, kind, low, high, step, what it does) - 2.59.0: Settings › Advanced › Fine tuning
    FINE = (("range_factor", "Search rolls from", "pct", 50, 100, 5, "% of your item's rolls (lower = more listings)"),
            ("min_results", "Fewest listings for a price", "int", 1, 20, 1, "fewer than this: no price, only a hint"),
            ("spread_warn", "Warn when prices spread", "int", 0, 200, 5, "times apart, cheapest to dearest (0 = off)"),
            ("stale_days", "Re-check a learned mod after", "int", 1, 60, 1, "days"),
            ("toast_secs", "Messages stay for", "int", 1, 60, 1, "seconds"),
            ("learn", "Learn new mods in the background", "bool", 0, 0, 0, "looks up each new mod's price, slowly"),
            ("tray", "Minimize to the system tray", "bool", 0, 0, 0, "takes effect when the app starts"),
            ("memory_shortcut", "Skip a search the Mod Book already agrees on", "bool", 0, 0, 0,
             "5+ identical searches in the last day"),
            ("model_shortcut", "Let the model price an item by itself", "bool", 0, 0, 0,
             "only after 100 checked guesses at 99 percent"))

    FINE_WINDOW = ("toast_secs", "tray")      # 2.116.0 (P10): on General › Window, not Price checking













    def dlg_parent(self):
        """The window a question / file box belongs to: the window in front (2.0 beta 21)."""
        sh = getattr(self, "shell", None)
        w = sh.windows.get(sh.active) if sh is not None and sh.active else None
        try:
            if w is not None and w.state_ == "open" and w.winfo_ismapped():
                return w
        except tk.TclError:
            pass
        return self.root

    def parent_dialogs(self):
        """2.0 beta 21: every "Are you sure?" / file box opens over the window you are using. They belonged to the
        app's main window, so a question asked from Wealth came up behind or instead of it (Wealth seemed to hide)."""
        from tkinter import filedialog as fd, messagebox as mb, simpledialog as sd
        if getattr(mb, "_soe2_parented", False):
            return
        app = self

        def wrap(fn):
            def call(*a, **kw):
                if kw.get("parent") is None:
                    kw["parent"] = app.dlg_parent()
                return fn(*a, **kw)
            return call
        for mod, names in ((mb, ("askyesno", "askokcancel", "askyesnocancel", "askquestion", "askretrycancel",
                                 "showinfo", "showwarning", "showerror")),
                           (fd, ("askopenfilename", "asksaveasfilename", "askdirectory", "askopenfilenames")),
                           (sd, ("askstring", "askinteger", "askfloat"))):
            for n in names:
                if hasattr(mod, n):
                    setattr(mod, n, wrap(getattr(mod, n)))
        mb._soe2_parented = True

    def open_path(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(path)                           # (the folder in Explorer)
            else:
                webbrowser.open("file://" + str(path))
        except Exception as e:
            self._say(f"Couldn't open {path}: {e}", 8)



    def relook(self):
        from .style import relook
        from .hangwatch import step
        step("theme change: re-colour every window")
        n, secs = relook(self.root, SETTINGS.get("theme"))
        step("theme change: theme cards")
        self._paint_look_cards()
        step("theme change: title bar")
        self.paint_titlebar()
        if getattr(self, "mg_win", None) is not None and self.ov_look() == "classic":
            # the overlay over the game is built again only in Classic - the one style that takes the app theme's
            # colours (2.112.4: the others keep their own, so closing and reopening every window over the game on
            # each swap was slow - and risky on Windows - for nothing)
            step("theme change: overlay rebuild")
            try:
                self.merged_set()
            except Exception:
                buglog.caught()
        step("theme change: done")
        if getattr(self, "shown_rec", None) is not None or hasattr(self, "detail"):
            try:
                self.show_detail(self.shown_rec)
            except Exception:
                buglog.caught()
        if hasattr(self, "update_limit_ui"):
            try:
                self.update_limit_ui()
            except Exception:
                buglog.caught()
        self.look_stats = (n, secs)             # (tests read it: how many widgets, how long)



    def paint_titlebar(self):
        """2.61.0: the app window's own (Windows) title bar in the theme's colors - Windows 11 takes any color,
        Windows 10 only dark or light. Elsewhere nothing happens."""
        from . import themes as _th
        from .winsys import set_titlebar
        cap, txt, edge = _th.window_colors()
        try:                                     # 2.112.2: only before the window first shows - forcing every
            if not self.root.winfo_ismapped():   # pending redraw here on each theme change could spin forever
                self.root.update_idletasks()     # (a page relaying itself out in a loop - see style.SbGuard)
        except tk.TclError:
            return
        self.titlebar_colors = (cap, txt, edge)
        set_titlebar(self.root, cap, txt, edge, dark=not _th.ST.theme.light)


    def restart_app(self):
        """Close and start again (2.0.0: for Appearance changes). Windows, lists and settings are saved first."""
        import subprocess
        save_json("settings.json", SETTINGS)
        try:
            if FROZEN:
                cmd = [sys.executable, "--restarted"]
            else:
                cmd = [sys.executable, os.path.join(APP_DIR, "stashofexile2.py"), "--restarted"]
            flags = 0x00000008 | 0x00000200 if sys.platform == "win32" else 0     # detached, own process group
            # 2.26.1: a fresh start of the one-file exe. Without this the new copy reused THIS copy's unpacked
            # folder (PyInstaller passes it on to child processes), which is deleted when this one closes - then
            # cv2 (Delirium / Ritual helpers) and the data files were gone: "No module named 'cv2'".
            env = clean_env()
            subprocess.Popen(cmd, close_fds=True, creationflags=flags, cwd=APP_DIR, env=env)
        except Exception as e:
            return self._say(f"Couldn't restart by itself ({e}); close and open the app to see the change.", 10)
        self.on_close()
















        # (2.98.3, feedback: One-key copy is gone - not a viable way to copy; Ctrl+Alt+C is)







    # ---------------- key bar, hotkeys
    def hdr_layout(self):
        """2.0 beta 7: there is no header any more (kept so older callers don't break)."""

    def refresh_total_header(self):
        self.update_total()

    HOTKEYS = [("Ctrl+Alt+C", "Add item to the list", "add"), ("C", "Copy item name", "copy"), ("O", "Open trade", "trade"),
               ("F2", "Pause searches", "pause"), ("Esc", "Minimize", "min")]

    def build_keybar(self, parent):
        """The bottom plate with the shortcuts drawn as little keys (click one to do the same thing)."""
        kb = Plate(parent, 36, top="#2b4670", mid="#213c66", low="#162b4d", bottom="#0f1d36", edge="#5b80b8")
        kb.pack(fill="x")
        tk.Frame(parent, height=14, bg=C["bg"]).pack(fill="x", side="bottom")       # breathing room under the key bar
        self.keybar, self.key_texts = kb, {}
        x = 14
        self.key_dot = kb.create_text(x, 18, text="●", anchor="w", fill=C["green"], font=("Segoe UI", 11))
        x = kb.bbox(self.key_dot)[2] + 6
        self.key_state = kb.create_text(x, 18, text="Auto-pricing", anchor="w", fill="#cfe0ff", font=("Segoe UI", 9, "bold"))
        x = kb.bbox(self.key_state)[2] + 22
        for cap, text, name in self.HOTKEYS:
            lb = tk.Label(kb, text=cap, bg=C["key"], fg="#eaf2ff", font=(MONO, 9, "bold"), padx=8, pady=1, bd=2,
                          relief="raised", cursor="hand2" if name != "add" else "arrow")
            wid = kb.create_window(x, 18, window=lb, anchor="w")
            kb.update_idletasks()
            x = kb.bbox(wid)[2] + 7
            t = kb.create_text(x, 18, text=text, anchor="w", fill="#b9ccee", font=("Segoe UI", 9))
            self.key_texts[name] = t
            x = kb.bbox(t)[2] + 26
            if name != "add":
                act = {"copy": self.hk_copy, "trade": self.hk_trade, "pause": self.toggle_pause, "min": self.hk_min}[name]
                lb.bind("<Button-1>", lambda e, f=act: f())
                kb.tag_bind(t, "<Button-1>", lambda e, f=act: f())
        self.upd_btn = ttk.Button(kb, text="Check for updates", command=self.check_updates)   # (Settings > General now)
        # 2.0 beta 21: what Price checks is for, where the update button used to be
        self.key_upd = kb.create_text(1000, 18, text="Made for tablets, jewels & waystones  ⓘ", anchor="e",
                                      fill=C["good"], font=("Segoe UI", 9, "bold"))
        kb.tag_bind(self.key_upd, "<Button-1>", lambda e: self.explain_scope())
        kb.tag_bind(self.key_upd, "<Enter>", lambda e: kb.config(cursor="hand2"))
        kb.tag_bind(self.key_upd, "<Leave>", lambda e: kb.config(cursor=""))
        self.key_end = x

        def place_scope(e):                                  # only where it fits next to the keys
            kb.coords(self.key_upd, e.width - 14, 18)
            box = kb.bbox(self.key_upd)
            fits = box is not None and e.width - 14 - (box[2] - box[0]) > self.key_end
            kb.itemconfigure(self.key_upd, state="normal" if fits else "hidden")
        kb.bind("<Configure>", place_scope, add="+")

    EMPTY_TEXT = ("Nothing to price yet\nHover an item in game and press Ctrl+Alt+C: it shows up here and gets "
                  "priced. Tablets, jewels, waystones and gear - weapons, armour, rings, uniques.")
    EMPTY_TEXT_TAB = ("Type your tab's price above and press Read tab:\nevery item on it shows up here and gets priced.\n"
                      "(Ctrl+Alt+C in game still adds items one at a time.)")

    @property
    def empty_text(self):
        """2.8.0: the hint for an empty list follows "Add items from"."""
        return self.EMPTY_TEXT_TAB if SETTINGS.get("pctab", {}).get("mode") == "Stash tab" else self.EMPTY_TEXT

    SCOPE_TEXT = ("Bulk Pricing prices tablets, jewels, waystones and gear. Gear (2.72.0) is searched on the mods "
                  "buyers pay for - filler mods and low tiers are left out - by its totals (defences, DPS, total "
                  "resistances), uniques by name and their well-rolled mods, crafting bases by item level. When the "
                  "listings found don't back a price up, it says Price manually: then check it on the trade site "
                  "(press O on the item).")

    def explain_scope(self):
        self.info_card(self.SCOPE_TEXT, secs=40)

    # ---------------- updates
    def startup_update_check(self):
        """2.0 beta 7: Settings > Updates. Auto-update installs a newer version without asking; auto-check only
        tells you (a card with Update now). Both stay quiet when you are up to date or GitHub can't be reached.
        2.100.0: every start looks once (closing and reopening the app checks again) - with both switches off it only
        lights the update badge; the hourly look (feedback_page.quiet_update_check) carries on from there."""
        if SETTINGS.get("auto_update"):
            self.check_updates(mode="auto")
        elif SETTINGS.get("auto_check_updates"):
            self.check_updates(mode="silent")
        else:
            self.check_updates(mode="badge")

    def check_updates(self, mode="ask"):
        """mode: "ask" (the button: tells you the result, asks before downloading), "silent" (at start: only speaks up
        when there is a new version), "auto" (at start: downloads and installs a new version by itself)."""
        if getattr(self, "_upd_busy", False):
            return
        self._upd_busy = True
        self._upd_mode = mode
        self.upd_btn.config(state="disabled")
        if mode == "ask":
            self._say("Checking GitHub for a new version...", 15)

        def work():
            kind, data = latest_release(preview=bool(SETTINGS.get("update_preview")))
            self.ui_q.put(("update", kind, data))
        threading.Thread(target=work, daemon=True).start()

    def _upd_done(self):
        self._upd_busy = False
        self.upd_btn.config(state="normal")

    def ev_update(self, kind, data):
        self._upd_done()
        if kind == "ok":                                    # 2.100.0: this check speaks for itself - no second card
            self._upd_told = data.get("tag_name")
        if kind == "ok" and hasattr(self, "upd_badge"):            # 2.48.0: the taskbar badge follows every check
            self.ev_update_badge(data.get("tag_name"))
        mode = getattr(self, "_upd_mode", "ask")
        if mode == "badge":                                 # 2.100.0: start-up look with the switches off: badge only
            return
        if mode != "ask":                                   # automatic check at start: quiet unless there is news
            if kind != "ok" or not is_newer(data.get("tag_name", ""), APP_VERSION):
                self.status_text, self.status_until = ("Update check: " + (f"you have the newest version ({pretty_version()})."
                                                       if kind == "ok" or kind == "none" else "GitHub couldn't be reached.")), time.time() + 8
                return
            asset = pick_asset(data)
            tag = data.get("tag_name", "")
            if not asset:
                return
            if mode == "auto":
                self.info_card(f"Updating to version {pretty_version(tag)} (auto-update is on in Settings). The app restarts "
                               "by itself when the download is done.", secs=60)
                self._download_update(asset)
            else:
                self.info_card(f"Version {pretty_version(tag)} is available (you have {pretty_version()}).",
                               [("Update now", lambda: self.check_updates("ask")), ("Settings", lambda: self.shell.open("settings"))],
                               secs=120)
            return
        if kind != "ok":
            self.app_toast(data if kind == "none" else "Could not check for updates.\n" + data, "Check for updates",
                           kind="info" if kind == "none" else "warning")
            self._say(data if kind == "none" else "Update check failed.")
            return
        tag = data.get("tag_name", "")
        if not is_newer(tag, APP_VERSION):
            self.app_toast(f"You are up to date (version {pretty_version()}).", "Check for updates", kind="success")
            self._say("You have the newest version.")
            return
        asset = pick_asset(data)
        notes = plain_notes(data.get("body") or "")
        notes = (notes[:700] + " ...") if len(notes) > 700 else notes
        if not asset:
            messagebox.showinfo("Check for updates", f"Version {tag.lstrip('vV')} is out, but it has no download file attached yet.\n\n"
                                                    f"See https://github.com/{REPO}/releases")
            return
        mb = asset.get("size", 0) / 1048576
        verify = "GitHub's checksum will be checked." if str(asset.get("digest", "")).lower().startswith("sha256:") \
            else "This release has no checksum, so the file can not be verified."
        how = ("The app will close, swap in the new version and start again. Your settings and data are kept."
               if FROZEN and sys.platform == "win32" else "The file will be saved next to the app; you start it yourself.")
        if not messagebox.askyesno("Update available", f"Version {pretty_version(tag)} is available (you have {pretty_version()}).\n\n"
                                   + (f"What's new:\n{notes}\n\n" if notes else "") +
                                   f"Download {asset['name']} ({mb:.1f} MB) now?\n{verify}\n{how}"):
            self._say("Update skipped.")
            return
        self._download_update(asset)

    def _download_update(self, asset):
        self._upd_busy = True
        self.upd_btn.config(state="disabled")
        base = APP_DIR
        dest = os.path.join(base, ("StashOfExile2_update.exe" if FROZEN and sys.platform == "win32" else asset["name"]))

        def work():
            def prog(got, total):
                self.status_text = f"Downloading the update... {got * 100 // total if total else 0}%"
                self.status_until = time.time() + 5
            ok, msg, verified = download_asset(asset, dest, prog)
            self.ui_q.put(("update_downloaded", ok, msg, dest, verified))
        threading.Thread(target=work, daemon=True).start()

    # ---------------- 2.31.0: the community Mod book (communitymods.py)
    def cm_start(self):
        from . import communitymods as CM
        from . import board as BRD
        if not BRD.configured():
            self.root.after(CM.EVERY * 1000, self.cm_start)       # the board may get switched on later
            return
        if not self.cm_asked():
            self.cm_ask()
        self.root.after(60000, self.cm_tick)

    # 2.69.1: sharing is opt-in - the first run asks; nothing is sent until you say yes
    def cm_sharing(self):
        from . import communitymods as CM
        return CM.sharing()

    def cm_asked(self):
        return bool(SETTINGS.get("share_asked"))

    def cm_set_sharing(self, on, say=True):
        was = bool(SETTINGS.get("share_prices")) and bool(SETTINGS.get("share_asked"))
        if was and not on:                               # 2.89.3: turning it off takes your times off the leaderboards
            try:
                from . import board as B
                if B.configured() and B.signed_in():
                    threading.Thread(target=B.lb_forget, daemon=True).start()
            except Exception:
                buglog.caught()
        SETTINGS["share_prices"] = bool(on)
        SETTINGS["share_asked"] = True
        save_json("settings.json", SETTINGS)
        if hasattr(self, "cm_share_var"):
            self.cm_share_var.set(bool(on))
        w = getattr(self, "cm_ask_win", None)
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass
            self.cm_ask_win = None
        if say:
            self._say("Thanks - you're sharing anonymous data with the community." if on else
                      "Nothing will be shared. You still get everyone else's data.", 6)

    def cm_opt_out(self):
        self.cm_set_sharing(False)

    def cm_ask(self, then=None, info=False):
        """The first-run question (and the one before an upload while sharing is off). A small window in the middle
        of the app; closing it without an answer asks again next time - and shares nothing. then(on) runs after an
        answer. 2.89.2: it says what each thing sent is, what it's for and where it goes (communitymods.DETAILS);
        info=True is the same page from Settings ("What's shared?"), with just a Close."""
        from . import communitymods as CM
        old = getattr(self, "cm_ask_win", None)
        if old is not None and old.winfo_exists():
            old.lift()
            return old
        P2 = C["panel2"]
        w = self.cm_ask_win = tk.Toplevel(self.root, bg=P2)
        w.title("Community data sharing")
        w.transient(self.root)
        w.resizable(False, False)
        box = tk.Frame(w, bg=P2, padx=16, pady=16)
        box.pack(fill="both", expand=True)
        tk.Label(box, text="What's shared, and why" if info else "Share anonymous data with the community?", bg=P2,
                 fg=C["text"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(box, text="It's off until you say yes. Nothing is shared unless you turn it on, and you get "
                 "everyone else's data either way. We respect your privacy: no selling, no ads, no tracking.",
                 bg=P2, fg=C["text"], justify="left", wraplength=520, anchor="w").pack(fill="x", pady=(8, 8))
        g = tk.Frame(box, bg=P2)
        g.pack(fill="x")
        for c, h in enumerate(("WHAT", "WHAT EXACTLY", "WHAT IT'S FOR")):
            tk.Label(g, text=h, bg=P2, fg=C["muted"], font=("Segoe UI", 9, "bold"), anchor="w").grid(
                row=0, column=c, sticky="w", padx=(0, 12), pady=(0, 2))
        for r, (what, exact, why) in enumerate(CM.DETAILS, start=1):
            for c, (t, wl, col) in enumerate(((what, 150, C["text"]), (exact, 190, C["muted"]), (why, 170, C["muted"]))):
                tk.Label(g, text=t, bg=P2, fg=col, font=("Segoe UI", 9, "bold" if c == 0 else "normal"), justify="left",
                         wraplength=wl, anchor="nw").grid(row=r, column=c, sticky="nw", padx=(0, 12), pady=4)
        self.cm_ask_rows = len(CM.DETAILS)
        tk.Label(box, text=CM.WHERE, bg=P2, fg=C["muted"], justify="left", wraplength=520, anchor="w").pack(
            fill="x", pady=(8, 0))
        tk.Label(box, text=CM.NEVER, bg=P2, fg=C["muted"], justify="left", wraplength=520, anchor="w").pack(
            fill="x", pady=(8, 0))
        tk.Label(box, text="Change it any time: Settings › Privacy & community.", bg=P2, fg=C["muted"],
                 justify="left", wraplength=520, anchor="w").pack(fill="x", pady=(8, 16))
        row = tk.Frame(box, bg=P2)
        row.pack(fill="x")

        def answer(on):
            self.cm_set_sharing(on)
            if then:
                then(on)
        if info:
            ttk.Button(row, text="Close", command=lambda: (w.destroy(), setattr(self, "cm_ask_win", None))).pack(
                side="right")
        else:
            ttk.Button(row, text="Share", style="Primary.TButton", command=lambda: answer(True)).pack(side="right")
            ttk.Button(row, text="No thanks", command=lambda: answer(False)).pack(side="right", padx=(0, 8))
        w.protocol("WM_DELETE_WINDOW", lambda: (w.destroy(), setattr(self, "cm_ask_win", None)))
        try:
            w.update_idletasks()
            hx, hy, hw, hh = self.root.winfo_rootx(), self.root.winfo_rooty(), self.root.winfo_width(), self.root.winfo_height()
            w.geometry(f"+{hx + max(0, (hw - w.winfo_reqwidth()) // 2)}+{hy + max(0, (hh - w.winfo_reqheight()) // 3)}")
            w.lift()
        except tk.TclError:
            pass
        return w

    def cm_need_sharing(self, then):
        """Before anything goes up to the community board: sharing must be on. -> True when it is (run it now);
        otherwise asks, and then(…) runs if you say Share."""
        if self.cm_sharing():
            return True
        if self.cm_asked():                              # 2.98.5: you said no - never asked again; just say where it is
            self._say("Community data sharing is off - nothing was sent. Settings › Privacy & community turns it on.", 8)
            return False
        self.cm_ask(lambda on: on and then())
        return False

    def cm_tick(self):
        from . import communitymods as CM
        threading.Thread(target=self._cm_work, daemon=True).start()
        try:
            self.lb_send()                               # 2.86.0: your best times to the leaderboards (opt-in)
        except Exception:
            self.log_error("leaderboards")
        self.root.after(CM.EVERY * 1000, self.cm_tick)

    def _cm_work(self):
        from . import communitymods as CM
        try:
            res = CM.sync(MARKET, dict(RULES))
        except Exception:
            res = None
        if res and res[1][0]:
            self.ui_q.put(("cm_synced",))

    def ev_cm_synced(self):
        MARKET.refresh_learned()                     # pooled prices + ratings join what the Mod book knows
        try:
            self.refresh_all()
            self.refresh_rules()
        except Exception:
            buglog.caught()
        self.cm_paint()

    def cm_paint(self):
        from . import communitymods as CM
        chip = getattr(self, "cm_chip", None)
        if chip is None:
            return
        n, mine = CM.stats_count(), CM.helped()
        if not n and not mine:
            chip.pack_forget()
            return
        chip.config(text=f"🌐 Community: {n:,} mod prices" + (f"  ·  you added {mine:,}" if mine else ""))
        if not chip.winfo_manager():
            chip.pack(side="right", padx=(0, 8))

    def cm_share_changed(self):
        self.cm_set_sharing(bool(self.cm_share_var.get()), say=False)

    def ev_update_downloaded(self, ok, msg, dest, verified):
        self._upd_done()
        if not ok and getattr(self, "_upd_mode", "ask") == "auto":
            self.info_card("Auto-update: the download failed, nothing was changed. " + msg, secs=60)
            return
        if not ok:
            messagebox.showerror("Update", msg)
            self._say("Update failed - nothing was changed.")
            return
        if not (FROZEN and sys.platform == "win32"):
            messagebox.showinfo("Update", f"Downloaded to:\n{dest}\n\nClose this program and start that file to use the new version.")
            return
        old = sys.executable
        try:
            import subprocess
            # 2.29.1: the new exe does the swap itself (no .bat, no console windows) - see updates.finish_update
            subprocess.Popen([dest, "--finish-update", old], close_fds=True, env=clean_env())
        except Exception as e:
            messagebox.showerror("Update", f"The new version was downloaded to:\n{dest}\n\nbut could not be installed automatically ({e}).\n"
                                           "Close this program and replace the old file with it yourself.")
            return
        self.on_close()
        os._exit(0)                                  # 2.26.3: really gone (no thread left keeping the exe in use)

    def bind_hotkeys(self):
        """C, O, F2 and Esc work only while THIS window is focused (the game uses those keys too).
        Ctrl+Alt+C is the one global one: it's the game's copy that the clipboard watcher listens for."""
        r = self.root
        for seq, fn, needs_text_ok in (("c", self.hk_copy, False), ("C", self.hk_copy, False), ("o", self.hk_trade, False),
                                       ("O", self.hk_trade, False), ("F2", self.toggle_pause, True),
                                       ("Escape", self.hk_esc, False)):
            r.bind_all(f"<KeyPress-{seq}>", lambda e, f=fn, ok=needs_text_ok: self.on_hotkey(e, f, ok))   # every window
        for seq, act in (("<Control-a>", "all"), ("<Control-A>", "all"), ("<Control-z>", "undo"),
                         ("<Control-Z>", "undo"), ("<KeyPress-Delete>", "delete")):
            r.bind_all(seq, lambda e, a=act: self.on_list_key(a))

    def on_list_key(self, action):
        """Ctrl+A, Ctrl+Z and Del act on the list in the window in front - not while you type in a box (there they
        keep their usual job). 2.4.0: every window's lists, not only Price checks (listkeys.py)."""
        if callable(action):                                   # (older callers passed the function itself)
            action = {self.hk_select_all: "all", self.undo_mark: "undo", self.hk_clear: "delete"}.get(action, "")
        try:
            cls = self.root.focus_get().winfo_class()
        except Exception:
            cls = ""
        if cls in ("TEntry", "Entry", "TSpinbox", "Spinbox", "TCombobox", "Text"):
            return None
        if self._on_checks():
            {"all": self.hk_select_all, "undo": self.undo_mark, "delete": self.hk_clear}[action]()
            return "break"
        sh = getattr(self, "shell", None)
        if sh is not None and sh.active and self.list_key(sh.active, action):
            return "break"
        return None

    def hk_select_all(self):
        kids = self.tree.get_children()
        if kids:
            self.tree.selection_set(kids)
            self.tree.focus(kids[0])

    def hk_clear(self):
        self.remove_selected()                    # 2.0 beta 19: Del deletes the selected items (Clear list empties it)

    def on_hotkey(self, e, fn, even_when_typing):
        if hotkey_blocked(e.state):                                      # Ctrl / Alt held: not ours (Ctrl+C etc.)
            return
        typing = ("TEntry", "Entry", "TSpinbox", "Spinbox", "TCombobox", "Text")
        classes = []
        for get in (lambda: e.widget, self.root.focus_get):          # 2.10.0: the key's own box counts too, and
            try:                                                      # "don't know" never swallows a typed letter
                classes.append(get().winfo_class())
            except Exception:
                classes.append(None)
        if not even_when_typing and (None in classes or any(c in typing for c in classes)):
            return                                                       # you're typing in a box
        fn()
        return "break"

    def hk_esc(self):
        """Esc: 2.55.1 - first closes an item box (Price checks / Insights), else minimizes as before."""
        if not self.ins_preview_dismiss():
            self.hk_min()

    def hk_copy(self):
        sel = self.tree.selection() if self._on_checks() else ()
        if len(sel) >= 1 and int(sel[0]) in self.records:
            self.copy_name(self.records[int(sel[0])], True)
        else:
            self.status_text, self.status_until = "Select an item first, then press C to copy its name.", time.time() + 5

    def hk_trade(self):
        if self._on_checks() and self.tree.selection():
            self.open_trade()
        else:
            self.status_text, self.status_until = "Select an item first, then press O to open its search on the trade site.", time.time() + 5

    def hk_min(self):
        self.min_ok_until = time.time() + 3       # YOU asked for it: on_unmap lets it go through
        self.root.iconify()                       # goes to the system tray when that is available (see on_unmap)

    # ---------------- settings handlers
    def on_league(self, _e=None):
        self.league_changed(self.league_var.get())
        for rid, rec in self.records.items():      # re-price everything for the new league
            rec["state"] = "queued"
            self.update_row(rid)
            self.engine.add(2, "price", rid)

    def league_changed(self, new):
        """Switch the market memory to `new`. Prices never mix between leagues; on a new league the list of
        valuable mods is carried over (after one yes/no)."""
        old = SETTINGS.get("market_league") or SETTINGS.get("league")
        SETTINGS["league"] = new
        if old and old != new:
            carry = False
            if MARKET.has_data(old) and not MARKET.has_data(new):
                carry = messagebox.askyesno(
                    "New league?",
                    f"You switched from {old} to {new}.\n\nIs {new} a NEW league (a fresh start)?\n\n"
                    "Yes: prices start fresh, but the app keeps what it learned about which mods are valuable.\n"
                    "No: prices start fresh as well (they never mix between leagues), and the old league's mod "
                    "knowledge is NOT carried over.")
            if carry:
                n = MARKET.snapshot_league(old)
                self.status_text, self.status_until = f"New league: kept {n} valuable mods from {old}; prices start fresh.", time.time() + 12
        SETTINGS["market_league"] = new
        MARKET.refresh_learned()
        save_json("settings.json", SETTINGS)




    def league_link(self, parent, bg):
        """2.59.0: the league, shown with a link to Settings › General where it is set (one home for it)."""
        lbl = tk.Label(parent, textvariable=self.league_var, bg=bg, fg=C["accent"], cursor="hand2",
                       font=("Segoe UI", 10, "underline"))
        lbl.bind("<Button-1>", lambda e: (self.close_whatsnew() if getattr(self, "_whatsnew", None) else None,
                                          self.settings_open("General", "league")))
        return lbl

    def acc_text(self):
        v = SETTINGS.get("wealth_account", "")
        return f"Account: {v}  ⚙" if v else "Account: not set  ⚙"

    def acc_link(self, parent, bg):
        """A small 'Account: Name ⚙' label that opens Settings › Price checking, where the account is set."""
        self.pc_vars()
        lbl = tk.Label(parent, text=self.acc_text(), bg=bg, fg=C["accent"], cursor="hand2", font=("Segoe UI", 9, "underline"))
        lbl.bind("<Button-1>", lambda e: self.settings_open("Price checking", "account"))
        self.acc_links.append(lbl)
        return lbl






    def toggle_pause(self):
        self.engine.paused = not self.engine.paused
        self.pause_btn.config(text="Resume" if self.engine.paused else "Pause")
        kb = self.keybar
        kb.itemconfigure(self.key_texts["pause"], text="Resume searches" if self.engine.paused else "Pause searches")
        kb.itemconfigure(self.key_state, text="Paused" if self.engine.paused else "Auto-pricing")
        kb.itemconfigure(self.key_dot, fill=C["good"] if self.engine.paused else C["green"])

    # ---------------- rate limit display
    def limit_banner(self, parent, before):
        """2.103.3: the same "Staying under the trade site's limits" line as Bulk Pricing, on another page."""
        ban = tk.Label(parent, text="", anchor="w", padx=12, pady=2, font=("Segoe UI", 9), justify="left")
        self.limit_banners = getattr(self, "limit_banners", []) + [(ban, before)]
        return ban

    def update_limit_ui(self):
        st = LIMITER.state()
        waiting = sum(1 for r in self.records.values() if r["state"] in ("queued", "pricing"))
        if self.engine.paused:
            txt, bg, fg = "⏸  Paused - items you copy still queue up. Press Resume to continue.", C["panel2"], C["muted"]
        elif st["blocked"] > 0:
            txt = (f"⏳  The trade site rate-limited us. Resuming automatically in {mmss(st['blocked'])}.  "
                   + (f"{waiting} item{'s' if waiting != 1 else ''} queued - nothing is lost." if waiting
                      else "You can keep copying items; they'll queue up."))
            bg, fg = "#3a1a16", C["red"]
        elif st["wait"] > 20:
            txt = (f"⏳  Staying under the trade site's limits - next check in {mmss(st['wait'])} ({st['why']}).  "
                   + (f"{waiting} queued." if waiting else ""))
            bg, fg = "#2e2514", C["good"]
        else:
            txt = ""
        for ban, before in [(self.banner, self.checks_area)] + list(getattr(self, "limit_banners", [])):
            try:                                   # 2.103.3 (feedback): Price Checks and Favorites show it too
                if txt:
                    ban.config(text=txt, bg=bg, fg=fg)
                    if not ban.winfo_ismapped():
                        ban.pack(fill="x", padx=8, pady=(0, 4), before=before)
                elif ban.winfo_ismapped():
                    ban.pack_forget()
            except tk.TclError:
                pass
        parts, worst = [], 0
        for cls in ("search", "fetch"):
            h, mx, per = max(LIMITER.usage(cls), key=lambda u: u[0] / u[1])
            worst = max(worst, h / mx)
            parts.append(f"{cls.title()} {h}/{mx} ({per_text(per)})")
        dot = C["red"] if (st["blocked"] > 0 or worst >= 0.8) else C["good"] if worst >= 0.5 else C["green"]
        pill = getattr(self, "limit_pill", None)
        if pill is not None:
            if st["blocked"] > 0:
                ptxt, pfg = f"● Trade site: paused {mmss(st['blocked'])}", C["red"]
            elif st["wait"] >= 2:
                ptxt, pfg = f"● Trade site: wait {mmss(st['wait'])}", C["good"]
            else:
                ptxt, pfg = "● Trade site: ready", C["green"]
            try:
                pill.config(text=ptxt, fg=pfg)
                self.limit_tip.text = ("How much of the trade site's limits the app has used (it stays well under "
                                       "them):\n" + "\n".join(parts) + "\nClick for the details.")
            except tk.TclError:
                pass
        self.limit_lbl.config(text="    ".join(p.split(" ", 1)[1] for p in parts) + "   ", fg=dot)

    # ---------------- exchange rates
    def rates_tick(self):
        """Every 30 s: show how fresh the rates are, and fetch new ones (in the background) when they're over an hour old."""
        try:
            lg = SETTINGS.get("league")
            age = RATES.age()
            stale = RATES.league != lg or age is None or age > 3600
            if lg and stale and not self._rates_busy and time.time() - RATES.attempt > 600:
                self._rates_busy = True
                threading.Thread(target=self._rates_worker, args=(lg, False), daemon=True).start()
            old = age is None or age > 7200
            self.rates_lbl.config(text=RATES.status_text() + "  ", fg=C["good"] if (old or RATES.error) else C["muted"])
            if self.rates_win and self.rates_win.winfo_exists():
                self.draw_rates()
        except Exception:
            self.log_error("exchange rates")
        finally:
            self.root.after(30000, self.rates_tick)

    def _rates_worker(self, league, force):
        try:
            RATES.ensure(league, force=force)
        finally:
            self._rates_busy = False
            self.ui_q.put(("rates_done",))       # 2.114.0 (P9: the status bar said "none yet" for up to 30 s after)

    def ev_rates_done(self):
        age = RATES.age()
        old = age is None or age > 7200
        self.rates_lbl.config(text=RATES.status_text() + "  ", fg=C["good"] if (old or RATES.error) else C["muted"])
        if self.rates_win and self.rates_win.winfo_exists():
            self.draw_rates()

    def refresh_rates_now(self):
        lg = SETTINGS.get("league")
        if lg and not self._rates_busy:
            self._rates_busy = True
            threading.Thread(target=self._rates_worker, args=(lg, True), daemon=True).start()
            self.rates_lbl.config(text="Rates: updating…  ")
            self.root.after(2500, lambda: self.rates_win and self.rates_win.winfo_exists() and self.draw_rates())

    def on_rates_auto(self):
        SETTINGS["rates_auto"] = self.rates_auto_var.get()
        save_json("settings.json", SETTINGS)

    def open_rates(self, _e=None):
        """2.0 beta 7: Exchange rates is its own utility window."""
        self.shell.open("rates")

    def rates_status_dot(self):
        age = RATES.age()
        if not RATES.table:
            return False
        return "warn" if (RATES.error or age is None or age > 7200) else True

    def build_rates_window(self, win):
        self.rates_win = win
        # 2.4.0: tabs - Rates, Exchange Helper (2.92.0: Arbitrage removed; its flip check is under Exchange Helper)
        self.rates_view = SegBar(win, ["Rates", "Exchange Helper"], command=lambda v: self.rates_show_page(),
                                 size=10, pad=(16, 4))
        self.rates_view.pack(anchor="w", padx=16, pady=(8, 0))
        if getattr(self, "shell", None) is not None:          # 2.64.0: its tabs are listed in the sidebar
            self.shell.register_tabs("rates", self.rates_view)
        self.rates_pages = {k: tk.Frame(win, bg=C["panel"]) for k in ("Rates", "Exchange Helper")}
        w = self.rates_pages["Rates"]
        w.pack(fill="both", expand=True)
        top = tk.Frame(w, bg=C["panel"], padx=16, pady=8)
        top.pack(fill="x")
        self.rates_status = tk.Label(top, text="", bg=C["panel"], fg=C["text"], anchor="w", justify="left", wraplength=360)
        self.rates_status.pack(side="left", fill="x", expand=True)
        ttk.Button(top, text="Refresh now", style="Primary.TButton", command=self.refresh_rates_now).pack(side="right")
        # (2.105.0, feedback: no "Check for new rates every hour" switch - they're always checked hourly)
        # ---- 2.2.0: what to post on the in-game Currency Exchange (2.4.0: its own tab, "Exchange Helper")
        hp = self.rates_pages["Exchange Helper"]
        exo, ex = chrome_section(hp, "Exchange Helper")
        exo.pack(fill="x", padx=16, pady=8)
        tk.Label(ex, text="Pick what you're selling and what you want: it shows the ratio to post on the Currency "
                          "Exchange, and what you'd get.", bg=C["panel2"], fg=C["muted"], anchor="w", justify="left",
                 wraplength=560).pack(fill="x")
        er = tk.Frame(ex, bg=C["panel2"])
        er.pack(fill="x", pady=(4, 0))
        tk.Label(er, text="I sell", bg=C["panel2"], fg=C["muted"]).pack(side="left")
        self.ex_amt = tk.StringVar(value="10")
        ttk.Entry(er, textvariable=self.ex_amt, width=7).pack(side="left", padx=8)
        self.ex_have = tk.StringVar(value="Divine Orb")
        self.ex_want = tk.StringVar(value="Exalted Orb")
        self.ex_boxes = []
        for i, var in enumerate((self.ex_have, self.ex_want)):
            if i:
                tk.Label(er, text="for", bg=C["panel2"], fg=C["muted"]).pack(side="left", padx=(8, 8))
            cb = ttk.Combobox(er, textvariable=var, state="readonly", width=22)
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>", lambda e: self.draw_exchange())
            self.ex_boxes.append(cb)
        ttk.Button(er, text="⇄", width=3, command=self.ex_swap, style="Quiet.TButton").pack(side="left", padx=8)
        self.ex_out = tk.Label(ex, text="", bg=C["panel2"], fg=C["text"], font=(MONO, 10), anchor="w", justify="left")
        self.ex_out.pack(fill="x", pady=(8, 0))
        tk.Label(ex, text="The Currency Exchange only takes whole numbers, so these are the closest whole-number "
                          "ratios to the market. Rates are from poe.ninja and move during the day.",
                 bg=C["panel2"], fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left",
                 wraplength=560).pack(fill="x", pady=(8, 0))
        self.ex_amt.trace_add("write", lambda *a: self.draw_exchange())
        cvo, conv = chrome_section(hp, "Convert")   # 2.105.0 (feedback): under Exchange Helper (was on Rates)
        cvo.pack(fill="x", padx=16, pady=8)
        row = tk.Frame(conv, bg=C["panel2"])
        row.pack(fill="x")
        tk.Label(row, text="What is", bg=C["panel2"], fg=C["muted"]).pack(side="left")
        sel = self.tree.selection() if hasattr(self, "tree") else ()
        start = ""
        if len(sel) == 1 and self.records.get(int(sel[0]), {}).get("est"):
            start = _num(self.records[int(sel[0])]["est"])
        self.conv_var = tk.StringVar(value=start or "8.5")
        ttk.Entry(row, textvariable=self.conv_var, width=9).pack(side="left", padx=8)
        tk.Label(row, text="divines worth in the other currencies?", bg=C["panel2"], fg=C["muted"]).pack(side="left")
        self.conv_out = tk.Label(conv, text="", bg=C["panel2"], fg=C["good"], font=(MONO, 10, "bold"), anchor="w", justify="left",
                                 wraplength=580)
        self.conv_out.pack(fill="x", pady=(8, 0))
        self.conv_var.trace_add("write", lambda *a: self.draw_rates())
        cols = [("cur", "Currency", 200, "w"), ("worth", "In divines", 120, "e"), ("per", "1 divine buys", 120, "e"),
                ("vol", "Volume (div)", 110, "e")]
        tk.Label(w, text="From poe.ninja, about hourly. Volume: how much it saw traded, in divines. Prices in a "  # 2.114.0
                         "currency not listed are left out and flagged.",
                 bg=C["panel"], fg=C["muted"], wraplength=600, justify="left", padx=16, pady=8).pack(side="bottom", fill="x")
        SectionBar(w, "Rates").pack(fill="x", padx=16)         # 2.69.0: the list under its strip, sunken
        rvp = Viewport(w)
        rvp.pack(fill="both", expand=True, padx=16)
        tv = ttk.Treeview(rvp.body, columns=[c[0] for c in cols], show="headings")
        for cid, title, width, anchor in cols:
            tv.heading(cid, text=title)
            tv.column(cid, width=width, anchor=anchor, stretch=(cid == "cur"))
        sb = ttk.Scrollbar(rvp.body, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tv.pack(fill="both", expand=True)
        tv.tag_configure("odd", background=C["odd"])
        tv.tag_configure("thin", foreground=C["muted"])
        self.rates_tv = tv
        self.list_register("rates", tv)
        self.build_flip(self.rates_pages["Exchange Helper"])   # 2.92.0: at the bottom of Exchange Helper
        self.draw_rates()

    def rates_show_page(self):
        pick = self.rates_view.get()
        for k, f in self.rates_pages.items():
            if k == pick:
                f.pack(fill="both", expand=True)
            else:
                f.pack_forget()

    def draw_rates(self):
        w = self.rates_win
        if not (w and w.winfo_exists()):
            return
        self.rates_status.config(text=RATES.status_text() + (f"\nLast problem: {RATES.error}" if RATES.error else "")
                                 + ("" if RATES.table else "\nNo rates yet - pick a league and press Refresh now."))
        try:
            x = float(self.conv_var.get().replace(",", "."))
            eq = RATES.equivalents(x)
            txt = "   ".join(f"≈ {_amt(a)} {cur}" for cur, a in eq) or "no rates yet"
            opt = RATES.list_options(x)
            self.conv_out.config(text=txt + (("\n" + opt) if opt else ""))
        except ValueError:
            self.conv_out.config(text="type a number of divines")
        self.draw_exchange()
        tv = self.rates_tv
        tv.delete(*tv.get_children())
        rows = sorted(((c, v) for c, v in RATES.table.items() if v), key=lambda cv: -(RATES.vol.get(cv[0], 0)))
        names = ((WPRICES.parts.get("Currency") or {}).get("names") or {}) if WPRICES.parts else {}
        from .ovrates import cur_name, fmt_worth                # 2.114.0: names, plain numbers
        for i, (cur, v) in enumerate(rows[:120]):
            vol = RATES.vol.get(cur, 0)
            tv.insert("", "end", values=(cur_name(cur, names), fmt_worth(v), (f"{1 / v:,.0f}" if 1 / v >= 10 else f"{1 / v:.2g}"), f"{vol:,.0f}"),
                      tags=("thin",) if vol < 5 else (("odd",) if i % 2 else ()))

    def ex_currencies(self):
        """[(display name, currency id)] most traded first, Divine Orb on top."""
        from .ovrates import cur_name                            # (2.114.0: one list of names)
        names = ((WPRICES.parts.get("Currency") or {}).get("names") or {}) if WPRICES.parts else {}
        ids = sorted((c for c, v in RATES.table.items() if v), key=lambda c: -(RATES.vol.get(c, 0)))
        first = [c for c in ("exalted", "chaos") if RATES.table.get(c)]       # the usual ones always on top
        out = [("Divine Orb", "divine")]
        for c in first + [c for c in ids if c not in first][:40]:
            if c != "divine":
                out.append((cur_name(c, names), c))
        return out

    def ex_swap(self):
        a, b = self.ex_have.get(), self.ex_want.get()
        self.ex_have.set(b)
        self.ex_want.set(a)
        self.draw_exchange()

    def draw_exchange(self):
        if not hasattr(self, "ex_out"):
            return
        from .rates import exchange_offers
        cur = self.ex_currencies()
        names = [n for n, _c in cur]
        for cb in self.ex_boxes:
            cb["values"] = names
        ids = dict(cur)
        if self.ex_want.get() not in ids:                    # (first time: Exalted Orb, or the most traded one)
            ex = next((n for n, c in cur if c == "exalted"), cur[1][0] if len(cur) > 1 else None)
            if ex:
                self.ex_want.set(ex)
        have, want = ids.get(self.ex_have.get()), ids.get(self.ex_want.get())
        if have is None or want is None or have == want:
            self.ex_out.config(text="Pick two different currencies." if RATES.table else "No rates yet - press Refresh now.")
            return
        res = exchange_offers(have, want, RATES)
        if not res:
            self.ex_out.config(text="No rate for one of these currencies yet.")
            return
        r, offers = res
        try:
            amt = float(self.ex_amt.get().replace(",", "") or 0)
        except ValueError:
            amt = 0
        hn, wn = self.ex_have.get(), self.ex_want.get()
        def num(x):
            return _amt(x) if x >= 1 else f"{x:.3g}"
        lines = [f"Market: 1 {hn} ≈ {num(r)} {wn}   (1 {wn} ≈ {num(1 / r)} {hn})", ""]
        for label, a, b, note in offers:
            get = f"   → {_amt(amt)} {hn} gets you ≈ {num(amt * b / a)} {wn}" if amt else ""
            lines.append(f"{label:<11} post {a} : {b}{get}")
        self.ex_out.config(text="\n".join(lines))

    def open_limits(self, _e=None):
        if self.limit_win and self.limit_win.winfo_exists():
            self.limit_win.lift()
            return
        from .overlaywin import OverlayWindow                             # 2.0 beta 13: the app's own look
        w = OverlayWindow(self.root, "Trade site rate limits", "⏱",
                          (self.root.winfo_rootx() + 220, self.root.winfo_rooty() + 180, None, None),
                          opacity=255, body_bg=C["panel"], app_colours=True, lockable=False)
        w.attributes("-topmost", bool(SETTINGS.get("on_top", True)))     # stays above the main window (1.35)
        self.limit_win = w
        self.limit_body = tk.Frame(w.body, bg=C["panel"], padx=16, pady=16)
        self.limit_body.pack()
        self.draw_limits()

    def draw_limits(self):
        w = self.limit_win
        if not (w and w.winfo_exists()):
            return
        for c in self.limit_body.winfo_children():
            c.destroy()
        for cls in ("search", "fetch"):
            tk.Label(self.limit_body, text=cls.title(), bg=C["panel"], fg=C["text"], font=("Segoe UI", 12, "bold"),
                     anchor="w").pack(fill="x", pady=(8, 2))
            for h, mx, per in LIMITER.usage(cls):
                row = tk.Frame(self.limit_body, bg=C["panel"])
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f"{h} / {mx}  in {per_text(per)}", bg=C["panel"], fg=C["muted"], width=24,
                         anchor="w").pack(side="left")
                ratio = min(1.0, h / mx)
                from . import themes as _th                  # 2.60.0: the theme's meter
                _th.Meter(row, ratio, width=160, height=14,
                          on=C["red"] if ratio >= 0.8 else C["good"] if ratio >= 0.5 else None).pack(side="left")
        st = LIMITER.state()
        note = "Counts include requests from other tools on the same account or IP."
        if st["penalties"]:
            note += f"\nPenalties this session: {st['penalties']}"
        tk.Label(self.limit_body, text=note, bg=C["panel"], fg=C["muted"], justify="left", anchor="w",
                 wraplength=380).pack(fill="x", pady=(12, 0))
        self.root.after(1000, self.draw_limits)

    def on_toggles(self):
        SETTINGS["popups"] = self.pop_var.get()
        SETTINGS["sound"] = self.snd_var.get()
        SETTINGS["auto_copy"] = self.copy_var.get()
        save_json("settings.json", SETTINGS)

    def on_any_copy(self):
        SETTINGS["hotkey_only"] = not self.any_copy_var.get()
        self.hk_var.set(SETTINGS["hotkey_only"])
        save_json("settings.json", SETTINGS)

    # ---------------- clipboard + events
    def log_error(self, where):
        """Write an unexpected error to the app's log and say so in the status line - never let it stop the app.
        2.115.0: one log for everything (buglog - app_log.txt; was error_log.txt), cleaned the same way."""
        try:
            from . import buglog
            if buglog.record("error", where, exc=True):          # (the same error within 30 s: once)
                self.status_text = f"Something went wrong ({where}) - Report a bug sends the details"
                self.status_until = time.time() + 20
        except Exception:
            buglog.caught()

    def poll_clipboard(self, gen=None):
        if gen is not None and gen != self.poll_gen:
            return                                           # an older watcher that was replaced: let it die
        gen = self.poll_gen
        self.last_poll = time.time()
        self.copy_mark_check()
        try:
            seq = clip_seq()
            if seq is not None:                              # Windows: every copy bumps the counter, even identical text
                if seq != self.last_seq:
                    text = read_clipboard_text()
                    if text is None:                         # another program is holding the clipboard: try again next tick
                        pass
                    else:
                        self.last_seq = seq
                        if text and self._clip_ignored(text):     # our own chat-command paste (and putting yours back)
                            self.last_clip = text
                        elif text:
                            self.last_clip = text
                            if self.wealth_takes(text):        # 2.0 beta 7: a copied stack, counted on Wealth
                                self.wealth_clip(text)
                            elif self.pc_wants(text):            # 2.80.0: your price check key on an item -> Price Checks
                                self.last_heard = time.time()
                                self.pc_take(text)
                            elif self.gate_ok(text):
                                self.last_heard = time.time()
                                self.accept_clip(text)
            else:                                            # other systems: only changed text counts
                try:
                    text = self.root.clipboard_get()
                except tk.TclError:
                    text = ""
                if text and text != self.last_clip and self._clip_ignored(text):
                    self.last_clip = text
                elif text and text != self.last_clip:
                    self.last_clip = text
                    self.last_heard = time.time()
                    if self.wealth_takes(text):
                        self.wealth_clip(text)
                    else:
                        self.accept_clip(text)
        except Exception:
            self.log_error("reading the clipboard")
        finally:
            self.root.after(150, self.poll_clipboard, gen)

    def ignore_clip(self, text, secs=3.0):
        """The app itself is about to put this on the clipboard: don't treat it as your copy (called from any thread)."""
        now = time.time()               # (2.117.0: built whole, then swapped in - another thread may be reading it)
        keep = {t: u for t, u in dict(getattr(self, "_clip_ignore", {})).items() if u > now}
        keep[text] = now + secs
        self._clip_ignore = keep

    def _clip_ignored(self, text):
        return getattr(self, "_clip_ignore", {}).get(text, 0) > time.time()

    def keys_refresh(self):
        """2.88.2: Windows drops a keyboard hook that was slow to answer (a busy moment), silently; putting a fresh
        one in every few minutes keeps Ctrl+Alt+C / Ctrl+D / the hotkeys heard."""
        try:
            self.keys.rehook()
        finally:
            self.root.after(5 * 60 * 1000, self.keys_refresh)

    def gate_ok(self, text):
        """True if this copy may become a row: it must come from YOUR Ctrl+Alt+C (not another tool's key)."""
        if text == self.own_clip or not SETTINGS.get("hotkey_only", True) or not self.keys.active:
            return True
        if self.keys.combo_recent():
            return True
        if self.keys.hook_stale() and self.ADVANCED.search(text):    # 2.88.2: the key watcher was dropped by Windows
            self.keys.rehook()                                         # (no key seen at all): an advanced copy is
            self.keys.combo_time = time.time()                         # yours - and a fresh watcher goes in
            return True
        if text.lstrip().startswith("Item Class:"):
            self.status_text = ("Ignored an item copy that wasn't made with your Ctrl+Alt+C (another tool?). "
                                "Wrong? Settings > Keys > \"Also add items copied another way\"")
            self.status_until = time.time() + 8
        return False

    def copy_mark_check(self):
        """2.19.0: a fresh Ctrl+Alt+C (seen by the key watcher) -> a ring where the mouse is, for 10 seconds."""
        keys = getattr(self, "keys", None)
        dbl = getattr(keys, "esc_double", 0) if keys else 0
        if dbl and dbl > getattr(self, "_esc_double_seen", 0):  # 2.25.0: Esc tapped twice clears every mark
            self._esc_double_seen = dbl
            if getattr(self, "copy_marker", None) and self.copy_marker.marks:
                self.copy_marker.clear()
        t = getattr(keys, "combo_time", 0) if keys else 0
        if not t or t <= getattr(self, "_marked_combo", 0):
            return
        self._marked_combo = t
        if not SETTINGS.get("copy_marker", True):
            return
        try:
            from .copymark import CopyMarker
            if getattr(self, "copy_marker", None) is None:
                self.copy_marker = CopyMarker(self.root)
            x, y = self.root.winfo_pointerxy()
            hold = bool(SETTINGS.get("copy_marker_hold"))
            try:
                secs = max(1, min(600, int(float(SETTINGS.get("copy_marker_secs") or 10))))
            except (TypeError, ValueError):
                secs = 10
            self.copy_marker.show(x, y, secs=None if hold else secs, colour=self.marker_colour())
        except Exception:
            self.log_error("showing the copy marker")

    def restart_watcher(self):
        """Start a fresh clipboard watcher (the old one, if still alive, stops itself)."""
        self.poll_gen += 1
        self.last_poll = time.time()
        self.root.after(50, self.poll_clipboard, self.poll_gen)

    ADVANCED = re.compile(r"\{\s*(?:Prefix|Suffix|Implicit|Unique|Desecrated|Enchant)[^}]*\}", re.I)

    def accept_clip(self, text):
        """Only a real Ctrl+Alt+C copy of an item we haven't already got becomes a new row."""
        if not SETTINGS.get("listen", True):
            return
        if text.lstrip().startswith("Item Class:"):               # 2.45.0: the Strat Tracker's loot box / setup takes it
            if self.fd_capturing():                               # 2.51.0: Mod book › Manual feed, while it shows
                return self.fd_take_clip(text)
            if self.fl_capturing():
                return self.fl_take_clip(text)
            if self.fl_ed_open() and self.fl_ed_take(text):
                return None
        if not text.lstrip().startswith("Item Class:"):          # something else on the clipboard
            if text != self.own_clip:                            # (our own "copy name" isn't worth mentioning)
                self.status_text, self.status_until = "Heard a copy, but it isn't an item (ignored)", time.time() + 6
            return
        if parse_stack(text):                                    # currency & other stacks: offer the Wealth window
            return self.not_priceable_yet(text)
        if not self.ADVANCED.search(text):                       # plain Ctrl+C: no mod tiers/ranges, can't be priced well
            self.status_text = "Ignored a normal copy - use Ctrl+Alt+C so the mod details are included"
            self.status_until = time.time() + 10
            return
        item = self.read_any(text)
        if not item:
            self.not_priceable_yet(text)
            return
        same = [r for r in self.records.values() if self.item_sig(r["item"]) == self.item_sig(item)
                and r.get("src", "manual") == "manual"]           # 2.42.0: your own list (not a stash tab's)
        if same:                                                 # exact same name + exact same mods: ask
            self.dup_pending.append((text, item, same[-1], len(same)))
            if not self.dup_win:
                self.show_dup()
            return
        self.add_clean(text)

    def trade_stat_lookup(self, line):
        """For gamedata: find a mod wording on the trade site's own stat list (downloaded daily by the engine).
        Only exact matches (or 'reduced' read as a negative 'increased') are learned: a guess would be remembered."""
        table = self.engine.table
        if not table:
            return None
        variants = [line, line.lstrip().lstrip("+"), "+" + line.lstrip()]       # the sign is written either way
        for v in variants:
            sid, grp, flipped, note = find_stat(v, set(), table)
            if sid and (not note or note.startswith("matched with reduced")):
                line = v
                break
        else:
            return None
        entry = table.get(norm(line)) or {grp: sid}
        trade = {g: list(DUPS.get(i, [i])) for g, i in entry.items()}
        return {"ref": SIDTEXT.get(sid) or norm(line), "trade": trade, "negate": flipped}

    def not_priceable_yet(self, text):
        """A copy the price checker can't price (currency, gems, waystones, a base it doesn't know ...): say so plainly,
        and put the item on the Item library page to show how it is read. (Gear is priced from 1.41.)"""
        g = gamedata.read_item(text)
        if not g:
            self.status_text, self.status_until = "Heard an item copy, but couldn't read it as an item", time.time() + 10
            return
        cls = gamedata.classes().get(g.get("class") or "", {}).get("name") or g.get("class_text") or "This item"
        what = f"{g.get('name') or g.get('base') or 'item'}" + (f" ({g['base']})" if g.get("base") and g["base"] != g.get("name") else "")
        try:                                                 # 1.42: keep the text, so the reason can be found
            path = P("unpriced_items.txt")
            if not os.path.exists(path) or os.path.getsize(path) < 500_000:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} v{APP_VERSION}\n{text.strip()}\n")
        except Exception:
            buglog.caught()
        if g.get("stack") is not None and parse_stack(text):      # 2.0 beta 7: one click puts it on Wealth
            name, qty, _c = parse_stack(text)
            msg = (f"{name} x{qty:,} is a stack: stacks are counted on the Wealth window, not price-checked. "
                   "Tip: with the Wealth window in front (or while counting), a plain Ctrl+C adds stacks there.")
            self.status_text, self.status_until = msg, time.time() + 15
            if SETTINGS.get("labs"):
                self.info_card(msg, [("Add it to Wealth", lambda: (self.shell.open("wealth"), self.wealth_clip(text)))])
            else:
                self.info_card(f"{name} x{qty:,} is a stack: currency isn't price-checked. (Counting it is part of "
                               "Wealth, a beta feature: Settings › General › Beta features.)")
            self.stack_price(name, qty)                       # 2.72.1: what it's worth, in the status line
            return
        from .wealth import parse_currency_item
        cur = parse_currency_item(text)
        if cur:                                               # 2.114.0: a single currency-like item (a Wombgift)
            self.status_text, self.status_until = f"Pricing {cur[0]}...", time.time() + 10
            self.stack_price(cur[0], cur[1], loud=True)
            return
        if g.get("stack") is not None:
            why = "stackable items are counted on the Wealth window, not price-checked here"
        elif g.get("rarity") == "Normal" and g.get("class") in ("tablet", "jewel", "waystone"):
            why = "a normal (white) one has no mods to price"
        elif g.get("class") in ("tablet", "jewel") and g.get("rarity") in ("Magic", "Rare"):
            why = ("its name line wasn't recognized (the copied text is saved in unpriced_items.txt in the data "
                   "folder)")
        elif not g.get("base"):
            why = "its base type isn't in the library"
        else:
            why = "the price checker doesn't price this kind of item yet"
        msg = f"{cls}: not priced - {why}."                  # 2.18.0: no Under the hood link from Price checks
        self.status_text, self.status_until = msg, time.time() + 20
        if hasattr(self, "lib_in"):
            self.lib_in.delete("1.0", "end")
            self.lib_in.insert("1.0", text)
            self.lib_check()
        self.info_card(msg)

    def app_toast(self, text, title="", actions=(), secs=None, colour=None, kind=None):
        """2.18.0, 2.35.0: one of the app's toasts (soe2/toasts.py) - stacked in the app's bottom-right corner, with an
        icon per kind, paused while hovered, timed by text length, never taking the keyboard. kind: info / success /
        warning / error (guessed from the old color or the text when not given). Returns the toast's window."""
        if kind is None:
            low = (text or "").lower()
            if colour in (C["red"], "#ff6b5e") or low.startswith(("couldn't", "could not", "error", "failed")):
                kind = "error"
            elif colour in (C["green"], "#5fd38a") or low.startswith(("done", "saved", "copied", "✔")):
                kind = "success"
            else:
                kind = "info"
        t = self.toasts.show(text, title, kind, actions, secs if secs and secs > 20 else None)
        self._app_toast = t["win"]
        return t["win"]

    def info_card(self, text, actions=(), secs=25):
        """A note above the list you can't miss (the status line is easy to miss). Replaces the previous one; goes
        away by itself after `secs`, or with OK."""
        old = getattr(self, "_info_card", None)
        if old is not None:
            try:
                old.destroy()
            except Exception:
                buglog.caught()
        outer = tk.Frame(self.checks_body, bg=C["steel"], padx=1, pady=1)
        outer.pack(before=self.checks_area, fill="x", padx=8, pady=(0, 8))
        card = tk.Frame(outer, bg=C["panel2"], padx=16, pady=8)
        card.pack(fill="x")
        btns = tk.Frame(card, bg=C["panel2"])
        btns.pack(side="right", padx=(12, 0))

        def close():
            try:
                outer.destroy()
            except Exception:
                buglog.caught()
            if getattr(self, "_info_card", None) is outer:
                self._info_card = None
        for label, fn in actions:
            ttk.Button(btns, text=label, command=lambda f=fn: (close(), f())).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="OK", command=close).pack(side="left")
        lbl = tk.Label(card, text=text, bg=C["panel2"], fg=C["text"], anchor="w", justify="left", font=("Segoe UI", 10))
        lbl.pack(side="left", fill="x", expand=True)
        lbl.bind("<Configure>", lambda e: lbl.config(wraplength=max(300, e.width - 10)))
        self._info_card = outer
        self.root.after(secs * 1000, lambda o=outer: getattr(self, "_info_card", None) is o and close())
        sh = getattr(self, "shell", None)
        if sh is not None and sh.active != "checks":         # 2.62.0: on another page - say it there too
            try:
                self.app_toast(text, actions=list(actions) + [("Show", lambda: sh.open("checks"))], secs=secs)
            except Exception:
                buglog.caught()

    @staticmethod
    def item_sig(item):
        """Exact name + base + every mod line with its exact numbers (order doesn't matter)."""
        mods = sorted((m["kind"], re.sub(r"\s+", " ", m["text"]).strip().lower()) for m in item["mods"])
        return (item["name"].strip().lower(), item["base"].strip().lower(), tuple(mods))

    def add_clean(self, text):
        new = self.add_item_text(text)
        if new:
            self.status_text, self.status_until = f"Added: {self.records[new]['item']['name']}", time.time() + 6
        else:
            self.status_text, self.status_until = "Heard an item copy, but couldn't read it as an item", time.time() + 10

    def show_dup(self):
        """'Same item again?' as a banner INSIDE the app window (above the list), not a card over the game: it stays until you
        answer. The taskbar button flashes and a sound plays so you notice it."""
        while self.dup_pending and self.dup_pending[0][2]["id"] not in self.records:   # the row was removed meanwhile
            self.add_clean(self.dup_pending.pop(0)[0])
        if not self.dup_pending:
            return
        text, item, rec, n = self.dup_pending[0]
        kind = item.get("class", "Tablet").lower()                         # "tablet" or "jewel"
        self.shell.open("checks")
        outer = tk.Frame(self.checks_body, bg=C["accent"], padx=2, pady=2)
        outer.pack(before=self.checks_area, fill="x", padx=8, pady=(0, 8))
        card = tk.Frame(outer, bg=C["panel"], padx=16, pady=8)
        card.pack(fill="x")
        top = tk.Frame(card, bg=C["panel"])
        top.pack(fill="x")
        tk.Label(top, text="Same item again?", bg=C["panel"], fg=C["accent"], font=(FONT_TITLE, 16, "bold")).pack(side="left")
        more = len(self.dup_pending) - 1
        if more > 0:
            tk.Label(top, text=f"   (+{more} more waiting)", bg=C["panel"], fg=C["muted"], font=("Segoe UI", 9)).pack(side="left")
        ttk.Button(top, text=f"Different {kind} - add it", command=lambda: self.dup_answer(True)).pack(side="right")
        ttk.Button(top, text="Same item - skip it", style="Primary.TButton", command=lambda: self.dup_answer(False)).pack(side="right", padx=(0, 8))
        tk.Label(card, text=f"{item['name']}  -  {item['base']}", bg=C["panel"], fg=C["rare"] if item["rarity"] == "Rare" else C["magic"],
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", pady=(4, 2))
        tk.Label(card, text="   ·   ".join(pretty(m["text"]) for m in item["mods"]), bg=C["panel"], fg=C["text"], font=("Segoe UI", 9),
                 anchor="w", justify="left", wraplength=1100).pack(fill="x")
        here = "already in your list" + (f" ({n} times)" if n > 1 else "") + (f" - priced {fmt_div(rec['est'])}" if rec.get("est") is not None else "")
        tk.Label(card, text=f"An item with the exact same name and mods is {here}.", bg=C["panel"], fg=C["muted"], anchor="w",
                 font=("Segoe UI", 9)).pack(fill="x", pady=(8, 0))
        self.dup_win = outer
        self.root.title(f"? Same item again? - {APP_TITLE}")
        if sys.platform == "win32":                       # flash the taskbar button, without taking focus from the game
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
                ctypes.windll.user32.FlashWindow(hwnd, True)
                if SETTINGS.get("sound"):
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONQUESTION)
            except Exception:
                buglog.caught()

    def dup_answer(self, add):
        text, item, rec, n = self.dup_pending.pop(0)
        try:
            self.dup_win.destroy()
        except Exception:
            buglog.caught()
        self.dup_win = None
        self.root.title(APP_TITLE)
        if add:
            self.add_clean(text)
        else:
            rid = rec["id"]
            if rid in self.records and not self.visible(rec):
                SETTINGS["view"] = "All"
                self.view_var.set("All")
                self.rebuild_tree()
            if self.tree.exists(str(rid)):                   # jump to the existing row
                self.tree.selection_set(str(rid))
                self.tree.see(str(rid))
            self.status_text, self.status_until = f"Skipped - already in the list: {item['name']}", time.time() + 8
        self.show_dup()                                      # next question, if copies piled up meanwhile

    @staticmethod
    def read_any(text):
        """A copied item the price checker can price: tablets and jewels (their own checker), or any gear (1.41)."""
        return parse_item(text) or waystone.parse_waystone(text) or gear.parse_gear(text)

    def stack_price(self, name, qty, loud=False):
        """2.72.1: a copied stack -> its worth in the status line: poe.ninja's price, or (not listed there) the trade
        site's bulk exchange (one search, kept an hour). In the background; nothing is added to the list."""
        def work():
            from . import bulk
            from .wealth import WPRICES
            league = SETTINGS.get("league") or WPRICES.league or ""     # 2.73.4: always your league
            each, src = WPRICES.named(name), "poe.ninja"
            if each is None:
                xid = bulk.exchange_id(name)
                hit = bulk.price(league, xid, lambda a, c: RATES.to_div(a, c, league)) if xid else None
                each, src = (hit[0], bulk.text(hit)) if hit else (None, None)
            self.ui_q.put(("stack_priced", name, qty, each, src, loud))
        threading.Thread(target=work, daemon=True).start()

    def ev_stack_priced(self, name, qty, each, src, loud=False):
        if each is None:
            msg = f"{name}: no price on poe.ninja or the bulk exchange right now."
        elif qty == 1:
            msg = f"{name}: {fmt_div(each)} ({src})."
        else:
            msg = f"{name} x{qty:,}: {fmt_div(each * qty)} ({fmt_div(each)} each, {src})."
        if loud:                                         # 2.114.0: your price check key on it - a toast you'll see
            self.app_toast(msg, "Price check")
        self.status_text, self.status_until = msg, time.time() + 20
        self._say(msg, 12)
        self.last_stack_price = (name, qty, each, src)

    def add_item_text(self, text, src=None):
        item = self.read_any(text)
        if not item:
            return None
        src = src or "manual"                  # 2.42.0: which list it belongs to ("manual" or "tab:<id>")
        if src == "manual" and self.list_src() != "manual" and hasattr(self, "pc_mode"):
            self.pc_mode.pick("Manual Add")     # a Ctrl+Alt+C while a stash tab's list shows: show yours
            self.pctab_mode()
        rid = self.next_id
        self.next_id += 1
        try:                                           # 2.99.0: a unique's lines for Mod book › Unique rules
            from .gearbook import learn
            learn(item)
        except Exception:
            self.log_error("remembering a unique's lines")
        self.records[rid] = {"id": rid, "item": item, "state": "queued", "label": "", "total": 0,
                             "prices": [], "est": None, "qid": None, "time": time.time(), "resolved": False,
                             "mark": "new", "raw": text, "src": src}
        self.dirty = True
        self.batch_ids.add(rid)
        self.root.title(APP_TITLE)
        hidden_by_cat = not self.cat_ok(self.records[rid])
        if src != self.list_src():           # 2.73.2: it belongs to another list (a stash tab read while Manual Add
            self.engine.add(1, "resolve", rid)          # shows, or the other way round): priced, not shown here
            return rid
        if SETTINGS["view"] not in ("Not yet listed", "All") or hidden_by_cat:   # a new item would be hidden - show it
            if SETTINGS["view"] not in ("Not yet listed", "All"):
                SETTINGS["view"] = "Not yet listed"
                self.view_var.set(SETTINGS["view"])
            if hidden_by_cat:
                self.cat_var.set(self.ALL_CATS)
                self.rar_var.set("All")
                self.type_var.set("All")
            self.rebuild_tree()
        else:
            self.empty_lbl.place_forget()
            at_bottom = self.tree.yview()[1] >= 0.98          # only follow the new row if you were already at the bottom
            self.tree.insert("", "end", iid=str(rid), values=("",) * len(self.COLS))
            self.update_row(rid)
            if at_bottom:
                self.tree.see(str(rid))
            self.cat_refresh()                                # counts in the Category box
        self.engine.add(1, "resolve", rid)
        return rid

    # 2.117.0: the one way back to the window from a background thread - Tk isn't thread-safe, so a worker never
    # touches a widget (or calls root.after): it queues the call and poll_events runs it on the window's thread.
    def on_ui(self, fn, *args):
        """(any thread) Run fn(*args) on the window's thread, soon."""
        self.ui_q.put(("call", fn, args))

    def ev_call(self, fn, args):
        fn(*args)

    def run_bg(self, work, done):
        """work() on a background thread, then done(result) on the window's thread. mm_sync (tests): both now.
        An error in work() goes to the app's log and done isn't called (as before)."""
        if getattr(self, "mm_sync", False):
            return done(work())

        def go():
            try:
                r = work()
            except Exception:
                self.log_error("a background job")
                return
            self.on_ui(done, r)
        threading.Thread(target=go, daemon=True).start()

    def poll_events(self):
        try:
            while True:
                try:
                    ev = self.ui_q.get_nowait()
                except queue.Empty:
                    break
                try:
                    getattr(self, "ev_" + ev[0])(*ev[1:])
                except Exception:
                    self.log_error("handling " + ev[0])
            if time.time() - self.last_poll > 3:             # the clipboard watcher stalled: restart it
                self.log_error("clipboard watcher restarted")
                self.restart_watcher()
            for step in (self.update_status, self.update_limit_ui):
                try:
                    step()
                except Exception:
                    self.log_error(step.__name__)
            if self.dirty and time.time() - self.last_save > 4:
                self.save_session(background=True)           # 2.25.1: written off the window thread
        finally:
            self.root.after(100, self.poll_events)

    def ev_status(self, s):
        self.status_text, self.status_until = s, time.time() + 8

    def ev_queue(self):
        pass

    def ev_leagues(self, leagues):
        if not leagues:
            self.status_text = "Couldn't load the league list - type your league name into the box."
            self.league_box.configure(state="normal")
            return
        self.league_box["values"] = leagues
        if SETTINGS["league"] not in leagues:              # first start, or your old league is gone from the list:
            self.league_changed(self.newest_league(leagues))   # the newest league (same handling as picking one)
        self.league_var.set(SETTINGS["league"])

    @staticmethod
    def newest_league(leagues):
        """The current challenge league: the first one that isn't Standard / Hardcore / an SSF or HC version."""
        for l in leagues:
            low = l.lower()
            if low not in ("standard", "hardcore") and not low.startswith(("hc ", "hardcore ", "ssf ")) \
                    and "solo self-found" not in low and "(pl" not in low:
                return l
        return leagues[0]

    def close_splash(self):
        s = SPLASH[0]
        if s is not None and time.time() - s.started < 1.4:   # long enough to see, never a flicker
            self.root.after(int((1.4 - (time.time() - s.started)) * 1000) + 10, self.close_splash)
            return
        if s is not None:
            SPLASH[0] = None
            s.close()

    def ev_ready(self):
        self.close_splash()
        if time.time() > self.status_until:
            self.status_text = ""

    def ev_error(self, kind, msg, rid):
        if kind in ("price", "resolve") and rid in self.records and self.records[rid].get("src") == "ledger":
            return self.fl_priced(rid, error=msg)
        if kind in ("price", "resolve") and rid in self.records:
            rec = self.records[rid]
            said = re.search(r"server said: '(.*)'", msg)
            if said:                                          # 1.42: show the trade site's own reason, not the URL
                try:
                    said_txt = json.loads(said.group(1)).get("error", {}).get("message") or said.group(1)
                except Exception:
                    said_txt = said.group(1)
                msg = f"the trade site refused the search: {said_txt}"
            rec.update(state="error", label=msg[:160])
            if rid == getattr(self, "lib_rid", None):
                self.lib_price_show()
            self.update_row(rid)
            self.refresh_detail_if_selected(rid)
        else:
            self.status_text, self.status_until = f"Problem ({kind}): {msg[:140]}", time.time() + 20

    def pops_for(self, rec):
        """2.73.5: a price pop-up at the mouse only for an item you checked yourself (copied with the hotkey). A stash
        tab's items, the Strat Tracker's and the Item library's are priced out of sight - one at a time, so each
        looked like a single check and popped up wherever the mouse was."""
        return False                                # 2.79.0 (feedback): no pop-ups for Manual Add either - none at all

    def ev_resolved(self, rid):
        self.update_row(rid)
        self.refresh_detail_if_selected(rid)
        goods = self.good_mods(self.records[rid])
        if goods and SETTINGS["popups"] and self.pops_for(self.records[rid]):
            lines = [pretty(m["text"]) + (f"  -  listings with it ask about {fmt_div(med)}" if med is not None else "  -  learned as valuable")
                     for m, med in goods[:4]]
            self.toast.show(f"★ {len(goods)} valuable mod{'s' if len(goods) > 1 else ''}", lines, C["good"],
                            SETTINGS["toast_secs"])

    def ev_priced(self, rid):
        rec = self.records.get(rid)
        if not rec:
            return
        if rec.pop("open_after", False) and rec.get("qid") and not rec.get("changed"):
            self.open_qid(rec["qid"])                         # 2.105.1: Open on trade site waited for the search
        if rec.get("src") == "ledger":                        # 2.45.0: a Strat Tracker setup item, priced out of sight
            return self.fl_priced(rid)
        if rid == getattr(self, "lib_rid", None):            # priced from the Item library: show it there too
            self.lib_price_show()
        self.update_row(rid)
        self.refresh_detail_if_selected(rid)
        self.update_total_soon()                             # 2.25.1: once per burst of prices, not per price
        self.dirty = True
        if rec["state"] == "done":
            self.done_times.append(time.time())
            self.append_history(rec)
            if VALUE_LOG.add(rec, SETTINGS.get("league")):             # 2.4.0: Top value keeps it after a Clear list
                self.value_log_save_soon()
            # in a bulk run the end-of-batch summary covers this; only pop up for one-off checks
            if SETTINGS["popups"] and self.pops_for(rec) and len(self.batch_ids) <= 1 and rec["est"] is not None \
                    and rec["est"] >= SETTINGS["good_div"] and "WIDE SPREAD" not in rec.get("label", ""):
                self.toast.show(f"💰 ~{fmt_div(rec['est'])}", [rec["item"]["name"], rec["label"]], C["green"],
                                SETTINGS["toast_secs"])

    # ---------------- tracking: listed / removed, names, views
    def visible(self, rec):
        want = self.VIEW_MARK.get(SETTINGS.get("view", "Not yet listed"))
        return (rec.get("src", "manual") == self.list_src()             # 2.42.0: this list only
                and (want is None or rec.get("mark", "new") == want) and self.cat_ok(rec) and self.text_ok(rec))

    def text_ok(self, rec):
        """2.63.0: the Search box (name, base, type, label or a mod's text) and "Only ★" (a valuable mod)."""
        sv = getattr(self, "star_var", None)
        if sv is not None and sv.get() and not (rec.get("resolved") and self.key_mods(rec)):
            return False
        q = getattr(self, "search_var", None)
        q = q.get().strip().lower() if q is not None else ""
        if not q:
            return True
        it = rec["item"]
        hay = " ".join(str(x) for x in (it.get("name"), it.get("base"), it.get("class"), rec.get("label"))).lower()
        if all(w in hay for w in q.split()):
            return True
        mods = str(rec.get("raw") or "").lower()
        return all(w in hay or w in mods for w in q.split())

    def on_filter_text(self, soon=False):
        if soon:
            if getattr(self, "_flt_job", None):
                self.root.after_cancel(self._flt_job)
            self._flt_job = self.root.after(200, self.on_filter_text)
            return
        self._flt_job = None
        self.rebuild_tree()
        self.cat_refresh()
        self.clear_btn_state()

    def in_list(self, rec):
        return rec.get("src", "manual") == self.list_src()

    # ---------------- list filters by category / rarity / type (2.0 beta 3)
    ALL_CATS = "All items"
    CAT_ORDER = ("Tablets", "Waystones", "Jewels", "Rings", "Amulets", "Belts", "Helmets", "Body Armours", "Gloves", "Boots",
                 "Shields", "Bucklers", "Foci", "Quivers", "Charms", "Flasks", "Relics")

    @staticmethod
    def rec_cat(rec):
        """-> (category, rarity, type) of a row: ('Tablets', 'Rare', 'Ritual'), ('Gloves', 'Rare', 'Sirenscale Gloves')."""
        it = rec["item"]
        cls, base = str(it.get("class") or ""), str(it.get("base") or "")
        if cls in ("Tablet", "Tablets") or base.endswith(" Tablet"):
            return "Tablets", it.get("rarity") or "", base.replace(" Tablet", "") or "?"
        if cls in ("Jewel", "Jewels"):
            return "Jewels", it.get("rarity") or "", base or "?"
        if cls in ("Waystone", "Waystones"):
            return "Waystones", it.get("rarity") or "", base or "?"
        return (cls or "Other"), it.get("rarity") or "", base or "?"

    def cat_ok(self, rec):
        cat = getattr(self, "cat_var", None)
        if cat is None or cat.get() == self.ALL_CATS:
            return True
        c, r, t = self.rec_cat(rec)
        if c != self._cat_name(cat.get()):
            return False
        if self.rar_var.get() not in ("All", r):
            return False
        return self.type_var.get() in ("All", t)

    @staticmethod
    def _cat_name(label):
        return re.sub(r"\s*\(\d+\)$", "", label)                # "Tablets (12)" -> "Tablets"

    def cat_refresh(self):
        """Fill the three boxes from what is in the list right now (only choices that would show something)."""
        if not hasattr(self, "cat_box"):
            return
        want = self.VIEW_MARK.get(SETTINGS.get("view", "Not yet listed"))
        recs = [r for r in self.records.values() if (want is None or r.get("mark", "new") == want) and self.in_list(r)]
        cats = {}
        for r in recs:
            c, ra, t = self.rec_cat(r)
            cats.setdefault(c, []).append((ra, t))
        order = [c for c in self.CAT_ORDER if c in cats] + sorted(c for c in cats if c not in self.CAT_ORDER)
        self.cat_box["values"] = [self.ALL_CATS] + [f"{c} ({len(cats[c])})" for c in order]
        cur = self._cat_name(self.cat_var.get())
        if cur != self.ALL_CATS and cur in cats:
            self.cat_var.set(f"{cur} ({len(cats[cur])})")
        rows = cats.get(cur, []) if cur != self.ALL_CATS else []
        rar_order = ["Unique", "Rare", "Magic", "Normal"]
        rars = [x for x in rar_order if any(ra == x for ra, _t in rows)]
        types = sorted({t for ra, t in rows if self.rar_var.get() in ("All", ra)})
        self.rar_box["values"] = ["All"] + rars
        self.type_box["values"] = ["All"] + types
        state = "readonly" if rows else "disabled"
        self.rar_box.configure(state=state)
        self.type_box.configure(state=state)
        shown = sum(1 for r in self.records.values() if self.visible(r))
        mine = sum(1 for r in self.records.values() if self.in_list(r))
        self.cat_count.config(text=f"Showing {shown} of {mine} items" if mine else "")
        self.list_note()

    def list_note(self):
        """2.63.0: the list's header strip - which list, how many shown, how it's sorted."""
        head = getattr(self, "list_head", None)
        if head is None:
            return
        t = self.pctab_current() if self.list_src() != "manual" else None
        head.set_title(f"Stash tab · {t['name']}" if t else "Items · Manual Add")
        n = self.cat_count.cget("text")
        srt = {"est": "value", "conf": "confidence", "listings": "listings", "priced": "when priced", "name": "name",
               "type": "type", "mark": "status", "vmods": "★ mods", "ilvl": "item level"}.get(getattr(self, "sort_col", None))
        head.note(n + (f" · sorted by {srt}" if srt and n else ""))

    def on_cat(self, changed="cat"):
        if changed == "cat":
            self.rar_var.set("All")
            self.type_var.set("All")
        elif changed == "rar":
            self.type_var.set("All")
        self.cat_refresh()
        self.rebuild_tree()
        self.clear_btn_state()

    def clear_btn_state(self):
        btn = getattr(self, "clear_btn", None)
        if btn is not None:
            on = ((self.cat_var.get(), self.rar_var.get(), self.type_var.get()) != (self.ALL_CATS, "All", "All")
                  or bool(self.search_var.get().strip()) or self.star_var.get())
            btn.config(state="normal" if on else "disabled")

    def cat_reset(self):
        self.cat_var.set(self.ALL_CATS)
        if hasattr(self, "search_var"):
            self.star_var.set(False)
            self.search_var.set("")
            if getattr(self, "_flt_job", None):
                self.root.after_cancel(self._flt_job)
                self._flt_job = None
        self.on_cat()

    def rebuild_tree(self):
        sel = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        shown = 0
        for rid in sorted(self.records, key=lambda r: self.stash_key(self.records[r])):   # 2.87.0: a tab in its order
            if self.visible(self.records[rid]):
                self.tree.insert("", "end", iid=str(rid), values=("",) * len(self.COLS))
                self.update_row(rid)
                shown += 1
        self._apply_sort()
        keep = [i for i in self.tree.get_children() if i in sel]
        if keep:
            self.tree.selection_set(keep)
        else:
            self.show_detail(None)
        if shown:
            self.empty_lbl.place_forget()
        else:
            self.empty_lbl.config(text=("Nothing in this view." + (" Press Clear filters to see every item." if self.cat_var.get() != self.ALL_CATS else ""))
                                  if any(self.in_list(r) for r in self.records.values())
                                  else self.pctab_empty_text() if self.list_src() != "manual" else self.empty_text)
            self.empty_lbl.place(relx=0.5, rely=0.45, anchor="center")
        self.update_total()

    def _on_checks(self):
        """Is the Price checks window the one in front? (C / O / Del / Ctrl+A act on its list.)"""
        sh = getattr(self, "shell", None)
        return sh is None or sh.active == "checks"

    def toolbar_for_page(self):
        """2.0 beta 7: each window has its own toolbar (kept so older callers don't break)."""

    def on_page(self, _e=None):
        """Open (or bring to the front) the window named in page_var."""
        try:
            self.shell.open(self.page_key.get(self.page_var.get(), "checks"))
        except Exception:
            self.log_error("switching page")

    def on_view(self, _e=None):
        SETTINGS["view"] = self.view_var.get()
        save_json("settings.json", SETTINGS)
        self.rebuild_tree()

    def copy_name(self, rec, announce=False):
        """Put the item's name on the clipboard (and remember it, so it isn't mistaken for a new item)."""
        name = rec["item"]["name"]
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(name)
            self.last_clip = self.own_clip = name
        except tk.TclError:
            return
        if announce:
            self.status_text, self.status_until = f"Copied \"{name}\" - Ctrl+V in your stash search", time.time() + 6

    def mark_selected(self, mark):
        sel = [int(i) for i in self.tree.selection()]
        if not sel:
            return
        recs = [self.records[r] for r in sel if r in self.records]
        if mark in ("listed", "removed", "sold") and recs and all(r.get("mark", "new") == mark for r in recs):
            mark = "new"                                  # already listed / removed: the button switches it back (1.35)
        typed_sold = ""
        if mark == "sold":                                # 2.21.0: what it really sold for
            typed_sold = (getattr(self, "sold_var", None).get().strip() if getattr(self, "sold_var", None) else "")
            if len(sel) != 1 or not parse_price(typed_sold):
                return self._say("Type what it sold for in the item's panel (e.g. 3 div, 150 chaos, 40 ex), then press "
                                 "Mark as sold.", 10)
        self.undo = [(r["id"], r.get("mark", "new"), r.get("list_price")) for r in recs]
        self.undo_deleted = []
        self.undo_btn.config(state="normal")
        word = {"listed": "listed", "removed": "removed", "sold": f"sold for {typed_sold}", "new": "not listed"}[mark]
        self._say(f"Marked {len(recs)} item{'s' if len(recs) != 1 else ''} as {word}. Ctrl+Z or Undo puts it back.", 12)
        typed = ""
        if mark == "listed" and len(sel) == 1 and self.price_var is not None:
            typed = self.price_var.get().strip()
        kids = list(self.tree.get_children())
        first = min(kids.index(str(r)) for r in sel if str(r) in kids)
        for rid in sel:
            rec = self.records.get(rid)
            if not rec:
                continue
            if rec.get("mark") == "sold" and mark != "sold":     # unmarked: that sale isn't learned from any more
                MARKET.forget_sale(rec["item"])
            rec["mark"] = mark
            VALUE_LOG.mark(rec)
            if mark == "sold":                                    # 2.21.0: a real sale - the Mod book learns from it
                rec["sold_price"] = typed_sold
                MARKET.save_sale(rec["item"], parse_price(typed_sold), typed_sold)
            if mark == "listed":
                rec["list_price"] = typed or (fmt_div(rec["est"]) if rec.get("est") is not None and not rec.get("skip") else "")
                div = parse_price(rec["list_price"])              # remembered in market.db: a hint on similar items later
                if div:
                    MARKET.save_listed(rec["item"], rec.get("est") if not rec.get("skip") else None, div)
            if self.visible(rec):
                self.update_row(rid)
            elif self.tree.exists(str(rid)):
                self.tree.delete(str(rid))
        self.dirty = True
        self.value_log_save_soon()
        self.update_total()
        left = list(self.tree.get_children())
        if any(str(r) in left for r in sel):                  # still visible (Show: All) - just refresh the panel
            self.refresh_detail_if_selected(sel[0])
        elif left:                                            # move on to the next item in the list
            nxt = left[min(first, len(left) - 1)]
            self.tree.selection_set(nxt)
            self.tree.see(nxt)
        else:
            self.show_detail(None)
        self.update_mark_buttons()

    def undo_mark(self):
        """Put the items of the last Mark listed / removed back the way they were, and select them again
        (2.0 beta 19: or the items you just deleted)."""
        if getattr(self, "undo_deleted", None):
            back = []
            for rid, rec in self.undo_deleted:
                self.records[rid] = rec
                if rec.get("raw"):
                    self.seen_texts[hash(rec["raw"].strip())] = rid
                back.append(str(rid))
            self.undo_deleted = []
            self.undo_btn.config(state="disabled")
            self.dirty = True
            self.empty_lbl.place_forget()
            self.rebuild_tree()
            self.update_total()
            shown = [i for i in back if self.tree.exists(i)]
            if shown:
                self.tree.selection_set(shown)
                self.tree.see(shown[0])
            return self._say(f"Undone: {len(back)} item{'s' if len(back) != 1 else ''} back in the list.", 10)
        if not self.undo:
            return self._say("Nothing to undo.", 6)
        back = []
        for rid, mark, lp in self.undo:
            rec = self.records.get(rid)
            if not rec:
                continue
            rec["mark"] = mark
            VALUE_LOG.mark(rec)
            if lp is None:
                rec.pop("list_price", None)
            else:
                rec["list_price"] = lp
            back.append(str(rid))
        self.undo = []
        self.undo_btn.config(state="disabled")
        self.dirty = True
        self.rebuild_tree()
        shown = [i for i in back if self.tree.exists(i)]
        if shown:
            self.tree.selection_set(shown)
            self.tree.see(shown[0])
        self.update_mark_buttons()
        self._say(f"Undone: {len(back)} item{'s' if len(back) != 1 else ''} back as before"
                  + ("" if len(shown) == len(back) else " (some are hidden by the Show filter)") + ".", 10)

    def update_mark_buttons(self):
        """The toolbar buttons say what they will do: mark, or switch back."""
        recs = [self.records[int(i)] for i in self.tree.selection() if int(i) in self.records]
        for btn, mark, on, off in ((self.mark_btn, "listed", "✔ Mark listed", "↺ Unmark listed"),
                                   (self.remove_btn, "removed", "✖ Mark removed", "↺ Unmark removed"),
                                   (getattr(self, "item_mark_btn", None), "listed", "✔ Mark listed", "↺ Unmark listed")):
            if btn is None:
                continue
            btn.config(text=off if recs and all(r.get("mark", "new") == mark for r in recs) else on)
        for btn in (getattr(self, "mark_btn", None), getattr(self, "remove_btn", None),
                    getattr(self, "delete_btn", None)):        # P1 (2.103.0): they act on the picked rows - lit only then
            if btn is not None:
                btn.config(state="normal" if recs else "disabled")

    def toggle_mod(self, rec, mod, checked):
        g = impact_key(norm(mod["text"]))              # what the Mod rules tab says for every tablet
        self.set_item_impact(rec, mod, ("normal" if g == "ignore" else g) if checked else "ignore")

    def card_changed(self, rec):
        """2.88.2 (feedback): on Price Checks / Favorites a change on the card waits for Search; the card
        says so. Bulk Pricing prices it again at once, as before."""
        if rec.get("src") in ("pc", "fav"):
            rec["changed"] = True
            self.dirty = True
            if getattr(self, "_card_quiet", False):       # 2.103.3: the row is painted in place
                return self.fav_rec_changed(rec, redraw=False) if rec.get("src") == "fav" else None
            if rec.get("src") == "pc" and rec["id"] == getattr(self, "pc_rid", None):
                return self.pc_show(rec, card_only=True)    # 2.103.2: the listings stay (they flickered)
            if rec.get("src") == "fav":                     # 2.103.3: the listings stay (they flickered)
                return self.fav_rec_changed(rec, card_only=True)
            return self.refresh_detail_if_selected(rec["id"])
        # 2.108.0 (feedback: Bulk Pricing searched on every tick and redrew the card): Bulk Pricing waits for
        # Search again too, and a tick is painted in place - as on Price Checks
        rec["changed"] = True
        self.dirty = True
        if getattr(self, "_card_quiet", False):
            return None
        if getattr(self, "shown_rec", None) is rec:
            return self.show_detail(rec)
        return None

    def set_item_impact(self, rec, mod, imp):
        """Tick / untick / star a mod on this one item only (pack size is worth money on some tablets, not all).
        2.79.2 (feedback: "nothing is clickable under stat filters"): the override goes only when it matches what
        this mod would be anyway on this item - gear mods the price check left out (filler, low tier) can be ticked."""
        from .trade import ov_key
        k = ov_key(mod)
        ov = rec.setdefault("ov", {})
        mine = ov.pop(k, None)
        default = mod_impact(rec, mod)
        if mine is not None:
            ov[k] = mine
        if imp == default:
            ov.pop(k, None)
        else:
            ov[k] = imp
        self.dirty = True
        self.card_changed(rec)

    def flash_window(self):
        """Make the taskbar button flash and put the result in the title, so you notice even while in game."""
        n = sum(1 for r in self.records.values() if r["state"] == "done")
        self.root.title(f"✔ Pricing finished ({n} priced) - {APP_TITLE}")
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
                ctypes.windll.user32.FlashWindow(hwnd, True)
            except Exception:
                buglog.caught()

    def reprice(self, rids):
        for rid in rids:
            rec = self.records.get(rid)
            if not rec:
                continue
            rec["state"] = "queued"
            pc = rec.get("src") in ("pc", "fav")                 # 2.80.0: Price Checks go first (2.84.0: Favorites)
            if pc:                                               # 2.87.0: a new Search replaces its older one
                rec["gen"] = rec.get("gen", 0) + 1
            rec.pop("changed", None)
            self.batch_ids.add(rid)
            self.update_row(rid)
            self.refresh_detail_if_selected(rid)
            self.engine.add(0 if pc else (2 if rec["resolved"] else 1), "price" if rec["resolved"] else "resolve", rid)

    def reprice_all(self):
        self.reprice([rid for rid, r in self.records.items() if r.get("mark", "new") == "new" and self.in_list(r)])

    def on_listing_rules(self, _e=None):
        SETTINGS["status"], SETTINGS["age"] = self.status_var.get(), self.age_var.get()
        save_json("settings.json", SETTINGS)
        self.pc_rules_text()
        self.status_text = "Search rules changed - new items use them now; press Re-price all to refresh the rest."
        self.status_until = time.time() + 25

    # ---------------- saving the list between sessions
    _session_lock = threading.Lock()

    def save_session(self, background=False):
        """Price checks list -> session.json. 2.25.1: with background=True the file is written on another thread -
        a long list took seconds to write, and the app froze every few seconds while prices came in."""
        try:
            recs = []
            for rec in list(self.records.values()):
                r = dict(rec)
                it = dict(rec["item"])
                it["mods"] = [{**m, "flags": sorted(m["flags"])} for m in rec["item"]["mods"]]
                r["item"] = it
                if rec.get("src") in ("pc", "fav"):        # 2.87.0: Recent keeps its listings over a restart
                    from .trade import RAW_LISTINGS
                    ids = [i for st in rec.get("stages") or [] for i in st.get("ids") or []]
                    r["_raw"] = [RAW_LISTINGS[i] for i in dict.fromkeys(ids) if i in RAW_LISTINGS][:20]
                recs.append(r)
            data = {"next_id": self.next_id, "records": recs}
        except Exception:
            return                          # the engine was editing an item at that moment - try again shortly
        self.dirty, self.last_save = False, time.time()

        def write():
            with self._session_lock:          # one write at a time, newest last
                try:
                    save_json("session.json", data)
                except Exception:
                    self.dirty = True
        if background:
            if getattr(self, "_session_thread", None) is not None and self._session_thread.is_alive():
                self.dirty = True             # still writing the last one: try again in a few seconds
                return
            self._session_thread = threading.Thread(target=write, daemon=True)
            self._session_thread.start()
        else:
            t = getattr(self, "_session_thread", None)
            if t is not None and t.is_alive():
                t.join(10)
            write()

    def load_session(self):
        data = load_json("session.json", {})
        for r in data.get("records", []):
            try:
                for m in r["item"]["mods"]:
                    m["flags"] = set(m.get("flags", []))
                r["prices"] = [tuple(p) for p in r.get("prices", [])]
                r.setdefault("mark", "new")
                if not r["item"].get("ilvl") and r.get("raw"):  # 2.73.5: saved before 2.73.2 read it - from the copy
                    m = re.search(r"^Item Level:\s*(\d+)", r["raw"], re.M)
                    r["item"]["ilvl"] = int(m.group(1)) if m else None
                if r.get("src") == "ledger":                  # (a Strat Tracker item that was still being priced)
                    continue
                raw = r.pop("_raw", None)
                if raw:                                       # 2.87.0: a Price Checks item's listings, as they were
                    from .trade import keep_raw
                    for e in raw:
                        keep_raw(e)
                self.records[int(r["id"])] = r
                if r.get("state") in ("queued", "pricing"):      # was still waiting when the app closed
                    r["state"] = "queued"
                    self.engine.add(2 if r.get("resolved") else 1, "price" if r.get("resolved") else "resolve", r["id"])
            except Exception:
                continue
        self.next_id = max([int(data.get("next_id", 1))] + [rid + 1 for rid in self.records])
        self.seen_texts = {hash(r["raw"].strip()): rid for rid, r in self.records.items() if r.get("raw")}
        self.rebuild_tree()
        try:                                                  # 2.87.0 (feedback: Recent was empty after a restart):
            recs = self.pc_recs()                             # the page was built before the list was read
            self.pc_refresh_hist()
            if recs and not self.records.get(getattr(self, "pc_rid", None)):
                self.pc_show(recs[0])
        except Exception:
            self.log_error("Price Checks' Recent")

    # ---------------- mod rules tab
    def build_rules_page(self, tab, cat):
        ns = types.SimpleNamespace(cat=cat, keys={}, filt=tk.StringVar())
        self.rt[cat] = ns
        ns.filt.trace_add("write", lambda *a: self.refresh_rules(cat))
        # 2.114.0 (P8, feedback: "make Tier the only rating"): one rating, S-F - S / A = High (always searched),
        # B / C / D = Normal, F = Ignore - as on Gear rules. (Impact and its High / Normal / Ignore buttons are gone.)
        rbar = tk.Frame(tab, bg=C["panel"], padx=8, pady=8)
        rbar.pack(fill="x")
        tk.Label(rbar, text="Filter", bg=C["panel"], fg=C["muted"]).pack(side="left", padx=(0, 8))
        ttk.Entry(rbar, textvariable=ns.filt, width=18).pack(side="left")
        ttk.Button(rbar, text="Rate mods one at a time ›",               # 2.96.0 (2.120.0: opens Rate Mods)
                   command=lambda c=cat: self.rm_open(c)).pack(side="left", padx=(16, 0))
        more = ttk.Button(rbar, text="More ▾", style="Quiet.TButton")
        more.configure(command=lambda b=more, c=cat: self.mb_more(b, c))
        more.pack(side="right")
        tbar = tk.Frame(tab, bg=C["panel"], padx=8)
        tbar.pack(fill="x")
        tk.Label(tbar, text="Rate selected:", bg=C["panel"], fg=C["muted"]).pack(side="left", padx=(0, 8))
        for t in SHOWN_TIERS:
            tb_ = ttk.Button(tbar, text=t, width=3, command=lambda t=t: self.tiers_selected(t))
            tb_.pack(side="left", padx=(0, 4))
            if t == TIER_F:
                Tooltip(tb_, F_TIP)
        ttk.Button(tbar, text="Clear", command=lambda: self.tiers_selected(None), style="Quiet.TButton").pack(side="left", padx=(4, 0))
        help_ = tk.Label(tab, text="S / A = High (always searched), B / C / D = Normal, F = Ignore (never searched). When no "
                           "listing has all of an item's mods, D mods are left out first, then C. \"auto\" = the app's "
                           "own rating until you rate it.", bg=C["panel"], fg=C["muted"], font=("Segoe UI", 9),
                 anchor="w", justify="left", wraplength=900, padx=12)
        help_.pack(fill="x", pady=(8, 0))
        help_.bind("<Configure>", lambda e, l=help_: l.config(wraplength=max(300, e.width - 24)))
        if cat in SCOPED_CATS:                           # 2.6.0: what these rules are for
            tk.Label(tab, text={"waystone": "Waystones are priced on their numbers (pack size, rarity ...), not their "
                                            "mods. Rate the mods you want or don't want, and Regex uses it: ★ on the "
                                            "mod, and ★ Select valuable.",
                                "relic": "Rate the relic mods you're after. Regex marks them ★ and ★ Select valuable "
                                         "picks them; Market Insights lists them."}[cat],
                     bg=C["panel"], fg=C["muted"], anchor="w", justify="left", wraplength=760, padx=12,
                     font=("Segoe UI", 9)).pack(fill="x")
        bar = SectionBar(tab, {"tablet": "Tablet mods", "jewel": "Jewel mods", "waystone": "Waystone mods",
                               "relic": "Relic mods"}.get(cat, "Mods"))     # 2.69.0
        bar.pack(fill="x", padx=8, pady=(8, 0))
        ns.info = BarNote(bar)                          # 2.114.0: the counts sit in the section's strip

        rvp = Viewport(tab)
        rvp.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        rtab = rvp.body
        ns.tv = ttk.Treeview(rtab, columns=("tier", "type", "mod", "on", "learned"), show="headings",
                             selectmode="extended")
        for cid, title, w, anchor in (("tier", "Rating", 80, "w"), ("type", "Type", 70, "w"),
                                      ("mod", "Mod", 420, "w"), ("on", "Found on", 150 if cat == "tablet" else 260, "w"),
                                      ("learned", "Learned", 210, "w")):
            ns.tv.heading(cid, text=title)
            ns.tv.column(cid, width=w, anchor=anchor, stretch=(cid == "mod"))
        rsb = ttk.Scrollbar(rtab, orient="vertical", command=ns.tv.yview)
        ns.tv.configure(yscrollcommand=rsb.set)
        rsb.pack(side="right", fill="y")
        ns.tv.pack(fill="both", expand=True)
        ns.tv.tag_configure("high", foreground=C["good"])
        ns.tv.tag_configure("ignore", foreground=C["muted"])
        ns.tv.bind("<Double-1>", lambda e, c=cat: self.cycle_rule(e, c))
        if cat in SCOPED_CATS:
            ns.tv.heading("on", text="Tiers" if cat == "waystone" else "Relic sizes")
            ns.tv["displaycolumns"] = ("tier", "type", "mod", "on")           # nothing is learned for these
        self.list_register("modbook", ns.tv)                                      # 2.4.0: Ctrl+A, Shift / Ctrl+click

    def run_migrations(self):
        """The app's one-time changes not done on this PC yet (soe2/migrations.py, stage "app") - rules, Mod book."""
        from . import migrations
        migrations.run(SETTINGS, "app", lambda: save_json("settings.json", SETTINGS))

    MB_TABS = (("tablet", "Tablet rules"), ("jewel", "Jewel rules"), ("waystone", "Waystone rules"),
               ("relic", "Relic rules"), ("gear", "Gear rules"), ("unique", "Unique rules"))

    def rules_cat(self):
        """Which rules page is showing: 'tablet', 'jewel', 'waystone', 'relic', 'gear' or 'unique'."""
        try:
            i = self.mb_nb.index(self.mb_nb.select())
            return self.MB_TABS[i][0] if 0 <= i < len(self.MB_TABS) else "tablet"
        except Exception:
            return "tablet"

    def refresh_rules(self, cat=None):
        for c in ((cat,) if cat else [c for c, _t in self.MB_TABS]):
            if c in self.rt:
                if c in ("gear", "unique"):
                    self._refresh_picker_rules(c)
                else:
                    self._refresh_rules(c)

    def _refresh_scoped_rules(self, cat):
        """2.6.0: the Waystone / Relic rules page - every mod from the game data (regexdata.json, RePoE), one row per
        mod (a two-line mod is one row, and its rule covers both lines)."""
        from . import regex as R
        ns = self.rt[cat]
        q = ns.filt.get().lower().strip()
        keep = {tuple(ns.keys.get(i) or ()) for i in ns.tv.selection()}
        ns.tv.delete(*ns.tv.get_children())
        ns.keys = {}
        order = {"high": 0, "normal": 1, "ignore": 2}
        every = {t for m in R.mods(cat) for t in m.get("tags") or []} - {"Any"}
        rows = []
        for m in R.mods(cat):
            lines = m.get("lines") or [m["line"]]
            keys = [rule_key(cat, norm(l)) for l in lines]
            text = " / ".join(l[:1].upper() + l[1:] for l in lines)
            if q and q not in text.lower():
                continue
            imp = max((impact_key(k) for k in keys), key=lambda i: -order[i])
            tags = set(m.get("tags") or [])
            on = ("All" if not tags or "Any" in tags or tags >= every else
                  ", ".join(sorted(tags, key=lambda t: (len(t), t))))
            rows.append((order[imp], text.lower(), keys, text, imp, (m.get("side") or "").title(), on))
        for n, (_o, _t, keys, text, imp, side, on) in enumerate(sorted(rows)):
            iid = f"r{n}"
            ns.keys[iid] = keys
            ns.tv.insert("", "end", iid=iid, values=(self.mb_rating(keys), side, text, on, ""),
                         tags=(imp,) if imp != "normal" else ())
            if tuple(keys) in keep:
                ns.tv.selection_add(iid)
        counts = {i: sum(1 for r in rows if r[4] == i) for i in IMPACTS}
        ns.info.config(text=self.mb_counts(counts) + ("" if rows or q else "  ·  regexdata.json not found"))

    def _refresh_rules(self, cat):
        if cat in SCOPED_CATS:
            return self._refresh_scoped_rules(cat)
        ns = self.rt[cat]
        src, kind_src = (TABS, TAB_KINDS) if cat == "tablet" else (JEWELS, JEWEL_KINDS)
        q = ns.filt.get().lower().strip()
        known = {k: [v[0], set(v[1])] for k, v in src.items()}

        def short(base):
            return base.replace(" Tablet", "")

        def add(text, base):
            if not text:
                return
            k = norm(text)
            if mod_cat(k, base) != cat:
                return
            known.setdefault(k, [pretty(text), set()])[1].add(short(base))
        kinds = {k: set(v) for k, v in kind_src.items()}
        for rec in list(self.records.values()):
            for m in rec["item"]["mods"]:
                add(m["text"], rec["item"]["base"])
                if m.get("kind") in ("Prefix", "Suffix") and mod_cat(norm(m["text"]), rec["item"]["base"]) == cat:
                    kinds.setdefault(norm(m["text"]), set()).add(m["kind"])
        for e in list(MODBOOK.values()):
            add(e.get("text", ""), e.get("base", ""))
        every = {t for _, ts in src.values() for t in ts}
        keep = {ns.keys.get(i) for i in ns.tv.selection()}
        ns.tv.delete(*ns.tv.get_children())
        ns.keys = {}
        order = {"high": 0, "normal": 1, "ignore": 2}
        rows = [(order[impact_key(k)], text.lower(), k, text, types) for k, (text, types) in known.items()
                if not q or q in text.lower()]
        for n, (_, _, k, text, types) in enumerate(sorted(rows)):
            imp = impact_key(k)
            on = ("All tablets" if cat == "tablet" else "All jewels") if every and types >= every else ", ".join(sorted(types))
            iid = f"r{n}"
            ns.keys[iid] = k
            kd = kinds.get(k, set())
            li = learned_info(k)
            if li and li["tier"] == "high":
                learned = (f"High (community: {li['lift']:.1f}x, {li['n']} listings)" if li.get("from") == "community" else
                           ("High (carried over from " + li["from"] + ")") if li.get("from") else
                           f"High ({li['lift']:.1f}x, {li['n']} listings)")
                if RULES.get(k) == "ignore":
                    learned = "⚠ " + learned + " - you ignore it"
            elif k in COMMUNITY_ACTIVE:
                from .mods import BOARD_RATED
                learned = (f"Community ★ ({BOARD_RATED[k][0]} of {BOARD_RATED[k][1]} players)" if k in BOARD_RATED
                           else f"Shared by {len(COMMUNITY[k]['from'])}")
            elif k in COMMUNITY_DISAGREE:
                learned = "Shared - your data disagrees"
            else:
                learned = ""
            ns.tv.insert("", "end", iid=iid, values=(self.mb_rating([k]), "/".join(sorted(kd)) if len(kd) == 1 else ("Both" if kd else ""), text, on, learned or "-"),
                                 tags=(imp,) if imp != "normal" else ())
            if k in keep:
                ns.tv.selection_add(iid)
        counts = {i: sum(1 for k in known if impact_key(k) == i) for i in IMPACTS}
        fname = "tabs.txt" if cat == "tablet" else "jewels.txt"
        ns.info.config(text=self.mb_counts(counts) + ("" if src else f"  ·  {fname} not found - put it in {DATA_DIR} or next to the app and restart"))

    @staticmethod
    def mb_counts(counts):
        """2.114.0: the strip's note - by rating, not High / Normal / Ignore."""
        return f"{counts['high']} S/A  ·  {counts['normal']} B-D  ·  {counts['ignore']} F"

    @staticmethod
    def mb_rating(keys):
        """2.114.0: a row's one rating: S-D, F (ignored), with "· auto" when it's the app's own (you haven't rated it).
        A waystone / relic row can hold several lines: the best of them."""
        best = None
        for k in keys:
            t = tier_key(k) or TIER_F
            if best is None or SHOWN_TIERS.index(t) < SHOWN_TIERS.index(best[0]):
                best = (t, k)
        if best is None:
            return ""
        t, k = best
        return t if (k in RULES or k in TIERS) else f"{t}  · auto"

    def mb_more(self, btn, cat):
        """2.114.0: Export / Import (and Remove imported) - used now and then, so under More."""
        from .listkit import _menu
        m = _menu(btn)                                   # (the app's menu look, as on right-click menus)
        m.add_command(label="Export rules…", command=self.export_rules)
        m.add_command(label="Import rules…", command=self.import_rules)
        if cat not in SCOPED_CATS and any(mod_cat(k) == cat for k in COMMUNITY):     # (votes imported before 2.20.0)
            m.add_separator()
            m.add_command(label="Remove imported", command=self.clear_imported_rules)
        try:
            m.tk_popup(btn.winfo_rootx(), btn.winfo_rooty() + btn.winfo_height())
        finally:
            m.grab_release()

    # ---------------- sharing rules with other people
    def _say(self, text, secs=30):
        self.status_text = text
        self.status_until = time.time() + secs

    def rules_of_cat(self, cat):
        """{rule key: impact} of YOUR rules for this page's kind of mod."""
        if cat in SCOPED_CATS:
            return {k: v for k, v in RULES.items() if scoped(k) == cat}
        return {k: v for k, v in RULES.items() if not scoped(k) and mod_cat(k) == cat}

    def export_rules(self):
        """2.20.0: write your rules for this page (High / Normal / Ignore and tiers) to a file - to keep, move to another
        PC or give to a friend. Import rules reads it back. (Before 2.20.0 only High mods went out, as 'votes'.)"""
        if not SETTINGS.get("share_id"):
            SETTINGS["share_id"] = "%08x" % random.getrandbits(32)
            save_json("settings.json", SETTINGS)
        cat = self.rules_cat()
        rules = self.rules_of_cat(cat)
        tiers = {k: t for k, t in TIERS.items() if (scoped(k) == cat if cat in SCOPED_CATS else
                                                   not scoped(k) and mod_cat(k) == cat)}
        if not rules and not tiers:
            self.app_toast(f"You haven't set any {cat} mod rules yet.", "Export rules")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile=f"my_{cat}_mod_rules.json",
                                            filetypes=[("Mod rules", "*.json")])
        if not path:
            return
        high = [{"text": (TABS.get(k) or JEWELS.get(k) or [pretty(k.split(":", 1)[-1])])[0], "source": "my rule"}
                for k, v in rules.items() if v == "high"]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"app": "StashOfExile2", "format": 2, "id": SETTINGS["share_id"],
                           "exported": time.strftime("%Y-%m-%d"), "league": SETTINGS.get("league", ""),
                           "category": cat, "rules": rules, "tiers": tiers,
                           "high": high}, f, indent=1, ensure_ascii=False)        # "high": what older versions read
        except Exception as e:
            self.app_toast(f"Could not save the file: {e}", "Export rules", kind="error")
            return
        n = {i: sum(1 for v in rules.values() if v == i) for i in IMPACTS}
        self._say(f"Exported {len(rules)} {cat} rules ({n['high']} high, {n['normal']} normal, {n['ignore']} ignored)"
                  + (f" and {len(tiers)} tiers" if tiers else "") + f" to {os.path.basename(path)}.", 15)

    @staticmethod
    def read_rules_file(path):
        """-> (category or None, {rule key: impact}, {rule key: tier}). Raises ValueError for a file that isn't one."""
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict) or d.get("app") != "StashOfExile2":
            raise ValueError("not a StashOfExile2 rules file")
        cat = d.get("category") if d.get("category") in ("tablet", "jewel", "waystone", "relic") else None
        rules, tiers = {}, {}
        if isinstance(d.get("rules"), dict):                             # 2.20.0 files: everything, by rule key
            for k, v in d["rules"].items():
                if isinstance(k, str) and v in IMPACTS:
                    rules[k] = v
            for k, t in (d.get("tiers") or {}).items():
                if isinstance(k, str) and t in TIER_ORDER:
                    tiers[k] = t
        elif isinstance(d.get("high"), list):                            # older files: a list of High mods
            if len(d["high"]) > SHARE_MAX_HIGH * 4:
                raise ValueError(f"claims {len(d['high'])} high mods, looks wrong")
            for e in d["high"]:
                t = e.get("text") if isinstance(e, dict) else e if isinstance(e, str) else None
                if isinstance(t, str) and t.strip():
                    rules[rule_key(cat, norm(t)) if cat in SCOPED_CATS else norm(t)] = "high"
        else:
            raise ValueError("has no rules in it")
        fixed = {}
        for k, v in rules.items():                                      # older wording -> today's
            head = scoped(k)
            body = k.split(":", 1)[1] if head else k
            fixed[f"{head}:{current_key(body)}" if head else current_key(body)] = v
        return cat, fixed, tiers

    def import_rules(self):
        """2.20.0: read rule files (your own export, or a friend's) INTO your Mod book. Rules you already have that say
        something else are kept unless you choose to take the file's. (Before 2.20.0 an import only added 'votes' that
        could be outvoted by your own data, and your own export was refused - so it looked like nothing happened.)"""
        paths = filedialog.askopenfilenames(filetypes=[("Mod rules", "*.json")])
        if not paths:
            return
        incoming, tiers_in, bad = {}, {}, []
        for path in paths:
            try:
                _cat, rules, tiers = self.read_rules_file(path)
            except Exception as e:
                bad.append(f"{os.path.basename(path)}: {e}")
                continue
            incoming.update(rules)
            tiers_in.update(tiers)
        unknown = [k for k in incoming if not (scoped(k) or k in TABS or k in JEWELS or k in TEXT2SID)]
        for k in unknown:
            incoming.pop(k)
        new = {k: v for k, v in incoming.items() if k not in RULES}
        same = [k for k, v in incoming.items() if RULES.get(k) == v]
        differ = {k: v for k, v in incoming.items() if k in RULES and RULES[k] != v}
        take = False
        if differ:
            ans = messagebox.askyesnocancel(
                "Import rules", f"{len(new)} new rule(s) will be added.\n\n{len(differ)} rule(s) in the file differ from "
                                f"yours. Use the file's for those?\n\nYes = use the file's   ·   No = keep yours")
            if ans is None:
                return
            take = bool(ans)
        for k, v in list(new.items()) + (list(differ.items()) if take else []):
            RULES[k] = v
        t_new = 0
        for k, t in tiers_in.items():
            if (k not in TIERS or take) and TIERS.get(k) != t:
                TIERS[k] = t
                t_new += 1
        save_json("mod_rules.json", RULES)
        save_json("mod_tiers.json", TIERS)
        changed = set(new) | (set(differ) if take else set()) | set(tiers_in)
        self._after_rules_change(changed)
        self.refresh_rules()
        msg = (f"Imported {len(new) + (len(differ) if take else 0)} rule(s) into your Mod Book"
               + (f" and {t_new} tier(s)" if t_new else "") + ".")
        if same:
            msg += f" {len(same)} you already had."
        if differ and not take:
            msg += f" {len(differ)} kept as yours."
        if unknown:
            msg += f" {len(unknown)} unknown mod(s) skipped."
        if bad:
            self.app_toast("Some files were refused:\n" + "\n".join(bad), "Import rules", kind="warning")
        self._say(msg, 30)

    def clear_imported_rules(self):
        cat = self.rules_cat()
        mine = [k for k in COMMUNITY if mod_cat(k) == cat]
        if not mine:
            self.app_toast(f"Nothing imported for {cat} mods.", "Remove imported")
            return
        if not messagebox.askyesno("Remove imported", f"Remove the {len(mine)} imported {cat} mods? Your own rules are not touched."):
            return
        was = set(COMMUNITY_ACTIVE)
        for k in mine:
            del COMMUNITY[k]
        save_json("community_rules.json", COMMUNITY)
        rebuild_community(MARKET)
        self._after_rules_change(was)
        self._say("Imported rules removed.")

    def _after_rules_change(self, keys):
        affected = [rid for rid, rec in self.records.items()
                    if rec.get("mark", "new") == "new" and any(norm(m["text"]) in keys for m in rec["item"]["mods"])]
        if affected:
            self.reprice(affected)
        self.refresh_all()
        self.refresh_rules()

    def rules_selected(self, impact):
        ns = self.rt[self.rules_cat()]
        keys = []
        for i in ns.tv.selection():                       # (a waystone / relic row can hold several lines)
            k = ns.keys.get(i)
            keys += k if isinstance(k, list) else [k] if k else []
        self.set_rules(keys, impact)

    def tiers_selected(self, tier):
        """Rate the selected mods S..D, F (= ignore) or None (clear yours: back to the app's own rating), then
        re-price the not-yet-listed items that have them. 2.114.0: the Mod book's only rating (as on Gear rules)."""
        from . import ratemods as RM
        ns = self.rt[self.rules_cat()]
        keys = set()
        for i in ns.tv.selection():
            k = ns.keys.get(i)
            keys |= set(k if isinstance(k, list) else [k] if k else [])
        if not keys:
            return self._say("Select mods first (Ctrl+A for all, Shift / Ctrl + click), then pick a rating.", 8)
        RM.apply(sorted(keys), "ignore" if tier == TIER_F else tier)
        from .ratemods import key_for
        affected = [rid for rid, rec in self.records.items() if rec.get("mark", "new") == "new"
                    and any(norm(m["text"]) in keys or key_for(rec, m) in keys for m in rec["item"]["mods"])]
        if affected:
            self.reprice(affected)
        self.refresh_all()
        self.refresh_rules()
        self._say(f"{'Cleared' if tier is None else 'Rated ' + tier} {len(keys)} mod{'s' if len(keys) != 1 else ''}"
                  + (f"; re-pricing {len(affected)} item(s)." if affected else "."), 8)

    def cycle_rule(self, event, cat="tablet"):
        ns = self.rt[cat]
        iid = ns.tv.identify_row(event.y)
        if iid in ns.keys:
            k = ns.keys[iid]
            keys = k if isinstance(k, list) else [k]
            from . import ratemods as RM                  # 2.114.0: double-click steps the rating S, A ... F, S
            now = tier_key(keys[0]) or TIER_F
            nxt = SHOWN_TIERS[(SHOWN_TIERS.index(now) + 1) % len(SHOWN_TIERS)]
            RM.apply(keys, "ignore" if nxt == TIER_F else nxt)
            self.gb_reprice(keys)
            self.refresh_all()
            self.refresh_rules()

    def set_rules(self, keys, impact):
        """Change what these mods count for, then re-price the not-yet-listed items that have them."""
        keys = set(keys)
        if not keys:
            return
        for k in keys:
            if impact == auto_impact(k):
                RULES.pop(k, None)
            else:
                RULES[k] = impact
        save_json("mod_rules.json", RULES)
        from .ratemods import key_for
        affected = [rid for rid, rec in self.records.items()
                    if rec.get("mark", "new") == "new" and any(norm(m["text"]) in keys or key_for(rec, m) in keys
                                                               for m in rec["item"]["mods"])]
        self.reprice(affected)
        self.refresh_all()
        self.refresh_rules()
        if affected:
            self.status_text, self.status_until = f"Re-pricing {len(affected)} item{'s' if len(affected) != 1 else ''} with the new rule", time.time() + 8

    # ---------------- derived data
    def good_mods(self, rec):
        """Mods the data says are valuable: learned as High, or listings carrying them ask at least your 'valuable mod' amount."""
        out = []
        for m in rec["item"]["mods"]:
            if mod_impact(rec, m) == "ignore" or not m.get("sid"):
                continue
            li = learned_info(norm(m["text"]))
            med = MARKET.mod_median(rec["item"]["base"], m["sid"])
            if (li and li["tier"] == "high") or (med is not None and med >= SETTINGS["good_div"]):
                out.append((m, med))
        return out

    def key_mods(self, rec):
        """Mods to highlight: marked High (by you, by default, or learned from the data). Never ignored ones."""
        return [m for m in rec["item"]["mods"] if mod_impact(rec, m) == "high"]

    def update_row(self, rid):
        rec = self.records[rid]
        if not self.tree.exists(str(rid)):           # hidden by the Show filter
            return
        it = rec["item"]
        keys = len(self.key_mods(rec)) if rec["resolved"] else 0
        st = rec["state"]
        stamp = ""
        if st == "done":
            if rec.get("skip"):
                est = "low value"
            elif rec.get("nomatch"):
                est = "NO MATCH"
            elif rec.get("manual"):
                est = "CHECK BY HAND"
            elif self.price_manually(rec):
                est = "Price manually"                        # 2.16.0: a low-confidence number isn't shown as a price
            else:
                est = fmt_div(rec["est"]) if rec["est"] is not None else (fmt_price(rec["prices"][0]) if rec["prices"] else "none listed")
                if rec.get("partial") and rec["prices"]:
                    est = "≥ " + est
                elif rec.get("thin") and rec["prices"]:
                    est = "~ " + est
            listings = str(rec["total"])
            match = rec["label"]
            stamp = fmt_stamp(rec.get("priced_at"))
        elif st == "error":
            est, listings, match = "—", "", rec["label"]
        elif rec.get("held"):                                 # 2.73.2: paused by hand
            est, listings, match = "⏸", "", "paused - right-click › Resume pricing"
        else:
            est, listings, match = "…", "", "waiting" if st == "queued" else "searching…"
        mark = rec.get("mark", "new")
        tags = []
        if mark == "listed":
            tags.append("listed")
        elif mark == "removed":
            tags.append("removed")
        elif mark == "sold":
            tags.append("sold")
        elif st in ("queued", "pricing"):
            tags.append("pending")
        elif st == "error":
            tags.append("error")
        elif rec.get("nomatch") or rec.get("manual"):
            tags.append("nomatch")
        elif keys:
            tags.append("good")
        tags.append("even" if rid % 2 == 0 else "odd")
        conf = rec.get("conf", "") if st == "done" else ""
        conf = "" if conf == "-" else conf
        # (2.72.0: gear shows its own confidence - it used to say "Guess" for every non-unique piece)
        stars = "★" * keys if keys else ""                     # 2.24.0: its own column (2.19.0 put it before the name)
        ilvl = it.get("ilvl") or ""                            # 2.73.2
        status = self.MARK_TEXT[mark] or self.price_status(rec)     # P1 (2.103.0): the Status column says where it is
        self.tree.item(str(rid), values=(self.stash_spot(rec), it["name"], it["base"], status, est, conf, listings,
                                         stamp, match, stars, ilvl), tags=tags)

    def price_status(self, rec):
        """P1 (2.103.0): an item not marked listed / sold / removed - where its pricing is, in words."""
        st = rec["state"]
        if st == "done":
            if rec.get("nomatch") or rec.get("manual") or self.price_manually(rec):
                return "! Review"
            return "– Skipped" if rec.get("skip") else "✓ Priced"
        if st == "error":
            return "✖ Error"
        if rec.get("held"):
            return "⏸ Paused"
        return "⧗ Pricing" if st == "pricing" else "⧗ Waiting"

    def on_price_unit(self):
        from .pricefmt import PRICE_UNITS
        SETTINGS["price_unit"] = next((k for k, t in PRICE_UNITS if t == self.unit_var.get()), "auto")
        save_json("settings.json", SETTINGS)
        if getattr(self, "tree", None) is not None:
            self.refresh_all()
            self.update_total()
        for fn in ("refresh_insights", "wealth_fill_items", "tracker_draw"):   # other windows that show prices
            f = getattr(self, fn, None)
            if f:
                try:
                    f()
                except Exception:
                    buglog.caught()
        u = SETTINGS["price_unit"]
        if u not in ("auto", "divine") and not RATES.value(u):
            self._say("No exchange rate for that currency yet (Exchange Rates loads them): prices stay in divines "
                      "until it has one.", 8)

    def price_manually(self, rec):
        """2.16.0: Low confidence, or a gear item's rough guess: shown as "Price manually" and left out of the total
        (the rough number and why are still in the item's panel)."""
        from .pricefmt import needs_manual_price
        return rec.get("state") == "done" and needs_manual_price(rec)

    def refresh_all(self):
        for rid in list(self.records):
            if self.tree.exists(str(rid)):
                self.update_row(rid)
        sel = self.tree.selection()
        if len(sel) == 1:
            self.show_detail(self.records.get(int(sel[0])))

    def refresh_detail_if_selected(self, rid):
        rec = self.records.get(rid)
        if rec is not None and rec.get("src") == "pc":          # 2.80.0: an item on Price Checks
            if rid == getattr(self, "pc_rid", None):
                self.pc_show(rec)
            return
        if rec is not None and rec.get("src") == "fav":         # 2.84.0: an item favorite
            return self.fav_rec_changed(rec)
        sel = self.tree.selection()
        if len(sel) == 1 and sel[0] == str(rid):
            self.show_detail(self.records[rid])

    def update_total_soon(self, ms=250):
        """2.25.1: the total and the category counts go through every item (2,000+ in a long league): when prices
        arrive one after another, add them up once they pause instead of after each one."""
        if getattr(self, "_total_job", None) is None:
            self._total_job = self.root.after(ms, self._update_total_job)

    def _update_total_job(self):
        self._total_job = None
        self.update_total()

    def update_total(self):
        self.cat_refresh()                                                    # category counts follow every change
        shown = [r for r in self.records.values() if self.visible(r)]       # totals follow the Show filter
        done = [r for r in shown if r["state"] == "done"]
        tot = sum(r["est"] for r in done if r["est"] is not None and not self.price_manually(r))
        review = sum(1 for r in done if (r.get("manual") or r.get("nomatch") or r.get("conf") == "Low" or r["est"] is None)
                     and not r.get("skip"))
        if shown:
            txt = fmt_div(tot) if tot else "0 div"               # P1 (2.103.0): not "0.000 div"
            c = RATES.value("chaos")
            if c and tot >= 1:
                txt += f"  (~{tot / c:,.0f}c)"
            self.tot_val.config(text=txt)
            self.tot_lbl.config(text="TOTAL VALUATION  ≈")
            self.chip_priced.config(text=f"✓ {len(done)} / {len(shown)} Priced")
            self.chip_review.config(text=f"⚠ {review} Require Review")
            for w in (self.chip_priced, self.chip_review):
                if not w.winfo_ismapped():
                    w.pack(side="right", padx=(0, 8) if w is self.chip_priced else 0)
        else:
            self.tot_val.config(text="")
            self.tot_lbl.config(text="Nothing in the list yet")
            self.chip_priced.config(text="")
            self.chip_priced.pack_forget()
            self.chip_review.pack_forget()

    def batch_done(self):
        recs = [self.records[r] for r in self.batch_ids if r in self.records]
        self.batch_ids = set()
        if not recs:
            return
        ok = [r for r in recs if r["state"] == "done"]
        failed = len(recs) - len(ok)
        total = sum(r["est"] for r in ok if r["est"] is not None)
        worth = [r for r in ok if r["est"] is not None and r["est"] >= SETTINGS["good_div"]]
        best = max(worth, key=lambda r: r["est"], default=None)
        self.status_text = f"✔ Finished pricing {len(recs)} item{'s' if len(recs) != 1 else ''}"
        self.status_until = time.time() + 60
        lines = [f"{len(ok)} priced" + (f", {failed} couldn't be priced" if failed else ""),
                 f"Total ≈ {fmt_div(total)}",
                 f"{len(worth)} worth {SETTINGS['good_div']:g}+ div" + (f"  (best: {best['item']['name']}, {fmt_div(best['est'])})" if best else "")]
        self.flash_window()
        if SETTINGS["popups"] and any(self.pops_for(r) for r in recs):
            self.toast.show("✔ All items checked", lines, C["green"], 15)
        if SETTINGS["sound"]:
            try:
                if sys.platform == "win32":
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                else:
                    self.root.bell()
            except Exception:
                buglog.caught()

    def pace_secs_per_item(self):
        """2.26.2: a first guess at how long one item takes, before any has finished: the pace's search allowance
        (searches per 5 minutes) and about two searches an item."""
        from .net import PACE
        cap = PACE.get("cap300") or 8
        return 300 / cap * 2

    def update_status(self):
        if self.status_text and time.time() > self.status_until:
            self.status_text = ""
        n_items = sum(1 for r in self.records.values() if r["state"] in ("queued", "pricing"))
        parts = []
        if self.status_text:
            parts.append(self.status_text)
        if self.last_heard and not self.status_text and not n_items:
            parts.append("listening - last copy heard " + time.strftime("%H:%M:%S", time.localtime(self.last_heard)))
        if n_items:
            self.was_busy = True
        elif self.was_busy:
            self.was_busy = False
            self.batch_done()
        if not n_items:
            self.done_times.clear()
        chip = getattr(self, "chip_eta", None)
        if n_items:
            eta = ""
            per = None
            if len(self.done_times) >= 3:
                per = (self.done_times[-1] - self.done_times[0]) / (len(self.done_times) - 1)
                old = SETTINGS.get("price_secs_avg")                # 2.26.2: remembered for next time
                SETTINGS["price_secs_avg"] = round(per if not old else 0.8 * old + 0.2 * per, 1)
            else:                                                   # 2.26.2: no "pricing 215" without a time - an
                per = SETTINGS.get("price_secs_avg") or self.pace_secs_per_item()   # estimate from the start
            if per:
                eta = f" - about {mmss(n_items * per + LIMITER.state()['blocked'])} left"
            parts.append(f"pricing {n_items} item{'s' if n_items != 1 else ''}{eta}")
            if chip is not None:                             # 2.26.0: up top, next to Priced / Require Review
                chip.config(text=f"⏳ Pricing {n_items}" + (f" · {eta.replace(' - about ', '~')}" if eta else ""))
                if not chip.winfo_manager():
                    if self.chip_priced.winfo_manager():
                        chip.pack(side="right", padx=(0, 8), after=self.chip_priced)
                    else:
                        chip.pack(side="right", padx=(0, 8))
        elif chip is not None and chip.winfo_manager():
            chip.pack_forget()
        book = f"Mod Book: {MARKET.mods_known()} mods learned"
        parts.append(book)
        from . import buglog
        if buglog.debug_on():                           # 2.116.0: Developer options › Debug mode
            st = buglog.STATS
            book = f"{book}   ·   debug: {st['requests']} requests ({st['slow_requests']} slow), see the app's log"
            parts.append(f"debug: {st['requests']} requests ({st['slow_requests']} slow)")
        self.status.config(text="   ·   ".join(parts) if (n_items or self.status_text) else f"Ready   ·   {book}")

    # ---------------- sorting / selection / actions
    def sort_by(self, col):
        self.sort_rev = (not self.sort_rev) if self.sort_col == col else (col in ("est", "conf", "listings", "priced",
                                                                                   "vmods", "ilvl"))
        self.sort_col = col
        self._apply_sort()
        self.sort_headings()
        self.list_note()

    def sort_headings(self):
        """▲ / ▼ on the column the list is sorted by (2.0 beta 22), so you can see it and click # to go back to the
        order you added the items in."""
        for cid, title, _w, _a in self.COLS:
            arrow = (" ▼" if self.sort_rev else " ▲") if cid == self.sort_col else ""
            self.tree.heading(cid, text=title + arrow)

    # ---------------- 2.87.0 (feedback: the trade site lists a public tab's items in no order - "I work ... from top to
    # bottom and left to right across my stash"): each item read from a tab keeps its place (the listing's stash x / y),
    # and the list follows the tab - down each column, columns left to right (or across each row; Settings key
    # "stash_order": "columns" / "rows"). The # column shows the place (C3 R5 = column 3, row 5).
    def stash_key(self, rec):
        pos = rec.get("pos")
        if not pos:
            return (1, 0, 0, rec["id"])
        x, y = pos
        return (0, x, y, rec["id"]) if SETTINGS.get("stash_order", "columns") == "columns" else (0, y, x, rec["id"])

    def stash_spot(self, rec):
        pos = rec.get("pos")
        return f"C{pos[0] + 1} R{pos[1] + 1}" if pos else rec["id"]

    def stash_order_soon(self):
        if getattr(self, "_so_job", None) is None:
            def go():
                self._so_job = None
                if self.sort_col in (None, "added"):
                    self.sort_col = self.sort_col or "added"
                    self._apply_sort()
            self._so_job = self.root.after(300, go)

    def stash_order_set(self, how):
        SETTINGS["stash_order"] = how
        save_json("settings.json", SETTINGS)
        self.sort_added()

    def sort_added(self):
        self.sort_col, self.sort_rev = "added", False
        self._apply_sort()
        self.sort_headings()
        self.list_note()

    def _apply_sort(self):
        col = self.sort_col
        if not col:
            return

        def key(rid):
            rec = self.records[int(rid)]
            if col == "added":                                 # 2.0 beta 22: the order you copied them in
                return self.stash_key(rec)                      # (2.87.0: a stash tab's items: their place in it)
            if col == "est":
                return rec["est"] if rec["est"] is not None else -1
            if col == "conf":
                return {"High": 3, "Medium": 2, "Low": 1}.get(rec.get("conf"), 0)
            if col == "listings":
                return rec["total"]
            if col == "priced":
                return rec.get("priced_at") or 0
            if col == "name":
                return rec["item"]["name"].lower()
            if col == "type":
                return rec["item"]["base"].lower()
            if col == "mark":
                return rec.get("mark", "new")
            if col == "vmods":
                return len(self.key_mods(rec)) if rec.get("resolved") else 0
            if col == "ilvl":
                return rec["item"].get("ilvl") or 0
            return rec["label"].lower()
        ids = sorted(self.tree.get_children(), key=key, reverse=self.sort_rev)
        for i, iid in enumerate(ids):
            self.tree.move(iid, "", i)

    def _on_select_soon(self, _e=None):
        """2.3.0: the selection changes once per row when many rows are deleted (or selected) at once, and each change
        rebuilt the item panel - deleting 150 items took seconds. Now the panel is rebuilt once, when it settles."""
        if getattr(self, "_sel_job", None) is None:
            self._sel_job = self.root.after_idle(self._on_select_now)

    def _on_select_now(self):
        self._sel_job = None
        try:
            self.on_select()
        except tk.TclError:
            pass

    def on_select(self, _e=None):
        sel = self.tree.selection()
        rec = self.records.get(int(sel[0])) if len(sel) == 1 else None
        self.show_detail(rec)
        if hasattr(self, "item_trade_btn"):                # 2.63.0: the item panel's own buttons
            self.item_trade_btn.config(state="normal" if rec and rec.get("qid") else "disabled")
            self.item_mark_btn.config(state="normal" if sel else "disabled")
        self.update_mark_buttons()
        if rec and SETTINGS.get("auto_copy"):
            self.copy_name(rec)

    def checks_menu_actions(self, sel):
        """2.36.0: the Price checks rows' own right-click actions (Delete / Copy come from the standard list menu)."""
        rids = [int(i) for i in sel if str(i).isdigit() and int(i) in self.records]
        one = self.records[rids[0]] if len(rids) == 1 else None
        n = f" ({len(rids)})" if len(rids) > 1 else ""
        waiting = [r for r in rids if self.records[r].get("state") != "done"]
        held = [r for r in waiting if self.records[r].get("held")]
        return [(f"⏸ Pause pricing{n}" if not held or len(held) < len(waiting) else f"▶ Resume pricing{n}",
                 (lambda: self.pricing_hold(waiting, not (held and len(held) == len(waiting)))), bool(waiting)),
                (f"⏫ Price next{n}", lambda: self.pricing_move(waiting, 0), bool(waiting)),
                (f"⏬ Price last{n}", lambda: self.pricing_move(waiting, 90), bool(waiting)),
                None,
                (f"Re-price{n}", lambda: self.reprice(rids), bool(rids)),
                ("Copy name", lambda: self.copy_name(one, True), one is not None, "C"),
                ("Trade Site", self.open_trade, bool(one and one.get("qid")), "O")]   # (2.105.0: no Mark ...)

    # ---------------- 2.73.2: pause / reorder the items waiting to be priced
    def pricing_hold(self, rids, on=True):
        """Pause (on) or resume these items' pricing. A paused item keeps its place; Pause searches (F2) still
        pauses everything."""
        for rid in rids:
            rec = self.records.get(rid)
            if rec is None or rec.get("state") == "done":
                continue
            if on:
                rec["held"] = True
                self.engine.hold(rid)
            else:
                rec.pop("held", None)
                self.engine.unhold(rid)
            if self.tree.exists(str(rid)):
                self.update_row(rid)
        self._say(("Paused" if on else "Resumed") + f" pricing for {len(rids)} item{'s' if len(rids) != 1 else ''}.", 5)
        return len(rids)

    def pricing_move(self, rids, prio):
        """Price these next (prio 0) or last (90)."""
        n = 0
        for rid in (reversed(rids) if prio == 0 else rids):
            if rid in self.records and self.records[rid].get("state") != "done" and self.engine.bump(rid, prio):
                n += 1
        self._say(f"{n} item{'s' if n != 1 else ''} will be priced {'next' if prio == 0 else 'last'}.", 5)
        return n

    def open_trade(self):
        sel = self.tree.selection()
        if len(sel) != 1:
            return
        self.open_rec_trade(self.records[int(sel[0])])

    def open_rec_trade(self, rec):
        """2.105.1 (feedback: it opened without the changes on the card): filters changed since the last search -
        search them first, then the trade site opens on that search."""
        if not rec:
            return
        if rec.get("changed") or (not rec.get("qid") and rec.get("state") in ("queued", "pricing")):
            rec["open_after"] = True
            if rec.get("changed"):
                self.reprice([rec["id"]])
            self.status_text, self.status_until = "Searching your changes first - the trade site opens when it's done.", \
                time.time() + 8
            return
        if rec.get("qid"):
            self.open_qid(rec["qid"])

    def open_qid(self, qid):
        if qid:
            webbrowser.open(f"https://www.pathofexile.com/trade2/search/poe2/{SETTINGS['league']}/{qid}")

    def remove_selected(self):
        """2.0 beta 19: delete the selected items from the list (not the whole list). Ctrl+Z / Undo brings them back."""
        sel = [int(i) for i in self.tree.selection()]
        gone = [(rid, self.records[rid]) for rid in sel if rid in self.records]
        if not gone:
            return self._say("Select the items to delete first (click, Shift+click or Ctrl+click for several).", 8)
        kids = list(self.tree.get_children())
        first = min((kids.index(str(r)) for r in sel if str(r) in kids), default=0)
        for rid, rec in gone:
            self.records.pop(rid, None)
            self.batch_ids.discard(rid)
            if rec.get("raw"):
                self.seen_texts.pop(hash(rec["raw"].strip()), None)     # copying it again adds it again
            if self.tree.exists(str(rid)):
                self.tree.delete(str(rid))
        self.undo, self.undo_deleted = [], gone
        self.undo_btn.config(state="normal")
        self.dirty = True
        self.update_total()
        left = list(self.tree.get_children())
        if left:
            nxt = left[min(first, len(left) - 1)]
            self.tree.selection_set(nxt)
            self.tree.see(nxt)
        else:
            self.show_detail(None)
            if not self.records:
                self.empty_lbl.place(relx=0.5, rely=0.45, anchor="center")
        n = len(gone)
        self._say(f"Deleted {n} item{'s' if n != 1 else ''} from the list. Ctrl+Z or Undo brings "
                  f"{'them' if n != 1 else 'it'} back.", 12)

    def clear(self):
        """Clear the list you're looking at (2.42.0: Manual Add, or one stash tab's list - the others stay)."""
        mine = [rid for rid, r in self.records.items() if self.in_list(r)]
        src = self.list_src()
        what = "this tab's list" if src != "manual" else "the Manual Add list"
        if mine and not messagebox.askyesno("Clear list", f"Remove all items from {what}?\n(The mod book is kept.)"):
            return
        for rid in mine:
            del self.records[rid]
        if src != "manual":                          # (the rest below is about your own copies)
            self.dirty = True
            self.tree.delete(*self.tree.get_children())
            self.update_total()
            self.show_detail(None)
            if hasattr(self, "pctab_bar"):
                self.pctab_bar()
            return
        if hasattr(self, "cat_var"):
            self.cat_var.set(self.ALL_CATS)
        self.dup_pending.clear()
        if self.dup_win:
            try:
                self.dup_win.destroy()
            except Exception:
                buglog.caught()
            self.dup_win = None
        self.seen_texts.clear()                      # forget which items we've seen, so re-copying one adds it again
        self.batch_ids.clear()
        self.was_busy = False
        self.done_times.clear()
        self.last_seq = clip_seq()                   # whatever is on the clipboard now is not a new copy
        self.restart_watcher()
        self.dirty = True
        self.tree.delete(*self.tree.get_children())
        self.update_total()
        self.show_detail(None)
        self.empty_lbl.place(relx=0.5, rely=0.45, anchor="center")

    def export(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="stash_prices.csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name", "base", "rarity", "est_div", "listings", "match", "cheapest_listings", "valuable_mods", "mods", "tracked", "listed_price", "priced_at"])
            for iid in self.tree.get_children():
                r = self.records[int(iid)]
                w.writerow([r["item"]["name"], r["item"]["base"], r["item"]["rarity"],
                            "" if r["est"] is None else round(r["est"], 3), r["total"], r["label"],
                            " | ".join(fmt_price(p) for p in r["prices"][:5]),
                            " | ".join(pretty(m["text"]) for m, _ in self.good_mods(r)),
                            " / ".join(m["text"] for m in r["item"]["mods"]),
                            r.get("mark", "new"), r.get("list_price", ""),
                            time.strftime("%Y-%m-%d %H:%M", time.localtime(r["priced_at"])) if r.get("priced_at") else ""])

    def value_log_save_soon(self):
        if getattr(self, "_vl_job", None) is None:
            def go():
                self._vl_job = None
                threading.Thread(target=VALUE_LOG.save, daemon=True).start()   # 2.25.1: off the window thread
            self._vl_job = self.root.after(1500, go)

    def append_history(self, rec):
        new = not os.path.exists(P("history.csv"))
        try:
            with open(P("history.csv"), "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["time", "name", "base", "est_div", "listings", "match", "mods"])
                w.writerow([datetime.now().isoformat(timespec="seconds"), rec["item"]["name"], rec["item"]["base"],
                            "" if rec["est"] is None else round(rec["est"], 3), rec["total"], rec["label"],
                            " / ".join(m["text"] for m in rec["item"]["mods"])])
        except Exception:
            buglog.caught()

    # ---------------- detail panel
    def _canvas_resized(self, e):
        self.dcanvas.itemconfig(self._dwin, width=e.width)
        if abs(e.width - self._dwidth) > 20:             # panel was dragged wider/narrower: re-wrap the text
            self._dwidth = e.width
            if self._dafter:
                self.root.after_cancel(self._dafter)
            self._dafter = self.root.after(250, self._redraw_detail)

    def _redraw_detail(self):
        self._dafter = None
        if self.shown_rec is not None and self.shown_rec["id"] in self.records:
            self.show_detail(self.shown_rec)

    def show_detail(self, rec):
        """2.79.0 (feedback: "a clean view"): the item card holds every filter - properties,
        requirements, miscellaneous, each mod, pseudo totals, trade filters - then Search again / Open on trade site,
        and one ▸ Advanced section at the bottom (listing status, if you list it, how it's priced, rolls, raw text)."""
        if rec is not None and rec.get("src") == "pc":          # 2.80.0: the card on Price Checks
            return self.pc_show(rec)
        if rec is not None and rec.get("src") == "fav":         # 2.84.0: the card on Favorites
            return self.fav_rec_changed(rec)
        for w in self.detail.winfo_children():
            w.destroy()
        self.shown_rec = rec
        wrap = max(200, self.dcanvas.winfo_width() - 44)
        self.dcanvas.yview_moveto(0)
        d = self.detail
        self.price_var = None
        self.detail_vars = []
        P2, P1 = C["panel2"], C["panel"]
        if rec is None:
            n = len(self.tree.selection()) if hasattr(self, "tree") else 0
            tk.Label(d, text=f"{n} items selected" if n > 1 else "Select an item\nto see its mods",
                     bg=P2, fg=C["muted"], font=("Segoe UI", 10), justify="left", anchor="nw").pack(fill="x")
            return
        it = rec["item"]
        self._detail_card(d, rec, it, wrap)
        self.bulkv = types.SimpleNamespace(card_rows=self.card_rows, card_paint=self.card_paint,  # 2.103.4: ticks
                                           card_vals=self.card_vals, rid=rec["id"], search_btn=None)  # in place
        btns = tk.Frame(d, bg=P2)
        btns.pack(fill="x", pady=(8, 0))
        self.detail_search_btn = ttk.Button(btns, text=self._bulk_search_text(rec), style="Primary.TButton",
                                            command=lambda: self.reprice([rec["id"]]))
        self.detail_search_btn.pack(side="left", fill="x", expand=True)
        self.bulkv.search_btn = self.detail_search_btn
        self.detail_open_btn = ttk.Button(btns, text="Trade Site  [O]", command=self.open_trade)
        self.detail_open_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))
        if not rec.get("qid"):
            self.detail_open_btn.state(["disabled"])
        note = self._detail_note(rec)
        if note:
            tk.Label(d, text=note[0], bg=P2, fg=note[1], font=("Segoe UI", 9), anchor="w", justify="left",
                     wraplength=wrap).pack(fill="x", pady=(8, 0))
        adv = bool(SETTINGS.get("detail_adv"))
        head = tk.Label(d, text=("▾ " if adv else "▸ ") + "ADVANCED  ·  listing status, how it's priced, raw text",
                        bg=P1, fg=C["accent"], font=("Segoe UI", 9, "bold"), anchor="w", cursor="hand2", padx=8,
                        pady=8, highlightthickness=1, highlightbackground=C["accent"] if adv else C["line"])
        head.pack(fill="x", pady=(8, 0))
        head.bind("<Button-1>", lambda e: (SETTINGS.__setitem__("detail_adv", not adv), self.show_detail(rec)))
        self.detail_adv_head = head
        if adv:
            self._detail_advanced(d, rec, it, wrap)

    @staticmethod
    def _bulk_search_text(rec):
        return "Search again  •  filters changed" if rec.get("changed") else "Search again  [Enter]"

    def _detail_note(self, rec):
        """One short line under the buttons when the price needs a word: no match, by hand, an error, a used tablet."""
        st = rec["state"]
        if st == "error":
            return f"Couldn't price this: {rec.get('label', '')}", C["red"]
        if st != "done":
            return None
        if rec.get("nomatch"):
            return ("No matching listing - untick a mod or widen a filter, then Search again.", C["text"])
        if rec.get("manual"):
            return ("Check by hand: " + (rec.get("manual_why") or "the listings are priced too differently") + ".",
                    C["good"])
        if rec.get("uses_note"):
            return "✂ " + rec["uses_note"], C["good"]
        return None

    # ---------------- the card
    def _detail_card(self, d, rec, it, wrap):
        """The item as a card: name band, price, then every filter - each with its check box and
        Min / Max where it has a number. A click / Enter prices it again."""
        from . import themes as _th
        from .searchopts_page import item_facts
        P2 = C["panel2"]
        rar = (it.get("rarity") or "").lower()
        t = _th.ST.theme
        col = {"rare": C["rare"], "magic": C["magic"], "unique": t.c("unique", "#af6025")}.get(rar, C["text"])
        w = max(240, wrap + 12)

        def card_text(m):
            tx = m.get("shown") or m.get("text") or ""
            return re.sub(r"\s+", " ", re.sub(r"\[([^\]|]*\|)?([^\]]*)\]", r"\2", tx)).strip()
        own = [m for m in it.get("mods") or [] if m.get("kind") != "Total" and m.get("group") not in ("total", "pseudo")]
        totals = [m for m in it.get("mods") or [] if m.get("kind") == "Total" and m.get("group") != "pseudo"]
        pseudo = [m for m in it.get("mods") or [] if m not in own and m not in totals]
        facts = item_facts(rec)
        st, big, sub = rec["state"], "", ""
        if st == "done" and not rec.get("nomatch") and not rec.get("manual"):
            if rec.get("est") is not None:
                big = ("≥ " if rec.get("partial") else "~ " if rec.get("thin") else "") + fmt_div(rec["est"])
            elif rec.get("prices"):
                big = fmt_price(rec["prices"][0])
            cf = rec.get("conf")
            sub = "  ·  ".join(x for x in ((f"{cf} confidence" if cf and cf != "-" else ""),
                                           (f"{rec['total']} listings" if rec.get("total") is not None else "")) if x)
        elif st == "done":
            big = "No match" if rec.get("nomatch") else "Check by hand"
        elif st == "error":
            big = "Couldn't price"
        else:
            big = "Pricing…" if st == "pricing" else "Waiting in line…"
        cv = tk.Canvas(d, width=w, height=200, bg=P2, highlightthickness=0, bd=0)
        cv.pack(fill="x")
        fmod = ("Segoe UI", 10)
        self.card_rows, self.card_vals, self.card_opts, self.card_tris = {}, {}, {}, {}
        self.card_onlys = {}
        self.card_thumbs = {}
        self.card_paint = {}
        with _th.raw():
            bg = C["odd"]
            cv.create_rectangle(0, 0, w - 1, 199, fill=bg, outline=t.c(t.part("card", "border", default="border_light")),
                                tags=("cardframe",))
            name_c = _th.card_header(cv, 4, 4, w - 5, 54, col, bg)
            cv.create_text(w // 2, 20, text=it["name"], fill=name_c, font=(_th.head_font(), 12, "bold"),
                           width=w - 24, justify="center")
            if it.get("base") and it["base"] != it["name"]:
                cv.create_text(w // 2, 40, text=it["base"], fill=_th.mix(name_c, C["text"], .45), font=("Segoe UI", 10))
            y = 62
            good = st == "done" and big not in ("No match", "Check by hand")
            cv.create_text(16, y + 14, text=big, anchor="w", font=("Segoe UI", 16, "bold"),
                           fill=C["good"] if good else (C["red"] if st in ("done", "error") else C["muted"]),
                           tags=("cardprice",))
            if sub:
                cv.create_text(w - 16, y + 14, text=sub, anchor="e", font=("Segoe UI", 9), fill=C["muted"])
            y += 32
            sep = t.c(t.part("card", "sep", default="border"))
            mod_c, imp_c = MOD_COL["explicit"], MOD_COL["implicit"]
            fold = SETTINGS.setdefault("pc_fold", {})          # 2.97.2: each section folds; remembered
            if "req" not in fold and SETTINGS.get("card_req"):
                fold["req"] = False                            # (Requirements was opened before 2.97.2)
            self.card_sections = {}
            # fold all / unfold all
            keys_all = ("props", "req", "misc", "aug", "stats", "pseudo", "trade")
            all_open = any(not fold.get(k, k == "req") for k in keys_all)    # (any open: "Fold all")
            fa = cv.create_text(w - 16, y - 2, text="Fold all ▴" if all_open else "Unfold all ▾", anchor="e",
                                font=("Segoe UI", 9), fill=C["accent"], tags=("cardfoldall",))
            self._card_click(cv, "cardfoldall", lambda: self.card_fold_all(rec, all_open))

            def section(title, key, count=None, boxes=False, summary=""):
                """▾ TITLE (n) ─── MIN MAX: a click folds / unfolds it. -> open?"""
                nonlocal y
                shut = bool(fold.get(key, key == "req"))
                y += 4
                lab = ("▸ " if shut else "▾ ") + title + (f"  ({count})" if count else "")
                if shut and summary:
                    lab += "   " + summary
                tag = f"cardsec_{key}"
                tid = cv.create_text(12, y, text=lab, anchor="nw", font=("Segoe UI", 9, "bold"),
                                     fill=C["text"] if not shut else C["muted"], tags=(tag, "cardsec"))
                bb = cv.bbox(tid)
                x_end = w - 12
                if boxes and not shut:
                    x_end = w - 12 - 18 - CARD_BOX * 2 - 8
                    cv.create_text(w - 12 - 18 - CARD_BOX - CARD_BOX // 2 - 4, y, text="MIN", anchor="n",
                                   font=("Segoe UI", 9, "bold"), fill=C["muted"])
                    cv.create_text(w - 12 - 18 - CARD_BOX // 2, y, text="MAX", anchor="n",
                                   font=("Segoe UI", 9, "bold"), fill=C["muted"])
                if bb and bb[2] + 8 < x_end:
                    cv.create_line(bb[2] + 8, y + 8, x_end, y + 8, fill=sep)
                self._card_click(cv, tag, lambda k=key, s=shut: self.card_fold(rec, k, not s))
                self.card_sections[key] = not shut
                y += 20
                return not shut
            # ---- properties
            if section("PROPERTIES", "props", boxes=True):
                s = it.get("search") or {}
                if it.get("gear") and not it.get("waystone") and s.get("rarity") != "unique":
                    y = self._card_base_row(cv, rec, it, y, w)
                if it.get("corrupted"):                       # 2.120.1 (feedback): in plain sight, not folded away
                    y = self._card_corrupt_row(cv, rec, it, y, w)
                if it.get("quality"):
                    y = self._card_opt_row(cv, rec, "quality", f"Quality: +{it['quality']}%", it["quality"], y, w)
                for m in totals:
                    y = self._card_mod_row(cv, rec, m, y, w, fmod, C["good"], card_text(m))
                if it.get("waystone") and it.get("tier"):     # 2.103.2 (feedback): the tier can be widened
                    y = self._card_opt_row(cv, rec, "tier", "Waystone tier:", it["tier"], y, w)
                if it.get("ilvl"):
                    y = self._card_opt_row(cv, rec, "ilvl", f"Item level: {it['ilvl']}", it["ilvl"], y, w)
                if it.get("sockets"):
                    y = self._card_opt_row(cv, rec, "sockets", f"Sockets: {it['sockets']}", it["sockets"], y, w)
            # ---- requirements (folded at first)
            req = facts.get("req") or {}
            if req and section("REQUIREMENTS", "req", summary="  ·  ".join(f"{REQ_NAMES[k]} {v}" for k, v in req.items())):
                for k, v in req.items():
                    y = self._card_opt_row(cv, rec, "req_" + k, f"{REQ_NAMES[k]}: {v}", v, y, w)
            # ---- miscellaneous: Any / Yes / No
            from .searchopts_page import default_opts as _dopts
            _cur = {**_dopts(it), **(rec.get("opts") or {})}
            nset = sum(1 for key, _l in MISC_ROWS if _cur.get(key) not in (None, "any", "", "Any"))
            if section("MISCELLANEOUS", "misc", count=nset):
                col_w = (w - 24) // 2
                for i, (key, label) in enumerate(MISC_ROWS):
                    x0 = 16 + (i % 2) * col_w
                    self._card_tri(cv, rec, key, label, x0, y + (i // 2) * 20, facts)
                y += 20 * ((len(MISC_ROWS) + 1) // 2) + 2

            def ticked(ms):
                return sum(1 for m in ms if mod_impact(rec, m) != "ignore")
            # ---- each mod: its color says where it comes from (2.97.2)
            aug = [m for m in own if m.get("kind") == "Rune"]
            if aug and section("AUGMENTS", "aug", count=ticked(aug),
                               boxes=any(self._card_has_vals(rec, m) for m in aug)):   # 2.97.1: runes on their own
                for m in aug:
                    y = self._card_mod_row(cv, rec, m, y, w, fmod, MOD_COL["rune"], card_text(m))
            own = [m for m in own if m not in aug]
            if own and section("STAT FILTERS", "stats", count=ticked(own),
                               boxes=any(self._card_has_vals(rec, m) for m in own)):
                first = [m for m in own if m.get("kind") in ("Implicit", "Enchant")]
                for m in first + [m for m in own if m not in first]:
                    y = self._card_mod_row(cv, rec, m, y, w, fmod, imp_c if m in first else mod_c, card_text(m))
            if pseudo and section("PSEUDO FILTERS", "pseudo", count=ticked(pseudo), boxes=True):
                for m in pseudo:
                    y = self._card_mod_row(cv, rec, m, y, w, fmod, MOD_COL["pseudo"], card_text(m))
            # ---- trade filters
            if section("TRADE FILTERS", "trade"):
                from .searchopts_page import default_opts
                cur = {**default_opts(it), **(rec.get("opts") or {})}
                for key, label, choices in (("status", "Seller", STATUS_CHOICES), ("currency", "Priced in", CURRENCY_CHOICES)):
                    cv.create_text(16, y + 13, text=label, anchor="w", font=("Segoe UI", 9), fill=C["muted"])
                    names = [n for n, _v in choices]
                    var = tk.StringVar(value=next((n for n, v in choices if v == cur.get(key)), names[0]))
                    cb = ttk.Combobox(cv, textvariable=var, values=names, state="readonly")
                    cb.bind("<<ComboboxSelected>>", lambda e, k=key, v=var, c=choices: (
                        self.search_opt_set(rec, k, dict(c)[v.get()], redraw=False), self._card_mark(rec)))
                    cv.create_window(110, y, window=cb, anchor="nw", width=w - 126, height=26)
                    self.card_opts[key] = var
                    y += 30
            if it.get("corrupted"):
                cv.create_text(w // 2, y + 8, text="Corrupted", font=("Segoe UI", 10, "bold"), fill=C["red"])
                y += 20
            h2 = y + 8
            cv.configure(height=h2)
            cv.coords("cardframe", 0, 0, w - 1, h2 - 1)
        self.detail_card = cv
        return cv

    def card_fold(self, rec, key, shut):
        """2.97.2: fold / unfold one section of the card (remembered for every item)."""
        SETTINGS.setdefault("pc_fold", {})[key] = bool(shut)
        save_json("settings.json", SETTINGS)
        self.show_detail(rec)

    def card_fold_all(self, rec, shut):
        f = SETTINGS.setdefault("pc_fold", {})
        for k in ("props", "req", "misc", "aug", "stats", "pseudo", "trade"):
            f[k] = bool(shut)
        save_json("settings.json", SETTINGS)
        self.show_detail(rec)

    def _card_box(self, cv, x, y, on, tag, enabled=True):
        box = 14
        cv.create_rectangle(x, y, x + box, y + box, outline=C["muted"] if enabled else C["line"],
                            fill=C["accent"] if on and enabled else C["odd"], tags=("cardbox", tag, tag + "_box"))
        if on and enabled:
            cv.create_line(x + 3, y + 7, x + 6, y + 10, x + 11, y + 4, fill="#120a04", width=2,
                           tags=(tag, tag + "_chk"))

    def _card_box_paint(self, cv, x, y, on, tag):
        """2.104.1: tick / untick a box drawn by _card_box, in place."""
        try:
            cv.itemconfigure(tag + "_box", fill=C["accent"] if on else C["odd"])
            cv.delete(tag + "_chk")
            if on:
                cv.create_line(x + 3, y + 7, x + 6, y + 10, x + 11, y + 4, fill="#120a04", width=2,
                               tags=(tag, tag + "_chk"))
        except tk.TclError:
            pass

    def _card_mark(self, rec):
        """2.104.1 (feedback: every box on the card still flickered - only the mods were painted in place): a filter
        on the card changed. On Price Checks / Favorites nothing is built again - the caller paints its own row.
        -> True when quiet (paint the row), False when the card was built again (or Bulk Pricing prices it)."""
        v = self._card_view(rec)                      # (2.108.0: Bulk Pricing too)
        if v is None:
            self.card_changed(rec)
            return False
        self._card_quiet = True
        try:
            self.card_changed(rec)
        finally:
            self._card_quiet = False
        self._card_search_paint(rec, v)
        return True

    def _card_search_paint(self, rec, v):
        btn = getattr(self, "pc_search_btn", None) if rec.get("src") == "pc" else getattr(v, "search_btn", None)
        if btn is not None:
            try:
                if rec.get("src") not in ("pc", "fav"):
                    return btn.config(text=self._bulk_search_text(rec))
                btn.config(text="Search  •  filters changed" if rec.get("changed") else "Search")
            except tk.TclError:
                pass

    def _card_click(self, cv, tag, fn):
        cv.tag_bind(tag, "<Button-1>", lambda e: fn())
        cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))

    def _card_base_row(self, cv, rec, it, y, w):
        """Base type: ticked = this base only; unticked = any base of its kind."""
        from .searchopts_page import default_opts
        cur = {**default_opts(it), **(rec.get("opts") or {})}
        on = cur.get("base") == "same"
        tag = "cardbase"
        cv.create_rectangle(4, y - 2, w - 4, y + 18, outline="", fill=C["odd"], tags=(tag,))
        self._card_box(cv, 10, y + 2, on, tag)
        txt = cv.create_text(32, y, text=f"Base type: {it['base']}" if on else f"Any {it.get('class') or 'base'}",
                             anchor="nw", font=("Segoe UI", 10), fill=C["text"] if on else C["muted"], tags=(tag,))
        st = {"on": on}

        def click():
            st["on"] = not st["on"]
            self.search_opt_set(rec, "base", "same" if st["on"] else "class", redraw=False)
            self.card_opts["base"] = st["on"]
            if self._card_mark(rec):                  # 2.104.1: painted in place
                self._card_box_paint(cv, 10, y + 2, st["on"], tag)
                try:
                    cv.itemconfigure(txt, text=f"Base type: {it['base']}" if st["on"] else
                                     f"Any {it.get('class') or 'base'}", fill=C["text"] if st["on"] else C["muted"])
                except tk.TclError:
                    pass
        self._card_click(cv, tag, click)
        self.card_opts["base"] = on
        return y + 22

    def _card_corrupt_row(self, cv, rec, it, y, w):
        """2.120.1 (feedback: a toggle for it on the price check): a corrupted item - ticked = compared with corrupted
        listings only (buyers pay less for them); unticked = corrupted or not. The same setting as Miscellaneous ›
        Corrupted."""
        from .searchopts_page import default_opts
        cur = {**default_opts(it), **(rec.get("opts") or {})}
        on = cur.get("corrupted") == "yes"
        tag = "cardcorrupt"
        cv.create_rectangle(4, y - 2, w - 4, y + 18, outline="", fill=C["odd"], tags=(tag,))
        self._card_box(cv, 10, y + 2, on, tag)
        cv.create_text(32, y, text="Corrupted listings only" if on else "Corrupted or not", anchor="nw",
                       font=("Segoe UI", 10), fill=C["text"] if on else C["muted"], tags=(tag,))

        def click():
            self.search_opt_set(rec, "corrupted", "any" if on else "yes", redraw=False)
            self.card_changed(rec)                    # (built again: Miscellaneous shows the same setting)
        self._card_click(cv, tag, click)
        return y + 22

    def _card_opt_row(self, cv, rec, key, label, have, y, w):
        """[✓] Quality: +22%   [min] [max] - one of the item's own filters (rec["opts"][key]); ticked = searched."""
        from .searchopts_page import default_opts
        cur = {**default_opts(rec["item"]), **(rec.get("opts") or {})}.get(key)
        if isinstance(cur, dict):
            lo, hi = cur.get("min"), cur.get("max")
        else:
            lo, hi = cur, None
        on = cur not in (None, "", 0, {})
        tag = f"cardopt_{key}"
        cv.create_rectangle(4, y - 2, w - 4 - (2 * CARD_BOX + 34), y + 18, outline="", fill=C["odd"], tags=(tag,))
        self._card_box(cv, 10, y + 2, on, tag)
        txt = cv.create_text(32, y, text=label, anchor="nw", font=("Segoe UI", 10),
                             fill=C["text"] if on else C["muted"], tags=(tag,))
        st = {"on": on}
        boxes = {}
        for i, (k, v) in enumerate((("min", lo if on else have), ("max", hi if on else None))):
            e = self._card_entry(cv, "" if v is None else f"{v:g}" if isinstance(v, float) else str(v))
            cv.create_window(w - 12 - 18 - CARD_BOX * (2 - i) - (4 if i == 0 else 0), y - 1, window=e, anchor="nw",
                             width=CARD_BOX, height=20)
            boxes[k] = e

        def take(turn_on=True):
            vals = {}
            for k, e in boxes.items():
                tx = e.get().strip().replace(",", ".")
                try:
                    vals[k] = int(float(tx)) if tx else None
                except ValueError:
                    e.config(highlightbackground=C["red"])
                    return None
            if not turn_on or (vals["min"] is None and vals["max"] is None):
                vals = None
            self._card_opt_store(rec, key, vals)
            st["on"] = vals is not None
            self.card_opts[key] = (boxes, st["on"])
            if key == "ilvl":
                self.card_ilvl = (boxes["min"], st["on"])
            if self._card_mark(rec):                  # 2.104.1: painted in place
                self._card_box_paint(cv, 10, y + 2, st["on"], tag)
                try:
                    cv.itemconfigure(txt, fill=C["text"] if st["on"] else C["muted"])
                except tk.TclError:
                    pass
            return vals
        def keep(_e=None):                      # 2.103.4 (feedback: a typed tier went back to 15 on Search): a
            vals = {}                           # number is kept as you type, like the mods' Min / Max - not only
            for k, e in boxes.items():          # on Enter
                tx = e.get().strip().replace(",", ".")
                try:
                    vals[k] = int(float(tx)) if tx else None
                    e.config(highlightbackground=C["line"])
                except ValueError:
                    e.config(highlightbackground=C["red"])
                    return
            self._card_opt_store(rec, key, vals if vals["min"] is not None or vals["max"] is not None else None)
            rec["changed"] = True
        self._card_click(cv, tag, lambda: take(not st["on"]))
        for e in boxes.values():
            e.bind("<KeyRelease>", keep, add="+")
            e.bind("<Return>", lambda _e: (take(True), "break")[-1])
        self.card_opts[key] = (boxes, on)
        if key == "ilvl":
            self.card_ilvl = (boxes["min"], on)
        return y + 22

    def _card_opt_store(self, rec, key, vals):
        """None = not searched (kept as None when the item's own search would use it - white bases)."""
        self.search_opt_set(rec, key, {k: v for k, v in vals.items() if v is not None} if vals else None,
                            redraw=False)

    def card_ilvl_set(self, rec, on, text=None):
        """Item level on (with its number as the minimum) or off; prices the item again."""
        try:
            n = int(float(str(text).strip())) if on else None
        except (TypeError, ValueError):
            n = rec["item"].get("ilvl")
        self._card_opt_store(rec, "ilvl", {"min": max(1, min(100, n))} if n else None)
        self.card_changed(rec)
        return n

    def _card_tri(self, cv, rec, key, label, x, y, facts):
        """Corrupted: Any / Yes / No - a click steps through them (this item's search only)."""
        from .searchopts_page import default_opts
        cur = {**default_opts(rec["item"]), **(rec.get("opts") or {})}.get(key) or "any"
        has = facts.get("flags", set())
        tag = f"cardtri_{key}"
        cv.create_text(x, y, text=label, anchor="nw", font=("Segoe UI", 9),
                       fill=C["text"] if key in has else C["muted"], tags=(tag,))
        val = cv.create_text(x + 92, y, text=f"{cur.title()} ▾", anchor="nw", font=("Segoe UI", 9, "bold"),
                             fill=C["accent"] if cur != "any" else C["text"], tags=(tag,))
        st = {"cur": cur}

        def click():
            st["cur"] = nxt = {"any": "yes", "yes": "no", "no": "any"}[st["cur"]]
            self.search_opt_set(rec, key, nxt, redraw=False)
            self.card_tris[key] = nxt
            if self._card_mark(rec):                  # 2.104.1: painted in place
                try:
                    cv.itemconfigure(val, text=f"{nxt.title()} ▾", fill=C["accent"] if nxt != "any" else C["text"])
                    self._card_misc_count(cv, rec)
                except tk.TclError:
                    pass
        self._card_click(cv, tag, click)
        self.card_tris[key] = cur

    def _card_misc_count(self, cv, rec):
        """MISCELLANEOUS  (n) - the count follows the picks, in place."""
        from .searchopts_page import default_opts
        cur = {**default_opts(rec["item"]), **(rec.get("opts") or {})}
        n = sum(1 for key, _l in MISC_ROWS if cur.get(key) not in (None, "any", "", "Any"))
        cv.itemconfigure("cardsec_misc", text="▾ MISCELLANEOUS" + (f"  ({n})" if n else ""))

    # ---------------- ▸ Advanced (2.79.0): everything that isn't a filter
    def _detail_advanced(self, d, rec, it, wrap):
        P2, P1 = C["panel2"], C["panel"]

        def block(title):
            f = tk.Frame(d, bg=P1, padx=12, pady=8, highlightthickness=1, highlightbackground=C["line"])
            f.pack(fill="x", pady=(8, 0))
            tk.Label(f, text=title, bg=P1, fg=C["steel"], font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
            return f
        # (2.105.0: no LISTING STATUS - "Listed at" / "Sold for" are gone)
        if rec.get("est") is not None and not rec.get("nomatch") and not rec.get("manual") and not rec.get("skip"):
            eq, opt = RATES.equivalents(rec["est"]), RATES.list_options(rec["est"])
            if eq or opt:
                b = block("IF YOU LIST IT")
                if eq:
                    tk.Label(b, text="≈ " + "  ·  ".join(f"{_amt(a)} {cur}" for cur, a in eq), bg=P1, fg=C["text"],
                             font=("Segoe UI", 9), anchor="w", wraplength=wrap - 30, justify="left").pack(fill="x")
                if opt:
                    tk.Label(b, text="Round to:  " + opt, bg=P1, fg=C["good"], font=("Segoe UI", 9, "bold"),
                             anchor="w", wraplength=wrap - 30, justify="left").pack(fill="x")
        b = block("HOW IT'S PRICED")
        if it.get("gear"):
            tk.Label(b, text=(waystone.summary(it) if it.get("waystone") else gear.summary(it)) +
                     "".join("  ·  " + n for n in it.get("notes") or []), bg=P1, fg=C["muted"], font=("Segoe UI", 9),
                     anchor="w", wraplength=wrap - 30, justify="left").pack(fill="x", pady=(0, 4))
        if rec.get("priced_at"):
            tk.Label(b, text="Priced " + fmt_stamp(rec["priced_at"]), bg=P1, fg=C["muted"], font=("Segoe UI", 9),
                     anchor="w").pack(fill="x")
        hb = tk.Frame(b, bg=P1)
        hb.pack(fill="x")
        self._detail_how(hb, rec, wrap - 30)
        rolls = [m for m in it.get("mods") or [] if m.get("roll") is not None or m.get("tier")]
        if rolls:
            b = block("EACH MOD'S ROLL AND TIER")
            for m in rolls:
                bits = [x for x in ((f"{(m.get('kind') or ' ')[0]}{m['tier']}" if m.get("tier") else ""),
                                    (f"roll {round(m['roll'] * 100)}%" if m.get("roll") is not None else ""),
                                    ", ".join(sorted(m.get("flags") or []))) if x]
                tk.Label(b, text=f"{pretty(m['text'])}  ·  " + "  ·  ".join(bits), bg=P1, fg=C["muted"],
                         font=("Segoe UI", 9), anchor="w", wraplength=wrap - 30, justify="left").pack(fill="x")
        b = block("RAW TEXT")
        self._detail_raw(b, rec, wrap - 30)
        ttk.Button(b, text="Copy name  [C]", command=lambda: self.copy_name(rec, True)).pack(anchor="w", pady=(8, 0))

    def _detail_listing(self, bx, rec):
        """Listed / sold / removed (2.79.0: moved into Advanced)."""
        P1 = C["panel"]
        mark = rec.get("mark", "new")
        cur_txt = {"new": "Not listed yet",
                   "listed": "✔ Listed" + (f" for {rec['list_price']}" if rec.get("list_price") else ""),
                   "sold": "💰 Sold" + (f" for {rec['sold_price']}" if rec.get("sold_price") else ""),
                   "removed": "✖ Removed (reforged / changed)"}[mark]
        tk.Label(bx, text=cur_txt, bg=P1, font=("Segoe UI", 12, "bold"), anchor="w",
                 fg={"new": C["text"], "listed": C["green"], "sold": "#7fe0c0", "removed": C["muted"]}[mark]
                 ).pack(fill="x", pady=(2, 8))
        prow = tk.Frame(bx, bg=P1)
        prow.pack(fill="x", pady=(0, 8))
        tk.Label(prow, text="Listed at", bg=P1, fg=C["muted"], width=8, anchor="w").pack(side="left")
        suggest = rec.get("list_price") or (fmt_div(rec["est"]) if rec.get("est") is not None and not rec.get("skip") else "")
        self.price_var = tk.StringVar(value=suggest)
        ttk.Entry(prow, textvariable=self.price_var, width=14).pack(side="left", padx=(0, 8))
        if mark == "listed":
            ttk.Button(prow, text="↺ Unmark listed", command=lambda: self.mark_selected("new")).pack(side="left")
        else:
            ttk.Button(prow, text="✔ Mark as listed", style="Primary.TButton",
                       command=lambda: self.mark_selected("listed")).pack(side="left")
        srow = tk.Frame(bx, bg=P1)
        srow.pack(fill="x", pady=(0, 8))
        tk.Label(srow, text="Sold for", bg=P1, fg=C["muted"], width=8, anchor="w").pack(side="left")
        self.sold_var = tk.StringVar(value=rec.get("sold_price") or "")
        se = ttk.Entry(srow, textvariable=self.sold_var, width=14)
        se.pack(side="left", padx=(0, 8))
        se.bind("<Return>", lambda e: self.mark_selected("sold"))
        if mark == "sold":
            ttk.Button(srow, text="↺ Unmark sold", command=lambda: self.mark_selected("new")).pack(side="left")
        else:
            ttk.Button(srow, text="💰 Mark as sold", command=lambda: self.mark_selected("sold")).pack(side="left")
        tk.Label(bx, text="A real sale teaches the Mod Book what these mods are worth.", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w").pack(fill="x")
        if mark == "removed":
            ttk.Button(bx, text="↺ Unmark removed", command=lambda: self.mark_selected("new")).pack(anchor="w", pady=(4, 0))
        else:
            ttk.Button(bx, text="✖ Mark as removed (reforged / changed)", style="Quiet.TButton",
                       command=lambda: self.mark_selected("removed")).pack(anchor="w", pady=(4, 0))

    def _card_mod_row(self, cv, rec, m, y, w, font, colr, text):
        """2.74.4: one mod on the item card: [✓] tier  text. -> the next row's y."""
        idx = len(self.card_rows)
        tag = f"cardrow{idx}"
        on = mod_impact(rec, m) != "ignore"
        can = bool(m.get("sid")) or not rec.get("resolved")
        box, bx, tx = 14, 10, 32
        hit = cv.create_rectangle(4, y - 2, w - 4, y + 18, outline="", fill=C["odd"], tags=(tag,))   # the row's click area
        tier = f"{(m.get('kind') or ' ')[0]}{m['tier']}" if m.get("tier") else ""
        if tier:
            cv.create_text(tx, y + 1, text=tier, anchor="nw", font=("Segoe UI", 8), fill=C["muted"], tags=(tag,))
            tx += 22
        right = (2 * CARD_BOX + 16 if self._card_has_vals(rec, m) else 0) + 20     # 2.78.3: Min / Max; 2.79.0: ★
        from .ratemods import key_for
        rkey = key_for(rec, m) if can else None
        if rkey:
            right = 2 * CARD_BOX + 16 + 20 + 30              # 2.97.0: Rate ▾; 2.103.1: it sits by the Min / Max column,
                                                             # so a row without boxes keeps that room too (no overlap)
        fl0 = m.get("flags") or ()
        src0 = next((x for x in ("fractured", "desecrated") if x in fl0 or str(m.get("sid") or "").startswith(x + ".")),
                    None)
        if src0:                                             # 2.97.2: fractured tan, desecrated green
            colr = MOD_COL[src0]
        from . import themes as _th2                         # unticked: its own color, dimmed (not grey)
        shown_c = colr if on and can else (_th2.mix(colr, C["odd"], .5) if can else C["muted"])
        tid = cv.create_text(tx, y, text=text, anchor="nw", font=font, width=w - tx - 12 - right, justify="left",
                             fill=shown_c, tags=("cardmod", tag, f"cardtxt{idx}"))
        bb = cv.bbox(tid)
        y1 = (bb[3] if bb else y + 16) + 4
        if not can:                                          # not on the trade site: nothing to tick
            cv.create_text(tx, y1 - 2, text="not on the trade site", anchor="nw", font=("Segoe UI", 8),
                           fill=C["red"], tags=(tag,))
            y1 += 14
        by = y + 2
        rect = cv.create_rectangle(bx, by, bx + box, by + box, outline=C["muted"] if can else C["line"],
                                   fill=C["accent"] if on and can else C["odd"], tags=("cardbox", tag))
        if on and can:
            cv.create_line(bx + 3, by + 7, bx + 6, by + 10, bx + 11, by + 4, fill="#120a04", width=2,
                           tags=(tag, f"cardchk{idx}"))
        self.card_paint[idx] = {"cv": cv, "rec": rec, "colr": colr, "can": can, "bx": bx, "by": by, "tag": tag}
        fl = m.get("flags") or ()
        src = next((x for x in ("fractured", "desecrated") if x in fl or str(m.get("sid") or "").startswith(x + ".")),
                   None)
        if src and can:                                      # 2.79.0: a fractured mod says so; 2.93.0: and a box to
            only = bool((rec.get("only") or {}).get(norm(m["text"])))    # search it as fractured / desecrated only
            otag = f"cardonly{idx}"
            fc = MOD_COL[src]                                # 2.97.1 / 2.97.2: the mod's own color
            ob = 8                                           # ...and a small box right under it, tied with └
            cv.create_text(tx, y1 - 3, text="└", anchor="nw", font=("Segoe UI", 8), fill=fc, tags=(otag,))
            bx0 = tx + 12
            cv.create_rectangle(bx0, y1, bx0 + ob, y1 + ob, outline=fc, fill=fc if only else C["odd"],
                                tags=(otag, otag + "_r"))
            if only:
                cv.create_line(bx0 + 1, y1 + 4, bx0 + 3, y1 + 7, bx0 + 7, y1 + 1, fill="#120a04", width=2,
                               tags=(otag, otag + "_c"))
            self.card_paint[idx].update(obx=bx0, oby=y1, ofc=fc)
            ox = cv.create_text(bx0 + ob + 4, y1 - 2, text=f"{src} only", anchor="nw", font=("Segoe UI", 8), fill=fc,
                                tags=(otag,))
            cv.tag_bind(otag, "<Button-1>", lambda e, mm=m: self.card_only_click(rec, mm))
            cv.tag_bind(otag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
            cv.tag_bind(otag, "<Leave>", lambda e: cv.configure(cursor=""))
            self.card_onlys[idx] = (m, only, src)
            y1 = max(y1, (cv.bbox(ox) or (0, 0, 0, y1))[3] + 2)
        # (2.97.1: no "RUNE / SOCKETED" line - runes have their own AUGMENTS section)
        cv.coords(hit, 4, y - 2, w - 4 - right, y1 - 2)
        if self._card_has_vals(rec, m):
            self._card_val_boxes(cv, rec, m, y - 1, w, on and can)
        if can:                                              # 2.79.0: ★ = must match (a click: on / off)
            imp = mod_impact(rec, m)
            star = cv.create_text(w - 14, y + 1, text="★" if imp == "high" else "☆", anchor="ne",
                                  font=("Segoe UI", 10), fill=C["good"] if imp == "high" else C["muted"],
                                  tags=(f"cardstar{idx}",))
            cv.tag_bind(star, "<Button-1>", lambda e, mm=m: self.card_set(      # 2.103.3: painted in place
                rec, mm, "normal" if mod_impact(rec, mm) == "high" else "high"))
        if can:
            cv.tag_bind(tag, "<Button-1>", lambda e, mm=m: self.card_toggle(rec, mm, mod_impact(rec, mm) == "ignore"))
            cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
            cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
        if rkey:
            self._card_thumbs(cv, rec, m, rkey, idx, w, y)
        self.card_rows[idx] = (m, on, rect)
        return y1

    # ---------------- 2.78.3 (feedback: "we don't have the option to check ilvl ... to enter mod values / ranges"):
    # on the card itself - the item level with its own check box, Min / Max beside each mod
    def _card_has_vals(self, rec, m):
        if m.get("typed_only"):                             # 2.103.1: a waystone's mods - a range only if you type one
            return m.get("value") is not None and bool(m.get("sid"))
        return m.get("value") is not None and not m.get("novalue") and (bool(m.get("sid")) or not rec.get("resolved"))

    def _card_entry(self, cv, text, enabled=True):
        e = tk.Entry(cv, width=5, bg=C["panel"], fg=C["text"], insertbackground=C["text"], relief="flat",
                     highlightthickness=1, highlightbackground=C["line"], highlightcolor=C["accent"],
                     font=("Segoe UI", 9), justify="center", disabledbackground=C["odd"],
                     disabledforeground=C["muted"])
        e.insert(0, text)
        if not enabled:
            e.config(state="disabled")
        return e

    def _card_val_boxes(self, cv, rec, m, y, w, enabled):
        """Min / Max for one mod - what the search uses; typing changes it for this item; Enter prices it again."""
        saved = m.pop("uval", None)
        try:
            auto = vfilter(m) or {}
        finally:
            if saved is not None:
                m["uval"] = saved
        cur = m.get("uval") if m.get("uval") is not None else auto
        boxes = {}
        for i, key in enumerate(("min", "max")):
            v = cur.get(key)
            e = self._card_entry(cv, "" if v is None else f"{v:g}", enabled)
            x = w - 12 - 18 - CARD_BOX * (2 - i) - (4 if i == 0 else 0)
            cv.create_window(x, y, window=e, anchor="nw", width=CARD_BOX, height=20)
            boxes[key] = e
        if m.get("uval") is not None:
            for e in boxes.values():
                e.config(highlightbackground=C["accent"])

        def keep(_e=None):
            vals = {}
            for key, e in boxes.items():
                t = e.get().strip().replace(",", ".")
                try:
                    vals[key] = float(t) if t else None
                    e.config(highlightbackground=C["line"])
                except ValueError:
                    e.config(highlightbackground=C["red"])
                    return False
            if vals["min"] is not None and vals["max"] is not None and vals["min"] > vals["max"]:
                boxes["max"].config(highlightbackground=C["red"])
                return False
            norm_auto = {k: (None if auto.get(k) is None else float(auto[k])) for k in ("min", "max")}
            if vals == norm_auto:
                m.pop("uval", None)
            else:
                m["uval"] = vals
                for e in boxes.values():
                    e.config(highlightbackground=C["accent"])
            self.dirty = True
            return True
        for e in boxes.values():
            e.bind("<KeyRelease>", keep)
            e.bind("<Return>", lambda _e: (self.reprice([rec["id"]]) if keep() else None, "break")[-1])
        self.card_vals[id(m)] = boxes
        return boxes

    def card_only_click(self, rec, m):
        """2.104.1: the "fractured / desecrated only" box flips in place on Price Checks / Favorites."""
        on = not bool((rec.get("only") or {}).get(norm(m["text"])))
        idx = self._card_row_of(rec, m)
        v = self._card_view(rec)
        if idx is None or v is None:                  # (2.108.0: Bulk Pricing too)
            return self.card_only(rec, m, on)
        self._card_quiet = True
        try:
            self.card_only(rec, m, on)
        finally:
            self._card_quiet = False
        self._card_row_paint(v, idx)
        p = v.card_paint[idx]
        cv, otag = p["cv"], f"cardonly{idx}"
        if "obx" in p:
            try:
                bx0, y1 = p["obx"], p["oby"]
                cv.itemconfigure(otag + "_r", fill=p["ofc"] if on else C["odd"])
                cv.delete(otag + "_c")
                if on:
                    cv.create_line(bx0 + 1, y1 + 4, bx0 + 3, y1 + 7, bx0 + 7, y1 + 1, fill="#120a04", width=2,
                                   tags=(otag, otag + "_c"))
            except tk.TclError:
                pass
        return on

    def card_only(self, rec, m, on):
        """2.93.0 (feedback): search this fractured / desecrated mod only as fractured / desecrated (this item only)."""
        k = norm(m["text"])
        only = rec.setdefault("only", {})
        if on and mod_impact(rec, m) == "ignore":       # 2.97.0 (feedback: "only" did nothing): an unticked mod isn't
            self.toggle_mod(rec, m, True)               # searched at all - "only" ticks it too
        if on:
            only[k] = True
        else:
            only.pop(k, None)
        self.card_changed(rec)
        if getattr(self, "shown_rec", None) is rec and not getattr(self, "_card_quiet", False):
            self.show_detail(rec)
        return on

    def _card_thumbs(self, cv, rec, m, key, idx, w, y):
        """2.97.0 (feedback: ▲ / ▼ were a puzzle): "Rate ▾" left of Min - a menu S / A / B / C / D / F (ignore) / Clear,
        your rule for this mod on every item like it. Rated, it shows your grade ("A ▾"). With Community data sharing
        on it's your vote too."""
        from .ratemods import current
        cur = current([key])
        x = w - 12 - 18 - CARD_BOX * 2 - 4 - 22
        tag = f"cardrate{idx}"
        label = ("F" if cur == "ignore" else cur) if cur else "Rate"
        cv.create_text(x + 6, y + 1, text=label + " ▾", anchor="n", font=("Segoe UI", 8, "bold" if cur else "normal"),
                       fill=C["accent"] if cur else C["muted"], tags=(tag, "cardthumb"))
        cv.tag_bind(tag, "<Button-1>", lambda e: self.card_rate_menu(e, rec, m, key, cur))
        cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
        self.card_thumbs[idx] = (m, key, cur)

    def card_rate_menu(self, e, rec, m, key, cur):
        from .ratemods import set_of
        s = set_of(rec) or ""
        what = (rec.get("item") or {}).get("name") if s.startswith("unique:") else \
            (rec.get("item") or {}).get("class") if s.startswith("gear:") else \
            {"tablet": "tablet", "jewel": "jewel", "waystone": "waystone", "relic": "relic"}.get(s, "item")
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"Rate this mod for every {str(what).lower()}:", state="disabled")
        for g, label in (("S", "S - the price hangs on it"), ("A", "A"), ("B", "B - adds a little"), ("C", "C"),
                         ("D", "D"), ("ignore", "F - ignore (buyers don't pay for it)")):
            menu.add_command(label=("● " if g == cur else "    ") + label,
                             command=lambda g=g: self.card_thumb(rec, m, key, g))
        if cur:
            menu.add_separator()
            menu.add_command(label="Clear my rating", command=lambda: self.card_thumb(rec, m, key, None))
        self.card_rate_open = menu
        try:
            menu.tk_popup(e.x_root, e.y_root)
        finally:
            menu.grab_release()
        return menu

    def card_thumb(self, rec, m, key, what):
        """▲ (High), ▼ (Ignore) or None (clear) for this mod's rule; the item waits for Search (Price Checks) or is
        priced again (Bulk Pricing)."""
        from .ratemods import apply
        apply([key], what)
        from .trade import ov_key
        (rec.get("ov") or {}).pop(ov_key(m), None)              # (the rule speaks for this item now)
        self.card_changed(rec)
        if getattr(self, "shown_rec", None) is rec:
            self.show_detail(rec)
        msg = {"up": "This mod matters - searched on every item like it.",
               "down": "F - this mod doesn't matter: left out on every item like it.",
               "ignore": "F - this mod doesn't matter: left out on every item like it.",
               None: "Your rating for this mod is cleared."}.get(what) or f"Rated {what} - on every item like it."
        self.status_text, self.status_until = msg, time.time() + 6
        return what

    def card_toggle(self, rec, m, checked):
        """2.74.4: a tick on the card - the same as the mod's switch further down (this item only)."""
        g = impact_key(norm(m["text"]))
        if self.card_set(rec, m, ("normal" if g == "ignore" else g) if checked else "ignore"):
            return
        if getattr(self, "shown_rec", None) is rec:
            self.show_detail(rec)

    def _card_view(self, rec):
        """2.103.3: the Price Checks / Favorites view showing this record's card, or None."""
        v = getattr(self, "pcv", None) if rec.get("src") == "pc" else \
            getattr(self, "favv", None) if rec.get("src") == "fav" else getattr(self, "bulkv", None)
        if v is None or getattr(v, "card_paint", None) is None:
            return None
        if rec["id"] != (getattr(self, "pc_rid", None) if rec.get("src") == "pc" else v.rid):
            return None
        if rec.get("src") not in ("pc", "fav") and getattr(self, "shown_rec", None) is not rec:
            return None
        return v

    def _card_row_of(self, rec, m):
        v = self._card_view(rec)
        if v is None:
            return None
        return next((i for i, (mm, _on, _r) in v.card_rows.items() if mm is m and i in v.card_paint), None)

    def card_set(self, rec, m, imp):
        """2.103.3 (feedback: every tick still flickered - the whole card was built again): on Price Checks a tick or
        a star changes only that row on the card, in place. -> True when done that way."""
        idx = self._card_row_of(rec, m)
        if idx is None:
            self.set_item_impact(rec, m, imp)
            return False
        self._card_quiet = True
        try:
            self.set_item_impact(rec, m, imp)
        finally:
            self._card_quiet = False
        self._card_row_paint(self._card_view(rec), idx)
        return True

    def _card_row_paint(self, v, idx):
        from . import themes as _th2
        p = v.card_paint[idx]
        cv, rec, m, can = p["cv"], p["rec"], v.card_rows[idx][0], p["can"]
        imp = mod_impact(rec, m)
        on = imp != "ignore"
        try:
            cv.itemconfigure(f"cardtxt{idx}", fill=p["colr"] if on and can else
                             (_th2.mix(p["colr"], C["odd"], .5) if can else C["muted"]))
            rect = v.card_rows[idx][2]
            cv.itemconfigure(rect, fill=C["accent"] if on and can else C["odd"])
            cv.delete(f"cardchk{idx}")
            if on and can:
                bx, by = p["bx"], p["by"]
                cv.create_line(bx + 3, by + 7, bx + 6, by + 10, bx + 11, by + 4, fill="#120a04", width=2,
                               tags=(p["tag"], f"cardchk{idx}"))
            cv.itemconfigure(f"cardstar{idx}", text="★" if imp == "high" else "☆",
                             fill=C["good"] if imp == "high" else C["muted"])
            for e in (v.card_vals.get(id(m)) or {}).values():
                e.config(state="normal" if on and can else "disabled")
        except tk.TclError:
            return
        v.card_rows[idx] = (m, on, rect)
        self._card_search_paint(rec, v)

    def _detail_how(self, d, rec, wrap):
        """2.60.0: How it's priced - what was searched, why this confidence, each search."""
        P2 = C["panel2"]
        if rec["state"] != "done":
            tk.Label(d, text="Not priced yet - the searches show here when it is.", bg=P2, fg=C["muted"],
                     anchor="w").pack(fill="x")
            return
        for txt, fg in ((rec.get("label"), C["text"]), ("; ".join(rec.get("conf_why") or []), C["muted"]),
                        (rec.get("memory"), C["muted"]), (rec.get("model"), C["muted"])):
            if txt:
                tk.Label(d, text=txt, bg=P2, fg=fg, anchor="w", wraplength=wrap, justify="left",
                         font=("Segoe UI", 9 if fg == C["muted"] else 10)).pack(fill="x", pady=(0, 4))
        if rec.get("prices"):
            tk.Label(d, text="cheapest: " + ",  ".join(fmt_price(p) for p in rec["prices"][:8]), bg=P2,
                     fg=C["text"], anchor="w", wraplength=wrap, justify="left").pack(fill="x", pady=(0, 4))
        if not rec.get("stages"):
            tk.Label(d, text="No trade searches were needed for this one.", bg=P2, fg=C["muted"],
                     anchor="w").pack(fill="x", pady=(8, 0))
        self._detail_stages(d, rec, wrap)
        if rec.get("qid"):
            ttk.Button(d, text="Trade Site  [O]", style="Primary.TButton",
                       command=self.open_trade).pack(fill="x", pady=(8, 0))

    def _detail_raw(self, d, rec, wrap):
        """2.60.0: the item text exactly as the game copied it."""
        P2 = C["panel2"]
        raw = (rec.get("raw") or "").strip()
        if not raw:
            tk.Label(d, text="No copied text kept for this item.", bg=P2, fg=C["muted"], anchor="w").pack(fill="x")
            return
        n = raw.count("\n") + 1
        tx = tk.Text(d, height=min(40, n + 1), bg=C["odd"], fg=C["text"], font=(MONO, 9), relief="flat",
                     highlightthickness=1, highlightbackground=C["line"], wrap="word", padx=8, pady=8)
        tx.insert("1.0", raw)
        tx.config(state="disabled")
        tx.pack(fill="x")

        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(raw)
            self.app_toast("Copied the item text", kind="success")
        ttk.Button(d, text="Copy the item text", command=copy).pack(anchor="w", pady=(8, 0))

    def _detail_stages(self, d, rec, wrap):
        """The searches behind a price, one card each (2.60.0: the "How it's priced" tab)."""
        P2, P1 = C["panel2"], C["panel"]

        def box(parent, edge=None, pad=(12, 8)):            # 2.74.5: lighter
            return tk.Frame(parent, bg=P1, padx=pad[0], pady=pad[1], highlightthickness=1, highlightbackground=edge or C["line"])
        stages = rec.get("stages") or []
        if stages:
            tk.Label(d, text="HOW THIS PRICE WAS CALCULATED", bg=P2, fg=C["steel"], font=("Segoe UI", 9, "bold"),
                     anchor="w").pack(fill="x", pady=(8, 4))
            for i, s_ in enumerate(stages, 1):
                v = s_.get("verify") or {}
                sc = box(d, pad=(8, 8))
                sc.pack(fill="x", pady=2)
                top = tk.Frame(sc, bg=P1)
                top.pack(fill="x")
                link = tk.Label(top, text="open ↗", bg=P1, fg=C["accent"], cursor="hand2", font=("Segoe UI", 9, "bold"))
                link.pack(side="right", padx=(8, 0))
                link.bind("<Button-1>", lambda _e, q=s_["qid"]: self.open_qid(q))
                tk.Label(top, text=f"{i}. {s_['name']}", bg=P1, fg=C["text"] if s_.get("weight") else C["muted"],
                         font=("Segoe UI", 10, "bold"), anchor="w", wraplength=wrap-110, justify="left").pack(side="left", fill="x", expand=True)
                bot = tk.Frame(sc, bg=P1)
                bot.pack(fill="x")
                res = f"{s_['n']} listing{'s' if s_['n'] != 1 else ''} found"
                if v.get("bad") and not v.get("unverifiable"):
                    res += f" · {v['bad']} dropped (lacked a mod)"
                tk.Label(bot, text=res, bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(side="left")
                right = ""
                if s_.get("est") is not None and s_["n"]:
                    right = fmt_div(s_["est"]) + (f" · weight {s_['weight']:g}" if s_.get("weight") else " · not used")
                tk.Label(bot, text=right, bg=P1, fg=C["good"] if s_.get("weight") else C["muted"], font=(MONO, 9, "bold")).pack(side="right")

    def value_boxes(self, rec, m, row, imp):
        """Min / Max boxes for one mod (1.35). They show what the search uses; typing changes it for this item only.
        Each keystroke is kept (so clicking elsewhere loses nothing); Enter prices the item again."""
        P1 = C["panel"]
        auto = None
        saved_uval = m.pop("uval", None)
        try:
            auto = vfilter(m) or {}                       # what the search would use without your values
        finally:
            if saved_uval is not None:
                m["uval"] = saved_uval
        cur = m.get("uval") if m.get("uval") is not None else auto
        vb = tk.Frame(row, bg=P1)
        vb.pack(fill="x", pady=(4, 0))
        tk.Label(vb, text=f"your roll {m['value']:g}", bg=P1,
                 fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
        boxes = {}
        for key in ("min", "max"):
            tk.Label(vb, text=key.title(), bg=P1, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
            v = tk.StringVar(value="" if cur.get(key) is None else f"{cur[key]:g}")
            e = tk.Entry(vb, textvariable=v, width=6, bg=C["odd"], fg=C["text"], insertbackground=C["text"],
                         relief="flat", highlightthickness=1, highlightbackground=C["line"], highlightcolor=C["accent"],
                         font=("Segoe UI", 10), disabledbackground=C["panel2"])
            e.pack(side="left", padx=(0, 8))
            if imp == "ignore":
                e.config(state="disabled")                # not searched at all, so its value can't matter
            boxes[key] = (v, e)
        edited = tk.Label(vb, text="", bg=P1, fg=C["accent"], font=("Segoe UI", 9, "bold"), cursor="hand2")
        edited.pack(side="left")

        def mark_edited():
            edited.config(text="yours · reset" if m.get("uval") is not None else "")

        def keep(_e=None):
            vals, bad = {}, False
            for key, (v, e) in boxes.items():
                t = v.get().strip().replace(",", ".")
                if not t:
                    vals[key] = None
                    e.config(highlightbackground=C["line"])
                    continue
                try:
                    vals[key] = float(t)
                    e.config(highlightbackground=C["line"])
                except ValueError:
                    bad = True
                    e.config(highlightbackground=C["red"])
            if bad:
                return
            if vals.get("min") is not None and vals.get("max") is not None and vals["min"] > vals["max"]:
                boxes["max"][1].config(highlightbackground=C["red"])
                return
            norm_auto = {k: auto.get(k) for k in ("min", "max")}
            m["uval"] = None if vals == {k: (None if v is None else float(v)) for k, v in norm_auto.items()} else vals
            if m["uval"] is None:
                m.pop("uval", None)
            self.dirty = True
            mark_edited()

        def reset(_e=None):
            m.pop("uval", None)
            self.dirty = True
            self.card_changed(rec)

        for key, (v, e) in boxes.items():
            e.bind("<KeyRelease>", keep)
            e.bind("<Return>", lambda _e: (keep(), self.reprice([rec["id"]]), "break")[-1])
        edited.bind("<Button-1>", reset)
        mark_edited()

    # ---------------- mod book page
    def refresh_memory(self, force=False):
        """The 'Mod book' page: everything learned from the listings the app has fetched. Asking prices only - never sale
        prices, and mostly the cheap end."""
        if not hasattr(self, "mem_view") or (not force and not self.page_open("Mod Book")):
            return
        cat = self.rules_cat()                         # 2.99.0: the learned rows of the tab showing
        ns = self.rt.get(cat)
        if ns is None or not hasattr(ns, "mem_frame"):
            return
        self.mem_frame, self.mem_info, self.mem_empty = ns.mem_frame, ns.mem_info, ns.mem_empty
        for w in self.mem_frame.winfo_children():
            w.destroy()
        view = self.mem_view.get()
        q = self.mem_filter.get().lower().strip()

        def nice(sid):
            t = SIDTEXT.get(sid, sid)
            return re.sub(r"\s+(found )?in map$", "", t)
        if view == "Mod priority":
            cols = [("base", "Base", 140, "w"), ("mod", "Mod", 420, "w"), ("n", "Listings", 70, "e"),
                    ("med", "Median ask", 100, "e"), ("lift", "Worth vs others", 135, "e"), ("data", "Data says", 110, "w"),
                    ("mine", "Your mark", 90, "w"), ("check", "Check", 330, "w")]
            data = [r for r in self.priority_rows() if (not q or q in (r[0] + " " + nice(r[1])).lower())
                    and self.mb_base_ok(r[0], cat)]
            note = "Which mods the data says are valuable, next to your own marks. Rows that need a look come first."
        elif view == "Single mods":
            cols = [("base", "Base", 140, "w"), ("mod", "Mod", 480, "w"), ("n", "Listings seen", 90, "e"),
                    ("lo", "Cheapest ask", 110, "e"), ("med", "Median ask", 110, "e"), ("hi", "Highest ask", 110, "e"),
                    ("age", "Last seen", 90, "e")]
            data = [r for r in MARKET.mod_summary() if (not q or q in (r[0] + " " + nice(r[1])).lower())
                    and self.mb_base_ok(r[0], cat)]
            note = "Every mod seen on a fetched listing, and what those listings asked."
        elif view == "Mod combinations":
            cols = [("base", "Base", 140, "w"), ("mods", "Mods searched together", 560, "w"),
                    ("seen", "Searches", 70, "e"), ("best", "Highest cheapest-listing", 150, "e"),
                    ("last", "Latest cheapest", 110, "e"), ("est", "Latest estimate", 110, "e"), ("age", "Last seen", 90, "e")]
            data = [r for r in MARKET.combos() if (not q or q in (r[0] + " " + " ".join(nice(f[0]) for f in r[1])).lower())
                    and self.mb_base_ok(r[0], cat)]
            note = "Every set of mods that was searched together, and the price it came out at."
        else:
            cols = [("star", "★", 46, "center"), ("base", "Base", 140, "w"), ("text", "Mod", 420, "w"),
                    ("floor", "Cheapest with this mod", 160, "e"), ("total", "Listings", 80, "e"), ("age", "Checked", 100, "e")]
            data = sorted((e for e in MODBOOK.values() if (not q or q in (e.get("base", "") + " " + e.get("text", "")).lower())
                           and self.mb_base_ok(e.get("base", ""), cat)),
                          key=lambda e: (e.get("floor") is None, -(e.get("floor") or 0)))
            note = ("The old Mod Book, kept as it was and no longer updated. Mods it found valuable carry on as learned "
                    "'High' (see Mod priority); this league's own data overrules them.")
        tv = ttk.Treeview(self.mem_frame, columns=[c[0] for c in cols], show="headings")
        for cid, title, w, anchor in cols:
            tv.heading(cid, text=title)
            tv.column(cid, width=w, anchor=anchor, stretch=(cid in ("mods", "mod", "text")))
        tv.tag_configure("warn", foreground=C["orange"])
        tv.tag_configure("great", foreground=C["good"])
        self.list_register("modbook", tv)
        sb = ttk.Scrollbar(self.mem_frame, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tv.pack(fill="both", expand=True)
        tv.tag_configure("odd", background=C["odd"])
        for i, row in enumerate(data):
            tag = ("odd",) if i % 2 else ()
            if view == "Mod priority":
                base, sid, n, med, lift, says, mine, check, kind = row
                tv.insert("", "end", values=(base, nice(sid), n, fmt_div(med), "" if lift is None else f"{lift:.1f}x",
                                             says, mine, check), tags=(kind,) if kind else tag)
            elif view == "Mod combinations":
                base, filt, seen, best, (ts, n, fl, es) = row
                mods = "  +  ".join(nice(sid) + (f" ≥{t:g}" if op == "min" else f" ≤{t:g}" if op == "max" else "")
                                    for sid, op, t in filt)
                tv.insert("", "end", values=(base, mods, seen, fmt_div(best), fmt_div(fl), fmt_div(es), ago(ts)), tags=tag)
            elif view == "Single mods":
                base, sid, n, lo, med, hi, last = row
                tv.insert("", "end", values=(base, nice(sid), n, fmt_div(lo), fmt_div(med), fmt_div(hi), ago(last)), tags=tag)
            else:
                e = row
                good = e.get("floor") is not None and e["floor"] >= SETTINGS["good_div"]
                age = (time.time() - e.get("ts", 0)) / 86400
                tv.insert("", "end", values=("★" if good else "", e.get("base", ""), e.get("text", ""),
                                             fmt_div(e["floor"]) if e.get("floor") is not None else (e.get("raw") or "no listings"),
                                             e.get("total", ""), "long ago" if not e.get("ts") else "today" if age < 1 else f"{int(age)}d ago"),
                          tags=("great",) if good else tag)
        self.mem_tv = tv
        self.mem_info.config(text=note + "  Asking prices only, mostly the cheap end.\n" + MARKET.accuracy_text(), wraplength=1100)
        if data:
            self.mem_empty.place_forget()
        else:
            self.mem_empty.config(text=self.mem_empty_reason() if not q else "Nothing matches that filter.")
            self.mem_empty.place(relx=0.5, rely=0.4, anchor="center")

    def mem_empty_reason(self):
        """Say plainly WHY the Mod book has nothing to show."""
        if not MARKET.db:
            return ("The memory database could not be opened, so nothing can be learned.\n"
                    f"{MARKET.db_error or 'Reason unknown.'}\nThe file is market.db in {DATA_DIR}.")
        n_obs, n_list = MARKET.counts()
        if n_obs == 0:
            return ("Nothing has been recorded yet for this league.\nThe page fills in after items finish pricing with real trade-site "
                    "searches (items that only say NO MATCH or fail with an error record nothing).")
        if n_list == 0:
            return (f"{n_obs} searches are recorded, but no listing details were stored.\n"
                    f"Last recording problem: {MARKET.last_error or 'none seen - the listings may have had unknown currencies or no matching mod text.'}"
                    "\n\n" + MARKET.rec_summary() + self._mem_examples())
        view = self.mem_view.get()
        why = "\n\n" + MARKET.rec_summary() + self._mem_examples()
        if view == "Mod priority":
            return (f"{n_list} listings stored. A mod appears here once 8 listings have it and 8 do not.\n"
                    "Try the 'Single mods' view to see everything stored so far." + why)
        return f"{n_obs} searches and {n_list} listings are stored, but none of them carry mods the app could read." + why

    @staticmethod
    def _mem_examples():
        """A few of the listing lines that couldn't be read, so you can see what went wrong right here."""
        lines = (MARKET.rec_stats.get("line_samples") or [])[:3]
        out = ""
        if lines:
            out = "\n\nLines it couldn't read, for example:\n" + "\n".join("  " + l for l in lines)
        return out + "\nThe full details are in market_log.txt in the data folder."

    def priority_rows(self):
        """Mod priority view: your mark next to what the data says, with a plain Check column."""
        rows = []
        for (base, sid), st in MARKET.cached_stats().items():
            k = SIDTEXT.get(sid)
            if not k:
                continue
            mine = RULES.get(k) if RULES.get(k) in IMPACTS else default_impact(k)       # your mark, never the learned one
            if st["tier"] == "high":
                says = "High"
            elif not st["decided"]:
                says = "Not enough data"
            else:
                says = "Normal"
            if mine == "ignore" and says == "High":
                check, kind = "⚠ ignored (your rule or the built-in default), but the data says it's valuable", "warn"
            elif mine == "high" and says == "Normal":
                check, kind = "your S/A isn't backed by the data yet", "warn"
            elif mine == "high" and says == "High":
                check, kind = "agree", "great"
            elif mine != "high" and says == "High":
                check, kind = "learned: treated as High automatically", "great"
            else:
                check, kind = "", ""
            rows.append((base, sid, st["n"], st["med"], st["lift"], says, self.mb_rating([k]), check, kind))   # (2.114.0: the rating)
        rows.sort(key=lambda r: (r[8] == "", -(r[4] or 0)))
        return rows[:1000]

    def save_widths(self):
        try:
            SETTINGS["col_widths"] = {c[0]: int(self.tree.column(c[0], "width")) for c in self.COLS}
            pw = int(self.outer.winfo_width())
            if pw >= 250:              # 2.0 beta 22: a closed / minimised window reports 1 - that hid the item panel
                SETTINGS["panel_w"] = pw
        except Exception:
            buglog.caught()

    # ---------------- 2.23.1: the window opens where you left it
    @staticmethod
    def desktop_rect():
        """(left, top, width, height) of all monitors together (Windows), else the main screen; None if unknown."""
        if sys.platform == "win32":
            try:
                import ctypes
                g = ctypes.windll.user32.GetSystemMetrics
                return g(76), g(77), g(78), g(79)        # SM_X/YVIRTUALSCREEN, SM_CX/CYVIRTUALSCREEN
            except Exception:
                return None
        return None

    def saved_geometry(self):
        """"WxH+X+Y" from last time - only if its title bar is still on a screen (a monitor may be gone)."""
        g = SETTINGS.get("main_window") or {}
        try:
            w, h, x, y = int(g["w"]), int(g["h"]), int(g["x"]), int(g["y"])
        except (KeyError, TypeError, ValueError):
            return None
        w, h = max(1000, w), max(560, h)
        d = self.desktop_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        dx, dy, dw, dh = d
        if x + w - 120 < dx or x + 120 > dx + dw or y < dy - 10 or y + 40 > dy + dh:
            return f"{min(w, dw)}x{min(h, dh)}"            # off every screen now: keep the size, let Windows place it
        return f"{w}x{h}+{x}+{y}"

    def _note_window(self, e):
        """Remember the window's place and size as it moves (the normal size, not maximised)."""
        if e.widget is not self.root or not getattr(self, "_win_restored", False):
            return                    # 2.26.2: not while it opens - the first "normal" event wiped "maximised"
        try:
            st = self.root.state()
        except tk.TclError:
            return
        g = SETTINGS.setdefault("main_window", {})
        if st == "normal":
            if self.root.winfo_width() > 200:
                g.update(w=self.root.winfo_width(), h=self.root.winfo_height(), x=self.root.winfo_x(),
                         y=self.root.winfo_y())
            g["zoomed"] = False
        elif st == "zoomed":
            g["zoomed"] = True
        else:
            return
        job = getattr(self, "_win_save_job", None)            # written a moment after it stops moving (a crash
        if job:                                               # keeps it too)
            self.root.after_cancel(job)
        self._win_save_job = self.root.after(3000, lambda: save_json("settings.json", SETTINGS))

    def restore_zoom(self, tries=0):
        """Maximised last time -> maximised again. 2.25.4: only once the window is really on screen (asking before
        that did nothing on Windows, so it opened at the plain size), and checked: if Tk didn't, Windows is asked."""
        if not (SETTINGS.get("main_window") or {}).get("zoomed"):
            self._win_restored = True                                # from now on, moves and sizes are kept
            return
        try:
            if not self.root.winfo_viewable() or SPLASH[0] is not None:
                if tries < 60:                                       # up to ~15 s (the start-up screen)
                    self.root.after(250, lambda: self.restore_zoom(tries + 1))
                    return
            if self.root.state() != "zoomed":
                self.root.state("zoomed")
            self.root.update_idletasks()
            if self.root.state() != "zoomed" and sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.ShowWindow(self._hwnd(), 3)     # SW_MAXIMIZE
        except Exception:
            buglog.caught()
        self.root.after(500, lambda: setattr(self, "_win_restored", True))

    def on_close(self):
        self.save_widths()
        self.save_session()
        try:                                         # 2.31.0: send this hour's mod prices before going
            from . import communitymods as CM
            if CM.sharing():
                t = threading.Thread(target=lambda: CM.push(MARKET, dict(RULES)), daemon=True)
                t.start()
                t.join(4)
        except Exception:
            buglog.caught()
        try:                                         # 2.0 beta 9: a running session is kept (without a profit)
            s = getattr(self, "tk_session", None)
            if s is not None and s.ended is None:
                s.stop()
                s.note = (s.note + " (app closed)").strip()
                self.tk_sessions.add(s)
            self.merged_destroy()                    # (keeps where the overlay was)
        except Exception:
            buglog.caught()
        self.stop_utilities()                        # saves the notes; stops the Delirium alert if the app started it
        save_json("settings.json", SETTINGS)
        save_modbook()
        WEALTH.save()
        LIMITER._save(True)
        self.tray.hide_icon()
        self.root.destroy()


SPLASH = [None]          # the start-up screen while the app is built (2.0.0)
CRASHED = [False]        # 2.114.3: the app closed by itself last time (crash_report.txt was written)


def look_settings():
    """The theme's id from settings. 2.60.0: theme packs - everyone starts on Emberforge once (the user's pick).
    (2.119.0: accent and text size are gone.)"""
    from . import themes as _th
    if not SETTINGS.get("theme_packs"):
        SETTINGS["theme_packs"] = 1
        SETTINGS["theme"] = _th.DEFAULT
        save_json("settings.json", SETTINGS)
    return _th.pick_id(SETTINGS.get("theme"))


def _splash_step(text=None, i=None):
    s = SPLASH[0]
    if s is not None:
        try:
            s.step(text, i)
        except Exception:
            buglog.caught()


def main():
    if FROZEN and sys.platform == "win32":                # 2.29.1: remove what an update left behind
        threading.Thread(target=cleanup_update, args=(APP_DIR,), daemon=True).start()
    try:
        from .fonts import load as _load_fonts           # 2.110.0: the overlay styles' bundled fonts (this app only)
        _load_fonts()
    except Exception:
        buglog.caught()
    root = tk.Tk(className="StashOfExile2")      # 2.10.0: window managers (Hyprland) see class "Stashofexile2"
    try:                                         # 2.115.0: every problem in one log (buglog), uncaught ones too
        from .buglog import install as _bug_install
        _bug_install(root, APP_VERSION)
    except Exception:
        buglog.caught()
    try:                                         # 2.112.1: not responding? where it was stuck goes to hang_report.txt
        from .hangwatch import start as _hang_start
        from .config import P as _P
        _hang_start(root, _P("hang_report.txt"), APP_VERSION)
        from .hangwatch import crash_start as _crash_start   # 2.114.3: closed by itself last time? crash_report.txt
        if _crash_start(os.path.dirname(_P("hang_report.txt")), APP_VERSION):
            CRASHED[0] = True
    except Exception:
        buglog.caught()
    try:                               # the start-up screen (2.119.0: always - its switch is gone)
        from .splash import Splash
        from .style import apply_look
        apply_look(look_settings(), root)
        SPLASH[0] = Splash(root, ICON_B64, pretty_version(), SETTINGS.get("league") or "")
    except Exception:
        SPLASH[0] = None
    app = App(root)
    if CRASHED[0]:                     # 2.115.0: Report it - the form, filled in, with the crash in the app's log
        root.after(6000, lambda: app.app_toast(
            "The app closed by itself last time. Where it was (code locations only - nothing about you) is in the "
            "app's log; Report it sends it to be fixed.", "The app closed by itself",
            actions=[("Report it", lambda: app.bug_report_open(
                "The app closed by itself", "It closed by itself while I was ... (what were you doing?)")),
                     ("Not now", lambda: None)], kind="warning"))
    root.mainloop()
