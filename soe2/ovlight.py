"""Light looks for the overlay (2.101.0, from the mockups - feedback: "a lightweight one is needed desperately").

Four styles drawn with plain canvas lines and text - no Pillow artwork, nothing to re-render when the game window
changes size - each as a Bar (resting on the XP bar) and a Panel (a card you place anywhere), in a set of colours:
  hairline  no box: outlined text and one thin accent line, on one row
  slate     a flat box with thin dividers; a switch that's on is underlined (a bar on its left in the Panel)
  flanks    no box: the numbers beside the life orb, the switches beside the mana orb - the middle stays clear
  micro     the smallest: the times, the rank and the switches as lettered squares (Ritual shows its count, 2/3)
"Classic" is the stone-and-bronze look of before (hudart.py). Settings › Appearance › Overlay settings: Style, then
Colours ("Exile Gold" is the Game bar's own colours; the others are the theme packs'; "Follow the app theme").
The same parts as Classic: the timer and its ⏸ / ▶, the map's time, where you are, its rank (click to rank), Maps,
Avg, the clock, the switches, Notes ▾ / Calc ▾ / Regex ▾ / Vendor ▾, the lock and ⚙ - each with its switch in
Overlay › Options. The goal bar (Focus / Campaign) is drawn in the same style (ovparts.py).

No box (hairline, flanks) needs Windows' see-through colour key (-transparentcolor); on other systems they get the
colour set's box. GGG ToS: looks only - windows of the app's own; nothing here touches the game."""
import re
import sys
import tkinter as tk
from tkinter import font as tkfont

from .overlaywin import CanvasText, OverlayWindow, _P

STYLES = {"classic": "Classic (stone and bronze)", "hairline": "Hairline", "slate": "Slate", "flanks": "Flanks",
          "micro": "Micro"}
LIGHT = ("hairline", "slate", "flanks", "micro")
BOXLESS = ("hairline", "flanks")
KEY = "#010101"                    # a box-less look's see-through colour (never used for anything that shows)
WARN = "#e0a352"

# id: (name, box, line, text, strong, muted, accent) - each theme pack's own surface_sunken, border, text,
# text_strong, text_muted and accent (themes/*.json); Exile Gold is the Classic Game bar's (hudart.palette)
COLORS = {
    "theme": ("Follow the app theme",) + (None,) * 6,
    "exile": ("Exile Gold", "#0d0c0b", "#3a362f", "#d9cfb5", "#efe4c6", "#9a8f78", "#c4a05c"),
    "crypt": ("Gilded Crypt", "#080706", "#3a2e20", "#d9c9a6", "#f3e3be", "#8f7d5f", "#d2a24c"),
    "sunstep": ("Sunstep Temple", "#090705", "#3a3122", "#ecdfbf", "#fff6dd", "#a3926f", "#e8b53c"),
    "emberforge": ("Emberforge", "#070809", "#2d3237", "#e1e4e6", "#ffffff", "#8d959c", "#ff7b2e"),
    "ashen": ("Ashen Rite", "#060404", "#342222", "#ebdfd2", "#fff8f0", "#a08878", "#f0524a"),
    "daybreak": ("Daybreak Stalker", "#070c0a", "#26362e", "#e4e1cf", "#fffbea", "#929c88", "#ff9b54"),
    "midnight": ("Midnight Steel", "#0b111c", "#2b3d5f", "#dbe4f2", "#ffffff", "#7d8da8", "#ffa63d"),
    "hollow": ("Hollow Deep", "#040207", "#2a2238", "#e8e2ef", "#fbf8ff", "#8d82a0", "#b675ff"),
    "jade": ("Jade Circuit", "#050808", "#1f3030", "#cfe5de", "#effffa", "#6f8f86", "#3ee6b8"),
    "neon": ("Neon Chassis", "#0b0e11", "#2d343c", "#cdd6de", "#f4f8fb", "#8c98a4", "#39e58c"),
}
DEFAULT_COLORS = "exile"


def _keep_colors():
    """The colour sets keep their own colours in every app theme (like the Classic looks: overlaywin)."""
    from . import themes as _th
    for c in COLORS.values():
        _th.KEEP.update(v.lower() for v in c[1:] if v and _th.is_hex(v))
    _th.KEEP.update({KEY, WARN})
    _th.KEEP.difference_update({"#000000", "#ffffff"})


_keep_colors()


def can_see_through():
    return sys.platform == "win32"


def palette(style, cid):
    """The colours, font and shape of a light look. "theme" takes the app theme's (a light theme's dark text can't
    be read over the game without a box, so the box-less styles use Exile Gold then)."""
    from .overlaywin import pal
    c = COLORS.get(cid) or COLORS[DEFAULT_COLORS]
    if cid == "theme":
        b = pal()
        if b.get("light") and style in BOXLESS:
            c = COLORS["exile"]
        else:
            c = ("Follow the app theme", b["field"], b["line"], b["text"], b["big"], b["muted"], b.get("accent", b["head"]))
    _name, box, line, text, strong, muted, acc = c
    boxless = style in BOXLESS and can_see_through()
    bg = KEY if boxless else box
    return dict(_P, leather=bg if boxless else line, edge=bg if boxless else "#000000", border=0 if boxless else 1,
                bg=bg, band=bg, field=bg, box=box, head=acc, accent=acc, text=text, big=strong, icon=strong, sub=text,
                muted=muted, line=line, on=acc, off=muted, warn=WARN, cell_bg=bg, cell_line=line, rim=line,
                rim_hi=line, rim_lo=line, bg_top=bg, font="Segoe UI", hfont="Segoe UI", on_icon="◆",
                off_icon="◇", halo="#000000" if boxless else None, boxless=boxless, look=style)


