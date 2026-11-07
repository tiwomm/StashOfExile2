"""2.113.0: the price check in a card over the game (a sample - Price Checks in the app stays as it is).

Settings › Hotkeys › Price Checks › "Show it in a card over the game": your price check key copies the hovered item
(one press = one copy, as always) and, instead of bringing the app forward, a card opens over the game at a spot you
choose - drag it by its title, resize it from any edge; both are remembered. It takes the overlay's Style.

The card: the item (name in its rarity colour; rarity, class, base, item level, quality, corrupted), the price and
how sure it is, the mods searched with their ticks (a tick changes the search; Search again runs it), and the cheapest
listings - each a one-line summary that opens to the whole item (implicits, every mod, corrupted). Search again,
Trade site and Open in app sit at the bottom.

Typing: click into a Min / Max box and the card takes the keyboard (Enter searches again); click back into the
game and it has the keyboard again.

Privacy: other players' seller names show as on the app's card (public on the trade site); your own account name
is never shown here.
GGG ToS: the key presses the game's copy once (overlay.py, as before); the card only shows what the app found.
Works the same on Windows and Linux / Hyprland (an OverlayWindow: topmost, follows the game)."""
import tkinter as tk
from tkinter import ttk

from .config import SETTINGS, save_json
from .style import C, MOD_COL

KIND_COL = {"Implicit": "implicit", "Rune": "rune", "Enchant": "enchant", "Prefix": "explicit", "Suffix": "explicit",
            "Total": "pseudo"}
W0, H0 = 430, 600                 # the first size (then yours)


def pop_on():
    return bool(SETTINGS.get("pc_popup", False))


def ink(c, bg):
    """A game colour (rarity, mod kind) made readable on this card: on a light style (Gilded's marble) the light
    blues / greens / yellows are darkened, same hue, until they reach 4.5 : 1 against it. Dark styles: as is."""
    from .style import contrast, mix
    try:
        if contrast(c, bg) >= 4.5:
            return c
        out = c
        for t in (0.15, 0.3, 0.45, 0.6, 0.75):
            out = mix(c, "#000000", t)
            if contrast(out, bg) >= 4.5:
                return out
        return out
    except Exception:
        return c


