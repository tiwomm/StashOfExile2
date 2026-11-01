"""Farm Ledger (2.45.0, was Money Makers' Run tracker): does a farming setup really make money?

A SETUP is what you farm with: a strat (optional), the waystone you run, your tablets (and how many runs each lasts),
your atlas trees and notes, and any other cost per run. Changing it makes a new VERSION, so older numbers stay honest.
Every N runs (you pick N) you LOG: the loot is copied in game (Ctrl+Alt+C on each drop - or pasted) and priced with
poe.ninja item by item; cost comes from the setup; profit = loot - cost. The logs are the spreadsheet; the figures
(profit per run, div / hour, return on cost, spread) come from them.

Runs are counted by themselves from Client.txt (each new map you enter - the same file the Session timer reads) or
with a key you press. Nothing here acts in the game: it reads your copies and the log file, and shows a box.

Data: farm_ledger.json in the data folder. The old Run tracker's runs (money_runs.json) are moved in once, one
"Imported" setup per strat. CSV export uses one header for every Money Makers file (CSV_LOG_HEAD)."""
import csv
import io
import json
import re
import statistics
import time
import uuid

from .config import load_json, save_json

FILE = "farm_ledger.json"
OLD_RUNS = "money_runs.json"
EVERY = 5                    # runs between logs, by default (each setup has its own)
COUNTING = {"auto": "By itself - each new map you enter (Client.txt)", "key": "With a key after each run"}
ATLAS_TREES = ("Atlas passive tree", "Breach", "Delirium", "Ritual", "Expedition", "Abyss", "Essence", "Strongbox",
               "Rogue Exiles", "Shrines", "Overseer", "Temple")

# one layout for every CSV the app writes about strats and their numbers (2.46.0's strat guide CSV uses it too)
CSV_LOG_HEAD = ("setup", "version", "log", "start", "end", "runs", "minutes", "cost_div", "loot_div", "profit_div",
                "profit_per_run_div", "div_per_hour", "note", "loot")
CSV_LOOT_HEAD = ("setup", "version", "log", "start", "item", "qty", "each_div", "total_div")


def _id():
    return uuid.uuid4().hex[:10]


# ---------------------------------------------------------------- the file
def empty():
    return {"v": 1, "setups": [], "logs": [], "current": None, "pending": None}


def load():
    d = load_json(FILE, None)
    if not isinstance(d, dict):
        d = empty()
        _migrate(d)
    for k, v in empty().items():
        d.setdefault(k, v)
    return d


def save(d):
    return save_json(FILE, d)


def _migrate(d):
    """The Run tracker's runs (2.28.0-2.44.0): one "Imported" setup per strat, each run a log of 1 run."""
    old = load_json(OLD_RUNS, [])
    if not isinstance(old, list) or not old:
        return
    by = {}
    for r in old:
        if not isinstance(r, dict) or "start" not in r or "end" not in r:
            continue
        sid = r.get("strat")
        if sid not in by:
            s = new_setup(f"Imported runs{' - ' + sid if sid else ''}", strat=sid)
            s["every"] = 1
            d["setups"].append(s)
            by[sid] = s
        s = by[sid]
        p = r.get("profit")
        d["logs"].append({"id": _id(), "setup": s["id"], "v": 1, "start": r["start"], "end": r["end"], "runs": 1,
                          "map_secs": max(0.0, r["end"] - r["start"]), "cost": 0.0,
                          "loot": None if p is None else float(p), "profit": None if p is None else float(p),
                          "items": [], "note": "from the Run tracker", "skipped": p is None})
    if d["setups"]:
        d["current"] = d["setups"][0]["id"]


# ---------------------------------------------------------------- setups and versions
def new_version(v=1, base=None):
    out = {"v": v, "created": time.time(), "waystones": [], "tablets": [], "others": [],
           "atlas": {"trees": [], "notes": ""}, "extra": 0.0}
    if base:
        out.update({k: json.loads(json.dumps(base[k])) for k in ("waystones", "tablets", "others", "atlas", "extra")
                    if k in base})
    return out


