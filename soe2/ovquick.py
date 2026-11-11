"""P4 (2.108.0, feedback: "a mini settings page over the game when we right click the cog wheel"): right-click the
overlay's ⚙ = Quick settings, a small box over the game, above the cog and on the game's monitor. (2.119.0: either
click - All settings… in it opens the full Overlay ↳ Settings in the app.) Style (2.110.0 - the Overlay ON | OFF switch is gone from here), Sound,
Lock position, Click-through (2.120.1; Hide the overlay from screen captures is in Overlay ↳ Settings › Options), Helpers (2.118.0: each helper on / off - the bar has no switches for them any
more) and On the bar (the tools' menus). Esc, ✕, a click elsewhere or the cog again closes it.
GGG ToS: a window over the game; nothing is sent to the game."""
import tkinter as tk
from tkinter import ttk

from . import buglog
from .config import SETTINGS, save_json
from .style import Tooltip

# (label, key): the helpers switched on / off, then the tools' menus on the bar
QUICK_HELPERS = (("Breach", "breach"), ("Delirium", "delirium"), ("Ritual", "ritual"), ("Expedition", "remnant"),
                 ("Campaign", "campaign"), ("League Plan", "focus"), ("Whispers", "whispers"),
                 ("Top Up", "topup"), ("Breaks", "breaks"), ("Map profit", "mapprofit"), ("Temple", "temple"),
                 ("Desecration", "desecrate"))   # 2.131.1: every helper (2.132.1: Map profit, Temple)
BETA_HELPERS = {"desecrate": "desecrate"}      # (a chip only while its beta feature is on - Features)
QUICK_BAR = (("Notes", "notes"), ("Calc", "calc"), ("Regex", "regex"), ("Rates", "rates"))
# 2.124.0 (feedback: each toggle should say what it is on hover): the one-line tips (the helpers' come from
# alerts_page.HELPER_BLURBS - the same line as on Helpers)
QUICK_TIPS = {"Style": "How the overlay looks over the game",
              "Reload Overlay": "Reload Overlay: builds the overlay again - for when something looks stuck or wrong",
              "Layout": "Panel: a card you place anywhere. Bar: on the game's XP bar",
              "Sound": "Every helper's alert sound, on or off",
              "Lock position": "Keeps the overlay where it is - no dragging it by accident",
              "Place": "Where the overlay sits: the Bar on the XP bar or at the top, the Panel left or right. Picking "
                       "one puts it there, wherever you dragged it",
              "Click-through": "Clicks go through the overlay to the game",
              "notes": "Notes ▾ on the bar: your own notes in a window over the game",
              "calc": "Calc ▾ on the bar: a small calculator over the game",
              "regex": "Regex ▾ on the bar: your saved stash searches, one click to copy",
              "rates": "Rates ▾ on the bar: today's currency exchange rates"}


