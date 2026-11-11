"""2.132.3 Ritual Identifier - the alert card when you hover a Ritual Altar, and its row in Overlay ↳ Settings ›
Helpers (ritualid.py reads; hover_page.py looks)."""
import time
import tkinter as tk
from tkinter import ttk

from . import buglog
from . import ritualid as RID
from .config import SETTINGS, save_json
from .style import C, Tooltip

AGAIN_SECS = 120                    # the same type hovered again within this: no second card


class RitualIdPage:
    """Mixed into App."""

    def ritid_on(self):
        from . import features as FEAT
        return bool(RID.cfg().get("on")) and FEAT.on("overlay") and FEAT.on("ritualid")

    def ritid_set(self, on):
        RID.cfg()["on"] = bool(on)
        from . import features as FEAT
        FEAT.beta_on("ritualid", bool(on))
        save_json("settings.json", SETTINGS)
        if on:
            self.hover_start()
            if getattr(self, "br_reader", None) is None:    # (the game's log says when you're in a map)
                try:
                    self.breach_start()
                except Exception:
                    buglog.caught()

    def ritid_seen(self, key, now=None):
        """A type read off an altar's tooltip (or None)."""
        if not key or key not in RID.TYPES:
            return None
        now = time.time() if now is None else now
        last = getattr(self, "rid_told", None)
        if last and last[0] == key and now - last[1] < AGAIN_SECS:
            return None
        self.rid_told = (key, now)
        buglog.debug("Ritual", f"altar type {key}")
        return self.ritid_alert(key)

    def ritid_alert(self, key="tainted", test=False):
        title, sub = RID.card_text(key)
        from . import alertcard
        from .alerts_page import game_rect
        self.rid_win = alertcard.show(self.root, title, sub, color="#e05a4f", mark="☠", secs=5 if test else 10,
                                      game=game_rect(), tag="Ritual type", rank=3)
        return self.rid_win

    # ---------------------------------------------------------------- Overlay ↳ Settings › Helpers: its row
    def ritid_row(self, box, bg, CB):
        sm = ("Segoe UI", 9)
        row = tk.Frame(box, bg=bg)
        row.pack(fill="x", pady=(8, 0))
        self.al_ritid = tk.BooleanVar(value=bool(RID.cfg()["on"]))
        cb = ttk.Checkbutton(row, text="Ritual Identifier (BETA)", variable=self.al_ritid, style=CB,
                             command=lambda: self.ritid_set(bool(self.al_ritid.get())))
        cb.pack(side="left")
        tb = ttk.Button(row, text="Test", width=6, command=lambda: self.ritid_alert(test=True))
        tb.pack(side="left", padx=(8, 0))
        info = tk.Label(row, text="ⓘ", bg=bg, fg=C["muted"], font=sm, cursor="question_arrow")
        info.pack(side="left", padx=(8, 0))
        tk.Label(box, text="Hover a Ritual Altar: its type, loot and danger.", bg=bg, fg=C["muted"], font=sm,
                 anchor="w").pack(fill="x")
        Tooltip(cb, "Off until you turn it on.")
        Tooltip(tb, "Shows a Tainted Ritual card now.")
        Tooltip(info, "In maps only. Reads the altar's tooltip round the mouse. Nothing kept or sent.")