def new_setup(name, strat=None):
    return {"id": _id(), "name": name or "New setup", "strat": strat, "created": time.time(), "every": EVERY,
            "counting": "auto", "versions": [new_version()], "cur_v": 1}


def setup(d, sid):
    return next((s for s in d["setups"] if s["id"] == sid), None)


def version(s, v=None):
    v = v or s.get("cur_v") or s["versions"][-1]["v"]
    return next((x for x in s["versions"] if x["v"] == v), s["versions"][-1])


def bump_version(s):
    """A change to the waystone, tablets or atlas after logs exist: the next version (a copy to edit)."""
    cur = version(s)
    nv = new_version(max(x["v"] for x in s["versions"]) + 1, cur)
    s["versions"].append(nv)
    s["cur_v"] = nv["v"]
    return nv


def has_logs(d, sid, v):
    return any(l["setup"] == sid and l["v"] == v for l in d["logs"])


# ---------------------------------------------------------------- items you put into the setup
def parse_item(text):
    """A copied waystone / tablet / anything -> {name, base, cls, rarity, tier, mods, text} (None if not an item)."""
    lines = [l.strip() for l in str(text).replace("\r", "").split("\n")]
    if not lines or not lines[0].startswith("Item Class:"):
        return None
    cls = lines[0].split(":", 1)[1].strip()
    rarity, names, i = "", [], 1
    while i < len(lines) and not lines[i].startswith("--"):
        if lines[i].startswith("Rarity:"):
            rarity = lines[i].split(":", 1)[1].strip()
        elif lines[i]:
            names.append(lines[i])
        i += 1
    name = names[0] if names else cls
    base = names[-1] if names else cls
    tier = None
    m = re.search(r"\(Tier (\d+)\)", text) or re.search(r"^Waystone Tier:\s*(\d+)", text, re.M)
    if m:
        tier = int(m.group(1))
    mods, take = [], False
    for l in lines:                               # Ctrl+Alt+C: every mod comes under a { ... Modifier ... } line
        if l.startswith("{"):
            take = "Modifier" in l or "Implicit" in l
            continue
        if take and l and not l.startswith("--"):
            mods.append(re.sub(r"\(\-?[\d.]+-[\d.]+\)", "", l).replace("  ", " ").strip())
        elif l.startswith("--"):
            take = False
    if not mods:                                  # a plain Ctrl+C: the lines of the sections after Item Level
        secs, cur = [], []
        for l in lines:
            if l.startswith("--"):
                secs.append(cur)
                cur = []
            elif l:
                cur.append(l)
        secs.append(cur)
        after = False
        for sec in secs:
            if any(l.startswith("Item Level:") for l in sec):
                after = True
                continue
            if after:
                mods += [l for l in sec if ":" not in l and l not in ("Corrupted", "Unidentified")]
    return {"name": name, "base": base, "cls": cls, "rarity": rarity, "tier": tier, "mods": mods,
            "corrupted": "Corrupted" in lines, "text": text}


def kind_of(item):
    c = (item.get("cls") or "").lower()
    if "waystone" in c or "map" in c and "tablet" not in c:
        return "waystones"
    if "tablet" in c:
        return "tablets"
    return "others"


def new_entry(item, kind):
    return {"id": _id(), "name": item["name"], "base": item["base"], "cls": item["cls"], "rarity": item["rarity"],
            "tier": item.get("tier"), "mods": item["mods"], "key_mods": [], "text": item["text"],
            "count": 1, "lasts": 1 if kind == "waystones" else 10, "price": None, "priced_at": None,
            "price_src": "auto", "manual": None, "price_note": ""}


def entry_price(e):
    """What one of them costs, in divines: your own price if you typed one, else the checked one."""
    if e.get("price_src") == "manual" and isinstance(e.get("manual"), (int, float)):
        return float(e["manual"])
    return e.get("price") if isinstance(e.get("price"), (int, float)) else None


