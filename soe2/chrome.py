"""Section chrome (2.63.0): the header strip over a part of a page, and the sunken frame around a list - both drawn
from the running theme pack ("bars.section", "panels.viewport") and redrawn after a live theme swap.

GGG ToS: looks only - nothing here touches the game."""
import tkinter as tk

from . import themes as TH
from .style import C


class BarNote:
    """2.114.0: ns.info.config(text=...) -> the section strip's note (the counts used to sit on their own line)."""

    def __init__(self, bar):
        self.bar = bar

    def config(self, text=""):
        self.bar.note(text)

    configure = config

    def cget(self, _opt="text"):
        return self.bar.note()


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


def section(parent, title, note="", bg_key="panel2", padx=16, pady=8, expand=False, wrap=False):
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
    short, more = split_note(note)
    if note:
        # 2.120.0 (UX pass 2: walls of text): one short line; the rest of the note in the ⓘ you point at
        nl = tk.Label(inner, text=short + ("  ⓘ" if more else ""), bg=C[bg_key], fg=C["muted"], font=("Segoe UI", 9),
                      anchor="w", justify="left", wraplength=600, cursor="question_arrow" if more else "")
        nl.pack(fill="x", pady=(0, 8))
        if more:
            from .style import Tooltip
            Tooltip(nl, note)
        if wrap:                                         # 2.70.0: the note wraps to the section's width (a fixed-size
            def rewrap(e):                               # window only - damped, so it can't feed back on itself)
                want = min(600, e.width - 4)
                if e.width > 40 and abs(int(nl.cget("wraplength")) - want) > 24:
                    nl.config(wraplength=want)
            nl.bind("<Configure>", rewrap)
    inner.section_outer, outer.section_title, outer.section_bar = outer, title, bar
    outer.section_note = note                            # (Settings search finds the words in the ⓘ too)
    return outer, inner


def split_note(note):
    """2.120.0: a section's note -> (its first sentence, the rest or ""). A note of one sentence stays whole."""
    note = (note or "").strip()
    i = 0
    while True:
        i = note.find(". ", i)
        if i < 0:
            return note, ""
        if i >= 3 and note[i - 3:i] in ("e.g", "i.e") or note[i - 1:i].isupper() and (i < 2 or note[i - 2] in " ("):
            i += 2                                       # (e.g. / an initial - not the end of a sentence)
            continue
        return note[:i + 1], note[i + 2:].strip()


class Notice(tk.Frame):
    """2.74.5 (feedback: beta notices "should be able to be closed off of the screen"): a one-line notice with a small
    × at the right. Closed once, it stays closed (SETTINGS["notices_closed"][key]). show(**pack) packs it unless
    it was closed; the owner packs it with show() wherever it used to pack the label."""

    def __init__(self, parent, key, text, kind="beta"):
        from .config import SETTINGS
        bg, fg, edge = {"beta": (C["warn_bg"], "#ffcf40", C["accent"])}.get(kind, (C["panel2"], C["muted"], C["line"]))
        super().__init__(parent, bg=bg, highlightthickness=1, highlightbackground=edge)
        self.key, self._S = key, SETTINGS
        self.label = tk.Label(self, text=text, bg=bg, fg=fg, anchor="w", justify="left", padx=8, pady=2,
                              font=("Segoe UI", 9))
        self.label.pack(side="left", fill="x", expand=True)
        self.label.bind("<Configure>", lambda e: self.label.config(wraplength=max(200, e.width - 16)))
        self.x = tk.Label(self, text="✕", bg=bg, fg=fg, cursor="hand2", padx=8, font=("Segoe UI", 9, "bold"))
        self.x.pack(side="right", anchor="n")
        self.x.bind("<Button-1>", lambda e: self.close())

    def closed(self):
        return bool((self._S.get("notices_closed") or {}).get(self.key))

    def show(self, **pack):
        if self.closed():
            self.pack_forget()
            return False
        self.pack(**pack)
        return True

    def close(self):
        from .config import save_json
        self._S.setdefault("notices_closed", {})[self.key] = True
        save_json("settings.json", self._S)
        self.pack_forget()


class EmptyState(tk.Frame):
    """2.120.0 (UX pass 2: empty pages looked broken - grey text far down the page): one look for "nothing here yet"
    everywhere - an icon, what it is (one bold line), what to do (a muted line or two) and at most one button.
    set_text("Title\\nwhat to do") changes the words; place / place_forget as any widget."""

    def __init__(self, parent, icon="", text="", button=None, bg_key="panel", wrap=340):
        from tkinter import ttk
        bg = C[bg_key]
        super().__init__(parent, bg=bg, padx=24, pady=16, highlightthickness=1, highlightbackground=C["line"])
        if icon:
            tk.Label(self, text=icon, bg=bg, fg=C["muted"], font=("Segoe UI Symbol", 20)).pack()
        self.title_lbl = tk.Label(self, text="", bg=bg, fg=C["text"], font=("Segoe UI", 12, "bold"), justify="center",
                                  wraplength=wrap)
        self.title_lbl.pack(pady=(4, 2))
        self.body_lbl = tk.Label(self, text="", bg=bg, fg=C["muted"], font=("Segoe UI", 9), justify="center",
                                 wraplength=wrap)
        self.body_lbl.pack()
        self.btn = None
        if button:
            self.btn = ttk.Button(self, text=button[0], command=button[1])
            self.btn.pack(pady=(12, 0))
        self.set_text(text)

    def set_text(self, text):
        head, _, rest = str(text or "").partition("\n")
        self.title_lbl.config(text=head.strip())
        rest = " ".join(rest.split())
        self.body_lbl.config(text=rest)
        if rest and not self.body_lbl.winfo_manager():
            self.body_lbl.pack(after=self.title_lbl)
        elif not rest and self.body_lbl.winfo_manager():
            self.body_lbl.pack_forget()

    def place(self, cnf=None, **kw):
        """Placed over its parent's other children (a list beside it was drawn later - and covered it)."""
        super().place(cnf or {}, **kw)
        self.lift()
    place_configure = place

    def config(self, cnf=None, **kw):
        """text= and wraplength= go to the words (so it stands in for a plain Label); the rest to the frame."""
        if "text" in kw:
            self.set_text(kw.pop("text"))
        if "wraplength" in kw:
            wl = kw.pop("wraplength")
            self.title_lbl.config(wraplength=wl)
            self.body_lbl.config(wraplength=wl)
        if cnf or kw:
            return super().config(cnf, **kw)
        return None
    configure = config

    def cget(self, key):
        if key == "text":
            return (self.title_lbl.cget("text") + ("\n" + self.body_lbl.cget("text")
                                                   if self.body_lbl.cget("text") else ""))
        return super().cget(key)
