"""The Item library page (1.38): browse base types by class and base group, search modifier stats, and paste a copied
item to see how the app reads it (class, base, group, defences, sockets, each mod's trade stat)."""
import tkinter as tk
from tkinter import ttk

from . import gamedata
from .clipboard import read_clipboard_text
from .style import C, MONO
from .config import PAGE_CHECKS
from .pricefmt import fmt_div

DEF_SHORT = {"ar": "AR", "ev": "EV", "es": "ES"}


class LibraryPage:
    """Mixed into App."""

    def build_library_page(self, tab):
        lab = dict(bg=C["panel"], fg=C["muted"])
        bar = tk.Frame(tab, bg=C["panel"], padx=10, pady=10)
        bar.pack(fill="x")
        tk.Label(bar, text="Search", **lab).pack(side="left", padx=(0, 6))
        self.lib_q = tk.StringVar()
        self.lib_q.trace_add("write", lambda *a: self.root.after_idle(self.lib_fill))
        ttk.Entry(bar, textvariable=self.lib_q, width=30).pack(side="left")
        self.lib_info = tk.Label(bar, text="", anchor="w", padx=14, **lab)
        self.lib_info.pack(side="left", fill="x", expand=True)

        purpose = tk.Label(tab, text="Part of Price checks, for the curious: how the price checker reads an item. Paste a "
                           "copied item on the right (or press \"Under the hood\" on an item in Price checks) to see its "
                           "base, which bases it is compared with, and which trade-site search each mod turns into. On the "
                           "left, every base by class and group, and every mod the trade site can search for. You never "
                           "need this to price things.",
                 bg=C["panel"], fg=C["muted"], anchor="w", justify="left", wraplength=1100, padx=10,
                 font=("Segoe UI", 9))
        purpose.pack(fill="x", pady=(0, 6))
        purpose.bind("<Configure>", lambda e: purpose.config(wraplength=max(300, e.width - 24)))
        pane = ttk.PanedWindow(tab, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        left = tk.Frame(pane, bg=C["panel"])
        right = tk.Frame(pane, bg=C["panel2"], padx=12, pady=10, highlightthickness=1, highlightbackground=C["line"])
        pane.add(left, weight=3)
        pane.add(right, weight=2)

        nb = ttk.Notebook(left)
        nb.pack(fill="both", expand=True)
        self.lib_nb = nb
        tf = tk.Frame(nb, bg=C["panel"])
        sf = tk.Frame(nb, bg=C["panel"])
        nb.add(tf, text="Bases by class and group")
        nb.add(sf, text="Modifier stats")

        self.lib_tree = ttk.Treeview(tf, columns=("defence", "values", "count"), show="tree headings")
        self.lib_tree.heading("#0", text="Class / base group / base")
        for cid, title, w, anchor in (("defence", "Defences", 120, "w"), ("values", "Base values", 140, "w"),
                                      ("count", "Bases", 55, "e")):
            self.lib_tree.heading(cid, text=title)
            self.lib_tree.column(cid, width=w, anchor=anchor, stretch=False)
        self.lib_tree.column("#0", width=260, stretch=True)
        tsb = ttk.Scrollbar(tf, orient="vertical", command=self.lib_tree.yview)
        self.lib_tree.configure(yscrollcommand=tsb.set)
        tsb.pack(side="right", fill="y")
        self.lib_tree.pack(side="left", fill="both", expand=True)
        self.lib_tree.tag_configure("class", foreground=C["accent"], font=("Segoe UI", 10, "bold"))
        self.lib_tree.tag_configure("group", foreground=C["text"])
        self.lib_tree.tag_configure("base", foreground=C["muted"])

        self.lib_stats = ttk.Treeview(sf, columns=("mod", "better", "trade", "local"), show="headings")
        for cid, title, w, anchor in (("mod", "Mod wording (# = a number)", 290, "w"), ("better", "Better", 60, "center"),
                                      ("trade", "Trade-site stat id", 190, "w"), ("local", "Local", 50, "center")):
            self.lib_stats.heading(cid, text=title)
            self.lib_stats.column(cid, width=w, anchor=anchor, stretch=(cid in ("mod", "trade")))
        ssb = ttk.Scrollbar(sf, orient="vertical", command=self.lib_stats.yview)
        self.lib_stats.configure(yscrollcommand=ssb.set)
        ssb.pack(side="right", fill="y")
        self.lib_stats.pack(side="left", fill="both", expand=True)

        P2 = C["panel2"]
        tk.Label(right, text="Check an item", bg=P2, fg=C["text"], font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(right, text="Copy any item in game (Ctrl+C or Ctrl+Alt+C) and paste it here to see how the app reads it. Price check prices it the same way Ctrl+Alt+C in game does.",
                 bg=P2, fg=C["muted"], anchor="w", justify="left", wraplength=420, font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6))
        btns = tk.Frame(right, bg=P2)
        btns.pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text="Paste from clipboard", style="Accent.TButton", command=self.lib_paste).pack(side="left")
        ttk.Button(btns, text="Check", command=self.lib_check).pack(side="left", padx=6)
        ttk.Button(btns, text="Price check", command=self.lib_price).pack(side="left")
        ttk.Button(btns, text="Clear", command=lambda: (self.lib_in.delete("1.0", "end"), self.lib_check())).pack(side="left", padx=6)
        self.lib_in = tk.Text(right, height=9, bg=C["odd"], fg=C["text"], insertbackground=C["text"], relief="flat",
                              highlightthickness=1, highlightbackground=C["line"], font=(MONO, 9), wrap="none")
        self.lib_in.pack(fill="x")
        prow = tk.Frame(right, bg=P2)                       # 1.41: the price check result for the pasted item
        prow.pack(fill="x", pady=(8, 0))
        self.lib_open_btn = ttk.Button(prow, text="Show in Price checks", command=self.lib_open_check)
        self.lib_price_lbl = tk.Label(prow, text="", bg=P2, fg=C["muted"], anchor="w", justify="left", wraplength=420,
                                      font=("Segoe UI", 10, "bold"))
        self.lib_price_lbl.pack(side="left", fill="x", expand=True)
        self.lib_rid = None
        self.lib_out = tk.Text(right, bg=P2, fg=C["text"], relief="flat", highlightthickness=0, font=("Segoe UI", 10),
                               wrap="word", cursor="arrow")
        self.lib_out.pack(fill="both", expand=True, pady=(8, 0))
        self.root.after(0, lambda: self.attach_lookup(self.lib_out))      # 2.0 beta 10: right-click > Look up
        for tag, kw in (("h", dict(foreground=C["accent"], font=("Segoe UI", 10, "bold"))),
                        ("k", dict(foreground=C["muted"])), ("good", dict(foreground=C["green"])),
                        ("bad", dict(foreground=C["red"])), ("mono", dict(foreground=C["steel"], font=(MONO, 9)))):
            self.lib_out.tag_configure(tag, **kw)
        self.lib_loaded = False
        self.lib_check()

    # ---------------- filling
    def refresh_library(self, force=False):
        if not force and not self.page_open("Under the hood"):
            return
        if not self.lib_loaded:
            self.lib_loaded = True
            self.lib_fill()

    def lib_fill(self):
        if not getattr(self, "lib_loaded", False):
            return
        inf = gamedata.info()
        if inf["error"]:
            self.lib_info.config(text=inf["error"], fg=C["red"])
        else:
            src = inf["source"]
            self.lib_info.config(fg=C["muted"], text=f"{inf['bases']:,} bases in {inf['groups']} groups · {inf['stats']:,} mod stats · "
                                                     f"data from {src.get('name', '?')} ({(src.get('commit') or '').split(' ')[-1]})")
        q = self.lib_q.get().strip().lower()
        t = self.lib_tree
        t.delete(*t.get_children())
        cls, grps, bases = gamedata.classes(), gamedata.groups(), gamedata.load()["bases"]
        for cid, c in cls.items():
            gids = [gid for gid, g in grps.items() if g["class"] == cid]
            rows = []
            for gid in gids:
                g = grps[gid]
                names = [b for b in g["bases"] if not q or q in b.lower() or q in g["name"].lower() or q in c["name"].lower()]
                if names:
                    rows.append((gid, g, names))
            if not rows:
                continue
            cnode = t.insert("", "end", text=c["name"], values=("", "", sum(len(n) for _, _, n in rows)), tags=("class",),
                             open=bool(q))
            for gid, g, names in rows:
                d = g.get("defence")
                dtxt = " / ".join(DEF_SHORT[k] for k in (d or "").split("_") if k in DEF_SHORT) if d and d != "none" else ""
                gnode = t.insert(cnode, "end", text=g["name"], values=(dtxt, "", len(names)), tags=("group",), open=bool(q))
                for n in names:
                    b = bases.get(n, {})
                    vals = "  ".join(f"{DEF_SHORT[k]} {v[1]}" for k, v in (b.get("armour") or {}).items())
                    t.insert(gnode, "end", text=n, values=("", vals, ""), tags=("base",))
        s = self.lib_stats
        s.delete(*s.get_children())
        shown = 0
        for st in gamedata.load()["stats"]:
            if q and q not in st["ref"].lower():
                continue
            ids = ", ".join(i for v in st["trade"].values() for i in v[:1])
            s.insert("", "end", values=(st["ref"], "higher" if st.get("better", 1) >= 0 else "lower", ids,
                                        "yes" if st.get("local") else ""))
            shown += 1
            if shown >= 800:
                s.insert("", "end", values=("… more: type in Search to narrow it down", "", "", ""))
                break

    # ---------------- check an item
    def lib_paste(self):
        txt = read_clipboard_text()
        if not txt:
            try:
                txt = self.root.clipboard_get()
            except tk.TclError:
                txt = ""
        self.lib_in.delete("1.0", "end")
        self.lib_in.insert("1.0", txt or "")
        self.lib_check()

    def lib_check(self):
        o = self.lib_out
        o.config(state="normal")
        o.delete("1.0", "end")
        txt = self.lib_in.get("1.0", "end").strip()
        if not txt:
            o.insert("end", "Nothing pasted yet.", "k")
            o.config(state="disabled")
            return
        it = gamedata.read_item(txt)
        if not it:
            o.insert("end", "That isn't a copied item (it should start with \"Item Class:\").", "bad")
            o.config(state="disabled")
            return
        g = gamedata.group(it["group"]) if it["group"] else None
        c = gamedata.classes().get(it["class"] or "", {})
        o.insert("end", f"{it['name'] or it['base'] or '?'}\n", "h")

        def row(k, v, tag=None):
            o.insert("end", f"{k}: ", "k")
            o.insert("end", f"{v}\n", tag)
        row("Class", c.get("name") or f"{it['class_text']} (not in the library)", None if c else "bad")
        row("Base", it["base"] or "not recognised", None if it["base"] else "bad")
        if g:
            row("Base group", g["name"], "good")
        if it["rarity"]:
            row("Rarity", it["rarity"])
        props = []
        if it["quality"]:
            props.append(f"quality {it['quality']}%")
        for k, w in (("armour", "armour"), ("evasion", "evasion"), ("energy_shield", "energy shield")):
            if k in it["props"]:
                props.append(f"{w} {it['props'][k]}")
        if it["sockets"]:
            jw = it.get("socket_types", "").count("J")
            props.append(f"{it['sockets']} socket{'s' if it['sockets'] != 1 else ''}" + (f" ({jw} jewel)" if jw else ""))
        for f in it.get("flags", []):
            if f != "corrupted":
                props.append(f)
        if it["ilvl"]:
            props.append(f"item level {it['ilvl']}")
        if it["corrupted"]:
            props.append("corrupted")
        if it["stack"] is not None:
            props.append(f"stack {it['stack']:,}" + (f" of {it['stack_max']:,}" if it.get("stack_max") else ""))
        if props:
            row("Properties", ", ".join(props))
        if it["mods"]:
            o.insert("end", f"\nModifiers ({len(it['mods'])})\n", "h")
            for m in it["mods"]:
                head = " ".join(w for w in (m.get("source"), m["kind"]) if w) + (f" T{m['tier']}" if m["tier"] else "")
                o.insert("end", f"{head}  ", "k")
                o.insert("end", m["text"] + "\n")
                if m["stat"]:
                    o.insert("end", f"    → {m['stat']}" + ("  (local)" if m["local"] else "")
                             + ("  (learned from the trade site)" if m.get("learned") else "") + "\n", "good")
                    o.insert("end", f"    {', '.join(m['trade'])}\n", "mono")
                else:
                    o.insert("end", "    → not found in the library\n", "bad")
        if it["unknown"]:
            o.insert("end", f"\n{len(it['unknown'])} line{'s' if len(it['unknown']) != 1 else ''} not found in the library or "
                            "on the trade site's stat list, so left out of price checks.", "bad")
        o.config(state="disabled")

    # ---------------- price check from here (1.41): the same price checker as the Price checks page
    def lib_price(self):
        txt = self.lib_in.get("1.0", "end").strip()
        item = self.read_any(txt) if txt else None
        if not item:
            self.lib_rid = None
            self.lib_price_lbl.config(text="Nothing to price: paste a copied item first." if not txt else
                                      "This item can't be price-checked (only gear, tablets and jewels can).", fg=C["red"])
            self.lib_open_btn.pack_forget()
            return
        same = [r for r in self.records.values() if self.item_sig(r["item"]) == self.item_sig(item)]
        if same:                                             # already in the list: show that one (Re-price there to redo it)
            self.lib_rid = same[-1]["id"]
        else:
            self.lib_rid = self.add_item_text(txt)
        self.lib_price_show()

    def lib_price_show(self):
        rec = self.records.get(self.lib_rid) if self.lib_rid is not None else None
        if not rec:
            self.lib_price_lbl.config(text="")
            self.lib_open_btn.pack_forget()
            return
        st = rec["state"]
        if st == "done":
            if rec.get("nomatch"):
                txt, col = "No match: no listings carry these mods.", C["red"]
            elif rec.get("manual"):
                txt, col = "Check by hand: matching listings are priced too far apart.", C["red"]
            elif rec.get("est") is not None:
                cf = rec.get("conf")
                txt = f"Price: {fmt_div(rec['est'])}" + (f"  ·  {cf} confidence" if cf and cf != "-" else "") + \
                      f"  ·  {rec['total']} listings"
                col = C["good"]
            else:
                txt, col = rec.get("label") or "Not priced.", C["muted"]
        elif st == "error":
            txt, col = "Couldn't price it: " + (rec.get("label") or ""), C["red"]
        else:
            txt, col = ("Pricing… " if st == "pricing" else "Waiting in line… ") + "(it is on the Price checks page too)", C["muted"]
        self.lib_price_lbl.config(text=txt, fg=col)
        self.lib_open_btn.pack(side="right", padx=(8, 0))

    def lib_inspect(self, text):
        """Open Under the hood with this copied item in it (Price checks: 'Under the hood' on an item)."""
        self.shell.open("library")
        self.lib_in.delete("1.0", "end")
        self.lib_in.insert("1.0", text or "")
        self.lib_check()

    def lib_lookup(self, words):
        """Show a base or mod on the left (Game search: 'how the price checker sees it')."""
        self.shell.open("library")
        self.lib_q.set(words)

    def lib_open_check(self):
        rid = self.lib_rid
        self.shell.open("checks")
        if rid is not None and self.tree.exists(str(rid)):
            self.tree.selection_set(str(rid))
            self.tree.see(str(rid))
