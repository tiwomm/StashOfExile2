"""2.131.0 Latency (plan: "FPS / latency - a small readout, toggled only in Quick settings"): your connection to the
game server, on the overlay's bar next to the clock. The game writes its own connect time to each area's server in
its log ("Connect time to instance server was N ms"); the bar shows this area's, the hover the last 10 (middle and
range).
GGG ToS (TOS.md 5, clause 7.5): only reads the log the game writes - nothing is sent to the game's servers (no ping)."""
import re
import statistics

from .config import SETTINGS

CONNECT_MS = re.compile(r"^Connect time to instance server was (\d+)\s*ms", re.I)
KEEP = 10                            # the hover: the last 10 areas

_state = {"samples": []}


def cfg():
    c = SETTINGS.setdefault("latency", {})
    c.setdefault("on", False)
    return c


def on():
    return bool(cfg().get("on"))


def log_line(text):
    """One Client.txt message (after the [DEBUG Client n] part) -> the connect time in ms, or None."""
    m = CONNECT_MS.match(text)
    return int(m.group(1)) if m else None


def add(ms):
    _state["samples"] = (_state["samples"] + [int(ms)])[-KEEP:]


def clear():
    _state["samples"] = []


def reading():
    """-> (this area's ms or None, the middle of the last 10, (low, high), n)."""
    s = _state["samples"]
    if not s:
        return None, None, (None, None), 0
    return s[-1], int(statistics.median(s)), (min(s), max(s)), len(s)


def text():
    ms = reading()[0]
    return f"{ms} ms" if ms is not None else "- ms"


def how_text():
    """The hover: how the number was worked out."""
    ms, mid, (lo, hi), n = reading()
    if ms is None:
        return "Latency to the game server - shows once you change area (the game writes it in its log)."
    more = f" Last {n} areas: middle {mid} ms ({lo}-{hi} ms)." if n > 1 else ""
    return f"This area's server: {ms} ms - the game's own connect time, from its log.{more}"
