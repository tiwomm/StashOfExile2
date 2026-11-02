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
from .style import ScrollArea, C, FONT_TITLE, KeyCapture, SegBar, Tooltip
from .tracker import fmt_time, Session, Sessions

DEFAULTS = {"overlay": True, "locked": False, "x": 60, "y": 260, "w": 230, "h": 190, "opacity": 225,
            "lines": {"session": True, "map": True, "maps": True, "avg": True},   # 2.54.0: no profit (Farm Ledger has it)
            "key_toggle": "", "key_pause": "", "ask_count": True, "log_path": "",
            "character": "", "character_guess": "", "alerts_bar": True, "autostart": False,
            "clock": True,
            "merged": True, "layout": "panel"}            # 2.55.0: one overlay window (merged_page.py), Panel / Strip                         # 2.39.0: the in-game clock on the timer (Settings > Appearance > Clock)
DEFAULT_KEYS = {"key_toggle": "Ctrl+Alt+S", "key_pause": "Ctrl+Alt+P"}       # 2.10.0: set once, change them in Options
# 2.54.0 (the user): the Session timer times your play; money lives in one place, Money Makers › Farm Ledger.
# Profit (Wealth at Stop minus at Start) is gone from here: its tiles, overlay line, options and Stop count.
LINE_NAMES = [("session", "Session time"), ("map", "This map's time"), ("maps", "Maps done"), ("avg", "Average map")]


