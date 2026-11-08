"""Craft Helper (2.123.0, phase 1 of the overhaul: tablets and jewels only - other items have too many mods to advise
on reliably).

Every mod gets one S-F letter, and says where it came from - nothing else (feedback: no prices - they move too fast and
only a live search, your own price check, can say what an item is worth; and no stash search - the game's search box
holds 250 characters, so it could never cover every keeper):
  1. you      - your Mod Book rating (S-D, or F = ignore)
  2. players  - the community board's votes (3+), High -> A, Ignore -> F, mixed -> C
  3. market   - how far tablets / jewels WITH the mod sell above that kind's middle price, across many listings
                (the board's pooled prices, per base and league; else your own price checks). It only picks the
                letter; no price is shown. A mod that makes no difference is D, whatever it rides on
                (feedback: "monsters have #% increased effectiveness" showed 2 div - filler on good tablets).
  4. default  - the app's shipped defaults (default_rules.json), High -> A, Ignore -> F
  5. none     - not enough to go on: "-".

Phase 2 (2.123.4): verdict() turns a copied item into one of four words - Worth pricing, Craft on, Reforge, Vendor -
with the next step, the mods it found with their letters, and why. It never searches by itself: "Price it" runs your
own price check.

KINDS is the per-kind data (types, the craft steps, the words) - the game will change these at 1.0 and between
leagues, so they live in one table, not in the page code."""
from . import mods as M

KINDS = {
    "tablet": {
        "label": "Tablets", "one": "tablet", "item_class": "Tablet",
        "types": ("All", "Breach", "Delirium", "Ritual", "Expedition", "Abyss", "Overseer", "Temple"),
        "flow": (("White tablet", "Orb of Transmutation, then Orb of Augmentation: 2 mods."),
                 ("2 bad mods", "Orb of Alchemy."),
                 ("2 good mods", "Regal Orb, then Exalted Orb."),
                 ("4 junk mods", "Don't sell it - keep it to reforge."),
                 ("Good mods", "Worth pricing: press your price check key on it, then list it.")),
    },
    "jewel": {
        "label": "Jewels", "one": "jewel", "item_class": "Jewel",
        "types": ("All", "Ruby", "Emerald", "Sapphire", "Time-Lost"),
        "flow": (("White jewel", "Orb of Transmutation, then Orb of Augmentation: 2 mods."),
                 ("2 good mods", "Regal Orb, then Exalted Orbs to fill it."),
                 ("0-1 good mods", "Not worth more currency: start over on another jewel."),
                 ("Rare, 1-2 good mods", "Chaos Orb swaps a mod - stop when it's down to junk."),
                 ("3+ good mods", "Worth pricing: press your price check key on it, then list it.")),
    },
}
GOOD = ("S", "A")                      # what counts as a good mod in the advice
SOURCE_WORD = {"you": "you", "players": "players", "market": "market", "default": "the app's default",
               "none": "not enough data yet"}
LIFT_TIERS = ((3.0, "S"), (2.0, "A"), (1.5, "B"), (1.2, "C"))     # market: x the kind's middle price -> letter
MARKET_MIN_N = 12


def type_of(kind, base):
    """A base name -> its type in KINDS[kind]["types"] ("Ritual Precursor Tablet" -> Ritual), or "" (any)."""
    b = str(base or "")
    if kind == "jewel" and "Time-Lost" in b:
        return "Time-Lost"
    return next((t for t in KINDS[kind]["types"][1:] if t != "Time-Lost" and t.lower() in b.lower()), "")


def _players(key):
    """The board's votes for a Mod Book key -> (letter, votes) or None (fewer than 3)."""
    from . import communitymods as CM
    for row in CM.cached().get("ratings", []):
        try:
            k, high, normal, ignore = row
        except (TypeError, ValueError):
            continue
        if k != key:
            continue
        high, normal, ignore = high or 0, normal or 0, ignore or 0
        total = high + normal + ignore
        if total < CM.VOTE_MIN:
            return None
        if high / total >= CM.VOTE_SHARE:
            return "A", total
        if ignore / total >= CM.VOTE_SHARE:
            return "F", total
        return "C", total
    return None


