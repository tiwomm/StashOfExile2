"""2.132.3 One look in maps for the helpers that read a tooltip: the Temple Helper (a Vaal Beacon's "Energised Beacons
55/60") and the Ritual Identifier (a Ritual Altar's type). One picture and one text read feeds both.
2.132.6 (feedback: "I need it to just read as I'm potentially running past it ... they're too fast to show and then
disappear"): the whole game is read (not just round the mouse), every second. A failed read no longer stops it
(a picture of a window on another monitor stopped every later look)."""
import time
import tkinter as tk

from . import buglog
from . import ritualid as RID
from . import temple as TM

EVERY_MS = 1000                     # how often it looks (only in a map, the game in front)
SCREEN = (0.0, 0.0, 1.0, 0.86)      # the part of the game read: all of it but the bottom bar (life, skills, flasks)
CONTENT_EVERY = 4.0                 # how often Map Content is checked for the Temple icon (until it's seen)
# 2.137.2 (feedback: "this ritual didn't pop up the message ... it's consistent 100% of the time at any resolution"):
# one read of the whole game misses small labels (a 4K game is shrunk to fit the text reader; a busy fight breaks
# the reader's lines). Every other look reads one quarter of it instead, overlapping, at up to twice the size - so
# each part of the screen is read big at least every 8 s, and the whole of it every 2 s.
TILES = ((0.0, 0.0, 0.56, 0.56), (0.44, 0.0, 1.0, 0.56), (0.0, 0.44, 0.56, 1.0), (0.44, 0.44, 1.0, 1.0))


def look_box(g, n):
    """Look number n -> the part of the game read (screen pixels): even = all of it, odd = one quarter in turn."""
    gx, gy, gw, gh = g
    x0, y0 = gx + int(gw * SCREEN[0]), gy + int(gh * SCREEN[1])
    w, h = int(gw * (SCREEN[2] - SCREEN[0])), int(gh * (SCREEN[3] - SCREEN[1]))
    if n % 2 == 0:
        return (x0, y0, x0 + w, y0 + h)
    t = TILES[(n // 2) % len(TILES)]
    return (x0 + int(w * t[0]), y0 + int(h * t[1]), x0 + int(w * t[2]), y0 + int(h * t[3]))


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
        n = self._hv_n = getattr(self, "_hv_n", -1) + 1
        box = look_box(g, n)
        if box[2] <= box[0] or box[3] <= box[1]:
            return None
        self._hv_busy = True
        # 2.132.4: does this map have a Temple (Map Content's icon)? Looked for until it's seen, every few seconds
        look_temple = (self.temple_on() or force) and not getattr(self, "tm_in_map", False) and \
            time.time() - getattr(self, "_tm_content_at", 0.0) > CONTENT_EVERY
        if look_temple:
            self._tm_content_at = time.time()

        def work():
            from . import remnant as RM
            try:
                has = TM.content_has(RM.grab(TM.content_box(g)), g[3]) if look_temple else None
                return RM.ocr(RM.grab(box)), has
            except Exception:
                buglog.caught()
                return [], None

        def done(got):
            self._hv_busy = False
            lines, has = got or ([], None)
            if has:
                self.tm_in_map = True
                try:
                    self.ritual_readout_sync()
                except Exception:
                    buglog.caught()
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
