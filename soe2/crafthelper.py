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
leagues, so they live in one table, not in the page code.

Phase 3 (2.125.5):
  - The data pack, crafthelper.json (the kinds, the market letters, the counts), is shipped with the app and kept
    up to date from GitHub (one small public download, at most twice a day while the Craft Helper is open, nothing
    sent about you), so a new game patch's types and steps don't wait for an app update. Its "patch" says which game
    patch it was made for. The newest copy wins; KINDS is updated in place (other modules hold it).
  - Learned mod pairs: two mods that sell well TOGETHER on your own price checks' listings (this league), clearly
    above either mod alone - pairs(). They get one letter (no prices), and a checked item carrying a good pair
    counts it in its verdict."""
import json
import os
import statistics
import time

from . import buglog
from . import mods as M
from .config import APP_UA, APP_DIR, RESOURCE_DIR, P, SETTINGS, save_json

FILE = "crafthelper.json"
SCHEMA = 1
REPO = "tiwomm/StashOfExile2"
LIVE_URL = f"https://raw.githubusercontent.com/{REPO}/main/{FILE}"
LIVE_EVERY = 12 * 3600

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
PAIR_MIN_N = 6                         # listings with both mods before a pair says anything
PAIR_GAIN = 1.3                        # ... and together they must ask this much more than the better one alone

_BUILTIN = {"kinds": json.loads(json.dumps(KINDS)), "lift_tiers": [list(t) for t in LIFT_TIERS],
            "market_min_n": MARKET_MIN_N, "pair_min_n": PAIR_MIN_N, "pair_gain": PAIR_GAIN}
_PACK = {"key": None, "data": None}


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    return d if _valid(d) else None


def _valid(d):
    """A data pack the app can use: every kind with a label, its types and its steps."""
    if not isinstance(d, dict) or not isinstance(d.get("kinds"), dict):
        return False
    for k, v in d["kinds"].items():
        if k not in _BUILTIN["kinds"] or not isinstance(v, dict):
            return False
        if not isinstance(v.get("types", []), list) or not isinstance(v.get("flow", []), list):
            return False
        if any(not (isinstance(f, (list, tuple)) and len(f) == 2) for f in v.get("flow", [])):
            return False
    return True


def _newness(d):
    return d.get("schema", 1), d.get("revision", 0)


def pack():
    """-> the newest data pack (fetched, or shipped with the app)."""
    paths = (P(FILE), os.path.join(RESOURCE_DIR, FILE), os.path.join(APP_DIR, FILE))
    key = tuple((p, os.path.getmtime(p)) for p in paths if os.path.isfile(p))
    if _PACK["key"] == key and _PACK["data"] is not None:
        return _PACK["data"]
    best = None
    for p in paths:
        d = _read(p)
        if d and d.get("schema", 1) <= SCHEMA and (best is None or _newness(d) > _newness(best)):
            best = d
    best = best or dict(_BUILTIN, schema=SCHEMA, revision=0, patch="?")
    _PACK.update(key=key, data=best)
    _apply(best)
    return best


def _apply(d):
    """The pack's values into KINDS (in place - other modules hold it) and the market numbers."""
    global LIFT_TIERS, MARKET_MIN_N, PAIR_MIN_N, PAIR_GAIN
    kinds = {}
    for k, base in _BUILTIN["kinds"].items():
        v = dict(base)
        for f, val in ((d.get("kinds") or {}).get(k) or {}).items():
            v[f] = tuple(tuple(x) for x in val) if f == "flow" else tuple(val) if f == "types" else val
        if not isinstance(v["types"], tuple):
            v["types"] = tuple(v["types"])
        if not isinstance(v["flow"], tuple) or (v["flow"] and not isinstance(v["flow"][0], tuple)):
            v["flow"] = tuple(tuple(x) for x in v["flow"])
        kinds[k] = v
    KINDS.clear()
    KINDS.update(kinds)
    try:
        LIFT_TIERS = tuple((float(a), str(b)) for a, b in d.get("lift_tiers") or _BUILTIN["lift_tiers"])
        MARKET_MIN_N = int(d.get("market_min_n") or _BUILTIN["market_min_n"])
        PAIR_MIN_N = int(d.get("pair_min_n") or _BUILTIN["pair_min_n"])
        PAIR_GAIN = float(d.get("pair_gain") or _BUILTIN["pair_gain"])
    except (TypeError, ValueError):
        pass


def pack_line():
    """The data pack in one line, for the page."""
    d = pack()
    return f"Data pack: game patch {d.get('patch', '?')} · revision {d.get('revision', 0)}"


