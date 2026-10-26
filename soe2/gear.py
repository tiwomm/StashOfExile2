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
from .mods import read_numbers, roll_pct, strip_markup
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
              "explicit": "Explicit"}
AFFIX_KINDS = ("Prefix", "Suffix", "Explicit")
_PAIR = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)")


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


def _pseudo_id(ref):
    for st in gamedata.load()["stats"]:
        if st["ref"] == ref and st["trade"].get("pseudo"):
            return st["trade"]["pseudo"][0]
    return None


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
        if not stat:
            m["note"] = "not found in the library or on the trade site's stat list"
        if kind not in AFFIX_KINDS:
            m["covered"] = {"Implicit": "implicit: comes with the base", "Rune": "socketed rune: can be swapped",
                            "Enchant": "enchant"}.get(kind, kind.lower())
        if unique:
            m["covered"] = m["covered"] or "uniques are searched by name (tick a mod to search on its roll too)"
        mods.append(m)
        refs_of.append(stat["ref"] if stat else None)

    totals, notes = [], []
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
    for m in mods:
        if m["covered"] and not m.get("note"):
            m["note"] = m["covered"]

    search = {"category": cinfo.get("trade"), "type": None, "name": None, "rarity": "nonunique",
              "corrupted": bool(g.get("corrupted")), "sockets_min": None}
    if unique:
        search.update(name=g["name"], type=g["base"], rarity="unique", category=None)
    elif cls in PER_BASE_CLASSES or not totals:
        search.update(type=g["base"], category=None)        # its own market (and anything without totals to compare on)
    need = EXCEPTIONAL_SOCKETS.get(cls)
    if need and g.get("sockets", 0) >= need and not g.get("corrupted"):
        search["sockets_min"] = g["sockets"]
        notes.append(f"exceptional: {g['sockets']} sockets")
    if q > 20:
        notes.append(f"exceptional: {q}% quality")
    return {"class": cinfo.get("name") or g.get("class_text") or "Gear", "gear": True, "gclass": cls,
            "rarity": g["rarity"], "name": g["name"] or g["base"], "base": g["base"], "mods": totals + mods,
            "uses": None, "corrupted": bool(g.get("corrupted")), "quality": q, "sockets": g.get("sockets", 0),
            "ilvl": g.get("ilvl"), "group_id": g.get("group"), "search": search, "notes": notes}


# ---------------------------------------------------------------- searching
def _stat_filter(m, value):
    f = {"id": m["sid"]}
    if value:
        f["value"] = value
    return f


def _ids(m, plain):
    ids = m.get("search_ids") or m.get("ids") or [m["sid"]]
    if plain:                                   # the simplest form: the plain explicit id only
        ids = [i for i in ids if not i.split(".")[0] in ("fractured", "desecrated", "crafted")][:1] or ids[:1]
    return ids


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
    and_f = []
    for m in must:
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
    if and_f or not query["stats"]:
        query["stats"].insert(0, {"type": "and", "filters": and_f})
    if optional:
        opt = [_stat_filter({"sid": i}, values.get(id(m))) for m in optional for i in _ids(m, plain)]
        query["stats"].append({"type": "count", "value": {"min": count_min}, "filters": opt})
    if s.get("sockets_min") and not plain:
        eq["rune_sockets"] = {"min": s["sockets_min"]}
    if eq:
        filters["equipment_filters"] = {"filters": eq}
    if mp:
        filters["map_filters"] = {"filters": mp}
    filters["misc_filters"] = {"filters": {"corrupted": {"option": "true" if s.get("corrupted") else "false"}}}
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
    elif s.get("type"):
        how = f"by base type ({s['type']})"
    else:
        how = f"by category ({item['class']}) and its totals"
    bits = [how, "corrupted only" if s.get("corrupted") else "uncorrupted only"]
    if s.get("sockets_min"):
        bits.append(f"{s['sockets_min']}+ sockets")
    return "Searched " + ", ".join(bits)
