"""Currency exchange rates from poe.ninja (what each currency is worth in divines).

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import math
import os
import re
import requests
import threading
import time
from .config import APP_VERSION, load_json, P, save_json
from .util import _num


# ------------------------------------------------------------------ currency -> divine
NINJA_URL = (os.environ.get("SOE2_NINJA") or "https://poe.ninja") + "/poe2/api/economy/exchange/current/overview"


LOW_CURRENCIES = {"exalted", "chaos", "regal", "alch", "alchemy", "aug", "augmentation", "transmute", "transmutation"}


# trade-site currency names that differ from poe.ninja's ids -> poe.ninja's id
RATE_ALIASES = {"alchemy": "alch", "augmentation": "aug", "transmutation": "transmute", "orb-of-annulment": "annul",
                "vaal-orb": "vaal", "divine-orb": "divine", "chaos-orb": "chaos", "exalted-orb": "exalted",
                "mirror-of-kalandra": "mirror", "regal-orb": "regal"}


RATES_UA = f"StashOfExile2/{APP_VERSION} (personal Path of Exile 2 price checker; one small request an hour)"


class Rates:
    """What each currency is worth in divines, from poe.ninja's public exchange overview (one small request per hour -
    the site itself only refreshes PoE 2 about hourly, and asks apps to use its HTTP caching, which we do with ETag).
    rates.json can override any currency, e.g. {"vaal": 0.016}."""

    def __init__(self):
        self.manual = load_json("rates.json", {})
        cached = load_json("rates_cache.json", {})
        self.table = cached.get("table", {})
        self.vol = cached.get("vol", {})              # how much of each currency traded (in divines): thin markets are shaky
        self.league = cached.get("league")
        self.fetched = cached.get("ts", 0)
        self.etag = cached.get("etag")
        self.source = cached.get("source", "")
        self.attempt = 0.0
        self.error = ""
        self.lock = threading.Lock()
        self.unknown = {}                              # currency id -> how many listings were left out for lack of a rate

    @staticmethod
    def key(cur):
        c = str(cur).strip().lower().replace("_", "-")
        return RATE_ALIASES.get(c, c)

    @staticmethod
    def names_for(league):
        """The league may be spelled differently on poe.ninja than on the trade site."""
        base = re.sub(r"\s*\((?:SC|Softcore)\)\s*$", "", league)
        out = [league, base]
        if base.startswith("Hardcore "):
            out.append("HC " + base[9:])
        if base.startswith("HC "):
            out.append("Hardcore " + base[3:])
        return list(dict.fromkeys(out))

    def age(self):
        return (time.time() - self.fetched) if self.fetched else None

    def _save(self):
        save_json("rates_cache.json", {"table": self.table, "vol": self.vol, "league": self.league, "ts": self.fetched,
                                       "etag": self.etag, "source": self.source})

    def ensure(self, league, force=False):
        """Refresh the table if it is over an hour old (or `force`). Safe to call from any thread."""
        now = time.time()
        if not force:
            if self.league == league and now - self.fetched < 3600:
                return
            if self.league == league and now - self.attempt < 600:
                return                                           # failed recently, don't hammer
        with self.lock:                                          # one refresh at a time
            if not force and self.league == league and time.time() - self.fetched < 3600:
                return
            self.attempt = time.time()
            for name in self.names_for(league):
                try:
                    hdr = {"User-Agent": RATES_UA}
                    if self.etag and self.league == league:
                        hdr["If-None-Match"] = self.etag         # "nothing new" costs them almost nothing
                    r = requests.get(NINJA_URL, params={"league": name, "type": "Currency"}, headers=hdr, timeout=20)
                    if r.status_code == 304 and self.league == league:
                        self.fetched, self.error = time.time(), ""
                        self._save()
                        return
                    r.raise_for_status()
                    body = r.json()
                    lines = body.get("lines", [])
                    tbl = {ln["id"]: float(ln["primaryValue"]) for ln in lines if ln.get("id") and ln.get("primaryValue")}
                    # 2.0 beta 7: values are in poe.ninja's primary currency, which isn't always the divine: convert
                    core = body.get("core") or {}
                    primary = core.get("primary") or "divine"
                    if primary != "divine" and tbl:
                        per = (core.get("rates") or {}).get("divine")       # 1 primary = this many divines
                        if not per and tbl.get("divine"):
                            per = 1.0 / tbl["divine"]
                        if per:
                            tbl = {k: v * float(per) for k, v in tbl.items()}
                            vol_f = float(per)
                        else:
                            tbl, vol_f = {}, 1.0
                    else:
                        vol_f = 1.0
                    if tbl:
                        tbl["divine"] = 1.0
                        self.table = tbl
                        self.vol = {ln["id"]: float(ln.get("volumePrimaryValue") or 0) * vol_f for ln in lines if ln.get("id")}
                        self.league, self.fetched, self.error = league, time.time(), ""
                        self.etag, self.source = r.headers.get("ETag"), f"poe.ninja ({name})"
                        self._save()
                        return
                    self.error = "poe.ninja sent no currency prices"
                except Exception as e:
                    self.error = str(e)[:120]
            if self.league != league:                            # different league than the cached numbers: drop them
                self.table, self.vol, self.league, self.fetched, self.etag = {}, {}, league, 0.0, None

    def value(self, cur):
        k = self.key(cur)
        r = self.manual.get(cur, self.manual.get(k, self.table.get(k)))
        if r is None or (k in LOW_CURRENCIES and r > 1):  # a 'cheap' currency worth more than a divine = bad data
            return None
        return float(r)

    def to_div(self, amount, cur, league):
        if self.key(cur) == "divine":
            return float(amount)
        self.ensure(league)
        r = self.value(cur)
        if r is None:
            self.note_unknown(cur)
            return None
        return float(amount) * r

    def note_unknown(self, cur):
        """A listing was priced in a currency we have no rate for: count it, and write it down once so it can be fixed."""
        first = cur not in self.unknown
        self.unknown[cur] = self.unknown.get(cur, 0) + 1
        if first:
            try:
                with open(P("currency_log.txt"), "a", encoding="utf-8") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  no exchange rate for '{cur}' (poe.ninja ids: "
                            f"{', '.join(sorted(self.table)[:40])}...)\n")
            except Exception:
                pass

    def status_text(self):
        a = self.age()
        if not self.table:
            return "Rates: none yet" + (f" ({self.error})" if self.error else "")
        mins = int(a // 60) if a is not None else 0
        ago_txt = "just now" if mins < 1 else f"{mins} min ago" if mins < 120 else f"{mins // 60} h ago"
        return f"Rates: {self.source or 'poe.ninja'} · {ago_txt}" + ("  ⚠ " + self.error if self.error and a and a > 5400 else "")

    def equivalents(self, div, min_volume=5):
        """[(currency id, amount)] for the currencies people list in, worth a look next to a price in divines."""
        out = []
        for cur in ("chaos", "exalted", "vaal"):
            r = self.value(cur)
            if r and (self.vol.get(cur, min_volume) >= min_volume or cur in self.manual):
                out.append((cur, div / r))
        return out

    def list_options(self, div):
        """Plain-text help for 'is 8.5 div worth 8 or 9?': the neighbouring whole numbers, and a divine + chaos split."""
        if div is None or div < 2:
            return ""
        lo, hi = math.floor(div), math.ceil(div)
        bits = []
        if lo != hi:
            bits.append(f"{lo} div ({(lo / div - 1) * 100:+.0f}%)  or  {hi} div ({(hi / div - 1) * 100:+.0f}%)")
            c = self.value("chaos")
            if c:
                bits.append(f"or  {lo} div + {_num((div - lo) / c)} chaos")
        else:
            bits.append(f"{lo} div")
        return "   ".join(bits)


RATES = Rates()


# ---------------------------------------------------------------- the in-game Currency Exchange (2.2.0)
def whole_ratio(r, max_left=20, tol=0.004):
    """r = how many of B one A is worth -> (a, b) whole numbers with b / a close to r, the smallest a that's within
    tol (0.4%) - the Currency Exchange only takes whole numbers. 182.3 -> (1, 182); 0.0055 -> (182, 1)."""
    if r is None or r <= 0:
        return None
    if r < 1:
        b, a = whole_ratio(1 / r, max_left, tol)
        return a, b
    best = None
    for a in range(1, max_left + 1):
        b = max(1, round(r * a))
        err = abs(b / a - r) / r
        if best is None or err < best[2] - 1e-12:
            best = (a, b, err)
        if err <= tol:
            break
    return best[0], best[1]


def exchange_offers(have, want, rates, spread=0.02):
    """What to post on the Currency Exchange when you sell `have` for `want`:
    [(label, a, b, note)] - a of `have` for b of `want`. Quick = a little under the market (fills fast), Fair = the
    market rate, Patient = a little over (waits for a buyer). None if either rate is missing."""
    vh, vw = rates.value(have) if have != "divine" else 1.0, rates.value(want) if want != "divine" else 1.0
    if not vh or not vw:
        return None
    r = vh / vw                                          # how many `want` one `have` is worth
    out = []
    for label, k, note in (("Quick sale", 1 - spread, "a little under the market: someone takes it soon"),
                           ("Fair", 1.0, "the market rate"),
                           ("Patient", 1 + spread, "a little over the market: wait for a buyer")):
        a, b = whole_ratio(r * k)
        out.append((label, a, b, note))
    return r, out
