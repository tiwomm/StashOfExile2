"""The desktop (2.0 beta 7): every module and utility in its own window inside the app, a dock down the left, the
Toolkit menu, and a taskbar. The shell knows nothing about what the windows hold: modules (soe2/modules) build their
own content into the window they are given.

  Desktop  - the area the windows live in, with the wallpaper (a dark gradient, or an image you pick in Settings)
  Dock     - the orb (opens the Toolkit menu), one button per module, one per utility (with an on/off dot), Settings
  Taskbar  - a button per open window (click: bring to front / restore), league, searches, utility dots, clock
  Window   - title bar (drag), minimise to the taskbar, maximise, close (hides it; utilities keep running), resize corner

Window positions, sizes and which ones are open are saved in settings.json ("shell")."""
import sys
import time
import tkinter as tk

from .style import C

TITLE_ON = ("#34508a", "#1a2a4c")
TITLE_OFF = ("#26324a", "#182236")
UTIL_TITLE = ("#3a3020", "#1e1810")
DOCK_W = 96
KINDS = (("module", "MODULES"), ("tool", "TOOLS"), ("utility", "UTILITIES"))
# tile colours per kind: fill, fill under the mouse, edge, gloss line
TILE = {"module": ("#22396a", "#2e4c88", "#5b77ad", "#3f5f9e"), "tool": ("#173836", "#21504c", "#3f9a90", "#2c5c58"),
        "utility": ("#2a2416", "#3a3220", "#a8741a", "#4a3c22")}
EDGE = 5                        # the resize border around every window
BORDER_ON, BORDER_OFF = "#2c4372", "#1c2840"
TASK_H = 40
MIN_W, MIN_H = 320, 200


CLOCK = {"format": "auto"}       # 2.0 beta 21: "auto" (like Windows), "12" or "24" (Settings > Appearance)


def windows_24h():
    """Does Windows show the time as 24-hour? (Control Panel > Region; read once.)"""
    if "win24" not in CLOCK:
        CLOCK["win24"] = False                      # 12-hour unless Windows is set to 24-hour (2.1.0)
        if sys.platform == "win32":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\International") as k:
                    CLOCK["win24"] = str(winreg.QueryValueEx(k, "iTime")[0]) == "1"
            except Exception:
                pass
    return CLOCK["win24"]


def clock_text(now=None):
    """The taskbar clock, like Windows': time on top, date under it. Your PC's own clock and time zone."""
    t = time.localtime(now)
    fmt = CLOCK.get("format", "auto")
    h24 = windows_24h() if fmt == "auto" else fmt == "24"
    clock = time.strftime("%H:%M", t) if h24 else time.strftime("%I:%M %p", t).lstrip("0")
    return f"{clock}\n{time.strftime('%a %b', t)} {t.tm_mday}"


def _blend(a, b, t):
    ra, rb = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


class GradientBar(tk.Canvas):
    """A canvas painted top-to-bottom from one colour to another (title bars, taskbar)."""

    def __init__(self, parent, height, colours, **kw):
        super().__init__(parent, height=height, highlightthickness=0, bd=0, bg=colours[1], **kw)
        self.colours = colours
        self.bind("<Configure>", lambda e: self.paint())

    def paint(self, colours=None):
        if colours:
            self.colours = colours
        self.delete("grad")
        h = max(1, self.winfo_height())
        w = self.winfo_width()
        steps = min(h, 24)
        for i in range(steps):
            y0, y1 = int(i * h / steps), int((i + 1) * h / steps)
            self.create_rectangle(0, y0, w, y1, outline="", fill=_blend(self.colours[0], self.colours[1], i / max(1, steps - 1)),
                                  tags="grad")
        self.tag_lower("grad")


