"""Two parts of the overlay that got their own place (2.76.0).

  * Map rank - your rank for the map you're in (S A B C D or Avoid; the community's in brackets when you have none)
    was glued onto "where you are". It's its own part now, with its own switch (Overlay › Options › On the overlay).
    Click it to rank the map. "Ask me to rank maps I haven't ranked" (on by default): leaving a map you haven't
    ranked, a small card asks - S A B C D Avoid, Not now, or Never for this map. Feedback: "isolate the Map
    Tier/rating piece on the overlay and add an option ... to prompt a user to give unrated maps a rating".
  * The goal bar - League Focus's line (and the Campaign Helper's, 2.77.0) sat in the map's place on the bar and
    crowded it. It has its own small bar now, in the overlay's style: a short plate over the Game bar, or a small card
    under the Panel. Dragged where you like while unlocked; the overlay's one lock holds it. Feedback: "a second,
    smaller version of the overlay/overlay bar".

GGG ToS: windows and the game's log only - nothing is sent to the game."""
import tkinter as tk
from tkinter import ttk

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
        self._say("Rank a map from the Map library (Overlay ↳ Map library), or click this while you're in one.", 6)
        return None

    def maprank_prompt(self, name):
        """A small card at the top of the game: how was this map? -> the window."""
        from .overlaywin import OverlayWindow, pal
        from .alerts_page import game_rect
        self.maprank_close()
        P = pal()
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        W = 420
        geo = (r[0] + (r[2] - W) // 2, r[1] + int(r[3] * 0.08), W, None)
        w = OverlayWindow(self.root, "Rank this map", "★", geo, palette=P, lockable=False, follow_game=True,
                          no_activate=True, on_close=self.maprank_close)
        bg = P["bg"]
        body = tk.Frame(w.body, bg=bg, padx=16, pady=8)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=f"How was {name}?", bg=bg, fg=P["text"], font=(P["font"], 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(body, text="Your rank shows on the overlay next time, and counts as your vote for the community's.",
                 bg=bg, fg=P["muted"], font=(P["font"], 9), anchor="w", justify="left", wraplength=W - 40).pack(fill="x")
        row = tk.Frame(body, bg=bg)
        row.pack(fill="x", pady=(8, 0))
        self.maprank_btns = {}
        for rk in RANK_BUTTONS:
            b = ttk.Button(row, text=rk, width=6 if rk == "Avoid" else 3,
                           command=lambda rk=rk: self.maprank_set(name, rk))
            b.pack(side="left", padx=(0, 4))
            self.maprank_btns[rk] = b
        row2 = tk.Frame(body, bg=bg)
        row2.pack(fill="x", pady=(8, 0))
        for key, label in (("later", "Not now"), ("never", "Never for this map")):
            b = ttk.Button(row2, text=label, style="Quiet.TButton", command=lambda k=key: self.maprank_skip(name, k))
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
            pass

    def maprank_skip(self, name, how):
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
        """What the goal bar holds, top to bottom: 'campaign' (2.77.0, while you're in the campaign), 'focus'."""
        rows = []
        try:
            if self.camp_on_bar():
                rows.append("campaign")
        except Exception:
            self.log_error("the campaign line")
        if self.focus_line()[0]:
            rows.append("focus")
        return rows

    def goalbar_wanted(self):
        return bool(self.goalbar_rows())

    def goalbar_destroy(self):
        w, self.gb_win = getattr(self, "gb_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def _goalbar_spot(self, layout, gw, gh):
        cfg = self.tracker_cfg()
        saved = (cfg.get("goal_pos") or {}).get(layout)
        if isinstance(saved, (list, tuple)) and len(saved) == 2:
            return int(saved[0]), int(saved[1])
        main = getattr(self, "mg_win", None)
        try:
            main.update_idletasks()
            mx, my, mw, mh = main.winfo_x(), main.winfo_y(), main.winfo_width(), main.winfo_height()
            if mw <= 1:
                raise tk.TclError
        except (tk.TclError, AttributeError):
            from .alerts_page import game_rect
            r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
            return r[0] + (r[2] - gw) // 2, r[1] + int(r[3] * 0.80)
        if layout == "xpbar":                                 # over the Game bar, in the middle
            return mx + (mw - gw) // 2, my - gh - 6
        from .alerts_page import game_rect
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        if my + mh + 6 + gh > r[1] + r[3]:                    # no room under the Panel: over it
            return mx, max(r[1], my - gh - 6)
        return mx, my + mh + 6                                # under the Panel

    def goalbar_build(self):
        """(Re)build the goal bar after the overlay was built. -> the window or None."""
        from .overlaywin import OverlayWindow
        from .merged_page import _Trunc
        from . import hudart, themes as TH
        from .overlaywin import _seed, pal
        import tkinter.font as tkfont
        self.goalbar_destroy()
        main = getattr(self, "mg_win", None)
        if main is None or not self.goalbar_wanted():
            return None
        cfg = self.tracker_cfg()
        layout = self.merged_layout()
        hud = layout == "xpbar"
        P = hudart.palette(pal()) if hud else hudart.card_palette(pal())
        _seed(TH, P)
        try:
            main.update_idletasks()
            mw, mh = main.winfo_width(), main.winfo_height()
        except tk.TclError:
            mw, mh = 600, 60
        mw = mw if mw > 1 else 600
        mh = mh if mh > 1 else 60
        rows = self.goalbar_rows()
        gw = max(320, int(mw * (0.6 if hud else 1.0)))
        if "campaign" in rows:                               # 2.78.2: as wide as the overlay's bar (feedback: "scale
            gw = mw                                          # to match the width of the other piece")
        row_h = max(30, int((self.hud_spots("xpbar")[0][3] if hud else 60) * (0.55 if hud else 0.62)))
        gh = row_h + int(row_h * 0.8) * (len(rows) - 1)
        x, y = self._goalbar_spot(layout, gw, gh)

        def moved(nx, ny, _w, _h):
            cfg.setdefault("goal_pos", {})[layout] = [int(nx), int(ny)]
            self.tracker_save()
        w = OverlayWindow(self.root, "Goal", "🎯", (x, y, gw, gh), opacity=int(cfg.get("opacity", 225)),
                          locked=bool(cfg.get("mlocked")), min_size=(200, 24), on_close=None,
                          on_lock=lambda on: self.overlay_lock(on), on_moved=moved, follow_game=True,
                          no_activate=True, resizable=False, titlebar=False, palette=P)
        w.withdraw()
        cv = w.canvas_body()
        W, H = gw - 2, gh - 2
        cv.configure(width=W, height=H)
        if not cfg.get("mlocked"):
            w.draggable(cv)
        if hud:
            ends, self._hud_ends = getattr(self, "_hud_ends", None), ("amber", "amber")
            lft, rgt = self._hud_frame(cv, P, W, H)
            self._hud_ends = ends or ("crimson", "sapphire")
        else:
            art = hudart.card(cv, W, H, None, [(8, 6, W - 8, H - 6, 1, 1)], None)
            if art is not None:
                cv.create_image(0, 0, image=art, anchor="nw", tags=("hudbg",))
                cv._card_imgs = [art]
            lft, rgt = 16, W - 16
        mids = [int(H * (2 * i + 1) / (2 * len(rows))) for i in range(len(rows))]
        f = (P["font"], self._hf(10))
        self.gb_rows = rows
        if "campaign" in rows:
            self.camp_draw_row(cv, P, lft, rgt, mids[rows.index("campaign")], f)
            if len(rows) > 1:
                y = (mids[0] + mids[1]) // 2
                cv.create_line(lft, y, rgt, y, fill=P["line"], tags=("mg",))
        if "focus" not in rows:
            return self._goalbar_show(w, cv)
        mid = mids[rows.index("focus")]
        ftext, fprog = self.focus_line()
        f = (P["font"], self._hf(10))
        fm = tkfont.Font(root=cv, family=P["font"], size=self._hf(10))
        cv.create_text(lft, mid, text="▸ NOW", anchor="w", fill=P["head"], font=(P["hfont"], self._hf(9), "bold"),
                       tags=("mg",))
        nx = lft + fm.measure("▸ NOW ") + 8
        pw = 0 if fprog is None else self._hf(56)
        ft = self._mg_text(cv, P, nx, mid, "focus", f, cls=_Trunc)
        ft.limit = max(4, int((rgt - nx - pw - 12) / (fm.measure("n") or 7)))
        ft.config(text=ftext)
        self._focus_click(cv, ft)
        if fprog is not None:
            cv.create_rectangle(rgt - pw, mid - 2, rgt, mid + 2, fill=P["cell_bg"], outline=P["line"], tags=("mg",))
            cv.create_rectangle(rgt - pw, mid - 2, rgt - pw + int(pw * min(1.0, fprog)), mid + 2, fill=P["on"],
                                outline="", tags=("mg",))
        return self._goalbar_show(w, cv)

    def _goalbar_show(self, w, cv):
        self.gb_win, self.gb_cv = w, cv
        w.click_through = self.click_through_on()
        from .merged_page import set_click_through
        set_click_through(w, w.click_through)
        if getattr(self, "mg_hidden", False):
            w.hide()
        else:
            w.show()
        return w