class TrackerPage:
    # ---------------- set-up
    def tracker_cfg(self):
        cfg = SETTINGS.setdefault("tracker", {})
        for k, v in DEFAULTS.items():
            cfg.setdefault(k, copy.deepcopy(v))
        for k, v in DEFAULTS["lines"].items():
            cfg["lines"].setdefault(k, v)
        if not cfg.get("keys_210"):                  # 2.10.0: start / stop and pause get a key (only if you had none)
            cfg["keys_210"] = True
            for k, v in DEFAULT_KEYS.items():
                if not cfg.get(k):
                    cfg[k] = v
        return cfg

    def tracker_save(self):
        save_json("settings.json", SETTINGS)

    # ---------------- 2.44.0: Overlays - everything shown over the game, in one window
    OVH_TABS = ("Session timer", "Mechanic Helper", "Notes", "Appearance")      # 2.49.0: was "Look"

    def build_overlays_hub(self, body):
        """Overlays (was Session tracker): one tab per thing over the game - each with its own switch, key, place and
        options - and Look for all of them (parchment / classic, how see-through each one is)."""
        P1 = C["panel"]
        self.ovh_bar = SegBar(body, list(self.OVH_TABS), command=lambda v: self.ovh_show(), size=10, pad=(16, 4))
        self.ovh_bar.pack(anchor="w", padx=8, pady=(8, 0))
        tk.Frame(body, height=1, bg=C["line"]).pack(fill="x", padx=8)
        host = tk.Frame(body, bg=P1)
        host.pack(fill="both", expand=True)
        self.ovh_pages = {}
        page = tk.Frame(host, bg=P1)
        self.ovh_pages["Session timer"] = page
        self.build_tracker_window(page)
        for name in self.OVH_TABS[1:]:
            sa = ScrollArea(host, P1)
            self.ovh_pages[name] = sa
            inner = sa.inner
            if name == "Mechanic Helper":
                tk.Label(inner, text="Small helpers for league mechanics. They only watch and show - they never act in "
                                     "the game. Click one on the Mechanic Helper bar to switch it on or off.",
                         bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left",
                         wraplength=640).pack(fill="x", padx=12, pady=(8, 8))
                self.build_alerts_panel(inner).pack(fill="x", padx=8, pady=(0, 8))
            elif name == "Notes":
                self.build_notes_window(inner)
            else:
                self.build_overlay_look(inner)
        self.ovh_show()

    def ovh_show(self):
        cur = self.ovh_bar.get()
        for name, f in self.ovh_pages.items():
            if name == cur:
                f.pack(fill="both", expand=True)
            else:
                f.pack_forget()

    def ovh_open(self, tab):
        """Open Overlays at one tab (Settings' link, the old Notes window, the ⚙ on the Mechanic Helper bar)."""
        self.shell.open("tracker")
        if getattr(self, "ovh_bar", None) is not None:
            self.ovh_bar.pick(tab, notify=False)
            self.ovh_show()

    def build_tracker_window(self, body):
        cfg = self.tracker_cfg()
        P1, P2 = C["panel"], C["panel2"]
        self.tk_session, self.tk_sessions = None, Sessions()
        self.tk_reader, self.tk_waiting_count, self.tk_finishing = None, False, False
        self.tk_overlay = None
        # ---- top: start / pause, and where the log is
        top = tk.Frame(body, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
        top.pack(fill="x", padx=8, pady=(8, 8))
        self.tk_start_btn = ttk.Button(top, text="▶ Start tracking", style="Primary.TButton", command=self.tracker_toggle)
        self.tk_start_btn.pack(side="left")
        self.tk_pause_btn = ttk.Button(top, text="Pause", command=self.tracker_pause_toggle, state="disabled")
        self.tk_pause_btn.pack(side="left", padx=8)
        self.tk_state = tk.Label(top, text="Not tracking", bg=P2, fg=C["muted"], font=("Segoe UI", 12, "bold"))
        self.tk_state.pack(side="left", padx=12)
        self.tk_ov_btn = ttk.Button(top, text="Show timer", command=self.tracker_overlay_toggle)
        self.tk_ov_btn.pack(side="right")
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
        # 2.0 beta 21: only shown when Client.txt can't be found (right-click the line above to pick another one)
        self.tk_pick_btn = ttk.Button(lrow, text="Find Client.txt…", command=self.tracker_pick_log)
        self.tk_log_lbl.bind("<Button-3>", lambda e: self.tracker_pick_log())

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
        tk.Label(led, text="Profit is tracked per farming setup in Money Makers › Farm Ledger.", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9)).pack(side="left")
        ttk.Button(led, text="Open Farm Ledger", style="Quiet.TButton",
                   command=self.tracker_open_ledger).pack(side="left", padx=8)
        # (2.10.0's "Alerts while you play" panel is the Mechanic Helper tab since 2.44.0: build_overlays_hub)

        # ---- this session's maps / past sessions
        self.tk_view = SegBar(body, ["This session's maps", "Map stats", "Past sessions", "Options"],
                              command=lambda v: self.tracker_view(),
                              size=9, pad=(12, 4))
        self.tk_view.pack(anchor="w", padx=8, pady=(4, 8))
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
        po = ScrollArea(body, bg=P1)                   # 2.4.0: scrolls when the window is short
        self._tracker_options(po.inner)
        self.tk_pages["Options"] = po
        tk.Label(body, text="Reads only Path of Exile 2's own log file (Client.txt) on your PC: never the game's memory, "
                            "never its servers, never sends keys or clicks.", bg=P1, fg=C["steel"], font=("Segoe UI", 9),
                 anchor="w").pack(side="bottom", fill="x", padx=12, pady=(0, 8))
        self.tracker_view()
        self.tracker_fill_history()
        self.root.after(1000, self.tracker_tick)
        if cfg.get("autostart"):                         # 2.14.0: a session starts with the app (once Client.txt is read)
            self.root.after(4000, self.tracker_autostart)
        # (the timer shows while a session runs - beta 10; Show timer brings it up any time)

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
        right = tk.Frame(split, bg=P2, highlightthickness=1, highlightbackground=C["line"], padx=8, pady=8)
        right.grid(row=0, column=1, sticky="nsew")
        self.tk_board_title = tk.Label(right, text="Leaderboard", bg=P2, fg=C["accent"], anchor="w",
                                       font=("Segoe UI", 10, "bold"))
        self.tk_board_title.pack(fill="x")
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
        day = tk.Frame(page, bg=P2, highlightthickness=1, highlightbackground=C["line"], padx=8, pady=8)
        day.pack(fill="x", pady=(8, 0))
        tk.Label(day, text="Maps per day (last 14 days)", bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold"),
                 anchor="w").pack(fill="x")
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
        cfg, P2 = self.tracker_cfg(), C["panel2"]
        box = tk.Frame(po, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
        box.pack(fill="x")
        tk.Label(box, text="Options", bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w")
        tk.Label(box, text="What the small timer over the game shows:", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).grid(
            row=0, column=0, columnspan=3, sticky="e")
        self.tk_line_vars = {}
        for i, (k, label) in enumerate(LINE_NAMES):
            v = tk.BooleanVar(value=bool(cfg["lines"].get(k)))
            self.tk_line_vars[k] = v
            ttk.Checkbutton(box, text=label, variable=v, command=self.tracker_options_changed).grid(
                row=1 + i // 3, column=i % 3, sticky="w", padx=(0, 16))
        self.tk_auto = tk.BooleanVar(value=bool(cfg.get("autostart")))           # 2.14.0
        ttk.Checkbutton(box, text="Start tracking when StashOfExile2 starts", variable=self.tk_auto,
                        command=self.tracker_options_changed).grid(row=7, column=0, columnspan=3, sticky="w",
                                                                   pady=(8, 0))
        self.tk_lock = tk.BooleanVar(value=bool(cfg.get("locked")))
        lk = tk.Frame(box, bg=P2)
        lk.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Checkbutton(lk, text="Lock it (can't be moved or resized by accident)", variable=self.tk_lock,
                        command=self.tracker_options_changed).pack(side="left")
        self.ingame_clock_var = tk.BooleanVar(value=bool(cfg.get("clock", True)))     # 2.39.0 (2.52.0: was in Settings)
        ttk.Checkbutton(lk, text="Clock and date on the timer", variable=self.ingame_clock_var,
                        command=self.on_ingame_clock).pack(side="left", padx=(16, 0))
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
        # 2.52.0 (the user: opacity was here AND in Appearance): one place for how every overlay looks
        tk.Label(op, text="Style and opacity of the timer:", bg=P2, fg=C["text"]).pack(side="left")
        ttk.Button(op, text="Overlays › Appearance", style="Quiet.TButton",
                   command=lambda: self.ovh_open("Appearance")).pack(side="left", padx=(8, 0))
        box2 = tk.Frame(po, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
        box2.pack(fill="x", pady=(8, 0))
        tk.Label(box2, text="Hotkeys (work while the game is in front; also on the Hotkeys list in Settings)", bg=P2,
                 fg=C["accent"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")
        self.tk_key_vars = {}
        for i, (k, label) in enumerate((("key_toggle", "Start / stop"), ("key_pause", "Pause / resume"))):
            tk.Label(box2, text=label, bg=P2, fg=C["text"]).grid(row=1, column=i * 2, sticky="w", padx=(0, 8))
            v = tk.StringVar(value=cfg.get(k, ""))
            self.tk_key_vars[k] = v
            KeyCapture(box2, v, width=12, on_change=lambda t: self.tracker_save_keys()).grid(row=1, column=i * 2 + 1, sticky="w", padx=(0, 16))
        self.tk_key_msg = tk.Label(box2, text="Click a box and press the key. Esc keeps the old one; Backspace or "
                                              "right-click clears it.", bg=P2, fg=C["muted"], font=("Segoe UI", 9))
        self.tk_key_msg.grid(row=2, column=0, columnspan=5, sticky="w", pady=(4, 0))

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
        cfg["locked"] = bool(self.tk_lock.get())
        cfg["autostart"] = bool(self.tk_auto.get())
        self.tracker_save()
        if self.tk_overlay is not None:
            self.tracker_overlay_build()

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
        parts = [f"{what} {key_label(cfg[k])}" for k, what in (("key_toggle", "Start/stop"), ("key_pause", "Pause"))
                 if cfg.get(k)]
        if getattr(self, "tk_keys_lbl", None) is not None:
            self.tk_keys_lbl.config(text=("In game: " + "  ·  ".join(parts)) if parts else "")

    # ---------------- the game log
    def tracker_pick_log(self):
        p = filedialog.askopenfilename(parent=self.root, title="Find Path of Exile 2's Client.txt (in its logs folder)",
                                       filetypes=[("Client.txt", "Client.txt"), ("Text", "*.txt"), ("All files", "*.*")])
        if p:
            self.tracker_cfg()["log_path"] = p
            self.tracker_save()
            self.tk_reader = None
            self.tracker_open_log()

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
            self.tracker_draw()
        except Exception:
            self.log_error("session tracker")
        self.root.after(1000, self.tracker_tick)

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
        if self.tk_overlay is None and self.tracker_cfg().get("overlay"):
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
        """2.54.0: Money Makers › Farm Ledger, where profit is tracked."""
        self.shell.open("money")
        self.mm_page.pick("Farm Ledger", notify=False)
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
            self.tracker_pause_toggle()

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
        self.tk_ov_btn.config(text="Hide timer")

    def tracker_overlay_hide(self):
        if self.merged_on():                       # 2.55.0: the timer leaves the one window (the rest stays)
            self.mg_timer = False
            self.tk_overlay = None
            self.merged_build()
            self.tk_ov_btn.config(text="Show timer")
            return
        if self.tk_overlay is not None:
            self._tracker_store_geo()
            self.tk_overlay.destroy()
            self.tk_overlay = None
        # (2.49.0: the Mechanic Helper bar stays - it has its own switch)
        self.tk_ov_btn.config(text="Show timer")

    def _tracker_store_geo(self):
        w = self.tk_overlay
        try:
            if w is not None and w.winfo_ismapped() and w.winfo_width() > 1:
                self.tracker_cfg().update(x=w.winfo_x(), y=w.winfo_y(), w=w.winfo_width(), h=w.winfo_height())
        except Exception:
            pass

    def tracker_overlay_build(self):
        """The timer over the game: the shared over-the-game window (overlaywin.py, same look as Notes)."""
        from .overlaywin import OverlayWindow, pal
        cfg = self.tracker_cfg()
        if self.merged_on():                       # 2.55.0: one window for the timer, the switches and Notes
            self.mg_timer = True
            return self.merged_build()
        if self.tk_overlay is not None:
            self._tracker_store_geo()
            self.tk_overlay.destroy()
        P = pal()                                  # 2.43.0: parchment (or the classic dark look)
        BODY_BG, fg = P["bg"], P["big"]

        def moved(x, y, ww, hh):
            cfg.update(x=x, y=y, w=ww, h=hh)
            self.tracker_save()

        def lock(on):
            cfg["locked"] = bool(on)
            if getattr(self, "tk_lock", None) is not None:
                self.tk_lock.set(bool(on))
            self.tracker_save()
            self.tracker_overlay_build()
        w = OverlayWindow(self.root, "Session", "⏱", (cfg["x"], cfg["y"], cfg["w"], cfg["h"]),
                          opacity=int(cfg.get("opacity", 225)), locked=bool(cfg.get("locked")),
                          min_size=(140, 60), on_close=self.tracker_overlay_toggle, on_lock=lock, on_moved=moved,
                          drag_body=True, follow_game=True, no_activate=True)
        w.withdraw()
        self.tk_ov_lbls = {}
        self.tk_ov_clock = None
        self.tk_ov_cv = None
        if w.parch:                                # 2.47.0: the mockups' layout, drawn on the skin's background
            self._tracker_ov_canvas(w, cfg, P)
            self.tk_overlay = w
            self.tracker_helpers_sync()
            self.tracker_overlay_draw(self.tracker_numbers())
            w.show()
            return
        inner = tk.Frame(w.body, bg=BODY_BG, padx=8, pady=4)
        inner.pack(fill="both", expand=True)
        top = tk.Frame(inner, bg=BODY_BG)          # the session time, and (2.39.0) the clock on the same row
        top.pack(fill="x")
        if not cfg.get("locked"):
            w.draggable(top)
        if cfg.get("clock", True):                 # 2.39.0: clock + date like the app's taskbar clock, small, at the
            self.tk_ov_clock = tk.Label(top, text="", bg=BODY_BG, fg=P["muted"], font=(P["font"], 9),   # right -
                                        anchor="ne", justify="right")                                 # no extra line
            self.tk_ov_clock.pack(side="right", anchor="n", padx=(8, 0))
            if not cfg.get("locked"):
                w.draggable(self.tk_ov_clock)
        for k, _label in LINE_NAMES:
            if cfg["lines"].get(k):
                lab = tk.Label(top if k == "session" else inner, text="", bg=BODY_BG,
                               fg=fg if k == "session" else P["text"],
                               font=(P["font"], 18 if k == "session" else 10, "bold" if k == "session" else "normal"),
                               anchor="w")
                lab.pack(side="left", fill="x", expand=True) if k == "session" else lab.pack(fill="x")
                self.tk_ov_lbls[k] = lab
                if not cfg.get("locked"):
                    w.draggable(lab)
        if not cfg.get("locked"):
            w.draggable(inner)
        self.tk_overlay = w
        self.tracker_helpers_sync()                # 2.49.0: its own window, with its own switch
        self.tracker_overlay_draw(self.tracker_numbers())
        w.show()                                   # only while the game (or the app) is in front (2.0 beta 15)

    def _tracker_ov_canvas(self, w, cfg, P):
        """2.47.0 (the user: "the example you showed me looked so nice and clean"): Session on the title bar with the
        clock at its right; the big time; then two columns - Map 9:54 | Oasis, Maps 1 | Avg 9:54, Profit."""
        from .overlaywin import CanvasText
        cv = w.canvas_body()
        self.tk_ov_cv = cv
        # 2.51.0 (the user: "barely legible"): a size up and a halo round every letter. 2.53.0 ("a bit too harsh now"):
        # the rows back to plain weight, only the time and Profit bold, a thinner and softer halo
        f_big, f_row = (P["font"], 20, "bold"), (P["font"], 10)
        items = {"session": cv.create_text(12, 6, text="", anchor="nw", fill=P["big"], font=f_big)}
        lines = cfg["lines"]
        rows = []
        if lines.get("map"):
            rows.append(("map", "where"))
        if lines.get("maps") or lines.get("avg"):
            rows.append(("maps" if lines.get("maps") else None, "avg" if lines.get("avg") else None))
        for left, right in rows:
            if left:
                items[left] = cv.create_text(12, 0, text="", anchor="w", fill=P["text"],
                                             font=f_row)
            if right:
                items[right] = cv.create_text(0, 0, text="", anchor="e", fill=P["text"], font=f_row)

        halo = P.get("halo") if P.get("texture") else None
        self.tk_ov_lbls = {k: CanvasText(cv, it, P["bg"], halo=halo) for k, it in items.items()}
        lbl = self.tk_ov_lbls

        def layout(_e=None):
            wd = max(cv.winfo_width(), 120)
            y = 48
            for left, right in rows:
                if left:
                    lbl[left].place(12, y)
                if right:
                    lbl[right].place(wd - 12, y)
                y += 21
        cv.bind("<Configure>", layout, add="+")
        layout()
        if not cfg.get("locked"):
            w.draggable(cv)
        if cfg.get("clock", True):                 # the clock on the title bar, like the mockup - or, when it doesn't
            on_bar = P["align"] != "center" and not P.get("plate")      # fit there (2.50.0: it ran into "Session")
            clk = cv.create_text(0, 10, text="", anchor="ne", fill=P["muted"], font=(P["font"], 9),   # or the title is
                                 justify="right")                                                   # centred, top right
            cv.bind("<Configure>", lambda e: cv.coords(clk, e.width - 10, 10), add="+")

            class _Clock:
                text = ""

                def cget(self_, key):
                    return self_.text if key == "text" else ""

                def config(self_, text="", **_kw):
                    self_.text = text
                    fits = on_bar and w.bar_note(" · ".join(text.splitlines()))
                    if not fits:
                        w.bar_note("")
                    cv.itemconfigure(clk, text="" if fits else text)
            self.tk_ov_clock = _Clock()

    # ---------------- the Helpers bar (2.38.0: its own small window, shown with the timer, moved on its own)
    HELPERS = ("breach", "delirium", "ritual", "remnant")
    HELPER_W = {"ritual": 11}                      # room for "Ritual 2/3", so the bar never changes size

    def tracker_helpers_build(self):
        """● Breach | ● Delirium | ● Ritual | ● Remnant  ⚙ - one fixed-size bar (as big as its content, never cut
        off), shown and hidden with the Session timer but placed, moved and locked on its own."""
        from .overlaywin import OverlayWindow, pal
        cfg = self.tracker_cfg()
        P = pal()
        self.tracker_helpers_destroy()
        if self.merged_on():                             # 2.55.0: the switches live in the one window
            return self.merged_build()
        self.tk_ov_alerts = {}
        if not cfg.get("alerts_bar", True):
            return
        hx, hy = cfg.get("hx"), cfg.get("hy")
        first = hx is None or hy is None
        if first:                                        # first time: right under the timer (2.39.0: or above it)
            hx, hy = cfg["x"], cfg["y"] + cfg["h"] + 8

        def moved(x, y, _w, _h):
            cfg.update(hx=x, hy=y)
            self.tracker_save()

        def lock(on):
            cfg["hlocked"] = bool(on)
            self.tracker_save()
            self.tracker_helpers_build()
            self.tracker_overlay_draw(self.tracker_numbers())

        def close():                                     # × = no Helpers bar (Alerts panel: "Helpers bar")
            cfg["alerts_bar"] = False
            if getattr(self, "al_bar", None) is not None:
                self.al_bar.set(False)
            self.tracker_save()
            self.tracker_helpers_destroy()
        w = OverlayWindow(self.root, "Mechanic Helper", "\u25c9", (hx, hy, None, None),
                          opacity=int(cfg.get("hopacity", cfg.get("opacity", 225))),
                          locked=bool(cfg.get("hlocked")), min_size=(120, 30), on_close=close, on_lock=lock,
                          on_moved=moved, drag_body=True, follow_game=True, no_activate=True, resizable=False)
        w.withdraw()
        if w.parch:                                      # 2.47.0: drawn cells, like the mockups
            self._helpers_canvas(w, P)
            self.tk_helpers = w
            self._helpers_on_screen(w, hx, hy, first)
            w.show()
            return
        BB = P["bg"]
        bar = tk.Frame(w.body, bg=BB, padx=8, pady=4)
        bar.pack(fill="both", expand=True)
        for i, k in enumerate(self.HELPERS):
            if i:
                tk.Label(bar, text="|", bg=BB, fg=P["line"], font=("Segoe UI", 9)).pack(side="left", padx=4)
            cell = tk.Frame(bar, bg=BB, cursor="hand2")
            cell.pack(side="left")
            dot = tk.Label(cell, text="\u25c6", bg=BB, fg=P["off"], font=("Segoe UI", 9), cursor="hand2")
            dot.pack(side="left")
            lab = tk.Label(cell, text=k.title(), bg=BB, fg=P["text"], font=(P["font"], 10, "bold"), cursor="hand2",
                           width=self.HELPER_W.get(k, len(k) + 1), anchor="w")
            lab.pack(side="left", padx=(2, 0))
            for wd in (cell, dot, lab):                        # a click switches that helper on / off
                wd.bind("<Button-1>", lambda e, k=k: self.tracker_helper_click(k))
            self.tk_ov_alerts[k] = (dot, lab)
        cog = tk.Label(bar, text="\u2699", bg=BB, fg=P["muted"], font=("Segoe UI Symbol", 10), cursor="hand2")
        cog.pack(side="left", padx=(12, 0))
        cog.bind("<Button-1>", lambda e: self.tracker_helpers_settings())
        Tooltip(cog, "Mechanic Helper options (Overlays › Mechanic Helper)")
        self.tk_helpers = w
        self._helpers_on_screen(w, hx, hy, first)
        w.show()

    def _helpers_canvas(self, w, P):
        """One cell per helper - an icon (◆ on / ◇ off; ✓ / ✕ on the Quiet HUD) and its name - then ⚙."""
        from tkinter import font as tkfont
        from .overlaywin import CanvasText
        cv = w.canvas_body()
        fnt = (P["font"], 10, "bold")
        f = tkfont.Font(root=cv, family=P["font"], size=10, weight="bold")
        widths = {k: f.measure("Ritual 3/3" if k == "ritual" else k.title()) + 40 for k in self.HELPERS}
        x, h, gap = 8, 30, 6
        for k in self.HELPERS:
            tag = f"cell_{k}"
            cv.create_rectangle(x, 6, x + widths[k], 6 + h, fill=P["cell_bg"], outline=P["cell_line"], tags=(tag,))
            # 2.50.0: bigger, bright icons - the 9 pt dark diamonds read as black on parchment
            dot = cv.create_text(x + 14, 6 + h // 2, text=P["off_icon"], fill=P["off"], font=("Segoe UI Symbol", 12),
                                 tags=(tag,))
            lab = cv.create_text(x + 28, 6 + h // 2, text=k.title(), anchor="w", fill=P["text"], font=fnt, tags=(tag,))
            cv.tag_bind(tag, "<Button-1>", lambda e, k=k: self.tracker_helper_click(k))
            cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
            cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
            self.tk_ov_alerts[k] = (CanvasText(cv, dot, P["cell_bg"]), CanvasText(cv, lab, P["cell_bg"]))
            x += widths[k] + gap
        cog = cv.create_text(x + 8, 6 + h // 2, text="\u2699", fill=P["muted"], font=("Segoe UI Symbol", 12),
                             tags=("cog",))
        cv.tag_bind("cog", "<Button-1>", lambda e: self.tracker_helpers_settings())
        cv.configure(width=x + 24, height=h + 12)

    def _helpers_on_screen(self, w, hx, hy, first):
        """2.39.0: never off the screen. The timer often sits at the bottom of the screen, and "right under it" was
        below the screen's edge - the bar was there, just invisible. First time: under the timer if it fits, else
        above it. Any saved place that's off the screen (a monitor unplugged, another resolution) comes back on."""
        from .style import monitor_rect
        cfg = self.tracker_cfg()
        try:
            w.update_idletasks()
            bw, bh = max(w.winfo_reqwidth(), 120), max(w.winfo_reqheight(), 30)
            # 2.50.0: the whole screen, not its work area - the bar moved up a few pixels when locked at the very
            # bottom edge (the game is full screen; the Windows taskbar's strip is fine to sit on)
            l_, t, r, b = monitor_rect(self.root, hx + 10, hy + 10, full=True)
        except Exception:
            return
        if first and hy + bh > b:
            hy = cfg["y"] - bh - 8
        hx = max(l_, min(int(hx), r - bw))
        hy = max(t, min(int(hy), b - bh))
        if (hx, hy) != (cfg.get("hx"), cfg.get("hy")):
            cfg.update(hx=hx, hy=hy)
            self.tracker_save()
        w.geometry(f"+{hx}+{hy}")

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
        texts = {"session": n.get("time", "0:00") if live else "not tracking",
                 "map": f"Map  {n.get('map', '-')}" + (f"   {n.get('where', '')}" if live and n.get("where") not in ("-", None) else "")
                        + self._ov_rank(n.get("where") if live else None),
                 "maps": f"Maps  {n.get('maps', '0')}", "avg": f"Avg  {n.get('avg', '-')}",
                 }
        if getattr(self, "tk_ov_cv", None) is not None:    # 2.47.0: the skins' two columns
            where = n.get("where") if live and n.get("where") not in ("-", None) else ""
            texts.update(map=f"Map  {n.get('map', '-')}", where=(where + self._ov_rank(where or None)).strip())
        for k, lab in self.tk_ov_lbls.items():
            lab.config(text=texts.get(k, ""))
        if getattr(self, "tk_ov_clock", None) is not None:
            from .shell import clock_text
            try:
                self.tk_ov_clock.config(text=clock_text())          # time, and the date under it
            except tk.TclError:
                pass

    def tracker_helpers_paint(self):
        """The Mechanic Helper bar's cells: on (green) / off (red) / needs attention, Ritual's live count."""
        if getattr(self, "tk_ov_alerts", None):
            states = self.alert_states()
            for k, (dot, lab) in self.tk_ov_alerts.items():
                st = states.get(k, "off")
                txt = k.title()
                if k == "ritual" and st == "on":                   # 2.14.0: the live count
                    from .utilities import RITUAL
                    if RITUAL.seen == "ok" and RITUAL.count:
                        txt = f"Ritual {RITUAL.count[0]}/{RITUAL.count[1]}"
                from .overlaywin import pal
                P = pal()
                dot.config(fg=P[st], text=P["on_icon"] if st != "off" else P["off_icon"])   # green on, red off
                lab.config(text=txt, fg=P["text"] if st != "off" else P["muted"])

    def tracker_helpers_sync(self):
        """2.49.0 (the user: "it's a different bar, independent of the session tracker"): the bar shows whenever its
        switch is on - timer or not, session or not - and only while the game is in front (like every overlay)."""
        on = bool(self.tracker_cfg().get("alerts_bar", True))
        if self.merged_on():                             # 2.55.0: in the one window
            if getattr(self, "tk_helpers", None) is not None:
                self.tracker_helpers_destroy()
            if on != bool(getattr(self, "mg_built", {}).get("helpers")) or (on and getattr(self, "mg_win", None) is None):
                self.merged_build()
            self.tracker_helpers_paint()
            return
        if on and getattr(self, "tk_helpers", None) is None:
            self.tracker_helpers_build()
        elif not on and getattr(self, "tk_helpers", None) is not None:
            self.tracker_helpers_destroy()
        self.tracker_helpers_paint()

    def tracker_helper_click(self, key):
        """2.26.0: a click on a helper in the timer's bar switches it on / off."""
        on = self.alert_states().get(key, "off") != "off"
        try:
            self.alerts_toggle(key, not on)
        except Exception:
            self.log_error(f"switching {key} from the timer")
        self.tracker_overlay_draw(self.tracker_numbers())

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
        if self.fl_on_key(vk, ctrl, alt, shift):                       # 2.45.0: Farm Ledger "a run is done"
            return True
        cfg = SETTINGS.get("tracker") or {}
        for key, action in (("key_toggle", "toggle"), ("key_pause", "pause")):
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
        rows = [("Add the item under the mouse to Price checks", "Ctrl+Alt+C", "fixed", None),
                ("One-key copy (experimental, in game)", SETTINGS.get("quick_copy_key", ""), "Price checks",
                 "checks:quick_copy_key"),
                ("Copy your stash search (in game)", SETTINGS.get("regex_key", ""), "Regex", "checks:regex_key"),
                ("Open poe2db's modifier list in your browser", SETTINGS.get("poe2db_key", ""), "Settings > Hotkeys",
                 "checks:poe2db_key"),
                ("Go to hideout", oc.get("hideout_key", ""), "Settings > Chat commands", "overlay:hideout_key"),
                ("Show / hide notes", oc.get("notes_key", ""), "Overlays › Notes", "overlay:notes_key"),
                ("Session timer: start / stop", tc.get("key_toggle", ""), "Overlays › Session timer", "tracker:key_toggle"),
                ("Session timer: pause / resume", tc.get("key_pause", ""), "Overlays › Session timer", "tracker:key_pause"),
                ("Expedition Remnant Price Checker (in game)", self.remnant_cfg().get("key", ""),
                 "Overlays › Mechanic Helper", "remnant:key"),
                ("Farm Ledger: a run is done (setups counted by key)", SETTINGS.get("ledger_key") or "Ctrl+Alt+N",
                 "Money Makers › Farm Ledger", None)]
        for c in oc.get("commands", []) or []:
            rows.append((f"Chat: {c.get('cmd', '')}", c.get("key", ""), "Settings > Chat commands", None))
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
