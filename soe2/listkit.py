"""Standard keys, right-click menus and striped rows everywhere (2.12.0).

Every list (Treeview), in every window:
  - rows alternate colors like a spreadsheet (in every theme), kept right after rows are added, removed or sorted;
  - Ctrl+C copies the selected rows (tab-separated, pastes into a spreadsheet); Ctrl+A / Delete / Ctrl+Z as before
    (listkeys.py);
  - right-click: the window's own actions for the row (2.36.0: tree.menu_actions), then Copy, Copy every row,
    Select all, and Delete / Undo where that list has them;
  - the Menu key / Shift+F10 opens the same menu from the keyboard (2.36.0).
Every box you type in (Entry, Spinbox, Combobox, Text):
  - Ctrl+A selects everything, Ctrl+Z undoes your last change (Ctrl+C / X / V as always);
  - right-click: Undo, Cut, Copy, Paste, Delete, Select all.
A widget that already has its own right-click menu keeps it. Plain Tk class bindings - Windows and Linux alike.

Also the poe2db key (Ctrl+Shift+D by default, Settings > Hotkeys): opens poe2db's modifier list in your browser. It's a
link only - nothing is read from or copied off that site."""
import tkinter as tk
from tkinter import ttk
import webbrowser

from .style import C

POE2DB_URL = "https://poe2db.tw/us/Modifiers"
STRIPE = ("row_a", "row_b")
TYPING = ("Entry", "TEntry", "Spinbox", "TSpinbox", "TCombobox")
UNDO_DEPTH = 50


def _stripe_bg():
    return C.get("stripe", "#16213a")


# ================================================================ striped rows
def restripe(tree):
    """Give the visible rows alternating backgrounds, top to bottom (open branches included)."""
    try:
        if not tree.winfo_exists():
            return
        tree.tag_configure(STRIPE[0], background=C["panel"])
        tree.tag_configure(STRIPE[1], background=_stripe_bg())
        n = 0

        def walk(parent):
            nonlocal n
            for iid in tree.get_children(parent):
                cur = list(tree.item(iid, "tags") or ())                 # (read once - 2.25.1)
                want = [t for t in cur if t not in STRIPE and t not in ("odd", "even")] + [STRIPE[n % 2]]
                if cur != want:
                    tree.item(iid, tags=want)
                n += 1
                if tree.item(iid, "open"):
                    walk(iid)
        walk("")
    except tk.TclError:
        pass
    finally:
        try:
            tree._stripe_job = None
        except Exception:
            pass


def schedule_restripe(tree):
    if getattr(tree, "_stripe_job", None) is None and not getattr(tree, "_restriping", False):
        try:
            tree._stripe_job = tree.after_idle(lambda: _run_restripe(tree))
        except tk.TclError:
            pass


def _run_restripe(tree):
    tree._restriping = True
    try:
        restripe(tree)
    finally:
        tree._restriping = False


def _patch_treeview():
    """Any change to a list's rows restripes it once things are idle (so a fill of 500 rows restripes once)."""
    if getattr(ttk.Treeview, "_soe2_striped", False):
        return
    ttk.Treeview._soe2_striped = True
    for name in ("insert", "delete", "move", "detach", "reattach"):
        orig = getattr(ttk.Treeview, name)

        def wrapped(self, *a, _orig=orig, **k):
            res = _orig(self, *a, **k)
            schedule_restripe(self)
            return res
        setattr(ttk.Treeview, name, wrapped)
    orig_item = ttk.Treeview.item

    def item(self, iid, option=None, **kw):              # someone set new tags: put the stripe back
        if "tags" in kw and not getattr(self, "_restriping", False):
            # 2.25.1: keep this row's own stripe instead of restriping the whole list - with 2,000 rows every price
            # that came in restriped all of them (half the time of each update)
            try:
                have = [t for t in (orig_item(self, iid, "tags") or ()) if t in STRIPE]
            except tk.TclError:
                have = []
            new = kw["tags"]
            new = [new] if isinstance(new, str) else list(new or ())
            if have:
                kw["tags"] = [t for t in new if t not in STRIPE and t not in ("odd", "even")] + have[:1]
                return orig_item(self, iid, option, **kw)
            res = orig_item(self, iid, option, **kw)
            schedule_restripe(self)
            return res
        return orig_item(self, iid, option, **kw)
    ttk.Treeview.item = item


# ================================================================ copying rows
def rows_text(tree, iids):
    lines = []
    for iid in iids:
        vals = list(tree.item(iid, "values") or ())
        txt = tree.item(iid, "text")
        if txt:
            vals.insert(0, txt)
        lines.append("\t".join(str(v) for v in vals))
    return "\n".join(lines)


def copy_rows(tree, every=False):
    iids = tree.get_children("") if every else tree.selection()
    if not iids:
        return False
    txt = rows_text(tree, iids)
    tree.clipboard_clear()
    tree.clipboard_append(txt)
    return True


