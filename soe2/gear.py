"""The gear price checker (1.41, Phase 3): turns any copied piece of gear (rings, amulets, belts, armour, weapons,
quivers, foci, charms, flasks ...) into a price-check record, and builds its trade-site searches.

How a piece of gear is searched (the rules agreed in the roadmap doc):
  - Armour pieces (gloves, boots, helmets, body armours, shields, bucklers, foci): searched by item category plus the
    item's TOTAL Armour / Evasion / Energy Shield, worked out as if at 20% quality (or at its own quality if that is
    higher, i.e. exceptional). The mods that feed those totals (+# to maximum Energy Shield, % increased ES ...)
    are left out: they are already counted in the total.
  - Attack weapons: category plus physical / elemental DPS (same idea; the local damage and attack-speed mods that
    feed the DPS are left out).
  - Rings, amulets, belts, quivers, charms, flasks, relics: searched by their exact base type (each base its own
    market: Breach Ring, Mnemonic Ring ...).
  - Several resistances / attributes / life lines add up into one trade-site "pseudo" total (total elemental
    resistance ...) when two or more mods feed it, so items with the same total but a different split also count.
  - Uniques: by name (their mods are fixed; tick one to search on its roll).
  - Uncorrupted items are compared with uncorrupted listings, corrupted with corrupted. Exceptional socket counts
    (2 on gloves / boots / helmets, 3 on body armours) are required in the search.

Priorities, per item (the side panel, same as tablets): ★ = must have (never dropped), ☑ = counts (may be dropped one
or two at a time when too few listings are found), unticked = ignored. Totals start as ★.

Search ladder: 1) everything  2) all but one of the ☑ mods  3) all but two. It stops as soon as one search finds
enough listings. That is at most 3 searches per item, so the rate limit allows it."""
import json
import re
import time

from . import gamedata
from .config import BASE
from .mods import merge_dups, norm, option_for, read_numbers, search_sid, roll_pct, strip_markup
from .net import call
from .trade import apply_opts, _cached, _search_cache, listing_rules

ARMOUR_CLASSES = {"body_armour", "helmet", "gloves", "boots", "shield", "buckler", "focus"}
PER_BASE_CLASSES = {"ring", "amulet", "belt", "quiver", "charm", "flask", "relic"}
ATTACK_WEAPONS = {"bow", "crossbow", "quarterstaff", "spear", "flail", "dagger", "one_hand_axe", "one_hand_mace",
                  "one_hand_sword", "two_hand_axe", "two_hand_mace", "two_hand_sword", "talisman", "claw"}
EXCEPTIONAL_SOCKETS = {"gloves": 2, "boots": 2, "helmet": 2, "body_armour": 3}
NOT_GEAR = {"tablet", "waystone", "jewel"}             # priced by the tablet / jewel checker (or not at all)

DEFENCES = {        # trade-site filter -> (item property, name, the stat wordings that feed it)
    "ar": ("armour", "Armour", ("# to Armour", "#% increased Armour", "#% increased Armour and Energy Shield",
                                "#% increased Armour and Evasion", "#% increased Armour, Evasion and Energy Shield")),
    "ev": ("evasion", "Evasion Rating", ("# to Evasion Rating", "#% increased Evasion Rating", "#% increased Armour and Evasion",
                                         "#% increased Evasion and Energy Shield",
                                         "#% increased Armour, Evasion and Energy Shield")),
    "es": ("energy_shield", "Energy Shield", ("# to maximum Energy Shield", "#% increased Energy Shield",
                                              "#% increased Armour and Energy Shield", "#% increased Evasion and Energy Shield",
                                              "#% increased Armour, Evasion and Energy Shield")),
}
WEAPON_FEEDERS = ("Adds # to # Physical Damage", "#% increased Physical Damage", "Adds # to # Fire Damage",
                  "Adds # to # Cold Damage", "Adds # to # Lightning Damage", "#% increased Attack Speed")
KIND_NAMES = {"prefix": "Prefix", "suffix": "Suffix", "implicit": "Implicit", "rune": "Rune", "enchant": "Enchant",
              "explicit": "Explicit", "unique": "Explicit"}   # 2.74.1: "{ Unique Modifier }" - a unique's explicit mods
AFFIX_KINDS = ("Prefix", "Suffix", "Explicit")
SKILL = re.compile(r"^Grants Skill:\s*(?:Level\s+\d+\s+)?(.+?)\s*$", re.I)


