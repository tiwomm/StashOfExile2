"""App icon, the global Ctrl+Alt+C key watcher and the system tray.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import sys
import threading
import time
from .config import APP_TITLE


# ------------------------------------------------------------------ icon + system tray
ICON_B64 = (                    # 2.0 beta 13: an open treasure chest drawn for StashOfExile2 (no game art)
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


class KeyWatch:
    """Notices when YOU press Ctrl+Alt+C. Windows marks key presses sent by other programs (Sidekick) as 'injected',
    so those are ignored. Needs nothing installed."""

    def __init__(self):
        self.combo_time, self.active, self.err = 0.0, False, None
        self.ctrl = self.alt = self.shift = False
        self.listener = None        # 2.0: f(vk, ctrl, alt, shift) -> True to swallow the key (Utilities hotkeys)
        self._swallowed = set()
        self.mouse_on, self._mouse_hook, self._tid = False, None, None     # 2.0 beta 17: mouse buttons as hotkeys

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
