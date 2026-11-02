"""Overlay ↳ Game Plan (2.73.0, League Focus part 1): goals by phase, a stockpile to buy while it's cheap, the farm
plan, a build lock and the poke settings - set once at league start, then forget it (focus.py keeps it; the overlay's
focus line and, from 2.73.1, the pokes bring it back when it matters). Every switch is a toggle; everything is
drawn with the app's theme (chrome sections, Card.* styles), so a theme swap repaints it like every other page."""
import tkinter as tk
from tkinter import ttk

from . import focus as F
from .chrome import section as chrome_section
from .style import C, ScrollArea, SegBar, Tooltip


def _num(text):
    try:
        return float(str(text).replace(",", ".").strip())
    except ValueError:
        return None


class GamePlanPage:
    """Mixed into App."""

    def build_game_plan(self, body):
        P1, P2 = C["panel"], C["panel2"]
        f = F.cfg()
        page = tk.Frame(body, bg=P1)
        top = tk.Frame(page, bg=P1, padx=8, pady=8)
        top.pack(fill="x")
        self.gp_on = tk.BooleanVar(value=bool(f["on"]))
        ttk.Checkbutton(top, text="League Focus on", variable=self.gp_on, command=self.gp_switch,
                        style="Bar.TCheckbutton").pack(side="left")
        tk.Label(top, text="Phase", bg=P1, fg=C["muted"]).pack(side="left", padx=(24, 8))
        self.gp_phase = SegBar(top, [n for _k, n in F.PHASES], command=lambda v: self.gp_phase_pick(v), size=9,
                               pad=(8, 4))
        self.gp_phase.pack(side="left")
        self.gp_phase.pick(F.phase_name(f["phase"]), notify=False)
        tk.Label(top, text="Set it once - the overlay's focus line and pokes bring it back when it matters.",
                 bg=P1, fg=C["muted"], font=("Segoe UI", 9)).pack(side="right")
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
        self._gp_farms(right)
        self._gp_lock(right)
        self.gp_fill()
        return page

    # ---------------- A: goals by phase
    def _gp_goals(self, parent):
        P2 = C["panel2"]
        o, box = chrome_section(parent, "Goals by phase", "League start, when you reach maps, long term. ▸ makes "
                                                          "one the goal on the overlay's focus line.", wrap=True)
        o.pack(fill="x", pady=(0, 8))
        self.gp_goal_box = tk.Frame(box, bg=P2)
        self.gp_goal_box.pack(fill="x")
        add = tk.Frame(box, bg=P2)
        add.pack(fill="x", pady=(8, 0))
        self.gp_new = tk.StringVar()
        e = ttk.Entry(add, textvariable=self.gp_new)
        e.pack(side="left", fill="x", expand=True)
        e.bind("<Return>", lambda ev: self.gp_add_goal())
        self.gp_new_phase = tk.StringVar(value=F.PHASES[0][1])
        ttk.Combobox(add, textvariable=self.gp_new_phase, values=[n for _k, n in F.PHASES], state="readonly",
                     width=17).pack(side="left", padx=(8, 0))
        ttk.Button(add, text="+ Add", style="Primary.TButton", command=self.gp_add_goal).pack(side="left", padx=(8, 0))
        opt = tk.Frame(box, bg=P2)
        opt.pack(fill="x", pady=(8, 0))
        tk.Label(opt, text="Poke me", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left")
        self.gp_new_trig = tk.StringVar(value=F.TRIGGERS[0][1])
        ttk.Combobox(opt, textvariable=self.gp_new_trig, values=[n for _k, n in F.TRIGGERS], state="readonly",
                     width=26).pack(side="left", padx=(8, 12))
        tk.Label(opt, text="Target (div, optional)", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left")
        self.gp_new_target = tk.StringVar()
        ttk.Entry(opt, textvariable=self.gp_new_target, width=6).pack(side="left", padx=(8, 0))

    def gp_add_goal(self):
        text = self.gp_new.get().strip()
        if not text:
            return None
        phase = next((k for k, n in F.PHASES if n == self.gp_new_phase.get()), "start")
        trig = next((k for k, n in F.TRIGGERS if n == self.gp_new_trig.get()), "town")
        g = F.add_goal(text, phase, trig, _num(self.gp_new_target.get()) if self.gp_new_target.get().strip() else None)
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
        worth = self.gp_worth()
        for key, name in F.PHASES:
            gs = F.goals_of(key)
            tk.Label(box, text=name.upper() + ("  ·  NOW" if f["phase"] == key else ""), bg=P2,
                     fg=C["good"] if f["phase"] == key else C["muted"], font=("Segoe UI", 9, "bold"),
                     anchor="w").pack(fill="x", pady=(8, 2))
            if not gs:
                tk.Label(box, text="Nothing yet.", bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(fill="x")
            for g in gs:
                r = tk.Frame(box, bg=P2)
                r.pack(fill="x", pady=1)
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
                note = "poke: " + trig.get(g["trigger"], g["trigger"])
                p = F.progress(g, worth)
                if g.get("target_div"):
                    note += f"  ·  {p[0]:.0f} of {p[1]:g} div" if p else f"  ·  target {g['target_div']:g} div"
                tk.Label(box, text=note, bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(fill="x",
                                                                                                padx=(24, 0))

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
        for var in (getattr(self, "gp_on", None), getattr(self, "tk_focus_var", None)):
            if var is not None and bool(var.get()) != bool(on):
                var.set(bool(on))
        self.gp_overlay()

    def gp_overlay(self):
        """Redraw the overlay (its focus line and Focus switch follow the plan)."""
        try:
            self.merged_build()
        except Exception:
            pass

    def gp_worth(self):
        """Your net worth in divines (Wealth's last snapshot), for goals with a target, or None."""
        try:
            from .wealth import WEALTH
            snaps = WEALTH.snapshots
            return float(snaps[-1]["total"]) if snaps else None
        except Exception:
            return None

    # ---------------- B: stockpile
    def _gp_stock(self, parent):
        P2 = C["panel2"]
        o, box = chrome_section(parent, "Stockpile while it's cheap", "What to buy and sit on. Have = your Wealth "
                                                                       "count, Now = poe.ninja (or the bulk exchange).",
                                wrap=True)
        o.pack(fill="x", pady=(0, 8))
        self.gp_stock_box = tk.Frame(box, bg=P2)
        self.gp_stock_box.pack(fill="x")
        add = tk.Frame(box, bg=P2)
        add.pack(fill="x", pady=(8, 0))
        self.gp_s_name, self.gp_s_goal, self.gp_s_under = tk.StringVar(), tk.StringVar(), tk.StringVar()
        tk.Label(add, text="Item", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        ttk.Entry(add, textvariable=self.gp_s_name).pack(side="left", fill="x", expand=True)
        add2 = tk.Frame(box, bg=P2)
        add2.pack(fill="x", pady=(8, 0))
        for lab, var in (("Goal", self.gp_s_goal), ("Buy under (div)", self.gp_s_under)):
            tk.Label(add2, text=lab, bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
            ttk.Entry(add2, textvariable=var, width=7).pack(side="left", padx=(0, 12))
        ttk.Button(add2, text="+ Add", command=self.gp_add_stock).pack(side="right")

    def gp_add_stock(self):
        name = self.gp_s_name.get().strip()
        if not name:
            return None
        row = F.add_stock(name, int(_num(self.gp_s_goal.get()) or 0), _num(self.gp_s_under.get()))
        for v in (self.gp_s_name, self.gp_s_goal, self.gp_s_under):
            v.set("")
        self.gp_fill()
        return row

    def gp_have(self, name):
        try:
            from .wealth import WEALTH
            return sum(int(i.get("qty") or 0) for i in WEALTH.all_items()
                       if (i.get("type") or i.get("base") or "").lower() == name.lower())
        except Exception:
            return None

    def gp_each(self, name):
        try:
            from .wealth import WPRICES
            from . import bulk
            each = WPRICES.named(name)
            if each is None:
                xid = bulk.exchange_id(name)
                hit = bulk.cached(WPRICES.league or "", xid, max_age=6 * 3600) if xid else None
                each = hit[0] if hit else None
            return each
        except Exception:
            return None

    def _gp_stock_rows(self):
        P2 = C["panel2"]
        box = self.gp_stock_box
        for w in box.winfo_children():
            w.destroy()
        rows = F.cfg()["stockpile"]
        if not rows:
            tk.Label(box, text="Nothing yet - add what's cheap at league start and worth more later.", bg=P2,
                     fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(fill="x")
            return
        for c, h in enumerate(("Item", "Have / goal", "Buy under", "Now", "")):
            tk.Label(box, text=h, bg=P2, fg=C["muted"], font=("Segoe UI", 9, "bold"), anchor="w").grid(
                row=0, column=c, sticky="w", padx=(0, 12))
        self.gp_stock_state = {}
        for i, r in enumerate(rows, 1):
            have, each = self.gp_have(r["name"]), self.gp_each(r["name"])
            st = F.stock_status(r, have, each)
            self.gp_stock_state[r["name"]] = st
            vals = (r["name"], f"{have if have is not None else '?'} / {r['goal'] or '-'}",
                    f"{r['under']:g} div" if r.get("under") is not None else "-",
                    (f"{each:.3g} div" if each is not None else "no price") + ("  · cheap" if st == "cheap" else
                                                                               "  · done" if st == "done" else ""))
            for c, v in enumerate(vals):
                tk.Label(box, text=v, bg=P2, fg=C["green"] if c == 3 and st == "cheap" else C["text"],
                         font=("Segoe UI", 9, "bold" if c == 3 and st == "cheap" else "normal"), anchor="w").grid(
                    row=i, column=c, sticky="w", padx=(0, 12), pady=1)
            x = tk.Label(box, text="✕", bg=P2, fg=C["muted"], cursor="hand2")
            x.grid(row=i, column=4, sticky="e")
            x.bind("<Button-1>", lambda e, n=r["name"]: (F.remove_stock(n), self.gp_fill()))

    # ---------------- C: farm plan
    def _gp_farms(self, parent):
        P2 = C["panel2"]
        o, box = chrome_section(parent, "Farm plan", "The strats you mean to run, in order (from Money Makers).",
                                wrap=True)
        o.pack(fill="x", pady=(0, 8))
        self.gp_farm_box = tk.Frame(box, bg=P2)
        self.gp_farm_box.pack(fill="x")
        add = tk.Frame(box, bg=P2)
        add.pack(fill="x", pady=(8, 0))
        self.gp_f_pick, self.gp_f_until = tk.StringVar(), tk.StringVar()
        self.gp_f_box = ttk.Combobox(add, textvariable=self.gp_f_pick, state="readonly", width=28,
                                     postcommand=self.gp_farm_choices)
        self.gp_f_box.pack(side="left")
        tk.Label(add, text="until", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(8, 4))
        ttk.Entry(add, textvariable=self.gp_f_until, width=14).pack(side="left")
        ttk.Button(add, text="+ Add", command=self.gp_add_farm).pack(side="left", padx=(8, 0))

    def gp_farm_choices(self):
        from . import moneymakers as MM
        self.gp_f_strats = {s["name"]: s["id"] for s in sorted(MM.all_strats(), key=lambda s: s["name"].lower())}
        self.gp_f_box.configure(values=list(self.gp_f_strats))
        return list(self.gp_f_strats)

    def gp_add_farm(self, name=None, until=None):
        name = name or self.gp_f_pick.get()
        strats = getattr(self, "gp_f_strats", None) or {}
        if not strats:
            self.gp_farm_choices()
            strats = self.gp_f_strats
        if name not in strats:
            return None
        row = F.add_farm(strats[name], name, until if until is not None else self.gp_f_until.get().strip())
        self.gp_f_pick.set("")
        self.gp_f_until.set("")
        self.gp_fill()
        return row

    def _gp_farm_rows(self):
        P2 = C["panel2"]
        box = self.gp_farm_box
        for w in box.winfo_children():
            w.destroy()
        farms = F.cfg()["farms"]
        if not farms:
            tk.Label(box, text="Nothing yet - pin the strats you plan to run.", bg=P2, fg=C["muted"],
                     font=("Segoe UI", 9), anchor="w").pack(fill="x")
            return
        for i, r in enumerate(farms):
            row = tk.Frame(box, bg=P2)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{i + 1}. {r['name']}" + ("   · next up" if i == 0 else ""), bg=P2,
                     fg=C["text"], anchor="w", font=("Segoe UI", 10, "bold" if i == 0 else "normal")).pack(side="left")
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
                                                      "poke first (2.73.1).", wrap=True)
        o.pack(fill="x", pady=(0, 8))
        self.gp_lock_on = tk.BooleanVar(value=bool(lk["on"]))
        ttk.Checkbutton(box, text="Build lock on", variable=self.gp_lock_on, style="Card.TCheckbutton",
                        command=self.gp_lock_save).pack(anchor="w")
        self.gp_lock_vars = {}
        for key, lab in (("character", "My character"), ("build", "My build"), ("until", "Locked until")):
            r = tk.Frame(box, bg=P2)
            r.pack(fill="x", pady=(8, 0))
            tk.Label(r, text=lab, bg=P2, fg=C["muted"], width=13, anchor="w").pack(side="left")
            v = tk.StringVar(value=lk.get(key, ""))
            v.trace_add("write", lambda *a: self.gp_lock_save())
            ttk.Entry(r, textvariable=v).pack(side="left", fill="x", expand=True)
            self.gp_lock_vars[key] = v

    def gp_lock_save(self):
        lk = F.cfg()["lock"]
        lk["on"] = bool(self.gp_lock_on.get())
        for k, v in getattr(self, "gp_lock_vars", {}).items():
            lk[k] = v.get().strip()
        F.save()

    # ---------------- K: poke settings (the pokes themselves arrive in 2.73.1)
    def _gp_pokes(self, parent):
        P2 = C["panel2"]
        pk = F.cfg()["pokes"]
        o, box = chrome_section(parent, "Pokes", "How often and where the plan reminds you. Quiet by default.",
                                wrap=True)
        o.pack(fill="x", pady=(0, 8))
        self.gp_poke_vars = {}
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
        sw = tk.Frame(box, bg=P2)
        sw.pack(fill="x", pady=(8, 0))
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
        tr = tk.Frame(box, bg=P2)
        tr.pack(fill="x", pady=(8, 0))
        tk.Label(tr, text="Tone", bg=P2, fg=C["text"]).pack(side="left")
        self.gp_tone = SegBar(tr, list(F.TONES), command=lambda v: self.gp_pokes_save(), size=9, pad=(8, 4), bg=P2)
        self.gp_tone.pack(side="left", padx=8)
        self.gp_tone.pick(pk.get("tone", "Gentle"), notify=False)

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
        self._gp_farm_rows()
        f = F.cfg()
        if hasattr(self, "gp_phase"):
            self.gp_phase.pick(F.phase_name(f["phase"]), notify=False)
        self.gp_on.set(bool(f["on"]))
