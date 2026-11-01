"""Build moneymakers.json from the strats/ folder (2.28.0): one strat per file (.json, or the plain-text .txt
layout from the app's Download Format) plus oneliners.json (Lucrative Strats). Every file is checked against the layout
(soe2.moneymakers.validate - the same check the app uses).

    py tools/build_strats.py           check + write moneymakers.json (revision goes up when the strats changed)
    py tools/build_strats.py --check   check only (exit 1 on a problem) - run by CI on every pull request"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from soe2.moneymakers import SCHEMA, from_text, tidy, tidy_one, validate, validate_one  # noqa: E402

FOLDER, OUT = os.path.join(ROOT, "strats"), os.path.join(ROOT, "moneymakers.json")


def collect():
    strats, problems = [], []
    for name in sorted(os.listdir(FOLDER)):
        if name.startswith("_") or name == "oneliners.json" or not name.endswith((".json", ".txt")):
            continue
        path = os.path.join(FOLDER, name)
        try:
            with open(path, encoding="utf-8-sig") as f:
                s = json.load(f) if name.endswith(".json") else from_text(f.read())
        except Exception as e:
            problems.append(f"{name}: can't be read ({e})")
            continue
        bad = validate(s)
        stem = os.path.splitext(name)[0]
        if s.get("id") and stem != s["id"]:
            bad.append(f"file name must be {s['id']}{os.path.splitext(name)[1]}")
        problems += [f"{name}: {p}" for p in bad]
        strats.append(tidy(s))
    ids = [s.get("id") for s in strats]
    problems += [f"id used twice: {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    ones = []
    path = os.path.join(FOLDER, "oneliners.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8-sig") as f:
                raw = json.load(f)
        except Exception as e:
            raw, _ = [], problems.append(f"oneliners.json: can't be read ({e})")
        for o in raw if isinstance(raw, list) else []:
            problems += [f"oneliners.json {o.get('id', '?') if isinstance(o, dict) else '?'}: {p}" for p in validate_one(o)]
            ones.append(tidy_one(o) if isinstance(o, dict) else o)
        oids = [o.get("id") for o in ones if isinstance(o, dict)]
        problems += [f"oneliners.json: id used twice: {i}" for i in sorted({i for i in oids if oids.count(i) > 1})]
    return strats, ones, problems


def main():
    strats, ones, problems = collect()
    for p in problems:
        print("PROBLEM", p)
    if problems:
        return 1
    if "--check" in sys.argv:
        print(f"OK: {len(strats)} strats, {len(ones)} one-liners")
        return 0
    old = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    rev = old.get("revision", 0) + (old.get("strats") != strats or old.get("oneliners", []) != ones)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"schema": SCHEMA, "revision": rev, "strats": strats, "oneliners": ones}, f, indent=1,
                  ensure_ascii=False)
        f.write("\n")
    print(f"moneymakers.json: {len(strats)} strats, {len(ones)} one-liners, revision {rev}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
