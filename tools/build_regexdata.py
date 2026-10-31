"""Builds regexdata.json (the Regex page's mod lists) from RePoE's Path of Exile 2 export.

  git clone --depth 1 https://github.com/repoe-fork/poe2 repoe2      (only data/mods.json is needed)
  python tools/build_regexdata.py repoe2/data/mods.json regexdata.json [repoe2/data/base_items.json]

2.22.0: jewels (Ruby / Emerald / Sapphire / Diamond, Time-Lost too) and gear (rings, amulets, belts, armour, weapons)
as well. base_items.json gives the gear and jewel base names, which a token must not match either.

For every tablet, waystone and relic mod that can roll, it keeps the text as the game shows it (numbers as #), which
tablet types / relic sizes / waystone tiers it rolls on, its value range, and a short SEARCH TOKEN: the shortest piece
of its text that appears in no other mod of that item type and in none of the item's other lines (properties,
implicits, flavour text), so the stash search never matches the wrong thing.

RePoE is MIT licensed (code); the data itself is Grinding Gear Games' (see THIRD_PARTY_NOTICES.txt)."""
import json
import re
import sys
import time

DOMAINS = {"tablet": "tablet", "area": "waystone", "sanctum_relic": "relic"}
# 2.22.0: kinds whose mods come from several domains, kept only when they roll on one of these tags
JEWEL_TAGS = {"strjewel": "Ruby", "dexjewel": "Emerald", "intjewel": "Sapphire", "radius_jewel": "Time-Lost",
              "str_radius_jewel": "Time-Lost", "dex_radius_jewel": "Time-Lost", "int_radius_jewel": "Time-Lost"}
WEAPON_TAGS = ("weapon", "one_hand_weapon", "two_hand_weapon", "wand", "staff", "sceptre", "sword", "mace", "axe", "bow",
               "crossbow", "spear", "flail", "dagger", "claw", "talisman", "warstaff", "trap")
GEAR_TAGS = {"ring": "Ring", "amulet": "Amulet", "belt": "Belt", "gloves": "Gloves", "boots": "Boots", "helmet": "Helmet",
             "body_armour": "Body Armour", "shield": "Shield", "focus": "Focus", "quiver": "Quiver",
             **{t: "Weapon" for t in WEAPON_TAGS},
             **{t: "Armour" for t in ("armour", "str_armour", "dex_armour", "int_armour", "str_dex_armour",
                                      "str_int_armour", "dex_int_armour", "str_dex_int_armour")}}
MULTI = {"jewel": (("misc", "desecrated"), JEWEL_TAGS), "gear": (("item", "desecrated"), GEAR_TAGS)}
GEAR_CLASSES = ("Ring", "Amulet", "Belt", "Gloves", "Boots", "Helmet", "Body Armour", "Shield", "Buckler", "Focus",
                "Quiver", "One Hand Mace", "Two Hand Mace", "Warstaff", "Spear", "Bow", "Crossbow", "Talisman",
                "One Hand Sword", "Two Hand Sword", "Dagger", "One Hand Axe", "Two Hand Axe", "Flail", "Staff", "Wand",
                "Sceptre", "Claw")

# Waystone mods carry their bonus as extra lines (15% more Waystones found in Area ...); the game adds those up into the
# waystone's properties instead of showing them as mod lines, so they are not part of the searchable mod text.
HIDDEN = [re.compile(p) for p in (
    r"^# ?% more waystones found in area$", r"^# ?% more pack size$", r"^# ?% more rarity of items found in this area$",
    r"^# ?% more magic and rare monsters$", r"^rare monsters have #% more chance of monster modifiers$",
    r"^monsters have #% more effectiveness$")]

