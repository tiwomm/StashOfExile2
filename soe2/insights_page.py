"""Top value (2.1.0, a Labs tool): the most valuable things the app has seen, per kind of item - your own priced items
(Price checks), the mods worth the most (what the Mod book learned from listings) and the dearest listings it looked
at on the trade site. Nothing is searched for this window: it only shows what earlier price checks found."""
import re
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from .market import MARKET
from .mods import impact_key, JEWEL_BASE, norm, SIDTEXT
from .pricefmt import fmt_div
from .style import C, FONT_TITLE, SegBar

KINDS = ["Tablets", "Waystones", "Jewels", "Relics"]


def kind_of(base, cls=""):
    b, c = str(base or ""), str(cls or "").lower()
    if b.endswith("Tablet") or "tablet" in c:
        return "Tablets"
    if b.startswith("Waystone") or "waystone" in c:
        return "Waystones"
    if JEWEL_BASE.search(b) or c.startswith("jewel"):
        return "Jewels"
    if "Relic" in b or "relic" in c:
        return "Relics"
    return None


def _mod_text(sid):
    t = SIDTEXT.get(sid, sid)
    return re.sub(r"\s+(found )?in map$", "", t)


class InsightsPage:
    """Mixed into App."""

    def build_insights_window(self, body):
        P1, P2 = C["panel"], C["panel2"]
        top = tk.Frame(body, bg=P1, padx=12, pady=10)
        top.pack(fill="x")
        tk.Label(top, text="Top value", bg=P1, fg=C["text"], font=(FONT_TITLE, 16, "bold")).pack(side="left")
        self.ins_kind = SegBar(top, KINDS, command=lambda v: self.refresh_insights(), size=9, pad=(12, 4))
        self.ins_kind.pack(side="left", padx=16)
        ttk.Button(top, text="Refresh", command=self.refresh_insights).pack(side="right")
        tk.Label(body, text="The most valuable things your price checks have found so far. The more you price, the "
                            "more this fills in. Nothing is searched for this page.", bg=P1, fg=C["muted"],
                 anchor="w", padx=12, font=("Segoe UI", 9)).pack(fill="x")
        grid = tk.Frame(body, bg=P1)
        grid.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        grid.columnconfigure(0, weight=1, uniform="g")
        grid.columnconfigure(1, weight=1, uniform="g")
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)
        self.ins_tables = {}

        def table(r, c, key, title, hint, cols, colspan=1):
            f = tk.Frame(grid, bg=P2, padx=10, pady=8, highlightthickness=1, highlightbackground=C["line"])
            f.grid(row=r, column=c, columnspan=colspan, sticky="nsew", padx=4, pady=4)
            tk.Label(f, text=title, bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
            tk.Label(f, text=hint, bg=P2, fg=C["muted"], font=("Segoe UI", 8), anchor="w", justify="left").pack(fill="x")
            box = tk.Frame(f, bg=P2)
            box.pack(fill="both", expand=True, pady=(4, 0))
            tv = ttk.Treeview(box, columns=[k for k, *_ in cols], show="headings", height=5, selectmode="browse")
            for cid, t, w, a in cols:
                tv.heading(cid, text=t)
                tv.column(cid, width=w, anchor=a, stretch=(cid in ("name", "mod", "mods")))
            sb = ttk.Scrollbar(box, orient="vertical", command=tv.yview)
            tv.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            tv.pack(fill="both", expand=True)
            tv.tag_configure("star", foreground="#ffd9a8")
            empty = tk.Label(box, text="", bg=C["panel"], fg=C["muted"], font=("Segoe UI", 9), justify="center")
            self.ins_tables[key] = (tv, empty)
            return tv
        mine = table(0, 0, "mine", "Your most valuable", "From your Price checks list. Double-click to open it there.",
                     (("name", "Item", 160, "w"), ("base", "Type", 110, "w"), ("est", "Worth", 70, "e"),
                      ("status", "Status", 70, "w")))
        mine.bind("<Double-1>", lambda e: self.ins_open_record())
        table(0, 1, "mods", "Mods worth the most", "What the Mod book learned: the typical asking price of listings "
                                                    "with this mod. ★ = valuable in your Mod book.",
              (("mod", "Mod", 220, "w"), ("base", "On", 90, "w"), ("med", "Typical", 70, "e"), ("n", "Seen", 45, "e")))
        table(1, 0, "seen", "Dearest listings seen", "The most expensive listings your price checks came across on the "
                                                     "trade site (this league).",
              (("price", "Price", 70, "e"), ("base", "Type", 110, "w"), ("mods", "Mods", 260, "w"),
               ("when", "Seen", 70, "w")), colspan=2)
        self.ins_rowmap = {}
        self.refresh_insights()

    def refresh_insights(self):
        if not hasattr(self, "ins_tables"):
            return
        kind = self.ins_kind.get()
        # ---- your own priced items
        tv, empty = self.ins_tables["mine"]
        tv.delete(*tv.get_children())
        self.ins_rowmap = {}
        recs = [r for r in self.records.values()
                if kind_of(r["item"].get("base"), r["item"].get("class")) == kind and r.get("est") is not None
                and not r.get("skip")]
        recs.sort(key=lambda r: -r["est"])
        for r in recs[:50]:
            iid = tv.insert("", "end", values=(r["item"]["name"], r["item"]["base"], fmt_div(r["est"]),
                                               {"listed": "listed", "removed": "removed"}.get(r.get("mark"), "")))
            self.ins_rowmap[iid] = r["id"]
        self._ins_empty(empty, not recs, f"No priced {kind.lower()} yet.\nPrice some with Ctrl+Alt+C.")
        # ---- mods worth the most (the Mod book's data)
        tv, empty = self.ins_tables["mods"]
        tv.delete(*tv.get_children())
        stats = MARKET.cached_stats() if kind != "Waystones" else {}
        rows = [(base, sid, st) for (base, sid), st in stats.items()
                if kind_of(base) == kind and st.get("n", 0) >= 3 and st.get("med") is not None]
        rows.sort(key=lambda r: -r[2]["med"])
        for base, sid, st in rows[:50]:
            text = _mod_text(sid)
            star = impact_key(norm(text)) == "high"
            tv.insert("", "end", values=(("★ " if star else "") + text[:1].upper() + text[1:], base.replace(" Tablet", ""),
                                         fmt_div(st["med"]), st["n"]), tags=("star",) if star else ())
        why = ("Waystones are priced on their numbers (drop chance, pack size ...), not their mods." if kind == "Waystones"
               else "Relics aren't price-checked yet." if kind == "Relics"
               else f"Nothing learned about {kind[:-1].lower()} mods yet.\nIt fills in as you price {kind.lower()}.")
        self._ins_empty(empty, not rows, why)
        # ---- dearest listings seen
        tv, empty = self.ins_tables["seen"]
        tv.delete(*tv.get_children())
        seen = [x for x in MARKET.top_listings() if kind_of(x[0]) == kind][:50]
        now = time.time()
        for base, ts, price, sids in seen:
            mods = "  ·  ".join(_mod_text(s)[:40] for s in sids[:4]) + (" …" if len(sids) > 4 else "")
            age = now - (ts or now)
            when = "today" if age < 86400 else datetime.fromtimestamp(ts).strftime("%b %d")
            tv.insert("", "end", values=(fmt_div(price), base, mods, when))
        self._ins_empty(empty, not seen, "Nothing seen yet." if kind != "Relics" else "Relics aren't price-checked yet.")

    @staticmethod
    def _ins_empty(lbl, show, text):
        if show:
            lbl.config(text=text)
            lbl.place(relx=0.5, rely=0.5, anchor="center")
        else:
            lbl.place_forget()

    def ins_open_record(self):
        tv = self.ins_tables["mine"][0]
        sel = tv.selection()
        rid = self.ins_rowmap.get(sel[0]) if sel else None
        if rid is None or rid not in self.records:
            return
        self.shell.open("checks")
        if not self.tree.exists(str(rid)):
            self.cat_reset()
            if hasattr(self, "view_var"):
                from .config import SETTINGS
                SETTINGS["view"] = "All"
                self.view_var.set("All")
            self.rebuild_tree()
        if self.tree.exists(str(rid)):
            self.tree.selection_set(str(rid))
            self.tree.see(str(rid))
            self.on_select()
