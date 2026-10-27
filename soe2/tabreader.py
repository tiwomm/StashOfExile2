"""Price checks > Add items from: Stash tab (2.8.0).

Instead of copying items one by one with Ctrl+Alt+C, read a whole public stash tab and add everything on it to the
Price checks list. It works like Wealth's synced tabs: in game, make a Premium stash tab public and give the whole tab
one price nobody would pay (e.g. 37882 Divine Orbs). That odd price is how the app finds YOUR tab on the trade site:
it searches your account's listings at exactly that price, reads them, and turns each into the same text a Ctrl+Alt+C
copy gives (wealth.item_text). Each one is then priced like any other item.

Only when you press Read tab; searches and fetches share the trade site's limits with everything else, one at a time,
behind your own price checks. Items already in the list are skipped. Your own marker listings can't distort prices:
they're far above anything real, and price searches sort cheapest first."""
import re
import time

import requests

from .config import BASE, P, SETTINGS
from .net import call
from .wealth import item_text, wealth_children, wealth_query

PCTAB = {"gen": 0, "running": False, "cancel": False, "msg": "", "found": 0, "read": 0, "error": "", "warnings": [],
         "qid": None, "skipped": {}, "log": []}
LOG_FILE = "tab_reader_log.txt"        # 2.8.1: what happened to every listing of the last read (for problem reports)
PCTAB_PRIO = 4                     # behind the item pricing it creates (0-2), ahead of a Wealth sync (5-9)


def account_ok(acc):
    return bool(re.search(r"#\d+$", (acc or "").strip()))


class TabReaderJobs:
    """Engine jobs (mixed into Engine: same thread as every other trade-site request)."""

    def pctab_start(self, account, amount, currency):
        """Queue reading one tab. -> error text or None."""
        league = SETTINGS.get("league")
        if PCTAB["running"]:
            return "Already reading a tab."
        if not league:
            return "Pick a league first (Settings)."
        if not account_ok(account):
            return "Type your account name with its number, e.g. YourName#1234 (it's shown on the trade site)."
        if not amount or amount <= 0:
            return "Type the price you put on the tab in game (e.g. 37882) and pick its currency."
        PCTAB["gen"] += 1
        PCTAB.update(running=True, cancel=False, msg="Searching your tab…", found=0, read=0, error="", warnings=[],
                     qid=None, seen=set(), skipped={}, log=[f"{time.strftime('%Y-%m-%d %H:%M:%S')}  league {league}, "
                                                          f"tab price {amount} {currency}"],
                     league=league, account=account.strip(),
                     tab={"id": "pctab", "label": "the tab", "amount": amount, "currency": currency})
        self.add(PCTAB_PRIO, "pctab_search", PCTAB["gen"], {}, "top", "")
        self.add(PCTAB_PRIO + 0.5, "pctab_finish", PCTAB["gen"])
        return None

    def _pctab_live(self, gen):
        return PCTAB["running"] and PCTAB["gen"] == gen and not PCTAB["cancel"] and not PCTAB["error"]

    def do_pctab_search(self, gen, extra, level, label):
        if not self._pctab_live(gen):
            return
        PCTAB["msg"] = "Searching your tab" + (f" ({label})" if label else "") + "…"
        self.ui_q.put(("pctab", "progress"))
        try:
            res = call("POST", f"{BASE}/search/poe2/{requests.utils.quote(PCTAB['league'])}",
                       json=wealth_query(PCTAB["account"], PCTAB["tab"], extra))
        except Exception as e:
            PCTAB["error"] = f"The search failed: {str(e)[:200]}"
            return
        total, ids, qid = int(res.get("total") or 0), list(res.get("result") or []), res.get("id")
        if level == "top":
            PCTAB["found"], PCTAB["qid"] = total, qid
            PCTAB["log"].append(f"search: {total} listing(s) at that price")
        kids = wealth_children(extra, level) if total > len(ids) and ids else []
        if kids:                                       # more than one search can return: split it up, like Wealth
            for ex, lv, lab in kids:
                self.add(PCTAB_PRIO, "pctab_search", gen, ex, lv, f"{label}, {lab}" if label else lab)
            return
        if total > len(ids):
            PCTAB["warnings"].append(f"{label or 'The tab'} has {total} items, but only {len(ids)} can be read.")
        new = [i for i in ids if i not in PCTAB["seen"]]
        PCTAB["seen"].update(new)
        for i in range(0, len(new), 10):
            self.add(PCTAB_PRIO, "pctab_fetch", gen, qid, new[i:i + 10])

    def do_pctab_fetch(self, gen, qid, ids):
        if not self._pctab_live(gen):
            return
        PCTAB["msg"] = f"Reading items… ({PCTAB['read']} so far)"
        try:
            res = call("GET", f"{BASE}/fetch/{','.join(ids)}", params={"query": qid})
        except Exception as e:
            PCTAB["error"] = f"Reading the items failed: {str(e)[:200]}"
            return
        acc, tab = PCTAB["account"].lower(), PCTAB["tab"]
        for e in res.get("result") or []:
            if not e:
                continue
            lst, it = e.get("listing") or {}, e.get("item") or {}
            p = lst.get("price") or {}
            owner = str((lst.get("account") or {}).get("name") or "").lower()
            mine = not owner or owner == acc or owner.split("#")[0] == acc.split("#")[0] and ("#" not in owner or
                                                                                         "#" not in acc)
            name = f"{it.get('name') or ''} {it.get('typeLine') or ''}".strip()
            why = ("someone else's listing" if not mine else
                   f"priced {p.get('amount')} {p.get('currency')}, not the tab's price"
                   if p.get("amount") != tab["amount"] or p.get("currency") != tab["currency"] else
                   "unique" if it.get("frameType") == 3 else
                   "a stack (currency etc.)" if it.get("stackSize") else
                   "not an item the price checker reads" if it.get("frameType", 0) not in (0, 1, 2) else None)
            if why:
                PCTAB["skipped"][why.split(",")[0] if why.startswith("priced") else why] = \
                    PCTAB["skipped"].get(why.split(",")[0] if why.startswith("priced") else why, 0) + 1
                PCTAB["log"].append(f"skipped ({why}): {name}")
                continue
            try:
                text = item_text(it)
            except Exception as ex:                     # 2.8.1: one odd listing mustn't stop the rest
                PCTAB["skipped"]["couldn't be read"] = PCTAB["skipped"].get("couldn't be read", 0) + 1
                PCTAB["log"].append(f"couldn't turn into item text ({ex!r}): {name}")
                continue
            PCTAB["read"] += 1
            self.ui_q.put(("pctab", "item", text))
        self.ui_q.put(("pctab", "progress"))

    def do_pctab_finish(self, gen):
        if PCTAB["gen"] != gen:
            return
        PCTAB["log"].append(f"read {PCTAB['read']} item(s) from {PCTAB['found']} listing(s)")
        PCTAB["running"] = False
        self.ui_q.put(("pctab", "done"))


def write_log(lines):
    try:
        with open(P(LOG_FILE), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass
