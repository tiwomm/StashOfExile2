"""The sidebar (2.62.0): every tool as a line of text down the left, grouped, child tools indented under their
parent with "↳", the open one marked in the theme's style; Toolkit and Settings at the bottom. Clicking a line
opens that tool as the page (one page at a time).

GGG ToS: looks only - nothing here touches the game."""
import tkinter as tk

from . import themes as TH
from .style import C

WIDE, NARROW = 212, 52                 # wide: icon + name; narrow (small app window): icons only
GROUPS = (("module", "Modules"), ("tool", "Tools"), ("utility", "In game"))


class Sidebar(tk.Canvas):
    def __init__(self, shell, parent):
        super().__init__(parent, width=WIDE, highlightthickness=0, bd=0, bg=C["panel2"])
        self.shell = shell
        self.hover, self.compact, self._rows = None, False, []
        TH.self_painted(self)
        TH.subscribe(lambda t: self.redraw(), owner=self)
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda e: self._set_hover(None))
        self.bind("<Button-1>", self._click)

    # ---- what is listed
    def items(self):
        sh = self.shell
        out = []
        for kind, label in GROUPS:
            mods = [m for m in sh.modules.values() if m.kind == kind and sh.listed(m)]
            if not mods:
                continue
            out.append({"group": label})
            for m in mods:
                out.append({"key": m.key, "mod": m})
                for c in sh.children(m.key):
                    out.append({"key": c.key, "mod": c, "child": True})
        return out

    def set_compact(self, on):
        if on != self.compact:
            self.compact = on
            self.configure(width=NARROW if on else WIDE)
            self.redraw()

    # ---- mouse
    def _hit(self, y):
        return next((k for k, y0, y1 in self._rows if y0 <= y < y1), None)

    def _motion(self, e):
        self._set_hover(self._hit(e.y))

    def _set_hover(self, k):
        if k != self.hover:
            self.hover = k
            self.configure(cursor="hand2" if k else "")
            self.redraw()
            mod = self.shell.modules.get(k)
            if mod is not None and getattr(mod, "blurb", ""):
                self.shell.app._say(f"{mod.title}: {mod.blurb}", 4)

    def _click(self, e):
        k = self._hit(e.y)
        if k == "_toolkit":
            self.shell.toggle_menu()
        elif k:
            self.shell.open(k)

    # ---- drawing (the theme's own nav style: bar, glow, pill, gem, bracket, arrow, step)
    def redraw(self):
        with TH.raw():
            self._redraw()

    def _redraw(self):
        t = TH.ST.theme
        if t is None:
            return
        self.delete("all")
        nav = t.part("nav") or {}
        w, h = max(self.winfo_width(), 2), max(self.winfo_height(), 2)
        bg = t.c(nav.get("bg", "surface_raised")) if t.id != TH.IDENTITY else C["panel2"]
        self.configure(bg=bg)
        if nav.get("texture", "none") not in ("none", None):
            TH.texture(self, t, nav["texture"], 0, 0, w, h, bg,
                       glow=t.c(nav["texture_color"]) if nav.get("texture_color") else None)
        self.create_line(w - 1, 0, w - 1, h, fill=C["line"])
        acc = t.c(nav.get("marker_color", "accent")) if nav.get("marker_color") else C["accent"]
        sel_bg = t.c(nav.get("sel_bg", "selection"))
        hov_bg = t.c(nav.get("hover_bg", "surface_high"))
        txt, sel_txt = t.c(nav.get("text", "text")), t.c(nav.get("sel_text", "text_strong"))
        grp = t.c(nav.get("group", "text_muted"))
        mk = nav.get("marker", "bar")
        rh, y = 30, 8
        self._rows = []
        active = self.shell.active
        for it in self.items() + [{"group": None}, {"key": "_toolkit", "title": "Toolkit", "icon": "◆"},
                                  {"key": "settings", "title": "Settings", "icon": "⚙"}]:
            if "group" in it:
                if it["group"] is None:                       # the bottom: Toolkit and Settings
                    y = max(y + 8, h - 2 * (rh + 2) - 12)
                    self.create_line(10, y, w - 10, y, fill=C["line"])
                    y += 8
                    continue
                if self.compact:
                    self.create_line(10, y + 6, w - 10, y + 6, fill=C["line"])
                    y += 12
                    continue
                y += 6
                self.create_text(14, y + 8, text=it["group"].upper(), anchor="w", font=("Segoe UI", 8, "bold"), fill=grp)
                y += 22
                continue
            k = it["key"]
            mod = it.get("mod")
            title = mod.title if mod is not None else it["title"]
            icon = mod.icon if mod is not None else it["icon"]
            y0, y1 = y, y + rh
            x0, x1 = (6, w - 6) if not self.compact else (4, w - 4)
            sel = k == active or (k == "_toolkit" and self.shell.menu is not None)
            if sel:
                self._marker(mk, x0, y0, x1, y1, acc, sel_bg, bg)
            elif k == self.hover:
                if mk == "pill":
                    TH.round_rect(self, x0, y0 + 1, x1, y1 - 1, 4, fill=hov_bg, outline=t.c(nav.get("hover_border", "border")))
                else:
                    self.create_rectangle(x0, y0, x1, y1, fill=hov_bg, outline="")
            cy = (y0 + y1) // 2
            fg = sel_txt if sel else txt
            if self.compact:
                self.create_text((x0 + x1) // 2, cy, text=icon, font=("Segoe UI Emoji", 12), fill=fg)
            else:
                ind = 14 if it.get("child") else 0
                if it.get("child"):
                    self.create_text(x0 + 10, cy, text="↳", anchor="w", font=("Segoe UI", 9), fill=grp)
                self.create_text(x0 + 12 + ind + (6 if mk == "gem" else 0), cy, text=icon, anchor="w",
                                 font=("Segoe UI Emoji", 12 if not it.get("child") else 10), fill=fg)
                self.create_text(x0 + 40 + ind, cy, text=title, anchor="w", fill=fg,
                                 font=("Segoe UI", 10 if not it.get("child") else 9, "bold" if sel else "normal"))
                if mod is not None and getattr(mod, "kind", "") == "utility" and not it.get("child"):
                    st = None
                    try:
                        st = mod.status() if hasattr(mod, "status") else None
                    except Exception:
                        pass
                    col = C["green"] if st is True else C["orange"] if st == "warn" else C["muted"]
                    self.create_oval(x1 - 16, cy - 4, x1 - 8, cy + 4, fill=col, outline="")
                elif mod is not None and _beta(mod):
                    self.create_text(x1 - 6, cy, text="BETA", anchor="e", font=("Segoe UI", 7, "bold"), fill=acc)
            self._rows.append((k, y0, y1))
            y = y1 + 2

    def _marker(self, mk, x0, y0, x1, y1, acc, sbg, bg):
        mix = TH.mix
        if mk == "pill":
            TH.round_rect(self, x0, y0 + 1, x1, y1 - 1, 4, fill=sbg, outline=acc)
            self.create_line(x0 + 4, y0 + 2, x1 - 4, y0 + 2, fill=mix(sbg, "#ffffff", .6))
        elif mk == "glow":
            for i in range(x1 - x0):
                self.create_line(x0 + i, y0, x0 + i, y1, fill=mix(mix(acc, sbg, .45), bg, (i / (x1 - x0)) ** .7))
            self.create_line(x0, y0, x0, y1, fill=mix(acc, "#ffffff", .3), width=2)
        elif mk == "gem":
            for i in range(x1 - x0):
                self.create_line(x0 + i, y0, x0 + i, y1, fill=mix(sbg, bg, i / (x1 - x0)))
            cy = (y0 + y1) // 2
            self.create_polygon(x0 + 6, cy - 5, x0 + 11, cy, x0 + 6, cy + 5, x0 + 1, cy, fill=acc,
                                outline=mix(acc, "#000000", .55))
        elif mk == "bracket":
            self.create_rectangle(x0, y0, x1, y1, fill=sbg, outline="")
            n = 6
            self.create_line(x0 + n, y0, x0, y0 + n, x0, y1 - n, x0 + n, y1, fill=acc, width=2)
            self.create_line(x1 - n, y0, x1, y0 + n, x1, y1 - n, x1 - n, y1, fill=acc, width=2)
        elif mk == "arrow":
            self.create_rectangle(x0, y0, x1, y1, fill=sbg, outline="")
            my = y1 - 3
            self.create_line(x0 + 6, my, x1 - 12, my, fill=mix(acc, sbg, .3))
            self.create_polygon(x1 - 12, my - 4, x1 - 3, my, x1 - 12, my + 4, fill=acc, outline="")
        elif mk == "step":
            self.create_rectangle(x0, y0, x1, y1, fill=sbg, outline="")
            self.create_polygon(x0, y0 + 2, x0 + 3, y0 + 2, x0 + 3, y0 + 6, x0 + 6, y0 + 6, x0 + 6, y1 - 6,
                                x0 + 3, y1 - 6, x0 + 3, y1 - 2, x0, y1 - 2, fill=acc, outline="")
        else:                                                  # bar
            self.create_rectangle(x0, y0, x1, y1, fill=sbg, outline="")
            for i in range(24):
                self.create_line(x0 + 3 + i, y0, x0 + 3 + i, y1, fill=mix(acc, sbg, .6 + .4 * i / 24))
            self.create_rectangle(x0, y0, x0 + 3, y1, fill=acc, outline="")


def _beta(mod):
    from .shell import is_beta
    return is_beta(mod)
