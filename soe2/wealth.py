"""Wealth tracker: priced tabs, syncing them through the trade site, poe.ninja prices, snapshots.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import json
import os
import re
import requests
import threading
import time
from .config import APP_VERSION, BASE, load_json, save_json, SETTINGS
from .net import call
from .rates import Rates
from .mods import JEWEL_KINDS, norm, strip_markup, TAB_KINDS
from . import gamedata


# ------------------------------------------------------------------ wealth: net worth of your marker-priced stash tabs (1.33)
# PoE 2 has no stash API that tools may use, so the Wealth page reads your stash through the trade site instead: set a
# public Premium stash tab to an exact price nobody would pay (e.g. 37916 Vaal Orbs) and the app searches for every
# listing on your account at that price, reads the items 10 at a time and values them with poe.ninja.
# Every request goes through the same call() and LIMITER as item pricing, as jobs on the same background thread with a
# LOWER priority, so an item you copy with Ctrl+Alt+C is always priced first and the two never compete for the limits.

WEALTH_PRIO = 5                    # item pricing uses 0-2, so it always jumps ahead of a running wealth sync


WEALTH_FINISH_PRIO = 9             # runs once every search and fetch of the sync is done


WEALTH_CURRENCIES = [("divine", "Divine Orb"), ("vaal", "Vaal Orb"), ("chaos", "Chaos Orb"), ("exalted", "Exalted Orb"),
                     ("regal", "Regal Orb"), ("annul", "Orb of Annulment"), ("alch", "Orb of Alchemy")]


# The trade site returns at most 100 listing ids per search. A tab holding more is searched again in slices: by
# category, then sub-category (ids as Sidekick uses them for PoE 2), then rarity, then item level.
WEALTH_CATS = {
    "weapon": ["weapon.bow", "weapon.crossbow", "weapon.claw", "weapon.dagger", "weapon.oneaxe", "weapon.onemace",
               "weapon.onesword", "weapon.flail", "weapon.sceptre", "weapon.spear", "weapon.staff", "weapon.rod",
               "weapon.talisman", "weapon.twoaxe", "weapon.twomace", "weapon.twosword", "weapon.wand", "weapon.warstaff"],
    "armour": ["armour.chest", "armour.boots", "armour.gloves", "armour.helmet", "armour.shield", "armour.focus",
               "armour.buckler", "armour.quiver"],
    "accessory": ["accessory.amulet", "accessory.belt", "accessory.ring"],
    "jewel": [],
    "flask": ["flask.life", "flask.mana"],
    "gem": ["gem.activegem", "gem.supportgem"],
    "map": ["map.waystone", "map.tablet", "map.logbook", "map.bosskey", "map.barya", "map.ultimatum"],
    "currency": [],
    "sanctum": ["sanctum.relic"],
}


WEALTH_RARITIES = ["normal", "magic", "rare", "unique"]


WEALTH_ILVLS = [(None, 44), (45, 64), (65, 74), (75, 79), (80, 81), (82, None)]


NINJA_ECON = (os.environ.get("SOE2_NINJA") or "https://poe.ninja") + "/poe2/api/economy"


NINJA_EXCHANGE_TYPES = ["Currency", "Fragments", "Abyss", "UncutGems", "LineageSupportGems", "Essences", "SoulCores",
                        "Idols", "Runes", "Ritual", "Expedition", "Delirium", "Breach", "Verisium"]


NINJA_ITEM_TYPES = ["UniqueWeapons", "UniqueArmours", "UniqueAccessories", "UniqueFlasks", "UniqueCharms", "UniqueJewels",
                    "UniqueSanctumRelics", "UniqueTablets", "PrecursorTablets"]


WEALTH_UA = f"StashOfExile2/{APP_VERSION} (personal Path of Exile 2 net worth tracker; prices refreshed at most hourly)"


def wealth_children(extra, level):
    """The slices to search when a search at `level` found more listings than one search can return.
    -> [(type filters, next level, label)]"""
    def with_(key, value):
        d = dict(extra)
        d[key] = value
        return d
    if level == "top":
        return [(with_("category", {"option": c}), "cat", c) for c in WEALTH_CATS]
    if level == "cat":
        subs = WEALTH_CATS.get(extra.get("category", {}).get("option"), [])
        if subs:
            return [(with_("category", {"option": s}), "sub", s.split(".", 1)[1]) for s in subs]
        level = "sub"
    if level == "sub":
        return [(with_("rarity", {"option": r}), "rarity", r) for r in WEALTH_RARITIES]
    if level == "rarity":
        out = []
        for lo, hi in WEALTH_ILVLS:
            v = {k: n for k, n in (("min", lo), ("max", hi)) if n is not None}
            out.append((with_("ilvl", v), "ilvl", f"ilvl {lo or 1}-{hi}" if hi else f"ilvl {lo}+"))
        return out
    return []


def wealth_query(account, tab, extra):
    filters = {"trade_filters": {"filters": {"account": {"input": account.strip()},
                                             "price": {"option": tab["currency"], "min": tab["amount"], "max": tab["amount"]}}}}
    if extra:
        filters["type_filters"] = {"filters": dict(extra)}
    # status "any": Premium tab listings are whisper listings, so they are not "securable" (instant buyout)
    return {"query": {"status": {"option": "any"}, "filters": filters}, "sort": {"price": "asc"}}


def wealth_trade_url(league, qid):
    return f"https://www.pathofexile.com/trade2/search/poe2/{requests.utils.quote(league)}/{qid}"


def _item_level_prop(it):
    for p in it.get("properties") or []:
        if str(p.get("name", "")).strip().lower() == "level":
            try:
                return int(re.findall(r"\d+", str(p["values"][0][0]))[0])
            except Exception:
                return None
    return None


RARITY_OF_FRAME = {0: "Normal", 1: "Magic", 2: "Rare", 3: "Unique"}
MOD_SOURCES = (("explicit", "explicitMods", ""), ("fractured", "fracturedMods", "Fractured "),
               ("desecrated", "desecratedMods", "Desecrated "), ("crafted", "craftedMods", "Crafted "))


def _kind_guess(line, cls_text):
    """Prefix or Suffix for a mod line when the listing doesn't say: tabs.txt / jewels.txt know (tablets, jewels)."""
    k = norm(line)
    kinds = (TAB_KINDS if "tablet" in cls_text.lower() else JEWEL_KINDS).get(k) or set()
    return next(iter(kinds)) if len(kinds) == 1 else "Prefix"


