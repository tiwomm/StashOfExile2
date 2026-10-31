"""Waystones (2.0 beta 18). What a waystone is worth comes from the numbers at the top of it - Waystone Drop Chance,
Pack Size, Item Rarity, Monster Rarity, Monster Effectiveness - which the trade site searches under "Endgame Filters"
(map_bonus, map_packsize ...). The monster / area mods underneath don't decide its price and aren't searched.
2.0 beta 19: the numbers are worth the same (which one a buyer wants depends on the buyer), so none is preferred:
when too few listings match, all of them are lowered together instead of some being let go.

A waystone becomes a price-check item shaped like gear (see gear.py), so the Price checks list, the side panel and the
search flow all work as for gear: each endgame number is a "mod" with sid "map:<filter id>", searched with
"at least your value". Every line can be ticked, unticked or starred on the item like any other mod."""
import re

from .mods import roll_pct, strip_markup

# the property line on the copied item -> (trade-site Endgame filter, short name, searched by default?)
PROPS = {
    "waystone drop chance": ("map_bonus", "Waystone Drop Chance", "normal"),
    "pack size": ("map_packsize", "Pack Size", "normal"),
    "item rarity": ("map_iir", "Item Rarity", "normal"),
    "monster rarity": ("map_rare_monsters", "Monster Rarity", "normal"),
    "monster effectiveness": ("map_magic_monsters", "Monster Effectiveness", "normal"),
    "experience gain": ("map_experience", "Experience", "normal"),
    "gold found": ("map_gold", "Gold Found", "normal"),
    "revives available": ("map_revives", "Revives Available", "normal"),
}
_PROP = re.compile(r"^([A-Za-z ]+):\s*([+-]?\d+(?:\.\d+)?)%?")
_TIER = re.compile(r"Waystone \(Tier (\d+)\)")


def is_waystone_text(text):
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    return first.startswith("Item Class:") and "waystone" in first.lower()


def parse_waystone(text):
    """A copied waystone -> a price-check item, or None."""
    if not is_waystone_text(text):
        return None
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rarity = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("Rarity:")), "")
    if rarity not in ("Normal", "Magic", "Rare", "Unique"):
        return None
    start = next(i for i, l in enumerate(lines) if l.startswith("Rarity:")) + 1
    names = []
    for l in lines[start:]:
        if l.startswith("--"):
            break
        names.append(l)
    base = next((m.group(0) for l in reversed(names) for m in [_TIER.search(l)] if m), None)
    if not base:
        return None
    tier = int(_TIER.search(base).group(1))
    name = names[0] if rarity in ("Rare", "Unique") and len(names) > 1 else " ".join(names)
    mods, mid = [], 0
    seen = set()
    for l in lines:                                    # the endgame numbers: "Pack Size: +15% (augmented)"
        m = _PROP.match(l)
        if not m:
            continue
        key = m.group(1).strip().lower()
        if key not in PROPS or key in seen:
            continue
        seen.add(key)
        fid, short, default = PROPS[key]
        v = float(m.group(2))
        v = int(v) if v.is_integer() else v
        pct = "%" if "%" in l else ""
        mods.append({"text": f"{short}: #{pct}", "shown": f"{short}: {'+' if v > 0 and pct else ''}{v:g}{pct}",
                     "kind": "Endgame", "tier": None, "mid": f"map:{fid}",
                     "flags": set(), "value": v, "lo": None, "hi": None, "roll": None, "sid": f"map:{fid}",
                     "ids": [f"map:{fid}"], "group": "total", "guess": None, "key": None, "novalue": False,
                     "covered": "not searched by default (tick it to search on it)" if default == "ignore" else None,
                     "note": ("searched at your value or more (all the numbers are lowered together when too few "
                              "listings match)" if default != "ignore" else "not searched by default (tick it to search on it)"),
                     "endgame": True})
        mid += 1
    cur = None                                          # the monster / area mods: shown, never searched
    for l in lines:
        if l.startswith("{") and "Modifier" in l:
            low = l.lower()
            cur = "Prefix" if "prefix" in low else "Suffix" if "suffix" in low else "Implicit" if "implicit" in low else "Other"
            mid += 1
            continue
        if l.startswith("--"):
            cur = None
            continue
        if cur:
            clean = re.sub(r"\s*\((desecrated|fractured|crafted|implicit)\)", "", l, flags=re.I)
            mod = {"text": clean, "shown": re.sub(r"\(-?\d+(?:\.\d+)?-+\d+(?:\.\d+)?\)", "", strip_markup(clean)),
                   "kind": cur, "tier": None, "mid": mid, "flags": set(), "value": None, "lo": None, "hi": None,
                   "sid": None, "ids": [], "group": "explicit", "guess": None, "key": None, "novalue": True,
                   "covered": "the waystone's mods don't set its price: not searched",
                   "note": "the waystone's mods don't set its price: not searched"}
            mod["roll"] = roll_pct(mod)
            mods.append(mod)
    corrupted = any(l == "Corrupted" for l in lines)
    search = {"category": None, "type": base, "name": None,
              "rarity": "unique" if rarity == "Unique" else rarity.lower() if rarity in ("Magic", "Rare") else "normal",
              "corrupted": corrupted, "sockets_min": None}
    if rarity == "Unique":
        search["name"] = name
    return {"class": "Waystone", "gear": True, "waystone": True, "gclass": "waystone", "rarity": rarity, "name": name,
            "base": base, "tier": tier, "mods": mods, "uses": None, "corrupted": corrupted, "quality": 0, "sockets": 0,
            "ilvl": next((int(x.group(1)) for l in lines for x in [re.match(r"Item Level:\s*(\d+)", l)] if x), None),
            "group_id": None, "search": search, "notes": []}


def summary(item):
    s = item["search"]
    bits = [f"by base type ({s['type']})", f"{item['rarity'].lower()} only",
            "corrupted only" if s.get("corrupted") else "uncorrupted only"]
    return "Searched on its endgame numbers " + ", ".join(bits)


def plan(must, opt):
    """The searches for a waystone, in order, until one finds enough listings (at most 4). Every number counts the
    same, so they are lowered together:
         1. every searched number at your value or more
         2. all at 90% of your values
         3. all at 75%
         4. if you starred (★) some numbers: only those, at 90%
    -> [(name, must mods, optional mods, count, values)]; the numbers are plain "at least" filters, so 'optional' is
    always empty here."""
    from .mods import vfilter

    def at(m, share):
        if m.get("uval") is not None:                      # values you typed on the item win
            return vfilter(m)
        v = m["value"]
        if v is None:
            return None
        return {"min": int(v * share) if share < 1 else v} if v > 0 else {"min": v}
    allm = must + opt
    steps = [("all at your values", allm, [], len(opt), {id(m): at(m, 1) for m in allm})]
    if any(m["value"] for m in allm):
        steps.append(("all at 90% of yours", allm, [], len(opt), {id(m): at(m, 0.9) for m in allm}))
        steps.append(("all at 75% of yours", allm, [], len(opt), {id(m): at(m, 0.75) for m in allm}))
    if must and opt:
        steps.append((f"only the starred {' and '.join(m['text'].split(':')[0] for m in must)}, at 90% of yours", must,
                      [], 0, {id(m): at(m, 0.9) for m in must}))
    return steps
