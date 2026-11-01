"""The Map library (2.32.0): every endgame area - maps, towers, unique maps, citadels, pinnacle fights and league
areas - with your rank for each, and what the Session tracker learned.

  * mapdata.json (built by tools/build_mapdata.py from the game data) is the list the app ships with.
  * maps_learned.json: endgame areas the game added later. The tracker learns one the first time you enter it
    (level 65+, not a hideout or a town); "Not a map" in the library forgets it and never counts it again.
  * map_ranks.json: your ranks - S A B C D, or Avoid - by map name (what the tracker shows). They live in the data
    folder, so they carry over to every new version. Export / Import share them as a .json file; on import you pick
    Replace all, Add and update, or Add new only (keep yours where they differ).
Your ranks also count as your vote for the community map ranks (communitymods: hourly, anonymous)."""
import json
import os
import re
import time

from .config import APP_DIR, RESOURCE_DIR, P, load_json, save_json

FILE, LEARNED, RANKS_FILE = "mapdata.json", "maps_learned.json", "map_ranks.json"
RANKS = ("S", "A", "B", "C", "D", "Avoid")
SCORE = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}        # for the community average (Avoid is counted apart)
KINDS = ("Map", "Tower", "Unique map", "Citadel", "Pinnacle", "League area", "Learned")
EXPORT_FORMAT = "soe2-map-ranks"
CAMPAIGN = re.compile(r"^(G\d|P\d|C_|G_)")              # campaign / interlude / login areas: never maps

_lib = None


def _bundled():
    for path in (P(FILE), os.path.join(RESOURCE_DIR, FILE), os.path.join(APP_DIR, FILE)):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict) and isinstance(d.get("areas"), dict):
                return d["areas"]
        except Exception:
            continue
    return {}


def learned():
    d = load_json(LEARNED, {})
    return d if isinstance(d, dict) else {}


def library(reload=False):
    """{map name: {"kind", "ids": [area ids], "level", "learned": bool}} - shipped areas + learned ones."""
    global _lib
    if _lib is not None and not reload:
        return _lib
    out = {}
    for aid, a in _bundled().items():
        e = out.setdefault(a["name"], {"kind": a["kind"], "ids": [], "level": a.get("level"), "learned": False})
        e["ids"].append(aid)
    for aid, a in learned().items():
        if a.get("not_map") or not a.get("name"):
            continue
        e = out.setdefault(a["name"], {"kind": "Learned", "ids": [], "level": a.get("level"), "learned": True})
        if aid not in e["ids"]:
            e["ids"].append(aid)
    _lib = out
    return out


def id_name(area_id):
    for name, e in library().items():
        if area_id in e["ids"]:
            return name
    return None


def is_hideout(area_id, name=""):
    return "hideout" in (area_id or "").lower() or str(name or "").strip().lower().endswith("hideout")


def area_kind(area_id, seed, level=0):
    """'map' (anything the tracker counts as a run), 'hideout', 'town' or 'other'."""
    a = area_id or ""
    if is_hideout(a):
        return "hideout"
    if seed == 1:
        return "town"
    if id_name(a) or a.startswith("Map"):
        return "map"
    lg = learned().get(a)
    if lg and lg.get("not_map"):
        return "other"
    if lg or (level or 0) >= 65 and not CAMPAIGN.match(a):
        return "map"                                     # an endgame area the library doesn't know yet: learn it
    return "other"


def learn(area_id, name, level=None):
    """The tracker entered an endgame area the library doesn't know (and got its name from the game). -> True if new."""
    if not area_id or not name or is_hideout(area_id, name) or id_name(area_id):
        return False
    d = learned()
    if area_id in d and d[area_id].get("name") == name:
        return False
    d[area_id] = {"name": name, "level": level, "first_seen": d.get(area_id, {}).get("first_seen") or time.time(),
                  "not_map": d.get(area_id, {}).get("not_map", False)}
    save_json(LEARNED, d)
    library(reload=True)
    return True


def not_a_map(name):
    """'Not a map' on a learned entry: forget it and never count it again."""
    d = learned()
    hit = False
    for aid, a in d.items():
        if a.get("name") == name:
            a["not_map"] = True
            hit = True
    if hit:
        save_json(LEARNED, d)
        library(reload=True)
    return hit


# ---------------------------------------------------------------- your ranks
def ranks():
    d = load_json(RANKS_FILE, {})
    return {k: v for k, v in d.items() if v in RANKS} if isinstance(d, dict) else {}


def set_rank(names, rank):
    """rank None = no rank."""
    r = ranks()
    for n in names if isinstance(names, (list, tuple, set)) else [names]:
        if rank in RANKS:
            r[n] = rank
        else:
            r.pop(n, None)
    save_json(RANKS_FILE, r)
    return r


def export_ranks(path, only=None):
    r = ranks()
    if only:
        r = {k: v for k, v in r.items() if k in only}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"format": EXPORT_FORMAT, "version": 1, "exported": time.strftime("%Y-%m-%d"), "ranks": r}, f,
                  indent=1, ensure_ascii=False)
    return len(r)


def read_ranks_file(path):
    """-> {name: rank} from an exported file (raises ValueError when it isn't one)."""
    with open(path, encoding="utf-8-sig") as f:
        d = json.load(f)
    return check_ranks(d)


def check_ranks(d):
    if not isinstance(d, dict) or d.get("format") != EXPORT_FORMAT or not isinstance(d.get("ranks"), dict):
        raise ValueError("not a map ranks file (Map library > Export makes one)")
    out = {str(k)[:80]: v for k, v in d["ranks"].items() if v in RANKS and str(k).strip()}
    if not out:
        raise ValueError("it has no ranks in it")
    return out


def compare(incoming):
    """-> (new, same, differ) against your ranks."""
    mine = ranks()
    new = {k: v for k, v in incoming.items() if k not in mine}
    same = [k for k, v in incoming.items() if mine.get(k) == v]
    differ = {k: v for k, v in incoming.items() if k in mine and mine[k] != v}
    return new, same, differ


def apply_import(incoming, mode):
    """mode: "replace" (your ranks become the file's), "update" (add new + take the file's where they differ),
    "add" (add new only - keep yours where they differ). -> how many ranks changed."""
    mine = ranks()
    if mode == "replace":
        changed = len(set(mine) ^ set(incoming)) + sum(1 for k in incoming if k in mine and mine[k] != incoming[k])
        save_json(RANKS_FILE, dict(incoming))
        return changed
    new, _same, differ = compare(incoming)
    mine.update(new)
    if mode == "update":
        mine.update(differ)
    save_json(RANKS_FILE, mine)
    return len(new) + (len(differ) if mode == "update" else 0)


# ---------------------------------------------------------------- the community's ranks (downloaded by communitymods)
def community():
    """name -> {"rank": average letter, "score": 1-5, "votes": n, "avoid": n} (at least 2 votes)."""
    d = load_json("community_mods.json", {})
    out = {}
    for row in d.get("maps", []) if isinstance(d, dict) else []:
        try:
            name, counts = row
        except (TypeError, ValueError):
            continue
        scored = sum(counts.get(k, 0) for k in SCORE)
        total = scored + counts.get("Avoid", 0)
        if total < 2:
            continue
        avg = sum(SCORE[k] * counts.get(k, 0) for k in SCORE) / scored if scored else 0
        letter = min(SCORE, key=lambda k: abs(SCORE[k] - avg)) if scored else "Avoid"
        if counts.get("Avoid", 0) > scored:
            letter = "Avoid"
        out[name] = {"rank": letter, "score": round(avg, 2), "votes": total, "avoid": counts.get("Avoid", 0)}
    return out
