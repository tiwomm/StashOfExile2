# StashOfExile2 roadmap

**Current version: 2.26.0**

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

## ▶ Next up

| Version | Plan |
|---|---|
| 2.27.0 | Money Makers: farming guides, tablet crafting reference, run tracker. Each strat gets a difficulty rating in **Thoughts per Click** (fewer = easier) and **Clicks per hour**, so you can sort and filter strats by effort. |
| 2.28.0 | Map library with ranks, import / export. |
| Later | Sidekick / Exiled Exchange-style pricing for more item types; public stash order test tool; Ancients price helper; Linux build. |

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
