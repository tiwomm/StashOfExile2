"""One look for every small window shown over the game (2.0 beta 13): Notes, the Session timer, and anything added
later. Same frame as the app's own windows: a thin title bar (utility colours), a 1px border, resize edges and a
lock button. Callers put their content in .body and get told when the window was moved or resized.

    w = OverlayWindow(root, "Notes", "📌", (x, y, w, h), opacity=215, locked=False,
                      on_close=..., on_lock=lambda locked: ..., on_moved=lambda x, y, w, h: ...)
    tk.Text(w.body, ...).pack(fill="both", expand=True)
"""
import os
import sys
import tkinter as tk

from .style import C
from .shell import GradientBar, UTIL_TITLE, TITLE_ON, BORDER_OFF

BAR_H = 22
EDGE = 4
OUTLINE = "#5b77ad"              # the same 1px outline as the app's windows
BODY_BG = "#0d1424"

# ---- over-the-game windows only show while the game is in front (2.0 beta 15)
GAME_ONLY = [True]                # Settings > Window: "only while Path of Exile 2 is in front"
GAME_TITLE = ["Path of Exile 2"]  # the Chat commands window's game title
_LIVE = []                        # windows that follow the game
_JOB = [None]
TICK_MS = 350


def _fg_hwnd():
    import ctypes
    return ctypes.windll.user32.GetForegroundWindow()


def foreground_ok():
    """May over-the-game windows show right now? Yes while Path of Exile 2 is the window in front, or one of these
    windows itself is (you clicked the note to type in it). 2.0 beta 17: not just because the app is in front - they
    popped up over the app's own windows."""
    if not GAME_ONLY[0] or sys.platform != "win32":
        return True
    try:
        from .overlay import game_active
        if game_active(GAME_TITLE[0] or "Path of Exile 2"):
            return True
        import ctypes
        u = ctypes.windll.user32
        fg = _fg_hwnd()
        for w in _LIVE:
            if _alive(w) and (u.GetParent(w.winfo_id()) or w.winfo_id()) == fg:
                return True
        return False
    except Exception:
        return True


def _tick(root):
    _JOB[0] = None
    _LIVE[:] = [w for w in _LIVE if _alive(w)]
    if not _LIVE:
        return
    ok = foreground_ok()
    for w in _LIVE:
        w.sync(ok)
    _JOB[0] = root.after(TICK_MS, _tick, root)


def _alive(w):
    try:
        return bool(w.winfo_exists())
    except Exception:
        return False


def resync():
    """Settings changed: apply now."""
    ok = foreground_ok()
    for w in list(_LIVE):
        if _alive(w):
            w.sync(ok)


