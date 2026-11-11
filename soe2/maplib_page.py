"""Session tracker > Map library (2.32.0): every endgame area with your rank, the community's rank and your runs.
Data and ranks: maplib.py."""
import tkinter as tk
from tkinter import filedialog, ttk

from . import buglog
from . import maplib as ML
from .style import over_app
from .style import C, Tooltip, place_near
from .chrome import SectionBar, Viewport

RANK_TAG = {"S": "s", "A": "a", "B": "b", "C": "c", "D": "d", "Avoid": "avoid"}


class MapLibraryPage:
    """Mixed into App."""

    def build_map_library(self, body):
        P1 = C["panel"]
        page = tk.Frame(body, bg=P1)
        bar = tk.Frame(page, bg=P1)
        bar.pack(fill="x", pady=(0, 8))
        tk.Label(bar, text="Search", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 8))
        self.ml_q = tk.StringVar()
        self.ml_q.trace_add("write", lambda *_a: self.root.after_idle(self.ml_fill))
        ttk.Entry(bar, textvariable=self.ml_q, width=18).pack(side="left")

        def pick(label, var, values, width):
            tk.Label(bar, text=label, bg=P1, fg=C["muted"]).pack(side="left", padx=(12, 8))
            cb = ttk.Combobox(bar, textvariable=var, values=values, state="readonly", width=width)
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>", lambda e: (self.ml_fill(), self.root.after(20, self.root.focus_set)))
        self.ml_kind, self.ml_rankf = tk.StringVar(value="All"), tk.StringVar(value="Any")
        pick("Kind", self.ml_kind, ("All",) + ML.KINDS, 11)
        pick("Rank", self.ml_rankf, ("Any", "Ranked", "Not ranked") + ML.RANKS, 10)
        self.ml_run_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Only maps I've run", variable=self.ml_run_only, command=self.ml_fill).pack(
            side="left", padx=(12, 0))
        exp = ttk.Button(bar, text="Share ▾", command=lambda: self.ml_share_menu(exp))
        exp.pack(side="right")
        # P5 (2.108.0): ranking is one compact group in the toolbar - S A B C D ✖, then Clear
        ttk.Button(bar, text="Clear", style="Quiet.TButton", command=lambda: self.ml_set(None)).pack(
            side="right", padx=(0, 8))
        grp = tk.Frame(bar, bg=C["line"], padx=1, pady=1)
        grp.pack(side="right", padx=(0, 8))
        cols = {"S": "#ffcf40", "A": "#ffd9a8", "B": C["text"], "C": C["text"], "D": C["muted"], "Avoid": C["red"]}
        self.ml_rank_btns = {}
        for i, r in enumerate(ML.RANKS):
            lab = tk.Label(grp, text="✖" if r == "Avoid" else r, bg=C["panel2"], fg=cols.get(r, C["text"]),
                           font=("Segoe UI", 10, "bold"), width=3, pady=4, cursor="hand2")
            lab.pack(side="left", padx=(1 if i else 0, 0))
            lab.bind("<Button-1>", lambda e, rr=r: self.ml_set(rr))
            lab.bind("<Enter>", lambda e, w=lab: w.config(bg=C["panel"]))
            lab.bind("<Leave>", lambda e, w=lab: w.config(bg=C["panel2"]))
            Tooltip(lab, "Avoid" if r == "Avoid" else f"Rank the selected {r}")
            self.ml_rank_btns[r] = lab
        tk.Label(bar, text="Rank", bg=P1, fg=C["muted"]).pack(side="right", padx=(12, 8))
        from .style import flowify
        flowify(bar)
        # 2.120.0 (UX pass 2: each setting where it's used): the rank cards' switch (was Overlay ↳ Overlay Settings › Options)
        arow = tk.Frame(page, bg=P1)
        arow.pack(fill="x", pady=(0, 8))
        self.ml_rank_ask = tk.BooleanVar(value=self.rank_ask_on())
        ttk.Checkbutton(arow, text="Ask me to rank a map I haven't ranked (a card when I leave it)",
                        variable=self.ml_rank_ask, style="Card.TCheckbutton",
                        command=lambda: self.rank_ask_set(bool(self.ml_rank_ask.get()))).pack(side="left")

        SectionBar(page, "Maps").pack(fill="x")               # 2.69.0: the list under a strip, sunken
        bvp = Viewport(page)
        bvp.pack(fill="both", expand=True)
        box = bvp.body
        cols = (("map", "Map", 200, "w"), ("kind", "Kind", 90, "w"), ("rank", "Your rank", 90, "center"),
                ("com", "Community", 110, "center"), ("runs", "Your runs", 84, "e"), ("avg", "Avg time", 80, "e"),
                ("best", "Best", 70, "e"))
        tv = ttk.Treeview(box, columns=[c[0] for c in cols], show="headings", selectmode="extended", height=8)
        self.ml_sort = ("map", False)
        for cid, title, w, anchor in cols:
            tv.heading(cid, text=title, command=lambda c=cid: self.ml_sort_by(c))
            tv.column(cid, width=w, minwidth=50, anchor=anchor, stretch=cid == "map")
        for r, tag in RANK_TAG.items():
            tv.tag_configure(tag, foreground={"s": "#ffcf40", "a": "#ffd9a8", "b": C["text"], "c": C["text"],
                                              "d": C["muted"], "avoid": C["red"]}[tag])
        tv.tag_configure("learned", font=("Segoe UI", 10, "italic"))
        sb = ttk.Scrollbar(box, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tv.pack(side="left", fill="both", expand=True)
        tv.bind("<Button-3>", self.ml_menu)
        for key, r in (("s", "S"), ("a", "A"), ("b", "B"), ("c", "C"), ("d", "D"), ("x", "Avoid")):
            tv.bind(f"<KeyPress-{key}>", lambda e, rr=r: self.ml_set(rr))
        tv.bind("<BackSpace>", lambda e: self.ml_set(None))
        self.ml_tv = tv
        self.ml_info = tk.Label(page, text="", bg=P1, fg=C["text"], font=("Segoe UI", 9, "bold"), anchor="w")
        self.ml_info.pack(fill="x", pady=(4, 0))
        tk.Label(page, text="Rank maps S (best) to D, or ✖ Avoid - right-click, the buttons, or press S A B C D / X. "
                            "Your ranks also count toward the Community column (anonymous). Areas the game adds later "
                            "are learned the first time you enter them (in italics).", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w", justify="left", wraplength=760).pack(fill="x", pady=(4, 0))
        return page

    # ---------------- the list
    def ml_rows(self):
        from .tracker import map_stats
        lib, mine, com = ML.library(), ML.ranks(), ML.community()
        try:
            st = map_stats(self.tk_sessions.items, self.tk_session)
        except Exception:
            st = {}
        q, kind, rf = self.ml_q.get().strip().lower(), self.ml_kind.get(), self.ml_rankf.get()
        names = set(lib) | set(st) | set(mine)
        out = []
        for name in names:
            e = lib.get(name, {"kind": "Learned" if name in st else "Map", "learned": name in st})
            r = mine.get(name)
            if q and q not in name.lower():
                continue
            if kind != "All" and e["kind"] != kind:
                continue
            if rf == "Ranked" and not r or rf == "Not ranked" and r or rf in ML.RANKS and r != rf:
                continue
            if self.ml_run_only.get() and name not in st:
                continue
            out.append((name, e, r, com.get(name), st.get(name)))
        col, rev = self.ml_sort
        order = {r: i for i, r in enumerate(ML.RANKS)}
        keyf = {"map": lambda x: x[0].lower(), "kind": lambda x: (ML.KINDS.index(x[1]["kind"]) if x[1]["kind"] in ML.KINDS else 9, x[0]),
                "rank": lambda x: (order.get(x[2], 9), x[0]), "com": lambda x: (-(x[3] or {}).get("score", 0), x[0]),
                "runs": lambda x: (-(x[4] or {}).get("runs", 0), x[0]), "avg": lambda x: ((x[4] or {}).get("avg", 1e9), x[0]),
                "best": lambda x: ((x[4] or {}).get("best", 1e9), x[0])}[col]
        return sorted(out, key=keyf, reverse=rev)

    def ml_fill(self):
        from .tracker import fmt_time
        tv = self.ml_tv
        keep = set(tv.selection())
        tv.delete(*tv.get_children())
        rows = self.ml_rows()
        for name, e, r, c, s in rows:
            tags = ((RANK_TAG[r],) if r else ()) + (("learned",) if e.get("learned") else ())
            tv.insert("", "end", iid=name, tags=tags, values=(
                name, e["kind"], ("✖ Avoid" if r == "Avoid" else r) or "",
                f"{c['rank']}  ({c['votes']})" if c else "", s["runs"] if s else "",
                fmt_time(s["avg"]) if s else "", fmt_time(s["best"]) if s else ""))
        sel = [n for n in keep if tv.exists(n)]
        if sel:
            tv.selection_set(sel)
        mine = ML.ranks()
        self.ml_info.config(text=f"{len(rows)} shown · {len(mine)} ranked · "
                                 f"{sum(1 for v in mine.values() if v == 'Avoid')} to avoid")

    def ml_sort_by(self, col):
        cur, rev = self.ml_sort
        self.ml_sort = (col, not rev if cur == col else False)
        self.ml_fill()

    def ml_set(self, rank):
        sel = list(self.ml_tv.selection())
        if not sel:
            self._say("Select one or more maps first.", 4)
            return
        ML.set_rank(sel, rank)
        self.ml_fill()
        try:
            self.tracker_fill_maps()
        except Exception:
            buglog.caught()

    def ml_menu(self, e):
        tv = self.ml_tv
        row = tv.identify_row(e.y)
        if not row:
            return
        if row not in tv.selection():
            tv.selection_set(row)
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84")
        for r in ML.RANKS:
            m.add_command(label=("✖ Avoid" if r == "Avoid" else f"Rank {r}"), command=lambda rr=r: self.ml_set(rr))
        m.add_command(label="Clear rank", command=lambda: self.ml_set(None))
        lib = ML.library()
        learned = [n for n in tv.selection() if lib.get(n, {}).get("learned")]
        if learned:
            m.add_separator()
            m.add_command(label="Not a map (stop counting it)", command=lambda: self.ml_not_map(learned))
        m.tk_popup(e.x_root, e.y_root)

    def ml_not_map(self, names):
        for n in names:
            ML.not_a_map(n)
        self.ml_fill()
        self._say("Forgotten - it won't be counted as a map any more.", 6)

    # ---------------- share: export / import (files) and the community's ranks
    def ml_share_menu(self, btn):
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84")
        m.add_command(label="Export my ranks…", command=self.ml_export)
        m.add_command(label="Import ranks…", command=self.ml_import)
        m.add_separator()
        m.add_command(label="Take the community's ranks…", command=self.ml_take_community)
        m.add_command(label="Upload my ranks to the community", command=self.ml_upload)     # 2.98.5
        m.tk_popup(btn.winfo_rootx(), btn.winfo_rooty() + btn.winfo_height())

    def ml_export(self, path=None):
        path = path or filedialog.asksaveasfilename(parent=self.root, defaultextension=".json",
                                                    initialfile="map-ranks.json", filetypes=[("Map ranks", "*.json")])
        if not path:
            return None
        n = ML.export_ranks(path)
        self._say(f"Saved {n} map ranks to {path}", 8)
        return n

    def ml_import(self, path=None, mode=None):
        path = path or filedialog.askopenfilename(parent=self.root, filetypes=[("Map ranks", "*.json")])
        if not path:
            return None
        try:
            incoming = ML.read_ranks_file(path)
        except Exception as ex:
            self.app_toast(f"Couldn't import that file: {ex}", "Import map ranks")
            return None
        return self.ml_take(incoming, "Import map ranks", mode)

    def ml_take_community(self, mode=None):
        incoming = {n: c["rank"] for n, c in ML.community().items()}
        if not incoming:
            self.app_toast("No community ranks yet - they arrive with the hourly community sync once players rank maps.",
                           "Community map ranks")
            return None
        return self.ml_take(incoming, "Community map ranks", mode)

    def ml_upload(self):
        """2.98.5: send your map ranks now instead of with the hourly sync. Opt-in (Community data sharing); at most
        once per 45 minutes here and on the board (which also limits each address per day)."""
        from . import board as BRD
        from . import communitymods as CM
        title = "Upload map ranks"
        if not BRD.configured():
            self.app_toast("The community board isn't switched on yet.", title)
            return "off"
        if not self.cm_need_sharing(self.ml_upload):
            return "ask"
        if getattr(self, "_ml_uploading", False):
            return "busy"
        if not CM.maps_unsent():
            self._say("Your map ranks are already up - nothing new to upload.", 6)
            return "none"
        wait = CM.upload_wait()
        if wait:
            self._say(f"Uploaded a little while ago. Try again in {max(1, -(-wait // 60))} min.", 6)
            return "wait"
        self._ml_uploading = True

        def work():
            from .market import MARKET
            from .mods import RULES
            return CM.sync(MARKET, dict(RULES))

        def done(res):
            self._ml_uploading = False
            push = res[0] if res else (False, "busy")
            if push[0]:
                self._say("Map ranks uploaded. Everyone sees them after the community's next update.", 8)
            elif "too soon" in str(push[1]) or "too many" in str(push[1]):
                self._say("The board says it's too soon - try again later.", 6)
            else:
                self._say("Couldn't upload right now - the hourly sync will try again.", 6)
        self._lb_bg(work, done)
        return "sent"

    def ml_take(self, incoming, title, mode=None):
        """Ask how to bring these ranks in: Replace all / Add and update / Add new only (keep mine)."""
        new, same, differ = ML.compare(incoming)
        if mode is None:
            mode = self.ml_ask_mode(title, len(incoming), len(new), len(same), len(differ))
        if not mode:
            return None
        n = ML.apply_import(incoming, mode)
        self.ml_fill()
        self._say(f"{title}: {n} rank{'s' if n != 1 else ''} changed.", 8)
        return n

    def ml_ask_mode(self, title, total, new, same, differ):
        P1 = C["panel"]
        win = tk.Toplevel(self.root, bg=P1)
        over_app(win, self.dlg_parent())               # 2.114.3: over the app, on its monitor
        win.title(title)
        win.transient(self.root)
        win.grab_set()
        res = {"mode": None}
        f = tk.Frame(win, bg=P1, padx=16, pady=12)
        f.pack(fill="both", expand=True)
        tk.Label(f, text=f"{total} ranks: {new} new, {differ} different from yours, {same} the same.", bg=P1,
                 fg=C["text"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        for mode, label, why in (("replace", "Replace all", "your ranks become exactly these"),
                                 ("update", "Add and update", "add the new ones, and take these where they differ"),
                                 ("add", "Add new only", "add the new ones, keep yours where they differ")):
            row = tk.Frame(f, bg=P1)
            row.pack(fill="x", pady=(8, 0))
            ttk.Button(row, text=label, width=16, command=lambda m=mode: (res.update(mode=m), win.destroy())).pack(
                side="left")
            tk.Label(row, text=why, bg=P1, fg=C["muted"]).pack(side="left", padx=8)
        ttk.Button(f, text="Cancel", command=win.destroy, style="Quiet.TButton").pack(anchor="e", pady=(12, 0))
        win.bind("<Escape>", lambda e: win.destroy())
        place_near(self.root, win, self.root.winfo_pointerx() - 150, self.root.winfo_pointery() - 80)
        self.ml_dialog = win
        win.wait_window()
        return res["mode"]
