"""Price checks > "Add items from: Ctrl+Alt+C | Stash tab" (2.8.0). The Stash tab row; the reading is tabreader.py.
Ctrl+Alt+C keeps working in both modes: the choice only shows or hides the tab row."""
import tkinter as tk
from tkinter import ttk

from .config import save_json, SETTINGS
from .style import C, SegBar
from .tabreader import PCTAB
from .wealth import parse_price_text, parse_trade_link, WEALTH_CURRENCIES

MODES = ["Ctrl+Alt+C", "Stash tab"]


class TabReaderPage:
    """Mixed into App."""

    def build_tab_reader(self, tb):
        """The mode picker (in the toolbar box, first row) and the Stash tab row under it."""
        P1 = C["panel"]
        cfg = SETTINGS.setdefault("pctab", {})
        mrow = tk.Frame(tb, bg=P1, padx=10, pady=6)
        mrow.pack(fill="x", before=tb.winfo_children()[0])
        tk.Label(mrow, text="Add items from", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 8))
        self.pc_mode = SegBar(mrow, MODES, value=cfg.get("mode", MODES[0]), command=lambda v: self.pctab_mode(),
                              size=9, pad=(12, 3))
        self.pc_mode.pack(side="left")
        self.pc_mode_hint = tk.Label(mrow, text="", bg=P1, fg=C["muted"], font=("Segoe UI", 8))
        self.pc_mode_hint.pack(side="left", padx=10)
        # ---- the Stash tab row (shown in that mode)
        row = tk.Frame(tb, bg=P1, padx=10, pady=4)
        self.pc_tabrow = row
        self.pc_tabrow_after = mrow
        tk.Label(row, text="Account", bg=P1, fg=C["muted"]).pack(side="left")
        self.pc_acc = tk.StringVar(value=SETTINGS.get("wealth_account", ""))
        ttk.Entry(row, textvariable=self.pc_acc, width=18).pack(side="left", padx=(6, 12))
        tk.Label(row, text="Tab's price", bg=P1, fg=C["muted"]).pack(side="left")
        self.pc_amt = tk.StringVar(value=str(cfg.get("amount") or ""))
        ttk.Entry(row, textvariable=self.pc_amt, width=9).pack(side="left", padx=(6, 4))
        self.pc_cur = tk.StringVar(value=dict(WEALTH_CURRENCIES).get(cfg.get("currency") or "divine", "Divine Orb"))
        ttk.Combobox(row, textvariable=self.pc_cur, values=[n for _c, n in WEALTH_CURRENCIES], state="readonly",
                     width=14).pack(side="left")
        self.pc_stop = ttk.Button(row, text="Stop", command=self.pctab_stop, state="disabled")
        self.pc_stop.pack(side="right")
        self.pc_read_btn = ttk.Button(row, text="Read tab", style="Accent.TButton", command=self.pctab_read)
        self.pc_read_btn.pack(side="right", padx=(0, 6))
        how = tk.Label(row, text="ⓘ How", bg=P1, fg="#6ea8ff", cursor="hand2", font=("Segoe UI", 9, "underline"))
        how.pack(side="right", padx=(0, 10))
        how.bind("<Button-1>", lambda e: self.pctab_explain())
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
            self.pc_msg.pack(fill="x", after=self.pc_tabrow)
            self.pc_mode_hint.config(text="reads a public stash tab and adds everything on it (Ctrl+Alt+C still works)")
            if not self.pc_msg.cget("text"):
                self.pc_msg.config(text="Make a Premium stash tab public and give the whole tab one price nobody would "
                                        "pay (like 37882 Divine Orbs). Type that price here and press Read tab.",
                                   fg=C["muted"])
        else:
            self.pc_tabrow.pack_forget()
            self.pc_msg.pack_forget()
            self.pc_mode_hint.config(text="hover an item in game and press Ctrl+Alt+C")

    def pctab_explain(self):
        self.pc_msg.config(fg=C["text"], text=(
            "How it works: Path of Exile 2 has no stash access for tools, so the app reads your tab through the trade "
            "site. In game: pick a Premium stash tab, make it public, and give the whole tab one price nobody would pay "
            "(e.g. 37882 Divine Orbs) - that odd price is how the app finds your tab. Don't use a Merchant's tab: those "
            "sell instantly. Press Read tab: every item on it is added here and priced. Items already in the list are "
            "skipped. A new tab listing can take a minute to show on the trade site. The same tab works for Wealth."))

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
        else:
            amount, cur = parse_price_text(txt)
            cur = cur or next((c for c, n in WEALTH_CURRENCIES if n == self.pc_cur.get()), "divine")
        cfg = SETTINGS.setdefault("pctab", {})
        cfg.update(amount=amount, currency=cur)
        if acc:
            SETTINGS["wealth_account"] = acc           # one account name for Wealth and this
        save_json("settings.json", SETTINGS)
        err = self.engine.pctab_start(acc, amount, cur)
        if err:
            return self.pc_msg.config(text=err, fg=C["red"])
        self._pctab = {"added": 0, "already": 0, "unreadable": 0}
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
        """One item from the tab -> a row (unless it's already in the list, or isn't something the app can price)."""
        st = self.__dict__.setdefault("_pctab", {"added": 0, "already": 0, "unreadable": 0})
        if hash(text.strip()) in self.seen_texts:
            st["already"] += 1
            return
        item = self.read_any(text)
        if not item:
            st["unreadable"] += 1
            return
        if any(self.item_sig(r["item"]) == self.item_sig(item) for r in self.records.values()):
            st["already"] += 1
            return
        if self.add_item_text(text):
            st["added"] += 1

    def pctab_finished(self, stopped=False):
        st = getattr(self, "_pctab", {"added": 0, "already": 0, "unreadable": 0})
        self.pc_read_btn.config(state="normal")
        self.pc_stop.config(state="disabled")
        if PCTAB["error"]:
            return self.pc_msg.config(text=PCTAB["error"], fg=C["red"])
        if stopped:
            return self.pc_msg.config(text=f"Stopped. Added {st['added']} item{'s' if st['added'] != 1 else ''}.",
                                      fg=C["good"])
        if not PCTAB["found"]:
            return self.pc_msg.config(fg=C["good"], text=(
                "No listings found at that price. Is the tab public, priced at exactly this amount and currency, and "
                "has the trade site had a minute to show it? Check the account name too (with its #number)."))
        parts = [f"Read {PCTAB['read']} item{'s' if PCTAB['read'] != 1 else ''} from your tab: "
                 f"added {st['added']} to the list"]
        if st["already"]:
            parts.append(f"{st['already']} already in it")
        if st["unreadable"]:
            parts.append(f"{st['unreadable']} the price checker can't price")
        msg = ", ".join(parts) + "." + (" They're being priced now." if st["added"] else "")
        if PCTAB["warnings"]:
            msg += " " + " ".join(PCTAB["warnings"]) + " Move some items to another tab with its own price."
        self.pc_msg.config(text=msg, fg=C["green"] if st["added"] else C["good"])
