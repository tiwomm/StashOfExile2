"""The start-up screen (2.0.0): the app's chest with a glow, its name and version, and what is being loaded.

It never adds waiting time: it closes as soon as the app is ready (at most a few seconds while the trade site's mod list
loads), a click closes it at once, and Settings > Appearance can turn it off. It doesn't take the keyboard from the game.
"""
import base64
import io
import sys
import time
import tkinter as tk

BG, PANEL, LINE, TEXT, MUTED = "#090e17", "#0e1522", "#2b3d5f", "#dbe4f2", "#7d8da8"
W, H = 440, 300
def _accent():
    from .style import C
    return C["accent"]


STEPS = ["Loading your settings", "Building your windows", "Restoring your windows", "Trade site mod list", "Ready"]


def _frames(icon_b64, n=8):
    """The chest with a glow behind it that breathes in and out: a few frames made once with Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageTk
        chest = Image.open(io.BytesIO(base64.b64decode("".join(icon_b64.split())))).convert("RGBA").resize(
            (112, 112), Image.LANCZOS)
    except Exception:
        return []
    out = []
    for i in range(n):
        k = 0.5 - 0.5 * __import__("math").cos(2 * 3.14159 * i / n)          # 0 .. 1 .. 0
        im = Image.new("RGBA", (180, 160), PANEL)
        glow = Image.new("RGBA", (180, 160), (0, 0, 0, 0))
        r = 46 + 14 * k
        ImageDraw.Draw(glow).ellipse((90 - r, 72 - r * 0.8, 90 + r, 72 + r * 0.8),
                                     fill=(255, 166, 61, int(70 + 90 * k)))
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(18)))
        im.alpha_composite(chest, (34, 26))
        out.append(ImageTk.PhotoImage(im))
    return out


class Splash:
    def __init__(self, root, icon_b64, version, league=""):
        self.root, self.closed, self.step_i = root, False, 0
        self.started = time.time()
        w = tk.Toplevel(root, bg=LINE)
        w.overrideredirect(True)
        try:
            w.attributes("-topmost", True)
        except tk.TclError:
            pass
        # 2.25.2: in the middle of where the app was last time (its monitor), not always the main monitor
        try:
            from .config import SETTINGS
            from .style import monitor_rect
            g = SETTINGS.get("main_window") or {}
            cx, cy = int(g["x"]) + int(g["w"]) // 2, int(g["y"]) + int(g["h"]) // 2
            l, t, r, b = monitor_rect(root, cx, cy)
            cx, cy = max(l + W // 2, min(cx, r - W // 2)), max(t + H // 2, min(cy, b - H // 2))
        except Exception:
            cx, cy = root.winfo_screenwidth() // 2, root.winfo_screenheight() // 2
        w.geometry(f"{W}x{H}+{cx - W // 2}+{cy - H // 2}")
        inner = tk.Frame(w, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(inner, bg=_accent(), height=2).pack(fill="x")
        self.frames = _frames(icon_b64)
        self.pic = tk.Label(inner, bg=PANEL, image=self.frames[0] if self.frames else "")
        self.pic.pack(pady=(10, 0))
        tk.Label(inner, text="StashOfExile2", bg=PANEL, fg="#ffffff", font=("Palatino Linotype", 20, "bold")).pack()
        tk.Label(inner, text=f"version {version}" + (f"   ·   {league}" if league else ""), bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack()
        self.msg = tk.Label(inner, text=STEPS[0] + "…", bg=PANEL, fg=TEXT, font=("Segoe UI", 9))
        self.msg.pack(pady=(10, 4))
        self.bar = tk.Canvas(inner, width=W - 80, height=6, bg=BG, highlightthickness=0)
        self.bar.pack()
        self.fill = self.bar.create_rectangle(0, 0, 0, 6, fill=_accent(), outline="")
        for wid in (w, inner, self.pic, self.msg, self.bar):
            wid.bind("<Button-1>", lambda e: self.close())
        self.win = w
        self._frame_i = 0
        w.update_idletasks()
        if sys.platform == "win32":                       # never takes the keyboard (e.g. from the game)
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(w.winfo_id()) or w.winfo_id()
                st = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                ctypes.windll.user32.SetWindowLongW(hwnd, -20, st | 0x08000000 | 0x00000080)
            except Exception:
                pass
        self._animate()
        self.pump()

    def pump(self):
        try:
            self.win.lift()                               # stay above the windows being built
            self.win.update()
        except tk.TclError:
            pass

    def _animate(self):
        if self.closed or not self.frames:
            return
        self._frame_i = (self._frame_i + 1) % len(self.frames)
        try:
            self.pic.config(image=self.frames[self._frame_i])
            self.win.lift()
            self.root.after(110, self._animate)
        except tk.TclError:
            pass

    def step(self, text=None, i=None):
        """Show the next step (or a given one)."""
        if self.closed:
            return
        if i is not None:
            self.step_i = i
        else:
            self.step_i = min(self.step_i + 1, len(STEPS) - 1)
        try:
            self.msg.config(text=(text or STEPS[self.step_i]) + ("" if self.step_i == len(STEPS) - 1 else "…"))
            self.bar.coords(self.fill, 0, 0, (W - 80) * (self.step_i + 1) / len(STEPS), 6)
        except tk.TclError:
            return
        self.pump()

    def close(self, fade=True):
        if self.closed:
            return
        try:
            self.step("Ready", i=len(STEPS) - 1)
        except Exception:
            pass
        self.closed = True

        def fade_out(a=1.0):
            try:
                if a <= 0.05:
                    self.win.destroy()
                    return
                self.win.attributes("-alpha", a)
                self.root.after(25, fade_out, a - 0.15)
            except tk.TclError:
                pass
        if fade:
            self.root.after(120, fade_out)
        else:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
