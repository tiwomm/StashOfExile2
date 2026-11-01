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
import soe2.moneymakers as MM  # noqa: E402
from soe2.moneymakers import SCHEMA, from_text, tidy, tidy_one, validate, validate_one  # noqa: E402

FOLDER, OUT = os.path.join(ROOT, "strats"), os.path.join(ROOT, "moneymakers.json")
BOARD_SCHEMA = os.path.join(ROOT, "board", "src", "schema.json")


def write_board_schema():
    """2.30.0: the layout rules for the community board server (board/src/index.js checks posts with them), so
    the app and the server never disagree."""
    d = {"schema": SCHEMA, "taxonomy": MM.TAXONOMY, "tags": list(MM.ALL_TAGS), "tag_groups": MM.TAG_GROUPS,
         "thinking": {str(k): w for k, (w, _d) in MM.THINKING.items()}, "clicks": list(MM.CLICKS),
         "units": list(MM.UNITS), "required": list(MM.REQUIRED), "lists": list(MM.LISTS), "order": list(MM.ORDER),
         "one_order": list(MM.ONE_ORDER)}
    os.makedirs(os.path.dirname(BOARD_SCHEMA), exist_ok=True)
    with open(BOARD_SCHEMA, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")


def collect():
    strats, problems = [], []
    for name in sorted(os.listdir(FOLDER)):
        if name.startswith("_") or name == "oneliners.json" or not name.endswith((".json", ".txt", ".csv")):
            continue
        path = os.path.join(FOLDER, name)
        try:
            with open(path, encoding="utf-8-sig") as f:
                s = json.load(f) if name.endswith(".json") else MM.read_any(f.read())     # .csv (2.46.0) or .txt
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
    if "--check" not in sys.argv:
        write_board_schema()
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
    url_file = os.path.join(ROOT, "board", "url.txt")
    board_url = open(url_file, encoding="utf-8").read().strip() if os.path.exists(url_file) else ""
    rev = old.get("revision", 0) + (old.get("strats") != strats or old.get("oneliners", []) != ones or
                                    old.get("board_url", "") != board_url)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        out = {"schema": SCHEMA, "revision": rev, "strats": strats, "oneliners": ones}
        if board_url:
            out["board_url"] = board_url                     # 2.30.0: where the Community board lives
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"moneymakers.json: {len(strats)} strats, {len(ones)} one-liners, revision {rev}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
