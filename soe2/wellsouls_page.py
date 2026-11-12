"""2.81.0: the Desecration Helper in the app - its switch (Overlay › Mechanic Helper, Overlay › Options; 2.81.1: not
on the bar - it turns itself on at the Well), the notice over the game when you arrive, the watcher (only while you're at The Well of
Souls - Client.txt says when; feedback: "eliminate the need for an always-on watcher") and the tier tags.
The reading and rating are in wellsouls.py. GGG ToS: it looks at your screen and draws on top - nothing is sent."""
import threading
import time
import tkinter as tk

from . import buglog
from . import remnant as RM
from . import wellsouls as W
from .config import save_json, SETTINGS

POLL = 0.3                  # seconds between looks while you're at the Well
SETTLE = 4                  # reads right after the window appears (it fades in)
GONE = 2                    # looks without the window = it closed: tags off
NOTICE_SECS = 4


class WellSoulsPage:
    def ws_cfg(self):
        c = SETTINGS.setdefault("desecrate", {})
        c.setdefault("on", True)
        c.setdefault("notice", True)              # the small "Desecration Helper on" over the game
        c.setdefault("asked", False)              # 2.90.0: the first visit to the Well asks whether you want it
        return c

    def ws_status(self):
        from . import features as FEAT
        if not self.ws_cfg().get("on") or not FEAT.on("overlay"):    # 2.131.0
            return "off"
        if getattr(self, "ws_problem", None) is None:
            self.ws_problem = RM.ocr_available()
        return "warn" if self.ws_problem else "on"

    def ws_text(self, row):
        if not self.ws_cfg().get("on"):
            return row["what"]
        if self.ws_status() == "warn":
            return f"Can't read the screen: {self.ws_problem}."
        if getattr(self, "ws_here", False):
            return "On - you're at The Well of Souls: each option shows its tier"
        return "On - Well of Souls Desecration Tiers."

    def ws_toggle(self, want):
        c = self.ws_cfg()
        c["on"] = bool(want)
        save_json("settings.json", SETTINGS)
        self.ws_problem = None
        if want:
            if not getattr(self, "_br_ticking", False):
                self.breach_start()                   # the game's log is followed while a helper needs it
            if getattr(self, "ws_here", False):
                self.ws_start()
        else:
            self.ws_stop()
        return f"Can't read the screen: {self.ws_problem}." if want and self.ws_status() == "warn" else None

    # ---------------------------------------------------------------- the area (Client.txt)
    def ws_scene(self, name):
        """2.125.7 (feedback: a player at the Well - the Session tracker said so - got nothing): the game's scene name
        says it too, so a Well whose area id isn't the one known (W.AREAS) still wakes the helper."""
        if W.is_well_name(name) and not getattr(self, "ws_here", False):
            self.ws_area(W.AREAS[0], why=f"scene {name}")

    def ws_area(self, area_id, why=None):
        """Every area change: at the Well -> on (with a notice); anywhere else -> off."""
        here = str(area_id or "") in W.AREAS
        before = getattr(self, "ws_here", False)
        self.ws_here = here
        if here and not before and not self.ws_cfg().get("asked"):
            self.ws_ask()                                 # 2.90.0: nobody knew it was there - ask at the Well
            return
        if not here and before:
            self.ws_ask_close()
        if here and not before and self.ws_cfg().get("on"):
            self.ws_problem = None                        # (checked again at each visit)
            st = self.ws_status()
            msg = f"at The Well of Souls ({why or 'area ' + str(area_id)}) - " + \
                ("watching" if st == "on" else f"can't read the screen: {self.ws_problem}")
            if st == "on":
                buglog.debug("Desecration Helper", msg)
            else:                                         # (in the log for a bug report: why it showed nothing)
                buglog.record("error", "Desecration Helper", msg)
            if self.ws_cfg().get("notice", True) or st != "on":
                self.ws_notice(None if st == "on" else f"Desecration Helper can't read the screen: {self.ws_problem}")
            self.ws_start()
        elif not here and before:
            self.ws_stop()

    # ---------------------------------------------------------------- 2.90.0: asked at the Well, once
    def ws_ask(self):
        """A card over the game the first time you reach The Well of Souls: want the Desecration Helper (Beta)?"""
        from tkinter import ttk
        self.ws_ask_close()
        try:
            w, body, P = self._camp_card("Desecration Helper", "◆", 460, top=0.14,
                                         on_close=lambda: self.ws_answer(None))
        except Exception:
            self.log_error("the Desecration Helper question")
            return None
        bg = P["bg"]
        tk.Label(body, text="You're at The Well of Souls. Want each revealed option to show its tier (T1 = the best "
                            "for that item type)?", bg=bg, fg=P["text"], font=(P["font"], self.ov_font(10)),
                 justify="left", anchor="w", wraplength=self.ov_px(420)).pack(fill="x")
        tk.Label(body, text="Beta: it reads your screen while you're here, and it's still being tuned. Change it any "
                            "time: Overlay ↳ Overlay Settings › Helpers.", bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(9)),
                 justify="left", anchor="w", wraplength=self.ov_px(420)).pack(fill="x", pady=(4, 0))
        row = tk.Frame(body, bg=bg)
        row.pack(fill="x", pady=(8, 0))
        self.ws_ask_btns = {}
        for k, label, style in (("yes", "Turn it on", "Primary.TButton"), ("no", "No thanks", "TButton")):
            b = ttk.Button(row, text=label, style=self.ov_btn(style), command=lambda k=k: self.ws_answer(k == "yes"))
            b.pack(side="left", padx=(0, 8))
            self.ws_ask_btns[k] = b
        self.ws_ask_win = w
        w.show()
        return w

    def ws_answer(self, on):
        """Yes / No: kept (asked). Closed with ×: asked again next visit."""
        self.ws_ask_close()
        if on is None:
            return
        c = self.ws_cfg()
        c["asked"] = True
        save_json("settings.json", SETTINGS)
        self.alerts_toggle("desecrate", bool(on))
        if on and getattr(self, "ws_here", False):
            self.ws_start()

    def ws_ask_close(self):
        w, self.ws_ask_win = getattr(self, "ws_ask_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def ws_notice(self, problem=None):
        """A small notice over the game: the helper is on while you're here (2.125.7: or why it can't read)."""
        try:
            from .overlaywin import pal
            from .alerts_page import game_rect, click_through, force_topmost
            from .remnant_page import no_capture
            P = pal()
            g = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
            ui = max(0.7, g[3] / 1440.0)
            w = tk.Toplevel(self.root)
            w.withdraw()
            w.overrideredirect(True)
            w.attributes("-topmost", True)
            tk.Label(w, text=("◆  " + problem) if problem else
                     "◆  Desecration Helper on  -  each option at the Well shows its tier", fg=P["text"],
                     bg=P["bg"], font=("Segoe UI", -max(11, int(14 * ui))), padx=8, pady=4,
                     highlightthickness=1, highlightbackground=P["line"]).pack()
            w.update_idletasks()
            w.geometry(f"+{int(g[0] + (g[2] - w.winfo_reqwidth()) / 2)}+{int(g[1] + g[3] * 0.12)}")
            w.deiconify()
            click_through(w)
            force_topmost(w)
            no_capture(w)
            self.ws_note_win = w
            self.root.after((NOTICE_SECS * 3 if problem else NOTICE_SECS) * 1000, lambda: w.winfo_exists() and w.destroy())
        except Exception:
            self.log_error("the Desecration Helper notice")

    # ---------------------------------------------------------------- the watcher (only at the Well)
    def ws_start(self):
        if self.ws_status() != "on" or getattr(self, "ws_alive", False):
            return
        self.ws_gen = getattr(self, "ws_gen", 0) + 1
        self.ws_alive = True
        threading.Thread(target=self._ws_watch, args=(self.ws_gen,), daemon=True).start()

    def ws_stop(self):
        self.ws_gen = getattr(self, "ws_gen", 0) + 1
        self.ws_alive = False
        self.ws_hide()

    def ws_read(self, rect, cx, img_box=None, img_slot=None):
        """The window at center x cx -> [(row text, rating, (x0, y0, x1, y1) on screen)] (blocking: OCR)."""
        bl, bt, br, bb = W.part(rect, cx, W.BOX)
        if img_box is None:
            img_box = RM.grab((bl, bt, br, bb))
        texts = W.rows_from_lines(RM.ocr(img_box), bb - bt)
        if not any(texts):
            return []
        tpls = [W.resolve(t)[0] if t else None for t in texts]
        cls = W.classes_for([t for t in tpls if t])
        bases = [b for bs in cls.values() for b in bs]
        if len(cls) > 1:                                   # the options fit several item types: the picture decides
            if img_slot is None:
                img_slot = RM.grab(W.part(rect, cx, W.SLOT))
            bases = W.match_art(img_slot, bases)
        if W.heart_fits(texts) and (not bases or any(W.rate(t, bases) is None or W.rate(t, bases).get("tier") is None
                                                     for t in texts if t)):
            bases = [W.heart_base()]                       # 2.130.3: a Heart of the Well's options
        rh = (bb - bt) / W.ROWS
        out = []
        for i, t in enumerate(texts):
            r = W.rate(t, bases) if t else None
            if r is not None:                                  # (the "Place an item ..." text before Reveal: no tags)
                out.append((t, r, (bl, int(bt + i * rh), br, int(bt + (i + 1) * rh))))
        return out

    def _ws_watch(self, gen):
        from .alerts_page import game_rect
        from .overlay import game_active
        last, misses, settle = None, 0, 0
        try:
            while gen == getattr(self, "ws_gen", 0):
                time.sleep(POLL)
                if not game_active():
                    continue
                g = game_rect()
                if not g:
                    continue
                rect = (g[0], g[1], g[0] + g[2], g[1] + g[3])
                try:
                    cx = next((x for x in W.centre_xs(rect)
                               if W.plate_share(RM.grab(W.part(rect, x, W.TITLE))) >= W.PARCH), None)
                    if cx is None:
                        last, settle = None, 0
                        misses += 1
                        if misses == GONE:
                            self.ui_q.put(("ws_tags", []))
                        continue
                    misses = 0
                    img = RM.grab(W.part(rect, cx, W.BOX))
                    th = RM.thumb(img)
                    if last is None:
                        settle = SETTLE
                    if not RM.changed(last, th) and settle <= 0:
                        continue
                    settle -= 1
                    last = th
                    rows = self.ws_read(rect, cx, img_box=img)
                except RM.OcrUnavailable:
                    break
                except Exception:
                    continue
                if rows:
                    self.ui_q.put(("ws_tags", rows))
        finally:
            if gen == getattr(self, "ws_gen", 0):
                self.ws_alive = False

    # ---------------------------------------------------------------- the tags
    def ev_ws_tags(self, rows):
        sig = tuple((t, W.label(r)) for t, r, _b in rows)
        if not rows:
            self.ws_hide()
            self.ws_sig = None
            return
        if sig == getattr(self, "ws_sig", None) and getattr(self, "ws_wins", None):
            return
        self.ws_sig = sig
        self.ws_show(rows)

    def ws_colour(self, r, P):
        if not r or r.get("tier") is None:
            return P["muted"]
        if r.get("abyss"):
            return "#9be37a"                                   # the Well's own green
        if r["tier"] <= 2:
            return P["warn"] if P.get("warn") else "#ffd25a"
        return P["text"] if r["tier"] <= max(3, r["of"] // 2) else P["muted"]

    def ws_show(self, rows):
        self.ws_hide()
        from tkinter import font as tkfont
        from .overlaywin import pal
        from .alerts_page import click_through, force_topmost
        from .remnant_page import no_capture
        P = pal()
        wins = []
        for text, r, (x0, y0, x1, y1) in rows:
            ui = max(0.7, (y1 - y0) / 108.0)                   # a row is ~108 px at 1440p
            size = -max(11, int(15 * ui))
            txt = W.label(r)
            if r and r.get("tier") == 1 and not r.get("abyss"):
                txt = "★ " + txt
            w = tk.Toplevel(self.root)
            w.withdraw()
            w.overrideredirect(True)
            try:
                w.attributes("-topmost", True)
            except tk.TclError:
                pass
            f = tkfont.Font(root=w, family="Segoe UI", size=size, weight="bold")
            col = self.ws_colour(r, P)
            tk.Label(w, text=txt, fg=col, bg=P["bg"], font=f, padx=8, pady=2, highlightthickness=1,
                     highlightbackground=col if r and r.get("tier") == 1 else P["line"]).pack()
            w.update_idletasks()
            w.geometry(f"+{int(x1 + 10)}+{int((y0 + y1) / 2 - w.winfo_reqheight() / 2)}")
            w.deiconify()
            try:
                click_through(w)
                force_topmost(w)
            except Exception:
                buglog.caught()
            no_capture(w)
            wins.append(w)
        self.ws_wins = wins or None

    def ws_hide(self):
        wins, self.ws_wins = getattr(self, "ws_wins", None), None
        for w in wins or ():
            try:
                w.destroy()
            except tk.TclError:
                pass

    def ws_test(self):
        """Test: example tags in the middle of the screen (no picture, no reading)."""
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x0, x1, y = sw // 2 - 300, sw // 2 + 300, sh // 2 - 120
        gloves = [b for b in W.data()["bases"] if b["c"] == "Gloves"]
        rows = []
        for i, t in enumerate(("+17% to Cold and Chaos Resistances", "13% increased Rarity of Items found",
                               "+29% to Fire Resistance")):
            rows.append((t, W.rate(t, gloves), (x0, y + i * 80, x1, y + i * 80 + 70)))
        self.ws_show(rows)
        self.root.after(6000, self.ws_hide)
        return "Example tier tags show in the middle of your screen for 6 seconds."