# Everything else on these items that a token must not match.
NOISE = {
    "tablet": ["item class: tablet", "rarity: normal", "rarity: magic", "rarity: rare", "rarity: unique", "item level: #",
               "# uses remaining", "can be used in a personal map device to add modifiers to a map.", "corrupted",
               "adds ritual altars to a map", "adds breaches to a map", "adds expeditions to a map",
               "adds delirium mirrors to a map", "adds abysses to a map", "adds vaal beacons to a map",
               "adds an additional boss to a map", "adds irradiated to a map",
               "precursor tablet", "irradiated tablet", "ritual tablet", "breach tablet", "expedition tablet", "delirium tablet",
               "abyss tablet", "overseer tablet", "temple tablet", "requires level #"],
    "waystone": ["item class: waystones", "rarity: normal", "rarity: magic", "rarity: rare", "rarity: unique",
                 "waystone (tier #)", "waystone tier: #", "revives available: #", "monster pack size: +#%",
                 "magic monsters: +#%", "rare monsters: +#%", "item rarity: +#%", "waystone drop chance: +#%",
                 "monster effectiveness: +#%", "monster rarity: +#%", "item level: #", "corrupted", "delirious",
                 "can be used in a map device, allowing you to enter a map. waystones can only be used once.",
                 "modifiers may be added by tablets placed in a map device", "unidentified"],
    "relic": ["item class: relics", "rarity: normal", "rarity: magic", "rarity: rare", "rarity: unique", "item level: #",
              "urn relic", "amphora relic", "vase relic", "seal relic", "coffer relic", "tapestry relic", "incense relic",
              "place this item on the altar in the relic chamber to apply its effects to your trials", "corrupted",
              "requires level #"],
    "jewel": ["item class: jewels", "rarity: normal", "rarity: magic", "rarity: rare", "rarity: unique", "item level: #",
              "place into an allocated jewel socket on the passive skill tree. right click to remove from the socket.",
              "radius: small", "radius: medium", "radius: large", "corrupted", "unidentified", "requires level #"],
    "gear": ["item class: rings", "item class: amulets", "item class: belts", "item class: gloves", "item class: boots",
             "item class: helmets", "item class: body armours", "item class: shields", "item class: foci",
             "item class: quivers", "rarity: normal", "rarity: magic", "rarity: rare", "rarity: unique", "quality: +#%",
             "armour: #", "evasion rating: #", "energy shield: #", "block chance: #%", "spirit: #",
             "physical damage: #-#", "fire damage: #-#", "cold damage: #-#", "lightning damage: #-#",
             "chaos damage: #-#", "critical hit chance: #%", "attacks per second: #", "reload time: #",
             "requires: level #", "requires level #", "item level: #", "sockets: s", "corrupted", "unidentified",
             "mirrored", "fractured item", "charm slots: #"],
}
TAG_NAMES = {
    "default": "Any", "tower_augment_generic": "Irradiated", "tower_augment_breach": "Breach", "tower_augment_expedition": "Expedition",
    "tower_augment_delirium": "Delirium", "tower_augment_ritual": "Ritual", "tower_augment_map_boss": "Overseer",
    "tower_augment_abyss": "Abyss", "tower_augment_incursion": "Temple",
    "small_sanctum_relic": "Small", "medium_sanctum_relic": "Medium", "large_sanctum_relic": "Large",
    "map_key_low": "T1-5", "map_key_medium": "T6-10", "map_key_high": "T11-15", "map_key_highest": "T16",
}
_MARKUP = re.compile(r"\[([^\]|]*\|)?([^\]]*)\]")
_RANGE = re.compile(r"\(\s*-?\d+(?:\.\d+)?\s*-\s*-?\d+(?:\.\d+)?\s*\)")
_NUM = re.compile(r"\d+(?:\.\d+)?")
TOKEN_CHARS = re.compile(r"^\^?[a-z%',\- ]+\$?$")
_TEXT_RANGE = re.compile(r"\((-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\)|(?<![\w.])(\d+(?:\.\d+)?)")


def display(text):
    """'Monsters have (10-15)% increased [MonsterEffectiveness|Effectiveness]' -> lines with every number as #."""
    t = _MARKUP.sub(r"\2", text)
    t = _RANGE.sub("#", t)
    t = _NUM.sub("#", t)
    return [re.sub(r"\s+", " ", l).strip().lower() for l in t.split("\n") if l.strip()]


def shown_range(text):
    """The first number range as the game SHOWS it: '(30-20)% reduced' -> (20, 30); '1 extra pack' -> (1, 1)."""
    m = _TEXT_RANGE.search(_MARKUP.sub(r"\2", text))
    if not m:
        return None
    if m.group(3):
        v = float(m.group(3))
        return v, v
    a, b = abs(float(m.group(1))), abs(float(m.group(2)))
    return min(a, b), max(a, b)


def singular_variant(line):
    """'... allow rerolling favours # additional times' -> '... allow rerolling favours an additional time' (how the game
    writes a count of 1). None if the line has no '# additional <plural>'."""
    m = re.search(r"# additional ([a-z ]+?)s?(\b(?: in| from| before| when| at| on| to)\b.*)?$", line)
    if not m or not re.search(r"# additional [a-z ]*s\b", line):
        return None
    words = line[m.start():].split(" ")
    for k, w in enumerate(words):
        if k > 1 and w.endswith("s") and (k + 1 == len(words) or words[k + 1] in ("in", "from", "before", "when", "at", "on", "to")):
            words[k] = w[:-2] if w.endswith(("xes", "shes", "ches")) else w[:-1]
            break
    else:
        return None
    words[0] = "an"
    return line[:m.start()] + " ".join(words)