def cost_per_run(ver):
    """-> (divines a run, [(label, divines a run)], unknown count)."""
    parts, unknown = [], 0
    for kind in ("waystones", "tablets", "others"):
        for e in ver.get(kind) or []:
            p = entry_price(e)
            if p is None:
                unknown += 1
                continue
            per = p * max(1, int(e.get("count") or 1)) / max(1, int(e.get("lasts") or 1))
            parts.append((f"{e.get('count', 1)}× {e['name']}" + (f" / {e['lasts']} runs" if (e.get("lasts") or 1) > 1 else ""),
                          per))
    extra = float(ver.get("extra") or 0)
    if extra:
        parts.append(("other costs", extra))
    return sum(p for _l, p in parts), parts, unknown


def what_changed(old, new):
    """A short line: what this version changed from the one before."""
    out = []
    for kind in ("waystones", "tablets", "others"):
        a = {e["name"]: e.get("count", 1) for e in old.get(kind) or []}
        b = {e["name"]: e.get("count", 1) for e in new.get(kind) or []}
        for nm in sorted(set(a) | set(b)):
            if nm not in a:
                out.append(f"+{b[nm]} {nm}")
            elif nm not in b:
                out.append(f"-{a[nm]} {nm}")
            elif a[nm] != b[nm]:
                out.append(f"{nm} {a[nm]}→{b[nm]}")
    ta = {t["name"]: t.get("points", 0) for t in old.get("atlas", {}).get("trees", [])}
    tb = {t["name"]: t.get("points", 0) for t in new.get("atlas", {}).get("trees", [])}
    for nm in sorted(set(ta) | set(tb)):
        if ta.get(nm) != tb.get(nm):
            out.append(f"{nm} {ta.get(nm, 0)}→{tb.get(nm, 0)} pts")
    if (old.get("extra") or 0) != (new.get("extra") or 0):
        out.append(f"other costs {old.get('extra') or 0:g}→{new.get('extra') or 0:g}")
    return ", ".join(out) or "-"


# ---------------------------------------------------------------- loot
_LEAD = re.compile(r"^\s*(\d{1,5})\s*[x×]?\s+(?=\D)", re.I)


def parse_drops(text):
    """Copied drops (one or many Ctrl+Alt+C / Ctrl+C texts) or typed lines ("7 Divine Orb", "Divine Orb x7") ->
    [(name, qty)]."""
    from .wealth import parse_stack
    from .remnant import split_qty
    text = str(text or "").replace("\r", "")
    out = []
    if "Item Class:" in text:
        # a copied item has no empty line in it: empty lines (and "Item Class:") separate items from typed lines
        blocks = [b for chunk in re.split(r"\n\s*\n", text) for b in re.split(r"(?=^Item Class:)", chunk, flags=re.M)]
        for b in blocks:
            if not b.strip().startswith("Item Class:"):
                for line in b.split("\n"):
                    if line.strip():
                        out += parse_drops(line)
                continue
            st = parse_stack(b)
            if st:
                out.append((st[0], st[1]))
                continue
            it = parse_item(b)
            if it:
                out.append((it["name"] if it["rarity"].lower() == "unique" else it["base"] if it["rarity"].lower()
                            in ("rare", "magic") else it["name"], 1))
        return out
    for line in text.split("\n"):
        line = line.strip().strip("-•*").strip()
        if not line:
            continue
        m = _LEAD.match(line)
        if m:
            out.append((line[m.end():].strip(), int(m.group(1))))
        else:
            out.append(split_qty(line))
    return [(n, q) for n, q in out if n]


def merge_drops(drops):
    got = {}
    for n, q in drops:
        key = n.lower()
        if key in got:
            got[key] = (got[key][0], got[key][1] + q)
        else:
            got[key] = (n, q)
    return list(got.values())


