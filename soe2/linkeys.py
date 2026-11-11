"""Linux / Hyprland keys (#235, linux branch). Written from the fix a Linux player (Tylo) found and tested on Arch +
Hyprland 0.56 / Proton - the idea and the steps are theirs.

Windows lets the app watch keys with a keyboard hook (winsys.KeyWatch). Wayland has no global hook, so instead:

- Keys in: for every key in Settings › Keybinds the app adds a Hyprland pass-through bind (non-consuming: the game
  still gets the key) that writes the key's name to the app's own socket ($XDG_RUNTIME_DIR/stashofexile2.sock).
  Binds are added with `hyprctl eval 'hl.bind(...)'` (Lua configs), else `hyprctl keyword bindnd` (classic configs),
  each named "SoE2 <key>" so the app only adds the ones that are missing - your config file is never edited.
- Keys out: the game's Ctrl+Alt+C copy (price check key) and the chat command keys are sent with `xdotool` (X11 key
  events through XWayland - what the game hears; Wayland's virtual keyboard (`wtype`) does nothing in it), `wtype` only
  as a fallback.

Needs `socat` (the binds write with it) and `xdotool`. ToS: same as Windows - one key press, one action; the keys you
press reach the game as always."""
import os
import shutil
import socket
import subprocess
import threading
import time

from . import buglog

SOCK_NAME = "stashofexile2.sock"
TAG = "SoE2 "                         # every bind the app adds is described "SoE2 <key>"
RESYNC_SECS = 20                      # binds are checked again this often (a config reload drops them)

# our key names (overlay.VK) -> xkb key names (what Hyprland and xdotool call them)
XKB = {"esc": "Escape", "escape": "Escape", "enter": "Return", "space": "space", "tab": "Tab",
       "backspace": "BackSpace", "insert": "Insert", "ins": "Insert", "delete": "Delete", "del": "Delete",
       "home": "Home", "end": "End", "pgup": "Prior", "pageup": "Prior", "pgdn": "Next", "pagedown": "Next",
       "up": "Up", "down": "Down", "left": "Left", "right": "Right", "pause": "Pause", "break": "Pause",
       "`": "grave", "-": "minus", "=": "equal", "[": "bracketleft", "]": "bracketright", ";": "semicolon",
       "'": "apostrophe", ",": "comma", ".": "period", "/": "slash", "\\": "backslash"}
VK_XKB = {0x10: "shift", 0x11: "ctrl", 0x12: "alt", 0x0D: "Return", 0x08: "BackSpace", 0x1B: "Escape",
          0x09: "Tab", 0x20: "space"}


def sock_path():
    base = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return os.path.join(base, SOCK_NAME)


def key_line(text):
    """A key as Settings shows it ("Ctrl+D", "F6", "Esc", "Ctrl+;") -> the line its bind writes ("ctrl+d", "f6",
    "escape", "ctrl+semicolon": letters, digits, + and _ only - safe in a shell), or None (a mouse button, or not
    understood)."""
    from .overlay import parse_key, MOUSE_VKS, VK
    k = parse_key(text)
    if not k or k[0] in MOUSE_VKS:
        return None
    name = next((n for n, v in VK.items() if v == k[0]), None)
    if name is None:
        return None
    return "+".join([m for m, on in zip(("ctrl", "alt", "shift"), k[1:]) if on] + [xkb_name(name).lower()])


def line_key(line):
    """The other way: "ctrl+semicolon" -> (vk, ctrl, alt, shift), or None."""
    from .overlay import parse_key
    parts = str(line or "").strip().lower().split("+")
    back = {v.lower(): k for k, v in XKB.items()}
    name = parts[-1]
    name = back.get(name) or ("numpad" + name[3:] if name.startswith("kp_") else name)
    return parse_key("+".join(parts[:-1] + [name]))


def xkb_name(name):
    """Our key name ("d", "f6", "esc", "numpad3") -> the xkb one ("D", "F6", "Escape", "KP_3")."""
    if name in XKB:
        return XKB[name]
    if name.startswith("numpad"):
        return "KP_" + name[6:]
    if len(name) == 1 or (name[0] == "f" and name[1:].isdigit()):
        return name.upper()
    return name


def bind_parts(line):
    """"ctrl+shift+d" -> (["CTRL", "SHIFT"], "D"); "escape" -> ([], "Escape")."""
    parts = line.split("+")
    k = line_key(line)
    from .overlay import VK
    name = next((n for n, v in VK.items() if k and v == k[0]), parts[-1])
    return [m.upper() for m in parts[:-1]], xkb_name(name)


def write_cmd(line, path=None):
    """The command a bind runs: the key's line to the app's socket."""
    return f"echo {line} | socat - UNIX-CONNECT:{path or sock_path()}"


def lua_bind(line, path=None):
    mods, key = bind_parts(line)
    keys = "+".join(mods + [key])
    return (f'hl.bind("{keys}", hl.dsp.exec_cmd("{write_cmd(line, path)}"), '
            f'{{ non_consuming = true, description = "{TAG}{line}" }})')


