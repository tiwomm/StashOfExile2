"""Top value (2.1.0, a Labs tool): the most valuable things the app has seen, per kind of item - your own priced items
(Price checks), the mods worth the most (what the Mod book learned from listings) and the dearest listings it looked
at on the trade site. Nothing is searched for this window: it only shows what earlier price checks found."""
import re
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from .config import SETTINGS
from .market import MARKET
from .valuelog import VALUE_LOG, sig_of
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
        tk.Label(body, text="The most valuable things your price checks have found so far - kept even after you clear "
                            "the Price checks list. The more you price, the more this fills in. Nothing is searched "
                            "for this page.", bg=P1, fg=C["muted"], anchor="w", padx=12, font=("Segoe UI", 9),
                 justify="left", wraplength=760).pack(fill="x")
        # 2.4.0: details of the row you pick (bottom)
        det = tk.Frame(body, bg=P2, padx=12, pady=8, highlightthickness=1, highlightbackground=C["line"])
        det.pack(side="bottom", fill="x", padx=14, pady=(0, 10))
        dbar = tk.Frame(det, bg=P2)
        dbar.pack(side="right", anchor="n")
        self.ins_det_btns = {
            "open": ttk.Button(dbar, text="Show in Price checks", command=self.ins_open_record),
            "again": ttk.Button(dbar, text="Price it again", command=self.ins_price_again),
            "trade": ttk.Button(dbar, text="Open the search", command=self.ins_open_search)}
        self.undo_button(dbar, "insights").pack(side="bottom", pady=(6, 0))
        self.ins_det = tk.Label(det, text="Pick a row to see its details.", bg=P2, fg=C["muted"], anchor="nw",
                                justify="left", font=("Segoe UI", 9))
        self.ins_det.pack(side="left", fill="both", expand=True)
        self.ins_det.bind("<Configure>", lambda e: self.ins_det.config(wraplength=max(300, e.width - 10)))
        self.ins_pick = None
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
            tv = ttk.Treeview(box, columns=[k for k, *_ in cols], show="headings", height=5)
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
            tv.bind("<<TreeviewSelect>>", lambda e, k=key: self.ins_show(k))
            return tv
        mine = table(0, 0, "mine", "Your most valuable", "Everything you've priced (this league). Delete removes rows "
                                                         "from here only; Ctrl+Z undoes.",
                     (("name", "Item", 160, "w"), ("base", "Type", 110, "w"), ("est", "Worth", 70, "e"),
                      ("status", "Status", 70, "w")))
        mine.bind("<Double-1>", lambda e: self.ins_open_record())
        self.list_register("insights", mine, delete=self.ins_forget)
        table(0, 1, "mods", "Mods worth the most", "What the Mod book learned: the typical asking price of listings "
                                                    "with this mod. ★ = valuable in your Mod book.",
              (("mod", "Mod", 220, "w"), ("base", "On", 90, "w"), ("med", "Typical", 70, "e"), ("n", "Seen", 45, "e")))
        table(1, 0, "seen", "Dearest listings seen", "The most expensive listings your price checks came across on the "
                                                     "trade site (this league).",
              (("price", "Asking", 90, "e"), ("name", "Item", 200, "w"), ("mods", "Mods", 360, "w"),
               ("when", "Seen", 70, "w")), colspan=2)
        self.list_register("insights", self.ins_tables["seen"][0])
        self.list_register("insights", self.ins_tables["mods"][0])
        self.ins_rowmap, self.ins_seenmap = {}, {}
        self.refresh_insights()

    def refresh_insights(self):
        if not hasattr(self, "ins_tables"):
            return
        kind = self.ins_kind.get()
        # ---- your own priced items
        tv, empty = self.ins_tables["mine"]
        tv.delete(*tv.get_children())
        self.ins_rowmap = {}
        league = SETTINGS.get("league")
        added = False
        for r in self.records.values():                      # (what's in Price checks now goes in the log too)
            if r.get("state") == "done" and r.get("est") is not None and sig_of(r.get("raw")) not in VALUE_LOG.items:
                added = VALUE_LOG.add(r, league) or added
        if added:
            VALUE_LOG.save()
        recs = VALUE_LOG.top(league, kind_of, kind)
        for e in recs:
            iid = tv.insert("", "end", values=(e["name"], e["base"], fmt_div(e["est"]),
                                               {"listed": "listed", "removed": "removed"}.get(e.get("mark"), "")))
            self.ins_rowmap[iid] = e
        self._ins_empty(empty, not recs, f"No priced {kind.lower()} yet.\nPrice some with Ctrl+Alt+C.")
        # ---- mods worth the most (the Mod book's data)
        tv, empty = self.ins_tables["mods"]
        tv.delete(*tv.get_children())
        if kind in ("Waystones", "Relics"):                 # 2.6.0: your ★ rules for these (nothing is learned)
            self._ins_rated_mods(tv, empty, kind)
            return self._ins_fill_seen(kind)
        stats = MARKET.cached_stats()
        rows = [(base, sid, st) for (base, sid), st in stats.items()
                if kind_of(base) == kind and st.get("n", 0) >= 3 and st.get("med") is not None]
        rows.sort(key=lambda r: -r[2]["med"])
        for base, sid, st in rows[:50]:
            text = _mod_text(sid)
            star = impact_key(norm(text)) == "high"
            tv.insert("", "end", values=(("★ " if star else "") + text[:1].upper() + text[1:], base.replace(" Tablet", ""),
                                         fmt_div(st["med"]), st["n"]), tags=("star",) if star else ())
        why = f"Nothing learned about {kind[:-1].lower()} mods yet.\nIt fills in as you price {kind.lower()}."
        self._ins_empty(empty, not rows, why)
        self._ins_fill_seen(kind)

    def _ins_rated_mods(self, tv, empty, kind):
        """Waystones / Relics: the mods you rate ★ in the Mod book, and the best one you've priced with each."""
        from . import regex as R
        from .mods import impact_key, rule_key
        cat = "waystone" if kind == "Waystones" else "relic"
        league = SETTINGS.get("league")
        priced = VALUE_LOG.top(league, kind_of, kind, limit=3000)
        have = [({norm(t) for t in e.get("mods") or []}, e) for e in priced]
        rows = []
        for m in R.mods(cat):
            lines = m.get("lines") or [m["line"]]
            keys = [norm(l) for l in lines]
            if not any(impact_key(rule_key(cat, k)) == "high" for k in keys):
                continue
            with_it = [e for ks, e in have if any(k in ks for k in keys)]
            best = max((e["est"] for e in with_it if e.get("est") is not None), default=None)
            text = " / ".join(l[:1].upper() + l[1:] for l in lines)
            rows.append((best if best is not None else -1, text, len(with_it), best))
        rows.sort(key=lambda r: (-r[0], r[1]))
        for _o, text, n, best in rows:
            tv.insert("", "end", values=("★ " + text, kind[:-1], fmt_div(best) if best is not None else "-",
                                         n or "-"), tags=("star",))
        self._ins_empty(empty, not rows, f"No ★ {kind[:-1].lower()} mods yet.\nRate them in Mod book > "
                                         f"{kind[:-1]} rules,\nor right-click a mod in Regex.")

    def _ins_fill_seen(self, kind):
        # ---- dearest listings seen
        tv, empty = self.ins_tables["seen"]
        tv.delete(*tv.get_children())
        seen = [x for x in MARKET.top_listings(detail=True) if kind_of(x["base"]) == kind][:50]
        now = time.time()
        self.ins_seenmap = {}
        for x in seen:
            mods = "  ·  ".join(l[:48] for l in self.ins_listing_mods(x)[:4]) or "(mods weren't saved for this one)"
            ts = x["seen"]
            age = now - (ts or now)
            when = "today" if age < 86400 else datetime.fromtimestamp(ts).strftime("%b %d")
            name = x["name"] or x["base"]
            iid = tv.insert("", "end", values=(x["price"] or fmt_div(x["div"]), name, mods, when))
            self.ins_seenmap[iid] = x
        self._ins_empty(empty, not seen, "Nothing seen yet." if kind != "Relics" else "Relics aren't price-checked yet.")

    @staticmethod
    def ins_listing_mods(x):
        """A listing's mods as the trade site wrote them; older rows only kept the stat ids (and the first number)."""
        if x.get("lines"):
            return [l for l in x["lines"] if l.strip()]
        out = []
        for sid in x.get("sids") or []:
            t = _mod_text(sid)
            v = (x.get("vals") or {}).get(sid)
            if v is not None and "#" in t:
                t = t.replace("#", f"{v:g}", 1)
            out.append(t[:1].upper() + t[1:])
        return out

    def ins_show(self, key):
        """Details of the row picked in one of the lists."""
        tv = self.ins_tables[key][0]
        sel = tv.selection()
        for k, (other, _e) in self.ins_tables.items():      # one list at a time
            if k != key and other.selection():
                other.selection_remove(*other.selection())
        for b in self.ins_det_btns.values():
            b.pack_forget()
        if not sel:
            return
        if key == "mine":
            e = self.ins_rowmap.get(sel[0])
            if not e:
                return
            self.ins_pick = ("mine", e)
            here = any(sig_of(r.get("raw")) == e["sig"] for r in self.records.values())
            when = datetime.fromtimestamp(e["ts"]).strftime("%b %d %H:%M")
            mods = "\n".join("  " + m for m in e.get("mods") or [])
            txt = (f"{e['name']}  ({e['base']})  -  worth about {fmt_div(e['est'])}"
                   + (f", {e['conf']} confidence" if e.get("conf") and e["conf"] != "-" else "") + f"\nPriced {when}"
                   + ("" if here else " · no longer in your Price checks list") + (f"\n{mods}" if mods else ""))
            self.ins_det.config(text=txt, fg=C["text"])
            (self.ins_det_btns["open"] if here else self.ins_det_btns["again"]).pack(fill="x")
        elif key == "seen":
            x = self.ins_seenmap.get(sel[0])
            if not x:
                return
            self.ins_pick = ("seen", x)
            when = datetime.fromtimestamp(x["seen"]).strftime("%b %d %H:%M") if x.get("seen") else "?"
            mods = "\n".join("  " + m for m in self.ins_listing_mods(x)) or "  (mods weren't saved for this one)"
            txt = (f"{x['name'] or x['base']}  -  asking {x['price'] or fmt_div(x['div'])} (≈ {fmt_div(x['div'])})"
                   f"\nSeen {when} while pricing a {x['base']}\n{mods}")
            self.ins_det.config(text=txt, fg=C["text"])
            if x.get("qid"):
                self.ins_det_btns["trade"].pack(fill="x")
        else:
            self.ins_pick = None
            vals = tv.item(sel[0], "values")
            if self.ins_kind.get() in ("Waystones", "Relics"):
                self.ins_det.config(fg=C["text"], text=(
                    f"{vals[0]}  - rated valuable in your Mod book. "
                    + (f"You've priced {vals[3]} with it; the best was worth {vals[2]}." if vals[3] != "-" else
                       "None priced with it yet.")))
            else:
                self.ins_det.config(text=f"{vals[0]}  on {vals[1]}: listings with this mod typically ask {vals[2]} "
                                         f"({vals[3]} seen).", fg=C["text"])

    def ins_forget(self, rows):
        """Delete in Your most valuable: forget those items here (not in Price checks)."""
        sigs = [self.ins_rowmap[r]["sig"] for r in rows if r in self.ins_rowmap]
        gone = VALUE_LOG.remove(sigs)
        if not gone:
            return
        VALUE_LOG.save()
        label = f"{len(gone)} item{'s' if len(gone) != 1 else ''}"

        def restore():
            VALUE_LOG.restore(gone)
            VALUE_LOG.save()
            self.refresh_insights()
        self.push_undo("insights", label, restore)
        self._say(f"Removed {label} from Top value. Ctrl+Z (or Undo) puts them back.", 8)
        self.refresh_insights()

    def ins_price_again(self):
        if not self.ins_pick or self.ins_pick[0] != "mine":
            return
        raw = self.ins_pick[1].get("raw")
        if not raw:
            return
        old = SETTINGS.get("listen", True)
        SETTINGS["listen"] = True
        try:
            self.accept_clip(raw)
        finally:
            SETTINGS["listen"] = old
        self.shell.open("checks")

    def ins_open_search(self):
        if not self.ins_pick or self.ins_pick[0] != "seen" or not self.ins_pick[1].get("qid"):
            return
        import webbrowser
        from .wealth import wealth_trade_url
        webbrowser.open(wealth_trade_url(SETTINGS.get("league", ""), self.ins_pick[1]["qid"]))

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
        e = self.ins_rowmap.get(sel[0]) if sel else None
        rid = next((r["id"] for r in self.records.values() if e and sig_of(r.get("raw")) == e["sig"]), None)
        if rid is None:
            return self.ins_price_again() if e else None
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
