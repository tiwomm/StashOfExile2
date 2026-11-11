"""Two parts of the overlay that got their own place (2.76.0).

  * Map rank - your rank for the map you're in (S A B C D or Avoid; the community's in brackets when you have none)
    was glued onto "where you are". It's its own part now, with its own switch (Overlay › Options › On the overlay).
    Click it to rank the map. "Ask me to rank maps I haven't ranked" (on by default): leaving a map you haven't
    ranked, a small card asks - S A B C D Avoid, Not now, or Never for this map. Feedback: "isolate the Map
    Tier/rating piece on the overlay and add an option ... to prompt a user to give unrated maps a rating".
  * The lines - League Plan's NOW line, the Campaign Helper's (2.77.0) and Ritual's (2.118.0). 2.124.0: drawn at
    the top of the overlay's own window (they had their own small bar), which grows upward by their height - the bar
    never moves. Feedback: "instead of having it as an isolated separate bar, can we just have it combine".

GGG ToS: windows and the game's log only - nothing is sent to the game."""
import tkinter as tk
from tkinter import ttk
from . import buglog

RANK_BUTTONS = ("S", "A", "B", "C", "D", "Avoid")


class OverlayParts:
    """Mixed into App."""

    # ================================================================ map rank
    def rank_text(self, where):
        """'★ A', '★ (B)' (the community's), '★ -' (none yet) or '' (not in a map)."""
        if not where or where == "-":
            return ""
        r = self._ov_rank(where).strip()
        if r.startswith("["):
            return "★ " + r.strip("[]").title()
        if r.startswith("("):
            return "★ " + r
        return "★ -"

    def rank_ask_on(self):
        return bool(self.tracker_cfg().get("rank_ask", True))

    def maprank_log(self, kind, data):
        """The session tracker's log events: leaving a map you haven't ranked -> the card (if the option is on)."""
        if kind != "area":
            return None
        from .gamelog import area_kind
        ak = area_kind(data.get("area"), data.get("seed"), data.get("level", 0))
        if ak == "map":
            from .maplib import display_name                 # 2.78.1: its name, not its area id ("MapRugosa")
            self._mr_in = display_name(data.get("area"))
            return None
        left, self._mr_in = getattr(self, "_mr_in", None), None
        if left:
            self._mr_last = left
        if not left or ak not in ("town", "hideout") or not self.rank_ask_on():
            return None
        from .config import SETTINGS
        from .maplib import display_name, ranks
        never = SETTINGS.get("rank_never") or []
        if any(display_name(n) != n for n in never):         # 2.78.1: ids saved by 2.76.0 -> names
            SETTINGS["rank_never"] = never = list(dict.fromkeys(display_name(n) for n in never))
        if left in ranks() or left in never:
            return None
        return self.maprank_prompt(left)

    def maprank_click(self):
        """The rank on the overlay was clicked: rank the map you're in (or were in last)."""
        where = getattr(self, "_mr_in", None) or getattr(self, "_mr_last", None)
        if where:
            return self.maprank_prompt(where)
        self._say("Rank a map from the Map Library (Overlay ↳ Map Library), or click this while you're in one.", 6)
        return None

    def maprank_prompt(self, name):
        """A small card at the top of the game: how was this map? -> the window."""
        from .overlaywin import OverlayWindow, pal
        from .alerts_page import game_rect
        self.maprank_close()
        P = pal()
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        W = self.ov_px(420)                                  # 2.78.3: the game's size
        geo = (r[0] + (r[2] - W) // 2, r[1] + int(r[3] * 0.08), W, None)
        w = OverlayWindow(self.root, "Rank this map", "★", geo, palette=P, lockable=False, follow_game=True,
                          no_activate=True, on_close=self.maprank_close)
        bg = P["bg"]
        body = tk.Frame(w.body, bg=bg, padx=self.ov_px(16), pady=self.ov_px(8))
        body.pack(fill="both", expand=True)
        tk.Label(body, text=f"How was {name}?", bg=bg, fg=P["text"], font=(P["font"], self.ov_font(11), "bold"), anchor="w").pack(fill="x")
        tk.Label(body, text="Your rank shows on the overlay next time, and counts as your vote for the community's.",
                 bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(9)), anchor="w", justify="left", wraplength=W - self.ov_px(40)).pack(fill="x")
        row = tk.Frame(body, bg=bg)
        row.pack(fill="x", pady=(8, 0))
        self.maprank_btns = {}
        for rk in RANK_BUTTONS:
            b = ttk.Button(row, text=rk, width=6 if rk == "Avoid" else 3, style=self.ov_btn(),
                           command=lambda rk=rk: self.maprank_set(name, rk))
            b.pack(side="left", padx=(0, 4))
            self.maprank_btns[rk] = b
        row2 = tk.Frame(body, bg=bg)
        row2.pack(fill="x", pady=(8, 0))
        from .config import SETTINGS, save_json
        opts = [("later", "Not now"), ("never", "Never for this map")]
        if not SETTINGS.get("rank_card_seen"):              # 2.98.5: the first card you see: a way out of ranking
            SETTINGS["rank_card_seen"] = True
            save_json("settings.json", SETTINGS)
            opts.append(("optout", "Opt out"))
        for key, label in opts:
            b = ttk.Button(row2, text=label, style=self.ov_btn("Quiet.TButton"), command=lambda k=key: self.maprank_skip(name, k))
            b.pack(side="left", padx=(0, 8))
            self.maprank_btns[key] = b
        self.maprank_win, self.maprank_name = w, name
        w.show()
        return w

    def maprank_set(self, name, rank):
        from .maplib import set_rank
        set_rank([name], rank)
        from .tracker_page import TrackerPage
        TrackerPage._ov_cache = None                         # (the overlay shows it at once)
        self.maprank_close()
        self._say(f"{name}: ranked {rank}.", 4)
        try:
            self.tracker_overlay_draw(self.tracker_numbers())
        except Exception:
            buglog.caught()

    def maprank_skip(self, name, how):
        if how == "optout":                                  # 2.98.5: no more rank cards (Overlay › Overlay Settings brings them back)
            self.tracker_cfg()["rank_ask"] = False
            self.tracker_save()
            v = getattr(self, "ml_rank_ask", None)
            if v is not None:
                v.set(False)
            self.maprank_close()
            self._say("No more map rank cards. Turn them back on: Overlay ↳ Map Library › Ask me to rank.", 8)
            return
        if how == "never":
            from .config import SETTINGS, save_json
            SETTINGS.setdefault("rank_never", [])
            if name not in SETTINGS["rank_never"]:
                SETTINGS["rank_never"].append(name)
            save_json("settings.json", SETTINGS)
        self.maprank_close()

    def maprank_close(self):
        w, self.maprank_win = getattr(self, "maprank_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    # ================================================================ the goal bar
    def goalbar_rows(self):
        """What the goal bar holds, top to bottom: 'campaign' (2.77.0, while you're in the campaign), 'ritual' (2.118.0,
        in a map with Ritual), 'focus'."""
        rows = []
        try:
            if self.camp_on_bar():
                rows.append("campaign")
        except Exception:
            self.log_error("the campaign line")
        try:
            if self.ritual_readout():
                rows.append("ritual")
        except Exception:
            buglog.caught()
        if self.focus_line()[0]:
            rows.append("focus")
        return rows

    def goalbar_wanted(self):
        return bool(self.goalbar_rows())

    def goalbar_destroy(self, keep_place=True):
        """The lines come off the overlay's window; keep_place: the window shrinks back down to its bar (the bar
        itself never moves)."""
        cv, self.gb_cv = getattr(self, "gb_cv", None), None
        h, self._gb_h = getattr(self, "_gb_h", 0), 0
        if cv is None:
            return
        main = getattr(self, "mg_win", None)
        geo = self._gb_geo(main) if keep_place and main is not None else None
        try:
            cv.destroy()
        except tk.TclError:
            pass
        if geo and h:
            self._gb_place(main, geo, -h, getattr(self, "_gb_below", False))

    @staticmethod
    def _gb_geo(main):
        """(w, h, x, y) of the window before the lines go on or come off."""
        try:
            main.update_idletasks()
            g = (main.winfo_width(), main.winfo_height(), main.winfo_x(), main.winfo_y())
            return g if g[0] > 1 else (main.winfo_reqwidth(), main.winfo_reqheight(), g[2], g[3])
        except tk.TclError:
            return None

    @staticmethod
    def _gb_place(main, geo, dh, below=False):
        """The window dh px taller (the lines added on top) or shorter than it was - its bottom stays put.
        2.130.1: below - the lines sit under the bar (the Bar at the top of the screen): its top stays put."""
        if not geo:
            return
        ww, hh, x, y = geo
        try:
            main.geometry(f"{ww}x{max(1, hh + dh)}+{x}+{y if below else y - dh}")
        except tk.TclError:
            pass

    def goalbar_build(self):
        """2.124.0 (feedback: "instead of an isolated separate bar, can we just have it combine"): the Campaign,
        Ritual and NOW lines are drawn at the top of the overlay's own window, as wide as it, and the window grows
        upward by their height - the bar itself never moves. (Was its own small window, docked or dragged.)
        -> the lines' canvas or None."""
        import tkinter.font as tkfont
        self.goalbar_destroy()
        main = getattr(self, "mg_win", None)
        if main is None or not self.goalbar_wanted():
            self.goal_rows = []
            return None
        cfg = self.tracker_cfg()
        hud = self.merged_layout() == "xpbar"
        light = self.ov_light()
        P = getattr(self, "mg_P", None) or {}
        if "font" not in P:
            from .overlaywin import pal
            P = pal()
        try:
            mcv = next(c for c in main.body.winfo_children() if isinstance(c, tk.Canvas))
            main.update_idletasks()
            W = int(mcv.cget("width")) or mcv.winfo_reqwidth()
            mh = int(mcv.cget("height")) or mcv.winfo_reqheight()
        except (StopIteration, tk.TclError, ValueError, AttributeError):
            return None
        rows = self.goalbar_rows()
        k = getattr(self, "_hud_k", 1.0)
        if light:
            side = self._u(12)
        elif hud:
            from . import hudart
            side = hudart.cap_width(mh) + 14                  # (in line with the bar's well under it)
        else:
            side = int(16 * k)                                # (in line with the Panel's cells)
        f = (P["font"], self._hf(10))
        fm = tkfont.Font(root=self.root, family=P["font"], size=self._hf(10))
        lh = fm.metrics("linespace")
        row_h = lh + max(8, int(10 * k))                      # 2.124.0 (feedback: too tall): one line and a little air
        classic = not light
        if classic and hud:                                   # 2.124.1 (feedback: the added height didn't match the bar):
            row_h = max(row_h, int(mh * 0.85))               # a line about as tall as the bar under it
        pad = int(10 * k) if classic and not hud else 0       # (the Panel's frame round the lines)
        hs = [row_h] * len(rows)
        camp_n = 1
        if "campaign" in rows:                                # 2.123.7: a narrow bar wraps the line instead of cutting it
            camp_n = self.camp_lines(P, W - 2 * side)
            hs[rows.index("campaign")] += (camp_n - 1) * lh
        H = sum(hs) + 2 * pad
        bg = P.get("bg", "#15130f")
        if light and P.get("boxless"):
            from .ovlight import KEY
            bg = KEY
        geo = self._gb_geo(main)
        cv = tk.Canvas(main.body, bg=bg, highlightthickness=0, width=W, height=H)
        # 2.130.1 (feedback: "overlay at top caused the ritual portion of the bar style to be beyond the edge of the
        # monitor"): with the Bar placed at the top, the lines go under it, and the window grows down
        self._gb_below = bool(hud and self.ov_spot() == "top")
        if self._gb_below:
            cv.pack(side="top", fill="x", after=mcv)
        else:
            cv.pack(side="top", fill="x", before=mcv)
        if not cfg.get("mlocked"):
            main.draggable(cv)
        lft, rgt = side, W - side
        if classic and hud:                                   # 2.124.1 (feedback: didn't match the bar): the bar's own
            from . import hudart                              # stone plate and end caps
            ends, self._hud_ends = getattr(self, "_hud_ends", None), ("amber", "amber")
            lft, rgt = self._hud_frame(cv, P, W, H, cap=hudart.cap_width(mh))
            self._hud_ends = ends or ("crimson", "sapphire")
        elif classic:                                         # the Panel's stone and frame (2.124.1: as the Bar)
            from . import hudart
            art = hudart.panel(cv, W, H)
            if art is not None:
                cv.create_image(0, 0, image=art, anchor="nw", tags=("hudbg",))
                cv._card_imgs = [art]
        else:
            cv.create_line(lft, H - 1, rgt, H - 1, fill=P.get("accent") if P.get("boxless") else P.get("line", "#4a3f2c"),
                           tags=("mg",))
        mids, edges, top = [], [], pad
        for h in hs:                                          # each row's middle (2.123.7: rows can differ in height)
            mids.append(int(top + h / 2))
            top += h
            edges.append(top)
        self.goal_rows = rows                               # (2.118.0: was gb_rows - the Gear book has a method of that name)
        for e in edges[:-1]:                                  # a thin line between two lines (at the row's edge)
            cv.create_line(lft, e, rgt, e, fill=P["line"], tags=("mg",))
        if "campaign" in rows:
            self.camp_draw_row(cv, P, lft, rgt, mids[rows.index("campaign")], f, n=camp_n, lh=lh)
            if light:
                self._lt_halo_tags(cv, P, ("camp",))
        if "ritual" in rows:                                  # 2.118.0: the Ritual line
            mid = mids[rows.index("ritual")]
            fm = tkfont.Font(root=cv, family=P["font"], size=self._hf(10))
            tag = "▸ " + self.ritual_line_label()             # 2.132.2: RITUAL / TEMPLE / IN MAP
            cv.create_text(lft, mid, text=tag, anchor="w", fill=P["head"],
                           font=(P["hfont"], self._hf(9), "bold"), tags=("mg", "rit"))
            rt = self._mg_text(cv, P, lft + fm.measure("▸ IN MAP ") + 8, mid, "ritual", f)
            cv.addtag_withtag("rit", rt.item)
            rt.config(text=self.ritual_readout())
            if light:
                self._lt_halo_tags(cv, P, ("rit",))
        if "focus" not in rows:
            return self._goalbar_show(main, cv, H, geo)
        mid = mids[rows.index("focus")]
        ftext, fprog = self.focus_line()
        cv.create_text(lft, mid, text="▸ NOW", anchor="w", fill=P["head"], font=(P["hfont"], self._hf(9), "bold"),
                       tags=("mg",))
        nx = lft + fm.measure("▸ NOW ") + 8
        pw = 0 if fprog is None else self._hf(56)
        from .campaign_ui import FitText
        ft = self._mg_text(cv, P, nx, mid, "focus", f, cls=FitText)
        ft.fnt, ft.px = fm, max(40, rgt - nx - pw - 12)     # 2.123.7: fitted by width, not a count of letters
        ft.config(text=ftext)
        self._focus_click(cv, ft)
        if fprog is not None:
            cv.create_rectangle(rgt - pw, mid - 2, rgt, mid + 2, fill=P["cell_bg"], outline=P["line"], tags=("mg",))
            cv.create_rectangle(rgt - pw, mid - 2, rgt - pw + int(pw * min(1.0, fprog)), mid + 2, fill=P["on"],
                                outline="", tags=("mg",))
        return self._goalbar_show(main, cv, H, geo)

    def _goalbar_show(self, main, cv, H, geo):
        self.gb_cv, self._gb_h = cv, H
        self._gb_place(main, geo, H, getattr(self, "_gb_below", False))
        return cv