class OverlayQuick:
    """Mixed into App."""

    # ---------------------------------------------------------------- the one Sound (shared with Overlay ↳ Settings)
    def helpers_sound_set(self, on):
        """Every helper's alert sound on or off (the Sound switch here and on Overlay ↳ Settings › Helpers)."""
        on = bool(on)
        SETTINGS["helpers_sound"] = on
        try:
            self.breach_cfg()["sound"] = on
            self.ritual_cfg()["sound"] = on
        except Exception:
            buglog.caught()
        save_json("settings.json", SETTINGS)
        try:
            from . import whispers as _W
            _W.cfg()["sound"] = on
            _W.save()
        except Exception:
            buglog.caught()
        try:
            from .utilities import DELIRIUM
            DELIRIUM.set_sound(on)
        except Exception:
            buglog.caught()
        for key in ("delirium", "breach", "ritual", "whispers"):
            r = (getattr(self, "al_rows", None) or {}).get(key)
            if r is not None:
                r["sound"].set(on)
        v = getattr(self, "al_sound_all", None)
        if v is not None and bool(v.get()) != on:
            v.set(on)

    # ---------------------------------------------------------------- what's on the bar
    def quick_bar_on(self, key):
        b = self.bar_cfg()
        if key == "notes":
            return self.notes_on_bar()
        if key == "calc":
            return self.calc_on_bar()
        if key == "rates":
            return bool(self.ovr_cfg()["on"])
        if key in [k for _l, k in QUICK_HELPERS]:
            return self.alert_states().get(key, "off") != "off"
        return bool(b.get(key, True))

    def quick_bar_set(self, key, on):
        on = bool(on)
        if key in [k for _l, k in QUICK_HELPERS]:                 # 2.118.0: a helper itself, on / off
            try:
                self.alerts_toggle(key, on)
            except Exception:
                self.log_error(f"switching {key} from Quick settings")
            return None
        b = self.bar_cfg()
        if key == "rates":
            self.ovr_switch(on)
        elif key == "notes":
            b["notes"] = on
            self.overlay.cfg["notes_choice"] = True
            self.overlay.set_notes(on)
        elif key == "calc":
            b["calc"] = on
            self.calc_cfg()["on"] = on
            if not on:
                self.calc_ov_close(remember=False)
            self.calc_save()
        else:
            b[key] = on
            if key == "regex" and not on:
                self.rx_ov_close()
        self.tracker_save()
        try:
            self.tracker_helpers_sync()
        except Exception:
            buglog.caught()
        v = (getattr(self, "tk_bar_vars", None) or {}).get(key)
        if v is not None and bool(v.get()) != on:
            v.set(on)
        self.merged_build()

    # ---------------------------------------------------------------- the box
    def ov_quick_toggle(self, e=None):
        if getattr(self, "ov_quick_win", None) is not None:
            return self.ov_quick_close()
        self.ov_quick_show(e)

    def ov_quick_close(self, _e=None):
        w, self.ov_quick_win = getattr(self, "ov_quick_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def ov_quick_style(self):
        """2.125.1 (feedback: "Quick settings cog UI needs to match the style chosen"): its colors and type from the
        overlay's style (the app theme's before)."""
        from .overlaywin import pal
        P = pal()
        return {"bg": P["bg"], "band": P.get("band") or P.get("field") or P["bg"], "text": P["text"],
                "muted": P["muted"], "line": P["line"],
                "accent": P["head"] if P.get("poe") else (P.get("accent") or P["head"]),     # (Classic: its gold)
                "field": P.get("cell_bg") or P.get("field") or P["bg"], "font": P.get("font") or "Segoe UI",
                "hfont": P.get("hfont") or P.get("font") or "Segoe UI"}

    def ov_quick_show(self, e=None):
        self.ov_quick_close()
        Q = self.ovq_P = self.ov_quick_style()
        P1, P2, F = Q["bg"], Q["band"], Q["font"]
        w = tk.Toplevel(self.root, bg=Q["line"])
        w.withdraw()
        w.overrideredirect(True)
        try:
            w.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.ov_quick_win = w
        box = tk.Frame(w, bg=P1, padx=0, pady=0)
        box.pack(padx=1, pady=1)
        head = tk.Frame(box, bg=P2, padx=12, pady=8, highlightthickness=0)
        head.pack(fill="x")
        tk.Label(head, text="Quick settings", bg=P2, fg=Q["text"], font=(Q["hfont"], 12, "bold")).pack(side="left")
        x = tk.Label(head, text="✕", bg=P2, fg=Q["muted"], font=(F, 11), cursor="hand2", padx=4)
        x.pack(side="right")
        x.bind("<Button-1>", lambda _e: self.ov_quick_close())
        Tooltip(x, "Close")
        tk.Frame(box, bg=Q["accent"], height=2).pack(fill="x")
        body = tk.Frame(box, bg=P1, padx=12, pady=8)
        body.pack(fill="x")
        self.ovq_vars = {}

        def row(label, value, fn):
            v = tk.BooleanVar(value=bool(value))
            cb = tk.Checkbutton(body, text=label, variable=v, command=lambda: fn(bool(v.get())), bg=P1, fg=Q["text"],
                                activebackground=P1, activeforeground=Q["text"], selectcolor=Q["field"],
                                font=(F, 10), anchor="w", highlightthickness=0, bd=0)
            cb.pack(anchor="w", pady=2)
            Tooltip(cb, QUICK_TIPS.get(label, ""))
            self.ovq_vars[label] = v
            return v
        cfg = self.tracker_cfg()
        # 2.110.0 (feedback): no Overlay ON | OFF here - the overlay's Style instead
        from .ovlight import STYLES
        srow = tk.Frame(body, bg=P1)
        srow.pack(fill="x", pady=(0, 8))
        tk.Label(srow, text="Style", bg=P1, fg=Q["text"], font=(F, 10)).pack(side="left")
        names = list(STYLES.values())
        self.ovq_style = tk.StringVar(value=STYLES.get(self.ov_look(), names[0]))
        cb = ttk.Combobox(srow, textvariable=self.ovq_style, values=names, state="readonly", width=24)
        cb.pack(side="right")
        cb.bind("<<ComboboxSelected>>", lambda _e: self._ovq_style())
        Tooltip(srow, QUICK_TIPS["Style"])
        # 2.124.1 (feedback: "quick settings needs a panel | bar toggle as well"): the Layout, as in Settings
        # (2.125.1: two chips in the overlay's style, the one in use with ✓)
        from .merged_page import LAYOUTS
        lrow = tk.Frame(body, bg=P1)
        lrow.pack(fill="x", pady=(0, 8))
        tk.Label(lrow, text="Layout", bg=P1, fg=Q["text"], font=(F, 10)).pack(side="left")
        self.ovq_layout_chips = {}
        for key in ("xpbar", "panel"):
            ch = tk.Label(lrow, font=(F, 9), padx=8, pady=4, cursor="hand2", highlightthickness=1)
            ch.pack(side="right", padx=(4, 0))
            ch.bind("<Button-1>", lambda _e, k=key: self._ovq_layout(LAYOUTS[k]))
            self.ovq_layout_chips[key] = ch
        self._ovq_layout_paint()
        Tooltip(lrow, QUICK_TIPS["Layout"])
        # 2.130.0 (feedback: "a dropdown on the cog to choose location ... top or bottom for the bar style, and left
        # or right for the panel style"): where it sits; picking one puts it there (wherever it was dragged)
        prow = tk.Frame(body, bg=P1)
        prow.pack(fill="x", pady=(0, 8))
        tk.Label(prow, text="Place", bg=P1, fg=Q["text"], font=(F, 10)).pack(side="left")
        opts = self.ov_spots()
        self.ovq_place = tk.StringVar(value=opts.get(self.ov_spot(), next(iter(opts.values()))))
        pc = ttk.Combobox(prow, textvariable=self.ovq_place, values=list(opts.values()), state="readonly", width=24)
        pc.pack(side="right")
        pc.bind("<<ComboboxSelected>>", lambda _e: self.ov_spot_set(
            next((k for k, v in self.ov_spots().items() if v == self.ovq_place.get()), None)))
        Tooltip(prow, QUICK_TIPS["Place"])
        self.ovq_place_box = pc
        row("Sound", SETTINGS.get("helpers_sound", True), self.helpers_sound_set)
        # 2.120.1: Lock position and Click-through, as in Options (Hide from captures is in Settings › Advanced)
        self.ovq_lock = row("Lock position", cfg.get("mlocked"), self._ovq_lock)
        self.ovq_ct = row("Click-through", self.click_through_on(), self.ov_click_through_set)
        self.ovq_chips = {}
        for title, items in (("HELPERS", QUICK_HELPERS), ("ON THE BAR", QUICK_BAR)):
            tk.Label(body, text=title, bg=P1, fg=Q["muted"], font=(F, 9, "bold"), anchor="w").pack(
                fill="x", pady=(8, 4))
            grid = tk.Frame(body, bg=P1)
            grid.pack(fill="x")
            from . import features as _FEAT
            items = [(lb, k) for lb, k in items if k not in BETA_HELPERS or _FEAT.on(BETA_HELPERS[k])]
            for i, (label, key) in enumerate(items):
                b = tk.Label(grid, text=label, font=(F, 9), padx=8, pady=4, cursor="hand2",
                             highlightthickness=1)
                b.grid(row=i // 4, column=i % 4, sticky="ew", padx=(0, 4), pady=(0, 4))
                b.bind("<Button-1>", lambda _e, k=key: self._ovq_chip(k))
                from .alerts_page import HELPER_BLURBS
                Tooltip(b, HELPER_BLURBS.get(key) or QUICK_TIPS.get(key, ""))
                b.label = label
                self.ovq_chips[key] = b
                self._ovq_paint(key)
        foot = tk.Frame(box, bg=P1, padx=12, pady=8)
        foot.pack(fill="x")
        allb = tk.Label(foot, text="All settings…", bg=Q["field"], fg=Q["text"], font=(F, 10), pady=4, cursor="hand2",
                        highlightthickness=1, highlightbackground=Q["line"])
        allb.pack(side="left", fill="x", expand=True)
        allb.bind("<Button-1>", lambda _e: (self.ov_quick_close(), self.overlay_settings_go()))
        # 2.125.3 (feedback: "a Reload Overlay button to reload the overlay if it has any issues")
        rl = tk.Label(foot, text="⟳", bg=Q["field"], fg=Q["text"], font=(F, 11), padx=8, pady=2, cursor="hand2",
                      highlightthickness=1, highlightbackground=Q["line"])
        rl.pack(side="left", padx=(8, 0), fill="y")
        rl.bind("<Button-1>", lambda _e: (self.ov_quick_close(), self.overlay_reload()))
        rl.bind("<Enter>", lambda _e: rl.config(highlightbackground=Q["accent"]))
        rl.bind("<Leave>", lambda _e: rl.config(highlightbackground=Q["line"]))
        Tooltip(rl, QUICK_TIPS["Reload Overlay"])
        self.ovq_reload = rl
        allb.bind("<Enter>", lambda _e: allb.config(highlightbackground=Q["accent"]))
        allb.bind("<Leave>", lambda _e: allb.config(highlightbackground=Q["line"]))
        w.bind("<Escape>", self.ov_quick_close)
        w.update_idletasks()
        ww, wh = w.winfo_reqwidth(), w.winfo_reqheight()
        x0, y0 = (e.x_root, e.y_root) if e is not None else (self.root.winfo_pointerx(), self.root.winfo_pointery())
        try:
            from .alerts_page import game_rect
            g = game_rect()
        except Exception:
            g = None
        if not g:
            g = (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        gx, gy, gw, gh = g
        x = min(max(gx, x0 - ww + 20), gx + gw - ww)              # (stays on the game's monitor)
        y = y0 - wh - 12 if y0 - wh - 12 >= gy else min(y0 + 16, gy + gh - wh)
        w.geometry(f"+{int(x)}+{int(y)}")
        w.deiconify()
        try:
            w.focus_force()
        except tk.TclError:
            pass
        w.bind("<FocusOut>", lambda _e: self.root.after(150, self._ovq_focus_gone))

    def _ovq_focus_gone(self):
        w = getattr(self, "ov_quick_win", None)
        if w is None:
            return
        try:                                     # 2.112.3: Tk's own name for the focus - a dropdown's open list
            f = str(w.tk.call("focus"))          # (".…combobox.popdown.f.l") isn't a tkinter widget, so focus_get()
        except tk.TclError:                      # failed, read as "focus left", and closed the box under the list
            f = ""
        if not f.startswith(str(w)):
            self.ov_quick_close()

    def _ovq_paint(self, key):
        b = (getattr(self, "ovq_chips", None) or {}).get(key)
        if b is None:
            return
        on = self.quick_bar_on(key)
        self._ovq_chip_look(b, on, getattr(b, "label", b.cget("text").lstrip("✓ ")))

    def _ovq_chip_look(self, b, on, label):
        """A chip in the overlay's style; on: ✓, the accent edge and the strong text (2.124.0: a mark and a word, not
        color alone)."""
        Q = getattr(self, "ovq_P", None) or self.ov_quick_style()
        try:
            b.config(text=("✓ " if on else "") + label, bg=Q["field"] if on else Q["bg"],
                     fg=Q["text"] if on else Q["muted"], highlightbackground=Q["accent"] if on else Q["line"])
        except tk.TclError:
            pass

    def _ovq_layout_paint(self):
        from .merged_page import LAYOUTS
        for key, ch in (getattr(self, "ovq_layout_chips", None) or {}).items():
            self._ovq_chip_look(ch, key == self.merged_layout(), LAYOUTS[key])

    def _ovq_chip(self, key):
        self.quick_bar_set(key, not self.quick_bar_on(key))
        self._ovq_paint(key)

    def _ovq_style(self):
        """2.110.0: a style picked here - the overlay is drawn again in it (Settings › Appearance shows it too)."""
        from .ovlight import STYLES
        name = self.ovq_style.get()
        key = next((k for k, v in STYLES.items() if v == name), None)
        if key and key != self.ov_look():
            self.ov_look_set(style=key)
            w = getattr(self, "ov_quick_win", None)        # 2.125.1: the box takes the new style too, where it is
            if w is not None:
                try:
                    x, y = w.winfo_x(), w.winfo_y()
                    self.ov_quick_show()
                    self.ov_quick_win.geometry(f"+{x}+{y}")
                except tk.TclError:
                    pass
            v = getattr(self, "ov_look_var", None)           # (Settings › Appearance shows it too)
            if v is not None:
                try:
                    v.set(name)
                    self._ov_look_paint()
                except tk.TclError:
                    pass

    def _ovq_layout(self, name):
        """Panel | Bar picked here - the overlay is built again (Settings › Appearance shows it too)."""
        from .merged_page import LAYOUTS
        key = next((k for k, t in LAYOUTS.items() if t == name), None)
        if not key or key == self.merged_layout():
            return
        self.merged_set(layout=key)
        self._ovq_layout_paint()
        box = getattr(self, "ovq_place_box", None)          # (2.130.0: Place's choices follow the layout)
        try:
            if box is not None and box.winfo_exists():
                opts = self.ov_spots()
                box.configure(values=list(opts.values()))
                self.ovq_place.set(opts[self.ov_spot()])
        except tk.TclError:
            pass
        v = getattr(self, "ov_layout_var", None)
        seg = getattr(self, "ov_layout_seg", None)
        try:
            if v is not None:
                v.set(name)
            if seg is not None:
                seg.pick(name, notify=False)
            pk = getattr(self, "ov_style_pick", None)
            if pk is not None:
                pk.set(self.ov_look(), redraw=True)
        except Exception:
            buglog.caught()

    def overlay_reload(self):
        """Reload Overlay (2.125.3): the overlay, its lines and its open helpers built again, and the loop that keeps
        them over the game started again."""
        from . import overlaywin as OW
        try:
            OW._LIVE[:] = [w for w in OW._LIVE if OW._alive(w)]
            if OW._JOB[0] is not None:
                try:
                    self.root.after_cancel(OW._JOB[0])
                except tk.TclError:
                    pass
                OW._JOB[0] = None
            self.merged_set()
            if OW._JOB[0] is None:
                OW._JOB[0] = self.root.after(OW.TICK_MS, OW._tick, self.root)
            self._say("Overlay reloaded")
        except Exception:
            self.log_error("reloading the overlay")

    def _ovq_lock(self, on):
        self.overlay_lock(on)
