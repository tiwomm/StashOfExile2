"""Expedition Remnant Price Checker in the app (2.37.0): the "Remnant" helper next to Delirium, Breach and Ritual -
its row in Session tracker > Alerts, its cell in the timer's Helpers bar, its key, and the price tags over the game.
The reading and matching are in remnant.py. Idea: PoE Ancients Price Helper by Pedro Quitério (no code from it)."""
import sys
import threading
import time
import tkinter as tk

from . import remnant as RM
from .config import save_json, SETTINGS
from .pricefmt import fmt_short

TAG_BG, TAG_BEST = "#101826", "#2a2108"


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
        pass


class RemnantPage:
    def remnant_cfg(self):
        c = SETTINGS.setdefault("remnant", {})
        c.setdefault("on", False)
        c.setdefault("key", RM.DEFAULT_KEY)
        c.pop("sound", None)                        # 2.39.0: no sound (the tags are enough)
        c.setdefault("auto", True)                  # Auto: watch where the book opens; tags come and go by themselves
        c.setdefault("area", None)                  # None = RM.AREA; set only when a key press found it elsewhere
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
        from .overlay import key_label
        if not c.get("on"):
            return row["what"]
        if self.remnant_status() == "warn":
            return f"Can't read the screen: {self.rm_problem}."
        last = getattr(self, "rm_last", "")
        key = key_label(c.get("key") or RM.DEFAULT_KEY)
        if c.get("auto"):
            head = f"On - Auto: prices show by themselves when a remnant's reward book opens ({key} works too)"
        else:
            head = f"On - open a remnant's reward list and press {key}"
        return head + (f"  ·  {last}" if last else "")

    def remnant_toggle(self, want):
        c = self.remnant_cfg()
        c["on"] = bool(want)
        save_json("settings.json", SETTINGS)
        self.rm_problem = None
        if not want:
            self.remnant_hide()
        st = self.remnant_status()
        self.remnant_auto_sync()
        return f"Can't read the screen: {self.rm_problem}." if want and st == "warn" else None

    def remnant_auto_changed(self, on):
        self.remnant_cfg()["auto"] = bool(on)
        save_json("settings.json", SETTINGS)
        self.remnant_auto_sync()
        try:
            self.alerts_refresh()
        except Exception:
            pass

    # ---------------- Auto: a light watcher on the learned area
    def remnant_auto_sync(self):
        """Start / stop the watcher to match the settings (on + Auto + an area learned + OCR works)."""
        c = self.remnant_cfg()
        want = bool(c.get("on") and c.get("auto") and self.remnant_status() == "on")
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
        last, misses = None, 0
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
                ar = RM.area_rect(area, rect)
                try:
                    img = RM.grab(ar)
                    if RM.parchment_share(img) < RM.PARCHMENT:     # no book there: nothing to read (cheap)
                        lines, last = [], None
                        misses += 1
                        if misses == RM.AUTO_GONE:
                            self.ui_q.put(("remnant_auto", rect, []))
                        continue
                    th = RM.thumb(img)
                    if not RM.changed(last, th):
                        continue
                    last = th
                    lines = RM.shift(RM.ocr(img), ar[0] - rect[0], ar[1] - rect[1])
                    rows = self.remnant_price(lines, SETTINGS.get("league", ""))
                except RM.OcrUnavailable:
                    break
                except Exception:
                    continue
                misses = 0 if rows else misses + 1
                if rows or misses >= RM.AUTO_GONE:
                    self.ui_q.put(("remnant_auto", rect, rows))
        finally:
            if gen == getattr(self, "rm_auto_gen", 0):
                self.rm_auto_alive = False

    def ev_remnant_auto(self, rect, rows):
        sig = tuple((r["name"], r["qty"]) for r in rows)
        if rows:
            if sig != getattr(self, "rm_auto_sig", None) or getattr(self, "rm_win", None) is None:
                self.remnant_show(rect, rows, secs=None)
                self.rm_auto_shown = True
                self.rm_auto_sig = sig
                self.remnant_note(rows, auto=True)
        elif getattr(self, "rm_auto_shown", False):
            self.remnant_hide()
            self.rm_auto_sig = None
        try:
            self.alerts_refresh()
        except Exception:
            pass

    def remnant_note(self, rows, auto=False):
        best = next((r for r in rows if r.get("best")), None)
        self.rm_last = (f"{time.strftime('%H:%M')}: {len(rows)} priced" + (f", best {best['name']}" if best else "")
                        + (" (Auto)" if auto else ""))

    # ---------------- the key (keyboard watcher thread)
    def remnant_on_key(self, vk, ctrl, alt, shift):
        c = SETTINGS.get("remnant") or {}
        if not c.get("on"):
            return False
        from .overlay import game_active, parse_key
        k = parse_key(c.get("key") or RM.DEFAULT_KEY)
        if k and k == (vk, ctrl, alt, shift):
            self.ui_q.put(("remnant_check",))
            return bool(game_active())
        return False

    # ---------------- one check: picture -> OCR -> prices -> tags
    def ev_remnant_check(self):
        if getattr(self, "rm_win", None) is not None and not getattr(self, "rm_auto_shown", False):
            self.remnant_hide()                                # the key again: tags off
            return
        if getattr(self, "rm_busy", False):
            return
        self.rm_busy = True
        from .alerts_page import game_rect
        g = game_rect()
        rect = (g[0], g[1], g[0] + g[2], g[1] + g[3]) if g else (0, 0, self.root.winfo_screenwidth(),
                                                                  self.root.winfo_screenheight())
        league = SETTINGS.get("league", "")

        def work():
            err, rows = "", []
            try:
                img = RM.grab(rect)
                lines = RM.ocr(img)
                rows = self.remnant_price(lines, league)
            except RM.OcrUnavailable as e:
                err = str(e)
            except Exception as e:
                err = f"{e.__class__.__name__}: {e}"
                self.log_error("Expedition Remnant Price Checker")
            self.ui_q.put(("remnant_done", rect, rows, err))
        threading.Thread(target=work, daemon=True).start()

    @staticmethod
    def remnant_names_values(league):
        """(Names, value_of) from the poe.ninja prices Wealth uses (fetched if over an hour old)."""
        from .wealth import NINJA_EXCHANGE_TYPES, NINJA_ITEM_TYPES, WPRICES
        try:
            WPRICES.ensure(league)
        except Exception:
            pass
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

    def ev_remnant_done(self, rect, rows, err):
        self.rm_busy = False
        if err:
            self.rm_problem = err if "text reader" in err or "Windows" in err else self.rm_problem
            self.rm_last = "couldn't read the screen"
            self.app_toast(err, "Expedition Remnant Price Checker", kind="error")
        elif not rows:
            self.rm_last = "no rewards found on screen"
            self.app_toast("No remnant rewards found on the screen. Open a remnant's reward list first, then press the "
                           "key.", "Expedition Remnant Price Checker", kind="warning")
        else:
            self.remnant_show(rect, rows)
            self.remnant_note(rows)
            c = self.remnant_cfg()                     # found somewhere Auto doesn't look (UI scale)? look there
            if not RM.inside(rows, c.get("area") or RM.AREA, rect):
                c["area"] = RM.learn_area(rows, rect)
                save_json("settings.json", SETTINGS)
            self.rm_auto_sig = tuple((r["name"], r["qty"]) for r in rows)
            self.remnant_auto_sync()
        try:
            self.alerts_refresh()
            self.alerts_overlay_redraw()
        except Exception:
            pass

    # ---------------- the tags over the game
    # 2.38.0: one small, solid, click-through window per tag. (2.37.0 drew them on ONE window as big as the game, made
    # see-through with a colour key; on some PCs the colour key isn't honoured and that window showed black over the
    # whole game - and Auto, seeing its own black window, hid and showed it again and again.) Each tag is also hidden
    # from screen capture (Windows 10 2004+), so the watcher never reads its own tags.
    def remnant_show(self, rect, rows, secs=RM.SHOW_SECS):
        self.remnant_hide()
        l_, t, r, b = rect
        ui = max(0.7, (b - t) / 1440.0)
        size = -int(16 * ui)
        wins = []

        def tag(x, y_mid, text, fg, bg, edge, bold=True):
            w = tk.Toplevel(self.root)
            w.withdraw()
            w.overrideredirect(True)
            try:
                w.attributes("-topmost", True)
            except tk.TclError:
                pass
            lab = tk.Label(w, text=text, fg=fg, bg=bg, font=("Segoe UI", size, "bold" if bold else "normal"),
                           padx=8, pady=2, highlightthickness=1, highlightbackground=edge)
            lab.pack()
            w.update_idletasks()
            hh = w.winfo_reqheight()
            w.geometry(f"+{int(x)}+{int(y_mid - hh / 2)}")
            w.deiconify()
            try:
                from .alerts_page import click_through, force_topmost
                click_through(w)
                force_topmost(w)
            except Exception:
                pass
            no_capture(w)
            wins.append(w)

        for row in rows:
            x0, y0, x1, y1 = row["box"]
            if row["total"] is None:
                txt, fg = "no price", "#9aa6bd"
            else:
                txt = fmt_short(row["total"])                   # 2.39.0: 16ex, 20c, 29d
                if row["qty"] > 1:
                    txt = f"{txt}  ({row['qty']} × {fmt_short(row['each'])})"
                fg = "#ffd25a" if row.get("best") else "#e8eefc"
            if row.get("best"):
                txt = "★ " + txt
            mid = t + (y0 + y1) / 2
            if row.get("label"):                               # (the Test: an example line to tag)
                tag(l_ + x0, mid, row["label"], "#c8b98a", "#1a140c", "#5a4a2a", bold=False)
            tag(l_ + x1 + 14, mid, txt, fg, TAG_BEST if row.get("best") else TAG_BG,
                "#ffd25a" if row.get("best") else "#3d5582")
        self.rm_win = wins or None
        self.rm_auto_shown = False
        if secs and wins:                                      # (Auto's tags stay until the list closes)
            self.root.after(int(secs * 1000), lambda: getattr(self, "rm_win", None) is wins and self.remnant_hide())

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
