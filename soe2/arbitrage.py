"""Uneven exchange rates (2.4.0): where the Currency Exchange prices the same thing differently in different markets.

Data: Grinding Gear Games' own public Currency Exchange history (pathofexile.com/developer/docs - "Currency Exchange",
https://web.poecdn.com/api/currency-exchange/poe2/<hour>). It's a summary of each finished hour: for every pair of
currencies traded in a league, how much of each changed hands. No account or key is needed. It is history only: the
current hour, and the live order book, aren't in it - the game shows those (hover the market ratio, hold Alt).

From one hour's summary, the average rate of a market A|B is (B traded) / (A traded). Going round three markets -
divine -> X -> exalted -> divine - ends with exactly what you started with when the markets agree. When the product of
the three average rates is above 1, one of them is cheaper than the others: that's an uneven rate.

What it is not: a promise of profit. Averages mix buys and sells, someone else may get there first, the exchange
charges gold for every trade, and big orders move the price. The page says so.

poe.ninja can't show this: it works out each currency's price from that currency's busiest market, so its prices agree
with each other by construction (checked against its data in 2.4.0).

Requests: only when you press Refresh, at most HOURS_MAX hours, one at a time with a pause, and finished hours are
cached (they never change), so a refresh usually asks for one new hour. A 429 answer (too many requests) stops the
refresh and waits as long as GGG asks."""
import os
import threading
import time

import requests

from .config import APP_VERSION, load_json, save_json

CX_URL = (os.environ.get("SOE2_CX") or "https://web.poecdn.com") + "/api/currency-exchange/poe2/{hour}"
CX_UA = f"StashOfExile2/{APP_VERSION} (contact: https://github.com/tiwomm/StashOfExile2)"
CACHE = "cx_history.json"
HOURS_MAX = 6                   # how far back one refresh looks
KEEP_HOURS = 48
GAP = 1.5                       # seconds between two requests
HUBS = ("divine", "exalted", "chaos")
HUB_NAMES = {"divine": "Divine Orb", "exalted": "Exalted Orb", "chaos": "Chaos Orb"}


