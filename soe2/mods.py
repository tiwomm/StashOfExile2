"""Reading copied items, matching mods to trade-site stats, mod impact rules, tabs.txt / jewels.txt.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import difflib
import math
import re
from .config import load_json, P, save_json, SETTINGS


# ------------------------------------------------------------------ stat matching / parsing
VAL = re.compile(r"(-?\d+(?:\.\d+)?)(?:\((-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)\))?")


JEWEL_BASE = re.compile(r"(Time-Lost )?(Ruby|Emerald|Sapphire|Diamond)")


TABLET_BASE = re.compile(r"([A-Z][a-z]+ Tablet)")


FLAG_WORDS = ("desecrated", "fractured", "essence", "crafted")


def strip_markup(text):
    return re.sub(r"\[([^\]|]*\|)?([^\]]*)\]", r"\2", text)


def norm(text):
    text = VAL.sub("#", strip_markup(text))
    return re.sub(r"\s+", " ", text).strip().lower()


def pretty(text):
    return re.sub(r"\s+", " ", VAL.sub("#", strip_markup(text))).strip()


# The game words a negative roll as "reduced", but the trade site only lists the "increased" stat (with a negative value).
FLIP_PAIRS = (("reduced", "increased"), ("decreased", "increased"), ("less", "more"), ("slower", "faster"))


_alias_cache = {}


def _alias_for(table):
    """Trade stats carry qualifiers the game text doesn't have, e.g. '#% increased Gold found in Map (Gold Piles)'.
    This maps the text without the trailing '(...)' to those stats."""
    key = id(table)
    if key not in _alias_cache:
        alias = {}
        for k, v in table.items():
            stripped = re.sub(r"\s*\([^()#]*\)\s*$", "", k)
            if stripped != k:
                alias.setdefault(stripped, []).append((k, v))
        _alias_cache.clear()
        _alias_cache[key] = alias
    return _alias_cache[key]


_STOP = {"in", "from", "around", "are", "when", "for", "on", "at", "per", "that", "which", "within"}


def _singular(word):
    if word.endswith("sses"):
        return word[:-2]                                  # abysses -> abyss
    if word.endswith(("xes", "ches", "shes")):
        return word[:-2]                                  # strongboxes -> strongbox
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]                                  # chests -> chest, essences -> essence
    return word


def singular_wording(key):
    """'map contains # additional rare chests' -> 'map contains an additional rare chest'.
    The trade site lists some count mods only in this singular form, with no number to filter on."""
    toks = key.split()
    if "#" not in toks or "additional" not in toks:
        return None
    i = toks.index("additional")
    if i == 0 or toks[i - 1] != "#":
        return None
    j = i + 1
    while j < len(toks) and toks[j] not in _STOP:
        j += 1
    if j == i + 1:
        return None
    toks[j - 1] = _singular(toks[j - 1])
    toks[i - 1] = "an"
    return " ".join(toks)


def _plural(word):
    if word.endswith(("x", "ch", "sh", "ss", "s")):
        return word + "es"
    return word + "s"


def plural_wordings(key):
    """The reverse of singular_wording (1.43): 'ritual altars ... allow rerolling favours an additional time' ->
    {'... # additional times', '... # additional time'}. Listings with 2+ of it are written that way."""
    toks = key.split()
    if "an" not in toks or "additional" not in toks:
        return set()
    i = toks.index("additional")
    if i == 0 or toks[i - 1] != "an":
        return set()
    j = i + 1
    while j < len(toks) and toks[j] not in _STOP:
        j += 1
    if j == i + 1:
        return set()
    toks[i - 1] = "#"
    one = " ".join(toks)
    toks[j - 1] = _plural(toks[j - 1])
    return {one, " ".join(toks)}


_LINE_CACHE = {"n": -1, "map": {}}


def sid_for_line(key):
    """A listing's mod line (normalised) -> trade stat id (2.0). Exact wording first; then the other ways the game and
    the trade site write the same stat: 'reduced' for a negative 'increased', '3 additional times' for
    'an additional time', '# additional rare chest' for '# additional rare chests'."""
    sid = TEXT2SID.get(key)
    if sid:
        return sid
    if _LINE_CACHE["n"] != len(TEXT2SID):                  # rebuilt when the trade site's list changes
        m = {}
        for text, s_ in TEXT2SID.items():
            for alt in plural_wordings(text):
                m.setdefault(alt, s_)
            hs = hash_singular(text)
            if hs:
                m.setdefault(hs, s_)
        _LINE_CACHE.update(n=len(TEXT2SID), map=m)
    alias = _LINE_CACHE["map"]
    for k in [key] + [re.sub(rf"\b{a}\b", b, key, count=1) for a, b in FLIP_PAIRS if re.search(rf"\b{a}\b", key)]:
        hit = TEXT2SID.get(k) or alias.get(k)
        if hit:
            return hit
        sing = singular_wording(k)
        if sing and sing in TEXT2SID:
            return TEXT2SID[sing]
    # 2.0 beta 7: last try, the item library's own matchers (Exiled Exchange 2's wordings, plus what was learned)
    try:
        from . import gamedata
        e, _neg = gamedata.stat_for(key.replace("+#", "#"), learn=False)
        if e and e.get("trade"):
            tr = e["trade"]
            for g in ("explicit", "fractured", "desecrated", "crafted", "implicit", "enchant", "rune"):
                if tr.get(g):
                    return tr[g][0]
            ids = next((v for v in tr.values() if v), None)
            if ids:
                return ids[0]
    except Exception:
        pass
    return None


def hash_singular(key):
    """'map contains # additional azmeri spirits' -> 'map contains # additional azmeri spirit' (keeps the #)."""
    toks = key.split()
    if "#" not in toks or "additional" not in toks:
        return None
    i = toks.index("additional")
    if i == 0 or toks[i - 1] != "#":
        return None
    j = i + 1
    while j < len(toks) and toks[j] not in _STOP:
        j += 1
    if j == i + 1:
        return None
    toks[j - 1] = _singular(toks[j - 1])
    return " ".join(toks)


def find_stat(text, flags, table, ranged=None):
    """-> (stat id, group, flipped, info).
    flipped: the game said 'reduced' but the trade stat is the 'increased' one (so the value is negative).
    info: closest guess when nothing matched, or a note describing how a non-exact match was made."""
    key = norm(text)
    variants = [(key, False)]
    for a, b in FLIP_PAIRS:
        if re.search(rf"\b{a}\b", key):
            variants.append((re.sub(rf"\b{a}\b", b, key, count=1), True))
    entry, flipped, note = None, False, None
    if ranged is False:                                      # fixed number, no (a-b) range: the trade site's "an additional X" stat
        fixed = singular_wording(key)
        if fixed and fixed in table:
            entry, note = table[fixed], f"singular wording on the trade site ({fixed}) - fixed count, no roll to filter"
    elif ranged is True and not entry:                       # has a roll: the "# additional X" stat, singular spelling too
        hs = hash_singular(key)
        if key not in table and hs and hs in table:
            entry, note = table[hs], None
    for k, fl in ([] if entry else variants):                # exact text, then reduced->increased etc.
        if k in table:
            entry, flipped = table[k], fl
            note = "matched with reduced/increased swapped" if fl else None
            break
    if not entry:
        alias = _alias_for(table)
        for k, fl in variants:                               # same, ignoring a trailing "(Gold Piles)" style qualifier
            if k in alias:
                full, entry = alias[k][0]
                flipped = fl
                note = f"matched to: {full}" + (f"  (1 of {len(alias[k])} similar)" if len(alias[k]) > 1 else "")
                break
    if not entry:
        sing = singular_wording(key)
        if sing and sing in table:
            entry, note = table[sing], f"singular wording on the trade site ({sing}) - roll not filtered"
    if not entry:
        close = difflib.get_close_matches(key, table.keys(), n=1, cutoff=0.95)
        if close:
            entry, note = table[close[0]], f"matched to: {close[0]}"
    if not entry:
        g = difflib.get_close_matches(key, table.keys(), n=1, cutoff=0.7)
        return None, None, False, (g[0] if g else None)
    order = [g for g in ("crafted", "desecrated", "fractured") if g in flags] + ["explicit"]
    for g in order:
        if g in entry:
            return entry[g], g, flipped, note
    g, sid = next(iter(entry.items()))
    return sid, g, flipped, note


def read_numbers(text):
    vals, los, his = [], [], []
    for m in VAL.finditer(text):
        vals.append(float(m.group(1)))
        if m.group(2) is not None:
            los.append(float(m.group(2)))
            his.append(float(m.group(3)))
    if not vals:
        return None, None, None
    v = sum(vals) / len(vals)
    if los and len(los) == len(vals):
        return v, sum(los) / len(los), sum(his) / len(his)
    return v, None, None


def parse_item(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines or not lines[0].startswith("Item Class:"):
        return None
    cls = lines[0].split(":", 1)[1].strip().lower()
    if "tablet" in cls:                     # 1.42: any wording of the class ("Tablets", "Precursor Tablets" ...)
        kind_re, kind = TABLET_BASE, "Tablet"
    elif cls.startswith("jewel"):
        kind_re, kind = JEWEL_BASE, "Jewel"
    else:
        return None
    rarity = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("Rarity:")), "")
    if rarity not in ("Magic", "Rare"):
        return None
    start = next(i for i, l in enumerate(lines) if l.startswith("Rarity:")) + 1
    name_block = []
    for l in lines[start:]:
        if l.startswith("--"):
            break
        name_block.append(l)
    base = None
    for l in reversed(name_block):
        m = kind_re.search(l)
        if m:
            base = m.group(0)
            break
    if not base:
        return None
    name = name_block[0] if rarity == "Rare" and len(name_block) > 1 else " ".join(name_block)

    mods, cur, mid = [], None, -1
    for l in lines:
        if l.startswith("{") and "Modifier" in l:
            mid += 1
            low = l.lower()
            mkind = ("Implicit" if "implicit" in low else "Prefix" if "prefix" in low
                     else "Suffix" if "suffix" in low else "Other")
            tier = re.search(r"Tier:\s*(\d+)", l)
            cur = {"kind": mkind, "flags": {w for w in FLAG_WORDS if w in low},
                   "tier": tier.group(1) if tier else None, "mid": mid}
            continue
        if l.startswith("--"):
            cur = None
            continue
        if cur and cur["kind"] in ("Prefix", "Suffix"):
            flags = set(cur["flags"])
            for t in re.findall(r"\((desecrated|fractured|crafted)\)", l, flags=re.I):
                flags.add(t.lower())
            clean = re.sub(r"\s*\((desecrated|fractured|crafted)\)", "", l, flags=re.I)
            clean = re.sub(r"\s+[—-]\s+Unscalable Value.*$", "", clean)
            v, lo, hi = read_numbers(clean)
            mod = {"text": clean, "kind": cur["kind"], "tier": cur["tier"], "mid": cur["mid"],
                   "flags": flags, "value": v, "lo": lo, "hi": hi,
                   "shown": re.sub(r"\(-?\d+(?:\.\d+)?-+\d+(?:\.\d+)?\)", "", strip_markup(clean))}
            mod["roll"] = roll_pct(mod)       # quality as the game shows it, before any sign flip
            mods.append(mod)
    uses = next((int(m.group(1)) for l in lines for m in [re.search(r"(\d+)\s+uses?\s+remaining", l, re.I)] if m), None)
    return {"class": kind, "rarity": rarity, "name": name, "base": base, "mods": mods, "uses": uses,
            "corrupted": any(l == "Corrupted" for l in lines)}


