# Linux / Hyprland (groundwork, untested)

StashOfExile2's releases are Windows-only. Since 2.10.0 the code has a start on Linux support so anyone can package it themselves. Nothing here is built or tested by the project yet.

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
| Build script | `build_linux.sh` | written, never run |

## Still Windows-only

- Global hotkeys and Ctrl+Alt+C detection (`winsys.KeyWatch`, a Windows keyboard hook). Plan: a Hyprland `bindn` pass-through bind that writes to a local socket the app listens on, plus `wl-paste --watch` for the clipboard.
- Chat command keys (`SendInput`). Plan: `wtype`.
- Delirium alert screen reads (`mss`). Plan: `grim -g "x,y wxh"` with the rect from `linsys.game_rect()`.
- Window owner tricks in `shell.py` (no-ops elsewhere) and `winsound` beeps (fall back to the Tk bell).

## Fonts

Tk must be built with Xft. Map the Windows fonts in fontconfig, e.g. `Segoe UI` → `Liberation Sans`, `Segoe UI Emoji` → `Noto Color Emoji`, or text silently falls back to a bitmap font.

## Run from source

```
python3 -m venv .venv && . .venv/bin/activate
pip install requests pillow pystray
python stashofexile2.py
```
