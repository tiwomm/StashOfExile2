# Linux / Hyprland (player-built)

> **GGG ToS safety check - read first.** One key press = one action, only when you press it · nothing acts in the game by itself (watchers only look and show) · never touch the game's memory, code or traffic · the mouse is never moved or clicked for you · it reads only your clipboard, Client.txt, screen pixels, the trade site (within its limits) and poe.ninja. Every change must pass all of [TOS.md](../TOS.md) (`tools/check_tos.py` checks the code on every PR).

StashOfExile2's releases are Windows-only. Since 2.10.0 the code has a start on Linux support so anyone can package it themselves. The project doesn't build or test Linux itself; a player builds every release from source with `build_linux.sh` on Arch + Hyprland (Wayland, XWayland Tk) and uses it daily - that is where the "tested" below comes from.

**Build from the `linux` branch.** It is `main` plus the Linux fixes below (InDesk windows, clipboard reads, exact game-window match), kept in step with each release. Same version number as the `main` release it follows.

## What exists

| Piece | File | Status |
|---|---|---|
| Hyprland IPC (active window, clients, game rect) over the socket, no `hyprctl` spawns | `soe2/linsys.py` | written, unit-tested without Hyprland |
| Game found by class `steam_app_2694490` or a window titled exactly "Path of Exile 2" (like Windows since 2.88.3 - a browser tab "... Path of Exile 2 ..." isn't the game) | `soe2/linsys.py` | tested by a player |
| Client.txt found in every Steam library (`libraryfolders.vdf`, native / `~/.steam` / Flatpak) | `soe2/linsys.py`, `soe2/gamelog.py` | written |
| "Only while the game is in front" for the timer, notes, Breach banner | `soe2/overlaywin.py` | uses Hyprland when present, else always shows |
| Window class `Stashofexile2` for window rules | `soe2/app.py` (`tk.Tk(className=...)`) | done |
| Updater never downloads an `.exe` off Windows | `soe2/updates.py` | done |
| Window rules | `linux/hyprland.conf`, `linux/hyprland.lua` | `hyprland.lua` tested by a player |
| Clipboard reads (`clipboard.read_clipboard_text`) use Tk's clipboard off Windows - Money Makers › Check my tablet read nothing before | `soe2/clipboard.py` | tested by a player |
| Price checks from Ctrl+C / Ctrl+Alt+C copies (clipboard path), Wealth › Sync stash tabs (trade site) | - | tested by a player (one tab: 368 items read) |
| Build script | `build_linux.sh` | tested by a player on Arch + Hyprland, Python 3.12+, for every release 2.20 - 2.101.0: a venv with `pyinstaller requests pillow pystray`, Tk with Xft, `PATH` pointing at the venv -> a ~136 MB onefile `dist/StashOfExile2` that runs on Hyprland |
| Desk windows, the What's new card and the Toolkit menu inside the app's window (InDesk: they move, hide and change workspace with the app; `SOE2_REAL_WINDOWS=1` turns it off) | `soe2/shell.py` | tested by a player in daily use on Hyprland (as their own patch, 2.20 - 2.101.0) |
| Screen text (OCR) for the Expedition Remnant Price Checker, Island Rumours and Well of Souls: Tesseract instead of Windows' OCR, the picture from `grim` on Wayland (`mss` on X11). Needs `tesseract` + English data and `grim` installed | `soe2/remnant.py` (`ocr_linux`, `grab_wayland`) | written, tested here on drawn game-style pictures only - not in the game yet |

## Still Windows-only

- Global hotkeys and Ctrl+Alt+C detection (`winsys.KeyWatch`, a Windows keyboard hook). Plan: a Hyprland `bindn` pass-through bind that writes to a local socket the app listens on, plus `wl-paste --watch` for the clipboard.
- Chat command keys (`SendInput`). Plan: `wtype`.
- Delirium alert screen reads (`mss`). Plan: `grim -g "x,y wxh"` with the rect from `linsys.game_rect()`.
- `winsound` beeps (fall back to the Tk bell).
- The Remnant key (Ctrl+Alt+R) needs the Windows key hook - on Linux use the Remnant's Auto mode.
- Leaving our own tags out of screen pictures (`WDA_EXCLUDEFROMCAPTURE`) is Windows-only: on Linux an OCR read can also see the app's tags if they sit inside the read area.
- Wealth › Scan stash (2.102.0) reads the screen with `mss` - untested on Linux; under Wayland it likely needs `grim` like the Delirium reads.

## Known issues

- **Game in fullscreen** (Proton through XWayland): clicking an app window over the game also clicks the game - the game holds the pointer. Run the game windowed (the compositor can still make it fill the screen).
- **Copying from a Wayland app:** XWayland hands the Wayland clipboard to X11 apps when an X11 window gets focus, so the app sees it once it is clicked. Copies made in the game (XWayland) are seen at once.

## Fonts

Tk must be built with Xft. The code asks for Windows fonts by name (Segoe UI and its Semibold / Light / Black, Tahoma, Consolas, Lucida Console) and Tk's own default is `sans-serif`; unmapped, text falls back to whatever fontconfig picks, or a bitmap font. Mapping them system-wide changes every other app that asks for them too (web pages using Segoe UI), so scope it to the app: a fonts.conf that includes the system one and maps those names, read only by the app through `FONTCONFIG_FILE` in its launcher (tested by a player):

```xml
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
 <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
 <!-- one per name: Segoe UI, Segoe UI Semibold, Segoe UI Light, Segoe UI Black, Tahoma, Consolas, Lucida Console, sans-serif -->
 <match target="pattern"><test name="family" qual="any"><string>Segoe UI</string></test>
  <edit name="family" mode="assign" binding="strong"><string>Liberation Sans</string></edit></match>
</fontconfig>
```

```sh
#!/bin/sh
FONTCONFIG_FILE="$HOME/.stashofexile2/fontconfig/fonts.conf" exec /path/to/StashOfExile2 "$@"
```

Emoji and symbol fonts (`Segoe UI Emoji` → `Noto Color Emoji`, `Segoe UI Symbol`) can be left to fontconfig's own fallback.

## Run from source

```
# system: tesseract + English data, grim (Wayland screen pictures)
#   Arch: sudo pacman -S tesseract tesseract-data-eng grim
#   Debian/Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-eng grim
python3 -m venv .venv && . .venv/bin/activate
pip install requests pillow pystray numpy mss
python stashofexile2.py
```

OCR without the game in front: `python -c "from soe2 import remnant; print(remnant.selftest())"` should print `Orb of Alchemy x3`. `SOE2_TESS_PSM=6` tries Tesseract's one-block mode if lines come out split.
