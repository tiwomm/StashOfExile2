"""Utilities: helpers that run alongside the price checker.

2.0 beta 7: the Delirium alert is built in. It runs as a helper process of the app (the same StashOfExile2.exe started
with --delirium, see delirium_runner.py), so screen capture never slows the app's window and a crash in it can't take
the app down. This module starts and stops it, sends it commands and keeps its state for the Delirium window.
The standalone PoE2DeliriumAlert.exe still works on its own; the two never run at the same time (same mutex)."""
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time

from .config import APP_DIR, DATA_DIR

FROZEN = bool(getattr(sys, "frozen", False))
_APP_MARK = [None]


def app_mark():
    """2.40.0: a named mutex held for as long as the app runs - a helper checks it exists to know the app is still
    there (delirium_runner.parent_alive). Windows lets it go when the app ends."""
    if sys.platform != "win32" or _APP_MARK[0]:
        return
    try:
        import ctypes
        from .delirium_runner import APP_MARK
        k = ctypes.windll.kernel32
        k.CreateMutexW.restype = ctypes.c_void_p
        _APP_MARK[0] = k.CreateMutexW(None, False, APP_MARK.format(pid=os.getpid()))
    except Exception:
        pass


MUTEX = "PoE2DeliriumAlert_single_instance"             # the name the alert uses to allow only one copy
NEEDS = ("cv2", "mss", "numpy", "PIL")
STATES = {"watching": "Watching", "active": "Delirium active in this map", "alert": "ALERT showing: END DELIRIUM",
          "nogame": "Waiting for the game window", "error": "Screen capture problem", "move": "Moving the splinter",
          "stopped": "Stopped", "starting": "Starting…"}


def _no_window():
    return 0x08000000 if sys.platform == "win32" else 0     # CREATE_NO_WINDOW


def kill_tree(p):
    """2.26.3: end a helper and everything it started. The one-file exe runs as two processes (a small starter and
    the real program): terminate() only ended the starter, the real one kept running - and kept the exe in use, so
    an update could never replace it."""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/f", "/t", "/pid", str(p.pid)], capture_output=True, timeout=5,
                           creationflags=0x08000000)
        else:
            p.terminate()
        p.wait(timeout=3)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