def _txt(x):
    """A text field of a trade-site listing as plain text (2.8.2). Some listings (Irradiated Tablets, Oct 2026) give a
    field as an object instead of a string - e.g. {"text": ...} or {"name": ...} - which used to stop item_text."""
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        for k in ("text", "value", "name", "line", "description"):
            v = x.get(k)
            if isinstance(v, (str, list, dict)) and v:
                return _txt(v)
        return ""
    if isinstance(x, (list, tuple)):
        return "\n".join(t for t in (_txt(v) for v in x) if t)
    return str(x)


def item_text(it):
    """A trade-site listing's item -> the text a Ctrl+Alt+C copy of it would give (2.0), so the Wealth page can price
    rares with the same price checkers. Mod headers (prefix / suffix, tier) come from the listing's 'extended' data."""
    frame = it.get("frameType", 0)
    rarity = it.get("rarity") or RARITY_OF_FRAME.get(frame, "Normal")
    base = strip_markup(_txt(it.get("baseType")))
    b = gamedata.base(gamedata.find_base(base) or base) or {}
    cls = gamedata.classes().get(b.get("class") or "", {}).get("name") or ""
    if not cls:
        cat = ((it.get("extended") or {}).get("category") or "").lower()
        cls = "Tablet" if "tablet" in base.lower() or "tablet" in cat else "Jewels" if cat == "jewel" else cat.title() or "Item"
    lines = [f"Item Class: {cls}", f"Rarity: {rarity}"]
    if it.get("name"):
        lines.append(strip_markup(_txt(it["name"])))
    lines.append(strip_markup(_txt(it.get("typeLine")) or base))
    props, uses = [], None
    for p in it.get("properties") or []:
        name = strip_markup(_txt(p.get("name"))).strip()
        vals = ", ".join(strip_markup(_txt(v[0] if isinstance(v, (list, tuple)) else v)) for v in (p.get("values") or []) if v)
        if not name:
            continue
        if "use" in name.lower() and vals:
            uses = re.sub(r"[^\d]", "", vals) or None
            continue
        if "{0}" in name:
            name = name.replace("{0}", vals)
            props.append(name)
        else:
            props.append(f"{name}: {vals}" if vals else name)
    lines += ["--------"] + (props or ["(no properties)"])
    if it.get("sockets"):
        lines += ["--------", "Sockets: " + " ".join("J" if s_.get("type") == "jewel" else "S" for s_ in it["sockets"])]
    if it.get("ilvl"):
        lines += ["--------", f"Item Level: {it['ilvl']}"]
    imp = [strip_markup(_txt(m)) for m in it.get("implicitMods") or []]
    if uses and not any("uses remaining" in m.lower() for m in imp):
        imp.append(f"{uses} uses remaining")
    if imp:
        lines += ["--------", "{ Implicit Modifier }"] + [l for m in imp for l in m.split("\n")]
    for m in it.get("runeMods") or []:
        lines += ["--------", strip_markup(_txt(m)) + " (rune)"]
    ext = it.get("extended") or {}
    body = []
    for key, field, src in MOD_SOURCES:
        texts = it.get(field) or []
        hashes = (ext.get("hashes") or {}).get(key) or []
        info = (ext.get("mods") or {}).get(key) or []
        last = None
        for n, raw in enumerate(texts):
            t = strip_markup(_txt(raw))
            mi = None
            try:
                mi = hashes[n][1][0] if hashes[n][1] else None
            except Exception:
                mi = None
            m = info[mi] if mi is not None and mi < len(info) else None
            if m is None or mi != last:                       # a new affix (lines of one hybrid mod share a header)
                tier = str((m or {}).get("tier") or "")
                kind = {"P": "Prefix", "S": "Suffix"}.get(tier[:1]) or _kind_guess(t, cls)
                num = re.sub(r"[^\d]", "", tier)
                head = f'{{ {src}{kind} Modifier' + (f' "{_txt(m.get("name"))}"' if m and m.get("name") else "") + \
                       (f" (Tier: {num})" if num else "") + " }"
                body.append(head)
            last = mi
            body += t.split("\n")
    if body:
        lines += ["--------"] + body
    if it.get("corrupted"):
        lines += ["--------", "Corrupted"]
    return "\n".join(lines)