_LOOSE = {"n": -1, "map": {}}


def _loosen(k):
    return re.sub(r"\s+", " ", re.sub(r"\+|\bto\b|\bincreased\b", " ", k)).strip()


def _loose_id(k):
    """A trade id whose wording matches once "+", "to" and "increased" are left out - only when exactly one does."""
    from .trade import TEXT2SID
    if _LOOSE["n"] != len(TEXT2SID):
        m = {}
        for key, sid in TEXT2SID.items():
            m.setdefault(_loosen(key), set()).add(sid)
        _LOOSE.update(n=len(TEXT2SID), map=m)
    hits = _LOOSE["map"].get(_loosen(k)) or set()
    return next(iter(hits)) if len(hits) == 1 else None


def live_ids(text):
    """2.79.0: a mod the game data doesn't know -> its id on the trade site's own stat list (the daily download),
    trying the wording as it is, then a granted skill without its level. -> [id] or []."""
    from .trade import TEXT2SID
    from .mods import norm
    if not TEXT2SID:
        return []
    tries = [text]
    sk = SKILL.match(strip_markup(text))
    names = []
    if sk:
        n = sk.group(1)
        names = [n] + ([n[7:]] if n.lower().startswith("summon ") else [])     # 2.79.1: trade says "Rhoa Mount"
        for n in names:
            tries += [f"Grants Skill: Level # {n}", f"Grants Skill: {n}"]
    for t in tries:
        k = norm(t)
        if k in TEXT2SID:
            return [TEXT2SID[k]]
    hit = _loose_id(norm(text))                       # 2.103.2 (feedback: "Monsters have +21% Critical Damage Bonus"
    if hit:                                          # wasn't found): the wording without "+" / "to" / "increased"
        return [hit]
    for n in names:                                  # 2.79.1: any granted-skill wording ending in the skill's name
        tail = norm(n)
        for k, v in TEXT2SID.items():
            if k.startswith("grants skill") and (k.endswith(" " + tail) or k.endswith(":" + tail)):
                return [v]
    return []


def relink(item):
    """2.79.0: mods left without a trade id when the item was read (the trade list wasn't downloaded yet) -> try
    again. -> how many were found."""
    n = 0
    for m in item.get("mods") or []:
        if m.get("sid") or m.get("kind") == "Total":
            continue
        ids = live_ids(m["text"])
        if ids:
            m.update(sid=ids[0], ids=ids, note=None if not m.get("covered") else m.get("note"))
            opt = option_for(ids[0], m["text"])
            if opt is not None:
                m.update(option=opt, novalue=True)
                if item.get("rarity") == "Unique" and m.get("covered", "").startswith("uniques are searched"):
                    m.update(covered=None, auto="high", note="which one it has decides the price - searched")
            n += 1
    return n
_PAIR = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)")
# 2.72.0: mods that buyers hardly pay for on a rare - searching on them only hides the comparable listings. Left out
# by default (✕ Ignore; tick one to search on it anyway). Our own list, from how the trade site's rare listings price.
FILLER = {"#% increased Light Radius", "# to # Physical Thorns damage", "# to # Fire Thorns damage",
          "# to # Cold Thorns damage", "#% increased Thorns damage", "# to Stun Threshold", "#% increased Stun Threshold",
          "#% increased Stun Recovery", "#% increased Stun Duration", "#% increased Attribute Requirements",
          "#% increased Knockback Distance", "Recover #% of maximum Life on Kill", "Recover #% of maximum Mana on Kill"}
LOW_TIER = 6                 # 2.72.0: an affix of tier 6 or lower (T6, T7 ...) rarely adds to a rare's price
GOOD_ROLL = 0.75             # 2.72.0: a unique's mod rolled in the top quarter of its range is searched on
CRAFT_ILVL = 75              # 2.72.0: a normal / magic base this high is a crafting base: searched at its item level
MAX_ILVL = 82                # (no mod needs more than this - a higher item level is worth the same)


def is_gear(g):
    """A gamedata.read_item() result that the gear checker handles."""
    if not (g and g.get("class") and g.get("base")):
        return False
    if g["class"] in NOT_GEAR:                 # unique tablets / jewels / waystones: priced by name here (1.42)
        return g.get("rarity") == "Unique"
    return g.get("rarity") in ("Normal", "Magic", "Rare", "Unique")


