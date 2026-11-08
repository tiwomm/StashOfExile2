"""P4 (2.108.0, feedback: "a mini settings page over the game when we right click the cog wheel"): right-click the
overlay's ⚙ = Quick settings, a small box over the game, above the cog and on the game's monitor. Left-click still
opens the full Overlay ↳ Settings in the app. Style (2.110.0 - the Overlay ON | OFF switch is gone from here), Sound,
Lock, Hide from screen captures, Helpers (2.118.0: each helper on / off - the bar has no switches for them any
more) and On the bar (the tools' menus). Esc, ✕, a click elsewhere or the cog again closes it.
GGG ToS: a window over the game; nothing is sent to the game."""
import tkinter as tk
from tkinter import ttk

from . import buglog
from .config import SETTINGS, save_json
from .style import C

# (label, key): the helpers switched on / off, then the tools' menus on the bar
QUICK_HELPERS = (("Breach", "breach"), ("Delirium", "delirium"), ("Ritual", "ritual"), ("Expedition", "remnant"),
                 ("Campaign", "campaign"), ("Focus", "focus"), ("Whispers", "whispers"))
QUICK_BAR = (("Notes", "notes"), ("Calc", "calc"), ("Regex", "regex"), ("Rates", "rates"))


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

    def ov_quick_show(self, e=None):
        self.ov_quick_close()
        P1, P2 = C["panel"], C["panel2"]
        w = tk.Toplevel(self.root, bg=C["line"])
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
        tk.Label(head, text="Quick settings", bg=P2, fg=C["text"], font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(head, text="✕", width=3, style="Quiet.TButton", command=self.ov_quick_close).pack(side="right")
        tk.Frame(box, bg=C["accent"], height=2).pack(fill="x")
        body = tk.Frame(box, bg=P1, padx=12, pady=8)
        body.pack(fill="x")
        CB = "Bar.TCheckbutton"
        self.ovq_vars = {}

        def row(label, value, fn):
            v = tk.BooleanVar(value=bool(value))
            cb = ttk.Checkbutton(body, text=label, variable=v, style=CB, command=lambda: fn(bool(v.get())))
            cb.pack(anchor="w", pady=2)
            self.ovq_vars[label] = v
            return v
        cfg = self.tracker_cfg()
        # 2.110.0 (feedback): no Overlay ON | OFF here - the overlay's Style instead
        from .ovlight import STYLES
        srow = tk.Frame(body, bg=P1)
        srow.pack(fill="x", pady=(0, 8))
        tk.Label(srow, text="Style", bg=P1, fg=C["text"], font=("Segoe UI", 10)).pack(side="left")
        names = list(STYLES.values())
        self.ovq_style = tk.StringVar(value=STYLES.get(self.ov_look(), names[0]))
        cb = ttk.Combobox(srow, textvariable=self.ovq_style, values=names, state="readonly", width=24)
        cb.pack(side="right")
        cb.bind("<<ComboboxSelected>>", lambda _e: self._ovq_style())
        row("Sound", SETTINGS.get("helpers_sound", True), self.helpers_sound_set)
        row("Lock overlay", cfg.get("mlocked"), self._ovq_lock)
        row("Hide from screen captures", cfg.get("hide_capture", False), self._ovq_hidecap)
        self.ovq_chips = {}
        for title, items in (("HELPERS", QUICK_HELPERS), ("ON THE BAR", QUICK_BAR)):
            tk.Label(body, text=title, bg=P1, fg=C["muted"], font=("Segoe UI", 9, "bold"), anchor="w").pack(
                fill="x", pady=(8, 4))
            grid = tk.Frame(body, bg=P1)
            grid.pack(fill="x")
            for i, (label, key) in enumerate(items):
                b = tk.Label(grid, text=label, font=("Segoe UI", 9), padx=8, pady=4, cursor="hand2",
                             highlightthickness=1)
                b.grid(row=i // 4, column=i % 4, sticky="ew", padx=(0, 4), pady=(0, 4))
                b.bind("<Button-1>", lambda _e, k=key: self._ovq_chip(k))
                self.ovq_chips[key] = b
                self._ovq_paint(key)
        foot = tk.Frame(box, bg=P1, padx=12, pady=8)
        foot.pack(fill="x")
        ttk.Button(foot, text="All settings…", command=lambda: (self.ov_quick_close(), self.overlay_settings_go())).pack(
            fill="x")
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
        try:
            b.config(bg=C["sel"] if on and "sel" in C else (C["panel2"] if on else C["panel"]),
                     fg=C["text"] if on else C["muted"], highlightbackground=C["accent"] if on else C["line"])
        except tk.TclError:
            pass

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
            v = getattr(self, "ov_look_var", None)           # (Settings › Appearance shows it too)
            if v is not None:
                try:
                    v.set(name)
                    self._ov_look_paint()
                except tk.TclError:
                    pass

    def _ovq_lock(self, on):
        self.overlay_lock(on)

    def _ovq_hidecap(self, on):
        self.tracker_cfg()["hide_capture"] = bool(on)
        v = getattr(self, "tk_hidecap", None)
        if v is not None and bool(v.get()) != bool(on):
            v.set(bool(on))
        self.tracker_save()
        self.overlay_click_through()