def min_for(mod):
    v = mod["value"]
    if v is None:
        return None
    if abs(v) <= 3:
        return v
    return math.floor(v * SETTINGS["range_factor"]) if v > 0 else math.ceil(v * SETTINGS["range_factor"])


def vfilter(mod):
    """Value filter for the trade search: 'at least this strong'. Negative stats: at most -N.
    Values you typed in the side panel (mod["uval"], 1.35) win: {"min": .., "max": ..}, either may be None."""
    if mod.get("novalue"):
        return None
    uv = mod.get("uval")
    if uv is not None:
        out = {k: v for k, v in uv.items() if k in ("min", "max") and v is not None}
        return out or None
    t = min_for(mod)
    if t is None:
        return None
    return {"max": t} if mod["value"] < 0 else {"min": t}


def roll_pct(mod):
    if mod["lo"] is not None and mod["hi"] is not None and mod["hi"] > mod["lo"] and mod["value"] is not None:
        return max(0.0, min(1.0, (mod["value"] - mod["lo"]) / (mod["hi"] - mod["lo"])))
    return None


# ------------------------------------------------------------------ mod impact (what is worth searching for)
IMPACTS = ("normal", "high", "ignore")          # the order the button on a mod clicks through them


IMPACT_LABEL = {"high": "▲ High", "normal": "● Normal", "ignore": "✕ Ignore"}


