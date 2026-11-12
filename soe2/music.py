"""2.134.0 Music Controls (feedback: "Some keyboards have Previous Track, Pause/Play, Next Track buttons ... could we
have music controls as an in-game overlay?"): the same three commands a keyboard's media keys give, for whatever
player you use (Spotify, a browser, ...).

How: Windows - the app's own window hands Windows an app command (WM_APPCOMMAND through DefWindowProc), the way a
media key reaches the system; Windows passes it to the media player. No key is pressed or sent, nothing goes to the
game, and the game's window never sees it. Linux - playerctl, when it's installed.
GGG ToS: a click on the app's own window = one command to Windows; nothing is sent to the game."""
import shutil
import subprocess
import sys

from .config import SETTINGS

DEFAULTS = {"on": False, "x": None, "y": None}
WM_APPCOMMAND = 0x0319
COMMANDS = {"prev": 12, "play": 14, "next": 11}          # APPCOMMAND_MEDIA_PREVIOUSTRACK / PLAY_PAUSE / NEXTTRACK
PLAYERCTL = {"prev": "previous", "play": "play-pause", "next": "next"}
# (icon, name in its tooltip) - the buttons, left to right
BUTTONS = (("prev", "⏮", "Previous track"), ("play", "⏯", "Play / pause"), ("next", "⏭", "Next track"))


def cfg():
    c = SETTINGS.setdefault("music", {})
    for k, v in DEFAULTS.items():
        c.setdefault(k, v)
    return c


def lparam(what):
    """The app command in the high word, as a media key sends it (device: key)."""
    return COMMANDS[what] << 16


def send(what, hwnd=None):
    """One command to the media player -> True when it was handed over. hwnd: the app's own window (Windows)."""
    if what not in COMMANDS:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            u = ctypes.windll.user32
            u.DefWindowProcW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
            u.DefWindowProcW.restype = ctypes.c_ssize_t
            h = hwnd or u.GetDesktopWindow()
            u.DefWindowProcW(h, WM_APPCOMMAND, h, lparam(what))
            return True
        except Exception:
            return False
    exe = shutil.which("playerctl")
    if not exe:
        return False
    try:
        return subprocess.run([exe, PLAYERCTL[what]], capture_output=True, timeout=3).returncode == 0
    except Exception:
        return False
