"""2.86.0: Overlay ↳ Leaderboards - Campaign, Maps, Bosses & pinnacles, Trials; Mine (this PC) or Everyone (the
community board, opt-in through Community data sharing); this league or all; by class.
Right-click a row on Everyone: Report (and, for reviewers / admins, Hide / Keep). GGG ToS: the game's log only."""
import threading
import time
import tkinter as tk
from tkinter import ttk

from . import board as B
from . import leaderboard as LB
from .config import SETTINGS, save_json
from .style import C, SegBar

ALL_LEAGUES = "All leagues"
TOPS = (5, 10, 20, 30, 50, 100)             # 2.104.1 (feedback): how many rows a board shows


class LeaderboardPage:
    def build_leaderboards(self, body):
        P1 = C["panel"]
        # P5 (2.108.0): two rows - the board and sharing on top, the filters under it
        top = tk.Frame(body, bg=P1, padx=8, pady=8)
        top.pack(fill="x")
        top2 = tk.Frame(body, bg=P1, padx=8)
        top2.pack(fill="x", pady=(0, 4))
        self.lb_cat = SegBar(top, [n for _k, n in LB.CATS], command=lambda v: self.lb_refresh(), size=10, pad=(12, 4))
        self.lb_cat.pack(side="left")
        from .community_page import chip_text                  # 2.94.0: your community name, as on Money Makers
        self.lb_acct = ttk.Button(top, text=chip_text() + " ▾", command=self.community_open)
        self.lb_acct.pack(side="right")
        self.lb_share_var = tk.BooleanVar(value=bool(SETTINGS.get("lb_share", True)))
        ttk.Checkbutton(top, text="Share my times", variable=self.lb_share_var, command=self.lb_share_switch,
                        style="Card.TCheckbutton").pack(side="right", padx=(0, 12))
        self.lb_who = SegBar(top2, ["Mine", "Everyone"], value="Everyone", command=lambda v: self.lb_refresh(), size=9,
                             pad=(12, 4))
        self.lb_who.pack(side="left")
        tk.Label(top2, text="League", bg=P1, fg=C["muted"]).pack(side="left", padx=(16, 4))
        self.lb_league = tk.StringVar(value=SETTINGS.get("league") or ALL_LEAGUES)   # 2.104.1: the league's name
        cb = ttk.Combobox(top2, textvariable=self.lb_league, values=self.lb_league_names(), state="readonly",
                          width=22)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.lb_refresh())
        self.lb_league_box = cb
        tk.Label(top2, text="Class", bg=P1, fg=C["muted"]).pack(side="left", padx=(12, 4))
        self.lb_cls = tk.StringVar(value="All")
        self.lb_cls_box = ttk.Combobox(top2, textvariable=self.lb_cls, values=("All",), state="readonly", width=16)
        self.lb_cls_box.pack(side="left")
        self.lb_cls_box.bind("<<ComboboxSelected>>", lambda e: self.lb_refresh())
        from .style import Tooltip
        Tooltip(self.lb_cls_box, "Your class comes from the game's log: it names it at every level-up "
                                 "(\"ExampleWitch (Invoker) is now level 24\"). Everyone's: the classes players shared.")
        tk.Label(top2, text="Show", bg=P1, fg=C["muted"]).pack(side="left", padx=(12, 4))
        top_n = SETTINGS.get("lb_top", 10)
        self.lb_top = tk.StringVar(value=f"Top {top_n if top_n in TOPS else 10}")
        tb = ttk.Combobox(top2, textvariable=self.lb_top, values=[f"Top {n}" for n in TOPS], state="readonly", width=8)
        tb.pack(side="left")
        tb.bind("<<ComboboxSelected>>", lambda e: self.lb_top_pick())
        ttk.Button(top2, text="↻ Refresh", style="Quiet.TButton", command=lambda: self.lb_refresh(send=True)).pack(
            side="right")
        self.lb_msg = tk.Label(body, text="", bg=P1, fg=C["muted"], anchor="w", justify="left", padx=12)
        self.lb_msg.pack(fill="x")
        split = tk.Frame(body, bg=P1)
        split.pack(fill="both", expand=True, padx=8, pady=8)
        left = tk.Frame(split, bg=P1, width=380)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        kv = ttk.Treeview(left, columns=("mine", "best", "n"), show="tree headings", selectmode="browse")
        kv.heading("#0", text="Act / map")
        kv.heading("mine", text="My best")
        kv.heading("best", text="Best")
        kv.heading("n", text="Players")
        kv.column("#0", width=150)
        for c, w in (("mine", 72), ("best", 64), ("n", 68)):
            kv.column(c, width=w, anchor="e", stretch=False)
        kv.pack(fill="both", expand=True)
        kv.bind("<<TreeviewSelect>>", lambda e: self.lb_board_fill())
        self.lb_keys_empty = tk.Label(left, text="No times on this board yet.\n\nPlay the campaign with the Campaign "
                                                 "Helper, or run maps with the session timer - your times show here.",
                                      bg=self._lb_field(), fg=C["muted"], wraplength=300, justify="center")
        self.lb_keys_tv = kv
        right = tk.Frame(split, bg=P1)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.lb_title = tk.Label(right, text="", bg=P1, fg=C["accent"], font=("Segoe UI", 12, "bold"), anchor="w")
        self.lb_title.pack(fill="x")
        cols = (("rank", "#", 40, "e"), ("name", "Player", 150, "w"), ("time", "Time", 80, "e"), ("cls", "Class", 120, "w"),
                ("lvl", "Level", 60, "e"), ("deaths", "Deaths", 66, "e"), ("league", "League", 120, "w"),
                ("when", "When", 100, "w"))
        bv = ttk.Treeview(right, columns=[c[0] for c in cols], show="tree headings", selectmode="browse")
        bv.column("#0", width=24, minwidth=24, stretch=False, anchor="center")            # 2.95.0: the contributor icon
        self.lb_rep_names = {}
        self.rep_tree_hover(bv, lambda iid: self.lb_rep_names.get(iid))
        for cid, title, w, a in cols:
            bv.heading(cid, text=title)
            bv.column(cid, width=w, anchor=a, stretch=cid in ("name", "cls"))
        bv.tag_configure("gold", foreground="#ffd25a")
        bv.tag_configure("me", foreground=C["green"])
        bv.tag_configure("hidden", foreground=C["muted"])
        bv.pack(fill="both", expand=True, pady=(4, 0))
        self.lb_board_empty = tk.Label(right, text="Pick a board on the left.", bg=self._lb_field(), fg=C["muted"])
        bv.menu_actions = self.lb_menu_actions
        self.list_register("leaderboards", bv, multi=False)
        self.list_register("leaderboards", kv, multi=False)
        self.lb_tv = bv
        tk.Label(right, text="Times are self-reported - they come from the game's log (Client.txt), like the overlay's "
                             "session timer: a map's time is time inside it; a campaign act is its split (away time "
                             "left out). The board refuses impossible times, and reports, reviewers and admins hide "
                             "the rest. Your community name shows - never your account or character.",
                 bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left", wraplength=760).pack(
            fill="x", pady=(8, 0))
        self.lb_rows = {}                                     # (filled when the page is opened: on_show)

    @staticmethod
    def _lb_field():
        try:
            return ttk.Style().lookup("Treeview", "fieldbackground") or C["bg"]
        except tk.TclError:
            return C["bg"]

    # ---------------------------------------------------------------- data
    def lb_cat_key(self):
        return next(k for k, n in LB.CATS if n == self.lb_cat.get())

    def lb_mine(self):
        return LB.mine(self.tk_sessions.items if hasattr(self, "tk_sessions") else [], getattr(self, "tk_session", None))

    def lb_league_names(self, more=()):
        """The current league first, then the others your times or the board name, then All leagues."""
        cur = SETTINGS.get("league") or ""
        mine = [e.get("league") for e in (getattr(self, "lb_my", None) or [])]
        names = [n for n in dict.fromkeys([cur] + mine + list(more)) if n and n != ALL_LEAGUES]
        return names + [ALL_LEAGUES]

    def lb_top_n(self):
        try:
            n = int(str(self.lb_top.get()).split()[-1])
        except (ValueError, IndexError, AttributeError):
            n = 10
        return n if n in TOPS else 10

    def lb_top_pick(self):
        SETTINGS["lb_top"] = self.lb_top_n()
        save_json("settings.json", SETTINGS)
        self.lb_board_fill()

    def lb_filters(self):
        v = self.lb_league.get()
        if v == "This league":                        # (before 2.104.1)
            v = SETTINGS.get("league") or ALL_LEAGUES
            self.lb_league.set(v)
        league = "" if v == ALL_LEAGUES else v
        cls = "" if self.lb_cls.get() in ("All", "") else self.lb_cls.get()
        return league, cls

    def _lb_bg(self, work, done):
        if getattr(self, "mm_sync", False):
            return done(work())
        threading.Thread(target=lambda: self.ui_q.put(("lb_done", done, work())), daemon=True).start()

    def ev_lb_done(self, done, res):
        """(The answer comes back to the window thread through the app's event queue.)"""
        done(res)

    def lb_share_switch(self):
        SETTINGS["lb_share"] = bool(self.lb_share_var.get())
        save_json("settings.json", SETTINGS)
        cv = getattr(self, "cy_lb_var", None)                    # 2.94.0: Settings › Privacy & community follows
        if cv is not None and bool(cv.get()) != SETTINGS["lb_share"]:
            cv.set(SETTINGS["lb_share"])
        from . import board as B
        if SETTINGS["lb_share"] and B.configured() and not B.signed_in() and not getattr(self, "mm_sync", False):
            self.mm_join("show your times on the Leaderboards")       # 2.94.0: a name only when you need one
            self.cy_paint()
        if SETTINGS["lb_share"]:
            self.lb_send(force=True)
        else:                                                # 2.89.3: off = your times come off the board
            from . import board as B
            if B.configured() and B.signed_in():
                self._lb_bg(B.lb_forget, lambda r: None)

    def lb_send(self, force=False):
        """Your best times to the board (Community data sharing on, a community name, Share my times on). At most
        every 15 minutes unless forced (the board takes one batch per 10 minutes)."""
        if not (LB.sharing_on() and B.configured() and B.signed_in()):
            return False
        if not force and time.time() - SETTINGS.get("lb_sent", 0) < LB.SEND_EVERY:
            return False
        data = LB.payload(self.lb_mine())
        if not data:
            return False
        SETTINGS["lb_sent"] = time.time()

        def done(res):
            ok, d = res
            if ok and getattr(self, "lb_msg", None) is not None and isinstance(d, dict) and d.get("refused"):
                self.lb_msg.config(text=f"{d['refused']} of your times were refused (faster than anyone can play).",
                                   fg=C["muted"])
        self._lb_bg(lambda: B.lb_send(data), done)
        return True

    # ---------------------------------------------------------------- showing
    def lb_classes_once(self):
        """2.87.0: once a run, read the classes from the last part of Client.txt (in the background), then refresh."""
        if getattr(self, "_lb_cls_read", False):
            return
        self._lb_cls_read = True
        from .gamelog import find_log
        path = find_log(self.tracker_cfg().get("log_path")) if hasattr(self, "tracker_cfg") else None
        if path:
            threading.Thread(target=lambda: self.ui_q.put(("lb_done", lambda r: r and self.lb_refresh(),
                                                           LB.learn_classes(path))), daemon=True).start()

    def lb_refresh(self, send=False):
        if not hasattr(self, "lb_keys_tv"):
            return
        self.lb_classes_once()
        if send:
            self.lb_send(force=True)
        cat = self.lb_cat_key()
        league, cls = self.lb_filters()
        mine = self.lb_mine()
        self.lb_my = mine
        self.lb_my_keys = {k: (b, n) for k, b, n in LB.keys_of(mine, cat, league or None, cls or None)}
        self.lb_league_box.config(values=self.lb_league_names())
        classes = sorted({e["cls"] for e in mine if e.get("cls")})
        if self.lb_who.get() == "Mine":
            self._lb_keys_fill(None, classes)
            return
        if not B.configured():
            self.lb_msg.config(text="The community board isn't set up yet - showing yours.", fg=C["muted"])
            return self._lb_keys_fill(None, classes)
        if not LB.sharing_on():
            self.lb_msg.config(text="Everyone's times show once Community data sharing is on (Settings) - yours are "
                                    "added then too.", fg=C["muted"])
        self.lb_msg.config(text="Loading…", fg=C["muted"]) if LB.sharing_on() else None

        def done(res):
            ok, d = res
            if not ok:
                self.lb_msg.config(text=d, fg=C["red"])
                return self._lb_keys_fill(None, classes)
            n = len(d.get("keys") or [])
            self.lb_msg.config(text=f"{n} board{'s' if n != 1 else ''}. Pick one on the left.", fg=C["muted"])
            self.lb_league_box.config(values=self.lb_league_names(d.get("leagues") or ()))
            self._lb_keys_fill(d, sorted(set(classes) | set(d.get("classes") or [])))
        self._lb_bg(lambda: B.lb_keys(cat, league, cls), done)

    def _lb_keys_fill(self, d, classes):
        kv = self.lb_keys_tv
        keep = kv.selection()
        kv.delete(*kv.get_children())
        self.lb_cls_box.config(values=["All"] + classes)
        world = {r["key"]: r for r in (d or {}).get("keys") or []}
        keys = list(dict.fromkeys(list(self.lb_my_keys) + list(world)))
        if self.lb_cat_key() == "campaign":
            order = {k: i for i, (k, _b, _n) in enumerate(LB.keys_of(self.lb_my, "campaign"))}
            keys.sort(key=lambda k: (order.get(k, 999), k))
        for k in keys:
            mb = self.lb_my_keys.get(k, (None, 0))[0]
            w = world.get(k) or {}
            kv.insert("", "end", iid=k, text=k, values=(LB.fmt(mb), LB.fmt(w.get("best")) if w else "-",
                                                         w.get("players", "") if w else ""))
        if not keys:
            self.lb_msg.config(text="No times yet. Run maps with the overlay's session timer on, or play the campaign "
                                    "with the Campaign Helper - your times show here." if self.lb_who.get() == "Mine"
                               else "", fg=C["muted"])
        if keys:
            self.lb_keys_empty.place_forget()
        else:
            self.lb_keys_empty.place(relx=0.5, rely=0.45, anchor="center")
        sel = keep[0] if keep and kv.exists(keep[0]) else (keys[0] if keys else None)
        if sel:
            kv.selection_set(sel)
        else:
            self.lb_board_fill()

    def lb_board_fill(self):
        bv = self.lb_tv
        bv.delete(*bv.get_children())
        self.lb_rows = {}
        sel = self.lb_keys_tv.selection()
        if not sel:
            self.lb_title.config(text="")
            self.lb_board_empty.place(in_=bv, relx=0.5, rely=0.45, anchor="center")
            return
        self.lb_board_empty.place_forget()
        key, cat = sel[0], self.lb_cat_key()
        league, cls = self.lb_filters()
        self.lb_title.config(text=f"🏆 {key}" + (f" · {cls}" if cls else "") + (f" · {league}" if league else " · all leagues"))
        if self.lb_who.get() == "Mine":
            rows = sorted((e for e in self.lb_my if e["cat"] == cat and e["key"] == key
                           and (not league or e["league"] == league) and (not cls or e.get("cls") == cls)),
                          key=lambda e: e["secs"])[:self.lb_top_n()]
            for i, e in enumerate(rows):
                bv.insert("", "end", iid=f"m{i}", values=(i + 1, e.get("char") or "me", LB.fmt(e["secs"]),
                                                          e.get("cls") or "", e.get("level") or "", e.get("deaths", 0),
                                                          e["league"], time.strftime("%b %d", time.localtime(e["at"]))),
                          tags=("gold",) if i == 0 else ())
            return

        def done(res):
            ok, d = res
            if not ok:
                return self.lb_msg.config(text=d, fg=C["red"])
            for i, r in enumerate(d.get("rows") or []):
                iid = f"b{r['id']}"
                self.lb_rows[iid] = r
                tags = ("hidden",) if r.get("hidden") else ("me",) if r.get("mine") else ("gold",) if i == 0 else ()
                from . import rep as R
                img = R.icon(self.root, r.get("rep"))                             # 2.95.0: the contributor icon
                if img is not None:
                    self.lb_rep_names[iid] = r["name"]
                bv.insert("", "end", iid=iid, **({"image": img} if img is not None else {}), values=(i + 1, r["name"] + (" (you)" if r.get("mine") else ""),
                                                      LB.fmt(r["secs"]), r.get("cls") or "", r.get("level") or "",
                                                      r.get("deaths", 0), r.get("league", ""),
                                                      time.strftime("%b %d", time.localtime(r["at"]))), tags=tags)
        top = self.lb_top_n()
        self._lb_bg(lambda: B.lb_board(cat, key, league, cls, limit=top), done)

    # ---------------------------------------------------------------- reports / reviewers
    def lb_menu_actions(self, sel):
        r = self.lb_rows.get(sel[0]) if sel else None
        if not r:
            return []
        me = B.signed_in() or {}
        acts = []
        if not r.get("mine"):
            acts.append(("⚑ Report this time…", lambda: self.lb_report(r)))
        if (me.get("reviewer") or me.get("admin")) and not r.get("mine"):
            acts += [("Reviewer: hide it", lambda: self.lb_review(r, "hide")),
                     ("Reviewer: keep it (clear reports)", lambda: self.lb_review(r, "keep"))]
        return acts

    def lb_report(self, r):
        from tkinter import simpledialog
        if self.mm_need_login("report a time"):
            return
        why = simpledialog.askstring("Report", "What's wrong with this time?", parent=self.root)
        if why is None:
            return
        self._lb_bg(lambda: B.lb_report(r["id"], why), lambda res: (
            self._say("Reported - thanks." if res[0] else res[1], 6), self.lb_board_fill()))

    def lb_review(self, r, vote):
        self._lb_bg(lambda: B.lb_review(r["id"], vote), lambda res: (
            self._say(("Done." if res[0] else res[1]), 6), self.lb_board_fill()))

    def lb_open(self):
        self.shell.open("leaderboards")
