# StashOfExile2 roadmap

> **GGG ToS safety check - read first.** One key press = one action, only when you press it · nothing acts in the game by itself (watchers only look and show) · never touch the game's memory, code or traffic · the mouse is never moved or clicked for you · it reads only your clipboard, Client.txt, screen pixels, the trade site (within its limits) and poe.ninja. Every change must pass all of [TOS.md](TOS.md) (`tools/check_tos.py` checks the code on every PR).

> **Who we build for - read second.** Path of Exile players are utilitarian: they love data and information, problem solving and creative thinking. So every feature shows its numbers *and how they were worked out*, lets you sort, filter, compare and export them (CSV), keeps power-user depth (keys, versions, raw data) one click away instead of hiding it, explains in plain words, and leaves the decision to the player. Pretty is welcome; vague is not.

**Current version: 2.90.0**

Versions follow Semantic Versioning 2.0.0, always written in full: 2.10.0 adds features, 2.10.1 only fixes. Each step below is one release; we work through them top to bottom.

## ✅ Done

| Version | What it brought |
|---|---|
| 2.0 | The app as a desktop with windows, dock and taskbar. Price checks for tablets, jewels and waystones. Mod book, Regex, chat keys, sticky note, Delirium alert. Themes and a start-up screen. Updates that never go backwards. |
| 2.1 | Map stats with per-map leaderboards (Session tracker). Top value (Labs). Clock follows Windows' 12 / 24-hour setting. |
| 2.2 | Regex key: one key in game copies your stash search. Currency Exchange helper (whole-number ratios to post). CSV export for map runs, sessions and Wealth. |
| 2.3 | Windows check-up done. Wealth, step by step: a guided first setup, "up X since yesterday", snapshots you can compare, your own prices marked. Rough prices for jewels and tablets instead of "check by hand"; no freeze when deleting many price checks; a problem report. |
| 2.4 | Lists work the same everywhere (multi-select, Delete, Ctrl+Z / Undo). Wealth Clear and Undo. Regex Favorites tab. Exchange rates tabs with Exchange Helper and Arbitrage (GGG's hourly exchange history). Top value keeps your priced items after clearing and shows listing details. Profit / hour explained. |
| 2.5 | Search filters in the item panel (seller, priced in, corrupted, gear item level / quality / sockets / base). Wiki link. |
| 2.6 | Waystone and relic mod rules in the Mod book (their own ratings, apart from tablet / jewel ones); Regex and Top value use them. |
| 2.7 | Session tracker: only your own deaths count (checked against a real log), AFK off resumes, maps-per-day chart. |
| 2.8 | Price checks can read a whole public stash tab (Add items from: Manual Add or Stash tab). |
| 2.9 | Alerts while you play (Session tracker): Breach Hiveblood banner, Delirium on / off. Wealth sync skips unreadable listings. |
| 2.10.0 | Alerts panel on the Session tracker's main page (Delirium + Breach, "full" Hiveblood banner); tracker out of Labs with default keys; typing lock-up and window sizing fixes; Settings > About with Discord; quick start guide; Linux groundwork. |
| 2.10.1 – 2.10.2 | Windows no longer vanish on resize / maximise / snap; typing in boxes fixed. |
| 2.11.0 | Breach: reminder to spend Hiveblood when you leave a map. |
| 2.12.0 | Striped rows, Ctrl+C and right-click menus on every list and box; poe2db key (Ctrl+Shift+D). |
| 2.13.0 | Breach banners in the Delirium alert's style; Top value renamed Market Insights. |
| 2.14.0 | Ritual watcher (reads the 0/3 counter, reminds you when you leave a map with rituals left); tracker can start with the app. |
| 2.14.1 – 2.15.0 | Ritual watcher fixed in the exe and reads every counter; Game search links to the wiki. |
| 2.16.0 | Own listings never count; "Price manually" for low confidence; prices in any currency; 24 currencies for tab prices. |
| 2.17.0 | Game search > Anoints: each notable's three Liquid Emotions with poe.ninja prices and the total; search by notable, effect or emotion. |
| 2.18.0 | Mod book learns again (trade site's new mod format); Market Insights item preview, own / marker listings left out; Wealth shares the Price checks tab. |
| 2.19.0 | Copy marker: a ring for 10 seconds where you pressed Ctrl+Alt+C; a ★ per valuable mod in Price checks. |
| 2.20.0 | Mod book tiers S-D (lowest left out first when nothing matches); Import rules really imports; the author's current rules ship as defaults. |
| 2.21.0 | Price checks: Mark as sold (the Mod book learns from real sales); Regex ranges and maximums; Favorites Copy button. |
| 2.22.0 | Regex for jewels and gear. |
| 2.23.0 | Note tabs; Game search "more ›" details; Arbitrage Live scan. |
| 2.23.1 | The app opens where you left it. |
| 2.24.0 | Copy marker is a small + (seconds setting, or keep until Esc is held 3 s); Price checks "★ Valuable" column. |
| 2.25.0 | Copy marks clear with a double tap of Esc; pick the +'s colour. |
| 2.25.1 | Faster with long lists: price updates about 15x quicker, no more freezes while saving. |
| 2.25.2 | Popups open on the monitor you're using. |
| 2.25.3 | Waystone previews show real numbers; app popups open in the middle of the app. |
| 2.25.4 | Maximised stays maximised; Slowness recorder (Settings > Advanced). |
| 2.26.0 | Timer's Helpers bar (click to switch, ⚙ to options); pricing time-left chip; Arbitrage works again (BETA); Lag finder. |
| 2.26.1 | Fix: restarting after a theme change no longer breaks the Delirium / Ritual helpers. |
| 2.26.2 | Regex type switching without freezes; maximised really stays maximised; time left from the start. |
| 2.26.3 | Updates no longer hang with a flashing console window. |
| 2.26.4 | Regex Jewels / Gear fast (list widget); star legend up top; "Clear filters" button. |
| 2.27.0 | Chat commands is a tab in Settings (no longer a Utilities window). |
| 2.28.0 | Money Makers: community strats in one layout (Thoughts per Click, Clicks per hour), live updates from GitHub, own strats + Share, simple run tracker. |
| 2.29.0 | Money Makers reworked: Category › Type browser + tag groups, effort in words, tablet / waystone / atlas / craft sections, waystone tiers, Download Format (.txt), Lucrative Strats, Tablet Crafting quick reference. |
| 2.29.1 | Fix: updating opens no console windows (the new exe installs itself). |
| 2.30.0 | Money Makers Community board: no login (pick a name), post / upvote / report, admins promote to Official (Cloudflare Worker). |
| 2.31.0 | Community Mod book: pooled mod prices (anonymous, hourly) and community ratings; Stash tab marked BETA; Ritual Capture, Lag finder and the toolbar "Ctrl+Alt+C only" box removed. |
| 2.32.0 | Map library: every endgame area (maps, citadels, pinnacles, league areas), ranks S-D / Avoid, export / import, community ranks; the tracker counts pinnacles and learns new areas. |
| 2.33.0 | Child tools: one layout rule for the whole app (below). Map library under Session tracker; Mod book, Under the hood, Market Insights under Price checks. |
| 2.33.1 | Map library: ✖ Avoid button no longer cut off. |
| 2.34.0 | Polish 1: design tokens (4 text sizes, one spacing scale, colour roles), button types (primary / secondary / quiet / danger), readable text in every theme and accent (WCAG AA, checked on every PR). |
| 2.35.0 | Polish 2: one toast system (info / success / warning / error with icons, stacked in the app, pause on hover, timed by length, never steal focus); last 20 in Settings > Advanced. |
| 2.36.0 | Polish 3: right-click menus with each list's own actions (Price checks, Market Insights, Regex Favorites); the Menu key / Shift+F10 opens them from the keyboard. |
| 2.37.0 | Expedition Remnant Price Checker: a remnant's reward book gets a poe.ninja price on each reward (best ★), by itself (Auto watcher, scaled to your resolution) or with a key; a helper in Session tracker › Alerts and the timer's Helpers bar. Idea credited to PoE Ancients Price Helper by Pedro Quitério (no code used). |
| 2.38.0 | GGG ToS safety check (TOS.md, at the top of every guide, `tools/check_tos.py` on every PR and release); Remnant tags fixed (no black screen); the Helpers bar is its own window; Money Makers and Stash tab tagged BETA. |
| 2.39.0 | In-game clock: time and date on the Session timer (12 / 24-hour setting), switch in Settings > Appearance > Clock. |
| 2.39.1 | Remnant checker: rewards poe.ninja doesn't list show "no price"; a similar name can't lend its price. |
| 2.40.0 | Runeshape tips next to the remnant prices (every runeshape, S to D); Stash tab reads whole tabs (not 20); Ritual leave-map reminder fixed; banners see-through in every theme; Stash tab currency kept. |
| 2.40.1 | Stash tab and Wealth read every item of big tabs (hundreds of the same kind). |
| 2.41.0 | Waystone prices: few listings -> the cheapest real offer; Listings: Any is called out. |
| 2.42.0 | Price checks: Manual Add and Stash tab lists apart; one list per stash tab, to switch between. |
| 2.43.0 | Over-the-game windows in the remnant book's parchment look (Classic dark optional), opacity each in Settings; Helpers -> Mechanic Helper; remnant tags stay while the book is open; runeshape tips from the first show, switch in Settings. |
| 2.44.0 | Overlays (was Session tracker): Session timer, Mechanic Helper, Notes and Look as tabs of one window; Settings links to Look. |
| 2.45.0 | Farm Ledger (was Run tracker): setups with versions, items priced by themselves, loot copied and priced by poe.ninja item by item every N runs, a spreadsheet, figures, compare, CSV. |
| 2.46.0 | Strat guides as CSV (the Farm Ledger's column names); a setup exports as a guide; Cost now: a strat's items checked on the trade site once a day. |
| 2.47.0 | Overlays › Look: Runeshape parchment (grungy, the mockup's layout), Relic tooltip, Carved frame, Quiet HUD, Classic. ＋ Tab is a button. |
| 2.48.0 | Taskbar: ⬆ Update badge (any window) and 🐞 Report a bug (GitHub issue through the board server, Discord told). |
| 2.49.0 | Settings (cog) at the top of the dock, Toolkit at the left of the taskbar; on / off options are switches. |
| 2.50.0 | Overlays › Appearance (was Look) explains opacity with a %; runeshape tips only on Mechanic Helper; the Mechanic Helper bar stands on its own. |
| 2.51.0 | Mod book › Manual feed: teach it an item's price (counts as 1-10 listings, optional High rating, before / after, undo, CSV). A more readable Session timer. |
| 2.52.0 | Menus tidied: each setting in one place (opacity in Overlays › Appearance; the timer's clock switch in its Options). |
| 2.53.0 | Price checks: click a row for the item's box (as in Insights). A softer Session timer. US spelling everywhere (Font and Colors). |
| 2.54.0 | Money Makers filters: Thoughts per click, Clicks per hour. Profit leaves the Session timer: money is tracked in one place, the Farm Ledger. |
| 2.54.1 | Manual feed: the price is optional (no price = the ticked mods are rated High); no "Counts as N listings" - one item is one price. |
| 2.55.0 | One overlay window: Session timer, Mechanic Helper and Notes together (Merged switch splits them). New styles Codex and Minimal; Layout Panel or Strip for any style. |
| 2.55.1 | The item box (Price checks, Insights) closes with Esc, Space or a click anywhere else. |
| 2.56.0 | Farm Ledger redone (part 1): setups as cards, the verdict in words, figures, where the money comes from, a counting strip, a first-time page, Compare says who wins. |
| 2.56.1 | Strip: drag it wider or narrower (never under what it shows); always back on the screen, locked or not. One opacity slider. "Classic dark". |
| 2.56.2 | Remnant price tags: smaller, plain weight, in the overlay style's colors and texture; show up faster, go when the book closes. |
| 2.57.0 | Settings cleanup 1 - every key is set in Settings › Hotkeys only (grouped; chat command and Farm Ledger keys editable); other pages show their key with a link. |
| 2.58.0 | Settings cleanup 2 - one Appearance tab: the overlays' look moved into Settings › Appearance (with Notes text size); Notes and the copy marker follow the style. |
| 2.59.0 | Settings cleanup 3+4 - always one overlay window (Layout under Style, no × on the strip); "Session timer" is now Overlay, one screen; F6 shows / hides the overlay (no notes key); Settings › Price checking and Tools; Client.txt and window title in General › Game; one league place; one overlay lock; no Save & apply; Fine tuning in Advanced; a search box in Settings. |
| 2.60.0 | **Theme packs:** ten themes for the whole app (Emberforge default, Midnight Steel = the old look), swapped live in Settings › Appearance; bevelled buttons, list headings and title bars per theme; meters for the trade limits and mod rolls; an item card with Item / How it's priced / Raw in Price checks; a new icon. Themes are JSON (themes/); your own go in the data folder's themes folder. |
| 2.61.0 | The app window's own title bar in the theme's colors (Windows 11; dark / light on Windows 10). A fresh install starts by picking a theme. |
| 2.61.1 | Chat command keys are set on the Chat commands page again, with a warning when a key is taken; a command without a key is kept. |
| 2.62.0 | **Pages (redesign step 1):** a text sidebar (groups, ↳ sub-tools, Toolkit + Settings at the bottom); one tool fills the window at a time; a status bar instead of the taskbar; Frost Pane readability. |
| 2.63.0 | **Price checks (redesign step 2):** header strips over the list and the item, the list in a sunken frame, Search and Only ★ filters, the picked rows' buttons under the list, the item panel's own buttons; no more pop-up box on a click. |
| 2.64.0 | Tabs in the sidebar: each page's tabs are listed under it with ↳ (Money Makers, Regex, Exchange rates, Mod book); Farm Ledger is now Farm Tracker. |
| 2.65.0 | **Game bar overlay layouts:** on the XP bar, or split beside the life and mana orbs, in the game's own bar look, fitted to the game window (Fit to the game after a drag). The sidebar unfolds only the open tool; Regex lists just Favorites. |
| 2.66.0 | The overlay in two game-styled looks: the Panel (like the game's vendor windows) and the Game bar - no Style list, no Strip / Minimal. Game bar in PoE2's own HUD style (pewter frame, arched gem end caps, flask-slot sockets); Game search ↳ Anoints; slimmer halves beside the orbs; no Fit button. A click on a tool's row goes back to its own page from a tab or sub-tool. |
| 2.66.1 | The Panel redrawn to match the game's Treasurer window (small-caps title band, red league band, gold numbers in charcoal boxes). |
| 2.66.2 | The Panel redone: heavy dark-metal frame with filigree corners, framed header banner, stats in a 2 x 2 grid with icons and big gold numbers. |
| 2.67.0 | Overlay: the Panel and the XP-bar Game bar only (switches in both); Notes in the overlay's look. Farm Tracker: one mods-matter question at a time, centered; no valuable-mods pop-up; Trade search + Copy regex per item. |
| 2.67.1 | Money Makers › Tablet Crafting renamed Tablet Craft Helper. |
| 2.67.2 | The XP bar overlay in two rows: the switches on top, the numbers under them. |
| 2.68.0 | Farm Tracker is now Strat Tracker; waystones pick their endgame numbers (and search by them); the setup window stays in front after Done / Skip. |
| 2.68.1 | Notes is part of the overlay: its settings section and every trace of a notes key are gone. |
| 2.69.0 | Redesign step 3: every tool's parts under the theme's header strips in sunken frames, like Price checks (Settings, Wealth, Regex, Exchange rates, Game search, Insights, Under the hood, Money Makers, Map library, Mod book, Overlay, Calculator). |
| 2.69.1 | Community data sharing is opt-in (asks once; covers mod prices, map ranks and strat uploads); Strat Tracker 📤 Upload to the community strats; Toolkit footer no longer cut off. |
| 2.69.2 | Overlay: a paused session shows a small PAUSED tag by the time instead of "(paused)" running into the next number. |
| 2.69.3 | Session: the game closing or crashing pauses the session and asks End session / Keep it going (the game coming back resumes it). Roadmap: Maybe later. |
| 2.70.0 | Strat Tracker part 2: the setup in 5 short steps with the cost of one run always in sight; the log-loot box in 3 steps (Runs, Loot, Profit). |
| 2.70.1 | Overlay: a Timer over the game switch (timer only) instead of Hide timer; On the overlay - a switch for each part (numbers, where you are, clock, Notes, Mechanic Helper switches). |
| 2.71.0 | Strats browser redone: filter buttons, strats as cards (List stays), Your numbers and Track in Strat Tracker in the strat's panel. |
| 2.72.0 | Gear priced properly: filler / low-tier mods left out of the search, a real price when the listings back it up; uniques by roll; crafting bases by item level. |
| 2.72.1 | Stackables poe.ninja doesn't list are priced from the trade site's bulk exchange (Wealth; a copied stack in Price checks). |
| 2.72.2 | Notes: a right-click menu on each tab (Rename on the tab, New, Duplicate, Move, Copy, Clear, Reopen a closed note, Close). |
| 2.73.0 | League Focus part 1: Overlay ↳ Game Plan (goals by phase, stockpile, farm plan, build lock, poke settings), the focus line on the overlay, a Focus switch on the bar; every feature's On and "on the bar" switches. |
| 2.73.1 | League Focus part 2: pokes over the game - nudge, reaching maps, cheap stockpile prices, the build lock's new-character guard, the check-in - with limits, quiet hours, tone, history. |
| 2.73.2 | Price checks fixes: stash-tab items only in their own list, Pause / Price next / Price last for waiting items, an iLvl column; Market Insights item panel at the side and Remove (with Undo) in all three lists; the tagline "One tool to rule them all." |
| 2.73.3 | Map supply pokes (League Focus): Game Plan › Map supplies - refill every N maps or N minutes in maps (from the game's log, not Wealth), a poke between maps with Refilled / Snooze / Skip, its own switch. |
| 2.73.4 | League Focus polish: prices only for your league; stockpile from the Currency Exchange's list or any name (Quantity); farms of your own; goal targets by kind (div, level and maps from the log, act, a number); the overlay bar spaced out, with hover tips and a first-time card per switch (Feature tips); Game Plan's visual hierarchy. |
| 2.73.5 | The overlay bar: room above and below the switches (a taller bar; side to side as before), dividers in the numbers row, hover tips that stay on screen, the focus line hidden with Focus; price pop-ups only for items you check yourself (not a stash tab's); iLvl for older rows. |
| 2.74.0 | Advanced tools hidden by default: Price checks ↳ Under the hood ↳ Mod book, shown with Settings › Advanced › Show advanced tools (both keep working - learning, community data sharing). The calculator over the game: a fixed-size window from Calc ▾ on the overlay's bar, held by the overlay's lock, its own switch (out of Tools). The overlay bar halfway between 2.73.4's and 2.73.5's height; the Remnant tip names the runeshape list; Settings › Appearance › Overlay settings (Layout, Opacity, Click-through - on by default, while locked); the Game bar is the default layout, named "Game bar".
| 2.74.1 | Price checks' Item card shows the mods and their values as in game; uniques' mods read (Unique Modifier headers), named rolls (Legacy of Gold) and trade-site options searched, flavour text never a mod. |
| 2.74.2 | Settings › Advanced › Report a bug (the bottom bar's form, not a .zip); a new version shows in the sidebar above Toolkit and Settings. |
| 2.74.3 | Session timer: ⏸ / ▶ on the overlay and the keyboard's Pause key (no Ctrl+Alt start / stop / pause keys); click-through its own switch, off by default. |
| 2.74.4 | Price checks: check boxes for each mod on the item card, Min / Max under Fine-tune; uniques' flavour text never a mod. |
| 2.74.5 | Price checks, a lighter page (fewer rows, less padding, no legend chip or Only ★); closable beta notices. |
| 2.75.0 | Wealth UX pass: Wealth ↳ Overview / Stash tabs / Snapshots in the sidebar; Sync and Count currency on every page; setup steps as cards on the Overview, then one status line; a From list over the items. |
| 2.76.0 | The overlay: the map's rank its own part (click to rank) and a card asking to rank maps you haven't; League Focus's line on its own small goal bar (Game bar / Panel style), where the Campaign Helper goes next. |
| 2.77.0 | **Campaign Helper**: the campaign line on the goal bar, the act route (I'm here, ◀ ▶ and keys, start from here), rewards (missed / did you get it? in town; hand ticks win; "proof" zones tick themselves), Vendor ▾ in town, unknown zones learned (note, optional, newer guide) and pooled through Community data sharing, act splits with a best per league, its settings and switches. The guide pack (campaign.json) updates from GitHub; a weekly Action adds zones players found. |
| 2.78.0 | **Money Makers rework:** content tags (pinnacles, bosses, map content - one tag system, shipped in strats/content.json) ticked in the Strat Tracker's Atlas & content step and filtered by in a Content row; an atlas screenshot with the strat (pasted or a file, kept small, uploaded to the board, shown in the Strat panel - no planner links); a Publish step that asks what it is, Thinking, Clicks, tags and steps before anything goes out; the Strat panel's What you need - each tablet and waystone with Copy regex and Trade. |
| 2.78.1 | The rank card says the map's name, not its area id, and saves the rank under it (ranks saved under an id move over). |
| 2.78.2 | The campaign line's bar is as wide as the overlay's bar. |
| 2.78.3 | The overlay scales to any resolution (720p to 4K, cards too); the item card has Item level and Min / Max beside each mod. |
| 2.79.0 | A clean item panel (every filter on the card, ▸ Advanced for the rest), no pop-ups, unique / granted-skill mods from the trade site's list, the white / magic base rule, Remnant tags on time. |
| 2.79.1 | Mageblood: stat options in the id, the same Legacy twice = Min 2; granted skills found without "Summon"; campaign line docked on the bar; the bar as wide as the XP bar, refit per resolution; update look hourly. |
| 2.79.2 | Every mod under Stat filters can be ticked (left-out ones too); searches start at Instant Buyout, priced in Exalted Orb Equivalent. |
| 2.80.0 | **Price Checks**: Ctrl+C on an item in game shows its card with every filter and the trade site's listings beside it (name band, properties, item level, requirements, mods with tiers, price, seller, when, picture; Recent 20). The old page is **Bulk Pricing** (Ctrl+Alt+C, stash tabs), a child of Price Checks with Market Insights and Under the hood. |
| 2.81.0 | **Desecration Helper**: at The Well of Souls (from Client.txt, with a notice) each revealed option shows its tier for the item type, Abyss lords' mods their range; the item type from the options and the item's picture. |
| 2.81.1 | Desecration Helper tags show just the tier (T5); its switch only in Overlay › Options (not on the bar). |
| 2.81.2 | Desecration Helper reads hybrids shown in either line order (Accuracy + Light Radius). |
| 2.82.0 | Overlay ↳ Settings: the overlay's options on their own page, in cards (On the bar, Features, Campaign, Behaviour, Mechanic Helper). |
| 2.83.0 | **Island Rumours**: in your hideout, each rumour on the Uncharted Waters card gets its island and your Map library rank. Remnant watcher off in hideouts / towns / campaign, in maps only with the Expedition mark on screen, always on in Grand Expedition islands. |
| 2.83.1 | Price Checks' key is Ctrl+D (Settings › Hotkeys); the game's plain Ctrl+C is left alone. |
| 2.84.0 | **Price Checks ↳ Favorites**: items from Price Checks (☆ Add to favorites) and pasted trade links, in groups and your order; each opens with its filters and the trade site's listings. Right-click for rename / edit / duplicate / move / copy link / delete (Ctrl+Z). Money Makers item links: Instant Buyout, waystone numbers and tier; regex with numbers. |
| 2.85.0 | **Community board protections**: only authors edit, every change kept (History, roll back), **Suggest an edit** (the author accepts), opt-in reviewers (2 approve changes to Official strats and decide reports), unique community names asked once at start-up (change once every 7 days), field checks and daily limits. Money Makers / Strat Tracker accuracy fixes (units, negatives, sources, labels, tracking Community strats). |
| 2.85.1 | Money Makers filter labels show in full. Roadmap: the Community FAQ becomes a Community forum. |
| 2.85.2 | Ritual / Delirium watchers see the game under the overlay bar (the bar is left out of screen captures; switch in Overlay ↳ Settings). The docked Focus / campaign line sits flush with matching ends. |
| 2.86.0 | **Global leaderboards**: Overlay ↳ Leaderboards - Campaign (acts + whole), Maps, Bosses & pinnacles, Trials; Mine / Everyone, league, class; opt-in sharing (community name only); self-reported times checked by the board, reports, reviewers, admins. |
| 2.86.1 | Community names: slurs and hate words refused (with look-alike spellings); old ones reset and asked again. |
| 2.87.0 | **Stash order**: a stash tab's items follow the tab (down columns or across rows; the trade site keeps no order, but says where each item sits). Price Checks go first, Search again replaces the older search, and they search exactly what's ticked; Recent is kept over a restart. Leaderboards: Simulacrum of Delusion under Bosses & pinnacles. |
| 2.88.0 | **Listing order lab** (admins, Under the hood): read a tab's trade link, walk the tab with Ctrl+Alt+C, compare the site's order with yours (rounds kept, CSV) - to work out the listing order. |
| 2.88.1 | Fixed: Bulk Pricing stalled when you had Favorites (Price Checks-first waited for a job that wasn't there). |
| 2.88.2 | Ctrl+Alt+C heard reliably (a dropped key watcher is noticed and renewed); Price Checks wait for Search after a tick; every long trade link reads. |
| 2.88.3 | Campaign switch always on the bar; overlay shows only over the game's own window; hidden from captures only while a watcher runs. |
| 2.89.0 | A new campaign asks Speedrun or Full rewards and follows that guide (a real speedrun route: bosses and side areas that only give gems or loot skipped, the rewards worth the time kept); Settings can't stay stuck in front after resizing the app. |
| 2.89.1 | Screenshots show the overlay (capture hiding off by default); a ⚙ by the overlay's lock opens its settings; "Campaign" on the bar; Campaign options no longer overlap. |
| 2.89.2 | Privacy: the sharing question says what, why and where; no user name in logs or bug reports; Act splits is the Act timer. |
| 2.89.3 | Privacy hardening: delete all your board data, day-only leaderboard times, private leagues never shared, rates not totals, screenshots checked, names kept out of logs and reports. |
| 2.90.0 | The overlay bar: one switch per helper (asked once which you want), Map + area + rank as one centered part shown whole, Maps: / Avg. centered; Settings › Helpers holds every helper; the Well asks once (Desecration Helper is Beta); no campaign line after the campaign. |

## ▶ Next up

Re-styling the app (e.g. the YouTube Music-style shell) is set aside for later (2.57.0).

Order (decided 2.34.0): the Polish basics first, so new features are built on them; then the features; then the polish that touches every window; Linux last.

| Version | Plan |
|---|---|
| 2.91.0 | **Exchange rates on the overlay + Arbitrage:** a small movable window over the game (off until you turn it on) listing today's most-used rates (chaos:div, exalt:div ...), in the overlay's look (both looks); Arbitrage › Check a flip you see in game picks Buy / Sell from a list of every item Exchange rates tracks. |
| 2.92.0 | **Help rate mods + Bulk Pricing floor** (mockups OK'd 2026-11-04): a subtle opt-in to rate mods (S/A/B/C/D/Ignore, one at a time, per rule set incl. gear base types) that feeds the board; Bulk Pricing skips items the Mod book is sure are under a floor (1 div by default, per rule set) and flags unsure-cheap ones "check by hand". "Not now" asks again once, at random, 3-7 days later; "No thanks" never asks again. |
| Before 1.0 (Dec 11) | **Campaign guide pack refresh** for 0.5.5 and then 1.0: Dreadnought Vanguard is gone (Jamanra in The Dreadnought), Azarian moved to the Heart of Keth, the Waterways levers are pressure pads, the Primal Arena's +2 points moved to Omniphobia, the Whakapanu shark's permanent choice and Plunder's Point are missing, and about 10 Interlude zones are missing. 1.0 may bring Acts 5-6. |
| Later | **Mageblood search helper:** build the trade search for the flasks / charms you want on a Mageblood. Starting point, the user's search: [Mageblood search](https://www.pathofexile.com/trade2/search/poe2/Forbidden%20Rites/H4sIAAAAAAAACp3TwUrEMBAG4FeR_xykyWbbTY7e97gnKZJ1owykabGzYql5d4mLKLggzjWTL_MzSVbMHPg8w68YJ6YxwyPkBUUhhyHCYx-e4zGN4wkKvEx16cCUiJebu5gY6vOIGf5-_aqHXDc_UeL4cinQCR7xbUr0SHxbwYNprWlNs7XvOyi8hnSONcVAGd6Uov5AWwmyEqS1RG0kqBPlE7VqRa2MRImQaOi6kSgnanX1LfXV_ecXbHadtU53ze_7sM13Chp-Im11a5xx7upk-9KXD_rzLDzYAwAA). How it's used: uncheck every mod but the ones you want and set each one's min to how many you want. 2x Quicksilver + 2x Gold: uncheck all but Gold and Quicksilver, min 2 on each. 1 Basalt + 1 Quicksilver + 2 Gold: uncheck all but Basalt, Quicksilver and Gold; min Basalt 1, Quicksilver 1, Gold 2. Builds on 2.79.1 (two of the same Legacy = Min 2). The rest gets worked out when we get there. |
| 2.93.0 | **Polish 4 - Responsive:** windows reflow when narrow (toolbars wrap, side panels drop under the list, sensible minimum sizes), sharp on every monitor (per-monitor DPI), a text size setting (100-150 %). |
| 2.94.0 | **Polish 5 - Hover, focus, micro-interactions:** the same hover and pressed look on every button, row, icon and tab; a visible keyboard focus ring everywhere; short (120-180 ms) fades for popups and toasts, never on lists; a "Reduce motion" setting that turns them off. Everything over the game matches the overlay's own theme (both looks): tooltips, pop-ups, cards, notices, toasts. |
| 2.95.0 | **Polish 6 - Visual hierarchy:** the suggestions below, window by window, with before / after screenshots in each PR. |
| Last | **Linux build** (Hyprland / Wayland first) - the groundwork is in place (session_linux_handover.txt). |
| Very end | **Kind words** (a hidden, opt-in easter egg): short affirmations in a quick centered box over the game, like PoE's loading-screen tips (e.g. on zone loads, at most every N minutes, fading after a few seconds). Found only by digging through the menus. I keep the rotation myself with little upkeep and no spoilers (the raw lines shouldn't be easy to read); how I add lines is still to decide - a scrambled file in the repo plus an Actions form, the board server, or lines built into each release. A starter template of lines. Extra polish. |

### Visual hierarchy - suggestions (for 2.47.0)

- **One primary action per window**, in the accent color (Price checks: Re-price all, Regex: Copy, Wealth: Refresh). Everything else is secondary or quiet.
- **Big number, small label:** totals and prices large; their labels small and muted. The same chip style for every status (Priced, Require Review, time left).
- **Group toolbars** into labeled clusters; move rarely used actions into a "⋯ More" menu so the main row stays short.
- **Gold means value only** (prices, ★ valuable mods). Headings and highlights use the accent or white instead.
- **Numbers line up:** right-aligned, same-width digits in price and count columns.
- **Empty states** say what to do next, with the button to do it ("Nothing in the list yet - hover an item and press Ctrl+Alt+C").
- **Section cards** everywhere: the same title style, padding and spacing, so settings and tools read the same way.
- **Sidebar:** a clear bar on the active module; BETA badges smaller and quieter.

### Accessibility - WCAG 2.1 AA (applies to every Polish release)

- **Contrast:** text at least 4.5:1 (3:1 for large text); borders, icons and focus rings at least 3:1 - checked for every theme by a test.
- **Not colour alone:** selected / avoided / valuable / error states also change shape, icon or weight (✔, ✕, ★, bold).
- **Keyboard:** every action reachable without a mouse, in a sensible Tab order, with a visible focus ring; no keyboard traps.
- **Timing:** toasts can be paused and found again later; nothing important disappears before you can read it.
- **Motion:** nothing flashes more than 3 times a second; Reduce motion turns animations off.
- **Resize:** text up to 150 % without cut-off text or overlapping controls.
- **Names:** every icon-only button gets a text label or tooltip. (Tk gives screen readers little to work with on Windows, so full screen-reader support is not promised.)

## 🤔 Maybe later (ideas to weigh when the plan above is done)

- **Trials & Simulacrum tracker** (Overlay ↳ Trials): counts Trial of Sekhemas, Trial of Chaos and Simulacrum runs from the game's log (entering the area; finishing, if the log says so), with a "Got it!" for each mechanic's chase item (your own list; defaults such as Simulacrum → Voices, Trial of Chaos → Adorned, checked against current drop info first). Shows runs, runs since the last chase drop, the drop history and your runs per drop; a small run counter on the overlay inside a trial. Later: drop rates pooled through Community data sharing (opt-in).
- **Community FAQ → Community forum** (expanded 2.85.1; mockups first, when it comes up): the FAQ works like a forum, a hybrid of two popular forums - threads in sections (Questions, Farm strats, Trading, Builds, General), each post under the player's community name (asked once at start-up), replies, and upvotes that count for both farm strats and FAQ answers. The asker marks the answer that solved it, and that answer goes to the searchable FAQ (e.g. "Can Sanctify add a socket, or only corruption?" -> "Corruption only ..."); players who opted in get unanswered questions offered to them. A player profile shows their posts and total upvotes (reputation), as on the trading-style popular forum. Moderation follows admin privileges plus the 2.85.0 reviewers: reports with reasons, hide / lock / pin / move threads, edit history, bans. Runs on the community board server (board/). **To solve first:** how the app gets updates - pulling new threads, replies, votes and moderation changes (when to poll and how often, what to cache on this PC, unread counts, notifications, staying inside the board's free-plan limits).

## 💤 Parked (not planned unless something changes)

- **One-key copy:** stays an experiment; Ctrl+Alt+C is the reliable way.
- **Automatic loot logging, auto-syncing stash tabs:** too intrusive / too many trade-site requests.
- **Gold from selling in the Session tracker:** no reliable way to count it.
- **One-click price note, "worth listing vs vendor" split, price history charts, map stats by waystone mod:** good ideas, not needed right now.

## How the app is organised (decided in 2.33.0)

Every new feature goes in one of three places:

- **Top-level tool:** you open it on its own (dock, Toolkit menu, desktop icon). Now: Price checks, Wealth, Money Makers, Regex, Game search, Exchange rates, Session tracker, Notes, Settings. (2.74.0: the Calculator is over the game, from the overlay's bar.)
- **Child tool:** built on one top-level tool's data. It is a button in the parent's title bar and sits indented under the parent in the Toolkit menu. Its window is called "Parent › Child". It is not on the dock. Now: Session tracker › Map library; Price checks › Under the hood › Mod book, Market Insights. 2.74.0: a child tool can have its own child (one level deeper); `advanced = True` hides a tool unless Settings › Advanced › Show advanced tools is on (Under the hood, the Mod book).
- **Tab:** a different part of the same tool (e.g. Money Makers › Strats / Lucrative Strats / Tablet Craft Helper / Farm Tracker). **2.64.0: a page's tabs are listed in the sidebar under the page, indented with ↳ - never as a button row along the page's top.** 2.65.0: the sidebar shows only the tools at first; the open one unfolds. A tab that is the page itself is passed as `home=` and not listed (Regex: Build a search). Register the page's SegBar / SegBook with `shell.register_tabs("<key>", bar)` and the sidebar does the rest (a child tool's tabs go one step further in). Small switches that only change what a list or chart shows (Official / Community / Mine, Total / Daily, Item / How it's priced / Raw) stay on the page.

**Look (2.34.0):** messages to the player go through `app_toast(text, title, kind=...)` (2.35.0); a list's own right-click actions go in `tree.menu_actions` (2.36.0).

**Tokens:** use the tokens in `soe2/style.py`: text sizes `SMALL 9 / BODY 10 / HEAD 12 / TITLE 16`, spacing `4 / 8 / 12 / 16 / 24` (0-2 only for hairlines), colours by `role()`. Buttons: `Primary.TButton` (one main action per area), plain `TButton`, `Quiet.TButton` (cancel, back, small helpers), `Danger.TButton` (deletes or clears). `tools/check_tokens.py` and `tools/check_contrast.py` run on every PR.

There's only one level of child tools: a child tool has no child tools of its own (it can have tabs). In code, `parent = "<key>"` on the module does it.

## Rules this project keeps

The GGG Terms of Service check in [TOS.md](TOS.md) comes first; these follow from it.

- **Lean pull requests.** Only what the app or its build needs: no screenshots or pictures (except the matching templates in `soe2/templates/` and the app icon), no scratch files. Before / after pictures go in the PR's description, not in the repository.

- **One action per key press.** Nothing is automated in the game.
- **Only reads what's yours to read.** No game memory or packets; only your clipboard, the game's own log file and your own screen.
- **Respects the trade site.** Its limits are respected and nothing syncs on a timer.
- **No copied art or data.** All game data comes from RePoE, and the icons are original.
