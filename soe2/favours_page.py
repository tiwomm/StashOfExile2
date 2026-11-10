"""2.128.0 Favours prices in the app (the Ritual helper's option): the watcher thread, the price tags over the game,
and learning a reward's picture when you price check it. The reading itself is in favours.py.
Switch: Overlay › Settings › Helpers › Ritual › Favours prices (on with the Ritual helper)."""
import os
import threading
import time
import tkinter as tk
from tkinter import font as tkfont

from . import buglog
from . import favours as FV
from .config import P, SETTINGS, save_json
from .pricefmt import fmt_short

POLL = 0.5                     # seconds between looks while the game is in front
GONE = 2                       # looks without the window = it closed: the tags go
GRAB = (0.62, 0.80)            # the part of the game that is looked at (from its top-left): the window is there


def fv_log(line):
    try:
        d = P("ritual")
        os.makedirs(d, exist_ok=True)
        f = os.path.join(d, "favours_log.txt")
        if os.path.exists(f) and os.path.getsize(f) > 300_000:
            os.replace(f, os.path.join(d, "favours_log.old.txt"))
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {line}\n")
    except Exception:
        buglog.caught()


class FavoursPage:
    def favours_on(self):
        c = self.ritual_cfg()
        return bool(c.get("on") and c.setdefault("favours", True))

    def favours_changed(self, on):
        self.ritual_cfg()["favours"] = bool(on)
        save_json("settings.json", SETTINGS)
        self.favours_sync()

    def favours_sync(self):
        """Start / stop the watcher to match the switches (the Ritual helper on, and Favours prices on)."""
        want = self.favours_on()
        alive = getattr(self, "fv_alive", False)
        if want and not alive:
            self.fv_gen = getattr(self, "fv_gen", 0) + 1
            self.fv_alive = True
            threading.Thread(target=self._fv_watch, args=(self.fv_gen,), daemon=True).start()
        elif not want and alive:
            self.fv_gen = getattr(self, "fv_gen", 0) + 1
            self.fv_alive = False
            self.favours_hide()

    # ---------------------------------------------------------------- the pictures to compare with
    def favours_refs(self, fetch=True):
        """Build them (a background thread): poe.ninja's exchange items with a picture, downloaded once."""
        from .config import APP_UA
        from .wealth import WPRICES
        items = FV.ninja_items(getattr(WPRICES, "parts", None))
        if fetch and items:
            got = FV.fetch_art(items, APP_UA)
            if got:
                fv_log(f"downloaded {got} item pictures")
        self.fv_refs = FV.build_refs(items)
        self.fv_names = {nid: name for nid, (name, _p) in items.items()}
        return self.fv_refs

    # ---------------------------------------------------------------- the watcher (its own thread)
    def _fv_watch(self, gen):
        from .alerts_page import game_rect
        from .overlay import game_active
        try:
            import cv2
            import mss
            import numpy as np
        except Exception as e:
            fv_log(f"can't run: {e.__class__.__name__}: {e}")
            self.fv_alive = False
            return
        tpl = FV.title_template()
        if tpl is None:
            fv_log("favours_title.png is missing from the app")
            self.fv_alive = False
            return
        try:
            self.favours_refs()
        except Exception as e:
            fv_log(f"pictures: {e.__class__.__name__}: {e}")
        misses, last_sig, shown = 0, None, False
        with mss.mss() as sct:
            while gen == getattr(self, "fv_gen", 0):
                time.sleep(POLL)
                try:
                    if not game_active():
                        continue
                    g = game_rect()
                    if not g:
                        continue
                    gx, gy, gw, gh = g
                    w, h = int(gw * GRAB[0]), int(gh * GRAB[1])
                    shot = sct.grab({"left": gx, "top": gy, "width": w, "height": h})
                    img = np.asarray(shot)[:, :, :3]
                    win = FV.find_window(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), tpl, gh, gw)
                    if win is None:
                        misses += 1
                        if misses == GONE and shown:
                            shown, last_sig = False, None
                            self.ui_q.put(("favours", g, []))
                        continue
                    misses = 0
                    grid = FV.grid_box(win)
                    occ = FV.occupied(img, grid)
                    sig = tuple(sorted(occ.items())), cv2.resize(img[grid[1]:grid[1] + int(grid[2] * FV.ROWS),
                                                                     grid[0]:grid[0] + int(grid[2] * FV.COLS)],
                                                                 (48, 40)).tobytes()
                    self.fv_last = (time.time(), g, grid, img)     # (price checking a reward teaches its picture)
                    if sig == last_sig:
                        continue
                    last_sig = sig
                    refs = getattr(self, "fv_refs", None) or FV.Refs()
                    rows = []
                    for r, c in FV.single_cells(occ):
                        cut = FV.cell_crop(img, grid, r, c)
                        if not cut.size:
                            continue
                        name, sc, _m = refs.best(FV.feats(cut))
                        if name:
                            rows.append({"r": r, "c": c, "name": name, "score": sc,
                                         "box": FV.cell_rect(grid, r, c)})
                    if not shown:
                        fv_log(f"window open: {len(occ)} cells hold items, {len(rows)} known - "
                               + ", ".join(f"{x['name']} ({x['score']:.2f})" for x in rows[:12]))
                    shown = True
                    self.ui_q.put(("favours", g, rows))
                except Exception as e:
                    fv_log(f"read failed: {e.__class__.__name__}: {e}")
        self.fv_alive = False if gen == getattr(self, "fv_gen", 0) else self.fv_alive

    # ---------------------------------------------------------------- the tags
    def ev_favours(self, g, rows):
        if not rows:
            return self.favours_hide()
        from .wealth import WPRICES
        priced = []
        for row in rows:
            each = WPRICES.named(row["name"])
            priced.append(dict(row, each=each))
        best = max((x for x in priced if x["each"] is not None), key=lambda x: x["each"], default=None)
        self.favours_show(g, priced, best)

    def favours_show(self, g, rows, best=None):
        """One small click-through tag per known reward, at the foot of its cell, in the overlay style's colors (like
        the Expedition helper's); the dearest one in the warm color with a ★."""
        self.favours_hide()
        from .overlaywin import pal, skinned
        from .remnant_page import no_capture
        P_ = pal()
        gx, gy, _gw, gh = g
        ui = max(0.7, gh / 1440.0)
        size = -max(10, int(12 * ui))
        BG, TXT, MUT = P_["bg"], P_["text"], P_["muted"]
        WARM = P_["warn"] if skinned() else "#ffd25a"
        EDGE = P_["line"] if skinned() else "#3d5582"
        wins = []
        for row in rows:
            x, y, w, h = row["box"]
            if row["each"] is None:
                txt, fg, edge = "no price", MUT, EDGE
            else:
                txt, fg, edge = fmt_short(row["each"]), TXT, EDGE
            if row is best:
                txt, fg, edge = "★ " + txt, WARM, WARM
            t = tk.Toplevel(self.root)
            t.withdraw()
            t.overrideredirect(True)
            try:
                t.attributes("-topmost", True)
            except tk.TclError:
                pass
            bold = row is best
            f = tkfont.Font(root=t, family="Segoe UI", size=size, weight="bold" if bold else "normal")
            tk.Label(t, text=txt, fg=fg, bg=BG, font=f, padx=4, pady=0, highlightthickness=1,
                     highlightbackground=edge).pack()
            t.update_idletasks()
            tw, th = t.winfo_reqwidth(), t.winfo_reqheight()
            t.geometry(f"+{int(gx + x + (w - tw) / 2)}+{int(gy + y + h - th - 2)}")
            t.deiconify()
            try:
                from .alerts_page import click_through, force_topmost
                click_through(t)
                force_topmost(t)
            except Exception:
                buglog.caught()
            no_capture(t)
            wins.append(t)
        self.fv_wins = wins or None

    def favours_hide(self):
        wins, self.fv_wins = getattr(self, "fv_wins", None), None
        for w in wins or ():
            try:
                w.destroy()
            except tk.TclError:
                pass

    # ---------------------------------------------------------------- learning a reward's picture
    def favours_learn(self, name):
        """Your price check key on a reward while the Favours window is open: remember what it looks like (the cell
        under the mouse, from the last look). -> True if learned."""
        last = getattr(self, "fv_last", None)
        if not name or not last or time.time() - last[0] > 3:
            return False
        _t, g, grid, img = last
        try:
            mx, my = self.root.winfo_pointerxy()
        except tk.TclError:
            return False
        cs = grid[2]
        c, r = int((mx - g[0] - grid[0]) // cs), int((my - g[1] - grid[1]) // cs)
        if not (0 <= r < FV.ROWS and 0 <= c < FV.COLS):
            return False
        x, y, w, h = FV.cell_rect(grid, r, c)
        if FV.backing(img[y + 6:y + h - 6, x + 6:x + w - 6]) is None:
            return False
        if not FV.learn(name, FV.cell_crop(img, grid, r, c)):
            return False
        fv_log(f"learned the picture of {name} (cell {r},{c})")
        threading.Thread(target=lambda: self.favours_refs(fetch=False), daemon=True).start()
        return True