def wealth_item(entry, tab):
    """Keep what the Wealth page needs from one fetched listing."""
    it, lst = entry.get("item") or {}, entry.get("listing") or {}
    mods = []
    for k in ("implicitMods", "runeMods", "explicitMods", "fracturedMods", "desecratedMods", "craftedMods"):
        for m in it.get(k) or []:
            mods += [strip_markup(l) for l in _txt(m).split("\n") if l.strip()]
    return {"lid": entry.get("id"), "tab": tab["id"], "stash": (lst.get("stash") or {}).get("name") or tab["label"],
            "name": _txt(it.get("name")), "type": _txt(it.get("typeLine")), "base": _txt(it.get("baseType")),
            "frame": it.get("frameType", 0), "qty": it.get("stackSize") or 1, "ilvl": it.get("ilvl"),
            "corrupted": bool(it.get("corrupted")), "cat": (it.get("extended") or {}).get("category") or "",
            "level": _item_level_prop(it), "mods": mods[:14],
            "text": item_text(it) if it.get("frameType", 0) in (1, 2) else None}     # 2.0: for pricing rares


COUNTED_TAB = "counted"               # the "tab" of everything counted by hand
COUNTED_LABEL = "Counted by hand"
CLASS_CAT = {"stackable currency": "currency", "map fragments": "fragment", "omen": "currency", "socketable": "currency",
             "delirium instill": "currency", "essence": "currency", "splinter": "fragment", "catalyst": "currency",
             "divination card": "card", "uncut gem": "gem"}


def holding_item(name, h):
    """A counted stack as a Wealth item (same shape as one read from a tab)."""
    cls = (h.get("cls") or "").lower()
    return {"lid": "held:" + name, "tab": COUNTED_TAB, "stash": COUNTED_LABEL, "name": "", "type": name, "base": name,
            "frame": 5, "qty": int(h.get("qty") or 0), "ilvl": None, "corrupted": False,
            "cat": CLASS_CAT.get(cls, "currency" if not cls else cls.split()[0]), "level": None, "mods": [], "text": None,
            "held": True}


def parse_stack(text):
    """A copied stack (Ctrl+C on currency, fragments, essences, omens ...) -> (name, quantity, item class) or None."""
    if not text or "Stack Size:" not in text:
        return None
    lines = [l.strip() for l in text.replace("\r", "").split("\n")]
    cls, name, qty = "", None, None
    for i, l in enumerate(lines):
        if l.startswith("Item Class:"):
            cls = l.split(":", 1)[1].strip()
        elif l.startswith("Rarity:"):
            name = next((x for x in lines[i + 1:] if x and not x.startswith("--")), None)
        elif l.startswith("Stack Size:"):
            m = re.match(r"Stack Size:\s*([\d,.\s]+)", l)
            if m:
                try:
                    qty = int(re.sub(r"[^\d]", "", m.group(1)))
                except ValueError:
                    qty = None
    if not name or not qty:
        return None
    return name, qty, cls


def wealth_display_name(it):
    base = it["type"] or it["base"]
    return f"{it['name']} {base}".strip() if it["name"] else base


def wealth_key(it):
    """Manual prices are shared by every copy of the same thing (rares get their own, keyed by listing)."""
    if it["frame"] in (1, 2):
        return "item:" + str(it["lid"])
    if it["frame"] == 3:
        return "unique:" + it["name"].lower()
    return "type:" + (it["base"] or it["type"]).lower()


WEALTH_CUR_WORDS = {"div": "divine", "divs": "divine", "divine": "divine", "divines": "divine", "d": "divine",
                    "vaal": "vaal", "vaals": "vaal", "chaos": "chaos", "c": "chaos", "ex": "exalted", "exa": "exalted",
                    "exalt": "exalted", "exalted": "exalted", "exalts": "exalted", "regal": "regal", "annul": "annul",
                    "annulment": "annul", "alch": "alch", "alchemy": "alch"}


def parse_price_text(text):
    """"37882", "37,882", "37882 div", "~price 37882 divine", "~b/o 150 vaal" -> (amount, currency id or None).
    (None, None) if there's no number in it."""
    t = (text or "").strip().lower().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*([a-z]*)", t)
    if not m:
        return None, None
    amount = float(m.group(1))
    word = m.group(2)
    if word == "k":                              # "38k" = 38,000
        amount, word = amount * 1000, t[m.end():].strip().split(" ")[0] if t[m.end():].strip() else ""
    amount = int(amount) if amount.is_integer() else amount
    cur = WEALTH_CUR_WORDS.get(word)
    if cur is None and word:                     # "divine orb" etc.: try the first word, then a known prefix
        cur = next((v for k, v in WEALTH_CUR_WORDS.items() if len(k) > 2 and word.startswith(k)), None)
    return amount, cur


