"""One overlay (2.55.0, from the mockups): the Session timer, the Mechanic Helper and Notes in ONE window
over the game. 2.67.0: two looks, both the game's own - the Panel (a card like the game's vendor windows: header
plate, stats in a grid, the switches) and the Bar (on the XP bar, in the HUD's own frame). 2.67.0: the four
switches are in both whenever the timer shows. Notes opens as its own window from Notes ▾.

Which parts show: the timer while a session runs (2.70.1: each part - the timer, each number, where you are, the clock,
Notes, the switches - has its switch in Overlay › Options › On the overlay), the switches while their switch is on. One window holds whatever is on; when nothing is, it's gone. ToS: it only shows
things - the same reading as the separate windows."""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from . import buglog
from .overlaywin import CanvasText, OverlayWindow, pal

# 2.66.0: one look (the app's theme); the layout says the shape - Minimal moved here from the old Style list
# 2.67.0 (feedback: "get rid of all of the other options"): the Panel in the game's vendor-window style (the
# Treasurer's ledger) and the Bar on the XP bar. Strip, Minimal and beside-the-orbs are gone (-> Panel).
LAYOUTS = {"panel": "Panel", "xpbar": "Bar"}     # 2.67.0: beside the orbs is gone; 2.74.0: "Bar"
HUD = ("xpbar",)                 # 2.65.0: fitted to the game's own bottom bar, in its look

# Where the game's bottom bar leaves room, as parts of the game window's height (PoE2 at 16:9, UI scale 100 %;
# the orbs' panels are anchored to the left and right edges, the XP bar runs between them). (x0, x1, bottom, h)
#   x0 / x1 >= 0: from the left edge, < 0: from the right edge; bottom: up from the bottom edge.
# 2.79.1: as wide as the XP bar (measured at 1440p), over it. 2.118.0: one row (no switches above it) - 0.036 high
# (was 0.056 for two rows); a bar you moved keeps its bottom edge where you put it (OLD_HUD_H)
HUD_SPOTS = {"xpbar": [(0.531, -0.531, 0.0205, 0.036)]}
OLD_HUD_H = 0.056


def click_not_drag(cv, item, fn):
    """2.112.5: fn() on a click of a canvas item - not when the press became a drag (the Campaign line opened its
    route card when you dragged the line by its text)."""
    st = {}
    cv.tag_bind(item, "<ButtonPress-1>", lambda e: st.update(x=e.x_root, y=e.y_root), add="+")

    def release(e):
        if st and abs(e.x_root - st.get("x", e.x_root)) <= 4 and abs(e.y_root - st.get("y", e.y_root)) <= 4:
            fn()
        st.clear()
    cv.tag_bind(item, "<ButtonRelease-1>", release, add="+")



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
        fam, size = self.font[0], int(self.font[1])
        rest = tuple(self.font[2:])

        def join(where):
            return "  ".join(t for t in (m, where, rk) if t and t != "-")
        text = join(wh)
        try:
            fnt = tkfont.Font(root=self.canvas, family=fam, size=size, weight=rest[0] if rest else "normal")
            # 2.124.1 (feedback: map time, name and session crammed): the area's name is cut first, the time and
            # rank kept whole at the bar's size; only then one size smaller, then cut
            cut = wh
            while cut and fnt.measure(text) > self.width:
                cut = cut[:-2].rstrip()
                text = join(cut + "…" if cut else "")
            if fnt.measure(text) > self.width and size > 8:
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
            m = re.match(r"^\s*(?:Maps:?|Map:?|Zone:?|Avg\.?:?|★)\s*(.*)$", str(kw["text"]))
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
    dim = None          # 2.119.0 (XP bar): (normal, paused) colors - paused dims the time instead of a PAUSED tag

    def config(self, **kw):
        if "text" in kw:
            t = str(kw["text"])
            paused = "(paused)" in t
            t = t.replace("(paused)", "").rstrip()
            if self.num and "tracking" in t:
                t = "--:--"
            kw["text"] = t
            if self.dim:
                kw["fg"] = self.dim[1] if paused else self.dim[0]
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
                    buglog.caught()
            return
        super().config(**kw)
    configure = config


