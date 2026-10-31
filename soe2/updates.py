"""Checking GitHub Releases for a new version and downloading it.

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import os
import re
import requests
import sys


# ------------------------------------------------------------------ updates (GitHub Releases)
REPO = "tiwomm/StashOfExile2"


RELEASE_URL = f"https://api.github.com/repos/{REPO}/releases/latest"


FROZEN = bool(getattr(sys, "frozen", False))       # True when running as the built .exe


_VER = re.compile(r"^\s*[vV]?\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?\s*[-_. ]?\s*"
                  r"(?:(alpha|beta|rc|pre|a|b)\s*[-_. ]?\s*(\d*))?", re.I)
_PRE_RANK = {"alpha": 0, "a": 0, "pre": 0, "beta": 1, "b": 1, "rc": 2}


def vtuple(text):
    """A version you can compare: '1.28' < '2.0.0-beta.3' < '2.0.0-beta.10' < '2.0.0-rc.1' < '2.0.0' < '2.0.1'.
    A beta sorts before the release it leads to. 2.0.0 (beta 23): every way a tag may be written is read the same -
    'v2.0.0-beta.17', '2.0-beta17', '2.0 beta 17', 'v2.0b17' - the old reader took the 17 of '2.0b17' as the patch
    number (2.0.17), so an old beta looked newer than beta 22."""
    m = _VER.match(str(text))
    if not m:
        return (0, 0, 0, 9, 0)
    nums = tuple(int(m.group(i) or 0) for i in (1, 2, 3))
    if m.group(4):
        return nums + (_PRE_RANK[m.group(4).lower()], int(m.group(5) or 0))
    return nums + (9, 0)


def is_newer(tag, current):
    """Only ever offer a version that is really newer than the one running (never go backwards)."""
    return vtuple(tag) > vtuple(current)


def pick_asset(rel, frozen=None):
    """The file to download from a release: the .exe when we are an exe, else a .py (or the .exe if none)."""
    frozen = FROZEN if frozen is None else frozen
    assets = [a for a in rel.get("assets", []) if a.get("browser_download_url", "").startswith(f"https://github.com/{REPO}/")]
    exe = [a for a in assets if a.get("name", "").lower().endswith(".exe")]
    if sys.platform != "win32":                      # 2.10.0: never an .exe on Linux / macOS
        exe = []
    exe.sort(key=lambda a: not a.get("name", "").lower().startswith("stashofexile2"))   # 2.0: not the Delirium helper
    py = [a for a in assets if a.get("name", "").lower().endswith(".py")]
    kit = [a for a in assets if a.get("name", "").lower().endswith(".zip")]
    order = exe + kit + py if frozen else kit + exe + py
    return order[0] if order else None


def latest_release():
    """-> ("ok", release dict) / ("none", msg) / ("error", msg). One small public request; nothing is sent about you."""
    try:
        r = requests.get(RELEASE_URL, headers={"Accept": "application/vnd.github+json", "User-Agent": "StashOfExile2-update-check"}, timeout=20)
    except Exception as e:
        return "error", f"Could not reach GitHub ({e}). Check your internet."
    if r.status_code == 404:
        return "none", "No release has been published yet."
    if r.status_code != 200:
        return "error", f"GitHub answered {r.status_code}."
    try:
        return "ok", r.json()
    except Exception:
        return "error", "GitHub's answer could not be read."


def download_asset(asset, dest, progress=None):
    """Download to dest, verify size, 'MZ' exe header and GitHub's sha256 checksum. -> (ok, message, verified)"""
    import hashlib
    url = asset["browser_download_url"]
    if not url.startswith(f"https://github.com/{REPO}/"):
        return False, "The download address is not from the project's GitHub page.", False
    h, got = hashlib.sha256(), 0
    try:
        with requests.get(url, headers={"User-Agent": "StashOfExile2-update-check"}, stream=True, timeout=30) as r:
            if r.status_code != 200:
                return False, f"Download failed (GitHub answered {r.status_code}).", False
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
                    h.update(chunk)
                    got += len(chunk)
                    if progress:
                        progress(got, asset.get("size", 0))
    except Exception as e:
        return False, f"Download failed: {e}", False
    bad = None
    if asset.get("size") and got != asset["size"]:
        bad = f"incomplete download ({got} of {asset['size']} bytes)"
    digest = str(asset.get("digest") or "")
    verified = digest.lower().startswith("sha256:")
    if not bad and verified and digest.split(":", 1)[1].lower() != h.hexdigest():
        bad = "the file does not match GitHub's checksum"
    if not bad and dest.lower().endswith(".exe"):
        with open(dest, "rb") as f:
            if f.read(2) != b"MZ":
                bad = "it is not a Windows program"
    if bad:
        try:
            os.remove(dest)
        except OSError:
            pass
        return False, f"The downloaded file was rejected: {bad}.", False
    return True, "ok", verified


SWAP_BAT = """@echo off
set "OLD={old}"
set "NEW={new}"
set /a n=0
:wait
set /a n+=1
if %n% gtr 90 exit /b 1
timeout /t 1 /nobreak >nul
move /y "%NEW%" "%OLD%" >nul 2>&1
if errorlevel 1 goto wait
start "" "%OLD%"
(goto) 2>nul & del "%~f0"
"""
