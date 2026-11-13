"""Light looks for the overlay (2.101.0, from the mockups - feedback: "a lightweight one is needed desperately").

Four styles drawn with plain canvas lines and text - no Pillow artwork, nothing to re-render when the game window
changes size - each as a Bar (resting on the XP bar) and a Panel (a card you place anywhere), in a set of colors:
  hairline  no box: outlined text and one thin accent line, on one row
  slate     a flat box with thin dividers; a switch that's on is underlined (a bar on its left in the Panel)
  flanks    (shown as Split) no box: the numbers beside the life orb, the switches beside the mana orb - the middle stays clear
  micro     the smallest: the times, the rank and the switches as lettered squares (Ritual shows its count, 2/3)
"Classic" is the stone-and-bronze look of before (hudart.py). Settings › Appearance › Overlay: Style, then
Colors ("Exile Gold" is the Bar's own colors; the others are the theme packs'; "Follow the app theme").
The same parts as Classic: the timer and its ⏸ / ▶, the map's time, where you are, its rank (click to rank), Maps,
Avg, the clock, the switches, Notes ▾ / Calc ▾ / Regex ▾ / Vendor ▾, the lock and ⚙ - each with its switch in
Overlay › Options. The goal bar (Focus / Campaign) is drawn in the same style (ovparts.py).

No box (hairline, flanks) needs Windows' see-through color key (-transparentcolor); on other systems they get the
color set's box. GGG ToS: looks only - windows of the app's own; nothing here touches the game."""
import sys
import tkinter as tk
from tkinter import font as tkfont

from .overlaywin import CanvasText, OverlayWindow, _P

from .ovskins import NAMES as _ORN_NAMES, ORNATE, palette as _ornate_palette

STYLES = {"classic": "Classic (stone and bronze)", "hairline": "Hairline", "slate": "Slate", "flanks": "Split",
          "micro": "Micro"}
STYLES.update(_ORN_NAMES)                                    # 2.110.0: Herald, Gilded, Warbanner, Verdant, Gloom
_FM_CACHE = {}                   # 2.112.3: measuring fonts, kept (see _lt_fm)
LIGHT = ("hairline", "slate", "flanks", "micro") + ORNATE
BOXLESS = ("hairline", "flanks")
KEY = "#010101"                    # a box-less look's see-through color (never used for anything that shows)
WARN = "#e0a352"

# id: (name, box, line, text, strong, muted, accent) - each theme pack's own surface_sunken, border, text,
# text_strong, text_muted and accent (themes/*.json); Exile Gold is the Classic Bar's (hudart.palette)
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
    """The color sets keep their own colors in every app theme (like the Classic looks: overlaywin)."""
    from . import themes as _th
    for c in COLORS.values():
        _th.KEEP.update(v.lower() for v in c[1:] if v and _th.is_hex(v))
    _th.KEEP.update({KEY, WARN})
    _th.KEEP.difference_update({"#000000", "#ffffff"})


_keep_colors()


def can_see_through():
    return sys.platform == "win32"


def palette(style, cid, boxed=False):
    """The colors, font and shape of a light look. "theme" takes the app theme's (a light theme's dark text can't
    be read over the game without a box, so the box-less styles use Exile Gold then)."""
    from .overlaywin import theme_palette
    if style in ORNATE:                                      # 2.110.0: its own colors (Colors doesn't apply)
        return _ornate_palette(style)
    c = COLORS.get(cid) or COLORS[DEFAULT_COLORS]
    if cid == "theme":
        b = theme_palette()
        if b.get("light") and style in BOXLESS:
            c = COLORS["exile"]
        else:
            c = ("Follow the app theme", b["field"], b["line"], b["text"], b["big"], b["muted"], b.get("accent", b["head"]))
    _name, box, line, text, strong, muted, acc = c
    boxless = style in BOXLESS and can_see_through() and not boxed   # (windows - Notes, Calc… - always get a box)
    bg = KEY if boxless else box
    return dict(_P, leather=bg if boxless else line, edge=bg if boxless else "#000000", border=0 if boxless else 1,
                bg=bg, band=bg, field=bg, box=box, head=acc, accent=acc, text=text, big=strong, icon=strong, sub=text,
                muted=muted, line=line, on=acc, off=muted, warn=WARN, cell_bg=bg, cell_line=line, rim=line,
                rim_hi=line, rim_lo=line, bg_top=bg, font="Segoe UI", hfont="Segoe UI", on_icon="◆",
                off_icon="◇", halo="#000000" if boxless else None, boxless=boxless, look=style)


