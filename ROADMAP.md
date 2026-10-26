# StashOfExile2 roadmap

**Current version: 2.3.0**

Releases are numbered 2.x for new features and 2.x.y for fixes. Each step below is one release; we work through them top to bottom.

## ✅ Done

| Version | What it brought |
|---|---|
| 2.0 | The app as a desktop with windows, dock and taskbar. Price checks for tablets, jewels and waystones. Mod book, Regex, chat keys, sticky note, Delirium alert. Themes and a start-up screen. Updates that never go backwards. |
| 2.1 | Map stats with per-map leaderboards (Session tracker). Top value (Labs). Clock follows Windows' 12 / 24-hour setting. |
| 2.2 | Regex key: one key in game copies your stash search. Currency Exchange helper (whole-number ratios to post). CSV export for map runs, sessions and Wealth. |
| 2.3 | Windows check-up done. Wealth, step by step: a guided first setup, "up X since yesterday", snapshots you can compare, your own prices marked. Rough prices for jewels and tablets instead of "check by hand"; no freeze when deleting many price checks; a problem report. |

## ▶ Next up

| Version | Plan | Why |
|---|---|---|
| 2.4 | **Waystone & relic mods in the Mod book.** Rate their mods like tablet mods; Regex and Top value pick it up. | Today they can only be rated from Regex with a right-click. |
| 2.5 | **Session tracker polish.** Deaths and time away from keyboard checked against real Client.txt logs; daily maps chart. | The death / AFK lines haven't been confirmed for PoE2 yet. |
| 2.6 | **Leaving Labs.** Decide what Wealth, the Session tracker, Game search and Top value each need to drop the BETA tag, and do it. | |

## 💤 Parked (not planned unless something changes)

- **One-key copy:** stays an experiment; Ctrl+Alt+C is the reliable way.
- **Automatic loot logging, auto-syncing stash tabs:** too intrusive / too many trade-site requests.
- **Gold from selling in the Session tracker:** no reliable way to count it.
- **One-click price note, "worth listing vs vendor" split, price history charts, map stats by waystone mod:** good ideas, not needed right now.

## Rules this project keeps

- **One action per key press.** Nothing is automated in the game.
- **Only reads what's yours to read.** No game memory or packets; only your clipboard, the game's own log file and your own screen.
- **Respects the trade site.** Its limits are respected and nothing syncs on a timer.
- **No copied art or data.** All game data comes from RePoE, and the icons are original.