def _q20(value, quality):
    """A defence / damage value as it would be at 20% quality (or at the item's own quality if that is higher)."""
    q = quality or 0
    return value / (1 + q / 100) * (1 + max(20, q) / 100)


def _weapon_props(text):
    """-> (physical average, elemental average, attacks per second) from a copied weapon."""
    phys = ele = aps = 0.0
    for l in (text or "").replace("\r", "").split("\n"):
        l = l.strip()
        if l.startswith("Physical Damage:"):
            phys = sum((float(a) + float(b)) / 2 for a, b in _PAIR.findall(l.split(":", 1)[1]))
        elif l.startswith(("Elemental Damage:", "Fire Damage:", "Cold Damage:", "Lightning Damage:")):
            ele += sum((float(a) + float(b)) / 2 for a, b in _PAIR.findall(l.split(":", 1)[1]))
        elif l.startswith("Attacks per Second:"):
            m = re.search(r"(\d+(?:\.\d+)?)", l.split(":", 1)[1])
            aps = float(m.group(1)) if m else 0.0
    return phys, ele, aps


def _total(text, shown, value, sid, why):
    return {"text": text, "shown": shown, "kind": "Total", "tier": None, "mid": f"total:{sid}", "flags": set(),
            "value": float(round(value)), "lo": None, "hi": None, "roll": None, "sid": sid, "ids": [sid],
            "group": "total", "guess": None, "note": why, "key": None, "novalue": False, "covered": None}


SOURCES_ONLY = ("fractured", "desecrated")
HYBRID_RES = re.compile(r"^#% to (Fire|Cold|Lightning|Chaos) and (Fire|Cold|Lightning|Chaos) Resistances$")


def only_source(rec, m):
    """2.93.0: "fractured" / "desecrated" when this mod is ticked to be searched only as that (the small box beside
    it on the card), else None."""
    src = next((s for s in SOURCES_ONLY if s in (m.get("flags") or ())), None)
    if src and (rec.get("only") or {}).get(norm(m.get("text") or "")):
        return src
    return None


def hybrid_split(mods, totals):
    """2.93.0 (feedback): a hybrid resistance ("+17% to Lightning and Chaos Resistances") -> a pseudo total per
    resistance it has (total Lightning, total Chaos), each adding up every mod that feeds it. Chaos isn't in the
    total Elemental Resistance, so its total is searched (☑); an elemental one is offered unticked (the elemental
    total already counts it). -> the new totals."""
    rules = {r["pseudo"]: r for r in gamedata.load().get("pseudo_rules", [])}
    have = {t["sid"] for t in totals}
    out = []
    for h in mods:
        mt = HYBRID_RES.match(h.get("ref") or "")
        if not mt or h["value"] is None or h["kind"] not in AFFIX_KINDS + ("Implicit",):
            continue
        for el in mt.groups():
            rule = rules.get(f"#% total to {el} Resistance")
            pid = _pseudo_id(rule["pseudo"]) if rule else None
            if not pid or pid in have:
                continue
            weights = {s["ref"]: s.get("x", 1) for s in rule["stats"]}
            feeding = [m for m in mods if m.get("ref") in weights and m["value"] is not None
                       and m["kind"] in AFFIX_KINDS + ("Implicit",)]
            tot = sum(m["value"] * weights[m["ref"]] for m in feeding)
            t = _total(rule["pseudo"], rule["pseudo"].replace("#", f"{tot:g}", 1), tot, pid,
                       f"{el} part of a hybrid resistance" + (f" + {len(feeding) - 1} more" if len(feeding) > 1 else ""))
            t["group"] = "pseudo"
            if el != "Chaos":
                t["auto"] = "ignore"
                t["note"] += " - counted in the total Elemental Resistance (tick it to search on it too)"
            else:
                t["auto"] = "normal"
            out.append(t)
            have.add(pid)
    return out


def _pseudo_id(ref):
    for st in gamedata.load()["stats"]:
        if st["ref"] == ref and st["trade"].get("pseudo"):
            return st["trade"]["pseudo"][0]
    return None


