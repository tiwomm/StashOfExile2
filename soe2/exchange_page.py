"""Exchange rates > Arbitrage (2.4.0): uneven rates on the Currency Exchange, and a check for a flip you see in game.
The numbers come from arbitrage.py (GGG's public hourly Currency Exchange history); see there for how it works."""
import threading
import tkinter as tk
from tkinter import ttk

from . import arbitrage as A
from .config import save_json, SETTINGS
from .rates import whole_ratio
from .style import C, MONO
from .util import _amt

LOOKBACK = {"Last hour": 1, "Last 3 hours": 3, "Last 6 hours": 6}


def _n(x):
    if x is None:
        return "-"
    if x >= 100:
        return f"{x:,.0f}"
    if x >= 1:
        return f"{x:,.2f}".rstrip("0").rstrip(".")
    return f"{x:.3g}"


class ExchangePage:
    """Mixed into App."""

    MAX_EDGE = 0.30          # 2.26.0: a "gain" above this is almost always thin, one-sided hourly data, not a real gap

    def build_arbitrage(self, page):
        P1, P2 = C["panel"], C["panel2"]
        head = tk.Frame(page, bg=P1, padx=14)                 # 2.26.0: BETA until it's fully developed
        head.pack(fill="x", pady=(10, 0))
        tk.Label(head, text="BETA", bg="#3a2a10", fg="#ffcf40", font=("Segoe UI", 8, "bold"), padx=6, pady=1,
                 highlightthickness=1, highlightbackground="#7a6428").pack(side="left")
        tk.Label(head, text="How to use: press Refresh. It reads the last finished hours of Grinding Gear Games' "
                            "Currency Exchange history (a few seconds). Rows appear when three trades in a row would "
                            "end with more than you started.", bg=P1, fg=C["text"], font=("Segoe UI", 9),
                 justify="left", anchor="w", wraplength=560).pack(side="left", padx=8, fill="x", expand=True)
        tk.Label(page, text="Markets on the Currency Exchange that priced the same thing differently in the last few "
                            "hours - from Grinding Gear Games' own hourly trade history. Each row is a loop of three "
                            "trades that would end with more than you started, at those hours' average rates. It's a "
                            "lead to check in game, not a sure profit: every trade costs gold, others see the same gap, "
                            "and rates move.", bg=P1, fg=C["muted"], justify="left", anchor="w", wraplength=640,
                 padx=14).pack(fill="x", pady=(10, 4))
        bar = tk.Frame(page, bg=P1, padx=14)
        bar.pack(fill="x", pady=(2, 6))
        self.arb_back = tk.StringVar(value=SETTINGS.get("arb_back", "Last 3 hours"))
        cb = ttk.Combobox(bar, textvariable=self.arb_back, values=list(LOOKBACK), state="readonly", width=12)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.arb_opts_changed())
        tk.Label(bar, text="at least", bg=P1, fg=C["muted"]).pack(side="left", padx=(12, 4))
        self.arb_edge = tk.StringVar(value=str(SETTINGS.get("arb_edge", 2)))
        ttk.Spinbox(bar, from_=1, to=50, textvariable=self.arb_edge, width=4,
                    command=self.arb_opts_changed).pack(side="left")
        tk.Label(bar, text="% gain, markets with at least", bg=P1, fg=C["muted"]).pack(side="left", padx=4)
        self.arb_depth = tk.StringVar(value=str(SETTINGS.get("arb_depth", 5)))
        ttk.Spinbox(bar, from_=0, to=1000, increment=5, textvariable=self.arb_depth, width=5,
                    command=self.arb_opts_changed).pack(side="left")
        tk.Label(bar, text="div traded", bg=P1, fg=C["muted"]).pack(side="left", padx=4)
        for v in (self.arb_edge, self.arb_depth):
            v.trace_add("write", lambda *a: self.root.after_idle(self.arb_opts_changed))
        self.arb_btn = ttk.Button(bar, text="Refresh", style="Accent.TButton", command=self.arb_refresh)
        self.arb_btn.pack(side="right")
        # 2.23.0: live scan - GGG publishes each hour when it ends; the app reads it as soon as it's out
        self.arb_live = tk.BooleanVar(value=bool(SETTINGS.get("arb_live")))
        ttk.Checkbutton(bar, text="Live scan", variable=self.arb_live,
                        command=self.arb_live_changed).pack(side="right", padx=(0, 10))
        self.arb_status = tk.Label(page, text="", bg=P1, fg=C["muted"], anchor="w", padx=14, justify="left")
        self.arb_status.pack(fill="x")
        tf = tk.Frame(page, bg=P1)                      # (packed last: the boxes below keep their room)
        cols = (("route", "Loop", 360, "w"), ("gain", "Gain", 70, "e"), ("depth", "Traded (div)", 104, "e"),
                ("hours", "Uneven in", 86, "e"))
        tv = ttk.Treeview(tf, columns=[c[0] for c in cols], show="headings", height=7)
        for cid, title, w, anchor in cols:
            tv.heading(cid, text=title)
            tv.column(cid, width=w, anchor=anchor, stretch=(cid == "route"))
        sb = ttk.Scrollbar(tf, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tv.pack(fill="both", expand=True)
        tv.tag_configure("odd", background=C["odd"])
        tv.tag_configure("steady", foreground=C["good"])
        tv.bind("<<TreeviewSelect>>", lambda e: self.arb_show_steps())
        self.list_register("rates", tv)
        self.arb_tv, self.arb_rows = tv, {}
        self.arb_steps = tk.Label(page, text="Pick a row to see the three trades.", bg=P2, fg=C["text"], anchor="nw",
                                  justify="left", font=(MONO, 9), padx=12, pady=8, highlightthickness=1,
                                  highlightbackground=C["line"])
        self.arb_steps.pack(side="bottom", fill="x", padx=14, pady=(6, 6))
        self.arb_steps.bind("<Configure>", lambda e: self.arb_steps.config(wraplength=max(300, e.width - 24)))
        # ---- a flip you see in game
        fl = tk.Frame(page, bg=P2, padx=14, pady=10, highlightthickness=1, highlightbackground=C["line"])
        fl.pack(side="bottom", fill="x", padx=14, pady=(0, 10), before=self.arb_steps)
        tk.Label(fl, text="Check a flip you see in game", bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(fl, text="On the Currency Exchange, hover the market ratio and hold Alt: it lists what people are "
                          "offering both ways. Type the two prices for one item here.", bg=P2, fg=C["muted"],
                 anchor="w", justify="left", wraplength=600).pack(fill="x")
        row = tk.Frame(fl, bg=P2)
        row.pack(fill="x", pady=(6, 0))
        self.flip_buy, self.flip_sell, self.flip_qty = tk.StringVar(), tk.StringVar(), tk.StringVar(value="100")
        self.flip_item, self.flip_cur = tk.StringVar(value="the item"), tk.StringVar(value="Exalted Orb")
        tk.Label(row, text="I can buy 1", bg=P2, fg=C["text"]).pack(side="left")
        ttk.Entry(row, textvariable=self.flip_item, width=18).pack(side="left", padx=4)
        tk.Label(row, text="for", bg=P2, fg=C["text"]).pack(side="left")
        ttk.Entry(row, textvariable=self.flip_buy, width=7).pack(side="left", padx=4)
        tk.Label(row, text="and sell 1 for", bg=P2, fg=C["text"]).pack(side="left")
        ttk.Entry(row, textvariable=self.flip_sell, width=7).pack(side="left", padx=4)
        ttk.Combobox(row, textvariable=self.flip_cur, values=["Exalted Orb", "Divine Orb", "Chaos Orb"],
                     width=12).pack(side="left", padx=4)
        row2 = tk.Frame(fl, bg=P2)
        row2.pack(fill="x", pady=(4, 0))
        tk.Label(row2, text="How many I'd flip", bg=P2, fg=C["text"]).pack(side="left")
        ttk.Entry(row2, textvariable=self.flip_qty, width=6).pack(side="left", padx=4)
        self.flip_out = tk.Label(fl, text="", bg=P2, fg=C["text"], anchor="w", justify="left", font=(MONO, 9))
        self.flip_out.pack(fill="x", pady=(6, 0))
        self.flip_out.bind("<Configure>", lambda e: self.flip_out.config(wraplength=max(300, e.width - 10)))
        for v in (self.flip_buy, self.flip_sell, self.flip_qty, self.flip_item, self.flip_cur):
            v.trace_add("write", lambda *a: self.flip_draw())
        self.flip_draw()
        tf.pack(fill="both", expand=True, padx=14, pady=(4, 0))
        if SETTINGS.get("arb_live"):                         # 2.23.0: Live scan was left on
            self.root.after(3000, lambda: self.arb_live_tick(first=True))

    # ---- 2.23.0: live scan
    LIVE_CHECK_MS = 5 * 60 * 1000                       # look for a newly finished hour every 5 minutes

    def arb_live_changed(self):
        SETTINGS["arb_live"] = bool(self.arb_live.get())
        save_json("settings.json", SETTINGS)
        if SETTINGS["arb_live"]:
            self.arb_live_seen = None                      # this scan's loops don't count as "new"
            self.arb_live_tick(first=True)
        self._say("Live scan on: each new hour of Currency Exchange history is read when it's out, and a new uneven "
                  "loop pops up." if SETTINGS["arb_live"] else "Live scan off.", 10)

    def arb_live_tick(self, first=False):
        """While Live scan is on: read the newest finished hour as soon as GGG publishes it (it's hourly - there is
        nothing more live to read), then say if a loop appeared that wasn't there before. Never more than one
        refresh at a time, and the reader already waits between requests and honours "slow down"."""
        job = getattr(self, "_arb_live_job", None)
        if job:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        self._arb_live_job = None
        if not SETTINGS.get("arb_live"):
            return
        league = SETTINGS.get("league")
        if league and not A.CX.busy:
            n = LOOKBACK.get(self.arb_back.get(), 3) if hasattr(self, "arb_back") else 3
            newest = A.CX.wanted(1)[0]
            if first or A.CX.league != league or newest not in A.CX.hours:
                threading.Thread(target=lambda: A.CX.refresh(league, n), daemon=True).start()
                self.root.after(300, self.arb_poll)
        self._arb_live_job = self.root.after(self.LIVE_CHECK_MS, self.arb_live_tick)

    def arb_live_notify(self, loops, newest=None):
        """A loop that wasn't in the last scan -> a popup (only while Live scan is on, and only when a new hour came
        in - changing the settings above doesn't count)."""
        keys = {" > ".join(a for a, _b, _r in lp["steps"]): lp for lp in loops}
        seen = getattr(self, "arb_live_seen", None)
        fresh = newest is not None and newest != getattr(self, "arb_live_newest", None)
        self.arb_live_newest = newest
        self.arb_live_seen = set(keys)
        if seen is None or not fresh or not SETTINGS.get("arb_live"):
            return []
        new = [lp for k, lp in keys.items() if k not in seen]
        if new:
            best = max(new, key=lambda lp: lp["edge"])
            names = [self.arb_name(a) for a, _b, _r in best["steps"]] + [self.arb_name(best["start"])]
            self.app_toast(" → ".join(names) + f"  (+{best['edge'] * 100:.1f} %)"
                           + (f" and {len(new) - 1} more" if len(new) > 1 else "") + ". Check it in game first.",
                           title="💱 New uneven loop on the Currency Exchange", secs=20, colour=C["good"])
        return new

    # ---- names
    def arb_name(self, cid):
        n = A.item_name(cid)                                 # 2.26.0: game ids -> names (cxnames.json)
        if n:
            return n
        try:
            from .wealth import WPRICES
            for part in (WPRICES.parts or {}).values():
                n = (part.get("names") or {}).get(cid)
                if n:
                    return n
        except Exception:
            pass
        return cid.rsplit("/", 1)[-1].replace("-", " ").title()

    # ---- refresh
    def arb_opts_changed(self):
        SETTINGS["arb_back"] = self.arb_back.get()
        for key, var in (("arb_edge", self.arb_edge), ("arb_depth", self.arb_depth)):
            try:
                SETTINGS[key] = float(var.get())
            except ValueError:
                pass
        save_json("settings.json", SETTINGS)
        self.arb_draw()

    def arb_refresh(self):
        league = SETTINGS.get("league")
        if not league:
            return self.arb_status.config(text="Pick your league in Settings first.", fg=C["red"])
        if A.CX.busy:
            return
        n = LOOKBACK.get(self.arb_back.get(), 3)
        threading.Thread(target=lambda: A.CX.refresh(league, n), daemon=True).start()
        self.arb_btn.config(state="disabled")
        self.root.after(300, self.arb_poll)

    def arb_poll(self):
        if A.CX.busy:
            self.arb_status.config(text=A.CX.msg or "Reading…", fg=C["muted"])
            return self.root.after(400, self.arb_poll)
        self.arb_btn.config(state="normal")
        self.arb_draw()

    def arb_draw(self):
        if not hasattr(self, "arb_tv"):
            return
        league = SETTINGS.get("league")
        n = LOOKBACK.get(self.arb_back.get(), 3)
        hours = [h for h in A.CX.wanted(n) if h in A.CX.hours] if A.CX.league == league else []
        per_hour = [A.combine([A.CX.hours[h]]) for h in hours]
        tot = A.combine([A.CX.hours[h] for h in hours])
        try:
            edge = max(0.0, float(self.arb_edge.get())) / 100
        except ValueError:
            edge = 0.02
        try:
            depth = max(0.0, float(self.arb_depth.get()))
        except ValueError:
            depth = 5.0
        loops = A.find_loops(tot, edge, depth) if tot else []
        wild = [lp for lp in loops if lp["edge"] > self.MAX_EDGE]          # 2.26.0: too good to be true
        loops = [lp for lp in loops if lp["edge"] <= self.MAX_EDGE]
        if hours:
            self.arb_live_notify(loops, max(hours))
        tv = self.arb_tv
        tv.delete(*tv.get_children())
        self.arb_rows = {}
        for i, lp in enumerate(loops[:200]):
            names = [self.arb_name(a) for a, _b, _r in lp["steps"]] + [self.arb_name(lp["start"])]
            k = A.hours_uneven(per_hour, lp, edge) if len(per_hour) > 1 else None
            steady = k is not None and k == len(per_hour)
            iid = tv.insert("", "end", values=(" → ".join(names), f"+{lp['edge'] * 100:.1f} %", _n(lp["depth"]),
                                               f"{k} of {len(per_hour)} h" if k is not None else "1 h"),
                            tags=[t for t in (("odd" if i % 2 else ""), ("steady" if steady else "")) if t])
            self.arb_rows[iid] = lp
        if A.CX.error:
            txt, fg = A.CX.error, C["red"]
        elif not hours:
            txt, fg = ("No history read yet - press Refresh (it reads the finished hours from Grinding Gear Games' "
                       "Currency Exchange history; nothing runs on its own)."), C["muted"]
        else:
            import time as _t
            last = max(hours)
            txt = (f"{len(tot)} markets traded in {league}, {len(hours)} finished hour{'s' if len(hours) != 1 else ''} "
                   f"(up to {_t.strftime('%H:%M', _t.localtime(last + 3600))}). {len(loops)} uneven loop"
                   f"{'s' if len(loops) != 1 else ''} at these settings. Highlighted rows were uneven in every one of those hours."
                   + (f" {len(wild)} more claimed over {self.MAX_EDGE * 100:.0f} % - left out: that's thin, one-sided "
                      f"trading in the hourly numbers, not a real gap." if wild else "")
                   + ("" if loops else " None right now is normal: the exchange is usually even. Try a lower gain "
                                       "(1 %) or a smaller amount traded (0)."))
            fg = C["muted"]
        self.arb_status.config(text=txt, fg=fg, wraplength=640)
        self.arb_steps.config(text="Pick a row to see the three trades." if loops else "")

    def arb_show_steps(self):
        sel = self.arb_tv.selection()
        lp = self.arb_rows.get(sel[0]) if sel else None
        if not lp:
            return
        lines, amt = [], 1.0
        for i, (a, b, r) in enumerate(lp["steps"]):
            got = amt * r
            lines.append(f"{i + 1}. {_n(amt)} {self.arb_name(a)}  →  {_n(got)} {self.arb_name(b)}"
                         f"   (1 {self.arb_name(a)} ≈ {_n(r)} {self.arb_name(b)}; post {self._ratio_txt(r)})")
            amt = got
        lines.append(f"Start with 1 {self.arb_name(lp['start'])}, end with {_n(amt)}: +{lp['edge'] * 100:.1f} % before "
                     "gold costs. Check each ratio in game first (hover it, hold Alt) - these are past averages.")
        self.arb_steps.config(text="\n".join(lines))

    @staticmethod
    def _ratio_txt(r):
        a, b = whole_ratio(r)
        return f"{a} : {b}"

    # ---- a flip you type in
    def flip_draw(self):
        def num(v):
            try:
                return float(v.get().replace(",", ".").strip())
            except ValueError:
                return None
        buy, sell, qty = num(self.flip_buy), num(self.flip_sell), num(self.flip_qty) or 1
        item, cur = self.flip_item.get().strip() or "the item", self.flip_cur.get().strip() or "currency"
        gain, margin = A.flip(buy, sell)
        if gain is None:
            self.flip_out.config(text="Type what one costs to buy, and what one sells for.", fg=C["muted"])
            return
        if gain <= 0:
            self.flip_out.config(text=f"No gain: buying costs {_n(buy)} and selling brings {_n(sell)} {cur}. Flipping "
                                      f"only works when people pay more than others ask.", fg=C["red"])
            return
        ba, bb = whole_ratio(1 / buy)
        sa, sb = whole_ratio(sell)
        self.flip_out.config(fg=C["green"], text=(
            f"+{_n(gain)} {cur} per {item} ({margin * 100:.1f} %).  × {_amt(qty)} = +{_n(gain * qty)} {cur}, "
            f"before gold costs.\n"
            f"To buy, post {ba} : {bb} ({cur} : {item});  to sell, post {sa} : {sb} ({item} : {cur})."))


