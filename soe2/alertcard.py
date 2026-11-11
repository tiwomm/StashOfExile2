"""2.130.0 Helper alerts as one alert card (feedback: "a more elegant solution than just giant bold flashing letters,
that's gonna piss some people off"): a small card over the game in the overlay's Style - a colored edge, a mark (! or
✓) and a word, a line of detail, × to close it early and a thin line counting down its time. No flashing: it fades in
once. Where it shows (Center, Above the bar, Top center, Top right) and its size (Small, Medium, Large) are settings
(Game Overlay › Settings › Helpers › Alerts). Every helper's alert and the break reminders use it.
2.131.4: alerts that come together share one card - a row each, most urgent on top, one countdown."""
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


def no_focus(win):
    """Windows: the card never takes the keyboard from the game (its × still takes a click)."""
    import sys
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from .alerts_page import _hwnd
        u = ctypes.windll.user32
        u.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        u.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
        h = _hwnd(win)
        u.SetWindowLongW(h, -20, u.GetWindowLongW(h, -20) | 0x80 | 0x08000000)    # tool window, no activate
    except Exception:
        buglog.caught()


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


class _Text:
    """A row's title / detail / × as the card shows it (cget / config like a Label; config redraws the card)."""

    def __init__(self, row, text):
        self.row, self.text = row, text

    def cget(self, key):
        return self.text if key == "text" else ""

    def config(self, **kw):
        if "text" in kw:
            self.text = kw["text"]
            self.row.card.render()
    configure = config


class Row:
    """2.131.4 one alert in the card -> what show() gives back. Reads like the card's window (winfo_x, attributes...)
    so a caller can keep it as "the alert"; destroy() takes this one away quietly, card_close() as its × does."""

    def __init__(self, card, title, sub, color, mark, secs, tag, rank, on_close):
        self.card, self.color, self.mark, self.secs, self.tag, self.rank = card, color, mark, secs, tag, rank
        self.on_close = on_close
        self.card_title, self.card_x = _Text(self, title), _Text(self, "×")
        self.card_sub = _Text(self, sub) if sub else None

    def __getattr__(self, name):                     # the rest is the card's window
        return getattr(self.__dict__["card"].win, name)

    def winfo_exists(self):
        return self in self.card.rows and self.card.alive()

    def destroy(self):
        self.card.drop(self, quiet=True)

    def card_close(self, _e=None):
        self.card.drop(self)


