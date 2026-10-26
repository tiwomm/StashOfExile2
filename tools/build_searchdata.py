"""Turn the PoE2 Keyword Search page (PoE2-Search.html, built from the RePoE export of Path of Exile 2's game files)
into searchdata.json for the app's Game search window.

    py tools/build_searchdata.py path\\to\\PoE2-Search.html

Writes searchdata.json next to the app; bump "searchdata.json" in BUNDLED_DATA (soe2/config.py) so existing data
folders take the new copy."""
import json
import re
import sys

src = sys.argv[1] if len(sys.argv) > 1 else "PoE2-Search.html"
s = open(src, encoding="utf-8").read()
data = json.loads(re.search(r"var DATA = (\[.*?\]);\s*\n", s, re.S).group(1))
order = json.loads(re.search(r"var ORDER = (\[[^\]]*\])", s).group(1).replace("'", '"'))
ver = re.search(r'var META = \{ version: "([^"]+)"', s).group(1)
out = {"version": ver, "source": "RePoE export of Path of Exile 2's game files", "order": order,
       "nolink": ["Modifiers", "Keywords & Mechanics"], "rows": [[d["n"], d["g"], d["c"], d["k"], d["t"]] for d in data]}
with open("searchdata.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print(f"searchdata.json: {len(out['rows'])} entries, game version {ver}")
