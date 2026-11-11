"""2.132.3 One look round the mouse in maps, for the helpers that read a tooltip there: the Temple Helper (a Vaal
Beacon's "Energised Beacons 55/60") and the Ritual Identifier (a Ritual Altar's type). One picture and one text read
every 1.5 s feeds both (was the Temple Helper's own look)."""
import tkinter as tk

from . import buglog
from . import ritualid as RID
from . import temple as TM

EVERY_MS = 1500                     # how often it looks (only in a map, the game in front)


class HoverPage:
    """Mixed into App."""

    def hover_wanted(self):
        return self.temple_on() or self.ritid_on()

    def hover_start(self):
        if getattr(self, "_hv_ticking", False) or not self.hover_wanted():
            return
        self._hv_ticking = True
        self.root.after(EVERY_MS, self.hover_tick)

    def hover_tick(self):
        if not self.hover_wanted():
            self._hv_ticking = False
            return
        try:
            if self.temple_on():
                self.ritual_readout_sync()                  # (the crystals ride on the line above the bar)
            self.hover_look()
        except Exception:
            self.log_error("reading tooltips in maps")
        self.root.after(EVERY_MS, self.hover_tick)

    def hover_look(self, force=False):
        """One look round the mouse (a background thread); the text goes to each helper that's on."""
        if getattr(self, "_hv_busy", False):
            return None
        if not force:
            if getattr(self, "br_area", None) != "map" or not self.hover_wanted():
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
        self._hv_busy = True

        def work():
            from . import remnant as RM
            return RM.ocr(RM.grab(box))

        def done(lines):
            self._hv_busy = False
            if self.temple_on() or force:
                self.temple_seen(TM.parse(lines))
            if self.ritid_on() or force:
                self.ritid_seen(RID.parse(lines))
        try:
            self.run_bg(work, done)
        except Exception:
            self._hv_busy = False
            raise
        return True
