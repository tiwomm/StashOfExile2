"""Window / keyboard diagnostics (2.10.1). Off unless the file diag_on.txt exists in the data folder.

Writes diag_log.txt (data folder, kept under ~2 MB) with what Windows and Tk each think about the keyboard and the
app's windows: every key press and click (which widget got it, which window Windows has in front and gives the
keyboard to, whether a Tk grab is active), focus changes, and each desktop window's state whenever the app's
window is moved, resized, minimised or restored. Nothing is sent anywhere; it's for finding the "typing stops"
and "windows vanish on resize" bugs. Delete diag_on.txt to stop it."""
import os
import sys
import time
import tkinter as tk

from .config import P

FLAG = "diag_on.txt"
LOG = "diag_log.txt"
MAX_BYTES = 2_000_000


def enabled():
    return os.path.isfile(P(FLAG))


class Diag:
    def __init__(self, app):
        self.app, self.root = app, app.root
        self.lines, self.last_snap = [], ""
        self._cfg_job = None
        r = self.root
        r.bind_all("<KeyPress>", self.on_key, add="+")
        r.bind_all("<ButtonPress>", self.on_click, add="+")
        r.bind_all("<FocusIn>", lambda e: self.on_focus(e, "FocusIn"), add="+")
        r.bind_all("<FocusOut>", lambda e: self.on_focus(e, "FocusOut"), add="+")
        r.bind("<Configure>", self.on_root_cfg, add="+")
        for seq in ("<Map>", "<Unmap>"):
            r.bind(seq, lambda e, s=seq: self.on_root_map(e, s), add="+")
        self.log(f"=== start {time.strftime('%Y-%m-%d %H:%M:%S')}  {sys.platform}  Tk {r.tk.call('info', 'patchlevel')}")
        self.root.after(1000, self.tick)
        self.root.after(2000, lambda: self.snapshot("start"))

    # ---- Windows helpers
    def _u(self):
        if sys.platform != "win32":
            return None
        import ctypes
        u = ctypes.windll.user32
        for fn in ("GetParent", "GetForegroundWindow", "GetFocus", "GetActiveWindow"):
            getattr(u, fn).restype = ctypes.c_void_p
        u.GetParent.argtypes = [ctypes.c_void_p]
        u.GetWindow.restype = ctypes.c_void_p
        u.GetWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        u.IsWindowVisible.argtypes = [ctypes.c_void_p]
        u.IsWindow.argtypes = [ctypes.c_void_p]
        u.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        return u

    def _wrap(self, w):
        u = self._u()
        try:
            return (u.GetParent(w.winfo_id()) or w.winfo_id()) if u else w.winfo_id()
        except Exception:
            return None

    def _names(self):
        """hwnd -> our name, for the root, every desktop window and every other toplevel."""
        out = {}
        try:
            out[self._wrap(self.root)] = "ROOT"
            for k, w in getattr(self.app.shell, "windows", {}).items():
                out[self._wrap(w)] = "win:" + k
            for w in self.root.winfo_children():
                if isinstance(w, tk.Toplevel) and self._wrap(w) not in out:
                    out[self._wrap(w)] = "top:" + str(w)
        except Exception:
            pass
        return out

    def _who(self, h, names):
        if not h:
            return "none"
        if h in names:
            return names[h]
        u = self._u()
        if u:
            p = u.GetParent(h)                       # a child control: say whose
            if p in names:
                return names[p] + "(child)"
            import ctypes
            buf = ctypes.create_unicode_buffer(80)
            u.GetWindowTextW(ctypes.c_void_p(h), buf, 80)
            return f"other:{h:#x}:{buf.value[:30]!r}"
        return str(h)

    def _os(self):
        u = self._u()
        if not u:
            return "os=n/a"
        n = self._names()
        return (f"fg={self._who(u.GetForegroundWindow(), n)} active={self._who(u.GetActiveWindow(), n)} "
                f"kbfocus={self._who(u.GetFocus(), n)}")

    def _state(self, w):
        try:
            return w.state()
        except Exception as e:
            return f"?{e!r}"

    def _tk(self):
        try:
            f = self.root.focus_get()
        except Exception as e:
            f = f"?{type(e).__name__}"
        try:
            g = self.root.grab_current()
        except Exception:
            g = "?"
        return f"tkfocus={f} grab={g}"

    # ---- events
    def on_key(self, e):
        self.log(f"KEY {e.keysym!r} on {e.widget} | {self._tk()} | {self._os()}")

    def on_click(self, e):
        self.log(f"CLICK b{e.num} on {e.widget} | {self._tk()} | {self._os()}")

    def on_focus(self, e, kind):
        if isinstance(e.widget, str):
            return
        self.log(f"{kind} {e.widget} detail={getattr(e, 'detail', '')}")

    def on_root_map(self, e, seq):
        if e.widget is self.root:
            self.log(f"ROOT {seq} state={self._state(self.root)}")
            self.root.after(300, lambda: self.snapshot("after root " + seq))

    def on_root_cfg(self, e):
        if e.widget is not self.root:
            return
        if self._cfg_job:
            self.root.after_cancel(self._cfg_job)
        self._cfg_job = self.root.after(400, lambda: self.snapshot("root resized/moved"))

    def tick(self):
        """Every 2 s: a snapshot only when something about the windows changed."""
        try:
            self.snapshot("tick", only_if_changed=True)
            self.flush()
        except Exception:
            pass
        self.root.after(2000, self.tick)

    def snapshot(self, why, only_if_changed=False):
        u = self._u()
        rows = [f"root geo={self.root.winfo_geometry()} state={self._state(self.root)} "
                f"desk={self.app.shell.desk.winfo_width()}x{self.app.shell.desk.winfo_height()}"
                f"@{self.app.shell.desk_origin()} on_top={self.root.attributes('-topmost')}"]
        for k, w in getattr(self.app.shell, "windows", {}).items():
            if w.state_ == "closed":
                continue
            h = self._wrap(w)
            extra = ""
            if u and h:
                ex = u.GetWindowLongW(h, -20)
                extra = (f" hwnd={h:#x} IsWindow={u.IsWindow(h)} visible={u.IsWindowVisible(h)} "
                         f"owner={self._who(u.GetWindow(h, 4), self._names())} exstyle={ex & 0xffffffff:#x}")
            rows.append(f"  {k}: app_state={w.state_} tk_state={self._state(w)} mapped={w.winfo_ismapped()} "
                        f"geo={w.winfo_geometry()} _g={w._g}{extra}")
        text = "\n".join(rows)
        if only_if_changed and text == self.last_snap:
            return
        self.last_snap = text
        self.log(f"SNAP ({why}) | {self._tk()} | {self._os()}\n{text}")

    # ---- file
    def log(self, line):
        self.lines.append(f"{time.strftime('%H:%M:%S')}.{int(time.time() * 1000) % 1000:03d} {line}")
        if len(self.lines) > 200:
            self.flush()

    def flush(self):
        if not self.lines:
            return
        path = P(LOG)
        try:
            if os.path.isfile(path) and os.path.getsize(path) > MAX_BYTES:
                os.replace(path, path + ".old")
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n".join(self.lines) + "\n")
        except OSError:
            pass
        self.lines = []


def start(app):
    if not enabled():
        return None
    try:
        return Diag(app)
    except Exception:
        return None
