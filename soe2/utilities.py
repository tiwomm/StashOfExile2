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
MUTEX = "PoE2DeliriumAlert_single_instance"             # the name the alert uses to allow only one copy
NEEDS = ("cv2", "mss", "numpy", "PIL")
STATES = {"watching": "Watching", "active": "Delirium active in this map", "alert": "ALERT showing: END DELIRIUM",
          "nogame": "Waiting for the game window", "error": "Screen capture problem", "move": "Moving the splinter",
          "stopped": "Stopped", "starting": "Starting…"}


def _no_window():
    return 0x08000000 if sys.platform == "win32" else 0     # CREATE_NO_WINDOW


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
                p.wait(timeout=4)
            except Exception:
                try:
                    p.terminate()
                    p.wait(timeout=3)
                except Exception:
                    pass
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