def parse_trade_link(link):
    """Read a pathofexile.com/trade2 search link the way the site encodes it (gzip + base64 after the league).
    -> ({"league", "account", "amount", "currency"}, None) or (None, plain-English reason)."""
    import base64
    import gzip
    from urllib.parse import unquote, urlparse
    link = (link or "").strip()
    m = re.search(r"/trade2?/search/poe2/([^/?#]+)/([^/?#]+)", urlparse(link).path if "://" in link else link)
    if not m:
        return None, "That doesn't look like a Path of Exile 2 trade-site search link."
    league, code = unquote(m.group(1)), m.group(2)
    if not code.startswith("H4sI"):
        return None, ("That is a short saved-search link, which only the trade site can read. Type the tab's price "
                      "instead, or copy the address again after changing a filter on the page (it then gets longer).")
    try:
        raw = base64.urlsafe_b64decode(code + "=" * (-len(code) % 4))
        q = json.loads(gzip.decompress(raw))
    except Exception:
        return None, "The search in that link couldn't be read. Type the tab's price instead."
    q = q.get("query", q) if isinstance(q, dict) else {}
    tf = ((q.get("filters") or {}).get("trade_filters") or {}).get("filters") or {}
    price, account = tf.get("price") or {}, ((tf.get("account") or {}).get("input") or "").strip()
    amount = price.get("min") if price.get("min") is not None else price.get("max")
    if amount is None or not price.get("option"):
        return None, ("That link has no price filter, so it covers everything you have listed. Use a link that "
                      "searches for your tab's price (set Buyout Price min to it, and pick its currency).")
    amount = int(amount) if float(amount).is_integer() else float(amount)
    return {"league": league, "account": account, "amount": amount, "currency": str(price["option"])}, None


class WealthStore:
    """wealth.json: your tab markers, the items last read from them, manual prices and the net worth history."""

    def __init__(self):
        d = load_json("wealth.json", {})
        self.lock = threading.RLock()
        self.tabs = d.get("tabs", [])              # {id, label, amount, currency, enabled}
        self.items = d.get("items", {})            # tab id -> [wealth_item]
        self.overrides = d.get("overrides", {})    # wealth_key -> divines
        self.snapshots = d.get("snapshots", [])    # {ts, league, total, by_tab, by_cat, n, priced}
        self.results = d.get("results", {})        # tab id -> {total, fetched, warnings, error, qid, ts}
        self.last_sync = d.get("last_sync", 0)
        self.rare_prices = d.get("rare_prices", {})  # 2.0: listing id -> {est, sig, ts, label, conf, qid, league}
        self.holdings = d.get("holdings", {})      # 2.0 beta 7: counted by hand: name -> {qty, cls, ts}

    def save(self):
        with self.lock:
            known = {str(i["lid"]) for lst in self.items.values() for i in lst}
            self.rare_prices = {k: v for k, v in self.rare_prices.items() if k in known}   # gone from your tabs: forget
            data = {"tabs": self.tabs, "items": self.items, "overrides": self.overrides, "snapshots": self.snapshots[-3000:],
                    "results": self.results, "last_sync": self.last_sync, "rare_prices": self.rare_prices,
                    "holdings": self.holdings}
        save_json("wealth.json", data)

    def tab(self, tab_id):
        return next((t for t in self.tabs if t["id"] == tab_id), None)

    def all_items(self):
        with self.lock:
            known = {t["id"] for t in self.tabs}
            out = [i for tid, lst in self.items.items() if tid in known for i in lst]
            return out + [holding_item(n, h) for n, h in sorted(self.holdings.items())]

    # ---- counted by hand (2.0 beta 7): currency and other stacks you copy (Ctrl+C) or type in
    def set_holding(self, name, qty, cls=""):
        name = name.strip()
        with self.lock:
            if qty is None or qty <= 0:
                self.holdings.pop(name, None)
            else:
                old = self.holdings.get(name) or {}
                self.holdings[name] = {"qty": int(qty), "cls": cls or old.get("cls", ""), "ts": time.time()}
        self.save()

    def holding(self, name):
        h = self.holdings.get(name.strip())
        return h["qty"] if h else 0

    def snapshot(self, league, prices, why=""):
        rows, total, priced = wealth_rows(self.all_items(), prices, self.overrides)
        if not rows:
            return None
        by_tab, by_cat = {}, {}
        for it, each, tot, _src in rows:
            if tot is None:
                continue
            by_tab[it["stash"]] = by_tab.get(it["stash"], 0) + tot
            cat = (it["cat"] or "other").split(".")[0]
            by_cat[cat] = by_cat.get(cat, 0) + tot
        snap = {"ts": time.time(), "league": league, "total": total, "by_tab": by_tab, "by_cat": by_cat,
                "n": len(rows), "priced": priced, "why": why}     # why (2.3.0): counted / synced / prices / ...
        with self.lock:
            if self.snapshots and snap["ts"] - self.snapshots[-1]["ts"] < 300 and self.snapshots[-1].get("league") == league:
                self.snapshots[-1] = snap           # a price update right after a sync: replace, don't add a twin
            else:
                self.snapshots.append(snap)
        self.save()
        return snap


