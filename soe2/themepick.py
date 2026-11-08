"""2.118.0 (feedback: "the theme previews should work like the overlay style previews"): Settings › Appearance ›
Theme - the themes as a list of names (Dark, Light) beside a big live preview of the app in the theme under the mouse,
with its one-line description. Hovering previews without changing anything; a click (or Enter / Space) picks it and
the whole app changes at once, as the cards did. (The first-start page keeps the small cards.)

The preview is drawn from the pack itself with the app's own parts - its title bar (themes.bar_into), the nav and its
selected-page marker (sidebar.draw_marker), a section bar, the flat buttons (themes.flat_spec), list rows, the meter -
in the pack's colours and fonts, with your Accent colour when you picked one.
GGG ToS: it only draws in the app's own window."""
import tkinter as tk

from .pickers import ListPreview

W, H = 560, 300


def _accent(t):
    """The pack's own accent (2.119.0: the Accent color choice is gone)."""
    return t.c("accent")


def draw(cv, t, w=W, h=H):
    """The app in pack `t`, at w x h: title bar, nav, a section with an item, a list and buttons."""
    from . import themes as TH
    from .sidebar import draw_marker
    with TH.raw():
        cv.delete("all")
        c, mix = t.c, TH.mix
        acc = _accent(t)
        head, body = TH.head_font(t), "Segoe UI"
        cv.create_rectangle(0, 0, w, h, fill=c("chassis"), outline=c("border"))
        # the window's title bar
        tb = 26
        fg = TH.bar_into(cv, t, "title", 1, 1, w - 1, tb)
        cv.create_text(10, tb // 2 + 1, text="StashOfExile2", anchor="w", fill=fg, font=(head, 10, "bold"))
        # the nav, with the selected page's marker
        nav = t.part("nav") or {}
        nw = 132
        nbg = c(nav.get("bg", "surface_raised"))
        cv.create_rectangle(1, tb, nw, h - 1, fill=nbg, outline="")
        if nav.get("texture", "none") not in ("none", None):
            TH.texture(cv, t, nav["texture"], 1, tb, nw, h - 1, nbg,
                       glow=c(nav["texture_color"]) if nav.get("texture_color") else None)
        cv.create_line(nw, tb, nw, h - 1, fill=c("border"))
        mk_col = c(nav["marker_color"]) if nav.get("marker_color") and nav["marker_color"] != "accent" else acc
        sel_bg = c(nav.get("sel_bg", "selection"))
        txt, sel_txt = c(nav.get("text", "text")), c(nav.get("sel_text", "text_strong"))
        y = tb + 10
        cv.create_text(12, y + 4, text="TOOLS", anchor="w", fill=c(nav.get("group", "text_muted")),
                       font=(body, 8, "bold"))
        y += 14
        for i, name in enumerate(("Price Checks", "Bulk Pricing", "Wealth", "Money Makers")):
            y0, y1 = y + i * 28, y + i * 28 + 26
            if i == 0:
                draw_marker(cv, nav.get("marker", "bar"), 6, y0, nw - 6, y1, mk_col, sel_bg, nbg)
            cv.create_text(22, (y0 + y1) // 2, text=name, anchor="w", fill=sel_txt if i == 0 else txt,
                           font=(body, 9, "bold" if i == 0 else "normal"))
        # the page: a section bar, the item's card, the meter, a list, buttons
        x0, x1 = nw + 12, w - 12
        sy = tb + 10
        sfg = TH.bar_into(cv, t, "section", x0, sy, x1, sy + 22)
        cv.create_text(x0 + 8, sy + 11, text="PRICE CHECK", anchor="w", fill=sfg, font=(head, 9, "bold"))
        cy0, cy1 = sy + 22, sy + 124
        cv.create_rectangle(x0, cy0, x1, cy1, fill=c("surface"), outline=c("border"))
        cv.create_text(x0 + 10, cy0 + 14, text="Gloom Shroud", anchor="w", fill=c("rare"), font=(head, 11, "bold"))
        cv.create_text(x0 + 10, cy0 + 32, text="Vaal Cuirass · item level 81", anchor="w", fill=c("text_muted"),
                       font=(body, 8))
        cv.create_text(x0 + 10, cy0 + 50, text="+92 to maximum Life", anchor="w", fill=c("text"), font=(body, 9))
        cv.create_text(x0 + 10, cy0 + 66, text="+38% to Cold Resistance", anchor="w", fill=c("text"), font=(body, 9))
        num = TH.head_font(t, "num")
        cv.create_text(x1 - 10, cy0 + 16, text="1.4 div", anchor="e", fill=c("money"), font=(num, 14, "bold"))
        cv.create_text(x1 - 10, cy0 + 36, text="+12% this week", anchor="e", fill=c("good"), font=(body, 8))
        cv.create_text(x1 - 10, cy0 + 50, text="3 sellers left", anchor="e", fill=c("bad"), font=(body, 8))
        ms = t.part("meter") or {}
        on, off, st = c(ms.get("on", "good")), c(ms.get("off", "surface_high")), ms.get("style", "bar")
        for i in range(10):
            mx, my = x0 + 10 + i * 10, cy1 - 14
            col = on if i < 6 else off
            if st == "runes":
                cv.create_polygon(mx + 3, my - 4, mx + 7, my, mx + 3, my + 4, mx - 1, my, fill=col, outline="")
            elif st == "orbs":
                cv.create_oval(mx, my - 4, mx + 7, my + 3, fill=col, outline="")
            elif st == "ticks":
                cv.create_line(mx + 3, my - 5, mx + 3, my + 5, fill=col, width=2)
            else:
                cv.create_rectangle(mx, my - 4, mx + 7, my + 4, fill=col, outline="")
        cv.create_text(x0 + 116, cy1 - 14, text="sure", anchor="w", fill=c("text_muted"), font=(body, 8))
        # a list: heading row, striped rows, one selected
        ly = cy1 + 10
        hs = TH.flat_spec(t, "heading")
        cv.create_rectangle(x0, ly, x1, ly + 20, fill=TH.grad_at(t.grad(hs["fill"]), .5), outline=hs["border"])
        cols = (("Seller", x0 + 10, "w"), ("Price", x1 - 120, "e"), ("Listed", x1 - 10, "e"))
        for text, x, anchor in cols:
            cv.create_text(x, ly + 10, text=text, anchor=anchor, fill=hs["text"] or c("text_muted"),
                           font=(body, 8, "bold"))
        rows = (("ExileOne", "1.3 div", "2 min"), ("Wraeclast_", "1.4 div", "9 min"), ("StashLord", "1.5 div", "1 h"))
        for i, (a, b, d) in enumerate(rows):
            r0 = ly + 20 + i * 22
            sel = i == 1
            fill = c("selection") if sel else (c("stripe") if i % 2 else c("surface"))
            cv.create_rectangle(x0, r0, x1, r0 + 22, fill=fill, outline="")
            fgr = c("selection_text") if sel else c("text")
            for text, (_t, x, anchor) in zip((a, b, d), cols):
                cv.create_text(x, r0 + 11, text=text, anchor=anchor, fill=fgr, font=(body, 9))
        cv.create_rectangle(x0, ly, x1, ly + 20 + 3 * 22, outline=c("border"))
        # buttons: the flat faces every theme uses
        by = ly + 20 + 3 * 22 + 12
        bx = x1
        for kind, label in (("primary", "Price it"), ("normal", "Search")):
            sp = TH.flat_spec(t, kind)
            if kind == "primary":
                sp = dict(sp, fill=[[0, acc], [1, acc]], border=acc)
            bw = 86
            face = TH.grad_at(t.grad(sp["fill"]), .5)
            TH.round_rect(cv, bx - bw, by, bx, by + 24, sp.get("radius") or 0, fill=face, outline=sp["border"])
            tcol = sp.get("text") or (c("chassis") if kind == "primary" and not t.light else
                                      "#ffffff" if kind == "primary" else c("text"))
            cv.create_text(bx - bw // 2, by + 12, text=label, fill=tcol, font=(body, 9, "bold" if kind == "primary"
                                                                                   else "normal"))
            bx -= bw + 8
        cv.create_text(x0, by + 12, text="Prices from the official trade site", anchor="w", fill=c("text_muted"),
                       font=(body, 8))


class ThemePicker(ListPreview):
    """The theme names (Dark, Light) and the app drawn in the one under the mouse. on_pick(theme id) on a click."""

    def __init__(self, parent, current, on_pick):
        from . import themes as TH
        packs = TH.ordered()
        self.packs = {t.id: t for t in packs}
        groups = [(title, [(t.id, t.name) for t in packs if bool(t.light) == light])
                  for title, light in (("Dark", False), ("Light", True))]
        groups = [g for g in groups if g[1]]
        super().__init__(parent, groups, current, on_pick, self._render,
                         about=lambda tid: (self.packs[tid].data.get("description") or "") if tid in self.packs else "",
                         cols=2, name_width=15, preview_width=W)

    def _render(self, host, tid):
        t = self.packs.get(tid)
        cv = getattr(self, "cv", None)
        if cv is None or not cv.winfo_exists():
            from . import themes as TH
            cv = self.cv = TH.self_painted(tk.Canvas(host, width=W, height=H, highlightthickness=0, bd=0))
            cv.pack()
        if t is not None:
            draw(cv, t)
