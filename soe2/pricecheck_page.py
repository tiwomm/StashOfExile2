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


def listing_facts(e):
    """One trade-site entry -> what its card shows."""
    it, lst = (e or {}).get("item") or {}, (e or {}).get("listing") or {}
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
            "price": (price.get("amount"), price.get("currency")) if price.get("amount") is not None else None,
            "seller": ((lst.get("account") or {}).get("name") or ""), "ts": ts, "id": (e or {}).get("id")}



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


class PriceCheckPage:
    # ---------------------------------------------------------------- the page
    def build_pc(self, body):
        self.pc_body = body
        self.pc_rid = None
        self._pc_art_cache, self._pc_art_wait = {}, set()
        P2 = C["panel2"]
        wrap = tk.Frame(body, bg=P2)
        wrap.pack(fill="both", expand=True)
        # ---- left: the item card (scrolls)
        left = tk.Frame(wrap, bg=P2, width=380)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        top = tk.Frame(left, bg=P2, padx=12, pady=8)
        top.pack(fill="x")
        tk.Label(top, text="Recent", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left")
        self.pc_hist_var = tk.StringVar()
        self.pc_hist_cb = ttk.Combobox(top, textvariable=self.pc_hist_var, state="readonly")
        self.pc_hist_cb.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.pc_hist_cb.bind("<<ComboboxSelected>>", lambda e: self.pc_pick_hist())
        self.pc_lcanvas, self.pc_left = self._pc_scroller(left, padx=12)
        # ---- right: the listings
        right = tk.Frame(wrap, bg=C["panel"])
        right.pack(side="left", fill="both", expand=True)
        head = tk.Frame(right, bg=C["panel"], padx=12, pady=8)
        head.pack(fill="x")
        self.pc_count_lbl = tk.Label(head, text="", bg=C["panel"], fg=C["text"], font=("Segoe UI", 10, "bold"))
        self.pc_count_lbl.pack(side="left")
        self.pc_open_btn = ttk.Button(head, text="Open on trade site", command=self.pc_open_trade, state="disabled")
        self.pc_open_btn.pack(side="right")
        self.pc_fav_btn = ttk.Button(head, text="☆ Add to favorites", command=self.pc_add_fav, state="disabled")
        self.pc_fav_btn.pack(side="right", padx=(0, 8))           # 2.84.0
        self.pc_rcanvas, self.pc_list = self._pc_scroller(right, padx=12, bg_key="panel")
        self.pcv = PCView(self.pc_left, self.pc_lcanvas, self.pc_list, self.pc_rcanvas, self.pc_count_lbl,
                          self.pc_open_btn)
        self.pcv.redraw = lambda: self.pc_draw_list(self.records.get(self.pc_rid))
        self.pc_refresh_hist()
        recs = self.pc_recs()
        self.pc_show(recs[0] if recs else None)

    def _pc_scroller(self, parent, padx=0, bg_key="panel2"):
        bg = C[bg_key]
        box = tk.Frame(parent, bg=bg)
        box.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(box, orient="vertical")
        sb.pack(side="right", fill="y")
        cv = tk.Canvas(box, bg=bg, highlightthickness=0, yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.config(command=cv.yview)
        inner = tk.Frame(cv, bg=bg, padx=padx, pady=4)
        win = cv.create_window((0, 0), window=inner, anchor="nw")
        cv.bind("<Configure>", lambda e: cv.itemconfigure(win, width=e.width))
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))

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
    def pc_wants(self, text):
        """An item copied with your price check key (Ctrl+D; Settings › Hotkeys), with its switch on. Set to Ctrl+C,
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
        want - Settings › Hotkeys)."""
        rid = self.add_item_text(text, src="pc")
        if rid is None:
            self.status_text, self.status_until = "Copied, but that item can't be price checked yet", time.time() + 6
            return None
        old = self.pc_recs()[PC_MAX:]
        for r in old:
            self.records.pop(r["id"], None)
        self.pc_refresh_hist()
        self.pc_show(self.records[rid])
        try:
            self.shell.open("pricecheck")
            if SETTINGS.get("pc_front", True):
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
        except Exception:
            self.log_error("opening Price Checks")
        return rid

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

    def pc_pick_hist(self):
        i = self.pc_hist_cb.current()
        ids = getattr(self, "_pc_hist_ids", [])
        if 0 <= i < len(ids) and ids[i] in self.records:
            self.pc_show(self.records[ids[i]])

    # ---------------------------------------------------------------- showing it
    def pc_show(self, rec):
        if not hasattr(self, "pc_left"):
            return
        for w in self.pc_left.winfo_children():
            w.destroy()
        self.pc_rid = rec["id"] if rec else None
        self.pc_refresh_hist()
        P2 = C["panel2"]
        if rec is None:
            tk.Label(self.pc_left, text=f"Hover an item in game and press {pc_key_label()}.\nIt shows here with the trade "
                                        "site's listings.\n\n(Ctrl+Alt+C adds items to Bulk Pricing.)",
                     bg=P2, fg=C["muted"], font=("Segoe UI", 10), justify="left", anchor="nw").pack(fill="x", pady=12)
            self.pc_draw_list(None)
            return
        self.pc_card, self.pc_search_btn = self.pcv_card(self.pcv, rec)
        self.pc_draw_list(rec)

    def pcv_card(self, v, rec):
        """The item card with every filter and the Search button, into a view's left side."""
        P2, wrap = C["panel2"], 330
        same = getattr(v, "shown_rid", None) == rec["id"]        # 2.88.2: a tick on the same card keeps the scroll
        top = v.lcanvas.yview()[0] if same else 0
        v.shown_rid = rec["id"]
        self._detail_card(v.left, rec, rec["item"], wrap)
        card = self.detail_card
        btns = tk.Frame(v.left, bg=P2)
        btns.pack(fill="x", pady=(8, 0))
        btn = ttk.Button(btns, text="Search  •  filters changed" if rec.get("changed") else "Search",
                         style="Primary.TButton", command=lambda: self.reprice([rec["id"]]))
        btn.pack(side="left", fill="x", expand=True)
        note = self._detail_note(rec)
        if note:
            tk.Label(v.left, text=note[0], bg=P2, fg=note[1], font=("Segoe UI", 9), anchor="w", justify="left",
                     wraplength=wrap).pack(fill="x", pady=(8, 0))
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
            return self.pcv_entries(v, None, 0, 0, "Searching the trade site…" if st == "pricing" else
                                    ("Couldn't search" if st == "error" else "Waiting in line…"))
        entries, total, n = self.pc_entries(rec)
        self.pcv_entries(v, entries, total, n)

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
        width = max(420, v.rcanvas.winfo_width() - 40)
        for e in entries:
            v.cards.append(self._pc_card(v.lst, listing_facts(e), width))
        v.rcanvas.yview_moveto(0)

    def _pc_card(self, parent, f, w):
        """One listing, the way the trade site shows it: name band, properties, item level, requirements, mods with
        their tiers on the left edge, and on the right the price, the seller, how long ago, the picture."""
        from . import themes as _th
        t = _th.ST.theme
        bg = C["odd"]
        rk = RARITY_COL.get(f["rarity"])
        col = t.c("unique", "#af6025") if rk == "unique" else (C[rk] if rk else C["text"])
        cv = tk.Canvas(parent, width=w, height=200, bg=C["panel"], highlightthickness=0, bd=0)
        cv.pack(fill="x", pady=(0, 8))
        with _th.raw():
            frame = cv.create_rectangle(0, 0, w - 1, 199, fill=bg, outline=t.c(t.part("card", "border",
                                                                                       default="border_light")))
            two = bool(f["name"]) and f["name"] != f["base"]
            hh = 50 if two else 32
            name_c = _th.card_header(cv, 4, 4, w - 5, hh, col, bg)
            if two:
                cv.create_text(w // 2, 16, text=f["name"], fill=name_c, font=(_th.head_font(), 11, "bold"))
                cv.create_text(w // 2, 36, text=f["base"], fill=name_c, font=(_th.head_font(), 10))
            else:
                cv.create_text(w // 2, hh // 2 + 2, text=f["base"] or f["name"], fill=name_c,
                               font=(_th.head_font(), 11, "bold"))
            side = 150                                   # the price / seller / picture column
            cx = (w - side) // 2
            y = hh + 12
            for line in f["props"]:
                cv.create_text(cx, y, text=line, fill=C["muted"] if ":" not in line else C["text"],
                               font=("Segoe UI", 9))
                y += 16
            if f["ilvl"]:
                y += 4
                cv.create_text(cx, y, text=f"Item Level: {f['ilvl']}", fill=C["text"], font=("Segoe UI", 9))
                y += 16
            if f["req"]:
                cv.create_text(cx, y, text=f["req"], fill=C["muted"], font=("Segoe UI", 9))
                y += 16
            if f["mods"]:
                cv.create_line(cx - 120, y, cx + 120, y, fill=C["line"])
                y += 10
            kc = {"implicit": C["magic"], "rune": C["magic"], "enchant": C["magic"], "fractured": "#e8d6a8",
                  "desecrated": "#d08cff", "crafted": "#b8daf2"}
            for tier, text, kind in f["mods"]:
                if tier:
                    cv.create_text(12, y, text=tier, anchor="w", font=("Segoe UI", 8, "bold"),
                                   fill=C["good"] if tier[1:] in ("1", "2") else C["muted"])
                tid = cv.create_text(cx, y, text=text, fill=kc.get(kind, C["magic"]), font=("Segoe UI", 9),
                                     width=w - side - 60, justify="center")
                bb = cv.bbox(tid)
                y = (bb[3] if bb else y + 8) + 9
            if f["corrupted"]:
                cv.create_text(cx, y + 2, text="Corrupted", fill=C["red"], font=("Segoe UI", 9, "bold"))
                y += 18
            # price, seller, age, picture
            px = w - side // 2 - 8
            py = hh + 22
            if f["price"]:
                amt, cur = f["price"]
                amt = int(amt) if float(amt).is_integer() else amt
                cv.create_text(px, py, text=f"{amt} {cur}", fill=C["text"], font=(_th.head_font(), 14, "bold"),
                               tags=("pcprice",))
            cv.create_text(px, py + 24, text=f["seller"], fill=C["text"], font=("Segoe UI", 9, "bold"),
                           width=side - 10)
            if f["ts"]:
                cv.create_text(px, py + 42, text=ago(f["ts"]), fill=C["muted"], font=("Segoe UI", 8))
            img = self.pc_art(f["icon"]) if SETTINGS.get("pc_art", True) else None
            if img is not None:
                cv.create_image(px, py + 60, image=img, anchor="n")
                cv._art = img
            elif f["icon"] and SETTINGS.get("pc_art", True):
                cv._art_url = f["icon"]
            h = max(y + 10, py + 60 + ART_PX + 12)
            cv.configure(height=h)
            cv.coords(frame, 0, 0, w - 1, h - 1)
        cv._facts = f
        return cv

    def pc_open_trade(self):
        rec = self.records.get(self.pc_rid)
        if rec and rec.get("qid"):
            self.open_qid(rec["qid"])

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
        if self._pc_art_wait:
            self.root.after(500, self._pc_art_poll)
