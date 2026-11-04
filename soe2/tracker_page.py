"""The Session tracker utility (2.0 beta 9): its window, the timer overlay over the game, and its hotkeys.

Mixed into App. The logic is in tracker.py, the game log reading in gamelog.py. Wealth is only READ: at the start
the tracker notes what your Wealth holds; at the end it compares, both at the same (latest) prices."""
import copy
import os
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, ttk

from .config import save_json, SETTINGS
from .gamelog import find_log, LogReader
from .overlay import game_active, key_label, parse_key
from .style import ScrollArea, C, FONT_TITLE, SegBar
from .chrome import SectionBar, Viewport, section as chrome_section
from .tracker import fmt_time, Session, Sessions

DEFAULTS = {"overlay": True, "locked": False, "x": 60, "y": 260, "w": 230, "h": 190, "opacity": 225,
            "lines": {"session": True, "map": True, "maps": True, "avg": True, "where": True, "rank": True},   # 2.70.1: where   # 2.54.0: no profit (Strat Tracker has it)
            "key_pause": "", "key_camp_prev": "", "key_camp_next": "", "ask_count": True, "log_path": "",
            "character": "", "character_guess": "", "alerts_bar": True, "autostart": False,
            "clock": True,
            "merged": True, "layout": "xpbar"}   # 2.39.0 clock; 2.55.0: one overlay window; 2.74.0: Game bar
DEFAULT_KEYS = {"key_pause": "Pause",            # 2.74.3: the keyboard's Pause key (was Ctrl+Alt+P; start / stop's
                "key_overlay": "F6"}             # Ctrl+Alt+S is gone - Ctrl+Alt keys got in the way of game input)           # 2.59.0: F6 shows / hides the whole overlay       # 2.10.0: set once, change them in Options
# 2.54.0: the Session timer times your play; money lives in one place, Money Makers › Strat Tracker.
# Profit (Wealth at Stop minus at Start) is gone from here: its tiles, overlay line, options and Stop count.
LINE_NAMES = [("session", "Session timer"), ("map", "This map's time"), ("maps", "Maps done"), ("avg", "Average map"),
              ("rank", "Map rank"),                                              # 2.76.0: its own part
              ("where", "Where you are")]


class _BarTitle:
    """2.69.0: a section strip's title that old code sets like a Label (.config(text=...))."""

    def __init__(self, bar):
        self.bar = bar

    def config(self, text=None, **_kw):
        if text is not None:
            self.bar.set_title(text)
    configure = config

    def cget(self, key):
        return self.bar.title if key == "text" else ""


