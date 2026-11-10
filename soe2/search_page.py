"""The Game search window (2.0 beta 10, a Labs tool): the PoE2 Keyword Search page rebuilt as a window of the app.
Mixed into App. Data and matching are in gamesearch.py."""
import tkinter as tk
from tkinter import ttk

from . import buglog
from . import gamesearch
from .config import SETTINGS, save_json
from .style import C, FONT_TITLE, SegBar
from .chrome import SectionBar, Viewport

PAGE = 60


class SearchPage:
    def build_search_window(self, body):
        P1, P2 = C["panel"], C["panel2"]
        self.gs_active, self.gs_shown, self.gs_job, self.gs_last = None, PAGE, None, []
        top = tk.Frame(body, bg=P1, padx=12, pady=8)
        top.pack(fill="x")
        d = gamesearch.load()
        head = tk.Frame(top, bg=P1)
        head.pack(fill="x")
        tk.Label(head, text="Game Search", bg=P1, fg=C["text"], font=(FONT_TITLE, 16, "bold")).pack(side="left")
        tk.Label(head, text=f"game data {d['version']} · {len(d['rows']):,} entries", bg=P1, fg=C["muted"],
                 font=("Consolas", 9)).pack(side="left", padx=8, pady=(8, 0))
        row = tk.Frame(top, bg=P1)
        row.pack(fill="x", pady=(8, 0))
        self.gs_q = tk.StringVar()
        self.gs_entry = tk.Entry(row, textvariable=self.gs_q, bg=C["odd"], fg=C["text"], insertbackground=C["text"],
                                 relief="flat", highlightthickness=1, highlightbackground=C["line"],
                                 highlightcolor=C["accent"], font=("Segoe UI", 12))
        self.gs_entry.pack(side="left", fill="x", expand=True, ipady=8)
        ttk.Button(row, text="Clear", command=self.gs_clear).pack(side="left", padx=(8, 0))
        self.gs_chips = tk.Frame(top, bg=P1, height=30)
        self.gs_chips.pack(fill="x", pady=(8, 0))
        self.gs_chips.bind("<Configure>", lambda e: self._gs_flow())
        self.gs_summary = tk.Label(body, text="", bg=P1, fg=C["muted"], anchor="w", padx=12)
        self.gs_summary.pack(fill="x")
        self.gs_head = SectionBar(body, "Results")          # 2.69.0: the results under a strip, in a sunken frame
        self.gs_head.pack(fill="x", padx=12, pady=(4, 0))
        rvp = Viewport(body, bg_key="panel2")
        rvp.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        res = rvp.body
        sb = ttk.Scrollbar(res, orient="vertical")
        sb.pack(side="right", fill="y")
        t = tk.Text(res, bg=P2, fg=C["text"], relief="flat", wrap="word", padx=16, pady=8, cursor="arrow",
                    highlightthickness=0, yscrollcommand=sb.set, font=("Segoe UI", 10))
        t.pack(side="left", fill="both", expand=True)
        sb.config(command=t.yview)
        t.tag_configure("name", font=("Segoe UI", 12, "bold"), foreground="#ffd9a8")
        t.tag_configure("tag", font=("Consolas", 9), foreground=C["muted"])
        t.tag_configure("link", foreground="#6ea8ff", underline=True)
        t.tag_configure("txt", lmargin1=0, lmargin2=0, spacing1=2)
        t.tag_configure("kw", foreground=C["steel"], font=("Segoe UI", 9, "italic"))
        t.tag_configure("mark", background=C["accent"], foreground=C["bg"])
        t.tag_configure("sep", font=("Segoe UI", 9))
        t.tag_configure("more", foreground=C["accent"], font=("Segoe UI", 10, "bold"), underline=True)
        t.tag_configure("empty", foreground=C["muted"], font=("Segoe UI", 10), justify="center")
        t.tag_configure("emo", foreground="#d9b8ff", font=("Segoe UI", 10, "bold"))       # 2.17.0: Anoints
        t.tag_configure("price", foreground=C["good"], font=("Segoe UI", 10))
        t.tag_configure("total", foreground="#ffd9a8", font=("Segoe UI", 10, "bold"))
        t.tag_bind("link", "<Enter>", lambda e: t.config(cursor="hand2"))
        t.tag_bind("link", "<Leave>", lambda e: t.config(cursor="arrow"))
        t.tag_bind("more", "<Button-1>", lambda e: self.gs_more())
        t.tag_bind("more", "<Enter>", lambda e: t.config(cursor="hand2"))
        t.tag_bind("more", "<Leave>", lambda e: t.config(cursor="arrow"))
        t.tag_configure("h2", font=(FONT_TITLE, 12, "bold"), foreground=C["accent"], spacing1=10, spacing3=4)
        t.tag_configure("try", font=("Consolas", 10, "bold"), foreground=C["text"], background=C["panel"])
        t.tag_configure("why", foreground=C["muted"])
        t.tag_configure("clear", foreground=C["accent"], font=("Segoe UI", 9), underline=True)
        for tg in ("try", "clear"):
            t.tag_bind(tg, "<Enter>", lambda e: t.config(cursor="hand2"))
            t.tag_bind(tg, "<Leave>", lambda e: t.config(cursor="arrow"))
        t.tag_bind("clear", "<Button-1>", lambda e: self.gs_recent_clear())
        t.config(state="disabled")
        self.gs_text = t
        self.gs_save_job = None
        # 2.66.0: Anoints is its own page, listed under Game search in the sidebar (Game search ↳ Anoints)
        self.gs_tabs = SegBar(top, ["Search", "Anoints"], command=lambda v: self.gs_tab_changed())
        self.gs_tabs.pack(anchor="w")
        if getattr(self, "shell", None) is not None:
            self.shell.register_tabs("search", self.gs_tabs, home="Search")
        self.gs_q.trace_add("write", lambda *a: self._gs_later())
        self.gs_entry.bind("<Escape>", lambda e: self.gs_clear())
        self.gs_render()

    def attach_lookup(self, widget):
        """Right-click in a text box: 'Look up ... in Game search' (the selected words, or the line under the mouse)."""
        def menu(e):
            from .config import SETTINGS
            from . import features as FEAT
            if not FEAT.on("search"):                        # 2.131.0: Game Search is a beta feature
                return
            try:
                txt = widget.get("sel.first", "sel.last")
            except tk.TclError:
                idx = widget.index(f"@{e.x},{e.y}")
                txt = widget.get(f"{idx} linestart", f"{idx} lineend")
            import re
            txt = re.sub(r"[\d.+%()\-–]+", " ", txt)          # numbers and ranges out: search the wording
            txt = re.sub(r"\s+", " ", txt).strip()[:60]
            if not txt:
                return
            m = tk.Menu(widget, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84")
            m.add_command(label=f"Look up “{txt[:40]}” in Game Search", command=lambda: self.gs_lookup(txt))
            m.tk_popup(e.x_root, e.y_root)
        widget.bind("<Button-3>", menu, add="+")

    # ---------------- searching
    def _gs_later(self):
        if self.gs_job:
            self.root.after_cancel(self.gs_job)
        self.gs_job = self.root.after(140, self._gs_go)

    def _gs_go(self):
        self.gs_job = None
        self.gs_shown = PAGE
        self.gs_render()
        if getattr(self, "gs_save_job", None):
            self.root.after_cancel(self.gs_save_job)
        self.gs_save_job = self.root.after(2000, self.gs_recent_add)

    # ---- P7 (2.108.0): Try examples and your recent searches on the empty page
    TRY = (("spirit", "every word must match"), ("cold -support", "-word leaves things out"),
           ('"cast speed"', "quotes for a phrase"), ("omen", "or pick a category above to see all of it"))

    def gs_recent(self):
        r = SETTINGS.get("gs_recent")
        return [x for x in r if isinstance(x, str)][:8] if isinstance(r, list) else []

    def gs_recent_add(self, q=None):
        self.gs_save_job = None
        q = " ".join((q if q is not None else self.gs_q.get()).split())
        if len(q) < 2:
            return
        r = [x for x in self.gs_recent() if x.lower() != q.lower()]
        if r and (q.lower().startswith(r[0].lower()) or r[0].lower().startswith(q.lower())):
            r = r[1:]                                      # (the same search, typed on)
        SETTINGS["gs_recent"] = [q] + r[:7]
        save_json("settings.json", SETTINGS)

    def gs_recent_clear(self):
        SETTINGS["gs_recent"] = []
        save_json("settings.json", SETTINGS)
        self.gs_render()

    def gs_try(self, q):
        self.gs_q.set(q)
        self._gs_go()

    def _gs_empty_page(self):
        t = self.gs_text
        t.insert("end", "Try\n", "h2")
        for i, (q, why) in enumerate(self.TRY):
            tg = f"try{i}"
            t.insert("end", f" {q} ", ("try", tg))
            t.insert("end", f"   {why}\n", ("why",))
            t.tag_bind(tg, "<Button-1>", lambda e, q=q: self.gs_try(q))
        rec = self.gs_recent()
        if rec:
            t.insert("end", "Your recent searches   ", "h2")
            t.insert("end", "Clear", ("clear",))
            t.insert("end", "\n")
            for i, q in enumerate(rec):
                tg = f"rec{i}"
                t.insert("end", f" {q} ", ("try", tg))
                t.insert("end", "\n")
                t.tag_bind(tg, "<Button-1>", lambda e, q=q: self.gs_try(q))

    def gs_clear(self):
        self.gs_q.set("")
        self.gs_active = None
        self.gs_shown = PAGE
        self.gs_render()
        self.gs_entry.focus_set()

    def gs_lookup(self, text):
        """Open Game search with this already typed (from other windows: 'Look up')."""
        self.shell.open_tab("search", "Search")
        self.gs_active = None
        self.gs_q.set(text.strip())
        self._gs_go()
        self.gs_entry.focus_set()

    def gs_pick(self, group):
        bar = getattr(self, "gs_tabs", None)
        if bar is not None:                                  # 2.66.0: Anoints is its own page
            want = "Anoints" if group == gamesearch.ANOINTS else "Search"
            if bar.get() != want:
                bar.pick(want, notify=False)
        self.gs_active = group
        self.gs_shown = PAGE
        self.gs_render()

    def gs_more(self):
        self.gs_shown += PAGE
        self.gs_render(keep_scroll=True)

    def gs_on_anoints(self):
        bar = getattr(self, "gs_tabs", None)
        return bar is not None and bar.get() == "Anoints"

    def gs_tab_changed(self):
        """Search <-> Anoints (from the sidebar)."""
        self.gs_active = gamesearch.ANOINTS if self.gs_on_anoints() else None
        self.gs_shown = PAGE
        self.gs_render()

    def gs_render(self, keep_scroll=False):
        d = gamesearch.load()
        q = self.gs_q.get()
        terms, neg = gamesearch.parse(q)
        has = bool(terms or neg)
        allr = gamesearch.search(q) if has else d["rows"]
        anoints = self.gs_on_anoints()
        if anoints:
            self.gs_active = gamesearch.ANOINTS
        elif self.gs_active == gamesearch.ANOINTS:
            self.gs_active = None
        allr = [it for it in allr if (it["g"] == gamesearch.ANOINTS) == anoints]
        order = [g for g in d["order"] if g != gamesearch.ANOINTS]
        counts = {}
        for it in allr:
            counts[it["g"]] = counts.get(it["g"], 0) + 1
        self._gs_chips(counts, len(allr), order)
        if anoints:
            self.gs_chips.pack_forget()
        elif not self.gs_chips.winfo_manager():
            self.gs_chips.pack(fill="x", pady=(8, 0))
        lst = [it for it in allr if it["g"] == self.gs_active] if self.gs_active else allr
        self.gs_last = lst
        t = self.gs_text
        y = t.yview()[0]
        t.config(state="normal")
        t.delete("1.0", "end")
        if d.get("error"):
            t.insert("end", "\n" + d["error"], "empty")
        elif not has and not self.gs_active:
            self.gs_summary.config(text="")
            self._gs_empty_page()
        else:
            if has:
                self.gs_summary.config(text=f"{len(lst):,} result{'s' if len(lst) != 1 else ''}"
                                            + (f" in {self.gs_active}" if self.gs_active else " across all categories"))
            else:                                              # 2.0 beta 21: a category on its own lists all of it
                self.gs_summary.config(text=f"All {len(lst):,} in {self.gs_active}. Type to narrow it down."
                                       + ("  Type an emotion (e.g. Isolation) to see every anoint that uses it. "
                                          "Prices: poe.ninja." if self.gs_active == gamesearch.ANOINTS else ""))
            if not lst:
                t.insert("end", "\nNothing matched. Try fewer words, or a different spelling.", "empty")
            for n, it in enumerate(lst[:self.gs_shown]):
                self._gs_insert(it, terms, n)
            if len(lst) > self.gs_shown:
                t.insert("end", f"\nShow {min(PAGE, len(lst) - self.gs_shown)} more", "more")
        t.config(state="disabled")
        if keep_scroll:
            t.yview_moveto(y)

    @staticmethod
    def _gs_cut(text, terms, size):
        low = text.lower()
        pos = min([p for p in (low.find(x) for x in terms) if p >= 0] or [-1])
        start = pos - 90 if pos > 120 else 0
        end = min(len(text), start + size)
        return ("… " if start > 0 else "") + text[start:end] + (" …" if end < len(text) else "")

    def _gs_put(self, text, terms, base_tags):
        """Insert text with every search word highlighted."""
        t = self.gs_text
        low = text.lower()
        marks = []
        for w in terms:
            i = low.find(w)
            while i >= 0:
                marks.append((i, i + len(w)))
                i = low.find(w, i + len(w))
        marks.sort()
        pos = 0
        for a, b in marks:
            if a < pos:
                continue
            if a > pos:
                t.insert("end", text[pos:a], base_tags)
            t.insert("end", text[a:b], base_tags + ("mark",))
            pos = b
        t.insert("end", text[pos:], base_tags)

    def _gs_insert(self, it, terms, n):
        t = self.gs_text
        if n:
            t.insert("end", "\n", "sep")
        self._gs_put(it["n"], terms, ("name",))
        t.insert("end", f"   {it['g']} · {it['c']}", ("tag",))
        if it.get("n"):                                   # 2.14.2: its wiki page (the inspector link is gone)
            tag = f"lnk{n}"
            t.insert("end", "   ")
            t.insert("end", "wiki ›", ("link", tag))
            t.tag_bind(tag, "<Button-1>", lambda e, nm=it["n"]: self.gs_wiki(nm))
        t.insert("end", "\n")
        opened = it["n"] + "|" + it["g"] in getattr(self, "gs_open", set())
        if it["t"]:
            if opened:                                    # 2.23.0: the whole text, one line per part
                self._gs_put(it["t"].replace(" | ", "\n"), terms, ("txt",))
            else:
                self._gs_put(self._gs_cut(it["t"], terms, 300), terms, ("txt",))
            if len(it["t"]) > 300 or " | " in it["t"] or (it["k"] and len(it["k"]) > 160):
                tag = f"det{n}"
                t.insert("end", "   ")
                t.insert("end", "less ‹" if opened else "more ›", ("link", tag))
                t.tag_bind(tag, "<Button-1>", lambda e, key=it["n"] + "|" + it["g"]: self.gs_toggle(key))
            t.insert("end", "\n")
        if it.get("a"):                                   # 2.17.0: an anoint - its emotions and what they cost
            return self._gs_anoint(it, terms)
        if it["k"]:
            self._gs_put(it["k"] if opened else self._gs_cut(it["k"], terms, 160), terms, ("kw",))
            t.insert("end", "\n")

    def _gs_anoint(self, it, terms):
        """The three Liquid Emotions, each with its poe.ninja price, and the total."""
        from .pricefmt import fmt_div
        from .wealth import WPRICES
        t = self.gs_text
        self.gs_prices_wanted()
        total, missing = 0.0, False
        for i, (name, n) in enumerate(gamesearch.emotion_counts(it["a"])):
            t.insert("end", "   +   " if i else "", ("tag",))
            if n > 1:
                t.insert("end", f"{n}× ", ("emo",))
            self._gs_put(name, terms, ("emo",))
            v = WPRICES.named(name) if self.gs_prices_ok() else None
            if v is None:
                missing = True
                t.insert("end", "  (no price)" if self.gs_prices_ok() else "", ("tag",))
            else:
                total += v * n
                t.insert("end", f"  {fmt_div(v)}" + (" each" if n > 1 else ""), ("price",))
        if self.gs_prices_ok() and total:
            t.insert("end", f"   =  {fmt_div(total)}" + (" + the unpriced one" if missing else ""), ("total",))
        elif getattr(self, "gs_price_state", "") == "loading":
            t.insert("end", "   prices loading from poe.ninja…", ("tag",))
        elif getattr(self, "gs_price_state", "") == "none":
            t.insert("end", "   (no prices: pick your league in Settings)" if not self.gs_league() else
                     "   (poe.ninja prices unavailable right now)", ("tag",))
        t.insert("end", "\n")

    @staticmethod
    def gs_league():
        from .config import SETTINGS
        return SETTINGS.get("league") or ""

    def gs_prices_ok(self):
        from .wealth import WPRICES
        return (getattr(self, "gs_price_state", "") == "ok" and WPRICES.ok
                and bool((WPRICES.parts.get("Delirium") or {}).get("lines")))

    def gs_prices_wanted(self):
        """Liquid Emotion prices from poe.ninja: fetched in the background the first time an anoint is shown, and
        again when they're over an hour old (WealthPrices.ensure_types)."""
        import threading
        import time
        lg = self.gs_league()
        st = getattr(self, "gs_price_state", "")
        if st == "loading" or (st in ("ok", "none") and lg == getattr(self, "gs_price_league", None)
                               and time.time() - getattr(self, "gs_price_ts", 0) < 3600):
            return
        if not lg:
            self.gs_price_state, self.gs_price_league, self.gs_price_ts = "none", lg, time.time()
            return
        self.gs_price_state, self.gs_price_league = "loading", lg

        def work():
            from .wealth import WPRICES
            try:
                WPRICES.ensure_types(lg, ("Delirium",))
            except Exception:
                buglog.caught()
            self.ui_q.put(("search_prices",))
        threading.Thread(target=work, daemon=True).start()

    def ev_search_prices(self):
        import time
        from .wealth import WPRICES
        self.gs_price_ts = time.time()
        self.gs_price_state = "ok" if WPRICES.ok and (WPRICES.parts.get("Delirium") or {}).get("lines") else "none"
        if getattr(self, "gs_text", None) is not None and self.gs_text.winfo_exists():
            self.gs_render(keep_scroll=True)

    def gs_toggle(self, key):
        """2.23.0: open / close one result's full details (the whole text and every keyword)."""
        s = self.__dict__.setdefault("gs_open", set())
        s.symmetric_difference_update({key})
        self.gs_render(keep_scroll=True)

    def gs_wiki(self, name):
        import urllib.parse
        import webbrowser
        webbrowser.open("https://www.poe2wiki.net/wiki/" + urllib.parse.quote(name.replace(" ", "_")))

    # ---------------- category buttons (wrap onto more rows when the window is narrow)
    def _gs_chips(self, counts, total, order):
        f = self.gs_chips
        for w in f.winfo_children():
            w.destroy()
        self.gs_chip_w = []
        for g, label in [(None, f"All  {total:,}")] + [(g, f"{g}  {counts.get(g, 0):,}") for g in order]:
            on = self.gs_active == g
            zero = g is not None and not counts.get(g)
            b = tk.Label(f, text=label, padx=8, pady=4, cursor="hand2", font=("Segoe UI", 9, "bold" if on else "normal"),
                         bg="#2c4a84" if on else "#111a2c", fg="#ffffff" if on else (C["steel"] if zero else "#cfdaf0"),
                         highlightthickness=1, highlightbackground=C["accent"] if on else C["line"])
            b.bind("<Button-1>", lambda e, gg=g: self.gs_pick(gg))
            self.gs_chip_w.append(b)
        self._gs_flow()

    def _gs_flow(self):
        f = self.gs_chips
        width = max(200, f.winfo_width())
        x = y = 0
        row_h = 0
        for b in getattr(self, "gs_chip_w", []):
            w, h = b.winfo_reqwidth(), b.winfo_reqheight()
            if x and x + w > width:
                x, y = 0, y + row_h + 5
                row_h = 0
            b.place(x=x, y=y)
            x += w + 5
            row_h = max(row_h, h)
        f.configure(height=y + row_h + 2)
