"""
PoE2 Delirium End Reminder
--------------------------
Passive, read-only screen watcher. It takes screenshots of small parts of
your screen, looks for a few images, and shows a big "END DELIRIUM" banner:

  1. The Delirium fast-forward arrows   -> Delirium is running in this map
  2. EITHER the "MAP COMPLETED" popup (bottom centre)
     OR "Map Completed" under Map Objectives (right side) -> map boss is dead

It never reads game memory, never touches the game process or its files,
never sends keys or clicks. You still click the arrows yourself.

While running it shows a Simulacrum Splinter icon on screen and in the system
tray. Right-click the tray icon for options / Quit.

Usage:
  python delirium_alert.py            run the overlay
  python delirium_alert.py --debug    run + print match scores to the console
  python delirium_alert.py --test-alert   just show the banner for 5 s
  python delirium_alert.py --test-image some_screenshot.png   check detection on a file
  python delirium_alert.py --grab     save a full screenshot (to re-crop templates)
"""

import argparse
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

if getattr(sys, "frozen", False):          # running as the compiled .exe
    HERE = Path(sys.executable).resolve().parent        # log/settings go next to the exe
    TEMPLATE_DIR = Path(getattr(sys, "_MEIPASS", HERE)) / "templates"   # bundled images
else:
    HERE = Path(__file__).resolve().parent
    TEMPLATE_DIR = HERE / "templates"

# ----------------------------------------------------------------- settings
CONFIG = {
    # The tool finds the game window by its title and watches only that window,
    # whichever monitor it is on.
    "game_window_title": "Path of Exile 2",
    "poll_seconds": 0.4,     # how often to look

    # Match thresholds (0..1). Raise if you get false alarms, lower if it misses.
    "arrows_threshold": 0.78,
    "banner_threshold": 0.75,

    # Where to look, as fractions of the screen (left, top, right, bottom).
    # Arrows: whole screen until first found, then a tall band around that spot
    # (the button can shift up/down by an inch or two).
    "arrows_region": (0.50, 0.40, 1.0, 1.0),   # bottom-right area of the game
    "arrows_band_x_px": 60,      # once found: +/- this many px horizontally
    "arrows_band_y_px": 300,     # once found: +/- this many px vertically
    # "Map Completed" banner shows at the bottom centre of the screen.
    "banner_region": (0.25, 0.45, 0.75, 1.0),
    # Backup check: "Map Completed" in the Map Objectives list on the right
    # (the popup occasionally doesn't show).
    "objective_threshold": 0.68,
    "objective_region": (0.70, 0.05, 1.0, 0.60),

    # Delirium counts as "active" if the arrows were seen within this many seconds
    # (the banner can briefly cover things / the button can flicker).
    "arrows_memory_seconds": 20,

    # Alert behaviour
    "alert_timeout_seconds": 45,     # auto-hide after this long
    "hide_when_arrows_gone_s": 1.5,  # hide once arrows are gone this long (you clicked them)
    "beep": True,                    # one sound per map; toggle from the tray menu

    # On-screen splinter icon, anchored to the game's bottom-right corner (like the
    # HUD), so it stays put at any resolution or aspect ratio. Values are distances
    # from the right / bottom edge as a fraction of screen height. Default: inside
    # the empty "3" skill slot. Easier: tray icon -> "Move splinter icon" and drag.
    "indicator": True,
    "indicator_anchor": (0.441, 0.0535),
    "indicator_size": 34,          # pixels at 1440p; scaled for other resolutions

    # System tray icon
    "tray": True,

    # Scales to try until each template is found once (handles other resolutions).
    # Matching only works within a few % of the exact size, so this list is dense.
    # The banner's size is then taken from the arrows' size (they scale together).
    "scales": sorted({round(1.0 + d * 0.03, 2) for d in range(-17, 34)}, key=lambda v: abs(v - 1)),
}
# -------------------------------------------------------------------------

