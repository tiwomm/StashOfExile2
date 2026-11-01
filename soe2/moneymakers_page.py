"""The Money Makers window (2.28.0): community strats in one standard layout (left: the list, right: the strat) and a
simple run tracker of its own. Data and the layout check live in moneymakers.py."""
import json
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, ttk

from . import moneymakers as MM
from .config import SETTINGS, save_json
from .style import C, MONO, SegBar, place_near

ORIGIN = {"community": "Community", "mine": "Mine", "example": "Example"}


def _hms(secs):
    secs = int(max(0, secs))
    h, rest = divmod(secs, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class MoneyMakersPage:
    """Mixed into App."""

    def build_money_window(self, body):
        P1 = C["panel"]
        self.mm_strats, self.mm_sel, self.mm_sort = [], None, ("thoughts_per_click", False)
        self.mm_run = None                                   # {"strat", "start"} while a run is going
        self.mm_page = SegBar(body, ["Strats", "Lucrative Strats", "Tablet Crafting", "Run tracker"],
                              command=lambda v: self.mm_show_page(), size=10, pad=(16, 5))
        self.mm_page.pack(anchor="w", padx=10, pady=(8, 0))
        self.mm_pages = {name: tk.Frame(body, bg=P1) for name in self.mm_page.btns}
        self.mm_strat_page, self.mm_run_page = self.mm_pages["Strats"], self.mm_pages["Run tracker"]
        self.mm_build_strats(self.mm_strat_page)
        self.mm_build_oneliners(self.mm_pages["Lucrative Strats"])
        self.mm_build_tablets(self.mm_pages["Tablet Crafting"])
        self.mm_build_runs(self.mm_run_page)
        self.mm_strat_page.pack(fill="both", expand=True)
        self.mm_reload()

    def mm_show_page(self):
        cur = self.mm_page.value
        for name, f in self.mm_pages.items():
            if name != cur:
                f.pack_forget()
        self.mm_pages[cur].pack(fill="both", expand=True)
        if cur == "Run tracker":
            self.mm_runs_refresh()
        elif cur == "Tablet Crafting":
            self.mm_tab_fill()
        elif cur == "Lucrative Strats":
            self.mm_one_fill()

    # ---------------- the strats list
    def mm_build_strats(self, page):
        P1, P2 = C["panel"], C["panel2"]
        bar = tk.Frame(page, bg=P1, padx=10, pady=8)
        bar.pack(fill="x")
        tk.Label(bar, text="Search", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 6))
        self.mm_q = tk.StringVar()
        self.mm_q.trace_add("write", lambda *_a: self.root.after_idle(self.mm_fill))
        ttk.Entry(bar, textvariable=self.mm_q, width=22).pack(side="left")
        ttk.Button(bar, text="↻ Check for new strats", command=lambda: self.mm_check_live(force=True)).pack(side="right")
        self.mm_live_lbl = tk.Label(bar, text="", bg=P1, fg=C["muted"], font=("Segoe UI", 9))
        self.mm_live_lbl.pack(side="right", padx=8)
        fbar = tk.Frame(page, bg=P1, padx=10)
        fbar.pack(fill="x", pady=(0, 6))

        def pick(label, var, values, width, first=False):
            tk.Label(fbar, text=label, bg=P1, fg=C["muted"]).pack(side="left", padx=(0 if first else 12, 6))
            cb = ttk.Combobox(fbar, textvariable=var, values=values, state="readonly", width=width)
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>", lambda e: (self.mm_fill(), self.root.after(20, self.root.focus_set)))
        self.mm_tag, self.mm_tier = tk.StringVar(value="Any"), tk.StringVar(value="Any")
        self.mm_max, self.mm_cmax = tk.StringVar(value="Any"), tk.StringVar(value="Any")
        tag_values = ["Any"] + [t for g in MM.TAG_GROUPS.values() for t in g]
        pick("Tag", self.mm_tag, tag_values, 15, first=True)
        pick("Waystone tier", self.mm_tier, ("Any",) + tuple(str(i) for i in range(1, 17)), 4)
        pick("🧠 Thinking at most", self.mm_max, ["Any"] + [w for w, _d in MM.THINKING.values()], 10)
        pick("🖱 Clicks at most", self.mm_cmax, ["Any"] + list(MM.CLICKS), 8)
        self.mm_cat = tk.StringVar(value="")                 # picked in the browser on the left ("" = all)
        self.mm_type = tk.StringVar(value="")

        bar2 = tk.Frame(page, bg=P1, padx=10)
        bar2.pack(fill="x", pady=(0, 6))
        for text, cmd in (("⬇ Download Format", self.mm_download_format), ("Import file…", self.mm_import),
                          ("+ Add my own", self.mm_add)):
            ttk.Button(bar2, text=text, command=cmd).pack(side="right", padx=(6, 0))
        leg = tk.Label(bar2, text="🧠 Thinking: Autopilot · Easy · Moderate · Hard · Big brain      "
                                  "🖱 Clicks per hour: Chill · Steady · Busy · Frantic",
                       bg=P1, fg="#ffd9a8", font=("Segoe UI", 9), anchor="w", justify="left")
        leg.pack(side="left", fill="x", expand=True)
        leg.bind("<Configure>", lambda e: leg.config(wraplength=max(200, e.width - 4)))

        pane = ttk.PanedWindow(page, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        # 2.28.0: browse by what the strat IS - Category > Type (Mapping > Breach), with counts
        nav = tk.Frame(pane, bg=P1)
        pane.add(nav, weight=0)
        self.mm_nav = ttk.Treeview(nav, columns=("n",), show="tree headings", selectmode="browse", height=8)
        self.mm_nav.heading("#0", text="Browse", anchor="w")
        self.mm_nav.heading("n", text="#")
        self.mm_nav.column("#0", width=150, minwidth=110, stretch=True)
        self.mm_nav.column("n", width=34, minwidth=30, anchor="center", stretch=False)
        self.mm_nav.tag_configure("empty", foreground=C["muted"])
        self.mm_nav.tag_configure("cat", font=("Segoe UI", 10, "bold"))
        self.mm_nav.pack(fill="both", expand=True)
        self.mm_nav.bind("<<TreeviewSelect>>", lambda e: self.mm_nav_pick())
        left = tk.Frame(pane, bg=P1)
        pane.add(left, weight=3)
        self.mm_pane = pane
        cols = (("name", "Strat", 170, "w"), ("type", "Type", 110, "w"),
                ("thoughts_per_click", "🧠 Thinking", 84, "center"), ("clicks_per_hour", "🖱 Clicks/h", 80, "center"),
                ("profit", "Est. profit/h", 92, "center"), ("origin", "From", 70, "center"))
        self.mm_tree = ttk.Treeview(left, columns=[c[0] for c in cols], show="headings", selectmode="browse")
        for cid, title, w, anchor in cols:
            self.mm_tree.heading(cid, text=title, command=lambda c=cid: self.mm_sort_by(c))
            self.mm_tree.column(cid, width=w, minwidth=56, anchor=anchor, stretch=cid == "name")
        self.mm_tree.tag_configure("mine", foreground=C["green"])
        self.mm_tree.tag_configure("example", foreground=C["muted"])
        sb = ttk.Scrollbar(left, orient="vertical", command=self.mm_tree.yview)
        self.mm_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.mm_tree.pack(side="left", fill="both", expand=True)
        self.mm_tree.bind("<<TreeviewSelect>>", lambda e: self.mm_pick())
        self.mm_tree.bind("<Button-3>", self.mm_menu)
        self.mm_empty = tk.Label(left, text="", bg=C["panel"], fg=C["muted"], font=("Segoe UI", 10))

        right = tk.Frame(pane, bg=P2, highlightthickness=1, highlightbackground=C["line"])
        pane.add(right, weight=2)
        acts = tk.Frame(right, bg=P2, padx=10, pady=8)
        acts.pack(fill="x")
        self.mm_btns = {}
        for key, text, cmd, style in (("track", "▶ Track runs", self.mm_track, "Accent.TButton"),
                                      ("regex", "Copy regex", self.mm_copy_regex, "TButton"),
                                      ("share", "Share…", self.mm_share, "TButton"),
                                      ("more", "⋯ More", self.mm_more, "TButton")):
            self.mm_btns[key] = ttk.Button(acts, text=text, command=cmd, style=style)
        self.mm_detail = tk.Text(right, bg=P2, fg=C["text"], relief="flat", wrap="word", padx=12, pady=6,
                                 font=("Segoe UI", 10), highlightthickness=0, cursor="arrow")
        dsb = ttk.Scrollbar(right, orient="vertical", command=self.mm_detail.yview)
        self.mm_detail.configure(yscrollcommand=dsb.set)
        dsb.pack(side="right", fill="y")
        self.mm_detail.pack(fill="both", expand=True)
        t = self.mm_detail
        t.tag_configure("title", font=("Segoe UI", 14, "bold"), foreground=C["text"], spacing3=2)
        t.tag_configure("meta", foreground=C["muted"], font=("Segoe UI", 9))
        t.tag_configure("summary", font=("Segoe UI", 10, "italic"), spacing1=6, spacing3=6)
        t.tag_configure("h", font=("Segoe UI", 10, "bold"), foreground=C["accent"], spacing1=10, spacing3=2)
        t.tag_configure("stat", font=("Segoe UI", 10, "bold"), foreground="#ffd9a8")
        t.tag_configure("li", lmargin1=10, lmargin2=26)
        t.tag_configure("mono", font=(MONO, 9), foreground=C["good"])
        t.tag_configure("chip", font=("Segoe UI", 10, "bold"), foreground="#8fc4ff")
        t.tag_configure("kicker", font=("Segoe UI", 9, "bold"), foreground=C["steel"])
        t.tag_configure("link", foreground="#8fc4ff", underline=True)
        t.tag_bind("link", "<Enter>", lambda e: t.config(cursor="hand2"))
        t.tag_bind("link", "<Leave>", lambda e: t.config(cursor="arrow"))
        self.mm_show_detail(None)
        pane.bind("<Map>", lambda e: self.root.after(50, self.mm_sash), add="+")

    def mm_sash(self):
        try:
            w = self.mm_pane.winfo_width()
            if w > 200 and not getattr(self, "_mm_sash_set", False):
                self._mm_sash_set = True
                self.mm_pane.sashpos(0, 190)
                self.mm_pane.sashpos(1, max(int(w * 0.62), min(800, w - 300)))
        except tk.TclError:
            pass

    def mm_reload(self, keep=None):
        self.mm_strats = MM.all_strats()
        self.mm_nav_fill()
        self.mm_fill(keep)
        if hasattr(self, "mm_one_tree"):
            self.mm_one_fill()

    def mm_rows(self):
        q = self.mm_q.get().strip().lower()
        cat, typ, tag, tier = self.mm_cat.get(), self.mm_type.get(), self.mm_tag.get(), self.mm_tier.get()
        words = {w: k for k, (w, _d) in MM.THINKING.items()}
        mx = words.get(self.mm_max.get(), 5)
        bands = list(MM.CLICKS)
        cmax = bands.index(self.mm_cmax.get()) if self.mm_cmax.get() in bands else len(bands)
        out = []
        for s in self.mm_strats:
            if cat and s.get("category") != cat:
                continue
            if typ and s.get("type") != typ:
                continue
            if tag != "Any" and tag not in (s.get("tags") or []) and tag != s.get("type"):
                continue
            wt = s.get("waystone_tiers")
            if tier != "Any" and wt and not wt["min"] <= int(tier) <= wt["max"]:
                continue
            if s.get("thoughts_per_click", 5) > mx:
                continue
            if s.get("clicks_per_hour") in bands and bands.index(s["clicks_per_hour"]) > cmax:
                continue
            if q and q not in json.dumps(s, ensure_ascii=False).lower():
                continue
            out.append(s)
        key, rev = self.mm_sort
        num = key in ("thoughts_per_click", "profit")

        def k(s):
            if key == "profit":
                p = s.get("est_profit") or {}
                return p.get("high") or p.get("low") or -1
            if key == "type":
                return MM.type_text(s).lower()
            if key == "clicks_per_hour":
                return list(MM.CLICKS).index(s["clicks_per_hour"]) if s.get("clicks_per_hour") in MM.CLICKS else 9
            return s.get(key, 0) if num else str(s.get(key, "")).lower()
        return sorted(out, key=k, reverse=rev)

    def mm_nav_fill(self):
        """The Category > Type browser, with how many strats each has (types with none are greyed)."""
        nav = self.mm_nav
        cur = nav.selection()[0] if nav.selection() else "all"
        nav.delete(*nav.get_children())
        n = {}
        for s in self.mm_strats:
            n[s.get("category")] = n.get(s.get("category"), 0) + 1
            n[(s.get("category"), s.get("type"))] = n.get((s.get("category"), s.get("type")), 0) + 1
        nav.insert("", "end", iid="all", text="All strats", values=(len(self.mm_strats),), tags=("cat",))
        for cat, types in MM.TAXONOMY.items():
            nav.insert("", "end", iid=cat, text=cat, values=(n.get(cat, 0) or "",),
                       tags=("cat",) if n.get(cat) else ("cat", "empty"), open=bool(n.get(cat)))
            for t in types:
                c = n.get((cat, t), 0)
                nav.insert(cat, "end", iid=f"{cat}|{t}", text=t, values=(c or "",), tags=() if c else ("empty",))
        nav.selection_set(cur if nav.exists(cur) else "all")

    def mm_nav_pick(self):
        sel = self.mm_nav.selection()
        cat, _, typ = (sel[0] if sel and sel[0] != "all" else "").partition("|")
        if (cat, typ) != (self.mm_cat.get(), self.mm_type.get()):
            self.mm_cat.set(cat)
            self.mm_type.set(typ)
            self.mm_tree.heading("type", text="Type" if cat else "Category › Type")
            self.mm_fill()

    def mm_fill(self, keep=None):
        keep = keep or self.mm_sel
        tv = self.mm_tree
        tv.delete(*tv.get_children())
        rows = self.mm_rows()
        for s in rows:
            tv.insert("", "end", iid=s["id"] + "|" + s["origin"], tags=(s["origin"],),
                      values=(s["name"], s.get("type", "") if self.mm_cat.get() else MM.type_text(s),
                              MM.thinking_word(s.get("thoughts_per_click")), s.get("clicks_per_hour", ""),
                              MM.money_text(s.get("est_profit")), ORIGIN.get(s["origin"], "")))
        if rows:
            self.mm_empty.place_forget()
        else:
            self.mm_empty.config(text="No strats match." if self.mm_strats else
                                 "No strats yet. Press ↻ Check for new strats, or + Add my own.")
            self.mm_empty.place(relx=0.5, rely=0.3, anchor="center")
        if keep and tv.exists(keep):
            tv.selection_set(keep)
            tv.see(keep)
        elif rows:
            tv.selection_set(tv.get_children()[0])
        else:
            self.mm_show_detail(None)

    def mm_sort_by(self, col):
        key = "thoughts_per_click" if col == "thoughts_per_click" else col
        cur, rev = self.mm_sort
        self.mm_sort = (key, not rev if cur == key else key in ("profit",))
        self.mm_fill()

    def mm_current(self):
        sel = self.mm_tree.selection()
        if not sel:
            return None
        return next((s for s in self.mm_strats if s["id"] + "|" + s["origin"] == sel[0]), None)

    def mm_pick(self):
        s = self.mm_current()
        self.mm_sel = self.mm_tree.selection()[0] if s else None
        self.mm_show_detail(s)

    def mm_show_detail(self, s):
        t = self.mm_detail
        t.config(state="normal")
        t.delete("1.0", "end")
        for b in self.mm_btns.values():
            b.pack_forget()
        if not s:
            t.insert("end", "Pick a strat on the left.", "meta")
            t.config(state="disabled")
            return
        show = ["track"] + (["regex"] if s.get("regex") else []) + ["share", "more"]
        for key in show:
            self.mm_btns[key].pack(side="left", padx=(0, 6))
        t.insert("end", MM.type_text(s).upper() + "\n", "kicker")
        t.insert("end", s["name"] + "\n", "title")
        t.insert("end", f"by {s.get('author', '?')} · game {s.get('patch', '?')} · "
                        f"updated {s.get('updated', '?')} · {ORIGIN.get(s['origin'], '')}"
                        + "\n", "meta")
        t.insert("end", s.get("summary", "") + "\n", "summary")
        tpc, cph = s.get("thoughts_per_click", 0), s.get("clicks_per_hour", "")
        word, why = MM.THINKING.get(tpc, ("?", ""))
        t.insert("end", "🧠 Thinking  ", "h")
        t.insert("end", word, "stat")
        t.insert("end", f"  {why}\n", "meta")
        t.insert("end", "🖱 Clicks per hour  ", "h")
        t.insert("end", cph, "stat")
        t.insert("end", f"  {MM.CLICKS.get(cph, '')}\n", "meta")
        t.insert("end", "Est. profit  ", "h")
        t.insert("end", MM.money_text(s.get("est_profit"), " / h") + "     ", "stat")
        t.insert("end", "Est. cost  ", "h")
        t.insert("end", MM.money_text(s.get("est_cost")) + "\n", "stat")
        if s.get("waystone_tiers"):
            t.insert("end", "Waystone tiers  ", "h")
            t.insert("end", MM.tiers_text(s["waystone_tiers"]) + "\n", "stat")
        tags = s.get("tags") or []
        for group, opts in MM.TAG_GROUPS.items():
            got = [x for x in opts if x in tags]
            if got:
                t.insert("end", group + "  ", "h")
                t.insert("end", " · ".join(got) + "\n", "chip")
        mine = MM.stats(MM.runs(), s["id"])
        if mine["runs"]:
            pph = mine["profit_per_hour"]
            t.insert("end", "Your runs  ", "h")
            t.insert("end", f"{mine['runs']} runs, {_hms(mine['avg_secs'])} each"
                            + (f", {pph:.1f} div / h" if pph is not None else "") + "\n", "stat")
        for key, title in (("requirements", "Requirements"), ("tablets", "Tablets"), ("waystones", "Waystones"),
                           ("atlas", "Atlas / master setup"), ("craft_steps", "Craft steps"), ("setup", "Other setup"),
                           ("steps", "Steps"),
                           ("loot", "Loot to sell"), ("tips", "Tips"), ("risks", "Risks")):
            items = s.get(key) or []
            if not items:
                continue
            t.insert("end", title + "\n", "h")
            for i, line in enumerate(items, 1):
                t.insert("end", (f"{i}. " if key == "steps" else "• ") + line + "\n", "li")
        if s.get("regex"):
            t.insert("end", "Stash regex\n", "h")
            t.insert("end", s["regex"] + "\n", "mono")
        if s.get("sources"):
            t.insert("end", "Sources\n", "h")
            for i, src in enumerate(s["sources"]):
                tag = f"src{i}"
                t.insert("end", "• ", "li")
                t.insert("end", (src.get("title") or src["url"]) + "\n", ("li", "link", tag))
                t.tag_bind(tag, "<Button-1>", lambda e, u=src["url"]: webbrowser.open(u))
        t.config(state="disabled")

    def mm_more(self):
        b = self.mm_btns["more"]
        self.mm_menu(None, b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())

    def mm_menu(self, e, x=None, y=None):
        """Right-click a strat (or ⋯ More): everything you can do with it."""
        if e is not None:
            row = self.mm_tree.identify_row(e.y)
            if not row:
                return
            self.mm_tree.selection_set(row)
            x, y = e.x_root, e.y_root
        s = self.mm_current()
        if not s:
            return
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84")
        m.add_command(label="▶ Track runs", command=self.mm_track)
        if s and s.get("regex"):
            m.add_command(label="Copy regex", command=self.mm_copy_regex)
        m.add_command(label="Share…", command=self.mm_share)
        m.add_command(label="Export…", command=self.mm_export)
        if s and s["origin"] == "mine":
            m.add_separator()
            m.add_command(label="Edit", command=self.mm_edit)
            m.add_command(label="Delete", command=self.mm_delete)
        m.tk_popup(x, y)

    # ---------------- live updates from GitHub
    def mm_on_show(self):
        self.mm_check_live(force=False)

    def mm_check_live(self, force=False):
        if getattr(self, "_mm_checking", False):
            return
        self._mm_checking = True
        if force:
            self.mm_live_lbl.config(text="Checking GitHub…", fg=C["muted"])

        def work():
            res = MM.fetch_live(force=force)
            self.root.after(0, lambda: self.mm_live_done(res, force))
        threading.Thread(target=work, daemon=True).start()

    def mm_live_done(self, res, force):
        self._mm_checking = False
        what, info = res
        if what != "skip":
            save_json("settings.json", SETTINGS)
        if what == "new":
            self.mm_reload()
            self.mm_live_lbl.config(text=f"New strats: {info} in the shared list.", fg=C["green"])
        elif what == "same" and force:
            self.mm_live_lbl.config(text="Up to date.", fg=C["muted"])
        elif what == "error" and force:
            self.mm_live_lbl.config(text=info, fg=C["red"])

    # ---------------- actions
    def mm_copy_regex(self):
        s = self.mm_current()
        if s and s.get("regex"):
            self.root.clipboard_clear()
            self.root.clipboard_append(s["regex"])
            self.own_clip = s["regex"]
            self._say("Copied the strat's stash search. In game: Ctrl+F, Ctrl+V.", 6)

    def mm_share(self):
        s = self.mm_current()
        if s:
            webbrowser.open(MM.issue_link(s))
            self._say("Opened a GitHub issue with the strat filled in - check it and press Submit.", 8)

    def mm_export(self):
        s = self.mm_current()
        if not s:
            return
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".txt", initialfile=s["id"] + ".txt",
                                            filetypes=[("Strat (text, opens in Notepad)", "*.txt"),
                                                       ("Strat (JSON)", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8", newline="\r\n") as f:
                if path.lower().endswith(".json"):
                    json.dump(MM.tidy(s), f, indent=2, ensure_ascii=False)
                else:
                    f.write(MM.to_text(s))
            self._say(f"Saved {path}", 6)

    def mm_download_format(self, path=None):
        """The blank standard layout as a .txt file (opens in Notepad on any Windows PC): fill it in, then Import
        file… - or attach it to a Strategy issue on GitHub to share it."""
        path = path or filedialog.asksaveasfilename(parent=self.root, defaultextension=".txt",
                                                    initialfile="money-maker-strat-template.txt",
                                                    filetypes=[("Strat (text, opens in Notepad)", "*.txt")])
        if not path:
            return None
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(MM.to_text(None))
        self.app_toast(f"Saved the strat template:\n{path}\n\nOpen it in Notepad, fill it in, then press Import "
                       "file… here (or attach it to a Strategy issue on GitHub to share it).", "Download Format")
        return path

    def mm_import(self, path=None):
        path = path or filedialog.askopenfilename(parent=self.root, filetypes=[("Strat", "*.txt *.json")])
        if not path:
            return None
        try:
            with open(path, encoding="utf-8-sig") as f:
                raw = f.read()
            d = json.loads(raw) if raw.lstrip().startswith(("{", "[")) else MM.from_text(raw)
        except Exception as e:
            self.app_toast(f"Couldn't read that file ({e.__class__.__name__}).", "Import strat")
            return None
        items = d.get("strats") if isinstance(d, dict) and "strats" in d else d if isinstance(d, list) else [d]
        mine = MM.mine()
        added, bad = 0, []
        for s in items:
            if isinstance(s, dict):
                s = {k: v for k, v in s.items() if k != "origin"}
            probs = MM.validate(s)
            if probs:
                bad.append(f"{(s or {}).get('name', '?') if isinstance(s, dict) else '?'}: {probs[0]}")
                continue
            mine = [m for m in mine if m["id"] != s["id"]] + [s]
            added += 1
        MM.save_mine(mine)
        self.mm_reload()
        msg = f"Added {added} strat{'s' if added != 1 else ''} to Mine."
        if bad:
            msg += "\nLeft out (not in the standard layout): " + "; ".join(bad[:3])
        self.app_toast(msg, "Import strat")
        return added

    def mm_delete(self):
        s = self.mm_current()
        if s and s["origin"] == "mine":
            MM.save_mine([m for m in MM.mine() if m["id"] != s["id"]])
            self.mm_sel = None
            self.mm_reload()

    def mm_add(self):
        self.mm_form(MM.new_strat())

    def mm_edit(self):
        s = self.mm_current()
        if s and s["origin"] == "mine":
            self.mm_form(dict(s))

    def mm_form(self, s):
        """Add / edit one of your strats - exactly the fields of the standard layout."""
        from .style import ScrollArea
        P1 = C["panel"]
        win = tk.Toplevel(self.root, bg=P1)
        win.title("Your strat")
        win.transient(self.root)
        self.mm_form_win = win
        sa = ScrollArea(win, P1)
        sa.pack(fill="both", expand=True)
        f = tk.Frame(sa.inner, bg=P1, padx=14, pady=10)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        v = {}
        r = 0

        def head(text):
            nonlocal r
            tk.Label(f, text=text, bg=P1, fg=C["accent"], font=("Segoe UI", 10, "bold"), anchor="w").grid(
                row=r, column=0, columnspan=2, sticky="w", pady=(10, 2))
            r += 1

        def entry(key, label, value, width=40):
            nonlocal r
            tk.Label(f, text=label, bg=P1, fg=C["text"], anchor="w").grid(row=r, column=0, sticky="w", pady=2)
            v[key] = tk.StringVar(value=value)
            ttk.Entry(f, textvariable=v[key], width=width).grid(row=r, column=1, sticky="w" if width < 40 else "we",
                                                                 pady=2)
            r += 1

        def combo(key, label, values, value):
            nonlocal r
            tk.Label(f, text=label, bg=P1, fg=C["text"], anchor="w").grid(row=r, column=0, sticky="w", pady=2)
            v[key] = tk.StringVar(value=value)
            cb = ttk.Combobox(f, textvariable=v[key], values=values, state="readonly", width=60)
            cb.grid(row=r, column=1, sticky="w", pady=2)
            r += 1
            return cb

        def checks(key, label, options, picked):
            nonlocal r
            tk.Label(f, text=label, bg=P1, fg=C["text"], anchor="nw").grid(row=r, column=0, sticky="nw", pady=2)
            box = tk.Frame(f, bg=P1)
            box.grid(row=r, column=1, sticky="w", pady=2)
            v[key] = {}
            for i, opt in enumerate(options):
                var = tk.BooleanVar(value=opt in (picked or []))
                ttk.Checkbutton(box, text=opt, variable=var).grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 14))
                v[key][opt] = var
            r += 1

        def lines(key, label, h=2):
            nonlocal r
            tk.Label(f, text=label, bg=P1, fg=C["text"], anchor="nw").grid(row=r, column=0, sticky="nw", pady=2)
            t = tk.Text(f, height=h, width=60, bg=C["odd"], fg=C["text"], insertbackground=C["text"], relief="flat",
                        highlightthickness=1, highlightbackground=C["line"], font=("Segoe UI", 9), wrap="word")
            t.insert("1.0", "\n".join(s.get(key) or []))
            t.grid(row=r, column=1, sticky="we", pady=2)
            v[key] = t
            r += 1

        p, inv, wt = s.get("est_profit") or {}, s.get("est_cost") or {}, s.get("waystone_tiers") or {}
        head("About it")
        entry("name", "Name *", s.get("name", ""))
        entry("summary", "Summary (one line) *", s.get("summary", ""))
        entry("patch", "Game version", s.get("patch", ""), 10)
        head("What it is: the main thing you farm or do")
        cat_cb = combo("category", "Category *", MM.CATEGORIES, s.get("category", "Mapping"))
        typ_cb = combo("type", "Type *", MM.TAXONOMY.get(s.get("category", "Mapping"), ()), s.get("type", ""))

        def cat_changed(_e=None):
            types = MM.TAXONOMY.get(v["category"].get(), ())
            typ_cb.config(values=types)
            if v["type"].get() not in types:
                v["type"].set(types[0] if types else "")
        cat_cb.bind("<<ComboboxSelected>>", cat_changed)
        head("Effort")
        think = [f"{w} - {d}" for w, d in MM.THINKING.values()]
        combo("tpc", "🧠 Thinking *", think, think[s.get("thoughts_per_click", 2) - 1])
        clicks = [f"{w} - {d}" for w, d in MM.CLICKS.items()]
        cur = next((c for c in clicks if c.startswith(str(s.get("clicks_per_hour")) + " ")), clicks[1])
        combo("cph", "🖱 Clicks per hour *", clicks, cur)
        head("Tags (everything else about it)")
        v["tags"] = {}
        for group, opts in MM.TAG_GROUPS.items():
            checks("tags:" + group, group, opts, s.get("tags"))
            v["tags"].update(v["tags:" + group])
        head("Numbers (estimates)")
        entry("tiers", "Waystone tiers (1-16, e.g. 14-16)",
              "" if not wt else MM.tiers_text(wt).replace("T", ""), 10)
        entry("inv", "Est. cost (div)", "" if not inv else f"{inv.get('amount', ''):g}", 10)
        entry("profit", "Est. profit per hour (div, e.g. 5-10)",
              "" if not p else MM.money_text(p).replace(" div", ""), 10)
        head("The guide (one line per item)")
        lines("requirements", "Requirements")
        lines("tablets", "Tablets")
        lines("waystones", "Waystones")
        lines("atlas", "Atlas / master setup")
        lines("craft_steps", "Craft steps", 3)
        lines("setup", "Other setup")
        lines("steps", "Steps *", 5)
        lines("loot", "Loot to sell")
        lines("tips", "Tips")
        lines("risks", "Risks")
        entry("regex", "Stash regex", s.get("regex", ""))
        entry("sources", "Source link", (s.get("sources") or [{}])[0].get("url", ""))
        msg = tk.Label(f, text="* = needed. Everything else is optional.", bg=P1, fg=C["muted"], anchor="w",
                       font=("Segoe UI", 9))
        msg.grid(row=r, column=0, columnspan=2, sticky="we", pady=(8, 0))
        r += 1

        def save():
            out = dict(s)
            out.pop("origin", None)
            for k in ("name", "category", "type", "summary", "patch", "regex"):
                out[k] = v[k].get().strip()
            for k in ("requirements", "tablets", "waystones", "atlas", "craft_steps", "setup", "steps", "loot", "tips",
                      "risks"):
                out[k] = [ln.strip() for ln in v[k].get("1.0", "end").split("\n") if ln.strip()]
            out["tags"] = [opt for opt, var in v["tags"].items() if var.get()] + \
                [x for x in s.get("tags") or [] if x not in v["tags"]]          # (e.g. "example")
            words = [w for w, _d in MM.THINKING.values()]
            out["thoughts_per_click"] = words.index(v["tpc"].get().split(" - ")[0]) + 1
            out["clicks_per_hour"] = v["cph"].get().split(" - ")[0]
            try:
                rng = MM._num_range(v["profit"].get())
                out["est_profit"] = {"low": rng[0], "high": rng[1], "unit": "div"} if rng else None
                rng = MM._num_range(v["inv"].get())
                out["est_cost"] = {"amount": rng[0], "unit": "div"} if rng else None
                rng = MM._num_range(v["tiers"].get().lower().replace("t", ""))
                out["waystone_tiers"] = {"min": int(rng[0]), "max": int(rng[1])} if rng else None
            except (TypeError, ValueError):
                msg.config(text="Numbers only in tiers, cost and profit.", fg=C["red"])
                return
            url = v["sources"].get().strip()
            out["sources"] = [{"title": url, "url": url}] if url else []
            out["patch"] = out["patch"] or "?"
            out["updated"] = time.strftime("%Y-%m-%d")
            if not s.get("name"):
                out["id"] = MM.slug("my-" + out["name"])
            out = MM.tidy(out)
            probs = MM.validate(out)
            if probs:
                msg.config(text="Not saved: " + probs[0], fg=C["red"])
                return
            mine = [m for m in MM.mine() if m["id"] not in (s.get("id"), out["id"])] + [out]
            MM.save_mine(mine)
            win.destroy()
            self.mm_reload(keep=out["id"] + "|mine")

        btns = tk.Frame(win, bg=P1, padx=14, pady=8)
        btns.pack(fill="x", side="bottom", before=sa)
        ttk.Button(btns, text="Save", style="Accent.TButton", command=save).pack(side="right")
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right", padx=6)
        win.bind("<Escape>", lambda e: win.destroy())
        self.mm_form_save = save
        self.mm_form_vars = v
        win.update_idletasks()
        win.geometry(f"{min(820, f.winfo_reqwidth() + 40)}x{min(720, f.winfo_reqheight() + 70)}")
        place_near(self.root, win, self.root.winfo_rootx() + 80, self.root.winfo_rooty() + 40)
        return win

    # ---------------- the run tracker (its own, simple)
    def mm_build_runs(self, page):
        P1, P2 = C["panel"], C["panel2"]
        top = tk.Frame(page, bg=P2, padx=14, pady=12, highlightthickness=1, highlightbackground=C["line"])
        top.pack(fill="x", padx=10, pady=(10, 8))
        tk.Label(top, text="Strat", bg=P2, fg=C["muted"]).grid(row=0, column=0, sticky="w")
        self.mm_run_strat = tk.StringVar(value="(no strat)")
        self.mm_run_box = ttk.Combobox(top, textvariable=self.mm_run_strat, state="readonly", width=40)
        self.mm_run_box.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.mm_run_box.bind("<<ComboboxSelected>>", lambda e: (self.mm_runs_refresh(),
                                                               self.root.after(20, self.root.focus_set)))
        self.mm_clock = tk.Label(top, text="0:00", bg=P2, fg=C["text"], font=(MONO, 28, "bold"))
        self.mm_clock.grid(row=0, column=2, rowspan=2, padx=24)
        self.mm_go = ttk.Button(top, text="▶ Start run", style="Accent.TButton", command=self.mm_run_toggle)
        self.mm_go.grid(row=0, column=3, rowspan=2, sticky="ns")
        tk.Label(top, text="Profit this run (div)", bg=P2, fg=C["muted"]).grid(row=1, column=0, sticky="w",
                                                                                pady=(8, 0))
        self.mm_profit = tk.StringVar()
        ttk.Entry(top, textvariable=self.mm_profit, width=10).grid(row=1, column=1, sticky="w", padx=(8, 0),
                                                                    pady=(8, 0))
        tk.Label(top, text="Start when you enter the map (or start the block), end when you're done and have sold or "
                           "counted the loot. Type the profit any time before you end the run - or leave it empty.",
                 bg=P2, fg=C["muted"], font=("Segoe UI", 9), wraplength=700, justify="left").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))

        self.mm_summary = tk.Label(page, text="", bg=P1, fg="#ffd9a8", font=("Segoe UI", 11, "bold"), anchor="w")
        self.mm_summary.pack(fill="x", padx=12, pady=(0, 6))
        box = tk.Frame(page, bg=P1)
        box.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        cols = (("when", "When", 140, "w"), ("strat", "Strat", 220, "w"), ("time", "Time", 80, "center"),
                ("profit", "Profit", 90, "center"))
        self.mm_runs_tree = ttk.Treeview(box, columns=[c[0] for c in cols], show="headings", selectmode="extended")
        for cid, title, w, anchor in cols:
            self.mm_runs_tree.heading(cid, text=title)
            self.mm_runs_tree.column(cid, width=w, anchor=anchor, stretch=cid == "strat")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.mm_runs_tree.yview)
        self.mm_runs_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.mm_runs_tree.pack(side="left", fill="both", expand=True)
        self.mm_runs_tree.bind("<Delete>", lambda e: self.mm_runs_delete())
        bot = tk.Frame(page, bg=P1)
        bot.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(bot, text="Delete selected runs", command=self.mm_runs_delete).pack(side="left")

    def mm_run_names(self):
        names = {s["id"]: s["name"] for s in MM.all_strats()}
        return names

    def mm_runs_refresh(self):
        names = self.mm_run_names()
        self.mm_run_ids = {"(no strat)": None}
        for sid, name in sorted(names.items(), key=lambda kv: kv[1].lower()):
            self.mm_run_ids[name] = sid
        self.mm_run_box.config(values=list(self.mm_run_ids))
        if self.mm_run_strat.get() not in self.mm_run_ids:
            self.mm_run_strat.set("(no strat)")
        items = MM.runs()
        sid = self.mm_run_ids.get(self.mm_run_strat.get())
        tv = self.mm_runs_tree
        tv.delete(*tv.get_children())
        for i, rr in reversed(list(enumerate(items))):
            if sid and rr.get("strat") != sid:
                continue
            p = rr.get("profit")
            tv.insert("", "end", iid=str(i), values=(time.strftime("%Y-%m-%d %H:%M", time.localtime(rr["start"])),
                                                     names.get(rr.get("strat"), "(no strat)"),
                                                     _hms(rr["end"] - rr["start"]),
                                                     "" if p is None else f"{p:g} div"))
        st = MM.stats(items, sid)
        if st["runs"]:
            pph = st["profit_per_hour"]
            text = (f"{st['runs']} runs · {_hms(st['avg_secs'])} each · {st['per_hour']:.1f} runs / hour"
                    + (f" · {st['profit']:g} div total · {pph:.1f} div / hour" if pph is not None else ""))
        else:
            text = "No runs yet - press ▶ Start run."
        self.mm_summary.config(text=text)

    def mm_run_toggle(self):
        if self.mm_run is None:
            sid = getattr(self, "mm_run_ids", {}).get(self.mm_run_strat.get())
            self.mm_run = {"strat": sid, "start": time.time()}
            self.mm_go.config(text="■ End run")
            self.mm_tick()
            return
        txt = self.mm_profit.get().strip().replace(",", ".")
        try:
            profit = float(txt) if txt else None
        except ValueError:
            self._say("Profit: a number of divines (e.g. 2.5), or leave it empty.", 6)
            return
        items = MM.runs()
        items.append({"strat": self.mm_run["strat"], "start": self.mm_run["start"], "end": time.time(),
                      "profit": profit})
        MM.save_runs(items)
        self.mm_run = None
        self.mm_profit.set("")
        self.mm_go.config(text="▶ Start run")
        self.mm_clock.config(text="0:00")
        self.mm_runs_refresh()

    def mm_tick(self):
        if self.mm_run is None:
            return
        self.mm_clock.config(text=_hms(time.time() - self.mm_run["start"]))
        self.root.after(1000, self.mm_tick)

    def mm_runs_delete(self):
        sel = {int(i) for i in self.mm_runs_tree.selection()}
        if sel:
            MM.save_runs([r for i, r in enumerate(MM.runs()) if i not in sel])
            self.mm_runs_refresh()

    def mm_track(self):
        s = self.mm_current()
        self.mm_page.pick("Run tracker", notify=False)
        self.mm_show_page()
        if s:
            self.mm_runs_refresh()
            name = next((n for n, i in self.mm_run_ids.items() if i == s["id"]), None)
            if name and self.mm_run is None:
                self.mm_run_strat.set(name)
                self.mm_runs_refresh()

    # ---------------- Lucrative Strats: simple one-liners
    def mm_build_oneliners(self, page):
        P1 = C["panel"]
        bar = tk.Frame(page, bg=P1, padx=10, pady=8)
        bar.pack(fill="x")
        tk.Label(bar, text="Search", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 6))
        self.mm_one_q = tk.StringVar()
        self.mm_one_q.trace_add("write", lambda *_a: self.root.after_idle(self.mm_one_fill))
        ttk.Entry(bar, textvariable=self.mm_one_q, width=26).pack(side="left")
        for text, cmd, style in (("+ Add a one-liner", self.mm_one_add, "Accent.TButton"),
                                 ("Share…", self.mm_one_share, "TButton"), ("Copy", self.mm_one_copy, "TButton")):
            ttk.Button(bar, text=text, command=cmd, style=style).pack(side="right", padx=(6, 0))
        tk.Label(page, text="Quick money makers in one line - no guide needed. Shared ones arrive with the strats; "
                            "Share sends yours to everyone.", bg=P1, fg=C["muted"], font=("Segoe UI", 9),
                 anchor="w").pack(fill="x", padx=12, pady=(0, 6))
        box = tk.Frame(page, bg=P1)
        box.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        cols = (("text", "Strat", 600, "w"), ("mech", "Type / tags", 150, "w"), ("by", "By", 110, "w"),
                ("origin", "From", 80, "center"))
        self.mm_one_tree = ttk.Treeview(box, columns=[c[0] for c in cols], show="headings", selectmode="browse")
        for cid, title, w, anchor in cols:
            self.mm_one_tree.heading(cid, text=title)
            self.mm_one_tree.column(cid, width=w, minwidth=60, anchor=anchor, stretch=cid == "text")
        self.mm_one_tree.tag_configure("mine", foreground=C["green"])
        sb = ttk.Scrollbar(box, orient="vertical", command=self.mm_one_tree.yview)
        self.mm_one_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.mm_one_tree.pack(side="left", fill="both", expand=True)
        self.mm_one_tree.bind("<Button-3>", self.mm_one_menu)
        self.mm_one_tree.bind("<Double-1>", lambda e: self.mm_one_copy())
        self.mm_one_tree.bind("<Delete>", lambda e: self.mm_one_delete())
        self.mm_one_empty = tk.Label(box, text="", bg=P1, fg=C["muted"], font=("Segoe UI", 10))

    def mm_one_fill(self):
        tv = self.mm_one_tree
        tv.delete(*tv.get_children())
        q = self.mm_one_q.get().strip().lower()
        self.mm_ones = {}
        for o in MM.oneliners():
            if q and q not in json.dumps(o, ensure_ascii=False).lower():
                continue
            iid = o["id"] + "|" + o["origin"]
            self.mm_ones[iid] = o
            tv.insert("", "end", iid=iid, tags=(o["origin"],),
                      values=(o["text"], MM.type_text(o) if o.get("category") else ", ".join(o.get("tags") or []),
                              o.get("author", ""),
                              ORIGIN.get(o["origin"], "")))
        if self.mm_ones:
            self.mm_one_empty.place_forget()
        else:
            self.mm_one_empty.config(text="Nothing yet - press + Add a one-liner.")
            self.mm_one_empty.place(relx=0.5, rely=0.3, anchor="center")

    def mm_one_current(self):
        sel = self.mm_one_tree.selection()
        return self.mm_ones.get(sel[0]) if sel else None

    def mm_one_add(self, text=None):
        from tkinter import simpledialog
        text = text if text is not None else simpledialog.askstring(
            "Lucrative strat", "Your money maker in one line:", parent=self.root)
        text = (text or "").strip()
        if not text:
            return None
        o = {"id": MM.slug("my-" + text[:40]), "text": text[:300], "author": "me",
             "updated": time.strftime("%Y-%m-%d")}
        mine = [x for x in MM.mine_one() if x["id"] != o["id"]] + [o]
        MM.save_mine_one(mine)
        self.mm_one_fill()
        return o

    def mm_one_copy(self):
        o = self.mm_one_current()
        if o:
            self.root.clipboard_clear()
            self.root.clipboard_append(o["text"])
            self.own_clip = o["text"]
            self._say("Copied.", 4)

    def mm_one_share(self):
        o = self.mm_one_current()
        if o:
            webbrowser.open(MM.one_issue_link(o))

    def mm_one_delete(self):
        o = self.mm_one_current()
        if o and o["origin"] == "mine":
            MM.save_mine_one([x for x in MM.mine_one() if x["id"] != o["id"]])
            self.mm_one_fill()

    def mm_one_menu(self, e):
        row = self.mm_one_tree.identify_row(e.y)
        if not row:
            return
        self.mm_one_tree.selection_set(row)
        o = self.mm_one_current()
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84")
        m.add_command(label="Copy", command=self.mm_one_copy)
        m.add_command(label="Share…", command=self.mm_one_share)
        if o and o["origin"] == "mine":
            m.add_separator()
            m.add_command(label="Delete", command=self.mm_one_delete)
        m.tk_popup(e.x_root, e.y_root)

    # ---------------- Tablet Crafting quick reference
    def mm_build_tablets(self, page):
        P1, P2 = C["panel"], C["panel2"]
        pane = ttk.PanedWindow(page, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=10, pady=10)
        left = tk.Frame(pane, bg=P2, padx=14, pady=10, highlightthickness=1, highlightbackground=C["line"])
        pane.add(left, weight=2)
        tk.Label(left, text="HOW TO CRAFT A TABLET", bg=P2, fg=C["steel"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x")
        for i, (when, what) in enumerate(MM.TABLET_FLOW, 1):
            row = tk.Frame(left, bg=P2)
            row.pack(fill="x", pady=(8, 0))
            tk.Label(row, text=str(i), bg=C["accent"], fg="#10141c", font=("Segoe UI", 10, "bold"), width=2).pack(
                side="left", anchor="n")
            col = tk.Frame(row, bg=P2)
            col.pack(side="left", fill="x", expand=True, padx=(10, 0))
            tk.Label(col, text=when, bg=P2, fg=C["text"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
            lab = tk.Label(col, text=what, bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left")
            lab.pack(fill="x")
            lab.bind("<Configure>", lambda e, w=lab: w.config(wraplength=max(150, e.width - 4)))
        tk.Frame(left, bg=C["line"], height=1).pack(fill="x", pady=12)
        tk.Label(left, text="CHECK YOUR TABLET", bg=P2, fg=C["steel"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(left, text="Hover a tablet in game, press Ctrl+C, then:", bg=P2, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(2, 6))
        ttk.Button(left, text="Check my tablet", style="Accent.TButton", command=self.mm_tab_check).pack(anchor="w")
        self.mm_tab_advice = tk.Label(left, text="", bg=P2, fg=C["text"], font=("Segoe UI", 10, "bold"), anchor="w",
                                      justify="left")
        self.mm_tab_advice.pack(fill="x", pady=(8, 0))
        self.mm_tab_advice.bind("<Configure>", lambda e: self.mm_tab_advice.config(wraplength=max(150, e.width - 4)))

        right = tk.Frame(pane, bg=P1)
        pane.add(right, weight=3)
        bar = tk.Frame(right, bg=P1)
        bar.pack(fill="x", pady=(0, 6))
        tk.Label(bar, text="Tablet", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 6))
        self.mm_tab_type = tk.StringVar(value="All")
        cb = ttk.Combobox(bar, textvariable=self.mm_tab_type, values=MM.TABLET_TYPES, state="readonly", width=11)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: (self.mm_tab_fill(), self.root.after(20, self.root.focus_set)))
        self.mm_tab_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Only valuable", variable=self.mm_tab_only, command=self.mm_tab_fill).pack(
            side="left", padx=(12, 0))
        ttk.Button(bar, text="Copy regex (valuable)", command=self.mm_tab_copy_all).pack(side="right")
        tk.Label(right, text="Valuable = ★ in your Mod book, or listings with it cost at least your Valuable mod "
                             "price. Prices are what the app learned from your price checks. Double-click a mod to "
                             "check its price on the trade site.", bg=P1, fg=C["muted"], font=("Segoe UI", 9),
                 anchor="w", justify="left", wraplength=560).pack(fill="x", pady=(0, 6))
        box = tk.Frame(right, bg=P1)
        box.pack(fill="both", expand=True)
        cols = (("star", "★", 30, "center"), ("mod", "Mod", 300, "w"), ("where", "Tablet", 90, "w"),
                ("side", "Prefix / suffix", 90, "center"), ("price", "Learned price", 100, "center"))
        self.mm_tab_tree = ttk.Treeview(box, columns=[c[0] for c in cols], show="headings", selectmode="extended")
        for cid, title, w, anchor in cols:
            self.mm_tab_tree.heading(cid, text=title)
            self.mm_tab_tree.column(cid, width=w, minwidth=30, anchor=anchor, stretch=cid == "mod")
        self.mm_tab_tree.tag_configure("good", foreground="#ffd9a8")
        self.mm_tab_tree.tag_configure("plain", foreground=C["muted"])
        sb = ttk.Scrollbar(box, orient="vertical", command=self.mm_tab_tree.yview)
        self.mm_tab_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.mm_tab_tree.pack(side="left", fill="both", expand=True)
        self.mm_tab_tree.bind("<Double-1>", lambda e: self.mm_tab_trade())
        self.mm_tab_tree.bind("<Button-3>", self.mm_tab_menu)
        self.mm_tab_rows = {}

    def mm_tab_data(self):
        """Every tablet mod -> (mod, valuable?, why, learned (median div, listings, base) or None, stat id)."""
        from . import regex as R
        from .market import MARKET
        R.load()
        try:
            stats = MARKET.cached_stats()
        except Exception:
            stats = {}
        by_sid = {}
        for (base, sid), st in stats.items():
            if "Tablet" in str(base) and st.get("n", 0) >= 3 and st.get("med") is not None:
                if sid not in by_sid or st["med"] > by_sid[sid][0]:
                    by_sid[sid] = (st["med"], st["n"], base)
        try:
            good = float(SETTINGS.get("good_div", 0.5) or 0.5)
        except (TypeError, ValueError):
            good = 0.5
        out = []
        for m in R.mods("tablet"):
            imp, why = self.rx_worth(m, "tablet")
            sid = MM.stat_id(m["line"])
            learned = by_sid.get(sid) if sid else None
            valuable = imp == "high" or bool(learned and learned[0] >= good)
            if imp == "ignore":
                valuable = False
            out.append((m, valuable, why if imp == "high" else "learned price" if valuable else "", learned, sid))
        out.sort(key=lambda r: (not r[1], -(r[3][0] if r[3] else -1), r[0]["text"]))
        return out

    def mm_tab_fill(self):
        tv = self.mm_tab_tree
        tv.delete(*tv.get_children())
        kind, only = self.mm_tab_type.get(), self.mm_tab_only.get()
        self.mm_tab_rows = {}
        for m, valuable, why, learned, sid in self.mm_tab_data():
            if kind != "All" and kind not in m["tags"] and "Any" not in m["tags"]:
                continue
            if only and not valuable:
                continue
            txt = m["text"]
            where = ", ".join(t for t in m["tags"] if t != "Any") or "Any"
            price = f"{learned[0]:.2g} div ({learned[1]})" if learned else "-"
            tv.insert("", "end", iid=m["id"], tags=("good" if valuable else "plain",),
                      values=("★" if valuable else "", txt[:1].upper() + txt[1:], where, m.get("side", ""), price))
            self.mm_tab_rows[m["id"]] = (m, valuable, why, learned, sid)
        if not self.mm_tab_rows and only:
            tv.insert("", "end", iid="_none", values=("", "No valuable tablet mods yet: rate some ★ in Regex "
                                                          "(right-click) or the Mod book, or price some tablets.",
                                                      "", "", ""), tags=("plain",))

    def mm_tab_regex(self, ids):
        from . import regex as R
        s, _notes = R.build("tablet", [(i, None) for i in ids], [], False, {})
        return s

    def mm_tab_copy(self, ids, what):
        s = self.mm_tab_regex(ids) if ids else ""
        if not s:
            self._say("No mods to search for.", 5)
            return None
        self.root.clipboard_clear()
        self.root.clipboard_append(s)
        self.own_clip = s
        self._say(f"Copied the stash search for {what}. In game: Ctrl+F, Ctrl+V.", 6)
        return s

    def mm_tab_copy_all(self):
        ids = [i for i, r in self.mm_tab_rows.items() if r[1]]
        return self.mm_tab_copy(ids, f"{len(ids)} valuable tablet mods")

    def mm_tab_trade(self, mid=None):
        sel = [mid] if mid else [i for i in self.mm_tab_tree.selection() if i in self.mm_tab_rows]
        if not sel:
            return None
        m, _v, _w, learned, sid = self.mm_tab_rows[sel[0]]
        if not sid:
            self._say("The trade site's name for this mod isn't known yet (it loads with the first price check).", 8)
            return None
        url = MM.trade_link(SETTINGS.get("league"), sid, learned[2] if learned else None)
        webbrowser.open(url)
        return url

    def mm_tab_menu(self, e):
        row = self.mm_tab_tree.identify_row(e.y)
        if row not in self.mm_tab_rows:
            return
        if row not in self.mm_tab_tree.selection():
            self.mm_tab_tree.selection_set(row)
        sel = [i for i in self.mm_tab_tree.selection() if i in self.mm_tab_rows]
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84")
        m.add_command(label="Check price on the trade site", command=lambda: self.mm_tab_trade(row))
        m.add_command(label=f"Copy regex ({len(sel)} mod{'s' if len(sel) > 1 else ''})",
                      command=lambda: self.mm_tab_copy(sel, f"{len(sel)} mod{'s' if len(sel) > 1 else ''}"))
        m.tk_popup(e.x_root, e.y_root)

    def mm_tab_check(self, text=None):
        """Read the copied tablet and say what to do next (the crafting flow on the left)."""
        from . import regex as R
        from .clipboard import read_clipboard_text
        if text is None:
            text = read_clipboard_text() or ""
        if "Tablet" not in text or not text.lstrip().startswith("Item Class:"):
            self.mm_tab_advice.config(text="The clipboard has no tablet: hover one in game, press Ctrl+C, then try "
                                           "again.", fg=C["red"])
            return None
        R.load()
        found = R.matching_mods("tablet", text)
        worth = {m["id"]: v for m, v, _w, _l, _s in self.mm_tab_data()}
        good = [i for i in found if worth.get(i)]
        rarity = MM.tablet_rarity(text)
        advice = MM.tablet_advice(rarity, len(found), len(good))
        names = {m["id"]: m["text"] for m in R.mods("tablet")}
        lines = [advice, ""] + [("★ " if i in good else "· ") + names.get(i, i) for i in found]
        self.mm_tab_advice.config(text="\n".join(lines), fg=C["text"])
        return advice
