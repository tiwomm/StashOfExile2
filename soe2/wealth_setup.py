"""Wealth, step by step (2.3.0): a small guide that walks you through the first setup.

  1. Count your currency  - hover each stack in game and press Ctrl+C; the list fills in as you go.
  2. Add a stash tab       - optional: for items that aren't currency (tablets, waystones, gear ...).
  3. Done                   - what the numbers mean and what to do next time.

It drives the same buttons as the Wealth window (Count currency, Add tab, Sync), so nothing works differently - it
just does it in order and says what each step is for. It opens by itself the first time you open Wealth with nothing
in it; "Set up step by step" in the Wealth window brings it back."""
import tkinter as tk
from tkinter import ttk

from .config import save_json, SETTINGS
from .pricefmt import fmt_div
from .style import C
from .wealth import WEALTH, WEALTH_CURRENCIES, WEALTH_SYNC

STEPS = ["Count your currency", "Add a stash tab (optional)", "All set"]


class WealthSetup:
    """Mixed into App."""

    def wealth_first_open(self):
        """The first time Wealth opens with nothing in it, the guide opens too."""
        if SETTINGS.get("wealth_setup_seen") or WEALTH.holdings or WEALTH.tabs or WEALTH.snapshots:
            return
        self.wealth_setup_open()

    def wealth_setup_open(self, step=0):
        from .overlaywin import OverlayWindow
        old = getattr(self, "_ws_win", None)
        if old is not None and old.winfo_exists():
            old.lift()
            return self.wealth_setup_show(step)
        w = self.shell.windows.get("wealth")
        x = (w.winfo_rootx() + 80) if w is not None and w.winfo_ismapped() else self.root.winfo_rootx() + 200
        y = (w.winfo_rooty() + 70) if w is not None and w.winfo_ismapped() else self.root.winfo_rooty() + 120
        win = OverlayWindow(self.root, "Set up Wealth", "💰", (x, y, 660, 540), opacity=255, body_bg=C["panel"],
                            app_colours=True, lockable=False, on_close=self.wealth_setup_close)
        self._ws_win = win
        P1 = C["panel"]
        head = tk.Frame(win.body, bg=P1, padx=16, pady=8)
        head.pack(fill="x")
        self._ws_dots = []
        for i, name in enumerate(STEPS):
            lab = tk.Label(head, text=f"{i + 1}  {name}", bg=P1, fg=C["muted"], font=("Segoe UI", 9, "bold"), padx=8)
            lab.pack(side="left")
            self._ws_dots.append(lab)
        self._ws_body = tk.Frame(win.body, bg=P1, padx=16, pady=8)
        self._ws_body.pack(fill="both", expand=True)
        foot = tk.Frame(win.body, bg=P1, padx=16, pady=8)
        foot.pack(fill="x", side="bottom")
        self._ws_back = ttk.Button(foot, text="‹ Back", command=lambda: self.wealth_setup_show(self._ws_step - 1), style="Quiet.TButton")
        self._ws_back.pack(side="left")
        self._ws_next = ttk.Button(foot, text="Next ›", style="Primary.TButton",
                                   command=lambda: self.wealth_setup_show(self._ws_step + 1))
        self._ws_next.pack(side="right")
        self._ws_skip = ttk.Button(foot, text="Skip this step", command=lambda: self.wealth_setup_show(self._ws_step + 1), style="Quiet.TButton")
        self._ws_skip.pack(side="right", padx=8)
        SETTINGS["wealth_setup_seen"] = True
        save_json("settings.json", SETTINGS)
        self.wealth_setup_show(step)

    def wealth_setup_close(self):
        if getattr(self, "w_counting", False) and getattr(self, "_ws_counting", False):
            self.wealth_count_finish()
        self._ws_counting = False
        w = getattr(self, "_ws_win", None)
        if w is not None:
            w.destroy()
        self._ws_win = None

    # ---- the steps
    def wealth_setup_show(self, step):
        step = max(0, min(len(STEPS) - 1, step))
        if getattr(self, "_ws_step", None) == 0 and step != 0 and self.w_counting and self._ws_counting:
            self.wealth_count_finish()                     # leaving step 1 while counting: keep what was copied
            self._ws_counting = False
        self._ws_step = step
        for i, lab in enumerate(self._ws_dots):
            lab.config(fg=C["accent"] if i == step else (C["green"] if i < step else C["muted"]))
        for w in self._ws_body.winfo_children():
            w.destroy()
        (self._ws_count, self._ws_tab, self._ws_done)[step](self._ws_body)
        self._ws_back.config(state="normal" if step else "disabled")
        self._ws_next.config(text="Close" if step == len(STEPS) - 1 else "Next ›",
                             command=self.wealth_setup_close if step == len(STEPS) - 1 else
                             (lambda: self.wealth_setup_show(self._ws_step + 1)))
        if step == len(STEPS) - 1:
            self._ws_skip.pack_forget()
        elif not self._ws_skip.winfo_ismapped():
            self._ws_skip.pack(side="right", padx=8, before=self._ws_next)

    def _ws_text(self, parent, text, **kw):
        lab = tk.Label(parent, text=text, bg=C["panel"], fg=kw.pop("fg", C["text"]), justify="left", anchor="w",
                       wraplength=580, font=kw.pop("font", ("Segoe UI", 10)), **kw)
        lab.pack(fill="x", pady=(0, 8))
        return lab

    def _ws_count(self, body):
        self._ws_text(body, "Count your currency", fg=C["accent"], font=("Segoe UI", 12, "bold"))
        self._ws_text(body, "Currency is most of what people own, and it's the quickest part. Press Start counting, "
                            "then in game hover each currency stack in your stash and press Ctrl+C. Stacks of the "
                            "same currency add up. Come back here and press Finish when you're done.")
        row = tk.Frame(body, bg=C["panel"])
        row.pack(fill="x", pady=(4, 8))
        self._ws_count_btn = ttk.Button(row, text="Start counting", style="Primary.TButton", command=self._ws_count_go)
        self._ws_count_btn.pack(side="left")
        self._ws_count_lbl = tk.Label(row, text="", bg=C["panel"], fg=C["muted"])
        self._ws_count_lbl.pack(side="left", padx=8)
        box = tk.Frame(body, bg=C["panel2"], highlightthickness=1, highlightbackground=C["line"])
        box.pack(fill="both", expand=True)
        self._ws_list = tk.Label(box, text="", bg=C["panel2"], fg=C["text"], justify="left", anchor="nw",
                                 font=("Segoe UI", 10), padx=8, pady=8)
        self._ws_list.pack(fill="both", expand=True)
        self._ws_count_tick()

    def _ws_count_go(self):
        if self.w_counting:
            self.wealth_count_finish()
            self._ws_counting = False
        else:
            self.wealth_count_toggle()
            self._ws_counting = True
        self._ws_count_tick(once=True)

    def _ws_count_tick(self, once=False):
        if getattr(self, "_ws_step", None) != 0 or getattr(self, "_ws_win", None) is None:
            return
        try:
            if self.w_counting:
                tot = {}
                for name, qty, _c in self.w_session:
                    tot[name] = tot.get(name, 0) + qty
                self._ws_count_btn.config(text="Finish")
                self._ws_count_lbl.config(text="● counting - copy your stacks in game with Ctrl+C", fg=C["green"])
                self._ws_list.config(text="\n".join(f"{n}:  {q:,}" for n, q in tot.items()) or
                                     "Nothing copied yet. Hover a stack in game and press Ctrl+C.")
            else:
                self._ws_count_btn.config(text="Count again" if WEALTH.holdings else "Start counting")
                self._ws_count_lbl.config(text=(f"{len(WEALTH.holdings)} kinds of currency counted." if WEALTH.holdings
                                                else ""), fg=C["muted"])
                self._ws_list.config(text="\n".join(f"{n}:  {h.get('qty', 0):,}" for n, h in
                                                    sorted(WEALTH.holdings.items())) or
                                     "Nothing counted yet.")
        except tk.TclError:
            return
        if not once:
            self.root.after(700, self._ws_count_tick)

    def _ws_tab(self, body):
        self._ws_text(body, "Add a stash tab (optional)", fg=C["accent"], font=("Segoe UI", 12, "bold"))
        self._ws_text(body, "For things that aren't currency - tablets, waystones, gear - the app can read a stash "
                            "tab through the trade site (the game has no other way for tools to see your stash). "
                            "In game:")
        self._ws_text(body, "1.  Pick a Premium stash tab and make it public.\n"
                            "2.  Give the whole tab a price nobody would pay, like 37882 Divine Orbs. That odd price "
                            "is how the app finds your tab.\n"
                            "3.  Don't use a Merchant's Tab: those sell instantly, even when you're offline.",
                      fg=C["steel"])
        g = tk.Frame(body, bg=C["panel"])
        g.pack(fill="x", pady=(4, 4))
        tk.Label(g, text="Your account name", bg=C["panel"], fg=C["text"]).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(g, textvariable=self.w_acc, width=26).grid(row=0, column=1, columnspan=2, sticky="w", padx=8)
        tk.Label(g, text="The price on the tab", bg=C["panel"], fg=C["text"]).grid(row=1, column=0, sticky="w", pady=2)
        pr = tk.Frame(g, bg=C["panel"])
        pr.grid(row=1, column=1, columnspan=2, sticky="w", padx=8)
        ttk.Entry(pr, textvariable=self.w_new_amt, width=12).pack(side="left")
        wcb = ttk.Combobox(pr, textvariable=self.w_new_cur, values=[n for _, n in WEALTH_CURRENCIES], state="readonly",
                           width=24)
        wcb.config(postcommand=lambda c=wcb: c.config(values=[n for _, n in WEALTH_CURRENCIES]))   # 2.16.0: full list
        wcb.pack(side="left", padx=(8, 0))
        tk.Label(g, text="A name for it (optional)", bg=C["panel"], fg=C["text"]).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(g, textvariable=self.w_new_name, width=26).grid(row=2, column=1, columnspan=2, sticky="w", padx=8)
        tk.Label(g, text="…or paste a trade-site link", bg=C["panel"], fg=C["text"]).grid(row=3, column=0, sticky="w",
                                                                                      pady=(8, 2))
        lk = tk.Frame(g, bg=C["panel"])
        lk.grid(row=3, column=1, columnspan=2, sticky="w", padx=8, pady=(8, 2))
        ttk.Entry(lk, textvariable=self.w_link, width=40).pack(anchor="w")
        tk.Label(lk, text="(your trade-site search for that price - it fills in the boxes above)", bg=C["panel"],
                 fg=C["muted"], font=("Segoe UI", 9)).pack(anchor="w")
        row = tk.Frame(body, bg=C["panel"])
        row.pack(fill="x", pady=(8, 0))
        ttk.Button(row, text="Add the tab and check it", style="Primary.TButton", command=self._ws_add).pack(side="left")
        self._ws_tab_msg = tk.Label(row, text=f"{len(WEALTH.tabs)} tab{'s' if len(WEALTH.tabs) != 1 else ''} set up."
                                    if WEALTH.tabs else "", bg=C["panel"], fg=C["muted"], justify="left",
                                    wraplength=380, anchor="w")
        self._ws_tab_msg.pack(side="left", padx=8, fill="x", expand=True)

    def _ws_add(self):
        if self.w_link.get().strip():
            before = len(WEALTH.tabs)
            if not self.wealth_add_from_link(quiet=True):
                self._ws_tab_msg.config(text="That link didn't work: " + (self.w_msg.cget("text") or
                                        "copy the whole address of a trade-site search."), fg=C["red"])
                return
            return self._ws_check(len(WEALTH.tabs) > before)
        self.wealth_save_account()
        if not self.w_acc.get().strip():
            self._ws_tab_msg.config(text="Type your account name first (the one on the trade site).", fg=C["red"])
            return
        before = len(WEALTH.tabs)
        if not self.wealth_add_tab(quiet=True):
            self._ws_tab_msg.config(text="Type the price you put on the tab (a number, e.g. 37882) and pick its "
                                         "currency.", fg=C["red"])
            return
        self._ws_check(len(WEALTH.tabs) > before)

    def _ws_check(self, added):
        self._ws_tab_msg.config(text=("Added. " if added else "That tab was already set up. ") +
                                "Checking it on the trade site… this can take a minute.", fg=C["muted"])
        self.wealth_sync()
        self._ws_watch_sync()

    def _ws_watch_sync(self):
        if getattr(self, "_ws_step", None) != 1 or getattr(self, "_ws_win", None) is None:
            return
        try:
            cur = WEALTH_SYNC.get("cur") or {}
            if cur.get("running"):
                self._ws_tab_msg.config(text="Checking it on the trade site…  " + (cur.get("msg") or ""),
                                        fg=C["muted"])
                self.root.after(800, self._ws_watch_sync)
                return
            t = WEALTH.tabs[-1] if WEALTH.tabs else None
            res = WEALTH.results.get(t["id"]) if t else None
            if res and res.get("error"):
                self._ws_tab_msg.config(text="That didn't work: " + res["error"], fg=C["red"])
            elif res and res.get("ts"):
                n = res.get("fetched", 0)
                self._ws_tab_msg.config(text=(f"✔ Found {n} item{'s' if n != 1 else ''} in that tab." if n else
                                              "The trade site found no items with that price yet. Check the tab is "
                                              "public and priced exactly like this - new listings can take a few "
                                              "minutes to show up."),
                                        fg=C["green"] if n else C["good"])
            else:
                self.root.after(800, self._ws_watch_sync)
        except tk.TclError:
            pass

    def _ws_done(self, body):
        from .wealth import wealth_rows, WPRICES
        rows, total, _p = wealth_rows(WEALTH.all_items(), WPRICES, WEALTH.overrides)
        self._ws_text(body, "All set", fg=C["accent"], font=("Segoe UI", 12, "bold"))
        self._ws_text(body, f"Right now you're worth about {fmt_div(total)}." if rows else
                            "Nothing counted yet - you can come back to this any time.",
                      font=("Segoe UI", 12, "bold"), fg=C["good"])
        self._ws_text(body, "What to do next time:\n"
                            "•  Count currency again after a play session (only the stacks you copy change).\n"
                            "•  Press Sync to re-read your stash tabs.\n"
                            "•  Each count or sync saves a snapshot, so the chart shows how your wealth changes - "
                            "pick two under Snapshots to see what changed between them.\n"
                            "•  Right-click an item to set your own price, or go back to the market price.")
        self._ws_text(body, "\"How it works\" in the Wealth window explains each part; \"Set up step by step\" opens "
                            "this guide again.", fg=C["muted"], font=("Segoe UI", 9))