def _merge_same_stat(mods, refs_of):
    """2.98.5 (feedback: a rare with a Rarity prefix AND a Rarity suffix found listings without them): the game and
    the trade site add two mods with the same stat into one line ("34% increased Rarity of Items found"), so two
    filters on one stat don't match the way the card shows. Two affixes with one stat -> one mod, the values added.
    Fractured / desecrated / crafted ones stay apart (Fractured only searches the mod on its own)."""
    first = {}
    i = 0
    while i < len(mods):
        m = mods[i]
        k = m.get("sid")
        if (not k or m["kind"] not in AFFIX_KINDS or m["value"] is None or m["flags"] or m.get("option") is not None
                or m.get("skill")):
            i += 1
            continue
        j = first.get(k)
        if j is None or mods[j]["mid"] == m["mid"]:
            first.setdefault(k, i)
            i += 1
            continue
        a = mods[j]
        parts = a.get("parts") or [a["value"]]
        parts.append(m["value"])
        a["value"] = sum(parts)
        if a["lo"] is not None and m["lo"] is not None and a["hi"] is not None and m["hi"] is not None:
            a["lo"], a["hi"] = a["lo"] + m["lo"], a["hi"] + m["hi"]
        else:
            a["lo"] = a["hi"] = None
        a["parts"] = parts
        a["roll"] = roll_pct(a)
        nums = " + ".join(f"{p:g}" for p in parts)
        a["shown"] = re.sub(r"-?\d+(?:\.\d+)?", f"{a['value']:g}", a["shown"], count=1) + f"  ({nums})"
        tiers = [t for t in (a["tier"], m["tier"]) if t]
        a["tier"] = min(tiers, key=lambda t: int(t) if t.isdigit() else 99) if tiers else None
        if a.get("auto") == "ignore" and m.get("auto") != "ignore":
            a.pop("auto", None)
            a["note"] = None
        a["note"] = (a["note"] + "; " if a["note"] else "") + f"two mods add up ({nums}): searched as one line, like the trade site"
        del mods[i]
        del refs_of[i]