class DeliriumHelper:
    def __init__(self):
        self.proc = None
        self.state = "stopped"
        self.lines = []                 # what it said, newest last
        self.started_at = 0.0

    # ---- how to start it
    def locate(self):
        """-> (command to start it, working folder) or (None, reason)."""
        if FROZEN:
            return [sys.executable, "--delirium", DATA_DIR], APP_DIR
        missing = [m for m in NEEDS if importlib.util.find_spec(m) is None]
        if missing:
            names = {"cv2": "opencv-python-headless", "PIL": "pillow"}
            return None, ("The Delirium alert needs " + ", ".join(names.get(m, m) for m in missing) +
                          ". Run:  py -m pip install " + " ".join(names.get(m, m) for m in missing) + "  and restart.")
        launcher = os.path.join(APP_DIR, "stashofexile2.py")
        py = sys.executable
        pyw = os.path.join(os.path.dirname(py), "pythonw.exe")
        return [pyw if os.path.isfile(pyw) else py, launcher, "--delirium", DATA_DIR], APP_DIR

    # ---- is it running?
    def running(self):
        if self.proc is not None and self.proc.poll() is None:
            return "mine"
        if sys.platform == "win32":
            import ctypes
            h = ctypes.windll.kernel32.OpenMutexW(0x00100000, False, MUTEX)        # SYNCHRONIZE
            if h:
                ctypes.windll.kernel32.CloseHandle(h)
                return "other"                       # the standalone PoE2DeliriumAlert.exe
        return None

    def _reader(self, proc):
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                if line.startswith("state "):
                    self.state = line[6:].strip()
                else:
                    self.lines.append(line)
                    del self.lines[:-30]
        except Exception:
            pass
        if self.proc is proc:
            self.state = "stopped"

    def start(self, test=False):
        """-> None, or why it couldn't start."""
        if self.running():
            return None
        cmd, where = self.locate()
        if cmd is None:
            return where
        try:
            app_mark()
            cmd = cmd + ["--parent", str(os.getpid())]       # 2.40.0: so it can tell "app gone" from "pipe broken"
            p = subprocess.Popen(cmd + (["--test-alert"] if test else []), cwd=where, creationflags=_no_window(),
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace", bufsize=1)
        except Exception as e:
            return f"Couldn't start the Delirium alert: {e}"
        if test:
            threading.Thread(target=lambda: p.communicate(timeout=30), daemon=True).start()
            return None
        self.proc, self.state, self.lines, self.started_at = p, "starting", [], time.time()
        threading.Thread(target=self._reader, args=(p,), daemon=True).start()
        return None

    def send(self, cmd):
        if self.running() != "mine":
            return False
        try:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()
            return True
        except Exception:
            return False

    def stop(self):
        """-> None, or why it couldn't be stopped."""
        r = self.running()
        if r == "mine":
            p = self.proc
            self.send("quit")
            try:
                p.wait(timeout=3)
            except Exception:
                kill_tree(p)
            self.proc, self.state = None, "stopped"
            return None
        if r == "other":
            return "The standalone PoE2DeliriumAlert.exe is running: quit it from its tray icon (the splinter) first."
        return None

    def test_alert(self):
        """Show the END DELIRIUM banner for 5 seconds (through the running alert, or a quick one-off)."""
        if self.send("test"):
            return None
        if self.running() == "other":
            return "The standalone PoE2DeliriumAlert.exe is running: use Test alert on its tray icon."
        return self.start(test=True)

    def last_message(self):
        return "\n".join(self.lines[-3:])

    # ---- its settings (data folder/delirium/settings.json, the file the alert itself reads)
    def _settings_path(self):
        return os.path.join(DATA_DIR, "delirium", "settings.json")

    def _read(self):
        try:
            with open(self._settings_path(), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write(self, key, value):
        p = self._settings_path()
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            data = self._read()
            data[key] = value
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def get_sound(self):
        return bool(self._read().get("beep", True))

    def set_sound(self, on):
        """Sound once per map. Applies straight away when it is running."""
        self._write("beep", bool(on))
        self.send("sound_on" if on else "sound_off")

    def get_indicator(self):
        return bool(self._read().get("indicator", True))

    def set_indicator(self, on):
        """The small splinter on screen (shows the state while you play)."""
        self._write("indicator", bool(on))
        self.send("indicator_on" if on else "indicator_off")

    def set_title(self, title):
        self._write("game_window_title", title or "Path of Exile 2")


DELIRIUM = DeliriumHelper()


class RitualHelper(DeliriumHelper):
    """2.14.0: the Ritual watcher (ritual_alert.py) - the same kind of helper process, started with --ritual.
    It reports "count 2/3" / "count none" / "count unread" and "captured <file>"."""
    FLAG = "--ritual"

    def __init__(self):
        super().__init__()
        self.count = None               # (done, total) while a Ritual counter is on screen
        self.seen = "none"              # "ok" / "none" / "unread"
        self.captured = None

    def locate(self):
        cmd, where = super().locate()
        if cmd is None:
            return None, where.replace("The Delirium alert", "The Ritual watcher")
        return [("--ritual" if c == "--delirium" else c) for c in cmd], where

    def running(self):
        return "mine" if self.proc is not None and self.proc.poll() is None else None

    def _reader(self, proc):
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                if line.startswith("state "):
                    self.state = line[6:].strip()
                elif line.startswith("count "):
                    v = line[6:].strip()
                    if "/" in v:
                        a, b = v.split("/", 1)
                        self.count, self.seen = (int(a), int(b)), "ok"
                    else:
                        self.count, self.seen = None, v
                elif line.startswith("captured "):
                    self.captured = line[9:].strip()
                else:
                    self.lines.append(line)
                    del self.lines[:-30]
        except Exception:
            pass
        if self.proc is proc:
            self.state = "stopped"

    def start(self, test=False):
        if test:
            return None
        err = super().start()
        return err.replace("Delirium alert", "Ritual watcher") if err else None

    def stop(self):
        super().stop()
        self.count, self.seen = None, "none"
        return None

    def capture(self):
        return self.send("capture")


RITUAL = RitualHelper()
