# StashOfExile2 roadmap

> **GGG ToS safety check - read first.** One key press = one action, only when you press it · nothing acts in the game by itself (watchers only look and show) · never touch the game's memory, code or traffic · the mouse is never moved or clicked for you · it reads only your clipboard, Client.txt, screen pixels, the trade site (within its limits) and poe.ninja. Every change must pass all of [TOS.md](TOS.md) (`tools/check_tos.py` checks the code on every PR).

> **Who we build for - read second.** Path of Exile players are utilitarian: they love data and information, problem solving and creative thinking. So every feature shows its numbers *and how they were worked out*, lets you sort, filter, compare and export them (CSV), keeps power-user depth (keys, versions, raw data) one click away instead of hiding it, explains in plain words, and leaves the decision to the player. Pretty is welcome; vague is not.

**Current version: 2.138.4**

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
| 2.10.1 – 2.10.2 | Windows no longer vanish on resize / maximize / snap; typing in boxes fixed. |
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
| 2.25.0 | Copy marks clear with a double tap of Esc; pick the +'s color. |
| 2.25.1 | Faster with long lists: price updates about 15x quicker, no more freezes while saving. |
| 2.25.2 | Popups open on the monitor you're using. |
| 2.25.3 | Waystone previews show real numbers; app popups open in the middle of the app. |
| 2.25.4 | Maximized stays maximized; Slowness recorder (Settings > Advanced). |
| 2.26.0 | Timer's Helpers bar (click to switch, ⚙ to options); pricing time-left chip; Arbitrage works again (BETA); Lag finder. |
| 2.26.1 | Fix: restarting after a theme change no longer breaks the Delirium / Ritual helpers. |
| 2.26.2 | Regex type switching without freezes; maximized really stays maximized; time left from the start. |
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
| 2.34.0 | Polish 1: design tokens (4 text sizes, one spacing scale, color roles), button types (primary / secondary / quiet / danger), readable text in every theme and accent (WCAG AA, checked on every PR). |
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
| 2.74.1 | Price checks' Item card shows the mods and their values as in game; uniques' mods read (Unique Modifier headers), named rolls (Legacy of Gold) and trade-site options searched, flavor text never a mod. |
| 2.74.2 | Settings › Advanced › Report a bug (the bottom bar's form, not a .zip); a new version shows in the sidebar above Toolkit and Settings. |
| 2.74.3 | Session timer: ⏸ / ▶ on the overlay and the keyboard's Pause key (no Ctrl+Alt start / stop / pause keys); click-through its own switch, off by default. |
| 2.74.4 | Price checks: check boxes for each mod on the item card, Min / Max under Fine-tune; uniques' flavor text never a mod. |
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
| 2.82.0 | Overlay ↳ Settings: the overlay's options on their own page, in cards (On the bar, Features, Campaign, Behavior, Mechanic Helper). |
| 2.83.0 | **Island Rumors**: in your hideout, each rumor on the Uncharted Waters card gets its island and your Map library rank. Remnant watcher off in hideouts / towns / campaign, in maps only with the Expedition mark on screen, always on in Grand Expedition islands. |
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
| 2.91.0 | Exchange rates over the game (a small window in the overlay's look, off until you turn it on); Arbitrage's Check a flip picks from every exchange item. |
| 2.92.0 | Arbitrage removed - **deprecated**: it read GGG's hourly Currency Exchange history from an address outside their documented API, and GGG's terms for that data are unclear. The flip check stays, under Exchange rates › Exchange Helper. |
| 2.92.1 | Listing order lab: corrupted items match, item sizes, column-by-column order to compare (ready for a 1x1 round). |
| 2.92.2 | Overlay Enabled / Disabled (one master switch; the bar question comes when you enable it); Regex ▾ favorites on the bar; Vendor ▾ fixed and moved beside Notes / Calc. |
| 2.93.0 | Price Checks: a fractured / desecrated mod can be searched as that only (a small box beside it); a hybrid resistance adds a pseudo total per resistance (Chaos searched, the elemental one offered); socketed rune lines are marked and left out unless ticked. |
| 2.93.1 | Price Checks: listing cards laid out like the trade site; a Clear button beside Search empties Price Checks. |
| 2.94.0 | Settings › Privacy & community: what leaves your PC, the data sharing switches, your community name (why, what's stored, every action - moved from Money Makers - and Move to another PC), your rights; 👤 chips on Money Makers and Leaderboards open it; no name asked at start. |
| 2.95.0 | Rep (karma-style) and the contributor icon: upvotes on your strats, accepted edits, reviews, ratings that match the community (opt-in), an admin's thank-you; a small icon beside your name that steps up white / blue / yellow / orange, its card on hover. Nothing locked behind it. |
| 2.96.0 | Help rate mods: ▲ / ▼ beside each mod on Price Checks (your rule; gear per item class), Rate mods one at a time (S-D / Ignore) from the Mod book or Privacy & community, a gentle ask (once; Not now = once more 3-7 days later; No thanks = never); Bulk Pricing skips items the Mod book is sure sell under your floor (1 div per rule set), thin data = check by hand. |
| 2.96.1 | Overlay ↳ Settings regrouped: On the bar (one switch per item) and Options; Helpers with each helper's options and bar switch on its row; Campaign full width; doubles, the Act timer switch, the character name and the hotkey line gone; the Exchange rates window moves and follows the lock; poe.ninja credited. |
| 2.97.0 | Polish 4 - feedback round: the Rate mods ask says what it is (Count me in! / Not now / Never ask again) and opens in front; Rate mods starts with "Which items do you know best?", lights only your rating, Back / Next / Done under it; F is the ignore tier everywhere tiers show (saved as Ignore); Focus / Campaign on = their line shows (no line switch; both on = one bar, two rows, in Panel and Game bar), switching one on turns the overlay on; a finished character's campaign line and Vendor ▾ come back in campaign zones; Price Checks: Rate ▾ replaces ▲ / ▼, the card and listings fit the window (scrollbar only when needed), Fractured only ticks the mod. |
| 2.97.1 | Price Checks card: a rune's line and an affix with the same wording are ticked apart; runes in their own AUGMENTS section (no RUNE / SOCKETED lines); Fractured / Desecrated only small, right under its mod, the mod in its color. |
| 2.97.2 | Price Checks card - visual hierarchy: a mod's color says where it comes from (affix blue, rune light blue, fractured tan, desecrated green, pseudo pink; unticked = dimmed, not gray), the listing cards match; every section folds with how many are ticked, Fold all / Unfold all. |
| 2.113.2 | Island rumors matched by letter shape too (a misread middle rumor); What's new never claims a fix. |
| 2.114.0 | P8 + P9: Mod book one rating (S-F), Rate mods picker grouped, Under the hood Paste item / Price it, Exchange rates names and numbers, Notes opens the note, calculator starts blank; Listing order lab removed. |
| 2.114.1 | Wombgifts searched on the trade site by type; the price check card over the game gets the item's properties (base type, item level, quality, sockets) like the app. |
| 2.114.2 | Scan stash (beta) reads the Expedition, Ritual, Essence and Fragments tabs; "12.2K" stacks read as 12,200. |
| 2.114.3 | crash_report.txt when the app closes by itself (a theme change closed it on another player's PC; not reproduced here). |
| 2.115.0 | One bug log (app_log.txt) for errors, crashes, freezes, slow spots and refused requests; Report a bug sends it; exact build versions; ruff in Checks. |
| 2.116.0 | P10: one Keys tab (hotkeys + chat commands), overlay style picker with a live preview, Developer options (Debug mode, Unmatched mods), Advanced › Problems; Always on top / tray off for new installs. |
| 2.117.0 | Errors the app works around go to its log as [caught] (where and the type only, once per place a run); one-time settings changes in one ordered list (soe2/migrations.py); no window work from a background thread (run_bg / on_ui, tools/check_threads.py in Checks); Settings out of app.py (soe2/settings_page.py). |
| 2.117.1 | Ashen Rite froze the app on some PCs: the desktop's settle step waits for queued layout jobs instead of forcing them (a page laying itself out again never let it return); Ashen Rite uses Georgia (was Sylfaen); a layout loop is logged once a run. |
| 2.121.0 | Items pass: the trade site's own item list downloaded daily (bases and uniques newer than the game data; unknown unique names never sent; unknown kinds searched by type); tools/check_items.py checks every base and unique. |
| 2.121.1 | The price check card: Esc closes it (bindable), a ⚙ with Card settings. Unmatched mod lines ride on Community data sharing (wording only). |
| 2.120.1 | Lock position and Click-through as two switches again (the Mouse choice was confusing); Any Belts (Base type unticked) searches the whole kind; crafted "Modifier magnitudes" lines aren't searched. |
| 2.120.0 | UX pass 2: Rate Mods its own page (Price Checks ↳ Rate Mods); Settings › Price checking in groups, the price check key one choice; one-line section notes (ⓘ for the rest); one mouse choice for the overlay; Hide from captures and the window title in Advanced, rank maps on the Map Library; a Trade site pill instead of the limit meters; no duplicate title-bar buttons; one orange button a page; Title Case page names, one BETA, Beta features; one empty-state look. |
| 2.119.0 | UX pass 1: the bar's timer only as wide as itself (rank in the map text on light styles), ⚙ = Quick settings on either click; one line per helper + one Client.txt banner; Expedition always Auto (no chip or key); one name, League Plan; Pace, Accent color, Text size, the start-up screen and "overlay only while the game is in front" switches gone (old settings cleaned once); Notes' text size on the note (A− / A+); rep gone from the privacy text. |
| 2.118.0 | No helper switches on the overlay bar (one row in every style; helpers on by default for a new install, off in Helpers / Quick settings); the Ritual line over the bar (count; tribute next); real-bar style previews; theme picker with a live preview; community rep removed (app and board; its data deleted). |
| 2.113.1 | Price Checks: the Show over the game switch on its header and in Settings › Price checking (out of Hotkeys); Island rumors: the middle rumor (whole-text search, read at 2x, rumours_read.txt). |
| 2.113.0 | Each seller counts once in every price (their cheapest, "listed N times"; listings 11-20 fetched when too few sellers); Min within the mod's tier. Island rumors: all of a card's rumors (a rumor run together with the heading matched nothing; read up to 3 times), a compact panel. Price check in a card over the game (opt-in, Settings › Hotkeys › Price Checks): item, price, mods with ticks and Min / Max, cheapest listings that open to the whole item; movable, resizable, remembered; the overlay's Style. |
| 2.112.5 | Hotfix: dragging the Campaign / Focus line no longer opens its card. |
| 2.112.4 | Theme cards: a burst of clicks swaps once; the overlay is rebuilt on a theme change only in Classic; Flanks renamed Split; the Campaign / Focus line can be dragged (undocks it). |
| 2.112.3 | Quick settings' Style list stays open (Windows focus check); plain update notes; slow_report.txt for slow theme changes; overlay measuring fonts kept. |
| 2.112.2 | Fixed: app-theme changes froze / crashed on Windows (every title bar read the PC's whole font list on each redraw - now once); auto-hiding scroll bars can't flip forever. |
| 2.112.1 | A local not-responding report (hang_report.txt, code locations only) to find the Windows theme-change freeze; switches on cards take the card's color. |
| 2.112.0 | Overlay ↳ Settings › Helpers reworked: one table, a row per helper, On bar / Remind columns, option chips, grouped In maps / Play / Trading & more. |
| 2.111.0 | Ornate styles wave 2 (Totem, Hellfire, Psionic, Guildhall); What's new = hero rows + folded small changes with a big / small standard; every app color follows the theme (`tools/check_theme.py` on every PR). |
| 2.110.0 | Five ornate overlay styles (wave 1): Herald, Gilded, Warbanner, Verdant, Gloom - bar, panel and every window over the game; bundled OFL fonts (Windows + Linux, never installed); switches Campaign / Focus / Breach / Delirium / Ritual / Expedition; Avg:; the cog's Quick settings pick the Style. |
| 2.109.0 | Regex options in one card (button rows); ★ first / Only ★ / Select valuable removed; Ctrl+V hints (PoE 2 has no find key); every window over the game follows the overlay's Style / Colors. |
| 2.108.0 | Polish 7 P4 - P7 - Price Checks Recent under the card, Money Makers ⋯ menu, Regex tabs and chips, Game search Try / recent, right-click the cog = Quick settings over the game, one Island rumors panel, Game Plan in tabs, Leaderboards two-row toolbar, Map library rank group. |
| 2.107.0 | Polish 7 P2.5 - Controls refresh: segmented ON / OFF switches everywhere, flat buttons in every theme, Price Checks in 3 columns (Recent list), Overlay ON / OFF switch, one Sound switch for helpers, "Trade Site". |
| 2.106.0 | Polish 7 P3 - Wealth: synced stash tabs removed (clean start for old tab data); Count currency first, Scan stash beside it; Items From: Counted / Scanned / Added by hand; Snapshots say what happened, the change, and the picked one beside the list; the chart uses its height. Also: link favorites (a ticked stat turns its group on, Seller follows your setting, Open on trade site opens the card as it is). |
| 2.105.1 (in 2.106.0) | Feedback: a ticked stat turns its group on (link favorites); link favorites follow your Seller setting; Open on trade site opens the card as it is now. |
| 2.105.0 | Feedback: every box on the card (base, tier, item level, Corrupted / Mirrored / ..., Seller, "only") changes in place - no card redraw; Rates ▾ on the overlay bar; Map: / Avg.: labels; Leaderboards: league names and Top 5-100; Island Rumors: two causes fixed (needs an in-game check); exact searches need every ticked mod; amulet quality and anoints; 15 searches / 5 min; Market Insights slot / tablet kind and trade-site card; listing marks removed; Convert under Exchange Helper, hourly rates always. |
| 2.104.0 | Polish 7 P2 - Favorites and Market Insights: empty list says how to add; link box hint; wider card with Search / Open on trade site under it; "why nothing matched" on Favorites; Undo only when there's something to undo; Market Insights All and Gear tabs, no Refresh, columns fit, buttons under the item. |
| 2.103.4 | P1 feedback 4: "Has 1 Charm Slot" takes a Min (was read as a choice); a typed waystone tier is kept on Search; the Favorites list changes in place (it was built again on every save - the flicker); Bulk Pricing paints a tick in place. |
| 2.103.3 | P1 feedback 3: a tick repaints only its row on Price Checks and Favorites (the card was still built again - it flickered); Favorites keeps its listings on a card change; a waystone tier range searches every waystone (category + map_tier); Add trade link asks for a name; the "Staying under the limits" line on Price Checks and Favorites. |
| 2.103.2 | P1 feedback 2: a tick no longer redraws the listings (still flickered); Waystone tier row (range / any); "+" mod wordings found on the trade list; toolbar rows keep their gaps again. |
| 2.103.1 | P1 feedback: Bulk Pricing filters, Export CSV and Clear list back where they were; row actions light at once; no flicker on a tick; waystone mods take a typed Min / Max; long mods keep clear of Rate ▾. |
| 2.103.0 | Polish 7 P1 - Price Checks and Bulk Pricing: a check that finds nothing says why (Search again / Search with fewer mods); Bulk Pricing filters behind Filters ▾, Export CSV and Clear list in ⋯, row actions lit only with rows picked, a Status column (Priced / Review / Pricing), "0 div"; one font in the status bar. |
| 2.102.0 | Wealth › Scan stash (beta, may not work): a card over the game asks for one tab at a time (Currency, Abyss, Delirium, Breach › Catalysts) - Start reading finds the panel, checks the tab, reads each slot's stack number; a check window before Save (fix / drop rows); the picture is never kept; only digit shapes and slot boxes ship. |
| 2.101.0 | Overlay styles: Settings › Appearance › Overlay settings › Style - Classic (stone and bronze, as before) or four light looks drawn with plain lines and text (Hairline: no box; Slate: a flat box; Flanks: no box, numbers by the life orb and switches by the mana orb; Micro: the smallest), each as a Game bar and a Panel with the goal bar in the same style; Colors: Exile Gold, nine theme packs' sets or Follow the app theme. |
| 2.100.0 | Polish 6 - hover, focus, motion: list rows light under the mouse, clickable icons brighten; a focus ring on Tab (buttons, switches, boxes, lists); tooltips, toasts and windows over the game fade in (~150 ms; Settings › Appearance › Reduce motion, following Windows until chosen); tooltips over the game in the overlay's colors. |
| 2.99.1 | Updates: the hourly check follows Preview builds; every start checks once (badge only with the switches off); a version found mid-session gets one card (Install now / Later); tray menu › Check for updates. Roadmap: Character Appraisal and Patch notes (maybe later). |
| 2.99.0 | Mod book: Gear rules (27 item classes, every line from RePoE, S-F), Unique rules (a priced unique's lines + every option, e.g. Mageblood's Legacies), What the app learned inside each tab; a search with nothing in "listed within" retries once with older listings. |
| 2.98.6 | Expedition remnant prices back in every map (the mark check no longer blocks; a 2+ reward book confirms the map; looser mark match); runeshape tips box: Never show again. |
| 2.98.5 | Stockpile item box pick-only (the name box narrows it); map supplies "when it's used up" (Omen of Amelioration: poked back in town after the map the log says used it); the first map rank card has Opt out; Map library › Share › Upload my ranks to the community (opt-in, once per 45 min, matches the board's limit).; Two affixes with one stat (Rarity prefix + suffix) added up and searched as one line; after a No, Community data sharing is never asked again; roadmap: Privacy & data hub, "opting out is final". |
| 2.98.4 | Mageblood priced on its Legacies (Min N each; known from the game data when the trade site's list isn't loaded), its charm slots and, with a duplicate, the per-duplicate roll (the planned Mageblood search helper, built into the price check). |
| 2.98.3 | Dialogs open over the app on its monitor; One-key copy and "Other ways of copying" gone; poe2db key under Tools; Fine tuning under Price checking; no Settings › Tools (rates switch on Exchange rates); About › Credits with GitHub links. |
| 2.98.2 | Corrupted items priced as corrupted: Twice Corrupted counts; Corruption Enhancements read and searched (enchant ids, at least their value); a corrupted item's sockets searched. The Toolkit menu stays on the app's monitor. |
| 2.98.1 | Trade Whisper Watcher (Overlay › Settings › Helpers): a card over the game for each "I would like to buy your…" whisper - item, price, tab spot, who; on during the campaign, Keep on after the campaign; nothing saved. README credits the gamedata.json source correctly. |
| 2.98.0 | Polish 5 - Responsive, part 1: wrapped labels re-wrap to their width everywhere; button rows wrap (flowify) on Bulk Pricing, Regex, Money Makers, Game Plan, Overlay; Overlay › Settings switch grids drop columns; the status bar's meters step aside when narrow; one-line notes wrap. |
| 2.97.3 | Money Makers goes with Labs (hidden while it's off); the status bar loses "● Overlay" and the 📌 (Always on top stays in Settings); Price Checks: Add to favorites / Open on trade site under Search and Clear. Previews: every new version is published as a pre-release; Actions › Promote release makes it the full release after it's been played; Settings › Updates › Preview builds (opt-in) gets previews, auto-install too. |

## ▶ Next up

Re-styling the app (e.g. the YouTube Music-style shell) is set aside for later (2.57.0).

Order (decided 2026-11-05): the page passes, then the Privacy & data hub, then the craft helpers, then a stress test of every menu. Linux is player-built.

| Step | Plan |
|---|---|
| 2.122.0 | Price Checks: a row at the top says what the price check key does (On this page / In a card over the game), replacing Show over the game. Anonymous contributions stay in the pool after Leave and delete. |
| 2.123.0 | Craft Helper phase 1: Tablets and Jewels, every mod rated S-F with where it came from (you, players, market, default); no prices, no stash regex. UX pass 3: price checking settings in three groups, Price Checks verdict strip + Recent chips, Bulk Pricing one toolbar row / Columns ▾ / Item pane on pick. |
| 2.123.1 | Rate limits: 12 searches / 5 min, learns the site's unreported limit, 5 / 5 min for 30 min after a penalty; Skip cheap items isn't overruled by built-in High marks; the limits window doesn't flicker. |
| 2.123.2 | Hotfix: Price Checks' buttons under the item again; Here \| Overlay \| Both. |
| 2.123.3 | Hotfix: Here \| Overlay + Here; a draggable divider for the item's width on Price Checks. |
| 2.123.4 | Craft Helper phase 2: a verdict per item (Worth pricing, Craft on, Reforge, Vendor) and Price it; a smooth divider with a visible grip on Price Checks. |
| 2.123.5 | US spelling everywhere (the game's own words stay as the game writes them); `tools/check_spelling.py` on every pull request. Island Rumors only on the real card (its own lines must be read). |
| 2.123.6 | The app opens on the monitor you left it on (Windows' own placement record; each monitor checked). |
| 2.124.0 | The Campaign / Ritual / NOW lines inside the overlay (it grows up, the bar never moves); Zone timer in campaign zones (no rank, Maps, Avg); a Campaign zones leaderboard (opt-in); the route card swaps tabs and ticks lines in place; Layout first and Panel previews in Settings; Game bar is now Bar; Quick settings tips; no Death Recap. |
| 2.124.1 | Classic Panel in the Bar's look (and the lines over it); Quick settings Layout; Panel menus inside the frame; the map's name cut before the time shrinks; the window's place saved before an update; Zone time from entering a zone; no preview flicker. |
| 2.125.0 | Campaign Helper: a Rush (carry) route from the carrier's side (each step's rush line in the guide pack; order from poe2wiki's Acts quick guide). |
| 2.125.1 | Quick settings in the overlay's style; the Settings preview's freeze / flicker; the start-up screen centered on a maximized app's monitor. |
| 2.125.2 | Updates: starting the new version waits (up to 20 s) while Windows still holds the downloaded file (WinError 32). |
| 2.125.3 | Campaign route card: scrolls and fits the screen, stays up while its act list is open, Routes ▾ and Options ▾ on the card; routes named Full, Speedrun, Rush (carry), My Own; Reload Overlay in Quick settings; Bulk Pricing shows every column (Columns ▾ turns them off). |
| 2.125.4 | Route card: act list on the right, Routes ▾ rows divided and the one in use marked, quicker (pages built as shown, the overlay line after), your size kept. |
| 2.125.5 | Craft Helper phase 3: learned mod pairs and its data pack from GitHub (per game patch). Updates fetch the newest version at download time (no double updates). Cards over the game in the overlay's style. Price check card: what's socketed. |
| 2.125.6 | What's new shows notes about beta features only with Beta features on. Search Options (with Prices in); no Mod Book or Shortcuts rows (shortcuts removed); the overlay's ⚙ says In the app; Craft Helper's pairs on a divider. |
| 2.125.7 | Desecration Helper wakes at The Well of Souls by its name and when started there; says why it can't read the screen. A magic tablet with 2 bad mods: Reforge or Alchemy. |
| 2.125.8 | Leaderboards: a board looked up twice no longer draws half its rows (only the newest answer); a board with only your time says why. Sharing opt-in on the quick start; sharers asked once for a community name (times need one). |
| 2.126.0 | **UX pass 3 (code):** dead code out; tools/check_removed.py (a removed feature leaves no text, setting or test behind), soe2/names.py + tools/check_names.py (one name per feature), tools/check_ux.py (one orange button and one BETA chip per screen; lists the round 2 items). Bulk Pricing: Undo, Delete and Clear All as small buttons in the Items strip. |
| 2.127.0 | Lineage gems priced; currency's going rate in the price check card; the session survives a close / update / crash; Mageblood Legacies found by wording; Bulk Pricing's Item pane always on screen; Regex favorites lockable; Settings › Keybinds with ↺ Defaults; Ritual watcher stays running; Remnant log. |
| 2.128.0 | **Favours prices:** the Ritual helper prices each 1-cell reward in the Favours window (poe.ninja art + pictures learned from your price checks). |
| 2.128.1 | Expedition and Favours price tags show in screenshots, screen share and streams (the watchers paint over their own tags before reading). |
| 2.129.0 | Favours prices from learned pictures only (Scan stash, price checks), no uniques, ★ Mageblood / Headhunter; Tribute reminder; Remnant reads only under its title; exchange items priced on poe.ninja; Ritual watcher restarted when it stops. |
| 2.129.1 | Ritual watcher no longer stuck at start (it loads before reading the app's pipe); Remnant looks for the book's title in its own place; gray, sealed Favours rewards read; tribute banner 4 s. |
| 2.129.2 | Trade whispers is on or off (its After the campaign option is gone - its switch couldn't turn it on); Remnant prices fetched before a book opens (the first read waited 14 s). |
| 2.129.3 | Favours: same-shape omens told apart by color, Sacred Bloom and idols ship, a copy in the window teaches a reward (idols), ★ Rite of Passage, tags cleared on a reroll; tribute read from the last look; Map Content's ticked Ritual icon = all done; Overlay + Here leaves the app alone; pages follow to another monitor. |
| 2.129.4 | In a map with Ritual still to do, the bar is left out of captures so the watcher can read the counter under the Ritual line. |
| 2.130.0 | AGPL-3.0 (up to 2.129.4 GPL-3.0); new league heads-up; Filter in the Ritual window guide (NeverSink, Ryonnen); Game Overlay Place + Reset position; gems priced (price check key, remnant books); remnant "Could be" uniques and long books read to the end; tribute reminder not while Favours is open; learned omens ship; Ritual counts above 4 (3/6). |
| 2.130.1 | Bar at the top keeps its Ritual line on screen (under it); Bar at the bottom sits on the XP bar; tribute plate's 0 read as 0 (no late reminder); a gem's Sockets option = gem sockets. |
| 2.130.2 | No Ritual reminder through character select; theme clicks queue (no freeze); Gruvbox Dark / Light (morhetz, MIT); light themes turn all text dark; short README. |
| 2.130.3 | Client.txt found wherever the game is installed (Windows' installed-programs list, every Steam library); Desecration Helper reads Heart of the Well options. |
| 2.132.2 | Map profit: emptying your inventory between visits isn't a loss; BETA. Top Up ignores the chat box. |
| 2.132.3 | Ritual Identifier (BETA). What's new in keywords. |
| 2.132.4 | Overlay Settings name; Ritual Identifier is a Ritual helper option. |
| 2.132.5 | Shorter helper and tooltip text. |
| 2.136.0 | Temple Notepad: a note over the game, only inside the temple. |
| 2.136.1 | Temple Notepad in Vaal Ruins too; crystals read from the Temple Console (under the bar); marked old once a run starts. |
| 2.136.2 | Vaal Ruins is a town: Map profit counts temple runs (inventory before and after), the Session tracker stops counting Vaal Ruins as a map. |
| 2.137.0 | Error reports: opt-in, its own switch - where in the code an error happened and its type, trade site errors, counted - to the community board so bugs get fixed. |
| 2.137.1 | Alert cards at the top center by default (not on your character); a space after HELPERS. |
| 2.137.2 | Ritual Identifier and Temple Helper read a quarter of the screen bigger every other look: small labels found at any size. |
| 2.138.0 | Map profit: Export CSV, and Clear all asks (export first, hide from the list, or delete). Leaderboards: Export my times. |
| 2.138.1 | Fast Beacon Read (opt-in, Helpers › Temple): catches a Vaal Beacon's count as you stand on it. Alerts close with a click anywhere on them (no ×). |
| 2.138.4 | Megalomaniac: each passive it allocates is read and searched. |
| 2.138.3 | Fast Beacon Read looks 30 times a second and reads only a tooltip; a stuck screen read no longer stops later looks. |
| 2.138.2 | An Abyss's depths (Lightless Void, Abyssal Depths, Dark Domain) count with their map, not as another map. |
| 2.135.1 | No fades (Reduce motion always on); Regex: Genesis Tree, warping rune and Alloy mods. |
| 2.135.0 | Page windows stay with the app; Scan stash out of BETA, Count currency in More; Temple crystals in runs. |
| 2.134.1 | Update question: What's new only, checksums stay on the release page. |
| 2.134.0 | Music Controls (BETA): ⏮ ⏯ ⏭ in a small window over the game. |
| 2.133.1 | Theme swap with the overlay open: no forced redraw. |
| 2.133.0 | Community data: every price-checked item pooled, gear too. |
| 2.132.8 | Releases: SHA-256 checksums and a VirusTotal scan link. |
| 2.132.7 | Regex keys: 4 keys, one favorite each, press = copied. |
| 2.132.6 | Regex keys; shared Regex and trade favorites; one-liner views and tags. |
| 2.132.1 | Temple Helper: your crystals on the bar, a card when they're full. |
| 2.132.0 | Map profit: what each map earned from your inventory, on your PC only; vital alert cards in red. |
| 2.131.6 | The Ritual line keeps your tribute until it's 0 or the map ends; End Delirium is an alert card. |
| 2.131.5 | Ritual line shows your tribute (the game's counter); a quick offer is seen; Top Up ignores covered looks. |
| 2.131.4 | Top Up teaches with the game's Ctrl+C (F7's copy was turned away); items that don't stack count 1 each. |
| 2.131.3 | League Plan's Map supplies moved into Top Up Reminders (the list moves over once; Keep 0 until set). |
| 2.131.2 | Community names: a made-up name asked for everywhere; names containing your account / characters turned down. |
| 2.131.1 | Start session on the bar; picker says a name is asked next; sharing asked once; popups kept above the app; League ▾ player counts. |\n| 2.131.0 | Full release: Feature Picker, Settings over the app, alert cards, Break reminders, Top Up Reminders; My Own route removed; What's new gathers 2.126-2.130. |
| 2.130.4 | Remnant: 10x read as IOX, Level 20 gems, gem budget + 6 h cache; runeshapes C/D alphabetical; Ritual filter button with its state + Turn it on (game closed, that line only). |
| Later | **Tribute counter under the Bar** (shelved, circle back soon): the game's tribute counter sits under the overlay's Bar in Ritual maps. Not by moving the Bar (no). |
| 2.128.0+ | Favours prices for bigger rewards (uniques: their art by size, priced on poe.ninja's unique lists). |
| 2.126.0+ | **UX pass round 2** (all 21 approved): paste to price, price spread, Rate ▾ on hover, card closes when the mouse leaves (hold Ctrl), Ctrl+K go to anything (Ctrl+F = this page's search), F1 keys sheet, get-started steps, Exchange Rates search/sort/pin/trend, rank on the Map Library row, one Money Makers filter bar, buttons off until a pick, one Bulk Pricing toolbar row, never color alone, Edit layout mode, hold Alt through Click-through, ↺ Defaults per section, search top left, tips on icon buttons. |
| Fix | **Wealth's old stash tab sync** (hidden since 2.106.0; Scan stash replaced it): its engine jobs, the hidden Sync button and the Stash tabs steps still ship. Remove them and their tests; tools/check_removed.py lists it as pending. |
| Plan | **Tablet Craft Helper + Mod book:** plan merging them into one place. |
| - | (Responsive part 2 - text size overlaps, sharp DPI - is folded into the page passes; started on branch wip-text-scale.) |
| Fix | **poe.ninja through our own server** - poe.ninja's API rules ask desktop apps to fetch through their own backend, not from players' PCs (the app fetches exchange rates straight from each PC today). Route it through the Cloudflare worker: one cached fetch an hour for everyone, and poe.ninja never sees players' internet addresses. |
| Fix | **Fix the Expedition rumor helper** (Session tracker › Alerts › Rumors: the island each Uncharted Waters rumor leads to) - nothing shows at all. The card can be anywhere on screen. Checked on your 6 screenshots (2560x1440, local test kit): the card finder finds the card every time, so the fault is later - the hideout gate (it starts only on an area change into a hideout), Windows' text reader on the card's handwriting, or an error the watcher swallows. 2.105.0 fixed two causes (the app started in your hideout never started it; a card read while still opening was never read again) and logs its first error - needs a check in game. Still to do if it fails: a step-by-step log under Debug mode, a test on the 6 shots. |
| Fix | **Expedition remnant price helper sometimes doesn't show** (player report, 2026-11-06: the Runeshape Combinations book open, no price tags). Find which step drops it - the book finder, the text read, or the Auto watcher's timing - with a step-by-step log under Debug mode, then fix. |
| 2.112.0 | **Price check popup over the game** (a sample; Price Checks stays in the app): the price-check key on a hovered item opens a semi-compact card at a spot you move / resize (remembered), in the overlay's style with a matching scrollbar - item name, class, rarity, base, item level, quality, every mod; price, matched mods; cheapest listings that expand to the full item. No seller names. Windows and Linux / Hyprland. |
| Later | **Debloat pass of the whole program:** every page, menu and setting - remove what isn't used or doesn't earn its place, merge duplicates, shorten text (after the page passes). |
| 1 | **Polish 7 - Page passes** (one version per pass, below): each page is gone through with the Page standard; I bring a findings list + mockup, you suggest changes, then I build it. |
| 2 | **Privacy & data hub** (one home - Settings › Privacy & community): every point where data is collected, typed in or shared, and every community vote, listed in one place - what it is, what's sent (if anything), where it goes, why, its on / off switch and "delete mine". Covers Community data sharing (mod prices, Mod book votes, map ranks, campaign zones), Rate mods, the Mod book's unique lines (unique_mods.json, item wording only, never leaves the PC), map rank cards, Leaderboards, Money Makers strats / votes / reports / pictures, the community name, Trade Whisper Watcher (nothing saved), the Strat Tracker, Wealth (never leaves the PC) and anything added later (each new one must join this list). Opting out of anything is final: it's never asked again - not later, not in a few days. |
| 3 | **Tablet Craft Helper + Jewel Craft Helper** (player feedback: "preload all tablets I have listed and grade them for me - what to reforge, what to regal and what to div"): a Start / Stop button on the helper page listens for Ctrl+Alt+C copies and feeds them only to the helper (not Bulk Pricing) while on; the whole batch is graded Reforge / Regal / Divine / Keep. The Jewel Craft Helper uses the same mechanism for jewels. Windows and Linux (the clipboard path works on both). |
| 4 | **Stress test every menu:** go through each page and menu, try everything, log what breaks, fix it. |
| - | **Linux:** player-built. `build_linux.sh` stays in the repo; the project builds and tests Windows only (decided 2026-11-04). |
| Later | **Stash tab reads in stash order** (from the listing-order lab, 2026-11-05): the trade site's order for same-price items is random and reshuffles every read, so nothing to decode - but every listing carries its tab spot (x / y, 0-based; a whisper's "left 12, top 5" = x + 1, y + 1). A tab read lists items down the columns (how you walk a tab) with "left X, top Y" on each; a search returns at most 100 listings, so a tab of 100+ items is read in split searches until every square is covered (and says what's still missing). The Listing order lab's 1x1 round isn't needed. |
| Very end | **Kind words** (a hidden, opt-in easter egg): short affirmations in a quick centered box over the game, like PoE's loading-screen tips (e.g. on zone loads, at most every N minutes, fading after a few seconds). Found only by digging through the menus. I keep the rotation myself with little upkeep and no spoilers (the raw lines shouldn't be easy to read); how I add lines is still to decide - a scrambled file in the repo plus an Actions form, the board server, or lines built into each release. A starter template of lines. Extra polish. |

### Page passes (Polish 7) - in this order

Most-used first; pages that share data go together so their doubles can be merged in one go.

| Pass | Pages |
|---|---|
| P1 | Price Checks (list, item card, Bulk Pricing, Search) |
| P2 | Price Checks' children: Favorites, Market Insights (Bulk Pricing was in P1) - ✅ 2.104.0 |
| P2.5 | ✅ 2.107.0 - **Controls refresh** (feedback: "the buttons feel amateur, the UI a bit generic"): one app-wide pass on the controls themselves, in style.py, so every later pass gets them - buttons (shape, depth, hover / press, icon + text), toggle switches, entries, dropdowns, check boxes, tabs, headings. Mockup first (2-3 directions per theme), you pick, then build. |
| P3 | ✅ 2.106.0 - Wealth - and remove the public stash tabs from Wealth (Stash tabs page, Sync stash tabs, the odd-price setup, synced items, every step / chip / help line about it): Scan stash replaces it. Price Checks › Add items from: Stash tab stays (it still has a use there). |
| P4 | ✅ 2.108.0 - Overlay hub, Overlay › Settings, the bar itself (Panel and Game bar), helpers' pop-ups (done in 2.107.0: the "In game: Pause / resume" line gone, Overlay ON / OFF switch, one Sound switch); right-click the cog wheel = a small settings pop-up over the game (left click still opens the full Settings in the app). |
| P5 | ✅ 2.108.0 - Overlay's children: Game Plan, Map library, Leaderboards |
| P6 | ✅ 2.108.0 - Money Makers (Strats, Lucrative Strats, Tablet Craft Helper, Farm Tracker, strat editor) |
| P7 | ✅ 2.108.0 - Regex, Game search |
| P8 | ✅ 2.114.0 - Under the hood: Mod book, Rate mods - and remove the Listing order lab (an admin tool, done its job). |
| P9 | ✅ 2.114.0 - Exchange rates, Notes, Calculator |
| P10 | ✅ 2.116.0 - Settings (every tab), Privacy & community, About, the welcome / what's new card, first start - plus Settings › Advanced › Developer options (off and hidden until switched on): a Debug mode for Windows and Linux builds (more detail in the error log, a debug line in the status bar, nothing personal logged); an Unmatched mods page - every mod the app couldn't find on the trade list (unmatched_mods.txt) beside the closest trade wording, so each mismatch points at its fix. |

### Next UI/UX pass - notes (collected as they come)

- Map profit on the overlay bar (feedback 2026-11-12: "the profit tracker on the overlay needs some visual improvements"): "+9.8 exalted" sits tight against Avg with no separator and the word "exalted" is long for the bar.

### Page standard (every pass checks the same things, in this order)

1. **Purpose:** one sentence for what the page is for; one primary action (accent), everything else secondary or quiet.
2. **One home per thing:** a setting or action that also lives on another page is merged into one place (the other page links to it). Same thing = same name everywhere.
3. **Layout:** anything drawn to a width redraws when the window changes size (nothing cut off, no stale widths); section cards (same title, padding, spacing); most-used first; related controls grouped; rarely used actions in "⋯ More"; nothing cut off at 100-150 % text.
4. **Words:** plain US English, short labels, no jargon; a tooltip for anything that isn't obvious; numbers right-aligned.
5. **Controls:** switch for on / off, segmented bar for 2-4 choices, dropdown for 5+; a choice that matters is asked as a question ("Which items do you know best?"), not a bare dropdown.
6. **Flows and pop-ups:** open in front, focused, centered on the app and on the app's monitor (never another screen - menus, dialogs, tooltips, cards); steps end with **Back | Next | Done** centered at the bottom; an ask offers **Yes-action | Not now | Never ask again** (Not now asks once more, later) and says how long it takes and that you can stop any time - never an open-ended "a few".
7. **States:** empty (what to do next, with the button), loading, error and disabled states say why; selected / your choice is lit on its own (one highlight, never two), and not by color alone.
8. **Feedback:** every action confirms (toast or inline); deletes ask or can be undone.
9. **Tiers and ratings:** S / A / B / C / D / F everywhere tiers show; F = ignore, with "F = ignore" said where it appears.
10. **Over the game:** the overlay's theme; works in every bar style (Panel, Bar); one switch per item, no doubles.
11. **Privacy:** nothing personal shown or logged; anything shared is opt-in and says what, why and where; it's listed in the Privacy & data hub; an opt-out (No, Never, a switch turned off) is never asked again.
12. **Accessibility:** keyboard reachable, focus ring, contrast (WCAG AA), icon buttons named.
13. **Proof:** before / after screenshots in the PR; tests updated.

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
- **Not color alone:** selected / avoided / valuable / error states also change shape, icon or weight (✔, ✕, ★, bold).
- **Keyboard:** every action reachable without a mouse, in a sensible Tab order, with a visible focus ring; no keyboard traps.
- **Timing:** toasts can be paused and found again later; nothing important disappears before you can read it.
- **Motion:** nothing flashes more than 3 times a second; Reduce motion turns animations off.
- **Resize:** text up to 150 % without cut-off text or overlapping controls.
- **Names:** every icon-only button gets a text label or tooltip. (Tk gives screen readers little to work with on Windows, so full screen-reader support is not promised.)

### Ideas Board picks (decided 2026-11-09)

From a research pass on PoE1 / PoE2 tools, forum and Reddit wishes. Order to be set.

| Area | Plan |
|------|------|
| New | **Waystone danger check:** Ctrl+D on a waystone marks each mod OK / Careful / Can't do for your build (a list you set once; mark + word, not color alone). |
| New | **Crafting view (one place for three ideas):** the mod pool (what can still roll at this item level, tiers), which currencies can be used on the item now and what each does, and the Whittling preview (which mod an Omen of Whittling + Chaos Orb would replace). Where it lives: to decide. |
| New | **Timers:** a countdown / stopwatch on the overlay's lines, started from Quick settings. |
| New | **Cheat sheets:** only with a design that adds no clutter (e.g. shown while a key is held). |
| New | **Patch notes feed:** a dot on What's new when GGG posts PoE2 patch notes (public feed). |
| Expand | **Strat Tracker:** map run profit - juice in (waystone, tablets, omens), loot out, per map and per hour. |
| Expand | **Trials & Simulacrum:** runs and chase drops in the Session tracker and Leaderboards. |
| Expand | **Remnant helper:** rune combinations and Verisium (Runes of Aldur). |
| Expand | **Ritual pricing:** the tribute board priced like remnants, reusing the Wealth / Scan stash item recognition. |
| Expand | **Price check history:** "last time: 3 ex, 4 days ago" and a small chart, kept on this PC. |
| Expand | **Trade whispers to your phone:** optional, inside Trade whispers (your own Discord webhook), off by default. |
| Expand | **Bulk Pricing - where it was:** remember the screen spot of the + marker for each item; clicking the item's name in Bulk Pricing shows the + there again. |
| UX | **One home for the overlay's look:** Style and Layout live in Settings › Appearance; Overlay Settings links there; Quick settings stays the one shortcut. |
| UX | **"Settings" in the Overlay group becomes "Overlay Settings"** (one name per feature). |
| UX | **Search box everywhere:** check every list page and Settings have one (top left, first in the toolbar). |
| UX | **First-run setup:** check the current flow covers league, log, overlay, keys and sharing in one Back / Next / Done. |
| UX | **Privacy & data hub** (planned #2) also gathers Under the Hood's info and every manual data job - Rate mods, map ranks and the like - in a "Manual data submissions" section ("when you're bored"). |
| Test | **Ultrawide pass:** the overlay, cards and Price Checks at 5120x1440 and 3840x1080. |
| Data | **Campaign guide pack:** update the first week of December. |
| New | **Suggest a feature** (decided 2026-11-12): next to Report a bug, the same form for an idea. When an idea ships, What's new and the README credit the person, only by a name they choose to give (nothing sent or shown unless they opt in). |
| Future | **Atlas progress tracker** (only if the log shows enough to track it), **leveling gems from a PoB code**, **debloat pass**. |
| Future | **Buff watch** (a player's ask, 2026-11-09): one buff you pick (Guard, an aura) read from the game's buff bar and shown big near your health bar (BETA, off by default; pixels only, no memory, no keys). GGG's stance on mirroring UI is a gray area (Hinekora, AGPL-3.0, says so) - check before building. |

### Strat & profit overhaul (asked 2026-11-12)

One run record for the whole app (area, time, loadout, content, loot, profit) that Session, Map profit, Strat Tracker and Leaderboards all read - so each page shows the same runs its own way. May move features between pages; a UX/UI pass comes with it.

| Area | Plan |
|------|------|
| Link | **Map profit ↔ Strat Tracker:** each run's profit counts toward the strat you're running (per run, per hour, best and worst run). |
| UX | **Create a strat - one panel, no wall of switches:** activity (Atlas map, pinnacle boss, temple ...), map type, solo / party, atlas masters (pick per master, up to their limit), content tags (search, or type a new one), loadout (waystone + tablets), and the rarity it adds up to (waystone + tablets + character), each number one hover from how it was worked out. |
| New | **Pinnacle content:** ready-made strats per pinnacle boss - fragments in, drops out, profit per kill. Lives in the Strat Tracker as an activity (decided 2026-11-12); profit per kill comes from Map profit. |
| New | **Content mix bar** in the Session tracker: the share of your runs per content (Abyss, Breach, Delirium, Ritual ...), with a mark and a word per part, not color alone. How runs get their content: Map Content's icons (already read for Temple and Ritual) first; tablets in the map device as a later idea. |
| Expand | **Run history:** one row per run with its content tags, time, rarity and profit; pin the drops you care about to the top. |
| Credit | Ideas (not code, words or design) from Juice Tools (juicetools.app, by Mort). Its terms keep its code, design and text its own, so ours is built and worded from scratch; credited in the README for the ideas. |

## 🤔 Maybe later (ideas to weigh when the plan above is done)

- **Community FAQ → Community forum** (expanded 2.85.1; mockups first, when it comes up): the FAQ works like a forum, a hybrid of two popular forums - threads in sections (Questions, Farm strats, Trading, Builds, General), each post under the player's community name (asked once at start-up), replies, and upvotes that count for both farm strats and FAQ answers. The asker marks the answer that solved it, and that answer goes to the searchable FAQ (e.g. "Can Sanctify add a socket, or only corruption?" -> "Corruption only ..."); players who opted in get unanswered questions offered to them. A player profile shows their posts and total upvotes (reputation), as on the trading-style popular forum. Moderation follows admin privileges plus the 2.85.0 reviewers: reports with reasons, hide / lock / pin / move threads, edit history, bans. Runs on the community board server (board/). **To solve first:** how the app gets updates - pulling new threads, replies, votes and moderation changes (when to poll and how often, what to cache on this PC, unread counts, notifications, staying inside the board's free-plan limits).

- **Mod matching, our own** (feedback: "we frequently have missing mods"): the trade site's daily stat list (GGG's public data) becomes the main source, with our own rules from the game's wording to the trade wording - singular / plural ("Has 1 Charm Slot" / "# Charm Slots"), reduced / less = negative increased / more, with or without "+" / "to", local vs global (weapons, armor), hybrid mods split; wordings you fix by hand are learned (on this PC); the Unmatched mods page (from P10) shows what's still missing so each gets a rule. The bundled gamedata.json (Exiled Exchange 2 data, MIT, credited; a snapshot from Oct 24 2026, not refreshed) becomes the backup, then goes. Not reading the game's own files (7.9).

## 💤 Parked (not planned unless something changes)

- **Not doing (Ideas Board, 2026-11-09):** loot filter quick edits (FilterBlade does it), a missing-key warning, exchange rate history (poe.ninja's history is too thin), campaign layout hints (no free data), merchant earnings (the game and trade site have it), Character Appraisal (not yet), Scan stash Socketables (too many, change every league), map stats by waystone mod, map radar / memory readers, logged-in features, model price predictions.

- **Bulk Pricing speed** (on the shelf): fewer searches per list, never more than the limits (no proxies / VPNs - clause 22). Check what the app already does, then: poe.ninja first for stackables and uniques, one search for identical items, reuse a recent result, 10 listings per fetch, fewer lowered tries when they rarely help, price obvious junk without a search unless ticked, run right at the limits the site sends back.
- **Campaign guide pack refresh** (shelved until the 1.0 data is out - nothing can be done before it) for 0.5.5 and then 1.0: Dreadnought Vanguard is gone (Jamanra in The Dreadnought), Azarian moved to the Heart of Keth, the Waterways levers are pressure pads, the Primal Arena's +2 points moved to Omniphobia, the Whakapanu shark's permanent choice and Plunder's Point are missing, and about 10 Interlude zones are missing. 1.0 may bring Acts 5-6. The pace choice stays: Full rewards (normal pace), Speedrun and My own, each switching the optional steps on / off (2.89.0).
- **One-key copy:** stays an experiment; Ctrl+Alt+C is the reliable way.
- **Automatic loot logging, auto-syncing stash tabs:** too intrusive / too many trade-site requests.
- **Gold from selling in the Session tracker:** no reliable way to count it.
- **"Item sold" alerts from the trade site's history page; a login token for price checks:** both need your login session stored on this PC (full account access if it leaked), and a logged-in trade search is not faster - it adds the account's own, stricter rate limit on top of the per-IP one.
- **One-click price note, "worth listing vs vendor" split, price history charts, map stats by waystone mod:** good ideas, not needed right now.

## How the app is organized (decided in 2.33.0)

Every new feature goes in one of three places:

- **Top-level tool:** you open it on its own (dock, Toolkit menu, desktop icon). Now: Price checks, Wealth, Money Makers, Regex, Game search, Exchange rates, Session tracker, Notes, Settings. (2.74.0: the Calculator is over the game, from the overlay's bar.)
- **Child tool:** built on one top-level tool's data. It is a button in the parent's title bar and sits indented under the parent in the Toolkit menu. Its window is called "Parent › Child". It is not on the dock. Now: Session tracker › Map library; Price checks › Under the hood › Mod book, Market Insights. 2.74.0: a child tool can have its own child (one level deeper); `advanced = True` hides a tool unless Settings › Advanced › Show advanced tools is on (Under the hood, the Mod book).
- **Tab:** a different part of the same tool (e.g. Money Makers › Strats / Lucrative Strats / Tablet Craft Helper / Farm Tracker). **2.64.0: a page's tabs are listed in the sidebar under the page, indented with ↳ - never as a button row along the page's top.** 2.65.0: the sidebar shows only the tools at first; the open one unfolds. A tab that is the page itself is passed as `home=` and not listed (Regex: Build a search). Register the page's SegBar / SegBook with `shell.register_tabs("<key>", bar)` and the sidebar does the rest (a child tool's tabs go one step further in). Small switches that only change what a list or chart shows (Official / Community / Mine, Total / Daily, Item / How it's priced / Raw) stay on the page.

**Look (2.34.0):** messages to the player go through `app_toast(text, title, kind=...)` (2.35.0); a list's own right-click actions go in `tree.menu_actions` (2.36.0).

**Tokens:** use the tokens in `soe2/style.py`: text sizes `SMALL 9 / BODY 10 / HEAD 12 / TITLE 16`, spacing `4 / 8 / 12 / 16 / 24` (0-2 only for hairlines), colors by `role()`. Buttons: `Primary.TButton` (one main action per area), plain `TButton`, `Quiet.TButton` (cancel, back, small helpers), `Danger.TButton` (deletes or clears). `tools/check_tokens.py` and `tools/check_contrast.py` run on every PR.

There's only one level of child tools: a child tool has no child tools of its own (it can have tabs). In code, `parent = "<key>"` on the module does it.

## Rules this project keeps

The GGG Terms of Service check in [TOS.md](TOS.md) comes first; these follow from it.

- **Lean pull requests.** Only what the app or its build needs: no screenshots or pictures (except the matching templates in `soe2/templates/` and the app icon), no scratch files. Before / after pictures go in the PR's description, not in the repository.

- **Opting out is final.** When you say no to anything (sharing, an ask, a card), it's never asked again - not later, not in a few days. Only you turn it back on, from its switch.
- **Everything follows the look you picked.** App windows, cards and dialogs use the app theme's tokens (`C[...]`); everything over the game uses the overlay Style (`App.ov_palette`). No hard-coded colors (`tools/check_theme.py` checks every PR); colors that must stay fixed (item rarity) are marked `# theme-ok`.
- **What's new never claims a fix.** A note can't know a fix worked on every PC: it says what changed and that it should help, never "Fixed X".
- **What's new: big first.** Each version's notes are `big` (hero rows) and `small` (folded lines), by the standard in `soe2/whatsnew.py`: big = a player would notice it without being told, or needs it to keep playing the same way (new tool / style / helper, something moved or works differently, anything about data or privacy, a widely hit fix); at most 3 per card.
- **One action per key press.** Nothing is automated in the game.
- **Only reads what's yours to read.** No game memory or packets; only your clipboard, the game's own log file and your own screen.
- **Respects the trade site.** Its limits are respected and nothing syncs on a timer.
- **No copied art; data credited.** Game data comes from RePoE, plus `gamedata.json` from Exiled Exchange 2's MIT data files (credited in README and THIRD_PARTY_NOTICES); the icons are original.