# Starting point only - every mod can be changed on the Mod rules tab or with the button on the mod itself.
# Matched against the mod text with numbers turned into '#', lower-case.
DEFAULT_IMPACT = [(re.compile(rx), imp) for rx, imp in (
    (r"^monsters have #% increased effectiveness$", "high"),
    (r"increased rarity of items found in map$", "high"),
    (r"monster rarity", "high"),
    (r"number of rare monsters", "high"),
    (r"increased tribute", "high"),
    (r"increased chance to be rare", "high"),
    (r"additional rare monsters", "high"),
    (r"additional crystal", "high"),
    (r"desecrated currency", "high"),
    (r"^#% (?:increased|reduced) pack size in map$", "ignore"),
    (r"experience gain in map", "ignore"),
    (r"^#% (?:increased|reduced) gold found in map$", "ignore"),
)]


RULES = load_json("mod_rules.json", {})        # your own changes: normalised mod text -> impact

# 2.6.0: waystone and relic rules have their own names ("relic:#% increased movement speed"), so a relic mod never
# picks up a jewel rule that happens to use the same words. Tablet and jewel rules keep the plain wording.
SCOPED_CATS = ("waystone", "relic")


def rule_key(cat, k):
    """The name a rule is saved under: the mod text for tablets and jewels, "<cat>:<text>" for waystones and relics."""
    return f"{cat}:{k}" if cat in SCOPED_CATS else k


