"""2.80.0: Price Checks - one item at a time (feedback: "copy the price checker / item panel into a new panel called
Price Checks ... a display of the items on the trade site"). Your price check key (Ctrl+D since 2.83.1) on an item in game opens it here: the item
card with every filter on the left, the trade site's listings as cards on the right (name band, properties, item
level, requirements, each mod with its tier, price, seller, when it was listed, the item's picture). Ctrl+Alt+C
still adds to Bulk Pricing (the old Price checks page).

The listings are the ones the price search already fetched (trade.RAW_LISTINGS) - no extra request. Pictures come
from the trade site's own image server, cached in %APPDATA%/StashOfExile2/art.
GGG ToS: reads your clipboard after YOUR Ctrl+C (the game copies, the app sends nothing) and the trade site's search
within its limits; nothing is clicked, bought or whispered."""
import hashlib
import os
import re
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from .config import APP_UA, P, SETTINGS
from .style import C
from .trade import ago, RAW_LISTINGS, strip_markup

PC_MAX = 20                  # items kept in Recent
ART_PX = 78
RARITY_COL = {"Unique": "unique", "Rare": "rare", "Magic": "magic"}
MOD_KEYS = (("enchantMods", "enchant"), ("implicitMods", "implicit"), ("runeMods", "rune"),
            ("fracturedMods", "fractured"), ("explicitMods", "explicit"), ("desecratedMods", "desecrated"),
            ("craftedMods", "crafted"))


def _clean(x):
    return re.sub(r"\s+", " ", strip_markup(str(x or ""))).strip()


def prop_lines(item):
    """The trade site's properties -> ["Gloves", "Quality: +30%", "Energy Shield: 138"]."""
    out = []
    for p in item.get("properties") or []:
        name, vals = _clean(p.get("name")), [_clean(v[0]) for v in p.get("values") or [] if v]
        if not vals:
            out.append(name)
        elif p.get("displayMode") == 3 and "{0}" in name:
            t = name
            for i, v in enumerate(vals):
                t = t.replace("{%d}" % i, v)
            out.append(t)
        else:
            out.append(f"{name}: {', '.join(vals)}" if name else ", ".join(vals))
    return [x for x in out if x]


def prop_parts(item):
    """2.93.1: the properties as the trade site draws them -> [(label, value, augmented)]: "Energy Shield", "211",
    True when the value is raised by quality / mods (drawn blue). A line without a value: (label, "", False)."""
    out = []
    for p in item.get("properties") or []:
        name = _clean(p.get("name"))
        vals = [v for v in p.get("values") or [] if v]
        if not vals:
            if name:
                out.append((name, "", False))
            continue
        aug = any(len(v) > 1 and v[1] == 1 for v in vals)
        txt = ", ".join(_clean(v[0]) for v in vals)
        if p.get("displayMode") == 3 and "{0}" in name:
            t = name
            for i, v in enumerate(vals):
                t = t.replace("{%d}" % i, _clean(v[0]))
            out.append((t, "", aug))
        else:
            out.append((name, txt, aug))
    return out


def cur_label(cur):
    """A trade-site currency id -> "Divine Orb" (its name when known)."""
    try:
        from .cxnames import item_name
        n = item_name(cur)
    except Exception:
        n = None
    return n or {"divine": "Divine Orb", "exalted": "Exalted Orb", "chaos": "Chaos Orb", "mirror": "Mirror of Kalandra",
                 "annul": "Orb of Annulment", "regal": "Regal Orb", "alch": "Orb of Alchemy",
                 "vaal": "Vaal Orb"}.get(cur, str(cur or "").replace("-", " ").title())


def req_line(item):
    parts = []
    for r in item.get("requirements") or []:
        name, vals = _clean(r.get("name")), [_clean(v[0]) for v in r.get("values") or [] if v]
        if not vals:
            continue
        parts.append(f"Level {vals[0]}" if name.lower() == "level" else f"{vals[0]} {name}")
    return ("Requires: " + ", ".join(parts)) if parts else ""


def _mod_obj(x, kind):
    """2.81.0 (feedback screenshot: mods showed as raw {'description': ...}): one mod as the trade site sends it now -
    {"description", "flags": {"fractured": True ...}, "domain": "rune" / "explicit" / "desecrated" ..., "mods":
    {"tier": "P1", ...} or [...]} -> [(tier, text, kind)]."""
    fl = x.get("flags") or {}
    dom = str(x.get("domain") or "")
    kind = next((k for k in ("fractured", "desecrated", "crafted") if fl.get(k) or dom == k), None) or \
        {"rune": "rune", "implicit": "implicit", "enchant": "enchant"}.get(dom, kind)
    m = x.get("mods")
    if isinstance(m, list):
        m = m[0] if m and isinstance(m[0], dict) else {}
    tier = str((m or {}).get("tier") or "") if isinstance(m, dict) else ""
    out = []
    for part in str(x.get("description") or x.get("text") or "").split("\n"):
        if part.strip():
            out.append((tier, _clean(part), kind))
            tier = ""
    return out


