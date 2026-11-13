"""2.139.0 The overlay's Map First layout (the mockup the user picked - "I like a8 yeah, make sure it works for all
themes"), in every style, Bar and Panel:

  [● IN MAP]  📍 THIS MAP · ★ A          | SESSION ⓘ | LAST MAP'S PROFIT ⓘ    ...  tools  clock  🔒 ⚙
              Penitentiary   3:41        | 17:04:33  | +5.5 chaos

The chip says where you are with a mark and a word (In map, Paused, Hideout, Town, Start) and pauses / resumes the
session; the map you're in leads; maps run and the average are one hover away on SESSION; the profit's hover shows
how it was worked out. Each style keeps its own frame, colors, fonts and dividers - this draws the parts.

GGG ToS: the app's own windows only; nothing here touches the game."""
import tkinter as tk

from . import buglog
from .overlaywin import CanvasText

CHIPS = {"map": ("●", "IN MAP"), "paused": ("❚❚", "PAUSED"), "hideout": ("⌂", "HIDEOUT"), "town": ("⌂", "TOWN"),
         "idle": ("▶", "START SESSION"), "zone": ("●", "CAMPAIGN"), "other": ("●", "TRACKING")}
CHIP_TIPS = {"paused": "Resume the session", "idle": "Start a session"}
LONGEST_CHIP = "● TRACKING"           # (a running session's longest; START SESSION has the bar to itself)


def chip_key(session, camp=False):
    """The chip's state from the session: idle (none running), paused, campaign, or where you are."""
    if session is None or getattr(session, "ended", None) is not None:
        return "idle"
    if getattr(session, "paused_at", None):
        return "paused"
    if camp:
        return "zone"
    kind = (getattr(session, "where", None) or {}).get("kind")
    return kind if kind in ("map", "hideout", "town") else "other"


def chip_text(key):
    mark, word = CHIPS.get(key, CHIPS["other"])
    return f"{mark} {word}"


def place_texts(n, session, live, camp=False, zone_time=None):
    """-> (label, place, timer): what the map part says. In a map: THIS MAP / its name / its time; out of one: NOW /
    Hideout, Town or Between maps; the campaign: ZONE / the zone / its time."""
    if camp:
        return "ZONE", "", zone_time or ""
    kind = (getattr(session, "where", None) or {}).get("kind") if live else None
    t = n.get("map")
    t = "" if t in (None, "-") else str(t)
    if live and kind == "map":
        where = n.get("where")
        return "THIS MAP", ("" if where in (None, "-") else str(where)), t
    if not live:
        return "NOW", "Not tracking", ""
    return "NOW", {"hideout": "Hideout", "town": "Town"}.get(kind, "Between maps"), ""


class _Chip(CanvasText):
    """The state chip: one width (the longest state's), its text centered - the parts after it never move."""
    configure = CanvasText.config


class _Fit(CanvasText):
    """Text cut to a width in pixels (a map's long name); the map's time (follow) sits right after it."""
    width, font, follow, gap = 200, None, None, 8

    def config(self, **kw):
        if "text" in kw and self.font is not None:
            from tkinter import font as tkfont
            t = " ".join(str(kw["text"] or "").split())
            try:
                f = tkfont.Font(root=self.canvas, font=self.font)
                while len(t) > 2 and f.measure(t) > self.width:
                    t = t[:-2].rstrip() + "…"
            except tk.TclError:
                pass
            kw["text"] = t
        super().config(**kw)
        if self.follow is not None and "text" in kw:
            try:
                bb = self.canvas.bbox(self.item)
                x, y = self.canvas.coords(self.follow.item)
                nx = (bb[2] if bb and kw["text"] else self.canvas.coords(self.item)[0]) + self.gap
                self.follow.canvas.move(self.follow.item, nx - x, 0)
                for h, _dx, _dy in getattr(self.follow, "halos", []):
                    self.follow.canvas.move(h, nx - x, 0)
            except (tk.TclError, ValueError, TypeError):
                pass
    configure = config


