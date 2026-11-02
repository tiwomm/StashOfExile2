"""Section chrome (2.63.0): the header strip over a part of a page, and the sunken frame around a list - both drawn
from the running theme pack ("bars.section", "panels.viewport") and redrawn after a live theme swap.

GGG ToS: looks only - nothing here touches the game."""
import tkinter as tk

from . import themes as TH
from .style import C


class SectionBar(tk.Canvas):
    """A header strip: title on the left, a short note on the right (bar.note(text)), optional widgets on the right
    (bar.add_right(widget) - make them with this bar as parent)."""

    H = 28

    def __init__(self, parent, title, note=""):
        super().__init__(parent, height=self.H, highlightthickness=0, bd=0, bg=C["panel2"])
        self.title, self._note, self._right = title, note, []
        TH.self_painted(self)
        TH.subscribe(lambda t: self.redraw(), owner=self)
        self.bind("<Configure>", lambda e: self.redraw())

    def set_title(self, title):
        if title != self.title:
            self.title = title
            self.redraw()

    def note(self, text=None):
        if text is None:
            return self._note
        if text != self._note:
            self._note = text
            self.redraw()
        return text

    def add_right(self, widget):
        TH.self_painted(widget)
        self._right.append(widget)
        self.redraw()
        return widget

    def redraw(self):
        if TH.ST.theme is None:
            return
        with TH.raw():
            self._redraw()

    def _redraw(self):
        self.delete("all")
        w, h = max(self.winfo_width(), 2), self.H
        fg = TH.paint_bar(self, "section", tag="bar")
        t = TH.ST.theme
        stops = t.grad(t.part("bars", "section", "fill") or t.part("bars", "title", "fill"))
        mid = TH.grad_at(stops, .5)
        self.create_text(12, h // 2, text=self.title, anchor="w", fill=fg, font=(TH.head_font(), 11, "bold"))
        x = w - 8
        for wd in reversed(self._right):
            try:
                if wd.winfo_class() in ("Label", "Checkbutton"):
                    wd.configure(bg=mid, activebackground=mid) if wd.winfo_class() == "Checkbutton" else wd.configure(bg=mid)
            except tk.TclError:
                continue
            x -= wd.winfo_reqwidth()
            wd.place(in_=self, x=x, y=h // 2, anchor="w")
            x -= 8
        if self._note:
            self.create_text(x, h // 2, text=self._note, anchor="e", fill=C["steel"], font=("Segoe UI", 9))


class Viewport(tk.Frame):
    """A sunken frame for a list or a preview. Put children in .body."""

    def __init__(self, parent, bg_key="panel"):
        super().__init__(parent, bd=0, highlightthickness=0, bg=C[bg_key])
        self.bg_key, self._edges = bg_key, []
        self.body = tk.Frame(self, bd=0, highlightthickness=0, bg=C[bg_key])
        self.body.pack(fill="both", expand=True)
        TH.self_painted(self)
        TH.subscribe(lambda t: self.restyle(), owner=self)
        self.restyle()

    def restyle(self):
        t = TH.ST.theme
        if t is None:
            return
        with TH.raw():
            self.configure(bg=C[self.bg_key])
            for e in self._edges:
                e.destroy()
            self._edges = []
            layers = t.part("panels", "viewport", "edges") or []
            for i, (tl, br) in enumerate(layers):
                for place, role in ((dict(x=i, y=i, relwidth=1, width=-2 * i, height=1), tl),
                                    (dict(x=i, y=i, width=1, relheight=1, height=-2 * i), tl),
                                    (dict(x=i, rely=1, y=-i - 1, relwidth=1, width=-2 * i, height=1), br),
                                    (dict(relx=1, x=-i - 1, y=i, width=1, relheight=1, height=-2 * i), br)):
                    f = tk.Frame(self, bg=t.c(role), bd=0, highlightthickness=0)
                    TH.self_painted(f)
                    f.place(**place)
                    self._edges.append(f)
            self.body.pack_configure(padx=len(layers), pady=len(layers))


def section(parent, title, note="", bg_key="panel2", padx=16, pady=8, expand=False):
    """2.69.0: a part of a page the way Price checks draws them - the theme's header strip with the title, and a
    sunken frame under it. -> (outer, inner): place outer (pack / grid), put the content in inner.
    inner.section_outer / outer.section_title / outer.section_bar are set for code that needs them."""
    outer = tk.Frame(parent, bg=C["panel"], highlightthickness=1, highlightbackground=C["panel"])
    bar = SectionBar(outer, title)
    bar.pack(fill="x")
    vp = Viewport(outer, bg_key=bg_key)
    vp.pack(fill="both", expand=True)
    inner = tk.Frame(vp.body, bg=C[bg_key], padx=padx, pady=pady)
    inner.pack(fill="both", expand=True)
    if note:
        tk.Label(inner, text=note, bg=C[bg_key], fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left",
                 wraplength=600).pack(fill="x", pady=(0, 8))
    inner.section_outer, outer.section_title, outer.section_bar = outer, title, bar
    return outer, inner
