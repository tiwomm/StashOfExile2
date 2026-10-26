"""Trade-site searches and fetches for price checks, and checking listings really carry the mods.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import json
import re
import statistics
import time
from datetime import datetime
from .config import AGE_OPTIONS, APP_VERSION, BASE, P, SETTINGS, STATUS_OPTIONS
from .net import call
from .rates import RATES
from .mods import DUPS, FLIP_PAIRS, impact_of, IMPACTS, norm, plural_wordings, SIDTEXT, strip_markup, TEXT2SID, VAL, vfilter


# ------------------------------------------------------------------ trade searching
_search_cache, _fetch_cache = {}, {}


CACHE_SECS = 600          # a repeated identical search within 10 minutes is free; after that listings are re-checked


def _cached(cache, key):
    hit = cache.get(key)
    return hit[1] if hit and time.time() - hit[0] < CACHE_SECS else None


_uses_cache = {}


def uses_stat_id(table):
    """The trade site's '# Uses Remaining (Tablets)' stat, found by name in the downloaded stat list."""
    key = id(table)
    if key not in _uses_cache:
        cands = [(k, entry) for k, entry in table.items() if re.match(r"^#?\s*uses? remaining", k)]
        found = next((c for c in cands if "(tablets)" in c[0]), cands[0] if cands else None)
        sid = None
        if found:
            for g in ("implicit", "explicit", "enchant", "pseudo"):
                if g in found[1]:
                    sid = found[1][g]
                    break
            sid = sid or next(iter(found[1].values()))
        _uses_cache.clear()
        _uses_cache[key] = sid
    return _uses_cache[key]


def uses_filter(table, is_tablet, own_uses):
    """-> ([stat filter], label note). Tablets only; follows the 'Min uses' dropdown (default 10)."""
    if not is_tablet:                  # 1.35: always "at least 10 uses" for tablets (the dropdown is gone)
        return [], ""
    n = 10
    if not n:
        return [], ""
    sid = uses_stat_id(table or {})
    if not sid:
        return [], " · uses-remaining filter unavailable"
    return [{"id": sid, "value": {"min": n}}], f" · {n}+ uses"


def mod_impact(rec, mod):
    """What this mod counts for on THIS item: your tick/star on the item first, else the global rule."""
    ov = (rec.get("ov") or {}).get(norm(mod["text"]))
    if ov in IMPACTS:
        return ov
    if mod.get("covered"):                  # gear (1.41): already counted in a total, or an implicit / rune
        return "ignore"
    if mod.get("kind") == "Total":          # gear totals (defences, DPS, pseudo totals) are must-haves
        return "high"
    if (rec.get("item") or {}).get("gear"):
        return "normal"                     # 2.0: tablet / jewel rules are worded like gear mods but aren't about gear
    return impact_of(mod["text"])


def listing_rules():
    """-> (API status value, API 'listed within' value, max age in hours or None) from the two dropdowns."""
    status = dict(STATUS_OPTIONS).get(SETTINGS.get("status"), "securable")      # unknown -> Instant Buyout
    api_age, hours = next(((a, h) for lab, a, h in AGE_OPTIONS if lab == SETTINGS.get("age")), ("3days", 48))
    return status, api_age, hours


