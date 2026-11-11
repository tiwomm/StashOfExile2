"""A removed feature leaves nothing behind (2.126.0, UX rule: "Removing a feature: run tools/check_removed.py; clean
code, docs, tests, settings").

REMOVED below lists every feature taken out of the app: the words a person read for it and the names the code used
(functions, variables, setting keys). The check looks for them in:
  * the app's text - strings in soe2/ and stashofexile2.py (not comments or docstrings, which keep the history)
  * the app's code - names and setting keys (a line that only clears an old key - .pop( / del - is fine)
  * the docs - README.md, TOS.md and the folders' README.md files (ROADMAP.md is the history and is left alone)
  * the tests, with --tests DIR (the tests in DIR/runall.sh): a test may check a feature is gone ("not hasattr",
    "not in", "gone"), not use it; a line that needs an old name (a migration's test data) says "removed" in a comment
Left alone: migrations.py (it clears the old settings) and whatsnew.py (the release notes are the history).

Removing a feature: add a line to REMOVED (version, what it was, its words, its names), then run this.
A line marked pending=True is a known leftover still to clear: it is listed as a warning and doesn't fail the run.
Run: python tools/check_removed.py [--tests DIR]   (exit 1 lists each place)."""
import io
import os
import re
import sys
import tokenize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"migrations.py", "whatsnew.py", "names.py"}      # (names.py lists old names on purpose)
DOCS = ("README.md", "TOS.md", "linux/README.md", "themes/README.md", "strats/README.md")

# (version, what it was, words a person read, names in the code / settings keys[, pending])
REMOVED = [
    ("2.132.4", "the Ritual Identifier as a helper of its own (its Helpers row, Quick settings chip, BETA feature) - "
                "it's a Ritual helper option now", ("Ritual Identifier (BETA)",), ("ritid_row", "ritid_set", "al_ritid")),
    ("2.131.2", "League Plan's Map supplies (refill every N maps / minutes, its pokes) - Top Up Reminders count the "
                "inventory instead; its list moves there once",
     ("Map supply pokes", "ADD A SUPPLY", "REFILL YOUR MAP SUPPLIES", "Refill every"),
     ("add_supply", "remove_supply", "set_supply", "supplies_due", "supply_used", "SUPPLY_RULES", "SUPPLY_PRESETS",
      "USED_UP", "_gp_supplies", "_gp_sup_rows", "gp_sup_on", "gp_add_supply", "OMEN_USED")),
    ("2.131.0", "the campaign's 4th route (your last run's zone order) - Full, Speedrun and Rush (carry) stay",
     ("My Own",), ()),
    ("2.131.0", "the single Show beta features switch (Features has a Beta cluster); the quick start's sharing page "
                "(the Feature Picker asks)", ("Show beta features (marked BETA)", "Share with the community?"),
     ("on_labs", "labs_var", "set_labs", "SHARE_PAGE", "qs_share_row")),
    ("2.129.2", "Trade whispers' After the campaign option (on is on)", ("After the campaign",
     "Keep on after the campaign"), ("al_wafter", "ww_after_changed", "in_campaign")),
    ("2.11.0", "Recorder", ("Ritual Capture",), ()),
    ("2.31.0", "Lag finder; the toolbar's 'Ctrl+Alt+C only' box", ("Lag finder",), ()),
    ("2.92.0", "Arbitrage (Exchange Helper's flip check stays)", ("Arbitrage",), ()),
    ("2.98.3", "One-key copy and Other ways of copying", ("One-key copy", "Other ways of copying"),
     ("quick_copy_key", "hotkey_only", "any_copy_var", "quick_copy_btn")),
    ("2.68.1", "The notes key (Notes is part of the overlay)", ("Notes key",), ("notes_key",)),
    ("2.118.0", "Community rep", ("Thank someone with rep",), ("rep_give", "rep_btn")),
    ("2.119.0", "Feature tips; the 'only while the game is in front' switch", ("Feature tips",), ("game_only_var",)),
    ("2.125.5", "Skip cheap items; Valuable mods amount; Card over the game", ("Skip cheap items", "Card over the game"),
     ("floor_var", "good_div_var")),
    ("2.125.6", "Mod Book re-check rows and Bulk Pricing shortcuts",
     ("How searches are made", "Re-check a learned mod after", "Learn new mods in the background",
      "Skip a search the Mod Book already agrees on"),
     ("memory_shortcut", "model_shortcut")),
    ("2.106.0", "Wealth's public stash tabs (Scan stash replaces them)", ("Sync stash tabs",), ("w_sync_btn",), True),
]
ABSENT = re.compile(r"\bnot\b|\bgone\b|\bremoved\b|\bno longer\b|\.pop\(|\bdel\b|None\)", re.I)


