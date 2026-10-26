# StashOfExile2

A Windows toolkit for **Path of Exile 2** that runs next to the game. Its main job is pricing lots of simpler items quickly: **tablets, jewels and waystones**.

Hover an item in game and press **Ctrl+Alt+C**. The item is added to a list and priced from the official trade site, using the mods (or waystone numbers) that actually decide its price.

## Features

- **Price checks.** Bulk price tablets, jewels and waystones.
  - Mods are rated ★ must-have, ☑ counts, or ignored; you can change that per item.
  - Searches loosen step by step when too few listings match.
  - Each price has a confidence rating, and suggested list prices are given in divines and other currencies.
  - Other gear gets a rough guess only. Check those yourself.
- **Mod book.** Learns what mods are worth from the listings it sees. Your tablet and jewel rules live here.
- **Regex.** Builds stash-search strings for tablets, waystones and relics. ★ marks the mods your Mod book rates valuable.
- **Utilities:** chat command keys (e.g. `/hideout`), a sticky note over the game, and a Delirium "end it now" alert.
- **Tools:** exchange rates (poe.ninja) with an Exchange Helper and Arbitrage, a calculator, and "Under the hood" (how an item is read).
- **Your look:** six themes, accent colours and text size (Settings > Appearance).
- **Labs (experimental, off by default):** Wealth (stash value over time), a session tracker (maps, time, profit), and an offline game-data search.

## Install

- **Download:** get the latest `StashOfExile2.exe` from [Releases](../../releases) and run it. It can update itself (Settings > General > Updates).
- **Build it yourself:** on Windows with Python from python.org (tick the `py` launcher), double-click `build_exe.bat`. It installs the build tools and makes `dist\StashOfExile2.exe`.
- **Run from source:** `py -m pip install requests pystray pillow mss numpy opencv-python-headless`, then `py stashofexile2.py`. Keep the `soe2` folder next to it.

Your settings and data are kept in `%APPDATA%\StashOfExile2` and survive updates.

## Fair play

- **One action per key press.** The app never plays the game for you.
- **Nothing read from the game itself.** The app never reads game memory or network traffic. It only uses:
  - item text you copy;
  - the game's own `Client.txt` log (session tracker);
  - screenshots of your own screen (Delirium alert).
- **Trade site limits respected.** Requests stay within the site's rate limits, and nothing syncs automatically.

## Credits

- **[RePoE](https://github.com/repoe-fork/repoe-fork):** game data.
- **[poe.ninja](https://poe.ninja):** prices.
- **Grinding Gear Games' public [Currency Exchange history](https://www.pathofexile.com/developer/docs):** the Arbitrage tab in Exchange rates (only read when you press Refresh).
- **[Exiled Exchange 2](https://github.com/Kvan7/Exiled-Exchange-2) (MIT):** base types, stat wordings and trade stat ids.

See `THIRD_PARTY_NOTICES.txt` for the full list.

Path of Exile 2 is a trademark of Grinding Gear Games. StashOfExile2 is a fan-made tool, not affiliated with or endorsed by Grinding Gear Games.