def listed_ts(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:
        return time.time()          # can't read the date: keep the listing


def search_ids(league, base, filters, count_min, corrupted=None):
    """One trade search. Returns (total matches, first listing ids, query id). Same search twice = free."""
    plain, extra = [], []
    for f in filters:
        if f.get("own"):                              # 1.43: a count mod the trade site words in the singular
            f = {k: v for k, v in f.items() if k != "own"}
            extra.append({"type": "count", "value": {"min": 1}, "filters": [f]})
            continue
        ids = DUPS.get(f.get("id"))
        if ids and len(ids) > 1:                      # same wording under several ids: "at least 1 of these"
            extra.append({"type": "count", "value": {"min": 1},
                          "filters": [{**f, "id": i} for i in ids]})
        else:
            plain.append(f)
    if count_min is None:
        group = {"type": "and", "filters": plain}
    else:
        group = {"type": "count", "value": {"min": count_min}, "filters": plain}
    groups = ([group] if plain or not extra else []) + extra
    status, api_age, _hours = listing_rules()
    query = {"status": {"option": status}, "type": base, "stats": groups}
    flt = {}
    if corrupted is not None:
        flt["misc_filters"] = {"filters": {"corrupted": {"option": "true" if corrupted else "false"}}}
    if api_age:
        flt["trade_filters"] = {"filters": {"indexed": {"option": api_age}}}
    if flt:
        query["filters"] = flt
    key = league + json.dumps(query, sort_keys=True)
    hit = _cached(_search_cache, key)
    if hit is None:
        res = call("POST", f"{BASE}/search/poe2/{league}", json={"query": query, "sort": {"price": "asc"}})
        hit = (res.get("total", 0), res.get("result", [])[:10], res.get("id"))
        _search_cache[key] = (time.time(), hit)
    return hit


LISTING_MOD_KEYS = ("explicitMods", "fracturedMods", "craftedMods", "desecratedMods")


def fetch_rich(qid, ids, max_hours=None):
    """One fetch call for up to 10 listings -> [{id, price, ts, mods}] cheapest first.
    mods = [(normalised text, [numbers])] straight from the listing, or None if the listing didn't say.
    Listings older than max_hours are dropped (the search already filters, this is the double-check)."""
    key = ("rich", qid, tuple(ids), max_hours)
    out = _cached(_fetch_cache, key)
    if out is None:
        out = []
        if ids:
            fetched = call("GET", f"{BASE}/fetch/{','.join(ids)}", params={"query": qid})
            cutoff = time.time() - max_hours * 3600 if max_hours else None
            for e in fetched["result"]:
                lst = (e or {}).get("listing") or {}
                p = lst.get("price")
                if not p:
                    continue
                ts = listed_ts(lst.get("indexed"))
                if cutoff is not None and ts < cutoff:
                    continue
                it = (e or {}).get("item") or {}
                lines, seen_any = [], False
                for k in LISTING_MOD_KEYS:
                    v = it.get(k)
                    if isinstance(v, list):
                        seen_any = True
                        for x in v:
                            lines += [l for l in str(x).split("\n") if l.strip()]
                mods = None
                if seen_any:
                    mods = [(norm(l), [float(m.group(1)) for m in VAL.finditer(strip_markup(l))]) for l in lines]
                out.append({"id": (e or {}).get("id"), "price": (p["amount"], p["currency"]), "ts": ts, "mods": mods,
                            "fields": None if mods is not None else sorted(it.keys())[:40]})   # 2.0: for market_log.txt
        _fetch_cache[key] = (time.time(), out)
    return out


def fetch_prices(qid, ids, max_hours=None):
    """Same call, prices only: [(amount, currency)] cheapest first."""
    return [r["price"] for r in fetch_rich(qid, ids, max_hours)]


def build_sidtext(table):
    SIDTEXT.clear()
    TEXT2SID.clear()
    for k, groups in table.items():
        for g, sid in groups.items():
            SIDTEXT[sid] = k
        TEXT2SID[k] = groups.get("explicit") or next(iter(groups.values()))
    for sid, ids in DUPS.items():
        if sid not in SIDTEXT:
            t = next((SIDTEXT[i] for i in ids if i in SIDTEXT), None)
            if t:
                SIDTEXT[sid] = t


def acceptable_texts(sid):
    t = SIDTEXT.get(sid)
    if not t:
        return None
    out = {t} | plural_wordings(t)                   # 1.43: "an additional time" is listed as "3 additional times"
    for a, b in FLIP_PAIRS:                         # a "reduced" mod is listed under the "increased" stat with a minus
        if re.search(rf"\b{b}\b", t):
            out.add(re.sub(rf"\b{b}\b", a, t, count=1))
        if re.search(rf"\b{a}\b", t):
            out.add(re.sub(rf"\b{a}\b", b, t, count=1))
    return out


_verify_logged = [0]


def verify_listings(rich, mods):
    """Keep only listings that really carry every mod we searched for.
    -> (kept listings, {"ok", "bad", "unknown", "unverifiable"})."""
    required = [acc for acc in (acceptable_texts(m["sid"]) for m in mods if m.get("sid")) if acc]
    info = {"ok": 0, "bad": 0, "unknown": 0, "unverifiable": False}
    if not required:
        info["unknown"] = len(rich)
        return list(rich), info
    verdict = []
    for r in rich:
        if r["mods"] is None:
            verdict.append("unknown")
            continue
        lines = {t for t, _ in r["mods"]}
        verdict.append("ok" if all(any(a in lines for a in acc) for acc in required) else "bad")
    info["ok"], info["bad"], info["unknown"] = verdict.count("ok"), verdict.count("bad"), verdict.count("unknown")
    if info["bad"] and not info["ok"]:
        # EVERY readable listing failed: far more likely that our reader is wrong than that every listing is - keep them
        info["unverifiable"] = True
        if _verify_logged[0] < 3:
            _verify_logged[0] += 1
            try:
                with open(P("verify_log.txt"), "a", encoding="utf-8") as f:
                    f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} v{APP_VERSION}\nwe searched for: {required}\n")
                    for r in rich[:2]:
                        f.write(f"a listing says: {r['mods']}\n")
            except Exception:
                pass
        return list(rich), info
    return [r for r, v in zip(rich, verdict) if v != "bad"], info


def _flt(m, with_roll=True):
    f = {"id": m["sid"]}
    if m.get("novalue"):                              # no number on the trade site's wording: its own "at least 1" group
        f["own"] = True
    vf = vfilter(m) if with_roll else None
    if vf:
        f["value"] = vf
    return f


def estimate(prices, league):
    """Median of the cheapest 5 listings, in divines (None if currencies can't be converted)."""
    conv = []
    for amt, cur in prices[:5]:
        d = RATES.to_div(amt, cur, league)
        if d is not None:
            conv.append(d)
    return statistics.median(conv) if conv else None


def unconvertible(prices, league):
    """Currencies among the cheapest listings that we have no exchange rate for (those listings are left out of the price)."""
    return sorted({cur for amt, cur in prices[:5] if RATES.to_div(amt, cur, league) is None})


def ago(ts):
    sec = max(0, time.time() - ts)
    return f"{int(sec // 60)} min ago" if sec < 3600 else f"{int(sec // 3600)} h ago" if sec < 86400 else f"{int(sec // 86400)} d ago"
