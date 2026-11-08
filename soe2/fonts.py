"""Bundled fonts for the overlay styles (2.110.0) - Cinzel, EB Garamond, Marcellus SC, Cormorant Garamond and
Cormorant SC, all SIL Open Font License 1.1 (the licenses sit beside them in soe2/fonts; credits in About › Credits
and the README). Loaded for this app only - nothing is installed on the PC:
  Windows: AddFontResourceExW with FR_PRIVATE (gone when the app closes)
  Linux:   FcConfigAppFontAddDir on the app's own fontconfig (Tk's Xft fonts see them)
If a font can't be loaded the styles fall back to Palatino Linotype / Segoe UI (FALLBACK)."""
import os
import sys

from .config import RESOURCE_DIR

DIR = os.path.join(RESOURCE_DIR, "soe2", "fonts")
if not os.path.isdir(DIR):                                   # (running from source: next to this file)
    DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
SERIF, HEAD = "Palatino Linotype", "Palatino Linotype"
FALLBACK = {"Cinzel": SERIF, "EB Garamond": SERIF, "Marcellus SC": SERIF, "Cormorant Garamond": SERIF,
            "Cormorant SC SemiBold": SERIF}
_LOADED = [None]


def load():
    """Make the bundled fonts usable by Tk. -> True when they were loaded (once per run)."""
    if _LOADED[0] is not None:
        return _LOADED[0]
    ok = False
    try:
        files = [os.path.join(DIR, f) for f in sorted(os.listdir(DIR)) if f.lower().endswith(".ttf")]
    except OSError:
        files = []
    if files and sys.platform == "win32":
        try:
            import ctypes
            add = ctypes.windll.gdi32.AddFontResourceExW
            ok = all(add(f, 0x10, 0) > 0 for f in files)        # 0x10 = FR_PRIVATE
        except Exception:
            ok = False
    elif files:
        try:
            import ctypes
            import ctypes.util
            name = ctypes.util.find_library("fontconfig") or "libfontconfig.so.1"
            fc = ctypes.CDLL(name)
            fc.FcConfigAppFontAddDir.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            ok = bool(fc.FcConfigAppFontAddDir(None, DIR.encode()))
        except Exception:
            ok = False
    _LOADED[0] = ok
    return ok


def family(name):
    """The family to ask Tk for: the bundled one when loaded, else the fallback."""
    return name if load() else FALLBACK.get(name, SERIF)
