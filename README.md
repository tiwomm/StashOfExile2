# StashOfExile2

*One tool to rule them all.*

> **GGG ToS safety check - read first.** One key press = one action · nothing plays the game for you · never touches the game's memory, code or traffic · reads only your clipboard, Client.txt, your screen, the trade site and poe.ninja. Every change must pass [TOS.md](TOS.md).

A Windows toolkit that runs next to **Path of Exile 2**: price checks, bulk pricing, an overlay with helpers, and planning tools. Written by Claude (an AI by Anthropic), directed and tested by a human player. Open source.

## What it does

**Pricing**
- **Price Checks** - hover an item, press **Ctrl+D**: price, how sure, and how it was worked out.
- **Bulk Pricing** - **Ctrl+Alt+C** on many items (best for tablets, waystones, jewels); priced as a list.
- **Favorites** - save a search or paste a trade link.
- **Rate Mods** - rate mods S to F; your ratings tune your price checks.
- **Exchange Rates** - poe.ninja rates, a converter and a flip check.

**Game Overlay** (over the game, in your chosen style)
- **The Bar** - session timer, maps run, average per map, clock, Notes, Calc, Regex, Rates.
- **Price check card** - the price over the game instead of in the app.
- **Ritual** - counts rituals, prices Favours rewards, reminds you about tribute and unfinished rituals.
- **Expedition** - prices each reward in a remnant's book.
- **Breach / Delirium** - reminders when Hiveblood is full or a Delirium is about to end.
- **Trade whispers** - a card for each buy whisper.
- **Campaign Helper** - where you are, what's next, missed rewards.
- **Island Rumors** - which island each rumor leads to.

**Planning**
- **League Plan** - goals by phase, stockpile and farm plan.
- **Map Library** - every map ranked S to D, by you and the community.
- **Regex** - stash search strings for tablets, waystones, relics, jewels and gear.
- **Leaderboards** - fastest acts, maps and bosses (opt-in).
- **Money Makers** (BETA) - community farming strats and the Craft Helper.

**Beta** (off until you turn it on): Wealth, Market Insights, Game Search, Desecration Helper.

## Install

Download `StashOfExile2.exe` from [Releases](../../releases) and run it. It updates itself; your settings stay in `%APPDATA%\StashOfExile2`.

Each release lists the SHA-256 of every download and a VirusTotal scan of the exe.

From source (Python 3.12): `py -m pip install requests pystray pillow mss numpy opencv-python-headless` then `py stashofexile2.py`. Linux: see [linux/](linux/README.md).

## Privacy

- Nothing leaves your PC unless you turn on Community data sharing - and then only anonymous data, never names or wealth.
- Logs (`app_log.txt`, `crash_report.txt`) stay on your PC and leave out your names and folders. You see every word before a bug report is sent.
- Settings › Privacy & community › Leave and delete my data removes everything of yours from the community board.

## Fair play

One action per key press. Nothing read from the game's memory or traffic. The trade site is searched slowly, well under its limits.

## Community

Questions and bug reports: [Discord](https://discord.gg/Ta8EVnxx4T). Plans: [ROADMAP.md](ROADMAP.md).

## Credits

Thank you!

- **[RePoE](https://github.com/repoe-fork/repoe-fork)** (repoe-fork): the game data behind the mod lists, Regex, Game Search and tiers, exported from Path of Exile 2's own files.
- **[poe.ninja](https://github.com/rasmuskl)** (rasmuskl): the economy data behind Exchange Rates, the rates window over the game, the Remnant prices and currency values.
- **[Exiled Exchange 2](https://github.com/Kvan7/Exiled-Exchange-2)** (Kvan7, MIT): general ideas, and the base types, mod wordings, trade-site stat ids and pseudo-total rules in `gamedata.json`, from its data files under its license; and the ideas (2.113.0) of counting each seller once and keeping a mod's Min within its tier, written our own way.
- **[Sidekick](https://github.com/Sidekick-Poe/Sidekick)**: general ideas. None of its code is used.
- **[hypr-exiled](https://github.com/gfsd3v/hypr-exiled)** (gfsd3v): the idea for the Trade Whisper Watcher, built from scratch here; none of its code is used.
- **[Path of Building PoE2](https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2)**: the anoint recipes.
- **[poe2pricer](https://github.com/saxe78/poe2pricer)** (saxe78): the idea for Favours prices (finding the Ritual window by a piece of its own art, its rewards by their pictures). Written from scratch here; none of its code is used.
- **gruvbox** by Pavel Pertsev (morhetz), MIT: the colors of the Gruvbox Dark and Gruvbox Light themes ([github](https://github.com/morhetz/gruvbox)).
- **NeverSink and Ryonnen** (reddit): the game's hidden setting that applies your item filter to the Ritual window (`apply_item_filter_to_ritual`), which Filter in the Ritual window walks you through ([NeverSink's video](https://www.youtube.com/watch?v=6hiQtcQhB3k)).
- **[PoE Ancients Price Helper](https://github.com/pedro-quiterio/PoeAncientsPriceHelper)** (Pedro Quitério): the idea for the Expedition Remnant Price Checker. None of its code is used.
- **[Path of Exile 2 Wiki](https://www.poe2wiki.net/wiki/Guide:Acts_quick_guide)** (poe2wiki.net editors): the Campaign Helper's Rush (carry) route follows the order and essentials of its Guide:Acts quick guide, rewritten here from the carrier's side.
- **Fonts of the ornate overlay styles** (SIL Open Font License 1.1, licenses in `soe2/fonts`): **[Cinzel](https://github.com/NDISCOVER/Cinzel)** (Natanael Gama), **[EB Garamond](https://github.com/octaviopardo/EBGaramond12)** (Georg Duffner, Octavio Pardo), **[Cormorant](https://github.com/CatharsisFonts/Cormorant)** (Christian Thalmann) **[Marcellus and Marcellus SC](https://github.com/google/fonts/tree/main/ofl/marcellussc)** (Brian J. Bonislawsky, Astigmatic), **[Metamorphous](https://github.com/google/fonts/tree/main/ofl/metamorphous)** (Sorkin Type) and **[IM FELL English SC](https://github.com/google/fonts/tree/main/ofl/imfellenglishsc)** (Igino Marini). Cinzel, EB Garamond and Cormorant were converted to TTF from [Fontsource](https://github.com/fontsource/fontsource)'s Latin files.

## License

The code is free software under the **GNU Affero General Public License v3.0** ([LICENSE](LICENSE)): you can use it, change it and share it. Anything made from it has to stay under the same license, with its source - and that includes a changed version people use over a network (a website or an online service), not only one you hand out. Versions up to 2.129.4 were released under the GNU GPL v3.0.

Game data in `regexdata.json`, `searchdata.json`, `tabs.txt`, `jewels.txt` and `tierdata.json` comes from [RePoE](https://github.com/repoe-fork/repoe-fork); `gamedata.json` (base types, mod wordings, trade-site stat ids, pseudo-total rules) is built from [Exiled Exchange 2](https://github.com/Kvan7/Exiled-Exchange-2)'s data files (MIT) (anoint recipes in `anointdata.json`: [Path of Building PoE2](https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2)) and belongs to Grinding Gear Games; it isn't covered by this license. Other sources and their licenses are in [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

This product isn't affiliated with or endorsed by Grinding Gear Games in any way. Path of Exile 2 is a trademark of Grinding Gear Games.