class _Clean(CanvasText):
    """Spaces tidied: "Map:  3:12" -> "Map: 3:12" (2.104.1 feedback: the labels keep their colon - Map:, Avg:)."""

    def config(self, **kw):
        if "text" in kw:
            kw["text"] = " ".join(str(kw["text"]).split())
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


def _inert(cv):
    """A preview's canvas: every click, hover and cursor binding on its items taken off (the drawing stays)."""
    try:
        seen = set()
        for it in cv.find_all():
            for t in (it,) + tuple(cv.gettags(it)):
                if t in seen:
                    continue
                seen.add(t)
                for seq in cv.tag_bind(t) or ():
                    cv.tag_unbind(t, seq)
        cv.configure(cursor="")
    except tk.TclError:
        pass


class LightOverlay:
    """Mixed into App (with MergedOverlay, which calls _mg_light_build when a light style is chosen)."""

    # ---------------------------------------------------------------- 2.118.0: the real bar as a preview
    def ov_preview(self, host, style, width=700, scene="#17130f"):
        """Draw the bar of `style` into `host` (a Frame) with the very code that draws it over the game - its palette,
        frame, fonts and parts, sample numbers, at `width` px (a 1440p game's XP bar, scaled) - so Settings ›
        Appearance shows what you'll get (feedback: the old mock-up previews had wrong colors and shapes). The
        Colors you picked apply, as over the game. A see-through style shows `scene` (a dark bit of game) behind it.
        Nothing in it answers clicks. The overlay over the game is left as it was. -> [canvas]"""
        from . import hudart, themes as TH
        from .merged_page import hud_k
        from .overlaywin import OverlayFrame, _seed, theme_palette
        for c in host.winfo_children():
            c.destroy()
        keep = ("tk_ov_lbls", "tk_ov_alerts", "tk_ov_clock", "tk_ov_cv", "tk_ov_map_part", "_play_spots", "mg_P",
                "_hud_k", "_hud_ends", "_play_last", "_play_drawn")
        saved = {k: getattr(self, k) for k in keep if hasattr(self, k)}
        canvases = []
        self._ov_previewing = True
        try:
            scale = width / 1031                                  # (the XP bar is 1031 px wide on a 2560 x 1440 game)
            self._hud_k = hud_k(1440) * scale
            self.tk_ov_lbls, self.tk_ov_alerts, self.tk_ov_clock, self.tk_ov_cv = {}, {}, None, None
            self._play_spots = []
            self.play_glyph = lambda: "⏸"                         # (tracking, in the picture)
            want = {"bar": True, "timer": True, "helpers": False, "notes": False}
            if style == "classic":
                P = hudart.palette(hudart.palette(theme_palette()))    # (as ov_palette, then _mg_hud_build)
            else:
                P = palette(style, self.ov_look_colors())
                if P.get("boxless"):                              # Windows' see-through key: the game shows there
                    P = {k: (scene if v == KEY else v) for k, v in P.items()}
            _seed(TH, P)
            self.mg_P = P
            row = tk.Frame(host, bg=scene)
            row.pack(fill="x")
            panel = self.merged_layout() != "xpbar"          # 2.124.0: the layout picked (the Panel too)
            pieces = ["left", "right"] if style == "flanks" and not panel else ["all"]
            from .merged_page import HUD_SPOTS
            spot_h = max(26, int(HUD_SPOTS["xpbar"][0][3] * 1440 * scale))
            if panel:
                self._hud_k = hud_k(1440) * 0.8
            for piece in pieces:
                if panel and style == "classic":
                    P = hudart.panel_palette(theme_palette())
                    _seed(TH, P)
                    self.mg_P = P
                f = OverlayFrame(row, P)
                cv = f.canvas_body()
                if panel and style == "classic":
                    W, H = self._mg_classic_panel(f, cv, P, want)
                elif panel:
                    kind = "ornate" if style in ORNATE else style
                    W, H = getattr(self, f"_lt_{kind}_panel")(f, cv, P, want, (0, 0, width, spot_h), piece)
                elif style == "classic":
                    W, H = width - 2, spot_h - 2
                    self._hud_ends = ("crimson", "sapphire")
                    self._hud_row(f, cv, P, want, W, H)
                else:
                    kind = "ornate" if style in ORNATE else style
                    W, H = getattr(self, f"_lt_{kind}_bar")(f, cv, P, want, (0, 0, width, spot_h), piece)
                cv.configure(width=W, height=H)
                side = "right" if piece == "right" else "left"
                f.pack(side=side, anchor="s", padx=(max(0, (width - W) // 2) if style == "micro" and not panel else 0, 0))
                canvases.append(cv)
            sample = {"session": "1:24:07", "map": "Map: 3:12", "where": "Bluff", "maps": "Maps: 6",
                      "avg": "Avg: 6:01", "rank": "★ A",
                      # 2.139.0 Map First
                      "a8_chip": "● IN MAP", "a8_label": "THIS MAP · ★ A", "a8_place": "Bluff", "a8_timer": "3:12",
                      "profit": "+1.2 div"}
            for k, lab in self.tk_ov_lbls.items():
                try:
                    lab.config(text=sample.get(k, ""))
                except tk.TclError:
                    pass
            if self.tk_ov_clock is not None:
                try:
                    self.tk_ov_clock.config(text="9:41 PM")
                except tk.TclError:
                    pass
            for cv in canvases:
                _inert(cv)
        finally:
            self._ov_previewing = False
            self.__dict__.pop("play_glyph", None)
            for k in keep:
                if k in saved:
                    setattr(self, k, saved[k])
                else:
                    self.__dict__.pop(k, None)
        return canvases

    # ---------------------------------------------------------------- settings
    def ov_look(self):
        v = self.tracker_cfg().get("look", "classic")
        return v if v in STYLES else "classic"

    def ov_look_colors(self):
        """2.111.0: no Colors picker any more - every light style uses its default set (Exile Gold)."""
        return DEFAULT_COLORS

    def ov_light(self):
        return self.ov_look() in LIGHT

    def ov_palette(self):
        """2.109.0: the one look of everything over the game - the bar's Style, Colors and Layout. Notes, Calc,
        Regex favorites, Rates, the goal bar and every card take it (they used the app theme or the Classic colors
        before, so none matched)."""
        from . import hudart, themes as TH
        from .overlaywin import theme_palette, _seed
        if self.ov_light():
            P = palette(self.ov_look(), self.ov_look_colors(), boxed=True)
        else:
            base = theme_palette()
            P = hudart.palette(base) if self.merged_layout() == "xpbar" else hudart.panel_palette(base)
        _seed(TH, P)
        return P

    def ov_look_set(self, style=None, colors=None):
        """Settings › Appearance › Overlay: Style / Colors picked - the overlay is built again."""
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
        """A font to measure with - one per family / size / weight for the whole run (2.112.3: every chip and
        label made a new one each time the overlay was built, and Windows makes fonts slowly)."""
        key = (family or P["font"], self._hf(size), bool(bold))
        cache = _FM_CACHE.get(key)
        if cache is None:
            cache = _FM_CACHE[key] = tkfont.Font(root=cv.winfo_toplevel().nametowidget("."), family=key[0],
                                                 size=key[1], weight="bold" if bold else "normal")
        return cache

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
        box-less look gets a plain line (a fade would end in the see-through color's black, not the game)."""
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
        """The lock and ⚙ (Quick settings), right to left from x. -> x left of them."""
        locked = bool(self.tracker_cfg().get("mlocked"))
        for txt, cmd, tag in (("⚙", None, "mg_cog"),
                              ("🔒" if locked else "🔓", lambda: w._toggle_lock(), "mg_lock")):
            it = cv.create_text(x, y, text=txt, anchor="e", fill=P["muted"],
                                font=("Segoe UI Symbol", self._hf(9)), tags=("mg", tag))
            CanvasText(cv, it, P["bg"], halo=P.get("halo"))
            if tag == "mg_cog":                          # 2.119.0: either click = Quick settings over the game
                for b in ("<Button-1>", "<Button-3>"):   # (its All settings… opens Overlay ↳ Overlay Settings in the app)
                    cv.tag_bind(tag, b, lambda e: self.ov_quick_toggle(e))
            else:
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

    def _lt_menus(self, w, cv, P, x, y, anchor="e", right=None, step=0):
        """Notes ▾ / Calc ▾ / Regex ▾ / Vendor ▾ (MergedOverlay draws them). -> the far edge."""
        x = self._mg_bar_buttons(w, cv, P, x, y, anchor=anchor, right=right, step=step)
        self._lt_halo_tags(cv, P, ("mg_start", "mg_notes", "mg_calc", "mg_regex", "mg_rates", "mg_vendor"))
        return x

    def _lt_menus_w(self, cv, P):
        start = (self._lt_fm(cv, P, 9, True).measure(self.START_TEXT) + self._hf(9) + 24) if self.start_on_bar() else 0
        return start + self.mg_tools_w(cv, P) + self._u(6)     # 2.139.0: icons

    def _lt_time(self, cv, P, x, y, size, num=True):
        """The session time (bold). -> the width kept for it. 2.119.0 (UX pass, feedback: long map names were cut):
        only the time's own width - not tracking shows --:--, paused dims it (the ▶ beside it says so); there was
        room kept for a PAUSED tag and the words "not tracking"."""
        t = self._lt_text(cv, P, x, y, "", size, P["big"], bold=True, key="session", cls=self._time_cls())
        t.num, t.dim = True, (P["big"], P["muted"])
        return self._lt_fm(cv, P, size, True).measure("0:00:00") + 6

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
                    pos[slot] = [int(nx), int(ny) + (getattr(self, "_gb_h", 0) if slot == 0 else 0)]   # (under the lines)
                    rr = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
                    cfg.setdefault("lt_res", {})[style] = [int(rr[2]), int(rr[3])]
                else:
                    cfg.update(mx=nx, my=ny + getattr(self, "_gb_h", 0))
                self.tracker_save()
            dx, dy = self.ov_panel_xy()                      # 2.130.0: its own place (Quick settings › Place)
            px, py = (cfg.get("mx", dx), cfg.get("my", dy)) if not bar else (0, 0)
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
            kind = "ornate" if style in ORNATE else style
            draw = getattr(self, f"_lt_{kind}_{'bar' if bar else 'panel'}")
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
            elif "mx" not in cfg and self.ov_spot() == "right":    # (the Panel on the right: its width is known)
                rx, ry = self.ov_panel_xy(W)
                w.geometry(f"+{int(rx)}+{int(ry)}")
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

    # ---------------------------------------------------------------- Bars
    def _lt_row(self, w, cv, P, want, W, style):
        """Hairline / Slate bar, as wide as the XP bar, one row: ⏸ time | ★ rank  Map 3:12  Arcane Isle | Maps | Avg
        ... menus | clock, lock, ⚙. (2.118.0: no helper switches - the row never needs a second line.)"""
        from .merged_page import _MapPart, _PartOf
        u = self._u
        slate = style == "slate" or style in ORNATE
        cfg, ln = self.tracker_cfg(), self.ov_lines()
        fm = self._lt_fm(cv, P, 10)
        pad, sw = u(10), u(20)                              # (sw: a separator's slot)
        menus_w = self._lt_menus_w(cv, P) if self.bar_buttons_on() else 0
        clock = want["timer"] and cfg.get("clock", True)
        widths = {"maps": fm.measure("Maps 000") + u(4), "avg": fm.measure("Avg 00:00") + u(4)}
        fixed = [k for k in ("maps", "avg") if ln.get(k)] if want["timer"] else []

        def sep(x, y0, y1, mid):
            if slate:
                cv.create_line(x, y0, x, y1, fill=P["line"], tags=("mg",))
            else:
                self._lt_text(cv, P, x, mid, "·", 10, P["muted"], anchor="center")

        H = u(34)                                           # 2.139.0: a label over each value (2.139.1: 40 -> 34)
        r2 = (u(5), H - (u(5) if slate else u(7)))
        m2 = (r2[0] + r2[1]) // 2
        # ---- the right end: lock, ⚙, the clock, the menus
        x = self._lt_glyphs(w, cv, P, W - pad, m2)
        if clock:
            x -= self._lt_clock(cv, P, x, m2) + u(4)
            sep(x - sw // 2, *r2, m2)
            x -= sw
        if menus_w:
            x = self._lt_menus(w, cv, P, x, m2) + 12 - u(4)
            if want["timer"]:
                sep(x - sw // 2, *r2, m2)
                x -= sw
        right = x
        # 2.139.0 Map First: chip | the map part | SESSION | LAST MAP'S PROFIT (ova8)
        self.a8_bar(w, cv, P, want, pad, right, m2, lambda sx: sep(sx, *r2, m2))
        if not slate:                                       # the hairline under the (bottom) row
            self._lt_rule(cv, P, pad, W - pad, H - u(3), strong="c")
        return W, H

    def _lt_hairline_bar(self, w, cv, P, want, spot, piece):
        return self._lt_row(w, cv, P, want, spot[2], "hairline")

    def _lt_slate_bar(self, w, cv, P, want, spot, piece):
        return self._lt_row(w, cv, P, want, spot[2], "slate")

    def _lt_ornate_bar(self, w, cv, P, want, spot, piece):
        """2.110.0: Herald, Gilded, Warbanner, Verdant, Gloom - the Slate row in the skin's colors, fonts and tabs
        (the frame, its inner line and the corner marks come from the window: overlaywin)."""
        return self._lt_row(w, cv, P, want, spot[2], P["skin"])

    def _lt_flanks_bar(self, w, cv, P, want, spot, piece):
        """Flanks: "left" = the numbers (right of the life orb), "right" = the switches, menus, clock, lock and ⚙
        (left of the mana orb). Each piece is as small as its content."""
        u = self._u
        cfg, ln = self.tracker_cfg(), self.ov_lines()
        pad = u(6)
        rl = u(150)                                          # the accent rule's length
        if piece == "left":                                 # 2.139.0 Map First (ova8), as wide as it needs
            H = u(38)
            mid = u(5) + (H - u(5)) // 2
            x = self.a8_bar(w, cv, P, want, pad, None, mid,
                            lambda sx: cv.create_line(sx, mid - u(13), sx, mid + u(13), fill=P["line"], tags=("mg",)),
                            map_w=u(190))
            W = max(x, rl) + pad
            self._lt_rule(cv, P, pad, pad + rl, u(4), strong="l")
            self.tk_ov_cv = cv
            return W, H
        # right
        y = u(4)
        rows_w = []
        gw = self._lt_glyphs_w(cv, P)
        clock = want["timer"] and cfg.get("clock", True)
        foot_w = gw + (self._lt_fm(cv, P, 9).measure("00:00 PM") + u(10) if clock else 0)
        menus_w = self._lt_menus_w(cv, P) if self.bar_buttons_on() else 0
        rows_w += [foot_w + (menus_w + u(6) if menus_w and foot_w + menus_w < u(320) else 0), rl]
        W = max(rows_w) + 2 * pad
        R = W - pad
        self._lt_rule(cv, P, R - rl, R, y, strong="r")
        y += u(6)
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
        """Micro: chip | the map part | SESSION | profit | menus · clock · lock ⚙ - only as wide as that (2.139.0 Map
        First, ova8)."""
        u = self._u
        cfg = self.tracker_cfg()
        H = u(34)
        mid = H // 2
        pad = u(8)

        def sep(x):
            cv.create_line(x, mid - u(12), x, mid + u(12), fill=P["line"], tags=("mg",))
            return x + u(10)
        x = self.a8_bar(w, cv, P, want, pad, None, mid, sep, map_w=u(160)) + u(10) if want["timer"] else pad
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
        """Hairline Panel: the Map First panel (2.139.0) in Hairline's colors."""
        return self._lt_slate_panel(w, cv, P, want, spot, piece)      # 2.139.0: Map First in every style

    def _lt_ornate_panel(self, w, cv, P, want, spot, piece):
        return self._lt_slate_panel(w, cv, P, want, spot, piece, style=P["skin"])

    def _lt_slate_panel(self, w, cv, P, want, spot, piece, style="slate"):
        """2.139.0 Map First (ova8): the chip and the clock, the map part, SESSION | LAST MAP'S PROFIT, the tools -
        the Panel of every style (Classic draws its stone round it)."""
        PW = self._u(290)
        return PW, self.a8_panel(w, cv, P, want, PW)

    def _lt_flanks_panel(self, w, cv, P, want, spot, piece):
        """Split Panel: the Map First panel (2.139.0) in Split's colors."""
        return self._lt_slate_panel(w, cv, P, want, spot, piece)      # 2.139.0: Map First in every style

    def _lt_micro_panel(self, w, cv, P, want, spot, piece):
        """Micro Panel: the Map First panel (2.139.0) in Micro's colors."""
        return self._lt_slate_panel(w, cv, P, want, spot, piece)      # 2.139.0: Map First in every style

