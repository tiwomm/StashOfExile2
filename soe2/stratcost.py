"""What a strat costs today (2.46.0). A strat that lists its items (the waystone it runs, its tablets - with the mods
that matter, "key_mods") gets one trade-site search per item, at most once a day: base type + those mods, cheapest
first, the cheapest real offer (trade.cheapest_real) in divines. Results in strat_costs.json; Money Makers shows
"Cost now" next to the strat's own estimate.

Engine jobs (mixed into Engine: the same thread and trade-site limits as every other search). Only searches and
reads listings - never buys, whispers or lists anything (TOS.md)."""
import time

import requests

from .config import BASE, STATUS_OPTIONS, SETTINGS, load_json, save_json
from .net import call

FILE = "strat_costs.json"
EVERY = 24 * 3600
PRIO = 6                     # behind your own price checks


def costs():
    d = load_json(FILE, {})
    return d if isinstance(d, dict) else {}


def save_costs(d):
    save_json(FILE, d)


def due(s, all_costs, league, now=None):
    """Has this strat's cost not been checked in this league for a day?"""
    if not s.get("items"):
        return False
    c = all_costs.get(s.get("id")) or {}
    return c.get("league") != league or (now or time.time()) - (c.get("at") or 0) > EVERY


def query(item):
    """One item of a strat -> a trade search: its base type, its key mods (those the app knows), cheapest first."""
    from .moneymakers import stat_id
    st = dict(STATUS_OPTIONS).get(SETTINGS.get("status"), "securable")
    q = {"query": {"status": {"option": st}, "type": item["base"]}, "sort": {"price": "asc"}}
    ids = [i for i in (stat_id(m) for m in item.get("key_mods") or []) if i]
    if ids:
        q["query"]["stats"] = [{"type": "and", "filters": [{"id": i} for i in ids]}]
    return q, len(ids), len(item.get("key_mods") or [])


class StratCostJobs:
    def strat_cost_start(self, s, league):
        """Queue one strat's items (from the Money Makers window)."""
        for i, it in enumerate(s.get("items") or []):
            if it.get("base"):
                self.add(PRIO, "strat_cost", s["id"], i, dict(it), league)
        self.add(PRIO + 0.5, "strat_cost_done", s["id"], league)

    def do_strat_cost(self, sid, i, item, league):
        from .trade import cheapest_real
        q, known, wanted = query(item)
        res = call("POST", f"{BASE}/search/poe2/{requests.utils.quote(league)}", json=q)
        ids = list(res.get("result") or [])[:10]
        prices = []
        if ids:
            got = call("GET", f"{BASE}/fetch/{','.join(ids)}", params={"query": res.get("id")})
            for e in got.get("result") or []:
                p = ((e or {}).get("listing") or {}).get("price") or {}
                if p.get("amount") is not None and p.get("currency"):
                    prices.append((p["amount"], p["currency"]))
        price = cheapest_real(prices, league) if prices else None
        self.ui_q.put(("strat_cost", sid, i, price, {"listings": int(res.get("total") or 0), "mods_known": known,
                                                     "mods_wanted": wanted}))

    def do_strat_cost_done(self, sid, league):
        self.ui_q.put(("strat_cost_finished", sid, league))
