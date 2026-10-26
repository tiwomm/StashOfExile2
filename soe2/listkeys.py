"""Lists that behave the same everywhere (2.4.0).

Every list in the app takes:
  click              select one row
  Ctrl+click         add / remove a row
  Shift+click        select everything between
  Ctrl+A             select every row
  Delete             remove the selected rows (where removing makes sense)
  Ctrl+Z             undo the last removal in that window (also the Undo button where there is one)

Keys go to the list you last clicked in the window that's in front (each window keeps its own). Typing in a box keeps
the usual meaning of those keys. Undo keeps the last 20 removals per window, until the app closes."""
import tkinter as tk

UNDO_DEPTH = 20


class ListKeys:
    """Mixed into App."""

    def _lk_init(self):
        if not hasattr(self, "_lk_lists"):
            self._lk_lists, self._lk_last, self._lk_undo = {}, {}, {}

    def list_register(self, key, tree, delete=None, multi=True):
        """Make `tree` (in the window `key`) behave like every other list. delete(rows) removes the selected rows."""
        self._lk_init()
        if multi:
            try:
                tree.configure(selectmode="extended")
            except tk.TclError:
                pass
        lst = self._lk_lists.setdefault(key, [])
        lst[:] = [(t, d) for t, d in lst if _alive(t)]           # lists that are rebuilt leave their old copy behind
        lst.append((tree, delete))
        tree.bind("<ButtonPress-1>", lambda e, k=key, t=tree: self._lk_clicked(k, t), add="+")

    def _lk_clicked(self, key, tree):
        self._lk_last[key] = tree
        try:
            tree.focus_set()
        except tk.TclError:
            pass

    def list_target(self, key):
        """The list Ctrl+A / Delete act on in window `key`: the one you last clicked, else the first one on screen."""
        self._lk_init()
        lists = [(t, d) for t, d in self._lk_lists.get(key, []) if _alive(t)]
        last = self._lk_last.get(key)
        for t, d in lists:
            if t is last and t.winfo_ismapped():
                return t, d
        for t, d in lists:
            if t.winfo_ismapped():
                return t, d
        return None, None

    def list_key(self, key, action):
        """Ctrl+A / Delete / Ctrl+Z in window `key` (not the Price checks window: it has its own)."""
        if action == "undo":
            return self.undo_last(key) or True
        tree, delete = self.list_target(key)
        if tree is None:
            return False
        if action == "all":
            kids = tree.get_children()
            if kids and str(tree.cget("selectmode")) == "extended":
                tree.selection_set(kids)
            return True
        if action == "delete" and delete is not None:
            sel = tree.selection()
            if sel:
                delete(sel)
            return True
        return False

    # ---- undo, per window
    def push_undo(self, key, label, restore):
        """Remember how to put back what was just removed. label: what it was ("3 counted stacks")."""
        self._lk_init()
        st = self._lk_undo.setdefault(key, [])
        st.append((label, restore))
        del st[:-UNDO_DEPTH]
        self.undo_changed(key)

    def can_undo(self, key):
        self._lk_init()
        return bool(self._lk_undo.get(key))

    def undo_last(self, key):
        self._lk_init()
        st = self._lk_undo.get(key)
        if not st:
            self.undo_say(key, "Nothing to undo.")
            return False
        label, restore = st.pop()
        restore()
        self.undo_say(key, f"Undone: {label} back.")
        self.undo_changed(key)
        return True

    def undo_say(self, key, text):
        tell = {"wealth": lambda t: self._w_tell(t, "ok")}.get(key)
        if tell:
            return tell(text)
        try:
            self._say(text, 6)
        except Exception:
            pass

    def undo_changed(self, key):
        """Undo buttons follow whether there's something to undo."""
        for btn in getattr(self, "_undo_btns", {}).get(key, []):
            try:
                btn.config(state="normal" if self.can_undo(key) else "disabled")
            except tk.TclError:
                pass

    def undo_button(self, parent, key, **pack):
        from tkinter import ttk
        b = ttk.Button(parent, text="↶ Undo", command=lambda: self.undo_last(key), state="disabled")
        self.__dict__.setdefault("_undo_btns", {}).setdefault(key, []).append(b)
        return b


def _alive(w):
    try:
        return bool(w.winfo_exists())
    except tk.TclError:
        return False
