"""Reading the Windows clipboard directly.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import sys


def read_clipboard_text():
    """Text on the Windows clipboard, read directly. '' = no text there, None = another program is holding it (retry)."""
    if sys.platform != "win32":
        return ""
    try:
        import ctypes
        from ctypes import wintypes
        u, k = ctypes.windll.user32, ctypes.windll.kernel32
        u.OpenClipboard.argtypes, u.OpenClipboard.restype = [wintypes.HWND], wintypes.BOOL
        u.GetClipboardData.argtypes, u.GetClipboardData.restype = [wintypes.UINT], wintypes.HANDLE
        k.GlobalLock.argtypes, k.GlobalLock.restype = [wintypes.HANDLE], ctypes.c_void_p
        k.GlobalUnlock.argtypes = [wintypes.HANDLE]
        if not u.OpenClipboard(None):
            return None
        try:
            h = u.GetClipboardData(13)                 # CF_UNICODETEXT
            if not h:
                return ""
            p = k.GlobalLock(h)
            if not p:
                return ""
            try:
                return ctypes.wstring_at(p)
            finally:
                k.GlobalUnlock(h)
        finally:
            u.CloseClipboard()
    except Exception:
        return None


def clip_seq():
    """Windows' clipboard change counter: goes up on EVERY copy, even if the text is identical. None elsewhere."""
    if sys.platform == "win32":
        try:
            import ctypes
            return int(ctypes.windll.user32.GetClipboardSequenceNumber())
        except Exception:
            return None
    return None


def write_clipboard_text(text):
    """Put text on the Windows clipboard (2.0 beta 8: chat commands are pasted, like Sidekick does). -> True if done."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        u, k = ctypes.windll.user32, ctypes.windll.kernel32
        u.OpenClipboard.argtypes, u.OpenClipboard.restype = [wintypes.HWND], wintypes.BOOL
        u.SetClipboardData.argtypes, u.SetClipboardData.restype = [wintypes.UINT, wintypes.HANDLE], wintypes.HANDLE
        k.GlobalAlloc.argtypes, k.GlobalAlloc.restype = [wintypes.UINT, ctypes.c_size_t], wintypes.HGLOBAL
        k.GlobalLock.argtypes, k.GlobalLock.restype = [wintypes.HGLOBAL], ctypes.c_void_p
        k.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        data = (text or "").encode("utf-16-le") + b"\0\0"
        for _ in range(10):                            # another program may hold the clipboard for a moment
            if u.OpenClipboard(None):
                break
            import time
            time.sleep(0.01)
        else:
            return False
        try:
            u.EmptyClipboard()
            h = k.GlobalAlloc(0x0002, len(data))       # GMEM_MOVEABLE
            p = k.GlobalLock(h)
            ctypes.memmove(p, data, len(data))
            k.GlobalUnlock(h)
            return bool(u.SetClipboardData(13, h))     # CF_UNICODETEXT (Windows owns the memory now)
        finally:
            u.CloseClipboard()
    except Exception:
        return False