def _is_kind(kind, base):
    b = str(base or "")
    if kind == "tablet":
        return "Tablet" in b
    return any(t in b for t in ("Ruby", "Emerald", "Sapphire", "Diamond"))


def _letter(lift):
    return next((t for floor, t in LIFT_TIERS if lift >= floor), "D")


def _market(kind, sid, ttype, pooled):
    """The board's pooled prices: the best showing of this mod on bases of the type -> (letter, listings) or None."""
    if not sid:
        return None
    best = None
    for (base, s_), st in pooled.items():
        if s_ != sid or not _is_kind(kind, base):
            continue
        if ttype not in ("All", "") and type_of(kind, base) not in (ttype, ""):
            continue
        lift, n = st.get("lift"), st.get("n", 0)
        if lift is None or n < MARKET_MIN_N:
            continue
        if best is None or lift > best[0]:
            best = (lift, n)
    return (_letter(best[0]), best[1]) if best else None


def rating(kind, mod, ttype="All", pooled=None):
    """-> (letter or "-", source key, count) for one regex-data mod (its lines) - the most valuable of its lines."""
    pooled = pooled if pooled is not None else _pooled()
    best = None
    for line in mod.get("lines") or [mod["line"]]:
        k = M.rule_key(kind, M.norm(line))
        if k in M.RULES or k in M.TIERS:
            r = ("F" if M.impact_key(k) == "ignore" else (M.tier_key(k) or "C"), "you", 0)
        else:
            p = _players(k)
            if p:
                r = (p[0], "players", p[1])
            else:
                mk = _market(kind, mod.get("sid") or _sid(line), ttype, pooled)
                if not mk:                                  # your own price checks (every base of the kind)
                    li = M.learned_info(k)
                    if li and li.get("lift") is not None and (li.get("n") or 0) >= MARKET_MIN_N:
                        mk = (_letter(li["lift"]), li["n"])
                if mk:
                    r = (mk[0], "market", mk[1])
                elif k in M.DEFAULT_RULES:                  # the app's shipped defaults (default_rules.json)
                    r = ({"high": "A", "ignore": "F"}.get(M.DEFAULT_RULES[k], "C"), "default", 0)
                else:
                    r = ("-", "none", 0)
        if best is None or _rank(r[0]) < _rank(best[0]):
            best = r
    return best or ("-", "none", 0)


def _rank(letter):
    return {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4, "F": 6}.get(letter, 5)


def _sid(line):
    from .moneymakers import stat_id
    try:
        return stat_id(line)
    except Exception:
        return None


def _pooled():
    from . import communitymods as CM
    try:
        return CM.pooled()
    except Exception:
        return {}


def source_text(src, n):
    w = SOURCE_WORD.get(src, src)
    if src == "players":
        return f"{w} · {n} votes"
    if src == "market":
        return f"{w} · {n} listings"
    return w


def _line_rx(line):
    import re
    body = re.escape(line).replace(r"\#", "#").replace("#", r"[+-]?\d+(?:\.\d+)?(?:\([\d.]+-[\d.]+\))?")
    return re.compile(r"^\s*" + body + r"\s*(?:\((?:desecrated|fractured|crafted|rune|enchant|implicit)\))?\s*$", re.I)


def item_mods(kind, text):
    """The mods of this kind an item carries -> [mod id], matched on whole lines (a mod with two lines needs both);
    one wording counted once (a line can be a mod of several jewel types)."""
    from . import regex as R
    lines = [l.strip() for l in str(text or "").splitlines() if l.strip() and not l.startswith(("Item Class", "Rarity"))]
    out, seen = [], set()
    for m in R.mods(kind):
        want = m.get("lines") or [m["line"]]
        if all(any(_line_rx(w).match(l) for l in lines) for w in want) and m["text"] not in seen:
            seen.add(m["text"])
            out.append(m["id"])
    # a two-line mod whose lines are each a mod of their own as well: count the single mods (one line, one mod)
    by = R.by_id(kind)
    singles = {by[i]["line"] for i in out if len(by[i].get("lines") or [1]) == 1}
    return [i for i in out if len(by[i].get("lines") or [1]) == 1 or not set(by[i]["lines"]) <= singles]


