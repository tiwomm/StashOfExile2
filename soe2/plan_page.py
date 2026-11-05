"""Overlay ↳ Game Plan (2.73.0, League Focus part 1): goals by phase, a stockpile to buy while it's cheap, the farm
plan, a build lock and the poke settings - set once at league start, then forget it (focus.py keeps it; the overlay's
focus line and, from 2.73.1, the pokes bring it back when it matters). Every switch is a toggle; everything is
drawn with the app's theme (chrome sections, Card.* styles), so a theme swap repaints it like every other page."""
import tkinter as tk
from tkinter import ttk

from . import focus as F
from .chrome import section as chrome_section
from .config import SETTINGS
from .style import C, ScrollArea, SegBar, Tooltip


def _num(text):
    try:
        return float(str(text).replace(",", ".").strip())
    except ValueError:
        return None


class GamePlanPage:
    """Mixed into App. 2.73.4 (feedback: "it all sort of blends together"): one look for every part - what's in it
    first, then a hairline and a small ADD heading over its form, labels in one column, the same + Add button
    everywhere; phase headings with counts, goal details on a quieter second line, a summary strip on top."""

    # ---------------- the parts every section uses
    @staticmethod
    def _gp_head(parent, text, color=None, top=12, count=None):
        row = tk.Frame(parent, bg=parent["bg"])
        row.pack(fill="x", pady=(top, 4))
        tk.Label(row, text=text, bg=parent["bg"], fg=color or C["steel"], font=("Segoe UI", 9, "bold"),
                 anchor="w").pack(side="left")
        if count is not None:
            tk.Label(row, text=f"  {count}", bg=parent["bg"], fg=C["muted"], font=("Segoe UI", 9)).pack(side="left")
        return row

    @staticmethod
    def _gp_empty(parent, text):
        tk.Label(parent, text=text, bg=parent["bg"], fg=C["muted"], font=("Segoe UI", 9, "italic"), anchor="w",
                 justify="left").pack(fill="x", pady=(0, 2))

    def _gp_add_area(self, box, title):
        """A hairline, a small heading, and the form under it (a grid: labels in column 0)."""
        tk.Frame(box, bg=C["line"], height=1).pack(fill="x", pady=(12, 0))
        self._gp_head(box, title, top=8)
        form = tk.Frame(box, bg=box["bg"])
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        return form

    @staticmethod
    def _gp_label(form, row, text):
        tk.Label(form, text=text, bg=form["bg"], fg=C["muted"], font=("Segoe UI", 9), anchor="w").grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=2)

    @staticmethod
    def _gp_table_head(box, cols, weights=None):
        for c, h in enumerate(cols):
            tk.Label(box, text=h, bg=box["bg"], fg=C["muted"], font=("Segoe UI", 9, "bold"), anchor="w").grid(
                row=0, column=c, sticky="w", padx=(0, 12))
        tk.Frame(box, bg=C["line"], height=1).grid(row=1, column=0, columnspan=len(cols) + 1, sticky="ew",
                                                    pady=(2, 4))

    @staticmethod
    def _gp_bar(parent, frac, w=64):
        cv = tk.Canvas(parent, width=w, height=6, bg=parent["bg"], highlightthickness=0)
        cv.create_rectangle(0, 1, w - 1, 5, fill=C["panel"], outline=C["line"])
        if frac:
            cv.create_rectangle(0, 1, int((w - 1) * min(1.0, frac)), 5, fill=C["green"] if frac >= 1 else C["accent"],
                                outline="")
        return cv

    # ---------------- the page
    def build_game_plan(self, body):
        P1, P2 = C["panel"], C["panel2"]
        f = F.cfg()
        page = tk.Frame(body, bg=P1)
        top = tk.Frame(page, bg=P2, padx=12, pady=8, highlightthickness=1, highlightbackground=C["line"])
        top.pack(fill="x", padx=8, pady=(8, 8))
        self.gp_on = tk.BooleanVar(value=bool(f["on"]))
        ttk.Checkbutton(top, text="League Focus", variable=self.gp_on, command=self.gp_switch,
                        style="Card.TCheckbutton").pack(side="left")
        tk.Frame(top, bg=C["line"], width=1, height=22).pack(side="left", padx=12)
        tk.Label(top, text="PHASE", bg=P2, fg=C["muted"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
        self.gp_phase = SegBar(top, [n for _k, n in F.PHASES], command=lambda v: self.gp_phase_pick(v), size=9,
                               pad=(8, 4), bg=P2)
        self.gp_phase.pack(side="left")
        self.gp_phase.pick(F.phase_name(f["phase"]), notify=False)
        self.gp_summary = tk.Label(top, text="", bg=P2, fg=C["text"], font=("Segoe UI", 9), anchor="e")
        self.gp_summary.pack(side="right")
        tk.Label(page, text="Set it once - the overlay's focus line and pokes bring it back when it matters.",
                 bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=12, pady=(0, 4))
        sa = ScrollArea(page, bg=P1)
        sa.pack(fill="both", expand=True)
        grid = tk.Frame(sa.inner, bg=P1, padx=8)
        grid.pack(fill="both", expand=True)
        for c in range(2):
            grid.columnconfigure(c, weight=1, uniform="gp")
        left, right = tk.Frame(grid, bg=P1), tk.Frame(grid, bg=P1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._gp_goals(left)
        self._gp_pokes(left)
        self._gp_stock(right)
        self._gp_supplies(right)
        self._gp_farms(right)
        self._gp_lock(right)
        self.gp_fill()
        return page

    def gp_summary_text(self):
        f = F.cfg()
        open_ = sum(1 for g in f["goals"] if not g["done"])
        bits = [f"{open_} goal{'s' if open_ != 1 else ''} open"]
        if f["stockpile"]:
            bits.append(f"{len(f['stockpile'])} to stockpile")
        if f["supplies"]:
            bits.append(f"{len(f['supplies'])} map suppl{'ies' if len(f['supplies']) != 1 else 'y'}")
        if f["farms"]:
            bits.append(f"{len(f['farms'])} farm{'s' if len(f['farms']) != 1 else ''}")
        bits.append(("pokes on" if int(f["pokes"].get("per_hour") or 0) else "pokes off") if f["on"] else "Focus off")
        return "  ·  ".join(bits)

    # ---------------- A: goals by phase
    def _gp_goals(self, parent):
        P2 = C["panel2"]
        o, box = chrome_section(parent, "Goals by phase", "League start, when you reach maps, long term. ▸ puts one "
                                                          "on the overlay's focus line.", wrap=True)
        o.pack(fill="x", pady=(0, 12))
        self.gp_goal_box = tk.Frame(box, bg=P2)
        self.gp_goal_box.pack(fill="x")
        form = self._gp_add_area(box, "ADD A GOAL")
        self._gp_label(form, 0, "Goal")
        self.gp_new = tk.StringVar()
        e = ttk.Entry(form, textvariable=self.gp_new)
        e.grid(row=0, column=1, columnspan=3, sticky="ew", pady=2)
        e.bind("<Return>", lambda ev: self.gp_add_goal())
        self._gp_label(form, 1, "Phase")
        r1 = tk.Frame(form, bg=P2)
        r1.grid(row=1, column=1, columnspan=3, sticky="ew", pady=2)
        self.gp_new_phase = tk.StringVar(value=F.PHASES[0][1])
        ttk.Combobox(r1, textvariable=self.gp_new_phase, values=[n for _k, n in F.PHASES], state="readonly",
                     width=17).pack(side="left")
        tk.Label(r1, text="Poke me", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(12, 8))
        self.gp_new_trig = tk.StringVar(value=F.TRIGGERS[0][1])
        ttk.Combobox(r1, textvariable=self.gp_new_trig, values=[n for _k, n in F.TRIGGERS], state="readonly",
                     width=24).pack(side="left", fill="x", expand=True)
        self._gp_label(form, 2, "Target")
        r2 = tk.Frame(form, bg=P2)
        r2.grid(row=2, column=1, columnspan=3, sticky="ew", pady=2)
        self.gp_new_tkind = tk.StringVar(value="No target")
        cb = ttk.Combobox(r2, textvariable=self.gp_new_tkind, state="readonly", width=17,
                          values=["No target"] + [n for _k, n, _u in F.TARGETS])
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.gp_target_hint())
        self.gp_new_target = tk.StringVar()
        self.gp_new_target_e = ttk.Entry(r2, textvariable=self.gp_new_target, width=7)
        self.gp_new_target_e.pack(side="left", padx=(8, 0))
        self.gp_new_target_e.bind("<Return>", lambda ev: self.gp_add_goal())
        self.gp_target_note = tk.Label(r2, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9))
        self.gp_target_note.pack(side="left", padx=(8, 0))
        ttk.Button(r2, text="+ Add", command=self.gp_add_goal).pack(side="right")
        self.gp_target_hint()

    TARGET_HINTS = {"No target": "", "div": "divines - you type how many you have",
                    "level": "level - read from the game's log", "act": "act number - you tick how far you are",
                    "maps": "maps - counted from the log", "count": "you type how many you have"}

    def gp_target_kind(self):
        lab = self.gp_new_tkind.get()
        return next((k for k, n, _u in F.TARGETS if n == lab), None)

    def gp_target_hint(self):
        k = self.gp_target_kind()
        self.gp_target_note.config(text=self.TARGET_HINTS.get(k or "No target", ""))
        self.gp_new_target_e.state(["!disabled"] if k else ["disabled"])
        if not k:
            self.gp_new_target.set("")

    def gp_add_goal(self):
        text = self.gp_new.get().strip()
        if not text:
            return None
        phase = next((k for k, n in F.PHASES if n == self.gp_new_phase.get()), "start")
        trig = next((k for k, n in F.TRIGGERS if n == self.gp_new_trig.get()), "town")
        n = _num(self.gp_new_target.get()) if self.gp_new_target.get().strip() else None
        kind = self.gp_target_kind() if hasattr(self, "gp_new_tkind") else None
        if n and not kind:                                 # a number with No target picked: divines (as before)
            kind = "div"
        g = F.add_goal(text, phase, trig, target_kind=kind, target=n)
        self.gp_new.set("")
        self.gp_new_target.set("")
        self.gp_fill()
        self.gp_overlay()
        return g

    def _gp_goal_rows(self):
        P2 = C["panel2"]
        box = self.gp_goal_box
        for w in box.winfo_children():
            w.destroy()
        f = F.cfg()
        cur = F.current()
        self.gp_goal_vars = {}
        trig = dict(F.TRIGGERS)
        for i, (key, name) in enumerate(F.PHASES):
            gs = F.goals_of(key)
            now_phase = f["phase"] == key
            h = self._gp_head(box, name.upper(), C["good"] if now_phase else C["steel"], top=0 if i == 0 else 12,
                              count=f"{sum(1 for g in gs if g['done'])} / {len(gs)} done" if gs else None)
            if now_phase:
                tk.Label(h, text=" NOW ", bg=C["good"], fg=C["bg"], font=("Segoe UI", 9, "bold")).pack(side="left",
                                                                                                  padx=(8, 0))
            if not gs:
                self._gp_empty(box, "Nothing yet.")
            for g in gs:
                r = tk.Frame(box, bg=P2)
                r.pack(fill="x", pady=(2, 0))
                v = tk.BooleanVar(value=bool(g["done"]))
                self.gp_goal_vars[g["id"]] = v
                ttk.Checkbutton(r, text=g["text"], variable=v, style="Card.TCheckbutton",
                                command=lambda gid=g["id"], v=v: (F.set_done(gid, v.get()), self.gp_fill(),
                                                                  self.gp_overlay())).pack(side="left")
                x = tk.Label(r, text="✕", bg=P2, fg=C["muted"], cursor="hand2")
                x.pack(side="right")
                x.bind("<Button-1>", lambda e, gid=g["id"]: (F.remove_goal(gid), self.gp_fill(), self.gp_overlay()))
                Tooltip(x, "Remove this goal")
                now = cur is not None and cur["id"] == g["id"]
                b = tk.Label(r, text="▸ on the overlay" if now else "▸", bg=P2, fg=C["accent"] if now else C["muted"],
                             cursor="hand2", font=("Segoe UI", 9, "bold" if now else "normal"))
                b.pack(side="right", padx=8)
                b.bind("<Button-1>", lambda e, gid=g["id"]: self.gp_set_now(gid))
                Tooltip(b, "Show this one on the overlay's focus line")
                meta = tk.Frame(box, bg=P2)                # the quieter second line: target, then when it pokes
                meta.pack(fill="x", padx=(24, 0), pady=(0, 4))
                kind, target = F.goal_target(g)
                if kind:
                    have, _t = F.progress(g)
                    if kind in F.AUTO_TARGETS:
                        tk.Label(meta, text=F.progress_text(g), bg=P2, fg=C["text"], font=("Segoe UI", 9)).pack(
                            side="left")
                        tk.Label(meta, text=" from the log", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(
                            side="left")
                    else:
                        tk.Label(meta, text="Act" if kind == "act" else "have", bg=P2, fg=C["muted"],
                                 font=("Segoe UI", 9)).pack(side="left")
                        hv = tk.StringVar(value=f"{g.get('have') or 0:g}")
                        he = ttk.Entry(meta, textvariable=hv, width=5)
                        he.pack(side="left", padx=4)
                        he.bind("<Return>", lambda e, gid=g["id"], hv=hv: self.gp_goal_have(gid, hv.get()))
                        he.bind("<FocusOut>", lambda e, gid=g["id"], hv=hv: self.gp_goal_have(gid, hv.get()))
                        unit = next((u for k, _n, u in F.TARGETS if k == kind), "")
                        tk.Label(meta, text=f"/ {target:g}" + (f" {unit}" if unit and kind != "act" else ""), bg=P2,
                                 fg=C["muted"], font=("Segoe UI", 9)).pack(side="left")
                    self._gp_bar(meta, have / target if target else 0).pack(side="left", padx=(8, 0))
                tk.Label(meta, text="poke: " + trig.get(g["trigger"], g["trigger"]), bg=P2, fg=C["muted"],
                         font=("Segoe UI", 9)).pack(side="right")

    def gp_set_now(self, gid):
        F.cfg()["now"] = gid
        F.save()
        self.gp_fill()
        self.gp_overlay()

    def gp_phase_pick(self, name):
        F.set_phase(next((k for k, n in F.PHASES if n == name), "start"))
        self.gp_fill()
        self.gp_overlay()

    def gp_switch(self):
        self.focus_set_on(bool(self.gp_on.get()))

    def focus_set_on(self, on):
        """League Focus on / off - the page's switch, the overlay's Focus switch and Options › On the overlay."""
        F.cfg()["on"] = bool(on)
        F.save()
        rows = getattr(self, "al_rows", None) or {}                # 2.90.0: Helpers › Focus follows too
        for var in (getattr(self, "gp_on", None), getattr(self, "tk_focus_var", None),
                    (rows.get("focus") or {}).get("on")):
            if var is not None and bool(var.get()) != bool(on):
                var.set(bool(on))
        self.gp_overlay()
        if hasattr(self, "gp_summary"):
            self.gp_summary.config(text=self.gp_summary_text())

    def gp_overlay(self):
        """Redraw the overlay (its focus line and Focus switch follow the plan)."""
        try:
            self.merged_build()
        except Exception:
            pass

    def gp_worth(self):
        """2.73.2: not used any more (Wealth doesn't track live) - goals carry the progress you type."""
        return None

    def gp_goal_have(self, gid, text):
        n = _num(text)
        if n is not None:
            g = F.goal(gid)
            if g is not None and float(g.get("have") or 0) != n:
                F.set_have(gid, n)
                self._gp_goal_rows()
                self.gp_overlay()

    # ---------------- B: stockpile
    def _gp_stock(self, parent):
        P2 = C["panel2"]
        o, box = chrome_section(parent, "Stockpile while it's cheap", "What to buy and sit on. Have = what you type "
                                                                       "(Enter keeps it); Now = poe.ninja for your "
                                                                       "league (or the bulk exchange).", wrap=True)
        o.pack(fill="x", pady=(0, 12))
        self.gp_stock_box = tk.Frame(box, bg=P2)
        self.gp_stock_box.pack(fill="x")
        form = self._gp_add_area(box, "ADD TO STOCKPILE")
        self.gp_s_name, self.gp_s_goal, self.gp_s_under = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.gp_s_cat, self.gp_s_pick = tk.StringVar(value="All"), tk.StringVar()
        self._gp_label(form, 0, "From the exchange")
        r0 = tk.Frame(form, bg=P2)
        r0.grid(row=0, column=1, sticky="ew", pady=2)
        self.gp_s_catbox = ttk.Combobox(r0, textvariable=self.gp_s_cat, state="readonly", width=14,
                                        postcommand=self.gp_stock_catalog)
        self.gp_s_catbox.pack(side="left")
        self.gp_s_catbox.bind("<<ComboboxSelected>>", lambda e: self.gp_stock_filter())
        self.gp_s_pickbox = ttk.Combobox(r0, textvariable=self.gp_s_pick, postcommand=self.gp_stock_filter)
        self.gp_s_pickbox.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.gp_s_pickbox.bind("<KeyRelease>", lambda e: self.gp_stock_filter(typed=True))
        Tooltip(self.gp_s_pickbox, "Pick an item, or type to narrow the list")
        self._gp_label(form, 1, "Or any item by name")
        ttk.Entry(form, textvariable=self.gp_s_name).grid(row=1, column=1, sticky="ew", pady=2)
        self._gp_label(form, 2, "Quantity")
        r2 = tk.Frame(form, bg=P2)
        r2.grid(row=2, column=1, sticky="ew", pady=2)
        ttk.Entry(r2, textvariable=self.gp_s_goal, width=7).pack(side="left")
        bu = tk.Frame(r2, bg=P2)                             # (2.98.0: "Buy under [ ] div each" stays together)
        bu.pack(side="left", padx=(12, 0))
        tk.Label(bu, text="Buy under", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
        ttk.Entry(bu, textvariable=self.gp_s_under, width=7).pack(side="left")
        tk.Label(bu, text="div each", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))
        ttk.Button(r2, text="+ Add", command=self.gp_add_stock).pack(side="right")
        from .style import flowify
        flowify(r2)                                          # 2.98.0: wraps in a narrow window

    def gp_stock_catalog(self):
        """The Currency Exchange's groups (Currency, Omens, Essences ...) for the first box."""
        from . import bulk
        self.gp_s_groups = dict(bulk.catalog())
        cats = ["All"] + list(self.gp_s_groups)
        self.gp_s_catbox.configure(values=cats)
        if not self.gp_s_cat.get():
            self.gp_s_cat.set("All")
        return cats

    def gp_stock_filter(self, typed=False):
        """The items of the picked group, narrowed to what you've typed."""
        if not getattr(self, "gp_s_groups", None):
            self.gp_stock_catalog()
        g = self.gp_s_cat.get() or "All"
        names = ([n for ns in self.gp_s_groups.values() for n in ns] if g == "All"
                 else list(self.gp_s_groups.get(g, [])))
        q = self.gp_s_pick.get().strip().lower() if typed else ""
        if q:
            names = [n for n in names if q in n.lower()]
        self.gp_s_pickbox.configure(values=names[:400])
        return names

    def gp_add_stock(self):
        name = self.gp_s_name.get().strip() or self.gp_s_pick.get().strip()   # typed by hand wins
        if not name:
            return None
        row = F.add_stock(name, int(_num(self.gp_s_goal.get()) or 0), _num(self.gp_s_under.get()))
        for v in (self.gp_s_name, self.gp_s_goal, self.gp_s_under, self.gp_s_pick):
            v.set("")
        self.gp_fill()
        return row

    def gp_have(self, name):
        """2.73.2: what you typed for it (Wealth isn't used - it doesn't track live)."""
        return F.stock_have(name)

    def gp_each(self, name):
        """Its price in divines - always your league's (2.73.4), or None."""
        try:
            from .wealth import WPRICES
            from . import bulk
            each = WPRICES.named(name)
            if each is None:
                xid = bulk.exchange_id(name)
                hit = bulk.cached(SETTINGS.get("league") or "", xid, max_age=6 * 3600) if xid else None
                each = hit[0] if hit else None
            return each
        except Exception:
            return None

    def gp_stock_have(self, name, text):
        n = _num(text)
        if n is not None and F.stock_have(name) != int(n):
            F.set_stock_have(name, n)
            self.gp_fill()

    def _gp_stock_rows(self):
        P2 = C["panel2"]
        box = self.gp_stock_box
        for w in box.winfo_children():
            w.destroy()
        rows = F.cfg()["stockpile"]
        if not rows:
            self._gp_empty(box, "Nothing yet - add what's cheap at league start and worth more later.")
            return
        self._gp_table_head(box, ("Item", "Have / qty", "Buy under", "Now"))
        self.gp_stock_state = {}
        for i, r in enumerate(rows, 2):
            have, each = self.gp_have(r["name"]), self.gp_each(r["name"])
            st = F.stock_status(r, have, each)
            self.gp_stock_state[r["name"]] = st
            tk.Label(box, text=r["name"], bg=P2, fg=C["text"], font=("Segoe UI", 10), anchor="w").grid(
                row=i, column=0, sticky="w", padx=(0, 12), pady=1)
            hf = tk.Frame(box, bg=P2)
            hf.grid(row=i, column=1, sticky="w", padx=(0, 12), pady=1)
            hv = tk.StringVar(value=str(have or 0))
            he = ttk.Entry(hf, textvariable=hv, width=5)
            he.pack(side="left")
            he.bind("<Return>", lambda e, n=r["name"], hv=hv: self.gp_stock_have(n, hv.get()))
            he.bind("<FocusOut>", lambda e, n=r["name"], hv=hv: self.gp_stock_have(n, hv.get()))
            tk.Label(hf, text=f" / {r['goal'] or '-'}", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left")
            tk.Label(box, text=f"{r['under']:g} div" if r.get("under") is not None else "-", bg=P2, fg=C["muted"],
                     font=("Segoe UI", 9), anchor="w").grid(row=i, column=2, sticky="w", padx=(0, 12), pady=1)
            now = (f"{each:.3g} div" if each is not None else "no price") + \
                  ("  · cheap" if st == "cheap" else "  · done" if st == "done" else "")
            tk.Label(box, text=now, bg=P2, fg=C["green"] if st in ("cheap", "done") else
                     (C["text"] if each is not None else C["muted"]),
                     font=("Segoe UI", 9, "bold" if st == "cheap" else "normal"), anchor="w").grid(
                row=i, column=3, sticky="w", padx=(0, 12), pady=1)
            x = tk.Label(box, text="✕", bg=P2, fg=C["muted"], cursor="hand2")
            x.grid(row=i, column=4, sticky="e")
            x.bind("<Button-1>", lambda e, n=r["name"]: (F.remove_stock(n), self.gp_fill()))
            Tooltip(x, "Remove")
        box.columnconfigure(4, weight=1)

    # ---------------- 2.73.3: map supplies
    def _gp_supplies(self, parent):
        P2 = C["panel2"]
        o, box = chrome_section(parent, "Map supplies", "What you use up in maps and when to refill it - every N "
                                                         "maps or N minutes in maps, counted from the game's log. "
                                                         "The poke comes between maps, in town or your hideout.",
                                wrap=True)
        o.pack(fill="x", pady=(0, 12))
        self.gp_sup_on = tk.BooleanVar(value=bool(F.cfg()["pokes"].get("supplies", True)))
        ttk.Checkbutton(box, text="Map supply pokes", variable=self.gp_sup_on, style="Card.TCheckbutton",
                        command=self.gp_sup_switch).pack(anchor="w", pady=(0, 8))
        self.gp_sup_box = tk.Frame(box, bg=P2)
        self.gp_sup_box.pack(fill="x")
        form = self._gp_add_area(box, "ADD A SUPPLY")
        self.gp_u_name, self.gp_u_every = tk.StringVar(), tk.StringVar(value="10")
        self.gp_u_rule = tk.StringVar(value=F.SUPPLY_RULES[0][1])
        self._gp_label(form, 0, "Supply")
        ttk.Combobox(form, textvariable=self.gp_u_name, values=F.SUPPLY_PRESETS).grid(row=0, column=1, sticky="ew",
                                                                                      pady=2)
        self._gp_label(form, 1, "Refill every")
        r1 = tk.Frame(form, bg=P2)
        r1.grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Spinbox(r1, from_=1, to=500, textvariable=self.gp_u_every, width=4).pack(side="left")
        ttk.Combobox(r1, textvariable=self.gp_u_rule, values=[n for _k, n in F.SUPPLY_RULES], state="readonly",
                     width=11).pack(side="left", padx=(4, 0))
        ttk.Button(r1, text="+ Add", command=self.gp_add_supply).pack(side="right")

    def gp_sup_switch(self):
        F.cfg()["pokes"]["supplies"] = bool(self.gp_sup_on.get())
        F.save()

    @staticmethod
    def _gp_rule_key(label):
        return next((k for k, n in F.SUPPLY_RULES if n == label), "maps")

    def gp_add_supply(self):
        name = self.gp_u_name.get().strip()
        if not name:
            return None
        row = F.add_supply(name, self._gp_rule_key(self.gp_u_rule.get()), int(_num(self.gp_u_every.get()) or 10))
        self.gp_u_name.set("")
        self.gp_fill()
        return row

    def gp_set_supply(self, sid, rule_label=None, every=None):
        n = _num(every) if every is not None else None
        F.set_supply(sid, self._gp_rule_key(rule_label) if rule_label else None, int(n) if n else None)
        self._gp_sup_rows()

    def _gp_sup_rows(self):
        P2 = C["panel2"]
        box = self.gp_sup_box
        for w in box.winfo_children():
            w.destroy()
        rows = F.cfg()["supplies"]
        self.gp_sup_cells = {}
        if not rows:
            self._gp_empty(box, "Nothing yet - e.g. Scroll of Wisdom every 10 maps.")
            return
        self._gp_table_head(box, ("Supply", "Refill every", "Since refill"))
        for i, r in enumerate(rows, 2):
            used, every = F.supply_used(r)
            tk.Label(box, text=r["name"], bg=P2, fg=C["text"], font=("Segoe UI", 10), anchor="w").grid(
                row=i, column=0, sticky="w", padx=(0, 12), pady=1)
            ef = tk.Frame(box, bg=P2)
            ef.grid(row=i, column=1, sticky="w", padx=(0, 12), pady=1)
            ev = tk.StringVar(value=str(r["every"]))
            e = ttk.Entry(ef, textvariable=ev, width=4)
            e.pack(side="left")
            e.bind("<Return>", lambda _e, sid=r["id"], ev=ev: self.gp_set_supply(sid, every=ev.get()))
            e.bind("<FocusOut>", lambda _e, sid=r["id"], ev=ev: self.gp_set_supply(sid, every=ev.get()))
            rv = tk.StringVar(value=dict(F.SUPPLY_RULES)[r["rule"]])
            cb = ttk.Combobox(ef, textvariable=rv, values=[n for _k, n in F.SUPPLY_RULES], state="readonly", width=11)
            cb.pack(side="left", padx=(4, 0))
            cb.bind("<<ComboboxSelected>>", lambda _e, sid=r["id"], rv=rv: self.gp_set_supply(sid, rv.get()))
            up = used >= every
            lab = tk.Label(box, text=f"{used} / {every}" + ("  · refill" if up else ""), bg=P2,
                           fg=C["orange"] if up else C["text"], font=("Segoe UI", 9, "bold" if up else "normal"),
                           anchor="w")
            lab.grid(row=i, column=2, sticky="w", padx=(0, 12), pady=1)
            self.gp_sup_cells[r["id"]] = lab
            ok = tk.Label(box, text="↻", bg=P2, fg=C["muted"], cursor="hand2")
            ok.grid(row=i, column=3, sticky="e")
            ok.bind("<Button-1>", lambda _e, rr=r: (F.refilled(rr), F.save(), self._gp_sup_rows()))
            Tooltip(ok, "Refilled - count again from now")
            x = tk.Label(box, text="✕", bg=P2, fg=C["muted"], cursor="hand2")
            x.grid(row=i, column=4, sticky="e", padx=(8, 0))
            x.bind("<Button-1>", lambda _e, sid=r["id"]: (F.remove_supply(sid), self._gp_sup_rows()))
            Tooltip(x, "Remove")
        box.columnconfigure(3, weight=1)

    # ---------------- C: farm plan
    def _gp_farms(self, parent):
        P2 = C["panel2"]
        o, box = chrome_section(parent, "Farm plan", "The strats you mean to run, in order - from Money Makers or "
                                                      "your own.", wrap=True)
        o.pack(fill="x", pady=(0, 12))
        self.gp_farm_box = tk.Frame(box, bg=P2)
        self.gp_farm_box.pack(fill="x")
        form = self._gp_add_area(box, "ADD A FARM")
        self.gp_f_pick, self.gp_f_until, self.gp_f_own = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self._gp_label(form, 0, "From Money Makers")
        self.gp_f_box = ttk.Combobox(form, textvariable=self.gp_f_pick, state="readonly",
                                     postcommand=self.gp_farm_choices)
        self.gp_f_box.grid(row=0, column=1, sticky="ew", pady=2)
        self._gp_label(form, 1, "Or your own")
        ttk.Entry(form, textvariable=self.gp_f_own).grid(row=1, column=1, sticky="ew", pady=2)
        self._gp_label(form, 2, "Until")
        r2 = tk.Frame(form, bg=P2)
        r2.grid(row=2, column=1, sticky="ew", pady=2)
        ttk.Entry(r2, textvariable=self.gp_f_until).pack(side="left", fill="x", expand=True)
        ttk.Button(r2, text="+ Add", command=self.gp_add_farm).pack(side="right", padx=(8, 0))

    def gp_farm_choices(self):
        from . import moneymakers as MM
        self.gp_f_strats = {s["name"]: s["id"] for s in sorted(MM.all_strats(), key=lambda s: s["name"].lower())}
        self.gp_f_box.configure(values=list(self.gp_f_strats))
        return list(self.gp_f_strats)

    def gp_add_farm(self, name=None, until=None):
        """A strat from Money Makers, or (2.73.4) any farm you type - typed wins."""
        own = (self.gp_f_own.get().strip() if hasattr(self, "gp_f_own") else "") if name is None else ""
        until = until if until is not None else self.gp_f_until.get().strip()
        if own:
            row = F.add_farm(None, own, until)
        else:
            name = name or self.gp_f_pick.get()
            strats = getattr(self, "gp_f_strats", None) or {}
            if not strats:
                self.gp_farm_choices()
                strats = self.gp_f_strats
            if name not in strats:
                return None
            row = F.add_farm(strats[name], name, until)
        for v in (self.gp_f_pick, self.gp_f_until, getattr(self, "gp_f_own", None)):
            if v is not None:
                v.set("")
        self.gp_fill()
        return row

    def _gp_farm_rows(self):
        P2 = C["panel2"]
        box = self.gp_farm_box
        for w in box.winfo_children():
            w.destroy()
        farms = F.cfg()["farms"]
        if not farms:
            self._gp_empty(box, "Nothing yet - pin the strats you plan to run.")
            return
        for i, r in enumerate(farms):
            row = tk.Frame(box, bg=P2)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{i + 1}.", bg=P2, fg=C["muted"], font=("Segoe UI", 10), width=3, anchor="w").pack(
                side="left")
            tk.Label(row, text=r["name"], bg=P2, fg=C["text"], anchor="w",
                     font=("Segoe UI", 10, "bold" if i == 0 else "normal")).pack(side="left")
            if i == 0:
                tk.Label(row, text=" NEXT UP ", bg=C["good"], fg=C["bg"], font=("Segoe UI", 9, "bold")).pack(
                    side="left", padx=(8, 0))
            if not r.get("strat"):
                tk.Label(row, text="  your own", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left")
            for txt, fn, tip in (("✕", lambda i=i: F.remove_farm(i), "Remove"), ("↓", lambda i=i: F.move_farm(i, 1), "Later"),
                                 ("↑", lambda i=i: F.move_farm(i, -1), "Sooner")):
                b = tk.Label(row, text=txt, bg=P2, fg=C["muted"], cursor="hand2", padx=4)
                b.pack(side="right")
                b.bind("<Button-1>", lambda e, fn=fn: (fn(), self.gp_fill()))
                Tooltip(b, tip)
            if r.get("until"):
                tk.Label(row, text="until " + r["until"], bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="right",
                                                                                                    padx=8)

    # ---------------- D: build lock
    def _gp_lock(self, parent):
        P2 = C["panel2"]
        lk = F.cfg()["lock"]
        o, box = chrome_section(parent, "Build lock", "Stop the reroll itch: your league starter, and when you're "
                                                      "allowed to switch. A new level-1 character in the log gets a "
                                                      "poke first.", wrap=True)
        o.pack(fill="x", pady=(0, 12))
        self.gp_lock_on = tk.BooleanVar(value=bool(lk["on"]))
        ttk.Checkbutton(box, text="Build lock on", variable=self.gp_lock_on, style="Card.TCheckbutton",
                        command=self.gp_lock_save).pack(anchor="w", pady=(0, 4))
        form = tk.Frame(box, bg=P2)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        self.gp_lock_vars = {}
        for i, (key, lab) in enumerate((("character", "My character"), ("build", "My build"),
                                        ("until", "Locked until"))):
            self._gp_label(form, i, lab)
            v = tk.StringVar(value=lk.get(key, ""))
            v.trace_add("write", lambda *a: self.gp_lock_save())
            ttk.Entry(form, textvariable=v).grid(row=i, column=1, sticky="ew", pady=2)
            self.gp_lock_vars[key] = v

    def gp_lock_save(self):
        lk = F.cfg()["lock"]
        lk["on"] = bool(self.gp_lock_on.get())
        for k, v in getattr(self, "gp_lock_vars", {}).items():
            lk[k] = v.get().strip()
        F.save()

    # ---------------- K: poke settings
    def _gp_pokes(self, parent):
        P2 = C["panel2"]
        pk = F.cfg()["pokes"]
        o, box = chrome_section(parent, "Pokes", "How often and where the plan reminds you. Quiet by default.",
                                wrap=True)
        o.pack(fill="x", pady=(0, 12))
        self.gp_poke_vars = {}
        self._gp_head(box, "LIMITS", top=0)
        nums = tk.Frame(box, bg=P2)
        nums.pack(fill="x")
        for i, (key, lab, lo, hi) in enumerate((("per_hour", "Pokes an hour, at most", 0, 12),
                                                 ("checkin_min", "Check-in every (min of play)", 0, 240),
                                                 ("snooze_min", "Snooze for (min)", 5, 480))):
            tk.Label(nums, text=lab, bg=P2, fg=C["text"], anchor="w").grid(row=i, column=0, sticky="w", pady=2)
            v = tk.StringVar(value=str(pk[key]))
            ttk.Spinbox(nums, from_=lo, to=hi, textvariable=v, width=5).grid(row=i, column=1, sticky="w", padx=8)
            v.trace_add("write", lambda *a: self.gp_pokes_save())
            self.gp_poke_vars[key] = v
        self._gp_head(box, "WHEN AND WHAT")
        sw = tk.Frame(box, bg=P2)
        sw.pack(fill="x")
        for c in range(2):
            sw.columnconfigure(c, weight=1, uniform="pk")
        for i, (key, lab) in enumerate((("town_only", "Only in town or hideout"), ("session_only", "Only during a session"),
                                        ("milestones", "Milestones from the log"), ("prices", "Stockpile price pokes"),
                                        ("quieter", "Quieter after 3 \"Not today\""), ("sound", "Soft sound"),
                                        ("why", "Say why it showed up"), ("quiet_on", "Quiet hours (23:00-08:00)"),
                                        ("windows", "A Windows notification when the game isn't in front"))):
            v = tk.BooleanVar(value=bool(pk[key]))
            last = key == "windows"
            ttk.Checkbutton(sw, text=lab, variable=v, style="Card.TCheckbutton",
                            command=self.gp_pokes_save).grid(row=i // 2, column=0 if last else i % 2,
                                                             columnspan=2 if last else 1, sticky="w", pady=1)
            self.gp_poke_vars[key] = v
        self._gp_head(box, "TONE")
        tr = tk.Frame(box, bg=P2)
        tr.pack(fill="x")
        self.gp_tone = SegBar(tr, list(F.TONES), command=lambda v: self.gp_pokes_save(), size=9, pad=(8, 4), bg=P2)
        self.gp_tone.pack(side="left")
        self.gp_tone.pick(pk.get("tone", "Gentle"), notify=False)
        ttk.Button(tr, text="Test a poke", command=self.focus_test).pack(side="right")
        ttk.Button(tr, text="History", command=self.focus_history, style="Quiet.TButton").pack(side="right", padx=8)

    def focus_history(self):
        """The last pokes and what you answered."""
        import time as _t
        from tkinter import messagebox
        h = F.cfg()["history"][-15:]
        lines = [f"{_t.strftime('%b %d %H:%M', _t.localtime(x['ts']))}  {x['kind']}: {x['text'].splitlines()[0][:60]}"
                 f"  ->  {x.get('answer') or '-'}" for x in reversed(h)] or ["No pokes yet."]
        messagebox.showinfo("Poke history", "\n".join(lines), parent=self.root)
        return lines

    def gp_pokes_save(self):
        pk = F.cfg()["pokes"]
        for k, v in self.gp_poke_vars.items():
            if isinstance(v, tk.BooleanVar):
                pk[k] = bool(v.get())
            else:
                n = _num(v.get())
                if n is not None:
                    pk[k] = int(n)
        if hasattr(self, "gp_tone"):
            pk["tone"] = self.gp_tone.get()
        F.save()

    # ---------------- all of it
    def gp_fill(self):
        if not hasattr(self, "gp_goal_box"):
            return
        self._gp_goal_rows()
        self._gp_stock_rows()
        self._gp_sup_rows()
        self._gp_farm_rows()
        f = F.cfg()
        if hasattr(self, "gp_phase"):
            self.gp_phase.pick(F.phase_name(f["phase"]), notify=False)
        self.gp_on.set(bool(f["on"]))
        if hasattr(self, "gp_summary"):
            self.gp_summary.config(text=self.gp_summary_text())
        if hasattr(self, "gp_sup_on"):
            self.gp_sup_on.set(bool(f["pokes"].get("supplies", True)))


class FocusPokes:
    """2.73.1: League Focus's pokes over the game - mixed into App. The session tracker's tick hands it the log's
    events (focus_log) and asks every 10 s whether a poke is due (focus_tick); a poke is a small window at the top
    middle of the game, in the overlay's look (the app's theme), that says why it showed up. A click answers it."""

    def focus_log(self, kind, data):
        from . import focus as F
        ak = None
        if kind == "area":
            from .gamelog import area_kind
            ak = area_kind(data.get("area"), data.get("seed"), data.get("level", 0))
        try:
            F.log_event(kind, data, ak)
        except Exception:
            self.log_error("League Focus (log)")

    def focus_tick(self, now=None):
        """-> the poke shown, or None."""
        from . import focus as F
        import time as _t
        now = now or _t.time()
        last = getattr(self, "_focus_last", None)
        if last is not None and now - last < 10 and now >= last:
            return None
        s = self.tk_session
        running = s is not None and s.ended is None and s.paused_at is None
        played = (now - last) if (last is not None and running) else 0.0
        self._focus_last = now
        if getattr(self, "focus_win", None) is not None:
            return None                                    # one at a time
        where = (getattr(s, "where", None) or {}) if s is not None else {}
        in_town = where.get("kind") in ("town", "hideout") if where else True
        poke = F.due(now, in_town=in_town, session=s is not None and s.ended is None, played=played,
                     prices=self.gp_each, have=self.gp_have)
        if poke:
            self.focus_show(poke)
        return poke

    def focus_show(self, poke):
        from . import focus as F
        from .overlaywin import OverlayWindow, pal
        from .alerts_page import game_rect
        title, text, why, buttons = F.poke_text(poke)
        F.sent(poke)
        P = pal()
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        W = 460
        geo = (r[0] + (r[2] - W) // 2, r[1] + int(r[3] * 0.08), W, None)
        w = OverlayWindow(self.root, title.title(), "🎯", geo, palette=P, lockable=False, follow_game=True,
                          no_activate=True, on_close=lambda: self.focus_answer(poke, "ok"))
        bg, fg = P["bg"], P["text"]
        body = tk.Frame(w.body, bg=bg, padx=16, pady=8)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=text, bg=bg, fg=fg, font=(P["font"], 11), justify="left", anchor="w",
                 wraplength=W - 40).pack(fill="x")
        if F.cfg()["pokes"].get("why", True) and why:
            tk.Label(body, text=why, bg=bg, fg=P["muted"], font=(P["font"], 9), justify="left", anchor="w",
                     wraplength=W - 40).pack(fill="x", pady=(8, 0))
        row = tk.Frame(body, bg=bg)
        row.pack(fill="x", pady=(8, 0))
        self.focus_btns = {}
        for i, (key, label) in enumerate(buttons):
            b = ttk.Button(row, text=label, style="Primary.TButton" if i == 0 else "TButton",
                           command=lambda k=key: self.focus_answer(poke, k))
            b.pack(side="left", padx=(0, 8))
            self.focus_btns[key] = b
        self.focus_win, self.focus_poke = w, poke
        w.show()
        pk = F.cfg()["pokes"]
        if pk.get("sound"):
            try:
                self.root.bell()
            except tk.TclError:
                pass
        if pk.get("windows") and getattr(self, "tray", None) is not None:
            try:
                from .overlay import game_active
                if not game_active():
                    self.tray.notify(f"{title.title()}: {text.splitlines()[0]}")
            except Exception:
                pass
        return w

    def focus_answer(self, poke, what):
        from . import focus as F
        w, self.focus_win = getattr(self, "focus_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass
        F.answer(poke, what)
        if what in ("plan", "sidetracked"):
            try:
                self.shell.open("plan")
                self.gp_fill()
            except Exception:
                pass
        elif what == "exchange":
            import webbrowser
            from urllib.parse import quote
            from .config import SETTINGS
            webbrowser.open("https://www.pathofexile.com/trade2/exchange/poe2/" + quote(SETTINGS.get("league") or ""))
        elif what == "done":
            self.gp_fill()
            self.gp_overlay()
        return what

    def focus_test(self):
        """Settings: Test a poke - a nudge (made up if the plan has no goal yet)."""
        from . import focus as F
        g = F.current()
        poke = {"kind": "nudge", "goal": g["id"]} if g else {"kind": "checkin", "goal": None}
        if getattr(self, "focus_win", None) is not None:
            self.focus_answer(self.focus_poke, "ok")
        return self.focus_show(poke)
