"""Colors, fonts and widget styles.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import sys
import re
import tkinter as tk
from tkinter import ttk

from . import buglog


# ------------------------------------------------------------------ look and feel
C = {   # Xfire-style steel blue and navy, with orange for actions and gold for money (a nod to the game's UI)
    "bg": "#090e17", "panel": "#0e1522", "panel2": "#131c2e", "line": "#2b3d5f", "gold_dim": "#3d5582",
    "steel": "#8fa3c7", "text": "#dbe4f2", "muted": "#7d8da8", "accent": "#ffa63d", "good": "#ffd25a",
    "green": "#5fd38a", "red": "#ff6b5e", "blue": "#6aa6ff", "purple": "#b794f6", "orange": "#ff9d3a",
    "rare": "#ffff77", "magic": "#8f9bff", "sel": "#1b4a96", "odd": "#0b111c", "stripe": "#16213a", "key": "#26354f",
    "warn_bg": "#2a2110", "bad_bg": "#34171a", "ok_bg": "#10281c",
}

# 2.97.2 (feedback: visual hierarchy, as the game and the trade site show them): a mod's color says where it comes from.
MOD_COL = {"explicit": "#8f9bff", "rune": "#9fd8ff", "implicit": "#9fd8ff", "enchant": "#b8daf2",
           "fractured": "#d9b871", "desecrated": "#a8d65c", "pseudo": "#e07ce0"}
_BASE = dict(C)                       # (as shipped - tools/check_contrast.py starts each theme from it)


# ------------------------------------------------------------------ design tokens (2.34.0, Polish 1)
# Every new widget uses these. tools/check_tokens.py (CI + test) keeps the code on them.
SPACE = (4, 8, 12, 16, 24)            # padding / gaps; 0-2 are allowed too, for hairlines and joined edges
XS, S_, M, L, XL = SPACE
SMALL, BODY, HEAD, TITLE = 9, 10, 12, 16     # the four text sizes: notes / chips, normal, section heads, window titles
DISPLAY = (18, 20, 22, 28)            # not text: icon glyphs and the big numbers (timer, totals)
ROLE = {                              # color roles -> which C color plays them
    "surface": "bg", "surface_raised": "panel", "surface_high": "panel2", "border": "line",
    "text": "text", "text_muted": "muted", "primary": "accent", "money": "good",
    "success": "green", "danger": "red", "info": "blue", "selected": "sel",
}


def role(name):
    """The color for a role (follows the theme and accent)."""
    return C[ROLE[name]]


FONT_TITLE = "Palatino Linotype"      # a serif close to the game's Fontin; falls back automatically if missing


FLAG_COLORS = {"crafted": C["blue"], "desecrated": C["purple"], "fractured": C["orange"], "essence": C["green"]}


MONO = "Consolas"


def _rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    """Color between a and b ('#rrggbb'), t from 0 (a) to 1 (b)."""
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * max(0, min(1, t))) for x, y in zip(ra, rb))


def contrast(a, b):
    """WCAG contrast ratio of two '#rrggbb' colors (1 to 21)."""
    def lum(c):
        r, g, b_ = (v / 255 for v in _rgb(c))
        f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b_)
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def text_on(bg, light="#fff7ea", dark="#1a1206"):
    """2.34.0: light or dark text, whichever reads better on bg (WCAG AA)."""
    return light if contrast(light, bg) >= contrast(dark, bg) else dark


def hotkey_blocked(state, platform=None):
    """True when Ctrl or Alt is held. On Windows bit 0x8 is NUM LOCK, not Alt (Alt is 0x20000): treating it as Alt made every
    shortcut key dead whenever Num Lock was on. On Linux/Mac bit 0x8 is Alt."""
    win = (platform or sys.platform) == "win32"
    return bool(state & 0x4 or state & (0x20000 if win else 0x8))


class Plate(tk.Canvas):
    """A glossy steel bar (like Xfire's window frame): a gradient with a bright top edge and a darker lower half.
    Things are drawn on it with create_text / create_window, so they sit on the gradient without a box around them."""

    def __init__(self, master, height, top="#3f64a0", mid="#2a4a7c", low="#1c3360", bottom="#13233f", edge="#86a9de", **kw):
        super().__init__(master, height=height, highlightthickness=0, bd=0, bg=bottom, **kw)
        self.colors, self.on_resize = (top, mid, low, bottom, edge), None
        self.bind("<Configure>", self._redraw)

    def _redraw(self, e=None):
        w, h = self.winfo_width(), int(float(self.cget("height")))
        top, mid, low, bottom, edge = self.colors
        self.delete("plate")
        half = h // 2
        for y in range(h):
            col = mix(top, mid, y / max(1, half)) if y < half else mix(low, bottom, (y - half) / max(1, h - half))
            self.create_line(0, y, w, y, fill=col, tags="plate")
        self.create_line(0, 0, w, 0, fill=edge, tags="plate")                      # bright top edge
        self.create_line(0, h - 1, w, h - 1, fill="#070b13", tags="plate")         # dark bottom edge
        self.tag_lower("plate")
        if self.on_resize:
            self.on_resize(w, h)


_SWITCH = {}


_MONO = {}


def _mono_font(size):
    """A bold monospace font for ON / OFF (Consolas on Windows, DejaVu Sans Mono on Linux), else Pillow's own."""
    if size in _MONO:
        return _MONO[size]
    from PIL import ImageFont
    f = None
    for name in ("consolab.ttf", "consola.ttf", "DejaVuSansMono-Bold.ttf", "LiberationMono-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"):
        try:
            f = ImageFont.truetype(name, size)
            break
        except Exception:
            continue
    if f is None:
        try:
            f = ImageFont.load_default(size=size)
        except Exception:
            f = ImageFont.load_default()
    _MONO[size] = f
    return f


def _switch_img(root, on, hover=False, disabled=False, w=68, h=24, gap=8):
    """P2.5 (2.107.0, picked: B - segmented): one picture of the switch - a 68 x 24 box split in two, ON | OFF; the
    chosen half is lit (ON: the accent; OFF: a raised face). Straight edges, drawn 1:1 so they stay crisp; the
    words in a monospace font. Pillow; without it a plain Tk drawing."""
    acc, sunk = C["accent"], C.get("odd") or C["panel2"]
    edge = mix(C["line"], C["text"], 0.18) if not hover or disabled else acc
    off_face = mix(sunk, C["text"], 0.28)
    on_text = text_on(acc)
    words = (("ON", acc if on else sunk, on_text if on else C["muted"]),
             ("OFF", sunk if on else off_face, C["muted"] if on else C["text"]))
    alpha = 110 if disabled else 255
    try:
        from PIL import Image, ImageDraw, ImageTk

        def rgba(c):
            c = c.lstrip("#")
            return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)
        im = Image.new("RGBA", (w + gap, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        half = w // 2
        f = _mono_font(10)
        for i, (word, bg, fg) in enumerate(words):
            x0 = i * half
            d.rectangle((x0, 0, x0 + half - (0 if i else 1), h - 1), fill=rgba(bg))
            try:
                l, t_, r, b = d.textbbox((0, 0), word, font=f)
                tw, th = r - l, b - t_
                d.text((x0 + (half - tw) // 2 - l, (h - th) // 2 - t_), word, font=f, fill=rgba(fg))
            except Exception:
                d.text((x0 + 6, 6), word, fill=rgba(fg))
        d.rectangle((0, 0, w - 1, h - 1), outline=rgba(edge))
        return ImageTk.PhotoImage(im, master=root)
    except Exception:
        img = tk.PhotoImage(master=root, width=w + gap, height=h)
        img.put(words[0][1], to=(0, 0, w // 2, h))
        img.put(words[1][1], to=(w // 2, 0, w, h))
        return img


def switches(root, s):
    """2.49.0 (feedback: "anywhere there's a checkbox... a modern slider in its place"): every ttk.Checkbutton
    (TCheckbutton and its Bar. / Mod. styles) shows a switch instead of a tick box. Same widgets, same variables."""
    name = "Switch2.indicator.%s" % (C["accent"] + C["line"] + C["text"] + C["panel2"]).replace("#", "")
    if (id(root), name) in _SWITCH:           # 2.62.0: this look's switch exists - keep ITS pictures (making new
        imgs = None                           # ones here freed the old ones: switches went blank after a swap back)
    else:
        imgs = {(on, hv, ds): _switch_img(root, on, hv, ds) for on in (0, 1) for hv in (0, 1) for ds in (0, 1)}
        _SWITCH[(id(root), name)] = imgs      # (kept, or Tk drops the pictures)
    try:
        if imgs is None:
            raise tk.TclError("exists")
        s.element_create(name, "image", imgs[(0, 0, 0)],
                         ("disabled", "selected", imgs[(1, 0, 1)]), ("disabled", imgs[(0, 0, 1)]),
                         ("active", "selected", imgs[(1, 1, 0)]), ("selected", imgs[(1, 0, 0)]),
                         ("active", imgs[(0, 1, 0)]), sticky="w")
    except tk.TclError:
        pass                                  # (already made for this look - 2.60.0: still lay it out again)
    layout = [("Checkbutton.padding", {"sticky": "nswe", "children": [
        (name, {"side": "left", "sticky": ""}),
        ("Checkbutton.focus", {"side": "left", "sticky": "w", "children": [
            ("Checkbutton.label", {"sticky": "nswe"})]})]})]
    for name in ("TCheckbutton", "Bar.TCheckbutton", "Mod.TCheckbutton", "Card.TCheckbutton"):
        s.layout(name, layout)
        s.configure(name, padding=(0, 2))


# ---------------------------------------------------------------- 2.98.0: responsive (decided 2026-11-05: everything
# drawn to a width redraws when the window changes size - the default for the whole app)
def _fills_x(w):
    """Does this widget get the width its parent gives it (pack fill x / both, grid sticky e+w, place relwidth)?"""
    try:
        mgr = w.winfo_manager()
        if mgr == "pack":
            return w.pack_info().get("fill") in ("x", "both")
        if mgr == "grid":
            st = str(w.grid_info().get("sticky", ""))
            return "e" in st and "w" in st
        if mgr == "place":
            return bool(w.place_info().get("relwidth"))
    except Exception:
        buglog.caught()
    return False


def _rewrap(e):
    """A wrapped label that fills its row re-wraps to the width it has (was a fixed wraplength, cut off or
    leaving a gap when the window changed size). Labels with their own <Configure> rule keep it."""
    w = e.widget
    try:
        wl = int(float(str(w.cget("wraplength")) or 0))
    except Exception:
        return
    if wl <= 0 or w.bind("<Configure>") or not _fills_x(w):
        return
    try:
        pad = int(float(str(w.cget("padx")) or 0)) * 2
    except Exception:
        pad = 0
    new = max(120, e.width - pad - 4)
    squeezed = e.width < w.winfo_reqwidth() - 1          # its parent gives it less than it asks for
    if (new > wl + 6) or (squeezed and new < wl - 6):     # (a window that sizes to its text never shrinks it)
        try:
            w.configure(wraplength=new)
        except Exception:
            buglog.caught()


def center_over(win, parent):
    """2.98.3: put a dialog in the middle of `parent` (the app), kept on the monitor the app is on - never pushed to
    the main monitor (feedback: Privacy & community's questions opened on the other screen)."""
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    try:
        px, py, pw, ph = parent.winfo_rootx(), parent.winfo_rooty(), parent.winfo_width(), parent.winfo_height()
    except tk.TclError:
        px, py, pw, ph = 0, 0, win.winfo_screenwidth(), win.winfo_screenheight()
    cx, cy = px + pw // 2, py + ph // 2
    l, t, r, b = monitor_rect(parent, cx, cy)
    x = max(l, min(cx - w // 2, r - w))
    y = max(t, min(cy - h // 2, b - h))
    win.geometry(f"+{x}+{y}")
    return x, y


def over_app(win, parent):
    """2.114.3 (feedback: the Scan stash check window came up on the wrong screen - "it should always appear over the
    app"): center a window over `parent` (the app window in front) on its monitor once its content is built."""
    def go():
        try:
            if win.winfo_exists():
                center_over(win, parent)
        except tk.TclError:
            pass
    win.after_idle(go)
    return win


def _place_dialog(w, parent=None):
    """tkinter.simpledialog's own placement kept dialogs inside the MAIN monitor (it clamps to winfo_vroot*, which
    on Windows is the main monitor) - so on two screens they opened on the other one. Over the app instead."""
    w.wm_withdraw()
    w.update_idletasks()
    par = parent if parent is not None and parent.winfo_ismapped() else w._root()
    center_over(w, par)
    w.wm_deiconify()


LOOP_LIMIT = 150                  # one widget resized this many times within a second = stuck in a layout loop
_LW = {"t": 0.0, "n": {}, "told": False, "size": {}}


def _layout_watch(e):
    """2.117.1: a widget resized LOOP_LIMIT times within a second is stuck laying itself out again and again (two
    parts that each resize when the other does - how a theme's font sizes can freeze the app). The first one is
    written to the app's log once a run: the widget's place in the window and its kind - no text from it."""
    if _LW["told"]:
        return
    try:
        import time as _t
        now = _t.monotonic()
        if now - _LW["t"] > 1.0:
            _LW["t"], _LW["n"] = now, {}
        k = str(e.widget)
        size = (e.width, e.height)                   # 2.124.1: a size change only - dragging a window moves it on
        if _LW["size"].get(k) == size:               # every mouse step, and that isn't a loop
            return
        _LW["size"][k] = size
        n = _LW["n"][k] = _LW["n"].get(k, 0) + 1
        if n < LOOP_LIMIT:
            return
        _LW["told"] = True
        kinds, w = [], e.widget
        while isinstance(w, tk.Misc) and len(kinds) < 8:
            try:
                kinds.append(w.winfo_class())
            except tk.TclError:
                break
            w = w.master
        buglog.record("freeze", "layout loop: a part of a window keeps resizing",
                      detail=f"{k}\n  kinds: {' < '.join(kinds)}\n  size now: {e.width}x{e.height}\n"
                             f"  theme: {getattr(getattr(_themes.ST, 'theme', None), 'id', '?')}")
    except Exception:
        buglog.caught()


def responsive(root):
    """Once, at start: every wrapped Label / ttk Label in the app re-wraps to its width (see _rewrap); 2.98.3: the
    simple question dialogs (askstring / askinteger) open over the app, on its monitor. 2.117.1: a layout loop is
    logged (_layout_watch)."""
    for cls in ("Label", "TLabel"):
        root.bind_class(cls, "<Configure>", _rewrap, add="+")
    root.bind_all("<Configure>", _layout_watch, add="+")
    try:
        import tkinter.simpledialog as _sd
        _sd._place_window = _place_dialog
    except Exception:
        buglog.caught()


def fit(widget, fn, min_delta=12, delay=150):
    """Call fn() again (debounced) whenever widget's width changes by min_delta or more - for anything drawn to a
    width (a canvas card, a chart, a list of cards). The first size it gets doesn't count (it was drawn for it)."""
    st = {"w": 0, "after": None}

    def cfg(e):
        if abs(e.width - st["w"]) < min_delta:
            return
        first = not st["w"]
        st["w"] = e.width
        if first:
            return
        if st["after"] is not None:
            try:
                widget.after_cancel(st["after"])
            except Exception:
                buglog.caught()

        def go():
            st["after"] = None
            try:
                fn()
            except Exception:
                buglog.caught()
        st["after"] = widget.after(delay, go)
    widget.bind("<Configure>", cfg, add="+")
    return st


def _pads(v):
    """pack's padx -> (left, right). 2.103.2: Tk hands a pair back as a tuple, (12, 0) - it was read as no padding,
    so every row made with flowify lost its gaps (Clear filters touched Order added)."""
    if isinstance(v, (tuple, list)):
        parts = [int(float(str(x))) for x in v]
    else:
        parts = [int(float(x)) for x in re.findall(r"-?\d+(?:\.\d+)?", str(v))]
    return (parts[0], parts[-1]) if parts else (0, 0)


def flowify(row, vgap=6):
    """2.98.0: turn a row of side-by-side widgets (pack side=left / right) into one that wraps when the window is
    too narrow - each child keeps its order, padding, right-alignment and stretch (expand=True takes the rest of
    its line). Call it once, after the row is built. Children added later are packed as usual (not wrapped)."""
    kids = []
    for w in row.pack_slaves():
        info = w.pack_info()
        l, r = _pads(info.get("padx", 0))
        kids.append({"w": w, "right": info.get("side") == "right", "l": l, "r": r, "hidden": False,
                     "grow": bool(int(info.get("expand", 0) or 0)) and info.get("fill") in ("x", "both")})
    if not kids:
        return row
    try:
        row.pack_propagate(False)
    except tk.TclError:
        pass
    lefts = [k for k in kids if not k["right"]]
    rights = list(reversed([k for k in kids if k["right"]]))      # (pack draws right-side ones outside in)
    for k in kids:
        k["w"].pack_forget()
    state = {"w": 0, "busy": False}

    def width(k):
        return k["l"] + k["w"].winfo_reqwidth() + k["r"]

    def layout(_e=None):
        if state["busy"]:
            return
        state["busy"] = True
        try:
            try:
                px = int(float(str(row.cget("padx") or 0)))
                py = int(float(str(row.cget("pady") or 0)))
            except Exception:
                px = py = 0
            W = row.winfo_width() - 2 * px
            if W <= 1 - 2 * px:
                W = sum(width(k) for k in kids)
            lines, cur, x = [], [], 0
            for k in kids:
                if k["hidden"]:
                    k["w"].place_forget()
            seq = [k for k in lefts + rights if not k["hidden"]]
            rw = sum(width(k) for k in rights if not k["hidden"])
            for k in seq:
                kw = width(k)
                room = W - (rw if (not lines and k in lefts) else 0)
                if cur and x + kw > room and not (k in rights and not lines and x + rw <= W):
                    lines.append(cur)
                    cur, x = [], 0
                cur.append(k)
                x += kw
            if cur:
                lines.append(cur)
            y = 0
            for li, line in enumerate(lines):
                h = max(k["w"].winfo_reqheight() for k in line)
                ls = [k for k in line if k in lefts]
                rs = [k for k in line if k in rights]
                used = sum(width(k) for k in line)
                grow = [k for k in ls if k["grow"]]
                extra = max(0, W - used) // len(grow) if grow else 0
                x = 0
                for k in ls:
                    ww = k["w"].winfo_reqwidth() + (extra if k in grow else 0)
                    k["w"].place(x=px + x + k["l"], y=py + y + (h - k["w"].winfo_reqheight()) // 2, width=ww)
                    x += k["l"] + ww + k["r"]
                rx = max(x, W - sum(width(k) for k in rs))      # right-aligned, in their on-screen order
                for k in rs:
                    ww = k["w"].winfo_reqwidth()
                    k["w"].place(x=px + rx + k["l"], y=py + y + (h - k["w"].winfo_reqheight()) // 2, width=ww)
                    rx += k["l"] + ww + k["r"]
                y += h + (vgap if li < len(lines) - 1 else 0)
            if int(row.cget("height") or 0) != y + 2 * py:
                row.configure(height=y + 2 * py)
        finally:
            state["busy"] = False

    def cfg(e):
        if e.widget is row and e.width != state["w"]:
            state["w"] = e.width
            layout()
    row.bind("<Configure>", cfg, add="+")
    for k in kids:
        k["w"].bind("<Configure>", lambda e: row.after_idle(layout), add="+")
    row.after_idle(layout)
    row._flow_layout = layout
    row._flow_kids = kids
    row._flow_lefts = lefts
    return row


def flow_add(row, w, padx=(0, 0), shown=True):
    """Add a widget to a flowify'd row, after its other left-side widgets (e.g. one that shows only sometimes)."""
    l, r = (padx, padx) if isinstance(padx, int) else padx
    k = {"w": w, "right": False, "l": l, "r": r, "hidden": not shown, "grow": False}
    row._flow_kids.append(k)
    row._flow_lefts.append(k)
    w.bind("<Configure>", lambda e: row.after_idle(row._flow_layout), add="+")
    row.after_idle(row._flow_layout)
    return w


def flow_show(row, w, on):
    """Show / hide one widget of a flowify'd row (instead of pack / pack_forget)."""
    for k in getattr(row, "_flow_kids", ()):
        if k["w"] is w:
            k["hidden"] = not on
    lay = getattr(row, "_flow_layout", None)
    if lay is not None:
        lay()


def _combo_on_top():
    """2.112.0: every dropdown's list opens above "always on top" windows (Quick settings over the game was one):
    without it the list opened behind the box and the click picked an item blind. Wraps ttk.Combobox once."""
    if getattr(ttk.Combobox, "_soe2_top", False):
        return
    orig = ttk.Combobox.__init__

    oconf = ttk.Combobox.configure

    def configure(self, cnf=None, **kw):
        if isinstance(cnf, dict) and "postcommand" in cnf:
            cnf = dict(cnf)
            kw["postcommand"] = cnf.pop("postcommand")
        if "postcommand" in kw:                       # the page's own list refresh runs after ours
            self._soe2_user = kw.pop("postcommand")
            kw["postcommand"] = self._soe2_post
        return oconf(self, cnf, **kw)

    def _post(self):
        try:
            pd = self.tk.call("ttk::combobox::PopdownWindow", self)
            self.tk.call("wm", "attributes", pd, "-topmost", 1)
        except tk.TclError:
            pass
        user = getattr(self, "_soe2_user", None)
        if callable(user):
            user()
        elif user:
            self.tk.eval(user)

    def __init__(self, master=None, **kw):
        user = kw.pop("postcommand", None)
        orig(self, master, **kw)
        self._soe2_post = self.register(lambda: _post(self))
        self._soe2_user = user
        oconf(self, postcommand=self._soe2_post)
    ttk.Combobox.__init__ = __init__
    ttk.Combobox.configure = configure
    ttk.Combobox.config = configure
    ttk.Combobox._soe2_top = True


_combo_on_top()


def _check_on_card():
    """2.112.1: a switch on a card (panel2) takes the card's color - plain ttk.Checkbuttons there showed the page's
    darker color as a box behind their text (Settings › General › Updates was one). Wraps ttk.Checkbutton once."""
    if getattr(ttk.Checkbutton, "_soe2_card", False):
        return
    orig = ttk.Checkbutton.__init__

    def __init__(self, master=None, **kw):
        if "style" not in kw and master is not None:
            try:
                if str(master.cget("bg")).lower() == str(C["panel2"]).lower():
                    kw["style"] = "Card.TCheckbutton"
            except (tk.TclError, AttributeError):
                pass
        orig(self, master, **kw)
    ttk.Checkbutton.__init__ = __init__
    ttk.Checkbutton._soe2_card = True


_check_on_card()


def setup_style(root):
    """The ttk styles, from the running theme pack (2.60.0). Called at start and again after a live theme swap."""
    from . import themes as TH
    _STYLE_LOG["quiet"] = True
    try:
        with TH.raw():                  # every color here is the running pack's already
            _setup_style(root, TH)
    finally:
        _STYLE_LOG["quiet"] = False


def _setup_style(root, TH):
    root.configure(bg=C["bg"])
    s = ttk.Style(root)
    s.theme_use("clam")
    t = TH.ST.theme
    ns = "%s_%s" % (t.id, C["accent"].lstrip("#"))          # element names: per pack + accent (ttk can't remake one)
    s.configure(".", background=C["bg"], foreground=C["text"], fieldbackground=C["odd"],
                bordercolor=C["line"], lightcolor=C["bg"], darkcolor=C["bg"], troughcolor=C["odd"],
                focuscolor=C["accent"], focusthickness=1)       # 2.100.0: a visible focus ring (Tab) everywhere
    # ---- list headings: a bevelled face from the pack
    hh = 34
    head = ns + ".Treeheading.face"
    TH.make_element(root, s, head, t, "heading", hh, [("pressed", "p"), ("active", "h")])
    s.layout("Treeview.Heading", [(head, {"sticky": "nswe", "children": [("Treeheading.padding", {
        "sticky": "nswe", "children": [("Treeheading.image", {"side": "right", "sticky": ""}),
                                       ("Treeheading.text", {"sticky": "we"})]})]})])
    s.configure("Treeview", background=C["panel"], fieldbackground=C["panel"], foreground=C["text"],
                rowheight=30, borderwidth=0, font=("Segoe UI", 10))
    s.configure("Treeview.Heading", foreground=TH.text_of(t, "heading", "text", C["text"]),
                font=("Segoe UI", 9, "bold"), padding=(8, 8))
    sel_fg = t.c("selection_text", "#ffffff")
    s.map("Treeview", background=[("selected", C["sel"])], foreground=[("selected", sel_fg)],
          bordercolor=[("focus", C["accent"])])                  # 2.100.0: a list you Tab to shows it
    s.map("Treeview.Heading", foreground=[("active", TH.text_of(t, "heading", "text_hover", t.c("text_strong")))])
    s.configure("TNotebook", background=C["bg"], borderwidth=1, bordercolor=C["line"], lightcolor=C["bg"],
                darkcolor=C["bg"], tabmargins=(0, 8, 0, 0))
    s.configure("TNotebook.Tab", background=C["bg"], foreground=C["muted"], padding=(24, 8),
                font=("Segoe UI", 10, "bold"), borderwidth=1, bordercolor=C["bg"], lightcolor=C["bg"],
                darkcolor=C["bg"], focuscolor=C["bg"])
    s.map("TNotebook.Tab",
          background=[("selected", C["panel"]), ("active", C["panel2"])],
          foreground=[("selected", C["accent"]), ("active", C["text"])],
          bordercolor=[("selected", C["gold_dim"]), ("active", C["bg"])],
          lightcolor=[("selected", C["accent"]), ("active", C["panel2"])],
          darkcolor=[("selected", C["panel"]), ("active", C["panel2"])],
          expand=[("selected", (0, 0, 0, 0))])
    s.layout("Plain.TNotebook.Tab", [])                       # no tab strip at all - the Page dropdown replaces it
    s.configure("Plain.TNotebook", background=C["bg"], borderwidth=1, bordercolor=C["gold_dim"], lightcolor=C["bg"],
                darkcolor=C["bg"], tabmargins=(0, 0, 0, 0))
    s.layout("TNotebook.Tab", [("Notebook.tab", {"sticky": "nswe", "children": [
        ("Notebook.padding", {"side": "top", "sticky": "nswe", "children": [
            ("Notebook.label", {"side": "top", "sticky": ""})]})]})])         # same as default minus the focus ring
    nb = TH.button_spec(t, "normal")
    face_mid = TH.grad_at(t.grad(nb["fill"]), 0.5)
    field = dict(fieldbackground=C["odd"], foreground=C["text"], bordercolor=C["line"],
                 lightcolor=mix(C["odd"], "#000000", 0.4), darkcolor=C["gold_dim"], insertcolor=C["text"])
    s.configure("TCombobox", background=face_mid, arrowcolor=C["text"], padding=4, **field)
    s.map("TCombobox", fieldbackground=[("readonly", C["odd"])], foreground=[("readonly", C["text"])],
          background=[("active", TH.grad_at(t.grad(nb["hover"]), 0.5))], bordercolor=[("focus", C["accent"])])
    root.option_add("*TCombobox*Listbox.background", C["panel2"])
    root.option_add("*TCombobox*Listbox.foreground", C["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["sel"])
    root.option_add("*TCombobox*Listbox.selectForeground", sel_fg)
    s.configure("TCheckbutton", background=C["bg"], foreground=C["text"], font=("Segoe UI", 10))
    s.map("TCheckbutton", background=[("active", C["bg"])])
    s.configure("Bar.TCheckbutton", background=C["panel"], foreground=C["text"], font=("Segoe UI", 10))
    s.map("Bar.TCheckbutton", background=[("active", C["panel"])])
    s.configure("Card.TCheckbutton", background=C["panel2"], foreground=C["text"], font=("Segoe UI", 10))
    s.map("Card.TCheckbutton", background=[("active", C["panel2"])])     # 2.70.1: a switch on a section's panel
    s.configure("Card.TRadiobutton", background=C["panel2"], foreground=C["text"], font=("Segoe UI", 10),
                indicatorbackground=C["panel"], indicatorforeground=C["accent"])   # 2.70.0: on a section's panel
    s.map("Card.TRadiobutton", background=[("active", C["panel2"])])
    s.configure("Mod.TCheckbutton", background=C["panel"], foreground=C["text"])
    s.map("Mod.TCheckbutton", background=[("active", C["panel"])])
    switches(root, s)                         # 2.49.0: every on / off box is a modern switch
    s.configure("TSpinbox", background=face_mid, arrowcolor=C["text"], **field)
    s.map("TSpinbox", bordercolor=[("focus", C["accent"])])
    # ---- buttons: bevelled faces drawn from the pack (gradient, light inner edge, round corners on some packs)
    bh = 34
    for style_name, spec, states in (
            ("TButton", "normal", [("disabled", "d"), ("pressed", "p"), ("active", "h")]),
            ("Primary.TButton", "primary", [("disabled", "d"), ("pressed", "p"), ("active", "h")]),
            ("Danger.TButton", "danger", [("disabled", "d"), ("pressed", "p"), ("active", "h")])):
        el = "%s.%s.face" % (ns, style_name.split(".")[0] if "." in style_name else "Button")
        TH.make_element(root, s, el, t, spec, bh, states)
        s.layout(style_name, [(el, {"sticky": "nswe", "children": [("Button.focus", {"sticky": "nswe", "children": [
            ("Button.padding", {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})]})]})])
        s.configure(style_name, focuscolor=C["accent"], focusthickness=1)     # 2.100.0: the focus ring (Tab)
    face = TH.grad_at(t.grad(TH.button_spec(t, "primary")["fill"]), 0.5)
    pri_text = TH.text_of(t, "primary", "text", text_on(face))
    s.configure("TButton", foreground=TH.text_of(t, "normal", "text", C["text"]), padding=(12, 8),
                font=("Segoe UI", 10), anchor="center")
    s.map("TButton", foreground=[("disabled", C["muted"]), ("active", TH.text_of(t, "normal", "text_hover", t.c("text_strong")))])
    s.configure("Primary.TButton", foreground=pri_text, padding=(12, 8), font=("Segoe UI", 10, "bold"), anchor="center")
    s.map("Primary.TButton", foreground=[("disabled", C["muted"]), ("active", TH.text_of(t, "primary", "text_hover", pri_text))])
    s.layout("Accent.TButton", s.layout("Primary.TButton"))   # (Accent.TButton = the old name of Primary)
    s.configure("Accent.TButton", foreground=pri_text, padding=(12, 8), font=("Segoe UI", 10, "bold"), anchor="center")
    s.map("Accent.TButton", foreground=[("disabled", C["muted"])])
    dface = TH.grad_at(t.grad(TH.button_spec(t, "danger")["fill"]), 0.5)
    s.configure("Danger.TButton", foreground=TH.text_of(t, "danger", "text", text_on(dface, "#ffe9e6")), padding=(12, 8),
                font=("Segoe UI", BODY), anchor="center")
    s.map("Danger.TButton", foreground=[("disabled", C["muted"])])
    # 2.34.0 button hierarchy: Primary (one per area), TButton = secondary, Quiet (no bevel), Danger (deletes)
    s.configure("Quiet.TButton", background=C["panel"], foreground=C["steel"], relief="flat", borderwidth=1,
                bordercolor=C["panel"], lightcolor=C["panel"], darkcolor=C["panel"], focuscolor=C["accent"],
                padding=(12, 8), font=("Segoe UI", BODY), focusthickness=1)
    s.map("Quiet.TButton", background=[("pressed", C["odd"]), ("active", C["panel2"])],
          bordercolor=[("active", C["line"])], lightcolor=[("active", C["panel2"])], darkcolor=[("active", C["panel2"])],
          foreground=[("active", C["text"]), ("disabled", C["muted"])])
    # 2.126.0: small flat buttons for a header strip (Bulk Pricing's Items strip: Undo, Delete, Clear All) - they fit
    # inside the strip; the delete ones have red words (and a word or icon, never the color alone)
    for name, fg in (("Strip.TButton", C["steel"]), ("StripDanger.TButton", C["red"])):
        s.layout(name, [("Button.border", {"sticky": "nswe", "border": "1", "children": [("Button.focus", {
            "sticky": "nswe", "children": [("Button.padding", {"sticky": "nswe", "children": [
                ("Button.label", {"sticky": "nswe"})]})]})]})])
        s.configure(name, background=C["panel"], foreground=fg, relief="solid", borderwidth=1, bordercolor=C["line"],
                    lightcolor=C["panel"], darkcolor=C["panel"], focuscolor=C["accent"], focusthickness=1,
                    padding=(8, 1), font=("Segoe UI", 9), anchor="center", width=0)   # (as wide as its words)
        s.map(name, background=[("pressed", C["odd"]), ("active", C["panel2"])],
              bordercolor=[("active", C["steel"])], lightcolor=[("active", C["panel2"])], darkcolor=[("active", C["panel2"])],
              foreground=[("disabled", C["muted"]), ("active", C["text"] if fg == C["steel"] else fg)])
    s.configure("TEntry", padding=4, **field)
    s.map("TEntry", bordercolor=[("focus", C["accent"])])
    for o in ("Vertical", "Horizontal"):
        s.configure(o + ".TScrollbar", background=face_mid, troughcolor=C["odd"], borderwidth=1,
                    bordercolor=t.c("border_dark"), arrowcolor=C["steel"], lightcolor=C["gold_dim"],
                    darkcolor=t.c("border_dark"))
        s.map(o + ".TScrollbar", background=[("active", TH.grad_at(t.grad(nb["hover"]), 0.5))])
    s.configure("Sash", sashthickness=7, gripcount=0, background=C["line"])


def monitor_rect(root, x, y, full=False):
    """2.25.2: (left, top, right, bottom) of the monitor holding the point (x, y) - its work area, without the
    taskbar. Popups are kept on THAT monitor; winfo_screenwidth() is only the main monitor, which pushed popups over
    to it when the app was on another one."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                            ("dwFlags", wintypes.DWORD)]
            u = ctypes.windll.user32
            u.MonitorFromPoint.restype = ctypes.c_void_p
            u.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
            u.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
            h = u.MonitorFromPoint(wintypes.POINT(int(x), int(y)), 2)        # MONITOR_DEFAULTTONEAREST
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if h and u.GetMonitorInfoW(h, ctypes.byref(mi)):
                r = mi.rcMonitor if full else mi.rcWork     # 2.50.0: full = the whole screen (the game is
                return r.left, r.top, r.right, r.bottom         # full screen: windows over it may sit on the taskbar)
        except Exception:
            buglog.caught()
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def place_near(root, win, x, y):
    """Put `win` with its corner at (x, y), kept inside the monitor that point is on."""
    win.update_idletasks()
    l, t, r, b = monitor_rect(root, x, y)
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    x = max(l, min(int(x), r - w - 8))
    y = max(t, min(int(y), b - h - 8))
    win.geometry(f"+{x}+{y}")
    return x, y


class Toast:
    """Small always-on-top popup near the mouse that never takes keyboard focus."""

    def __init__(self, root):
        self.root, self.win, self.job = root, None, None

    def hide(self):
        if self.job:
            self.root.after_cancel(self.job)
            self.job = None
        if self.win:
            try:
                self.win.destroy()
            except Exception:
                buglog.caught()
            self.win = None

    def show(self, title, lines, color, secs):
        self.hide()
        w = tk.Toplevel(self.root)
        w.withdraw()
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        try:
            w.attributes("-alpha", 0.97)
        except Exception:
            buglog.caught()
        outer = tk.Frame(w, bg=color, padx=2, pady=2)
        outer.pack()
        card = tk.Frame(outer, bg=C["panel"], padx=16, pady=8)
        card.pack()
        tk.Label(card, text=title, bg=C["panel"], fg=color, font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
        for ln in lines:
            tk.Label(card, text=ln, bg=C["panel"], fg=C["text"], font=("Segoe UI", 10), anchor="w",
                     justify="left").pack(fill="x")
        w.update_idletasks()
        place_near(self.root, w, self.root.winfo_pointerx() + 26, self.root.winfo_pointery() + 26)
        if sys.platform == "win32":      # do not steal focus from the game
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(w.winfo_id()) or w.winfo_id()
                st = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                ctypes.windll.user32.SetWindowLongW(hwnd, -20, st | 0x08000000 | 0x00000080)
            except Exception:
                buglog.caught()
        w.deiconify()
        w.bind("<Button-1>", lambda e: self.hide())
        self.win = w
        self.job = self.root.after(int(secs * 1000), self.hide)


class Tooltip:
    """2.37.0: a small tip under a widget while the mouse rests on it (also the text a screen reader can't get from
    an icon). Tooltip(widget, text); .text can be changed later."""

    def __init__(self, widget, text, delay=450):
        self.w, self.text, self.delay, self.win, self.job = widget, text, delay, None, None
        widget._tip = self                                  # (tools/check_ux.py: this button has a tip)
        widget.bind("<Enter>", self._enter, add="+")
        widget.bind("<Leave>", self._leave, add="+")
        widget.bind("<ButtonPress>", self._leave, add="+")
        widget.bind("<Unmap>", self._leave, add="+")       # P4 (2.108.0): a tip stayed up when its page was left
        widget.bind("<Destroy>", self._leave, add="+")

    def _enter(self, _e=None):
        self._cancel()
        self.job = self.w.after(self.delay, self.show)

    def _cancel(self):
        if self.job:
            try:
                self.w.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None

    def _leave(self, _e=None):
        self._cancel()
        self.hide()

    def show(self):
        self.job = None
        if not self.text or self.win is not None:
            return
        try:
            x, y = self.w.winfo_rootx() + 8, self.w.winfo_rooty() + self.w.winfo_height() + 4
        except tk.TclError:
            return
        self.win = tk.Toplevel(self.w)
        self.win.overrideredirect(True)
        try:
            self.win.attributes("-topmost", True)
        except tk.TclError:
            pass
        bg, fg, edge = self._colors()                   # 2.100.0: over the game, the overlay's own look
        tk.Label(self.win, text=self.text, bg=bg, fg=fg, font=("Segoe UI", SMALL), justify="left",
                 wraplength=420, padx=8, pady=4, highlightthickness=1, highlightbackground=edge).pack()
        place_near(self.w.winfo_toplevel(), self.win, x, y)
        self.w.after(400, self._watch)

    def _watch(self):
        """P4: gone as soon as its widget isn't on screen (a page change doesn't send a Leave)."""
        if self.win is None:
            return
        try:
            gone = not self.w.winfo_viewable()
        except tk.TclError:
            gone = True
        if gone:
            return self.hide()
        try:
            self.w.after(400, self._watch)
        except tk.TclError:
            self.hide()

    def _colors(self):
        """(bg, fg, edge): the app's colors - or, on a window over the game, the overlay's (its theme and look)."""
        try:
            from .overlaywin import OverlayWindow, pal
            if isinstance(self.w.winfo_toplevel(), OverlayWindow):
                P = pal()
                return P["bg"], P["text"], P.get("edge") or P.get("leather") or C["line"]
        except Exception:
            buglog.caught()
        return C["panel2"], C["text"], C["line"]

    def hide(self):
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None


class Splitter(tk.Frame):
    """2.123.4 (feedback: the divider was "janky and slow ... no visible indicator"): a left side you can widen or
    narrow by dragging a grip you can see (a line with dots that lights up under the mouse). While dragging only a
    thin guide line moves; the sides are laid out once, when you let go. Splitter(parent, width, lo, keep, on_set);
    .left and .right are the two sides; sashpos(0[, x]) reads or sets the left width."""

    GRIP = 9

    def __init__(self, parent, width=420, lo=330, keep=300, on_set=None, bg=None, **kw):
        super().__init__(parent, bg=bg or C["bg"], **kw)
        self.lo, self.keep, self.on_set, self._want = lo, keep, on_set, int(width)
        self.left = tk.Frame(self, bg=C["panel2"], width=self._want)
        self.left.pack_propagate(False)
        self.left.pack(side="left", fill="y")
        self.grip = tk.Frame(self, bg=C["panel"], width=self.GRIP, cursor="sb_h_double_arrow")
        self.grip.pack_propagate(False)
        self.grip.pack(side="left", fill="y")
        self._bar = tk.Frame(self.grip, bg=C["gold_dim"], width=1)
        self._bar.place(relx=0.5, rely=0, relheight=1, anchor="n")
        self._dots = tk.Label(self.grip, text="⋮\n⋮", bg=C["panel"], fg=C["muted"], font=("Segoe UI", 9),
                              cursor="sb_h_double_arrow", bd=0, padx=0, pady=0)
        self._dots.place(relx=0.5, rely=0.5, anchor="center")
        self.right = tk.Frame(self, bg=C["panel"])
        self.right.pack(side="left", fill="both", expand=True)
        self._guide = tk.Frame(self, bg=C["orange"], width=2)
        self._x0 = None
        for w in (self.grip, self._dots, self._bar):
            w.bind("<Enter>", lambda e: self._lit(True), add="+")
            w.bind("<Leave>", lambda e: self._lit(self._x0 is not None), add="+")
            w.bind("<ButtonPress-1>", self._press, add="+")
            w.bind("<B1-Motion>", self._drag, add="+")
            w.bind("<ButtonRelease-1>", self._release, add="+")
        Tooltip(self.grip, "Drag to make the item side wider or narrower")
        Tooltip(self._dots, "Drag to make the item side wider or narrower")
        self.bind("<Configure>", lambda e: self._clamp_now(), add="+")

    def _lit(self, on):
        try:
            self._bar.config(bg=C["orange"] if on else C["gold_dim"])
            self._dots.config(fg=C["orange"] if on else C["muted"])
        except tk.TclError:
            pass

    def clamp(self, x):
        pw = self.winfo_width()
        hi = pw - self.keep - self.GRIP if pw > self.lo + self.keep + self.GRIP else max(self.lo, x)
        return int(max(self.lo, min(x, hi)))

    def _clamp_now(self):
        x = self.clamp(self._want)
        if x != int(self.left.cget("width")):
            self.left.config(width=x)

    def _press(self, e):
        self._x0 = self.winfo_rootx()
        self._lit(True)
        self._guide.place(x=self._want + self.GRIP // 2, y=0, relheight=1)
        self._guide.lift()

    def _drag(self, e):
        if self._x0 is None:
            return
        x = self.clamp(e.x_root - self._x0)
        self._guide.place_configure(x=x + self.GRIP // 2)

    def _release(self, e):
        if self._x0 is None:
            return
        x = self.clamp(e.x_root - self._x0)
        self._x0 = None
        self._guide.place_forget()
        self._lit(False)
        self.sashpos(0, x)
        if self.on_set:
            self.on_set(self._want)

    def sashpos(self, _i=0, x=None):
        if x is None:
            return int(self.left.cget("width"))
        self._want = self.clamp(int(x))
        self.left.config(width=self._want)
        return self._want


class VSplitter(tk.Frame):
    """2.125.6 (feedback: the Craft Helper's pairs were "crammed at the bottom"): Splitter's grip turned on its side -
    a top part you make taller or shorter by dragging a grip you can see (a line with dots that lights up under the
    mouse); a thin guide moves while you drag, the parts are laid out once you let go. .top and .bottom are the two
    parts; sashpos(0[, y]) reads or sets the top's height; on_set(height) when you let go."""

    GRIP = 9

    def __init__(self, parent, height=360, lo=120, keep=110, on_set=None, bg=None, **kw):
        super().__init__(parent, bg=bg or C["panel"], **kw)
        self.lo, self.keep, self.on_set, self._want = lo, keep, on_set, int(height)
        self.top = tk.Frame(self, bg=bg or C["panel"], height=self._want)
        self.top.pack_propagate(False)
        self.top.pack(side="top", fill="x")
        self.grip = tk.Frame(self, bg=bg or C["panel"], height=self.GRIP, cursor="sb_v_double_arrow")
        self.grip.pack_propagate(False)
        self.grip.pack(side="top", fill="x")
        self._bar = tk.Frame(self.grip, bg=C["gold_dim"], height=1)
        self._bar.place(relx=0, rely=0.5, relwidth=1, anchor="w")
        self._dots = tk.Label(self.grip, text="⋯⋯", bg=bg or C["panel"], fg=C["muted"], font=("Segoe UI", 9),
                              cursor="sb_v_double_arrow", bd=0, padx=4, pady=0)
        self._dots.place(relx=0.5, rely=0.5, anchor="center")
        self.bottom = tk.Frame(self, bg=bg or C["panel"])
        self.bottom.pack(side="top", fill="both", expand=True)
        self._guide = tk.Frame(self, bg=C["orange"], height=2)
        self._y0 = None
        for w in (self.grip, self._dots, self._bar):
            w.bind("<Enter>", lambda e: self._lit(True), add="+")
            w.bind("<Leave>", lambda e: self._lit(self._y0 is not None), add="+")
            w.bind("<ButtonPress-1>", self._press, add="+")
            w.bind("<B1-Motion>", self._drag, add="+")
            w.bind("<ButtonRelease-1>", self._release, add="+")
        Tooltip(self._dots, "Drag to make the top part taller or shorter")
        self.bind("<Configure>", lambda e: self._clamp_now(), add="+")

    def _lit(self, on):
        try:
            self._bar.config(bg=C["orange"] if on else C["gold_dim"])
            self._dots.config(fg=C["orange"] if on else C["muted"])
        except tk.TclError:
            pass

    def clamp(self, y):
        ph = self.winfo_height()
        hi = ph - self.keep - self.GRIP if ph > self.lo + self.keep + self.GRIP else max(self.lo, y)
        return int(max(self.lo, min(y, hi)))

    def _clamp_now(self):
        y = self.clamp(self._want)
        if y != int(self.top.cget("height")):
            self.top.config(height=y)

    def _press(self, e):
        self._y0 = self.winfo_rooty()
        self._lit(True)
        self._guide.place(x=0, y=self._want + self.GRIP // 2, relwidth=1)
        self._guide.lift()

    def _drag(self, e):
        if self._y0 is None:
            return
        self._guide.place_configure(y=self.clamp(e.y_root - self._y0) + self.GRIP // 2)

    def _release(self, e):
        if self._y0 is None:
            return
        y = self.clamp(e.y_root - self._y0)
        self._y0 = None
        self._guide.place_forget()
        self._lit(False)
        self.sashpos(0, y)
        if self.on_set:
            self.on_set(self._want)

    def sashpos(self, _i=0, y=None):
        if y is None:
            return int(self.top.cget("height"))
        self._want = self.clamp(int(y))
        self.top.config(height=self._want)
        return self._want


class SegBar(tk.Frame):
    """A row of joined toggle buttons (2.0 beta 7), like  [ Total | Daily ].  One is picked at a time; the picked one is
    lit with an orange line under it. command(value) is called when you pick another."""

    def __init__(self, parent, options, value=None, command=None, bg=None, size=10, pad=(16, 4), badges=None):
        super().__init__(parent, bg=C["line"], padx=1, pady=1)
        self.command, self.value, self.btns = command, value if value is not None else options[0], {}
        self.size, self.pad = size, pad
        self.badges = dict(badges or {})            # 2.38.0: {"Stash tab": "BETA"} - a small tag inside that button
        for i, opt in enumerate(options):
            self._add(opt, i)
        self.paint()

    def _add(self, opt, i):
        f = tk.Frame(self, bg=C["line"])
        f.pack(side="left", padx=(1 if i else 0, 0))
        top = tk.Frame(f, bg=C["line"])
        top.pack(fill="x")
        badge = self.badges.get(opt)
        lab = tk.Label(top, text=opt, font=("Segoe UI", self.size, "bold"), padx=self.pad[0], pady=self.pad[1],
                       cursor="hand2")
        lab.pack(side="left", fill="both", expand=True)
        tag = None
        if badge:                                   # inside the button, so it reads as "this option is BETA"
            lab.config(padx=0)
            lab.pack_configure(padx=(self.pad[0], 4))
            tag = tk.Label(top, text=badge, bg="#3a2a10", fg="#ffcf40", font=("Segoe UI", SMALL - 2, "bold"), padx=4,
                           pady=0, cursor="hand2", highlightthickness=1, highlightbackground=C["accent"])
            tag.pack(side="left", padx=(0, self.pad[0]))
            tag.bind("<Enter>", lambda e, o=opt: self.paint(hover=o))
        line = tk.Frame(f, height=2)
        line.pack(fill="x")
        for w in (lab, line, top) + ((tag,) if tag else ()):
            w.bind("<Button-1>", lambda e, o=opt: self.pick(o))
        lab.bind("<Enter>", lambda e, o=opt: self.paint(hover=o))
        lab.bind("<Leave>", lambda e: self.paint())
        self.btns[opt] = (lab, line)

    def paint(self, hover=None):
        for opt, (lab, line) in self.btns.items():
            on = opt == self.value
            bg = "#2c4a84" if on else ("#1b2a48" if opt == hover else "#111a2c")
            lab.config(bg=bg, fg="#ffffff" if on else "#9fb0cc")
            lab.master.config(bg=bg)                # (the row that also holds a badge)
            line.config(bg=C["accent"] if on else bg)

    def pick(self, opt, notify=True):
        if opt not in self.btns:
            return
        changed = opt != self.value
        self.value = opt
        self.paint()
        if notify and changed and self.command:
            self.command(opt)

    def get(self):
        return self.value


class SegBook(tk.Frame):
    """Pages switched by a SegBar instead of notebook tabs (real buttons, 2.0 beta 7). Same calls as ttk.Notebook for
    what the app uses: add, select, index, tab(i, 'text'); fires <<NotebookTabChanged>>."""

    def __init__(self, parent, bg=None, **kw):
        super().__init__(parent, bg=bg or C["panel"], **kw)
        self.top = tk.Frame(self, bg=bg or C["panel"])
        self.top.pack(fill="x", pady=(0, 8))
        self.bar = SegBar(self.top, ["-"], command=self._picked, size=10, pad=(16, 8))
        self.bar.pack(side="left")
        for w in self.bar.winfo_children():
            w.destroy()
        self.bar.btns = {}
        self.pages, self.titles, self.cur = [], [], None

    def add(self, frame, text=""):
        self.pages.append(frame)
        self.titles.append(text)
        self.bar._add(text, len(self.titles) - 1)
        if self.cur is None:
            self.select(0)
        else:
            self.bar.paint()

    def _picked(self, text):
        self.select(self.titles.index(text))

    def select(self, which=None):
        if which is None:
            return str(self.pages[self.cur]) if self.cur is not None else ""
        i = which if isinstance(which, int) else self.pages.index(which)
        if i == self.cur:
            return
        if self.cur is not None:
            self.pages[self.cur].pack_forget()
        self.cur = i
        self.pages[i].pack(fill="both", expand=True)
        self.bar.pick(self.titles[i], notify=False)
        self.event_generate("<<NotebookTabChanged>>")

    def index(self, what):
        if what == "end":
            return len(self.pages)
        if isinstance(what, int):
            return what
        return next((i for i, p in enumerate(self.pages) if str(p) == str(what)), self.cur or 0)

    def tab(self, i, option="text"):
        return self.titles[i]


class SbGuard:
    """2.112.2: a scroll bar that shows only when needed can loop forever: shown -> the page is narrower -> its
    wrapped text is taller / shorter -> hidden -> wider -> shown ... Tk's idle queue never empties and the app stops
    responding (it hung Windows on a theme change: its scroll bar and text measure differently). Count the flips:
    after 3 within a second the bar stays shown until the page settles (2 s quiet)."""

    def __init__(self):
        self.flips = []
        self.hold = 0.0

    def may_hide(self):
        import time as _t
        return _t.time() >= self.hold

    def flipped(self):
        import time as _t
        now = _t.time()
        self.flips = [t for t in self.flips if now - t < 1.0] + [now]
        if len(self.flips) > 3:
            self.hold = now + 2.0
            self.flips = []


class ScrollArea(tk.Frame):
    """A frame whose content scrolls up and down (scroll bar + mouse wheel) when it is taller than the window
    (2.0 beta 14: Settings). Put the content in .inner; it is always as wide as the area.
    The wheel is caught on the area's own window, so it works over every widget inside and doesn't get in the way of
    other windows' scrolling."""

    def __init__(self, parent, bg, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.sb = ttk.Scrollbar(self, orient="vertical")
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, yscrollcommand=self._sb_set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.sb.config(command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=(0, 0, e.width, e.height)))
        self._hooked = None
        self._guard = SbGuard()
        self.bind("<Map>", lambda e: self._hook(), add="+")
        self.after_idle(self._hook)

    def _sb_set(self, a, b):
        """Show the scroll bar only when there is something to scroll (never flipping back and forth - SbGuard)."""
        shown = self.sb.winfo_ismapped()
        if float(a) <= 0.0 and float(b) >= 1.0:
            if shown and self._guard.may_hide():
                self.sb.pack_forget()
                self._guard.flipped()
        elif not shown:
            self.sb.pack(side="right", fill="y", before=self.canvas)
            self._guard.flipped()
        self.sb.set(a, b)

    def _hook(self):
        top = self.winfo_toplevel()
        if self._hooked is top:
            return
        self._hooked = top
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            top.bind(ev, self._wheel, add="+")

    def _over_me(self, e):
        try:
            w = self.winfo_containing(e.x_root, e.y_root)
        except (tk.TclError, KeyError):
            return False
        while w is not None:
            if w is self:
                return True
            w = w.master
        return False

    def _wheel(self, e):
        if not self.winfo_exists() or not self._over_me(e):
            return
        if isinstance(e.widget, (tk.Text, tk.Listbox, ttk.Treeview)):      # those scroll themselves
            return
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            return
        if getattr(e, "num", None) in (4, 5):
            step = -1 if e.num == 4 else 1
        else:
            step = -1 if e.delta > 0 else 1
        self.canvas.yview_scroll(step * 2, "units")


# ---------------------------------------------------------------- choosing a key by pressing it (2.0 beta 16)
CAPTURING = [None]           # the key box waiting for a key: the app's keyboard / mouse watcher hands it the key
CAPTURE_HOOK = [None]        # the app sets this: f(waiting) - e.g. watch the mouse buttons while a box waits
_KEYSYMS = {"Return": "enter", "KP_Enter": "enter", "space": "space", "Tab": "tab", "Insert": "insert",
            "Delete": "delete", "Home": "home", "End": "end", "Prior": "pgup", "Next": "pgdn", "Up": "up",
            "Down": "down", "Left": "left", "Right": "right", "grave": "`", "minus": "-", "equal": "=",
            "bracketleft": "[", "bracketright": "]", "semicolon": ";", "apostrophe": "'", "comma": ",",
            "period": ".", "slash": "/", "backslash": "\\"}
_MODS = {"Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R", "Super_L", "Super_R",
         "Win_L", "Win_R", "Caps_Lock", "Num_Lock", "ISO_Level3_Shift"}


def key_from_event(keysym, ctrl, alt, shift):
    """A key you pressed -> the text the app stores ('F3', 'Ctrl+Shift+H', 'Numpad5'), or None for a key it can't use."""
    k = None
    if keysym.startswith("F") and keysym[1:].isdigit() and 1 <= int(keysym[1:]) <= 24:
        k = keysym
    elif keysym.startswith("KP_") and keysym[3:].isdigit():
        k = "Numpad" + keysym[3:]
    elif len(keysym) == 1 and keysym.isalnum():
        k = keysym.upper()
    elif keysym in _KEYSYMS:
        k = _KEYSYMS[keysym]
        k = k.capitalize() if len(k) > 1 else k
    if k is None:
        return None
    return "+".join([m for m, on in (("Ctrl", ctrl), ("Alt", alt), ("Shift", shift)) if on] + [k])


def key_from_vk(vk, ctrl, alt, shift):
    """Windows key code -> stored text, using the same key names the hotkeys understand."""
    from .overlay import VK
    mouse = {0x04: "MButton", 0x05: "XButton1", 0x06: "XButton2"}
    names = [n for n, v in VK.items() if v == vk and n not in ("ins", "del", "escape", "pageup", "pagedown")]
    if vk in mouse:
        n = mouse[vk]
    elif not names:
        return None
    else:
        n = names[0]
        n = n.upper() if len(n) == 1 or (n[0] == "f" and n[1:].isdigit()) else n.capitalize()
    return "+".join([m for m, on in (("Ctrl", ctrl), ("Alt", alt), ("Shift", shift)) if on] + [n])


class KeyCapture(tk.Label):
    """A hotkey box like most apps have: click it and press the key (with Ctrl / Alt / Shift if you like).
    Esc = keep the old key, Backspace / Delete / right-click = no key. Holds its value in a StringVar."""

    TIMEOUT_MS = 15000

    def __init__(self, parent, variable, width=12, on_change=None, allow_esc=False, **kw):
        super().__init__(parent, width=width, anchor="w", padx=8, cursor="hand2", takefocus=1,
                         bg=C["odd"], fg=C["text"], font=("Consolas", 9), highlightthickness=1,
                         highlightbackground=C["line"], highlightcolor=C["accent"], **kw)
        self.var, self.on_change, self.waiting, self._alt = variable, on_change, False, False
        self.allow_esc = allow_esc          # 2.121.1: a close key may be Esc itself (a click elsewhere gives up)
        self.var.trace_add("write", lambda *a: self.show())
        self.bind("<Button-1>", lambda e: self.start())
        self.bind("<Button-3>", lambda e: self.set(""))
        self.bind("<KeyPress>", self._press)
        self.bind("<KeyRelease>", self._release)
        self.bind("<Button-2>", lambda e: self.waiting and self.set("MButton"))
        self._job = None
        self.show()

    def show(self):
        from .overlay import key_label
        if self.waiting:
            self.config(text="Press a key…", fg=C["accent"], highlightbackground=C["accent"])
        else:
            v = self.var.get().strip()
            self.config(text=key_label(v) if v else "click to set", fg=C["text"] if v else C["muted"],
                        highlightbackground=C["line"])

    def start(self):
        other = CAPTURING[0]
        if other is not None and other is not self:
            try:
                other.stop()                       # only one box waits at a time
            except tk.TclError:
                pass
        self.waiting, self._alt = True, False
        CAPTURING[0] = self
        top = self.winfo_toplevel()
        if not getattr(top, "_kc_click", False):   # a click anywhere else in the window gives up waiting
            top._kc_click = True
            top.bind("<ButtonPress>", lambda e: CAPTURING[0] is not None and e.widget is not CAPTURING[0]
                     and CAPTURING[0].stop(), add="+")
        try:
            self.focus_force()                     # the app's windows may not have the keyboard yet
        except tk.TclError:
            pass
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(self.TIMEOUT_MS, self.stop)
        if CAPTURE_HOOK[0]:
            CAPTURE_HOOK[0](True)
        self.show()

    def stop(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        if self.waiting:
            self.waiting = False
            if CAPTURING[0] is self:
                CAPTURING[0] = None
            if CAPTURE_HOOK[0]:
                CAPTURE_HOOK[0](False)
            self.show()

    def take(self, vk, ctrl, alt, shift):
        """A key (or mouse button) from the app's keyboard / mouse watcher, while this box waits (Windows)."""
        if not self.waiting:
            return
        if vk == 0x1B and self.allow_esc and not (ctrl or alt or shift):
            self.set("Esc")
        elif vk == 0x1B:
            self.stop()
        elif vk in (0x08, 0x2E) and not (ctrl or alt or shift):
            self.set("")
        else:
            k = key_from_vk(vk, ctrl, alt, shift)
            if k:
                self.set(k)

    def set(self, text):
        self.var.set(text)
        self.stop()
        if self.on_change:
            self.on_change(text)

    def _release(self, e):
        if e.keysym in ("Alt_L", "Alt_R"):
            self._alt = False

    def _press(self, e):
        if not self.waiting:
            if e.keysym in ("Return", "space"):
                self.start()
                return "break"
            return None
        if e.keysym in ("Alt_L", "Alt_R"):
            self._alt = True
            return "break"
        if e.keysym in _MODS:
            return "break"
        if e.keysym == "Escape":
            if self.allow_esc and not (e.state & 0x5):
                self.set("Esc")
            else:
                self.stop()
            return "break"
        if e.keysym in ("BackSpace", "Delete") and not (e.state & 0x5):
            self.set("")
            return "break"
        alt = self._alt or bool(e.state & 0x20000) or (sys.platform != "win32" and bool(e.state & 0x8))
        k = None
        if sys.platform == "win32":               # on Windows the key code IS the key (tells numpad 5 from 5 etc.)
            k = key_from_vk(e.keycode, bool(e.state & 0x4), alt, bool(e.state & 0x1))
        k = k or key_from_event(e.keysym, bool(e.state & 0x4), alt, bool(e.state & 0x1))
        if k:
            self.set(k)
        return "break"


# ---------------------------------------------------------------- the app's look (2.0.0: Settings > Appearance)
# A theme recolours the whole app in one place: every color handed to Tk passes through theme_color(), which moves the
# app's steel-blue / navy tones to the theme's hue (lightness kept, so contrast stays the same). Colors that mean
# something (item rarities, green / red, gold for money, the accent) are left alone. Applied at start-up.
import re as _re

# ------------------------------------------------------------------ 2.60.0: theme packs (soe2/themes.py, themes/*.json)
from . import themes as _themes

THEMES = {t.id: (t.name, None, 1.0) for t in _themes.ordered()}     # id: (label, -, -) - the old shape, kept
_STYLE_LOG = {"quiet": False, "calls": {}}     # ttk style calls made outside setup_style - replayed after a swap
_THEME = {"keep": set()}               # (old name, kept for code that adds to it)


def theme_color(c):
    """A color as the running theme shows it (every color given to Tk passes here)."""
    return _themes.tone(c)


def apply_look(theme=None, root=None):
    """Call once at start-up, before any window is built. relook() swaps it later, live. (2.119.0: a theme keeps its
    own accent and the text size is fixed - Settings › Appearance had both.)"""
    import tkinter.ttk as _ttk
    if not _themes.ST.base:
        _themes.init(C, _BASE)
    _themes.set_theme(_themes.packs()[_themes.pick_id(theme)], None)
    if not getattr(tk.Misc, "_soe2_themed", False):          # every color given to Tk goes through theme_color
        orig = tk.Misc._options

        def _options(self, cnf, kw=None):
            res = orig(self, cnf, kw)
            return tuple(theme_color(v) if isinstance(v, str) else v for v in res)
        tk.Misc._options = _options
        oa = tk.Misc.option_add

        def _option_add(self, pattern, value, priority=None):
            return oa(self, pattern, theme_color(value) if isinstance(value, str) else value, priority)
        tk.Misc.option_add = _option_add
        fo, fm = _ttk._format_optdict, _ttk._format_mapdict

        def _fo(*a, **k):
            return tuple(theme_color(v) if isinstance(v, str) else v for v in fo(*a, **k))

        hexes = _re.compile(r"#[0-9a-fA-F]{6}\b")

        def _fm(*a, **k):                                      # state maps: "readonly #0b111c" -> recolour inside
            return tuple(hexes.sub(lambda m_: theme_color(m_.group(0)), v) if isinstance(v, str) else v
                         for v in fm(*a, **k))
        _ttk._format_optdict, _ttk._format_mapdict = _fo, _fm
        sc, sm = _ttk.Style.configure, _ttk.Style.map

        def _sc(self, style, query_opt=None, **kw):            # 2.60.0: remember style calls made outside
            if kw and query_opt is None and not _STYLE_LOG["quiet"]:   # setup_style, to make them again after a swap
                _STYLE_LOG["calls"].setdefault(("configure", style), {}).update(kw)
            return sc(self, style, query_opt, **kw)

        def _sm(self, style, query_opt=None, **kw):
            if kw and query_opt is None and not _STYLE_LOG["quiet"]:
                _STYLE_LOG["calls"].setdefault(("map", style), {}).update(kw)
            return sm(self, style, query_opt, **kw)
        _ttk.Style.configure, _ttk.Style.map = _sc, _sm
        tk.Misc._soe2_themed = True
    return _themes.ST.theme


def relook(root, theme):
    """2.60.0: swap the theme while the app runs - every window, list, canvas and menu is re-colored in place."""
    import time as _t
    t0 = _t.time()
    old = _themes.snapshot()
    _themes.set_theme(_themes.packs()[_themes.pick_id(theme)], None)
    tr = _themes._translator(old)
    from .hangwatch import step                 # 2.114.3: where a theme change was, if the app closes on one
    step(f"theme change to {theme}: windows")
    n = _themes.walk(root, tr)
    step(f"theme change to {theme}: styles")
    setup_style(root)
    s = ttk.Style(root)
    _STYLE_LOG["quiet"] = True
    try:
        for (how, style), kw in list(_STYLE_LOG["calls"].items()):
            kw = ({k: (tr(("style", style, k), v) if _themes.is_hex(v) else v) for k, v in kw.items()}
                  if how == "configure" else kw)
            try:
                (s.configure if how == "configure" else s.map)(style, **kw)
            except Exception:
                buglog.caught()
    finally:
        _STYLE_LOG["quiet"] = False
    step(f"theme change to {theme}: self-painted parts")
    _themes.notify()
    step(f"theme change to {theme}: done")
    return n, _t.time() - t0