class Card:
    """2.131.4 (feedback: "people getting annoyed with 3 cards back to back"): one card for every alert that's up.
    An alert that comes while it shows joins it as a row - most urgent on top, one countdown (it starts again), × on a
    row closes that one, × at the top closes them all. One alone looks just as before."""

    def __init__(self, root):
        self.root, self.rows, self.win, self.game = root, [], None, None
        self.left = self.total = 0
        self.job = None

    def alive(self):
        try:
            return self.win is not None and bool(self.win.winfo_exists())
        except tk.TclError:
            return False

    def add(self, row, game):
        self.rows.append(row)
        self.rows.sort(key=lambda r: r.rank)              # (stable: same rank keeps the order they came)
        self.game = game
        self.left = self.total = max(self.left, int(row.secs * 1000), 1)
        new = not self.alive()
        if new:
            self.make()
        self.render()
        if new:
            self.win.after(35, self.fade)
            self.tick()

    def make(self):
        win = self.win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        try:
            win.attributes("-topmost", True)
            win.attributes("-alpha", FADE[0])
        except tk.TclError:
            pass

    def fade(self, i=1):
        if i < len(FADE) and self.alive():
            try:
                self.win.attributes("-alpha", FADE[i])
            except tk.TclError:
                return
            self.win.after(35, lambda: self.fade(i + 1))

    def drop(self, row, quiet=False):
        if row not in self.rows:
            return
        self.rows.remove(row)
        if not self.rows:
            self.end()
        else:
            self.render()
        if not quiet and row.on_close:
            try:
                row.on_close()
            except Exception:
                buglog.caught()

    def close_all(self, _e=None):
        for r in list(self.rows):
            self.drop(r)

    def end(self):
        self.rows = []
        w, self.win, self.left = self.win, None, 0
        try:
            if w is not None and w.winfo_exists():
                w.destroy()
        except tk.TclError:
            pass

    def tick(self):
        if not self.alive() or not self.rows:
            return
        if self.left <= 0:
            return self.close_all()
        try:
            bw = self.bar.winfo_width()
            self.bar.delete("all")
            self.bar.create_rectangle(0, 0, int(bw * self.left / max(1, self.total)), 2,
                                      fill=self.rows[0].color, outline="")
        except tk.TclError:
            return
        self.left -= 100
        self.win.after(100, self.tick)

    def render(self):
        """(Re)draw the card from its rows."""
        if not self.alive() or not self.rows:
            return
        from .overlaywin import pal
        from .style import Tooltip
        P = pal()
        c = cfg()
        k = SIZES[c["size"]][1]
        game = self.game or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        ui = max(0.6, game[3] / 1440.0) * k
        BG, TXT, MUT = P.get("bg", "#15111c"), P.get("big") or P.get("text", "#ece6f5"), P.get("muted", "#b3a9c6")
        LINE = P.get("rim") or P.get("line", "#3a3048")
        hfont, font = P.get("hfont") or "Segoe UI", P.get("font") or "Segoe UI"
        win = self.win
        for ch in win.winfo_children():
            ch.destroy()
        top = self.rows[0]
        many = len(self.rows) > 1
        box = tk.Frame(win, bg=BG, highlightthickness=1, highlightbackground=LINE)
        box.pack(fill="both", expand=True)
        tk.Frame(box, bg=top.color, width=max(3, int(4 * ui))).pack(side="left", fill="y")
        body = tk.Frame(box, bg=BG, padx=int(12 * ui), pady=int(9 * ui))
        body.pack(side="left", fill="both", expand=True)

        def xbutton(parent, tip, act, size=16):
            x = tk.Label(parent, text="×", bg=BG, fg=MUT, font=(font, -int(size * ui)), cursor="hand2", padx=4)
            x.pack(side="right", anchor="n", padx=(int(10 * ui), 0))
            x.bind("<Button-1>", act)
            x.bind("<Enter>", lambda _e=None: x.config(fg=TXT), add="+")
            x.bind("<Leave>", lambda _e=None: x.config(fg=MUT), add="+")
            Tooltip(x, tip)
            return x
        if many:
            head = tk.Frame(body, bg=BG)
            head.pack(fill="x", pady=(0, int(4 * ui)))
            self.head = tk.Label(head, text=f"{len(self.rows)} alerts", bg=BG, fg=TXT,
                                 font=(hfont, -int(19 * ui), "bold"), anchor="w")
            self.head.pack(side="left")
            xbutton(head, "Close all", self.close_all)
        else:
            self.head = None
        shown = self.rows[:MAX_ROWS]
        for i, r in enumerate(shown):
            if many:
                tk.Frame(body, bg=LINE, height=1).pack(fill="x")
            row = tk.Frame(body, bg=BG)
            row.pack(fill="x", pady=(int(6 * ui), int(6 * ui)) if many else 0)
            tk.Label(row, text=r.mark, bg=r.color, fg="#120c0c", font=(font, -int(15 * ui), "bold"),
                     width=2).pack(side="left", padx=(0, int(10 * ui)))
            r.box = row
            xbutton(row, "Close this one" if many else "Close", r.card_close, 14 if many else 16)
            if many and r.tag:
                tk.Label(row, text=r.tag, bg=BG, fg=MUT, font=(font, -int(11 * ui)), padx=int(5 * ui),
                         highlightthickness=1, highlightbackground=LINE).pack(side="right", anchor="n")
            txt = tk.Frame(row, bg=BG)
            txt.pack(side="left", fill="x", expand=True)
            tk.Label(txt, text=r.card_title.text, bg=BG, fg=TXT, anchor="w", justify="left",
                     font=(hfont, -int((16 if many else 19) * ui), "bold")).pack(fill="x")
            if r.card_sub is not None:
                tk.Label(txt, text=r.card_sub.text, bg=BG, fg=MUT, anchor="w", justify="left",
                         font=(font, -int((12 if many else 14) * ui))).pack(fill="x")
        more = len(self.rows) - len(shown)
        if more:
            tk.Label(body, text=f"+{more} more - close one to see it", bg=BG, fg=MUT, anchor="w",
                     font=(font, -int(12 * ui))).pack(fill="x", pady=(int(2 * ui), 0))
        self.bar = tk.Canvas(body, height=2, bg=BG, highlightthickness=0)
        self.bar.pack(fill="x", pady=(int(8 * ui), 0))
        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        px, py = place(c["where"], game, w, h)
        win.geometry(f"{w}x{h}+{int(px)}+{int(py)}")
        win.deiconify()
        try:
            from .alerts_page import force_topmost
            force_topmost(win)
            no_focus(win)
        except Exception:
            buglog.caught()


MAX_ROWS = 4
_CARDS = {}


def card(root):
    """The one alert card of this app."""
    c = _CARDS.get(str(root))
    if c is None or c.root is not root:
        c = _CARDS[str(root)] = Card(root)
    return c


def show(root, title, sub="", color="#ffb347", mark="!", secs=8, game=None, on_close=None, tag="", rank=5):
    """An alert -> its Row (reads like the card's window). Joins the card when one is up. game: (x, y, w, h) of the
    game (None: the screen). tag: the helper's name, shown on its row when there are more than one. rank: lower is
    more urgent (it goes higher)."""
    if game is None:
        game = (0, 0, root.winfo_screenwidth(), root.winfo_screenheight())
    cd = card(root)
    row = Row(cd, title, sub, color, mark, secs, tag, rank, on_close)
    cd.add(row, game)
    return row
