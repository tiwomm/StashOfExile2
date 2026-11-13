"""2.141.0 Vaal Lens (BETA): the marks over the Temple Console - when a card is picked and the game lights the tiles
it can go on, 1 (best) and 2 on two of them with a callout, a dashed ✕ on every lit tile that touches a reward
room, and + where the room it wants goes (2.142.0). A see-through window over the game: clicks go to the game, left out of captures (the board under it is read
too). It only draws; nothing is sent to the game."""
import tkinter as tk

from . import buglog

KEY = "#010203"                 # the see-through color (Windows)
RED = "#ff4d3d"
RIGHT = 1940                    # callouts sit right of the board (its right tip is at x ~1904 in the frame)


class Marks:
    def __init__(self, root):
        self.root = root
        self.win = None
        self.drawn = None

    def _make(self):
        w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=KEY)
        try:
            w.attributes("-transparentcolor", KEY)
        except tk.TclError:
            pass
        self.cv = tk.Canvas(w, bg=KEY, highlightthickness=0, bd=0)
        self.cv.pack(fill="both", expand=True)
        w.withdraw()
        self.win = w
        return w

    def shown(self):
        try:
            return self.win is not None and self.win.winfo_exists() and self.win.winfo_ismapped()
        except tk.TclError:
            return False

    def hide(self):
        self.drawn = None
        if self.win is not None:
            try:
                self.win.withdraw()
            except tk.TclError:
                pass

    def destroy(self):
        w, self.win = self.win, None
        self.drawn = None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def show(self, game, marks, P, font_px=None):
        """game: (left, top, width, height); marks: {tile: ("1" | "2" | "x", why)}; P: the overlay palette."""
        if not marks:
            return self.hide()
        key = (tuple(game), tuple(sorted(marks.items())))
        if key == self.drawn and self.shown():
            return
        from . import vaallens as V
        w = self.win if self.win is not None else self._make()
        gx, gy, gw, gh = (int(v) for v in game)
        w.geometry(f"{gw}x{gh}+{gx}+{gy}")
        cv = self.cv
        cv.delete("all")
        s, left, top = V.placing(game)
        ox, oy = left - gx, top - gy
        hw, hh = 69.3 * s * 0.9, 59.4 * s * 0.9
        # (the ✕ is always red - a theme's warn color can be the accent's orange - and dashed, with a ✕: not color alone)
        accent, warn, ink = P.get("head") or "#f0a04a", RED, P.get("text") or "#ece2cc"
        bg = P.get("bg") or "#15120f"
        fam = P.get("font") or "Segoe UI"
        big = -max(14, int(40 * s))
        small = -max(11, int(22 * s))
        call = {}
        for t, (m, why) in sorted(marks.items(), key=lambda kv: kv[1][0]):
            x, y = V.xy(*t)
            x, y = ox + x * s, oy + y * s
            pts = (x, y - hh, x + hw, y, x, y + hh, x - hw, y)
            if m == "x":
                cv.create_polygon(*pts, fill="", outline=warn, width=max(2, int(4 * s)), dash=(8, 6))
                cv.create_text(x, y, text="✕", fill=warn, font=(fam, big, "bold"))
            elif m == "p":                                  # 2.142.0: the hand's plan (TH, CC, AL...)
                cv.create_polygon(*pts, fill="", outline=accent, width=max(2, int(3 * s)), dash=(4, 4))
                cv.create_text(x, y, text=why, fill=accent, font=(fam, small, "bold"))
            elif m == "+":                                  # 2.142.0: where the room it wants goes, beside 1
                cv.create_polygon(*pts, fill="", outline=accent, width=max(2, int(3 * s)), dash=(4, 4))
                cv.create_text(x, y, text="+", fill=accent, font=(fam, big, "bold"))
            else:
                cv.create_polygon(*pts, fill="", outline=accent, width=max(2, int((6 if m == "1" else 3) * s)))
                cv.create_text(x, y, text=m, fill=accent, font=(fam, big, "bold"))
            call.setdefault(m, (x, y, why))
        # one callout, for the best tile, right of the board (2.142.0, feedback: the ✕ needs no callout - the Vaal
        # Lens card says what it means)
        for m, (title, color) in (("1", ("1 · BEST", accent)),):
            if m not in call:
                continue
            x, y, why = call[m]
            bx, by = ox + RIGHT * s, y - 30 * s
            tid = cv.create_text(bx + 14, by + 10, text=title, fill=color, font=(fam, small, "bold"), anchor="nw")
            wid = cv.create_text(bx + 14, by + 10 + abs(small) * 1.5, text=why[:1].upper() + why[1:],
                                 width=int(440 * s),
                                 fill=ink, font=(fam, small), anchor="nw")
            x0, y0, x1, y1 = cv.bbox(tid)[0], cv.bbox(tid)[1], cv.bbox(wid)[2], cv.bbox(wid)[3]
            x1 = max(x1, cv.bbox(tid)[2])
            box = cv.create_rectangle(x0 - 14, y0 - 10, x1 + 14, y1 + 10, fill=bg, outline="")
            cv.create_line(x0 - 14, y0 - 10, x1 + 14, y0 - 10, fill=color, width=3)
            cv.create_line(x0 - 14, y1 + 10, x1 + 14, y1 + 10, fill=color, width=3)
            cv.create_line(x + hw * 0.6, y, x0 - 14, (y0 + y1) / 2, fill=color, width=2)
            cv.tag_lower(box)
            cv.tag_raise(tid)
            cv.tag_raise(wid)
        self.drawn = key
        w.deiconify()
        w.update_idletasks()
        try:
            from .alerts_page import click_through
            from .remnant_page import no_capture
            click_through(w)
            no_capture(w)
        except Exception:
            buglog.caught()
