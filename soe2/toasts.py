"""One toast system for the whole app (2.35.0, Polish 2).

Toasts stack in the bottom-right corner of the app window, newest at the bottom. Each kind has its own icon as well as
its own color (never color alone): info ℹ, success ✔, warning ⚠, error ✖. A toast:
  * stays up longer for longer text (errors and toasts with buttons longer still),
  * pauses while the mouse is over it,
  * never takes the keyboard (no focus, and on Windows it never activates),
  * goes away with ✕, a click on its text, or one of its buttons.
The last 20 are kept (toasts.json in the data folder) and listed in Settings > Advanced > Recent messages.

The popup near the mouse over the GAME (style.Toast: valuable mods, "All items checked") is a different thing and stays."""
import collections
import sys
import time
import tkinter as tk
from tkinter import ttk

from .config import load_json, save_json
from .style import BODY, C, SMALL

KINDS = {               # icon, colour key
    "info": ("ℹ", "blue"),
    "success": ("✔", "green"),
    "warning": ("⚠", "good"),
    "error": ("✖", "red"),
}
FILE = "toasts.json"
KEEP = 20
MAX_SHOWN = 4
GAP, EDGE = 8, 16
WIDTH = 360


def duration(text, title="", kind="info", actions=0):
    """Seconds a toast stays up: about 1 s per 15 characters (reading speed), 4 s at least, 20 s at most."""
    secs = 3 + len(f"{title} {text}") / 15
    if kind == "error":
        secs *= 1.5
    if actions:
        secs = max(secs, 10)
    return round(max(4, min(20, secs)), 1)


