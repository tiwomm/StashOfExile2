"""2.96.0: Help rate mods - your ratings tune your own price checks at once, and (with Community data sharing on) they
are your vote in the community's ratings. (2.119.0: no rep - it was removed in 2.118.0.)

  * ▲ / ▼ beside each mod on Price Checks: "did this mod matter for the price?" ▲ = High, ▼ = Ignore, again = clear.
    Gear has its own rules per item class ("gear:helmet:# to maximum life"), so a helmet's ▲ doesn't touch rings.
  * Rate mods: one mod at a time, S / A / B / C / D or F (ignore), from one rule set (Tablets, Jewels, Waystones, Relics,
    or a gear class you've price checked). S / A count as High, B / C / D as Normal (the tier says what's left out first).
  * The ask: once, after you've priced enough items; Not now asks again once, at random 3-7 days later; No thanks
    never asks again. Rate Mods is always there (2.120.0: its own page, Price Checks ↳ Rate Mods).
  * Bulk Pricing floor: an item whose every searched mod sells for under your floor (1 div by default, per rule set)
    in the Mod book's own data - none rated High - isn't searched; with thin data it's marked "check by hand".
GGG ToS: your own settings and the app's own data; nothing touches the game, nothing extra is fetched."""
import random
import time

from .config import SETTINGS, save_json
from .mods import (IMPACTS, RULES, TIER_ORDER, TIERS, auto_impact, impact_key, norm, rule_key)

GRADES = TIER_ORDER + ("ignore",)
ASK_AFTER = 25                      # items priced before the first ask
SNOOZE_DAYS = (3, 7)
FLOOR_DEFAULT = 1.0                 # divines
SURE_N = 5                          # listings behind a mod's median before the floor is sure
MIN_N = 3
FLOOR_SETS = ("tablet", "jewel", "relic")


def set_of(rec):
    """The rule set an item's mods belong to: tablet / jewel / waystone / relic / gear:<class>, or None."""
    it = rec.get("item") or {}
    if it.get("waystone"):
        return "waystone"
    cls = str(it.get("class") or "")
    if cls.lower().startswith("relic"):
        return "relic"
    if it.get("gear") and it.get("rarity") == "Unique" and it.get("name"):     # 2.99.0: a unique has its own rules
        return "unique:" + str(it["name"]).strip().lower()
    if it.get("gear"):
        return "gear:" + str(it.get("gclass") or cls or "gear").lower()
    base = str(it.get("base") or "")
    return "tablet" if cls in ("Tablet", "Tablets") or base.endswith(" Tablet") else "jewel"


def key_for(rec, m):
    """The rule Rate ▾ on this mod sets, or None (totals, pseudo totals and lines with no trade id can't be rated)."""
    if m.get("kind") in ("Total", "Rune") or m.get("group") in ("total", "pseudo") or not m.get("text"):
        return None                     # (2.97.1: a socketed rune isn't rated - it shares an affix's wording)
    s = set_of(rec)
    k = norm(m["text"])
    if s is None:
        return None
    if s.startswith(("gear:", "unique:")):            # 2.99.0: no leading "+" (the Mod book's Gear / Unique rules)
        from .gearbook import gkey
        return f"{s}:{gkey(m['text'])}"
    return rule_key(s, k)


def thumb(key):
    """"up" (you rated it High), "down" (Ignore) or None - your own rule only, not the built-in default."""
    v = RULES.get(key)
    return "up" if v == "high" else "down" if v == "ignore" else None


def apply(keys, grade):
    """Rate these rule keys: S..D (S / A = High, B / C / D = Normal, with that tier), "ignore", "up", "down", or None
    (clear yours). -> the keys changed."""
    keys = [k for k in keys if k]
    for k in keys:
        if grade in (None, "clear"):
            RULES.pop(k, None)
            TIERS.pop(k, None)
            continue
        imp = {"up": "high", "down": "ignore", "ignore": "ignore"}.get(grade) or ("high" if grade in ("S", "A") else "normal")
        if imp == auto_impact(k) and grade not in TIER_ORDER + ("ignore",):   # 2.97.0: an F you gave stays yours
            RULES.pop(k, None)
        else:
            RULES[k] = imp
        if grade in TIER_ORDER:
            TIERS[k] = grade
        elif imp == "ignore":
            TIERS.pop(k, None)
    save_json("mod_rules.json", RULES)
    save_json("mod_tiers.json", TIERS)
    rated = SETTINGS.setdefault("rated_n", 0)
    SETTINGS["rated_n"] = rated + len(keys)
    save_json("settings.json", SETTINGS)
    return keys


