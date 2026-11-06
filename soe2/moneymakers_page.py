"""The Money Makers window (2.28.0): community strats in one standard layout (left: the list, right: the strat) and a
simple run tracker of its own. Data and the layout check live in moneymakers.py."""
import json
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, ttk

from . import board as B
from . import rep as R
from . import moneymakers as MM
from .config import SETTINGS, save_json
from .style import C, MONO, SegBar, Tooltip, place_near
from .chrome import SectionBar, Viewport, section as chrome_section

ORIGIN = {"community": "Official", "mine": "Mine", "example": "Example", "board": "Community"}
VIEWS = ("Official", "Community", "Mine")
CARD_SORT = {"Profit": ("profit", True), "Upvotes": ("score", True), "Easiest": ("thoughts_per_click", False),
             "Name": ("name", False)}                         # 2.71.0: the cards' Sort


def _hms(secs):
    secs = int(max(0, secs))
    h, rest = divmod(secs, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class MoneyMakersPage:
    """Mixed into App."""

    def build_money_window(self, body):
        P1 = C["panel"]
        self.mm_strats, self.mm_sel, self.mm_sort = [], None, ("profit", True)     # 2.71.0: best first
        self.mm_page = SegBar(body, ["Strats", "Lucrative Strats", "Tablet Craft Helper", "Strat Tracker"],
                              command=lambda v: self.mm_show_page(), size=10, pad=(16, 4))
        self.mm_page.pack(anchor="w", padx=8, pady=(8, 0))
        if getattr(self, "shell", None) is not None:          # 2.64.0: its tabs are listed in the sidebar
            self.shell.register_tabs("money", self.mm_page)
        self.mm_pages = {name: tk.Frame(body, bg=P1) for name in self.mm_page.btns}
        self.mm_strat_page, self.mm_run_page = self.mm_pages["Strats"], self.mm_pages["Strat Tracker"]
        self.mm_build_strats(self.mm_strat_page)
        self.mm_build_oneliners(self.mm_pages["Lucrative Strats"])
        self.mm_build_tablets(self.mm_pages["Tablet Craft Helper"])
        self.build_ledger(self.mm_run_page)                  # 2.45.0: Strat Tracker (was Run tracker: ledger_page.py)
        self.mm_strat_page.pack(fill="both", expand=True)
        self.mm_reload()

    def mm_show_page(self):
        cur = self.mm_page.value
        for name, f in self.mm_pages.items():
            if name != cur:
                f.pack_forget()
        self.mm_pages[cur].pack(fill="both", expand=True)
        if cur == "Strat Tracker":
            self.fl_refresh()
        elif cur == "Tablet Craft Helper":
            self.mm_tab_fill()
        elif cur == "Lucrative Strats":
            self.mm_one_fill()

    # ---------------- the strats list
    def mm_build_strats(self, page):
        P1, P2 = C["panel"], C["panel2"]
        bar = tk.Frame(page, bg=P1, padx=8, pady=8)
        bar.pack(fill="x")
        # 2.30.0: where the strats come from - the curated Official list, the Community board, or your own
        self.mm_view = SegBar(bar, list(VIEWS), command=lambda v: self.mm_view_changed(), size=10, pad=(12, 4))
        self.mm_view.pack(side="left", padx=(0, 16))
        self.mm_board, self.mm_board_ones, self.mm_official = [], [], self._mm_official_cache()
        tk.Label(bar, text="Search", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 8))
        self.mm_q = tk.StringVar()
        self.mm_q.trace_add("write", lambda *_a: self.root.after_idle(self.mm_fill))
        ttk.Entry(bar, textvariable=self.mm_q, width=22).pack(side="left")
        self.mm_acct = ttk.Button(bar, text="", command=self.mm_account_click)
        self.mm_acct.pack(side="right")
        ttk.Button(bar, text="↻ Refresh", command=self.mm_refresh).pack(side="right", padx=(0, 8))
        self.mm_live_lbl = tk.Label(bar, text="", bg=P1, fg=C["muted"], font=("Segoe UI", 9))
        self.mm_live_lbl.pack(side="right", padx=8)
        self.mm_account_paint()
        # 2.71.0: filter buttons - what it is (category, then its type), how much thinking, how busy the hands
        self.mm_tag, self.mm_tier = tk.StringVar(value="Any"), tk.StringVar(value="Any")
        self.mm_max, self.mm_cmax = tk.StringVar(value="Any"), tk.StringVar(value="Any")
        self.mm_cat = tk.StringVar(value="")                 # "" = all
        self.mm_type = tk.StringVar(value="")
        chips = tk.Frame(page, bg=P1, padx=8)
        chips.pack(fill="x")
        self.mm_chip_rows = {}
        self.mm_content = set()                              # 2.78.0: the Content row (pinnacles, map content)
        for key, label in (("cat", "Strats"), ("type", "Type"), ("think", "🧠 Thoughts per click"), ("clicks", "🖱 Clicks per hour"),
                           ("content", "◆ Content")):
            r = tk.Frame(chips, bg=P1)
            tk.Label(r, text=label, bg=P1, fg=C["muted"], font=("Segoe UI", 9), width=19, anchor="w").pack(  # 2.85.1: 19 (cut off)
                side="left", anchor="n", pady=(4, 0))
            r.chips = tk.Frame(r, bg=P1)
            r.chips.pack(side="left", fill="x", expand=True)
            r.chips.bind("<Configure>", lambda e, f=r.chips: self._mm_flow(f, e.width))
            self.mm_chip_rows[key] = r
        for key in ("cat", "think", "clicks", "content"):
            self.mm_chip_rows[key].pack(fill="x")
        Tooltip(self.mm_chip_rows["content"], "What a strat farms - pick any: strats with one of them show.")
        Tooltip(self.mm_chip_rows["think"], "How much thinking a strat needs - a pick shows that level and the easier ones.")
        Tooltip(self.mm_chip_rows["clicks"], "How busy your hands are - a pick shows that pace and the calmer ones.")
        for var in (self.mm_max, self.mm_cmax):
            var.trace_add("write", lambda *_a: self.root.after_idle(self.mm_chips_paint))
        fbar = tk.Frame(page, bg=P1, padx=8)
        fbar.pack(fill="x", pady=(4, 8))

        def pick(label, var, values, width, first=False):
            tk.Label(fbar, text=label, bg=P1, fg=C["muted"]).pack(side="left", padx=(0 if first else 12, 6))
            cb = ttk.Combobox(fbar, textvariable=var, values=values, state="readonly", width=width)
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>", lambda e: (self.mm_fill(), self.root.after(20, self.root.focus_set)))
            return cb
        tag_values = ["Any"] + [t for g in MM.tag_groups().values() for t in g]
        pick("Tag", self.mm_tag, tag_values, 15, first=True)
        pick("Waystone tier", self.mm_tier, ("Any",) + tuple(str(i) for i in range(1, 17)), 4)
        self.mm_csort = tk.StringVar(value="Profit")
        pick("Sort", self.mm_csort, tuple(CARD_SORT), 9).bind(
            "<<ComboboxSelected>>", lambda e: (self.mm_sort_card(), self.root.after(20, self.root.focus_set)))
        self.mm_bsort = tk.StringVar(value="Top")
        self.mm_bsort_lab = tk.Label(fbar, text="Board", bg=P1, fg=C["muted"])
        self.mm_bsort_box = ttk.Combobox(fbar, textvariable=self.mm_bsort, values=("Top", "New"), state="readonly", width=5)
        self.mm_bsort_box.bind("<<ComboboxSelected>>", lambda e: (self.mm_board_fetch(), self.root.after(20, self.root.focus_set)))
        # P6 (2.108.0): + Add my own, and a ⋯ menu for Import file… / Download Format
        more = ttk.Button(fbar, text="⋯", width=3, command=lambda: self.mm_more_menu(more))
        more.pack(side="right", padx=(8, 0))
        Tooltip(more, "Import file… · Download Format")
        ttk.Button(fbar, text="+ Add my own", command=self.mm_add).pack(side="right", padx=(8, 0))
        from .style import flowify, flow_add
        flowify(fbar)                                        # 2.98.0: wraps in a narrow window
        flow_add(fbar, self.mm_bsort_lab, (12, 8), shown=False)
        flow_add(fbar, self.mm_bsort_box, shown=False)
        self.mm_fbar = fbar

        pane = ttk.PanedWindow(page, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        lfo = tk.Frame(pane, bg=P1)
        pane.add(lfo, weight=3)
        self.mm_list_head = SectionBar(lfo, "Strats")
        self.mm_list_head.pack(fill="x")
        self.mm_layout = SegBar(self.mm_list_head, ["Cards", "List"], command=lambda v: self.mm_layout_changed(),
                                size=9, pad=(8, 2))
        self.mm_list_head.add_right(self.mm_layout)
        lvp = Viewport(lfo)
        lvp.pack(fill="both", expand=True)
        left = lvp.body
        self.mm_pane = pane
        # 2.71.0: strats as cards (the default); the List is the sortable table - it also keeps the selection
        from .style import ScrollArea
        self.mm_cards = ScrollArea(left, bg=C["panel2"])
        self.mm_cards.inner.configure(padx=8, pady=8)
        self.mm_cards.bind("<Configure>", lambda e: self.root.after_idle(self.mm_cards_reflow))
        self.mm_card_w = {}
        self.mm_listf = tk.Frame(left, bg=C["panel2"])
        cols = (("name", "Strat", 170, "w"), ("type", "Type", 110, "w"),
                ("thoughts_per_click", "🧠 Thoughts/click", 104, "center"), ("clicks_per_hour", "🖱 Clicks/h", 80, "center"),
                ("profit", "Est. profit/h", 92, "center"), ("score", "▲", 44, "center"), ("origin", "By", 90, "w"))
        self.mm_tree = ttk.Treeview(self.mm_listf, columns=[c[0] for c in cols], show="tree headings", selectmode="browse")
        self.mm_tree.column("#0", width=24, minwidth=24, stretch=False, anchor="center")   # 2.95.0: the contributor icon
        self.mm_rep_names = {}
        self.rep_tree_hover(self.mm_tree, lambda iid: self.mm_rep_names.get(iid))
        for cid, title, w, anchor in cols:
            self.mm_tree.heading(cid, text=title, command=lambda c=cid: self.mm_sort_by(c))
            self.mm_tree.column(cid, width=w, minwidth=56, anchor=anchor, stretch=cid == "name")
        self.mm_tree.tag_configure("mine", foreground=C["green"])
        self.mm_tree.tag_configure("example", foreground=C["muted"])
        self.mm_tree.tag_configure("hidden", foreground=C["red"])
        sb = ttk.Scrollbar(self.mm_listf, orient="vertical", command=self.mm_tree.yview)
        self.mm_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.mm_tree.pack(side="left", fill="both", expand=True)
        self.mm_tree.bind("<<TreeviewSelect>>", lambda e: self.mm_pick())
        self.mm_tree.bind("<Button-3>", self.mm_menu)
        self.mm_empty = tk.Label(left, text="", bg=C["panel2"], fg=C["muted"], font=("Segoe UI", 10))
        self.mm_layout.pick(SETTINGS.get("mm_layout", "Cards") if SETTINGS.get("mm_layout") in ("Cards", "List")
                            else "Cards", notify=False)
        self.mm_layout_changed(save=False)

        rgo, right = chrome_section(pane, "Strat", padx=0, pady=0)              # 2.69.0
        pane.add(rgo, weight=2)
        acts = tk.Frame(right, bg=P2, padx=8, pady=8)
        acts.pack(fill="x")
        self.mm_btns = {}
        for key, text, cmd, style in (("track", "▶ Track in Strat Tracker", self.mm_track, "Primary.TButton"),
                                      ("vote", "▲ Upvote", self.mm_vote, "TButton"),
                                      ("post", "📤 Post to Community", self.mm_post, "TButton"),
                                      ("regex", "Copy regex", self.mm_copy_regex, "TButton"),
                                      ("more", "More ▾", self.mm_more, "TButton")):
            self.mm_btns[key] = ttk.Button(acts, text=text, command=cmd, style=style)
        # 2.71.0: your own numbers for this strat (from the Strat Tracker), always on top of its text
        self.mm_mine_box = tk.Frame(right, bg=P1, padx=12, pady=8, highlightthickness=1,
                                    highlightbackground=C["line"])
        self.mm_mine_box.pack(fill="x", padx=8, pady=(0, 8))
        self.mm_detail = tk.Text(right, bg=P2, fg=C["text"], relief="flat", wrap="word", padx=12, pady=8,
                                 font=("Segoe UI", 10), highlightthickness=0, cursor="arrow")
        dsb = ttk.Scrollbar(right, orient="vertical", command=self.mm_detail.yview)
        self.mm_detail.configure(yscrollcommand=dsb.set)
        dsb.pack(side="right", fill="y")
        self.mm_detail.pack(fill="both", expand=True)
        t = self.mm_detail
        t.tag_configure("title", font=("Segoe UI", 16, "bold"), foreground=C["text"], spacing3=2)
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
                self.mm_pane.sashpos(0, max(int(w * 0.55), min(720, w - 380)))
        except tk.TclError:
            pass

    # ---------------- 2.71.0: filter buttons and strat cards
    def _mm_chip(self, parent, text, on, cmd, empty=False):
        bg = C["accent"] if on else C["panel2"]
        fg = C["bg"] if on else (C["muted"] if empty else C["text"])
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=("Segoe UI", 9, "bold" if on else "normal"), padx=8, pady=4,
                     cursor="hand2", highlightthickness=1, highlightbackground=C["accent"] if on else C["line"])
        b.bind("<Button-1>", lambda e: cmd())
        if not on:
            b.bind("<Enter>", lambda e: b.config(bg=C["sel"]))
            b.bind("<Leave>", lambda e: b.config(bg=C["panel2"]))
        return b

    def mm_chips_paint(self):
        """The filter buttons, with how many strats each has (none: grayed)."""
        rows = getattr(self, "mm_chip_rows", None)
        if not rows:
            return
        n = {}
        for s in self.mm_strats:
            n[s.get("category")] = n.get(s.get("category"), 0) + 1
            n[(s.get("category"), s.get("type"))] = n.get((s.get("category"), s.get("type")), 0) + 1
        self.mm_counts = n
        for r in rows.values():
            for c in r.chips.winfo_children():
                c.destroy()
        cat, typ = self.mm_cat.get(), self.mm_type.get()
        self._mm_chip(rows["cat"].chips, f"All  {len(self.mm_strats)}", not cat, lambda: self.mm_filter(""))
        for c in MM.CATEGORIES:
            self._mm_chip(rows["cat"].chips, f"{c}  {n.get(c, 0)}" if n.get(c) else c, cat == c,
                          lambda c=c: self.mm_filter(c), empty=not n.get(c))
        if cat:
            self._mm_chip(rows["type"].chips, "Any", not typ, lambda: self.mm_filter(cat, ""))
            for t in MM.TAXONOMY.get(cat, ()):
                k = n.get((cat, t), 0)
                self._mm_chip(rows["type"].chips, f"{t}  {k}" if k else t, typ == t,
                              lambda t=t: self.mm_filter(cat, t), empty=not k)
            if not rows["type"].winfo_manager():
                rows["type"].pack(fill="x", after=rows["cat"])
        else:
            rows["type"].pack_forget()
        mx, cm = self.mm_max.get(), self.mm_cmax.get()
        self.root.after_idle(lambda: [self._mm_flow(r.chips) for r in rows.values()])
        self._mm_chip(rows["think"].chips, "Any", mx == "Any", lambda: (self.mm_max.set("Any"), self.mm_fill()))
        for w, _d in MM.THINKING.values():
            self._mm_chip(rows["think"].chips, w, mx == w, lambda w=w: (self.mm_max.set(w), self.mm_fill()))
        self._mm_chip(rows["clicks"].chips, "Any", cm == "Any", lambda: (self.mm_cmax.set("Any"), self.mm_fill()))
        for w in MM.CLICKS:
            self._mm_chip(rows["clicks"].chips, w, cm == w, lambda w=w: (self.mm_cmax.set(w), self.mm_fill()))
        self._mm_content_chips(rows["content"].chips)

    def _mm_content_chips(self, box):
        """2.78.0: the Content row - the first group (pinnacles and bosses) folds into a menu of check boxes, the
        others are buttons; picked ones show as chips with ×."""
        groups = list(MM.content_groups().items())
        picked = self.mm_content
        self._mm_chip(box, "Any", not picked, lambda: self.mm_content_pick(None))
        for i, (group, tags) in enumerate(groups):
            if i == 0:
                n = len(picked & set(tags))
                b = self._mm_chip(box, f"{group}{f'  {n}' if n else ''} ▾", bool(n),
                                  lambda g=group: self.mm_content_menu(g))
                self.mm_content_btn = b
                for t in sorted(picked & set(tags)):
                    self._mm_chip(box, f"{t}  ×", True, lambda t=t: self.mm_content_pick(t))
                continue
            for t in tags:
                self._mm_chip(box, f"{t}  ×" if t in picked else t, t in picked, lambda t=t: self.mm_content_pick(t))

    def mm_content_pick(self, tag):
        """A Content button: on / off (None: Any - all off)."""
        if tag is None:
            self.mm_content = set()
        else:
            self.mm_content ^= {tag}
        self.mm_chips_paint()
        self.mm_fill()

    def mm_content_menu(self, group):
        m = tk.Menu(self.root, tearoff=0)
        self.mm_content_vars = {}
        for t in MM.content_groups().get(group, ()):
            v = tk.BooleanVar(value=t in self.mm_content)
            self.mm_content_vars[t] = v
            m.add_checkbutton(label=t, variable=v, command=lambda t=t: self.mm_content_pick(t))
        b = getattr(self, "mm_content_btn", None)
        try:
            m.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())
        except (AttributeError, tk.TclError):
            pass
        return m

    def _mm_flow(self, f, width=None):
        """Lay the buttons out left to right, wrapping onto the next line when the row is full (2.71.0)."""
        try:
            width = width or f.winfo_width()
            kids = f.winfo_children()
        except tk.TclError:
            return
        if width < 50:
            width = 2000
        key = (width, tuple(str(k) for k in kids))
        if getattr(f, "_flow", None) == key:
            return
        f._flow = key
        x = y = 0
        h = max([k.winfo_reqheight() for k in kids] or [24])
        for k in kids:
            w = k.winfo_reqwidth()
            if x and x + w > width:
                x, y = 0, y + h + 4
            k.place(x=x, y=y)
            x += w + 6
        f.configure(height=y + h + 4)

    def mm_filter(self, cat, typ=""):
        """A category (and type) filter button: "" = all."""
        self.mm_cat.set(cat)
        self.mm_type.set(typ if cat else "")
        self.mm_tree.heading("type", text="Type" if cat else "Category › Type")
        self.mm_chips_paint()
        self.mm_fill()

    def mm_layout_changed(self, save=True):
        cards = self.mm_layout.get() == "Cards"
        (self.mm_listf if cards else self.mm_cards).pack_forget()
        (self.mm_cards if cards else self.mm_listf).pack(fill="both", expand=True)
        if save:
            SETTINGS["mm_layout"] = self.mm_layout.get()
            save_json("settings.json", SETTINGS)
        if cards:
            self.mm_cards_fill()

    def mm_sort_card(self):
        key, rev = CARD_SORT.get(self.mm_csort.get(), ("profit", True))
        self.mm_sort = (key, rev)
        self.mm_fill()

    def mm_cards_fill(self):
        """One card per strat in the list (same filters, same order): what it is, its name, the effort, the
        estimated profit, upvotes and who - and your own numbers when you've tracked it."""
        box = self.mm_cards.inner
        for c in box.winfo_children():
            c.destroy()
        self.mm_card_w = {}
        P2, P1 = C["panel2"], C["panel"]
        mine = self._mm_my_numbers_all()
        for iid in self.mm_tree.get_children():
            s = next((x for x in self.mm_strats if x["id"] + "|" + x["origin"] == iid), None)
            if s is None:
                continue
            post = s.get("_post") or {}
            card = tk.Frame(box, bg=P1, padx=12, pady=8, highlightthickness=1, highlightbackground=C["line"],
                            cursor="hand2")
            tk.Label(card, text=MM.type_text(s).upper(), bg=P1, fg=C["steel"], font=("Segoe UI", 9, "bold"),
                     anchor="w").pack(fill="x")
            tk.Label(card, text=("✔ " if post.get("voted") else "") + s["name"], bg=P1,
                     fg=C["green"] if s["origin"] == "mine" else C["text"], font=("Segoe UI", 12, "bold"), anchor="w",
                     justify="left", wraplength=230).pack(fill="x")
            tk.Label(card, text=f"🧠 {MM.thinking_word(s.get('thoughts_per_click'))}   🖱 {s.get('clicks_per_hour', '?')}",
                     bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(4, 0))
            content = [t for t in s.get("tags") or [] if t in MM.content_tags()]       # 2.78.0
            if content:
                tk.Label(card, text="◆ " + " · ".join(content[:3]) + (f" +{len(content) - 3}" if len(content) > 3 else ""),
                         bg=P1, fg=C["steel"], font=("Segoe UI", 9, "bold"), anchor="w", justify="left",
                         wraplength=230).pack(fill="x", pady=(4, 0))
            tk.Label(card, text=MM.money_text(s.get("est_profit"), " / h"), bg=P1, fg=C["good"],
                     font=("Segoe UI", 16, "bold"), anchor="w").pack(fill="x", pady=(8, 0))
            by = post.get("author", {}).get("name") or (s.get("author") if s["origin"] != "mine" else "me")
            foot = (f"▲ {post.get('score', 0)}   " if post else "") + (f"by {by}" if by else "") + \
                ("   HIDDEN" if post.get("hidden") else "")
            tk.Label(card, text=foot, bg=P1, fg=C["red"] if post.get("hidden") else C["muted"], font=("Segoe UI", 9),
                     anchor="w").pack(fill="x", pady=(4, 0))
            f = mine.get(s["id"])
            if f and f["runs"]:
                tk.Label(card, text=f"Yours: {f['runs']} runs" + (f" · {f['per_hour']:.1f} div / h"
                                                                    if f["per_hour"] is not None else ""),
                         bg=P1, fg=C["green"], font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(2, 0))
            for w in [card] + list(card.winfo_children()):
                w.bind("<Button-1>", lambda e, i=iid: self.mm_select(i))
                w.bind("<Button-3>", lambda e, i=iid: (self.mm_select(i), self.mm_menu(None, e.x_root, e.y_root)))
            self.mm_card_w[iid] = card
        self._mm_cols = None
        self.mm_cards_reflow()
        self.mm_cards_mark()

    def mm_cards_reflow(self):
        cards = list(self.mm_card_w.values())
        if not cards:
            return
        try:
            w = self.mm_cards.winfo_width()
        except tk.TclError:
            return
        cols = max(1, min(4, (w - 16) // 270)) if w > 50 else 2
        if cols == getattr(self, "_mm_cols", None):
            return
        self._mm_cols = cols
        box = self.mm_cards.inner
        for c in range(4):
            box.columnconfigure(c, weight=1 if c < cols else 0, uniform="card" if c < cols else "")
        for i, card in enumerate(cards):
            card.grid(row=i // cols, column=i % cols, sticky="nsew", padx=(0, 8), pady=(0, 8))

    def mm_cards_mark(self):
        sel = self.mm_tree.selection()
        for iid, card in self.mm_card_w.items():
            on = bool(sel) and iid == sel[0]
            try:
                card.config(highlightthickness=2 if on else 1, highlightbackground=C["accent"] if on else C["line"])
            except tk.TclError:
                pass

    def mm_select(self, iid):
        if self.mm_tree.exists(iid):
            self.mm_tree.selection_set(iid)
            self.mm_tree.see(iid)
            self.mm_pick()

    def _mm_my_numbers_all(self):
        """strat id -> your Strat Tracker figures for it (every setup that follows it)."""
        from . import ledger as L
        try:
            d = self.fl_data()
        except Exception:
            return {}
        by = {}
        for x in d.get("setups", []):
            if x.get("strat"):
                by.setdefault(x["strat"], set()).add(x["id"])
        return {sid: L.figures([l for l in d["logs"] if l["setup"] in ids]) for sid, ids in by.items()}

    def mm_mine_paint(self, s):
        """The detail's "Your numbers" box: what your Strat Tracker logged for this strat, or how to start."""
        box = getattr(self, "mm_mine_box", None)
        if box is None:
            return
        for c in box.winfo_children():
            c.destroy()
        P1 = C["panel"]
        if not s:
            box.pack_forget()
            return
        if not box.winfo_manager():
            box.pack(fill="x", padx=8, pady=(0, 8), before=self.mm_detail)
        f = self._mm_my_numbers_all().get(s["id"])
        tk.Label(box, text="YOUR NUMBERS", bg=P1, fg=C["steel"], font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
        if not f or not f["runs"]:
            tk.Label(box, text="Not tracked yet. ▶ Track in Strat Tracker makes a setup for it - then your real cost, "
                               "loot and profit per hour show here.", bg=P1, fg=C["muted"], font=("Segoe UI", 9),
                     anchor="w", justify="left", wraplength=360).pack(fill="x", pady=(2, 0))
            return
        row = tk.Frame(box, bg=P1)
        row.pack(fill="x", pady=(4, 0))
        for big, small in ((f"{f['runs']}", "runs"),
                           (f"{f['per_hour']:.1f}" if f["per_hour"] is not None else "-", "div / hour"),
                           (f"{f['profit_run']:+.2f}" if f.get("profit_run") is not None else "-", "div a run"),
                           (_hms(f["avg_run"]) if f.get("avg_run") else "-", "a run")):
            c = tk.Frame(row, bg=P1)
            c.pack(side="left", padx=(0, 24))
            tk.Label(c, text=big, bg=P1, fg=C["good"], font=("Segoe UI", 16, "bold"), anchor="w").pack(anchor="w")
            tk.Label(c, text=small, bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(anchor="w")

    # ---------------- 2.30.0: Official / Community / Mine
    def _mm_official_cache(self):
        from .config import load_json
        d = load_json("board_official.json", {})
        return d if isinstance(d, dict) else {}

    def mm_view_list(self):
        view = self.mm_view.get()
        if view == "Community":
            return list(self.mm_board) if B.configured() else []
        local = MM.all_strats()
        if view == "Mine":
            return [s for s in local if s["origin"] == "mine"]
        have = {s["id"] for s in local}
        promoted = [dict(s, origin="community") for s in self.mm_official.get("strats") or []
                    if not MM.validate(s) and s.get("id") not in have]
        return [s for s in local if s["origin"] != "mine"] + promoted

    def mm_view_changed(self):
        community = self.mm_view.get() == "Community"
        from .style import flow_show
        for w in (self.mm_bsort_lab, self.mm_bsort_box):
            flow_show(self.mm_fbar, w, community)            # 2.98.0: the row wraps (was pack / pack_forget)
        if community:
            self.mm_board_fetch()
        self.mm_sel = None
        self.mm_reload()

    def mm_reload(self, keep=None):
        self.mm_strats = self.mm_view_list()
        self.mm_chips_paint()                                # 2.71.0: the filter buttons (were the Browse tree)
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
            if self.mm_content and not self.mm_content & set(s.get("tags") or []):
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
        num = key in ("thoughts_per_click", "profit", "score")

        def k(s):
            if key == "score":
                return (s.get("_post") or {}).get("score", -1)
            if key == "profit":                             # 2.85.0: in divines (ex / chaos converted); 0 is 0
                v = MM.div_value(s.get("est_profit"))
                return v if v is not None else float("-inf")
            if key == "origin":                             # (the By column: the author's name)
                post = s.get("_post") or {}
                return str(post.get("author", {}).get("name") or (s.get("author") if s["origin"] != "mine" else "me")).lower()
            if key == "type":
                return MM.type_text(s).lower()
            if key == "clicks_per_hour":
                return list(MM.CLICKS).index(s["clicks_per_hour"]) if s.get("clicks_per_hour") in MM.CLICKS else 9
            return s.get(key, 0) if num else str(s.get(key, "")).lower()
        return sorted(out, key=k, reverse=rev)

    def mm_fill(self, keep=None):
        keep = keep or self.mm_sel
        tv = self.mm_tree
        tv.delete(*tv.get_children())
        rows = self.mm_rows()
        for s in rows:
            post = s.get("_post") or {}
            tags = (s["origin"],) + (("hidden",) if post.get("hidden") else ())
            by = post.get("author", {}).get("name") or (s.get("author") if s["origin"] != "mine" else "me")
            img = R.icon(self.root, post.get("author", {}).get("rep")) if post else None      # 2.95.0
            if img is not None:
                self.mm_rep_names[s["id"] + "|" + s["origin"]] = post["author"].get("name")
            tv.insert("", "end", iid=s["id"] + "|" + s["origin"], tags=tags, **({"image": img} if img is not None else {}),
                      values=(("✔ " if post.get("voted") else "") + s["name"],
                              s.get("type", "") if self.mm_cat.get() else MM.type_text(s),
                              MM.thinking_word(s.get("thoughts_per_click")), s.get("clicks_per_hour", ""),
                              MM.money_text(s.get("est_profit")), post.get("score", "") if post else "", by or ""))
        if rows:
            self.mm_empty.place_forget()
        else:
            view = self.mm_view.get()
            empty = {"Community": "No community strats yet - post one of yours (Mine > 📤 Post to Community)."
                                  if B.configured() else "The community board isn't set up yet.",
                     "Mine": "None yet - press + Add my own.",
                     "Official": "No strats yet - press ↻ Refresh."}[view]
            self.mm_empty.config(text="No strats match." if self.mm_strats else empty)
            self.mm_empty.place(relx=0.5, rely=0.3, anchor="center")
        if keep and tv.exists(keep):
            tv.selection_set(keep)
            tv.see(keep)
        elif rows:
            tv.selection_set(tv.get_children()[0])
        else:
            self.mm_show_detail(None)
        if self.mm_layout.get() == "Cards":                  # 2.71.0
            self.mm_cards_fill()

    def mm_sort_by(self, col):
        key = "thoughts_per_click" if col == "thoughts_per_click" else col
        cur, rev = self.mm_sort
        self.mm_sort = (key, not rev if cur == key else key in ("profit", "score"))
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
        self.mm_cards_mark()

    def mm_show_detail(self, s):
        t = self.mm_detail
        t.config(state="normal")
        t.delete("1.0", "end")
        for b in self.mm_btns.values():
            b.pack_forget()
        self.mm_mine_paint(s)                                     # 2.71.0
        if not s:
            t.insert("end", "Pick a strat on the left.", "meta")
            t.config(state="disabled")
            return
        post = s.get("_post") or {}
        show = ["track"] + (["vote"] if post else []) + (["post"] if s["origin"] == "mine" else []) + \
            (["regex"] if s.get("regex") else []) + ["more"]
        if post:
            self.mm_btns["vote"].config(text=f"{'▲ Upvoted' if post.get('voted') else '▲ Upvote'} ({post.get('score', 0)})")
        for key in show:
            self.mm_btns[key].pack(side="left", padx=(0, 8))
        t.insert("end", MM.type_text(s).upper() + "\n", "kicker")
        t.insert("end", s["name"] + "\n", "title")
        t.insert("end", "by ", "meta")
        self.rep_text_mark(t, post.get("author", {}) if post else {}, "meta")         # 2.95.0: ◆ the contributor icon
        t.insert("end", f"{post.get('author', {}).get('name') or s.get('author', '?')} · game {s.get('patch', '?')} · "
                        f"updated {s.get('updated', '?')} · {ORIGIN.get(s['origin'], '')}"
                        + (f" · ▲ {post.get('score', 0)}" if post else "")
                        + (" · HIDDEN" if post.get("hidden") else "") + "\n", "meta")
        extra = []                                                # 2.85.0
        if (post.get("based_on") or {}).get("id"):
            extra.append(f"based on “{post['based_on'].get('name') or 'another strat'}”")
        if post.get("pending"):
            extra.append(f"{post['pending']} change waiting for reviewers")
        if post.get("mine") and post.get("suggestions"):
            extra.append(f"{post['suggestions']} suggested edit{'s' if post['suggestions'] != 1 else ''} for you (right-click › "
                         "Suggestions)")
        if extra:
            t.insert("end", " · ".join(extra) + "\n", "meta")
        t.insert("end", s.get("summary", "") + "\n", "summary")
        tpc, cph = s.get("thoughts_per_click", 0), s.get("clicks_per_hour", "")
        word, why = MM.THINKING.get(tpc, ("?", ""))
        t.insert("end", "🧠 Thoughts per click  ", "h")
        t.insert("end", word, "stat")
        t.insert("end", f"  {why}\n", "meta")
        t.insert("end", "🖱 Clicks per hour  ", "h")
        t.insert("end", cph, "stat")
        t.insert("end", f"  {MM.CLICKS.get(cph, '')}\n", "meta")
        t.insert("end", "Est. profit  ", "h")
        t.insert("end", MM.money_text(s.get("est_profit"), " / h") + "     ", "stat")
        t.insert("end", "Est. cost  ", "h")
        t.insert("end", MM.money_text(s.get("est_cost")) + "\n", "stat")
        self.mm_cost_lines(t, s)                                  # 2.46.0: what it costs today
        if s.get("waystone_tiers"):
            t.insert("end", "Waystone tiers  ", "h")
            t.insert("end", MM.tiers_text(s["waystone_tiers"]) + "\n", "stat")
        tags = s.get("tags") or []
        for group, opts in MM.tag_groups().items():
            got = [x for x in opts if x in tags]
            if got:
                t.insert("end", group + "  ", "h")
                t.insert("end", " · ".join(got) + "\n", "chip")
        # (2.71.0: your Strat Tracker numbers are in the Your numbers box above)
        if isinstance(s.get("ledger"), dict):
            t.insert("end", "Author's Strat Tracker  ", "h")
            t.insert("end", MM.ledger_text(s["ledger"]) + "\n", "meta")
        self.mm_need_items(t, s)                                   # 2.78.0: W - regex + trade for each item
        self.mm_atlas(t, s)
        for key, title in (("requirements", "Requirements"), ("tablets", "Tablets"), ("waystones", "Waystones"),
                           ("craft_steps", "Craft steps"), ("setup", "Other setup"),
                           ("steps", "Steps"),
                           ("loot", "Loot to sell"), ("tips", "Tips"), ("risks", "Risks")):
            if key in ("tablets", "waystones") and s.get("items"):
                continue                                          # (the cards above have them)
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

    # ---------------- 2.78.0: W - what a strat needs, with a regex and a trade search for each item
    def mm_need_items(self, t, s):
        items = s.get("items") or []
        if not items:
            return
        P1 = C["panel"]
        now = MM.cost_now(s, self.mm_costs())
        prices = {}
        c = (self.mm_costs() or {}).get(s.get("id")) or {}
        for i in range(len(items)):
            p = (c.get("prices") or {}).get(str(i))
            if p is not None:
                prices[i] = p
        t.insert("end", "What you need - search or buy it\n", "h")
        self.mm_item_btns = []
        for i, it in enumerate(items):
            card = tk.Frame(t, bg=P1, padx=8, pady=8, highlightthickness=1, highlightbackground=C["line"])
            top = tk.Frame(card, bg=P1)
            top.pack(fill="x")
            kind = {"waystone": "WAYSTONE", "tablet": "TABLET"}.get(it.get("kind"), "ITEM")
            tk.Label(top, text=f"{kind} ×{it.get('count', 1)}", bg=P1, fg=C["muted"], font=("Segoe UI", 9, "bold"),
                     width=11, anchor="w").pack(side="left")
            last = f" · lasts {it.get('lasts')} runs" if int(it.get("lasts") or 1) > 1 else ""
            tk.Label(top, text=(it.get("name") or it["base"]) + last, bg=P1, fg=C["text"],
                     font=("Segoe UI", 10, "bold"), anchor="w").pack(side="left")
            price = prices.get(i)
            if it.get("key_mods"):
                tk.Label(card, text="\n".join("★ " + m for m in it["key_mods"]), bg=P1, fg=C["muted"],
                         font=("Segoe UI", 9), anchor="w", justify="left", wraplength=440).pack(fill="x", pady=(2, 0))
            row = tk.Frame(card, bg=P1)
            row.pack(fill="x", pady=(8, 0))
            rx = MM.item_regex([it])
            b1 = ttk.Button(row, text="Copy regex", style="Quiet.TButton",
                            command=lambda rx=rx, it=it: self.mm_item_copy(rx, it.get("name") or it["base"]))
            b1.pack(side="left")
            b2 = ttk.Button(row, text="Trade ↗", style="Quiet.TButton", command=lambda it=it: self.mm_item_trade(it))
            b2.pack(side="left", padx=(8, 0))
            if not rx:
                b1.state(["disabled"])
            self.mm_item_btns.append((b1, b2, rx))
            tk.Label(row, text=f"~{price:.2f} div today" if price is not None else
                     ("no recent listings" if now or c else ""), bg=P1, fg=C["good"] if price is not None else C["muted"],
                     font=("Segoe UI", 9)).pack(side="left", padx=8)
            t.window_create("end", window=card, stretch=1)
            t.insert("end", "\n")
        tabs = [it for it in items if it.get("kind") != "waystone" and it.get("key_mods")]
        if len(tabs) > 1:
            rx = MM.item_regex(tabs)
            b = ttk.Button(t, text="Copy one regex for all the tablets", style="Quiet.TButton",
                           command=lambda: self.mm_item_copy(rx, "all the tablets"))
            self.mm_all_tabs_btn = b
            t.window_create("end", window=b)
            t.insert("end", "  stash or vendor: Ctrl+F, Ctrl+V · Trade: the ★ mods, cheapest first\n", "meta")

    def mm_item_copy(self, rx, what):
        if not rx:
            return None
        self.root.clipboard_clear()
        self.root.clipboard_append(rx)
        self.own_clip = rx
        self._say(f"Copied the search for {what}. In game: Ctrl+F, Ctrl+V.", 6)
        return rx

    def mm_item_trade(self, it):
        url = MM.item_trade_link(SETTINGS.get("league"), it)
        webbrowser.open(url)
        return url

    # ---------------- 2.78.0: the atlas - trees, the author's screenshot (click: see it big), notes
    def mm_atlas(self, t, s):
        lines, ref = s.get("atlas") or [], s.get("atlas_image")
        if not lines and not ref:
            return
        t.insert("end", "Atlas / master setup\n", "h")
        if ref:
            from . import stratimg
            path = stratimg.path_of(ref) if ref.startswith("l:") else None
            if ref.startswith("b:"):
                path = self.mm_board_image(ref, s)
            img = self.strat_thumb(path, 320, 180) if path else None
            if img is not None:
                self.mm_atlas_img = img
                lbl = tk.Label(t, image=img, bg=C["panel"], cursor="hand2", highlightthickness=1,
                               highlightbackground=C["line"])
                lbl.bind("<Button-1>", lambda e, p=path: self.mm_atlas_big(p))
                t.window_create("end", window=lbl)
                t.insert("end", "\n")
                t.insert("end", "Click the picture to see it big.\n", "meta")
            else:
                t.insert("end", "loading the author's atlas screenshot…\n" if ref.startswith("b:") else
                         "The atlas screenshot is missing from this PC.\n", "meta")
        for line in lines:
            t.insert("end", "• " + line + "\n", "li")

    def mm_board_image(self, ref, s):
        """A board image: kept on this PC after the first download (in the background; the panel redraws)."""
        from . import stratimg
        import os
        p = os.path.join(stratimg.folder(), f"board_{ref[2:]}.jpg")
        if os.path.isfile(p):
            return p
        busy = getattr(self, "_mm_img_busy", set())
        if ref not in busy:
            self._mm_img_busy = busy | {ref}

            def done(path):
                self._mm_img_busy = getattr(self, "_mm_img_busy", set()) - {ref}
                cur = self.mm_current()
                if path and cur and cur.get("atlas_image") == ref:
                    self.mm_show_detail(cur)
            self._mm_bg(lambda: stratimg.path_of(ref), done)
        return None

    def mm_atlas_big(self, path):
        """The screenshot in its own window, as big as the screen allows."""
        try:
            from PIL import Image, ImageTk
            im = Image.open(path)
        except Exception:
            return None
        w = tk.Toplevel(self.root)
        w.title("Atlas")
        w.configure(bg=C["bg"])
        sw, sh = int(self.root.winfo_screenwidth() * 0.9), int(self.root.winfo_screenheight() * 0.85)
        im.thumbnail((sw, sh))
        img = ImageTk.PhotoImage(im, master=self.root)
        lbl = tk.Label(w, image=img, bg=C["bg"])
        lbl.image = img
        lbl.pack()
        w.bind("<Escape>", lambda e: w.destroy())
        lbl.bind("<Button-1>", lambda e: w.destroy())
        self.mm_atlas_win = w
        return w

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
        post, me = s.get("_post") or {}, B.signed_in() or {}
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84")
        m.add_command(label="▶ Track it in the Strat Tracker", command=self.mm_track)
        if s.get("regex"):
            m.add_command(label="Copy regex", command=self.mm_copy_regex)
        if post:
            m.add_command(label="▲ Remove my upvote" if post.get("voted") else "▲ Upvote", command=self.mm_vote)
        if s["origin"] == "mine":
            m.add_command(label="📤 Post to Community", command=self.mm_post)
        else:
            m.add_command(label="Copy to Mine (to change it)", command=self.mm_copy_mine)
        if post and not post.get("mine"):                          # 2.85.0
            m.add_command(label="✎ Suggest an edit…", command=self.mm_suggest)
        if post:
            m.add_command(label="History…", command=self.bm_history)
        if post.get("mine") and post.get("suggestions"):
            m.add_command(label=f"Suggestions waiting ({post['suggestions']})…", command=self.bm_inbox)
        m.add_command(label="Export…", command=self.mm_export)
        if s.get("items"):                                         # 2.46.0
            m.add_command(label="Check what it costs now", command=lambda: (self.mm_cost_check(True, s["id"]),
                                                                             self.mm_show_detail(s)))
        if s["origin"] == "mine" or post.get("mine"):
            m.add_separator()
            m.add_command(label="Edit", command=self.mm_edit)
            m.add_command(label="Delete", command=self.mm_delete)
        if post and not post.get("mine"):
            m.add_separator()
            m.add_command(label="⚑ Report…", command=self.mm_report)
        if post and me.get("admin"):
            m.add_separator()
            m.add_command(label="Admin: " + ("Un-hide" if post.get("hidden") else "Hide"),
                          command=lambda: self.mm_admin("unhide" if post.get("hidden") else "hide"))
            m.add_command(label="Admin: " + ("Remove from Official" if post.get("promoted") else "Promote to Official"),
                          command=lambda: self.mm_admin("unpromote" if post.get("promoted") else "promote"))
            m.add_command(label="Admin: Delete", command=lambda: self.mm_admin("delete"))
            m.add_command(label=f"Admin: Ban {post.get('author', {}).get('name', '')}",
                          command=lambda: self.mm_admin("ban"))
        m.tk_popup(x, y)

    # ---------------- the board (network work off the main thread; mm_sync = do it now, for tests)
    def _mm_bg(self, work, done):
        if getattr(self, "mm_sync", False):
            return done(work())
        threading.Thread(target=lambda: (lambda r: self.root.after(0, lambda: done(r)))(work()), daemon=True).start()

    def mm_refresh(self):
        self.mm_check_live(force=True)
        self.mm_board_fetch()
        self._mm_bg(B.official, self._mm_official_done)

    def _mm_official_done(self, res):
        ok, d = res
        if ok and isinstance(d, dict):
            self.mm_official = d
            save_json("board_official.json", d)
            if self.mm_view.get() == "Official":
                self.mm_reload()
            if hasattr(self, "mm_one_tree"):
                self.mm_one_fill()

    def mm_board_fetch(self, keep=None):
        if not B.configured():
            self.mm_live_lbl.config(text="The community board isn't set up yet.", fg=C["muted"])
            return
        sort = "new" if self.mm_bsort.get() == "New" else "top"
        admin = (B.signed_in() or {}).get("admin")
        self._mm_bg(lambda: (B.posts("strat", sort, limit=100, hidden=admin), B.posts("one", sort, limit=100, hidden=admin)),
                    lambda r: self._mm_board_done(r, keep))

    def _mm_board_done(self, res, keep=None):
        (ok, d), (ok1, d1) = res
        if not ok:
            self.mm_live_lbl.config(text=d, fg=C["red"])
            return
        # 2.85.0: a post that doesn't follow the layout (an older board let odd numbers in) isn't shown
        self.mm_board = [dict(p["data"], origin="board", _post=p) for p in d["posts"] if p["kind"] == "strat"
                         and not MM.validate(dict(p["data"]))]
        self.mm_board_ones = [dict(p["data"], origin="board", _post=p) for p in (d1 or {}).get("posts", [])] if ok1 else []
        self.mm_live_lbl.config(text=f"Community: {d['total']} strat{'s' if d['total'] != 1 else ''}", fg=C["muted"])
        if self.mm_view.get() == "Community":
            self.mm_reload(keep=keep)
        if hasattr(self, "mm_one_tree"):
            self.mm_one_fill()

    def mm_need_login(self, why):
        """No login: the first time you post / vote / report, pick a name and the board gives this install a key."""
        if B.signed_in():
            return False
        if not B.configured():
            self.app_toast("The community board isn't set up yet.", "Community")
            return True
        return not self.mm_join(why)

    def mm_join(self, why="use the Community board", name=None):
        from tkinter import simpledialog
        if name is None:
            name = simpledialog.askstring("Your community name", f"To {why}, pick a community name. Other players "
                                          "see it; it can change once every 7 days (2-24 letters or numbers). No "
                                          "password - this PC keeps a key. Not your account or character name.\n\n"
                                          "More: Settings › Privacy & community.", parent=self.root)
        if not name:
            return False
        ok, d = B.join(name.strip())
        self.mm_account_paint()
        if not ok:
            self.app_toast(d, "Community")
            return False
        self._say(f"You're on the board as {d.get('name', name)}.", 6)
        return True

    def mm_board_result(self, res, done_text=None, keep=None):
        ok, d = res
        if not ok:
            self.app_toast(d, "Community")
            return False
        if done_text:
            self._say(done_text, 6)
        self.mm_board_fetch(keep=keep)
        return True

    def mm_vote(self):
        s = self.mm_current()
        post = (s or {}).get("_post")
        if not post or self.mm_need_login("upvote"):
            return None
        self._mm_bg(lambda: B.vote(post["id"], not post.get("voted")),
                    lambda r: self.mm_board_result(r, keep=self.mm_sel))

    def mm_post(self):
        s = self.mm_current()
        if not s or s["origin"] != "mine" or not self.cm_need_sharing(self.mm_post) or self.mm_need_login("post"):
            return None
        data = {k: v for k, v in MM.tidy(s).items() if k not in ("id", "author")}
        if not self.mm_atlas_check(data):                         # 2.89.3: a public picture - look first
            return None

        def work():                                               # 2.78.0: the atlas screenshot goes up first
            from . import stratimg
            if str(data.get("atlas_image", "")).startswith("l:"):
                ok, ref = stratimg.upload(data["atlas_image"])
                if not ok:
                    return False, f"The atlas screenshot didn't upload ({ref})."
                data["atlas_image"] = ref
            meta = (SETTINGS.get("mm_meta") or {}).get(s["id"]) or {}
            if meta.get("post"):                               # 2.85.0: posted before - update it, no duplicate
                res = B.update(meta["post"], data)
                if res[0] or "only its author" not in str(res[1]) and "not found" not in str(res[1]):
                    return res
            res = B.post("strat", data, based_on=meta.get("based_on"))
            if res[0]:
                SETTINGS.setdefault("mm_meta", {}).setdefault(s["id"], {})["post"] = res[1]["post"]["id"]
                save_json("settings.json", SETTINGS)
            return res
        self._mm_bg(work, lambda r: self.mm_board_result(r, f"Posted \"{s['name']}\" to the Community board."))

    def mm_atlas_check(self, data):
        """2.89.3: a screenshot becomes public. Before it goes up: check it shows no character, account or guild
        names, chat or party. Yes = upload it, No = post without it, Cancel = stop. -> False when stopped."""
        if not str(data.get("atlas_image", "")).startswith("l:"):
            return True
        from tkinter import messagebox
        if hasattr(self, "mm_atlas_answer"):                      # (tests answer for you)
            a = self.mm_atlas_answer
        else:
            a = messagebox.askyesnocancel(
                "Your atlas screenshot will be public",
                "Anyone can see it. Check it shows NO character, account or guild names, no chat and no party - "
                "crop it to the atlas if it does.\n\nYes: upload it.  No: post without it.  Cancel: stop.",
                parent=self.root)
        if a is None:
            return False
        if not a:
            data.pop("atlas_image", None)
        return True

    def mm_report(self):
        s = self.mm_current()
        post = (s or {}).get("_post")
        if not post:
            return None
        return self._mm_report_post(post)

    def mm_admin(self, action):
        s = self.mm_current()
        post = (s or {}).get("_post")
        if not post:
            return None
        if action == "delete":
            work = lambda: B.delete(post["id"])  # noqa: E731
        elif action == "ban":
            work = lambda: B.ban(post["author"]["id"])  # noqa: E731
        else:
            work = lambda: B.admin(post["id"], action)  # noqa: E731
        self._mm_bg(work, lambda r: (self.mm_board_result(r, f"Done: {action}."),
                                     action in ("promote", "unpromote") and self._mm_bg(B.official, self._mm_official_done)))

    def mm_copy_mine(self):
        s = self.mm_current()
        if not s:
            return None
        c = {k: v for k, v in MM.tidy(s).items()}
        c["id"] = MM.slug("my-" + c["name"])
        for k in ("ledger", "atlas_image"):                  # 2.85.0: their numbers and screenshot aren't yours
            c.pop(k, None)
        c["author"] = (B.signed_in() or {}).get("name") or "me"
        post = s.get("_post") or {}
        meta = SETTINGS.setdefault("mm_meta", {})
        meta[c["id"]] = {"based_on": post.get("id")} if post.get("id") else {}
        save_json("settings.json", SETTINGS)
        MM.save_mine([m for m in MM.mine() if m["id"] != c["id"]] + [c])
        self.mm_show_mine(c["id"])
        return c

    def mm_show_mine(self, sid=None):
        if self.mm_view.get() != "Mine":
            self.mm_view.pick("Mine", notify=False)
            self.mm_view_changed()
        self.mm_reload(keep=(sid + "|mine") if sid else None)

    # ---------------- your board name (no login)
    def mm_account_paint(self):
        """The 👤 chips here and on Leaderboards, and Settings › Privacy & community (2.94.0)."""
        self.cy_paint()

    def mm_account_click(self):
        """2.94.0: the 👤 chip opens Settings › Privacy & community (the name's menu moved there)."""
        return self.community_open()

    def mm_rename(self, name=None):
        from tkinter import simpledialog
        name = name or simpledialog.askstring("Community board", "Your new name (it can change again in 7 days):",
                                              parent=self.root)
        if name:
            ok, d = B.rename(name.strip())
            self.app_toast("Done." if ok else d, "Community") if not ok else self._say("Name changed.", 4)
            self.mm_account_paint()
            self.mm_board_fetch()

    def mm_admin_key(self, key=None):
        from tkinter import simpledialog
        key = key or simpledialog.askstring("Community board", "The board's admin key (the ADMIN_KEY secret):",
                                            parent=self.root, show="•")
        if key:
            ok, d = B.become_admin(key)
            self.mm_account_paint()
            if ok:
                self._say("You're an admin on the board now (right-click a post for the admin tools).", 8)
                self.mm_board_fetch()
                try:                                         # 2.88.0: admin tools (the Listing order lab) show
                    self.shell.set_advanced(self.shell.advanced_on())
                except Exception:
                    pass
            else:
                self.app_toast(d, "Community")
            return ok

    def mm_leave(self):
        from tkinter import messagebox
        # 2.89.3: leaving can take everything with you
        a = messagebox.askyesnocancel("Community board", "Leave the board and DELETE everything of yours on it - your "
                                      "name, strats, pictures, votes, suggestions and leaderboard times?\n\nYes: delete "
                                      "it all.  No: just forget this account on this PC (your posts stay).",
                                      parent=self.root)
        if a is None:
            return
        if a:
            ok, d = B.delete_me()
            self._say("Done - nothing of yours is on the board any more." if ok else f"Couldn't delete it ({d}).", 8)
        else:
            B.sign_out()
        self.mm_account_paint()
        self.mm_board_fetch()

    # ---------------- 2.46.0: what a strat costs today (stratcost.py: one search per item, once a day)
    def mm_costs(self):
        if getattr(self, "_mm_costs", None) is None:
            from .stratcost import costs
            self._mm_costs = costs()
        return self._mm_costs

    def mm_cost_check(self, force=False, only=None):
        """Queue the strats whose cost wasn't checked today (or one strat now: force=True, only=its id)."""
        from .stratcost import due
        league = SETTINGS.get("league") or ""
        if not league:
            return 0
        n = 0
        for s in self.fl_all_strats():                         # 2.85.0: Community and Official too
            if only and s["id"] != only:
                continue
            if s.get("items") and (force or due(s, self.mm_costs(), league)):
                if s["id"] in getattr(self, "_mm_cost_busy", set()):
                    continue
                self._mm_cost_busy = getattr(self, "_mm_cost_busy", set()) | {s["id"]}
                self.engine.strat_cost_start(s, league)
                n += 1
        return n

    def ev_strat_cost(self, sid, i, price, info):
        c = self.mm_costs().setdefault(sid, {})
        c.setdefault("prices", {})[str(i)] = price
        c.setdefault("info", {})[str(i)] = info

    def ev_strat_cost_finished(self, sid, league):
        from .stratcost import save_costs
        c = self.mm_costs().setdefault(sid, {})
        c.update(at=time.time(), league=league)
        save_costs(self.mm_costs())
        self._mm_cost_busy = getattr(self, "_mm_cost_busy", set()) - {sid}
        cur = self.mm_current()
        if cur and cur["id"] == sid:
            self.mm_show_detail(cur)

    def mm_cost_lines(self, t, s):
        if not s.get("items"):
            return
        now = MM.cost_now(s, self.mm_costs())
        busy = s["id"] in getattr(self, "_mm_cost_busy", set())
        t.insert("end", "Cost now  ", "h")
        if now:
            total, parts, at = now
            ago = max(0, time.time() - (at or time.time()))
            when = "today" if ago < 86400 else f"{int(ago // 86400)} days ago"
            t.insert("end", f"{total:.2f} div a run", "stat")
            t.insert("end", f"  (trade site, checked {when}{' - checking again…' if busy else ''})\n", "meta")
        else:
            t.insert("end", "checking the trade site…\n" if busy else
                     "not checked yet (once a day while Money Makers is open)\n", "meta")

    def mm_on_show(self):
        self.mm_check_live(force=False)
        try:
            self.mm_cost_check()                                  # 2.46.0: once a day, strats that list their items
        except Exception:
            self.log_error("checking what strats cost")
        self.mm_account_paint()
        if B.configured() and not getattr(self, "_mm_official_asked", False):
            self._mm_official_asked = True
            self._mm_bg(B.official, self._mm_official_done)

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

    def mm_export(self):
        s = self.mm_current()
        if not s:
            return
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".csv", initialfile=s["id"] + ".csv",
                                            filetypes=[("Strat guide (CSV - Excel, Google Sheets)", "*.csv"),
                                                       ("Strat (JSON)", "*.json")])
        return self.mm_write_strat(s, path)

    def mm_write_strat(self, s, path):
        """2.46.0: a strat guide is a CSV file (the same layout as the Strat Tracker's numbers); JSON for the repo."""
        if not path:
            return None
        from . import board as _B
        from .privacy import known_names
        mine = s.get("origin") == "mine"
        s = MM.tidy(s)                                       # 2.89.3: a file you might share - your board name or "me",
        if mine or str(s.get("author") or "") in known_names():   # never an account / character name
            s["author"] = (_B.signed_in() or {}).get("name") or "me"
        if path.lower().endswith(".json"):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(s, f, indent=2, ensure_ascii=False)
        elif path.lower().endswith(".txt"):
            with open(path, "w", encoding="utf-8", newline="\r\n") as f:
                f.write(MM.to_text(s))
        else:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:      # (Excel reads UTF-8 with the BOM)
                f.write(MM.to_csv(s))
        self._say(f"Saved {path}", 6)
        return path

    def mm_more_menu(self, btn):
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84")
        m.add_command(label="Import file…", command=self.mm_import)
        m.add_command(label="⬇ Download Format", command=self.mm_download_format)
        m.tk_popup(btn.winfo_rootx(), btn.winfo_rooty() + btn.winfo_height())
        return m

    def mm_download_format(self, path=None):
        """The blank standard layout as a CSV file (2.46.0; opens in Excel / Google Sheets, the "note" column says
        what goes in each row): fill it in, then Import file… - or attach it to a Strategy issue on GitHub."""
        path = path or filedialog.asksaveasfilename(parent=self.root, defaultextension=".csv",
                                                    initialfile="money-maker-strat-template.csv",
                                                    filetypes=[("Strat guide (CSV)", "*.csv")])
        if not path:
            return None
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(MM.to_csv(None))
        self.app_toast(f"Saved the strat template:\n{path}\n\nOpen it in Excel or Google Sheets, fill in the value "
                       "column (the note column says what goes there), then press Import file… here (or attach it to "
                       "a Strategy issue on GitHub to share it).", "Download Format")
        return path

    def mm_import(self, path=None):
        path = path or filedialog.askopenfilename(parent=self.root, filetypes=[("Strat", "*.csv *.txt *.json")])
        if not path:
            return None
        try:
            with open(path, encoding="utf-8-sig") as f:
                raw = f.read()
            d = MM.read_any(raw)                                     # 2.46.0: CSV, the older .txt, or JSON
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
        self.mm_show_mine()
        msg = f"Added {added} strat{'s' if added != 1 else ''} to Mine."
        if bad:
            msg += "\nLeft out (not in the standard layout): " + "; ".join(bad[:3])
        self.app_toast(msg, "Import strat")
        return added

    def mm_delete(self):
        s = self.mm_current()
        post = (s or {}).get("_post")
        if post and post.get("mine"):
            return self._mm_bg(lambda: B.delete(post["id"]), lambda r: self.mm_board_result(r, "Deleted."))
        if s and s["origin"] == "mine":
            MM.save_mine([m for m in MM.mine() if m["id"] != s["id"]])
            self.mm_sel = None
            self.mm_reload()

    def mm_add(self):
        self.mm_form(MM.new_strat())

    def mm_edit(self):
        s = self.mm_current()
        if s and (s["origin"] == "mine" or (s.get("_post") or {}).get("mine")):
            self.mm_form(dict(s))

    def mm_form(self, s, suggest=False):
        """Add / edit one of your strats - exactly the fields of the standard layout. 2.85.0: suggest=True - someone
        else's Community strat: your version goes to its author (with a note) instead."""
        from .style import ScrollArea
        P1 = C["panel"]
        win = tk.Toplevel(self.root, bg=P1)
        win.title("Suggest an edit" if suggest else "Your strat")
        win.transient(self.root)
        self.mm_form_win = win
        sa = ScrollArea(win, P1)
        sa.pack(fill="both", expand=True)
        f = tk.Frame(sa.inner, bg=P1, padx=16, pady=8)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        v = {}
        r = 0

        def head(text):
            nonlocal r
            tk.Label(f, text=text, bg=P1, fg=C["accent"], font=("Segoe UI", 10, "bold"), anchor="w").grid(
                row=r, column=0, columnspan=2, sticky="w", pady=(8, 2))
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
                ttk.Checkbutton(box, text=opt, variable=var).grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 16))
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
        tpc0 = s.get("thoughts_per_click") if s.get("thoughts_per_click") in MM.THINKING else 2
        combo("tpc", "🧠 Thoughts per click *", think, think[tpc0 - 1])
        clicks = [f"{w} - {d}" for w, d in MM.CLICKS.items()]
        cur = next((c for c in clicks if c.startswith(str(s.get("clicks_per_hour")) + " ")), clicks[1])
        combo("cph", "🖱 Clicks per hour *", clicks, cur)
        head("Tags (everything else about it)")
        v["tags"] = {}
        for group, opts in MM.tag_groups().items():                 # 2.78.0: + the Content groups
            checks("tags:" + group, group, opts, s.get("tags"))
            v["tags"].update(v["tags:" + group])
        head("Numbers (estimates)")
        entry("tiers", "Waystone tiers (1-16, e.g. 14-16)",
              "" if not wt else MM.tiers_text(wt).replace("T", ""), 10)
        entry("inv", "Est. cost per run (e.g. 2 div, 50 ex)", MM.money_edit(inv), 16)
        entry("profit", "Est. profit per hour (e.g. 5-10 div)", MM.money_edit(p), 16)
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
        srcs = s.get("sources") or []                             # 2.85.0: every link (only the first was kept)
        s = dict(s, _src_lines=[x.get("url", "") for x in srcs])
        lines("_src_lines", "Source links (one per line)")
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
                out["est_profit"] = MM.money_parse(v["profit"].get())          # 2.85.0: units kept, negatives fine
                out["est_cost"] = MM.money_parse(v["inv"].get(), single=True)
                rng = MM._num_range(v["tiers"].get().lower().replace("t", ""))
                out["waystone_tiers"] = {"min": int(rng[0]), "max": int(rng[1])} if rng else None
            except (TypeError, ValueError):
                msg.config(text="Tiers, cost and profit: a number or a range (5-10), with div, ex or chaos.", fg=C["red"])
                return
            out.pop("_src_lines", None)
            titles = {x.get("url"): x.get("title") or x.get("url") for x in srcs}
            urls = [ln.strip() for ln in v["_src_lines"].get("1.0", "end").split("\n") if ln.strip()]
            out["sources"] = [{"title": titles.get(u, u), "url": u} for u in urls]
            out["patch"] = out["patch"] or "?"
            out["updated"] = time.strftime("%Y-%m-%d")
            if not s.get("name"):
                out["id"] = MM.slug("my-" + out["name"])
            post = s.get("_post")
            out = MM.tidy(out)
            probs = MM.validate(out)
            if probs:
                msg.config(text="Not saved: " + probs[0], fg=C["red"])
                return
            if post and suggest:                             # 2.85.0: someone else's: a suggestion for its author
                from tkinter import simpledialog
                note = simpledialog.askstring("Suggest an edit", "What did you change, and why? (the author reads this)",
                                              parent=win)
                if not note or len(note.strip()) < 3:
                    msg.config(text="Not sent: say in a few words what you changed and why.", fg=C["red"])
                    return
                data = {k: v for k, v in out.items() if k not in ("id", "author")}
                ok, d = self.bm_send_suggestion(post, data, note.strip())
                if not ok:
                    msg.config(text="Not sent: " + d, fg=C["red"])
                    return
                win.destroy()
                return
            if post:                                         # your Community post: saved on the board
                data = {k: v for k, v in out.items() if k not in ("id", "author")}
                ok, d = B.update(post["id"], data)
                if not ok:
                    msg.config(text="Not saved: " + d, fg=C["red"])
                    return
                win.destroy()
                if isinstance(d, dict) and d.get("pending"):  # 2.85.0: an Official post - reviewers look first
                    self._say("Saved - it's an Official strat, so the change goes live once 2 reviewers approve it "
                              "(History shows it waiting).", 12)
                self.mm_board_fetch(keep=s["id"] + "|board")
                return
            mine = [m for m in MM.mine() if m["id"] not in (s.get("id"), out["id"])] + [out]
            MM.save_mine(mine)
            win.destroy()
            self.mm_show_mine(out["id"])

        btns = tk.Frame(win, bg=P1, padx=16, pady=8)
        btns.pack(fill="x", side="bottom", before=sa)
        ttk.Button(btns, text="Save", style="Primary.TButton", command=save).pack(side="right")
        ttk.Button(btns, text="Cancel", command=win.destroy, style="Quiet.TButton").pack(side="right", padx=8)
        win.bind("<Escape>", lambda e: win.destroy())
        self.mm_form_save = save
        self.mm_form_vars = v
        win.update_idletasks()
        win.geometry(f"{min(820, f.winfo_reqwidth() + 40)}x{min(720, f.winfo_reqheight() + 70)}")
        place_near(self.root, win, self.root.winfo_rootx() + 80, self.root.winfo_rooty() + 40)
        return win

    # ---------------- the run tracker (its own, simple)
    def mm_track(self):
        """A strat's "▶ Strat Tracker": its setup there (made if there's none yet)."""
        s = self.mm_current()
        self.mm_page.pick("Strat Tracker", notify=False)
        self.mm_show_page()
        if s:
            self.fl_for_strat(s["id"])

    # ---------------- Lucrative Strats: simple one-liners
    def mm_build_oneliners(self, page):
        P1 = C["panel"]
        bar = tk.Frame(page, bg=P1, padx=8, pady=8)
        bar.pack(fill="x")
        tk.Label(bar, text="Search", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 8))
        self.mm_one_q = tk.StringVar()
        self.mm_one_q.trace_add("write", lambda *_a: self.root.after_idle(self.mm_one_fill))
        ttk.Entry(bar, textvariable=self.mm_one_q, width=26).pack(side="left")
        for text, cmd, style in (("+ Add a one-liner", self.mm_one_add, "Primary.TButton"),
                                 ("📤 Post", self.mm_one_post, "TButton"), ("▲ Upvote", self.mm_one_vote, "TButton"),
                                 ("Copy text", self.mm_one_copy, "TButton")):
            ttk.Button(bar, text=text, command=cmd, style=style).pack(side="right", padx=(8, 0))
        tk.Label(page, text="Quick money makers in one line - no guide needed. Official ones come with the app, "
                            "Community ones from other players; 📤 Post shares yours.", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=12, pady=(0, 8))
        box = tk.Frame(page, bg=P1)
        box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        cols = (("text", "Strat", 560, "w"), ("mech", "Type / tags", 150, "w"), ("score", "▲", 44, "center"),
                ("by", "By", 110, "w"), ("origin", "From", 90, "center"))
        self.mm_one_tree = ttk.Treeview(box, columns=[c[0] for c in cols], show="headings", selectmode="browse")
        for cid, title, w, anchor in cols:
            self.mm_one_tree.heading(cid, text=title)
            self.mm_one_tree.column(cid, width=w, minwidth=40, anchor=anchor, stretch=cid == "text")
        self.mm_one_tree.tag_configure("mine", foreground=C["green"])
        self.mm_one_tree.tag_configure("hidden", foreground=C["red"])
        sb = ttk.Scrollbar(box, orient="vertical", command=self.mm_one_tree.yview)
        self.mm_one_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.mm_one_tree.pack(side="left", fill="both", expand=True)
        self.mm_one_tree.bind("<Button-3>", self.mm_one_menu)
        self.mm_one_tree.bind("<Double-1>", lambda e: self.mm_one_copy())
        self.mm_one_tree.bind("<Delete>", lambda e: self.mm_one_delete())
        self.mm_one_empty = tk.Label(box, text="", bg=P1, fg=C["muted"], font=("Segoe UI", 10))

    def mm_one_items(self):
        have = {o["id"] for o in MM.oneliners()}
        promoted = [dict(o, origin="community") for o in self.mm_official.get("oneliners") or []
                    if o.get("id") not in have]
        return MM.oneliners() + promoted + list(getattr(self, "mm_board_ones", []))

    def mm_one_fill(self):
        tv = self.mm_one_tree
        tv.delete(*tv.get_children())
        q = self.mm_one_q.get().strip().lower()
        self.mm_ones = {}
        for o in self.mm_one_items():
            if q and q not in o.get("text", "").lower() + " " + " ".join(o.get("tags") or []).lower():
                continue
            iid = o["id"] + "|" + o["origin"]
            post = o.get("_post") or {}
            self.mm_ones[iid] = o
            tv.insert("", "end", iid=iid, tags=(o["origin"],) + (("hidden",) if post.get("hidden") else ()),
                      values=(("✔ " if post.get("voted") else "") + o["text"],
                              MM.type_text(o) if o.get("category") else ", ".join(o.get("tags") or []),
                              post.get("score", "") if post else "",
                              post.get("author", {}).get("name") or o.get("author", ""), ORIGIN.get(o["origin"], "")))
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

    def mm_one_post(self):
        o = self.mm_one_current()
        if not o or o["origin"] != "mine":
            self._say("Pick one of your own one-liners (From: Mine) to post it.", 6)
            return None
        if not self.cm_need_sharing(self.mm_one_post) or self.mm_need_login("post"):
            return None
        data = {k: v for k, v in MM.tidy_one(o).items() if k not in ("id", "author")}
        self._mm_bg(lambda: B.post("one", data), lambda r: self.mm_board_result(r, "Posted to the Community board."))

    def mm_one_vote(self):
        o = self.mm_one_current()
        post = (o or {}).get("_post")
        if not post:
            self._say("Upvotes are for Community one-liners.", 5)
            return None
        if self.mm_need_login("upvote"):
            return None
        self._mm_bg(lambda: B.vote(post["id"], not post.get("voted")), lambda r: self.mm_board_result(r))

    def mm_one_delete(self):
        o = self.mm_one_current()
        post = (o or {}).get("_post")
        if post and (post.get("mine") or (B.signed_in() or {}).get("admin")):
            return self._mm_bg(lambda: B.delete(post["id"]), lambda r: self.mm_board_result(r, "Deleted."))
        if o and o["origin"] == "mine":
            MM.save_mine_one([x for x in MM.mine_one() if x["id"] != o["id"]])
            self.mm_one_fill()

    def mm_one_menu(self, e):
        row = self.mm_one_tree.identify_row(e.y)
        if not row:
            return
        self.mm_one_tree.selection_set(row)
        o = self.mm_one_current()
        post, me = (o or {}).get("_post") or {}, B.signed_in() or {}
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84")
        m.add_command(label="Copy text", command=self.mm_one_copy)
        if post:
            m.add_command(label="▲ Remove my upvote" if post.get("voted") else "▲ Upvote", command=self.mm_one_vote)
        if o and o["origin"] == "mine":
            m.add_command(label="📤 Post to Community", command=self.mm_one_post)
        if (o and o["origin"] == "mine") or post.get("mine"):
            m.add_separator()
            m.add_command(label="Delete", command=self.mm_one_delete)
        if post and not post.get("mine"):
            m.add_command(label="⚑ Report…", command=lambda: self._mm_report_post(post))
        if post and me.get("admin"):
            m.add_separator()
            for label, act in (("Un-hide" if post.get("hidden") else "Hide", "unhide" if post.get("hidden") else "hide"),
                               ("Remove from Official" if post.get("promoted") else "Promote to Official",
                                "unpromote" if post.get("promoted") else "promote")):
                m.add_command(label="Admin: " + label, command=lambda a=act: self._mm_bg(
                    lambda: B.admin(post["id"], a), lambda r: (self.mm_board_result(r, f"Done: {a}."),
                                                              self._mm_bg(B.official, self._mm_official_done))))
            m.add_command(label="Admin: Delete", command=lambda: self._mm_bg(lambda: B.delete(post["id"]),
                                                                             lambda r: self.mm_board_result(r, "Deleted.")))
        m.tk_popup(e.x_root, e.y_root)

    def _mm_report_post(self, post):
        from tkinter import simpledialog
        if self.mm_need_login("report"):
            return None
        why = simpledialog.askstring("Report", "What's wrong with it? (spam, wrong, offensive ...)", parent=self.root)
        if why is not None:
            self._mm_bg(lambda: B.report(post["id"], why), lambda r: self.mm_board_result(r, "Reported - thanks."))

    # ---------------- Tablet Craft Helper quick reference
    def mm_build_tablets(self, page):
        P1, P2 = C["panel"], C["panel2"]
        pane = ttk.PanedWindow(page, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=8, pady=8)
        lfo, left = chrome_section(pane, "How to craft a tablet")              # 2.69.0
        pane.add(lfo, weight=2)
        for i, (when, what) in enumerate(MM.TABLET_FLOW, 1):
            row = tk.Frame(left, bg=P2)
            row.pack(fill="x", pady=(8, 0))
            tk.Label(row, text=str(i), bg=C["accent"], fg="#10141c", font=("Segoe UI", 10, "bold"), width=2).pack(
                side="left", anchor="n")
            col = tk.Frame(row, bg=P2)
            col.pack(side="left", fill="x", expand=True, padx=(8, 0))
            tk.Label(col, text=when, bg=P2, fg=C["text"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
            lab = tk.Label(col, text=what, bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left")
            lab.pack(fill="x")
            lab.bind("<Configure>", lambda e, w=lab: w.config(wraplength=max(150, e.width - 4)))
        tk.Frame(left, bg=C["line"], height=1).pack(fill="x", pady=12)
        tk.Label(left, text="CHECK YOUR TABLET", bg=P2, fg=C["steel"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(left, text="Hover a tablet in game, press Ctrl+C, then:", bg=P2, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(2, 8))
        ttk.Button(left, text="Check my tablet", style="Primary.TButton", command=self.mm_tab_check).pack(anchor="w")
        self.mm_tab_advice = tk.Label(left, text="", bg=P2, fg=C["text"], font=("Segoe UI", 10, "bold"), anchor="w",
                                      justify="left")
        self.mm_tab_advice.pack(fill="x", pady=(8, 0))
        self.mm_tab_advice.bind("<Configure>", lambda e: self.mm_tab_advice.config(wraplength=max(150, e.width - 4)))

        right = tk.Frame(pane, bg=P1)
        pane.add(right, weight=3)
        bar = tk.Frame(right, bg=P1)
        bar.pack(fill="x", pady=(0, 8))
        tk.Label(bar, text="Tablet", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 8))
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
                 anchor="w", justify="left", wraplength=560).pack(fill="x", pady=(0, 8))
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