STATE_COLORS = {                 # ring / badge colour per state
    "watching": (70, 150, 255),
    "active":   (190, 90, 255),
    "alert":    (255, 40, 40),
    "error":    (255, 150, 0),
    "nogame":   (120, 120, 120),
    "move":     (255, 215, 0),
}
STATE_TEXT = {
    "watching": "Watching (no Delirium seen)",
    "active":   "Delirium detected this map",
    "alert":    "END DELIRIUM!",
    "error":    "Screen capture error",
    "nogame":   "Waiting for the Path of Exile 2 window",
    "move":     "Drag the splinter where you want it, then let go",
}


BASE_HEIGHT = 1440   # the template images were cut from a 2560x1440 screen


def ui_scale(sh):
    return sh / BASE_HEIGHT


class Template:
    def __init__(self, path):
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            sys.exit(f"Missing template: {path}")
        self.base = img
        self.scale = None          # locked after first confident match
        self._cache = {}
        self._cursor = 0           # where the unlocked size sweep is up to
        self.order = list(CONFIG["scales"])
        self.hint = None

    def set_hint(self, ui):
        """Sweep sizes outward from the predicted UI size first."""
        if ui != self.hint:
            self.hint = ui
            self.order = [round(ui * f, 3) for f in CONFIG["scales"]]
            self._cursor = 0

    def scaled(self, s):
        if s not in self._cache:
            h, w = self.base.shape
            self._cache[s] = cv2.resize(
                self.base, (max(8, int(w * s)), max(8, int(h * s))),
                interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
        return self._cache[s]

    def match(self, gray, threshold, scales=None):
        """Return (score, (x, y, w, h)) of best match in gray image.
        Stops at the first scale that clears the threshold."""
        if scales is None:
            if self.scale:
                scales = [self.scale]
            else:   # sweep a few sizes per scan so the CPU stays low
                allsc, n = self.order, 8
                scales = [allsc[(self._cursor + i) % len(allsc)] for i in range(n)]
                self._cursor = (self._cursor + n) % len(allsc)
        best = (0.0, None, None)
        for s in scales:
            t = self.scaled(s)
            if t.shape[0] > gray.shape[0] or t.shape[1] > gray.shape[1]:
                continue
            res = cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            if mx > best[0]:
                best = (mx, (loc[0], loc[1], t.shape[1], t.shape[0]), s)
                if mx >= threshold:
                    break
        if best[0] >= threshold and self.scale is None:
            best = self._refine(gray, best)
            self.scale = best[2]
        return best[0], best[1]

    def _refine(self, gray, best):
        """Fine-tune the size (1% steps) before locking it in."""
        for d in [x / 100 for x in range(-12, 13) if x]:
            s = round(best[2] + d, 3)
            t = self.scaled(s)
            if t.shape[0] > gray.shape[0] or t.shape[1] > gray.shape[1]:
                continue
            res = cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            if mx > best[0]:
                best = (mx, (loc[0], loc[1], t.shape[1], t.shape[0]), s)
        return best


def frac_box(region, sw, sh):
    l, t, r, b = region
    return int(l * sw), int(t * sh), int(r * sw), int(b * sh)


class Detector:
    def __init__(self):
        self.arrows = Template(TEMPLATE_DIR / "delirium_arrows.png")
        self.banner = Template(TEMPLATE_DIR / "map_completed.png")
        self.objective = Template(TEMPLATE_DIR / "objective_completed.png")
        self.last = {"banner": 0.0, "objective": 0.0}
        self.arrows_pos = None   # absolute screen (cx, cy) once found
        self._banner_cursor = 0

    def arrows_box(self, sw, sh):
        if self.arrows_pos:
            cx, cy = self.arrows_pos
            ui = sh / BASE_HEIGHT
            bx = int((CONFIG["arrows_band_x_px"] + 60) * ui)
            by = int(CONFIG["arrows_band_y_px"] * ui)
            return max(0, cx - bx), max(0, cy - by), min(sw, cx + bx), min(sh, cy + by)
        return frac_box(CONFIG["arrows_region"], sw, sh)

    def banner_scales(self, tpl=None):
        tpl = tpl or self.banner
        if tpl.scale:
            return [tpl.scale]
        if self.arrows.scale:
            a = self.arrows.scale
            near = [round(a * f, 3) for f in (1, 0.97, 1.03, 0.94, 1.06)]
            # safety net: also sweep a few other sizes each scan until it's found once
            allsc = tpl.order
            c = self._banner_cursor
            self._banner_cursor = (c + 4) % len(allsc)
            return near + [allsc[(c + i) % len(allsc)] for i in range(4)]
        return None   # unknown yet: full list

    def objective_scales(self, ui):
        """Small text: needs 1% size steps around the expected size."""
        if self.objective.scale:
            return [self.objective.scale]
        base = self.arrows.scale or ui
        return [round(base * (1 + k / 100), 3) for k in (0, -1, 1, -2, 2, -3, 3, -4, 4, -5, 5, -6, 6, -8, 8)]

    def check(self, grab, sw, sh, need_banner=True):
        """grab(l,t,r,b) -> grayscale ndarray. Returns (arrows_score, banner_score).
        The banner is only looked for when need_banner (i.e. Delirium is running)."""
        ui = sh / BASE_HEIGHT      # PoE2's UI scales with screen height
        self.arrows.set_hint(ui)
        self.banner.set_hint(ui)
        self.objective.set_hint(ui)
        l, t, r, b = self.arrows_box(sw, sh)
        a_score, a_box = self.arrows.match(grab(l, t, r, b), CONFIG["arrows_threshold"])
        if a_score >= CONFIG["arrows_threshold"] and a_box:
            x, y, w, h = a_box
            self.arrows_pos = (l + x + w // 2, t + y + h // 2)

        b_score = 0.0
        if need_banner or a_score >= CONFIG["arrows_threshold"]:
            l, t, r, b = frac_box(CONFIG["banner_region"], sw, sh)
            b_score, _ = self.banner.match(grab(l, t, r, b), CONFIG["banner_threshold"],
                                           self.banner_scales())
            l, t, r, b = frac_box(CONFIG["objective_region"], sw, sh)
            o_score, _ = self.objective.match(grab(l, t, r, b), CONFIG["objective_threshold"],
                                              self.objective_scales(ui))
            self.last = {"banner": b_score, "objective": o_score}
            # Report "map completed" as a single score, normalised to the banner threshold.
            o_norm = o_score * CONFIG["banner_threshold"] / CONFIG["objective_threshold"]
            b_score = max(b_score, o_norm)
        else:
            self.last = {"banner": 0.0, "objective": 0.0}
        return a_score, b_score


# ------------------------------------------------------------ icon images
KEY_RGB = (255, 0, 254)          # colour made fully transparent in the on-screen icon
KEY_HEX = "#ff00fe"


def load_splinter(size):
    from PIL import Image, ImageDraw
    try:
        img = Image.open(TEMPLATE_DIR / "splinter.png").convert("RGBA")
    except OSError:                    # StashOfExile2 2.10.0 doesn't ship the splinter picture: a plain diamond
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(img).polygon([(32, 2), (60, 32), (32, 62), (4, 32)], fill=(150, 110, 220, 255))
    img.thumbnail((size, size), Image.LANCZOS)
    return img


def indicator_images(size):
    """On-screen icon per state, on a solid key colour with hard edges
    (Windows colour-key transparency can't do soft edges)."""
    from PIL import Image, ImageEnhance, ImageFilter
    pad = 2
    spl = load_splinter(size)
    mask = spl.getchannel("A").point(lambda a: 255 if a > 110 else 0)
    canvas_size = (spl.width + 2 * pad, spl.height + 2 * pad)
    big_mask = Image.new("L", canvas_size, 0)
    big_mask.paste(mask, (pad, pad))
    ring_mask = big_mask.filter(ImageFilter.MaxFilter(3))

    out = {}
    for state, ring in STATE_COLORS.items():
        for pulse in (False, True):
            s = spl.convert("RGB")
            if state == "error":
                s = ImageEnhance.Color(s).enhance(0.6)
                s = ImageEnhance.Brightness(s).enhance(0.75)
            if pulse:
                s = ImageEnhance.Brightness(s).enhance(1.6)
            canvas = Image.new("RGB", canvas_size, KEY_RGB)
            if ring:
                canvas.paste(Image.new("RGB", canvas_size, ring), (0, 0), ring_mask)
            canvas.paste(s, (pad, pad), mask)
            out[(state, pulse)] = canvas
    return out


def tray_images():
    """Tray icon per state: splinter with a coloured badge in the corner."""
    from PIL import Image, ImageDraw
    out = {}
    base = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    spl = load_splinter(64)
    base.paste(spl, ((64 - spl.width) // 2, (64 - spl.height) // 2), spl)
    for state in STATE_COLORS:
        img = base.copy()
        color = STATE_COLORS[state]
        d = ImageDraw.Draw(img)
        d.ellipse((38, 38, 63, 63), fill=color + (255,), outline=(0, 0, 0, 255), width=3)
        out[state] = img
    return out


# ------------------------------------------------------------------ windows
def _hwnd(win):
    import ctypes
    return ctypes.windll.user32.GetParent(win.winfo_id())


def click_through(win, on=True):
    """Let mouse clicks pass through a window and never steal focus (Windows only).
    on=False makes it grabbable again (used while moving the splinter)."""
    if sys.platform != "win32":
        return
    import ctypes
    hwnd = _hwnd(win)
    GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT = -20, 0x80000, 0x20
    WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = 0x80, 0x08000000
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    style = style | WS_EX_TRANSPARENT if on else style & ~WS_EX_TRANSPARENT
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


def force_topmost(win):
    """Push a window back above the game (borderless games sometimes cover it)."""
    if sys.platform != "win32":
        win.attributes("-topmost", True)
        return
    import ctypes
    HWND_TOPMOST, SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = -1, 0x1, 0x2, 0x10
    ctypes.windll.user32.SetWindowPos(_hwnd(win), HWND_TOPMOST, 0, 0, 0, 0,
                                      SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)


def make_dpi_aware():
    """Use real pixels so the game window, screenshots and overlay all line up
    (otherwise Windows display scaling blows the overlay up and shifts it)."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # per-monitor v2
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def find_game_rect():
    """(width, height, left, top) of the PoE2 window's game area in screen pixels,
    or None if it isn't open / is minimised. Only looks at window title & position."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    title_want = CONFIG["game_window_title"].lower()
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if buf.value.strip().lower() == title_want or cls.value == "POEWindowClass":
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(cb, 0)
    if not found:
        return None
    hwnd = found[0]
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    pt = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w < 200 or h < 200:
        return None
    return w, h, pt.x, pt.y


class Alert:
    TRANSPARENT = "#010203"

    def __init__(self, root, sw, sh, ox, oy):
        import tkinter as tk
        self.root = root
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=self.TRANSPARENT)
        try:
            self.win.attributes("-transparentcolor", self.TRANSPARENT)  # Windows
        except tk.TclError:
            pass
        self.label = tk.Label(self.win, text="END DELIRIUM", fg="#ff2a2a",
                              bg=self.TRANSPARENT, font=("Segoe UI Black", 54, "bold"))
        self.label.pack(expand=True, fill="both")
        self.place(sw, sh, ox, oy)
        self.win.update_idletasks()
        click_through(self.win)
        self.win.withdraw()
        self.visible = False
        self._flash = False

    def place(self, sw, sh, ox, oy):
        ui = ui_scale(sh)
        w, h = int(1000 * ui), int(190 * ui)
        self.label.configure(font=("Segoe UI Black", -int(96 * ui), "bold"))  # negative = pixels
        self.win.geometry(f"{w}x{h}+{ox + (sw - w) // 2}+{oy + int(sh * 0.62)}")

    def show(self):
        if not self.visible:
            self.win.deiconify()
            force_topmost(self.win)
            self.visible = True
            self._blink()

    def hide(self):
        if self.visible:
            self.win.withdraw()
            self.visible = False

    def _blink(self):
        if not self.visible:
            return
        self._flash = not self._flash
        self.label.configure(fg="#ffffff" if self._flash else "#ff2a2a")
        self.root.after(350, self._blink)


class SplinterIndicator:
    """Small always-on-top splinter: blue ring = watching, purple ring = Delirium seen,
    red ring = END DELIRIUM. Follows the game window if it moves."""

    def __init__(self, root, sw, sh, ox, oy):
        import tkinter as tk
        from PIL import ImageTk
        self.root = root
        self.ImageTk = ImageTk
        self.size = None
        self.photos = {}
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=KEY_HEX)
        try:
            self.win.attributes("-transparentcolor", KEY_HEX)
        except tk.TclError:
            pass
        self.state = "watching"
        self.label = tk.Label(self.win, bg=KEY_HEX, bd=0, highlightthickness=0)
        self.label.pack()
        self.place(sw, sh, ox, oy)
        self.win.update_idletasks()
        click_through(self.win)
        force_topmost(self.win)
        self.visible = True
        self.moving = False
        self.on_moved = None
        self._drag = None
        self.label.bind("<ButtonPress-1>", self._press)
        self.label.bind("<B1-Motion>", self._motion)
        self.label.bind("<ButtonRelease-1>", self._release)

    def set(self, state):
        if self.moving:
            return
        self.state = state
        self.label.configure(image=self.photos[(state, False)])

    def place(self, sw, sh, ox, oy):
        """Size and position for the current game window (any resolution)."""
        self.rect = (sw, sh, ox, oy)
        size = max(16, round(CONFIG["indicator_size"] * ui_scale(sh)))
        if size != self.size:
            self.size = size
            self.photos = {k: self.ImageTk.PhotoImage(v) for k, v in indicator_images(size).items()}
        self.label.configure(image=self.photos[("move" if getattr(self, "moving", False) else self.state, False)])
        right, bottom = CONFIG["indicator_anchor"]
        self.x = ox + sw - int(right * sh)
        self.y = oy + sh - int(bottom * sh)
        self.win.geometry(f"+{self.x}+{self.y}")

    # --- move mode: one drag, then it locks again
    def start_move(self, on_moved):
        self.on_moved = on_moved
        self.moving = True
        self.set_visible(True)
        self.label.configure(image=self.photos[("move", False)], cursor="fleur")
        click_through(self.win, False)

    def _press(self, e):
        if self.moving:
            self._drag = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def _motion(self, e):
        if self.moving and self._drag:
            self.x, self.y = e.x_root - self._drag[0], e.y_root - self._drag[1]
            self.win.geometry(f"+{self.x}+{self.y}")

    def _release(self, e):
        if not (self.moving and self._drag):
            return
        self._drag = None
        self.moving = False
        sw, sh, ox, oy = self.rect
        CONFIG["indicator_anchor"] = (round((ox + sw - self.x) / sh, 4), round((oy + sh - self.y) / sh, 4))
        self.label.configure(cursor="")
        click_through(self.win, True)
        self.set(self.state)
        if self.on_moved:
            self.on_moved(CONFIG["indicator_anchor"])

    def set_visible(self, on):
        self.visible = on
        if on:
            self.win.deiconify()
            force_topmost(self.win)
        else:
            self.win.withdraw()


class Tray:
    """System tray icon (runs on its own thread). Commands go back to the
    Tk thread through a list that the scan loop drains."""

    def __init__(self, commands):
        import pystray
        self.pystray = pystray
        self.commands = commands
        self.images = tray_images()
        self.state = "watching"
        self.indicator_on = CONFIG["indicator"]
        self.sound_on = CONFIG["beep"]
        Item, Menu = pystray.MenuItem, pystray.Menu
        menu = Menu(
            Item(lambda _: f"Status: {STATE_TEXT[self.state]}", None, enabled=False),
            Menu.SEPARATOR,
            Item("Sound (once per map)", self._toggle_sound,
                 checked=lambda _: self.sound_on),
            Item("Show on-screen splinter", self._toggle_indicator,
                 checked=lambda _: self.indicator_on),
            Item("Move splinter icon", lambda: self.commands.append("move")),
            Item("Reset splinter position", lambda: self.commands.append("reset_pos")),
            Item("Test alert (5 s)", lambda: self.commands.append("test")),
            Menu.SEPARATOR,
            Item("Quit", lambda: self.commands.append("quit")),
        )
        self.icon = pystray.Icon("poe2_delirium", self.images["watching"],
                                 "PoE2 Delirium watch: " + STATE_TEXT["watching"], menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def _toggle_sound(self):
        self.sound_on = not self.sound_on
        self.commands.append("sound_on" if self.sound_on else "sound_off")

    def _toggle_indicator(self):
        self.indicator_on = not self.indicator_on
        self.commands.append("indicator_on" if self.indicator_on else "indicator_off")

    def set(self, state):
        if state == self.state:
            return
        self.state = state
        try:
            self.icon.icon = self.images[state]
            self.icon.title = "PoE2 Delirium watch: " + STATE_TEXT[state]
            self.icon.update_menu()
        except Exception:
            pass

    def stop(self):
        try:
            self.icon.stop()
        except Exception:
            pass


LOG_FILE = HERE / "delirium_log.txt"
CALIB_FILE = HERE / "calibration_v2.json"
SETTINGS_FILE = HERE / "settings.json"
DEFAULT_INDICATOR_ANCHOR = CONFIG["indicator_anchor"]


def load_calibration():
    import json
    try:
        return json.loads(CALIB_FILE.read_text())
    except Exception:
        return {}


def save_calibration(data):
    import json
    try:
        CALIB_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def beep():
    if not CONFIG["beep"]:
        return
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        print("\a", end="", flush=True)


# --------------------------------------------------------------------- main
def load_settings():
    import json
    try:
        data = json.loads(SETTINGS_FILE.read_text())
        if "indicator_pos" in data and "indicator_anchor" not in data:
            # older versions saved screen fractions on a 16:9 screen: convert
            fx, fy = data.pop("indicator_pos")
            data["indicator_anchor"] = [round((1 - fx) * 16 / 9, 4), round(1 - fy, 4)]
            SETTINGS_FILE.write_text(json.dumps(data, indent=2))
        if "indicator_anchor" in data:
            CONFIG["indicator_anchor"] = tuple(data["indicator_anchor"])
        if "beep" in data:
            CONFIG["beep"] = bool(data["beep"])
    except Exception:
        pass


def save_setting(key, value):
    """Write one setting to settings.json (None removes it)."""
    import json
    try:
        data = json.loads(SETTINGS_FILE.read_text()) if SETTINGS_FILE.exists() else {}
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
        SETTINGS_FILE.write_text(json.dumps(data, indent=2))
    except Exception as e:
        print("Couldn't save settings:", e)


def already_running():
    """Only allow one copy at a time (Windows named mutex)."""
    if sys.platform != "win32":
        return False
    import ctypes
    global _MUTEX
    _MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "PoE2DeliriumAlert_single_instance")
    return ctypes.windll.kernel32.GetLastError() == 183   # ERROR_ALREADY_EXISTS


def run(debug=False, test_alert=False):
    if not test_alert and already_running():
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None, "PoE2 Delirium Alert is already running.\nLook for the splinter in your system tray.",
                "PoE2 Delirium Alert", 0x40)
        return
    make_dpi_aware()
    load_settings()
    import tkinter as tk
    import mss
    sct = mss.MSS() if hasattr(mss, "MSS") else mss.mss()

    def primary():
        m = next((m for m in sct.monitors[1:] if m["left"] == 0 and m["top"] == 0), sct.monitors[1])
        return m["width"], m["height"], m["left"], m["top"]

    game = find_game_rect()
    g = {"rect": game or primary(), "found": game is not None, "last_check": time.time()}

    def grab(l, t, r, b):
        _, _, ox, oy = g["rect"]
        shot = sct.grab({"left": ox + l, "top": oy + t, "width": r - l, "height": b - t})
        return cv2.cvtColor(np.asarray(shot), cv2.COLOR_BGRA2GRAY)

    root = tk.Tk()
    root.withdraw()
    alert = Alert(root, *g["rect"])

    if test_alert:
        alert.show(); beep()
        root.after(5000, root.destroy)
        root.mainloop()
        return

    indicator = SplinterIndicator(root, *g["rect"])
    if not CONFIG["indicator"]:
        indicator.set_visible(False)

    commands = []
    tray = None
    if CONFIG["tray"]:
        try:
            tray = Tray(commands)
        except Exception as e:
            print("Tray icon unavailable:", e)

    def save_position(pos):
        save_setting("indicator_pos", None)
        save_setting("indicator_anchor", None if pos is None else list(pos))
        log("Splinter position " + ("reset" if pos is None else f"saved: {pos}"))

    det = Detector()
    calib = load_calibration()

    def apply_calibration():
        key = f"{g['rect'][0]}x{g['rect'][1]}"
        det.arrows.scale = calib.get(key, {}).get("arrows")
        det.banner.scale = calib.get(key, {}).get("banner")
        det.objective.scale = calib.get(key, {}).get("objective")
    apply_calibration()

    def remember_scales():
        key = f"{g['rect'][0]}x{g['rect'][1]}"
        entry = {"arrows": det.arrows.scale, "banner": det.banner.scale,
                 "objective": det.objective.scale}
        if calib.get(key) != entry:
            calib[key] = entry
            save_calibration(calib)

    state = {"arrows_seen": 0.0, "alert_since": None, "banner_latched": False,
             "alerted_this_map": False,
             "last_topmost": 0.0, "alert_limit": CONFIG["alert_timeout_seconds"]}
    def describe():
        w, h, x, y = g["rect"]
        if g["found"]:
            print(f"Found Path of Exile 2 ({w}x{h} at {x},{y}), UI size x{ui_scale(h):.2f}. Watching it.")
        else:
            print("Path of Exile 2 window not found yet - start the game (windowed fullscreen). Waiting...")
    describe()
    log("Started")
    print("Running. Quit from the tray icon menu, or close this window.")

    def quit_app():
        if tray:
            tray.stop()
        root.destroy()

    def set_state(s):
        if indicator.moving:
            return
        indicator.set(s)
        if tray:
            tray.set(s)

    def tick():
        now = time.time()

        while commands:
            cmd = commands.pop(0)
            if cmd == "quit":
                quit_app()
                return
            if cmd == "test":
                state["alert_since"], state["alert_limit"] = now, 5
                alert.show(); beep()
            if cmd == "move":
                if tray:
                    tray.set("move")
                indicator.start_move(save_position)
            if cmd == "reset_pos":
                CONFIG["indicator_anchor"] = DEFAULT_INDICATOR_ANCHOR
                indicator.place(*g["rect"])
                save_position(None)
            if cmd in ("sound_on", "sound_off"):
                CONFIG["beep"] = cmd == "sound_on"
                save_setting("beep", CONFIG["beep"])
                log("Sound " + ("on" if CONFIG["beep"] else "off"))
            if cmd in ("indicator_on", "indicator_off"):
                indicator.set_visible(cmd == "indicator_on")

        if now - g["last_check"] > 3:
            g["last_check"] = now
            rect = find_game_rect()
            if (rect is not None) != g["found"] or (rect and rect != g["rect"]):
                g["found"] = rect is not None
                if rect:
                    g["rect"] = rect
                    det.arrows_pos = None
                    apply_calibration()
                    alert.place(*rect)
                    indicator.place(*rect)
                describe()

        if not g["found"]:
            set_state("nogame")
            root.after(1000, tick)
            return

        sw, sh = g["rect"][0], g["rect"][1]
        try:
            a, b = det.check(grab, sw, sh,
                             need_banner=now - state["arrows_seen"] < CONFIG["arrows_memory_seconds"])
        except Exception as e:
            print("capture error:", e)
            set_state("error")
            root.after(1000, tick)
            return
        remember_scales()
        arrows_now = a >= CONFIG["arrows_threshold"]
        banner_now = b >= CONFIG["banner_threshold"]
        if arrows_now:
            if now - state["arrows_seen"] >= CONFIG["arrows_memory_seconds"]:
                log(f"Delirium arrows detected (score {a:.2f}, size x{det.arrows.scale}, at {det.arrows_pos})")
            state["arrows_seen"] = now
        delirium_active = now - state["arrows_seen"] < CONFIG["arrows_memory_seconds"]
        if not delirium_active and state["alerted_this_map"]:
            state["alerted_this_map"] = False      # Delirium ended / left the map: re-arm

        if debug:
            print(f"arrows={a:.2f}{'*' if arrows_now else ' '} popup={det.last['banner']:.2f} "
                  f"objective={det.last['objective']:.2f} completed={'YES' if banner_now else 'no '} "
                  f"delirium={'ON ' if delirium_active else 'off'} alert={'ON' if alert.visible else 'off'}")

        # Trigger once per map: "Map Completed" stays in the objectives list for the
        # rest of the map, so don't re-alert until Delirium has ended.
        if banner_now and not state["banner_latched"] and not state["alerted_this_map"]:
            state["banner_latched"] = True
            src = " + ".join(k for k, v in (("popup", det.last["banner"] >= CONFIG["banner_threshold"]),
                                            ("objectives list", det.last["objective"] >= CONFIG["objective_threshold"])) if v)
            log(f"Map Completed seen via {src} (popup {det.last['banner']:.2f}, "
                f"objective {det.last['objective']:.2f}); "
                f"Delirium {'running' if delirium_active else 'not seen'}")
            if delirium_active:
                state["alerted_this_map"] = True
                state["alert_since"], state["alert_limit"] = now, CONFIG["alert_timeout_seconds"]
                alert.show(); beep()
                log("ALERT shown: END DELIRIUM")
        elif not banner_now:
            state["banner_latched"] = False

        if alert.visible:
            testing = state["alert_limit"] == 5
            gone = not testing and now - state["arrows_seen"] > CONFIG["hide_when_arrows_gone_s"]
            timed_out = now - state["alert_since"] > state["alert_limit"]
            if gone or timed_out:
                alert.hide()
                if gone:
                    state["arrows_seen"] = 0.0

        if alert.visible:
            set_state("alert")
        elif now - state["arrows_seen"] < CONFIG["arrows_memory_seconds"]:
            set_state("active")
        else:
            set_state("watching")

        if now - state["last_topmost"] > 2:
            state["last_topmost"] = now
            if indicator.visible:
                force_topmost(indicator.win)
            if alert.visible:
                force_topmost(alert.win)

        root.after(int(CONFIG["poll_seconds"] * 1000), tick)

    root.after(200, tick)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        quit_app()


def test_image(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        sys.exit(f"Can't read {path}")
    sh, sw = img.shape
    # For a test file, search the whole image for both.
    CONFIG["arrows_region"] = (0, 0, 1, 1)
    det = Detector()
    a = b = pop = obj = 0.0
    for _ in range(len(CONFIG["scales"]) // 8 + 2):   # full size sweep
        a2, b2 = det.check(lambda l, t, r, bb: img[t:bb, l:r], sw, sh)
        a, b = max(a, a2), max(b, b2)
        pop, obj = max(pop, det.last["banner"]), max(obj, det.last["objective"])
    print(f"{path}: arrows={a:.3f} (need {CONFIG['arrows_threshold']}, scale {det.arrows.scale}) "
          f"popup={pop:.3f} objective={obj:.3f} -> map completed: {'YES' if b >= CONFIG['banner_threshold'] else 'no'}")


def grab_screen():
    import mss
    with mss.mss() as sct:
        out = sct.shot(mon=1, output=str(HERE / "screenshot.png"))
    print("Saved", out)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--debug", action="store_true")
    p.add_argument("--test-alert", action="store_true")
    p.add_argument("--test-image")
    p.add_argument("--grab", action="store_true")
    args = p.parse_args()
    if args.test_image:
        test_image(args.test_image)
    elif args.grab:
        grab_screen()
    else:
        run(debug=args.debug, test_alert=args.test_alert)