def parse_gear(text):
    """A copied piece of gear -> a price-check item (same shape as a tablet / jewel item, plus "gear": True and the
    search plan), or None if it isn't gear."""
    g = gamedata.read_item(text)
    if not is_gear(g):
        return None
    cls = g["class"]
    cinfo = gamedata.classes().get(cls, {})
    unique = g["rarity"] == "Unique"
    mods, refs_of = [], []
    prev_key, mid = None, -1
    for gm in g["mods"]:
        kind = KIND_NAMES.get(gm["kind"], gm["kind"].title())
        key = (gm["kind"], gm.get("affix"), gm.get("tier"))
        if gm.get("affix") is None or key != prev_key:      # lines of one hybrid mod share one header
            mid += 1
        prev_key = key
        clean = re.sub(r"\s*\((implicit|rune|enchant|crafted|desecrated|fractured)\)\s*$", "", gm["text"], flags=re.I)
        clean = re.sub(r"\s+[—-]\s+Unscalable Value.*$", "", clean)
        clean = gamedata._WRANGE.sub("", clean)            # 2.74.1: "Legacy of Gold (Amethyst-Topaz)"
        v, lo, hi = read_numbers(strip_markup(clean))
        stat, neg = gamedata.stat_for(gm["text"])
        if neg and v is not None:
            v = -v
            if lo is not None and hi is not None:
                lo, hi = -hi, -lo
        ids = []
        if stat:
            tr = stat["trade"]
            grp = "explicit" if kind in AFFIX_KINDS else gm["kind"]
            ids = list(tr.get(grp) or tr.get("explicit") or next(iter(tr.values()), []))
            if kind == "Enchant" and not tr.get("enchant"):  # 2.98.2: a corruption enchantment - the trade site's
                ids = ["enchant." + i.split(".", 1)[1] for i in ids if "." in i] or ids  # own id (same number)
            if gm.get("source") and kind in AFFIX_KINDS:     # a fractured / desecrated / crafted mod: listed either way
                ids += [i for i in tr.get(gm["source"], []) if i not in ids]
        m = {"text": clean, "shown": re.sub(r"\(-?\d+(?:\.\d+)?-+\d+(?:\.\d+)?\)", "", strip_markup(clean)),
             "kind": kind, "tier": str(gm["tier"]) if gm.get("tier") else None, "mid": mid,
             "flags": {gm["source"]} if gm.get("source") else set(), "value": v, "lo": lo, "hi": hi,
             "sid": ids[0] if ids else None, "ids": ids, "group": "explicit" if kind in AFFIX_KINDS else gm["kind"],
             "guess": None, "note": None, "key": None, "novalue": v is None, "covered": None,
             "ref": stat["ref"] if stat else None}
        m["roll"] = roll_pct(m)
        if v is not None and neg and m["roll"] is not None:
            m["roll"] = 1 - m["roll"]
        if not ids:                                          # 2.79.0: the game data doesn't know it - the trade site's
            ids = live_ids(clean)                             # own list (downloaded daily) might (Mageblood, new skills)
            if ids:
                m.update(sid=ids[0], ids=ids)
        skill = SKILL.match(strip_markup(clean))
        if skill:                                            # 2.79.0: "Grants Skill: Level 20 Summon Rhoa Mount" - which
            m.update(auto="high", novalue=True, skill=skill.group(1).strip())   # skill decides the price; no level filter
            if not m["sid"]:
                m["note"] = "its skill isn't on the trade site's list yet"
        opt = option_for(ids[0], clean) if ids else None     # 2.74.1: a stat with a choice (Legacy of Gold ...)
        if opt is not None:
            m.update(option=opt, novalue=True)
        if not stat and not m["sid"]:
            m["note"] = m["note"] or "not found in the library or on the trade site's stat list"
        if kind == "Enchant" and g.get("corrupted") and m["sid"]:    # 2.98.2 (feedback): a corrupted item's
            m["auto"] = "high"                                       # enchantment is what the corruption gave it -
            m["note"] = "corruption enchantment - searched"          # listings must have it too
        elif kind not in AFFIX_KINDS:
            m["covered"] = {"Implicit": "implicit: comes with the base", "Rune": "socketed rune: can be swapped",
                            "Enchant": "enchant"}.get(kind, kind.lower())
        if kind == "Enchant" and m.get("auto") == "high":
            pass                                             # (2.98.2: the corruption enchantment, searched above)
        elif unique and not m["covered"] and m.get("option") is not None:    # 2.74.1: which one it has sets the price
            m["auto"] = "high"
            m["note"] = "which one it has decides the price - searched"
        elif unique and not m["covered"]:                    # 2.72.0: uniques by roll
            r = m["roll"]
            if r is not None and r >= GOOD_ROLL and m["sid"] and kind in AFFIX_KINDS:
                m["note"] = f"well rolled ({r:.0%} of its range): searched at least this high"
            else:
                m["covered"] = ("uniques are searched by name" + (f" - this roll is {r:.0%} of its range" if r is not None
                                                                   else "") + " (tick it to search on its roll too)")
        elif kind in AFFIX_KINDS and stat and g["rarity"] in ("Magic", "Rare"):     # 2.72.0: what buyers pay for
            if stat["ref"] in FILLER:
                m["auto"] = "ignore"
                m["note"] = "rarely adds to a rare's price - not searched (tick it to search on it)"
            elif str(gm.get("tier") or "").isdigit() and int(gm["tier"]) >= LOW_TIER:
                m["auto"] = "ignore"
                m["note"] = f"low tier (T{gm['tier']}) - rarely adds to the price, not searched (tick it to search on it)"
        mods.append(m)
        refs_of.append(stat["ref"] if stat else None)
    _merge_same_stat(mods, refs_of)

    # 2.98.4 (feedback: "I am unable to accurately price check a mageblood"): what a Mageblood's price hangs on -
    # its Legacies (which ones, how many of each: searched as Min N), its charm slots, and - with a duplicate - the
    # "increased effect per duplicate" roll (at least its value)
    notes = []
    picks = [m for m in mods if m.get("option") is not None]
    if unique and picks:
        from collections import Counter
        n = Counter((m["sid"], m["option"]) for m in picks)
        dup = any(v > 1 for v in n.values())
        for m in mods:
            low = m["text"].lower()
            if "per duplicate" in low and m["sid"]:
                if dup:
                    m.update(auto="high", covered=None, novalue=False,
                             note="your Legacies have a duplicate: this roll counts - searched at least this high")
                else:
                    m["note"] = "no duplicate Legacy: this roll doesn't count (tick it to search on it anyway)"
            elif m["kind"] == "Implicit" and "charm slot" in low and m["sid"] and m.get("value"):
                m.update(auto="high", covered=None,
                         note=f"{int(m['value'])} charm slots - searched at least that")
        name = {(x["sid"], x["option"]): x["shown"] for x in picks}
        legs = ", ".join(name[k] + (f" ×{v}" if v > 1 else "") for k, v in n.items())
        if legs:
            notes.append("Legacies: " + legs)

    totals = []
    q = g.get("quality") or 0
    if cls in ARMOUR_CLASSES and not unique:
        for key, (prop, name, feeders) in DEFENCES.items():
            val = g["props"].get(prop)
            if not val:
                continue
            at = _q20(val, q)
            qtxt = f"at {max(20, q)}% quality" + ("" if q == max(20, q) else f" (yours is {q}%)")
            totals.append(_total(f"Total {name}", f"{name}: {round(at)}  ({qtxt})", at, f"equip:{key}",
                                 f"total {name} {qtxt}: the mods that add {name} are counted in it"))
            for m in mods:
                if m.get("ref") in feeders and m["kind"] in AFFIX_KINDS:
                    m["covered"] = f"counted in the total {name}"
    if cls in ATTACK_WEAPONS and not unique:
        phys, ele, aps = _weapon_props(text)
        if aps:
            if phys:
                p = _q20(phys, q) * aps
                totals.append(_total("Physical DPS", f"Physical DPS: {p:.0f}  (at {max(20, q)}% quality)", p, "equip:pdps",
                                     "physical damage per second at 20% quality: the local damage and attack speed mods are counted in it"))
            if ele:
                e = ele * aps
                totals.append(_total("Elemental DPS", f"Elemental DPS: {e:.0f}", e, "equip:edps",
                                     "elemental damage per second: the local added elemental damage mods are counted in it"))
            if phys or ele:
                for m in mods:
                    if m.get("ref") in WEAPON_FEEDERS and m["kind"] in AFFIX_KINDS:
                        m["covered"] = "counted in the weapon's DPS"
    if not unique:                                         # pseudo totals: two or more mods feeding one total
        for rule in gamedata.load().get("pseudo_rules", []):
            if not rule.get("on"):
                continue
            weights = {s["ref"]: s.get("x", 1) for s in rule["stats"]}
            feeding = [m for m in mods if m.get("ref") in weights and m["value"] is not None and not m["covered"]
                       and m["kind"] in AFFIX_KINDS + ("Implicit",)]
            pid = _pseudo_id(rule["pseudo"])
            if len(feeding) < 2 or not pid:
                continue
            tot = sum(m["value"] * weights[m["ref"]] for m in feeding)
            name = re.sub(r"\s+", " ", re.sub(r"\+?#%?", "", rule["pseudo"])).strip()      # "total Elemental Resistance"
            t = _total(rule["pseudo"].replace("+#", "#"), rule["pseudo"].replace("#", f"{tot:g}", 1), tot, pid,
                       f"{len(feeding)} mods add up to this {name}")
            t["group"] = "pseudo"
            totals.append(t)
            for m in feeding:
                m["covered"] = f"counted in the {name}"
        totals += hybrid_split(mods, totals)
    for m in mods:
        if m["covered"] and not m.get("note"):
            m["note"] = m["covered"]

    search = {"category": cinfo.get("trade"), "type": None, "name": None, "rarity": "nonunique",
              "corrupted": bool(g.get("corrupted")), "sockets_min": None}
    if unique:
        search.update(name=g["name"], type=g["base"], rarity="unique", category=None)
        rolls = [m["roll"] for m in mods if m["roll"] is not None and m["kind"] in AFFIX_KINDS]
        if rolls:                                           # 2.72.0: how well its rolls came out, on the whole
            avg = sum(rolls) / len(rolls)
            notes.append(f"rolls: {avg:.0%} of their ranges" + (" (well rolled)" if avg >= GOOD_ROLL else
                                                                 " (low: most listings roll better)" if avg < 0.3 else ""))
    elif cls in PER_BASE_CLASSES or not totals:
        search.update(type=g["base"], category=None)        # its own market (and anything without totals to compare on)
    if g["rarity"] in ("Normal", "Magic"):              # 2.79.0 (feedback): white and blue bases - the exact item
        white = g["rarity"] == "Normal"                 # level, Normal / Magic, not corrupted, fractured or
        search.update(type=g["base"], category=None, rarity="normal" if white else "magic", corrupted=False,
                      fractured=False, sanctified=False, ilvl_min=g.get("ilvl"), ilvl_max=g.get("ilvl"),
                      quality_min=q or None, sockets_min=g.get("sockets") or None)   # sanctified; its quality and
        notes.append(("white" if white else "magic") + " base: " + ", ".join(    # sockets (at least) when it has them
            x for x in (f"item level {g['ilvl']}" if g.get("ilvl") else "", f"{q}%+ quality" if q else "",
                        f"{g['sockets']}+ sockets" if g.get("sockets") else "",
                        "not corrupted, fractured or sanctified") if x))
    need = EXCEPTIONAL_SOCKETS.get(cls)
    if need and g.get("sockets", 0) >= need and not g.get("corrupted"):
        search["sockets_min"] = g["sockets"]
        notes.append(f"exceptional: {g['sockets']} sockets")
    elif g.get("corrupted") and g.get("sockets"):           # 2.98.2 (feedback): a corrupted item can't get more
        search["sockets_min"] = g["sockets"]                 # sockets - the ones it has are part of what it is
        notes.append(f"corrupted with {g['sockets']} socket{'s' if g['sockets'] != 1 else ''}: searched at least that")
    if g.get("corrupted"):
        ench = [m for m in mods if m["kind"] == "Enchant" and m.get("auto") == "high"]
        notes.append("corrupted" + (": " + ", ".join(m["shown"] for m in ench) if ench else "") + " - only corrupted "
                     "listings are compared")
    if q > 20:
        notes.append(f"exceptional: {q}% quality")
    return {"class": cinfo.get("name") or g.get("class_text") or "Gear", "gear": True, "gclass": cls,
            "rarity": g["rarity"], "name": g["name"] or g["base"], "base": g["base"], "mods": totals + mods,
            "uses": None, "corrupted": bool(g.get("corrupted")), "quality": q, "sockets": g.get("sockets", 0),
            "ilvl": g.get("ilvl"), "group_id": g.get("group"), "search": search, "notes": notes}


