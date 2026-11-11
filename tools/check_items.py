"""2.121.0 (items pass): every base type and unique in gamedata.json, as a minimal copied item, through the gear
reader - does each one get its base, its class and a search the trade site can take (an unidentified unique too)?

    py tools/check_items.py

Prints what failed, grouped; exits 1 if anything did. Jewels, tablets and waystones have readers of their own."""
import collections
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from soe2 import gamedata as GD, gear as G  # noqa: E402
d = GD.load()
cls_text = {cid: c["name"] for cid, c in d["classes"].items()}
probs = collections.Counter(); ex = collections.defaultdict(list)
def item(rarity, name, base, cid, extra=""):
    return f"Item Class: {cls_text[cid]}\nRarity: {rarity}\n" + (f"{name}\n" if name else "") + f"{base}\n--------\nItem Level: 80\n--------\n{extra}"
n = 0
for base, b in d["bases"].items():
    cid = b.get("class")
    if cid not in cls_text:
        probs["base class not in classes"] += 1; ex["base class not in classes"].append(base); continue
    for rar, name in (("Rare", "Doom Grasp"), ("Magic", None), ("Normal", None)):
        if cid in ("tablet", "waystone", "relic", "jewel", "flask", "charm") and rar != "Rare":
            continue
        t = item(rar, name, base, cid)
        n += 1
        try:
            it = G.parse_gear(t)
        except Exception as e:
            probs["crash"] += 1; ex["crash"].append((base, rar, repr(e))); continue
        if it is None:
            k = f"not gear ({cid})"; probs[k] += 1; ex[k].append(base); continue
        if it.get("base") != base:
            probs["base mismatch"] += 1; ex["base mismatch"].append((base, it.get("base")))
        s = it.get("search") or {}
        if not (s.get("type") or s.get("category")):
            probs["no type/category"] += 1; ex["no type/category"].append(base)
for uname, bases in (d.get("uniques") or {}).items():
    for base in bases:
        b = d["bases"].get(base)
        if not b:
            probs["unique on unknown base"] += 1; ex["unique on unknown base"].append((uname, base)); continue
        cid = b["class"]
        for unid in (False, True):
            t = item("Unique", None if unid else uname, base, cid, "Unidentified" if unid else "")
            n += 1
            try:
                it = G.parse_gear(t)
            except Exception as e:
                probs["unique crash"] += 1; ex["unique crash"].append((uname, repr(e))); continue
            if it is None:
                probs[f"unique not gear ({cid})"] += 1; ex[f"unique not gear ({cid})"].append(uname); continue
            s = it["search"]
            if unid:
                if s.get("name") == base:
                    probs["unid: base as name"] += 1; ex["unid: base as name"].append(uname)
            elif s.get("name") != uname:
                probs["unique name lost"] += 1; ex["unique name lost"].append((uname, s.get("name")))
OWN_READERS = ("not gear (waystone)", "not gear (jewel)", "not gear (tablet)")
bad = {k: v for k, v in probs.items() if k not in OWN_READERS}
for k, v in sorted(bad.items(), key=lambda kv: -kv[1]):
    print(f"{v:5}  {k}   e.g. {ex[k][:4]}")
print(f"OK - {n} items read (every base and unique)" if not bad else f"{sum(bad.values())} problem(s) in {n} items")
sys.exit(1 if bad else 0)
