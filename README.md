# StashOfExile2

*One tool to rule them all.*

> **GGG ToS safety check - read first.** One key press = one action, only when you press it · nothing acts in the game by itself (watchers only look and show) · never touch the game's memory, code or traffic · the mouse is never moved or clicked for you · it reads only your clipboard, Client.txt, screen pixels, the trade site (within its limits) and poe.ninja. Every change must pass all of [TOS.md](TOS.md) (`tools/check_tos.py` checks the code on every PR).

> **Who we build for - read second.** Path of Exile players are utilitarian: they love data and information, problem solving and creative thinking. So every feature shows its numbers *and how they were worked out*, lets you sort, filter, compare and export them (CSV), keeps power-user depth (keys, versions, raw data) one click away instead of hiding it, explains in plain words, and leaves the decision to the player. Pretty is welcome; vague is not.

A Windows toolkit for **Path of Exile 2** that runs next to the game. Its main job is pricing items from the official trade site, in bulk or one at a time, with a Campaign Helper, League Focus and a session overlay alongside.

Hover an item in game and press **Ctrl+D** to price check it, or **Ctrl+Alt+C** to add it to the Bulk Pricing list. Prices come from the official trade site, using the mods that decide them.

> **Written by AI.** This project's code, data tools and text were written by Claude (an AI made by Anthropic), directed and tested by a human who plays the game. It's shared openly so anyone can read it, check it, change it and use it.

## What it does

