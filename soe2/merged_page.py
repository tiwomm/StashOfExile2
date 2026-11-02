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

LAYOUTS = {"panel": "Panel", "strip": "Strip"}
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
        return self.merged_on() and self.merged_layout() == "panel" and not pal().get("minimal")

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
            cfg["layout"] = layout
        self.tracker_save()
        self.mg_timer = timer
        self.merged_build()
        if notes_on and not self.merged_embeds_notes():
            self.overlay.show_notes()

    # ---------------------------------------------------------------- the window
    def merged_destroy(self):
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
        P = pal()
        strip, mini = self.merged_layout() == "strip", bool(P.get("minimal"))
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
        for win in (w, note):
            if win is None:
                continue
            try:
                win.hide() if self.mg_hidden else win.show()
            except tk.TclError:
                pass
        if not self.mg_hidden and w is not None:
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
            dot = cv.create_text(x0 + 13, mid, text=P["off_icon"], fill=P["off"], font=("Segoe UI Symbol", 11),
                                 tags=("mg", tag))
            lab = cv.create_text(x0 + 26, mid, text=k.title(), anchor="w", fill=P["text"],
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
        clk = cv.create_text(x, y, text="", anchor=anchor, fill=P["muted"], font=(P["font"], 9), justify="right",
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
        cv.create_text(x, y, text=txt, anchor=anchor, fill=P["muted"], font=(P["font"], 9), tags=("mg", "mg_notes"))
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
            w = getattr(self, "mg_win", None)
            try:
                if w is not None and w.winfo_ismapped():
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
