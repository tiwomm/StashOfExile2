"""The community Mod book (2.31.0): every install's price checks make everyone's prices better.

Once an hour (and when the app closes) the app sends the Community board a SUMMARY of the listings its own price
checks saw since the last time - per (base, mod): how many listings and their median price, per base the same - plus
the Mod book rules you set (High / Normal / Ignore count as your vote). Nothing else: no account names, no items, no
listing ids. 2.69.1: off until you say yes - the first run asks (Settings › General › Community data sharing,
"share_prices"; "share_asked" once answered). The same switch covers putting strats on the Money Makers board.
Reading what everyone pooled works either way: it is downloaded with the same hourly sync and used where your own data has nothing to say yet -
  * a mod the pooled prices show as valuable (enough listings, lift, median at least your Valuable mod) counts as
    learned High ("from": "community"), unless your own data for this league decides it;
  * a mod most players rate High (at least 3 votes, 60 %) counts as shared High (mods.COMMUNITY_ACTIVE).
Your own rules always win. Nothing here searches the trade site."""
import json
import re
import secrets
import statistics
import threading
import time

from . import board as B
from .config import SETTINGS, load_json, save_json

FILE = "community_mods.json"          # what was downloaded: {league, stats, ratings, players, ts}
SENT = "community_sent.json"          # {last_ts, votes: {key: value}, helped: {league: n}}
EVERY = 3600
UPLOAD_EVERY = 45 * 60      # 2.98.5: "Upload to community" - the board takes one batch per install per 45 min
MIN_N, MIN_BATCHES = 12, 3            # a pooled price counts once this many listings from this many summaries
VOTE_MIN, VOTE_SHARE = 3, 0.6
MAX_PRICES, MAX_BASES = 600, 100      # what the board takes from one batch
POOL = "pool:"                         # 2.133.0: gear / uniques / fallback searches - never teach the Mod book

_lock = threading.Lock()


# 2.69.1: what "Community data sharing" sends - said the same way in Settings and in the first-run question
WHAT = ("Community data sharing is off until you say yes. If you turn it on, the app sends anonymous data to its own "
        "community server so everyone's numbers get better: mod prices, Mod Book ratings, map ranks, your best times "
        "for the Leaderboards, new campaign zones, mod lines it couldn't read, and the strats you upload. No account or character names, no "
        "items, no listing ids. It is never sold and never used for ads.")

# 2.89.2 (feedback): each thing sent, and what it's for. Keep this list TRUE - every
# new upload that rides on this switch gets a line here.
DETAILS = (
    ("Mod prices your price checks see", "a summary only - how many listings and their middle price, per mod, for any item "
     "you price-check (gear too)", "better "
     "prices for everyone in the Mod Book, most of all early in a league"),
    ("Your Mod Book ratings", "the S-F tier (F = ignore) you set for a mod", "the pooled ratings that decide which mods "
     "matter"),
    ("Your map ranks", "the rank you gave a map", "the community map ranks"),
    ("Your best times", "map, boss, trial and act times with your class, level, deaths and league - under your "
     "community name, never your character's", "the Leaderboards (you can turn this one off on its own)"),
    ("Campaign zones the guide doesn't know", "the zone's name, its act and level", "the next update of the campaign "
     "guide"),
    ("Mod lines the app couldn't read", "the wording only, numbers as #, and the item's base type (like Solar Amulet)",
     "fixing them in the next update"),
    ("Strats you upload yourself", "only when you press Upload / Post - with rates (div per hour), never your totals",
     "the Money Makers and Strat Tracker boards"),
    ("Your community name, votes and reports", "only when you join, vote or report yourself", "the board itself"),
)
WHERE = ("It all goes to the StashOfExile2 community server (run by the app's developer on Cloudflare) - not to GGG, "
         "not to anyone else. It is never sold and never used for ads or tracking. Your internet address is never "
         "stored: only a keyed scramble of it, to stop spam, deleted the next day. Private leagues are never shared, and "
         "leaderboard times show the day, not the time. Settings › Privacy & community › Leave and delete my data "
         "deletes your name, strats and leaderboard times. What you shared anonymously (mod prices, ratings, map "
         "ranks, unmatched mods) stays in the pool for everyone - it was never linked to you.")
NEVER = ("Never sent: your account or character names, your wealth (stash value, net worth), your items or stash, "
         "listing ids, files from your computer. Check a screenshot before you upload it - it's public. Bug reports are "
         "separate: they go only when you press Report a bug, and you see every word first.")


