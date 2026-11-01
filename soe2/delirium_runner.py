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
    """The app talks to a helper over pipes (stdin / stdout). A windowed exe may have no sys.stdin / sys.stdout - or
    (2.40.0) stand-ins that aren't the pipes, which made the Ritual watcher read "end of input" at once and quit
    the moment it started. So in the exe, whenever the OS handle really is a pipe, open sys.stdin / sys.stdout from
    it, whatever Python set them to."""
    if sys.platform != "win32":
        return
    frozen = bool(getattr(sys, "frozen", False))
    if not frozen and sys.stdin is not None and sys.stdout is not None:
        return
    try:
        import ctypes
        import msvcrt
        k = ctypes.windll.kernel32
        k.GetStdHandle.restype = ctypes.c_void_p
        k.GetFileType.argtypes = [ctypes.c_void_p]

        def pipe(n):
            h = k.GetStdHandle(n)
            if not h or h == ctypes.c_void_p(-1).value:
                return None
            return h if k.GetFileType(h) == 3 else None          # FILE_TYPE_PIPE
        h = pipe(-10)
        if h and (frozen or sys.stdin is None):
            sys.stdin = open(msvcrt.open_osfhandle(h, os.O_RDONLY), "r", encoding="utf-8", errors="replace")
        h = pipe(-11)
        if h and (frozen or sys.stdout is None):
            sys.stdout = open(msvcrt.open_osfhandle(h, os.O_WRONLY), "w", encoding="utf-8", errors="replace")
        if sys.stderr is None:
            sys.stderr = sys.stdout
    except Exception:
        pass


def parent_pid(argv):
    """2.40.0: the app passes its process id (--parent <pid>), so a helper can tell "the app is gone" apart from
    "the pipe is broken"."""
    try:
        return int(argv[argv.index("--parent") + 1]) if "--parent" in argv else None
    except (ValueError, IndexError):
        return None


APP_MARK = "StashOfExile2_app_{pid}"     # 2.40.0: the app holds a named mutex while it runs (utilities.app_mark)


def parent_alive(pid):
    """Is the app that started this helper still running? On Windows: does its named mark still exist (it goes
    when the app ends) - nothing about the process itself is opened."""
    if not pid:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            k.OpenMutexW.restype = ctypes.c_void_p
            h = k.OpenMutexW(0x00100000, False, APP_MARK.format(pid=int(pid)))      # SYNCHRONIZE
            if not h:
                return False
            k.CloseHandle(ctypes.c_void_p(h))
            return True
        except Exception:
            return True
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def after_stdin_ends(pid, quit_fn, log=None):
    """The app's pipe ended. Normally that means the app is gone: quit. 2.40.0: if the app is still running (the
    pipe was never really connected), keep working and quit only when the app goes away."""
    import time
    if not pid or not parent_alive(pid):
        quit_fn()
        return
    if log:
        log("the app's pipe closed but the app is running - carrying on until it ends")
    while parent_alive(pid):
        time.sleep(2.0)
    quit_fn()


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
            self.pid = parent_pid(argv)
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
            after_stdin_ends(self.pid, lambda: self.commands.append("quit"))     # the app is gone: so are we

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