PRICES_VERSION = 2


def slug(name):
    """'Hinekora's Lock' -> 'hinekoras-lock' (how poe.ninja writes its ids)."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("'", "")).strip("-")


class WealthPrices:
    """poe.ninja's PoE 2 prices for stackables (exchange overview) and uniques (item overview), all in divines.
    Refreshed at most hourly (PoE 2 data only updates about hourly), one request at a time, with ETags so an unchanged
    category costs poe.ninja almost nothing. Cached in wealth_prices.json."""

    def __init__(self):
        c = load_json("wealth_prices.json", {})
        if c.get("v") != PRICES_VERSION:            # 2.0 beta 7: older caches lack item names: fetch everything again
            c = {}
        self.league = c.get("league")          # the trade-site league these prices are for
        self.src = c.get("src")                # how poe.ninja spells it
        self.ts = c.get("ts", 0)
        self.parts = c.get("parts", {})        # type -> parsed response (values in poe.ninja's primary currency)
        self.etags = c.get("etags", {})
        self.lock = threading.Lock()
        self.errors = []
        self._index()

    def age(self):
        return time.time() - self.ts if self.ts else None

    def _get(self, typ, league):
        """One poe.ninja overview. -> parsed JSON, or None when it hasn't changed since last time (HTTP 304)."""
        path = "exchange/current/overview" if typ in NINJA_EXCHANGE_TYPES else "stash/current/item/overview"
        hdr = {"User-Agent": WEALTH_UA, "Accept": "application/json"}
        if self.src == league and self.etags.get(typ) and typ in self.parts:
            hdr["If-None-Match"] = self.etags[typ]
        r = requests.get(f"{NINJA_ECON}/{path}", params={"league": league, "type": typ}, headers=hdr, timeout=20)
        if r.status_code == 304:
            return None
        r.raise_for_status()
        self.etags[typ] = r.headers.get("ETag")
        return r.json()

    def ensure(self, league, force=False):
        """Refresh if older than an hour (or `force`). `league` is the trade-site name; poe.ninja may spell it
        differently, so the same alternatives as the exchange rates are tried (Rates.names_for)."""
        if not league or (not force and self.league == league and self.age() is not None and self.age() < 3600):
            return
        with self.lock:
            errors, parts = [], {}
            for name in Rates.names_for(league):
                errors, parts = [], dict(self.parts) if self.league == league else {}
                for typ in NINJA_EXCHANGE_TYPES + NINJA_ITEM_TYPES:
                    try:
                        body = self._get(typ, name)
                    except Exception as e:
                        errors.append(f"{typ}: {str(e)[:80]}")
                        continue
                    if body is not None:                       # None = 304, what we have is still current
                        parts[typ] = self._parse(typ, body)
                    if typ == "Currency" and not (parts.get("Currency") or {}).get("lines"):
                        break                                  # this spelling has no data: don't ask for the rest
                if (parts.get("Currency") or {}).get("lines"):
                    self.parts, self.league, self.src, self.ts = parts, league, name, time.time()
                    break                                      # this spelling of the league worked
            self.errors = errors
            save_json("wealth_prices.json", {"v": PRICES_VERSION, "league": self.league, "src": self.src, "ts": self.ts,
                                             "parts": self.parts, "etags": self.etags})
            self._index()

    @staticmethod
    def _parse(typ, body):
        if typ in NINJA_EXCHANGE_TYPES:
            core = body.get("core") or {}
            names, images = {}, {}
            # 2.0 beta 7: every item's name is in the top-level "items" list; "core.items" only holds the few core
            # currencies (Divine / Chaos / Exalted). Reading only core.items left everything else nameless, so only
            # those three were found. (Same layout Sidekick reads: ApiExchangeOverview.Items.)
            for items in (core.get("items"), body.get("items")):
                if isinstance(items, list):
                    for i in items:
                        if isinstance(i, dict) and i.get("id"):
                            names[i["id"]] = i.get("name") or names.get(i["id"]) or i["id"]
                            if i.get("image"):
                                images[i["id"]] = i["image"]
                elif isinstance(items, dict):
                    for k, v in items.items():
                        names[k] = (v or {}).get("name") or names.get(k) or k
            lines = []
            for ln in body.get("lines") or []:
                try:
                    lines.append([ln["id"], names.get(ln["id"]) or ln["id"], float(ln["primaryValue"]),
                                  float(ln.get("volumePrimaryValue") or 0)])
                except (KeyError, TypeError, ValueError):
                    pass
            return {"primary": core.get("primary"), "names": names, "lines": lines, "images": images}
        lines = []
        for ln in body.get("lines") or []:
            try:
                lines.append([ln["name"], ln.get("baseType") or "", float(ln["primaryValue"]),
                              int(ln.get("listingCount") or 0), bool(ln.get("corrupted"))])
            except (KeyError, TypeError, ValueError):
                pass
        return {"lines": lines}

    def _index(self):
        """Build the lookup tables in divines."""
        cur = self.parts.get("Currency") or {}
        primary = cur.get("primary") or "divine"
        per_div = 1.0
        if primary != "divine":                                # values are in e.g. exalted: divide by exalted-per-divine
            per_div = next((v for cid, _n, v, _vol in cur.get("lines", []) if cid == "divine"), None) or 0
        self.ok = per_div > 0
        self.primary = primary
        self.by_name, self.uniques = {}, {}
        if not self.ok:
            return
        prim_name = (cur.get("names") or {}).get(primary) or {"exalted": "Exalted Orb", "divine": "Divine Orb",
                                                               "chaos": "Chaos Orb"}.get(primary)
        if prim_name:
            self.by_name[prim_name.lower()] = (1.0 / per_div, "poe.ninja Currency")
        self.by_slug = {}
        for typ in NINJA_EXCHANGE_TYPES:
            for cid, name, v, _vol in (self.parts.get(typ) or {}).get("lines", []):
                self.by_name[str(name).lower()] = (v / per_div, f"poe.ninja {typ}")
                self.by_slug[str(cid).lower()] = (v / per_div, f"poe.ninja {typ}")
        for typ in NINJA_ITEM_TYPES:
            for name, base, v, count, corrupted in (self.parts.get(typ) or {}).get("lines", []):
                self.uniques.setdefault(name.lower(), []).append((base.lower(), v / per_div, count, corrupted, f"poe.ninja {typ}"))
        self.by_name.setdefault("divine orb", (1.0, "poe.ninja Currency"))

    def value(self, it):
        """-> (divines per unit, source) or (None, None)."""
        if it["frame"] == 3:
            cands = self.uniques.get(it["name"].lower()) or []
            if not cands:
                return None, None
            base = (it["base"] or it["type"]).lower()
            pool = [c for c in cands if c[0] == base] or cands
            pool = [c for c in pool if c[3] == it["corrupted"]] or pool
            best = max(pool, key=lambda c: c[2])
            return best[1], best[4]
        if it["frame"] in (1, 2):                               # magic / rare: the price checker's result (2.0)
            rp = WEALTH.rare_prices.get(str(it.get("lid")))
            if rp and rp.get("est") is not None and rp.get("sig") == rare_sig(it):
                uses = re.match(r"(\d+/\d+ uses)", rp.get("label") or "")
                return rp["est"], ("price check" + (f" ({rp['conf']})" if rp.get("conf") and rp["conf"] != "-" else "")
                                   + (f" · {uses.group(1)}" if uses else ""))
            return None, None
        names = [n for n in (it["type"], it["base"]) if n]
        if it.get("level"):
            names = [f"{n} (Level {it['level']})" for n in names] + names
        for n in names:
            hit = self.by_name.get(n.lower())
            if hit:
                return hit
        for n in names:                                         # poe.ninja's id is often the name as a slug
            hit = getattr(self, "by_slug", {}).get(slug(n))
            if hit:
                return hit
        return None, None


