"""Market memory (market.db): every search and listing seen, learned priority, comparables.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import json
import sqlite3
import statistics
import threading
import time
from .config import MODBOOK, P, SETTINGS
from .rates import RATES
from .mods import HIGH_LIFT, impact_of, LEARNED, MIN_WITH, MIN_WITHOUT, rebuild_community, sid_for_line, SIDTEXT, TEXT2SID, vfilter


class Market:
    """Everything the app has seen, kept in market.db: each search (which mods, how many listings, cheapest, estimate)
    and each listing (its mods, rolls and asking price). Every row is tagged with its league, so a new league starts
    with fresh prices. Used to spot a price that contradicts earlier searches, to hint at comparable listings, to
    learn which mods matter (LEARNED), and to keep score of how good its own guesses are (table preds)."""

    KEEP_DAYS = 45

    def __init__(self):
        self.lock = threading.RLock()
        self.db = None
        self.db_error = self.last_error = ""
        self.since_learn = 0
        self.rec_stats = self._new_rec_stats()
        try:
            self.db = sqlite3.connect(P("market.db"), check_same_thread=False)
            with self.lock:
                self.db.executescript(
                    "CREATE TABLE IF NOT EXISTS obs(ts REAL, base TEXT, key TEXT, filters TEXT, stage TEXT, total INT,"
                    " n INT, floor_div REAL, est_div REAL);"
                    "CREATE INDEX IF NOT EXISTS obs_base ON obs(base, ts);"
                    "CREATE TABLE IF NOT EXISTS listings(id TEXT PRIMARY KEY, base TEXT, seen REAL, indexed REAL,"
                    " price_div REAL, sids TEXT);"
                    "CREATE TABLE IF NOT EXISTS preds(ts REAL, league TEXT, base TEXT, pred REAL, actual REAL, n_comp INT);"
                    "CREATE TABLE IF NOT EXISTS listed(sig TEXT PRIMARY KEY, ts REAL, league TEXT, base TEXT, name TEXT,"
                    " sids TEXT, vals TEXT, est_div REAL, listed_div REAL);"
                    "CREATE TABLE IF NOT EXISTS legacy(sid TEXT PRIMARY KEY, lift REAL, n INT, league TEXT, text TEXT);")
                for table, col, kind in (("obs", "league", "TEXT"), ("listings", "league", "TEXT"), ("listings", "vals", "TEXT")):
                    if col not in [r[1] for r in self.db.execute(f"PRAGMA table_info({table})")]:
                        self.db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {kind}")
                lg = SETTINGS.get("market_league") or SETTINGS.get("league")
                if lg:                                    # rows written before 1.23 belong to the league you were on
                    self.db.execute("UPDATE obs SET league=? WHERE league IS NULL", (lg,))
                    self.db.execute("UPDATE listings SET league=? WHERE league IS NULL", (lg,))
                    if not SETTINGS.get("market_league"):
                        SETTINGS["market_league"] = lg
                cut = time.time() - self.KEEP_DAYS * 86400
                self.db.execute("DELETE FROM obs WHERE ts<?", (cut,))
                self.db.execute("DELETE FROM listings WHERE seen<?", (cut,))
                self.db.execute("CREATE INDEX IF NOT EXISTS listings_bl ON listings(base, league)")
                self.db.commit()
        except Exception as e:
            self.db = None
            self.db_error = f"{type(e).__name__}: {e}"
        self.refresh_learned()

    @staticmethod
    def cur():
        return SETTINGS.get("league") or ""

    @staticmethod
    def filters_of(mods):
        out = []
        for m in mods:
            vf = vfilter(m) if m.get("sid") else None
            op, t = (next(iter(vf.items())) if vf else (None, None))
            out.append([m["sid"], op, t])
        return sorted(out, key=lambda f: f[0])

    def record(self, base, filt, stage, total, kept, est):
        if not self.db:
            return
        try:
            league, now = self.cur(), time.time()
            pairs = [(r, RATES.to_div(r["price"][0], r["price"][1], league)) for r in kept]
            rs = self.rec_stats
            rs["listings"] += len(kept)
            for r, d in pairs:
                if d is None:
                    rs["no_rate"] += 1
                    rs["currencies"].add(str(r["price"][1]))
            pairs = [(r, d) for r, d in pairs if d is not None]            # a listing in a currency with no rate is left out
            if kept and not pairs:
                self.last_error = f"all {len(kept)} listings were in currencies with no exchange rate (see currency_log.txt)"
            divs = [d for _, d in pairs]
            with self.lock:
                self.db.execute("INSERT INTO obs VALUES (?,?,?,?,?,?,?,?,?,?)",
                                (now, base, json.dumps(filt), json.dumps(filt), stage, total, len(kept),
                                 min(divs) if divs else None, est, league))
                for r, d in pairs:
                    if not r.get("id"):
                        rs["no_id"] += 1
                    elif r["mods"] is None:
                        rs["no_mods"] += 1
                        if r.get("fields") and len(rs["field_samples"]) < 3:
                            rs["field_samples"].append(r["fields"])
                    if r.get("id") and r["mods"] is not None:
                        sids, vals = set(), {}
                        for t, nums in r["mods"]:
                            sid = sid_for_line(t)
                            if sid:
                                sids.add(sid)
                                if nums:
                                    vals[sid] = nums[0]
                            else:
                                rs["lines_unmatched"] += 1
                                if len(rs["line_samples"]) < 12 and t not in rs["line_samples"]:
                                    rs["line_samples"].append(t)
                        rs["lines"] += len(r["mods"])
                        rs["stored"] += 1
                        rs["stored_with_mods"] += bool(sids)
                        if not sids:
                            self.last_error = ("a listing's mods did not match the trade site's mod list "
                                               f"(known mod texts: {len(TEXT2SID)}) - if that is 0 the mod list failed to download")
                        self.db.execute("INSERT OR REPLACE INTO listings(id, base, seen, indexed, price_div, sids, league, vals)"
                                        " VALUES (?,?,?,?,?,?,?,?)",
                                        (r["id"], base, now, r["ts"], d, json.dumps(sorted(sids)), league, json.dumps(vals)))
                self.db.commit()
            self.write_log()
            self.since_learn += 1
            if self.since_learn >= 20:                    # now and then: re-work out which mods matter
                self.since_learn = 0
                self.refresh_learned()
        except Exception as e:
            self.last_error = f"{type(e).__name__}: {e}"

    def _new_rec_stats(self):
        return {"listings": 0, "no_rate": 0, "currencies": set(), "no_id": 0, "no_mods": 0, "field_samples": [],
                "stored": 0, "stored_with_mods": 0, "lines": 0, "lines_unmatched": 0, "line_samples": [],
                "known_texts": 0}

    def rec_summary(self):
        """One plain paragraph: what happened to the listings fetched since the app started (2.0)."""
        rs = self.rec_stats
        if not rs["listings"]:
            return "No listings fetched since the app started."
        out = [f"Since the app started: {rs['listings']} listings fetched, {rs['stored']} saved, "
               f"{rs['stored_with_mods']} of them with mods the app could read."]
        if rs["no_rate"]:
            out.append(f"{rs['no_rate']} were priced in currencies with no exchange rate ({', '.join(sorted(rs['currencies']))}).")
        if rs["no_mods"]:
            out.append(f"{rs['no_mods']} came without any mod text.")
        if rs["lines_unmatched"]:
            out.append(f"{rs['lines_unmatched']} of {rs['lines']} mod lines were not on the trade site's mod list "
                       f"(it knows {len(TEXT2SID)} wordings).")
        return " ".join(out)

    def write_log(self):
        """market_log.txt in the data folder: the same summary plus examples, so the cause of an empty Mod book can be
        found."""
        rs = self.rec_stats
        try:
            with open(P("market_log.txt"), "w", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S") + f"  league {self.cur()!r}\n{self.rec_summary()}\n")
                f.write(f"database: {self.counts()[0]} searches, {self.counts()[1]} listings stored this league\n")
                if rs["field_samples"]:
                    f.write("\nfields of listings without mod text:\n" + "\n".join(map(str, rs["field_samples"])) + "\n")
                if rs["line_samples"]:
                    f.write("\nmod lines not on the trade site's list:\n" + "\n".join(rs["line_samples"]) + "\n")
                if self.last_error:
                    f.write(f"\nlast recording problem: {self.last_error}\n")
        except Exception:
            pass

    def counts(self):
        """(searches recorded, listings stored) for the current league."""
        if not self.db:
            return 0, 0
        try:
            with self.lock:
                a = self.db.execute("SELECT COUNT(*) FROM obs WHERE league=?", (self.cur(),)).fetchone()[0]
                b = self.db.execute("SELECT COUNT(*) FROM listings WHERE league=?", (self.cur(),)).fetchone()[0]
            return a, b
        except Exception:
            return 0, 0

    @staticmethod
    def _fits(filt, vals):
        for sid, op, t in filt:
            v = vals.get(sid)
            if sid not in vals:
                return False
            if op == "min" and (v is None or v < t):
                return False
            if op == "max" and (v is None or v > t):
                return False
        return True

    def lower_bound(self, base, vals, hours=24):
        """Earlier searches (>= 2 listings) whose every filter this item also meets -> the dearest 'cheapest listing'."""
        if not self.db:
            return None
        try:
            with self.lock:
                rows = self.db.execute("SELECT ts, filters, n, floor_div FROM obs WHERE base=? AND league=? AND ts>? AND n>=2 "
                                       "AND floor_div IS NOT NULL", (base, self.cur(), time.time() - hours * 3600)).fetchall()
            best = None
            for ts, filters, n, floor in rows:
                filt = json.loads(filters)
                if filt and self._fits(filt, vals) and (best is None or floor > best["floor"]):
                    best = {"floor": floor, "ts": ts, "n": n, "mods": len(filt)}
            return best
        except Exception:
            return None

    def combos(self, limit=500):
        """[(base, filters, seen, best floor, (ts, n, floor, est))] - the combinations with the dearest 'cheapest listing'."""
        if not self.db:
            return []
        try:
            with self.lock:
                rows = self.db.execute("SELECT base, key, ts, n, floor_div, est_div FROM obs WHERE league=? ORDER BY ts",
                                       (self.cur(),)).fetchall()
        except Exception:
            return []
        agg = {}
        for base, key, ts, n, fl, es in rows:
            a = agg.setdefault((base, key), {"seen": 0, "best": None, "last": None})
            a["seen"] += 1
            if fl is not None:
                a["best"] = max(a["best"] or 0, fl)
            a["last"] = (ts, n, fl, es)
        out = [(b, json.loads(k), a["seen"], a["best"], a["last"]) for (b, k), a in agg.items() if a["best"] is not None]
        return sorted(out, key=lambda r: -r[3])[:limit]

    def mod_summary(self, limit=1000):
        """[(base, sid, listings seen, cheapest, median, highest, last seen)] from every listing ever fetched."""
        if not self.db:
            return []
        try:
            with self.lock:
                rows = self.db.execute("SELECT base, seen, price_div, sids FROM listings WHERE league=?", (self.cur(),)).fetchall()
        except Exception:
            return []
        agg = {}
        for base, seen, price, sids in rows:
            for sid in json.loads(sids):
                a = agg.setdefault((base, sid), {"p": [], "last": 0})
                a["p"].append(price)
                a["last"] = max(a["last"], seen)
        out = [(b, sid, len(a["p"]), min(a["p"]), statistics.median(a["p"]), max(a["p"]), a["last"]) for (b, sid), a in agg.items()]
        return sorted(out, key=lambda r: -r[5])[:limit]

    def exact(self, base, filt, hours):
        if not self.db:
            return []
        try:
            with self.lock:
                return self.db.execute("SELECT ts, n, floor_div, est_div FROM obs WHERE base=? AND key=? AND league=? AND ts>? "
                                       "AND est_div IS NOT NULL", (base, json.dumps(filt), self.cur(), time.time() - hours * 3600)).fetchall()
        except Exception:
            return []

    # ---------------- learning: which mods matter
    def stats(self, league=None):
        """{(base, sid): {n, med, lift, tier}}.  lift = median ask of listings WITH the mod / median ask of listings
        WITHOUT it (same base), so a mod that merely appears on everything scores about 1.  A mod counts as 'high' when
        it has enough listings, a lift of 2 or more, and its own median ask is at least your 'valuable mod' amount."""
        if not self.db:
            return {}
        league = self.cur() if league is None else league
        try:
            with self.lock:
                rows = self.db.execute("SELECT base, price_div, sids FROM listings WHERE league=? ORDER BY seen DESC LIMIT 30000",
                                       (league,)).fetchall()
        except Exception:
            return {}
        by_base = {}
        for base, price, sids in rows:
            if price is not None:
                by_base.setdefault(base, []).append((price, set(json.loads(sids))))
        good = float(SETTINGS.get("good_div", 0.5))
        out = {}
        for base, items in by_base.items():
            by_sid = {}
            for price, sids in items:
                for sid in sids:
                    by_sid.setdefault(sid, []).append(price)
            for sid, with_ in by_sid.items():
                without = [p for p, sids in items if sid not in sids]
                med = statistics.median(with_)
                lift = (med / max(statistics.median(without), 1e-9)) if len(without) >= MIN_WITHOUT else None
                decided = lift is not None and len(with_) >= MIN_WITH
                out[(base, sid)] = {"n": len(with_), "med": med, "lift": lift, "decided": decided,
                                    "tier": "high" if decided and lift >= HIGH_LIFT and med >= good else ""}
        return out

    _stats_cache = (0.0, "", {})

    def cached_stats(self):
        """stats() as of the last refresh_learned (every 20 listings fetched) - cheap enough for the screens to ask often."""
        t, lg, st = self._stats_cache
        if lg != self.cur():
            self.refresh_learned()
            t, lg, st = self._stats_cache
        return st

    def mods_known(self):
        return len(self.cached_stats())

    def mod_median(self, base, sid):
        """Median asking price (divines) of the stored listings that carry this mod, or None if fewer than 3."""
        st = self.cached_stats().get((base, sid))
        return st["med"] if st and st["n"] >= 3 else None

    def import_old_modbook(self, modbook, good):
        """One time: mods the old Mod book had found valuable (cheapest listing at least `good` divines) carry on as
        'learned high', unless this league's own data says otherwise. The old file itself is left alone."""
        if not self.db:
            return 0
        n = 0
        try:
            with self.lock:
                for e in modbook.values():
                    if e.get("sid") and e.get("floor") is not None and e["floor"] >= good and impact_of(e.get("text", "")) != "ignore":
                        cur = self.db.execute("INSERT OR IGNORE INTO legacy VALUES (?,?,?,?,?)",
                                              (e["sid"], 0.0, int(e.get("total") or 0), "the old mod book", e.get("text", "")))
                        n += cur.rowcount
                self.db.commit()
        except Exception:
            return 0
        self.refresh_learned()
        return n

    def legacy_rows(self):
        if not self.db:
            return {}
        try:
            with self.lock:
                return {sid: {"lift": lift, "n": n, "league": lg, "text": txt}
                        for sid, lift, n, lg, txt in self.db.execute("SELECT sid, lift, n, league, text FROM legacy")}
        except Exception:
            return {}

    def refresh_learned(self):
        """Rebuild LEARNED (stat id -> learned priority) from this league's listings plus what earlier leagues taught."""
        new = {sid: {"tier": "high", "lift": r["lift"], "n": r["n"], "from": r["league"]} for sid, r in self.legacy_rows().items()}
        decided, high = set(), {}
        every = self.stats()
        self._stats_cache = (time.time(), self.cur(), every)               # the screens read this copy (no re-counting)
        for (base, sid), st in every.items():
            if st["decided"]:
                decided.add(sid)
            if st["tier"] == "high" and (sid not in high or st["lift"] > high[sid]["lift"]):
                high[sid] = st
        for sid in decided:                                # this league has enough data to overrule an old verdict
            new.pop(sid, None)
        for sid, st in high.items():
            new[sid] = {"tier": "high", "lift": st["lift"], "n": st["n"], "from": None}
        LEARNED.clear()                                    # in place: other modules hold this dict
        LEARNED.update(new)
        rebuild_community(self)
        return len(new)

    def snapshot_league(self, league):
        """A league is ending for us: remember which mods were high in it, so the next league starts with that knowledge."""
        if not self.db or not league:
            return 0
        best = {}
        for (base, sid), st in self.stats(league).items():
            if st["tier"] == "high" and (sid not in best or st["lift"] > best[sid]["lift"]):
                best[sid] = st
        try:
            with self.lock:
                for sid, st in best.items():
                    self.db.execute("INSERT OR REPLACE INTO legacy VALUES (?,?,?,?,?)",
                                    (sid, st["lift"], st["n"], league, SIDTEXT.get(sid, "")))
                self.db.commit()
        except Exception:
            return 0
        self.refresh_learned()
        return len(best)

    def has_data(self, league):
        if not self.db:
            return False
        try:
            with self.lock:
                return bool(self.db.execute("SELECT 1 FROM obs WHERE league=? LIMIT 1", (league,)).fetchone())
        except Exception:
            return False

    # ---------------- comparables, accuracy score, your own listed prices
    def comparables(self, base, filt, max_mods, exclude=(), days=7):
        """Prices (divines, cheapest first) of stored listings that carry every searched mod at the searched rolls and
        no more than max_mods mods in all. Listings in `exclude` (the ones this very pricing just fetched) are skipped,
        so the guess can't peek at the answer."""
        if not self.db or not filt:
            return []
        try:
            with self.lock:
                rows = self.db.execute("SELECT id, price_div, sids, vals FROM listings WHERE base=? AND league=? AND seen>?",
                                       (base, self.cur(), time.time() - days * 86400)).fetchall()
        except Exception:
            return []
        out = []
        for id_, price, sids, vals in rows:
            if price is None or id_ in exclude:
                continue
            sids, vals = set(json.loads(sids)), json.loads(vals or "{}")
            if len(sids) > max_mods:
                continue
            ok = True
            for sid, op, t in filt:
                v = vals.get(sid)
                if sid not in sids or (op == "min" and (v is None or v < t)) or (op == "max" and (v is None or v > t)):
                    ok = False
                    break
            if ok:
                out.append(price)
        return sorted(out)

    @staticmethod
    def guess(prices):
        """The model's price from comparables: the same recipe as a real search (median of the cheapest 5)."""
        return statistics.median(prices[:5]) if len(prices) >= 3 else None

    def log_prediction(self, base, pred, actual, n_comp):
        if not self.db or pred is None or actual is None or actual <= 0:
            return
        try:
            with self.lock:
                self.db.execute("INSERT INTO preds VALUES (?,?,?,?,?,?)", (time.time(), self.cur(), base, pred, actual, n_comp))
                self.db.commit()
        except Exception:
            pass

    def accuracy(self, base=None, tol=0.25, limit=300):
        """-> (checked guesses, how many landed within tol of the real search, median guess/real ratio)."""
        if not self.db:
            return 0, 0, None
        try:
            with self.lock:
                q = "SELECT pred, actual FROM preds WHERE league=?" + (" AND base=?" if base else "") + " ORDER BY ts DESC LIMIT ?"
                rows = self.db.execute(q, (self.cur(), *( (base,) if base else () ), limit)).fetchall()
        except Exception:
            return 0, 0, None
        if not rows:
            return 0, 0, None
        hits = sum(1 for p, a in rows if abs(p / a - 1) <= tol)
        return len(rows), hits, statistics.median(p / a for p, a in rows)

    def model_trusted(self, base):
        """The 99 percent rule: 100 checked guesses for this base, 99 or more of them within 20 percent."""
        n, hits, _ = self.accuracy(base, 0.20, 100)
        return n >= 100 and hits / n >= 0.99

    def save_listed(self, item, est, listed_div):
        if not self.db or listed_div is None:
            return
        try:
            mods = [m for m in item["mods"] if m.get("sid")]
            sids = sorted({m["sid"] for m in mods})
            vals = {m["sid"]: m["value"] for m in mods if m.get("value") is not None}
            sig = f"{self.cur()}|{item['name']}|{json.dumps(sids)}|{json.dumps(vals, sort_keys=True)}"
            with self.lock:
                self.db.execute("INSERT OR REPLACE INTO listed VALUES (?,?,?,?,?,?,?,?,?)",
                                (sig, time.time(), self.cur(), item["base"], item["name"], json.dumps(sids), json.dumps(vals),
                                 est, listed_div))
                self.db.commit()
        except Exception:
            pass

    def my_listed(self, base, filt, max_mods):
        """Prices (divines) you yourself listed for items carrying these mods at least at these rolls, this league."""
        if not self.db or not filt:
            return []
        try:
            with self.lock:
                rows = self.db.execute("SELECT sids, vals, listed_div FROM listed WHERE base=? AND league=?",
                                       (base, self.cur())).fetchall()
        except Exception:
            return []
        out = []
        for sids, vals, price in rows:
            sids, vals = set(json.loads(sids)), json.loads(vals or "{}")
            if len(sids) > max_mods:
                continue
            if all(sid in sids and (op is None or (vals.get(sid) is not None and (vals[sid] >= t if op == "min" else vals[sid] <= t)))
                   for sid, op, t in filt):
                out.append(price)
        return sorted(out)

    def listed_vs_estimate(self):
        """-> (how many of your listings had an app estimate, median listed/estimate ratio)."""
        if not self.db:
            return 0, None
        try:
            with self.lock:
                rows = self.db.execute("SELECT est_div, listed_div FROM listed WHERE league=? AND est_div>0 AND listed_div>0",
                                       (self.cur(),)).fetchall()
        except Exception:
            return 0, None
        return (len(rows), statistics.median(l / e for e, l in rows)) if rows else (0, None)

    def accuracy_text(self):
        n, hits, ratio = self.accuracy()
        if n < 5:
            txt = f"Model check: {n} guess{'es' if n != 1 else ''} checked so far - too few to say anything (it needs 100 per tablet type before it may set a price)."
        else:
            txt = (f"Model check: its own guess landed within 25% of the real search {hits} of {n} times ({hits / n:.0%})"
                   f", typical guess {ratio:.2f}x the real price. It may only set a price at 100 checks and 99%.")
        k, r = self.listed_vs_estimate()
        if k >= 3:
            txt += f"  You listed {r:.2f}x the app's estimate (median of {k})."
        return txt


MARKET = Market()


if not SETTINGS.get("modbook_imported") and MODBOOK:
    MARKET.import_old_modbook(MODBOOK, float(SETTINGS.get("good_div", 0.5)))
    SETTINGS["modbook_imported"] = True
