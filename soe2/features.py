"""2.131.0 Feature Picker (feedback: "ask a person what features they're interested in ... Menu options to
enable/disable features ... Any disabled features should not listen for their hotkey"): the app's features in a few
groups, each one switch. Off: its pages leave the menu and its keys do nothing (the game gets them); its data is
kept. Asked once in a popup (new installs and once after updating): closed without choosing, it comes back at the
next start; "Never ask again" stops it for good. The same switches live in Settings › General › Features (one place
in Settings). The beta features are a cluster of their own - this replaces the single "Show beta features" switch."""
from .config import SETTINGS

GROUPS = (
    {"key": "price", "name": "Price checking", "keys": "pc_key",
     "what": "Price the item under your mouse: Price Checks, Favorites, Mod Book, Rate Mods.",
     "modules": ("pricecheck", "favorites", "modbook", "ratemods", "library")},
    {"key": "bulk", "name": "Bulk Pricing", "keys": "Ctrl+Alt+C",
     "what": "Price many tablets, waystones and jewels at once, in the background. Other items work, but it isn't "
             "built for them - price expensive items by hand.",
     "modules": ("checks",)},
    {"key": "overlay", "name": "Game Overlay", "keys": "its keys",
     "what": "Over the game: the timer bar, Notes, Calc, Regex and the helpers (Breach, Delirium, Ritual, Expedition, "
             "Trade whispers...).",
     "modules": ("ovset", "notes", "regex")},
    {"key": "planning", "name": "Planning & Farming", "keys": "",
     "what": "League Plan, Map Library, Leaderboards.",
     "modules": ("plan", "maps", "leaderboards")},
    {"key": "rates", "name": "Exchange Rates", "keys": "",
     "what": "Currency rates from poe.ninja, and the Rates menu on the Game Overlay.",
     "modules": ("rates",)},
)
BETA = (
    {"key": "wealth", "name": "Wealth", "what": "What your stash is worth: Scan stash, totals over time.",
     "modules": ("wealth",)},
    {"key": "insights", "name": "Market Insights", "what": "What sells, and for how much, over time.",
     "modules": ("insights",)},
    {"key": "search", "name": "Game Search", "what": "Search the game's items and mods.", "modules": ("search",)},
    {"key": "money", "name": "Money Makers", "what": "Community farming strats and the Craft Helper.",
     "modules": ("money",)},
    # 2.132.2 (feedback: "anything else helper-wise until it's fully tested and checklist approved should be marked
    # beta. desecration helper can come out of beta"): the newer helpers are BETA; the Desecration Helper isn't
    {"key": "topup", "name": "Top Up Reminders", "what": "What's running low in your inventory, back from a map.",
     "modules": (), "was": ("topup", "on")},
    {"key": "breaks", "name": "Break reminders", "what": "A kind nudge in long sessions, in your hideout or a town.",
     "modules": (), "was": ("breaks", "on")},
    {"key": "mapprofit", "name": "Map profit", "what": "What each map earned, from your inventory - on your PC only.",
     "modules": (), "was": ("map_profit", "on")},
    {"key": "temple", "name": "Temple Helper", "what": "Your crystals on the bar, and a card when they're full.",
     "modules": (), "was": ("temple", "on")},
)
ALL = GROUPS + BETA
# the Overlay page (the session timer) holds the overlay's settings and the planning pages: shown while either is on
SHARED = {"tracker": ("overlay", "planning")}


def cfg():
    """{feature: on} - every group on and the beta ones as the old Beta features switch was, until you choose."""
    c = SETTINGS.setdefault("features", {})
    for g in GROUPS:
        c.setdefault(g["key"], True)
    beta = bool(SETTINGS.get("labs"))
    for g in BETA:
        was = g.get("was")                     # (2.132.2: a helper you already use stays on as it becomes BETA)
        c.setdefault(g["key"], beta or bool(was and (SETTINGS.get(was[0]) or {}).get(was[1])))
    c.pop("desecrate", None)                   # (2.132.2: the Desecration Helper isn't BETA any more)
    return c


def on(key):
    return bool(cfg().get(key, True))


def beta_on(key, value=True):
    """2.132.2: turning a BETA helper on turns its feature on too (as Features shows it)."""
    if value and not on(key):
        set_on(key, True)


def group_of(module_key):
    for g in ALL:
        if module_key in g["modules"]:
            return g["key"]
    return None


def module_on(module_key):
    """Is this page's feature on? (A page in no group - Settings, the Overlay page's own - always is.)"""
    if module_key in SHARED:
        return any(on(k) for k in SHARED[module_key])
    g = group_of(module_key)
    return True if g is None else on(g)


def any_beta():
    return any(on(g["key"]) for g in BETA)


def set_on(key, value):
    cfg()[key] = bool(value)
    SETTINGS["labs"] = any_beta()          # (older code: "a beta feature is on")


def asked():
    """None (ask), "done" (answered) or "never" (Never ask again)."""
    return SETTINGS.get("features_asked")
