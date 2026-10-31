"""Check that every place holding the version agrees, and that it is SemVer 2.0.0 (2.10.0).

    py tools/check_version.py        (run from the project folder; exit code 1 + PROBLEM lines when something is off)

Places: APP_VERSION and the VERSION line in stashofexile2.py, __version__ in soe2/__init__.py, the newest
VERSION HISTORY entry in stashofexile2.py, the newest NOTES entry in soe2/whatsnew.py, "Current version" in ROADMAP.md."""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def found():
    out = {}
    launcher = read("stashofexile2.py")
    m = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', launcher, re.M)
    out["APP_VERSION (stashofexile2.py)"] = m and m.group(1)
    m = re.search(r"^VERSION\s+v?(\d+\.\d+\.\d+\S*)\s*$", launcher, re.M)
    out["VERSION line (stashofexile2.py)"] = m and m.group(1)
    m = re.search(r"VERSION HISTORY.*?\n\s*v?(\d+\.\d+\.\d+[^\s:]*)", launcher, re.S)
    out["newest VERSION HISTORY entry"] = m and m.group(1)
    m = re.search(r'__version__\s*=\s*"([^"]+)"', read(os.path.join("soe2", "__init__.py")))
    out["__version__ (soe2/__init__.py)"] = m and m.group(1)
    tree = ast.parse(read(os.path.join("soe2", "whatsnew.py")))
    notes = next((n.value for n in tree.body if isinstance(n, ast.Assign)
                  and any(getattr(t, "id", "") == "NOTES" for t in n.targets)), None)
    keys = [k.value for k in getattr(notes, "keys", [])] if notes is not None else []
    out["newest NOTES entry (whatsnew.py)"] = max(keys, key=vt) if keys else None
    m = re.search(r"Current version:\s*\**\s*v?(\d+\.\d+\.\d+\S*?)\**\s*$", read("ROADMAP.md"), re.M)
    out["Current version (ROADMAP.md)"] = m and m.group(1)
    return out


def vt(v):
    return tuple(int(x) for x in re.findall(r"\d+", v.split("-")[0])[:3])


def main():
    vals = found()
    want = vals["APP_VERSION (stashofexile2.py)"]
    problems = []
    if not want or not SEMVER.match(want):
        problems.append(f"APP_VERSION {want!r} is not MAJOR.MINOR.PATCH")
    for where, v in vals.items():
        if v != want:
            problems.append(f"{where} is {v!r}, APP_VERSION is {want!r}")
    for where, v in vals.items():
        print(f"  {where:40} {v}")
    for p in problems:
        print("PROBLEM", p)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
