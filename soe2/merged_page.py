"""One overlay (2.55.0, from the mockups): the Session timer, the Mechanic Helper and Notes in ONE window
over the game, in any style (Overlays › Appearance › Style) and either layout:

    Panel  a card: the time, Map | where, Maps | Avg, the four mechanic switches in two rows, then Notes (tabs + text)
    Strip  one thin bar along the top edge: SESSION 42:17 | Map 6:12 Oasis | Maps 7 · Avg 6:01 | the four switches |
           NOTES first line ▾ (opens the note right under the bar) | the clock, lock and ×

The Minimal style is always compact: the time and clock, Map, the four switches with short names, a Notes button.
(2.59.0: always one window - the Merged switch and the separate windows are gone.)

Which parts show: the timer while it's shown (Show timer, or a session running - as before), the switches while the
Mechanic Helper's switch is on, Notes while they're shown (the notes key, or Overlays › Notes). One window holds
whatever is on; when nothing is, it's gone. ToS: it only shows things - the same reading as the separate windows."""
import tkinter as tk
from tkinter import font as tkfont

from .overlaywin import CanvasText, OverlayWindow, pal

# 2.66.0: one look (the app's theme); the layout says the shape - Minimal moved here from the old Style list
LAYOUTS = {"panel": "Panel", "strip": "Strip", "minimal": "Minimal", "xpbar": "Game bar - on the XP bar",
           "orbs": "Game bar - beside the orbs"}
HUD = ("xpbar", "orbs")          # 2.65.0: fitted to the game's own bottom bar, in its look

# Where the game's bottom bar leaves room, as parts of the game window's height (PoE2 at 16:9, UI scale 100 %;
# the orbs' panels are anchored to the left and right edges, the XP bar runs between them). (x0, x1, bottom, h)
#   x0 / x1 >= 0: from the left edge, < 0: from the right edge; bottom: up from the bottom edge.
HUD_SPOTS = {"xpbar": [(0.535, -0.535, 0.0205, 0.026)],
             "orbs": [(0.215, 0.525, 0.138, 0.046), (-0.525, -0.215, 0.138, 0.046)]}
# 2.66.0 (feedback: too wide): beside the orbs each half is only as wide as what it shows, from the orb's side
SHORT = {"breach": "Brch", "delirium": "Deli", "ritual": "Ritl", "remnant": "Remn"}
PANEL_W, MINI_W = 290, 224


class _Short(CanvasText):
    """Minimal: the helper's short name (Ritual's live count stays: 2/3)."""
    key = ""

    def config(self, **kw):
        if "text" in kw:
            t = kw["text"]
            kw["text"] = t.split(" ", 1)[1] if (" " in t and "/" in t) else SHORT.get(self.key, t)
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


