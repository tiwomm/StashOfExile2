"""
StashOfExile2 - a Path of Exile 2 price checker for tablets and jewels, with a window instead of a text dump.
Free software under the GNU GPL v3.0 (see LICENSE). Written by an AI (Claude, by Anthropic) under a human's direction.

VERSION 2.8   (2.8.1)
  How versions are numbered (from 2.0.0 on):
    MAJOR.MINOR.PATCH.  The 22 betas ended here: this build is 2.0.0. From now on every build gets a plain number:
      2.0.1, 2.0.2 ...  fixes (nothing new to learn)
      2.1.0, 2.2.0 ...  new features or changes you'll notice
      3.0.0             another big change
    Only when a bigger version needs testing first does it get a short run of release candidates (2.1.0-rc.1, -rc.2,
    shown as "2.1 RC 1"), never long beta numbers again. Older names still sort right: 2.0 beta 22 < 2.0 RC 1 < 2.0.
    "Check for updates" only ever offers a version newer than the one running (updates.is_newer).
  The test builds 1.33 to 1.45 were all on the way to 2.0; their notes are kept below.
  The app is this launcher (always called stashofexile2.py) plus the soe2 folder next to it. The version is in two
  places that must match: APP_VERSION below and __version__ in soe2/__init__.py; the launcher refuses to start a
  soe2 folder from another version. Your data never lives here: it is in %APPDATA%/StashOfExile2, shared by every
  version (settings.json, session.json, modbook.json, mod_rules.json, wealth.json, tabs.txt ...).

VERSION HISTORY
  2.8.1
       (1) Stash tab reading explains itself: how many listings were found at the tab's price, what was left out and
           why (another price, someone else's, unique, stack), and per item whether it was added, already in the
           list, unreadable or hit an error - in the message and in tab_reader_log.txt (data folder; rewritten each
           read). An error on one item is caught and counted instead of being lost. (A real read reported "Read 7,
           added 0" with nothing in error_log.txt; this is to find out why.)
       (2) "Ctrl+Alt+C" mode is called Manual Add.
  2.8.0
       (1) Price checks > Add items from: Ctrl+Alt+C | Stash tab (tabreader.py, tabreader_page.py). Stash tab reads a
           public Premium tab the way Wealth's synced tabs do (your account's listings at one odd price, e.g. 37882
           Divine Orbs; searches split when there are more than 100), turns each listing into Ctrl+Alt+C text
           (wealth.item_text) and adds it to the list to be priced. Uniques and stacks are left out; items already
           in the list are skipped. Only when you press Read tab; jobs run on the engine thread at priority 4 (behind
           the pricing it creates, ahead of a Wealth sync). Account name shared with Wealth (wealth_account); the
           tab's price is kept in SETTINGS pctab. Ctrl+Alt+C keeps working in both modes.
  2.7.2
       (1) Windows could still slip behind the app's window (with or without Always on top) and leave only the
           desktop showing: Tk's transient() doesn't make the app's window their real owner for borderless windows on
           Windows. DeskWindow.own_by_app sets the owner in Windows itself (GWLP_HWNDPARENT), so Windows always keeps
           them above it; it's checked every time a window shows, comes to the front or is restacked, and when the
           app's window takes the focus (Always on top on or off).
  2.7.1
       (1) Always on top hid every window: only the app's own window was made "topmost", and on Windows a topmost
           window sits above the windows it owns, so they were open but behind it. Now the desktop's windows follow
           the setting (DeskWindow.follow_on_top) and are put back above it in their order (Shell.restack) when it's
           switched, when a window opens or comes to the front, and when the app's own window takes the focus.
  2.7.0
       (1) Session tracker: only YOUR deaths count. A real PoE 2 log (Oct 2026) logs ": <name> has been slain." for
           party members too, and ": <name> has joined / left the area." for other players only (never you). So a
           death counts when the name is your character name (Options), or - with no name set - when that name hasn't
           joined or left your area; the first one counted is remembered as you (tracker cfg character_guess).
       (2) AFK: "AFK mode is now OFF." resumes a session that "AFK mode is now ON." paused (not one you paused).
       (3) Map stats: a maps-per-day chart for the last 14 days (tracker.daily_maps), with a red dot on days you died.
       (1) Mod book > Waystone rules and Relic rules: every waystone / relic mod from regexdata.json (RePoE), rated
           High / Normal / Ignore like tablet mods (filter, Set selected to, double-click). One row per mod; a
           two-line mod's rule covers both lines.
       (2) Waystone and relic rules are saved under their own names ("waystone:<text>", "relic:<text>",
           mods.rule_key), so they never pick up a tablet / jewel rule with the same words (before, the relic mod
           "#% increased movement speed" showed as High because of a jewel rule). Rules set from Regex in earlier
           versions move over once (mods.migrate_scoped_rules, SETTINGS rules_scoped_26). default_rules.json may
           list "waystone" and "relic" too.
       (3) Regex uses them for ★ and ★ Select valuable, and right-click saves to them.
       (4) Top value > Waystones / Relics: your ★ mods, how many items you've priced with each and the best one.
       (1) Item panel > Search filters (searchopts_page.py), like a trade site's own filters, for one item at a time:
           seller (Instant Buyout / + In Person / Online / Any), priced in (divine / exalted / chaos / exalted or
           divine), corrupted (Any / Yes / No), and for gear item level, quality and sockets minimums and "this base
           only / any base of its kind". Kept as rec["opts"] (only what differs from the usual); trade.apply_opts adds
           them to every search for that item (thread-local, set in engine.price_rec). Searches narrowed this way
           don't teach the Mod book (engine._stage).
       (2) Wiki ↗ link next to Under the hood: the item's base type on poe2wiki.net.
       (3) The source is on GitHub (main branch, one commit per version from 2.0.0), GPL-3.0. Releases build themselves:
           when main gets a new APP_VERSION, .github/workflows/release.yml builds StashOfExile2.exe on GitHub's Windows
           runner, tags v<version> and publishes the release that "Check for updates" reads.
  2.4.0
       (1) Lists behave the same everywhere (listkeys.py): click / Ctrl+click / Shift+click / Ctrl+A select, Delete
           removes, Ctrl+Z undoes - routed to the list last clicked in the window in front (Delete in Wealth works
           again: the key never reached the list, only the Price checks window got it). Undo per window, 20 deep.
       (2) Wealth: Delete removes counted or synced rows (combined stacks: all of them), snapshots and tabs; Clear…
           empties the item list (tabs and history stay); Undo button + Ctrl+Z.
       (3) Regex: "Saved searches" -> a Favorites tab (regex_favorites.json + .backup.json, every item type in one
           list; the old regex_presets.json is brought over once). save_json now returns False and logs to
           error_log.txt instead of failing silently (config.SAVE_ERRORS).
       (4) Exchange rates in tabs: Rates / Exchange Helper / Arbitrage. Arbitrage (arbitrage.py, exchange_page.py):
           GGG's public hourly Currency Exchange history (web.poecdn.com/api/currency-exchange/poe2/<hour>, no key),
           three-market loops whose average rates don't agree; only on Refresh, finished hours cached, 1.5 s between
           requests, stops on 429. Plus "Check a flip you see in game". (poe.ninja can't show this: its prices come
           from each currency's busiest pair, so they always agree.)
       (5) Top value: "Your most valuable" comes from value_log.json (valuelog.py), kept after Clear list; details
           panel; Delete + Undo. "Dearest listings seen" stores and shows each listing's name, mod lines, own price
           and the search it came from (market.db listings: name, lines, price_txt, qid).
       (6) Session tracker: Profit / hour explained in Options (with the count-on-stop setting next to it, worded
           plainly); a "Profit / hour" card instead of "Wealth at start"; a note and a Set up Wealth button when
           Wealth is empty. "Timer over the game" is called Options.
       (7) What's new no longer shows "Coming next".
  2.3.0
       (1) Price checks: deleting many rows no longer hangs (the item panel redraw is debounced, app._on_select_soon).
       (2) Jewels / tablets: the spread is measured per search (engine.spread_of) - a wide spread gives a ROUGH PRICE
           with Low confidence instead of CHECK BY HAND; a stat filled in twice is dropped instead of giving up; when
           no listing has all the mods together, the best mod alone gives a floor price.
       (3) Settings > Advanced > Problem report (report.py): a zip of recent price checks and logs to look at misses.
       (4) Session tracker: "gold from selling" removed (it can't be tracked reliably); its card is "Fastest map".
       (5) Wealth: step-by-step setup (wealth_setup.py; opens the first time Wealth opens empty, and from "Set up
           step by step"); "Up X since yesterday"; snapshots say why they were taken (wealth.snapshot why=) and two
           can be compared; your own prices are marked and right-click goes back to the market price.
       (6) trade.estimate leaves out listings under 1/5 or over 5x the median (two far apart: the cheaper); the
           Session tracker's opacity slider has its own row (it sat on top of its label).
  2.2.0
       (1) Regex key (SETTINGS regex_key, also in Settings > Hotkeys): in game, copies the chosen search to the
           clipboard (regex_hotkey_search: the search set up for a kind, or a saved search) and shows a small card.
           Clipboard only - nothing is sent to the game.
       (2) Currency Exchange helper (Exchange rates window): sell X of A for B -> market ratio and three whole-number
           ratios to post (quick sale -2%, fair, patient +2%; rates.whole_ratio / exchange_offers), with what you'd
           get for your amount.
       (3) CSV export (csvexport.py): every map run (Map stats), sessions (Past sessions), Wealth history and items
           (Wealth > More).
       (4) ROADMAP.md rewritten as one list of releases (done / next up / parked); "Coming next" on the card follows it.
  2.1.0
       (1) Session tracker > Map stats: every map you ran, over all sessions (tracker.map_stats): runs, best,
           average, deaths, last run; pick a map for its leaderboard (your 10 fastest runs, the running map in green).
           Time = time inside the map; visits under 30 s don't count. Sortable columns; most-run first.
       (2) Top value (Labs tool, insights_page.py): per kind (Tablets, Waystones, Jewels, Relics) your most valuable
           priced items (double-click opens it in Price checks), the mods worth the most (Mod book data: median ask
           of listings with the mod, ★ = High in your rules) and the dearest listings seen (market.db, this league;
           Market.top_listings). Nothing is searched for it.
       (3) Clock: 12-hour or 24-hour only; until you pick, it follows Windows (12-hour if it can't tell).
       (4) Calculator: no Windows calculator button.
       (5) What's new / intro rewritten in plain words: only what helps you use the app.
  2.0.0  (the end of the 2.0 betas)
       (1) Updates never go backwards: version tags are read the same however they are written ("v2.0b17",
           "2.0 beta 17", "2.0.0-beta.17"); the old reader took "2.0b17" for 2.0.17 and offered beta 17 to beta 22.
           updates.is_newer() is the one check.
       (2) A start-up screen (splash.py): the chest with a breathing glow, version and league, and the real steps
           (settings, building windows, restoring windows, trade site mod list). Closes when the app is ready (at
           most 3 s after the windows are built), on a click, and never takes the keyboard; Settings > Appearance
           can turn it off. The welcome card waits for it.
       (3) The app's look (Settings > Appearance > Look of the app): theme (Midnight blue, Ember, Forest, Amethyst,
           Crimson, Graphite), accent colour and text size, for every window. style.apply_look() at start-up: every
           colour given to Tk (widgets, canvases, ttk styles, option database) passes through style.theme_color(),
           which moves the app's blues to the theme's hue and keeps meaningful colours (rarities, green / red, gold,
           the accent). The accent button is derived from the accent colour. Restart now (App.restart_app) restarts
           the app to apply it (launcher: --restarted waits for the old window to close).
       (4) The note's colours / opacity / font are back in the Notes window; the pixel boxes for its place and size
           are gone (drag and resize the note itself; "Put it back in the corner" if it's lost).
       (5) Numbering: this is 2.0.0; see "How versions are numbered" above.
  2.0 beta 22
       (1) The item panel (mods with Min / Max, Search with these values, Mark listed ...) could vanish: its width was
           saved at close even when the Price checks window was closed or minimised (a real window since beta 13
           reports 1 pixel then), or after dragging the divider to the edge. Widths under 250 are no longer saved,
           a saved one is put back to 430, and letting go of the divider near the edge leaves the panel 300 wide.
       (2) Price checks: a # column (the record id = the order items were added), "↕ Order added" next to Show all,
           and ▲ / ▼ on the column the list is sorted by.
  2.0 beta 21
       (1) Settings in tabs (SegBook): General (league / pace, window, Labs, updates), Appearance (launcher, wallpaper,
           clock, the note's colours / opacity / font - moved here from the Notes window), Hotkeys, Advanced (Mod
           book, Under the hood, data folder). App.open_settings_tab(name).
       (2) Launcher: dock, desktop icons or both (Shell.set_launcher; one is always on). Without the dock, Toolkit sits
           on the taskbar next to Settings.
       (3) Clock: time over the date, like Windows; 12 / 24-hour follows Windows (registry iTime) or your choice.
       (4) Calculator tool (calc.py): safe arithmetic only (ast), 12k / 5% / ans, history, Windows calculator button.
       (5) Every question / file dialog belongs to the window in front (App.parent_dialogs): a question from Wealth
           made Wealth disappear behind the main window. Wealth's list selects several rows (Ctrl+A) and Delete
           removes all selected counted stacks with one question. "How it works" guide for Wealth.
       (6) Price checks: the update button is gone from the key bar (Settings > General has it); in its place what
           Price checks is for; gear prices show "Guess" / "Rough guess" with a note to check by hand.
       (7) Ctrl+Alt+C is fixed; one-key copy is marked experimental with a warning and "Reset to Ctrl+Alt+C only".
       (8) Mod book is hidden from the dock / menu (Settings > Advanced opens it). Game search: picking a category
           with nothing typed lists all of it. Session tracker: "Find Client.txt" only when it can't be found, with
           the usual Steam / standalone folders; right-click the log line to pick another.
       (9) The welcome / what's new card has "Coming next" (whatsnew.NEXT); ROADMAP.md and README.md in the kit.
  2.0 beta 20
       (1) Regex and the Mod book work together: each Regex mod is rated with the same rule the price checker uses
           (mods.impact_key: your rules, then learned-from-prices, shared rules, built-in). ★ = High, dimmed =
           Ignore. "★ first" sorts them to the top (remembered), "Only ★" hides the rest, "★ Select valuable" puts
           every ★ mod in "I want" with Match: Any. Re-rated whenever the Regex window comes to the front, so a rule
           changed in the Mod book shows straight away. Right-click a mod to rate it (High / Normal / Ignore): it is
           saved as a Mod book rule (App.set_rules), which also re-prices affected items. Tablet mods all have
           built-in rules; waystone and relic mods start unrated, so you rate the ones you care about.
  2.0 beta 19
       (1) Price checks: "🗑 Delete" (and the Del key, which used to ask to clear the whole list) deletes only the
           selected items (click, Shift+click, Ctrl+click, Ctrl+A); Ctrl+Z / Undo puts them back and selects them.
           A deleted item copied again is added again.
       (2) Waystones: the endgame numbers are worth the same, so none is starred by default and none is dropped:
           the searches are all at your values, all at 90%, all at 75% (and, if you star some, only those at 90%).
  2.0 beta 18
       (1) Waystone price checks (soe2/waystone.py). A waystone's price comes from its endgame numbers, which the trade
           site searches as Endgame Filters: Waystone Drop Chance (map_bonus), Pack Size (map_packsize), Item Rarity
           (map_iir), Monster Rarity (map_rare_monsters), Monster Effectiveness (map_magic_monsters), plus Experience /
           Gold if a waystone shows them; Revives Available is read but not searched unless you tick it. Searched by
           its exact base ("Waystone (Tier 15)"), rarity and corrupted state, at your value or more. Its monster /
           area mods are shown but never searched.
           Up to 4 searches until enough listings: all at your values; all at 90%; the least important half of the
           ☑ numbers let go (Monster Effectiveness, then Monster Rarity, Item Rarity, Pack Size); only the ★ ones
           (Waystone Drop Chance). Waystones are handled like gear ("map:" stat ids -> map_filters in gear.build_query).
  2.0 beta 17
       (1) Key boxes didn't get the key on Windows (the app's borderless windows didn't have the keyboard). They now
           take it from the app's own keyboard watcher, which sees every key wherever the focus is; the key is used
           up, so it doesn't also do something in the game. Only one box waits at a time; a click elsewhere, Esc or
           15 seconds gives up.
       (2) Mouse buttons as hotkeys: middle, Mouse 4 and Mouse 5 (side buttons), with Ctrl / Alt / Shift if you like,
           for every hotkey (one-key copy, chat commands, notes, session tracker). Stored as MButton / XButton1 /
           XButton2 (AutoHotkey names). The mouse hook is only on while a hotkey uses a mouse button or a key box
           waits, and it only looks at those three buttons.
       (3) Clicking a window gives it the keyboard (to the box you clicked), so typing works in every window.
       (4) "Windows open at random": restoring the app re-showed and re-stacked every window, and Notes / the timer
           showed whenever the app was in front. Now Windows itself keeps a minimised app's windows, they are only
           re-shown after the tray; Notes / the timer show only while the game (or the note itself) is in front; and
           "Always on top" no longer touches the desktop's windows or the note / timer.
  2.0 beta 16
       (1) Hotkeys are chosen by pressing them (style.KeyCapture): click the box, press the key with any Ctrl / Alt /
           Shift. Saved at once (Settings > Hotkeys, Chat commands, Notes, Session tracker), so the "Save keys"
           buttons are gone. Esc keeps the old key; Backspace, Delete or right-click clears it. While a box waits
           for a key the app's own hotkeys stand still, so pressing F6 there sets F6 instead of showing the note.
           Keys are stored as readable text (F3, Ctrl+Shift+H); old AutoHotkey-style ones (^h) still work.
  2.0 beta 15
       (1) Notes and the Session timer (overlaywin.py, follow_game) only show while Path of Exile 2 or one of this
           app's own windows is the window in front; they hide when you switch to anything else. Showing them never
           takes the keyboard from the game, and clicking the timer never does either (WS_EX_NOACTIVATE). Settings >
           Window: "Notes and timer only while Path of Exile 2 is in front" (on by default).
       (2) One-key copy (Settings > Hotkeys, off until you pick a key): while the game is in front, that key presses
           the game's own Ctrl+Alt+C once (one key press = one copy; nothing is clicked, moved or sent to the game's
           servers), so pricing a tab of tablets is hover + one key per tablet.
       (3) Settings moved from the bottom of the dock to the left end of the taskbar, under the dock.
  2.0 beta 14
       (1) Settings scrolls (scroll bar and mouse wheel) when its window is smaller than its content: style.ScrollArea,
           for any window that needs it.
       (2) Price breakdown (the old Item library) is now "Under the hood", part of Price checks: opened from the link
           at the top right of Price checks or from "Under the hood" on an item (and from Game search). It is no longer
           on the dock, the Toolkit menu or the desktop (modules can now be hidden = True). Old names still open it.
  2.0 beta 13
       (1) Every window on the desktop is now a real (borderless) window owned by the app's window, instead of a frame
           drawn inside it. Windows itself moves, stacks and repaints them: a window follows the mouse while you drag
           it (the outline and the "Show window contents while moving" setting are gone), and clicking any window
           brings it to the front. They follow the app's window when it moves, and hide with it (minimise / tray).
       (2) The welcome / what's new card is a window of its own and stays above everything until you press Got it.
           On first start it asks which league you play; if you don't pick, the newest league is used (the first
           league in the trade site's list that isn't Standard, Hardcore, SSF or a private league).
       (3) Item inspector is now called Price breakdown (it shows why an item got its price); Price checks' link on
           each item says "Price breakdown". The old names still open it.
       (4) New icons drawn for the app (an open treasure chest) and for the Delirium alert (a pale shard): no game art
           is shipped as icons any more. (The small screen crops the Delirium alert matches against stay: they are
           only compared with your own screen.)
       (5) One look for windows over the game: Notes and the Session timer share overlaywin.py (title bar, border,
           lock button, resize edges, opacity). Anything shown over the game later uses it too.
  2.0 beta 12
       (1) A welcome / what's new card: once after a fresh install (what the app is, what it does) and once after each
           update (what changed since the version you had). Toolkit menu > What's new shows it again.
       (2) Item library is now the Item inspector, a tool (not a module): for when a price looks wrong, it shows how the
           price checker read an item. Price checks has "How was it read?" on every item to open it there.
       (3) No website data or links: tabs.txt and jewels.txt (every tablet / jewel mod for the Mod rules pages) are now
           built from RePoE's export of the game files (tools/build_modlists.py), in the game's own wording; Time-Lost
           jewel lines use Exiled Exchange 2's wordings (MIT). Rules saved with the old wording are moved to the new one
           by themselves (also when importing someone's rules file). Game search links to the Item inspector instead
           of a website ("how the price checker sees it").
  2.0 beta 11
       (1) Moving or resizing a window no longer leaves smeared copies of it behind: an orange outline follows the
           mouse and the window jumps there when you let go (like Windows with "show window contents while
           dragging" off). Settings > Desktop > "Show window contents while moving" brings back live moving.
  2.0 beta 10
       (1) Game search (new tool): your PoE2 Keyword Search page rebuilt as a window of the app. 8,534 skills, supports,
           uniques, bases, currency, soul cores, runes, modifiers and keywords from the RePoE export of the game files.
           Every word must match, -word leaves things out, "exact phrase" for phrases; category buttons with live
           counts; the words are highlighted. Right-click a line in the Item library: Look up.
           (searchdata.json; tools/build_searchdata.py rebuilds it from a newer page.)
       (2) Labs: experimental features are marked BETA and only show when Labs is on (Settings > Labs): Wealth, the
           Session tracker and Game search. Labs starts on if you already use Wealth or the tracker.
       (3) The dock has three groups: MODULES (big tools you work in: Price checks, Mod book, Item library, Wealth),
           TOOLS (quick helpers that only do something while open: Regex, Exchange rates, Game search) and UTILITIES
           (keep working in or over the game while closed, with an on/off dot: Session tracker, Chat commands, Notes,
           Delirium alert). Tools have their own colour.
       (4) The session timer shows while a session runs (Show timer brings it up any time).
  2.0 beta 9
       (1) New utility: Session tracker. Start / Stop / Pause (buttons or your own hotkeys) and it shows:
           session time, where you are, this map's time, maps done, average map time, gold from selling, Wealth at the
           start and, when you stop, the profit and profit per hour. A small timer sits over the game: drag it,
           resize it from its edges, lock it, pick its lines and opacity.
           Maps are counted from the game's own log file (Client.txt): a map is counted once per seed, so going back
           into it through its portal after a hideout trip is the same map; a new map has a new seed. Only the end of
           the file is read (it can be hundreds of MB) and only new lines after that. Client.txt is found in the usual
           Steam / standalone folders, or pick it with "Choose Client.txt…".
           Profit: what Wealth holds at the end minus what it held at the start, both at today's prices (a price
           change during the session isn't profit). Stopping offers "Count in Wealth first" so new currency is
           included; the session ends by itself when you finish counting. Past sessions are kept, with notes.
       (2) Settings has a Hotkeys list: every key the app listens for in one place, editable, clashes in red.
  2.0 beta 8
       (1) Chat commands are sent the way Sidekick sends them: the command goes on the clipboard and one quick burst
           of keys opens chat, clears it, pastes and sends. Nothing is typed letter by letter, so chat only flashes.
           Your clipboard is put back right after, and the app doesn't mistake either for a copy of yours.
       (2) Version numbers: every build gets its own number from now on (the earlier "beta 7" kits were several builds).
  2.0 beta 7  (the toolkit desktop)
       (1) The app is now a small desktop: every tool opens in its own window inside the app. Drag a window by its
           title bar, resize it from the corner, minimise it to the taskbar, maximise it (or double-click the title),
           close it. Resize from any edge or corner, like a normal window. Several can be open side by side; the one in front has the orange line under its title.
           Which windows are open, and where, is remembered.
             - Dock (left): the orb opens the Toolkit menu; a desktop-style icon with its name for every module
               (Price checks, Wealth, Mod book, Item library, Regex) and utility (Chat commands, Notes, Delirium, with
               a dot that is green while it is on); an orange edge = its window is open; the gear opens Settings.
             - Toolkit menu: search box (type a few letters + Enter), every module and utility, Settings,
               Check for updates, Quit.
             - Taskbar: a button per open window (click = bring it forward, click again = minimise), the league
               (click = Settings), the utilities' on/off dots, 📌 always on top, the clock.
             - Wallpaper: a dark gradient, or any picture you pick in Settings. Desktop icons are optional (Settings).
       (2) No more header or League / Pace bars across every page: the price-check toolbar, the total and the key
           bar live in the Price checks window only. League and Pace (and always on top, exchange rates, updates)
           are in the Settings window.
       (3) Chat commands and Notes are two separate utilities, each with its own window and its own On switch
           (your old setting turns both on, as before).
       (4) The Delirium alert is built in: no second exe. It runs next to the app as a helper process (the same
           StashOfExile2.exe started with --delirium), so its screen watching never slows the app. Its window has
           Start / Stop / Test alert, Move the splinter / Reset its position, sound, the on-screen splinter, start
           with the app, and shows what it sees (watching / waiting for the game / Delirium active / ALERT). Its log
           and settings are in your data folder, under delirium. (The standalone PoE2DeliriumAlert.exe still works,
           but not at the same time.)
       (5) Notes: the note itself only has its × now; every option is in the Notes window: key, colours, opacity,
           font size, and new: its place and size typed in, Lock it (no moving / resizing by accident), Reset place and
           size. The note resizes from any edge or corner. (Fixed: a note shown and saved straight away could be stored
           as 1x1 pixels.)
       (6) Updates (Settings): "Check for updates when the app starts" (tells you, asks first) and "Install updates
           automatically when the app starts" (no questions; it restarts itself). Both are off unless you turn them
           on, and they stay as you set them. Up to date or offline = only a quiet line in the status bar.
       (7) The dock's Toolkit button is the app's own icon; optional desktop icons look like the dock's tiles.
       (8) Wealth, redesigned (ideas from Wealthy Exile, not a copy): a Wealth card (total, change, Total / Daily
           chart over 24 hours / 7 days / 30 days / Lifetime), a Breakdown card (value per category, in divines or
           percent; click one to show only those items), your tabs down the side as coloured buttons (click one to
           show only that tab) or your Snapshots, and every item with Name / Tab / Quantity / Price / Total. Sync,
           Stop and "Synced 8 minutes ago" sit above the list; Update prices and Re-check rares are under More.
           Setting up priced tabs is behind "Edit synced tabs".
       (9) Currency counted by hand: with the Wealth window in front, copy a stack in game (plain Ctrl+C) and it is
           added to "Counted by hand"; the same currency again asks Add / Replace / type an amount. "Count currency"
           counts a whole tab: copy every stack (from any window), stacks of the same currency add up, Undo last,
           Finish replaces the amounts you copied and keeps the rest. More > Add currency by hand to type one in.
           Double-click a counted quantity to change it, Delete removes it. A stack copied on Price checks offers
           "Add it to Wealth".
      (10) Mod book: its three pages are real buttons now. Listing mod lines the trade site's list doesn't word the same
           way are matched through the item library's wordings too (the Mod book showed 0 readable mods), and when
           lines still can't be read, a few examples show right on the page.
      (11) Fixed: Wealth found only Divine, Chaos and Exalted on poe.ninja. poe.ninja puts every item's name in a list
           the app wasn't reading (only the three core currencies were named), so Mirror of Kalandra, Hinekora's Lock,
           essences, omens, runes ... all said "not on poe.ninja". Now read the way Sidekick reads it, with the
           poe.ninja id as a fallback. The old price cache is thrown away once so everything is fetched fresh.
      (12) Exchange rates are its own utility (dock, Toolkit menu, taskbar dot), with currency names, and rates are
           converted from poe.ninja's main currency when that isn't the Divine Orb.
      (13) Sync with no priced tabs but counted currency just updates prices (no more "add your priced tab first").
      (14) Under the hood: soe2/shell.py (the desktop) and soe2/modules/ (one small file per module / utility,
           so new tools can be added on their own).
  2.0 beta 6
       (1) New Utilities page, a card per helper, each turned on separately and running on every page:
           - Chat commands & notes: the POE2 Overlay (AutoHotkey) rebuilt in the app. A key types /hideout (F1), up
             to 8 more keys type your own chat commands; they only act while Path of Exile 2 is the active window.
             F6 shows / hides an always-on-top sticky note (drag, resize, colours, opacity, font size; it saves
             itself and hides while the game is closed). Your POE2 Overlay settings are read in the first time.
           - Delirium alert: the END DELIRIUM screen watcher, as its own program PoE2DeliriumAlert.exe (built by
             build_exe.bat next to StashOfExile2.exe; it needs OpenCV, so it stays out of the app's exe). Start /
             Stop / Test alert, start it with the app, sound on or off.
       (2) Built-in jewel rules: 46 High jewel mods in default_rules.json, next to the 20 tablet ones.
       (3) The updater picks StashOfExile2.exe from a release even when PoE2DeliriumAlert.exe is attached too.
       (4) Gear price checks no longer use the tablet / jewel mod rules (a jewel rule like "increased Critical Damage
           Bonus" was making that mod a must-have on gloves). Gear rules of your own come with Phase 4.
  2.0 beta 5
       (1) Regex: much shorter strings, written the way poe2.re writes them. Any digit after the first is '.',
           waystone properties use short cues (drop chance 120+ = "p c.*([2-9]..|1[2-9].)%"), tiers are compact
           ("er 1[4-6]\\)"). Every pattern was checked against every value from 0 to 999.
       (2) Built-in tablet rules: default_rules.json ships with the app with 20 High tablet mods (Hiveblood,
           Wombgifts, the Ritual reroll / omen / tribute mods, Abyss mods, additional random modifiers ...). Anyone who
           hasn't marked a mod themselves gets these; your own marks in Mod book > Tablet mod rules always win.
  2.0 beta 4  (finishes Phase 3, the gear price checker)
       Wealth: magic and rare items from your tabs are now price-checked, with the same checkers as Ctrl+Alt+C
       (tablets and jewels by their mods, gear by its totals and mods, used tablets by their uses left). It runs in
       the background after each sync, one item at a time, always behind anything you copy yourself (F2 pauses it,
       Stop stops it). Only new or changed items, or prices older than 3 days, are checked again, the dearest first.
       "Re-check rares" does it on demand. The net worth includes them; "Priced by" says "price check (High)" etc.,
       or why an item has no price (waiting, no matching listings, check by hand).
  2.0 beta 3
       Price checks: a filter row above the list. Show (moved down from the toolbar), then Category (Tablets,
       Jewels, Rings, Gloves ... with how many of each are in the list), Rarity (Unique / Rare / Magic / Normal) and
       Type (tablet type such as Ritual or Temple, the jewel, or the base type). Each box only offers what is in your
       list. "Show all" clears them; the total valuation and the Priced / Review counts follow what is shown.
       A newly copied item that the filter would hide switches the list back to all items, so it never vanishes.
  2.0 beta 2
       (1) The Mod book page now holds your mod rules too: tabs "What the app learned", "Tablet mod rules" and
           "Jewel mod rules" (the two rules pages are gone from the Page list).
       (2) Mod book "Single mods" / "Mod priority" stayed empty: the listings behind them weren't being saved with
           their mods. The app now counts what happens to every listing it fetches and says why one wasn't usable
           (no exchange rate, no mod text, mod wording not on the trade site's list), on the empty Mod book and in
           market_log.txt in the data folder. Listing lines worded differently from the trade site ("reduced" for a
           negative "increased", "3 additional times" for "an additional time") are now recognised.
  2.0 beta 1  (was going to be 1.46)
       (1) New version numbering (see above). The launcher is now always called stashofexile2.py.
       (2) Regex page laid out like poe2.re: the search string on top (Copy, Reset, Test on copied item), option
           cards (tablets: rarity, type, min. uses; waystones: item rarity / pack size / monster rarity /
           effectiveness / drop chance, tier and revives, rarity, corrupted or not; relics: rarity and size), and
           two mod lists: "I want these mods" (Match any / all, with a box for "at least") and "I don't want any of
           these mods". Click a mod to select it. "Round down to nearest 10" makes the string much shorter.
           Waystones: the Delirious option is gone (removed from the game). Tablets: Irradiated Tablet (the generic
           one) instead of "Precursor".
  ---- 1.33 to 1.45: test builds on the way to 2.0 ----
  1.45 (1) The price-check toolbar (Valuable mod, Popups, Pause, Clear list, Listings, Mark listed, Re-price all ...) and
       the list's total valuation only show on the Price checks page. Other pages get one slim row with League and
       Pace, which they share. The key bar at the bottom stays: Ctrl+Alt+C works from every page.
       (2) Used tablets: the search is still for full 10-use tablets, and the price is scaled by the uses left
       (5 of 10 uses = 50% of the 10-use price). The side panel and the "How it was priced" column say so.
  1.44 New Regex page: stash-search strings for Tablets, Waystones and Relics (like poe2.re, built into the app).
       Tick the mods you want (any or all of them) and the ones to avoid, set "at least" values, plus tablet types and
       uses, waystone tier / item rarity / drop chance / pack size / monster rarity / effectiveness / delirious, relic
       sizes, corrupted or not. It shows the string and its length (the game takes 250 characters), copies it,
       saves presets, and can test the search on a copied item (and tick the mods that item has).
       Mod lists come from the game's own data (RePoE, regexdata.json); the strings are generated by the app.
  1.43 Ritual Tablets: "Ritual Altars in Map allow rerolling Favours # additional times" now counts in the price.
       The trade site words that mod "an additional time" (no number), and listings with 2 or 3 rerolls show
       "3 additional times" - the listing check didn't accept that wording and threw those listings out. Both
       wordings are accepted now, and the mod is searched the way the trade site's own search does it (its own
       "at least 1" group, no value). Same for every other "an additional ..." count mod.
  1.42 Fixes. (1) The minimize button works again with Always on top on (the check for "did you minimize it?"
       looked for the mouse on the title bar after Windows had already moved the window off screen). Also: minimizing
       again right after the app brought the window back always sticks.
       (2) Gear searches the trade site refused (400): only stat ids on the trade site's own list are used, a refused
       search is tried once more in its simplest form, and the trade site's own reason is shown instead of a URL.
       (3) Tablets: any wording of the tablet class is accepted; unique tablets and jewels are priced by name; a
       white tablet says it has no mods; anything else not priced is saved to unpriced_items.txt in the data folder.
  1.41 Gear price checker (Phase 3). Ctrl+Alt+C on any piece of gear (rings, amulets, belts, gloves, boots, helmets,
       body armours, shields, foci, quivers, weapons, charms, flasks) now prices it, on the Price checks page like a
       tablet. The Item library's "Check an item" box has a Price check button that does the same.
       - Armour pieces are searched on their total Armour / Evasion / Energy Shield (at 20% quality, or their own
         quality if higher), weapons on their physical / elemental DPS; the mods that feed those totals are left out.
       - Rings, amulets, belts, quivers, charms and flasks are searched by their exact base type.
       - Two or more resistance / attribute / life mods are searched as one total (the trade site's pseudo stats).
       - Uniques are searched by name. Corrupted only against corrupted, uncorrupted against uncorrupted.
         Exceptional socket counts (2 on gloves / boots / helmets, 3 on body armours) are required.
       - The side panel shows the totals and every mod: star = must match, tick = counts, untick = not searched,
         and Min / Max values can be edited, as for tablets. If the exact search finds too few listings, one, then
         two ticked mods may be left out (at most 3 searches per item).
  1.40 (1) The Items page is now called "Price checks" (same page, same features).
       (2) Item library: a line it doesn't know is looked up on the trade site's own stat list (downloaded daily) and
           remembered (learned_stats.json in the data folder), so it is known from then on. Only exact matches are
           learned. Nothing asks you to report anything any more.
       (3) Lines that describe the whole item ("Fractured Item", "Mirrored", "Unidentified" ...) are read as the item's
           flags, not as unknown mods. Fractured, desecrated and crafted mods get their own trade-site stat ids
           (the search needs those), and jewel sockets (S J) are told apart from normal ones.
       (4) The Item library says what it is for at the top.
  1.39 Copying gear (gloves, rings, weapons ...) with Ctrl+Alt+C no longer looks like nothing happened. The price
       checker still only prices tablets and jewels (gear comes with the gear price checker, Phase 3), but now the
       status line says so, names the item, and puts it on the Item library page (Check an item) so you can see how
       the app reads it.
  1.38 Phase 2 of the plan: the game-data library. New page "Item library" (Page dropdown):
       (1) Every PoE 2 base type (1,574) sorted by class and base group: body armours / helmets / gloves / boots /
           shields / foci by defence type (Energy Shield only, Armour / Evasion ...), rings / amulets / belts / jewels /
           charms one group per base (Breach Ring and Refined Breach Ring together; Runeforged / Runemastered versions
           with their base), weapons by class (bows, wands, quarterstaves ...), with each base's defence values.
       (2) Every modifier stat (2,518): its wording, whether higher is better, its trade-site stat ids, local or not.
       (3) Check an item: paste any copied item (Ctrl+C) and see how the app reads it: class, base, base group,
           quality, defences, sockets, item level, corrupted, and every mod with its tier, roll range and trade stat.
           Lines it can't place are shown in red.
       The data comes from Exiled Exchange 2 (MIT licence, see THIRD_PARTY_NOTICES.txt) and ships as gamedata.json,
       versioned like tabs.txt. tools/build_gamedata.py rebuilds it after a patch. This is the base the gear price
       checker (Phase 3) and the Ctrl+C currency sweep will use. Nothing else changes, except: the Wealth page now
       says honestly that poe.ninja prices currency, stackables and uniques, and that rares need the gear checker.
  1.37 Behind the scenes only: nothing you can see or use has changed. The code (one 6,000-line file) is split into
       a package, soe2/, with one module per part: config, net (rate limiter), rates, mods, trade, market, engine,
       wealth, the pages and the window. Every line of the old code is unchanged apart from the few the split
       needed. This is Phase 1 of the plan: the base for the gear price checker and the mod library.
       (1) tabs.txt and jewels.txt now have version numbers inside the app. A newer copy in a future version
           replaces the one in your data folder (the old one is kept as .bak); until now an old copy stayed forever.
       (2) Updates: running from source (not the exe) now takes the build kit .zip from GitHub, since the app is
           more than one file. The exe updates itself exactly as before.
  1.36 Wealth page: a price you typed counts even if you didn't press Add tab. Sync tabs adds whatever is in the Price
       box (or the trade-link box) first, then syncs. The Price box also understands "37882 div", "37882 divine" and the
       game's own tab name "~price 37882 divine" (the currency in the text wins over the dropdown), and a trade link
       pasted there works too. The same goes for the Name box if the price was typed there by mistake.
  1.35 (1) Always on top: the window stays in front of other windows (button "Always on top" in the header, next to
           Exchange rates; on by default). It also no
           longer gets minimized behind your back: if Windows minimizes it without you pressing Esc, clicking its
           minimize button / taskbar button or using a Win-key shortcut, it comes straight back (without taking the
           keyboard away from the game). With the box off, everything behaves as before.
       (2) Mark listed / Mark removed work as on/off switches: press them on an item that is already listed (or removed)
           to put it back to "not listed". Ctrl+Z (or the Undo button) undoes the last mark, even when the item has
           already disappeared from the list because of the Show filter.
       (3) Ctrl+A selects every item in the list. Del does the same as "Clear list" (it still asks first).
       (4) Min uses is always 10 for tablets: the dropdown is gone.
       (5) Your own mod values, like Sidekick: every mod in the side panel has Min and Max boxes, filled with what the
           search uses (your roll x 0.9 by default). Change them and press Enter or "Search with these values" to
           price the item again with them; "reset" puts a mod back to the automatic value.
  1.34 Fix: the shortcut bar and "Check for updates" button at the bottom disappeared in 1.33 (on every page), because
       the Wealth page asked for more height than the window had. The bottom bar now always keeps its place.
       Wealth page, clearer setup. (1) "Tab markers" are now "Your priced tabs": the price you put on the whole tab in
       game (e.g. 37882 Divine Orbs). Type that price and press Add tab, or paste a trade-site link that searches
       for it ("Add from link" reads the price, your account and the league out of the link). The name is optional:
       it defaults to "~price 37882 divine", the name the game gives the tab. (2) Mistakes are explained on the
       page itself (not only in the status line at the bottom), and pressing Sync with no priced tab says exactly
       what to do. (3) Your listings count as yours whether the trade site writes your account with or without #1234.
  1.33 New "Wealth" page (Page dropdown): your net worth in the league, like WealthyExile for PoE 1.
       PoE 2 has no stash API tools may use, so the page reads your stash through the trade site: set a public Premium
       stash tab to a tab-wide price nobody would pay (e.g. 37916 Vaal Orbs, a different amount per tab) and add that
       price as a "tab marker". Sync tabs then searches the trade site for your account's listings at exactly that price,
       reads the items 10 at a time, and values them with poe.ninja (currency, essences, omens, runes, soul cores, uncut
       gems, uniques...). Rares need your own price: double-click one. Each sync adds a point to the history chart.
       (1) It shares this app's rate limiter and background worker, at a LOWER priority than item pricing: copy an item
           mid-sync and it is priced first. Nothing ever runs two requests at once.
       (2) A tab with more than 100 items (the most one search returns) is searched again in slices: category, then
           sub-category, rarity and item level. Big tabs take a while at the safe pace; the page shows progress, and
           Stop keeps the last complete data.
       (3) Listings without the exact marker price, or on another account, are thrown out. A tab whose sync fails keeps
           the items from its last good sync.
       (4) poe.ninja prices for the page are fetched at most hourly with ETags (wealth_prices.json). Your markers, items,
           prices and history live in wealth.json in the data folder.
       Never use a Merchant's Tab as a marker tab: those sell instantly, even while you're offline.
  1.32 The "Same item again?" question is now a banner inside the app window (above the list) instead of a card drawn over
       the game; the taskbar button flashes and a sound plays when it appears. Its button says "Different jewel" or
       "Different tablet" to match the item.
  1.31 Jewels get their own rules page. The "Mod rules" page is now two pages, "Tablet mod rules" and "Jewel mod rules"
       (fed by jewels.txt, the jewel mod list). Both work the same: High / Normal / Ignore, learned priority,
       Export rules / Import rules / Remove imported (each acts on the page you are on). Your existing rules carry
       over unchanged. The Mod book page now says WHY it is empty (database problem, nothing recorded yet, or the last
       recording error) instead of a generic message.
  1.30 A little empty space under the bottom key bar.
  1.29 "Check for updates" button (bottom bar, right). Click it: the app asks GitHub (github.com/tiwomm/StashOfExile2,
       Releases) for the newest version, tells you if there is one, shows what is new, and asks whether to download it.
       Yes = it downloads the new exe, checks it against GitHub's checksum, closes, swaps itself and starts again.
       Your settings, rules and market data stay (they live in a separate folder). Nothing is checked or downloaded
       until you click.
  1.28 Trade-site errors now say the full request (method + whole address + what the server answered) and are also written
       to http_error_log.txt, because a "405 Method Not Allowed" gave too little to find the cause. Redirects are followed
       with the same method (a redirect used to turn the search POST into a GET, which the site answers with 405).
  1.27 Export rules / Import rules (Mod rules page). Export writes your high-priority mods (your own rules plus what your
       app learned) to a file. Import reads friends' files: a mod they share counts as High only if you set nothing
       yourself, your own data does not contradict it, and it is a real mod. Imported votes sit in community_rules.json
       and can be removed with "Remove imported". Setting "community_min" in settings.json = how many different people
       must share a mod (default 1).
  1.26 Fixes. (1) The shortcut keys (C, O, F2, Esc) did nothing on Windows whenever Num Lock was on: the app mistook Num
       Lock for the Alt key. (2) The Exchange rates window now has an "Exchange rates" button next to the Page dropdown
       (it was only reachable by clicking the small "Rates: ..." text at the bottom).
  1.25 Exchange rates (Vaal Orbs and every other currency listings are priced in).
       (1) The rates are refreshed once an hour in the background from poe.ninja's public exchange overview (the same
           data its Economy page shows; PoE 2 only updates about hourly there, so more often would gain nothing). It sends
           the saved ETag so "nothing new" costs them almost nothing, and one request covers every currency.
       (2) Footer shows how old the rates are; click it for the Exchange rates window: every currency's worth, how much of
           it traded, a "Refresh now" button, an hourly on/off switch, and a converter ("what is 8.5 div in chaos, exalted,
           vaal?").
       (3) The side panel has "IF YOU LIST IT": the price in chaos / exalted / vaal and the two whole-divine neighbours
           ("8 div (-6%) or 9 div (+6%)") plus a divine + chaos split. "Listed at" now understands "8 div 50 chaos" and
           "150 vaal".
       (4) A listing priced in a currency with NO known rate used to be left out of the average without a word. It is still
           left out (guessing would be worse), but the row now says so, confidence drops, and currency_log.txt records
           the currency's name so it can be added.
       (5) Fixed: when one listing couldn't be converted, the next listings in market.db could get its neighbour's price.
  1.24 New look (Xfire-style steel and navy, with the game's gold for money) and the Mod book merged into one page.
       (1) Glossy header with the total valuation, a "Priced" chip and a "Require Review" chip; raised steel buttons;
           blue selection bar in the list; the side panel is cards (estimated value + confidence badge, a warning box
           with the reasons, one card per search step, the mods). Every button and option is still there.
       (2) Shortcut bar at the bottom, drawn as keys (click one to use it): Ctrl+Alt+C adds an item (works from inside the
           game, as before), and while THIS window is focused: C copies the selected item's name, O opens its trade
           search, F2 pauses / resumes searching, Esc minimizes (to the tray if it's on). They are ignored while you type
           in a box, and never reach the game.
       (3) The old Mod book page is gone. It searched every mod on its own in the background, which used up searches the
           real pricing needed, so it stayed nearly empty. "Mod book" is now the page that learns from the listings the app
           has already fetched (no extra searches): Mod priority, Single mods, Mod combinations, and "Old mod book" (your old
           list, kept as it was). Mods the old book found valuable carry on as learned High.
       (4) The "Learn mods" checkbox is gone (there is no background learning to switch off).
       (5) Dropdowns hand the keyboard back to the window after you pick something, so the shortcut keys keep working.
  1.23 The local learning model (free: plain Python, no outside service, nothing to pay for).
       (1) Mods that keep showing up in the dearer listings are promoted to High on their own ("learned priority"), and the
           Mod rules page shows a Learned column next to your own mark. Your own rule always wins.
       (2) New Market memory view "Mod priority": your mark vs what the data says, with a plain Check column
           (agree / you ignore something that looks valuable / data doesn't back your High yet).
       (3) Comparables: stored listings carrying the same mods at your rolls are shown next to the price as a hint
           (never as the price).
       (4) Accuracy score: before each price is finalised the model guesses it from stored listings, then the real search
           answers; the hit rate is shown on the Market memory page. The model may only set a price after 100 checked
           guesses at 99 percent (setting "model_shortcut", OFF by default, and 1 in 10 are still searched for real).
       (5) The "Listed at" prices you type are now saved (table "listed" in market.db) and shown as a hint on similar items.
       (6) New league: market data is tagged by league, so prices start fresh; the learned list of valuable mods is
           carried over (and the mod book re-checks each mod). The app asks yes/no the first time it sees a new league.
       (7) The column header "Conf." is now "Confidence".
  1.22 (1) The list now runs oldest at the TOP and each new item is added BENEATH the previous ones (it was newest on top).
       (2) New page "Market memory" (Page dropdown): what the app has learned - mod combinations with the cheapest asking
       price they ever showed, and single mods with the asking prices of every listing seen.
  1.21 Listings are now CHECKED and REMEMBERED.
       (1) Every listing the app fetches comes with its real mods: listings that don't actually carry the mods that were
           searched are thrown out (and if EVERY listing fails the check, the app assumes its own reader is wrong, keeps
           them, lowers confidence and writes verify_log.txt so it can be fixed).
       (2) New "Confidence" column - High / Medium / Low - and the reasons in the side panel (few listings, wide spread, loosened
           search, old listings, ...).
       (3) Market memory (market.db in the data folder): every search and every listing it saw is stored. Before pricing,
           the app looks for earlier searches whose mods this item also has; if its new price is far below what those
           found, it warns. Setting "memory_shortcut" (default false) lets it skip searching when 5+ identical searches
           in the last 24 h agree within 10 percent - off by default, memory never sets a price on its own otherwise.
  1.20 Same-wording mods: the trade site lists some mods TWICE with identical wording but different ids (e.g. "Map contains
       an additional Shrine"). The app only knew the first one, so it missed every listing that carries the other. It now
       remembers all of them and searches "at least 1 of these" (exactly what Sidekick does). Needs a fresh download of
       the trade site's mod list on first start (automatic).
  1.19 Ready for the .exe: files packed INSIDE the exe (tabs.txt) are copied into the data folder on first start, so a
       brand-new user needs nothing else. Added build_exe.bat (one double-click builds StashOfExile2.exe).
  1.18 (1) Only YOUR Ctrl+Alt+C counts: the app now sees your real key presses (a Windows keyboard hook, which can tell
       keys you pressed from keys another program sent) and ignores item copies made by Sidekick's Ctrl+D etc.
       Toolbar box "Ctrl+Alt+C only" turns this off. (2) Duplicate check by exact name + exact mods (not by the raw copied
       text): a small always-on-top card asks "same item - skip" or "different tablet - add it".
  1.17 Safety check: if two different mods on one item end up on the SAME trade-site stat (the Azmeri Spirit mix-up
       was exactly this), nothing is searched and the row says CHECK BY HAND with the reason, instead of a wrong price.
  1.16 Fix for 'Map contains N additional ...' mods that exist twice (e.g. Azmeri Spirit as a PREFIX with a fixed 1, and as
       a SUFFIX that rolls 1-2). The trade site has two different stats for them ("an additional X" = the fixed one,
       "# additional X" = the one with a roll) and the app used to swap them. It now looks at whether the mod shows a
       roll range in brackets: no range = fixed = "an additional X"; range = "# additional X" with your roll as the
       minimum. NEW last-resort search: if nothing at all is found with your rolls (about 90 percent of them), it searches
       once more with ANY value, and shows the result as '>= price' with a note, because a high roll can be worth more.
  1.15 The Items / Mod book / Mod rules tab strip is gone. A "Page" dropdown in the header switches between
       them instead. Nothing else changed.
  1.14 Tabs (Items / Mod book / Mod rules) restyled: no more boxed grey outlines - flat dark tabs, the selected one is
       lifted with a gold top edge and gold text, hover brightens. The built-in icon now has a transparent background.
  1.13 Path of Exile look: warm near-black panels, gold accents and borders, serif title with the Mirror of Kalandra,
       gold buttons and tabs, in-game rarity colours (rare yellow, magic blue). Looks only - no behaviour changed.
  1.12 (1) Wide spread = no price: when the listings behind a price are 20x or more apart, the row shows CHECK BY HAND
       (red) with the lowest and highest price, instead of a number. (2) Clipboard watcher rebuilt: it now reads the
       Windows clipboard directly (not through Tkinter, which can keep a stale copy after the app writes an item name
       to the clipboard), retries when another program is holding it, restarts itself if it ever stalls, and the status
       line says what it did with every copy (added / already in the list / not an item / normal copy).
  1.11 Wide-spread warning. When the listings behind a price are wildly different (cheapest and dearest 20x apart or
       more, e.g. 1 chaos vs 100 div), the row now says so and shows the lowest and highest price, and the 'worth a look'
       pop-up is not shown, because a median of a handful of far-apart prices is not a real price. The number itself is
       unchanged (median of the cheapest 5 listings). Setting "spread_warn" in settings.json (default 20, 0 = off).
  1.10 Rate limits now survive a restart. Before, closing and reopening the app (or a crash) made it forget how many
       requests it had just sent and any 'wait 10 minutes' penalty, so it fired straight into an active penalty
       (the 429s on the league list at startup in your log). It now saves its request history and penalty clock to
       rate_state.json in the data folder and reloads them. The 429 log line also shows how many requests the app
       had sent in the last 5 minutes and since it started.
  1.9  Fix: after "Clear list", copying the SAME item again (Ctrl+Alt+C) was ignored, because the app only noticed the
       clipboard text CHANGING and the text was identical to the last one. It now watches Windows' own clipboard
       change counter, so every copy counts, even of identical text. "Clear list" also resets the duplicate memory and
       the batch counters. If a clipboard read fails (another program holds the clipboard) it retries instead of
       dropping the copy. The status line shows when the last copy was heard.
  1.8  Your data now lives in ONE fixed folder that never changes between versions or app locations:
       Windows: %APPDATA%/StashOfExile2   (type that into the File Explorer address bar to open it).
       On start the app copies in any data file it finds next to itself (tabs.txt, mod_rules.json, modbook.json,
       session.json, settings.json ...) when the data folder does not have that file yet - it never overwrites.
  1.7  App renamed to StashOfExile2 (file stashofexile2_v1.7.py). Mirror of Kalandra icon (built into the file) on the window
       and taskbar. Minimizing hides the window to the system tray (needs pystray + pillow; without them it minimizes
       normally). Tray icon: click or "Show" to bring it back, "Quit" to close. Clipboard watching and pricing keep
       running while it is in the tray. Setting "tray": false in settings.json turns this off.
  1.6  App renamed to ExileScout (file name exilescout_v1.6.py, window title, header). Data files keep their names, so your list, settings and mod book carry over.
  1.5  Jewels use the same ladder as tablets: search 1 = all affixes; if it finds too few listings, drop ONE affix at a time
       (every affix gets its turn, up to 4 extra searches) and average the searches that found listings.
       Tablets still never drop a suffix (only prefixes rotate). ALL searches for ALL items now use Corrupted = Any
       (Fractured and Desecrated were never filtered, so they are Any too).
  1.4  Jewel searches now use Corrupted = Any (before, an uncorrupted jewel searched only uncorrupted ones). Tablets still match the item.
  1.3  Shortcut: if search 1 (all mods) already finds enough listings (Min results, default 3), that is the price
       and the two prefix searches are skipped - 1 search + 1 fetch instead of 3 + 3. Tablets and jewels.
  1.2  New pricing flow for tablets AND jewels: search 1 = all mods, then one search per prefix (each with all suffixes),
       final price = plain average of those searches (a search that finds nothing is left out; nothing at all = NO MATCH).
       Max requests per 5 minutes (a cap below what the site reports, because real 429s came earlier). Fuller 429 log.
  1.1  App renamed to PoE2 Tablet + Jewel Pricer (window title, header, this text). No behaviour changes.
  1.0  First numbered version. Multi-pass tablet pricing with a weighted average and NO MATCH;
       Instant Buyout / listed-within / minimum-uses filters; per-mod impact (High / Normal /
       Ignore) with per-tablet tick boxes and a Mod rules tab fed by tabs.txt (with Prefix / Suffix);
       listed / removed tracking, saved between sessions; item name copied for stash search;
       "Priced at" timestamps; resizable panel and columns; rate-limit pacing with
       rate_limit_log.txt; error_log.txt; mod book explanation; singular-wording stat matching.

HOW TO USE
  1. Run:  py stashofexile2.py   (needs:  py -m pip install requests   - and, for the system tray:  py -m pip install pystray pillow)
  2. Pick your league at the top.
  3. In game hover an item and press Ctrl+Alt+C. Do it as fast as you like.
     Each item appears in the list straight away and gets priced in the background.
  4. Click a row to see its mods, roll quality and listings.

PRICING (how a tablet or jewel is priced)
  Every mod has an impact: High, Normal or Ignore (pack size, gold, experience...). Ignored mods are
  never searched. Tick / untick or star a mod on an item to change it for that item only; the
  Mod rules tab (fed by tabs.txt) sets it for every item.
  Search 1: every affix that counts. If it finds enough listings (default 3) that is the price and the item is done.
  Otherwise (tablets: one search per prefix with all suffixes; jewels: leave one affix out at a time, each affix in turn):
  one search per prefix, each together with ALL the suffixes (best 2 prefixes).  The price is the plain
  average of those searches (each search = median of its cheapest 5 listings). A search that finds
  nothing is left out of the average. No search finds anything = NO MATCH (no guessed price).
  Only Instant Buyout listings from the last 1-2 days with enough uses remaining (default 10) count.

TRACKING
  Click a row: its name is copied (paste it into the stash search with Ctrl+F). Under the mods
  press "Mark listed" once you've listed it, or "Mark removed" if you reforged / changed it.
  The list is saved between sessions (session.json).

THE "LEARNING" PART
  Every mod on every item you copy gets looked up once on the trade site: "what is the
  cheapest you can buy this mod for on this base type?". That goes into the Mod book tab.
  Mods whose cheapest listing is above your threshold are marked with a star, and you get
  a small popup the moment you copy an item that has one.
  (The game only reports an item when you copy it, so the popup appears on Ctrl+Alt+C,
  not on hover.)
"""
# Start the app. The code lives in the soe2 folder next to this file (one module per part of the program);
# this file only checks that the two belong together and starts it.
import os
import sys

APP_VERSION = "2.8.1"  # bump this and __version__ in soe2/__init__.py together (see VERSION above)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if "--restarted" in sys.argv:                                 # 2.0.0: the app restarted itself (Appearance changes)
        sys.argv.remove("--restarted")
        import time
        time.sleep(1.2)                                           # let the old window save and close first
    if len(sys.argv) > 1 and sys.argv[1] == "--delirium":       # 2.0 beta 7: the Delirium alert helper (started by the app)
        from soe2.delirium_runner import main as delirium
        sys.exit(delirium(sys.argv[2:]))
    try:
        import soe2
        from soe2 import config
    except ImportError as e:
        _fail(f"The soe2 folder is missing next to this file ({e}).\n\nKeep this file and the soe2 folder together.")
        return
    if config.APP_VERSION != APP_VERSION or soe2.__version__ != APP_VERSION:
        _fail(f"This launcher is version {APP_VERSION}, but the soe2 folder next to it is version {config.APP_VERSION}.\n\n"
              "Use the launcher that came with that folder (or the folder that came with this launcher).")
        return
    from soe2.app import main as run
    run()


def _fail(msg):
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror("StashOfExile2", msg)
        r.destroy()
    except Exception:
        print(msg)


if __name__ == "__main__":
    main()