class DeskWindow(tk.Toplevel):
    """One window on the desktop. body is where the module draws.

    2.0 beta 13: a real (borderless) window of its own, owned by the app's window, instead of a frame drawn inside it.
    Tk can't stack overlapping frames reliably on Windows (windows smeared when moved and didn't come to the front);
    real windows are moved, stacked and repainted by Windows itself. Positions are still kept relative to the desktop
    area, and the windows move with the app's window."""

    def __init__(self, shell, key, title, icon, utility=False):
        super().__init__(shell.root, bg=BORDER_OFF, highlightthickness=1, highlightbackground="#5b77ad")
        self.withdraw()
        self.overrideredirect(True)
        try:
            self.transient(shell.root)
        except tk.TclError:
            pass
        self.shell, self.key, self.title, self.icon, self.utility = shell, key, title, icon, utility
        self.inner = tk.Frame(self, bg=C["panel"])
        self.inner.pack(fill="both", expand=True, padx=EDGE, pady=EDGE)
        self.state_ = "closed"                 # closed / open / minimised
        self.maxed = False
        self.geo = None                        # [x, y, w, h] on the desktop (kept while closed / minimised / maximised)
        self._g = None                         # where it is now
        self._move_job = None
        colours = UTIL_TITLE if utility else TITLE_ON
        self.bar = GradientBar(self.inner, 30, colours)
        self.bar.pack(fill="x")
        self.accent = tk.Frame(self.inner, height=2, bg=C["accent"])
        self.accent.pack(fill="x")
        self.lbl = self.bar.create_text(10, 15, text=f"{icon}  {title}", anchor="w", fill="#ffffff",
                                        font=("Segoe UI", 10, "bold"))
        self.btns = []
        for txt, cmd, bg in (("×", self.close, "#7a2a20"), ("□", self.toggle_max, "#22345a"), ("_", self.minimise, "#22345a")):
            b = tk.Label(self.bar, text=txt, bg=bg, fg="#cfe0ff", font=("Segoe UI", 9, "bold"), width=2,
                         highlightthickness=1, highlightbackground="#5b77ad", cursor="hand2")
            b.bind("<Button-1>", lambda e, c=cmd: c())
            self.btns.append(self.bar.create_window(0, 15, window=b, anchor="e"))
        self.bar.bind("<Configure>", self._bar_resized, add="+")
        self.bar.bind("<ButtonPress-1>", self._press)
        self.bar.bind("<B1-Motion>", self._drag)
        self.bar.bind("<ButtonRelease-1>", lambda e: self._drop())
        self.bar.bind("<Double-1>", lambda e: self.toggle_max())
        self.body = tk.Frame(self.inner, bg=C["panel"])
        self.body.pack(fill="both", expand=True)
        self.grip = tk.Label(self.inner, text="◢", bg=C["panel"], fg=C["steel"], font=("Segoe UI", 8),
                             cursor="bottom_right_corner")
        self.grip.place(relx=1.0, rely=1.0, anchor="se")
        self._resize_bind(self.grip, "se")
        # resize from any edge or corner, like a normal window
        c = 14
        self.handles = {}
        for side, cur, kw in (
                ("n", "sb_v_double_arrow", dict(x=0, y=0, relwidth=1, height=EDGE)),
                ("s", "sb_v_double_arrow", dict(x=0, rely=1, y=-EDGE, relwidth=1, height=EDGE)),
                ("w", "sb_h_double_arrow", dict(x=0, y=0, width=EDGE, relheight=1)),
                ("e", "sb_h_double_arrow", dict(relx=1, x=-EDGE, y=0, width=EDGE, relheight=1)),
                ("nw", "top_left_corner", dict(x=0, y=0, width=c, height=EDGE)),
                ("ne", "top_right_corner", dict(relx=1, x=-c, y=0, width=c, height=EDGE)),
                ("sw", "bottom_left_corner", dict(x=0, rely=1, y=-c, width=EDGE, height=c)),
                ("se", "bottom_right_corner", dict(relx=1, x=-EDGE, rely=1, y=-c, width=EDGE, height=c))):
            h = tk.Frame(self, bg=BORDER_OFF, cursor=cur)
            h.place(**kw)
            self._resize_bind(h, side)
            self.handles[side] = h
        for side, kw in (("nw", dict(x=0, y=0, width=EDGE, height=c)), ("ne", dict(relx=1, x=-EDGE, y=0, width=EDGE, height=c)),
                         ("sw", dict(x=0, rely=1, y=-EDGE, width=c, height=EDGE)),
                         ("se", dict(relx=1, x=-c, rely=1, y=-EDGE, width=c, height=EDGE))):
            h = tk.Frame(self, bg=BORDER_OFF, cursor=self.handles[side].cget("cursor"))      # the other arm of each corner
            h.place(**kw)
            self._resize_bind(h, side)
            self.handles[side + "2"] = h
        self.bind("<ButtonPress-1>", self._clicked, add="+")
        self._d = {}

    # ---- title bar
    def _bar_resized(self, _e=None):
        w = self.bar.winfo_width()
        for n, item in enumerate(self.btns):
            self.bar.coords(item, w - 6 - n * 30, 15)

    def set_active(self, on):
        if self.utility:
            colours = UTIL_TITLE if on else ("#2a2418", "#16120c")
        else:
            colours = TITLE_ON if on else TITLE_OFF
        self.bar.paint(colours)
        self.bar.itemconfigure(self.lbl, fill="#ffffff" if on else "#aab6cc")
        self.accent.config(bg=C["accent"] if on else "#2b3d5f")
        border = BORDER_ON if on else BORDER_OFF
        self.config(bg=border)
        for h in self.handles.values():
            h.config(bg=border)

    # ---- moving (the window itself follows the mouse: Windows moves it, nothing to repaint)
    def _press(self, e):
        self.shell.focus(self.key)
        g = self.current_geo()
        self._d = {"x": e.x_root - g[0], "y": e.y_root - g[1], "g": g, "to": None}

    def _drag(self, e):
        if self.maxed or "x" not in self._d:
            return
        dw, dh = self.shell.desk.winfo_width(), self.shell.desk.winfo_height()
        g = self._d["g"]
        # 2.0 beta 13: real windows aren't cut off at the desktop's edge, so they stay on it (never over the dock
        # or the taskbar)
        x = min(max(e.x_root - self._d["x"], 0), max(0, dw - g[2]))
        y = min(max(e.y_root - self._d["y"], 0), max(0, dh - g[3]))
        self._d["to"] = [x, y, g[2], g[3]]
        self._move_soon()

    def _move_soon(self):
        """Mouse moves come faster than the screen updates: move at most once per frame, to the newest spot."""
        if self._move_job is None:
            self._move_job = self.after(12, self._move_now)

    def _move_now(self):
        self._move_job = None
        to = self._d.get("to") if self._d else None
        if to and not self.maxed:
            self.place_at(*to)

    def _drop(self, _e=None):
        if self._move_job is not None:
            self.after_cancel(self._move_job)
            self._move_job = None
        to = self._d.get("to") if self._d else None
        if to and not self.maxed:
            self.place_at(*to)
        self._d = {}
        self.shell.save_layout()

    # ---- resizing (any edge / corner, and the ◢ grip)
    def _clicked(self, e):
        self.shell.click_focus(self.key)
        self.take_keyboard(e.widget)

    TYPING = ("Entry", "TEntry", "Text", "Spinbox", "TSpinbox", "TCombobox", "Listbox", "Treeview")

    def take_keyboard(self, widget=None):
        """2.0 beta 17: a borderless window doesn't always get the keyboard when you click it (Windows), so typing
        went nowhere. Clicking a window now hands it the keyboard: to the box you clicked if it takes typing."""
        try:
            f = self.focus_get()
        except (tk.TclError, KeyError):
            f = None
        try:
            if f is not None and f.winfo_toplevel() is self and (widget is None or f is widget):
                return                                            # it already has it
            if widget is not None and widget.winfo_class() in self.TYPING:
                widget.focus_force()
            elif f is None or f.winfo_toplevel() is not self:
                self.focus_force()
        except tk.TclError:
            pass

    def _resize_bind(self, widget, side):
        widget.bind("<ButtonPress-1>", lambda e: self._resize_press(e, side))
        widget.bind("<B1-Motion>", self._resize_drag)
        widget.bind("<ButtonRelease-1>", lambda e: self._drop())

    def _resize_press(self, e, side):
        self.shell.focus(self.key)
        self._d = {"side": side, "x0": e.x_root, "y0": e.y_root, "g": self.current_geo(), "to": None}

    def _resize_drag(self, e):
        d = self._d
        if self.maxed or "side" not in d or not d.get("g"):
            return
        x, y, w, h = d["g"]
        dw, dh = self.shell.desk.winfo_width(), self.shell.desk.winfo_height()
        dx, dy, side = e.x_root - d["x0"], e.y_root - d["y0"], d["side"]
        if "e" in side:
            w = max(MIN_W, min(w + dx, dw - x))
        if "s" in side:
            h = max(MIN_H, min(h + dy, dh - y))
        if "w" in side:
            nw = max(MIN_W, min(w - dx, x + w))
            x, w = x + w - nw, nw
        if "n" in side:
            nh = max(MIN_H, h - dy)
            ny = y + h - nh
            if ny < 0:                                   # never above the top of the desktop
                nh, ny = nh + ny, 0
            y, h = ny, nh
        d["to"] = [x, y, w, h]
        self._move_soon()

    # (older names, kept for tests and callers)
    def _grip_press(self, e):
        self._resize_press(e, "se")

    def _grip_drag(self, e):
        self._resize_drag(e)

    # ---- show / hide
    def place_at(self, x, y, w, h):
        """Put it at x, y (desktop coordinates), w x h."""
        x, y, w, h = int(x), int(y), int(w), int(h)
        self._g = [x, y, w, h]
        ox, oy = self.shell.desk_origin()
        self.geometry(f"{w}x{h}+{ox + x}+{oy + y}")

    def place_configure(self, **kw):          # (the old frame API, for callers that still use it)
        g = list(self._g or self.geo or [0, 0, MIN_W, MIN_H])
        for i, k in enumerate(("x", "y", "width", "height")):
            if k in kw:
                g[i] = kw[k]
        self.place_at(*g)

    def current_geo(self):
        if self.maxed:
            return self.geo
        return list(self._g) if self._g else self.geo

    def _show(self):
        self.deiconify()
        self.lift()

    def open(self):
        if self.state_ == "open":
            return
        if self.maxed:
            self.place_at(0, 0, self.shell.desk.winfo_width(), self.shell.desk.winfo_height())
        else:
            self.place_at(*self.shell.fit(self.geo or self.shell.default_geo(self)))
        self._show()
        self.state_ = "open"

    def reposition(self):
        """The app's window moved or changed size: follow it."""
        if self.state_ != "open":
            return
        if self.maxed:
            self.place_at(0, 0, self.shell.desk.winfo_width(), self.shell.desk.winfo_height())
        elif self._g:
            self.place_at(*self._g)

    def minimise(self):
        self.geo = self.current_geo()
        self.withdraw()
        self.state_ = "minimised"
        self.shell.after_change(self.key)

    def close(self):
        self.geo = self.current_geo()
        self.withdraw()
        self.state_ = "closed"
        self.shell.after_change(self.key)

    def toggle_max(self):
        if self.maxed:
            self.maxed = False
            self.place_at(*(self.geo or self.shell.default_geo(self)))
        else:
            self.geo = self.current_geo()
            self.maxed = True
            self.place_at(0, 0, self.shell.desk.winfo_width(), self.shell.desk.winfo_height())
        self.shell.focus(self.key)
        self.shell.save_layout()


