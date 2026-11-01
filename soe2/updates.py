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


UPDATE_NAME = "StashOfExile2_update.exe"
NO_WINDOW = 0x08000000                              # CREATE_NO_WINDOW


def clean_env():
    """For starting another copy of the one-file exe: it must unpack fresh, not reuse this copy's folder."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("_PYI_", "_MEIPASS"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def finish_update(old, me=None, tries=240, wait=0.5, run=None, popen=None, sleep=None):
    """2.29.1: the swap, done by the NEW exe itself - started as  StashOfExile2_update.exe --finish-update <old exe>.
    It has no window and runs no console commands (2.26.3's .bat waited with ping, and started detached every ping
    and move opened a console window of its own). It waits for the old exe to close, copies itself over it, starts
    it, and ends; the started app deletes StashOfExile2_update.exe. After 15 s it ends what's left of the old exe
    (a helper's inner process could keep the file in use); after 2 minutes it gives up, writes why to
    update_log.txt and starts the new version from where it is, so you still get it. -> 0 done / 1 gave up."""
    import shutil
    import subprocess
    import time
    me = me or sys.executable
    run, popen, sleep = run or subprocess.run, popen or subprocess.Popen, sleep or time.sleep
    image = os.path.basename(old)
    for i in range(tries):
        try:
            shutil.copyfile(me, old)
            break
        except OSError:
            if i == int(15 / wait) and image.lower() != os.path.basename(me).lower() and sys.platform == "win32":
                try:
                    run(["taskkill", "/f", "/t", "/im", image], capture_output=True, timeout=10, creationflags=NO_WINDOW)
                except Exception:
                    pass
            sleep(wait)
    else:
        try:
            with open(os.path.join(os.path.dirname(old), "update_log.txt"), "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} the update could not replace {old} (still in use) - "
                        f"running the new version from {me}\n")
        except OSError:
            pass
        popen([me], env=clean_env(), close_fds=True)
        return 1
    popen([old], env=clean_env(), close_fds=True)
    return 0


def cleanup_update(app_dir, me=None, tries=20, sleep=None):
    """At start-up: remove what an update left behind (the downloaded exe once it's been copied, and 2.26.3's
    StashOfExile2_update.bat). The finishing copy may still be closing, so it tries for a few seconds."""
    import time
    me = os.path.abspath(me or sys.executable)
    sleep = sleep or time.sleep
    left = [os.path.join(app_dir, n) for n in (UPDATE_NAME, "StashOfExile2_update.bat")]
    left = [p for p in left if os.path.exists(p) and os.path.abspath(p) != me]
    for _ in range(tries):
        for p in list(left):
            try:
                os.remove(p)
                left.remove(p)
            except OSError:
                pass
        if not left:
            return True
        sleep(0.5)
    return False
