"""Copy marker (2.19.0): after Ctrl+Alt+C, a small ring shows for 10 seconds where the mouse was, so you can see which
items you've already copied.

Display only: a click-through, see-through window over the game (like the Delirium and Breach alerts). It sends no
keys or clicks to the game and reads nothing from it - the mouse position comes from Windows / Tk."""
import sys
import tkinter as tk

from .alerts_page import TRANSPARENT, click_through, force_topmost

MARK_SECS = 10
MAX_MARKS = 30                      # many quick copies: the oldest go first
RING = "#ffcf40"
COLOURS = {"Gold": "#ffcf40", "White": "#ffffff", "Red": "#ff3b3b", "Lime": "#5dff3b", "Cyan": "#3be8ff",
           "Magenta": "#ff3df0", "Orange": "#ff9a1f", "Blue": "#4d8dff"}     # 2.25.0
SIZE = 16                           # 2.24.0: the + is this many pixels across


class CopyMarker:
    def __init__(self, root):
        self.root = root
        self.marks = []

    def show(self, x, y, number=None, secs=MARK_SECS, colour=RING):
        """A ring centered on (x, y) (screen pixels, Tk's coordinates) for `secs`. -> the window."""
        while len(self.marks) >= MAX_MARKS:
            self._close(self.marks[0])
        pad = 4
        full = SIZE + 2 * pad
        w = tk.Toplevel(self.root)
        w.withdraw()
        w.overrideredirect(True)
        try:
            w.attributes("-topmost", True)
        except tk.TclError:
            pass
        w.configure(bg=TRANSPARENT)
        if sys.platform == "win32":
            try:
                w.attributes("-transparentcolor", TRANSPARENT)
            except tk.TclError:
                pass
        c = tk.Canvas(w, width=full, height=full, bg=TRANSPARENT, highlightthickness=0, bd=0)
        c.pack()
        m = full // 2
        h = SIZE // 2
        for col, width in (("#000000", 5), (colour, 2)):              # a dark edge, so it shows on any background
            c.create_line(m - h, m, m + h + 1, m, fill=col, width=width)
            c.create_line(m, m - h, m, m + h + 1, fill=col, width=width)
        if number is not None:
            c.create_text(full - 1, 1, text=str(number), anchor="ne", fill="#ffffff", font=("Segoe UI", 7, "bold"))
        w.geometry(f"{full}x{full}+{int(x) - m}+{int(y) - m}")
        w.deiconify()
        w.update_idletasks()
        click_through(w)
        force_topmost(w)
        self.marks.append(w)
        if secs:                                             # None / 0: stays until clear() (Esc held 3 s)
            self.root.after(int(secs * 1000), lambda: self._close(w))
        return w

    def _close(self, w):
        if w in self.marks:
            self.marks.remove(w)
        try:
            w.destroy()
        except tk.TclError:
            pass

    def clear(self):
        for w in list(self.marks):
            self._close(w)
