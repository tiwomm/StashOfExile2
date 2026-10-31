"""The Game search window (2.0 beta 10, a Labs tool): the PoE2 Keyword Search page rebuilt as a window of the app.
Mixed into App. Data and matching are in gamesearch.py."""
import tkinter as tk
from tkinter import ttk

from . import gamesearch
from .style import C, FONT_TITLE

PAGE = 60


class SearchPage:
    def build_search_window(self, body):
        P1, P2 = C["panel"], C["panel2"]
        self.gs_active, self.gs_shown, self.gs_job, self.gs_last = None, PAGE, None, []
        top = tk.Frame(body, bg=P1, padx=12, pady=10)
        top.pack(fill="x")
        d = gamesearch.load()
        head = tk.Frame(top, bg=P1)
        head.pack(fill="x")
        tk.Label(head, text="Game search", bg=P1, fg=C["text"], font=(FONT_TITLE, 16, "bold")).pack(side="left")
        tk.Label(head, text=f"game data {d['version']} · {len(d['rows']):,} entries", bg=P1, fg=C["muted"],
                 font=("Consolas", 9)).pack(side="left", padx=10, pady=(6, 0))
        row = tk.Frame(top, bg=P1)
        row.pack(fill="x", pady=(8, 0))
        self.gs_q = tk.StringVar()
        self.gs_entry = tk.Entry(row, textvariable=self.gs_q, bg=C["odd"], fg=C["text"], insertbackground=C["text"],
                                 relief="flat", highlightthickness=1, highlightbackground=C["line"],
                                 highlightcolor=C["accent"], font=("Segoe UI", 13))
        self.gs_entry.pack(side="left", fill="x", expand=True, ipady=6)
        ttk.Button(row, text="Clear", command=self.gs_clear).pack(side="left", padx=(8, 0))
        tk.Label(top, text='Every word must match.  -word leaves things out.  "exact phrase" for phrases.', bg=P1,
                 fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(6, 0))
        self.gs_chips = tk.Frame(top, bg=P1, height=30)
        self.gs_chips.pack(fill="x", pady=(8, 0))
        self.gs_chips.bind("<Configure>", lambda e: self._gs_flow())
        self.gs_summary = tk.Label(body, text="", bg=P1, fg=C["muted"], anchor="w", padx=12)
        self.gs_summary.pack(fill="x")
        res = tk.Frame(body, bg=P1)
        res.pack(fill="both", expand=True, padx=12, pady=(4, 10))
        sb = ttk.Scrollbar(res, orient="vertical")
        sb.pack(side="right", fill="y")
        t = tk.Text(res, bg=P2, fg=C["text"], relief="flat", wrap="word", padx=14, pady=10, cursor="arrow",
                    highlightthickness=1, highlightbackground=C["line"], yscrollcommand=sb.set, font=("Segoe UI", 10))
        t.pack(side="left", fill="both", expand=True)
        sb.config(command=t.yview)
        t.tag_configure("name", font=("Segoe UI", 12, "bold"), foreground="#ffd9a8")
        t.tag_configure("tag", font=("Consolas", 9), foreground=C["muted"])
        t.tag_configure("link", foreground="#6ea8ff", underline=True)
        t.tag_configure("txt", lmargin1=0, lmargin2=0, spacing1=2)
        t.tag_configure("kw", foreground=C["steel"], font=("Segoe UI", 9, "italic"))
        t.tag_configure("mark", background="#6a5418", foreground="#ffffff")
        t.tag_configure("sep", font=("Segoe UI", 4))
        t.tag_configure("more", foreground=C["accent"], font=("Segoe UI", 10, "bold"), underline=True)
        t.tag_configure("empty", foreground=C["muted"], font=("Segoe UI", 11), justify="center")
        t.tag_configure("emo", foreground="#d9b8ff", font=("Segoe UI", 10, "bold"))       # 2.17.0: Anoints
        t.tag_configure("price", foreground=C["good"], font=("Segoe UI", 10))
        t.tag_configure("total", foreground="#ffd9a8", font=("Segoe UI", 10, "bold"))
        t.tag_bind("link", "<Enter>", lambda e: t.config(cursor="hand2"))
        t.tag_bind("link", "<Leave>", lambda e: t.config(cursor="arrow"))
        t.tag_bind("more", "<Button-1>", lambda e: self.gs_more())
        t.tag_bind("more", "<Enter>", lambda e: t.config(cursor="hand2"))
        t.tag_bind("more", "<Leave>", lambda e: t.config(cursor="arrow"))
        t.config(state="disabled")
        self.gs_text = t
        self.gs_q.trace_add("write", lambda *a: self._gs_later())
        self.gs_entry.bind("<Escape>", lambda e: self.gs_clear())
        self.gs_render()

    def attach_lookup(self, widget):
        """Right-click in a text box: 'Look up ... in Game search' (the selected words, or the line under the mouse)."""
        def menu(e):
            from .config import SETTINGS
            if not SETTINGS.get("labs"):
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
            m.add_command(label=f"Look up “{txt[:40]}” in Game search", command=lambda: self.gs_lookup(txt))
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

    def gs_clear(self):
        self.gs_q.set("")
        self.gs_active = None
        self.gs_shown = PAGE
        self.gs_render()
        self.gs_entry.focus_set()

    def gs_lookup(self, text):
        """Open Game search with this already typed (from other windows: 'Look up')."""
        self.shell.open("search")
        self.gs_active = None
        self.gs_q.set(text.strip())
        self._gs_go()
        self.gs_entry.focus_set()

    def gs_pick(self, group):
        self.gs_active = group
        self.gs_shown = PAGE
        self.gs_render()

    def gs_more(self):
        self.gs_shown += PAGE
        self.gs_render(keep_scroll=True)

    def gs_render(self, keep_scroll=False):
        d = gamesearch.load()
        q = self.gs_q.get()
        terms, neg = gamesearch.parse(q)
        has = bool(terms or neg)
        allr = gamesearch.search(q) if has else d["rows"]
        counts = {}
        for it in allr:
            counts[it["g"]] = counts.get(it["g"], 0) + 1
        self._gs_chips(counts, len(allr), d["order"])
        lst = [it for it in allr if it["g"] == self.gs_active] if self.gs_active else allr
        self.gs_last = lst
        t = self.gs_text
        y = t.yview()[0]
        t.config(state="normal")
        t.delete("1.0", "end")
        if d.get("error"):
            t.insert("end", "\n" + d["error"], "empty")
        elif not has and not self.gs_active:
            self.gs_summary.config(text=f"{len(d['rows']):,} entries ready. Type a word to search all of them at once, "
                                        "or pick a category to see everything in it.")
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
        if it["t"]:
            self._gs_put(self._gs_cut(it["t"], terms, 300), terms, ("txt",))
            t.insert("end", "\n")
        if it.get("a"):                                   # 2.17.0: an anoint - its emotions and what they cost
            return self._gs_anoint(it, terms)
        if it["k"]:
            self._gs_put(self._gs_cut(it["k"], terms, 160), terms, ("kw",))
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
                pass
            self.ui_q.put(("search_prices",))
        threading.Thread(target=work, daemon=True).start()

    def ev_search_prices(self):
        import time
        from .wealth import WPRICES
        self.gs_price_ts = time.time()
        self.gs_price_state = "ok" if WPRICES.ok and (WPRICES.parts.get("Delirium") or {}).get("lines") else "none"
        if getattr(self, "gs_text", None) is not None and self.gs_text.winfo_exists():
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
            b = tk.Label(f, text=label, padx=10, pady=3, cursor="hand2", font=("Segoe UI", 9, "bold" if on else "normal"),
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
