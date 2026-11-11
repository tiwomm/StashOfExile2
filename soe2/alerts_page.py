"""Alerts while you play (2.10.0): the Delirium and Breach alerts, switched on and watched from one panel on the
Session tracker's main page. (2.9.0 had Breach in Session tracker > Options and Delirium in its own window.)

Breach: the game writes its Hiveblood warnings to its own log, Client.txt (seen in real PoE 2 logs, Oct 2026):
    : <brequelwarning>{Stored Hiveblood is almost at the maximum!}
    : <brequelwarning>{Cannot store any more Hiveblood! Go to the Genesis Tree to consume it.}
Both are easy to miss in the middle of a Breach. This follows Client.txt (only new lines, about once a second - the
same way the Session tracker does) and shows a banner over the game: an "almost full" one, and a stronger "full"
one. Nothing is read from the game itself and no keys are sent. A banner looks like the Delirium alert's END DELIRIUM (2.12.1): big flashing text over the game,
no box; clicks go through it. It goes after a few seconds, or as soon as you open the Genesis Tree.

Remnant (2.37.0): the Expedition Remnant Price Checker (remnant.py / remnant_page.py) - a screen watcher.

Delirium: the helper (utilities.DELIRIUM, delirium_runner.py) looks at your screen; its END DELIRIUM banner is its own.
This panel only starts / stops it, sets its sound and tests it. Its splinter icon is gone (2.10.0)."""
import os
import sys
import time
import tkinter as tk
from tkinter import ttk

from . import buglog
from .config import P, save_json, SETTINGS
from .gamelog import area_kind as gl_area_kind, find_log, LogReader
from .style import C, Tooltip

REPEAT_SECS = 45          # the game repeats a warning (twice in 2 s, then every ~15 s when full): one banner per level
RETRY_TICKS = 15          # Client.txt not found: look again every this many seconds
LEVELS = {
    # 2.131.0 (feedback: "a more elegant solution than just giant bold flashing letters"): the calm alert card's title,
    # its detail line, its mark and its color (alertcard.py)
    "almost": ("Hiveblood almost full", "Spend it at the Genesis Tree", "!", "#d86bd0"),
    "full": ("Hiveblood is full", "Go to the Genesis Tree to consume it", "!", "#ff5a5a"),
    # 2.11.0: you left a map after the game warned and haven't opened the Genesis Tree since
    "ritual": ("Rituals not done", "Go back through your portal", "!", "#ff6a5a"),      # 2.14.0
    "tribute": ("Offer your tribute", "Tribute left - offer it to the King", "!", "#ffb347"),   # 2.129.0
    "leave": ("Spend your Hiveblood", "It was almost full when you left the map: visit the Genesis Tree", "!",
              "#ffb347"),
}
DOT = {"on": "#5ee08a", "off": "#6b7690", "warn": "#ffb347"}
TRANSPARENT = "#010203"
# 2.12.1: then it goes by itself (like END DELIRIUM). 2.129.1 (feedback: the tribute one stayed too long): 4 s
BANNER_SECS = {"almost": 8, "full": 10, "leave": 8, "ritual": 8, "tribute": 4}


def _hwnd(win):
    import ctypes
    u = ctypes.windll.user32
    u.GetParent.restype = ctypes.c_void_p
    u.GetParent.argtypes = [ctypes.c_void_p]
    return u.GetParent(win.winfo_id()) or win.winfo_id()


def click_through(win):
    """Clicks go through to the game and it never takes the keyboard (Windows) - as the Delirium alert does."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        u = ctypes.windll.user32
        u.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        u.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
        h = _hwnd(win)
        u.SetWindowLongW(h, -20, u.GetWindowLongW(h, -20) | 0x80000 | 0x20 | 0x80 | 0x08000000)
    except Exception:
        buglog.caught()


def force_topmost(win):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        u = ctypes.windll.user32
        u.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_uint]
        u.SetWindowPos(_hwnd(win), ctypes.c_void_p(-1), 0, 0, 0, 0, 0x1 | 0x2 | 0x10)
    except Exception:
        buglog.caught()


def game_rect(title="Path of Exile 2"):
    """-> (left, top, width, height) of the game window, or None (then the main screen is used)."""
    if sys.platform.startswith("linux"):
        from .linsys import game_rect as _gr
        return _gr(title)
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def cb(hwnd, _):
            if u.IsWindowVisible(hwnd):
                n = u.GetWindowTextLengthW(hwnd)
                if n:
                    buf = ctypes.create_unicode_buffer(n + 1)
                    u.GetWindowTextW(hwnd, buf, n + 1)
                    if buf.value.strip().lower() == title.lower():
                        r = wintypes.RECT()
                        u.GetWindowRect(hwnd, ctypes.byref(r))
                        found.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
                        return False
            return True
        u.EnumWindows(cb, 0)
        return found[0] if found and found[0][2] > 200 and found[0][3] > 200 else None
    except Exception:
        return None


def breach_level(text):
    """The game's warning text -> "full" or "almost"."""
    t = (text or "").lower()
    return "full" if "cannot store" in t or "any more" in t else "almost"


# 2.119.0 (UX pass): what each helper does, in one line - under its name on Helpers, and (2.124.0) the tip on its
# Quick settings chip
HELPER_BLURBS = {"delirium": "END DELIRIUM when a map ends with Delirium still on",
                 "breach": "Warns when your stored Hiveblood is almost full",
                 "ritual": "Counts rituals done; reminds you if you leave early",
                 "remnant": "Prices each reward in a remnant's book",
                 "focus": "Your current goal on the bar, a nudge in town",
                 "campaign": "Where you are in the campaign and what's next",
                 "whispers": "A card when someone wants to buy your item",
                 "desecrate": "Each Well of Souls option's tier",
                 "topup": "Says what's running low when you open your inventory in a hideout or town",   # 2.131.1
                 "breaks": "A calm card after a long stretch of play, in a hideout or town"}