def keyword_bind(line, path=None):
    mods, key = bind_parts(line)
    return f"{' '.join(mods)}, {key}, {TAG}{line}, exec, {write_cmd(line, path)}"


def wanted_lines(keys):
    """Key texts -> the lines to bind (no repeats). Ctrl+Alt+C (Bulk Pricing) and Ctrl+C are always there - the
    app needs to know you pressed them, like on Windows."""
    out = []
    for t in list(keys) + ["Ctrl+Alt+C", "Ctrl+C"]:
        ln = key_line(t) if t else None
        if ln and ln not in out:
            out.append(ln)
    return out


def bound_lines(binds):
    """Hyprland's j/binds -> the lines the app already bound."""
    return {str(b.get("description"))[len(TAG):] for b in binds or [] if isinstance(b, dict)
            and str(b.get("description") or "").startswith(TAG)}


def hyprctl(*args, run=subprocess.run):
    try:
        r = run(["hyprctl", *args], capture_output=True, text=True, timeout=3)
        return r.returncode == 0 and "error" not in (r.stdout or "").lower() and "invalid" not in (r.stdout or "").lower()
    except (OSError, subprocess.SubprocessError):
        return False


def sync_binds(keys, binds=None, run=subprocess.run):
    """Add the missing pass-through binds -> the lines added."""
    from .linsys import hypr
    if binds is None:
        binds = hypr("j/binds")
    have = bound_lines(binds)
    added = []
    for ln in wanted_lines(keys):
        if ln in have:
            continue
        if hyprctl("eval", lua_bind(ln), run=run) or hyprctl("keyword", "bindnd", keyword_bind(ln), run=run):
            added.append(ln)
        else:
            buglog.debug("Keys", f"Hyprland didn't take the bind for {ln}")
    return added


class LinuxKeys:
    """The socket side of KeyWatch on Hyprland: each line is one key you pressed."""

    def __init__(self, on_line, keys_source, path=None):
        self.on_line, self.keys_source, self.path = on_line, keys_source, path or sock_path()
        self.err = None

    def start(self):
        missing = [t for t in ("socat", "xdotool") if not shutil.which(t)]
        if missing:
            buglog.debug("Keys", "missing on this system: " + ", ".join(missing))
        threading.Thread(target=self.listen, daemon=True).start()
        threading.Thread(target=self.binds_loop, daemon=True).start()

    def listen(self):
        try:
            if os.path.exists(self.path):
                os.unlink(self.path)                  # (left by an earlier run)
            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            srv.bind(self.path)
            os.chmod(self.path, 0o600)                # (only you can write keys to it)
            srv.listen(8)
        except OSError as e:
            self.err = f"key socket: {e}"
            return
        while True:
            try:
                conn, _ = srv.accept()
                with conn:
                    conn.settimeout(1.0)
                    data = b""
                    while len(data) < 256:
                        b = conn.recv(256)
                        if not b:
                            break
                        data += b
                for ln in data.decode("utf-8", "replace").split():
                    self.on_line(ln.strip().lower())
            except Exception:
                buglog.caught()

    def binds_loop(self):
        while True:
            try:
                added = sync_binds(self.keys_source())
                if added:
                    buglog.debug("Keys", f"Hyprland binds added: {len(added)}")
            except Exception:
                buglog.caught()
            time.sleep(RESYNC_SECS)


# ---------------------------------------------------------------- keys out (xdotool; wtype as a fallback)
def _run(cmd, run=subprocess.run):
    try:
        return run(cmd, capture_output=True, timeout=2).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def send_copy(run=subprocess.run, sleep=time.sleep):
    """The game's Ctrl+Alt+C once (Shift let go first), keys held ~10 ms like other price-check tools."""
    if shutil.which("xdotool"):
        _run(["xdotool", "keyup", "shift"], run)
        ok = _run(["xdotool", "keydown", "ctrl+alt+c"], run)
        sleep(0.01)
        _run(["xdotool", "keyup", "ctrl+alt+c"], run)
        if ok:
            return True
    if shutil.which("wtype"):
        return _run(["wtype", "-m", "shift", "-M", "ctrl", "-M", "alt", "c", "-m", "alt", "-m", "ctrl"], run)
    return False


def vk_xkb(vk):
    """A Windows key code -> the xkb name xdotool takes."""
    if vk in VK_XKB:
        return VK_XKB[vk]
    from .overlay import VK
    name = next((n for n, v in VK.items() if v == vk), None)
    return xkb_name(name).lower() if name and len(name) == 1 else (xkb_name(name) if name else None)


def send_keys(events, run=subprocess.run):
    """overlay._send_keys' events [(vk or None, char or None, up)] through xdotool."""
    if not shutil.which("xdotool"):
        return False
    for vk, ch, up in events:
        if ch:
            if not up:
                _run(["xdotool", "type", "--delay", "0", ch], run)
            continue
        name = vk_xkb(vk)
        if name:
            _run(["xdotool", "keyup" if up else "keydown", name], run)
    return True
