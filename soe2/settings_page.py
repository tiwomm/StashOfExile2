"""Settings (2.117.0: out of app.py - the window, its tabs and every switch on them; split as the app grew).

The App mixes this in (app.py: class App(..., SettingsPage)). Methods only - state lives on the App.
Part of StashOfExile2 (see the launcher's VERSION HISTORY)."""
import os
import time
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from . import buglog
from .config import (
    AGE_OPTIONS, APP_VERSION, pretty_version, DATA_DIR, P,
    save_json, SETTINGS, STATUS_OPTIONS, DEFAULTS,
)
from .net import PACES
from .style import C, MONO, SegBook, KeyCapture, Tooltip
from .chrome import section as chrome_section


class SettingsPage:
    """Settings › every tab, and their handlers."""

    def build_pc_settings(self, section):
        """2.59.0: every price check setting in one place (it was spread over the Price checks toolbar, General, the
        Stash tab row and Wealth). Changes save at once."""
        from .pricefmt import PRICE_UNITS
        P2 = C["panel2"]
        self.pc_vars()
        lab = dict(bg=P2, fg=C["text"])

        def combo(row, var, values, cmd, width):
            cb = ttk.Combobox(row, textvariable=var, values=values, state="readonly", width=width)
            cb.bind("<<ComboboxSelected>>", lambda e: (cmd(), self.root.after(20, self.root.focus_set)))
            return cb

        # 2.113.1 (feedback: Hotkeys was the wrong place): the card over the game - the same switch as Price Checks' header
        row = section("Price checking", "Over the game", "Your price check key shows the price in a card over the game "
                                                          "instead of bringing the app forward. It takes the overlay's "
                                                          "Style; drag and resize it - it remembers. Price Checks still "
                                                          "gets every item.")
        ttk.Checkbutton(row, text="Show price checks over the game", variable=self.pc_pop_var(),
                        style="Card.TCheckbutton", command=self.pc_pop_set).pack(side="left")
        self.pc_set_vars = getattr(self, "pc_set_vars", None) or {}
        self.pc_set_vars["pc_popup"] = self.pc_pop_var()
        # 2.116.0 (P10): the price check key's switches - here, with the card over the game (they were at the
        # bottom of Settings › Hotkeys)
        row = section("Price checking", "Your price check key", "Hover an item in game and press it (Ctrl+D - set it "
                                                                "on Keys): the game copies it once and Price Checks "
                                                                "shows it. Ctrl+Alt+C adds it to Bulk Pricing instead.")
        for k, label in (("pc_ctrl_c", "It opens Price Checks"),
                         ("pc_front", "Bring the app to the front"), ("pc_art", "Show the items' pictures")):
            v = tk.BooleanVar(value=bool(SETTINGS.get(k, True)))
            cmd = (lambda k=k, v=v: (SETTINGS.__setitem__(k, bool(v.get())), save_json("settings.json", SETTINGS)))
            self.pc_set_vars[k] = v
            ttk.Checkbutton(row, text=label, variable=v, style="Card.TCheckbutton", command=cmd).pack(side="left", padx=(0, 16))
        row = section("Price checking", "Valuable items", "A mod is valuable when the cheapest listings with it cost "
                                                           "at least this much. Valuable items are green in the list, and "
                                                           "can play a sound when they're priced.")
        tk.Label(row, text="Valuable mod from", **lab).pack(side="left", padx=(0, 8))
        sp = ttk.Spinbox(row, from_=0.05, to=500, increment=0.25, width=6, textvariable=self.good_var, command=self.on_good)
        sp.pack(side="left")
        sp.bind("<Return>", lambda e: self.on_good())
        sp.bind("<FocusOut>", lambda e: self.on_good())
        tk.Label(row, text="div", **lab).pack(side="left", padx=(4, 16))
        ttk.Checkbutton(row, text="Sound", variable=self.snd_var, command=self.on_toggles).pack(side="left")
        row = section("Price checking", "Listings to price from", "Which trade listings count. Older listings are often "
                                                                   "stale or from players who are gone. New items use a "
                                                                   "change at once; Re-price all refreshes the rest.")
        tk.Label(row, text="Listings", **lab).pack(side="left", padx=(0, 8))
        combo(row, self.status_var, [l for l, _ in STATUS_OPTIONS], self.on_listing_rules, 22).pack(side="left")
        tk.Label(row, text="Listed within", **lab).pack(side="left", padx=(16, 8))
        combo(row, self.age_var, [a[0] for a in AGE_OPTIONS], self.on_listing_rules, 10).pack(side="left")
        row = section("Price checking", "Skip cheap items", "Bulk Pricing doesn't search an item when every mod it would "
                                                          "search sells for under this in the Mod book's own data and "
                                                          "none is rated High; with only a few listings to go on it's "
                                                          "marked \"check by hand\" instead. Price Checks always search.")
        self.build_floor_settings(row)                                                           # 2.96.0
        row = section("Price checking", "Prices", "The currency every price is shown in (Price Checks, Bulk Pricing, Wealth, Market "
                                                  "Insights, the timer).")
        tk.Label(row, text="Prices in", **lab).pack(side="left", padx=(0, 8))
        combo(row, self.unit_var, [t for _k, t in PRICE_UNITS], self.on_price_unit, 22).pack(side="left")
        ttk.Checkbutton(row, text="Copy an item's name when I click it", variable=self.copy_var,
                        command=self.on_toggles).pack(side="left", padx=(16, 0))
        row = section("Price checking", "Account", "Your account name as the trade site shows it, like Name#1234. Read "
                                                   "tab (Stash tab) and Wealth use it to find your public tabs.")
        self.set_anchors["account"] = row.master
        tk.Label(row, text="Account", **lab).pack(side="left", padx=(0, 8))
        e = ttk.Entry(row, textvariable=self.acc_var, width=26)
        e.pack(side="left")
        e.bind("<Return>", lambda ev: self.root.focus_set())

    def build_fine_tuning(self, row, keys=None, defaults=True):
        """The fine-tuning rows for `keys` (all when None); defaults: the Defaults button (for those rows)."""
        P2 = C["panel2"]
        g = tk.Frame(row, bg=P2)
        g.pack(fill="x")
        self.fine_vars = getattr(self, "fine_vars", None) or {}
        spec = [f for f in self.FINE if keys is None or f[0] in keys]
        for r, (key, name, kind, lo, hi, step, note) in enumerate(spec):
            tk.Label(g, text=name, bg=P2, fg=C["text"], anchor="w").grid(row=r, column=0, sticky="w", padx=(0, 12), pady=2)
            if kind == "bool":
                v = tk.BooleanVar(value=bool(SETTINGS.get(key, DEFAULTS[key])))
                ttk.Checkbutton(g, variable=v, command=lambda k=key: self.on_fine(k)).grid(row=r, column=1, sticky="w")
            else:
                cur = SETTINGS.get(key, DEFAULTS[key])
                v = tk.StringVar(value=str(round(float(cur) * 100)) if kind == "pct" else str(cur))
                sp = ttk.Spinbox(g, from_=lo, to=hi, increment=step, width=6, textvariable=v,
                                 command=lambda k=key: self.on_fine(k))
                sp.grid(row=r, column=1, sticky="w")
                sp.bind("<FocusOut>", lambda e, k=key: self.on_fine(k))
                sp.bind("<Return>", lambda e, k=key: self.on_fine(k))
            tk.Label(g, text=note, bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w").grid(row=r, column=2, sticky="w",
                                                                                              padx=(8, 0))
            self.fine_vars[key] = v
        if defaults:
            ttk.Button(row.master, text="Defaults", style="Quiet.TButton",
                       command=lambda: self.fine_defaults([f[0] for f in spec])).pack(anchor="w", pady=(8, 0))

    def on_fine(self, key):
        spec = next(f for f in self.FINE if f[0] == key)
        _k, _n, kind, lo, hi, _s, _w = spec
        v = self.fine_vars[key]
        if kind == "bool":
            SETTINGS[key] = bool(v.get())
        else:
            try:
                n = max(lo, min(hi, float(v.get())))
            except ValueError:
                return
            SETTINGS[key] = round(n / 100, 2) if kind == "pct" else int(n)
            v.set(str(int(n)))
        save_json("settings.json", SETTINGS)

    def fine_defaults(self, keys=None):
        for key, _n, kind, *_r in self.FINE:
            if keys is not None and key not in keys:
                continue
            d = DEFAULTS[key]
            self.fine_vars[key].set(bool(d) if kind == "bool" else str(round(d * 100)) if kind == "pct" else str(d))
            SETTINGS[key] = d
        save_json("settings.json", SETTINGS)

    # ---------------- the Settings window (League and Pace moved here from the old header bars)
    def build_settings(self, body):
        """2.0 beta 21: tabs - General, Appearance (the look of everything), Hotkeys, Advanced (the parts most people
        never need: the Mod book, Under the hood, the data folder)."""
        P1, P2 = C["panel"], C["panel2"]
        from .style import ScrollArea
        # 2.59.0: search every setting by its name and plain words
        srow = tk.Frame(body, bg=C["panel"])
        srow.pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(srow, text="Search settings", bg=C["panel"], fg=C["muted"]).pack(side="left", padx=(0, 8))
        self.set_q = tk.StringVar()
        se = ttk.Entry(srow, textvariable=self.set_q, width=40)
        se.pack(side="left")
        se.bind("<Return>", lambda e: self.settings_search(go=True))
        se.bind("<Escape>", lambda e: self.set_q.set(""))
        self.set_q.trace_add("write", lambda *_a: self.settings_search())
        self.set_hits = tk.Frame(body, bg=C["panel"])
        self.set_index = None
        self.set_nb = SegBook(body)
        self.set_nb.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        pages = {}
        # (2.98.3: no Tools tab - its one switch is on Exchange rates; 2.116.0, P10: Hotkeys + Chat commands = Keys)
        for name in ("General", "Appearance", "Keys", "Price checking", "Privacy & community", "Advanced", "About"):
            sa = ScrollArea(self.set_nb, P1)
            wrap = tk.Frame(sa.inner, bg=P1, padx=8, pady=4)
            wrap.pack(fill="both", expand=True)
            self.set_nb.add(sa, text=name)
            pages[name] = (sa, wrap)
        self.settings_scroll = pages["General"][0]                # 2.0 beta 14: scrolls when the window is small
        self.settings_pages = pages

        def section(page, title, note=""):
            outer, f = chrome_section(pages[page][1], title, note)    # 2.69.0: header strip + sunken frame
            outer.pack(fill="x", pady=(0, 8))
            row = tk.Frame(f, bg=P2)
            row.pack(fill="x")
            return row

        self.build_about(pages["About"][1])                      # 2.10.0
        self.set_anchors = {}
        self.build_pc_settings(section)                          # 2.59.0: Settings › Price checking
        # (2.98.3, feedback: Settings › Tools › Exchange rates is gone - "Check for new rates every hour" sits on the
        # Exchange rates page, by Refresh now)
        row = section("Price checking", "Copy marker", "After Ctrl+Alt+C, a small + shows where your mouse was, so you can "
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
        # (2.58.0: its color follows the overlay style - Settings › Appearance; it had its own color box here)

        # ======== General
        row = section("General", "League and search pace", "The league is used everywhere: Price Checks, Bulk Pricing, Wealth and "
                                                           "the session tracker. Pace = how fast the trade site is "
                                                           "searched (slower = fewer waits from its limits).")
        self.set_anchors["league"] = row.master
        tk.Label(row, text="League", bg=P2, fg=C["text"]).pack(side="left", padx=(0, 8))
        self.league_box = ttk.Combobox(row, textvariable=self.league_var, state="readonly", width=24)
        self.league_box.pack(side="left")
        self.league_box.bind("<<ComboboxSelected>>", self.on_league)
        tk.Label(row, text="Pace", bg=P2, fg=C["text"]).pack(side="left", padx=(16, 8))
        pace = ttk.Combobox(row, textvariable=self.pace_var, values=list(PACES), state="readonly", width=10)
        pace.pack(side="left")
        pace.bind("<<ComboboxSelected>>", self.on_pace)
        for cb in (self.league_box, pace):
            cb.bind("<<ComboboxSelected>>", lambda e: self.root.after(20, self.root.focus_set), add="+")

        # 2.59.0: the game - its log file (was a right-click in the Session timer) and window title (was in Chat commands)
        row = section("General", "Game", "Client.txt is the game's own log file: the timer counts maps from it, and "
                                         "the Breach and Ritual helpers read it. It's found by itself; pick it here if "
                                         "not. The window title tells the app when Path of Exile 2 is in front.")
        self.set_anchors["game"] = row.master
        g = tk.Frame(row, bg=P2)
        g.pack(fill="x")
        tk.Label(g, text="Game log (Client.txt)", bg=P2, fg=C["text"]).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.log_path_lbl = tk.Label(g, text="", bg=P2, fg=C["text"], anchor="w", font=("Segoe UI", 9), wraplength=420,
                                     justify="left")
        self.log_path_lbl.grid(row=0, column=1, sticky="w")
        ttk.Button(g, text="Change…", command=self.tracker_pick_log).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(g, text="Find it by itself", style="Quiet.TButton",
                   command=lambda: self.tracker_set_log("")).grid(row=0, column=3, padx=(8, 0))
        tk.Label(g, text="Game window title", bg=P2, fg=C["text"]).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        self.ov_vars = getattr(self, "ov_vars", None) or {}          # (2.116.0: Keys - and chat - are built later)
        if "poe_title" not in self.ov_vars:
            self.ov_vars["poe_title"] = tk.StringVar(value=self._ensure_overlay().cfg.get("poe_title", "") or
                                                     "Path of Exile 2")
        te = ttk.Entry(g, textvariable=self.ov_vars["poe_title"], width=24)
        te.grid(row=1, column=1, sticky="w", pady=(8, 0))
        te.bind("<FocusOut>", lambda e: self.ov_save())
        te.bind("<Return>", lambda e: (self.ov_save(), self.root.focus_set()))
        self.game_log_text()

        # 2.31.0 / 2.69.1: Community data sharing - 2.94.0: on its own page with your community name
        self.build_privacy_community(section)
        row = section("General", "Window", "Always on top keeps StashOfExile2 in front of the game (and brings it "
                                           "back if something minimizes it). "
                                           "The overlay (timer, Mechanic Helper, Notes) is shown over the game: "
                                           "normally only while the game is the window in front.")
        self.top_btn = ttk.Checkbutton(row, text="Always on top", variable=self.top_var, command=self.on_top_toggle)
        self.top_btn.pack(side="left")
        self.game_only_var = tk.BooleanVar(value=bool(SETTINGS.get("overlay_game_only", True)))
        ttk.Checkbutton(row, text="The overlay only while Path of Exile 2 is in front", variable=self.game_only_var,
                        command=self.on_game_only).pack(side="left", padx=(16, 0))
        wrow = tk.Frame(row.master, bg=P2)              # 2.116.0 (P10): from Price checking › Advanced fine tuning -
        wrow.pack(fill="x", pady=(8, 0))                # they're about the app's windows, not prices
        self.build_fine_tuning(wrow, keys=self.FINE_WINDOW, defaults=False)

        row = section("General", "Labs (experimental)", "Features still being tried out: Wealth, Game search and "
                                                         "Market Insights. They work, but may change a lot or have "
                                                         "rough edges. When Labs is off they are hidden.")
        self.labs_var = tk.BooleanVar(value=bool(SETTINGS.get("labs")))
        ttk.Checkbutton(row, text="Show Labs features (marked BETA)", variable=self.labs_var,
                        command=self.on_labs).pack(side="left")

        row = section("General", "Updates", f"You have {pretty_version()}"
                                            + (" - previews too." if SETTINGS.get("update_preview") else " - full "
                                               "releases only.") + " From GitHub; your settings and data are kept.")
        ttk.Button(row, text="Check for updates", command=self.check_updates).pack(side="left")
        row2 = tk.Frame(row.master, bg=P2)
        row2.pack(fill="x", pady=(8, 0))
        self.auto_check_var = tk.BooleanVar(value=bool(SETTINGS.get("auto_check_updates")))
        self.auto_update_var = tk.BooleanVar(value=bool(SETTINGS.get("auto_update")))
        ttk.Checkbutton(row2, text="Check when the app starts (asks before installing)",
                        variable=self.auto_check_var, command=lambda: self.on_update_options("check")).pack(anchor="w")
        ttk.Checkbutton(row2, text="Install by itself when the app starts (it restarts itself)",
                        variable=self.auto_update_var, command=lambda: self.on_update_options("update")).pack(anchor="w")
        self.update_preview_var = tk.BooleanVar(value=bool(SETTINGS.get("update_preview")))   # 2.97.3
        pv = ttk.Checkbutton(row2, text="Preview builds too (new versions before they're played)",
                             variable=self.update_preview_var, command=lambda: self.on_update_options("preview"))
        pv.pack(anchor="w")
        Tooltip(pv, "Each new version comes out as a preview first and becomes a full update once it's been played. "
                    "On: you get previews too - with the switches above, checked or installed by themselves. "
                    "They may have rough edges.")

        # ======== Appearance
        tk.Label(pages["Appearance"][1], text="THE APP", bg=P1, fg=C["muted"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x", pady=(0, 4))
        from .shell import PAGES as _PAGES
        self.launcher_var = tk.StringVar(value=dict(self.shell.LAUNCHERS).get(self.shell.cfg.get("launcher", "dock")))
        self.icons_var = tk.BooleanVar(value=bool(self.shell.cfg.get("desktop_icons")))     # (older code / tests)
        if not _PAGES:                     # 2.62.0: the sidebar is the launcher and pages cover the desktop
            row = section("Appearance", "Launcher", "How you open things: the dock on the left, icons on the desktop, or "
                                                    "both. One of them is always there. With the dock hidden, Toolkit "
                                                    "moves to the taskbar.")
            lb = ttk.Combobox(row, textvariable=self.launcher_var, values=[t for _k, t in self.shell.LAUNCHERS],
                              state="readonly", width=22)
            lb.pack(side="left")
            lb.bind("<<ComboboxSelected>>", lambda e: self.on_launcher())

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
        # 2.52.0: the switch for the clock on the Session timer moved to the timer's own options
        ttk.Button(row, text="On the timer: Overlay › Settings", style="Quiet.TButton",   # (2.116.0: its name now)
                   command=lambda: self.ovh_open("Settings")).pack(side="left", padx=(16, 0))


        from .style import ACCENTS, THEMES
        from . import themes as _th
        row = section("Appearance", "Theme", "The look of every window. Click one - it changes at once, nothing "
                                             "restarts. Every theme keeps the same icons and layout; only colors, "
                                             "bevels and textures change. Your own: put a .json in the themes "
                                             "folder of your data folder (Settings › Advanced › Your data).")
        self.set_anchors["theme"] = row.master
        self.look_vars = {"theme": tk.StringVar(value=THEMES.get(SETTINGS.get("theme"), (_th.DEFAULT,))[0])}
        self.look_cards = self.theme_cards(row, "settings")
        self._paint_look_cards()
        grid = tk.Frame(row, bg=P2)
        grid.pack(fill="x", pady=(8, 0))
        for r, (key, label, options, default) in enumerate((
                ("accent", "Accent color", {"theme": "The theme's own", **{k: v[0] for k, v in ACCENTS.items()}},
                 "theme"),
                ("ui_scale", "Text size", {90: "Smaller (90%)", 100: "Normal (100%)", 115: "Bigger (115%)",
                                           130: "Biggest (130%)"}, 100))):
            tk.Label(grid, text=label, bg=P2, fg=C["text"]).grid(row=r, column=0, sticky="w", padx=(0, 8), pady=4)
            cur = SETTINGS.get(key, default)
            v = tk.StringVar(value=options.get(cur, options[default]))
            cb = ttk.Combobox(grid, textvariable=v, values=list(options.values()), state="readonly", width=26)
            cb.grid(row=r, column=1, sticky="w", pady=4)
            cb.bind("<<ComboboxSelected>>", lambda e, k=key, o=options, vv=v: self.on_look(k, o, vv))
            self.look_vars[key] = v
        brow = tk.Frame(row, bg=P2)
        brow.pack(fill="x", pady=(8, 0))
        # 2.116.0 (P10): Restart now shows only once a restart is needed (a greyed-out main button looked broken)
        self.look_restart = ttk.Button(brow, text="Restart now", style="Primary.TButton", command=self.restart_app)
        self.look_msg = tk.Label(brow, text="Text size changes after a restart (your windows and lists are kept).",
                                 bg=P2, fg=C["muted"])
        self.look_msg.pack(side="left")
        self.splash_var = tk.BooleanVar(value=bool(SETTINGS.get("splash", True)))
        ttk.Checkbutton(row, text="Show the start-up screen", variable=self.splash_var,
                        command=lambda: (SETTINGS.__setitem__("splash", bool(self.splash_var.get())),
                                         save_json("settings.json", SETTINGS))).pack(anchor="w", pady=(8, 0))

        # 2.58.0 (one Appearance tab): every look in one place - over the game too (was Overlays › Appearance)
        self.ov_look_top = tk.Label(pages["Appearance"][1], text="OVER THE GAME", bg=P1, fg=C["muted"],
                                    font=("Segoe UI", 9, "bold"), anchor="w")
        self.ov_look_top.pack(fill="x", pady=(8, 4))
        self.build_overlay_look(pages["Appearance"][1])

        # ======== Keys (2.116.0, P10: Hotkeys and Chat commands on one tab)
        row = section("Keys", "Hotkeys", "Every key the app listens for. Click a box and press the key (with Ctrl / "
                                         "Alt / Shift, or a mouse button) - it saves at once. Esc keeps the old key, "
                                         "Backspace or right-click clears it. Two things on one key show in red.")
        self.hk_frame = row
        self.hk_vars = {}
        row2 = tk.Frame(row.master, bg=P2)
        row2.pack(fill="x", pady=(8, 0))
        self.hk_msg = tk.Label(row2, text="", bg=P2, fg=C["muted"], anchor="w", justify="left")
        self.hk_msg.pack(side="left", padx=8)
        self.fill_hotkeys()
        outer, chat = chrome_section(pages["Keys"][1], "Chat commands",
                                     "Keys that type a chat command into the game - only while it's the window in "
                                     "front. Close any AutoHotkey script that types the same ones.")
        outer.pack(fill="x", pady=(0, 8))
        self.build_chat_window(chat)                             # 2.27.0: was its own window; 2.116.0: on Keys
        # (2.98.3, feedback: "Other ways of copying" was a dead switch - Bulk Pricing adds only what you copy with
        # Ctrl+Alt+C, always)

        # ======== Advanced
        # 2.59.0: settings that had no place in the app (only in settings.json)
        row = section("Price checking", "Advanced fine tuning", "Settings most players never touch. Each one saves at once; Defaults "
                                                 "puts all of them back.")
        self.set_anchors["fine"] = row.master
        self.build_fine_tuning(row, keys=[f[0] for f in self.FINE if f[0] not in self.FINE_WINDOW])
        # 2.74.0: Under the hood (with the Mod book inside it) is hidden unless you want it - both keep working
        row = section("Advanced", "Under the hood", "How the price checker reads an item (its base, which bases it "
                                                    "is compared with, which trade-site search each mod becomes), and "
                                                    "the Mod book: what it has learned about each mod from real "
                                                    "listings and the rules for which tablet / jewel mods count. Both "
                                                    "work on their own whether they're shown or not - learning, "
                                                    "community data sharing and Regex's ratings carry on.")
        self.adv_var = tk.BooleanVar(value=self.shell.advanced_on())
        cb = ttk.Checkbutton(row, text="Show advanced tools - Price Checks ↳ Under the hood ↳ Mod book",
                             variable=self.adv_var, command=self.advanced_switch, style="Card.TCheckbutton")
        cb.pack(side="left")
        self.adv_switch = cb
        # 2.116.0 (P10): Problems - Report a bug (it's on the bottom bar too), the app's log, what it holds
        row = section("Advanced", "Problems", "What went wrong this week is in the app's log - where in the app's "
                                              "code, nothing about you. Report a bug can send it.")
        self.adv_log_lbl = tk.Label(row, text="", bg=P2, fg=C["text"], anchor="w")
        self.adv_log_lbl.pack(side="left", padx=(0, 16))
        ttk.Button(row, text="🐞 Report a bug…", command=self.bug_report_open).pack(side="left")
        ttk.Button(row, text="Open the app's log", style="Quiet.TButton",
                   command=lambda: self.open_path(P("app_log.txt")) if os.path.exists(P("app_log.txt")) else
                   self._say("Nothing logged yet - no errors, crashes or freezes.", 6)).pack(side="left", padx=(8, 0))
        self.adv_log_paint()
        # 2.116.0 (P10 / roadmap): Developer options - off and hidden until switched on
        row = section("Advanced", "Developer options", "For finding out why something happens. Nothing personal is "
                                                       "logged either way.")
        self.dev_var = tk.BooleanVar(value=bool(SETTINGS.get("dev_options")))
        ttk.Checkbutton(row, text="Show developer options", variable=self.dev_var, command=self.dev_paint,
                        style="Card.TCheckbutton").pack(anchor="w")
        self.dev_box = tk.Frame(row.master, bg=P2)
        self.debug_var = tk.BooleanVar(value=bool(SETTINGS.get("debug_mode")))
        ttk.Checkbutton(self.dev_box, text="Debug mode - every trade-site request (its answer and time) in the app's "
                                           "log, and a debug line in the status bar", variable=self.debug_var,
                        command=self.dev_paint, style="Card.TCheckbutton").pack(anchor="w", padx=(24, 0), pady=(8, 0))
        ur = tk.Frame(self.dev_box, bg=P2)
        ur.pack(fill="x", padx=(24, 0), pady=(8, 0))
        ttk.Button(ur, text="Unmatched mods…", command=self.unmatched_open).pack(side="left")
        self.dev_unm_lbl = tk.Label(ur, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9))
        self.dev_unm_lbl.pack(side="left", padx=(8, 0))
        self.dev_paint(save=False)
        row = section("Advanced", "Recent messages", "The last 20 messages the app showed you (they go away "
                                                     "by themselves, so they're kept here). Hover one to keep it up.")
        self.build_toast_log(row)
        row = section("Advanced", "Your data", "Settings, price-check lists, the Mod book, Wealth and sessions are "
                                               "kept here, shared by every version of the app.")
        tk.Label(row, text=self.data_dir_shown(), bg=P2, fg=C["text"], font=(MONO, 9)).pack(side="left")
        ttk.Button(row, text="Open folder", command=lambda: self.open_path(DATA_DIR), style="Quiet.TButton").pack(side="left", padx=8)

    @staticmethod
    def data_dir_shown():
        """2.116.0 (P10): the data folder without your Windows user name on screen (%APPDATA%\\StashOfExile2)."""
        d = str(DATA_DIR)
        for env in ("APPDATA", "LOCALAPPDATA"):
            v = os.environ.get(env)
            if v and d.lower().startswith(v.lower()):
                return f"%{env}%" + d[len(v):]
        home = os.path.expanduser("~")
        return "~" + d[len(home):] if home and d.startswith(home) else d

    def adv_log_paint(self):
        """Settings › Advanced › Problems: what the log holds this week."""
        from . import buglog
        n = buglog.counts()
        words = {"error": "error", "crash": "crash", "freeze": "freeze", "slow": "slow spot", "net": "refused request",
                 "debug": "debug note"}
        bits = [f"{v} {words.get(k, k)}{'es' if k == 'crash' and v != 1 else 's' if v != 1 else ''}"
                for k, v in sorted(n.items()) if v and k != "debug"]
        try:
            self.adv_log_lbl.config(text="This week: " + (", ".join(bits) if bits else "nothing went wrong") + ".")
        except (AttributeError, tk.TclError):
            pass

    def dev_paint(self, save=True):
        """Developer options shown or hidden; Debug mode saved."""
        SETTINGS["dev_options"] = bool(self.dev_var.get())
        SETTINGS["debug_mode"] = bool(self.debug_var.get())
        if save:
            save_json("settings.json", SETTINGS)
        if SETTINGS["dev_options"]:
            self.dev_box.pack(fill="x")
        else:
            self.dev_box.pack_forget()
        n = len(self.unmatched_rows())
        self.dev_unm_lbl.config(text=f"{n} mod{'s' if n != 1 else ''} the trade site didn't know" if n else
                                "none so far")

    @staticmethod
    def unmatched_rows():
        """unmatched_mods.txt -> [(mod, closest trade wording or where it was seen)], newest first, no repeats."""
        try:
            with open(P("unmatched_mods.txt"), encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError:
            return []
        out, seen = [], set()
        for ln in reversed(lines):
            mod, _sep, rest = ln.partition("\t| ")
            mod = mod.strip()
            if not mod or mod in seen:
                continue
            seen.add(mod)
            rest = rest.strip()
            out.append((mod, rest[len("closest on trade site: "):] if rest.startswith("closest on trade site: ")
                        else (f"seen on {rest}" if rest else "")))
        return out

    def unmatched_open(self):
        """2.116.0 (roadmap): Developer options › Unmatched mods - every mod the app couldn't find on the trade site
        beside the closest trade wording, so each mismatch points at its fix."""
        from .style import over_app
        rows = self.unmatched_rows()
        P1, P2 = C["panel"], C["panel2"]
        w = tk.Toplevel(self.root, bg=P1, padx=16, pady=12)
        over_app(w, self.dlg_parent())
        w.title("Unmatched mods")
        w.transient(self.root)
        tk.Label(w, text="Mods the trade site didn't know", bg=P1, fg=C["accent"], font=("Segoe UI", 12, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(w, text="Each one can't be searched for. Beside it: the closest trade-site wording (or the item it "
                         "was on). From unmatched_mods.txt in your data folder.", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w", justify="left", wraplength=640).pack(fill="x", pady=(2, 8))
        f = tk.Frame(w, bg=P1)
        f.pack(fill="both", expand=True)
        tv = ttk.Treeview(f, columns=("mod", "near"), show="headings", height=min(18, max(6, len(rows))))
        for cid, title, wd in (("mod", "Mod", 360), ("near", "Closest trade wording", 320)):
            tv.heading(cid, text=title)
            tv.column(cid, width=wd, anchor="w", stretch=True)
        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        for mod, near in rows:
            tv.insert("", "end", values=(mod, near or "-"))
        if not rows:
            tv.insert("", "end", values=("None so far - every mod you price checked was found.", ""))
        b = tk.Frame(w, bg=P1)
        b.pack(fill="x", pady=(8, 0))

        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(f"{m}\t{n}" for m, n in rows))
            self._say(f"Copied {len(rows)} unmatched mods.", 6)

        def clear():
            try:
                os.replace(P("unmatched_mods.txt"), P("unmatched_mods.old.txt"))
            except OSError:
                pass
            tv.delete(*tv.get_children())
            self.dev_paint(save=False)
        ttk.Button(b, text="Close", style="Quiet.TButton", command=w.destroy).pack(side="right")
        ttk.Button(b, text="Copy all", command=copy).pack(side="right", padx=(0, 8))
        ttk.Button(b, text="Clear the list", style="Quiet.TButton", command=clear).pack(side="left")
        self.unm_win, self.unm_tv = w, tv
        return w

    def on_click_through(self):
        """2.74.0: Settings › Appearance › Overlay settings › Click-through."""
        self.tracker_cfg()["click_through"] = bool(self.ov_ct_var.get())
        self.tracker_save()
        self.overlay_click_through()

    def advanced_switch(self):
        """2.74.0: Settings › Advanced › Show advanced tools."""
        self.shell.set_advanced(bool(self.adv_var.get()))

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

    def on_look(self, key, options, var):
        value = next((k for k, t in options.items() if t == var.get()), None)
        if value is None:
            return
        SETTINGS[key] = value
        save_json("settings.json", SETTINGS)
        if key == "ui_scale":
            if not self.look_restart.winfo_ismapped():
                self.look_restart.pack(side="left", before=self.look_msg, padx=(0, 8))
            self.look_msg.config(text="Saved - restart to see the new text size.", fg=C["good"])
            return
        self.relook()

    def pick_theme(self, tid, wait=False):
        """2.60.0: a theme card in Settings › Appearance - swapped live. (2.112.3: a swap slower than 1.5 s writes
        slow_report.txt - code locations only - so a slow PC can show where the time goes.)"""
        from .style import THEMES
        from .hangwatch import profiled
        SETTINGS["theme"] = tid
        save_json("settings.json", SETTINGS)
        if "theme" in getattr(self, "look_vars", {}):
            self.look_vars["theme"].set(THEMES.get(tid, (tid,))[0])
        # 2.112.4: quick clicks through the cards swap ONCE, 200 ms after the last (each swap re-colours every window;
        # a burst of them back to back crashed the app on Windows)
        job = getattr(self, "_theme_job", None)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except tk.TclError:
                pass

        def go():
            self._theme_job = None
            profiled("theme change", self.relook, P("slow_report.txt"), APP_VERSION)
        if not wait:                                             # (code and tests: at once)
            return go()
        try:
            self._paint_look_cards()                             # (the clicked card lights at once)
        except Exception:
            buglog.caught()
        self._theme_job = self.root.after(200, go)

    def theme_cards(self, parent, where, cols=4, scale=1.0):
        """2.60.0 / 2.61.0: the theme cards - a small picture of each pack; click = that theme, live. Used in
        Settings › Appearance and on the first page of the quick start."""
        from . import themes as _th
        from .style import Tooltip
        P2 = C["panel2"]
        gal = tk.Frame(parent, bg=P2)
        gal.pack(fill="x")
        cards = {}
        w, h = int(168 * scale), int(92 * scale)
        for n, t in enumerate(_th.ordered()):
            card = tk.Frame(gal, bg=P2, highlightthickness=2, highlightbackground=P2, cursor="hand2")
            card.grid(row=n // cols, column=n % cols, padx=(0, 8), pady=(0, 8), sticky="nw")
            cv = _th.self_painted(tk.Canvas(card, width=w, height=h, highlightthickness=0, bd=0, cursor="hand2"))
            cv.pack()
            _th.preview(cv, t)
            if scale != 1.0:
                cv.scale("all", 0, 0, scale, scale)
            name = tk.Label(card, text=t.name, bg=P2, fg=C["text"], font=("Segoe UI", 10 if scale >= 1 else 9, "bold"),
                            anchor="w")
            name.pack(fill="x", pady=(4, 0))
            if t.data.get("description"):
                Tooltip(card, t.data["description"])
            for wd in (card, cv, name):
                wd.bind("<Button-1>", lambda e, tid=t.id: self.pick_theme(tid, wait=True))
            cards[t.id] = card
        self.__dict__.setdefault("look_card_sets", {})[where] = cards
        self._paint_look_cards()
        return cards

    def _paint_look_cards(self):
        cur = SETTINGS.get("theme")
        for cards in getattr(self, "look_card_sets", {}).values():
            for tid, card in cards.items():
                on = tid == cur
                try:
                    card.config(highlightbackground=C["accent"] if on else C["panel2"])
                    card.winfo_children()[1].config(fg=C["accent"] if on else C["text"])
                except (tk.TclError, IndexError):
                    pass

    def draw_look_swatch(self):
        """(2.0.0's swatch - the theme cards show each look now)"""
        return None

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

    # ---- 2.43.0: the look of the windows over the game (2.44.0: Overlays › Look; 2.49.0: › Appearance)
    def build_overlay_look(self, parent):
        P2 = C["panel2"]

        def section(_page, title, note=""):
            outer, f = chrome_section(parent, title, note)            # 2.69.0: header strip + sunken frame
            outer.pack(fill="x", pady=(0, 8))
            row = tk.Frame(f, bg=P2)
            row.pack(fill="x")
            return row
        # 2.66.0: no Style list - everything over the game is drawn in the app's theme (Settings › Appearance ›
        # Theme). The Layout says the shape.
        # 2.74.0: one area - Layout, Opacity and Click-through (were the Overlay layout and Opacity sections)
        row = section("Appearance", "Overlay settings", "The overlay over the game (timer, Mechanic Helper, Focus): "
                                                        "pick a style, its shape and its colours. Notes, the calculator and the remnant "
                                                        "price tags use your theme's colors.")
        from .merged_page import LAYOUTS
        g = tk.Frame(row, bg=P2)
        g.pack(fill="x")
        g.columnconfigure(1, weight=1)

        def label(r, text):
            tk.Label(g, text=text, bg=P2, fg=C["text"], width=12, anchor="w").grid(row=r, column=0, sticky="nw",
                                                                                   pady=(8 if r else 0, 0))

        def hint(r, text):
            lab = tk.Label(g, text=text, bg=P2, fg=C["muted"], font=("Segoe UI", 9), justify="left", wraplength=560,
                           anchor="w")
            lab.grid(row=r, column=1, columnspan=2, sticky="w", pady=(2, 0))
            return lab
        # 2.101.0: the Style first, then its Layout (2.111.0: no Colours - each style keeps its own)
        from .ovlight import STYLES
        # 2.116.0 (P10, feedback: a visual indicator for each style): the names beside a live preview of the bar
        # in the style under the mouse - was a dropdown over ten lines describing all fourteen
        label(0, "Style")
        self.ov_look_var = tk.StringVar(value=STYLES[self.ov_look()])     # (the cog's Style list keeps it in step)
        from .ovstylepick import StylePicker
        self.ov_style_pick = StylePicker(g, self.ov_look(), lambda st: (self.ov_look_var.set(STYLES[st]),
                                                                       self.on_ov_look(style=st)))
        self.ov_style_pick.grid(row=0, column=1, rowspan=2, sticky="w")
        label(2, "Layout")
        self.ov_layout_var = tk.StringVar(value=LAYOUTS.get(self.merged_layout(), LAYOUTS["xpbar"]))
        lc = ttk.Combobox(g, textvariable=self.ov_layout_var, values=list(LAYOUTS.values()), state="readonly", width=24)
        lc.grid(row=2, column=1, sticky="w", pady=(8, 0))
        lc.bind("<<ComboboxSelected>>", lambda e: self.merged_set(
            layout=next((k for k, t in LAYOUTS.items() if t == self.ov_layout_var.get()), "xpbar")))
        hint(3, "Game bar: rests on the game's XP bar (unlocked, drag it; picking it again puts it back). "
                "Panel: a card like the game's vendor windows - place it anywhere.")
        # 2.56.1: ONE opacity for everything over the game (it was one slider each)
        label(6, "Opacity")
        op = tk.Frame(g, bg=P2)
        op.grid(row=6, column=1, sticky="w", pady=(8, 0))
        v = tk.IntVar(value=self.ov_opacity_get("session"))
        self.ov_op_vars = {"all": v}
        ttk.Scale(op, from_=60, to=255, variable=v, orient="horizontal", length=260,
                  command=lambda _v: self.on_ov_opacity()).pack(side="left")
        pct = tk.Label(op, text=f"{round(v.get() * 100 / 255)}%", bg=P2, fg=C["muted"], font=(MONO, 9), width=5,
                       anchor="e")
        pct.pack(side="left", padx=(8, 0))
        self.ov_op_pct = {"all": pct}
        hint(7, "100% = fully solid. Lower = see-through, text and all (24% is the lowest). Over a busy spot, "
                "95-100% reads best.")
        label(8, "Click-through")
        self.ov_ct_var = tk.BooleanVar(value=bool(self.tracker_cfg().get("click_through", False)))
        ct = ttk.Checkbutton(g, text="Clicks go through the overlay to the game",
                             variable=self.ov_ct_var, command=self.on_click_through, style="Card.TCheckbutton")
        ct.grid(row=8, column=1, sticky="w", pady=(8, 0))
        self.ov_ct_switch = ct
        hint(9, "On: the overlay's bar can't be clicked - its switches, ⏸ / ▶, Notes ▾ and Calc ▾ too (the Pause key "
                "still pauses the timer). The lock only stops it moving. Notes and the calculator always take clicks.")
        row = section("Appearance", "Notes", "The note uses the style's colors and font; only its text size is "
                                             "yours.")
        tk.Label(row, text="Text size", bg=P2, fg=C["text"]).pack(side="left")
        self.notes_font_var = tk.IntVar(value=int(self._ensure_overlay().cfg.get("notes_font", 11)))
        ttk.Spinbox(row, from_=8, to=24, textvariable=self.notes_font_var, width=5,
                    command=self.on_notes_font).pack(side="left", padx=8)
        self.notes_font_var.trace_add("write", lambda *_a: self.root.after(300, self.on_notes_font))
        row = section("Appearance", "Motion", "Tooltips, notices and windows over the game fade in for a moment. "
                                              "Reduce motion makes them appear at once. Until you choose, it "
                                              "follows Windows' own \"Show animations\" setting.")
        from .motion import reduced
        self.reduce_motion_var = tk.BooleanVar(value=reduced())
        ttk.Checkbutton(row, text="Reduce motion", variable=self.reduce_motion_var, style="Card.TCheckbutton",
                        command=self.on_reduce_motion).pack(side="left")

    def on_ov_look(self, style=None, colors=None):
        """2.101.0: Settings › Appearance › Overlay settings › Style - saved and shown at once."""
        self.ov_look_set(style=style, colors=colors)
        self._ov_look_paint()

    def _ov_look_paint(self):
        """Keep Settings › Appearance's style picker in step (2.116.0: picked from the cog's list too)."""
        pk = getattr(self, "ov_style_pick", None)
        if pk is not None:
            try:
                if pk.current != self.ov_look():
                    pk.set(self.ov_look())
            except tk.TclError:
                pass

    def on_reduce_motion(self):
        """2.100.0: Settings › Appearance › Reduce motion (saved; from then on your choice beats Windows')."""
        SETTINGS["reduce_motion"] = bool(self.reduce_motion_var.get())
        save_json("settings.json", SETTINGS)
        self._say("Saved: " + ("windows appear at once." if SETTINGS["reduce_motion"] else
                               "tooltips, notices and windows over the game fade in."), 6)

    @staticmethod
    def marker_colour():
        """2.58.0: the copy marker's color comes from the overlay style (its warm color; a bright one for the
        light parchment, which would be dark ink on the game)."""
        from .overlaywin import pal
        P = pal()
        return "#e0a352" if P.get("texture") else P.get("warn") or "#ffd25a"

    def appearance_open(self):
        """2.58.0: Settings › Appearance, scrolled to Over the game (every look lives there)."""
        self.shell.open("settings")
        try:
            self.set_nb.select(self.set_nb.titles.index("Appearance"))
            sa = self.settings_pages["Appearance"][0]
            self.root.update_idletasks()
            top = getattr(self, "ov_look_top", None)               # straight to OVER THE GAME
            h = max(1, sa.inner.winfo_height())
            sa.canvas.yview_moveto((top.winfo_y() / h) if top is not None else 0)
        except (ValueError, AttributeError, tk.TclError, KeyError):
            pass

    def on_notes_font(self):
        """2.58.0: Notes' text size, with the other looks (the note's colors and font come from the style)."""
        try:
            self.overlay.cfg["notes_font"] = max(8, min(24, int(self.notes_font_var.get())))
        except (ValueError, tk.TclError):
            return
        self.overlay.save_settings()
        self.overlay.restyle()

    def ov_opacity_get(self, key="session"):
        """The opacity of the windows over the game (2.56.1: one for all; the timer's is the one kept)."""
        return int(self.tracker_cfg().get("opacity", 225))

    def on_ov_opacity(self, _key=None):
        v = int(float(self.ov_op_vars["all"].get()))
        self.ov_op_pct["all"].config(text=f"{round(v * 100 / 255)}%")
        t = self.tracker_cfg()
        t["opacity"] = t["hopacity"] = v
        self.overlay.cfg["notes_opacity"] = v
        for w in (getattr(self, "tk_overlay", None), getattr(self, "tk_helpers", None),
                  getattr(self.overlay, "notes", None), getattr(self, "mg_win", None), getattr(self, "mg_win2", None)):
            try:
                if w is not None and w.winfo_exists():
                    w.set_opacity(v)
            except Exception:
                buglog.caught()
        job = getattr(self, "_ov_save_job", None)              # save once the slider stops
        if job:
            self.root.after_cancel(job)
        self._ov_save_job = self.root.after(400, self._ov_save)

    def _ov_save(self):
        self._ov_save_job = None
        self.tracker_save()
        self.overlay.save_settings()

    def on_ingame_clock(self):
        """2.39.0: the clock + date line on the Session timer, on or off."""
        self.tracker_cfg()["clock"] = bool(self.ingame_clock_var.get())
        self.tracker_save()
        if getattr(self, "mg_win", None) is not None:
            self.merged_build()

    def on_update_options(self, which="update"):
        if which == "update" and self.auto_update_var.get():     # installing automatically includes checking
            self.auto_check_var.set(True)
        if which == "check" and not self.auto_check_var.get():   # no checking = no installing either
            self.auto_update_var.set(False)
        SETTINGS["auto_check_updates"] = bool(self.auto_check_var.get())
        SETTINGS["auto_update"] = bool(self.auto_update_var.get())
        if getattr(self, "update_preview_var", None) is not None:
            SETTINGS["update_preview"] = bool(self.update_preview_var.get())
        save_json("settings.json", SETTINGS)
        if which == "preview":
            return self._say("Saved: " + ("you'll get preview builds too." if SETTINGS["update_preview"] else
                                          "full releases only."), 8)
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
        i, group = 0, None
        self.hk_rows = {}
        chat_said = False
        for what, key, where, kid in self.all_hotkeys():
            if where == "Chat commands":                          # 2.116.0: set in Chat commands, just below
                if not chat_said:
                    tk.Label(f, text="CHAT COMMANDS", bg=P2, fg=C["accent"], font=("Segoe UI", 9, "bold"),
                             anchor="w").grid(row=i, column=0, columnspan=3, sticky="w", pady=(10 if i else 0, 2))
                    tk.Label(f, text="set below, with their commands", bg=P2, fg=C["muted"],
                             font=("Segoe UI", 9), anchor="w").grid(row=i + 1, column=0, columnspan=3, sticky="w",
                                                                    padx=(12, 0))
                    i += 2
                    chat_said = True
                continue
            if where != group:                                    # 2.57.0: a heading per group
                group = where
                tk.Label(f, text=group.upper(), bg=P2, fg=C["accent"], font=("Segoe UI", 9, "bold"), anchor="w").grid(
                    row=i, column=0, columnspan=3, sticky="w", pady=(10 if i else 0, 2))
                i += 1
            col = C["red"] if what in clash_keys else C["text"]
            lab = tk.Label(f, text=what, bg=P2, fg=col, anchor="w")
            lab.grid(row=i, column=0, sticky="w", padx=(12, 12))
            if kid:
                v = tk.StringVar(value=key)
                self.hk_vars[kid] = v
                kc = KeyCapture(f, v, width=16, on_change=lambda t: self.root.after(10, self.save_hotkeys))   # 2.0 beta 16
                kc.grid(row=i, column=1, sticky="w", pady=1)
                self.hk_rows[kid] = (lab, kc)
                if what in clash_keys:
                    kc.config(fg=col)
            else:
                tk.Label(f, text=key_label(key) if key else "-", bg=P2, fg=col, anchor="w", font=(MONO, 9)).grid(
                    row=i, column=1, sticky="w")
            if not kid:
                tk.Label(f, text="the game's own copy - always on", bg=P2, fg=C["muted"],
                         font=("Segoe UI", 9)).grid(row=i, column=2, sticky="w", padx=(12, 0))
            i += 1

    def hotkeys_open(self, kid=None):
        """2.57.0: Settings › Keys, where every key is set - the row asked for is lit up for a moment."""
        self.shell.open("settings")
        try:
            self.set_nb.select(self.set_nb.titles.index("Keys"))
        except (ValueError, AttributeError, tk.TclError):
            pass
        row = getattr(self, "hk_rows", {}).get(kid)
        if row:
            lab = row[0]
            lab.config(bg=C["accent"], fg="#1a1206")
            self.root.after(1600, lambda: lab.winfo_exists() and lab.config(bg=C["panel2"], fg=C["text"]))
            try:
                row[1].focus_set()
            except tk.TclError:
                pass

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
            if where == "cmd":                                     # 2.57.0: chat command keys are set here too
                cmds = self.overlay.cfg.get("commands", []) or []
                n = int(key)
                if n < len(cmds):
                    cmds[n]["key"] = txt
                    rows = getattr(self, "ov_cmd_vars", [])
                    if n < len(rows) and rows[n][1].get() != txt:
                        rows[n][1].set(txt)
                continue
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
        for refresh in ("_tk_keys_text", "_rx_key_text", "_chat_keys_text"):
            if hasattr(self, refresh):                             # 2.57.0: the places that show a key
                try:
                    getattr(self, refresh)()
                except Exception:
                    buglog.caught()
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

    def on_good(self):
        try:
            SETTINGS["good_div"] = max(0.01, float(self.good_var.get()))
        except ValueError:
            return
        save_json("settings.json", SETTINGS)
        self.pc_rules_text()
        if getattr(self, "tree", None) is not None:
            self.refresh_all()

    # ---------------- 2.59.0: Settings › Price checking - one home for the price check settings
    def pc_vars(self):
        """The Price checking settings' variables, made once and shared by Settings, the Price checks toolbar, the
        Stash tab row and Wealth (whichever is built first makes them)."""
        if getattr(self, "good_var", None) is not None:
            return
        from .pricefmt import PRICE_UNITS
        self.good_var = tk.StringVar(value=str(SETTINGS["good_div"]))
        self.pop_var = tk.BooleanVar(value=SETTINGS["popups"])
        self.snd_var = tk.BooleanVar(value=SETTINGS["sound"])
        self.copy_var = tk.BooleanVar(value=SETTINGS["auto_copy"])
        self.hk_var = tk.BooleanVar(value=SETTINGS.get("hotkey_only", True))
        self.status_var = tk.StringVar(value=SETTINGS["status"])
        self.age_var = tk.StringVar(value=SETTINGS["age"])
        self.unit_var = tk.StringVar(value=dict(PRICE_UNITS).get(SETTINGS.get("price_unit") or "auto", PRICE_UNITS[0][1]))
        self.acc_var = tk.StringVar(value=SETTINGS.get("wealth_account", ""))
        self.pc_acc = self.w_acc = self.acc_var                 # (the names the Stash tab row and Wealth used)
        self.acc_var.trace_add("write", lambda *_a: self.on_account())
        self.acc_links = []                                      # labels that show the account (Stash tab, Wealth)

    def on_account(self):
        v = self.acc_var.get().strip()
        if v != SETTINGS.get("wealth_account", ""):
            SETTINGS["wealth_account"] = v
            save_json("settings.json", SETTINGS)
        for lbl in list(getattr(self, "acc_links", [])):
            try:
                lbl.config(text=self.acc_text())
            except tk.TclError:
                self.acc_links.remove(lbl)

    def pc_rules_text(self):
        lbl = getattr(self, "pc_rules_lbl", None)
        if lbl is None:
            return
        try:
            lbl.config(text=f"★ valuable mod ≥ {SETTINGS['good_div']:g} div  ·  {SETTINGS['status']}  ·  "
                            f"listed within {SETTINGS['age']}")
        except tk.TclError:
            pass

    def settings_open(self, page, anchor=None):
        """Settings at a page, scrolled to a part of it (anchor: a key in self.set_anchors) which is lit for a moment."""
        self.shell.open("settings")
        try:
            self.set_nb.select(self.set_nb.titles.index(page))
        except (ValueError, AttributeError, tk.TclError):
            return
        w = anchor if isinstance(anchor, tk.Misc) else getattr(self, "set_anchors", {}).get(anchor)
        if w is None:
            return
        w = getattr(w, "section_outer", w)                 # 2.69.0: the whole section (its strip and frame)
        try:
            sa = self.settings_pages[page][0]
            self.root.update_idletasks()
            h = max(1, sa.inner.winfo_height())
            sa.canvas.yview_moveto(max(0, w.winfo_y() - 8) / h)
            old = w.cget("highlightbackground")
            w.config(highlightbackground=C["accent"])
            self.root.after(1500, lambda: w.winfo_exists() and w.config(highlightbackground=old))
        except (tk.TclError, KeyError, AttributeError):
            pass

    def settings_index(self):
        """[(page, section frame, its title, all its words)] - built the first time you search."""
        out = []

        def words(w, acc):
            for c in w.winfo_children():
                try:
                    t = c.cget("text")
                    if t:
                        acc.append(str(t))
                except tk.TclError:
                    pass
                words(c, acc)
            return acc
        for page, (_sa, wrap) in self.settings_pages.items():
            for f in wrap.winfo_children():
                acc = words(f, [])
                title = getattr(f, "section_title", None)     # 2.69.0: the title is drawn on the header strip
                if title:
                    acc.insert(0, title)
                if acc:
                    out.append((page, f, acc[0].strip()[:60], " ".join(acc).lower() + " " + page.lower()))
        return out

    def settings_search(self, go=False):
        q = self.set_q.get().strip().lower()
        for w in self.set_hits.winfo_children():
            w.destroy()
        if not q:
            self.set_hits.pack_forget()
            return []
        if self.set_index is None:
            self.set_index = self.settings_index()
        hits = [h for h in self.set_index if all(word in h[3] for word in q.split())]
        if go and hits:
            self.set_q.set("")
            self.settings_open(hits[0][0], hits[0][1])
            return hits
        self.set_hits.pack(fill="x", padx=12, pady=(4, 0), before=self.set_nb)
        if not hits:
            tk.Label(self.set_hits, text="Nothing found.", bg=C["panel"], fg=C["muted"]).pack(anchor="w")
        for page, f, title, _t in hits[:8]:
            lb = tk.Label(self.set_hits, text=f"{page} › {title}", bg=C["panel"], fg=C["accent"], cursor="hand2",
                          font=("Segoe UI", 9, "underline"), anchor="w")
            lb.pack(anchor="w")
            lb.bind("<Button-1>", lambda e, p=page, w=f: (self.set_q.set(""), self.settings_open(p, w)))
        return hits

    def on_copy_marker(self, preview=False):
        SETTINGS["copy_marker"] = bool(self.mark_var.get())
        if preview:                                          # show it next to the box for 2 s
            try:
                from .copymark import CopyMarker
                if getattr(self, "copy_marker", None) is None:
                    self.copy_marker = CopyMarker(self.root)
                self.copy_marker.show(self.root.winfo_pointerx() + 30, self.root.winfo_pointery(), secs=2,
                                      colour=self.marker_colour())
            except Exception:
                buglog.caught()
        try:
            SETTINGS["copy_marker_secs"] = max(1, min(600, int(float(self.mark_secs.get()))))
        except (ValueError, AttributeError):
            pass
        if hasattr(self, "mark_hold"):
            SETTINGS["copy_marker_hold"] = bool(self.mark_hold.get())
        save_json("settings.json", SETTINGS)
        if not SETTINGS["copy_marker"] and getattr(self, "copy_marker", None):
            self.copy_marker.clear()
