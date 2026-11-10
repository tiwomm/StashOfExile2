"""2.130.0 Filter in the Ritual window (feedback: "open the poe config file and have it tell a person what line to
ctrl+f for ... to enable filter to work in the ritual window"): the game has a setting with no switch in its menus -
apply_item_filter_to_ritual in poe2_production_Config.ini - that makes your item filter apply to the Ritual altar's
Favours window. Found by Ryonnen (reddit) and shown by NeverSink. The app finds the file, says whether it's on, copies
the line to search for and opens the folder; you change it yourself (the game rewrites the file when it closes, so it
must be closed). Reads that one line only, and never opens anything else in that folder (the game keeps your login
there too).

2.130.4 (feedback: a "Turn it on" button - "ONLY if we can safely and accurately adjust that line from =false to
=true without messing with anything else"): turn_on() changes that one line and nothing else - every other byte of
the file stays as it was (checked before the file is replaced), a copy is kept in the app's data folder first, and
the new file replaces the old in one step. Only when you press the button, only while the game is closed."""
import os
import sys

KEY = "apply_item_filter_to_ritual"
FILE = "poe2_production_Config.ini"
CREDIT = "Found by Ryonnen (reddit), shown by NeverSink"


def documents():
    """Your Documents folder (where Windows really keeps it - OneDrive may have moved it)."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]
            docs = GUID(0xFDD39AD0, 0x238F, 0x46AF, (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(docs), 0, None, ctypes.byref(p)) == 0:
                out = p.value
                ctypes.windll.ole32.CoTaskMemFree(p)
                if out:
                    return out
        except Exception:                                  # (the usual place below)
            from . import buglog
            buglog.caught()
    return os.path.join(os.path.expanduser("~"), "Documents")


def config_path(docs=None):
    """-> the game's config file (it may not exist yet: the game makes it on first start)."""
    return os.path.join(docs or documents(), "My Games", "Path of Exile 2", FILE)


def shown(path, docs=None):
    """The file's place to show on screen - without your Windows user name (a screenshot may be shared)."""
    docs = docs or documents()
    try:
        rel = os.path.relpath(path, docs)
        if not rel.startswith(".."):
            return " › ".join(["Documents"] + rel.split(os.sep))
    except ValueError:
        pass
    home = os.path.expanduser("~")
    return path.replace(home, "~", 1) if path.startswith(home) else path


def read_value(path):
    """-> True / False (the line's value), None (no such line) - or raises OSError (no file)."""
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            k, sep, v = line.strip().partition("=")
            if sep and k.strip().lower() == KEY:
                return v.strip().lower() in ("true", "1", "yes")
    return None


def state(path=None):
    """-> ("on" | "off" | "missing" | "nofile", path)."""
    path = path or config_path()
    try:
        v = read_value(path)
    except OSError:
        return "nofile", path
    return ("on" if v else "off" if v is False else "missing"), path


def turn_on(path, backup_dir):
    """-> (True, note) or (False, why). Changes apply_item_filter_to_ritual=false to =true - that line only."""
    import re
    import shutil
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return False, "The game's settings file isn't there - start the game once, close it, try again."
    pat = re.compile(rb"(?im)^([ \t]*" + KEY.encode() + rb"[ \t]*=[ \t]*)(false)([ \t]*)(?=\r?$)")
    hits = list(pat.finditer(raw))
    if not hits:
        st, _p = state(path)
        if st == "on":
            return True, "It's already on."
        return False, "The line isn't in your file - start the game once, close it, try again."
    if len(hits) > 1:
        return False, "The line is in the file more than once - change it by hand (Open folder)."
    m = hits[0]
    new = raw[:m.start(2)] + b"true" + raw[m.end(2):]
    a, b = raw.split(b"\n"), new.split(b"\n")              # every line but that one is byte for byte the same
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    if len(a) != len(b) or len(diff) != 1 or KEY.encode() not in b[diff[0]].lower():
        return False, "Couldn't change it safely - change it by hand (Open folder)."
    try:
        os.makedirs(backup_dir, exist_ok=True)
        shutil.copy2(path, os.path.join(backup_dir, FILE + ".backup"))
        tmp = path + ".soe2tmp"
        with open(tmp, "wb") as f:
            f.write(new)
        os.replace(tmp, path)
    except OSError as e:
        return False, f"Couldn't save the file ({e.__class__.__name__}) - nothing was changed."
    if state(path)[0] != "on":
        return False, "It didn't take - change it by hand (Open folder)."
    return True, "Done - it's on."
