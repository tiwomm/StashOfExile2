"""Currency Exchange item names (cxnames.json, from RePoE's export of the game files) and the flip check's arithmetic.

2.92.0: what is left of the Arbitrage tab (exchange_page.py). Arbitrage read Grinding Gear Games' hourly Currency
Exchange history from an address outside their documented API; it was removed as deprecated - GGG's terms for that
data are unclear. Nothing here makes a request."""
import os

HUB_NAMES = {"divine": "Divine Orb", "exalted": "Exalted Orb", "chaos": "Chaos Orb"}
# 2.26.0: the history now names items by their game id; the three hubs are turned back into the short names the
# loop finder works with (old cached hours used the short names already). Before this, no loop was ever found.
_NAMES = {}


def item_name(cid):
    """A Currency Exchange id -> its name (cxnames.json, from RePoE), or None."""
    if cid in HUB_NAMES:
        return HUB_NAMES[cid]
    if not _NAMES:
        import json
        from .config import APP_DIR, P
        try:
            from .config import RESOURCE_DIR
        except ImportError:
            RESOURCE_DIR = APP_DIR
        for path in (P("cxnames.json"), os.path.join(RESOURCE_DIR, "cxnames.json"), os.path.join(APP_DIR, "cxnames.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    _NAMES.update(json.load(f))
                break
            except (OSError, ValueError):
                continue
        _NAMES.setdefault("_loaded", "1")
    return _NAMES.get(cid)


def flip(buy, sell):
    """You can buy 1 X for `buy` Y and sell 1 X for `sell` Y. -> (Y gained per X, margin as a fraction)."""
    if not buy or buy <= 0 or sell is None:
        return None, None
    return sell - buy, (sell - buy) / buy
