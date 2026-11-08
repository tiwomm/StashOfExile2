"""Expedition Remnant Price Checker in the app (2.37.0): the "Remnant" helper next to Delirium, Breach and Ritual -
its row in Overlay › Settings › Helpers, its cell in the timer's Helpers bar, and the price tags over the game.
The reading and matching are in remnant.py. Idea: PoE Ancients Price Helper by Pedro Quitério (no code from it)."""
import sys
import threading
import time
import tkinter as tk

from . import buglog
from . import remnant as RM
from .config import save_json, SETTINGS
from .pricefmt import fmt_short



def capture_affinity(win, hide=True):
    """2.85.2: hide = this window is left out of screen captures (WDA_EXCLUDEFROMCAPTURE: a capture sees what's under
    it); False = back in them. Windows 10 2004+ only; nothing in the game changes."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        u = ctypes.windll.user32
        u.GetParent.restype = ctypes.c_void_p
        u.GetParent.argtypes = [ctypes.c_void_p]
        h = u.GetParent(win.winfo_id()) or win.winfo_id()
        u.SetWindowDisplayAffinity.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        u.SetWindowDisplayAffinity(h, 0x11 if hide else 0x0)
    except Exception:
        buglog.caught()


def no_capture(win):
    """Windows 10 2004+: leave this window out of screen captures (WDA_EXCLUDEFROMCAPTURE), so the Auto watcher -
    and any screenshot - sees the game, not our tags. Only hides it from captures; it changes nothing in the game."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        u = ctypes.windll.user32
        u.GetParent.restype = ctypes.c_void_p
        u.GetParent.argtypes = [ctypes.c_void_p]
        h = u.GetParent(win.winfo_id()) or win.winfo_id()
        u.SetWindowDisplayAffinity.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        u.SetWindowDisplayAffinity(h, 0x11)
    except Exception:
        buglog.caught()


