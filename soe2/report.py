"""A problem report (2.3.0): one .zip you can send when something prices badly or goes wrong. It holds the copied
item texts of your recent price checks with what the app did with them, and the app's own log files. No account
name, no Wealth data, no settings."""
import json
import os
import time
import zipfile

from .config import APP_VERSION, P

LOGS = ("error_log.txt", "verify_log.txt", "currency_log.txt", "unpriced_items.txt")


def make_report(path, records, limit=60):
    """-> number of price checks put in the report."""
    recs = sorted(records.values(), key=lambda r: r.get("id", 0))[-limit:]
    out = []
    for r in recs:
        out.append({"item_text": r.get("raw", ""), "state": r.get("state"), "result": r.get("label"),
                    "estimate_div": r.get("est"), "confidence": r.get("conf"), "listings": r.get("total"),
                    "check_by_hand": bool(r.get("manual")), "no_match": bool(r.get("nomatch")),
                    "searches": [{"name": s.get("name"), "found": s.get("total"), "used": s.get("n"),
                                  "cheapest": [list(p) for p in (s.get("prices") or [])[:5]]}
                                 for s in (r.get("stages") or [])],
                    "mods": [{"text": m.get("text"), "stat": m.get("sid"), "note": m.get("note")}
                             for m in (r.get("item") or {}).get("mods", [])]})
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("about.txt", f"StashOfExile2 v{APP_VERSION} problem report, made "
                                f"{time.strftime('%Y-%m-%d %H:%M:%S')}.\n{len(out)} recent price checks are in "
                                "price_checks.json; the app's log files are next to it.\n")
        z.writestr("price_checks.json", json.dumps(out, indent=1, ensure_ascii=False))
        for name in LOGS:
            p = P(name)
            if os.path.exists(p):
                with open(p, "rb") as f:
                    data = f.read()[-400_000:]                 # the end of a long log is what matters
                z.writestr(name, data)
    return len(out)
