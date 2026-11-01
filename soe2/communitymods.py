"""The community Mod book (2.31.0): every install's price checks make everyone's prices better.

Once an hour (and when the app closes) the app sends the Community board a SUMMARY of the listings its own price
checks saw since the last time - per (base, mod): how many listings and their median price, per base the same - plus
the Mod book rules you set (High / Normal / Ignore count as your vote). Nothing else: no account names, no items, no
listing ids. On by default with a notice the first time (Settings: "share_prices"). Reading what everyone pooled works
either way: it is downloaded with the same hourly sync and used where your own data has nothing to say yet -
  * a mod the pooled prices show as valuable (enough listings, lift, median at least your Valuable mod) counts as
    learned High ("from": "community"), unless your own data for this league decides it;
  * a mod most players rate High (at least 3 votes, 60 %) counts as shared High (mods.COMMUNITY_ACTIVE).
Your own rules always win. Nothing here searches the trade site."""
import json
import secrets
import statistics
import threading
import time

from . import board as B
from .config import SETTINGS, load_json, save_json

FILE = "community_mods.json"          # what was downloaded: {league, stats, ratings, players, ts}
SENT = "community_sent.json"          # {last_ts, votes: {key: value}, helped: {league: n}}
EVERY = 3600
MIN_N, MIN_BATCHES = 12, 3            # a pooled price counts once this many listings from this many summaries
VOTE_MIN, VOTE_SHARE = 3, 0.6

_lock = threading.Lock()


def sharing():
    return bool(SETTINGS.get("share_prices", True))


def cid():
    c = SETTINGS.get("contrib_id")
    if not (isinstance(c, str) and len(c) == 32):
        c = SETTINGS["contrib_id"] = secrets.token_hex(16)
        save_json("settings.json", SETTINGS)
    return c


def cached():
    d = load_json(FILE, {})
    return d if isinstance(d, dict) else {}


def sent_state():
    d = load_json(SENT, {})
    return d if isinstance(d, dict) else {}


def helped(league=None):
    """How many mod prices you've added to the community Mod book this league."""
    league = league if league is not None else SETTINGS.get("league") or ""
    return int(sent_state().get("helped", {}).get(league, 0))


# ---------------------------------------------------------------- what this install sends
def summary(market, since, league):
    """Listings your price checks stored since `since` -> (prices, bases, newest ts)."""
    if not market.db:
        return [], [], since
    with market.lock:
        rows = market.db.execute("SELECT base, price_div, sids, seen FROM listings WHERE league=? AND seen>? "
                                 "AND price_div IS NOT NULL ORDER BY seen LIMIT 20000", (league, since)).fetchall()
    by_pair, by_base, newest = {}, {}, since
    for base, price, sids, seen in rows:
        newest = max(newest, seen)
        by_base.setdefault(base, []).append(price)
        for sid in json.loads(sids or "[]"):
            by_pair.setdefault((base, sid), []).append(price)
    prices = [{"base": b, "sid": s, "n": len(v), "med": round(statistics.median(v), 4)}
              for (b, s), v in sorted(by_pair.items(), key=lambda kv: -len(kv[1]))][:600]
    bases = [{"base": b, "n": len(v), "med": round(statistics.median(v), 4)} for b, v in by_base.items()][:100]
    return prices, bases, newest


def vote_changes(rules, before):
    """Your Mod book rules -> the votes that changed since the last sync ({key, value}; None = you cleared it)."""
    out = [{"key": k, "value": v} for k, v in rules.items() if before.get(k) != v and v in ("high", "normal", "ignore")]
    out += [{"key": k, "value": None} for k in before if k not in rules]
    return out[:400]