def best_token(line, others, also=()):
    """The cheapest piece of `line` (3+ chars, no numbers) found in none of `others`. A piece may start at the line's
    start (^) or end at its end ($). A space inside costs extra: two words' edges could also meet in a rare item's
    random name ("...age Grip" contains "e g")."""
    full = "^" + line + "$"
    oth = ["^" + o + "$" for o in others]
    n = len(full)
    best = None
    for i in range(n):
        for j in range(i + 3, min(n, i + 24) + 1):
            s = full[i:j]
            if not TOKEN_CHARS.match(s) or "#" in s:
                continue
            core = s.strip("^$")
            if len(core) < 2 or core[0] == " " or core[-1] == " " or sum(c.isalpha() for c in core) < 2:
                continue
            cost = len(s) + 2 * core.count(" ") + (4 if s.startswith("^") else 0)   # ^ only when nothing else works
            if best and cost >= best[0]:
                continue
            if any(s in o for o in oth) or any(s not in "^" + v + "$" for v in also):
                continue
            best = (cost, i, s)
    return best[2] if best else None


def main(src, out, bases_path=None):
    mods = json.load(open(src, encoding="utf-8"))
    if bases_path:                                        # 2.22.0: base names are on every item: no token may match
        bases = json.load(open(bases_path, encoding="utf-8"))
        for kind, classes in (("gear", GEAR_CLASSES), ("jewel", ("Jewel",))):
            NOISE[kind] += sorted({b["name"].lower() for b in bases.values()
                                   if b.get("item_class") in classes and b.get("release_state") == "released"})
    result = {"version": 1, "generated": time.strftime("%Y-%m-%d"), "source": {"name": "RePoE (repoe-fork/poe2)",
              "url": "https://github.com/repoe-fork/poe2"}, "types": {}}
    for dom, kind in list(DOMAINS.items()) + [(None, k) for k in MULTI]:
        by_type = {}
        doms, keep = MULTI.get(kind, ((dom,), None))
        for mid, m in mods.items():
            if m.get("domain") not in doms or m.get("generation_type") not in ("prefix", "suffix") or not m.get("text"):
                continue
            tags = [w["tag"] for w in m.get("spawn_weights", []) if w["weight"] > 0]
            if keep is not None:
                tags = sorted({keep[t] for t in tags if t in keep})
            if not tags:
                continue
            lines = [l for l in display(m["text"]) if not any(h.match(l) for h in HIDDEN)]
            if not lines:
                continue
            key = m["type"] if kind not in MULTI else (m["generation_type"], tuple(lines))   # same text = one mod
            e = by_type.setdefault(key, {"id": m["type"], "side": m["generation_type"], "lines": lines, "tags": set(),
                                               "min": None, "max": None, "names": set()})
            e["tags"].update(tags)
            if m.get("name"):
                e["names"].add(m["name"])
            rng = shown_range(m["text"])
            if rng:
                lo, hi = rng
                e["min"] = lo if e["min"] is None else min(e["min"], lo)
                e["max"] = hi if e["max"] is None else max(e["max"], hi)
        entries = list(by_type.values())
        noise = NOISE[kind]
        for e in entries:
            # 2.22.0 jewels / gear: a line another mod has word for word (a hybrid's half, the same mod as a prefix and
            # a suffix) isn't "the wrong thing" - that item has the stat too - so it doesn't block a token
            same = set(e["lines"]) if kind in MULTI else set()
            others = ([l for o in entries if o is not e for l in o["lines"] if l not in same] + noise
                      + [n.lower() for o in entries if o is not e for n in o["names"]])   # magic items' names
            main_line = next((l for l in e["lines"] if "#" in l), e["lines"][0])
            var = singular_variant(main_line) if (e["min"] or 0) <= 1 else None
            tok = best_token(main_line, others, [var]) if var else None    # must match "an additional ..." too
            e["also"] = [var] if var and tok else []
            tok = tok or best_token(main_line, others)
            if tok is None:                                  # no unique piece in that line: try the others
                tok = next((t for t in (best_token(l, others) for l in e["lines"]) if t), None)
                main_line = next((l for l in e["lines"] if tok and tok.strip("^$") in l), main_line)
            e["token"], e["line"] = tok, main_line
            if tok is None and kind in MULTI:              # 2.22.0: the whole line, numbers as \d+, both ends fixed
                main_line = next((l for l in e["lines"] if "#" in l), e["lines"][0])
                e["token"] = "^" + re.sub(r"([\\^$.|?*+()\[\]{}])", r"\\\1", main_line).replace("#", r"\d+") + "$"
                e["line"], e["rx"] = main_line, True
            e["text"] = " / ".join(e["lines"])
            e["tags"] = sorted(TAG_NAMES.get(t, t) for t in e["tags"])
            e["names"] = sorted(e["names"])
        entries.sort(key=lambda e: (e["side"], e["text"]))
        seen_ids = {}                                       # 2.22.0: one RePoE type can have two texts: unique ids
        for e in entries:
            n = seen_ids.get(e["id"], 0)
            seen_ids[e["id"]] = n + 1
            if n:
                e["id"] = f"{e['id']}~{n + 1}"
        result["types"][kind] = {"mods": entries, "noise": noise}
        print(kind, len(entries), "mods,", sum(1 for e in entries if not e["token"]), "without a token")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
