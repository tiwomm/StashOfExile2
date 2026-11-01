#!/usr/bin/env bash
# Linux build (UNTESTED groundwork, 2.10.0). The official releases are Windows-only; see linux/README.md.
# Needs: python3 with Tk built with Xft (fonts), pip install pyinstaller requests pillow pystray
set -euo pipefail
cd "$(dirname "$0")"
python3 -c "import tkinter; r=tkinter.Tk(); r.withdraw(); print('Tk', tkinter.TkVersion)" >/dev/null
python3 -m PyInstaller --noconfirm --onefile --name StashOfExile2 \
  --add-data "gamedata.json:." --add-data "searchdata.json:." --add-data "anointdata.json:." --add-data "cxnames.json:." --add-data "moneymakers.json:." --add-data "mapdata.json:." --add-data "regexdata.json:." \
  --add-data "default_rules.json:." --add-data "jewels.txt:." --add-data "tabs.txt:." \
  --add-data "soe2/templates:soe2/templates" --add-data "soe2/ritual_glyphs.json:soe2" \
  --hidden-import PIL._tkinter_finder --exclude-module pystray._win32 \
  stashofexile2.py
tar -C dist -czf dist/StashOfExile2-linux.tar.gz StashOfExile2
echo "Built dist/StashOfExile2-linux.tar.gz"
