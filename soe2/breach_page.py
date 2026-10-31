"""Breach alert (2.9.0, a checkbox in Session tracker > Options): a big HIVEBLOOD ALMOST FULL banner over the game
when the game says so.

The game writes this to its own log, Client.txt (seen in a real PoE 2 log, Oct 2026):
    : <brequelwarning>{Stored Hiveblood is almost at the maximum!}
It's easy to miss in the middle of a Breach. This follows Client.txt (only new lines, about once a second - the same
way the Session tracker does) and shows a banner over the game, with a sound if you like. Nothing is read from the
game itself and no keys are sent. The banner stays until you click it, or until you open the Brequel tree (the game
logs that too)."""
import time
import tkinter as tk
from tkinter import ttk

from .config import save_json, SETTINGS
from .gamelog import find_log, LogReader
from .style import C

REPEAT_SECS = 45          # the game writes the warning twice in 2 s: one banner, not two


class BreachAlert:
    """Mixed into App."""

    def breach_cfg(self):
        return SETTINGS.setdefault("breach_alert", {"on": False, "sound": True})

    def build_breach_controls(self, box):
        """2.9.0: in Session tracker > Options > Alerts while you play: on / off, sound, a test."""
        P2 = C["panel2"]
        cfg = self.breach_cfg()
        row = tk.Frame(box, bg=P2)
        row.pack(fill="x", pady=(6, 0))
        self.br_on = tk.BooleanVar(value=bool(cfg.get("on")))
        ttk.Checkbutton(row, text="Breach: a big banner when your stored Hiveblood is almost full", variable=self.br_on,
                        command=self.breach_toggle).pack(side="left")
        ttk.Button(row, text="Test", command=lambda: self.breach_alert(test=True)).pack(side="right")
        self.br_sound = tk.BooleanVar(value=bool(cfg.get("sound", True)))
        ttk.Checkbutton(row, text="Sound", variable=self.br_sound,
                        command=lambda: (cfg.__setitem__("sound", bool(self.br_sound.get())),
                                         save_json("settings.json", SETTINGS))).pack(side="right", padx=8)
        self.br_status = tk.Label(box, text="", bg=P2, fg=C["muted"], anchor="w", justify="left", wraplength=600,
                                  font=("Segoe UI", 8))
        self.br_status.pack(fill="x", padx=(22, 0))
        self.br_msg = self.br_status
        self.br_reader, self.br_last, self.br_win = None, 0.0, None
        if cfg.get("on"):
            self.root.after(1500, self.breach_start)
        self.breach_draw()

    # ---- on / off
    def breach_toggle(self):
        cfg = self.breach_cfg()
        cfg["on"] = bool(self.br_on.get())
        save_json("settings.json", SETTINGS)
        if cfg["on"]:
            self.breach_start()
        else:
            self.br_reader = None
        self.breach_draw()

    def breach_start(self):
        """Follow Client.txt from its end (the same file the Session tracker uses, or the one you picked there)."""
        tc = getattr(self, "tracker_cfg", None)
        path = find_log(tc().get("log_path") if tc else None)
        if not path:
            self.br_reader = None
            self.breach_draw("Client.txt wasn't found. Pick it here in the Session tracker (right-click the log line at "
                             "the top), then switch this off and on.")
            return
        self.br_reader = LogReader(path)
        self.br_reader.start()                       # only what the game writes from now on
        self.breach_draw()
        if not getattr(self, "_br_ticking", False):
            self._br_ticking = True
            self.root.after(1000, self.breach_tick)

    def breach_tick(self):
        try:
            if self.br_reader is not None and self.breach_cfg().get("on"):
                for kind, ts, data in self.br_reader.poll():
                    if kind == "breach" and "hiveblood" in data["text"].lower():
                        self.breach_alert(text=data["text"])
                    elif kind == "brequel_tree":
                        self.breach_dismiss()
        except Exception:
            self.log_error("breach alert")
        if self.breach_cfg().get("on"):
            self.root.after(1000, self.breach_tick)
        else:
            self._br_ticking = False

    # ---- the banner
    def breach_alert(self, text="Stored Hiveblood is almost at the maximum!", test=False):
        now = time.time()
        if not test and now - self.br_last < REPEAT_SECS:
            return
        self.br_last = now
        self.breach_dismiss()
        from .overlaywin import OverlayWindow
        sw = self.root.winfo_screenwidth()
        w, h = 560, 120
        win = OverlayWindow(self.root, "Breach alert", "🩸", ((sw - w) // 2, 90, w, h), opacity=245,
                            body_bg="#2a0d10", lockable=False, no_activate=True, on_close=self.breach_dismiss)
        big = tk.Label(win.body, text="HIVEBLOOD ALMOST FULL", bg="#2a0d10", fg="#ff5a4a", cursor="hand2",
                       font=("Segoe UI", 26, "bold"))
        big.pack(fill="x", pady=(10, 0))
        small = tk.Label(win.body, text="Spend it at the Brequel tree  ·  click to close", bg="#2a0d10",
                         fg="#ffd9cf", cursor="hand2", font=("Segoe UI", 11), wraplength=w - 30)
        small.pack(fill="x", pady=(2, 10))
        for wdg in (win.body, big, small):
            wdg.bind("<Button-1>", lambda e: self.breach_dismiss())
        win.show()
        self.br_win = win
        self._breach_flash(big, 8)
        if self.breach_cfg().get("sound", True):
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                self.root.bell()
        self.breach_draw(("Test banner shown." if test else
                          f"Warned at {time.strftime('%H:%M')}: {text}"))
        if test:
            self.root.after(5000, lambda: self.br_win is win and self.breach_dismiss())

    def _breach_flash(self, lbl, n):
        if n <= 0 or self.br_win is None:
            return
        try:
            lbl.config(fg="#ff5a4a" if n % 2 else "#ffe36e")
        except tk.TclError:
            return
        self.root.after(450, lambda: self._breach_flash(lbl, n - 1))

    def breach_dismiss(self):
        w, self.br_win = self.br_win, None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    # ---- state
    def breach_status(self):
        if not self.breach_cfg().get("on"):
            return False
        if self.br_win is not None or self.br_reader is None:
            return "warn"
        return True

    def breach_draw(self, note=None):
        if not hasattr(self, "br_status"):
            return
        on = self.breach_cfg().get("on")
        if note is not None:
            txt, col = note, (C["good"] if "wasn't found" in note else C["muted"])
        elif not on:
            txt, col = "Reads only the game's log (Client.txt). Click the banner to close it; opening the Brequel tree "\
                       "closes it too.", C["muted"]
        elif self.br_reader is None:
            txt, col = "On - but Client.txt wasn't found (pick it: right-click the log line at the top).", C["good"]
        else:
            txt, col = "On - watching for the game's Hiveblood warning.", C["green"]
        self.br_status.config(text=txt, fg=col)