def base_ladder(item):
    """2.99.0: a white / blue base's searches, exact first, each a little wider: [(label, item with that search)].
    [] for anything else. Exact item level + quality -> item level or higher -> 21%+ quality (still exceptional) ->
    any quality."""
    s = item.get("search") or {}
    if item.get("rarity") not in ("Normal", "Magic") or not s.get("ilvl_max"):
        return []
    lv, q = s.get("ilvl_min"), s.get("quality_min")

    def var(**kw):
        return dict(item, search=dict(s, **kw))
    out = [(f"item level {lv}" + (f", {q}%+ quality" if q else ""), item),
           (f"item level {lv}+" + (f", {q}%+ quality" if q else ""), var(ilvl_max=None))]
    if q and q > 21:
        out.append((f"item level {lv}+, 21%+ quality (exceptional)", var(ilvl_max=None, quality_min=21)))
    if q:
        out.append((f"item level {lv}+, any quality", var(ilvl_max=None, quality_min=None)))
    return out


# ---------------------------------------------------------------- searching
def _stat_filter(m, value):
    f = {"id": search_sid(m)}
    if value:
        f["value"] = value
    return f


def _ids(m, plain):
    ids = m.get("search_ids") or m.get("ids") or [m["sid"]]
    if plain:                                   # the simplest form: the plain explicit id only
        ids = [i for i in ids if not i.split(".")[0] in ("fractured", "desecrated", "crafted")][:1] or ids[:1]
    return [search_sid(m, i) for i in ids]


