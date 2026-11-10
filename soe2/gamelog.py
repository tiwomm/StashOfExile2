"""Reading Path of Exile 2's own log file, Client.txt (2.0 beta 9), for the session tracker.

Only reads a text file the game writes on your PC: it never touches the game, its memory, its servers or your input.
The file grows forever (often hundreds of MB), so it is never loaded whole: the reader jumps to the end, looks back a
little to learn where you are now, then only reads lines the game adds after that.

Lines used (seen in a real PoE 2 log, Oct 2026):
  2026/10/25 17:04:22 ... [DEBUG Client 24908] Generating level 80 area "MapSunTemple" with seed 1312512231
  2026/10/25 17:04:22 ... [INFO Client 24908] [SCENE] Set Source [Sun Temple]
  2026/10/25 17:04:11 ... [DEBUG Client 24908] local player sold an item for 610 gold
  2026/10/25 17:10:56 ... [INFO Client 24908] [WINDOW] Lost focus
  2026/10/26 13:10:02 ... [INFO Client 21412] : ExampleWitch has been slain.        (anyone in your area, you too)
  2026/10/26 12:14:20 ... [INFO Client 21412] : ExampleWitch has joined the area.    (OTHER players only)
  2026/10/26 14:25:27 ... [INFO Client 21412] : AFK mode is now ON. Autoreply "This player is AFK."
Going back into the same map through its portal logs the same area with the SAME seed; a new map has a new seed.
Hideouts and towns have seed 1. "has been slain" is logged for party members too, and your own joins aren't logged,
so a name that joins or leaves your area is someone else (2.7.0: only your own deaths count)."""
import os
import re
import string
import sys
from datetime import datetime

