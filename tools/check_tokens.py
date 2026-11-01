"""Keeps the code on the design tokens (2.34.0, Polish 1 - see soe2/style.py).

  py tools/check_tokens.py          list what is off the scale (exit 1 if anything)
  py tools/check_tokens.py --fix    move it onto the scale

Text: SMALL 9, BODY 10, HEAD 12, TITLE 16 (+ DISPLAY 18 / 20 / 22 / 28 for icon glyphs and big numbers).
Space (padx / pady / ipadx / ipady / padding / pad): 0 1 2 (hairlines, joined edges) or 4 8 12 16 24.
Not checked: canvas drawing (create_text - sized in pixels inside fixed shapes) and lines marked "# token-ok"."""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = {9, 10, 12, 16}
DISPLAY = {18, 20, 22, 28}
SPACE = {0, 1, 2, 4, 8, 12, 16, 24}
FONT = re.compile(r'(\(\s*(?:"(?:Segoe UI|Segoe UI Emoji|Segoe UI Symbol|Consolas|Palatino Linotype)"|FONT_TITLE|MONO)\s*,\s*)(\d+)(\s*(?:,\s*("[^"]*"))?)')
PAD = re.compile(r'(\b(?:i?pad[xy]|padding|pad)\s*=\s*)(\(\s*\d+(?:\s*,\s*\d+){1,3}\s*\)|\d+)(?![\w.])')


def font_size(n, bold):
    if n in TEXT or n in DISPLAY:
        return n
    if n <= 9:
        return 9
    if n == 11:
        return 12 if bold else 10
    if n <= 13:
        return 12
    if n <= 17:
        return 16
    return min(DISPLAY, key=lambda d: abs(d - n))


def space(n):
    if n in SPACE:
        return n
    return {3: 4, 5: 4, 6: 8, 7: 8, 9: 8, 10: 8, 11: 12, 13: 12, 14: 16, 15: 16, 18: 16, 20: 16, 22: 24}.get(n, 24 if n > 22 else n)


def scan(text, fix=False):
    out, bad = [], []
    for no, line in enumerate(text.split("\n"), 1):
        if "# token-ok" in line or line.lstrip().startswith("#"):
            out.append(line)
            continue
        def f(m):
            n = int(m.group(2))
            if "create_text" in line:
                return m.group(0)
            want = font_size(n, "bold" in (m.group(4) or ""))
            if want != n:
                bad.append((no, f"text size {n} -> {want}"))
            return m.group(1) + str(want) + m.group(3)

        def p(m):
            nums = [int(x) for x in re.findall(r"\d+", m.group(2))]
            want = [space(x) for x in nums]
            if want == nums:
                return m.group(0)
            bad.append((no, f"space {m.group(2)} -> {want}"))
            new = str(want[0]) if not m.group(2).startswith("(") else "(" + ", ".join(map(str, want)) + ")"
            return m.group(1) + new
        line = FONT.sub(f, line)
        line = PAD.sub(p, line)
        out.append(line)
    return "\n".join(out), bad


def files():
    return sorted(glob.glob(os.path.join(ROOT, "soe2", "**", "*.py"), recursive=True))


def main():
    fix = "--fix" in sys.argv
    total = 0
    for path in files():
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        new, bad = scan(text, fix)
        total += len(bad)
        rel = os.path.relpath(path, ROOT)
        for no, what in bad if not fix else []:
            print(f"{rel}:{no}: {what}")
        if fix and new != text:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(new)
            print(f"fixed {len(bad):3} in {rel}")
    if not fix:
        print("OK - everything is on the design tokens" if not total else f"{total} off the tokens (--fix moves them)")
    return 1 if total and not fix else 0


if __name__ == "__main__":
    sys.exit(main())
