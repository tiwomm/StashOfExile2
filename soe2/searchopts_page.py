"""The item panel's "Search filters" box (2.4.1): narrow the trade searches for one item, like a trade site's own
filters - who's selling, what they price in, corrupted or not, and for gear item level, quality, sockets and whether
to compare with the same base only. Kept on the item (rec["opts"]); used by every search for it (trade.apply_opts).
"Search with these values" prices it again with them. Nothing changes for other items."""
import tkinter as tk
from tkinter import ttk

from .config import SETTINGS, STATUS_OPTIONS
from .style import C
from .trade import CURRENCY_CHOICES, STATUS_CHOICES

CORRUPT_CHOICES = [("Any", "any"), ("Yes", "yes"), ("No", "no")]


def default_opts(item):
    """What the searches use when you haven't changed anything (for showing it, and for Reset)."""
    st = dict(STATUS_OPTIONS).get(SETTINGS.get("status"), "securable")
    if st == "onlineleague":
        st = "online"
    gear = bool(item.get("gear")) and not item.get("waystone")
    s = item.get("search") or {}
    out = {"status": st, "currency": None,
           "corrupted": ("yes" if item.get("corrupted") else "no") if item.get("gear") else "any"}
    if gear:
        out.update(ilvl=None, quality=None, sockets=s.get("sockets_min"),
                   base="same" if s.get("type") else "class")
    return out


class SearchOptsPage:
    """Mixed into App."""

    def search_filters_box(self, rec, parent, wrap):
        it = rec["item"]
        P1, P2 = C["panel"], C["panel2"]
        base = default_opts(it)
        cur = {**base, **(rec.get("opts") or {})}
        changed = bool(rec.get("opts"))
        open_ = changed or SETTINGS.get("filters_open", False)
        head = tk.Frame(parent, bg=P2)
        head.pack(fill="x", pady=(12, 2))
        arrow = tk.Label(head, text=("▾ " if open_ else "▸ ") + "SEARCH FILTERS", bg=P2, fg=C["steel"], cursor="hand2",
                         font=("Segoe UI", 9, "bold"), anchor="w")
        arrow.pack(side="left")
        if changed:
            tk.Label(head, text="changed for this item", bg=P2, fg=C["good"], font=("Segoe UI", 9)).pack(side="left",
                                                                                                   padx=8)
            rs = tk.Label(head, text="reset", bg=P2, fg="#6ea8ff", cursor="hand2", font=("Segoe UI", 9, "underline"))
            rs.pack(side="right")
            rs.bind("<Button-1>", lambda e: self.search_opts_reset(rec))

        def toggle(_e=None):
            SETTINGS["filters_open"] = not open_
            self.show_detail(rec)
        arrow.bind("<Button-1>", toggle)
        if not open_:
            return
        box = tk.Frame(parent, bg=P1, padx=12, pady=8, highlightthickness=1, highlightbackground=C["line"])
        box.pack(fill="x")
        tk.Label(box, text="Narrow the searches for this item only. Then press Search with these values.", bg=P1,
                 fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left", wraplength=wrap - 40).pack(fill="x")
        g = tk.Frame(box, bg=P1)
        g.pack(fill="x", pady=(4, 0))
        g.columnconfigure(1, weight=1)
        row = [0]

        def label(text):
            tk.Label(g, text=text, bg=P1, fg=C["text"], anchor="w").grid(row=row[0], column=0, sticky="w", pady=2,
                                                                          padx=(0, 8))

        def choice(text, key, choices):
            label(text)
            names = [n for n, _v in choices]
            var = tk.StringVar(value=next((n for n, v in choices if v == cur.get(key)), names[0]))
            cb = ttk.Combobox(g, textvariable=var, values=names, state="readonly", width=24)
            cb.grid(row=row[0], column=1, sticky="w", pady=2)
            cb.bind("<<ComboboxSelected>>", lambda e: self.search_opt_set(rec, key, dict(choices)[var.get()]))
            row[0] += 1

        choice("Seller", "status", STATUS_CHOICES)
        choice("Priced in", "currency", CURRENCY_CHOICES)
        choice("Corrupted", "corrupted", CORRUPT_CHOICES)
        if "base" in base:                                    # gear: how wide to look, and its numbers
            choice("Compare with", "base", [(f"{it['base']} only", "same"),
                                            (f"Any {it.get('class') or 'base of this kind'}", "class")])
            for key, text, have in (("ilvl", "Item level at least", it.get("ilvl")),
                                    ("quality", "Quality at least", it.get("quality")),
                                    ("sockets", "Sockets at least", it.get("sockets"))):
                if not have:
                    continue
                label(text)
                f = tk.Frame(g, bg=P1)
                f.grid(row=row[0], column=1, sticky="w", pady=2)
                on = tk.BooleanVar(value=cur.get(key) not in (None, "", 0))
                val = tk.StringVar(value=str(cur.get(key) or have))
                ent = ttk.Entry(f, textvariable=val, width=6, state="normal" if on.get() else "disabled")

                def flip(k=key, o=on, v=val, e=ent):
                    e.config(state="normal" if o.get() else "disabled")
                    self.search_opt_set(rec, k, _int(v.get()) if o.get() else None, redraw=False)

                def typed(*_a, k=key, o=on, v=val):
                    if o.get():
                        self.search_opt_set(rec, k, _int(v.get()), redraw=False)
                ttk.Checkbutton(f, variable=on, command=flip).pack(side="left")
                ent.pack(side="left", padx=(2, 8))
                val.trace_add("write", typed)
                tk.Label(f, text=f"(this one: {have})", bg=P1, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left")
                row[0] += 1

    def search_opt_set(self, rec, key, value, redraw=True):
        base = default_opts(rec["item"])
        o = dict(rec.get("opts") or {})
        if base.get(key) == value:
            o.pop(key, None)
        else:
            o[key] = value
        if o:
            rec["opts"] = o
        else:
            rec.pop("opts", None)
        self.dirty = True
        if redraw:
            self.show_detail(rec)

    def search_opts_reset(self, rec):
        rec.pop("opts", None)
        self.dirty = True
        self.show_detail(rec)


def _int(s):
    try:
        return int(float(str(s).strip()))
    except ValueError:
        return None
