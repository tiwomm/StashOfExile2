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
# 2.130.0 (feedback: "still telling me with favours window open to offer tribute"): a reward's tooltip over the
# window's title hid it for a second - the reminder waits until the window has been gone this many looks (4 s)
REMIND = 8
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
    def favours_refs(self, fetch=False):
        """Build them (a background thread): the Ritual tab's omens that ship with the app, and the pictures learned
        on this PC - poe.ninja's exchange items only."""
        from .wealth import WPRICES
        items = FV.ninja_items(getattr(WPRICES, "parts", None))
        self.fv_refs = FV.build_refs(items)
        self.fv_stars = FV.star_refs()
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
        misses, last_sig, shown, counts = 0, None, False, {}
        from . import remnant as RM                             # (its OCR reads the tribute)
        belts = FV.belt_refs()
        stars = FV.star_refs()                                  # 2.129.3: Rite of Passage ...
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
                            # 2.129.0 (feedback): closed with tribute to spend - offer it. 2.129.3 (feedback: "you
                            # can offer tribute no matter if you have rerolls or not ... no matter what it should
                            # ask"): rerolls don't count; offered (0 left) - nothing.
                            # The tribute is read from the last look before it closed, not one up to 1.5 s older
                            # (2.129.3, feedback: "ONLY ... after ... not offering tribute").
                            last = counts.get("last")
                            if last is not None:
                                t = self.favours_tribute_read(*last, RM)
                                if t is not None:
                                    counts["tribute"] = t
                            owed = counts.get("tribute") or 0
                            counts = {"owed": owed} if owed > 0 else {}
                        elif misses == REMIND and counts.get("owed"):     # 2.130.0: still gone - really closed
                            fv_log(f"closed with {counts['owed']:,} tribute left: reminder")
                            self.ui_q.put(("favours_tribute", counts.pop("owed")))
                        continue
                    if misses >= GONE and counts.pop("owed", None):     # 2.130.0: back before the reminder - only
                        fv_log("window back (a tooltip hid it): no reminder")   # hidden for a moment
                    misses = 0
                    counts["last"] = (img, win)
                    if time.time() - counts.get("at", 0) > 1.5:          # the tribute, now and then
                        counts["at"] = time.time()
                        t = self.favours_tribute_read(img, win, RM)
                        if t is not None:
                            counts["tribute"] = t
                    grid = FV.grid_box(win)
                    occ = FV.occupied(img, grid)
                    # (2.128.1: what's in the cells' top parts - the tags at their feet don't count as a change)
                    sig = tuple(sorted(occ.items())), b"".join(
                        cv2.resize(FV.cell_crop(img, grid, r, c), (8, 6)).tobytes() for r, c in sorted(occ))
                    self.fv_last = (time.time(), g, grid, img)     # (price checking a reward teaches its picture)
                    if sig == last_sig:
                        continue
                    moved = last_sig is None or set(sig[0]) != set(last_sig[0])     # (cells filled / emptied,
                    if not moved and len(sig[1]) == len(last_sig[1]) and sig[1]:     # or most of them clearly
                        a_ = np.frombuffer(sig[1], np.uint8).reshape(-1, 144).astype(np.int16)     # changed: a
                        b_ = np.frombuffer(last_sig[1], np.uint8).reshape(-1, 144).astype(np.int16)  # reroll, not
                        moved = (np.abs(a_ - b_).mean(1) > 14).mean() >= 0.6                       # a tooltip)
                    if shown and moved and getattr(self, "fv_wins", None):   # 2.129.3: new rewards (a reroll) -
                        self.ui_q.put(("favours", g, []))           # our tags go first: over new rewards they'd spoil
                        time.sleep(0.3)                             # the read (each is also read whole now)
                        img = np.asarray(sct.grab({"left": gx, "top": gy, "width": w, "height": h}))[:, :, :3]
                        win = FV.find_window(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), tpl, gh, gw)
                        if win is None:
                            continue
                        grid = FV.grid_box(win)
                        occ = FV.occupied(img, grid)
                        sig = tuple(sorted(occ.items())), b"".join(
                            cv2.resize(FV.cell_crop(img, grid, r, c), (8, 6)).tobytes() for r, c in sorted(occ))
                        self.fv_last = (time.time(), g, grid, img)
                    last_sig = sig
                    refs = getattr(self, "fv_refs", None) or FV.Refs()
                    rows, seen, left = [], [], []
                    for r, c in FV.single_cells(occ):
                        f = FV.cell_feats(img, grid, r, c)
                        if f is None:
                            continue
                        name, sc, _m = refs.best(f)
                        if name:
                            rows.append({"r": r, "c": c, "name": name, "score": sc,
                                         "box": FV.cell_rect(grid, r, c)})
                            continue
                        left.append((r, c))
                        if not shown:                        # (2.129.0: the log says how close it came)
                            top = refs.ranked(f, 2)
                            if top and top[0][0] > 0.45:
                                seen.append(f"{r},{c}: " + " / ".join(f"{n} {s_:.2f} {k}" for s_, n, k in top))
                    for name, sc, box in FV.find_belts(img, grid, occ, belts):   # ★ Mageblood / Headhunter
                        rows.append({"name": name, "score": sc, "box": box, "belt": True})
                    for name, sc, box in FV.find_stars(img, grid, left, getattr(self, "fv_stars", None) or stars):
                        rows.append({"name": name, "score": sc, "box": box, "belt": True})
                    if not shown:
                        fv_log(f"window open: {len(occ)} cells hold items, {len(rows)} known - "
                               + ", ".join(f"{x['name']} ({x['score']:.2f})" for x in rows[:12])
                               + (f"; not sure: {'; '.join(seen[:8])}" if seen else ""))
                    shown = True
                    self.ui_q.put(("favours", g, rows))
                except Exception as e:
                    fv_log(f"read failed: {e.__class__.__name__}: {e}")
        self.fv_alive = False if gen == getattr(self, "fv_gen", 0) else self.fv_alive

    @staticmethod
    def favours_tribute_read(img, win, RM):
        """The tribute number on the window's plate (OCR), or None."""
        try:
            from PIL import Image
            box = FV.tribute_box(img, win)
            return FV.tribute_of(RM.ocr(Image.fromarray(box[:, :, ::-1]))) if box.size else None
        except Exception:                                  # (no OCR: no reminder, nothing else changes)
            buglog.caught()
            return None

    # ---------------------------------------------------------------- the tags
    def ev_favours(self, g, rows):
        if not rows:
            return self.favours_hide()
        from .wealth import WPRICES
        priced = []
        for row in rows:
            each = None if row.get("belt") else WPRICES.named(row["name"])     # (a belt: a ★ and its name only)
            priced.append(dict(row, each=each))
        best = max((x for x in priced if x["each"] is not None), key=lambda x: x["each"], default=None)
        self.favours_show(g, priced, best)

    def favours_show(self, g, rows, best=None):
        """One small click-through tag per known reward, at the foot of its cell, in the overlay style's colors (like
        the Expedition helper's); the most valuable one in the warm color with a ★."""
        self.favours_hide()
        from .overlaywin import pal, skinned
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
            if row.get("belt"):                           # 2.129.0: Mageblood / Headhunter - worth a look, no price
                txt, fg, edge = "★ " + row["name"], WARM, WARM
            elif row["each"] is None:
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
            # (2.128.1, feedback: "show up on screenshots / screen share / streaming": not left out of captures)
            wins.append(t)
        self.fv_wins = wins or None

    def ev_favours_tribute(self, tribute):
        """2.129.0 (feedback): the Favours window closed with tribute still to spend (2.129.3: rerolls or not)."""
        if not self.ritual_cfg().get("tribute_reminder", True):
            return
        self.breach_alert(level="tribute", sub=f"{tribute:,} tribute left - offer it to the King")

    def favours_hide(self):
        wins, self.fv_wins = getattr(self, "fv_wins", None), None
        for w in wins or ():
            try:
                w.destroy()
            except tk.TclError:
                pass

    # ---------------------------------------------------------------- learning a reward's picture
    def favours_copy_learn(self, text):
        """2.129.3 (feedback: omens, idols and Sacred Bloom went unpriced): any copy of a reward's text (Ctrl+C or
        your price check key) while the Favours window is open teaches its picture - exchange items (priced), and the
        uniques that get a ★ (FV.STARS). -> True if learned."""
        if not getattr(self, "fv_last", None) or time.time() - self.fv_last[0] > 3:
            return False
        lines = [ln.strip() for ln in str(text or "").splitlines()]
        i = next((k for k, ln in enumerate(lines) if ln.startswith("Rarity:")), None)
        if i is None or i + 1 >= len(lines):
            return False
        rarity, name = lines[i][7:].strip(), lines[i + 1]
        if rarity == "Unique" and name not in FV.STARS:
            return False
        if rarity not in ("Currency", "Unique", "Gem"):
            return False
        return self.favours_learn(name)

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
        if FV.backing(img[y + 6:y + int(h * FV.TOP), x + 6:x + w - 6]) is None:
            return False
        if not FV.learn(name, FV.cell_crop(img, grid, r, c), FV.cell_inside(img, grid, r, c)):
            return False
        fv_log(f"learned the picture of {name} (cell {r},{c})")
        threading.Thread(target=lambda: self.favours_refs(fetch=False), daemon=True).start()
        return True