def queue(set_name, gear_mods=None):
    """Mods to rate in one set, the ones you haven't rated first: [(keys, text)]."""
    out = []
    if set_name.startswith(("gear:", "unique:")):
        seen = set()
        for k, text in gear_mods or []:
            if k not in seen:
                seen.add(k)
                out.append(([k], text))
    else:
        from . import regex as R
        for m in R.mods(set_name):
            lines = m.get("lines") or [m["line"]]
            keys = [rule_key(set_name, norm(line)) for line in lines]
            out.append((keys, " / ".join(line[:1].upper() + line[1:] for line in lines)))
    mine = lambda keys: any(k in RULES or k in TIERS for k in keys)      # noqa: E731
    return [x for x in out if not mine(x[0])] + [x for x in out if mine(x[0])]


def current(keys):
    """Your grade for these keys: S..D, "ignore", or None."""
    k = keys[0]
    if impact_key(k) == "ignore" and k in RULES:
        return "ignore"
    t = TIERS.get(k)
    return t if t in TIER_ORDER else None


# ---------------------------------------------------------------- the ask
def ask_state():
    return SETTINGS.setdefault("rate_ask", {"state": "new", "at": 0})


def should_ask(priced):
    """Ask now? (new and enough items priced, or a snooze that's over and hasn't asked again yet)."""
    a = ask_state()
    if a.get("state") == "new":
        return priced >= ASK_AFTER
    if a.get("state") == "snoozed":
        return time.time() >= a.get("at", 0)
    return False


def answer(what, rng=random):
    """"yes" / "not_now" / "no". Not now once: again at random 3-7 days later; not now again, or no: never."""
    a = ask_state()
    if what == "not_now" and a.get("state") == "new":
        a.update(state="snoozed", at=time.time() + rng.uniform(*SNOOZE_DAYS) * 86400)
    elif what == "yes":
        a.update(state="yes", at=0)
    else:
        a.update(state="never", at=0)
    save_json("settings.json", SETTINGS)
    return a["state"]


# ---------------------------------------------------------------- Bulk Pricing floor
def floor_cfg():
    c = SETTINGS.setdefault("floor", {})
    c.setdefault("on", True)
    for s in FLOOR_SETS:
        c.setdefault(s, FLOOR_DEFAULT)
    return c


def floor_check(rec, searchable, median_n):
    """searchable: [(mod, impact)]; median_n(base, sid) -> (median div, listings) or (None, 0).
    -> ("skip", why) when the Mod book is sure the item is under the floor, ("hand", why) when its data says so but is
    thin, else None (search it)."""
    c = floor_cfg()
    s = set_of(rec)
    if not c.get("on") or s not in FLOOR_SETS or not searchable or rec.get("src") in ("pc", "fav"):
        return None
    floor = float(c.get(s) or FLOOR_DEFAULT)
    if floor <= 0:
        return None
    base = (rec.get("item") or {}).get("base")
    thin, top = False, 0.0
    for m, imp in searchable:
        k = rule_key(s, norm(m["text"]))
        if imp == "high" or TIERS.get(k) in ("S", "A"):
            return None                                # a mod you rate High: always searched
        med, n = median_n(base, m["sid"])
        if med is None or n < MIN_N:
            return None                                # nothing known about it: search
        if med >= floor:
            return None
        thin = thin or n < SURE_N
        top = max(top, med)
    why = f"every mod sells for under {floor:g} div (the most: {top:.2f} div) in the Mod Book"
    return ("hand", why + ", from few listings") if thin else ("skip", why)


def valid_grade(g):
    return g in GRADES or g in ("up", "down", None, "clear") or g in IMPACTS
