"""The Session tracker utility (2.0 beta 9): its window, the timer overlay over the game, and its hotkeys.

Mixed into App. The logic is in tracker.py, the game log reading in gamelog.py. Wealth is only READ: at the start
the tracker notes what your Wealth holds; at the end it compares, both at the same (latest) prices."""
import copy
import os
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, ttk

from .config import save_json, SETTINGS
from .gamelog import find_log, LogReader
from .overlay import game_active, key_label, parse_key
from .pricefmt import fmt_div
from .style import ScrollArea, C, FONT_TITLE, KeyCapture, SegBar
from .tracker import fmt_time, Session, Sessions, value_at
from .wealth import WEALTH, wealth_key, WPRICES

DEFAULTS = {"overlay": True, "locked": False, "x": 60, "y": 260, "w": 230, "h": 190, "opacity": 225,
            "lines": {"session": True, "map": True, "maps": True, "avg": True, "profit": True, "gold": False},
            "key_toggle": "", "key_pause": "", "ask_count": True, "log_path": "",
            "character": "", "character_guess": "", "alerts_bar": True, "autostart": False}
DEFAULT_KEYS = {"key_toggle": "Ctrl+Alt+S", "key_pause": "Ctrl+Alt+P"}       # 2.10.0: set once, change them in Options
LINE_NAMES = [("session", "Session time"), ("map", "This map's time"), ("maps", "Maps done"), ("avg", "Average map"),
              ("profit", "Profit")]        # (2.3.0: "gold from selling" is gone - it can't be read reliably)


