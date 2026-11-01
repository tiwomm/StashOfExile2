"""Build moneymakers.json from the strats/ folder (2.28.0). Every file is checked against the layout
(soe2.moneymakers.validate - the same check the app uses).

    py tools/build_strats.py           check + write moneymakers.json (revision goes up when the strats changed)
    py tools/build_strats.py --check   check only (exit 1 on a problem) - run by CI on every pull request"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from soe2.moneymakers import SCHEMA, tidy, validate  # noqa: E402

FOLDER, OUT = os.path.join(ROOT, "strats"), os.path.join(ROOT, "moneymakers.json")


def collect():
    strats, problems = [], []
    for name in sorted(os.listdir(FOLDER)):
        if not name.endswith(".json") or name.startswith("_"):
            continue
        try:
            with open(os.path.join(FOLDER, name), encoding="utf-8") as f:
                s = json.load(f)
        except Exception as e:
            problems.append(f"{name}: not valid JSON ({e})")
            continue
        bad = validate(s)
        if s.get("id") and name != s["id"] + ".json":
            bad.append(f"file name must be {s['id']}.json")
        problems += [f"{name}: {p}" for p in bad]
        strats.append(tidy(s))
    ids = [s.get("id") for s in strats]
    problems += [f"id used twice: {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    return strats, problems


def main():
    strats, problems = collect()
    for p in problems:
        print("PROBLEM", p)
    if problems:
        return 1
    if "--check" in sys.argv:
        print(f"OK: {len(strats)} strats")
        return 0
    old = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    rev = old.get("revision", 0) + (old.get("strats") != strats)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"schema": SCHEMA, "revision": rev, "strats": strats}, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"moneymakers.json: {len(strats)} strats, revision {rev}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
