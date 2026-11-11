"""One name per feature (2.126.0, UX rule: "One name per feature (soe2/names.py). No synonyms.").

PAGES   - every page's name, by its module key (soe2/modules/). Page names are in Title Case.
FEATURES - the names of the parts inside pages that a person meets by name (helpers, switches, sections).
OLD     - names that were used before, or crept in as synonyms -> the one name to use. They never appear in the
          app's text; the app still knows the old page names (App.page_key), so an old saved layout or a link opens
          the right page.

Adding a feature: put its name here first, use that exact name everywhere (labels, tooltips, What's new, README).
Renaming one: change it here, add the old name to OLD, and run tools/check_names.py (it lists every leftover)."""

PAGES = {
    "pricecheck": "Price Checks",
    "checks": "Bulk Pricing",
    "favorites": "Favorites",
    "insights": "Market Insights",
    "library": "Under the Hood",
    "modbook": "Mod Book",
    "ratemods": "Rate Mods",
    "wealth": "Wealth",
    "money": "Money Makers",
    "regex": "Regex",
    "search": "Game Search",
    "rates": "Exchange Rates",
    "tracker": "Overlay",
    "maps": "Map Library",
    "leaderboards": "Leaderboards",
    "plan": "League Plan",
    "ovset": "Settings",
    "notes": "Notes",
    "settings": "Settings",
}

FEATURES = (
    "Alert card",               # 2.131.0 every helper's alert over the game (alertcard.py); 2.131.6: was "calm alert card"
    "Map profit",               # 2.132.0 what each map earned, from your inventory (Overlay ↳ Settings › Helpers)
    "Alerts show",              # 2.131.0 Overlay › Settings › Helpers: where and how big the alert card is
    "Data folder",              # 2.131.0 where your settings and lists live (Feature Picker; Settings › Advanced)
    "Feature Picker",
    "Top Up Reminders",         # 2.131.0 what's running low in your inventory (Overlay ↳ Settings › Helpers)           # 2.131.0 the popup asked once: which features you use
    "Features",                 # 2.131.0 Settings › General: one switch per feature group, plus the BETA ones
    "Break reminders",          # 2.131.0 Overlay › Settings › Helpers: a kind nudge in long sessions
    "Campaign Helper",
    "Clear All",                # Bulk Pricing › Items strip: empties the list shown
    "Community data sharing",
    "Craft Helper",
    "Data pack",                # the Craft Helper's mod data from GitHub
    "Keybinds",                 # Settings: every key the app listens for (2.127.0: was Keys)
    "Desecration Helper",       # at The Well of Souls
    "Exchange Helper",
    "Favours prices",           # the Ritual helper: prices on the Favours window's rewards
    "Tribute reminder",         # the Ritual helper: tribute left when the Favours window closes
    "Filter in the Ritual window",   # the Ritual helper: the game's hidden setting that applies your filter there
    "Mechanic Helper",
    "Quick settings",           # the overlay's ⚙
    "Reset position",           # Game Overlay › Settings › Options: the overlay back in its own place
    "Scan stash",
    "Search Options",           # Settings › Price checking
    "Session timer",
    "Stash tab",                # Price Checks › Add items from
    "Trade Whisper Watcher",
)

OLD = {
    # page names before Title Case (2.120.0) and before their renames
    "Price checks": "Price Checks",
    "Mod book": "Mod Book",
    "Map library": "Map Library",
    "Exchange rates": "Exchange Rates",
    "Game search": "Game Search",
    "Under the hood": "Under the Hood",
    "Item library": "Under the Hood",
    "Item inspector": "Under the Hood",
    "Price breakdown": "Under the Hood",
    "Utilities": "Notes",
    "Money makers": "Money Makers",
    "Market insights": "Market Insights",
    "League plan": "League Plan",
    "Bulk pricing": "Bulk Pricing",
    "Bulk Price Checker": "Bulk Pricing",
    # features
    "Calm alerts": "Alert card",          # 2.131.6 (feedback: "stop calling it calm alert card ... that sounds dumb")
    "calm alert card": "Alert card",
    "Labs": "Features",
    "Beta features": "Features",
    "Craft helper": "Craft Helper",
    "Desecration helper": "Desecration Helper",
    "Well of Souls helper": "Desecration Helper",
    "Campaign helper": "Campaign Helper",
    "Exchange helper": "Exchange Helper",
    "Mechanic helper": "Mechanic Helper",
    "Whisper watcher": "Trade Whisper Watcher",
    "Session tracker": "Session timer",
    "Stash scan": "Scan stash",
    "Quick Settings": "Quick settings",
    "Community Data Sharing": "Community data sharing",
    "How searches are made": "Search Options",
    "dearest": "most valuable",          # 2.129.0 (feedback): "nobody uses that word"
    "Clear list": "Clear All",          # Bulk Pricing's button (2.126.0: on screen, in the Items strip)
    "Settings › Keys": "Settings › Keybinds",          # 2.127.0
    "Settings > Keys": "Settings › Keybinds",
}

# an old page name that now means another page: before 2.80.0, Bulk Pricing was called "Price checks"
WAS_PAGE = {"Price checks": "checks"}

SMALL = {"a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "by", "at"}


def title_case(name):
    """True if a page name is in Title Case: every word starts with a capital, except small words inside it."""
    words = name.split()
    return all(w[:1].isupper() or (i and w in SMALL) or not w[:1].isalpha() for i, w in enumerate(words))


def key_of(name):
    """The page key for a page name, old or new (None if it isn't a page)."""
    if name in WAS_PAGE:
        return WAS_PAGE[name]
    name = OLD.get(name, name)
    return next((k for k, v in PAGES.items() if v == name and k != "ovset"), None)