class PricePopup:
    """Mixin on the App."""

    # ---------------------------------------------------------------- the window
    def pcpop_geo(self):
        g = SETTINGS.get("pc_pop_geo")
        if isinstance(g, (list, tuple)) and len(g) == 4:
            return tuple(int(v) for v in g)
        try:
            from .alerts_page import game_rect
            r = game_rect()
        except Exception:
            r = None
        if not r:
            r = (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        gx, gy, gw, gh = r
        return gx + gw - W0 - 48, gy + int(gh * 0.12), W0, H0       # right of the middle, clear of the bar

    def pcpop_close(self):
        w, self.pp_win = getattr(self, "pp_win", None), None
        self.pp_rid = None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def pcpop_show(self, rec):
        """Open (or refill) the card for this item."""
        from .overlaywin import OverlayWindow, pal
        if rec is None:
            return None
        if getattr(self, "pp_rid", None) != rec["id"]:
            self.pp_open = set()                          # (which listings are opened - a new item starts closed)
        self.pp_rid = rec["id"]
        w = getattr(self, "pp_win", None)
        if w is not None:
            try:
                if not w.winfo_exists():
                    w = None
            except tk.TclError:
                w = None
        if w is None:
            P = pal()

            def moved(x, y, ww, hh):
                SETTINGS["pc_pop_geo"] = [int(x), int(y), int(ww), int(hh)]
                save_json("settings.json", SETTINGS)
            w = OverlayWindow(self.root, "Price check", "⚖", self.pcpop_geo(), opacity=255, locked=False,
                              min_size=(320, 260), on_close=self.pcpop_close, on_moved=moved, follow_game=True,
                              no_activate=False, resizable=True, lockable=False, palette=P)   # (Min / Max: typing)
            self.pp_win, self.pp_P = w, P
            self._pcpop_frame(w, P)
        self.pcpop_fill(rec)
        w.show()
        try:
            w.lift()
        except tk.TclError:
            pass
        return w

    def _pcpop_frame(self, w, P):
        """The scrolling body (its bar in the style's colours) and the button row under it."""
        st = ttk.Style(self.root)
        name = "PcPop.Vertical.TScrollbar"
        st.configure(name, background=P["line"], troughcolor=P.get("field", P["bg"]), bordercolor=P["bg"],
                     arrowcolor=P["muted"], lightcolor=P["line"], darkcolor=P["line"], gripcount=0, arrowsize=12)
        st.map(name, background=[("active", P["accent"]), ("pressed", P["accent"])])
        foot = tk.Frame(w.body, bg=P["bg"])
        foot.pack(fill="x", side="bottom", padx=8, pady=8)
        self.pp_foot = foot
        tk.Frame(w.body, bg=P["line"], height=1).pack(fill="x", side="bottom")
        box = tk.Frame(w.body, bg=P["bg"])
        box.pack(fill="both", expand=True)
        cv = tk.Canvas(box, bg=P["bg"], highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(box, orient="vertical", command=cv.yview, style=name)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(cv, bg=P["bg"])
        win = cv.create_window((0, 0), window=inner, anchor="nw")
        cv.bind("<Configure>", lambda e: (cv.itemconfigure(win, width=e.width), self._pcpop_wrap(e.width)))
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=(0, 0, e.width, e.height)))

        def wheel(e):
            d = -1 if (getattr(e, "delta", 0) > 0 or getattr(e, "num", 0) == 4) else 1
            cv.yview_scroll(d * 3, "units")
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            w.bind_all(ev, lambda e: wheel(e) if self._pcpop_under(e) else None, add="+")
        self.pp_cv, self.pp_inner, self.pp_sb = cv, inner, sb

    def _pcpop_under(self, e):
        w = getattr(self, "pp_win", None)
        try:
            x, y = w.winfo_rootx(), w.winfo_rooty()
            return w.winfo_ismapped() and x <= e.x_root < x + w.winfo_width() and y <= e.y_root < y + w.winfo_height()
        except (tk.TclError, AttributeError):
            return False

    def _pcpop_wrap(self, width):
        for lbl in getattr(self, "pp_wraps", []):
            try:
                lbl.configure(wraplength=max(160, width - 40))
            except tk.TclError:
                pass

    # ---------------------------------------------------------------- what it shows
    def pcpop_refresh(self, rec):
        """The item on Price Checks changed (searched, priced, a tick): the card follows if it shows that item."""
        if rec is None or getattr(self, "pp_win", None) is None or rec["id"] != getattr(self, "pp_rid", None):
            return
        if getattr(self, "_pp_job", None):
            return

        def go():
            self._pp_job = None
            try:                                          # (never under your typing: a Min / Max box has the keyboard -
                f = str(self.pp_win.tk.call("focus"))     #  try again in a moment)
            except (tk.TclError, AttributeError):
                f = ""
            if f.startswith(str(self.pp_win)) and "entry" in f.lower():
                self._pp_job = self.root.after(400, go)
                return
            self.pcpop_fill(rec)
        self._pp_job = self.root.after(60, go)

    def pcpop_fill(self, rec):
        from .pricecheck_page import RARITY_COL, cur_label, listing_facts
        from .pricefmt import fmt_div
        from .trade import ago, mod_impact
        P = self.pp_P
        inner = self.pp_inner
        top = self.pp_cv.yview()[0] if inner.winfo_children() else 0.0
        for c in inner.winfo_children():
            c.destroy()
        self.pp_wraps = []
        it = rec.get("item") or {}
        body, head = P.get("body") or P["font"], P.get("hfont") or P["font"]
        pad = dict(padx=16)

        def lab(parent, text, fg=None, size=10, bold=False, font=None, wrap=True, **pk):
            l_ = tk.Label(parent, text=text, bg=P["bg"], fg=fg or P["text"], anchor="w", justify="left",
                          font=(font or body, size, "bold") if bold else (font or body, size))
            l_.pack(fill="x", **pk)
            if wrap:
                self.pp_wraps.append(l_)
            return l_

        # the item
        rcol = ink(C.get(RARITY_COL.get(it.get("rarity"), ""), P["big"]), P["bg"])
        name = " ".join(x for x in (it.get("name"), it.get("base")) if x and x != it.get("name") or x == it.get("name")
                        ) if it.get("name") else (it.get("base") or "Item")
        lab(inner, it.get("name") or it.get("base") or "Item", fg=rcol, size=13, bold=True, font=head, pady=(8, 0), **pad)
        info = [f"{it.get('rarity') or ''} {it.get('class') or ''}".strip(),
                it.get("base") if it.get("name") and it.get("base") and it.get("base") != it.get("name") else "",
                f"item level {it['ilvl']}" if it.get("ilvl") else "",
                f"quality {it['quality']}%" if it.get("quality") else ""]
        lab(inner, " · ".join(x for x in info if x), fg=P["muted"], size=9, **pad)
        if it.get("corrupted"):
            lab(inner, "Corrupted", fg=ink(C["red"], P["bg"]), size=9, bold=True, **pad)
        del name

        # the price
        st = rec.get("state")
        box = tk.Frame(inner, bg=P.get("field", P["bg"]), highlightthickness=1, highlightbackground=P["line"])
        box.pack(fill="x", padx=16, pady=(8, 0))
        if st == "done" and rec.get("est") is not None:
            tk.Label(box, text="≈ " + fmt_div(rec["est"]), bg=box["bg"], fg=P["big"], font=(head, 18, "bold"),
                     anchor="w").pack(fill="x", padx=8, pady=(8, 0))
            entries, total, n = self.pc_entries(rec)
            conf = {"high": "a solid price", "medium": "a fair guess", "low": "thin data - check by hand"}.get(
                str(rec.get("conf") or "").lower(), "")
            sub = f"from the {min(n, 5) or n} cheapest of {total} listing{'s' if total != 1 else ''}" + \
                (f" · {conf}" if conf else "")
            tk.Label(box, text=sub, bg=box["bg"], fg=P["muted"], font=(body, 9), anchor="w").pack(
                fill="x", padx=8, pady=(0, 8))
        else:
            msg = {"pricing": "Searching the trade site…", "error": rec.get("label") or "Couldn't search",
                   "done": "No listings matched these mods"}.get(st, "Waiting in line…")
            tk.Label(box, text=msg, bg=box["bg"], fg=C["red"] if st == "error" else P["text"], font=(body, 11),
                     anchor="w", justify="left", wraplength=360).pack(fill="x", padx=8, pady=8)
        if rec.get("changed"):
            lab(inner, "Ticks changed - press Search again.", fg=P["accent"], size=9, pady=(4, 0), **pad)

        # the mods searched (tick = searched; a click changes it, Search again runs it)
        mods = [m for m in it.get("mods") or [] if m.get("text")]
        if mods:
            hr = tk.Frame(inner, bg=P["bg"])
            hr.pack(fill="x", padx=16, pady=(12, 2))
            tk.Label(hr, text="MODS SEARCHED", bg=P["bg"], fg=P["head"], font=(head, 9, "bold")).pack(side="left")
            if any(m.get("sid") and self._card_has_vals(rec, m) for m in mods):
                tk.Label(hr, text="Min      Max", bg=P["bg"], fg=P["muted"], font=(body, 9)).pack(side="right")
            ticked = {id(m) for m in self.pc_ticked(rec)}
            if not ticked:
                ticked = {id(m) for m in mods if m.get("sid") and mod_impact(rec, m) != "ignore"}
            for m in mods:
                row = tk.Frame(inner, bg=P["bg"])
                row.pack(fill="x", padx=16)
                on = id(m) in ticked
                can = bool(m.get("sid"))
                cb = tk.Label(row, text=("☑" if on else "☐") if can else "·", bg=P["bg"],
                              fg=P["accent"] if on else P["muted"], font=("Segoe UI Symbol", 10),
                              cursor="hand2" if can else "")
                cb.pack(side="left", anchor="n")
                col = MOD_COL.get(KIND_COL.get(m.get("kind"), "explicit"), P["text"])
                flags = m.get("flags") or set()
                if "fractured" in flags:
                    col = MOD_COL["fractured"]
                elif "desecrated" in flags:
                    col = MOD_COL["desecrated"]
                tl = tk.Label(row, text=m.get("shown") or m["text"], bg=P["bg"], fg=ink(col, P["bg"]) if on or not can else P["muted"],
                              font=(body, 10), anchor="w", justify="left", cursor="hand2" if can else "")
                if can and self._card_has_vals(rec, m):
                    self._pcpop_vals(row, P, rec, m, on)
                tl.pack(side="left", fill="x", expand=True, padx=(4, 0))
                self.pp_wraps.append(tl)
                if can:
                    for wdg in (cb, tl):
                        wdg.bind("<Button-1>", lambda e, mm=m, o=on: self._pcpop_tick(rec, mm, not o))

        # the cheapest listings - a summary each; click opens the whole item (no seller names)
        if st == "done":
            entries, total, n = self.pc_entries(rec)
            if entries:
                lab(inner, "CHEAPEST LISTINGS", fg=P["head"], size=9, bold=True, font=head, pady=(12, 2), **pad)
            for e in entries:
                f = listing_facts(e)
                self._pcpop_listing(inner, P, f, body, head, cur_label, ago, RARITY_COL)
        tk.Frame(inner, bg=P["bg"], height=10).pack(fill="x")

        # the buttons
        for c in self.pp_foot.winfo_children():
            c.destroy()
        self._pcpop_btn("Search again", lambda: self.reprice([rec["id"]]), primary=True).pack(side="left")
        self._pcpop_btn("Trade site", self.pc_open_trade, enabled=bool(rec.get("qid"))).pack(side="left", padx=(8, 0))
        self._pcpop_btn("Open in app", lambda: self._pcpop_in_app(rec)).pack(side="right")
        self.root.after_idle(lambda: self._pcpop_after(top))

    def _pcpop_btn(self, text, cmd, primary=False, enabled=True):
        """A button in the overlay's Style (not the app theme's): the main one filled with its accent."""
        P = self.pp_P
        if not enabled:
            bg, fg, line = P["bg"], P["muted"], P["line"]
        elif primary:
            bg, fg, line = P["accent"], P.get("on_fg") if P.get("skin") and P.get("on_bg") == P["accent"] else P["bg"], P["accent"]
        else:
            bg, fg, line = P.get("off_bg", P["bg"]), P["text"], P["line"]
        b = tk.Label(self.pp_foot, text=text, bg=bg, fg=fg, padx=12, pady=4, highlightthickness=1,
                     highlightbackground=line, font=(P.get("body") or P["font"], 10, "bold" if primary else "normal"),
                     cursor="hand2" if enabled else "")
        if enabled:
            b.bind("<Button-1>", lambda _e: cmd())
            b.bind("<Enter>", lambda _e: b.config(highlightbackground=P["accent"]))
            b.bind("<Leave>", lambda _e: b.config(highlightbackground=line))
        return b

    def _pcpop_after(self, top):
        try:
            self._pcpop_wrap(self.pp_cv.winfo_width())
            self.pp_cv.update_idletasks()
            self.pp_cv.yview_moveto(top)
        except (tk.TclError, AttributeError):
            pass

    def _pcpop_listing(self, inner, P, f, body, head, cur_label, ago, RARITY_COL):
        lid = f.get("id")
        opened = lid in self.pp_open
        card = tk.Frame(inner, bg=P["bg"], highlightthickness=1, highlightbackground=P["line"])
        card.pack(fill="x", padx=16, pady=(4, 0))
        top = tk.Frame(card, bg=P["bg"], cursor="hand2")
        top.pack(fill="x", padx=8, pady=4)
        amt, cur = f["price"] if f.get("price") else (None, None)
        price = f"{amt:g} {cur_label(cur)}" if amt is not None else "?"
        arrow = tk.Label(top, text="▾" if opened else "▸", bg=P["bg"], fg=P["muted"], font=("Segoe UI Symbol", 10))
        arrow.pack(side="left")
        tk.Label(top, text=price, bg=P["bg"], fg=P["big"], font=(head, 10, "bold")).pack(side="left", padx=(4, 8))
        when = ago(f["ts"]) if f.get("ts") else ""
        seller = f.get("seller") or ""
        if seller and not self._pcpop_mine(seller):          # (yours never shows - with or without its #1234)
            when = f"{seller} · {when}" if when else seller
        if f.get("times", 1) > 1:                             # 2.113.0: one row per seller
            when = f"listed {f['times']}× · {when}" if when else f"listed {f['times']}×"
        if when:
            tk.Label(top, text=when, bg=P["bg"], fg=P["muted"], font=(body, 9)).pack(side="right")
        mods = [t for _tier, t, k in f.get("mods") or [] if k not in ("implicit", "enchant", "rune")]
        summ = " · ".join(mods[:3]) + (" …" if len(mods) > 3 else "")
        sl = tk.Label(card, text=summ or "(no mods)", bg=P["bg"], fg=P["muted"], font=(body, 9), anchor="w",
                      justify="left", cursor="hand2")
        sl.pack(fill="x", padx=(24, 8), pady=(0, 4))
        self.pp_wraps.append(sl)
        if opened:
            sl.pack_forget()
            full = tk.Frame(card, bg=P["bg"])
            full.pack(fill="x", padx=(24, 8), pady=(0, 8))
            rcol = ink(C.get(RARITY_COL.get(f.get("rarity"), ""), P["text"]), P["bg"])
            nm = " ".join(x for x in (f.get("name"), f.get("base")) if x)
            tk.Label(full, text=nm, bg=P["bg"], fg=rcol, font=(head, 10, "bold"), anchor="w").pack(fill="x")
            parts = " · ".join(str(p) for p in (f.get("parts") or []) if p)
            if f.get("ilvl"):
                parts = (parts + " · " if parts else "") + f"item level {f['ilvl']}"
            if parts:
                l_ = tk.Label(full, text=parts, bg=P["bg"], fg=P["muted"], font=(body, 9), anchor="w", justify="left")
                l_.pack(fill="x")
                self.pp_wraps.append(l_)
            for tier, text, kind in f.get("mods") or []:
                l_ = tk.Label(full, text=(f"{tier}  " if tier else "") + text, bg=P["bg"],
                              fg=ink(MOD_COL.get(kind, P["text"]), P["bg"]), font=(body, 10), anchor="w", justify="left")
                l_.pack(fill="x")
                self.pp_wraps.append(l_)
            if f.get("corrupted"):
                tk.Label(full, text="Corrupted", bg=P["bg"], fg=ink(C["red"], P["bg"]), font=(body, 9, "bold"), anchor="w").pack(fill="x")
            if f.get("note"):
                l_ = tk.Label(full, text=f["note"], bg=P["bg"], fg=P["muted"], font=(body, 9), anchor="w", justify="left")
                l_.pack(fill="x")
                self.pp_wraps.append(l_)

        def flip(_e=None):
            (self.pp_open.discard if opened else self.pp_open.add)(lid)
            rec = self.records.get(self.pp_rid)
            if rec is not None:
                self.pcpop_fill(rec)
        for wdg in (top, arrow, sl, *top.winfo_children()):
            wdg.bind("<Button-1>", flip)

    def _pcpop_vals(self, row, P, rec, m, on):
        """Min / Max for one mod, as on the app's card: what the search uses; typing changes it for this item (the same
        m["uval"] the app's card keeps); Enter searches again."""
        from .mods import vfilter
        saved = m.pop("uval", None)
        try:
            auto = vfilter(m) or {}
        finally:
            if saved is not None:
                m["uval"] = saved
        cur = m.get("uval") if m.get("uval") is not None else auto
        boxes = {}
        for key in ("max", "min"):                      # (packed from the right: Min | Max)
            v = cur.get(key)
            e = tk.Entry(row, width=5, bg=P.get("field", P["bg"]), fg=P["text"], insertbackground=P["text"],
                         relief="flat", highlightthickness=1, justify="center",
                         highlightbackground=P["accent"] if m.get("uval") is not None else P["line"],
                         highlightcolor=P["accent"], font=(P.get("body") or P["font"], 9),
                         state="normal" if on else "disabled", disabledbackground=P["bg"],
                         disabledforeground=P["muted"])
            e.insert(0, "" if v is None else f"{v:g}")
            e.pack(side="right", padx=(4, 0))
            boxes[key] = e

        def keep(_e=None):
            vals = {}
            for key, e in boxes.items():
                t = e.get().strip().replace(",", ".")
                try:
                    vals[key] = float(t) if t else None
                    e.config(highlightbackground=P["line"])
                except ValueError:
                    e.config(highlightbackground=C["red"])
                    return False
            if vals["min"] is not None and vals["max"] is not None and vals["min"] > vals["max"]:
                boxes["max"].config(highlightbackground=C["red"])
                return False
            norm_auto = {k: (None if auto.get(k) is None else float(auto[k])) for k in ("min", "max")}
            if vals == norm_auto:
                m.pop("uval", None)
            else:
                m["uval"] = vals
                for e in boxes.values():
                    e.config(highlightbackground=P["accent"])
            rec["changed"] = True
            self.dirty = True
            return True
        for e in boxes.values():
            e.keep = keep                                 # (tests call it: no window manager there to focus a box)
            e.bind("<KeyRelease>", keep)
            e.bind("<Return>", lambda _e: (self.reprice([rec["id"]]) if keep() else None, "break")[-1])
            e.bind("<Button-1>", lambda _e, ee=e: self._pcpop_type(ee), add="+")
        return boxes

    def _pcpop_type(self, e):
        """The card takes the keyboard for typing (Windows: a click on a window over the game may not)."""
        try:
            self.pp_win.focus_force()
            e.focus_set()
        except (tk.TclError, AttributeError):
            pass

    @staticmethod
    def _pcpop_mine(seller):
        try:
            from .trade import is_own
            return is_own(seller)
        except Exception:
            return False

    def _pcpop_tick(self, rec, mod, on):
        self.toggle_mod(rec, mod, on)
        self.card_changed(rec)
        self.pcpop_fill(rec)

    def _pcpop_in_app(self, rec):
        try:
            self.pc_show(rec)
            self.shell.open("pricecheck")
            self.root.deiconify()
            self.root.lift()
        except Exception:
            self.log_error("opening Price Checks")
