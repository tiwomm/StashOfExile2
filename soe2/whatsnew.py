"""The welcome / what's new card (2.0 beta 12): shown once after a fresh install and once after each update.

INTRO says what the app is; NOTES has a few plain lines per version, newest first. The full history stays in the
launcher (stashofexile2.py, VERSION HISTORY)."""
from .updates import vtuple

INTRO = [
    "StashOfExile2 is a toolkit for Path of Exile 2 that runs next to the game.",
    "Price checks: hover an item in game and press Ctrl+Alt+C. It's listed and priced from the trade site, using the "
    "mods that matter, and you can see what it would sell for.",
    "Everything opens as a window on the app's desktop: the dock on the left has Modules (big tools), Tools (quick "
    "helpers) and Utilities (keep working over the game: chat command keys, a sticky note, the Delirium alert).",
    "Your league and search pace are in Settings (bottom left). Features marked BETA are experimental; turn them "
    "on under Settings > General > Labs.",
]

# the roadmap, shown under "Coming next" on the card (2.0 beta 21). Keep it short and honest; the full plan is in
# ROADMAP.md next to the app.
NEXT = [
    "Wealth: a guided first setup (count currency, add a synced tab step by step), clearer totals and snapshots, "
    "and moving it out of Labs once it's solid.",
    "Waystones and relics in the Mod book, so their mods can be rated like tablet mods.",
    "Session tracker: deaths and AFK time checked against real Client.txt logs.",
    "One-key copy made reliable (or kept as an experiment), and more testing on Windows.",
    "2.1: the next round of features, starting with Wealth.",
]

