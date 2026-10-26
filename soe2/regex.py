"""Stash-search strings for tablets, waystones and relics (1.44), and a tester that runs one against copied item text.

The game's stash search: each "quoted term" is a regular expression (case doesn't matter), terms separated by spaces
must ALL match, "a|b" inside one term means either, and a term starting with ! must NOT match. It searches every line
of the item (name, properties, mods), so a term must not match anything but the mod it is meant for.

regexdata.json (tools/build_regexdata.py, from RePoE's export of the game data) gives every mod a short TOKEN: the
cheapest piece of its text found in no other mod of that item type and in none of the item's other lines.
A minimum value turns a token into  <number at least N><the text between>token  on the same line."""
import json
import os
import re
import threading

from .config import APP_DIR, P, RESOURCE_DIR

LIMIT = 250                      # the game's search box takes at most this many characters
_lock = threading.Lock()
_data = None

KINDS = ("tablet", "waystone", "relic")
TABLET_TYPES = ("Irradiated", "Ritual", "Delirium", "Breach", "Abyss", "Temple", "Overseer", "Expedition")
RARITIES = ("Rare", "Magic", "Normal")
RELIC_SIZES = {"Small": ("Urn", "Seal"), "Medium": ("Amphora", "Tapestry"), "Large": ("Vase", "Coffer", "Incense")}
# Waystone properties (the numbers the game adds up from the mods): label words that start that line
WAYSTONE_PROPS = (("item_rarity", "Item Rarity", "m rar"), ("drop_chance", "Waystone Drop Chance", "p c"),
                  ("pack_size", "Pack Size", "k s"), ("monster_rarity", "Monster Rarity", "r rar"),
                  ("effectiveness", "Monster Effectiveness", "r ef"))      # label words, and the short cue for that line


def load():
    global _data
    with _lock:
        if _data is None:
            path = next((p for p in (P("regexdata.json"), os.path.join(RESOURCE_DIR, "regexdata.json"),
                                     os.path.join(APP_DIR, "regexdata.json")) if os.path.isfile(p)), None)
            try:
                with open(path, encoding="utf-8") as f:
                    _data = json.load(f)
            except Exception as e:
                _data = {"types": {k: {"mods": [], "noise": []} for k in KINDS},
                         "error": f"regexdata.json {'not found' if not path else 'could not be read'} ({e})"}
        return _data


def mods(kind):
    return load()["types"].get(kind, {}).get("mods", [])


def by_id(kind):
    return {m["id"]: m for m in mods(kind)}


# ---------------------------------------------------------------- numbers
def _digits_from(lo):
    """A character class for 'digit lo or more': 0 -> . (any), 8 -> [89], 9 -> 9, 5 -> [5-9]."""
    return "." if lo == 0 else "9" if lo == 9 else "[89]" if lo == 8 else f"[{lo}-9]"


def at_least(n, round10=False):
    r"""Regex for a whole number >= n, as short as poe2.re writes it: 120 -> (1[2-9].|[2-9]..),  35 -> (3[5-9]|[4-9].|\d..).
    A digit after the first is written '.' (any character): the text that follows the number (a %, ' uses' ...) still has
    to match right after it, so nothing but a digit can stand there. A match inside a longer number ('35' in '135') is
    still >= n, so no word boundaries are needed. Numbers of 1,000 or more never occur on these items, so 3-digit
    minimums don't add a 4-digit case.
    round10: round n down to a multiple of 10 first (shorter still: 57 -> 50 -> ([5-9].|\d..)).
    -> None when there is nothing to filter (n rounds to 0)."""
    n = int(n)
    if round10:
        n -= n % 10
    if n <= 0:
        return None
    s = str(n)
    d = len(s)
    alts = []
    for i in range(d):
        rest = s[i + 1:]
        if rest and set(rest) == {"0"}:                   # 120: '1[2-9].' covers 120-199 in one go
            alts.append(s[:i] + _digits_from(int(s[i])) + "." * len(rest))
            break
        lo = int(s[i]) + (0 if i == d - 1 else 1)
        if lo > 9 or (i == 0 and lo == 0):
            continue
        alts.append(s[:i] + _digits_from(lo) + "." * (d - 1 - i))
    if d < 3:
        alts.append(r"\d" + "." * d)                      # one digit more (the first must be a real digit)
    alts = list(dict.fromkeys(alts))
    return alts[0] if len(alts) == 1 else "(" + "|".join(alts) + ")"


