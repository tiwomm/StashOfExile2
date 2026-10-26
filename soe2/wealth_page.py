"""The Wealth page of the window.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import random
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import messagebox
from tkinter import ttk
from .config import save_json, SETTINGS
from .util import _amt, _num
from .net import fmt_stamp
from .rates import RATES
from .trade import ago
from .pricefmt import fmt_div
from .wealth import (
    parse_price_text, parse_trade_link, WEALTH, WEALTH_CURRENCIES, wealth_display_name, wealth_key,
    wealth_rows, WEALTH_SYNC, wealth_trade_url, WPRICES, WEALTH_RARES, rare_sig, parse_stack, COUNTED_TAB, COUNTED_LABEL,
)
from .style import C, FONT_TITLE, SegBar


class _MenuItem:
    """A menu entry that answers .config(state=...) like the button it replaced (2.0 beta 7)."""

    def __init__(self, menu, index):
        self.menu, self.index = menu, index

    def config(self, state="normal", **_kw):
        try:
            self.menu.entryconfigure(self.index, state=state)
        except Exception:
            pass
    configure = config


# ------------------------------------------------------------------ the app
class WealthPage:
    """The Wealth page (mixed into App): tab markers, sync, net worth, history and every item with its value."""

    W_COLS = [("item", "Name", 320, "w"), ("tab", "Tab", 150, "w"), ("qty", "Quantity", 90, "e"),
              ("each", "Price", 100, "e"), ("total", "Total", 110, "e"), ("src", "Priced by", 190, "w")]
    TAB_COLOURS = ["#3c6b2c", "#7a2020", "#2c3290", "#8a7414", "#6a1c1c", "#5c2a14", "#6a6a6a", "#6a3a8a", "#8a5414",
                   "#2a5a6a", "#4a1a6a", "#7a4a2a"]
    CAT_INFO = {"currency": ("💰", "Currency"), "fragment": ("🧩", "Fragments"), "gem": ("💎", "Gems"),
                "jewel": ("🔷", "Jewels"), "map": ("🗺", "Waystones"), "armour": ("🛡", "Armour"),
                "weapon": ("⚔", "Weapons"), "accessory": ("💍", "Jewellery"), "card": ("🃏", "Cards"),
                "flask": ("🧪", "Flasks"), "sanctum": ("🏺", "Relics"), "relic": ("🏺", "Relics"), "other": ("📦", "Other")}
    RANGES = {"24 hours": 86400, "7 days": 7 * 86400, "30 days": 30 * 86400, "Lifetime": None}

    def build_wealth_page(self, tab):
        """2.0 beta 7: laid out like a wealth tracker: the Wealth card (total, change, history), the Breakdown card
        (value per category), your tabs down the side, and every item in a list. Setting up the priced tabs is behind
        "Edit synced tabs". Currency you count by hand (copy it with Ctrl+C while this window is in front, or type it)
        sits in its own "Counted by hand" tab."""
        P1, P2 = C["panel"], C["panel2"]
        lab = dict(bg=P1, fg=C["muted"])
        self.w_tabfilter, self.w_catfilter, self.w_snap_sel = None, None, None
        self.w_counting, self.w_session, self.w_editing = False, [], False
        self.w_msg = tk.Label(tab, text="", anchor="w", justify="left", bg=P1, fg=C["muted"], padx=12,
                              font=("Segoe UI", 10, "bold"))
        self.w_msg.pack(fill="x", pady=(6, 0))
        self.w_msg.bind("<Configure>", lambda e: self.w_msg.config(wraplength=max(300, e.width - 30)))

        # ---- the two cards
        cards = tk.Frame(tab, bg=P1)
        cards.pack(fill="x", padx=10, pady=(6, 8))
        cards.columnconfigure(0, weight=3, uniform="c")
        cards.columnconfigure(1, weight=2, uniform="c")

        def card(col):
            f = tk.Frame(cards, bg=P2, padx=14, pady=10, highlightthickness=1, highlightbackground=C["line"])
            f.grid(row=0, column=col, sticky="nsew", padx=(0, 5) if col == 0 else (5, 0))
            return f
        c1 = card(0)
        head = tk.Frame(c1, bg=P2)
        head.pack(fill="x")
        tk.Label(head, text="Wealth", bg=P2, fg=C["text"], font=(FONT_TITLE, 15, "bold")).pack(side="left")
        how = tk.Label(head, text="ⓘ How it works", bg=P2, fg="#6ea8ff", cursor="hand2", font=("Segoe UI", 9, "underline"))
        how.pack(side="left", padx=(10, 0))                        # 2.0 beta 21
        how.bind("<Button-1>", lambda e: self.wealth_guide())
        setup = tk.Label(head, text="▶ Set up step by step", bg=P2, fg="#6ea8ff", cursor="hand2",
                         font=("Segoe UI", 9, "underline"))
        setup.pack(side="left", padx=(10, 0))                       # 2.3.0
        setup.bind("<Button-1>", lambda e: self.wealth_setup_open())
        self.w_mode = SegBar(head, ["Total", "Daily"], command=lambda v: self.wealth_draw_chart(), size=9, pad=(10, 3))
        self.w_mode.pack(side="left", padx=(16, 8))
        self.w_range = tk.StringVar(value=SETTINGS.get("wealth_range", "7 days"))
        rb = ttk.Combobox(head, textvariable=self.w_range, values=list(self.RANGES), state="readonly", width=10)
        rb.pack(side="left")
        rb.bind("<<ComboboxSelected>>", lambda e: (SETTINGS.__setitem__("wealth_range", self.w_range.get()),
                                                    save_json("settings.json", SETTINGS), self.wealth_draw_chart(),
                                                    self.root.after(20, self.root.focus_set)))
        self.w_total = tk.Label(head, text="-", bg=P2, fg=C["good"], font=("Segoe UI", 22, "bold"))
        self.w_total.pack(side="right")
        self.w_delta = tk.Label(head, text="", bg=P2, fg=C["green"], font=("Segoe UI", 11, "bold"))
        self.w_delta.pack(side="right", padx=(0, 10))
        self.w_equiv = tk.Label(c1, text="", bg=P2, fg=C["steel"], anchor="e")
        self.w_equiv.pack(fill="x")
        self.w_chart = tk.Canvas(c1, height=130, bg=P2, highlightthickness=0)
        self.w_chart.pack(fill="both", expand=True, pady=(2, 0))
        self.w_chart.bind("<Configure>", lambda e: self.wealth_draw_chart())
        self.w_facts = tk.Label(c1, text="", bg=P2, fg=C["muted"], anchor="w", justify="left", font=("Segoe UI", 8))
        self.w_facts.pack(fill="x")

        c2 = card(1)
        head2 = tk.Frame(c2, bg=P2)
        head2.pack(fill="x")
        tk.Label(head2, text="Breakdown", bg=P2, fg=C["text"], font=(FONT_TITLE, 15, "bold")).pack(side="left")
        self.w_bd_mode = SegBar(head2, ["Divines", "Percent"], command=lambda v: self.wealth_breakdown(), size=9, pad=(10, 3))
        self.w_bd_mode.pack(side="right")
        self.w_bd_note = tk.Label(c2, text="", bg=P2, fg=C["muted"], anchor="w", font=("Segoe UI", 8))
        self.w_bd_note.pack(fill="x", pady=(2, 4))
        self.w_bd = tk.Frame(c2, bg=P2)
        self.w_bd.pack(fill="both", expand=True)

        # ---- below: your tabs (or snapshots) on the left, the items on the right
        main = tk.Frame(tab, bg=P1)
        main.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        side = tk.Frame(main, bg=P1, width=196)
        side.pack(side="left", fill="y", padx=(0, 10))
        side.pack_propagate(False)
        self.w_side_mode = SegBar(side, ["Tabs", "Snapshots"], command=lambda v: self.wealth_side(), size=10, pad=(16, 5))
        self.w_side_mode.pack(anchor="w", pady=(0, 8))
        self.w_side_tabs = tk.Frame(side, bg=C["accent"], padx=2, pady=2)
        self.w_side_snaps = tk.Frame(side, bg=P1)
        sv = ttk.Treeview(self.w_side_snaps, columns=("when", "why", "total"), show="headings", selectmode="extended")
        sv.heading("when", text="When")
        sv.heading("why", text="After")
        sv.heading("total", text="Total")
        sv.column("when", width=78, anchor="w")
        sv.column("why", width=50, anchor="w")
        sv.column("total", width=58, anchor="e")
        sv.pack(fill="both", expand=True)
        tk.Label(self.w_side_snaps, text="Ctrl+click two to compare. Delete removes.", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 8), anchor="w").pack(fill="x")
        sv.bind("<<TreeviewSelect>>", lambda e: self.wealth_pick_snapshot())
        self.w_snaps = sv
        self.list_register("wealth", sv, delete=lambda rows: self.wealth_remove_snaps(rows))
        self.w_edit_lbl = tk.Label(side, text="✎ Edit synced tabs", bg=P1, fg=C["blue"] if "blue" in C else "#6ea8ff",
                                   cursor="hand2", font=("Segoe UI", 10), anchor="w")
        self.w_edit_lbl.pack(side="bottom", fill="x", pady=(8, 0))
        self.w_edit_lbl.bind("<Button-1>", lambda e: self.wealth_toggle_edit())

        right = tk.Frame(main, bg=P1)
        right.pack(side="left", fill="both", expand=True)
        abar = tk.Frame(right, bg=P1)                   # 2.4.0: actions on their own row, so none get squeezed out
        abar.pack(fill="x", pady=(0, 6))
        ibar = tk.Frame(right, bg=P1)
        ibar.pack(fill="x", pady=(0, 6))
        self.w_filter = tk.StringVar()
        self.w_filter.trace_add("write", lambda *a: self.wealth_fill_items())
        se = tk.Entry(ibar, textvariable=self.w_filter, width=24, bg=C["odd"], fg=C["text"], insertbackground=C["text"],
                      relief="flat", highlightthickness=1, highlightbackground=C["line"], font=("Segoe UI", 10))
        se.pack(side="left", ipady=4)
        ph = tk.Label(se, text="🔍  Search items", bg=C["odd"], fg=C["muted"], font=("Segoe UI", 10))
        ph.bind("<Button-1>", lambda e: se.focus_set())

        def placeholder(*_a):
            if self.w_filter.get() or self.root.focus_get() is se:
                ph.place_forget()
            else:
                ph.place(x=4, rely=0.5, anchor="w")
        se.bind("<FocusIn>", placeholder, add="+")
        se.bind("<FocusOut>", placeholder, add="+")
        self.w_filter.trace_add("write", placeholder)
        self.root.after(200, placeholder)
        self.w_unpriced = tk.BooleanVar(value=False)
        ttk.Checkbutton(ibar, text="Needs a price", variable=self.w_unpriced, style="Bar.TCheckbutton",
                        command=self.wealth_fill_items).pack(side="left", padx=(12, 4))
        self.w_combine = tk.BooleanVar(value=True)
        ttk.Checkbutton(ibar, text="Combine stacks", variable=self.w_combine, style="Bar.TCheckbutton",
                        command=self.wealth_fill_items).pack(side="left", padx=4)
        self.w_filter_chip = tk.Label(ibar, text="", bg="#2c4a84", fg="#ffffff", padx=8, pady=2, cursor="hand2",
                                      font=("Segoe UI", 9, "bold"))
        self.w_filter_chip.bind("<Button-1>", lambda e: self.wealth_clear_filters())
        more = tk.Menubutton(abar, text="More ▾", bg="#1b2a48", fg=C["text"], activebackground="#2c4a84",
                             activeforeground="#ffffff", relief="flat", padx=10, pady=4, cursor="hand2")
        mm = tk.Menu(more, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84")
        mm.add_command(label="Update prices from poe.ninja", command=self.wealth_update_prices)
        mm.add_command(label="Re-check magic / rare items", command=self.wealth_recheck_rares)
        mm.add_command(label="Add currency by hand…", command=self.wealth_manual_add)
        mm.add_separator()
        mm.add_command(label="Export history (CSV)…", command=self.wealth_export_history)    # 2.2.0
        mm.add_command(label="Export items (CSV)…", command=self.wealth_export_items)
        mm.add_separator()
        mm.add_command(label="Edit synced tabs", command=self.wealth_toggle_edit)
        more.config(menu=mm)
        more.pack(side="right")
        self.w_price_btn = _MenuItem(mm, 0)
        self.w_rares_btn = _MenuItem(mm, 1)
        self.w_stop_btn = ttk.Button(abar, text="Stop", command=self.wealth_stop, state="disabled")
        self.w_stop_btn.pack(side="right", padx=(0, 6))
        self.w_sync_btn = ttk.Button(abar, text="⟳ Sync", style="Accent.TButton", command=self.wealth_sync)
        self.w_sync_btn.pack(side="right", padx=(0, 6))
        self.w_count_btn = ttk.Button(abar, text="Count currency", command=self.wealth_count_toggle)
        self.w_count_btn.pack(side="right", padx=(0, 6))

        self.w_synced = tk.Label(abar, text="", **lab)
        self.w_synced.pack(side="right", padx=(0, 10))

        # counting / "copied a stack" strip (hidden until used)
        self.w_cstrip = tk.Frame(right, bg="#2a2110", padx=12, pady=8, highlightthickness=1, highlightbackground="#7a6428")
        self.w_cstrip_lbl = tk.Label(self.w_cstrip, text="", bg="#2a2110", fg=C["text"], anchor="w", justify="left",
                                     font=("Segoe UI", 10))
        self.w_cstrip_lbl.pack(side="left", fill="x", expand=True)
        self.w_cstrip_btns = tk.Frame(self.w_cstrip, bg="#2a2110")
        self.w_cstrip_btns.pack(side="right")
        self.w_cstrip_lbl.bind("<Configure>", lambda e: self.w_cstrip_lbl.config(wraplength=max(260, e.width - 10)))
        # add by hand (hidden until used)
        self.w_manual = tk.Frame(right, bg=P2, padx=12, pady=8, highlightthickness=1, highlightbackground=C["line"])
        tk.Label(self.w_manual, text="Add by hand", bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold")).pack(side="left")
        self.w_man_name = tk.StringVar()
        self.w_man_qty = tk.StringVar()
        self.w_man_box = ttk.Combobox(self.w_manual, textvariable=self.w_man_name, width=26)
        self.w_man_box.pack(side="left", padx=(10, 6))
        tk.Label(self.w_manual, text="amount", bg=P2, fg=C["muted"]).pack(side="left")
        qe = ttk.Entry(self.w_manual, textvariable=self.w_man_qty, width=9)
        qe.pack(side="left", padx=(6, 6))
        qe.bind("<Return>", lambda e: self.wealth_manual_set())
        ttk.Button(self.w_manual, text="Set", style="Accent.TButton", command=self.wealth_manual_set).pack(side="left")
        ttk.Button(self.w_manual, text="Close", command=lambda: self.w_manual.pack_forget()).pack(side="left", padx=6)

        # ---- the setup of your priced tabs (folded away behind "Edit synced tabs" once you have one)
        self.w_setup = tk.Frame(right, bg=P2, padx=12, pady=10, highlightthickness=1, highlightbackground=C["line"])
        lab2 = dict(bg=P2, fg=C["muted"])
        arow = tk.Frame(self.w_setup, bg=P2)
        arow.pack(fill="x")
        tk.Label(arow, text="Your priced tabs", bg=P2, fg=C["text"], font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(arow, text="Account", **lab2).pack(side="left", padx=(20, 6))
        self.w_acc = tk.StringVar(value=SETTINGS.get("wealth_account", ""))
        acc = ttk.Entry(arow, textvariable=self.w_acc, width=24)
        acc.pack(side="left")
        acc.bind("<FocusOut>", lambda e: self.wealth_save_account())
        acc.bind("<Return>", lambda e: (self.wealth_save_account(), self.root.focus_set()))
        ttk.Button(arow, text="Done", command=self.wealth_toggle_edit).pack(side="right")
        self.w_help = tk.Label(self.w_setup, text="In game, make a Premium stash tab public and price the whole tab at "
                                                  "something nobody would pay, like 37882 Divine Orbs. Add that price "
                                                  "below. Each tab needs its own price. Never use a Merchant's Tab: those "
                                                  "sell instantly, even when you're offline.\nCurrency doesn't need a "
                                                  "tab: press Count currency and copy each stack in game with Ctrl+C.",
                               bg=P2, fg=C["muted"], justify="left", anchor="w", font=("Segoe UI", 9), wraplength=700)
        self.w_help.pack(fill="x", pady=(4, 6))
        tvf = tk.Frame(self.w_setup, bg=P2)
        tvf.pack(fill="x", pady=(4, 0))
        self.w_tabs = ttk.Treeview(tvf, columns=("tab", "marker", "items", "value", "last"), show="headings",
                                   height=3, selectmode="browse")
        for cid, title, w, anchor in (("tab", "Tab", 165, "w"), ("marker", "Price on the tab", 140, "w"),
                                      ("items", "Items", 60, "e"), ("value", "Value", 95, "e"),
                                      ("last", "Last sync", 185, "w")):
            self.w_tabs.heading(cid, text=title)
            self.w_tabs.column(cid, width=w, anchor=anchor, stretch=False)
        self.w_tabs.tag_configure("off", foreground=C["muted"])
        self.w_tabs.tag_configure("bad", foreground=C["red"])
        self.w_tabs.tag_configure("warn", foreground=C["good"])
        self.w_tabs.pack(side="left")
        self.w_tabs.bind("<<TreeviewSelect>>", lambda e: self.wealth_show_tab_result())
        self.w_tabs.bind("<Double-1>", lambda e: self.wealth_open_trade())
        self.list_register("wealth", self.w_tabs, delete=lambda rows: self.wealth_remove_tab(), multi=False)
        add = tk.Frame(self.w_setup, bg=P2, pady=8)
        add.pack(fill="x")
        self.w_add = add
        self.w_new_name = tk.StringVar()
        self.w_new_amt = tk.StringVar()
        self.w_new_cur = tk.StringVar(value=WEALTH_CURRENCIES[0][1])
        tk.Label(add, text="Price", **lab2).pack(side="left")
        self.w_amt_entry = ttk.Entry(add, textvariable=self.w_new_amt, width=9)
        self.w_amt_entry.pack(side="left", padx=(4, 4))
        self.w_amt_entry.bind("<Return>", lambda e: self.wealth_add_tab())
        cur = ttk.Combobox(add, textvariable=self.w_new_cur, values=[n for _, n in WEALTH_CURRENCIES], state="readonly", width=14)
        cur.pack(side="left")
        cur.bind("<<ComboboxSelected>>", lambda e: self.root.after(20, self.root.focus_set), add="+")
        tk.Label(add, text="Name (optional)", **lab2).pack(side="left", padx=(10, 0))
        ttk.Entry(add, textvariable=self.w_new_name, width=12).pack(side="left", padx=(4, 0))
        ttk.Button(add, text="Add tab", command=self.wealth_add_tab).pack(side="left", padx=(8, 0))
        lnk = tk.Frame(self.w_setup, bg=P2)
        lnk.pack(fill="x", pady=(0, 8))
        self.w_lnk = lnk
        tk.Label(lnk, text="or paste a trade link", **lab2).pack(side="left")
        self.w_link = tk.StringVar()
        le = ttk.Entry(lnk, textvariable=self.w_link, width=38)
        le.pack(side="left", padx=(6, 0))
        le.bind("<Return>", lambda e: self.wealth_add_from_link())
        ttk.Button(lnk, text="Add from link", command=self.wealth_add_from_link).pack(side="left", padx=(8, 0))
        acts = tk.Frame(self.w_setup, bg=P2)
        acts.pack(fill="x", pady=(6, 0))
        self.w_acts = acts
        self.w_adding = False
        self.w_add_btn = ttk.Button(acts, text="Add a tab", command=self.wealth_toggle_adding)
        self.w_add_btn.pack(side="left", padx=(0, 6))
        ttk.Button(acts, text="Include / leave out", command=self.wealth_toggle_tab).pack(side="left")
        ttk.Button(acts, text="Remove", command=self.wealth_remove_tab).pack(side="left", padx=6)
        ttk.Button(acts, text="Open on trade site", command=self.wealth_open_trade).pack(side="left")
        self.w_tabinfo = tk.Label(self.w_setup, text="", bg=P2, fg=C["muted"], justify="left", anchor="w",
                                  wraplength=640, font=("Segoe UI", 9))
        self.w_tabinfo.pack(fill="x", pady=(4, 0))

        # ---- every item
        itf = tk.Frame(right, bg=P1)
        itf.pack(fill="both", expand=True)
        self.w_itf = itf
        self.w_items = ttk.Treeview(itf, columns=[c[0] for c in self.W_COLS], show="headings", selectmode="extended",
                                    height=3)            # grows with the window; small so the page never asks for more room
        for cid, title, w, anchor in self.W_COLS:
            self.w_items.heading(cid, text=title, command=lambda c=cid: self.wealth_sort(c))
            self.w_items.column(cid, width=w, anchor=anchor, stretch=(cid in ("item", "src")))
        isb = ttk.Scrollbar(itf, orient="vertical", command=self.w_items.yview)
        self.w_items.configure(yscrollcommand=isb.set)
        isb.pack(side="right", fill="y")
        self.w_items.pack(side="left", fill="both", expand=True)
        for tg, col in (("unique", C["orange"]), ("rare", C["rare"]), ("magic", C["magic"]), ("gem", C["green"]),
                        ("none", C["muted"]), ("held", "#ffe2a8")):
            self.w_items.tag_configure(tg, foreground=col)
        self.w_items.tag_configure("odd", background=C["odd"])
        self.w_items.tag_configure("own", foreground="#7cc7ff")
        self.w_items.bind("<Button-3>", self.wealth_item_menu)
        self.w_items.bind("<Double-1>", self.wealth_set_price)
        self.list_register("wealth", self.w_items, delete=lambda rows: self.wealth_remove_rows(rows))   # 2.4.0
        crow = tk.Frame(right, bg=P1)                    # 2.4.0: under the list - what's in it, Clear and Undo
        crow.pack(fill="x", pady=(4, 0))
        self.undo_button(crow, "wealth").pack(side="right")
        ttk.Button(crow, text="Clear…", command=self.wealth_clear_items).pack(side="right", padx=(0, 6))
        self.w_count = tk.Label(crow, text="", bg=P1, fg=C["muted"], anchor="w", font=("Segoe UI", 8),
                                justify="left")
        self.w_count.pack(side="left", fill="x", expand=True)
        self.w_count.bind("<Configure>", lambda e: self.w_count.config(wraplength=max(200, e.width - 6)))
        self.w_empty = tk.Label(itf, bg=P1, fg=C["muted"], font=("Segoe UI", 11), justify="center",
                                text="Nothing here yet.\nPress Count currency and copy your currency stacks in game "
                                     "(Ctrl+C),\nor set up a priced tab (Edit synced tabs) and press Sync.")
        self.w_rowmap, self.w_sort_col, self.w_sort_rev = {}, "total", True
        self.refresh_wealth(force=True)

    WEALTH_GUIDE = [
        ("What Wealth is", "An estimate of what your stash is worth, in divines, and how that changes over time. It "
                           "is worked out on your PC from two kinds of items: tabs the app reads through the trade "
                           "site, and currency you count yourself."),
        ("Counted by hand", "The quickest start. Press Count currency, then hover each currency stack in game and "
                            "press Ctrl+C: the stack and its size are added. You can also type a name and amount. "
                            "Double-click a quantity to change it; select rows (Ctrl+A for all) and press Delete to "
                            "remove them."),
        ("Synced tabs", "Path of Exile 2 has no stash API that tools may use, so the app reads a tab through the trade "
                        "site: make the tab public, give it a price nobody would pay (e.g. 37916 Vaal Orbs), and add "
                        "it under Edit synced tabs. Sync searches your account's listings at that price and reads "
                        "them. Sync only runs when you press it, and it shares the trade site's limits with price "
                        "checks (price checks always go first)."),
        ("Prices", "Currency, fragments and other stackables come from poe.ninja. Rares are priced like Price checks "
                   "(slowly, in the background). Double-click an item's price to set your own."),
        ("Total and Breakdown", "Total is everything added up; the chart shows it over time (Daily = the change per "
                                "day). Breakdown splits it by kind (currency, fragments, gear ...)."),
        ("Snapshots", "Each sync or count saves a snapshot of the total, so the chart and the Session tracker can "
                      "show how much you made. Pick one under Snapshots to look back."),
    ]

    def wealth_guide(self):
        """2.0 beta 21: what each part of Wealth does, in one place."""
        old = getattr(self, "_w_guide", None)
        if old is not None and old.winfo_exists():
            old.lift()
            return
        from .overlaywin import OverlayWindow
        w = self.shell.windows.get("wealth")
        x = (w.winfo_rootx() + 60) if w is not None else self.root.winfo_rootx() + 200
        y = (w.winfo_rooty() + 60) if w is not None else self.root.winfo_rooty() + 120
        g = OverlayWindow(self.root, "How Wealth works", "💰", (x, y, 560, 520), opacity=255, body_bg=C["panel"],
                          app_colours=True, lockable=False, on_close=lambda: g.destroy())
        t = tk.Text(g.body, bg=C["panel"], fg=C["text"], relief="flat", wrap="word", padx=14, pady=10,
                    highlightthickness=0, font=("Segoe UI", 10), cursor="arrow")
        t.pack(fill="both", expand=True)
        t.tag_configure("h", foreground=C["accent"], font=("Segoe UI", 11, "bold"), spacing1=8, spacing3=3)
        for head, body in self.WEALTH_GUIDE:
            t.insert("end", head + "\n", "h")
            t.insert("end", body + "\n")
        t.config(state="disabled")
        self._w_guide = g

    # ---------------- 2.0 beta 7: currency counted by hand
    def wealth_takes(self, text):
        """Does this copy belong to the Wealth window? A copied stack (currency, fragments, essences ...) does while you
        are counting, or while the Wealth window is the one in front."""
        if not SETTINGS.get("labs") or not parse_stack(text):        # Wealth is a Labs feature (2.0 beta 10)
            return False
        sh = getattr(self, "shell", None)
        return bool(self.w_counting or (sh is not None and sh.active == "wealth"))

    def wealth_clip(self, text):
        got = parse_stack(text)
        if not got:
            return
        name, qty, cls = got
        if self.w_counting:
            self.w_session.append((name, qty, cls))
            self.wealth_count_strip()
            self._say(f"Counted {name} x{qty:,}", 4)
            return
        have = WEALTH.holding(name)
        if not have:
            WEALTH.set_holding(name, qty, cls)
            self._w_strip(f"Added {name} x{qty:,} to Counted by hand.", [("Undo", lambda: (WEALTH.set_holding(name, 0),
                                                                                            self._w_strip_close(),
                                                                                            self.refresh_wealth(force=True)))])
            self.refresh_wealth(force=True)
            return
        self._w_strip(f"{name} x{qty:,} copied. You already have {have:,} counted.",
                      [(f"Add ({have + qty:,})", lambda: self._w_held_set(name, have + qty, cls)),
                       (f"Replace ({qty:,})", lambda: self._w_held_set(name, qty, cls)),
                       ("Type an amount…", lambda: self._w_held_ask(name, cls)),
                       ("Cancel", self._w_strip_close)], accent=0)

    def _w_held_set(self, name, qty, cls=""):
        WEALTH.set_holding(name, qty, cls)
        self._w_strip_close()
        self.refresh_wealth(force=True)
        self._say(f"{name}: {qty:,} counted.", 6)

    def _w_held_ask(self, name, cls=""):
        from tkinter import simpledialog
        n = simpledialog.askinteger("How many?", f"How many {name} do you have in all?", parent=self.root,
                                    initialvalue=WEALTH.holding(name) or None, minvalue=0)
        if n is not None:
            self._w_held_set(name, n, cls)

    def _w_strip(self, text, actions=(), accent=None):
        for w in self.w_cstrip_btns.winfo_children():
            w.destroy()
        self.w_cstrip_lbl.config(text=text)
        for i, (label, fn) in enumerate(actions):
            ttk.Button(self.w_cstrip_btns, text=label, command=fn,
                       style="Accent.TButton" if i == accent else "TButton").pack(side="left", padx=(6, 0))
        if not self.w_cstrip.winfo_ismapped():
            self.w_cstrip.pack(fill="x", pady=(0, 6), before=self.w_setup if self.w_setup.winfo_ismapped() else self.w_itf)

    def _w_strip_close(self):
        self.w_cstrip.pack_forget()

    def wealth_count_toggle(self):
        if self.w_counting:
            return self.wealth_count_finish()
        self.w_counting, self.w_session = True, []
        self.w_count_btn.config(text="Finish counting", style="Accent.TButton")
        self.wealth_count_strip()

    def wealth_count_strip(self):
        tot, stacks = {}, {}
        for name, qty, _cls in self.w_session:
            tot[name] = tot.get(name, 0) + qty
            stacks[name] = stacks.get(name, 0) + 1
        if tot:
            parts = [f"{n} {q:,}" + (f" ({stacks[n]} stacks)" if stacks[n] > 1 else "") for n, q in tot.items()]
            body = "   ·   ".join(parts)
        else:
            body = "nothing yet"
        text = ("● Counting: hover each stack in game and press Ctrl+C (plain Ctrl+C works while counting). Stacks of "
                "the same currency add up. Finish replaces the amounts for everything you copied; the rest is kept.\n"
                + body)
        self._w_strip(text, [("Finish", self.wealth_count_finish), ("Undo last", self.wealth_count_undo),
                             ("Cancel", self.wealth_count_cancel)], accent=0)

    def wealth_count_undo(self):
        if self.w_session:
            name, qty, _c = self.w_session.pop()
            self._say(f"Took back {name} x{qty:,}", 4)
        self.wealth_count_strip()

    def wealth_count_cancel(self):
        self.w_counting, self.w_session = False, []
        self.w_count_btn.config(text="Count currency", style="TButton")
        self._w_strip_close()

    def wealth_count_finish(self):
        tot, cls = {}, {}
        for name, qty, c in self.w_session:
            tot[name] = tot.get(name, 0) + qty
            cls[name] = c
        for name, q in tot.items():
            WEALTH.set_holding(name, q, cls[name])
        self.wealth_count_cancel()
        if tot:
            self._w_tell(f"Counted {len(tot)} kind{'s' if len(tot) != 1 else ''} of currency: "
                         + ", ".join(f"{n} {q:,}" for n, q in tot.items()) + ".", "ok")
            lg = SETTINGS.get("league")
            if lg:
                threading.Thread(target=self._w_prices_then_snapshot, args=(lg,), daemon=True).start()
        self.refresh_wealth(force=True)
        if hasattr(self, "tracker_after_count"):           # 2.0 beta 9: the session tracker was waiting for this count
            self.tracker_after_count()

    def _w_prices_then_snapshot(self, lg):
        try:
            WPRICES.ensure(lg)
            WEALTH.snapshot(lg, WPRICES, "counted")
        except Exception:
            pass
        self.ui_q.put(("wealth", "prices"))

    def wealth_manual_add(self):
        names = sorted({n.title() for n in WPRICES.by_name} | set(WEALTH.holdings)) if WPRICES.by_name else \
            sorted(set(WEALTH.holdings) | {"Divine Orb", "Exalted Orb", "Chaos Orb", "Orb of Annulment", "Vaal Orb",
                                           "Regal Orb", "Orb of Alchemy", "Gemcutter's Prism"})
        self.w_man_box.config(values=names)
        if not self.w_manual.winfo_ismapped():
            self.w_manual.pack(fill="x", pady=(0, 6), before=self.w_itf)
        self.w_man_box.focus_set()

    def wealth_manual_set(self):
        name = self.w_man_name.get().strip()
        try:
            qty = int(float(self.w_man_qty.get().replace(",", "").strip()))
        except ValueError:
            return self._w_tell("Type how many you have (a number).")
        if not name:
            return self._w_tell("Pick or type the currency's name.")
        known = {n.lower(): n for n in WEALTH.holdings}
        name = known.get(name.lower(), name)
        WEALTH.set_holding(name, qty, "Stackable Currency")
        self.w_man_qty.set("")
        self._w_tell(f"{name}: {qty:,} counted." if qty > 0 else f"Removed {name}.", "ok")
        self.refresh_wealth(force=True)

    def wealth_export_history(self):
        from .csvexport import write_wealth_history
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="wealth_history.csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            n = write_wealth_history(path, WEALTH.snapshots, SETTINGS.get("league"))
            self._w_tell(f"Saved {n} snapshots to {path}.", "ok")

    def wealth_export_items(self):
        from .csvexport import write_wealth_items
        from .wealth import wealth_rows
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="wealth_items.csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            rows, _total, _priced = wealth_rows(WEALTH.all_items(), WPRICES, WEALTH.overrides)
            n = write_wealth_items(path, rows)
            self._w_tell(f"Saved {n} items to {path}.", "ok")

    def wealth_remove_held(self):
        """(Older callers.) Delete removes the selected rows."""
        self.wealth_remove_rows(self.w_items.selection())

    def wealth_remove_rows(self, rows):
        """2.4.0: Delete removes the selected rows - one, several (Ctrl / Shift+click) or all (Ctrl+A). Counted stacks
        are gone until you count them again; items from a synced tab come back with the next sync if they're still
        in that tab. Ctrl+Z / Undo puts them back."""
        items = [it for r in rows for it in (self.w_rowitems.get(r) or [])]
        if not items:
            return
        held = [it for it in items if it.get("held")]
        synced = [it for it in items if not it.get("held")]
        with WEALTH.lock:
            old_hold = {it["type"]: dict(WEALTH.holdings[it["type"]]) for it in held if it["type"] in WEALTH.holdings}
            lids = {str(it["lid"]) for it in synced}
            old_items = {tid: list(lst) for tid, lst in WEALTH.items.items() if any(str(i["lid"]) in lids for i in lst)}
            for name in old_hold:
                WEALTH.holdings.pop(name, None)
            for tid in old_items:
                WEALTH.items[tid] = [i for i in WEALTH.items[tid] if str(i["lid"]) not in lids]
        WEALTH.save()
        n = len(held) + len(synced)
        label = f"{n} item{'s' if n != 1 else ''}"

        def restore():
            with WEALTH.lock:
                WEALTH.holdings.update(old_hold)
                WEALTH.items.update(old_items)
            WEALTH.save()
            self.refresh_wealth(force=True)
        self.push_undo("wealth", label, restore)
        self._w_tell(f"Removed {label}." + (" Synced items come back with the next sync if they're still in the tab."
                                            if synced else "") + " Ctrl+Z (or Undo) puts them back.", "ok")
        self.refresh_wealth(force=True)

    def wealth_clear_items(self):
        """2.4.0: empty the item list - counted stacks and what synced tabs found. Tabs and history stay."""
        n = len(WEALTH.holdings) + sum(len(v) for v in WEALTH.items.values())
        if not n:
            return self._w_tell("The list is already empty.", "note")
        if not messagebox.askyesno("Clear Wealth items",
                                   f"Clear all {n:,} items from the list?\n\nYour synced tabs and your history (the "
                                   "chart and snapshots) stay. Count currency or Sync to fill it again.\n\n"
                                   "You can undo this with Ctrl+Z or the Undo button.", parent=self.dlg_parent()):
            return
        with WEALTH.lock:
            old_hold, old_items = dict(WEALTH.holdings), dict(WEALTH.items)
            WEALTH.holdings.clear()
            WEALTH.items = {}
        WEALTH.save()

        def restore():
            with WEALTH.lock:
                WEALTH.holdings.update(old_hold)
                WEALTH.items.update(old_items)
            WEALTH.save()
            self.refresh_wealth(force=True)
        self.push_undo("wealth", f"{n:,} items", restore)
        self._w_tell(f"Cleared {n:,} items. Ctrl+Z (or Undo) puts them back.", "ok")
        self.refresh_wealth(force=True)

    def wealth_remove_snaps(self, rows):
        """2.4.0: Delete removes the selected snapshots (points on the chart)."""
        idx = sorted({int(r) for r in rows if str(r).isdigit()}, reverse=True)
        with WEALTH.lock:
            gone = [(i, WEALTH.snapshots[i]) for i in idx if i < len(WEALTH.snapshots)]
            for i, _sn in gone:
                del WEALTH.snapshots[i]
        if not gone:
            return
        WEALTH.save()
        label = f"{len(gone)} snapshot{'s' if len(gone) != 1 else ''}"

        def restore():
            with WEALTH.lock:
                for i, sn in sorted(gone):
                    WEALTH.snapshots.insert(min(i, len(WEALTH.snapshots)), sn)
            WEALTH.save()
            self.refresh_wealth(force=True)
            self.wealth_side()
        self.push_undo("wealth", label, restore)
        self._w_tell(f"Removed {label}. Ctrl+Z (or Undo) puts them back.", "ok")
        self.refresh_wealth(force=True)
        self.wealth_side()

    # ---------------- 2.0 beta 7: side list, breakdown, filters
    def wealth_toggle_edit(self):
        self.w_editing = not self.w_editing
        self.wealth_setup_layout()

    def wealth_side(self):
        for w in self.w_side_tabs.winfo_children():
            w.destroy()
        if self.w_side_mode.get() == "Snapshots":
            self.w_side_tabs.pack_forget()
            self.w_side_snaps.pack(fill="both", expand=True)
            lg = SETTINGS.get("league", "")
            self.w_snaps.delete(*self.w_snaps.get_children())
            for i, sn in reversed(list(enumerate(WEALTH.snapshots))):
                if sn.get("league") == lg:
                    self.w_snaps.insert("", "end", iid=str(i), values=(
                        datetime.fromtimestamp(sn["ts"]).strftime("%b %d %H:%M"),
                        {"synced": "sync", "counted": "count", "rares priced": "rares", "prices updated": "prices",
                         "session start": "start", "session end": "end"}.get(sn.get("why", ""), sn.get("why", "")),
                        fmt_div(sn["total"])))
            return
        self.w_side_snaps.pack_forget()
        if self.w_snap_sel is not None:
            self.w_snap_sel = None
            self.wealth_breakdown()
        self.w_side_tabs.pack(fill="x")
        entries = [(None, "All tabs", "#1b2a48")]
        for n, t in enumerate(WEALTH.tabs):
            if t.get("enabled", True):
                entries.append((t["id"], t["label"], self.TAB_COLOURS[n % len(self.TAB_COLOURS)]))
        if WEALTH.holdings:
            entries.append((COUNTED_TAB, COUNTED_LABEL, "#5a4a1a"))
        for tid, label, col in entries:
            on = self.w_tabfilter == tid
            b = tk.Label(self.w_side_tabs, text=label, bg=col, fg="#ffffff", anchor="w", padx=10, pady=4, cursor="hand2",
                         font=("Segoe UI", 12, "bold" if on else "normal"), highlightthickness=2,
                         highlightbackground="#ffffff" if on else col)
            b.pack(fill="x", pady=(0, 1))
            b.bind("<Button-1>", lambda e, t=tid: self.wealth_pick_tab(t))

    def wealth_pick_tab(self, tid):
        self.w_tabfilter = tid
        self.wealth_side()
        self.wealth_fill_items()

    def wealth_pick_cat(self, cat):
        self.w_catfilter = None if self.w_catfilter == cat else cat
        self.wealth_breakdown()
        self.wealth_fill_items()

    def wealth_clear_filters(self):
        self.w_tabfilter = self.w_catfilter = None
        self.wealth_side()
        self.wealth_breakdown()
        self.wealth_fill_items()

    def wealth_pick_snapshot(self):
        sel = self.w_snaps.selection()
        if len(sel) == 2:                                     # 2.3.0: two picked - what changed between them
            a, b = sorted((WEALTH.snapshots[int(i)] for i in sel), key=lambda s: s["ts"])
            self._w_tell(self.wealth_compare(a, b), "ok")
            return
        self.w_snap_sel = int(sel[0]) if sel else None
        self.wealth_breakdown()

    def wealth_compare(self, a, b):
        """A line saying what changed between two snapshots, biggest changes first."""
        d = b["total"] - a["total"]
        when = (f"From {datetime.fromtimestamp(a['ts']).strftime('%b %d %H:%M')} to "
                f"{datetime.fromtimestamp(b['ts']).strftime('%b %d %H:%M')}")
        cats = set(a.get("by_cat") or {}) | set(b.get("by_cat") or {})
        ch = sorted(((c, (b.get("by_cat") or {}).get(c, 0) - (a.get("by_cat") or {}).get(c, 0)) for c in cats),
                    key=lambda x: -abs(x[1]))
        parts = [f"{self.CAT_INFO.get(c, ('', c))[1]} {'+' if v >= 0 else '-'}{fmt_div(abs(v))}"
                 for c, v in ch if abs(v) >= 0.01][:5]
        return (f"{when}: {'+' if d >= 0 else '-'}{fmt_div(abs(d))} in total"
                + (" (" + ", ".join(parts) + ")" if parts else "") + ".")

    @staticmethod
    def _w_cat(it):
        c = (it.get("cat") or "other").split(".")[0].lower()
        return c if c in WealthPage.CAT_INFO else "other"

    def wealth_breakdown(self):
        for w in self.w_bd.winfo_children():
            w.destroy()
        P2 = C["panel2"]
        if self.w_snap_sel is not None and self.w_snap_sel < len(WEALTH.snapshots):
            sn = WEALTH.snapshots[self.w_snap_sel]
            by = {}
            for k, v in (sn.get("by_cat") or {}).items():
                kk = k if k in self.CAT_INFO else "other"
                by[kk] = by.get(kk, 0) + v
            self.w_bd_note.config(text="Snapshot of " + datetime.fromtimestamp(sn["ts"]).strftime("%b %d %H:%M") +
                                  f" - {fmt_div(sn['total'])}")
        else:
            by = {}
            for it, _e, tot, _s in getattr(self, "w_rows", []):
                if tot:
                    k = self._w_cat(it)
                    by[k] = by.get(k, 0) + tot
            self.w_bd_note.config(text="Click a category to show only those items." if by else
                                  "Sync a tab or count your currency to see where your wealth is.")
        total = sum(by.values()) or 1
        pct = self.w_bd_mode.get() == "Percent"
        cols = 3
        for n, (k, v) in enumerate(sorted(by.items(), key=lambda kv: -kv[1])):
            icon, name = self.CAT_INFO[k]
            on = self.w_catfilter == k
            f = tk.Frame(self.w_bd, bg="#1b2a48" if on else "#121c30", padx=8, pady=5, cursor="hand2",
                         highlightthickness=1, highlightbackground=C["accent"] if on else C["line"])
            f.grid(row=n // cols, column=n % cols, sticky="ew", padx=(0, 6), pady=(0, 6))
            a = tk.Label(f, text=f"{icon}  {v / total * 100:.0f}%" if pct else f"{icon}  {fmt_div(v)}", bg=f.cget("bg"),
                         fg="#ffffff", font=("Segoe UI", 11, "bold"), anchor="w")
            a.pack(anchor="w")
            b = tk.Label(f, text=name, bg=f.cget("bg"), fg=C["muted"], font=("Segoe UI", 8), anchor="w")
            b.pack(anchor="w")
            for w in (f, a, b):
                w.bind("<Button-1>", lambda e, kk=k: self.wealth_pick_cat(kk))
        for c in range(cols):
            self.w_bd.columnconfigure(c, weight=1)

    # ---------------- actions
    def wealth_save_account(self):
        v = self.w_acc.get().strip()
        if v != SETTINGS.get("wealth_account", ""):
            SETTINGS["wealth_account"] = v
            save_json("settings.json", SETTINGS)

    def wealth_next_amount(self):
        used = [t["amount"] for t in WEALTH.tabs]
        return max(used) + 1 if used else 37916

    def wealth_toggle_adding(self):
        self.w_adding = not self.w_adding
        self.wealth_setup_layout()
        if self.w_adding:
            self.w_amt_entry.focus_set()

    def wealth_setup_layout(self):
        """Setup help and the add-tab rows show while you have no tab (or press "Add a tab"); otherwise they fold away
        so the item list gets the room."""
        want_setup = self.w_editing or (not WEALTH.tabs and not WEALTH.holdings)
        if want_setup and not self.w_setup.winfo_ismapped():
            self.w_setup.pack(fill="x", pady=(0, 6), before=self.w_itf)
        elif not want_setup and self.w_setup.winfo_ismapped():
            self.w_setup.pack_forget()
        self.w_edit_lbl.config(text="✓ Done editing tabs" if self.w_editing else "✎ Edit synced tabs")
        show = not WEALTH.tabs or self.w_adding
        if show and not self.w_add.winfo_ismapped():
            self.w_add.pack(fill="x", before=self.w_acts)
            self.w_lnk.pack(fill="x", pady=(0, 8), before=self.w_acts)
        elif not show and self.w_add.winfo_ismapped():
            self.w_add.pack_forget()
            self.w_lnk.pack_forget()
        if not WEALTH.tabs and not self.w_help.winfo_ismapped():
            self.w_help.pack(fill="x", pady=(4, 6), before=self.w_tabs.master)
        elif WEALTH.tabs and self.w_help.winfo_ismapped():
            self.w_help.pack_forget()
        if WEALTH.tabs:
            self.w_add_btn.pack(side="left", padx=(0, 6), before=self.w_acts.winfo_children()[1])
            self.w_add_btn.config(text="Done adding" if self.w_adding else "Add a tab")
        else:
            self.w_add_btn.pack_forget()

    def _w_tell(self, text, kind="error"):
        """Say something on the Wealth page itself (and in the status line)."""
        self.w_msg.config(text=text, fg={"error": C["red"], "ok": C["green"], "note": C["good"]}.get(kind, C["muted"]))
        self._say(text, 15)

    def _wealth_add(self, amount, cur, name=""):
        """-> True if added."""
        if any(t["amount"] == amount and t["currency"] == cur for t in WEALTH.tabs):
            self._w_tell(f"You already have a tab priced at {amount:,} {dict(WEALTH_CURRENCIES).get(cur, cur)}.", "note")
            return False
        with WEALTH.lock:
            WEALTH.tabs.append({"id": "%08x" % random.getrandbits(32), "label": name or f"~price {amount} {cur}",
                                "amount": amount, "currency": cur, "enabled": True})
        WEALTH.save()
        self.refresh_wealth(force=True)
        return True

    def wealth_pending(self):
        """Is something typed in the Price, Name or trade-link box that hasn't been added yet?"""
        return any(v.get().strip() for v in (self.w_new_amt, self.w_new_name, self.w_link))

    def wealth_add_tab(self, quiet=False):
        """Add what's typed. -> True if a tab was added (or that exact price already was one)."""
        txt, name = self.w_new_amt.get().strip(), self.w_new_name.get().strip()
        if "trade2/search" in txt or "trade2/search" in name:          # a link pasted in the wrong box
            self.w_link.set(txt if "trade2/search" in txt else name)
            self.w_new_amt.set("")
            self.w_new_name.set("")
            return self.wealth_add_from_link(quiet)
        amount, cur = parse_price_text(txt)
        if amount is None and name:                                     # price typed in the Name box
            amount, cur = parse_price_text(name)
            if amount is not None:
                name = ""
        if not amount or amount <= 0:
            self.w_amt_entry.focus_set()
            self._w_tell("Type the price you put on the tab in game in the Price box (e.g. 37882), pick its currency, "
                         "then press Add tab.")
            return False
        cur = cur or next((cid for cid, n in WEALTH_CURRENCIES if n == self.w_new_cur.get()), "divine")
        if any(t["amount"] == amount and t["currency"] == cur for t in WEALTH.tabs):
            self.w_new_amt.set("")
            self.w_new_name.set("")
            return True
        if self._wealth_add(amount, cur, name):
            self.w_new_name.set("")
            self.w_new_amt.set("")
            if not quiet:
                self._w_tell(f"Added the tab priced at {amount:,} {dict(WEALTH_CURRENCIES).get(cur, cur)}. "
                             f"Press Sync tabs to read it.", "ok")
            return True
        return False

    def wealth_add_from_link(self, quiet=False):
        info, err = parse_trade_link(self.w_link.get())
        if err:
            self._w_tell(err)
            return False
        notes = []
        acc_now = self.w_acc.get().strip()
        if info["account"] and info["account"].lower() != acc_now.lower():
            self.w_acc.set(info["account"])
            self.wealth_save_account()
            notes.append(f"account set to {info['account']}" + (f" (was {acc_now})" if acc_now else ""))
        if info["league"] != SETTINGS.get("league"):
            notes.append(f"this link is for {info['league']}: pick that league in Settings (⚙ on the dock)")
        if any(t["amount"] == info["amount"] and t["currency"] == info["currency"] for t in WEALTH.tabs):
            self.w_link.set("")
            return True
        if not self._wealth_add(info["amount"], info["currency"]):
            return False
        self.w_link.set("")
        cur = dict(WEALTH_CURRENCIES).get(info["currency"], info["currency"])
        msg = f"Added the tab priced at {info['amount']:,} {cur}" + ("; " + "; ".join(notes) if notes else "") + "."
        if any("league" in n for n in notes) or not quiet:
            self._w_tell(msg + ("" if quiet else " Press Sync tabs."), "note" if any("league" in n for n in notes) else "ok")
        return True

    def _wealth_sel_tab(self):
        sel = self.w_tabs.selection()
        return WEALTH.tab(sel[0]) if sel else None

    def wealth_toggle_tab(self):
        t = self._wealth_sel_tab()
        if not t:
            return self._w_tell("Select a tab in the list first.", "note")
        with WEALTH.lock:
            t["enabled"] = not t.get("enabled", True)
        WEALTH.save()
        self.refresh_wealth(force=True)

    def wealth_remove_tab(self):
        t = self._wealth_sel_tab()
        if not t:
            return self._w_tell("Select a tab in the list first.", "note")
        if not messagebox.askyesno("Remove tab", f"Remove \"{t['label']}\" and the items read from it?\n\n"
                                                 "Your net worth history is kept."):
            return
        with WEALTH.lock:
            pos = next((i for i, x in enumerate(WEALTH.tabs) if x["id"] == t["id"]), len(WEALTH.tabs))
            old_items, old_res = WEALTH.items.get(t["id"]), WEALTH.results.get(t["id"])
            WEALTH.tabs = [x for x in WEALTH.tabs if x["id"] != t["id"]]
            WEALTH.items.pop(t["id"], None)
            WEALTH.results.pop(t["id"], None)
        WEALTH.save()

        def restore():
            with WEALTH.lock:
                WEALTH.tabs.insert(pos, t)
                if old_items is not None:
                    WEALTH.items[t["id"]] = old_items
                if old_res is not None:
                    WEALTH.results[t["id"]] = old_res
            WEALTH.save()
            self.refresh_wealth(force=True)
        self.push_undo("wealth", f"the tab \"{t['label']}\"", restore)
        self.refresh_wealth(force=True)

    def wealth_open_trade(self):
        t = self._wealth_sel_tab()
        res = WEALTH.results.get(t["id"]) if t else None
        if not res or not res.get("qid"):
            return self._say("Sync first: the trade-site link comes from the last sync of that tab.", 8)
        webbrowser.open(wealth_trade_url(res.get("league") or SETTINGS.get("league", ""), res["qid"]))

    def wealth_sync(self):
        self.wealth_save_account()
        if not WEALTH.tabs and not self.wealth_pending():          # 2.0 beta 7: only counted currency: just re-price it
            if WEALTH.holdings:
                self.wealth_update_prices()
                self.w_msg.config(text="Updating prices… (no priced tabs are set up, so Sync only updates the prices of "
                                       "what you counted by hand; Edit synced tabs adds a tab)", fg=C["muted"])
                return
            self.w_editing = True
            self.wealth_setup_layout()
        if self.wealth_pending():                       # 1.36: a price still in the boxes counts - add it first
            ok = (self.wealth_add_from_link(quiet=True) if self.w_link.get().strip() and not self.w_new_amt.get().strip()
                  else self.wealth_add_tab(quiet=True))
            if not ok:
                return
        err = self.engine.wealth_start()
        if err:
            if "priced tab" in err:
                self.w_amt_entry.focus_set()
            return self._w_tell(err)
        busy = sum(1 for r in self.records.values() if r["state"] in ("queued", "pricing"))
        self.w_msg.config(text="Waiting for item pricing to finish…" if busy else "Starting…", fg=C["muted"])
        self.wealth_buttons()

    def wealth_stop(self):
        s = WEALTH_SYNC["cur"]
        if s and s["running"]:
            s["cancel"] = True
            self.w_msg.config(text="Stopping after the current request…", fg=C["muted"])
        if WEALTH_RARES["running"]:                       # 2.0: stop pricing rares too (what's priced so far is kept)
            WEALTH_RARES["gen"] += 1
            WEALTH_RARES["running"] = False
            WEALTH.save()
            self.w_msg.config(text=f"Stopped price-checking rares after {WEALTH_RARES['done']} of {WEALTH_RARES['total']}. "
                                   "Re-check rares carries on.", fg=C["muted"])
            self.refresh_wealth(force=True)
        self.wealth_buttons()

    def wealth_recheck_rares(self):
        """Price-check the magic / rare items again: the ones that are new, changed or 3+ days old (2.0)."""
        lg = SETTINGS.get("league")
        if not lg:
            return self._say("Pick a league first.", 8)
        if (WEALTH_SYNC["cur"] or {}).get("running") or WEALTH_RARES["running"]:
            return self._say("Already busy - wait for the sync / rare checks to finish (or press Stop).", 8)
        n = self.engine.wealth_queue_rares(lg)
        if not n:
            n = self.engine.wealth_queue_rares(lg, force=True)       # all fresh: the button means "do them all again"
        self.w_msg.config(text=f"Price-checking {n} magic / rare item{'s' if n != 1 else ''} in the background…" if n else
                          "No magic or rare items in your tabs (sync first).", fg=C["muted"])
        self.wealth_buttons()

    def wealth_update_prices(self):
        lg = SETTINGS.get("league")
        if not lg:
            return self._say("Pick a league first.", 8)
        self.w_price_btn.config(state="disabled")
        self.w_msg.config(text="Updating prices from poe.ninja…", fg=C["muted"])

        def work():
            try:
                WPRICES.ensure(lg, force=True)
                WEALTH.snapshot(lg, WPRICES, "prices updated")
            except Exception as e:
                WPRICES.errors = [str(e)[:120]]
            self.ui_q.put(("wealth", "prices"))
        threading.Thread(target=work, daemon=True).start()

    def wealth_set_price(self, e):
        iid = self.w_items.identify_row(e.y)
        it = self.w_rowmap.get(iid)
        if not it:
            return
        if it.get("held") and self.w_items.identify_column(e.x) in ("#2", "#3"):       # Tab / Quantity: the amount
            return self._w_held_ask(it["type"])
        key = wealth_key(it)
        now = WEALTH.overrides.get(key)
        scope = "this item" if key.startswith("item:") else "every copy of it"
        from tkinter import simpledialog
        ans = simpledialog.askstring("Your price", f"{wealth_display_name(it)}\n\nPrice in Divine Orbs for {scope}.\n"
                                                   "Leave empty to go back to the automatic price.",
                                     initialvalue="" if now is None else _num(now), parent=self.root)
        if ans is None:
            return
        ans = ans.strip().replace(",", ".")
        with WEALTH.lock:
            if not ans:
                WEALTH.overrides.pop(key, None)
            else:
                try:
                    WEALTH.overrides[key] = max(0.0, float(ans))
                except ValueError:
                    return self._say("That isn't a number.", 8)
        WEALTH.save()
        self.refresh_wealth(force=True)

    def wealth_item_menu(self, e):
        """Right-click an item: set your own price, or go back to the market price (2.3.0)."""
        iid = self.w_items.identify_row(e.y)
        it = self.w_rowmap.get(iid)
        if not it:
            return
        self.w_items.selection_set(iid)
        key = wealth_key(it)
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84")
        m.add_command(label="Set my own price…", command=lambda: self.wealth_set_price(e))
        if key in WEALTH.overrides:
            m.add_command(label="Use the market price again", command=lambda: self.wealth_clear_price(key))
        if it.get("held"):
            m.add_command(label="Change the amount…", command=lambda: self._w_held_ask(it["type"]))
        m.tk_popup(e.x_root, e.y_root)

    def wealth_clear_price(self, key):
        with WEALTH.lock:
            WEALTH.overrides.pop(key, None)
        WEALTH.save()
        self._w_tell("Back to the market price.", "ok")
        self.refresh_wealth(force=True)

    def wealth_sort(self, col):
        self.w_sort_rev = not self.w_sort_rev if self.w_sort_col == col else col in ("qty", "each", "total")
        self.w_sort_col = col
        self.wealth_fill_items()

    # ---------------- events from the engine
    def ev_wealth(self, kind):
        s = WEALTH_SYNC["cur"]
        if kind == "progress" and s:
            extra = f"   {s['fetched']} of {s['expected']} items read" if s["expected"] else ""
            self.w_msg.config(text=s["msg"] + extra, fg=C["muted"])
        elif kind == "done" and s:
            self.w_msg.config(text=s["msg"], fg=C["red"] if "failed" in s["msg"] else C["green"])
            self._say(s["msg"], 15)
            self.refresh_wealth(force=True)
        elif kind == "rare":
            R = WEALTH_RARES
            self.w_msg.config(text=f"Price-checking magic / rare items: {R['done']} of {R['total']} done, {R['priced']} priced "
                                   f"(behind anything you copy; F2 pauses)…", fg=C["muted"])
            if R["done"] % 5 == 0:
                self.refresh_wealth(force=True)
        elif kind == "rares_done":
            self.w_msg.config(text=WEALTH_RARES["msg"], fg=C["green"])
            self.refresh_wealth(force=True)
        elif kind == "prices":
            self.w_price_btn.config(state="normal")
            msg = "Prices updated." if not WPRICES.errors else "Prices updated, but some poe.ninja categories failed."
            if not WEALTH.tabs and WEALTH.holdings:
                msg += " (No priced tabs are set up, so Sync only updates the prices of what you counted by hand.)"
            self.w_msg.config(text=msg, fg=C["green"] if not WPRICES.errors else C["good"])
            self.refresh_wealth(force=True)
        self.wealth_buttons()

    def wealth_buttons(self):
        s = WEALTH_SYNC["cur"]
        running = bool(s and s["running"])
        rares = bool(WEALTH_RARES["running"])
        self.w_sync_btn.config(state="disabled" if running or rares else "normal")
        self.w_stop_btn.config(state="normal" if running or rares else "disabled")
        if hasattr(self, "w_rares_btn"):
            self.w_rares_btn.config(state="disabled" if running or rares else "normal")

    # ---------------- drawing
    def refresh_wealth(self, force=False):
        if not force and not self.page_open("Wealth"):
            return
        self.wealth_buttons()
        self.wealth_setup_layout()
        rows, total, priced = wealth_rows(WEALTH.all_items(), WPRICES, WEALTH.overrides)
        self.w_rows = rows
        by_tab = {}
        for it, _e, tot, _s in rows:
            by_tab.setdefault(it["tab"], [0, 0.0])
            by_tab[it["tab"]][0] += 1
            by_tab[it["tab"]][1] += tot or 0
        sel = self.w_tabs.selection()
        self.w_tabs.delete(*self.w_tabs.get_children())
        curname = dict(WEALTH_CURRENCIES)
        for t in WEALTH.tabs:
            res = WEALTH.results.get(t["id"]) or {}
            n, val = by_tab.get(t["id"], (0, 0.0))
            if res.get("error"):
                last, tag = "failed - select for details", "bad"
            elif res.get("ts"):
                last, tag = fmt_stamp(res["ts"]) + (" - see note" if res.get("warnings") else ""), ("warn" if res.get("warnings") else "")
            else:
                last, tag = "not synced yet", ""
            if not t.get("enabled", True):
                tag, last = "off", "left out of syncs"
            self.w_tabs.insert("", "end", iid=t["id"], tags=(tag,) if tag else (),
                               values=(t["label"], f"{t['amount']:,} {curname.get(t['currency'], t['currency'])}",
                                       n, fmt_div(val) if val else "", last))
        if sel and self.w_tabs.exists(sel[0]):
            self.w_tabs.selection_set(sel[0])
        self.wealth_show_tab_result()

        lg = SETTINGS.get("league", "")
        self.w_total.config(text=fmt_div(total) if rows else "No items yet", fg=C["good"] if rows else C["muted"],
                            font=("Segoe UI", 22 if rows else 13, "bold"))
        self.w_synced.config(text=f"Synced {self._w_ago(WEALTH.last_sync)}" if WEALTH.last_sync else "")
        eq = []
        for cid, name in (("exalted", "Exalted"), ("chaos", "Chaos")):
            r = RATES.value(cid) or (WPRICES.by_name.get(f"{name.lower()} orb") or (None,))[0]
            if r and rows:
                eq.append(f"{_amt(total / r)} {name}")
        self.w_equiv.config(text=("or about " + " or ".join(eq)) if eq else "")
        snaps = [s for s in WEALTH.snapshots if s.get("league") == lg]
        delta = ""
        if snaps and rows:
            prev = self.wealth_compare_point(snaps)
            if prev:
                d = total - prev["total"]
                delta = f"{'+' if d >= 0 else '-'}{fmt_div(abs(d))}"
                self.w_delta_since = self.wealth_since_words(prev["ts"])
                self.w_delta.config(fg=C["green"] if d >= 0 else C["red"])
        self.w_delta.config(text=delta)
        facts = []
        if rows:
            facts.append(f"{priced} of {len(rows)} items priced.")
        if WPRICES.ts:
            facts.append(f"Prices from poe.ninja, {self._w_ago(WPRICES.ts)}.")
        if WPRICES.errors:
            facts.append(f"{len(WPRICES.errors)} poe.ninja categories failed last time.")
        if WEALTH.last_sync:
            facts.append(f"Tabs read {self._w_ago(WEALTH.last_sync)}.")
        if delta:
            word = "Up" if not delta.startswith("-") else "Down"
            facts.insert(0, f"{word} {delta.lstrip('+-')} {getattr(self, 'w_delta_since', '')}.")
        self.w_facts.config(text="  ".join(facts))
        self.wealth_side()
        self.wealth_breakdown()
        self.wealth_draw_chart()
        self.wealth_fill_items()

    @staticmethod
    def wealth_compare_point(snaps, now=None):
        """The snapshot to compare today's total with (2.3.0): one from about a day ago if there is one, else the
        last one at least 30 minutes old."""
        now = now or time.time()
        day = [s for s in snaps if 18 * 3600 <= now - s["ts"] <= 48 * 3600]
        if day:
            return min(day, key=lambda s: abs((now - s["ts"]) - 86400))
        return next((s for s in reversed(snaps) if now - s["ts"] >= 1800), None)

    @staticmethod
    def wealth_since_words(ts, now=None):
        now = now or time.time()
        age = now - ts
        if 18 * 3600 <= age <= 48 * 3600:
            return "since yesterday"
        if age < 18 * 3600:
            h = max(1, round(age / 3600))
            return f"in the last {h} hour{'s' if h != 1 else ''}"
        return f"since {datetime.fromtimestamp(ts).strftime('%b %d')}"

    @staticmethod
    def _w_ago(ts):
        return "just now" if time.time() - ts < 60 else ago(ts)

    def wealth_show_tab_result(self):
        t = self._wealth_sel_tab()
        if not t:
            self.w_tabinfo.config(text="", fg=C["muted"])
            return
        res = WEALTH.results.get(t["id"]) or {}
        if res.get("error"):
            self.w_tabinfo.config(text=f"{t['label']}: {res['error']}", fg=C["red"])
        elif res.get("warnings"):
            self.w_tabinfo.config(text=f"{t['label']}: " + "  ".join(res["warnings"]), fg=C["good"])
        elif res.get("ts"):
            self.w_tabinfo.config(text=f"{t['label']}: read {res.get('fetched', 0)} of {res.get('total', 0)} items. "
                                       f"Double-click the tab to see it on the trade site.", fg=C["muted"])
        else:
            self.w_tabinfo.config(text="", fg=C["muted"])

    def wealth_fill_items(self):
        rows = getattr(self, "w_rows", [])
        needle = self.w_filter.get().strip().lower()
        only_unpriced = self.w_unpriced.get()
        shown = []
        for it, each, tot, src in rows:
            if only_unpriced and each is not None:
                continue
            if self.w_tabfilter is not None and it["tab"] != self.w_tabfilter:
                continue
            if self.w_catfilter is not None and self._w_cat(it) != self.w_catfilter:
                continue
            name = wealth_display_name(it)
            if needle and needle not in name.lower() and not any(needle in m.lower() for m in it["mods"]):
                continue
            shown.append([it, name, it["qty"], each, tot, src, 1, [it]])
        if self.w_combine.get():
            merged = {}
            for r in shown:
                it = r[0]
                k = it["lid"] if it["frame"] in (1, 2) else (it["stash"], r[1], it["corrupted"], r[3])
                if k in merged:
                    m = merged[k]
                    m[2] += r[2]
                    m[4] = (m[4] or 0) + (r[4] or 0) if m[4] is not None else None
                    m[6] += 1
                    m[7] = m[7] + r[7]
                else:
                    merged[k] = list(r)
            shown = list(merged.values())
        col = self.w_sort_col
        keyf = {"item": lambda r: r[1].lower(), "tab": lambda r: r[0]["stash"].lower(), "qty": lambda r: r[2],
                "each": lambda r: r[3] if r[3] is not None else -1, "total": lambda r: r[4] if r[4] is not None else -1,
                "src": lambda r: r[5] or ""}[col]
        shown.sort(key=keyf, reverse=self.w_sort_rev)
        self.w_items.delete(*self.w_items.get_children())
        self.w_rowmap, self.w_rowitems = {}, {}
        rarity_tag = {1: "magic", 2: "rare", 3: "unique", 4: "gem"}
        for n, (it, name, qty, each, tot, src, stacks, parts) in enumerate(shown):
            tags = (["held"] if it.get("held") else [rarity_tag.get(it["frame"], "")]) if each is not None else ["none"]
            if src == "your price":                           # 2.3.0: prices you set yourself stand out
                tags = ["own"]
                src = "✎ your price (right-click to undo)"
            if n % 2:
                tags.append("odd")
            label = name + (f"   ({stacks} stacks)" if stacks > 1 else "") + ("   corrupted" if it["corrupted"] else "")
            iid = self.w_items.insert("", "end", tags=[t for t in tags if t],
                                      values=(label, it["stash"], f"{qty:,}", fmt_div(each) if each is not None else "set price",
                                              fmt_div(tot) if tot is not None else "", src or self._w_why_unpriced(it)))
            self.w_rowmap[iid] = it
            self.w_rowitems[iid] = parts
        filt = []
        if self.w_tabfilter is not None:
            filt.append(COUNTED_LABEL if self.w_tabfilter == COUNTED_TAB else
                        (WEALTH.tab(self.w_tabfilter) or {}).get("label", "tab"))
        if self.w_catfilter is not None:
            filt.append(self.CAT_INFO[self.w_catfilter][1])
        if filt:
            self.w_filter_chip.config(text="Showing: " + " · ".join(filt) + "   ✕")
            if not self.w_filter_chip.winfo_ismapped():
                self.w_filter_chip.pack(side="left", padx=(10, 0))
        else:
            self.w_filter_chip.pack_forget()
        shown_total = sum(r[4] or 0 for r in shown)
        self.w_count.config(text=f"{len(shown)} shown, worth {fmt_div(shown_total)}.   Double-click a price to set your "
                                 f"own; on Counted by hand, double-click the quantity to change it. Select rows and press Delete to remove them "
                                 f"(Ctrl+Z undoes).")
        if rows or self.w_setup.winfo_ismapped():
            self.w_empty.place_forget()
        else:
            self.w_empty.place(relx=0.5, y=40, anchor="n")

    @staticmethod
    def _w_why_unpriced(it):
        if it["frame"] not in (1, 2):
            return "not on poe.ninja"
        rp = WEALTH.rare_prices.get(str(it.get("lid")))
        if not rp or rp.get("sig") != rare_sig(it):
            return "waiting for a price check" if WEALTH_RARES["running"] else "not checked yet (Re-check rares)"
        lab = rp.get("label") or ""
        if "no listings" in lab or "NO MATCH" in lab:
            return "price check: no matching listings"
        if lab.startswith("CHECK BY HAND"):
            return "price check: check by hand"
        return "price check: " + (lab[:60] or "no price")

    def wealth_draw_chart(self):
        """Total: your net worth over the picked range. Daily: how much it went up or down each day."""
        cv = self.w_chart
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        if w < 60 or h < 40:
            return
        lg = SETTINGS.get("league", "")
        span_s = self.RANGES.get(self.w_range.get())
        now = time.time()
        allpts = [(s["ts"], s["total"]) for s in WEALTH.snapshots if s.get("league") == lg]
        pts = [p for p in allpts if span_s is None or p[0] >= now - span_s]
        daily = self.w_mode.get() == "Daily"
        day = lambda t: datetime.fromtimestamp(t).strftime("%b %d").replace(" 0", " ")
        pad_l, pad_r, pad_t, pad_b = 54, 10, 8, 20
        if daily:
            last = {}
            for t, v in allpts:
                last[datetime.fromtimestamp(t).date()] = (t, v)
            days = sorted(last.items())
            bars = [(days[i][1][0], days[i][1][1] - days[i - 1][1][1]) for i in range(1, len(days))]
            bars = [b for b in bars if span_s is None or b[0] >= now - span_s]
            if not bars:
                cv.create_text(4, h // 2, anchor="w", fill=C["muted"], font=("Segoe UI", 9),
                               text="Daily change shows once there are syncs on two different days.")
                return
            m = max(abs(v) for _, v in bars) or 1
            mid = pad_t + (h - pad_t - pad_b) / 2
            cv.create_line(pad_l, mid, w - pad_r, mid, fill=C["line"])
            cv.create_text(pad_l - 6, pad_t + 4, anchor="e", fill=C["muted"], font=("Segoe UI", 8), text="+" + fmt_div(m))
            cv.create_text(pad_l - 6, h - pad_b - 4, anchor="e", fill=C["muted"], font=("Segoe UI", 8), text="-" + fmt_div(m))
            bw = max(3, (w - pad_l - pad_r) / len(bars) - 4)
            for i, (t, v) in enumerate(bars):
                x0 = pad_l + i * (w - pad_l - pad_r) / len(bars) + 2
                y = mid - v / m * (h - pad_t - pad_b) / 2
                cv.create_rectangle(x0, min(mid, y), x0 + bw, max(mid, y), outline="", fill=C["green"] if v >= 0 else C["red"])
            cv.create_text(pad_l, h - 4, anchor="sw", fill=C["muted"], font=("Segoe UI", 8), text=day(bars[0][0]))
            cv.create_text(w - pad_r, h - 4, anchor="se", fill=C["muted"], font=("Segoe UI", 8), text=day(bars[-1][0]))
            return
        if len(pts) < 2:
            cv.create_text(4, h // 2, anchor="w", fill=C["muted"], font=("Segoe UI", 9),
                           text="Each sync or count adds a point. The line appears after the second one"
                                + (" in this range." if len(allpts) >= 2 else "."))
            return
        t0, t1 = pts[0][0], max(pts[-1][0], pts[0][0] + 1)
        vmax = max(v for _, v in pts) * 1.05 or 1
        vmin = 0
        span = max(vmax - vmin, 1e-9)
        X = lambda t: pad_l + (t - t0) / (t1 - t0) * (w - pad_l - pad_r)
        Y = lambda v: pad_t + (1 - (v - vmin) / span) * (h - pad_t - pad_b)
        cv.create_line(pad_l, pad_t, pad_l, h - pad_b, fill=C["line"])
        cv.create_line(pad_l, h - pad_b, w - pad_r, h - pad_b, fill=C["line"])
        cv.create_text(pad_l - 6, Y(vmax), anchor="e", fill=C["muted"], font=("Segoe UI", 8), text=fmt_div(vmax))
        xy = [c for t, v in pts for c in (X(t), Y(v))]
        cv.create_polygon(*xy, X(t1), h - pad_b, X(t0), h - pad_b, fill="#2a2214", outline="")
        cv.create_line(*xy, fill="#e8a65a", width=2, smooth=True)
        cv.create_oval(X(pts[-1][0]) - 3, Y(pts[-1][1]) - 3, X(pts[-1][0]) + 3, Y(pts[-1][1]) + 3, fill="#e8a65a", outline="")
        n = 4 if w > 420 else 2
        for i in range(n + 1):
            t = t0 + (t1 - t0) * i / n
            cv.create_text(X(t), h - 4, anchor="s" if 0 < i < n else ("sw" if i == 0 else "se"), fill=C["muted"],
                           font=("Segoe UI", 8), text=day(t))
