"""The Campaign Helper over the game (2.77.0) - the logic is campaign.py.

  * L  The campaign line, on the goal bar (over the Bar / by the Panel): the act and zone, what to do there and
       what it's worth, the next zone, your level against the zone's, the step. Click it for the act's route.
  * M  The act's route: every step - ✓ done, ▸ here, ○ to do, "passed" (gone past without entering). Click a step:
       "I'm here" (a character that's partway through: pick the act, click its step). ◀ ▶ (and their keys).
  * N  Rewards: points, spirit and resistances earned on this character; tick or untick any by hand.
  * O  Vendor search - in town, "Vendor ▾" on the campaign line: this act's searches and your Regex favorites. A click
       copies one; you paste it in the shop's search box (the app never types into the game).
  * P  A zone the guide doesn't know: added to your route where you went, with a note, Mark optional, or a newer guide.
  * Q  Act splits - this run against your best (per league).
  * R  Its settings (Overlay › Options › Campaign); S, T: its switches in "On the overlay" and "On the bar".

Mixed into App. GGG ToS: windows, the clipboard and the game's log only."""
import tkinter as tk
from tkinter import ttk

from . import buglog
from . import campaign as CP
from .overlaywin import CanvasText

PAGES = ("Route", "Rewards", "Act times")   # 2.89.2: "Splits" said nothing to most players


def fit_lines(fnt, text, px, lines):
    """2.123.7: text word-wrapped to px pixels (measured, not counted in letters) on at most `lines` lines; what's
    left over is cut with "…" at the end of the last line."""
    text = " ".join(str(text or "").split())
    out, cur = [], ""
    words = text.split(" ")
    for i, wd in enumerate(words):
        t = f"{cur} {wd}" if cur else wd
        if not cur or fnt.measure(t) <= px:
            cur = t
            continue
        out.append(cur)
        cur = wd
        if len(out) == lines:                          # no room for more: the rest goes on the last line, then cut
            out[-1] = " ".join([out[-1]] + words[i:])
            cur = ""
            break
    if cur:
        out.append(cur)
    for i, ln in enumerate(out):
        if fnt.measure(ln) > px:
            while len(ln) > 1 and fnt.measure(ln + "…") > px:
                ln = ln[:-1]
            out[i] = ln.rstrip(" ,.") + "…"
    return "\n".join(out)


class FitText(CanvasText):
    """A canvas text that fits itself into px pixels on at most `lines` lines (the campaign line - its text is set
    again on every overlay refresh)."""
    fnt, px, lines = None, 200, 1

    def config(self, **kw):
        if "text" in kw and self.fnt is not None:
            kw["text"] = fit_lines(self.fnt, kw["text"], self.px, self.lines)
        super().config(**kw)
    configure = config


