"""2.81.0: tierdata.json for the Desecration Helper - every prefix / suffix (the item pool and the Abyss lords'
desecrated mods) by its wording with the numbers taken out, each tier with its level, value ranges and spawn tags;
every equipment base with its class, tags and a small fingerprint of its picture (to tell the item in the Well's slot).

    git clone --depth 1 --filter=blob:none --sparse https://github.com/repoe-fork/poe2 repoe2
    cd repoe2 && git sparse-checkout set data && cd ..
    py tools/build_tierdata.py repoe2/data

Data: RePoE (https://github.com/repoe-fork/poe2), Path of Exile 2's game files - see THIRD_PARTY_NOTICES.txt."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from soe2.wellsouls import clean, fingerprint, fp_pack, NUM, template  # noqa: E402

CLASSES = {"Gloves", "Boots", "Helmet", "Body Armour", "Shield", "Buckler", "Focus", "Quiver", "Belt", "Ring", "Amulet",
           "Jewel", "One Hand Mace", "Two Hand Mace", "Warstaff", "Spear", "Bow", "Crossbow", "Talisman",
           "One Hand Sword", "Two Hand Sword", "One Hand Axe", "Two Hand Axe", "Dagger", "Flail", "Staff", "Wand",
           "Sceptre", "Claw"}


def ranges(text):
    out = []
    for m in NUM.finditer(clean(text).replace("+", "")):
        if m.group(1) is not None:
            out.append([float(m.group(1)), float(m.group(2))])
        else:
            out.append([float(m.group(3))] * 2)
    return out


HEART_TAGS = ("heart_unique_jewel_prefix", "heart_unique_jewel_suffix")
HEART_BASE = {"n": "Heart of the Well", "c": "Jewel", "t": list(HEART_TAGS), "a": "JewelDiamond"}


def heart_mods(mods, table):
    """2.130.3 (feedback: the Desecration Helper showed nothing on a Heart of the Well): the unique Diamond's own
    desecrated mods (generation type "unique", tags heart_unique_jewel_prefix / _suffix). One range each - shown as
    Heart with where the roll sits in it."""
    n = 0
    for mid, m in mods.items():
        spawn = [[w["tag"], w["weight"]] for w in m.get("spawn_weights") or []]
        side = next((t for t, w in spawn if t in HEART_TAGS and w > 0), None)
        if not side or not m.get("text"):
            continue
        entry = {"g": mid, "k": "p" if side.endswith("prefix") else "s", "l": m.get("required_level", 1),
                 "r": ranges(m["text"]), "s": spawn, "a": 1, "h": 1, "id": mid}
        lst = table.setdefault(template(m["text"]), [])
        if not any(e.get("id") == mid for e in lst):
            lst.append(entry)
            n += 1
    return n


def add_heart(src, out="tierdata.json"):
    """py tools/build_tierdata.py --heart [repoe2/data]: add the Heart of the Well's mods to the tierdata.json there
    is (nothing else in it changes)."""
    mods = json.load(open(os.path.join(src, "mods.json"), encoding="utf-8"))
    data = json.load(open(out, encoding="utf-8"))
    n = heart_mods(mods, data["mods"])
    data["bases"] = [b for b in data["bases"] if b["n"] != HEART_BASE["n"]] + [dict(HEART_BASE)]
    if HEART_BASE["a"] not in data.get("arts", {}):
        data["bases"][-1]["a"] = None
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), sort_keys=True)
    print(f"{n} Heart of the Well mods added -> {out}")


def main(src, out="tierdata.json"):
    from PIL import Image
    mods = json.load(open(os.path.join(src, "mods.json"), encoding="utf-8"))
    bases = json.load(open(os.path.join(src, "base_items.json"), encoding="utf-8"))
    table = {}
    heart_mods(mods, table)
    for mid, m in mods.items():
        if m.get("domain") not in ("item", "desecrated") or m.get("generation_type") not in ("prefix", "suffix"):
            continue
        if not m.get("text") or m.get("is_essence_only"):
            continue
        spawn = [[w["tag"], w["weight"]] for w in m.get("spawn_weights") or []]
        if not any(w > 0 for _t, w in spawn):
            continue
        tpl = template(m["text"])
        table.setdefault(tpl, []).append({
            "g": (m.get("groups") or [mid])[0], "k": m["generation_type"][0], "l": m.get("required_level", 1),
            "r": ranges(m["text"]), "s": spawn,
            "a": 1 if m["domain"] == "desecrated" or any(t in ("kurgal_mod", "amanamu_mod", "ulaman_mod")
                                                         for t, _w in spawn) else 0, "id": mid})
    arts, blist = {}, []
    for k, b in bases.items():
        if b.get("item_class") not in CLASSES or b.get("release_state") == "unreleased":
            continue
        dds = (b.get("visual_identity") or {}).get("dds_file") or ""
        aid = os.path.splitext(os.path.basename(dds))[0]
        if aid and aid not in arts:
            stem = os.path.join(src, os.path.splitext(dds)[0])
            for ext in (".png", ".webp"):
                if os.path.exists(stem + ext):
                    try:
                        fp = fingerprint(Image.open(stem + ext).convert("RGBA"))
                        if fp:
                            arts[aid] = fp_pack(fp)
                    except Exception:
                        pass
                    break
        blist.append({"n": b["name"], "c": b["item_class"], "t": sorted(set(b.get("tags") or [])),
                      "a": aid if aid in arts else None})
    blist.append(dict(HEART_BASE, a=HEART_BASE["a"] if HEART_BASE["a"] in arts else None))
    data = {"version": 1, "source": {"name": "RePoE", "url": "https://github.com/repoe-fork/poe2"},
            "mods": table, "bases": blist, "arts": arts}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), sort_keys=True)
    print(f"{len(table)} mod wordings, {len(blist)} bases, {len(arts)} pictures -> {out} "
          f"({os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--heart"]:
        add_heart(a[1] if len(a) > 1 else "repoe2/data")
    else:
        main(a[0] if a else "repoe2/data")
