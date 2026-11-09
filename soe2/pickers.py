"""2.118.0: one picker for Settings › Appearance - a list of names (grouped) beside a big live preview, with one line
about the one shown. Hovering a name (or tabbing to it) previews it without changing anything; a click, Enter or Space
picks it. Leaving the list shows the one in use again. Used by the app theme (ThemePicker, themepick.py) and the
overlay style (StylePicker, ovstylepick.py) - feedback: "theme previews should work like the overlay style previews".

The preview is drawn by `render(host, key)` into an empty Frame; a quick run of hovers draws only the last one
(DELAY ms after the mouse stops). GGG ToS: it only draws in the app's own window."""
import tkinter as tk

from . import buglog
from .style import C

DELAY = 60                        # ms: hovering across the list draws only where the mouse stops


class ListPreview(tk.Frame):
    """groups: [(title, [(key, name), ...])]; render(host, key) draws key's preview into host; about(key) -> one line;
    on_pick(key) is called when one is clicked."""

    def __init__(self, parent, groups, current, on_pick, render, about=None, cols=2, name_width=12,
                 preview_width=None):
        super().__init__(parent, bg=C["panel2"])
        self.groups, self.current, self.on_pick, self.render = groups, current, on_pick, render
        self.about_of = about or (lambda _k: "")
        self.names = {k: n for _t, items in groups for k, n in items}
        self.rows, self.shown, self._job = {}, None, None
        left = tk.Frame(self, bg=C["panel2"])
        left.pack(side="left", fill="y", anchor="n")
        for title, items in groups:
            tk.Label(left, text=title.upper(), bg=C["panel2"], fg=C["muted"], font=("Segoe UI", 9, "bold"),
                     anchor="w").pack(fill="x", pady=(8, 1))
            box = tk.Frame(left, bg=C["panel2"])
            box.pack(fill="x")
            for i, (k, name) in enumerate(items):
                lab = tk.Label(box, text=name, bg=C["panel2"], fg=C["text"], anchor="w", padx=8, pady=2,
                               cursor="hand2", font=("Segoe UI", 10), width=name_width, takefocus=1)
                lab.grid(row=i // cols, column=i % cols, sticky="w")
                lab.bind("<Enter>", lambda e, k=k: self.hover(k))
                lab.bind("<FocusIn>", lambda e, k=k: self.hover(k))
                lab.bind("<Button-1>", lambda e, k=k: self.pick(k))
                lab.bind("<Return>", lambda e, k=k: self.pick(k))
                lab.bind("<space>", lambda e, k=k: self.pick(k))
                self.rows[k] = lab
        left.bind("<Leave>", lambda e: self.hover(self.current))
        right = tk.Frame(self, bg=C["panel2"])
        right.pack(side="left", fill="both", expand=True, padx=(16, 0), anchor="n")
        self.host = tk.Frame(right, bg=C["panel2"])
        if preview_width:
            self.host.configure(width=preview_width)
        self.host.pack(anchor="w", pady=(8, 4))
        self.name = tk.Label(right, text="", bg=C["panel2"], fg=C["text"], font=("Segoe UI", 10, "bold"), anchor="w")
        self.name.pack(fill="x")
        self.about = tk.Label(right, text="", bg=C["panel2"], fg=C["muted"], font=("Segoe UI", 9), anchor="w",
                              justify="left", wraplength=preview_width or 460)
        self.about.pack(fill="x")
        self.about.bind("<Configure>", lambda e: None)    # 2.125.1: keeps its own wrap (style._rewrap and the held
        self.name.bind("<Configure>", lambda e: None)     # preview size re-wrapped it back and forth - a freeze)
        self.paint()
        self.show(current)

    # ---- what's lit, what's shown
    def paint(self):
        for k, lab in self.rows.items():
            on = k == self.current
            try:
                lab.config(fg=C["accent"] if on else C["text"], font=("Segoe UI", 10, "bold" if on else "normal"))
            except tk.TclError:
                pass

    def hover(self, key):
        """Show `key` once the mouse rests (a sweep across the list draws only the last one)."""
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
        try:
            self._job = self.after(DELAY, lambda: self.show(key))
        except tk.TclError:
            self._job = None

    def show(self, key):
        self._job = None
        if key != self.shown:
            self.shown = key
            try:
                self.render(self.host, key)
            except Exception:
                buglog.caught()
                for c in self.host.winfo_children():
                    c.destroy()
            try:
                self.after(40, self._hold_size)           # 2.125.1: measured once Tk has laid it out (no
            except tk.TclError:                           # update_idletasks here - it ran the loop until a freeze)
                pass
        try:
            self.name.config(text=self.names.get(key, key) + ("  - in use" if key == self.current else
                                                                "  - click to use it"))
            self.about.config(text=self.about_of(key))
        except tk.TclError:
            pass

    def _hold_size(self):
        """2.124.1 (feedback: the text under the preview flickered): the preview keeps the biggest size it has needed,
        so a shorter one doesn't pull the list up under the mouse (Leave -> the one in use -> Enter -> ... a loop)."""
        try:
            kids = self.host.winfo_children()
            need_w = max([c.winfo_reqwidth() for c in kids] or [0])
            need_h = sum(c.winfo_reqheight() for c in kids)
            if need_w < 40 or need_h < 16:                # (not laid out yet - nothing held)
                return
            w = max(getattr(self, "_max_w", 0), need_w)
            h = max(getattr(self, "_max_h", 0), need_h)
            if (w, h) == (getattr(self, "_max_w", None), getattr(self, "_max_h", None)) and \
                    not self.host.pack_propagate():
                return                                    # (nothing to change)
            self._max_w, self._max_h = w, h
            self.host.pack_propagate(False)
            self.host.configure(width=max(1, w), height=max(1, h))
        except tk.TclError:
            pass

    def pick(self, key):
        if key == self.current:
            return
        self.current = key
        self.paint()
        self.show(key)
        self.on_pick(key)

    def set(self, key, redraw=False):
        """Picked somewhere else (or its look changed, redraw=True): show it here too."""
        self.current = key
        if redraw:
            self.shown = None
            self._max_w = self._max_h = 0            # (another layout: its own size)
        self.paint()
        self.show(key)
