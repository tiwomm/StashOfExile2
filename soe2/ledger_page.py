"""Money Makers > Farm Ledger (2.45.0, was Run tracker): the window, the setup editor, the log box (in the app and
over the game) and the run counting. Data and every calculation live in ledger.py.

The Session timer times your play; the Farm Ledger measures one farming SETUP - what a run costs, what its loot is
worth, and whether it beats your other setups. ToS: it only reads your copies (Ctrl+Alt+C, which you press) and
Client.txt, and shows a box; it never acts in the game."""
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import ledger as L
from . import moneymakers as MM
from .config import SETTINGS, save_json
from .pricefmt import fmt_short
from .style import C, MONO, SegBar, Tooltip


def _hms(secs):
    secs = int(max(0, secs or 0))
    h, rest = divmod(secs, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _d(x, sign=False):
    if not isinstance(x, (int, float)):
        return "-"
    return (f"{x:+.2f}" if sign else f"{x:.2f}") + "d"


def _num(text):
    t = str(text or "").strip().lower().replace(",", ".").rstrip("d").strip()
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return False


KPIS = (("runs", "Runs"), ("avg", "Avg run"), ("cost", "Cost/run"), ("loot", "Loot/run"),
        ("profit", "Profit/run"), ("ph", "Div/hour"), ("roi", "ROI"))
LOG_COLS = (("n", "#", 40, "e"), ("when", "When", 120, "w"), ("v", "Ver.", 44, "center"), ("runs", "Runs", 50, "e"),
            ("time", "Time", 70, "e"), ("cost", "Cost", 66, "e"), ("loot", "Loot", 70, "e"), ("profit", "Profit", 74, "e"),
            ("ppr", "Profit/run", 78, "e"), ("dph", "d/h", 60, "e"), ("note", "Note", 220, "w"))
LOOT_COLS = (("item", "Item", 260, "w"), ("qty", "Dropped", 80, "e"), ("total", "Worth", 90, "e"),
             ("share", "Share", 80, "e"), ("per", "Per run", 80, "e"))
EDITABLE = {"runs": "runs", "cost": "cost", "loot": "loot", "profit": "profit", "note": "note"}


class LedgerPage:
    """Mixed into App."""

    # ================================================================ data
    def fl_data(self):
        if getattr(self, "_fl", None) is None:
            self._fl = L.load()
        return self._fl

    def fl_save(self):
        L.save(self.fl_data())

    def fl_setup(self):
        d = self.fl_data()
        return L.setup(d, d.get("current")) or (d["setups"][0] if d["setups"] else None)

    # ================================================================ the page
    def build_ledger(self, page):
        P1, P2 = C["panel"], C["panel2"]
        self.fl_view_v = None                                   # None: the setup's current version; else one version
        strip = tk.Frame(page, bg=P1)
        strip.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(strip, text="Does this setup really make money?", bg=P1, fg=C["accent"],
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        why = tk.Label(strip, text="The Session timer times your play. The Farm Ledger measures one farming setup: "
                                   "what a run costs, what its loot is worth, and how it compares.", bg=P1,
                       fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left")
        why.pack(side="left", padx=8, fill="x", expand=True)
        why.bind("<Configure>", lambda e: why.config(wraplength=max(200, e.width - 8)))
        body = tk.Frame(page, bg=P1)
        body.pack(fill="both", expand=True)
        # ---- left: your setups
        left = tk.Frame(body, bg=P2, padx=8, pady=8, highlightthickness=1, highlightbackground=C["line"])
        left.pack(side="left", fill="y", padx=(8, 0), pady=(0, 8))
        lh = tk.Frame(left, bg=P2)
        lh.pack(fill="x")
        tk.Label(lh, text="YOUR SETUPS", bg=P2, fg=C["muted"], font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(lh, text="＋ New", command=self.fl_new, style="Quiet.TButton").pack(side="right")
        self.fl_list = ttk.Treeview(left, columns=("name", "runs", "ph"), show="headings", height=12,
                                    selectmode="extended")
        for cid, title, w, a in (("name", "Setup", 150, "w"), ("runs", "Runs", 50, "e"), ("ph", "d/h", 54, "e")):
            self.fl_list.heading(cid, text=title)
            self.fl_list.column(cid, width=w, anchor=a, stretch=cid == "name")
        self.fl_list.pack(fill="y", expand=True, pady=(8, 8))
        self.fl_list.bind("<<TreeviewSelect>>", lambda e: self.fl_pick())
        self.fl_list.bind("<Button-3>", self.fl_list_menu)
        ttk.Button(left, text="Compare selected", command=self.fl_compare).pack(fill="x")
        tk.Label(left, text="Ctrl+click to pick several.\nA changed tablet or atlas makes\na new version: old numbers\n"
                            "stay with the old one.", bg=P2, fg=C["muted"], font=("Segoe UI", 9), justify="left",
                 anchor="w").pack(fill="x", pady=(8, 0))
        # ---- right: the setup
        main = tk.Frame(body, bg=P1)
        main.pack(side="left", fill="both", expand=True, padx=8, pady=(0, 8))
        head = tk.Frame(main, bg=P1)
        head.pack(fill="x")
        names = tk.Frame(head, bg=P1)
        names.pack(side="left")
        self.fl_title = tk.Label(names, text="", bg=P1, fg="#ffffff", font=("Segoe UI", 16, "bold"), anchor="w")
        self.fl_title.pack(anchor="w")
        self.fl_sub = tk.Label(names, text="", bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left")
        self.fl_sub.pack(anchor="w")
        btns = tk.Frame(main, bg=P1)                            # (its own row: never cut off in a narrow window)
        btns.pack(fill="x", pady=(8, 0))
        self.fl_ver_var = tk.StringVar()
        self.fl_ver_box = ttk.Combobox(btns, textvariable=self.fl_ver_var, state="readonly", width=16)
        self.fl_ver_box.pack(side="left", padx=(0, 8))
        self.fl_ver_box.bind("<<ComboboxSelected>>", lambda e: (self.fl_ver_picked(),
                                                               self.root.after(20, self.root.focus_set)))
        Tooltip(self.fl_ver_box, "Show one version's numbers, or all of them")
        ttk.Button(btns, text="Edit setup", command=self.fl_edit).pack(side="left", padx=(0, 8))
        self.fl_export_btn = ttk.Button(btns, text="Export ▾", command=self.fl_export_menu)
        self.fl_export_btn.pack(side="left", padx=(0, 8))
        self.fl_count_btn = ttk.Button(btns, text="▶ Start counting", command=self.fl_count_toggle)
        self.fl_count_btn.pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="✎ Log loot", style="Primary.TButton", command=self.fl_log_now).pack(side="right")
        # ---- the figures
        kp = tk.Frame(main, bg=P1)
        kp.pack(fill="x", pady=(8, 8))
        self.fl_kpi = {}
        for i, (k, label) in enumerate(KPIS):
            f = tk.Frame(kp, bg=P2, padx=8, pady=4, highlightthickness=1,
                         highlightbackground=C["accent"] if k == "ph" else C["line"])
            f.grid(row=0, column=i, sticky="nsew", padx=(0, 8))
            tk.Label(f, text=label.upper(), bg=P2, fg=C["accent"] if k == "ph" else C["muted"],
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            v = tk.Label(f, text="-", bg=P2, fg=C["text"], font=(MONO, 12, "bold"), anchor="w")
            v.pack(anchor="w")
            s = tk.Label(f, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w")
            s.pack(anchor="w")
            self.fl_kpi[k] = (v, s)
            kp.columnconfigure(i, weight=1, uniform="k")
        # ---- the chart: profit per log (bars), in total (line)
        self.fl_chart = tk.Canvas(main, height=96, bg=C["panel"], highlightthickness=1,
                                  highlightbackground=C["line"])
        self.fl_chart.pack(fill="x")
        self.fl_chart.bind("<Configure>", lambda e: self.fl_draw_chart())
        # ---- the sheet
        bar = tk.Frame(main, bg=P1)
        bar.pack(fill="x", pady=(8, 4))
        self.fl_sheet = SegBar(bar, ["Logs", "Loot"], command=lambda v: self.fl_fill_sheet(), size=9, pad=(12, 4))
        self.fl_sheet.pack(side="left")
        tk.Label(bar, text="Filter", bg=P1, fg=C["muted"]).pack(side="left", padx=(16, 4))
        self.fl_filter = tk.StringVar()
        fe = ttk.Entry(bar, textvariable=self.fl_filter, width=24)
        fe.pack(side="left")
        self.fl_filter.trace_add("write", lambda *a: self.fl_fill_sheet())
        Tooltip(fe, "Words in the note or the loot, or >1 / <0 for the profit per run")
        tk.Label(bar, text="Double-click a cell to change it · Ctrl+C copies rows", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9)).pack(side="right")
        box = tk.Frame(main, bg=P1)
        box.pack(fill="both", expand=True)
        self.fl_tree = ttk.Treeview(box, show="headings", selectmode="extended")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.fl_tree.yview)
        self.fl_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.fl_tree.pack(side="left", fill="both", expand=True)
        self.fl_tree.tag_configure("sum", foreground=C["accent"])
        self.fl_tree.tag_configure("bad", foreground=C["red"])
        self.fl_tree.tag_configure("skip", foreground=C["muted"])
        self.fl_tree.bind("<Double-1>", self.fl_cell_edit)
        self.fl_tree.bind("<Delete>", lambda e: self.fl_delete_logs())
        self.fl_tree.bind("<Control-c>", lambda e: self.fl_copy_rows())
        self.fl_tree.bind("<Button-3>", self.fl_log_menu)
        self.fl_sort = ("when", True)
        self.fl_status = tk.Label(main, text="", bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w")
        self.fl_status.pack(fill="x", pady=(4, 0))
        self.fl_refresh()

    # ================================================================ filling it
    def fl_refresh(self):
        if not hasattr(self, "fl_list"):
            return
        d = self.fl_data()
        tv = self.fl_list
        sel = set(tv.selection())
        tv.delete(*tv.get_children())
        for s in d["setups"]:
            f = L.figures(L.logs_of(d, s["id"]))
            ph = f["per_hour"]
            tv.insert("", "end", iid=s["id"], values=(s["name"] + (" ●" if (d.get("pending") or {}).get("setup") == s["id"] else ""),
                                                      f["runs"], "-" if ph is None else f"{ph:.1f}"))
        cur = self.fl_setup()
        keep = [i for i in sel if tv.exists(i)]
        if cur and not (len(keep) > 1 and cur["id"] in keep):       # (several picked for Compare: keep them)
            keep = [cur["id"]]
        self._fl_selecting = True
        tv.selection_set(keep)
        self.root.after_idle(lambda: setattr(self, "_fl_selecting", False))
        self.fl_fill_setup()

    def fl_pick(self):
        sel = self.fl_list.selection()
        if not sel or getattr(self, "_fl_selecting", False):
            return
        d = self.fl_data()
        if d.get("current") != sel[0]:
            d["current"] = sel[0]
            self.fl_view_v = None
            self.fl_save()
            self.fl_fill_setup()

    def fl_logs_shown(self):
        s = self.fl_setup()
        if not s:
            return []
        return L.logs_of(self.fl_data(), s["id"], self.fl_view_v)

    def fl_fill_setup(self):
        s = self.fl_setup()
        d = self.fl_data()
        if not s:
            self.fl_title.config(text="No setup yet")
            self.fl_sub.config(text="Press ＋ New: name it, pick its strat, Ctrl+Alt+C your waystone and tablets.")
            for v, sub in self.fl_kpi.values():
                v.config(text="-")
                sub.config(text="")
            self.fl_fill_sheet()
            self.fl_draw_chart()
            self.fl_paint_status()
            return
        ver = L.version(s)
        strat = next((x for x in MM.all_strats() if x["id"] == s.get("strat")), None)
        self.fl_title.config(text=f"{s['name']}   v{ver['v']}")
        cost, _parts, unknown = L.cost_per_run(ver)
        chips = []
        if ver["waystones"]:
            w = ver["waystones"][0]
            chips.append(f"Waystone {('T' + str(w['tier'])) if w.get('tier') else w['name']}"
                         + (f" · {len(w['mods'])} mods" if w.get("mods") else ""))
        if ver["tablets"]:
            chips.append(" · ".join(f"{t.get('count', 1)}× {t['base'] or t['name']}" for t in ver["tablets"]))
        if ver["atlas"]["trees"]:
            chips.append("Atlas: " + " · ".join(f"{t['name']} {t.get('points', 0)}" for t in ver["atlas"]["trees"]))
        line = (f"Strat: {strat['name']}" if strat else "Your own setup (no strat)") + \
            f"   ·   cost a run {_d(cost)}" + (f" ({unknown} without a price)" if unknown else "")
        self.fl_sub.config(text=line + ("\n" + "    ".join(chips) if chips else "\nEdit setup: add your waystone and tablets"))
        vers = ["All versions"] + [f"v{x['v']}" + (" (now)" if x["v"] == ver["v"] else "") for x in s["versions"]]
        self.fl_ver_box.config(values=vers)
        self.fl_ver_var.set(vers[0] if self.fl_view_v is None else
                            next((x for x in vers if x.startswith(f"v{self.fl_view_v}")), vers[0]))
        f = L.figures(self.fl_logs_shown())
        k = self.fl_kpi
        k["runs"][0].config(text=str(f["runs"]))
        k["runs"][1].config(text=f"{f['logs']} logs")
        k["avg"][0].config(text=_hms(f["avg_run"]) if f["avg_run"] else "-")
        k["avg"][1].config(text=f"fastest {_hms(f['fastest'])}" if f["fastest"] else "")
        k["cost"][0].config(text=_d(f["cost_run"]) if f["cost_run"] is not None else _d(cost))
        k["cost"][1].config(text="logged" if f["cost_run"] is not None else "from the setup")
        k["loot"][0].config(text=_d(f["loot_run"]))
        k["loot"][1].config(text=f"median {_d(f['loot_run_median'])}" if f["loot_run_median"] is not None else "")
        pr = f["profit_run"]
        k["profit"][0].config(text=_d(pr, True), fg=C["green"] if (pr or 0) > 0 else C["red"] if (pr or 0) < 0 else C["text"])
        k["profit"][1].config(text=f"±{f['spread']:.2f} spread" if f["spread"] is not None else "")
        ph = f["per_hour"]
        k["ph"][0].config(text="-" if ph is None else f"{ph:.1f}", fg=C["good"] if (ph or 0) >= 0 else C["red"])
        best = self.fl_best_other(s, ph)
        k["ph"][1].config(text=best)
        k["roi"][0].config(text="-" if f["roi"] is None else f"{f['roi'] * 100:.0f}%")
        k["roi"][1].config(text="loot ÷ cost")
        self.fl_fill_sheet()
        self.fl_draw_chart()
        self.fl_paint_status()

    def fl_best_other(self, s, ph):
        """vs this setup's version before, or your best other setup."""
        if ph is None:
            return ""
        d = self.fl_data()
        if len(s["versions"]) > 1 and self.fl_view_v is None:
            prev = s["versions"][-2]["v"]
            fp = L.figures(L.logs_of(d, s["id"], prev))["per_hour"]
            if fp is not None:
                return f"{'▲' if ph >= fp else '▼'} {abs(ph - fp):.1f} vs v{prev}"
        return ""

    def fl_rows(self):
        logs = sorted(self.fl_logs_shown(), key=lambda l: l["start"])
        rows = []
        for n, l in enumerate(logs, 1):
            secs = max(0.0, l["end"] - l["start"])
            money = not l.get("skipped") and isinstance(l.get("profit"), (int, float))
            ppr = l["profit"] / l["runs"] if money and l["runs"] else None
            rows.append({"log": l, "n": n, "when": time.strftime("%b %d %H:%M", time.localtime(l["start"])),
                         "v": f"v{l['v']}", "runs": l["runs"], "time": _hms(secs),
                         "cost": f"{l['cost']:.2f}", "loot": "-" if l.get("loot") is None else f"{l['loot']:.2f}",
                         "profit": "skipped" if l.get("skipped") else "-" if l.get("profit") is None else f"{l['profit']:+.2f}",
                         "ppr": "-" if ppr is None else f"{ppr:+.2f}",
                                      "dph": "-" if not money or secs < 60 else f"{l['profit'] * 3600 / secs:.1f}",
                         "note": (l.get("note") or "") + (("  ·  " + ", ".join(f"{r['qty']}× {r['name']}" for r in l["items"][:3])
                                                            + (" …" if len(l["items"]) > 3 else "")) if l.get("items") else ""),
                         "_ppr": ppr, "_start": l["start"]})
        flt = self.fl_filter.get().strip().lower() if hasattr(self, "fl_filter") else ""
        if flt:
            num = _num(flt[1:]) if flt[:1] in "<>" else None
            if num not in (None, False):
                rows = [r for r in rows if r["_ppr"] is not None and (r["_ppr"] > num if flt[0] == ">" else r["_ppr"] < num)]
            else:
                rows = [r for r in rows if flt in r["note"].lower()]
        return rows

    def fl_fill_sheet(self):
        if not hasattr(self, "fl_tree"):
            return
        tv = self.fl_tree
        tv.delete(*tv.get_children())
        loot_view = self.fl_sheet.get() == "Loot"
        cols = LOOT_COLS if loot_view else LOG_COLS
        tv.configure(columns=[c[0] for c in cols])
        for cid, title, w, a in cols:
            arrow = (" ▼" if self.fl_sort[1] else " ▲") if self.fl_sort[0] == cid else ""
            tv.heading(cid, text=title + arrow, command=lambda c=cid: self.fl_sort_by(c))
            tv.column(cid, width=w, anchor=a, stretch=cid in ("note", "item"))
        if loot_view:
            logs = self.fl_logs_shown()
            runs = sum(l["runs"] for l in logs if l.get("items")) or 1
            for g in L.loot_table(logs):
                tv.insert("", "end", values=(g["name"], g["qty"], f"{g['total']:.2f}", f"{g['share'] * 100:.0f}%",
                                             f"{g['total'] / runs:.3f}"))
            return
        rows = self.fl_rows()
        key, desc = self.fl_sort
        sk = {"when": "_start", "ppr": "_ppr"}.get(key, key)

        def sort_key(r):
            v = r.get(sk)
            if isinstance(v, str):
                n = _num(v.replace("+", ""))
                return (0, n) if isinstance(n, float) else (1, v.lower())
            return (0, v if v is not None else float("-inf"))
        rows.sort(key=sort_key, reverse=desc)
        for r in rows:
            l = r["log"]
            tag = "skip" if l.get("skipped") else "bad" if (r["_ppr"] or 0) < 0 else ""
            tv.insert("", "end", iid=l["id"], values=tuple(r[c[0]] for c in LOG_COLS), tags=(tag,) if tag else ())
        if rows:
            logs = [r["log"] for r in rows]
            f = L.figures(logs)
            tv.insert("", "end", iid="__sum", tags=("sum",), values=(
                "Σ", f"{len(rows)} logs", "", f["runs"], _hms(f["secs"]), f"{f['cost']:.2f}", f"{f['loot']:.2f}",
                f"{f['profit']:+.2f}", "-" if f["profit_run"] is None else f"{f['profit_run']:+.2f}",
                "-" if f["per_hour"] is None else f"{f['per_hour']:.1f}", ""))

    def fl_sort_by(self, col):
        self.fl_sort = (col, not self.fl_sort[1] if self.fl_sort[0] == col else True)
        self.fl_fill_sheet()

    def fl_draw_chart(self):
        cv = getattr(self, "fl_chart", None)
        if cv is None:
            return
        cv.delete("all")
        w, h = max(200, cv.winfo_width()), max(60, cv.winfo_height())
        logs = [l for l in sorted(self.fl_logs_shown(), key=lambda l: l["start"])
                if not l.get("skipped") and isinstance(l.get("profit"), (int, float))]
        cv.create_text(8, 8, text="Profit per log (bars) and in total (line), divines", anchor="nw", fill=C["muted"],
                       font=("Segoe UI", 9))
        if not logs:
            cv.create_text(w // 2, h // 2 + 6, text="Log your first loot to see the chart", fill=C["muted"],
                           font=("Segoe UI", 9))
            return
        top, bottom, left, right = 26, h - 8, 12, w - 110
        vals = [l["profit"] for l in logs]
        run, cum = 0.0, []
        for v in vals:
            run += v
            cum.append(run)
        lo, hi = min(0.0, min(vals), min(cum)), max(0.0, max(vals), max(cum))
        span = (hi - lo) or 1.0

        def y(v):
            return bottom - (v - lo) / span * (bottom - top)
        n = len(vals)
        step = (right - left) / max(1, n)
        bw = max(3, min(34, step * 0.6))
        cv.create_line(left, y(0), right, y(0), fill=C["line"])
        pts = []
        for i, v in enumerate(vals):
            x = left + step * i + step / 2
            cv.create_rectangle(x - bw / 2, min(y(0), y(v)), x + bw / 2, max(y(0), y(v)),
                                fill=C["gold_dim"] if v >= 0 else C["red"], width=0)
            pts += [x, y(cum[i])]
        if len(pts) >= 4:
            cv.create_line(*pts, fill=C["good"], width=2)
        cv.create_text(w - 8, h // 2 - 8, text=f"total {cum[-1]:+.1f}d", anchor="e", fill=C["good"],
                       font=(MONO, 10, "bold"))
        bad = sum(1 for v in vals if v < 0)
        cv.create_text(w - 8, h // 2 + 10, text=f"{bad} losing log{'s' if bad != 1 else ''}" if bad else "no losing logs",
                       anchor="e", fill=C["muted"], font=("Segoe UI", 9))

    def fl_paint_status(self):
        d, s = self.fl_data(), self.fl_setup()
        p = d.get("pending")
        if p and s and p.get("setup") == s["id"]:
            how = "Counting maps from Client.txt" if s.get("counting", "auto") == "auto" else \
                f"Press {self.fl_key_label()} after each run"
            txt = f"● {how}  ·  this log: {p.get('runs', 0)} of {s.get('every', L.EVERY)} runs  ·  " \
                  f"the loot box opens when you're back in your hideout after the last one"
            self.fl_count_btn.config(text="■ Stop counting")
        elif p:
            other = L.setup(d, p.get("setup"))
            txt = f"Counting runs for {other['name'] if other else 'another setup'} - pick it to see it."
            self.fl_count_btn.config(text="▶ Count this one")
        else:
            txt = "Not counting. ▶ Start counting when you start farming with this setup (the box asks for the loot " \
                  f"every {s.get('every', L.EVERY) if s else L.EVERY} runs)."
            self.fl_count_btn.config(text="▶ Start counting")
        self.fl_status.config(text=txt)

    # ================================================================ setups
    def fl_new(self):
        d = self.fl_data()
        n = len(d["setups"]) + 1
        s = L.new_setup(f"Setup {n}")
        d["setups"].append(s)
        d["current"] = s["id"]
        self.fl_save()
        self.fl_refresh()
        self.fl_edit(new=True)
        return s

    def fl_for_strat(self, sid):
        """Money Makers' "Track this": that strat's setup (made if there's none)."""
        d = self.fl_data()
        s = next((x for x in d["setups"] if x.get("strat") == sid), None)
        if not s:
            strat = next((x for x in MM.all_strats() if x["id"] == sid), None)
            s = L.new_setup(strat["name"] if strat else "New setup", strat=sid)
            d["setups"].append(s)
        d["current"] = s["id"]
        self.fl_view_v = None
        self.fl_save()
        self.fl_refresh()
        return s

    def fl_list_menu(self, e):
        iid = self.fl_list.identify_row(e.y)
        if not iid:
            return
        self.fl_list.selection_set(iid)
        self.fl_pick()
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84",
                    activeforeground="#ffffff")
        m.add_command(label="Edit setup…", command=self.fl_edit)
        m.add_command(label="Rename…", command=self.fl_rename)
        m.add_command(label="Duplicate", command=self.fl_duplicate)
        m.add_separator()
        m.add_command(label="Delete setup and its logs", command=self.fl_delete_setup)
        m.tk_popup(e.x_root, e.y_root)

    def fl_rename(self):
        from tkinter import simpledialog
        s = self.fl_setup()
        if not s:
            return
        name = simpledialog.askstring("Rename setup", "Name:", initialvalue=s["name"], parent=self.dlg_parent())
        if name and name.strip():
            s["name"] = name.strip()[:60]
            self.fl_save()
            self.fl_refresh()

    def fl_duplicate(self):
        import json as _json
        s = self.fl_setup()
        if not s:
            return
        c = _json.loads(_json.dumps(s))
        c.update(id=L._id(), name=s["name"] + " (copy)", created=time.time())
        c["versions"] = [dict(L.version(c), v=1)]
        c["cur_v"] = 1
        d = self.fl_data()
        d["setups"].append(c)
        d["current"] = c["id"]
        self.fl_save()
        self.fl_refresh()

    def fl_delete_setup(self):
        d, s = self.fl_data(), self.fl_setup()
        if not s:
            return
        n = len(L.logs_of(d, s["id"]))
        if not messagebox.askyesno("Delete setup", f"Delete {s['name']} and its {n} log(s)?", parent=self.dlg_parent()):
            return
        d["setups"] = [x for x in d["setups"] if x["id"] != s["id"]]
        d["logs"] = [l for l in d["logs"] if l["setup"] != s["id"]]
        if (d.get("pending") or {}).get("setup") == s["id"]:
            d["pending"] = None
        d["current"] = d["setups"][0]["id"] if d["setups"] else None
        self.fl_save()
        self.fl_refresh()

    def fl_ver_picked(self):
        t = self.fl_ver_var.get()
        self.fl_view_v = None if t.startswith("All") else int(t[1:].split()[0])
        self.fl_fill_setup()

    # ================================================================ the sheet: edit, delete, copy
    def fl_log(self, lid):
        return next((l for l in self.fl_data()["logs"] if l["id"] == lid), None)

    def fl_cell_edit(self, e):
        tv = self.fl_tree
        if self.fl_sheet.get() != "Logs":
            return
        iid, col = tv.identify_row(e.y), tv.identify_column(e.x)
        if not iid or iid == "__sum" or not col:
            return
        key = LOG_COLS[int(col[1:]) - 1][0]
        if key not in EDITABLE:
            return
        l = self.fl_log(iid)
        x, y, w, h = tv.bbox(iid, col)
        cur = {"runs": l["runs"], "cost": l["cost"], "loot": l.get("loot") if l.get("loot") is not None else "",
               "profit": l.get("profit") if l.get("profit") is not None else "", "note": l.get("note") or ""}[key]
        v = tk.StringVar(value=str(cur))
        ent = ttk.Entry(tv, textvariable=v)
        ent.place(x=x, y=y, width=max(w, 80 if key != "note" else 240), height=h)
        ent.focus_set()
        ent.select_range(0, "end")

        def done(save=True):
            if save:
                self.fl_set_cell(l, key, v.get())
            ent.destroy()
        ent.bind("<Return>", lambda ev: done())
        ent.bind("<KP_Enter>", lambda ev: done())
        ent.bind("<Escape>", lambda ev: done(False))
        ent.bind("<FocusOut>", lambda ev: done())
        self.fl_editing = ent

    def fl_set_cell(self, l, key, text):
        """One edited cell -> the log (profit and loot follow each other: profit = loot - cost)."""
        if key == "note":
            l["note"] = text.strip()[:200]
        else:
            n = _num(text)
            if n is False or (n is None and key in ("runs", "cost")):
                self._say("A number, please (divines: 2.5).", 5)
                return
            if key == "runs":
                l["runs"] = max(1, int(n))
            elif key == "cost":
                l["cost"] = n
                if l.get("loot") is not None:
                    l["profit"] = round(l["loot"] - n, 4)
            elif key == "loot":
                l["loot"] = n
                l["profit"] = None if n is None else round(n - l["cost"], 4)
                l["skipped"] = n is None
            elif key == "profit":
                l["profit"] = n
                l["loot"] = None if n is None else round(n + l["cost"], 4)
                l["skipped"] = n is None
        self.fl_save()
        self.fl_refresh()

    def fl_delete_logs(self):
        ids = [i for i in self.fl_tree.selection() if i != "__sum"]
        if not ids or self.fl_sheet.get() != "Logs":
            return
        if not messagebox.askyesno("Delete logs", f"Delete {len(ids)} log(s)?", parent=self.dlg_parent()):
            return
        d = self.fl_data()
        d["logs"] = [l for l in d["logs"] if l["id"] not in ids]
        self.fl_save()
        self.fl_refresh()

    def fl_copy_rows(self):
        tv = self.fl_tree
        ids = tv.selection() or tv.get_children()
        cols = [tv.heading(c)["text"].rstrip(" ▲▼") for c in tv["columns"]]
        lines = ["\t".join(cols)] + ["\t".join(str(x) for x in tv.item(i, "values")) for i in ids]
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        self.own_clip = "\n".join(lines)
        self._say(f"Copied {len(ids)} row(s) - paste into a spreadsheet.", 4)

    def fl_log_menu(self, e):
        iid = self.fl_tree.identify_row(e.y)
        if not iid or iid == "__sum" or self.fl_sheet.get() != "Logs":
            return
        if iid not in self.fl_tree.selection():
            self.fl_tree.selection_set(iid)
        l = self.fl_log(iid)
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84",
                    activeforeground="#ffffff")
        m.add_command(label="See its loot…", command=lambda: self.fl_show_loot(l))
        m.add_command(label="Copy rows", command=self.fl_copy_rows)
        m.add_separator()
        m.add_command(label="Delete", command=self.fl_delete_logs)
        m.tk_popup(e.x_root, e.y_root)

    def fl_show_loot(self, l):
        lines = [f"{r['qty']}× {r['name']}  -  " + ("no price" if r.get("total") is None else
                                                    f"{r['total']:.2f}d ({r['each']:.3f} each)")
                 for r in l.get("items") or []] or ["No loot was copied for this log (only its total)."]
        messagebox.showinfo("Loot of this log", "\n".join(lines), parent=self.dlg_parent())

    # ================================================================ export / import
    def fl_export_menu(self):
        b = self.fl_export_btn
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84",
                    activeforeground="#ffffff")
        m.add_command(label="CSV - logs (Excel, Google Sheets)", command=lambda: self.fl_export("logs"))
        m.add_command(label="CSV - every drop", command=lambda: self.fl_export("loot"))
        m.add_command(label="CSV - logs of every setup", command=lambda: self.fl_export("all"))
        m.add_command(label="Setup file (.json) - for a friend's Farm Ledger", command=lambda: self.fl_export("json"))
        m.add_command(label="Strat guide (CSV) - share this setup as a strat", command=lambda: self.fl_export("strat"))
        m.add_command(label="Copy summary (for Discord)", command=self.fl_copy_summary)
        m.add_separator()
        m.add_command(label="Import a setup file…", command=self.fl_import_json)
        m.add_command(label="Import logs from a CSV…", command=self.fl_import_csv)
        m.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())

    def fl_export(self, what, path=None):
        d, s = self.fl_data(), self.fl_setup()
        if not s and what != "all":
            return None
        name = (s["name"] if s else "farm-ledger").replace(" ", "_")
        ext = ".json" if what == "json" else ".csv"
        if what == "strat":                                        # 2.46.0: the standard strat guide, from this setup
            st = self.fl_strat_guide(s)
            if path is None:
                path = filedialog.asksaveasfilename(parent=self.dlg_parent(), defaultextension=".csv",
                                                    initialfile=f"{st['id'] or name}.csv",
                                                    filetypes=[("Strat guide (CSV)", "*.csv")])
            if not path:
                return None
            self.mm_write_strat(st, path)
            probs = MM.validate(st)
            if probs:
                self._say(f"Saved {path} - fill in the rest before sharing it ({probs[0]}).", 10)
            return path
        if path is None:
            path = filedialog.asksaveasfilename(parent=self.dlg_parent(), defaultextension=ext,
                                                initialfile=f"{name}_{what}{ext}",
                                                filetypes=[("JSON" if ext == ".json" else "CSV", "*" + ext)])
        if not path:
            return None
        text = (L.setup_json(d, s["id"]) if what == "json" else L.loot_csv(d, {s["id"]}) if what == "loot" else
                L.logs_csv(d, None if what == "all" else {s["id"]}))
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        self._say(f"Saved {path}", 6)
        return path

    def fl_strat_guide(self, s):
        """2.46.0: a setup -> a strat in the standard layout: its strat's text (if it has one), the items it runs
        (with the mods that matter - Money Makers checks their cost every day), the atlas, and its numbers."""
        import json as _json
        base = next((x for x in MM.all_strats() if x["id"] == s.get("strat")), None)
        st = {k: v for k, v in _json.loads(_json.dumps(base)).items() if not k.startswith("_") and k != "origin"} if base \
            else MM.new_strat(name=s["name"], summary="", steps=[], author=SETTINGS.get("wealth_account") or "me")
        ver = L.version(s)
        st["waystones"] = [f"{e.get('count', 1)}× {e['name']}" + (f" - ★ {', '.join(e['key_mods'])}" if e.get("key_mods") else "")
                           for e in ver["waystones"]] or st.get("waystones", [])
        st["tablets"] = [f"{e.get('count', 1)}× {e['name']} (lasts {e.get('lasts', 1)} runs)"
                         + (f" - ★ {', '.join(e['key_mods'])}" if e.get("key_mods") else "")
                         for e in ver["tablets"] + ver["others"]] or st.get("tablets", [])
        atlas = [f"{t['name']}: {t.get('points', 0)} points" for t in ver["atlas"]["trees"]]
        atlas += [l for l in (ver["atlas"].get("notes") or "").splitlines() if l.strip()]
        if atlas:
            st["atlas"] = atlas
        tiers = [e["tier"] for e in ver["waystones"] if e.get("tier")]
        if tiers:
            st["waystone_tiers"] = {"min": min(tiers), "max": max(tiers)}
        st["items"] = [{"kind": k[:-1], "base": e["base"], "name": e["name"], "count": e.get("count", 1),
                        "lasts": e.get("lasts", 1), "key_mods": e.get("key_mods") or []}
                       for k in ("waystones", "tablets", "others") for e in ver[k]]
        if not st["items"]:
            st.pop("items")
        f = L.figures(L.logs_of(self.fl_data(), s["id"], ver["v"]))
        if f["runs"]:
            lg = {"runs": f["runs"], "minutes": round(f["secs"] / 60, 1)}
            for k, v in (("cost_per_run_div", f["cost_run"]), ("loot_per_run_div", f["loot_run"]),
                         ("profit_per_run_div", f["profit_run"]), ("div_per_hour", f["per_hour"])):
                if v is not None:
                    lg[k] = round(v, 3)
            st["ledger"] = lg
            if f["per_hour"] is not None:
                st["est_profit"] = {"low": round(f["per_hour"], 1), "high": round(f["per_hour"], 1), "unit": "div"}
        cost = L.cost_per_run(ver)[0]
        if cost:
            st["est_cost"] = {"amount": round(cost, 3), "unit": "div"}
        st["updated"] = time.strftime("%Y-%m-%d")
        return st

    def fl_copy_summary(self):
        s = self.fl_setup()
        if not s:
            return
        t = L.summary(s, L.figures(L.logs_of(self.fl_data(), s["id"])))
        self.root.clipboard_clear()
        self.root.clipboard_append(t)
        self.own_clip = t
        self._say("Copied: " + t, 6)

    def fl_import_json(self, path=None):
        path = path or filedialog.askopenfilename(parent=self.dlg_parent(), filetypes=[("Setup file", "*.json")])
        if not path:
            return None
        try:
            with open(path, encoding="utf-8") as fh:
                s = L.import_setup_json(self.fl_data(), fh.read())
        except Exception as e:
            self._say(f"Couldn't read that setup file: {e}", 8)
            return None
        self.fl_data()["current"] = s["id"]
        self.fl_save()
        self.fl_refresh()
        return s

    def fl_import_csv(self, path=None):
        s = self.fl_setup()
        if not s:
            return 0
        path = path or filedialog.askopenfilename(parent=self.dlg_parent(), filetypes=[("CSV", "*.csv")])
        if not path:
            return 0
        with open(path, encoding="utf-8-sig") as fh:
            n = L.import_logs_csv(self.fl_data(), s["id"], L.version(s)["v"], fh.read())
        self.fl_save()
        self.fl_refresh()
        self._say(f"Added {n} log(s) to {s['name']}.", 6)
        return n

    # ================================================================ compare
    def fl_compare(self):
        d = self.fl_data()
        ids = [i for i in self.fl_list.selection()] or [s["id"] for s in d["setups"]]
        cols = []
        for sid in ids:
            s = L.setup(d, sid)
            if not s:
                continue
            if len(ids) == 1:                                     # one setup: its versions side by side
                for v in s["versions"]:
                    cols.append((f"{s['name']} v{v['v']}", L.figures(L.logs_of(d, sid, v["v"])), s, v))
            else:
                cols.append((s["name"], L.figures(L.logs_of(d, sid)), s, L.version(s)))
        if not cols:
            return None
        win = tk.Toplevel(self.root)
        win.title("Farm Ledger - compare")
        win.configure(bg=C["panel"])
        win.transient(self.root)
        rows = (("Runs", "runs", lambda f: str(f["runs"]), max),
                ("Avg run", "avg_run", lambda f: _hms(f["avg_run"]) if f["avg_run"] else "-", min),
                ("Cost / run", "cost_run", lambda f: _d(f["cost_run"]), min),
                ("Loot / run", "loot_run", lambda f: _d(f["loot_run"]), max),
                ("Profit / run", "profit_run", lambda f: _d(f["profit_run"], True), max),
                ("Div / hour", "per_hour", lambda f: "-" if f["per_hour"] is None else f"{f['per_hour']:.1f}", max),
                ("Spread", "spread", lambda f: "-" if f["spread"] is None else f"±{f['spread']:.2f}", min))
        g = tk.Frame(win, bg=C["panel"], padx=16, pady=16)
        g.pack(fill="both", expand=True)
        for j, (title, *_r) in enumerate(cols):
            tk.Label(g, text=title, bg=C["panel2"], fg="#ffffff", font=("Segoe UI", 10, "bold"), padx=8,
                     pady=4).grid(row=0, column=j + 1, sticky="nsew")
        for i, (label, key, fmt, best_fn) in enumerate(rows, 1):
            tk.Label(g, text=label, bg=C["panel"], fg=C["accent"] if key == "per_hour" else C["muted"],
                     font=("Segoe UI", 10, "bold" if key == "per_hour" else "normal"), padx=8, pady=4,
                     anchor="w").grid(row=i, column=0, sticky="w")
            vals = [c[1].get(key) for c in cols]
            known = [v for v in vals if isinstance(v, (int, float))]
            best = best_fn(known) if len(known) > 1 else None
            for j, c in enumerate(cols):
                star = best is not None and vals[j] == best
                tk.Label(g, text=fmt(c[1]) + (" ★" if star else ""), bg=C["panel"],
                         fg=C["green"] if star else C["text"], font=(MONO, 10, "bold" if star else "normal"),
                         padx=8, pady=4).grid(row=i, column=j + 1, sticky="e")
        tk.Label(g, text="What changed", bg=C["panel"], fg=C["muted"], padx=8, pady=4, anchor="w").grid(
            row=len(rows) + 1, column=0, sticky="w")
        for j, (_t, _f, s, v) in enumerate(cols):
            prev = next((x for x in s["versions"] if x["v"] == v["v"] - 1), None)
            tk.Label(g, text=L.what_changed(prev, v) if prev else "-", bg=C["panel"], fg=C["muted"],
                     font=("Segoe UI", 9), wraplength=180, justify="left", padx=8, pady=4).grid(
                row=len(rows) + 1, column=j + 1, sticky="w")
        few = [c[0] for c in cols if 0 < c[1]["runs"] < 20]
        if few:
            tk.Label(g, text="Few runs (under 20) - rough numbers: " + ", ".join(few), bg=C["panel"], fg=C["muted"],
                     font=("Segoe UI", 9)).grid(row=len(rows) + 2, column=0, columnspan=len(cols) + 1, sticky="w",
                                                pady=(8, 0))
        self.fl_compare_win = win
        return win

    # ================================================================ counting runs
    def fl_count_toggle(self):
        d, s = self.fl_data(), self.fl_setup()
        if not s:
            return
        p = d.get("pending")
        if p and p.get("setup") == s["id"]:
            if p.get("runs") and not messagebox.askyesno(
                    "Stop counting", f"{p['runs']} run(s) haven't been logged yet. Stop counting anyway?\n"
                                     "(✎ Log loot now logs them first.)", parent=self.dlg_parent()):
                return
            d["pending"] = None
        else:
            d["pending"] = {"setup": s["id"], "v": L.version(s)["v"], "start": time.time(), "runs": 0,
                            "map_secs": 0.0, "where": None, "entered": None, "asked": False}
            if s.get("counting", "auto") == "auto":
                try:
                    if getattr(self, "br_reader", None) is None:
                        self.breach_start()           # (follows Client.txt - log_wanted() now says yes)
                except Exception:
                    self.log_error("starting the Farm Ledger's map counting")
        self.fl_save()
        self.fl_refresh()

    def fl_counting(self):
        """Is Client.txt wanted for counting runs?"""
        d = self.fl_data()
        p = d.get("pending")
        s = L.setup(d, p.get("setup")) if p else None
        return bool(s and s.get("counting", "auto") == "auto")

    def fl_area(self, kind, where, before):
        """From the Client.txt follower (alerts_page.breach_area): a new map = one run; back in your hideout (or a
        town) after the Nth run = the loot box."""
        d = self.fl_data()
        p = d.get("pending")
        s = L.setup(d, p.get("setup")) if p else None
        if not s or s.get("counting", "auto") != "auto":
            return
        now = time.time()
        if kind == "map" and before != "map":
            if where is None or where != p.get("where"):           # (back through your portal: the same run)
                p["runs"] = p.get("runs", 0) + 1
                p["where"] = where
            p["entered"] = now
            self.fl_save()
        elif before == "map" and kind in ("hideout", "town"):
            if p.get("entered"):
                p["map_secs"] = p.get("map_secs", 0.0) + now - p["entered"]
                p["entered"] = None
            if self.fl_due(s, p):
                self.fl_prompt()
            self.fl_save()
        if hasattr(self, "fl_status"):
            self.fl_paint_status()

    @staticmethod
    def fl_due(s, p):
        """Time for the loot box: N runs done (Later: one more)."""
        return (p.get("runs", 0) >= s.get("every", L.EVERY) and not p.get("asked")
                and p.get("runs", 0) >= p.get("later_at", 0))

    def fl_key_label(self):
        from .overlay import key_label
        return key_label(SETTINGS.get("ledger_key") or "Ctrl+Alt+N")

    def fl_on_key(self, vk, ctrl, alt, shift):
        """(keyboard thread) The "a run is done" key, for setups counted by key."""
        from .overlay import game_active, parse_key
        k = parse_key(SETTINGS.get("ledger_key") or "Ctrl+Alt+N")
        if k and k == (vk, ctrl, alt, shift):
            self.ui_q.put(("ledger_key",))
            return bool(game_active())
        return False

    def ev_ledger_key(self):
        d = self.fl_data()
        p = d.get("pending")
        s = L.setup(d, p.get("setup")) if p else None
        if not s or s.get("counting", "auto") != "key":
            return
        p["runs"] = p.get("runs", 0) + 1
        self.fl_save()
        if self.fl_due(s, p):
            self.fl_prompt()
        if hasattr(self, "fl_status"):
            self.fl_paint_status()

    # ================================================================ the loot box (in the app and over the game)
    def fl_log_now(self):
        d, s = self.fl_data(), self.fl_setup()
        if not s:
            return self.fl_new()
        p = d.get("pending")
        if not p or p.get("setup") != s["id"]:
            p = {"setup": s["id"], "v": L.version(s)["v"], "start": time.time(), "runs": 0, "map_secs": 0.0,
                 "where": None, "entered": None, "manual": True}
        return self.fl_prompt(p, in_app=True)

    def fl_prompt(self, p=None, in_app=False):
        """The box: runs since the last log, the loot (Ctrl+Alt+C each drop, or paste), its worth from poe.ninja item
        by item, cost from the setup, profit. Parchment over the game, like the Session timer."""
        from .overlaywin import OverlayWindow, pal, parchment
        d = self.fl_data()
        p = p or d.get("pending")
        s = L.setup(d, p.get("setup")) if p else None
        if not s:
            return None
        if getattr(self, "fl_box", None) is not None:
            try:
                self.fl_box.destroy()
            except tk.TclError:
                pass
        if not p.get("manual"):
            p["asked"] = True
        P = pal()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        geo = SETTINGS.get("ledger_box") or (sw // 2 - 240, sh // 4, 480, 560)

        def moved(x, y, w, h):
            SETTINGS["ledger_box"] = (x, y, w, h)
            save_json("settings.json", SETTINGS)
        w = OverlayWindow(self.root, f"Farm Ledger · {s['name']}", "✎", geo, opacity=250, on_close=self.fl_box_later,
                          on_moved=moved, lockable=False, min_size=(380, 420), follow_game=not in_app)
        self.fl_box, self.fl_box_p = w, p
        bg, fg, mut = P["bg"], P["text"], P["muted"]
        font = (P["font"], 10)
        body = tk.Frame(w.body, bg=bg, padx=12, pady=8)
        body.pack(fill="both", expand=True)
        secs = time.time() - p.get("start", time.time())
        top = tk.Frame(body, bg=bg)
        top.pack(fill="x")
        tk.Label(top, text="Runs", bg=bg, fg=fg, font=(P["font"], 12, "bold")).pack(side="left")
        self.fl_box_runs = tk.StringVar(value=str(max(1, p.get("runs", 0)) if not p.get("manual") else max(1, p.get("runs", 0) or 1)))
        ttk.Spinbox(top, from_=1, to=999, textvariable=self.fl_box_runs, width=4,
                    command=self.fl_box_recalc).pack(side="left", padx=(8, 8))
        self.fl_box_runs.trace_add("write", lambda *a: self.fl_box_recalc())
        tk.Label(top, text=f"since your last log · {_hms(secs)}", bg=bg, fg=mut, font=font).pack(side="left")
        tk.Label(body, text="Loot - Ctrl+Alt+C each drop in game (or a stash full of them), paste, or type "
                            "\"7 Divine Orb\":", bg=bg, fg=mut, font=(P["font"], 9), anchor="w", justify="left",
                 wraplength=440).pack(fill="x", pady=(8, 2))
        self.fl_box_text = tk.Text(body, height=4, bg=P["field"], fg=fg, insertbackground=fg, relief="flat",
                                   highlightthickness=1, highlightbackground=P["line"], font=font, wrap="word")
        self.fl_box_text.pack(fill="x")
        self.fl_box_text.bind("<<Modified>>", self._fl_box_typed)
        self.fl_box_rows = tk.Frame(body, bg=bg)
        self.fl_box_rows.pack(fill="both", expand=True, pady=(8, 0))
        sums = tk.Frame(body, bg=bg)
        sums.pack(fill="x", pady=(8, 0))
        self.fl_box_vars = {}
        for i, (key, label) in enumerate((("loot", "Loot worth"), ("cost", "Cost"), ("profit", "Profit"))):
            tk.Label(sums, text=label, bg=bg, fg=fg, font=(P["font"], 10, "bold" if key == "profit" else "normal"),
                     anchor="w").grid(row=i, column=0, sticky="w", pady=1)
            v = tk.StringVar()
            self.fl_box_vars[key] = v
            e = ttk.Entry(sums, textvariable=v, width=10)
            e.grid(row=i, column=1, sticky="w", padx=(8, 8))
            if key == "cost":
                e.configure(state="readonly")
            note = tk.Label(sums, text="", bg=bg, fg=mut, font=(P["font"], 9), anchor="w")
            note.grid(row=i, column=2, sticky="w")
            self.fl_box_vars[key + "_note"] = note
        self.fl_box_vars["loot"].trace_add("write", lambda *a: self.fl_box_typed_total("loot"))
        self.fl_box_vars["profit"].trace_add("write", lambda *a: self.fl_box_typed_total("profit"))
        nrow = tk.Frame(body, bg=bg)
        nrow.pack(fill="x", pady=(8, 0))
        tk.Label(nrow, text="Note", bg=bg, fg=fg, font=font).pack(side="left")
        self.fl_box_note = tk.StringVar()
        ttk.Entry(nrow, textvariable=self.fl_box_note).pack(side="left", fill="x", expand=True, padx=(8, 0))
        brow = tk.Frame(body, bg=bg)
        brow.pack(fill="x", pady=(8, 0))
        ttk.Button(brow, text="Log it", style="Primary.TButton", command=self.fl_box_log).pack(side="right")
        ttk.Button(brow, text="Skip", command=self.fl_box_skip, style="Quiet.TButton").pack(side="right", padx=(0, 8))
        ttk.Button(brow, text="Later", command=self.fl_box_later, style="Quiet.TButton").pack(side="right", padx=(0, 8))
        for b_ in brow.winfo_children():
            t_ = b_.cget("text")
            Tooltip(b_, {"Later": "Ask again after your next run", "Skip": "These runs count for time, not money",
                         "Log it": "Save this log (Enter)"}.get(t_, t_))
        self.fl_box_items, self._fl_box_typing = [], None
        self._fl_box_set = False
        self.fl_box_recalc()
        w.show()
        return w

    def fl_capturing(self):
        """Ctrl+Alt+C copies go to the loot box while it's open (accept_clip)."""
        b = getattr(self, "fl_box", None)
        try:
            return b is not None and b.winfo_exists() and getattr(b, "wanted", True)
        except tk.TclError:
            return False

    def fl_take_clip(self, text):
        """A Ctrl+Alt+C in game -> one short line in the box ("7 Divine Orb"), not the whole item text."""
        t = self.fl_box_text
        drops = L.parse_drops(text)
        if not drops:
            return
        cur = t.get("1.0", "end-1c")
        t.insert("end", ("\n" if cur and not cur.endswith("\n") else "") + "\n".join(f"{q} {n}" for n, q in drops) + "\n")
        self._say("Added to the Farm Ledger's loot: " + ", ".join(f"{q}× {n}" for n, q in drops), 3)

    def _fl_box_typed(self, _e=None):
        t = self.fl_box_text
        if not t.edit_modified():
            return
        t.edit_modified(False)
        if self._fl_box_typing:
            self.root.after_cancel(self._fl_box_typing)
        self._fl_box_typing = self.root.after(350, self.fl_box_price)

    def fl_box_price(self):
        """Read the loot box and price each item with poe.ninja (Wealth's prices, fetched in the background)."""
        self._fl_box_typing = None
        try:
            drops = L.parse_drops(self.fl_box_text.get("1.0", "end-1c"))
        except tk.TclError:                                      # (the box was closed meanwhile)
            return
        league = SETTINGS.get("league", "")

        def work():
            names, value_of = self.fl_names(league)
            return L.price_drops(drops, names.match, value_of)

        def done(rows):
            if getattr(self, "fl_box", None) is None:
                return
            self.fl_box_items = rows
            self._fl_box_set = False
            self.fl_box_recalc()
        self._mm_bg(work, done)

    def fl_names(self, league):
        from .wealth import WPRICES
        cache = getattr(self, "_fl_names", None)
        if not cache or cache[0] != (league, getattr(WPRICES, "ts", 0)) or time.time() - cache[3] > 600:
            names, value_of = self.remnant_names_values(league)
            cache = self._fl_names = ((league, getattr(WPRICES, "ts", 0)), names, value_of, time.time())
        return cache[1], cache[2]

    def fl_box_cost(self):
        d, p = self.fl_data(), self.fl_box_p
        s = L.setup(d, p["setup"])
        per, _parts, unknown = L.cost_per_run(L.version(s, p.get("v")))
        try:
            runs = max(1, int(self.fl_box_runs.get()))
        except (ValueError, tk.TclError):
            runs = 1
        return per * runs, per, runs, unknown

    def fl_box_recalc(self):
        """The rows and the totals (unless you typed a total yourself)."""
        from .overlaywin import pal
        if getattr(self, "fl_box", None) is None:
            return
        P = pal()
        box = self.fl_box_rows
        for c in box.winfo_children():
            c.destroy()
        rows = self.fl_box_items
        for i, r in enumerate(rows[:12]):
            tk.Label(box, text=f"{r['qty']}×", bg=P["bg"], fg=P["muted"], font=(P["font"], 10), anchor="e",
                     width=4).grid(row=i, column=0, sticky="e")
            tk.Label(box, text=r["name"], bg=P["bg"], fg=P["text"], font=(P["font"], 10), anchor="w").grid(
                row=i, column=1, sticky="w", padx=(4, 8))
            tk.Label(box, text="no price" if r["total"] is None else fmt_short(r["total"]), bg=P["bg"],
                     fg=P["muted"] if r["total"] is None else P["text"], font=(P["font"], 10, "bold"),
                     anchor="e").grid(row=i, column=2, sticky="e")
        if len(rows) > 12:
            tk.Label(box, text=f"… and {len(rows) - 12} more", bg=P["bg"], fg=P["muted"], font=(P["font"], 9)).grid(
                row=13, column=1, sticky="w")
        box.columnconfigure(1, weight=1)
        cost, per, runs, unknown = self.fl_box_cost()
        self._fl_box_set = True
        self.fl_box_vars["cost"].set(f"{cost:.2f}")
        self.fl_box_vars["cost_note"].config(text=f"{runs} × {per:.2f} from your setup" +
                                                  (f" ({unknown} item(s) without a price)" if unknown else ""))
        if not getattr(self, "_fl_typed_total", None):
            loot = L.loot_total(rows)
            self.fl_box_vars["loot"].set(f"{loot:.2f}" if rows else "")
            self.fl_box_vars["profit"].set(f"{loot - cost:+.2f}" if rows else "")
        self.fl_box_vars["loot_note"].config(text=f"poe.ninja, {sum(1 for r in rows if r['total'] is not None)} of "
                                                  f"{len(rows)} priced" if rows else "or type it")
        self._fl_box_set = False
        self.fl_box_typed_total(None)

    def fl_box_typed_total(self, which):
        """You typed the loot's worth or the profit: the other follows (profit = loot - cost)."""
        if getattr(self, "_fl_box_set", False) or getattr(self, "fl_box", None) is None:
            return
        cost = self.fl_box_cost()[0]
        if which:
            self._fl_typed_total = which
        which = which or getattr(self, "_fl_typed_total", None)
        self._fl_box_set = True
        try:
            if which == "loot":
                n = _num(self.fl_box_vars["loot"].get())
                self.fl_box_vars["profit"].set("" if not isinstance(n, float) else f"{n - cost:+.2f}")
            elif which == "profit":
                n = _num(self.fl_box_vars["profit"].get().replace("+", ""))
                self.fl_box_vars["loot"].set("" if not isinstance(n, float) else f"{n + cost:.2f}")
            n = _num(self.fl_box_vars["profit"].get().replace("+", ""))
            secs = time.time() - self.fl_box_p.get("start", time.time())
            self.fl_box_vars["profit_note"].config(
                text=f"{n * 3600 / secs:.1f} div / hour" if isinstance(n, float) and secs > 60 else "")
        finally:
            self._fl_box_set = False

    def _fl_box_close(self):
        w, self.fl_box = getattr(self, "fl_box", None), None
        self._fl_typed_total = None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def fl_box_log(self, skip=False):
        d, p = self.fl_data(), self.fl_box_p
        cost, _per, runs, _u = self.fl_box_cost()
        loot = _num(self.fl_box_vars["loot"].get())
        profit = _num(self.fl_box_vars["profit"].get().replace("+", ""))
        if not skip and loot in (None, False) and profit in (None, False):
            self._say("Copy or type the loot, or type the profit - or Skip.", 6)
            return None
        now = time.time()
        log = L.new_log(p["setup"], p.get("v") or 1, p.get("start", now), now, runs, cost,
                        [] if skip else self.fl_box_items, self.fl_box_note.get().strip(),
                        map_secs=p.get("map_secs") or None,
                        loot=None if skip or loot in (None, False) else loot,
                        profit=None if skip or profit in (None, False) else profit)
        if skip:
            log.update(skipped=True, loot=None, profit=None)
        d["logs"].append(log)
        pend = d.get("pending")
        if pend is p or (pend and not p.get("manual") and pend.get("setup") == p["setup"]):
            s = L.setup(d, p["setup"])                            # the next log starts now, same setup and version
            d["pending"] = {"setup": p["setup"], "v": L.version(s)["v"], "start": now, "runs": 0, "map_secs": 0.0,
                            "where": pend.get("where"), "entered": None, "asked": False}
        self.fl_save()
        self._fl_box_close()
        self.fl_refresh()
        return log

    def fl_box_skip(self):
        return self.fl_box_log(skip=True)

    def fl_box_later(self):
        p = getattr(self, "fl_box_p", None)
        if p is not None and not p.get("manual"):
            p["asked"] = False                                   # ask again after the next run
            p["later_at"] = p.get("runs", 0) + 1
            self.fl_save()
        self._fl_box_close()

    # ================================================================ the setup editor
    def fl_edit(self, new=False):
        """Name, strat, waystone, tablets (and other items), atlas, logging. Items are priced by themselves (the price
        checker) - or type your own price."""
        import json as _json
        d, s = self.fl_data(), self.fl_setup()
        if not s:
            return self.fl_new()
        P1, P2 = C["panel"], C["panel2"]
        if getattr(self, "fl_ed", None) is not None:
            try:
                self.fl_ed.destroy()
            except tk.TclError:
                pass
        win = tk.Toplevel(self.root)
        win.title(f"Farm Ledger - {s['name']}")
        win.configure(bg=P1)
        win.transient(self.root)
        win.geometry("1060x640")
        self.fl_ed, self.fl_ed_s = win, s
        self.fl_ed_ver = _json.loads(_json.dumps(L.version(s)))           # edited as a copy; Save decides the version
        top = tk.Frame(win, bg=P2, padx=16, pady=8)
        top.pack(fill="x")
        tk.Label(top, text="Name", bg=P2, fg=C["muted"]).pack(side="left")
        self.fl_ed_name = tk.StringVar(value=s["name"])
        ttk.Entry(top, textvariable=self.fl_ed_name, width=28).pack(side="left", padx=(8, 16))
        tk.Label(top, text="Strat", bg=P2, fg=C["muted"]).pack(side="left")
        strats = sorted(MM.all_strats(), key=lambda x: x["name"].lower())
        self.fl_ed_strats = {"(none - my own idea)": None, **{x["name"]: x["id"] for x in strats}}
        cur = next((n for n, i in self.fl_ed_strats.items() if i == s.get("strat")), "(none - my own idea)")
        self.fl_ed_strat = tk.StringVar(value=cur)
        cb = ttk.Combobox(top, textvariable=self.fl_ed_strat, values=list(self.fl_ed_strats), state="readonly", width=34)
        cb.pack(side="left", padx=(8, 0))
        cb.bind("<<ComboboxSelected>>", lambda e: self.root.after(20, win.focus_set))
        ttk.Button(top, text="Save", style="Primary.TButton", command=self.fl_ed_save).pack(side="right")
        ttk.Button(top, text="Cancel", style="Quiet.TButton", command=win.destroy).pack(side="right", padx=(0, 8))
        cols = tk.Frame(win, bg=P1)
        cols.pack(fill="both", expand=True, padx=8, pady=8)
        self.fl_ed_cols = {}
        for i, (kind, title, hint) in enumerate((("waystones", "Waystone", "one copy of the kind you run"),
                                                 ("tablets", "Tablets & more", "runs each one lasts"))):
            f = tk.Frame(cols, bg=P2, padx=8, pady=8, highlightthickness=1, highlightbackground=C["line"])
            f.grid(row=0, column=i, sticky="nsew", padx=(0, 8))
            h = tk.Frame(f, bg=P2)
            h.pack(fill="x")
            tk.Label(h, text=title, bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold")).pack(side="left")
            tk.Label(h, text=hint, bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=8)
            drop = tk.Label(f, text="Ctrl+Alt+C it in game - or click here to paste",
                            bg=C["panel"], fg=C["muted"], font=("Segoe UI", 9), pady=8, cursor="hand2",
                            highlightthickness=1, highlightbackground=C["gold_dim"])
            drop.pack(fill="x", pady=(8, 8))
            drop.bind("<Button-1>", lambda e, k=kind: self.fl_ed_paste(k))
            lst = tk.Frame(f, bg=P2)
            lst.pack(fill="both", expand=True)
            self.fl_ed_cols[kind] = lst
            cols.columnconfigure(i, weight=1, uniform="c")
        cols.rowconfigure(0, weight=1)
        # ---- atlas + logging
        right = tk.Frame(cols, bg=P1)
        right.grid(row=0, column=2, sticky="nsew")
        cols.columnconfigure(2, weight=1, uniform="c")
        a = tk.Frame(right, bg=P2, padx=8, pady=8, highlightthickness=1, highlightbackground=C["line"])
        a.pack(fill="x")
        tk.Label(a, text="Atlas", bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        self.fl_ed_trees = tk.Frame(a, bg=P2)
        self.fl_ed_trees.pack(fill="x", pady=(4, 4))
        add = tk.Frame(a, bg=P2)
        add.pack(fill="x")
        self.fl_ed_tree_name = tk.StringVar(value=L.ATLAS_TREES[1])
        ttk.Combobox(add, textvariable=self.fl_ed_tree_name, values=list(L.ATLAS_TREES), width=18).pack(side="left")
        self.fl_ed_tree_pts = tk.StringVar(value="10")
        ttk.Spinbox(add, from_=0, to=200, textvariable=self.fl_ed_tree_pts, width=4).pack(side="left", padx=4)
        tk.Label(add, text="points", bg=P2, fg=C["muted"]).pack(side="left")
        ttk.Button(add, text="Add", command=self.fl_ed_add_tree, style="Quiet.TButton").pack(side="left", padx=(8, 0))
        tk.Label(a, text="Atlas link or notes (masters, the order you take nodes …)", bg=P2, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(8, 2))
        self.fl_ed_notes = tk.Text(a, height=3, bg=C["panel"], fg=C["text"], insertbackground=C["text"],
                                   relief="flat", font=("Segoe UI", 9), wrap="word")
        self.fl_ed_notes.pack(fill="x")
        self.fl_ed_notes.insert("1.0", self.fl_ed_ver["atlas"].get("notes", ""))
        g = tk.Frame(right, bg=P2, padx=8, pady=8, highlightthickness=1, highlightbackground=C["line"])
        g.pack(fill="x", pady=(8, 0))
        tk.Label(g, text="Logging", bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        er = tk.Frame(g, bg=P2)
        er.pack(fill="x", pady=(4, 4))
        tk.Label(er, text="Ask for the loot every", bg=P2, fg=C["text"]).pack(side="left")
        self.fl_ed_every = tk.StringVar(value=str(s.get("every", L.EVERY)))
        ttk.Spinbox(er, from_=1, to=100, textvariable=self.fl_ed_every, width=4).pack(side="left", padx=4)
        tk.Label(er, text="runs", bg=P2, fg=C["text"]).pack(side="left")
        self.fl_ed_counting = tk.StringVar(value=s.get("counting", "auto"))
        for k, label in L.COUNTING.items():
            ttk.Radiobutton(g, text=label if k == "auto" else f"{label} ({self.fl_key_label()})",
                            variable=self.fl_ed_counting, value=k).pack(anchor="w")
        xr = tk.Frame(g, bg=P2)
        xr.pack(fill="x", pady=(8, 0))
        tk.Label(xr, text="Other costs a run (omens …)", bg=P2, fg=C["text"]).pack(side="left")
        self.fl_ed_extra = tk.StringVar(value=f"{self.fl_ed_ver.get('extra') or 0:g}")
        ttk.Entry(xr, textvariable=self.fl_ed_extra, width=6).pack(side="left", padx=4)
        tk.Label(xr, text="div", bg=P2, fg=C["text"]).pack(side="left")
        self.fl_ed_extra.trace_add("write", lambda *a: self.fl_ed_cost())
        self.fl_ed_cost_lbl = tk.Label(g, text="", bg=P2, fg=C["good"], font=(MONO, 10, "bold"), anchor="w",
                                       justify="left")
        self.fl_ed_cost_lbl.pack(fill="x", pady=(8, 0))
        self.fl_ed_fill()
        if new:
            win.after(50, lambda: self._say("New setup: name it, then Ctrl+Alt+C your waystone and tablets in game.", 8))
        return win

    def fl_ed_open(self):
        w = getattr(self, "fl_ed", None)
        try:
            return w is not None and w.winfo_exists()
        except tk.TclError:
            return False

    def fl_ed_fill(self):
        P2 = C["panel2"]
        ver = self.fl_ed_ver
        for kind, lst in self.fl_ed_cols.items():
            for c in lst.winfo_children():
                c.destroy()
            items = ver["waystones"] if kind == "waystones" else ver["tablets"] + ver["others"]
            if not items:
                tk.Label(lst, text="Nothing yet.", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(anchor="w")
            for e in items:
                self.fl_ed_card(lst, e, kind)
        for c in self.fl_ed_trees.winfo_children():
            c.destroy()
        for t in ver["atlas"]["trees"]:
            r = tk.Frame(self.fl_ed_trees, bg=P2)
            r.pack(fill="x")
            tk.Label(r, text=t["name"], bg=P2, fg=C["text"], anchor="w").pack(side="left")
            x = tk.Label(r, text="×", bg=P2, fg=C["muted"], cursor="hand2")
            x.pack(side="right")
            x.bind("<Button-1>", lambda ev, t=t: (ver["atlas"]["trees"].remove(t), self.fl_ed_fill()))
            tk.Label(r, text=f"{t.get('points', 0)} points", bg=P2, fg=C["text"], font=(MONO, 9)).pack(side="right", padx=8)
        self.fl_ed_cost()

    def fl_ed_card(self, parent, e, kind):
        P1 = C["panel"]
        card = tk.Frame(parent, bg=P1, padx=8, pady=4, highlightthickness=1, highlightbackground=C["line"])
        card.pack(fill="x", pady=(0, 4))
        h = tk.Frame(card, bg=P1)
        h.pack(fill="x")
        colour = {"Rare": C["rare"], "Magic": C["magic"], "Unique": C["orange"]}.get(e.get("rarity"), C["text"])
        tk.Label(h, text=e["name"] + (f"  ({e['base']})" if e["base"] != e["name"] else ""), bg=P1, fg=colour,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(side="left")
        x = tk.Label(h, text="×", bg=P1, fg=C["muted"], cursor="hand2")
        x.pack(side="right")
        x.bind("<Button-1>", lambda ev: self.fl_ed_remove(e))
        key = [m for m in e.get("mods") or [] if m in (e.get("key_mods") or [])]
        mods = tk.Label(card, text=("★ " + " · ".join(key)) if key else
                        (" · ".join((e.get("mods") or [])[:3]) or "no mods read"),
                        bg=P1, fg=C["good"] if key else C["magic"], font=("Segoe UI", 9), anchor="w", justify="left",
                        wraplength=280)
        mods.pack(fill="x")
        r = tk.Frame(card, bg=P1)
        r.pack(fill="x", pady=(4, 0))
        cnt = tk.StringVar(value=str(e.get("count", 1)))
        ttk.Spinbox(r, from_=1, to=99, textvariable=cnt, width=3).pack(side="left")
        tk.Label(r, text="×", bg=P1, fg=C["muted"]).pack(side="left", padx=(2, 8))
        cnt.trace_add("write", lambda *a: self._fl_ed_int(e, "count", cnt))
        if kind != "waystones":
            tk.Label(r, text="lasts", bg=P1, fg=C["muted"]).pack(side="left")
            lasts = tk.StringVar(value=str(e.get("lasts", 10)))
            ttk.Spinbox(r, from_=1, to=999, textvariable=lasts, width=4).pack(side="left", padx=4)
            tk.Label(r, text="runs", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 8))
            lasts.trace_add("write", lambda *a: self._fl_ed_int(e, "lasts", lasts))
        auto = e.get("price_src", "auto") == "auto"
        pl = tk.Label(r, text=self.fl_price_text(e), bg=P1, fg=C["good"] if L.entry_price(e) is not None else C["muted"],
                      font=(MONO, 9, "bold"))
        pl.pack(side="right")
        mine = tk.StringVar(value="" if auto or e.get("manual") is None else f"{e['manual']:g}")
        ent = ttk.Entry(r, textvariable=mine, width=6)
        ent.pack(side="right", padx=(0, 4))
        Tooltip(ent, "Your own price (divines) - empty: the price checker's")
        mine.trace_add("write", lambda *a: self._fl_ed_manual(e, mine, pl))
        km = tk.Label(card, text="★ Pick the mods that matter…", bg=P1, fg=C["blue"], cursor="hand2",
                      font=("Segoe UI", 9, "underline"), anchor="w")
        km.pack(fill="x", pady=(2, 0))
        km.bind("<Button-1>", lambda ev: self.fl_key_mods(e))

    def fl_price_text(self, e):
        p = L.entry_price(e)
        if e.get("price_src") == "manual" and p is not None:
            return f"{p:.2f}d mine"
        if p is not None:
            return f"{p:.2f}d"
        return e.get("price_note") or "checking…"

    def _fl_ed_int(self, e, key, var):
        try:
            e[key] = max(1, int(var.get()))
        except (ValueError, tk.TclError):
            return
        self.fl_ed_cost()

    def _fl_ed_manual(self, e, var, lbl):
        n = _num(var.get())
        if n is None:
            e["price_src"], e["manual"] = "auto", None
        elif isinstance(n, float):
            e["price_src"], e["manual"] = "manual", n
        lbl.config(text=self.fl_price_text(e), fg=C["good"] if L.entry_price(e) is not None else C["muted"])
        self.fl_ed_cost()

    def fl_ed_cost(self):
        if not self.fl_ed_open():
            return
        n = _num(self.fl_ed_extra.get())
        self.fl_ed_ver["extra"] = n if isinstance(n, float) else 0.0
        per, parts, unknown = L.cost_per_run(self.fl_ed_ver)
        lines = [f"Cost of one run: {per:.3f}d"] + [f"  {lab}: {v:.3f}" for lab, v in parts]
        if unknown:
            lines.append(f"  {unknown} item(s) still without a price")
        self.fl_ed_cost_lbl.config(text="\n".join(lines))

    def fl_ed_remove(self, e):
        for k in ("waystones", "tablets", "others"):
            if e in self.fl_ed_ver[k]:
                self.fl_ed_ver[k].remove(e)
        self.fl_ed_fill()

    def fl_ed_add_tree(self):
        name = self.fl_ed_tree_name.get().strip()
        try:
            pts = int(self.fl_ed_tree_pts.get())
        except ValueError:
            pts = 0
        if not name:
            return
        trees = self.fl_ed_ver["atlas"]["trees"]
        t = next((t for t in trees if t["name"] == name), None)
        if t:
            t["points"] = pts
        else:
            trees.append({"name": name, "points": pts})
        self.fl_ed_fill()

    def fl_ed_paste(self, kind=None):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            text = ""
        if not self.fl_ed_take(text, kind):
            self._say("The clipboard has no item - hover one in game and press Ctrl+Alt+C.", 6)

    def fl_ed_take(self, text, kind=None):
        """A copied item -> the setup (waystone / tablet / other by its item class), priced, then its mods to pick."""
        it = L.parse_item(text)
        if not it:
            return None
        k = L.kind_of(it)
        if kind == "tablets" and k == "waystones":
            k = "waystones"
        e = L.new_entry(it, k)
        self.fl_ed_ver[k].append(e)
        self.fl_ed_fill()
        self.fl_price_entry(e)
        if e["mods"]:
            self.root.after(100, lambda: self.fl_key_mods(e))
        return e

    def fl_price_entry(self, e):
        """The price checker prices it, out of sight (its row lives in no list you see), then it's gone again."""
        try:
            item = self.read_any(e["text"])
        except Exception:
            item = None
        if not item:
            e["price_note"] = "type its price"
            return None
        rid = self.next_id
        self.next_id += 1
        self.records[rid] = {"id": rid, "item": item, "state": "queued", "label": "", "total": 0, "prices": [],
                             "est": None, "qid": None, "time": time.time(), "resolved": False, "mark": "new",
                             "raw": e["text"], "src": "ledger"}
        self.fl_pricing = getattr(self, "fl_pricing", {})
        self.fl_pricing[rid] = e
        self.engine.add(1, "resolve", rid)
        return rid

    def fl_priced(self, rid, error=None):
        """(ev_priced / ev_error) a setup item's price came back."""
        e = getattr(self, "fl_pricing", {}).pop(rid, None)
        rec = self.records.pop(rid, None)
        if e is None:
            return
        if error or rec is None or rec.get("est") is None:
            e["price_note"] = "no price found - type it"
        else:
            e["price"], e["priced_at"], e["price_note"] = float(rec["est"]), time.time(), ""
        d = self.fl_data()                                        # (also update the saved setup, if it holds it)
        for s in d["setups"]:
            for v in s["versions"]:
                for k in ("waystones", "tablets", "others"):
                    for x in v[k]:
                        if x.get("id") == e.get("id") and x is not e:
                            x.update(price=e.get("price"), priced_at=e.get("priced_at"), price_note=e["price_note"])
        self.fl_save()
        if self.fl_ed_open():
            self.fl_ed_fill()
        self.fl_fill_setup() if hasattr(self, "fl_title") else None

    def fl_key_mods(self, e):
        """Which mods make it work? Starred mods are what the setup needs (shown on the card; 2.46.0 checks their cost
        every day)."""
        if not e.get("mods"):
            return None
        win = tk.Toplevel(self.root)
        win.title("The mods that matter")
        win.configure(bg=C["panel"])
        win.transient(self.root)
        f = tk.Frame(win, bg=C["panel"], padx=16, pady=12)
        f.pack(fill="both", expand=True)
        tk.Label(f, text=f"{e['name']}: which mods make this setup work?", bg=C["panel"], fg=C["accent"],
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(f, text="Tick the ones you'd pay for (pack size, rarity, +1 Breach …). They're shown on the setup and "
                         "used to check what it costs.", bg=C["panel"], fg=C["muted"], font=("Segoe UI", 9),
                 wraplength=420, justify="left", anchor="w").pack(fill="x", pady=(2, 8))
        vars_ = []
        for m in e["mods"]:
            v = tk.BooleanVar(value=m in (e.get("key_mods") or []))
            ttk.Checkbutton(f, text=m, variable=v).pack(anchor="w")
            vars_.append((m, v))

        def ok():
            e["key_mods"] = [m for m, v in vars_ if v.get()]
            win.destroy()
            if self.fl_ed_open():
                self.fl_ed_fill()
        b = tk.Frame(f, bg=C["panel"])
        b.pack(fill="x", pady=(12, 0))
        ttk.Button(b, text="Done", style="Primary.TButton", command=ok).pack(side="right")
        ttk.Button(b, text="Skip", style="Quiet.TButton", command=win.destroy).pack(side="right", padx=(0, 8))
        self.fl_km_win, self.fl_km_vars, self.fl_km_ok = win, vars_, ok
        return win

    def fl_ed_save(self):
        d, s = self.fl_data(), self.fl_ed_s
        ver = self.fl_ed_ver
        ver["atlas"]["notes"] = self.fl_ed_notes.get("1.0", "end-1c").strip()
        s["name"] = self.fl_ed_name.get().strip()[:60] or s["name"]
        s["strat"] = self.fl_ed_strats.get(self.fl_ed_strat.get())
        try:
            s["every"] = max(1, int(self.fl_ed_every.get()))
        except ValueError:
            pass
        s["counting"] = self.fl_ed_counting.get()
        cur = L.version(s)
        changed = L.what_changed(cur, ver) != "-"
        if changed and L.has_logs(d, s["id"], cur["v"]):            # numbers so far stay with the old version
            nv = L.bump_version(s)
            for k in ("waystones", "tablets", "others", "atlas", "extra"):
                nv[k] = ver[k]
            self._say(f"Saved as v{nv['v']}: {L.what_changed(cur, nv)}. The logs so far stay with v{cur['v']}.", 8)
        else:
            for k in ("waystones", "tablets", "others", "atlas", "extra"):
                cur[k] = ver[k]
        p = d.get("pending")
        if p and p.get("setup") == s["id"] and not p.get("runs"):
            p["v"] = L.version(s)["v"]
        self.fl_save()
        try:
            self.fl_ed.destroy()
        except tk.TclError:
            pass
        self.fl_ed = None
        self.fl_refresh()