class CampaignUI:
    """Mixed into App."""

    # ================================================================ the log
    def campaign_log(self, kind, ts, data):
        """Every game-log event (the session tracker's reader). -> what campaign.log_event said."""
        if kind not in ("area", "scene", "afk", "level"):
            return None
        ak = None
        if kind == "area":
            from .gamelog import area_kind
            ak = area_kind(data.get("area"), data.get("seed"), data.get("level", 0))
            self._camp_town = ak == "town"
        before = CP.line_text()
        try:
            out = CP.log_event(kind, ts, data, ak)
        except Exception:
            self.log_error("the campaign helper")
            return None
        if kind == "area":                                         # 2.92.2: Vendor ▾ on the bar - in town only
            try:
                v = self.vendor_on_bar()
                if v != getattr(self, "_vendor_was", None):
                    self._vendor_was = v
                    if not v:
                        self.camp_vendor_close()
                    if getattr(self, "mg_win", None) is not None:
                        self.merged_build()
            except Exception:
                self.log_error("the Vendor menu")
        if kind == "scene" and getattr(self, "_camp_town", False) and CP.cfg()["warn"] and CP.asks():
            self._camp_later = set()                               # a new town: "Remind me in town" asks again
            self.camp_ask_show()                                   # in town: the rewards to answer
        if out == "maps" and CP.cfg()["off_at_maps"]:
            self._say("Maps! The campaign line hides in maps and comes back in campaign zones (Overlay › Settings › "
                      "Campaign).", 6)
        if out or CP.line_text() != before:
            self.camp_refresh()
        if CP.needs_route() and getattr(self, "camp_rq_win", None) is None:
            self.camp_route_ask_show()                             # 2.89.0: a new campaign - which guide?
        return out

    # ---------------------------------------------------------------- 2.89.0: which guide, when a campaign starts
    def camp_route_ask_show(self):
        self.camp_route_ask_close()
        w, body, P = self._camp_card("New campaign", "🗺", 460, top=0.16,
                                     on_close=lambda: self.camp_route_pick_new(CP.cfg()["route"]))
        bg = P["bg"]
        tk.Label(body, text="Which guide should I follow?", bg=bg, fg=P["head"],
                 font=(P["font"], self.ov_font(11), "bold"), anchor="w").pack(fill="x")
        self.camp_rq_btns = {}
        for k, title, txt, style in (
                ("speed", "Speedrun", "The main story. Skips side zones and most extras; keeps only the rewards "
                                      "worth the time.", "Primary.TButton"),
                ("full", "Full rewards", "Every passive point, spirit and resistance, with the side zones that give "
                                         "them.", "TButton")):
            f = tk.Frame(body, bg=bg, pady=4)
            f.pack(fill="x")
            b = ttk.Button(f, text=title, style=self.ov_btn(style), width=14,
                           command=lambda k=k: self.camp_route_pick_new(k))
            b.pack(side="left", anchor="n")
            tk.Label(f, text=txt, bg=bg, fg=P["text"], font=(P["font"], self.ov_font(9)), anchor="w", justify="left",
                     wraplength=self.ov_px(290)).pack(side="left", fill="x", padx=(8, 0))
            self.camp_rq_btns[k] = b
        self.camp_rq_keep = tk.BooleanVar(value=False)
        tk.Checkbutton(body, text="Use this every time (don't ask again)", variable=self.camp_rq_keep, bg=bg,
                       fg=P["text"], activebackground=bg, activeforeground=P["text"], selectcolor=P["bg"],
                       font=(P["font"], self.ov_font(9)), anchor="w", highlightthickness=0).pack(anchor="w", pady=(8, 0))
        tk.Label(body, text="Change it any time: Overlay › Options › Campaign › Route.", bg=bg, fg=P["muted"],
                 font=(P["font"], self.ov_font(8)), anchor="w").pack(fill="x", pady=(2, 0))
        self.camp_rq_win = w
        w.show()
        return w

    def camp_route_pick_new(self, route):
        CP.set_route(route, remember=bool(getattr(self, "camp_rq_keep", None) and self.camp_rq_keep.get()))
        if getattr(self, "tk_camp_route", None) is not None:
            try:
                self.tk_camp_route.pick(dict(CP.ROUTES).get(CP.cfg()["route"]), notify=False)
            except Exception:
                buglog.caught()
        if getattr(self, "tk_camp_vars", None) and "ask_route" in self.tk_camp_vars:
            self.tk_camp_vars["ask_route"].set(bool(CP.cfg()["ask_route"]))
        self.camp_route_ask_close()
        self.camp_refresh()

    def camp_route_ask_close(self):
        w, self.camp_rq_win = getattr(self, "camp_rq_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def camp_refresh(self, card=True):
        """The line changed: redraw it on the overlay (in place when it still fits the same rows) and the open
        route card's pages (card=False: a click on the card already changed its own line)."""
        try:
            if not self.camp_line_redraw():
                self.goalbar_build()
        except Exception:
            self.log_error("the goal bar")
        if card and getattr(self, "camp_win", None) is not None:
            act = CP.char().get("act")
            if act and act != getattr(self, "_camp_act", None):      # a new act: the card follows you there
                self.camp_view = act
            self._camp_act = act
            self.camp_route_fill()

    def camp_line_redraw(self):
        """2.124.0: the campaign line redrawn where it is, when it still takes as many lines - no rebuild of the
        overlay's lines (the window kept jumping). -> False when the lines must be built again."""
        cv, spot = getattr(self, "gb_cv", None), getattr(self, "_gb_camp", None)
        if cv is None or spot is None or "campaign" not in (getattr(self, "goal_rows", None) or []) \
                or not self.camp_on_bar() or self.goalbar_rows() != self.goal_rows:
            return False
        P, lft, rgt, mid, f, n, lh = spot
        if self.camp_lines(P, rgt - lft) != n:
            return False
        try:
            for tag in ("camp", "campline", "campinfo"):
                cv.delete(tag)
            self.camp_draw_row(cv, P, lft, rgt, mid, f, n=n, lh=lh)
            if self.ov_light():
                self._lt_halo_tags(cv, P, ("camp",))
        except tk.TclError:
            return False
        return True

    def camp_in_town(self):
        d = CP.line()
        return bool(d) and (d["in_town"] or bool(getattr(self, "_camp_town", False)))

    def camp_on_bar(self):
        return CP.active()                                  # 2.97.0: on = its line shows (no line switch)

    def camp_set_on(self, on):
        CP.cfg()["on"] = bool(on)
        CP.save()
        if getattr(self, "tk_camp_var", None) is not None and bool(self.tk_camp_var.get()) != bool(on):
            self.tk_camp_var.set(bool(on))
        r = (getattr(self, "al_rows", None) or {}).get("campaign")        # 2.90.0: Helpers › Campaign follows
        if r is not None and bool(r["on"].get()) != bool(on):
            r["on"].set(bool(on))
        if not on:
            self.camp_close_all()
        self.merged_build()

    def camp_close_all(self):
        for name in ("camp_win", "camp_vendor_win", "camp_ask_win", "camp_rq_win"):
            w = getattr(self, name, None)
            setattr(self, name, None)
            if w is not None:
                try:
                    w.destroy()
                except tk.TclError:
                    pass

    # ================================================================ L: the line (drawn on the goal bar)
    def _camp_fonts(self, P, root=None):
        import tkinter.font as tkfont
        root = root or self.root
        return (tkfont.Font(root=root, family=P["hfont"], size=self._hf(9), weight="bold"),      # the head
                tkfont.Font(root=root, family=P["font"], size=self._hf(10)),                    # the line
                tkfont.Font(root=root, family=P["font"], size=self._hf(9)))                     # levels / step

    @staticmethod
    def _camp_info(d, fi, room):
        """Levels and step if they fit in room px, else the step only, else "2/14" (2.123.7), else nothing."""
        short = d["step"].replace("step ", "").replace(" of ", "/") if d["step"] else ""
        for info in ("   ".join(t for t in (d["levels"], d["step"]) if t), d["step"], short):
            if info and fi.measure(info) + 14 <= room:
                return info
        return ""

    def camp_lines(self, P, avail):
        """2.123.7 (feedback: "you can't see any of the information"): how many text lines the campaign row needs
        in avail px - 1 when the head and the whole line fit side by side, else the head on its own line and the
        line under it, wrapped to at most 3 lines (2.124.1: 2 cut long guide steps)."""
        d = CP.line()
        if not d:
            return 1
        fh, fm, fi = self._camp_fonts(P)
        text = "▸ " + CP.line_text()
        side = avail - fh.measure(d["head"]) - 12              # (the same sums as camp_draw_row's one line)
        info = self._camp_info(d, fi, side * 0.45)
        if fm.measure(text) <= side - (fi.measure(info) + 14 if info else 0):
            return 1
        return 1 + len(fit_lines(fm, text, avail, 3).split("\n"))

    def camp_draw_row(self, cv, P, lft, rgt, mid, font, n=1, lh=0):
        """Draw the campaign line between lft and rgt, centered on mid; n > 1: the head and step on top, the line
        wrapped under them (n - 1 lines, lh px each). -> the items clicked for the route card."""
        from .merged_page import click_not_drag
        d = CP.line()
        if not d:
            return None
        hf = (P["hfont"], self._hf(9), "bold")
        fh, fm, fi = self._camp_fonts(P, cv)
        y1 = mid - (n - 1) * lh / 2 if n > 1 else mid       # the head's line
        y2 = mid + lh / 2 if n > 1 else mid                 # the middle of the line's block under it
        keep = fi.measure(self._camp_info(d, fi, 10 ** 6).split("   ")[-1].replace("step ", "").replace(" of ", "/")) \
            + 26 if d["step"] else 0                         # (room for at least "2/14" beside the head)
        head = cv.create_text(lft, y1, text=fit_lines(fh, d["head"], rgt - lft - keep, 1), anchor="w",
                              fill=P["head"], font=hf, tags=("mg", "camp"))
        x = lft + fh.measure(cv.itemcget(head, "text")) + 12
        right = rgt
        # (2.92.2: Vendor ▾ moved to the bar's menus, beside Notes / Calc / Regex)
        info = self._camp_info(d, fi, (rgt - x) if n > 1 else (rgt - x) * 0.45)
        if info:
            cv.create_text(right, y1, text=info, anchor="e", fill=P["muted"], font=(P["font"], self._hf(9)),
                           tags=("mg", "campinfo"))
            right -= fi.measure(info) + 14
        if n > 1:
            x, right = lft, rgt
        it = cv.create_text(x, y2, text="", anchor="w", fill=P["text"], font=font, tags=("mg", "campline"))
        t = FitText(cv, it, P["bg"], halo=self._mg_halo(P))
        t.fnt, t.px, t.lines = fm, max(40, right - x), max(1, n - 1)
        t.config(text="▸ " + CP.line_text())
        self.tk_ov_lbls["campaign"] = t
        if cv is getattr(self, "gb_cv", None) or getattr(self, "gb_cv", None) is None:
            self._gb_camp = (P, lft, rgt, mid, font, n, lh)
        for item in (head, it):
            click_not_drag(cv, item, self.camp_route_show)      # (2.112.5: a drag moves the line, no card)
            cv.tag_bind(item, "<Enter>", lambda e: cv.configure(cursor="hand2"))
            cv.tag_bind(item, "<Leave>", lambda e: cv.configure(cursor=""))
        return head, it

    # ================================================================ cards over the game
    def _camp_card(self, title, icon, W, top=0.10, on_close=None):
        from .overlaywin import OverlayWindow, pal
        from .alerts_page import game_rect
        P = pal()
        r = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        W = self.ov_px(W)                                    # 2.78.3: the game's size
        geo = (r[0] + (r[2] - W) // 2, r[1] + int(r[3] * top), W, None)
        w = OverlayWindow(self.root, title, icon, geo, palette=P, lockable=False, follow_game=True,
                          no_activate=True, on_close=on_close)
        body = tk.Frame(w.body, bg=P["bg"], padx=16, pady=8)
        body.pack(fill="both", expand=True)
        return w, body, P

    # ---------------------------------------------------------------- M, N, Q: the route card
    def camp_route_show(self, page=None, act_key=None):
        if getattr(self, "camp_win", None) is not None:
            if act_key and act_key != self.camp_view:         # another act: its pages again
                self.camp_view = act_key
                self.camp_page = page or self.camp_page
                self.camp_route_fill()
            elif page:
                self.camp_tab(page)                           # 2.124.0: a tab only swaps the page shown
            return self.camp_win
        self.camp_page = page or "Route"
        self.camp_view = act_key or CP.char().get("act") or (CP.acts()[0]["key"] if CP.acts() else None)
        self._camp_act = CP.char().get("act")
        w, body, P = self._camp_card("Campaign", "🗺", 560, on_close=lambda: self.camp_route_close())
        self.camp_win, self.camp_body, self.camp_P = w, body, P
        self.camp_size = (0, 0)
        self.camp_route_fill()
        w.show()
        return w

    def camp_route_close(self):
        w, self.camp_win = getattr(self, "camp_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def camp_route_fill(self):
        """Build the card: the tabs, the act list and all three pages at once (2.124.0, feedback: clicking Rewards
        made the window resize over and over) - a tab then only swaps the page shown, and the card keeps one size,
        the biggest page's."""
        body, P = self.camp_body, self.camp_P
        for c in body.winfo_children():
            c.destroy()
        bg = P["bg"]
        top = tk.Frame(body, bg=bg)
        top.pack(fill="x")
        self.camp_page_btns = {}
        for p in PAGES:
            b = ttk.Button(top, text=p, style=self.ov_btn("Primary.TButton" if p == self.camp_page else "Quiet.TButton"),
                           command=lambda p=p: self.camp_route_show(page=p))
            b.pack(side="left", padx=(0, 4))
            self.camp_page_btns[p] = b
        names = [a["name"] for a in CP.acts()]
        self.camp_act_cb = None
        if names:
            self.camp_act_var = tk.StringVar(value=CP.act_name(self.camp_view))
            cb = ttk.Combobox(top, values=names, textvariable=self.camp_act_var, state="readonly", width=12)
            # 2.124.0: after the list has closed - the card is built again, and the list went with it while its
            # own dropdown still held the mouse
            cb.bind("<<ComboboxSelected>>", lambda e: self.root.after(1, lambda: self.camp_route_show(
                act_key=next((a["key"] for a in CP.acts() if a["name"] == self.camp_act_var.get()), None))))
            self.camp_act_cb = cb
        self.camp_pages, self._camp_route_dirty = {}, False
        for name, fn in (("Route", self._camp_route_page), ("Rewards", self._camp_rewards_page),
                         ("Act times", self._camp_splits_page)):
            page = tk.Frame(body, bg=bg)
            fn(page, P)
            self.camp_pages[name] = page
        w = self.camp_win
        need_w, need_h = getattr(self, "camp_size", (0, 0))
        for name in PAGES:                                    # (each page shown once to measure it)
            self._camp_show_page(name)
            try:
                w.update_idletasks()
                need_w, need_h = max(need_w, w.winfo_reqwidth()), max(need_h, w.winfo_reqheight())
            except tk.TclError:
                pass
        self._camp_show_page(self.camp_page)
        self.camp_size = (need_w, need_h)
        try:                                                  # one fixed size: what's inside no longer resizes it
            w.geometry(f"{need_w}x{need_h}+{w.winfo_x()}+{w.winfo_y()}")
        except tk.TclError:
            pass

    def _camp_show_page(self, name):
        for n, pg in self.camp_pages.items():
            if n != name:
                pg.pack_forget()
        self.camp_pages[name].pack(fill="both", expand=True, pady=(8, 0))
        cb = getattr(self, "camp_act_cb", None)
        if cb is not None:
            if name == "Act times":
                cb.pack_forget()
            elif not cb.winfo_ismapped():
                cb.pack(side="right")

    def camp_tab(self, page):
        if page not in getattr(self, "camp_pages", {}):
            return
        self.camp_page = page
        if page == "Route" and getattr(self, "_camp_route_dirty", False):
            self._camp_route_dirty = False
            pg = self.camp_pages["Route"]
            for c in pg.winfo_children():
                c.destroy()
            self._camp_route_page(pg, self.camp_P)
        for p, b in self.camp_page_btns.items():
            b.configure(style=self.ov_btn("Primary.TButton" if p == page else "Quiet.TButton"))
        self._camp_show_page(page)

    def _camp_route_page(self, page, P):
        bg, c, run = P["bg"], CP.cfg(), CP.char()
        key = self.camp_view
        head = tk.Frame(page, bg=bg)
        head.pack(fill="x")
        town = (CP.act(key) or {}).get("town") or ""
        tk.Label(head, text=(CP.act_name(key) + (f" · {town}" if town else "")).upper(), bg=bg, fg=P["head"],
                 font=(P["hfont"] or P["font"], self.ov_font(10), "bold"), anchor="w").pack(side="left")
        tk.Label(head, text="route: " + dict(CP.ROUTES).get(CP.route_of(), ""), bg=bg, fg=P["muted"],
                 font=(P["font"], self.ov_font(9))).pack(side="right")
        rows = CP.steps(key, run)
        self.camp_rows = []
        self.camp_marks = marks = {"done": ("✓", P["on"]), "here": ("▸", P["head"]), "todo": ("○", P["muted"]),
                 "passed": ("–", P["muted"])}
        gives = {}
        for r in CP.rewards(key):
            if run["rewards"].get(r["id"]) not in ("got", "skip"):
                gives.setdefault(CP.norm(r["zone"]), []).append(CP.short_gives(r))
        patch = CP.pack().get("patch", "?")
        for i, s in enumerate(rows):
            here = s["state"] == "here"
            rbg = P.get("cell_bg", bg) if here else bg
            f = tk.Frame(page, bg=rbg, cursor="hand2")
            f.pack(fill="x", pady=1)
            mk, col = marks[s["state"]]
            ml = tk.Label(f, text=mk, bg=rbg, fg=col, width=2, font=(P["font"], self.ov_font(10)))
            ml.pack(side="left")
            txt = s["zone"] + (f" - {s['do']}" if s.get("do") else "")
            fg = P["text"] if s["state"] in ("here", "todo") else P["muted"]
            tl = tk.Label(f, text=txt, bg=rbg, fg=fg, font=(P["font"], self.ov_font(10), "bold" if here else "normal"),
                          anchor="w", wraplength=380, justify="left")
            tl.pack(side="left", fill="x", expand=True)
            f.parts = (ml, tl)
            side = ", ".join(gives.get(CP.norm(s["zone"]), []))
            if s.get("learned"):
                side = f"not in the {patch} guide"
            elif s["state"] == "passed":
                side = side or "passed"
            elif s.get("note"):
                side = side or s["note"]
            if side:
                tk.Label(f, text=side, bg=rbg, fg=P["on"] if gives.get(CP.norm(s["zone"])) else P["muted"],
                         font=(P["font"], self.ov_font(9))).pack(side="right")
            for wdg in [f] + list(f.winfo_children()):
                wdg.bind("<Button-1>", lambda e, i=i: self.camp_here(i))
            self.camp_rows.append(f)
            if here and s.get("learned"):
                self._camp_unknown_row(page, P, s)
        if not rows:
            tk.Label(page, text="The guide has no steps for this act yet - they're added as you go.", bg=bg,
                     fg=P["muted"], font=(P["font"], self.ov_font(10))).pack(anchor="w")
        nav = tk.Frame(page, bg=bg)
        nav.pack(fill="x", pady=(8, 0))
        ttk.Button(nav, text="◀", width=3, style=self.ov_btn(), command=lambda: self.camp_step(-1)).pack(side="left")
        ttk.Button(nav, text="▶", width=3, style=self.ov_btn(), command=lambda: self.camp_step(1)).pack(side="left", padx=(4, 0))
        tk.Label(nav, text="Click a step: I'm here", bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(9))).pack(side="left",
                                                                                                 padx=(8, 0))
        tip = (CP.act(key) or {}).get("tip")
        if tip and c["tips"]:
            tk.Label(page, text="Tip: " + tip, bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(9)), anchor="w",
                     justify="left", wraplength=self.ov_px(520)).pack(fill="x", pady=(8, 0))

    def _camp_unknown_row(self, page, P, s):
        """P: a zone the guide doesn't know - a note for it, Mark optional, or check for a newer guide."""
        bg = P["bg"]
        f = tk.Frame(page, bg=bg)
        f.pack(fill="x", pady=(2, 8), padx=(24, 0))
        tk.Label(f, text="The guide doesn't have this zone yet. It's on your route where you went, with its level, "
                         "so it's there next time.", bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(9)), anchor="w",
                 justify="left", wraplength=self.ov_px(480)).pack(fill="x")
        row = tk.Frame(f, bg=bg)
        row.pack(fill="x", pady=(4, 0))
        self.camp_note_var = tk.StringVar(value=s.get("note", ""))
        e = ttk.Entry(row, textvariable=self.camp_note_var, width=22)
        e.pack(side="left")
        ttk.Button(row, text="Add a note", style=self.ov_btn("Primary.TButton"),
                   command=lambda: self.camp_note(s["zone"])).pack(side="left", padx=(4, 0))
        ttk.Button(row, text="Mark optional", style=self.ov_btn("Quiet.TButton"),
                   command=lambda: self.camp_optional(s["zone"])).pack(side="left", padx=(4, 0))
        ttk.Button(row, text="Check for a newer guide", style=self.ov_btn("Quiet.TButton"),
                   command=self.camp_check_pack).pack(side="left", padx=(4, 0))

    def _camp_rewards_page(self, page, P):
        bg, run = P["bg"], CP.char()
        tot = CP.totals(run)
        self.camp_total_labs = {}
        grid = tk.Frame(page, bg=bg)
        grid.pack(fill="x")
        cells = (("SKILL POINTS", "points"), ("SPIRIT", "spirit"))
        for i, (lab, k) in enumerate(cells):
            have, of = tot.get(k, (0, 0))
            f = tk.Frame(grid, bg=bg)
            f.grid(row=0, column=i, sticky="w", padx=(0, 24))
            tk.Label(f, text=lab, bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(8), "bold")).pack(anchor="w")
            self.camp_total_labs[k] = tk.Label(f, text=f"{have} / {of}", bg=bg, fg=P["text"],
                                               font=(P["font"], self.ov_font(15), "bold"))
            self.camp_total_labs[k].pack(anchor="w")
        f = tk.Frame(grid, bg=bg)
        f.grid(row=0, column=2, sticky="w")
        tk.Label(f, text="RESISTANCES", bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(8), "bold")).pack(anchor="w")
        self.camp_total_labs["res"] = tk.Label(f, text=self._camp_res_text(tot), bg=bg, fg=P["text"],
                                               font=(P["font"], self.ov_font(10), "bold"))
        self.camp_total_labs["res"].pack(anchor="w", pady=(4, 0))
        tk.Label(page, text=CP.act_name(self.camp_view).upper(), bg=bg, fg=P["head"],
                 font=(P["hfont"] or P["font"], self.ov_font(9), "bold"), anchor="w").pack(fill="x", pady=(8, 2))
        self.camp_reward_vars = {}
        for r in CP.rewards(self.camp_view):
            st = run["rewards"].get(r["id"])
            v = tk.BooleanVar(value=st == "got")
            self.camp_reward_vars[r["id"]] = v
            row = tk.Frame(page, bg=bg)
            row.pack(fill="x")
            cb = tk.Checkbutton(row, text=f"{r['zone']} - {r['what']}: {r['gives']}", variable=v, bg=bg,
                                fg=P["text"], selectcolor=bg, activebackground=bg, activeforeground=P["text"],
                                font=(P["font"], self.ov_font(10)), anchor="w", highlightthickness=0, bd=0,
                                command=lambda r=r, v=v: self.camp_tick(r["id"], v.get()))
            cb.pack(side="left")
            if st in ("missed", "skip", "remind"):
                tk.Label(row, text={"missed": "missed", "skip": "skipped", "remind": "remind me"}[st], bg=bg,
                         fg=P.get("off", P["muted"]) if st == "missed" else P["muted"],
                         font=(P["font"], self.ov_font(9))).pack(side="right")
        tk.Label(page, text=f"The list comes from the guide pack ({CP.pack().get('name', '')}). Only what the log "
                            "can prove ticks by itself - tick or untick any reward by hand.", bg=bg, fg=P["muted"],
                 font=(P["font"], self.ov_font(9)), anchor="w", justify="left", wraplength=self.ov_px(520)).pack(fill="x", pady=(8, 0))

    def _camp_splits_page(self, page, P):
        bg = P["bg"]
        if not CP.cfg()["splits"]:
            tk.Label(page, text="The act timer is off (Overlay › Options › Campaign).", bg=bg, fg=P["muted"],
                     font=(P["font"], self.ov_font(10))).pack(anchor="w")
            return
        g = tk.Frame(page, bg=bg)
        g.pack(fill="x")
        for c, h in enumerate(("ACT", "THIS RUN", "BEST", "+/-")):
            tk.Label(g, text=h, bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(8), "bold")).grid(row=0, column=c, sticky="w",
                                                                                     padx=(0, 24))
        self.camp_split_rows = []
        for i, (name, mine, best, here) in enumerate(CP.splits(), start=1):
            diff, dcol = "", P["muted"]
            if mine is not None and best is not None and not here:
                d = round(mine - best)
                diff, dcol = (("+" if d > 0 else "-") + CP.fmt(abs(d)), P.get("off", P["muted"]) if d > 0 else P["on"])
                if d == 0:
                    diff, dcol = "even", P["muted"]
            elif mine is not None and best is not None and here and mine < best:
                diff, dcol = "ahead", P["on"]
            vals = (name, CP.fmt(mine) + (" ▸" if here else ""), CP.fmt(best), diff)
            for c, v in enumerate(vals):
                tk.Label(g, text=v, bg=bg, fg=dcol if c == 3 else (P["text"] if mine is not None else P["muted"]),
                         font=(P["font"], self.ov_font(10))).grid(row=i, column=c, sticky="w", padx=(0, 24))
            self.camp_split_rows.append(vals)
        tk.Label(page, text="From the game log's zone changes, with pauses for AFK. Each league keeps its own best.",
                 bg=bg, fg=P["muted"], font=(P["font"], self.ov_font(9)), anchor="w").pack(fill="x", pady=(8, 0))

    # ---------------------------------------------------------------- actions
    def camp_here(self, i):
        run = CP.char()
        same = run.get("act") == self.camp_view
        if same:
            CP.set_here(i, run)
        else:
            CP.start_here(self.camp_view, i, run)                  # "Start from here" (partway through)
        if same and self._camp_rows_restyle():                     # 2.124.0: only the rows whose mark changed
            return self.camp_refresh(card=False)
        self.camp_refresh()

    def _camp_rows_restyle(self):
        """The route page's rows take their new state (✓ ▸ ○ –) in place. -> False when the steps changed."""
        rows, P = CP.steps(self.camp_view, CP.char()), self.camp_P
        frames = getattr(self, "camp_rows", None) or []
        if len(rows) != len(frames) or any(s.get("learned") for s in rows):
            return False
        bg = P["bg"]
        try:
            for s, f in zip(rows, frames):
                here = s["state"] == "here"
                rbg = P.get("cell_bg", bg) if here else bg
                mk, col = self.camp_marks[s["state"]]
                ml, tl = f.parts
                if ml.cget("text") == mk and f.cget("bg") == rbg:
                    continue
                for wdg in f.winfo_children() + [f]:
                    wdg.configure(bg=rbg)
                ml.configure(text=mk, fg=col)
                tl.configure(fg=P["text"] if s["state"] in ("here", "todo") else P["muted"],
                             font=(P["font"], self.ov_font(10), "bold" if here else "normal"))
        except (tk.TclError, AttributeError, KeyError):
            return False
        return True

    def camp_step(self, delta):
        """◀ ▶ on the route card: a step back or on (2.124.0: within the act, only the rows that changed)."""
        CP.step_by(delta)
        act = CP.char().get("act") or self.camp_view
        if act == self.camp_view and getattr(self, "camp_win", None) is not None and self._camp_rows_restyle():
            return self.camp_refresh(card=False)
        self.camp_view = act
        self.camp_refresh()

    def camp_tick(self, rid, on):
        """A reward ticked on the card: its box already shows it - the totals and the overlay's line follow
        (2.124.0: the card isn't built again)."""
        CP.set_reward(rid, "got" if on else None)
        self._camp_totals_paint()
        self._camp_route_dirty = True                          # (the Route page's "worth" notes: when it's shown)
        self.camp_refresh(card=False)

    def _camp_totals_paint(self):
        tot, labs = CP.totals(CP.char()), getattr(self, "camp_total_labs", None) or {}
        try:
            for k, lab in labs.items():
                have, of = tot.get(k, (0, 0))
                if k == "res":
                    continue
                lab.configure(text=f"{have} / {of}")
            if "res" in labs:
                labs["res"].configure(text=self._camp_res_text(tot))
        except tk.TclError:
            pass

    @staticmethod
    def _camp_res_text(tot):
        res = []
        for k, name in (("res_cold", "Cold"), ("res_lightning", "Lightning"), ("res_fire", "Fire")):
            have, of = tot.get(k, (0, 0))
            res.append(f"{name} {'✓' if of and have >= of else '○'}")
        return " · ".join(res)

    def camp_note(self, zone):
        CP.set_note(zone, self.camp_note_var.get())
        self.camp_refresh()

    def camp_optional(self, zone):
        CP.mark_optional(zone)
        self.camp_refresh()

    def camp_check_pack(self):
        st, msg = CP.fetch_live()
        txt = {"new": f"New guide pack: {msg}.", "same": f"You have the newest guide pack ({msg})."}.get(st, msg)
        self._say(txt, 6)
        if getattr(self, "tk_camp_pack", None) is not None:
            try:
                self.tk_camp_pack.config(text=self.camp_pack_text())
            except tk.TclError:
                pass
        if st == "new":
            self.camp_refresh()
        return st

    def camp_pack_text(self):
        p = CP.pack()
        return f"Guide pack: {p.get('name', '?')} (revision {p.get('revision', 0)})"

    # ---------------------------------------------------------------- the rewards to answer (N)
    def camp_ask_show(self):
        self.camp_ask_close()
        later = getattr(self, "_camp_later", set())
        items = [(r, st) for r, st in CP.asks() if r["id"] not in later]
        if not items:
            return None
        w, body, P = self._camp_card("Campaign rewards", "★", 460, top=0.16, on_close=lambda: self.camp_ask_close())
        bg = P["bg"]
        self.camp_ask_btns = {}
        for r, st in items[:4]:
            f = tk.Frame(body, bg=bg, pady=4)
            f.pack(fill="x")
            if st == "missed":
                head, txt = "Missed one:", f"{r['what']} in {r['zone']} ({r['gives']}). It's still there."
            else:
                head, txt = "Did you get it?", f"{r['what']} in {r['zone']} ({r['gives']})."
            tk.Label(f, text=head, bg=bg, fg=P["head"], font=(P["font"], self.ov_font(10), "bold"), anchor="w").pack(fill="x")
            tk.Label(f, text=txt, bg=bg, fg=P["text"], font=(P["font"], self.ov_font(10)), anchor="w", justify="left",
                     wraplength=self.ov_px(420)).pack(fill="x")
            row = tk.Frame(f, bg=bg)
            row.pack(fill="x", pady=(4, 0))
            for k, label, style in (("got", "Got it", "Primary.TButton"), ("remind", "Remind me in town", "TButton"),
                                    ("skip", "Skip it", "Quiet.TButton")):
                b = ttk.Button(row, text=label, style=self.ov_btn(style), command=lambda r=r, k=k: self.camp_answer(r["id"], k))
                b.pack(side="left", padx=(0, 8))
                self.camp_ask_btns[(r["id"], k)] = b
        if len(items) > 4:
            tk.Label(body, text=f"+{len(items) - 4} more - Campaign › Rewards", bg=bg, fg=P["muted"],
                     font=(P["font"], self.ov_font(9))).pack(anchor="w")
        self.camp_ask_win = w
        w.show()
        return w

    def camp_answer(self, rid, how):
        """Got it / Remind me in town (asks again at the next town) / Skip it."""
        CP.set_reward(rid, how)
        if how == "remind":
            self._camp_later = getattr(self, "_camp_later", set()) | {rid}
        if not self.camp_ask_show():
            self.camp_ask_close()
        self.camp_refresh()

    def camp_ask_close(self):
        w, self.camp_ask_win = getattr(self, "camp_ask_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    # ---------------------------------------------------------------- O: vendor search
    def camp_vendor_show(self):
        self.camp_vendor_close()
        w, body, P = self._camp_card("Vendor search", "🔎", 420, top=0.14, on_close=lambda: self.camp_vendor_close())
        bg = P["bg"]
        tk.Label(body, text="Click one = copied · Ctrl+V in the shop search", bg=bg, fg=P["muted"],
                 font=(P["font"], self.ov_font(9)), anchor="w").pack(fill="x")
        self.camp_vendor_btns = {}

        def group(title, rows):
            if not rows:
                return
            tk.Label(body, text=title, bg=bg, fg=P["head"], font=(P["hfont"] or P["font"], self.ov_font(8), "bold"),
                     anchor="w").pack(fill="x", pady=(8, 2))
            for name, rx in rows:
                b = ttk.Button(body, text=name, style=self.ov_btn(), command=lambda n=name, rx=rx: self.camp_copy(n, rx))
                b.pack(fill="x", pady=1)
                self.camp_vendor_btns[name] = b
        group("FOR THIS ACT", CP.vendor_searches())      # (2.92.2: your favorites: Regex ▾ on the bar)
        if not CP.vendor_searches():
            tk.Label(body, text="No vendor searches for this act.", bg=bg, fg=P["muted"],
                     font=(P["font"], self.ov_font(9)), anchor="w").pack(fill="x", pady=(8, 0))
        # 2.124.0 (feedback: a click made the card wider to fit "Copied: ..."): two lines kept for it, wrapped to the
        # card's width, and the card keeps its size
        self.camp_vendor_msg = tk.Label(body, text="", bg=bg, fg=P["on"], font=(P["font"], self.ov_font(9)), anchor="nw",
                                        justify="left", height=2)
        self.camp_vendor_msg.pack(fill="x", pady=(8, 0))
        self.camp_vendor_win = w
        w.show()
        try:
            w.update_idletasks()
            self.camp_vendor_msg.configure(wraplength=max(120, body.winfo_width() - 8))
            w.geometry(f"{w.winfo_width()}x{w.winfo_height()}+{w.winfo_x()}+{w.winfo_y()}")
        except tk.TclError:
            pass
        return w

    def camp_copy(self, name, rx):
        self.root.clipboard_clear()
        self.root.clipboard_append(rx)
        if getattr(self, "camp_vendor_msg", None) is not None:
            try:
                self.camp_vendor_msg.config(text=f"✓ Copied: {name} - paste it in the shop's search box.")
            except tk.TclError:
                pass
        return rx

    def camp_vendor_close(self):
        w, self.camp_vendor_win = getattr(self, "camp_vendor_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    # ================================================================ R: its settings (Overlay › Options)
    def camp_options(self, po, into=None):
        """Its options (route, splits ...). 2.82.0: into = the Campaign card on Overlay ↳ Settings."""
        from .chrome import section as chrome_section
        from .style import C, SegBar
        c = CP.cfg()
        P2 = C["panel2"]
        if into is not None:
            box = tk.Frame(into, bg=P2)
            box.pack(fill="x", pady=(8, 0))
        else:
            so, box = chrome_section(po, "Campaign", "The Campaign Helper: where you are, what's next and what it's "
                                                      "worth - from the game's log. Click its line on the overlay for "
                                                      "the act's route, rewards and splits.")
            so.pack(fill="x", pady=(8, 0))
        row = tk.Frame(box, bg=P2)
        row.pack(fill="x")
        tk.Label(row, text="Route", bg=P2, fg=C["text"]).pack(side="left", padx=(0, 8))
        names = [n for _k, n in CP.ROUTES]
        self.tk_camp_route = SegBar(row, names, value=dict(CP.ROUTES).get(c["route"], names[0]), size=9, pad=(12, 4),
                                    command=self.camp_route_pick)
        self.tk_camp_route.pack(side="left")
        grid = tk.Frame(box, bg=P2)
        grid.pack(fill="x", pady=(8, 0))
        self.tk_camp_vars = {}
        opts = (("ask_route", "Ask Speedrun or Full rewards when a campaign starts"),   # 2.89.0
                ("optional", "Optional zones"), ("tips", "Tips (bosses, vendor checks)"),
                ("warn", "Missing rewards - warn when I leave an act"),
                ("off_at_maps", "Hide it in maps (back in campaign zones)"))
        # (2.96.1: no Act timer switch - act times are always kept; the Leaderboards get them only if you share data)
        for i, (k, label) in enumerate(opts):
            v = tk.BooleanVar(value=bool(c[k]))
            self.tk_camp_vars[k] = v
            cb = ttk.Checkbutton(grid, text=label, variable=v, style="Card.TCheckbutton",
                                 command=lambda k=k: self.camp_opt(k))
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 24), pady=2)
        # (2.90.0: Dock is in On the bar › Lines above the bar, with the lines themselves)
        for col in range(2):
            grid.columnconfigure(col, uniform="cs")
        pk = tk.Frame(box, bg=P2)
        pk.pack(fill="x", pady=(8, 0))
        self.tk_camp_pack = tk.Label(pk, text=self.camp_pack_text(), bg=P2, fg=C["muted"], font=("Segoe UI", 9))
        self.tk_camp_pack.pack(side="top" if into is not None else "left", anchor="w")   # 2.82.0: in a card, own line
        ttk.Button(pk, text="Check for a newer one", style="Quiet.TButton", command=self.camp_check_pack).pack(
            side="left", padx=(0 if into is not None else 8, 0), pady=(4 if into is not None else 0, 0))
        ttk.Button(pk, text="Open the route", style="Quiet.TButton", command=self.camp_route_show).pack(
            side="left", padx=(8, 0), pady=(4 if into is not None else 0, 0))

    def camp_route_pick(self, name):
        CP.cfg()["route"] = next((k for k, n in CP.ROUTES if n == name), "full")
        run = CP.char()
        if run.get("act") is not None and not run.get("done"):   # 2.89.0: the run you're on follows too
            run["route"] = CP.cfg()["route"]
        CP.save()
        self.camp_route_ask_close()
        self.camp_refresh()

    def camp_opt(self, k):
        CP.cfg()[k] = bool(self.tk_camp_vars[k].get())
        CP.save()
        self.camp_refresh()

    def camp_line_switch(self, var=None):
        CP.cfg()["line"] = bool((var or self.tk_cline_var).get())    # 2.90.0: the box you clicked, not a stale copy
        CP.save()
        self.merged_build()

    def camp_vendor_toggle(self):
        """2.92.2: Vendor ▾ on the bar opens / closes the card."""
        if getattr(self, "camp_vendor_win", None) is not None:
            self.camp_vendor_close()
        else:
            self.camp_vendor_show()
        if getattr(self, "mg_win", None) is not None:
            self.merged_build()

    def camp_vendor_switch(self, var=None):
        on = bool((var or self.tk_cvendor_var).get())
        CP.cfg()["vendor"] = on
        self.bar_cfg()["vendor"] = on                 # 2.92.2: one switch (it was two that had to agree)
        self.tracker_save()
        bv = (getattr(self, "tk_bar_vars", None) or {}).get("vendor")
        if bv is not None and bv is not var and bool(bv.get()) != on:
            bv.set(on)
        CP.save()
        if not CP.cfg()["vendor"]:
            self.camp_vendor_close()
        self.merged_build()
