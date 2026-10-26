"""Build gamedata.json - StashOfExile2's library of PoE 2 base types, base groups and modifier stats.

    py tools/build_gamedata.py <Exiled-Exchange-2 checkout> [gamedata.json]

Source: Exiled Exchange 2 (https://github.com/Kvan7/Exiled-Exchange-2, MIT licence, see THIRD_PARTY_NOTICES.txt):
renderer/public/data/en/items.ndjson (base types, their category, tags and base defences) and stats.ndjson (every
modifier's wording, which way is better, and its trade-site stat ids). The pseudo-total rules below are transcribed
from its renderer/src/web/price-check/filters/pseudo/index.ts.

Run it again after each patch (with an updated checkout) and bump GAMEDATA_VERSION, so the new file replaces the old
one in everyone's data folder (soe2/config.py BUNDLED_DATA)."""
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date

GAMEDATA_VERSION = 1

# EE2 category -> (class id, the game's "Item Class:" text, trade-site category, kind of item)
CLASSES = {
    "Body Armour": ("body_armour", "Body Armours", "armour.chest", "armour"),
    "Helmet": ("helmet", "Helmets", "armour.helmet", "armour"),
    "Gloves": ("gloves", "Gloves", "armour.gloves", "armour"),
    "Boots": ("boots", "Boots", "armour.boots", "armour"),
    "Shield": ("shield", "Shields", "armour.shield", "armour"),
    "Buckler": ("buckler", "Bucklers", "armour.buckler", "armour"),
    "Focus": ("focus", "Foci", "armour.focus", "armour"),
    "Quiver": ("quiver", "Quivers", "armour.quiver", "jewellery"),
    "Ring": ("ring", "Rings", "accessory.ring", "jewellery"),
    "Amulet": ("amulet", "Amulets", "accessory.amulet", "jewellery"),
    "Belt": ("belt", "Belts", "accessory.belt", "jewellery"),
    "Jewel": ("jewel", "Jewels", "jewel", "jewel"),
    "Charm": ("charm", "Charms", "flask", "flask"),
    "Flask": ("flask", "Flasks", "flask", "flask"),
    "Bow": ("bow", "Bows", "weapon.bow", "weapon"),
    "Crossbow": ("crossbow", "Crossbows", "weapon.crossbow", "weapon"),
    "Wand": ("wand", "Wands", "weapon.wand", "weapon"),
    "Staff": ("staff", "Staves", "weapon.staff", "weapon"),
    "Warstaff": ("quarterstaff", "Quarterstaves", "weapon.warstaff", "weapon"),
    "Sceptre": ("sceptre", "Sceptres", "weapon.sceptre", "weapon"),
    "Talisman": ("talisman", "Talismans", "weapon.talisman", "weapon"),
    "Spear": ("spear", "Spears", "weapon.spear", "weapon"),
    "Flail": ("flail", "Flails", "weapon.flail", "weapon"),
    "Dagger": ("dagger", "Daggers", "weapon.dagger", "weapon"),
    "One Hand Axe": ("one_hand_axe", "One Hand Axes", "weapon.oneaxe", "weapon"),
    "One Hand Mace": ("one_hand_mace", "One Hand Maces", "weapon.onemace", "weapon"),
    "One Hand Sword": ("one_hand_sword", "One Hand Swords", "weapon.onesword", "weapon"),
    "Two Hand Axe": ("two_hand_axe", "Two Hand Axes", "weapon.twoaxe", "weapon"),
    "Two Hand Mace": ("two_hand_mace", "Two Hand Maces", "weapon.twomace", "weapon"),
    "Two Hand Sword": ("two_hand_sword", "Two Hand Swords", "weapon.twosword", "weapon"),
    "Relic": ("relic", "Relics", "sanctum.relic", "other"),
    "TowerAugment": ("tablet", "Tablets", "map.tablet", "other"),
    "Map": ("waystone", "Waystones", "map.waystone", "other"),
}
DEFENCE_NAMES = {"ar": "Armour", "ev": "Evasion", "es": "Energy Shield", "ar_ev": "Armour / Evasion",
                 "ar_es": "Armour / Energy Shield", "ev_es": "Evasion / Energy Shield",
                 "ar_ev_es": "Armour / Evasion / Energy Shield", "none": "no defences"}
