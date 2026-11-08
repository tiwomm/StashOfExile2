"""2.96.0: Help rate mods - the one-at-a-time rater, the (once, gentle) ask, and the Bulk Pricing floor settings.
See ratemods.py for the rules. GGG ToS: your own settings only; nothing touches the game."""
import random
import tkinter as tk
from tkinter import ttk

from . import buglog
from . import ratemods as RM
from .mods import F_TIP
from .style import C, Tooltip

SETS = (("tablet", "Tablets"), ("jewel", "Jewels"), ("waystone", "Waystones"), ("relic", "Relics"))
WHAT = ("S / A: the price hangs on it (High).  B / C / D: it adds a little (Normal; the lower, the sooner it's left out "
        "when too few listings have everything).  F: ignore - buyers don't pay for it.")
SHOWN = (("S", "S"), ("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("ignore", "F"))   # 2.97.0: F is the ignore tier


def grade_label(g):
    return "F (ignore)" if g == "ignore" else g


def on_top(w):
    """2.97.0 (feedback: it opened behind the app): in front, with focus, once - then a normal window again."""
    try:
        w.deiconify()
        w.lift()
        w.attributes("-topmost", True)
        w.after(400, lambda: w.winfo_exists() and w.attributes("-topmost", False))
        w.focus_force()
    except tk.TclError:
        pass


class RateModsPage:
    """Mixed into App."""

    # ---------------------------------------------------------------- the rater
    def rm_sets(self):
        """[(set, label)]: the four rule sets, every gear class (2.99.0: from the game data), then each unique you've
        price checked."""
        from . import gearbook as GB
        out = list(SETS) + [(f"gear:{c}", f"Gear: {n}") for c, n in GB.classes()]
        uniq = sorted(GB.store(), key=str.lower)
        return out + [(f"unique:{n.lower()}", f"Unique: {n}") for n in uniq]

    def rm_gear_mods(self, set_name):
        from . import gearbook as GB
        if set_name.startswith("gear:"):                     # 2.99.0: every line that rolls on the class
            out = [(r["key"], r["text"]) for r in GB.class_mods(set_name[5:])]
        else:
            name = next((n for n in GB.store() if f"unique:{n.lower()}" == set_name), None)
            out = [(r["key"], r["text"]) for r in GB.unique_rows(name)] if name else []
        for rec in self.records.values():
            if RM.set_of(rec) != set_name:
                continue
            for m in (rec.get("item") or {}).get("mods") or []:
                k = RM.key_for(rec, m)
                if k:
                    out.append((k, m.get("shown") or m["text"]))
        return out

    def rm_queue(self, s):
        return RM.queue(s, self.rm_gear_mods(s) if s.startswith(("gear:", "unique:")) else None)

    # 2.120.0 (UX pass 2, feedback: "window drawing is really janky"): a page, Price Checks ↳ Rate Mods - it was a
    # window that changed size between its two views (and shared self.rm_win with the Expedition tags, so showing
    # remnant prices could break it). The item kinds stay on the left, the rater on the right; nothing is rebuilt
    # between mods, only re-filled.
    def build_ratemods_page(self, body):
        P1, P2 = C["panel"], C["panel2"]
        page = self.rm_page = tk.Frame(body, bg=P1, takefocus=1, highlightthickness=0)
        page.pack(fill="both", expand=True)
        tk.Label(page, text="Rate how much each mod matters to an item's price. Your price checks use it at once; "
                            "with Community data sharing on, it's your vote too.", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w", justify="left").pack(fill="x", padx=12, pady=(8, 4))
        wrap = tk.Frame(page, bg=P1)
        wrap.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        # ---- left: what to rate
        from .style import ScrollArea
        left = tk.Frame(wrap, bg=P2, width=270, highlightthickness=1, highlightbackground=C["line"])
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Label(left, text="Which items do you know best?", bg=P2, fg=C["text"], font=("Segoe UI", 10, "bold"),
                 anchor="w", padx=8, pady=8).pack(fill="x")
        sa = ScrollArea(left, bg=P2)
        sa.pack(fill="both", expand=True)
        self.rm_list = sa.inner
        self.rm_rows = {}
        # ---- right: one mod at a time (built once)
        right = tk.Frame(wrap, bg=P1)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        card = tk.Frame(right, bg=P2, padx=24, pady=16, highlightthickness=1, highlightbackground=C["line"])
        card.pack(fill="x", anchor="n")
        self.rm_box = card
        top = tk.Frame(card, bg=P2)
        top.pack(fill="x")
        self.rm_head = tk.Label(top, text="", bg=P2, fg=C["text"], font=("Segoe UI", 12, "bold"), anchor="w")
        self.rm_head.pack(side="left")
        self.rm_count = tk.Label(top, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="e")
        self.rm_count.pack(side="right")
        self.rm_mod = tk.Label(card, text="", bg=C["panel"], fg=C["magic"], font=("Segoe UI", 12), wraplength=520,
                               justify="center", padx=12, pady=16, height=3)
        self.rm_mod.pack(fill="x", pady=(12, 8))
        self.rm_now = tk.Label(card, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9))
        self.rm_now.pack()
        row = tk.Frame(card, bg=P2)
        row.pack(pady=(8, 4))
        self.rm_btns = {}
        for g, label in SHOWN:                           # one row of tiers; yours is the lit one
            b = ttk.Button(row, text=label, width=5, command=lambda g=g: self.rm_rate(g))
            b.pack(side="left", padx=4)
            self.rm_btns[g] = b
            if g == "ignore":
                Tooltip(b, F_TIP)
        nav = tk.Frame(card, bg=P2)
        nav.pack(pady=(8, 0))
        self.rm_nav = {}
        for k, label, cmd in (("back", "‹ Back", lambda: self.rm_step(-1)), ("next", "Next ›", lambda: self.rm_step(1))):
            b = ttk.Button(nav, text=label, style="Quiet.TButton", width=10, command=cmd)
            b.pack(side="left", padx=4)
            self.rm_nav[k] = b
        self.rm_done_lbl = tk.Label(card, text="", bg=P2, fg=C["good"], font=("Segoe UI", 9))
        self.rm_done_lbl.pack(pady=(8, 0))
        tk.Label(right, text=WHAT, bg=P1, fg=C["muted"], font=("Segoe UI", 9), wraplength=560, justify="left",
                 anchor="w").pack(fill="x", pady=(8, 0))
        tk.Label(right, text="Keys: S A B C D F rate it · ← → move", bg=P1, fg=C["muted"], font=("Segoe UI", 9),
                 anchor="w").pack(fill="x", pady=(4, 0))
        for k, g in (("s", "S"), ("a", "A"), ("b", "B"), ("c", "C"), ("d", "D"), ("f", "ignore"), ("i", "ignore")):
            for w in (page, card):
                w.bind(k, lambda e=None, g=g: self.rm_rate(g))
        for w in (page, card):
            w.bind("<Right>", lambda e=None: self.rm_step(1))
            w.bind("<Left>", lambda e=None: self.rm_step(-1))
        page.bind("<Button-1>", lambda e: page.focus_set(), add="+")
        self.rm_rated, self.rm_q, self.rm_i, self.rm_set = 0, [], 0, None
        self.rm_view = "rate"
        return page

    def rm_on_show(self):
        """The page came up: the list filled (counts change as you price check), the last kind picked."""
        self.rm_fill_list()
        if not getattr(self, "rm_set", None):
            sets = dict(self.rm_sets())
            last = RM.SETTINGS.get("rate_set")
            self.rm_pick(last if last in sets else next(iter(sets)))
        try:
            self.rm_page.focus_set()
        except (AttributeError, tk.TclError):
            pass

    def rm_open(self, set_name=None):
        """Price Checks ↳ Rate Mods (set_name: straight to that kind - the Mod book's button)."""
        if getattr(self, "rm_page", None) is None:
            return None
        self.shell.open("ratemods")
        if set_name:
            self.rm_pick(set_name)
        return self.rm_page

    def rm_fill_list(self):
        """The item kinds, grouped - Map items, Gear, Uniques you've checked - each with how many are left."""
        box = getattr(self, "rm_list", None)
        if box is None:
            return
        for c in box.winfo_children():
            c.destroy()
        self.rm_rows = {}
        P2 = C["panel2"]
        groups = [("Map items", []), ("Gear", []), ("Uniques you've checked", [])]
        for s, label in self.rm_sets():
            g = 1 if s.startswith("gear:") else 2 if s.startswith("unique:") else 0
            groups[g][1].append((s, label.split(": ", 1)[-1]))
        for title, sets in groups:
            if not sets:
                continue
            tk.Label(box, text=title.upper(), bg=P2, fg=C["muted"], font=("Segoe UI", 9, "bold"), anchor="w",
                     padx=8).pack(fill="x", pady=(8, 2))
            for s, label in sets:
                self._rm_row(box, s, label)
        self._rm_paint_rows()

    def _rm_row(self, parent, s, label):
        P2 = C["panel2"]
        q = self.rm_queue(s)
        left = sum(1 for keys, _t in q if RM.current(keys) is None)
        sub = (f"{left} to rate" if left else "all rated ✓") if q else "nothing yet"
        row = tk.Frame(parent, bg=P2, cursor="hand2" if q else "", padx=8, pady=4)
        row.pack(fill="x")
        name = tk.Label(row, text=label, bg=P2, fg=C["text"] if q else C["muted"], anchor="w", font=("Segoe UI", 9))
        name.pack(side="left")
        cnt = tk.Label(row, text=sub, bg=P2, fg=C["muted"], anchor="e", font=("Segoe UI", 9))
        cnt.pack(side="right")
        if q:
            for w in (row, name, cnt):
                w.bind("<Button-1>", lambda e, s=s: self.rm_pick(s))
        self.rm_rows[s] = (row, name, cnt, bool(q))
        return row

    def _rm_paint_rows(self):
        cur = getattr(self, "rm_set", None)
        for s, (row, name, cnt, has) in getattr(self, "rm_rows", {}).items():
            on = s == cur
            bg = C["odd"] if on else C["panel2"]
            try:
                for w in (row, name, cnt):
                    w.config(bg=bg)
                name.config(fg=C["accent"] if on else (C["text"] if has else C["muted"]),
                            font=("Segoe UI", 9, "bold" if on else "normal"))
            except tk.TclError:
                pass

    def _rm_recount(self, s):
        r = getattr(self, "rm_rows", {}).get(s)
        if not r:
            return
        q = self.rm_queue(s)
        left = sum(1 for keys, _t in q if RM.current(keys) is None)
        try:
            r[2].config(text=(f"{left} to rate" if left else "all rated ✓") if q else "nothing yet")
        except tk.TclError:
            pass

    def rm_pick(self, set_name):
        RM.SETTINGS["rate_set"] = set_name
        labels = dict(self.rm_sets())
        self.rm_set = set_name
        self.rm_set_label = labels.get(set_name, set_name)
        if getattr(self, "rm_head", None) is not None:
            self.rm_head.config(text=self.rm_set_label.split(": ", 1)[-1])
            self.rm_done_lbl.config(text="")
        self._rm_paint_rows()
        self.rm_load()

    def rm_load(self):
        self.rm_q = self.rm_queue(self.rm_set)
        cur = [i for i, (keys, _t) in enumerate(self.rm_q) if RM.current(keys) is None]
        self.rm_i = cur[0] if cur else 0                 # (starts at the first one you haven't rated)
        self.rm_show()

    def rm_show(self):
        if getattr(self, "rm_mod", None) is None:
            return
        q, i = self.rm_q, self.rm_i
        if not q:
            self.rm_mod.config(text="Nothing to rate here yet - price check a few of these first.")
            self.rm_now.config(text="")
            self.rm_count.config(text="")
            for b in list(self.rm_btns.values()) + list(self.rm_nav.values()):
                b.state(["disabled"])
            return
        i = self.rm_i = max(0, min(i, len(q) - 1))
        keys, text = q[i]
        cur = RM.current(keys)
        self.rm_count.config(text=f"{i + 1} of {len(q)}")
        self.rm_mod.config(text=text)
        self.rm_now.config(text=f"Yours: {grade_label(cur)}" if cur else "Not rated by you yet")
        for g, b in self.rm_btns.items():
            b.state(["!disabled"])
            b.config(style="Primary.TButton" if g == cur else "TButton")
        self.rm_nav["back"].state(["!disabled"] if i > 0 else ["disabled"])
        self.rm_nav["next"].state(["!disabled"] if i < len(q) - 1 else ["disabled"])

    def rm_rate(self, grade):
        if not getattr(self, "rm_q", None):
            return None
        keys, _text = self.rm_q[self.rm_i]
        RM.apply(keys, grade)
        self.rm_rated += 1
        last = self.rm_i >= len(self.rm_q) - 1
        self.rm_done_lbl.config(text=f"{self.rm_rated} rated - thanks!")
        affected = [rid for rid, rec in self.records.items() if rec.get("mark", "new") == "new" and rec.get("src") not in
                    ("pc", "fav") and any(RM.key_for(rec, m) in keys for m in rec["item"]["mods"])]
        if affected:
            self.reprice(affected)
        self._rm_recount(self.rm_set)
        self._rm_rules_later()
        if last:
            self.rm_show()                                 # the last one: it stays, lit
            self.rm_done_lbl.config(text=f"{self.rm_rated} rated - that's the lot here. Thanks!")
        else:
            self.rm_step(1)
        return grade

    def rm_step(self, d):
        self.rm_i = getattr(self, "rm_i", 0) + d
        self.rm_show()

    def _rm_rules_later(self):
        """The Mod book's lists follow your ratings - once you pause (they were redrawn when the window closed)."""
        job = getattr(self, "_rm_rules_job", None)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except tk.TclError:
                pass

        def go():
            self._rm_rules_job = None
            try:
                self.refresh_rules()
            except Exception:
                buglog.caught()
        self._rm_rules_job = self.root.after(1500, go)

    # ---------------------------------------------------------------- the ask (once; Not now = once more, later)
    def rm_ask_tick(self):
        """Every 10 minutes: enough items priced (or a snooze over) and the app in front - ask, gently."""
        try:
            priced = sum(1 for r in self.records.values() if r.get("state") == "done")
            if RM.should_ask(priced) and getattr(self, "rm_ask_win", None) is None and self.root.focus_displayof():
                self.rm_ask()
        except Exception:
            buglog.caught()
        self.root.after(10 * 60 * 1000, self.rm_ask_tick)

    def rm_ask(self):
        """2.97.0 (feedback): what it is, how long, and that it ends when you say - no "a few" that never stops."""
        P2 = C["panel2"]
        w = self.rm_ask_win = tk.Toplevel(self.root, bg=P2)
        w.title("Help rate mods?")
        w.transient(self.root)
        w.resizable(False, False)
        box = tk.Frame(w, bg=P2, padx=16, pady=16)
        box.pack(fill="both", expand=True)
        tk.Label(box, text="Help rate mods?", bg=P2, fg=C["text"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(box, text="You pick the items you know best, then rate their mods one at a time: S (the price hangs "
                           "on it) to F (ignore). Rate as many or as few as you like - Done ends it.",
                 bg=P2, fg=C["text"], wraplength=440, justify="left", anchor="w").pack(fill="x", pady=(8, 4))
        tk.Label(box, text="Your ratings tune your own price checks right away. With Community data sharing on, "
                           "they're your vote too.",
                 bg=P2, fg=C["muted"], wraplength=440, justify="left", anchor="w").pack(fill="x", pady=(0, 12))
        row = tk.Frame(box, bg=P2)
        row.pack()

        def pick(what):
            RM.answer(what, random)
            self.rm_ask_close()
            if what == "yes":
                self.rm_open()
        self.rm_ask_btns = {}
        for k, label, style in (("yes", "Count me in!", "Primary.TButton"), ("not_now", "Not now", "TButton"),
                                ("no", "Never ask again", "Quiet.TButton")):
            b = ttk.Button(row, text=label, style=style, command=lambda k=k: pick(k))
            b.pack(side="left", padx=4)
            self.rm_ask_btns[k] = b
        tk.Label(box, text="Not now asks once more in a few days. Either way, it's always in Price Checks ↳ "
                           "Rate Mods.",
                 bg=P2, fg=C["muted"], font=("Segoe UI", 9), wraplength=440, justify="center").pack(pady=(12, 0))
        w.protocol("WM_DELETE_WINDOW", lambda: pick("not_now"))
        self.rm_ask_pick = pick
        try:
            from .style import center_over                # 2.114.0: centred over the app (2.114.3: on its monitor)
            center_over(w, self.dlg_parent())
        except tk.TclError:
            pass
        on_top(w)
        return w

    def rm_ask_close(self):
        w, self.rm_ask_win = getattr(self, "rm_ask_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    # ---------------------------------------------------------------- Settings › Price checking › Skip cheap items
    def build_floor_settings(self, row):
        P2 = C["panel2"]
        c = RM.floor_cfg()
        self.floor_on = tk.BooleanVar(value=bool(c["on"]))
        ttk.Checkbutton(row, text="Skip cheap items in Bulk Pricing", variable=self.floor_on,
                        command=self.floor_save).pack(side="left")
        self.floor_vars = {}
        for s, label in (("tablet", "Tablets"), ("jewel", "Jewels"), ("relic", "Relics")):
            tk.Label(row, text=label, bg=P2, fg=C["muted"]).pack(side="left", padx=(16, 4))
            v = tk.StringVar(value=f"{float(c[s]):g}")
            e = ttk.Entry(row, textvariable=v, width=5)
            e.pack(side="left")
            e.bind("<FocusOut>", lambda _e: self.floor_save())
            e.bind("<Return>", lambda _e: self.floor_save())
            tk.Label(row, text="div", bg=P2, fg=C["muted"]).pack(side="left", padx=(2, 0))
            self.floor_vars[s] = v

    def floor_save(self):
        from .config import SETTINGS, save_json
        c = RM.floor_cfg()
        c["on"] = bool(self.floor_on.get())
        for s, v in getattr(self, "floor_vars", {}).items():
            try:
                c[s] = max(0.0, float(str(v.get()).replace(",", ".")))
            except ValueError:
                v.set(f"{float(c[s]):g}")
        save_json("settings.json", SETTINGS)
        return c
