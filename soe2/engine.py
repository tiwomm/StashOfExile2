"""The background thread that does all network work, one request at a time.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import os
import queue
import random
import re
import statistics
import threading
import time
from .config import BASE, load_json, P, save_json, SETTINGS
from .util import mmss
from .net import call, STATUS
from .rates import RATES
from .mods import DUPS, find_stat, norm, pretty, vfilter
from . import gear, waystone
from .trade import (cheapest_real,
    _flt, build_sidtext, estimate, fetch_rich, listing_rules, mod_impact, search_ids, unconvertible,
    uses_filter, verify_listings,
)
from .market import MARKET, Market
from .pricefmt import confidence, fmt_div, fmt_price
from .wealth import WealthJobs
from .tabreader import TabReaderJobs


def spread_of(stages, league):
    """How far apart the cheapest listings are, per search (2.3.0). Before, the cheapest 5 of SEVERAL different
    searches were thrown together - a stricter and a looser search naturally differ - and one price-fixer listing
    (1 chaos among 2-divine listings) was enough, so many jewels and tablets came out as "check by hand".
    Now each search is measured on its own, after leaving out listings far below the rest (under a fifth of their
    median) or far above them (over five times it: a jewel with better extra mods, or a "make me an offer" price).
    -> (largest ratio, cheapest kept (amount, currency), dearest kept) or (None, None, None)."""
    worst = (None, None, None)
    for st in stages:
        vals = []
        for amt, cur in (st.get("prices") or [])[:5]:
            d = RATES.to_div(amt, cur, league)
            if d is not None and d > 0:
                vals.append((d, (amt, cur)))
        if len(vals) < 2:
            continue
        med = statistics.median(v for v, _ in vals)
        kept = [v for v in vals if med / 5 <= v[0] <= med * 5]
        if len(kept) < 2:
            kept = vals                                    # e.g. two listings, 1 chaos and 30 divine: say so
        lo, hi = min(kept), max(kept)
        r = hi[0] / lo[0]
        if worst[0] is None or r > worst[0]:
            worst = (r, lo[1], hi[1])
    return worst


# ------------------------------------------------------------------ background engine
class Engine(TabReaderJobs, WealthJobs, threading.Thread):
    """One background thread does all network work. Lower priority number = sooner."""

    def __init__(self, records, ui_q):
        super().__init__(daemon=True)
        self.records, self.ui_q = records, ui_q
        self.jobs = queue.PriorityQueue()
        self.seq = 0
        self.table = None
        self.logged_unmatched = set()
        self.paused = False
        self.lock = threading.Lock()

    def add(self, prio, *job):
        with self.lock:
            self.seq += 1
            self.jobs.put((prio, self.seq, job))

    def run(self):
        while True:
            while self.paused:
                time.sleep(0.3)
            try:
                _, _, job = self.jobs.get(timeout=2)
            except queue.Empty:
                continue
            try:
                getattr(self, "do_" + job[0])(*job[1:])
            except Exception as e:
                self.ui_q.put(("error", job[0], str(e), job[1] if len(job) > 1 else None))
            self.ui_q.put(("queue",))

    # ---- jobs
    def do_init(self):
        try:
            leagues = [l["id"] for l in call("GET", BASE + "/data/leagues")["result"]]
        except Exception:
            leagues = []
        self.ui_q.put(("leagues", leagues))
        try:
            self.table = self._load_stats()
        except Exception as e:
            self.ui_q.put(("error", "init", f"Couldn't download the trade site's mod list ({e}). Check your internet.", None))
        self._load_static()
        self.ui_q.put(("ready",))

    def _load_static(self):
        """2.16.0: the trade site's list of currencies (ids for every currency a stash tab can be priced in), once a
        day like the mod list. Never stops the app: without it the built-in currencies stay."""
        from .wealth import set_trade_currencies
        try:
            cache = P("trade_static.json")
            if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 86400:
                data = load_json("trade_static.json", {})
            else:
                data = call("GET", BASE + "/data/static")
                save_json("trade_static.json", data)
            set_trade_currencies(data)
            self.ui_q.put(("currencies_loaded",))          # 2.40.0: Stash tab's box can show the saved currency
        except Exception:
            pass

    def _load_stats(self):
        cache = P("stats_cache.json")
        if os.path.exists(cache) and os.path.exists(P("stats_dups.json")) and time.time() - os.path.getmtime(cache) < 86400:
            DUPS.clear()
            DUPS.update(load_json("stats_dups.json", {}))
            table = load_json("stats_cache.json", {})
            build_sidtext(table)
            return table
        STATUS("Downloading the trade site's mod list (once a day)...")
        data = call("GET", BASE + "/data/stats")
        table, same = {}, {}
        for group in data["result"]:
            for e in group["entries"]:
                k = norm(e["text"])
                table.setdefault(k, {}).setdefault(group.get("id"), e["id"])
                same.setdefault((k, group.get("id")), []).append(e["id"])
        dups = {}
        for ids in same.values():
            if len(ids) > 1:
                for i in ids:
                    dups[i] = ids
        save_json("stats_cache.json", table)
        save_json("stats_dups.json", dups)
        DUPS.clear()
        DUPS.update(dups)
        build_sidtext(table)
        return table

    def do_resolve(self, rid):
        rec = self.records.get(rid)
        if not rec:
            return
        self.resolve_rec(rec)
        self.ui_q.put(("resolved", rid))
        self.add(2, "price", rid)

    def resolve_rec(self, rec):
        """Match every mod of a record's item to its trade-site stat (2.0: also used for Wealth items)."""
        if self.table is None:
            self.table = self._load_stats()      # first attempt failed (no internet?) - try once more
        item = rec["item"]
        if item.get("gear"):                     # 1.41: gear mods were matched from the game-data library already
            for m in item["mods"]:
                m["key"] = f"{item['base']}|{m['sid']}" if m.get("sid") else None
            rec["resolved"] = True
            return
        for m in item["mods"]:
            m["sid"], m["group"], flipped, info = find_stat(m["text"], m["flags"], self.table, ranged=m["lo"] is not None)
            m["guess"], m["note"] = (None, info) if m["sid"] else (info, None)
            m["key"] = f"{item['base']}|{m['sid']}" if m["sid"] else None
            m["novalue"] = bool(m["sid"] and info and info.startswith("singular wording"))   # no number to filter on
            if flipped and m["value"] is not None:
                m["value"] = -m["value"]
                if m["lo"] is not None and m["hi"] is not None:
                    m["lo"], m["hi"] = -m["hi"], -m["lo"]
            if not m["sid"] and m["text"] not in self.logged_unmatched:
                self.logged_unmatched.add(m["text"])
                try:
                    with open(P("unmatched_mods.txt"), "a", encoding="utf-8") as f:
                        f.write(f"{m['text']}\t| closest on trade site: {m['guess']}\n")
                except Exception:
                    pass
        rec["resolved"] = True

    def do_price(self, rid):
        rec = self.records.get(rid)
        if not rec:
            return
        self.price_rec(rec, lambda: self.ui_q.put(("priced", rid)))

    def price_rec(self, rec, tell=lambda: None):
        """Price a record (its mods resolved first). tell() is called whenever its state changes.
        2.4.1: the item's own search filters (rec["opts"], set in the item panel) apply to every search for it."""
        from .trade import use_opts
        use_opts(rec.get("opts"))
        try:
            return self._price_rec(rec, tell)
        finally:
            use_opts(None)

    def _price_rec(self, rec, tell):
        item, league = rec["item"], SETTINGS["league"]
        if not league:
            rec.update(state="error", label="pick a league first", total=0, prices=[], est=None, qid=None)
            tell()
            return
        rec["state"] = "pricing"
        tell()
        if item.get("gear"):
            _status, _age, hours = listing_rules()
            out = self._price_gear(rec, hours, SETTINGS["min_results"])
            out.setdefault("model", "")
            rec.update(state="done", priced_at=time.time(), **out)
            tell()
            return
        impacts = [(m, mod_impact(rec, m)) for m in item["mods"]]
        ignored = sum(1 for _, i in impacts if i == "ignore")
        searchable = [(m, i) for m, i in impacts if i != "ignore" and m.get("sid")]
        unmatched = sum(1 for m, i in impacts if i != "ignore" and not m.get("sid"))
        note = f" · {ignored} low-impact mod{'s' if ignored != 1 else ''} ignored" if ignored else ""
        if not searchable:
            low = bool(ignored) and not unmatched
            rec.update(state="done", total=0, prices=[], est=None, qid=None, partial=False, skip=low, thin=False,
                       nomatch=False, stages=[], priced_at=time.time(),
                       label="only low-impact mods - not worth a search" if low else "no searchable mods")
            tell()
            return
        rec["skip"] = False
        _status, _age, hours = listing_rules()
        extra, uses_note = uses_filter(self.table, item["class"] == "Tablet", item.get("uses"))
        note += uses_note
        need = SETTINGS["min_results"]
        out = self._price_item(rec, searchable, extra, hours, need)
        out.setdefault("model", "")
        self._scale_for_uses(item, out)
        label = out.pop("label")
        if unmatched:
            label += f" · {unmatched} mod{'s' if unmatched != 1 else ''} not on the trade site"
            out["partial"] = True
        rec.update(state="done", label=label + note, priced_at=time.time(), **out)
        tell()

    def _price_item(self, rec, searchable, extra, hours, need):
        """Tablets and jewels, same flow:
             search 1: every affix that counts
             then, tablets: one search per prefix, each with ALL the suffixes (2+ prefixes needed)
                  jewels:  one search per affix left out (3+ affixes needed), the other affixes all kept
             price = plain average of the searches that found listings; none found = NO MATCH.
        A hybrid mod has several lines but is ONE affix."""
        item, league = rec["item"], SETTINGS["league"]
        groups, by = [], {}
        for pos, (m, imp) in enumerate(searchable):
            k = (m["kind"], m.get("mid", f"line{pos}"))
            if k not in by:
                by[k] = {"kind": m["kind"], "mods": [], "impact": imp}
                groups.append(by[k])
            by[k]["mods"].append(m)
            if imp == "high":
                by[k]["impact"] = "high"

        def worth(g):
            return max((MARKET.mod_median(item["base"], m.get("sid")) or 0) for m in g["mods"])

        def short(g):                                       # "#% increased Pack Size in Map" -> "Pack Size"
            t = re.sub(r"^[+\-#%\s]*(?:increased |reduced |more |less )?", "", pretty(g["mods"][0]["text"]), flags=re.I)
            return re.sub(r"\s+(?:found )?in Map$", "", t, flags=re.I)[:28]
        seen_sid, doubled = {}, []                          # one trade stat must not stand for two different mods:
        for g in groups:                                    # 2.3.0: search on it once (it used to stop the price check)
            keep = []
            for m in g["mods"]:
                other = seen_sid.setdefault(m["sid"], g)
                if other is not g:
                    doubled.append(pretty(m["text"]))
                else:
                    keep.append(m)
            g["mods"] = keep
        groups = [g for g in groups if g["mods"]]
        suffixes = [g for g in groups if g["kind"] == "Suffix"]
        prefixes = sorted([g for g in groups if g["kind"] != "Suffix"], key=lambda g: (g["impact"] != "high", -worth(g)))
        plan = [("all mods", suffixes + prefixes)]
        if item["class"] == "Tablet":                      # tablets: suffixes are always kept, prefixes rotate
            if suffixes and len(prefixes) >= 2:
                plan += [(f"suffixes + {short(p)}", suffixes + [p]) for p in prefixes[:2]]
        else:                                              # jewels (and later rings...): drop ONE affix at a time
            allg = suffixes + prefixes
            if len(allg) >= 3:
                from .mods import tier_key, tier_rank                  # 2.20.0: the lowest tier is left out first
                order = sorted(reversed(allg), key=lambda g: -min(tier_rank(tier_key(norm(m["text"]))) for m in g["mods"]))
                plan += [(f"without {short(d)}", [g for g in allg if g is not d]) for d in order]
        vals = {m["sid"]: m["value"] for g in groups for m in g["mods"] if m.get("sid")}
        mem = MARKET.lower_bound(item["base"], vals, SETTINGS.get("memory_hours", 24) or 24)
        filt_all = Market.filters_of([m for g in plan[0][1] for m in g["mods"]])
        n_item_mods = len(item["mods"])
        if SETTINGS.get("model_shortcut") and MARKET.model_trusted(item["base"]) and random.random() >= 0.1:
            comp = MARKET.comparables(item["base"], filt_all, n_item_mods, days=2)     # 1 in 10 is still searched for real
            g_ = Market.guess(comp)
            if g_ is not None and len(comp) >= 5:
                n_, hits_, _r = MARKET.accuracy(item["base"], 0.20, 100)
                return dict(label=f"FROM MODEL: {len(comp)} similar stored listings from the last 2 days. The model has been "
                                  f"right {hits_} of its last {n_} checks - no search needed",
                            total=0, prices=[], est=g_, qid=None, partial=False, thin=False, nomatch=False, stages=[],
                            wide=False, manual=False, conf="High", conf_why=[f"model proven: {hits_} of {n_} guesses within 20%"],
                            memory="", model="")
        if SETTINGS.get("memory_shortcut"):                  # 5+ identical searches lately, all agreeing within 10 percent
            obs = MARKET.exact(item["base"], Market.filters_of([m for g in plan[0][1] for m in g["mods"]]),
                               SETTINGS.get("memory_hours", 24) or 24)
            ests = [o[3] for o in obs if o[1] >= 3]
            if len(ests) >= 5 and max(ests) / max(min(ests), 1e-9) <= 1.1:
                est = statistics.median(ests)
                return dict(label=f"FROM MEMORY: {len(ests)} identical searches in the last {SETTINGS.get('memory_hours', 24)} h "
                                  f"all agree ({fmt_div(min(ests))} to {fmt_div(max(ests))}) - no search needed",
                            total=0, prices=[], est=est, qid=None, partial=False, thin=False, nomatch=False, stages=[],
                            wide=False, manual=False, conf="High", conf_why=["identical searches agree"], memory="")
        stages, verify_tot = [], {"bad": 0, "unverifiable": False}
        for name, gs in plan:
            fs = [_flt(m) for g in gs for m in g["mods"]]
            total, ids, qid = search_ids(league, item["base"], fs + extra, None, None)   # Corrupted/Fractured/Desecrated = Any
            st = self._stage(item["base"], name, gs, total, ids, qid, hours, league, verify_tot)
            stages.append(st)
            if len(stages) == 1 and st["n"] >= need:       # search 1 found enough listings: that's the price, skip the rest
                break
        found = [s for s in stages if s["n"]]
        any_roll = False
        relaxed = None
        if not found and len(plan[0][1]) >= 2:                  # 2.20.0: leave out the lowest-tier mods, then the next
            from .mods import tier_key, tier_rank, TIER_ORDER
            for g in plan[0][1]:
                ranks = [tier_rank(tier_key(norm(m["text"]))) for m in g["mods"]]
                g["tier_rank"] = min(ranks + ([1] if g["impact"] == "high" else []))
            keep = list(plan[0][1])
            for _ in range(2):                                  # at most 2 more searches (the trade site's limits)
                low = max(g["tier_rank"] for g in keep)
                left = [g for g in keep if g["tier_rank"] != low]
                if not left or low <= 0:                        # never drop everything, never drop S
                    break
                dropped = [g for g in keep if g["tier_rank"] == low]
                keep = left
                fs = [_flt(m) for g in keep for m in g["mods"]]
                total, ids, qid = search_ids(league, item["base"], fs + extra, None, None)
                tname = TIER_ORDER[low] if low < len(TIER_ORDER) else "?"
                st = self._stage(item["base"], f"without {tname}-tier: " + ", ".join(short(g) for g in dropped), keep,
                                 total, ids, qid, hours, league, verify_tot, record=False)
                stages.append(st)
                relaxed = (relaxed or []) + [(tname, [short(g) for g in dropped])]
                if st["n"]:
                    found = [st]
                    break
            if not found:
                relaxed = None
        if not found:                                           # nothing at your rolls: once more with ANY value
            fs = [_flt(m, with_roll=False) for g in plan[0][1] for m in g["mods"]]
            total, ids, qid = search_ids(league, item["base"], fs + extra, None, None)
            st = self._stage(item["base"], "any roll", plan[0][1], total, ids, qid, hours, league, verify_tot, record=False)
            stages.append(st)
            found = [st] if st["n"] else []
            any_roll = bool(found)
        alone = None
        if not found and len(plan[0][1]) >= 2:                  # 2.3.0: still nothing - the best mod on its own
            best = sorted(plan[0][1], key=lambda g: (g["impact"] != "high", -worth(g)))[0]
            fs = [_flt(m) for m in best["mods"]]
            total, ids, qid = search_ids(league, item["base"], fs + extra, None, None)
            st = self._stage(item["base"], f"only {short(best)}", [best], total, ids, qid, hours, league, verify_tot,
                             record=False)
            stages.append(st)
            if st["n"]:
                found, any_roll, alone = [st], True, short(best)
        used = [s for s in stages if s["weight"]]
        if not found:
            return dict(label="no listings carry these mods - not priced", total=0, prices=[], est=None,
                        qid=stages[0]["qid"], partial=False, thin=False, nomatch=True, stages=stages,
                        conf="-", conf_why=[], memory=self._mem_text(mem))
        est = sum(s["est"] for s in used) / len(used) if used else None
        wide, ratio = False, None
        primary = found[0]
        thin = not any(s["n"] >= need for s in found)
        if relaxed:
            label = ("no listing has all these mods together - left out the "
                     + "; ".join(f"{t}-tier {', '.join(n)}" for t, n in relaxed)
                     + ", so it's a floor (those mods add to it)")
        elif alone:
            label = (f"no listing has all these mods together - priced on {alone} alone, so it's a floor (the other "
                     f"mods add to it)")
        elif any_roll:
            label = ("nothing found at your rolls - searched with ANY roll: price is a floor (a high roll can be worth more)")
        elif len(stages) == 1:
            label = stages[0]["name"] + (" (enough listings, other searches skipped)" if len(plan) > 1 else "")
        else:
            label = f"average of {len(used)} of {len(stages)} searches: " + "  |  ".join(f"{s['name']} ({s['n']})" for s in used)
        if thin:
            label += " · few listings"
        skipped = sorted({c for s_ in stages for c in s_.get("unk", ())})
        if skipped:
            label += " · ⚠ listings priced in " + ", ".join(skipped) + " left out (no exchange rate)"
        spread = SETTINGS.get("spread_warn") or 0
        rough = False
        if used:
            ratio, lo, hi = spread_of(used, league)
            if spread and ratio and ratio >= spread:          # 2.3.0: a rough price instead of no price
                label = (f"ROUGH PRICE: the listings that match range from {fmt_price(lo)} to {fmt_price(hi)}, so "
                         f"worth a look by hand · " + label)
                rough = True
        if doubled:
            label += " · " + ", ".join(doubled[:2]) + " is the same trade-site stat as another mod: searched once"
        conflict = bool(mem and est is not None and est < 0.5 * mem["floor"])
        if conflict:
            label += f" · ⚠ earlier searches for these mods found listings from {fmt_div(mem['floor'])}"
        model_txt, model_conflict = self._model_review(item, filt_all, n_item_mods, stages, need, any_roll, est, wide)
        conflict = conflict or model_conflict
        ages = [s_["age_h"] for s_ in used if s_.get("age_h") is not None]
        conf, why = confidence(max((s_["n"] for s_ in used), default=0), len(used) > 1 and not any_roll, any_roll, ratio,
                               verify_tot["unverifiable"], verify_tot["bad"], max(ages) if ages else None, conflict, skipped)
        if rough:
            conf = "Low"
            why = ["matching listings are priced far apart"] + [w for w in why if "apart" not in w]
        return dict(label=label, total=primary["total"], prices=primary["prices"], qid=primary["qid"], est=est,
                    partial=any_roll or bool(relaxed), thin=thin, nomatch=False, stages=stages, wide=wide, manual=wide,
                    conf=conf, conf_why=why, memory=self._mem_text(mem), model=model_txt, spread=ratio)

    FULL_USES = 10

    def _scale_for_uses(self, item, out):
        """1.45: a used tablet. The search is for full 10-use tablets; the price is scaled by the uses left
        (5 of 10 uses -> 50% of the 10-use price), and the record says so."""
        out["uses_note"] = ""
        uses = item.get("uses")
        if item.get("class") != "Tablet" or uses is None or uses >= self.FULL_USES or out.get("est") is None:
            return
        share = max(0, uses) / self.FULL_USES
        full = out["est"]
        out["full_est"] = full
        out["est"] = full * share
        out["uses_note"] = (f"Your tablet has {uses} of {self.FULL_USES} uses left, so it is priced at {share:.0%} of a "
                            f"full {self.FULL_USES}-use tablet ({fmt_div(full)} × {share:.0%} = {fmt_div(out['est'])}). "
                            f"The listings below are {self.FULL_USES}-use tablets.")
        out["label"] = f"{uses}/{self.FULL_USES} uses: {share:.0%} of the {self.FULL_USES}-use price ({fmt_div(full)}) · " + out["label"]

    def _price_gear(self, rec, hours, need):
        """1.41: any piece of gear. ★ mods and totals are always searched; ☑ mods may be dropped one or two at a time
        (a "count" search: at least N of them) until enough listings are found. At most 3 searches."""
        item, league = rec["item"], SETTINGS["league"]
        valid = self._valid_ids()
        must, opt, unknown, ignored = [], [], 0, 0
        for m in item["mods"]:
            imp = mod_impact(rec, m)
            if imp == "ignore":
                ignored += 1
                continue
            if not m.get("sid"):
                unknown += 1
                continue
            if valid and not str(m["sid"]).startswith(("equip:", "map:")):  # 1.42: only ids the trade site's own list has
                m["search_ids"] = [i for i in (m.get("ids") or [m["sid"]]) if i in valid]
                if not m["search_ids"]:
                    unknown += 1
                    continue
            (must if imp == "high" else opt).append(m)
        blank = dict(total=0, prices=[], est=None, qid=None, partial=False, thin=False, nomatch=False, stages=[],
                     wide=False, manual=False, conf="-", conf_why=[], memory="", skip=False)
        if not must and not opt and item["rarity"] not in ("Unique", "Normal"):
            return dict(blank, label="nothing ticked to search on" + (f" · {unknown} mods not on the trade site" if unknown else ""))
        values = {id(m): vfilter(m) for m in must + opt}
        check = [m for m in must if m.get("group") not in ("total", "pseudo")]     # listings' mod lines are checked for these
        stages, verify_tot = [], {"bad": 0, "unverifiable": False}
        if item.get("waystone"):
            steps = waystone.plan(must, opt)
        else:
            steps = [(name, must, opt, k, values) for name, k in gear.ladder(len(opt))]
        for name, must_s, opt_s, k, vals in steps:
            q = gear.build_query(item, must_s, opt_s, k, vals)
            try:
                total, ids, qid = gear.run_search(league, q)
            except RuntimeError as e:
                if not str(e).startswith("400 "):
                    raise
                q = gear.build_query(item, must_s, opt_s, k, vals, plain=True)   # refused: once more, the simplest form
                total, ids, qid = gear.run_search(league, q)
            st = self._stage(item["base"], name, [{"mods": check}], total, ids, qid, hours, league, verify_tot, record=False)
            st["k"] = k
            stages.append(st)
            if st["n"] >= need:
                break
        if not check:                       # nothing to check the listings' mod lines against (totals only): not a warning
            verify_tot["unverifiable"] = False
        enough = [s_ for s_ in stages if s_["n"] >= need and s_["est"] is not None]
        some = [s_ for s_ in stages if s_["n"] and s_["est"] is not None]
        how = waystone.summary(item) if item.get("waystone") else gear.summary(item)
        if not some:
            return dict(blank, label=f"no listings match - not priced ({how.lower()})", qid=stages[0]["qid"] if stages else None,
                        nomatch=True, stages=stages)
        chosen = (enough or some)[0]
        step = stages.index(chosen)
        for s_ in stages:
            s_["weight"] = 1 if s_ is chosen else 0
        thin = chosen["n"] < need
        dropped = len(opt) - chosen["k"]
        label = chosen["name"] if len(steps) > 1 or opt else "search"
        if item.get("waystone") and step > 0:
            label = chosen["name"] + " (your exact values found too few)"
        elif dropped:
            label = f"{len(opt) - dropped} of {len(opt)} ☑ mods had to match (exact search found too few)"
        label += f" · {how.lower()}"
        if thin:
            label += " · few listings"
        if unknown:
            label += f" · {unknown} mod{'s' if unknown != 1 else ''} not on the trade site"
        if ignored:
            label += f" · {ignored} line{'s' if ignored != 1 else ''} not searched"
        skipped = sorted(set(chosen.get("unk", ())))
        if skipped:
            label += " · ⚠ listings priced in " + ", ".join(skipped) + " left out (no exchange rate)"
        ratio, lo, hi = spread_of([chosen], league)
        est, wide = chosen["est"], False
        if item.get("waystone") and thin and chosen["prices"]:     # 2.41.0: few listings - the cheapest real offer
            low = cheapest_real(chosen["prices"], league)
            if low is not None and est is not None and low < est:
                est = low
                label += " · few listings: priced at the cheapest"
        status_any = SETTINGS.get("status") == "Any"               # 2.41.0: say when offline sellers count
        if status_any:
            label += " · Listings: Any counts offline / whisper-only sellers (Instant Buyout is closer to real sales)"
        spread = SETTINGS.get("spread_warn") or 0
        rough = bool(spread and ratio and ratio >= spread)
        if rough:                                          # 2.3.0: a rough price instead of no price
            label = (f"ROUGH PRICE: the listings that match range from {fmt_price(lo)} to {fmt_price(hi)}, so worth a "
                     f"look by hand · " + label)
        conf, why = confidence(chosen["n"], step > 0, False, ratio, verify_tot["unverifiable"], verify_tot["bad"],
                               chosen.get("age_h"), False, skipped)
        if status_any and conf == "High":
            conf = "Medium"
        if status_any:
            why = list(why) + ["Listings: Any - offline sellers' asks count too"]
        if item.get("waystone") and thin and conf == "High":         # (a handful of listings is never "High")
            conf = "Medium"
        if rough:
            conf = "Low"
        return dict(blank, label=label, total=chosen["total"], prices=chosen["prices"], qid=chosen["qid"], est=est,
                    partial=False, thin=thin, stages=stages, wide=wide, manual=wide, conf=conf, conf_why=why,
                    spread=ratio)

    def _valid_ids(self):
        """Every stat id on the trade site's downloaded list (empty if it couldn't be downloaded: then don't filter)."""
        if getattr(self, "_valid_for", None) is not self.table:
            ids = set()
            for groups in (self.table or {}).values():
                ids.update(groups.values())
            for i, same in DUPS.items():
                ids.add(i)
                ids.update(same)
            if len(ids) < 500:              # a partial / odd list: filtering by it would throw away good mods
                ids = set()
            self._valid, self._valid_for = ids, self.table
        return self._valid

    @staticmethod
    def _model_review(item, filt_all, n_item_mods, stages, need, any_roll, est, wide):
        """After the real search: what would the stored listings have said? Keep score, and return
        (plain text for the side panel, True if the model clearly disagrees and has earned some trust)."""
        base = item["base"]
        seen_ids = {i for s in stages for i in s.get("ids", [])}
        comp = MARKET.comparables(base, filt_all, n_item_mods, exclude=seen_ids, days=2)
        pred = Market.guess(comp)
        bits = []
        conflict = False
        first = stages[0] if stages else None
        if pred is not None and not any_roll and first and first["n"] >= need and first.get("est"):
            MARKET.log_prediction(base, pred, first["est"], len(comp))        # guess vs the real all-mods search
        if pred is not None:
            bits.append(f"Model: {len(comp)} similar stored listings (last 2 days) would have said about {fmt_div(pred)}.")
            n_, hits_, _r = MARKET.accuracy(base)
            if est is not None and not wide and n_ >= 20 and hits_ / n_ >= 0.7 and est < 0.5 * pred:
                conflict = True
                bits.append("⚠ The model has been mostly right lately and expected much more than this search found.")
        elif len(comp) > 0:
            bits.append(f"Model: only {len(comp)} similar stored listing{'s' if len(comp) != 1 else ''} - too few to guess from.")
        mine = MARKET.my_listed(base, filt_all, n_item_mods)
        if mine:
            bits.append(f"You listed similar items at {fmt_div(mine[0])}" + (f" to {fmt_div(mine[-1])}" if len(mine) > 1 and mine[-1] != mine[0] else "") + ".")
        return " ".join(bits), conflict

    @staticmethod
    def _mem_text(mem):
        if not mem:
            return ""
        return (f"Memory: an earlier search ({mmss(time.time() - mem['ts'])} ago, {mem['n']} listings, {mem['mods']} of these mods) "
                f"found listings from {fmt_div(mem['floor'])}.")

    def _stage(self, base, name, gs, total, ids, qid, hours, league, verify_tot, record=True):
        """One search -> fetch -> check the listings really carry the mods -> remember it."""
        mods = [m for g in gs for m in g["mods"]]
        rich = fetch_rich(qid, ids, hours) if total > 0 else []
        kept, info = verify_listings(rich, mods)
        if not info["unverifiable"]:
            verify_tot["bad"] += info["bad"]
        if info["unverifiable"] or (info["unknown"] and not info["ok"]):     # we couldn't confirm what these listings carry
            verify_tot["unverifiable"] = True
        prices = [r["price"] for r in kept]
        st = {"name": name, "total": total, "n": len(prices), "qid": qid, "prices": prices, "est": estimate(prices, league),
              "verify": info, "unk": unconvertible(prices, league)}
        st["weight"] = 1 if st["n"] and st["est"] is not None else 0
        st["ids"] = [r["id"] for r in rich if r.get("id")]            # so the model's guess can't peek at these listings
        ages = sorted((time.time() - r["ts"]) / 3600 for r in kept)
        st["age_h"] = ages[len(ages) // 2] if ages else None
        from .trade import current_opts
        if record and not current_opts():          # 2.4.1: a search narrowed by hand doesn't teach the Mod book
            MARKET.record(base, Market.filters_of(mods), name, total, kept, st["est"])
        return st
