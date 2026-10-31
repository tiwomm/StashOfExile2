"""Slowness recorder (2.25.4): Settings > Advanced > "Record slowness". For a few minutes, a watcher thread notes every
time the window stops responding for more than STALL seconds and writes WHICH code was running at that moment
(the window thread's stack) to perf_log.txt in the data folder - so a slow spot on someone's own PC can be found and
fixed instead of guessed at. Nothing leaves the PC; it stops by itself."""
import sys
import threading
import time
import traceback

from .config import P

STALL = 0.15                    # seconds without a heartbeat = the window is stuck
BEAT_MS = 50


class PerfLog:
    def __init__(self):
        self.on = False
        self.until = 0.0
        self.beat = 0.0
        self.main_id = None
        self.lines = []
        self.stalls = 0
        self.worst = 0.0

    def start(self, root, minutes=5):
        if self.on:
            return
        self.on, self.until, self.stalls, self.worst = True, time.time() + minutes * 60, 0, 0.0
        self.main_id = threading.get_ident()
        self.beat = time.time()
        self.lines = [f"{time.strftime('%Y-%m-%d %H:%M:%S')}  slowness recorder on for {minutes} min "
                      f"(stuck > {STALL * 1000:.0f} ms is written down)"]
        self._root = root
        self._heartbeat()
        threading.Thread(target=self._watch, daemon=True).start()

    def stop(self):
        if not self.on:
            return
        self.on = False
        self.lines.append(f"{time.strftime('%H:%M:%S')}  stopped: {self.stalls} stall(s), the longest "
                          f"{self.worst * 1000:.0f} ms")
        self.write()

    def _heartbeat(self):
        if not self.on:
            return
        self.beat = time.time()
        if time.time() > self.until:
            return self.stop()
        try:
            self._root.after(BEAT_MS, self._heartbeat)
        except Exception:
            self.on = False

    def _watch(self):
        """Another thread: when the heartbeat is late, take the window thread's stack (once per stall)."""
        noted = 0.0
        while self.on:
            time.sleep(0.03)
            late = time.time() - self.beat
            if late > STALL and noted != self.beat:
                noted = self.beat
                frame = sys._current_frames().get(self.main_id)
                stack = "".join(traceback.format_stack(frame, limit=14)) if frame is not None else "(no stack)"
                self.stalls += 1
                self.lines.append(f"--- {time.strftime('%H:%M:%S')} stuck for at least {late * 1000:.0f} ms, "
                                  f"running:\n{stack}")
                while self.on and time.time() - self.beat > STALL:   # how long it really lasted
                    time.sleep(0.02)
                total = time.time() - noted
                self.worst = max(self.worst, total)
                self.lines.append(f"    ... it lasted {total * 1000:.0f} ms")
                if len(self.lines) > 4000:
                    self.lines = self.lines[:1] + self.lines[-3000:]
                if self.stalls % 10 == 0:
                    self.write()

    def write(self):
        try:
            with open(P("perf_log.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(self.lines) + "\n")
        except OSError:
            pass


PERF = PerfLog()
