"""Money Makers > Strat Tracker (2.45.0, was Run tracker): the window, the setup editor, the log box (in the app and
over the game) and the run counting. Data and every calculation live in ledger.py.

The Session timer times your play; the Strat Tracker measures one farming SETUP - what a run costs, what its loot is
worth, and whether it beats your other setups. ToS: it only reads your copies (Ctrl+Alt+C, which you press) and
Client.txt, and shows a box; it never acts in the game."""
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import ledger as L
from . import moneymakers as MM
from .config import SETTINGS, save_json
from .pricefmt import fmt_short
from .chrome import section as chrome_section
from .style import C, MONO, ScrollArea, SegBar, Tooltip
from .trade import listing_rules


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


# 2.56.0: Div / hour is the verdict's big number; these are the tiles next to it
TILES = (("profit", "Profit / run", "loot − cost"), ("roi", "Loot ÷ cost", "150% = the loot is worth 1.5× the cost"),
         ("avg", "Average run", ""), ("loot", "Loot / run", ""), ("cost", "Cost / run", ""), ("runs", "Runs", ""))
LOG_COLS = (("n", "#", 40, "e"), ("when", "When", 120, "w"), ("v", "Ver.", 44, "center"), ("runs", "Runs", 50, "e"),
            ("time", "Time", 70, "e"), ("cost", "Cost", 66, "e"), ("loot", "Loot", 70, "e"), ("profit", "Profit", 74, "e"),
            ("ppr", "Profit/run", 78, "e"), ("dph", "d/h", 60, "e"), ("note", "Note", 220, "w"))
LOOT_COLS = (("item", "Item", 260, "w"), ("qty", "Dropped", 80, "e"), ("total", "Worth", 90, "e"),
             ("share", "Share", 80, "e"), ("per", "Per run", 80, "e"))
EDITABLE = {"runs": "runs", "cost": "cost", "loot": "loot", "profit": "profit", "note": "note"}


class Steps:
    """2.70.0: a short form in steps - numbered steps along the top (click one to go there), one page at a time.
    col: bg / band / text / muted / accent colors (the app's theme, or the overlay's palette)."""

    def __init__(self, parent, names, col, on_change=None, font="Segoe UI"):
        self.names, self.col, self.on_change, self.font = list(names), col, on_change, font
        self.bar = tk.Frame(parent, bg=col["band"], padx=8, pady=8)
        self.pills = []
        for i, n in enumerate(self.names):
            if i:
                tk.Label(self.bar, text="›", bg=col["band"], fg=col["muted"], font=(font, 10)).pack(side="left", padx=2)
            lb = tk.Label(self.bar, text=f"{i + 1}  {n}", bg=col["band"], fg=col["muted"], font=(font, 10),
                          cursor="hand2", padx=8, pady=2)
            lb.pack(side="left")
            lb.bind("<Button-1>", lambda e, i=i: self.go(i))
            self.pills.append(lb)
        self.body = tk.Frame(parent, bg=col["bg"])
        self.frames = [tk.Frame(self.body, bg=col["bg"]) for _ in self.names]
        self.cur, self.seen = 0, {0}

    def go(self, i):
        i = max(0, min(len(self.frames) - 1, i))
        for f in self.frames:
            f.pack_forget()
        self.frames[i].pack(fill="both", expand=True)
        self.cur = i
        self.seen.add(i)
        c = self.col
        for j, lb in enumerate(self.pills):
            now = j == i
            lb.config(text=("✓ " if j in self.seen and not now and j < i else "") + f"{j + 1}  {self.names[j]}",
                      fg=c["accent"] if now else (c["text"] if j in self.seen else c["muted"]),
                      font=(self.font, 10, "bold") if now else (self.font, 10))
        if self.on_change:
            self.on_change(i)
        return i

    def last(self):
        return self.cur == len(self.frames) - 1


