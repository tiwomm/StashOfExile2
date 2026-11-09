"""2.113.0: the price check in a card over the game (a sample - Price Checks in the app stays as it is).

Settings › Keys › Price Checks › "Show it in a card over the game": your price check key copies the hovered item
(one press = one copy, as always) and, instead of bringing the app forward, a card opens over the game at a spot you
choose - drag it by its title, resize it from any edge; both are remembered. It takes the overlay's Style.

The card: the item (name in its rarity color; rarity, class, base, item level, quality, corrupted), the price and
how sure it is, the mods searched with their ticks (a tick changes the search; Search again runs it), and the cheapest
listings - each a one-line summary that opens to the whole item (implicits, every mod, corrupted). Search again,
Trade site and Open in app sit at the bottom.

Typing: click into a Min / Max box and the card takes the keyboard (Enter searches again); click back into the
game and it has the keyboard again.

Close key (2.121.1, feedback): Esc by default, as PoE Overlay closes its dialogs - only while the card is open and the
game (or the card) is in front, and that press is used up (the game's menu doesn't open). Set it on Settings › Keys or
with the card's ⚙ (Card settings: the close key, where the price shows, All price check settings…).

Privacy: other players' seller names show as on the app's card (public on the trade site); your own account name
is never shown here.
GGG ToS: the key presses the game's copy once (overlay.py, as before); the card only shows what the app found.
Works the same on Windows and Linux / Hyprland (an OverlayWindow: topmost, follows the game)."""
import tkinter as tk
from tkinter import ttk

from .config import SETTINGS, save_json
from .style import C, MOD_COL

def socket_words(it):
    """2.125.5: an item's socket letters in words -> " (2 augment, 1 jewel)" or ""."""
    t = it.get("socket_types") or ""
    parts = [f"{n} {w}" for n, w in ((t.count("S"), "augment"), (t.count("J"), "jewel")) if n]
    return f" ({', '.join(parts)})" if parts else ""


KIND_COL = {"Implicit": "implicit", "Rune": "rune", "Enchant": "enchant", "Prefix": "explicit", "Suffix": "explicit",
            "Total": "pseudo"}
W0, H0 = 430, 600                 # the first size (then yours)


def pop_on():
    return bool(SETTINGS.get("pc_popup", False))


