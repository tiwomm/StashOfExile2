"""Price checks > "Add items from: Manual Add | Stash tab" (2.8.0). The Stash tab row; the reading is tabreader.py.
Ctrl+Alt+C keeps working in both modes: the choice only shows or hides the tab row."""
import tkinter as tk
from tkinter import ttk

from .config import save_json, SETTINGS
from .style import C, SegBar
from .tabreader import PCTAB
from .wealth import parse_price_text, parse_trade_link, WEALTH_CURRENCIES

# 2.40.0: names for trade-site currency ids that aren't in the built-in list (it is replaced by the site's own list a
# moment after start; until then the box still shows the right name)
KNOWN_CURRENCY_NAMES = {"mirror": "Mirror of Kalandra", "divine": "Divine Orb", "exalted": "Exalted Orb",
                        "chaos": "Chaos Orb", "vaal": "Vaal Orb", "regal": "Regal Orb", "annul": "Orb of Annulment",
                        "alch": "Orb of Alchemy", "transmute": "Orb of Transmutation", "aug": "Orb of Augmentation",
                        "chance": "Orb of Chance", "artificers": "Artificer's Orb", "wisdom": "Scroll of Wisdom"}

MODES = ["Manual Add", "Stash tab"]          # 2.8.1: "Manual Add" was called "Ctrl+Alt+C"


