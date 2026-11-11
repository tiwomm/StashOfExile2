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
HUD_EVERY = 1.0                 # 2.131.5: seconds between looks at the game's tribute counter (in a map)
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
        from . import features as FEAT
        return bool(c.get("on") and c.setdefault("favours", True) and FEAT.on("overlay"))

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
        misses, last_sig, shown, counts, seen_at = 0, None, False, {}, None
        sticky = {}                                            # 2.130.4: (r, c) -> (name, its feats, score)

        def still_open(img, at):
            """2.130.0 (feedback: "it won't stop FLASHING TO OFFER TRIBUTE WITH THE WINDOW OPEN"): the title wasn't
            found, but most of the cells last seen holding items still hold them where they were - the window is
            open, a tooltip is over its title."""
            if not at or not at[1]:
                return False
            try:
                now = set(FV.occupied(img, at[0]))
            except Exception:
                return False
            return len(now & at[1]) >= max(2, 0.5 * len(at[1]))
        from . import remnant as RM                             # (its OCR reads the tribute)
        belts = FV.belt_refs()
        stars = FV.star_refs()                                  # 2.129.3: Rite of Passage ...
        hud = {"at": 0.0, "reads": [], "sent": "-", "num_at": 0.0, "n": None}

        def hud_look(g):
            """2.131.5: the game's tribute counter (bottom middle) about once a second in a map -> the Ritual line,
            and the reads the reminder checks after the window closes."""
            if time.time() - hud["at"] < HUD_EVERY or getattr(self, "br_area", None) not in ("map", None):
                return
            hud["at"] = time.time()
            n = self.favours_hud_read(sct, g, RM, np)
            hud["reads"] = (hud["reads"] + [(hud["at"], n)])[-12:]
            if n is not None:
                hud["num_at"], hud["n"] = hud["at"], n
            two = [x for _t, x in hud["reads"][-2:]]
            show = n if n is not None else (None if len(two) == 2 and two == [None, None] else hud["sent"])
            if show != hud["sent"]:
                hud["sent"] = show
                self.ui_q.put(("ritual_tribute", show))

        def hud_says_offered(at, was):
            """After the window closed (at) with `was` on the counter: it counted down, or went -> True."""
            if was is None:
                return None
            since = [x for t, x in hud["reads"] if t >= at]
            if any(x is not None and x < was for x in since):
                return "it counted down"
            if len(since) >= 2 and since[-1] is None and since[-2] is None:
                return "it went"
            return None
        with mss.mss() as sct:
            while gen == getattr(self, "fv_gen", 0):
                time.sleep(POLL)
                try:
                    if not game_active():
                        continue
                    g = game_rect()
                    if not g:
                        continue
                    try:
                        hud_look(g)
                    except Exception:
                        buglog.caught()
                    gx, gy, gw, gh = g
                    w, h = int(gw * GRAB[0]), int(gh * GRAB[1])
                    shot = sct.grab({"left": gx, "top": gy, "width": w, "height": h})
                    img = np.asarray(shot)[:, :, :3]
                    win = FV.find_window(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), tpl, gh, gw)
                    if win is None and shown and still_open(img, seen_at):
                        misses = 0                                   # 2.130.0: the title is covered (a reward's
                        continue                                     # tooltip) - its cells are still there
                    if win is None:
                        misses += 1
                        if misses == GONE and shown:
                            shown, last_sig = False, None
                            sticky.clear()
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
                                btn = FV.tribute_offered(*last)
                                if btn:
                                    counts["offered"] = True
                                counts["btn"] = {True: "gray", False: "red"}.get(btn, "unsure")
                            owed = 0 if counts.get("offered") else (counts.get("tribute") or 0)
                            if counts.get("offered") and (counts.get("tribute") or 0) > 0:
                                fv_log("closed while the tribute counted down - the button was gray: no reminder")
                            hud_was = hud["n"] if time.time() - hud["num_at"] < 5 else None
                            counts = {"owed": owed, "btn": counts.get("btn", "unseen"), "closed_at": time.time(),
                                      "hud": hud_was} if owed > 0 else {}
                        elif misses == REMIND and counts.get("owed"):     # 2.130.0: still gone - really closed
                            # 2.131.5 (feedback: "it doesn't turn gray when I click it and rapidly close the
                            # window"): the game's counter says - it counted down or went: offered, no reminder
                            why = hud_says_offered(counts.get("closed_at", 0), counts.get("hud"))
                            if why:
                                fv_log(f"closed with {counts['owed']:,} tribute left, but the counter at the bottom "
                                       f"{why}: offered - no reminder")
                                counts = {}
                                continue
                            fv_log(f"closed with {counts['owed']:,} tribute left (button {counts.pop('btn', '?')}, "
                                   f"counter {counts.get('hud') if counts.get('hud') is not None else 'not seen'}): "
                                   "reminder")
                            self.ui_q.put(("favours_tribute", counts.pop("owed")))
                        continue
                    if misses >= GONE and counts.pop("owed", None):     # 2.130.0: back before the reminder - only
                        fv_log("window back (a tooltip hid it): no reminder")   # hidden for a moment
                    misses = 0
                    counts["last"] = (img, win)
                    if FV.tribute_offered(img, win):          # 2.131.2: the button went gray - offered (or none)
                        counts["offered"] = True
                        if not counts.get("said_offered"):    # 2.131.4 (feedback: "still asking me to offer tribute
                            counts["said_offered"] = True     # after I already dumped tribute"): open again with
                            self.ui_q.put(("favours_offered",))   # nothing owed - a reminder up takes itself back
                    if time.time() - counts.get("at", 0) > 1.5:          # the tribute, now and then
                        counts["at"] = time.time()
                        t = self.favours_tribute_read(img, win, RM)
                        if t is not None:
                            counts["tribute"] = t
                    grid = FV.grid_box(win)
                    occ = FV.occupied(img, grid)
                    seen_at = (grid, set(occ))
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
                    if moved:
                        sticky.clear()                       # (new rewards: nothing carried over)
                    last_sig = sig
                    refs = getattr(self, "fv_refs", None) or FV.Refs()
                    rows, seen, left = [], [], []
                    known_f, unknown_f = [], []
                    for r, c in FV.single_cells(occ):
                        f = FV.cell_feats(img, grid, r, c)
                        if f is None:
                            continue
                        name, sc, _m = refs.best(f)
                        if name:
                            rows.append({"r": r, "c": c, "name": name, "score": sc,
                                         "box": FV.cell_rect(grid, r, c)})
                            known_f.append((f, name))
                            sticky[(r, c)] = (name, f, sc)
                            continue
                        unknown_f.append(((r, c), f))
                    tw = FV.twins(known_f, unknown_f)                 # 2.130.4: a copy of a named reward
                    # 2.130.4: a cell named in an earlier look at these same rewards keeps its name when a later look
                    # misses it (the golden omens sparkle - one frame matches, the next may not)
                    for (r, c), f in unknown_f:
                        old_ = sticky.get((r, c))
                        if (r, c) not in tw and old_ and FV.score(f["top"], old_[1]["top"]) >= FV.TWIN - 0.1:
                            tw[(r, c)] = (old_[0], old_[2])
                    for (r, c), f in unknown_f:
                        if (r, c) in tw:
                            rows.append({"r": r, "c": c, "name": tw[(r, c)][0], "score": tw[(r, c)][1],
                                         "box": FV.cell_rect(grid, r, c), "twin": True})
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
                    said_ = (len(occ), len(rows))
                    if shown and not tw and said_ != counts.get("said"):     # (2.130.4: a later look that differs)
                        fv_log(f"read again: {len(occ)} cells hold items, {len(rows)} known")
                    counts["said"] = said_
                    if not shown or tw:
                        fv_log(f"window {'open' if not shown else 'read again'}: {len(occ)} cells hold items, "
                               f"{len(rows)} known ({len(tw)} as a copy of another) - "
                               + ", ".join(f"{x['name']} ({x['score']:.2f})" for x in rows[:16])
                               + (f"; not sure: {'; '.join(seen[:8])}" if seen else ""))
                    shown = True
                    self.ui_q.put(("favours", g, rows))
                except Exception as e:
                    fv_log(f"read failed: {e.__class__.__name__}: {e}")
        self.fv_alive = False if gen == getattr(self, "fv_gen", 0) else self.fv_alive

    @staticmethod
    def favours_hud_read(sct, g, RM, np):
        """2.131.5: the game's tribute counter (bottom middle) -> its number, or None (not there / not read)."""
        try:
            shot = np.asarray(sct.grab(FV.hud_rect(g)))[:, :, :3]
            return FV.hud_number(RM.ocr(FV.hud_prep(shot)))
        except Exception:                                  # (no OCR: the line shows no tribute)
            return None

    def ev_ritual_tribute(self, n):
        """2.131.5: the tribute the game's counter shows (None: not on screen) - on the Ritual line."""
        from .utilities import RITUAL
        RITUAL.tribute = n
        self.ritual_readout_sync()

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
        self.fv_owed_at = time.time()
        self.breach_alert(level="tribute", sub=f"{tribute:,} tribute left - offer it to the King")

    def ev_favours_offered(self):
        """2.131.4: the Favours window shows nothing owed (its button is gray) - the tribute reminder, if it's up or
        waiting for the game to be in front, is taken back."""
        self.fv_offered_at = time.time()
        if getattr(self, "br_level", None) == "tribute" and getattr(self, "br_win", None) is not None:
            fv_log("open again with nothing owed: the reminder is taken back")
            self.breach_dismiss()

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