def no_activate(w):
    """Windows: a toast never becomes the active window, so it can't take the keyboard from the game or a box."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(w.winfo_id()) or w.winfo_id()
        st = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, st | 0x08000000 | 0x00000080)   # NOACTIVATE | TOOLWINDOW
    except Exception:
        pass


class Toasts:
    def __init__(self, root):
        self.root = root
        self.shown = []                        # [{"win", "job", "left", "since"}], oldest first
        saved = load_json(FILE, [])
        self.history = collections.deque(saved if isinstance(saved, list) else [], maxlen=KEEP)
        self.on_history = None                 # Settings > Advanced repaints its list with this
        self._lift_job = None
        for ev in ("<Visibility>", "<FocusIn>", "<Map>"):   # the app came forward: put the toasts back on top at once
            try:
                root.bind(ev, lambda e: self._lift_soon(), add="+")
            except tk.TclError:
                pass

    def _lift_soon(self):
        if self.shown and not self._lift_job:
            self._lift_job = self.root.after_idle(self.lift_all)

    def lift_all(self):
        self._lift_job = None
        for t in self.shown:
            try:
                t["win"].attributes("-topmost", True)
                t["win"].lift()
            except tk.TclError:
                pass

    # ------------------------------------------------------------------ showing
    def show(self, text, title="", kind="info", actions=(), secs=None):
        kind = kind if kind in KINDS else "info"
        icon, ckey = KINDS[kind]
        colour = C[ckey]
        secs = secs if secs else duration(text, title, kind, len(actions))
        self.history.append({"ts": time.time(), "kind": kind, "title": title, "text": text})
        try:
            save_json(FILE, list(self.history))
        except Exception:
            pass
        if self.on_history:
            try:
                self.on_history()
            except Exception:
                pass
        while len(self.shown) >= MAX_SHOWN:
            self.close(self.shown[0])

        w = tk.Toplevel(self.root)
        w.withdraw()
        w.overrideredirect(True)
        try:
            w.attributes("-topmost", True)
        except tk.TclError:
            pass
        outer = tk.Frame(w, bg=colour, padx=0, pady=0)
        outer.pack(fill="both", expand=True)
        tk.Frame(outer, bg=colour, width=4).pack(side="left", fill="y")          # a coloured edge, plus the icon
        box = tk.Frame(outer, bg=C["panel2"], padx=12, pady=8)
        box.pack(side="left", fill="both", expand=True)
        head = tk.Frame(box, bg=C["panel2"])
        head.pack(fill="x")
        tk.Label(head, text=icon, bg=C["panel2"], fg=colour, font=("Segoe UI Symbol", BODY, "bold")).pack(side="left")
        tk.Label(head, text=title or kind.capitalize(), bg=C["panel2"], fg=C["text"], font=("Segoe UI", BODY, "bold"),
                 anchor="w").pack(side="left", fill="x", expand=True, padx=(8, 0))
        x = tk.Label(head, text="✕", bg=C["panel2"], fg=C["muted"], cursor="hand2", font=("Segoe UI", SMALL))
        x.pack(side="right")
        body = tk.Label(box, text=text, bg=C["panel2"], fg=C["text"], font=("Segoe UI", SMALL), wraplength=WIDTH - 40,
                        justify="left", anchor="w")
        body.pack(fill="x", pady=(4, 0))
        t = {"win": w, "job": None, "left": secs, "since": None, "kind": kind}
        if actions:
            row = tk.Frame(box, bg=C["panel2"])
            row.pack(fill="x", pady=(8, 0))
            for label, fn in actions:
                ttk.Button(row, text=label, takefocus=0,
                           command=lambda f=fn: (self.close(t), f())).pack(side="right", padx=(8, 0))
        x.bind("<Button-1>", lambda e: self.close(t))
        body.bind("<Button-1>", lambda e: self.close(t))
        w.bind("<Enter>", lambda e: self._pause(t))
        w.bind("<Leave>", lambda e: self._resume(t))
        self.shown.append(t)
        w.update_idletasks()
        w.geometry(f"{WIDTH}x{max(w.winfo_reqheight(), 48)}")
        self.place()
        w.deiconify()
        no_activate(w)
        self._resume(t)
        self._keep_up()
        return t

    def _keep_up(self):
        """The app itself can be "always on top" too, and comes up over the toasts when a window opens - so lift them
        twice a second while any are shown (lift only: never focus)."""
        if getattr(self, "_up_job", None) or not self.shown:
            return

        def tick():
            self._up_job = None
            for t in self.shown:
                try:
                    t["win"].attributes("-topmost", True)
                    t["win"].lift()
                except tk.TclError:
                    pass
            if self.shown:
                self._up_job = self.root.after(500, tick)
        self._up_job = self.root.after(500, tick)

    def _pause(self, t):
        if t["job"]:
            self.root.after_cancel(t["job"])
            t["job"] = None
            t["left"] = max(1.5, t["left"] - (time.time() - t["since"]))

    def _resume(self, t):
        if t["job"] is None and t in self.shown:
            t["since"] = time.time()
            t["job"] = self.root.after(int(t["left"] * 1000), lambda: self.close(t))

    def close(self, t):
        if t in self.shown:
            self.shown.remove(t)
        if t.get("job"):
            try:
                self.root.after_cancel(t["job"])
            except tk.TclError:
                pass
            t["job"] = None
        try:
            t["win"].destroy()
        except tk.TclError:
            pass
        self.place()

    def clear(self):
        for t in list(self.shown):
            self.close(t)

    def place(self):
        """Stack them up from the app window's bottom-right corner (inside the app, above its taskbar)."""
        try:
            self.root.update_idletasks()
            rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
            rw, rh = self.root.winfo_width(), self.root.winfo_height()
            if rw < 200 or rh < 200 or not self.root.winfo_viewable():
                rx, ry, rw, rh = 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        except tk.TclError:
            return
        y = ry + rh - EDGE - 64                    # 64: keep clear of the app's own taskbar and status line
        for t in reversed(self.shown):
            w = t["win"]
            try:
                h = w.winfo_reqheight()
                y -= h
                w.geometry(f"+{rx + rw - WIDTH - EDGE}+{y}")
                y -= GAP
            except tk.TclError:
                pass