def tier_range(lo, hi):
    r"""'Waystone (Tier 15)' for tiers lo..hi, as short as possible: 14-16 -> er 1[4-6]\), 5-16 -> er ([5-9]|1[0-6])\)."""
    lo, hi = max(1, int(lo)), min(16, int(hi))
    parts = []
    a, b = lo, min(hi, 9)
    if a <= b:
        parts.append(str(a) if a == b else f"[{a}-{b}]")
    a, b = max(lo, 10), hi
    if a <= b:
        parts.append(f"1{a - 10}" if a == b else f"1[{a - 10}-{b - 10}]")
    inner = parts[0] if len(parts) == 1 else "(" + "|".join(parts) + ")"
    return f"er {inner}\\)"


def one_of(numbers):
    nums = sorted({int(x) for x in numbers})
    return str(nums[0]) if len(nums) == 1 else "(" + "|".join(str(x) for x in nums) + ")"


_SPECIAL = re.compile(r"([\\^$.|?*+()\[\]{}])")


def esc(text):
    return _SPECIAL.sub(r"\\\1", text)


# ---------------------------------------------------------------- one mod
def mod_term(m, minimum=None, round10=False):
    """The regex for one mod, optionally 'value at least minimum'."""
    tok = m["token"]
    core = tok.strip("^$")
    start, end = tok.startswith("^"), tok.endswith("$")
    line = m["line"]
    if minimum is None or "#" not in line or (m.get("min") is not None and float(minimum) <= float(m["min"])) \
            or float(minimum) != int(float(minimum)):
        return tok if (start or end) else esc(core)            # no value check: the token alone
    num = at_least(minimum, round10)
    if num is None:
        return tok if (start or end) else esc(core)
    h = line.index("#")
    t = len(line) - len(core) if end else 0 if start else line.find(core)     # an anchored token sits at the end / start
    # The character right after the number (%, a space ...) is always written out: the number pattern writes digits
    # as '.', which is only exact when fixed text follows it.
    after = line[h + 1:h + 2]
    if t > h:                                                  # number ... token
        gap = line[h + 1:t]
        mid = esc(gap) if len(gap) <= 6 else esc(after) + ".*"
        return num + mid + esc(core) + ("$" if end else "")
    gap = line[t + len(core):h]                                # token ... number
    mid = esc(gap) if len(gap) <= 6 else ".*"
    return ("^" if start else "") + esc(core) + mid + num + esc(after)


# ---------------------------------------------------------------- the whole search
def _q(term):
    return f'"{term}"'


def _num_term(prefix, n, round10, suffix="%"):
    rx = at_least(n, round10) if n else None
    return _q(f"{prefix}{rx}{suffix}") if rx else None


