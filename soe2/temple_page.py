"""2.132.1 Temple Helper - the watcher (a look round the mouse in maps, for the Vaal Beacon's tooltip), the bar's
crystals part and the alert card when they're full; its row in Overlay ↳ Settings › Helpers (temple.py reads)."""
import tkinter as tk
from tkinter import ttk

from . import buglog
from . import temple as TM
from .config import SETTINGS, save_json
from .style import C, Tooltip

EVERY_MS = 1500                     # how often it looks (only in a map, the game in front)


class TemplePage:
    """Mixed into App."""

    def temple_on(self):
        from . import features as FEAT
        return bool(TM.cfg().get("on")) and FEAT.on("overlay")

    def temple_set(self, on):
        TM.cfg()["on"] = bool(on)
        save_json("settings.json", SETTINGS)
        if on:
            self.temple_start()
            if getattr(self, "br_reader", None) is None:    # (the game's log says when you're in a map)
                try:
                    self.breach_start()
                except Exception:
                    buglog.caught()
        try:
            self.merged_build()                             # (the bar's crystals part comes / goes)
        except Exception:
            buglog.caught()

    def temple_start(self):
        if getattr(self, "_tm_ticking", False) or not self.temple_on():
            return
        self._tm_ticking = True
        self.root.after(EVERY_MS, self.temple_tick)

    def temple_tick(self):
        if not self.temple_on():
            self._tm_ticking = False
            return
        try:
            self.temple_look()
        except Exception:
            self.log_error("the Temple Helper")
        self.root.after(EVERY_MS, self.temple_tick)

    def temple_look(self, force=False):
        """One look round the mouse (a background thread) for "Energised Beacons: n/m"."""
        if getattr(self, "_tm_busy", False):
            return None
        if not force:
            if getattr(self, "br_area", None) != "map":
                return None
            try:
                from .overlaywin import foreground_ok
                if not foreground_ok():
                    return None
            except Exception:
                buglog.caught()
        from .alerts_page import game_rect
        g = game_rect()
        if not g:
            return None
        try:
            p = self.root.winfo_pointerxy()
        except tk.TclError:
            return None
        box = TM.region(p, g)
        self._tm_busy = True

        def work():
            from . import remnant as RM
            return TM.parse(RM.ocr(RM.grab(box)))

        def done(got):
            self._tm_busy = False
            self.temple_seen(got)
        try:
            self.run_bg(work, done)
        except Exception:
            self._tm_busy = False
            raise
        return True

    def temple_seen(self, got):
        """A read (have, most) or None (no tooltip there)."""
        if not got:
            return None
        old = TM.state()
        st = TM.state_set(*got)
        if not old or (old["have"], old["most"]) != got:
            buglog.debug("Temple", f"crystals {got[0]}/{got[1]}")
            try:
                self.tracker_overlay_draw(self.tracker_numbers())
            except Exception:
                buglog.caught()
        if TM.full(st) and not (old and TM.full(old) and getattr(self, "tm_told", False)):
            self.temple_alert(st)
        elif not TM.full(st):
            self.tm_told = False
        return st

    def temple_alert(self, st=None, test=False):
        """Crystals full: a vital alert card (red words)."""
        st = st or TM.state() or {"have": 60, "most": 60}
        self.tm_told = True
        from . import alertcard
        from .alerts_page import game_rect
        self.tm_win = alertcard.show(self.root, "Crystals full", f"Energised Beacons {st['have']}/{st['most']} - open "
                                     "the Vaal Ruins", color="#d9a441", mark="◆", secs=5 if test else 10,
                                     game=game_rect(), tag="Temple", rank=1, vital=True)
        return self.tm_win

    def temple_bar_text(self):
        return TM.bar_text(TM.state()) if self.temple_on() else ""

    # ---------------------------------------------------------------- Overlay ↳ Settings › Helpers: its row
    def temple_row(self, box, bg, CB):
        sm = ("Segoe UI", 9)
        row = tk.Frame(box, bg=bg)
        row.pack(fill="x", pady=(8, 0))
        self.al_temple = tk.BooleanVar(value=bool(TM.cfg()["on"]))
        cb = ttk.Checkbutton(row, text="Temple Helper", variable=self.al_temple, style=CB,
                             command=lambda: self.temple_set(bool(self.al_temple.get())))
        cb.pack(side="left")
        tb = ttk.Button(row, text="Test", width=6, command=lambda: self.temple_alert(test=True))
        tb.pack(side="left", padx=(8, 0))
        info = tk.Label(row, text="ⓘ", bg=bg, fg=C["muted"], font=sm, cursor="question_arrow")
        info.pack(side="left", padx=(8, 0))
        tk.Label(box, text="Your crystals (Energised Beacons) on the bar, and a card when they're full.", bg=bg,
                 fg=C["muted"], font=sm, anchor="w").pack(fill="x")
        Tooltip(cb, "Hover a Vaal Beacon in a map: its tooltip's \"Energised Beacons: 55/60\" is read. Off until you "
                    "turn it on.")
        Tooltip(tb, "Shows the Crystals full card now.")
        Tooltip(info, "In maps only, it looks round the mouse every second and a half for that one line (Windows' text "
                      "reader). Only the two numbers are kept - nothing else on screen, nothing sent anywhere.")
