"""2.98.1: Trade Whisper Watcher - a card over the game when someone whispers to buy an item you've listed.

Why: at league start you list items in a public stash tab and buyers whisper you ("Hi, I would like to buy your ...")
- easy to miss in a busy chat while you're running the campaign. The watcher reads the game's own log (Client.txt),
spots a whisper TO you that's a trade request, and shows a short card: the item, the price, where it sits in your tab,
and who's asking.

On by default during the campaign (a character that hasn't reached maps); Keep on after the campaign is an option.
Privacy: nothing is saved or sent - the buyer's name is shown on the card and forgotten when it closes.
GGG ToS: only reads Client.txt; never types, never invites, never sends anything to the game."""
import re

from .config import SETTINGS, save_json

DEFAULTS = {"on": True, "after": False, "sound": True, "secs": 20}

# The trade site's whisper (PoE 2, as copied from "Whisper"), sent to you and logged as:
#   @From <GUILD> Name: Hi, I would like to buy your Havoc Visage Ancestral Tiara listed for 90 divine in Rise of the
#   Abyssal (stash tab "~b/o 90 divine"; position: left 3, top 5)
# and the bulk / currency form: "Hi, I'd like to buy your 10 Chaos Orb for my 1 Divine Orb in <league>."
FROM = re.compile(r"^@From (?:<[^>]*> )?([^:]+?): (.*)$")
ASK = re.compile(r"\bI(?: would|'d) like to buy your\b", re.I)
LISTED = re.compile(r"like to buy your (?P<item>.+?) listed for (?P<price>.+?) in (?P<league>.+?)"
                    r"(?: \(stash tab \"(?P<tab>.*?)\"; position: left (?P<left>\d+), top (?P<top>\d+)\))?\.?\s*$", re.I)
BULK = re.compile(r"like to buy your (?P<item>.+?) for my (?P<price>.+?) in (?P<league>.+?)\.?\s*$", re.I)


def cfg():
    c = SETTINGS.setdefault("whispers", {})
    for k, v in DEFAULTS.items():
        c.setdefault(k, v)
    return c


def save():
    save_json("settings.json", SETTINGS)


def parse_from(text):
    """A log line's text ("@From Name: message") -> (name, message) for a whisper sent TO you, else None."""
    m = FROM.match(text or "")
    return (m.group(1).strip(), m.group(2).strip()) if m else None


def parse_trade(msg):
    """A whisper's message -> {item, price, league, tab, left, top} when it's a trade request, else None."""
    if not msg or not ASK.search(msg):
        return None
    m = LISTED.search(msg) or BULK.search(msg)
    if not m:
        return {"item": "", "price": "", "league": "", "tab": "", "left": None, "top": None}
    d = m.groupdict()
    return {"item": (d.get("item") or "").strip(), "price": (d.get("price") or "").strip(),
            "league": (d.get("league") or "").strip(), "tab": d.get("tab") or "",
            "left": int(d["left"]) if d.get("left") else None, "top": int(d["top"]) if d.get("top") else None}


def in_campaign():
    """The character you're playing hasn't reached maps (the Campaign Helper's own record)."""
    try:
        from . import campaign as CP
        run = CP.char()
        if run.get("done"):
            return False
        return CP.char_level() < CP.MAPS_LEVEL
    except Exception:
        return True


def active():
    c = cfg()
    return bool(c["on"]) and (bool(c["after"]) or in_campaign())


def where(d):
    """'Tab "~b/o 1 div" · left 3, top 5' (or '')."""
    parts = []
    if d.get("tab"):
        parts.append(f'Tab "{d["tab"]}"')
    if d.get("left") is not None and d.get("top") is not None:
        parts.append(f"left {d['left']}, top {d['top']}")
    return " · ".join(parts)
