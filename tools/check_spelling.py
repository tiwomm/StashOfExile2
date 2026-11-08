"""US spelling in everything a person reads (2.123.5, feedback: "we don't use the UK spelling of stuff").

Looks at the app's text - strings, comments and docstrings in soe2/ and stashofexile2.py, and the .md docs - for UK
spellings (colour, behaviour, grey, centre, cancelled, ...). Left alone: names in the code, lowercase data keys and
file names, and the game's own words the app reads or searches for (Armour, favours, Honour, Rumours, Defences ...),
which stay as the game writes them. A line that must quote the game can end with "# game text".
Run: python tools/check_spelling.py   (exit 1 lists each line)."""
import io
import os
import re
import sys
import tokenize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UK = (r"colour|behaviour|neighbour|flavour|organis(?:e|ed|es|ing|ation)|recognis(?:e|ed|es|ing)|realis(?:e|ed|es|ing)\b|"
      r"customis(?:e|ed|es|ing|ation)|optimis(?:e|ed|es|ing|ation)\b|prioritis|summaris|minimis(?:e|ed|es|ing)|"
      r"maximis(?:e|ed|es|ing)|categoris|normalis|initialis|personalis|synchronis|visualis|authoris|utilis|apologis|"
      r"analys(?:e|ed|ing)\b|centre|centred|licence|cancell(?:ed|ing)|travell(?:ed|ing|er)|labell(?:ed|ing)|"
      r"modell(?:ed|ing)|levell(?:ed|ing)|catalogue|offence|judgement|whilst|grey|programme\b|learnt\b|spelt\b|"
      r"burnt\b|fibre|jewellery")
RX = re.compile(r"(?<![\w.])(" + UK + r")(?!\w*_)", re.I)     # (not inside a name: flavour_sections)
GAME_OK = re.compile(r"#\s*game text")


def py_hits(path):
    src = open(path, encoding="utf-8").read()
    lines = src.splitlines()
    out = []
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        name = tokenize.tok_name[t.type]
        if name not in ("COMMENT", "STRING", "FSTRING_MIDDLE"):
            continue
        body = t.string
        if name != "COMMENT":
            inner = re.sub(r"^[rbfuRBFU]*['\"]{1,3}|['\"]{1,3}$", "", body)
            if re.fullmatch(r"[a-z_0-9.]*", inner):
                continue
        for m in RX.finditer(body):
            ln = t.start[0] + body[:m.start()].count("\n")
            if not GAME_OK.search(lines[ln - 1]):
                out.append((ln, m.group(1)))
    return out


def md_hits(path):
    out = []
    for i, line in enumerate(open(path, encoding="utf-8"), 1):
        plain = re.sub(r"`[^`]*`|\"[^\"\n]*\"|https?://\S+", "", line)      # code, quotes (feedback, game text), links
        out += [(i, m.group(1)) for m in RX.finditer(plain)]
    return out


def main():
    files = [os.path.join(ROOT, "stashofexile2.py")]
    for top in ("soe2", "tools"):
        for d, _s, fs in os.walk(os.path.join(ROOT, top)):
            files += [os.path.join(d, f) for f in fs if f.endswith(".py")]
    for d, _s, fs in os.walk(ROOT):
        if any(x in d for x in (".git", "node_modules", ".wrangler")):
            continue
        files += [os.path.join(d, f) for f in fs if f.endswith(".md")]
    bad = []
    for f in sorted(set(files)):
        if os.path.basename(f) == "check_spelling.py" or "THIRD_PARTY" in f:
            continue
        for ln, word in (py_hits(f) if f.endswith(".py") else md_hits(f)):
            bad.append(f"{os.path.relpath(f, ROOT)}:{ln}: {word}")
    if bad:
        print("UK spelling (use US):")
        print("\n".join(bad))
        return 1
    print(f"US spelling: ok ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