# name prefixes that are versions of the same base (same mod pool): grouped together
SAME_BASE_PREFIXES = ("Runeforged ", "Runemastered ", "Refined ")
# for these classes every base family is its own group (implicits / mod pools differ per base)
PER_BASE = {"ring", "amulet", "belt", "jewel", "charm", "quiver", "flask"}

# Pseudo totals (the trade site adds these up for us). From EE2 pseudo/index.ts, the rules it uses (not the
# commented-out ones). "x" = how much one point of the source stat counts.
RES = [("#% to All Resistances", "fcl", True), ("#% to all Elemental Resistances", "fcl", False),
       ("#% to Fire Resistance", "f", False), ("#% to Cold Resistance", "c", False),
       ("#% to Lightning Resistance", "l", False), ("#% to Fire and Lightning Resistances", "fl", False),
       ("#% to Fire and Cold Resistances", "fc", False), ("#% to Cold and Lightning Resistances", "cl", False),
       ("#% to Chaos Resistance", "", True), ("#% to Fire and Chaos Resistances", "f", True),
       ("#% to Cold and Chaos Resistances", "c", True), ("#% to Lightning and Chaos Resistances", "l", True)]
ATTR = [("# to all Attributes", "sdi"), ("# to Strength", "s"), ("# to Dexterity", "d"), ("# to Intelligence", "i"),
        ("# to Strength and Intelligence", "si"), ("# to Strength and Dexterity", "sd"),
        ("# to Dexterity and Intelligence", "di")]


def pseudo_rules():
    ele = [r for r in RES if r[1]]
    rules = [
        {"pseudo": "#% total to all Elemental Resistances", "on": False, "stats": [{"ref": r} for r, _, _ in ele]},
        {"pseudo": "#% total Elemental Resistance", "on": True, "stats": [{"ref": r, "x": len(e)} for r, e, _ in ele]},
    ]
    for el, word in (("f", "Fire"), ("c", "Cold"), ("l", "Lightning")):
        rules.append({"pseudo": f"#% total to {word} Resistance", "on": False,
                      "stats": [{"ref": r} for r, e, _ in RES if el in e]})
    rules.append({"pseudo": "#% total to Chaos Resistance", "on": True, "stats": [{"ref": r} for r, _, ch in RES if ch]})
    rules.append({"pseudo": "+# total to all Attributes", "on": False, "stats": [{"ref": "# to all Attributes"}]})
    for a, word in (("s", "Strength"), ("d", "Dexterity"), ("i", "Intelligence")):
        rules.append({"pseudo": f"+# total to {word}", "on": False, "stats": [{"ref": r} for r, at in ATTR if a in at]})
    rules.append({"pseudo": "+# total maximum Life", "on": True,
                  "stats": [{"ref": "# to maximum Life", "required": True}] + [{"ref": r, "x": 2} for r, at in ATTR if "s" in at]})
    rules.append({"pseudo": "+# total maximum Mana", "on": False,
                  "stats": [{"ref": "# to maximum Mana", "required": True}] + [{"ref": r, "x": 2} for r, at in ATTR if "i" in at]})
    rules.append({"pseudo": "#% total increased maximum Energy Shield", "on": False,
                  "stats": [{"ref": "#% increased maximum Energy Shield"}]})
    rules.append({"pseudo": "+# total maximum Energy Shield", "on": False, "stats": [{"ref": "# to maximum Energy Shield"}]})
    rules.append({"pseudo": "#% increased Movement Speed", "on": True, "stats": [{"ref": "#% increased Movement Speed"}]})
    return rules


def family(name):
    for p in SAME_BASE_PREFIXES:
        if name.startswith(p):
            return name[len(p):]
    return name


def defence_of(armour):
    keys = [k for k in ("ar", "ev", "es") if (armour or {}).get(k)]
    return "_".join(keys) if keys else "none"


