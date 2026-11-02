"""CSV exports for the data-minded (2.2.0): every map run, every session, Wealth's history and items.
Plain comma-separated files that open in Excel, Google Sheets or LibreOffice; times are in seconds and as m:ss."""
import csv
from datetime import datetime

from .tracker import fmt_time, MIN_RUN_SECS


def _when(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else ""


def write_map_runs(path, sessions, current=None):
    """One row per map run, oldest first. -> rows written."""
    pool = list(sessions) + ([current] if current is not None and current not in sessions else [])
    n = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["session_started", "map", "area_level", "entered_at", "time_seconds", "time", "times_entered",
                    "deaths", "counted_as_run"])
        for s in pool:
            live = s.where.get("map") if (s.ended is None and s.where) else None
            for i, m in enumerate(s.maps):
                t = s.current_map_time() if live == i else m["time"]
                w.writerow([_when(s.started), m["name"], m.get("level") or "", _when(m.get("first")), round(t or 0),
                            fmt_time(t), m.get("entries", 1), m.get("deaths", 0),
                            "yes" if (t or 0) >= MIN_RUN_SECS else "no (under 30 s)"])
                n += 1
    return n


def write_sessions(path, sessions):
    n = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        # 2.54.0: no wealth / profit columns - profit is tracked in Money Makers › Farm Ledger (its own CSV)
        w.writerow(["started", "ended", "length_seconds", "length", "maps", "average_map_seconds", "deaths", "note"])
        for s in sessions:
            avg = s.avg_map_time()
            w.writerow([_when(s.started), _when(s.ended), round(s.elapsed()), fmt_time(s.elapsed()), s.map_count(),
                        "" if avg is None else round(avg), s.deaths, s.note])
            n += 1
    return n


def write_wealth_history(path, snapshots, league=None):
    n = 0
    cats = sorted({c for sn in snapshots for c in (sn.get("by_cat") or {})})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "league", "total_div", "items"] + [f"{c}_div" for c in cats])
        for sn in snapshots:
            if league and sn.get("league") != league:
                continue
            w.writerow([_when(sn.get("ts")), sn.get("league", ""), round(sn.get("total") or 0, 3), sn.get("n", "")]
                       + [round((sn.get("by_cat") or {}).get(c, 0), 3) for c in cats])
            n += 1
    return n


def write_wealth_items(path, rows):
    """rows: wealth_rows() output [(item, each, total, source)]."""
    n = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item", "base", "tab", "quantity", "each_div", "total_div", "price_from"])
        for it, each, tot, src in rows:
            w.writerow([it.get("name") or it.get("type"), it.get("type") or it.get("base", ""), it.get("stash", ""),
                        it.get("qty", 1), "" if each is None else round(each, 4), "" if tot is None else round(tot, 4),
                        src or ""])
            n += 1
    return n