class MergedOverlay:
    """Mixed into App (with TrackerPage, which builds the separate windows)."""

    # ---------------------------------------------------------------- settings
    def merged_on(self):
        """2.59.0: always one window - the separate windows of 2.54 are gone."""
        return True

    def merged_layout(self):
        v = self.tracker_cfg().get("layout", "xpbar")      # 2.74.0: the Bar by default
        return v if v in LAYOUTS else "panel"            # (2.67.0: an old Strip / Minimal is the Panel now)

    def merged_embeds_notes(self):
        """2.67.0: the note always opens as its own window, from the overlay's Notes ▾."""
        return False

    def hud_spots(self, layout=None):
        """2.65.0: the Bar windows' places -> [(x, y, w, h)]: fitted to the game window (or the main screen),
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
            saved = []                                                             # fitted again, bottom center
        out = []
        for i, (a, b, bot, hh) in enumerate(HUD_SPOTS[layout]):
            x0 = gx + (a * gh if a >= 0 else gw + a * gh)
            x1 = gx + (b * gh if b >= 0 else gw + b * gh)
            h = max(26, int(hh * gh))
            w = max(160, int(x1 - x0))
            x, y = int(x0), int(gy + gh - bot * gh - h)
            if i < len(saved) and isinstance(saved[i], (list, tuple)) and len(saved[i]) == 2:
                x, y = int(saved[i][0]), int(saved[i][1])
                if not cfg.get("hud_one_row"):                # (moved while it had two rows: same bottom edge)
                    y += max(26, int(OLD_HUD_H * gh)) - h
            out.append((x, y, w, h))
        return out

    def merged_wants(self):
        oc = self.overlay.cfg
        if not self.ov_enabled():                         # 2.92.2: the master switch is off - nothing over the game
            return {"bar": False, "timer": False, "helpers": False, "notes": False}
        # 2.118.0 (feedback: the helpers' switches were "just screen clutter"): no switches on the bar - every helper
        # is on or off in Settings › Overlay › Helpers. The bar itself (menus, clock, lock, ⚙) shows while the
        # overlay is on; "helpers" stays False for the drawing code that used to lay the switches out.
        return {"bar": True, "timer": bool(getattr(self, "mg_timer", False)), "helpers": False,
                "notes": self.merged_embeds_notes() and bool(oc.get("notes_enabled")) and bool(oc.get("notes_visible"))}

    # 2.73.0: what sits on the overlay's bar - each menu has an "on the bar" switch (Overlay ↳ Settings › On the bar).
    # 2.118.0: menus only - the helpers' switches are gone (their old keys are left as they were, unread).
    def bar_cfg(self):
        b = self.tracker_cfg().setdefault("bar", {})
        b.setdefault("notes", True)
        b.setdefault("calc", True)                       # 2.74.0: Calc ▾ (the calculator over the game)
        b.setdefault("vendor", True)                     # 2.77.0: Vendor ▾ in town (campaign)
        b.setdefault("regex", True)                      # 2.92.2: Regex ▾ (your favorites)
        return b


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
            click_not_drag(cv, ft.item, lambda: self.ov_intro_setup("focus"))
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

    def ov_camp_mode(self):
        """2.124.0 (feedback: in campaign areas it should say Zone, no tier rank or average): the Campaign Helper is
        on and its line shows (the campaign, hideouts on the way included - Vendor ▾ is on the bar then, and the map
        numbers had no room) - the overlay shows the act line, the session and the zone's time only."""
        if getattr(self, "_ov_previewing", False):         # (Settings' preview shows a map, as its sample says)
            return False
        try:
            from . import campaign as CP
            return bool(CP.active())
        except Exception:
            return False

    def ov_lines(self):
        """The overlay's parts that show (Options › On the overlay) - in a campaign zone without the map's rank, its
        name, Maps and Avg."""
        ln = dict(self.tracker_cfg()["lines"])
        if self.ov_camp_mode():
            ln.update(rank=False, where=False, maps=False, avg=False)
        return ln

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
            if layout != cfg.get("layout"):                 # 2.66.0: a Bar layout picked again starts fitted
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
        try:                                                # 2.109.0: Calc and Regex favorites too
            self.calc_ov_restyle()
            if self.rx_ov_shown():
                self.rx_ov_show()
        except Exception:
            self.log_error("restyling the overlay's windows")
        try:
            self.ov_cards_restyle()
        except Exception:
            self.log_error("restyling the cards over the game")

    def ov_cards_restyle(self):
        """2.125.5 (feedback: every tool over the game follows the overlay's style): the open cards are built again
        in the new style, where they were - the route card (its page, act and size), Vendor search, the price check
        card."""
        def spot(w):
            try:
                return w.winfo_x(), w.winfo_y()
            except (tk.TclError, AttributeError):
                return None

        def put(w, xy):
            if w is not None and xy:
                try:
                    w.geometry(f"+{xy[0]}+{xy[1]}")
                except tk.TclError:
                    pass
        w = getattr(self, "camp_win", None)
        if w is not None:
            xy, page, act = spot(w), self.camp_page, self.camp_view
            self.camp_route_close()
            put(self.camp_route_show(page=page, act_key=act), xy)
        w = getattr(self, "camp_vendor_win", None)
        if w is not None:
            xy = spot(w)
            self.camp_vendor_show()
            put(getattr(self, "camp_vendor_win", None), xy)
        w = getattr(self, "pp_win", None)
        rid = getattr(self, "pp_rid", None)
        if w is not None and rid is not None and rid in getattr(self, "records", {}):
            self.pcpop_close()
            self.pcpop_show(self.records[rid])

    # ---------------------------------------------------------------- the window
    def merged_destroy(self):
        lines_h = getattr(self, "_gb_h", 0)                           # (2.124.0: the lines on top - the bar is under them)
        self.goalbar_destroy(keep_place=False)
        w2, self.mg_win2 = getattr(self, "mg_win2", None), None      # 2.65.0: the second Bar half
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
                cfg.update(mx=w.winfo_x(), my=w.winfo_y() + lines_h)
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
            self.goalbar_build()                             # 2.124.0: the NOW / Campaign / Ritual lines, on top
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
        game's counters under it. Its own switch (Overlay ↳ Settings › Behavior), on by default; off = screenshots
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
        for w in (getattr(self, "mg_win", None), getattr(self, "mg_win2", None)):
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
        self._ov_camp_built = self.ov_camp_mode()
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
        P = hudart.panel_palette(pal())                     # 2.124.1: the Bar's look (2.67.0: a vendor window)
        _seed(TH, P)
        self.mg_P = P
        self.hud_spots("xpbar")                             # (sizes follow the game window's height)
        x, y = cfg.get("mx", cfg.get("x", 60)), cfg.get("my", cfg.get("y", 260))

        def moved(nx, ny, _ww, _hh):
            cfg.update(mx=nx, my=ny + getattr(self, "_gb_h", 0))     # (2.124.0: where the bar is, under the lines)
            self.tracker_save()
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
        self._mg_classic_panel(w, cv, P, want)
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
        """2.59.0: F6 (Settings › Keys) hides the whole overlay - timer, switches, Notes - and shows it
        again, as it was. Nothing is switched off; it's only out of sight."""
        self.mg_hidden = not getattr(self, "mg_hidden", False)
        w = getattr(self, "mg_win", None)
        note = self.overlay.notes if getattr(self.overlay, "notes", None) is not None else None
        for win in (w, getattr(self, "mg_win2", None), note):
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
                              ("⚙", None, "mg_cog")):         # 2.119.0: ⚙ = Quick settings (either click)
            cv.create_text(x, y, text=txt, anchor="e", fill=P["muted"], font=("Segoe UI Symbol", 10, "bold"),
                           tags=("mg", tag))
            if tag == "mg_cog":                          # (its All settings… opens Overlay ↳ Settings in the app)
                for b in ("<Button-1>", "<Button-3>"):
                    cv.tag_bind(tag, b, lambda e: self.ov_quick_toggle(e))
            else:
                cv.tag_bind(tag, "<Button-1>", lambda e, c=cmd: c())
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
            return None
        self.calc_ov_close(remember=False)
        self.ovr_close()
        self.rx_ov_close()
        self.camp_vendor_close()
        try:
            if getattr(self.overlay, "notes", None) is not None and not self.overlay._embedded():
                self.overlay.hide_notes(remember=False)
        except Exception:
            buglog.caught()
        self.merged_build()
        return None

    # ---------------------------------------------------------------- 2.90.0: which switches on the bar


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

    def _mg_bar_buttons(self, w, cv, P, x, y, anchor="e", right=None, step=0):
        """2.74.0: Notes ▾ and Calc ▾ side by side (each only when it's on the bar); 2.92.2: Regex ▾ and Vendor ▾
        too. -> the far edge. 2.124.0 (feedback: Vendor ▾ ran off the Panel): left-anchored with right / step, a menu
        that would pass `right` goes on a new line step px lower (self._mg_menu_rows: how many lines)."""
        order = self.bar_buttons()
        if anchor == "e":
            order.reverse()                               # drawn right to left
        x0, first, self._mg_menu_rows = x, True, 1
        for what in order:
            tag = "mg_notes" if what == "notes" else "mg_" + what
            if what == "notes":
                nx = self._mg_notes_button(w, cv, P, x, y, anchor=anchor)
            else:
                nx = self._mg_menu_button(cv, P, x, y, what, anchor=anchor)
            bb = cv.bbox(tag)
            if anchor == "w" and right is not None and step and bb and bb[2] > right and not first:
                cv.move(tag, x0 - bb[0], step)            # (a new line)
                y += step
                self._mg_menu_rows += 1
                bb = cv.bbox(tag)
            first = False
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
    def _mg_classic_panel(self, w, cv, P, want):
        """2.124.1 (feedback: "classic panel visual look needs to be the same as bar"): the Slate Panel's parts on the
        Bar's stone and pewter frame, in its colors and type. (2.67.0-2.124.0: a vendor-window card, _mg_card.)"""
        from . import hudart
        spot = self.hud_spots("xpbar")[0]
        W, H = self._lt_slate_panel(w, cv, P, want, spot, "all")
        cv.configure(width=W, height=H)
        art = hudart.panel(cv, W, H)
        if art is not None:
            cv.create_image(0, 0, image=art, anchor="nw", tags=("hudbg",))
            cv.tag_lower("hudbg")
            cv._card_imgs = [art]
        return W, H

    # ---------------------------------------------------------------- 2.65.0: Bar (on the XP bar / beside the orbs)
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
                pos[slot] = [nx, ny + (getattr(self, "_gb_h", 0) if slot == 0 else 0)]     # (the bar, under the lines)
                cfg["hud_one_row"] = True                    # (2.118.0: placed for the one-row bar)
                from .alerts_page import game_rect
                r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
                cfg.setdefault("hud_res", {})[layout] = [int(r[2]), int(r[3])]       # 2.79.1: kept for this size
                self.tracker_save()
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
        """A button style for a card over the game: its text at the game's size.
        2.125.5 (feedback: "ALL tools that open over the game ... should follow these rules for styling matching"):
        in the overlay's style too - its colors and font, not the app's (the app's orange and blue showed on every
        card). Primary = the one picked: the style's accent edge and strong text (Quick settings' chips)."""
        from .overlaywin import pal
        from .style import mix
        P = pal()
        size = self.ov_font(10)
        kind = style.split(".")[0] if "." in style else "TButton"
        sig = "|".join(str(P.get(k)) for k in ("bg", "text", "muted", "line", "head", "accent", "cell_bg", "font", "poe"))
        name = f"Ov{size}x{abs(hash(sig)) % 10 ** 6}.{style}"
        acc = P["head"] if P.get("poe") else (P.get("accent") or P["head"])
        face = P.get("cell_bg") or P["bg"]
        on = kind == "Primary"
        bg = mix(face, acc, 0.22) if on else face
        try:
            st = ttk.Style(self.root)
            # (the app's buttons are drawn from images in its colors - these use the plain frame in the overlay's)
            st.layout(name, [("Button.border", {"sticky": "nswe", "border": "1", "children": [
                ("Button.focus", {"sticky": "nswe", "children": [("Button.padding", {"sticky": "nswe", "children": [
                    ("Button.label", {"sticky": "nswe"})]})]})]})])
            st.configure(name, font=(P.get("font") or "Segoe UI", size, "bold" if on else "normal"), anchor="center",
                         padding=(self.ov_px(8), self.ov_px(4)), background=bg,
                         foreground=P["text"] if on else (P["text"] if kind != "Quiet" else P["text"]),
                         bordercolor=acc if on else P["line"], lightcolor=bg, darkcolor=bg,
                         focuscolor=acc, relief="solid", borderwidth=1)
            hov = mix(bg, P["text"], 0.10)
            st.map(name, background=[("disabled", P["bg"]), ("pressed", mix(bg, acc, 0.35)), ("active", hov),
                                     ("!disabled", bg)],          # (the last: the app's own Primary orange never shows)
                   foreground=[("disabled", P["muted"]), ("!disabled", P["text"])],
                   bordercolor=[("active", acc), ("!disabled", acc if on else P["line"])],
                   lightcolor=[("active", hov), ("!disabled", bg)], darkcolor=[("active", hov), ("!disabled", bg)])
        except tk.TclError:
            return style
        return name

    def ov_combo(self, cb):
        """2.125.5: a list (combobox) on a card over the game in the overlay's style - its field and its dropdown."""
        from .overlaywin import pal
        P = pal()
        face = P.get("field") or P.get("cell_bg") or P["bg"]
        sig = "|".join(str(P.get(k)) for k in ("bg", "text", "line", "field", "cell_bg", "font"))
        name = f"Ov{abs(hash(sig)) % 10 ** 6}.TCombobox"
        try:
            st = ttk.Style(self.root)
            st.configure(name, fieldbackground=face, background=P.get("cell_bg") or face, foreground=P["text"],
                         arrowcolor=P["text"], bordercolor=P.get("cell_line") or P["line"], lightcolor=face,
                         darkcolor=face, selectbackground=face, selectforeground=P["text"])
            st.map(name, fieldbackground=[("readonly", face)], foreground=[("readonly", P["text"])],
                   selectbackground=[("readonly", face)], selectforeground=[("readonly", P["text"])])
            cb.configure(style=name, font=(P.get("font") or "Segoe UI", self.ov_font(10)))
            pd = cb.tk.call("ttk::combobox::PopdownWindow", str(cb))
            cb.tk.call(f"{pd}.f.l", "configure", "-background", P["bg"], "-foreground", P["text"],
                       "-selectbackground", P.get("cell_bg") or P["line"], "-selectforeground", P["head"],
                       "-font", (P.get("font") or "Segoe UI", self.ov_font(10)))
        except tk.TclError:
            pass
        return cb

    def _hf(self, n):
        """A font size for the Bar, grown with the game window (made for 1080 px high)."""
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


    def _hud_gap(self):
        return 6                                             # 2.73.5: back to 2.73.3's spacing (room goes up / down)

    def _hud_clock(self, w, cv, P, x, y):
        self._mg_clock(w, cv, P, x, y, anchor="e", on_bar=False)
        self.tk_ov_clock.config = (lambda fn: (lambda text="", **kw: fn(text=text.splitlines()[0]
                                                                        if text else "")))(self.tk_ov_clock.config)

    def _hud_row(self, w, cv, P, want, W, H):
        """On the XP bar, one row (2.118.0: no helper switches above it): the time | the map and where you are |
        Maps · Avg ... Notes ▾ / Calc ▾ … | the clock, the lock and ⚙."""
        cfg = self.tracker_cfg()
        lft, rgt = self._hud_frame(cv, P, W, H)
        mid = H // 2 + 1
        f = (P["font"], self._hf(10))
        fm = tkfont.Font(root=cv, family=P["font"], size=self._hf(10))
        # ---- row 2 (or the only row): the numbers - 2.73.5: a divider between each part (feedback: "more visual
        # division between the different areas of text")
        SW = self._hf(14)                                    # a divider's slot (2.118.0: 20 -> 14, one row holds more)
        sh = None
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
        if want["timer"] and self.bar_buttons_on():         # 2.118.0: one row - Notes ▾ … before the clock
            right = self._mg_bar_buttons(w, cv, P, right - 4, mid, anchor="e") - SW
            self._hud_sep(cv, P, right + SW // 2, H, cy=mid, h=sh)
        x = lft
        ln = self.ov_lines()                                 # 2.70.1: each part has its switch (Options)
        if want["timer"]:
            if ln.get("session", True):
                x += self._mg_play(cv, P, x, mid, anchor="w", size=12) + 8      # 2.74.3: ⏸ / ▶ before the time
                t = self._mg_text(cv, P, x, mid, "session", (P["font"], self._hf(13), "bold"), fill=P["big"], cls=_Time)
                # 2.119.0 (UX pass, feedback: long map names were cut): the time takes only its own width - not
                # tracking shows --:--, paused dims it (the ▶ beside it says so); no room kept for a PAUSED tag
                t.num, t.dim = True, (P["big"], P["muted"])
                fb_ = tkfont.Font(root=cv, family=P["font"], size=self._hf(13), weight="bold")
                x += fb_.measure("0:00:00") + 6
                drawn.append("session")
            # 2.90.0: | Map 3:12  Arcane Isle | Maps: 4 | Avg. 6:01 | - the map and where you are share one part,
            # each part's text is centered between its dividers, and the area's name is shown whole (smaller type
            # before it is ever cut)
            mw, aw = fm.measure("Maps: 000") + 8, fm.measure("Avg: 00:00") + 8
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
        elif self.bar_buttons_on():
            self._mg_bar_buttons(w, cv, P, x, mid, anchor="w")
