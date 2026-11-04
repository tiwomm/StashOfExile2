# Linux / Hyprland (player-built)

> **GGG ToS safety check - read first.** One key press = one action, only when you press it · nothing acts in the game by itself (watchers only look and show) · never touch the game's memory, code or traffic · the mouse is never moved or clicked for you · it reads only your clipboard, Client.txt, screen pixels, the trade site (within its limits) and poe.ninja. Every change must pass all of [TOS.md](../TOS.md) (`tools/check_tos.py` checks the code on every PR).

StashOfExile2's releases are Windows-only. Since 2.10.0 the code has a start on Linux support so anyone can package it themselves. The project doesn't build or test Linux itself; a player builds every release from source with `build_linux.sh` on Arch + Hyprland (Wayland, XWayland Tk) and uses it daily - that is where the "tested" below comes from.

## What exists

| Piece | File | Status |
|---|---|---|
| Hyprland IPC (active window, clients, game rect) over the socket, no `hyprctl` spawns | `soe2/linsys.py` | written, unit-tested without Hyprland |
| Game found by class `steam_app_2694490` or title "Path of Exile 2" | `soe2/linsys.py` | written |
| Client.txt found in every Steam library (`libraryfolders.vdf`, native / `~/.steam` / Flatpak) | `soe2/linsys.py`, `soe2/gamelog.py` | written |
| "Only while the game is in front" for the timer, notes, Breach banner | `soe2/overlaywin.py` | uses Hyprland when present, else always shows |
| Window class `Stashofexile2` for window rules | `soe2/app.py` (`tk.Tk(className=...)`) | done |
| Updater never downloads an `.exe` off Windows | `soe2/updates.py` | done |
| Window rules | `linux/hyprland.conf`, `linux/hyprland.lua` | written |
| Build script | `build_linux.sh` | tested by a player on Arch + Hyprland, Python 3.12+, for every release 2.20 - 2.89.1: a venv with `pyinstaller requests pillow pystray`, Tk with Xft, `PATH` pointing at the venv -> a ~136 MB onefile `dist/StashOfExile2` that runs on Hyprland |
| Desk windows, the What's new card and the Toolkit menu inside the app's window (InDesk: they move, hide and change workspace with the app; `SOE2_REAL_WINDOWS=1` turns it off) | `soe2/shell.py` | tested by a player in daily use on Hyprland (as their own patch, 2.20 - 2.89.1); in the app from 2.91.1 |

## Still Windows-only

- Global hotkeys and Ctrl+Alt+C detection (`winsys.KeyWatch`, a Windows keyboard hook). Plan: a Hyprland `bindn` pass-through bind that writes to a local socket the app listens on, plus `wl-paste --watch` for the clipboard.
- Chat command keys (`SendInput`). Plan: `wtype`.
- Delirium alert screen reads (`mss`). Plan: `grim -g "x,y wxh"` with the rect from `linsys.game_rect()`.
- `winsound` beeps (fall back to the Tk bell).

## Fonts

Tk must be built with Xft. Map the Windows fonts in fontconfig, e.g. `Segoe UI` → `Liberation Sans`, `Segoe UI Emoji` → `Noto Color Emoji`, or text silently falls back to a bitmap font.

## Run from source

```
python3 -m venv .venv && . .venv/bin/activate
pip install requests pillow pystray
python stashofexile2.py
```