class TabReaderPage:
    """Mixed into App."""

    def build_tab_reader(self, tb):
        """The mode picker (in the toolbar box, first row) and the Stash tab row under it."""
        P1 = C["panel"]
        cfg = SETTINGS.setdefault("pctab", {})
        if cfg.get("mode") not in MODES:
            cfg["mode"] = MODES[0]
        mrow = tk.Frame(tb, bg=P1, padx=8, pady=8)
        mrow.pack(fill="x", before=tb.winfo_children()[0])
        tk.Label(mrow, text="Add items from", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 8))
        # 2.31.0: Stash tab is BETA - a good idea that doesn't work well in practice yet (2.38.0: the tag sits inside
        # its button - next to the bar it read as a label for the hint text)
        self.pc_mode = SegBar(mrow, MODES, value=cfg["mode"], command=lambda v: self.pctab_mode(),
                              size=9, pad=(12, 4), badges={"Stash tab": "BETA"})
        self.pc_mode.pack(side="left")
        self.pc_mode_hint = tk.Label(mrow, text="", bg=P1, fg=C["muted"], font=("Segoe UI", 9))
        self.pc_mode_hint.pack(side="left", padx=8)
        # ---- the Stash tab row (shown in that mode)
        row = tk.Frame(tb, bg=P1, padx=8, pady=4)
        self.pc_tabrow = row
        self.pc_tabrow_after = mrow
        tk.Label(row, text="Account", bg=P1, fg=C["muted"]).pack(side="left")
        self.pc_acc = tk.StringVar(value=SETTINGS.get("wealth_account", ""))
        ttk.Entry(row, textvariable=self.pc_acc, width=18).pack(side="left", padx=(8, 12))
        tk.Label(row, text="Tab's price", bg=P1, fg=C["muted"]).pack(side="left")
        self.pc_amt = tk.StringVar(value=str(cfg.get("amount") or ""))
        ttk.Entry(row, textvariable=self.pc_amt, width=9).pack(side="left", padx=(8, 4))
        # 2.40.0: the box is built before the trade site's full currency list arrives, so a saved Mirror of Kalandra
        # isn't in the list yet - it showed "Divine Orb", and Read tab then searched in divines. Show the saved name.
        cid = cfg.get("currency") or "divine"
        self.pc_cur = tk.StringVar(value=dict(WEALTH_CURRENCIES).get(cid) or cfg.get("currency_name")
                                   or KNOWN_CURRENCY_NAMES.get(cid) or "Divine Orb")
        cb = ttk.Combobox(row, textvariable=self.pc_cur, values=[n for _c, n in WEALTH_CURRENCIES], state="readonly",
                          width=24)
        cb.config(postcommand=lambda c=cb: c.config(values=[n for _c, n in WEALTH_CURRENCIES]))   # 2.16.0: full list
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.pctab_cur_picked(), add="+")
        self.pc_cur_box = cb
        self.pc_stop = ttk.Button(row, text="Stop", command=self.pctab_stop, state="disabled")
        self.pc_stop.pack(side="right")
        self.pc_read_btn = ttk.Button(row, text="Read tab", style="Primary.TButton", command=self.pctab_read)
        self.pc_read_btn.pack(side="right", padx=(0, 8))
        self.pc_to_wealth = tk.Label(row, text="＋ Count it in Wealth", bg=P1, fg="#6ea8ff", cursor="hand2",
                                     font=("Segoe UI", 9, "underline"))          # 2.18.0: the same tab in Wealth
        self.pc_to_wealth.bind("<Button-1>", lambda e: self.pctab_to_wealth())
        how = tk.Label(row, text="ⓘ How", bg=P1, fg="#6ea8ff", cursor="hand2", font=("Segoe UI", 9, "underline"))
        how.pack(side="right", padx=(0, 8))
        how.bind("<Button-1>", lambda e: self.pctab_explain())
        self.pc_beta = tk.Label(tb, text="⚠ BETA: reading a stash tab may not work as intended and is of limited "
                                         "use - many tabs read only partly. Ctrl+Alt+C on each item is the reliable "
                                         "way.", bg="#2a2110", fg="#ffcf40", anchor="w", justify="left", padx=12,
                                pady=4, font=("Segoe UI", 9))
        self.pc_beta.bind("<Configure>", lambda e: self.pc_beta.config(wraplength=max(300, e.width - 24)))
        self.pc_msg = tk.Label(tb, text="", bg=P1, fg=C["muted"], anchor="w", justify="left", padx=12,
                               font=("Segoe UI", 9))
        self.pc_msg.bind("<Configure>", lambda e: self.pc_msg.config(wraplength=max(300, e.width - 24)))
        self.pctab_mode(save=False)

    def pctab_mode(self, save=True):
        mode = self.pc_mode.get()
        cfg = SETTINGS.setdefault("pctab", {})
        cfg["mode"] = mode
        if save:
            save_json("settings.json", SETTINGS)
        if not self.records and hasattr(self, "empty_lbl"):
            self.empty_lbl.config(text=self.empty_text)
        if mode == "Stash tab":
            self.pc_tabrow.pack(fill="x", after=self.pc_tabrow_after)
            self.pc_beta.pack(fill="x", after=self.pc_tabrow, padx=8, pady=(2, 0))
            self.pc_msg.pack(fill="x", after=self.pc_beta)
            self.pc_mode_hint.config(text="reads a public stash tab and adds what it can (Ctrl+Alt+C still works)")
            if not self.pc_msg.cget("text"):
                self.pc_msg.config(text="Make a Premium stash tab public and give the whole tab one price nobody would "
                                        "pay (like 37882 Divine Orbs). Type that price here and press Read tab.",
                                   fg=C["muted"])
        else:
            self.pc_tabrow.pack_forget()
            self.pc_beta.pack_forget()
            self.pc_msg.pack_forget()
            self.pc_mode_hint.config(text="hover an item in game and press Ctrl+Alt+C")

    def pctab_wealth_link(self):
        """Show "Count it in Wealth" once a tab was read and Wealth doesn't have it yet."""
        from .wealth import WEALTH
        cfg = SETTINGS.get("pctab") or {}
        have = any(t["amount"] == cfg.get("amount") and t["currency"] == cfg.get("currency") for t in WEALTH.tabs)
        if cfg.get("amount") and cfg.get("read_ok") and not have:
            if not self.pc_to_wealth.winfo_ismapped():
                self.pc_to_wealth.pack(side="right", padx=(0, 8))
        else:
            self.pc_to_wealth.pack_forget()

    def pctab_to_wealth(self):
        cfg = SETTINGS.get("pctab") or {}
        if not hasattr(self, "_wealth_add"):
            return
        if cfg.get("amount") and self._wealth_add(cfg["amount"], cfg.get("currency") or "divine", "Price checks tab"):
            self.pc_msg.config(text="Added to Wealth. Sync there to count it (it's read the same way).", fg=C["green"])
        self.pctab_wealth_link()

    def pctab_explain(self):
        self.pc_msg.config(fg=C["text"], text=(
            "How it works: Path of Exile 2 has no stash access for tools, so the app reads your tab through the trade "
            "site. In game: pick a Premium stash tab, make it public, and give the whole tab one price nobody would pay "
            "(e.g. 37882 Divine Orbs) - that odd price is how the app finds your tab, and a price that high keeps "
            "whispers away (your own listings never count when items are priced). Any currency works. Don't use a "
            "Merchant's tab: those "
            "sell instantly. Press Read tab: every item on it is added here and priced. Items already in the list are "
            "skipped. A new tab listing can take a minute to show on the trade site. The same tab works for Wealth."))

    def pctab_cur_picked(self):
        """2.38.0: keep the tab's currency as soon as it's picked (not only on Read tab), and give the keyboard back
        so nothing else can change it."""
        cur = self.pctab_cur_id()
        if cur:
            cfg = SETTINGS.setdefault("pctab", {})
            cfg.update(currency=cur, currency_name=self.pc_cur.get())     # 2.40.0: the name too (see the box)
            save_json("settings.json", SETTINGS)
        cb = getattr(self, "pc_cur_box", None)

        def done():                                    # 2.40.0: no lingering highlight; the keyboard leaves the box
            try:
                cb.selection_clear()
                cb.winfo_toplevel().focus_set()
            except (tk.TclError, AttributeError):
                self.root.focus_set()
        self.root.after(20, done)

    def ev_currencies_loaded(self):
        """2.40.0: the trade site's full currency list arrived - show the saved currency by its name."""
        cfg = SETTINGS.get("pctab") or {}
        name = dict(WEALTH_CURRENCIES).get(cfg.get("currency"))
        if name and getattr(self, "pc_cur", None) is not None and self.pc_cur.get() != name:
            self.pc_cur.set(name)
            cfg["currency_name"] = name

    def pctab_cur_id(self):
        """The currency id for what the box shows - from the trade site's list, or the saved one when the box shows
        the saved name (the list may not be loaded yet)."""
        name = self.pc_cur.get()
        cur = next((c for c, n in WEALTH_CURRENCIES if n == name), None)
        cfg = SETTINGS.get("pctab") or {}
        if cur is None and name and name == cfg.get("currency_name"):
            cur = cfg.get("currency")
        if cur is None:
            cur = next((c for c, n in KNOWN_CURRENCY_NAMES.items() if n == name), None)
        return cur

    def pctab_read(self):
        acc = self.pc_acc.get().strip()
        txt = self.pc_amt.get().strip()
        if "trade2/search" in txt:                     # a pasted trade-site link: read account and price from it
            info, err = parse_trade_link(txt)
            if err:
                return self.pc_msg.config(text=err, fg=C["red"])
            acc = info["account"] or acc
            self.pc_acc.set(acc)
            amount, cur = info["amount"], info["currency"]
            self.pc_amt.set(str(amount))
            self.pc_cur.set(dict(WEALTH_CURRENCIES).get(cur, cur))
            SETTINGS.setdefault("pctab", {})["currency_name"] = self.pc_cur.get()
        else:
            amount, cur = parse_price_text(txt)
            cur = cur or self.pctab_cur_id() or "divine"
        cfg = SETTINGS.setdefault("pctab", {})
        cfg.update(amount=amount, currency=cur)
        if dict(WEALTH_CURRENCIES).get(cur):
            cfg["currency_name"] = dict(WEALTH_CURRENCIES)[cur]
        from .market import remember_marker
        remember_marker(amount, cur)                   # 2.18.0: never counted as someone's price
        if acc:
            SETTINGS["wealth_account"] = acc           # one account name for Wealth and this
        save_json("settings.json", SETTINGS)
        err = self.engine.pctab_start(acc, amount, cur)
        if err:
            return self.pc_msg.config(text=err, fg=C["red"])
        self._pctab = {"added": 0, "already": 0, "unreadable": 0, "failed": 0}
        self.pc_read_btn.config(state="disabled")
        self.pc_stop.config(state="normal")
        self.pc_msg.config(text="Searching your tab…", fg=C["muted"])

    def pctab_stop(self):
        PCTAB["cancel"] = True
        PCTAB["running"] = False
        self.pctab_finished(stopped=True)

    def ev_pctab(self, what, *args):
        if what == "item":
            self.pctab_add(args[0])
        elif what == "progress":
            st = getattr(self, "_pctab", {})
            self.pc_msg.config(fg=C["muted"], text=f"{PCTAB['msg']}  ·  added {st.get('added', 0)}"
                               + (f", {st['already']} already in the list" if st.get("already") else ""))
        elif what == "done":
            self.pctab_finished()

    def pctab_add(self, text):
        """One item from the tab -> a row (unless it's already in the list, or isn't something the app can price).
        2.8.1: what happens to each one goes in tab_reader_log.txt, and an error on one item doesn't hide the rest."""
        st = self.__dict__.setdefault("_pctab", {"added": 0, "already": 0, "unreadable": 0, "failed": 0})
        st.setdefault("failed", 0)
        first = " / ".join(l for l in text.splitlines()[2:4] if l and not l.startswith("--"))
        try:
            if hash(text.strip()) in self.seen_texts:
                st["already"] += 1
                return PCTAB["log"].append(f"already in the list: {first}")
            item = self.read_any(text)
            if not item:
                st["unreadable"] += 1
                return PCTAB["log"].append(f"the price checker can't read it: {first}\n    " +
                                          text.replace("\n", "\n    "))
            if any(self.item_sig(r["item"]) == self.item_sig(item) for r in self.records.values()):
                st["already"] += 1
                return PCTAB["log"].append(f"already in the list: {first}")
            if self.add_item_text(text):
                st["added"] += 1
                PCTAB["log"].append(f"added: {first}")
            else:
                st["unreadable"] += 1
                PCTAB["log"].append(f"couldn't be added: {first}")
        except Exception:
            import traceback
            st["failed"] += 1
            PCTAB["log"].append(f"error on {first}:\n{traceback.format_exc()}")
            self.log_error("adding an item from the stash tab")

    def pctab_finished(self, stopped=False):
        st = getattr(self, "_pctab", {"added": 0, "already": 0, "unreadable": 0})
        self.pc_read_btn.config(state="normal")
        self.pc_stop.config(state="disabled")
        from .tabreader import write_log
        PCTAB["log"].append(f"result: added {st.get('added', 0)}, already {st.get('already', 0)}, can't read "
                            f"{st.get('unreadable', 0)}, errors {st.get('failed', 0)}"
                            + (f"; stopped" if stopped else "") + (f"; error: {PCTAB['error']}" if PCTAB["error"] else ""))
        write_log(PCTAB["log"])
        if PCTAB["error"]:
            return self.pc_msg.config(text=PCTAB["error"], fg=C["red"])
        if stopped:
            return self.pc_msg.config(text=f"Stopped. Added {st['added']} item{'s' if st['added'] != 1 else ''}.",
                                      fg=C["good"])
        if not PCTAB["found"]:
            return self.pc_msg.config(fg=C["good"], text=(
                "No listings found at that price. Is the tab public, priced at exactly this amount and currency, and "
                "has the trade site had a minute to show it? Check the account name too (with its #number)."))
        parts = [f"Found {PCTAB['found']} listing{'s' if PCTAB['found'] != 1 else ''} at that price, read "
                 f"{PCTAB['read']}: added {st['added']} to the list"]
        if st["already"]:
            parts.append(f"{st['already']} already in it")
        if st["unreadable"]:
            parts.append(f"{st['unreadable']} the price checker can't read")
        if st.get("failed"):
            parts.append(f"{st['failed']} hit an error")
        msg = ", ".join(parts) + "."
        if PCTAB["skipped"]:
            msg += " Left out: " + ", ".join(f"{n} {why}" for why, n in PCTAB["skipped"].items()) + "."
        if PCTAB["found"] and PCTAB["found"] < 10 and not st["added"]:
            msg += (" Only a few found? Items with their own price note keep that price - they aren't found by the "
                    "tab's price.")
        msg += (" They're being priced now." if st["added"] else "") + "  (Every item: tab_reader_log.txt)"
        SETTINGS.setdefault("pctab", {})["read_ok"] = True
        self.pctab_wealth_link()
        if PCTAB["warnings"]:
            msg += " " + " ".join(PCTAB["warnings"]) + " Move some items to another tab with its own price."
        self.pc_msg.config(text=msg, fg=C["green"] if st["added"] else C["good"])