def advice(kind, rarity, n_mods, n_good):
    """What to do next with a tablet or jewel. "Good" = rated S or A."""
    if kind == "tablet":
        from .moneymakers import tablet_advice
        return tablet_advice(rarity, n_mods, n_good)
    rarity = (rarity or "").capitalize()
    if rarity == "Normal" or (not rarity and n_mods == 0):
        return "White jewel: Orb of Transmutation, then Orb of Augmentation."
    if rarity == "Magic":
        if n_mods < 2:
            return "One mod so far: Orb of Augmentation for the second."
        if n_good >= 2:
            return "Both mods are good (S or A): Regal Orb, then Exalted Orbs to fill it."
        if n_good == 1:
            return ("One good mod: your call - Regal + Exalt if that mod is rated S (see its rating below), "
                    "otherwise start over on another jewel.")
        return "No good mods: not worth more currency - start over on another jewel."
    if rarity == "Rare":
        if n_good >= 3:
            return f"{n_good} good mods: worth pricing - press your price check key on it."
        if n_mods < 4:
            return f"{n_good} good mod{'s' if n_good != 1 else ''}: Exalted Orb to fill it, then check again."
        if n_good:
            return f"{n_good} good mod{'s' if n_good != 1 else ''}: Chaos Orb swaps a mod - stop when it's down to junk."
        return "No good mods: vendor it."
    return f"Copy a {KINDS[kind]['one']} in game (Ctrl+C), then press Check."


# 2.123.4 (Craft Helper phase 2): one word for what to do with the item - each with a mark, so it's never color alone
VERDICTS = {
    "price": ("✓", "Worth pricing", "green"),
    "craft": ("↻", "Craft on", "good"),
    "reforge": ("⟲", "Reforge", "good"),
    "vendor": ("✕", "Vendor", "red"),
}


def verdict(kind, text, letters):
    """A copied tablet / jewel -> {"key", "mark", "word", "tone", "next", "why"}. letters = the S-F letter of each mod
    found on it ("-" = no rating yet). Good = S or A. Corrupted items can't be crafted on: price or vendor."""
    from .moneymakers import tablet_rarity
    rarity = tablet_rarity(text)
    n, good = len(letters), sum(1 for l in letters if l in GOOD)
    best = min(letters, key=_rank) if letters else "-"
    corrupted = any(l.strip() == "Corrupted" for l in str(text or "").splitlines())
    one = KINDS[kind]["one"]
    nxt = advice(kind, rarity, n, good)
    if corrupted:
        key = "price" if good else "vendor"
        nxt = ("Corrupted - it can't be crafted on. " +
               ("Press your price check key on it." if good else "Nothing on it is rated S or A."))
    elif rarity == "Normal" or (not rarity and n == 0):
        key = "craft"
    elif rarity == "Magic":
        if n < 2 or good >= 2:
            key = "craft"
        elif good == 1:
            key = "craft" if best == "S" else ("reforge" if kind == "tablet" else "vendor")
            nxt = (f"One good mod, rated {best}: " +
                   ("Regal Orb, then Exalted Orb." if best == "S" else
                    "only an S mod is worth a Regal - " +
                    ("treat it as 2 bad mods: Orb of Alchemy." if kind == "tablet" else "start over on another jewel.")))
        else:
            key = "reforge" if kind == "tablet" else "vendor"
    elif rarity == "Rare":
        full = 4
        if (kind == "jewel" and good >= 3) or (kind == "tablet" and good and n >= full):
            key = "price"
        elif good or n < full:
            key = "craft"
        else:
            key = "reforge" if kind == "tablet" else "vendor"
    else:
        key = "craft"
    mark, word, tone = VERDICTS[key]
    unrated = sum(1 for l in letters if l == "-")
    why = (f"{good} of {n} mod{'s' if n != 1 else ''} rated S or A" if n else f"No mods yet - a white {one}")
    if unrated:
        why += f"; {unrated} not rated yet (right-click it in the list to rate it)"
    return {"key": key, "mark": mark, "word": word, "tone": tone, "next": nxt, "why": why + "."}
