"""One name per feature (2.126.0, UX rule: "One name per feature (soe2/names.py). No synonyms.").

Checks that:
  * every page (soe2/modules/) is named as soe2/names.py's PAGES says, and every page name is in Title Case
  * no old name or synonym (names.OLD) is in the app's text - strings in soe2/ and stashofexile2.py (not comments
    or docstrings, which keep the history) - or in README.md / TOS.md
Left alone: names.py itself, whatsnew.py (the release notes are the history) and migrations.py.
Run: python tools/check_names.py   (exit 1 lists each place, with the name to use)."""
import ast
import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from check_removed import tokens   # noqa: E402

SKIP = {"names.py", "whatsnew.py", "migrations.py"}
DOCS = ("README.md", "TOS.md")


def load_names():
    spec = importlib.util.spec_from_file_location("names", os.path.join(ROOT, "soe2", "names.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def module_titles(N):
    """(file, key, title) for each page module, read from its class (key, title, ... = ...)."""
    consts = {"PAGE_CHECKS": N.PAGES["checks"], "PAGE_PC": N.PAGES["pricecheck"]}
    folder = os.path.join(ROOT, "soe2", "modules")
    out = []
    for f in sorted(os.listdir(folder)):
        if not f.endswith(".py") or f == "__init__.py":
            continue
        tree = ast.parse(open(os.path.join(folder, f), encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple):
                names = [t.id for t in node.targets[0].elts if isinstance(t, ast.Name)]
                if "key" in names and "title" in names and isinstance(node.value, ast.Tuple):
                    vals = [v.value if isinstance(v, ast.Constant) else consts.get(getattr(v, "id", ""), "?")
                            for v in node.value.elts]
                    d = dict(zip(names, vals))
                    out.append((f, d["key"], d["title"]))
    return out


def main():
    N = load_names()
    bad = []
    for f, key, title in module_titles(N):
        want = N.PAGES.get(key)
        if want is None:
            bad.append(f"soe2/modules/{f}: page '{key}' isn't in names.PAGES")
        elif title != want:
            bad.append(f"soe2/modules/{f}: titled {title!r}, names.PAGES says {want!r}")
    for key, title in N.PAGES.items():
        if not N.title_case(title):
            bad.append(f"soe2/names.py: page name {title!r} isn't in Title Case")
    for old, new in N.OLD.items():
        if old == new or new in N.OLD:
            bad.append(f"soe2/names.py: OLD {old!r} -> {new!r} (must lead to a name in use)")
    rx = [(re.compile(r"(?<![\w-])" + re.escape(old) + r"(?![\w-])"), old, new) for old, new in N.OLD.items()]
    files = [os.path.join(ROOT, "stashofexile2.py")] + sorted(
        os.path.join(ROOT, "soe2", d, f) for d in ("", "modules") for f in os.listdir(os.path.join(ROOT, "soe2", d))
        if f.endswith(".py"))
    for path in files:
        if os.path.basename(path) in SKIP:
            continue
        toks, _lines = tokens(path)
        for kind, text, ln in toks:
            if kind != "str":
                continue
            for r, old, new in rx:
                if r.search(text):
                    bad.append(f"{os.path.relpath(path, ROOT)}:{ln}: {old!r} - the name is {new!r}")
    for rel in DOCS:
        path = os.path.join(ROOT, rel)
        for ln, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
            for r, old, new in rx:
                if r.search(line):
                    bad.append(f"{rel}:{ln}: {old!r} - the name is {new!r}")
    for b in bad:
        print(b)
    print(f"check_names: {len(N.PAGES)} pages, {len(N.FEATURES)} features, {len(N.OLD)} old names - "
          + ("ok" if not bad else f"{len(bad)} to fix"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