class OverlayWindow(tk.Toplevel):
    def __init__(self, root, title, icon, geo, *, opacity=230, locked=False, body_bg=BODY_BG, min_size=(140, 60),
                 on_close=None, on_lock=None, on_moved=None, drag_body=False, app_colours=False, lockable=True,
                 follow_game=False, no_activate=False):
        """geo = (x, y, w, h); w / h None = as big as the content. app_colours: the blue title bar of the app's own
        windows (for small pop-ups of the app) instead of the utility colours (things shown over the game).
        follow_game: only visible while the game (or the window itself) is in front; show() / hide() say whether you want it.
        no_activate: clicking it never takes the keyboard away from the game (for windows you don't type in)."""
        super().__init__(root, bg=BORDER_OFF, highlightthickness=1, highlightbackground=OUTLINE)
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
            self.attributes("-alpha", max(0.15, min(1.0, int(opacity) / 255)))
        except Exception:
            pass
        x, y, w, h = geo
        if w is None or h is None:
            self.geometry(f"+{int(x)}+{int(y)}")
        else:
            self.geometry(f"{max(min_size[0], int(w))}x{max(min_size[1], int(h))}+{int(x)}+{int(y)}")
        self.locked, self.min_size = bool(locked), min_size
        self.on_moved, self.on_lock, self.on_close = on_moved, on_lock, on_close
        edge = 0 if self.locked else EDGE
        inner = tk.Frame(self, bg=body_bg)
        inner.pack(fill="both", expand=True, padx=edge, pady=edge)
        title_fg, btn_bg, btn_line, accent = (("#ffffff", "#22345a", "#5b77ad", C["accent"]) if app_colours else
                                              ("#ffe2b8", "#3a3020", "#6a5a3a", "#8a6a3a"))
        self.bar = GradientBar(inner, BAR_H, TITLE_ON if app_colours else UTIL_TITLE)
        self.bar.pack(fill="x")
        self.bar.configure(cursor="" if self.locked else "fleur")
        self.bar.create_text(8, BAR_H // 2, text=f"{icon}  {title}", anchor="w", fill=title_fg,
                             font=("Segoe UI", 8, "bold"))
        self._btns = []
        buttons = [("×", self._close, "#7a2a20")]
        if lockable:
            buttons.append(("🔒" if self.locked else "🔓", self._toggle_lock, btn_bg))
        for txt, cmd, bg in buttons:
            b = tk.Label(self.bar, text=txt, bg=bg, fg=title_fg, font=("Segoe UI", 7, "bold"), width=2,
                         highlightthickness=1, highlightbackground=btn_line, cursor="hand2")
            b.bind("<Button-1>", lambda e, c=cmd: c())
            self._btns.append(self.bar.create_window(0, BAR_H // 2, window=b, anchor="e"))
        self.bar.bind("<Configure>", self._place_btns, add="+")
        tk.Frame(inner, height=1 if not app_colours else 2, bg=accent).pack(fill="x")     # the accent line
        self.body = tk.Frame(inner, bg=body_bg)
        self.body.pack(fill="both", expand=True)
        self._drag, self._size = {}, {}
        self.wanted, self.follow_game, self.no_activate, self._noact_done = True, follow_game, no_activate, False
        if follow_game:
            _LIVE.append(self)
            if _JOB[0] is None:
                _JOB[0] = root.after(TICK_MS, _tick, root)
        if not self.locked:
            self.draggable(self.bar)
            if drag_body:
                self.draggable(self.body)
            self._edges()

    # ---- showing / hiding
    def show(self):
        self.wanted = True
        self.sync(foreground_ok() if self.follow_game else True)

    def hide(self):
        self.wanted = False
        self.withdraw()

    def sync(self, ok):
        """ok = the game (or this window) is in front."""
        try:
            mapped = self.state() != "withdrawn"
        except tk.TclError:
            return
        if self.wanted and ok and not mapped:
            self._show_quietly()
        elif mapped and not (self.wanted and ok):
            self.withdraw()

    def _show_quietly(self):
        """Show it without taking the keyboard away from whatever is in front (the game)."""
        fg = None
        if sys.platform == "win32":
            try:
                fg = _fg_hwnd()
            except Exception:
                fg = None
        self.deiconify()
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        if sys.platform != "win32":
            return
        try:
            import ctypes
            u = ctypes.windll.user32
            self.update_idletasks()
            hwnd = u.GetParent(self.winfo_id()) or self.winfo_id()
            if self.no_activate and not self._noact_done:
                u.SetWindowLongW(hwnd, -20, u.GetWindowLongW(hwnd, -20) | 0x08000000)    # WS_EX_NOACTIVATE
                self._noact_done = True
            if fg and u.GetForegroundWindow() != fg:
                u.SetForegroundWindow(fg)                     # hand the keyboard straight back
        except Exception:
            pass

    # ---- title bar buttons
    def _place_btns(self, _e=None):
        w = self.bar.winfo_width()
        for n, item in enumerate(self._btns):
            self.bar.coords(item, w - 4 - n * 24, BAR_H // 2)

    def _close(self):
        if self.on_close:
            self.on_close()
        else:
            self.destroy()

    def _toggle_lock(self):
        if self.on_lock:
            self.on_lock(not self.locked)

    # ---- moving
    def draggable(self, widget):
        """Let this widget (and nothing else in the content) move the window: e.g. a label in the body."""
        widget.bind("<ButtonPress-1>", self._press, add="+")
        widget.bind("<B1-Motion>", self._move, add="+")
        widget.bind("<ButtonRelease-1>", self._moved, add="+")

    def _press(self, e):
        self._drag = {"x": e.x_root - self.winfo_x(), "y": e.y_root - self.winfo_y()}

    def _move(self, e):
        if self._drag:
            self.geometry(f"+{e.x_root - self._drag['x']}+{e.y_root - self._drag['y']}")

    def _moved(self, _e=None):
        self._drag = {}
        self.report()

    def report(self):
        if self.on_moved and self.winfo_ismapped() and self.winfo_width() > 1:
            self.on_moved(self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height())

    # ---- resizing from every edge and corner
    def _edges(self):
        k = 14
        for sd, cur, kw in (("n", "sb_v_double_arrow", dict(x=0, y=0, relwidth=1, height=EDGE)),
                            ("s", "sb_v_double_arrow", dict(x=0, rely=1, y=-EDGE, relwidth=1, height=EDGE)),
                            ("w", "sb_h_double_arrow", dict(x=0, y=0, width=EDGE, relheight=1)),
                            ("e", "sb_h_double_arrow", dict(relx=1, x=-EDGE, y=0, width=EDGE, relheight=1)),
                            ("nw", "top_left_corner", dict(x=0, y=0, width=k, height=EDGE)),
                            ("nw", "top_left_corner", dict(x=0, y=0, width=EDGE, height=k)),
                            ("ne", "top_right_corner", dict(relx=1, x=-k, y=0, width=k, height=EDGE)),
                            ("ne", "top_right_corner", dict(relx=1, x=-EDGE, y=0, width=EDGE, height=k)),
                            ("sw", "bottom_left_corner", dict(x=0, rely=1, y=-EDGE, width=k, height=EDGE)),
                            ("sw", "bottom_left_corner", dict(x=0, rely=1, y=-k, width=EDGE, height=k)),
                            ("se", "bottom_right_corner", dict(relx=1, x=-k, rely=1, y=-EDGE, width=k, height=EDGE)),
                            ("se", "bottom_right_corner", dict(relx=1, x=-EDGE, rely=1, y=-k, width=EDGE, height=k))):
            h = tk.Frame(self, bg=BORDER_OFF, cursor=cur)
            h.place(**kw)
            self.resizer(h, sd)

    def resizer(self, widget, side):
        widget.bind("<ButtonPress-1>", lambda e: self._size.update(
            x0=e.x_root, y0=e.y_root, g=(self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height()),
            sd=side))
        widget.bind("<B1-Motion>", self._resize)
        widget.bind("<ButtonRelease-1>", self._resized)

    def _resize(self, e):
        if "g" not in self._size:
            return
        x, y, ww, hh = self._size["g"]
        mw, mh = self.min_size
        dx, dy, sd = e.x_root - self._size["x0"], e.y_root - self._size["y0"], self._size["sd"]
        if "e" in sd:
            ww = max(mw, ww + dx)
        if "s" in sd:
            hh = max(mh, hh + dy)
        if "w" in sd:
            nw = max(mw, ww - dx)
            x, ww = x + ww - nw, nw
        if "n" in sd:
            nh = max(mh, hh - dy)
            y, hh = y + hh - nh, nh
        self.geometry(f"{ww}x{hh}+{x}+{y}")

    def _resized(self, _e=None):
        self._size.clear()
        self.report()