def scoped(k):
    """-> the category of a "<cat>:<text>" rule name, or None."""
    head = k.split(":", 1)[0]
    return head if head in SCOPED_CATS and ":" in k else None


def _load_default_rules():
    """default_rules.json (ships with the app, 2.0): built-in High / Ignore marks, below your own rules."""
    import json
    import os
    from .config import APP_DIR, RESOURCE_DIR
    out = {}
    for path in (P("default_rules.json"), os.path.join(RESOURCE_DIR, "default_rules.json"), os.path.join(APP_DIR, "default_rules.json")):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        for cat in ("tablet", "jewel", "waystone", "relic"):
            for imp in ("high", "normal", "ignore"):
                for text in (d.get(cat) or {}).get(imp) or []:
                    out[rule_key(cat, norm(text))] = imp
        break
    return out


DEFAULT_RULES = _load_default_rules()        # normalised mod text -> impact


def default_impact(k):
    if k in DEFAULT_RULES:
        return DEFAULT_RULES[k]
    for rx, imp in DEFAULT_IMPACT:
        if rx.search(k):
            return imp
    return "normal"


LEARNED = {}                       # stat id -> {"tier": "high", "lift", "n", "from": earlier league or None}  (see Market)


HIGH_LIFT, MIN_WITH, MIN_WITHOUT = 2.0, 8, 8


