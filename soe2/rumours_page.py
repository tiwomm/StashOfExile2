"""2.83.0: Island Rumours in the app (part of the Expedition helper, Remnant's row in Overlay ↳ Settings) and the
Remnant watcher's places: it watches only where remnants can be (feedback: "it keeps popping up in random areas").
  * Island Rumours: only in your hideout (Client.txt; feedback: "watch only in hideout"). A look at a small copy of
    the screen for the Uncharted Waters card's parchment; only then its part is read. Each rumour gets a tag: the
    island and your Map library rank.
  * Remnant: always on in a Grand Expedition island (Client.txt: ExpeditionLogBook_...), off in hideouts, towns and
    the campaign; in other maps as before.
GGG ToS: it looks at your screen and draws on top - nothing is sent to the game."""
import threading
import time
import tkinter as tk

from . import remnant as RM
from . import rumours as RU
from .config import save_json, SETTINGS

POLL = 0.6
GONE = 2
GRAND = "ExpeditionLogBook_"


class RumoursPage:
    # ---------------------------------------------------------------- where you are (Client.txt)
    def expedition_area(self, area_id, kind):
        """Every area change: the Remnant watcher's zone and the rumours watcher (hideout only)."""
        a = str(area_id or "")
        self.rm_zone = "grand" if a.startswith(GRAND) else kind
        if not self.rm_zone_ok():
            self.remnant_hide()                       # no remnants here: no leftover tags
        here = kind == "hideout"
        before = getattr(self, "ru_here", False)
        self.ru_here = here
        if here and not before:
            self.ru_start()
        elif not here and before:
            self.ru_stop()

    def rm_zone_ok(self):
        """The Remnant watcher looks only where remnants can be: not in a hideout, town or the campaign."""
        return getattr(self, "rm_zone", None) not in ("hideout", "town", "other")

    # ---------------------------------------------------------------- Island Rumours
    def ru_on(self):
        c = self.remnant_cfg()
        return bool(c.get("on") and c.get("rumours", True))

    def ru_changed(self, on):
        self.remnant_cfg()["rumours"] = bool(on)
        save_json("settings.json", SETTINGS)
        if on and getattr(self, "ru_here", False):
            self.ru_start()
        elif not on:
            self.ru_stop()

    def ru_start(self):
        if not self.ru_on() or getattr(self, "ru_alive", False) or RM.ocr_available():
            return
        self.ru_gen = getattr(self, "ru_gen", 0) + 1
        self.ru_alive = True
        threading.Thread(target=self._ru_watch, args=(self.ru_gen,), daemon=True).start()

    def ru_stop(self):
        self.ru_gen = getattr(self, "ru_gen", 0) + 1
        self.ru_alive = False
        self.ru_hide()

    def ru_read(self, rect, img=None):
        """The game window -> [(rumour, island, box on screen)] (blocking: OCR), [] when no card."""
        if img is None:
            img = RM.grab(rect)
        card = RU.find_card(img, rect[3] - rect[1])
        if card is None:
            return [], None
        x0, y0, x1, y1 = card
        pad = int((y1 - y0) * 0.1)
        cut = (max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad))
        lines = RM.ocr(img.crop(cut))
        ox, oy = rect[0] + cut[0], rect[1] + cut[1]
        out = [(r, i, (b[0] + ox, b[1] + oy, b[2] + ox, b[3] + oy)) for r, i, b in RU.rows(lines)]
        return out, (rect[0] + x1, rect[1] + y0, rect[0] + x1, rect[1] + y1)

    def _ru_watch(self, gen):
        from .alerts_page import game_rect
        from .overlay import game_active
        last, misses = None, 0
        try:
            while gen == getattr(self, "ru_gen", 0):
                time.sleep(POLL)
                if not game_active():
                    continue
                g = game_rect()
                if not g:
                    continue
                rect = (g[0], g[1], g[0] + g[2], g[1] + g[3])
                try:
                    img = RM.grab(rect)
                    card = RU.find_card(img, g[3])
                    if card is None:
                        misses += 1
                        last = None
                        if misses == GONE:
                            self.ui_q.put(("ru_tags", [], None))
                        continue
                    misses = 0
                    th = RM.thumb(img.crop(card))
                    if not RM.changed(last, th):
                        continue
                    last = th
                    rows, edge = self.ru_read(rect, img)
                except RM.OcrUnavailable:
                    break
                except Exception:
                    continue
                if rows:
                    self.ui_q.put(("ru_tags", rows, edge))
        finally:
            if gen == getattr(self, "ru_gen", 0):
                self.ru_alive = False

    def ev_ru_tags(self, rows, edge):
        if not rows:
            self.ru_hide()
            self.ru_sig = None
            return
        sig = tuple(r[1] for r in rows)
        if sig == getattr(self, "ru_sig", None) and getattr(self, "ru_wins", None):
            return
        self.ru_sig = sig
        self.ru_show(rows, edge)

    def ru_show(self, rows, edge):
        self.ru_hide()
        from tkinter import font as tkfont
        from . import maplib
        from .overlaywin import pal
        from .alerts_page import click_through, force_topmost
        from .remnant_page import no_capture
        P = pal()
        mine = maplib.ranks()
        good = {"S": P.get("warn") or "#ffd25a", "A": P.get("warn") or "#ffd25a", "Avoid": P.get("bad") or "#e06c5a"}
        wins = []
        for _r, island, (x0, y0, x1, y1) in rows:
            rank = mine.get(island)
            w = tk.Toplevel(self.root)
            w.withdraw()
            w.overrideredirect(True)
            try:
                w.attributes("-topmost", True)
            except tk.TclError:
                pass
            size = -max(11, int((y1 - y0) * 0.75))
            f = tkfont.Font(root=w, family="Segoe UI", size=size, weight="bold")
            col = good.get(rank, P["text"] if rank else P["muted"])
            tk.Label(w, text=RU.tag_text(island, rank), fg=col, bg=P["bg"], font=f, padx=8, pady=1,
                     highlightthickness=1, highlightbackground=col if rank in ("S", "A") else P["line"]).pack()
            w.update_idletasks()
            x = (edge[0] if edge else x1) + 12
            w.geometry(f"+{int(x)}+{int((y0 + y1) / 2 - w.winfo_reqheight() / 2)}")
            w.deiconify()
            try:
                click_through(w)
                force_topmost(w)
            except Exception:
                pass
            no_capture(w)
            wins.append(w)
        self.ru_wins = wins or None

    def ru_hide(self):
        wins, self.ru_wins = getattr(self, "ru_wins", None), None
        for w in wins or ():
            try:
                w.destroy()
            except tk.TclError:
                pass
