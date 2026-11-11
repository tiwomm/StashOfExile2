"""Screen pictures for the watchers (2.103.0 linux branch): Delirium, Ritual, Scan stash, and remnant.grab (OCR).

Windows and X11: mss, exactly as before. Wayland (Hyprland): mss can't see the screen there, so each picture is ONE
`grim` call for the asked rect in layout coordinates (the ones linsys.game_rect gives), "-s 1" so 1 image pixel = 1
layout pixel at any output scale. Nothing else changes: it only LOOKS at the screen, like a screenshot (TOS.md).

screen() is a drop-in for mss.mss(): .grab({"left", "top", "width", "height"}) -> a shot that numpy reads as BGRA
(np.asarray(shot)), with .size / .width / .height / .rgb; .monitors like mss's (index 0 = all, 1.. = each)."""
import os
import shutil
import subprocess
import sys


def use_grim():
    return sys.platform.startswith("linux") and bool(os.environ.get("WAYLAND_DISPLAY")) and bool(shutil.which("grim"))


def grim_image(left, top, width, height):
    """Wayland: one picture of the rect -> PIL RGB image of exactly width x height, or None."""
    from io import BytesIO
    from PIL import Image
    w, h = max(1, int(width)), max(1, int(height))
    try:
        out = subprocess.run(["grim", "-s", "1", "-t", "ppm", "-g", f"{int(left)},{int(top)} {w}x{h}", "-"],
                             capture_output=True, timeout=5, check=True).stdout
        img = Image.open(BytesIO(out)).convert("RGB")
    except Exception:
        return None
    return img if img.size == (w, h) else img.resize((w, h))


class Shot:
    """The parts of an mss shot the app uses, from a PIL image."""

    def __init__(self, img):
        self.img = img
        self.size = img.size
        self.width, self.height = img.size

    @property
    def rgb(self):
        return self.img.tobytes()

    def __array__(self, dtype=None, copy=None):
        import numpy as np
        a = np.asarray(self.img)                                   # RGB
        bgra = np.empty((a.shape[0], a.shape[1], 4), dtype=np.uint8)
        bgra[..., 0], bgra[..., 1], bgra[..., 2], bgra[..., 3] = a[..., 2], a[..., 1], a[..., 0], 255
        return bgra if dtype is None else bgra.astype(dtype)


def hypr_monitors():
    """Hyprland's monitors in mss's shape (layout coordinates), or []."""
    try:
        from .linsys import hypr
        ms = hypr("j/monitors") or []
    except Exception:
        return []
    out = []
    for m in ms:
        try:
            sc = float(m.get("scale") or 1) or 1
            out.append({"left": int(m["x"]), "top": int(m["y"]),
                        "width": int(round(m["width"] / sc)), "height": int(round(m["height"] / sc))})
        except (KeyError, TypeError, ValueError):
            continue
    if not out:
        return []
    l_, t = min(m["left"] for m in out), min(m["top"] for m in out)
    r, b = max(m["left"] + m["width"] for m in out), max(m["top"] + m["height"] for m in out)
    return [{"left": l_, "top": t, "width": r - l_, "height": b - t}] + out


class Screen:
    def __init__(self):
        self._mss = None
        self._grim = use_grim()
        try:
            import mss
            self._mss = mss.mss() if hasattr(mss, "mss") else mss.MSS()
        except Exception:
            if not self._grim:
                raise

    @property
    def monitors(self):
        if self._grim:
            ms = hypr_monitors()
            if ms:
                return ms
        if self._mss is not None:
            return self._mss.monitors
        return [{"left": 0, "top": 0, "width": 1920, "height": 1080}] * 2

    def grab(self, mon):
        if self._grim:
            img = grim_image(mon["left"], mon["top"], mon["width"], mon["height"])
            if img is not None:
                return Shot(img)
        if self._mss is None:
            raise RuntimeError("no screen picture: grim failed and mss isn't installed")
        return self._mss.grab(mon)

    def close(self):
        if self._mss is not None:
            try:
                self._mss.close()
            except Exception:
                from . import buglog
                buglog.caught()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def screen():
    """Drop-in for mss.mss() (see the module text). Not on Wayland: the plain mss object, as before."""
    if not use_grim():
        import mss
        return mss.mss() if hasattr(mss, "mss") else mss.MSS()
    return Screen()
