"""Confidence scores and price formatting / parsing.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import re
from .util import _amt, _num
from .rates import RATES


def confidence(n_best, loosened, any_roll, ratio, unverifiable, dropped, age_h, conflict, skipped=()):
    """-> (High / Medium / Low, [reasons]).  Starts at 100 and loses points for anything that makes the price shakier."""
    score, why = 100, []
    if n_best <= 1:
        score -= 40
        why.append("only 1 listing")
    elif n_best == 2:
        score -= 25
        why.append("only 2 listings")
    elif n_best < 5:
        score -= 15
        why.append(f"only {n_best} listings")
    if any_roll:
        score -= 35
        why.append("searched with ANY roll (nothing at your rolls)")
    elif loosened:
        score -= 15
        why.append("averaged from looser searches (the exact search found too few)")
    if ratio is not None and ratio >= 5:
        score -= 25
        why.append(f"listing prices {ratio:.0f}x apart")
    elif ratio is not None and ratio >= 2:
        score -= 10
        why.append(f"listing prices {ratio:.1f}x apart")
    if unverifiable:
        score -= 10
        why.append("couldn't check the listings' mods")
    if dropped:
        score -= 5
        why.append(f"{dropped} listing(s) dropped: they lacked a searched mod")
    if age_h is not None and age_h > 48:
        score -= 10
        why.append("listings are old")
    elif age_h is not None and age_h > 24:
        score -= 5
    if skipped:
        score -= 10
        why.append("listings priced in " + ", ".join(skipped) + " were left out (no exchange rate known)")
    if conflict:
        score -= 30
        why.append("earlier searches found higher prices for these mods")
    return ("High" if score >= 85 else "Medium" if score >= 55 else "Low"), why


PRICE_UNITS = [("auto", "Auto (div / chaos / ex)"), ("divine", "Divine Orbs"), ("exalted", "Exalted Orbs"),
               ("chaos", "Chaos Orbs"), ("vaal", "Vaal Orbs")]
UNIT_NAMES = {"divine": "div", "exalted": "ex", "chaos": "chaos", "vaal": "vaal"}


def price_unit():
    """2.16.0: the currency prices are shown in (Price checks > Show prices in), or "auto"."""
    try:
        from .config import SETTINGS
        u = SETTINGS.get("price_unit") or "auto"
    except Exception:
        u = "auto"
    return u if u in UNIT_NAMES or u == "auto" else "auto"


def fmt_div(x):
    """Show a value in the unit people actually trade it in: divine, chaos or exalted - or, 2.16.0, always in the
    currency picked under Show prices in (converted with poe.ninja's rates; divines when a rate isn't known)."""
    if x is None:
        return "—"
    unit = price_unit()
    if unit not in ("auto", "divine"):
        r = RATES.value(unit)
        if r:
            v = x / r
            return f"{_amt(v) if v >= 1 else f'{v:.2f}'} {UNIT_NAMES[unit]}"
    elif unit == "divine":
        return f"{_num(x)} div" if x >= 1 else f"{x:.2f} div"
    if x >= 1:
        return f"{_num(x)} div"
    for cur, name in (("chaos", "chaos"), ("exalted", "exalted")):
        r = RATES.value(cur)
        if r and x / r >= 0.95:
            return f"{_num(x / r)} {name}"
    return f"{x:.3f} div"


def fmt_price(p):
    a = p[0]
    return f"{int(a) if float(a).is_integer() else a} {p[1]}"


def parse_price(text):
    """What you typed in 'Listed at' ("8", "8 div", "35c", "2 ex", "8 div 50 chaos", "150 vaal") -> value in divines, or None
    if it can't be read. A bare number means divines. Never goes online: it only uses the exchange rates already loaded."""
    t = str(text or "").strip().lstrip("~≥> ")
    parts = re.findall(r"(\d+(?:[.,]\d+)?)\s*([a-zA-Z-]*)", t)
    if not parts or not re.fullmatch(r"(?:\d+(?:[.,]\d+)?\s*[a-zA-Z-]*[\s,+&]*)+", t):
        return None
    total = 0.0
    for num, unit in parts:
        amount, unit = float(num.replace(",", ".")), unit.lower()
        if unit in ("", "d") or unit.startswith("div"):
            total += amount
            continue
        cur = ("chaos" if unit == "c" or unit.startswith("chaos") else "exalted" if unit in ("e", "ex") or unit.startswith("exalt")
               else RATES.key(unit))
        r = RATES.value(cur)
        if r is None:
            return None
        total += amount * r
    return total