def learned_info(k):
    """What the data says about a mod (normalised text) -> {"tier", "lift", "n", "from"} or None."""
    sid = TEXT2SID.get(k)
    if not sid or not LEARNED:
        return None
    for s_ in [sid] + list(DUPS.get(sid, ())):
        if s_ in LEARNED:
            return LEARNED[s_]
    return None


# ---- shared rules (Export rules / Import rules). Imported votes live in their own file so they never touch YOUR rules.
COMMUNITY = load_json("community_rules.json", {})     # normalised mod text -> {"text", "from": [sharer ids]}


COMMUNITY_ACTIVE, COMMUNITY_DISAGREE = set(), set()


SHARE_MAX_HIGH = 80                                    # a file claiming more "high" mods than this looks wrong: refused


def rebuild_community(market=None):
    """Which imported mods count: enough different sharers, and your own data does not clearly contradict them."""
    need = max(1, int(SETTINGS.get("community_min", 1) or 1))
    cand = {k for k, v in COMMUNITY.items() if len(v.get("from", [])) >= need}
    bad = set()
    try:
        if market is not None:
            every = market.stats()
            for k in cand:
                sid = TEXT2SID.get(k)
                if not sid:
                    continue
                sts = [st for (b, s_), st in every.items() if s_ == sid or s_ in DUPS.get(sid, ())]
                if sts and all(st["decided"] and st["tier"] != "high" for st in sts):
                    bad.add(k)                       # your own data has enough listings and says it is NOT valuable
    except Exception:
        pass
    COMMUNITY_DISAGREE.clear()
    COMMUNITY_DISAGREE.update(bad)
    COMMUNITY_ACTIVE.clear()
    COMMUNITY_ACTIVE.update(cand - bad)


def auto_impact(k):
    """The rule when YOU have set nothing: the built-in default, but a mod the data (or enough sharers) say is valuable becomes High."""
    if scoped(k):                                  # waystone / relic: only the shipped defaults (nothing is learned)
        return DEFAULT_RULES.get(k, "normal")
    d = default_impact(k)
    if d == "normal":
        li = learned_info(k)
        if (li and li["tier"] == "high") or k in COMMUNITY_ACTIVE:
            return "high"
    return d


def impact_key(k):
    v = RULES.get(k)
    return v if v in IMPACTS else auto_impact(k)


def impact_of(text):
    return impact_key(norm(text))


def impact_for(cat, text_or_key):
    """The rule for a mod of this category (waystone and relic rules are their own)."""
    return impact_key(rule_key(cat, norm(text_or_key)))


def migrate_scoped_rules(waystone_lines, relic_lines):
    """Once (2.6.0): rules set from Regex for waystone / relic mods were saved under the plain wording. Give them their
    own names. A wording that is also a tablet / jewel mod keeps its plain rule too (it belongs to that mod as well).
    -> how many were moved."""
    moved = 0
    for cat, lines in (("waystone", waystone_lines), ("relic", relic_lines)):
        for k in {norm(l) for l in lines}:
            if k in RULES and rule_key(cat, k) not in RULES:
                RULES[rule_key(cat, k)] = RULES[k]
                if k not in TABS and k not in JEWELS:
                    del RULES[k]
                moved += 1
    return moved


# ---- tabs.txt: every tablet mod, so the Mod rules tab can list them all. From 2.0 beta 12 it is built from RePoE's export
#      of the game files (tools/build_modlists.py, first line "# RePoE ..."): clean, one mod per line, in the game's own
#      wording. Older copies (pasted from a website) still load, with the clean-up below.
_GLUE = re.compile(r"%?\s*(?:reduced Pack Size in Map|increased Quantity of Waystones found in Map)")


