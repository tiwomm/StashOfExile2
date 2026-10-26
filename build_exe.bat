@echo off
rem Builds StashOfExile2.exe from stashofexile2.py + the soe2 folder (keep them together). Double-click this file (needs Python installed from python.org, "py" launcher ticked).
rem 2.0 beta 7: one exe. The Delirium alert is built in (it runs as StashOfExile2.exe --delirium, started by the app).
cd /d "%~dp0"
echo Installing the build tools (first time only - OpenCV is big, this can take a few minutes)...
py -m pip install --upgrade requests pystray pillow pyinstaller mss numpy opencv-python-headless
if errorlevel 1 goto fail
echo Building StashOfExile2.exe - this takes a few minutes...
py -m PyInstaller --noconfirm --clean --onefile --windowed --name StashOfExile2 --icon stashofexile2.ico --collect-submodules soe2 ^
  --add-data "tabs.txt;." --add-data "jewels.txt;." --add-data "gamedata.json;." --add-data "regexdata.json;." --add-data "default_rules.json;." --add-data "searchdata.json;." --add-data "stashofexile2.ico;." ^
  --add-data "soe2\templates;soe2\templates" --hidden-import pystray._win32 --hidden-import PIL._tkinter_finder ^
  --hidden-import cv2 --hidden-import mss --hidden-import numpy stashofexile2.py
if errorlevel 1 goto fail

echo.
echo DONE. Your program is in:  %~dp0dist\StashOfExile2.exe
echo Give people that one file. The app makes its own data folder in %%APPDATA%%\StashOfExile2 on first start.
pause
exit /b 0
:fail
echo.
echo Something went wrong - scroll up for the red/error lines to see what failed.
pause
exit /b 1
