"""2.116.0 (P10, feedback: the overlay styles had cards "for a visual indicator ... if you can figure out a better
system, go for it"): Settings › Appearance › Overlay style - the 14 styles as a list of names (grouped: Classic,
Light, Ornate) beside a big live preview of the bar drawn in the style under the mouse (or the one picked), with
one line about it. Hovering previews without changing anything; a click (or Enter / arrow keys) picks it - the
overlay over the game changes at once, as the old dropdown did. The preview takes each style's real colours and
fonts (ovlight.palette / ovskins.palette / hudart), not a mock-up.
GGG ToS: it only draws in the app's own window."""
import tkinter as tk

from .style import C

GROUPS = (("Classic", ("classic",)), ("Light", ("hairline", "slate", "flanks", "micro")),
          ("Ornate", ("herald", "gilded", "warbanner", "verdant", "gloom", "totem", "hellfire", "psionic", "guildhall")))
ABOUT = {
    "classic": "Carved stone and bronze, like the game's own bar. Takes your app theme's colours.",
    "hairline": "No box - one thin line under plain text. The lightest on the game and on the PC.",
    "slate": "A flat, quiet box.",
    "flanks": "No box: the numbers sit by the life orb, the switches by the mana orb.",
    "micro": "The smallest: a switch shows as its first letter.",
    "herald": "Crimson plates with gilt bevels.",
    "gilded": "White marble and gold leaf, umber text.",
    "warbanner": "A gold frame and royal-blue bands.",
    "verdant": "Forest green and aged bronze.",
    "gloom": "Smoky slate and pewter, pale text.",
    "totem": "Timber and red war banners.",
    "hellfire": "Rusted iron and ember gold.",
    "psionic": "Gold over deep-blue glass, cyan light.",
    "guildhall": "Oak, brass and parchment.",
}
SCENE = "#17130f"                 # a dark stretch of game behind the preview (box-less styles show what they're on)
W, H = 460, 74


def style_palette(style):
    """The colours and fonts the bar uses in this style (whatever style is picked now)."""
    from .ovlight import palette, DEFAULT_COLORS, ORNATE
    if style == "classic":
        from . import hudart
        from .overlaywin import theme_palette
        return hudart.palette(theme_palette())
    if style in ORNATE:
        from .ovskins import palette as ornate
        return ornate(style)
    P = palette(style, DEFAULT_COLORS)
    if P.get("boxless"):
        P = dict(P, bg=SCENE, band=SCENE)
    return P


def draw(cv, style):
    """The bar in `style` on canvas cv (W x H): the timer, three switches, Notes - as it looks over the game."""
    cv.delete("all")
    P = style_palette(style)
    cv.create_rectangle(0, 0, W, H, fill=SCENE, width=0)
    for i in range(0, W, 23):                                         # a hint of floor under it
        cv.create_line(i, H, i + 30, H - 30, fill="#1d1813")
    font = P.get("font") or "Segoe UI"
    body = P.get("body") or font
    boxless = style in ("hairline", "flanks") or bool(P.get("boxless"))
    x0, y0, x1, y1 = 14, 18, W - 14, H - 14
    if style == "flanks":
        pass                                                          # (no box: numbers left, switches right)
    elif style == "hairline":
        cv.create_line(x0, y1, x1, y1, fill=P.get("line") or P["muted"])
    elif not boxless:
        cv.create_rectangle(x0, y0, x1, y1, fill=P.get("band") or P["bg"], outline=P.get("leather") or P["line"],
                            width=2 if P.get("skin") or style == "classic" else 1)
        if P.get("skin") or style == "classic":
            cv.create_rectangle(x0 + 3, y0 + 3, x1 - 3, y1 - 3, outline=P.get("line") or P["muted"], width=1)
    mid = (y0 + y1) // 2
    small = style == "micro"
    size = 9 if small else 11
    t = cv.create_text(x0 + 12, mid, text="Map  3:12", anchor="w", fill=P["text"], font=(body, size))
    x = cv.bbox(t)[2] + 18
    if style == "flanks":
        x = x1 - 230
    for name, on in (("Breach", True), ("Delirium", False), ("Ritual", True)):
        label = name[0] if small else name
        txt = (P.get("on_icon", "◆") if on else P.get("off_icon", "◇")) + " " + label
        t = cv.create_text(x, mid, text=txt, anchor="w", fill=P.get("on") if on else P.get("off") or P["muted"],
                           font=(font, size, "bold" if on else "normal"))
        x = cv.bbox(t)[2] + (8 if small else 14)
    cv.create_text(x1 - 12, mid, text="N" if small else "Notes ▾", anchor="e", fill=P["muted"], font=(body, size))


