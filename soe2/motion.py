"""2.100.0 Polish 6 - hover, focus and motion, the same everywhere (installed once at start by style.responsive's
caller, App.__init__):
  * Hover: a list row lights under the mouse (every ttk Treeview); a clickable icon or link (a Label with a hand cursor
    - ✕, ↻, ⋯, "Never show again" ...) brightens. Buttons already had hover / pressed faces (themes.make_element).
  * Focus: Tab to a button, switch, box or list and it shows a ring in the accent color (style._setup_style).
  * Motion: none. (2.135.1, feedback: "reduce motion ... should have that enabled by default and remove the toggle":
    tooltips, toasts and windows over the game appear at once - the fade and its switch are gone.)
Nothing here touches the game: it's the app's own windows."""
import tkinter as tk

from .config import SETTINGS

HOVER_CURSORS = ("hand2", "hand1")
_STATE = {"installed": False}


def _mix(a, b, t):
    try:
        a, b = a.lstrip("#"), b.lstrip("#")
        ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
        cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
        return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))
    except (ValueError, IndexError):
        return None


def _hex(w, color):
    """Any Tk color -> #rrggbb (or None)."""
    try:
        r, g, b = w.winfo_rgb(color)
        return "#%02x%02x%02x" % (r // 256, g // 256, b // 256)
    except tk.TclError:
        return None


# ---------------------------------------------------------------- clickable labels
def _label_enter(e):
    w = e.widget
    try:
        if str(w.cget("cursor")) not in HOVER_CURSORS or str(w.cget("state")) == "disabled":
            return
        fg = _hex(w, w.cget("fg"))
    except (tk.TclError, AttributeError):
        return
    if not fg:
        return
    lit = _mix(fg, "#ffffff", 0.45)
    if lit and lit != fg:
        w._hover_fg = (fg, lit)
        w.configure(fg=lit)


def _label_leave(e):
    w = e.widget
    old = getattr(w, "_hover_fg", None)
    if not old:
        return
    w._hover_fg = None
    try:
        if _hex(w, w.cget("fg")) == old[1]:        # (code changed it meanwhile: leave theirs)
            w.configure(fg=old[0])
    except tk.TclError:
        pass


# ---------------------------------------------------------------- list rows
def _row_color():
    from .style import C
    return _mix(C["panel"], C.get("accent", "#e8812c"), 0.16) or C.get("odd", "#1a2230")


BG_TAGS = ("row_a", "row_b", "odd", "even")     # tags that paint a row's background (listkit stripes, older lists)


def _set_tags(tv, iid, tags):
    """Set a row's tags without listkit putting its stripe back (it would hide the hover)."""
    was = getattr(tv, "_restriping", False)
    tv._restriping = True
    try:
        tv.item(iid, tags=tags)
    finally:
        tv._restriping = was


def _tree_motion(e):
    tv = e.widget
    try:
        iid = tv.identify_row(e.y)
    except tk.TclError:
        return
    if iid == getattr(tv, "_hover", (None,))[0]:
        return
    _tree_clear(tv)
    if not iid:
        return
    try:
        tv.tag_configure("_hover", background=_row_color())        # (cheap; follows a theme swap)
        old = tuple(tv.item(iid, "tags") or ())
        # Tk paints the background of the tag created FIRST - a stripe always beat a hover tag, so the row's
        # background tags step aside while the mouse is on it
        new = tuple(t for t in old if t not in BG_TAGS) + ("_hover",)
        _set_tags(tv, iid, new)
        tv._hover = (iid, old, new)
    except tk.TclError:
        pass


def _tree_clear(tv):
    iid, old, new = getattr(tv, "_hover", (None, None, None))
    tv._hover = (None, None, None)
    if iid:
        try:
            if tv.exists(iid) and tuple(tv.item(iid, "tags") or ()) == new:   # (unchanged since: put it back)
                _set_tags(tv, iid, old)
        except tk.TclError:
            pass


def _tree_leave(e):
    _tree_clear(e.widget)


def install(root):
    """Once per app: the class bindings (they reach every Label / Treeview, made now or later)."""
    if _STATE["installed"]:
        return
    _STATE["installed"] = True
    root.bind_class("Label", "<Enter>", _label_enter, add="+")
    root.bind_class("Label", "<Leave>", _label_leave, add="+")
    root.bind_class("Treeview", "<Motion>", _tree_motion, add="+")
    root.bind_class("Treeview", "<Leave>", _tree_leave, add="+")

