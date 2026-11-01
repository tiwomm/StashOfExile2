"""Build mapdata.json - the Map library (2.32.0) - from RePoE's world_areas.json.

    py tools/build_mapdata.py [path to repoe2/data/world_areas.json]

Every endgame area the Session tracker can count, with a kind:
  Map, Tower, Unique map, Citadel (the lineage / special maps: citadels, Jade Isles ...), Pinnacle (Simulacrum,
  Arbiter, Breach, Ritual, Abyss, Expedition bosses ...), League area (Trials, Expedition logbooks, Vaal temple ...).
Hideouts, towns, the campaign and test areas are left out (the tracker never counts those). Areas the game adds later
are learned by the app the first time you enter them (maplib.learn)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), "repoe2", "data", "world_areas.json")
OUT = os.path.join(ROOT, "mapdata.json")

PINNACLE_IDS = {"BreachDomain_01", "RitualLeagueBoss", "Delirium_Act1Town", "Delirium_HungerBoss", "Abyss_Pinnacle",
                "Abyss_Boss1", "Abyss_Boss2", "ExpeditionLeagueBoss", "ChayulaLeague_TowerBoss",
                "ExpeditionSubArea_BlackKnightBoss"}
LEAGUE_PREFIX = ("Sanctum_", "Abyss_", "ExpeditionLogBook_", "ExpeditionSubArea_", "ChayulaLeague", "IncursionTemple",
                 "IncursionHubEndgame", "PrecursorVault", "Delirium_", "Abyss_Depths", "EndgameDoodad_")
SKIP = ("MapHideout", "Hideout", "MapLeaguePortal", "BossRush", "Design", "Programming", "BlackTest")


def kind_of(a):
    i, tags = a["id"], set(a.get("tags") or [])
    if a.get("is_town") or i.startswith(SKIP) or i.endswith("_Quest"):
        return None
    if a.get("area_level", 0) < 60 and i not in PINNACLE_IDS and not i.startswith(("Sanctum_", "Abyss_")):
        return None                                      # (the data gives trials and the Abyss a low level)
    if i in PINNACLE_IDS or "pinnacle_boss" in tags and not i.startswith("MapUberBoss_") or \
            i.startswith("MapUberBoss_") and "pinnacle_boss" in tags:
        return "Pinnacle"
    if i.startswith("MapUberBoss_"):
        return "Citadel"
    if i.startswith(("MapUnique", "Map_")) or i.startswith(("MapMothersoul", "MapVoid")):
        return "Unique map"
    if i.startswith("Map"):
        return "Tower" if "map_tower" in tags or i.startswith("MapPrecursorTower") else "Map"
    if i.startswith(LEAGUE_PREFIX):
        return "League area"
    return None


def main():
    with open(SRC, encoding="utf-8") as f:
        areas = json.load(f)
    out = {}
    for a in areas.values():
        k = kind_of(a)
        if k and a.get("name") and not a["name"].startswith("["):
            out[a["id"]] = {"name": a["name"].strip(), "kind": k, "level": a.get("area_level") or None}
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"version": 1, "source": "RePoE world_areas.json", "areas": dict(sorted(out.items()))}, f,
                  indent=1, ensure_ascii=False)
        f.write("\n")
    by = {}
    for v in out.values():
        by[v["kind"]] = by.get(v["kind"], 0) + 1
    print(f"mapdata.json: {len(out)} areas {by}")


if __name__ == "__main__":
    main()
