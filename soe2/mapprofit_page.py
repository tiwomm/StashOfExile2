"""2.132.0 Map profit - the watcher's side (mapprofit.py has the counting and the log), the bar's profit part with
its breakdown one hover away, the Map profit window (every map, searchable) and its row in Overlay ↳ Settings ›
Helpers. Off until you turn it on. Everything stays on your PC (map_profit.jsonl) - never sent anywhere."""
import time
import tkinter as tk
from tkinter import ttk

from . import buglog
from . import mapprofit as MP
from .config import SETTINGS, save_json
from .style import C, Tooltip

REFS_SECS = 600                     # Scan stash's pictures are built again at most this often


class MapProfitPage:
    """Mixed into App."""

    # ---------------------------------------------------------------- on / off
    def mp_on(self):
        from . import features as FEAT
        return bool(MP.cfg().get("on")) and FEAT.on("overlay") and FEAT.on("mapprofit")      # (2.132.2: BETA)

    def mp_set(self, on):
        MP.cfg()["on"] = bool(on)
        if on:
            from . import features as FEAT                  # (its BETA feature comes on with it, as Features shows)
            if not FEAT.on("mapprofit"):
                FEAT.set_on("mapprofit", True)
        save_json("settings.json", SETTINGS)
        if on:
            self.topup_start()                              # (Top Up's inventory looks do the reading)
            if getattr(self, "br_reader", None) is None:    # (the game's log says when you're in a map)
                try:
                    self.breach_start()
                except Exception:
                    buglog.caught()
            self.mp_refs(force=True)
            try:
                from .wealth import WPRICES
                lg = SETTINGS.get("league") or ""
                self.run_bg(lambda: WPRICES.ensure(lg), lambda _r: None)
            except Exception:
                buglog.caught()
        try:
            self.merged_build()                             # (the bar's profit part comes / goes)
        except Exception:
            buglog.caught()

    def mp_price(self, name):
        from .wealth import WPRICES
        return WPRICES.named(name)

    def mp_refs(self, force=False):
        """Scan stash's pictures of exchange items (built on a background thread; None until then)."""
        at = getattr(self, "mp_refs_at", 0)
        if not force and (getattr(self, "mp_refs_v", None) is not None or getattr(self, "_mp_refs_busy", False)) \
                and time.time() - at < REFS_SECS:
            return getattr(self, "mp_refs_v", None)
        if getattr(self, "_mp_refs_busy", False):
            return getattr(self, "mp_refs_v", None)
        self._mp_refs_busy = True

        def work():
            from . import favours as FV
            from .wealth import WPRICES
            return FV.build_refs(FV.ninja_items(getattr(WPRICES, "parts", None)))

        def done(r):
            self._mp_refs_busy = False
            self.mp_refs_v, self.mp_refs_at = r, time.time()
        try:
            self.run_bg(work, done)
        except Exception:
            self._mp_refs_busy = False
            buglog.caught()
        return getattr(self, "mp_refs_v", None)

    # ---------------------------------------------------------------- reading (from Top Up's clear looks)
    def mp_seen(self, res):
        """A look at the open inventory (topup_seen) in your hideout or a town.

        2.132.2 (feedback: "needs to account for inventory dumps if a player empties inventory and goes back into
        the map"): a map is counted visit by visit. What you came back with is the most of each item seen while
        you're home in your first looks (MP.ARRIVE_SECS from the first: stashing or selling only lowers it, and a
        covered look only hides cells - so a covered look counts here too; taking more from your stash later doesn't
        count); what you went back in with is the last clear look before the map. Each visit's loot = came back with
        - went in with, so emptying your inventory between visits isn't a loss."""
        if not self.mp_on() or getattr(self, "br_area", None) not in ("hideout", "town"):
            return None
        from . import topup as TU
        counts, unknown = MP.identify(res.get("cells") or [], TU.learned(), self.mp_refs())
        counts = MP.exchange_only(counts, self.mp_price)
        snap = {"t": time.time(), "counts": counts, "unknown": unknown}
        pend = getattr(self, "mp_pending", None)
        if pend is not None:
            t0 = pend.setdefault("visit_t0", snap["t"])
            vis = pend.setdefault("visit", {})
            if snap["t"] - t0 <= MP.ARRIVE_SECS:
                for k, n in counts.items():
                    vis[k] = max(vis.get(k, 0), n)
            pend["unknown"] = max(pend.get("unknown", 0), unknown)
            self.mp_check_done()
            self.mp_paint()
        if not res.get("covered"):
            self.mp_home = snap                             # (what you'd go into the next map with)
        return snap

    @staticmethod
    def _mp_visit_in(run):
        """Add the last visit home's loot (came back with - went in with) to the run's gain."""
        vis = run.pop("visit", None)
        run.pop("visit_t0", None)
        if vis is None:
            return
        went = run.get("seg_before") or {}
        g = run.setdefault("gain", {})
        for k in set(vis) | set(went):
            d = vis.get(k, 0) - went.get(k, 0)
            if d:
                g[k] = g.get(k, 0) + d

    def _mp_entry(self, run):
        base = run["before"]["counts"]
        gain = dict(run.get("gain") or {})
        vis = run.get("visit")
        if vis is not None:                                 # (the visit you're on now, so far)
            went = run.get("seg_before") or {}
            for k in set(vis) | set(went):
                gain[k] = gain.get(k, 0) + vis.get(k, 0) - went.get(k, 0)
        after = {k: base.get(k, 0) + gain.get(k, 0) for k in set(base) | set(gain)}
        return MP.entry(run["map"], run["secs"], base, after, self.mp_price,
                        unknown=max(run["before"].get("unknown", 0), run.get("unknown", 0)))

    def mp_done(self):
        """The map you came back from is done: its line goes in the log (if you looked at your inventory after it)."""
        pend, self.mp_pending = getattr(self, "mp_pending", None), None
        if pend is None or (pend.get("visit") is None and not pend.get("gain")):
            return None
        e = self._mp_entry(pend)
        e["run"] = pend["run"]
        MP.log_add(e)
        self.mp_last = e
        buglog.debug("Map profit", f"a map: {len(e['rows'])} items changed")      # (no names, no amounts)
        self.mp_paint()
        return e

    def mp_check_done(self, now=None):
        """Not back into it for DONE_SECS: it's done."""
        pend = getattr(self, "mp_pending", None)
        if pend is not None and (now or time.time()) - pend.get("left", 0) >= MP.DONE_SECS:
            return self.mp_done()
        return None

    def mp_so_far(self):
        """The map you're between visits of (a town trip): its profit so far, or None."""
        pend = getattr(self, "mp_pending", None)
        if pend is None or (pend.get("visit") is None and not pend.get("gain")):
            return None
        return self._mp_entry(pend)

    def mp_area(self, kind, before, where, left):
        """breach_area: into a map from home - its "before" is the last clear look at home; out of it - each visit
        home adds its loot until it's done. Back into the same map (its portal, a town trip): the same run."""
        if not self.mp_on():
            return
        now = time.time()
        self.mp_check_done(now)
        run = getattr(self, "mp_run", None)
        if kind == "map" and before != "map":
            pend = getattr(self, "mp_pending", None)
            if pend is not None and pend.get("where") == where:
                self._mp_visit_in(pend)                     # (back through its portal: the same map goes on, from
                home = getattr(self, "mp_home", None)       # what you went back in with)
                if home is not None and home["t"] >= pend.get("left", 0):
                    pend["seg_before"] = dict(home["counts"])
                pend["start"] = now
                self.mp_run, self.mp_pending = pend, None
                return
            self.mp_done()                                  # (another map: the last one is done)
            home = getattr(self, "mp_home", None)
            if home is not None and now - home["t"] < MP.BEFORE_SECS:
                self._mp_n = getattr(self, "_mp_n", 0) + 1
                self.mp_run = {"before": home, "seg_before": dict(home["counts"]), "gain": {}, "start": now,
                               "secs": 0, "where": where, "map": self.mp_map_name(where),
                               "run": f"{now:.3f}-{self._mp_n}"}
            else:
                self.mp_run = None                          # (no look at home before it: this map isn't counted)
        elif left and run is not None:
            run["secs"] += now - run["start"]
            run["left"] = now
            self.mp_pending, self.mp_run = run, None

    @staticmethod
    def mp_map_name(where):
        try:
            from . import maplib
            return maplib.display_name(where[0]) if where else ""
        except Exception:
            return ""

    # ---------------------------------------------------------------- what it says
    def mp_totals(self):
        s = getattr(self, "tk_session", None)
        start = getattr(s, "started", None) if s is not None else None
        if not isinstance(start, (int, float)):
            start = time.time() - 12 * 3600
        return MP.totals(MP.log_read(time.time() - 2 * 86400), session_start=start)

    def mp_bar_text(self):
        """The bar's part: the last map's profit, with its mark (▲ / ▼) - or "Profit –" before one is counted."""
        if not self.mp_on():
            return ""
        from .pricefmt import fmt_div
        try:
            self.mp_check_done()                            # (the bar redraws each second: a map can be done now)
        except Exception:
            buglog.caught()
        e = getattr(self, "mp_last", None)
        if e is None:
            last = MP.log_read(time.time() - 12 * 3600)
            e = self.mp_last = last[-1] if last else None
        if e is None:
            return "Profit –"
        return ("▲ " if e["div"] >= 0 else "▼ ") + MP.signed(e["div"], fmt_div)

    def mp_breakdown(self, e=None):
        """How the bar's number was worked out: [line, ...] (the hover)."""
        from .pricefmt import fmt_div
        so_far = None if e is not None else self.mp_so_far()
        e = e or getattr(self, "mp_last", None)
        if e is None and so_far is None:
            return ["No map counted yet.",
                    "Open your inventory in your hideout before a map and again after it."]
        out = []
        if so_far is not None:                              # 2.132.1: a town trip - it counts when you're done
            out.append(f"This map so far: {MP.signed(so_far['div'], fmt_div)}" +
                       (f"  ·  {so_far['map']}" if so_far.get("map") else "") + "  (counted when you start another)")
            if e is None:
                e = so_far
        mins = e.get("secs", 0) // 60
        out.append(f"Last map: {MP.signed(e['div'], fmt_div)}" + (f"  ·  {e['map']}" if e.get("map") else "")
                   + (f"  ·  {mins} min" if mins else ""))
        if so_far is not None and e is so_far:
            out.pop()
        for name, b, a, each in e.get("rows", [])[:8]:
            out.append(f"{name}: {b} → {a}  ({MP.signed((a - b) * each, fmt_div)})")
        if len(e.get("rows", [])) > 8:
            out.append(f"+{len(e['rows']) - 8} more - Maps… has them all")
        t = self.mp_totals()
        sd, sn = t["session"]
        out.append(f"Session: {MP.signed(sd, fmt_div)} · {sn} map{'s' if sn != 1 else ''}"
                   + (f" · {MP.signed(t['per_hour'], fmt_div)} / hour" if t["per_hour"] is not None else ""))
        if e.get("unknown"):
            out.append(f"{e['unknown']} item{'s' if e['unknown'] != 1 else ''} not known - teach with "
                       f"{self.topup_key_text()} or Scan stash")
        out.append("Currency Exchange items only · Exchange Rates prices · on your PC only")
        return out

    def mp_paint(self):
        try:
            self.tracker_overlay_draw(self.tracker_numbers())
        except Exception:
            buglog.caught()
        try:
            self.mp_list_refresh()
        except Exception:
            buglog.caught()

    # ---------------------------------------------------------------- the bar's hover
    def mp_hover_show(self, x, y):
        self.mp_hover_hide()
        from .overlaywin import pal
        P = pal()
        w = self.mp_tip = tk.Toplevel(self.root)
        w.overrideredirect(True)
        try:
            w.attributes("-topmost", True)
        except tk.TclError:
            pass
        box = tk.Frame(w, bg=P.get("bg", "#151311"), highlightthickness=1,
                       highlightbackground=P.get("rim") or P.get("line", "#3a3226"), padx=8, pady=8)
        box.pack()
        for i, line in enumerate(self.mp_breakdown()):
            tk.Label(box, text=line, bg=P.get("bg", "#151311"), anchor="w", justify="left",
                     fg=(P.get("big") or P.get("text", "#efe6d2")) if i == 0 else
                     (P.get("muted", "#a3957e") if i >= len(self.mp_breakdown()) - 1 else P.get("text", "#efe6d2")),
                     font=(P.get("font") or "Segoe UI", 10, "bold" if i == 0 else "normal")).pack(fill="x")
        w.update_idletasks()
        w.geometry(f"+{int(x - w.winfo_reqwidth() // 2)}+{int(y - w.winfo_reqheight() - 8)}")

    def mp_hover_hide(self, _e=None):
        w, self.mp_tip = getattr(self, "mp_tip", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def mp_bar_bind(self, cv, item):
        """The bar's profit part: hover = how it was worked out, click = Maps…"""
        cv.addtag_withtag("mg_profit", item)
        cv.tag_bind("mg_profit", "<Enter>", lambda e: self.mp_hover_show(e.x_root, e.y_root - 6))
        cv.tag_bind("mg_profit", "<Leave>", self.mp_hover_hide)
        cv.tag_bind("mg_profit", "<Button-1>", lambda _e: (self.mp_hover_hide(), self.mp_list_open()))

    # ---------------------------------------------------------------- the Map profit window
    def mp_list_open(self):
        old = getattr(self, "mp_win", None)
        if old is not None and old.winfo_exists():
            old.lift()
            return old
        P2 = C["panel2"]
        w = self.mp_win = tk.Toplevel(self.root, bg=P2)
        w.title("Map Profit")
        w.geometry("760x480")
        box = tk.Frame(w, bg=P2, padx=16, pady=16)
        box.pack(fill="both", expand=True)
        head = tk.Frame(box, bg=P2)
        head.pack(fill="x")
        tk.Label(head, text="Maps", bg=P2, fg=C["text"], font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(head, text="What each map earned, counted from your inventory", bg=P2, fg=C["muted"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(8, 0))
        ii = tk.Label(head, text="ⓘ", bg=P2, fg=C["muted"], cursor="question_arrow")
        ii.pack(side="left", padx=(8, 0))
        Tooltip(ii, "Open your inventory in your hideout or a town before a map and again after it: what changed is "
                    "that map's loot. Only Currency Exchange items count (no waystones, no gear), at Exchange Rates' "
                    "prices. Kept on your PC only (map_profit.jsonl) - never uploaded or shared.")
        bar = tk.Frame(box, bg=P2)
        bar.pack(fill="x", pady=(8, 8))
        self.mp_q = tk.StringVar()
        # (UX: the search box first, top left - 2.132.1, feedback: "wtf is this textbox for?": it says so, as the
        # other list pages do)
        tk.Label(bar, text="Search", bg=P2, fg=C["muted"]).pack(side="left", padx=(0, 8))
        ent = ttk.Entry(bar, textvariable=self.mp_q, width=24)
        ent.pack(side="left")
        Tooltip(ent, "Find a map, or every map an item dropped in (Divine Orb, Omen of ...).")
        self.mp_q.trace_add("write", lambda *_a: self.mp_list_refresh())
        self.mp_sum = tk.Label(bar, text="", bg=P2, fg=C["text"], font=("Segoe UI", 9))
        self.mp_sum.pack(side="right")
        cols = ("map", "time", "profit", "when")
        tv = self.mp_tv = ttk.Treeview(box, columns=cols, show="headings", height=12)
        for c, title, wd, anc in (("map", "Map", 260, "w"), ("time", "Time", 70, "e"), ("profit", "Profit", 120, "e"),
                                  ("when", "When", 150, "w")):
            tv.heading(c, text=title)
            tv.column(c, width=wd, anchor=anc)
        tv.pack(fill="both", expand=True)
        tv.bind("<Motion>", self._mp_row_hover)
        tv.bind("<Leave>", lambda _e: self.mp_hover_hide())
        self.mp_empty = tk.Frame(box, bg=P2)
        foot = tk.Label(box, text="On your PC only - never uploaded or shared.", bg=P2, fg=C["muted"],
                        font=("Segoe UI", 9), anchor="w")
        foot.pack(fill="x", pady=(8, 0))
        w.protocol("WM_DELETE_WINDOW", lambda: (self.mp_hover_hide(), w.destroy(), setattr(self, "mp_win", None)))
        try:
            self.popup_over_app(w)
        except Exception:
            buglog.caught()
        self.mp_list_refresh()
        ent.focus_set()
        return w

    def mp_runs(self, q=""):
        """The log as maps (a map you went back into through your portal is one), newest first."""
        runs = {}
        for e in MP.log_read(time.time() - MP.KEEP_DAYS * 86400):
            r = runs.setdefault(e.get("run") or str(e.get("t")), {"map": e.get("map", ""), "t": e["t"], "secs": 0,
                                                                   "div": 0.0, "rows": {}, "unknown": 0,
                                                                   "n": len(runs)})
            r["t"] = max(r["t"], e["t"])
            r["secs"] += e.get("secs", 0)
            r["div"] += e.get("div", 0)
            r["unknown"] = max(r["unknown"], e.get("unknown", 0))
            for name, b, a, each in e.get("rows", []):
                was = r["rows"].get(name)
                r["rows"][name] = [was[0] if was else b, a, each]
        out = sorted(runs.values(), key=lambda r: (-r["t"], -r["n"]))
        q = (q or "").strip().lower()
        if q:
            out = [r for r in out if q in r["map"].lower() or any(q in n.lower() for n in r["rows"])]
        return out

    def mp_list_refresh(self):
        tv = getattr(self, "mp_tv", None)
        if tv is None or not tv.winfo_exists():
            return
        from .pricefmt import fmt_div
        runs = self.mp_runs(self.mp_q.get() if getattr(self, "mp_q", None) else "")
        tv.delete(*tv.get_children())
        self.mp_rows = {}
        for i, r in enumerate(runs):
            iid = f"r{i}"
            self.mp_rows[iid] = r
            m, s = divmod(int(r["secs"]), 60)
            tv.insert("", "end", iid=iid, values=(
                r["map"] or "a map", f"{m}:{s:02d}" if r["secs"] else "–",
                ("▲ " if r["div"] >= 0 else "▼ ") + MP.signed(r["div"], fmt_div),
                time.strftime("%a %d %b, %H:%M", time.localtime(r["t"]))))
        t = self.mp_totals()
        sd, sn = t["session"]
        dd, dn = t["day"]
        self.mp_sum.config(text=(f"Session: {sn} map{'s' if sn != 1 else ''} · {MP.signed(sd, fmt_div)}"
                                 + (f" · {MP.signed(t['per_map'], fmt_div)} / map" if t["per_map"] is not None else "")
                                 + (f" · {MP.signed(t['per_hour'], fmt_div)} / hour" if t["per_hour"] is not None
                                    else "") if sn else "Session: no maps yet")
                                + (f"   Today: {MP.signed(dd, fmt_div)}" if dn else ""))
        for ch in self.mp_empty.winfo_children():
            ch.destroy()
        if runs:
            self.mp_empty.pack_forget()
            return
        P2 = C["panel2"]                                    # (UX: empty - what it is + one button)
        self.mp_empty.pack(fill="x", before=tv, pady=(0, 8))
        tk.Label(self.mp_empty, text="No maps counted yet. Open your inventory in your hideout before a map and "
                                     "again after it.", bg=P2, fg=C["text"], anchor="w").pack(side="left")
        if not self.mp_on():
            ttk.Button(self.mp_empty, text="Turn on Map profit", style="Primary.TButton",
                       command=lambda: (self.mp_set(True), self.mp_sync_switch(), self.mp_list_refresh())
                       ).pack(side="right")

    def _mp_row_hover(self, e):
        tv = self.mp_tv
        iid = tv.identify_row(e.y)
        r = (getattr(self, "mp_rows", None) or {}).get(iid)
        if r is None:
            return self.mp_hover_hide()
        if getattr(self, "_mp_hover_iid", None) == iid and getattr(self, "mp_tip", None) is not None:
            return None
        self._mp_hover_iid = iid
        rows = sorted(([n, v[0], v[1], v[2]] for n, v in r["rows"].items()),
                      key=lambda x: -abs((x[2] - x[1]) * x[3]))
        e2 = {"div": r["div"], "map": r["map"], "secs": r["secs"], "rows": rows, "unknown": r["unknown"]}
        lines = self.mp_breakdown(e2)
        self.mp_hover_hide()
        w = self.mp_tip = tk.Toplevel(self.root, bg=C["panel"])
        w.overrideredirect(True)
        box = tk.Frame(w, bg=C["panel"], highlightthickness=1, highlightbackground=C["line"], padx=8, pady=8)
        box.pack()
        for i, line in enumerate(lines):
            tk.Label(box, text=line, bg=C["panel"], fg=C["muted"] if i == len(lines) - 1 else C["text"],
                     font=("Segoe UI", 9, "bold" if i == 0 else "normal"), anchor="w").pack(fill="x")
        w.geometry(f"+{e.x_root + 16}+{e.y_root + 12}")
        return None

    # ---------------------------------------------------------------- Overlay ↳ Settings › Helpers: its row
    def mp_row(self, box, bg, CB):
        sm = ("Segoe UI", 9)
        row = tk.Frame(box, bg=bg)
        row.pack(fill="x", pady=(8, 0))
        self.al_mp = tk.BooleanVar(value=bool(MP.cfg()["on"]))
        cb = ttk.Checkbutton(row, text="Map profit (BETA)", variable=self.al_mp, style=CB,
                             command=lambda: self.mp_set(bool(self.al_mp.get())))
        cb.pack(side="left")
        mb = ttk.Button(row, text="Maps…", command=self.mp_list_open)
        mb.pack(side="left", padx=(8, 0))
        info = tk.Label(row, text="ⓘ", bg=bg, fg=C["muted"], font=sm, cursor="question_arrow")
        info.pack(side="left", padx=(8, 0))
        tk.Label(box, text="What each map earned, from your inventory before and after it - on your PC only.", bg=bg,
                 fg=C["muted"], font=sm, anchor="w").pack(fill="x")
        Tooltip(cb, "Reads your inventory when it's open in your hideout or a town (the same quick look as Top Up). "
                    "Off until you turn it on.")
        Tooltip(mb, "Every map counted, with how each number was worked out.")
        Tooltip(info, "Only Currency Exchange items count - currency, omens, runes... - never waystones or gear. Items "
                      "are known by Scan stash's pictures or the ones you taught with "
                      f"{self.topup_key_text()}. Prices: Exchange Rates. Saved in map_profit.jsonl in your data folder "
                      "and never sent anywhere.")

    def mp_sync_switch(self):
        v = getattr(self, "al_mp", None)
        if v is not None and bool(v.get()) != bool(MP.cfg()["on"]):
            v.set(bool(MP.cfg()["on"]))
