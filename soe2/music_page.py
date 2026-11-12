"""2.134.0 Music Controls - a small window over the game with ⏮ ⏯ ⏭, dragged where you want it, apart from the
overlay's bar / panel, in the overlay's chosen style and held by its one lock. On / off: its row in Overlay ↳ Overlay
Settings › Helpers (and Quick settings). music.py sends the commands."""
import tkinter as tk

from . import buglog
from . import music as MU
from .config import SETTINGS, save_json


class MusicPage:
    """Mixed into App."""

    def music_wanted(self):
        """Its switch (and its BETA feature) is on."""
        from . import features as FEAT
        return bool(MU.cfg().get("on")) and FEAT.on("overlay") and FEAT.on("music")

    def music_on(self):
        """Wanted, and the overlay is on: the window shows."""
        return self.music_wanted() and self.ov_enabled()

    def music_set(self, on):
        MU.cfg()["on"] = bool(on)
        from . import features as FEAT
        FEAT.beta_on("music", bool(on))
        save_json("settings.json", SETTINGS)
        self.music_sync()
        v = getattr(self, "al_music", None)
        if v is not None and bool(v.get()) != bool(on):
            v.set(bool(on))

    def music_shown(self):
        w = getattr(self, "mu_win", None)
        try:
            return w is not None and w.winfo_exists()
        except tk.TclError:
            return False

    def music_sync(self):
        """Shown while it's on (and the overlay is), gone when it's off."""
        try:
            if self.music_on() and not self.music_shown():
                self.music_build().show()
            elif not self.music_on() and self.music_shown():
                self.music_close()
        except Exception:
            self.log_error("the Music Controls")

    def music_restyle(self):
        """The overlay's style or lock changed: built again, where it was."""
        if self.music_shown():
            self.music_close()
            self.music_sync()

    def music_close(self):
        w, self.mu_win = getattr(self, "mu_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def _music_spot(self):
        c = MU.cfg()
        if c["x"] is not None and c["y"] is not None:
            return int(c["x"]), int(c["y"])
        from .alerts_page import game_rect                # first time: top right of the game, below its edge
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        return r[0] + int(r[2] * 0.80), r[1] + int(r[3] * 0.06)

    def music_build(self):
        from .overlaywin import OverlayWindow, pal
        from .style import Tooltip
        P = pal()
        bg, txt = P["bg"], P["text"]
        locked = bool(self.tracker_cfg().get("mlocked"))

        def moved(x, y, _w, _h):
            MU.cfg().update(x=int(x), y=int(y))
            save_json("settings.json", SETTINGS)
        x, y = self._music_spot()
        w = OverlayWindow(self.root, "Music", "♪", (x, y, None, None), palette=P, locked=locked,
                          on_lock=self.overlay_lock, on_close=lambda: self.music_set(False), on_moved=moved,
                          follow_game=True, no_activate=True, resizable=False)
        w.withdraw()
        body = tk.Frame(w.body, bg=bg, padx=8, pady=4)
        body.pack(fill="both", expand=True)
        self.mu_btns = {}
        for i, (what, icon, name) in enumerate(MU.BUTTONS):
            b = tk.Label(body, text=icon, bg=P["cell_bg"], fg=txt, font=(P["font"], self.ov_font(13)), width=3,
                         pady=2, cursor="hand2", highlightthickness=1,
                         highlightbackground=P.get("cell_line") or P["line"])
            b.grid(row=0, column=i, padx=2)
            b.bind("<Button-1>", lambda e, k=what: self.music_press(k))
            Tooltip(b, name)
            self.mu_btns[what] = b
        self.mu_win = w
        return w

    def music_press(self, what):
        """One click = one command to your media player."""
        w = getattr(self, "mu_win", None)
        hwnd = None
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(w.winfo_id()) or w.winfo_id()
        except Exception:
            pass
        ok = MU.send(what, hwnd)
        b = getattr(self, "mu_btns", {}).get(what)
        if b is not None:
            from .overlaywin import pal
            P = pal()
            try:
                b.config(bg=P.get("on_bg") or P["line"])
                b.after(160, lambda: b.winfo_exists() and b.config(bg=P["cell_bg"]))
            except tk.TclError:
                pass
        if not ok and not getattr(self, "mu_warned", False):
            self.mu_warned = True
            buglog.debug("Music", f"no media player reached ({what})")
            self._say("Music Controls couldn't reach a media player. Linux needs playerctl.", 8)
        return ok
