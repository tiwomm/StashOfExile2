"""2.132.3 Ritual Identifier (feedback: "build ritual identifier"): hover a Ritual Altar in a map - its tooltip says
the type ("Tainted Ritual Altar") - and an alert card says what that type gives and what to watch out for.

Read the same way as the Temple Helper (a part of the screen round the mouse, in maps only; one look feeds both).
Nothing is kept. ToS: it only looks at the screen and shows something.

What each type does: the dangers follow the game's own danger lines (in our words); Tainted's loot (rare belts, charms,
flasks) and Queen's (10 more omens in the first Favours, a Corrupted Idol from the Queen - 0.5.2 patch notes) from
community guides."""
import re

DEFAULTS = {"on": False}
# key: (name, what it gives - "" for nothing extra, danger)
TYPES = {
    "tainted": ("Tainted", "Rare belts, charms, flasks ↑", "Boils explode when touched"),
    "queens": ("Queen's", "+10 omens in first Favours, Corrupted Idol", "Queen in the Mists boss"),
    "smothered": ("Smothered", "", "Plants drop explosive pods"),
    "infested": ("Infested", "", "Rat tornadoes chase you"),
    "sapping": ("Sapping", "", "Slows you, lowers your res"),
    "contaminated": ("Contaminated", "", "Blood waves knock you back"),
    "prowling": ("Prowling", "", "Crimson Wolves"),
    "fractured": ("Fractured", "", "Exploding corpses"),
    "plagued": ("Plagued", "", "Locust swarms"),
    "croaking": ("Croaking", "", "Plague toads"),
}
WORDS = {k: re.sub(r"[^A-Z]", "", v[0].upper()) for k, v in TYPES.items()}      # "QUEENS", "TAINTED" ...
# the danger line under the tooltip names the type too (game text, letters only)
DANGERS = {"QUEENINTHEMISTS": "queens", "WAVESOFBLOOD": "contaminated", "TORNADOESOFRATS": "infested",
           "CHAOTICBOILS": "tainted", "EXPLOSIVEPODS": "smothered", "ELEMENTALDISTURBANCE": "sapping",
           "CRIMSONWOLVES": "prowling", "EXPLODINGCORPSES": "fractured", "SWARMSOFLOCUSTS": "plagued",
           "PLAGUEBRINGINGTOADS": "croaking"}
ALTAR = re.compile(r"RITUALAL(?:TAR|T|TI)?")
SUFFIX = 4                          # a cut-off name ("NTED Ritual Altar") still counts if its last letters are this many


def cfg():
    from .config import SETTINGS
    c = SETTINGS.setdefault("ritual_id", {})
    for k, v in DEFAULTS.items():
        c.setdefault(k, v)
    return c


def letters(text):
    return re.sub(r"[^A-Z]", "", str(text).upper())


def _from_name(before):
    """The letters before "RITUALALTAR" -> a type key, or None."""
    for k, w in WORDS.items():
        if before.endswith(w):
            return k
    hits = [k for k, w in WORDS.items() if len(before) >= SUFFIX and w.endswith(before[-SUFFIX:])]
    return hits[0] if len(hits) == 1 else None


def parse(lines):
    """OCR lines -> a type key ("tainted") or None. The tooltip's "<Type> Ritual Altar" first, then its danger line.
    "... Ritual Rewards" (after it's done) doesn't count."""
    texts = [letters(t) for t, _box in lines or []]
    for s in texts:
        m = ALTAR.search(s)
        if m:
            k = _from_name(s[:m.start()])
            if k:
                return k
    for s in texts:
        for d, k in DANGERS.items():
            if d in s:
                return k
    return None


def card_text(key):
    """-> (title, sub) for the alert card: "Tainted Ritual", "Rare belts, charms, flasks ↑ · ⚠ Boils explode ..."."""
    name, gain, danger = TYPES[key]
    return f"{name} Ritual", f"{gain or 'No loot bonus'} · ⚠ {danger}"