class OverlayA8:
    """Mixed into App."""

    # ---------------------------------------------------------------- what it says (tracker_overlay_draw)
    def a8_texts(self, n, live, camp=False):
        s = getattr(self, "tk_session", None)
        zt = None
        if camp:
            try:
                from . import campaign as CP
                from .tracker import fmt_time
                z = CP.zone_time()
                zt = fmt_time(z) if z is not None else ""
            except Exception:
                buglog.caught()
        label, place, timer = place_texts(n, s, live, camp, zt)
        if camp:
            try:
                from . import campaign as CP
                place = CP.line_text() or "Campaign"
            except Exception:
                place = "Campaign"
        rank = ""
        try:
            rank = self.rank_text(n.get("where") if live and getattr(self, "_mr_in", None) else None) or ""
        except Exception:
            buglog.caught()
        if rank and label == "THIS MAP":
            label = f"THIS MAP · {rank}"
        return {"a8_chip": chip_text(chip_key(s, camp)), "a8_label": label, "a8_place": place, "a8_timer": timer}

    def a8_session_tip(self):
        n = self.tracker_numbers() or {}
        maps, avg = n.get("maps", "0"), n.get("avg", "-")
        return f"{maps} maps this session" + (f", {avg} on average" if avg not in (None, "-", "") else "")

    def a8_chip_tip(self):
        return CHIP_TIPS.get(chip_key(getattr(self, "tk_session", None)), "Pause the session")

    # ---------------------------------------------------------------- the parts
    def _a8_label(self, cv, P, x, y, text, key=None, anchor="w"):
        """A part's small label (SESSION ⓘ ...) above its value."""
        return self._lt_text(cv, P, x, y, text, 8, P["muted"], anchor=anchor, bold=True, key=key)

    def _a8_chip(self, cv, P, x, mid, h, longest=LONGEST_CHIP):
        """The state chip at x (left edge). -> its width."""
        u = self._u
        f = (P["font"], self._hf(8), "bold")
        fm = self._lt_fm(cv, P, 8, True)
        w = fm.measure(longest) + 2 * u(8)
        y0, y1 = mid - h // 2, mid + h // 2
        cv.create_rectangle(x, y0, x + w, y1, outline=P.get("line", P["muted"]),
                            fill=P.get("cell_bg") or P.get("field") or P["bg"], tags=("mg", "mg_a8chip"))
        it = cv.create_text(x + w // 2, mid, text="● IN MAP", anchor="center", fill=P.get("accent") or P["text"],
                            font=f, tags=("mg", "mg_a8chip"))
        t = _Chip(cv, it, P["bg"], halo=P.get("halo"))
        self.tk_ov_lbls["a8_chip"] = t
        cv.tag_bind("mg_a8chip", "<Button-1>", lambda e: (self.ov_tip_hide(), self.tracker_play_click()))
        self.ov_tip(cv, "mg_a8chip", self.a8_chip_tip)
        return w

    def _a8_pin(self, cv, P, x, y):
        """A map pin, drawn (fonts' pins differ from PC to PC). -> its width."""
        u = self._u
        r = u(4)
        col = P.get("accent") or P["text"]
        cv.create_oval(x, y - r * 2, x + 2 * r, y, outline=col, width=max(1, u(2)), tags=("mg",))
        cv.create_line(x + r, y, x + r, y + r + u(2), fill=col, width=max(1, u(2)), tags=("mg",))
        return 2 * r

    def a8_bar(self, w, cv, P, want, x0, right, mid, sep, map_w=None, spread=None):
        """The Bar's left side from x0: chip, the map part, SESSION, LAST MAP'S PROFIT - up to `right` (the map part
        takes the room left), or as wide as it needs when right is None (map_w for the map part). sep(x) draws the
        style's divider. -> the x it ended at."""
        u = self._u
        ln = self.ov_lines()
        if not want["timer"]:                               # no session: the chip alone - ▶ START SESSION starts one
            cw = self._a8_chip(cv, P, x0, mid, u(20), longest=chip_text("idle"))
            self.tk_ov_lbls.pop("a8_chip").config(text=chip_text("idle"))
            return x0 + cw + u(12)
        ly, vy = (mid - spread[0], mid + spread[1]) if spread else (mid - u(8), mid + u(7))     # label / value lines
        x = x0 + self._a8_chip(cv, P, x0, mid, u(20)) + u(12)
        fl, fv = self._lt_fm(cv, P, 8, True), self._lt_fm(cv, P, 11, True)
        ses_w = max(fl.measure("SESSION ⓘ"), fv.measure("00:00:00")) if ln.get("session", True) else 0
        prof = False
        try:
            prof = bool(self.mp_on())
        except Exception:
            buglog.caught()
        prof_w = max(fl.measure("LAST MAP'S PROFIT ⓘ"), fv.measure("+00.0 chaos")) if prof else 0
        gap = u(20)                                          # a divider's slot
        fixed = (ses_w + gap if ses_w else 0) + (prof_w + gap if prof_w else 0)
        show_map = ln.get("map", True) or ln.get("where", True)
        if right is None:
            room = map_w or u(240)
        else:
            room = right - x - fixed - u(6)
            if room < u(150) and ses_w:                     # narrow: the session leaves first (the profit stays)
                fixed -= ses_w + gap
                ses_w = 0
                room = right - x - fixed - u(6)
            room = min(room, u(300))                        # (wide: the rest is space before the tools)
        if show_map and room > u(60):
            px = x + self._a8_pin(cv, P, x, mid + u(3)) + u(8)
            self._a8_label(cv, P, px, ly, "THIS MAP", key="a8_label")
            tf = self._lt_fm(cv, P, 12, True)
            tw = tf.measure("00:00") + u(4)
            tm = self._lt_text(cv, P, px, vy, "", 12, P.get("accent") or P["big"], bold=True, key="a8_timer")
            t = self._lt_text(cv, P, px, vy, "", 12, P["big"], bold=True, key="a8_place", cls=_Fit)
            t.width, t.font = max(u(40), x + room - px - tw - u(8)), (P["font"], self._hf(12), "bold")
            t.follow, t.gap = tm, u(10)
            x += room
        if ses_w:
            sep(x + gap // 2)
            x += gap
            from .merged_page import _Time
            lab = self._a8_label(cv, P, x, ly, "SESSION ⓘ")
            t = self._lt_text(cv, P, x, vy, "", 11, P["big"], bold=True, key="session", cls=_Time)
            t.num, t.dim = True, (P["big"], P["muted"])
            cv.addtag_withtag("mg_a8ses", t.item)
            cv.addtag_withtag("mg_a8ses", lab.item)
            self.ov_tip(cv, "mg_a8ses", self.a8_session_tip, hand=False)
            x += ses_w
        if prof_w:
            sep(x + gap // 2)
            x += gap
            lab = self._a8_label(cv, P, x, ly, "LAST MAP'S PROFIT ⓘ")
            t = self._lt_text(cv, P, x, vy, "", 11, P.get("accent") or P["big"], bold=True, key="profit")
            try:
                self.mp_bar_bind(cv, t.item)
                self.mp_bar_bind(cv, lab.item)
            except Exception:
                buglog.caught()
            x += prof_w
        if self.tk_ov_cv is None:
            self.tk_ov_cv = cv
        return x

    def a8_panel(self, w, cv, P, want, PW):
        """The Panel: the chip and the clock, the map part, SESSION | LAST MAP'S PROFIT, the tools. -> its height."""
        u = self._u
        cfg, ln = self.tracker_cfg(), self.ov_lines()
        pad = u(10)
        R = PW - pad
        hh = u(30)
        self._a8_chip(cv, P, pad, hh // 2, u(20))
        if not want["timer"]:                               # no session: ▶ START SESSION starts one
            self.tk_ov_lbls.pop("a8_chip").config(text=chip_text("idle"))
        x = self._lt_glyphs(w, cv, P, R, hh // 2)
        if want["timer"] and cfg.get("clock", True):
            self._lt_clock(cv, P, x, hh // 2)
        cv.create_line(0, hh, PW, hh, fill=P["line"], tags=("mg",))
        y = hh
        if want["timer"]:
            if ln.get("map", True) or ln.get("where", True):
                ly, vy = y + u(12), y + u(30)
                px = pad + self._a8_pin(cv, P, pad, vy - u(4)) + u(8)
                self._a8_label(cv, P, px, ly, "THIS MAP", key="a8_label")
                self._lt_text(cv, P, R, vy, "", 13, P.get("accent") or P["big"], anchor="e", bold=True,
                              key="a8_timer")
                tw = self._lt_fm(cv, P, 13, True).measure("00:00") + u(8)
                t = self._lt_text(cv, P, px, vy, "", 13, P["big"], bold=True, key="a8_place", cls=_Fit)
                t.width, t.font = R - px - tw, (P["font"], self._hf(13), "bold")
                y += u(44)
                cv.create_line(pad, y, R, y, fill=P["line"], tags=("mg",))
            ly, vy = y + u(12), y + u(28)
            colw = (PW - 2 * pad) // 2
            if ln.get("session", True):
                from .merged_page import _Time
                lab = self._a8_label(cv, P, pad, ly, "SESSION ⓘ")
                t = self._lt_text(cv, P, pad, vy, "", 11, P["big"], bold=True, key="session", cls=_Time)
                t.num, t.dim = True, (P["big"], P["muted"])
                cv.addtag_withtag("mg_a8ses", t.item)
                cv.addtag_withtag("mg_a8ses", lab.item)
                self.ov_tip(cv, "mg_a8ses", self.a8_session_tip, hand=False)
            try:
                prof = bool(self.mp_on())
            except Exception:
                prof = False
            if prof:
                lab = self._a8_label(cv, P, pad + colw, ly, "LAST MAP'S PROFIT ⓘ")
                t = self._lt_text(cv, P, pad + colw, vy, "", 11, P.get("accent") or P["big"], bold=True, key="profit")
                try:
                    self.mp_bar_bind(cv, t.item)
                    self.mp_bar_bind(cv, lab.item)
                except Exception:
                    buglog.caught()
            y += u(40)
            self.tk_ov_cv = cv
        if self.bar_buttons_on():
            cv.create_line(0, y, PW, y, fill=P["line"], tags=("mg",))
            self._lt_menus(w, cv, P, pad, y + u(14), anchor="w", right=PW - pad, step=u(22))
            y += u(28) + (getattr(self, "_mg_menu_rows", 1) - 1) * u(22)
        else:
            y += u(4)
        return y
