# StashOfExile2 roadmap

Where things stand at **2.0.0**, and what comes next. Main features are stable. Labs features are experimental: they're marked BETA and only show when Settings > General > Labs is on.

## Done in the 2.0 betas

- **The app as a desktop.** Every tool is a real window, with a dock (or desktop icons, or both), a Toolkit menu and a taskbar with a clock. Settings has General, Appearance, Hotkeys and Advanced tabs.
- **Price checks** for tablets, jewels and waystones.
  - Tablets and jewels are priced on the mods that matter.
  - Waystones are priced on their endgame numbers (Waystone Drop Chance, Pack Size, Item Rarity, Monster Rarity, Monster Effectiveness).
  - Other gear is priced as a rough guess.
  - Selected items can be deleted, with undo.
- **Mod book.** It learns what mods are worth from real listings, and holds your tablet and jewel mod rules. Regex shows the same ratings with ★.
- **Regex.** Stash search strings for tablets, waystones and relics.
- **Utilities:**
  - chat command keys;
  - a sticky note and the session timer, both shown over the game only while it's in front;
  - the Delirium alert;
  - one list of hotkeys, set by pressing the key or a mouse button.
- **Tools:** Exchange rates, Calculator, Under the hood (how an item is read).
- **Labs:** Wealth, the Session tracker and Game search.
- **Look:** themes, accent colours and text size for the whole app, plus a start-up screen.
- **Licensing and polish:**
  - all game data comes from RePoE;
  - the icons are original;
  - a what's-new card once per version;
  - optional update checks.

## Next

1. **Testing on Windows.** Check window focus and typing, the mouse-button hotkeys, minimising and the tray, and waystone prices against real listings.
2. **Wealth (Labs) usability:**
   - a guided first setup: count currency, then add a synced tab step by step with a check that the price marker is right;
   - totals, the breakdown and snapshots that explain themselves (the "How it works" guide is the first step);
   - clearer price overrides;
   - moving it out of Labs once it holds up.
3. **Mod book for waystones and relics.** Rule lists for their mods (today they can only be rated from Regex with a right-click).
4. **Session tracker (Labs).** Check the death and AFK lines against real Client.txt logs, and refine how maps are counted.
5. **One-key copy.** Make it reliable on every keyboard and mouse, or keep it as an experiment. Ctrl+Alt+C stays the default and can't be changed.
6. **Labs graduation.** Decide what Wealth, the Session tracker and Game search each need before they lose the BETA tag.
7. **Publish 2.0 on GitHub** as a release, so people on 1.28 update straight to it. After that: 2.0.x for fixes, 2.1 for the next features.

## Rules this project keeps

- **One action per key press.** Nothing is automated in the game.
- **No game memory, no packet reading.** The app only reads:
  - your clipboard (item copies);
  - the game's own log file (session tracker);
  - your screen (Delirium alert).
- **Trade site limits respected.** No automatic syncing; price checks queue behind the rate limits.
- **No copied art or data.** Game data comes from RePoE (see THIRD_PARTY_NOTICES.txt), and every icon is drawn for this app.