PROFIT_HOW = ("How it works: when you press Start, the app notes what everything in Wealth is worth. When you press "
              "Stop, it values Wealth again - both times at today's prices, so price swings don't count. Profit is "
              "the difference; per hour is the profit divided by the session's time (pauses don't count). So it "
              "needs Wealth set up: your currency counted, and any synced stash tabs.")


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
                                        ("maps", "Maps"), ("avg", "Average map"), ("best", "Fastest map"),
                                        ("profit", "Profit"), ("ph", "Profit / hour"))):
            f = tk.Frame(nums, bg=P2, padx=8, pady=8, highlightthickness=1, highlightbackground=C["line"])
            f.grid(row=i // 4, column=i % 4, sticky="nsew", padx=(0, 8), pady=(0, 8))
            tk.Label(f, text=label, bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(anchor="w")
            v = tk.Label(f, text="-", bg=P2, fg=C["text"], font=("Segoe UI", 10 if k == "where" else 13, "bold"), anchor="w")
            v.pack(anchor="w")
            self.tk_nums[k] = v
        for c in range(4):
            nums.columnconfigure(c, weight=1, uniform="n")
        # ---- 2.10.0: alerts while you play (Delirium, Breach) on the main page
        self.build_alerts_panel(body).pack(fill="x", padx=8, pady=(0, 8))

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
        hv = ttk.Treeview(ph, columns=("when", "len", "maps", "avg", "profit", "ph", "note"), show="headings", height=4)
        for cid, title, w, a in (("when", "Started", 120, "w"), ("len", "Length", 70, "e"), ("maps", "Maps", 50, "e"),
                                 ("avg", "Avg map", 70, "e"), ("profit", "Profit", 90, "e"), ("ph", "Per hour", 90, "e"),
                                 ("note", "Note", 200, "w")):
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
        ttk.Checkbutton(box, text="Lock it (can't be moved or resized by accident)", variable=self.tk_lock,
                        command=self.tracker_options_changed).grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))
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
        tk.Label(op, text="Opacity", bg=P2, fg=C["text"]).pack(side="left")
        self.tk_opacity = tk.IntVar(value=int(cfg.get("opacity", 225)))
        ttk.Scale(op, from_=60, to=255, variable=self.tk_opacity, orient="horizontal", length=160,
                  command=lambda _v: self.tracker_options_changed()).pack(side="left", padx=(8, 0))
        tk.Label(op, text="(lower = see more of the game through it)", bg=P2, fg=C["muted"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(8, 0))
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
        # ---- 2.4.0: profit explained, with its one setting next to it
        box3 = tk.Frame(po, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
        box3.pack(fill="x", pady=(8, 0))
        tk.Label(box3, text="Profit / hour", bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(box3, text=PROFIT_HOW, bg=P2, fg=C["text"], anchor="w", justify="left", wraplength=620,
                 font=("Segoe UI", 9)).pack(fill="x", pady=(2, 4))
        self.tk_ask = tk.BooleanVar(value=bool(cfg.get("ask_count", True)))
        ttk.Checkbutton(box3, text="When I press Stop, let me count the currency I picked up first (recommended)",
                        variable=self.tk_ask, command=self.tracker_options_changed).pack(anchor="w")
        tk.Label(box3, text="Without it, only what changed in your synced stash tabs counts - currency in your "
                            "inventory or counted by hand would be left out.", bg=P2, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w", justify="left", wraplength=620).pack(fill="x", padx=(24, 0))
        self.tk_profit_state = tk.Label(box3, text="", bg=P2, fg=C["good"], anchor="w", justify="left",
                                        wraplength=620, font=("Segoe UI", 9))
        self.tk_profit_state.pack(fill="x", pady=(8, 0))
        self.tk_profit_btn = ttk.Button(box3, text="Set up Wealth", command=self.tracker_setup_wealth)
        self.tracker_profit_state()

    def tracker_profit_state(self):
        """The line under Profit / hour: can a profit be worked out right now, and if not, why."""
        if not hasattr(self, "tk_profit_state"):
            return
        labs = SETTINGS.get("labs")
        empty = not (WEALTH.holdings or any(WEALTH.items.values()))
        if not labs:
            txt, btn = "Profit needs Wealth, which is in Labs: turn on Labs in Settings > General.", False
        elif empty:
            txt, btn = "Wealth is empty, so there's nothing to compare against yet - set it up first.", True
        else:
            txt, btn = "Ready: the next session you start will show its profit when you stop.", False
        self.tk_profit_state.config(text=txt, fg=C["green"] if txt.startswith("Ready") else C["good"])
        if btn:
            self.tk_profit_btn.pack(anchor="w", pady=(4, 0))
        else:
            self.tk_profit_btn.pack_forget()

    def tracker_setup_wealth(self):
        if not SETTINGS.get("labs"):
            return self._say("Wealth is in Labs: turn on Labs in Settings > General first.", 8)
        self.shell.open("wealth")
        self.wealth_setup_open()

    def tracker_view(self):
        if self.tk_view.get() == "Map stats":
            self.tracker_fill_stats()
        if self.tk_view.get() == "Options":
            self.tracker_profit_state()
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
        cfg["opacity"] = int(float(self.tk_opacity.get()))
        cfg["ask_count"] = bool(self.tk_ask.get())
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
            self.tk_log_lbl.config(text="Client.txt wasn't found, so maps aren't counted (the timer and profit still "
                                        "work). It's in the game's logs folder, usually:\n"
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
        items = copy.deepcopy(WEALTH.all_items())
        s = Session(now=now, start_items=items)
        s.start_value = value_at(items, WPRICES, WEALTH.overrides, wealth_key) if items else None
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
        self._say("Session started." + ("" if s.start_value is not None else " (Wealth is empty, so no profit can be "
                                                                              "worked out; the timer and maps still work.)"), 8)
        if s.start_value is None:                       # 2.4.0: say why, and how to fix it, where you're looking
            self._tk_strip("Timing your maps. Profit needs Wealth to know what you own at the start - it's empty, so "
                           "this session won't show a profit.", [("Set up Wealth", self.tracker_setup_wealth),
                                                                 ("OK", self._tk_strip_close)])
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
        if self.tracker_cfg().get("ask_count") and s.start_value is not None:
            s.pause()
            self._tk_strip("Count what you picked up? Wealth opens: copy each currency stack you have now (Ctrl+C), "
                           "then press Finish counting - the profit is worked out right after. (Timer is paused.)",
                           [("Count now", self.tracker_count_first), ("Skip, finish now", self.tracker_finish),
                            ("Keep playing", self.tracker_keep_going)])
            return
        self.tracker_finish()

    def tracker_keep_going(self):
        self._tk_strip_close()
        if self.tk_session and self.tk_session.paused_at is not None:
            self.tk_session.resume()

    def tracker_count_first(self):
        self.tk_waiting_count = True
        self._tk_strip("Counting in Wealth: copy your new stacks (Ctrl+C), then press Finish counting there - the "
                       "session ends by itself after that.", [("Finish now", self.tracker_finish)])
        self.shell.open("wealth")
        if not self.w_counting:
            self.wealth_count_toggle()

    def tracker_after_count(self):
        """Wealth finished a count (wealth_page calls this)."""
        if self.tk_waiting_count:
            self.tk_waiting_count = False
            self.root.after(300, self.tracker_finish)

    def tracker_finish(self):
        s = self.tk_session
        if not s or s.ended is not None or self.tk_finishing:
            return
        self.tk_finishing = True
        self.tk_waiting_count = False
        self._tk_strip("Working out the profit (fresh prices from poe.ninja)…", [])
        lg = SETTINGS.get("league")

        def work():
            try:
                if lg:
                    WPRICES.ensure(lg)
            except Exception:
                pass
            self.ui_q.put(("tracker", "finish"))
        threading.Thread(target=work, daemon=True).start()

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
        end_items = WEALTH.all_items()
        start_now = value_at(s.start_items, WPRICES, WEALTH.overrides, wealth_key) if s.start_items else None
        end_now = value_at(end_items, WPRICES, WEALTH.overrides, wealth_key) if end_items else None
        profit = (end_now - start_now) if (start_now is not None and end_now is not None) else None
        s.stop(end_value=end_now, profit=profit)
        self.tk_sessions.add(s)
        self.tk_start_btn.config(text="▶ Start tracking", style="Primary.TButton")
        self.tk_pause_btn.config(state="disabled", text="Pause")
        ph = s.per_hour()
        msg = (f"Session done: {fmt_time(s.elapsed())}, {s.map_count()} map{'s' if s.map_count() != 1 else ''}"
               + (f", profit {'+' if profit >= 0 else '-'}{fmt_div(abs(profit))}" if profit is not None else "")
               + (f" ({fmt_div(ph)} per hour)" if ph is not None else "") + ".")
        self._tk_strip(msg + " Both ends are valued at today's prices, so price changes don't count as profit.",
                       [("OK", self._tk_strip_close)])
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
        prof = s.profit
        ph = s.per_hour() if s.ended else None
        runs = [(m["time"], m["name"]) for m in s.maps if m["time"] >= 30]
        best = f"{fmt_time(min(runs)[0])}  {min(runs)[1]}" if runs else "-"
        return {"time": fmt_time(s.elapsed(now)) + ("  (paused)" if s.paused_at and not s.ended else ""),
                "where": s.location(), "map": fmt_time(cur) if cur is not None else "-", "maps": str(s.map_count()),
                "avg": fmt_time(avg) if avg is not None else "-", "best": best,
                "start": fmt_div(s.start_value) if s.start_value is not None else "-",
                "profit": (('+' if prof >= 0 else '-') + fmt_div(abs(prof))) if prof is not None else
                ("worked out when you stop" if s.ended is None and s.start_value is not None else
                 "needs Wealth" if s.start_value is None else "-"),
                "ph": (('+' if ph >= 0 else '-') + fmt_div(abs(ph))) if ph is not None else
                ("when you stop" if s.ended is None and s.start_value is not None else "-")}

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
            ph = s.per_hour()
            hv.insert("", "end", iid=str(i), values=(
                datetime.fromtimestamp(s.started).strftime("%b %d %H:%M"), fmt_time(s.elapsed()), s.map_count(),
                fmt_time(avg) if avg is not None else "-",
                (('+' if s.profit >= 0 else '-') + fmt_div(abs(s.profit))) if s.profit is not None else "-",
                fmt_div(ph) if ph is not None else "-", s.note))

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
        if self.tk_overlay is not None:
            self._tracker_store_geo()
            self.tk_overlay.destroy()
            self.tk_overlay = None
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
        from .overlaywin import OverlayWindow, BODY_BG
        cfg = self.tracker_cfg()
        if self.tk_overlay is not None:
            self._tracker_store_geo()
            self.tk_overlay.destroy()
        fg = "#ffd9a8"

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
        inner = tk.Frame(w.body, bg=BODY_BG, padx=8, pady=4)
        inner.pack(fill="both", expand=True)
        self.tk_ov_lbls = {}
        for k, _label in LINE_NAMES:
            if cfg["lines"].get(k):
                lab = tk.Label(inner, text="", bg=BODY_BG, fg=fg if k == "session" else "#e8eefc",
                               font=("Segoe UI", 16 if k == "session" else 10, "bold" if k in ("session", "profit") else "normal"),
                               anchor="w")
                lab.pack(fill="x")
                self.tk_ov_lbls[k] = lab
                if not cfg.get("locked"):
                    w.draggable(lab)
        if not cfg.get("locked"):
            w.draggable(inner)
        self.tk_ov_alerts = {}
        if cfg.get("alerts_bar", True):          # 2.26.0: "Helpers: ● Breach | ● Delirium | ● Ritual  ⚙"
            BB = "#16213a"
            bar = tk.Frame(w.body, bg=BB, padx=8, pady=2)
            bar.pack(side="bottom", fill="x", before=inner)
            tk.Label(bar, text="Helpers:", bg=BB, fg="#8b96b0", font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
            for i, k in enumerate(("breach", "delirium", "ritual", "remnant")):
                if i:
                    tk.Label(bar, text="|", bg=BB, fg="#3a4560", font=("Segoe UI", 9)).pack(side="left", padx=4)
                cell = tk.Frame(bar, bg=BB, cursor="hand2")
                cell.pack(side="left")
                dot = tk.Label(cell, text="\u25cf", bg=BB, fg="#ff5c5c", font=("Segoe UI", 9), cursor="hand2")
                dot.pack(side="left")
                lab = tk.Label(cell, text=k.title(), bg=BB, fg="#cfd8ea", font=("Segoe UI", 9, "bold"),
                               cursor="hand2")
                lab.pack(side="left", padx=(2, 0))
                for wd in (cell, dot, lab):                    # a click switches that helper on / off
                    wd.bind("<Button-1>", lambda e, k=k: self.tracker_helper_click(k))
                self.tk_ov_alerts[k] = (dot, lab)
            cog = tk.Label(bar, text="\u2699", bg=BB, fg="#8b96b0", font=("Segoe UI Symbol", 10), cursor="hand2")
            cog.pack(side="right")
            cog.bind("<Button-1>", lambda e: self.tracker_helpers_settings())
            if not cfg.get("locked"):
                w.draggable(bar)
        self.tk_overlay = w
        self.tracker_overlay_draw(self.tracker_numbers())
        w.show()                                   # only while the game (or the app) is in front (2.0 beta 15)

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
        if self.tk_overlay is None:
            return
        s = self.tk_session
        live = s is not None and s.ended is None
        texts = {"session": n.get("time", "0:00") if live else "not tracking",
                 "map": f"Map  {n.get('map', '-')}" + (f"   {n.get('where', '')}" if live and n.get("where") not in ("-", None) else "")
                        + self._ov_rank(n.get("where") if live else None),
                 "maps": f"Maps  {n.get('maps', '0')}", "avg": f"Avg  {n.get('avg', '-')}",
                 "profit": "Profit  " + (n["profit"] if s is not None and n.get("profit", "")[:1] in "+-"
                                         else "at stop" if s is not None and s.start_value is not None else "-"),
                 }
        for k, lab in self.tk_ov_lbls.items():
            lab.config(text=texts.get(k, ""))
        if getattr(self, "tk_ov_alerts", None):
            states = self.alert_states()
            for k, (dot, lab) in self.tk_ov_alerts.items():
                st = states.get(k, "off")
                txt = k.title()
                if k == "ritual" and st == "on":                   # 2.14.0: the live count
                    from .utilities import RITUAL
                    if RITUAL.seen == "ok" and RITUAL.count:
                        txt = f"Ritual {RITUAL.count[0]}/{RITUAL.count[1]}"
                dot.config(fg={"on": "#5ee08a", "off": "#ff5c5c", "warn": "#ffb347"}[st])   # green on, red off
                lab.config(text=txt, fg="#e8eefc" if st != "off" else "#8b96b0")

    def tracker_helper_click(self, key):
        """2.26.0: a click on a helper in the timer's bar switches it on / off."""
        on = self.alert_states().get(key, "off") != "off"
        try:
            self.alerts_toggle(key, not on)
        except Exception:
            self.log_error(f"switching {key} from the timer")
        self.tracker_overlay_draw(self.tracker_numbers())

    def tracker_helpers_settings(self):
        """2.26.0: the ⚙ on the timer's bar - the Session tracker window, where the helpers' options are."""
        self.shell.open("tracker")
        try:
            self.root.deiconify()
            self.root.lift()
        except Exception:
            pass

    # ---------------- hotkeys (fed by the keyboard watcher, on its own thread)
    def tracker_on_key(self, vk, ctrl, alt, shift):
        if self.remnant_on_key(vk, ctrl, alt, shift):                   # 2.37.0: Expedition Remnant Price Checker
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
                ("Show / hide notes", oc.get("notes_key", ""), "Notes", "overlay:notes_key"),
                ("Session tracker: start / stop", tc.get("key_toggle", ""), "Session tracker", "tracker:key_toggle"),
                ("Session tracker: pause / resume", tc.get("key_pause", ""), "Session tracker", "tracker:key_pause"),
                ("Expedition Remnant Price Checker (in game)", self.remnant_cfg().get("key", ""),
                 "Session tracker > Alerts", "remnant:key")]
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
