"""The welcome / what's new card (2.0 beta 12): shown once after a fresh install and once after each update.

INTRO says what the app is; NOTES has a few plain lines per version, newest first. The full history stays in the
launcher (stashofexile2.py, VERSION HISTORY)."""
from .updates import vtuple

INTRO = [
    "StashOfExile2 runs next to Path of Exile 2 and prices your items for you.",
    "To price an item: hover it in game and press Ctrl+Alt+C. It appears in Price checks with what it's worth and "
    "what to list it for. It works best on tablets, jewels and waystones.",
    "The bar on the left opens everything. Tools work while their window is open; Utilities (chat keys, the sticky "
    "note, the Session tracker and its alerts) keep working over the game.",
    "Your league is in Settings (bottom left). Things marked BETA are still being worked on: turn them on under "
    "Settings > General > Labs if you'd like to try them.",
]

# What's being worked on (2.4.0: not shown in the app any more - kept for ROADMAP.md / the developer).
NEXT = [
    "2.27.0: Money Makers with Thoughts per Click and Clicks per hour (see ROADMAP.md).",
]

# What's new, per version: only what helps you use the app - what you can do now and where to find it.
#
# 2.111.0: a version is either a plain list (old ones: all shown as small lines) or
#   {"big": [(icon, title, one line, (link text, target) or None, area)], "small": [(area, line)]}
# target: a page key (shell.open) or "settings:<tab>". The card shows big ones as hero rows, the small ones fold
# under "▸ N smaller changes".
#
# BIG OR SMALL - the standard. A change is BIG when a player would notice it without being told, or needs to know
# it to keep playing the same way:
#   * a new tool, page, window, style or helper
#   * something they use works or sits differently (keys, flow, moved, removed)
#   * anything about their data or privacy (always big)
#   * a fix for a problem many players hit or reported
# Everything else is SMALL: wording, looks, order, spacing, small fixes, speed.
# At most MAX_BIG big per card (skipped updates together, newest first); the rest go small.
MAX_BIG = 3

