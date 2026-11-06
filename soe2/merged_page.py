"""One overlay (2.55.0, from the mockups): the Session timer, the Mechanic Helper and Notes in ONE window
over the game. 2.67.0: two looks, both the game's own - the Panel (a card like the game's vendor windows: header
plate, stats in a grid, the switches) and the Game bar (on the XP bar, in the HUD's own frame). 2.67.0: the four
switches are in both whenever the timer shows. Notes opens as its own window from Notes ▾.

Which parts show: the timer while a session runs (2.70.1: each part - the timer, each number, where you are, the clock,
Notes, the switches - has its switch in Overlay › Options › On the overlay), the switches while their switch is on. One window holds whatever is on; when nothing is, it's gone. ToS: it only shows
things - the same reading as the separate windows."""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from .overlaywin import CanvasText, OverlayWindow, pal

# 2.66.0: one look (the app's theme); the layout says the shape - Minimal moved here from the old Style list
# 2.67.0 (feedback: "get rid of all of the other options"): the Panel in the game's vendor-window style (the
# Treasurer's ledger) and the Game bar on the XP bar. Strip, Minimal and beside-the-orbs are gone (-> Panel).
LAYOUTS = {"panel": "Panel", "xpbar": "Game bar"}     # 2.67.0: beside the orbs is gone; 2.74.0: "Game bar"
HUD = ("xpbar",)                 # 2.65.0: fitted to the game's own bottom bar, in its look

# Where the game's bottom bar leaves room, as parts of the game window's height (PoE2 at 16:9, UI scale 100 %;
# the orbs' panels are anchored to the left and right edges, the XP bar runs between them). (x0, x1, bottom, h)
#   x0 / x1 >= 0: from the left edge, < 0: from the right edge; bottom: up from the bottom edge.
HUD_SPOTS = {"xpbar": [(0.531, -0.531, 0.0205, 0.056)]}   # 2.79.1: as wide as the XP bar (measured at 1440p), over it   # 2.67.2: two rows (switches on top); 2.74.0: between 2.73.4 and 2.73.5
# 2.89.2: full words on the bar, never short forms; the Remnant switch reads "Expedition" (what players call it)
NAMES = {"breach": "Breach", "delirium": "Delirium", "ritual": "Ritual", "remnant": "Expedition", "focus": "Focus",
         "campaign": "Campaign", "desecrate": "Desecration"}
SHORT = NAMES                     # (the old short forms - Brch, Deli ... - are gone)


CHIPS = ("breach", "delirium", "ritual", "remnant", "focus", "campaign")   # 2.90.0: the switches the bar can show


def chip_name(k):
    return NAMES.get(k, k.title())


def hud_k(game_h):
    """2.78.3 (feedback: "make sure the overlay is detecting a person's resolution and scaling it to fit"): how much
    bigger than at 1080 px the overlay is drawn - the game window's height / 1080 (720p 0.67, 1440p 1.33, 4K 2.0)."""
    return max(0.6, min(3.0, (game_h or 1080) / 1080))


def set_click_through(w, on):
    """Windows: mouse clicks pass through the window to whatever is under it (WS_EX_TRANSPARENT on a layered window).
    GGG ToS: a window style of the app's own window - nothing is sent to the game."""
    import sys
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        u = ctypes.windll.user32
        w.update_idletasks()
        hwnd = u.GetParent(w.winfo_id()) or w.winfo_id()
        ex = u.GetWindowLongW(hwnd, -20)
        ex = (ex | 0x20 | 0x80000) if on else (ex & ~0x20)
        u.SetWindowLongW(hwnd, -20, ex)
        return True
    except Exception:
        return False


class _Short(CanvasText):
    """Minimal: the helper's short name (Ritual's live count stays: 2/3)."""
    key = ""

    def config(self, **kw):
        if "text" in kw:
            t = kw["text"]
            kw["text"] = t if "/" in t else SHORT.get(self.key, t)        # 2.89.2: full words, live count too
        super().config(**kw)
    configure = config


class _Trunc(CanvasText):
    """Strip: a long area name is cut so it never runs into Maps / Avg."""
    limit = 16

    def config(self, **kw):
        if "text" in kw and len(kw["text"]) > self.limit:
            kw["text"] = kw["text"][:self.limit - 1].rstrip() + "…"
        super().config(**kw)
    configure = config


class _MapPart(CanvasText):
    """2.90.0: "Map 3:12  Arcane Isle" - the map's time and the area as one text, fitted whole into its part."""
    width, font, show, muted = 200, ("Segoe UI", 10), (True, True, True), None

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.parts = {"map": "", "where": "", "rank": ""}

    def set_part(self, key, text):
        self.parts[key] = " ".join(str(text or "").split())
        m = self.parts["map"] if self.show[0] else ""
        wh = self.parts["where"] if self.show[1] else ""
        rk = self.parts["rank"] if self.show[2] else ""
        text = "  ".join(t for t in (m, wh, rk) if t and t != "-")
        fam, size = self.font[0], int(self.font[1])
        rest = tuple(self.font[2:])
        try:
            while size > 8 and tkfont.Font(root=self.canvas, family=fam, size=size, weight=rest[0] if rest else "normal") \
                    .measure(text) > self.width:
                size -= 1
            fnt = tkfont.Font(root=self.canvas, family=fam, size=size, weight=rest[0] if rest else "normal")
            while len(text) > 4 and fnt.measure(text) > self.width:     # (only a very narrow bar cuts it)
                text = text[:-2].rstrip() + "…"
            self.canvas.itemconfigure(self.item, font=(fam, size) + rest)
            for h, _dx, _dy in self.halos:
                self.canvas.itemconfigure(h, font=(fam, size) + rest)
        except tk.TclError:
            pass
        CanvasText.config(self, text=text)
        self.shown_size = size


class _PartOf:
    """One of _MapPart's two parts, answering like a label (config(text=...), cget("text"))."""

    def __init__(self, part, key):
        self.part, self.key = part, key

    @property
    def item(self):
        return self.part.item

    @property
    def canvas(self):
        return self.part.canvas

    def config(self, **kw):
        if "text" in kw:
            self.part.set_part(self.key, kw["text"])
        if "fg" in kw and self.key == "map":
            CanvasText.config(self.part, fg=kw["fg"])
    configure = config

    def cget(self, key):
        return self.part.parts.get(self.key, "") if key == "text" else self.part.cget(key)


class _Num(CanvasText):
    """The Panel's numbers: the value only - its icon says what it is ("Maps 7" -> "7", "Avg 6:01" -> "6:01")."""

    def config(self, **kw):
        if "text" in kw:
            import re
            m = re.match(r"^\s*(?:Map:?|Maps:?|Avg\.?:?|★)\s*(.*)$", str(kw["text"]))
            if m:
                kw["text"] = m.group(1)
            elif "tracking" in str(kw["text"]):              # (no session running)
                kw["text"] = "--:--"
        super().config(**kw)
    configure = config


