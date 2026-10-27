"""The welcome / what's new card (2.0 beta 12): shown once after a fresh install and once after each update.

INTRO says what the app is; NOTES has a few plain lines per version, newest first. The full history stays in the
launcher (stashofexile2.py, VERSION HISTORY)."""
from .updates import vtuple

INTRO = [
    "StashOfExile2 runs next to Path of Exile 2 and prices your items for you.",
    "To price an item: hover it in game and press Ctrl+Alt+C. It appears in Price checks with what it's worth and "
    "what to list it for. It works best on tablets, jewels and waystones.",
    "The bar on the left opens everything. Tools work while their window is open; Utilities (chat keys, the sticky "
    "note, the Delirium alert) keep working over the game.",
    "Your league is in Settings (bottom left). Things marked BETA are still being worked on: turn them on under "
    "Settings > General > Labs if you'd like to try them.",
]

# What's being worked on (2.4.0: not shown in the app any more - kept for ROADMAP.md / the developer).
NEXT = [
    "2.9: deciding what Wealth, the Session tracker, Game search and Top value need to leave Labs.",
]

# What's new, per version: only what helps you use the app - what you can do now and where to find it.
NOTES = {
    "2.8.0": [
        "Price checks can read a whole stash tab: pick Add items from > Stash tab, type the price you put on the tab "
        "and press Read tab. Every item on it is added and priced - no Ctrl+Alt+C one by one.",
        "The tab has to be a public Premium tab with one price on the whole tab (like 37882 Divine Orbs). The same "
        "tab works for Wealth.",
    ],
    "2.7.2": [
        "Fixed: windows could still slip behind the app's main window and leave only the desktop showing.",
    ],
    "2.7.1": [
        "Fixed: with Always on top switched on, the app's windows were open but hidden behind its main window.",
    ],
    "2.7.0": [
        "Session tracker counts only your own deaths, not your party's. Type your character name in Options, or "
        "let the app work it out.",
        "When the game turns AFK off, a session that AFK paused carries on by itself.",
        "Map stats shows how many maps you ran each day, over the last two weeks.",
    ],
    "2.6.0": [
        "Mod book has Waystone rules and Relic rules: rate each mod High, Normal or Ignore, like tablet mods.",
        "Regex marks the mods you rate High with ★, and ★ Select valuable picks them.",
        "Top value shows your ★ waystone and relic mods, and the best item you've priced with each.",
        "Waystone and relic ratings are kept apart from tablet and jewel ones, so a jewel rule no longer shows up on "
        "a relic mod with the same wording.",
    ],
    "2.5.0": [
        "Price checks: the item panel has Search filters - who's selling, what they price in, corrupted or not, and "
        "for gear item level, quality, sockets and whether to compare with the same base only. They change the "
        "search for that item only; press Search with these values.",
        "A Wiki link next to Under the hood opens the item's base type on the community wiki.",
    ],
    "2.4.0": [
        "Every list works the same way: Ctrl+click or Shift+click to pick several, Ctrl+A for all, Delete to "
        "remove, and Ctrl+Z (or Undo) to put them back.",
        "Wealth: Delete works again, Clear… empties the item list (your tabs and history stay), and Undo puts "
        "things back.",
        "Regex: your saved searches are now Favorites, in their own tab - every item type in one list, with Copy, "
        "Rename and \"Use for the Regex key\".",
        "Exchange rates has tabs: Rates, Exchange Helper, and Arbitrage - currencies the Currency Exchange priced "
        "differently in the last few hours, from Grinding Gear Games' own trade history. There's also a check for a "
        "flip you see in game.",
        "Top value remembers what you've priced even after you clear Price checks, and shows the mods and price of "
        "the dearest listings seen.",
        "Session tracker > Options explains how profit per hour works, and tells you when Wealth needs setting up "
        "first.",
    ],
    "2.3.0": [
        "Wealth has a step-by-step setup: count your currency, then (if you like) add a stash tab. It opens the first "
        "time, and \"Set up step by step\" in Wealth brings it back.",
        "Wealth says how much you're up or down since yesterday. Snapshots say why they were taken - pick two to see "
        "what changed between them.",
        "Prices you set yourself in Wealth are shown in blue. Right-click an item to go back to the market price.",
        "Jewels and tablets get a price more often: when the listings vary a lot you get a rough price to look at "
        "instead of \"check by hand\".",
        "One very cheap or very dear listing no longer throws the price off.",
        "Deleting many price checks at once no longer freezes the app.",
        "Session tracker > Options: the opacity slider no longer sits on top of its label.",
        "Session tracker no longer has \"gold from selling\" - the game doesn't give a reliable way to count it.",
        "Price checks still missing? Settings > Advanced > Problem report saves them in a zip you can share.",
    ],
    "2.2.0": [
        "Regex key: set a key in the Regex window (or Settings > Hotkeys) and pick which search it copies. Press it "
        "in game, then Ctrl+F and Ctrl+V in your stash.",
        "Exchange rates > Currency Exchange helper: pick what you sell and what you want, and it shows the ratio to "
        "post - quick sale, fair or patient - in whole numbers like the game asks for.",
        "Export to a spreadsheet (CSV): Session tracker > Map stats and Past sessions, and Wealth > More.",
    ],
    "2.1.0": [
        "Session tracker > Map stats: every map you've run, how many times, your best and average time, and a "
        "leaderboard of your fastest runs for each map.",
        "Top value (Labs): the most valuable tablets, waystones and jewels you've priced, the mods worth the most, and "
        "the dearest listings your price checks came across.",
        "The clock is 12-hour or 24-hour (Settings > Appearance); it starts out the way your Windows clock is set.",
    ],
    "2.0.0": [
        "Pick how the app looks: Settings > Appearance > Look of the app has themes, accent colours and text size.",
        "A start-up screen shows while the app loads (you can turn it off in Settings > Appearance).",
        "Check for updates only ever offers a newer version.",
        "The sticky note's colours are set in the Notes window. Move and resize the note by dragging it.",
    ],
    "2.0.0-beta.22": [
        "Price checks: the # column shows the order you copied items in. Press \"Order added\" to go back to it "
        "after sorting by price.",
    ],
    "2.0.0-beta.21": [
        "Settings has tabs: General, Appearance, Hotkeys and Advanced.",
        "Choose whether things open from the bar on the left, from icons on the desktop, or both "
        "(Settings > Appearance).",
        "Calculator: type a sum and press Enter. 12k means 12,000.",
        "Wealth: select several rows (Ctrl+A for all) and press Delete to remove them. \"How it works\" explains "
        "each part.",
        "Price checks is made for tablets, jewels and waystones. Prices for other gear are only a rough guess - "
        "check those yourself.",
    ],
    "2.0.0-beta.20": [
        "Regex: ★ marks mods your Mod book counts as valuable. \"★ Select valuable\" builds a stash search for all "
        "of them. Right-click a mod to rate it.",
    ],
    "2.0.0-beta.19": [
        "Price checks: select items and press Delete (or the Del key) to remove them. Ctrl+Z brings them back.",
    ],
    "2.0.0-beta.18": [
        "Waystones can be price-checked. They're priced on the numbers at the top (drop chance, pack size, rarity "
        "...), not on the monster mods.",
    ],
    "2.0.0-beta.17": [
        "Hotkeys can use the middle or side mouse buttons, e.g. hover a tablet and press a side button to copy it.",
    ],
    "2.0.0-beta.16": [
        "To set a hotkey, click its box and press the key. Esc keeps the old one; right-click clears it.",
    ],
    "2.0.0-beta.15": [
        "The sticky note and the session timer only show while the game is in front.",
    ],
    "2.0.0-beta.14": [
        "\"Under the hood\" (top right of Price checks) shows how an item was read - only if you're curious.",
    ],
    "2.0.0-beta.13": [
        "First start asks which league you play.",
    ],
    "2.0.0-beta.12": [
        "This card: a short what's new after each update. Toolkit menu > What's new shows it again.",
    ],
    "2.0.0-beta.10": [
        "Game search (Labs): look up any skill, support, unique, base, currency or keyword.",
        "Labs: features still being worked on are marked BETA and only show when Labs is on.",
    ],
    "2.0.0-beta.9": [
        "Session tracker (Labs): how long you play, how many maps, average map time and profit, with a timer over "
        "the game.",
        "Settings > Hotkeys lists every key the app uses; two things on one key show in red.",
    ],
    "2.0.0-beta.7": [
        "Every tool opens in its own window. Chat commands, Notes and the Delirium alert are utilities that work "
        "over the game.",
    ],
}


def notes_between(seen, current):
    """[(version, [lines])] newer than `seen` up to `current`, newest first (seen None = just the current one)."""
    cur = vtuple(current)
    out = []
    for v, lines in sorted(NOTES.items(), key=lambda kv: vtuple(kv[0]), reverse=True):
        if vtuple(v) > cur:
            continue
        if seen is None:
            if vtuple(v) == cur:
                out.append((v, lines))
            continue
        if vtuple(v) > vtuple(seen):
            out.append((v, lines))
    return out
