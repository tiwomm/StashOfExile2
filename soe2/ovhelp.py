"""What each switch on the overlay's bar is for (2.73.4). Feedback: "when I toggle on Focus, it does nothing to
indicate what its purpose is" - and the Mechanic Helper switches were the same. Two light touches, nothing more:

  * hover a switch (half a second): a one-line tip under it - what it does;
  * the first time you switch one on: a small card over the game - what it does, why you'd want it, and a way to
    set it up (Got it closes it for good; each card shows once).

Both follow the overlay's theme (overlaywin.pal) and never take the keyboard from the game. One switch turns them
off: Overlay › Options › On the overlay › Feature tips. GGG ToS: windows only - nothing is sent to the game."""
import tkinter as tk
from tkinter import ttk

from .config import save_json, SETTINGS

# key -> (name, what it does, why you'd want it, set-up button label or None)
HELP = {
    "breach": ("Breach", "A banner when your stored Hiveblood is almost full, and again when it's full.",
               "Spend it at the Genesis Tree instead of wasting it. Reads the game's log.", "Breach settings"),
    "delirium": ("Delirium", "END DELIRIUM flashes when you finish a map with Delirium still on.",
                 "Easy to miss when the map's done - and easy to fix. Reads your screen.", "Delirium settings"),
    "ritual": ("Ritual", "Shows the map's Ritual count (2/3) and reminds you if you leave with altars unfinished.",
               "Unfinished altars are tribute left behind. Reads your screen.", "Ritual settings"),
    "remnant": ("Remnant", "Prices each reward in an Expedition remnant's book (poe.ninja, your league), with a "
                           "list of the runeshapes players rate best for loot (S to D).",
                "Pick the reward that's actually worth the most, and the runeshapes that pay - by itself, or with "
                "its key.", "Remnant settings"),
    "focus": ("Focus", "Your current league goal on this bar, and a short poke in town now and then.",
              "Keeps you on your plan when the league pulls you sideways. Quiet by default.", "Open Game Plan"),
}
TIP_DELAY = 450          # ms of hover before the tip


def tips_on():
    return bool(SETTINGS.get("tracker", {}).get("tips", True))


def seen():
    return SETTINGS.setdefault("ov_intro_seen", [])


