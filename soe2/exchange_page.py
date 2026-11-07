"""Exchange rates > Exchange Helper: Check a flip you see in game (2.69.0; 2.92.0: moved here from the Arbitrage tab).

2.92.0: Arbitrage (uneven rates from Grinding Gear Games' hourly Currency Exchange history) is removed - deprecated
because GGG's terms for reading that history are unclear (it came from an address outside their documented API). The
flip check stays: it is arithmetic on two prices you type, and makes no requests."""
import tkinter as tk
from tkinter import ttk

from . import buglog
from . import cxnames as CXN
from .rates import whole_ratio
from .style import C, MONO
from .chrome import section as chrome_section
from .util import _amt


def _n(x):
    if x is None:
        return "-"
    if x >= 100:
        return f"{x:,.0f}"
    if x >= 1:
        return f"{x:,.2f}".rstrip("0").rstrip(".")
    return f"{x:.3g}"


class ExchangePage:
    """Mixed into App."""

    def build_flip(self, page):
        P2 = C["panel2"]
        # ---- a flip you see in game
        flo, fl = chrome_section(page, "Check a flip you see in game")      # 2.69.0
        flo.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(fl, text="On the Currency Exchange, hover the market ratio and hold Alt: it lists what people are "
                          "offering both ways. Type the two prices for one item here.", bg=P2, fg=C["muted"],
                 anchor="w", justify="left", wraplength=600).pack(fill="x")
        row = tk.Frame(fl, bg=P2)
        row.pack(fill="x", pady=(8, 0))
        self.flip_buy, self.flip_sell, self.flip_qty = tk.StringVar(), tk.StringVar(), tk.StringVar(value="100")
        self.flip_item, self.flip_cur = tk.StringVar(value="the item"), tk.StringVar(value="Exalted Orb")
        tk.Label(row, text="I can buy 1", bg=P2, fg=C["text"]).pack(side="left")
        # 2.91.0: every item the Currency Exchange trades (type to narrow the list)
        self.flip_item.set("")
        self.flip_box = ttk.Combobox(row, textvariable=self.flip_item, values=self.flip_names(), width=26)
        self.flip_box.pack(side="left", padx=4)
        self.flip_box.bind("<KeyRelease>", lambda e: self.flip_filter())
        self.flip_box.bind("<Button-1>", lambda e: self.flip_box.configure(values=self.flip_names()), add="+")
        tk.Label(row, text="for", bg=P2, fg=C["text"]).pack(side="left")
        ttk.Entry(row, textvariable=self.flip_buy, width=7).pack(side="left", padx=4)
        tk.Label(row, text="and sell 1 for", bg=P2, fg=C["text"]).pack(side="left")
        ttk.Entry(row, textvariable=self.flip_sell, width=7).pack(side="left", padx=4)
        ttk.Combobox(row, textvariable=self.flip_cur, values=["Exalted Orb", "Divine Orb", "Chaos Orb"],
                     width=12).pack(side="left", padx=4)
        row2 = tk.Frame(fl, bg=P2)
        row2.pack(fill="x", pady=(4, 0))
        tk.Label(row2, text="How many I'd flip", bg=P2, fg=C["text"]).pack(side="left")
        ttk.Entry(row2, textvariable=self.flip_qty, width=6).pack(side="left", padx=4)
        self.flip_out = tk.Label(fl, text="", bg=P2, fg=C["text"], anchor="w", justify="left", font=(MONO, 9))
        self.flip_out.pack(fill="x", pady=(8, 0))
        self.flip_out.bind("<Configure>", lambda e: self.flip_out.config(wraplength=max(300, e.width - 10)))
        for v in (self.flip_buy, self.flip_sell, self.flip_qty, self.flip_item, self.flip_cur):
            v.trace_add("write", lambda *a: self.flip_draw())
        self.flip_draw()

    def cx_name(self, cid):
        n = CXN.item_name(cid)                                 # 2.26.0: game ids -> names (cxnames.json)
        if n:
            return n
        try:
            from .wealth import WPRICES
            for part in (WPRICES.parts or {}).values():
                n = (part.get("names") or {}).get(cid)
                if n:
                    return n
        except Exception:
            buglog.caught()
        return cid.rsplit("/", 1)[-1].replace("-", " ").title()

    # ---- refresh
    def flip_names(self):
        """2.91.0: every Currency Exchange item by name - the rates table's (most traded first) and the full list of
        exchange items (cxnames.json) after them."""
        out = []
        try:
            from .rates import RATES
            names = {}
            try:
                from .wealth import WPRICES
                for part in (WPRICES.parts or {}).values():
                    names.update(part.get("names") or {})
            except Exception:
                buglog.caught()
            for cid in sorted((c for c, v in RATES.table.items() if v), key=lambda c: -(RATES.vol.get(c, 0))):
                out.append(names.get(cid) or self.cx_name(cid))
        except Exception:
            buglog.caught()
        try:
            CXN.item_name("divine")                            # (loads cxnames.json)
            out += sorted(v for k, v in CXN._NAMES.items() if k != "_loaded" and isinstance(v, str))
        except Exception:
            buglog.caught()
        seen, uniq = set(), []
        for n in out:
            if n and n.lower() not in seen:
                seen.add(n.lower())
                uniq.append(n)
        return uniq

    def flip_filter(self):
        """Typing narrows the list to the names that hold what you typed."""
        t = self.flip_item.get().strip().lower()
        allv = self.flip_names()
        self.flip_box.configure(values=[n for n in allv if t in n.lower()] if t else allv)

    def flip_draw(self):
        def num(v):
            try:
                return float(v.get().replace(",", ".").strip())
            except ValueError:
                return None
        buy, sell, qty = num(self.flip_buy), num(self.flip_sell), num(self.flip_qty) or 1
        item, cur = self.flip_item.get().strip() or "the item", self.flip_cur.get().strip() or "currency"
        gain, margin = CXN.flip(buy, sell)
        if gain is None:
            self.flip_out.config(text="Type what one costs to buy, and what one sells for.", fg=C["muted"])
            return
        if gain <= 0:
            self.flip_out.config(text=f"No gain: buying costs {_n(buy)} and selling brings {_n(sell)} {cur}. Flipping "
                                      f"only works when people pay more than others ask.", fg=C["red"])
            return
        ba, bb = whole_ratio(1 / buy)
        sa, sb = whole_ratio(sell)
        self.flip_out.config(fg=C["green"], text=(
            f"+{_n(gain)} {cur} per {item} ({margin * 100:.1f} %).  × {_amt(qty)} = +{_n(gain * qty)} {cur}, "
            f"before gold costs.\n"
            f"To buy, post {ba} : {bb} ({cur} : {item});  to sell, post {sa} : {sb} ({item} : {cur})."))


