"""2.130.0 Helper alerts as one calm card (feedback: "a more elegant solution than just giant bold flashing letters,
that's gonna piss some people off"): a small card over the game in the overlay's Style - a colored edge, a mark (! or
✓) and a word, a line of detail, × to close it early and a thin line counting down its time. No flashing: it fades in
once. Where it shows (Center, Above the bar, Top center, Top right) and its size (Small, Medium, Large) are settings
(Game Overlay › Settings › Helpers › Alerts). Every helper's alert and the break reminders use it."""
import tkinter as tk

from . import buglog
from .config import SETTINGS

WHERE = {"center": "Center", "bar": "Above the bar", "top": "Top center", "topright": "Top right"}
SIZES = {"small": ("Small", 0.8), "medium": ("Medium", 1.0), "large": ("Large", 1.3)}
DEFAULTS = {"where": "center", "size": "medium"}
FADE = (0.25, 0.5, 0.75, 0.92, 1.0)        # the fade in, one step every 35 ms


def cfg():
    c = SETTINGS.setdefault("alert_card", {})
    for k, v in DEFAULTS.items():
        c.setdefault(k, v)
    if c["where"] not in WHERE:
        c["where"] = DEFAULTS["where"]
    if c["size"] not in SIZES:
        c["size"] = DEFAULTS["size"]
    return c


def place(where, game, w, h):
    """Where the card goes over the game (x, y of its top-left)."""
    gx, gy, gw, gh = game
    if where == "bar":                                  # just above the overlay's bar, on the XP bar
        return gx + (gw - w) // 2, gy + int(gh * 0.86) - h
    if where == "top":
        return gx + (gw - w) // 2, gy + int(gh * 0.07)
    if where == "topright":                             # left of the minimap
        return gx + int(gw * 0.80) - w, gy + int(gh * 0.07)
    return gx + (gw - w) // 2, gy + int(gh * 0.40) - h // 2


def show(root, title, sub="", color="#ffb347", mark="!", secs=8, game=None, on_close=None):
    """The card -> its window (a Toplevel). game: (x, y, w, h) of the game (None: the screen)."""
    from .overlaywin import pal
    P = pal()
    c = cfg()
    k = SIZES[c["size"]][1]
    if game is None:
        game = (0, 0, root.winfo_screenwidth(), root.winfo_screenheight())
    ui = max(0.6, game[3] / 1440.0) * k
    BG, TXT, MUT = P.get("bg", "#15111c"), P.get("big") or P.get("text", "#ece6f5"), P.get("muted", "#b3a9c6")
    LINE = P.get("rim") or P.get("line", "#3a3048")
    hfont, font = P.get("hfont") or "Segoe UI", P.get("font") or "Segoe UI"
    win = tk.Toplevel(root)
    win.withdraw()
    win.overrideredirect(True)
    try:
        win.attributes("-topmost", True)
        win.attributes("-alpha", FADE[0])
    except tk.TclError:
        pass
    box = tk.Frame(win, bg=BG, highlightthickness=1, highlightbackground=LINE)
    box.pack(fill="both", expand=True)
    tk.Frame(box, bg=color, width=max(3, int(4 * ui))).pack(side="left", fill="y")
    body = tk.Frame(box, bg=BG, padx=int(12 * ui), pady=int(9 * ui))
    body.pack(side="left", fill="both", expand=True)
    row = tk.Frame(body, bg=BG)
    row.pack(fill="x")
    ico = tk.Label(row, text=mark, bg=color, fg="#120c0c", font=(font, -int(15 * ui), "bold"), width=2)
    ico.pack(side="left", padx=(0, int(10 * ui)))
    txt = tk.Frame(row, bg=BG)
    txt.pack(side="left", fill="x", expand=True)
    tl = tk.Label(txt, text=title, bg=BG, fg=TXT, font=(hfont, -int(19 * ui), "bold"), anchor="w")
    tl.pack(fill="x")
    sl = None
    if sub:
        sl = tk.Label(txt, text=sub, bg=BG, fg=MUT, font=(font, -int(14 * ui)), anchor="w")
        sl.pack(fill="x")
    x = tk.Label(row, text="×", bg=BG, fg=MUT, font=(font, -int(16 * ui)), cursor="hand2", padx=4)
    x.pack(side="right", anchor="n", padx=(int(14 * ui), 0))
    bar = tk.Canvas(body, height=2, bg=BG, highlightthickness=0)
    bar.pack(fill="x", pady=(int(8 * ui), 0))
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    px, py = place(c["where"], game, w, h)
    win.geometry(f"+{int(px)}+{int(py)}")
    win.deiconify()
    try:
        from .alerts_page import force_topmost
        force_topmost(win)
    except Exception:
        buglog.caught()

    def close(_e=None):
        try:
            if win.winfo_exists():
                win.destroy()
        except tk.TclError:
            pass
        if on_close:
            try:
                on_close()
            except Exception:
                buglog.caught()
    x.bind("<Button-1>", close)
    x.bind("<Enter>", lambda _e: x.config(fg=TXT))
    x.bind("<Leave>", lambda _e: x.config(fg=MUT))

    def fade(i=1):
        if i < len(FADE) and win.winfo_exists():
            try:
                win.attributes("-alpha", FADE[i])
            except tk.TclError:
                return
            win.after(35, lambda: fade(i + 1))
    win.after(35, fade)
    total = max(1, int(secs * 1000))
    step = 100

    def tick(left=total):
        if not win.winfo_exists():
            return
        if left <= 0:
            return close()
        try:
            bw = bar.winfo_width()
            bar.delete("all")
            bar.create_rectangle(0, 0, int(bw * left / total), 2, fill=color, outline="")
        except tk.TclError:
            return
        win.after(step, lambda: tick(left - step))
    tick()
    win.card_close, win.card_title, win.card_sub, win.card_x = close, tl, sl, x
    return win
