tools/build_gamedata.py rebuilds gamedata.json (the Item library: base types, base groups, modifier stats).
You only need it after a game patch, when Exiled Exchange 2 has published updated data.

  1. Get Exiled Exchange 2:   git clone --depth 1 https://github.com/Kvan7/Exiled-Exchange-2.git
  2. Next to the launcher:    py tools/build_gamedata.py path\to\Exiled-Exchange-2 gamedata.json
  3. In tools/build_gamedata.py raise GAMEDATA_VERSION by 1, and in soe2/config.py raise "gamedata.json" in
     BUNDLED_DATA to the same number, so the new file replaces the old one in everyone's data folder.
  4. Build the exe as usual (build_exe.bat).

tools/build_regexdata.py rebuilds regexdata.json (the Regex page: tablet, waystone and relic mods and their search
tokens). After a game patch, once RePoE has published updated data:

  1. Get RePoE's PoE 2 data:  git clone --depth 1 https://github.com/repoe-fork/poe2 repoe2
  2. Next to the launcher:    py tools/build_regexdata.py repoe2\data\mods.json regexdata.json
  3. In soe2/config.py raise "regexdata.json" in BUNDLED_DATA by 1, then build the exe as usual.