class MergedOverlay:
    """Mixed into App (with TrackerPage, which builds the separate windows)."""

    # ---------------------------------------------------------------- settings
    def merged_on(self):
        """2.59.0: always one window - the separate windows of 2.54 are gone."""
        return True

    def merged_layout(self):
        v = self.tracker_cfg().get("layout", "panel")
        return v if v in LAYOUTS else "panel"

    def merged_embeds_notes(self):
        """Notes sit inside the window (Panel, not Minimal); else the note opens as its own window under it."""
        return self.merged_on() and self.merged_layout() == "panel"

    def hud_spots(self, layout=None):
        """2.65.0: the Game bar windows' places -> [(x, y, w, h)]: fitted to the game window (or the main screen),
        or where you dragged them (Settings › Appearance › Fit to the game puts them back)."""
        layout = layout or self.merged_layout()
        from .alerts_page import game_rect
        r = game_rect()
        if r is None:
            r = (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        gx, gy, gw, gh = r
        self._hud_k = max(0.8, min(1.6, gh / 1080))
        saved = (self.tracker_cfg().get("hud_pos") or {}).get(layout) or []
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
        return {"timer": bool(getattr(self, "mg_timer", False)),
                "helpers": bool(self.tracker_cfg().get("alerts_bar", True)),
                "notes": self.merged_embeds_notes() and bool(oc.get("notes_enabled")) and bool(oc.get("notes_visible"))}

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
            cfg["layout"] = layout
        self.tracker_save()
        self.mg_timer = timer
        self.merged_build()
        if notes_on and not self.merged_embeds_notes():
            self.overlay.show_notes()

    # ---------------------------------------------------------------- the window
    def merged_destroy(self):
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
        """(Re)build the one window from what's on. -> the window, or None when nothing is on."""
        cfg = self.tracker_cfg()
        self.merged_destroy()
        want = self.merged_wants()
        self.mg_built = dict(want)
        if not any(want.values()):
            return None
        if self.merged_layout() in HUD:                     # 2.65.0
            return self._mg_hud_build(want)
        P = pal()
        self.mg_P = P
        self._hud_k = 1.0
        strip, mini = self.merged_layout() == "strip", self.merged_layout() == "minimal"
        compact = strip or mini
        x, y = cfg.get("mx", cfg.get("x", 60)), cfg.get("my", cfg.get("y", 260))
        if strip and "mx" not in cfg:
            x, y = 400, 0
        notes = want["notes"]
        title = "Session" if want["timer"] else ("Mechanic Helper" if want["helpers"] else "Notes")

        def moved(nx, ny, ww, hh):
            cfg.update(mx=nx, my=ny)
            if notes:
                cfg.update(mw=ww, mh=hh)
            if strip:                                       # 2.56.1: the strip's own width
                cfg["sw"] = ww
            self.tracker_save()

        def lock(on):
            self.overlay_lock(on)
        geo = (x, y, cfg.get("mw", PANEL_W) if notes else None, cfg.get("mh", 420) if notes else None)
        w = OverlayWindow(self.root, title, "⏱", geo, opacity=int(cfg.get("opacity", 225)),
                          locked=bool(cfg.get("mlocked")), min_size=(220, 200) if notes else (120, 30),
                          on_close=self.merged_close, on_lock=lock, on_moved=moved, follow_game=True,
                          no_activate=not notes, resizable=notes or strip, titlebar=not compact,
                          resize_axes="x" if strip else "xy")
        w.withdraw()
        self.mg_win = w
        cv = w.canvas_body()
        self.tk_ov_cv = cv
        self.tk_ov_lbls, self.tk_ov_alerts, self.tk_ov_clock = {}, {}, None
        if not cfg.get("mlocked"):
            w.draggable(cv)
        if strip:
            self._mg_strip(w, cv, P, want)
        elif mini:
            self._mg_mini(w, cv, P, want)
        else:
            self._mg_panel(w, cv, P, want)
        self.tk_overlay = w if want["timer"] else None
        self.tk_helpers = None
        self.tracker_overlay_draw(self.tracker_numbers())
        self.tracker_helpers_paint()
        if strip:
            w.min_size = (getattr(self, "mg_strip_min", 300), 30)
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
        if ww > r - l_ and self.merged_layout() == "strip":
            ww = max(getattr(self, "mg_strip_min", 300), r - l_)
            cfg["sw"] = ww
            w.geometry(f"{ww}x{hh}")
        nx, ny = max(l_, min(x, r - ww)), max(t, min(y, b - hh))
        if (nx, ny) != (x, y):
            w.geometry(f"+{nx}+{ny}")
            cfg.update(mx=nx, my=ny)
            self.tracker_save()

    def merged_close(self):
        """× on the one window: everything in it goes (the timer, the switches' bar, the note) - each comes back from
        its own place (Show timer, Overlays › Mechanic Helper, the notes key)."""
        cfg = self.tracker_cfg()
        cfg["overlay"] = False
        cfg["alerts_bar"] = False
        if getattr(self, "al_bar", None) is not None:
            self.al_bar.set(False)
        self.mg_timer = False
        if self.overlay.cfg.get("notes_visible"):
            self.overlay.cfg["notes_visible"] = False
            self.overlay.save_settings()
        self.tracker_save()
        self.merged_destroy()
        if getattr(self, "tk_ov_btn", None) is not None:
            self.tk_ov_btn.config(text="Show timer")
        self._say("Overlay closed. Show it again from Overlays (Show timer, Mechanic Helper, or the notes key).", 8)

    # ---------------------------------------------------------------- pieces
    def _mg_halo(self, P):
        return P.get("halo") if P.get("texture") else None

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
            lab = cv.create_text(x0 + 13 + self._hf(13), mid, text=k.title(), anchor="w", fill=P["text"],
                                 font=label_font or (P["font"], 10, "bold" if not P.get("caps") else "normal"),
                                 tags=("mg", tag))
        cv.tag_bind(tag, "<Button-1>", lambda e, k=k: self.tracker_helper_click(k))
        cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
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
        for txt, cmd, tag in (("🔒" if locked else "🔓", lambda: w._toggle_lock(), "mg_lock"),):
            cv.create_text(x, y, text=txt, anchor="e", fill=P["muted"], font=("Segoe UI Symbol", 10, "bold"),
                           tags=("mg", tag))
            cv.tag_bind(tag, "<Button-1>", lambda e, c=cmd: c())
            cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
            cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
            x -= 20
        return x

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

    # ---------------------------------------------------------------- Panel
    def _mg_panel(self, w, cv, P, want):
        cfg = self.tracker_cfg()
        f_big, f_row = (P["font"], 20, "bold"), (P["font"], 10)
        st = {"notes_win": None}

        def draw(W, H):
            cv.delete("mg")
            self.tk_ov_lbls, self.tk_ov_alerts = {}, {}
            y = 8
            if want["timer"]:
                self._mg_text(cv, P, 12, y, "session", f_big, fill=P["big"], anchor="nw")
                if cfg.get("clock", True):
                    self._mg_clock(w, cv, P, W - 12, y + 4, on_bar=P["align"] != "center" and not P.get("plate"))
                y += 40
                rows = []
                if cfg["lines"].get("map"):
                    rows.append(("map", "where"))
                if cfg["lines"].get("maps") or cfg["lines"].get("avg"):
                    rows.append(("maps" if cfg["lines"].get("maps") else None, "avg" if cfg["lines"].get("avg") else None))
                for left, right in rows:
                    if left:
                        self._mg_text(cv, P, 12, y, left, f_row)
                    if right:
                        self._mg_text(cv, P, W - 12, y, right, f_row, anchor="e")
                    y += 20
                y += 6
            if want["helpers"]:
                if want["timer"] or want["notes"]:
                    self._mg_header(cv, P, 12, y, W - 24, "Mechanics", "⚙", self.tracker_helpers_settings)
                    y += 14
                cw, ch, gap = (W - 24 - 6) // 2, 30, 6
                for i, k in enumerate(self.HELPERS):
                    cx, cy = 12 + (i % 2) * (cw + gap), y + (i // 2) * (ch + gap)
                    self._mg_cell(cv, P, k, cx, cy, cx + cw, cy + ch)
                y += 2 * (ch + gap) + 4
            if want["notes"]:
                self._mg_header(cv, P, 12, y, W - 24, "Notes", "Hide", self.overlay.hide_notes)
                y += 12
                st["notes_y"] = y
                if st["notes_win"] is None:
                    st["notes_win"] = cv.create_window(12, y, window=self._mg_notes_frame(cv, P), anchor="nw")
                cv.coords(st["notes_win"], 12, y)
                cv.itemconfigure(st["notes_win"], width=max(40, W - 24), height=max(40, H - y - 10))
            st["h"] = y
            self.tracker_overlay_draw(self.tracker_numbers())
            self.tracker_helpers_paint()
            return y

        h = draw(PANEL_W if not want["notes"] else int(cfg.get("mw", PANEL_W)), 400)
        if not want["notes"]:
            cv.configure(width=PANEL_W, height=h + 4)
        last = {"wh": None}

        def on_cfg(e):
            if (e.width, e.height) != last["wh"] and e.width > 50:
                last["wh"] = (e.width, e.height)
                draw(e.width, e.height)
        cv.bind("<Configure>", on_cfg, add="+")

    def _mg_notes_frame(self, cv, P):
        """The note inside the panel: the Overlay's own tabs and text, so typing, tabs and saving work as before."""
        ov = self.overlay
        bg, fg = ov.note_colours()
        host = tk.Frame(cv, bg=bg, highlightthickness=1, highlightbackground=P["line"])
        ov.notes_tabbar = tk.Frame(host, bg=bg)
        ov.notes_tabbar.pack(fill="x")
        text = tk.Text(host, bg=bg, fg=fg, insertbackground=fg, relief="flat", highlightthickness=0, wrap="word",
                       font=(P["font"], int(ov.cfg.get("notes_font", 11))), padx=8, pady=4, spacing1=2, spacing3=2)
        text.pack(fill="both", expand=True)
        tabs, i = ov.note_tabs(), ov.note_index()
        text.insert("1.0", tabs[i]["text"])
        text.edit_modified(False)
        text.bind("<<Modified>>", ov._text_changed)
        ov.notes_text = text
        self.mg_notes_in = True
        ov._paint_tabs()
        return host

    # ---------------------------------------------------------------- Minimal
    def _mg_mini(self, w, cv, P, want):
        cfg = self.tracker_cfg()
        W = MINI_W
        y = 8
        gx = self._mg_glyphs(w, cv, P, W - 8, 14)
        if want["timer"]:
            self._mg_text(cv, P, 12, y, "session", (P["font"], 20, "bold"), fill=P["big"], anchor="nw")
            if cfg.get("clock", True):
                self._mg_clock(w, cv, P, gx - 4, 14, anchor="e", on_bar=False)
                self.tk_ov_clock.config = (lambda f: (lambda text="", **kw: f(text=text.splitlines()[0]
                                                                             if text else "")))(self.tk_ov_clock.config)
            y += 44
            self._mg_text(cv, P, 12, y, "map", (P["font"], 10))
            self._mg_text(cv, P, W - 12, y, "where", (P["font"], 9), fill=P["muted"], anchor="e")
            y += 14
        if want["helpers"]:
            cv.create_line(12, y, W - 12, y, fill=P["line"], tags=("mg",))
            y += 4
            cw = (W - 24) // 4
            for i, k in enumerate(self.HELPERS):
                self._mg_cell(cv, P, k, 12 + i * cw, y, 12 + (i + 1) * cw - 2, y + 38, label_cls=_Short,
                              label_font=(P["font"], 8), icon_only_row=True)
            y += 42
        if self.overlay.cfg.get("notes_enabled"):
            self._mg_notes_button(w, cv, P, W - 12, y + 6)
            y += 16
        cv.configure(width=W, height=y + 6)

    # ---------------------------------------------------------------- Strip
    def _mg_strip_widths(self, cv, P, want):
        """The strip's parts at their smallest (2.56.1: the minimum width shows all of it). -> {part: px}."""
        cfg = self.tracker_cfg()
        f = tkfont.Font(root=cv, family=P["font"], size=10)
        hf = tkfont.Font(root=cv, family=P.get("hfont") or P["font"], size=9, weight="bold")
        fbig = tkfont.Font(root=cv, family=P["font"], size=15, weight="bold")
        fb = tkfont.Font(root=cv, family=P["font"], size=9)
        wd = {}
        if want["timer"]:
            wd["title"] = hf.measure("SESSION") + 10
            wd["time"] = max(fbig.measure("0:00:00"), fbig.measure("not tracking")) + 14
            wd["map"] = f.measure("Map  00:00") + 10
            wd["where"] = f.measure("Mmmmmmm") + 10                 # grows with the strip
            if cfg["lines"].get("maps") or cfg["lines"].get("avg"):
                wd["maps"] = f.measure("Maps  000") + 8 + f.measure("Avg  00:00") + 12
        if want["helpers"]:
            wd["cells"] = sum(fb.measure("Ritual 3/3" if k == "ritual" else k.title()) + 40 for k in self.HELPERS) + 38
        if self.overlay.cfg.get("notes_enabled"):
            wd["notes"] = fb.measure("NOTES  Mmmmmm  ▾") + 12              # grows with the strip
        wd["right"] = (f.measure("00:00 PM") + 14 if want["timer"] and cfg.get("clock", True) else 0) + 56
        return wd

    def _mg_strip(self, w, cv, P, want):
        """2.56.1: as wide as you drag it (from its left / right edge while unlocked), never narrower than what it
        shows; the area name and the note's first line get the room."""
        cfg = self.tracker_cfg()
        H, mid = 40, 20
        wd = self._mg_strip_widths(cv, P, want)
        min_w = 14 + sum(wd.values()) + 24
        self.mg_strip_min = min_w
        W0 = max(min_w, int(cfg.get("sw") or min_w + 220))

        def sep(xx):
            cv.create_line(xx, 8, xx, H - 8, fill=P["line"], tags=("mg",))

        def draw(W):
            cv.delete("mg")
            self.tk_ov_lbls, self.tk_ov_alerts = {}, {}
            W = max(W, min_w)
            extra = W - min_w
            grow_where = min(extra // 3, 120) if "where" in wd else 0
            grow_notes = extra - grow_where if "notes" in wd else 0
            fch = tkfont.Font(root=cv, family=P["font"], size=10).measure("m") or 8
            x = 14
            if want["timer"]:
                t = "SESSION" if (P.get("caps") or P.get("rules")) else "Session"
                cv.create_text(x, mid, text=t, anchor="w", fill=P["head"],
                               font=(P.get("hfont") or P["font"], 9, "bold"), tags=("mg",))
                x += wd["title"]
                self._mg_text(cv, P, x, mid, "session", (P["font"], 15, "bold"), fill=P["big"])
                x += wd["time"]
                sep(x)
                x += 14
                self._mg_text(cv, P, x, mid, "map", (P["font"], 10))
                x += wd["map"]
                where = self._mg_text(cv, P, x, mid, "where", (P["font"], 10), fill=P["muted"], cls=_Trunc)
                where.limit = max(6, int((wd["where"] + grow_where - 10) / (fch * 0.8)))
                x += wd["where"] + grow_where
                if "maps" in wd:
                    fm = tkfont.Font(root=cv, family=P["font"], size=10)
                    self._mg_text(cv, P, x, mid, "maps", (P["font"], 10))
                    self._mg_text(cv, P, x + fm.measure("Maps  000") + 8, mid, "avg", (P["font"], 10))
                    x += wd["maps"]
                sep(x)
                x += 10
            if want["helpers"]:
                fb = tkfont.Font(root=cv, family=P["font"], size=9)
                for k in self.HELPERS:
                    cw = fb.measure("Ritual 3/3" if k == "ritual" else k.title()) + 34
                    self._mg_cell(cv, P, k, x, 7, x + cw, H - 7, label_font=(P["font"], 9))
                    x += cw + 6
                cv.create_text(x + 4, mid, text="\u2699", anchor="w", fill=P["muted"], font=("Segoe UI Symbol", 11),
                               tags=("mg", "mg_cog"))
                cv.tag_bind("mg_cog", "<Button-1>", lambda e: self.tracker_helpers_settings())
                x += 26
                sep(x)
                x += 12
            if "notes" in wd:
                self._mg_notes_button(w, cv, P, x, mid, anchor="w", peek=True,
                                      chars=max(6, int((wd["notes"] + grow_notes) / (fch * 0.75)) - 10))
            gx = self._mg_glyphs(w, cv, P, W - 8, mid)
            if want["timer"] and cfg.get("clock", True):
                self._mg_clock(w, cv, P, gx - 6, mid, anchor="e", on_bar=False)
                self.tk_ov_clock.config = (lambda fn: (lambda text="", **kw: fn(text=text.splitlines()[0]
                                                                                if text else "")))(self.tk_ov_clock.config)
            if getattr(self, "tk_overlay", None) is not None or want["timer"]:
                self.tk_overlay = w if want["timer"] else None
                self.tracker_overlay_draw(self.tracker_numbers())
            self.tracker_helpers_paint()
        draw(W0)
        cv.configure(width=W0, height=H)
        last = {"w": W0}

        def on_cfg(e):
            if e.width != last["w"] and e.width > 50:
                last["w"] = e.width
                draw(e.width)
        cv.bind("<Configure>", on_cfg, add="+")

    # ---------------------------------------------------------------- 2.65.0: Game bar (on the XP bar / beside the orbs)
    def _mg_hud_build(self, want):
        """One window resting on the XP bar, or two - right of the life orb (the timer) and left of the mana orb
        (the switches, Notes, the clock) - in the game's own bar look. Fitted to the game window; drag them while
        unlocked if your UI scale puts the bar elsewhere."""
        cfg = self.tracker_cfg()
        layout = self.merged_layout()
        P = pal()
        self.mg_P = P
        spots = self.hud_spots(layout)
        if layout == "orbs":                                # 2.66.0: as wide as what each half shows
            spots = self._hud_snug(spots, want, P)
        parts = [("all", spots[0])] if layout == "xpbar" else [("timer", spots[0]), ("rest", spots[1])]
        if layout == "orbs" and not want["timer"]:
            parts = [("rest", spots[1])]
        elif layout == "orbs" and not want["helpers"] and not self.overlay.cfg.get("notes_enabled"):
            parts = [("timer", spots[0])]
        self.tk_ov_lbls, self.tk_ov_alerts, self.tk_ov_clock, self.tk_ov_cv = {}, {}, None, None
        wins = []
        for part, (x, y, ww, hh) in parts:
            slot = 0 if part in ("all", "timer") else 1

            def moved(nx, ny, _w, _h, slot=slot):
                pos = cfg.setdefault("hud_pos", {}).setdefault(layout, [None] * len(HUD_SPOTS[layout]))
                while len(pos) < len(HUD_SPOTS[layout]):
                    pos.append(None)
                pos[slot] = [nx, ny]
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
            if part == "all":
                self._hud_row(w, cv, P, want, W, H)
            elif part == "timer":
                self._hud_timer(cv, P, W, H)
            else:
                self._hud_rest(w, cv, P, want, W, H)
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

    def _hf(self, n):
        """A font size for the Game bar, grown with the game window (made for 1080 px high)."""
        return max(7, round(n * getattr(self, "_hud_k", 1.0)))

    def _hud_snug(self, spots, want, P):
        """Beside the orbs: each half's width from its content, kept against its orb (left half grows right, the
        right half grows left)."""
        from . import hudart
        cfg = self.tracker_cfg()
        fm = tkfont.Font(root=self.root, family=P["font"], size=self._hf(10))
        fb = tkfont.Font(root=self.root, family=P["font"], size=self._hf(13), weight="bold")
        out = []
        for i, (x, y, w, h) in enumerate(spots):
            m = 2 * (hudart.cap_width(h) + 8)
            if i == 0:
                need = max(max(fb.measure("0:00:00"), fb.measure("not tracking")) + 16 + fm.measure("Avg  00:00"),
                           fm.measure("Map  00:00") + 8 + fm.measure("Mmmmm") + 8 + fm.measure("Maps  00"))
            else:
                side = max(fm.measure("00:00 PM"), fm.measure("Notes  ▾") + 22) + 8
                cells = (2 * max(56, max(self._hud_cell_w_root(P, k) for k in self.HELPERS)) + 5 + 12
                         if want["helpers"] else 0)
                need = side + cells
            nw = int(min(w, max(need + m, 0.13 * h / 0.046)))
            saved = ((cfg.get("hud_pos") or {}).get("orbs") or [None, None])
            moved = i < len(saved) and saved[i]
            if i == 1 and not moved:
                x = x + w - nw
            out.append((x, y, nw, h))
        return out

    def _hud_cell_w_root(self, P, k):
        fb = tkfont.Font(root=self.root, family=P["font"], size=self._hf(9))
        return fb.measure(SHORT[k]) + 16 + self._hf(12)

    def _hud_frame(self, cv, P, W, H):
        """The game bar's plate (hudart: carved stone, bevelled bronze frame, end caps with an amber gem, a
        recessed well). -> the left / right edges of the well, where content goes."""
        from . import hudart
        img = hudart.plate(cv, W, H, P)
        m = hudart.cap_width(H) + 8
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

    def _hud_sep(self, cv, P, x, H):
        from . import hudart
        img = hudart.divider(cv, max(10, H - 14), P)
        if img is not None:
            cv.create_image(x, H // 2, image=img, tags=("mg",))
        else:
            cv.create_line(x, 7, x, H - 7, fill=P["line"], tags=("mg",))

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
        lab = cv.create_text(x0 + 9 + self._hf(12), mid, text=k.title(), anchor="w", fill=P["text"], font=font,
                             tags=("mg", tag))
        cv.tag_bind(tag, "<Button-1>", lambda e, k=k: self.tracker_helper_click(k))
        cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
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
        return fb.measure(SHORT[k] if short else ("Ritual 3/3" if k == "ritual" else k.title())) + 16 + self._hf(12)

    def _hud_cells(self, cv, P, x, y0, y1, short, cols=4, cw=None):
        """The four switches in a row (short names when space is tight) or a 2 x 2 grid. -> right edge."""
        lc, font = (_Short if short else CanvasText), (P["font"], self._hf(9))
        if cols == 4:
            for k in self.HELPERS:
                w_ = self._hud_cell_w(cv, P, k, short)
                self._hud_cell(cv, P, k, x, y0, x + w_, y1, lc, font)
                x += w_ + 4
            return x
        rh = (y1 - y0 - 4) // 2
        for i, k in enumerate(self.HELPERS):
            cx, cy = x + (i % 2) * (cw + 5), y0 + (i // 2) * (rh + 4)
            self._hud_cell(cv, P, k, cx, cy, cx + cw, cy + rh, lc, font)
        return x + 2 * cw + 5

    def _hud_clock(self, w, cv, P, x, y):
        self._mg_clock(w, cv, P, x, y, anchor="e", on_bar=False)
        self.tk_ov_clock.config = (lambda fn: (lambda text="", **kw: fn(text=text.splitlines()[0]
                                                                        if text else "")))(self.tk_ov_clock.config)

    def _hud_row(self, w, cv, P, want, W, H):
        """On the XP bar: one line - time | map | maps · avg | switches | Notes ▾ ... clock 🔒."""
        cfg = self.tracker_cfg()
        lft, rgt = self._hud_frame(cv, P, W, H)
        mid = H // 2 + 1
        f = (P["font"], self._hf(10))
        fm = tkfont.Font(root=cv, family=P["font"], size=self._hf(10))
        gx = self._mg_glyphs(w, cv, P, rgt, mid)
        right = gx
        if want["timer"] and cfg.get("clock", True):
            self._hud_clock(w, cv, P, gx - 2, mid)
            right = gx - fm.measure("00:00 PM") - 12
        x = lft
        cy0, cy1 = 7, H - 7
        if want["timer"]:
            self._mg_text(cv, P, x, mid, "session", (P["font"], self._hf(13), "bold"), fill=P["big"])
            fb_ = tkfont.Font(root=cv, family=P["font"], size=self._hf(13), weight="bold")
            x += max(fb_.measure("0:00:00"), fb_.measure("not tracking")) + 10
            self._hud_sep(cv, P, x, H)
            x += 12
            self._mg_text(cv, P, x, mid, "map", f)
            x += fm.measure("Map  00:00") + 8
            need_rest = (fm.measure("Maps  000") + fm.measure("Avg  00:00") + 24 if (
                cfg["lines"].get("maps") or cfg["lines"].get("avg")) else 0)
            cells_w = sum(self._hud_cell_w(cv, P, k, True) + 4 for k in self.HELPERS) + 24 if want["helpers"] else 0
            notes_w = fm.measure("Notes  ▾") + 16 if self.overlay.cfg.get("notes_enabled") else 0
            where_w = right - x - need_rest - cells_w - notes_w - 24
            if where_w > 40:
                wt = self._mg_text(cv, P, x, mid, "where", f, fill=P["muted"], cls=_Trunc)
                wt.limit = max(4, int(where_w / ((fm.measure("m") or 8) * 0.8)))
                x += where_w
            if need_rest:
                self._mg_text(cv, P, x, mid, "maps", f)
                self._mg_text(cv, P, x + fm.measure("Maps  000") + 8, mid, "avg", f)
                x += need_rest - 10
            self._hud_sep(cv, P, x, H)
            x += 12
        if want["helpers"]:
            x = self._hud_cells(cv, P, x, cy0, cy1, short=True)
            self._hud_sep(cv, P, x + 4, H)
            x += 14
        if self.overlay.cfg.get("notes_enabled") and x < right - 40:
            self._mg_notes_button(w, cv, P, x, mid, anchor="w")

    def _hud_timer(self, cv, P, W, H):
        """Right of the life orb: the time and Avg on top, a rule, then the map, where you are and Maps."""
        cfg = self.tracker_cfg()
        lft, rgt = self._hud_frame(cv, P, W, H)
        top, low = H * 0.36, H * 0.70
        self._mg_text(cv, P, lft, top, "session", (P["font"], self._hf(13), "bold"), fill=P["big"])
        fm = tkfont.Font(root=cv, family=P["font"], size=self._hf(10))
        if cfg["lines"].get("avg"):
            self._mg_text(cv, P, rgt, top, "avg", (P["font"], self._hf(10)), anchor="e")
        self._hud_rule(cv, P, lft, rgt, H * 0.53)
        end = rgt
        if cfg["lines"].get("maps"):
            self._mg_text(cv, P, rgt, low, "maps", (P["font"], self._hf(10)), anchor="e")
            end = rgt - fm.measure("Maps  00") - 8
        if cfg["lines"].get("map", True):
            self._mg_text(cv, P, lft, low, "map", (P["font"], self._hf(10)))
            x = lft + fm.measure("Map  00:00") + 8
            if end - x > 30:
                wt = self._mg_text(cv, P, x, low, "where", (P["font"], self._hf(10)), fill=P["muted"], cls=_Trunc)
                wt.limit = max(4, int((end - x) / ((fm.measure("m") or 8) * 0.8)))

    def _hud_rule(self, cv, P, x0, x1, y):
        """A thin bronze rule that fades out at both ends, a small lozenge in the middle."""
        from .themes import mix
        n = 24
        seg = (x1 - x0) / n
        for i in range(n):
            a = 1 - abs((i + 0.5) / n - 0.5) * 2
            cv.create_line(x0 + i * seg, y, x0 + (i + 1) * seg, y, fill=mix(P["bg"], P["rim"], a ** 0.7), tags=("mg",))
        cx = (x0 + x1) / 2
        cv.create_polygon(cx, y - 3, cx + 3, y, cx, y + 3, cx - 3, y, fill=P["rim"], outline=P["rim_lo"], tags=("mg",))

    def _hud_rest(self, w, cv, P, want, W, H):
        """Left of the mana orb: the four switches (2 x 2), then Notes, the clock and the lock."""
        cfg = self.tracker_cfg()
        lft, rgt = self._hud_frame(cv, P, W, H)
        fm = tkfont.Font(root=cv, family=P["font"], size=self._hf(10))
        side = max(fm.measure("00:00 PM"), fm.measure("Notes  ▾") + 22) + 8
        top, low = H * 0.36, H * 0.70
        gx = self._mg_glyphs(w, cv, P, rgt, low)
        if want["timer"] and cfg.get("clock", True):
            self._hud_clock(w, cv, P, rgt, top)
        if self.overlay.cfg.get("notes_enabled"):
            self._mg_notes_button(w, cv, P, gx - 2, low, anchor="e")
        if want["helpers"]:
            cw = max(56, (rgt - lft - side - 12 - 5) // 2)
            x = self._hud_cells(cv, P, lft, 9, H - 9, short=cw < 86, cols=2, cw=cw)
            self._hud_sep(cv, P, x + 4, H)