def tokens(path):
    """(kind, text, line) for the strings that aren't docstrings, and the names."""
    src = open(path, encoding="utf-8").read()
    out, prev = [], "NEWLINE"
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    for i, t in enumerate(toks):
        name = tokenize.tok_name[t.type]
        if name == "STRING":
            nxt = next((tokenize.tok_name[x.type] for x in toks[i + 1:] if tokenize.tok_name[x.type] != "NL"), "")
            if not (prev in ("NEWLINE", "INDENT", "DEDENT") and nxt == "NEWLINE"):      # (a docstring)
                out.append(("str", t.string, t.start[0]))
        elif name == "FSTRING_MIDDLE":
            out.append(("str", t.string, t.start[0]))
        elif name == "NAME":
            out.append(("name", t.string, t.start[0]))
        if name not in ("NL", "COMMENT"):
            prev = name
    return out, src.splitlines()


def word_rx(w):
    return re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)")         # (as the label read: "a card over the game" is fine)


def check_code(found):
    files = [os.path.join(ROOT, "stashofexile2.py")] + sorted(
        os.path.join(ROOT, "soe2", f) for f in os.listdir(os.path.join(ROOT, "soe2")) if f.endswith(".py"))
    for path in files:
        if os.path.basename(path) in SKIP:
            continue
        toks, lines = tokens(path)
        for ent in REMOVED:
            words, names = [word_rx(w) for w in ent[2]], set(ent[3])
            for kind, text, ln in toks:
                line = lines[ln - 1]
                if kind == "str":
                    inner = re.sub(r"^[rbfuRBFU]*['\"]{1,3}|['\"]{1,3}$", "", text)
                    if inner in names and not ABSENT.search(line):
                        found.append((ent, path, ln, f"setting key {inner!r}"))
                    for rx in words:
                        if rx.search(text):
                            found.append((ent, path, ln, f"text {rx.search(text).group(0)!r}"))
                elif text in names and not ABSENT.search(line):
                    found.append((ent, path, ln, f"name {text}"))


def check_docs(found):
    for rel in DOCS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        for ln, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
            for ent in REMOVED:
                for w in ent[2]:
                    if word_rx(w).search(line) and not ABSENT.search(line):
                        found.append((ent, path, ln, f"doc {w!r}"))


def check_tests(found, folder):
    run = os.path.join(folder, "runall.sh")
    names = sorted(set(re.findall(r"\b(test_\w+)", open(run).read()))) if os.path.exists(run) else []
    for n in names:
        path = os.path.join(folder, n + ".py")
        if not os.path.exists(path):
            continue
        for ln, line in enumerate(open(path, encoding="utf-8", errors="ignore").read().splitlines(), 1):
            if ABSENT.search(line) or line.lstrip().startswith("#"):
                continue
            for ent in REMOVED:
                for nm in ent[3]:
                    if re.search(r"(?<!\w)" + re.escape(nm) + r"(?!\w)", line):
                        found.append((ent, path, ln, f"test uses {nm}"))


def main(argv):
    found = []
    check_code(found)
    check_docs(found)
    if "--tests" in argv:
        check_tests(found, argv[argv.index("--tests") + 1])
    bad = [f for f in found if not (len(f[0]) > 4 and f[0][4])]
    warn = [f for f in found if f not in bad]
    for ent, path, ln, what in warn:
        print(f"warning (pending, {ent[0]} {ent[1]}): {os.path.relpath(path, ROOT)}:{ln}: {what}")
    for ent, path, ln, what in bad:
        print(f"{os.path.relpath(path, ROOT)}:{ln}: {what} - removed in {ent[0]} ({ent[1]})")
    print(f"check_removed: {len(REMOVED)} removed features, {len(bad)} leftovers" + (f", {len(warn)} pending" if warn else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