NOTES = {
    "2.112.5": {
        "big": [],
        "small": [
            ("Overlay", "Dragging the Campaign line no longer opens the route card - a plain click still does."),
        ],
    },
    "2.112.4": {
        "big": [],
        "small": [
            ("Looks", "Clicking quickly through the theme cards changes the theme once, to the last one you clicked."),
            ("Looks", "Theme changes no longer rebuild the overlay over the game (only Classic takes the theme's "
                      "colours)."),
            ("Overlay", "The Flanks style is now called Split."),
            ("Overlay", "Unlocked, the Campaign / Focus line can be dragged anywhere (by its ⠿ grip); that undocks it "
                        "from the bar - Dock the lines to the bar puts it back."),
        ],
    },
    "2.112.3": {
        "big": [],
        "small": [
            ("Overlay", "Quick settings: the Style list stays open until you pick a style."),
            ("Updates", "The update question shows what's new as plain lines."),
            ("Fixes", "A theme change that takes over 1.5 s notes where the time went in slow_report.txt (your data "
                      "folder, code locations only, never sent) - share it to help speed it up."),
        ],
    },
    "2.112.2": {
        "big": [
            ("✔", "Theme changes no longer freeze", "Changing the app theme no longer hangs or closes the app "
             "on Windows.", ("Pick a theme", "settings:Appearance"), "Fixes"),
        ],
        "small": [],
    },
    "2.112.1": {
        "big": [],
        "small": [
            ("Fixes", "If the app ever stops responding, it notes where in hang_report.txt (your data folder) - code "
                      "locations only, nothing personal, never sent. Share it to help fix a freeze."),
            ("Looks", "No dark boxes behind switch text on Settings cards."),
        ],
    },
    "2.112.0": {
        "big": [
            ("☰", "Helpers, tidied up", "One row per helper with On bar and Remind columns, grouped by where you use "
             "them.", ("Open them", "ovset"), "Overlay"),
        ],
        "small": [
            ("Overlay", "Quick settings: the Style list stays open until you pick one."),
        ],
    },
    "2.111.0": {
        "big": [
            ("✦", "Four more overlay styles", "Totem, Hellfire, Psionic and Guildhall - nine ornate looks in all.",
             ("Pick one", "settings:Appearance"), "Overlay"),
        ],
        "small": [
            ("What's new", "This card shows the big changes first; the small ones fold under one line."),
            ("Looks", "The What's new card and About follow your app theme."),
            ("Updates", "The update note's buttons no longer squeeze one into a blank box."),
            ("Overlay", "The Colours picker is gone from Overlay settings - each style keeps its own colours."),
        ],
    },
    "2.110.0": {
        "big": [
            ("✦", "Five new overlay styles", "Herald, Gilded, Warbanner, Verdant and Gloom - the bar, the panel and "
             "every window over the game.", ("Pick one", "settings:Appearance"), "Overlay"),
        ],
        "small": [
            ("Overlay", "The switches go Campaign, Focus, Breach, Delirium, Ritual, Expedition."),
            ("Overlay", "Right-click the cog to pick a style."),
            ("Overlay", "\"Avg:\" lost its period."),
        ],
    },
    "2.109.0": {
        "big": [
            ("▣", "Everything over the game matches", "Notes, Calc, Regex favorites, Rates and every card follow "
             "your overlay's Style.", ("Overlay settings", "settings:Appearance"), "Overlay"),
            ("✱", "Regex: one card of options", "Every setting is a row of buttons in one card, like Money Makers.",
             ("Open Regex", "regex"), "Regex"),
        ],
        "small": [
            ("Regex", "Copied a search? Just Ctrl+V into the stash search in game."),
            ("Regex", "★ first, Only ★ and Select valuable are gone."),
        ],
    },
    "2.108.0": [
        "Right-click the overlay's cog: Quick settings over the game - overlay, sound, lock, what's on the bar. "
        "Left-click still opens the full settings.",
        "Expedition: the island rumours show in one panel beside the card.",
        "Game Plan: goals by phase in tabs, and Stockpile / Map supplies / Farm plan / Pokes in tabs.",
        "Leaderboards: a tidier toolbar, and a hint when a board is empty.",
        "Map library: rank buttons S A B C D ✖ sit together in the toolbar.",
        "Price Checks: Recent sits under the item card, so the page has more room.",
        "Overlay bar: no stray \"-\" after Map: and Avg.: before your first map.",
        "Bulk Pricing: ticking boxes on the item card no longer searches each time or redraws the card - press "
        "Search again when you're ready.",
        "Money Makers: Import file and Download Format are in the ⋯ menu next to + Add my own.",
        "Regex: item kinds are tabs, options are click-to-toggle chips, and the Regex key line sits under your search.",
        "Game search: click a Try example, or one of your recent searches.",
    ],
    "2.107.0": [
        "New look for controls: every switch is a clear ON | OFF box, and buttons are flat in every theme.",
        "Price Checks: your recent checks are a list on the left (was a dropdown).",
        "Overlay: one ON | OFF switch for the overlay, and one Sound switch for every helper's alert.",
        "\"Open on trade site\" is now \"Trade Site\".",
    ],
    "2.106.0": [
        "Wealth: synced stash tabs are gone - count your currency (Ctrl+C) or Scan stash (beta). Old tab data is "
        "cleared once; what you counted stays.",
        "Wealth: Items show where each stack came from (Counted, Scanned, Added by hand) - filter by it.",
        "Wealth › Snapshots: what happened each time, the change since the one before, and the picked one beside "
        "the list.",
        "Wealth: the chart's line uses its height, so ups and downs show.",
        "Favorites: ticking a stat on a trade-link favorite turns its group on - ticked mods are searched.",
        "Favorites: trade-link favorites use your Seller setting (Instant Buyout) unless you pick one on the card.",
        "Open on trade site: always opens what the card shows now - changed filters are searched first.",
    ],
    "2.105.0": [
        "Price Checks and Favorites: Base type, tier, item level, Corrupted / Mirrored / Desecrated, Seller and "
        "\"only\" boxes change in place - the card no longer redraws on each click.",
        "Overlay: Rates ▾ on the bar when Exchange rates is on - click it to open or close the rates.",
        "Overlay: the bar reads Map: and Avg.:.",
        "Leaderboards: pick a league by name, and how many rows to show (Top 5 to Top 100).",
        "Island Rumours: two problems fixed (starting the app in your hideout; a card read while opening). "
        "Not confirmed in game yet - tell us if tags still don't show.",
        "Price Checks: an exact search now needs every mod you ticked (a fractured or desecrated mod could count "
        "twice, so listings missing one of your mods showed up).",
        "Amulets: catalyst quality (\"Quality (Caster Modifiers)\") and the anoint (\"Allocates ...\") are read "
        "and can be searched.",
        "Searches: up to 15 per 5 minutes on the Balanced pace (was 8), still well under the trade site's limit.",
        "Market Insights: Gear and Tablets get a second box - the slot (Helmets, Rings ...) or tablet kind.",
        "Market Insights: the item shows like a trade-site card; \"Open on trade site\" and \"Remove\".",
        "Exchange rates: Convert moved to Exchange Helper; rates always refresh hourly (no switch).",
        "Bulk Pricing: no more Mark listed / sold / removed - every item shows.",
    ],
    "2.104.0": [
        "Favorites: an empty list says how to add one; the link box says what goes in it.",
        "Favorites: a wider item card; Search and Open on trade site sit under it, like Price Checks.",
        "Favorites: a check that found nothing says why, with Search again / Search with fewer mods.",
        "Favorites: Undo shows only when there's something to undo; a failed price shows \"-\".",
        "Market Insights: All and Gear tabs - priced gear shows here now.",
        "Market Insights: no Refresh button (it fills in by itself); the item's buttons sit under its card.",
        "Waystones: the tier row says just \"Waystone tier:\" - the boxes hold the numbers.",
    ],
    "2.103.4": [
        "Charm slots (\"Has 1 Charm Slot\") get a Min box and search as a number.",
        "Waystones: a tier you type is kept when you press Search (no Enter needed).",
        "Favorites: the list on the left changes in place instead of being built again.",
        "Bulk Pricing: a tick on the item panel changes only that row first.",
    ],
    "2.103.3": [
        "Price Checks: a tick or a star changes only that mod's row - the card is no longer built again.",
        "Waystones: a tier range (or an unticked tier) now searches every waystone in that range.",
        "Favorites: same - a tick changes only its row, and the listings stay put.",
        "Favorites: Add trade link asks what to call the bookmark.",
        "Price Checks and Favorites show the \"Staying under the trade site's limits\" line, like Bulk Pricing.",
    ],
    "2.103.2": [
        "Price Checks: ticking a mod no longer redraws the listings.",
        "Waystones: a Waystone tier row (a range searches only from 2.103.3).",
        "Buttons in toolbars have their spacing back.",
    ],
    "2.103.1": [
        "Bulk Pricing: the filters, Export CSV and Clear list are back where they were.",
        "Waystones: type a Min / Max on any mod on the card to search on it.",
    ],
    "2.103.0": [
        "Price Checks: when nothing matched, it says why and offers Search again or Search with fewer mods.",
        "Bulk Pricing: Filters ▾ opens the list filters; Export CSV and Clear list are under ⋯; the Status column "
        "shows Priced, Review, Pricing or Waiting.",
    ],
    "2.102.0": [
        "Wealth › Scan stash (beta - may not work): open your Currency, Abyss, Delirium and Breach tabs one at a time "
        "and press Start reading on the card over the game - no Ctrl+C on every stack.",
        "You check every number before it's saved; the screen picture is never kept.",
    ],
    "2.101.0": [
        "New overlay styles: Settings › Appearance › Overlay settings › Style - Hairline, Slate, Flanks and Micro "
        "are light, plain looks (no box for Hairline and Flanks); Classic is the stone-and-bronze look you know.",
        "Each comes as a Game bar or a Panel (Layout), in ten colour sets or your app theme's (Colours).",
    ],
    "2.100.0": [
        "List rows light up under the mouse, and clickable icons brighten.",
        "Press Tab to move around: the focused button, switch or list shows a ring.",
        "Tooltips and notices fade in for a moment - Settings › Appearance › Reduce motion turns that off.",
    ],
    "2.99.1": [
        "Updates are checked every time the app starts and every hour - preview builds too, when you've opted in.",
        "Right-click the tray icon › Check for updates.",
    ],
    "2.99.0": [
        "Mod book › Gear rules: every item class (helmets, belts, rings, amulets, weapons ...) with every mod it can "
        "roll. Rate them S-F: S / A are always searched, F never.",
        "Mod book › Unique rules: rate a unique's mods and each option - every Mageblood Legacy, for example.",
        "What the app learned now sits inside each Mod book tab, showing only that tab's mods.",
        "Price checks: a rare white base widens its search when the exact one finds too few, and when nothing was "
        "listed recently, older listings are searched once (the card says so).",
    ],
    "2.98.6": [
        "Expedition remnant prices show again in maps where the app didn't spot the Expedition mark.",
        "The runeshape tips box has Never show again.",
    ],
    "2.98.5": [
        "Game Plan › Stockpile: pick from the list, or type any item in the name box (it narrows the list too).",
        "Map supplies: Omen of Amelioration pokes you once you're back from a map where the game used it up.",
        "The first map rank card has Opt out.",
        "Map library › Share › Upload my ranks to the community (Community data sharing; once per 45 min).",
        "Price checks: a Rarity prefix and suffix (or any two mods with one stat) are added up and searched as one "
        "line, like the trade site shows them.",
        "Saying no to Community data sharing is final: it's never asked again.",
    ],
    "2.98.4": [
        "Mageblood is priced on its Legacies (how many of each), its charm slots and, with a duplicate, its "
        "per-duplicate roll.",
    ],
    "2.98.3": [
        "Dialogs open over the app, on its monitor.",
        "Settings: Fine tuning is under Price checking; the every-hour rates switch is on the Exchange rates page.",
        "About › Credits: everyone we thank, with a link to their GitHub page.",
    ],
    "2.98.2": [
        "Corrupted uniques (and other corrupted gear) are priced as corrupted: Twice Corrupted counts, and the "
        "corruption enhancement and the sockets it has are searched.",
        "The Toolkit menu stays on the monitor the app is on.",
    ],
    "2.98.1": [
        "Trade Whisper Watcher: at league start, a card over the game when someone whispers to buy an item you "
        "listed (Overlay › Settings › Helpers › Trade whispers). On during the campaign; it can stay on after.",
    ],
    "2.98.0": [
        "Narrow windows: button rows wrap and text re-wraps instead of being cut off; Overlay settings switches "
        "fall into fewer columns.",
    ],
    "2.97.3": [
        "Money Makers is a Labs feature now: turn on Labs in Settings to see it.",
        "Price Checks: Add to favorites and Open on trade site are under Search.",
        "Updates: new versions are tested in game before everyone gets them. Want them sooner? Settings › Updates › "
        "Preview builds.",
    ],
    "2.97.2": [
        "Price Checks: each mod's color shows where it comes from (affix, rune, fractured, desecrated, pseudo).",
        "Every section of the item card folds, with how many are ticked; Fold all / Unfold all at the top.",
    ],
    "2.97.1": [
        "Price Checks: socketed runes have their own Augments section, and a rune's line no longer ticks an affix "
        "with the same wording.",
        "Fractured only / Desecrated only sits right under its mod, small, and the mod shows in its color.",
    ],
    "2.97.0": [
        "Rate mods starts by asking which items you know best, and Back / Next / Done sit under the tiers.",
        "F is the ignore tier, wherever tiers show.",
        "Price Checks: Rate ▾ beside each mod (S to F, for every item like it) replaces ▲ / ▼. The card and the "
        "listings fit the window; the scrollbar only shows when there's more to see.",
        "Fractured only / Desecrated only now ticks the mod too, so it's searched.",
        "League Focus and the Campaign Helper: switch one on and its line shows on the overlay (both on: one bar). "
        "Past the campaign, its line and Vendor ▾ come back when you visit a campaign zone.",
    ],
    "2.96.1": [
        "Overlay ↳ Settings is tidier: one switch per item on the bar, each helper's options on its own row, and "
        "Options for how the overlay behaves.",
        "The Exchange rates window can be moved again (unlock the overlay, then drag it).",
        "Vendor ▾ stays on the bar the whole campaign.",
    ],
    "2.96.0": [
        "Price Checks: ▲ / ▼ beside each mod - did it matter for the price? Your answer counts for every item like it.",
        "Rate mods one at a time (S to D, or Ignore): Mod book, or Settings › Privacy & community. It tunes your price "
        "checks and earns rep when it matches everyone's.",
        "Bulk Pricing skips items the Mod book is sure sell under 1 div (Settings › Price checking › Skip cheap items).",
    ],
    "2.95.0": [
        "Rep: help the community (upvoted strats, accepted edits, reviews, ratings that match everyone's) and a small "
        "contributor icon shows beside your name. Hover anyone's icon for their card.",
        "Settings › Privacy & community: your rep, where it came from, and switches to hide the icon or count your "
        "mod ratings. Nothing is locked behind rep.",
    ],
    "2.94.0": [
        "Settings › Privacy & community: what you share, and your community name - change it, become a reviewer or "
        "admin, move it to another PC, or delete everything. The 👤 chip on Money Makers and Leaderboards opens it.",
        "No more name question at start: you're asked only when you post, vote or share leaderboard times.",
    ],
    "2.93.1": [
        "Price Checks: listings look like the trade site's own preview.",
        "Price Checks: Clear (beside Search) empties the page and Recent.",
    ],
    "2.93.0": [
        "Price Checks: tick the small box under a fractured or desecrated mod to search it only as fractured / "
        "desecrated.",
        "Price Checks: a hybrid resistance (Lightning and Chaos ...) adds a total per resistance - Chaos is searched, "
        "the elemental one is there to tick.",
        "Price Checks: socketed rune lines are marked and left out unless you tick them.",
    ],
    "2.92.2": [
        "Overlay page: Overlay Enabled | Overlay Disabled - one switch for everything over the game. You pick which "
        "switches go on the bar when you enable it.",
        "Regex ▾ on the overlay bar, beside Notes and Calc: click a favorite to copy it.",
        "Vendor ▾ works again in campaign towns, beside the other menus (one switch for it).",
    ],
    "2.92.1": [
        "Listing order lab (admins): corrupted items match their listing; item sizes and a column-by-column order are "
        "shown for comparing.",
    ],
    "2.92.0": [
        "Arbitrage is removed (deprecated): the Currency Exchange history it read comes from GGG without clear terms "
        "for tools, so the app no longer reads it.",
        "Check a flip you see in game stays - it's now at the bottom of Exchange rates › Exchange Helper.",
        "The app now tells the trade site and poe.ninja plainly who's asking: StashOfExile2 and its version.",
    ],
    "2.91.0": [
        "New: an Exchange rates window over the game (chaos : div, exalt : div ...), in the overlay's look. Turn it "
        "on in Overlay ↳ Settings › Features and drag it where you like.",
        "Arbitrage › Check a flip: pick the item from every Currency Exchange item (type to narrow the list).",
    ],
    "2.90.0": [
        "Overlay bar: the map's time, the area and its rank share one part, shown whole; every part is centered.",
        "Pick which switches your bar shows - one per helper (Breach, Delirium, Ritual, Expedition, Focus, Campaign).",
        "Overlay ↳ Settings is regrouped: every helper's on / off is in Helpers; lines and switches are in On the bar.",
        "Desecration Helper (Beta): your first visit to The Well of Souls asks if you want it.",
        "Fixed: the Campaign line and Dock switches did nothing; the campaign line showed after the campaign.",
    ],
    "2.89.3": [
        "Privacy: Money Makers › Leave the board can now delete everything of yours on the community board.",
        "Leaderboards show the day of a run, not the time; private leagues are never shared.",
        "Strats you share carry your rates (div per hour), never your totals or your account name.",
        "A screenshot asks before it goes public; a community name can't be your account or character name.",
        "Logs and bug reports leave out your account and character names.",
    ],
    "2.89.2": [
        "Privacy: Community data sharing stays off until you say yes, and now shows exactly what's shared, what for "
        "and where it goes (Settings › General › What's shared, and why?).",
        "Error logs and bug reports no longer contain your Windows user name.",
        "\"Act splits\" is now the Act timer: your time in each act against your best.",
        "The overlay bar spells out each switch (Breach, Delirium, Ritual, Expedition ...).",
    ],
    "2.89.1": [
        "Screenshots show the overlay again. (Overlay ↳ Settings › Behaviour can hide it, if it covers a counter the "
        "Ritual or Delirium watcher reads.)",
        "A ⚙ next to the overlay's lock opens its settings.",
        "The bar's switch says Campaign; the Campaign settings no longer print two options on top of each other.",
    ],
    "2.89.0": [
        "Campaign Helper: starting a campaign asks Speedrun or Full rewards, then follows that guide. Speedrun skips "
        "the bosses and side areas that only give gems or loot, and keeps the points, spirit and resistances.",
        "Change it any time: Overlay › Options › Campaign › Route (or turn the question off there).",
        "Settings can't get stuck in front of everything after you resize the app.",
    ],
    "2.88.3": [
        "The Campaign switch is always on the overlay's bar now, so you can find the Campaign Helper. Don't want it? "
        "Overlay › Options › On the bar.",
        "The overlay only shows over the game itself - not over a browser tab or video with \"Path of Exile 2\" in "
        "its name.",
        "Screenshots show the overlay again. It's only hidden from captures while the Ritual or Delirium watcher runs.",
    ],
    "2.88.2": [
        "Ctrl+Alt+C is heard more reliably: if Windows stopped passing keys to the app, your next copy still counts and "
        "the app starts listening again.",
        "Price Checks: ticking or unticking mods no longer searches by itself - press Search when you're ready.",
        "Pasted trade links of every kind read (some long ones said \"no search for that link\").",
    ],
    "2.88.1": [
        "Fixed: items copied with Ctrl+Alt+C weren't priced in Bulk Pricing (when you had Favorites).",
    ],
    "2.88.0": [
        "For board admins: Under the hood ↳ Listing order lab - read a public tab's trade link, walk the tab with "
        "Ctrl+Alt+C, and see which order the trade site's list follows.",
    ],
    "2.87.0": [
        "Bulk Pricing › Stash tab: the list follows your tab - down each column, left to right (or across each row: "
        "List order). The # column shows where each item sits (C3 R5 = column 3, row 5).",
        "Price Checks go first: Bulk Pricing waits while one runs, and pressing Search again replaces the older "
        "search. Price Checks now search exactly the mods you ticked.",
        "Price Checks' Recent (and each check's listings) is kept when you close the app.",
        "Leaderboards: Simulacrum of Delusion is under Bosses & pinnacles (it was under Trials), and your classes are "
        "read from the game's log (it names the class at every level-up), so Class can filter.",
    ],
    "2.86.1": [
        "Community names: slurs and hate words aren't allowed (also with swapped letters, numbers or spaces). A name "
        "like that from before is reset - the app asks you for a new one.",
    ],
    "2.86.0": [
        "New: Overlay ↳ Leaderboards - your fastest campaign acts, maps, pinnacle fights and trials, and everyone's. "
        "Filter by league and class.",
        "Everyone's times come from players who share (Community data sharing + Share my times): your community name "
        "shows, never your account or character. Times are self-reported from the game's log; impossible ones are "
        "refused, and a time can be reported.",
    ],
    "2.85.2": [
        "Ritual alerts work under the overlay bar again: the bar is left out of screen captures, so the watcher sees "
        "the Ritual counter beneath it. Switch: Overlay ↳ Settings › Behaviour (off = screenshots and streams show the "
        "bar).",
        "The Focus / campaign line docks flush on the overlay bar, with matching ends.",
    ],
    "2.85.1": [
        "Money Makers: the filter labels on the left (Thoughts per click, Clicks per hour) show in full again.",
    ],
    "2.85.0": [
        "Your community name: asked once, it's yours alone on Money Makers and can change once every 7 days.",
        "Community strats are protected: only their author edits them, and every change is kept (right-click › "
        "History, roll back). Want something fixed? Right-click › Suggest an edit - the author accepts or declines.",
        "Help keep strats honest: become a reviewer from your name's menu. Changes to Official strats and reported "
        "posts wait for two reviewers.",
        "Money Makers and the Strat Tracker: costs and profits keep their currency (ex, chaos) and can be negative, "
        "every source link is kept, Community and Official strats can be tracked, and the labels match everywhere.",
    ],
    "2.84.0": [
        "New: Price Checks ↳ Favorites. Press ☆ Add to favorites on Price Checks, or paste a trade-site link: each "
        "favorite opens with its filters and the trade site's listings, like Price Checks.",
        "Put favorites in groups, drag them into your order, and right-click for everything else (rename, edit, "
        "duplicate, move, copy the trade link, delete - Ctrl+Z undoes).",
        "Money Makers: the Trade links of a strat's items search Instant Buyout (your Settings choice), a waystone's "
        "numbers and tier are searched too, and Copy regex includes the numbers.",
    ],
    "2.83.1": [
        "Price Checks' key is now Ctrl+D: hover an item in game and press it. Change it in Settings › Hotkeys. "
        "The game's plain Ctrl+C no longer opens Price Checks.",
    ],
    "2.83.0": [
        "New: Island Rumours. Open the world map in your hideout and each rumour on the Uncharted Waters card shows "
        "the island it leads to and your Map library rank for it. Rank the islands in the Map library.",
        "The Remnant price tags no longer pop up in hideouts, towns, the campaign or maps without an Expedition (the "
        "app looks for the Expedition mark under Map Content); on Grand Expedition islands they're always watching.",
    ],
    "2.82.0": [
        "Overlay ↳ Settings: every overlay option on its own page, grouped - On the bar, Features, Campaign, "
        "Behaviour and the Mechanic Helper. Open it from the sidebar or the Overlay settings button.",
    ],
    "2.81.2": [
        "Desecration Helper: two-line options like Accuracy + Light Radius get their tier too.",
    ],
    "2.81.1": [
        "Desecration Helper: the tags show just the tier (T5), and its switch is only in Overlay › Options (not on "
        "the bar) - it turns itself on at the Well.",
    ],
    "2.81.0": [
        "New: Desecration Helper. At The Well of Souls, each revealed option shows its tier (T1 = best for that "
        "item type), and Abyss lords' mods show their range and how good the roll is.",
        "It only wakes up while you're at the Well (from the game's log) - a small notice says so. Switch it in "
        "Overlay › Mechanic Helper.",
        "Fixed: Price Checks' listing cards showed the mods as raw data.",
    ],
    "2.80.0": [
        "New: Price Checks. Hover an item in game and press Ctrl+C - it opens with every filter on the left and the "
        "trade site's listings on the right (mods with tiers, price, seller, when, the item's picture). Recent keeps "
        "your last 20.",
        "The old Price checks page is now Bulk Pricing, under Price Checks with Market Insights: Ctrl+Alt+C still "
        "adds items there.",
        "Settings › Hotkeys › Price Checks: turn Ctrl+C off, stop the app coming to the front, or hide pictures.",
    ],
    "2.79.2": [
        "Price checks: every mod under Stat filters can be ticked on and off again.",
        "Searches start at Instant Buyout, priced in Exalted Orb Equivalent.",
    ],
    "2.79.1": [
        "Mageblood and similar uniques price correctly: two of the same Legacy (2 Quicksilver, 2 Diamond) are searched "
        "as one stat with Min 2, like the trade site does.",
        "The campaign line sits docked on top of the overlay bar and moves with it (switch: Overlay › Options › "
        "Campaign). The bar is as wide as the XP bar, bottom centre, and refits when your resolution changes.",
        "Updates are looked for every hour.",
    ],
    "2.79.0": [
        "Price checks: a clean item panel - every filter on the item card (properties, requirements, "
        "corrupted / fractured / desecrated / sanctified / mirrored / unidentified, each mod with Min / Max and ★, "
        "trade filters). Listing status, how it's priced and the raw text are under ▸ Advanced.",
        "No price pop-ups over your screen any more.",
        "Uniques like Mageblood and bases with a granted skill (Summon Rhoa Mount) find their mods on the trade site. "
        "White and magic bases are compared at their exact item level, rarity, quality and sockets.",
        "The Remnant price tags show up as soon as the book is open.",
    ],
    "2.78.3": [
        "The overlay sizes itself to your game's resolution, from 720p to 4K - the bar, its text and the cards over "
        "the game (map rank, campaign, the calculator).",
        "Price checks: the item card has Item level (tick it, type a number) and Min / Max boxes beside each mod. "
        "Press Enter to search again with them.",
    ],
    "2.78.2": [
        "The Campaign Helper's line is as wide as the overlay's bar, lined up with it.",
    ],
    "2.78.1": [
        "The \"Rank this map\" card shows the map's name (Rugosa, not MapRugosa), and the ranks you gave there now "
        "show in the Map library.",
    ],
    "2.78.0": [
        "Money Makers: strats say what they farm - pinnacles, bosses, Azmerian Wisps, Viridian Wildwood and more - "
        "and you can filter by it in the new Content row.",
        "The Strat Tracker asks how people should find your strat (what it is, Thinking, Clicks, tags, steps) "
        "before it's published, and takes a screenshot of your atlas (paste it with Ctrl+V).",
        "A strat's panel lists what you need: each tablet and waystone with Copy regex and a trade search, plus the "
        "author's atlas - click it to see it big.",
    ],
    "2.77.0": [
        "The Campaign Helper: a line over the overlay's bar says where you are in the campaign, what to do there, "
        "what it's worth and where to go next - it follows you by itself from the game's log. Click it for the "
        "act's route, your rewards and your act times.",
        "Never miss a permanent reward: leaving an act, it asks about the passive points, spirit and resistances you "
        "may have skipped (Got it, Remind me in town, Skip it).",
        "In town, Vendor ▾ copies a shop search (movement speed boots, resistances ...) - paste it in the shop's "
        "search box. Its options are in Overlay › Options › Campaign.",
    ],
    "2.76.0": [
        "The map's rank is its own part of the overlay - click it to rank the map you're in. Leaving a map you "
        "haven't ranked, a small card asks how it was (Overlay › Options can switch that off).",
        "League Focus's goal has its own small bar now, over the Game bar (or by the Panel), so the main bar keeps "
        "its room. Unlock the overlay to drag it where you like.",
    ],
    "2.75.0": [
        "Wealth is easier to find your way around: Wealth ↳ Overview, ↳ Stash tabs and ↳ Snapshots in the sidebar. "
        "Your stash tabs have their own page - the list, and adding one, always in view.",
        "Sync stash tabs and Count currency are on top of every Wealth page. The first time, the setup steps are "
        "right on the Overview and tick themselves off; after that, one line says what's counted, synced and "
        "still needs a price.",
        "Pick which tab's items to show with From, over the item list.",
    ],
    "2.74.5": [
        "Price checks is lighter: fewer rows and less padding, the settings line on top, and beta notices you can "
        "close with the × on their right.",
    ],
    "2.74.4": [
        "Price checks: tick the mods right on the item card - ticked mods are searched on. Min / Max "
        "and key mods are under Fine-tune the search.",
        "A unique's flavour text is never taken for a mod any more.",
    ],
    "2.74.3": [
        "The session timer has a ⏸ / ▶ button on the overlay, and the Pause key on your keyboard pauses and resumes "
        "it. The Ctrl+Alt start / stop and pause keys are gone - they could get in the way of the game.",
        "Click-through (Settings › Appearance › Overlay settings) is its own switch now, off to start with - the "
        "lock only stops the overlay moving.",
    ],
    "2.74.2": [
        "A new version now shows in the sidebar, above Toolkit and Settings - click it to see what's new and update.",
        "Settings › Advanced › Report a bug opens the same Report a bug as the bottom bar.",
    ],
    "2.74.1": [
        "Price checks: the Item card shows the item as it reads in game - its mods and their values right on the "
        "card, with tier tags, no scrolling for them.",
        "Uniques are read properly: their mods count (they were left out), Mageblood's Legacies are searched by "
        "name (Legacy of Gold, Quicksilver ...), and flavour text is never taken for a mod.",
    ],
    "2.74.0": [
        "Under the hood and the Mod book are advanced tools now, hidden unless you want them: Settings › Advanced › "
        "Show advanced tools. The Mod book sits inside Under the hood (Price checks ↳ Under the hood ↳ Mod book). "
        "Both keep working either way.",
        "The calculator is over the game: Calc ▾ on the overlay's bar opens a small calculator you can drag where "
        "you like; the overlay's lock holds it in place. Overlay › Options turns it off or takes Calc ▾ off the bar.",
        "The overlay bar is a little slimmer again, and the Remnant switch's tip mentions the runeshape list.",
        "Settings › Appearance › Overlay settings: Layout, Opacity and Click-through in one place. Click-through is "
        "on: while the overlay is locked, clicks go through it to the game - unlock it to use its switches. The Game "
        "bar is the default layout for new setups.",
    ],
    "2.73.5": [
        "The overlay bar is a little taller, so its switches have room above and below (side to side they're "
        "back to how they were).",
        "A switch's hover tip shows above your pointer when there's no room below it - it was cut off at the "
        "bottom of the screen.",
        "Dividers between the time, map, goal, maps and average on the bar. Hiding Focus from the bar hides its "
        "goal line too.",
        "Price pop-ups no longer appear all over the screen while a stash tab is being priced - only for items you "
        "check yourself.",
        "The iLvl column now shows the item level for items you added before 2.73.2 too.",
    ],
    "2.73.4": [
        "Prices are always for your league - after switching leagues, old prices are never shown as current.",
        "Game Plan: stockpile items from the Currency Exchange's list (or type any name), set a Quantity; add your "
        "own farms; goal targets can be divines, a character level or maps run (both read from the game's log), "
        "an act, or any number.",
        "The overlay bar has more room between its switches. Hover one to see what it does - the first time you "
        "switch one on, a short card explains it (Overlay › Options › Feature tips).",
        "Game Plan is easier to scan: a summary on top, clearer headings and one look for every form.",
    ],
    "2.73.3": [
        "Map supply pokes: Overlay ↳ Game Plan › Map supplies - list what you use up in maps (Scrolls of Wisdom, "
        "omens, any currency) and refill it every N maps or N minutes in maps. Between maps, in town, a poke says "
        "it's time - Refilled, Snooze or Skip. Counted from the game's log; its own switch.",
    ],
    "2.73.2": [
        "Price checks: items read from a stash tab stay in that tab's list (they also showed in Manual Add). "
        "Right-click waiting items to Pause pricing, Price next or Price last. A new iLvl column.",
        "Market Insights: click an item to see it in the Item panel at the side (no more tooltip at the cursor). "
        "Remove items from any of its lists - Delete, or right-click › Remove; Ctrl+Z puts them back.",
        "StashOfExile2 - One tool to rule them all.",
    ],
    "2.73.1": [
        "League Focus pokes: your plan now reminds you over the game - a nudge in your own words, \"you reached "
        "maps\" with what you planned for it, cheap stockpile prices, a heads-up before you reroll, and a check-in "
        "every 45 min of play. Only in town, never more than you allow - tune it in Overlay ↳ Game Plan › Pokes.",
    ],
    "2.73.0": [
        "League Focus: Overlay ↳ Game Plan - set your league goals by phase, a stockpile to buy while it's cheap, your "
        "farm plan and a build lock once, then forget it.",
        "The overlay shows your current goal on a focus line, and a Focus switch sits on the bar next to Breach and "
        "Delirium.",
        "Overlay › Options › On the overlay: choose which features have a switch on the overlay's bar.",
    ],
    "2.72.2": [
        "Notes: right-click a note's tab for Rename, New note, Duplicate, Move left / right, Copy, Clear, Reopen a "
        "closed note and Close. Right-click no longer closes a note by itself.",
    ],
    "2.72.1": [
        "Wealth: stackable items poe.ninja doesn't list now get a price from the trade site's bulk exchange.",
        "Price checks: copy a stack and the status line says what it's worth.",
    ],
    "2.72.0": [
        "Price checks: rare gear now gets a real price. The search skips mods buyers hardly pay for (light radius, "
        "thorns, stun ...) and low tiers, so it compares your item with ones like it. Only a price the listings "
        "can't back up still says Price manually.",
        "Uniques are priced by their rolls: a well-rolled mod is searched at least that high, and the item shows how "
        "well it rolled overall.",
        "Normal and magic bases of item level 75+ are priced as crafting bases, at their item level.",
    ],
    "2.71.0": [
        "Money Makers › Strats: filter buttons for what a strat is, how much thinking and how many clicks it takes.",
        "Strats show as cards with their estimated profit per hour - Cards / List switches back to the table.",
        "Pick a strat to see Your numbers from the Strat Tracker, and ▶ Track in Strat Tracker to start.",
    ],
    "2.70.1": [
        "Overlay: \"Hide timer\" is now a \"Timer over the game\" switch - it hides only the timer.",
        "Overlay › Options › On the overlay: switch off any part you don't want over the game - each number, where "
        "you are, the clock, Notes, the Mechanic Helper switches.",
    ],
    "2.70.0": [
        "Strat Tracker: setting up a strat is now 5 short steps - Name & strat, Waystone, Tablets & more, Atlas, "
        "Logging - with the cost of one run always showing at the right.",
        "Strat Tracker: logging your loot is 3 steps - how many runs, what dropped, the profit. Ctrl+Alt+C a drop "
        "and it jumps to the loot step.",
    ],
    "2.69.3": [
        "Session: if the game closes or crashes while you're tracking, the session pauses and asks whether to end "
        "it. The time after the game closed isn't counted, and opening the game again picks the session back up.",
    ],
    "2.69.2": [
        "Overlay: when the session is paused, a small PAUSED tag shows next to the time instead of running into "
        "the numbers beside it.",
    ],
    "2.69.1": [
        "Community data sharing is now opt-in: the app asks once, and nothing is shared until you say yes. Change it "
        "any time in Settings › General › Community data sharing. It covers mod prices, map ranks and the strats "
        "you upload.",
        "Strat Tracker: 📤 Upload puts your setup and its numbers on the community strats in Money Makers.",
        "Toolkit: the Check for updates button isn't cut off any more.",
    ],
    "2.69.0": [
        "Every tool now has the same look as Price checks: each part sits under a header strip in its own framed "
        "panel - Settings, Wealth, Regex, Exchange rates, Game search, Market Insights, Money Makers, Map library, "
        "Mod book, Overlay and Calculator. They follow your theme.",
    ],
    "2.68.1": [
        "Notes is simply part of the overlay now - open it from Notes ▾ on the overlay, F6 hides it with the rest. "
        "Its separate settings and the old notes key are gone.",
    ],
    "2.68.0": [
        "Farm Tracker is now Strat Tracker.",
        "Strat Tracker: for a waystone, \"which numbers make this setup work?\" now lists its Pack Size, Item "
        "Rarity, Monster Rarity and the rest - what the trade site actually searches - and its Trade search uses "
        "them with its tier.",
        "Fixed: after Done or Skip, the setup window no longer disappears behind the app.",
    ],
    "2.67.2": [
        "The XP bar overlay is tidier: the Breach / Delirium / Ritual / Remnant switches sit in their own row on top, "
        "your time and maps in the row under it.",
    ],
    "2.67.1": [
        "Money Makers › Tablet Crafting is now called Tablet Craft Helper.",
    ],
    "2.67.0": [
        "Overlay layouts: the Panel and the Game bar on the XP bar - and the XP bar now has the Breach / Delirium / "
        "Ritual / Remnant switches too. Notes match the overlay's look and still move and resize.",
        "Farm Tracker: \"The mods that matter\" asks about one item at a time, in the middle of the setup window "
        "(no more pile in the screen's corner), and the \"valuable mods\" pop-up no longer shows for setup items.",
        "Farm Tracker: each item now has a Trade search (that base, the mods that matter, 10+ uses remaining) and a "
        "Copy regex for your stash.",
    ],
    "2.66.2": [
        "The Panel, redone: a heavy dark-metal frame with gold filigree corners, a framed header banner, and your "
        "numbers in big antique gold in a clean 2 x 2 grid with a small icon each.",
    ],
    "2.66.1": [
        "The Panel now looks like the game's Treasurer window: the title in small caps on a dark band, the league "
        "or area in red under it, and your numbers in gold in dark boxes.",
    ],
    "2.66.0": [
        "The overlay comes in two looks, both straight out of the game: the Panel, styled like the game's vendor "
        "windows (a header plate, your stats in gold, the switches in boxes that glow when on), and the Game bar. "
        "The old styles, Strip and Minimal are gone - one less thing to set up.",
        "The Game bar layouts look like part of the game's own bar: dark stone in a pewter frame, arched end caps "
        "with a red gem by the life orb and a blue one by the mana orb, and the switches in slots like your flasks "
        "and skills that glow gold when on.",
        "Anoints has its own page now: Game search ↳ Anoints in the sidebar.",
        "Beside the orbs is slimmer: each half is only as wide as what it shows. Dragged it? Pick the layout again "
        "to put it back.",
        "Fixed: clicking a tool in the sidebar while you're on one of its tabs or sub-tools (Regex from Favorites, "
        "Overlay from Map library) now takes you back to it. Click it again to fold it.",
    ],
    "2.65.0": [
        "Two new overlay layouts in the game's own bar look (Settings › Appearance › Layout): \"Game bar - on the "
        "XP bar\" sits right on top of the experience bar, and \"Game bar - beside the orbs\" splits it - your "
        "time and map right of the life orb, the switches, Notes and clock left of the mana orb.",
        "They fit themselves to the game window. A different UI scale? Unlock and drag them; \"Fit to the game\" "
        "puts them back.",
        "The sidebar is tidier: only the tools are listed, and the one you open unfolds to show what's under it. "
        "Click it again to fold it. Regex lists just Favorites under it.",
    ],
    "2.64.0": [
        "Each tool's tabs are now listed in the sidebar right under it (↳) - for example Money Makers ↳ Strats, "
        "Lucrative Strats, Tablet Crafting, Farm Tracker; Regex ↳ Favorites; Mod book ↳ its rule tabs. Click one "
        "to go straight there. On a short window only the open tool's tabs are listed.",
        "Farm Ledger is now called Farm Tracker.",
    ],
    "2.63.0": [
        "Price checks has a cleaner layout: the list and the item each sit under their own header, the list says "
        "how many items it shows and how it's sorted, and the buttons for the picked rows sit right under the list.",
        "New: a Search box (finds an item by name, type or mod text) and an \"Only ★\" switch for items with a "
        "valuable mod.",
        "Clicking a row no longer opens a pop-up box - the item shows in the panel on the right, with Open on trade "
        "site and Mark listed at its foot.",
    ],
    "2.62.0": [
        "A new layout: every tool is listed by name in the sidebar on the left (sub-tools indented under theirs with "
        "↳), and the one you pick fills the window - one at a time, no more floating windows.",
        "The bar along the bottom holds the messages, exchange rates, trade-limit meters, league and clock. Toolkit "
        "and Settings are at the bottom of the sidebar.",
        "Frost Pane (the light theme) is easier to read: no more pale gold or white text on light panels, and no "
        "dark patches left over.",
    ],
    "2.61.1": [
        "Chat commands: set each command's key right on that page again - click the Key box and press the key. If "
        "another hotkey already uses it, the box turns red and says which one.",
        "Fixed: a chat command you hadn't given a key yet wasn't kept.",
    ],
    "2.61.0": [
        "The app window's own title bar now takes the theme's colors too (Windows 11; on Windows 10 it turns dark "
        "or light to match).",
        "A fresh install starts by letting you pick a theme - you can change it any time in Settings › Appearance.",
        "Fixed: the on / off switches in Settings could disappear after changing themes.",
    ],
    "2.60.0": [
        "Themes: ten looks for the whole app in Settings › Appearance - click one and it changes at once, nothing "
        "restarts. Emberforge (iron, embers and blue rune-glow) is the new default; Midnight Steel is the old look.",
        "Bevelled buttons, list headings and title bars drawn by each theme. Icons and layout stay the same.",
        "The trade limits at the bottom right are meters now (and in the limits window); mod rolls too.",
        "Price checks: the item shows as a card at the top of the side panel, with tabs Item / How it's priced / Raw.",
        "A new app icon: a stash chest with a toolbox lid.",
    ],
    "2.59.0": [
        "The overlay is always one window. Pick Style and Layout (Panel or Strip) in Settings › Appearance.",
        "Session timer is now Overlay: the timer, Mechanic Helper and Notes on one screen. F6 shows / hides the whole "
        "overlay (change it in Settings › Hotkeys); one lock for all of it.",
        "New in Settings: Price checking (valuable mod, popups, sound, listings, prices in, account, copy marker), "
        "Tools (exchange rates), General › Game (Client.txt, window title) and Advanced › Fine tuning.",
        "A search box at the top of Settings finds any setting. Changes save by themselves - no Save & apply.",
    ],
    "2.58.0": [
        "Every look is in one place: Settings › Appearance - the app, and over the game (style, one window, layout, "
        "opacity, Notes text size). Overlays no longer has an Appearance tab.",
        "Notes and the copy marker follow the overlay style - no separate colors to set.",
    ],
    "2.57.0": [
        "Every key is set in one place: Settings › Hotkeys, grouped by what it's for. Chat command keys and the Farm "
        "Ledger's \"a run is done\" key can now be changed there.",
        "Regex, Notes, the Session timer and Chat commands show their key with a button to change it in Hotkeys.",
    ],
    "2.56.2": [
        "Expedition remnant price tags are smaller and calmer: plain text in your overlay style's colors (on the "
        "parchment texture with Runeshape parchment). They show up about twice as fast and go as soon as the book "
        "closes; the key's tags stay 12 seconds (was 30).",
    ],
    "2.56.1": [
        "Strip layout: drag its left or right edge to make it wider or narrower - the area name and your note's line "
        "get the room. It never gets narrower than what it shows.",
        "An overlay past the edge of the screen (a locked strip, say) comes back on the screen by itself.",
        "One opacity slider for everything over the game (Overlays › Appearance).",
    ],
    "2.56.0": [
        "Farm Ledger, redone: your setups as cards, the answer in plain words (\"Makes about 10.3 div an hour\"), "
        "the key numbers, where the money comes from, and a strip that shows runs counted since your last log.",
        "New to the Farm Ledger? It starts with three steps and one button. Compare now says which setup wins.",
    ],
    "2.55.1": [
        "The item box (click an item in Price checks or Insights) closes with Esc, Space, or a click anywhere else - "
        "or click the same item again. A click on the box keeps it.",
    ],
    "2.55.0": [
        "One overlay window: the Session timer, the Mechanic Helper and Notes together over the game. Turn \"One "
        "window\" off in Overlays › Appearance for three separate windows.",
        "Two new styles: Codex (dark stone, bronze corners) and Minimal (just the time, the map and the four switches).",
        "Layout: Panel (a card) or Strip (one thin bar for the top edge - Notes drop down from it), with any style.",
    ],
    "2.54.1": [
        "Mod book › Manual feed: the price is optional. Without one, the item is kept and the mods you tick are rated "
        "High. \"Counts as N listings\" is gone: a fed item is one price, like any listing.",
    ],
    "2.54.0": [
        "Money Makers: the filters are named like the fields - 🧠 Thoughts per click and 🖱 Clicks per hour (each shows "
        "the level you pick and the easier / calmer ones).",
        "The Session timer no longer shows profit: it times your play. Money is tracked in one place - Money Makers › "
        "Farm Ledger (there's a link on the Session timer).",
    ],
    "2.53.0": [
        "Price checks: click an item (Manual Add or a stash tab's list) to see its box - name, mods and price - like "
        "in Insights. Click it or press Esc to close it.",
        "The Session timer's text is softer: plain rows, only the time and Profit bold, a lighter outline.",
        "US spelling everywhere (Notes: \"Font and Colors\").",
    ],
    "2.52.0": [
        "Tidier menus: every setting lives in one place. Opacity is only in Overlays › Appearance; the clock on the "
        "Session timer is switched in Overlays › Session timer › Options.",
    ],
    "2.51.0": [
        "Mod book › Manual feed: Ctrl+Alt+C (or paste) an item you know the price of - an expensive tablet, say - type "
        "the price and Feed it. The Mod book learns from it like a sale; you see what changed, and can undo it.",
        "The Session timer is easier to read: bigger, bolder text with a light outline, and a calmer parchment under "
        "it. Still hard over a busy spot? Raise its opacity in Overlays › Appearance.",
    ],
    "2.50.0": [
        "Overlays › Appearance (was Look) says what opacity does and shows it in %.",
        "The Mechanic Helper bar is its own thing now: switch it on in Overlays › Mechanic Helper and it shows over "
        "the game whether the Session timer is running or not.",
        "Fix: the Mechanic Helper icons are bigger and clearly green (on) / red (off); the Session timer's clock no "
        "longer runs into its title; overlays stay at the very bottom of the screen when you lock them.",
        "Report a bug: Tab moves to the next box, the buttons are never cut off, and there's no name box.",
    ],
    "2.49.0": [
        "Settings is the cog at the top of the dock; the Toolkit menu is at the left end of the taskbar, like Start.",
        "Every on / off option is a switch now.",
    ],
    "2.48.0": [
        "The taskbar shows ⬆ Update when a new version is out - whatever window you're in.",
        "🐞 Report a bug on the taskbar: describe it, see exactly what's sent, and it lands on GitHub for the "
        "developer.",
    ],
    "2.47.0": [
        "Overlays › Look has four Path of Exile 2 styles: Runeshape parchment (now with real grunge, and the clean "
        "layout from the mockup), Relic tooltip, Carved frame and Quiet HUD - or the old Classic dark.",
        "Price checks › Stash tab: ＋ Tab is a proper button.",
    ],
    "2.46.0": [
        "Strat guides are CSV files now (open them in Excel or Google Sheets) - Download Format, Export and Import. "
        "Older .txt guides still import.",
        "Farm Ledger > Export > Strat guide: turn your setup and its numbers into a guide to share.",
        "Money Makers checks once a day what a strat's waystone and tablets cost on the trade site (\"Cost now\").",
    ],
    "2.45.0": [
        "Money Makers > Farm Ledger (was Run tracker): does a farming setup really make money? Add your waystone and "
        "tablets with Ctrl+Alt+C (priced for you, or type your own price) and your atlas trees.",
        "Every few runs (you pick how many) a box asks for the loot: Ctrl+Alt+C each drop in game and see what it's "
        "worth item by item (poe.ninja), minus what the runs cost.",
        "A spreadsheet of your logs, divines per hour, return on cost, a chart, setups side by side, and CSV export.",
    ],
    "2.44.0": [
        "Session tracker is now Overlays: the Session timer, the Mechanic Helper, Notes and their Look (style and "
        "opacity) are tabs in one window, each with its own options.",
    ],
    "2.43.0": [
        "New look for the Session timer, Notes and the Mechanic Helper bar (was Helpers): parchment, like the "
        "remnant's reward book. Prefer the old dark look? Settings > Appearance > Over the game.",
        "Settings > Appearance > Over the game: how see-through each of them is. They still move by their title bar "
        "and lock with the lock.",
        "Remnant prices stay while the book is open - hovering a reward no longer makes its price vanish. The "
        "runeshape tips show with the first prices, and can be switched off in Settings too.",
    ],
    "2.42.0": [
        "Price checks: Manual Add and Stash tab now keep separate lists - switch between them at the top.",
        "Stash tab has its own tabs, one per stash tab you price (each remembers its price). Press ＋ Tab to add "
        "one; right-click a tab to rename or delete it.",
    ],
    "2.41.0": [
        "Waystone prices are more realistic: when only a few match, the price is the cheapest real offer (not the "
        "middle one), and it never says High confidence from a handful of listings.",
        "Tip: Listings set to \"Any\" counts offline sellers' old asks - the price check now says so. Instant Buyout "
        "is closest to what really sells.",
    ],
    "2.40.1": [
        "Stash tab reads every item, even hundreds of the same kind (a tab of 455 waystones read 234 before). Wealth "
        "syncs read big tabs completely too.",
    ],
    "2.40.0": [
        "Runeshape tips: while a remnant's prices show, a small list next to them rates every runeshape for loot, "
        "S to D (S: Opulent, Power, Oath). Switch it off in Session tracker > Alerts (Runeshape tips).",
        "Fix: the Ritual reminder when you leave a map with rituals unfinished works again - the Ritual watcher was "
        "stopping the moment it started. Going back into the same map also keeps its count.",
        "Fix: Breach and Ritual banners show see-through text again (they had a black box with some themes).",
        "Stash tab reads the whole tab now (it seemed to stop at 20 items): it reads everything first, then prices "
        "it, and tabs with more than 100 tablets, jewels or waystones are split by type / tier so all of them are "
        "found.",
        "Fix: Stash tab's currency (e.g. Mirror of Kalandra) really stays now - it went back to Divine Orb when the app "
        "started - and its name no longer stays highlighted after you pick it.",
    ],
    "2.39.1": [
        "Fix: Expedition Remnant Price Checker - a reward poe.ninja doesn't list (like Warding Rune of Obsession) now "
        "shows \"no price\" instead of nothing, and can never get a similar-named item's price.",
    ],
    "2.39.0": [
        "The Session timer shows a small clock and the date, so you can keep track of the time in game. It follows "
        "your 12 / 24-hour setting; switch it off in Settings > Appearance > Clock.",
        "Fix: the Helpers bar could open below the bottom of the screen when the timer sits low. It now opens above "
        "the timer when there's no room under it, and always stays on the screen.",
        "Remnant price tags are shorter (16ex, 20c, 29d) and make no sound.",
    ],
    "2.38.0": [
        "Fix: the Expedition Remnant Price Checker could black out the game and flicker. Each price is now its own "
        "small tag, and the watcher never sees its own tags.",
        "The Helpers bar (Breach, Delirium, Ritual, Remnant) is its own small window: never cut off, shows with the "
        "Session timer, and you can move it anywhere.",
        "Money Makers is tagged BETA, and Stash tab's BETA tag now sits inside its button.",
        "Fix: Stash tab's currency no longer jumps back to Divine Orb - scrolling the mouse wheel no longer changes "
        "any dropdown (pick with a click or the arrow keys).",
        "Every feature is checked against Grinding Gear Games' rules: one key press = one action, nothing acts in the "
        "game by itself, nothing touches the game. See TOS.md on GitHub.",
    ],
    "2.37.0": [
        "New: Expedition Remnant Price Checker. Open a remnant's reward book and every reward gets its poe.ninja price "
        "right next to it, the best one ★ - by itself (Auto, no box to draw) or with Ctrl+Alt+R. Switch it on in "
        "Session tracker > Alerts or click \"Remnant\" in the timer's Helpers bar.",
        "The idea comes from PoE Ancients Price Helper by Pedro Quitério - thank you! None of its code is used; this "
        "is our own version (see Settings > About).",
    ],
    "2.36.0": [
        "Right-click a row for what you'd want to do with it: in Price checks Re-price, Copy name, Open on trade site, "
        "Mark listed / sold / removed; in Market Insights and Regex Favorites their own actions too.",
        "The Menu key (or Shift+F10) opens the same menu from the keyboard, on lists and text boxes alike.",
    ],
    "2.35.0": [
        "One kind of message popup for the whole app: in the app's bottom-right corner, with an icon for info, done, "
        "warning or problem. They stay up longer for longer text, wait while your mouse is on them, and never take "
        "your keyboard.",
        "Missed one? Settings > Advanced > Recent messages keeps the last 20.",
    ],
    "2.34.0": [
        "A cleaner, steadier look: the same text sizes and spacing everywhere, and buttons that tell you what they do - "
        "the main action in your accent color, deleting and clearing in red, small helpers quiet.",
        "Every theme and accent color now has readable text (checked against the WCAG accessibility standard). Buttons "
        "with a bright accent (gold, lime, teal, ice) use dark text now.",
    ],
    "2.33.1": [
        "Map library: the ✖ Avoid button is no longer cut off.",
    ],
    "2.33.0": [
        "Tools that belong to another tool now sit in its title bar: 🗺 Map library in the Session tracker; Mod book, "
        "Under the hood and Market Insights in Price checks. The Toolkit menu shows them under their parent.",
    ],
    "2.32.0": [
        "New: Map library (Toolkit, or 🗺 in the Session tracker) - every map, tower, citadel, pinnacle fight and league "
        "area. Rank them S to D or ✖ Avoid; your rank shows on the in-game timer.",
        "The Session tracker now counts pinnacle fights (Simulacrum, Arbiter, Breach, Ritual ...) and special maps, and "
        "learns new areas the first time you enter them. Hideouts are never counted.",
        "Share your map ranks as a file (⋯ Share), or take the community's - on import you choose Replace all, Add and "
        "update, or Add new only.",
    ],
    "2.31.0": [
        "Community Mod book: everyone's price checks pool their mod prices (anonymously, once an hour), so stars and "
        "estimates get better for everyone - most of all early in a league. Your own rules always win.",
        "Price checks shows how many community prices there are and how many you added. Settings > General turns "
        "sharing off; you still get everyone else's prices.",
        "Removed: the Ritual Capture button and the Lag finder.",
        "Price checks: Stash tab is marked BETA (it often reads tabs only partly - Ctrl+Alt+C is the reliable way).",
        "The \"Ctrl+Alt+C only\" box left the toolbar: Settings > Hotkeys > \"Also add items copied another way\".",
    ],
    "2.30.0": [
        "Money Makers > Strats: Official, Community and Mine. Community is a board where players post their strats, "
        "upvote the good ones and report junk. No account needed: just pick a name the first time.",
        "Post one of yours with 📤 Post to Community; the best ones get promoted to the Official list.",
        "Lucrative Strats shows Community one-liners too, with upvotes.",
    ],
    "2.29.1": [
        "Fixed: updating no longer opens black windows (\"Pinging 127.0.0.1\") over and over - the new version "
        "now installs itself, with no windows at all.",
    ],
    "2.29.0": [
        "Money Makers, reworked: browse strats by what they are (Mapping › Breach, Crafting › Tablet crafting ...), "
        "search by tag, and filter by waystone tier and effort. Effort is shown in words (Thinking: Easy ... Big "
        "brain; Clicks per hour: Chill ... Frantic).",
        "Strats have their own sections for tablets, waystones, atlas setup and craft steps. Download Format saves "
        "the layout as a text file to fill in with Notepad, then Import. Your 2.28.0 strats are converted.",
        "Money Makers > Lucrative Strats: quick one-line money makers. Tablet Crafting: what to do with each tablet, "
        "the valuable tablet mods with a stash regex and a trade link, and Check my tablet (copy one with Ctrl+C).",
    ],
    "2.28.0": [
        "New: Money Makers - farming strats shared by the community, all in the same layout, rated by Thoughts per "
        "Click (how much thinking) and Clicks per hour (how busy your hands are). New strats arrive by themselves.",
        "Money Makers > Run tracker: Start / End each run, type the profit if you like, see runs and divines per hour.",
        "Add your own strats, and press Share to send one to everyone (opens a filled-in GitHub form).",
    ],
    "2.27.0": [
        "Chat commands moved: Settings > Chat commands (it's no longer in Utilities).",
    ],
    "2.26.4": [
        "Regex: Jewels and Gear items open fast now. Click a mod to pick it; click its Value cell to type a value.",
        "Price checks: what the ★ stars mean is shown up top.",
        "Price checks: \"Show all\" is now \"✕ Clear filters\" - it clears Category, Rarity and Type.",
    ],
    "2.26.3": [
        "Fixed: updating could hang, with a black window popping up again and again, until you closed the app.",
    ],
    "2.26.2": [
        "Regex: switching between tablets, waystones, jewels, gear ... no longer freezes the app.",
        "Fixed: maximised when you closed it -> maximised when you open it (for real this time).",
        "Price checks shows the time left right from the start, not only after a few items are done.",
        "Price checks: the column is called \"Valuable mods\", and a line under the list explains the stars.",
    ],
    "2.26.1": [
        "Fixed: after changing the theme (the app restarts itself), the Delirium alert could fail with "
        "\"No module named 'cv2'\".",
    ],
    "2.26.0": [
        "Session tracker timer: \"Helpers: ● Breach | ● Delirium | ● Ritual\" - green is on, red is off. Click one "
        "to switch it; ⚙ opens their options.",
        "Price checks: the time left while pricing shows up top, next to Priced and Require Review.",
        "Exchange rates > Arbitrage (BETA) finds loops again (Grinding Gear Games changed how the history names "
        "items). Press Refresh; gains that look too good to be true are left out.",
        "Settings > Advanced: the Lag finder (was \"Slowness recorder\").",
    ],
    "2.25.4": [
        "Fixed: maximised when you closed it -> maximised again when you open it.",
        "Settings > Advanced > Slowness recorder: if the app feels slow, press Start and use it for a few minutes - "
        "it writes down what was busy whenever the window got stuck.",
    ],
    "2.25.3": [
        "Market Insights: waystone previews show the real numbers (pack size, rarity, drop chance, revives).",
        "The app's own popups (like the Fast pace warning) open in the middle of the app.",
    ],
    "2.25.2": [
        "Popups (Market Insights' item preview, the price popups) open on the monitor you're using, next to the "
        "mouse - not on your main monitor.",
    ],
    "2.25.1": [
        "Faster with long lists: prices coming in no longer slow the app down, and saving no longer freezes it for "
        "seconds.",
    ],
    "2.25.0": [
        "Copy marker: double-tap Esc clears the + marks (when you keep them). Pick the +'s color in Settings > "
        "General > Copy marker.",
    ],
    "2.24.0": [
        "The Ctrl+Alt+C marker is a small +. Settings > General > Copy marker: how many seconds it stays (10 by "
        "default), or keep the marks until you hold Esc for 3 seconds.",
        "Price checks: a \"★ Valuable\" column - one star for each mod your Mod book rates valuable. Click its "
        "heading to sort.",
    ],
    "2.23.1": [
        "The app opens where you left it - same place, same size, maximised if it was.",
    ],
    "2.23.0": [
        "The sticky note has tabs: + adds one, double-click renames, right-click deletes.",
        "Game search: \"more ›\" shows a result's whole text.",
        "Exchange rates > Arbitrage > Live scan: each new hour of Currency Exchange history is read as soon as it's "
        "out, and a new uneven loop pops up.",
    ],
    "2.22.0": [
        "Regex works for jewels (Ruby, Emerald, Sapphire, Diamond, Time-Lost) and gear (rings, amulets, belts, armour, "
        "weapons ...) - with the same at least / range / at most boxes.",
    ],
    "2.21.0": [
        "Price checks: type what an item sold for and press 💰 Mark as sold. The Mod book learns from real sales. "
        "Show: Sold lists them.",
        "Regex: in a mod's box, 50 = at least 50, 50-80 = from 50 to 80, <80 = at most 80.",
        "Regex Favorites: a 📋 Copy button on every row.",
    ],
    "2.20.0": [
        "Mod book tiers: give mods a tier from S (matters most) to D. When no listing has all of an item's mods, the "
        "D-tier ones are left out first, then C - so you get a price instead of no match.",
        "Import rules now puts the rules into your Mod book (and your own export works as a backup). Export takes "
        "all your rules for that page, tiers too - waystones and relics as well.",
        "The built-in rules are updated to the author's current ones. Your own rules always win.",
    ],
    "2.19.0": [
        "Ctrl+Alt+C now leaves a small ring for 10 seconds where your mouse was, so you can see what you've copied. "
        "Turn it off in Settings > General > Copy marker.",
        "Price checks: a ★ before an item's name for each mod your Mod book rates valuable (that's why it's gold).",
    ],
    "2.18.0": [
        "Fixed: the Mod book stopped learning from listings (the trade site changed how it sends mods). What was "
        "saved since then is repaired.",
        "Market Insights: click an item to see it like the game shows it. Your own stash-tab listings (and other "
        "people's marker tabs) no longer top the list.",
        "Wealth: \"Use my Price checks tab\" adds the tab you read in Price checks. Low-confidence rare prices say "
        "Price manually, like in Price checks.",
        "Price checks: no more Under the hood / Wiki links. Picking the Fast pace warns you about rate limits.",
    ],
    "2.17.0": [
        "Game search > Anoints: every notable you can anoint, the three Liquid Emotions it takes and what they cost "
        "on poe.ninja, with the total.",
        "Search by the notable, by what it does, or by an emotion (e.g. Isolation) to see every anoint that uses it.",
    ],
    "2.16.0": [
        "Your own listings never count towards a price (the account name you typed for Stash tab / Wealth).",
        "Low-confidence prices say \"Price manually\" instead of a guessed number, and aren't in the total.",
        "Price checks > Prices in: show every price in Divine, Exalted, Chaos or Vaal Orbs.",
        "Stash tab prices can be in any currency, from Exalted to Mirror of Kalandra.",
    ],
    "2.15.0": [
        "Fixed: the Ritual watcher couldn't read some counters (like 3/4).",
        "The Ritual reminder only comes when you did some rituals but left before finishing (0 done = skipped).",
        "Game search: the \"how the price checker sees it\" links are gone; results link to the wiki instead.",
    ],
    "2.14.1": [
        "Fixed: the Ritual watcher didn't work in the app you download (it stopped right after starting).",
    ],
    "2.14.0": [
        "Ritual watcher (Session tracker > Alerts): reads the Ritual counter (0/3 ...) from your screen and reminds "
        "you if you leave a map with rituals not done. The timer shows the count.",
        "Session tracker > Options: start tracking when StashOfExile2 starts.",
    ],
    "2.13.0": [
        "Breach alerts look like the Delirium alert again: big flashing text over the game, no box. They go by "
        "themselves after a few seconds.",
        "Top value is now called Market Insights; \"Dearest listings seen\" is \"Most expensive listings seen\".",
    ],
    "2.12.0": [
        "Lists have striped rows, like a spreadsheet. Ctrl+C copies the selected rows; right-click a list to copy, "
        "select all, delete or undo.",
        "Boxes you type in: Ctrl+A selects everything, Ctrl+Z undoes, and right-click has Cut / Copy / Paste.",
        "Ctrl+Shift+D opens poe2db's modifier list in your browser (change the key in Settings > Hotkeys).",
        "The quick start guide is in the Toolkit menu too.",
    ],
    "2.11.0": [
        "Breach: if your Hiveblood was almost full, leaving the map reminds you to spend it at the Genesis Tree - "
        "until you do. Switch it off with \"Remind me when I leave the map\" in the Session tracker's Alerts.",
    ],
    "2.10.2": [
        "Fixed: windows disappearing behind the app when you maximize, restore, snap or resize it.",
        "Fixed (likely): typing stopping in boxes after the app was resized.",
    ],
    "2.10.1": [
        "Windows that disappeared when you resized the app come back on their own.",
        "A recorder for the typing and window bugs (off unless switched on for a problem report).",
    ],
    "2.10.0": [
        "Session tracker: Delirium and Breach alerts are on its main page, each with on / off, sound and Test. The "
        "timer over the game shows whether they're on.",
        "Breach: a second, stronger banner when the game says you can't store any more Hiveblood.",
        "The Session tracker is out of Labs. Ctrl+Alt+S starts / stops it and Ctrl+Alt+P pauses it in game (change "
        "them in its Options).",
        "Fixed: typing in a box could stop working until the window was reopened.",
        "Fixed: windows now stay inside the app when you make it smaller.",
        "Settings > About: what's new, the GitHub page and our Discord. New installs get a short quick start guide.",
    ],
    "2.9.0": [
        "Session tracker > Options > Alerts while you play: a big banner when your stored Hiveblood is almost full "
        "(Breach), and the Delirium alert's on / off.",
        "Wealth sync carries on past a listing it can't read, and says so.",
    ],
    "2.8.2": [
        "Fixed: reading a stash tab of Irradiated Tablets added nothing.",
    ],
    "2.8.1": [
        "Reading a stash tab now says how many items it found, which it left out and why, and what happened to "
        "each one.",
        "The other way to add items is called Manual Add.",
    ],
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
        "Pick how the app looks: Settings > Appearance > Look of the app has themes, accent colors and text size.",
        "A start-up screen shows while the app loads (you can turn it off in Settings > Appearance).",
        "Check for updates only ever offers a newer version.",
        "The sticky note's colors are set in the Notes window. Move and resize the note by dragging it.",
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


def split_notes(notes):
    """[(version, entry)] newest first -> (big hero rows, small lines) for the card (see the standard above)."""
    big, small = [], []
    for _v, entry in notes:
        if isinstance(entry, dict):
            for icon, title, text, go, area in entry.get("big", []):
                if len(big) < MAX_BIG:
                    big.append((icon, title, text, go))
                else:
                    small.append((area, f"{title}: {text}"))
            small += [tuple(x) for x in entry.get("small", [])]
        else:
            small += [("", line) for line in entry]
    return big, small


def plain_lines(entry):
    """A version's notes as plain lines (About › Version), big ones first."""
    if not isinstance(entry, dict):
        return list(entry)
    return [f"{title} - {text}" for _i, title, text, _go, _a in entry.get("big", [])] + \
        [f"{a}: {t}" if a else t for a, t in entry.get("small", [])]
