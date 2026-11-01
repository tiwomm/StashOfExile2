"""One look for every small window shown over the game (2.0 beta 13): Notes, the Session timer, and anything added
later. Same frame as the app's own windows: a thin title bar (utility colours), a 1px border, resize edges and a
lock button. Callers put their content in .body and get told when the window was moved or resized.

    w = OverlayWindow(root, "Notes", "📌", (x, y, w, h), opacity=215, locked=False,
                      on_close=..., on_lock=lambda locked: ..., on_moved=lambda x, y, w, h: ...)
    tk.Text(w.body, ...).pack(fill="both", expand=True)
"""
import os
import sys
import tkinter as tk

from .style import C
from .shell import GradientBar, UTIL_TITLE, TITLE_ON, BORDER_OFF

BAR_H = 22
EDGE = 4
OUTLINE = "#5b77ad"              # the same 1px outline as the app's windows
BODY_BG = "#0d1424"

# ---- 2.43.0 / 2.47.0: the look of the windows over the game (Overlays › Look). Four PoE2-style skins from the
# 2.43.0 mockups - the user picked C, Runeshape parchment (the default) and wanted all four to choose from - plus the
# Classic dark look of 2.42.
#   parchment  the Expedition remnant's reward book: grungy parchment (made by texture(), no image file) in a dark
#              leather binding, ink text, serif title, diamond icons
#   relic      item / relic tooltips: near-black glass, a gold title band, a thin bronze rule
#   carved     Inventory / Currency Exchange: stone panel, double bronze frame, a raised title plate
#   hud        the area info top right: almost no box, a dark band between two gold hairlines, game-orange text
LOOKS = {"parchment": "Runeshape parchment (default)", "relic": "Relic tooltip", "carved": "Carved frame",
         "hud": "Quiet HUD", "classic": "Classic dark (2.42)"}
LOOK = ["parchment"]
SERIF = "Palatino Linotype"
_P = {"title_size": 10, "align": "w", "texture": False, "on_icon": "\u25c6", "off_icon": "\u25c7", "rules": False,
      "plate": False, "frame2": None, "cell_bg": None, "cell_line": None}
PALETTES = {
    "parchment": dict(_P, leather="#2a1f16", edge="#000000", border=5, bg="#d8c49a", band="#d8c49a", head="#4a3520",
                      text="#2e2216", muted="#5d4630", line="#a88a5c", on="#1f8a1c", off="#c0261b", warn="#a86a00",
                      field="#e6d6b0", big="#2e2216", font=SERIF, texture=True, cell_bg="#ead9b2", cell_line="#a88a5c"),
    "relic": dict(_P, leather="#6e5b3a", edge="#000000", border=1, bg="#0c0a08", band="#17130e", head="#e6d39f",
                  text="#e9e2cf", muted="#a89a7c", line="#6e5b3a", on="#62c45a", off="#d24b3a", warn="#e0a352",
                  field="#14110d", big="#f2e6c4", font=SERIF, align="center", cell_bg="#0c0a08", cell_line="#2c251b"),
    "carved": dict(_P, leather="#8a7046", edge="#000000", border=2, bg="#1a1714", band="#1a1714", head="#f0dca4",
                   text="#e9e2cf", muted="#a89a7c", line="#4d3f2a", on="#62c45a", off="#d24b3a", warn="#e0a352",
                   field="#12100d", big="#f2e6c4", font=SERIF, align="center", plate=True, frame2="#4d3f2a",
                   cell_bg="#12100d", cell_line="#4f6a3a"),
    "hud": dict(_P, leather="#000000", edge="#000000", border=0, bg="#0a0907", band="#0a0907", head="#e0a352",
                text="#f3e3bd", muted="#d9c79e", line="#7a5a2e", on="#6fd36a", off="#e5604c", warn="#e0a352",
                field="#0a0907", big="#f3e3bd", font=SERIF, rules=True, on_icon="\u2713", off_icon="\u2715",
                cell_bg="#0a0907", cell_line="#0a0907"),
    "classic": dict(_P, leather=BORDER_OFF, edge=OUTLINE, border=0, bg=BODY_BG, band=BODY_BG, head="#ffe2b8",
                    text="#e8eefc", muted="#9fb0cc", line="#8a6a3a", on="#5ee08a", off="#ff5c5c", warn="#ffb347",
                    field=BODY_BG, big="#ffd9a8", font="Segoe UI", on_icon="\u25cf", off_icon="\u25cf"),
}