def build_query(item, must, optional, count_min, values, plain=False):
    """The trade-site query for one step of the ladder.
    must / optional: lists of mods; values: mod -> value filter ({"min": ..} or None).
    plain=True (after the trade site refused a search): one id per mod and no socket filter."""
    s = item["search"]
    status, api_age, _hours = listing_rules()
    query = {"status": {"option": status}, "stats": []}
    if s.get("type"):
        query["type"] = s["type"]
    if s.get("name"):
        query["name"] = s["name"]
    filters = {}
    tf = {}
    if s.get("category"):
        tf["category"] = {"option": s["category"]}
    if s.get("rarity"):
        tf["rarity"] = {"option": s["rarity"]}
    if tf:
        filters["type_filters"] = {"filters": tf}
    eq, mp = {}, {}
    if item.get("waystone") and item.get("tier") is not None:
        mp["map_tier"] = {"min": item["tier"], "max": item["tier"]}     # 2.10.0: same tier only
    if optional and count_min >= len(optional):         # 2.105.0 (feedback: an amulet's exact search found listings
        must, optional = list(must) + list(optional), []   # without its +186 Mana): every mod must match, like ★ mods -
    and_f = []                                          # a count over each mod's several ids (fractured, desecrated
    for m in must:                                      # ...) let one mod count two or three times
        v = values.get(id(m))
        if m["sid"].startswith("equip:"):
            if v:
                eq[m["sid"][6:]] = v
            continue
        if m["sid"].startswith("map:"):                      # 2.0 beta 18: waystones' Endgame Filters
            if v:
                mp[m["sid"][4:]] = v
            continue
        ids = _ids(m, plain)
        if len(ids) > 1:                                     # same wording under several ids: any one of them
            query["stats"].append({"type": "count", "value": {"min": 1}, "filters": [_stat_filter({"sid": i}, v) for i in ids]})
        else:
            and_f.append(_stat_filter(m, v))
    and_f = merge_dups(and_f)                                # 2.79.1: two Legacy of Quicksilver -> one, Min 2
    if and_f or not query["stats"]:
        query["stats"].insert(0, {"type": "and", "filters": and_f})
    if optional:                                      # "all but N": one id per mod, so each counts once
        opt = merge_dups([_stat_filter({"sid": _ids(m, plain)[0]}, values.get(id(m))) for m in optional])
        query["stats"].append({"type": "count", "value": {"min": count_min}, "filters": opt})
    if s.get("sockets_min") and not plain:
        eq["rune_sockets"] = {"min": s["sockets_min"]}
    if eq:
        filters["equipment_filters"] = {"filters": eq}
    if mp:
        filters["map_filters"] = {"filters": mp}
    filters["misc_filters"] = {"filters": {"corrupted": {"option": "true" if s.get("corrupted") else "false"}}}
    for k, name in (("fractured", "fractured_item"), ("sanctified", "sanctified")):     # 2.79.0: white / blue bases
        if s.get(k) is False:
            filters["misc_filters"]["filters"][name] = {"option": "false"}
    if s.get("ilvl_min"):                                     # 2.72.0: crafting bases (item level: a type filter)
        filters.setdefault("type_filters", {"filters": {}})["filters"]["ilvl"] = {
            k: v for k, v in (("min", s["ilvl_min"]), ("max", s.get("ilvl_max"))) if v}
    if s.get("quality_min"):                                  # 2.79.0: white bases
        filters.setdefault("type_filters", {"filters": {}})["filters"]["quality"] = {"min": s["quality_min"]}
    if api_age:
        filters["trade_filters"] = {"filters": {"indexed": {"option": api_age}}}
    query["filters"] = filters
    return apply_opts(query, item)                            # 2.4.1: this item's own search filters


