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
NOTES = {
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
        "the main action in your accent colour, deleting and clearing in red, small helpers quiet.",
        "Every theme and accent colour now has readable text (checked against the WCAG accessibility standard). Buttons "
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
        "Copy marker: double-tap Esc clears the + marks (when you keep them). Pick the +'s colour in Settings > "
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
        "Fixed: windows disappearing behind the app when you maximise, restore, snap or resize it.",
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
