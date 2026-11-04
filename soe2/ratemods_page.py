"""2.96.0: Help rate mods - the one-at-a-time rater, the (once, gentle) ask, and the Bulk Pricing floor settings.
See ratemods.py for the rules. GGG ToS: your own settings only; nothing touches the game."""
import random
import tkinter as tk
from tkinter import ttk

from . import ratemods as RM
from .style import C

SETS = (("tablet", "Tablets"), ("jewel", "Jewels"), ("waystone", "Waystones"), ("relic", "Relics"))
WHAT = ("S / A: the price hangs on it (High).  B / C / D: it adds a little (Normal; the lower, the sooner it's left out "
        "when too few listings have everything).  Ignore: buyers don't pay for it.")


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

    def rm_open(self, set_name=None):
        old = getattr(self, "rm_win", None)
        if old is not None and old.winfo_exists():
            old.lift()
            return old
        P2 = C["panel2"]
        w = self.rm_win = tk.Toplevel(self.root, bg=P2)
        w.title("Rate mods")
        w.transient(self.root)
        w.resizable(False, False)
        box = tk.Frame(w, bg=P2, padx=16, pady=16)
        box.pack(fill="both", expand=True)
        top = tk.Frame(box, bg=P2)
        top.pack(fill="x")
        tk.Label(top, text="Rate mods", bg=P2, fg=C["text"], font=("Segoe UI", 12, "bold")).pack(side="left")
        sets = self.rm_sets()
        self.rm_set_names = dict((label, s) for s, label in sets)
        self.rm_set_var = tk.StringVar(value=next((label for s, label in sets if s == set_name), sets[0][1]))
        cb = ttk.Combobox(top, textvariable=self.rm_set_var, values=[label for _s, label in sets], state="readonly",
                          width=22)
        cb.pack(side="right")
        cb.bind("<<ComboboxSelected>>", lambda e: self.rm_load())
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
        row.pack(fill="x", pady=(8, 4))
        self.rm_btns = {}
        for g in RM.GRADES:
            b = ttk.Button(row, text="Ignore" if g == "ignore" else g, width=7 if g == "ignore" else 4,
                           style="Primary.TButton" if g in ("S", "A") else "TButton",
                           command=lambda g=g: self.rm_rate(g))
            b.pack(side="left", padx=(0, 8))
            self.rm_btns[g] = b
        ttk.Button(row, text="Skip", style="Quiet.TButton", command=lambda: self.rm_step(1)).pack(side="right")
        ttk.Button(row, text="◀", style="Quiet.TButton", width=3, command=lambda: self.rm_step(-1)).pack(side="right",
                                                                                                         padx=(0, 8))
        tk.Label(box, text=WHAT, bg=P2, fg=C["muted"], font=("Segoe UI", 9), wraplength=480, justify="left",
                 anchor="w").pack(fill="x", pady=(8, 8))
        bot = tk.Frame(box, bg=P2)
        bot.pack(fill="x")
        self.rm_done_lbl = tk.Label(bot, text="", bg=P2, fg=C["good"], font=("Segoe UI", 9), anchor="w")
        self.rm_done_lbl.pack(side="left")
        ttk.Button(bot, text="Done", command=self.rm_close).pack(side="right")
        for k, g in (("s", "S"), ("a", "A"), ("b", "B"), ("c", "C"), ("d", "D"), ("i", "ignore")):
            w.bind(k, lambda e, g=g: self.rm_rate(g))
        w.bind("<Right>", lambda e: self.rm_step(1))
        w.bind("<Left>", lambda e: self.rm_step(-1))
        w.protocol("WM_DELETE_WINDOW", self.rm_close)
        self.rm_rated = 0
        self.rm_load()
        try:
            w.update_idletasks()
            hx, hy, hw = self.root.winfo_rootx(), self.root.winfo_rooty(), self.root.winfo_width()
            w.geometry(f"+{hx + max(0, (hw - w.winfo_reqwidth()) // 2)}+{hy + 80}")
        except tk.TclError:
            pass
        return w

    def rm_load(self):
        s = self.rm_set_names.get(self.rm_set_var.get(), "tablet")
        self.rm_set = s
        self.rm_q = RM.queue(s, self.rm_gear_mods(s) if s.startswith("gear:") else None)
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
        self.rm_now.config(text=f"Yours: {'Ignore' if cur == 'ignore' else cur}" if cur else "Not rated by you yet")
        for g, b in self.rm_btns.items():
            b.state(["pressed"] if g == cur else ["!pressed"])

    def rm_rate(self, grade):
        if not getattr(self, "rm_q", None):
            return None
        keys, _text = self.rm_q[self.rm_i]
        RM.apply(keys, grade)
        self.rm_rated += 1
        self.rm_done_lbl.config(text=f"{self.rm_rated} rated - thanks!")
        affected = [rid for rid, rec in self.records.items() if rec.get("mark", "new") == "new" and rec.get("src") not in
                    ("pc", "fav") and any(RM.key_for(rec, m) in keys for m in rec["item"]["mods"])]
        if affected:
            self.reprice(affected)
        self.rm_step(1)
        return grade

    def rm_step(self, d):
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
        P2 = C["panel2"]
        w = self.rm_ask_win = tk.Toplevel(self.root, bg=P2)
        w.title("Help rate mods?")
        w.transient(self.root)
        w.resizable(False, False)
        box = tk.Frame(w, bg=P2, padx=16, pady=16)
        box.pack(fill="both", expand=True)
        tk.Label(box, text="Help rate mods?", bg=P2, fg=C["text"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(box, text="A minute, one mod at a time: S to D, or Ignore. Your ratings tune your own price checks at "
                           "once. With Community data sharing on they're your vote too, and earn rep when they match "
                           "everyone's. You can also use ▲ / ▼ beside any mod on Price Checks.",
                 bg=P2, fg=C["muted"], wraplength=420, justify="left", anchor="w").pack(fill="x", pady=(8, 12))
        row = tk.Frame(box, bg=P2)
        row.pack(fill="x")

        def pick(what):
            RM.answer(what, random)
            self.rm_ask_close()
            if what == "yes":
                self.rm_open()
        ttk.Button(row, text="Rate a few", style="Primary.TButton", command=lambda: pick("yes")).pack(side="right")
        ttk.Button(row, text="Not now", command=lambda: pick("not_now")).pack(side="right", padx=(0, 8))
        ttk.Button(row, text="No thanks", style="Quiet.TButton", command=lambda: pick("no")).pack(side="left")
        w.protocol("WM_DELETE_WINDOW", lambda: pick("not_now"))
        self.rm_ask_pick = pick
        try:
            w.update_idletasks()
            hx, hy, hw = self.root.winfo_rootx(), self.root.winfo_rooty(), self.root.winfo_width()
            w.geometry(f"+{hx + max(0, hw - w.winfo_reqwidth() - 24)}+{hy + 60}")
        except tk.TclError:
            pass
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