# ================================================================ typing boxes: select all / undo
def _get(w):
    try:
        return w.get("1.0", "end-1c") if isinstance(w, tk.Text) else w.get()
    except tk.TclError:
        return None


def _set(w, text):
    if isinstance(w, tk.Text):
        w.delete("1.0", "end")
        w.insert("1.0", text)
    else:
        w.delete(0, "end")
        w.insert(0, text)
        w.icursor("end")


def _editable(w):
    try:
        return str(w.cget("state")) not in ("disabled", "readonly")
    except tk.TclError:
        return True


def select_all(w):
    try:
        if isinstance(w, tk.Text):
            w.tag_add("sel", "1.0", "end-1c")
            w.mark_set("insert", "end-1c")
        else:
            w.selection_range(0, "end")
            w.icursor("end")
    except (tk.TclError, AttributeError):
        pass
    return "break"


class History:
    """Undo for one-line boxes (Tk's own Entry has none). Remembers each value before a change."""

    def __init__(self):
        self.data = {}

    def note(self, w):
        cur = _get(w)
        if cur is None:
            return
        h = self.data.setdefault(str(w), {"last": cur, "stack": []})
        if cur != h["last"]:
            h["stack"].append(h["last"])
            del h["stack"][:-UNDO_DEPTH]
            h["last"] = cur

    def start(self, w):
        cur = _get(w)
        if cur is not None:
            h = self.data.setdefault(str(w), {"last": cur, "stack": []})
            if not h["stack"]:
                h["last"] = cur

    def undo(self, w):
        h = self.data.get(str(w))
        if not h or not h["stack"] or not _editable(w):
            return "break"
        prev = h["stack"].pop()
        h["last"] = prev
        _set(w, prev)
        return "break"


HISTORY = History()


# ================================================================ the menus
def _menu(widget):
    return tk.Menu(widget, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84",
                   activeforeground="#ffffff", disabledforeground=C["muted"])


def _own_menu(widget):
    """True when this widget has its own right-click (Game search look-up, Wealth's item menu ...)."""
    try:
        return bool(widget.bind("<Button-3>"))
    except tk.TclError:
        return False


def edit_menu(e):
    w = e.widget
    if _own_menu(w) or not isinstance(w, tk.Misc):
        return None
    try:
        w.focus_set()
    except tk.TclError:
        pass
    ed = _editable(w)
    try:
        has_sel = bool(w.tag_ranges("sel")) if isinstance(w, tk.Text) else w.selection_present()
    except (tk.TclError, AttributeError):
        has_sel = False
    try:
        clip = bool(w.clipboard_get())
    except tk.TclError:
        clip = False
    st = lambda on: "normal" if on else "disabled"                       # noqa: E731
    h = HISTORY.data.get(str(w))
    can_undo = ed and (bool(h and h["stack"]) if not isinstance(w, tk.Text) else True)
    m = _menu(w)
    m.add_command(label="Undo", accelerator="Ctrl+Z", state=st(can_undo),
                  command=lambda: w.event_generate("<<Undo>>") if isinstance(w, tk.Text) else HISTORY.undo(w))
    m.add_separator()
    m.add_command(label="Cut", accelerator="Ctrl+X", state=st(ed and has_sel), command=lambda: _edit(w, "<<Cut>>"))
    m.add_command(label="Copy", accelerator="Ctrl+C", state=st(has_sel), command=lambda: w.event_generate("<<Copy>>"))
    m.add_command(label="Paste", accelerator="Ctrl+V", state=st(ed and clip), command=lambda: _edit(w, "<<Paste>>"))
    m.add_command(label="Delete", accelerator="Del", state=st(ed and has_sel), command=lambda: _edit(w, "<<Clear>>"))
    m.add_separator()
    m.add_command(label="Select all", accelerator="Ctrl+A", command=lambda: select_all(w))
    m.tk_popup(e.x_root, e.y_root)
    return "break"


def _edit(w, ev):
    w.event_generate(ev)
    HISTORY.note(w)