def price_drops(drops, match, value_of):
    """[(name, qty)] -> [{"name", "qty", "each", "total"}] (each / total None: poe.ninja has no price for it)."""
    rows = []
    for n, q in merge_drops(drops):
        real = match(n) or n
        each = value_of(real)
        rows.append({"name": real, "qty": q, "each": each, "total": None if each is None else each * q})
    rows.sort(key=lambda r: -(r["total"] or 0))
    return rows


def loot_total(items):
    return sum(r["total"] for r in items if isinstance(r.get("total"), (int, float)))


# ---------------------------------------------------------------- logs and figures
def new_log(sid, v, start, end, runs, cost, items, note="", map_secs=None, loot=None, profit=None):
    if loot is None and (items or profit is None):
        loot = loot_total(items)
    if loot is None:                              # only the profit was typed
        loot = profit + cost
    if profit is None:
        profit = loot - cost
    return {"id": _id(), "setup": sid, "v": v, "start": start, "end": end, "runs": int(runs), "map_secs": map_secs,
            "cost": round(float(cost), 4), "loot": None if loot is None else round(float(loot), 4),
            "profit": None if profit is None else round(float(profit), 4), "items": items, "note": note,
            "skipped": False}


def logs_of(d, sid=None, v=None):
    return [l for l in d["logs"] if (sid is None or l["setup"] == sid) and (v is None or l["v"] == v)]


def figures(logs):
    """The numbers at the top of a setup: runs, time, cost / loot / profit per run, div / hour, return on cost,
    spread (how much profit per run moves from log to log), best and worst log."""
    runs = sum(l["runs"] for l in logs)
    secs = sum(max(0.0, l["end"] - l["start"]) for l in logs)
    money = [l for l in logs if not l.get("skipped") and isinstance(l.get("profit"), (int, float))]
    mruns = sum(l["runs"] for l in money)
    msecs = sum(max(0.0, l["end"] - l["start"]) for l in money)
    cost = sum(l["cost"] for l in money)
    loot = sum(l["loot"] or 0 for l in money)
    profit = sum(l["profit"] for l in money)
    ppr = [l["profit"] / l["runs"] for l in money if l["runs"]]
    lpr = [(l["loot"] or 0) / l["runs"] for l in money if l["runs"]]
    map_secs = [l["map_secs"] / l["runs"] for l in logs if l.get("map_secs") and l["runs"]]
    return {"runs": runs, "logs": len(logs), "money_logs": len(money), "secs": secs,
            "avg_run": secs / runs if runs else None, "fastest": min(map_secs) if map_secs else None,
            "cost_run": cost / mruns if mruns else None, "loot_run": loot / mruns if mruns else None,
            "loot_run_median": statistics.median(lpr) if lpr else None,
            "profit_run": profit / mruns if mruns else None, "profit": profit, "loot": loot, "cost": cost,
            "per_hour": profit * 3600 / msecs if msecs >= 60 else None, "roi": loot / cost if cost else None,
            "spread": statistics.pstdev(ppr) if len(ppr) > 1 else None,
            "best": max(money, key=lambda l: l["profit"] / max(1, l["runs"]), default=None),
            "worst": min(money, key=lambda l: l["profit"] / max(1, l["runs"]), default=None)}


def loot_table(logs):
    """Every drop over these logs: [{"name", "qty", "total", "share"}] - what the money comes from."""
    got = {}
    for l in logs:
        for r in l.get("items") or []:
            g = got.setdefault(r["name"], {"name": r["name"], "qty": 0, "total": 0.0})
            g["qty"] += r.get("qty") or 0
            g["total"] += r.get("total") or 0
    rows = sorted(got.values(), key=lambda g: -g["total"])
    whole = sum(g["total"] for g in rows) or 1
    for g in rows:
        g["share"] = g["total"] / whole
    return rows


# ---------------------------------------------------------------- export / import
def _when(t):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) if t else ""


