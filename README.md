# StashOfExile2

A Windows toolkit for **Path of Exile 2** that runs next to the game. Its main job is pricing simple items in bulk: **tablets, jewels and waystones**.

Hover an item in game and press **Ctrl+Alt+C**. It goes into a list and is priced from the official trade site, using the mods that decide its price.

> **Written by AI.** This project's code, data tools and text were written by Claude (an AI made by Anthropic), directed and tested by a human who plays the game. It's shared openly so anyone can read it, check it, change it and use it.

## What it does

- **Price checks:** bulk pricing for tablets, jewels and waystones, with a confidence rating and filters per item. Other gear gets a rough guess only.
- **Mod book:** learns which mods are worth money from the listings it sees.
- **Money Makers:** community farming strats in one layout, rated by Thoughts per Click and Clicks per hour, updated from GitHub; add and share your own; simple run tracker. Strat format: [strats/README.md](strats/README.md).
- **Regex:** builds stash-search strings for tablets, waystones, relics, jewels and gear (at least, ranges, at most), with saved Favorites.
- **Exchange rates:** poe.ninja rates, an Exchange Helper, and an Arbitrage tab for uneven Currency Exchange rates.
- **Session tracker:** time, maps and deaths per session with a timer over the game, plus Delirium, Breach (Hiveblood) and Ritual alerts.
- **Utilities:** chat command keys, a sticky note, a calculator.
- **Labs (off by default):** Wealth (stash value over time), Market Insights and an offline game-data search (with every anoint, its Liquid Emotions and their poe.ninja prices).

## Install

Download `StashOfExile2.exe` from [Releases](../../releases) and run it. It can update itself (Settings > General > Updates). Your settings live in `%APPDATA%\StashOfExile2`, so updates never touch them.

**From source** (Windows, Python 3.12 from python.org):

```
py -m pip install requests pystray pillow mss numpy opencv-python-headless
py stashofexile2.py
```

**Linux:** not supported yet. There's untested groundwork for Hyprland in [linux/](linux/README.md) for anyone who wants to package it.

To build the exe yourself, run `build_exe.bat`; it makes `dist\StashOfExile2.exe`. Every version tag pushed here builds the exe automatically and publishes it as a release (`.github/workflows/release.yml`).

## Community

Questions, ideas and bug reports: [Discord](https://discord.gg/Ta8EVnxx4T). The plan is in [ROADMAP.md](ROADMAP.md).

## Fair play

- **One action per key press.** It never plays the game for you.
- **Reads nothing from the game itself:** no memory, no network traffic. Only item text you copy, the game's own `Client.txt` log, and screenshots of your own screen (Delirium alert, Ritual watcher).
- **Respects the trade site's rate limits**, and nothing syncs on its own.

## License

The code is free software under the **GNU General Public License v3.0** ([LICENSE](LICENSE)): you can use it, change it and share it. If you share a changed version, it has to stay under the same license, with its source.

Game data in `gamedata.json`, `regexdata.json` and `searchdata.json` comes from [RePoE](https://github.com/repoe-fork/repoe-fork) (anoint recipes in `anointdata.json`: [Path of Building PoE2](https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2)) and belongs to Grinding Gear Games; it isn't covered by this license. Other sources and their licenses are in [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

This product isn't affiliated with or endorsed by Grinding Gear Games in any way. Path of Exile 2 is a trademark of Grinding Gear Games.