def rare_sig(it):
    """Changes when the item's text changes (re-rolled, re-crafted): its price must be checked again."""
    import hashlib
    return hashlib.sha1((it.get("text") or "").encode("utf-8")).hexdigest()[:16]


RARE_MAX_AGE = 3 * 86400            # a rare's price is checked again after 3 days (or when the item changed)


def rares_to_price(items, league, now=None):
    """Magic and rare items needing a price check: new, changed or old. Most valuable (last time) first."""
    now = now or time.time()
    out = []
    for it in items:
        if it["frame"] not in (1, 2) or not it.get("text"):
            continue
        rp = WEALTH.rare_prices.get(str(it["lid"]))
        if rp and rp.get("sig") == rare_sig(it) and rp.get("league") == league and now - rp.get("ts", 0) < RARE_MAX_AGE:
            continue
        out.append((-(rp or {}).get("est", 0) if rp and rp.get("est") else 0, it))
    out.sort(key=lambda x: x[0])
    return [it for _k, it in out]


def wealth_rows(items, prices, overrides):
    """-> ([(item, divines each or None, divines total or None, source)], total, priced count)"""
    rows, total, priced = [], 0.0, 0
    for it in items:
        ov = overrides.get(wealth_key(it))
        if ov is not None:
            each, src = float(ov), "your price"
        else:
            each, src = prices.value(it)
        tot = each * it["qty"] if each is not None else None
        if tot is not None:
            total += tot
            priced += 1
        rows.append((it, each, tot, src))
    return rows, total, priced


WEALTH = WealthStore()


WPRICES = WealthPrices()


WEALTH_SYNC = {"cur": None}        # the running (or last) sync: progress for the page, read by the UI thread
WEALTH_RARES = {"gen": 0, "total": 0, "done": 0, "priced": 0, "running": False, "msg": ""}   # 2.0: pricing rares
WEALTH_RARE_PRIO = 10              # after the sync (5-9) and far behind items you copy yourself (0-2)


