"""Overlay recap card (over the game, after a death). Mixed into App."""
import random
import tkinter as tk
from tkinter import ttk

from .config import SETTINGS, save_json

CHANCE = 0.05
HITS = ("2,147,483,647", "9,999,999,999", "69,420,000,000", "1,000,000,000,000")


class OverlayRecap:
    def recap_death(self, who, rng=random):
        """A death in the log: yours, the overlay on, not seen before - a small chance of the card."""
        try:
            if SETTINGS.get("recap_seen") or not self.ov_enabled():
                return None
            if hasattr(self, "tracker_is_me") and not self.tracker_is_me(who):
                return None
            if rng.random() >= CHANCE:
                return None
            SETTINGS["recap_seen"] = True
            save_json("settings.json", SETTINGS)
            return self.recap_show(rng)
        except Exception:
            return None

    def recap_show(self, rng=random):
        from .alerts_page import game_rect
        from .overlaywin import OverlayWindow, pal
        self.recap_close()
        P = pal()
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        W = self.ov_px(420)
        w = OverlayWindow(self.root, "Death Recap", "☠", (r[0] + (r[2] - W) // 2, r[1] + int(r[3] * 0.18), W, None),
                          palette=P, lockable=False, follow_game=True, no_activate=False, on_close=self.recap_close)
        self.recap_win = w
        self.recap_body = tk.Frame(w.body, bg=P["bg"], padx=16, pady=12)
        self.recap_body.pack(fill="both", expand=True)
        a = rng.uniform(.45, .7)
        b = rng.uniform(.1, 1 - a - .05)
        self.recap_split = (("Physical", a, "#c8b48a"), ("Fire", b, "#e0703c"), ("Chaos", 1 - a - b, "#a86ad0"))
        self.recap_hit = rng.choice(HITS)
        self.recap_page(1)
        w.show()
        return w

    def recap_page(self, n):
        from .overlaywin import pal
        P = pal()
        bg, f = P["bg"], self.recap_body
        for c in f.winfo_children():
            c.destroy()
        tk.Label(f, text="☠  DEATH RECAP", bg=bg, fg="#d65a4a", font=(P["font"], self.ov_font(12), "bold"),
                 anchor="w").pack(fill="x")
        tk.Frame(f, bg=P["line"], height=1).pack(fill="x", pady=(8, 8))
        self.recap_btns = {}
        if n == 1:
            tk.Label(f, text="You were slain.", bg=bg, fg=P["head"], font=(P["font"], self.ov_font(11), "bold"),
                     anchor="w").pack(fill="x")
            tk.Label(f, text="Damage taken in the last 5 s", bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(9)),
                     anchor="w").pack(fill="x", pady=(8, 2))
            for name, pct, col in self.recap_split:
                row = tk.Frame(f, bg=bg)
                row.pack(fill="x", pady=1)
                tk.Label(row, text=name, width=9, bg=bg, fg=P["text"], font=(P["font"], self.ov_font(9)),
                         anchor="w").pack(side="left")
                bw = self.ov_px(200)
                cv = tk.Canvas(row, width=bw, height=self.ov_px(10), bg=P.get("cell_bg", P["bg"]), highlightthickness=0)
                cv.pack(side="left")
                cv.create_rectangle(0, 0, int(bw * pct), self.ov_px(10), fill=col, outline="")
                tk.Label(row, text=f"{int(round(pct * 100))}%", bg=bg, fg=P["muted"],
                         font=(P["font"], self.ov_font(9))).pack(side="left", padx=8)
            tk.Label(f, text=f"Biggest hit: {self.recap_hit} · Killer: Unknown", bg=bg, fg=P["muted"],
                     font=(P["font"], self.ov_font(9)), anchor="w").pack(fill="x", pady=(8, 8))
            b = ttk.Button(f, text="Show full recap ▸", style=self.ov_btn("Primary.TButton"),
                           command=lambda: self.recap_page(2))
            b.pack(fill="x")
            self.recap_btns["more"] = b
        else:
            tk.Label(f, text="Analysis complete.", bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(9)),
                     anchor="w").pack(fill="x")
            tk.Label(f, text="( ͡° ͜ʖ ͡°)", bg=bg, fg=P["text"], font=(P["font"], self.ov_font(26))).pack(pady=(8, 0))
            tk.Label(f, text="Skill issue.", bg=bg, fg=P["head"], font=(P["font"], self.ov_font(22), "bold")).pack(
                pady=(4, 16))
            row = tk.Frame(f, bg=bg)
            row.pack(fill="x")
            for k, label in (("true", "True"), ("off", "Fuck off")):
                b = ttk.Button(row, text=label, style=self.ov_btn("TButton"), command=self.recap_close)
                b.pack(side="left", fill="x", expand=True, padx=(0 if k == "true" else 8, 0))
                self.recap_btns[k] = b

    def recap_close(self):
        w, self.recap_win = getattr(self, "recap_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass
