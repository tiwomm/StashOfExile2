"""2.91.0: Exchange rates over the game - a small window in the overlay's own look (both looks) with today's
most-used rates: how many of each per Divine Orb (cheap ones) or how many divines each is worth (dear ones). Off until
you turn it on (Overlay ↳ Settings › Features); drag it where you like (the overlay's lock locks it too). The numbers
are the Exchange rates table the app already keeps (poe.ninja, once an hour) - nothing extra is fetched.
GGG ToS: a window on top that only shows numbers; nothing is sent to the game."""
import tkinter as tk

from .config import SETTINGS, save_json

# what most players watch, in this order (poe.ninja ids); the ones the table has are shown
COMMON = ("exalted", "chaos", "annul", "vaal", "regal", "gcp", "alch", "greater-exalted-orb", "perfect-exalted-orb",
          "hinekoras-lock", "mirror")
NAMES = {"exalted": "Exalted Orb", "chaos": "Chaos Orb", "annul": "Orb of Annulment", "vaal": "Vaal Orb",
         "regal": "Regal Orb", "gcp": "Gemcutter's Prism", "alch": "Orb of Alchemy", "greater-exalted-orb":
         "Greater Exalted Orb", "perfect-exalted-orb": "Perfect Exalted Orb", "hinekoras-lock": "Hinekora's Lock",
         "mirror": "Mirror of Kalandra"}
REFRESH_MS = 60 * 1000
MAX_ROWS = 8


def rate_rows(table, limit=MAX_ROWS):
    """[(name, text)] from the divine table: cheap items "N per div", dear ones "N div each"."""
    out = []
    for cid in COMMON:
        v = table.get(cid)
        if not v or v <= 0:
            continue
        if v < 1:
            per = 1 / v
            txt = f"{per:,.0f} : 1 div" if per >= 10 else f"{per:.2f} : 1 div"
        else:
            txt = f"{v:,.0f} div each" if v >= 10 else f"{v:.2f} div each"
        out.append((NAMES.get(cid, cid), txt))
        if len(out) >= limit:
            break
    return out


class OverlayRates:
    """Mixed into App."""

    def ovr_cfg(self):
        c = SETTINGS.setdefault("rates_ov", {})
        c.setdefault("on", False)                 # off until you turn it on
        c.setdefault("shown", bool(c["on"]))      # 2.104.1: Rates ▾ on the bar opens / closes it
        c.setdefault("x", None)
        c.setdefault("y", None)
        return c

    def ovr_switch(self, on):
        """2.104.1 (feedback: it didn't work like Notes / Calc / Regex): the switch puts Rates ▾ on the bar; the
        button opens / closes the window."""
        c = self.ovr_cfg()
        c["on"] = bool(on)
        if not on:
            c["shown"] = False
        save_json("settings.json", SETTINGS)
        if not on:
            self.ovr_close()
        self._ovr_bar()

    def ovr_shown(self):
        return getattr(self, "ovr_win", None) is not None

    def ovr_toggle(self, show=None):
        show = (not self.ovr_shown()) if show is None else bool(show)
        c = self.ovr_cfg()
        c["shown"] = bool(show and c["on"])
        save_json("settings.json", SETTINGS)
        if c["shown"] and self.ov_enabled():
            self.ovr_build()
        else:
            self.ovr_close()
        self._ovr_bar()
        return c["shown"]

    def _ovr_bar(self):
        if getattr(self, "mg_win", None) is not None:
            try:
                self.merged_build()                      # (Rates ▾ / ▴ on the bar)
            except Exception:
                pass

    def ovr_restore(self):
        if self.ovr_cfg()["on"] and self.ovr_cfg()["shown"] and self.ov_enabled():   # 2.92.2: not while disabled
            try:
                self.ovr_build()
            except Exception:
                self.log_error("showing the exchange rates over the game")

    def ovr_close(self):
        job, self._ovr_job = getattr(self, "_ovr_job", None), None
        if job:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        w, self.ovr_win = getattr(self, "ovr_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def _ovr_spot(self):
        c = self.ovr_cfg()
        if c["x"] is not None and c["y"] is not None:
            return int(c["x"]), int(c["y"])
        from .alerts_page import game_rect                # first time: top right of the game, under its own icons
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        return r[0] + int(r[2] * 0.80), r[1] + int(r[3] * 0.18)

    def ovr_palette(self):
        """The overlay's own look: the Game bar's colours over the game bar layout, the Panel's card colours otherwise."""
        from .overlaywin import pal
        return pal()                                     # 2.109.0: the overlay's chosen style

    def ovr_build(self):
        from .overlaywin import OverlayWindow
        self.ovr_close()
        P = self.ovr_palette()
        locked = bool(self.tracker_cfg().get("mlocked"))

        def moved(x, y, _w, _h):
            self.ovr_cfg().update(x=int(x), y=int(y))
            save_json("settings.json", SETTINGS)
        x, y = self._ovr_spot()
        w = OverlayWindow(self.root, "Exchange rates", "⇄", (x, y, None, None), palette=P, locked=locked,
                          on_lock=self.overlay_lock, on_close=lambda: self.ovr_toggle(False), on_moved=moved,
                          follow_game=True, resizable=False, no_activate=True)
        w.withdraw()
        body = tk.Frame(w.body, bg=P["bg"], padx=8, pady=8)
        body.pack(fill="both", expand=True)
        self.ovr_body, self.ovr_P, self.ovr_win = body, P, w
        self.ovr_fill()
        w.show()
        return w

    def ovr_fill(self):
        from .rates import RATES
        body, P = getattr(self, "ovr_body", None), getattr(self, "ovr_P", None)
        if body is None:
            return
        try:
            for c in body.winfo_children():
                c.destroy()
        except tk.TclError:
            return
        rows = rate_rows(RATES.table or {})
        self.ovr_rows = rows
        if not rows:
            tk.Label(body, text="No rates yet - they load once the league is set.", bg=P["bg"], fg=P["muted"],
                     font=(P["font"], self.ov_font(9))).grid(row=0, column=0, sticky="w")
        for i, (name, txt) in enumerate(rows):
            tk.Label(body, text=name, bg=P["bg"], fg=P["text"], font=(P["font"], self.ov_font(10)), anchor="w").grid(
                row=i, column=0, sticky="w", padx=(0, 12))
            tk.Label(body, text=txt, bg=P["bg"], fg=P.get("head", P["text"]), font=(P["font"], self.ov_font(10), "bold"),
                     anchor="e").grid(row=i, column=1, sticky="e")
        age = RATES.age()
        if age is not None:
            tk.Label(body, text=f"poe.ninja · {int(age // 60)} min ago", bg=P["bg"], fg=P["muted"],
                     font=(P["font"], self.ov_font(8))).grid(row=len(rows) + 1, column=0, columnspan=2, sticky="w",
                                                             pady=(4, 0))
        w = getattr(self, "ovr_win", None)                       # 2.96.1 (feedback: it couldn't be moved): unlocked,
        if w is not None and not w.locked:                         # any spot on it drags it, not just its title bar
            for c in [body] + list(body.winfo_children()):
                w.draggable(c)
        self._ovr_job = self.root.after(REFRESH_MS, self.ovr_fill)