class AlertsPage:
    """Mixed into App."""

    # ================================================================ settings
    def breach_cfg(self):
        c = SETTINGS.setdefault("breach_alert", {})
        c.setdefault("on", True)     # 2.118.0: on by default (a new install; yours is kept)
        c.setdefault("sound", True)
        c.setdefault("leave_reminder", True)       # 2.11.0
        c.setdefault("pending", None)              # 2.11.0: "almost" / "full" since the last warning, until the tree
        return c

    def ritual_cfg(self):
        """2.14.0: the Ritual watcher (ritual_alert.py, its own helper process)."""
        c = SETTINGS.setdefault("ritual_alert", {})
        c.setdefault("on", True)     # 2.118.0: on by default (a new install; yours is kept)
        c.setdefault("sound", True)
        c.setdefault("leave_reminder", True)
        c.setdefault("readout", True)               # 2.118.0: the Ritual line above the overlay's bar (On screen)
        return c

    def ritual_readout(self):
        """2.118.0 (feedback: show the Ritual count and your tribute on screen, with a switch): the text of the Ritual
        line over the game - "2 of 4 rituals done · 1,240 tribute" - while a map's Ritual counter has been seen, or
        "" (no line). The count used to ride on the bar's Ritual switch, which is gone."""
        c = self.ritual_cfg()
        if not (c.get("on") and c.get("readout", True)):
            return ""
        from .utilities import RITUAL
        count = RITUAL.count if RITUAL.seen == "ok" and RITUAL.count else None
        if count is None and getattr(self, "br_area", None) == "map":
            count = getattr(self, "rt_map", None)
        if getattr(self, "rt_done", False) and getattr(self, "br_area", None) == "map":
            if count and count[0] < count[1]:
                count = (count[1], count[1])
            elif not count:
                return "All rituals done ✔"
        if not count:
            return ""
        d, t = count
        txt = f"{d} of {t} rituals done" + (" ✔" if d >= t else "")
        tribute = getattr(RITUAL, "tribute", None)
        if tribute is not None:
            txt += f"  ·  {int(tribute):,} tribute"
        return txt

    def ritual_readout_sync(self):
        """The line comes and goes with the count; while it shows, its text follows."""
        try:
            txt = self.ritual_readout()
            shown = "ritual" in (getattr(self, "goal_rows", None) or []) and getattr(self, "gb_cv", None) is not None
            if bool(txt) != shown:
                if getattr(self, "mg_win", None) is not None:
                    self.goalbar_build()
            elif txt:
                lab = (getattr(self, "tk_ov_lbls", None) or {}).get("ritual")
                if lab is not None and lab.cget("text") != txt:
                    lab.config(text=txt)
        except Exception:
            buglog.caught()

    def ritual_readout_changed(self, on):
        self.ritual_cfg()["readout"] = bool(on)
        save_json("settings.json", SETTINGS)
        self.ritual_readout_sync()

    def log_wanted(self):
        """Client.txt is followed while Breach or Ritual needs it (Ritual: to know when you leave a map)."""
        from . import whispers as _W
        return bool(self.breach_cfg().get("on") or self.ritual_cfg().get("on") or self.ws_cfg().get("on")
                    or self.remnant_cfg().get("on") or _W.cfg()["on"]
                    or (hasattr(self, "fl_counting") and self.fl_counting())      # 2.45.0: the Strat Tracker's runs
                    or bool(SETTINGS.get("topup", {}).get("on")))                 # 2.131.0: Top Up (hideout / town)

    def alerts_init(self):
        """At start-up (start_utilities): the Breach watcher runs whether or not the tracker window was opened."""
        if getattr(self, "_alerts_ready", False):
            return
        self._alerts_ready = True
        self.br_reader, self.br_last, self.br_win, self.br_level = None, {}, None, None
        self.br_ticks, self._br_ticking, self.br_note = 0, False, ""
        self.br_area = None                        # 2.11.0: "map" / "hideout" / "town" / "other" - where you are
        self.rt_map = None                         # 2.14.0: the last Ritual count seen in this map (done, total)
        self.rt_done = False                       # 2.129.3: Map Content's Ritual icon is ticked
        if self.log_wanted():
            self.root.after(1500, self.breach_start)
        if self.ritual_cfg().get("on"):
            self.root.after(2500, self.ritual_start)
        if self.remnant_cfg().get("on"):                 # 2.37.0: the Remnant Auto watcher
            self.root.after(3000, self.remnant_auto_sync)
        self.root.after(3500, self.topup_start)          # 2.131.0: Top Up Reminders (only when on)
        self.root.after(3000, self.topup_take_supplies)  # 2.131.2: League Plan's Map supplies move here (once)

    # ================================================================ the panel (Session tracker, main page)
    def build_alerts_panel(self, parent):
        """2.112.0 (rework): one row per helper, the same columns for all - on / off, the name with what it's doing
        now, its own options (chips), Remind, and Test / Open (2.118.0: no On bar - the bar has no helper switches). Grouped: In maps, Play, Trading & more. One
        Sound switch for every helper sits at the top."""
        self.alerts_init()
        P2 = C["panel2"]
        box = tk.Frame(parent, bg=P2, padx=12, pady=8, highlightthickness=1, highlightbackground=C["line"])
        CB = "Card.TCheckbutton"
        self.al_rows = {}
        sm = ("Segoe UI", 9)
        top = tk.Frame(box, bg=P2)
        top.pack(fill="x")
        # (2.119.0: "They only watch and show..." is the section's own intro - it was said twice)
        self.al_sound_all = tk.BooleanVar(value=bool(SETTINGS.get("helpers_sound", True)))
        ttk.Checkbutton(top, text="Sound", variable=self.al_sound_all, style=CB,
                        command=self.alerts_sound_all).pack(side="right")
        # 2.131.0: where the alert card shows and how big - one place for every helper's alert
        from . import alertcard as _AC
        acf = _AC.cfg()
        tk.Label(top, text="Alerts show:", bg=P2, fg=C["text"], font=sm).pack(side="left")
        wv = tk.StringVar(value=_AC.WHERE[acf["where"]])
        wcb = ttk.Combobox(top, textvariable=wv, values=list(_AC.WHERE.values()), state="readonly", width=14)
        wcb.pack(side="left", padx=(8, 0))
        wcb.bind("<<ComboboxSelected>>", lambda _e: self.alert_card_set(
            "where", next(k for k, v in _AC.WHERE.items() if v == wv.get())))
        sv = tk.StringVar(value=_AC.SIZES[acf["size"]][0])
        scb = ttk.Combobox(top, textvariable=sv, values=[v[0] for v in _AC.SIZES.values()], state="readonly", width=8)
        scb.pack(side="left", padx=(8, 0))
        scb.bind("<<ComboboxSelected>>", lambda _e: self.alert_card_set(
            "size", next(k for k, v in _AC.SIZES.items() if v[0] == sv.get())))
        tb = ttk.Button(top, text="Test", command=self.alert_card_test, width=6)
        tb.pack(side="left", padx=(8, 0))
        Tooltip(wcb, "Where every helper's alert card shows over the game.")
        Tooltip(scb, "How big the alert card is.")
        Tooltip(tb, "Shows a sample alert card over the game.")
        self.al_card_where, self.al_card_size = wcb, scb
        # 2.119.0 (UX pass): Client.txt not found - one banner here (it was the same red line on every helper)
        ban = tk.Frame(box, bg=C["warn_bg"], padx=8, pady=8, highlightthickness=1, highlightbackground=C["red"])
        tk.Label(ban, text="The game's log (Client.txt) wasn't found. Breach, Ritual, Campaign, Trade whispers and "
                           "more need it.", bg=C["warn_bg"], fg=C["text"], font=sm, anchor="w", justify="left",
                 wraplength=520).pack(side="left", fill="x", expand=True)
        ttk.Button(ban, text="Find it…", command=self.tracker_pick_log).pack(side="right", padx=(8, 0))
        self.al_log_banner, self.al_log_after = ban, top
        tbl = tk.Frame(box, bg=P2)
        tbl.pack(fill="x", pady=(8, 0))
        self.al_table = tbl
        tbl.grid_columnconfigure(1, minsize=300)
        tbl.grid_columnconfigure(2, weight=1)
        for c, t in ((1, "Helper"), (2, "Options"), (3, "Remind")):
            tk.Label(tbl, text=t, bg=P2, fg=C["muted"], font=sm).grid(row=0, column=c, sticky="w" if c < 3 else "",
                                                                       padx=(0, 12), pady=(0, 4))
        r_ = [1]

        def rule():
            tk.Frame(tbl, bg=C["line"], height=1).grid(row=r_[0], column=0, columnspan=5, sticky="ew")
            r_[0] += 1

        def chip(parent, text, var, cmd, tip=None):
            """An option of a helper: a small button, filled when on (as Money Makers' filters)."""
            b = tk.Label(parent, text=text, font=sm, padx=8, pady=2, cursor="hand2", highlightthickness=1)

            def paint(dim=None):
                """Filled when on; while its helper is off, an outline only (it still switches)."""
                if dim is not None:
                    b.dim = dim
                on, dim = bool(var.get()), getattr(b, "dim", False)
                if on and not dim:
                    b.config(bg=C["accent"], fg=C["bg"], highlightbackground=C["accent"])
                else:
                    b.config(bg=P2, fg=C["muted"] if dim else (C["accent"] if on else C["text"]),
                             highlightbackground=C["accent"] if on else C["line"])

            def flip(_e=None):
                var.set(not var.get())
                paint()
                cmd()
            b.bind("<Button-1>", flip)
            b.paint = paint
            b.var = var
            paint()
            if tip:
                Tooltip(b, tip)
            return b

        self.al_chips = {}
        what = {
            "delirium": "END DELIRIUM when you finish a map with Delirium still on (reads your screen)",
            "breach": "a banner when your stored Hiveblood is almost full, and when it's full (reads Client.txt)",
            "ritual": "reads the Ritual counter (0/3 ...) from your screen; reminds you if you leave a map after "
                      "starting its rituals but not finishing them",
            "remnant": "Expedition Remnant Price Checker: each reward in a remnant's book gets its poe.ninja price, by "
                       "itself, beside the runeshapes players rate best for loot",
            "focus": "League Plan: your current goal on the bar, and a short poke in town now and then "
                     "(Overlay ↳ League Plan)",
            "campaign": "Campaign Helper: where you are in the campaign, what's next and what it's worth (reads "
                        "Client.txt)",
            "whispers": "Trade Whisper Watcher: a card over the game when someone whispers to buy an item you listed - "
                        "easy to miss in a busy chat (reads Client.txt; nothing is saved)",
            "desecrate": "Desecration Helper (BETA): at The Well of Souls each revealed option shows its tier (T1 = best "
                         "for that item type) - on only while you're there (reads Client.txt, then your screen)"}
        tests = {"delirium": self.alerts_test_delirium, "breach": lambda: self.breach_alert(test=True),
                 "ritual": self.alerts_test_ritual, "remnant": self.alerts_test_remnant,
                 "focus": lambda: self.ov_intro_setup("focus"), "campaign": lambda: self.camp_route_show(),
                 "whispers": lambda: self.ww_show_test(), "desecrate": self.alerts_test_desecrate}
        names = {"delirium": "Delirium", "breach": "Breach", "ritual": "Ritual", "remnant": "Expedition",
                 "focus": "League Plan", "campaign": "Campaign", "whispers": "Trade whispers",
                 "desecrate": "Desecration (BETA)"}
        # 2.119.0 (UX pass): what each one does, in one gray line under its name (it was only a tooltip)
        blurb = HELPER_BLURBS
        self.al_leave = tk.BooleanVar(value=bool(self.breach_cfg().get("leave_reminder", True)))
        self.al_rleave = tk.BooleanVar(value=bool(self.ritual_cfg().get("leave_reminder", True)))
        self.al_rshow = tk.BooleanVar(value=bool(self.ritual_cfg().get("readout", True)))
        self.al_rfav = tk.BooleanVar(value=bool(self.ritual_cfg().setdefault("favours", True)))
        self.al_rtrib = tk.BooleanVar(value=bool(self.ritual_cfg().setdefault("tribute_reminder", True)))
        self.al_rru = tk.BooleanVar(value=bool(self.remnant_cfg().get("rumours", True)))
        self.al_rtips = tk.BooleanVar(value=bool(self.remnant_cfg().get("tips", True)))
        opts = {
            "remnant": [("Island rumors", self.al_rru, lambda: self.ru_changed(self.al_rru.get()),
                         "On the world map's Uncharted Waters card, each rumor gets the island it leads to and your "
                         "Map Library rank for it. Only in your hideout."),
                        ("Runeshape tips", self.al_rtips, lambda: self.remnant_tips_changed(self.al_rtips.get()),
                         "A small list next to the prices: the runeshapes players rate best for loot (S and A tier).")],
            "ritual": [("On screen", self.al_rshow, lambda: self.ritual_readout_changed(self.al_rshow.get()),
                        "A line over the overlay's bar while you're in a map with Ritual: how many rituals are done and "
                        "your tribute."),
                       ("Favours prices", self.al_rfav, lambda: self.favours_changed(self.al_rfav.get()),
                        "At a Ritual altar's Favours window: poe.ninja's price on each omen and other 1-cell reward. "
                        "Price check one there (your price check key) and it learns its picture."),
                       ("Tribute reminder", self.al_rtrib, self.alerts_tribute_changed,
                        "Close the Favours window with tribute left: a reminder to offer it to "
                        "the King.")]}
        remind = {"breach": (self.al_leave, self.alerts_leave_changed),
                  "ritual": (self.al_rleave, self.alerts_ritual_leave_changed)}
        for group, keys in (("IN MAPS", ("breach", "delirium", "ritual", "remnant")), ("PLAY", ("campaign", "focus")),
                            ("TRADING & MORE", ("whispers", "desecrate"))):
            rule()
            tk.Label(tbl, text=group, bg=P2, fg=C["muted"], font=("Segoe UI", 9, "bold")).grid(
                row=r_[0], column=0, columnspan=5, sticky="w", pady=(8, 2))
            r_[0] += 1
            for key in keys:
                rule()
                r = r_[0]
                on = tk.BooleanVar(value=False)
                sw = ttk.Checkbutton(tbl, variable=on, style=CB, command=lambda k=key: self.alerts_toggle(k))
                sw.grid(row=r, column=0, sticky="w", padx=(0, 12), pady=4)
                cell = tk.Frame(tbl, bg=P2)
                cell.grid(row=r, column=1, sticky="w", padx=(0, 12), pady=4)
                nl = tk.Label(cell, text=names[key], bg=P2, fg=C["text"], font=("Segoe UI", 10, "bold"), anchor="w")
                nl.pack(anchor="w")
                Tooltip(nl, what[key])
                tk.Label(cell, text=blurb[key], bg=P2, fg=C["muted"], font=sm, anchor="w", justify="left",
                         wraplength=320).pack(anchor="w")
                st = tk.Label(cell, text="", bg=P2, fg=C["muted"], font=sm, anchor="w", justify="left",
                              wraplength=320)
                st.pack(anchor="w")                 # (what it's doing now - hidden while it's off)
                dot = tk.Label(cell, text="●", bg=P2, fg=DOT["off"])          # (kept for alerts_refresh; not shown)
                oc = tk.Frame(tbl, bg=P2)
                oc.grid(row=r, column=2, sticky="w", padx=(0, 12))
                mine = []
                for text, var, cmd, tip in opts.get(key, ()):
                    c = chip(oc, text, var, cmd, tip)
                    c.pack(side="left", padx=(0, 8), pady=2)
                    self.al_chips[text] = c
                    mine.append(c)
                if key in remind:
                    rv, rcmd = remind[key]
                    rs = ttk.Checkbutton(tbl, variable=rv, style=CB, command=rcmd)
                    rs.grid(row=r, column=3, padx=(0, 12))
                    Tooltip(rs, "Remind me when I leave the map with it unfinished")
                else:
                    tk.Label(tbl, text="-", bg=P2, fg=C["muted"]).grid(row=r, column=3, padx=(0, 12))
                ttk.Button(tbl, text="Open" if key in ("focus", "campaign") else "Test", command=tests[key],
                           width=6).grid(row=r, column=4, sticky="e")
                r_[0] += 1
                snd = tk.BooleanVar(value=True)
                self.al_rows[key] = {"dot": dot, "on": on, "sound": snd, "status": st, "what": what[key], "note": "",
                                     "row": cell, "switch": sw, "grid": True, "chips": mine}
        self.al_rows["breach"]["on"].set(bool(self.breach_cfg().get("on")))
        self.al_rows["breach"]["sound"].set(bool(self.breach_cfg().get("sound", True)))
        self.al_rows["ritual"]["on"].set(bool(self.ritual_cfg().get("on")))
        self.al_rows["ritual"]["sound"].set(bool(self.ritual_cfg().get("sound", True)))
        # 2.130.0 (feedback): the game's hidden setting that applies your item filter to the Favours window
        # 2.130.4 (feedback: "the text for opening the filter in ritual window is a bad UI+UX design choice"): a
        # plain button with the setting's state beside it (a mark and a word), not orange link text
        frow = tk.Frame(self.al_rows["ritual"]["row"], bg=P2)
        frow.pack(anchor="w", pady=(4, 0))
        fl = ttk.Button(frow, text="Filter in the Ritual window…", command=self.ritual_filter_open)
        fl.pack(side="left")
        Tooltip(fl, "Make your item filter work in the Ritual altar's Favours window (a game setting with no switch "
                    "in its menus) - the app shows where and what to change.")
        fst = tk.Label(frow, text="", bg=P2, fg=C["muted"], font=sm, anchor="w")
        fst.pack(side="left", padx=(8, 0))
        self.al_rfilter_link, self.al_rfilter_state = fl, fst
        self.ritual_filter_state()
        self.al_rows["remnant"]["on"].set(bool(self.remnant_cfg().get("on")))          # 2.37.0
        self.al_rows["desecrate"]["on"].set(bool(self.ws_cfg().get("on")))            # 2.81.0
        from . import campaign as _CP, focus as _F
        self.al_rows["focus"]["on"].set(bool(_F.cfg()["on"]))                          # 2.90.0
        self.al_rows["campaign"]["on"].set(bool(_CP.cfg()["on"]))
        from . import whispers as _W                                                    # 2.98.1
        self.al_rows["whispers"]["on"].set(bool(_W.cfg()["on"]))
        self.al_rows["whispers"]["sound"].set(bool(_W.cfg()["sound"]))
        try:
            from .utilities import DELIRIUM
            self.al_rows["delirium"]["sound"].set(bool(DELIRIUM.get_sound()))
        except Exception:
            buglog.caught()
        # 2.131.0: break reminders - off until turned on
        from . import breaks as _BR
        bc = _BR.cfg()
        brow = tk.Frame(box, bg=P2)
        brow.pack(fill="x", pady=(8, 0))
        self.al_break = tk.BooleanVar(value=bool(bc["on"]))
        bcb = ttk.Checkbutton(brow, text="Break reminders", variable=self.al_break, style=CB,
                              command=lambda: self.break_set("on", bool(self.al_break.get())))
        bcb.pack(side="left")
        tk.Label(brow, text="every", bg=P2, fg=C["text"], font=sm).pack(side="left", padx=(8, 4))
        ev = tk.StringVar(value=f"{bc['every']} min")
        ecb = ttk.Combobox(brow, textvariable=ev, values=[f"{m} min" for m in _BR.EVERY], state="readonly", width=8)
        ecb.pack(side="left")
        ecb.bind("<<ComboboxSelected>>", lambda _e: self.break_set("every", int(ev.get().split()[0])))
        btest = ttk.Button(brow, text="Test", width=6, command=lambda: self.break_check(force=True))
        btest.pack(side="left", padx=(8, 0))
        bi = tk.Label(brow, text="ⓘ", bg=P2, fg=C["muted"], font=sm, cursor="question_arrow")
        bi.pack(side="left", padx=(8, 0))
        tk.Label(box, text="A kind nudge in long sessions (water, stretch, food, sleep), only in your hideout or a town.",
                 bg=P2, fg=C["muted"], font=sm, anchor="w").pack(fill="x")
        Tooltip(bcb, "One small card every so often while you play - never in a map. Off until you turn it on.")
        Tooltip(bi, "The lines rotate; more join the longer you play (a meal at 2 h, fresh air at 4 h, a shower at "
                    "8 h, sleep at 12 h or late at night). Play time is the Session timer's. Nothing is saved or sent.")
        Tooltip(btest, "Shows the next reminder now.")
        self.al_break_every = ecb
        self.topup_row(box, P2, CB)                         # 2.131.0: Top Up Reminders
        self.alerts_refresh()
        return box

    def alerts_toggle(self, key, want=None):
        """On / off for one helper. want=None: what its box in the Alerts panel says. 2.26.0: the timer's Helpers bar
        switches them too (the panel may not even be built then)."""
        rows = getattr(self, "al_rows", None) or {}

        class _Box:                                           # the panel's box, or a stand-in when it isn't built
            def __init__(self, v):
                self.v = v

            def get(self):
                return self.v

            def set(self, v):
                self.v = v
        r = rows.get(key) or {"on": _Box(bool(want)), "note": ""}
        if want is None:
            want = bool(r["on"].get())
        else:
            r["on"].set(bool(want))
        if key == "breach":
            self.breach_cfg()["on"] = want
            save_json("settings.json", SETTINGS)
            if want:
                self.breach_start()
            else:
                self.breach_stop()
        elif key == "ritual":
            self.ritual_cfg()["on"] = want
            save_json("settings.json", SETTINGS)
            err = self.ritual_start() if want else self.ritual_stop()
            r["note"] = err or ""
            if err and want:
                r["on"].set(False)
                self.ritual_cfg()["on"] = False
                save_json("settings.json", SETTINGS)
        elif key == "remnant":                                # 2.37.0
            err = self.remnant_toggle(want)
            r["note"] = err or ""
        elif key == "desecrate":                              # 2.81.0
            err = self.ws_toggle(want)
            r["note"] = err or ""
        elif key == "focus":                                  # 2.90.0
            self.focus_set_on(bool(want))
            self._helper_needs_overlay(want, "League Plan")
        elif key == "campaign":
            self.camp_set_on(bool(want))
            self._helper_needs_overlay(want, "The Campaign Helper")
        elif key == "topup":                                  # 2.131.1: Quick settings switch it too
            self.topup_set(bool(want))
            v = getattr(self, "al_topup", None)
            if v is not None and bool(v.get()) != bool(want):
                v.set(bool(want))
        elif key == "breaks":
            self.break_set("on", bool(want))
            v = getattr(self, "al_break", None)
            if v is not None and bool(v.get()) != bool(want):
                v.set(bool(want))
        elif key == "whispers":                               # 2.98.1
            from . import whispers as _W
            _W.cfg()["on"] = bool(want)
            _W.save()
            if want:
                self.breach_start()                           # (the helpers' Client.txt reader)
            else:
                self.breach_stop()
            self._helper_needs_overlay(want, "The Trade Whisper Watcher")
        else:
            SETTINGS["util_delirium_autostart"] = want       # on = it also starts with the app next time
            save_json("settings.json", SETTINGS)
            err = self.dl_do_start() if want else self.dl_do_stop()
            r["note"] = err or ""
            if err and want:
                r["on"].set(False)
        if rows:
            self.alerts_refresh()
        self.alerts_overlay_redraw()

    def _helper_needs_overlay(self, want, name):
        """2.97.0: Focus and Campaign live on the overlay's bar - switching one on turns the overlay on too."""
        try:
            if want and not self.ov_enabled():
                self.ov_enable(True)
                self._say(f"{name} shows on the overlay, so the overlay is on now.", 6)
        except Exception:
            self.log_error("the overlay")

    # ================================================================ 2.98.1: Trade Whisper Watcher
    def ww_whisper(self, data):
        """A whisper to you (from the log). A trade request while the watcher is active -> the card."""
        from . import whispers as W
        if not W.active():
            return None
        trade = W.parse_trade(data.get("msg"))
        if trade is None:
            return None
        self.ww_last = time.strftime("%H:%M")
        return self.ww_show(data.get("who") or "", trade)

    def ww_show_test(self):
        return self.ww_show("ExampleBuyer", {"item": "Havoc Visage Ancestral Tiara", "price": "90 divine",
                                             "league": "", "tab": "~b/o 90 divine", "left": 3, "top": 5}, test=True)

    def ww_show(self, who, trade, test=False):
        """A card at the top of the game: who wants what, for how much, where it is in your tab. It stays until you
        close it or for its time (Settings: 20 s), several stack; the overlay's own look. Nothing is saved."""
        from . import whispers as W
        from .overlaywin import OverlayWindow, pal
        if not test and not self.ov_enabled():
            return None
        P = pal()
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        Wd = self.ov_px(420)
        cards = [c for c in getattr(self, "ww_cards", []) if c.winfo_exists()]
        while len(cards) >= 3:                                   # at most 3 at once - the oldest goes
            old = cards.pop(0)
            try:
                old.destroy()
            except tk.TclError:
                pass
        y = r[1] + int(r[3] * 0.08) + sum(c.winfo_height() + 8 for c in cards)
        w = OverlayWindow(self.root, "Trade whisper", "💬", (r[0] + (r[2] - Wd) // 2, y, Wd, None), palette=P,
                          lockable=False, follow_game=True, no_activate=True, on_close=None)
        bg = P["bg"]
        body = tk.Frame(w.body, bg=bg, padx=16, pady=8)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=trade.get("item") or "Someone wants to buy an item", bg=bg, fg=P["head"],
                 font=(P["font"], self.ov_font(12), "bold"), anchor="w", justify="left",
                 wraplength=Wd - 40).pack(fill="x")
        if trade.get("price"):
            tk.Label(body, text=f"for {trade['price']}", bg=bg, fg=P["text"], font=(P["font"], self.ov_font(11)),
                     anchor="w").pack(fill="x")
        spot = W.where(trade)
        if spot:
            tk.Label(body, text=spot, bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(9)), anchor="w").pack(fill="x")
        if who:
            tk.Label(body, text=f"from {who}" + ("   (a test)" if test else ""), bg=bg, fg=P["muted"],
                     font=(P["font"], self.ov_font(9)), anchor="w").pack(fill="x", pady=(4, 0))
        w.show()
        cards.append(w)
        self.ww_cards = cards
        secs = int(W.cfg().get("secs") or 20)
        self.root.after(secs * 1000, lambda: w.winfo_exists() and w.destroy())
        if W.cfg().get("sound") and not test:
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                buglog.caught()
        self.alerts_refresh()
        return w

    def alerts_sound_all(self):
        """P2.5: the one Sound switch - every helper's alert sound on or off."""
        self.helpers_sound_set(bool(self.al_sound_all.get()))     # (P4: shared with Quick settings)

    def alerts_sound(self, key):
        r = self.al_rows[key]
        if key == "whispers":
            from . import whispers as _W
            _W.cfg()["sound"] = bool(r["sound"].get())
            _W.save()
            return
        if key in ("breach", "ritual"):
            cfg = {"breach": self.breach_cfg, "ritual": self.ritual_cfg}[key]()
            cfg["sound"] = bool(r["sound"].get())
            save_json("settings.json", SETTINGS)
        else:
            from .utilities import DELIRIUM
            DELIRIUM.set_sound(bool(r["sound"].get()))

    def alerts_leave_changed(self):
        self.breach_cfg()["leave_reminder"] = bool(self.al_leave.get())
        save_json("settings.json", SETTINGS)

    def alerts_tribute_changed(self):
        self.ritual_cfg()["tribute_reminder"] = bool(self.al_rtrib.get())
        save_json("settings.json", SETTINGS)

    def ritual_filter_state(self):
        """The state beside the button: ✓ On / ✗ Off / ? Not found (read from the game's file - that line only)."""
        from . import ritual_filter as RF
        lbl = getattr(self, "al_rfilter_state", None)
        if lbl is None:
            return None
        st, _path = RF.state()
        text, col = {"on": ("✓ On", C.get("good", C["text"])), "off": ("✗ Off", C.get("warn", C["text"])),
                     "missing": ("? Not set", C["muted"]), "nofile": ("? Not found", C["muted"])}[st]
        try:
            lbl.config(text=text, fg=col)
        except tk.TclError:
            pass
        return st

    def ritual_filter_open(self):
        """2.130.0 Filter in the Ritual window: where the game's setting is, whether it's on, and how to turn it on
        (one line to change). 2.130.4: Turn it on changes it for you while the game is closed."""
        from . import ritual_filter as RF
        old = getattr(self, "rf_dlg", None)
        if old is not None:
            try:
                if old.winfo_exists():
                    old.destroy()
            except tk.TclError:
                pass
        P2 = C["panel2"]
        dlg = tk.Toplevel(self.root)
        dlg.title("Filter in the Ritual window")
        dlg.configure(bg=P2, padx=16, pady=16)
        dlg.transient(self.dlg_parent())
        dlg.resizable(False, False)
        self.rf_dlg = dlg
        top = tk.Frame(dlg, bg=P2)
        top.pack(fill="x")
        tk.Label(top, text="Make your item filter hide junk in the Ritual altar's Favours window.", bg=P2,
                 fg=C["text"], font=("Segoe UI", 10), anchor="w").pack(side="left")
        tip = tk.Label(top, text="ⓘ", bg=P2, fg=C["muted"], font=("Segoe UI", 10), cursor="question_arrow")
        tip.pack(side="left", padx=(8, 0))
        Tooltip(tip, f"A game setting with no switch in its menus: {RF.KEY} in {RF.FILE}. {RF.CREDIT}. The app reads "
                     "that line; Turn it on changes it (only that line, only while the game is closed), or follow the "
                     "steps to change it yourself.")
        status = tk.Label(dlg, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 10, "bold"), anchor="w",
                          justify="left", wraplength=460)
        status.pack(fill="x", pady=(8, 2))
        where = tk.Label(dlg, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left",
                         wraplength=460)
        where.pack(fill="x")
        steps = ("1.  Close the game (it rewrites this file when it closes).",
                 f"2.  Open folder (where your item filters are), then open {RF.FILE} in Notepad.",
                 "3.  Use Edit › Find in Notepad and paste (Copy line puts it on your clipboard).",
                 "4.  Change false to true, then save.",
                 "5.  Start the game and open a Ritual altar's Favours window.")
        box = tk.Frame(dlg, bg=P2)
        box.pack(fill="x", pady=(8, 4))
        for s_ in steps:
            tk.Label(box, text=s_, bg=P2, fg=C["text"], font=("Segoe UI", 10), anchor="w").pack(fill="x", pady=1)
        said = tk.Label(dlg, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w")
        said.pack(fill="x", pady=(4, 0))

        def check():
            st, path = RF.state()
            text, col = {"on": ("✓ On - your filter applies in the Favours window.", C.get("good", C["text"])),
                         "off": ("✗ Off - follow the steps below.", C.get("warn", C["text"])),
                         "missing": ("? The line isn't in your file - start the game once, close it, check again.",
                                     C["muted"]),
                         "nofile": ("? The file isn't there yet - start the game once, close it, check again.",
                                    C["muted"])}[st]
            status.config(text=text, fg=col)
            where.config(text=RF.shown(path))          # (no Windows user name on screen)
            self.ritual_filter_state()
            try:                                       # (grayed out unless it's off - nothing to turn on)
                if wait.get("job") is None:
                    on_btn.state(["!disabled"] if st == "off" else ["disabled"])
            except (NameError, tk.TclError):
                pass
            return st, path

        def open_folder():
            _st, path = RF.state()
            try:
                if sys.platform == "win32":
                    import subprocess
                    if os.path.isfile(path):
                        subprocess.Popen(["explorer", "/select,", path])
                    else:
                        os.startfile(os.path.dirname(path) if os.path.isdir(os.path.dirname(path))
                                     else RF.documents())
                    said.config(text="Opened the folder.")
                else:
                    said.config(text="Opening folders works on Windows.")
            except Exception:
                buglog.caught()
                said.config(text="Couldn't open the folder - it's shown above.")

        def copy_line():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(f"{RF.KEY}=false")
                self.own_clip = f"{RF.KEY}=false"
                said.config(text=f"Copied: {RF.KEY}=false - paste it into Notepad's Find.")
            except tk.TclError:
                said.config(text="Couldn't copy - type it: " + RF.KEY)
        wait = {"job": None, "gone": None, "mt": None}

        def file_mtime(path):
            try:
                return os.path.getmtime(path)
            except OSError:
                return None

        def turn_on():
            """2.130.4 (feedback): the game must be fully closed (it saves this file as it closes) - then the one
            line is changed, and you're told when to start the game again."""
            if not dlg.winfo_exists():
                return
            _st, path = RF.state()
            if game_rect() is not None:
                wait["gone"], wait["mt"] = None, None
                said.config(text="Close the game fully (not just to the character screen) - waiting for it…",
                            fg=C.get("warn", C["text"]))
                on_btn.state(["disabled"])
                wait["job"] = dlg.after(1000, turn_on)
                return
            now, mt = time.time(), file_mtime(path)
            if wait["gone"] is None or mt != wait["mt"]:          # just closed (or still saving): wait 4 s quiet
                wait["gone"], wait["mt"] = now, mt
            if now - wait["gone"] < 4:
                said.config(text="The game is closing - one moment…", fg=C["muted"])
                wait["job"] = dlg.after(1000, turn_on)
                return
            ok, note = RF.turn_on(path, P("backups"))
            wait["job"] = None
            said.config(text=(note + " You can start the game again.") if ok else note,
                        fg=C.get("good", C["text"]) if ok else C.get("warn", C["text"]))
            check()
        btns = tk.Frame(dlg, bg=P2)
        btns.pack(fill="x", pady=(12, 0))
        on_btn = ttk.Button(btns, text="Turn it on", style="Primary.TButton", command=turn_on)
        on_btn.pack(side="left")
        Tooltip(on_btn, "Changes that one line from false to true - nothing else in the file. The game must be closed; "
                        "a copy of the file is kept in the app's data folder first.")
        ttk.Button(btns, text="Open folder", command=open_folder).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Copy line", command=copy_line).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Check again", command=check).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Close", command=dlg.destroy).pack(side="right")
        dlg.bind("<Escape>", lambda _e: dlg.destroy())
        check()
        try:
            from .style import center_over
            center_over(dlg, self.dlg_parent())
        except Exception:
            buglog.caught()
        dlg.rf_check, dlg.rf_open, dlg.rf_copy, dlg.rf_said, dlg.rf_status = check, open_folder, copy_line, said, status
        dlg.rf_on, dlg.rf_on_btn = turn_on, on_btn
        return dlg

    def alerts_ritual_leave_changed(self):
        self.ritual_cfg()["leave_reminder"] = bool(self.al_rleave.get())
        save_json("settings.json", SETTINGS)

    def alerts_test_desecrate(self):
        r = self.al_rows["desecrate"]
        r["note"] = self.ws_test()
        self.alerts_refresh()

    def alerts_test_remnant(self):
        r = self.al_rows["remnant"]
        r["note"] = self.remnant_test()
        self.alerts_refresh()

    def alerts_test_ritual(self):
        self.breach_alert(test=True, level="ritual", sub="1 of 3 done (a test)")

    # ---- Ritual helper
    def ritual_start(self):
        from . import features as FEAT
        if not FEAT.on("overlay"):                     # 2.131.0: the Game Overlay is off (Features)
            return
        from .utilities import RITUAL
        err = RITUAL.start()
        if not err and self.br_reader is None:
            self.breach_start()                         # to see you leave a map
        self.favours_sync()                             # 2.128.0: Favours prices
        self.root.after(1500, self.alerts_refresh)
        return err

    def ritual_stop(self):
        from .utilities import RITUAL
        RITUAL.stop()
        self.rt_map = None
        self.rt_done = False
        self.favours_sync()
        if not self.log_wanted():
            self.br_reader = None
        self.alerts_refresh()
        return None

    def ritual_status(self):
        from .utilities import RITUAL
        if not self.ritual_cfg().get("on"):
            return "off"
        if not RITUAL.running() or RITUAL.state == "error":
            return "warn"
        return "on"


    def alerts_test_delirium(self):
        err = self.dl_do_test()
        r = self.al_rows["delirium"]
        r["note"] = err or "The END DELIRIUM banner shows for 5 seconds."
        self.alerts_refresh()

    def alert_states(self):
        """{"delirium": "on" | "off" | "warn", "breach": ...}: the panel's dots and the timer's bar.
        warn = switched on but not working (the Delirium helper hit an error; Client.txt not found)."""
        try:
            from .utilities import DELIRIUM
            run = DELIRIUM.running()
            d = "off" if not run else "warn" if run == "mine" and DELIRIUM.state == "error" else "on"
        except Exception:
            d = "off"
        b = self.breach_status()
        return {"delirium": d, "breach": "off" if b is False else "warn" if b == "warn" and self.br_reader is None
                else "on", "ritual": self.ritual_status(), "remnant": self.remnant_status(),
                "desecrate": self.ws_status()} | self._alert_states_more()

    def _alert_states_more(self):
        from . import campaign as _CP, focus as _F                                # 2.90.0
        from . import whispers as _W
        w = "off" if not _W.cfg()["on"] else ("on" if _W.active() and getattr(self, "br_reader", None) is not None
                                              else "warn" if getattr(self, "br_reader", None) is None else "off")
        from . import topup as _TU, breaks as _BR                                   # 2.131.1
        return {"focus": "on" if _F.cfg()["on"] else "off", "campaign": "on" if _CP.cfg()["on"] else "off",
                "whispers": w, "topup": "on" if _TU.cfg().get("on") else "off",
                "breaks": "on" if _BR.cfg().get("on") else "off"}

    def alerts_refresh(self):
        """Every 2 s (util_refresh) and after a change: dots, checkboxes and status lines."""
        rows = getattr(self, "al_rows", None)
        if not rows:
            return
        states = self.alert_states()
        try:
            from .utilities import DELIRIUM, STATES
            run = DELIRIUM.running()
            rows["delirium"]["on"].set(bool(run))
            if run == "other":
                dtxt = "On (the standalone PoE2DeliriumAlert.exe)"
            elif run == "mine":
                dtxt = "On - " + STATES.get(DELIRIUM.state, DELIRIUM.state or "starting…")
            elif DELIRIUM.lines and DELIRIUM.lines[-1].startswith("error"):
                dtxt = "It stopped: " + DELIRIUM.lines[-1][6:]
            else:
                dtxt = rows["delirium"]["what"]
        except Exception:
            dtxt = rows["delirium"]["what"]
        if rows["delirium"]["note"]:
            dtxt, rows["delirium"]["note"] = rows["delirium"]["note"], ""
        if not self.breach_cfg().get("on"):
            btxt = rows["breach"]["what"]
        elif self.br_reader is None:
            btxt = self.br_note or "On - looking for Client.txt…"
        elif self.br_win is not None:
            btxt = f"Warned at {time.strftime('%H:%M', time.localtime(max(self.br_last.values() or [time.time()])))}"
        elif self.breach_cfg().get("pending"):
            btxt = ("On - Hiveblood is waiting to be spent" + (": you'll be reminded when you leave the map"
                                                              if self.breach_cfg().get("leave_reminder", True) else ""))
        else:
            btxt = "On - watching for the game's Hiveblood warnings"
        rtxt = self.ritual_text(rows["ritual"])
        mtxt = rows["remnant"]["note"] or self.remnant_text(rows["remnant"])
        rows["remnant"]["note"] = ""
        rows["remnant"]["on"].set(bool(self.remnant_cfg().get("on")))
        wtxt = rows["desecrate"]["note"] or self.ws_text(rows["desecrate"])         # 2.81.0
        rows["desecrate"]["note"] = ""
        rows["desecrate"]["on"].set(bool(self.ws_cfg().get("on")))
        from . import campaign as _CP, focus as _F                                # 2.90.0
        rows["focus"]["on"].set(bool(_F.cfg()["on"]))
        rows["campaign"]["on"].set(bool(_CP.cfg()["on"]))
        ftxt = ("On - " + (self.focus_line()[0] or "pick a goal in Overlay ↳ League Plan")) if _F.cfg()["on"] else rows["focus"]["what"]
        ctxt = ("On - " + (_CP.line_text() or "waits for a campaign zone in the game's log")) if _CP.cfg()["on"] else rows["campaign"]["what"]
        from . import whispers as _W                                              # 2.98.1
        rows["whispers"]["on"].set(bool(_W.cfg()["on"]))
        if not _W.cfg()["on"]:
            vtxt = rows["whispers"]["what"]
        elif getattr(self, "br_reader", None) is None:
            vtxt = self.br_note or "On - looking for Client.txt…"
        else:
            last = getattr(self, "ww_last", None)
            vtxt = "On - watching your whispers" + (f" (last trade whisper {last})" if last else "")
        for k, txt in (("delirium", dtxt), ("breach", btxt), ("ritual", rtxt), ("remnant", mtxt), ("desecrate", wtxt),
                       ("focus", ftxt), ("campaign", ctxt), ("whispers", vtxt)):
            st = states[k]
            lbl = rows[k]["status"]
            if rows[k].get("grid"):                 # 2.112.0: one short line under the name
                if st == "off" and txt == rows[k]["what"]:
                    txt = ""                        # 2.119.0: off - the switch says so; the gray line says what it does
                elif txt.startswith("On - "):
                    txt = txt[5:6].upper() + txt[6:]
                try:
                    if txt and not lbl.winfo_manager():
                        lbl.pack(anchor="w")
                    elif not txt and lbl.winfo_manager():
                        lbl.pack_forget()
                except tk.TclError:
                    pass
            else:
                show = st != "off" or txt != rows[k]["what"]
                try:
                    if show and not lbl.winfo_manager():
                        lbl.pack(fill="x", padx=(24, 8), after=rows[k]["row"])
                    elif not show and lbl.winfo_manager():
                        lbl.pack_forget()
                except tk.TclError:
                    pass
            rows[k]["dot"].config(fg=DOT[st])
            for c in rows[k].get("chips", ()):
                try:
                    c.paint(dim=st == "off")
                except tk.TclError:
                    pass
            rows[k]["status"].config(text=txt, fg=C["red"] if st == "warn" else C["green"] if st == "on" else C["muted"])
        ban = getattr(self, "al_log_banner", None)            # 2.119.0: Client.txt not found - one banner
        if ban is not None:
            want = getattr(self, "br_reader", None) is None and bool(self.br_note)
            try:
                if want and not ban.winfo_manager():
                    ban.pack(fill="x", pady=(8, 0), after=self.al_log_after)
                elif not want and ban.winfo_manager():
                    ban.pack_forget()
            except tk.TclError:
                pass

    def ritual_text(self, row):
        from .utilities import RITUAL
        if row["note"]:
            txt, row["note"] = row["note"], ""
            return txt
        if not self.ritual_cfg().get("on"):
            return row["what"]
        if not RITUAL.running():
            last = RITUAL.lines[-1] if RITUAL.lines else ""
            return "It stopped" + (": " + last[6:] if last.startswith("error") else "") + " - switch it off and on."
        if RITUAL.state == "nogame":
            return "On - waiting for the game window"
        if RITUAL.state == "error":
            return "Screen capture problem: " + (RITUAL.lines[-1] if RITUAL.lines else "")
        if RITUAL.seen == "ok" and RITUAL.count:
            d, t = RITUAL.count
            return f"On - this map: {d} of {t} rituals done" + (" ✔" if d >= t else "")
        if RITUAL.seen == "unread":
            return ("On - the Ritual counter is on screen but couldn't be read. Make a problem report "
                    "(Settings > Advanced) while it shows so it can be fixed.")
        return "On - watching for the Ritual counter (it shows in maps with Ritual)"

    def ritual_seen(self):
        """Every second: remember the counter while you're in a map."""
        from .utilities import RITUAL
        if RITUAL.seen == "ok" and RITUAL.count and self.br_area in ("map", None):
            self.rt_map = RITUAL.count
        # 2.129.3 (feedback: the line said 1 of 3, it was 3 of 3 - the counter isn't always on screen): Map
        # Content's Ritual icon has its green tick - every ritual in this map is done
        if getattr(RITUAL, "content", None) == "done" and self.br_area in ("map", None):
            self.rt_done = True
            if self.rt_map and self.rt_map[0] < self.rt_map[1]:
                self.rt_map = (self.rt_map[1], self.rt_map[1])
        try:                                                 # 2.129.4: a Ritual map - the bar out of captures while
            self.overlay_capture_sync()                      # its rituals are left (the watcher sees the counter)
        except Exception:
            buglog.caught()
        # 2.129.0 (feedback: "still isn't reminding me when I leave the map"): the Ritual helper is on but its
        # watcher isn't running (its log: it was told to stop the moment it started) - start it again, at most
        # every 30 s; the app's log says so each time
        if self.ritual_cfg().get("on") and not RITUAL.running() and RITUAL.state != "error":
            now = time.time()
            if now - getattr(self, "_rt_restart_at", 0) > 30:
                self._rt_restart_at = now
                buglog.record("debug", "Ritual watcher wasn't running - started again")
                RITUAL.start()
        self.ritual_readout_sync()

    def alerts_overlay_redraw(self):
        try:
            self.tracker_helpers_paint()                           # 2.49.0: the bar stands on its own
        except Exception:
            buglog.caught()
        if getattr(self, "tk_overlay", None) is not None:
            try:
                self.tracker_overlay_draw(self.tracker_numbers())
            except Exception:
                buglog.caught()

    # ================================================================ Breach: following Client.txt
    def breach_start(self):
        """Follow Client.txt from its end (the Session tracker's file, or the one picked there)."""
        self.alerts_init()
        tc = getattr(self, "tracker_cfg", None)
        path = find_log(tc().get("log_path") if tc else None)
        if not path:
            self.br_reader = None
            self.br_note = "On - waiting for Client.txt (see the note above)"     # 2.119.0: the banner says why
        else:
            self.br_reader = LogReader(path)
            tail = self.br_reader.start()             # only what the game writes from now on
            self.br_note = ""
            last = next((d for k, _t, d in reversed(tail or []) if k == "area"), None)
            if last is not None:                      # 2.104.1 (feedback: Island Rumors never showed): started in
                try:                                  # your hideout, the helpers knew only after the next area
                    self.expedition_area(last.get("area"), gl_area_kind(
                        last.get("area"), last.get("seed"), last.get("level", 0)))
                    # 2.125.7 (feedback: turned on while at the Well, nothing showed): the Desecration Helper too
                    self.ws_area(last.get("area"))
                    i = next((n for n, (k, _t, _d) in enumerate(tail) if _d is last), None)
                    scene = next((d for k, _t, d in (tail[i:] if i is not None else []) if k == "scene"), None)
                    if scene is not None:
                        self.ws_scene(scene.get("name"))
                except Exception:
                    self.log_error("the area helpers")
        if not self._br_ticking:
            self._br_ticking = True
            self.root.after(1000, self.breach_tick)
        self.alerts_refresh()

    def breach_stop(self):
        if not self.log_wanted():
            self.br_reader = None
        self.breach_dismiss()
        self.alerts_refresh()

    def breach_tick(self):
        try:
            if self.ritual_cfg().get("on"):
                self.ritual_seen()
            if self.log_wanted():
                if self.br_reader is None:
                    self.br_ticks += 1
                    if self.br_ticks % RETRY_TICKS == 0:
                        self.breach_start()
                else:
                    for kind, _ts, data in self.br_reader.poll():
                        if kind == "breach" and "hiveblood" in data["text"].lower() and \
                                self.breach_cfg().get("on"):
                            self.breach_set_pending(breach_level(data["text"]))
                            self.breach_alert(text=data["text"])
                        elif kind == "whisper":
                            self.ww_whisper(data)                  # 2.98.1: Trade Whisper Watcher
                        elif kind == "brequel_tree":
                            self.breach_set_pending(None)          # spent (the tree was opened)
                            self.breach_dismiss()
                        elif kind == "login":
                            self.br_relog = True             # 2.130.2: the character screen (any character)
                        elif kind == "scene":
                            try:
                                self.ws_scene(data.get("name"))      # 2.125.7: the Well by its name too
                            except Exception:
                                self.log_error("the Desecration Helper")
                        elif kind == "area":
                            try:
                                self.ws_area(data.get("area"))        # 2.81.0: the Desecration Helper
                                self.expedition_area(data.get("area"), gl_area_kind(      # 2.83.0: Remnant's places,
                                    data.get("area"), data.get("seed"), data.get("level", 0)))  # Island Rumors
                            except Exception:
                                self.log_error("the area helpers")
                            self.breach_area(gl_area_kind(data.get("area"), data.get("seed"), data.get("level", 0)),
                                             (data.get("area"), data.get("seed")))
        except Exception:
            self.log_error("breach alert")
        if self.log_wanted():
            self.root.after(1000, self.breach_tick)
        else:
            self._br_ticking = False

    def breach_set_pending(self, level):
        cfg = self.breach_cfg()
        if level == "almost" and cfg.get("pending") == "full":
            return
        if cfg.get("pending") != level:
            cfg["pending"] = level
            save_json("settings.json", SETTINGS)

    def breach_area(self, kind, where=None):
        """2.11.0: leaving a map (to your hideout or a town) with Hiveblood still waiting -> one reminder per exit,
        every exit, until the Genesis Tree has been opened."""
        before, self.br_area = self.br_area, kind
        if before != kind:
            buglog.debug("area", f"{before} -> {kind}")     # 2.129.3: kinds only (map, hideout, town), no names
        try:
            self.fl_area(kind, where, before)                # 2.45.0: the Strat Tracker counts its runs
        except Exception:
            self.log_error("Strat Tracker run counting")
        cfg = self.breach_cfg()
        left = before == "map" and kind in ("hideout", "town")
        relog, self.br_relog = getattr(self, "br_relog", False), False
        if left and relog:          # 2.130.2 (feedback): out through the character screen (died, switched character,
            buglog.debug("leave check", "skipped: came back through the character screen")   # logged out) - the
            left = False            # map is still there to go back to; no reminder for leaving it
        if left and cfg.get("on") and cfg.get("pending") and cfg.get("leave_reminder", True):
            self.breach_alert(level="leave")
        rc, got = self.ritual_cfg(), self.rt_map            # 2.14.0: rituals left undone in the map you just left
        if left and rc.get("on"):                           # 2.129.3 (feedback: 2 of 3 and no reminder): the log says
            buglog.debug("Ritual leave check", f"count {got}, all done {getattr(self, 'rt_done', False)}, "   # why
                                               f"reminder {'on' if rc.get('leave_reminder', True) else 'off'}")
        # only when you started them (2.15.0: 0 done = you chose to skip Ritual in this map)
        if (left and rc.get("on") and rc.get("leave_reminder", True) and got and 0 < got[0] < got[1]
                and not getattr(self, "rt_done", False)):         # (2.129.3: Map Content says all done)
            self.root.after(9000 if cfg.get("on") and cfg.get("pending") else 0,
                            lambda g=got: self.breach_alert(level="ritual", sub=f"{g[0]} of {g[1]} done - go back "
                                                                                 f"through your portal"))
        self.topup_visit()                                   # 2.131.0: Top Up may remind once a visit
        if kind in ("hideout", "town") and before != kind:
            self.break_check()                               # 2.131.0: break reminders - in hideout / town only
        if kind == "map" and before != "map":
            # a new map: its own count. 2.40.0: back into the SAME map (same area and seed - through your portal)
            # keeps it, so a quick in-and-out still reminds you
            if where is None or where != getattr(self, "rt_where", None):
                self.rt_map = None
                self.rt_done = False
                try:
                    from .utilities import RITUAL
                    RITUAL.content = None              # (the last map's tick isn't this one's)
                except Exception:
                    buglog.caught()
            self.rt_where = where

    # ================================================================ Breach: the banner
    def breach_alert(self, text="Stored Hiveblood is almost at the maximum!", test=False, level=None, sub=None):
        self.alerts_init()
        from . import features as FEAT
        if not test and not FEAT.on("overlay"):           # 2.131.0: the Game Overlay is off (Features)
            return
        level = level or breach_level(text)
        now = time.time()
        if not test:
            if level not in ("leave", "ritual", "tribute") and now - self.br_last.get(level, 0) < REPEAT_SECS:
                return
            try:
                from .overlaywin import foreground_ok        # only over the game (Settings: "only while it's in front")
                if not foreground_ok():
                    # 2.129.3 (feedback: left a map at 2 of 3, no reminder): a reminder waits (up to a minute) for
                    # the game to be in front again - a screenshot tool or another window had it
                    tries = getattr(self, "_alert_wait", {}).get(level, 0)
                    if level in ("leave", "ritual", "tribute") and tries < 60:
                        self.__dict__.setdefault("_alert_wait", {})[level] = tries + 1
                        self.root.after(1000, lambda: self.breach_alert(text, level=level, sub=sub))
                    else:
                        getattr(self, "_alert_wait", {}).pop(level, None)
                        buglog.debug("alert not shown", f"{level}: the game wasn't the window in front")
                    return
                getattr(self, "_alert_wait", {}).pop(level, None)
            except Exception:
                buglog.caught()
        self.br_last[level] = now
        if level == "full":
            self.br_last["almost"] = now                     # "almost" right after "full" adds nothing
        self.breach_dismiss()
        title, small_txt, mark, color = LEVELS[level]
        small_txt = sub or small_txt
        from . import alertcard
        win = alertcard.show(self.root, title, small_txt, color=color, mark=mark,
                             secs=5 if test else BANNER_SECS.get(level, 8), game=game_rect(),
                             tag="Ritual" if level in ("ritual", "tribute") else "Breach",
                             rank=0 if level in ("ritual", "tribute") else 1, on_close=lambda: self.br_win is win and self.breach_dismiss())
        self.br_win, self.br_level = win, level
        if (self.ritual_cfg() if level == "ritual" else self.breach_cfg()).get("sound", True):
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONHAND if level == "full" else winsound.MB_ICONEXCLAMATION)
            except Exception:
                self.root.bell()
        self.alerts_refresh()
        self.alerts_overlay_redraw()

    # ---------------------------------------------------------------- 2.131.0 break reminders
    def break_played(self):
        """Seconds played: the Session timer's when it runs, otherwise since this app run's first area."""
        s = getattr(self, "tk_session", None)
        if s is not None and not getattr(s, "ended", False):
            try:
                return float(s.elapsed())
            except Exception:
                buglog.caught()
        start = self.__dict__.setdefault("_play_start", time.time())
        return time.time() - start

    def break_check(self, force=False):
        from . import breaks as BR
        c = BR.cfg()
        if not c.get("on") and not force:
            return None
        played = self.break_played()
        st = self.__dict__.setdefault("_break", {"last": 0.0, "n": 0})
        if not force and not BR.due(played, st["last"], c["every"]):
            return None
        line, st["n"] = BR.next_line(played / 3600.0, st["n"])
        st["last"] = played
        from . import alertcard
        try:
            from .overlaywin import foreground_ok
            if not force and not foreground_ok():
                st["last"] = played - c["every"] * 60     # (not in front: the next hideout / town visit)
                return None
        except Exception:
            buglog.caught()
        self.break_win = alertcard.show(self.root, line, BR.played_text(played), color="#7fd9a0", mark="♥", secs=10,
                                        game=game_rect(), tag="Breaks", rank=4)
        return line

    def break_set(self, key, value):
        from . import breaks as BR
        BR.cfg()[key] = value
        save_json("settings.json", SETTINGS)
        if key == "on" and value:
            self.__dict__["_break"] = {"last": self.break_played(), "n": 0}     # (counted from now)

    def alert_card_test(self):
        """Settings: a sample card where and how big alerts will show."""
        self.breach_alert(test=True, level="ritual", sub="A sample - this is where alerts show")

    def alert_card_set(self, key, value):
        from . import alertcard
        alertcard.cfg()[key] = value
        save_json("settings.json", SETTINGS)
        self.alert_card_test()

    def breach_dismiss(self):
        w, self.br_win = getattr(self, "br_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass
            self.alerts_refresh()

    def breach_status(self):
        """False = off, True = watching, "warn" = a banner is up or Client.txt isn't found."""
        if not self.breach_cfg().get("on"):
            return False
        if getattr(self, "br_win", None) is not None or getattr(self, "br_reader", None) is None:
            return "warn"
        return True