def main(ee2, out):
    data = os.path.join(ee2, "renderer", "public", "data", "en")
    items = [json.loads(l) for l in open(os.path.join(data, "items.ndjson"), encoding="utf-8") if l.strip()]
    stats = [json.loads(l) for l in open(os.path.join(data, "stats.ndjson"), encoding="utf-8") if l.strip()]
    try:
        commit = subprocess.run(["git", "-C", ee2, "log", "-1", "--format=%H %cs"], capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = ""

    classes, bases, groups = {}, {}, {}
    for ee2_cat, (cid, name, trade, kind) in CLASSES.items():
        classes[cid] = {"name": name, "trade": trade, "kind": kind, "ee2": ee2_cat}
    for it in items:
        if it.get("namespace") != "ITEM":
            continue
        cat = (it.get("craftable") or {}).get("category")
        if cat not in CLASSES or not it.get("name"):
            continue
        cid = CLASSES[cat][0]
        name, fam = it["name"], family(it["name"])
        d = defence_of(it.get("armour")) if CLASSES[cat][3] == "armour" else None
        if cid in PER_BASE:
            gid, gname = f"{cid}.{re.sub(r'[^a-z0-9]+', '_', fam.lower()).strip('_')}", fam
            if cid == "flask":
                kind = "life" if "Life" in fam else "mana"
                gid, gname = f"flask.{kind}", f"{kind.title()} Flasks"
        elif d:
            gid, gname = f"{cid}.{d}", f"{classes[cid]['name']}: {DEFENCE_NAMES[d]}"
        else:
            gid, gname = cid, classes[cid]["name"]
        b = bases.get(name)
        if b is None:
            b = bases[name] = {"class": cid, "family": fam, "group": gid, "tags": sorted(set(it.get("tags") or [])),
                               "w": it.get("w"), "h": it.get("h")}
            if d:
                b["defence"] = d
            if it.get("armour"):
                b["armour"] = {k: v for k, v in it["armour"].items() if v}
        else:                                  # the same name twice (an older and a newer version): keep the higher values
            b["tags"] = sorted(set(b["tags"]) | set(it.get("tags") or []))
            for k, v in (it.get("armour") or {}).items():
                if v and (k not in b.get("armour", {}) or v[1] > b["armour"][k][1]):
                    b.setdefault("armour", {})[k] = v
        g = groups.setdefault(gid, {"name": gname, "class": cid, "defence": d, "bases": []})
        if name not in g["bases"]:
            g["bases"].append(name)
    for g in groups.values():
        g["bases"].sort()

    out_stats = []
    for s in stats:
        ids = (s.get("trade") or {}).get("ids") or {}
        if not ids:
            continue
        e = {"ref": s["ref"], "better": s.get("better", 1), "trade": ids,
             "matchers": [{k: v for k, v in m.items() if k in ("string", "negate", "value")} for m in s.get("matchers", [])]}
        if s.get("id"):
            e["id"] = s["id"]
            if s["id"].startswith("local_"):
                e["local"] = True
        if s.get("dp"):
            e["dp"] = True
        out_stats.append(e)

    currency, uniques = {}, defaultdict(list)
    for it in items:
        if it.get("namespace") == "ITEM" and it.get("tradeTag") and it.get("name"):
            currency[it["name"]] = {"trade": it["tradeTag"], "category": (it.get("craftable") or {}).get("category")}
        if it.get("namespace") == "UNIQUE" and it.get("name"):
            base = (it.get("unique") or {}).get("base")
            if base and base not in uniques[it["name"]]:
                uniques[it["name"]].append(base)

    doc = {
        "version": GAMEDATA_VERSION,
        "generated": date.today().isoformat(),
        "source": {"name": "Exiled Exchange 2", "url": "https://github.com/Kvan7/Exiled-Exchange-2", "licence": "MIT",
                   "commit": commit},
        "classes": classes, "groups": dict(sorted(groups.items())), "bases": dict(sorted(bases.items())),
        "stats": out_stats, "pseudo_rules": pseudo_rules(),
        "currency": dict(sorted(currency.items())), "uniques": dict(sorted(uniques.items())),
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{out}: {len(bases)} bases in {len(groups)} groups ({len(classes)} classes), {len(out_stats)} stats, "
          f"{len(doc['pseudo_rules'])} pseudo rules, {len(currency)} stackables, {len(uniques)} uniques, "
          f"{os.path.getsize(out) // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "gamedata.json")