class _Clean(CanvasText):
    """"Maps: 4" -> "Maps 4", "Avg. 6:01" -> "Avg 6:01", "Map  3:12" -> "Map 3:12"."""

    def config(self, **kw):
        if "text" in kw:
            t = " ".join(str(kw["text"]).split())
            kw["text"] = re.sub(r"^(Maps|Avg)[:.]", r"\1", t)
        super().config(**kw)
    configure = config


class _Letter(CanvasText):
    """Micro: a switch's first letter (Ritual's live count stays: 2/3)."""

    def config(self, **kw):
        if "text" in kw:
            t = str(kw["text"])
            m = re.search(r"(\d+/\d+)", t)
            kw["text"] = m.group(1) if m else (t[:1].upper() or "?")
        super().config(**kw)
    configure = config


class _LtClock:
    """The clock: the time only (the date line is left out)."""

    def __init__(self, t):
        self.t, self.text = t, ""

    def cget(self, key):
        return self.text if key == "text" else ""

    def config(self, text="", **_kw):
        self.text = text
        self.t.config(text=(str(text).splitlines() or [""])[0])
    configure = config


class LightOverlay:
    """Mixed into App (with MergedOverlay, which calls _mg_light_build when a light style is chosen)."""

    # ---------------------------------------------------------------- settings
    def ov_look(self):
        v = self.tracker_cfg().get("look", "classic")
        return v if v in STYLES else "classic"

    def ov_look_colors(self):
        v = self.tracker_cfg().get("look_colors", DEFAULT_COLORS)
        return v if v in COLORS else DEFAULT_COLORS

    def ov_light(self):
        return self.ov_look() in LIGHT

    def ov_look_set(self, style=None, colors=None):
        """Settings › Appearance › Overlay settings: Style / Colours picked - the overlay is built again."""
        cfg = self.tracker_cfg()
        if style in STYLES and style != cfg.get("look"):
            cfg["look"] = style
            cfg.pop("lt_pos", None)                        # (a new shape starts fitted to the game)
        if colors in COLORS:
            cfg["look_colors"] = colors
        self.merged_set()

    # ---------------------------------------------------------------- small parts
    def _u(self, n):
        return max(1, int(round(n * getattr(self, "_hud_k", 1.0))))

    def _lt_fm(self, cv, P, size, bold=False, family=None):
        return tkfont.Font(root=cv, family=family or P["font"], size=self._hf(size), weight="bold" if bold else "normal")

    def _lt_text(self, cv, P, x, y, text, size, fill, anchor="w", bold=False, key=None, cls=CanvasText, tags=()):
        f = (P["font"], self._hf(size), "bold") if bold else (P["font"], self._hf(size))
        it = cv.create_text(x, y, text=text, anchor=anchor, fill=fill, font=f, tags=("mg",) + tuple(tags))
        t = cls(cv, it, P["bg"], halo=P.get("halo"))
        if key:
            self.tk_ov_lbls[key] = t
        return t

    def _lt_halo_tags(self, cv, P, tags):
        """Box-less: an outline round text drawn by the shared helpers (menus), so it reads over the game."""
        if not P.get("halo"):
            return
        for tag in tags:
            for it in cv.find_withtag(tag):
                if cv.type(it) == "text":
                    CanvasText(cv, it, P["bg"], halo=P["halo"])

    def _lt_rule(self, cv, P, x0, x1, y, strong="c"):
        """A thin accent line: fading out at the ends (strong "c" = in the middle, "l" / "r" = at that end); a
        box-less look gets a plain line (a fade would end in the see-through colour's black, not the game)."""
        if P.get("boxless") or x1 - x0 < 8:
            cv.create_line(x0, y, x1, y, fill=P["accent"], tags=("mg",))
            return
        from .themes import mix
        n = 24
        seg = (x1 - x0) / n
        for i in range(n):
            t = (i + 0.5) / n
            a = {"l": 1 - t, "r": t}.get(strong, 1 - abs(t - 0.5) * 2)
            cv.create_line(x0 + i * seg, y, x0 + (i + 1) * seg + 1, y, fill=mix(P["bg"], P["accent"], a ** 0.8),
                           tags=("mg",))

    def _lt_glyphs(self, w, cv, P, x, y):
        """The lock and ⚙ (Overlay ↳ Settings), right to left from x. -> x left of them."""
        locked = bool(self.tracker_cfg().get("mlocked"))
        for txt, cmd, tag in (("⚙", self.overlay_settings_go, "mg_cog"),
                              ("🔒" if locked else "🔓", lambda: w._toggle_lock(), "mg_lock")):
            it = cv.create_text(x, y, text=txt, anchor="e", fill=P["muted"],
                                font=("Segoe UI Symbol", self._hf(9)), tags=("mg", tag))
            CanvasText(cv, it, P["bg"], halo=P.get("halo"))
            cv.tag_bind(tag, "<Button-1>", lambda e, c=cmd: c())
            cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
            cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
            bb = cv.bbox(it)
            x = (bb[0] if bb else x - 16) - self._u(6)
        return x

    def _lt_glyphs_w(self, cv, P):
        f = self._lt_fm(cv, P, 9, family="Segoe UI Symbol")
        return f.measure("⚙") + f.measure("🔓") + 2 * self._u(6)

    def _lt_clock(self, cv, P, x, y, anchor="e"):
        t = self._lt_text(cv, P, x, y, "", 9, P["muted"], anchor=anchor)
        self.tk_ov_clock = _LtClock(t)
        return self._lt_fm(cv, P, 9).measure("00:00 PM")

    def _lt_menus(self, w, cv, P, x, y, anchor="e"):
        """Notes ▾ / Calc ▾ / Regex ▾ / Vendor ▾ (MergedOverlay draws them). -> the far edge."""
        x = self._mg_bar_buttons(w, cv, P, x, y, anchor=anchor)
        self._lt_halo_tags(cv, P, ("mg_notes", "mg_calc", "mg_regex", "mg_vendor"))
        return x

    def _lt_menus_w(self, cv, P):
        f = self._lt_fm(cv, P, 9)
        names = {"notes": "Notes  ▾", "calc": "Calc  ▾", "regex": "Regex  ▾", "vendor": "Vendor  ▾"}
        return sum(f.measure(names[k]) + 12 for k in self.bar_buttons()) + self._u(6)

    def _lt_time(self, cv, P, x, y, size, num=False, below=False):
        """The session time (bold) and its small PAUSED tag. -> the width kept for it."""
        t = self._lt_text(cv, P, x, y, "", size, P["big"], bold=True, key="session", cls=self._time_cls())
        t.num = num
        tag = cv.create_text(x, y, text="", anchor="nw" if below else "w", fill=P["muted"],
                             font=(P["font"], self._hf(7), "bold"), tags=("mg",))
        t.tag = (tag, "below" if below else "right")
        fb, fp = self._lt_fm(cv, P, size, True), self._lt_fm(cv, P, 7, True)
        if num:                                              # ("not tracking" shows as --:--)
            return fb.measure("0:00:00") + 6 + fp.measure("PAUSED")
        return max(fb.measure("0:00:00") + 6 + fp.measure("PAUSED"), fb.measure("not tracking")) + 4

    @staticmethod
    def _time_cls():
        from .merged_page import _Time
        return _Time

    def _lt_rank(self, cv, P, x, y, size=9, anchor="w"):
        t = self._lt_text(cv, P, x, y, "", size, P["accent"], anchor=anchor, bold=True, key="rank")
        self._rank_click(cv, t)
        return self._lt_fm(cv, P, size, True).measure("★ (A)")

    def _lt_where(self, cv, P, x, y, limit, anchor="w", size=9):
        from .merged_page import _Trunc
        t = self._lt_text(cv, P, x, y, "", size, P["text"], anchor=anchor, key="where", cls=_Trunc)
        t.limit = max(4, int(limit))
        return t

    # ---------------------------------------------------------------- the switches
    def _lt_chip_w(self, cv, P, k, style, size=9):
        from .merged_page import chip_name
        f = self._lt_fm(cv, P, size)
        name = "Ritual 3/3" if k == "ritual" else chip_name(k)
        if style == "micro":
            return max(self._u(22), f.measure("3/3") + self._u(8))
        if style == "slate":
            return f.measure(name) + 2 * self._u(9)
        return self._lt_fm(cv, P, size, family="Segoe UI Symbol").measure("◆") + self._u(4) + f.measure(name)

    def _lt_chip(self, cv, P, k, x, y0, y1, style, size=9, mark="under"):
        """One switch from x, between y0 and y1 (click switches it; hover says what it does). Each style shows on
        / off its own way: ◆ / ◇ (hairline, flanks), an accent underline or left bar (slate), a filled square
        (micro). -> its width."""
        from .merged_page import chip_name
        tag = f"mgcell_{k}"
        mid = (y0 + y1) // 2
        cw = self._lt_chip_w(cv, P, k, style, size)
        f = (P["font"], self._hf(size))
        if style in ("hairline", "flanks"):
            dot = cv.create_text(x, mid, text=P["off_icon"], anchor="w", fill=P["off"],
                                 font=("Segoe UI Symbol", self._hf(size)), tags=("mg", tag))
            gx = self._lt_fm(cv, P, size, family="Segoe UI Symbol").measure("◆") + self._u(4)
            lab = cv.create_text(x + gx, mid, text=chip_name(k), anchor="w", fill=P["text"], font=f, tags=("mg", tag))
            d = CanvasText(cv, dot, P["bg"], halo=P.get("halo"))
            lt = CanvasText(cv, lab, P["bg"], halo=P.get("halo"))
        elif style == "slate":
            cv.create_rectangle(x, y0, x + cw, y1, fill=P["bg"], outline="", tags=("mg", tag))     # (the click area)
            dot = cv.create_text(x, mid, text=P["off_icon"], state="hidden", tags=("mg", tag))
            lab = cv.create_text(x + self._u(9), mid, text=chip_name(k), anchor="w", fill=P["text"], font=f,
                                 tags=("mg", tag))
            mk = self._u(2)
            box = (x, y1 - mk, x + cw, y1) if mark == "under" else (x, y0, x + mk, y1)
            lit = cv.create_rectangle(*box, fill=P["accent"], outline="", state="hidden", tags=("mg", tag))
            d = CanvasText(cv, dot, P["bg"])
            lt = CanvasText(cv, lab, P["bg"])

            def relit(d=d, lit=lit):
                on = cv.itemcget(d.item, "text") == P["on_icon"]
                cv.itemconfigure(lit, state="normal" if on else "hidden", fill=cv.itemcget(d.item, "fill") or P["on"])
            d.on_change = relit
        else:                                                # micro: a lettered square
            sq = cv.create_rectangle(x, y0, x + cw, y1, fill=P["bg"], outline=P["line"], tags=("mg", tag))
            dot = cv.create_text(x, mid, text=P["off_icon"], state="hidden", tags=("mg", tag))
            lab = cv.create_text(x + cw // 2, mid, text=chip_name(k)[:1], anchor="center", fill=P["muted"],
                                 font=(P["font"], self._hf(size - 1), "bold"), tags=("mg", tag))
            d = CanvasText(cv, dot, P["bg"])
            lt = _Letter(cv, lab, P["bg"])

            def relit(d=d, lab=lab, sq=sq):
                on = cv.itemcget(d.item, "text") == P["on_icon"]
                col = cv.itemcget(d.item, "fill") or P["on"]
                cv.itemconfigure(sq, fill=col if on else P["bg"], outline=col if on else P["line"])
                cv.itemconfigure(lab, fill=P["box"] if on else P["muted"])
            lt.on_change = relit
        lt.key = k
        cv.tag_bind(tag, "<Button-1>", lambda e, k=k: self.tracker_helper_click(k))
        cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
        self.ov_help_bind(cv, tag, k)                       # what it does, on hover
        self.tk_ov_alerts[k] = (d, lt)
        return cw

    def _lt_chip_grid(self, cv, P, x0, x1, y, style, right=False, size=9, rh=None, mark="under"):
        """The switches in two columns between x0 and x1 (right=True: pushed to the right edge). -> y under them."""
        chips = self.bar_chips()
        rh = rh or self._u(18)
        gap = self._u(12)
        colw = max([self._lt_chip_w(cv, P, k, style, size) for k in chips] or [0])
        if style == "slate":
            colw = (x1 - x0) // 2
            gap = 0
        for i, k in enumerate(chips):
            col, row = i % 2, i // 2
            if right:
                cx = x1 - (2 - col) * colw - (1 - col) * gap
                cx = cx + colw - self._lt_chip_w(cv, P, k, style, size) if style != "slate" else cx
            else:
                cx = x0 + col * (colw + gap)
            self._lt_chip(cv, P, k, cx, y + row * rh, y + (row + 1) * rh, style, size, mark=mark)
        return y + ((len(chips) + 1) // 2) * rh

    def _lt_chip_grid_w(self, cv, P, style, size=9):
        chips = self.bar_chips()
        colw = max([self._lt_chip_w(cv, P, k, style, size) for k in chips] or [0])
        return colw * min(2, len(chips)) + (self._u(12) if len(chips) > 1 else 0)

    # ---------------------------------------------------------------- the window(s)
    def _mg_light_build(self, want):
        """The overlay in a light style: one window (two for the Flanks bar - right of the life orb and left of the
        mana orb). A Bar is fitted to the game's XP bar (drag it while unlocked; picking the style again puts it
        back); a Panel goes where you put it."""
        from . import themes as TH
        from .overlaywin import _seed
        cfg = self.tracker_cfg()
        style = self.ov_look()
        bar = self.merged_layout() == "xpbar"
        P = palette(style, self.ov_look_colors())
        _seed(TH, P)
        self.mg_P = P
        spot = self.hud_spots("xpbar")[0]                    # (sizes follow the game window's height)
        self.tk_ov_lbls, self.tk_ov_alerts, self.tk_ov_clock, self.tk_ov_cv = {}, {}, None, None
        if bar and style == "flanks":
            pieces = (["left"] if want["timer"] else []) + ["right"]
        else:
            pieces = ["all"]
        from .alerts_page import game_rect
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        saved = (cfg.get("lt_pos") or {}).get(style) or []
        if saved and (cfg.get("lt_res") or {}).get(style) != [int(r[2]), int(r[3])]:
            saved = []                                       # (another game size: fitted again)
        wins = []
        for slot, piece in enumerate(pieces):
            def moved(nx, ny, _w, _h, slot=slot):
                if bar:
                    pos = cfg.setdefault("lt_pos", {}).setdefault(style, [])
                    while len(pos) <= slot:
                        pos.append(None)
                    pos[slot] = [int(nx), int(ny)]
                    rr = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
                    cfg.setdefault("lt_res", {})[style] = [int(rr[2]), int(rr[3])]
                else:
                    cfg.update(mx=nx, my=ny)
                self.tracker_save()
                self.goalbar_follow()
            px, py = (cfg.get("mx", cfg.get("x", 60)), cfg.get("my", cfg.get("y", 260))) if not bar else (0, 0)
            w = OverlayWindow(self.root, "Session", "⏱", (px, py, None, None), opacity=int(cfg.get("opacity", 225)),
                              locked=bool(cfg.get("mlocked")), min_size=(40, 16), on_close=self.merged_close,
                              on_lock=lambda on: self.overlay_lock(on), on_moved=moved, follow_game=True,
                              no_activate=True, resizable=False, titlebar=False, palette=P)
            w.withdraw()
            if P["boxless"]:
                try:
                    w.attributes("-transparentcolor", KEY)
                except tk.TclError:
                    pass
            cv = w.canvas_body()
            if not cfg.get("mlocked"):
                w.draggable(cv)
            draw = getattr(self, f"_lt_{style}_{'bar' if bar else 'panel'}")
            W, H = draw(w, cv, P, want, spot, piece)
            cv.configure(width=W, height=H)
            if bar:
                sx, sy, sw, sh = spot
                bottom = sy + sh
                x = sx if piece in ("all", "left") else sx + sw - W
                if style == "micro":
                    x = sx + (sw - W) // 2
                y = bottom - H
                if slot < len(saved) and isinstance(saved[slot], (list, tuple)) and len(saved[slot]) == 2:
                    x, y = int(saved[slot][0]), int(saved[slot][1])
                w.geometry(f"+{int(x)}+{int(y)}")
            wins.append(w)
        self.mg_win = wins[0]
        self.mg_win2 = wins[1] if len(wins) > 1 else None
        self.mg_notes_host = wins[-1]
        self.tk_overlay = self.mg_win if want["timer"] else None
        self.tk_helpers = None
        self.tracker_overlay_draw(self.tracker_numbers())
        self.tracker_helpers_paint()
        for w in wins:
            if getattr(self, "mg_hidden", False):
                w.hide()
            else:
                w.show()
        if not bar and not getattr(self, "mg_hidden", False):
            self._mg_on_screen(self.mg_win)
        return self.mg_win

    def _mg_bounds(self):
        """(x, y, w, h) round the overlay's window(s) - both halves of the Flanks bar."""
        out = None
        for w in (getattr(self, "mg_win", None), getattr(self, "mg_win2", None)):
            if w is None:
                continue
            w.update_idletasks()
            x, y, ww, hh = w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height()
            if ww <= 1:
                continue
            if out is None:
                out = [x, y, x + ww, y + hh]
            else:
                out = [min(out[0], x), min(out[1], y), max(out[2], x + ww), max(out[3], y + hh)]
        if out is None:
            raise tk.TclError("no overlay window")
        return out[0], out[1], out[2] - out[0], out[3] - out[1]

    # ---------------------------------------------------------------- Bars
    def _lt_row(self, w, cv, P, want, W, style):
        """Hairline / Slate bar, as wide as the XP bar. One row when it all fits: ⏸ time | ★ rank  Map 3:12  Arcane
        Isle | Maps | Avg ... the switches | menus | clock, lock, ⚙. Two rows when it doesn't (the XP bar is narrow
        at 16:9): the switches and menus on top, the numbers, clock, lock and ⚙ under them."""
        from .merged_page import _MapPart, _PartOf
        u = self._u
        slate = style == "slate"
        cfg, ln = self.tracker_cfg(), self.tracker_cfg()["lines"]
        fm = self._lt_fm(cv, P, 10)
        pad, sw = u(10), u(20)                              # (sw: a separator's slot)
        chips = self.bar_chips() if want["helpers"] else []
        cgap = 0 if slate else u(12)
        chips_w = sum(self._lt_chip_w(cv, P, k, style) for k in chips) + cgap * max(0, len(chips) - 1)
        menus_w = self._lt_menus_w(cv, P) if self.bar_buttons_on() else 0
        clock = want["timer"] and cfg.get("clock", True)
        clock_w = self._lt_fm(cv, P, 9).measure("00:00 PM") if clock else 0
        widths = {"maps": fm.measure("Maps 000") + u(4), "avg": fm.measure("Avg 00:00") + u(4)}
        fixed = [k for k in ("maps", "avg") if ln.get(k)] if want["timer"] else []
        left_min = 0
        if want["timer"]:
            left_min = self._lt_fm(cv, P, 12, True).measure("0:00:00 PAUSED") + u(30) + sw + u(40) + u(110) + \
                sum(widths[k] + sw for k in fixed)
        right_w = self._lt_glyphs_w(cv, P) + (clock_w + sw if clock else 0) + (menus_w + sw if menus_w else 0) + \
            (chips_w + sw if chips else 0)
        two = bool(chips) and want["timer"] and left_min + right_w > W - 2 * pad

        def sep(x, y0, y1, mid):
            if slate:
                cv.create_line(x, y0, x, y1, fill=P["line"], tags=("mg",))
            else:
                self._lt_text(cv, P, x, mid, "·", 10, P["muted"], anchor="center")

        if two:
            H = u(52)
            r1, r2 = (0, u(25)), (u(25), H - (0 if slate else u(4)))
        else:
            H = u(30)
            r1 = r2 = (0, H - (0 if slate else u(4)))
        m1, m2 = (r1[0] + r1[1]) // 2, (r2[0] + r2[1]) // 2

        def draw_chips(x_right, y0, y1, mid):
            cx = x_right - chips_w
            for k in chips:
                cx += self._lt_chip(cv, P, k, cx, y0 if slate else mid - u(9), y1 if slate else mid + u(9), style) + cgap
            return x_right - chips_w
        # ---- the right end of the (bottom) row: lock, ⚙, the clock; in one row also the menus and switches
        x = self._lt_glyphs(w, cv, P, W - pad, m2)
        if clock:
            x -= self._lt_clock(cv, P, x, m2) + u(4)
            sep(x - sw // 2, *r2, m2)
            x -= sw
        if not two:
            if menus_w:
                x = self._lt_menus(w, cv, P, x, m2) + 12 - u(4)
                sep(x - sw // 2, *r2, m2)
                x -= sw
            if chips:
                x = draw_chips(x, *r2, m2) - u(4)
                if want["timer"]:
                    sep(x - sw // 2, *r2, m2)
                    x -= sw
        else:                                                # ---- the top row: switches, then the menus
            tx = W - pad
            if menus_w:
                tx = self._lt_menus(w, cv, P, tx, m1) + 12 - u(4)
                sep(tx - sw // 2, *r1, m1)
                tx -= sw
            draw_chips(tx, *r1, m1)
            if slate:
                cv.create_line(0, r1[1], W, r1[1], fill=P["line"], tags=("mg",))
            else:
                self._lt_rule(cv, P, pad, W - pad, r1[1], strong="c")
        right = x
        x = pad
        if want["timer"]:
            drawn = []

            def lead(x):
                if drawn:
                    sep(x + sw // 2, *r2, m2)
                    return x + sw
                return x
            if ln.get("session", True):
                x += self._mg_play(cv, P, x, m2, anchor="w", size=10) + u(6)
                x += self._lt_time(cv, P, x, m2, 12, num=True) + u(4)
                drawn.append("session")
            if ln.get("rank", True) or ln.get("map", True) or ln.get("where", True):
                x = lead(x)
                if ln.get("rank", True):
                    x += self._lt_rank(cv, P, x, m2) + u(6)
                room = right - x - sum(widths[k] + sw for k in fixed) - u(4)
                if room > u(30) and (ln.get("map", True) or ln.get("where", True)):
                    it = cv.create_text(x, m2, text="", anchor="w", fill=P["text"], font=(P["font"], self._hf(10)),
                                        tags=("mg",))
                    part = _MapPart(cv, it, P["bg"], halo=P.get("halo"))
                    part.width, part.font = room, (P["font"], self._hf(10))
                    part.show = (ln.get("map", True), ln.get("where", True), False)
                    self.tk_ov_lbls["map"] = _PartOf(part, "map")
                    self.tk_ov_lbls["where"] = _PartOf(part, "where")
                    x += room
                drawn.append("map")
            for k in fixed:
                x = lead(x)
                self._lt_text(cv, P, x + widths[k] // 2, m2, "", 10, P["big"], anchor="center", key=k, cls=_Clean)
                x += widths[k]
                drawn.append(k)
            if self.tk_ov_cv is None:
                self.tk_ov_cv = cv
        if not slate:                                       # the hairline under the (bottom) row
            self._lt_rule(cv, P, pad, W - pad, H - u(3), strong="c")
        return W, H

    def _lt_hairline_bar(self, w, cv, P, want, spot, piece):
        return self._lt_row(w, cv, P, want, spot[2], "hairline")

    def _lt_slate_bar(self, w, cv, P, want, spot, piece):
        return self._lt_row(w, cv, P, want, spot[2], "slate")

    def _lt_flanks_bar(self, w, cv, P, want, spot, piece):
        """Flanks: "left" = the numbers (right of the life orb), "right" = the switches, menus, clock, lock and ⚙
        (left of the mana orb). Each piece is as small as its content."""
        u = self._u
        cfg, ln = self.tracker_cfg(), self.tracker_cfg()["lines"]
        pad = u(6)
        rl = u(150)                                          # the accent rule's length
        if piece == "left":
            fm = self._lt_fm(cv, P, 9)
            y1 = u(8) + u(11)
            y2 = y1 + u(19)
            x = pad
            if ln.get("session", True):
                x += self._mg_play(cv, P, x, y1, anchor="w", size=10) + u(6)
                x += self._lt_time(cv, P, x, y1, 13, num=True) + u(6)
            if ln.get("map", True):
                self._lt_text(cv, P, x, y1, "", 9, P["text"], key="map", cls=_Clean)
                x += fm.measure("Map 00:00")
            w1 = x
            x = pad
            if ln.get("rank", True):
                x += self._lt_rank(cv, P, x, y2) + u(6)
            if ln.get("where", True):
                self._lt_where(cv, P, x, y2, 22)
                x += fm.measure("Arcane Isle of the Dead") + u(6)
            for k, sample in (("maps", "Maps 000"), ("avg", "Avg 00:00")):
                if ln.get(k):
                    self._lt_text(cv, P, x, y2, "", 9, P["big"], key=k, cls=_Clean)
                    x += fm.measure(sample) + u(8)
            W = max(w1, x, rl) + pad
            self._lt_rule(cv, P, pad, pad + rl, u(4), strong="l")
            self.tk_ov_cv = cv
            return W, y2 + u(12)
        # right
        y = u(4)
        rows_w = []
        cw = self._lt_chip_grid_w(cv, P, "flanks") if want["helpers"] else 0
        gw = self._lt_glyphs_w(cv, P)
        clock = want["timer"] and cfg.get("clock", True)
        foot_w = gw + (self._lt_fm(cv, P, 9).measure("00:00 PM") + u(10) if clock else 0)
        menus_w = self._lt_menus_w(cv, P) if self.bar_buttons_on() else 0
        rows_w += [cw, foot_w + (menus_w + u(6) if menus_w and foot_w + menus_w < u(320) else 0), rl]
        W = max(rows_w) + 2 * pad
        R = W - pad
        self._lt_rule(cv, P, R - rl, R, y, strong="r")
        y += u(6)
        if want["helpers"]:
            y = self._lt_chip_grid(cv, P, pad, R, y, "flanks", right=True)
        fy = y + u(9)
        x = self._lt_glyphs(w, cv, P, R, fy)
        if clock:
            x -= self._lt_clock(cv, P, x, fy) + u(10)
        if menus_w:
            if foot_w + menus_w < u(320):
                self._lt_menus(w, cv, P, x, fy)
            else:
                fy += u(18)
                self._lt_menus(w, cv, P, R, fy)
        return W, fy + u(10)

    def _lt_micro_bar(self, w, cv, P, want, spot, piece):
        """Micro: ⏸ time | 3:12 ★ A | B D R E | menus · lock ⚙ - only as wide as that."""
        u = self._u
        cfg, ln = self.tracker_cfg(), self.tracker_cfg()["lines"]
        H = u(26)
        mid = H // 2
        pad = u(8)
        fm = self._lt_fm(cv, P, 10)
        x = pad

        def sep(x):
            cv.create_line(x, mid - u(7), x, mid + u(7), fill=P["line"], tags=("mg",))
            return x + u(10)
        if want["timer"]:
            if ln.get("session", True):
                x += self._mg_play(cv, P, x, mid, anchor="w", size=9) + u(4)
                x += self._lt_time(cv, P, x, mid, 11, num=True) + u(8)
            if ln.get("map", True) or ln.get("rank", True):
                x = sep(x)
            if ln.get("map", True):
                from .merged_page import _Num
                self._lt_text(cv, P, x, mid, "", 10, P["text"], key="map", cls=_Num)
                x += fm.measure("00:00") + u(6)
            if ln.get("rank", True):
                x += self._lt_rank(cv, P, x, mid) + u(4)
            self.tk_ov_cv = cv
        if want["helpers"]:
            if x > pad:
                x = sep(x)
            for k in self.bar_chips():
                x += self._lt_chip(cv, P, k, x, mid - u(9), mid + u(9), "micro") + u(4)
            x += u(4)
        if self.bar_buttons_on():
            x = sep(x)
            mw = self._lt_menus_w(cv, P)
            self._lt_menus(w, cv, P, x + mw, mid)
            x += mw + u(6)
        if want["timer"] and cfg.get("clock", True):
            x = sep(x)
            x += self._lt_clock(cv, P, x, mid, anchor="w") + u(8)
        x = sep(x)
        W = x + self._lt_glyphs_w(cv, P) + pad
        self._lt_glyphs(w, cv, P, W - pad, mid)
        return W, H

    # ---------------------------------------------------------------- Panels
    def _lt_hairline_panel(self, w, cv, P, want, spot, piece):
        """Hairline Panel: everything right-aligned, like the game's area info (top right): the time, Map / Maps /
        Avg, where you are and its rank, a thin rule, the switches in two columns, the clock, lock and ⚙."""
        u = self._u
        cfg, ln = self.tracker_cfg(), self.tracker_cfg()["lines"]
        PW = u(240)
        pad = u(8)
        R = PW - pad
        y = pad
        fm = self._lt_fm(cv, P, 9)
        if want["timer"]:
            if ln.get("session", True):
                fb, fp = self._lt_fm(cv, P, 16, True), self._lt_fm(cv, P, 7, True)
                tw = fb.measure("0:00:00")
                ty = y + fb.metrics("linespace") // 2
                tx = R - tw - fp.measure("PAUSED") - 6
                self._lt_time(cv, P, tx, ty, 16)
                d = self._hf(10) + 6
                self._mg_play(cv, P, tx - u(6) - d, ty, anchor="w", size=10)
                y += fb.metrics("linespace") + u(2)
            parts = [(k, s) for k, s in (("map", "Map 00:00"), ("maps", "Maps 000"), ("avg", "Avg 00:00")) if ln.get(k)]
            if parts:
                cy = y + u(8)
                x = R
                for k, sample in reversed(parts):
                    self._lt_text(cv, P, x, cy, "", 9, P["big"], anchor="e", key=k, cls=_Clean)
                    x -= fm.measure(sample) + u(10)
                y += u(17)
            if ln.get("where", True) or ln.get("rank", True):
                cy = y + u(8)
                x = R
                if ln.get("rank", True):
                    x -= self._lt_rank(cv, P, R, cy, anchor="e") + u(6)
                if ln.get("where", True):
                    self._lt_where(cv, P, x, cy, 26, anchor="e")
                y += u(17)
            self.tk_ov_cv = cv
        if want["helpers"]:
            if want["timer"]:
                y += u(4)
                self._lt_rule(cv, P, R - u(150), R, y, strong="r")
                y += u(6)
            y = self._lt_chip_grid(cv, P, pad, R, y, "hairline", right=True, rh=u(17))
        y += u(4)
        fy = y + u(8)
        x = self._lt_glyphs(w, cv, P, R, fy)
        if want["timer"] and cfg.get("clock", True):
            x -= self._lt_clock(cv, P, x, fy) + u(10)
        if self.bar_buttons_on():
            fy += u(18)
            self._lt_menus(w, cv, P, R, fy)
        return PW, fy + u(10)

    def _lt_slate_panel(self, w, cv, P, want, spot, piece):
        """Slate Panel: a SESSION header (clock, lock, ⚙ on the right), the time / Map / Maps / Avg in a 2 x 2 grid,
        where you are and the rank, the switches in two columns (an accent bar on the left when on), the menus."""
        from .merged_page import _Num
        u = self._u
        cfg, ln = self.tracker_cfg(), self.tracker_cfg()["lines"]
        PW = u(250)
        pad = u(10)
        R = PW - pad
        hh = u(24)
        self._lt_text(cv, P, pad, hh // 2, "SESSION" if want["timer"] else "MECHANICS", 8, P["accent"], bold=True)
        x = self._lt_glyphs(w, cv, P, R, hh // 2)
        if want["timer"] and cfg.get("clock", True):
            self._lt_clock(cv, P, x, hh // 2)
        cv.create_line(0, hh, PW, hh, fill=P["line"], tags=("mg",))
        y = hh + u(6)
        colw = (PW - 2 * pad) // 2
        if want["timer"]:
            cells = [k for k in ("session", "map", "maps", "avg") if ln.get(k, k in ("session", "map"))]
            rh = u(24)
            for i, k in enumerate(cells):
                cx, cy = pad + (i % 2) * colw, y + (i // 2) * rh + rh // 2
                if k == "session":
                    cx += self._mg_play(cv, P, cx, cy, anchor="w", size=9) + u(5)
                    self._lt_time(cv, P, cx, cy, 11, num=True)
                    continue
                lab = {"map": "Map", "maps": "Maps", "avg": "Avg"}[k]
                self._lt_text(cv, P, cx, cy, lab, 8, P["muted"])
                lw = self._lt_fm(cv, P, 8).measure(lab) + u(5)
                self._lt_text(cv, P, cx + lw, cy, "", 12 if k == "map" else 10, P["big"], bold=k == "map", key=k,
                              cls=_Num)
            y += ((len(cells) + 1) // 2) * rh + u(2)
            if ln.get("where", True) or ln.get("rank", True):
                cy = y + u(8)
                x = R
                if ln.get("rank", True):
                    x -= self._lt_rank(cv, P, R, cy, anchor="e") + u(6)
                if ln.get("where", True):
                    self._lt_where(cv, P, pad, cy, int((x - pad) / max(1, self._lt_fm(cv, P, 9).measure("n"))))
                y += u(18)
            self.tk_ov_cv = cv
        if want["helpers"]:
            y += u(2)
            cv.create_line(0, y, PW, y, fill=P["line"], tags=("mg",))
            y = self._lt_chip_grid(cv, P, 0, PW, y + 1, "slate", rh=u(24), mark="left")
        if self.bar_buttons_on():
            cv.create_line(0, y, PW, y, fill=P["line"], tags=("mg",))
            self._lt_menus(w, cv, P, pad, y + u(12), anchor="w")
            y += u(24)
        else:
            y += u(4)
        return PW, y

    def _lt_flanks_panel(self, w, cv, P, want, spot, piece):
        """Flanks Panel: the numbers on the left under an accent rule, the switches, clock, lock and ⚙ pushed right
        under another - the bar's two halves stacked."""
        u = self._u
        cfg, ln = self.tracker_cfg(), self.tracker_cfg()["lines"]
        PW = u(230)
        pad = u(6)
        R = PW - pad
        rl = u(130)
        fm = self._lt_fm(cv, P, 9)
        y = pad
        if want["timer"]:
            self._lt_rule(cv, P, pad, pad + rl, y, strong="l")
            y += u(14)
            x = pad
            if ln.get("session", True):
                x += self._mg_play(cv, P, x, y, anchor="w", size=10) + u(6)
                x += self._lt_time(cv, P, x, y, 13, num=True) + u(8)
            if ln.get("map", True):
                self._lt_text(cv, P, x, y, "", 9, P["text"], key="map", cls=_Clean)
            y += u(18)
            if ln.get("where", True) or ln.get("rank", True):
                x = pad
                if ln.get("rank", True):
                    x += self._lt_rank(cv, P, x, y) + u(6)
                if ln.get("where", True):
                    self._lt_where(cv, P, x, y, 26)
                y += u(16)
            x = pad
            for k, sample in (("maps", "Maps 000"), ("avg", "Avg 00:00")):
                if ln.get(k):
                    self._lt_text(cv, P, x, y, "", 9, P["big"], key=k, cls=_Clean)
                    x += fm.measure(sample) + u(10)
            if x > pad:
                y += u(16)
            self.tk_ov_cv = cv
            y += u(4)
        self._lt_rule(cv, P, R - rl, R, y, strong="r")
        y += u(6)
        if want["helpers"]:
            y = self._lt_chip_grid(cv, P, pad, R, y, "flanks", right=True, rh=u(17))
        fy = y + u(9)
        x = self._lt_glyphs(w, cv, P, R, fy)
        if want["timer"] and cfg.get("clock", True):
            self._lt_clock(cv, P, x - u(4), fy)
        if self.bar_buttons_on():
            fy += u(18)
            self._lt_menus(w, cv, P, R, fy)
        return PW, fy + u(10)

    def _lt_micro_panel(self, w, cv, P, want, spot, piece):
        """Micro Panel: a small tile - the time, this map's time and the rank; the switches as lettered squares;
        lock and ⚙ (and the menus) under them."""
        from .merged_page import _Num
        u = self._u
        cfg, ln = self.tracker_cfg(), self.tracker_cfg()["lines"]
        pad = u(8)
        fm = self._lt_fm(cv, P, 10)
        y = pad
        x = pad
        row_w = []
        if want["timer"]:
            cy = y + u(10)
            if ln.get("session", True):
                x += self._mg_play(cv, P, x, cy, anchor="w", size=9) + u(4)
                x += self._lt_time(cv, P, x, cy, 12, num=True) + u(8)
            if ln.get("map", True):
                self._lt_text(cv, P, x, cy, "", 10, P["text"], key="map", cls=_Num)
                x += fm.measure("00:00") + u(6)
            if ln.get("rank", True):
                x += self._lt_rank(cv, P, x, cy) + u(4)
            row_w.append(x)
            y += u(22)
            self.tk_ov_cv = cv
        if want["helpers"]:
            x = pad
            for k in self.bar_chips():
                x += self._lt_chip(cv, P, k, x, y, y + u(18), "micro") + u(4)
            row_w.append(x)
            y += u(24)
        gw = self._lt_glyphs_w(cv, P)
        mw = self._lt_menus_w(cv, P) if self.bar_buttons_on() else 0
        clock = want["timer"] and cfg.get("clock", True)
        cw = self._lt_fm(cv, P, 9).measure("00:00 PM") + u(8) if clock else 0
        row_w.append(pad + mw + cw + gw)
        W = max(row_w) + pad
        fy = y + u(6)
        x = self._lt_glyphs(w, cv, P, W - pad, fy)
        if clock:
            self._lt_clock(cv, P, x, fy)
        if mw:
            self._lt_menus(w, cv, P, pad, fy, anchor="w")
        return W, fy + u(10)
