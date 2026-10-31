"""Build anointdata.json for Game search > Anoints (2.17.0): which three Liquid Emotions instil each notable.

    git clone --depth 1 https://github.com/repoe-fork/poe2 repoe2
    git clone --depth 1 --filter=blob:none --sparse https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2 pob2
    (cd pob2 && git sparse-checkout set src/TreeData)
    py tools/build_anointdata.py pob2/src/TreeData/0_5/tree.json repoe2/data/base_items.json repoe2/version.txt

The emotion item names come from RePoE (base_items.json). RePoE doesn't export the anoint recipes, so those come from
the passive tree that Path of Building extracts from the same game files (each notable's "recipe").
Writes anointdata.json next to the app; bump "anointdata.json" in BUNDLED_DATA (soe2/config.py) after a rebuild."""
import json
import re
import sys

tree_path, items_path = sys.argv[1], sys.argv[2]
ver = open(sys.argv[3]).read().strip() if len(sys.argv) > 3 else "?"
items = json.load(open(items_path, encoding="utf-8"))
emotions = {}                                       # "Ire" -> "Diluted Liquid Ire", in tier order
for pre in ("Metadata/Items/Currency/DistilledEmotion", "Metadata/Items/Currency/EndgameDistilledEmotion"):
    for i in range(1, 30):
        it = items.get(f"{pre}{i}")
        if not it:
            break
        emotions[it["name"].split()[-1]] = it["name"]
tree = json.load(open(tree_path, encoding="utf-8"))
rows, missing = [], set()
for node in tree["nodes"].values():
    if not isinstance(node, dict) or not node.get("recipe") or not node.get("name"):
        continue
    rec = list(node["recipe"])
    missing |= {r for r in rec if r not in emotions}
    stats = " | ".join(re.sub(r"\s+", " ", s).strip() for s in node.get("stats") or [])
    rows.append([node["name"], rec, stats])
if missing:
    sys.exit(f"recipe emotions with no item in base_items.json: {sorted(missing)}")
rows.sort(key=lambda r: r[0])
seen, out = set(), []
for r in rows:                                      # a few notables appear twice on the tree with the same recipe
    k = (r[0], tuple(r[1]))
    if k not in seen:
        seen.add(k)
        out.append(r)
data = {"version": ver, "source": "Liquid Emotion names: RePoE export of Path of Exile 2's game files. Recipes: the "
                                  "passive tree Path of Building extracts from the game files.",
        "emotions": emotions, "rows": out}
with open("anointdata.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
print(f"anointdata.json: {len(out)} anoints, {len(emotions)} emotions, game version {ver}")
