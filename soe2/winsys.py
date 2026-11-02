"""App icon, the global Ctrl+Alt+C key watcher and the system tray.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import sys
import threading
import time
from .config import APP_TITLE


# ------------------------------------------------------------------ icon + system tray
ICON_B64 = (                    # 2.60.0: a stash chest with a toolbox lid and a hex-nut lock (tools/make_icon.py)
    "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"
)


def app_icon_image():
    """The app icon as a PIL image (None if pillow is missing)."""
    try:
        import base64, io
        from PIL import Image
        return Image.open(io.BytesIO(base64.b64decode("".join(ICON_B64.split())))).convert("RGBA")
    except Exception:
        return None


DOUBLE_TAP = 0.5                   # 2.25.0: two Esc presses this close together = a double tap


class KeyWatch:
    """Notices when YOU press Ctrl+Alt+C. Windows marks key presses sent by other programs (Sidekick) as 'injected',
    so those are ignored. Needs nothing installed."""

    def __init__(self):
        self.combo_time, self.active, self.err = 0.0, False, None
        self.esc_since = 0.0        # 2.24.0: when Esc went down (0 = it's up)
        self.esc_last = 0.0         # 2.25.0: the last fresh Esc press, and when two came quickly (a double tap)
        self.esc_double = 0.0
        self.ctrl = self.alt = self.shift = False
        self.listener = None        # 2.0: f(vk, ctrl, alt, shift) -> True to swallow the key (Utilities hotkeys)
        self._swallowed = set()
        self.mouse_on, self._mouse_hook, self._tid = False, None, None     # 2.0 beta 17: mouse buttons as hotkeys

    def note_esc(self, down, up, now=None):
        """2.25.0: Esc went down / up. Two fresh presses within DOUBLE_TAP = a double tap (esc_double); a held key's
        repeats aren't fresh presses."""
        now = time.time() if now is None else now
        if down and not self.esc_since:
            self.esc_since = now
            if now - self.esc_last <= DOUBLE_TAP:
                self.esc_double = now
            self.esc_last = now
        elif up:
            self.esc_since = 0.0

    def set_mouse(self, on):
        """Watch the middle / side mouse buttons too (only while a hotkey uses one, or a key box is waiting: a mouse
        hook sees every mouse move, so it is off when nothing needs it)."""
        on = bool(on)
        if on == self.mouse_on:
            return
        self.mouse_on = on
        if sys.platform == "win32" and self._tid:
            try:
                import ctypes
                ctypes.windll.user32.PostThreadMessageW(self._tid, 0x8001 if on else 0x8002, 0, 0)
            except Exception:
                pass

    def start(self):
        if sys.platform == "win32":
            threading.Thread(target=self._run, daemon=True).start()

    def combo_recent(self, secs=1.5):
        return time.time() - self.combo_time < secs

    def _run(self):
        try:
            import ctypes
            from ctypes import wintypes
            user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
            LRESULT = ctypes.c_ssize_t

            class KBD(ctypes.Structure):
                _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD), ("flags", wintypes.DWORD),
                            ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]
            HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
            user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
            user32.SetWindowsHookExW.restype = wintypes.HHOOK
            user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
            user32.CallNextHookEx.restype = LRESULT
            user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
            kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
            kernel32.GetModuleHandleW.restype = wintypes.HMODULE

            def proc(n, w, l):
                try:
                    if n >= 0:
                        k = ctypes.cast(l, ctypes.POINTER(KBD)).contents
                        if not (k.flags & 0x10):                    # 0x10 = injected by a program, not your keyboard
                            down, up = w in (0x100, 0x104), w in (0x101, 0x105)
                            vk = k.vkCode
                            if vk in (0xA2, 0xA3, 0x11):
                                self.ctrl = down or (self.ctrl and not up)
                            elif vk in (0xA4, 0xA5, 0x12):
                                self.alt = down or (self.alt and not up)
                            elif vk in (0xA0, 0xA1, 0x10):
                                self.shift = down or (self.shift and not up)
                            elif vk == 0x43 and down and self.ctrl and self.alt:
                                self.combo_time = time.time()
                            if vk == 0x1B:                                   # Esc: never swallowed, only timed
                                self.note_esc(down, up)
                            if up and vk in self._swallowed:            # the release of a key we acted on
                                self._swallowed.discard(vk)
                                return 1
                            if down and self.listener and vk not in (0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x10, 0x11, 0x12):
                                if self.listener(vk, self.ctrl, self.alt, self.shift):
                                    self._swallowed.add(vk)
                                    return 1                            # the key did something: the game doesn't get it
                except Exception:
                    pass
                return user32.CallNextHookEx(None, n, w, l)
            self._proc = HOOKPROC(proc)                             # keep a reference or Python frees it
            hook = user32.SetWindowsHookExW(13, self._proc, kernel32.GetModuleHandleW(None), 0)
            if not hook:
                self.err = "Windows refused the keyboard hook"
                return

            class MSLL(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG), ("mouseData", wintypes.DWORD),
                            ("flags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

            def mproc(n, w, l):
                # only the middle and side buttons matter; everything else (moves, left / right clicks) goes straight on
                try:
                    if n >= 0 and w in (0x207, 0x208, 0x20B, 0x20C):
                        m = ctypes.cast(l, ctypes.POINTER(MSLL)).contents
                        if not (m.flags & 0x01):                    # 0x01 = injected by a program
                            vk = 0x04 if w in (0x207, 0x208) else (0x05 if (m.mouseData >> 16) == 1 else 0x06)
                            if w in (0x208, 0x20C):
                                if vk in self._swallowed:
                                    self._swallowed.discard(vk)
                                    return 1
                            elif self.listener and self.listener(vk, self.ctrl, self.alt, self.shift):
                                self._swallowed.add(vk)
                                return 1
                except Exception:
                    pass
                return user32.CallNextHookEx(None, n, w, l)
            self._mproc = HOOKPROC(mproc)
            self._tid = kernel32.GetCurrentThreadId()
            if self.mouse_on:
                self._mouse_hook = user32.SetWindowsHookExW(14, self._mproc, kernel32.GetModuleHandleW(None), 0)
            self.active = True
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x8001 and not self._mouse_hook:              # mouse buttons wanted
                    self._mouse_hook = user32.SetWindowsHookExW(14, self._mproc, kernel32.GetModuleHandleW(None), 0)
                    continue
                if msg.message == 0x8002 and self._mouse_hook:                  # not any more
                    user32.UnhookWindowsHookEx(self._mouse_hook)
                    self._mouse_hook = None
                    continue
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as e:
            self.err, self.active = str(e), False


class Tray:
    """System tray icon. Needs:  py -m pip install pystray pillow   (without them everything else still works)."""

    def __init__(self, post):
        self.post, self.icon, self.available = post, None, False
        try:
            import pystray
            self.pystray = pystray
            self.image = app_icon_image()
            self.available = self.image is not None
        except Exception:
            self.available = False

    def show_icon(self):
        if not self.available or self.icon:
            return self.available
        try:
            ps = self.pystray
            menu = ps.Menu(ps.MenuItem("Show StashOfExile2", lambda i, it: self.post("show"), default=True),
                           ps.MenuItem("Quit", lambda i, it: self.post("quit")))
            self.icon = ps.Icon("StashOfExile2", self.image, APP_TITLE, menu)
            self.icon.run_detached()
            return True
        except Exception:
            self.icon = None
            return False

    def hide_icon(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None

    def notify(self, text):
        try:
            if self.icon:
                self.icon.notify(text, "StashOfExile2")
        except Exception:
            pass
