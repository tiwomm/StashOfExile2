"""Runs the Delirium alert (delirium_alert.py, unchanged) as a helper process of StashOfExile2 (2.0 beta 7).

The app starts a second copy of itself with  --delirium <data folder>  (StashOfExile2.exe --delirium ..., or
python stashofexile2.py --delirium ...). That copy lands here, never loads the app, and runs the alert. Instead of its
own tray icon it is controlled by the app over stdin / stdout:

  app -> helper (one per line): test, sound_on, sound_off, quit
  helper -> app:                "state <watching|active|alert|nogame|error|move>", anything else = a message line

If the app goes away (stdin closes) the helper quits too. Its log, calibration and settings live in
<data folder>/delirium. Screen capture + OpenCV run in this process, so a slow frame never stalls the app's window."""
import json
import os
import sys
import threading
from pathlib import Path


def _reopen_std():
    """A windowed exe has no sys.stdin / sys.stdout even when the app gave it pipes: open them from the OS handles."""
    if sys.platform != "win32" or (sys.stdin is not None and sys.stdout is not None):
        return
    try:
        import ctypes
        import msvcrt
        k = ctypes.windll.kernel32
        k.GetStdHandle.restype = ctypes.c_void_p
        if sys.stdin is None:
            h = k.GetStdHandle(-10)
            if h and h != ctypes.c_void_p(-1).value:
                sys.stdin = open(msvcrt.open_osfhandle(h, os.O_RDONLY), "r", encoding="utf-8", errors="replace")
        if sys.stdout is None:
            h = k.GetStdHandle(-11)
            if h and h != ctypes.c_void_p(-1).value:
                sys.stdout = open(msvcrt.open_osfhandle(h, os.O_WRONLY), "w", encoding="utf-8", errors="replace")
        if sys.stderr is None:
            sys.stderr = sys.stdout
    except Exception:
        pass


def template_dir():
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "soe2" / "templates"
    return Path(__file__).resolve().parent / "templates"


def main(argv):
    _reopen_std()
    folder = Path(argv[0]) if argv else Path.home() / ".stashofexile2"
    folder = folder / "delirium"
    folder.mkdir(parents=True, exist_ok=True)
    out_lock = threading.Lock()

    def say(line):
        with out_lock:
            try:
                sys.stdout.write(str(line).rstrip("\n") + "\n")
                sys.stdout.flush()
            except Exception:
                pass

    import builtins
    builtins_print = builtins.print

    from . import delirium_alert as D
    D.HERE = folder
    D.TEMPLATE_DIR = template_dir()
    D.LOG_FILE = folder / "delirium_log.txt"
    D.CALIB_FILE = folder / "calibration_v2.json"
    D.SETTINGS_FILE = folder / "settings.json"
    D.CONFIG["tray"] = True                              # "tray" = our pipe below, not an icon
    D.CONFIG["indicator"] = False      # 2.10.0: no splinter over the game; the Session tracker shows if it's on
    try:
        data = json.loads(D.SETTINGS_FILE.read_text())
        if data.get("game_window_title"):
            D.CONFIG["game_window_title"] = str(data["game_window_title"])
    except Exception:
        pass
    # its messages (print) go to the app as message lines
    def relay(*a, **k):
        text = " ".join(str(x) for x in a)
        if not text.startswith("Running. Quit from the tray"):       # it has no tray here: stopped from the app
            say(text)
    D.print = relay

    class PipeTray:
        """Stands in for its tray icon: commands from the app, state back to the app."""

        def __init__(self, commands):
            self.commands = commands
            self.state = None
            threading.Thread(target=self._read, daemon=True).start()
            say("state watching")

        def _read(self):
            try:
                for line in sys.stdin:
                    cmd = line.strip()
                    if cmd:
                        self.commands.append(cmd)
            except Exception:
                pass
            self.commands.append("quit")                  # the app is gone: so are we

        def set(self, state):
            if state != self.state:
                self.state = state
                say("state " + state)

        def stop(self):
            say("state stopped")

    D.Tray = PipeTray
    test = "--test-alert" in argv
    try:
        D.run(test_alert=test)
    except Exception as e:                               # tell the app what went wrong, then end
        say(f"error {type(e).__name__}: {e}")
        builtins_print(e, file=sys.stderr)
        return 1
    return 0
