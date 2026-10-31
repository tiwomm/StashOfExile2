"""Build default_rules.json (the Mod book rules everyone starts with) from a mod_rules.json - the author's own rules.

    py tools/build_default_rules.py path\\to\\mod_rules.json [path\\to\\mod_tiers.json]

The current default_rules.json is the starting point (the app only saves a rule that differs from the default, so
a mod you left at its default isn't in mod_rules.json); your rules are laid over it.

Each rule goes under its kind of mod (tablet / jewel / waystone / relic) as High / Normal / Ignore, with tiers if
given. Your own rules always win over these. Bump "default_rules.json" in BUNDLED_DATA (soe2/config.py) after."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from soe2.mods import JEWELS, mod_cat, pretty, scoped, TABS  # noqa: E402

from soe2.mods import DEFAULT_RULES  # noqa: E402

rules = dict(DEFAULT_RULES)                        # what ships now (rule key -> impact) ...
rules.update(json.load(open(sys.argv[1], encoding="utf-8")))      # ... with your own rules over it
tiers = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 else {}
out = {"about": "Built-in mod rules that ship with StashOfExile2 (the author's own rules, exported "
                + time.strftime("%b %d, %Y") + "). Your own rules (Mod book) always win over these.", "version": 3}
skipped = []


def text_of(k):
    body = k.split(":", 1)[1] if scoped(k) else k
    return (TABS.get(body) or JEWELS.get(body) or [pretty(body)])[0]


for k, imp in sorted(rules.items()):
    cat = scoped(k) or mod_cat(k)
    if cat not in ("tablet", "jewel", "waystone", "relic") or imp not in ("high", "normal", "ignore"):
        skipped.append(k)
        continue
    out.setdefault(cat, {}).setdefault(imp, []).append(text_of(k))
for k, t in sorted(tiers.items()):
    cat = scoped(k) or mod_cat(k)
    if cat in ("tablet", "jewel", "waystone", "relic"):
        out.setdefault(cat, {}).setdefault("tiers", {})[text_of(k)] = t
with open("default_rules.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print("default_rules.json:", {c: {i: len(v) for i, v in d.items()} for c, d in out.items() if isinstance(d, dict)},
      f"skipped {len(skipped)}: {skipped[:5]}")