def push(market, rules, call=None):
    """Send this hour's summary + rule changes. -> (True, how many prices) / (False, why)."""
    if not B.configured() or not sharing():
        return False, "off"
    league = SETTINGS.get("league") or ""
    st = sent_state()
    since = float(st.get("last_ts", 0) or 0) or (time.time() - EVERY)
    prices, bases, newest = summary(market, since, league)
    votes = vote_changes(dict(rules), st.get("votes", {}))
    from .maplib import ranks as map_ranks                # 2.32.0: your map ranks count as your vote too
    mine_maps = map_ranks()
    before = st.get("maps", {})
    maps = [{"name": k, "rank": v} for k, v in mine_maps.items() if before.get(k) != v]
    maps += [{"name": k, "rank": None} for k in before if k not in mine_maps]
    if not prices and not votes and not maps:
        return True, 0
    ok, d = (call or B.call)("POST", "/mods/batch", body={"cid": cid(), "league": league, "prices": prices,
                                                         "bases": bases, "votes": votes, "maps": maps[:400]})
    if not ok:
        return False, d
    st["last_ts"] = newest
    st["votes"] = {k: v for k, v in dict(rules).items() if v in ("high", "normal", "ignore")}
    st["maps"] = dict(mine_maps)
    st.setdefault("helped", {})[league] = int(st.get("helped", {}).get(league, 0)) + int(d.get("prices", 0))
    save_json(SENT, st)
    return True, int(d.get("prices", 0))


# ---------------------------------------------------------------- what everyone pooled
def pull(call=None):
    """Download the pooled prices for your league and the community ratings. -> (True, data) / (False, why)."""
    if not B.configured():
        return False, "off"
    league = SETTINGS.get("league") or ""
    ok, s = (call or B.call)("GET", "/mods/stats", {"league": league})
    if not ok:
        return False, s
    ok2, r = (call or B.call)("GET", "/mods/ratings")
    ok3, mp = (call or B.call)("GET", "/maps/ratings")
    d = {"league": league, "stats": s.get("stats", []), "players": s.get("players", 0),
         "ratings": r.get("ratings", []) if ok2 else cached().get("ratings", []),
         "maps": mp.get("maps", []) if ok3 else cached().get("maps", []), "ts": time.time()}
    save_json(FILE, d)
    return True, d


def learned_highs(league, good, high_lift):
    """sid -> {"tier", "lift", "n", "from": "community"} for mods the pooled prices show as valuable."""
    d = cached()
    if d.get("league") != league:
        return {}
    out = {}
    for row in d.get("stats", []):
        try:
            base, sid, n, med, lift, batches = row
        except (TypeError, ValueError):
            continue
        if n >= MIN_N and batches >= MIN_BATCHES and lift is not None and lift >= high_lift and med >= good:
            if sid not in out or lift > out[sid]["lift"]:
                out[sid] = {"tier": "high", "lift": lift, "n": n, "from": "community", "med": med}
    return out


def pooled(league=None):
    """(base, sid) -> {"n", "med", "lift", "batches"} - the community's prices (for showing next to your own)."""
    d = cached()
    league = league if league is not None else SETTINGS.get("league") or ""
    if d.get("league") != league:
        return {}
    return {(r[0], r[1]): {"n": r[2], "med": r[3], "lift": r[4], "batches": r[5]} for r in d.get("stats", []) if len(r) == 6}


def rated_high():
    """Mod book key -> (High votes, all votes) for the mods most players rate High."""
    out = {}
    for row in cached().get("ratings", []):
        try:
            key, high, normal, ignore = row
        except (TypeError, ValueError):
            continue
        total = (high or 0) + (normal or 0) + (ignore or 0)
        if total >= VOTE_MIN and (high or 0) / total >= VOTE_SHARE:
            out[key] = (high, total)
    return out


def stats_count():
    d = cached()
    return len(d.get("stats", [])) if d.get("league") == (SETTINGS.get("league") or "") else 0


# ---------------------------------------------------------------- the hourly sync
def sync(market, rules, apply=None):
    """push + pull, one at a time. apply() is called after new data arrived (re-learn, repaint)."""
    if not _lock.acquire(blocking=False):
        return None
    try:
        res = push(market, rules)
        got = pull()
        if got[0] and apply:
            apply()
        return res, got
    finally:
        _lock.release()
