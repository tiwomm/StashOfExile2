"""
StashOfExile2 - a Path of Exile 2 price checker for tablets and jewels, with a window instead of a text dump.
Free software under the GNU GPL v3.0 (see LICENSE). Written by an AI (Claude, by Anthropic) under a human's direction.

VERSION 2.83.0
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
  2.83.0
       Island Rumours (feedback: "use our Map library to build an add-on for the expedition helper"): in your hideout
       (Client.txt; feedback: "watch only in hideout") the app looks for the world map's Uncharted Waters card - the
       one large light parchment patch on a small copy of the screen - and reads only that part. Each rumour gets a
       tag beside the card: the island it leads to and your Map library rank for it ("Frigid Bluffs · A"; S / A in
       gold). rumours.py: the 20 rumours and their islands (the newest guides agree on the pairs); matched loosely
       (the card's handwriting reads as "clif fs"). Switch: Remnant's row, "Island rumours (in your hideout)".
       Remnant watcher (feedback: "it keeps popping up in random areas"): off in hideouts, towns and the campaign
       (Client.txt), always on in a Grand Expedition island (ExpeditionLogBook_...), in other maps as before.
  2.82.0
       Overlay ↳ Settings (feedback: the Options "shouldn't be nested beside the map stats ... reorganizing ...
       grouping of the toggle-able options"): the overlay's options are their own page under Overlay (in the
       sidebar, the title bar's Settings button and an "Overlay settings" button on the Overlay page), in cards:
       On the bar (the numbers; the switches and menus on it), Features (Notes, Calculator, League Focus, Focus
       line, map rank questions, Desecration Helper), Campaign (its switches and options), Behaviour (lock, tips,
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
       labelled "Any currency").
  2.79.1
       Mageblood and other uniques with a choice stat: searched like the trade site, with the option in the stat id
       (explicit.stat_264262054|8 = Legacy of Quicksilver), not a separate option value. The same stat more than once
       (2 Quicksilver, 2 Diamond) is one filter with Min = how many (feedback). A granted skill is also found without
       "Summon" (the trade site says "Grants Skill: Level # Rhoa Mount").
       The campaign / Focus line is docked to the top of the overlay bar by default, as wide, and moves with it
       (Overlay › Options › Campaign › "Dock it to the top of the overlay bar"; off = drag it anywhere). The Game bar
       spans the XP bar, bottom centre, just above it; a position you dragged is kept per resolution, so another
       resolution fits it again. The update badge looks for a new release every hour (was 6 h).
  2.79.0
       The item panel, cleaned up (feedback: "a clean view ... all of those functions"). One card holds
       every filter: Properties (base type - this base or any of its kind -, quality, defences / DPS totals, item
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
       right edge cut off). A unique's flavour text is never read as a mod, wherever it sits - The Brass Dome's
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
       is searched, it sets the price. Flavour text (the lore lines at the bottom) is never read as a mod, on any
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
       "How the app is organised" has the rule. test_v2640; tests renamed to Farm Tracker.
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
       previous page back; finish opens the last page (cfg "page"); minimise = minimize the app (Esc). soe2/sidebar.py
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
       (#e6d6b2). US spelling in every user-facing text (colour -> color, grey -> gray ...); Notes' card "Font and
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
       (overlaywin.texture: grain, fibres, stains, burnt edges - Pillow, no image file), drawn titles and buttons on
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
       D1, deployed by .github/workflows/board.yml with repo secrets - board/README.md has the setup). No login
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
       (2) The window really opens maximised again: the first "normal" size while the window appeared was saved
           and wiped the "maximised" flag before it was used (since 2.23.1). Nothing is recorded until the start-up
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
       (1) Maximised last time -> maximised again: restore_zoom waits until the window is on screen and the start-up
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
       (1) The app opens where you left it: place, size and maximised (SETTINGS main_window, kept as the window
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
           armour, shields, foci, quivers, weapons). tools/build_regexdata.py: MULTI kinds from several RePoE
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
           never S) before "any roll" / "best mod alone". The price is labelled a floor.
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
       (2) Top value is now Market Insights (window, dock, Labs text); its "Dearest listings seen" table is "Most
           expensive listings seen".
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
           saved at close even when the Price checks window was closed or minimised (a real window since beta 13
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

APP_VERSION = "2.83.0"  # bump this and __version__ in soe2/__init__.py together (see VERSION above)

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