class TrackerPage:
    # ---------------- set-up
    def tracker_cfg(self):
        cfg = SETTINGS.setdefault("tracker", {})
        for k, v in DEFAULTS.items():
            cfg.setdefault(k, copy.deepcopy(v))
        for k, v in DEFAULTS["lines"].items():
            cfg["lines"].setdefault(k, v)
        if not cfg.get("ov_2701"):                   # 2.70.1: no Hide timer button any more - each part has its switch
            cfg["ov_2701"] = True
            cfg["overlay"] = True
            cfg["alerts_bar"] = True                 # (the overlay's × used to switch these off without saying so)
        if not cfg.get("keys_210"):                  # 2.10.0: start / stop and pause get a key (only if you had none)
            cfg["keys_210"] = True
            for k, v in DEFAULT_KEYS.items():
                if not cfg.get(k):
                    cfg[k] = v
        if not cfg.get("keys_2743"):                 # 2.74.3: no start / stop key; pause on the Pause key
            cfg["keys_2743"] = True
            cfg.pop("key_toggle", None)
            if cfg.get("key_pause") in (None, "", "Ctrl+Alt+P"):
                cfg["key_pause"] = "Pause"
        return cfg

    def tracker_save(self):
        save_json("settings.json", SETTINGS)

    # ---------------- 2.44.0: Overlays - everything shown over the game, in one window
    # 2.59.0: one screen, "Overlay" - no tabs. The session (start, numbers, maps, past sessions) on top;
    # Options holds every option of the overlay: the timer, the Mechanic Helper and Notes. Looks: Settings › Appearance.
    OVH_TABS = ("Overlay",)

    def build_overlays_hub(self, body):
        P1 = C["panel"]
        self.ovh_bar = None
        page = tk.Frame(body, bg=P1)
        page.pack(fill="both", expand=True)
        self.ovh_pages = {"Overlay": page, "Session timer": page}
        self.build_tracker_window(page)

    def ovh_show(self):
        pass

    def ovh_open(self, tab):
        """Open the Overlay screen: the Mechanic Helper or Notes part of its Options (the ⚙ on the overlay, old links).
        "Appearance" is Settings › Appearance."""
        if tab == "Appearance":
            return self.appearance_open()
        if tab in ("Mechanic Helper", "Notes", "Options", "Settings"):     # 2.82.0: Overlay ↳ Settings
            self.shell.open("ovset")
            part = self.ovh_pages.get(tab)
            sa = getattr(self, "tk_opt_area", None)
            if part is not None and sa is not None:
                try:
                    self.root.update_idletasks()
                    sa.canvas.yview_moveto(part.winfo_y() / max(1, sa.inner.winfo_height()))
                except tk.TclError:
                    pass
        else:
            self.shell.open("tracker")

    def build_tracker_window(self, body):
        cfg = self.tracker_cfg()
        P1, P2 = C["panel"], C["panel2"]
        self.tk_session, self.tk_sessions = None, Sessions()
        self.tk_reader, self.tk_waiting_count, self.tk_finishing = None, False, False
        self.tk_overlay = None
        # ---- top: start / pause, and where the log is
        tpo, top = chrome_section(body, "Session")                             # 2.69.0
        tpo.pack(fill="x", padx=8, pady=(8, 8))
        self.tk_start_btn = ttk.Button(top, text="▶ Start tracking", style="Primary.TButton", command=self.tracker_toggle)
        self.tk_start_btn.pack(side="left")
        self.tk_pause_btn = ttk.Button(top, text="Pause", command=self.tracker_pause_toggle, state="disabled")
        self.tk_pause_btn.pack(side="left", padx=8)
        self.tk_state = tk.Label(top, text="Not tracking", bg=P2, fg=C["muted"], font=("Segoe UI", 12, "bold"))
        self.tk_state.pack(side="left", padx=12)
        # 2.70.1: a switch for the timer only (was "Hide timer", which hid every number); the rest: Options
        self.tk_timer_var = tk.BooleanVar(value=bool(cfg["lines"].get("session", True)))
        self.tk_timer_sw = ttk.Checkbutton(top, text="Timer over the game", variable=self.tk_timer_var,
                                           command=self.tracker_timer_switch, style="Card.TCheckbutton")
        self.tk_timer_sw.pack(side="right")
        self.tk_keys_lbl = tk.Label(top, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9))       # 2.10.0
        self.tk_keys_lbl.pack(side="right", padx=8)
        self.tracker_keys_hint()
        self.tk_strip = tk.Frame(body, bg="#2a2110", padx=12, pady=8, highlightthickness=1, highlightbackground="#7a6428")
        self.tk_strip_lbl = tk.Label(self.tk_strip, text="", bg="#2a2110", fg=C["text"], anchor="w", justify="left",
                                     wraplength=640)
        self.tk_strip_lbl.pack(side="left", fill="x", expand=True)
        self.tk_strip_btns = tk.Frame(self.tk_strip, bg="#2a2110")
        self.tk_strip_btns.pack(side="right")
        lrow = tk.Frame(body, bg=P1)
        lrow.pack(fill="x", padx=12)
        self.tk_log_lbl = tk.Label(lrow, text="", bg=P1, fg=C["muted"], anchor="w", font=("Segoe UI", 9))
        self.tk_log_lbl.pack(side="left", fill="x", expand=True)
        # 2.0 beta 21: only shown when Client.txt can't be found. 2.59.0: the file is set in Settings › General › Game
        self.tk_pick_btn = ttk.Button(lrow, text="Set Client.txt in Settings › General",
                                      command=lambda: self.settings_open("General", "game"))
        self.tk_log_lbl.bind("<Button-3>", lambda e: self.settings_open("General", "game"))

        # ---- the numbers
        nums = tk.Frame(body, bg=P1)
        nums.pack(fill="x", padx=8, pady=(8, 8))
        self.tk_nums = {}
        for i, (k, label) in enumerate((("time", "Session"), ("where", "Where you are"), ("map", "This map"),
                                        ("maps", "Maps"), ("avg", "Average map"), ("best", "Fastest map"))):
            f = tk.Frame(nums, bg=P2, padx=8, pady=8, highlightthickness=1, highlightbackground=C["line"])
            f.grid(row=i // 3, column=i % 3, sticky="nsew", padx=(0, 8), pady=(0, 8))
            tk.Label(f, text=label, bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(anchor="w")
            v = tk.Label(f, text="-", bg=P2, fg=C["text"], font=("Segoe UI", 10 if k == "where" else 13, "bold"), anchor="w")
            v.pack(anchor="w")
            self.tk_nums[k] = v
        for c in range(3):
            nums.columnconfigure(c, weight=1, uniform="n")
        led = tk.Frame(body, bg=P1)                    # 2.54.0: where the money went
        led.pack(fill="x", padx=8, pady=(0, 4))
        tk.Label(led, text="Profit is tracked per farming setup in Money Makers › Strat Tracker.", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9)).pack(side="left")
        ttk.Button(led, text="Open Strat Tracker", style="Quiet.TButton",
                   command=self.tracker_open_ledger).pack(side="left", padx=8)
        # (2.10.0's "Alerts while you play" panel is the Mechanic Helper tab since 2.44.0: build_overlays_hub)

        # ---- this session's maps / past sessions
        vrow = tk.Frame(body, bg=P1)
        vrow.pack(fill="x", padx=8, pady=(4, 8))
        self.tk_view = SegBar(vrow, ["This session's maps", "Map stats", "Past sessions"],
                              command=lambda v: self.tracker_view(),
                              size=9, pad=(12, 4))
        self.tk_view.pack(side="left")
        # 2.82.0 (feedback: Options "shouldn't be nested beside the map stats"): Overlay ↳ Settings, its own page
        self.tk_settings_btn = ttk.Button(vrow, text="⚙  Overlay settings", style="Primary.TButton",
                                          command=lambda: self.shell.open("ovset"))
        self.tk_settings_btn.pack(side="right")
        self.tk_pages = {}
        pm = tk.Frame(body, bg=P1)
        tv = ttk.Treeview(pm, columns=("n", "map", "lvl", "time", "entries", "deaths", "rank"), show="headings",
                          height=4)
        for cid, title, w, a in (("n", "#", 40, "e"), ("map", "Map", 220, "w"), ("lvl", "Level", 60, "e"),
                                 ("time", "Time in it", 90, "e"), ("entries", "Times entered", 100, "e"),
                                 ("deaths", "Deaths", 70, "e"), ("rank", "Rank", 70, "center")):
            tv.heading(cid, text=title)
            tv.column(cid, width=w, anchor=a, stretch=(cid == "map"))
        tv.pack(fill="both", expand=True)
        self.tk_maps = tv
        self.list_register("tracker", tv)
        self.tk_pages["This session's maps"] = pm
        ph = tk.Frame(body, bg=P1)
        hv = ttk.Treeview(ph, columns=("when", "len", "maps", "avg", "note"), show="headings", height=4)
        for cid, title, w, a in (("when", "Started", 120, "w"), ("len", "Length", 70, "e"), ("maps", "Maps", 50, "e"),
                                 ("avg", "Avg map", 70, "e"), ("note", "Note", 260, "w")):
            hv.heading(cid, text=title)
            hv.column(cid, width=w, anchor=a, stretch=(cid == "note"))
        hv.pack(fill="both", expand=True)
        hv.bind("<Double-1>", self.tracker_edit_note)
        self.tk_hist = hv
        self.list_register("tracker", hv, delete=self.tracker_remove_sessions)          # 2.4.0
        prow = tk.Frame(ph, bg=P1)
        prow.pack(fill="x")
        tk.Label(prow, text="Double-click a session to write a note (e.g. 'T15 Breach + Delirium'). Delete removes "
                            "the selected ones (Ctrl+Z undoes).", bg=P1,
                 fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(side="left")
        ttk.Button(prow, text="Export CSV", command=self.tracker_export_sessions).pack(side="right", pady=(4, 0))
        self.undo_button(prow, "tracker").pack(side="right", padx=8, pady=(4, 0))
        self.tk_pages["Past sessions"] = ph
        self.tk_pages["Map stats"] = self._tracker_stats_page(body)
        # (2.82.0: the options are on their own page, Overlay ↳ Settings - build_ov_settings)
        tk.Label(body, text="Reads only Path of Exile 2's own log file (Client.txt) on your PC: never the game's memory, "
                            "never its servers, never sends keys or clicks.", bg=P1, fg=C["steel"], font=("Segoe UI", 9),
                 anchor="w").pack(side="bottom", fill="x", padx=12, pady=(0, 8))
        self.tracker_view()
        self.tracker_fill_history()
        self.root.after(1000, self.tracker_tick)
        if cfg.get("autostart"):                         # 2.14.0: a session starts with the app (once Client.txt is read)
            self.root.after(4000, self.tracker_autostart)
        # (the numbers show while a session runs - beta 10; 2.70.1: each part has its switch in Options)

    # ---------------- 2.1.0: statistics for every map you ran, with a leaderboard of your fastest runs
    def _tracker_stats_page(self, body):
        P1, P2 = C["panel"], C["panel2"]
        page = tk.Frame(body, bg=P1)
        srow = tk.Frame(page, bg=P1)
        srow.pack(fill="x", pady=(0, 4))
        ttk.Button(srow, text="Export CSV", command=self.tracker_export_runs).pack(side="right")
        self.tk_stats_sum = tk.Label(srow, text="", bg=P1, fg=C["text"], anchor="w", justify="left",
                                     font=("Segoe UI", 9, "bold"))
        self.tk_stats_sum.pack(side="left", fill="x", expand=True)
        split = tk.Frame(page, bg=P1)
        split.pack(fill="both", expand=True)
        split.columnconfigure(0, weight=3, uniform="s")
        split.columnconfigure(1, weight=2, uniform="s")
        split.rowconfigure(0, weight=1)
        left = tk.Frame(split, bg=P1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        cols = (("map", "Map", 170, "w"), ("runs", "Runs", 50, "e"), ("best", "Best", 65, "e"),
                ("avg", "Average", 70, "e"), ("deaths", "Deaths", 55, "e"), ("last", "Last run", 90, "w"))
        tv = ttk.Treeview(left, columns=[c[0] for c in cols], show="headings", height=6, selectmode="browse")
        for cid, title, w, a in cols:
            tv.heading(cid, text=title, command=lambda c=cid: self.tracker_stats_sort(c))
            tv.column(cid, width=w, anchor=a, stretch=(cid == "map"))
        sb = ttk.Scrollbar(left, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tv.pack(fill="both", expand=True)
        tv.bind("<<TreeviewSelect>>", lambda e: self.tracker_board())
        self.tk_stats = tv
        rgo, right = chrome_section(split, "Leaderboard", padx=8, pady=8)      # 2.69.0
        rgo.grid(row=0, column=1, sticky="nsew")
        self.tk_board_title = _BarTitle(rgo.section_bar)
        ttk.Button(right, text="🏆 Global leaderboards", style="Quiet.TButton",          # 2.86.0
                   command=lambda: self.shell.open("leaderboards")).pack(anchor="e")
        bcols = (("rank", "#", 30, "e"), ("time", "Time", 70, "e"), ("when", "When", 110, "w"), ("lvl", "Level", 50, "e"),
                 ("deaths", "Deaths", 55, "e"))
        bv = ttk.Treeview(right, columns=[c[0] for c in bcols], show="headings", height=6, selectmode="none")
        for cid, title, w, a in bcols:
            bv.heading(cid, text=title)
            bv.column(cid, width=w, anchor=a, stretch=(cid == "when"))
        bv.tag_configure("gold", foreground="#ffd25a")
        bv.tag_configure("live", foreground=C["green"])
        bv.pack(fill="both", expand=True, pady=(4, 0))
        self.tk_board = bv
        tk.Label(right, text="Your fastest runs of the map you pick on the left. Time = time inside the map (hideout "
                             "visits in between don't count); visits under 30 seconds aren't counted.",
                 bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left", wraplength=320).pack(fill="x", pady=(4, 0))
        # ---- 2.7.0: maps per day
        dyo, day = chrome_section(page, "Maps per day (last 14 days)", padx=8, pady=8)   # 2.69.0
        dyo.pack(fill="x", pady=(8, 0))
        self.tk_daily = tk.Canvas(day, height=110, bg=P2, highlightthickness=0)
        self.tk_daily.pack(fill="x")
        self.tk_daily.bind("<Configure>", lambda e: self.tracker_draw_daily())
        self.tk_stats_sort_col, self.tk_stats_rev = "runs", True
        return page

    def tracker_draw_daily(self):
        """Bars: maps each day; the number on top, a red dot when you died that day."""
        from .tracker import daily_maps
        cv = getattr(self, "tk_daily", None)
        if cv is None:
            return
        cv.delete("all")
        rows = daily_maps(self.tk_sessions.items, self.tk_session)
        w, h = max(cv.winfo_width(), 300), int(cv.cget("height"))
        top, bottom = 16, 18
        most = max((r[1] for r in rows), default=0) or 1
        slot = w / len(rows)
        bw = max(6, min(34, slot * 0.6))
        for i, (d, maps, deaths, secs) in enumerate(rows):
            x = slot * i + slot / 2
            bh = (h - top - bottom) * maps / most
            y1 = h - bottom
            if maps:
                cv.create_rectangle(x - bw / 2, y1 - bh, x + bw / 2, y1, fill=C["accent"], outline="")
                cv.create_text(x, y1 - bh - 7, text=str(maps), fill=C["text"], font=("Segoe UI", 8, "bold"))
                if deaths:
                    cv.create_oval(x + bw / 2 - 3, y1 - bh - 3, x + bw / 2 + 5, y1 - bh + 5, fill=C["red"], outline="")
            else:
                cv.create_line(x - bw / 2, y1 - 1, x + bw / 2, y1 - 1, fill=C["line"])
            label = "today" if i == len(rows) - 1 else d.strftime("%a %d")
            cv.create_text(x, h - 7, text=label, fill=C["muted"], font=("Segoe UI", 7))
        if not any(r[1] for r in rows):
            cv.create_text(w / 2, (h - bottom) / 2, text="No maps in the last 14 days.", fill=C["muted"],
                           font=("Segoe UI", 9))

    def _csv_path(self, name):
        from tkinter import filedialog
        return filedialog.asksaveasfilename(defaultextension=".csv", initialfile=name, filetypes=[("CSV", "*.csv")])

    def tracker_export_runs(self):
        """2.2.0: every map run (all sessions) as a spreadsheet file."""
        from .csvexport import write_map_runs
        path = self._csv_path("map_runs.csv")
        if path:
            n = write_map_runs(path, self.tk_sessions.items, self.tk_session)
            self._say(f"Saved {n} map runs to {path}.", 8)

    def tracker_export_sessions(self):
        from .csvexport import write_sessions
        path = self._csv_path("sessions.csv")
        if path:
            n = write_sessions(path, self.tk_sessions.items)
            self._say(f"Saved {n} sessions to {path}.", 8)

    def tracker_stats_sort(self, col):
        self.tk_stats_rev = (not self.tk_stats_rev) if self.tk_stats_sort_col == col else (col != "map")
        self.tk_stats_sort_col = col
        self.tracker_fill_stats()

    def tracker_fill_stats(self):
        from .tracker import map_stats
        st = map_stats(self.tk_sessions.items, self.tk_session)
        self.tk_stats_data = st
        tv = self.tk_stats
        keep = tv.selection()
        tv.delete(*tv.get_children())
        key = {"map": lambda kv: kv[0].lower(), "runs": lambda kv: kv[1]["runs"], "best": lambda kv: kv[1]["best"],
               "avg": lambda kv: kv[1]["avg"], "deaths": lambda kv: kv[1]["deaths"],
               "last": lambda kv: kv[1]["last"]}[self.tk_stats_sort_col]
        for name, d in sorted(st.items(), key=key, reverse=self.tk_stats_rev):
            tv.insert("", "end", iid=name, values=(name, d["runs"], fmt_time(d["best"]), fmt_time(d["avg"]), d["deaths"],
                                                   datetime.fromtimestamp(d["last"]).strftime("%b %d")))
        runs = sum(d["runs"] for d in st.values())
        if st:
            most = max(st.items(), key=lambda kv: kv[1]["runs"])
            fast = min(st.items(), key=lambda kv: kv[1]["best"])
            self.tk_stats_sum.config(text=f"{runs:,} map runs · {len(st)} different maps · most run: {most[0]} "
                                          f"({most[1]['runs']}) · fastest: {fast[0]} in {fmt_time(fast[1]['best'])}")
        else:
            self.tk_stats_sum.config(text="No maps yet: start a session and run some maps - they show up here, with "
                                          "your best times.")
        self.tracker_draw_daily()
        if keep and tv.exists(keep[0]):
            tv.selection_set(keep[0])
        elif tv.get_children():
            tv.selection_set(tv.get_children()[0])
        self.tracker_board()

    def tracker_board(self):
        bv = self.tk_board
        bv.delete(*bv.get_children())
        sel = self.tk_stats.selection()
        d = getattr(self, "tk_stats_data", {}).get(sel[0]) if sel else None
        if not d:
            self.tk_board_title.config(text="Leaderboard")
            return
        self.tk_board_title.config(text=f"🏆 {sel[0]}: your fastest runs")
        for i, r in enumerate(d["list"][:10]):
            tags = ("live",) if r.get("live") else (("gold",) if i == 0 else ())
            bv.insert("", "end", values=(i + 1, fmt_time(r["time"]),
                                         "now (running)" if r.get("live") else
                                         datetime.fromtimestamp(r["when"]).strftime("%b %d %H:%M"),
                                         r["level"] or "-", r["deaths"]), tags=tags)

    def _tracker_options(self, po):
        """2.82.0 (feedback: options "a more predominant feature ... reorganizing ... grouping"): Overlay ↳ Settings,
        in cards - On the bar, Features, Campaign, Behaviour, then the Mechanic Helper (build_ov_settings)."""
        cfg, P2 = self.tracker_cfg(), C["panel2"]
        cards = tk.Frame(po, bg=C["panel"])
        cards.pack(fill="x")
        for c in range(2):
            cards.columnconfigure(c, weight=1, uniform="ovc")
        self.tk_ov_switches = {}

        def card(r, c, title, text=None):
            o, b = chrome_section(cards, title, text) if text else chrome_section(cards, title)
            o.grid(row=r, column=c, sticky="nsew", padx=(0 if c == 0 else 6, 6 if c == 0 else 0), pady=(0, 8))
            return b

        def switches(parent, items, cols, prefix=""):
            g = tk.Frame(parent, bg=P2)
            g.pack(fill="x")
            for i, (label, v, fn) in enumerate(items):
                cb = ttk.Checkbutton(g, text=label, variable=v, command=fn, style="Card.TCheckbutton")
                cb.grid(row=i // cols, column=i % cols, sticky="w", padx=(0, 24), pady=2)
                self.tk_ov_switches[prefix + label] = cb
            for c in range(cols):
                g.columnconfigure(c, uniform="sw")
            return g

        def sub(parent, text, top=0):
            tk.Label(parent, text=text, bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(
                fill="x", pady=(top, 2))
        # ---- On the bar: the numbers, then the switches and menus on it
        bar = card(0, 0, "On the bar", "What the overlay's bar shows over the game. Its look, layout and opacity: "
                                       "Settings › Appearance.")
        self.tk_line_vars = {}
        nums = []
        for k, label in LINE_NAMES:
            v = self.tk_timer_var if k == "session" and getattr(self, "tk_timer_var", None) is not None else \
                tk.BooleanVar(value=bool(cfg["lines"].get(k, True)))
            self.tk_line_vars[k] = v
            nums.append((label, v, self.tracker_options_changed))
        self.ingame_clock_var = tk.BooleanVar(value=bool(cfg.get("clock", True)))     # 2.39.0 (2.52.0: was in Settings)
        nums.append(("Clock", self.ingame_clock_var, self.on_ingame_clock))
        sub(bar, "Numbers")
        switches(bar, nums, 3)
        self.tk_switches_var = tk.BooleanVar(value=bool(cfg.get("alerts_bar", True)))
        self.tk_bar_vars = {"focus": tk.BooleanVar(value=bool(self.bar_cfg().get("focus", True))),
                            "notes": tk.BooleanVar(value=bool(self.bar_cfg().get("notes", True))),
                            "calc": tk.BooleanVar(value=bool(self.bar_cfg().get("calc", True))),
                            "campaign": tk.BooleanVar(value=bool(self.bar_cfg().get("campaign", True))),
                            "vendor": tk.BooleanVar(value=bool(self.bar_cfg().get("vendor", True)))}
        sub(bar, "Switches and menus - flip a feature mid-game (it keeps working when its switch isn't on the bar)", 8)
        switches(bar, (("Mechanic Helper switches", self.tk_switches_var, self.tracker_switches_switch),
                       ("Focus switch", self.tk_bar_vars["focus"], self.tracker_bar_switch),
                       ("Campaign switch", self.tk_bar_vars["campaign"], self.tracker_bar_switch),
                       ("Notes ▾", self.tk_bar_vars["notes"], self.tracker_bar_switch),
                       ("Calc ▾", self.tk_bar_vars["calc"], self.tracker_bar_switch),
                       ("Vendor ▾ (in town)", self.tk_bar_vars["vendor"], self.tracker_bar_switch)), 2, prefix="bar:")
        # ---- Features
        feat = card(0, 1, "Features", "Switch off what you don't want over the game.")
        self.tk_notes_var = tk.BooleanVar(value=bool(self._ensure_overlay().cfg.get("notes_enabled", True)))
        self.tk_calc_var = tk.BooleanVar(value=bool(self.calc_cfg()["on"]))          # 2.74.0
        from . import focus as F                                  # 2.73.0: League Focus (Overlay ↳ Game Plan)
        self.tk_focus_var = tk.BooleanVar(value=bool(F.cfg()["on"]))
        self.tk_fline_var = tk.BooleanVar(value=bool(F.cfg()["line"]))
        self.tk_rank_ask = tk.BooleanVar(value=self.rank_ask_on())               # 2.76.0
        self.tk_ws_var = tk.BooleanVar(value=bool(self.ws_cfg().get("on")))        # 2.81.0
        switches(feat, (("Notes", self.tk_notes_var, self.tracker_notes_switch),
                        ("Calculator", self.tk_calc_var, self.tracker_calc_switch),
                        ("League Focus", self.tk_focus_var, lambda: self.focus_set_on(bool(self.tk_focus_var.get()))),
                        ("Focus line (its own bar)", self.tk_fline_var, self.tracker_fline_switch),
                        ("Ask me to rank maps I haven't ranked", self.tk_rank_ask, self.tracker_rank_ask_switch),
                        ("Desecration Helper (at the Well)", self.tk_ws_var,
                         lambda: self.alerts_toggle("desecrate", bool(self.tk_ws_var.get())))), 2)
        # ---- Campaign: its switches, then its own options (route, splits ...)
        camp = card(1, 0, "Campaign", "The Campaign Helper: where you are, what's next and what it's worth - from the "
                                      "game's log. Click its line on the overlay for the act's route, rewards and "
                                      "splits.")
        from . import campaign as CP                              # 2.77.0: the Campaign Helper
        self.tk_camp_var = tk.BooleanVar(value=bool(CP.cfg()["on"]))
        self.tk_cline_var = tk.BooleanVar(value=bool(CP.cfg()["line"]))
        self.tk_cvendor_var = tk.BooleanVar(value=bool(CP.cfg()["vendor"]))
        switches(camp, (("Campaign Helper", self.tk_camp_var, lambda: self.camp_set_on(bool(self.tk_camp_var.get()))),
                        ("Campaign line (on the goal bar)", self.tk_cline_var, self.camp_line_switch),
                        ("Vendor search (in town)", self.tk_cvendor_var, self.camp_vendor_switch)), 2)
        self.camp_options(po, into=camp)
        # ---- Behaviour
        box = card(1, 1, "Behaviour")
        self.tk_lock = tk.BooleanVar(value=bool(cfg.get("mlocked")))      # 2.59.0: ONE lock for the whole overlay
        self.tk_tips_var = tk.BooleanVar(value=bool(cfg.get("tips", True)))      # 2.73.4: what each switch is for
        self.tk_auto = tk.BooleanVar(value=bool(cfg.get("autostart")))           # 2.14.0
        self.overlay_hide_capture()                                                    # (2.89.1: its one-time reset)
        self.tk_hidecap = tk.BooleanVar(value=bool(cfg.get("hide_capture", False)))   # 2.85.2
        lk = tk.Frame(box, bg=P2)
        lk.grid(row=3, column=0, columnspan=3, sticky="w")
        sw = switches(lk, (("Lock the overlay (can't be moved or resized by accident)", self.tk_lock,
                            self.tracker_options_changed),
                           ("Feature tips - hover a switch for what it does; a short card the first time you turn "
                            "one on", self.tk_tips_var, self.tracker_tips_switch),
                           ("Start tracking when StashOfExile2 starts", self.tk_auto, self.tracker_options_changed),
                           ("Hide the bar from screen captures while the Ritual or Delirium watcher runs - only if the "
                            "bar covers a counter they read; while it's on, screenshots won't show the bar", self.tk_hidecap, self.tracker_hidecap_switch)), 1)
        self.tk_ov_switches["tips"] = self.tk_ov_switches.pop("Feature tips - hover a switch for what it does; a "
                                                              "short card the first time you turn one on")
        del sw
        ch = tk.Frame(box, bg=P2)                       # 2.7.0: whose deaths count
        ch.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))
        tk.Label(ch, text="Your character name", bg=P2, fg=C["text"]).pack(side="left")
        self.tk_char = tk.StringVar(value=cfg.get("character", ""))
        ttk.Entry(ch, textvariable=self.tk_char, width=22).pack(side="left", padx=(8, 0))
        self.tk_char.trace_add("write", lambda *a: self.tracker_char_set())
        self.tk_char_hint = tk.Label(box, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w",
                                     justify="left", wraplength=600)
        self.tk_char_hint.grid(row=6, column=0, columnspan=3, sticky="w")
        self.tracker_char_hint()
        op = tk.Frame(box, bg=P2)                       # 2.3.0: own row - it used to sit on top of its label
        op.grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))
        # 2.52.0 (feedback: opacity was here AND in Appearance): one place for how every overlay looks
        tk.Label(op, text="Style, layout and opacity of the overlay:", bg=P2, fg=C["text"]).pack(side="left")
        ttk.Button(op, text="Settings › Appearance", style="Quiet.TButton",
                   command=self.appearance_open).pack(side="left", padx=(8, 0))
        box2 = tk.Frame(box, bg=P2)                                            # 2.82.0: keys, in Behaviour
        box2.grid(row=8, column=0, columnspan=3, sticky="w", pady=(8, 0))
        # 2.57.0: keys are set in Settings › Hotkeys only - here they're shown, with the way there
        self.tk_key_vars = {k: tk.StringVar(value=cfg.get(k, "")) for k in ("key_pause",)}
        self.tk_key_msg = tk.Label(box2, text="", bg=P2, fg=C["text"], font=("Segoe UI", 9), anchor="w", justify="left")
        self.tk_key_msg.grid(row=1, column=0, columnspan=3, sticky="w")
        ttk.Button(box2, text="Change in Settings › Hotkeys", style="Quiet.TButton",
                   command=lambda: self.hotkeys_open("tracker:key_overlay")).grid(row=2, column=0, sticky="w", pady=(4, 0))
        self._tk_keys_text()


    def tracker_hidecap_switch(self):
        """2.85.2: the bar in / out of screen captures."""
        self.tracker_cfg()["hide_capture"] = bool(self.tk_hidecap.get())
        self.tracker_save()
        self.overlay_click_through()

    def build_ov_settings(self, body):
        """2.82.0: Overlay ↳ Settings - cards (On the bar, Features, Campaign, Behaviour) and the Mechanic Helper."""
        P1 = C["panel"]
        po = ScrollArea(body, bg=P1)
        po.pack(fill="both", expand=True, padx=8, pady=8)
        self.tk_opt_area = po
        self._tracker_options(po.inner)
        mo, mb = chrome_section(po.inner, "Mechanic Helper", "Small helpers for league mechanics. They only watch and "
                                                            "show - they never act in the game. Click one on the "
                                                            "overlay to switch it on or off.")
        mo.pack(fill="x")
        self.build_alerts_panel(mb).pack(fill="x")
        self.ovh_pages = getattr(self, "ovh_pages", {})
        self.ovh_pages.update({"Mechanic Helper": mo})
        return po

    def tracker_view(self):
        if self.tk_view.get() == "Map stats":
            self.tracker_fill_stats()
        for name, f in self.tk_pages.items():
            if name == self.tk_view.get():
                f.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            else:
                f.pack_forget()

    def tracker_options_changed(self):
        cfg = self.tracker_cfg()
        for k, v in self.tk_line_vars.items():
            cfg["lines"][k] = bool(v.get())
        cfg["autostart"] = bool(self.tk_auto.get())
        self.overlay_lock(bool(self.tk_lock.get()))           # (saves, and redraws the overlay with its parts)

    # 2.70.1: the overlay's switches
    def tracker_timer_switch(self):
        """Timer over the game: the session's time only - the other numbers, the switches and Notes stay."""
        if getattr(self, "tk_line_vars", None) is None:
            self.tracker_cfg()["lines"]["session"] = bool(self.tk_timer_var.get())
            self.tracker_save()
            return self.merged_build()
        return self.tracker_options_changed()

    def tracker_notes_switch(self):
        on = bool(self.tk_notes_var.get())
        self.overlay.cfg["notes_choice"] = True                # (kept as you set it, not switched back on at start)
        self.overlay.set_notes(on)
        self.merged_build()

    def tracker_calc_switch(self):
        """2.74.0: the calculator over the game on / off (off: its window and Calc ▾ go)."""
        on = bool(self.tk_calc_var.get())
        self.calc_cfg()["on"] = on
        if not on:
            self.calc_ov_close(remember=False)
        self.calc_save()
        self.merged_build()

    def tracker_rank_ask_switch(self):
        self.tracker_cfg()["rank_ask"] = bool(self.tk_rank_ask.get())
        self.tracker_save()

    def tracker_fline_switch(self):
        from . import focus as F
        F.cfg()["line"] = bool(self.tk_fline_var.get())
        F.save()
        self.merged_build()

    def tracker_bar_switch(self):
        """2.73.0: a feature's switch on the overlay's bar shown or not (the feature keeps working)."""
        b = self.bar_cfg()
        for k, v in self.tk_bar_vars.items():
            b[k] = bool(v.get())
        self.tracker_save()
        self.tracker_helpers_sync()
        self.merged_build()

    def tracker_switches_switch(self):
        on = bool(self.tk_switches_var.get())
        self.tracker_cfg()["alerts_bar"] = on
        if getattr(self, "al_bar", None) is not None:
            self.al_bar.set(on)
        self.tracker_save()
        self.tracker_helpers_sync()

    def overlay_lock(self, on):
        """2.59.0: one lock for everything over the game (the timer, the switches, Notes) - the 🔒 on the overlay and
        Lock it in Options are the same switch."""
        cfg = self.tracker_cfg()
        cfg["mlocked"] = cfg["locked"] = bool(on)
        self.overlay.cfg["notes_locked"] = bool(on)
        if getattr(self, "tk_lock", None) is not None and bool(self.tk_lock.get()) != bool(on):
            self.tk_lock.set(bool(on))
        self.tracker_save()
        self.overlay.save_settings()
        self.merged_build()
        if self.overlay.notes is not None:                  # a dropped-down note (Strip, Minimal)
            self.overlay.restyle()
        self.calc_ov_restyle()                               # 2.74.0: the calculator follows the one lock

    def _tk_keys_text(self):
        from .overlay import key_label
        cfg = self.tracker_cfg()
        if getattr(self, "tk_key_msg", None) is not None:
            self.tk_key_msg.config(text=f"Show / hide the overlay: {key_label(cfg.get('key_overlay')) or 'none'}     "
                                        f"Pause / resume the timer: {key_label(cfg.get('key_pause')) or 'none'} "
                                        f"(or ⏸ / ▶ on the overlay)")

    def tracker_save_keys(self):
        cfg, bad = self.tracker_cfg(), []
        for k, v in self.tk_key_vars.items():
            txt = v.get().strip()
            if txt and not parse_key(txt):
                bad.append(txt)
                continue
            cfg[k] = txt
        self.tracker_save()
        clash = self.hotkey_clashes()
        msg = ("Not understood: " + ", ".join(bad)) if bad else ("Saved. " + ("Clash: " + "; ".join(clash) if clash else ""))
        self.tk_key_msg.config(text=msg, fg=C["red"] if bad or clash else C["green"])
        self.tracker_keys_hint()

    def tracker_keys_hint(self):
        """The keys next to Start (2.10.0), so you know they exist."""
        from .overlay import key_label
        cfg = self.tracker_cfg()
        parts = [f"{what} {key_label(cfg[k])}" for k, what in (("key_pause", "Pause / resume"),) if cfg.get(k)]
        if getattr(self, "tk_keys_lbl", None) is not None:
            self.tk_keys_lbl.config(text=("In game: " + "  ·  ".join(parts)) if parts else "")

    # ---------------- the game log
    def tracker_pick_log(self):
        p = filedialog.askopenfilename(parent=self.root, title="Find Path of Exile 2's Client.txt (in its logs folder)",
                                       filetypes=[("Client.txt", "Client.txt"), ("Text", "*.txt"), ("All files", "*.*")])
        if p:
            self.tracker_set_log(p)

    def tracker_set_log(self, p):
        """2.59.0: Settings › General › Game sets the game's log file ('' = find it by itself)."""
        self.tracker_cfg()["log_path"] = p
        self.tracker_save()
        self.tk_reader = None
        if getattr(self, "tk_log_lbl", None) is not None:
            self.tracker_open_log()
        self.game_log_text()

    def game_log_text(self):
        lbl = getattr(self, "log_path_lbl", None)
        if lbl is None:
            return
        mine = self.tracker_cfg().get("log_path") or ""
        found = find_log(mine or None)
        txt = (f"{found}" + ("" if mine else "  (found by itself)")) if found else \
            "Not found - press Change… and pick Client.txt in the game's logs folder."
        try:
            lbl.config(text=txt, fg=C["text"] if found else C["red"])
        except tk.TclError:
            pass

    def tracker_open_log(self):
        """-> True if the log is being followed."""
        if self.tk_reader is not None and not self.tk_reader.error:
            return True
        path = find_log(self.tracker_cfg().get("log_path"))
        if not path:
            self.tk_log_lbl.config(text="Client.txt wasn't found, so maps aren't counted (the timer still "
                                        "works). It's in the game's logs folder, usually:\n"
                                        "  Steam: C:\\Program Files (x86)\\Steam\\steamapps\\common\\Path of Exile 2\\logs\n"
                                        "  Standalone: C:\\Program Files (x86)\\Grinding Gear Games\\Path of Exile 2\\logs\n"
                                        "(or the same folders in your Steam library on another drive).",
                                   fg=C["good"], justify="left")
            if not self.tk_pick_btn.winfo_ismapped():
                self.tk_pick_btn.pack(side="right", anchor="n", before=self.tk_log_lbl)   # 2.34.0: keeps its room
            return False
        self.tk_pick_btn.pack_forget()
        self.tk_reader = LogReader(path)
        evs = self.tk_reader.start()
        self.tk_last_area = next((e for e in reversed(evs) if e[0] == "area"), None)
        self.tk_others = {e[2]["who"].lower() for e in evs if e[0] == "party"}       # 2.7.0: other players seen
        self.tk_last_scene = next((e for e in reversed(evs) if e[0] == "scene" and e[2]["name"] != "Atlas"), None)
        size = os.path.getsize(path) / 1048576 if os.path.exists(path) else 0
        self.tk_log_lbl.config(text=f"Following {path} ({size:,.0f} MB - only new lines are read). "
                                    "Right-click here to use a different Client.txt.", fg=C["muted"])
        return True

    def tracker_char_set(self):
        cfg = self.tracker_cfg()
        cfg["character"] = self.tk_char.get().strip()
        self.tracker_save()
        self.tracker_char_hint()

    def tracker_char_hint(self):
        cfg = self.tracker_cfg()
        guess = cfg.get("character_guess")
        if (cfg.get("character") or "").strip():
            txt = "Only this character's deaths count - party members' deaths don't."
        elif guess:
            txt = (f"Counting deaths for {guess} (worked out from the log). Not you? Type your character's name. "
                   "Party members' deaths don't count.")
        else:
            txt = ("Deaths count for you only, not party members. Leave it empty and the app works it out, or type "
                   "your character's name.")
        self.tk_char_hint.config(text=txt)

    def tracker_is_me(self, who):
        """Is this death yours? Your character name (Options) if you set it; otherwise anyone who hasn't joined or
        left your area (the game only logs that for other players). The first death counted that way names you."""
        cfg = self.tracker_cfg()
        mine = (cfg.get("character") or "").strip().lower()
        w = (who or "").strip().lower()
        if mine:
            return w == mine
        if w in getattr(self, "tk_others", set()):
            return False
        if cfg.get("character_guess", "").lower() != w:
            cfg["character_guess"] = who
            self.tracker_save()
            if hasattr(self, "tk_char_hint"):
                self.tracker_char_hint()
        return True

    def tracker_tick(self):
        try:
            s = self.tk_session
            if s is not None and s.ended is None and self.tk_reader is not None:
                changed = False
                for kind, ts, data in self.tk_reader.poll():
                    if kind == "party":
                        self.tk_others = getattr(self, "tk_others", set()) | {data["who"].lower()}
                        continue
                    if kind in ("area", "level"):              # 2.73.1: League Focus watches these too
                        self.focus_log(kind, data)
                        self.maprank_log(kind, data)          # 2.76.0: ask for a rank after a map
                    self.campaign_log(kind, ts, data)         # 2.77.0: the Campaign Helper
                    if kind == "death" and not self.tracker_is_me(data["who"]):
                        continue                              # a party member died, not you
                    changed |= s.feed(kind, ts, data)
                    if kind == "afk" and data["on"] and s.running():
                        s.pause(ts)
                        self.tk_afk_paused = True             # 2.7.0: AFK off resumes it (only a pause AFK made)
                        self.tk_pause_btn.config(text="Resume")
                        changed = True
                    elif kind == "afk" and not data["on"] and getattr(self, "tk_afk_paused", False):
                        self.tk_afk_paused = False
                        if s.paused_at is not None and s.ended is None:
                            s.resume(ts)
                            self.tk_pause_btn.config(text="Pause")
                            changed = True
                if changed:
                    self.tracker_fill_maps()
            self.tracker_game_watch()
            self.focus_tick()                                 # 2.73.1: a League Focus poke due?
            self.tracker_draw()
        except Exception:
            self.log_error("session tracker")
        self.root.after(1000, self.tracker_tick)

    # ---------------- 2.69.3: the game closed (or crashed) while a session runs -> ask to end it
    GAME_GONE_SECS = 15          # closed this long before asking (a restart of the game is quicker)
    RESTORED_GRACE = 60          # a session kept from the last time the app ran: the game gets this long to show up

    def tracker_game_watch(self, now=None, is_open=None):
        """Every 5 s while a session is open: is the game's window still there (overlay.game_open: window titles
        only, True when it can't tell)? Once it has been gone GAME_GONE_SECS, the session is paused at the moment
        it went and you're asked: End session / Keep it going. Only after the game was seen during this session -
        starting a session before the game is fine - or for a session kept from the last time the app ran (the
        app or PC crashed). The game coming back resumes it."""
        s = self.tk_session
        now = now or time.time()
        if s is None or s.ended is not None:
            self.tk_game = {"seen": False, "gone": None, "asked": False, "paused": False, "s": None}
            return None
        g = getattr(self, "tk_game", None)
        if g is None or g.get("s") is not s:
            g = self.tk_game = {"seen": False, "gone": None, "asked": False, "paused": False, "s": s,
                                "since": now, "restored": not getattr(s, "fresh", False)}
        if is_open is None:
            if now - g.get("checked", 0) < 5:
                return None
            g["checked"] = now
            from . import overlay as OV
            is_open = OV.game_open(self.overlay.cfg.get("poe_title") or OV.POE_TITLE)
        if is_open:
            back = g["paused"]
            g.update(seen=True, gone=None, asked=False, paused=False)
            if back and s.paused_at is not None:
                s.resume(now)
                self.tk_pause_btn.config(text="Pause")
                self._tk_strip_close()
                self._say("The game is back - the session goes on.", 8)
            return "open"
        if g["gone"] is None:
            g["gone"] = now
        if g["asked"]:
            return "asked"
        wait = self.GAME_GONE_SECS if g["seen"] else (self.RESTORED_GRACE if g["restored"] else None)
        if wait is None or now - (g["gone"] if g["seen"] else max(g["gone"], g["since"])) < wait:
            return "waiting"
        g["asked"] = True
        if s.paused_at is None:
            s.pause(g["gone"] if g["seen"] else now)          # the time after the game went doesn't count
            g["paused"] = True
            self.tk_pause_btn.config(text="Resume")
        self.tracker_game_ask()
        return "ask"

    def tracker_game_ask(self):
        msg = "Path of Exile 2 isn't running any more (closed or crashed). End this session?"
        self._tk_strip(msg, [("End session", self.tracker_game_end), ("Keep it going", self.tracker_game_keep)])
        self.tk_game_toast = self.app_toast(msg + " The time since it closed isn't counted.", "Session",
                                            actions=[("End session", self.tracker_game_end),
                                                     ("Keep it going", self.tracker_game_keep)], secs=600)

    def _tracker_game_toast_close(self):
        t = getattr(self, "tk_game_toast", None)
        try:
            if t is not None and t.winfo_exists():
                t.destroy()
        except Exception:
            pass
        self.tk_game_toast = None

    def tracker_game_end(self):
        self._tracker_game_toast_close()
        self._tk_strip_close()
        self._tracker_finish_now()

    def tracker_game_keep(self):
        """Keep the session: it stays paused if the game closing paused it (Resume, or the game coming back,
        goes on); asked again only after the game was seen and closed again."""
        self._tracker_game_toast_close()
        self._tk_strip_close()
        g = getattr(self, "tk_game", None) or {}
        g["seen"], g["restored"] = False, False
        self._say("The session is kept (paused). Resume it when you're back - or the game coming back does.", 8)

    # ---------------- start / pause / stop
    def tracker_autostart(self):
        if self.tk_session is None or self.tk_session.ended is not None:
            self.tracker_start()

    def tracker_toggle(self):
        if self.tk_session is None or self.tk_session.ended is not None:
            self.tracker_start()
        else:
            self.tracker_stop()

    def tracker_start(self):
        now = time.time()
        s = Session(now=now)
        s.fresh = True                                 # 2.69.3: started in this run of the app (not kept from the last)
        self.tk_session = s
        self.tracker_open_log()
        la = getattr(self, "tk_last_area", None)
        if la:                                     # where you are right now (from the end of the log)
            s.feed("area", now, la[2])
            sc = getattr(self, "tk_last_scene", None)
            if sc and sc[1] >= la[1]:
                s.feed("scene", now, sc[2])
        self.tk_start_btn.config(text="■ Stop", style="TButton")
        self.tk_pause_btn.config(state="normal", text="Pause")
        self._tk_strip_close()
        self.tracker_fill_maps()
        self.tracker_draw()
        self._say("Session started.", 8)
        if self.tk_overlay is None:                    # 2.70.1: what shows is up to its switches (Options)
            self.tracker_overlay_show()

    def tracker_pause_toggle(self):
        s = self.tk_session
        if not s or s.ended is not None:
            return
        self.tk_afk_paused = False                         # your own press: AFK off won't undo it
        if s.paused_at is None:
            s.pause()
            self.tk_pause_btn.config(text="Resume")
        else:
            s.resume()
            self.tk_pause_btn.config(text="Pause")
        self.tracker_draw()

    def tracker_stop(self):
        s = self.tk_session
        if not s or s.ended is not None:
            return
        self.tracker_finish()

    def tracker_open_ledger(self):
        """2.54.0: Money Makers › Strat Tracker, where profit is tracked."""
        self.shell.open("money")
        self.mm_page.pick("Strat Tracker", notify=False)
        self.mm_show_page()

    def tracker_after_count(self):
        """Wealth finished a count (wealth_page calls this). 2.54.0: the timer no longer waits for one."""

    def tracker_finish(self):
        self._tracker_finish_now()

    def ev_tracker(self, what):
        if what == "finish":
            self._tracker_finish_now()
        elif what == "toggle":
            self.tracker_toggle()
        elif what == "pause":
            self.tracker_play_click()                          # 2.74.3: as ⏸ / ▶ (starts it when it isn't running)
        elif what == "overlay":
            self.overlay_hide_toggle()
        elif what in ("camp_prev", "camp_next"):                    # 2.77.0: the campaign's ◀ ▶
            self.camp_step(-1 if what == "camp_prev" else 1)

    def _tracker_finish_now(self):
        s = self.tk_session
        self.tk_finishing = False
        if not s or s.ended is not None:
            return
        s.stop()
        self.tk_sessions.add(s)
        self.tk_start_btn.config(text="▶ Start tracking", style="Primary.TButton")
        self.tk_pause_btn.config(state="disabled", text="Pause")
        msg = f"Session done: {fmt_time(s.elapsed())}, {s.map_count()} map{'s' if s.map_count() != 1 else ''}."
        self._tk_strip(msg, [("OK", self._tk_strip_close)])
        self._say(msg, 15)
        self.tracker_fill_history()
        self.tracker_draw()
        self.root.after(8000, lambda: (self.tk_session is s and s.ended is not None) and self.tracker_overlay_hide())

    def _tk_strip(self, text, actions):
        for w in self.tk_strip_btns.winfo_children():
            w.destroy()
        self.tk_strip_lbl.config(text=text)
        for i, (label, fn) in enumerate(actions):
            ttk.Button(self.tk_strip_btns, text=label, command=fn, style="Primary.TButton" if i == 0 else "TButton").pack(
                side="left", padx=(8, 0))
        if not self.tk_strip.winfo_ismapped():
            self.tk_strip.pack(fill="x", padx=8, pady=(0, 8), after=self.tk_start_btn.master)

    def _tk_strip_close(self):
        self.tk_strip.pack_forget()

    # ---------------- drawing
    def tracker_numbers(self):
        s, now = self.tk_session, time.time()
        if s is None:
            return {}
        avg = s.avg_map_time(now)
        cur = s.current_map_time(now)
        runs = [(m["time"], m["name"]) for m in s.maps if m["time"] >= 30]
        best = f"{fmt_time(min(runs)[0])}  {min(runs)[1]}" if runs else "-"
        return {"time": fmt_time(s.elapsed(now)) + ("  (paused)" if s.paused_at and not s.ended else ""),
                "where": s.location(), "map": fmt_time(cur) if cur is not None else "-", "maps": str(s.map_count()),
                "avg": fmt_time(avg) if avg is not None else "-", "best": best,
                }

    def tracker_draw(self):
        s = self.tk_session
        n = self.tracker_numbers()
        for k, lab in self.tk_nums.items():
            lab.config(text=n.get(k, "-"))
        if s is None or s.ended is not None:
            self.tk_state.config(text="Not tracking", fg=C["muted"])
        elif s.paused_at is not None:
            self.tk_state.config(text="⏸ Paused", fg=C["good"])
        else:
            self.tk_state.config(text="● Tracking", fg=C["green"])
        self.tracker_overlay_draw(n)

    def tracker_fill_maps(self):
        tv = self.tk_maps
        tv.delete(*tv.get_children())
        s = self.tk_session
        if not s:
            return
        now = time.time()
        from .maplib import community, ranks
        mine, com = ranks(), community()
        for i, m in enumerate(s.maps):
            t = s.current_map_time(now) if (s.where and s.where.get("map") == i) else m["time"]
            rank = mine.get(m["name"]) or (f"({com[m['name']]['rank']})" if m["name"] in com else "")
            tv.insert("", "end", values=(i + 1, m["name"], m["level"], fmt_time(t), m["entries"], m["deaths"], rank))

    def tracker_fill_history(self):
        hv = self.tk_hist
        hv.delete(*hv.get_children())
        for i, s in reversed(list(enumerate(self.tk_sessions.items))):
            avg = s.avg_map_time()
            hv.insert("", "end", iid=str(i), values=(
                datetime.fromtimestamp(s.started).strftime("%b %d %H:%M"), fmt_time(s.elapsed()), s.map_count(),
                fmt_time(avg) if avg is not None else "-", s.note))

    def tracker_remove_sessions(self, rows):
        """2.4.0: Delete removes the selected past sessions (Ctrl+Z puts them back)."""
        items = self.tk_sessions.items
        idx = sorted({int(r) for r in rows if str(r).isdigit() and int(r) < len(items)}, reverse=True)
        gone = [(i, items[i]) for i in idx if items[i] is not self.tk_session]
        if not gone:
            return
        for i, _s in gone:
            del items[i]
        self.tk_sessions.save()
        label = f"{len(gone)} session{'s' if len(gone) != 1 else ''}"

        def restore():
            for i, s_ in sorted(gone, key=lambda g: g[0]):
                items.insert(min(i, len(items)), s_)
            self.tk_sessions.save()
            self.tracker_fill_history()
        self.push_undo("tracker", label, restore)
        self._say(f"Removed {label}. Ctrl+Z (or Undo) puts them back.", 8)
        self.tracker_fill_history()

    def tracker_edit_note(self, e):
        iid = self.tk_hist.identify_row(e.y)
        if not iid:
            return
        from tkinter import simpledialog
        s = self.tk_sessions.items[int(iid)]
        txt = simpledialog.askstring("Note", "A note for this session:", initialvalue=s.note, parent=self.root)
        if txt is not None:
            s.note = txt.strip()
            self.tk_sessions.save()
            self.tracker_fill_history()

    # ---------------- the timer over the game
    def tracker_overlay_toggle(self):
        cfg = self.tracker_cfg()
        if self.tk_overlay is not None:
            self.tracker_overlay_hide()
            cfg["overlay"] = False
        else:
            cfg["overlay"] = True
            self.tracker_overlay_show()
        self.tracker_save()

    def tracker_overlay_show(self):
        self.tracker_overlay_build()

    def tracker_overlay_hide(self):
        """The timer leaves the overlay window (the switches and Notes stay)."""
        self.mg_timer = False
        self.tk_overlay = None
        self.merged_build()

    def tracker_overlay_build(self):
        """The timer over the game: part of the one overlay window (merged_page.py; 2.59.0: always one window)."""
        self.mg_timer = True
        return self.merged_build()

    # ---------------- the Mechanic Helper switches (2.59.0: part of the one overlay window)
    HELPERS = ("breach", "delirium", "ritual", "remnant")
    HELPER_W = {"ritual": 11}                      # room for "Ritual 2/3", so the bar never changes size

    def tracker_helpers_build(self):
        """The four mechanic switches: part of the one overlay window (2.59.0: always one window)."""
        self.tracker_helpers_destroy()
        return self.merged_build()

    def tracker_helpers_destroy(self):
        w, self.tk_helpers = getattr(self, "tk_helpers", None), None
        self.tk_ov_alerts = {}
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    @staticmethod
    def _ov_rank(where):
        """2.32.0: the map's rank on the timer (yours, else the community's in brackets)."""
        if not where or where == "-":
            return ""
        import time as _t
        from .maplib import community, ranks
        cache = TrackerPage.__dict__.get("_ov_cache")
        if not cache or _t.time() - cache[0] > 5:              # (the timer redraws every second)
            cache = (_t.time(), ranks(), community())
            TrackerPage._ov_cache = cache
        r = cache[1].get(where)
        if r:
            return f"  [{'AVOID' if r == 'Avoid' else r}]"
        c = cache[2].get(where)
        return f"  ({c['rank']})" if c else ""

    def tracker_overlay_draw(self, n):
        self.tracker_helpers_paint()               # 2.49.0: the Mechanic Helper bar stands on its own
        if self.tk_overlay is None:
            return
        s = self.tk_session
        live = s is not None and s.ended is None
        show_where = bool(self.tracker_cfg()["lines"].get("where", True))       # 2.70.1
        texts = {"session": n.get("time", "0:00") if live else "not tracking",
                 "map": f"Map  {n.get('map', '-')}" + (f"   {n.get('where', '')}" if show_where and live and
                                                       n.get("where") not in ("-", None) else "")
                        + self._ov_rank(n.get("where") if live else None),
                 "maps": f"Maps  {n.get('maps', '0')}", "avg": f"Avg  {n.get('avg', '-')}",
                 }
        if getattr(self, "tk_ov_cv", None) is not None:    # 2.47.0: the skins' two columns
            where = n.get("where") if show_where and live and n.get("where") not in ("-", None) else ""
            texts.update(map=f"Map  {n.get('map', '-')}", where=where.strip())      # 2.76.0: the rank is its own part
        texts["rank"] = self.rank_text(n.get("where") if live and getattr(self, "_mr_in", None) else None)
        texts["focus"] = self.focus_line()[0]                 # 2.73.0: League Focus's line
        from . import campaign as CP
        texts["campaign"] = "▸ " + CP.line_text() if CP.active() else ""          # 2.77.0: the campaign line
        for k, lab in self.tk_ov_lbls.items():
            lab.config(text=texts.get(k, ""))
        self.play_refresh()                                   # 2.74.3: ⏸ / ▶ follows the timer
        if getattr(self, "tk_ov_clock", None) is not None:
            from .shell import clock_text
            try:
                self.tk_ov_clock.config(text=clock_text())          # time, and the date under it
            except tk.TclError:
                pass

    def tracker_helpers_paint(self):
        """The Mechanic Helper bar's cells: on (green) / off (red) / needs attention, Ritual's live count."""
        try:
            self.overlay_capture_sync()                            # 2.88.3: hidden from captures only while watching
        except Exception:
            self.log_error("the overlay's capture setting")
        if getattr(self, "tk_ov_alerts", None):
            states = self.alert_states()
            from . import focus as F                               # 2.73.0: the Focus switch on the bar
            states["focus"] = "on" if F.cfg()["on"] else "off"
            from . import campaign as CP                           # 2.77.0
            states["campaign"] = "on" if CP.cfg()["on"] else "off"
            for k, (dot, lab) in self.tk_ov_alerts.items():
                st = states.get(k, "off")
                from .merged_page import chip_name
                txt = chip_name(k)                                 # 2.89.2: full words (Expedition)
                if k == "ritual" and st == "on":                   # 2.14.0: the live count
                    from .utilities import RITUAL
                    if RITUAL.seen == "ok" and RITUAL.count:
                        txt = f"Ritual {RITUAL.count[0]}/{RITUAL.count[1]}"
                from .overlaywin import pal
                P = getattr(self, "mg_P", None) or pal()      # 2.65.0: the Game bar brings its own colors
                dot.config(fg=P[st], text=P["on_icon"] if st != "off" else P["off_icon"])   # green on, red off
                lab.config(text=txt, fg=P["text"] if st != "off" else P["muted"])

    def tracker_helpers_sync(self):
        """2.49.0 (feedback: "it's a different bar, independent of the session tracker"): the bar shows whenever its
        switch is on - timer or not, session or not - and only while the game is in front (like every overlay)."""
        on = bool(self.bar_chips())          # 2.70.1: its own switch, timer or not; 2.73.0: or the Focus switch
        shown = set(getattr(self, "tk_ov_alerts", None) or {})
        if on != bool(getattr(self, "mg_built", {}).get("helpers")) or (on and getattr(self, "mg_win", None) is None) \
                or (on and shown != set(self.bar_chips())):          # 2.73.0: which switches are on the bar changed
            self.merged_build()
        self.tracker_helpers_paint()

    def tracker_helper_click(self, key):
        """2.26.0: a click on a helper in the timer's bar switches it on / off."""
        if key == "focus":                                         # 2.73.0: League Focus on / off
            from . import focus as F
            self.focus_set_on(not F.cfg()["on"])
            return self.ov_intro_maybe(key)                        # 2.73.4: the first time: what it's for
        if key == "campaign":                                      # 2.77.0: the Campaign Helper on / off
            from . import campaign as CP
            self.camp_set_on(not CP.cfg()["on"])
            return self.ov_intro_maybe(key)
        on = self.alert_states().get(key, "off") != "off"
        try:
            self.alerts_toggle(key, not on)
        except Exception:
            self.log_error(f"switching {key} from the timer")
        self.tracker_overlay_draw(self.tracker_numbers())
        return self.ov_intro_maybe(key)

    def tracker_tips_switch(self):
        self.tracker_cfg()["tips"] = bool(self.tk_tips_var.get())
        if not self.tracker_cfg()["tips"]:
            self.ov_tip_hide()
        save_json("settings.json", SETTINGS)

    def tracker_helpers_settings(self):
        """2.26.0: the ⚙ on the timer's bar - 2.44.0: Overlays › Mechanic Helper, where its options are."""
        self.ovh_open("Mechanic Helper")
        try:
            self.root.deiconify()
            self.root.lift()
        except Exception:
            pass

    # ---------------- hotkeys (fed by the keyboard watcher, on its own thread)
    def tracker_on_key(self, vk, ctrl, alt, shift):
        if self.remnant_on_key(vk, ctrl, alt, shift):                   # 2.37.0: Expedition Remnant Price Checker
            return True
        if self.fl_on_key(vk, ctrl, alt, shift):                       # 2.45.0: Strat Tracker "a run is done"
            return True
        cfg = SETTINGS.get("tracker") or {}
        for key, action in (("key_pause", "pause"), ("key_overlay", "overlay"), ("key_camp_prev", "camp_prev"),
                            ("key_camp_next", "camp_next")):
            k = parse_key(cfg.get(key) or "")
            if k and k == (vk, ctrl, alt, shift):
                self.ui_q.put(("tracker", action))
                return bool(game_active())          # in game: the key is used up; elsewhere it still does its usual job
        return False

    def tracker_status(self):
        s = getattr(self, "tk_session", None)
        if s is None or s.ended is not None:
            return False
        return "warn" if s.paused_at is not None else True

    # ---------------- every hotkey in one list (Settings)
    def all_hotkeys(self):
        """[(what, key text, where it is set, editable key id or None)]"""
        ov = getattr(self, "overlay", None)
        oc = ov.cfg if ov else {}
        tc = self.tracker_cfg()
        # 2.57.0 (feedback: every key in Settings › Hotkeys, nowhere else): the third field is the group the key
        # belongs to (a heading on the Hotkeys page); every key but Ctrl+Alt+C is set here and only here
        rows = [("Price check the item under the mouse (in game)", SETTINGS.get("pc_key", "Ctrl+D"), "Price Checks",
                 "checks:pc_key"),
                ("Add the item under the mouse to Bulk Pricing", "Ctrl+Alt+C", "Bulk Pricing", None),
                ("One-key copy (experimental, in game)", SETTINGS.get("quick_copy_key", ""), "Bulk Pricing",
                 "checks:quick_copy_key"),
                ("Open poe2db's modifier list in your browser", SETTINGS.get("poe2db_key", ""), "Bulk Pricing",
                 "checks:poe2db_key"),
                ("Copy your stash search (in game)", SETTINGS.get("regex_key", ""), "Regex", "checks:regex_key"),
                ("Session timer: pause / resume (or ⏸ / ▶ on the overlay)", tc.get("key_pause", ""), "Overlays",
                 "tracker:key_pause"),
                ("Show / hide the overlay", tc.get("key_overlay", ""), "Overlays", "tracker:key_overlay"),
                ("Campaign: a step back (◀)", tc.get("key_camp_prev", ""), "Overlays", "tracker:key_camp_prev"),
                ("Campaign: a step on (▶)", tc.get("key_camp_next", ""), "Overlays", "tracker:key_camp_next"),
                ("Expedition Remnant Price Checker (in game)", self.remnant_cfg().get("key", ""), "Overlays",
                 "remnant:key"),
                ("Strat Tracker: a run is done (setups counted by key)", SETTINGS.get("ledger_key") or "Ctrl+Alt+N",
                 "Money Makers", "checks:ledger_key"),
                ("Go to hideout", oc.get("hideout_key", ""), "Chat commands", "overlay:hideout_key")]
        for i, c in enumerate(oc.get("commands", []) or []):
            if c.get("cmd"):
                rows.append((f"Chat: {c.get('name') or c.get('cmd', '')}", c.get("key", ""), "Chat commands",
                             f"cmd:{i}"))
        return rows

    def hotkey_clashes(self):
        seen, out = {}, []
        for what, key, _w, _id in self.all_hotkeys():
            k = parse_key(key) if key and key != "Ctrl+Alt+C" else ((0x43, True, True, False) if key == "Ctrl+Alt+C" else None)
            if not k:
                continue
            if k in seen:
                out.append(f"{key_label(key)} is used by \"{seen[k]}\" and \"{what}\"")
            else:
                seen[k] = what
        return out