def logs_csv(d, sids=None):
    """One row per log - the Farm Ledger's CSV (the same columns in every export)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_LOG_HEAD)
    names = {s["id"]: s["name"] for s in d["setups"]}
    for n, l in enumerate(sorted((l for l in d["logs"] if sids is None or l["setup"] in sids), key=lambda l: l["start"]), 1):
        mins = max(0.0, l["end"] - l["start"]) / 60
        w.writerow((names.get(l["setup"], ""), l["v"], n, _when(l["start"]), _when(l["end"]), l["runs"], f"{mins:.1f}",
                    _f(l["cost"]), _f(l.get("loot")), _f(l.get("profit")),
                    _f(l["profit"] / l["runs"]) if isinstance(l.get("profit"), (int, float)) and l["runs"] else "",
                    _f(l["profit"] * 60 / mins) if isinstance(l.get("profit"), (int, float)) and mins else "",
                    l.get("note") or "", "; ".join(f"{r['qty']}x {r['name']}" for r in l.get("items") or [])))
    return buf.getvalue()


def loot_csv(d, sids=None):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_LOOT_HEAD)
    names = {s["id"]: s["name"] for s in d["setups"]}
    for n, l in enumerate(sorted((l for l in d["logs"] if sids is None or l["setup"] in sids), key=lambda l: l["start"]), 1):
        for r in l.get("items") or []:
            w.writerow((names.get(l["setup"], ""), l["v"], n, _when(l["start"]), r["name"], r["qty"], _f(r.get("each")),
                        _f(r.get("total"))))
    return buf.getvalue()


def _f(x):
    return "" if not isinstance(x, (int, float)) else f"{x:.4f}".rstrip("0").rstrip(".")


def import_logs_csv(d, sid, v, text):
    """Rows in the Farm Ledger CSV layout -> logs on this setup. -> how many were added."""
    rows = list(csv.DictReader(io.StringIO(text)))
    n = 0
    for r in rows:
        try:
            start = time.mktime(time.strptime(r["start"], "%Y-%m-%d %H:%M"))
            end = time.mktime(time.strptime(r["end"], "%Y-%m-%d %H:%M")) if r.get("end") else start
            runs = int(float(r.get("runs") or 1))
            cost = float(r.get("cost_div") or 0)
            loot = float(r["loot_div"]) if r.get("loot_div") else None
            profit = float(r["profit_div"]) if r.get("profit_div") else None
        except (KeyError, ValueError):
            continue
        items = []
        for part in (r.get("loot") or "").split(";"):
            m = re.match(r"\s*(\d+)x\s+(.+)", part)
            if m:
                items.append({"name": m.group(2).strip(), "qty": int(m.group(1)), "each": None, "total": None})
        d["logs"].append(new_log(sid, v, start, end, runs, cost, items, r.get("note") or "", loot=loot,
                                 profit=profit))
        n += 1
    return n


def setup_json(d, sid):
    s = setup(d, sid)
    return json.dumps({"farm_ledger": 1, "setup": s, "logs": logs_of(d, sid)}, indent=1, ensure_ascii=False)


def import_setup_json(d, text):
    j = json.loads(text)
    if not isinstance(j, dict) or "setup" not in j:
        raise ValueError("not a Farm Ledger setup file")
    s = j["setup"]
    old = s["id"]
    s["id"] = _id()
    if any(x["name"] == s["name"] for x in d["setups"]):
        s["name"] += " (imported)"
    d["setups"].append(s)
    for l in j.get("logs") or []:
        if l.get("setup") == old:
            l = dict(l, setup=s["id"], id=_id())
            d["logs"].append(l)
    return s


def summary(s, f, v=None):
    """One line for Discord."""
    if not f["runs"]:
        return f"{s['name']}: no runs logged yet."
    ph = f"{f['per_hour']:.1f} div/h" if f.get("per_hour") is not None else "no profit logged"
    pr = f" ({f['profit_run']:+.2f} a run)" if f.get("profit_run") is not None else ""
    return f"{s['name']}{f' v{v}' if v else ''}: {ph} over {f['runs']} runs{pr} - Farm Ledger, StashOfExile2"