class WealthJobs:
    """Engine jobs for the Wealth page (mixed into Engine, so they run on the same thread, one request at a time)."""

    def wealth_start(self):
        """Queue a sync of every included tab. Called from the window. -> error text or None."""
        league, acc = SETTINGS.get("league"), (SETTINGS.get("wealth_account") or "").strip()
        tabs = [t for t in WEALTH.tabs if t.get("enabled", True)]
        cur = WEALTH_SYNC["cur"]
        if cur and cur["running"]:
            return "A sync is already running."
        if not league:
            return "Pick a league first (Settings, ⚙ on the dock)."
        if not re.search(r"#\d+$", acc):
            return "Enter your account name with its number, e.g. YourName#1234 (it's shown on the trade site)."
        if not tabs:
            return ("Add your priced tab first: under \"Your priced tabs\", type the price you put on the tab in game "
                    "(e.g. 37882 and Divine Orb) and press Add tab, or paste a trade link for it and press Add from link.")
        sid = time.time()
        WEALTH_RARES["gen"] += 1                       # a new sync replaces any rare pricing still queued
        WEALTH_RARES["running"] = False
        WEALTH_SYNC["cur"] = {"id": sid, "running": True, "cancel": False, "started": sid, "league": league, "account": acc,
                              "expected": 0, "fetched": 0, "searches": 0, "msg": "Waiting for item pricing to finish…",
                              "tabs": {t["id"]: {"label": t["label"], "total": None, "seen": set(), "items": [],
                                                 "warnings": [], "error": None, "qid": None, "dropped": 0} for t in tabs}}
        for t in tabs:
            self.add(WEALTH_PRIO, "wealth_search", sid, t["id"], {}, "top", "")
        self.add(WEALTH_FINISH_PRIO, "wealth_finish", sid)
        return None

    def _wsync(self, sid):
        s = WEALTH_SYNC["cur"]
        return s if s and s["id"] == sid and s["running"] and not s["cancel"] else None

    def _wsay(self, s, msg):
        s["msg"] = msg
        self.ui_q.put(("wealth", "progress"))

    def do_wealth_search(self, sid, tab_id, extra, level, label):
        s = self._wsync(sid)
        tab = WEALTH.tab(tab_id)
        if not s or not tab or s["tabs"][tab_id]["error"]:
            return
        t = s["tabs"][tab_id]
        self._wsay(s, f"Searching {tab['label']}" + (f" ({label})" if label else "") + "…")
        try:
            res = call("POST", f"{BASE}/search/poe2/{requests.utils.quote(s['league'])}",
                       json=wealth_query(s["account"], tab, extra))
        except Exception as e:
            t["error"] = str(e)[:300]
            self._wsay(s, f"{tab['label']}: search failed")
            return
        s["searches"] += 1
        total, ids, qid = int(res.get("total") or 0), list(res.get("result") or []), res.get("id")
        if level == "top":
            t["total"], t["qid"] = total, qid
        kids = wealth_children(extra, level) if total > len(ids) and ids else []
        if kids:
            for ex, lv, lab in kids:
                self.add(WEALTH_PRIO, "wealth_search", sid, tab_id, ex, lv, f"{label}, {lab}" if label else lab)
            return
        if total > len(ids):
            t["warnings"].append(f"{label or 'The tab'}: {total} items but only {len(ids)} can be read. "
                                 f"Move some to another tab with its own price.")
        new = [i for i in ids if i not in t["seen"]]
        t["seen"].update(new)
        for i in range(0, len(new), 10):
            self.add(WEALTH_PRIO, "wealth_fetch", sid, tab_id, qid, new[i:i + 10])
        s["expected"] += len(new)
        self.ui_q.put(("wealth", "progress"))

    def do_wealth_fetch(self, sid, tab_id, qid, ids):
        s = self._wsync(sid)
        tab = WEALTH.tab(tab_id)
        if not s or not tab or s["tabs"][tab_id]["error"]:
            return
        t = s["tabs"][tab_id]
        self._wsay(s, f"Reading items from {tab['label']}…")
        try:
            res = call("GET", f"{BASE}/fetch/{','.join(ids)}", params={"query": qid})
        except Exception as e:
            t["error"] = str(e)[:300]
            return
        acc = s["account"].lower()
        for e in res.get("result") or []:
            if not e:
                continue
            lst = e.get("listing") or {}
            p = lst.get("price") or {}
            owner = str((lst.get("account") or {}).get("name") or "").lower()
            mine = not owner or owner == acc or owner.split("#")[0] == acc.split("#")[0] and ("#" not in owner or "#" not in acc)
            if p.get("amount") != tab["amount"] or p.get("currency") != tab["currency"] or not mine:
                t["dropped"] += 1                   # not carrying the exact marker price, or someone else's listing
                continue
            try:
                t["items"].append(wealth_item(e, tab))
            except Exception as ex:                 # 2.8.3: one odd listing mustn't lose the rest of its batch
                t["unreadable"] = t.get("unreadable", 0) + 1
                if t["unreadable"] == 1:
                    t["warnings"].append(f"Couldn't read a listing ({type(ex).__name__}: {str(ex)[:80]}) - it was left "
                                         f"out. Problem report (Settings > Advanced) helps find out why.")
                continue
            s["fetched"] += 1
        self.ui_q.put(("wealth", "progress"))

    def do_wealth_finish(self, sid):
        s = WEALTH_SYNC["cur"]
        if not s or s["id"] != sid:
            return
        if s["cancel"]:
            s["running"], s["msg"] = False, "Sync stopped. The last complete data is kept."
            self.ui_q.put(("wealth", "done"))
            return
        now, good = time.time(), 0
        with WEALTH.lock:
            for tab_id, t in s["tabs"].items():
                res = {"total": t["total"], "fetched": len(t["items"]), "warnings": list(t["warnings"]),
                       "error": t["error"], "qid": t["qid"], "ts": now, "league": s["league"]}
                if t["dropped"]:
                    res["warnings"].append(f"{t['dropped']} listing(s) not at exactly this tab's price were left out.")
                if t.get("unreadable", 0) > 1:
                    res["warnings"].append(f"{t['unreadable']} listings couldn't be read and were left out.")
                if not t["error"]:
                    good += 1
                    WEALTH.items[tab_id] = t["items"]             # a tab that failed keeps its last good items
                    if t["total"] == 0:
                        res["warnings"].append("No listings found. Is the tab public, priced at exactly this amount and "
                                               "currency, and has the trade site had a minute to list it?")
                    elif t["total"] and len(t["items"]) + t.get("unreadable", 0) < t["total"]:
                        res["warnings"].append(f"Read {len(t['items'])} of {t['total']} items; the rest are in a "
                                               f"category the app can't search separately. Split the tab.")
                WEALTH.results[tab_id] = res
            WEALTH.last_sync = now
        WEALTH.save()
        self._wsay(s, "Pricing currency, stackables and uniques with poe.ninja (magic / rare items get price-checked next)…")
        try:
            WPRICES.ensure(s["league"])
        except Exception as e:
            WPRICES.errors = [str(e)[:120]]
        WEALTH.snapshot(s["league"], WPRICES, "synced")
        n = sum(len(t["items"]) for t in s["tabs"].values() if not t["error"])
        failed = len(s["tabs"]) - good
        queued = self.wealth_queue_rares(s["league"])
        s["running"] = False
        s["msg"] = (f"Synced {n} items from {good} tab{'s' if good != 1 else ''} with {s['searches']} searches"
                    + (f". {failed} tab{'s' if failed != 1 else ''} failed - see the tab list." if failed else ".")
                    + (f" Now price-checking {queued} magic / rare item{'s' if queued != 1 else ''} in the background "
                       f"(behind anything you copy)." if queued else ""))
        self.ui_q.put(("wealth", "done"))

    # ---- rares (2.0): priced with the same price checkers as Ctrl+Alt+C, one at a time, behind your own checks
    def wealth_queue_rares(self, league, force=False):
        """Queue price checks for the magic / rare items that need one. -> how many."""
        items = WEALTH.all_items()
        todo = [i for i in items if i["frame"] in (1, 2) and i.get("text")] if force else rares_to_price(items, league)
        WEALTH_RARES["gen"] += 1
        gen = WEALTH_RARES["gen"]
        WEALTH_RARES.update(total=len(todo), done=0, priced=0, running=bool(todo), msg="")
        for it in todo:
            self.add(WEALTH_RARE_PRIO, "wealth_rare", it["lid"], gen)
        if todo:
            self.add(WEALTH_RARE_PRIO + 1, "wealth_rares_done", gen)
        return len(todo)

    def do_wealth_rare(self, lid, gen):
        if gen != WEALTH_RARES["gen"]:
            return                                     # stopped, or replaced by a newer sync
        it = next((i for i in WEALTH.all_items() if i.get("lid") == lid), None)
        if not it or not it.get("text"):
            return
        from .mods import parse_item
        from . import gear, waystone
        item = parse_item(it["text"]) or waystone.parse_waystone(it["text"]) or gear.parse_gear(it["text"])
        rp = {"sig": rare_sig(it), "ts": time.time(), "league": SETTINGS.get("league"), "est": None, "conf": "-",
              "label": "", "qid": None}
        if not item:
            rp["label"] = "this kind of item can't be price-checked"
        else:
            rec = {"item": item, "ov": {}, "resolved": False, "state": "queued", "label": "", "total": 0, "prices": [],
                   "est": None, "qid": None}
            self.resolve_rec(rec)
            self.price_rec(rec)
            rp.update(est=rec.get("est") if not rec.get("manual") else None, conf=rec.get("conf") or "-",
                      label=rec.get("label", "")[:200], qid=rec.get("qid"))
        with WEALTH.lock:
            WEALTH.rare_prices[str(lid)] = rp
        WEALTH_RARES["done"] += 1
        WEALTH_RARES["priced"] += rp["est"] is not None
        if WEALTH_RARES["done"] % 5 == 0:
            WEALTH.save()
        self.ui_q.put(("wealth", "rare"))

    def do_wealth_rares_done(self, gen):
        if gen != WEALTH_RARES["gen"]:
            return
        WEALTH.save()
        WEALTH.snapshot(SETTINGS.get("league"), WPRICES, "rares priced")
        R = WEALTH_RARES
        R["running"] = False
        R["msg"] = (f"Price-checked {R['done']} magic / rare item{'s' if R['done'] != 1 else ''}: "
                    f"{R['priced']} got a price.")
        self.ui_q.put(("wealth", "rares_done"))