LINE = re.compile(r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \S+ \S+ \[(\w+) Client \d+\] (.*)$")
AREA = re.compile(r'Generating level (\d+) area "([^"]+)" with seed (\d+)')
SCENE = re.compile(r"\[SCENE\] Set Source \[(.+)\]")
# 2.130.2 (feedback: died, exited to character selection, came back on another character - the Ritual reminder came):
# going through the character screen connects to the login server again (seen in a real log, Nov 2026):
#   ... [INFO Client 17636] Async connecting to wdc.login.pathofexile2.com:21268
LOGIN = re.compile(r"^Async connecting to \S*login\.", re.I)
GOLD = re.compile(r"local player sold an item for ([\d,]+) gold")
SLAIN = re.compile(r"^: (.+) has been slain\.")           # 2.7.0: confirmed in a real PoE 2 log (anyone in the area)
PARTY = re.compile(r"^: (.+) has (joined|left) the area\.")
AFK_ON = re.compile(r"AFK mode is now ON", re.I)
AFK_OFF = re.compile(r"AFK mode is now OFF", re.I)
FOCUS = re.compile(r"\[WINDOW\] (Lost|Gained) focus", re.I)
LEVELUP = re.compile(r"^: (.+?) \(([^)]+)\) is now level (\d+)")     # 2.73.1: League Focus (new characters)
# 2.9.0, seen in a real PoE 2 log (Oct 2026), twice within 2 s:
#   2026/10/27 04:50:56 ... [INFO Client 27512] : <brequelwarning>{Stored Hiveblood is almost at the maximum!}
# 2.98.5: a game message that an omen was used up. confirmed - ": Omen of  Amelioration in your inventory
# has been consumed" (two spaces; a death line follows). Only the game's own messages (": ..."), never chat.
OMEN = re.compile(r"\b(Omen\s+of\s+(?:the\s+)?[A-Z][\w']*(?:\s+[A-Z][\w']*)*)")
OMEN_USED = re.compile(r"\b(consum|used up|activat|trigger)", re.I)
BREACH_WARN = re.compile(r"^: <brequelwarning>\{([^}]*)\}")
#   ... : <brequelwarning>{Cannot store any more Hiveblood! Go to the Genesis Tree to consume it.}   (2.10.0)
#   ... [WARN Client 27512] "BrequelTreeBreachstonesSlot" is missing from ...   (logged while the Brequel tree is open)
BREQUEL_TREE = re.compile(r'^"BrequelTree')

LOOKBACK = 256 * 1024          # bytes read before the end at start-up, to find the area you are in now


def candidates():
    """Where Client.txt usually is: Steam and the standalone client, on every drive letter."""
    rels = [r"Program Files (x86)\Steam\steamapps\common\Path of Exile 2\logs\Client.txt",
            r"Program Files\Steam\steamapps\common\Path of Exile 2\logs\Client.txt",
            r"SteamLibrary\steamapps\common\Path of Exile 2\logs\Client.txt",
            r"Steam\steamapps\common\Path of Exile 2\logs\Client.txt",
            r"Program Files (x86)\Grinding Gear Games\Path of Exile 2\logs\Client.txt",
            r"Program Files\Grinding Gear Games\Path of Exile 2\logs\Client.txt",
            r"Grinding Gear Games\Path of Exile 2\logs\Client.txt",
            r"Games\Path of Exile 2\logs\Client.txt"]
    if os.name != "nt":                      # 2.10.0: Linux (Steam / Proton) - see linsys.py
        if sys.platform.startswith("linux"):
            from .linsys import log_candidates
            return log_candidates()
        return []
    out = []
    for d in string.ascii_uppercase[2:]:
        root = f"{d}:\\"
        if not os.path.exists(root):
            continue
        out += [os.path.join(root, r) for r in rels]
    return out


FOUND = {}


def installed_game_dirs():
    """2.130.3 (feedback: a player who installs games elsewhere got nothing - Client.txt wasn't found): where Windows
    says Path of Exile 2 is installed (its list of installed programs - Steam and the standalone client both put it
    there). Only the registry is read; the game itself is never touched."""
    if os.name != "nt":
        return []
    out = []
    try:
        import winreg
        for hive, base in ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                           (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                           (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")):
            try:
                root = winreg.OpenKey(hive, base)
            except OSError:
                continue
            with root:
                for n in range(winreg.QueryInfoKey(root)[0]):
                    try:
                        with winreg.OpenKey(root, winreg.EnumKey(root, n)) as k:
                            name = str(winreg.QueryValueEx(k, "DisplayName")[0])
                            if "path of exile 2" in name.lower():
                                out.append(str(winreg.QueryValueEx(k, "InstallLocation")[0]))
                    except OSError:
                        continue
    except Exception:
        from . import buglog
        buglog.caught()
        return out
    return [d for d in out if d]


def steam_libraries():
    """2.130.3: every Steam library folder (Steam's own libraryfolders.vdf), on any drive or folder."""
    if os.name != "nt":
        return []
    roots = []
    try:
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
            try:
                with winreg.OpenKey(hive, key) as k:
                    for name in ("SteamPath", "InstallPath"):
                        try:
                            roots.append(winreg.QueryValueEx(k, name)[0])
                        except OSError:
                            pass
            except OSError:
                pass
    except Exception:
        from . import buglog
        buglog.caught()
    libs = []
    for r in roots + [r"C:\Program Files (x86)\Steam"]:
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        try:
            with open(vdf, encoding="utf-8", errors="replace") as f:
                libs += [m.replace("\\\\", "\\") for m in re.findall(r'"path"\s+"([^"]+)"', f.read())]
        except OSError:
            continue
    return list(dict.fromkeys(os.path.normpath(x) for x in libs + roots if x))


def more_candidates():
    """2.130.3: where Windows says the game is installed, then every Steam library."""
    out = [os.path.join(d, "logs", "Client.txt") for d in installed_game_dirs()]
    out += [os.path.join(lib, "steamapps", "common", "Path of Exile 2", "logs", "Client.txt") for lib in steam_libraries()]
    return out


def find_log(saved=None):
    """-> path of Client.txt or None. A path you picked yourself wins. 2.130.3: then the usual places, then the
    game's install folder (as Windows lists it) and every Steam library (games installed anywhere)."""
    if saved and os.path.isfile(saved):
        return saved
    if FOUND.get("p") and os.path.isfile(FOUND["p"]):
        return FOUND["p"]
    for p in candidates():
        if os.path.isfile(p):
            return p
    import time
    if time.time() - FOUND.get("t", 0) < 20:          # (the slower look: at most every 20 s)
        return None
    FOUND["t"] = time.time()
    try:
        for p in more_candidates():
            if os.path.isfile(p):
                FOUND["p"] = p
                return p
    except Exception:
        from . import buglog
        buglog.caught()
    return None


def parse(line):
    """One log line -> (kind, timestamp, data) or None."""
    m = LINE.match(line.rstrip("\r\n"))
    if not m:
        return None
    try:
        ts = datetime.strptime(m.group(1), "%Y/%m/%d %H:%M:%S").timestamp()
    except ValueError:
        return None
    text = m.group(3)
    a = AREA.search(text)
    if a:
        return "area", ts, {"level": int(a.group(1)), "area": a.group(2), "seed": int(a.group(3))}
    if LOGIN.search(text):
        return "login", ts, {}                    # (no server name kept)
    s = SCENE.search(text)
    if s:
        name = s.group(1)
        return ("scene", ts, {"name": name}) if name != "(null)" else None
    g = GOLD.search(text)
    if g:
        return "gold", ts, {"amount": int(g.group(1).replace(",", ""))}
    d = SLAIN.search(text)
    if d:
        return "death", ts, {"who": d.group(1)}
    lv = LEVELUP.search(text)
    if lv:
        return "level", ts, {"who": lv.group(1), "cls": lv.group(2), "level": int(lv.group(3))}
    p = PARTY.search(text)
    if p:
        return "party", ts, {"who": p.group(1), "joined": p.group(2) == "joined"}
    if AFK_ON.search(text):
        return "afk", ts, {"on": True}
    if AFK_OFF.search(text):
        return "afk", ts, {"on": False}
    f = FOCUS.search(text)
    if f:
        return "focus", ts, {"on": f.group(1).lower() == "gained"}
    b = BREACH_WARN.search(text)
    if b:
        return "breach", ts, {"text": b.group(1).strip()}
    if BREQUEL_TREE.search(text):
        return "brequel_tree", ts, {}
    if text.startswith(": ") and "Omen of" in text:     # 2.98.5: an omen was used up (map supplies)
        o = OMEN.search(text)
        if o and OMEN_USED.search(text):
            return "omen", ts, {"name": " ".join(o.group(1).split())}
    if text.startswith("@From "):                       # 2.98.1: a whisper TO you (Trade Whisper Watcher)
        from .whispers import parse_from
        w = parse_from(text)
        if w:
            return "whisper", ts, {"who": w[0], "msg": w[1]}
    return None


def area_kind(area, seed, level=0):
    """'map' (anything the tracker counts as a run: maps, towers, unique maps, citadels, pinnacle fights, league
    areas - see maplib), 'hideout', 'town' or 'other' (campaign ...). 2.32.0: from the Map library; claimable
    hideouts ("MapHideout...") are hideouts now, not maps."""
    from .maplib import area_kind as kind
    return kind(area, seed, level)


class LogReader:
    """Follows Client.txt from its end. poll() -> new events since the last call (call it about once a second)."""

    def __init__(self, path):
        self.path = path
        self.pos = None
        self.buf = b""
        self.error = ""

    def start(self):
        """Jump near the end. -> the events in the last bit of the file (to learn the current area)."""
        try:
            size = os.path.getsize(self.path)
            with open(self.path, "rb") as f:
                f.seek(max(0, size - LOOKBACK))
                tail = f.read()
            self.pos = size
            self.error = ""
        except OSError as e:
            self.error = str(e)
            return []
        lines = tail.split(b"\n")[1:] if size > LOOKBACK else tail.split(b"\n")
        return [ev for ev in (parse(l.decode("utf-8", "replace")) for l in lines) if ev]

    def poll(self):
        if self.pos is None:
            self.start()
            return []
        try:
            size = os.path.getsize(self.path)
            if size < self.pos:                       # the file was cleared (or replaced): start over at its top
                self.pos, self.buf = 0, b""
            if size == self.pos:
                return []
            with open(self.path, "rb") as f:
                f.seek(self.pos)
                data = f.read(min(size - self.pos, 4 * 1024 * 1024))
            self.pos += len(data)
            self.error = ""
        except OSError as e:
            self.error = str(e)
            return []
        data = self.buf + data
        lines = data.split(b"\n")
        self.buf = lines.pop()                       # a line the game is still writing
        return [ev for ev in (parse(l.decode("utf-8", "replace")) for l in lines) if ev]