def ink(c, bg):
    """A game color (rarity, mod kind) made readable on this card: on a light style (Gilded's marble) the light
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
        self.pcpop_settings_close()
        w, self.pp_win = getattr(self, "pp_win", None), None
        self.pp_rid, self.pp_up = None, False
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
                              no_activate=False, resizable=True, lockable=False, palette=P,   # (Min / Max: typing)
                              extra=[("⚙", self.pcpop_settings_toggle, "Card settings")])
            self.pp_win, self.pp_P = w, P
            w.bind("<Escape>", lambda _e: self._pcpop_esc(), add="+")    # (the card has the keyboard: Min / Max)
            self._pcpop_frame(w, P)
        self.pcpop_fill(rec)
        self.pp_up = True                                 # (read by the keyboard watcher: the close key works now)
        w.show()
        try:
            w.lift()
        except tk.TclError:
            pass
        return w

    # ---------------------------------------------------------------- the close key (2.121.1)
    def pc_close_hotkey(self, vk, ctrl, alt, shift):
        """Keyboard watcher thread: your close key while the card is open and the game is in front -> close it (the
        press is used up). Anywhere else the key does its usual job."""
        if not getattr(self, "pp_up", False):
            return False
        from .overlay import parse_key, game_active, POE_TITLE
        k = parse_key(SETTINGS.get("pc_close_key", "Esc") or "")
        if not k or k != (vk, ctrl, alt, shift):
            return False
        if not game_active((getattr(self, "overlay", None) and self.overlay.cfg.get("poe_title")) or POE_TITLE):
            return False
        self.ui_q.put(("pcclose",))
        return True

    def ev_pcclose(self):
        if getattr(self, "pcs_win", None) is not None:   # Card settings open: that goes first
            return self.pcpop_settings_close()
        self.pcpop_close()

    def _pcpop_esc(self):
        """Esc while the card itself has the keyboard (typing a Min / Max) - when Esc is your close key."""
        from .overlay import parse_key
        if parse_key(SETTINGS.get("pc_close_key", "Esc") or "") == (0x1B, False, False, False):
            self.ev_pcclose()

    # ---------------------------------------------------------------- ⚙ Card settings (2.121.1)
    def pcpop_settings_toggle(self):
        if getattr(self, "pcs_win", None) is not None:
            return self.pcpop_settings_close()
        self.pcpop_settings_show()

    def pcpop_settings_close(self, _e=None):
        w, self.pcs_win = getattr(self, "pcs_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def pcpop_settings_show(self):
        """A small box under the ⚙, over the game: where the price shows (Here | Overlay + Here - the same setting as
        Settings and Price Checks), the close key (2.125.5: shown here, set on Keys only), All price check settings….
        2.125.5 (feedback: everything over the game follows the overlay's style): in the overlay's colors and font."""
        from .style import CAPTURING, Tooltip
        from .overlay import key_label
        self.pcpop_settings_close()
        card = getattr(self, "pp_win", None)
        if card is None:
            return
        Q = self.ov_quick_style()
        P1, P2, F = Q["bg"], Q["band"], Q["font"]
        w = tk.Toplevel(self.root, bg=Q["line"])
        w.withdraw()
        w.overrideredirect(True)
        try:
            w.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.pcs_win = w
        box = tk.Frame(w, bg=P1)
        box.pack(padx=1, pady=1)
        head = tk.Frame(box, bg=P2, padx=12, pady=8)
        head.pack(fill="x")
        tk.Label(head, text="Price check overlay", bg=P2, fg=Q["text"], font=(Q["hfont"], 12, "bold")).pack(side="left")
        x_ = tk.Label(head, text="✕", bg=P2, fg=Q["muted"], font=(F, 11), cursor="hand2", padx=4)
        x_.pack(side="right")
        x_.bind("<Button-1>", lambda _e: self.pcpop_settings_close())
        Tooltip(x_, "Close")
        body = tk.Frame(box, bg=P1, padx=12, pady=8)
        body.pack(fill="x")
        tk.Label(body, text="Price shows", bg=P1, fg=Q["text"], font=(F, 10), anchor="w").pack(fill="x")
        chips = tk.Frame(body, bg=P1)
        chips.pack(fill="x", pady=(4, 8))
        cur = "Overlay + Here" if self.pc_show_get() == "both" else "Here"
        self.pcs_chips = {}
        # 2.125.6 (feedback: "Here" = in the app): over the game, "Here" would read as the overlay - the app is named
        words = {"Here": "In the app", "Overlay + Here": "Overlay + the app"}
        for name in self.PC_WHERE:
            on = name == cur
            c = tk.Label(chips, text=("✓ " if on else "") + words[name], bg=Q["field"] if on else P1,
                         fg=Q["text"] if on else Q["muted"], font=(F, 10, "bold" if on else "normal"), padx=8, pady=4,
                         cursor="hand2", highlightthickness=1, highlightbackground=Q["accent"] if on else Q["line"])
            c.pack(side="left", padx=(0, 8))
            c.bind("<Button-1>", lambda _e, n=name: (self._pc_where_pick(n), self.pcpop_settings_show()))
            self.pcs_chips[name] = c
        k = SETTINGS.get("pc_close_key", "Esc")
        r = tk.Frame(body, bg=P1)
        r.pack(fill="x")
        tk.Label(r, text=f"Close key: {key_label(k)}" if k else "Close key: none", bg=P1, fg=Q["text"],
                 font=(F, 10)).pack(side="left")
        go = tk.Label(r, text="Change on Keys ›", bg=P1, fg=Q["accent"], font=(F, 9, "underline"), cursor="hand2")
        go.pack(side="right")
        go.bind("<Button-1>", lambda _e: (self.pcpop_settings_close(), self._pcs_keys()))
        foot = tk.Frame(box, bg=P1, padx=12, pady=8)
        foot.pack(fill="x")
        allb = tk.Label(foot, text="All price check settings…", bg=Q["field"], fg=Q["text"], font=(F, 10), pady=4,
                        cursor="hand2", highlightthickness=1, highlightbackground=Q["line"])
        allb.pack(fill="x")
        allb.bind("<Button-1>", lambda _e: self._pcs_all())
        allb.bind("<Enter>", lambda _e: allb.config(highlightbackground=Q["accent"]))
        allb.bind("<Leave>", lambda _e: allb.config(highlightbackground=Q["line"]))
        w.bind("<Escape>", lambda e: None if CAPTURING[0] is not None else self.pcpop_settings_close())
        w.update_idletasks()
        ww, wh = w.winfo_reqwidth(), w.winfo_reqheight()
        try:
            cx, cy, cw = card.winfo_rootx(), card.winfo_rooty(), card.winfo_width()
        except tk.TclError:
            cx, cy, cw = self.root.winfo_pointerx(), self.root.winfo_pointery(), ww
        try:
            from .alerts_page import game_rect
            g = game_rect()
        except Exception:
            g = None
        if not g:
            g = (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        gx, gy, gw, gh = g
        x = min(max(gx, cx + cw - ww), gx + gw - ww)              # (under the ⚙, on the game's monitor)
        y = min(cy + 34, gy + gh - wh)
        w.geometry(f"+{int(x)}+{int(y)}")
        w.deiconify()
        try:
            w.focus_force()
        except tk.TclError:
            pass
        w.bind("<FocusOut>", lambda _e: self.root.after(150, self._pcs_focus_gone))

    def _pcs_focus_gone(self):
        w = getattr(self, "pcs_win", None)
        if w is None:
            return
        from .style import CAPTURING
        if CAPTURING[0] is not None:                       # (the key box is waiting for a key)
            return
        try:
            f = str(w.tk.call("focus"))
        except tk.TclError:
            f = ""
        if not f.startswith(str(w)):
            self.pcpop_settings_close()

    def _pcs_keys(self):
        """The overlay's close key is set on Keys (2.125.5: one place)."""
        try:
            self.hotkeys_open("checks:pc_close_key")
            self.root.deiconify()
            self.root.lift()
        except Exception:
            from . import buglog
            buglog.caught()

    def _pcs_all(self):
        self.pcpop_settings_close()
        try:
            self.settings_open("Price checking", "pc_single")
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            from . import buglog
            buglog.caught()

    def _pcpop_frame(self, w, P):
        """The scrolling body (its bar in the style's colors) and the button row under it."""
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

        # 2.114.0 (feedback: white / magic bases didn't price the same here): the item's own filters, as on the
        # app's card - base type, item level, quality, sockets (a base's search is these, not its mods)
        s_ = it.get("search") or {}
        if it.get("gear") and s_.get("rarity") != "unique" and it.get("rarity") != "Currency":
            self._pcpop_props(inner, P, rec, it, body, head)

        # the mods searched (tick = searched; a click changes it, Search again runs it)
        every = [m for m in it.get("mods") or [] if m.get("text")]
        mods = [m for m in every if m.get("kind") != "Rune"]
        runes = [m for m in every if m.get("kind") == "Rune"]
        if runes or "J" in (it.get("socket_types") or ""):
            self._pcpop_socketed(inner, P, rec, it, runes, body, head)
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

    def _pcpop_socketed(self, inner, P, rec, it, runes, body, head):
        """2.125.5 (feedback: "it doesn't say slots or show what is in them"): what's in the item's sockets - the
        game's copy gives each socketed rune / soul core / talisman's effect, marked (rune), but not its name, so
        those effects are listed here (tick one to search it); a jewel socket says it's there."""
        from .style import Tooltip
        hr = tk.Frame(inner, bg=P["bg"])
        hr.pack(fill="x", padx=16, pady=(12, 2))
        tk.Label(hr, text="SOCKETED", bg=P["bg"], fg=P["head"], font=(head, 9, "bold")).pack(side="left")
        info = tk.Label(hr, text=(socket_words(it).strip(" ()") or "") + "  ⓘ", bg=P["bg"], fg=P["muted"],
                        font=(body, 9))
        info.pack(side="left", padx=(8, 0))
        Tooltip(info, "What the item's sockets hold. The game's copy (Ctrl+C) lists what each socketed rune, soul "
                      "core or talisman does - not its name - and nothing about a socketed jewel. Socketed effects "
                      "can be swapped, so they aren't searched unless you tick one.")
        ticked = {id(m) for m in self.pc_ticked(rec)}
        for m in runes:
            row = tk.Frame(inner, bg=P["bg"])
            row.pack(fill="x", padx=16)
            on, can = id(m) in ticked, bool(m.get("sid"))
            cb = tk.Label(row, text=("☑" if on else "☐") if can else "◆", bg=P["bg"],
                          fg=P["accent"] if on else P["muted"], font=("Segoe UI Symbol", 10), cursor="hand2" if can else "")
            cb.pack(side="left", anchor="n")
            tl = tk.Label(row, text=m.get("shown") or m["text"], bg=P["bg"],
                          fg=ink(MOD_COL["rune"], P["bg"]) if on or not can else P["muted"], font=(body, 10),
                          anchor="w", justify="left", cursor="hand2" if can else "")
            tl.pack(side="left", fill="x", expand=True, padx=(4, 0))
            self.pp_wraps.append(tl)
            if can:
                for wdg in (cb, tl):
                    wdg.bind("<Button-1>", lambda e, mm=m, o=on: self._pcpop_tick(rec, mm, not o))
        if "J" in (it.get("socket_types") or ""):
            tk.Label(inner, text="◇ A jewel socket - the game's copy doesn't say which jewel is in it.", bg=P["bg"],
                     fg=P["muted"], font=(body, 9), anchor="w", justify="left").pack(fill="x", padx=16)

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

    def _pcpop_props(self, inner, P, rec, it, body, head):
        """PROPERTIES: [✓] Base type (unticked = any base of its kind), [✓] Item level / Quality / Sockets with
        Min / Max - the same rec["opts"] the app's card changes (search_opt_set); Enter searches again."""
        from .searchopts_page import default_opts
        cur = {**default_opts(it), **(rec.get("opts") or {})}
        rows = []
        if it.get("ilvl"):
            rows.append(("ilvl", f"Item level: {it['ilvl']}", it["ilvl"]))
        if it.get("quality"):
            rows.append(("quality", f"Quality: +{it['quality']}%", it["quality"]))
        if it.get("sockets"):
            rows.append(("sockets", f"Sockets: {it['sockets']}" + socket_words(it), it["sockets"]))
        hr = tk.Frame(inner, bg=P["bg"])
        hr.pack(fill="x", padx=16, pady=(12, 2))
        tk.Label(hr, text="PROPERTIES", bg=P["bg"], fg=P["head"], font=(head, 9, "bold")).pack(side="left")
        if rows:
            tk.Label(hr, text="Min      Max", bg=P["bg"], fg=P["muted"], font=(body, 9)).pack(side="right")

        def tick_row(on, text, cmd):
            row = tk.Frame(inner, bg=P["bg"])
            row.pack(fill="x", padx=16)
            cb = tk.Label(row, text="☑" if on else "☐", bg=P["bg"], fg=P["accent"] if on else P["muted"],
                          font=("Segoe UI Symbol", 10), cursor="hand2")
            cb.pack(side="left", anchor="n")
            tl = tk.Label(row, text=text, bg=P["bg"], fg=P["text"] if on else P["muted"], font=(body, 10),
                          anchor="w", cursor="hand2")
            tl.pack(side="left", fill="x", expand=True, padx=(4, 0))
            for wdg in (cb, tl):
                wdg.bind("<Button-1>", lambda e: cmd())
            return row

        def changed():
            rec["changed"] = True
            self.dirty = True
            self.pcpop_fill(rec)

        same = cur.get("base") == "same"
        tick_row(same, f"Base type: {it['base']}" if same else f"Any {it.get('class') or 'base'}",
                 lambda: (self.search_opt_set(rec, "base", "class" if same else "same", redraw=False), changed()))
        if it.get("corrupted"):                              # 2.120.1 (feedback): the Corrupted toggle here too
            cor = cur.get("corrupted") == "yes"
            tick_row(cor, "Corrupted listings only" if cor else "Corrupted or not",
                     lambda: (self.search_opt_set(rec, "corrupted", "any" if cor else "yes", redraw=False), changed()))
        self.pp_props = {}
        for key, label, have in rows:
            v = cur.get(key)
            lo, hi = (v.get("min"), v.get("max")) if isinstance(v, dict) else (v, None)
            on = v not in (None, "", 0, {})
            row = tick_row(on, label, lambda k=key, o=on, h=have: (
                self.search_opt_set(rec, k, None if o else {"min": h}, redraw=False), changed()))
            boxes = {}
            for k, val in (("max", hi if on else None), ("min", lo if on else have)):    # (packed from the right)
                e = tk.Entry(row, width=5, bg=P.get("field", P["bg"]), fg=P["text"], insertbackground=P["text"],
                             relief="flat", highlightthickness=1, highlightbackground=P["line"],
                             highlightcolor=P["accent"], justify="center", font=(body, 9),
                             state="normal" if on else "disabled", disabledbackground=P["bg"],
                             disabledforeground=P["muted"])
                e.insert(0, "" if val is None else str(val))
                e.pack(side="right", padx=(4, 0))
                boxes[k] = e

            def keep(_e=None, k_=key, b=boxes):
                vals = {}
                for k2, e2 in b.items():
                    t = e2.get().strip()
                    try:
                        vals[k2] = int(float(t)) if t else None
                        e2.config(highlightbackground=P["line"])
                    except ValueError:
                        e2.config(highlightbackground=C["red"])
                        return False
                vals = {k2: v2 for k2, v2 in vals.items() if v2 is not None}
                self.search_opt_set(rec, k_, vals or None, redraw=False)
                rec["changed"] = True
                self.dirty = True
                return True
            for e in boxes.values():
                e.keep = keep                                 # (tests call it, as on the mods' boxes)
                e.bind("<KeyRelease>", keep)
                e.bind("<Return>", lambda _e, kp=keep: (self.reprice([rec["id"]]) if kp() else None, "break")[-1])
            self.pp_props[key] = boxes

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