def _clean_tab_line(line):
    """Old pasted lists (before 2.0 beta 12) glued a hybrid mod's extra lines onto the next one - split them apart again."""
    t = re.sub(r"\(-?\d+(?:\.\d+)?\s*[—–-]\s*-?\d+(?:\.\d+)?\)", "#", line.strip())
    t = re.sub(r"expedition elite pack size.*$", "", t, flags=re.I).strip()
    if not t or t == "#% increased Quantity of Waystones found in Map":
        return [t] if t else []
    if _GLUE.search(t):
        return [p.strip() for p in _GLUE.sub("|", t).split("|") if p.strip()]
    return [t]


TAB_KINDS = {}      # normalised mod text -> {"Prefix", "Suffix"} as listed in tabs.txt


def load_tabs():
    """tabs.txt -> {normalised mod text: [display text, {tablet types it can roll on}]}"""
    out, cur, kind = {}, None, None
    try:
        with open(P("tabs.txt"), encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    except Exception:
        return out
    clean = bool(lines) and lines[0].startswith("#")
    for raw in lines:
        line = raw.strip()
        if line.startswith("#") and not line.startswith("#%"):
            continue
        if line in ("Base Prefix", "Base Suffix"):
            kind = line.split()[1]
            continue
        if line == "CurrencyVaalCorrupted":
            kind = ""
            continue
        if not line or line.startswith("Crafting Tag"):
            continue
        m = re.fullmatch(r"([A-Z][a-z]+) Tablet", line)
        if m:
            cur = m.group(1)
            continue
        if cur is None:
            continue
        for t in ([re.sub(r"\(-?\d+(?:\.\d+)?\s*[—–-]\s*-?\d+(?:\.\d+)?\)", "#", line)] if clean else _clean_tab_line(line)):
            out.setdefault(norm(t), [t, set()])[1].add(cur)
            if kind:
                TAB_KINDS.setdefault(norm(t), set()).add(kind)
    return out


TABS = load_tabs()


# ---- jewels.txt: every jewel mod, so the Jewel mod rules page can list them all (RePoE from 2.0 beta 12, as tabs.txt)
JEWEL_NAMES = ["Ruby", "Emerald", "Sapphire", "Diamond", "Time-Lost Ruby", "Time-Lost Emerald", "Time-Lost Sapphire", "Time-Lost Diamond"]


_JTAGS = ["Energy Shield", "Elemental", "Resistance", "Critical", "Physical", "Lightning", "Damage", "Ailment", "Attack", "Minion",
          "Speed", "Caster", "Chaos", "Armour", "Evasion", "Charm", "Curse", "Life", "Mana", "Cold", "Fire", "Aura", "Gem", "Block",
          "Projectile", "Defences", "Presence", "Flask", "Duration", "Attribute"]


_JTAG_ALT = "|".join(sorted(map(re.escape, _JTAGS), key=len, reverse=True))


_JTAG_RUN = re.compile(r"(?:%s)+" % _JTAG_ALT)


_JTAG_ES = re.compile(r"(.*Energy Shield.*?) Energy Shield(?:%s)*" % _JTAG_ALT)


_JBAD_END = {"increased", "reduced", "to", "of", "the", "with", "and", "a", "an", "by", "while", "per", "for"}


_JRANGE = re.compile(r"\(-?\d+(?:\.\d+)?\s*[—–-]\s*-?\d+(?:\.\d+)?\)")


_JSPLIT = re.compile(r"(?<=[a-z])(?=#|\+?\(\d|\+#)|(?<=.)(?=(?:Notable|Small) Passive Skills in Radius)")


def _jewel_strip_tags(t):
    """Old pasted lists (before 2.0 beta 12) glued the mod's tags (DamageElementalFire...) onto the end of its line."""
    t = t.strip()
    m = _JTAG_ES.fullmatch(t)
    if m:
        return m.group(1)
    w = t.rsplit(" ", 1)
    if len(w) == 2 and _JTAG_RUN.fullmatch(w[1]) and w[0].strip().rsplit(" ", 1)[-1].lower() not in _JBAD_END:
        return w[0].strip()
    return t


def clean_jewel_line(line):
    out = []
    for part in _JSPLIT.split(line.strip()):
        t = _JRANGE.sub("#", _jewel_strip_tags(part)).strip()
        if t and "local jewel effect" not in t and t not in ("Notable Passive Skills in Radius", "Small Passive Skills in Radius"):
            out.append(t)
    return out


JEWEL_KINDS = {}      # normalised mod text -> {"Prefix", "Suffix"}


def load_jewels():
    """jewels.txt -> {normalised mod text: [display text, {jewel types it can roll on}]}.  Desecrated pools are skipped
    (those mods are always searched as 'Any')."""
    out, cur, kind, skip = {}, None, None, False
    try:
        with open(P("jewels.txt"), encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    except Exception:
        return out
    clean = bool(lines) and lines[0].startswith("#")
    for raw in lines:
        line = raw.strip()
        if line.startswith("#") and not line.startswith("#%"):
            continue
        if not line or line.startswith("Crafting Tag") or re.fullmatch(r"\d*Total", line):
            continue
        if line in JEWEL_NAMES:
            cur, kind, skip = line, None, False
            continue
        if cur is None:
            continue
        if line in ("Base Prefix", "Base Suffix"):
            kind, skip = line.split()[1], False
            continue
        m = re.search(r"Emotions (Prefix|Suffix)$", line)
        if m:
            kind, skip = m.group(1), False
            continue
        if re.search(r"Desecrated Modifiers (Prefix|Suffix)$", line):
            skip = True
            continue
        if line in ("CurrencyVaalCorrupted", "Orb of Sacrifice"):
            kind, skip = "", False
            continue
        if skip:
            continue
        for t in ([_JRANGE.sub("#", line)] if clean else clean_jewel_line(line)):
            out.setdefault(norm(t), [t, set()])[1].add(cur)
            if kind:
                JEWEL_KINDS.setdefault(norm(t), set()).add(kind)
    return out


JEWELS = load_jewels()


def _canon(k):
    """One spelling for wordings that differ only in 'an additional' vs '# additional' and singular vs plural."""
    k = re.sub(r"\ban additional\b", "# additional", k)
    return hash_singular(k) or k


def migrate_rule_keys(d, save=None):
    """2.0 beta 12: the tablet / jewel lists now use the game's own wording (RePoE). Rules saved with the old website
    wording ('map contains # additional summoning circles') are moved to the new one ('... an additional summoning
    circle'), and cut-off old wordings ('#% increased armour break') to the one full wording they start."""
    known = set(TABS) | set(JEWELS)
    if not known:
        return 0
    canon = {}
    for k in known:
        canon.setdefault(_canon(k), k)
    moved = 0
    for k in list(d):
        if k in known:
            continue
        new = canon.get(_canon(k))
        if not new:
            longer = [n for n in known if n.startswith(k + " ")]
            new = longer[0] if len(longer) == 1 else None
        if new and new not in d:
            d[new] = d.pop(k)
            moved += 1
    if moved and save:
        save()
    return moved


def current_key(k):
    """An old-wording mod key -> today's (or k itself)."""
    d = {k: 1}
    migrate_rule_keys(d)
    return next(iter(d))


MIGRATED_RULES = migrate_rule_keys(RULES, lambda: save_json("mod_rules.json", RULES))
migrate_rule_keys(DEFAULT_RULES)


def mod_cat(k, base=None):
    """'tablet' or 'jewel' for a normalised mod text (base = the item's base type, used when the lists don't know the mod)."""
    if k in JEWELS:
        return "jewel"
    if k in TABS:
        return "tablet"
    if base:
        return "jewel" if JEWEL_BASE.search(base) else "tablet"
    return "tablet"


DUPS = {}       # stat id -> every stat id with the same wording (trade site lists some mods twice)


# ---- what the trade site calls each stat, so a listing's mod lines can be compared with what we searched for
SIDTEXT = {}        # stat id -> normalised wording


TEXT2SID = {}       # normalised wording -> stat id (explicit if there is one)
