"""2.96.0: Help rate mods - the one-at-a-time rater, the (once, gentle) ask, and the Bulk Pricing floor settings.
See ratemods.py for the rules. GGG ToS: your own settings only; nothing touches the game."""
import random
import tkinter as tk
from tkinter import ttk

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
        """[(set, label)]: the four rule sets, then each gear class you've price checked."""
        out = list(SETS)
        seen = {}
        for rec in self.records.values():
            s = RM.set_of(rec)
            if s and s.startswith("gear:") and s not in seen:
                seen[s] = (rec.get("item") or {}).get("class") or s[5:].title()
        return out + sorted(((s, f"Gear: {n}") for s, n in seen.items()), key=lambda x: x[1])

    def rm_gear_mods(self, set_name):
        out = []
        for rec in self.records.values():
            if RM.set_of(rec) != set_name:
                continue
            for m in (rec.get("item") or {}).get("mods") or []:
                k = RM.key_for(rec, m)
                if k:
                    out.append((k, m.get("shown") or m["text"]))
        return out

    def rm_queue(self, s):
        return RM.queue(s, self.rm_gear_mods(s) if s.startswith("gear:") else None)

    def rm_open(self, set_name=None):
        """The rater. set_name: straight to that set (the Mod book's button); None: first, which you know best."""
        old = getattr(self, "rm_win", None)
        if old is not None and old.winfo_exists():
            on_top(old)
            if set_name:
                self.rm_pick(set_name)
            return old
        P2 = C["panel2"]
        w = self.rm_win = tk.Toplevel(self.root, bg=P2)
        w.title("Rate mods")
        w.transient(self.root)
        w.resizable(False, False)
        self.rm_box = tk.Frame(w, bg=P2, padx=16, pady=16)
        self.rm_box.pack(fill="both", expand=True)
        for k, g in (("s", "S"), ("a", "A"), ("b", "B"), ("c", "C"), ("d", "D"), ("f", "ignore"), ("i", "ignore")):
            w.bind(k, lambda e=None, g=g: self.rm_rate(g) if getattr(self, "rm_view", "") == "rate" else None)
        w.bind("<Right>", lambda e=None: self.rm_step(1))
        w.bind("<Left>", lambda e=None: self.rm_step(-1))
        w.protocol("WM_DELETE_WINDOW", self.rm_close)
        self.rm_rated = 0
        self.rm_q, self.rm_i = [], 0
        if set_name:
            self.rm_pick(set_name)
        else:
            self.rm_picker()
        try:
            w.update_idletasks()
            hx, hy, hw = self.root.winfo_rootx(), self.root.winfo_rooty(), self.root.winfo_width()
            w.geometry(f"+{hx + max(0, (hw - w.winfo_reqwidth()) // 2)}+{hy + 80}")
        except tk.TclError:
            pass
        on_top(w)
        return w

    def _rm_clear(self):
        for c in self.rm_box.winfo_children():
            c.destroy()

    def rm_picker(self):
        """2.97.0: which items do you know best? Each set with how many of its mods you haven't rated."""
        self._rm_clear()
        self.rm_view = "pick"
        P2, box = C["panel2"], self.rm_box
        tk.Label(box, text="Which items do you know best?", bg=P2, fg=C["text"], font=("Segoe UI", 12, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(box, text="Pick the one you're most sure about. You can switch any time.", bg=P2, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(4, 12))
        last = RM.SETTINGS.get("rate_set")
        self.rm_pick_btns = {}
        grid = tk.Frame(box, bg=P2)
        grid.pack(fill="x")
        for i, (s, label) in enumerate(self.rm_sets()):
            q = self.rm_queue(s)
            left = sum(1 for keys, _t in q if RM.current(keys) is None)
            sub = (f"{left} of {len(q)} not rated yet" if left else f"all {len(q)} rated") if q else "nothing to rate yet"
            b = ttk.Button(grid, text=f"{label}\n{sub}", width=24, style="Primary.TButton" if s == last else "TButton",
                           command=lambda s=s: self.rm_pick(s))
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else 8, 0), pady=(0, 8))
            if not q:
                b.state(["disabled"])
            self.rm_pick_btns[s] = b
        grid.columnconfigure(0, weight=1, uniform="p")
        grid.columnconfigure(1, weight=1, uniform="p")
        bot = tk.Frame(box, bg=P2)
        bot.pack(fill="x", pady=(8, 0))
        ttk.Button(bot, text="Done", style="Quiet.TButton", command=self.rm_close).pack(side="right")

    def rm_pick(self, set_name):
        RM.SETTINGS["rate_set"] = set_name
        labels = dict(self.rm_sets())
        self.rm_set = set_name
        self.rm_set_label = labels.get(set_name, set_name)
        self.rm_rater()
        self.rm_load()

    def rm_rater(self):
        self._rm_clear()
        self.rm_view = "rate"
        P2, box = C["panel2"], self.rm_box
        top = tk.Frame(box, bg=P2)
        top.pack(fill="x")
        tk.Label(top, text=f"Rate mods · {self.rm_set_label}", bg=P2, fg=C["text"],
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(top, text="Change", style="Quiet.TButton", command=self.rm_picker).pack(side="right")
        tk.Label(box, text="One mod at a time. Each rating tunes your own price checks at once - and with Community "
                           "data sharing on, it's your vote too (it earns rep when it matches everyone's).",
                 bg=P2, fg=C["muted"], font=("Segoe UI", 9), wraplength=480, justify="left", anchor="w").pack(
            fill="x", pady=(8, 8))
        self.rm_count = tk.Label(box, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w")
        self.rm_count.pack(fill="x")
        self.rm_mod = tk.Label(box, text="", bg=C["panel"], fg=C["magic"], font=("Segoe UI", 12), wraplength=470,
                               justify="center", padx=12, pady=16)
        self.rm_mod.pack(fill="x", pady=(4, 8))
        self.rm_now = tk.Label(box, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w")
        self.rm_now.pack(fill="x")
        row = tk.Frame(box, bg=P2)
        row.pack(pady=(8, 4))
        self.rm_btns = {}
        for g, label in SHOWN:                           # 2.97.0: one row of tiers; yours is the lit one
            b = ttk.Button(row, text=label, width=5, command=lambda g=g: self.rm_rate(g))
            b.pack(side="left", padx=4)
            self.rm_btns[g] = b
            if g == "ignore":
                Tooltip(b, F_TIP)
        tk.Label(box, text=WHAT, bg=P2, fg=C["muted"], font=("Segoe UI", 9), wraplength=480, justify="left",
                 anchor="w").pack(fill="x", pady=(8, 8))
        self.rm_done_lbl = tk.Label(box, text="", bg=P2, fg=C["good"], font=("Segoe UI", 9))
        self.rm_done_lbl.pack()
        if self.rm_rated:
            self.rm_done_lbl.config(text=f"{self.rm_rated} rated - thanks!")
        bot = tk.Frame(box, bg=P2)                       # 2.97.0: Back | Next | Done, centered under the tiers
        bot.pack(pady=(8, 0))
        self.rm_nav = {}
        for k, label, style, cmd in (("back", "Back", "TButton", lambda: self.rm_step(-1)),
                                     ("next", "Next", "TButton", lambda: self.rm_step(1)),
                                     ("done", "Done", "Quiet.TButton", self.rm_close)):
            b = ttk.Button(bot, text=label, style=style, width=10, command=cmd)
            b.pack(side="left", padx=4)
            self.rm_nav[k] = b

    def rm_load(self):
        self.rm_q = self.rm_queue(self.rm_set)
        self.rm_i = 0
        self.rm_show()

    def rm_show(self):
        q, i = self.rm_q, self.rm_i
        if not q:
            self.rm_mod.config(text="Nothing to rate here yet - price check a few of these first.")
            self.rm_now.config(text="")
            self.rm_count.config(text="")
            return
        i = self.rm_i = max(0, min(i, len(q) - 1))
        keys, text = q[i]
        cur = RM.current(keys)
        self.rm_count.config(text=f"{i + 1} of {len(q)}")
        self.rm_mod.config(text=text)
        self.rm_now.config(text=f"Yours: {grade_label(cur)}" if cur else "Not rated by you yet")
        for g, b in self.rm_btns.items():
            b.config(style="Primary.TButton" if g == cur else "TButton")
        nav = getattr(self, "rm_nav", {})
        if nav:
            nav["back"].state(["!disabled"] if i > 0 else ["disabled"])
            nav["next"].state(["!disabled"] if i < len(q) - 1 else ["disabled"])

    def rm_rate(self, grade):
        if not getattr(self, "rm_q", None) or getattr(self, "rm_view", "") != "rate":
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
        if last:
            self.rm_show()                                 # the last one: it stays, lit, until Done / Change
            self.rm_done_lbl.config(text=f"{self.rm_rated} rated - that's the lot here. Thanks!")
        else:
            self.rm_step(1)
        return grade

    def rm_step(self, d):
        if getattr(self, "rm_view", "") != "rate":
            return
        self.rm_i = getattr(self, "rm_i", 0) + d
        self.rm_show()

    def rm_close(self):
        w, self.rm_win = getattr(self, "rm_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass
        try:
            self.refresh_rules()
        except Exception:
            pass

    # ---------------------------------------------------------------- the ask (once; Not now = once more, later)
    def rm_ask_tick(self):
        """Every 10 minutes: enough items priced (or a snooze over) and the app in front - ask, gently."""
        try:
            priced = sum(1 for r in self.records.values() if r.get("state") == "done")
            if RM.should_ask(priced) and getattr(self, "rm_ask_win", None) is None and self.root.focus_displayof():
                self.rm_ask()
        except Exception:
            pass
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
        tk.Label(box, text="Not now asks once more in a few days. Either way, Rate mods stays in the Mod book and "
                           "Settings › Privacy & community.",
                 bg=P2, fg=C["muted"], font=("Segoe UI", 9), wraplength=440, justify="center").pack(pady=(12, 0))
        w.protocol("WM_DELETE_WINDOW", lambda: pick("not_now"))
        self.rm_ask_pick = pick
        try:
            w.update_idletasks()
            hx, hy, hw = self.root.winfo_rootx(), self.root.winfo_rooty(), self.root.winfo_width()
            w.geometry(f"+{hx + max(0, (hw - w.winfo_reqwidth()) // 2)}+{hy + 80}")
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