def list_menu(app, e):
    tree = e.widget
    if _own_menu(tree):
        return None
    row = tree.identify_row(e.y)
    if row and row not in tree.selection():
        tree.selection_set(row)
        tree.focus(row)
    try:
        tree.focus_set()
    except tk.TclError:
        pass
    key, delete = app.listkit_owner(tree)
    sel = tree.selection()
    st = lambda on: "normal" if on else "disabled"                       # noqa: E731
    m = _menu(tree)
    n = len(sel)
    acts = getattr(tree, "menu_actions", None)          # 2.36.0: the window's own actions for the rows, on top
    acts = acts(sel) if callable(acts) and sel else []
    for a in acts:
        if a is None:
            m.add_separator()
            continue
        label, fn, *rest = a
        on = rest[0] if rest else True
        m.add_command(label=label, state=st(on), command=fn, accelerator=rest[1] if len(rest) > 1 else "")
    if acts:
        m.add_separator()
    m.add_command(label=f"Copy {n} row{'s' if n != 1 else ''}" if n else "Copy", accelerator="Ctrl+C",
                  state=st(n), command=lambda: copy_rows(tree))
    m.add_command(label="Copy every row", state=st(tree.get_children("")), command=lambda: copy_rows(tree, every=True))
    multi = str(tree.cget("selectmode")) == "extended"
    m.add_command(label="Select all", accelerator="Ctrl+A", state=st(multi and tree.get_children("")),
                  command=lambda: tree.selection_set(tree.get_children("")))
    if delete is not None:
        m.add_separator()
        m.add_command(label=f"Delete {n}" if n > 1 else "Delete", accelerator="Del", state=st(n),
                      command=lambda: delete(tree.selection()))
    if key is not None and app.can_undo(key):
        m.add_command(label="Undo", accelerator="Ctrl+Z", command=lambda: app.undo_last(key))
    m.tk_popup(e.x_root, e.y_root)
    return "break"


def menu_key(e=None):
    """2.36.0: the Menu key / Shift+F10 opens the right-click menu of whatever has the keyboard (a list: at its focused
    row; a box: at the cursor) - so every menu works without a mouse."""
    root = e.widget.winfo_toplevel() if e is not None else None
    try:
        w = (root or tk._default_root).focus_get()
    except (tk.TclError, KeyError, AttributeError):
        w = None
    if w is None:
        return None
    x, y = 12, 12
    try:
        if isinstance(w, ttk.Treeview):
            row = w.focus() or (w.selection() or ("",))[0]
            if row and not w.selection():
                w.selection_set(row)
            box = w.bbox(row) if row else ""
            if box:
                x, y = box[0] + 24, box[1] + box[3] // 2
        else:
            x, y = min(40, max(4, w.winfo_width() // 2)), max(4, w.winfo_height() // 2)
        w.event_generate("<Button-3>", x=x, y=y, rootx=w.winfo_rootx() + x, rooty=w.winfo_rooty() + y)
    except tk.TclError:
        return None
    return "break"


# ================================================================ wiring (once, at start-up)
def install(app):
    root = app.root
    C.setdefault("stripe", "#16213a")
    _patch_treeview()
    try:
        root.option_add("*Text.undo", True)            # Text boxes made from now on keep an undo history
        root.option_add("*Text.autoSeparators", True)
    except tk.TclError:
        pass
    for cls in TYPING + ("Text",):
        root.bind_class(cls, "<Button-3>", edit_menu, add="+")
        root.bind_class(cls, "<Control-a>", lambda e: select_all(e.widget))
        root.bind_class(cls, "<Control-A>", lambda e: select_all(e.widget))
    for cls in TYPING:
        root.bind_class(cls, "<FocusIn>", lambda e: HISTORY.start(e.widget), add="+")
        root.bind_class(cls, "<KeyRelease>", lambda e: HISTORY.note(e.widget), add="+")
        root.bind_class(cls, "<<Paste>>", lambda e: e.widget.after_idle(lambda w=e.widget: HISTORY.note(w)), add="+")
        root.bind_class(cls, "<Control-z>", lambda e: HISTORY.undo(e.widget))
        root.bind_class(cls, "<Control-Z>", lambda e: HISTORY.undo(e.widget))
    # 2.38.0: the mouse wheel never changes a dropdown. On Windows Tk sends the wheel to the box that has the keyboard,
    # not the one under the mouse, so after picking e.g. Mirror of Kalandra, scrolling the list below quietly changed
    # the pick (Stash tab's currency "went back"). Pick with a click or the arrow keys.
    # (Replacing the class binding - not "break" - so the page around it still scrolls with the wheel.)
    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        root.bind_class("TCombobox", seq, lambda e: None)
    root.bind_class("Treeview", "<Button-3>", lambda e: list_menu(app, e), add="+")
    for seq in ("<Shift-F10>", "<KeyPress-App>", "<KeyPress-Menu>"):    # 2.36.0: menus without a mouse
        try:
            root.bind_all(seq, menu_key, add="+")
        except tk.TclError:
            pass
    root.bind_class("Treeview", "<Control-c>", lambda e: copy_rows(e.widget) and "break", add="+")
    root.bind_class("Treeview", "<Control-C>", lambda e: copy_rows(e.widget) and "break", add="+")
    for ev in ("<<TreeviewOpen>>", "<<TreeviewClose>>"):
        root.bind_class("Treeview", ev, lambda e: schedule_restripe(e.widget), add="+")


def open_poe2db():
    try:
        webbrowser.open(POE2DB_URL)
        return True
    except Exception:
        return False
