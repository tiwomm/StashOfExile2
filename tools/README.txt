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

tools/check_items.py (2.121.0) reads every base type and unique in gamedata.json as a copied item - its base, class
and a search the trade site takes (unidentified uniques too). Run it after rebuilding gamedata.json:

  py tools/check_items.py           (prints what failed; exits 1 if anything did)

Bases and uniques newer than gamedata.json don't need a rebuild to work: the app downloads the trade site's own item
list once a day (trade_items.json in the data folder) and uses it where the game data has nothing.

Checks a release runs (each exits 1 and lists what to fix):

  py tools/check_names.py      one name per feature: page names from soe2/names.py, in Title Case; no old names
  py tools/check_removed.py    a removed feature leaves no text, setting or test behind (REMOVED lists them;
                               add --tests path\to\tests to look at the tests too)
  py tools/check_ux.py         opens every page in an empty data folder (offline): one orange button and one BETA
                               chip per screen; lists icon buttons without a tip, list pages whose search box isn't
                               first, and buttons that are on with nothing picked (UX round 2)