def sharing():
    """Opt-in (2.69.1): only after you said yes."""
    return bool(SETTINGS.get("share_prices", False)) and bool(SETTINGS.get("share_asked"))


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
    """Listings your price checks stored since `since` -> (prices, bases, newest ts). 2.133.0: the Mod book's listings
    first, then the pool's (gear, uniques, fallback searches) fill what's left of the batch."""
    if not market.db:
        return [], [], since
    with market.lock:
        rows = market.db.execute("SELECT base, price_div, sids, seen FROM listings WHERE league=? AND seen>? "
                                 "AND price_div IS NOT NULL ORDER BY seen LIMIT 20000", (league, since)).fetchall()
        more = market.db.execute("SELECT base, price_div, sids, seen FROM pool WHERE league=? AND seen>? "
                                 "AND price_div IS NOT NULL ORDER BY seen LIMIT 20000", (league, since)).fetchall()
    newest, prices, bases = since, [], []
    for tag, part in (("", rows), (POOL, more)):        # pool rows go up as "pool:<base>": kept apart on the board
        by_pair, by_base = {}, {}
        for base, price, sids, seen in part:
            base = (tag + base)[:80]
            newest = max(newest, seen)
            by_base.setdefault(base, []).append(price)
            for sid in json.loads(sids or "[]"):
                by_pair.setdefault((base, sid), []).append(price)
        prices += [{"base": b, "sid": s, "n": len(v), "med": round(statistics.median(v), 4)}
                   for (b, s), v in sorted(by_pair.items(), key=lambda kv: -len(kv[1]))][:MAX_PRICES - len(prices)]
        bases += [{"base": b, "n": len(v), "med": round(statistics.median(v), 4)}
                  for b, v in sorted(by_base.items(), key=lambda kv: -len(kv[1]))][:MAX_BASES - len(bases)]
    return prices, bases, newest


# 2.121.1 (feedback: "unmatched_mods.txt to the cloud ... whatever requires no input from anyone"): the mod lines
# your price checks couldn't match ride on the same switch and the same hourly batch - no new option. Only the wording
# with every number as #, and the base type; never the item's name, never a note. The board publishes a line once
# two installs sent it (GET /mods/unmatched); a weekly workflow keeps a copy for fixing the matcher.
_UM_OK = re.compile(r"^[\w #%+\-.,'():/]{3,100}$")
_UM_BASE = re.compile(r"^[\w ',.\-]{1,60}$")


