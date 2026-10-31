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
SIZE = 34


class CopyMarker:
    def __init__(self, root):
        self.root = root
        self.marks = []

    def show(self, x, y, number=None, secs=MARK_SECS):
        """A ring centred on (x, y) (screen pixels, Tk's coordinates) for `secs`. -> the window."""
        while len(self.marks) >= MAX_MARKS:
            self._close(self.marks[0])
        pad = 6
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
        c.create_oval(pad, pad, pad + SIZE, pad + SIZE, outline="#000000", width=6)       # dark edge: shows on any
        c.create_oval(pad, pad, pad + SIZE, pad + SIZE, outline=RING, width=3)            # background
        m = full // 2
        c.create_oval(m - 3, m - 3, m + 3, m + 3, fill=RING, outline="#000000")
        if number is not None:
            c.create_text(full - 2, 2, text=str(number), anchor="ne", fill="#ffffff",
                          font=("Segoe UI", 9, "bold"))
        w.geometry(f"{full}x{full}+{int(x) - m}+{int(y) - m}")
        w.deiconify()
        w.update_idletasks()
        click_through(w)
        force_topmost(w)
        self.marks.append(w)
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