- **Price Checks:** hover an item in game and press **Ctrl+D** (change it in Settings › Hotkeys). Its card shows every filter on the left and the trade site's listings on the right, with mods and tiers, price, seller, when it was listed and the item's picture. Your last 20 checks stay in the Recent list on the left. A fractured or desecrated mod can be searched as only that; hybrid resistances add a total per resistance; socketed rune lines stay out unless you tick them.
- **Privacy & community (Settings):** what leaves your PC (nothing unless you turn it on), the data sharing switches, and your community name - why you'd want one, what's stored, rename, reviewer, admin, move it to another PC, delete everything.
- **Help rate mods:** Colors by source and folding sections on Price Checks, Rate ▾ beside each mod, or rate mods one at a time, starting with the items you know best (S to F; F = ignore). Your ratings tune your own price checks at once. Bulk Pricing skips items the Mod book is sure sell under your floor (1 div by default).
- **Rep and the contributor icon:** helping the community (upvoted strats, accepted edits, reviews, ratings that match everyone's) earns rep, and a small icon beside your name steps up in color. Hover it for the card. Nothing is locked behind it.
- **Favorites:** press ☆ Add to favorites on Price Checks, or paste a trade-site link. Each favorite opens with its filters and the trade site's listings. Sort them into groups, drag them into your order, rename, edit or duplicate them from the right-click menu.
- **Bulk Pricing:** press **Ctrl+Alt+C** on many items (tablets, jewels, waystones, gear) and they are priced from the official trade site as a list. Each item opens in one clean panel with every trade filter: this base or any of its kind, item level, quality, sockets, requirements, Any / Yes / No flags (corrupted, fractured, desecrated, sanctified ...), and each mod with Min / Max and ★ for must-match. You also get a confidence rating and how the price was worked out. It can read a whole public stash tab, listed in the tab's own order (down each column, or across each row).
- **Overlay over the game:** a bar on the XP bar, scaled to your resolution. One ON | OFF switch turns it on or off. It shows the session timer, map, maps run, the average per map, the clock, Notes, a calculator and your Regex favorites (Vendor searches too, in campaign towns). When you enable it, you pick which helper switches it holds (Campaign, Focus, Breach, Delirium, Ritual, Expedition); the map's time, area and rank share one part. It shows only while the game is in front. Screenshots show it; if it covers a counter the Ritual or Delirium watcher reads, a switch hides it from captures while they run. A ⚙ by its lock opens its settings; right-click it for Quick settings over the game (style, sound, lock, what's on the bar). Every part has its own switch. Price checks can open in a card over the game too (Show over the game, top right of Price Checks): the price, the mods with Min / Max to type in, and the cheapest listings, in the overlay's Style. Notes, Calc, Regex favorites, Rates and the cards over the game all take the overlay's Style. Styles: Classic (default), the light Hairline, Slate, Split and Micro, and the ornate Herald, Gilded, Warbanner, Verdant, Gloom, Totem, Hellfire, Psionic and Guildhall (their own colours and bundled fonts).
- **Exchange rates over the game:** a small window in the overlay's look with today's most-used rates (off until you turn it on; then Rates ▾ on the bar opens and closes it).
- **Trade Whisper Watcher:** at league start your items sell by whisper - a card over the game shows each "I would like to buy your…" whisper (item, price, where it is in your tab, who) so you don't miss it in chat. On during the campaign; it can stay on after. Nothing is saved.
- **Campaign Helper:** where you are, what's next and which rewards you missed, act by act from the game's log, on a line docked to the overlay bar (with League Focus on too, both share one bar). It asks Speedrun or Full rewards when a campaign starts and follows that guide. It includes act routes, Vendor tips and act splits. Past the campaign it hides in maps and comes back when you visit a campaign zone.
- **League Focus:** a Game Plan of goals by phase (in tabs), stockpile, farm plan and build lock, plus gentle reminders over the game (map supplies, such as an Omen of Amelioration the game used up, and cheap stockpile prices). Switching it on turns the overlay on.
- **Money Makers (Labs):** community farming strats in one layout, with content tags (pinnacles, bosses, map content) and atlas screenshots, rated by Thoughts per Click and Clicks per hour. You can post and upvote on the Community board (no login: a community name, asked once; slurs and hate words aren't allowed). Only authors edit their strats; anyone can **Suggest an edit**, every change is kept (History), and opt-in reviewers check changes to Official strats and reported posts. It also has the Tablet Craft Helper and the Strat Tracker (what a farming setup really makes). Strat format: [strats/README.md](strats/README.md).
- **Regex:** builds stash-search strings for tablets, waystones, relics, jewels and gear (at least, ranges, at most), with saved Favorites. All options sit in one card, a button per setting. Copy it, then Ctrl+V into the stash search in game.
- **Exchange rates:** poe.ninja rates (refreshed hourly), an Exchange Helper with Convert, and a flip check for trades you see in game. (Arbitrage was removed in 2.92.0: GGG's terms for the data it read are unclear.)
- **Leaderboards:** your fastest campaign acts, maps, pinnacle fights and trials, and everyone's who shares (Community data sharing). Filter by league and class, and show the Top 5 to Top 100. Times come from the game's log, so they're self-reported: the board refuses impossible ones and players can report a time.
- **Map library:** every map, citadel and pinnacle fight, ranked S to D or Avoid by you and the community. You can share ranks as a file or upload them to the community (opt-in), and opt out of rank cards from the first one.
- **Desecration Helper (Beta):** the first time you reach The Well of Souls it asks if you want it. Then at the Well, each revealed option gets a tag with its tier for that item type (T1 = best), and the Abyss lords' own mods show their range and how good the roll is. It wakes up only while you're at the Well.
- **Island Rumours:** open the world map in your hideout and one panel beside the Uncharted Waters card lists the island each rumour leads to and your Map library rank for it.
- **Expedition Remnant Price Checker:** open a remnant's reward book and each reward gets its poe.ninja price next to it, with the best one marked ★. The idea comes from [PoE Ancients Price Helper](https://github.com/pedro-quiterio/PoeAncientsPriceHelper) by Pedro Quitério. None of its code is used, because it isn't open source.
- **Utilities:** chat command keys and a sticky note over the game.
- **Advanced tools (Settings › Advanced):** Under the hood and the Mod book, which learns which mods are worth money from listings and, if you opt in, from pooled community price checks.
- **Labs (off by default):** Wealth (what you own over time, from the currency you count with Ctrl+C or Scan stash - beta - which reads your Currency, Abyss, Delirium, Breach and Expedition tabs from the screen; you check the numbers before they are saved), Market Insights (by slot or tablet kind, each item drawn like a trade-site card) and an offline game-data search.

## Install

Download `StashOfExile2.exe` from [Releases](../../releases) and run it. It can update itself (Settings > General > Updates): it looks for a new version every time it starts and every hour, and the tray icon's menu has Check for updates. Each new version comes out as a preview first and becomes a full release once it has been played in game; turn on **Preview builds** there to get previews too. Your settings live in `%APPDATA%\StashOfExile2`, so updates never touch them.

**From source** (Windows, Python 3.12 from python.org):

```
py -m pip install requests pystray pillow mss numpy opencv-python-headless
py stashofexile2.py
```

**Linux:** releases and tests are Windows-only. Players can build it themselves with `build_linux.sh` (see [linux/](linux/README.md)).

To build the exe yourself, run `build_exe.bat`; it makes `dist\StashOfExile2.exe`. Every version tag pushed here builds the exe automatically and publishes it as a release (`.github/workflows/release.yml`).

## Community

Questions, ideas and bug reports: [Discord](https://discord.gg/Ta8EVnxx4T). The plan is in [ROADMAP.md](ROADMAP.md). Next up: rating mods for the Mod book and a Bulk Pricing floor, polish, then a Community forum (questions and answers, farm strats, upvotes, moderation) inside the app.

## Privacy

- **Nothing is shared unless you say yes.** Community data sharing is off until you turn it on. The question (and Settings › General › What's shared, and why?) lists each thing sent, what it's for and where it goes.
- **Anonymous:** no account or character names, no items, no listing ids. It goes only to the app's own community server, is never sold, and is never used for ads or tracking.
- **Your logs stay yours:** error logs, problem reports and bug reports leave out your Windows user name, home folder, account and character names.
- **Nobody can be singled out:** leaderboards show the day, not the time; private leagues are never shared; shared strats carry rates, never totals; your wealth never leaves your PC.
- **If the app freezes:** it writes `hang_report.txt` in your data folder - only where in the app's own code it was stuck (file, function, line), never your name, folders, items or chat. A theme change slower than 1.5 seconds writes `slow_report.txt` the same way, and the Island rumours helper writes what it read off the last Uncharted Waters card to `rumours_read.txt` (the card's words only). Both stay on your PC; share them only if you want to help.
- **Leave any time:** Settings › Privacy & community › Leave and delete my data deletes everything of yours on the community board.

## Fair play

- **One action per key press.** It never plays the game for you.
- **Reads nothing from the game itself:** no memory, no network traffic. Only item text you copy, the game's own `Client.txt` log, and screenshots of your own screen (Delirium, Ritual and Remnant watchers).
- **Respects the trade site's rate limits**, and nothing syncs on its own.

## Credits

Thank you! Each links to its developers' GitHub page.

- **[RePoE](https://github.com/repoe-fork/repoe-fork)** (repoe-fork): the game data behind the mod lists, Regex, Game search and tiers, exported from Path of Exile 2's own files.
- **[poe.ninja](https://github.com/rasmuskl)** (rasmuskl): the economy data behind Exchange rates, the rates window over the game, the Remnant prices and currency values.
- **[Exiled Exchange 2](https://github.com/Kvan7/Exiled-Exchange-2)** (Kvan7, MIT): general ideas, and the base types, mod wordings, trade-site stat ids and pseudo-total rules in `gamedata.json`, from its data files under its license; and the ideas (2.113.0) of counting each seller once and keeping a mod's Min within its tier, written our own way.
- **[Sidekick](https://github.com/Sidekick-Poe/Sidekick)**: general ideas. None of its code is used.
- **[hypr-exiled](https://github.com/gfsd3v/hypr-exiled)** (gfsd3v): the idea for the Trade Whisper Watcher, built from scratch here; none of its code is used.
- **[Path of Building PoE2](https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2)**: the anoint recipes.
- **[PoE Ancients Price Helper](https://github.com/pedro-quiterio/PoeAncientsPriceHelper)** (Pedro Quitério): the idea for the Expedition Remnant Price Checker. None of its code is used.
- **Fonts of the ornate overlay styles** (SIL Open Font License 1.1, licences in `soe2/fonts`): **[Cinzel](https://github.com/NDISCOVER/Cinzel)** (Natanael Gama), **[EB Garamond](https://github.com/octaviopardo/EBGaramond12)** (Georg Duffner, Octavio Pardo), **[Cormorant](https://github.com/CatharsisFonts/Cormorant)** (Christian Thalmann) **[Marcellus and Marcellus SC](https://github.com/google/fonts/tree/main/ofl/marcellussc)** (Brian J. Bonislawsky, Astigmatic), **[Metamorphous](https://github.com/google/fonts/tree/main/ofl/metamorphous)** (Sorkin Type) and **[IM FELL English SC](https://github.com/google/fonts/tree/main/ofl/imfellenglishsc)** (Igino Marini). Cinzel, EB Garamond and Cormorant were converted to TTF from [Fontsource](https://github.com/fontsource/fontsource)'s Latin files.

## License

The code is free software under the **GNU General Public License v3.0** ([LICENSE](LICENSE)): you can use it, change it and share it. If you share a changed version, it has to stay under the same license, with its source.

Game data in `regexdata.json`, `searchdata.json`, `tabs.txt`, `jewels.txt` and `tierdata.json` comes from [RePoE](https://github.com/repoe-fork/repoe-fork); `gamedata.json` (base types, mod wordings, trade-site stat ids, pseudo-total rules) is built from [Exiled Exchange 2](https://github.com/Kvan7/Exiled-Exchange-2)'s data files (MIT) (anoint recipes in `anointdata.json`: [Path of Building PoE2](https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2)) and belongs to Grinding Gear Games; it isn't covered by this license. Other sources and their licenses are in [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

This product isn't affiliated with or endorsed by Grinding Gear Games in any way. Path of Exile 2 is a trademark of Grinding Gear Games.