def unmatched_line(line):
    """One unmatched_mods.txt line -> {"text", "base"} safe to share, or None."""
    text, _, where = (line or "").rstrip("\n").partition("\t|")
    t = re.sub(r"\d+(?:\.\d+)?", "#", text.strip())
    t = re.sub(r"\(#-#\)", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not _UM_OK.match(t) or t.lower().startswith("note") or "~" in t or "#" not in t and len(t) > 80:
        return None
    m = re.match(r"^\s*.*\((.+)\)\s*$", where or "")
    base = m.group(1).strip() if m and not where.strip().startswith("closest") else ""
    return {"text": t, "base": base if _UM_BASE.match(base or "") else ""}


def unmatched_unsent(st=None, limit=100):
    """The shareable unmatched lines the board hasn't had from this install yet."""
    from .config import P
    st = st if st is not None else sent_state()
    done = set(st.get("unmatched") or [])
    out, seen = [], set()
    try:
        with open(P("unmatched_mods.txt"), encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return []
    for line in lines:
        u = unmatched_line(line)
        if u and u["text"] not in done and u["text"] not in seen:
            seen.add(u["text"])
            out.append(u)
    return out[-limit:]


def vote_changes(rules, before):
    """Your Mod book rules -> the votes that changed since the last sync ({key, value}; None = you cleared it)."""
    out = [{"key": k, "value": v} for k, v in rules.items() if before.get(k) != v and v in ("high", "normal", "ignore")]
    out += [{"key": k, "value": None} for k in before if k not in rules]
    return out[:400]


def push(market, rules, call=None):
    """Send this hour's summary + rule changes. -> (True, how many prices) / (False, why)."""
    if not B.configured() or not sharing():
        return False, "off"
    from .privacy import is_private_league                 # 2.89.3: a private league's numbers never go up
    if is_private_league(SETTINGS.get("league")):
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
    from . import campaign as CP                          # 2.77.0: campaign zones the guide pack didn't know
    zones = CP.to_pool()
    unmatched = unmatched_unsent(st)                      # 2.121.1
    gems, gems_ts = gems_unsent(league, st)               # 2.132.0: gem prices your searches found
    if not prices and not votes and not maps and not zones and not unmatched and not gems:
        return True, 0
    ok, d = (call or B.call)("POST", "/mods/batch", body={"cid": cid(), "league": league, "prices": prices,
                                                         "bases": bases, "votes": votes, "maps": maps[:400],
                                                         "zones": zones, "unmatched": unmatched, "gems": gems})
    if not ok:
        return False, d
    CP.pooled(zones)
    st["pushed"] = time.time()
    st["last_ts"] = newest
    st["votes"] = {k: v for k, v in dict(rules).items() if v in ("high", "normal", "ignore")}
    st["maps"] = dict(mine_maps)
    st["unmatched"] = (list(st.get("unmatched") or []) + [u["text"] for u in unmatched])[-2000:]
    if gems:
        st["gems_ts"] = gems_ts
    st.setdefault("helped", {})[league] = int(st.get("helped", {}).get(league, 0)) + int(d.get("prices", 0))
    save_json(SENT, st)
    return True, int(d.get("prices", 0))


def gems_unsent(league, st=None):
    """2.132.0: gem prices found by your own searches since the last batch (remnant_gems.json) -> ([{kind, level,
    name, div}], newest time). Only market prices - nothing about you."""
    from .config import load_json
    st = sent_state() if st is None else st
    since = float(st.get("gems_ts", 0) or 0)
    out, newest = [], since
    for k, v in (load_json("remnant_gems.json", {}) or {}).items():
        parts = k.split("|")
        try:
            each, ts = v[0], float(v[1])
        except (TypeError, ValueError, IndexError):
            continue
        if len(parts) != 4 or parts[0] != league or each is None or ts <= since:
            continue
        out.append({"kind": parts[1], "level": int(parts[2]) if parts[2] else 0, "name": parts[3], "div": float(each)})
        newest = max(newest, ts)
    return out[:200], newest


def community_gem(league, kind, level, name):
    """2.132.0: the board's pooled price for a gem -> (divines, when found) or None."""
    memo = _GEMS.get("memo")
    if memo is None or time.time() - memo[0] > 30:                 # (a book is read often: the file once a while)
        d = cached()
        table = {}
        for row in d.get("gems") or []:
            try:
                table[(row[0], int(row[1]), str(row[2]))] = (float(row[3]), float(row[4]))
            except (TypeError, ValueError, IndexError):
                continue
        memo = _GEMS["memo"] = (time.time(), d.get("league"), table)
    if memo[1] != league:
        return None
    return memo[2].get((kind, int(level or 0), str(name).casefold()))


_GEMS = {}


def upload_wait(now=None):
    """2.98.5: seconds until the next upload is allowed (0 = now). Matches the board's own limit, so a button
    can't be used to spam it."""
    last = float(sent_state().get("pushed", 0) or 0)
    return max(0, int(UPLOAD_EVERY - ((now or time.time()) - last)))


def maps_unsent():
    """2.98.5: how many of your map ranks the board doesn't have yet."""
    from .maplib import ranks as map_ranks
    mine, before = map_ranks(), sent_state().get("maps", {})
    return sum(1 for k, v in mine.items() if before.get(k) != v) + sum(1 for k in before if k not in mine)


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
    ok4, gm = (call or B.call)("GET", "/gems", {"league": league})      # 2.132.0: pooled gem prices
    d = {"league": league, "stats": s.get("stats", []), "players": s.get("players", 0), "active": s.get("active"),
         "ratings": r.get("ratings", []) if ok2 else cached().get("ratings", []),
         "maps": mp.get("maps", []) if ok3 else cached().get("maps", []),
         "gems": gm.get("gems", []) if ok4 else cached().get("gems", []), "ts": time.time()}
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
        if str(base).startswith(POOL):
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
    return {(r[0], r[1]): {"n": r[2], "med": r[3], "lift": r[4], "batches": r[5]} for r in d.get("stats", [])
            if len(r) == 6 and not str(r[0]).startswith(POOL)}


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


def installs():
    """2.133.0: (installs that ever shared, active in the last 7 days) from the last sync, or None before one."""
    d = cached()
    if not d.get("ts"):
        return None
    return int(d.get("players") or 0), d.get("active")


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