class _Time(CanvasText):
    """2.69.2: the session time. "(paused)" is not part of the big number any more (it ran into Map / the next
    cell): a small muted PAUSED tag sits beside it (XP bar) or under it (Panel)."""
    tag = None          # (canvas item, "right" / "below")
    num = False         # the Panel: "not tracking" -> --:--

    def config(self, **kw):
        if "text" in kw:
            t = str(kw["text"])
            paused = "(paused)" in t
            t = t.replace("(paused)", "").rstrip()
            if self.num and "tracking" in t:
                t = "--:--"
            kw["text"] = t
            super().config(**kw)
            if self.tag:
                item, where = self.tag
                cv = self.canvas
                try:
                    cv.itemconfigure(item, text="PAUSED" if paused else "")
                    bb = cv.bbox(self.item)
                    if bb:
                        if where == "right":
                            cv.coords(item, bb[2] + 6, (bb[1] + bb[3]) // 2)
                        else:
                            cv.coords(item, bb[0], bb[3] + 1)
                except Exception:
                    pass
            return
        super().config(**kw)
    configure = config


class _Sub(_Trunc):
    """The Panel's red subtitle: where you are, or the league when the game hasn't said yet."""
    limit = 30

    def config(self, **kw):
        if "text" in kw and not str(kw["text"]).strip():
            from .config import SETTINGS
            kw["text"] = f"League: {SETTINGS.get('league') or '-'}"
        if "text" in kw:
            kw["text"] = str(kw["text"]).upper()             # (small caps, like the game's subtitles)
        super().config(**kw)
    configure = config


class MergedOverlay:
    """Mixed into App (with TrackerPage, which builds the separate windows)."""

    # ---------------------------------------------------------------- settings
    def merged_on(self):
        """2.59.0: always one window - the separate windows of 2.54 are gone."""
        return True

    def merged_layout(self):
        v = self.tracker_cfg().get("layout", "xpbar")      # 2.74.0: the Game bar by default
        return v if v in LAYOUTS else "panel"            # (2.67.0: an old Strip / Minimal is the Panel now)

    def merged_embeds_notes(self):
        """2.67.0: the note always opens as its own window, from the overlay's Notes ▾."""
        return False

    def hud_spots(self, layout=None):
        """2.65.0: the Game bar windows' places -> [(x, y, w, h)]: fitted to the game window (or the main screen),
        or where you dragged them (Settings › Appearance › Fit to the game puts them back)."""
        layout = layout or self.merged_layout()
        from .alerts_page import game_rect
        r = game_rect()
        if r is None:
            r = (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        gx, gy, gw, gh = r
        self._hud_k = hud_k(gh)                            # 2.78.3: no 0.8-1.6 cap - 4K and 720p fit too
        cfg = self.tracker_cfg()
        saved = (cfg.get("hud_pos") or {}).get(layout) or []
        if saved and (cfg.get("hud_res") or {}).get(layout) != [int(gw), int(gh)]:   # 2.79.1: another resolution -
            saved = []                                                             # fitted again, bottom centre
        out = []
        for i, (a, b, bot, hh) in enumerate(HUD_SPOTS[layout]):
            x0 = gx + (a * gh if a >= 0 else gw + a * gh)
            x1 = gx + (b * gh if b >= 0 else gw + b * gh)
            h = max(26, int(hh * gh))
            w = max(160, int(x1 - x0))
            x, y = int(x0), int(gy + gh - bot * gh - h)
            if i < len(saved) and isinstance(saved[i], (list, tuple)) and len(saved[i]) == 2:
                x, y = int(saved[i][0]), int(saved[i][1])
            out.append((x, y, w, h))
        return out

    def merged_wants(self):
        oc = self.overlay.cfg
        if not self.ov_enabled():                         # 2.92.2: the master switch is off - nothing over the game
            return {"timer": False, "helpers": False, "notes": False}
        return {"timer": bool(getattr(self, "mg_timer", False)),
                "helpers": bool(self.bar_chips()),       # 2.70.1: its own switch; 2.73.0: or the Focus switch
                "notes": self.merged_embeds_notes() and bool(oc.get("notes_enabled")) and bool(oc.get("notes_visible"))}

    # 2.73.0: what sits on the overlay's bar - each feature has an "on the bar" switch (Overlay › Options)
    def bar_cfg(self):
        b = self.tracker_cfg().setdefault("bar", {})
        # 2.90.0: each helper's switch can leave the bar on its own; a new install starts with none (it asks which)
        if getattr(self, "_fresh_install", False) and not b.get("chips_set"):
            for k in CHIPS:
                b.setdefault(k, False)
        b.setdefault("focus", True)
        b.setdefault("notes", True)
        b.setdefault("calc", True)                       # 2.74.0: Calc ▾ (the calculator over the game)
        b.setdefault("campaign", True)                   # 2.77.0: the Campaign switch, and Vendor ▾ in town
        b.setdefault("vendor", True)
        b.setdefault("regex", True)                      # 2.92.2: Regex ▾ (your favorites)
        b.pop("desecrate", None)                         # 2.81.1 (feedback): no Desecration switch on the bar
        for k in self.HELPERS:
            b.setdefault(k, True)
        b["chips_set"] = True
        return b

    def bar_chips(self):
        """The switches on the bar: the Mechanic Helper's four (their switch on), then Focus and Campaign (their own)."""
        b = self.bar_cfg()
        chips = [k for k in self.HELPERS if b.get(k, True)] if self.tracker_cfg().get("alerts_bar", True) else []
        if b.get("focus"):
            chips.append("focus")
        if self.bar_cfg().get("campaign"):             # 2.88.3 (feedback): always on
            chips.append("campaign")                     # the bar while its switch is on, campaign or not
        return chips

    def notes_on_bar(self):
        return bool(self.overlay.cfg.get("notes_enabled")) and bool(self.bar_cfg().get("notes", True))

    def _rank_click(self, cv, rt):
        """2.76.0: a click on the map's rank ranks the map you're in."""
        try:
            cv.tag_bind(rt.item, "<Button-1>", lambda e: self.maprank_click())
            cv.tag_bind(rt.item, "<Enter>", lambda e: cv.configure(cursor="hand2"))
            cv.tag_bind(rt.item, "<Leave>", lambda e: cv.configure(cursor=""))
        except (AttributeError, tk.TclError):
            pass

    def _focus_click(self, cv, ft):
        """2.73.4: a click on the focus line opens Game Plan (where its goal is set)."""
        try:
            cv.tag_bind(ft.item, "<Button-1>", lambda e: self.ov_intro_setup("focus"))
            cv.tag_bind(ft.item, "<Enter>", lambda e: cv.configure(cursor="hand2"))
            cv.tag_bind(ft.item, "<Leave>", lambda e: cv.configure(cursor=""))
        except (AttributeError, tk.TclError):
            pass

    def focus_line(self):
        """-> (text, progress 0-1 or None) for the overlay's focus line, or ("", None)."""
        from . import focus as F
        try:
            return F.line_text(self.gp_worth() if hasattr(self, "gp_worth") else None)
        except Exception:
            return "", None

    def merged_set(self, layout=None):
        """Settings › Appearance: the style or the Layout changed - rebuild the overlay (and a dropped-down note)."""
        cfg = self.tracker_cfg()
        timer = getattr(self, "mg_timer", False)
        notes_on = bool(self.overlay.cfg.get("notes_enabled")) and bool(self.overlay.cfg.get("notes_visible"))
        self.merged_destroy()
        self.tracker_helpers_destroy()
        if self.overlay.notes is not None:
            try:
                self.overlay._store_geometry()
                self.overlay.notes.destroy()
            except tk.TclError:
                pass
            self.overlay.notes = None
        if layout in LAYOUTS:
            if layout != cfg.get("layout"):                 # 2.66.0: a Game bar layout picked again starts fitted
                (cfg.get("hud_pos") or {}).pop(layout, None)
                cfg.pop("lt_pos", None)                      # 2.101.0: the light looks' bars too
            cfg["layout"] = layout
        self.tracker_save()
        self.mg_timer = timer
        self.merged_build()
        if notes_on and not self.merged_embeds_notes():
            self.overlay.show_notes()
        if getattr(self, "ovr_win", None) is not None:      # 2.91.0: the rates window takes the new look too
            self.ovr_build()

    # ---------------------------------------------------------------- the window
    def merged_destroy(self):
        self.goalbar_destroy()                                        # 2.76.0
        w2, self.mg_win2 = getattr(self, "mg_win2", None), None      # 2.65.0: the second Game bar half
        if w2 is not None:
            try:
                w2.destroy()
            except tk.TclError:
                pass
        w, self.mg_win = getattr(self, "mg_win", None), None
        if w is None:
            return
        if getattr(self, "mg_notes_in", False):
            self.overlay._keep_text()
            self.overlay.notes_text = None
            self.overlay.notes_tabbar = None
        self.mg_notes_in = False
        try:
            if w.winfo_ismapped() and w.winfo_width() > 1:
                cfg = self.tracker_cfg()
                cfg.update(mx=w.winfo_x(), my=w.winfo_y())
                if w.winfo_height() > 1 and getattr(self, "mg_built", {}).get("notes"):
                    cfg.update(mw=w.winfo_width(), mh=w.winfo_height())
            w.destroy()
        except tk.TclError:
            pass
        if getattr(self, "tk_overlay", None) is w:
            self.tk_overlay = None
        self.tk_ov_lbls, self.tk_ov_alerts, self.tk_ov_clock, self.tk_ov_cv = {}, {}, None, None

    def merged_build(self):
        """(Re)build the one window from what's on. -> the window, or None when nothing is on. 2.74.0: then
        click-through, as the lock says."""
        w = self._merged_build()
        try:
            self.goalbar_build()                             # 2.76.0: League Focus (and the campaign) on its own bar
        except Exception:
            self.log_error("the goal bar")
        self.overlay_click_through()
        return w

    def click_through_on(self):
        """Settings › Appearance › Overlay settings › Click-through: clicks go through the overlay's bar to the game.
        2.74.3 (feedback: "an isolated toggle that isn't tied to being locked"): its own switch, off by default."""
        return bool(self.tracker_cfg().get("click_through", False))

    def overlay_hide_capture(self):
        """2.85.2 (feedback: "Ritual alerts aren't working, maybe because the overlay is in the position of where the
        ritual (x/3) counter is"): the bar is left out of screen captures, so the Ritual / Delirium watchers see the
        game's counters under it. Its own switch (Overlay ↳ Settings › Behaviour), on by default; off = screenshots
        and streams show the bar."""
        cfg = self.tracker_cfg()
        if not cfg.get("hidecap_2891"):
            # 2.89.1 (feedback): off for everyone, once - the Ritual /
            # Delirium watchers ran all the time for anyone who had them on, so the bar was never in a screenshot.
            # Turn it on again only if a watcher can't read a counter the bar covers.
            cfg["hide_capture"], cfg["hidecap_2891"] = False, True
        if not cfg.get("hide_capture", False):
            return False
        # 2.88.3 (feedback): only while the Ritual or
        # Delirium watcher is running - they're the ones that need to see under the bar. Otherwise screenshots show it.
        from .utilities import DELIRIUM, RITUAL
        try:
            return bool(RITUAL.running() or DELIRIUM.running())
        except Exception:
            return True

    def overlay_click_through(self):
        """The overlay's bar windows (not Notes or the calculator - you type in those)."""
        from .remnant_page import capture_affinity
        on, hide = self.click_through_on(), self.overlay_hide_capture()
        for w in (getattr(self, "mg_win", None), getattr(self, "mg_win2", None), getattr(self, "gb_win", None)):
            if w is None:
                continue
            w.click_through = on
            set_click_through(w, on)
            capture_affinity(w, hide)
        self._cap_hidden = hide

    def overlay_capture_sync(self):
        """2.88.3: a watcher started or stopped - put the bar in / out of captures to match."""
        if self.overlay_hide_capture() != getattr(self, "_cap_hidden", None):
            self.overlay_click_through()

    def _merged_build(self):
        cfg = self.tracker_cfg()
        self.merged_destroy()
        want = self.merged_wants()
        self.mg_built = dict(want)
        if not any(want.values()):
            return None
        if self.ov_light():                                 # 2.101.0: Hairline, Slate, Flanks or Micro (ovlight.py)
            return self._mg_light_build(want)
        if self.merged_layout() in HUD:                     # 2.65.0
            return self._mg_hud_build(want)
        from . import hudart, themes as TH
        from .overlaywin import _seed
        P = hudart.card_palette(pal())                      # 2.67.0: the game's vendor-window look, every theme
        _seed(TH, P)
        self.mg_P = P
        self.hud_spots("xpbar")                             # (sizes follow the game window's height)
        x, y = cfg.get("mx", cfg.get("x", 60)), cfg.get("my", cfg.get("y", 260))

        def moved(nx, ny, _ww, _hh):
            cfg.update(mx=nx, my=ny)
            self.tracker_save()
            self.goalbar_follow()
        w = OverlayWindow(self.root, "Session", "⏱", (x, y, None, None), opacity=int(cfg.get("opacity", 225)),
                          locked=bool(cfg.get("mlocked")), min_size=(120, 30), on_close=self.merged_close,
                          on_lock=lambda on: self.overlay_lock(on), on_moved=moved, follow_game=True,
                          no_activate=True, resizable=False, titlebar=False, palette=P)
        w.withdraw()
        self.mg_win = w
        cv = w.canvas_body()
        self.tk_ov_cv = cv
        self.tk_ov_lbls, self.tk_ov_alerts, self.tk_ov_clock = {}, {}, None
        if not cfg.get("mlocked"):
            w.draggable(cv)
        self._mg_card(w, cv, P, want)
        self.tk_overlay = w if want["timer"] else None
        self.tk_helpers = None
        self.tracker_overlay_draw(self.tracker_numbers())
        self.tracker_helpers_paint()
        if getattr(self, "mg_hidden", False):               # hidden with F6: built, kept out of sight
            w.hide()
            return w
        w.show()
        self._mg_on_screen(w)
        return w

    def overlay_hide_toggle(self):
        """2.59.0: F6 (Settings › Hotkeys) hides the whole overlay - timer, switches, Notes - and shows it
        again, as it was. Nothing is switched off; it's only out of sight."""
        self.mg_hidden = not getattr(self, "mg_hidden", False)
        w = getattr(self, "mg_win", None)
        note = self.overlay.notes if getattr(self.overlay, "notes", None) is not None else None
        for win in (w, getattr(self, "mg_win2", None), note, getattr(self, "gb_win", None)):
            if win is None:
                continue
            try:
                win.hide() if self.mg_hidden else win.show()
            except tk.TclError:
                pass
        if not self.mg_hidden and w is not None and self.merged_layout() not in HUD:
            self._mg_on_screen(w)
        return self.mg_hidden

    def _mg_on_screen(self, w):
        """2.56.1 (feedback: a locked strip past the screen's edge couldn't be reached): always all on the screen it
        is on - moved in, and a strip wider than the screen made narrower (never under its minimum)."""
        from .style import monitor_rect
        cfg = self.tracker_cfg()
        try:
            w.update_idletasks()
            x, y = w.winfo_x(), w.winfo_y()
            ww, hh = max(w.winfo_width(), w.winfo_reqwidth()), max(w.winfo_height(), w.winfo_reqheight())
            l_, t, r, b = monitor_rect(self.root, x + 10, y + 10, full=True)
        except Exception:
            return
        nx, ny = max(l_, min(x, r - ww)), max(t, min(y, b - hh))
        if (nx, ny) != (x, y):
            w.geometry(f"+{nx}+{ny}")
            cfg.update(mx=nx, my=ny)
            self.tracker_save()

    def merged_close(self):
        """× on the one window: everything in it goes (the timer, the switches' bar, the note) - each comes back from
        its own place (the next session, Overlay › Options › On the overlay)."""
        cfg = self.tracker_cfg()
        cfg["overlay"] = False                     # (2.96.1: the helpers' switches stay as they are)
        self.mg_timer = False
        if self.overlay.cfg.get("notes_visible"):
            self.overlay.cfg["notes_visible"] = False
            self.overlay.save_settings()
        self.tracker_save()
        self.merged_destroy()
        self._say("Overlay closed. The numbers come back with your next session; the Mechanic Helper switches with "
                  "their switch in Overlay › Options › On the overlay.", 8)

    # ---------------------------------------------------------------- pieces
    def _mg_halo(self, P):
        return P.get("halo") if (P.get("texture") or P.get("boxless")) else None     # 2.101.0: box-less looks

    def _hud_map_part(self, cv, P, x0, x1, y, font, show_map=True, show_where=True, show_rank=True):
        """2.90.0: the map's time and where you are, as one centered text between x0 and x1. The area's name is shown
        whole: the type gets smaller (down to 7 pt) before anything is cut."""
        it = cv.create_text((x0 + x1) // 2, y, text="", anchor="center", fill=P["text"], font=font, tags=("mg",))
        part = _MapPart(cv, it, P["bg"], halo=self._mg_halo(P))
        part.width, part.font, part.show = max(20, x1 - x0 - 8), font, (show_map, show_where, show_rank)
        part.muted = P["muted"]
        self.tk_ov_lbls["map"] = _PartOf(part, "map")
        self.tk_ov_lbls["where"] = _PartOf(part, "where")
        self.tk_ov_lbls["rank"] = _PartOf(part, "rank")
        self._rank_click(cv, part)
        self.tk_ov_map_part = part
        return part

    def _mg_text(self, cv, P, x, y, key, font, fill=None, anchor="w", cls=CanvasText):
        it = cv.create_text(x, y, text="", anchor=anchor, fill=fill or P["text"], font=font, tags=("mg",))
        t = cls(cv, it, P["bg"], halo=self._mg_halo(P))
        self.tk_ov_lbls[key] = t
        return t

    def _mg_header(self, cv, P, x, y, w, text, right=None, right_cmd=None):
        """A small section title with a line after it (and a small action at the right)."""
        f = (P.get("hfont") or P["font"], 8, "bold")
        t = text.upper() if (P.get("caps") or P.get("rules")) else text
        cv.create_text(x, y, text=t, anchor="w", fill=P["head"], font=f, tags=("mg",))
        tw = tkfont.Font(root=cv, family=f[0], size=8, weight="bold").measure(t)
        end = x + w
        if right:
            rid = cv.create_text(end, y, text=right, anchor="e", fill=P["muted"], font=(P["font"], 9),
                                 tags=("mg", "mg_hdr_" + text))
            cv.tag_bind("mg_hdr_" + text, "<Button-1>", lambda e: right_cmd())
            cv.tag_bind("mg_hdr_" + text, "<Enter>", lambda e: cv.configure(cursor="hand2"))
            cv.tag_bind("mg_hdr_" + text, "<Leave>", lambda e: cv.configure(cursor=""))
            bb = cv.bbox(rid)
            end = (bb[0] if bb else end) - 8
        if end > x + tw + 8:
            cv.create_line(x + tw + 8, y, end, y, fill=P["line"], tags=("mg",))

    def _mg_cell(self, cv, P, k, x0, y0, x1, y1, label_cls=CanvasText, label_font=None, icon_only_row=False):
        """One mechanic switch: a box (on: green-tinted in Codex), its icon (◆ / ◇, ✓ / ✕) and its name."""
        tag = f"mgcell_{k}"
        rect = cv.create_rectangle(x0, y0, x1, y1, fill=P["cell_bg"], outline=P["cell_line"], tags=("mg", tag))
        mid = (y0 + y1) // 2
        if icon_only_row:                                   # Minimal: the icon over a short name
            dot = cv.create_text((x0 + x1) // 2, y0 + 10, text=P["off_icon"], fill=P["off"],
                                 font=("Segoe UI Symbol", 10), tags=("mg", tag))
            lab = cv.create_text((x0 + x1) // 2, y1 - 9, text=SHORT[k], fill=P["text"], font=label_font,
                                 tags=("mg", tag))
        else:
            dot = cv.create_text(x0 + 13, mid, text=P["off_icon"], fill=P["off"], font=("Segoe UI Symbol", self._hf(11)),
                                 tags=("mg", tag))
            lab = cv.create_text(x0 + 13 + self._hf(13), mid, text=chip_name(k), anchor="w", fill=P["text"],
                                 font=label_font or (P["font"], 10, "bold" if not P.get("caps") else "normal"),
                                 tags=("mg", tag))
        cv.tag_bind(tag, "<Button-1>", lambda e, k=k: self.tracker_helper_click(k))
        cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
        self.ov_help_bind(cv, tag, k)                 # 2.73.4: what it does, on hover
        d = CanvasText(cv, dot, P["cell_bg"])
        lt = label_cls(cv, lab, P["cell_bg"])
        lt.key = k
        if P.get("on_bg"):                                  # Codex: the box itself says on / off too
            def recolor(d=d, rect=rect):
                on = cv.itemcget(d.item, "text") == P["on_icon"]
                cv.itemconfigure(rect, fill=P["on_bg"] if on else P["cell_bg"],
                                 outline=P["on_line"] if on else P["cell_line"])
            d.on_change = recolor
        self.tk_ov_alerts[k] = (d, lt)

    def _mg_clock(self, w, cv, P, x, y, anchor="ne", on_bar=True):
        clk = cv.create_text(x, y, text="", anchor=anchor, fill=P["muted"], font=(P["font"], self._hf(9)), justify="right",
                             tags=("mg", "mg_clock"))

        class _Clock:
            text = ""

            def cget(self_, key):
                return self_.text if key == "text" else ""

            def config(self_, text="", **_kw):
                self_.text = text
                one = " · ".join(text.splitlines())
                fits = on_bar and w.bar_note(one)
                if on_bar and not fits:
                    w.bar_note("")
                try:
                    cv.itemconfigure(clk, text="" if fits else (one if not on_bar else text))
                except tk.TclError:
                    pass
        self.tk_ov_clock = _Clock()
        return clk

    def _mg_glyphs(self, w, cv, P, x, y):
        """The lock drawn on the canvas (Minimal and Strip have no title bar). -> x left of it. (2.59.0: no
        × - it was easy to hit by mistake and the overlay vanished; F6 shows / hides it.)"""
        locked = bool(self.tracker_cfg().get("mlocked"))
        for txt, cmd, tag in (("🔒" if locked else "🔓", lambda: w._toggle_lock(), "mg_lock"),
                              ("⚙", self.overlay_settings_go, "mg_cog")):    # 2.89.1: Overlay ↳ Settings
            cv.create_text(x, y, text=txt, anchor="e", fill=P["muted"], font=("Segoe UI Symbol", 10, "bold"),
                           tags=("mg", tag))
            cv.tag_bind(tag, "<Button-1>", lambda e, c=cmd: c())
            if tag == "mg_cog":                          # P4 (2.108.0): right-click = Quick settings over the game
                cv.tag_bind(tag, "<Button-3>", lambda e: self.ov_quick_toggle(e))
            cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
            cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
            x -= 20
        return x

    # ---------------------------------------------------------------- 2.92.2: the master switch
    def ov_enabled(self):
        """Overlay Enabled | Overlay Disabled (Overlay page, top). A new install starts disabled; an install that
        already had the overlay keeps it on."""
        cfg = self.tracker_cfg()
        if "ov_on" not in cfg:
            cfg["ov_on"] = not getattr(self, "_fresh_install", False)
        return bool(cfg["ov_on"])

    def ov_enable(self, on):
        """On: the bar, the calculator and the rates window come back as you left them - then, the first time, which
        switches go on the bar. Off: all of it goes (each helper's own setting is kept)."""
        on = bool(on)
        self.tracker_cfg()["ov_on"] = on
        self.tracker_save()
        v = getattr(self, "tk_ov_master", None)
        if v is not None and v.get() != ("on" if on else "off"):
            v.set("on" if on else "off")
        if on:
            self.merged_build()
            self.calc_ov_restore()
            self.ovr_restore()
            return self.ov_chips_maybe()
        self.calc_ov_close(remember=False)
        self.ovr_close()
        self.rx_ov_close()
        self.camp_vendor_close()
        try:
            if getattr(self.overlay, "notes", None) is not None and not self.overlay._embedded():
                self.overlay.hide_notes(remember=False)
        except Exception:
            pass
        self.merged_build()
        return None

    # ---------------------------------------------------------------- 2.90.0: which switches on the bar
    def ov_chips_maybe(self):
        """Once: ask which helpers' switches go on the overlay's bar (a new install shows none until you pick)."""
        cfg = self.tracker_cfg()
        if cfg.get("chips_asked"):
            return None
        return self.ov_chips_ask()

    def ov_chips_ask(self):
        from .style import C
        from . import ovhelp as OH
        old = getattr(self, "ov_chips_win", None)
        if old is not None and old.winfo_exists():
            old.lift()
            return old
        P2 = C["panel2"]
        w = self.ov_chips_win = tk.Toplevel(self.root, bg=P2)
        w.title("Your overlay bar")
        w.transient(self.root)
        w.resizable(False, False)
        box = tk.Frame(w, bg=P2, padx=16, pady=16)
        box.pack(fill="both", expand=True)
        tk.Label(box, text="Which switches do you want on the overlay's bar?", bg=P2, fg=C["text"],
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(box, text="Tick the helpers you use. Each switch turns its helper on and off mid-game; the bar fits "
                 "itself to the ones you keep. Change this any time: Overlay ↳ Settings › On the bar.", bg=P2,
                 fg=C["muted"], justify="left", wraplength=460, anchor="w").pack(fill="x", pady=(4, 8))
        b = self.bar_cfg()
        self.ov_chip_vars = {}
        for k in CHIPS:
            v = tk.BooleanVar(value=bool(b.get(k)) if not getattr(self, "_fresh_install", False) else False)
            self.ov_chip_vars[k] = v
            row = tk.Frame(box, bg=P2)
            row.pack(fill="x", pady=2)
            ttk.Checkbutton(row, text=chip_name(k), variable=v, width=12).pack(side="left")
            what = (OH.HELP.get(k) or ("", ""))[1]
            tk.Label(row, text=what, bg=P2, fg=C["muted"], font=("Segoe UI", 9), justify="left", wraplength=340,
                     anchor="w").pack(side="left", fill="x")
        btns = tk.Frame(box, bg=P2)
        btns.pack(fill="x", pady=(12, 0))
        ttk.Button(btns, text="Save", style="Primary.TButton", command=self.ov_chips_save).pack(side="right")
        w.protocol("WM_DELETE_WINDOW", self.ov_chips_save)
        try:
            w.update_idletasks()
            hx, hy, hw, hh = self.root.winfo_rootx(), self.root.winfo_rooty(), self.root.winfo_width(), self.root.winfo_height()
            w.geometry(f"+{hx + max(0, (hw - w.winfo_reqwidth()) // 2)}+{hy + max(0, (hh - w.winfo_reqheight()) // 3)}")
            w.lift()
        except tk.TclError:
            pass
        return w

    def ov_chips_save(self):
        b = self.bar_cfg()
        for k, v in (getattr(self, "ov_chip_vars", None) or {}).items():
            b[k] = bool(v.get())
        if any(b.get(k) for k in self.HELPERS):
            self.tracker_cfg()["alerts_bar"] = True
        self.tracker_cfg()["chips_asked"] = True
        self.tracker_save()
        w, self.ov_chips_win = getattr(self, "ov_chips_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass
        for k, v in (getattr(self, "tk_bar_vars", None) or {}).items():
            try:
                v.set(bool(b.get(k)))
            except tk.TclError:
                pass
        self.tracker_helpers_sync()
        self.merged_build()

    def overlay_settings_go(self):
        """2.89.1 (feedback): the app comes forward on Overlay ↳ Settings."""
        try:
            self.ovh_open("Settings")
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            self.log_error("opening the overlay's settings")

    def _mg_notes_button(self, w, cv, P, x, y, anchor="e", peek=False, chars=28):
        """Minimal / Strip: Notes opens the note as its own window right under this one."""
        oc = self.overlay.cfg
        if not oc.get("notes_enabled"):
            return x
        txt = "Notes"
        if peek:
            tabs = self.overlay.note_tabs()
            first = (tabs[self.overlay.note_index()]["text"].strip().splitlines() or [""])[0]
            first = first if len(first) <= chars else first[:max(1, chars - 1)].rstrip() + "…"
            txt = ("NOTES  " if P.get("caps") else "Notes  ") + (first or "-")
        txt += "  ▾" if not self.overlay.notes_shown() else "  ▴"
        cv.create_text(x, y, text=txt, anchor=anchor, fill=P["muted"], font=(P["font"], self._hf(9)), tags=("mg", "mg_notes"))
        cv.tag_bind("mg_notes", "<Button-1>", lambda e: self.merged_notes_drop())
        cv.tag_bind("mg_notes", "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind("mg_notes", "<Leave>", lambda e: cv.configure(cursor=""))
        bb = cv.bbox("mg_notes")
        return (bb[0] if bb else x) - 12

    def bar_buttons(self):
        """2.92.2: the menus on the bar, left to right: Notes ▾, Calc ▾, Regex ▾, Rates ▾, Vendor ▾ (each only when
        it's on). 2.104.1: Rates ▾ (the exchange rates window)."""
        return [k for k, on in (("notes", self.notes_on_bar()), ("calc", self.calc_on_bar()),
                                ("regex", self.regex_on_bar()), ("rates", bool(self.ovr_cfg()["on"])),
                                ("vendor", self.vendor_on_bar())) if on]

    def regex_on_bar(self):
        return bool(self.bar_cfg().get("regex", True))

    def vendor_on_bar(self):
        """2.92.2 (feedback: the Vendor switch did nothing): Vendor ▾ sits with the other menus, not on the campaign
        line. 2.96.1 (feedback): on the bar the whole campaign, in town or not, until the campaign is done."""
        from . import campaign as CP
        try:
            return bool(CP.cfg()["vendor"]) and bool(self.bar_cfg().get("vendor", True)) and CP.active()
        except Exception:
            return False

    def _mg_bar_buttons(self, w, cv, P, x, y, anchor="e"):
        """2.74.0: Notes ▾ and Calc ▾ side by side (each only when it's on the bar); 2.92.2: Regex ▾ and Vendor ▾
        too. -> the far edge."""
        order = self.bar_buttons()
        if anchor == "e":
            order.reverse()                               # drawn right to left
        for what in order:
            if what == "notes":
                nx = self._mg_notes_button(w, cv, P, x, y, anchor=anchor)
                bb = cv.bbox("mg_notes")
            else:
                nx = self._mg_menu_button(cv, P, x, y, what, anchor=anchor)
                bb = cv.bbox("mg_" + what)
            x = nx if anchor == "e" else ((bb[2] if bb else x) + 12)
        return x

    def _mg_menu_button(self, cv, P, x, y, what, anchor="e"):
        """Calc ▾, Regex ▾ or Vendor ▾: a click opens / closes its small window."""
        name, shown, click = {
            "calc": ("Calc", self.calc_ov_shown, self.calc_ov_toggle),
            "regex": ("Regex", self.rx_ov_shown, self.rx_ov_toggle),
            "rates": ("Rates", self.ovr_shown, self.ovr_toggle),
            "vendor": ("Vendor", lambda: getattr(self, "camp_vendor_win", None) is not None, self.camp_vendor_toggle),
        }[what]
        tag = "mg_" + what
        cv.create_text(x, y, text=name + ("  ▴" if shown() else "  ▾"), anchor=anchor, fill=P["muted"],
                       font=(P["font"], self._hf(9)), tags=("mg", tag))
        cv.tag_bind(tag, "<Button-1>", lambda e: click())
        cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
        bb = cv.bbox(tag)
        return (bb[0] if bb else x) - 12

    # 2.92.2 (feedback): your Regex favorites over the game, beside Notes and Calc
    def rx_ov_shown(self):
        return getattr(self, "rx_ov_win", None) is not None

    def rx_ov_toggle(self, show=None):
        show = (not self.rx_ov_shown()) if show is None else bool(show)
        if show:
            self.rx_ov_show()
        else:
            self.rx_ov_close()
        if getattr(self, "mg_win", None) is not None:
            self.merged_build()                          # (Regex ▾ / ▴ on the bar)
        return show

    def rx_ov_favs(self):
        out = []
        for f in getattr(self, "rx_favs", None) or []:
            try:
                s = self.rx_fav_search(f)
            except Exception:
                s = ""
            if s:
                out.append((f.get("name") or "Favorite", s))
        return out

    def rx_ov_show(self):
        self.rx_ov_close()
        w, body, P = self._camp_card("Regex favorites", "★", 380, top=0.14, on_close=lambda: self.rx_ov_toggle(False))
        bg = P["bg"]
        favs = self.rx_ov_favs()
        tip = "Click one = copied · Ctrl+V in the stash or shop search" if favs else \
            "No favorites yet. Build a search on the Regex page, then press ☆ Add to Favorites."
        tk.Label(body, text=tip, bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(9)), anchor="w", justify="left",
                 wraplength=self.ov_px(340)).pack(fill="x")
        self.rx_ov_btns = {}
        for name, rx in favs[:12]:
            b = ttk.Button(body, text=name, style=self.ov_btn(), command=lambda n=name, rx=rx: self.rx_ov_copy(n, rx))
            b.pack(fill="x", pady=1)
            self.rx_ov_btns[name] = b
        if len(favs) > 12:
            tk.Label(body, text=f"+{len(favs) - 12} more on the Regex page", bg=bg, fg=P["muted"],
                     font=(P["font"], self.ov_font(8)), anchor="w").pack(fill="x", pady=(4, 0))
        self.rx_ov_msg = tk.Label(body, text="", bg=bg, fg=P["on"], font=(P["font"], self.ov_font(9)), anchor="w")
        self.rx_ov_msg.pack(fill="x", pady=(8, 0))
        self.rx_ov_win = w
        w.show()
        return w

    def rx_ov_copy(self, name, rx):
        self.root.clipboard_clear()
        self.root.clipboard_append(rx)
        try:
            self.rx_ov_msg.config(text=f"Copied: {name}")
        except (AttributeError, tk.TclError):
            pass
        return rx

    def rx_ov_close(self):
        w, self.rx_ov_win = getattr(self, "rx_ov_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    # 2.74.3 (feedback: "a small pause play toggle for the session tracker directly on the overlay")
    def play_glyph(self):
        s = getattr(self, "tk_session", None)
        running = s is not None and s.ended is None and s.paused_at is None
        return "⏸" if running else "▶"

    def _mg_play(self, cv, P, x, y, anchor="w", size=12):
        """The session timer's ⏸ / ▶: pause, resume - or start, when it isn't tracking. Drawn as shapes (a font's
        ⏸ isn't there on every PC), in a small round button. -> its width."""
        d = self._hf(size) + 6                              # the button's size
        x0 = x - d // 2 if anchor == "center" else x
        y0 = y - d // 2
        cv.create_oval(x0, y0, x0 + d, y0 + d, fill=P.get("cell_bg", P["bg"]), outline=P.get("line", P["muted"]),
                       tags=("mg", "mg_play"))
        self._play_spots = [sp for sp in getattr(self, "_play_spots", []) if sp[0] is not cv or sp[1:3] != (x0, y0)]
        self._play_spots.append((cv, x0, y0, d, P.get("head", P["text"])))
        self._play_draw(cv, x0, y0, d, P.get("head", P["text"]))
        cv.tag_bind("mg_play", "<Button-1>", lambda e: self.tracker_play_click())
        cv.tag_bind("mg_play", "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind("mg_play", "<Leave>", lambda e: cv.configure(cursor=""))
        return d

    def _play_draw(self, cv, x0, y0, d, col):
        tag = f"mg_play_g{x0}_{y0}"
        cv.delete(tag)
        c, r = (x0 + d / 2, y0 + d / 2), d * 0.24
        if self.play_glyph() == "⏸":                      # two bars
            w = max(2, d * 0.13)
            for dx in (-r * 0.55, r * 0.55):
                cv.create_rectangle(c[0] + dx - w / 2, c[1] - r, c[0] + dx + w / 2, c[1] + r, fill=col, outline="",
                                    tags=("mg", "mg_play", tag))
        else:                                              # a triangle, a little right of center
            cv.create_polygon(c[0] - r * 0.7, c[1] - r, c[0] - r * 0.7, c[1] + r, c[0] + r, c[1], fill=col,
                              outline="", tags=("mg", "mg_play", tag))
        cv.itemconfigure(tag, state="disabled")            # (the button underneath takes the click)

    def tracker_play_click(self):
        s = getattr(self, "tk_session", None)
        if s is None or s.ended is not None:
            self.tracker_start()
        else:
            self.tracker_pause_toggle()
        self.play_refresh()

    def play_refresh(self):
        g = self.play_glyph()
        if g == getattr(self, "_play_last", None) and getattr(self, "_play_drawn", 0) == len(getattr(self, "_play_spots", [])):
            return
        self._play_last, live = g, []
        for cv, x0, y0, d, col in getattr(self, "_play_spots", []):
            try:
                if cv.winfo_exists():
                    self._play_draw(cv, x0, y0, d, col)
                    live.append((cv, x0, y0, d, col))
            except tk.TclError:
                pass
        self._play_spots = live
        self._play_drawn = len(live)

    def bar_buttons_on(self):
        return bool(self.bar_buttons())

    def merged_notes_drop(self):
        """The note under the strip / Minimal card (opened there each time, so it drops down from it)."""
        ov = self.overlay
        if ov.notes_shown():
            ov.hide_notes()
        else:
            w = getattr(self, "mg_win2", None) or getattr(self, "mg_win", None)
            try:
                if w is not None and w.winfo_ismapped() and self.merged_layout() in HUD:   # opens above the bar
                    ov.cfg.update(notes_x=w.winfo_x() + max(0, w.winfo_width() - int(ov.cfg.get("notes_w", 300))),
                                  notes_y=max(0, w.winfo_y() - int(ov.cfg.get("notes_h", 220)) - 6))
                elif w is not None and w.winfo_ismapped():
                    ov.cfg.update(notes_x=w.winfo_x() + max(0, w.winfo_width() - int(ov.cfg.get("notes_w", 300))),
                                  notes_y=w.winfo_y() + w.winfo_height() + 4)
            except tk.TclError:
                pass
            ov.show_notes()
        if getattr(self, "mg_win", None) is not None:
            self.merged_build()                              # (the ▾ / ▴)

    # ---------------------------------------------------------------- 2.66.1: the Panel (the game's Treasurer window)
    def _smallcaps(self, cv, P, cx, cy, text, size, fill):
        """Small caps like the game's titles: each word's first letter bigger, the rest in smaller capitals; centered."""
        big = tkfont.Font(root=cv, family=P["hfont"], size=self._hf(size), weight="bold")
        small = tkfont.Font(root=cv, family=P["hfont"], size=self._hf(round(size * 0.78)), weight="bold")
        parts = []
        for wi, word in enumerate(text.split(" ")):
            if wi:
                parts.append((" ", small))
            if word:
                parts.append((word[0].upper(), big))
                if word[1:]:
                    parts.append((word[1:].upper(), small))
        total = sum(f.measure(t_) for t_, f in parts)
        x = cx - total / 2
        base = cy + big.metrics("ascent") / 2 - 1
        for t_, f in parts:
            cv.create_text(x, base, text=t_, anchor="sw", fill=fill, font=f, tags=("mg",))
            x += f.measure(t_)

    def _mg_card(self, w, cv, P, want):
        """The Panel: a heavy dark-metal frame with filigree corners; a header banner (SESSION in antique gold small
        caps, where you are under it); the time, this map's time, maps done and the average in a 2 x 2 grid split by
        thin lines - a small cream icon, a big gold number; the switches in a second 2 x 2 grid (a gold glow when
        on); the clock, Notes ▾ and the lock under a thin rule."""
        from . import hudart
        cfg = self.tracker_cfg()
        k = getattr(self, "_hud_k", 1.0)
        W = int(300 * k)
        fw = int(12 * k)                                     # frame + its gold line
        gx0, gx1 = fw + int(4 * k), W - fw - int(4 * k)
        cx = W // 2
        by0, by1 = fw + int(4 * k), fw + int(4 * k) + int(46 * k)
        self._smallcaps(cv, P, cx, by0 + (by1 - by0) * 0.38, "Session" if want["timer"] else "Mechanics", 14, P["head"])
        if want["timer"]:
            self._mg_text(cv, P, cx, by0 + (by1 - by0) * 0.74, "where", (P["hfont"], self._hf(9)), fill=P["sub"],
                          anchor="center", cls=_Sub).config(text="")
        else:
            cv.create_text(cx, by0 + (by1 - by0) * 0.74, text="CLICK ONE TO SWITCH IT", fill=P["sub"],
                           font=(P["hfont"], self._hf(8)), tags=("mg",))
        y = by1 + int(8 * k)
        grids = []
        colw = (gx1 - gx0) // 2
        cells = []
        if want["timer"]:                                   # 2.70.1: each number has its switch (Options)
            for key, icon in (("session", "\u23f1"), ("map", "\u231b"), ("maps", "\u2691"), ("avg", "\u2248"),
                              ("rank", "\u2605")):            # 2.76.0: the map's rank, its own cell
                if cfg["lines"].get(key, True):
                    cells.append((key, icon))
        if cells:
            rows = (len(cells) + 1) // 2
            rh = int(40 * k)
            grids.append((gx0, y, gx1, y + rows * rh, rows, 2 if len(cells) > 1 else 1))
            for i, (key, icon) in enumerate(cells):
                x0, y0 = gx0 + (i % 2) * colw, y + (i // 2) * rh
                if key == "session":                        # 2.74.3: the ⏸ / ▶ button in the timer's place
                    self._mg_play(cv, P, x0 + int(16 * k), y0 + rh // 2, anchor="center", size=13)
                else:
                    cv.create_text(x0 + int(16 * k), y0 + rh // 2, text=icon, fill=P["icon"],
                                   font=("Segoe UI Symbol", self._hf(13)), tags=("mg",))
                if key == "session":                        # 2.69.2: PAUSED under the time, not after it
                    t = self._mg_text(cv, P, x0 + int(32 * k), y0 + rh // 2 - int(3 * k), key,
                                      (P["font"], self._hf(15), "bold"), fill=P["big"], cls=_Time)
                    t.num = True
                    t.tag = (cv.create_text(x0 + int(32 * k), y0 + rh - int(4 * k), text="", anchor="nw",
                                            fill=P["muted"], font=(P["font"], self._hf(7), "bold"), tags=("mg",)),
                             "below")
                    continue
                t = self._mg_text(cv, P, x0 + int(32 * k), y0 + rh // 2, key,
                                  (P["font"], self._hf(14), "bold"), fill=P["big"], cls=_Num)
                if key == "rank":                            # 2.76.0: click it to rank the map
                    self._rank_click(cv, t)
            y += rows * rh + int(8 * k)
        if want["helpers"]:
            chips = self.bar_chips()                         # 2.73.0: + Focus (each has its "on the bar" switch)
            nr = (len(chips) + 1) // 2
            rh = int(30 * k)
            grids.append((gx0, y, gx1, y + nr * rh, nr, 2))
            for i, kk in enumerate(chips):
                x0, y0 = gx0 + (i % 2) * colw, y + (i // 2) * rh
                self._card_switch(cv, P, kk, x0, y0, colw, rh)
            y += nr * rh + int(6 * k)
        ftext, fprog = "", None                              # 2.76.0: the focus line has its own bar (ovparts)
        if ftext:                                            # 2.73.0: the focus line (League Focus, I)
            rh = int(30 * k)
            grids.append((gx0, y, gx1, y + rh, 1, 1))
            cv.create_text(gx0 + int(10 * k), y + rh // 2, text="NOW", anchor="w", fill=P["head"],
                           font=(P["hfont"], self._hf(8), "bold"), tags=("mg",))
            ft = self._mg_text(cv, P, gx0 + int(44 * k), y + rh // 2, "focus", (P["font"], self._hf(9)), cls=_Trunc)
            ft.limit = 34 if fprog is None else 26
            ft.config(text=ftext)
            self._focus_click(cv, ft)
            if fprog is not None:
                bx1 = gx1 - int(10 * k)
                bx0 = bx1 - int(44 * k)
                cv.create_rectangle(bx0, y + rh // 2 - 2, bx1, y + rh // 2 + 2, fill=P["cell_bg"], outline=P["line"],
                                    tags=("mg",))
                cv.create_rectangle(bx0, y + rh // 2 - 2, bx0 + int((bx1 - bx0) * min(1.0, fprog)), y + rh // 2 + 2,
                                    fill=P["on"], outline="", tags=("mg",))
            y += rh + int(6 * k)
        foot = y + int(2 * k)
        fy = foot + int(11 * k)
        gx = self._mg_glyphs(w, cv, P, gx1 - int(4 * k), fy)
        menus_left = gx
        if self.bar_buttons_on():
            menus_left = self._mg_bar_buttons(w, cv, P, gx - 4, fy, anchor="e")
        extra = 0
        if want["timer"] and cfg.get("clock", True):
            self._mg_clock(w, cv, P, gx0 + int(4 * k), fy, anchor="w", on_bar=False)
            self.tk_ov_clock.config = (lambda fn: (lambda text="", **kw: fn(text=text.splitlines()[0]
                                                                            if text else "")))(self.tk_ov_clock.config)
            import tkinter.font as _tkf
            cw = _tkf.Font(root=cv, family=P["font"], size=self._hf(9)).measure("12:00 AM")
            if gx0 + int(4 * k) + cw + int(8 * k) > menus_left:   # 2.97.0: four menus and the clock don't fit - clock below
                extra = int(18 * k)
                cv.move("mg_clock", 0, extra)
        H = fy + extra + int(12 * k) + fw
        art = hudart.card(cv, W, H, (by0, by1), grids, foot)
        if art is not None:
            cv.create_image(0, 0, image=art, anchor="nw", tags=("hudbg",))
            cv.tag_lower("hudbg")
            cv._card_imgs = [art]
        cv.configure(width=W, height=H)

    def _card_switch(self, cv, P, k, x0, y0, bw, bh):
        """One mechanic switch in its grid cell: a diamond and its name; the cell glows gold when it's on."""
        from . import hudart
        tag = f"mgcell_{k}"
        g = hudart.glow(cv, bw - 4, bh - 4)
        lit = cv.create_image(x0 + 2, y0 + 2, image=g, anchor="nw", state="hidden", tags=("mg", tag)) if g else None
        hit = cv.create_rectangle(x0, y0, x0 + bw, y0 + bh, outline="", fill="", tags=("mg", tag))
        mid = y0 + bh // 2
        dot = cv.create_text(x0 + self._hf(16), mid, text=P["off_icon"], fill=P["off"],
                             font=("Segoe UI Symbol", self._hf(11)), tags=("mg", tag))
        lab = cv.create_text(x0 + self._hf(30), mid, text=chip_name(k), anchor="w", fill=P["text"],
                             font=(P["font"], self._hf(11)), tags=("mg", tag))
        cv.tag_bind(tag, "<Button-1>", lambda e, k=k: self.tracker_helper_click(k))
        cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
        self.ov_help_bind(cv, tag, k)                 # 2.73.4: what it does, on hover
        d = CanvasText(cv, dot, P["cell_bg"])
        lt = CanvasText(cv, lab, P["cell_bg"])
        lt.key = k

        def relit(d=d):
            if lit is not None:
                on = cv.itemcget(d.item, "text") == P["on_icon"]
                cv.itemconfigure(lit, state="normal" if on else "hidden")
        d.on_change = relit
        cv._hud_socks = getattr(cv, "_hud_socks", []) + [g]
        self.tk_ov_alerts[k] = (d, lt)
        _ = hit

    # ---------------------------------------------------------------- 2.65.0: Game bar (on the XP bar / beside the orbs)
    def _mg_hud_build(self, want):
        """One window resting on the XP bar, or two - right of the life orb (the timer) and left of the mana orb
        (the switches, Notes, the clock) - in the game's own bar look. Fitted to the game window; drag them while
        unlocked if your UI scale puts the bar elsewhere."""
        from . import hudart, themes as TH
        from .overlaywin import _seed
        cfg = self.tracker_cfg()
        layout = self.merged_layout()
        P = hudart.palette(pal())                           # 2.66.0: the game's own HUD look, in every theme
        _seed(TH, P)
        self.mg_P = P
        spots = self.hud_spots(layout)
        parts = [("all", spots[0])]
        self.tk_ov_lbls, self.tk_ov_alerts, self.tk_ov_clock, self.tk_ov_cv = {}, {}, None, None
        wins = []
        for part, (x, y, ww, hh) in parts:
            slot = 0 if part in ("all", "timer") else 1

            def moved(nx, ny, _w, _h, slot=slot):
                pos = cfg.setdefault("hud_pos", {}).setdefault(layout, [None] * len(HUD_SPOTS[layout]))
                while len(pos) < len(HUD_SPOTS[layout]):
                    pos.append(None)
                pos[slot] = [nx, ny]
                from .alerts_page import game_rect
                r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
                cfg.setdefault("hud_res", {})[layout] = [int(r[2]), int(r[3])]       # 2.79.1: kept for this size
                self.tracker_save()
                self.goalbar_follow()
            w = OverlayWindow(self.root, "Session", "⏱", (x, y, ww, hh), opacity=int(cfg.get("opacity", 225)),
                              locked=bool(cfg.get("mlocked")), min_size=(120, 24), on_close=self.merged_close,
                              on_lock=lambda on: self.overlay_lock(on), on_moved=moved, follow_game=True,
                              no_activate=True, resizable=False, titlebar=False, palette=P)
            w.withdraw()
            cv = w.canvas_body()
            cv.configure(width=ww - 2, height=hh - 2)
            if not cfg.get("mlocked"):
                w.draggable(cv)
            W, H = ww - 2, hh - 2
            self._hud_ends = ("crimson", "sapphire")
            self._hud_row(w, cv, P, want, W, H)
            wins.append(w)
            if self.tk_ov_cv is None:
                self.tk_ov_cv = cv
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
        return self.mg_win

    # 2.78.3: the cards over the game (map rank, campaign, feature tips) follow the game's size too
    def ov_k(self):
        from .alerts_page import game_rect
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        return hud_k(r[3])

    def ov_font(self, n):
        return max(7, round(n * self.ov_k()))

    def ov_px(self, n):
        return int(round(n * self.ov_k()))

    def ov_btn(self, style="TButton"):
        """A button style for a card over the game: its text at the game's size."""
        size = self.ov_font(10)
        name = f"Ov{size}.{style}"
        try:
            ttk.Style(self.root).configure(name, font=("Segoe UI", size), padding=(self.ov_px(8), self.ov_px(4)))
        except tk.TclError:
            return style
        return name

    def _hf(self, n):
        """A font size for the Game bar, grown with the game window (made for 1080 px high)."""
        return max(7, round(n * getattr(self, "_hud_k", 1.0)))

    def _hud_frame(self, cv, P, W, H, cap=None):
        """The game bar's plate (hudart: carved stone, bevelled bronze frame, end caps with an amber gem, a
        recessed well). -> the left / right edges of the well, where content goes."""
        from . import hudart
        img = hudart.plate(cv, W, H, P, ends=getattr(self, "_hud_ends", ("crimson", "sapphire")), cap=cap)
        m = (cap or hudart.cap_width(H)) + 14
        if img is not None:
            cv.create_image(0, 0, image=img, anchor="nw", tags=("hudbg",))
            cv._hud_img = img
            return m, W - m
        from .themes import mix                              # (no Pillow: a plain shaded bar)
        for i in range(max(1, H)):
            cv.create_line(0, i, W, i, fill=mix(P["bg_top"], P["bg"], i / max(1, H)), tags=("hudbg",))
        cv.create_line(0, 0, W, 0, fill=P["rim"], tags=("hudbg",))
        cv.create_line(1, 1, W - 1, 1, fill=P["rim_hi"], tags=("hudbg",))
        cv.create_line(0, H - 1, W, H - 1, fill=P["rim_lo"], tags=("hudbg",))
        return 16, W - 16

    def _hud_sep(self, cv, P, x, H, cy=None, h=None):
        from . import hudart
        h = h or max(10, H - 14)
        cy = H // 2 if cy is None else cy
        img = hudart.divider(cv, h, P)
        if img is not None:
            cv.create_image(x, cy, image=img, tags=("mg",))
        else:
            cv.create_line(x, cy - h // 2, x, cy + h // 2, fill=P["line"], tags=("mg",))

    def _hud_cell(self, cv, P, k, x0, y0, x1, y1, label_cls, font):
        """One switch in a recessed socket: lit when on. Click switches it (as everywhere)."""
        from . import hudart
        tag = f"mgcell_{k}"
        w_, h_ = max(8, x1 - x0), max(8, y1 - y0)
        off_img, on_img = hudart.socket(cv, w_, h_, P, False), hudart.socket(cv, w_, h_, P, True)
        if off_img is None:
            return self._mg_cell(cv, P, k, x0, y0, x1, y1, label_cls=label_cls, label_font=font)
        sock = cv.create_image(x0, y0, image=off_img, anchor="nw", tags=("mg", tag))
        mid = (y0 + y1) // 2
        dot = cv.create_text(x0 + 6 + self._hf(5), mid, text=P["off_icon"], fill=P["off"],
                             font=("Segoe UI Symbol", self._hf(10)), tags=("mg", tag))
        lab = cv.create_text(x0 + 9 + self._hf(12), mid, text=chip_name(k), anchor="w", fill=P["text"], font=font,
                             tags=("mg", tag))
        cv.tag_bind(tag, "<Button-1>", lambda e, k=k: self.tracker_helper_click(k))
        cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
        self.ov_help_bind(cv, tag, k)                 # 2.73.4: what it does, on hover
        d = CanvasText(cv, dot, P["cell_bg"])
        lt = label_cls(cv, lab, P["cell_bg"])
        lt.key = k

        def relit(d=d):
            on = cv.itemcget(d.item, "text") == P["on_icon"]
            cv.itemconfigure(sock, image=on_img if on else off_img)
        d.on_change = relit
        cv._hud_socks = getattr(cv, "_hud_socks", []) + [off_img, on_img]
        self.tk_ov_alerts[k] = (d, lt)

    def _hud_cell_w(self, cv, P, k, short):
        fb = tkfont.Font(root=cv, family=P["font"], size=self._hf(9))
        return fb.measure(SHORT[k] if short else ("Ritual 3/3" if k == "ritual" else chip_name(k))) + 16 + self._hf(12)

    def _hud_cells(self, cv, P, x, y0, y1, short, cols=4, cw=None):
        """The four switches in a row (short names when space is tight) or a 2 x 2 grid. -> right edge."""
        lc, font = (_Short if short else CanvasText), (P["font"], self._hf(9))
        if cols == 4:
            for k in self.bar_chips():
                w_ = self._hud_cell_w(cv, P, k, short)
                self._hud_cell(cv, P, k, x, y0, x + w_, y1, lc, font)
                x += w_ + self._hud_gap()
            return x
        rh = (y1 - y0 - 4) // 2
        for i, k in enumerate(self.bar_chips()):
            cx, cy = x + (i % 2) * (cw + 5), y0 + (i // 2) * (rh + 4)
            self._hud_cell(cv, P, k, cx, cy, cx + cw, cy + rh, lc, font)
        return x + 2 * cw + 5

    def _hud_gap(self):
        return 6                                             # 2.73.5: back to 2.73.3's spacing (room goes up / down)

    def _hud_clock(self, w, cv, P, x, y):
        self._mg_clock(w, cv, P, x, y, anchor="e", on_bar=False)
        self.tk_ov_clock.config = (lambda fn: (lambda text="", **kw: fn(text=text.splitlines()[0]
                                                                        if text else "")))(self.tk_ov_clock.config)

    def _hud_row(self, w, cv, P, want, W, H):
        """On the XP bar (2.67.2: two rows, feedback "too cluttered"): the four switches on top, with Notes ▾;
        under a thin rule the time | the map and where you are | Maps · Avg ... the clock and the lock."""
        from .themes import mix
        cfg = self.tracker_cfg()
        lft, rgt = self._hud_frame(cv, P, W, H)
        two = want["helpers"]
        top_mid = int(H * 0.30)                              # 2.73.5: more room above / below each row
        mid = int(H * 0.74) if two else H // 2 + 1
        f = (P["font"], self._hf(10))
        fm = tkfont.Font(root=cv, family=P["font"], size=self._hf(10))
        if two:                                              # ---- row 1: the switches, centered; Notes at the end
            ch = int(H * 0.28)                               # (the socket: about 2.73.5's size)
            gap = self._hud_gap()
            room = (rgt - lft) * 0.75 - sum(self._hf(70 if k in ("notes", "vendor", "regex", "rates") else 60)
                                            for k in self.bar_buttons())
            short = sum(self._hud_cell_w(cv, P, k, False) + gap for k in self.bar_chips()) > room
            total = sum(self._hud_cell_w(cv, P, k, short) + gap for k in self.bar_chips()) - gap
            bleft = rgt
            if self.bar_buttons_on():                        # Notes ▾ / Calc ▾ first; the switches keep clear of them
                bleft = self._mg_bar_buttons(w, cv, P, rgt, top_mid, anchor="e")
            span = min(rgt - lft, 2 * (bleft - (lft + rgt) // 2) - 16) if bleft < rgt else rgt - lft
            x0 = lft + max(0, ((rgt - lft) - total) // 2)
            if total > span:                                 # (centered doesn't fit: as far left as needed)
                x0 = max(lft, bleft - 16 - total)
            elif x0 + total > bleft - 16:
                x0 = max(lft, bleft - 16 - total)
            self._hud_cells(cv, P, x0, top_mid - ch // 2, top_mid + ch // 2, short=short)
            ry = int(H * 0.535)                              # a thin rule between the rows, fading at the ends
            n = 32
            seg = (rgt - lft) / n
            for i in range(n):
                a_ = 1 - abs((i + 0.5) / n - 0.5) * 2
                cv.create_line(lft + i * seg, ry, lft + (i + 1) * seg, ry, fill=mix(P["bg"], P["rim"], a_ ** 0.8),
                               tags=("mg",))
        # ---- row 2 (or the only row): the numbers - 2.73.5: a divider between each part (feedback: "more visual
        # division between the different areas of text")
        SW = self._hf(20)                                    # a divider's slot
        sh = int(H * 0.34) if two else None
        drawn = []

        def lead(x):
            """Before the next part: a divider, when something came before it."""
            if not drawn:
                return x
            self._hud_sep(cv, P, x + SW // 2, H, cy=mid, h=sh)
            return x + SW

        gx = self._mg_glyphs(w, cv, P, rgt, mid)
        right = gx
        if want["timer"] and cfg.get("clock", True):
            self._hud_clock(w, cv, P, gx - 2, mid)
            right = gx - fm.measure("00:00 PM") - 6 - SW
            self._hud_sep(cv, P, right + SW // 2, H, cy=mid, h=sh)
        x = lft
        ln = cfg["lines"]                                    # 2.70.1: each part has its switch (Options)
        if want["timer"]:
            if ln.get("session", True):
                x += self._mg_play(cv, P, x, mid, anchor="w", size=12) + 8      # 2.74.3: ⏸ / ▶ before the time
                t = self._mg_text(cv, P, x, mid, "session", (P["font"], self._hf(13), "bold"), fill=P["big"], cls=_Time)
                pf = (P["font"], self._hf(7), "bold")          # 2.69.2: a small PAUSED tag after the time, room kept
                t.tag = (cv.create_text(x, mid, text="", anchor="w", fill=P["muted"], font=pf, tags=("mg",)), "right")
                fb_ = tkfont.Font(root=cv, family=P["font"], size=self._hf(13), weight="bold")
                fp_ = tkfont.Font(root=cv, family=P["font"], size=self._hf(7), weight="bold")
                x += max(fb_.measure("0:00:00") + 6 + fp_.measure("PAUSED"), fb_.measure("not tracking")) + 4
                drawn.append("session")
            # 2.90.0: | Map 3:12  Arcane Isle | Maps: 4 | Avg. 6:01 | - the map and where you are share one part,
            # each part's text is centered between its dividers, and the area's name is shown whole (smaller type
            # before it is ever cut)
            mw, aw = fm.measure("Maps: 000") + 16, fm.measure("Avg.: 00:00") + 16
            fixed = [k for k, on in (("maps", ln.get("maps")), ("avg", ln.get("avg"))) if on]
            widths = {"maps": mw, "avg": aw}
            map_on = bool(ln.get("map", True) or ln.get("where", True))

            def room(keys):
                return right - x - sum(widths[k] + SW for k in keys) - (SW if drawn and map_on else 0)
            if map_on:                                        # (the map's rank rides in this part too: ★ A)
                x = lead(x)
                map_w = max(self._hf(60), room(fixed))
                self._hud_map_part(cv, P, x, x + map_w, mid, f, show_map=ln.get("map", True),
                                   show_where=ln.get("where", True), show_rank=bool(ln.get("rank", True)))
                x += map_w
                drawn.append("map")
            elif fixed:
                x = max(x, right - sum(widths[k] + SW for k in fixed))
            for k in fixed:
                x = lead(x)
                self._mg_text(cv, P, x + widths[k] // 2, mid, k, f, anchor="center")
                x += widths[k]
                drawn.append(k)
        elif not two and self.bar_buttons_on():
            self._mg_bar_buttons(w, cv, P, x, mid, anchor="w")
