"""Prints the release notes for one version (python tools/release_notes.py 2.5.0), from soe2/whatsnew.py's NOTES -
the same plain lines the app shows in What's new. Used by .github/workflows/release.yml."""
import ast
import os
import sys

v = sys.argv[1]
src = open(os.path.join(os.path.dirname(__file__), "..", "soe2", "whatsnew.py"), encoding="utf-8").read()
notes = {}
for node in ast.parse(src).body:                     # read NOTES without importing the app (no tkinter needed)
    if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "NOTES" for t in node.targets):
        notes = ast.literal_eval(node.value)
lines = notes.get(v) or ["See the VERSION HISTORY at the top of stashofexile2.py."]
print(f"## What's new in {v}\n")
for line in lines:
    print(f"- {line}")
print("\n**Download:** StashOfExile2.exe (Windows). The app keeps your data in %APPDATA%\\StashOfExile2, so updating "
      "never touches it.\n\nThis product isn't affiliated with or endorsed by Grinding Gear Games in any way.")
