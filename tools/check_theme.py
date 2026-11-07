"""Every colour in the app follows the theme (2.111.0). Lists colours written into the code (bg="#...", fg=...,
fill=..., a tag's foreground / background...) that stay the same in every theme pack - use a C[...] token instead.

  py tools/check_theme.py        exit 1 if any

Not checked: the overlay's own looks (they follow the overlay Style: ovskins, ovlight, hudart, overlaywin), the
theme engine itself (themes.py, style.py's palette), the start-up screen, and lines marked "# theme-ok" (colours
that must not change: item rarity, the game's own colours)."""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
SKIP = {"ovskins.py", "hudart.py", "ovlight.py", "overlaywin.py", "themes.py", "splash.py"}
PAT = re.compile(r'\b(bg|fg|foreground|background|fill|outline|highlightbackground|highlightcolor|activebackground|'
                 r'activeforeground|selectbackground|selectforeground|troughcolor|insertbackground)\s*=\s*'
                 r'"(#[0-9a-fA-F]{6})"')


def main():
    from soe2 import style, themes
    hits = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "soe2", "*.py"))):
        if os.path.basename(f) in SKIP:
            continue
        for i, line in enumerate(open(f, encoding="utf-8"), 1):
            if "theme-ok" in line:
                continue
            for m in PAT.finditer(line):
                hits.setdefault(m.group(2).lower(), []).append(f"soe2/{os.path.basename(f)}:{i}")
    themes.init(style.C, style._BASE)
    seen = {}
    for pid, pack in themes.packs().items():
        themes.set_theme(pack, None)
        for c in hits:
            seen.setdefault(c, set()).add(themes.tone(c))
    bad = sorted(c for c, v in seen.items() if len(v) == 1 and len(themes.packs()) > 1)
    for c in bad:
        print(f"{c}  same in every theme: {', '.join(hits[c])}")
    print("OK - every colour follows the theme" if not bad else f"{len(bad)} colour(s) ignore the theme - use C[...]")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