def pal():
    """The colours, font and shape of the windows over the game, for their content."""
    return PALETTES.get(LOOK[0], PALETTES["parchment"])


def parchment():
    return LOOK[0] == "parchment"


def skinned():
    """One of the PoE2-style looks (not Classic): content is drawn on a canvas, like the mockups."""
    return LOOK[0] in PALETTES and LOOK[0] != "classic"


_TEX = {}


def texture(root, w, h, seed=7):
    """2.47.0: a grungy parchment (the user: "too clean") - made here, no image file: the base colour, fibres and
    grain, a few stains and darker, burnt edges. A Tk PhotoImage (None without Pillow)."""
    key = (w // 16 * 16 + 16, h // 16 * 16 + 16, seed)
    if key in _TEX:
        return _TEX[key]
    try:
        import random
        from PIL import Image, ImageDraw, ImageFilter, ImageTk
    except Exception:
        return None
    W, H = key[0], key[1]
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), (216, 196, 154))
    px = img.load()
    for y in range(H):                                     # grain
        for x in range(W):
            n = rnd.randint(-10, 10)
            r, g, b = px[x, y]
            px[x, y] = (r + n, g + n, b + n - 2)
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(max(6, W * H // 6000)):                 # stains
        cx, cy, rr = rnd.randint(0, W), rnd.randint(0, H), rnd.randint(8, 40)
        d.ellipse((cx - rr, cy - rr * 0.7, cx + rr, cy + rr * 0.7), fill=(120, 86, 40, rnd.randint(10, 28)))
    for _ in range(W * H // 900):                          # fibres
        x0, y0 = rnd.randint(0, W), rnd.randint(0, H)
        d.line((x0, y0, x0 + rnd.randint(-14, 14), y0 + rnd.randint(-3, 3)), fill=(110, 80, 40, rnd.randint(14, 34)))
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    edge = Image.new("L", (W, H), 0)                       # burnt, darker edges
    de = ImageDraw.Draw(edge)
    for i in range(max(0, min(14, W // 2 - 1, H // 2 - 1))):
        de.rectangle((i, i, W - 1 - i, H - 1 - i), outline=int(150 * (1 - i / 14) ** 2))
    edge = edge.filter(ImageFilter.GaussianBlur(3))
    dark = Image.new("RGB", (W, H), (92, 62, 30))
    img = Image.composite(dark, img, edge)
    photo = ImageTk.PhotoImage(img, master=root)
    _TEX[key] = photo
    return photo


def paint_texture(canvas, seed=7):
    """Keep a canvas' background the parchment texture (redrawn when it changes size)."""
    def draw(_e=None):
        w, h = max(8, canvas.winfo_width()), max(8, canvas.winfo_height())
        img = texture(canvas, w, h, seed)
        canvas.delete("tex")
        if img is not None:
            canvas.create_image(0, 0, image=img, anchor="nw", tags="tex")
            canvas.tag_lower("tex")
    canvas.bind("<Configure>", draw, add="+")
    draw()


class CanvasText:
    """A text on a canvas that answers like a Label (config / cget of text, fg, bg) - the skinned overlays draw their
    text straight on the textured canvas, and the code that fills them still says lab.config(text=...)."""

    def __init__(self, canvas, item, bg=None):
        self.canvas, self.item, self._bg = canvas, item, bg

    def config(self, **kw):
        o = {}
        if "text" in kw:
            o["text"] = kw["text"]
        if "fg" in kw:
            o["fill"] = kw["fg"]
        if o:
            try:
                self.canvas.itemconfigure(self.item, **o)
            except tk.TclError:
                pass
        if hasattr(self, "on_change"):
            self.on_change()
    configure = config

    def cget(self, key):
        if key == "bg":
            return self._bg
        return self.canvas.itemcget(self.item, {"fg": "fill"}.get(key, key))

    def winfo_exists(self):
        try:
            return bool(self.canvas.winfo_exists())
        except tk.TclError:
            return False

# ---- over-the-game windows only show while the game is in front (2.0 beta 15)
GAME_ONLY = [True]                # Settings > Window: "only while Path of Exile 2 is in front"
GAME_TITLE = ["Path of Exile 2"]  # the Chat commands window's game title
_LIVE = []                        # windows that follow the game
_JOB = [None]
TICK_MS = 350


def _fg_hwnd():
    import ctypes
    return ctypes.windll.user32.GetForegroundWindow()


def foreground_ok():
    """May over-the-game windows show right now? Yes while Path of Exile 2 is the window in front, or one of these
    windows itself is (you clicked the note to type in it). 2.0 beta 17: not just because the app is in front - they
    popped up over the app's own windows."""
    if not GAME_ONLY[0]:
        return True
    if sys.platform != "win32":                      # 2.10.0: Hyprland can tell; anywhere else, don't block
        if sys.platform.startswith("linux"):
            from . import linsys
            if linsys.hypr_socket():
                return linsys.game_active(GAME_TITLE[0] or "Path of Exile 2") or bool(linsys.app_in_front())
        return True
    try:
        from .overlay import game_active
        if game_active(GAME_TITLE[0] or "Path of Exile 2"):
            return True
        import ctypes
        u = ctypes.windll.user32
        fg = _fg_hwnd()
        for w in _LIVE:
            if _alive(w) and (u.GetParent(w.winfo_id()) or w.winfo_id()) == fg:
                return True
        return False
    except Exception:
        return True


def _tick(root):
    _JOB[0] = None
    _LIVE[:] = [w for w in _LIVE if _alive(w)]
    if not _LIVE:
        return
    ok = foreground_ok()
    for w in _LIVE:
        w.sync(ok)
    _JOB[0] = root.after(TICK_MS, _tick, root)


def _alive(w):
    try:
        return bool(w.winfo_exists())
    except Exception:
        return False


def resync():
    """Settings changed: apply now."""
    ok = foreground_ok()
    for w in list(_LIVE):
        if _alive(w):
            w.sync(ok)


class OverlayWindow(tk.Toplevel):
    def set_opacity(self, opacity):
        """2.43.0: Settings > Appearance > Over the game: applied at once."""
        try:
            self.attributes("-alpha", max(0.15, min(1.0, int(opacity) / 255)))
        except Exception:
            pass

    def __init__(self, root, title, icon, geo, *, opacity=230, locked=False, body_bg=BODY_BG, min_size=(140, 60),
                 on_close=None, on_lock=None, on_moved=None, drag_body=False, app_colours=False, lockable=True,
                 follow_game=False, no_activate=False, resizable=True):
        """geo = (x, y, w, h); w / h None = as big as the content. app_colours: the blue title bar of the app's own
        windows (for small pop-ups of the app) instead of the utility colours (things shown over the game).
        follow_game: only visible while the game (or the window itself) is in front; show() / hide() say whether you want it.
        no_activate: clicking it never takes the keyboard away from the game (for windows you don't type in).
        resizable=False: always the size of its content (2.38.0: the Helpers bar)."""
        parch = skinned() and not app_colours             # 2.43.0 / 2.47.0: a PoE2-style skin
        P = pal()
        if parch:
            body_bg = P["bg"]
        super().__init__(root, bg=P["leather"] if parch else BORDER_OFF, highlightthickness=1,
                         highlightbackground=P["edge"] if parch else OUTLINE)
        self.parch, self.P = parch, P
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
            self.attributes("-alpha", max(0.15, min(1.0, int(opacity) / 255)))
        except Exception:
            pass
        x, y, w, h = geo
        if w is None or h is None:
            self.geometry(f"+{int(x)}+{int(y)}")
        else:
            self.geometry(f"{max(min_size[0], int(w))}x{max(min_size[1], int(h))}+{int(x)}+{int(y)}")
        self.locked, self.min_size = bool(locked), min_size
        self.on_moved, self.on_lock, self.on_close = on_moved, on_lock, on_close
        edge = 0 if self.locked else EDGE
        if parch:                                         # the binding / frame shows round the page, locked or not
            edge = max(P["border"], 0 if self.locked else 1)
        outer = self
        if parch and P.get("frame2"):                     # carved: the second, inner bronze line
            outer = tk.Frame(self, bg=P["frame2"])
            outer.pack(fill="both", expand=True, padx=edge, pady=edge)
            edge = 1
        inner = tk.Frame(outer, bg=body_bg)
        inner.pack(fill="both", expand=True, padx=edge, pady=edge)
        self.inner = inner
        if parch and P.get("rules"):                      # hud: a gold hairline above and below
            tk.Frame(inner, height=1, bg=P["line"]).pack(fill="x", side="top")
            tk.Frame(inner, height=1, bg=P["line"]).pack(fill="x", side="bottom")
        title_fg, btn_bg, btn_line, accent = (("#ffffff", "#22345a", "#5b77ad", C["accent"]) if app_colours else
                                              (P["head"], P["band"], P["band"], P["line"]) if parch else
                                              ("#ffe2b8", "#3a3020", "#6a5a3a", "#8a6a3a"))
        self._title = title
        if parch:                                         # (wide enough for its title and buttons)
            from tkinter import font as tkfont
            self._tfont = (P["font"], P["title_size"], "bold")
            need = tkfont.Font(root=root, family=P["font"], size=P["title_size"], weight="bold").measure(title) \
                + 24 + 22 * (2 if lockable else 1)
            self.bar = tk.Canvas(inner, height=BAR_H + (6 if P.get("plate") else 0), width=need, bg=P["band"],
                                 highlightthickness=0)
        else:
            self.bar = GradientBar(inner, BAR_H, TITLE_ON if app_colours else UTIL_TITLE)
        self.bar.pack(fill="x")
        self.bar.configure(cursor="" if self.locked else "fleur")
        self._btns = []
        buttons = [("×", self._close, btn_bg if parch else "#7a2a20")]
        if lockable:
            buttons.append(("🔒" if self.locked else "🔓", self._toggle_lock, btn_bg))
        if parch:
            if P.get("texture"):
                paint_texture(self.bar, seed=3)
            self._title_items = []
            self.bar_note_item = self.bar.create_text(0, BAR_H // 2, text="", anchor="e", fill=P["muted"],
                                                      font=(P["font"], 9))
            for i, (txt, cmd, _bg) in enumerate(buttons):     # drawn on the canvas: no flat box on the texture
                tag = f"btn{i}"
                it = self.bar.create_text(0, BAR_H // 2, text=txt, fill=P["muted"], font=("Segoe UI Symbol", 10, "bold"),
                                          anchor="e", tags=(tag,))
                self.bar.tag_bind(tag, "<Button-1>", lambda e, c=cmd: c())
                self.bar.tag_bind(tag, "<Enter>", lambda e: self.bar.configure(cursor="hand2"))
                self.bar.tag_bind(tag, "<Leave>", lambda e: self.bar.configure(cursor="" if self.locked else "fleur"))
                self._btns.append(it)
            self.bar.bind("<Configure>", self._paint_title, add="+")
            self._paint_title()
        else:
            self.bar.create_text(8, BAR_H // 2, text=f"{icon}  {title}", anchor="w", fill=title_fg,
                                 font=("Segoe UI", 9, "bold"))
            for txt, cmd, bg in buttons:
                b = tk.Label(self.bar, text=txt, bg=bg, fg=title_fg, font=("Segoe UI", 9, "bold"),
                             width=2, highlightthickness=1, highlightbackground=btn_line, cursor="hand2")
                b.bind("<Button-1>", lambda e, c=cmd: c())
                self._btns.append(self.bar.create_window(0, BAR_H // 2, window=b, anchor="e"))
        self.bar.bind("<Configure>", self._place_btns, add="+")
        if not (parch and P.get("plate")):
            tk.Frame(inner, height=1 if not app_colours else 2, bg=accent).pack(fill="x")     # the accent line
        self.body = tk.Frame(inner, bg=body_bg)
        self.body.pack(fill="both", expand=True)
        self._drag, self._size = {}, {}
        self.wanted, self.follow_game, self.no_activate, self._noact_done = True, follow_game, no_activate, False
        if follow_game:
            _LIVE.append(self)
            if _JOB[0] is None:
                _JOB[0] = root.after(TICK_MS, _tick, root)
        if not self.locked:
            self.draggable(self.bar)
            if drag_body:
                self.draggable(self.body)
            if resizable:
                self._edges()

    # ---- showing / hiding
    def show(self):
        self.wanted = True
        self.sync(foreground_ok() if self.follow_game else True)

    def hide(self):
        self.wanted = False
        self.withdraw()

    def sync(self, ok):
        """ok = the game (or this window) is in front."""
        try:
            mapped = self.state() != "withdrawn"
        except tk.TclError:
            return
        if self.wanted and ok and not mapped:
            self._show_quietly()
        elif mapped and not (self.wanted and ok):
            self.withdraw()

    def _show_quietly(self):
        """Show it without taking the keyboard away from whatever is in front (the game)."""
        fg = None
        if sys.platform == "win32":
            try:
                fg = _fg_hwnd()
            except Exception:
                fg = None
        self.deiconify()
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        if sys.platform != "win32":
            return
        try:
            import ctypes
            u = ctypes.windll.user32
            self.update_idletasks()
            hwnd = u.GetParent(self.winfo_id()) or self.winfo_id()
            if self.no_activate and not self._noact_done:
                u.SetWindowLongW(hwnd, -20, u.GetWindowLongW(hwnd, -20) | 0x08000000)    # WS_EX_NOACTIVATE
                self._noact_done = True
            if fg and u.GetForegroundWindow() != fg:
                u.SetForegroundWindow(fg)                     # hand the keyboard straight back
        except Exception:
            pass

    # ---- title bar buttons
    def _place_btns(self, _e=None):
        w = self.bar.winfo_width()
        step = 22 if self.parch else 24
        for n, item in enumerate(self._btns):
            self.bar.coords(item, w - 6 - n * step, self._bar_mid() if self.parch else BAR_H // 2)
        if self.parch:
            self.bar.coords(self.bar_note_item, w - 10 - len(self._btns) * step, self._bar_mid())

    def _bar_mid(self):
        return (BAR_H + (6 if self.P.get("plate") else 0)) // 2

    def _paint_title(self, _e=None):
        """The title as the skin draws it: left (parchment, hud), centred on a gold band (relic) or on a raised
        plate (carved), with a small diamond."""
        P, c = self.P, self.bar
        w = max(c.winfo_width(), int(c.cget("width")))
        mid = self._bar_mid()
        c.delete("title")
        if P.get("plate"):
            from tkinter import font as tkfont
            tw = tkfont.Font(root=c, family=P["font"], size=P["title_size"], weight="bold").measure(self._title)
            x0 = max(4, (w - tw) // 2 - 16)
            c.create_rectangle(x0, 2, x0 + tw + 32, mid * 2 - 2, fill="#2a2219", outline="#b08e56", tags="title")
            c.create_text(x0 + 16 + tw // 2, mid, text=self._title, fill=P["head"], font=self._tfont, tags="title")
        elif P["align"] == "center":
            c.create_polygon(10, mid, 14, mid - 4, 18, mid, 14, mid + 4, fill="#a8874e", tags="title")
            c.create_text(w // 2, mid, text=self._title.upper(), fill=P["head"], font=self._tfont, tags="title")
        else:
            txt = self._title.upper() if P.get("rules") else self._title
            c.create_text(10, mid, text=txt, anchor="w", fill=P["head"], font=self._tfont, tags="title")
            if not P.get("rules"):
                c.create_line(8, mid * 2 - 1, w - 8, mid * 2 - 1, fill=P["line"], tags="title")
        self._place_btns()

    def bar_note(self, text):
        """Small text on the title bar, left of its buttons (the Session timer's clock). -> False when it doesn't fit
        between the title and the buttons (2.50.0: it ran into "Session" on a narrow timer) - nothing is shown then."""
        if not self.parch:
            return False
        from tkinter import font as tkfont
        try:
            w = max(self.bar.winfo_width(), int(self.bar.cget("width")))
            title_end = 10 + tkfont.Font(root=self.bar, family=self.P["font"], size=self.P["title_size"],
                                         weight="bold").measure(self._title)
            need = tkfont.Font(root=self.bar, family=self.P["font"], size=9).measure(text)
            right = w - 10 - len(self._btns) * 22
        except tk.TclError:
            return False
        fits = not text or right - need >= title_end + 12
        self.bar.itemconfigure(self.bar_note_item, text=text if fits else "")
        return fits

    def canvas_body(self):
        """A canvas filling the body, with the skin's background (the parchment texture): draw text straight on it."""
        cv = tk.Canvas(self.body, bg=self.P["bg"], highlightthickness=0)
        cv.pack(fill="both", expand=True)
        if self.P.get("texture"):
            paint_texture(cv, seed=11)
        return cv

    def _close(self):
        if self.on_close:
            self.on_close()
        else:
            self.destroy()

    def _toggle_lock(self):
        if self.on_lock:
            self.on_lock(not self.locked)

    # ---- moving
    def draggable(self, widget):
        """Let this widget (and nothing else in the content) move the window: e.g. a label in the body."""
        widget.bind("<ButtonPress-1>", self._press, add="+")
        widget.bind("<B1-Motion>", self._move, add="+")
        widget.bind("<ButtonRelease-1>", self._moved, add="+")

    def _press(self, e):
        self._drag = {"x": e.x_root - self.winfo_x(), "y": e.y_root - self.winfo_y()}

    def _move(self, e):
        if self._drag:
            self.geometry(f"+{e.x_root - self._drag['x']}+{e.y_root - self._drag['y']}")

    def _moved(self, _e=None):
        self._drag = {}
        self.report()

    def report(self):
        if self.on_moved and self.winfo_ismapped() and self.winfo_width() > 1:
            self.on_moved(self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height())

    # ---- resizing from every edge and corner
    def _edges(self):
        k = 14
        for sd, cur, kw in (("n", "sb_v_double_arrow", dict(x=0, y=0, relwidth=1, height=EDGE)),
                            ("s", "sb_v_double_arrow", dict(x=0, rely=1, y=-EDGE, relwidth=1, height=EDGE)),
                            ("w", "sb_h_double_arrow", dict(x=0, y=0, width=EDGE, relheight=1)),
                            ("e", "sb_h_double_arrow", dict(relx=1, x=-EDGE, y=0, width=EDGE, relheight=1)),
                            ("nw", "top_left_corner", dict(x=0, y=0, width=k, height=EDGE)),
                            ("nw", "top_left_corner", dict(x=0, y=0, width=EDGE, height=k)),
                            ("ne", "top_right_corner", dict(relx=1, x=-k, y=0, width=k, height=EDGE)),
                            ("ne", "top_right_corner", dict(relx=1, x=-EDGE, y=0, width=EDGE, height=k)),
                            ("sw", "bottom_left_corner", dict(x=0, rely=1, y=-EDGE, width=k, height=EDGE)),
                            ("sw", "bottom_left_corner", dict(x=0, rely=1, y=-k, width=EDGE, height=k)),
                            ("se", "bottom_right_corner", dict(relx=1, x=-k, rely=1, y=-EDGE, width=k, height=EDGE)),
                            ("se", "bottom_right_corner", dict(relx=1, x=-EDGE, rely=1, y=-k, width=EDGE, height=k))):
            h = tk.Frame(self, bg=pal()["leather"] if self.parch else BORDER_OFF, cursor=cur)
            h.place(**kw)
            self.resizer(h, sd)

    def resizer(self, widget, side):
        widget.bind("<ButtonPress-1>", lambda e: self._size.update(
            x0=e.x_root, y0=e.y_root, g=(self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height()),
            sd=side))
        widget.bind("<B1-Motion>", self._resize)
        widget.bind("<ButtonRelease-1>", self._resized)

    def _resize(self, e):
        if "g" not in self._size:
            return
        x, y, ww, hh = self._size["g"]
        mw, mh = self.min_size
        dx, dy, sd = e.x_root - self._size["x0"], e.y_root - self._size["y0"], self._size["sd"]
        if "e" in sd:
            ww = max(mw, ww + dx)
        if "s" in sd:
            hh = max(mh, hh + dy)
        if "w" in sd:
            nw = max(mw, ww - dx)
            x, ww = x + ww - nw, nw
        if "n" in sd:
            nh = max(mh, hh - dy)
            y, hh = y + hh - nh, nh
        self.geometry(f"{ww}x{hh}+{x}+{y}")

    def _resized(self, _e=None):
        self._size.clear()
        self.report()
