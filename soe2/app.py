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
import tkinter as tk
import traceback
import types
import webbrowser
from datetime import datetime
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from .config import (
    AGE_OPTIONS, DATA_UPDATED, APP_DIR, APP_TITLE, APP_VERSION, pretty_version, DATA_DIR, load_json, MIGRATED, MODBOOK, MODBOOK_NOTE, P,
    save_json, save_modbook, SETTINGS, STATUS_OPTIONS, VIEWS,
)
from .clipboard import clip_seq, read_clipboard_text
from .util import _amt, _num, mmss
from .net import _STATUS_HOOK, fmt_stamp, LIMITER, PACES, per_text
from .updates import clean_env, cleanup_update, download_asset, FROZEN, latest_release, pick_asset, REPO, is_newer, vtuple
from .rates import RATES
from .mods import (
    auto_impact, COMMUNITY, COMMUNITY_ACTIVE, COMMUNITY_DISAGREE, default_impact, impact_key, IMPACT_LABEL,
    IMPACTS, JEWEL_KINDS, JEWELS, LEARNED, learned_info, mod_cat, norm, parse_item, pretty, rebuild_community,
    RULES, SHARE_MAX_HIGH, SIDTEXT, TAB_KINDS, TABS, TEXT2SID, vfilter, rule_key, SCOPED_CATS, migrate_scoped_rules,
    default_tier, scoped, tier_key, TIER_ORDER, TIERS,
)
from .mods import DUPS, find_stat, current_key
from .trade import ago, mod_impact
from .market import MARKET
from .pricefmt import fmt_div, fmt_price, parse_price
from .wealth import WEALTH, parse_stack, WPRICES
from .engine import Engine
from . import gear, waystone
from .toasts import Toasts
from .style import C, FLAG_COLORS, FONT_TITLE, hotkey_blocked, MONO, Plate, SegBook, SegBar, setup_style, Toast, KeyCapture
from .winsys import ICON_B64, KeyWatch, Tray
from .wealth_page import WealthPage
from .wealth_setup import WealthSetup
from .listkeys import ListKeys
from .alerts_page import AlertsPage
from .about_page import AboutPage
from .tabreader_page import TabReaderPage
from .searchopts_page import SearchOptsPage
from .valuelog import VALUE_LOG
from .exchange_page import ExchangePage
from .library_page import LibraryPage
from .regex_page import RegexPage
from .calc import CalcPage
from .insights_page import InsightsPage
from .moneymakers_page import MoneyMakersPage
from .maplib_page import MapLibraryPage
from .remnant_page import RemnantPage         # 2.37.0: Expedition Remnant Price Checker
from .ledger_page import LedgerPage           # 2.45.0: Money Makers > Farm Ledger
from .feedback_page import FeedbackPage       # 2.48.0: the update badge and Report a bug (taskbar)
from .utilities_page import UtilitiesPage
from .tracker_page import TrackerPage
from .search_page import SearchPage
from . import gamedata
from . import modules
from .shell import Shell


from .config import PAGE_CHECKS       # 1.40: was "Items"


