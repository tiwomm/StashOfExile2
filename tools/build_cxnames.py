"""Build cxnames.json: the names of everything traded on the Currency Exchange, by the game's own item id.

    py tools/build_cxnames.py repoe2/data/base_items.json

2.26.0: Grinding Gear Games' Currency Exchange history names items by their game id
("Metadata/Items/Currency/CurrencyModValues" = Divine Orb). The names come from RePoE's base_items.json."""
import json
import sys

CLASSES = {"StackableCurrency", "SoulCore", "Omen", "Support Skill Gem", "UncutSkillGemStackable",
           "UncutReservationGemStackable", "UncutSupportGemStackable", "MapFragment", "VaultKey",
           "PinnacleKeyStackable", "AtlasCurrency", "Breachstone", "Expedition2Logbooks", "IncubatorStackable",
           "DelveStackableSocketableCurrency", "AtlasUpgradeItem"}
bases = json.load(open(sys.argv[1], encoding="utf-8"))
out = {k: v["name"] for k, v in bases.items() if v.get("item_class") in CLASSES and v.get("name")}
with open("cxnames.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
print(f"cxnames.json: {len(out)} names")
