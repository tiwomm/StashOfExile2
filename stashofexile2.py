"""
StashOfExile2 - a Path of Exile 2 price checker for tablets and jewels, with a window instead of a text dump.
Free software under the GNU AGPL v3.0 (see LICENSE; up to 2.129.4: GNU GPL v3.0). Written by an AI (Claude, by Anthropic) under a human's direction.

VERSION 2.134.1
  How versions are numbered (from 2.0.0 on):
    MAJOR.MINOR.PATCH.  The 22 betas ended here: this build is 2.0.0. From now on every build gets a plain number:
      2.0.1, 2.0.2 ...  fixes (nothing new to learn)
      2.1.0, 2.2.0 ...  new features or changes you'll notice
      3.0.0             another big change
    Only when a bigger version needs testing first does it get a short run of release candidates (2.1.0-rc.1, -rc.2,
    shown as "2.1.0 RC 1"), never long beta numbers again. Always written in full (2.10.0). This is Semantic
    Versioning 2.0.0; py tools/check_version.py checks every place agrees before a release. Older names still sort right: 2.0 beta 22 < 2.0 RC 1 < 2.0.
    "Check for updates" only ever offers a version newer than the one running (updates.is_newer).
  The test builds 1.33 to 1.45 were all on the way to 2.0; their notes are kept below.
  The app is this launcher (always called stashofexile2.py) plus the soe2 folder next to it. The version is in two
  places that must match: APP_VERSION below and __version__ in soe2/__init__.py; the launcher refuses to start a
  soe2 folder from another version. Your data never lives here: it is in %APPDATA%/StashOfExile2, shared by every
  version (settings.json, session.json, modbook.json, mod_rules.json, wealth.json, tabs.txt ...).

VERSION HISTORY
  2.134.1
       - Update question (feedback: "why give a virustotal link if a person can't click it? I don't think we need that
         in the update available screen"): plain_notes leaves out the release page's "Check your download" block (the
         SHA-256s and the VirusTotal link stay on GitHub; the app checks the download's checksum itself).
  2.134.0
       - Music Controls (BETA) (feedback: "music controls as an in-game overlay ... a toggle on/off small overlay that
         can be moved around ... independent of the main overlay bar/panel ... follow your chosen style"): ⏮ ⏯ ⏭ in a
         small window of its own (music_page.py), dragged anywhere, held by the overlay's lock, in the overlay's style,
         never takes the keyboard. Its switch: Overlay Settings › Helpers › PLAY (and Quick settings). Windows: the
         app's own window hands Windows the media app command (WM_APPCOMMAND via DefWindowProc) - no key is sent, the
         game never sees it (TOS.md 6). Linux: playerctl. Feature Picker: a BETA feature.
  2.133.1
       - Theme change freeze (feedback: "Hollow deep is still causing crashes"; hang report: 12 s+ in
         set_click_through's update_idletasks during "overlay rebuild"): the overlay's window styles, its right-side
         placement and the keep-on-screen check no longer force pending layout jobs (update_idletasks runs them until
         none are left). They wait for idle; a window without its frame yet is tried again every 50 ms, up to 1 s.
  2.133.0
       - Community pool, every item (feedback: "All items should be pooled, gear included"): gear, uniques (by name),
         waystones and the fallback searches now go to market.db's pool table and up with the hourly summary as
         "pool:<base>" rows (Community data sharing only, same summary: listings + middle price per mod). Kept apart:
         the Mod book, Insights and learned Highs never read them; the board leaves them out of /mods/stats.
       - About (feedback: "An active user count would be nice"): "Community: N installs share data · M active this week"
         from the hourly sync (/mods/stats "active" = contributors with a batch in the last 7 days). Sharing installs only.
  2.132.8
       - Releases (feedback: "virustotal link and checksums"): SHA256SUMS.txt with each release, the SHA-256 in the
         notes, and the exe sent to VirusTotal (repo secret VT_API_KEY) for a scan link. tools/release_notes.py --sha / --vt.
  2.132.7
       - Regex keys simplified (feedback: "All I wanted was the ability to add keybinds to 1-4 favorite regex buttons
         that when pressed would copy its regex to clipboard"): up to 4, one favorite each; a press copies it. Favorites
         ⌨ Key… opens Settings › Keybinds on its row, waiting for the key. The Regex key window and type_search are gone.
  2.132.6
       - Regex keys (plan, mockup approved): up to 6 keys, each with 1-4 Regex favorites; in game a press types the
         next one in the open stash's search (overlay.type_search: Ctrl+V; your clipboard put back).
         ⌨ Key… on Favorites; each key in Settings › Keybinds › Regex. The old single key that copied became Regex
         key 1 (migrations).
       - Shared searches (feedback: "publish their regex to the database, as well as favorites from the trade site"):
         Regex › ★ Favorites and Price Checks › Favorites have Official | Community | Mine, Post, Upvote, Tags…,
         Add to Mine (share_page.py; board kinds "regex" and "trade" - a trade search keeps only its filters, the
         account filter is dropped on the board).
       - Lucrative Strats (feedback: "multiple copies of the same thing"): Official | Community | Mine, each copy
         once; Type & tags on yours.
       - Ritual Identifier / Temple Helper (feedback: "I need it to just read as I'm potentially running past it";
         "it currently only tracks the first crystal encounter and then stops"): the whole game is read each second
         (hover_page.SCREEN); a failed picture (the mouse on another monitor made a negative box) left the look busy
         for good - now caught. Each map's altars get their cards again.
       - The Helpers line says HELPERS (was RITUAL / TEMPLE / IN MAP); no ◆ before Crystals.
       - Temple is a row under Helpers › IN MAPS, after Expedition.
       - The map's name is never on the overlay (feedback; still known for the rank and the logs); Avg and Maps
         leave a full overlay before Map profit. "On the bar" says "On the overlay".
       - Map Profit is a page, Overlay ↳ Map Profit (while it's on): All Time / Daily / Hourly, bars, Delete, Clear
         all (Undo). Items a covered look sees after the last clear one count toward what you went in with (an omen
         moved from your stash isn't profit). Items it can't recognize: a hint, and the Top Up key teaches them
         (with Top Up off too). The app's own log showed every map since had 30-50 unknown cells.
  2.132.5
       - Shorter text (feedback: "nobody needs to know that ... unnecessary unprofessional filler"): the helpers' lines
         and tooltips (one line each now - HELPER_BLURBS is the tooltip too), statuses, the Ritual filter, Favours,
         Break reminders, Temple, Top Up, Map profit, Wealth, the mod list download and the community name, in the
         user's own words. The Ritual filter keeps its credit (RF.CREDIT).
  2.132.4
       - Overlay ↳ Settings is Overlay ↳ Overlay Settings (feedback); the button on the Overlay page says so too.
         Settings › Appearance's "Overlay settings" section is "Overlay" (one name each). Keybinds' "Overlays" group
         is "Overlay".
       - Ritual Identifier (feedback: "should be part of the Ritual Helper that can be toggled on/off"): a chip on the
         Ritual helper's row (ritual_alert.identify, on with it); its own row, Quick settings chip and BETA feature
         are gone (migrations: ritual_id cleared).
       - Temple Helper (feedback: "says Crystals ? without even having temple in the map"): the crystals show once
         Map Content has the Temple icon (templates/temple_content.png; 0.999+ there, 0.72 at most without).
  2.132.3
       - Ritual Identifier (BETA; feedback: "build ritual identifier"): hover a Ritual Altar in a map, its tooltip's
         type ("Tainted Ritual Altar", or its danger line) -> an alert card: type, loot, danger (ritualid.py). One
         look round the mouse (hover_page.py) now feeds it and the Temple Helper.
       - What's new in keywords (feedback: "caveman mode this"): 2.131.5-2.132.2 and the 2.132.0 summary rewritten.
       - Check a flip lists every exchange item (cxnames loaded with a non-hub id).
  2.132.2
       - Map profit (feedback: "needs to account for inventory dumps if a player empties inventory and goes back into
         the map ... find a good idea for it"): counted visit by visit - each visit home adds what you came back with
         (the most of each item in the first ARRIVE_SECS of looks there, covered looks too: stashing / selling only
         lowers it, a later restock isn't counted) minus what you went in with (the last clear look before the map,
         seg_before). Emptying your inventory between visits isn't a loss.
       - Map profit is a BETA feature (feedback: "needs beta flagged"): features.BETA "mapprofit" (mp_on needs it;
         turning Map profit on turns it on), "Map profit (BETA)" in Helpers, its Quick settings chip only while on
         (BETA_HELPERS) - as the Desecration Helper.
       - Helpers (feedback: "desecration needs moved up under 'play' settings to be above campaign"): PLAY is
         Desecration, Campaign, League Plan; the last group is TRADING (Trade whispers).
       - Top Up (feedback: "chat window blocks currency for the top up and prompts me to restock everything"):
         _tu_hidden - an item you had is gone but its cells hold something it can't name: covered (Seen keeps the
         last clear look, no reminder).
       - Ritual line (feedback: "if a player doesn't interact with the first ritual, it should not enable ... only
         appear when you start the ritual mechanics"): ritual_readout says nothing at 0 of N (all done still shows).
       - BETA (feedback: "temple helper should also be marked beta, anything else helper-wise until it's fully tested
         and checklist approved should be marked beta. desecration helper can come out of beta"): features.BETA has
         Top Up Reminders, Break reminders, Map profit, Temple Helper ("was": a helper already on keeps its feature
         on); each helper's own switch turns its feature on (beta_on); Helpers say "(BETA)"; their Quick settings
         chips only while on. The Desecration Helper isn't BETA (its key leaves features).
       - The bar (feedback: "overlay text overlap ... cramming too much into the bar ... I don't really want to go any
         bigger"): parts that don't fit leave it - Map profit's, then Avg, then Maps (mg_dropped); the Temple Helper's
         crystals moved to the line above the bar with Ritual's (its tag RITUAL / TEMPLE / IN MAP).
       - Map profit (feedback: "why is it marking as -div if I didn't actually lose anything ... the arrow up/down can
         be removed. I just want a total of my profit per map"): a map's profit is what it gained - fewer of an item is
         never a loss (it was used, stashed or covered); no ▲ / ▼.
  2.132.1
       - Temple Helper (feedback: "show how many crystals I am currently at when running maps"; "a red text card too
         when crystals are full"; the Vaal Beacon tooltip "Energised Beacons: 55/60"): temple.py (parse, the region
         round the mouse, temple.json: only the two numbers) + temple_page.py - in a map, every 1.5 s, Windows OCR of
         that region; "◆ Crystals 55/60" on the bar (the "temple" part); full: a vital alert card once (again after
         they drop). Its row in Overlay ↳ Overlay Settings › Helpers (Test), a Quick settings chip; log_wanted counts it.
       - Map profit: its search box says Search (feedback: "wtf is this textbox for?"); no maps: "Session: no maps
         yet"; a Quick settings chip.
       - Map profit (feedback: "needs to account for town trips/re-entering same map and only count when done"): the
         reads at home after a map are its "after" (pending["after"], the newest wins) until it's done - you start
         another map (mp_done) or DONE_SECS (15 min) pass without going back in (mp_check_done, also on the bar's
         redraw); back through its portal after a town trip: the same run, its first "before". The hover says "This
         map so far" meanwhile.
  2.132.0
       - Map profit (feedback: profit per map "using the same mechanism as top-up reminders", "only locally, never
         published or sent to the cloudflare database", "only currency exchange items", "per session/map/hour/day"):
         mapprofit.py (counting, map_profit.jsonl in the data folder - never uploaded) + mapprofit_page.py. Top Up's
         clear inventory looks (topup_looking: Top Up or Map profit on) -> mp_seen at home; breach_area -> mp_area
         (before = last home read, after = the first clear read back home; portal back = the same run). Cells are
         named by Top Up's taught pictures, then Scan stash's (favours refs, art box); only WPRICES.named items count
         (the exchange - no waystones, no gear). The bar's profit part (▲ / ▼, hover = how it was worked out, click =
         Maps…); the Map profit window lists every map (search first, hover = breakdown, session / today totals).
         Its row in Overlay ↳ Overlay Settings › Helpers. Off until turned on.
       - Alert cards (feedback: "for each of the vital alert cards the text should be red"): show(vital=True) - Breach,
         Ritual, tribute and End Delirium words are red. End Delirium says "Map done - Delirium is still on".
       - Tribute counter (feedback: "keeps bugging out and showing all kinds of numbers"; "still getting occasional
         reminders when I click through it all too fast"): a number counts once read the same twice in a row; the
         window's close uses the last steady number from the past minute (HUD_KEEP); "counted down" needs two lower
         reads.
       - Hide the overlay from screen captures (feedback: "needs relocated to where it makes sense, and changed to
         just say 'Hide the overlay from screen captures'"): back in Overlay ↳ Overlay Settings › Options (tk_hidecap), and on
         means always (overlay_hide_capture); off: only a Ritual map's own rule.
       - Runeshape gems (feedback: "people are gonna get rate limited hard"; "players were already supposed to be shared
         through the board, but we need another system on top of that"): your searches' prices go up with the
         community batch ("gems": league, kind, level, name, price) and the board pools them (gem_prices, GET /gems,
         newest wins, two weeks); a book's gem is priced from your own (a day), then the board's (a day), then either
         up to GEM_KEEP (two weeks) old - shown at once, searched again when the budget has room; searches go highest
         level first.
       - Full release: NOTES["2.132.0"]["rollup"] - the card since 2.125.8 (the last full release), as things work now.
  2.131.6
       - Ritual line (feedback: "the tribute amount should stay persistent ... until it goes to 0/map ends"): the
         game's counter leaving the screen keeps the last number; 0, or going right after counting down (offered),
         takes it off; a new map clears it (breach_area), then it's read again.
       - Delirium (feedback: "end delirium is still showing up as big flashing text and not the new alert style"):
         run by the app, the helper's Alert.show / hide only keep `visible` (delirium_runner) - its "state alert"
         reaches the app (DELIRIUM.on_state -> ev_delirium_state), which shows the alert card "End Delirium" (rank 2,
         tag Delirium) and takes it back on the next state. Test with the helper off: a sample card.
       - Names (feedback: "stop calling it calm alert card, just call it alert card"): "Alert card" in names.py
         (OLD: "Calm alerts", "calm alert card"); What's new 2.131.0's title says Alert cards.
  2.131.5
       - Ritual line (feedback: "add tribute count to the ritual counter overlay ... the overlay over xp bar blocks
         it"): the game's own tribute counter (bottom middle; favours.hud_rect / hud_prep / hud_number, Windows OCR)
         is read about once a second in a map by the Favours watcher -> RITUAL.tribute -> "6 of 6 rituals done ✔ ·
         1,376 tribute" (and "All rituals done ✔ · ..."). The bar stays out of captures for the whole Ritual map
         (content open or done), so the counter under it can be read.
       - Tribute (feedback: "it doesn't turn gray when I click it and rapidly close the window"): when the window
         closes with tribute owed, the counter decides - it counted down or went: offered, no reminder. The log says
         which, and the counter's number when it reminds.
       - Top Up (feedback: "if the game's text box blocks the currency item, it drops down to seen 0, ctrl + d
         triggers changes"): a look with the mouse over the inventory panel, or within 8 s of a price check, is
         "covered": Seen keeps the last clear look (cells_use) and the reminder waits for a clear one.
       - Top Up (feedback: "keeps showing up after not running maps ... after well of souls"): topup_visit only when
         you're back from a map (breach_area's `left`); maplib.NOT_MAPS - The Well of Souls (Abyss_Hub) is "other".
       - Linux (issue #234, Settings a black page on Hyprland): Shell.dim_show makes no layer on Linux under Wayland.
  2.131.4
       - Top Up (feedback: "F7 doesn't work ... it'll have to be ctrl+c"): F7's copy is sent by the app, so the key
         watcher (which skips injected keys) never saw a Ctrl+Alt+C and gate_ok turned it away. Top Up's copy is
         now taken first in poll_clipboard (topup_wants / topup_take): the Top Up key is the game's own Ctrl+C by
         default (F7 moves to it once); Ctrl+C anywhere but over the open inventory goes on as before.
       - Top Up (feedback: "go back to the Items... button and add new items"): Items… › + Add more - a name (the
         game's; suggestions in TU.SUGGEST) and a Keep; Seen says "teach it" until it's taught with Ctrl+C.
       - Top Up (feedback: "cryptic keys that do not stack"): item_name accepts Normal items, so a key can be
         taught; each cell holding one counts 1.
       - Alerts (feedback: "people getting annoyed with 3 cards back to back"; the Grouped Alert Card mockup):
         alertcard.Card - one card per app; an alert that comes while it's up joins it as a Row (show() returns the
         Row, which reads like the window). "N alerts" + × Close all, a row each (mark, words, helper tag, ×), rank
         order (Ritual 0, Breach 1, Top Up 3, Breaks 4), up to 4 rows then "+N more", one countdown (restarts on join).
       - Tribute (feedback: "still asking me to offer tribute after I already dumped tribute"; favours_log: closed with
         10,261 left, open again 9 s later at 0): the Favours window seen with its button gray sends favours_offered -
         a tribute reminder up is taken back, a late try (game not in front) is dropped. The log says the button's
         state at close.
       - White / magic bases (feedback: "any ilvl above 82 doesn't matter ... always search at ilvl 82 min"):
         gear.ILVL_TOP - ilvl 82+ searches {"min": 82} (no max; base_ladder has one step, search["base_exact"]).
         Their ☑ mods (feedback: "Count but not ... a count of 2"): base_ladder steps passed k=0, so the count group
         said min 0 - now k = every ☑ mod.
  2.131.3
       - League Plan's Map supplies (request: "move into top up") are gone: Top Up Reminders count what the inventory
         really holds. focus.supplies_out hands the list over once (topup_take_supplies: each name joins Top Up's
         items with Keep 0; Seen says "teach it" until it's taught); the Map supplies tab, its pokes, its switch and
         the game log's omen-used-up line went with it (check_removed).
       - Ask me about mods I haven't rated (feedback: "the rate up and down goes against the Rate Mods page ... tier
         system"): the strip's buttons are S A B C D F, Rate Mods' grades (F = ignore).
  2.131.2
       - Community names (feedback: "encourage users to not use personally identifiable names, and to never use their
         path of exile account or character names"): privacy.NAME_RULE / NAME_TIP - one line (+ ⓘ) on every ask
         (the Leaderboards' card, the board's name window, Money Makers' join and rename). name_problem also turns
         down a name that contains your account / a character's name, or is a big part of one (4+ / 5+ letters).
       - Ask me about mods I haven't rated (feedback: a tablet priced 124d sold near 225d - its unrated Expedition
         mod was left out; "an opt-in for whether or not they want to be asked to rate mods"): SETTINGS ask_unrated,
         off by default (Settings › Price checking › Mods you haven't rated; the Feature Picker asks once). On Price
         Checks the card asks about one unrated, non-★ mod (pc_ask_mod): S A B C D F (Rate Mods' grades, 2.131.3)
         and the item is priced again; Not now = this item only.
       - Overlay page (feedback: "clipped text/cropped buttons"): Start session / Stop without ▶ / ■ (a font without
         the symbol drew it wider than measured); the Not tracking label keeps 16 characters of room, left-aligned.
       - Tribute (feedback: "I click the offer tribute button and quickly exit the favour window ... it needs to be
         fool-proof"): favours.tribute_offered - OFFER TRIBUTE TO THE KING is gray (no color at all) once clicked or
         with nothing to offer, red (~19% clearly red) with tribute to offer; any look with it gray means nothing is
         owed, so closing while the number counts down brings no reminder.
       - Top Up (feedback: still 0 for an item held): the teach takes a look from the last 20 s with the mouse
         elsewhere (and still) for its picture; else the cell is kept in topup.json ("pending") until the next open
         inventory with the mouse off it - closing the inventory or the app in between included. A look while the
         mouse moved is never learned from.
       - Top Up (feedback: "asking me every single map, I only want it to ask when I am below a 70% threshold"):
         topup cfg "below" (0.3 by default) - low() reminds under Keep x (1 - below); Items… › Remind when "30% below"
         (0-70%) with how it's worked out beside it ("Keep 40: a card under 28").
  2.131.1
       - The bar (feedback: "the overlay on startup has no option to start session tracking"): while no session
         runs, ▶ Start session sits first on the bar (merged_page.start_on_bar / _mg_start_button, every look); the
         timer takes its place. One name: the Overlay page's button and its empty state say Start session too, and
         Options' autostart switch is "Start a session with StashOfExile2" (it always started a session).
       - Feature Picker (feedback: say why a name is asked): a line under the sharing tick - the Leaderboards need a
         community name, asked next. Sharing from before with no name: the name is asked after Save.
       - Sharing asked twice (bug): cm_start's older popup opened at 15 s when the quick start was closed, or over
         What's new; the Feature Picker asks it now (the popup only after Never ask again).
       - Lost windows (feedback: the picker opened under What's new and vanished): it waits until What's new / the
         quick start is closed and comes right after; the picker, the name card and the sharing popup are owned by
         the app's window (Windows keeps them above it) and follow Always on top.
       - Quick start page 5: ▶ Start session and Overlay › Overlay Settings › Helpers (Ctrl+Alt+S and "Mechanic Helper" are
         gone).
       - Top Up (feedback: the price check key left its card up): its own key, F7 (Settings › Keybinds; topup_key),
         copies the item and only teaches; the price check key just prices. Hover glow (feedback: "it didn't detect
         the quantities" - 0 held): topup_refine learns the taught cell again once the mouse is off it.
       - Quick settings › Helpers: Top Up, Breaks and Desecration (its beta feature on) chips.
       - Leaderboards (feedback: only my times): the keys answer has league_players (counts only); League ▾ says
         "Runes of Aldur · 1 player"; a league whose players ran different boards says so.
  2.131.0
       - Full release after the 2.126-2.130 pre-releases: whatsnew NOTES["2.131.0"]["rollup"] merges their notes
         with no repeats; notes_between shows it to anyone coming from 2.125.8 or older (pre-release users get only
         2.131.0's own lines).
       - Feature Picker (features.py / features_page.py): one popup for features, sharing and the data folder, shown
         once after updating; Settings › General › Features keeps the same switches. The Beta switch and the quick
         start sharing page are gone (check_removed).
       - Settings as a window over the app (shell OVER): inset on a dim layer; Esc, × or a click on the dim closes it;
         it reopens on its last tab.
       - Alerts: every helper alert is the alert card (alertcard) - Where / Size / Test in Overlay › Overlay Settings › Helpers.
       - Break reminders: off by default; after 45-120 min of play, a card in hideout / town.
       - Top Up Reminders (topup.py / topup_page.py): teach an item with the price check key while the inventory is
         open (banner template), counts read from the stack digits (shipped digit templates, learned from Stack Size,
         Windows OCR fallback); one card per hideout / town visit when an item is under its Keep. Screen only, no
         game files or servers (TOS.md item 2).
       - Campaign: the My Own route is gone; saved runs on it move to Full (campaign.cfg migration).
  2.130.4
       - Remnant (feedback: "expedition doesn't read 10x divine orb" - its log: 'IOX Divine Orb'): _fix_qty reads a
         count's I / l / | as 1 and O as 0; LEVEL_LINE "Level 20: X" (Skill hidden) is a skill gem; fix_case.
       - Remnant gems (feedback: "trade site rate limited us on fetching prices"): GEM_BUDGET 3 searches per 5 min,
         prices kept 6 h on disk (remnant_gems.json), the book re-read after each.
       - RUNE_TIERS: C and D alphabetical (feedback).
       - Favours (feedback: "not showing some items when there's duplicates"): FV.twins - an unnamed cell >= TWIN
         like a named one in the same window takes its name; a cell named earlier keeps it while the rewards are the
         same (sticky); later looks logged when they differ.
       - Filter in the Ritual window (feedback: "bad UI+UX"): a plain button with ✓ On / ✗ Off beside it. Turn it
         on (feedback: "ONLY if we can safely and accurately adjust that line"): ritual_filter.turn_on changes that
         one line (every other byte checked the same), copy in backups/ first, one-step replace; the dialog waits for
         the game window to close and the file to be quiet 4 s, then says to start the game again.
  2.130.3
       - Game log (feedback: a player who installs games elsewhere got no map counts or helpers - Client.txt wasn't
         found): gamelog.find_log also looks where Windows' installed-programs list says Path of Exile 2 is
         (installed_game_dirs, registry only) and in every Steam library (libraryfolders.vdf), at most every 20 s.
       - Desecration Helper (feedback: "needs to learn heart of the well diamond jewel mods"): its 72 own mods (RePoE,
         generation type "unique", heart_unique_jewel_prefix / _suffix) added to tierdata.json (build_tierdata.py
         --heart); options that are all Heart mods at Heart values (heart_fits) are rated on it: "Heart lo-hi · roll%".
  2.130.2
       - Ritual (feedback: died, exited to character selection, came back on another character - the reminder came):
         gamelog LOGIN (the login server connect) -> "login"; a map -> hideout move after it is no leave (br_relog).
       - Themes (feedback: "people keep crashing when rapidly changing themes"): clicks during a swap wait, only the
         last is applied after THEME_REST (400 ms); busy cursor on the cards.
       - Gruvbox Dark / Gruvbox Light packs (request; gruvbox by Pavel Pertsev / morhetz, MIT - THIRD_PARTY_NOTICES,
         README, About). themes.walk: KEEP (overlay colors) applies only outside the app's own windows - a color an
         overlay style shares with a pack stayed light on a light theme.
       - README: short, one line per feature.
  2.130.1
       Feedback: "overlay at top caused the ritual portion of the bar style to be beyond the edge of the monitor";
       "bottom alignment mode is a few px above the xp bar"; the tribute reminder came "after I already dumped my
       tribute" (the plate said "0 Tribute"):
       - goalbar_build: with the Bar placed at the top, the lines pack under it and the window grows down (_gb_below).
       - HUD_SPOTS bottom 0.0205 -> 0.0153 (the XP bar's top, 22 px up at 1440p).
       - favours.tribute_of: a lone O / "Tribute" with no number reads 0 - an old number never brings the reminder.
       - trade.apply_opts (feedback: "sockets: 5 ... chose augmentable sockets instead of just gem sockets"): on a gem,
         the item panel's Sockets is misc_filters.gem_sockets (rune_sockets dropped).
  2.130.0
       - License: GNU AGPL v3.0 (LICENSE, README, THIRD_PARTY_NOTICES, About); up to 2.129.4 GNU GPL v3.0.
       - New league heads-up (app.LEAGUE_NOTICE): one message on the first start from December 11, 2026.
       - Filter in the Ritual window (ritual_filter.py): reads only apply_item_filter_to_ritual from the game's
         poe2_production_Config.ini (shown without the user name), Open folder / Copy line / Check again; credits
         NeverSink and Ryonnen.
       - Game Overlay place: Quick settings › Place (Bar bottom / top, Panel left / right); Options › Reset position.
       - Gems (feedback): the price check key searches skill / support / spirit gems on the trade site (gem_level,
         gem_sockets, quality, corrupted); lineage gems stay on the exchange. Remnant books: "Skill Level 20: X" /
         "Support: X" lines priced in the background ("Fetching price…"), "Unique <kind>" (ring, belt, amulet, jewelry)
         lines name the most valuable uniques of that kind (poe.ninja, names only).
       - Remnant (feedback: the book's last two runes unpriced): an area learned by the old key is read together
         with AREA (reading_area), so a long book is read to its foot.
       - Favours (feedback: "FLASHING TO OFFER TRIBUTE WITH THE WINDOW OPEN"): the title hidden by a reward's tooltip
         isn't a close while most cells last seen holding items still do (still_open); otherwise the reminder waits
         until the window has been gone 4 s (REMIND). Six omens learned on the user's windows ship
         (templates/favours_learned.json, item pictures only).
       - Ritual counter (feedback: "ritual isn't accounting for anything above 4 rituals, you can get up to 7"; a
         3/6 screenshot): digits 5 - 9 added to ritual_glyphs.json (fonts + the user's 3/6, build_ritual_glyphs.py
         --add), totals 3 - 8 accepted (TOTAL_MAX).
       - alertcard.py (the alert card) is in, not wired yet.
  2.129.4
       Feedback ("ritual thing says 0/3 rituals done but I've done 2/3"; its log: the counter was seen at 0/3, then
       not for 9 minutes): the overlay's Ritual line sits over the game's counter, so the watcher couldn't see it
       change. While you're in a map whose Map Content shows Ritual still to do (the watcher's "content open"), the bar
       is left out of screen captures by itself (as Settings › Advanced's switch does, 2.85.2) - the watcher sees the
       counter under it. Everywhere else, and once every ritual there is done, screenshots and streams show it.
  2.129.3
       Feedback (Favours: "still missing some omens also and idols ... sacred bloom pricing missing"; "look for rite of
       passage charm"; the tribute reminder "should ONLY pop up after I've closed the ritual window after not
       offering tribute"):
       - Colors: favours.feats adds a hue histogram of the art's colored pixels (hue). The color layout took out the
         overall tint, so the same hand in teal (Refreshment) and purple (Whittling) scored 0.80 / 0.76. A close top
         two is settled when the colors match far better (HUE_BY 0.25: 0.54 vs 0.20).
       - Sacred Bloom ships as a Favours cell (templates/favours_cells.png + .json, shipped_cells).
       - Idols ship as the currency exchange lists them (templates/favours_icons.png + .json, from the user's
         screenshot): compared cropped to their art, Idol of the Pharisee scored 0.82 and every other cell under 0.64
         (omens' exchange icons stayed under 0.6). "Far ahead" (2.129.1) is now measured against pictures of the same
         kind, so an idol icon doesn't crowd out a sealed omen.
       - Any copy of a reward's text (Ctrl+C or the price check key) while the window is open teaches its look
         (favours_copy_learn): exchange items such as idols, and the uniques that get a ★.
       - ★ one-cell uniques (STARS: Rite of Passage, its picture from the game; star_refs, find_stars), no price.
       - When most rewards change (a reroll), our tags are taken down before the new ones are read - each cell is
         read whole now, and a tag over a new reward spoiled it.
       - Tribute reminder (feedback: "you can offer tribute no matter if you have rerolls or not ... if you close the
         favours window no matter what it should ask"): on any close with tribute left - rerolls no longer count. The
         tribute is read from the last look before the window closed (it was up to 1.5 s old), so after offering (0
         left) nothing shows.
       - Feedback ("moved [the app] to another screen ... the wealth screen stayed on screen"): when the app lands on
         another monitor, each page window is shown again in its place and any copy Windows left behind is hidden
         (shell.monitor_check).
       - Ritual (feedback: the line said 1 of 3 while it was 3 of 3 - the counter at the bottom isn't always on
         screen): the watcher also looks at Map Content under the minimap every 2 s (ritual_alert.content_state,
         templates/ritual_content.png: the Ritual icon 0.94 - 1.0, anything else under 0.7); its green tick means
         every ritual is done - the line says so and leaving doesn't remind you.
       - Ritual (feedback: left a map at 2 of 3, no reminder): a reminder that comes while the game isn't the window
         in front (a screenshot tool, another window) waits up to a minute for it; the log (Debug mode) says what the
         leave check saw and when a reminder couldn't show.
       - Price check key, Overlay + Here (feedback: "it's still prioritizing the app and bringing it to the front"):
         while the game is in front the app isn't touched; Price Checks opens on the item when you come back to it.
  2.129.2
       Feedback ("whispers button doesn't work when I click it ... perhaps we need to just remove the 'After the
       campaign' option all together"): Trade whispers is on or off. Past the campaign, with After the campaign off,
       it was on but resting - its chip showed off, and clicking it switched on what was already on, so nothing
       changed. The option, its setting (migration whispers_after_21292) and whispers.in_campaign are gone.
       - Remnant (feedback: "eventually popped up but took a while"; its log: the first read took 14.5 s): that read
         fetched every poe.ninja price list first (over an hour old). The watcher now fetches them in the background
         before a book opens (remnant_prefetch: one try in 5 minutes), and a read uses the prices held, refreshing
         stale ones meanwhile.
  2.129.1
       Feedback ("Expedition helper isn't showing up at all anymore", "no ritual reminder", an omen not read, "offer
       tribute ... stayed on-screen too long"):
       - Ritual watcher: its log showed "started" and "stopped" in the same second at every start (once 159 s late).
         It read the app's pipe in a thread before loading OpenCV / mss; on Windows a thread waiting on a pipe makes
         each newly loaded library wait too, until the app writes (its "quit" when it closes) - so the watcher sat
         stuck all session and the app saw it as running. Now everything loads first, then the pipe is read (as the
         Delirium helper always did). Its log says when it launched and how long starting took.
       - Remnant: a reading area learned by the old key can start inside the book's title, so the title check (2.129.0)
         never passed - nothing showed. The title is now looked for in its own place (remnant.TITLE_AREA), and the
         log says when parchment shows without the title (and the match).
       - Favours: a gray, sealed reward (Omen of Sanctification) scored 0.51 with the next item at 0.23. Far ahead of
         every other item (0.50 and 0.25 clear) counts too; wrong ones were never more than 0.15 ahead.
       - The OFFER YOUR TRIBUTE banner shows 4 s (was 8).
  2.129.0
       Feedback batch:
       - Favours prices: wrong prices (a junk unique 34d, Sacred Bloom and omens 4.6d) - poe.ninja's official art
         scored up to 0.64 for the wrong item and was never sure for the right one, and the 0.55 bar let those
         through. Now only pictures learned on this PC count: Scan stash keeps each one-cell slot's picture of the tabs
         it reads (three sizes; stashread.read_tab "pics", favours.learn_many) and the price check key on a reward
         (exchange items only - a learned unique is never priced). Matching leaves out the stack number's corner and
         adds colors; 0.72 and 0.10 clear of the next. Tried on the user's own windows with his Ritual tab: Bartering
         0.88, Catalysing Exaltation 0.74, nothing wrong. No uniques; Mageblood and Headhunter get a ★ (their
         trade-site pictures, templates/favours_*.png). Migration favours_art_2129 deletes art/ninja and the first
         learned file. The log lists each cell's closest calls.
       - Tribute reminder (Ritual helper option): the reroll button is gray at 0 rerolls (red otherwise) and the
         tribute is read (OCR) while the window is open; closed with 0 rerolls and tribute left -> a banner.
       - Remnant: reads only under the book's "Runeshape Combinations" title (templates/remnant_title.png; the book
         1.0, sandy ground 0.2) - the parchment color alone showed the runeshape list on a map. "lx" / "Ix" read as 1x
         (Warding Runes showed nothing); the log lists the lines it couldn't use. A tag worth less than an exalted
         says "<1ex" (fmt_div: "0.33 exalted", not "0.001 div").
       - Omens, lineage gems and every currency on the price check key or Ctrl+Alt+C: poe.ninja's exchange rate,
         never a trade search (parse_currency_item first; lineage gems by their tags; 2.127's lineage trade search is
         gone).
       - Ritual watcher (its log: told to quit the moment it started, every start): started again when it's on but
         not running (at most every 30 s), and who stopped it is in the app's log.
       - "dearest" is gone from the app (names.OLD: check_names finds it).
       - Every omen of the Ritual tab ships (templates/favours_omens.png + .json: slot pictures in the tab's order),
         so none has to be in your stash first; each cell is also compared cropped to its art (favours.art_box), which
         lines up a stash slot and a Favours cell. On the user's six windows: 8 of 8 omens right, none wrong. Wombgifts
         stay a trade search.
  2.128.1
       Feedback ("I'd like the expedition helper + runeshapes to show up on screenshots / screen share / streaming
       in the same way the overlay does"): the Remnant tags, the runeshape list, the Island rumors card and the
       Favours tags are no longer left out of captures (no_capture). The watchers would now see them, so they paint
       over their own windows before reading: remnant.OWN holds each one's place on screen (set when shown, cleared
       when hidden) and mask_own fills those spots with the picture's middle color. Favours reads only each cell's
       top part (favours.TOP 0.64 - its tag sits at the foot), for the official art too; pictures learned from now on
       are that part (favour_icons_v2.json).
  2.128.0
       Favours prices (feedback: "show me the currency exchange price of the item ... the same way we do expedition
       price helper"): the Ritual helper's new option. favours.py finds the Favours window by the word FAVOURS on its
       title plate (templates/favours_title.png, cut from a 1440p screenshot; other screens score ~0.3, it 1.0), the
       12 x 10 grid at a fixed offset (70 px cells at 1440p), the cells with a blue / red backing, and compares each
       with poe.ninja's exchange items' pictures (official art from web.poecdn.com, laid on the backing, plain and
       dimmed; cached in art/ninja) and the ones learned on this PC (favour_icons.json: your price check key on a
       reward while the window is open). Picture and outline correlation, the best must reach 0.55 and beat the next
       by 0.06 - the same omen across two windows scored 0.72-1.0, other items under 0.45. favours_page.py: the
       watcher thread (twice a second while the game is in front; only the top-left of the game is captured; a still
       window is read once), click-through tags at the foot of each cell (★ on the most valuable, hidden from capture) and
       ritual/favours_log.txt. 1-cell items only for now (omens, currency, runes ...). Idea looked at in poe2pricer by
       saxe78 (MIT) - our own code.
       Freeze (feedback: after a theme change, then opening Price Checks: "not responding", every sample in
       pcv_card's update_idletasks): no forced layout pass there (the scroll goes back after_idle), nor in
       bulk_pane; the recent-checks row repaints only on a real width change and never from the idle loop (its
       after_idle repaint changed the row's size, which could ask for another repaint, again and again); the
       verdict line re-wraps only on a real change. Ritual helper: no learned-shapes file isn't an error any more.
  2.127.0
       Feedback batch:
       - Lineage support gems (Arbiter's Ignition ...) are priced: gear.lineage_item reads a "Rarity: Gem" copy whose
         tags say Lineage and searches the trade site by its name (Price Checks and Bulk Pricing); poe.ninja's
         LineageSupportGems rate goes in its notes. Other gems still aren't priced (not traded as items).
       - Currency on your price check key: the card over the game (pcpop_rates) shows its going rate - 1 ≈ x div,
         1 = n exalted · n chaos, what a Divine / Exalted / Chaos Orb buys of it, the stack's worth (RATES.common) -
         with Open Exchange Rates. Card off: the toast says the same.
       - The session timer survives a close, an update or a crash: the running session is saved to
         session_live.json (at start, at each map, every 30 s, on close). The next start brings it back paused
         (the time the app was down doesn't count; the game being there resumes it) if it was saved under 2 h ago,
         else files it in the history as it was. on_close no longer ends it.
       - Mageblood: a Legacy whose game-data id isn't on the trade site's list is found there by its wording
         (mods.option_live) instead of being dropped from the search; a ticked mod left out says why on its line.
       - Bulk Pricing's Item pane is always on screen (an empty state while nothing is picked); its ✕ and the Esc
         that closed it are gone.
       - Regex favorites over the game: the overlay's one lock locks it too, and it stays where you drag it (rx_ov).
       - Ritual watcher (feedback: no reminder on leaving a map): its log showed it quitting the second it started,
         every start since late October - its input from the app ended and the app's mark wasn't found. Now, with
         no mark, the app's process id is looked up on the list of running processes (delirium_runner.process_alive,
         no process opened); the log says why input ended and why it quits. Same for the Delirium helper.
       - Remnant (feedback: tags ~10 s late again): remnant/remnant_log.txt logs each book - when it showed, each
         read (how long, lines, priced), failed reads (were silent), when the tags went up. The OCR engine is made
         once, not per read.
       - Settings › Keys is Settings › Keybinds, with ↺ Defaults (tracker_page.DEFAULT_HOTKEYS; chat command keys
         stay). names.py: OLD "Settings › Keys", FEATURES "Keybinds".
  2.126.0
       UX pass 3 (code). Dead code out: 41 functions and methods nothing called (kept "for older callers" or left
       by earlier removals), unused constants and imports, an always-true branch and a taskbar loop that never ran.
       The one-key copy's leftovers (2.98.3) - its key handler and the quick_copy_key / hotkey_only settings - are
       gone; migration leftovers_2126 clears the two keys. Three new checks, each with a one-line run:
       tools/check_removed.py (REMOVED lists every removed feature's words and names; none may be left in the
       app's text, code, docs or tests - --tests DIR), soe2/names.py + tools/check_names.py (one name per feature:
       PAGES by module key, FEATURES, OLD names that never appear in the app's text; page names in Title Case;
       old page names still open their page via names.OLD) and tools/check_ux.py (opens every page, tab and
       Settings section in an empty data folder, offline: one orange button per screen and one BETA chip are
       enforced; icon buttons without a tooltip, search box not first on a list page and buttons on with nothing
       picked are listed for UX round 2). style.Tooltip marks its widget (_tip). check_names and check_removed run
       in CI. Found by the checks: README names (Mod Book, Exchange Rates, Notes) and a stale line about Bulk
       Pricing's floor; Wealth's old stash tab sync (hidden since 2.106.0) is listed as pending.
       Feedback: Bulk Pricing's Undo and Delete were full-size buttons hanging out of the Items strip, and Clear list
       was only under ⋯. Now Undo, Delete and Clear All (app.clear_all_btn, lit while the list shown has items; was
       Clear list in ⋯) sit together in the strip as Strip.TButton / StripDanger.TButton - small, flat, sized to
       their words, with tooltips. SectionBar leaves its note out when the two sides leave it no room.
       Feedback (Remnant tags took ~10 s, game paused): after its settle reads the watcher only read a book again when
       the picture changed, so a still book first read mid-animation (or before prices / the map's Expedition mark)
       stayed bare. While no tags show it now reads again every RM.RETRY_SECS (1 s); once found, a still book isn't.
  2.125.8
       Feedback: "I still don't see anyone else's info/map times in leaderboards". app_log.txt: "Item b1767 already
       exists" while drawing a board. Picking a board looked it up twice (the pick and the list's refresh); the
       slower answer drew its rows again and stopped half-way with that error. Now only the newest answer is drawn,
       into a cleared list (lb_board_fill / lb_refresh count their looks). A board (or every board) with only your
       time says so: other players' times show once they share theirs (Community data sharing is opt-in).
       Why every board said Players 1 since 2.86.0: times go up only with sharing on AND a community name, and the
       name was asked only when you posted on Money Makers or flicked Share my times - players who opted in sent
       nothing. Feedback: "ask once on first install, and after this next update ask them to set their opt-in
       preferences ... and then pick their name if they opt-in". The quick start has a "Share with the community?"
       page (why you'd say yes, Share / No thanks, What's shared?); Share asks for a name next (cm_name_ask). After
       this update: not asked yet -> the sharing question (as before), then the name; sharing but no name -> the name,
       once (lb_name_asked). A No is never asked again.
  2.125.7
       Feedback (a player): at The Well of Souls - the Session tracker said so - the Desecration Helper (on, Beta
       features on) showed nothing. Three gaps: it woke only on the area id Abyss_Hub (the tracker goes by the scene's
       name), so it now wakes on the scene "The Well of Souls" too (ws_scene); started (or turned on) while already
       at the Well, it waited for the next area - the log's last area and scene now count at start; and when Windows'
       text reader (OCR) can't be used it said "on" and did nothing - the notice now says why, and app_log.txt has
       it (no names, no folders).
       Feedback: a magic tablet with 2 bad mods reads "Reforge or Alchemy" (the verdict's word; the step said it).
  2.125.6
       Feedback: "any updates to beta functions should only show in the What's new card if a person has labs/beta
       enabled". Notes whose area is a beta feature (whatsnew.BETA_AREAS: Wealth, Money Makers, Game Search, Market
       Insights, Craft Helper, Stash tab, Scan stash, Desecration Helper) show only with Settings › General › Beta
       features on; an update with nothing else to say shows no card (it's marked seen). The intro names the switch
       (it said Labs). About's version history still lists everything.
       Feedback on Settings › Price checking: Prices in joins "How searches are made", now called Search Options;
       the Mod Book rows (re-check a learned mod after N days, learn new mods in the background - "people ... won't
       know what that even means") are gone from Settings and keep working as they are; Shortcuts are removed (1.21's
       "from memory" and 1.23's "from model" skipped a search - engine branches, settings, migration shortcuts_2126).
       Feedback: over the game, the price check overlay's ⚙ says In the app | Overlay + the app ("Here" there read
       as the overlay). Feedback: the Craft Helper's mods and Pairs That Sell Together share the height on a divider
       with a visible grip (style.VSplitter - Splitter on its side); where you leave it is kept (ch_split).
       Feedback: "reforge or alch should be given as the option for 2 bad mods" - the tablet steps (data pack
       revision 2) and the advice say "Reforge it, or Orb of Alchemy."
  2.125.5
       Feedback: some players got two updates in a row. The version to install was picked when the update was offered
       (the "Update available" question, a card's Install now) - left open while a newer version came out, the older
       one was fetched, and the newer one was offered straight after the restart. _download_update now asks GitHub
       again just before the download and fetches the newest (it says so when that's a newer one); only one download
       runs at a time, and nothing else starts while one is being installed (_upd_installing - 2.125.2's retries
       for Windows' scanner could leave a gap for a second one).
       Feedback: "ALL tools that open over the game ... should follow these rules for styling matching". The buttons
       and lists on cards over the game (route card, Vendor search, Rank this map, Regex favorites, Well of Souls)
       were the app's (its orange Primary and blue buttons, drawn from images); ov_btn now gives them the overlay
       style's colors and font on a plain frame (the picked one: the style's accent edge, bold), and ov_combo the
       lists (field and dropdown). A style change rebuilds the open route card (its page, act, spot and size),
       Vendor search and the price check card (ov_cards_restyle), as Calc, Regex favorites and Rates already were.
       Feedback (a player): the price check card "doesn't say slots or show what is in them". Sockets: 2 (1
       augment, 1 jewel); a SOCKETED part lists what the socketed runes / soul cores / talismans do (the game's copy
       gives their effects, marked (rune), not their names - those lines moved out of MODS SEARCHED, still tickable),
       and says when there's a jewel socket (the copy says nothing of the jewel in it).
       Craft Helper phase 3: its data pack, crafthelper.json (each kind's types and steps, how the market picks a
       letter), ships with the app and updates from GitHub - at most twice a day while the page is open, one small
       public download, nothing about you sent - with "Data pack: game patch 0.5 · revision 1" and Check for a newer
       one on the page. Learned mod pairs: two mods whose listings (your price checks', this league) ask clearly more
       together than the better one alone (6+ listings with both, 1.3x+), with a letter from how far over the kind's
       middle price they ask - no prices; hover one for how it was worked out. A checked item carrying a pair rated
       better than its mods counts both at the pair's letter, and the verdict says so.
       Feedback on Settings › Price checking: Valuable mods ("they don't really add anything") - gone, the app's own
       amount (good_div 0.5) again; Skip cheap items (2.96.0's Bulk Pricing floor, "don't work") - removed (floor_cfg,
       floor_check, the engine's _floor, its settings; migration pc_settings_2125). Where the price shows: only
       Here | Overlay + Here, as on Price Checks ("In the app, behind the game" and "Nowhere" are gone - clear the
       key on Keys for none). "Card over the game" is called Overlay; its close key is set on Keys only (Settings'
       row and the overlay's ⚙ key box are gone - the ⚙ shows it with Change on Keys ›). The overlay's ⚙ box is in
       the overlay's style, with Here | Overlay + Here chips.
  2.125.4
       Feedback on the route card: "the act selection dropdown needs to be on the right" - it's now right of Routes ▾
       and Options ▾. Routes ▾ "needs some visual hierarchy ... for division of selectable options": each route is its
       own row with a line between them, the one in use on an accent-tinted ground with a bar and "✓ In use", and
       a row lights up under the mouse.
       "The whole campaign card is pretty laggy": a click no longer builds the card again - only the page shown is
       built again, the others when they're shown (camp_pages_refresh / _camp_build_page); the overlay's line is
       redrawn after the card has drawn its change (once for a run of clicks); the line's fonts are made once per
       look and their text widths remembered (fit_lines asked the same widths on every redraw); campaign.cfg() and
       focus.cfg() copied every default on every read - now only missing ones.
       "After resizing it isn't remembering size if I change to a screen that causes it to expand longer": a size you
       give the card is saved (Campaign card_size) and used from then on, and another act or page scrolls instead of
       growing it. It's never narrower than its toolbar (snug buttons), so Routes ▾ and Options ▾ stay in sight.
  2.125.3
       Feedback: the Campaign Helper's route card didn't scroll - resized, its list ran past the window. The pages
       are now in one scroll area, and the card is at most 85% of the monitor's height.
       Feedback: the card "disappears to the background until I click on the screen window again and again". Its
       act list's dropdown (and a tooltip) is a window of its own; while it was in front, nothing counted as the game
       or an overlay window, so every overlay window hid. A window's own dropdowns and tooltips now count as it
       (overlaywin._child_hwnds).
       Feedback: Routes ▾ and Options ▾ on the route card - the route, and the Campaign switches from Overlay
       Settings › Campaign (one setting each, kept in step both ways), as small panels inside the card, not windows.
       The routes are called Full, Speedrun and Rush (carry) (2.131.0: no 4th); "Ask which route when a campaign starts".
       Feedback: "where did all of the columns go on bulk price checker? ... show all of them by default but have
       options to toggle them off". The Item column stretched and its width was remembered (1891 px), so every column
       after it sat out of sight - and Columns ▾ ticks seemed to do nothing. Now every column shows, Columns ▾ turns
       any of them off but Item (bulk_cols_off), Item's width isn't remembered, others are kept to 420 px at most,
       and columns wider than the list scroll sideways. Migration cols_2125 drops bulk_cols and Item's old width.
       Feedback: Reload Overlay (⟳ next to All settings… in Quick settings) builds the overlay again and restarts the
       loop that keeps it over the game.
  2.125.2
       Feedback (a player's screenshot): "could not be installed automatically ([WinError 32] The process cannot
       access the file because it is being used by another process)". Starting the downloaded update right away
       failed while Windows (its virus scanner) still held the new file. Now it's tried again every 0.5 s for up to
       20 s, with "Installing the update - waiting for Windows to finish checking the file…", before the message.
  2.125.1
       Feedback: the app froze, then closed, picking Hairline from the cog with Settings open, and the text under
       Settings' style preview still flickered for the light styles in Panel. The preview's held size (2.124.1) was
       measured with update_idletasks, which ran a layout loop: the text under it re-wrapped to its width
       (style._rewrap), the width followed the held size... (hang_report: pickers._hold_size). Now its text keeps
       its own wrap and the size is read 40 ms after a preview is drawn, never forced.
       Feedback: Quick settings matches the overlay's style - its colors and type (Classic: its gold), a Layout pair of
       chips (✓ on the one in use) and All settings… in the same look; picking a style there redraws the box in it.
       Feedback: the start-up screen sits in the middle of the app's monitor when the app was maximized (it used the
       window's normal size and place).
  2.125.0
       Feedback: "we need the rush/carry helper ... in the perspective of the person giving the carry". The Campaign
       Helper's fourth route, Rush (carry): every step of the guide pack has a "rush" line for the carrier - what to
       clear, when to bring the other player in for a kill, what they pick up, which waypoints they tag and who they
       talk to (campaign.json revision 3). Skips as Speedrun; side zones with a rush line stay (Freythorn's spirit).
       The order and essentials follow poe2wiki.net's Guide:Acts quick guide (credited in the pack and the README).
       Overlay ↳ Overlay Settings › Campaign › Route says what each route does in one line, and picking one applies to a
       character past the campaign too (a carrier's). A Rush run isn't nagged about rewards it skips.
  2.124.1
       Feedback round on 2.124.0. Classic: the Panel is drawn in the Bar's look (stone, pewter frame, corner
       brackets, the Bar's colors and type - the Slate Panel's parts; hudart.panel / panel_palette) instead of the
       vendor-window card (removed with its code); the lines over it sit on the same stone, over the Bar on the Bar's
       own plate, one line about as tall as the bar. Notes in the Classic Panel take that look too.
       The Panel's menus stay inside its frame (wrapped). The Bar's map part cuts the area's name first and keeps the
       time at the bar's size (feedback: map name, time and session crammed). The campaign line wraps to 3 lines and
       reads "Burrow, then" (not "Burrow., then").
       Feedback: after an update the app opened on the wrong monitor (a plain restart was fine): the new version read
       settings.json before the old one saved its place on closing - now saved first (save_window_place).
       The Zone time counts from coming into the zone (it showed 0:00 when the app started inside one); it's "-"
       when not known. Zone times for the leaderboard: only while a character is still in the campaign - the board
       says so when it's empty. An older run without a league gets the current one.
       Settings › Appearance: the preview keeps its biggest size (feedback: the text under it flickered - a shorter
       preview pulled the list under the mouse, back and forth) and always shows a map. Quick settings: Layout,
       Panel | Bar (feedback). The layout-loop log counts size changes only (a dragged window moved on every mouse
       step and was logged as a loop).
  2.124.0
       Feedback: "instead of having it as an isolated separate bar, can we just have it combine when it's enabled?"
       The Campaign, Ritual and NOW lines are drawn at the top of the overlay's own window, as wide as it, and the
       window grows upward by their height - the bar itself never moves (goalbar_build: a canvas packed above the
       bar's; its saved place is the bar's, under the lines). No more separate small window, Dock switch or spot of
       its own (settings cleaned once). Each line is one text line and a little air (feedback: too tall).
       The campaign line fits by measured width, not a count of letters, and wraps under its head when the bar is
       narrow (feedback: "you can't see any of the information"); the step shortens to "2/14" before it goes. The NOW
       line is fitted by width too. Redrawn in place when it still takes as many lines (the window kept jumping).
       Feedback: in campaign areas it should say Zone, no tier ranking or average. With the Campaign Helper on, the
       whole campaign (hideouts on the way too - Vendor ▾ left the map name no room) shows the act line, the session
       and the zone's time (from entering the zone
       to leaving it, AFK and hideouts left out); NOW stays when League Plan is on. Each zone's best time goes to a new
       Campaign zones leaderboard, by the zone's name, only with Community data sharing on (as every board).
       Route card (feedback: Rewards made it resize over and over; a click redrew the whole window): all three pages
       are built once and a tab only swaps them; the card keeps one size; a tick or a step changes only its own
       lines. The act list switches after its dropdown has closed, and one window's error no longer stops the watch
       that shows the overlay over the game (feedback: the overlay vanished after many ◀ ▶ clicks and an act change).
       Vendor search: the Copied line wraps inside the card instead of widening it.
       Settings › Appearance: Layout first (Panel | Bar), then Style - its preview shows the layout picked (the Panel
       had none). "Game bar" is called Bar. The Panel's "Maps s: 6" reads "Maps 6" again. Its menus wrap.
       Quick settings: every switch and chip has a one-line tip, and an on chip shows ✓.
       The joke Death Recap card is gone (and its setting).
  2.123.6
       Feedback: "program not remembering where it was if on other monitors after it updates". Two changes: the
       "is it still on a screen?" test asks each monitor (MonitorFromPoint) instead of the box around all monitors
       (that box comes from the virtual-screen size, which can disagree with Tk's coordinates under display scaling,
       and a window there was sent back to the main monitor); and on Windows the app keeps Windows' own placement
       record (GetWindowPlacement: its normal place on its monitor) and puts the window back with it
       (SetWindowPlacement, maximized or not) - Windows keeps that on a screen itself if a monitor is gone.
  2.123.5
       Feedback: "we don't use the UK spelling of stuff, change any and all non US American spelling". Every string,
       comment, docstring and doc now uses US spelling (color, behavior, gray, center, canceled, maximized, Island
       Rumors, Jewelry, Defenses, Armor ...). Kept as the game writes them: the game's own words the app reads or
       searches for (Armour, favours, Honour, Defences, Body Armour ...), names in the code, data keys and file
       names. tools/check_spelling.py (on every pull request) keeps it that way.
       Feedback: Island Rumors showed in a hideout with no card open. It looks for the card's tan parchment on screen;
       a lit tan floor passed that color test and misread scraps loosely matched a rumor. Now rumors count only when
       one of the card's own lines is read too - its heading, "Use a logbook to chart the area" or "Requires:
       Expedition Logbook" (rumours.is_card, fuzzy for the handwriting); a patch that isn't the card isn't read again
       while it stays the same, and rumours_read.txt says "Not the card".
  2.123.4
       Feedback: the Price Checks divider was "janky and slow, almost like it's in slow motion, there's also no
       visible indicator". It's a Splitter now (style.py): a grip you can see (a line with dots that lights orange
       under the mouse, with a tooltip); while you drag only a thin guide line moves, and the item is drawn again
       once, when you let go. Same limits (330 px; all but 300 px of the page), remembered (pc_card_w).
       Craft Helper phase 2: Check my tablet / jewel gives a verdict - ✓ Worth pricing, ↻ Craft on, ⟲ Reforge,
       ✕ Vendor (crafthelper.verdict; a mark and a word, never color alone) - with the next step, each mod's
       rating, and why ("2 of 4 mods rated S or A"; mods not rated yet are said). Corrupted items: price or vendor,
       never craft. Price it runs your own price check on the item (the helper never searches by itself).
  2.123.3 (hotfix)
       Feedback: "remove Overlay or Both and change it to Overlay + Here" - the card over the game always comes with
       the app now (PC_WHERE Here | Overlay + Here; PC_SHOW has no card-only choice; an older card-only setting reads
       as Overlay + Here). And "you've made the item view too wide ... allow a person to resize it": Price Checks'
       item and listings share a divider you drag (a ttk PanedWindow, pc_pane), 420 px to start, never under 330 or
       over all but 300 px of the page, remembered (pc_card_w).
  2.123.2 (hotfix)
       Feedback: Price Checks' buttons belong under the item, not on the strip at the top - Search again (with
       "Search with fewer mods" when it helps) and Clear, then Add to favorites and Trade Site, are made with the
       card again (pcv_card); the strip keeps the price, how sure and how it was worked out. And "show the price:
       Here | Overlay | Both": Both (pc_both) = the card over the game, and the app shows the item too without taking
       the keyboard from the game (Windows: it's handed back) - also in Settings › Where the price shows and the
       card's ⚙.
       Feedback (Rate Mods): clicking on the last mod again kept counting up "## rated" (now the mods rated this
       session, rm_rated_keys), and the button just clicked stayed lit (focus) on the next mod - only your rating is.
  2.123.1
       Feedback: "I keep getting rate limited, did you change something?" The pace was the same (Balanced, since
       2.119.0 the only one - the user's earlier logs say Balanced too). Today's three 429s (app_log.txt) were all
       Retry-After 600 with no X-Rate-Limit headers - a rule the site doesn't report - at 15, then 14 and 9 searches
       per 5 minutes while the reported limits showed 5-15 of 30. So: 12 per 5 min to start with (was 15); such a 429
       teaches a cap of what was sent minus 3, kept for a day (Limiter.hidden_cap, rate_state.json); for 30 minutes
       after any penalty at most 5 per 5 minutes (COOLDOWN_CAP300; the cooldown was 15 minutes). The rate limits
       window says when it's going slower. It no longer rebuilds itself every second (it flickered).
       Feedback ("conflicting results"): Skip cheap items was on, yet dozens of 1-chaos tablets were searched - each
       had a mod the app's built-in rules mark High, and any High mod exempted the item. Now only your own High (S / A)
       or the players' votes exempt it; the built-in marks give way to the Mod Book's own prices (fewer searches too).
       Feedback (wording): "Search rolls from 90 %" is "Search Min: 10% below" (0% (exact), 5% ... 30% below - the way
       other price checkers say it; FINE kind "below", range_factor unchanged), and "times apart, cheapest to
       highest" is "Warn when prices vary: x - when the highest listing costs this many times the lowest".
  2.123.0
       Craft Helper overhaul, phase 1 (feedback: tablet mods on S-F, "effectiveness by itself is kind of useless",
       "see its price below" with no prices below; then: no prices at all - they move too fast, only your own price
       check can say; no stash search - 250 characters can't hold every keeper; tablets and jewels only). Money
       Makers › Tablet Craft Helper is Craft Helper, with Tablets | Jewels (crafthelper.KINDS: each kind's types and
       steps in one table, for league / 1.0 changes). Each mod has one S-F rating and says where it came from: you
       (Mod Book) > players (3+ board votes) > market (items with it sell clearly above that kind's middle price,
       12+ listings, this league - it only picks the letter) > the app's default > not enough data. The Learned price
       column and both Copy regex are gone; right-click rates a mod (the Mod Book's rating). Check my tablet / jewel
       matches whole lines (crafthelper.item_mods - the stash-search tokens over-matched), one line one mod.
       Bulk Pricing's footer said "Made for tablets, jewels & waystones" while the page prices gear too: it says so.
       UX pass 3 (feedback: price check settings "scattered all over the page"; both pages need an overhaul - 12
       cards, all yes): Settings › Price checking is three groups that name the pages they change (settings_group
       used=): ALL PRICE CHECKS (listings, prices in, valuable mods, how searches are made, Mod Book), SINGLE PRICE
       CHECKS (CTRL+D) (where the price shows, the card's close key - set on Keys), BULK PRICING (CTRL+ALT+C) (skip
       cheap, the list's sound / copy name, copy marker, shortcuts). Fine tuning's rows went to their group; Account
       to General › Your account. Each page's ⚙ opens its group (set_anchors pc_all / pc_single / pc_bulk).
       Price Checks: one verdict strip (pc_verdict_paint: the price, a mark and a word for how sure, how it was worked
       out; Search again (the one orange button), fewer mods, Trade Site, favorites, Clear) - the card and the listings
       no longer say it again (_card_no_price, the why box is Favorites' only); the filters column is 460+ px (40%);
       Recent is a row of chips with All ▾; the row's switch reads Here | Overlay with a ⚙.
       Bulk Pricing: one toolbar row (search first, filters, Columns ▾ - BASE_COLS always, EXTRA_COLS by choice,
       "Est. value" is Price - Re-price all, Pause, ⋯ = Export CSV / Order added / Clear list); Manual Add | Stash
       tab and Delete / Undo in the Items strip (SectionBar.add_left / add_right place widgets made by an ancestor);
       the rules line in plain words with Change…; the Item pane only while one item is picked (bulk_pane), ✕ or Esc
       (hk_min closes it before minimizing).
  2.122.0
       Feedback: Price Checks' "Show over the game" switch was unclear ("misleading and in an odd location" - the top
       right of the listings). It's a row across the top of the page now that says what it does: "When you press
       Ctrl+D on an item in game, show the price  On this page | In a card over the game" (_pc_where_row, SegBar),
       with an ⓘ for the rest; a note says when the key is off or the app stays behind the game. One setter for the
       four places (Settings › Price checking, this row, the card's ⚙, pc_pop_var): settings_page.pc_show_set, and
       each follows (pc_where_paint). Going back to On this page keeps In front / Behind as it was.
       Feedback ("once their data is sent ... it should stay in the database"): POST /mods/forget is gone - Leave and
       delete my data deletes your name, strats and leaderboard times; what was shared anonymously stays in the pool.
       The Privacy text says so. The Unmatched mods workflow prints each pooled line in its log.
  2.121.1
       Feedback: "a bind-able key for the price check overlay to close it" - checked what the others do: PoE Overlay
       closes its latest dialog with Esc (Space closes all), Exiled Exchange 2's Ctrl+D window closes when the mouse
       leaves it (no key). So Esc by default (pc_close_key; Settings › Keys › Price Checks): it only acts while the
       card is open and the game (or the card) is in front, and that press is used up - the game's menu doesn't open
       (pcpop.pc_close_hotkey, on the keyboard watcher). And "a settings cog for the price checker overlay": a ⚙ on
       the card's title bar (OverlayWindow extra=, each button says what it does on hover) opens Card settings - the
       close key, where the price shows, All price check settings… - the same settings as on Settings, one door more
       (as Quick settings on the overlay). A key box can take Esc itself where Esc is the key being set (allow_esc).
       Feedback on unmatched_mods.txt ("whatever requires no input from anyone"): no new option - with Community data
       sharing on, the hourly batch carries the lines your price checks couldn't match (communitymods.unmatched_line:
       the wording with every number as #, and the base type; never the item's name, never a note), each line once.
       The board pools a line once 2 installs sent it (GET /mods/unmatched); a weekly workflow (Unmatched mods) keeps
       a copy so the matcher can be fixed. Listed in What's shared, and why?. (POST /mods/forget - Leave and delete
       dropping the anonymous rows too - was taken back in 2.122.0, feedback: shared contributions stay in the pool.)
  2.121.0
       Items pass (feedback: "you have the entire database ... how are we still having issues with unknown items or
       unknown mods?"). The app's game data (gamedata.json) is built from Exiled Exchange 2's data files - their last
       update is from 2026-09-06, so a base type or unique newer than that was unknown, and only the mod list was
       downloaded daily. Now the trade site's own item list (/api/trade2/data/items: every base type and unique it
       knows) is downloaded once a day as well (engine._load_items, trade_items.json; yesterday's copy at start) and
       fills the gaps (gamedata.TRADE_ITEMS): a base the game data doesn't know is still read (find_base); the uniques
       on a base include the trade site's (uniques_on, for unidentified uniques); a unique name the trade site doesn't
       list is never sent to it ("unknown item name") - any unique on its base instead, with a note; and a kind of
       item the app doesn't know at all is searched by its type when the trade site lists it (type_only_item) rather
       than "can't be price checked yet".
       tools/check_items.py: every base and unique in the game data as a copied item through the reader - its base,
       class and a search the trade site takes, unidentified too (6114 items, none fail).
       From your unmatched_mods.txt: "9(5-10)% chance to Daze on Hit" (a jewel - its mods were matched on the trade
       site's list only; now the game data's wordings are tried next, engine._game_data_id, as gear always did), and
       "{ Enhancement }" read as a mod on a Solar Amulet - any { ... } line (full-width braces too) is a header now.
  2.120.1
       Feedback: the overlay's "Mouse" choice (Drag to move / Locked / Clicks pass through) was confusing. Back to the
       two names other overlays use, side by side in Overlay ↳ Overlay Settings › Options and Quick settings: Lock position
       and Click-through (clicks go to the game). Each works on its own again, as 2.74.3 asked (2.120.0's unlock also
       turned click-through off). ov_click_through_set; OV_MOUSE / ov_mouse_* gone.
       Feedback (a corrupted rare Heavy Belt): unticking Base type said "Any Belts" but the search still asked for a
       Heavy Belt - an item searched on its own base has no category in its plan, and trade.apply_opts only widened
       when it had one. It takes the class's category from the game data now (accessory.belt). And its crafted
       "21% increased Explicit Resistance Modifier magnitudes" was searched as a mod: what it adds is already in the
       resistances' own numbers, so asking for it only hid listings - "... Modifier magnitudes" lines are left out
       (tick one to search on it).
       Feedback: the same for every kind with several bases (checked for each game-data class). And a corrupted item
       has its own switch in Properties - Corrupted listings only / Corrupted or not (_card_corrupt_row; pcpop too) -
       the same setting as Miscellaneous › Corrupted, which was folded away.
  2.120.0
       UX pass, part 2. Feedback: the Rate mods window "drew really janky" and sat in Privacy & community. It's a page
       now, Price Checks ↳ Rate Mods (modules/ratemods.py, ratemods_page.build_ratemods_page): the item kinds on the
       left (Map items, Gear, Uniques you've checked - how many left to rate), one mod at a time on the right, built
       once and only re-filled; keys S A B C D F and ← →. The window changed size between its two views and shared
       self.rm_win with the Expedition tags (remnant_page) - showing remnant prices could break it. Privacy &
       community and the Mod Book's buttons open the page; the Mod Book's lists follow your ratings 1.5 s after you
       pause (they were redrawn when the window closed).
       Feedback: Settings › Price checking had like settings apart. Now grouped - PRICE CHECK KEY (Where the price
       shows), WHICH PRICES (Listings, Prices, Valuable items), BULK PRICING (Skip cheap items, Account, Copy marker),
       FINE TUNING - under group titles (settings_group: bigger, brighter, a rule to the edge; Appearance's THE APP /
       OVER THE GAME use it too). The price check key's four switches in two sections (Over the game, It opens Price
       Checks, Bring the app to the front) are one choice: Over the game / In the app (to the front) / In the app
       (behind the game) / Nowhere - the same three settings underneath (pc_popup, pc_ctrl_c, pc_front), Pictures
       stays a switch; Price Checks' own Show over the game follows it.
       Every section's note is one line: its first sentence, the rest in an ⓘ you point at (chrome.section,
       split_note); Settings search still finds every word.
       The overlay: the mouse on it is one choice in Overlay ↳ Overlay Settings › Options and Quick settings - Drag to move /
       Locked / Clicks pass through to the game (OV_MOUSE, ov_mouse_set; was Lock in Options and Quick settings and
       Click-through in Settings › Appearance; the 🔒 still locks and unlocks). Hide from screen captures and the
       game's window title moved to Settings › Advanced › Over the game; Ask me to rank maps to the Map Library page.
       The clock's format is the one clock setting (Appearance › Clock; the button to the overlay is gone).
       The status bar: one pill, Trade site: ready / wait 0:08 / paused 2:30, with the numbers when you point at it
       (the Search and Fetch meters were jargon). The sidebar lists every child page; their buttons in the page's
       title bar (the same links again) are gone. One orange button a page (Overlay settings and Wealth's toolbar
       Count were orange beside the main one). Page names in Title Case (Mod Book, Map Library, Exchange Rates, Game
       Search, Under the Hood; their old names still open them); BETA written one way; Labs is Beta features.
       Empty pages look alike: chrome.EmptyState - an icon, what it is, what to do, at most one button - on Bulk
       Pricing, Favorites (Open Price Checks), Market Insights, Leaderboards (Open the Overlay) and the Overlay's maps.
       Feedback: an unidentified unique (Ancient Leggings boots) - "trade site refused the search: unknown item name".
       Unidentified, a unique shows only its base, which was searched as the unique's name. Now the one unique on that
       base by name (gamedata.uniques_on), or any unique on it when there are several; a note says which.
  2.119.0
       UX pass, part 1 (the review: every page, tab and settings tab; decisions taken one by one). The overlay's bar
       kept room after the session time for a PAUSED tag and the words "not tracking", so long map names were cut.
       The time now takes only its own width in every style: not tracking shows --:--, paused dims it (the ▶ beside it
       already says so) - _Time.dim, ovlight._lt_time. On the light styles the map's rank rides in the map's text
       (_MapPart, as on Classic); its own slot stood empty whenever a map had no rank. The ⚙ opens Quick settings on
       either click (its All settings… opens Overlay ↳ Overlay Settings in the app) - a left-click used to pull you out of
       the game into the app.
       Helpers (Overlay ↳ Overlay Settings): each says what it does in one gray line under its name (it was only a tooltip);
       its live status shows under that only while it's on. Client.txt not found is one banner over the list with
       Find it… (it was the same red line on Breach, Ritual, Trade whispers ... and pointed at a right-click on the
       Session tracker that's long gone); the duplicate "They only watch and show" line is gone.
       Expedition is always Auto: no Auto chip and no Ctrl+Alt+R key (Settings › Keys) - the watcher shows the tags
       when a remnant's book opens. An area the old key learned is still used (remnant.learn_area / inside gone).
       One name: League Plan - the page (was Game Plan), the helper (was Focus / League Focus), Quick settings and
       the pokes. Its goals are still goals; "focus line" in the texts is the goal line.
       Settings, fewer switches: Pace is gone (always the old Balanced - net.PACE; PACES and the Fast warning gone);
       Accent color and Text size are gone (a theme keeps its own look - style.ACCENTS, apply_look's scale, the
       "restart" note); the start-up screen always shows (its switch sat under Theme); "The overlay only while Path of
       Exile 2 is in front" is gone (it always is). Notes' text size moved onto the note: A− / A+ beside its tabs, or
       Ctrl + mouse wheel in it (was Settings › Appearance › Notes). The old settings are taken out once
       (migrations ux_2119); Expedition's Auto and key with them.
       Privacy: What's shared, and why? still listed "Your rep", and Help rate mods said ratings earn rep - both
       missed in 2.118.0. Gone.
  2.118.0
       Feedback: the helpers' on / off switches on the overlay's bar were "just screen clutter". The bar has none now,
       in every style: one row (Classic was two - the switches over the numbers; HUD_SPOTS 0.056 -> 0.036 of the
       game's height, a Classic bar you'd moved keeps its bottom edge - OLD_HUD_H, hud_one_row), with the numbers, the
       menus (Notes / Calc / Regex / Rates / Vendor ▾), the clock, the lock and ⚙. Every helper starts on for a new
       install (Breach, Ritual, Expedition, Focus, Delirium; Campaign, whispers and Desecration were already) - an
       existing install keeps what it has - and goes off in Overlay ↳ Overlay Settings › Helpers (no On bar column) or Quick
       settings (right-click ⚙: Helpers switch the helper itself, On the bar the menus). Gone with the switches: the
       "which switches?" question when the overlay is enabled, their hover tips and first-time cards (ovhelp.py) and
       Options › Feature tips. The Classic bar's dividers are slimmer (20 -> 14) so the area's name fits beside the
       menus. merged_wants() has "bar" (the bar shows while the overlay is on); "helpers" stays False.
       Ritual: the live count moved from its switch to a line over the bar (the goal bar's lines - Campaign, Ritual,
       Focus): "2 of 4 rituals done", shown in a map once the counter's been read, with an On screen chip on the
       Ritual row in Helpers (ritual_cfg readout). It shows your tribute too once RITUAL.tribute is known - reading it
       off the Ritual page (V) is next. The lines over the bar keep their size (from OLD_HUD_H).
       Feedback: some style previews showed the wrong colors and shapes (they were a mock-up). The preview is the real
       bar now: App.ov_preview draws it with the same code as over the game (its palette with your Colors, frame -
       overlaywin.OverlayFrame / skin_inner, fonts, parts) at a 1440p XP bar's proportions, sample numbers, every click
       binding taken off (_inert); the overlay's own state is saved and put back. Feedback: the theme previews should
       work like that - Settings › Appearance › Theme is a ThemePicker (themepick.py): names (Dark, Light) beside a
       big live preview of the app in the theme under the mouse, drawn from the pack with the app's own parts
       (themes.bar_into, sidebar.draw_marker, flat_spec, the meter, your accent). Both pickers are pickers.ListPreview
       (hover previews after 60 ms of rest, click / Enter / Space picks). The first-start page keeps the small cards.
       Feedback: the community rep system is gone (for now): the icon beside names on Money Makers and the
       Leaderboards, the contributor card, your rep and its switches in Privacy & community, and an admin's Thank
       someone with rep (rep.py, board.set_rep / admin_rep / person). The board (worker) stops counting it and no longer
       sends it; GET /people, POST /me/rep and /admin/rep are gone. Its data is deleted (feedback: "get rid of
       rep"): the rep table and the two account columns it used - rep_hidden and cid_link (an install's link to a name,
       only there to count ratings toward rep).
       Found on the way: the goal bar kept its rows in self.gb_rows - the name of the Gear book's own method - so with
       a line over the bar (Focus, Campaign) the Gear rules list stopped working. Now goal_rows.
  2.117.1
       Feedback: switching to Ashen Rite still closed the app. Its log showed a freeze, not a crash: right after the
       theme change, the desktop's settle step (shell._settle, 0.4 s after the window moves or changes) called
       update_idletasks, which runs layout jobs until none are left - and a page that kept laying itself out again
       never let it return, so Windows marked the app as not responding. It now waits for the layout jobs already
       queued with after_idle (_settle_now), so the window keeps answering whatever a page does. Ashen Rite was the
       only theme with Sylfaen, a font with very tall lines (how text measures decides how pages wrap and scroll);
       its titles and numbers use Georgia now. And a layout loop is written to the app's log once a run
       (style._layout_watch: one widget resized LOOP_LIMIT 150 times within a second - its place in the window, its
       kind and the theme; no text from it), so the next one says where it is.
  2.117.0
       Nothing is stepped over silently any more: the 215 `except Exception: pass` (an error the app carries on
       past - a window already closed, a Windows-only call, a file it couldn't read) now call buglog.caught(), which
       writes a [caught] entry to the app's log: where in the code (file, function, line, the last 4 calls) and the
       error's type only - never its message, which can hold an item or a name. Once per place per run (a set
       lookup after that - safe in timers and loops), at most 100 places a run. Not in the "this week" counts (they
       aren't problems you saw); Report a bug sends them after the errors, crashes and freezes, while there's room.
       The narrow catches (tk.TclError for a closed window, OSError for a file) stay as they are. The first one
       found: a window's withdraw() ran before its ghost list existed (shell.hide_ghosts).
       Every one-time change to your settings and data is one ordered list: soe2/migrations.py (STEPS - id, version,
       stage "settings" at load / "app" before the windows, the function, its old flag). Were spread over app.py
       (copy_2983, gear_plus_299, tier_only_2114, rules_scoped_26 - migrate_rules_once), config.py (status_ib_2792)
       and market.py (modbook_imported, at import). Done ones are listed in migrations_done; a step done before under
       its old flag counts and the flag is kept (an older build put back skips it too). A failing step is logged and
       tried again next start, 3 times at most, and never stops the others; settings are saved once per stage. The
       files' own format upgrades (ledger, strats, mod rule keys) stay where they're read.
       No window work from a background thread (Tk isn't thread-safe - a widget touched from another thread can close
       the app with no message). Every thread was followed: the keyboard hook, tray, engine, screen watchers and
       price fetchers already hand results back through ui_q. Five places called root.after from a worker (bug report
       send, Money Makers' board and live list, board moderation, a community card) - they now use App.run_bg(work,
       done) / App.on_ui(fn, ...): queued, run by poll_events on the window's thread (ev_call). ignore_clip builds its
       list whole before swapping it in (the window's thread reads it). tools/check_threads.py follows every
       threading.Thread target (and the methods it calls, two levels) and fails on a Tk call - run in Checks.
       app.py split, a part at a time (it was 6,400 lines): Settings - the window, every tab and their handlers (48
       methods, 1,100 lines) - is soe2/settings_page.py (class SettingsPage, mixed into App like the other pages).
       Moved as they were; helpers the whole app uses (open_path, restart_app, dlg_parent, league / pace / pause,
       relook, the title bar) stay in app.py.
  2.116.0
       P10, the Settings page pass. Seven tabs: Hotkeys and Chat commands are one Keys tab - hotkeys first, then a
       Chat commands section with its rows (Go to hideout, then the commands; "+ Add a command" shows the next empty
       one) - and their keys are set there once (Hotkeys lists them under CHAT COMMANDS, "set below"). Old links
       (open_settings_tab "Hotkeys" / "Chat commands") open Keys. Price checking gets "Your price check key"
       (Ctrl+C, come to the front, pictures - out of Hotkeys); General › Window gets Messages stay for and Minimize to
       the system tray (FINE_WINDOW, out of Price checking's fine tuning).
       Overlay style (feedback: the cards were "a visual indicator of the theme, if you can figure out a better
       system, go for it"): ovstylepick.StylePicker - the 14 styles as names grouped Classic / Light / Ornate beside a
       live preview of the bar drawn in each style's own palette (ovlight / ovskins / hudart); hover previews, a click
       picks. Replaces the dropdown and its 10-line hint.
       Always on top and Minimize to the system tray are off for new installs (saved settings keep theirs). Restart now
       shows only after a text-size change (a grayed-out main button looked broken). Updates' switches shorter; the
       note says which builds you get. What's new: "What's new · version" and "you had ...". Quick start: dots.
       Advanced: Problems (this week's count from the app's log, Report a bug, Open the app's log). Developer options,
       off and hidden until switched on (roadmap): Debug mode - every trade-site request with its answer and time in
       the app's log (kind debug, cleaned the same way) and a debug line in the status bar; Unmatched mods - every mod
       in unmatched_mods.txt beside the closest trade wording, newest first, no repeats (Copy all, Clear the list).
       Your data shows the folder as %APPDATA%\StashOfExile2 (no Windows user name on screen).
       Privacy & community: shorter notes, a line when nothing of yours is on the board, links to TOS.md / README.
       About: header colors from the theme; credits name each project's author.
  2.115.0
       One bug log for the whole app (feedback: "we need one global bug logging system", and Report a bug should
       carry any crash): soe2/buglog.py - app_log.txt in the data folder, one entry per problem, kind error / crash /
       freeze / slow / net. log_error, save_json failures, HTTP errors and rate limits (were error_log.txt,
       http_error_log.txt, rate_limit_log.txt), and the hang / slow / crash reports all write there; buglog.install
       catches anything uncaught on the main thread, any background thread (threading.excepthook) and in Tk
       callbacks (report_callback_exception - they went nowhere before). Every entry: folders cut to file names first,
       then privacy.scrub_names; the same error within 30 s once; capped at 512 KB (the older moves to
       app_log.old.txt). Report a bug: "Add the app's log" sends buglog.diagnostics() - the last crash / freeze /
       slow report from the past week and the newest log entries, newest first, at most 12,000 characters - with a
       line saying what the log holds this week. After a crash the message has Report it (the form filled in) /
       Not now. report.py's problem report takes app_log.txt too.
       Builds use exact versions (requirements-build.txt - release.yml and build_exe.bat), so a library's new release
       can't change a build by itself. Checks run ruff (undefined names, broken code) on every pull request.
  2.114.3
       Feedback: switching to the Ashen Rite theme closed the app on another player's PC (latest version, fresh
       install) and no file was written - the hang report only covers freezes. Not reproduced here (every theme to
       Ashen Rite, overlay on, pages open, every style). hangwatch.crash_start: faulthandler writes where the app was
       when it dies (crash_raw.tmp); the next start turns it into crash_report.txt - file NAMES, function and line,
       the fatal error's kind, and the last steps (crash_steps.tmp, written on each step) - then a toast says so.
       Paths are cut on either slash, so no folder or Windows user name gets in. style.relook marks its steps.
       Scan stash (feedback: "led me through all the prompts but then did nothing"): after the last tab the app comes
       to the front on Wealth and the check window opens centered on it, on top once and focused (it opened behind the
       game); nothing read says so in a toast (it was a Wealth status line you couldn't see from the game).
       Feedback: it came up on the other screen - "it should always appear over the app". style.over_app (center_over
       once built, on the app's monitor) on the check window, the Rate mods picker and every dialog that had no place
       of its own: Favorites' group / edit, Ledger, Map library's import question, Money Makers' two, the board's
       moderation windows, Report a bug.
       Wealth (feedback: Ancient Potent Liquid Contempt "not on poe.ninja", and scanned items not all in the total):
       the trade site's bulk exchange is asked about EVERY stack poe.ninja has no price for (bulk_missing had a cap of
       30 - a scan of eight tabs has far more), the list fills in as it goes, and the snapshot taken before they had
       prices is replaced once it's done (snapshot replace=True). Why a stack has no price says which: asking the
       exchange, too few offers, or unknown to both (why_unpriced). The totals line says how many aren't in it.
       Scan stash (feedback: "it didn't count the divs in the wildcard slot, the 1193"): Currency's 2 x 7 wildcard
       slots are read - what each holds is told by its picture against the tab's fixed slots in the same shot
       (stashread._icon / _same_item, a few pixels of slide; 0.75 and a clear lead), and the ones it can't place
       against every tab read at the end (match_wild). Pictures stay in memory and are dropped after. One it still
       can't place is shown as "? (wildcard slot)" in the check window: double-click to name it (user: the white one
       is Sacred Bloom - on no tab's fixed slots), and its picture is remembered in stash_icons.json (40 x 26, an
       item's look only) for next time (learn_icon / learned_icons). Same-name counts add up on Save (5000 + 1193).
  2.114.2
       Scan stash (beta) reads the Expedition tab (the user's shots and every slot's name): stashlayouts.EXPEDITION -
       Logbook, the four Sagas (Aldur's slot left out: out of the game for now), Shattered Triskelion and The
       Triskelion Reforged (big slots), the three Verisiums, four Crests, 13 Alloys, four Fluxes. Stacks over 9,999 show
       as "12.2K": stashread has K and "." shapes and reads it as 12,200 (_value; _could_be keeps a stray "." or "K"
       match from taking a run over). Breach › Wombgifts stays out (they don't stack). test_v21010 extended; the
       reference shots stay in the local test kit (wealth data).
       Scan stash reads the Ritual tab too (the user's shot, every slot named): stashlayouts.RITUAL - An Audience with
       the King, Head of the King (double wide), Call of the Shadows and 28 omens; its two empty slots held items out
       of the game - left out.
       And the Essence tab (82 smaller slots, 63 x 63: ten Lesser / normal / Greater / Perfect lines on the left, nine
       on the right, the six special essences in the middle; the empty big and small middle slots aren't read).
       stashread: a tab's edge match is weighed by how many of its slots hold something there (locate - Essence's
       dense grid matched every panel a little and took Expedition); white strokes must be neutral white (feature - a
       Perfect essence's pink glow read as ink); a near-tie between runs can prefer the longer (TIE, 0 for now).
       And Fragments › Fragments (20 slots: crisis fragments, splinters, breachstone, Origin Spark / Cradle, the
       Triskelions, the King's items, Simulacrum, Raven's Reflection, Kulemak's Invitation, the three Fates). Items
       that also have a slot in their own tab are added up on Save (stash_scan_save), not overwritten. A slot whose
       item hides its backing (Weathered Crisis Fragment) still counts with a clear number (read_number sure=SURE).
       Breach's sac slot uses the game's name, "Breachlord Sac".
  2.114.1
       Wombgifts (feedback: "use trade site for the 5 types of wombgifts, they do exist"): gear.type_only_item -
       TYPE_ONLY_CLASSES ("Wombgifts") items are a price-check item searched by their type alone, as the site's own
       search for one (no corrupted filter); engine._price_gear lets a Currency item (and a magic base with its item
       level filter) search with nothing ticked. Other single currency items keep the going-rate toast (2.114.0).
       Price check card over the game (feedback: white / magic bases didn't price the same as in the app): a
       PROPERTIES part - Base type (ticked = this base, unticked = any of its kind), Item level, Quality, Sockets with
       Min / Max - the same rec["opts"] as the app's card (search_opt_set); Enter searches again.
  2.114.0
       P8 + P9 page passes (findings + mockup first; feedback: Tier the only rating, Rates plain, calculator plain).
       Listing order lab removed (an admin tool, done its job): orderlab.py, orderlab_page.py, modules/orderlab.py
       and the clipboard hook; shell.admin_on stays for any later admin tool. orderlab.json on a PC is left alone.
       Mod book: one rating, S-F (S / A = High, B / C / D = Normal, F = Ignore) on Tablet / Jewel / Waystone / Relic
       rules as on Gear rules - the Impact column and the High / Normal / Ignore buttons are gone; tiers_selected and
       a double-click (steps S ... F) use ratemods.apply; a row not rated by you reads "A · auto" (mb_rating). Once
       (tier_only_2114, mods.migrate_tier_only): a tier you gave decides High / Normal; an Ignore keeps F and drops
       its old tier. Export / Import / Remove imported under More ▾ (mb_more, listkit's menu look); the counts sit in
       the section strip (chrome.BarNote); the help line wraps to the window; Learned is the last column.
       Rate mods picker: grouped (Map items, Gear, Uniques you've checked), four across, "N to rate" with a bar,
       the gear part scrolls when it doesn't fit, centered over the app (it ran past the bottom).
       Under the hood: Paste item / Price it / Clear (Check gone - typing in the box reads it); a one-line intro.
       Exchange rates: currency names (ovrates.cur_name, one list for Rates, Exchange Helper and the overlay), plain
       small numbers (fmt_worth: no 4.762e-05), "In divines" / "Volume (div)"; the status bar updates as soon as a
       fetch ends (ev_rates_done - it said "none yet" for up to 30 s).
       Notes: opening it shows the note over the game and says where it lives (notes_open); switched off, it says
       which switch. Calculator: starts blank (no "0"), Recent in the Style's font; its "switched off" message names
       today's place.
       Price check key on a single "Rarity: Currency" item with no Stack Size (feedback: a Signet Wombgift did
       nothing): wealth.parse_currency_item -> stack_price(name, 1, loud=True) - poe.ninja or the bulk exchange, shown
       in a toast; the same on the plain Ctrl+Alt+C path.
  2.113.2
       Island rumors (rumours_read.txt from a real card: "Nothin' to drink..." read as "Wodviw' to c(riwkv.."):
       lines are compared by letter shape too (rumors.SHAPE: n/w/u/v/h/m, t/d/c/l, o/a, i/j) - rumors 0.88+, the
       card's other lines 0.56 or less, two rumors at most 0.64 alike; a match needs a 0.15 lead over the next.
       What's new never claims a fix (feedback): notes say what changed and that it should help; recent ones reworded.
  2.113.1
       Price Checks: a "Show over the game" switch on its header (feedback: it belongs there) - the same switch as
       Settings › Price checking › Over the game (pc_pop_var, one BooleanVar for both). It left Settings › Hotkeys
       (feedback: the wrong place).
       Island rumors (feedback: the middle of three still missing): a rumor no single line matches is looked for in
       the card's whole text (rumors.rows, WHOLE_MATCH 0.8 - Windows' reader can split one over two lines or join it
       to the next); the card is read at twice its size; what was read goes to rumours_read.txt (the card's words only,
       local) so a miss shows why.
  2.113.0
       Price check in a card over the game (a sample; soe2/pcpop.py - Price Checks in the app is unchanged and still
       gets the item). Settings › Hotkeys › Price Checks › "Show it in a card over the game" (off by default): your
       price check key copies the hovered item once, as before, and the card opens over the game instead of the app
       coming forward. The card: the item (name in its rarity color; rarity, class, base, item level, quality,
       corrupted), the price and how sure it is, the mods searched - tick / untick, Min / Max to type in (the same
       values as the app's card; Enter searches again) - and the cheapest listings, each a one-line summary that
       opens to the whole item (implicits, every mod, corrupted). Search again, Trade site, Open in app. Drag it by
       its title, resize from any edge - both remembered. The overlay's Style throughout (its scroll bar and buttons
       too). Other sellers' names show as on the app's card; your own account never does. It takes the keyboard
       when you click a box (to type); it never redraws under your typing. Windows and Linux / Hyprland.
       Readable in every overlay style: on a light style (Gilded) the game's rarity / mod colors are darkened,
       same hue, to 4.5 : 1 (pcpop.ink); a test checks every line in all 14 styles.
       Prices count each seller once (core, every search): trade.collapse_sellers keeps a seller's cheapest
       listing with how many times they listed it ("listed N times" on the cards); with fewer than 5 sellers in the
       first 10, listings 11-20 are fetched (trade.MORE_IDS) - one seller's seven copies no longer make up "the 5
       cheapest". Price Checks, Bulk Pricing, Favorites, the card over the game and Money Makers' costs. A mod's
       default Min never goes under its own tier's lowest roll (mods.min_for: 90% of a low roll searched the tier
       below). Ideas from Exiled Exchange 2 (MIT), written our own way - credited.
       Island rumors (feedback: only two of three showed; the panel was big and clunky): a rumor read on one line
       with the card's "Island Rumors" heading now matches (rumors._score: the best stretch of the line); each card
       is read up to 3 times and what's found is put together (READS); the panel is small, like the Runeshape tips -
       a title, then a rank badge, the island and the rumor per row.
  2.112.5 (hotfix)
       The Campaign / Focus line: dragging it by its text no longer opens the route card / Game Plan - a click opens
       it only when the press didn't move (merged_page.click_not_drag, also on the bar's Focus text).
  2.112.4
       Theme changes on Windows (feedback: 1-3 s each, and quick clicks through the cards crashed the app): a burst
       of card clicks swaps once, 200 ms after the last (pick_theme(wait=True) from the cards; code / tests swap at
       once); the overlay over the game is rebuilt on a theme change only in Classic - the one style that takes the
       app theme's colors - instead of closing and reopening every window over the game on each swap.
       Flanks is shown as Split (the key stays "flanks"). The Campaign / Focus line: unlocked, it can always be
       dragged - by a ⠿ grip at its left (see-through styles had nothing solid to grab) or its text; dragging a docked
       line undocks it and saves the spot (in Split the bar's halves can't move, so a docked line was stuck).
  2.112.3
       Quick settings (right-click the cog): the Style list closed the moment it opened. On Windows the open list
       takes the keyboard; focus_get() can't name it (it isn't a tkinter widget), the KeyError read as "focus
       left", and the box closed under it. Now Tk's own focus name is checked (ovquick._ovq_focus_gone).
       The update question shows the notes as plain lines (plain_notes) - GitHub's ## / ** / footer showed raw.
       Theme changes: the overlay's measuring fonts are made once per family / size (ovlight._lt_fm) instead of
       on every build; a theme change slower than 1.5 s writes slow_report.txt (hangwatch.profiled: the 30
       biggest steps as file:function:line, local only) - theme changes are still slow on Windows; this is to
       find where. 2.112.2's What's new no longer claims they're instant.
  2.112.2
       Fixed: changing the app theme froze / crashed on Windows (found with 2.112.1's hang_report.txt). Every title
       bar's redraw (about 100) asked Windows for the PC's whole font list (themes.head_font -> font.families());
       paint_titlebar's update_idletasks ran them all, for minutes. The list is read once and the answer kept per
       theme. Also: paint_titlebar forces pending redraws only before the window first shows, and the auto-hiding
       scroll bars (Settings, the Price Checks card) can't flip back and forth forever (style.SbGuard: 4 flips in a
       second = stays shown until the page settles) - that loop was found at some window widths.
  2.112.1
       Not responding? soe2/hangwatch.py: a tick on the Tk thread every 0.5 s; if it stops for 8 s, a watcher thread
       samples the main thread three times and writes hang_report.txt to the data folder - file name (no folders),
       function and line only, plus the last steps (theme change: re-color / title bar / overlay rebuild). Local
       only, never sent. For the theme-change freeze on Windows (not seen on Linux).
       Switches on a card take the card's color (style.py wraps ttk.Checkbutton): plain ones showed a dark box
       behind their text (Settings › General › Updates).
  2.112.0
       Overlay ↳ Overlay Settings › Helpers reworked (feedback: hard to read): one table, one row per helper - on / off,
       the name with one short line of what it's doing now (full text on hover), its own options as chips (filled
       when on, outlined while the helper is off), On bar and Remind columns (a dash where it doesn't apply), Test /
       Open. Grouped In maps / Play / Trading & more. Sound for every helper sits at the top right. Gone: the six
       "Switch on the bar" and two "Remind me when I leave the map" lines, the second row of switches under each
       helper, the long status sentences.
       Dropdowns: every list opens above "always on top" windows (style.py wraps ttk.Combobox). Quick settings' Style
       list opened behind the box over the game, so the click closed it and picked a style blind.
  2.111.0
       Ornate overlay styles, wave 2: Totem (timber frame, red war-banner bands, hide tabs), Hellfire (rusted
       iron, rivets, ember-gold Metamorphous), Psionic (gold over deep-blue glass, cyan light, Marcellus) and
       Guildhall (oak, brass, parchment tabs, IM FELL English SC). Same skin system as wave 1 (soe2/ovskins.py).
       New bundled OFL fonts, shipped unmodified: Metamorphous, Marcellus, IM FELL English SC.
       What's new card: big changes are hero rows (icon, title, one line, a link to the page); the rest fold under
       "▸ N smaller changes" (area · line). NOTES entries are {"big": [...], "small": [...]} with the big / small
       standard written in soe2/whatsnew.py (max 3 big per card; skipped updates merge). Old list entries show as
       small lines. The card, About › Version and the release notes read the new form (tools/release_notes.py).
       Theme: the What's new card, the Insights item card, the Price Checks / Session / Wealth strips, the BETA tag
       and Game search's highlight use theme tokens (they kept fixed colors in every theme). tools/check_theme.py
       (on every PR) fails any color written into the code that stays the same in every theme.
       Overlay settings: the Colors picker is removed (it didn't apply reliably and was one more box); the light
       styles always use their default set (Exile Gold); ornate styles keep their own.
       Toasts: action buttons wrap onto another row when they don't fit (the update note's three buttons squeezed
       the left one, Show, into a blank box).
  2.110.0
       Five ornate overlay styles (wave 1 of 2, from the mockups): Herald (crimson title plates, gilt line, iron
       tabs), Gilded (white marble, gold leaf, umber text), Warbanner (a heavy gold frame with corner caps, royal-blue
       bands), Verdant (forest green, aged bronze) and Gloom (smoky slate, pewter, ghost-pale small caps). Each is a
       skin over the Slate layout (soe2/ovskins.py): Game bar and Panel, every window over the game, scaled to the
       resolution. They keep their own colors (Colors doesn't apply). Classic stays the default.
       Fonts bundled (SIL OFL, soe2/fonts): Cinzel, EB Garamond, Cormorant, Marcellus SC - loaded for the app only
       (Windows: a private font resource; Linux: fontconfig app fonts), never installed (soe2/fonts.py).
       The bar's switches: Campaign | Focus | Breach | Delirium | Ritual | Expedition, room for new ones after.
       Avg: (no period). Right-click the cog: Quick settings picks the Style; the Overlay ON | OFF row is gone there
       (the overlay's own page keeps it).
  2.109.0
       Regex: the option cards are one card with a row of buttons per setting (Rarity, Type, Uses remaining…), the
       way Money Makers' filters look. ★ first, Only ★ and Select valuable are gone (★ still marks valuable mods).
       PoE 2 has no find key: every "copied" hint now says Ctrl+V into the stash (or shop) search.
       Everything over the game follows the overlay's Style and Colors (Settings › Appearance › Overlay settings):
       Notes, Calc, Regex favorites, Rates, the goal bar and every card - they used the app theme or the Classic
       colors before, so none matched. Windows keep a box in Hairline / Flanks. One palette: App.ov_palette.
  2.108.0
       Polish 7 - P4 + P5 + P6 + P7: the overlay and its children, Money Makers, Regex, Game search.
       - Right-click the overlay's cog = Quick settings, a small box over the game (soe2/ovquick.py): Overlay, Sound,
         Lock overlay, Hide from screen captures, and Overlays - chips for what sits on the bar - plus All settings….
         Left-click still opens Overlay ↳ Overlay Settings. Esc, ✕, a click elsewhere or the cog again closes it.
       - Overlay ↳ Overlay Settings › Helpers: each helper's options sit on their own line under it and wrap.
       - A tooltip can't stay stuck on screen when its widget goes away (style.Tooltip watches it).
       - Overlay: "No maps yet this session" text over the empty maps list.
       - Expedition: the Island rumors show in one panel beside the card (was one bar per rumor).
       - Game Plan: Goals by phase as tabs (+ Add adds to the phase on show; "I'm here now" moves you); Stockpile,
         Map supplies, Farm plan and Pokes (with Build lock) as tabs on the right; the stockpile form tidied.
       - Leaderboards: two toolbar rows (boards + sharing, then filters); empty texts on both lists.
       - Map library: ranking is one compact S A B C D ✖ group in the toolbar, then Clear and Share ▾.
       - Price Checks: Recent is a panel under the item card (was a column on the left - too crunched).
       - Overlay bar: no "-" after Map: / Avg.: while there's nothing to show yet.
       - Bulk Pricing: a tick or a filter on the item card waits for Search again (it searched on every click) and
         is painted in place (the whole card was drawn again) - as on Price Checks.
       - Money Makers: + Add my own, with Import file… and Download Format in a ⋯ menu beside it.
       - Regex: Tablets / Waystones / Relics / Jewels / Gear items are tabs; the Regex key line sits under the
         search; rarity / type / options are toggle chips; the how-to text is a ? tooltip.
       - Game search: the empty page shows Try examples (click one) and your recent searches (Clear empties them).
  2.107.0
       Polish 7 - P2.5: Controls refresh (mockup with 3 switch directions in all 10 themes, then built; picked: B).
       - Every on / off switch (every ttk Checkbutton) is a 68 x 24 segmented ON | OFF box: the chosen half lit
         (accent / raised face), straight edges, monospace words (style._switch_img; same widgets and variables).
       - Buttons are flat in every theme (themes.flat_spec): one color, 2 px corners, no gradient or bevel - normal
         a raised face (accent edge on hover), primary the accent, danger an outline in the theme's danger color.
         A pack can keep its own with "buttons": {"flat": false}.
       - Price Checks in 3 columns: Recent is a list on the left (item, price, time) - was a dropdown.
       - Overlay: one ON | OFF switch (was Overlay Enabled | Overlay Disabled); no "In game: Pause / resume" line;
         Overlay ↳ Overlay Settings › Helpers: one Sound switch for every helper's alert (each row had its own).
       - "Open on trade site" reads "Trade Site" everywhere.
  2.106.0
       Polish 7 - P3: Wealth (findings + mockup, then built). Synced stash tabs are gone (feedback: "clean start"):
       no Stash tabs page, no Sync / Stop / Re-check magic & rare items, no odd-price setup; what tabs read is
       dropped once (WealthStore init: tabs, items, results, rare prices and the history they were part of) -
       counted stacks stay. Price Checks › Add items from: Stash tab stays; its "Count it in Wealth" link is gone.
       - Count currency is the main button, Scan stash (beta) beside it; More: Update prices, Add currency by hand,
         Export history / items, How Wealth works.
       - The first time: two cards side by side - Count currency, Scan stash (either or both).
       - Items: From = Counted / Scanned / Added by hand (set_holding src), with a filter bar for each.
       - Snapshots: What happened (Counted currency, Scanned stash, Prices updated ...), the change since the one
         before, and the picked one beside the list - each kind and its change (or two compared).
       - The chart uses its height (it started at 0, so the line was flat); the status line says when you last
         counted and how old the prices are. Empty texts and How Wealth works say count / scan, not sync.
       Also (feedback, a Mageblood trade-link favorite): the legacies ticked on its card weren't searched - their group
       came from the link switched off ("this whole group"), so the whole group was left out. Ticking a stat now
       turns its group on. Seller: a link favorite follows your Seller setting (Instant Buyout) unless you pick one
       on its card (fav_status; a link's own "Any" doesn't count). Open on trade site: a link favorite opens the
       card as it is now (the search in the link, ?q= - nothing is searched from the app); Price Checks, Bulk
       Pricing and item favorites search changed filters first, then open (open_rec_trade, ev_priced).
  2.105.0
       Feedback: the card still flickered on every box that isn't a mod - Base type, Quality / Waystone tier /
       Item level / Sockets / requirements, Corrupted / Mirrored / Desecrated ..., Seller / Priced in, and
       "fractured / desecrated only". 2.103.3's in-place painting now covers all of them (_card_mark,
       _card_box_paint): on Price Checks and Favorites only that box changes; the MISCELLANEOUS count follows.
       Overlay: Rates ▾ on the bar (like Notes / Calc / Regex): the switch puts it there, the button opens / closes
       the exchange rates window (its x hides it). The labels read Map: and Avg.: .
       Leaderboards: the League box names the leagues (current first, then others seen, then All leagues); Show:
       Top 5 / 10 / 20 / 30 / 50 / 100 (kept).
       Island Rumors: the log's last lines say where you are when the watcher starts (started in your hideout, it
       never ran); a card read while still opening is read again until its rumors show; its first error is logged.
       Price Checks (feedback: an amulet's exact search found listings without its +186 Mana): when every ☑ mod must
       match, they're searched like ★ mods (gear.build_query) - the "count" over each mod's several ids (explicit,
       fractured, desecrated) let one mod count two or three times. "All but N" steps count one id per mod.
       Amulets: "Quality (Caster Modifiers): +40%" is the quality; "{ Enhancement }" heads the anoint - an enchant
       ("Allocates Paragon", enchant.stat_2954116742 with its notable); " — Unscalable Value" is dropped first.
       Searches: Balanced 15 per 5 min (was 8), Fast 20, Gentle 8 (net.PACES cap300).
       Listing marks are gone (feedback: nobody uses them): no Mark listed / sold / removed buttons or menu items,
       no LISTING STATUS block, no Show box (every item shows); Market Insights has no Status column.
       Market Insights: Gear / Tablets get a slot / tablet-kind box (the full list, subs_for / sub_match); the item
       is drawn like a trade-site card (ins_draw_card: picture - learned per base from listings, icons.json - name
       band, properties, item level, tiers, mod colors, worth); "Open on trade site", "Remove".
       Exchange rates: Convert sits under Exchange Helper; no "Check for new rates every hour" switch (always on).
  2.104.0
       Polish 7 - P2: Favorites and Market Insights (findings + mockup, then built).
       Favorites:
       - The empty list says how to add one (it showed nothing - a 2.103.4 refill skipped the note).
       - The link box: a "Trade link" label and a gray hint while empty; the long help line is shorter.
       - The list is 300 px (Price / Checked fit), the card at least 460 px (mods wrap less).
       - Open on trade site sits beside Search under the card (item and link favorites).
       - A check that found nothing (or couldn't search) shows the Price Checks "why" box with Search again /
         Search with fewer mods (pc_ticked follows the card that shows the item).
       - Undo shows only with something to undo (undo_button(..., **pack) hides it otherwise); a failed price "-".
       Market Insights:
       - All and Gear tabs: priced gear showed nowhere (kind_match).
       - No Refresh button or page title (the breadcrumb names it); one short line instead of the paragraph.
       - Columns fit (Typical, Status); empty tables say how they fill; "Priced" shows once; the item's buttons
         sit under its card (toasts covered them at the bottom), the fitting one is the main button.
       Also: the waystone tier row reads "Waystone tier:" (the boxes hold the numbers).
  2.103.4
       P1 feedback, round 4:
       - "Has 1 Charm Slot" was read as a fixed choice (the game data writes the one-slot wording as "# = 1", like
         Mageblood's Legacy of Gold), so it had no Min box. A wording with "#" in it is a number, not a choice.
       - Waystones: the tier went back to 15 on Search - the boxes were kept only on Enter. Now every key keeps them,
         like the mods' Min / Max.
       - Favorites still flickered: every save (400 ms after a change) built the whole list on the left again. Now
         when the rows are the same, only their words change.
       - Bulk Pricing's item panel paints a tick in place too (its own card rows, like Price Checks and Favorites).
  2.103.3
       P1 feedback, round 3:
       - Price Checks: every tick still flickered - 2.103.1 / 2.103.2 still built the whole card again on each one.
         Now a tick or a star repaints only that row (box, check mark, text color, star, Min / Max on or off) and the
         Search button's "filters changed". Nothing else is built again.
       - Waystones: the tier range did nothing - the search was for the base "Waystone (Tier 15)", which holds the
         tier. A range other than its own (or an unticked tier) now searches category map.waystone with map_tier, as
         the trade site does.
       - Favorites flickered the same way, on every action: a tick or a star is painted in place there too; other
         card changes build the card out of sight and swap it in, and keep the listings. Each view keeps its own card
         rows (Price Checks and Favorites shared them).
       - Favorites: Add trade link asks for the bookmark's name (Cancel = not added).
       - Price Checks and Favorites show Bulk Pricing's "Staying under the trade site's limits" line.
  2.103.2
       P1 feedback, round 2:
       - Price Checks: a tick (or a typed Min / Max) redraws only the card - the listings beside it stay put (redrawing
         them, pictures and all, was the flicker 2.103.1 didn't catch).
       - Waystones: a Waystone tier row under Properties (ticked: the same tier, as before; type a range, e.g. 14-16,
         or untick it for any tier - the trade site's map_tier).
       - A mod the trade list words without "+" (Monsters have +21% Critical Damage Bonus) is found: when the exact
         wording isn't on the list, it's matched without "+", "to" and "increased" - only when exactly one stat fits.
       - Rows that wrap in a narrow window (2.98.0) lost their gaps: Tk hands a padding pair back as a tuple and it
         was read as none. Read right now - Clear filters and Order added (and every such row) have their room back.
  2.103.1
       P1 feedback:
       - Bulk Pricing: the list filters are on screen again (no Filters ▾), Export CSV is back on the toolbar and Clear
         list next to Delete (the ⋯ menu is gone). Mark listed / Mark removed / Delete light up the moment rows are
         picked (they waited for the item panel).
       - Price Checks: ticking a mod no longer flickers - the new card is built beside the old one and swapped in.
       - Waystones: every mod with a number takes a Min / Max on the card. The search uses it only when you type one
         (until then it searches "has this mod", as before).
       - A narrow window: a long mod no longer runs under Rate ▾ - rows keep the Min / Max column's room.
  2.103.0
       Polish 7, P1 - Price Checks and Bulk Pricing (the page standard; feedback on the findings + mockups):
       - Price Checks: a check that finds nothing says why under Listings ("No listings matched these filters" - how
         many mod filters are on, what to try) with Search again and Search with fewer mods (unticks the last ticked
         mod and searches); a failed search says Couldn't search, the reason, and Search again. Kept as they are (your
         call): Search / Clear / Add to favorites / Open on trade site under the card, the header buttons, the card's
         width (a third of the page since 2.97.0).
       - Bulk Pricing: the list filters (Show, Category, Rarity, Type, Order added) open from Filters ▾ (it counts the
         ones set and stays open while one is); Export CSV and Clear list moved into ⋯ (one red button left: Delete);
         Mark listed / Mark removed / Delete light only with rows picked; the Status column says where pricing is
         (✓ Priced, ! Review, ⧗ Pricing / Waiting, ⏸ Paused, ✖ Error) until an item is marked; the ★ column's header
         is just ★; an empty total reads 0 div (not 0.000 div).
       - One font in the status bar and the card's price line (Segoe UI; its digits are fixed-width).
       - Not changed: ★ and Rate ▾ on the card stay apart - ★ is "must match" on this item, Rate is your rule for every
         item like it. Fractured / desecrated only stays the small line under its mod.
       Roadmap: P3 removes the public stash tabs from Wealth, P8 the Listing order lab; P10 adds Settings › Advanced ›
       Developer options with a Debug mode (Windows and Linux).
  2.102.0
       Wealth > Scan stash (beta, may not work): count currency by looking at the open stash tab instead of Ctrl+C
       on every stack (stashread.py, stashlayouts.py, stashscan_page.py). A card over the game asks for one tab at a
       time - Open your Currency tab > Start reading - then Abyss, Delirium and Breach (Catalysts page); Skip tab and
       Finish at any time. One picture per read, kept in memory and dropped; the card is left out of it.
       - The panel: each known tab's slot frames, drawn as boxes, matched against the picture's edges (left 60% of
         the game, worked at ~720 px high); the best tab wins - the wrong tab open says which one it looks like.
       - A slot is filled when its dark-blue backing shows; its number is read from digit shapes (white with a black
         outline) matched along the top edge - the longest run on one baseline. Wildcard slots, shards and the
         crafting hole are skipped.
       - A check window lists what was read (? = filled but unreadable); fix numbers (double-click), drop rows
         (Delete), Save sets them in Counted by hand (replacing those counts; the rest kept). Nothing saved before.
       - Only digit shapes and slot boxes ship; no picture of anyone's stash. tools/stash_slots.py and
         tools/stash_glyphs.py add tabs and rebuild the digits from your own shots (keep those local).
       Roadmap: Ritual, Expedition, Essence, Fragment and Socketables tabs for the scan.
  2.101.0
       Overlay styles (from the mockups; feedback: "a lightweight one is needed desperately"): Settings > Appearance >
       Overlay settings > Style - Classic (the stone-and-bronze Game bar and Panel, as before) or one of four light
       looks drawn with plain canvas lines and text (soe2/ovlight.py; no Pillow artwork, nothing re-rendered when the
       game window changes size), each as a Game bar and a Panel:
       - Hairline: no box - outlined text and one thin accent line; one row, or two when the XP bar is too narrow
         (the switches and menus on top).
       - Slate: a flat box with thin dividers; a switch that's on is underlined (a bar on its left in the Panel).
       - Flanks: no box - the numbers right of the life orb, the switches left of the mana orb (two small windows,
         the middle of the screen stays clear); the Panel stacks the two halves.
       - Micro: the smallest - the times, the rank and the switches as lettered squares (Ritual shows its count).
       Then Colors: Exile Gold (the Classic bar's own), nine theme packs' colors (Gilded Crypt, Sunstep Temple,
       Emberforge, Ashen Rite, Daybreak Stalker, Midnight Steel, Hollow Deep, Jade Circuit, Neon Chassis) or Follow
       the app theme; a small sample shows next to it. Every part is there as in Classic (timer and ⏸ / ▶, the map,
       where you are, its rank - click to rank -, Maps, Avg, the clock, the switches with their hover help, Notes /
       Calc / Regex / Vendor ▾, lock, ⚙), each part's switch in Overlay > Options still applies, and the goal bar
       (Focus / Campaign) is drawn in the same style. No box uses Windows' see-through color key (other systems get
       the color set's box). A bar is fitted to the XP bar (drag it while unlocked; picking the style or layout
       again puts it back, and a new game size fits it again).
  2.100.0
       Polish 6 - hover, focus, motion (the same everywhere; motion.py, installed once at start):
       - Hover: a list row lights under the mouse (every list - a class binding on Treeview; Tk paints the tag made
         first, so the row's stripe steps aside while the mouse is on it); a clickable icon or link (a Label with a
         hand cursor: ✕, ↻, ⋯, Never show again ...) brightens. Buttons already had hover / pressed faces.
       - Focus: Tab to a button, switch, box or list and it shows a ring in the accent color (Button.focus in the
         button layouts, focuscolor / focusthickness; a focused list's border).
       - Motion: tooltips, toasts and windows over the game fade in over ~150 ms (an over-the-game window only the
         first time it shows, not on every alt-tab); lists never animate. Settings > Appearance > Motion: Reduce motion
         (until you choose, it follows Windows' "Show animations").
       - Tooltips on windows over the game use the overlay's colors.
  2.99.1
       Updates (feedback): the hourly look for a new version (the update badge) only ever asked GitHub for full
       releases, so with Preview builds on it never found one - it follows Preview builds now. Every start looks once
       (closing and reopening the app checks again): with both update switches off it only lights the badge; with one
       on, as before (a card, or auto-install). A newer version found during the session gets one card when a switch
       is on: Install now, or Later (auto-update installs it at the next start). The tray icon's menu has Check for
       updates (the app comes back first, so the answer shows over it).
       Roadmap: Character Appraisal (a Path of Building code priced item by item) and Patch notes (opt-in, beside
       What's new) under Maybe later; "item sold" alerts and a login token for price checks parked.
  2.99.0
       Mod book (feedback: no rules for armor, belts, rings, amulets ... or uniques; "What the app learned" should sit
       with the rules it belongs to):
       - Gear rules: pick an item class (27 - every armor, jewelry and weapon class) and every line that can roll
         on it is listed (tierdata.json, RePoE), with how many tiers it has. Rate S-F: S / A = High (always
         searched), B / C / D = Normal, F = Ignore (never searched). These are the same rules Rate on Price Checks
         sets (gear:<class>:<wording>); saved ones lose their leading "+" once so both match (gear_plus_299).
       - Unique rules: pick a unique (the ones you've price checked first). Its lines come from your price checks
         (unique_mods.json - item wording only, on this PC); a line with a choice lists every option the trade site
         has (Mageblood: every Legacy). A priced unique uses its own rules (unique:<name>:<wording>) - an F Legacy
         isn't searched. Rate mods lists every gear class and each unique you've priced.
       - What the app learned is no longer a tab: each tab has Rules | What the app learned, showing only its own rows
         (a learned row's base -> tablet / jewel / waystone / relic / gear class / a unique's bases).
       Price checks (feedback: an Exceptional white base found nothing): white / blue bases widen step by step when
       the exact base finds too few (item level or higher -> 21%+ quality -> any quality; gear.base_ladder), and a
       search with no listing inside "listed within" is tried once more with any age ("older listings" on the card).
  2.98.6
       Expedition remnant prices (feedback: they stopped showing): since 2.83.0 the watcher skipped any map where it
       hadn't seen the Expedition mark under MAP CONTENT - a strict picture match (0.85, three sizes) that misses
       with another UI scale, the map overlay or a hidden panel, so in those maps nothing ever showed. Now it watches
       every map (still never hideouts, towns or the campaign); where the mark wasn't seen it waits for a book that
       lists 2+ rewards before showing tags (random parchment never does), and that book marks the map as having
       an Expedition. The mark match is looser (0.78, five sizes; screens without it score 0.68 at most).
       Runeshape tips: "Never show again" at the bottom of the box - it turns the tips off for good (Overlay >
       Settings > Helpers > Expedition > Runeshape tips brings them back). The box takes the click without taking
       the keyboard from the game.
  2.98.5
       Feedback round:
       - Game Plan > Stockpile: the item box is pick-only; typing goes in "Or any item by name", which also narrows
         the list (picking an item the typed text narrowed to adds that item).
       - Map supplies: a third refill rule, "when it's used up". The game's log says when an omen was used up
         (gamelog "omen" event: ": Omen of  Amelioration in your inventory has been consumed", two spaces;
         the game's own messages only, never chat); the poke comes once you're back in town or
         your hideout from that map - not every N maps. Omen of Amelioration uses it (a saved row moves over once).
       - The first "Rank this map" card has Opt out: no more rank cards (Overlay > Overlay Settings > Ask me to rank maps
         brings them back).
       - Map library > Share > Upload my ranks to the community: sends your ranks now instead of with the hourly
         sync. Opt-in (Community data sharing), and only when something changed; at most once per 45 minutes, the
         board's own limit per install (it also limits each address per day).
       - Price checks: two affixes with the same stat (a Rarity prefix and a Rarity suffix) are one mod with the
         values added ("34% increased Rarity of Items found (18 + 16)"), searched as one line - the game and the
         trade site add them up, so two filters on one stat found listings without them (feedback).
         Fractured / desecrated / crafted ones stay apart (gear._merge_same_stat).
       - Opting out is final: after a No to Community data sharing, an upload no longer asks again - it says where
         the switch is. Roadmap: the Privacy & data hub (every data point and switch in one place), and the rule.
  2.98.4
       Mageblood (feedback: it couldn't be priced accurately): priced on what sets its price, like the Mageblood
       search on the roadmap - its Legacies (which ones, Min N for each one it has more than once), its charm slots
       (at least as many), and with a duplicate Legacy the "increased effect per duplicate" roll (at least ~its
       value). A Legacy is known from the game data when the trade site's own list isn't loaded yet (mods.option_for
       fell back to nothing - every Legacy was left out and it priced as any Mageblood). The notes list them.
  2.98.3
       Tidy-ups (feedback):
       - Question dialogs (Privacy & community's and the rest: askstring / askinteger) open over the app, on its
         monitor - tkinter's own placement kept them inside the main monitor (style.center_over / _place_dialog).
       - One-key copy is gone (not a viable way to copy), and so is "Other ways of copying": Bulk Pricing adds only
         what you copy with Ctrl+Alt+C. The poe2db key sits under Tools in Settings > Hotkeys (not Bulk Pricing).
       - Settings: Fine tuning moves to Price checking > Advanced fine tuning; the Tools tab is gone - "Check for
         new rates every hour" is on the Exchange rates page, by Refresh now.
       - About > Credits (and README): RePoE, poe.ninja, Exiled Exchange 2, Sidekick, hypr-exiled, Path of Building
         PoE2, PoE Ancients Price Helper - each with what it gave (ideas or data) and a link to its developers'
         GitHub page.
  2.98.2
       Corrupted items priced as corrupted (feedback: corrupted uniques came out at uncorrupted prices):
       - "Twice Corrupted" counts as corrupted (it wasn't read, so those were searched "uncorrupted only").
       - "{ Corruption Enhancement — ... }" (what a Vaal Orb added) is read as the corruption enchantment - its
         header was read as a mod line and the enchantment itself left out. Searched as a must, with the trade
         site's own enchant id (the same stat number) and at least its value; several of them, all searched.
       - A corrupted item's sockets are searched (at least as many): it can't get more.
       - Only corrupted listings are compared with a corrupted item (as before); the notes say what was searched.
       The Toolkit menu (feedback: on two monitors it sometimes opened on the main one): shown only once it's in
       place, at the desk's corner read fresh, kept on the monitor the app is on (shell.menu_origin, monitor_of).
       Roadmap: stash tab reads in stash order (from the listing-order findings), at the end.
  2.98.1
       Trade Whisper Watcher (feedback: at league start items sell by whisper before the trade system opens up -
       easy to miss one in chat): Overlay > Overlay Settings > Helpers > Trade whispers. A whisper TO you that asks to buy
       ("Hi, I would like to buy your ..." - the trade site's whisper, or the bulk form) shows a card at the top of
       the game: the item, the price, its tab and spot, who's asking; up to 3 stack, each closes after 20 s or with
       x; Sound. On by default during the campaign (a character before maps); Keep on after the campaign. Nothing
       is saved (the buyer's name is on the card only). gamelog.parse -> "whisper"; soe2/whispers.py; the helpers'
       Client.txt reader (log_wanted) follows the log while it's on. GGG ToS: reads Client.txt only - never
       invites, types or trades.
       README / ROADMAP: gamedata.json's source credited correctly (Exiled Exchange 2's MIT data files).
       (Responsive part 2 moves to 2.98.2.)
  2.98.0
       Polish 5 - Responsive, part 1 (decided 2026-11-05: everything drawn to a width follows the window):
       - Every wrapped label that fills its row re-wraps to the width it has (style.responsive: one class binding
         for Label / TLabel; labels with their own <Configure> rule keep it).
       - Button rows wrap instead of being cut off (style.flowify: turns a packed row into a wrapping one in place -
         order, padding, right-alignment and stretch kept; flow_add / flow_show for widgets shown only sometimes):
         Bulk Pricing (Add items from, the filters and actions, the buttons under the list), Regex (the key row, the
         filter and ★ rows), Money Makers (Tag / tier / Sort and the buttons), Game Plan (stockpile quantity),
         Overlay (the Session row). style.fit(widget, fn) redraws anything drawn to a width (debounced).
       - Overlay > Overlay Settings switch grids drop to fewer columns when narrow (no "Rege", "Feature ti").
       - The status bar: in a narrow window the trade-limit meters step aside so the message keeps its room.
       - Market Insights, Under the hood, Wealth: their one-line notes wrap; the Bulk Pricing empty-list hint wraps.
       Part 2 (2.98.1): a pixel scale for the drawn layouts, then the text size setting and sharp text on
       high-DPI screens (they need every layout to grow with the text first).
  2.97.3
       Tidy-ups (feedback):
       - Money Makers is a Labs feature: hidden while Labs is off, like Wealth and Game search (was BETA, always
         shown).
       - The status bar: no "● Overlay" (the sidebar's dot shows it) and no 📌 (Always on top stays in Settings ›
         General › Window).
       - Price Checks: Add to favorites and Open on trade site sit under Search and Clear.
       - Previews (decided 2026-11-05: nobody gets an untested build): every new version is published as a preview
         (pre-release, not "latest"); Actions > Promote release makes it the full release once it's been played in
         game. Settings > Updates > Preview builds (opt-in, off): get previews too - checked or installed by
         themselves with the switches above. updates.latest_release(preview) / newest().
  2.97.2
       Price Checks card - visual hierarchy (feedback):
       - A mod's color says where it comes from, as the game and the trade site show it (style.MOD_COL): affixes
         blue, socketed runes / implicits light blue, fractured tan, desecrated green, pseudo totals pink. Unticked
         rows keep their color, dimmed (were gray). The listing cards use the same colors.
       - Every section folds: "▾ STAT FILTERS (3)" - a click folds / unfolds it, the number is how many are
         ticked (Miscellaneous: how many aren't Any); Requirements starts folded. Fold all / Unfold all at the top.
         Remembered for every item (settings pc_fold).
  2.97.1
       Price Checks card (feedback):
       - A socketed rune's line and an affix with the same wording (a rune's +18% and a fractured +37% to Lightning
         Resistance) are ticked apart: a tick on this item is saved under where the line comes from (trade.ov_key).
         Rune lines have no Rate ▾ (a rating would have rated the affix too).
       - Runes have their own AUGMENTS section, ruled off from STAT FILTERS; the "RUNE / SOCKETED" lines are gone.
       - Fractured / desecrated: the mod itself in its color when ticked, and a small "└ □ fractured only" box right
         under it, so it's clear which mod it belongs to.
  2.97.0
       Polish 4 - a feedback round (and the polish plan: ROADMAP.md › Page passes, Page standard):
       - Help rate mods? says what it is: pick the items you know best, rate one mod at a time, Done ends it.
         Count me in! | Not now (asks once more, days later) | Never ask again. It opens in front of the app.
       - Rate mods starts with "Which items do you know best?" (each set with how many of its mods you haven't
         rated; Change goes back). Only your rating is lit; Back | Next | Done centered under the tiers; the last
         mod stays put when rated.
       - F is the ignore tier wherever tiers show (Rate mods, Mod book tiers and its Tier column, Regex, ▲ / ▼'s
         Ignore = F); saved as an Ignore rule, so nothing that reads rules changes. A tier on an F mod un-ignores it.
       - Focus / Campaign: no "Its line above the bar" - on means its line shows; both on = one goal bar with two
         rows (Panel and Game bar). Switching either on turns the overlay on.
       - A character past the campaign: its campaign line and Vendor ▾ show again in campaign zones (towns too)
         and hide in maps / the hideout; the finished run (splits, rewards, route) isn't touched.
       - Price Checks (feedback): Rate ▾ beside each mod (a menu: S to F, for every item like it; rated, it shows
         your grade) replaces ▲ / ▼. The card's side takes about a third of the page (380-620 px) and the card and
         the listings are drawn again for the width they have, so nothing is cut off; the scrollbar shows only when
         there's more to see (Favorites too). Fractured only / Desecrated only ticks the mod too (an unticked mod
         wasn't searched at all).
  2.96.1
       Overlay ↳ Overlay Settings regrouped (feedback: doubles, cut-off text, black boxes behind the helpers' switches):
       - On the bar: one switch per item - Session timer, Map timer, Maps done, Average map time, Map rank: S-D, Map
         name, Clock; Notes ▾, Calc ▾, Regex ▾, Exchange rates (each one switch: the feature and its place on the bar -
         the Features card and the Menus list are gone).
       - Options (was Behavior, plus the Features leftovers): Lock the overlay, Feature tips, Start the overlay with
         StashOfExile2, Ask me to rank maps, Dock the lines to the bar, Hide from screen captures, Overlay appearance….
       - Helpers: each helper's options on its own row, with its "Switch on the bar" (and Focus / Campaign "Its line
         above the bar"); the "Show the Mechanic Helper bar" switch is gone (a bar that was off keeps its helpers'
         switches off). The switches use the card's colors - no black boxes. The overlay's × no longer turns the
         helpers' switches off.
       - Campaign, full width: Vendor ▾ is on the bar the whole campaign (in town or not, until the campaign is done);
         no Act timer switch (act times are always kept; the Leaderboards get them only if you share data).
       - Gone: Your character name (deaths count for the character the game's log names; a name you typed is kept)
         and the hotkey line (Settings › Hotkeys).
       Exchange rates window: unlocked, drag it by any spot (it could only be moved by its title bar), and it follows
       the overlay's lock (it kept the lock it was built with). poe.ninja (by rasmuskl) credited in the README and
       Settings › About.
  2.96.0
       Help rate mods (ratemods.py, ratemods_page.py). Your ratings tune your own price checks at once; with Community
       data sharing on they're your vote too (rep when they match everyone's, with Count my mod ratings on).
       - ▲ / ▼ beside each mod on Price Checks ("did it matter?"): ▲ = High, ▼ = Ignore, again = cleared - for every
         item like it. Gear gets its own rules per item class ("gear:<class>:<mod>"), so a helmet's ▲ doesn't touch
         rings; trade.mod_impact reads them for gear and waystones (after the item's own ticks and totals).
       - Rate mods: one mod at a time, S / A (High) B / C / D (Normal, with that tier) or Ignore, keys S A B C D I,
         ◀ back, Skip; per rule set (Tablets, Jewels, Waystones, Relics, each gear class you've checked). From the Mod
         book's rule pages and Settings › Privacy & community.
       - The ask: once, after 25 items are priced; Not now asks once more, at random 3-7 days later; No thanks (or
         Not now again) never asks again.
       - Bulk Pricing floor (Settings › Price checking › Skip cheap items, on, 1 div for Tablets / Jewels / Relics): an
         item whose every searched mod sells for under the floor in the Mod book's own data (5+ listings each, none
         rated High) isn't searched; with 3-4 listings it's marked check by hand. A mod with no data, or one rated
         High / S / A, means it's searched. Price Checks always search.
  2.95.0
       Rep - karma-style points for helping (feedback: contributors need something back, without anything locked
       away). The board counts it: an upvote on your strat +1 (gone if it's taken back; never your own), an edit of
       yours that's accepted +3 (declined -1), a review on the side that won +1, a mod rating or map rank that matches
       what the community settled on +1 each (only with Count my mod ratings on - it ties this PC's anonymous ratings to
       your name on the server, only to count them), an admin's thank-you (a fixed bug report); a post removed for the
       rules -2. Never below 0. Upvotes are kept as a scramble, so the board never stores who upvoted whom.
       The contributor icon: a small diamond beside a name on Money Makers (list and strat) and Leaderboards, white /
       blue / yellow / orange as rep grows (1 / 50 / 250 / 1000). Hover it: the card - rep, what it came from, member
       month. Settings › Privacy & community shows yours, with Show my contributor icon and Count my mod ratings;
       admins get Thank someone with rep. Leave and delete takes your rep, and the upvotes you gave come off others.
  2.94.0
       Settings › Privacy & community (feedback: the community name lived in Money Makers, though the Leaderboards
       use it too - and after the admin key changed there was nowhere obvious to become admin again). One page, top to
       bottom: What leaves your PC (nothing unless you turn it on; "What's shared, and why?"); Data sharing (the
       community switch, moved from General, and Leaderboard times - the same switch as Leaderboards › Share my times -
       each saying what is sent and where; the community FAQ will join them later); Your community name (why you'd
       want one, what's stored, and every action: pick / change it, Inbox, Review queue, reviewer, Become admin, Move
       to another PC, Leave and delete my data); Your rights.
       Move to another PC: saves this PC's board key to a file (with a warning: it works like a password), and Use a
       key file on the other PC takes it - a key the board doesn't know is refused and yours is kept.
       The 👤 chip on Money Makers (and a new one on Leaderboards) opens the page. No name is asked at start any more:
       only when you post, vote, report or turn on leaderboard times without one.
  2.93.1
       Price Checks (feedback: cleaner, like the trade site's own preview): each listing is the picture on the left,
       the item block in the middle (name band; centered groups split by thin lines - properties with raised values
       in blue, item level and requirements, socketed / implicit lines, the mods with their tiers at the block's left
       edge, P red and S blue; the site's own totals; Corrupted; the seller's note) and on the right "Asking price:
       90× Divine Orb", the seller and when it was listed. A Clear button beside Search empties Price Checks (Recent
       too); Bulk Pricing and Favorites are left alone.
  2.93.0
       Price Checks (feedback):
       - A fractured or desecrated mod gets a small box under it: "FRACTURED - only?" / "DESECRATED - only?". Ticked,
         that mod is searched as fractured (or desecrated) only; unticked, either way, as before. This item only.
       - A hybrid resistance ("+17% to Lightning and Chaos Resistances") adds a pseudo total for each resistance it
         has, adding up every mod that feeds it (total Lightning 37 + 17 = 54, total Chaos 17). Chaos isn't in the total
         Elemental Resistance, so its total is searched; the elemental one is offered unticked.
       - Socketed rune lines (above the mods) are marked "RUNE / SOCKETED" - not searched and not in any total unless
         you tick them.
  2.92.2
       Overlay page: "Timer over the game" becomes Overlay Enabled | Overlay Disabled - one master switch for the bar,
       its lines, the calculator, the rates window and the Regex / Vendor cards (each helper keeps its own setting). A
       new install starts disabled; an install that had the overlay keeps it on. "Which switches go on the bar?" is
       asked the first time you enable it, not when the app starts (feedback: it asked right after an update). The
       session timer's own switch stays in Settings › On the bar › Numbers.
       Regex ▾ on the bar beside Notes and Calc: your Regex favorites in a small card, a click copies one (you paste
       it). The Vendor card no longer lists them.
       Vendor ▾ fixed (feedback: its switch did nothing): it was drawn on the campaign line only, so with that line off
       it never showed. Now it sits with the bar's menus in a campaign town, and the two Vendor switches are one.
  2.92.1
       Listing order lab (admins): the first round showed the site's order follows nothing it reports (vs the walk,
       the place, the time, the id: -0.13 to +0.09) when every price is the same, while each listing's place (x / y,
       its top-left cell) is exact. Ready for a 1x1 round: corrupted / magic copies that word their name lines
       differently from the site's text match by base type and lines (they were skipped); a listing keeps its size
       (Size column) and whether it's corrupted; "middle, down columns / across rows" place big items by their
       middle cell; orderlab.stash_order = down each column from the top, then the next column right (the order to
       work a tab in); a copy that matches nothing goes to orderlab_unmatched.txt on this PC (names scrubbed).
  2.92.0
       Arbitrage removed (deprecated): it read Grinding Gear Games' hourly Currency Exchange history from an address
       outside their documented API (their developer docs say endpoints outside it are against their Terms of Use; the
       official Currency Exchange API needs a registered app). With the terms for that data unclear, the tab, its
       Live scan and every request to that address are gone (arbitrage.py removed; old arb_* settings and
       cx_history.json are simply not read). The Check a flip calculator stays - arithmetic on two prices you type,
       no requests - at the bottom of Exchange rates › Exchange Helper (exchange_page.build_flip); item names and the
       flip math live in cxnames.py.
       Every request says honestly which app is asking: "StashOfExile2/<version> (+https://github.com/tiwomm/
       StashOfExile2)" (config.APP_UA) - the trade site saw "personal-stash-pricer/1.0" before; poe.ninja, GitHub and
       the community board get the same name. No name, account or email of the user is in it.
  2.91.0
       Exchange rates over the game (ovrates.py): a small window in the overlay's own look (the Game bar's colors
       with that layout, the Panel's otherwise; rebuilt when the layout changes) listing the most-used rates - "210 :
       1 div" for cheap ones, "N div each" for dear ones - from the rates table the app already keeps (no extra
       requests). Off until turned on (Overlay ↳ Overlay Settings › Features › Exchange rates window); movable (kept, and the
       overlay's lock locks it); refreshed every minute; only while the game is in front.
       Arbitrage › Check a flip you see in game: the item is picked from every Currency Exchange item (the rates
       table, most traded first, then cxnames.json); typing narrows the list (flip_names / flip_filter).
       Roadmap: Polish 5 includes making everything over the game match the overlay's theme (tooltips, pop-ups, cards,
       notices, toasts).
  2.90.0
       The overlay bar's numbers row: | ⏸ time | Map 3:12  Arcane Isle  ★ A | Maps: 4 | Avg. 6:01 | clock ⚙ 🔒 - the
       map's time, the area and its rank are one part (merged_page._MapPart; tk_ov_lbls "map" / "where" / "rank" are
       _PartOf views of it), every part's text is centered between its dividers, and the area's name is shown whole
       (the type steps down to 8 pt before anything is cut).
       A switch per helper: bar_cfg holds breach / delirium / ritual / remnant / focus / campaign (merged_page.CHIPS);
       the bar fits itself to the ones on. Asked once which you want (ov_chips_ask, tracker cfg chips_asked); a new
       install (no seen_version) starts with none ticked.
       Overlay ↳ Overlay Settings regrouped: On the bar = Numbers, Switches (one per helper), Menus, Lines above the bar (Focus
       line, Campaign line, Dock the lines to the bar); Features = Notes, Calculator, rank maps; Campaign = its options;
       Helpers (was Mechanic Helper) = every helper's on / off, League Focus and the Campaign Helper included.
       The Campaign line / Dock switches act on the box you clicked (a rebuilt page left a stale copy, so the click did
       nothing). A character at level 65+ is past the campaign (campaign.MAPS_LEVEL): no campaign line in the hideout.
       The Desecration Helper is Beta everywhere, and the first visit to The Well of Souls asks whether you want it
       (ws_ask; desecrate cfg asked).
  2.89.3
       Privacy hardening, from a full audit (nobody may be singled out or targeted through this app).
       Board (Worker): atlas screenshots get unguessable keys ("b:<32 hex>"; old numbered ones were re-keyed once,
       imageKeys) and are handed out only while a visible post uses them (or to their uploader / reviewers), cached for
       an hour, deleted with their post, and swept daily when no post uses them. DELETE /me deletes everything of
       yours (name, posts, pictures, versions, votes, reports, reviews, leaderboard times, sessions) - Money Makers ›
       Leave the board offers it. Leaderboard times keep the day only (the second showed when people play); a rename
       rewrites the name in every copy of your posts; account ids go to admins only. Internet addresses: only an
       HMAC (IP_PEPPER secret, else a random key the board keeps) with the day and purpose, purged daily
       (housekeeping, also expired sessions). /mods/batch: per-address limits on batches and new installs; zone text
       restricted and 3 sources needed (as documented). /bugs: JSON with the app's header only (a web page can't post
       one), account names / home paths masked, no @everyone pings. Admin: a 32+ character key, and admin rights
       lapse when the key changes (users.admin_key).
       App: a strat's author is never your account name (board name or "me"), exports included; strats carry rates
       only (div per hour, per run), never runs / minutes / totals. A screenshot asks before it goes public (it may
       show names, chat, party). A community name can't be your account or a character's. Private leagues
       ("(PL12345)") never go to the leaderboard, the hourly sync or a bug report. Turning sharing (or Share my times)
       off takes your times off the board. Anonymous calls (/mods, /maps, /campaign, /bugs) never carry your board
       key. privacy.scrub_names: account / character names and Name#1234 out of error logs, problem reports and the
       whole bug report (which no longer sends the exact Windows build or screen size). update_log, rate_limit_log
       and tab_reader_log keep no paths, cookies or item notes. The sample character name in comments is gone.
       Workflows pin actions to commit SHAs; Discord posts can't mention everyone.
  2.89.2
       Privacy first. Community data sharing stays off until you say yes; its question now lists each thing sent, what
       exactly and what it's for (communitymods.DETAILS - keep it true when a new upload rides on the switch), where
       it goes (the app's own community server, never sold, no ads, no tracking) and what is never sent. Settings ›
       General › Community data sharing has "What's shared, and why?" (the same page, read only).
       New privacy.scrub: your home folder and user name leave error_log.txt, problem reports and bug reports (those
       become a public issue - older log lines are scrubbed on the way out too). http_error_log keeps only the
       rate-limit headers, never cookies.
       "Act splits" is the Act timer (tab "Act times"): on by default, it times each act while the session tracker
       runs, against your best per league; with sharing on (and a community name) your best act times go to the
       Leaderboards.
       Code comments and this history describe feedback in plain words - they don't quote it.
       The overlay bar's switches say full words (Breach, Delirium, Ritual, Expedition, Focus, Campaign) - no short
       forms; the Remnant switch reads Expedition (merged_page.NAMES / chip_name).
  2.89.1
       Screenshots: 2.88.3 hid the bar only while the Ritual / Delirium watcher ran - but it runs all the time for
       anyone who has it on. "Hide the bar from screen captures" is now off by default and turned off once for
       everyone (tracker cfg hidecap_2891); turn it on only if the bar covers a counter a watcher reads.
       The Campaign switch on the bar says "Campaign", not "Camp" (merged_page.SHORT).
       A ⚙ beside the overlay's lock opens Overlay ↳ Overlay Settings and brings the app forward (overlay_settings_go).
       Campaign options: 2.89.0's "Ask Speedrun or Full rewards..." switch was gridded into the same cell as "Dock it
       to the overlay bar" - the two labels overlapped. The Ask switch comes first, Dock after the rest.
  2.89.0
       Campaign: Speedrun or Full rewards. The first campaign zone of a run with no guide yet shows a card
       (camp_route_ask_show): Speedrun / Full rewards, "Use this every time". The pick is the run's own (run["route"],
       campaign.route_of; the default cfg route otherwise); "Use this every time" makes it the default and turns off
       "Ask Speedrun or Full rewards when a campaign starts" (Overlay › Options › Campaign; cfg ask_route). Picking a
       Route there moves the run you're on too.
       The guide pack (revision 2) has a real Speedrun guide: each step may carry "speed": {"skip": true} (left out) or
       {"do": ...} (its own instruction) - 38 steps say what a speedrun does there (bosses and side areas that only
       give gems or loot skipped, the rest run through), 2 are skipped (The Mud Burrow; Dreadnought Vanguard, gone
       in 0.5). Rewards a speedrun still takes carry "speed": true (25 of 26 - every point, spirit, resistance, life
       and mana; not the Goddess of Justice); leaving an act on Speedrun doesn't ask about the others.
       Settings stuck in front after resizing the app out of full screen: Tk can swap a page's real (Win32) window for
       a new one, and the old one stayed - topmost, no longer Tk's, so nothing hid it. DeskWindow.note_hwnd keeps the
       old handles; hide_ghosts hides them (not topmost, SW_HIDE) when the swap is seen (check_owner, _show) and on
       every withdraw - only windows of this app, never a handle a page uses now.
       Roadmap: Mageblood search helper, Help rate mods + the Bulk Pricing floor as 2.90.0, the guide pack refresh
       before 1.0; Polish 4-6 move to 2.91.0-2.93.0.
  2.88.3
       Campaign switch always on the overlay's bar: bar_chips shows it whenever its "On the bar" switch is on,
       campaign or not (it was hidden until the log showed a campaign zone, so it went unnoticed).
       Overlay showed when the game wasn't in front: game_active matched any window whose title held "Path of Exile 2"
       (a browser tab, a video). Now the game's own window class, or a window named exactly the game's title
       (overlay.title_is_game; window names only, ToS). A failed foreground check keeps the last answer.
       Screen captures: the bar leaves captures only while the Ritual or Delirium watcher runs; overlay_capture_sync
       puts it back when a watcher starts / stops (2.89.1: off by default).
  2.88.2
       Ctrl+Alt+C now and then not heard: Windows quietly drops a low-level keyboard hook that answers too slowly.
       KeyWatch notes the last physical / injected key it saw; an advanced copy arriving while the hook saw no key at
       all for 3 s counts as yours and puts a fresh hook in (rehook, thread message 0x8003); the app also renews the
       hook every 5 minutes (keys_refresh). A live hook that saw no Ctrl+Alt+C still ignores other tools' copies.
       Price Checks / Favorites: a tick, a Min / Max reset or a filter change on the card no longer searches by itself
       - app.card_changed marks the item and the button reads "Search • filters changed"; Bulk Pricing still prices
       again at once. A tick keeps the card's scroll position.
       Trade links: a long link that holds the bare search (no "query" around it) reads.
  2.88.1
       Bulk Pricing stalled (feedback: "ctrl + alt + c isn't working for bulk pricing"): 2.87.0's "Price Checks go
       first" asked whether any Price Checks / Favorites item was marked "queued" - a favorite that was never opened
       stays marked so with no job, so every Bulk Pricing item stepped aside for ever. engine.urgent_waiting now asks
       the queue itself: a Price Checks / Favorites job waiting at priority 0.
  2.88.0
       Listing order lab (feedback: "the tool reads the trade site link and then I go one time through each item
       manually and you try and decipher the listing order ... a tool under advanced -> under the hood ... that only
       admin has access to"). Under the hood ↳ Listing order lab (modules/orderlab.py: advanced + admin_only - the
       shell shows it only to a community board admin; orderlab.py + orderlab_page.py). Read: a tab's trade link ->
       the listings in the site's order (and the same search newest first), each with its place (stash x / y),
       indexed time and id. Walk: Start walking, Ctrl+Alt+C each item in your order - each copy is matched to its
       listing (name lines, then its lines with and without numbers) and doesn't go to Bulk Pricing meanwhile; Undo
       last. Compare: rank correlation of every candidate order (site, newest, place down columns / across rows,
       indexed, id) with your walk and with the site's order. Rounds kept in orderlab.json; Export CSV.
  2.87.0
       Stash order (ROADMAP "public stash order"; feedback: the trade site lists a public tab's items "seemingly at
       random", while "I work ... top to bottom and left to right across my stash"). The trade site doesn't keep any
       order of its own for a tab (it sorts by price, then as it likes), but every listing says where the item sits:
       listing.stash x / y. tabreader keeps it (record "pos"); Bulk Pricing's list follows the tab - down each column,
       columns left to right (stash_key; Settings "stash_order" columns / rows, "List order" on the Stash tab row) -
       and the # column shows the place (C3 R5).
       Price Checks first (feedback: "single price check isn't causing bulk price checks to pause ... should not queue
       single price checks each time you hit search"): engine._turn() before each search - a Bulk Pricing item steps
       aside (Preempted: back in line) while a Price Checks / Favorites item waits; Search again bumps rec "gen" and
       the older run stops (Superseded). Price Checks search exactly what's ticked (no "all but 1 of the ☑ mods"
       ladder - that's why the ticked "+2 to Level of all Projectile Skills" seemed ignored: the listings shown came
       from a looser search without it).
       Price Checks' Recent after a restart (feedback: "not keeping track on single price checks ... in between
       closing the app"): the page was built before session.json was read, so Recent stayed empty - load_session
       refreshes it now; and each Price Checks item saves its listings (up to 20, "_raw"), so the cards come back too.
       Leaderboards: Simulacrum of Delusion was under Trials (feedback: "should be pinnacle") - leaderboard.cat_of now
       asks the Map library's kind first (Pinnacle -> Bosses & pinnacles); the board moves times already sent.
       Leaderboards' Class (feedback: "we don't have a way to read the class"): the game's log names it at every
       level-up; 2.86.0 only noted it from then on, so the box stayed at "All". leaderboard.learn_classes reads the
       last 64 MB of Client.txt once a run (in the background) for each character's class; the box has a tooltip.
       The stash tab's "List order" box sits on the tabs row (on the Stash tab row it squeezed "Count it in Wealth" out).
  2.86.1
       Community-name filter (feedback: "deny inappropriate usernames, especially homophobic, transphobic, racist
       bigoted names, including variants with alternate spellings or misspellings"). Board: nameProblem() - the
       open-source obscenity package's English list (MIT; THIRD_PARTY_NOTICES), with its look-alike / leet /
       repeated-letter transformers, run on the name as typed and with spaces _ . - taken out, plus our HATE list
       (number swaps and squeezed repeats; words that sit inside real names - Nazir, Raccoon, Spice, Torpedo,
       Therapist, Aryan, Lynch - left out). Join and rename refuse; a name from before the filter is reset to
       "Player-<id>" on its next visit (name_reset, no 7-day wait) and POST /admin/names/sweep resets them all. App:
       board_name_check at start-up asks again when the board reset your name; the prompt shows the board's reason.
  2.86.0
       Global leaderboards (ROADMAP): Overlay ↳ Leaderboards (modules/leaderboards.py, leaderboard_page.py,
       leaderboard.py). Boards: Campaign (each act's split + the whole campaign, from the Campaign Helper's runs),
       Maps, Bosses & pinnacles (Map library kind Pinnacle), Trials (Sekhemas / Chaos / Simulacrum by name). Mine =
       worked out here (sessions now keep their league and each map run its character; the log's level-up line
       gives the class - focus state "classes"; sessions from before 2.86.0 have no league and are left out); Everyone
       = the board's GET /lb (one row per account, fastest first, by league / class). With Community data sharing on
       and "Share my times" (lb_share), the best per board / league / class goes up (POST /lb, every 15 minutes at
       most, from cm_tick and on opening): community name only, no character names. The board keeps the faster time,
       refuses impossible ones (floors: act 2 min, map 30 s, boss 10 s, trial 1 min), hides on reports from accounts
       7+ days old, reviewers' or an admin's vote (POST /lb/<id>/review). The session page's Leaderboard has a
       "Global leaderboards" button. Network answers come back through ui_q (ev_lb_done), never root.after from a
       thread.
  2.85.2
       Ritual alerts (feedback: "aren't working, maybe because the overlay is in the position of where the ritual
       (x/3) counter is"): the overlay's bar (and the goal bar) sit over the XP bar, right where the watcher looks
       (ritual_alert.SEARCH), and the screen capture saw the bar instead of the counter. The bar windows are now left
       out of screen captures (remnant_page.capture_affinity, WDA_EXCLUDEFROMCAPTURE, Windows 10 2004+), so the Ritual
       and Delirium watchers see the game under them. Switch: Overlay ↳ Overlay Settings › Behavior "Hide the bar from
       screen captures" (tracker cfg hide_capture, on by default; off = screenshots / streams show the bar).
       Docked goal / Focus line (feedback: "a fine gap between the two ... a slight width issue"): it sits right on
       the bar (no 6 px gap), uses the bar's end-cap width (hudart.plate cap=, so the frames line up) and is rebuilt
       when the bar's width changes (goalbar_follow).
  2.85.1
       Money Makers' filter rows: the labels ("Thoughts per click", "Clicks per hour") were cut off - their column is
       19 characters wide (was 11). ROADMAP: the Community FAQ grows into a Community forum (sections, threads,
       replies, upvotes for strats and answers, reputation, moderation by admins and reviewers) - mockups first.
  2.85.0
       Community board protections (feedback: "only allow author + admin to make edits", "Suggest Edits -> change
       things, publish to community / moderation", "opt-in community handled ... protections against data
       poisoning"; picked: reviewers opt in once earned, the author's OK is enough except on Official posts).
       board/src/index.js: revisions (every version kept: History, roll back), POST /posts/<id>/suggest (author
       accepts / declines), Official changes "pending" until 2 reviewers (or an admin) approve, suggestions to posts
       whose author is away 30 days go to reviewers too, GET /review + votes (never on your own), reports from
       accounts under 7 days don't count and never auto-hide an Official post, unique names, a rename once every 7
       days, daily limits (edits, suggestions, reports, votes, reviews, admin-key tries), field bounds (money, items,
       ledger, text, sources, dates), a screenshot must be the poster's own, based_on (a copy credits the original).
       The Worker adds its new columns / tables itself (migrate()).
       App: boardmod_page.py - the community name asked once at start-up (feedback: "prompt a user once at startup
       for their chosen username ... permanent ... only be changed every 7 days"), Suggest an edit (the editor in
       suggest mode + a note), History, Inbox, Review queue, Become a reviewer; Copy to Mine drops the original's
       numbers and screenshot and credits it (mm_meta), re-posting updates the post (no duplicates).
       Money Makers / Strat Tracker accuracy (an audit of every field): negative profits and ex / chaos amounts keep
       their sign and unit everywhere (money_parse / money_edit - they failed or became div), a cost range no longer
       crashes the editor, every source link is kept (only the first was), the author's numbers read in words (not
       "cost per rund"), Community posts that don't follow the layout aren't shown, profit sorts in divines, the By
       column sorts by author, a setup with no runs no longer publishes the followed strat's numbers as yours,
       Community and Official strats can be tracked and costed, editing a log's runs scales its cost, one label
       ("Thoughts per click") everywhere, "Loot ÷ cost" (was "Return on cost").
  2.84.0
       Price Checks ↳ Favorites (feedback: "a favorites (bookmark) tracker that you can paste a trade link into ...
       'Add to favorites' next to 'Open on trade site' ... reorganize, give a name, edit/delete/etc, fully context
       menu aware"). favorites.py: favorites.json (groups and favorites in your order), reading a trade link (the
       long form decodes by itself; a short id is one GET of /search/poe2/<league>/<id>), clean_query (switched-off
       filters left out). favorites_page.py: the list (groups, drag to reorder / regroup, right-click: Search now,
       Open on trade site, Copy trade link, Rename F2, Edit, Duplicate, Move up / down Alt+arrows, Move to group,
       New group; Delete + Ctrl+Z), an item favorite = a "fav" record with the Price Checks card (filters kept with
       the favorite), a link favorite = its search's filters with switches and Min / Max, searched in your league.
       Price Checks: ☆ Add to favorites. pricecheck_page.PCView: the card + listings layout both pages use.
       Money Makers item cards (feedback: the links "didn't fill in all of the information" and picked In Person):
       every trade link uses the Settings seller (Instant Buyout by default; trade.listing_rules) - the Strat
       Tracker's too; a waystone's ★ numbers (Monster Rarity: +103%) and tier go to the Endgame filters
       (moneymakers.waystone_props) and its regex uses them (not the words "monster rarity"); a tablet's regex asks
       for at least each ★ number.
  2.83.1
       Price Checks' key is Ctrl+D (feedback: "change the default keybind for price check from ctrl + c to ctrl + d"),
       set in Settings › Hotkeys (pc_key). In game it presses the game's own Ctrl+Alt+C once (overlay.send_copy - one
       key press, one item copied, now with mod tiers) and marks it as a price check (KeyWatch.pc_time), so it goes
       to Price Checks, not Bulk Pricing. The game's plain Ctrl+C is left alone (Wealth, tablets and regex tests keep
       it); set the key to Ctrl+C to have the 2.80.0 way back.
  2.83.0
       Island Rumors (feedback: "use our Map library to build an add-on for the expedition helper"): in your hideout
       (Client.txt; feedback: "watch only in hideout") the app looks for the world map's Uncharted Waters card - the
       one large light parchment patch on a small copy of the screen - and reads only that part. Each rumor gets a
       tag beside the card: the island it leads to and your Map library rank for it ("Frigid Bluffs · A"; S / A in
       gold). rumors.py: the 20 rumors and their islands (the newest guides agree on the pairs); matched loosely
       (the card's handwriting reads as "clif fs"). Switch: Remnant's row, "Island rumors (in your hideout)".
       Remnant watcher (feedback: "it keeps popping up in random areas"): off in hideouts, towns and the campaign
       (Client.txt), always on in a Grand Expedition island (ExpeditionLogBook_...); in other maps only once the
       Expedition mark (its swirl or its crystal under MAP CONTENT, right edge) has been seen - a cheap look every 2 seconds until
       it is (feedback: "check a fixed area on the screen for the indicator of expedition being present").
  2.82.0
       Overlay ↳ Overlay Settings (feedback: the Options "shouldn't be nested beside the map stats ... reorganizing ...
       grouping of the toggle-able options"): the overlay's options are their own page under Overlay (in the
       sidebar, the title bar's Settings button and an "Overlay settings" button on the Overlay page), in cards:
       On the bar (the numbers; the switches and menus on it), Features (Notes, Calculator, League Focus, Focus
       line, map rank questions, Desecration Helper), Campaign (its switches and options), Behavior (lock, tips,
       start tracking, look, character name, keys) and the Mechanic Helper. The Overlay page keeps the session, its
       numbers and This session's maps / Map stats / Past sessions. "Desecration" is written in full on its switch.
  2.81.2
       Desecration Helper: a hybrid option the game shows in another line order than the game data lists it
       ("+35 to Accuracy Rating / 10% increased Light Radius", feedback) is read - every order is tried.
  2.81.1
       Desecration Helper: the tags say just the tier ("T5", feedback: 'the "of x" isn't necessary'), and no switch
       on the overlay's bar (feedback: it turns itself on at the Well) - its switch is in Overlay › Options and
       Overlay › Mechanic Helper.
  2.81.0
       Desecration Helper (feedback: "show the tier of their mod as a small overlaid helper"; "reading client.txt for
       entering the well of souls ... a small popup"). Client.txt says you entered The Well of Souls (Abyss_Hub): a
       small notice over the game, and the helper looks for the Well's window - only while you're there. When the
       window shows its three options (in the middle of the screen, or left of the open inventory: its title plate
       is found), Windows' text reader reads them and each gets a tag: "T4 of 6" (T1 = the best tier for that item
       type, a star and gold for T1-T2), or "Abyss 13-17 · 100%" for the Abyss lords' own mods (one range: where the
       roll sits). A two-line option is one hybrid mod. The item type comes from the options (Movement Speed only
       rolls on boots ...) and, when they fit several, from the item's picture in the slot, matched against the
       game's own item art. tierdata.json (tools/build_tierdata.py, from RePoE): every prefix / suffix wording with
       each tier's level, ranges and spawn tags, every equipment base and a small fingerprint of its picture.
       Switches: Overlay › Mechanic Helper (Desecration, with Test), Overlay › Options › On the overlay, and On
       the bar (its switch shows on the bar while you're at the Well). On by default.
       Price Checks: the listing cards showed the trade site's mods raw ({'description': ...}) - the site sends each
       mod as an object now; read as text with its tier, and fractured / desecrated / crafted / rune by its kind.
  2.80.0
       Price Checks (feedback: "copy the price checker / item panel into a new panel called Price Checks ... a
       display of the items on the trade site"). Hover an item in game and press Ctrl+C: the app reads the copy
       (the game does the copying) and shows it on Price Checks - the item card with every filter on the left
       (Search searches again), and on the right the trade site's listings behind the price as cards: name band,
       properties, item level, requirements, each mod with its tier (P1 / S1) at the left edge, the price, the
       seller, when it was listed and the item's picture (from the trade site's image server, cached),
       "Showing X of Y", Open on trade site. Recent: the last 20 items. Its searches go first in line. The
       listings are the ones the price search already fetched (no extra requests). Settings › Hotkeys › Price
       Checks: Ctrl+C on an item opens Price Checks, Bring the app to the front, Show the items' pictures.
       The old Price checks page is now Bulk Pricing: Ctrl+Alt+C (and stash tabs) add items there, as before. Price
       Checks is the parent: Bulk Pricing, Market Insights and Under the hood are its children (feedback).
  2.79.2
       Stat filters: every mod can be ticked (feedback: "nothing is clickable under stat filters"). A tick on a mod the
       price check had left out (filler, low tier) removed the item's own setting instead of keeping it, so nothing
       changed; now it's kept unless it's what the mod would be anyway. The item's search starts at Instant Buyout
       (the Settings choice is reset to it once), priced in Exalted Orb Equivalent (the trade site's default; was
       labeled "Any currency").
  2.79.1
       Mageblood and other uniques with a choice stat: searched like the trade site, with the option in the stat id
       (explicit.stat_264262054|8 = Legacy of Quicksilver), not a separate option value. The same stat more than once
       (2 Quicksilver, 2 Diamond) is one filter with Min = how many (feedback). A granted skill is also found without
       "Summon" (the trade site says "Grants Skill: Level # Rhoa Mount").
       The campaign / Focus line is docked to the top of the overlay bar by default, as wide, and moves with it
       (Overlay › Options › Campaign › "Dock it to the top of the overlay bar"; off = drag it anywhere). The Game bar
       spans the XP bar, bottom center, just above it; a position you dragged is kept per resolution, so another
       resolution fits it again. The update badge looks for a new release every hour (was 6 h).
  2.79.0
       The item panel, cleaned up (feedback: "a clean view ... all of those functions"). One card holds
       every filter: Properties (base type - this base or any of its kind -, quality, defenses / DPS totals, item
       level, sockets, each with a check box and Min / Max), Requirements (Level, Str, Dex, Int read from "Requires:",
       folded), Miscellaneous (Corrupted, Fractured, Desecrated, Sanctified, Mirrored, Unidentified: Any / Yes / No -
       a click steps), Stat filters (each mod: check box, Min / Max, ★ must match, FRACTURED tag), Pseudo filters,
       Trade filters (seller, priced in). Then Search again [Enter] / Open on trade site [O], and one ▸ Advanced
       (listing status with Mark as listed / sold / removed, if you list it, how it's priced, each mod's roll and tier,
       raw text, Copy name). Gone: the Item / How it's priced / Raw tabs, Fine-tune, the Search filters box, the foot
       buttons. trade.apply_opts: Min / Max for any number filter (NUM_OPTS) and Any / Yes / No (MISC_OPTS).
       No price pop-ups at all (feedback: not for Manual Add either). Mods the game data doesn't know (Mageblood's
       legacies, new granted skills) are found on the trade site's own stat list (gear.live_ids / relink; unmatched
       ones go to unmatched_mods.txt). A granted skill must match (no level filter); one the trade site doesn't list
       makes the item "check by hand" (feedback: a Rhoa Mount Absent Amulet priced 3.7 div, really 28c). White and
       magic bases (feedback): their exact item level, Normal / Magic, not corrupted, fractured or sanctified, their
       quality and sockets at least. Remnant: when the book appears it's read again a few times while it settles
       (SETTLE_READS) - the first look could land mid-animation, find nothing, and wait for the picture to change
       (feedback: "not popping up on time").
  2.78.3
       The overlay fits any resolution (feedback: "detect a person's resolution and scale it to fit"): its size
       follows the game window's height (merged_page.hud_k: height / 1080) without the old 0.8-1.6 cap, so 720p and
       4K get a bar and text in proportion; the cards over the game (map rank, campaign route / rewards / vendor,
       feature tips, the calculator) follow it too (ov_font, ov_px, ov_btn). The item card (feedback: "we don't
       have the option to check ilvl ... to enter mod values / ranges"): Item level with a check box and its number
       (any item - it was gear only, folded under Search filters), and Min / Max beside each mod that has a value
       (they were folded under Fine-tune) - typing keeps them, Enter prices again.
  2.78.2
       The goal bar holding the campaign line is as wide as the overlay's bar (Game bar or Panel) and lines up with
       it (was: at most 900 px, centered).
  2.78.1
       The rank card ("Rank this map", 2.76.0) said the map's area id ("How was MapRugosa?") and saved the rank
       under it, so the Map library never showed it. It says and saves the map's name now (maplib.display_name: the
       library's name, else the id without "Map", with spaces). Ranks and "Never for this map" saved under an id
       move to the name by themselves. A workflow (branches.yml) deletes a pull request's branch once it's merged
       (and older merged ones still around).
  2.78.0
       Money Makers rework (feedback: the atlas step was a vague dropdown; no pinnacles, bosses or wisps; Upload
       never asked for tags, Thinking or Clicks; the Strat panel had no regex or trade links for its items).
       Content tags: pinnacles and bosses, map content (Azmerian Wisps, Viridian Wildwood ...) are tags like the
       others (one tag system) - moneymakers.content_groups() from the shared file's "content" (strats/content.json,
       built by tools/build_strats.py into moneymakers.json and the board's schema.json), so a new league's content
       arrives without an app update. The Strat Tracker's setup has 6 steps: Atlas & content (the content check
       boxes, trees and points, an atlas screenshot - pasted or a file, kept by stratimg.py as a JPEG of at most
       1600 px / 300 KB) and Publish (what it is, one line, Thinking, Clicks, tags, steps - Publish to Community or
       Keep it in Mine only). Upload opens on Publish while any of those is missing (was: posted with defaults).
       Posting uploads the screenshot first (board POST /images, GET /images/<id>; a strat names it
       "atlas_image": "b:<id>"); the setup keeps the board's copy. Money Makers: a Content row (the pinnacles in a
       menu of check boxes, map content as buttons), content on the cards, and in the Strat panel What you need -
       each tablet and waystone with its ★ mods, today's price, Copy regex (the Regex tool's terms) and Trade (that
       base and its ★ mods, cheapest first), one regex for all the tablets - and the author's atlas screenshot
       (click: big). No planner links: the app keeps you in the app. After publishing, Money Makers opens on it.
  2.77.0
       The Campaign Helper (campaign.py, campaign_ui.py; the guide pack campaign.json). It follows the zone you're in
       from the game's log (the area line's id gives the act - G1..G4, P1..P3 interludes - and the [SCENE] line its
       name): entering a zone jumps to its step, steps gone past without entering are "passed"; click a step (or
       ◀ ▶, keys key_camp_prev / key_camp_next, off by default) to say "I'm here", or a step in another act to start
       from there. Its line goes on the goal bar (a row over League Focus's): act and zone, what to do and what it's
       worth, the next zone, your level and the zone's, the step; Vendor ▾ in town copies this act's searches and
       your Regex favorites (you paste them - nothing is typed). A click opens the act's card: Route, Rewards (points,
       spirit, resistances; tick any by hand), Splits (time per act without AFK or long gaps; a best per league).
       Leaving an act, a reward whose zone you never entered is "missed", one whose zone you entered asks "Did you get
       it?" - in the next town: Got it, Remind me in town, Skip it. A reward's "proof" zones tick it by themselves;
       a hand tick always wins. Zones the guide doesn't know are added where you went (with a note, Mark optional, a
       newer guide) and pooled through Community data sharing (POST /mods/batch "zones", GET /campaign/zones); a
       weekly GitHub Action (guide.yml, tools/build_guide.py) adds the ones 3+ installs saw. Overlay › Options:
       Campaign (route Full rewards / Speedrun / My own, five switches, the guide pack and its check), the Campaign
       Helper / its line / Vendor search switches, and Campaign / Vendor ▾ on the bar. Turns itself off at maps.
  2.76.0
       Two parts of the overlay get their own place (ovparts.py). The map's rank (★ A, ★ (B) the community's, ★ -)
       is its own part, not glued onto where you are: its switch (lines "rank"), a click ranks the map you're in; on a
       bar too short for it, it steps aside. "Ask me to rank maps I haven't ranked" (on by default): leaving an
       unranked map, a card asks - S A B C D Avoid, Not now, Never for this map (SETTINGS rank_never). League
       Focus's line moved off the main bar onto its own small goal bar in the overlay's style - a short plate over
       the Game bar, a small card by the Panel (over it when there's no room under it) - dragged while unlocked
       (goal_pos per layout), held by the one lock, hidden with F6, click-through like the bar. The Campaign
       Helper's line will go there too (2.77.0).
  2.75.0
       Wealth's UX pass (feedback: "this page needs a major pass to improve ux" - the stash tabs were behind a small
       "Edit synced tabs" link, the setup guide's Next was off the window, Count again / Count currency read as two
       things). Three pages in the sidebar (register_tabs): Wealth ↳ Overview (total, Where it is, items with a From
       list - was the tab list at the side), ↳ Stash tabs (the list, Include / Open / Remove, and Add a stash tab with
       the three in-game steps, always shown) and ↳ Snapshots (pick one: what it held; two: what changed). ⟳ Sync stash
       tabs, Count currency… and More on top of every page, with what was done when. The setup guide is cards on
       the Overview now (wealth_steps_refresh: count currency, add a tab or skip, sync - each ticks itself off;
       More › Show the setup steps / Hide these steps), then one status line (currency counted, stash tabs, items
       that need a price - each clickable). wealth_setup.py (the pop-up guide) is gone.
  2.74.5
       Price checks, a lighter page (feedback: "too much clutter and thick heavy padding"): the Valuable mods legend
       chip is gone; the price-check settings line and its ⚙ sit on the top strip, after the total; Re-price all,
       Pause and Export CSV share the filters' row (one toolbar row less); slimmer paddings, Paused / limits bar and
       action row; no "Only ★" switch. chrome.Notice: a one-line notice with a small × that stays closed
       (SETTINGS notices_closed) - the Stash tab's BETA line is one.
  2.74.4
       The item card's mods have check boxes (feedback: "a check beside it", not a scroll
       down to the switches): each mod and total is a row - [✓] tier text - ticked = searched on; a click re-prices
       this item, as the switch did (app._card_mod_row / card_toggle). Min / Max, ★ and the rolls fold away under
       "Fine-tune the search" (SETTINGS detail_tune). The card is the panel's inner width (it was 20 px wider, the
       right edge cut off). A unique's flavor text is never read as a mod, wherever it sits - The Brass Dome's
       lore line was read because an "Unmodifiable" section came after it (gamedata.flavour_sections). A click that
       redraws the panel no longer prints an error (shell.take_keyboard).
  2.74.3
       The session timer's keys (feedback: the Ctrl+Alt keys "block some game input for some users"): no start / stop
       key any more (key_toggle gone - Settings › Hotkeys and Overlay › Options too); pause / resume is on the
       keyboard's Pause key (overlay.VK "pause" 0x13; Ctrl+Alt+P moved over once, keys_2743; a key of your own is
       kept) and starts the timer when it isn't running. A ⏸ / ▶ button on the overlay, before the time (Game bar)
       or in the timer's cell (Panel), drawn as shapes (merged_page._mg_play / play_refresh). Click-through is its
       own switch, off by default, not tied to the lock (click_through_on). The bar's switches keep clear of
       Notes ▾ / Calc ▾.
  2.74.2
       Settings › Advanced › Report a bug: the same form as the bottom bar's Report a bug (bug_report_open); the
       .zip problem report is gone from Settings (App.problem_report removed; report.py kept). A new version shows
       in the sidebar, above Toolkit and Settings - an accent row "Update to x.y.z" (sidebar._update_row; click:
       check_updates("ask")) - instead of the badge on the bottom bar (kept only without a sidebar).
  2.74.1
       The Item card reads like the item in game (feedback: the mod values were under the price,
       a scroll away): implicits, a rule, the other mods with their values and tier tags (P1 / S2), Corrupted,
       then the price - all on the card (app._detail_card). Uniques: a "{ Unique Modifier }" header is an explicit
       mod (gear.KIND_NAMES - they were all skipped as "unique"); a roll shown by name, Mageblood's "Legacy of
       Gold (Amethyst-Topaz)", is read as "Legacy of Gold" (gamedata._WRANGE); stats the trade site lists with a
       choice ("Legacy of #" - Gold, Quicksilver ...) are read with their options (engine._load_stats ->
       stats_options.json, mods.OPTS / option_for) and searched as {"option": id} - which Legacies a Mageblood has
       is searched, it sets the price. Flavor text (the lore lines at the bottom) is never read as a mod, on any
       item (gamedata.flavour_section).
  2.74.0
       Advanced tools hidden by default (feedback: "I don't think the mod book or under the hood information is
       useful to the average user"): Module.advanced; shell.visible() hides them unless SETTINGS["show_advanced"]
       (Settings › Advanced › Show advanced tools, shell.set_advanced - the two Open buttons are gone). The Mod book
       is a child of Under the hood now (parent = "library"): the sidebar lists a child's own children one step
       further in, the Toolkit menu too. They keep working out of sight (learning, community data sharing, Regex's
       ratings). The calculator over the game (calc.CalcOverlay, out of Tools - the Calculator module is gone): a
       fixed-size OverlayWindow (248 px wide, as tall as its keys), dragged where you like and held by the overlay's
       one lock (overlay_lock rebuilds it), opened from Calc ▾ on the overlay's bar beside Notes ▾
       (merged_page._mg_bar_buttons); Overlay › Options: Calculator on / off and Calc ▾ on the bar. The bar is
       0.056 of the game's height (halfway between 2.73.4 and 2.73.5). The Remnant tip mentions the runeshape list.
       Focus's line follows the Focus line switch again (2.73.5 also hid it with the Focus switch on the bar).
       Settings › Appearance › Overlay settings: Layout, Opacity and Click-through in one area (were Overlay layout
       and Opacity). Click-through (on by default): a locked overlay's bar lets clicks through to the game
       (merged_page.set_click_through - WS_EX_TRANSPARENT; overlay_click_through after every merged_build); unlock
       it to use its switches. Notes and the calculator always take clicks. The Game bar is the default layout for
       a new setup, and it's called "Game bar" (was "Game bar - on the XP bar").
  2.73.5
       The overlay bar's room goes up and down, not side to side (feedback: "more vertical padding, not
       horizontal"): HUD_SPOTS' xpbar is taller (0.046 -> 0.066 of the game's height), the switch row and the
       numbers row each get space above and below, the switches' side-to-side spacing is 2.73.3's again
       (_hud_gap 6). A switch's hover tip goes above the pointer when there's no room under it, and stays inside
       the game window (ovhelp._ov_tip_bounds) - it was cut off at the screen's bottom edge. A divider between each
       part of the bar's numbers row (time | map | where / NOW | maps | avg | clock). Focus hidden from the bar
       (Options) hides its focus line too. Price pop-ups at the mouse (worth it, valuable mods, all checked) only for
       items you checked yourself (App.pops_for): since 2.73.2 a stash tab's items are priced one at a time out of
       sight, each looked like a single check and popped up wherever the mouse was. iLvl for rows saved before
       2.73.2: load_session reads it from the row's copied text (a tab read again skips them as "already in the list").
  2.73.4
       League Focus polish. Your league only: WealthPrices.for_league() - named() / value() give nothing while the
       cached poe.ninja prices are another league's (a league switch waits for the next refresh); bulk prices are
       looked up for Settings' league (app.stack_price, Wealth's bulk fill, Game Plan). Stockpile: the Currency
       Exchange's list (bulk.catalog from trade_static.json, by group; poe.ninja's names before it's here) with
       type-to-narrow, or any item by name; Goal is Quantity. Farm plan: a farm of your own (add_farm(None, name)).
       Goal targets by kind (focus.TARGETS): div, level (focus.char_level from the log's level-ups - the build
       lock's character, else the last one), act, maps (counted by the log since the goal was set), a number;
       target_div kept for older goals. The overlay bar: more room between the switches (_hud_gap); ovhelp.py -
       hover a switch for one line on what it does, and the first time one is switched on a card (what / why /
       set it up), once each; Overlay › Options › On the overlay › Feature tips turns both off. The focus line
       with no goal says so and opens Game Plan on a click. Game Plan's look: a summary strip, phase headings with
       counts and a NOW badge, goal details on a quieter line with a progress bar, ADD headings over aligned
       forms, the same + Add everywhere, table headings with a rule, Pokes in Limits / When and what / Tone.
  2.73.3
       Map supply pokes (League Focus): focus.SETTINGS["focus"]["supplies"] rows {name, rule maps|minutes, every,
       at_maps, at_secs, snooze}. log_event counts waystone maps (a new area+seed; a portal back into the same map
       isn't one) and seconds in maps (enter -> leave, capped at 3 h). due() offers one "supply" poke for every row
       that's up, only in town / hideout (never in a map), after price pokes and before the check-in; Refilled and
       Skip count again from now, Snooze waits snooze_min. Its own switch (pokes["supplies"]). Game Plan › Map
       supplies: the switch, rows with Refill every (N + maps / min in maps), Since refill, ↻ refilled, ✕, and an
       add row with common supplies. Not Wealth (it doesn't track live).
  2.73.2
       Price checks fixes. add_item_text: an item read into another list (a stash tab's while Manual Add shows) is
       priced but not inserted into the visible tree. Engine: latest[(kind, rid)] = (newest seq, prio, copies);
       take() skips older copies and parks a held item's job in held[rid]; hold / unhold / bump(rid, 0 or 90) back
       the rows' right-click Pause / Resume pricing, Price next, Price last (a held row shows "⏸"). An iLvl
       column (gear / waystones / jewels give "ilvl"; sortable). Market Insights: the cursor tooltip is gone - the
       picked row is drawn in an Item panel at the side with Open / Price it again / Trade / Remove; Delete,
       right-click › Remove and Undo in all three lists (ins_hidden / ins_hidden_mods hide listings and mods; the
       Mod book keeps its data). config.TAGLINE "One tool to rule them all." in the title, Toolkit menu, About,
       README.
  2.73.1
       League Focus part 2: pokes over the game (focus.due / poke_text / answer, plan_page.FocusPokes). Checked
       every 10 s from the session tracker's tick; the log's area and (new) level-up events feed focus.log_event.
       Kinds, in the order they win: milestone (the first waystone map: the phase moves to maps, your maps goals
       and farm plan), guard (a new level 1-2 character while the build lock is on: Back to the plan / I'm sure -
       unlock), price (a stockpile item under your price, once a day each), check-in (every N min of play: On track
       / Got sidetracked / Taking a break - 30 min off), nudge (a goal in your own words, at most every 3 h, weekly
       ones weekly: Done / Snooze / Not today / Stop this one). Limits: per hour (milestones and the guard don't
       count; halved after 3 "Not today" in a row), quiet hours, only in town / hideout (urgent ones wait for town
       too), only during a session. Each says why it showed up (switchable); the tone changes the words; a soft
       sound; a Windows notification when the game isn't in front (switchable). A poke is an overlay window at the
       top middle of the game that never takes the keyboard (one at a time). Game Plan › Pokes: Test a poke,
       History (the last 15 and your answers). gamelog: LEVELUP.
  2.73.0
       League Focus part 1 (focus.py, plan_page.py; mockups A-K). Overlay ↳ Game Plan (module "plan"): goals by
       phase - league start / when I reach maps / long term - each with when to poke ("in town or my hideout", "when I
       reach this phase", "once a week", "never") and an optional target in divines (progress from Wealth's last
       snapshot); ▸ picks the one on the overlay's focus line (else the first open goal from the current phase on);
       the stockpile (have = your Wealth count, now = poe.ninja or the bulk exchange: cheap / ok / done); the farm
       plan (strats from Money Makers, in order); the build lock; the poke settings (the pokes come in 2.73.1).
       Every switch is a toggle (Card.TCheckbutton). Overlay: the focus line ("NOW" + the goal + a progress bar) in
       the Panel (its own row) and the XP bar (in where-you-are's place); a Focus switch on the bar next to the
       Mechanic Helper's (bar_chips). Options › On the overlay: League Focus and Focus line, and ON THE BAR -
       Mechanic Helper switches, Focus switch, Notes ▾ (bar_cfg) - a feature off the bar keeps working.
  2.72.2
       Notes: right-click on a note's tab opens a menu (it used to close the tab at once): Rename (right on the tab -
       Enter keeps it, Esc cancels; double-click does the same), New note, Duplicate, Move left / right, Copy its
       text, Clear its text, Reopen a closed note (the last 5 closed or cleared ones with text, notes_closed), Close.
  2.72.1
       Stackables poe.ninja doesn't list, priced from the trade site's bulk exchange (bulk.py): one "have Divine /
       want it" search per item (then Exalted if fewer than 3 offers), price per item = asked / given, the median
       of the cheapest five with far-off ones left out; kept an hour (bulk_prices.json). Its own rate-limit class
       ("exchange"). Names -> exchange ids from the trade site's /data/static (trade_static.json). Wealth: after
       poe.ninja's prices, the missing stackables are searched in the background (up to 30) and shown with source
       "bulk exchange (N offers in divine)". Price checks: a copied stack says what it's worth in the status line
       (poe.ninja, else the bulk exchange).
  2.72.0
       Gear priced properly (our own rules, from how the trade site's listings behave - no other tool's code).
       Rares / magic: filler mods buyers hardly pay for (gear.FILLER: light radius, thorns, stun, attribute
       requirements, knockback, recover on kill) and affixes of tier 6 or lower are left out of the search (mod
       "auto" = ignore, with a note; ticking one searches on it), so the count search finds the comparable listings.
       Gear shows its price once the searches back it up (Medium / High confidence) - it used to be "Price manually"
       / "Guess" for every non-unique piece; Low still says Price manually. Uniques by roll: a mod in the top quarter
       of its range is searched at least that high, the rest stay "searched by name" with their roll shown; the
       item's overall roll is a note. Normal / magic bases of item level 75+: crafting bases, searched by their base
       at item level min(own, 82)+ (type_filters ilvl). Price checks' hint and scope card say so.
  2.71.0
       Money Makers › Strats redone. Filter buttons instead of the Browse tree: Strats (All / each category, with
       counts; empty ones grayed), its Type (once a category is picked), 🧠 Thinking and 🖱 Clicks (a pick shows that
       level and the easier / calmer ones); they wrap to the window (_mm_flow, placed). Tag, Waystone tier and Sort
       (Profit, Upvotes, Easiest, Name) stay as lists; the legend line is gone. Strats show as cards by default (what
       it is, name, effort, estimated profit / h, upvotes, who, and "Yours: N runs · x div / h" when you tracked
       it); Cards / List on the strip - the List is the old sortable table and still holds the selection
       (mm_tree). The strat's panel: ▶ Track in Strat Tracker, and a Your numbers box (runs, div / hour, div a run,
       time a run - every Strat Tracker setup that follows the strat) or how to start. Best profit first.
  2.70.1
       Overlay page: the Hide timer button is gone (it took every number off the overlay, not just the timer). In
       its place a "Timer over the game" switch - the session's time only. Options › On the overlay (was Timer):
       a switch for each part - Session timer, This map's time, Maps done, Average map, Where you are (new), Clock,
       Notes (2.68.1 forced it on; now your choice is kept, overlay notes_choice), Mechanic Helper switches (the
       same switch as the Mechanic Helper page's; no longer forced on while the timer shows). Both looks (Panel, XP
       bar) follow them. Options › Session holds autostart, the lock, your character, the Appearance link.
       Card.TCheckbutton style. A session start always brings the overlay's numbers (cfg overlay migrated on).
  2.70.0
       Strat Tracker part 2. The setup editor is 5 short steps (ledger_page.Steps: numbered steps along the top,
       click one to go there; Back / Next, Enter goes on): Name & strat, Waystone, Tablets & more, Atlas, Logging -
       each in a header-strip section - with "Cost of one run" always at the right (the total in big type, the
       parts under it). A new setup saves at the end; an edited one from any step. Ctrl+Alt+C of an item jumps to
       its step. The log-loot box is 3 steps: Runs (with what those runs cost), Loot (Ctrl+Alt+C a drop jumps
       here), Profit (loot, cost, profit, note; Log it). Later / Skip on every step. Card.TRadiobutton style;
       chrome.section(wrap=True): its note wraps to
       the section's width (damped; only the editor uses it - on every page a theme swap made it loop).
  2.69.3
       Session: the game closing (or crashing) while a session is open is noticed (overlay.game_open, window titles
       only, every 5 s). After 15 s gone the session pauses at the moment it went (that time isn't counted) and the
       Session page + a toast ask End session / Keep it going; the game coming back resumes it. Only after the game
       was seen during the session (starting one before the game is fine), or - for a session kept from the last
       time the app ran (app / PC crash) - when the game doesn't show up within a minute. ROADMAP: "Maybe later"
       (Trials & Simulacrum tracker, Community FAQ).
  2.69.2
       Overlay: a paused session's "(paused)" ran into Map (XP bar) and the next cell (Panel). The time now stays
       alone (merged_page._Time) and a small muted PAUSED tag sits after it on the XP bar (its room is kept) or
       under it in the Panel's cell.
  2.69.1
       Community data sharing (was "Community Mod book" / "Share my mod prices") is opt-in: off until you say
       yes. The first run asks in a small window (Share / No thanks; closing it asks again next time); the answer
       is kept as share_asked. The same switch covers what goes to the community board: the hourly mod prices,
       Mod book ratings and map ranks, and posting strats / one-liners from Money Makers (asks first when off).
       Strat Tracker: 📤 Upload (and Export ▾ › Upload) puts a setup with its numbers on the community strats; if
       the board's layout still needs something it is kept in Money Makers › Strats › Mine to fill in. Toolkit:
       its footer buttons in two even rows and the menu as tall as its lists, so Check for updates isn't cut off.
  2.69.0
       Redesign step 3: every tool's parts sit under the theme's header strips in sunken frames, like Price checks
       (chrome.section(parent, title, note) -> (outer, inner)): every Settings section, Wealth (Totals, Sources,
       Items), Regex (Your search, each option card, want / avoid), Exchange rates (Convert, Exchange Helper,
       Rates), Game search results, Market Insights, Under the hood, Money Makers (Browse, Strats, the detail,
       How to craft), Map library, Mod book, Overlay (Session, Leaderboard, Maps per day, Timer, Hotkeys),
       Calculator history, Feed and Library. Settings search and its links still land on the section
       (section_outer / section_title).
  2.68.1
       Notes is part of the overlay now (its Notes ▾, F6 with the rest): the Notes section on the Overlay page is
       gone (on / off switch, Show / hide, "Put it back in the corner", the "its key brings it back" status), and
       so is every trace of a notes key (overlay DEFAULTS notes_key, the AHK import's Hotkeys/Notes, old saved
       ones are dropped). notes_enabled is always on (set_enabled only switches the chat commands). Its text size
       stays in Settings › Appearance.
  2.68.0
       Farm Tracker is now Strat Tracker (says what it does: tracks what a farming strat really makes). Waystones
       in a setup: "which numbers make this setup work?" lists its endgame numbers (Pack Size, Item Rarity,
       Monster Rarity ... from waystone.parse_waystone - what the trade site's Endgame Filters search), not its
       monster mods; its Trade search uses map_filters (its tier, each ticked number at your value or more) and its
       Copy regex the stash search's tier / property terms (_fl_waystone_search); waystones always get the links.
       After Done / Skip the setup window comes back to the front (the dialog is transient to it; nxt() lifts it)
       - it used to fall behind the Money Makers page. "Other costs a run (omens …)" -> "Other costs a run".
  2.67.2
       The XP bar Game bar in two rows (feedback: "too cluttered"): a taller plate (HUD_SPOTS height 0.046 of the
       game window) - the four switches centered on top with their full names (short ones only when narrow) and
       Notes ▾ at the end, a thin fading rule, then the time | the map and where you are (more room now) |
       Maps · Avg ... the clock and the lock. _hud_sep takes a center and height.
  2.67.1
       Money Makers › Tablet Crafting is called Tablet Craft Helper (what it does: tells you the next step for a
       tablet). Name only - same page, same key.
  2.67.0
       Overlay: two layouts only - the Panel (2.66.2's grid card) and the Game bar on the XP bar; beside-the-orbs
       is gone (_hud_snug / _hud_timer / _hud_rest / _hud_rule removed; HUD = ("xpbar",)). The four switches show
       in both whenever the timer does (merged_wants / tracker_helpers_sync: alerts_bar or mg_timer). On a narrow
       XP bar the switches win over Maps / Avg. Notes in the Panel's look (overlay.note_palette = hudart.card_palette;
       hudart.card with no banner draws its frame to the note's size), still moved by its title bar and resized
       from its edges. Farm Tracker: "The mods that matter" opens one at a time (fl_km_queue), centered on the
       setup window (_fl_center); the setup window opens centered on the app; no "valuable mods" pop-up for its
       own items (ev_resolved skips src "ledger"); each item card gets "🔗 Trade search" (fl_entry_search: the
       base, the mods that matter, 10+ uses for tablets, as a ?q= trade link) and "⧉ Copy regex" (regex.build for
       the matching mod tokens, the tablet type, 10+ uses). test_v2670; test_v2650 for the layouts.
  2.66.2
       The Panel again, from a written breakdown of the look: deep charcoal / dark wood / near-black leather (no
       red); a heavy dark-metal frame with a thin antique-gold line and filigree corners (hudart._filigree); a
       header banner with its own double gold frame and pointed ends (SESSION in antique-gold small caps, the
       area / league small under it); the stats in ONE leather panel split into a 2 x 2 grid by thin divider
       lines (a stud where they cross) - a small cream icon and a big gold number per cell (_Num: "Maps 7" -> 7,
       "--:--" when not tracking); the switches in a second 2 x 2 grid, a soft gold glow in the cell when on
       (hudart.glow); a thin rule over the clock / Notes / lock. hudart.card(w, h, banner, grids, foot_y).
  2.66.1
       The Panel redrawn to match the game's Treasurer window (feedback: 2.66.0's card didn't look like it): a
       dark wood frame with a raised ridge, a charcoal title band with cut corners and a pale metal top edge,
       SESSION in real small caps (_smallcaps: big first letter, smaller capitals), a dark maroon band under it
       with the area / league in red capitals (_Sub), stats in rounded charcoal boxes with a soft lit rim, cream
       icons and big gold numbers, the switches in the same boxes (gold rim and glow when on). No scrollwork.
       hudart.card(w, h, bands) / box() / card_palette() redone.
  2.66.0
       One look over the game: the app's theme. overlaywin.theme_palette() builds the overlay palette from the
       running pack (surfaces, text, accent, border, good / bad, heading font; metal for the Game bar from the
       border and accent) and pal() returns it - the Style list (parchment, codex, relic, carved, hud, classic,
       minimal) is gone from Settings; Minimal is a Layout now (an old Minimal style moves there once,
       SETTINGS ov_look_266). The palette's colors are seeded into themes' tone cache so Tk gets them as they are.
       A theme swap rebuilds the overlay (relook -> merged_set). The Game bar is the exception: it is part of the
       game's bar, so hudart draws it in PoE2's own HUD style in every theme (charcoal stone, pewter frame with a
       gold inner line, corner brackets and rivets, gothic-arch end caps with a crimson gem on the life side and
       a sapphire one on the mana side, a crest, square sockets like the flask / skill slots glowing gold when
       on, double dividers); hudart.palette() gives its cream / gold text in Palatino Linotype. Game search ↳
       Anoints: Anoints left the category chips for its own page (register_tabs("search", gs_tabs,
       home="Search")); the search leaves anoints out; gs_pick(ANOINTS) still lands there.
       Layouts cut to two looks, both the game's own: Panel (rebuilt like the game's vendor windows - the
       Treasurer's ledger: hudart.card / box / card_palette - an oxblood frame with bronze edges and scrollwork, a
       header plate with SESSION and the area (or the league) in red, the time, map time, Maps and Avg in dark
       boxes with gold numbers, the four switches in boxes that glow when on, a footer with clock, Notes ▾ and the
       lock) and the Game bar (XP bar / beside the orbs). Strip and Minimal are gone (an old one shows as the
       Panel); the note always opens as its own window (merged_embeds_notes False); _mg_panel / _mg_mini /
       _mg_strip removed. Beside the orbs: each half only as wide as it shows
       (_hud_snug), against its orb; smaller end caps; the timer half is time + Avg / map, area, Maps. No
       "Fit to the game" button: picking a Game bar layout again starts it fitted (merged_set drops its
       hud_pos). Plus 2.65.1 below (never released on its own).
  2.65.1
       Game bar artwork (soe2/hudart.py, Pillow, drawn 3x and scaled down, cached per size): plate() - carved
       stone (shade, mottling, grain), a bevelled bronze frame, end caps with a lozenge, flourishes and an amber
       gem, a recessed well, a small crest on top; socket() - each switch in a recessed socket that lights up
       (green-gold glow) when on; divider() - bronze dividers with a lozenge. Content sits inside the well
       (_hud_frame returns its edges); a fading rule with a lozenge splits the beside-the-orbs timer. Without
       Pillow the plain shaded bar is used. Sidebar fix: a click on a tool's own row goes back to its own page
       from one of its tabs or child tools (Regex from Favorites -> Build a search, Overlay from Map library ->
       Overlay); only on its own page does a click fold it. test_v2650 covers both.
  2.65.0
       Game bar overlay layouts (merged_page HUD = xpbar / orbs): "Game bar - on the XP bar" (one window between
       the orb panels, resting on the XP bar: time | map | maps · avg | the four switches, short names | Notes |
       clock, lock) and "Game bar - beside the orbs" (two windows: right of the life orb the time, Maps · Avg,
       map and area; left of the mana orb the switches 2 x 2, Notes, clock, lock). Placed from HUD_SPOTS - parts
       of the game window's height, from its edges (PoE2 16:9, UI scale 100 %) via alerts_page.game_rect (else
       the screen); fonts grow with the game height (_hf). Their own look whatever the style: PALETTES["gamebar"]
       (not in LOOKS) - dark stone shade, bronze rim with a pale highlight, end studs, gold serif text
       (_hud_frame). OverlayWindow(palette=) for that; tracker_helpers_paint uses mg_P. Unlocked they drag and
       keep their place (cfg hud_pos per layout); Settings › Appearance › "↺ Fit to the game" (hud_fit) puts
       them back. mg_win2 (the second half) is destroyed, hidden (F6) and faded with the first; Notes opens above
       the bar. Sidebar: only the tools at first - the open one unfolds (its child tools and tabs, ▸ / ▾);
       a click on the open one folds it (Sidebar.folded). Shell.register_tabs(home=): a tab that is the page
       itself, not listed (Regex: Build a search; only ★ Favorites under it). test_v2650; test_v2620 /
       test_v2640 for the folding.
  2.64.0
       A page's tabs are listed in the sidebar under the page (↳), not along its top: Shell.register_tabs(key, bar)
       hides a SegBar (pack_forget; command and pick wrapped so the sidebar follows) or a SegBook's button row
       (<<NotebookTabChanged>>); tab_titles / tab_current / open_tab. Sidebar.items lists them as rows
       ("<key>::<title>", depth 1 under a page, 2 under a child tool), a smaller row with the theme's marker; the
       page's own row goes bold instead. When everything doesn't fit, only the open page's tabs are listed
       (_fits / fold); none in the narrow icon sidebar. Registered: Money Makers (Strats, Lucrative Strats, Tablet
       Crafting, Farm Tracker), Regex (Build a search, ★ Favorites), Exchange rates (Rates, Exchange Helper,
       Arbitrage), Mod book (its six tabs). Farm Ledger is called Farm Tracker everywhere it's shown. ROADMAP's
       "How the app is organized" has the rule. test_v2640; tests renamed to Farm Tracker.
  2.63.0
       Price checks, redesign step 2: soe2/chrome.py (SectionBar - a header strip painted from the pack's
       "bars.section", title left, note right; Viewport - the sunken frame from "panels.viewport"; both redraw
       after a live swap). Every pack has both (ported from the mockups, no ornaments; DEFAULTS too). The toolbar:
       mode row + Search box, row 1 = settings link, rules, Re-price all / Pause / Export CSV, row 2 = Show,
       Category, Rarity, Type, Only ★, Clear filters, Order added. The list sits under an "Items · Manual Add" /
       "Stash tab · <name>" strip (count + sort as its note, list_note) in a Viewport, with Undo / Mark listed /
       Mark removed / Delete / Clear list under it. The item panel has an "Item" strip, a Viewport and Open on trade
       site / Mark listed at its foot. Search (text_ok: name, base, class, label, then the copied text) and Only ★
       (key_mods) filter the list; Clear filters clears them too. The click pop-up on Price checks rows
       (pc_preview_at, 2.53.0) is gone - the item panel shows the item. check_contrast checks the section strips.
       test_v2630; test_v2530 updated.
  2.62.0
       Pages (redesign step 1 of the mockup style): shell.PAGES - one tool at a time, filling the main area. Each
       module keeps its own real window (DeskWindow) but as a page: placed over the whole desk (page_fill), no
       edge / window buttons / resize handles / drag; Shell.open withdraws the other page; after_change brings the
       previous page back; finish opens the last page (cfg "page"); minimize = minimize the app (Esc). soe2/sidebar.py
       (Sidebar canvas, self-painted from the pack's "nav": bar / glow / pill / gem / bracket / arrow / step marker,
       texture): groups Modules / Tools / In game, child tools indented with ↳, utilities' running dots, BETA tags,
       Toolkit + Settings at the bottom, icons only under 1100 px. No dock and no taskbar: the status strip is the
       status bar (task_right moved into it: Report a bug, league, utility dots, pin, clock). Launcher and Wallpaper
       left Settings › Appearance. info_card also toasts when Price checks isn't the page. Light packs: bright
       text (white, gold, amber) becomes a dark shade of its hue, near-black leftovers follow the pack's surfaces.
       Packs carry "nav" (from the mockups). test_v2620; shell tests moved to pages (harness side_texts /
       side_click).
  2.61.1
       Chat commands: the Key column is a key box again (KeyCapture, like Settings › Hotkeys) and Go to hideout has
       one too - click, press the key, right-click clears. chat_key_set saves (ov_save), refreshes the Hotkeys page,
       and chat_key_marks paints a box red and names the hotkey that already uses its key. ov_save keeps every
       row in its place (row n = command n = the Hotkeys page's cmd:n) and keeps a command that has no key yet -
       before, a command without a key was dropped when saved. test_v2611; test_v2570 allows key boxes on the
       Chat commands page.
  2.61.0
       The app window's own (Windows) title bar follows the theme: winsys.set_titlebar (DWM: immersive dark mode
       20 / 19 on Windows 10; caption 35, text 36 and border 34 colors on Windows 11; SetWindowPos FRAMECHANGED),
       colorref(); themes.window_colors() (a pack's "window" {caption, text, border}, else the bottom of its title
       gradient, its bar text, border_light); App.paint_titlebar at start (+1.5 s once on screen) and after every
       swap. A fresh install starts the quick start on "Pick your look" (about_page THEME_PAGE): the theme cards
       (App.theme_cards, now shared with Settings › Appearance; look_card_sets) - click = live. check_contrast
       also checks the title bar. test_v2610; test_v2100 / v200b13 count the new first page.
       Fix (2.60.0): on / off switches went blank after going back to a theme used before - switches() made new
       pictures for a look whose element already existed, and the element's own pictures were freed. Now each
       look's pictures are made once and kept; the switch colors come straight from the theme's palette.
  2.60.0
       Theme packs (from the theme mockups; Emberforge the default; made-up names; the same icons in every
       theme; theme only in Settings › Appearance). soe2/themes.py: packs = themes/*.json (+ %APPDATA% themes),
       "extends", DEFAULTS; set_theme rewrites style.C in place from the pack's roles (LEGACY); tone() (=
       style.theme_color, hooked into every color given to Tk) maps C values to the pack, the app's other steel blues
       by lightness onto palette anchors, light text onto light packs, keeps rarity colors and the banners' #010203.
       Live swap: style.relook() - walk() re-colors every widget option, canvas item, text / tree tag and menu entry
       (MEM remembers what each one stands for, so swaps never drift), setup_style() again, other ttk style calls
       replayed (_STYLE_LOG), themes.notify() for self-painted canvases (title bars, meters). ttk faces = bevelled
       PhotoImage elements per pack (no PNG files): TButton, Primary, Danger, list headings; switches per look.
       Shell: title bars / Toolkit menu head painted by the pack (gradient + texture, no ornaments), Toolkit button
       follows the accent, Shell.relook. Meters (themes.Meter: segments / bar / runes / ticks / orbs): trade limits in
       the status strip and the limits window, mod rolls. Price checks side panel: item card (pack's name band) +
       Item / How it's priced / Raw (SETTINGS detail_tab). Settings › Appearance: theme cards (live), accent "The
       theme's own" + the old six, text size (restart). look_settings() migrates once (theme_packs). New icon
       (tools/make_icon.py): chest with a toolbox lid and a hex-nut lock. check_contrast: every pack x accent.
       test_v2600; test_v200 / v2400 updated.
  2.59.0
       Settings cleanup 3+4 (feedback: one window only, one Overlay screen, F6, then the rest of the standard).
       merged_page: always one window (merged_on() True; merged_set(layout) only; LAYOUTS Panel / Strip; no × glyph;
       overlay_hide_toggle + mg_hidden). Separate timer / helper windows and _tracker_ov_canvas gone. Overlays hub:
       no tabs (ovh_bar None), module title "Overlay", one Options screen with Timer, MECHANIC HELPER and NOTES;
       overlay_lock(on) = the one lock (timer, switches, note). Hotkeys: tracker:key_overlay F6 (ev "overlay"); no
       notes key. Settings: Price checking page (build_pc_settings; pc_vars shared by the toolbar, Stash tab row,
       Wealth; acc_var = the one account, acc_link / league_link chips; copy marker moved here), Tools page
       (rates_auto), General › Game (Client.txt via tracker_set_log, poe_title), Advanced › Fine tuning (FINE:
       range_factor, min_results, spread_warn, stale_days, toast_secs, learn, tray, memory / model shortcuts),
       settings_open(page, anchor), settings_search (index of section frames). Chat commands save as you type
       (ov_save_soon); no Save & apply. test_v2590; old tests moved to one window.
  2.58.0
       Settings cleanup 2 - one Appearance tab (standard rule 4): build_overlay_look moved from the Overlays hub into
       Settings › Appearance (THE APP: launcher, wallpaper, clock, look of the app; OVER THE GAME: style, one window +
       layout, opacity, Notes text size - notes_font_var / on_notes_font). OVH_TABS loses "Appearance";
       ovh_open("Appearance") -> appearance_open() (scrolls to OVER THE GAME). Notes: no Font and Colors card
       (build_notes_look, ov_pick, _ov_swatch gone); note_colours() = pal() field / text for every look, the font
       the style's. Copy marker: no color box; marker_colour() from the style. test_v2580; old tests updated.
  2.57.0
       Settings cleanup 1 (the Settings Organization mockups; standard rule 3): every key is set in
       Settings › Hotkeys only. all_hotkeys' third field is now its group (Price checks, Regex, Overlays, Money Makers,
       Chat commands) - headings on the page; ledger_key editable (checks:ledger_key); each chat command with a
       command gets an editable row (cmd:<i>, saved on overlay.cfg commands). Regex (_rx_key_text), Notes Show / hide
       card (_notes_key_text), Session timer Options (_tk_keys_text) and Chat commands (_chat_keys_text, key column
       read-only) show their key with a button: hotkeys_open(kid) opens Hotkeys and lights that row up. test_v2570.
  2.56.2
       Remnant tags (feedback: too long on screen, too slow to show, too bold and big): AUTO_POLL 0.7 -> 0.35 s (shows
       about twice as fast; gone ~0.7 s after the book closes), SHOW_SECS 30 -> 12 for the key, and a closed book
       now clears the key's tags too. Tags: 14 px x UI scale (min 11; was 16, bold), plain weight (best bold + ★),
       colors from the overlay style (pal(): bg / text / muted / line, best = warn, on parchment head ink), the
       parchment texture behind the text (texture(calm)); tips box a touch smaller, textured. test_v2370 format.
  2.56.1
       Strip: resizable left / right only (OverlayWindow resize_axes="x": e / w edges, no height change),
       width saved as tracker cfg "sw"; _mg_strip_widths gives the smallest width that shows everything (mg_strip_min
       = the window's min width); extra room goes to the area name (up to 120 px) and the note's first line.
       _mg_on_screen: every merged window is moved fully onto its screen when built (a locked strip past the edge
       couldn't be reached), a strip wider than the screen made narrower. ONE opacity slider (ov_op_vars["all"])
       sets the timer, the Mechanic Helper bar, Notes and the one window. "Classic dark (2.42)" -> "Classic dark".
       test_v2550 extended; v230 / v2430 / v2490 for the one slider.
  2.56.0
       Farm Ledger redone, part 1 (the Farm Ledger Redesign mockups): SetupCards (cards with name, what,
       runs/logs, div/hour, a counting dot; click picks, Ctrl+click several, right-click = fl_setup_menu; answers
       selection / selection_set / exists like the old list). Header + one primary Log loot; the counting strip
       (fl_status + fl_dots, a dash per run of this log). THE VERDICT: "Makes / Loses about X div an hour" (fl_kpi
       "ph"), why in words, how it ranks (_fl_rank). TILES: profit, return on cost, average run, loot, cost, runs.
       fl_draw_money: where the money comes from (top 3 drops + the rest). The sheet keeps its room in a short window.
       No setup: _fl_empty_page (3 steps, Make my first setup / Start from a strat / Import a CSV). Compare says who
       wins first (fl_compare_say). test_v2560; test_v2450 takes a maximized screenshot too.
  2.55.1
       The item box (ins_preview, Price checks + Insights): Esc, Space or a click anywhere that isn't on it
       closes it (_ins_pop_hooks: bind_all space / ButtonPress-1/3, set up once; app.hk_esc closes it before Esc
       minimizes). The same row clicked again leaves it closed (ins_pop_toggled_off). A click ON the box keeps it.
       test_v2530 extended.
  2.55.0
       One overlay window (merged_page.py, MergedOverlay; from the mockups, every style kept): the
       Session timer, the Mechanic Helper and Notes in one OverlayWindow. tracker cfg "merged" (default on) and "layout"
       (panel / strip); "mx"/"my" (+ "mw"/"mh" with Notes in it), "mlocked". Parts show while on: the timer (mg_timer,
       Show timer / a session), the switches (alerts_bar), Notes (notes_visible; embedded in Panel - the Overlay's own
       tabs + Text, Overlay.merged_host / _embedded(); in Strip and Minimal the note is its own window dropped under
       it, merged_notes_drop). × closes all three. Merged off = the three windows of 2.54 (merged_set rebuilds).
       New looks (overlaywin LOOKS): codex (obsidian, bronze corner_marks, caps headings, green-tinted on cells:
       on_bg / on_line) and minimal (no title bar: OverlayWindow titlebar=False; lock and × drawn; short names).
       Strip: no title bar, one 40 px row. Overlays › Appearance: "One window" switch and Layout. test_v2550.
  2.54.1
       Manual feed: the price is optional - no price keeps the item with no listing (fed.div NULL, 0
       copies) and only rates the ticked mods High; no price and nothing ticked says there's nothing to learn. "Counts
       as N listings" is gone (it made no sense): Market.feed writes ONE listing per priced item. Fed list / CSV lose
       the counts column. test_v2510 updated.
  2.54.0
       Money Makers filters renamed like the fields: "🧠 Thoughts per click" and "🖱 Clicks per hour" (were
       "Thinking at most" / "Clicks at most"; still "this level or easier", said in a tooltip); column "Thoughts/click".
       Profit leaves the Session timer (feedback: it clashed with the Farm Ledger - money in ONE place): no Profit /
       Profit per hour tiles, overlay line, Options box (PROFIT_HOW, ask_count count-first), Wealth snapshot at Start,
       or profit columns in Past sessions and the sessions CSV. Stop ends at once. A line + "Open Farm Ledger" button
       (tracker_open_ledger). Old sessions keep their saved profit in sessions.json; it's just not shown. test_v2540.
  2.53.0
       Price checks: a click on a row (Manual Add or a stash tab's list) shows the item's box - the same one Insights
       draws (ins_preview, key "pc": name in its rarity color, mods as in game - an advanced copy's { } lines and
       (min-max) ranges dropped - price, when added, listings seen). Ctrl / Shift clicks don't; a click on it, Esc
       or 20 s closes it (app.pc_preview_at). The Session timer softer (feedback: 2.51's text "a bit too harsh"):
       rows 10 plain, the time 20 bold, Profit bold; the halo thinner (4 sides, no corners) and nearer the page
       (#e6d6b2). US spelling in every user-facing text (UK -> US: color, gray ...); Notes' card "Font and
       Colors". test_v2530.
  2.52.0
       Menus tidied (feedback: opacity was in the Session timer's options AND in Appearance): every setting in one
       place. Opacity only in Overlays › Appearance - the Session timer's Options and Notes' card link there (no
       tk_opacity / ov_opacity any more). The clock-on-the-timer switch moved from Settings > Appearance > Clock to
       Overlays › Session timer › Options (next to Lock); Settings links there. Notes' card: "Font and Colors".
  2.51.0
       Mod book › Manual feed (feed_page.py; idea: paste an already expensive tablet with its price so the app
       learns it - on top of how it learns now). Ctrl+Alt+C (while the tab shows) or paste an item, type its price
       (parse_price: 8, 8 div, 35c, 2 ex), pick how much it counts (1-10 listings; MIN_WITH = 8 decides a mod) and
       Feed it: Market.feed stores it in table 'fed' and as listings 'fed:<sig>:<n>' at that price - the listings
       Market.stats learns from, like save_sale; never expire (seen refreshed at start); feeding the same item again
       replaces it. Optional: rate its ticked mods High (set_rules). Each mod shows what the Mod book thinks before /
       after (Market.standing). Fed so far: list, Forget (unfeed), CSV. Readability (feedback: the timer was "barely
       legible"): a halo in the page color round every letter on the parchment (CanvasText halo), a calmer texture
       under the text (texture calm), the timer's text a size up and bold; the Opacity note says 95-100% reads best.
       test_v2510.
  2.50.0
       Overlays: the Look tab is "Appearance"; Style and Opacity explained (100% = solid ... 24% lowest), with a % next
       to each slider; runeshape tips only on the Mechanic Helper tab. The Mechanic Helper bar stands on its own (the
       user: "a different bar, independent of the session tracker"): "Show the Mechanic Helper bar over the game"
       shows it timer or not (tracker_helpers_sync at start and on the switch; tracker_helpers_paint). Notes' own
       color card: "Colors and font (Classic style)". Fixes from a screenshot: the Mechanic Helper icons
       were 9 pt and a dark green that read as black - now 12 pt, brighter green / red on parchment; the clock ran
       into "Session" on a narrow timer - OverlayWindow.bar_note says when it doesn't fit, and the clock goes to the
       top right of the page; the bar moved up a few pixels when locked at the screen's bottom edge - it was kept
       inside the work area (without the Windows taskbar); now the whole screen (style.monitor_rect(full=True)).
       Report a bug (feedback: it reached Discord): no name / contact box, Tab moves to the next box (text boxes
       typed a tab), the buttons are packed first at the bottom so a short window squeezes the preview instead.
       test_v2490 (more checks), test_v2480, v2380 / v2430 / v2440 updated.
  2.49.0
       Settings (a cog) is the first thing on the dock; Toolkit (the menu) sits at the left end of the taskbar, where a
       Start button would be (shell: dock tag "settings", taskbar tag "tkbtn"; with the dock hidden Settings shows on
       the taskbar too). Every ttk.Checkbutton is a modern switch (style.switches: a "Switch.indicator" image element
       in the TCheckbutton / Bar. / Mod. layouts - same widgets and variables, Pillow-drawn, theme colors). test_v2490.
  2.48.0
       Taskbar (there whatever window is open; feedback_page.py): "⬆ Update x.y.z" when GitHub has a newer release
       (a quiet look 15 s after start and every 6 h, plus every other update check; click = Check for updates, which
       asks first) and "🐞 Report a bug": a form (title, what happened, steps, expected, optional contact, optional
       last 40 lines of error_log.txt) that shows exactly what is sent. It goes to the board server's POST /bugs,
       which opens a GitHub issue with its own token (Worker secret GITHUB_TOKEN from the repo secret
       BUGS_GITHUB_TOKEN; 5 a day per address, table bug_limits) and posts to Discord (DISCORD_WEBHOOK). Without the
       token, GitHub's new-issue page opens filled in. .github/workflows/issues-discord.yml posts every other new
       issue to Discord. test_v2480.
  2.47.0
       Overlays › Look: the four PoE2 looks of the 2.43.0 mockups, all to choose from - Runeshape parchment (default),
       Relic tooltip, Carved frame, Quiet HUD - plus Classic dark (overlaywin LOOKS / PALETTES, skinned()). Feedback:
       the 2.43.0 parchment didn't match mockup C and was "too clean". Now: a grungy parchment made at run time
       (overlaywin.texture: grain, fibers, stains, burned edges - Pillow, no image file), drawn titles and buttons on
       canvases (no flat boxes on the texture), the mockup's Session layout (title + clock on the bar, the big time,
       two columns: Map 9:54 | Oasis, Maps | Avg, Profit; CanvasText answers like a Label), drawn Mechanic Helper
       cells (◆ on / ◇ off; ✓ / ✕ on the HUD), Notes as a page on the parchment. Remnant tips follow the look.
       Price checks › Stash tab: "＋ Tab" is a button. Who we build for (PoE players are utilitarian: data, how it
       was worked out, sort / filter / export, depth one click away) is in ROADMAP, README, strats/README, the
       module docs and the handovers. test_v2470.
  2.46.0
       Strat guides as CSV (user: "csv files and a standardized formatting that matches the run tracker"): rows of
       section, field, value, note (moneymakers.to_csv / from_csv / read_any; .txt and JSON still read). The note
       column is help (the options for each field). New optional fields: items [{kind, base, name, count, lasts,
       key_mods}] and ledger {runs, minutes, cost_per_run_div, loot_per_run_div, profit_per_run_div, div_per_hour}
       - the Farm Ledger CSV's names. Download Format / Export / Import use CSV; build_strats reads .csv. Farm Ledger:
       Export ▸ Strat guide (CSV) makes a guide from a setup (fl_strat_guide). Cost now (stratcost.py, Engine
       StratCostJobs): a strat that lists items gets one trade search per item (base + key mods, cheapest first,
       trade.cheapest_real) once a day while Money Makers is open (strat_costs.json); its page shows the cost a run
       and each item's part; "Check what it costs now" in its menu. The strat page shows your Farm Ledger numbers
       (was the old Run tracker's). test_v2460.
  2.45.0
       Money Makers > Farm Ledger (was Run tracker; ledger.py = data + figures + CSV, ledger_page.py = UI). A SETUP =
       strat (optional) + waystone + tablets / other items (count, runs each lasts) + atlas trees and notes + other
       costs; a change after logs = a new VERSION (what_changed). Items: Ctrl+Alt+C while the setup is open; priced by
       the price checker out of sight (record src "ledger", removed once priced; never loaded back) or your own price;
       then "which mods matter?" (key_mods). Runs: counted from Client.txt (breach_area -> fl_area: a new map = a run,
       back through a portal isn't; log_wanted includes it) or a key (Ctrl+Alt+N). Every N runs (per setup) the loot
       box (parchment OverlayWindow) opens back in the hideout: Ctrl+Alt+C drops land in it as "7 Divine Orb" lines,
       priced item by item from poe.ninja (Wealth's prices, remnant_names_values); type the loot or the profit and the
       other follows; Later / Skip. Sheet: logs or loot, sort, filter (words, >1 / <0), double-click edits, Σ row,
       Ctrl+C rows; figures; chart; compare (setups, or one setup's versions); CSV (CSV_LOG_HEAD), every drop, setup
       file (.json), summary. The Run tracker's runs move in as "Imported runs". test_v2450.
  2.44.0
       Overlays (was Session tracker): everything over the game in one window, one tab each - Session timer (the old
       tracker page), Mechanic Helper (the old Alerts panel), Notes (was its own window: the Notes module is hidden and
       shell.open("notes") opens this tab) and Look (style + an opacity each + runeshape tips; was Settings >
       Appearance, which now links here). The ⚙ on the Mechanic Helper bar opens its tab; Settings > Hotkeys says
       "Overlays › ...". Module key stays "tracker". test_v2440.
  2.43.0
       The windows over the game look like the Expedition remnant's reward book (mockup C):
       parchment in a dark leather binding, ink text, a serif title (overlaywin LOOKS / pal(); Classic dark kept as a
       choice). Session timer, Notes and the Helpers bar - now "Mechanic Helper" (on = filled green diamond, off =
       hollow red). Settings > Appearance > Over the game: the look, an opacity slider each (timer, helper - new
       cfg hopacity - and Notes), applied at once; still moved by the title bar and locked with its lock.
       Remnant: hovering a reward put the game's tooltip over the book, the next read found fewer rewards and their
       tags vanished under the mouse. Now tags only come or update while the book is open (remnant_keep); the book
       closing clears them. The runeshape tips were placed from where the tags were on screen - nowhere yet on the
       first show - so they only came with a later redraw; now placed from the tags' own positions, shown with the
       first prices, parchment too, and switched on / off in Settings as well. test_v2430.
  2.42.0
       Price checks: separate lists. Manual Add (Ctrl+Alt+C copies) and Stash tab results no longer mix: each record
       has a src ("manual" or "tab:<id>") and the list shows only the one picked. Stash tab gets its own tabs (one
       per stash tab, each with its own price and currency, "＋ Tab" to add, right-click to rename / delete), shown as
       "Name (count)". Clear and Reprice act on the list showing. A copy while a tab list shows switches to Manual Add.
       The old single tab setting becomes "Tab 1". test_v2420.
  2.41.0
       Waystone prices: a player's corrupted T15 (IIR 28, pack 27, drop chance 150) showed 18 div, Medium - the
       search found 3 listings (8, 18, 20) and took the middle one, with Listings set to "Any" (offline / whisper
       sellers' asks count; a player's own search was Instant Buyout). Now a thin waystone result (under 5) is priced
       at the cheapest real offer (trade.cheapest_real: price fixers under a fifth of the median left out), never
       "High"; and Listings: Any is called out in the label and lowers High to Medium. test_v2410.
  2.40.1
       Stash tab (and Wealth) read every item of a big tab. A player's tab: 455 listings, 2.40.0 read 234 - 201 and
       220 rare tier-15 waystones were each one item-level slice of over 100 (one search returns 100). wealth_children
       now goes further when a slice is still too big: every single item level ("82+" -> 82 ... ILVL_TOP 86), then
       corrupted / not (misc_filters), then the same slice read from its other end (sort indexed desc, "__sort") -
       that last one is an extra view, so the slice's own 100 are kept too (both_ends). test_v2401: a stand-in trade
       site with the real filters reproduces 234 on 2.40.0 and reads all 455 now (51 searches).
  2.40.0
       Runeshape tips: next to the remnant price tags, a small click-through box "Runeshapes - community picks" with
       the S and A tier runeshapes for loot (remnant.RUNE_TIERS: S Opulent, Power, Oath; A Time, Death, Soul, Bond -
       mixed reports). It comes and goes with the tags (part of rm_win), left out of captures. Runeshapes are symbols
       in game, so the app can't tell which a remnant has - it's a cheat sheet. Sources (Nov 2026): epoe.io
       Expedition guide (Larky's priorities), timesaver.gg Aldur's Saga guide, game8 runeshape list. Alerts row:
       "Runeshape tips" switch (remnant cfg "tips", on).
       Fix: Stash tab's currency still went back to Divine Orb - the real cause: the box is built before the trade
       site's full currency list arrives, and Mirror isn't in the short built-in list, so a saved "mirror" showed as
       "Divine Orb" and Read tab then searched in divines. Now the name is saved too (pctab currency_name), known
       ids have names (KNOWN_CURRENCY_NAMES), Read uses the saved id when the box shows its name (pctab_cur_id), and
       the box is set again when the list arrives (engine -> "currencies_loaded"). After a pick the text is no
       longer left highlighted (selection_clear, focus to its window).
       Fix: Breach / Ritual banners had a black box instead of see-through text (like END DELIRIUM). Themes recolour
       every color handed to Tk, and the banners' key #010203 counts as a dark blue - under Amethyst the window
       became #020103 while the key stayed #010203. The key is now never recoloured (style._THEME keep). (Likely
       also the cause of 2.37.0's black remnant screen.) The Delirium banner runs in its own process, so it was fine.
       Fix: the Ritual "leave the map" reminder never fired - a player's ritual_log.txt showed the watcher stopping
       the second it started, every time: in the exe its stdin wasn't the app's pipe, so it read "end of input" and
       quit. Now (delirium_runner): in the exe the pipes are opened from the OS handles whenever they are pipes; the
       app passes --parent <pid> and holds a named mark (utilities.app_mark); a helper whose pipe ends while the app
       is still there keeps watching and quits when the app goes (after_stdin_ends). Same for the Delirium helper.
       Also: going back into the same map (same area + seed) no longer forgets its ritual count (rt_where).
       Runeshape tips list every runeshape (33): S / A players' picks with what they do, then B / C / D grouped by
       effect (B some upside, C only tougher monsters, D hazards) on one line each.
       Stash tab reads the whole tab (it stopped at 20): reading was queued BEHIND the pricing it creates (prio 4 vs
       0-2), so after two fetches (20 items) pricing those 20 took every trade-site request and the rest waited for
       minutes. tabreader.PCTAB_PRIO = -1: the whole tab is read first (progress "read X of Y"), then priced. And
       tabs with over 100 of one kind (one search returns at most 100): wealth_children splits rarity -> base before
       item level - waystones by tier 1-16 (map_filters), tablets / jewels by base type (from tabs.txt / jewels.txt,
       query "type"). wealth_query takes "__type" and "group/filter" keys. Wealth syncs split the same way.
  2.39.1
       Expedition Remnant Price Checker: rewards poe.ninja doesn't list (a player's Warding Rune of Obsession - 15
       other Warding runes are listed, not that one) got no tag at all; and a look-alike was only just kept out
       ("... of Obsession" vs "... of Protection" = 0.824, cutoff 0.84). Now a match also needs the last word to
       match (remnant.same_ending, >= 0.75 - OCR slips still pass), and a line with an amount ("1x ...") that
       matches nothing is tagged "no price" (remnant.explicit_qty; junk never has an amount).
  2.39.0
       In-game clock: the Session timer shows the time and date (shell.clock_text - your 12 / 24-hour setting), small,
       on the session time's row so the timer needs no extra line. Settings > Appearance > Clock: "Also show it on the
       Session timer (in game)" (tracker cfg "clock", on by default); changing 12 / 24-hour updates it at once.
       Fix: the Helpers bar (2.38.0) could be off the screen - first placed right under the timer, which often sits
       at the bottom of the screen. Now under it if it fits, else above it; any saved place off the screen (a
       monitor unplugged, another resolution) is pulled back on (tracker_page._helpers_on_screen, monitor_rect).
       Expedition Remnant Price Checker tags use short units, no space: 16ex, 20c, 29d (pricefmt.fmt_short). It makes no
       sound any more (by request): no beep, no Sound box on its Alerts row.
       Fix (2.38.0): blocking the wheel on dropdowns with "break" also stopped the page around them scrolling
       (Settings); the TCombobox wheel binding is now replaced with a no-op, so the page scrolls, the pick stays.
  2.38.0
       GGG ToS safety check: TOS.md (the 7 rules), a copy at the top of README / ROADMAP / board, strats and linux
       READMEs / both handovers, notes in every screen watcher; tools/check_tos.py (game-memory / injection APIs,
       mouse automation, packet tools, input-automation imports, SendInput outside overlay.py, mouse INPUT, a
       screen-capturing file that can send keys) runs in checks.yml on every PR and in release.yml before a build.
       Remnant price tags: one small solid click-through window per tag, left out of screen captures
       (SetWindowDisplayAffinity WDA_EXCLUDEFROMCAPTURE) - 2.37.0's single game-sized color-keyed window showed
       black on a player's PC, and Auto, capturing its own black window, toggled it on and off.
       Helpers bar: its own OverlayWindow (resizable=False: as big as its content, never cut off; "Remnant" was),
       shown and hidden with the Session timer, placed / locked / closed on its own (tracker cfg hx, hy, hlocked;
       × = alerts_bar off). tracker_helpers_build / _destroy; style.Tooltip on its ⚙.
       BETA tags: Module.beta (tag, still shown; labs = tag + hidden unless Labs) - Money Makers; shell.is_beta.
       SegBar badges={"Stash tab": "BETA"}: the tag sits inside the Stash tab button (it was a loose label next to
       the bar, read as part of the hint).
       Fix: Stash tab's currency "went back" (to Divine) after picking e.g. Mirror of Kalandra - on Windows Tk sends
       the mouse wheel to the focused dropdown, so scrolling anywhere changed it (and it was only saved on Read).
       listkit: the wheel never changes a TCombobox; the tab's currency is saved when picked and focus moves off.
       The tab search adds sale_type "any", like the site's own link. (The site shows 20 at a time with "Show
       more"; the reader always took all 100 a search returns and splits bigger searches, so it reads more.)
  2.37.0
       Expedition Remnant Price Checker (remnant.py, remnant_page.py). A
       helper like Delirium / Breach / Ritual: its row in Session tracker > Alerts (on / off, dot, Sound, Test, status
       line) and a green / red cell in the timer's Helpers bar (click = on / off). With a remnant's reward list open,
       its key (Ctrl+Alt+R, Settings > Hotkeys) takes one picture of the game window, reads it with Windows.Media.Ocr
       (PyWinRT winrt-* packages, --collect-submodules winrt), matches lines to poe.ninja names (WPRICES, all exchange
       types + uniques; split_qty for "x3" / "3x"; difflib >= 0.84), and draws click-through price tags right of each
       line (amount x each, best one ★, "no price"); the key again or 30 s takes them off. Auto (on by default):
       a light watcher looks at where the reward book opens - remnant.AREA, in game heights from the top-left (the
       game scales its UI by height and anchors the book left; measured on a player's 2560x1440 screenshot) - every
       0.7 s while the game is in front; only when that spot is mostly parchment (parchment_share >= 0.35, from a
       40x40 thumbnail) and changed does it read the text; tags come and go with the book. A key press that finds the
       list elsewhere (UI scale) learns that spot (learn_area). Client.txt logs nothing for remnants. Off Windows / without an OCR language it says why (status warn). CI checks.yml
       runs remnant.selftest() on Windows (informational). Credit: the idea is PoE Ancients Price Helper by Pedro
       Quitério (github.com/pedro-quiterio/PoeAncientsPriceHelper) - not open source, so no code, text or images
       from it; credited in About, README, THIRD_PARTY_NOTICES and the code.
  2.36.0
       Polish 3 - Context menus. listkit.list_menu puts a list's own actions on top (tree.menu_actions(sel) ->
       [(label, fn, enabled, accelerator) | None]), then the standard Copy / Select all / Delete / Undo. Price checks
       rows: Re-price, Copy name, Open on trade site, Mark listed / sold / removed. Market Insights: Show in Price
       checks, Price it again, Open the search. Regex Favorites: Copy, Open in Build a search, Use for the Regex key,
       Rename. listkit.menu_key: the Menu key / Shift+F10 opens the right-click menu of whatever has the keyboard
       (lists at the focused row, boxes too) - every menu works without a mouse. Wealth, Game search, Map library and
       Money Makers keep their own menus (reached by the key too).
  2.35.0
       Polish 2 - Toasts. soe2/toasts.py: one toast system - info ℹ / success ✔ / warning ⚠ / error ✖ (icon + edge
       color, never color alone), stacked in the app's bottom-right corner (at most 4, newest at the bottom), paused
       while hovered, timed by text length (4-20 s; errors x1.5, with buttons at least 10 s), never activated / focused
       (WS_EX_NOACTIVATE), lifted while the app is always-on-top. Last 20 in toasts.json and Settings > Advanced >
       Recent messages. app_toast() now uses it (kind= or guessed); simple messagebox infos became toasts (update
       check, Export / Import / Remove imported rules). style.Toast (the popup at the mouse over the game) stays.
  2.34.0
       Polish 1 - Foundation. Design tokens in style.py: SPACE (4 8 12 16 24; 0-2 for hairlines), text sizes SMALL 9 /
       BODY 10 / HEAD 12 / TITLE 16 (+ DISPLAY 18-28 for glyphs and big numbers), ROLE + role() color roles. Every
       font size and padding in soe2 moved onto them (tools/check_tokens.py --fix; canvas create_text and "# token-ok"
       lines are left alone). Button hierarchy: Primary.TButton (was Accent.TButton - kept as an alias), TButton,
       Quiet.TButton (flat), Danger.TButton (dark red; Delete, Clear list, Remove ...). Contrast: style.contrast() /
       text_on() - the primary button's text is light or dark by WCAG contrast (light text on orange / gold / lime /
       teal / ice was 1.9-3.4 : 1); accent-derived button colors are no longer recoloured by themes (Ice accent).
       tools/check_contrast.py: every text pair, every theme x accent >= 4.5 : 1. .github/workflows/checks.yml runs
       check_version, check_tokens and check_contrast on every PR. Roadmap reordered: Toasts 2.35, Context menus 2.36,
       Expedition Remnant Price Checker 2.37, more item types 2.38, stash order tool 2.39, Responsive 2.40, Hover / focus 2.41, Visual
       hierarchy 2.42, Linux last.
  2.33.1
       Map library: the "✖ Avoid" rank button was cut off (ttk width -7 = at least 7, grows to fit).
  2.33.0
       Child tools (shell.py: DeskWindow.add_child, Shell.children / link_children / paint_children; Module.parent).
       The layout rule for the whole app (ROADMAP "How the app is organized"): top-level tools / child tools / tabs. A
       child tool is a button in its parent's title bar, indented under it in the Toolkit menu, its window is titled
       "Parent › Child", and it is not on the dock or desktop. Session tracker › Map library (the placed 🗺 button is
       gone); Price checks › Mod book, Under the hood, Market Insights (Labs: its button shows only with Labs on).
  2.32.0
       Map library (maplib.py, maplib_page.py, modules/maps.py - its own window; the Session tracker has a 🗺 button).
       mapdata.json (tools/build_mapdata.py from RePoE world_areas): 209 endgame areas by kind - Map, Tower, Unique
       map, Citadel (lineage / special: citadels, Jade Isles), Pinnacle (Simulacrum, Arbiter, Breach, Ritual, Abyss,
       Expedition ...), League area (Trials, logbooks ...). gamelog.area_kind now asks the library: pinnacles and league
       areas count as runs; claimable "MapHideout..." are hideouts (they counted as maps before); an unknown area of
       level 65+ that isn't a hideout / town / campaign is learned on its first visit (maps_learned.json, by the name
       the game shows; "Not a map" forgets it for good). Ranks S A B C D / Avoid by map name (map_ranks.json in the
       data folder - kept across versions): buttons, right-click, keys S A B C D X. Export / Import (.json,
       format soe2-map-ranks); import and "Take the community's ranks" ask Replace all / Add and update / Add new
       only. Community: your ranks are votes in the hourly community sync (board map_votes, /maps/ratings); the
       library shows the community's average rank with its vote count. This session's maps and the in-game timer
       show the rank.
  2.31.0
       Community Mod book (communitymods.py; board /mods/batch, /mods/stats, /mods/ratings). Once an hour (and on
       close) the app sends a SUMMARY of the listings its price checks stored since the last time: per (base, mod)
       count + median, per base the same - no ids, names or items - plus changed Mod book rules as votes. Keyed by a
       random install id (contrib_id; the board keeps its sha256), one batch per 45 min, weight per batch capped,
       so one install can't swing a price; summaries (not listings) keep D1 writes inside the free plan. The server
       keeps a weighted mean of ln(median) per (league, base, mod) and per base -> pooled median + lift. On by
       default after a one-time notice (Don't share = SETTINGS share_prices False; Settings > General switch);
       reading works either way. Used where your own data is silent: refresh_learned adds pooled highs
       (n >= 12, 3 summaries, lift >= HIGH_LIFT, median >= Valuable mod) as LEARNED "from": "community" unless this
       league's own data decides the mod; rebuild_community adds mods >= 60 % of >= 3 players rate High
       (BOARD_RATED). Your rules always win. Price checks shows "🌐 Community: N mod prices · you added M"; the Mod
       book says "High (community ...)" / "Community ★ (x of y players)".
       Removed: the Ritual "Capture" button (Session tracker) and Settings > Advanced > Lag finder (perflog.py).
       Price checks: "Stash tab" is marked BETA with a warning note (pc_beta: may not work as intended, limited use);
       the "Ctrl+Alt+C only" toolbar box moved to Settings > Hotkeys as "Also add items copied another way" (the
       same SETTINGS hotkey_only, shown the other way round, off by default).
  2.30.0
       Money Makers: a Community board instead of GitHub issues for sharing. Server = board/ (Cloudflare Worker +
       D1, deployed by .github/workflows/board.yml). No login
       (Discord OAuth was dropped: its app rules were too much): the first post / vote / report asks for a display
       name, POST /auth/join returns a key (board_session.json); JOINS_PER_DAY (5) new accounts per hashed IP per
       day stop vote stuffing. Posts (strats + one-liners) are live at once, checked against the same layout
       (board/src/schema.json, written by build_strats.py); upvotes (one per player); reports (3 distinct = hidden
       until an admin looks); admins (entered the ADMIN_KEY secret: 👤 > Become admin) hide / un-hide / delete /
       ban / promote; promoted posts come from
       GET /official and join the Official list. App: soe2/board.py (client, never raises); Strats tab gets
       Official / Community / Mine, ▲ column, Top / New, Upvote, 📤 Post to Community, Report, Copy to Mine, admin
       items; your own posts edit through the same form. Lucrative Strats show Community one-liners too. The
       board's address comes from the shared strat file (board/url.txt -> moneymakers.json "board_url"), so it
       can be switched on without a release. GitHub issue forms and MM.issue_link are gone.
  2.29.1
       Fixed: updating opened console windows over and over ("Pinging 127.0.0.1 ..."). 2.26.3's swap .bat waited
       with ping and was started with CREATE_NO_WINDOW | DETACHED_PROCESS - Windows ignores NO_WINDOW with
       DETACHED, so cmd had no console and every ping / move opened a new one. The .bat is gone: the downloaded
       exe is started as  StashOfExile2_update.exe --finish-update <old exe>  (updates.finish_update): it waits
       for the old exe to close, copies itself over it (taskkill /t of what's left after 15 s), starts it and
       ends; after 2 minutes it gives up, writes update_log.txt and runs the new version from where it is.
       At start-up cleanup_update deletes StashOfExile2_update.exe and any old .bat. Note: updating FROM an older
       version still runs that version's .bat one last time.
  2.29.0
       Money Makers rebuilt to the original Task 11 plan (2.28.0 shipped the first draft). SCHEMA 2:
       what a strat IS = category + type (TAXONOMY: Mapping > Breach, Crafting > Tablet crafting ...), shown in a
       browser with counts; everything else = tags (TAG_GROUPS: Also uses, Farm type - City area / Sacred Bloom
       ..., Budget, Play style - checkboxes); tag search matches the type too. Effort picked from lists: Thinking
       (Autopilot / Easy / Moderate / Hard / Big brain = thoughts_per_click 1-5) and Clicks per hour (Chill /
       Steady / Busy / Frantic) - no dots, no typed numbers. Dedicated sections: tablets, waystones, atlas /
       master setup, craft steps; waystone tiers 1-16 (filter); est_cost / est_profit (were investment /
       profit_per_hour). "Download Format" = the blank layout as .txt for Notepad (to_text / from_text; Import and
       build_strats.py read .txt). New tabs: Lucrative Strats (one-liners: strats/oneliners.json,
       my_lucrative.json, lucrative.yml form) and Tablet Crafting (trans/aug -> 2 bad: alch / 2 good: regal +
       exalt -> 4 junk: keep to reforge; Check my tablet from the clipboard; valuable tablet mods from Mod book +
       learned prices + regex data; regex copy; trade link per mod). MM.migrate() converts 2.28.0 strats (yours,
       and a cached shared file); a 2.28.0 app refuses the schema-2 file from GitHub and says to update.
  2.28.0
       Money Makers (modules/money.py, moneymakers.py, moneymakers_page.py): community strats in ONE standard layout
       (schema 1, strats/README.md; validate() is shared by the app, tools/build_strats.py and CI .github/workflows/
       strats.yml). Strats live as one JSON file each in strats/ -> moneymakers.json (bundled) -> also fetched from
       GitHub main (raw) when the window opens, at most every 12 h, or with "Check for new strats" - newest
       "revision" wins, a file for a newer schema is refused. So a merged strat reaches everyone without a release.
       Rated by Thoughts per Click (1-5) and Clicks per hour (Chill/Steady/Busy/Frantic bands). Your own strats
       (my_strats.json): add / edit / import / export, Share = a GitHub issue form (.github/ISSUE_TEMPLATE/
       strategy.yml) filled in by URL. Run tracker of its own (money_runs.json): Start / End run, optional profit,
       runs per hour, div per hour; "Your runs" shows on the strat.
  2.27.0
       Chat commands left Utilities: it is a tab in Settings now (build_chat_window on the "Chat commands" page;
       modules/chat.py removed; shell.open("chat") opens that tab, so old saved layouts and links still work).
       ROADMAP: Money Makers -> 2.28.0, Map library -> 2.29.0, and a Polish series 2.30.0-2.35.0 (design tokens,
       responsive layout, hover / focus / micro-interactions, context menus, one toast system, visual hierarchy),
       all held to WCAG 2.1 AA.
  2.26.4
       Regex: both mod lists are a ttk.Treeview now (was a frame + labels + entry per mod). Tk laid out and drew
       hundreds of frame rows slowly on Windows - Jewels (207) and Gear (327) still lagged after the 2.26.2 cache.
       Filling a list takes 15-50 ms. Click a row to select it; click its Value cell to type 50 / 50-80 / <80 in a
       box over the cell (rx_edit / rx_set_value). The background row building (rx_warm) is gone.
       Price checks: the star legend moved up top, into the summary row. "Show all" is now "✕ Clear filters"
       (clears Category / Rarity / Type) and is only active when one of them is set.
  2.26.3
       Fixed: an update could hang with a console window flashing over and over. (1) The swap script waited with
       "timeout", which needs a console - run hidden it opened a new console every try; it waits with ping now.
       (2) Stopping a helper (Delirium / Ritual = the same one-file exe) only ended its starter process; the real
       one kept running and kept the exe in use, so the swap could never finish. utilities.kill_tree ends the whole
       tree (taskkill /t); the script also force-closes what's left of the old exe after 15 s, and gives up after
       90 tries with a line in update_log.txt instead of looping. (3) The app ends with os._exit(0) after closing
       for an update. Note: an update FROM an older version still runs that version's script.
  2.26.2
       (1) Regex: switching item type kept freezing (Lag finder: rx_build_lists destroying ~650 gear rows, up to
           0.8 s each time). Each type's rows are now built once and kept (canvas window swap); the other types are
           built in the background 25 rows at a time after Regex opens (rx_warm); rows only repaint when their color
           changes. A switch: gear 920 ms -> ~180 ms, also the first time. Rows know their own type (a background
           row's placeholder used to land in the showing type's search).
       (2) The window really opens maximized again: the first "normal" size while the window appeared was saved
           and wiped the "maximized" flag before it was used (since 2.23.1). Nothing is recorded until the start-up
           restore is done (_win_restored).
       (3) Price checks "Pricing 215" has a time from the start: the remembered seconds per item
           (SETTINGS price_secs_avg), or a guess from the pace's search allowance, until 3 items are done.
       (4) Price checks: the column is "Valuable mods" (no ★ in the heading) and a legend under the list says what
           the stars mean.
  2.26.1
       Fixed: "No module named 'cv2'" after changing the theme. restart_app started the new copy with this copy's
       PyInstaller environment, so it reused this copy's unpacked folder - deleted as this one closed - and cv2 (the
       Delirium / Ritual helpers) was gone. It now starts clean (PYINSTALLER_RESET_ENVIRONMENT=1, no _PYI_ /
       _MEIPASS variables), like the updater already did.
  2.26.0
       (1) Session tracker timer: the bar is "Helpers: ● Breach | ● Delirium | ● Ritual  ⚙" - a green dot is on,
           red off (amber: on but not working); click a helper to switch it on / off (alerts_toggle(key, want) now
           works without the Alerts panel being built); ⚙ opens the Session tracker window with their options.
       (2) Price checks: "⏳ Pricing 12 · ~1:30 left" chip next to Priced / Require Review (was only at the bottom).
       (3) Arbitrage FIX + BETA: GGG's history now names items by game id ("Metadata/Items/Currency/
           CurrencyModValues" = Divine Orb), so the three hubs never matched and no loop was ever found (0 of 1,449
           markets on the author's data; 347 after). arbitrage.HUB_IDS maps them back; cxnames.json
           (tools/build_cxnames.py, RePoE) names everything. A BETA badge and how-to on the tab; "gains" over 30 %
           are left out (thin one-sided hourly data) and the status says how many.
       (4) Settings > Advanced: "Slowness recorder" is now "Lag finder".
  2.25.4
       (1) Maximized last time -> maximized again: restore_zoom waits until the window is on screen and the start-up
           screen is gone (asking earlier did nothing on Windows: the author's settings said zoomed, yet it opened
           at 1280x800), checks, and asks Windows (ShowWindow SW_MAXIMIZE) if Tk didn't.
       (2) Settings > Advanced > Slowness recorder (perflog.py): for 5 minutes a watcher thread notes every time the
           window is stuck > 150 ms and writes the window thread's stack to perf_log.txt (also in problem reports).
           Measured here, tools open in 30-250 ms even with the author's real data, so the slowness is in Windows'
           drawing / something only on that PC: this finds it.
  2.25.3
       (1) Market Insights item preview: a saved line with # (waystones keep "Pack Size: #%") shows the line from the
           copied item with its real value ("Monster Pack Size: +32%") - insights_page.ins_with_value.
       (2) app_toast (the Fast pace warning, "Copied", new arbitrage loops) opens in the middle of the app, not its
           bottom-right corner. The price popups (style.Toast) open at the mouse on its monitor (2.25.2).
  2.25.2
       Popups open on the monitor you're using: style.monitor_rect (Win32 MonitorFromPoint / GetMonitorInfo work
       area) + place_near keep the Market Insights item preview and the price popups on the monitor under the mouse
       (they were clamped to winfo_screenwidth(), the MAIN monitor, so they jumped over to it). The start-up screen
       opens in the middle of where the app was last time.
  2.25.1
       Speed (measured with 2,200 Price checks rows, the author's list):
       (1) listkit: setting a row's tags keeps that row's stripe instead of restriping the whole list (every price
           that came in restriped all 2,200 rows: half of each update's time).
       (2) The total and category counts are added up once prices pause (update_total_soon, 250 ms) instead of after
           each price.
       (3) save_json writes with json.dumps (the C encoder) - json.dump streamed through the pure-Python encoder
           and saving a long list froze the app for seconds. session.json and value_log.json are written on
           another thread.
       Result: a price update 157 ms -> 9 ms; the longest freeze while the list saves 4.5 s -> 0.2 s.
  2.25.0
       (1) Copy marks: "Keep them until I double-tap Esc" (two fresh Esc presses within 0.5 s, winsys.DOUBLE_TAP;
           key repeat doesn't count) replaces holding Esc for 3 s, which didn't clear them for the author.
       (2) The +'s color: Gold, White, Red, Lime, Cyan, Magenta, Orange or Blue (copymark.COLORS,
           SETTINGS copy_marker_colour); picking one shows a sample + for 2 s.
  2.24.0
       (1) Copy marker: a small + instead of the ring (copymark.SIZE 16), shown for copy_marker_secs (Settings >
           General > Copy marker, 1-600, default 10) - or, with "Keep them until I hold Esc for 3 seconds"
           (copy_marker_hold), until Esc is held 3 s. The key watcher times Esc (winsys.KeyWatch.esc_since; Esc is
           never swallowed - the game still gets it); app.copy_mark_check clears the marks.
       (2) Price checks: "★ Valuable" column (one ★ per mod the Mod book rates High), shown right after Item and
           sortable. The stars no longer sit in front of the name. (Last in COLS / values, placed by displaycolumns.)
  2.23.1
       (1) The app opens where you left it: place, size and maximized (SETTINGS main_window, kept as the window
           moves and written 3 s after it stops). A spot that's no longer on any monitor (all monitors together,
           GetSystemMetrics virtual screen) keeps the size and lets Windows place it.
  2.23.0
       (1) Notes: tabs on the sticky note (overlay: cfg notes_tabs / notes_tab; + adds, double-click renames,
           right-click deletes; up to 12). The single note of older versions becomes "Note 1"; notes_text keeps the
           open tab for older versions.
       (2) Game search: "more ›" opens a result's whole text (one line per part) and every keyword; "less ‹" closes.
       (3) Exchange rates > Arbitrage: Live scan. GGG's Currency Exchange history is published per finished hour, so
           "live" = each new hour is read as soon as it's out (checked every 5 minutes while the app runs), and a
           loop that wasn't there the hour before pops up (app_toast). Settings arb_live.
  2.22.0
       (1) Regex for jewels (Ruby / Emerald / Sapphire / Diamond / Time-Lost) and gear (rings, amulets, belts,
           armor, shields, foci, quivers, weapons). tools/build_regexdata.py: MULTI kinds from several RePoE
           domains (misc / item / desecrated) kept by spawn tag; mods with the same text are one row; a line another
           mod shares word for word doesn't block a token; base names are noise; when no short token is unique the
           whole line is the token (^...$, numbers as \d+, mod["rx"]). Jewel type filter (base name), gear "Show
           mods for" slot boxes (list only). Ranges / maximums work the same. BUNDLED_DATA regexdata.json 2.
           Exact number patterns (regex.num_range writes \d, never '.', up to 9999) for whole-line tokens, lines with
           two numbers ("adds # to # ...") and mods that can reach 1,000+: checked over every roll of every mod.
  2.21.0
       (1) Price checks: "Sold for" + 💰 Mark as sold in the item's panel (mark "sold", Show: Sold). The sale goes in
           market.db (table sales, and as a listing "sale:<sig>" at the price it really went for) so the Mod book
           learns from real sales. Unmark sold takes it back out.
       (2) Regex: a mod's box takes 50 (at least), 50-80 (range) or <80 (at most). regex.num_range writes an exact
           number pattern with two characters before it and one after (no match inside a longer number; a term
           can't start with a space). Checked against every roll of every tablet / waystone / relic mod.
       (3) Regex Favorites: a "📋 Copy" cell on every row (one click copies) and a "✓ Copied" popup.
  2.20.0
       (1) Mod book tiers S / A / B / C / D (mods.TIERS, mod_tiers.json; not set: High = A, Normal = C). Tier column and
           "Tier for selected" buttons on the Tablet / Jewel mod rules pages. When no listing has all of an item's
           mods, the engine leaves out the lowest tier and searches again (then the next; at most 2 extra searches,
           never S) before "any roll" / "best mod alone". The price is labeled a floor.
       (2) Import rules really imports: rules go INTO your Mod book (mod_rules.json), your own export works as a
           backup, and differing rules ask "use the file's or keep yours". Export writes every rule of the page
           (High / Normal / Ignore + tiers, format 2) and still a "high" list older versions read. Waystone and relic
           pages can export / import too. (Before: an import only added outvotable "votes", your own file was
           refused, and nothing showed in the rules list.)
       (3) default_rules.json rebuilt from the author's current rules over the old defaults
           (tools/build_default_rules.py); BUNDLED_DATA bumped so everyone gets them. Your own rules still win.
  2.19.0
       (1) Copy marker: after Ctrl+Alt+C a gold ring shows for 10 s where the mouse was (soe2/copymark.py), so you
           can see which items you've copied. Up to 30 at once. Display only - a click-through, see-through window
           like the Delirium alert; sends nothing to the game, reads nothing from it (mouse position from Tk).
           Settings > General > Copy marker (on by default). Triggered from the key watcher's combo_time, checked
           on every clipboard poll (app.copy_mark_check).
       (2) Price checks: one ★ before the item's name per valuable mod (Mod book) - the gold rows now say why.
       (3) Release build: the first 2.19.0 build stopped at the release notes (Windows console cp1252 can't print
           "★"). tools/release_notes.py writes UTF-8 and lists every version since the last release.
  2.18.0
       (1) FIX: since late Oct 2026 the trade site sends each listing mod as a dict {"description", "hash", "mods"}
           instead of a string. fetch_rich stored str(dict), so every mod failed to match: the Mod book learned
           nothing and the listing check fell back to "unverifiable". trade.mod_lines reads the new format (text +
           the site's own stat id, used by verify_listings and market.record). market.repair_dict_rows turns the
           rows already saved that way back into mod lines + stat ids (once, on start).
       (2) Stash-tab marker listings out of market.db: your own tab prices (Price checks tab, Wealth tabs, every tab
           price you've used: SETTINGS own_markers) any price over 1,000 div shared by 3+ listings, and anything over 10,000 div
           (market.drop_markers, on start and when a new tab price is used). They topped Market Insights.
       (3) Market Insights: click a row for the item drawn like the game's tooltip (name, mods, price). Old rows with
           no saved mods are left out of "Most expensive listings seen".
       (4) Wealth and Price checks share the stash tab: "Use my Price checks tab" in Wealth, "Count it in Wealth"
           after reading a tab. Wealth's magic / rare pricing follows Price checks' "Price manually" rule
           (pricefmt.needs_manual_price).
       (5) Price checks: the "Under the hood" and "Wiki" links are gone (summary row, item panel, the "not priced"
           card). Under the hood still opens from Settings > Advanced.
       (6) Picking the Fast pace shows a warning popup (app_toast, bottom-right of the app): it hits the trade
           site's rate limits quickly. "Back to Balanced" on it.
  2.17.0
       (1) Game search > Anoints: all 875 notables an amulet can be instilled with, each with its three Liquid
           Emotions and their poe.ninja prices plus the total (2x when one is needed twice). Searchable like the
           rest: by the notable, what it does, or an emotion's name (every anoint that uses it).
           Data: anointdata.json (tools/build_anointdata.py): emotion names from RePoE, recipes from the passive
           tree Path of Building extracts from the game files (RePoE has no recipe table). Prices: only poe.ninja's
           Currency and Liquid Emotions overviews (WealthPrices.ensure_types), hourly.
  2.16.0
       (1) Your own listings never count towards a price: trade.fetch_rich drops listings whose seller is the account
           typed in Price checks > Stash tab / Wealth (with or without its #1234), so your high-priced tab can't lift
           prices. Covers Price checks, Market Insights' seen listings and the Mod book's learning (all use fetch_rich).
       (2) Low confidence (and gear's rough guesses) show "Price manually" in Price checks instead of a number, and
           are left out of the total; the item's panel still has the rough figure and why.
       (3) Price checks > Prices in: Auto (div / chaos / ex as before) or always Divine / Exalted / Chaos / Vaal Orbs,
           converted with poe.ninja's rates (pricefmt.fmt_div, SETTINGS price_unit); every window that shows prices
           follows. A currency without a rate yet stays in divines.
       (4) A stash tab's price can be in any of 24 currencies (wealth.TAB_CURRENCY_NAMES): their trade-site ids come
           from the site's own /data/static list (trade_static.json, once a day); without it the 7 built-in ones stay.
  2.15.0
       (1) Ritual: a player's four Capture pictures (0/4, 1/4, 3/4, 4/4) showed 3/4 couldn't be read - the box also
           caught the icon's edge and the frame's ornament, gluing the glyphs together. Only the main band of text rows
           is used now (text_band). All six real pictures read right, and the real game 0, 1, 3 and 4 are in
           ritual_glyphs.json (only 2 still comes from fonts).
       (2) Ritual reminder only when you did some rituals but not all (0 done = you skipped Ritual on purpose).
       (3) Game search: "how the price checker sees it" links are gone; each result links to its wiki page instead.
  2.14.1
       (1) The Ritual watcher never reported anything in the released exe: a windowed exe's helper process has no
           stdin / stdout until it opens them from the OS handles (delirium_runner._reopen_std, which the Delirium
           helper always did). Without it the helper read "end of input" and quit at once. Tests ran it as plain
           Python, where stdin / stdout exist, so they didn't catch it.
       (2) The helper keeps a small log (data folder / ritual / ritual_log.txt): game size, where it looks, readings,
           and once a minute how well the icon matched when it found nothing.
       (3) ritual_glyphs.json now includes the real game "1" (from a player's 1/3 capture); the reader reads the
           user's real 0/3 and 1/3 cut-outs.
  2.14.0
       (1) Ritual watcher (soe2/ritual_alert.py): the game doesn't log Ritual progress, so - like the Delirium alert -
           it reads the counter next to the Ritual icon (bottom right of center) from the screen, in its own helper
           process (StashOfExile2.exe --ritual, utilities.RITUAL), twice a second, only that corner. The icon is found
           by template matching (templates/ritual_icon.png, cut from a real 2560x1440 screenshot, scaled to the game's
           height); the counter's black box beside it is cut into glyphs; "/" is the slanted middle one and each digit
           is the nearest of the reference shapes in ritual_glyphs.json (tools/build_ritual_glyphs.py: sans fonts plus
           the real game glyphs). Only "d/3" or "d/4" with d <= total counts, seen twice in a row. Checked at 1600x900
           to 4K.
       (2) Session tracker > Alerts: a Ritual row (on/off, sound, "Remind me when I leave the map", Capture, Test).
           Leaving a map (Client.txt area lines) with rituals not all done shows RITUALS NOT DONE / "1 of 3 done - go
           back through your portal" in the Delirium style. The timer's bar shows "Ritual 2/3". Capture saves a picture
           of that corner to the data folder (ritual/), which a problem report includes, for fixing a misread.
       (3) Client.txt is followed while Breach or Ritual is on (log_wanted).
       (4) Session tracker > Options: "Start tracking when StashOfExile2 starts" (tracker setting autostart).
  2.13.0
       (1) Breach banners look like the Delirium alert's END DELIRIUM again (user's choice): big flashing text straight
           over the game on a see-through background, no box, clicks pass through (WS_EX_TRANSPARENT / NOACTIVATE),
           centered on the game window 22% down (END DELIRIUM sits at 62%). The text shrinks to fit the game window.
           Being click-through, they go by themselves (8 s; "full" 10 s) or when the Genesis Tree opens.
       (2) Top value is now Market Insights (window, dock, Labs text); and its table
           is "Most expensive listings seen".
  2.12.0
       (1) listkit.py: every list (ttk.Treeview) has striped rows like a spreadsheet, in every theme (tags row_a /
           row_b, background C["panel"] / C["stripe"]; the old per-list "odd" / "even" tags are replaced). Rows are
           restriped once things are idle after any insert / delete / move / tag change, so sorting and deleting
           keep the pattern. Ctrl+C copies the selected rows tab-separated. Right-click: Copy, Copy every row,
           Select all, and Delete / Undo where that list has them (Price checks included).
       (2) Every box (Entry, Spinbox, Combobox, Text): Ctrl+A selects all, Ctrl+Z undoes (one-line boxes get their own
           history, Text uses Tk's), right-click Undo / Cut / Copy / Paste / Delete / Select all. A widget with its own
           right-click (Game search look-up, Wealth items) keeps it.
       (3) poe2db key, Ctrl+Shift+D by default (Settings > Hotkeys): opens poe2db's modifier list in the browser, only
           while the game or the app is in front. A link only; nothing is read from the site.
       (4) Toolkit menu: Quick start.
  2.11.0
       (1) Breach: after the game's Hiveblood warning, leaving a map (to your hideout or a town, read from Client.txt's
           area lines) shows a SPEND YOUR HIVEBLOOD reminder - every time you leave a map, until the Genesis Tree is
           opened. Checkbox "Remind me when I leave the map" on the Breach row (on by default). The waiting state is
           kept in SETTINGS breach_alert.pending, so it survives a restart.
       (2) The window / keyboard recorder (diag.py) is gone: it found the 2.10.2 fix and isn't needed any more.
  2.10.2
       (1) The real cause of windows vanishing on resize, found with diag_log.txt on a player's PC: every maximize,
           restore or snap made Tk rebuild each desktop window's Win32 window (new HWND each time), because they were
           transient() to the app's window - and the rebuilt one had no owner, so it fell behind the app. On Windows
           they're no longer transient (own_by_app sets the owner); and any rebuilt window is spotted (check_owner:
           HWND changed) and gets its owner, stacking and keyboard back - on <Map>, every resize and every 2 s.
       (2) Likely the typing bug too: Tk's keyboard focus pointed at the window that had been thrown away.
  2.10.1
       (1) Windows that vanished when the app was resized by dragging its edge or by Windows snap (not maximize):
           while Windows runs its own sizing loop the positions Tk reports can be stale. Once the app has been still
           for 0.4 s every window is placed again from scratch (Shell._settle), and every 2 s an open window that is
           hidden or off the app's desktop is put back (Shell.heal). Clicking anywhere also lets go of a Tk grab left behind by a closed
           drop-down (one shuts every other window out of clicks and keys).
       (2) diag.py: a window / keyboard recorder for these two bugs, off unless diag_on.txt is in the data folder;
           writes diag_log.txt (what Tk and Windows each think has the keyboard, grabs, each window's state on resize).
  2.10.0
       (1) Alerts while you play moved to the Session tracker's main page (alerts_page.py, replaces breach_page.py): one
           panel with Delirium and Breach on / off, sound, Test and a status dot each. The timer over the game has a
           small "Delirium on / Breach off" bar (tracker setting alerts_bar). The Delirium alert has no window of its
           own any more (modules/delirium.py gone) and never draws its splinter icon; splinter.png isn't shipped.
       (2) Breach: the game's second warning, ": <brequelwarning>{Cannot store any more Hiveblood! Go to the Genesis
           Tree to consume it.}", shows a stronger CANNOT STORE ANY MORE HIVEBLOOD! banner straight away (seen in a
           real log). Banners only while the game is in front (Settings), 45 s per kind, and it keeps looking for
           Client.txt every 15 s if it wasn't found. It starts with the app, not with the tracker window.
       (3) The Session tracker is out of Labs. Its start / stop and pause keys work with Labs off, get Ctrl+Alt+S and
           Ctrl+Alt+P if you had none, and show next to the Start button.
       (4) Typing that stopped going into a box: Tk could still think the box had the keyboard while Windows sent the
           keys elsewhere, so clicking the box didn't help (DeskWindow.take_keyboard now checks with Windows). Keys
           that land on a bare window right after you typed in a box go back to that box (Shell._stray_key). The
           app's single-letter keys (C, O) never swallow a letter typed in a box.
       (5) Windows stay inside the app when it gets smaller (they shrink / move), and an open window that went missing
           comes back when the app is clicked.
       (6) Regex: the endgame number boxes save 150 ms after you stop typing (and when you leave the box), not on every
           key. Waystone searches stick to the waystone's own tier; Revives Available is searched by default.
       (7) Settings > About: version, what's new, GitHub page, Discord, license and credits. A fresh install gets a short
           quick start guide instead of the welcome card (About brings it back). Versions show in full (2.10.0).
       (8) Linux groundwork (not a Linux build): linsys.py (Hyprland IPC, the game window, Steam libraries),
           tk class "StashOfExile2", updater never picks an .exe off Windows, linux/ window rules, build_linux.sh.
       (9) tools/check_version.py checks the version in every place (also run by the release workflow).
  2.9.0
       (1) Breach alert (breach_page.py), a checkbox in Session tracker > Options > Alerts while you play: follows
           Client.txt (the tracker's file) and shows a big HIVEBLOOD ALMOST FULL banner over the game, with a sound,
           when the game writes ": <brequelwarning>{Stored Hiveblood is almost at the maximum!}" (seen in a real PoE 2
           log; written twice in 2 s, so one banner per 45 s). Only that system line counts, not chat. Click to close;
           opening the Brequel tree closes it too (the game logs '"BrequelTree..." is missing from ...' then).
           gamelog.parse: new "breach" and "brequel_tree" events.
       (2) The Delirium alert's on / off is a checkbox there too (its window keeps the other settings).
       (3) Wealth sync: one listing that can't be read is left out with a warning, instead of losing the rest of its
           batch of 10 (the same guard Stash tab reading got in 2.8.1); and it no longer blames a "category" for it.
  2.8.2
       (1) Stash tab reading failed on every item of a real tab of Irradiated Tablets ("expected string or bytes-like
           object, got 'dict'"): some listings give text fields as objects. wealth._txt reads either form for every
           text field item_text and wealth_item use (Wealth syncs benefit too). In 2.8.0 the error also stopped each
           batch of 10 after its first item - why a 70-item tab showed "Read 7, added 0". If a listing still can't be
           read, tab_reader_log.txt now keeps the first one in full.
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
           panel; Delete + Undo. "Most expensive listings seen" stores and shows each listing's name, mod lines, own price
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
           of listings with the mod, ★ = High in your rules) and the most expensive listings seen (market.db, this league;
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
           Crimson, Graphite), accent color and text size, for every window. style.apply_look() at start-up: every
           color given to Tk (widgets, canvases, ttk styles, option database) passes through style.theme_color(),
           which moves the app's blues to the theme's hue and keeps meaningful colors (rarities, green / red, gold,
           the accent). The accent button is derived from the accent color. Restart now (App.restart_app) restarts
           the app to apply it (launcher: --restarted waits for the old window to close).
       (4) The note's colors / opacity / font are back in the Notes window; the pixel boxes for its place and size
           are gone (drag and resize the note itself; "Put it back in the corner" if it's lost).
       (5) Numbering: this is 2.0.0; see "How versions are numbered" above.
  2.0 beta 22
       (1) The item panel (mods with Min / Max, Search with these values, Mark listed ...) could vanish: its width was
           saved at close even when the Price checks window was closed or minimized (a real window since beta 13
           reports 1 pixel then), or after dragging the divider to the edge. Widths under 250 are no longer saved,
           a saved one is put back to 430, and letting go of the divider near the edge leaves the panel 300 wide.
       (2) Price checks: a # column (the record id = the order items were added), "↕ Order added" next to Show all,
           and ▲ / ▼ on the column the list is sorted by.
  2.0 beta 21
       (1) Settings in tabs (SegBook): General (league / pace, window, Labs, updates), Appearance (launcher, wallpaper,
           clock, the note's colors / opacity / font - moved here from the Notes window), Hotkeys, Advanced (Mod
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
           showed whenever the app was in front. Now Windows itself keeps a minimized app's windows, they are only
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
           brings it to the front. They follow the app's window when it moves, and hide with it (minimize / tray).
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
           Delirium alert). Tools have their own color.
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
       (1) Chat commands are pasted: the command goes on the clipboard and one quick burst
           of keys opens chat, clears it, pastes and sends. Nothing is typed letter by letter, so chat only flashes.
           Your clipboard is put back right after, and the app doesn't mistake either for a copy of yours.
       (2) Version numbers: every build gets its own number from now on (the earlier "beta 7" kits were several builds).
  2.0 beta 7  (the toolkit desktop)
       (1) The app is now a small desktop: every tool opens in its own window inside the app. Drag a window by its
           title bar, resize it from the corner, minimize it to the taskbar, maximize it (or double-click the title),
           close it. Resize from any edge or corner, like a normal window. Several can be open side by side; the one in front has the orange line under its title.
           Which windows are open, and where, is remembered.
             - Dock (left): the orb opens the Toolkit menu; a desktop-style icon with its name for every module
               (Price checks, Wealth, Mod book, Item library, Regex) and utility (Chat commands, Notes, Delirium, with
               a dot that is green while it is on); an orange edge = its window is open; the gear opens Settings.
             - Toolkit menu: search box (type a few letters + Enter), every module and utility, Settings,
               Check for updates, Quit.
             - Taskbar: a button per open window (click = bring it forward, click again = minimize), the league
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
       (5) Notes: the note itself only has its × now; every option is in the Notes window: key, colors, opacity,
           font size, and new: its place and size typed in, Lock it (no moving / resizing by accident), Reset place and
           size. The note resizes from any edge or corner. (Fixed: a note shown and saved straight away could be stored
           as 1x1 pixels.)
       (6) Updates (Settings): "Check for updates when the app starts" (tells you, asks first) and "Install updates
           automatically when the app starts" (no questions; it restarts itself). Both are off unless you turn them
           on, and they stay as you set them. Up to date or offline = only a quiet line in the status bar.
       (7) The dock's Toolkit button is the app's own icon; optional desktop icons look like the dock's tiles.
       (8) Wealth, redesigned (ideas from Wealthy Exile, not a copy): a Wealth card (total, change, Total / Daily
           chart over 24 hours / 7 days / 30 days / Lifetime), a Breakdown card (value per category, in divines or
           percent; click one to show only those items), your tabs down the side as colored buttons (click one to
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
           essences, omens, runes ... all said "not on poe.ninja". Now read by its item id, with the
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
             F6 shows / hides an always-on-top sticky note (drag, resize, colors, opacity, font size; it saves
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
       Stop stops it). Only new or changed items, or prices older than 3 days, are checked again, the most expensive first.
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
           negative "increased", "3 additional times" for "an additional time") are now recognized.
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
  1.43 Ritual Tablets: "Ritual Altars in Map allow rerolling Favors # additional times" now counts in the price.
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
       body armors, shields, foci, quivers, weapons, charms, flasks) now prices it, on the Price checks page like a
       tablet. The Item library's "Check an item" box has a Price check button that does the same.
       - Armor pieces are searched on their total Armor / Evasion / Energy Shield (at 20% quality, or their own
         quality if higher), weapons on their physical / elemental DPS; the mods that feed those totals are left out.
       - Rings, amulets, belts, quivers, charms and flasks are searched by their exact base type.
       - Two or more resistance / attribute / life mods are searched as one total (the trade site's pseudo stats).
       - Uniques are searched by name. Corrupted only against corrupted, uncorrupted against uncorrupted.
         Exceptional socket counts (2 on gloves / boots / helmets, 3 on body armors) are required.
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
       (1) Every PoE 2 base type (1,574) sorted by class and base group: body armors / helmets / gloves / boots /
           shields / foci by defense type (Energy Shield only, Armor / Evasion ...), rings / amulets / belts / jewels /
           charms one group per base (Breach Ring and Refined Breach Ring together; Runeforged / Runemastered versions
           with their base), weapons by class (bows, wands, quarterstaves ...), with each base's defense values.
       (2) Every modifier stat (2,518): its wording, whether higher is better, its trade-site stat ids, local or not.
       (3) Check an item: paste any copied item (Ctrl+C) and see how the app reads it: class, base, base group,
           quality, defenses, sockets, item level, corrupted, and every mod with its tier, roll range and trade stat.
           Lines it can't place are shown in red.
       The data comes from Exiled Exchange 2 (MIT license, see THIRD_PARTY_NOTICES.txt) and ships as gamedata.json,
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
       (5) Your own mod values: every mod in the side panel has Min and Max boxes, filled with what the
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
       (3) The side panel has "IF YOU LIST IT": the price in chaos / exalted / vaal and the two whole-divine neighbors
           ("8 div (-6%) or 9 div (+6%)") plus a divine + chaos split. "Listed at" now understands "8 div 50 chaos" and
           "150 vaal".
       (4) A listing priced in a currency with NO known rate used to be left out of the average without a word. It is still
           left out (guessing would be worse), but the row now says so, confidence drops, and currency_log.txt records
           the currency's name so it can be added.
       (5) Fixed: when one listing couldn't be converted, the next listings in market.db could get its neighbor's price.
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
       remembers all of them and searches "at least 1 of these". Needs a fresh download of
       the trade site's mod list on first start (automatic).
  1.19 Ready for the .exe: files packed INSIDE the exe (tabs.txt) are copied into the data folder on first start, so a
       brand-new user needs nothing else. Added build_exe.bat (one double-click builds StashOfExile2.exe).
  1.18 (1) Only YOUR Ctrl+Alt+C counts: the app now sees your real key presses (a Windows keyboard hook, which can tell
       keys you pressed from keys another program sent) and ignores item copies made by other tools' keys.
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
  1.14 Tabs (Items / Mod book / Mod rules) restyled: no more boxed gray outlines - flat dark tabs, the selected one is
       lifted with a gold top edge and gold text, hover brightens. The built-in icon now has a transparent background.
  1.13 Path of Exile look: warm near-black panels, gold accents and borders, serif title with the Mirror of Kalandra,
       gold buttons and tabs, in-game rarity colors (rare yellow, magic blue). Looks only - no behavior changed.
  1.12 (1) Wide spread = no price: when the listings behind a price are 20x or more apart, the row shows CHECK BY HAND
       (red) with the lowest and highest price, instead of a number. (2) Clipboard watcher rebuilt: it now reads the
       Windows clipboard directly (not through Tkinter, which can keep a stale copy after the app writes an item name
       to the clipboard), retries when another program is holding it, restarts itself if it ever stalls, and the status
       line says what it did with every copy (added / already in the list / not an item / normal copy).
  1.11 Wide-spread warning. When the listings behind a price are wildly different (cheapest and most expensive 20x apart or
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
  1.1  App renamed to PoE2 Tablet + Jewel Pricer (window title, header, this text). No behavior changes.
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
  Click a row: its name is copied (Ctrl+V it into the stash search). Under the mods
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

APP_VERSION = "2.134.1"  # bump this and __version__ in soe2/__init__.py together (see VERSION above)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if "--restarted" in sys.argv:                                 # 2.0.0: the app restarted itself (Appearance changes)
        sys.argv.remove("--restarted")
        import time
        time.sleep(1.2)                                           # let the old window save and close first
    if len(sys.argv) > 2 and sys.argv[1] == "--finish-update":  # 2.29.1: the new exe swaps itself in (no .bat)
        from soe2.updates import finish_update
        sys.exit(finish_update(sys.argv[2]))
    if len(sys.argv) > 1 and sys.argv[1] == "--ritual":         # 2.14.0: the Ritual watcher helper (started by the app)
        from soe2.ritual_alert import main as ritual
        sys.exit(ritual(sys.argv[2:]))
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