def build(kind, want, avoid, want_all=False, options=None):
    """want / avoid: [(mod id, minimum or None)]. options (all optional):
      rarity: ["Rare", "Magic", "Normal"]       corrupted: "only" / "not"          round10: bool
      tablet:   types: [...], uses: n
      waystone: tier_min, tier_max, revives_min, revives_max, item_rarity, drop_chance, pack_size, monster_rarity,
                effectiveness
      relic:    sizes: ["Small", "Medium", "Large"]
    -> (search string, [notes])"""
    o = options or {}
    r10 = bool(o.get("round10"))
    idx = by_id(kind)
    notes, parts = [], []
    w = [mod_term(idx[i], mn, r10) for i, mn in want if i in idx]
    a = [mod_term(idx[i], None) for i, _ in avoid if i in idx]
    if w:
        parts += [_q(t) for t in w] if want_all else [_q("|".join(w))]
    if a:
        parts.append(_q("!" + "|".join(a)))
    rar = [r for r in RARITIES if r in (o.get("rarity") or [])]
    if rar and len(rar) < len(RARITIES):                 # "Rarity: Rare" -> y: r
        letters = [r[0].lower() for r in rar]
        parts.append(_q("y: " + (letters[0] if len(letters) == 1 else "(" + "|".join(letters) + ")")))
    if kind == "tablet":
        types = [t for t in o.get("types", []) if t in TABLET_TYPES]
        if types and len(types) < len(TABLET_TYPES):
            parts.append(_q("|".join(f"{t.lower()} tab" for t in types)))
        if o.get("uses"):
            t = _num_term("", o["uses"], False, " uses")
            if t:
                parts.append(t)
    elif kind == "waystone":
        lo, hi = int(o.get("tier_min") or 1), int(o.get("tier_max") or 16)
        if lo > 1 or hi < 16:
            parts.append(_q(tier_range(lo, hi)))
        rlo, rhi = o.get("revives_min"), o.get("revives_max")
        if rlo not in (None, "") or rhi not in (None, ""):
            rlo, rhi = int(rlo or 0), int(6 if rhi in (None, "") else rhi)
            if rlo > 0 or rhi < 6:                       # "Revives Available: 3"
                parts.append(_q(f"ble: [{max(0, rlo)}-{min(9, rhi)}]" if rhi > rlo else f"ble: {rlo}"))
        for key, _label, words in WAYSTONE_PROPS:
            if o.get(key):
                t = _num_term(f"{words}.*", o[key], r10)
                if t:
                    parts.append(t)
    elif kind == "relic":
        sizes = [x for x in o.get("sizes", []) if x in RELIC_SIZES]
        if sizes and len(sizes) < len(RELIC_SIZES):
            parts.append(_q("(" + "|".join(b_.lower() for x in sizes for b_ in RELIC_SIZES[x]) + ") rel"))
    cor = o.get("corrupted")
    if cor == "only":
        parts.append(_q("corrupted"))
    elif cor == "not":
        parts.append(_q("!corrupted"))
    s = " ".join(parts)
    if len(s) > LIMIT:
        notes.append(f"{len(s)} characters: the game only takes {LIMIT}. Remove some mods, or tick Round down to 10.")
    return s, notes


# ---------------------------------------------------------------- tester
def terms(search):
    """'"a|b" !c "!d e"' -> [(negated, regex)] the way the game splits it."""
    out, i, s = [], 0, search.strip()
    while i < len(s):
        if s[i].isspace():
            i += 1
            continue
        neg = False
        if s[i] == "!":
            neg, i = True, i + 1
        if i < len(s) and s[i] == '"':
            j = s.find('"', i + 1)
            j = len(s) if j < 0 else j
            body = s[i + 1:j]
            i = j + 1
        else:
            j = i
            while j < len(s) and not s[j].isspace():
                j += 1
            body = s[i:j]
            i = j
        if body.startswith("!"):
            neg, body = True, body[1:]
        body = body.lstrip()                       # the game drops a leading space in a term
        if body:
            out.append((neg, body))
    return out


_ADV_RANGE = re.compile(r"\((-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)\)")


def plain_text(item_text):
    """What the game's search sees: a Ctrl+Alt+C copy without its { Prefix Modifier ... } lines and roll ranges
    ('13(10-15)%' -> '13%')."""
    lines = [l for l in (item_text or "").replace("\r", "").split("\n") if not l.strip().startswith("{")]
    return _ADV_RANGE.sub("", "\n".join(lines))


def test(search, item_text):
    """-> (matches?, [(term, negated, matched?, what it matched)])"""
    text = plain_text(item_text)
    rows, ok = [], True
    for neg, body in terms(search):
        try:
            m = re.search(body, text, re.I | re.M)
        except re.error as e:
            rows.append((body, neg, False, f"not a valid regex ({e})"))
            ok = False
            continue
        good = (m is None) if neg else (m is not None)
        ok = ok and good
        rows.append((body, neg, good, m.group(0) if m else ""))
    return ok, rows


def matching_mods(kind, item_text):
    """Which mods of this kind the item carries, by their tokens (for 'tick what this item has')."""
    text = plain_text(item_text)
    out = []
    for m in mods(kind):
        try:
            if re.search(mod_term(m), text, re.I | re.M):
                out.append(m["id"])
        except re.error:
            pass
    return out