class App(ListKeys, AlertsPage, AboutPage, TabReaderPage, SearchOptsPage, ExchangePage, WealthSetup, WealthPage, LibraryPage, RegexPage, UtilitiesPage, TrackerPage, SearchPage, CalcPage, InsightsPage, MoneyMakersPage, MapLibraryPage, RemnantPage, LedgerPage, FeedbackPage):
    COLS = [("added", "#", 46, "e"), ("name", "Item", 220, "w"), ("type", "Type", 110, "w"), ("mark", "Status", 90, "center"),
            ("est", "Est. value", 110, "e"), ("conf", "Confidence", 95, "center"), ("listings", "Listings", 70, "e"), ("priced", "Priced at", 130, "w"),
            ("match", "How it was priced", 300, "w"), ("vmods", "Valuable mods", 100, "center")]
    # 2.24.0: "★ Valuable" (how many of the item's mods your Mod book rates High) is the last column in the data, so
    # older code reading values by position keeps working, but it's shown right after the item's name
    SHOW_COLS = ("added", "name", "vmods", "type", "mark", "est", "conf", "listings", "priced", "match")
    MARK_TEXT = {"new": "", "listed": "✔ listed", "sold": "💰 sold", "removed": "✖ removed"}
    VIEW_MARK = {"Not yet listed": "new", "Listed": "listed", "Sold": "sold", "Removed": "removed"}

    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        if sys.platform == "win32":      # own taskbar entry with our icon (not python's)
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("StashOfExile2.App")
            except Exception:
                pass
        try:
            self.icon_img = tk.PhotoImage(data="".join(ICON_B64.split()))     # keep on self or tk drops it
            root.iconphoto(True, self.icon_img)
        except Exception:
            pass
        root.geometry(self.saved_geometry() or "1280x800")      # 2.23.1: where you left it last time
        root.minsize(1000, 560)
        root.bind("<Configure>", self._note_window, add="+")
        from .style import apply_look                   # 2.0.0: Settings > Appearance (theme, accent, text size)
        apply_look(SETTINGS.get("theme", "midnight"), SETTINGS.get("accent", "orange"),
                   int(SETTINGS.get("ui_scale", 100) or 100), root)
        root.configure(bg=C["bg"])
        from . import overlaywin as _ow                  # 2.43.0: the look of the windows over the game
        _ow.LOOK[0] = SETTINGS.get("overlay_look") if SETTINGS.get("overlay_look") in _ow.LOOKS else "parchment"
        setup_style(root)
        self.records, self.next_id = {}, 1
        self.ui_q = queue.Queue()
        _STATUS_HOOK[0] = lambda s: self.ui_q.put(("status", s))
        self.engine = Engine(self.records, self.ui_q)
        gamedata.set_fallback(self.trade_stat_lookup)          # 1.40: learn unknown mod wordings from the trade site
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
        self.migrate_rules_once()
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
        self.start_utilities()                       # 2.0: chat commands & notes listen to the same keyboard watcher
        root.after(15000, self.cm_start)             # 2.31.0: the community Mod book (hourly)
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
            pass

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
            pass

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
                pass
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
        elif what == "quit":
            self.tray.hide_icon()
            self.on_close()

    # ---------------- layout (2.0 beta 7: a desktop with a window per module, see shell.py and modules/)
    def build(self):
        r = self.root
        r.configure(bg=C["bg"])
        self.PAGES = [PAGE_CHECKS, "Wealth", "Mod book", "Regex", "Notes",
                      "Settings"]
        self.page_var = tk.StringVar(value=PAGE_CHECKS)           # the window in front (kept for older code)
        self.top_var = tk.BooleanVar(value=SETTINGS.get("on_top", True))
        self.league_var = tk.StringVar(value=SETTINGS["league"])
        self.pace_var = tk.StringVar(value=SETTINGS["pace"] if SETTINGS["pace"] in PACES else "Balanced")
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
        self.limit_lbl = tk.Label(strip, text="", bg=C["bg"], fg=C["muted"], padx=16, cursor="hand2", font=(MONO, 9))
        self.limit_lbl.pack(side="right")
        self.limit_lbl.bind("<Button-1>", self.open_limits)
        self.rates_lbl = tk.Label(strip, text="Rates: …", bg=C["bg"], fg=C["muted"], padx=8, cursor="hand2", font=(MONO, 9))
        self.rates_lbl.pack(side="right")
        self.rates_lbl.bind("<Button-1>", self.open_rates)
        self.status = tk.Label(strip, text="Starting...", anchor="w", bg=C["bg"], fg=C["muted"], padx=16, pady=4)
        self.status.pack(side="left", fill="x", expand=True)

        # ---- taskbar, right side: league (opens Settings), utilities, always on top, clock
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
        self.pin_lbl = tk.Label(self.shell.task_right, text="📌", bg=tb, font=("Segoe UI Emoji", 10), cursor="hand2")
        self.pin_lbl.pack(side="left", padx=(8, 0), before=self.shell.clock)
        self.pin_lbl.bind("<Button-1>", lambda e: (self.top_var.set(not self.top_var.get()), self.on_top_toggle()))
        self._top_label()
        from . import shell as _shell
        _shell.CLOCK["format"] = SETTINGS.get("clock_format", "auto")
        _splash_step(i=2)
        self.shell.finish()
        self.shell.set_launcher(self.shell.cfg.get("launcher", "dock"))
        self.root.after(60, self.restore_zoom)                 # 2.23.1: maximised last time -> maximised again
        self.root.after(1500, self.show_whatsnew)              # 2.0 beta 12: once per new version
        if SPLASH[0] is not None:                              # 2.0.0: the start-up screen waits for the mod list,
            _splash_step(i=3)                                  # but never more than 3 seconds
            self.root.after(3000, self.close_splash)
        self.bind_hotkeys()
        self.refresh_total_header()

    # ---------------- welcome / what's new (once per version)
    def show_whatsnew(self, force=False):
        from .whatsnew import INTRO, notes_between
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
        head = tk.Frame(inner, bg="#1a2a4c", padx=16, pady=12)
        head.pack(fill="x")
        welcome = not seen and not force
        tk.Label(head, text="Welcome to StashOfExile2" if welcome else f"What's new in v{pretty_version()}",
                 bg="#1a2a4c", fg="#ffffff", font=(FONT_TITLE, 16, "bold"), anchor="w").pack(fill="x")
        tk.Label(head, text=f"version {pretty_version()}" + ("" if welcome or not seen or force else
                                                              f"  (you had {pretty_version(seen)})"),
                 bg="#1a2a4c", fg="#9fb6dd", anchor="w").pack(fill="x")
        if welcome:                                             # first start: pick your league right away
            lrow = tk.Frame(inner, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["accent"])
            lrow.pack(fill="x", padx=12, pady=(8, 0))
            tk.Label(lrow, text="Which league do you play?", bg=P2, fg=C["accent"],
                     font=("Segoe UI", 12, "bold")).pack(side="left")
            self.wn_league = ttk.Combobox(lrow, textvariable=self.league_var, state="readonly", width=28,
                                          values=list(self.league_box["values"] or ()) or [self.league_var.get()])
            self.wn_league.pack(side="left", padx=8)
            self.wn_league.bind("<<ComboboxSelected>>", self.on_league)
            tk.Label(inner, text="The newest league is picked for you. Prices come from this league; you can change "
                                 "it any time in Settings.", bg=P1, fg=C["muted"], font=("Segoe UI", 9),
                     anchor="w", padx=16).pack(fill="x", pady=(4, 0))
        foot = tk.Frame(inner, bg=P1, padx=16, pady=8)
        foot.pack(fill="x", side="bottom")
        ttk.Button(foot, text="Got it", style="Primary.TButton", command=self.close_whatsnew).pack(side="right")
        tk.Label(foot, text="Shows once per version. Toolkit menu > What's new brings it back.", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9)).pack(side="left")
        t = tk.Text(inner, bg=P2, fg=C["text"], relief="flat", wrap="word", padx=16, pady=12, highlightthickness=0,
                    font=("Segoe UI", 10), cursor="arrow")
        t.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        t.tag_configure("h", foreground=C["accent"], font=("Segoe UI", 12, "bold"), spacing1=8, spacing3=4)
        t.tag_configure("p", spacing3=6, lmargin1=0, lmargin2=0)
        t.tag_configure("li", spacing3=5, lmargin1=8, lmargin2=22)
        if welcome or force:
            t.insert("end", "What it is\n", "h")
            for line in INTRO:
                t.insert("end", line + "\n", "p")
        for v, lines in notes:
            t.insert("end", f"New in {pretty_version(v)}\n", "h")
            for line in lines:
                t.insert("end", "•  " + line + "\n", "li")
        # (2.4.0: "Coming next" is no longer shown here - the plan lives in ROADMAP.md)
        t.config(state="disabled")
        card.lift()

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
        return f"v{pretty_version()}  ·  {self.league_var.get() or 'no league picked'}"

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
        summ = tk.Frame(body, bg=C["panel2"], padx=12, pady=8)
        summ.pack(fill="x")
        self.tot_lbl = tk.Label(summ, text="", bg=C["panel2"], fg="#9fb6dd", font=("Segoe UI", 9, "bold"))
        self.tot_val = tk.Label(summ, text="", bg=C["panel2"], fg=C["good"], font=("Segoe UI", 16, "bold"))
        self.chip_priced = tk.Label(summ, text="", bg="#0f2038", fg=C["green"], font=("Segoe UI", 9, "bold"), padx=8, pady=4,
                                    highlightthickness=1, highlightbackground="#3f7a58")
        self.chip_review = tk.Label(summ, text="", bg="#2a2110", fg=C["good"], font=("Segoe UI", 9, "bold"), padx=8, pady=4,
                                    highlightthickness=1, highlightbackground="#7a6428")
        # 2.26.0: "pricing 12 items - about 1:30 left", next to the other two (was only in the status line)
        self.chip_eta = tk.Label(summ, text="", bg="#10203a", fg="#8fc4ff", font=("Segoe UI", 9, "bold"), padx=8,
                                 pady=4, highlightthickness=1, highlightbackground="#3f5f8f")
        self.tot_lbl.pack(side="left")
        self.tot_val.pack(side="left", padx=(8, 0))
        self.chip_review.pack(side="right")
        self.chip_priced.pack(side="right", padx=(0, 8))
        # 2.26.4: what the stars in Valuable mods mean - up top where it is seen (was a small line under the list)
        self.vmods_legend = tk.Label(summ, text="Valuable mods:  ★ = a mod your Mod book rates valuable  (★★★ = three)",
                                     bg="#2a2110", fg="#ffd9a8", font=("Segoe UI", 9, "bold"), padx=8, pady=4,
                                     highlightthickness=1, highlightbackground="#7a6428")
        self.vmods_legend.pack(side="left", padx=(16, 0))
        # 2.31.0: how much the community Mod book knows (shown once there is something)
        self.cm_chip = tk.Label(summ, text="", bg="#10203a", fg="#8fc4ff", font=("Segoe UI", 9), padx=8, pady=4,
                                highlightthickness=1, highlightbackground="#3f5f8f")
        self.root.after(3000, self.cm_paint)

        # ---- the two toolbar rows
        tb = tk.Frame(body, bg=C["panel"], highlightthickness=1, highlightbackground=C["line"])
        tb.pack(fill="x", padx=8, pady=(8, 8))
        self.price_tb = tb
        bar = tk.Frame(tb, bg=C["panel"], padx=8, pady=8)
        bar.pack(fill="x")
        tk.Frame(tb, bg=C["line"], height=1).pack(fill="x", padx=8)
        bar2 = tk.Frame(tb, bg=C["panel"], padx=8, pady=8)
        bar2.pack(fill="x")
        lab = dict(bg=C["panel"], fg=C["muted"])
        ttk.Button(bar, text="Export CSV", command=self.export).pack(side="right")          # right side first: never squeezed out
        ttk.Button(bar, text="Clear list", command=self.clear, style="Danger.TButton").pack(side="right", padx=8)
        self.pause_btn = ttk.Button(bar, text="Pause", command=self.toggle_pause, width=8)
        self.pause_btn.pack(side="right")
        ttk.Button(bar2, text="Re-price all", style="Primary.TButton", command=self.reprice_all).pack(side="right")
        self.remove_btn = ttk.Button(bar2, text="✖ Mark removed", command=lambda: self.mark_selected("removed"))
        self.remove_btn.pack(side="right", padx=8)
        self.delete_btn = ttk.Button(bar2, text="🗑 Delete", command=self.remove_selected, style="Danger.TButton")      # 2.0 beta 19
        self.delete_btn.pack(side="right", padx=(0, 8), before=self.remove_btn)
        self.mark_btn = ttk.Button(bar2, text="✔ Mark listed", command=lambda: self.mark_selected("listed"))
        self.mark_btn.pack(side="right")
        self.undo_btn = ttk.Button(bar2, text="↺ Undo", command=self.undo_mark, state="disabled", width=7, style="Quiet.TButton")
        self.undo_btn.pack(side="right", padx=(0, 8))
        self.undo = []                                   # [(record id, previous mark, previous listed-at)] of the last mark
        tk.Label(bar, text="Valuable mod ≥", **lab).pack(side="left", padx=(0, 8))
        self.good_var = tk.StringVar(value=str(SETTINGS["good_div"]))
        sp = ttk.Spinbox(bar, from_=0.05, to=500, increment=0.25, width=6, textvariable=self.good_var,
                         command=self.on_good)
        sp.pack(side="left")
        sp.bind("<Return>", lambda e: self.on_good())
        sp.bind("<FocusOut>", lambda e: self.on_good())
        tk.Label(bar, text="div", **lab).pack(side="left", padx=(4, 0))
        self.pop_var = tk.BooleanVar(value=SETTINGS["popups"])
        self.snd_var = tk.BooleanVar(value=SETTINGS["sound"])
        ttk.Checkbutton(bar, text="Popups", variable=self.pop_var, style="Bar.TCheckbutton", command=self.on_toggles).pack(side="left", padx=(16, 4))
        ttk.Checkbutton(bar, text="Sound", variable=self.snd_var, style="Bar.TCheckbutton", command=self.on_toggles).pack(side="left", padx=4)
        # 2.31.0: "Ctrl+Alt+C only" left the toolbar - Settings > Hotkeys > "Also add items copied another way"
        self.hk_var = tk.BooleanVar(value=SETTINGS.get("hotkey_only", True))
        self.copy_var = tk.BooleanVar(value=SETTINGS["auto_copy"])
        ttk.Checkbutton(bar, text="Copy name on click", variable=self.copy_var, style="Bar.TCheckbutton",
                        command=self.on_toggles).pack(side="left", padx=4)

        tk.Label(bar2, text="Listings", **lab).pack(side="left", padx=(0, 8))
        self.status_var = tk.StringVar(value=SETTINGS["status"])
        sbox = ttk.Combobox(bar2, textvariable=self.status_var, values=[l for l, _ in STATUS_OPTIONS],
                            state="readonly", width=22)
        sbox.pack(side="left")
        sbox.bind("<<ComboboxSelected>>", self.on_listing_rules)
        tk.Label(bar2, text="Listed within", **lab).pack(side="left", padx=(16, 8))
        self.age_var = tk.StringVar(value=SETTINGS["age"])
        abox = ttk.Combobox(bar2, textvariable=self.age_var, values=[a[0] for a in AGE_OPTIONS],
                            state="readonly", width=10)
        abox.pack(side="left")
        abox.bind("<<ComboboxSelected>>", self.on_listing_rules)
        self.view_var = tk.StringVar(value=SETTINGS["view"])    # its box sits above the list (2.0 beta 3)
        for cb in (sbox, abox):                                  # after picking from a dropdown, hand the keyboard back
            cb.bind("<<ComboboxSelected>>", lambda e: self.root.after(20, self.root.focus_set), add="+")
        self.build_tab_reader(tb)                                # 2.8.0: Add items from Ctrl+Alt+C | Stash tab

        # ---- the key bar, at the bottom of this window (claims its space first)
        kbf = tk.Frame(body, bg=C["panel"])
        kbf.pack(fill="x", side="bottom")
        self.build_keybar(kbf)
        self.banner = tk.Label(body, text="", anchor="w", padx=16, pady=8, font=("Segoe UI", 10, "bold"), justify="left")

        # ---- the list filters (2.0 beta 3), then the list and the side panel
        items_tab = tk.Frame(body, bg=C["panel"])
        items_tab.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self.checks_area = items_tab                       # cards and banners go just above it
        frow = tk.Frame(items_tab, bg=C["panel"], padx=4, pady=8)
        frow.pack(fill="x")
        flab = dict(bg=C["panel"], fg=C["muted"])
        tk.Label(frow, text="Show", **flab).pack(side="left", padx=(0, 8))
        vbox = ttk.Combobox(frow, textvariable=self.view_var, values=VIEWS, state="readonly", width=12)
        vbox.pack(side="left")
        vbox.bind("<<ComboboxSelected>>", self.on_view)
        self.cat_var, self.rar_var, self.type_var = tk.StringVar(value=self.ALL_CATS), tk.StringVar(value="All"), tk.StringVar(value="All")
        self.cat_box = ttk.Combobox(frow, textvariable=self.cat_var, state="readonly", width=15)
        self.rar_box = ttk.Combobox(frow, textvariable=self.rar_var, state="readonly", width=8)
        self.type_box = ttk.Combobox(frow, textvariable=self.type_var, state="readonly", width=15)
        for label, box, pad in (("Category", self.cat_box, 18), ("Rarity", self.rar_box, 12), ("Type", self.type_box, 12)):
            tk.Label(frow, text=label, **flab).pack(side="left", padx=(pad, 6))
            box.pack(side="left")
        self.cat_box.bind("<<ComboboxSelected>>", lambda e: self.on_cat(changed="cat"))
        self.rar_box.bind("<<ComboboxSelected>>", lambda e: self.on_cat(changed="rar"))
        self.type_box.bind("<<ComboboxSelected>>", lambda e: self.on_cat(changed="type"))
        for cb in (vbox, self.cat_box, self.rar_box, self.type_box):
            cb.bind("<<ComboboxSelected>>", lambda e: self.root.after(20, self.root.focus_set), add="+")
        # 2.26.4: was "Show all" - it clears Category / Rarity / Type, and only lights up when one is set
        self.clear_btn = ttk.Button(frow, text="✕ Clear filters", command=self.cat_reset, state="disabled")
        self.clear_btn.pack(side="left", padx=(12, 0))
        ttk.Button(frow, text="↕ Order added", command=self.sort_added).pack(side="left", padx=(8, 0))   # 2.0 beta 22
        from .pricefmt import PRICE_UNITS                    # 2.16.0: show every price in the currency you pick
        self.unit_var = tk.StringVar(value=dict(PRICE_UNITS).get(SETTINGS.get("price_unit") or "auto", PRICE_UNITS[0][1]))
        ubox = ttk.Combobox(frow, textvariable=self.unit_var, values=[t for _k, t in PRICE_UNITS], state="readonly",
                            width=20)
        ubox.pack(side="right")
        ubox.bind("<<ComboboxSelected>>", lambda e: (self.on_price_unit(), self.root.after(20, self.root.focus_set)))
        tk.Label(frow, text="Prices in", **flab).pack(side="right", padx=(12, 8))
        self.cat_count = tk.Label(frow, text="", **flab)
        self.cat_count.pack(side="right")
        self.pane = ttk.PanedWindow(items_tab, orient="horizontal")        # drag the divider to resize
        self.pane.pack(fill="both", expand=True)
        left = tk.Frame(self.pane, bg=C["panel"])
        self.pane.add(left, weight=1)
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
        self.tree.bind("<Double-1>", lambda e: self.open_trade())
        self.empty_lbl = tk.Label(left, bg=C["panel"], fg=C["muted"], font=("Segoe UI", 12), justify="center",
                                  text=self.empty_text)
        self.empty_lbl.place(relx=0.5, rely=0.45, anchor="center")

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
        dsb = ttk.Scrollbar(outer, orient="vertical")
        dsb.pack(side="right", fill="y")
        self.dcanvas = tk.Canvas(outer, bg=C["panel2"], highlightthickness=0, yscrollcommand=dsb.set)
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
        self.mb_nb = SegBook(book_tab)                         # real buttons, not notebook tabs (2.0 beta 7)
        self.mb_nb.pack(fill="both", expand=True, padx=8, pady=8)
        memory_tab = tk.Frame(self.mb_nb, bg=C["panel"])
        rules_tab = tk.Frame(self.mb_nb, bg=C["panel"])
        jrules_tab = tk.Frame(self.mb_nb, bg=C["panel"])
        wrules_tab = tk.Frame(self.mb_nb, bg=C["panel"])                # 2.6.0
        rrules_tab = tk.Frame(self.mb_nb, bg=C["panel"])
        self.mb_nb.add(memory_tab, text="What the app learned")
        self.mb_nb.add(rules_tab, text="Tablet rules")
        self.mb_nb.add(jrules_tab, text="Jewel rules")
        self.mb_nb.add(wrules_tab, text="Waystone rules")
        self.mb_nb.add(rrules_tab, text="Relic rules")
        self.mb_nb.bind("<<NotebookTabChanged>>", lambda e: (self.refresh_rules(), self.refresh_memory()))
        mbar = tk.Frame(memory_tab, bg=C["panel"], padx=8, pady=8)
        mbar.pack(fill="x")
        tk.Label(mbar, text="Show", bg=C["panel"], fg=C["muted"]).pack(side="left", padx=(0, 8))
        self.MEM_VIEWS = ["Mod priority", "Single mods", "Mod combinations", "Old mod book"]
        self.mem_view = tk.StringVar(value=self.MEM_VIEWS[0])
        mv = ttk.Combobox(mbar, textvariable=self.mem_view, values=self.MEM_VIEWS, state="readonly", width=18)
        mv.pack(side="left")
        mv.bind("<<ComboboxSelected>>", lambda e: (self.refresh_memory(True), self.root.after(20, self.root.focus_set)))
        tk.Label(mbar, text="Filter", bg=C["panel"], fg=C["muted"]).pack(side="left", padx=(16, 8))
        self.mem_filter = tk.StringVar()
        self.mem_filter.trace_add("write", lambda *a: self.refresh_memory(True))
        ttk.Entry(mbar, textvariable=self.mem_filter, width=24).pack(side="left")
        ttk.Button(mbar, text="Refresh", command=lambda: self.refresh_memory(True)).pack(side="left", padx=8)
        self.mem_info = tk.Label(memory_tab, bg=C["panel"], fg=C["muted"], justify="left", anchor="w", padx=12)
        self.mem_info.pack(fill="x")
        self.mem_frame = tk.Frame(memory_tab, bg=C["panel"])
        self.mem_frame.pack(fill="both", expand=True)
        self.mem_tv = None
        self.mem_empty = tk.Label(memory_tab, bg=C["panel"], fg=C["muted"], font=("Segoe UI", 10), justify="center", wraplength=640)
        self.build_rules_page(rules_tab, "tablet")
        self.build_rules_page(jrules_tab, "jewel")
        self.build_rules_page(wrules_tab, "waystone")
        self.build_rules_page(rrules_tab, "relic")

    # ---------------- the Settings window (League and Pace moved here from the old header bars)
    def build_settings(self, body):
        """2.0 beta 21: tabs - General, Appearance (the look of everything), Hotkeys, Advanced (the parts most people
        never need: the Mod book, Under the hood, the data folder)."""
        P1, P2 = C["panel"], C["panel2"]
        from .style import ScrollArea
        self.set_nb = SegBook(body)
        self.set_nb.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        pages = {}
        for name in ("General", "Appearance", "Hotkeys", "Chat commands", "Advanced", "About"):
            sa = ScrollArea(self.set_nb, P1)
            wrap = tk.Frame(sa.inner, bg=P1, padx=8, pady=4)
            wrap.pack(fill="both", expand=True)
            self.set_nb.add(sa, text=name)
            pages[name] = (sa, wrap)
        self.settings_scroll = pages["General"][0]                # 2.0 beta 14: scrolls when the window is small
        self.settings_pages = pages

        def section(page, title, note=""):
            f = tk.Frame(pages[page][1], bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
            f.pack(fill="x", pady=(0, 8))
            tk.Label(f, text=title, bg=P2, fg=C["accent"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
            if note:
                tk.Label(f, text=note, bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left",
                         wraplength=600).pack(fill="x", pady=(2, 8))
            row = tk.Frame(f, bg=P2)
            row.pack(fill="x")
            return row

        self.build_about(pages["About"][1])                      # 2.10.0
        self.build_chat_window(pages["Chat commands"][1])        # 2.27.0: was its own Utilities window
        # ======== General
        row = section("General", "League and search pace", "The league is used everywhere: Price checks, Wealth and "
                                                           "the session tracker. Pace = how fast the trade site is "
                                                           "searched (slower = fewer waits from its limits).")
        tk.Label(row, text="League", bg=P2, fg=C["text"]).pack(side="left", padx=(0, 8))
        self.league_box = ttk.Combobox(row, textvariable=self.league_var, state="readonly", width=24)
        self.league_box.pack(side="left")
        self.league_box.bind("<<ComboboxSelected>>", self.on_league)
        tk.Label(row, text="Pace", bg=P2, fg=C["text"]).pack(side="left", padx=(16, 8))
        pace = ttk.Combobox(row, textvariable=self.pace_var, values=list(PACES), state="readonly", width=10)
        pace.pack(side="left")
        pace.bind("<<ComboboxSelected>>", self.on_pace)
        ttk.Button(row, text="Exchange rates…", command=self.open_rates).pack(side="left", padx=(16, 0))
        for cb in (self.league_box, pace):
            cb.bind("<<ComboboxSelected>>", lambda e: self.root.after(20, self.root.focus_set), add="+")

        # 2.31.0: the community Mod book
        row = section("General", "Community Mod book", "Every player's price checks pool their mod prices, so the stars "
                                                        "and estimates get better for everyone - most of all early in a "
                                                        "league. Once an hour: mods and prices only, no account names or items. "
                                                        "You always get everyone else's prices, sharing or not.")
        self.cm_share_var = tk.BooleanVar(value=bool(SETTINGS.get("share_prices", True)))
        ttk.Checkbutton(row, text="Share my mod prices (anonymous)", variable=self.cm_share_var,
                        command=self.cm_share_changed).pack(side="left")
        row = section("General", "Copy marker", "After Ctrl+Alt+C, a small + shows where your mouse was, so you can "
                                                "see which items you've already copied. It only draws on the screen: "
                                                "nothing is sent to the game.")
        self.mark_var = tk.BooleanVar(value=SETTINGS.get("copy_marker", True))
        ttk.Checkbutton(row, text="Mark where I pressed Ctrl+Alt+C", variable=self.mark_var,
                        command=self.on_copy_marker).pack(side="left")
        tk.Label(row, text="for", bg=P2, fg=C["text"]).pack(side="left", padx=(16, 4))
        self.mark_secs = tk.StringVar(value=str(SETTINGS.get("copy_marker_secs", 10)))
        sp = ttk.Spinbox(row, from_=1, to=600, textvariable=self.mark_secs, width=5, command=self.on_copy_marker)
        sp.pack(side="left")
        sp.bind("<FocusOut>", lambda e: self.on_copy_marker())
        tk.Label(row, text="seconds", bg=P2, fg=C["text"]).pack(side="left", padx=(4, 16))
        self.mark_hold = tk.BooleanVar(value=bool(SETTINGS.get("copy_marker_hold")))
        ttk.Checkbutton(row, text="Keep them until I double-tap Esc", variable=self.mark_hold,
                        command=self.on_copy_marker).pack(side="left")
        from .copymark import COLOURS                       # 2.25.0: the +'s colour
        tk.Label(row, text="Colour", bg=P2, fg=C["text"]).pack(side="left", padx=(16, 4))
        self.mark_colour = tk.StringVar(value=SETTINGS.get("copy_marker_colour", "Gold"))
        mc = ttk.Combobox(row, textvariable=self.mark_colour, values=list(COLOURS), state="readonly", width=9)
        mc.pack(side="left")
        mc.bind("<<ComboboxSelected>>", lambda e: self.on_copy_marker(preview=True))

        row = section("General", "Window", "Always on top keeps StashOfExile2 in front of the game (and brings it "
                                           "back if something minimises it). The 📌 on the taskbar does the same. "
                                           "Notes and the Session timer are shown over the game: normally only while "
                                           "the game is the window in front.")
        self.top_btn = ttk.Checkbutton(row, text="Always on top", variable=self.top_var, command=self.on_top_toggle)
        self.top_btn.pack(side="left")
        self.game_only_var = tk.BooleanVar(value=bool(SETTINGS.get("overlay_game_only", True)))
        ttk.Checkbutton(row, text="Notes and timer only while Path of Exile 2 is in front", variable=self.game_only_var,
                        command=self.on_game_only).pack(side="left", padx=(16, 0))

        row = section("General", "Labs (experimental)", "Features still being tried out: Wealth, Game search and "
                                                         "Market Insights. They work, but may change a lot or have "
                                                         "rough edges. When Labs is off they are hidden.")
        self.labs_var = tk.BooleanVar(value=bool(SETTINGS.get("labs")))
        ttk.Checkbutton(row, text="Show Labs features (marked BETA)", variable=self.labs_var,
                        command=self.on_labs).pack(side="left")

        row = section("General", "Updates", f"You have version {pretty_version()}. Updates come from GitHub "
                                            "(tiwomm/StashOfExile2); your settings and data are always kept.")
        ttk.Button(row, text="Check for updates", command=self.check_updates).pack(side="left")
        row2 = tk.Frame(row.master, bg=P2)
        row2.pack(fill="x", pady=(8, 0))
        self.auto_check_var = tk.BooleanVar(value=bool(SETTINGS.get("auto_check_updates")))
        self.auto_update_var = tk.BooleanVar(value=bool(SETTINGS.get("auto_update")))
        ttk.Checkbutton(row2, text="Check for updates when the app starts (tells you, asks before installing)",
                        variable=self.auto_check_var, command=lambda: self.on_update_options("check")).pack(anchor="w")
        ttk.Checkbutton(row2, text="Install updates automatically when the app starts (no questions; it restarts itself)",
                        variable=self.auto_update_var, command=lambda: self.on_update_options("update")).pack(anchor="w")

        # ======== Appearance
        row = section("Appearance", "Launcher", "How you open things: the dock on the left, icons on the desktop, or "
                                                "both. One of them is always there. With the dock hidden, Toolkit "
                                                "moves to the taskbar.")
        self.launcher_var = tk.StringVar(value=dict(self.shell.LAUNCHERS).get(self.shell.cfg.get("launcher", "dock")))
        lb = ttk.Combobox(row, textvariable=self.launcher_var, values=[t for _k, t in self.shell.LAUNCHERS],
                          state="readonly", width=22)
        lb.pack(side="left")
        lb.bind("<<ComboboxSelected>>", lambda e: self.on_launcher())
        self.icons_var = tk.BooleanVar(value=bool(self.shell.cfg.get("desktop_icons")))     # (older code / tests)

        row = section("Appearance", "Wallpaper", "Any picture for the desktop background (it is scaled to fill).")
        ttk.Button(row, text="Choose wallpaper…", command=self.pick_wallpaper).pack(side="left")
        ttk.Button(row, text="Default", command=lambda: self.shell.set_wallpaper(None), style="Quiet.TButton").pack(side="left", padx=8)

        from .shell import windows_24h
        row = section("Appearance", "Clock", "The clock at the bottom right shows your PC's own time. It starts out "
                                             "the way your Windows clock is set. The Session timer can show it "
                                             "too, so you see the time in game.")
        fmt = SETTINGS.get("clock_format", "auto")
        if fmt not in ("12", "24"):
            fmt = "24" if windows_24h() else "12"
        self.clock_var = tk.StringVar(value={"12": "12-hour (3:45 PM)", "24": "24-hour (15:45)"}[fmt])
        cb = ttk.Combobox(row, textvariable=self.clock_var, state="readonly", width=20,
                          values=["12-hour (3:45 PM)", "24-hour (15:45)"])
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.on_clock())
        self.ingame_clock_var = tk.BooleanVar(value=bool(self.tracker_cfg().get("clock", True)))     # 2.39.0
        ttk.Checkbutton(row, text="Also show it on the Session timer (in game)", variable=self.ingame_clock_var,
                        command=self.on_ingame_clock).pack(side="left", padx=(16, 0))

        # 2.44.0: the look of the windows over the game lives in Overlays › Look (with the things it changes)
        row = section("Appearance", "Over the game", "The Session timer, the Mechanic Helper bar and Notes have their "
                                                     "own look and opacity, in Overlays › Look.")
        ttk.Button(row, text="Open Overlays › Look", command=lambda: self.ovh_open("Look")).pack(side="left")

        from .style import ACCENTS, THEMES
        row = section("Appearance", "Look of the app", "Colours and text size for every window. Changes take effect "
                                                       "when the app restarts (Restart now does it for you; your "
                                                       "windows and lists are kept).")
        grid = tk.Frame(row, bg=P2)
        grid.pack(fill="x")
        self.look_vars = {}
        for r, (key, label, options, default) in enumerate((
                ("theme", "Theme", {k: v[0] for k, v in THEMES.items()}, "midnight"),
                ("accent", "Accent colour", {k: v[0] for k, v in ACCENTS.items()}, "orange"),
                ("ui_scale", "Text size", {90: "Smaller (90%)", 100: "Normal (100%)", 115: "Bigger (115%)",
                                           130: "Biggest (130%)"}, 100))):
            tk.Label(grid, text=label, bg=P2, fg=C["text"]).grid(row=r, column=0, sticky="w", padx=(0, 8), pady=4)
            cur = SETTINGS.get(key, default)
            v = tk.StringVar(value=options.get(cur, options[default]))
            cb = ttk.Combobox(grid, textvariable=v, values=list(options.values()), state="readonly", width=26)
            cb.grid(row=r, column=1, sticky="w", pady=4)
            cb.bind("<<ComboboxSelected>>", lambda e, k=key, o=options, vv=v: self.on_look(k, o, vv))
            self.look_vars[key] = v
        if THEMES:
            sw = tk.Frame(grid, bg=P2)
            sw.grid(row=0, column=2, rowspan=2, sticky="w", padx=(16, 0))
            self.look_swatch = tk.Canvas(sw, width=150, height=40, bg=P2, highlightthickness=0)
            self.look_swatch.pack()
            self.draw_look_swatch()
        brow = tk.Frame(row, bg=P2)
        brow.pack(fill="x", pady=(8, 0))
        self.look_restart = ttk.Button(brow, text="Restart now", style="Primary.TButton", command=self.restart_app,
                                       state="disabled")
        self.look_restart.pack(side="left")
        self.look_msg = tk.Label(brow, text="", bg=P2, fg=C["muted"])
        self.look_msg.pack(side="left", padx=8)
        self.splash_var = tk.BooleanVar(value=bool(SETTINGS.get("splash", True)))
        ttk.Checkbutton(row, text="Show the start-up screen", variable=self.splash_var,
                        command=lambda: (SETTINGS.__setitem__("splash", bool(self.splash_var.get())),
                                         save_json("settings.json", SETTINGS))).pack(anchor="w", pady=(8, 0))

        # ======== Hotkeys
        row = section("Hotkeys", "Hotkeys", "Every key the app listens for, in one place. Click a box and press the "
                                            "key you want (with Ctrl / Alt / Shift if you like, or a mouse button); "
                                            "it's saved straight away. Esc keeps the old key, Backspace or "
                                            "right-click clears it. Two things on the same key show in red.")
        self.hk_frame = row
        self.hk_vars = {}
        row2 = tk.Frame(row.master, bg=P2)
        row2.pack(fill="x", pady=(8, 0))
        self.hk_msg = tk.Label(row2, text="", bg=P2, fg=C["muted"], anchor="w", justify="left")
        self.hk_msg.pack(side="left", padx=8)
        self.fill_hotkeys()
        row = section("Hotkeys", "Other ways of copying", "Price checks only adds items you copy with your own "
                                                          "Ctrl+Alt+C, so other tools (like Sidekick's Ctrl+D) don't "
                                                          "fill your list. Tick this to also add items copied any other "
                                                          "way, e.g. a plain Ctrl+C.")
        self.any_copy_var = tk.BooleanVar(value=not SETTINGS.get("hotkey_only", True))
        ttk.Checkbutton(row, text="Also add items copied another way", variable=self.any_copy_var,
                        command=self.on_any_copy).pack(side="left")

        # ======== Advanced
        row = section("Advanced", "Mod book", "What the price checker has learned about each mod from real "
                                              "listings, and the rules for which tablet / jewel mods count (★ worth "
                                              "searching on, ☑ normal, ignored). It works on its own; open it only "
                                              "if you want to see or change the rules. Regex uses the same ratings.")
        ttk.Button(row, text="Open the Mod book", command=lambda: self.shell.open("modbook")).pack(side="left")
        row = section("Advanced", "Under the hood", "How the price checker reads an item: its base, which bases it "
                                                    "is compared with, and which trade-site search each mod becomes.")
        ttk.Button(row, text="Open Under the hood", command=lambda: self.shell.open("library")).pack(side="left")
        row = section("Advanced", "Problem report", "Something priced badly or went wrong? This makes one .zip with "
                                                    "your recent price checks (the copied item texts and what the app "
                                                    "did with them) and the app's log files - no account name, no "
                                                    "Wealth data. Send it along with what you saw.")
        ttk.Button(row, text="Make a problem report…", command=self.problem_report).pack(side="left")
        row = section("Advanced", "Recent messages", "The last 20 messages the app showed you (they go away "
                                                     "by themselves, so they're kept here). Hover one to keep it up.")
        self.build_toast_log(row)
        row = section("Advanced", "Your data", "Settings, price-check lists, the Mod book, Wealth and sessions are "
                                               "kept here, shared by every version of the app.")
        tk.Label(row, text=str(DATA_DIR), bg=P2, fg=C["text"], font=(MONO, 9)).pack(side="left")
        ttk.Button(row, text="Open folder", command=lambda: self.open_path(DATA_DIR), style="Quiet.TButton").pack(side="left", padx=8)

    def build_toast_log(self, parent):
        """2.35.0: Settings > Advanced > Recent messages - the toast history, newest first."""
        from .toasts import KINDS
        P2 = C["panel2"]
        box = tk.Frame(parent, bg=P2)
        box.pack(fill="x", expand=True)
        tv = ttk.Treeview(box, columns=("when", "kind", "msg"), show="headings", height=6, selectmode="browse")
        for cid, title, w, st in (("when", "When", 90, False), ("kind", "", 34, False), ("msg", "Message", 520, True)):
            tv.heading(cid, text=title)
            tv.column(cid, width=w, minwidth=30, stretch=st, anchor="center" if cid == "kind" else "w")
        tv.pack(side="left", fill="x", expand=True)
        btns = tk.Frame(box, bg=P2)
        btns.pack(side="left", anchor="n", padx=(8, 0))
        self.toast_tv = tv

        def fill():
            if not tv.winfo_exists():
                return
            tv.delete(*tv.get_children())
            for n, h in enumerate(reversed(self.toasts.history)):
                msg = " - ".join(x for x in (h.get("title"), " ".join(str(h.get("text", "")).split())) if x)
                tv.insert("", "end", iid=str(n), values=(time.strftime("%H:%M:%S", time.localtime(h.get("ts", 0))),
                                                        KINDS.get(h.get("kind"), KINDS["info"])[0], msg))
            if not tv.get_children():
                tv.insert("", "end", values=("", "", "No messages yet."))

        def clear():
            self.toasts.history.clear()
            save_json("toasts.json", [])
            fill()
        ttk.Button(btns, text="Clear", command=clear, style="Quiet.TButton").pack(fill="x")
        self.toasts.on_history = fill
        fill()

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

    def problem_report(self):
        from .report import make_report
        path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("Zip", "*.zip")],
                                            initialfile=f"StashOfExile2_report_{time.strftime('%Y%m%d_%H%M')}.zip")
        if not path:
            return
        try:
            n = make_report(path, self.records)
        except Exception as e:
            return self._say(f"Couldn't make the report: {e}", 10)
        self._say(f"Report saved ({n} recent price checks): {path}", 12)
        self.open_path(os.path.dirname(path))

    def open_path(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(path)                           # noqa: the folder in Explorer
            else:
                webbrowser.open("file://" + str(path))
        except Exception as e:
            self._say(f"Couldn't open {path}: {e}", 8)

    def on_look(self, key, options, var):
        value = next((k for k, t in options.items() if t == var.get()), None)
        if value is None:
            return
        SETTINGS[key] = value
        save_json("settings.json", SETTINGS)
        self.draw_look_swatch()
        self.look_restart.config(state="normal")
        self.look_msg.config(text="Saved - restart to see it everywhere.", fg=C["good"])

    def draw_look_swatch(self):
        """A little preview of the chosen theme and accent (drawn without the running theme)."""
        from .style import ACCENTS, THEMES
        import colorsys
        c = getattr(self, "look_swatch", None)
        if c is None:
            return
        _, hue, sat = THEMES.get(SETTINGS.get("theme", "midnight"), THEMES["midnight"])

        def tone(col):
            if hue is None:
                return col
            r, g, b = (int(col[i:i + 2], 16) / 255 for i in (1, 3, 5))
            h, l_, s = colorsys.rgb_to_hls(r, g, b)
            r, g, b = colorsys.hls_to_rgb(hue / 360, l_, min(1, s * sat))
            return "#%02x%02x%02x" % tuple(round(v * 255) for v in (r, g, b))
        acc = ACCENTS.get(SETTINGS.get("accent", "orange"), ACCENTS["orange"])[1]
        c.delete("all")
        for i, col in enumerate(("#090e17", "#0e1522", "#131c2e", "#2b3d5f", "#5b77ad")):
            c.tk.call(c._w, "create", "rectangle", i * 24, 0, i * 24 + 22, 40, "-fill", tone(col), "-outline", "")
        c.tk.call(c._w, "create", "rectangle", 122, 0, 150, 40, "-fill", acc, "-outline", "")

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

    def on_launcher(self):
        mode = next((k for k, t in self.shell.LAUNCHERS if t == self.launcher_var.get()), "dock")
        self.shell.set_launcher(mode)
        self.icons_var.set(self.shell.cfg["desktop_icons"])
        save_json("settings.json", SETTINGS)

    def on_clock(self):
        from . import shell as _shell
        fmt = {"12-hour (3:45 PM)": "12", "24-hour (15:45)": "24"}.get(self.clock_var.get(), "auto")
        SETTINGS["clock_format"] = fmt
        _shell.CLOCK["format"] = fmt
        save_json("settings.json", SETTINGS)
        if self.shell.clock is not None:
            self.shell.clock.config(text=_shell.clock_text())
        if getattr(self, "tk_overlay", None) is not None:              # 2.39.0: the timer's clock follows it too
            self.tracker_overlay_draw(self.tracker_numbers())

    # ---- 2.43.0: the look of the windows over the game (2.44.0: Overlays › Look)
    def build_overlay_look(self, parent):
        P2 = C["panel2"]

        def section(_page, title, note=""):
            f = tk.Frame(parent, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
            f.pack(fill="x", padx=8, pady=(8, 0))
            tk.Label(f, text=title, bg=P2, fg=C["accent"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
            if note:
                tk.Label(f, text=note, bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left",
                         wraplength=600).pack(fill="x", pady=(2, 8))
            row = tk.Frame(f, bg=P2)
            row.pack(fill="x")
            return row
        from .overlaywin import LOOKS, LOOK
        row = section("Appearance", "Style and opacity", "For the Session timer, the Mechanic Helper bar and Notes. "
                                                         "Move each one by its title bar; its lock keeps it in place. "
                                                         "Lower opacity = see more of the game through it.")
        self.ov_look_var = tk.StringVar(value=LOOKS[LOOK[0]])
        lk = ttk.Combobox(row, textvariable=self.ov_look_var, values=list(LOOKS.values()), state="readonly", width=30)
        lk.pack(side="left")
        lk.bind("<<ComboboxSelected>>", lambda e: self.on_ov_look())
        grid = tk.Frame(row.master, bg=P2)
        grid.pack(fill="x", pady=(8, 0))
        self.ov_op_vars = {}
        for i, (key, label) in enumerate((("session", "Session timer"), ("helper", "Mechanic Helper"),
                                          ("notes", "Notes"))):
            tk.Label(grid, text=label, bg=P2, fg=C["text"]).grid(row=i, column=0, sticky="w", padx=(0, 8), pady=2)
            v = tk.IntVar(value=self.ov_opacity_get(key))
            self.ov_op_vars[key] = v
            ttk.Scale(grid, from_=60, to=255, variable=v, orient="horizontal", length=200,
                      command=lambda _v, k=key: self.on_ov_opacity(k)).grid(row=i, column=1, sticky="w")
        self.rm_tips_var = tk.BooleanVar(value=bool((SETTINGS.get("remnant") or {}).get("tips", True)))
        ttk.Checkbutton(row.master, text="Runeshape tips next to the remnant prices (while a remnant's book is open)",
                        variable=self.rm_tips_var,
                        command=lambda: self.remnant_tips_changed(self.rm_tips_var.get())).pack(anchor="w", pady=(8, 0))

    def ov_opacity_get(self, key):
        t = self.tracker_cfg()
        if key == "session":
            return int(t.get("opacity", 225))
        if key == "helper":
            return int(t.get("hopacity", t.get("opacity", 225)))
        return int(self.overlay.cfg.get("notes_opacity", 215))

    def on_ov_opacity(self, key):
        v = int(float(self.ov_op_vars[key].get()))
        t = self.tracker_cfg()
        if key == "session":
            t["opacity"] = v
            w = getattr(self, "tk_overlay", None)
            if getattr(self, "tk_opacity", None) is not None:
                self.tk_opacity.set(v)
        elif key == "helper":
            t["hopacity"] = v
            w = getattr(self, "tk_helpers", None)
        else:
            self.overlay.cfg["notes_opacity"] = v
            w = getattr(self.overlay, "notes", None)
            if getattr(self, "ov_opacity", None) is not None:
                self.ov_opacity.set(v)
        try:
            if w is not None and w.winfo_exists():
                w.set_opacity(v)
        except Exception:
            pass
        job = getattr(self, "_ov_save_job", None)              # save once the slider stops
        if job:
            self.root.after_cancel(job)
        self._ov_save_job = self.root.after(400, self._ov_save)

    def _ov_save(self):
        self._ov_save_job = None
        self.tracker_save()
        self.overlay.save_settings()

    def on_ov_look(self):
        from . import overlaywin
        key = next((k for k, t in overlaywin.LOOKS.items() if t == self.ov_look_var.get()), "parchment")
        SETTINGS["overlay_look"] = key
        overlaywin.LOOK[0] = key
        save_json("settings.json", SETTINGS)
        if getattr(self, "tk_overlay", None) is not None:
            self.tracker_overlay_build()
        try:
            self.overlay.restyle()
        except Exception:
            self.log_error("restyling Notes")

    def on_ingame_clock(self):
        """2.39.0: the clock + date line on the Session timer, on or off."""
        self.tracker_cfg()["clock"] = bool(self.ingame_clock_var.get())
        self.tracker_save()
        if getattr(self, "tk_overlay", None) is not None:
            self.tracker_overlay_build()

    def on_update_options(self, which="update"):
        if which == "update" and self.auto_update_var.get():     # installing automatically includes checking
            self.auto_check_var.set(True)
        if which == "check" and not self.auto_check_var.get():   # no checking = no installing either
            self.auto_update_var.set(False)
        SETTINGS["auto_check_updates"] = bool(self.auto_check_var.get())
        SETTINGS["auto_update"] = bool(self.auto_update_var.get())
        save_json("settings.json", SETTINGS)
        self._say("Saved: " + ("updates install by themselves when the app starts." if SETTINGS["auto_update"] else
                               "the app looks for updates when it starts." if SETTINGS["auto_check_updates"] else
                               "updates only when you press Check for updates."), 8)

    def on_labs(self):
        on = bool(self.labs_var.get())
        self.shell.set_labs(on)
        if not on and self.w_counting:                 # 2.10.0: the Session tracker isn't a Labs feature any more
            self.wealth_count_cancel()
        self._say("Labs features are " + ("on (marked BETA)." if on else "hidden."), 6)

    def fill_hotkeys(self):
        from .overlay import key_label, parse_key
        f, P2 = self.hk_frame, C["panel2"]
        for w in f.winfo_children():
            w.destroy()
        self.hk_vars = {}
        clash_keys = set()
        seen = {}
        for what, key, where, kid in self.all_hotkeys():
            k = parse_key(key) if key and key != "Ctrl+Alt+C" else None
            if k:
                if k in seen:
                    clash_keys |= {seen[k], what}
                seen.setdefault(k, what)
        for i, (what, key, where, kid) in enumerate(self.all_hotkeys()):
            col = C["red"] if what in clash_keys else C["text"]
            tk.Label(f, text=what, bg=P2, fg=col, anchor="w").grid(row=i, column=0, sticky="w", padx=(0, 12))
            if kid:
                v = tk.StringVar(value=key)
                self.hk_vars[kid] = v
                kc = KeyCapture(f, v, width=16, on_change=lambda t: self.root.after(10, self.save_hotkeys))   # 2.0 beta 16
                kc.grid(row=i, column=1, sticky="w", pady=1)
                if what in clash_keys:
                    kc.config(fg=col)
            else:
                tk.Label(f, text=key_label(key) if key else "-", bg=P2, fg=col, anchor="w", font=(MONO, 9)).grid(
                    row=i, column=1, sticky="w")
            tk.Label(f, text=where if where != "fixed" else "always on - the game's own copy, can't be changed",
                     bg=P2, fg=C["muted"], font=("Segoe UI", 9)).grid(row=i, column=2, sticky="w", padx=(12, 0))
            if kid == "checks:quick_copy_key" and key:              # 2.0 beta 21: a warning and the way back
                i_w = len(self.all_hotkeys()) + 1
                warn = tk.Frame(f, bg="#2a2110", padx=8, pady=8, highlightthickness=1, highlightbackground="#7a6428")
                warn.grid(row=i_w, column=0, columnspan=3, sticky="we", pady=(8, 0))
                tk.Label(warn, text="⚠ One-key copy is experimental. Ctrl+Alt+C is the reliable way to copy items: if "
                                    "copies go missing or keys seem stuck in game, reset it.", bg="#2a2110",
                         fg=C["good"], wraplength=520, justify="left", anchor="w").pack(side="left", fill="x", expand=True)
                ttk.Button(warn, text="Reset to Ctrl+Alt+C only", command=self.reset_quick_copy).pack(side="right", padx=(8, 0))

    def reset_quick_copy(self):
        SETTINGS["quick_copy_key"] = ""
        save_json("settings.json", SETTINGS)
        self.fill_hotkeys()
        self.update_mouse_watch()
        self.hk_msg.config(text="Reset: items are copied with Ctrl+Alt+C only.", fg=C["green"])

    def save_hotkeys(self):
        from .overlay import parse_key
        bad = []
        for kid, v in self.hk_vars.items():
            txt = v.get().strip()
            if txt and not parse_key(txt):
                bad.append(txt)
                continue
            where, key = kid.split(":")
            if where == "checks":
                SETTINGS[key] = txt
                if key == "regex_key" and hasattr(self, "rx_key_var") and self.rx_key_var.get() != txt:
                    self.rx_key_var.set(txt)
            elif where == "remnant":                               # 2.37.0
                self.remnant_cfg()[key] = txt
            elif where == "overlay":
                self.overlay.cfg[key] = txt
                if hasattr(self, "ov_vars") and key in self.ov_vars:
                    self.ov_vars[key].set(txt)
            else:
                self.tracker_cfg()[key] = txt
                if hasattr(self, "tk_key_vars") and key in self.tk_key_vars:
                    self.tk_key_vars[key].set(txt)
        self.overlay.rebind()
        self.overlay.save_settings()
        save_json("settings.json", SETTINGS)
        self.fill_hotkeys()
        clash = self.hotkey_clashes()
        self.hk_msg.config(text=("Not understood: " + ", ".join(bad)) if bad else
                           ("Saved, but: " + "; ".join(clash)) if clash else "Saved.",
                           fg=C["red"] if bad or clash else C["green"])

    def pick_wallpaper(self):
        path = filedialog.askopenfilename(parent=self.root, title="Choose a wallpaper",
                                          filetypes=[("Pictures", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"), ("All files", "*.*")])
        if path:
            self.shell.set_wallpaper(path)

    def on_game_only(self):
        from . import overlaywin
        SETTINGS["overlay_game_only"] = bool(self.game_only_var.get())
        overlaywin.GAME_ONLY[0] = SETTINGS["overlay_game_only"]
        save_json("settings.json", SETTINGS)
        overlaywin.resync()

    def on_desktop_icons(self):
        """(Before 2.0 beta 21 a checkbox; now Appearance > Launcher.)"""
        self.shell.set_launcher("both" if self.icons_var.get() else "dock")
        if hasattr(self, "launcher_var"):
            self.launcher_var.set(dict(self.shell.LAUNCHERS)[self.shell.cfg["launcher"]])
        save_json("settings.json", SETTINGS)

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

    EMPTY_TEXT = ("Hover an item in game and press Ctrl+Alt+C\nIt will show up here and get priced.\n\n"
                  "Made for pricing lots of tablets, jewels and waystones.\n"
                  "Other items get a rough guess - check those yourself.")
    EMPTY_TEXT_TAB = ("Type your tab's price above and press Read tab:\nevery item on it shows up here and gets priced.\n"
                      "(Ctrl+Alt+C in game still adds items one at a time.)")

    @property
    def empty_text(self):
        """2.8.0: the hint for an empty list follows "Add items from"."""
        return self.EMPTY_TEXT_TAB if SETTINGS.get("pctab", {}).get("mode") == "Stash tab" else self.EMPTY_TEXT

    SCOPE_TEXT = ("Price checks is made for pricing lots of simpler items quickly: tablets, jewels and waystones, where "
                  "a few mods or numbers decide the price. Other items (weapons, armour, rings ...) get a price too, "
                  "but treat it as a rough guess: their value depends on combinations this checker can't judge. "
                  "For those, check the price yourself on the trade site (press O on the item) or with your usual "
                  "price-check tool.")

    def explain_scope(self):
        self.info_card(self.SCOPE_TEXT, secs=40)

    # ---------------- updates
    def startup_update_check(self):
        """2.0 beta 7: Settings > Updates. Auto-update installs a newer version without asking; auto-check only
        tells you (a card with Update now). Both stay quiet when you are up to date or GitHub can't be reached."""
        if SETTINGS.get("auto_update"):
            self.check_updates(mode="auto")
        elif SETTINGS.get("auto_check_updates"):
            self.check_updates(mode="silent")

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
            kind, data = latest_release()
            self.ui_q.put(("update", kind, data))
        threading.Thread(target=work, daemon=True).start()

    def _upd_done(self):
        self._upd_busy = False
        self.upd_btn.config(state="normal")

    def ev_update(self, kind, data):
        self._upd_done()
        if kind == "ok" and hasattr(self, "upd_badge"):            # 2.48.0: the taskbar badge follows every check
            self.ev_update_badge(data.get("tag_name"))
        mode = getattr(self, "_upd_mode", "ask")
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
        notes = (data.get("body") or "").strip()
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
        if not SETTINGS.get("share_notice_seen"):
            SETTINGS["share_notice_seen"] = True
            save_json("settings.json", SETTINGS)
            self.app_toast("StashOfExile2 pools mod prices anonymously, so everyone's prices get better - especially "
                           "early in a league. Only mods and prices are sent once an hour: no account names, no items.\n\n"
                           "You can change this any time in Settings > General.", "Community Mod book",
                           actions=[("Don't share", self.cm_opt_out)], secs=60)
        self.root.after(60000, self.cm_tick)

    def cm_opt_out(self):
        SETTINGS["share_prices"] = False
        save_json("settings.json", SETTINGS)
        if hasattr(self, "cm_share_var"):
            self.cm_share_var.set(False)
        self._say("Mod prices won't be shared. You still get everyone else's.", 6)

    def cm_tick(self):
        from . import communitymods as CM
        threading.Thread(target=self._cm_work, daemon=True).start()
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
            pass
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
        SETTINGS["share_prices"] = bool(self.cm_share_var.get())
        SETTINGS["share_notice_seen"] = True
        save_json("settings.json", SETTINGS)

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
                                       ("Escape", self.hk_min, False)):
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

    def on_good(self):
        try:
            SETTINGS["good_div"] = max(0.01, float(self.good_var.get()))
        except ValueError:
            return
        save_json("settings.json", SETTINGS)
        self.refresh_all()

    def on_copy_marker(self, preview=False):
        SETTINGS["copy_marker"] = bool(self.mark_var.get())
        if hasattr(self, "mark_colour"):
            SETTINGS["copy_marker_colour"] = self.mark_colour.get()
        if preview:                                          # show the new colour next to the box for 2 s
            try:
                from .copymark import COLOURS, CopyMarker
                if getattr(self, "copy_marker", None) is None:
                    self.copy_marker = CopyMarker(self.root)
                self.copy_marker.show(self.root.winfo_pointerx() + 30, self.root.winfo_pointery(), secs=2,
                                      colour=COLOURS.get(SETTINGS["copy_marker_colour"], COLOURS["Gold"]))
            except Exception:
                pass
        try:
            SETTINGS["copy_marker_secs"] = max(1, min(600, int(float(self.mark_secs.get()))))
        except (ValueError, AttributeError):
            pass
        if hasattr(self, "mark_hold"):
            SETTINGS["copy_marker_hold"] = bool(self.mark_hold.get())
        save_json("settings.json", SETTINGS)
        if not SETTINGS["copy_marker"] and getattr(self, "copy_marker", None):
            self.copy_marker.clear()

    def on_pace(self, _e=None):
        SETTINGS["pace"] = self.pace_var.get()
        save_json("settings.json", SETTINGS)
        if SETTINGS["pace"] == "Fast":                      # 2.18.0: say what it costs
            self.app_toast("Fast pace searches the trade site much harder. You'll hit its rate limits quickly, and each "
                       "one locks searches for several minutes (sometimes longer). Balanced is safer.",
                       title="⚠  Fast pace: rate limits ahead",
                       actions=[("Back to Balanced", lambda: (self.pace_var.set("Balanced"), self.on_pace()))])

    def toggle_pause(self):
        self.engine.paused = not self.engine.paused
        self.pause_btn.config(text="Resume" if self.engine.paused else "Pause")
        kb = self.keybar
        kb.itemconfigure(self.key_texts["pause"], text="Resume searches" if self.engine.paused else "Pause searches")
        kb.itemconfigure(self.key_state, text="Paused" if self.engine.paused else "Auto-pricing")
        kb.itemconfigure(self.key_dot, fill=C["good"] if self.engine.paused else C["green"])

    # ---------------- rate limit display
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
        if txt:
            self.banner.config(text=txt, bg=bg, fg=fg)
            if not self.banner.winfo_ismapped():
                self.banner.pack(fill="x", padx=16, pady=(0, 8), before=self.checks_area)
        elif self.banner.winfo_ismapped():
            self.banner.pack_forget()
        parts, worst = [], 0
        for cls in ("search", "fetch"):
            h, mx, per = max(LIMITER.usage(cls), key=lambda u: u[0] / u[1])
            worst = max(worst, h / mx)
            parts.append(f"{cls.title()} {h}/{mx} ({per_text(per)})")
        dot = C["red"] if (st["blocked"] > 0 or worst >= 0.8) else C["good"] if worst >= 0.5 else C["green"]
        self.limit_lbl.config(text="●  " + "    ".join(parts) + "   ", fg=dot)

    # ---------------- exchange rates
    def rates_tick(self):
        """Every 30 s: show how fresh the rates are, and fetch new ones (in the background) when they're over an hour old."""
        try:
            lg = SETTINGS.get("league")
            age = RATES.age()
            stale = RATES.league != lg or age is None or age > 3600
            if lg and SETTINGS.get("rates_auto", True) and stale and not self._rates_busy and time.time() - RATES.attempt > 600:
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
        # 2.4.0: three tabs - Rates, Exchange Helper, Arbitrage (exchange_page.py)
        self.rates_view = SegBar(win, ["Rates", "Exchange Helper", "Arbitrage"], command=lambda v: self.rates_show_page(),
                                 size=10, pad=(16, 4))
        self.rates_view.pack(anchor="w", padx=16, pady=(8, 0))
        self.rates_pages = {k: tk.Frame(win, bg=C["panel"]) for k in ("Rates", "Exchange Helper", "Arbitrage")}
        w = self.rates_pages["Rates"]
        w.pack(fill="both", expand=True)
        top = tk.Frame(w, bg=C["panel"], padx=16, pady=8)
        top.pack(fill="x")
        self.rates_status = tk.Label(top, text="", bg=C["panel"], fg=C["text"], anchor="w", justify="left", wraplength=360)
        self.rates_status.pack(side="left", fill="x", expand=True)
        ttk.Button(top, text="Refresh now", style="Primary.TButton", command=self.refresh_rates_now).pack(side="right")
        self.rates_auto_var = tk.BooleanVar(value=SETTINGS.get("rates_auto", True))
        ttk.Checkbutton(w, text="Check for new rates every hour", variable=self.rates_auto_var, style="Bar.TCheckbutton",
                        command=self.on_rates_auto).pack(anchor="w", padx=16)
        conv = tk.Frame(w, bg=C["panel2"], padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
        conv.pack(fill="x", padx=16, pady=8)
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
        # ---- 2.2.0: what to post on the in-game Currency Exchange (2.4.0: its own tab, "Exchange Helper")
        hp = self.rates_pages["Exchange Helper"]
        ex = tk.Frame(hp, bg=C["panel2"], padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
        ex.pack(fill="x", padx=16, pady=8)
        tk.Label(ex, text="Exchange Helper", bg=C["panel2"], fg=C["accent"], font=("Segoe UI", 10, "bold"),
                 anchor="w").pack(fill="x")
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
        cols = [("cur", "Currency", 200, "w"), ("worth", "Worth (divines)", 120, "e"), ("per", "1 divine buys", 120, "e"),
                ("vol", "Traded (div)", 110, "e")]
        tk.Label(w, text="Rates come from poe.ninja's public exchange overview (they refresh about hourly) and are approximate. "
                         "Listings priced in a currency not in this list are left out of the price and flagged.",
                 bg=C["panel"], fg=C["muted"], wraplength=600, justify="left", padx=16, pady=8).pack(side="bottom", fill="x")
        tv = ttk.Treeview(w, columns=[c[0] for c in cols], show="headings")
        for cid, title, width, anchor in cols:
            tv.heading(cid, text=title)
            tv.column(cid, width=width, anchor=anchor, stretch=(cid == "cur"))
        sb = ttk.Scrollbar(w, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0, 8))
        tv.pack(fill="both", expand=True, padx=(16, 0))
        tv.tag_configure("odd", background=C["odd"])
        tv.tag_configure("thin", foreground=C["muted"])
        self.rates_tv = tv
        self.list_register("rates", tv)
        self.build_arbitrage(self.rates_pages["Arbitrage"])
        self.draw_rates()

    def rates_show_page(self):
        pick = self.rates_view.get()
        for k, f in self.rates_pages.items():
            if k == pick:
                f.pack(fill="both", expand=True)
            else:
                f.pack_forget()
        if pick == "Arbitrage":
            self.arb_draw()

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
        for i, (cur, v) in enumerate(rows[:120]):
            vol = RATES.vol.get(cur, 0)
            tv.insert("", "end", values=(names.get(cur) or cur, f"{v:.4g}", (f"{1 / v:,.0f}" if 1 / v >= 10 else f"{1 / v:.2g}"), f"{vol:,.0f}"),
                      tags=("thin",) if vol < 5 else (("odd",) if i % 2 else ()))

    def ex_currencies(self):
        """[(display name, currency id)] most traded first, Divine Orb on top."""
        known = {"exalted": "Exalted Orb", "chaos": "Chaos Orb", "annul": "Orb of Annulment", "vaal": "Vaal Orb",
                 "regal": "Regal Orb", "alch": "Orb of Alchemy", "gcp": "Gemcutter's Prism", "mirror": "Mirror of Kalandra",
                 "greater-exalted-orb": "Greater Exalted Orb", "perfect-exalted-orb": "Perfect Exalted Orb",
                 "hinekoras-lock": "Hinekora's Lock", "chance": "Orb of Chance", "transmute": "Orb of Transmutation",
                 "aug": "Orb of Augmentation", "artificers": "Artificer's Orb", "jewellers": "Jeweller's Orb"}
        names = ((WPRICES.parts.get("Currency") or {}).get("names") or {}) if WPRICES.parts else {}
        ids = sorted((c for c, v in RATES.table.items() if v), key=lambda c: -(RATES.vol.get(c, 0)))
        first = [c for c in ("exalted", "chaos") if RATES.table.get(c)]       # the usual ones always on top
        out = [("Divine Orb", "divine")]
        for c in first + [c for c in ids if c not in first][:40]:
            if c != "divine":
                out.append((names.get(c) or known.get(c) or c.replace("-", " ").title(), c))
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
                cv = tk.Canvas(row, width=160, height=8, bg=C["line"], highlightthickness=0)
                cv.pack(side="left")
                ratio = min(1.0, h / mx)
                cv.create_rectangle(0, 0, max(2, int(160 * ratio)), 8, outline="",
                                    fill=C["red"] if ratio >= 0.8 else C["good"] if ratio >= 0.5 else C["green"])
        st = LIMITER.state()
        note = "Counts include requests from other tools on the same account or IP (e.g. Sidekick)."
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
        """Write an unexpected error to error_log.txt and say so in the status line - never let it stop the app."""
        try:
            tb = traceback.format_exc()
            sig = tb.strip().splitlines()[-1] if tb.strip() else where
            if time.time() - self._err_seen.get(sig, 0) > 30:          # don't repeat the same error every 100 ms
                self._err_seen[sig] = time.time()
                with open(P("error_log.txt"), "a", encoding="utf-8") as f:
                    f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')}  v{APP_VERSION}  ({where})\n{tb}\n")
                self.status_text = f"Something went wrong ({where}) - details are in error_log.txt"
                self.status_until = time.time() + 20
        except Exception:
            pass

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
                            if self.wealth_takes(text):          # 2.0 beta 7: a copied stack, counted on Wealth
                                self.wealth_clip(text)
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
        self._clip_ignore = {t: u for t, u in getattr(self, "_clip_ignore", {}).items() if u > time.time()}
        self._clip_ignore[text] = time.time() + secs

    def _clip_ignored(self, text):
        return getattr(self, "_clip_ignore", {}).get(text, 0) > time.time()

    def gate_ok(self, text):
        """True if this copy may become a row: it must come from YOUR Ctrl+Alt+C (not Sidekick's Ctrl+D)."""
        if text == self.own_clip or not SETTINGS.get("hotkey_only", True) or not self.keys.active:
            return True
        if self.keys.combo_recent():
            return True
        if text.lstrip().startswith("Item Class:"):
            self.status_text = ("Ignored an item copy that wasn't made with your Ctrl+Alt+C (Sidekick?). "
                                "Wrong? Settings > Hotkeys > \"Also add items copied another way\"")
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
            from .copymark import COLOURS
            self.copy_marker.show(x, y, secs=None if hold else secs,
                                  colour=COLOURS.get(SETTINGS.get("copy_marker_colour"), COLOURS["Gold"]))
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
        if text.lstrip().startswith("Item Class:"):               # 2.45.0: the Farm Ledger's loot box / setup takes it
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
            pass
        if g.get("stack") is not None and parse_stack(text):      # 2.0 beta 7: one click puts it on Wealth
            name, qty, _c = parse_stack(text)
            msg = (f"{name} x{qty:,} is a stack: stacks are counted on the Wealth window, not price-checked. "
                   "Tip: with the Wealth window in front (or while counting), a plain Ctrl+C adds stacks there.")
            self.status_text, self.status_until = msg, time.time() + 15
            if SETTINGS.get("labs"):
                self.info_card(msg, [("Add it to Wealth", lambda: (self.shell.open("wealth"), self.wealth_clip(text)))])
            else:
                self.info_card(f"{name} x{qty:,} is a stack: currency isn't price-checked. (Counting it is part of "
                               "Wealth, a Labs feature: Settings > Labs.)")
            return
        if g.get("stack") is not None:
            why = "stackable items are counted on the Wealth window, not price-checked here"
        elif g.get("rarity") == "Normal" and g.get("class") in ("tablet", "jewel", "waystone"):
            why = "a normal (white) one has no mods to price"
        elif g.get("class") in ("tablet", "jewel") and g.get("rarity") in ("Magic", "Rare"):
            why = ("its name line wasn't recognised (the copied text is saved in unpriced_items.txt in the data "
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
        warning / error (guessed from the old colour or the text when not given). Returns the toast's window."""
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
                pass
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
                pass
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
                pass

    def dup_answer(self, add):
        text, item, rec, n = self.dup_pending.pop(0)
        try:
            self.dup_win.destroy()
        except Exception:
            pass
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
        self.records[rid] = {"id": rid, "item": item, "state": "queued", "label": "", "total": 0,
                             "prices": [], "est": None, "qid": None, "time": time.time(), "resolved": False,
                             "mark": "new", "raw": text, "src": src}
        self.dirty = True
        self.batch_ids.add(rid)
        self.root.title(APP_TITLE)
        hidden_by_cat = not self.cat_ok(self.records[rid])
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
        if getattr(self, "wn_league", None) is not None and self.wn_league.winfo_exists():
            self.wn_league["values"] = leagues
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

    def ev_resolved(self, rid):
        self.update_row(rid)
        self.refresh_detail_if_selected(rid)
        goods = self.good_mods(self.records[rid])
        if goods and SETTINGS["popups"]:
            lines = [pretty(m["text"]) + (f"  -  listings with it ask about {fmt_div(med)}" if med is not None else "  -  learned as valuable")
                     for m, med in goods[:4]]
            self.toast.show(f"★ {len(goods)} valuable mod{'s' if len(goods) > 1 else ''}", lines, C["good"],
                            SETTINGS["toast_secs"])

    def ev_priced(self, rid):
        rec = self.records.get(rid)
        if not rec:
            return
        if rec.get("src") == "ledger":                        # 2.45.0: a Farm Ledger setup item, priced out of sight
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
            if SETTINGS["popups"] and len(self.batch_ids) <= 1 and rec["est"] is not None and rec["est"] >= SETTINGS["good_div"] \
                    and "WIDE SPREAD" not in rec.get("label", ""):
                self.toast.show(f"💰 ~{fmt_div(rec['est'])}", [rec["item"]["name"], rec["label"]], C["green"],
                                SETTINGS["toast_secs"])

    # ---------------- tracking: listed / removed, names, views
    def visible(self, rec):
        want = self.VIEW_MARK.get(SETTINGS.get("view", "Not yet listed"))
        return (rec.get("src", "manual") == self.list_src()             # 2.42.0: this list only
                and (want is None or rec.get("mark", "new") == want) and self.cat_ok(rec))

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
            on = (self.cat_var.get(), self.rar_var.get(), self.type_var.get()) != (self.ALL_CATS, "All", "All")
            btn.config(state="normal" if on else "disabled")

    def cat_reset(self):
        self.cat_var.set(self.ALL_CATS)
        self.on_cat()

    def rebuild_tree(self):
        sel = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        shown = 0
        for rid in sorted(self.records):
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
            self.status_text, self.status_until = f"Copied \"{name}\" - Ctrl+F in your stash and paste it", time.time() + 6

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
                                   (self.remove_btn, "removed", "✖ Mark removed", "↺ Unmark removed")):
            btn.config(text=off if recs and all(r.get("mark", "new") == mark for r in recs) else on)

    def toggle_mod(self, rec, mod, checked):
        g = impact_key(norm(mod["text"]))              # what the Mod rules tab says for every tablet
        self.set_item_impact(rec, mod, ("normal" if g == "ignore" else g) if checked else "ignore")

    def set_item_impact(self, rec, mod, imp):
        """Tick / untick / star a mod on this one item only (pack size is worth money on some tablets, not all)."""
        k = norm(mod["text"])
        ov = rec.setdefault("ov", {})
        if imp == impact_key(k):
            ov.pop(k, None)
        else:
            ov[k] = imp
        self.dirty = True
        self.reprice([rec["id"]])

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
                pass

    def reprice(self, rids):
        for rid in rids:
            rec = self.records.get(rid)
            if not rec:
                continue
            rec["state"] = "queued"
            self.batch_ids.add(rid)
            self.update_row(rid)
            self.refresh_detail_if_selected(rid)
            self.engine.add(2 if rec["resolved"] else 1, "price" if rec["resolved"] else "resolve", rid)

    def reprice_all(self):
        self.reprice([rid for rid, r in self.records.items() if r.get("mark", "new") == "new" and self.in_list(r)])

    def on_listing_rules(self, _e=None):
        SETTINGS["status"], SETTINGS["age"] = self.status_var.get(), self.age_var.get()
        save_json("settings.json", SETTINGS)
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
                if r.get("src") == "ledger":                  # (a Farm Ledger item that was still being priced)
                    continue
                self.records[int(r["id"])] = r
                if r.get("state") in ("queued", "pricing"):      # was still waiting when the app closed
                    r["state"] = "queued"
                    self.engine.add(2 if r.get("resolved") else 1, "price" if r.get("resolved") else "resolve", r["id"])
            except Exception:
                continue
        self.next_id = max([int(data.get("next_id", 1))] + [rid + 1 for rid in self.records])
        self.seen_texts = {hash(r["raw"].strip()): rid for rid, r in self.records.items() if r.get("raw")}
        self.rebuild_tree()

    # ---------------- mod rules tab
    def build_rules_page(self, tab, cat):
        ns = types.SimpleNamespace(cat=cat, keys={}, filt=tk.StringVar())
        self.rt[cat] = ns
        ns.filt.trace_add("write", lambda *a: self.refresh_rules(cat))
        rbar = tk.Frame(tab, bg=C["panel"], padx=8, pady=8)
        rbar.pack(fill="x")
        tk.Label(rbar, text="Filter", bg=C["panel"], fg=C["muted"]).pack(side="left", padx=(0, 8))
        ttk.Entry(rbar, textvariable=ns.filt, width=18).pack(side="left")
        ttk.Button(rbar, text="Export rules", command=self.export_rules).pack(side="left", padx=(16, 0))
        ttk.Button(rbar, text="Import rules", command=self.import_rules).pack(side="left", padx=(8, 0))
        if cat not in SCOPED_CATS and any(mod_cat(k) == cat for k in COMMUNITY):   # (votes imported before 2.20.0)
            ttk.Button(rbar, text="Remove imported", command=self.clear_imported_rules, style="Danger.TButton").pack(side="left", padx=(8, 0))
        if cat not in SCOPED_CATS:                       # 2.20.0: tiers decide what's left out first
            tbar = tk.Frame(tab, bg=C["panel"], padx=8)
            tbar.pack(fill="x")
            tk.Label(tbar, text="Tier for selected:", bg=C["panel"], fg=C["muted"]).pack(side="left", padx=(0, 8))
            for t in TIER_ORDER:
                ttk.Button(tbar, text=t, width=3, command=lambda t=t: self.tiers_selected(t)).pack(side="left", padx=(0, 4))
            ttk.Button(tbar, text="Auto", command=lambda: self.tiers_selected(None), style="Quiet.TButton").pack(side="left", padx=(4, 0))
            tk.Label(tbar, text="S matters most, D least. When no listing has all of an item's mods, the D-tier mods "
                                "are left out first, then C. Not set: High = A, Normal = C.",
                     bg=C["panel"], fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=12)
        for imp in ("ignore", "normal", "high"):
            ttk.Button(rbar, text=IMPACT_LABEL[imp], command=lambda i=imp: self.rules_selected(i)).pack(side="right", padx=(8, 0))
        tk.Label(rbar, text="Set selected to:", bg=C["panel"], fg=C["muted"]).pack(side="right", padx=8)
        if cat in SCOPED_CATS:                           # 2.6.0: what these rules are for
            tk.Label(tab, text={"waystone": "Waystones are priced on their numbers (pack size, rarity ...), not their "
                                            "mods. Rate the mods you want or don't want, and Regex uses it: ★ on the "
                                            "mod, and ★ Select valuable.",
                                "relic": "Rate the relic mods you're after. Regex marks them ★ and ★ Select valuable "
                                         "picks them; Market Insights lists them."}[cat],
                     bg=C["panel"], fg=C["muted"], anchor="w", justify="left", wraplength=760, padx=12,
                     font=("Segoe UI", 9)).pack(fill="x")
        ns.info = tk.Label(tab, bg=C["panel"], fg=C["muted"], anchor="w", padx=12)
        ns.info.pack(fill="x")
        ns.tv = ttk.Treeview(tab, columns=("impact", "tier", "learned", "type", "mod", "on"), show="headings",
                             selectmode="extended")
        for cid, title, w, anchor in (("impact", "Impact", 100, "w"), ("tier", "Tier", 50, "center"),
                                      ("learned", "Learned from data", 190, "w"), ("type", "Type", 80, "w"),
                                      ("mod", "Mod", 420, "w"), ("on", "Found on", 220 if cat == "tablet" else 300, "w")):
            ns.tv.heading(cid, text=title)
            ns.tv.column(cid, width=w, anchor=anchor, stretch=(cid == "mod"))
        rsb = ttk.Scrollbar(tab, orient="vertical", command=ns.tv.yview)
        ns.tv.configure(yscrollcommand=rsb.set)
        rsb.pack(side="right", fill="y")
        ns.tv.pack(fill="both", expand=True)
        ns.tv.tag_configure("high", foreground=C["good"])
        ns.tv.tag_configure("ignore", foreground=C["muted"])
        ns.tv.bind("<Double-1>", lambda e, c=cat: self.cycle_rule(e, c))
        if cat in SCOPED_CATS:
            ns.tv.heading("on", text="Tiers" if cat == "waystone" else "Relic sizes")
            ns.tv["displaycolumns"] = ("impact", "type", "mod", "on")         # nothing is learned for these
        self.list_register("modbook", ns.tv)                                      # 2.4.0: Ctrl+A, Shift / Ctrl+click

    def migrate_rules_once(self):
        """2.6.0, once: waystone / relic rules set from Regex move to their own names (mods.migrate_scoped_rules)."""
        if SETTINGS.get("rules_scoped_26"):
            return
        try:
            from . import regex as R

            def lines(kind):
                return [l for m in R.mods(kind) for l in (m.get("lines") or [m["line"]])]
            if migrate_scoped_rules(lines("waystone"), lines("relic")):
                save_json("mod_rules.json", RULES)
            SETTINGS["rules_scoped_26"] = True
            save_json("settings.json", SETTINGS)
        except Exception:
            self.log_error("moving waystone / relic rules")

    def rules_cat(self):
        """Which rules page is showing: 'tablet', 'jewel', 'waystone' or 'relic'."""
        try:
            return {2: "jewel", 3: "waystone", 4: "relic"}.get(self.mb_nb.index(self.mb_nb.select()), "tablet")
        except Exception:
            return "tablet"

    def refresh_rules(self, cat=None):
        for c in ((cat,) if cat else ("tablet", "jewel", "waystone", "relic")):
            if c in self.rt:
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
            ns.tv.insert("", "end", iid=iid, values=(IMPACT_LABEL[imp], "", "", side, text, on),
                         tags=(imp,) if imp != "normal" else ())
            if tuple(keys) in keep:
                ns.tv.selection_add(iid)
        counts = {i: sum(1 for r in rows if r[4] == i) for i in IMPACTS}
        ns.info.config(text=f"{counts['high']} high  ·  {counts['normal']} normal  ·  {counts['ignore']} ignored"
                            + ("" if rows or q else "   (regexdata.json not found)"))

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
            t = tier_key(k)
            tier = (t + ("" if k in TIERS else " (auto)")) if t else ""
            ns.tv.insert("", "end", iid=iid, values=(IMPACT_LABEL[imp], tier, learned, "/".join(sorted(kd)) if len(kd) == 1 else ("Both" if kd else ""), text, on),
                                 tags=(imp,) if imp != "normal" else ())
            if k in keep:
                ns.tv.selection_add(iid)
        counts = {i: sum(1 for k in known if impact_key(k) == i) for i in IMPACTS}
        fname = "tabs.txt" if cat == "tablet" else "jewels.txt"
        ns.info.config(text=f"{counts['high']} high  ·  {counts['normal']} normal  ·  {counts['ignore']} ignored"
                            + ("" if src else f"   ({fname} not found - put it in {DATA_DIR} or next to the app and restart)"))

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
        msg = (f"Imported {len(new) + (len(differ) if take else 0)} rule(s) into your Mod book"
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
        """2.20.0: give the selected mods a tier (None = back to automatic), then re-price items that have them."""
        ns = self.rt[self.rules_cat()]
        keys = set()
        for i in ns.tv.selection():
            k = ns.keys.get(i)
            keys |= set(k if isinstance(k, list) else [k] if k else [])
        if not keys:
            return self._say("Select mods first (Ctrl+A for all, Shift / Ctrl + click), then pick a tier.", 8)
        for k in keys:
            if tier is None or tier == default_tier(k):
                TIERS.pop(k, None)
            else:
                TIERS[k] = tier
        save_json("mod_tiers.json", TIERS)
        affected = [rid for rid, rec in self.records.items() if rec.get("mark", "new") == "new"
                    and (rec.get("nomatch") or rec.get("partial")) and any(norm(m["text"]) in keys for m in rec["item"]["mods"])]
        self.reprice(affected)
        self.refresh_rules()
        self._say(f"Tier {tier or 'automatic'} for {len(keys)} mod{'s' if len(keys) != 1 else ''}"
                  + (f"; re-pricing {len(affected)} item(s) that didn't find every mod together" if affected else "."), 8)

    def cycle_rule(self, event, cat="tablet"):
        ns = self.rt[cat]
        iid = ns.tv.identify_row(event.y)
        if iid in ns.keys:
            k = ns.keys[iid]
            keys = k if isinstance(k, list) else [k]
            self.set_rules(keys, IMPACTS[(IMPACTS.index(impact_key(keys[0])) + 1) % len(IMPACTS)])

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
        affected = [rid for rid, rec in self.records.items()
                    if rec.get("mark", "new") == "new" and any(norm(m["text"]) in keys for m in rec["item"]["mods"])]
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
        if conf and it.get("gear") and not it.get("waystone") and it.get("rarity") != "Unique":
            conf = "Guess"                                    # 2.0 beta 21: gear prices are a rough guess
        stars = "★" * keys if keys else ""                     # 2.24.0: its own column (2.19.0 put it before the name)
        self.tree.item(str(rid), values=(rid, it["name"], it["base"], self.MARK_TEXT[mark], est, conf, listings,
                                         stamp, match, stars), tags=tags)

    def on_price_unit(self):
        from .pricefmt import PRICE_UNITS
        SETTINGS["price_unit"] = next((k for k, t in PRICE_UNITS if t == self.unit_var.get()), "auto")
        save_json("settings.json", SETTINGS)
        self.refresh_all()
        self.update_total()
        for fn in ("refresh_insights", "wealth_fill_items", "tracker_draw"):   # other windows that show prices
            f = getattr(self, fn, None)
            if f:
                try:
                    f()
                except Exception:
                    pass
        u = SETTINGS["price_unit"]
        if u not in ("auto", "divine") and not RATES.value(u):
            self._say("No exchange rate for that currency yet (Exchange rates loads them): prices stay in divines "
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
            txt = fmt_div(tot)
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
        if SETTINGS["popups"]:
            self.toast.show("✔ All items checked", lines, C["green"], 15)
        if SETTINGS["sound"]:
            try:
                if sys.platform == "win32":
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                else:
                    self.root.bell()
            except Exception:
                pass

    def pace_secs_per_item(self):
        """2.26.2: a first guess at how long one item takes, before any has finished: the pace's search allowance
        (searches per 5 minutes) and about two searches an item."""
        from .net import PACES
        cap = PACES.get(SETTINGS.get("pace"), PACES["Balanced"]).get("cap300") or 8
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
        book = f"Mod book: {MARKET.mods_known()} mods learned"
        parts.append(book)
        self.status.config(text="   ·   ".join(parts) if (n_items or self.status_text) else f"Ready   ·   {book}")

    # ---------------- sorting / selection / actions
    def sort_by(self, col):
        self.sort_rev = (not self.sort_rev) if self.sort_col == col else (col in ("est", "conf", "listings", "priced",
                                                                                   "vmods"))
        self.sort_col = col
        self._apply_sort()
        self.sort_headings()

    def sort_headings(self):
        """▲ / ▼ on the column the list is sorted by (2.0 beta 22), so you can see it and click # to go back to the
        order you added the items in."""
        for cid, title, _w, _a in self.COLS:
            arrow = (" ▼" if self.sort_rev else " ▲") if cid == self.sort_col else ""
            self.tree.heading(cid, text=title + arrow)

    def sort_added(self):
        self.sort_col, self.sort_rev = "added", False
        self._apply_sort()
        self.sort_headings()

    def _apply_sort(self):
        col = self.sort_col
        if not col:
            return

        def key(rid):
            rec = self.records[int(rid)]
            if col == "added":                                 # 2.0 beta 22: the order you copied them in
                return int(rid)
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
        self.update_mark_buttons()
        if rec and SETTINGS.get("auto_copy"):
            self.copy_name(rec)

    def checks_menu_actions(self, sel):
        """2.36.0: the Price checks rows' own right-click actions (Delete / Copy come from the standard list menu)."""
        rids = [int(i) for i in sel if str(i).isdigit() and int(i) in self.records]
        one = self.records[rids[0]] if len(rids) == 1 else None
        n = f" ({len(rids)})" if len(rids) > 1 else ""
        return [(f"Re-price{n}", lambda: self.reprice(rids), bool(rids)),
                ("Copy name", lambda: self.copy_name(one, True), one is not None, "C"),
                ("Open on trade site", self.open_trade, bool(one and one.get("qid")), "O"),
                None,
                (f"✔ Mark listed{n}", lambda: self.mark_selected("listed"), bool(rids)),
                (f"💰 Mark sold{n}", lambda: self.mark_selected("sold"), bool(rids)),
                (f"✖ Mark removed{n}", lambda: self.mark_selected("removed"), bool(rids))]

    def open_trade(self):
        sel = self.tree.selection()
        if len(sel) != 1:
            return
        rec = self.records[int(sel[0])]
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
                pass
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
            pass

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
        col = C["rare"] if it["rarity"] == "Rare" else C["magic"]

        def box(parent, edge=None, pad=(16, 8)):
            return tk.Frame(parent, bg=P1, padx=pad[0], pady=pad[1], highlightthickness=1, highlightbackground=edge or C["line"])

        # ---- title row: tablet type chip and the Copy button
        trow = tk.Frame(d, bg=P2)
        trow.pack(fill="x", pady=(0, 8))
        tk.Label(trow, text=it["base"].upper(), bg="#1b2b4a", fg="#cfe0ff", font=("Segoe UI", 9, "bold"), padx=8, pady=4,
                 highlightthickness=1, highlightbackground=C["gold_dim"]).pack(side="left")
        ttk.Button(trow, text="Copy name  [C]", command=lambda: self.copy_name(rec, True)).pack(side="right")
        tk.Label(d, text=it["name"], bg=P2, fg=col, font=("Segoe UI", 16, "bold"), anchor="w",
                 wraplength=wrap-11, justify="left").pack(fill="x")
        if it["corrupted"]:
            tk.Label(d, text="corrupted", bg=P2, fg=C["red"], anchor="w").pack(fill="x")
        if it.get("gear"):                                   # 1.41: how this piece of gear is searched
            tk.Label(d, text=(waystone.summary(it) if it.get("waystone") else gear.summary(it)) + "".join("  ·  " + n for n in it.get("notes") or []), bg=P2, fg=C["muted"],
                     font=("Segoe UI", 9), anchor="w", wraplength=wrap-11, justify="left").pack(fill="x")
        tk.Frame(d, bg=P2, height=8).pack()

        card = box(d)
        card.pack(fill="x", pady=(0, 8))
        st = rec["state"]
        if st == "done":
            nomatch = rec.get("nomatch")
            manual = rec.get("manual")
            if nomatch:
                big = "NO MATCH"
            elif manual:
                big = "CHECK BY HAND"
            else:
                big = fmt_div(rec["est"]) if rec["est"] is not None else (fmt_price(rec["prices"][0]) if rec["prices"] else "no listings")
                if rec.get("partial") and rec["prices"]:
                    big = "≥ " + big
                elif rec.get("thin") and rec["prices"]:
                    big = "~ " + big
            head = tk.Frame(card, bg=P1)
            head.pack(fill="x")
            left = tk.Frame(head, bg=P1)
            left.pack(side="left", fill="x", expand=True)
            tk.Label(left, text="ESTIMATED VALUE", bg=P1, fg=C["muted"], font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
            tk.Label(left, text=big, bg=P1, fg=C["red"] if (nomatch or manual or not rec["prices"]) else C["good"],
                     font=(MONO, 22, "bold"), anchor="w").pack(fill="x")
            cf = rec.get("conf")
            guess = it.get("gear") and not it.get("waystone") and it.get("rarity") != "Unique"
            if cf and cf != "-" and guess:                      # 2.0 beta 21: say plainly that gear is a guess
                right = tk.Frame(head, bg=P1)
                right.pack(side="right", anchor="n")
                tk.Label(right, text="Rough guess", bg=C["warn_bg"], fg=C["good"], font=("Segoe UI", 10, "bold"),
                         padx=8, pady=4, highlightthickness=1, highlightbackground=C["good"]).pack(anchor="e")
                cf = None
            if cf and cf != "-":
                tint = {"High": (C["ok_bg"], C["green"]), "Medium": (C["warn_bg"], C["good"]), "Low": (C["bad_bg"], C["red"])}.get(cf, (P2, C["muted"]))
                right = tk.Frame(head, bg=P1)
                right.pack(side="right", anchor="n")
                tk.Label(right, text=f"{cf} Confidence", bg=tint[0], fg=tint[1], font=("Segoe UI", 10, "bold"), padx=8, pady=4,
                         highlightthickness=1, highlightbackground=tint[1]).pack(anchor="e")
                if rec.get("spread"):
                    tk.Label(right, text=f"Spread: {rec['spread']:.0f}x", bg=P1, fg=C["muted"], font=(MONO, 9)).pack(anchor="e", pady=(4, 0))
            tk.Label(card, text=rec["label"] + ("" if nomatch else f"  ·  {rec['total']} listings"), bg=P1, fg=C["muted"],
                     anchor="w", wraplength=wrap-31, justify="left").pack(fill="x", pady=(2, 0))
            if guess:
                g = tk.Label(card, text="Price checks is made for tablets, jewels and waystones. For gear this is a "
                                        "rough guess: check it yourself (press O for the trade search, or use your "
                                        "usual price checker).", bg=P1, fg=C["good"], anchor="w",
                             wraplength=wrap-31, justify="left", font=("Segoe UI", 9))
                g.pack(fill="x", pady=(4, 0))
            why = rec.get("conf_why") or []
            if cf and cf not in ("-", "High") and why:
                wb = tk.Frame(card, bg=C["warn_bg"], padx=8, pady=8, highlightthickness=1, highlightbackground="#7a6428")
                wb.pack(fill="x", pady=(8, 0))
                tk.Label(wb, text="⚠  " + "; ".join(why) + ".", bg=C["warn_bg"], fg="#f0dca0", anchor="w", font=("Segoe UI", 9),
                         wraplength=wrap-70, justify="left").pack(fill="x")
            elif cf == "High" and why:
                tk.Label(card, text="Confidence: " + "; ".join(why), bg=P1, fg=C["green"], font=("Segoe UI", 9, "bold"), anchor="w",
                         wraplength=wrap-31, justify="left").pack(fill="x", pady=(8, 0))
            if rec.get("est") is not None and not nomatch and not manual and not rec.get("skip"):
                eq, opt = RATES.equivalents(rec["est"]), RATES.list_options(rec["est"])
                if eq or opt:
                    lb = tk.Frame(card, bg=P2, padx=8, pady=8, highlightthickness=1, highlightbackground=C["line"])
                    lb.pack(fill="x", pady=(8, 0))
                    tk.Label(lb, text="IF YOU LIST IT", bg=P2, fg=C["steel"], font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
                    if eq:
                        tk.Label(lb, text="≈ " + "  ·  ".join(f"{_amt(a)} {cur}" for cur, a in eq), bg=P2, fg=C["text"], font=("Segoe UI", 9),
                                 anchor="w", wraplength=wrap-60, justify="left").pack(fill="x", pady=(2, 0))
                    if opt:
                        tk.Label(lb, text="Round to:  " + opt, bg=P2, fg=C["good"], font=("Segoe UI", 9, "bold"), anchor="w",
                                 wraplength=wrap-60, justify="left").pack(fill="x", pady=(2, 0))
            if rec.get("uses_note") and not nomatch and not manual:      # 1.45: a used tablet, priced by its uses left
                ub = tk.Frame(card, bg=C["warn_bg"], padx=8, pady=8, highlightthickness=1, highlightbackground="#7a6428")
                ub.pack(fill="x", pady=(8, 0))
                tk.Label(ub, text="✂  " + rec["uses_note"], bg=C["warn_bg"], fg="#f0dca0", anchor="w", font=("Segoe UI", 9),
                         wraplength=wrap-70, justify="left").pack(fill="x")
            if rec.get("memory"):
                tk.Label(card, text=rec["memory"], bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w",
                         wraplength=wrap-31, justify="left").pack(fill="x", pady=(4, 0))
            if rec.get("model"):
                tk.Label(card, text=rec["model"], bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w",
                         wraplength=wrap-31, justify="left").pack(fill="x", pady=(4, 0))
            if rec.get("priced_at"):
                tk.Label(card, text="Priced " + fmt_stamp(rec["priced_at"]), bg=P1, fg=C["muted"],
                         font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(4, 0))
            if nomatch:
                tk.Label(card, text="None of the searches found a matching Instant Buyout listing, so no price is guessed. "
                                    "Try ticking off a mod below, or check the trade site by hand.",
                         bg=P1, fg=C["text"], anchor="w", wraplength=wrap-31, justify="left").pack(fill="x", pady=(8, 0))
            elif manual:
                tk.Label(card, text=(("Not searched: " + rec["manual_why"] + ". Please price it by hand.") if rec.get("manual_why") else
                                     "The listings that match this tablet are priced wildly differently, so any single number "
                                     "would be a guess. Please price it by hand: open a search below and look at the listings."),
                         bg=P1, fg=C["text"], anchor="w", wraplength=wrap-31, justify="left").pack(fill="x", pady=(8, 0))
                tk.Label(card, text="cheapest: " + ",  ".join(fmt_price(p) for p in rec["prices"][:5]),
                         bg=P1, fg=C["text"], anchor="w", wraplength=wrap-31, justify="left").pack(fill="x", pady=(4, 0))
            elif rec["prices"]:
                tk.Label(card, text="cheapest: " + ",  ".join(fmt_price(p) for p in rec["prices"][:5]),
                         bg=P1, fg=C["text"], anchor="w", wraplength=wrap-31, justify="left").pack(fill="x", pady=(4, 0))
            if rec.get("qid"):
                ttk.Button(card, text="Open on trade site  [O]", style="Primary.TButton", command=self.open_trade).pack(fill="x", pady=(8, 0))
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
        elif st == "error":
            tk.Label(card, text="Couldn't price this", bg=P1, fg=C["red"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
            tk.Label(card, text=rec["label"], bg=P1, fg=C["muted"], anchor="w", wraplength=wrap-31, justify="left").pack(fill="x")
        else:
            tk.Label(card, text="Pricing…" if st == "pricing" else "Waiting in line…", bg=P1, fg=C["muted"],
                     font=("Segoe UI", 12), anchor="w").pack(fill="x")

        head_txt = (f"TOTALS AND MODIFIERS ({len(it['mods'])})" if it.get("gear") else
                    f"{it['base'].upper().replace(' TABLET', '')} MODIFIERS ({len(it['mods'])})")
        tk.Label(d, text=head_txt, bg=P2, fg=C["steel"], font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(12, 0))
        legend = ("★ must match     ☑ counts (one or two may be dropped if too few listings)     unticked: not searched     "
                  "Min / Max: the values searched for  (this item only)" if it.get("gear") else
                  "☑ counts in the price search     ★ key mod     Min / Max: the values searched for  (this item only)")
        tk.Label(d, text=legend,
                 bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w", wraplength=wrap, justify="left").pack(fill="x", pady=(0, 4))
        for m in it["mods"]:
            med = MARKET.mod_median(it["base"], m.get("sid")) if m.get("sid") else None
            good = med is not None and med >= SETTINGS["good_div"]
            imp = mod_impact(rec, m)
            li = learned_info(norm(m["text"]))
            key = imp == "high" or (good and imp != "ignore")
            row = tk.Frame(d, bg=P1, padx=8, pady=4, highlightthickness=1,
                           highlightbackground=C["good"] if key else C["line"])
            row.pack(fill="x", pady=1)
            top = tk.Frame(row, bg=P1)
            top.pack(fill="x")
            on_var = tk.BooleanVar(value=imp != "ignore")          # tick = counts in the price search
            self.detail_vars.append(on_var)
            ttk.Checkbutton(top, variable=on_var, style="Mod.TCheckbutton", cursor="hand2",
                            command=lambda mm=m, v=on_var: self.toggle_mod(rec, mm, v.get())).pack(side="left")
            star = tk.Label(top, text="★" if imp == "high" else "☆", bg=P1, cursor="hand2",
                            fg=C["good"] if imp == "high" else C["muted"], font=("Segoe UI", 12))
            star.pack(side="right", padx=(8, 0))                   # click: mark / unmark as a key (high-impact) mod
            star.bind("<Button-1>", lambda _e, mm=m, cur=imp: self.set_item_impact(
                rec, mm, "normal" if cur == "high" else "high"))
            tk.Label(top, text=m.get("shown") or pretty(m["text"]),
                     bg=P1,
                     fg=C["muted"] if imp == "ignore" else C["text"] if m.get("sid") or not rec["resolved"] else C["red"],
                     anchor="w", wraplength=wrap-131, justify="left").pack(side="left", fill="x", expand=True)
            meta = tk.Frame(row, bg=P1)
            meta.pack(fill="x", pady=(4, 0))
            rp = m.get("roll")
            if rp is not None:
                cv = tk.Canvas(meta, width=90, height=8, bg=C["line"], highlightthickness=0)
                cv.pack(side="left")
                colr = C["green"] if rp >= 0.8 else C["good"] if rp >= 0.4 else C["red"]
                cv.create_rectangle(0, 0, max(3, int(90 * rp)), 8, fill=colr, outline="")
                tk.Label(meta, text=f"{round(rp * 100)}%", bg=P1, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(8, 8))
            if m["tier"]:
                tk.Label(meta, text=f"T{m['tier']}", bg=P1, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
            for fl in sorted(m["flags"]):
                tk.Label(meta, text=fl, bg=P1, fg=FLAG_COLORS.get(fl, C["muted"]), font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
            if m.get("value") is not None and not m.get("novalue") and (m.get("sid") or not rec["resolved"]):
                self.value_boxes(rec, m, row, imp)
            if m.get("note"):
                tk.Label(row, text=m["note"], bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w",
                         wraplength=wrap-51, justify="left").pack(fill="x")
            if rec["resolved"] and not m.get("sid"):
                tk.Label(meta, text="not found on trade site", bg=P1, fg=C["red"], font=("Segoe UI", 9)).pack(side="left")
                if m.get("guess"):
                    tk.Label(row, text=f"closest: {m['guess']}", bg=P1, fg=C["muted"], font=("Segoe UI", 9),
                             anchor="w", wraplength=wrap-51, justify="left").pack(fill="x")
            elif med is not None:
                tk.Label(meta, text=f"listings ask ~{fmt_div(med)}", bg=P1, fg=C["good"] if good else C["muted"],
                         font=("Segoe UI", 9, "bold" if good else "normal")).pack(side="right")
            elif li and li["tier"] == "high":
                tk.Label(meta, text="learned: valuable", bg=P1, fg=C["good"], font=("Segoe UI", 9, "bold")).pack(side="right")

        self.search_filters_box(rec, d, wrap)                 # 2.4.1: seller, currency, corrupted, gear numbers
        if rec.get("opts") or any(m.get("value") is not None and not m.get("novalue") for m in it["mods"]):
            ttk.Button(d, text="Search with these values  [Enter]", style="Primary.TButton",
                       command=lambda: self.reprice([rec["id"]])).pack(fill="x", pady=(8, 0))
        # ---- tracking: has this one been listed yet?
        ign = sum(1 for m in it["mods"] if mod_impact(rec, m) == "ignore")
        if ign:
            tk.Label(d, text=f"{ign} low-impact mod{'s' if ign != 1 else ''} left out of the price search",
                     bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(8, 0))
        mark = rec.get("mark", "new")
        bx = box(d)
        bx.pack(fill="x", pady=(8, 0))
        tk.Label(bx, text="LISTING STATUS", bg=P1, fg=C["steel"], font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
        cur_txt = {"new": "Not listed yet",
                   "listed": "✔ Listed" + (f" for {rec['list_price']}" if rec.get("list_price") else ""),
                   "sold": "💰 Sold" + (f" for {rec['sold_price']}" if rec.get("sold_price") else ""),
                   "removed": "✖ Removed (reforged / changed)"}[mark]
        tk.Label(bx, text=cur_txt, bg=P1, font=("Segoe UI", 12, "bold"), anchor="w",
                 fg={"new": C["text"], "listed": C["green"], "sold": "#7fe0c0", "removed": C["muted"]}[mark]
                 ).pack(fill="x", pady=(2, 8))
        prow = tk.Frame(bx, bg=P1)
        prow.pack(fill="x", pady=(0, 8))
        tk.Label(prow, text="Listed at", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 8))
        suggest = rec.get("list_price") or (fmt_div(rec["est"]) if rec.get("est") is not None and not rec.get("skip") else "")
        self.price_var = tk.StringVar(value=suggest)
        ttk.Entry(prow, textvariable=self.price_var, width=16).pack(side="left")
        if mark == "listed":
            ttk.Button(bx, text="↺ Unmark listed (back to not listed)", style="Primary.TButton",
                       command=lambda: self.mark_selected("new")).pack(fill="x", pady=2)
        else:
            ttk.Button(bx, text="✔ Mark as listed", style="Primary.TButton",
                       command=lambda: self.mark_selected("listed")).pack(fill="x", pady=2)
        # 2.21.0: what it really sold for - the Mod book learns from real sales
        srow = tk.Frame(bx, bg=P1)
        srow.pack(fill="x", pady=(8, 2))
        tk.Label(srow, text="Sold for", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 8))
        self.sold_var = tk.StringVar(value=rec.get("sold_price") or "")
        se = ttk.Entry(srow, textvariable=self.sold_var, width=16)
        se.pack(side="left")
        se.bind("<Return>", lambda e: self.mark_selected("sold"))
        if mark == "sold":
            ttk.Button(srow, text="↺ Unmark sold", command=lambda: self.mark_selected("new")).pack(side="left", padx=8)
        else:
            ttk.Button(srow, text="💰 Mark as sold", command=lambda: self.mark_selected("sold")).pack(side="left", padx=8)
        tk.Label(bx, text="A real sale teaches the Mod book what these mods are worth.", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w").pack(fill="x")
        if mark == "removed":
            ttk.Button(bx, text="↺ Unmark removed (back to not listed)", command=lambda: self.mark_selected("new")).pack(fill="x", pady=2)
        else:
            ttk.Button(bx, text="✖ Mark as removed (reforged / changed)",
                       command=lambda: self.mark_selected("removed")).pack(fill="x", pady=2)
        ttk.Button(bx, text="Re-price this item", command=lambda: self.reprice([rec["id"]])).pack(fill="x", pady=(8, 2))

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
            self.reprice([rec["id"]])

        for key, (v, e) in boxes.items():
            e.bind("<KeyRelease>", keep)
            e.bind("<Return>", lambda _e: (keep(), self.reprice([rec["id"]]), "break")[-1])
        edited.bind("<Button-1>", reset)
        mark_edited()

    # ---------------- mod book page
    def refresh_memory(self, force=False):
        """The 'Mod book' page: everything learned from the listings the app has fetched. Asking prices only - never sale
        prices, and mostly the cheap end."""
        if not hasattr(self, "mem_frame") or (not force and not self.page_open("Mod book")):
            return
        for w in self.mem_frame.winfo_children():
            w.destroy()
        view = self.mem_view.get()
        q = self.mem_filter.get().lower().strip()

        def nice(sid):
            t = SIDTEXT.get(sid, sid)
            return re.sub(r"\s+(found )?in map$", "", t)
        if view == "Mod priority":
            cols = [("base", "Tablet / jewel", 120, "w"), ("mod", "Mod", 420, "w"), ("n", "Listings", 70, "e"),
                    ("med", "Median ask", 100, "e"), ("lift", "Worth vs others", 135, "e"), ("data", "Data says", 110, "w"),
                    ("mine", "Your mark", 90, "w"), ("check", "Check", 330, "w")]
            data = [r for r in self.priority_rows() if not q or q in (r[0] + " " + nice(r[1])).lower()]
            note = "Which mods the data says are valuable, next to your own marks. Rows that need a look come first."
        elif view == "Single mods":
            cols = [("base", "Tablet / jewel", 120, "w"), ("mod", "Mod", 480, "w"), ("n", "Listings seen", 90, "e"),
                    ("lo", "Cheapest ask", 110, "e"), ("med", "Median ask", 110, "e"), ("hi", "Highest ask", 110, "e"),
                    ("age", "Last seen", 90, "e")]
            data = [r for r in MARKET.mod_summary() if not q or q in (r[0] + " " + nice(r[1])).lower()]
            note = "Every mod seen on a fetched listing, and what those listings asked."
        elif view == "Mod combinations":
            cols = [("base", "Tablet / jewel", 120, "w"), ("mods", "Mods searched together", 560, "w"),
                    ("seen", "Searches", 70, "e"), ("best", "Highest cheapest-listing", 150, "e"),
                    ("last", "Latest cheapest", 110, "e"), ("est", "Latest estimate", 110, "e"), ("age", "Last seen", 90, "e")]
            data = [r for r in MARKET.combos() if not q or q in (r[0] + " " + " ".join(nice(f[0]) for f in r[1])).lower()]
            note = "Every set of mods that was searched together, and the price it came out at."
        else:
            cols = [("star", "★", 46, "center"), ("base", "Base", 140, "w"), ("text", "Mod", 420, "w"),
                    ("floor", "Cheapest with this mod", 160, "e"), ("total", "Listings", 80, "e"), ("age", "Checked", 100, "e")]
            data = sorted((e for e in MODBOOK.values() if not q or q in (e.get("base", "") + " " + e.get("text", "")).lower()),
                          key=lambda e: (e.get("floor") is None, -(e.get("floor") or 0)))
            note = ("The old Mod book, kept as it was and no longer updated. Mods it found valuable carry on as learned "
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
                check, kind = "your High isn't backed by the data yet", "warn"
            elif mine == "high" and says == "High":
                check, kind = "agree", "great"
            elif mine != "high" and says == "High":
                check, kind = "learned: treated as High automatically", "great"
            else:
                check, kind = "", ""
            rows.append((base, sid, st["n"], st["med"], st["lift"], says, IMPACT_LABEL[mine], check, kind))
        rows.sort(key=lambda r: (r[8] == "", -(r[4] or 0)))
        return rows[:1000]

    def save_widths(self):
        try:
            SETTINGS["col_widths"] = {c[0]: int(self.tree.column(c[0], "width")) for c in self.COLS}
            pw = int(self.outer.winfo_width())
            if pw >= 250:              # 2.0 beta 22: a closed / minimised window reports 1 - that hid the item panel
                SETTINGS["panel_w"] = pw
        except Exception:
            pass

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
            pass
        self.root.after(500, lambda: setattr(self, "_win_restored", True))

    def on_close(self):
        self.save_widths()
        self.save_session()
        try:                                         # 2.31.0: send this hour's mod prices before going
            from . import communitymods as CM
            if SETTINGS.get("share_notice_seen") and CM.sharing():
                t = threading.Thread(target=lambda: CM.push(MARKET, dict(RULES)), daemon=True)
                t.start()
                t.join(4)
        except Exception:
            pass
        try:                                         # 2.0 beta 9: a running session is kept (without a profit)
            s = getattr(self, "tk_session", None)
            if s is not None and s.ended is None:
                s.stop()
                s.note = (s.note + " (app closed)").strip()
                self.tk_sessions.add(s)
            self._tracker_store_geo()
        except Exception:
            pass
        self.stop_utilities()                        # saves the notes; stops the Delirium alert if the app started it
        save_json("settings.json", SETTINGS)
        save_modbook()
        WEALTH.save()
        LIMITER._save(True)
        self.tray.hide_icon()
        self.root.destroy()


SPLASH = [None]          # the start-up screen while the app is built (2.0.0)


def _splash_step(text=None, i=None):
    s = SPLASH[0]
    if s is not None:
        try:
            s.step(text, i)
        except Exception:
            pass


def main():
    if FROZEN and sys.platform == "win32":                # 2.29.1: remove what an update left behind
        threading.Thread(target=cleanup_update, args=(APP_DIR,), daemon=True).start()
    root = tk.Tk(className="StashOfExile2")      # 2.10.0: window managers (Hyprland) see class "Stashofexile2"
    if SETTINGS.get("splash", True):
        try:
            from .splash import Splash
            from .style import apply_look
            apply_look(SETTINGS.get("theme", "midnight"), SETTINGS.get("accent", "orange"),
                       int(SETTINGS.get("ui_scale", 100) or 100), root)
            SPLASH[0] = Splash(root, ICON_B64, pretty_version(), SETTINGS.get("league") or "")
        except Exception:
            SPLASH[0] = None
    App(root)
    root.mainloop()