class OverlayHelp:
    """Mixed into App."""

    # ---------------- hover: one line
    def ov_help_bind(self, cv, tag, key):
        if key not in HELP:
            return
        cv.tag_bind(tag, "<Enter>", lambda e: self._ov_tip_later(cv, key), add="+")
        cv.tag_bind(tag, "<Leave>", lambda e: self.ov_tip_hide(), add="+")
        cv.tag_bind(tag, "<Button-1>", lambda e: self.ov_tip_hide(), add="+")

    def _ov_tip_later(self, cv, key):
        self.ov_tip_hide()
        if tips_on():
            self._ov_tip_job = self.root.after(TIP_DELAY, lambda: self.ov_tip_show(cv, key))

    def ov_tip_show(self, cv, key, x=None, y=None):
        """-> the tip window (a borderless line in the overlay's look, under the pointer)."""
        from .overlaywin import pal
        self.ov_tip_hide()
        P = pal()
        name, what = HELP[key][0], HELP[key][1]
        on = self.ov_switch_on(key)
        w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        try:
            w.attributes("-topmost", True)
        except tk.TclError:
            pass
        box = tk.Frame(w, bg=P["bg"], highlightthickness=1, highlightbackground=P.get("rim", P["line"]), padx=8,
                       pady=8)
        box.pack()
        head = tk.Frame(box, bg=P["bg"])
        head.pack(fill="x")
        tk.Label(head, text=name.upper(), bg=P["bg"], fg=P["head"], font=(P["hfont"] or P["font"], 9, "bold")).pack(side="left")
        tk.Label(head, text="  ON" if on else "  OFF", bg=P["bg"], fg=P["on"] if on else P["muted"],
                 font=(P["font"], 8, "bold")).pack(side="left")
        tk.Label(box, text=what, bg=P["bg"], fg=P["text"], font=(P["font"], 9), justify="left", anchor="w",
                 wraplength=300).pack(fill="x", pady=(2, 0))
        tk.Label(box, text="Click to switch " + ("off" if on else "on"), bg=P["bg"], fg=P["muted"],
                 font=(P["font"], 8), anchor="w").pack(fill="x", pady=(2, 0))
        try:
            px, py = (x, y) if x is not None else (cv.winfo_pointerx(), cv.winfo_pointery())
        except tk.TclError:
            px, py = 100, 100
        w.update_idletasks()
        tw, th = w.winfo_reqwidth(), w.winfo_reqheight()
        left, top, right, bottom = self._ov_tip_bounds()
        y = py + 22
        if y + th > bottom:                                  # 2.73.5: no room under the pointer (the XP bar is at
            y = py - th - 12                                 # the screen's bottom edge) -> above it
        x = max(left, min(px - tw // 2, right - tw))
        w.geometry(f"+{x}+{max(top, y)}")
        self._no_focus(w)
        self.ov_tip = w
        return w

    def _ov_tip_bounds(self):
        """The game window's edges (the tip stays inside it), else the screen's."""
        try:
            from .alerts_page import game_rect
            r = game_rect()
        except Exception:
            r = None
        if r:
            return r[0], r[1], r[0] + r[2], r[1] + r[3]
        return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def ov_tip_hide(self):
        job = getattr(self, "_ov_tip_job", None)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except (tk.TclError, ValueError):
                pass
            self._ov_tip_job = None
        w = getattr(self, "ov_tip", None)
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass
            self.ov_tip = None

    @staticmethod
    def _no_focus(w):
        """Windows: the tip can't take the keyboard from the game (WS_EX_NOACTIVATE), as the overlay's windows."""
        import sys
        if sys.platform != "win32":
            return
        try:
            import ctypes
            u = ctypes.windll.user32
            w.update_idletasks()
            hwnd = u.GetParent(w.winfo_id()) or w.winfo_id()
            u.SetWindowLongW(hwnd, -20, u.GetWindowLongW(hwnd, -20) | 0x08000000 | 0x20)   # + click-through
        except Exception:
            pass

    def ov_switch_on(self, key):
        if key == "focus":
            from . import focus as F
            return bool(F.cfg()["on"])
        try:
            return self.alert_states().get(key, "off") != "off"
        except Exception:
            return False

    # ---------------- first time on: a card
    def ov_intro_maybe(self, key):
        """After a switch was turned on: its card, once. -> the card or None."""
        if key not in HELP or not tips_on() or key in seen() or not self.ov_switch_on(key):
            return None
        return self.ov_intro_show(key)

    def ov_intro_show(self, key):
        from .overlaywin import OverlayWindow, pal
        from .alerts_page import game_rect
        self.ov_intro_close(remember=False)
        name, what, why, setup = HELP[key]
        P = pal()
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        W = 420
        geo = (r[0] + (r[2] - W) // 2, r[1] + int(r[3] * 0.10), W, None)
        w = OverlayWindow(self.root, f"{name} is on", "💡", geo, palette=P, lockable=False, follow_game=True,
                          no_activate=True, on_close=lambda: self.ov_intro_close())
        bg = P["bg"]
        body = tk.Frame(w.body, bg=bg, padx=16, pady=8)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="WHAT IT DOES", bg=bg, fg=P["head"], font=(P["hfont"] or P["font"], 8, "bold"), anchor="w").pack(fill="x")
        tk.Label(body, text=what, bg=bg, fg=P["text"], font=(P["font"], 11), justify="left", anchor="w",
                 wraplength=W - 40).pack(fill="x", pady=(2, 8))
        tk.Label(body, text="WHY", bg=bg, fg=P["head"], font=(P["hfont"] or P["font"], 8, "bold"), anchor="w").pack(fill="x")
        extra = ""
        if key == "focus":
            from . import focus as F
            if not F.current():
                extra = "\nNo goal yet - Open Game Plan and add one (10 seconds)."
        tk.Label(body, text=why + extra, bg=bg, fg=P["muted"], font=(P["font"], 10), justify="left", anchor="w",
                 wraplength=W - 40).pack(fill="x", pady=(2, 8))
        row = tk.Frame(body, bg=bg)
        row.pack(fill="x")
        self.ov_intro_btns = {}
        if setup:
            b = ttk.Button(row, text=setup, style="Primary.TButton", command=lambda: self.ov_intro_setup(key))
            b.pack(side="left", padx=(0, 8))
            self.ov_intro_btns["setup"] = b
        b = ttk.Button(row, text="Got it", command=lambda: self.ov_intro_close())
        b.pack(side="left")
        self.ov_intro_btns["ok"] = b
        tk.Label(row, text="Hover a switch for a reminder", bg=bg, fg=P["muted"], font=(P["font"], 8)).pack(side="right")
        self.ov_intro_win, self.ov_intro_key = w, key
        w.show()
        return w

    def ov_intro_close(self, remember=True):
        w, self.ov_intro_win = getattr(self, "ov_intro_win", None), None
        key = getattr(self, "ov_intro_key", None)
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass
        if remember and key and key not in seen():
            seen().append(key)
            save_json("settings.json", SETTINGS)

    def ov_intro_setup(self, key):
        self.ov_intro_close()
        try:
            if key == "focus":
                self.shell.open("plan")
                self.gp_fill()
            else:
                self.tracker_helpers_settings()
            self.root.deiconify()
            self.root.lift()
        except Exception:
            self.log_error(f"opening {key}'s settings")
