"""2.99.0: the Mod book's Gear rules and Unique rules tabs, and each tab's "Learned" view (what was "What the app
learned" - its rows now sit with the rules they belong to). Mixed into App; the data side is gearbook.py.

  * Gear rules: an item class picker (Helmets, Belts, Rings ...) and every line that can roll on it (RePoE).
  * Unique rules: a unique picker (every unique in the game data); its lines come from your price checks, and a
    line with a choice (Mageblood's Legacies) lists every option. Rate S-F: S / A = High (always searched),
    B / C / D = Normal, F = Ignore (never searched).
GGG ToS: your own settings and the app's own data; nothing touches the game, nothing extra is fetched."""
import types
import tkinter as tk
from tkinter import ttk

from . import gearbook as GB
from .mods import RULES, SHOWN_TIERS, TIER_F, TIERS, F_TIP, impact_key
from .chrome import BarNote, SectionBar, Viewport
from .style import C, Tooltip

IMPACT_LABEL = {"high": "High", "normal": "Normal", "ignore": "Ignore"}
GRADE_TIP = "S / A = High (always searched), B / C / D = Normal, F = Ignore (never searched)."


class GearBookPage:
    # ---------------------------------------------------------------- Rules | Learned on every tab
    def mb_split(self, tab, cat):
        """A tab -> (rules frame, learned frame) with a Rules | Learned switch at the top."""
        top = tk.Frame(tab, bg=C["panel"], padx=8, pady=(6))
        top.pack(fill="x")
        rf = tk.Frame(tab, bg=C["panel"])
        lf = tk.Frame(tab, bg=C["panel"])
        rf.pack(fill="both", expand=True)
        var = tk.StringVar(value="Rules")
        btns = {}

        def show(which):
            var.set(which)
            for name, b in btns.items():
                b.configure(style="Primary.TButton" if name == which else "Quiet.TButton")
            (lf if which == "Rules" else rf).pack_forget()
            (rf if which == "Rules" else lf).pack(fill="both", expand=True)
            if which == "Learned":
                self.refresh_memory(True)
        for name in ("Rules", "Learned"):
            b = ttk.Button(top, text=name if name == "Rules" else "What the app learned", style="Quiet.TButton",
                           command=lambda n=name: show(n))
            b.pack(side="left", padx=(0, 4))
            btns[name] = b
        show("Rules")
        return rf, lf, show, var

    def mb_learned(self, lf, ns):
        """The learned view inside one tab (its rows only)."""
        mbar = tk.Frame(lf, bg=C["panel"], padx=8, pady=8)
        mbar.pack(fill="x")
        tk.Label(mbar, text="Show", bg=C["panel"], fg=C["muted"]).pack(side="left", padx=(0, 8))
        mv = ttk.Combobox(mbar, textvariable=self.mem_view, values=self.MEM_VIEWS, state="readonly", width=18)
        mv.pack(side="left")
        mv.bind("<<ComboboxSelected>>", lambda e: (self.refresh_memory(True), self.root.after(20, self.root.focus_set)))
        tk.Label(mbar, text="Filter", bg=C["panel"], fg=C["muted"]).pack(side="left", padx=(16, 8))
        ttk.Entry(mbar, textvariable=self.mem_filter, width=24).pack(side="left")
        ttk.Button(mbar, text="Refresh", command=lambda: self.refresh_memory(True)).pack(side="left", padx=8)
        ns.mem_info = tk.Label(lf, bg=C["panel"], fg=C["muted"], justify="left", anchor="w", padx=12)
        ns.mem_info.pack(fill="x")
        ns.mem_frame = tk.Frame(lf, bg=C["panel"])
        ns.mem_frame.pack(fill="both", expand=True)
        ns.mem_empty = tk.Label(lf, bg=C["panel"], fg=C["muted"], font=("Segoe UI", 10), justify="center",
                                wraplength=640)

    def mb_base_ok(self, base, cat=None):
        """A learned row's base belongs to the tab showing?"""
        cat = cat or self.rules_cat()
        ns = self.rt.get(cat)
        bc = GB.base_cat(base)
        if cat == "gear":
            return bc == f"gear:{getattr(ns, 'cls', '')}"
        if cat == "unique":
            return base in GB.unique_bases(getattr(ns, "uname", ""))
        return bc == cat

    # ---------------------------------------------------------------- Gear rules / Unique rules
    def build_picker_rules(self, tab, cat):
        """The Gear rules (cat "gear") or Unique rules (cat "unique") page."""
        P = C["panel"]
        ns = types.SimpleNamespace(cat=cat, keys={}, filt=tk.StringVar(), cls="", uname="")
        self.rt[cat] = ns
        ns.filt.trace_add("write", lambda *a: self.refresh_rules(cat))
        bar = tk.Frame(tab, bg=P, padx=8, pady=8)
        bar.pack(fill="x")
        if cat == "gear":
            names = [n for _c, n in GB.classes()]
            tk.Label(bar, text="Item class", bg=P, fg=C["muted"]).pack(side="left", padx=(0, 8))
            ns.pick = tk.StringVar(value=names[0] if names else "")
            cb = ttk.Combobox(bar, textvariable=ns.pick, values=names, state="readonly", width=18)
        else:
            tk.Label(bar, text="Unique", bg=P, fg=C["muted"]).pack(side="left", padx=(0, 8))
            ns.pick = tk.StringVar()
            cb = ttk.Combobox(bar, textvariable=ns.pick, values=self.gb_unique_list(), state="readonly", width=26,
                              postcommand=lambda: cb.configure(values=self.gb_unique_list()))
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: (self.gb_picked(cat), self.root.after(20, self.root.focus_set)))
        ns.picker = cb
        tk.Label(bar, text="Filter", bg=P, fg=C["muted"]).pack(side="left", padx=(16, 8))
        ttk.Entry(bar, textvariable=ns.filt, width=18).pack(side="left")
        ttk.Button(bar, text="Rate mods one at a time…", style="Primary.TButton",
                   command=lambda: self.rm_open(self.gb_set(cat) or None)).pack(side="left", padx=(16, 0))
        tbar = tk.Frame(tab, bg=P, padx=8)
        tbar.pack(fill="x")
        tk.Label(tbar, text="Rate selected:", bg=P, fg=C["muted"]).pack(side="left", padx=(0, 8))
        for t in SHOWN_TIERS:
            b = ttk.Button(tbar, text=t, width=3, command=lambda t=t: self.gb_grade(cat, t))
            b.pack(side="left", padx=(0, 4))
            if t == TIER_F:
                Tooltip(b, F_TIP)
        ttk.Button(tbar, text="Clear", style="Quiet.TButton", command=lambda: self.gb_grade(cat, None)).pack(
            side="left", padx=(4, 0))
        help_ = tk.Label(tab, text=GRADE_TIP + " " + ("Every line that can roll on this item class (RePoE); your rating is "
                                              "used when you price check one." if cat == "gear" else
                            "A unique's lines come from the ones you price check (pick it after checking one). A line "
                            "with a choice, like Mageblood's Legacies, lists every option: rate the ones that matter."),
                 bg=P, fg=C["muted"], anchor="w", justify="left", wraplength=900, padx=12,
                 font=("Segoe UI", 9))
        help_.pack(fill="x", pady=(8, 0))
        help_.bind("<Configure>", lambda e, l=help_: l.config(wraplength=max(300, e.width - 24)))
        bar = SectionBar(tab, "Gear mods" if cat == "gear" else "Unique mods")
        bar.pack(fill="x", padx=8, pady=(8, 0))
        ns.info = BarNote(bar)                      # 2.114.0: the counts in the strip
        vp = Viewport(tab)
        vp.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        cols = (("rate", "Rating", 80, "w"), ("type", "Type", 80, "w"),             # 2.114.0: no Impact column
                ("mod", "Mod", 460, "w"), ("on", "Tiers" if cat == "gear" else "", 80, "center"))
        ns.tv = ttk.Treeview(vp.body, columns=[c[0] for c in cols], show="headings", selectmode="extended")
        for cid, title, w, anchor in cols:
            ns.tv.heading(cid, text=title)
            ns.tv.column(cid, width=w, anchor=anchor, stretch=(cid == "mod"))
        sb = ttk.Scrollbar(vp.body, orient="vertical", command=ns.tv.yview)
        ns.tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        ns.tv.pack(fill="both", expand=True)
        ns.tv.tag_configure("high", foreground=C["good"])
        ns.tv.tag_configure("ignore", foreground=C["muted"])
        ns.tv.bind("<Double-1>", lambda e: self.cycle_rule(e, cat))
        ns.empty = tk.Label(vp.body, bg=C["panel"], fg=C["muted"], font=("Segoe UI", 10), justify="center",
                            wraplength=560)
        self.list_register("modbook", ns.tv)
        self.gb_picked(cat, refresh=False)

    def gb_unique_list(self):
        """Uniques you've price checked first (they have lines), then every other unique."""
        mine = sorted(GB.store(), key=str.lower)
        return mine + [n for n in GB.unique_names() if n not in GB.store()]

    def gb_picked(self, cat, refresh=True):
        ns = self.rt[cat]
        if cat == "gear":
            ns.cls = next((c for c, n in GB.classes() if n == ns.pick.get()), "")
        else:
            ns.uname = ns.pick.get()
        if refresh:
            self.refresh_rules(cat)
            self.refresh_memory(True)

    def gb_set(self, cat):
        ns = self.rt[cat]
        if cat == "gear":
            return f"gear:{ns.cls}" if ns.cls else ""
        return f"unique:{ns.uname.lower()}" if ns.uname else ""

    def gb_pick(self, cat, name):
        """Show this class ("Belts" or "belt") / unique on its page."""
        ns = self.rt[cat]
        if cat == "gear":
            name = GB.class_name(name) if name in dict(GB.classes()) else name
        ns.pick.set(name)
        self.gb_picked(cat)

    def gb_rows(self, cat):
        ns = self.rt[cat]
        if cat == "gear":
            return GB.class_mods(ns.cls) if ns.cls else []
        return GB.unique_rows(ns.uname) if ns.uname else []

    def _refresh_picker_rules(self, cat):
        ns = self.rt[cat]
        q = ns.filt.get().lower().strip()
        keep = {ns.keys.get(i) for i in ns.tv.selection()}
        ns.tv.delete(*ns.tv.get_children())
        ns.keys = {}
        order = {"high": 0, "normal": 1, "ignore": 2}
        rows = [r for r in self.gb_rows(cat) if not q or q in r["text"].lower()]
        rows.sort(key=lambda r: (order[impact_key(r["key"])], not r.get("option"), r["text"].lower()))
        for n, r in enumerate(rows):
            k = r["key"]
            imp = impact_key(k)
            iid = f"g{n}"
            ns.keys[iid] = k
            ns.tv.insert("", "end", iid=iid, values=(self.mb_rating([k]),
                                                     ("Option" if r.get("option") else r.get("kind") or ""),
                                                     r["text"], r.get("tiers") or ""),
                         tags=(imp,) if k in RULES and imp != "normal" else ())
            if k in keep:
                ns.tv.selection_add(iid)
        rated = sum(1 for r in self.gb_rows(cat) if r["key"] in RULES)
        if cat == "unique" and ns.uname and not rows and not q:
            ns.empty.config(text=f"No lines for {ns.uname} yet.\nPrice check one (Ctrl+Alt+C on it in game, or on the "
                                 "trade site) and its lines show here, with every option of a choice line.")
            ns.empty.place(relx=0.5, rely=0.3, anchor="center")
        elif cat == "unique" and not ns.uname:
            ns.empty.config(text="Pick a unique above. Ones you've price checked come first.")
            ns.empty.place(relx=0.5, rely=0.3, anchor="center")
        else:
            ns.empty.place_forget()
        what = GB.class_name(ns.cls) if cat == "gear" else (ns.uname or "")
        ns.info.config(text=f"{what}: {len(rows)} lines · {rated} rated by you" if what else "")

    def gb_grade(self, cat, grade):
        """Rate the selected lines: S..D, F (= ignore) or None (clear yours)."""
        from . import ratemods as RM
        ns = self.rt[cat]
        keys = [ns.keys[i] for i in ns.tv.selection() if i in ns.keys]
        if not keys:
            return self._say("Select lines first (Ctrl+A for all, Shift / Ctrl + click), then pick a rating.", 8)
        RM.apply(keys, "ignore" if grade == TIER_F else grade)
        self.gb_reprice(keys)
        self.refresh_rules(cat)
        self._say(f"{'Cleared' if grade is None else 'Rated ' + grade} {len(keys)} line{'s' if len(keys) != 1 else ''}.", 6)
        return keys

    def gb_reprice(self, keys):
        """Re-price the not-yet-listed items that have any of these lines."""
        from .ratemods import key_for
        keys = set(keys)
        affected = [rid for rid, rec in self.records.items() if rec.get("mark", "new") == "new"
                    and any(key_for(rec, m) in keys for m in (rec.get("item") or {}).get("mods") or [])]
        if affected:
            self.reprice(affected)
        return affected