def mod_rows(item):
    """[(tier or "", text, kind)] in the game's order; the tier from the listing's extended data (P1 / S3)."""
    ext = item.get("extended") or {}
    hashes, mods = ext.get("hashes") or {}, ext.get("mods") or {}
    out = []
    for key, kind in MOD_KEYS:
        lines = item.get(key) or []
        hk = {"explicitMods": "explicit", "fracturedMods": "fractured", "desecratedMods": "desecrated",
              "implicitMods": "implicit", "craftedMods": "crafted"}.get(key)
        hl, ml = (hashes.get(hk) or []) if hk else [], (mods.get(hk) or []) if hk else []
        for i, line in enumerate(lines):
            if isinstance(line, dict):                   # 2.81.0: the trade site's mods are objects now
                out.extend(_mod_obj(line, kind))
                continue
            tier = ""
            try:
                idx = (hl[i][1] or [None])[0]
                if idx is not None and idx < len(ml):
                    tier = str(ml[idx].get("tier") or "")
            except (IndexError, TypeError, AttributeError):
                tier = ""
            for part in str(line).split("\n"):
                if part.strip():
                    out.append((tier, _clean(part), kind))
                    tier = ""
    return out


_ICONS = None


def icons():
    """2.105.0: base -> the trade site's picture of it (learned from listings; Market Insights' cards use it)."""
    global _ICONS
    if _ICONS is None:
        from .config import load_json
        try:
            _ICONS = dict(load_json("icons.json", {}) or {})
        except Exception:
            _ICONS = {}
    return _ICONS


def icon_learn(base, url):
    if not base or not str(url or "").startswith("https://"):
        return
    ic = icons()
    if ic.get(base) != url:
        ic[base] = url
        try:
            from .config import save_json
            save_json("icons.json", ic)
        except Exception:
            pass


def listing_facts(e):
    """One trade-site entry -> what its card shows."""
    it, lst = (e or {}).get("item") or {}, (e or {}).get("listing") or {}
    icon_learn(_clean(it.get("baseType") or it.get("typeLine")), it.get("icon"))
    price = lst.get("price") or {}
    ts = None
    try:
        from .trade import listed_ts
        ts = listed_ts(lst.get("indexed")) if lst.get("indexed") else None
    except Exception:
        ts = None
    return {"name": _clean(it.get("name")), "base": _clean(it.get("typeLine") or it.get("baseType")),
            "rarity": it.get("rarity") or "", "props": prop_lines(it), "ilvl": it.get("ilvl"), "req": req_line(it),
            "mods": mod_rows(it), "corrupted": bool(it.get("corrupted")), "icon": it.get("icon") or "",
            "parts": prop_parts(it), "pseudo": [_clean(x if not isinstance(x, dict) else x.get("description"))
                                                 for x in it.get("pseudoMods") or []],
            "note": _clean(it.get("note")) if it.get("note") else "",
            "price": (price.get("amount"), price.get("currency")) if price.get("amount") is not None else None,
            "seller": ((lst.get("account") or {}).get("name") or ""), "ts": ts, "id": (e or {}).get("id"),
            "times": int((e or {}).get("_times") or 1)}           # 2.113.0: the seller listed it this many times



def pc_key_is_copy():
    """2.83.1: is the price check key the game's own Ctrl+C (then the app only listens, as in 2.80.0)?"""
    from .overlay import parse_key
    return parse_key(SETTINGS.get("pc_key") or "") == (0x43, True, False, False)


def pc_key_label():
    from .overlay import key_label
    return key_label(SETTINGS.get("pc_key") or "") or "your price check key"


class PCView:
    """2.84.0: one item card + listings layout (Price Checks, and Favorites uses the same)."""

    def __init__(self, left, lcanvas, lst, rcanvas, count, open_btn):
        self.left, self.lcanvas, self.lst, self.rcanvas, self.count, self.open_btn = \
            left, lcanvas, lst, rcanvas, count, open_btn
        self.cards = []
        self.redraw = None           # fn() -> draw the listings again (a picture arrived)
        self.recard = None           # 2.97.0: fn() -> draw the item card again (its side changed width)