NOTES = {
    "2.0.0": [
        "2.0 is here - no more beta numbers. From now on: 2.0.1, 2.0.2 for fixes, 2.1 for new features.",
        "Settings > Appearance > Look of the app: pick a theme (Midnight blue, Ember, Forest, Amethyst, Crimson, "
        "Graphite), an accent colour and a text size for every window.",
        "A start-up screen while the app loads (Settings > Appearance can turn it off).",
        "Check for updates never offers an older version.",
        "The note's colours are back in the Notes window, and the pixel boxes for its place and size are gone: just "
        "drag and resize the note.",
    ],
    "2.0.0-beta.22": [
        "The item panel in Price checks (the item, its mods with Min / Max boxes, Search with these values) is back "
        "if it had disappeared, and it can no longer be squeezed or dragged out of sight.",
        "Price checks has a # column (the order you copied items in) and an \"Order added\" button; the sorted "
        "column shows ▲ / ▼.",
    ],
    "2.0.0-beta.21": [
        "Settings has tabs: General, Appearance (launcher, wallpaper, clock, the note's colours), Hotkeys and "
        "Advanced (Mod book, Under the hood, your data folder).",
        "Choose the dock, desktop icons or both (Appearance > Launcher). With the dock hidden, Toolkit is on the "
        "taskbar.",
        "A Calculator tool (12k = 12,000; history; a button for the Windows calculator). The clock shows the date "
        "and follows Windows' 12 / 24-hour style.",
        "Wealth: select several rows (or Ctrl+A) and press Delete; the question now opens over Wealth instead of "
        "hiding it. New \"How it works\" guide.",
        "Price checks says what it's for (tablets, jewels, waystones); gear prices are marked as a rough guess. The "
        "update button moved to Settings.",
        "Ctrl+Alt+C stays the copy key; one-key copy is marked experimental with a one-click reset.",
        "Mod book moved to Settings > Advanced (it works on its own). Game search: a category on its own lists "
        "everything in it. Session tracker: Find Client.txt only shows when it's missing, with where to look.",
    ],
    "2.0.0-beta.20": [
        "Regex shows what your Mod book thinks: ★ marks the mods it rates valuable (your rules, or what it learned "
        "from prices), mods you ignore are dimmed. \"★ first\", \"Only ★\" and \"★ Select valuable\" build a "
        "stash search for the good ones in one click. Right-click a mod to rate it; Mod book and Regex stay in step.",
    ],
    "2.0.0-beta.19": [
        "Price checks: Delete (button, or the Del key) removes just the items you selected; Ctrl+Z or Undo brings "
        "them back. Clear list still empties the whole list.",
        "Waystones: every endgame number counts the same; when too few listings match they are all lowered "
        "together (90%, then 75% of yours) instead of some being dropped.",
    ],
    "2.0.0-beta.18": [
        "Waystones are price-checked: on the numbers at the top (Waystone Drop Chance, Pack Size, Item Rarity, "
        "Monster Rarity, Monster Effectiveness), searched at your values or more - the same as the trade site's "
        "Endgame Filters. The monster / area mods underneath aren't searched.",
        "When too few listings match, all the numbers are lowered together (90%, then 75% of yours). Tick, untick "
        "or star any number on the item to change what's searched.",
    ],
    "2.0.0-beta.17": [
        "Hotkey boxes now catch the key you press (they waited forever before). Mouse buttons work too: middle "
        "and the two side buttons (Mouse 4 / Mouse 5), e.g. hover a tablet and press a side button to copy it.",
        "Clicking a window gives it the keyboard, so typing in its boxes works.",
        "Windows no longer pop up when the app comes back to the front, and Notes / the Session timer no longer "
        "appear over the app: only over the game.",
    ],
    "2.0.0-beta.16": [
        "Setting a hotkey works like other apps: click the box and press the key (with Ctrl / Alt / Shift if you "
        "like). It's saved straight away; Esc keeps the old key, Backspace or right-click clears it.",
    ],
    "2.0.0-beta.15": [
        "Notes and the Session timer only show while Path of Exile 2 is the window in front "
        "(Settings > Window can switch that off).",
        "One-key copy: give Price checks' copy a single key in Settings > Hotkeys (click the box, press the key), "
        "then just hover each tablet and press it. It presses the game's own Ctrl+Alt+C for you, once per key press.",
        "Settings moved to the bottom left, under the dock.",
    ],
    "2.0.0-beta.14": [
        "Settings scrolls when the window is too small for it.",
        "The item library is now \"Under the hood\", a part of Price checks (the link at the top right of Price "
        "checks, or on each item) instead of a tool on the dock: you never need it to price things.",
    ],
    "2.0.0-beta.13": [
        "Windows move with you as you drag them (no more outline), and clicking a window always brings it to the front.",
        "First start asks which league you play, and picks the newest league if you don't choose.",
        "New app and Delirium icons, drawn for StashOfExile2.",
        "Notes and the Session timer over the game share one look: same title bar, border, lock and resize edges.",
    ],
    "2.0.0-beta.12": [
        "This window: a short what's new after each update (Toolkit menu > What's new shows it again).",
        "Game search links to the price checker's view of an item instead of a website, and the tablet / jewel mod "
        "lists are now built from the game's own files (RePoE). Your mod rules are moved to the new wording by "
        "themselves.",
    ],
    "2.0.0-beta.11": [
        "Moving or resizing windows no longer leaves smeared copies behind.",
    ],
    "2.0.0-beta.10": [
        "Game search (Labs): 8,500+ skills, supports, uniques, bases, currency, runes, modifiers and keywords.",
        "Labs: experimental features are marked BETA and only show when Labs is on.",
        "The dock is grouped into Modules, Tools and Utilities.",
    ],
    "2.0.0-beta.9": [
        "Session tracker (Labs): time, maps (read from the game's log file), average map time and profit per session, "
        "with a timer over the game.",
        "Settings has one list of every hotkey, with clashes in red.",
    ],
    "2.0.0-beta.8": [
        "Chat commands are pasted in one go, like Sidekick: chat only flashes.",
    ],
    "2.0.0-beta.7": [
        "The app became a desktop: windows for every tool, a dock, a Toolkit menu and a taskbar.",
        "Chat commands and Notes are separate utilities; the Delirium alert is built in.",
        "Wealth (Labs) redesigned; currency can be counted with Ctrl+C.",
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
