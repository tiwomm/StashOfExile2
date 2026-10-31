"""Prints the release notes for one version (python tools/release_notes.py 2.5.0), from soe2/whatsnew.py's NOTES -
the same plain lines the app shows in What's new. Used by .github/workflows/release.yml.

2.19.0: also lists every version since the last published one (the newest v<version> git tag), so a release that
carries several versions (2.16.0 - 2.19.0 in one merge) shows all of them; and always writes UTF-8 (a "★" in the
notes stopped the Windows build: its console is cp1252)."""
import ast
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def vt(s):
    return tuple(int(x) for x in re.findall(r"\d+", s.split("-")[0])[:3])


v = sys.argv[1]
src = open(os.path.join(os.path.dirname(__file__), "..", "soe2", "whatsnew.py"), encoding="utf-8").read()
notes = {}
for node in ast.parse(src).body:                     # read NOTES without importing the app (no tkinter needed)
    if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "NOTES" for t in node.targets):
        notes = ast.literal_eval(node.value)
try:
    tags = subprocess.run(["git", "tag", "--list", "v*"], capture_output=True, text=True, timeout=20).stdout.split()
    released = [t[1:] for t in tags if re.match(r"^v\d+\.\d+\.\d+$", t) and vt(t[1:]) < vt(v)]
    prev = max(released, key=vt) if released else None
except Exception:
    prev = None
versions = sorted((k for k in notes if vt(k) <= vt(v) and (prev is None and k == v or prev and vt(k) > vt(prev))),
                  key=vt, reverse=True) or [v]
for i, ver in enumerate(versions):
    print(f"{'## What' + chr(39) + 's new in ' + ver if i == 0 else '### ' + ver}\n")
    for line in notes.get(ver) or ["See the VERSION HISTORY at the top of stashofexile2.py."]:
        print(f"- {line}")
    print()
print("**Download:** StashOfExile2.exe (Windows). The app keeps your data in %APPDATA%\\StashOfExile2, so updating "
      "never touches it.\n\nThis product isn't affiliated with or endorsed by Grinding Gear Games in any way.")
