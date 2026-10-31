"""Linux / Hyprland groundwork (2.10.0). Not used on Windows: every caller checks sys.platform first.

The official builds are Windows-only. This module is the start of what a Linux build needs, so people who package
it themselves have a place to work from (see session_linux_handover.txt in the build kit / repo notes):

- the game window under Hyprland, read over Hyprland's own IPC socket (no `hyprctl` process per poll):
  $XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket.sock, commands "j/activewindow" and "j/clients";
- Path of Exile 2 is found by its Proton window class (steam_app_2694490) or its title;
- where Steam keeps Client.txt (native, ~/.steam, Flatpak, and every library in libraryfolders.vdf).

Outside Hyprland: game_active() is False, game_open() is True (we can't tell, so don't block anything) and
game_rect() is None."""
import json
import os
import re
import socket

GAME_CLASS = "steam_app_2694490"
GAME_TITLE = "Path of Exile 2"
STEAM_ROOTS = ["~/.local/share/Steam", "~/.steam/steam", "~/.steam/root",
               "~/.var/app/com.valvesoftware.Steam/.local/share/Steam"]
LOG_REL = os.path.join("steamapps", "common", "Path of Exile 2", "logs", "Client.txt")


def hypr_socket():
    """-> path of Hyprland's command socket, or None when not running under Hyprland."""
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not sig:
        return None
    base = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    for p in (os.path.join(base, "hypr", sig, ".socket.sock"), os.path.join("/tmp", "hypr", sig, ".socket.sock")):
        if os.path.exists(p):
            return p
    return None


def hypr(cmd, timeout=0.3):
    """Send one IPC command ("j/activewindow") -> parsed JSON, or None."""
    path = hypr_socket()
    if not path:
        return None
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(path)
            s.sendall(cmd.encode())
            chunks = []
            while True:
                b = s.recv(65536)
                if not b:
                    break
                chunks.append(b)
        return json.loads(b"".join(chunks).decode("utf-8", "replace") or "null")
    except (OSError, ValueError):
        return None


def is_game(win, title=GAME_TITLE):
    if not isinstance(win, dict):
        return False
    return win.get("class") == GAME_CLASS or win.get("initialClass") == GAME_CLASS or \
        (title or GAME_TITLE).lower() in str(win.get("title") or "").lower()


def active_window():
    w = hypr("j/activewindow")
    return w if isinstance(w, dict) and w else None


def game_window(title=GAME_TITLE):
    clients = hypr("j/clients")
    if not isinstance(clients, list):
        return None
    return next((c for c in clients if is_game(c, title)), None)


def game_active(title=GAME_TITLE):
    """Is the game the window in front? False outside Hyprland."""
    return is_game(active_window(), title)


def game_open(title=GAME_TITLE):
    """Is the game running? True when we can't tell (outside Hyprland)."""
    if hypr_socket() is None:
        return True
    return game_window(title) is not None


def game_rect(title=GAME_TITLE):
    """-> (left, top, width, height) of the game window, or None."""
    w = game_window(title)
    try:
        (x, y), (ww, hh) = w["at"], w["size"]
        return int(x), int(y), int(ww), int(hh)
    except (TypeError, KeyError, ValueError):
        return None


def app_in_front(pid=None):
    """Is one of this app's own windows in front (Hyprland)? None when we can't tell."""
    w = active_window()
    if w is None:
        return None
    return w.get("pid") == (pid or os.getpid())


def steam_libraries(roots=None):
    """Every Steam library folder: the Steam roots plus the paths in steamapps/libraryfolders.vdf."""
    out = []
    for r in roots or STEAM_ROOTS:
        r = os.path.expanduser(r)
        if not os.path.isdir(r):
            continue
        out.append(r)
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        try:
            with open(vdf, encoding="utf-8", errors="replace") as f:
                out += re.findall(r'"path"\s+"([^"]+)"', f.read())
        except OSError:
            pass
    seen, uniq = set(), []
    for p in out:
        k = os.path.realpath(p)
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def log_candidates(roots=None):
    """Where Client.txt may be on Linux (Steam + Proton)."""
    return [os.path.join(lib, LOG_REL) for lib in steam_libraries(roots)]