class Shell:
    """Builds the desktop around the app. modules: list of objects with key, title, icon, kind ('module', 'utility',
    'core'), and optionally status() -> True / False / None (running dot for utilities)."""

    def __init__(self, app, root, settings, save):
        self.app, self.root, self.S, self.save = app, root, settings, save
        self.cfg = self.S.setdefault("shell", {})
        self.cfg.setdefault("windows", {})
        self.cfg.setdefault("desktop_icons", False)
        self.cfg.setdefault("launcher", "both" if self.cfg.get("desktop_icons") else "dock")     # 2.0 beta 21
        self.windows, self.modules, self.active = {}, {}, None
        self.taskbtns = {}
        # ---- layout: taskbar at the bottom, status strip above it, dock on the left, desktop fills the rest
        self.task = GradientBar(root, TASK_H, ("#1c2a47", "#0b1222"))
        self.task.pack(side="bottom", fill="x")
        self.task_inner = tk.Frame(self.task, bg="#111b30")
        self.task.create_window(DOCK_W + 6, TASK_H // 2, window=self.task_inner, anchor="w", tags="inner")
        self.task_right = tk.Frame(self.task, bg="#111b30")
        self.task_right_id = self.task.create_window(0, TASK_H // 2, window=self.task_right, anchor="e")
        self.task.bind("<Configure>", lambda e: self.task.coords(self.task_right_id, e.width - 8, TASK_H // 2), add="+")
        # Settings sits at the left end of the taskbar, under the dock (2.0 beta 15: where a Start button would be)
        t = self.task
        t.create_rectangle(8, 6, DOCK_W - 8, TASK_H - 6, fill="#1c2a47", outline="#3d5582", tags=("settings", "setbox"))
        t.create_text(DOCK_W // 2, TASK_H // 2, text="⚙  Settings", fill="#cfdaf0", font=("Segoe UI", 9, "bold"),
                      tags=("settings", "settxt"))
        t.tag_bind("settings", "<Button-1>", lambda e: self.open("settings"))
        t.tag_bind("settings", "<Enter>", lambda e: (t.config(cursor="hand2"), t.itemconfigure("setbox", fill="#2c4c8a",
                                                                                              outline=C["accent"])))
        t.tag_bind("settings", "<Leave>", lambda e: (t.config(cursor=""), t.itemconfigure("setbox", fill="#1c2a47",
                                                                                          outline="#3d5582")))
        # Toolkit on the taskbar too, while the dock is hidden (2.0 beta 21: Appearance > Launcher)
        x0 = DOCK_W
        t.create_rectangle(x0, 6, x0 + DOCK_W - 16, TASK_H - 6, fill="#3a2a12", outline=C["accent"],
                           tags=("tkbtn", "tkbox"), state="hidden")
        t.create_text(x0 + (DOCK_W - 16) // 2, TASK_H // 2, text="◆  Toolkit", fill="#ffd9a8",
                      font=("Segoe UI", 9, "bold"), tags=("tkbtn",), state="hidden")
        t.tag_bind("tkbtn", "<Button-1>", lambda e: self.toggle_menu())
        t.tag_bind("tkbtn", "<Enter>", lambda e: (t.config(cursor="hand2"), t.itemconfigure("tkbox", fill="#4e3816")))
        t.tag_bind("tkbtn", "<Leave>", lambda e: (t.config(cursor=""), t.itemconfigure("tkbox", fill="#3a2a12")))
        self.strip = tk.Frame(root, bg=C["bg"])
        self.strip.pack(side="bottom", fill="x")
        self.dock = tk.Canvas(root, bg="#0e1522", width=DOCK_W, highlightthickness=0, bd=0)
        self.dock.pack(side="left", fill="y")
        self.dock_sep = tk.Frame(root, bg="#3d5582", width=1)
        self.dock_sep.pack(side="left", fill="y")
        self.desk = tk.Canvas(root, bg="#0a0c12", highlightthickness=0, bd=0)
        self.desk.pack(side="left", fill="both", expand=True)
        self._wall_img, self._wall_job, self._wall_size = None, None, None
        self.desk.bind("<Configure>", self._desk_resized)
        self.root.bind("<Configure>", lambda e: e.widget is self.root and self._follow_soon(), add="+")
        self.icons = []
        self.orb = self.dock                    # clicks on the orb are part of the dock canvas (tag "orb")
        self.dock_btns, self.dots, self._dock_hover = {}, {}, None
        self.dock.bind("<Configure>", lambda e: self.draw_dock())
        self.menu = None
        self.clock = None
        self.root.bind_all("<ButtonPress-1>", self._any_click, add="+")
        self.root.after(1000, self._tick)

    # ---- the wallpaper
    def _desk_resized(self, e):
        if self._wall_job:
            self.root.after_cancel(self._wall_job)
        self._wall_job = self.root.after(150, self.paint_wallpaper)
        self._follow_soon()

    # ---- the windows are real windows (2.0 beta 13): keep them on the desktop area when the app moves / resizes
    def desk_origin(self):
        try:
            return self.desk.winfo_rootx(), self.desk.winfo_rooty()
        except tk.TclError:
            return 0, 0

    def _follow_soon(self, _e=None):
        if getattr(self, "_follow_job", None) is None:
            self._follow_job = self.root.after(15, self._follow)

    def _follow(self):
        self._follow_job = None
        org = self.desk_origin()
        size = (self.desk.winfo_width(), self.desk.winfo_height())
        if (org, size) == getattr(self, "_last_place", None):
            return
        self._last_place = (org, size)
        for w in self.windows.values():
            w.reposition()
        if self.menu is not None:
            self._place_menu()
        self.app_follow()

    def app_follow(self):
        """Pop-ups of the app that sit on the desktop (the what's new card) follow too."""
        fn = getattr(self.app, "whatsnew_follow", None)
        if fn:
            fn()

    def hide_all(self):
        """The app went to the tray / was minimised: its windows go with it."""
        self._all_hidden = True
        for w in self.windows.values():
            if w.state_ == "open":
                w.withdraw()
        if self.menu is not None:
            self.close_menu()

    def show_all(self):
        """Back from the tray: the windows that were open come back (2.0 beta 17: only after hide_all - showing the
        app's window for any other reason never pops windows up)."""
        if not getattr(self, "_all_hidden", False):
            return
        self._all_hidden = False
        for w in self.windows.values():
            if w.state_ == "open":
                w.reposition()
                w.deiconify()
        for k in getattr(self, "zorder", []):                  # back in the same stacking order
            w = self.windows.get(k)
            if w is not None and w.state_ == "open":
                w.lift()
        self.app_follow()

    def paint_wallpaper(self):
        self._wall_job = None
        w, h = max(2, self.desk.winfo_width()), max(2, self.desk.winfo_height())
        if self._wall_size == (w, h, self.cfg.get("wallpaper")):
            return
        self._wall_size = (w, h, self.cfg.get("wallpaper"))
        img = None
        try:
            from PIL import Image, ImageTk
            path = self.cfg.get("wallpaper")
            if path:
                try:
                    src = Image.open(path).convert("RGB")
                    s = max(w / src.width, h / src.height)            # cover the desktop, centred
                    src = src.resize((max(1, int(src.width * s)), max(1, int(src.height * s))), Image.LANCZOS)
                    l, t = (src.width - w) // 2, (src.height - h) // 2
                    img = src.crop((l, t, l + w, t + h))
                except Exception:
                    img = None
            if img is None:                                           # the default: dark, warm glow off-centre
                small = Image.new("RGB", (64, 40))
                px = small.load()
                for y in range(40):
                    for x in range(64):
                        d = (((x - 41) / 64) ** 2 + ((y - 14) / 40) ** 2) ** 0.5
                        t = min(1.0, d / 0.75)
                        a = (58, 42, 26) if t < 0.47 else (26, 20, 16)
                        b = (26, 20, 16) if t < 0.47 else (10, 12, 18)
                        k = t / 0.47 if t < 0.47 else (t - 0.47) / 0.53
                        px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))
                img = small.resize((w, h), Image.BICUBIC)
            self._wall_img = ImageTk.PhotoImage(img)
            self.desk.delete("wall")
            self.desk.create_image(0, 0, image=self._wall_img, anchor="nw", tags="wall")
            self.desk.tag_lower("wall")
            if self.cfg.get("desktop_icons"):
                self.draw_icons()
        except Exception:
            self.desk.configure(bg="#0f0f14")

    def set_wallpaper(self, path):
        self.cfg["wallpaper"] = path or None
        self._wall_size = None
        self.save()
        self.paint_wallpaper()

    # ---- Labs (2.0 beta 10): experimental modules only show when Labs is on in Settings
    def labs_on(self):
        return bool(self.S.get("labs"))

    def visible(self, mod):
        return not getattr(mod, "labs", False) or self.labs_on()

    def listed(self, mod):
        """On the dock, the Toolkit menu and the desktop (hidden ones open from inside other windows)."""
        return self.visible(mod) and not getattr(mod, "hidden", False)

    def set_labs(self, on):
        self.S["labs"] = bool(on)
        self.save()
        if not on:
            for k, m in self.modules.items():
                if getattr(m, "labs", False) and self.windows[k].state_ != "closed":
                    self.windows[k].close()
        self.draw_dock()
        self.make_task_dots()
        if self.cfg.get("desktop_icons"):
            self.draw_icons()
        self.refresh_taskbar()

    # ---- modules
    def register(self, mod):
        """Give a module its window and its dock button. -> the window's body (where the module draws)."""
        self.modules[mod.key] = mod
        title = mod.title + ("  (beta)" if getattr(mod, "labs", False) else "")
        win = DeskWindow(self, mod.key, title, mod.icon, utility=mod.kind == "utility")
        win.title = mod.title
        self.windows[mod.key] = win
        saved = self.cfg["windows"].get(mod.key) or {}
        win.geo = saved.get("geo")
        win.maxed = bool(saved.get("max"))
        if mod.kind in TILE:
            self.dock_btns[mod.key] = None              # drawn by draw_dock
            if mod.kind == "utility":
                self.dots[mod.key] = None
        return win.body

    # ---- the dock: the orb, then desktop-style icons (tile + name) for every module and utility, Settings at the bottom
    def draw_dock(self):
        d = self.dock
        d.delete("all")
        H = max(200, d.winfo_height())
        cx = DOCK_W // 2
        # the Toolkit button (the app's own icon): opens the Toolkit menu
        img = self.app_icon(3)
        t = 44
        self._round_rect(d, cx - t // 2 + 1, 10, cx + t // 2 + 1, 10 + t + 2, 10, fill="#05080e", outline="", tags=("orb",))
        self._orb_tile = self._round_rect(d, cx - t // 2, 8, cx + t // 2, 8 + t, 10, fill="#3a2a12", outline=C["accent"],
                                          width=1, tags=("orb",))
        if img is not None:
            d.create_image(cx, 8 + t // 2, image=img, tags=("orb",))
        else:
            d.create_text(cx, 8 + t // 2, text="◆", fill=C["accent"], font=("Segoe UI Symbol", 18), tags=("orb",))
        d.create_text(cx, 8 + t + 11, text="Toolkit", fill="#ffd9a8", font=("Segoe UI", 8, "bold"), tags=("orb",))
        d.create_line(10, 8 + t + 24, DOCK_W - 10, 8 + t + 24, fill="#26365a")
        d.tag_bind("orb", "<Button-1>", lambda e: self.toggle_menu())
        d.tag_bind("orb", "<Enter>", lambda e: (d.config(cursor="hand2"), d.itemconfigure(self._orb_tile, fill="#4e3816")))
        d.tag_bind("orb", "<Leave>", lambda e: (d.config(cursor=""), d.itemconfigure(self._orb_tile, fill="#3a2a12")))
        for k in list(self.dock_btns):
            self.dock_btns[k] = None
        for k in list(self.dots):
            self.dots[k] = None
        groups = [(k, [m for m in self.modules.values() if m.kind == k and self.listed(m)]) for k, _l in KINDS]
        n = sum(len(g) for _, g in groups)
        top, bottom = 84, 10                                     # 2.0 beta 15: Settings moved to the taskbar
        avail = H - top - bottom - 22 * len(groups)
        per = avail / max(1, n)
        labels = per >= 50
        tile = int(max(22, min(48, per - (24 if labels else 6))))
        step = tile + (24 if labels else 6)
        y = top
        for kind, mods in groups:
            if not mods:
                continue
            d.create_text(cx, y + 9, text=dict(KINDS)[kind], fill=C["steel"],
                          font=("Segoe UI", 7, "bold"))
            y += 22
            for m in mods:
                self._dock_item(m, cx, y, tile, labels)
                y += step
        self.paint_dock()
        self.refresh_dots()

    def app_icon(self, factor):
        """The app's .ico picture, made smaller (kept, or Tk forgets it)."""
        cache = self.__dict__.setdefault("_icons", {})
        if factor not in cache:
            try:
                cache[factor] = self.app.icon_img.subsample(factor, factor)
            except Exception:
                cache[factor] = None
        return cache[factor]

    @staticmethod
    def _round_rect(c, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r,
               x0, y0 + r, x0, y0]
        return c.create_polygon(pts, smooth=True, **kw)

    def _dock_item(self, m, cx, y, tile, labels):
        d = self.dock
        tag = "dk_" + m.key
        util = m.kind == "utility"
        fill, _hover, edge, gloss = TILE.get(m.kind, TILE["module"])
        x0, x1 = cx - tile // 2, cx + tile // 2
        self._round_rect(d, x0 + 1, y + 2, x1 + 1, y + tile + 2, 9, fill="#05080e", outline="", tags=(tag,))   # shadow
        t = self._round_rect(d, x0, y, x1, y + tile, 9, fill=fill, outline=edge, width=1, tags=(tag, tag + "_tile"))
        d.create_line(x0 + 7, y + 2, x1 - 7, y + 2, fill=gloss, tags=(tag,))          # gloss
        d.create_text(cx, y + tile // 2, text=m.icon, font=("Segoe UI Emoji", max(11, int(tile * 0.42))),
                      fill="#ffffff", tags=(tag,))
        if labels:
            d.create_text(cx, y + tile + 11, text=m.short or m.title if len(m.title) > 13 else m.title,
                          fill="#eef3ff", font=("Segoe UI", 8), width=DOCK_W - 6, tags=(tag, tag + "_lbl"))
        self.dock_btns[m.key] = t
        if getattr(m, "labs", False):                    # a Labs (experimental) one: a small BETA tag
            d.create_rectangle(x0 - 2, y + tile - 11, x0 + 22, y + tile - 1, fill=C["accent"], outline="", tags=(tag,))
            d.create_text(x0 + 10, y + tile - 6, text="BETA", fill="#1a1206", font=("Segoe UI", 6, "bold"), tags=(tag,))
        if util:
            self.dots[m.key] = d.create_oval(x1 - 9, y + 3, x1 - 2, y + 10, fill="#3b4a66", outline="#0e1522",
                                             tags=(tag,))
        d.tag_bind(tag, "<Button-1>", lambda e, k=m.key: self.open(k))
        d.tag_bind(tag, "<Enter>", lambda e, mm=m: self._dock_enter(mm))
        d.tag_bind(tag, "<Leave>", lambda e, mm=m: self._dock_leave(mm))

    def _dock_enter(self, m):
        self._dock_hover = m.key
        self.dock.config(cursor="hand2")
        self.paint_dock()
        if getattr(m, "blurb", ""):
            self.app._say(f"{m.title}: {m.blurb}", 4)

    def _dock_leave(self, m):
        if self._dock_hover == m.key:
            self._dock_hover = None
        self.dock.config(cursor="")
        self.paint_dock()

    def paint_dock(self):
        """Tile colours: lighter under the mouse, an orange edge while its window is open."""
        d = self.dock
        for k, t in self.dock_btns.items():
            if t is None:
                continue
            fill, hover, edge, _g = TILE.get(self.modules[k].kind, TILE["module"])
            w = self.windows.get(k)
            opened = w is not None and w.state_ != "closed"
            d.itemconfigure(t, fill=hover if self._dock_hover == k else fill, outline=C["accent"] if opened else edge,
                            width=2 if opened else 1)
            d.itemconfigure("dk_" + k + "_lbl", fill="#ffffff" if opened else "#cfdaf0")

    def finish(self):
        """After every module is registered: open the windows that were open last time (Price checks the first time)."""
        try:
            self.root.update_idletasks()                          # so the desktop has its real size for new windows
        except Exception:
            pass
        saved = self.cfg["windows"]
        opened = [k for k, v in saved.items() if v.get("open") and k in self.windows and self.visible(self.modules[k])]
        if not opened:
            opened = ["checks"] if "checks" in self.windows else list(self.windows)[:1]
        order = sorted(opened, key=lambda k: saved.get(k, {}).get("z", 0))
        for k in order:
            self.open(k, save=False)
        for k, v in saved.items():
            if v.get("min") and k in opened:
                self.windows[k].state_ = "minimised"
        self.refresh_taskbar()
        self.draw_dock()
        if self.cfg.get("desktop_icons"):
            self.root.after(300, self.draw_icons)

    def fit(self, g):
        """Keep a saved window on the desktop (the screen or the app window may be smaller than last time)."""
        x, y, w, h = [int(v) for v in g]
        dw, dh = self.desk.winfo_width(), self.desk.winfo_height()
        if dw < 200 or dh < 150:
            return [x, y, w, h]
        w, h = max(MIN_W, min(w, dw)), max(MIN_H, min(h, dh))
        x = min(max(x, 0), max(0, dw - w))                     # on the desktop, never over the dock / taskbar
        y = min(max(y, 0), dh - 40)
        if y + h > dh:                                            # keep the bottom (and its resize edge) reachable
            y = max(0, dh - h)
            h = min(h, dh - y)
        return [x, y, w, h]

    def default_geo(self, win):
        dw, dh = max(800, self.desk.winfo_width()), max(500, self.desk.winfo_height())
        n = list(self.windows).index(win.key)
        if win.key == "checks":
            return [16, 12, dw - 40, dh - 30]
        w, h = (min(1000, dw - 60), min(640, dh - 40)) if win.utility is False else (min(700, dw - 80), min(740, dh - 30))
        return [30 + 26 * (n % 6), 20 + 22 * (n % 6), w, h]

    # ---- open / focus
    def open(self, key, save=True):
        win = self.windows.get(key)
        if not win:
            return
        if not self.visible(self.modules[key]):            # a Labs one while Labs is off
            self.app._say(f"{self.modules[key].title} is a Labs (beta) feature: turn on Labs in Settings to use it.", 8)
            return
        win.open()
        self.focus(key)
        self._opened_at = time.time()             # a click that opened this window mustn't bring its own window back on top
        mod = self.modules.get(key)
        if mod is not None and hasattr(mod, "on_show"):
            try:
                mod.on_show()
            except Exception:
                pass
        self.close_menu()
        if save:
            self.save_layout()

    def focus(self, key):
        win = self.windows.get(key)
        if not win or win.state_ != "open":
            return
        win.lift()
        if self.menu is not None:
            self.menu.lift()
        self.zorder = [k for k in getattr(self, "zorder", []) if k != key] + [key]
        keep = getattr(self.app, "keep_on_top", None)         # e.g. the welcome card on the first start
        if keep:
            keep()
        if self.active != key:
            if self.active in self.windows:
                self.windows[self.active].set_active(False)
            self.active = key
            win.set_active(True)
            self.app.on_focus_module(key)
        self.refresh_taskbar()

    def _any_click(self, e):
        """A click anywhere inside a window brings that window to the front."""
        w = e.widget
        if self.menu is not None:                                 # a click outside the Toolkit menu closes it
            try:
                inside, p = False, w
                while p is not None:
                    if p is self.menu or p is self.orb:
                        inside = True
                        break
                    p = p.master
                if not inside:
                    self.close_menu()
            except Exception:
                pass
        try:
            while w is not None and not isinstance(w, DeskWindow):
                w = w.master
        except Exception:
            return
        if isinstance(w, DeskWindow) and w.key != self.active:
            self.click_focus(w.key)

    def click_focus(self, key):
        """A click anywhere in a window brings it forward - unless that click just opened another window."""
        if time.time() - getattr(self, "_opened_at", 0) < 0.3:
            return
        self.focus(key)

    def after_change(self, key):
        if self.active == key:
            self.active = None
            order = getattr(self, "zorder", [])
            nxt = next((k for k in reversed(order) if k in self.windows and self.windows[k].state_ == "open"), None)
            if nxt:                                               # the window that was under it comes forward
                self.focus(nxt)
        self.refresh_taskbar()
        self.save_layout()

    def is_open(self, key):
        w = self.windows.get(key)
        return bool(w and w.state_ == "open")

    def save_layout(self):
        out = {}
        for k, w in self.windows.items():
            out[k] = {"geo": w.current_geo() if w.state_ == "open" else w.geo, "max": w.maxed,
                      "open": w.state_ in ("open", "minimised"), "min": w.state_ == "minimised",
                      "z": (getattr(self, "zorder", []).index(k) + 1 if k in getattr(self, "zorder", []) else 1)
                      if w.state_ == "open" else 0}
        self.cfg["windows"] = out
        self.save()

    # ---- taskbar
    def refresh_taskbar(self):
        if self.dock_btns:
            self.paint_dock()
        for b in list(self.taskbtns.values()):
            b.destroy()
        self.taskbtns = {}
        for k, w in self.windows.items():
            if w.state_ == "closed":
                continue
            on = k == self.active and w.state_ == "open"
            b = tk.Label(self.task_inner, text=f"{w.icon} {w.title}", bg="#2c4c8a" if on else "#22345a",
                         fg="#ffffff" if w.state_ == "open" else C["muted"], padx=10, pady=4, cursor="hand2",
                         highlightthickness=1, highlightbackground=C["accent"] if on else "#3d5582", font=("Segoe UI", 9))
            b.pack(side="left", padx=3)
            b.bind("<Button-1>", lambda e, kk=k: self.task_click(kk))
            self.taskbtns[k] = b

    def task_click(self, key):
        w = self.windows[key]
        if w.state_ == "open" and self.active == key:
            w.minimise()
        else:
            self.open(key)

    def add_status(self, widget):
        """Modules / the core can put small status widgets on the right of the taskbar."""
        widget.pack(in_=self.task_right, side="left", padx=5)

    def refresh_dots(self):
        for k, d in self.dots.items():
            mod = self.modules[k]
            st = None
            try:
                st = mod.status() if hasattr(mod, "status") else None
            except Exception:
                st = None
            col = {True: C["green"], False: "#3b4a66", None: "#3b4a66", "warn": C["orange"]}.get(st, "#3b4a66")
            if d is not None:
                self.dock.itemconfigure(d, fill=col)
        if hasattr(self, "task_dots"):
            for k, (lab, mod) in self.task_dots.items():
                try:
                    st = mod.status()
                except Exception:
                    st = None
                lab.config(fg=C["green"] if st is True else C["orange"] if st == "warn" else "#5a6a88")

    def make_task_dots(self):
        old = getattr(self, "_task_dot_frame", None)
        if old is not None:
            for w in old.winfo_children():
                w.destroy()
            f = old
        else:
            f = tk.Frame(self.task_right, bg="#111b30")
            self._task_dot_frame = f
        self.task_dots = {}
        for k, mod in self.modules.items():
            if mod.kind != "utility" or not self.listed(mod):
                continue
            lab = tk.Label(f, text=f"● {mod.short}", bg="#111b30", fg="#5a6a88", font=("Segoe UI", 9), cursor="hand2")
            lab.pack(side="left", padx=4)
            lab.bind("<Button-1>", lambda e, kk=k: self.open(kk))
            self.task_dots[k] = (lab, mod)
        if old is not None:
            return
        f.pack(side="left", padx=6)
        self.clock = tk.Label(self.task_right, text="", bg="#111b30", fg=C["text"], font=("Segoe UI", 8, "bold"),
                              justify="right")
        self.clock.pack(side="left", padx=(8, 2))

    def _tick(self):
        try:
            if self.clock is not None:
                self.clock.config(text=clock_text())
            self.refresh_dots()
        except Exception:
            pass
        self.root.after(2000, self._tick)

    # ---- the Toolkit menu
    def toggle_menu(self):
        if self.menu is not None:
            self.close_menu()
        else:
            self.open_menu()

    def close_menu(self):
        if self.menu is not None:
            self.menu.destroy()
            self.menu = None

    def _place_menu(self):
        if self.menu is not None:
            h = min(560, self.desk.winfo_height() - 10)
            ox, oy = self.desk_origin()
            self.menu.geometry(f"430x{h}+{ox}+{oy}")

    def open_menu(self):
        P1 = C["panel"]
        m = tk.Toplevel(self.root, bg=P1, highlightthickness=1, highlightbackground="#3d5582")
        m.overrideredirect(True)
        try:
            m.transient(self.root)
        except tk.TclError:
            pass
        self.menu = m
        self._place_menu()
        m.lift()
        head = GradientBar(m, 62, TITLE_ON)
        head.pack(fill="x")
        tk.Frame(m, height=2, bg=C["accent"]).pack(fill="x")
        if self.app_icon(2) is not None:
            head.create_image(31, 31, image=self.app_icon(2))
        head.create_text(62, 22, text="StashOfExile2", anchor="w", fill="#ffffff", font=("Georgia", 15, "bold"))
        head.create_text(62, 44, text=self.app.menu_subtitle(), anchor="w", fill="#9fb6dd", font=("Segoe UI", 9))
        q = tk.StringVar()
        e = tk.Entry(m, textvariable=q, bg="#0b1222", fg=C["text"], insertbackground=C["text"], relief="flat",
                     highlightthickness=1, highlightbackground=C["line"], font=("Segoe UI", 10))
        e.pack(fill="x", padx=10, pady=10, ipady=4)
        e.insert(0, "")
        cols = tk.Frame(m, bg=P1)
        cols.pack(fill="both", expand=True, padx=6)
        lists = {}
        colf = [tk.Frame(cols, bg=P1), tk.Frame(cols, bg=P1)]
        for c in colf:
            c.pack(side="left", fill="both", expand=True, padx=4)
        for kind, label in KINDS:
            c = tk.Frame(colf[1 if kind == "utility" else 0], bg=P1)
            c.pack(fill="x", pady=(0, 8))
            tk.Label(c, text=label, bg=P1, fg=C["steel"], font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
            lists[kind] = c

        def fill(*_a):
            for c in lists.values():
                for w in c.winfo_children()[1:]:
                    w.destroy()
            words = q.get().strip().lower()
            for k, mod in self.modules.items():
                if mod.kind not in lists or not self.listed(mod):
                    continue
                if words and words not in (mod.title + " " + getattr(mod, "blurb", "")).lower():
                    continue
                st = mod.status() if hasattr(mod, "status") else None
                dot = ("● " if mod.kind == "utility" else "")
                row = tk.Label(lists[mod.kind], text=f"{dot}{mod.icon}  {mod.title}" + ("  ·beta" if getattr(mod, "labs", False) else ""), bg=P1, anchor="w", padx=8, pady=6,
                               fg=C["text"], cursor="hand2", font=("Segoe UI", 10))
                if mod.kind == "utility":
                    row.config(fg=C["green"] if st is True else C["text"])
                row.pack(fill="x")
                row.bind("<Enter>", lambda ev, r=row: r.config(bg=C["sel"]))
                row.bind("<Leave>", lambda ev, r=row: r.config(bg=P1))
                row.bind("<Button-1>", lambda ev, kk=k: self.open(kk))
        q.trace_add("write", fill)
        fill()
        foot = tk.Frame(m, bg=P1, highlightthickness=0)
        foot.pack(fill="x", side="bottom", padx=10, pady=10)
        for text, cmd in (("⚙ Settings", lambda: self.open("settings")), ("✦ What's new", lambda: self.app.show_whatsnew(True)),
                          ("⟳ Check for updates", self.app.check_updates),
                          ("✕ Quit", self.app.on_close)):
            b = tk.Label(foot, text=text, bg="#0b1222", fg=C["text"], padx=8, pady=4, cursor="hand2",
                         highlightthickness=1, highlightbackground=C["line"])
            b.pack(side="left" if "Quit" not in text else "right", padx=(0, 6))
            b.bind("<Button-1>", lambda ev, c=cmd: (self.close_menu(), c()))
        e.focus_set()
        e.bind("<Escape>", lambda ev: self.close_menu())
        e.bind("<Return>", lambda ev: self._menu_enter(q.get()))

    def _menu_enter(self, words):
        words = words.strip().lower()
        for k, mod in self.modules.items():
            if mod.kind in TILE and self.listed(mod) and (not words or words in mod.title.lower()):
                self.open(k)
                return

    # ---- optional desktop icons (Settings)
    LAUNCHERS = (("dock", "Dock on the left"), ("icons", "Icons on the desktop"), ("both", "Both"))

    def set_launcher(self, mode):
        """2.0 beta 21: how you open things - the dock, desktop icons, or both (one of them is always there)."""
        mode = mode if mode in dict(self.LAUNCHERS) else "dock"
        self.cfg["launcher"] = mode
        self.cfg["desktop_icons"] = mode in ("icons", "both")
        dock = mode in ("dock", "both")
        if dock and not self.dock.winfo_ismapped():
            self.dock.pack(side="left", fill="y", before=self.desk)
            self.dock_sep.pack(side="left", fill="y", before=self.desk)
        elif not dock:
            self.dock.pack_forget()
            self.dock_sep.pack_forget()
        state = "hidden" if dock else "normal"
        self.task.itemconfigure("tkbtn", state=state)
        self.task.coords("inner", DOCK_W + 6 + (0 if dock else DOCK_W - 10), TASK_H // 2)
        self.save()
        self.draw_icons()

    def draw_icons(self):
        """Optional desktop icons (Settings): the same tiles as the dock, bigger, in columns from the top left."""
        d = self.desk
        d.delete("dicon")
        self.icons = []
        if not self.cfg.get("desktop_icons"):
            return
        H = max(300, d.winfo_height())
        tile, colw, step = 54, 100, 96
        x, y = 14 + colw // 2, 14
        for kind, _label in KINDS:
            for k, mod in self.modules.items():
                if mod.kind != kind or not self.listed(mod):
                    continue
                if y + step > H:
                    x, y = x + colw, 14
                tag = "di_" + k
                fill, hover, edge, gloss = TILE[kind]
                x0, x1 = x - tile // 2, x + tile // 2
                self._round_rect(d, x0 + 2, y + 3, x1 + 2, y + tile + 3, 11, fill="#020305", outline="", tags=("dicon", tag))
                t = self._round_rect(d, x0, y, x1, y + tile, 11, fill=fill, outline=edge, width=1, tags=("dicon", tag))
                d.create_line(x0 + 8, y + 2, x1 - 8, y + 2, fill=gloss, tags=("dicon", tag))
                d.create_text(x, y + tile // 2, text=mod.icon, font=("Segoe UI Emoji", 22), fill="#ffffff", tags=("dicon", tag))
                for dx, col in ((1, "#000000"), (0, "#f2f6ff")):        # label with a shadow, readable on any wallpaper
                    d.create_text(x + dx, y + tile + 13 + dx, text=mod.title, fill=col, font=("Segoe UI", 9),
                                  width=colw - 8, justify="center", tags=("dicon", tag))
                d.tag_bind(tag, "<Button-1>", lambda e, kk=k: self.open(kk))
                d.tag_bind(tag, "<Enter>", lambda e, it=t, hv=hover: (d.config(cursor="hand2"), d.itemconfigure(it, fill=hv)))
                d.tag_bind(tag, "<Leave>", lambda e, it=t, fl=fill: (d.config(cursor=""), d.itemconfigure(it, fill=fl)))
                self.icons.append(tag)
                y += step
        self.desk.tag_lower("wall")
