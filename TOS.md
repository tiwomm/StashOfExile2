# GGG Terms of Service (ToS) safety check

**Read this first, before any change, plan or release.** Every guide in this project (README, ROADMAP, the handovers,
`strats/`, `board/`, `linux/`) starts with a short copy of this check and points here.

Grinding Gear Games doesn't approve or certify third-party tools. Their support answer is that they "cannot comment on
the legality of third-party tools". So StashOfExile2 stays well inside the rules GGG staff *have* stated, as
collected in the forum guide [What a macro is allowed to do in Path of Exile](https://www.pathofexile.com/forum/view-thread/2077975):
one action per key press, nothing automated, nothing that moves the cursor or clicks for you, whatever tool sends it.
GGG's [Terms of Use](https://www.pathofexile.com/legal/terms-of-use-and-privacy-policy) (checked Nov 2026), clause 7,
forbid without written approval: modifying the game client or its data, including through third-party tools (7.2);
automated software or bots (7.3); connecting to their servers with anything but the game client (7.5); data
extraction tools on their website (7.6); reverse engineering (7.9). Clause 22: never try to get around the website
API's limits.

## The check (every feature must pass all of these)

1. **One key press = one action, and only when you press it.** No macro does two things, rotates, repeats, or fires on
   a timer or a game event (life, mana, flasks, logout ...).
2. **Nothing acts in the game by itself.** Watchers (Delirium, Breach, Ritual, Expedition Remnant Price Checker) only
   *look and show*: a banner, a sound, a price tag. They never press, click, type or send anything.
3. **Never touch the game client.** No reading or writing its memory, no injecting code, no hooking its graphics, no
   reading or changing its network traffic.
4. **The app's only input to the game:** after *your* key press, one game action - the game's own item copy
   (Ctrl+Alt+C), or one chat command (pasted, one Enter). The mouse is never moved or clicked for you.
5. **What the app reads:** your clipboard, the game's own log file (Client.txt), and pixels of your screen (a
   screenshot, the same as any capture tool). Plus public websites: the official trade site's search API, only for
   searches you started (a copied item, a sync you pressed), always inside the limits it sends back (clause 22) -
   never automated buying, whispers or listing, never scraping its pages - and poe.ninja.
   The app never connects to the game's servers (7.5) and never changes the game client or its files (7.2).
6. **Overlays are just windows on top.** Click-through where they sit over the game, they never change what the game
   draws or does, and they're left out of screen captures where Windows allows it.
7. **When in doubt, leave it out** - or make it a manual, one-press action, and ask before shipping it.

## How it's enforced

- `tools/check_tos.py` runs on every pull request (`.github/workflows/checks.yml`) and in the test suite. It fails on:
  game-memory / process APIs (ReadProcessMemory, WriteProcessMemory, OpenProcess, VirtualAllocEx, CreateRemoteThread
  ...), mouse movement or clicks (SetCursorPos, mouse_event, mouse SendInput), packet tools (pydivert, scapy, pcap),
  input-automation libraries (pyautogui, pynput, keyboard, AutoHotkey), SendInput anywhere but `soe2/overlay.py`, and
  a screen watcher that can send keys.
- Every screen watcher's module notes say what it reads and that it sends nothing.