def run_search(league, query):
    """One trade search -> (total, first 10 ids, query id). The same search within 10 minutes is free."""
    key = "gear" + league + json.dumps(query, sort_keys=True)
    hit = _cached(_search_cache, key)
    if hit is None:
        res = call("POST", f"{BASE}/search/poe2/{league}", json={"query": query, "sort": {"price": "asc"}})
        hit = (res.get("total", 0), res.get("result", [])[:10], res.get("id"))
        _search_cache[key] = (time.time(), hit)
    return hit


def ladder(n_optional):
    """[(step name, how many of the optional mods must match)] - at most 3 steps."""
    steps = [("all mods", n_optional)]
    if n_optional >= 2:
        steps.append(("all but 1 of the ☑ mods", n_optional - 1))
    if n_optional >= 4:
        steps.append(("all but 2 of the ☑ mods", n_optional - 2))
    return steps


def summary(item):
    """One line for the side panel: how this item is searched."""
    s = item["search"]
    if s.get("name"):
        how = f"by name ({s['name']})"
        picks = [m["text"] for m in item.get("mods") or [] if m.get("option") is not None]
        if picks:                                            # 2.74.1: Mageblood's Legacies ...
            how += " with " + ", ".join(picks)
    elif s.get("type"):
        how = f"by base type ({s['type']})"
    else:
        how = f"by category ({item['class']}) and its totals"
    bits = [how, "corrupted only" if s.get("corrupted") else "uncorrupted only"]
    if s.get("sockets_min"):
        bits.append(f"{s['sockets_min']}+ sockets")
    return "Searched " + ", ".join(bits)