class RemnantPage:
    def remnant_cfg(self):
        c = SETTINGS.setdefault("remnant", {})
        c.setdefault("on", True)     # 2.118.0: on by default (a new install; yours is kept)
        c.pop("sound", None)                        # 2.39.0: no sound (the tags are enough)
        c.pop("auto", None)                         # 2.119.0 (UX pass): always Auto - the watcher shows the tags by
        c.pop("key", None)                          # itself; its Auto switch and Ctrl+Alt+R key are gone
        c.setdefault("area", None)                  # None = RM.AREA (an area learned by the old key is still used)
        c.setdefault("tips", True)                  # 2.40.0: the runeshape cheat sheet next to the tags
        c.setdefault("rumours", True)               # 2.83.0: Island Rumours on the world map, in your hideout
        return c

    def remnant_status(self):
        """off / on / warn (switched on but Windows' text reader can't be used)."""
        if not self.remnant_cfg().get("on"):
            return "off"
        if getattr(self, "rm_problem", None) is None:
            self.rm_problem = RM.ocr_available()
        return "warn" if self.rm_problem else "on"

    def remnant_text(self, row):
        c = self.remnant_cfg()
        if not c.get("on"):
            return row["what"]
        if self.remnant_status() == "warn":
            return f"Can't read the screen: {self.rm_problem}."
        last = getattr(self, "rm_last", "")
        head = "On - prices show by themselves when a remnant's reward book opens"
        return head + (f"  ·  {last}" if last else "")

    def remnant_toggle(self, want):
        c = self.remnant_cfg()
        c["on"] = bool(want)
        save_json("settings.json", SETTINGS)
        self.rm_problem = None
        if not want:
            self.remnant_hide()
            self.ru_stop()                            # 2.83.0: Island Rumours is part of it
        elif getattr(self, "ru_here", False):
            self.ru_start()
        if want and not getattr(self, "_br_ticking", False):
            self.breach_start()                       # 2.83.0: the game's log says where you are
        st = self.remnant_status()
        self.remnant_auto_sync()
        return f"Can't read the screen: {self.rm_problem}." if want and st == "warn" else None

    def remnant_tips_changed(self, on):
        self.remnant_cfg()["tips"] = bool(on)
        save_json("settings.json", SETTINGS)
        for name in ("al_rtips", "rm_tips_var"):               # 2.43.0: Alerts and Settings show the same switch
            v = getattr(self, name, None)
            if v is not None and bool(v.get()) != bool(on):
                v.set(bool(on))
        wins = getattr(self, "rm_win", None)                  # an open book: the tips come or go now
        if wins and getattr(self, "rm_auto_shown", False) and getattr(self, "rm_kept", None):
            self.rm_auto_sig = None
            self.ev_remnant_auto(self.rm_rect, list(self.rm_kept.values()))

    def remnant_tips_never(self):
        """2.98.6: the tips box's "Never show again" - off for good (only its switch turns it back on)."""
        self.remnant_tips_changed(False)
        for w in list(getattr(self, "rm_win", None) or []):
            if getattr(w, "rm_tips", False):
                try:
                    w.destroy()
                except tk.TclError:
                    pass
                self.rm_win.remove(w)
        self._say("Runeshape tips are off. Overlay › Settings › Helpers › Expedition › Runeshape tips turns them back on.", 8)

    # ---------------- Auto: a light watcher on the learned area
    def remnant_auto_sync(self):
        """Start / stop the watcher to match the settings (on + OCR works)."""
        c = self.remnant_cfg()
        want = bool(c.get("on") and self.remnant_status() == "on")
        running = getattr(self, "rm_auto_gen", 0) and getattr(self, "rm_auto_alive", False)
        if want and not running:
            self.rm_auto_gen = getattr(self, "rm_auto_gen", 0) + 1
            self.rm_auto_alive = True
            threading.Thread(target=self._remnant_watch, args=(self.rm_auto_gen,), daemon=True).start()
        elif not want and running:
            self.rm_auto_gen += 1                      # the thread sees a newer generation and stops
            self.rm_auto_alive = False
            if getattr(self, "rm_auto_shown", False):
                self.remnant_hide()

    def _remnant_watch(self, gen):
        from .alerts_page import game_rect
        from .overlay import game_active
        last, misses, settle = None, 0, 0
        try:
            while gen == getattr(self, "rm_auto_gen", 0):
                time.sleep(RM.AUTO_POLL)
                c = SETTINGS.get("remnant") or {}
                area = c.get("area") or RM.AREA
                if not game_active() or getattr(self, "rm_busy", False):
                    continue
                g = game_rect()
                if not g:
                    continue
                rect = (g[0], g[1], g[0] + g[2], g[1] + g[3])
                self.rm_mark_check(rect)              # 2.83.0: in a map, is there an Expedition?
                if not self.rm_zone_ok():
                    continue                          # not in hideouts / towns / campaign
                unsure = self.rm_unsure()             # 2.98.6: a map whose Expedition mark wasn't seen (yet)
                ar = RM.area_rect(area, rect)
                try:
                    img = RM.grab(ar)
                    if RM.parchment_share(img) < RM.PARCHMENT:     # no book there: nothing to read (cheap)
                        lines, last, settle = [], None, 0
                        misses += 1
                        if misses == RM.AUTO_GONE:
                            self.ui_q.put(("remnant_auto", rect, []))
                        continue
                    th = RM.thumb(img)
                    if last is None:                 # 2.79.0 (feedback: "not popping up on time"): the book just
                        settle = RM.SETTLE_READS     # opened - its first look can land mid-animation and find no
                    if not RM.changed(last, th) and settle <= 0:    # lines; read a few more times while it settles,
                        continue                     # not only when the picture changes a lot
                    settle -= 1
                    last = th
                    lines = RM.shift(RM.ocr(img), ar[0] - rect[0], ar[1] - rect[1])
                    rows = self.remnant_price(lines, SETTINGS.get("league", ""))
                except RM.OcrUnavailable:
                    break
                except Exception:
                    continue
                misses = 0                       # 2.43.0: the book is still open - a read with fewer rows (the
                if rows and unsure:              # 2.98.6: mark not seen - a real book lists several rewards; once
                    if len(rows) < RM.UNSURE_ROWS:   # one is read, this map has an Expedition
                        continue
                    self.rm_map_exp = True
                if rows:                         # game's tooltip over a reward) never takes tags away; only the
                    self.ui_q.put(("remnant_auto", rect, rows))      # book closing does
                    settle = min(settle, 1)      # (found them: one more read to catch the rest of the list)
        finally:
            if gen == getattr(self, "rm_auto_gen", 0):
                self.rm_auto_alive = False

    def ev_remnant_auto(self, rect, rows):
        rows = self.remnant_keep(rows)
        self.rm_rect = rect
        sig = tuple((r["name"], r["qty"]) for r in rows)
        if rows:
            if sig != getattr(self, "rm_auto_sig", None) or getattr(self, "rm_win", None) is None:
                self.remnant_show(rect, rows, secs=None)
                self.rm_auto_shown = True
                self.rm_auto_sig = sig
                self.remnant_note(rows)
        elif getattr(self, "rm_auto_shown", False) or getattr(self, "rm_win", None) is not None:
            self.remnant_hide()                  # 2.56.2: the book closed - every tag goes
            self.rm_auto_sig = None
        try:
            self.alerts_refresh()
        except Exception:
            buglog.caught()

    def remnant_keep(self, rows):
        """2.43.0: while the book stays open, the tags stay. Hovering a reward puts the game's tooltip over part of the
        book, so a read finds fewer rewards - their tags used to vanish under the mouse. Now a read only adds rewards
        (or updates the ones it sees); the book closing (rows = []) clears them."""
        if not rows:
            self.rm_kept = {}
            return rows
        kept = getattr(self, "rm_kept", None) or {}
        if not getattr(self, "rm_auto_shown", False):
            kept = {}
        for r in rows:
            kept[(r["name"], r["qty"])] = r
        self.rm_kept = kept
        out = sorted(kept.values(), key=lambda r: r["box"][1])
        if any(r.get("best") for r in out):                          # one best: the dearest
            top = max((r for r in out if r["total"] is not None), key=lambda r: r["total"], default=None)
            out = [dict(r, best=r is top) for r in out]
        return out

    def remnant_note(self, rows):
        best = next((r for r in rows if r.get("best")), None)
        self.rm_last = f"{time.strftime('%H:%M')}: {len(rows)} priced" + (f", best {best['name']}" if best else "")

    @staticmethod
    def remnant_names_values(league):
        """(Names, value_of) from the poe.ninja prices Wealth uses (fetched if over an hour old)."""
        from .wealth import NINJA_EXCHANGE_TYPES, NINJA_ITEM_TYPES, WPRICES
        try:
            WPRICES.ensure(league)
        except Exception:
            buglog.caught()
        names = []
        for typ in NINJA_EXCHANGE_TYPES:
            names += [ln[1] for ln in (WPRICES.parts.get(typ) or {}).get("lines", [])]
        for typ in NINJA_ITEM_TYPES:
            names += [ln[0] for ln in (WPRICES.parts.get(typ) or {}).get("lines", [])]

        def value_of(name):
            v = WPRICES.named(name)
            if v is not None:
                return v
            cands = getattr(WPRICES, "uniques", {}).get(name.lower()) or []
            return max(cands, key=lambda c: c[2])[1] if cands else None
        return RM.Names(names), value_of

    def remnant_price(self, lines, league):
        from .wealth import WPRICES
        key = (league, getattr(WPRICES, "ts", 0))
        cache = getattr(self, "rm_names", None)
        if not cache or cache[0] != key or time.time() - cache[3] > 600:     # (Auto reads often: build names once)
            names, value_of = self.remnant_names_values(league)
            cache = self.rm_names = ((league, getattr(WPRICES, "ts", 0)), names, value_of, time.time())
        return RM.price_lines(lines, cache[1], cache[2])

    # ---------------- the tags over the game
    # 2.38.0: one small, solid, click-through window per tag. (2.37.0 drew them on ONE window as big as the game, made
    # see-through with a colour key; on some PCs the colour key isn't honoured and that window showed black over the
    # whole game - and Auto, seeing its own black window, hid and showed it again and again.) Each tag is also hidden
    # from screen capture (Windows 10 2004+), so the watcher never reads its own tags.
    def remnant_show(self, rect, rows, secs=RM.SHOW_SECS):
        """2.56.2 (feedback: "very bold and large ... more compact, less intrusive"): smaller, plain-weight tags in
        the overlay style's own colors (Overlays › Appearance › Style), on its texture when it has one (the runeshape
        parchment), a thin edge; the best one in the style's warm color with a ★."""
        self.remnant_hide()
        from tkinter import font as tkfont
        from .overlaywin import pal, skinned, texture
        P = pal()
        l_, t, r, b = rect
        ui = max(0.7, (b - t) / 1440.0)
        size = -max(11, int(14 * ui))                      # (2.56.2: was 16 * ui, bold)
        wins = []
        BG, TXT, MUT = P["bg"], P["text"], P["muted"]
        BEST = P["warn"] if skinned() else "#ffd25a"
        EDGE, EDGE_BEST = (P["line"], BEST) if skinned() else ("#3d5582", "#ffd25a")
        if P.get("texture"):                           # on parchment: dark ink, the warm edge says "best"
            BEST = P["head"]

        def tag(x, y_mid, text, fg, edge, bold=False):
            w = tk.Toplevel(self.root)
            w.withdraw()
            w.overrideredirect(True)
            try:
                w.attributes("-topmost", True)
            except tk.TclError:
                pass
            fnt = ("Segoe UI", size, "bold" if bold else "normal")
            f = tkfont.Font(root=w, family="Segoe UI", size=size, weight="bold" if bold else "normal")
            tw, th = f.measure(text) + 12, f.metrics("linespace") + 4
            img = texture(w, tw, th, seed=5, calm=True) if P.get("texture") else None
            lab = tk.Label(w, text=text, fg=fg, bg=BG, font=fnt, highlightthickness=1, highlightbackground=edge,
                           **({"image": img, "compound": "center", "width": tw, "height": th, "padx": 0, "pady": 0}
                              if img is not None else {"padx": 6, "pady": 1}))
            lab.image = img
            lab.pack()
            w.update_idletasks()
            hh = w.winfo_reqheight()
            w.geometry(f"+{int(x)}+{int(y_mid - hh / 2)}")
            w.rm_x = int(x)                                    # 2.43.0: for the tips' place (winfo_x is 0 until shown)
            w.deiconify()
            try:
                from .alerts_page import click_through, force_topmost
                click_through(w)
                force_topmost(w)
            except Exception:
                buglog.caught()
            no_capture(w)
            wins.append(w)

        for row in rows:
            x0, y0, x1, y1 = row["box"]
            if row["total"] is None:                           # (2.40.0: also a reward poe.ninja doesn't list)
                txt, fg = "no price", MUT
            else:
                txt = fmt_short(row["total"])                   # 2.39.0: 16ex, 20c, 29d
                if row["qty"] > 1:
                    txt = f"{txt} ({row['qty']}×{fmt_short(row['each'])})"
                fg = BEST if row.get("best") else TXT
            if row.get("best"):
                txt = "★ " + txt
            mid = t + (y0 + y1) / 2
            if row.get("label"):                               # (the Test: an example line to tag)
                tag(l_ + x0, mid, row["label"], MUT, EDGE)
            tag(l_ + x1 + 10, mid, txt, fg, EDGE_BEST if row.get("best") else EDGE, bold=bool(row.get("best")))
        if wins and self.remnant_cfg().get("tips", True):
            self._remnant_tips(wins, rect, size, no_capture)
        self.rm_win = wins or None
        self.rm_auto_shown = False
        if secs and wins:                                      # (Auto's tags stay until the list closes)
            self.root.after(int(secs * 1000), lambda: getattr(self, "rm_win", None) is wins and self.remnant_hide())

    def _remnant_tips(self, wins, rect, size, no_capture):
        """2.40.0: "Runeshapes - community picks" next to the tags (right of the furthest one, at the book's top),
        click-through and left out of captures like them. It comes and goes with the tags (same list).
        2.43.0: shown as soon as the book's prices are, and stays while the book is open (it was placed from where
        the tags were on screen - nowhere yet the first time, so it only came with a later redraw)."""
        l_, t, r, b = rect
        try:
            right = max(getattr(w, "rm_x", w.winfo_x()) + w.winfo_reqwidth() for w in wins)
        except tk.TclError:
            return
        x = right + 24
        y = t + int(RM.AREA[1] * (b - t))
        w = tk.Toplevel(self.root)
        w.withdraw()
        w.overrideredirect(True)
        try:
            w.attributes("-topmost", True)
        except tk.TclError:
            pass
        small = -max(9, int(abs(size) * 0.9))                   # 2.56.2: a touch smaller than the tags
        from .overlaywin import pal, parchment, skinned       # 2.43.0: parchment, like the book beside it
        P = pal()
        BG, TXT, MUT = (P["bg"], P["text"], P["muted"]) if skinned() else ("#101826", "#e8eefc", "#9aa6bd")
        EDGE_ = P["leather"] if skinned() else "#5b77ad"                      # 2.47.0: every look
        box = tk.Frame(w, bg=BG, highlightthickness=max(1, P["border"]) if skinned() else 1, highlightbackground=EDGE_,
                       padx=8, pady=4)
        box.pack()
        tk.Label(box, text="Runeshapes for loot", bg=BG, fg=P["head"] if skinned() else TXT,
                 font=("Segoe UI", small, "bold"), anchor="w").pack(fill="x")
        for tier in ("S", "A", "B", "C", "D"):                 # 2.40.0: every runeshape, best first
            names = [(n, why) for tr, n, why in RM.RUNE_TIERS if tr == tier]
            bg, fg = RM.TIER_LOOK[tier]
            if tier in ("S", "A"):                            # the picks: one line each, with what they do
                for name, why in names:
                    row = tk.Frame(box, bg=BG)
                    row.pack(fill="x")
                    tk.Label(row, text=tier, bg=bg, fg=fg, font=("Segoe UI", small, "bold"), width=2).pack(side="left", pady=1)
                    tk.Label(row, text=name, bg=BG, fg=TXT, font=("Segoe UI", small), width=8,
                             anchor="w").pack(side="left", padx=(8, 0))
                    tk.Label(row, text=why, bg=BG, fg=MUT, font=("Segoe UI", small),
                             anchor="w").pack(side="left")
            else:                                             # the rest: one wrapped line of names per tier
                row = tk.Frame(box, bg=BG)
                row.pack(fill="x", pady=(2, 0))
                tk.Label(row, text=tier, bg=bg, fg=fg, font=("Segoe UI", small, "bold"), width=2).pack(side="left",
                                                                                                    anchor="n")
                tk.Label(row, text="  ·  ".join(n for n, _w in names), bg=BG, fg=MUT if tier == "C" else TXT if parchment() else fg,
                         font=("Segoe UI", small), anchor="w", justify="left",
                         wraplength=int(abs(size) * 24)).pack(side="left", padx=(8, 0))
        tk.Label(box, text=f"S-A: players' picks · B-D: grouped by effect ({RM.RUNE_TIPS_UPDATED})", bg=BG,
                 fg=MUT,
                 font=("Segoe UI", small), anchor="w").pack(fill="x", pady=(2, 0))
        never = tk.Label(box, text="Never show again", bg=BG, fg=MUT, cursor="hand2",      # 2.98.6 (feedback)
                         font=("Segoe UI", small, "underline"), anchor="e")
        never.pack(fill="x", pady=(4, 0))
        never.bind("<Button-1>", lambda _e: self.remnant_tips_never())
        w.rm_never = never
        w.update_idletasks()
        if P.get("texture") and skinned():                    # 2.56.2: the parchment shows round the lines
            from .overlaywin import texture
            img = texture(w, w.winfo_reqwidth(), w.winfo_reqheight(), seed=9, calm=True)
            if img is not None:
                bgl = tk.Label(box, image=img, bd=0)
                bgl.image = img
                bgl.place(x=-8, y=-4, relwidth=1, relheight=1, width=16, height=8)
                bgl.lower()
        try:
            from .style import monitor_rect
            ml, mt, mr, mb = monitor_rect(self.root, x, y)
            x = min(x, mr - w.winfo_reqwidth())
        except Exception:
            buglog.caught()
        w.geometry(f"+{int(x)}+{int(y)}")
        w.deiconify()
        try:
            from .alerts_page import force_topmost
            from .toasts import no_activate
            no_activate(w)                                    # 2.98.6: clickable (Never show again), but it never
            force_topmost(w)                                  # takes the keyboard from the game
        except Exception:
            buglog.caught()
        no_capture(w)
        w.rm_tips = True
        wins.append(w)

    def remnant_hide(self):
        self.rm_auto_shown = False
        wins, self.rm_win = getattr(self, "rm_win", None), None
        for w in wins or ():
            try:
                w.destroy()
            except tk.TclError:
                pass

    def remnant_test(self):
        """Test: example tags in the middle of the screen (no picture, no OCR)."""
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x, y = sw // 2 - 260, sh // 2 - 90
        rows = [{"name": "Orb of Alchemy", "qty": 3, "each": 0.004, "total": 0.012, "box": (x, y, x + 200, y + 24)},
                {"name": "Greater Rune of Leadership", "qty": 1, "each": 0.6, "total": 0.6,
                 "box": (x, y + 60, x + 300, y + 84)},
                {"name": "Divine Orb", "qty": 1, "each": 1.0, "total": 1.0, "box": (x, y + 120, x + 140, y + 144)}]
        for r in rows:
            r["best"] = r["name"] == "Divine Orb"
            r["label"] = r["name"] + (f" x{r['qty']}" if r["qty"] > 1 else "")
        self.remnant_show((0, 0, sw, sh), rows, secs=6)
        self.rm_last = "test: example tags for 6 seconds"
        return ("Example price tags show in the middle of your screen for 6 seconds. (Idea: PoE Ancients Price Helper "
                "by Pedro Quitério - see Settings > About.)")