class StylePicker(tk.Frame):
    """The list of style names and the preview. on_pick(style) is called when one is clicked."""

    def __init__(self, parent, current, on_pick):
        super().__init__(parent, bg=C["panel2"])
        from .ovlight import STYLES
        self.styles, self.on_pick, self.current = STYLES, on_pick, current
        self.rows = {}
        left = tk.Frame(self, bg=C["panel2"])
        left.pack(side="left", fill="y")
        for title, keys in GROUPS:
            tk.Label(left, text=title.upper(), bg=C["panel2"], fg=C["muted"], font=("Segoe UI", 9, "bold"),
                     anchor="w").pack(fill="x", pady=(8, 1))
            box = tk.Frame(left, bg=C["panel2"])
            box.pack(fill="x")
            for i, k in enumerate(keys):
                name = STYLES[k].split(" (")[0]
                lab = tk.Label(box, text=name, bg=C["panel2"], fg=C["text"], anchor="w", padx=8, pady=2,
                               cursor="hand2", font=("Segoe UI", 10), width=11, takefocus=1)
                lab.grid(row=i // 2, column=i % 2, sticky="w")
                lab.bind("<Enter>", lambda e, k=k: self.show(k))
                lab.bind("<Leave>", lambda e: self.show(self.current))
                lab.bind("<Button-1>", lambda e, k=k: self.pick(k))
                lab.bind("<Return>", lambda e, k=k: self.pick(k))
                lab.bind("<FocusIn>", lambda e, k=k: self.show(k))
                self.rows[k] = lab
        right = tk.Frame(self, bg=C["panel2"])
        right.pack(side="left", fill="both", expand=True, padx=(16, 0))
        self.cv = tk.Canvas(right, width=W, height=H, highlightthickness=1, highlightbackground=C["line"], bd=0)
        self.cv.pack(anchor="w", pady=(8, 4))
        self.name = tk.Label(right, text="", bg=C["panel2"], fg=C["text"], font=("Segoe UI", 10, "bold"), anchor="w")
        self.name.pack(fill="x")
        self.about = tk.Label(right, text="", bg=C["panel2"], fg=C["muted"], font=("Segoe UI", 9), anchor="w",
                              justify="left", wraplength=W)
        self.about.pack(fill="x")
        self.paint()
        self.show(current)

    def paint(self):
        for k, lab in self.rows.items():
            on = k == self.current
            lab.config(fg=C["accent"] if on else C["text"], font=("Segoe UI", 10, "bold" if on else "normal"))

    def show(self, style):
        try:
            draw(self.cv, style)
        except Exception:
            self.cv.delete("all")
        name = self.styles.get(style, style).split(" (")[0]
        self.name.config(text=name + ("  - in use" if style == self.current else "  - click to use it"))
        self.about.config(text=ABOUT.get(style, ""))

    def pick(self, style):
        if style == self.current:
            return
        self.current = style
        self.paint()
        self.show(style)
        self.on_pick(style)

    def set(self, style):
        """Picked somewhere else (the cog's Style list): show it here too."""
        self.current = style
        self.paint()
        self.show(style)