class SetupCards(tk.Frame):
    """2.56.0: your setups as cards (name, what it is, its div / hour; a dot while its runs are counted). Click picks,
    Ctrl+click picks several (for Compare), right-click is the setup's menu. Answers like the list it replaced:
    selection(), selection_set(), exists()."""

    def __init__(self, parent, page, bg):
        super().__init__(parent, bg=bg)
        self.page, self.bg = page, bg
        self.area = ScrollArea(self, bg=bg)
        self.area.pack(fill="both", expand=True)
        self.cards, self.sel = {}, []

    def clear(self):
        for c in self.cards.values():
            c[0].destroy()
        self.cards = {}

    def add(self, sid, name, sub, ph, counting=False):
        f = tk.Frame(self.area.inner, bg=C["panel"], padx=8, pady=8, highlightthickness=1,
                     highlightbackground=C["line"], cursor="hand2")
        f.pack(fill="x", pady=(0, 8))
        top = tk.Frame(f, bg=C["panel"])
        top.pack(fill="x")
        n = tk.Label(top, text=name, bg=C["panel"], fg="#ffffff", font=("Segoe UI", 10, "bold"), anchor="w")
        n.pack(side="left")
        bits = [f, top, n]
        if counting:
            dot = tk.Label(top, text="● counting", bg=C["panel"], fg=C["green"], font=("Segoe UI", 9))
            dot.pack(side="right")
            bits.append(dot)
        s = tk.Label(f, text=sub, bg=C["panel"], fg=C["muted"], font=("Segoe UI", 9), anchor="w")
        s.pack(fill="x")
        row = tk.Frame(f, bg=C["panel"])
        row.pack(fill="x", pady=(2, 0))
        v = tk.Label(row, text="-" if ph is None else f"{ph:.1f}", bg=C["panel"],
                     fg=C["accent"] if ph is not None and ph >= 0 else C["red"] if ph is not None else C["muted"],
                     font=("Segoe UI", 16, "bold"))
        v.pack(side="left")
        u = tk.Label(row, text="div / hour" if ph is not None else "not enough runs yet", bg=C["panel"],
                     fg=C["muted"], font=("Segoe UI", 9))
        u.pack(side="left", padx=(8, 0), pady=(4, 0))
        bits += [s, row, v, u]
        for w in bits:
            w.bind("<Button-1>", lambda e, i=sid: self._click(i, e))
            w.bind("<Button-3>", lambda e, i=sid: self._menu(i, e))
        self.cards[sid] = (f, bits)

    def _click(self, sid, e):
        if e.state & 0x0004:                                   # Ctrl: pick several
            sel = [i for i in self.sel if i != sid] if sid in self.sel else self.sel + [sid]
            self.selection_set(sel or [sid])
        else:
            self.selection_set([sid])
            self.page.fl_pick()

    def _menu(self, sid, e):
        self.selection_set([sid])
        self.page.fl_pick()
        self.page.fl_setup_menu(e)

    def selection(self):
        return tuple(self.sel)

    def selection_set(self, ids):
        ids = [ids] if isinstance(ids, str) else list(ids)
        self.sel = [i for i in ids if i in self.cards]
        for sid, (f, bits) in self.cards.items():
            on = sid in self.sel
            bg = C["panel2"] if on else C["panel"]
            f.config(highlightbackground=C["accent"] if on else C["line"])
            for w in bits:
                try:
                    w.config(bg=bg)
                except tk.TclError:
                    pass

    def exists(self, sid):
        return sid in self.cards

    def get_children(self):
        return tuple(self.cards)


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
        """2.56.0 (feedback: "a bit confusing ... modern, clean, functional, ease of use for the average user"; the
        Strat Tracker Redesign mockups): your setups as cards on the left; on the right the setup's name and what it
        is, ONE main button (Log loot), whether runs are being counted, then the verdict in plain words ("Makes about
        10.3 div an hour"), the figures, where the money comes from, profit per log, and the sheet. No setup yet:
        three steps and a button."""
        P1, P2 = C["panel"], C["panel2"]
        self.fl_view_v = None                                   # None: the setup's current version; else one version
        body = tk.Frame(page, bg=P1)
        body.pack(fill="both", expand=True, pady=(8, 0))
        # ---- left: your setups (cards)
        left = tk.Frame(body, bg=P2, padx=8, pady=8, highlightthickness=1, highlightbackground=C["line"], width=250)
        left.pack(side="left", fill="y", padx=(8, 0), pady=(0, 8))
        left.pack_propagate(False)
        lh = tk.Frame(left, bg=P2)
        lh.pack(fill="x")
        tk.Label(lh, text="MY SETUPS", bg=P2, fg=C["muted"], font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(lh, text="＋ New", command=self.fl_new, style="Quiet.TButton").pack(side="right")
        self.fl_list = SetupCards(left, self, bg=P2)
        self.fl_list.pack(fill="both", expand=True, pady=(8, 8))
        ttk.Button(left, text="Compare setups", command=self.fl_compare).pack(fill="x")
        tk.Label(left, text="Ctrl+click cards to compare a few. Right-click a card: rename, duplicate, delete.",
                 bg=P2, fg=C["muted"], font=("Segoe UI", 9), justify="left", anchor="w", wraplength=226).pack(
            fill="x", pady=(8, 0))
        # ---- right: no setup yet
        self.fl_empty = self._fl_empty_page(body)
        # ---- right: the setup
        main = tk.Frame(body, bg=P1)
        self.fl_main = main
        main.pack(side="left", fill="both", expand=True, padx=12, pady=(0, 8))
        head = tk.Frame(main, bg=P1)
        head.pack(fill="x")
        names = tk.Frame(head, bg=P1)
        names.pack(side="left", fill="x", expand=True)
        self.fl_title = tk.Label(names, text="", bg=P1, fg="#ffffff", font=("Segoe UI", 16, "bold"), anchor="w")
        self.fl_title.pack(anchor="w")
        self.fl_sub = tk.Label(names, text="", bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left")
        self.fl_sub.pack(anchor="w", fill="x")
        self.fl_sub.bind("<Configure>", lambda e: self.fl_sub.config(wraplength=max(200, e.width - 4)))
        btns = tk.Frame(main, bg=P1)                            # (its own row: never cut off in a narrow window)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Log loot", style="Primary.TButton", command=self.fl_log_now).pack(side="right")
        ttk.Button(btns, text="Edit setup", command=self.fl_edit).pack(side="right", padx=(0, 8))
        self.fl_export_btn = ttk.Button(btns, text="Export ▾", command=self.fl_export_menu, style="Quiet.TButton")
        self.fl_export_btn.pack(side="right", padx=(0, 8))
        self.fl_upload_btn = ttk.Button(btns, text="📤 Upload", command=self.fl_upload, style="Quiet.TButton")
        self.fl_upload_btn.pack(side="right", padx=(0, 8))         # 2.69.1: to the community strats
        tk.Label(btns, text="Numbers from", bg=P1, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left")
        self.fl_ver_var = tk.StringVar()
        self.fl_ver_box = ttk.Combobox(btns, textvariable=self.fl_ver_var, state="readonly", width=16)
        self.fl_ver_box.pack(side="left", padx=(8, 8))
        self.fl_ver_box.bind("<<ComboboxSelected>>", lambda e: (self.fl_ver_picked(),
                                                               self.root.after(20, self.root.focus_set)))
        Tooltip(self.fl_ver_box, "A changed tablet or atlas makes a new version: show one version's numbers, or all")
        # ---- counting runs
        st = tk.Frame(main, bg="#10203a", padx=12, pady=8, highlightthickness=1, highlightbackground="#22426e")
        st.pack(fill="x", pady=(8, 0))
        self.fl_count_btn = ttk.Button(st, text="▶ Start counting", command=self.fl_count_toggle, style="Quiet.TButton")
        self.fl_count_btn.pack(side="right")
        self.fl_dots = tk.Canvas(st, width=10, height=8, bg="#10203a", highlightthickness=0)
        self.fl_dots.pack(side="right", padx=(8, 12))
        self.fl_status = tk.Label(st, text="", bg="#10203a", fg=C["text"], font=("Segoe UI", 9), anchor="w",
                                  justify="left")
        self.fl_status.pack(side="left", fill="x", expand=True)
        self.fl_status.bind("<Configure>", lambda e: self.fl_status.config(wraplength=max(200, e.width - 4)))
        # ---- the verdict, and the figures
        vrow = tk.Frame(main, bg=P1)
        vrow.pack(fill="x", pady=(8, 0))
        verdict = tk.Frame(vrow, bg=P2, padx=16, pady=12, highlightthickness=1, highlightbackground=C["line"])
        verdict.pack(side="left", fill="both", expand=True)
        tk.Label(verdict, text="THE VERDICT", bg=P2, fg=C["muted"], font=("Segoe UI", 9, "bold"), anchor="w").pack(
            fill="x")
        line = tk.Frame(verdict, bg=P2)
        line.pack(fill="x", pady=(2, 2))
        self.fl_v_pre = tk.Label(line, text="", bg=P2, fg="#ffffff", font=("Segoe UI", 16, "bold"))
        self.fl_v_pre.pack(side="left")
        ph_v = tk.Label(line, text="-", bg=P2, fg=C["accent"], font=("Segoe UI", 16, "bold"))
        ph_v.pack(side="left")
        self.fl_v_post = tk.Label(line, text="", bg=P2, fg=C["accent"], font=("Segoe UI", 16, "bold"))
        self.fl_v_post.pack(side="left")
        self.fl_v_why = tk.Label(verdict, text="", bg=P2, fg=C["text"], font=("Segoe UI", 10), anchor="w",
                                 justify="left")
        self.fl_v_why.pack(fill="x")
        ph_s = tk.Label(verdict, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left")
        ph_s.pack(fill="x", pady=(4, 0))
        for lab in (self.fl_v_why, ph_s):
            lab.bind("<Configure>", lambda e, l=lab: l.config(wraplength=max(200, e.width - 4)))
        self.fl_kpi = {"ph": (ph_v, ph_s)}
        grid = tk.Frame(vrow, bg=P1)
        grid.pack(side="left", fill="y", padx=(8, 0))
        for i, (k, label, note) in enumerate(TILES):
            f = tk.Frame(grid, bg=P2, padx=8, pady=2, highlightthickness=1, highlightbackground=C["line"])
            f.grid(row=i // 2, column=i % 2, sticky="nsew", padx=(0, 8), pady=(0, 8))
            grid.columnconfigure(i % 2, weight=1, uniform="t", minsize=112)
            tk.Label(f, text=label, bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(anchor="w")
            v = tk.Label(f, text="-", bg=P2, fg=C["text"], font=(MONO, 12, "bold"), anchor="w")
            v.pack(anchor="w")
            s = tk.Label(f, text=note, bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w")
            s.pack(anchor="w")
            self.fl_kpi[k] = (v, s)
        # ---- where the money comes from | profit per log
        crow = tk.Frame(main, bg=P1)
        crow.pack(fill="both", expand=True, pady=(4, 0))
        self.fl_money = tk.Canvas(crow, height=110, bg=P2, highlightthickness=1, highlightbackground=C["line"])
        self.fl_money.pack(side="left", fill="both", expand=True)
        self.fl_money.bind("<Configure>", lambda e: self.fl_draw_money())
        self.fl_chart = tk.Canvas(crow, height=110, bg=P2, highlightthickness=1, highlightbackground=C["line"])
        self.fl_chart.pack(side="left", fill="both", expand=True, padx=(8, 0))
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
        self.fl_tree = ttk.Treeview(box, show="headings", selectmode="extended", height=5)
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
        # the sheet keeps its room in a short window (the verdict and charts give way first)
        for w, kw in ((box, dict(side="bottom", fill="x")), (bar, dict(side="bottom", fill="x",
                                                                                     pady=(8, 4)))):
            w.pack_forget()
            w.pack(before=vrow, **kw)
        self.fl_refresh()

    def _fl_empty_page(self, parent):
        """First time: what the Strat Tracker does, in three steps, and one button."""
        P1, P2 = C["panel"], C["panel2"]
        f = tk.Frame(parent, bg=P1)
        inner = tk.Frame(f, bg=P1)
        inner.place(relx=0.5, rely=0.42, anchor="center")
        tk.Label(inner, text="Does a farming setup really make money?", bg=P1, fg="#ffffff",
                 font=("Segoe UI", 18, "bold")).pack()
        tk.Label(inner, text="The Strat Tracker works it out from your own runs: what a run costs, what its loot is "
                             "worth, and how many divines an hour that makes.", bg=P1, fg=C["text"],
                 font=("Segoe UI", 10), wraplength=560, justify="center").pack(pady=(8, 16))
        steps = tk.Frame(inner, bg=P1)
        steps.pack()
        for i, (t, d) in enumerate((("Make a setup", "Ctrl+Alt+C your waystone and tablets in game. The app prices "
                                                     "them, so it knows what one run costs."),
                                    ("Just play", "Runs are counted by themselves from the game's log file. Nothing "
                                                  "acts in the game."),
                                    ("Log your loot", "Every few runs a box asks for your drops (Ctrl+Alt+C each). You "
                                                      "get profit per run and div / hour."))):
            c = tk.Frame(steps, bg=P2, padx=16, pady=12, highlightthickness=1, highlightbackground=C["line"],
                         width=220, height=150)
            c.grid(row=0, column=i, padx=8, sticky="n")
            c.pack_propagate(False)
            tk.Label(c, text=str(i + 1), bg=C["accent"], fg="#1a1206", font=("Segoe UI", 12, "bold"), width=2).pack(
                anchor="w")
            tk.Label(c, text=t, bg=P2, fg="#ffffff", font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x",
                                                                                                   pady=(8, 2))
            tk.Label(c, text=d, bg=P2, fg=C["muted"], font=("Segoe UI", 9), wraplength=190, justify="left",
                     anchor="w").pack(fill="x")
        b = tk.Frame(inner, bg=P1)
        b.pack(pady=(16, 0))
        ttk.Button(b, text="Make my first setup", style="Primary.TButton", command=self.fl_new).pack(side="left")
        ttk.Button(b, text="Start from a strat", command=self._fl_to_strats).pack(side="left", padx=(8, 0))
        ttk.Button(b, text="Import a CSV…", style="Quiet.TButton", command=self.fl_import_csv).pack(side="left",
                                                                                                 padx=(8, 0))
        return f

    def _fl_to_strats(self):
        self.mm_page.pick("Strats", notify=False)
        self.mm_show_page()

    # ================================================================ filling it
    def fl_refresh(self):
        if not hasattr(self, "fl_list"):
            return
        d = self.fl_data()
        cards = self.fl_list
        sel = set(cards.selection())
        cards.clear()
        pend = (d.get("pending") or {}).get("setup")
        for s in d["setups"]:
            f = L.figures(L.logs_of(d, s["id"]))
            strat = next((x for x in self.fl_all_strats() if x["id"] == s.get("strat")), None)
            what = (strat.get("type") or strat["name"]) if strat else "your own"
            cards.add(s["id"], s["name"], f"{what} · {f['runs']} runs · {f['logs']} logs", f["per_hour"],
                      counting=pend == s["id"])
        cur = self.fl_setup()
        keep = [i for i in sel if cards.exists(i)]
        if cur and not (len(keep) > 1 and cur["id"] in keep):       # (several picked for Compare: keep them)
            keep = [cur["id"]]
        cards.selection_set(keep)
        self.fl_fill_setup()

    def fl_pick(self):
        sel = self.fl_list.selection()
        if not sel:
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
        if not s:
            self.fl_main.pack_forget()
            self.fl_empty.pack(side="left", fill="both", expand=True, padx=12, pady=(0, 8))
            self.fl_title.config(text="No setup yet")
            self.fl_fill_sheet()
            return
        if not self.fl_main.winfo_ismapped():
            self.fl_empty.pack_forget()
            self.fl_main.pack(side="left", fill="both", expand=True, padx=12, pady=(0, 8))
        ver = L.version(s)
        strat = next((x for x in self.fl_all_strats() if x["id"] == s.get("strat")), None)
        self.fl_title.config(text=f"{s['name']}   v{ver['v']}")
        cost, _parts, unknown = L.cost_per_run(ver)
        chips = []
        if ver["waystones"]:
            w = ver["waystones"][0]
            chips.append(f"Waystone {('T' + str(w['tier'])) if w.get('tier') else w['name']}"
                         + (f" ({len(w['mods'])} mods)" if w.get("mods") else ""))
        if ver["tablets"]:
            chips.append(", ".join(f"{t.get('count', 1)}× {t['base'] or t['name']}" for t in ver["tablets"]))
        if ver["atlas"]["trees"]:
            chips.append("Atlas: " + ", ".join(f"{t['name']} {t.get('points', 0)}" for t in ver["atlas"]["trees"]))
        line = (f"Strat: {strat['name']}" if strat else "Your own setup (no strat)") + \
            f"  ·  a run costs {_d(cost)}" + (f" ({unknown} without a price)" if unknown else "")
        self.fl_sub.config(text=line + ("  ·  " + "  ·  ".join(chips) if chips else
                                        "  ·  Edit setup: add your waystone and tablets"))
        vers = ["All versions"] + [f"v{x['v']}" + (" (now)" if x["v"] == ver["v"] else "") for x in s["versions"]]
        self.fl_ver_box.config(values=vers)
        self.fl_ver_var.set(vers[0] if self.fl_view_v is None else
                            next((x for x in vers if x.startswith(f"v{self.fl_view_v}")), vers[0]))
        f = L.figures(self.fl_logs_shown())
        k = self.fl_kpi
        ph, pr = f["per_hour"], f["profit_run"]
        # ---- the verdict, in plain words
        if ph is None:
            self.fl_v_pre.config(text="Not enough logged yet" if f["runs"] else "No runs logged yet")
            k["ph"][0].config(text="")
            self.fl_v_post.config(text="")
            self.fl_v_why.config(text="Play a few runs with this setup, then press Log loot and copy your drops. "
                                      f"One run costs {_d(cost)}.")
        else:
            self.fl_v_pre.config(text="Makes about " if ph >= 0 else "Loses about ")
            k["ph"][0].config(text=f"{abs(ph):.1f}" if ph < 0 else f"{ph:.1f}", fg=C["accent"] if ph >= 0 else C["red"])
            self.fl_v_post.config(text=" div an hour", fg=C["accent"] if ph >= 0 else C["red"])
            why = (f"Every run costs {_d(f['cost_run'])} and brings back {_d(f['loot_run'])} of loot: "
                   f"{_d(pr, True)} {'profit' if (pr or 0) >= 0 else 'loss'} a run.")
            best = self._fl_rank(s, ph)
            self.fl_v_why.config(text=why + (f" {best}" if best else ""))
        bad = sum(1 for l in self.fl_logs_shown() if not l.get("skipped") and (l.get("profit") or 0) < 0)
        k["ph"][1].config(text=(f"From {f['runs']} runs in {f['logs']} log{'s' if f['logs'] != 1 else ''}"
                                + (f" · {bad} log{'s' if bad != 1 else ''} lost money" if bad else "")
                                + " · prices from poe.ninja" + (f" · {self.fl_best_other(s, ph)}"
                                                                 if self.fl_best_other(s, ph) else ""))
                          if f["runs"] else "")
        # ---- the figures
        k["runs"][0].config(text=str(f["runs"]))
        k["runs"][1].config(text=f"{f['logs']} logs")
        k["avg"][0].config(text=_hms(f["avg_run"]) if f["avg_run"] else "-")
        k["avg"][1].config(text=f"fastest {_hms(f['fastest'])}" if f["fastest"] else "a run, on average")
        k["cost"][0].config(text=_d(f["cost_run"]) if f["cost_run"] is not None else _d(cost))
        k["cost"][1].config(text="logged" if f["cost_run"] is not None else "from the setup")
        k["loot"][0].config(text=_d(f["loot_run"]))
        k["loot"][1].config(text=f"median {_d(f['loot_run_median'])}" if f["loot_run_median"] is not None
                            else "a run, on average")
        k["profit"][0].config(text=_d(pr, True), fg=C["green"] if (pr or 0) > 0 else C["red"] if (pr or 0) < 0 else C["text"])
        k["profit"][1].config(text=f"loot − cost · ±{f['spread']:.2f}" if f["spread"] is not None else "loot − cost")
        k["roi"][0].config(text="-" if f["roi"] is None else f"{f['roi'] * 100:.0f}%")
        self.fl_fill_sheet()
        self.fl_draw_chart()
        self.fl_draw_money()
        self.fl_paint_status()

    def _fl_rank(self, s, ph):
        """"Your best setup so far." / "Your 2nd best of 3." - against your other setups with numbers."""
        d = self.fl_data()
        others = [L.figures(L.logs_of(d, x["id"]))["per_hour"] for x in d["setups"] if x["id"] != s["id"]]
        others = [x for x in others if x is not None]
        if not others or self.fl_view_v is not None:
            return ""
        place = 1 + sum(1 for x in others if x > ph)
        return "Your best setup so far." if place == 1 else \
            f"Your {place}{'nd' if place == 2 else 'rd' if place == 3 else 'th'} best of {len(others) + 1}."

    def fl_draw_money(self):
        """Where the money comes from: the top drops as bars, the rest together."""
        cv = getattr(self, "fl_money", None)
        if cv is None:
            return
        cv.delete("all")
        w = max(200, cv.winfo_width())
        cv.create_text(10, 10, text="WHERE THE MONEY COMES FROM", anchor="nw", fill=C["muted"],
                       font=("Segoe UI", 9, "bold"))
        rows = L.loot_table(self.fl_logs_shown())
        if not rows:
            cv.create_text(w // 2, 64, text="Your drops show here once you log loot", fill=C["muted"],
                           font=("Segoe UI", 9))
            return
        top = rows[:3]
        rest = rows[3:]
        if rest:
            top = top + [{"name": f"Everything else ({len(rest)})", "total": sum(g["total"] for g in rest),
                          "share": sum(g["share"] for g in rest), "_rest": True}]
        y, name_w, val_w = 34, min(150, w // 3), 70
        for g in top:
            cv.create_text(10, y, text=g["name"][:22], anchor="w", fill=C["muted"] if g.get("_rest") else C["text"],
                           font=("Segoe UI", 9))
            x0, x1 = 10 + name_w, w - val_w - 10
            cv.create_rectangle(x0, y - 4, x1, y + 4, fill=C["line"], width=0)
            cv.create_rectangle(x0, y - 4, x0 + max(2, (x1 - x0) * g["share"]), y + 4,
                                fill=C["steel"] if g.get("_rest") else C["accent"], width=0)
            cv.create_text(w - 10, y, text=f"{g['total']:.2f} div", anchor="e", fill=C["text"], font=(MONO, 9))
            y += 20

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
        """The strip under the buttons: are runs being counted, how many since the last log (dots), when the box
        opens."""
        d, s = self.fl_data(), self.fl_setup()
        p = d.get("pending")
        every = int(s.get("every", L.EVERY)) if s else L.EVERY
        done = 0
        if p and s and p.get("setup") == s["id"]:
            done = int(p.get("runs", 0))
            how = "Counting runs by itself" if s.get("counting", "auto") == "auto" else \
                f"Counting: press {self.fl_key_label()} after each run"
            txt = f"● {how}  ·  {done} run{'s' if done != 1 else ''} since your last log  ·  the loot box opens " \
                  f"after {every}, back in your hideout"
            self.fl_count_btn.config(text="■ Stop counting")
            fg = C["green"]
        elif p:
            other = L.setup(d, p.get("setup"))
            txt = f"Counting runs for {other['name'] if other else 'another setup'} - pick it to see it."
            self.fl_count_btn.config(text="▶ Count this one")
            fg = C["text"]
        else:
            txt = f"Not counting. Press Start counting when you farm with this setup - the loot box opens every " \
                  f"{every} runs."
            self.fl_count_btn.config(text="▶ Start counting")
            fg = C["muted"]
        self.fl_status.config(text=txt, fg=fg)
        cv = getattr(self, "fl_dots", None)
        if cv is not None:                                       # one dash per run of this log
            n = max(1, min(every, 20))
            cv.delete("all")
            cv.config(width=n * 22)
            for i in range(n):
                cv.create_rectangle(i * 22, 1, i * 22 + 18, 7, width=0,
                                    fill=C["accent"] if i < done else "#2c3d60")

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
            strat = next((x for x in self.fl_all_strats() if x["id"] == sid), None)
            s = L.new_setup(strat["name"] if strat else "New setup", strat=sid)
            d["setups"].append(s)
        d["current"] = s["id"]
        self.fl_view_v = None
        self.fl_save()
        self.fl_refresh()
        return s

    def fl_list_menu(self, e):
        """(kept for older callers)"""
        return self.fl_setup_menu(e)

    def fl_setup_menu(self, e):
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
            if key == "runs":                              # 2.85.0: the cost scales with the runs (it stayed at the old count)
                old = max(1, int(l.get("runs") or 1))
                l["runs"] = max(1, int(n))
                if isinstance(l.get("cost"), (int, float)) and l["runs"] != old:
                    l["cost"] = round(l["cost"] * l["runs"] / old, 4)
                    if l.get("loot") is not None:
                        l["profit"] = round(l["loot"] - l["cost"], 4)
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
        m.add_command(label="Setup file (.json) - for a friend's Strat Tracker", command=lambda: self.fl_export("json"))
        m.add_command(label="Strat guide (CSV) - share this setup as a strat", command=lambda: self.fl_export("strat"))
        m.add_command(label="Copy summary (for Discord)", command=self.fl_copy_summary)
        m.add_command(label="📤 Upload to the community strats…", command=self.fl_upload)
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

    # ---------------- 2.69.1: upload a setup (with its numbers) to the community strats on the Money Makers board
    def fl_upload(self):
        """This setup as a strat (fl_strat_guide: its guide, items, mods that matter, atlas, content, cost and profit
        per run) -> kept in Money Makers › Mine, then posted to the community board. 2.78.0: the Publish step is
        asked first when what it is, Thinking, Clicks or the steps aren't picked yet (they were filled with
        defaults and posted without asking). Needs Community data sharing on and a board name (asks). The atlas
        screenshot goes up first. -> "posted" / "ask" / "fill" / None."""
        s = self.fl_setup()
        if not s:
            self._say("Pick a setup to upload first.", 6)
            return None
        if self.fl_pub_missing(self.fl_guide_of(s)):
            self.fl_edit()
            self.fl_ed_steps.go(len(self.fl_ed_steps.frames) - 1)
            self._say("Before it goes out: say what it is, how much thinking and clicking it takes, and its steps.", 8)
            return "ask"
        if not self.cm_need_sharing(self.fl_upload):
            return None
        st = self.fl_keep_mine(s)
        probs = MM.validate(st)
        if probs:
            self.fl_upload_fill(st, probs)
            return "fill"
        if self.mm_need_login("upload a strat"):
            return None
        data = {k: v for k, v in MM.tidy(st).items() if k not in ("id", "author")}
        from . import board as B
        from . import stratimg

        def work():
            if data.get("atlas_image", "").startswith("l:"):
                ok, ref = stratimg.upload(data["atlas_image"])
                if not ok:
                    return False, f"The atlas screenshot didn't upload ({ref})."
                data["atlas_image"] = ref
                st["atlas_image"] = ref                          # (Mine keeps the board's copy too)
                MM.save_mine([m for m in MM.mine() if m["id"] != st["id"]] + [MM.tidy(st)])
            return B.post("strat", data)

        def done(r):
            self.mm_board_result(r, f"Uploaded \"{st['name']}\" to the community strats.")
            if str(st.get("atlas_image", "")).startswith("b:"):    # (uploaded once: the setup keeps the board's copy)
                L.version(s)["atlas"]["image"] = st["atlas_image"]
                self.fl_save()
            if r and r[0]:
                self.fl_show_in_mm(st["id"])
        self._mm_bg(work, done)
        return "posted"

    def fl_guide_of(self, s):
        """The Publish step's answers for a setup, over the strat it follows (if it follows one)."""
        base = next((x for x in self.fl_all_strats() if x["id"] == s.get("strat")), None) or {}
        gd = {k: base[k] for k in ("category", "type", "summary", "thoughts_per_click", "clicks_per_hour", "tags",
                                   "steps") if base.get(k)}
        gd.update({k: v for k, v in (s.get("guide") or {}).items() if v not in (None, "", [])})
        return gd

    def fl_keep_mine(self, s):
        """The setup as a strat, kept in Money Makers › Mine. -> the strat."""
        st = self.fl_strat_guide(s)
        st["id"] = MM.slug("my-" + (st.get("name") or s["name"]))
        st["author"] = st.get("author") or SETTINGS.get("wealth_account") or "me"
        MM.save_mine([m for m in MM.mine() if m["id"] != st["id"]] + [MM.tidy(st)])
        return st

    def fl_show_in_mm(self, sid):
        """After publishing: Money Makers on the strat (its items, regex and trade links)."""
        try:
            self.shell.open("money")
        except Exception:
            pass
        try:
            self.mm_page.pick("Strats", notify=False)
            self.mm_show_page()
            self.mm_show_mine(sid)
        except Exception:
            self.log_error("opening the strat in Money Makers")

    def fl_upload_fill(self, st, probs):
        """The strat still misses something the board needs -> Money Makers › Strats › Mine with it picked."""
        self.mm_page.pick("Strats", notify=False)
        self.mm_show_page()
        self.mm_show_mine(st["id"])
        self.app_toast(f"\"{st['name']}\" is saved in Money Makers › Strats › Mine. Before it can go to the community "
                       f"strats it needs: {', '.join(p.replace('missing ', '') for p in probs[:4])}. Fill those in, "
                       "then press 📤 Post to Community.", "Upload a strat", secs=30)

    def fl_all_strats(self):
        """2.85.0: every strat a setup can follow - the bundled and yours, plus Community and Official posts (tracking
        one of those made a "New setup" that lost its link)."""
        out, seen = [], set()
        extra = list(getattr(self, "mm_board", None) or [])
        off = getattr(self, "mm_official", None) or {}
        extra += [dict(x, origin="official") for x in (off.get("strats") or []) if isinstance(x, dict)]
        for x in list(MM.all_strats()) + extra:
            if isinstance(x, dict) and x.get("id") and x["id"] not in seen and x.get("name"):
                seen.add(x["id"])
                out.append(x)
        return out

    def fl_strat_guide(self, s):
        """2.46.0: a setup -> a strat in the standard layout: its strat's text (if it has one), the items it runs
        (with the mods that matter - Money Makers checks their cost every day), the atlas, and its numbers."""
        import json as _json
        base = next((x for x in self.fl_all_strats() if x["id"] == s.get("strat")), None)
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
        st.pop("ledger", None)                              # 2.85.0: only YOUR numbers go up (a followed strat's
        if base is not None and base.get("author") != SETTINGS.get("wealth_account"):   # weren't yours to publish)
            st.pop("est_profit", None)
        from . import board as _B
        st["author"] = (_B.signed_in() or {}).get("name") or st.get("author") or "me"
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
        gd = s.get("guide") or {}                           # 2.78.0: the Publish step's answers win
        for k in ("category", "type", "summary", "thoughts_per_click", "clicks_per_hour", "steps"):
            if gd.get(k):
                st[k] = gd[k]
        tags = list(gd.get("tags") or st.get("tags") or [])
        tags += [t for t in s.get("content") or [] if t not in tags]
        if tags:
            st["tags"] = [t for t in tags if t in MM.all_tags()]
        if ver["atlas"].get("image"):
            st["atlas_image"] = ver["atlas"]["image"]
        if not st.get("patch"):                             # (the game version the guide pack is for)
            from .campaign import pack
            st["patch"] = pack().get("patch") or "?"
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
        win.title("Strat Tracker - compare")
        win.configure(bg=C["panel"])
        win.transient(self.root)
        rows = (("Runs", "runs", lambda f: str(f["runs"]), max),
                ("Avg run", "avg_run", lambda f: _hms(f["avg_run"]) if f["avg_run"] else "-", min),
                ("Cost / run", "cost_run", lambda f: _d(f["cost_run"]), min),
                ("Loot / run", "loot_run", lambda f: _d(f["loot_run"]), max),
                ("Profit / run", "profit_run", lambda f: _d(f["profit_run"], True), max),
                ("Div / hour", "per_hour", lambda f: "-" if f["per_hour"] is None else f"{f['per_hour']:.1f}", max),
                ("Spread", "spread", lambda f: "-" if f["spread"] is None else f"±{f['spread']:.2f}", min))
        ranked = sorted([c for c in cols if c[1]["per_hour"] is not None], key=lambda c: -c[1]["per_hour"])
        if len(ranked) >= 2:                                   # 2.56.0: the answer first, in words
            a_, b_ = ranked[0], ranked[1]
            say = f"{a_[0]} makes {a_[1]['per_hour'] - b_[1]['per_hour']:.1f} div an hour more than {b_[0]}."
            if a_[1]["spread"] is not None and b_[1]["spread"] is not None and b_[1]["spread"] < a_[1]["spread"]:
                say += f" {b_[0]} is steadier: its logs swing less."
        else:
            say = "Log loot on at least two of them to see which makes more."
        self.fl_compare_say = say
        tk.Label(win, text=say, bg=C["panel"], fg="#ffffff", font=("Segoe UI", 12, "bold"), padx=16, pady=8,
                 anchor="w", justify="left", wraplength=640).pack(fill="x", pady=(8, 0))
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
                    self.log_error("starting the Strat Tracker's map counting")
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
        w = OverlayWindow(self.root, f"Strat Tracker · {s['name']}", "✎", geo, opacity=250, on_close=self.fl_box_later,
                          on_moved=moved, lockable=False, min_size=(380, 420), follow_game=not in_app)
        self.fl_box, self.fl_box_p = w, p
        bg, fg, mut = P["bg"], P["text"], P["muted"]
        font = (P["font"], 10)
        # 2.70.0: three short steps - how many runs, the loot, the profit
        st = self.fl_box_steps = Steps(w.body, ("Runs", "Loot", "Profit"),
                                       {"bg": bg, "band": P.get("band", bg), "text": fg, "muted": mut,
                                        "accent": P.get("head", fg)}, on_change=self._fl_box_step, font=P["font"])
        st.bar.pack(fill="x")
        brow = tk.Frame(w.body, bg=bg, padx=12, pady=8)
        brow.pack(fill="x", side="bottom")
        self.fl_box_next = ttk.Button(brow, text="Next ›", style="Primary.TButton", command=self.fl_box_forward,
                                      width=8)
        self.fl_box_next.pack(side="right")
        self.fl_box_back = ttk.Button(brow, text="‹ Back", command=lambda: st.go(st.cur - 1), width=7)
        self.fl_box_back.pack(side="right", padx=(0, 8))
        ttk.Button(brow, text="Later", command=self.fl_box_later, style="Quiet.TButton", width=6).pack(side="left")
        ttk.Button(brow, text="Skip", command=self.fl_box_skip, style="Quiet.TButton", width=6).pack(side="left",
                                                                                                    padx=(8, 0))
        for b_ in brow.winfo_children():
            t_ = b_.cget("text")
            Tooltip(b_, {"Later": "Ask again after your next run", "Skip": "These runs count for time, not money",
                         "Next ›": "Next step (Enter)"}.get(t_, t_))
        st.body.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        f1, f2, f3 = st.frames
        secs = time.time() - p.get("start", time.time())
        # ---- 1: runs
        tk.Label(f1, text="How many runs does this log cover?", bg=bg, fg=fg, font=(P["font"], 12, "bold"),
                 anchor="w").pack(fill="x", pady=(4, 8))
        top = tk.Frame(f1, bg=bg)
        top.pack(fill="x")
        tk.Label(top, text="Runs", bg=bg, fg=fg, font=(P["font"], 11)).pack(side="left")
        self.fl_box_runs = tk.StringVar(value=str(max(1, p.get("runs", 0)) if not p.get("manual") else max(1, p.get("runs", 0) or 1)))
        self.fl_box_runs_box = ttk.Spinbox(top, from_=1, to=999, textvariable=self.fl_box_runs, width=4,
                                           command=self.fl_box_recalc)
        self.fl_box_runs_box.pack(side="left", padx=(8, 8))
        self.fl_box_runs.trace_add("write", lambda *a: self.fl_box_recalc())
        tk.Label(top, text=f"since your last log · {_hms(secs)}", bg=bg, fg=mut, font=font).pack(side="left")
        tk.Label(f1, text=("Counted by itself from the maps you entered - change it if it's off." if not p.get("manual")
                           else "Type how many runs since your last log."), bg=bg, fg=mut, font=(P["font"], 9),
                 anchor="w", justify="left", wraplength=420).pack(fill="x", pady=(12, 0))
        self.fl_box_runs_cost = tk.Label(f1, text="", bg=bg, fg=fg, font=(P["font"], 10), anchor="w")
        self.fl_box_runs_cost.pack(fill="x", pady=(12, 0))
        # ---- 2: loot
        tk.Label(f2, text="What dropped?", bg=bg, fg=fg, font=(P["font"], 12, "bold"), anchor="w").pack(fill="x",
                                                                                                   pady=(4, 2))
        tk.Label(f2, text="Ctrl+Alt+C each drop in game (or a stash full of them), paste, or type \"7 Divine Orb\". "
                          "Each one is priced with poe.ninja.", bg=bg, fg=mut, font=(P["font"], 9), anchor="w",
                 justify="left", wraplength=420).pack(fill="x", pady=(0, 8))
        self.fl_box_text = tk.Text(f2, height=4, bg=P["field"], fg=fg, insertbackground=fg, relief="flat",
                                   highlightthickness=1, highlightbackground=P["line"], font=font, wrap="word")
        self.fl_box_text.pack(fill="x")
        self.fl_box_text.bind("<<Modified>>", self._fl_box_typed)
        self.fl_box_rows = tk.Frame(f2, bg=bg)
        self.fl_box_rows.pack(fill="both", expand=True, pady=(8, 0))
        # ---- 3: profit
        tk.Label(f3, text="This log", bg=bg, fg=fg, font=(P["font"], 12, "bold"), anchor="w").pack(fill="x",
                                                                                              pady=(4, 8))
        sums = tk.Frame(f3, bg=bg)
        sums.pack(fill="x")
        self.fl_box_vars = {}
        for i, (key, label) in enumerate((("loot", "Loot worth"), ("cost", "Cost"), ("profit", "Profit"))):
            tk.Label(sums, text=label, bg=bg, fg=fg, font=(P["font"], 10, "bold" if key == "profit" else "normal"),
                     anchor="w").grid(row=i, column=0, sticky="w", pady=2)
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
        nrow = tk.Frame(f3, bg=bg)
        nrow.pack(fill="x", pady=(12, 0))
        tk.Label(nrow, text="Note", bg=bg, fg=fg, font=font).pack(side="left")
        self.fl_box_note = tk.StringVar()
        ttk.Entry(nrow, textvariable=self.fl_box_note).pack(side="left", fill="x", expand=True, padx=(8, 0))
        w.bind("<Return>", lambda e: None if isinstance(e.widget, tk.Text) else self.fl_box_forward())
        self.fl_box_items, self._fl_box_typing = [], None
        self._fl_box_set = False
        self.fl_box_recalc()
        st.go(0)
        w.show()
        return w

    # 2.70.0: the loot box's steps
    def _fl_box_step(self, i):
        st = self.fl_box_steps
        self.fl_box_back.state(["disabled"] if i == 0 else ["!disabled"])
        self.fl_box_next.config(text="Log it" if st.last() else "Next ›")
        if i == 1:
            self.root.after(30, lambda: self._fl_box_focus(self.fl_box_text))

    def _fl_box_focus(self, w):
        try:
            w.focus_set()
        except tk.TclError:
            pass

    def fl_box_forward(self):
        st = getattr(self, "fl_box_steps", None)
        if st is None or getattr(self, "fl_box", None) is None:
            return None
        if st.last():
            return self.fl_box_log()
        return st.go(st.cur + 1)

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
        st = getattr(self, "fl_box_steps", None)
        if st is not None and st.cur != 1:                   # 2.70.0: show the loot step
            st.go(1)
        self._say("Added to the Strat Tracker's loot: " + ", ".join(f"{q}× {n}" for n, q in drops), 3)

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
        rc = getattr(self, "fl_box_runs_cost", None)
        if rc is not None:                                   # 2.70.0: step 1 shows what those runs cost
            rc.config(text=(f"These {runs} runs cost" if runs != 1 else "This run costs") +
                           f" {cost:.2f} div ({per:.3f} a run, from your setup)")
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
        win.title(f"Strat Tracker - {s['name']}")
        win.configure(bg=P1)
        win.transient(self.root)
        W, H = 960, 640
        try:                                                 # 2.67.0: centered on the app, not the screen's corner
            rx, ry, rw, rh = self.root.winfo_rootx(), self.root.winfo_rooty(), self.root.winfo_width(), self.root.winfo_height()
            win.geometry(f"{W}x{H}+{rx + max(0, (rw - W) // 2)}+{ry + max(0, (rh - H) // 3)}")
        except tk.TclError:
            win.geometry(f"{W}x{H}")
        self.fl_ed, self.fl_ed_s, self.fl_ed_new = win, s, bool(new)
        self.fl_ed_ver = _json.loads(_json.dumps(L.version(s)))           # edited as a copy; Save decides the version
        # 2.70.0: five short steps, the cost of one run always in sight at the right
        # 2.78.0: Atlas & content (what it runs - tags - and a screenshot), and Publish (how people find it)
        st = self.fl_ed_steps = Steps(win, ("Name & strat", "Waystone", "Tablets & more", "Atlas & content",
                                            "Logging", "Publish"),
                                      {"bg": P1, "band": P2, "text": C["text"], "muted": C["muted"],
                                       "accent": C["accent"]}, on_change=self._fl_ed_step)
        st.bar.pack(fill="x")
        nav = tk.Frame(win, bg=P2, padx=16, pady=8)
        nav.pack(fill="x", side="bottom")
        ttk.Button(nav, text="Cancel", style="Quiet.TButton", command=win.destroy).pack(side="left")
        self.fl_ed_next = ttk.Button(nav, text="Next ›", style="Primary.TButton", command=self.fl_ed_forward)
        self.fl_ed_next.pack(side="right")
        self.fl_ed_back = ttk.Button(nav, text="‹ Back", command=lambda: st.go(st.cur - 1))
        self.fl_ed_back.pack(side="right", padx=(0, 8))
        self.fl_ed_save_btn = ttk.Button(nav, text="Save", style="Quiet.TButton", command=self.fl_ed_save)
        if not new:                                          # editing: Save from any step
            self.fl_ed_save_btn.pack(side="right", padx=(0, 16))
        main = tk.Frame(win, bg=P1)
        main.pack(fill="both", expand=True, padx=12, pady=12)
        side_o, side = chrome_section(main, "Cost of one run")
        side_o.pack(side="right", fill="y", padx=(12, 0))
        side_o.configure(width=270)
        side_o.pack_propagate(False)
        self.fl_ed_cost_big = tk.Label(side, text="", bg=P2, fg=C["good"], font=("Segoe UI", 20, "bold"), anchor="w")
        self.fl_ed_cost_big.pack(fill="x")
        tk.Label(side, text="a run, from the items you add", bg=P2, fg=C["muted"], font=("Segoe UI", 9),
                 anchor="w").pack(fill="x", pady=(0, 8))
        self.fl_ed_cost_lbl = tk.Label(side, text="", bg=P2, fg=C["text"], font=(MONO, 9), anchor="nw",
                                       justify="left", wraplength=230)
        self.fl_ed_cost_lbl.pack(fill="both", expand=True)
        st.body.pack(in_=main, side="left", fill="both", expand=True)
        st.body.lift(main)                                   # (made before main: keep it above main's background)
        f1, f2, f3, f4, f5, f6 = st.frames

        def head(f, title, hint):
            o, inner = chrome_section(f, title, hint, wrap=True)
            o.pack(fill="both", expand=True)
            return inner
        # ---- 1: name & strat
        g = head(f1, "Name & strat", "Give the setup a name you'll recognize. Pick the strat it follows, if it "
                                     "follows one - its guide, items and atlas come along when you upload it.")
        r = tk.Frame(g, bg=P2)
        r.pack(fill="x", pady=(0, 8))
        tk.Label(r, text="Name", bg=P2, fg=C["muted"], width=6, anchor="w").pack(side="left")
        self.fl_ed_name = tk.StringVar(value=s["name"])
        self.fl_ed_name_entry = ttk.Entry(r, textvariable=self.fl_ed_name, width=36)
        self.fl_ed_name_entry.pack(side="left", padx=(8, 0))
        r = tk.Frame(g, bg=P2)
        r.pack(fill="x")
        tk.Label(r, text="Strat", bg=P2, fg=C["muted"], width=6, anchor="w").pack(side="left")
        strats = sorted(self.fl_all_strats(), key=lambda x: x["name"].lower())
        self.fl_ed_strats = {"(none - my own idea)": None, **{x["name"]: x["id"] for x in strats}}
        cur = next((n for n, i in self.fl_ed_strats.items() if i == s.get("strat")), "(none - my own idea)")
        self.fl_ed_strat = tk.StringVar(value=cur)
        cb = ttk.Combobox(r, textvariable=self.fl_ed_strat, values=list(self.fl_ed_strats), state="readonly", width=40)
        cb.pack(side="left", padx=(8, 0))
        cb.bind("<<ComboboxSelected>>", lambda e: self.root.after(20, win.focus_set))
        # ---- 2 + 3: the items (Ctrl+Alt+C in game goes to the right step by itself)
        self.fl_ed_cols = {}
        for f, kind, title, hint in ((f2, "waystones", "Waystone", "One copy of the kind of waystone you run - "
                                      "Ctrl+Alt+C it in game. Then pick the numbers that make it work."),
                                     (f3, "tablets", "Tablets & more", "Each tablet (and anything else you use up), "
                                      "and how many runs it lasts. Ctrl+Alt+C each one in game.")):
            g = head(f, title, hint)
            drop = tk.Label(g, text="Ctrl+Alt+C it in game - or click here to paste", bg=P1, fg=C["muted"],
                            font=("Segoe UI", 9), pady=8, cursor="hand2", highlightthickness=1,
                            highlightbackground=C["gold_dim"])
            drop.pack(fill="x", pady=(0, 8))
            drop.bind("<Button-1>", lambda e, k=kind: self.fl_ed_paste(k))
            sa = ScrollArea(g, bg=P2)
            sa.pack(fill="both", expand=True)
            self.fl_ed_cols[kind] = sa.inner
        # ---- 4: atlas & content (2.78.0: what it runs, as tags; the atlas as a screenshot)
        g = head(f4, "Atlas & content", "Tick what this setup runs - the same tags Money Makers filters by. Then "
                                        "the atlas trees and their points, and a screenshot of your atlas.")
        sa = ScrollArea(g, bg=P2)
        sa.pack(fill="both", expand=True)
        a = sa.inner
        self.fl_ed_content = {}
        have = set(s.get("content") or [])
        for group, tags in MM.content_groups().items():
            tk.Label(a, text=group.upper(), bg=P2, fg=C["steel"], font=("Segoe UI", 9, "bold"), anchor="w").pack(
                fill="x", pady=(0, 2))
            box = tk.Frame(a, bg=P2)
            box.pack(fill="x", pady=(0, 8))
            for i, t in enumerate(tags):
                v = tk.BooleanVar(value=t in have)
                ttk.Checkbutton(box, text=t, variable=v, style="Card.TCheckbutton").grid(
                    row=i // 2, column=i % 2, sticky="w", padx=(0, 16), pady=1)
                self.fl_ed_content[t] = v
            for c in range(2):
                box.columnconfigure(c, uniform="ct")
        tk.Label(a, text="ATLAS TREES AND POINTS", bg=P2, fg=C["steel"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x", pady=(4, 2))
        self.fl_ed_trees = tk.Frame(a, bg=P2)
        self.fl_ed_trees.pack(fill="x", pady=(0, 4))
        add = tk.Frame(a, bg=P2)
        add.pack(fill="x")
        self.fl_ed_tree_name = tk.StringVar(value=L.ATLAS_TREES[1])
        ttk.Combobox(add, textvariable=self.fl_ed_tree_name, values=list(L.ATLAS_TREES), width=18).pack(side="left")
        self.fl_ed_tree_pts = tk.StringVar(value="10")
        ttk.Spinbox(add, from_=0, to=400, textvariable=self.fl_ed_tree_pts, width=4).pack(side="left", padx=4)
        tk.Label(add, text="points", bg=P2, fg=C["muted"]).pack(side="left")
        ttk.Button(add, text="Add", command=self.fl_ed_add_tree, style="Quiet.TButton").pack(side="left", padx=(8, 0))
        tk.Label(a, text="YOUR ATLAS", bg=P2, fg=C["steel"], font=("Segoe UI", 9, "bold"), anchor="w").pack(
            fill="x", pady=(16, 2))
        shot = tk.Frame(a, bg=P2)
        shot.pack(fill="x")
        self.fl_ed_shot = tk.Label(shot, text="No screenshot yet", bg=C["panel"], fg=C["muted"], width=28, height=6,
                                   font=("Segoe UI", 9), highlightthickness=1, highlightbackground=C["line"])
        self.fl_ed_shot.pack(side="left")
        sb = tk.Frame(shot, bg=P2)
        sb.pack(side="left", padx=(12, 0), anchor="n")
        tk.Label(sb, text="Screenshot your atlas in game, then", bg=P2, fg=C["muted"], font=("Segoe UI", 9),
                 anchor="w").pack(fill="x")
        self.fl_ed_shot_btns = {}
        for key, text, cmd, style in (("paste", "Paste screenshot (Ctrl+V)", self.fl_ed_shot_paste, "Primary.TButton"),
                                      ("file", "Pick an image file…", self.fl_ed_shot_file, "TButton"),
                                      ("clear", "Remove it", self.fl_ed_shot_clear, "Quiet.TButton")):
            b = ttk.Button(sb, text=text, command=cmd, style=style)
            b.pack(fill="x", pady=(4, 0))
            self.fl_ed_shot_btns[key] = b
        win.bind("<Control-v>", lambda e: self.fl_ed_shot_paste() if self.fl_ed_steps.cur == 3 else None, add="+")
        tk.Label(a, text="Notes (masters, the order you take nodes …)", bg=P2, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(12, 2))
        self.fl_ed_notes = tk.Text(a, height=4, bg=C["panel"], fg=C["text"], insertbackground=C["text"],
                                   relief="flat", font=("Segoe UI", 9), wrap="word")
        self.fl_ed_notes.pack(fill="x")
        self.fl_ed_notes.insert("1.0", self.fl_ed_ver["atlas"].get("notes", ""))
        self.fl_ed_shot_paint()
        # ---- 5: logging
        g = head(f5, "Logging", "When the Strat Tracker asks for your loot, how runs are counted, and what else "
                                "a run costs.")
        er = tk.Frame(g, bg=P2)
        er.pack(fill="x", pady=(0, 8))
        tk.Label(er, text="Ask for the loot every", bg=P2, fg=C["text"]).pack(side="left")
        self.fl_ed_every = tk.StringVar(value=str(s.get("every", L.EVERY)))
        ttk.Spinbox(er, from_=1, to=100, textvariable=self.fl_ed_every, width=4).pack(side="left", padx=4)
        tk.Label(er, text="runs", bg=P2, fg=C["text"]).pack(side="left")
        self.fl_ed_counting = tk.StringVar(value=s.get("counting", "auto"))
        for k, label in L.COUNTING.items():
            ttk.Radiobutton(g, text=label if k == "auto" else f"{label} ({self.fl_key_label()})",
                            variable=self.fl_ed_counting, value=k, style="Card.TRadiobutton").pack(anchor="w", pady=1)
        xr = tk.Frame(g, bg=P2)
        xr.pack(fill="x", pady=(12, 0))
        tk.Label(xr, text="Other costs a run", bg=P2, fg=C["text"]).pack(side="left")
        self.fl_ed_extra = tk.StringVar(value=f"{self.fl_ed_ver.get('extra') or 0:g}")
        ttk.Entry(xr, textvariable=self.fl_ed_extra, width=6).pack(side="left", padx=4)
        tk.Label(xr, text="div", bg=P2, fg=C["text"]).pack(side="left")
        self.fl_ed_extra.trace_add("write", lambda *a: self.fl_ed_cost())
        self._fl_ed_publish_page(head(f6, "Publish", "How people find it in Money Makers. Asked before anything "
                                                     "goes out - steps, loot and tips can be added after, in Mine."))
        win.bind("<Return>", lambda e: None if isinstance(e.widget, tk.Text) else self.fl_ed_forward())
        self.fl_ed_fill()
        st.go(0)
        if new:
            win.after(50, lambda: (self.fl_ed_name_entry.focus_set(), self.fl_ed_name_entry.select_range(0, "end")))
        return win

    # ---------------- 2.78.0: the atlas screenshot
    def fl_ed_shot_paint(self):
        lbl = getattr(self, "fl_ed_shot", None)
        if lbl is None:
            return
        from . import stratimg
        ref = self.fl_ed_ver["atlas"].get("image")
        img = self.strat_thumb(stratimg.path_of(ref), 220, 124) if ref else None
        if img is not None:
            lbl.config(image=img, text="", width=220, height=124)
            lbl.image = img
        else:
            lbl.config(image="", text="No screenshot yet" if not ref else "The screenshot is missing", width=28,
                       height=6)
            lbl.image = None
        self.fl_ed_shot_btns["clear"].pack_configure() if ref else self.fl_ed_shot_btns["clear"].pack_forget()

    def strat_thumb(self, path, w, h):
        """A picture file -> a Tk image that fits w x h (None without it, or without Pillow)."""
        if not path:
            return None
        try:
            from PIL import Image, ImageTk
            im = Image.open(path)
            im.thumbnail((w, h))
            return ImageTk.PhotoImage(im, master=self.root)
        except Exception:
            return None

    def fl_ed_shot_set(self, ref, how):
        if not ref:
            self._say("No picture on the clipboard - take a screenshot (Win+Shift+S, or Print Screen) and press "
                      "Paste again." if how == "paste" else "That file isn't a picture the app can read.", 8)
            return None
        self.fl_ed_ver["atlas"]["image"] = ref
        self.fl_ed_shot_paint()
        return ref

    def fl_ed_shot_paste(self, grab=None):
        from . import stratimg
        return self.fl_ed_shot_set(stratimg.from_clipboard(grab), "paste")

    def fl_ed_shot_file(self, path=None):
        from . import stratimg
        path = path or filedialog.askopenfilename(parent=self.fl_ed, title="Your atlas screenshot",
                                                  filetypes=[("Pictures", "*.png *.jpg *.jpeg *.bmp *.webp")])
        return self.fl_ed_shot_set(stratimg.from_file(path), "file") if path else None

    def fl_ed_shot_clear(self):
        self.fl_ed_ver["atlas"].pop("image", None)
        self.fl_ed_shot_paint()

    # ---------------- 2.78.0: Publish - how people find it (asked before anything goes out)
    def _fl_ed_publish_page(self, g):
        P2 = C["panel2"]
        s = self.fl_ed_s
        base = next((x for x in self.fl_all_strats() if x["id"] == s.get("strat")), None) or {}
        gd = dict(s.get("guide") or {})
        for k in ("category", "type", "summary", "thoughts_per_click", "clicks_per_hour", "tags"):
            if k not in gd and base.get(k):
                gd[k] = base[k]
        sa = ScrollArea(g, bg=P2)
        sa.pack(fill="both", expand=True)
        a = sa.inner
        row = tk.Frame(a, bg=P2)
        row.pack(fill="x", pady=(0, 8))
        tk.Label(row, text="What it is", bg=P2, fg=C["muted"], width=14, anchor="w").pack(side="left")
        self.fl_pub_cat = tk.StringVar(value=gd.get("category", ""))
        self.fl_pub_type = tk.StringVar(value=gd.get("type", ""))
        cb = ttk.Combobox(row, textvariable=self.fl_pub_cat, values=list(MM.CATEGORIES), state="readonly", width=12)
        cb.pack(side="left")
        tk.Label(row, text="›", bg=P2, fg=C["muted"]).pack(side="left", padx=4)
        self.fl_pub_type_box = ttk.Combobox(row, textvariable=self.fl_pub_type, state="readonly", width=20,
                                            values=list(MM.TAXONOMY.get(self.fl_pub_cat.get(), ())))
        self.fl_pub_type_box.pack(side="left")

        def cat_changed(_e=None):
            types = list(MM.TAXONOMY.get(self.fl_pub_cat.get(), ()))
            self.fl_pub_type_box.config(values=types)
            if self.fl_pub_type.get() not in types:
                self.fl_pub_type.set("")
            self.fl_pub_check()
        cb.bind("<<ComboboxSelected>>", cat_changed)
        self.fl_pub_type_box.bind("<<ComboboxSelected>>", lambda e: self.fl_pub_check())
        row = tk.Frame(a, bg=P2)
        row.pack(fill="x", pady=(0, 8))
        tk.Label(row, text="One line", bg=P2, fg=C["muted"], width=14, anchor="w").pack(side="left")
        self.fl_pub_sum = tk.StringVar(value=gd.get("summary", ""))
        ttk.Entry(row, textvariable=self.fl_pub_sum, width=52).pack(side="left", fill="x", expand=True)
        self.fl_pub_sum.trace_add("write", lambda *a: self.fl_pub_check())
        row = tk.Frame(a, bg=P2)
        row.pack(fill="x", pady=(0, 8))
        tk.Label(row, text="Thoughts per click", bg=P2, fg=C["muted"], width=16, anchor="w").pack(side="left")
        words = [w for w, _d in MM.THINKING.values()]
        self.fl_pub_think = SegBar(row, words, value=MM.THINKING.get(gd.get("thoughts_per_click"), ("",))[0],
                                   size=9, pad=(8, 4), command=lambda v: self.fl_pub_check())
        self.fl_pub_think.pack(side="left")
        row = tk.Frame(a, bg=P2)
        row.pack(fill="x", pady=(0, 8))
        tk.Label(row, text="Clicks per hour", bg=P2, fg=C["muted"], width=14, anchor="w").pack(side="left")
        self.fl_pub_clicks = SegBar(row, list(MM.CLICKS), value=gd.get("clicks_per_hour", ""), size=9, pad=(8, 4),
                                    command=lambda v: self.fl_pub_check())
        self.fl_pub_clicks.pack(side="left")
        grid = tk.Frame(a, bg=P2)
        grid.pack(fill="x", pady=(4, 0))
        self.fl_pub_tags = {}
        have = set(gd.get("tags") or [])
        for col, (group, tags) in enumerate(MM.TAG_GROUPS.items()):
            f = tk.Frame(grid, bg=P2)
            f.grid(row=0, column=col, sticky="nw", padx=(0, 12))
            tk.Label(f, text=group.upper(), bg=P2, fg=C["steel"], font=("Segoe UI", 9, "bold"), anchor="w").grid(
                row=0, column=0, columnspan=2, sticky="w")
            per = 6                                          # (a long group - Also uses - in two columns)
            for i, t in enumerate(tags):
                v = tk.BooleanVar(value=t in have)
                ttk.Checkbutton(f, text=t, variable=v, style="Card.TCheckbutton",
                                command=self.fl_pub_check).grid(row=1 + i % per, column=i // per, sticky="w",
                                                                padx=(0, 8))
                self.fl_pub_tags[t] = v
        tk.Label(a, text="STEPS - what you do, one per line", bg=P2, fg=C["steel"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x", pady=(8, 2))
        self.fl_pub_steps = tk.Text(a, height=4, bg=C["panel"], fg=C["text"], insertbackground=C["text"],
                                    relief="flat", font=("Segoe UI", 9), wrap="word")
        self.fl_pub_steps.pack(fill="x")
        self.fl_pub_steps.insert("1.0", "\n".join(gd.get("steps") or base.get("steps") or []))
        self.fl_pub_steps.bind("<KeyRelease>", lambda e: self.fl_pub_check())
        self.fl_pub_ready = tk.Label(a, text="", bg=P2, fg=C["text"], font=("Segoe UI", 9), anchor="w",
                                     justify="left")
        self.fl_pub_ready.pack(fill="x", pady=(8, 0))
        btns = tk.Frame(a, bg=P2)
        btns.pack(fill="x", pady=(8, 0))
        self.fl_pub_btn = ttk.Button(btns, text="📤 Publish to Community", style="Primary.TButton",
                                     command=self.fl_ed_publish)
        self.fl_pub_btn.pack(side="left")
        ttk.Button(btns, text="Keep it in Mine only", command=lambda: self.fl_ed_publish(post=False)).pack(
            side="left", padx=(8, 0))
        self.fl_pub_check()

    def fl_pub_guide(self):
        """What the Publish step holds -> the guide fields (setup["guide"])."""
        words = {w: k for k, (w, _d) in MM.THINKING.items()}
        return {"category": self.fl_pub_cat.get(), "type": self.fl_pub_type.get(),
                "summary": self.fl_pub_sum.get().strip(), "thoughts_per_click": words.get(self.fl_pub_think.get()),
                "clicks_per_hour": self.fl_pub_clicks.get() or None,
                "tags": [t for t, v in self.fl_pub_tags.items() if v.get()],
                "steps": [l.strip() for l in self.fl_pub_steps.get("1.0", "end-1c").splitlines() if l.strip()]}

    def fl_pub_missing(self, gd=None):
        gd = self.fl_pub_guide() if gd is None else gd
        out = []
        if not gd.get("category") or not gd.get("type"):
            out.append("what it is")
        if not gd.get("summary"):
            out.append("one line")
        if not gd.get("thoughts_per_click"):
            out.append("Thoughts per click")
        if not gd.get("clicks_per_hour"):
            out.append("Clicks per hour")
        if not gd.get("steps"):
            out.append("steps")
        return out

    def fl_pub_check(self):
        lbl = getattr(self, "fl_pub_ready", None)
        if lbl is None:
            return
        gd = self.fl_pub_guide()
        miss = self.fl_pub_missing(gd)
        content = [t for t, v in getattr(self, "fl_ed_content", {}).items() if v.get()]
        lines = [("✓" if not {"what it is", "one line"} & set(miss) else "○") + "  What it is, one line",
                 ("✓" if not {"Thoughts per click", "Clicks per hour"} & set(miss) else "○") + "  Thoughts per click, clicks",
                 ("✓" if "steps" not in miss else "○") + "  Steps",
                 f"{'✓' if gd['tags'] or content else '○'}  {len(gd['tags'])} tags, {len(content)} content (step 4)",
                 f"{'✓' if self.fl_ed_ver['atlas'].get('image') else '○'}  Atlas screenshot (optional)"]
        lbl.config(text="\n".join(lines) + ("" if not miss else "\n\nStill needed: " + ", ".join(miss)))
        try:
            self.fl_pub_btn.state(["disabled"] if miss else ["!disabled"])
        except (AttributeError, tk.TclError):
            pass

    def fl_ed_publish(self, post=True):
        """The Publish step's buttons: save the setup (with its guide), then post it - or keep it in Mine."""
        if post and self.fl_pub_missing():
            self._say("Still needed: " + ", ".join(self.fl_pub_missing()), 6)
            return None
        s = self.fl_ed_s
        self.fl_ed_save()
        if not post:
            st = self.fl_keep_mine(s)
            self._say(f"\"{st['name']}\" is kept in Money Makers › Mine.", 6)
            return "mine"
        return self.fl_upload()

    # 2.70.0: the steps
    def _fl_ed_step(self, i):
        st = self.fl_ed_steps
        self.fl_ed_back.state(["disabled"] if i == 0 else ["!disabled"])
        self.fl_ed_next.config(text="Save" if st.last() else "Next ›")

    def fl_ed_forward(self):
        st = getattr(self, "fl_ed_steps", None)
        if st is None:
            return None
        if st.cur == 0 and not self.fl_ed_name.get().strip():
            self._say("Give the setup a name first.", 5)
            return None
        if st.last():
            return self.fl_ed_save()
        return st.go(st.cur + 1)

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
                        wraplength=480)
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
        if (e.get("key_mods") or kind == "waystones") and kind != "others":        # 2.67.0: search for more of it, on the site or in your stash
            lr = tk.Frame(card, bg=P1)
            lr.pack(fill="x", pady=(2, 0))
            for text, fn, tip in (("🔗 Trade search", self.fl_open_search,
                                   "Opens the trade site: this base with the mods that matter"
                                   + (", 10+ uses remaining" if kind == "tablets" else "")),
                                  ("⧉ Copy regex", self.fl_copy_regex,
                                   "Copies a stash search for the mods that matter (paste it in your stash)")):
                lb = tk.Label(lr, text=text, bg=P1, fg=C["blue"], cursor="hand2", font=("Segoe UI", 9, "underline"))
                lb.pack(side="left", padx=(0, 12))
                lb.bind("<Button-1>", lambda ev, f=fn: f(e))
                Tooltip(lb, tip)

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
        lines = [f"Cost of one run: {per:.3f}d"] + [f"{lab}: {v:.3f}" for lab, v in parts]
        if unknown:
            lines.append(f"\n{unknown} item(s) still without a price - type it on the item")
        self.fl_ed_cost_lbl.config(text="\n".join(lines[1:]) or "Add your waystone and tablets - their part of "
                                                                 "a run shows here.")
        self.fl_ed_cost_lbl.full = "\n".join(lines)
        big = getattr(self, "fl_ed_cost_big", None)
        if big is not None:
            big.config(text=f"{per:.3f} div")

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
        if k == "waystones":                                 # 2.67.3: a waystone's value is its endgame numbers
            from . import waystone as WS                     # (the trade site's Endgame Filters), not its mods
            wi = WS.parse_waystone(text)
            props = [m for m in (wi or {}).get("mods", []) if m.get("endgame") and m.get("value")]
            e["props"] = [{"shown": m["shown"], "fid": m["sid"].split(":", 1)[1], "value": m["value"]} for m in props]
            e["mods"] = [p["shown"] for p in e["props"]]
            e["key_mods"] = []
        self.fl_ed_ver[k].append(e)
        st = getattr(self, "fl_ed_steps", None)
        if st is not None:                                   # 2.70.0: show it where it landed
            st.go(1 if k == "waystones" else 2)
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
        every day). 2.67.0: one at a time, centered on the app (several copied items wait their turn instead of
        piling up in the screen's corner)."""
        if not e.get("mods"):
            return None
        cur = getattr(self, "fl_km_win", None)
        try:
            busy = cur is not None and cur.winfo_exists()
        except tk.TclError:
            busy = False
        if busy:
            q = self.__dict__.setdefault("fl_km_queue", [])
            if e not in q:
                q.append(e)
            return None
        win = tk.Toplevel(self.root)
        win.title("The mods that matter")
        win.configure(bg=C["panel"])
        win.transient(self.fl_ed if self.fl_ed_open() else self.root)     # (2.67.3: over the setup window)
        f = tk.Frame(win, bg=C["panel"], padx=16, pady=12)
        f.pack(fill="both", expand=True)
        way = bool(e.get("props"))
        tk.Label(f, text=f"{e['name']}: which {'numbers' if way else 'mods'} make this setup work?", bg=C["panel"],
                 fg=C["accent"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(f, text="Tick the ones you'd pay for (pack size, rarity, +1 Breach …). They're shown on the setup and "
                         "used to check what it costs.", bg=C["panel"], fg=C["muted"], font=("Segoe UI", 9),
                 wraplength=420, justify="left", anchor="w").pack(fill="x", pady=(2, 8))
        vars_ = []
        for m in e["mods"]:
            v = tk.BooleanVar(value=m in (e.get("key_mods") or []))
            ttk.Checkbutton(f, text=m, variable=v).pack(anchor="w")
            vars_.append((m, v))

        def nxt():
            q = getattr(self, "fl_km_queue", [])
            if q:
                self.root.after(50, lambda: self.fl_key_mods(q.pop(0)))
            elif self.fl_ed_open():                          # 2.67.3: the setup window stays in front
                try:
                    self.fl_ed.deiconify()
                    self.fl_ed.lift()
                    self.fl_ed.focus_force()
                except tk.TclError:
                    pass

        def close():
            win.destroy()
            nxt()

        def ok():
            e["key_mods"] = [m for m, v in vars_ if v.get()]
            win.destroy()
            if self.fl_ed_open():
                self.fl_ed_fill()
            nxt()
        b = tk.Frame(f, bg=C["panel"])
        b.pack(fill="x", pady=(12, 0))
        ttk.Button(b, text="Done", style="Primary.TButton", command=ok).pack(side="right")
        ttk.Button(b, text="Skip", style="Quiet.TButton", command=close).pack(side="right", padx=(0, 8))
        win.protocol("WM_DELETE_WINDOW", close)
        self.fl_km_win, self.fl_km_vars, self.fl_km_ok = win, vars_, ok
        self._fl_center(win)
        return win

    def _fl_center(self, win):
        """Put a small window in the middle of the app (or of the Strat Tracker's setup window, when it's open)."""
        try:
            win.update_idletasks()
            host = self.fl_ed if self.fl_ed_open() else self.root
            hx, hy, hw, hh = host.winfo_rootx(), host.winfo_rooty(), host.winfo_width(), host.winfo_height()
            ww, wh = win.winfo_reqwidth(), win.winfo_reqheight()
            win.geometry(f"+{hx + max(0, (hw - ww) // 2)}+{hy + max(0, (hh - wh) // 3)}")
            win.lift()
            win.focus_force()
        except tk.TclError:
            pass

    # ---------------- 2.67.0: a trade search and a stash regex for the mods that matter
    def fl_entry_search(self, e):
        """-> (trade site URL or None, stash-search regex or "") for a setup item: its base, the mods you ticked as
        mattering, and (tablets) at least 10 uses remaining."""
        import json as _json
        from urllib.parse import quote
        from . import regex as RX
        from .mods import find_stat
        from .trade import uses_stat_id
        keys = [m for m in (e.get("key_mods") or []) if "uses remaining" not in m.lower()]
        tablet = "tablet" in str(e.get("cls") or "").lower() or str(e.get("base") or "").endswith("Tablet")
        if e.get("props") is not None:                       # a waystone: its tier and the endgame numbers ticked
            return self._fl_waystone_search(e, keys)
        url = None
        table = getattr(getattr(self, "engine", None), "table", None)
        if table:
            flt = []
            for t in keys:
                try:
                    sid = find_stat(t, (), table)[0]
                except Exception:
                    sid = None
                if sid:
                    flt.append({"id": sid})
            if tablet:
                us = uses_stat_id(table)
                if us:
                    flt.append({"id": us, "value": {"min": 10}})
            q = {"query": {"status": {"option": listing_rules()[0]}, "type": e.get("base") or e.get("name"),
                           "stats": [{"type": "and", "filters": flt}]}, "sort": {"price": "asc"}}
            league = SETTINGS.get("league") or "Standard"
            url = (f"https://www.pathofexile.com/trade2/search/poe2/{quote(league)}"
                   f"?q={quote(_json.dumps(q, separators=(',', ':')))}")
        kind = "tablet" if tablet else "waystone" if "waystone" in str(e.get("cls") or "").lower() else None
        rx = ""
        if kind:
            ids = []
            for t in keys:
                for i in RX.matching_mods(kind, t):
                    if i not in ids:
                        ids.append(i)
            opts = {}
            if tablet:
                opts["uses"] = 10
                first = str(e.get("base") or "").split(" ")[0]
                if first in RX.TABLET_TYPES:
                    opts["types"] = [first]
            rx, _notes = RX.build(kind, [(i, None) for i in ids], [], want_all=True, options=opts)
        return url, rx

    REGEX_PROPS = {"map_iir": "item_rarity", "map_bonus": "drop_chance", "map_packsize": "pack_size",
                   "map_rare_monsters": "monster_rarity", "map_magic_monsters": "effectiveness"}

    def _fl_waystone_search(self, e, keys):
        """A waystone: the trade site's Endgame Filters (its tier, and each number you ticked at your value or more),
        and the stash search for the same."""
        import json as _json
        from urllib.parse import quote
        from . import regex as RX
        picked = [p for p in e.get("props") or [] if p["shown"] in keys]
        tier = e.get("tier")
        mp = {"map_tier": {"min": tier, "max": tier}} if tier else {}
        for p in picked:
            mp[p["fid"]] = {"min": p["value"]}
        q = {"query": {"status": {"option": listing_rules()[0]}, "stats": [{"type": "and", "filters": []}],
                       "filters": {"map_filters": {"filters": mp}}}, "sort": {"price": "asc"}}
        league = SETTINGS.get("league") or "Standard"
        url = (f"https://www.pathofexile.com/trade2/search/poe2/{quote(league)}"
               f"?q={quote(_json.dumps(q, separators=(',', ':')))}")
        opts = {"tier_min": tier, "tier_max": tier} if tier else {}
        for p in picked:
            if p["fid"] in self.REGEX_PROPS:
                opts[self.REGEX_PROPS[p["fid"]]] = int(p["value"])
        rx, _notes = RX.build("waystone", [], [], options=opts)
        return url, rx

    def fl_open_search(self, e):
        url, _rx = self.fl_entry_search(e)
        if not url:
            return self._say("The trade site's mod list isn't loaded yet - try again in a moment.", 6)
        import webbrowser
        webbrowser.open(url)

    def fl_copy_regex(self, e):
        _url, rx = self.fl_entry_search(e)
        if not rx:
            return self._say("No stash search for these mods.", 6)
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(rx)
            self.last_clip = self.own_clip = rx
        except tk.TclError:
            pass
        self._say(f"Copied the stash search: {rx}", 8)

    def fl_ed_save(self):
        d, s = self.fl_data(), self.fl_ed_s
        ver = self.fl_ed_ver
        ver["atlas"]["notes"] = self.fl_ed_notes.get("1.0", "end-1c").strip()
        s["content"] = [t for t, v in self.fl_ed_content.items() if v.get()]           # 2.78.0
        s["guide"] = {k: v for k, v in self.fl_pub_guide().items() if v not in (None, "", [])}
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