class PriceCheckPage:
    # ---------------------------------------------------------------- the page
    def build_pc(self, body):
        self.pc_body = body
        self.pc_rid = None
        self._pc_art_cache, self._pc_art_wait = {}, set()
        P2 = C["panel2"]
        wrap = tk.Frame(body, bg=P2)
        self.limit_banner(body, wrap)                # 2.103.3: the "Staying under the limits" line
        wrap.pack(fill="both", expand=True)
        # ---- the item card (scrolls), and Recent under it (2.108.0, feedback: "not on the side, it's too crunched")
        left = tk.Frame(wrap, bg=P2, width=380)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        top = tk.Frame(left, bg=P2, padx=12, pady=4)
        top.pack(fill="x")
        self.pc_hist_var = tk.StringVar()                    # (the old dropdown: kept for its callers, never shown)
        self.pc_hist_cb = ttk.Combobox(top, textvariable=self.pc_hist_var, state="readonly")
        self.pc_hist_cb.bind("<<ComboboxSelected>>", lambda e: self.pc_pick_hist())
        rec_col = tk.Frame(left, bg=C["panel"], height=210)
        rec_col.pack(side="bottom", fill="x", padx=12, pady=(8, 8))
        rec_col.pack_propagate(False)
        from .chrome import SectionBar
        SectionBar(rec_col, "Recent").pack(fill="x")
        tv = ttk.Treeview(rec_col, columns=("item", "price", "when"), show="headings", selectmode="browse")
        for cid, title, w, a in (("item", "Item", 200, "w"), ("price", "Price", 80, "e"), ("when", "When", 60, "e")):
            tv.heading(cid, text=title)
            tv.column(cid, width=w, anchor=a, stretch=cid == "item")
        tsb = ttk.Scrollbar(rec_col, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=tsb.set)
        tsb.pack(side="right", fill="y")
        tv.pack(fill="both", expand=True)
        tv.bind("<<TreeviewSelect>>", lambda e: self.pc_pick_hist_tv())
        self.pc_hist_tv = tv
        self.pc_hist_empty = tk.Label(rec_col, text=f"Your last {PC_MAX} checks show here.", bg=C["panel"],
                                      fg=C["muted"], font=("Segoe UI", 9), wraplength=320, justify="center")
        self.pc_lcanvas, self.pc_left = self._pc_scroller(left, padx=12)
        # ---- right: the listings
        right = tk.Frame(wrap, bg=C["panel"])
        right.pack(side="left", fill="both", expand=True)
        head = tk.Frame(right, bg=C["panel"], padx=12, pady=8)
        head.pack(fill="x")
        self.pc_count_lbl = tk.Label(head, text="", bg=C["panel"], fg=C["text"], font=("Segoe UI", 10, "bold"))
        self.pc_count_lbl.pack(side="left")
        # 2.97.3 (feedback): Add to favorites / Open on trade site sit under Search and Clear (pcv_card makes them
        # with each card); these two stand in, unshown, while there's no item
        self.pc_open_btn0 = self.pc_open_btn = ttk.Button(head, text="Trade Site", command=self.pc_open_trade,
                                                          state="disabled")
        self.pc_fav_btn0 = self.pc_fav_btn = ttk.Button(head, text="☆ Add to favorites", command=self.pc_add_fav,
                                                        state="disabled")
        # 2.113.1 (feedback: the switch belongs here): the card over the game - the same switch as Settings › Hotkeys
        ov = ttk.Checkbutton(head, text="Show over the game", variable=self.pc_pop_var(), style="Bar.TCheckbutton",
                             command=self.pc_pop_set)
        ov.pack(side="right")
        from .style import Tooltip
        Tooltip(ov, "On: your price check key shows the price in a card over the game (it takes the overlay's Style; "
                    "drag and resize it - it remembers). Price Checks here still gets every item. Off: the app comes "
                    "to the front, as before.")
        self.pc_rcanvas, self.pc_list = self._pc_scroller(right, padx=12, bg_key="panel")
        self.pcv = PCView(self.pc_left, self.pc_lcanvas, self.pc_list, self.pc_rcanvas, self.pc_count_lbl,
                          self.pc_open_btn)
        self.pcv.redraw = lambda: self.pc_draw_list(self.records.get(self.pc_rid))
        self.pcv.recard = lambda: self.pc_show(self.records.get(self.pc_rid))
        self.pcv_fit(self.pcv, wrap, left)
        self.pc_refresh_hist()
        recs = self.pc_recs()
        self.pc_show(recs[0] if recs else None)

    def pcv_fit(self, v, page, side, lo=380, share=0.32):
        """2.97.0 (feedback: scale to fit, nothing cut off): the card's side takes about a third of the page (wider
        windows: fewer wrapped lines, so no scrollbar), and the card and the listings are drawn again for the width
        they have when the window changes size."""
        state = {"page": 0, "card": 0, "list": 0, "after_card": None, "after_list": None}

        def side_w(pw):
            return max(lo, min(620, int(pw * share)))

        def page_cfg(e):
            if abs(e.width - state["page"]) < 8:
                return
            state["page"] = e.width
            try:
                side.config(width=side_w(e.width))
            except tk.TclError:
                pass

        def later(what):
            slot = "after_" + what
            if state[slot] is not None:
                try:
                    self.root.after_cancel(state[slot])
                except Exception:
                    pass

            def go():
                state[slot] = None
                fn = v.recard if what == "card" else v.redraw
                if fn is not None:
                    try:
                        fn()
                    except Exception:
                        self.log_error("the price check view")
            state[slot] = self.root.after(150, go)

        def card_cfg(e):
            if abs(e.width - state["card"]) >= 12:
                first = not state["card"]
                state["card"] = e.width
                if not first:
                    later("card")

        def list_cfg(e):
            if abs(e.width - state["list"]) >= 12:
                first = not state["list"]
                state["list"] = e.width
                if not first and v.cards:
                    later("list")
        page.bind("<Configure>", page_cfg, add="+")
        v.lcanvas.bind("<Configure>", card_cfg, add="+")
        v.rcanvas.bind("<Configure>", list_cfg, add="+")

    def pcv_wrap(self, v):
        """The card's text width: what its side has (2.97.0; was a fixed 330)."""
        try:
            cw = v.lcanvas.winfo_width()
        except tk.TclError:
            cw = 0
        return max(330, cw - 24 - 12) if cw > 50 else 330

    def _pc_scroller(self, parent, padx=0, bg_key="panel2"):
        bg = C[bg_key]
        box = tk.Frame(parent, bg=bg)
        box.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(box, orient="vertical")
        cv = tk.Canvas(box, bg=bg, highlightthickness=0, yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.config(command=cv.yview)
        inner = tk.Frame(cv, bg=bg, padx=padx, pady=4)
        win = cv.create_window((0, 0), window=inner, anchor="nw")

        from .style import SbGuard
        guard = SbGuard()

        def fit(_e=None):
            """2.97.0 (feedback: no scrollbar when it fits): the bar shows only when there's more to see (2.112.2:
            never flipping back and forth - SbGuard)."""
            try:
                cv.configure(scrollregion=cv.bbox("all"))
                need = inner.winfo_reqheight() > cv.winfo_height() + 1
                if need and not sb.winfo_ismapped():
                    sb.pack(side="right", fill="y", before=cv)
                    guard.flipped()
                elif not need and sb.winfo_ismapped() and guard.may_hide():
                    sb.pack_forget()
                    guard.flipped()
                    cv.yview_moveto(0)
            except tk.TclError:
                pass
        cv.bind("<Configure>", lambda e: (cv.itemconfigure(win, width=e.width), fit()))
        inner.bind("<Configure>", fit)
        cv._sb = sb

        def wheel(e):
            d = -1 if (getattr(e, "delta", 0) > 0 or getattr(e, "num", 0) == 4) else 1
            if inner.winfo_reqheight() > cv.winfo_height():
                cv.yview_scroll(d * 2, "units")
        box.bind("<Enter>", lambda e: (box.bind_all("<MouseWheel>", wheel), box.bind_all("<Button-4>", wheel),
                                       box.bind_all("<Button-5>", wheel)))
        box.bind("<Leave>", lambda e: (box.unbind_all("<MouseWheel>"), box.unbind_all("<Button-4>"),
                                       box.unbind_all("<Button-5>")))
        return cv, inner

    # ---------------------------------------------------------------- items in
    def pc_pop_var(self):
        """The one switch for the card over the game (Price Checks' header and Settings › Keys share it)."""
        v = getattr(self, "_pc_pop_var", None)
        if v is None:
            v = self._pc_pop_var = tk.BooleanVar(value=bool(SETTINGS.get("pc_popup", False)))
        return v

    def pc_pop_set(self):
        from .config import save_json
        SETTINGS["pc_popup"] = bool(self.pc_pop_var().get())
        save_json("settings.json", SETTINGS)
        if not SETTINGS["pc_popup"]:
            self.pcpop_close()

    def pc_wants(self, text):
        """An item copied with your price check key (Ctrl+D; Settings › Keys), with its switch on. Set to Ctrl+C,
        the game's own plain copy counts as before."""
        keys = getattr(self, "keys", None)
        if not SETTINGS.get("pc_ctrl_c", True) or keys is None or not getattr(keys, "active", False):
            return False
        if not text.lstrip().startswith("Item Class:"):
            return False
        if pc_key_is_copy():
            return keys.copy_recent() and not keys.combo_recent()
        return keys.pc_recent()

    def pc_take(self, text):
        """An item for Price Checks: priced first in line, shown on the page (the app comes to the front if you
        want - Settings › Keys)."""
        rid = self.add_item_text(text, src="pc")
        if rid is None:
            from .wealth import parse_currency_item
            cur = parse_currency_item(text)
            if cur:                                      # 2.114.0: currency-like (a Wombgift, an omen ...): its
                self.status_text, self.status_until = f"Pricing {cur[0]}...", time.time() + 10   # going rate
                self.stack_price(cur[0], cur[1], loud=True)
                return None
            self.status_text, self.status_until = "Copied, but that item can't be price checked yet", time.time() + 6
            return None
        old = self.pc_recs()[PC_MAX:]
        for r in old:
            self.records.pop(r["id"], None)
        self.pc_refresh_hist()
        self.pc_show(self.records[rid])
        from .pcpop import pop_on
        if pop_on():                                     # 2.113.0: a card over the game; the app stays where it is
            try:
                self.pcpop_show(self.records[rid])
            except Exception:
                self.log_error("the price check card over the game")
            return rid
        try:
            self.shell.open("pricecheck")
            if SETTINGS.get("pc_front", True):
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
        except Exception:
            self.log_error("opening Price Checks")
        return rid

    def pc_clear(self):
        """2.93.1: clear the single searches - every item on Price Checks (Recent too). Bulk Pricing and Favorites
        stay as they are."""
        for r in self.pc_recs():
            self.records.pop(r["id"], None)
            getattr(self, "batch_ids", set()).discard(r["id"])
            if r.get("raw"):
                getattr(self, "seen_texts", {}).pop(hash(r["raw"].strip()), None)      # copying it again checks it again
        self.dirty = True
        self.pc_rid = None
        self.pc_refresh_hist()
        self.pc_show(None)

    def pc_recs(self):
        return sorted((r for r in self.records.values() if r.get("src") == "pc"), key=lambda r: -r.get("time", 0))

    def pc_label(self, r):
        it = r.get("item") or {}
        name = it.get("name") or it.get("base") or "item"
        return f"{name}  ·  {time.strftime('%H:%M', time.localtime(r.get('time', 0)))}"

    def pc_refresh_hist(self):
        if not hasattr(self, "pc_hist_cb"):
            return
        recs = self.pc_recs()
        self._pc_hist_ids = [r["id"] for r in recs]
        self.pc_hist_cb.config(values=[self.pc_label(r) for r in recs])
        cur = self.records.get(self.pc_rid)
        self.pc_hist_var.set(self.pc_label(cur) if cur else (f"{pc_key_label()} on an item in game" if not recs else ""))
        tv = getattr(self, "pc_hist_tv", None)
        if tv is not None:
            from .pricefmt import fmt_div
            self._pc_hist_quiet = True
            try:
                tv.delete(*tv.get_children())
                for r in recs:
                    it = r.get("item") or {}
                    price = fmt_div(r["est"]) if r.get("est") is not None and not r.get("skip") else \
                        ("…" if r.get("state") in ("queued", "pricing") else "-")
                    tv.insert("", "end", iid=str(r["id"]), values=(it.get("name") or it.get("base") or "item", price,
                                                                   time.strftime("%H:%M", time.localtime(r.get("time", 0)))))
                if cur is not None and tv.exists(str(cur["id"])):
                    tv.selection_set(str(cur["id"]))
                    tv.see(str(cur["id"]))
            finally:
                self._pc_hist_quiet = False
            if recs:
                self.pc_hist_empty.place_forget()
            else:
                self.pc_hist_empty.place(relx=0.5, rely=0.5, anchor="center")

    def pc_pick_hist_tv(self):
        if getattr(self, "_pc_hist_quiet", False):
            return
        sel = self.pc_hist_tv.selection()
        rec = self.records.get(int(sel[0])) if sel else None
        if rec is not None and rec["id"] != getattr(self, "pc_rid", None):
            self.pc_show(rec)

    def pc_pick_hist(self):
        i = self.pc_hist_cb.current()
        ids = getattr(self, "_pc_hist_ids", [])
        if 0 <= i < len(ids) and ids[i] in self.records:
            self.pc_show(self.records[ids[i]])

    # ---------------------------------------------------------------- showing it
    def pc_show(self, rec, card_only=False):
        if rec is not None and getattr(self, "pp_win", None) is not None:
            self.pcpop_refresh(rec)                      # 2.113.0: the card over the game follows
        if not hasattr(self, "pc_left"):
            return
        self._pc_card_only = card_only and rec is not None and rec["id"] == getattr(self, "pc_rid", None)
        old = list(self.pc_left.winfo_children())
        if rec is not None and old:                      # 2.103.1 (feedback: a tick made the card flicker): the new
            return self._pc_show_swap(rec, old)          # card is built beside the old one, then swapped in
        for w in old:
            w.destroy()
        self._pc_show_into(rec)

    def _pc_show_swap(self, rec, old):
        holder = tk.Frame(self.pc_left, bg=C["panel2"])
        self.pcv.left = holder
        try:
            self._pc_show_into(rec, swap=(holder, old))
        finally:
            self.pcv.left = self.pc_left

    def _pc_show_into(self, rec, swap=None):
        self.pc_rid = rec["id"] if rec else None
        self.pc_open_btn, self.pc_fav_btn = self.pc_open_btn0, self.pc_fav_btn0     # (until a card makes its own)
        self.pcv.open_btn = self.pc_open_btn
        self.pc_refresh_hist()
        P2 = C["panel2"]
        if rec is None:
            tk.Label(self.pc_left, text=f"Hover an item in game and press {pc_key_label()}.\nIt shows here with the trade "
                                        "site's listings.\n\n(Ctrl+Alt+C adds items to Bulk Pricing.)",
                     bg=P2, fg=C["muted"], font=("Segoe UI", 10), justify="left", anchor="nw").pack(fill="x", pady=12)
            self.pc_draw_list(None)
            return
        self.pc_card, self.pc_search_btn = self.pcv_card(self.pcv, rec, swap=swap)
        if getattr(self, "_pc_card_only", False):        # 2.103.2: a tick / a typed value - the listings stay as they
            self._pc_card_only = False                   # are (redrawing them was the flicker)
            self.pc_fav_state(rec)
            return
        self.pc_draw_list(rec)

    def pcv_card(self, v, rec, swap=None):
        """The item card with every filter and the Search button, into a view's left side. swap = (new holder, old
        widgets): built into the holder, then the old ones go and the holder shows - in one go (no flicker)."""
        P2, wrap = C["panel2"], self.pcv_wrap(v)
        same = getattr(v, "shown_rid", None) == rec["id"]        # 2.88.2: a tick on the same card keeps the scroll
        top = v.lcanvas.yview()[0] if same else 0
        v.shown_rid = rec["id"]
        self._detail_card(v.left, rec, rec["item"], wrap)
        v.card_rows, v.card_paint, v.card_vals = self.card_rows, self.card_paint, self.card_vals   # 2.103.3: per view
        card = self.detail_card
        btns = tk.Frame(v.left, bg=P2)
        btns.pack(fill="x", pady=(8, 0))
        btn = ttk.Button(btns, text="Search  •  filters changed" if rec.get("changed") else "Search",
                         style="Primary.TButton", command=lambda: self.reprice([rec["id"]]))
        btn.pack(side="left", fill="x", expand=True)
        if v is getattr(self, "pcv", None):                 # 2.93.1 (feedback): Clear - empties Price Checks
            ttk.Button(btns, text="Clear", command=self.pc_clear).pack(side="left", padx=(8, 0))
            more = tk.Frame(v.left, bg=P2)                  # 2.97.3 (feedback): under Search and Clear
            more.pack(fill="x", pady=(8, 0))
            self.pc_fav_btn = ttk.Button(more, text="☆ Add to favorites", command=self.pc_add_fav, state="disabled")
            self.pc_fav_btn.pack(side="left", fill="x", expand=True)
            self.pc_open_btn = ttk.Button(more, text="Trade Site", command=self.pc_open_trade,
                                          state="disabled")
            self.pc_open_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))
            v.open_btn = self.pc_open_btn
        elif v is getattr(self, "favv", None):              # P2 (2.104.0): Open on trade site under the card
            ob = ttk.Button(btns, text="Trade Site", command=self.fav_open_trade,
                            state="normal" if rec.get("qid") else "disabled")
            ob.pack(side="left", padx=(8, 0))
            v.open_btn = ob
        note = self._detail_note(rec)
        if note:
            tk.Label(v.left, text=note[0], bg=P2, fg=note[1], font=("Segoe UI", 9), anchor="w", justify="left",
                     wraplength=wrap).pack(fill="x", pady=(8, 0))
        if swap:
            holder, old = swap
            for w in old:
                w.destroy()
            holder.pack(fill="both", expand=True)
        v.lcanvas.update_idletasks()
        v.lcanvas.yview_moveto(top)
        return card, btn

    def pc_entries(self, rec):
        """The listings behind this item's price: the search the price came from (its first 10)."""
        stages = rec.get("stages") or []
        st = next((s for s in stages if s.get("qid") and s.get("qid") == rec.get("qid")), None) or \
            next((s for s in stages if s.get("ids")), None)
        ids = (st or {}).get("ids") or []
        return [RAW_LISTINGS[i] for i in ids if i in RAW_LISTINGS], (st or {}).get("total", rec.get("total") or 0), \
            len(ids)

    def pc_draw_list(self, rec):
        self.pcv_list(self.pcv, rec)
        self.pc_cards = self.pcv.cards
        self.pc_fav_state(rec)

    def pcv_list(self, v, rec):
        v.open_btn.config(state="normal" if rec and rec.get("qid") else "disabled")
        if rec is None:
            return self.pcv_entries(v, None, 0, 0, "")
        st = rec["state"]
        if st != "done":
            self.pcv_entries(v, None, 0, 0, "Searching the trade site…" if st == "pricing" else
                             ("Couldn't search" if st == "error" else "Waiting in line…"))
            if st == "error" and v in (getattr(self, "pcv", None), getattr(self, "favv", None)):
                why = rec.get("label") or "The trade site didn't answer."
                low = why.lower()
                tip = ("Too many filters for one search: untick a few mods." if "complex" in low else
                       "Pick a league in Settings." if "league" in low else "Wait a moment and try again.")
                self.pc_why_box(v, rec, "Couldn't search", f"{why}\n{tip}",
                                fewer="complex" in low and len(self.pc_ticked(rec)) > 1)
            return
        entries, total, n = self.pc_entries(rec)
        self.pcv_entries(v, entries, total, n)
        if not total and not n and v in (getattr(self, "pcv", None), getattr(self, "favv", None)):
            on = len(self.pc_ticked(rec))                    # P2: Favorites says why too
            self.pc_why_box(v, rec, "No listings matched these filters",
                            (f"{on} mod filter{'s are' if on != 1 else ' is'} on. " if on else "")
                            + "Untick the rarest mod or lower a Min, then press Search.", fewer=on > 1)

    def pc_ticked(self, rec):
        """P1 (2.103.0): the card's ticked mods, top to bottom (the card on screen)."""
        v = self._card_view(rec)                            # P2: Price Checks or Favorites, whichever shows it
        if v is None:
            return []
        rows = v.card_rows or {}
        return [m for _i, (m, on, _r) in sorted(rows.items()) if on and m.get("sid")]

    def pc_why_box(self, v, rec, title, text, fewer=False):
        """P1 (2.103.0): a price check that found nothing says why and what to try, with the buttons for it."""
        box = tk.Frame(v.lst, bg=C["panel2"], padx=16, pady=12, highlightthickness=1, highlightbackground=C["red"])
        box.pack(fill="x", pady=(12, 0))
        tk.Label(box, text=title, bg=C["panel2"], fg=C["red"], font=("Segoe UI", 12, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(box, text=text, bg=C["panel2"], fg=C["text"], anchor="w", justify="left",
                 wraplength=520).pack(fill="x", pady=(4, 0))
        row = tk.Frame(box, bg=C["panel2"])
        row.pack(fill="x", pady=(8, 0))
        ttk.Button(row, text="Search again", style="Primary.TButton",
                   command=lambda: self.reprice([rec["id"]])).pack(side="left")
        if fewer:
            b = ttk.Button(row, text="Search with fewer mods", command=lambda: self.pc_fewer(rec))
            b.pack(side="left", padx=(8, 0))
            from .style import Tooltip
            Tooltip(b, "Unticks the last ticked mod and searches again.")
        v.why_box = box
        return box

    def pc_fewer(self, rec):
        """Untick the last ticked mod and search again."""
        ticked = self.pc_ticked(rec)
        if not ticked:
            return self.reprice([rec["id"]])
        self.toggle_mod(rec, ticked[-1], False)
        self.status_text, self.status_until = f"Unticked: {ticked[-1].get('text', '')[:60]}", time.time() + 6
        self.reprice([rec["id"]])

    def pcv_entries(self, v, entries, total, n, head=None):
        """The listings as cards (entries None: only the heading)."""
        for w in v.lst.winfo_children():
            w.destroy()
        v.cards = []
        if entries is None:
            v.count.config(text=head or "")
            return
        v.count.config(text=f"Showing {len(entries)} of {total:,} items" if total else "No listings found")
        if n and not entries:
            tk.Label(v.lst, text="The listings aren't loaded any more - press Search to load them again.",
                     bg=C["panel"], fg=C["muted"], anchor="w").pack(fill="x", pady=8)
            return
        width = max(420, v.rcanvas.winfo_width() - 24 - 2)          # 2.97.0: the width it has (inner padx 12 + 12)
        for e in entries:
            v.cards.append(self._pc_card(v.lst, listing_facts(e), width))
        v.rcanvas.yview_moveto(0)

    def _pc_card(self, parent, f, w):
        """One listing, laid out as the trade site does (2.93.1, feedback: cleaner, like the site): the picture on the
        left; in the middle the name band, then centered groups split by thin lines - properties (raised values in
        blue), item level and requirements, the socketed / implicit lines, the mods with their tiers at the block's
        left edge (P red, S blue), the site's own totals, Corrupted, the seller's note; on the right the asking
        price, the seller and how long ago."""
        from . import themes as _th
        t = _th.ST.theme
        bg, panel = C["odd"], C["panel"]
        rk = RARITY_COL.get(f["rarity"])
        col = t.c("unique", "#af6025") if rk == "unique" else (C[rk] if rk else C["text"])
        cv = tk.Canvas(parent, width=w, height=200, bg=panel, highlightthickness=0, bd=0)
        cv.pack(fill="x", pady=(0, 8))
        blue, red = "#8888ff", "#d26e5e"
        with _th.raw():
            art_w, side = 100, 190                         # the picture column, the price column
            mx0, mx1 = art_w, max(art_w + 300, w - side - 12)
            cx = (mx0 + mx1) // 2
            box = cv.create_rectangle(mx0, 0, mx1, 199, fill=bg, outline=t.c(t.part("card", "border",
                                                                                     default="border_light")))
            two = bool(f["name"]) and f["name"] != f["base"]
            hh = 46 if two else 30
            name_c = _th.card_header(cv, mx0 + 2, 2, mx1 - 2, hh, col, bg)
            if two:
                cv.create_text(cx, 14, text=f["name"], fill=name_c, font=(_th.head_font(), 11, "bold"))
                cv.create_text(cx, 33, text=f["base"], fill=name_c, font=(_th.head_font(), 10, "bold"))
            else:
                cv.create_text(cx, hh // 2 + 1, text=f["base"] or f["name"], fill=name_c, font=(_th.head_font(), 11, "bold"))
            font = ("Segoe UI", 9)
            tw = mx1 - mx0 - 70
            y = hh + 12

            def sep():
                nonlocal y
                y += 1
                cv.create_line(cx - 110, y, cx + 110, y, fill=C["line"])
                y += 9

            def line(text, fill, bold=False):
                nonlocal y
                tid = cv.create_text(cx, y, text=text, fill=fill, font=("Segoe UI", 9, "bold") if bold else font,
                                     width=tw, justify="center", anchor="n")
                bb = cv.bbox(tid)
                y = (bb[3] if bb else y + 14) + 1
                return tid

            def pair(label, value, aug):
                """"Energy Shield: 211" - the label grey, the value white (blue when raised)."""
                nonlocal y
                if not value:
                    return line(label, C["muted"])
                fm = tkfont.Font(root=cv, family="Segoe UI", size=9)
                a, b = label + ": ", value
                x0 = cx - (fm.measure(a) + fm.measure(b)) // 2
                cv.create_text(x0, y, text=a, fill=C["muted"], font=font, anchor="nw")
                cv.create_text(x0 + fm.measure(a), y, text=b, fill=blue if aug else C["text"], font=font, anchor="nw")
                y += 15
            for label, value, aug in f.get("parts") or [(x, "", False) for x in f["props"]]:
                pair(label, value, aug)
            if f["ilvl"] or f["req"]:
                sep()
                if f["ilvl"]:
                    pair("Item Level", str(f["ilvl"]), False)
                if f["req"]:
                    line(f["req"], C["muted"])
            from .style import MOD_COL                     # 2.97.2: the same colors as the item card
            kc = {"implicit": MOD_COL["implicit"], "rune": MOD_COL["rune"], "enchant": MOD_COL["enchant"],
                  "fractured": MOD_COL["fractured"], "desecrated": MOD_COL["desecrated"], "crafted": MOD_COL["enchant"]}
            first = [m for m in f["mods"] if m[2] in ("enchant", "implicit", "rune")]
            rest = [m for m in f["mods"] if m not in first]
            for group in (first, rest):
                if not group:
                    continue
                sep()
                for tier, text, kind in group:
                    if tier:
                        cv.create_text(mx0 + 10, y, text=tier, anchor="nw", font=("Segoe UI", 8, "bold"),
                                       fill=red if tier[:1] == "P" else blue if tier[:1] == "S" else C["muted"])
                    line(text, kc.get(kind, MOD_COL["explicit"]))
            if f.get("pseudo"):
                y += 2
                for p in f["pseudo"]:
                    line(p, MOD_COL["pseudo"])
            if f["corrupted"]:
                sep()
                line("Corrupted", C["red"], bold=True)
            if f.get("note"):
                sep()
                line(f["note"], C["muted"])
            h_mid = y + 10
            # ---- right: asking price, seller, when
            px = w - side // 2 - 4
            py = 18
            cv.create_rectangle(w - side + 4, py - 8, w - 8, py + 46, fill=C["odd"], outline="")
            cv.create_text(px, py, text="Asking price:", fill=C["muted"], font=("Segoe UI", 9), anchor="n")
            if f["price"]:
                amt, cur = f["price"]
                amt = int(amt) if float(amt).is_integer() else amt
                cv.create_text(px, py + 18, text=f"{amt}× {cur_label(cur)}", fill=C["text"],
                               font=(_th.head_font(), 11, "bold"), anchor="n", width=side - 20, tags=("pcprice",))
            else:
                cv.create_text(px, py + 18, text="no price", fill=C["muted"], font=font, anchor="n")
            cv.create_text(px, py + 60, text=f["seller"] + (f"\nlisted {f['times']} times" if f.get("times", 1) > 1 else ""),
                           fill=C["text"], font=("Segoe UI", 9, "bold"), width=side - 16, anchor="n", justify="center")
            if f["ts"]:
                cv.create_text(px, py + 78, text="listed " + ago(f["ts"]), fill=C["muted"], font=("Segoe UI", 8),
                               anchor="n")
            # ---- left: the picture
            img = self.pc_art(f["icon"]) if SETTINGS.get("pc_art", True) else None
            if img is not None:
                cv.create_image(art_w // 2, max(hh + 8, h_mid // 2 - ART_PX // 2), image=img, anchor="n")
                cv._art = img
            elif f["icon"] and SETTINGS.get("pc_art", True):
                cv._art_url = f["icon"]
            h = max(h_mid, py + 100, ART_PX + hh + 16)
            cv.configure(height=h)
            cv.coords(box, mx0, 0, mx1, h_mid - 1)
        cv._facts = f
        return cv

    def pc_open_trade(self):
        self.open_rec_trade(self.records.get(self.pc_rid))     # 2.105.1: changes are searched first

    # ---------------------------------------------------------------- pictures (the trade site's image server)
    def _pc_art_path(self, url):
        d = P("art")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, hashlib.sha1(url.encode()).hexdigest()[:20] + ".png")

    def pc_art(self, url):
        """The item's picture, from the cache or loaded in the background (the cards are redrawn once it's here)."""
        if not url or not url.startswith("https://"):
            return None
        if url in self._pc_art_cache:
            return self._pc_art_cache[url]
        path = self._pc_art_path(url)
        if os.path.exists(path):
            try:
                from PIL import Image, ImageTk
                im = Image.open(path)
                im.thumbnail((ART_PX, ART_PX))
                ph = ImageTk.PhotoImage(im, master=self.root)
                self._pc_art_cache[url] = ph
                return ph
            except Exception:
                self._pc_art_cache[url] = None
                return None
        failed = getattr(self, "_pc_art_failed", {})
        if url not in self._pc_art_wait and time.time() - failed.get(url, 0) > 600:   # a failed one: again in 10 min
            self._pc_art_wait.add(url)
            threading.Thread(target=self._pc_art_get, args=(url, path), daemon=True).start()
            self.root.after(500, self._pc_art_poll)
        return None

    def _pc_art_get(self, url, path):
        try:
            import requests
            r = requests.get(url, headers={"User-Agent": APP_UA}, timeout=10)
            if r.status_code == 200 and r.content:
                tmp = path + ".tmp"
                with open(tmp, "wb") as fh:
                    fh.write(r.content)
                os.replace(tmp, path)
        except Exception:
            pass
        finally:
            self._pc_art_done = getattr(self, "_pc_art_done", set()) | {url}

    def _pc_art_poll(self):
        done = getattr(self, "_pc_art_done", set())
        if not done:
            if self._pc_art_wait:
                self.root.after(500, self._pc_art_poll)
            return
        self._pc_art_done = set()
        self._pc_art_wait -= done
        got = {u for u in done if os.path.exists(self._pc_art_path(u))}
        self._pc_art_failed = {**getattr(self, "_pc_art_failed", {}), **{u: time.time() for u in done - got}}
        done = got
        for v in (getattr(self, "pcv", None), getattr(self, "favv", None)):      # 2.84.0: each view with cards
            if v is not None and v.redraw and any(getattr(c, "_art_url", None) in done for c in v.cards):
                v.redraw()
        card = next(iter(getattr(self, "ins_card", None) and self.ins_card.winfo_children() or []), None)
        if card is not None and getattr(card, "_art_url", None) in done and getattr(self, "ins_pick", None):
            try:                                          # 2.105.0: Market Insights' card gets its picture too
                self.ins_show(self.ins_pick[0])
            except Exception:
                pass
        if self._pc_art_wait:
            self.root.after(500, self._pc_art_poll)