def hour_now(now=None):
    return int((now or time.time()) // 3600 * 3600)


class CxHistory:
    """The cached hourly summaries for one league: {hour: [[a, b, volume a, volume b], ...]}."""

    def __init__(self):
        c = load_json(CACHE, {}) or {}
        self.league = c.get("league")
        self.hours = {int(h): m for h, m in (c.get("hours") or {}).items()}
        self.lock = threading.Lock()
        self.busy = False
        self.msg = ""
        self.error = ""
        self.wait_until = 0.0

    def save(self):
        keep = sorted(self.hours)[-KEEP_HOURS:]
        self.hours = {h: self.hours[h] for h in keep}
        save_json(CACHE, {"league": self.league, "hours": {str(h): m for h, m in self.hours.items()}})

    def wanted(self, n=HOURS_MAX, now=None):
        """The finished hours to show, newest first."""
        last = hour_now(now) - 3600
        return [last - 3600 * i for i in range(n)]

    def refresh(self, league, n=HOURS_MAX, get=None, sleep=time.sleep, now=None):
        """Fetch the finished hours we don't have yet (newest first). Safe to call from a thread. -> new hours."""
        get = get or (lambda url: requests.get(url, headers={"User-Agent": CX_UA, "Accept": "application/json"},
                                               timeout=20))
        with self.lock:
            if self.league != league:
                self.league, self.hours = league, {}
            if time.time() < self.wait_until:
                self.error = f"GGG asked to wait - try again in {int(self.wait_until - time.time()) + 1} s."
                return 0
            self.busy, self.error, got = True, "", 0
            try:
                todo = [h for h in self.wanted(n, now) if h not in self.hours]
                for i, h in enumerate(todo):
                    self.msg = f"Reading hour {i + 1} of {len(todo)}…"
                    r = get(CX_URL.format(hour=h))
                    if r.status_code == 429:
                        wait = float(r.headers.get("Retry-After") or 60)
                        self.wait_until = time.time() + wait
                        self.error = f"GGG asked to slow down: wait {int(wait)} s before the next refresh."
                        break
                    if r.status_code >= 400:
                        self.error = f"The Currency Exchange history answered {r.status_code}."
                        break
                    body = r.json()
                    if str(body.get("next_change_id")) == str(h):     # that hour isn't finished yet
                        continue
                    self.hours[h] = [m for m in (parse_markets(body, league) or [])]
                    got += 1
                    if i < len(todo) - 1:
                        sleep(GAP)
            except Exception as e:
                self.error = f"Couldn't read the Currency Exchange history ({str(e)[:90]})."
            finally:
                self.busy, self.msg = False, ""
                self.save()
            return got


def parse_markets(body, league):
    """One hour's summary -> [[a, b, volume of a, volume of b]] for `league` (markets where both moved)."""
    from .rates import Rates
    names = {n.lower() for n in Rates.names_for(league)}
    out = []
    for m in body.get("markets") or []:
        if str(m.get("league", "")).lower() not in names:
            continue
        pair = m.get("market_pair") or str(m.get("market_id", "")).split("|")
        vol = m.get("volume_traded") or {}
        if len(pair) != 2:
            continue
        a, b = pair
        va, vb = float(vol.get(a) or 0), float(vol.get(b) or 0)
        if va > 0 and vb > 0:
            out.append([a, b, va, vb])
    return out


def combine(hours_markets):
    """Several hours -> {(a, b): [volume a, volume b]} with a < b (volumes added up = a volume-weighted average)."""
    tot = {}
    for markets in hours_markets:
        for a, b, va, vb in markets:
            if a > b:
                a, b, va, vb = b, a, vb, va
            t = tot.setdefault((a, b), [0.0, 0.0])
            t[0] += va
            t[1] += vb
    return tot


def rate(tot, a, b):
    """How many b one a got, on average (None if that market didn't trade)."""
    if (a, b) in tot:
        va, vb = tot[(a, b)]
        return vb / va
    if (b, a) in tot:
        vb, va = tot[(b, a)]
        return vb / va
    return None


def volume(tot, a, b):
    """How much of `a` moved in the a|b market."""
    if (a, b) in tot:
        return tot[(a, b)][0]
    if (b, a) in tot:
        return tot[(b, a)][1]
    return 0.0


def values_in_divines(tot):
    """What each currency is worth in divines, from its own market with divines, else through exalted or chaos."""
    val = {"divine": 1.0}
    for hub in ("exalted", "chaos"):
        r = rate(tot, hub, "divine")
        if r:
            val[hub] = r
    for (a, b) in tot:
        for x, other in ((a, b), (b, a)):
            if x in val:
                continue
            for hub in HUBS:
                if hub == x or hub not in val:
                    continue
                r = rate(tot, x, hub)
                if r:
                    val[x] = r * val[hub]
                    break
    return val


def find_loops(tot, min_edge=0.02, min_div=5.0):
    """Three-market loops whose average rates don't agree. -> [dict] best first:
    start (a hub), item, edge (0.04 = 4 % more than you started with), depth (divines that moved
    in the thinnest of the three markets), steps [(from, to, rate)]."""
    val = values_in_divines(tot)
    items = {x for k in tot for x in k}
    hubs = [h for h in HUBS if h in items or h == "divine"]
    out = []
    for x in sorted(items):
        for i, h1 in enumerate(hubs):
            for h2 in hubs[i + 1:]:
                if x in (h1, h2):
                    continue
                r1, r2, r3 = rate(tot, h1, x), rate(tot, x, h2), rate(tot, h2, h1)
                if not (r1 and r2 and r3):
                    continue
                p = r1 * r2 * r3                     # h1 -> x -> h2 -> h1
                if p >= 1:
                    steps = [(h1, x, r1), (x, h2, r2), (h2, h1, r3)]
                else:                                # the other way round is the uneven one
                    p = 1 / p
                    steps = [(h1, h2, 1 / r3), (h2, x, 1 / r2), (x, h1, 1 / r1)]
                edge = p - 1
                depth = min(volume(tot, a, b) * val.get(a, 0) for a, b, _r in steps)
                if edge >= min_edge and depth >= min_div:
                    out.append({"start": steps[0][0], "item": x, "edge": edge, "depth": depth, "steps": steps})
    out.sort(key=lambda d: -d["edge"] * min(d["depth"], 200))
    return out


def hours_uneven(per_hour, loop, min_edge=0.02):
    """In how many of the hours (each its own {pair: volumes}) the same loop was uneven the same way."""
    n = 0
    for tot in per_hour:
        rs = [rate(tot, a, b) for a, b, _r in loop["steps"]]
        if all(rs):
            p = rs[0] * rs[1] * rs[2]
            if p - 1 >= min_edge:
                n += 1
    return n


def flip(buy, sell):
    """You can buy 1 X for `buy` Y and sell 1 X for `sell` Y. -> (Y gained per X, margin as a fraction)."""
    if not buy or buy <= 0 or sell is None:
        return None, None
    return sell - buy, (sell - buy) / buy


CX = CxHistory()