def fetch_live(get=None, force=False, now=None):
    """Check GitHub for a newer data pack. -> ("new", line) / ("same", line) / ("skip", "") / ("error", why).
    One small public download; nothing is sent about you."""
    now = now or time.time()
    c = SETTINGS.setdefault("crafthelper", {})
    if not force and now - float(c.get("checked", 0) or 0) < LIVE_EVERY:
        return "skip", ""
    if get is None:
        import requests
        get = requests.get
    try:
        r = get(LIVE_URL, headers={"User-Agent": APP_UA}, timeout=15)
        if r.status_code != 200:
            return "error", f"GitHub answered {r.status_code}."
        d = r.json()
    except Exception as e:
        return "error", f"Could not reach GitHub ({e.__class__.__name__})."
    c["checked"] = now
    if not _valid(d):
        return "error", "The data pack on GitHub could not be read."
    if d.get("schema", 1) > SCHEMA:
        return "error", "The newest data pack needs a newer version of the app - update it."
    if _newness(d) <= _newness(pack()):
        return "same", pack_line()
    save_json(FILE, d)
    _PACK["key"] = None
    pack()
    return "new", pack_line()


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


def verdict(kind, text, letters, pair_lines=()):
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
    for pl in pair_lines:                                # 2.125.5: learned pairs it carries
        why += f"; {pl}"
    return {"key": key, "mark": mark, "word": word, "tone": tone, "next": nxt, "why": why + "."}


# ---------------------------------------------------------------- 2.125.5: learned mod pairs
_PAIRS = {"key": None, "data": {}}


def pairs(kind, rows=None, now=None):
    """Two mods that sell well TOGETHER on your price checks' listings of this kind (this league) ->
    [{"a", "b" (stat ids), "letter", "lift", "gain", "n", "lo", "hi", "base_n"}], best first.
    lift = the middle ask of listings with both / the middle ask of that base's listings; gain = with both / with the
    better one alone. A pair counts with PAIR_MIN_N+ listings, a gain of PAIR_GAIN+ and a letter of B or better.
    Worked out per base, the pair's best showing kept. Cached for a minute."""
    if rows is None:
        now = now or time.time()
        from .market import MARKET
        key = (kind, MARKET.cur(), int(now // 60))
        if _PAIRS["key"] == key:
            return _PAIRS["data"]
        rows = MARKET.listing_rows()
    else:
        key = None
    by_base = {}
    for base, price, sids in rows:
        if _is_kind(kind, base) and price > 0:
            by_base.setdefault(base, []).append((price, sids))
    best = {}
    for base, items in by_base.items():
        if len(items) < PAIR_MIN_N * 2:
            continue
        mid = statistics.median(p for p, _s in items)
        if mid <= 0:
            continue
        one, two = {}, {}
        for price, sids in items:
            ss = sorted(sids)
            for s_ in ss:
                one.setdefault(s_, []).append(price)
            for i in range(len(ss)):
                for j in range(i + 1, len(ss)):
                    two.setdefault((ss[i], ss[j]), []).append(price)
        for (a, b), ps in two.items():
            if len(ps) < PAIR_MIN_N:
                continue
            med = statistics.median(ps)
            alone = max(statistics.median(one[a]), statistics.median(one[b]))
            gain = med / max(alone, 1e-9)
            lift = med / mid
            letter = _letter(lift)
            if gain < PAIR_GAIN or _rank(letter) > _rank("B"):
                continue
            k = (a, b)
            if k not in best or lift > best[k]["lift"]:
                best[k] = {"a": a, "b": b, "letter": letter, "lift": round(lift, 2), "gain": round(gain, 2),
                           "n": len(ps), "base_n": len(items), "base": type_of(kind, base) or kind}
    out = sorted(best.values(), key=lambda r: (_rank(r["letter"]), -r["lift"], -r["n"]))
    if key is not None:
        _PAIRS.update(key=key, data=out)
    return out


def pair_text(kind, pr, names=None):
    """A pair -> "mod one + mod two" in the regex data's words (the stat id when its words aren't known)."""
    names = names if names is not None else sid_names(kind)
    return f"{names.get(pr['a'], pr['a'])} + {names.get(pr['b'], pr['b'])}"


def pair_how(pr):
    """How a pair's letter was worked out, in one line (no prices)."""
    return (f"{pr['n']} of {pr['base_n']} listings ({pr['base']}) have both: they ask {pr['lift']:g}x that kind's "
            f"middle price, {pr['gain']:g}x the better mod alone. Rated {pr['letter']} from your price checks, "
            "this league.")


def sid_names(kind):
    """Stat id -> the mod's words, for this kind's mods."""
    from . import regex as R
    out = {}
    try:
        R.load()
        for m in R.mods(kind):
            sid = _sid(m["line"])
            if sid and sid not in out:
                out[sid] = m["text"]
    except Exception:
        buglog.caught()
    return out


def item_pairs(kind, mod_ids, plist=None):
    """The learned pairs a checked item carries (its regex-data mod ids) -> [pair], best first."""
    from . import regex as R
    by = R.by_id(kind)
    sids = {_sid(by[i]["line"]) for i in mod_ids if i in by}
    sids.discard(None)
    plist = plist if plist is not None else pairs(kind)
    return [p for p in plist if p["a"] in sids and p["b"] in sids]


try:                                                     # the data pack's values from the start
    pack()
except Exception:
    buglog.caught()

