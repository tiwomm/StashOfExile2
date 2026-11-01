"""WCAG 2.1 AA contrast check for every theme x accent (2.34.0, Polish 1).

  py tools/check_contrast.py      prints the lowest pairs, exit 1 if any text pair is under 4.5 : 1

Pairs = the text colours the app puts on its surfaces (style.C / the button styles), after the theme recolours them."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from soe2 import style as S  # noqa: E402

AA = 4.5


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def pairs():
    C, mix = S.C, S.mix
    a, r = C["accent"], C["red"]
    out = []
    for surf in ("bg", "panel", "panel2", "odd", "stripe"):
        for fg in ("text", "muted", "steel", "accent", "good", "green", "red", "blue", "purple", "rare", "magic"):
            out.append((f"{fg} on {surf}", C[fg], C[surf]))
    out += [("white on selected row", "#ffffff", C["sel"]),
            ("list heading", "#cfe0ff", "#22365a"),
            ("button", "#e6eeff", "#25395f"),
            ("primary button", S.text_on(mix(a, "#000000", 0.15)), mix(a, "#000000", 0.15)),
            ("quiet button", C["steel"], C["panel"]),
            ("danger button", "#ffe9e6", mix(r, "#000000", 0.55)),
            ("title bar child button", "#e8eefc", "#22345a")]
    return out


def run():
    worst, fails = [], []
    for theme in S.THEMES:
        for accent in S.ACCENTS:
            S.C.update(S._BASE)
            S.apply_look(theme, accent)
            for name, fg, bg in pairs():
                fg, bg = S.theme_color(fg), S.theme_color(bg)
                r = ratio(fg, bg)
                worst.append((r, theme, accent, name, fg, bg))
                if r < AA:
                    fails.append((r, theme, accent, name, fg, bg))
    S.C.update(S._BASE)
    S.apply_look("midnight", "orange")
    return sorted(worst)[:8], sorted(fails)


if __name__ == "__main__":
    worst, fails = run()
    for r, t, a, n, fg, bg in (fails or worst)[:40]:
        print(f"{r:5.2f}  {t:9} {a:7} {n:28} {fg} on {bg}")
    print("OK - every pair is at least 4.5 : 1" if not fails else f"{len(fails)} pairs under 4.5 : 1")
    sys.exit(1 if fails else 0)
