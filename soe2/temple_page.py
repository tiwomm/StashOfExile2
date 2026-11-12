"""2.132.1 Temple Helper - the watcher (a look round the mouse in maps, for the Vaal Beacon's tooltip), the crystals
on the line above the bar (2.132.2, with Ritual's - the bar had no room) and the alert card when they're full; its row in Overlay ↳ Overlay Settings › Helpers (temple.py reads)."""
import tkinter as tk

from . import buglog
from . import temple as TM
from .config import SETTINGS, save_json


class TemplePage:
    """Mixed into App."""

    def temple_on(self):
        from . import features as FEAT
        return bool(TM.cfg().get("on")) and FEAT.on("overlay") and FEAT.on("temple")     # (2.132.2: BETA)

    def temple_set(self, on):
        TM.cfg()["on"] = bool(on)
        if not on:
            self.temple_pad_close()                         # 2.136.0
        elif getattr(self, "tm_in_temple", False) and TM.cfg().get("notepad", True):
            self.root.after_idle(self.temple_pad_show)
        from . import features as FEAT
        FEAT.beta_on("temple", bool(on))
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
        self.hover_start()                                  # 2.132.3: one look round the mouse feeds every reader

    def temple_look(self, force=False):
        return self.hover_look(force)

    def temple_seen(self, got):
        """A read (have, most) or None (no tooltip there)."""
        if not got:
            return None
        old = TM.state()
        st = TM.state_set(*got)
        if not old or (old["have"], old["most"]) != got:
            buglog.debug("Temple", f"crystals {got[0]}/{got[1]}")
            self.temple_pad_refresh()
            try:
                self.ritual_readout_sync()
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
        self.tm_win = alertcard.show(self.root, "Crystals full", f"Energised Beacons {st['have']}/{st['most']} "
                                     f"({TM.runs(st)} runs). Placed rooms stay until destabilized.", color="#d9a441", mark="◆", secs=5 if test else 10,
                                     game=game_rect(), tag="Temple", rank=1, vital=True)
        return self.tm_win

    # ---------------------------------------------------------------- 2.136.0: the Temple Notepad
    # (feedback: "possibly have a copy of our notepad as a temple notepad" - recommended: its own Notes-style window
    # that shows only inside the temple). Your crystals and runs on top, a page to type your plan on, the reminder
    # that placed rooms stay. Dragged anywhere, in the overlay's style; its text and spot are kept (temple.json via
    # SETTINGS["temple"]); Helpers › Temple › Temple Notepad switches it.
    def temple_area(self, area_id):
        """Every area change: in the temple -> the notepad shows (when it's on); anywhere else -> it goes."""
        here = str(area_id or "") in TM.TEMPLE_AREAS
        self.tm_in_temple = here
        if here and self.temple_pad_on():
            self.temple_pad_show()
        elif not here:
            self.temple_pad_close()

    def temple_pad_on(self):
        return self.temple_on() and bool(TM.cfg().get("notepad", True))

    def temple_pad_set(self, on):
        TM.cfg()["notepad"] = bool(on)
        save_json("settings.json", SETTINGS)
        if on and getattr(self, "tm_in_temple", False) and self.temple_on():
            self.temple_pad_show()
        elif not on:
            self.temple_pad_close()

    def temple_pad_shown(self):
        w = getattr(self, "tm_pad", None)
        try:
            return w is not None and w.winfo_exists()
        except tk.TclError:
            return False

    def temple_pad_close(self):
        self._temple_pad_keep()
        w, self.tm_pad = getattr(self, "tm_pad", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def _temple_pad_keep(self):
        t = getattr(self, "tm_pad_text", None)
        try:
            if t is not None and t.winfo_exists():
                TM.cfg()["notes"] = t.get("1.0", "end-1c")
                save_json("settings.json", SETTINGS)
        except tk.TclError:
            pass

    def temple_pad_line(self):
        st = TM.state()
        return TM.bar_text(st) if st else "Crystals ? - hover a Vaal Beacon in a map"

    def temple_pad_show(self):
        if self.temple_pad_shown():
            return self.tm_pad
        from .overlaywin import OverlayWindow, pal
        P = pal()
        c = TM.cfg()
        if c.get("pad_x") is None or c.get("pad_y") is None:
            from .alerts_page import game_rect
            r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
            x, y = r[0] + int(r[2] * 0.02), r[1] + int(r[3] * 0.18)
        else:
            x, y = int(c["pad_x"]), int(c["pad_y"])

        def moved(nx, ny, ww, hh):
            c.update(pad_x=int(nx), pad_y=int(ny), pad_w=int(ww), pad_h=int(hh))
            save_json("settings.json", SETTINGS)
        w = OverlayWindow(self.root, "Temple Notepad", "◆", (x, y, c.get("pad_w") or 300, c.get("pad_h") or 260),
                          palette=P, locked=bool(self.tracker_cfg().get("mlocked")), on_lock=self.overlay_lock,
                          on_close=self.temple_pad_close, on_moved=moved, follow_game=True, min_size=(220, 160))
        w.withdraw()
        body = tk.Frame(w.body, bg=P["bg"], padx=8, pady=8)
        body.pack(fill="both", expand=True)
        self.tm_pad_head = tk.Label(body, text=self.temple_pad_line(), bg=P["bg"], fg=P["head"],
                                    font=(P["font"], self.ov_font(10), "bold"), anchor="w")
        self.tm_pad_head.pack(fill="x")
        tk.Label(body, text="Placed rooms stay until destabilized.", bg=P["bg"], fg=P["muted"],
                 font=(P["font"], self.ov_font(9)), anchor="w").pack(fill="x", pady=(0, 4))
        t = tk.Text(body, bg=P.get("field") or P["cell_bg"], fg=P["text"], insertbackground=P["text"], relief="flat",
                    highlightthickness=1, highlightbackground=P["line"], wrap="word", height=6,
                    font=(P["font"], self.ov_font(10)), padx=8, pady=4)
        t.pack(fill="both", expand=True)
        t.insert("1.0", c.get("notes") or "")
        t.bind("<FocusOut>", lambda _e: self._temple_pad_keep(), add="+")
        t.bind("<KeyRelease>", lambda _e: self._temple_pad_soon(), add="+")
        self.tm_pad, self.tm_pad_text = w, t
        w.show()
        return w

    def _temple_pad_soon(self):
        job = getattr(self, "_tm_pad_job", None)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except tk.TclError:
                pass
        self._tm_pad_job = self.root.after(800, self._temple_pad_keep)

    def temple_pad_restyle(self):
        """The overlay's style or lock changed: built again, where it was."""
        if self.temple_pad_shown():
            self.temple_pad_close()
            self.temple_pad_show()

    def temple_pad_refresh(self):
        """The crystals line follows each new read."""
        lab = getattr(self, "tm_pad_head", None)
        try:
            if lab is not None and lab.winfo_exists():
                lab.config(text=self.temple_pad_line())
        except tk.TclError:
            pass
