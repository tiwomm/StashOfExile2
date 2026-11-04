"""Atlas screenshots for strats (2.78.0): paste one (Ctrl+V) or pick a file in the Strat Tracker's Atlas step.

A picture is shrunk to a small JPEG (at most 1600 px wide, about 300 KB) and kept in the data folder
(strat_images/). A strat names it in "atlas_image": "l:<file>" on this PC; posting the strat to the community board
uploads it first and it becomes "b:<id>" (the board keeps it; anyone's app downloads it once and keeps a copy).
Feedback: "I like the screenshot idea, no planner link - keep immersion in one place"."""
import base64
import io
import os
import re
import uuid

from .config import P

FOLDER = "strat_images"
MAX_W = 1600
MAX_BYTES = 300 * 1024


def folder():
    path = P(FOLDER)
    os.makedirs(path, exist_ok=True)
    return path


def jpeg(img):
    """A PIL image -> JPEG bytes, shrunk until it fits MAX_BYTES."""
    img = img.convert("RGB")
    if img.width > MAX_W:
        img = img.resize((MAX_W, round(img.height * MAX_W / img.width)))
    q = 82
    while True:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True)
        data = buf.getvalue()
        if len(data) <= MAX_BYTES or q <= 35:
            if len(data) > MAX_BYTES:                       # still too big: smaller
                img = img.resize((img.width * 3 // 4, img.height * 3 // 4))
                q = 70
                continue
            return data
        q -= 8


def keep(img):
    """A PIL image -> saved as a strat image. -> "l:<file>"."""
    name = uuid.uuid4().hex[:16] + ".jpg"
    with open(os.path.join(folder(), name), "wb") as f:
        f.write(jpeg(img))
    return "l:" + name


def from_clipboard(grab=None):
    """The picture on the clipboard (a screenshot, or a copied image file). -> "l:<file>" or None."""
    try:
        from PIL import Image, ImageGrab
        got = (grab or ImageGrab.grabclipboard)()
    except Exception:
        return None
    if isinstance(got, list):                            # files copied in Explorer
        for p in got:
            try:
                return keep(Image.open(p))
            except Exception:
                continue
        return None
    if got is None:
        return None
    try:
        return keep(got)
    except Exception:
        return None


def from_file(path):
    try:
        from PIL import Image
        return keep(Image.open(path))
    except Exception:
        return None


def path_of(ref, fetch=None):
    """"l:<file>" / "b:<id>" -> a local file (a board image is downloaded once and kept). None when it can't be had."""
    if not isinstance(ref, str):
        return None
    m = re.fullmatch(r"l:([A-Za-z0-9._-]{1,80})", ref)
    if m:
        p = os.path.join(folder(), m.group(1))
        return p if os.path.isfile(p) else None
    m = re.fullmatch(r"b:([0-9a-f]{32})", ref)               # 2.89.3: an unguessable key
    if not m:
        return None
    p = os.path.join(folder(), f"board_{m.group(1)}.jpg")
    if os.path.isfile(p):
        return p
    from . import board as B
    ok, data = (fetch or B.image)(m.group(1))
    if not ok or not data:
        return None
    with open(p, "wb") as f:
        f.write(data)
    return p


def upload(ref, call=None):
    """A strat's "l:" image -> sent to the board. -> (True, "b:<id>") / (False, why). A "b:" one stays."""
    if not isinstance(ref, str) or ref.startswith("b:"):
        return True, ref
    p = path_of(ref)
    if not p:
        return False, "the atlas screenshot is missing from this PC"
    with open(p, "rb") as f:
        data = f.read()
    from . import board as B
    ok, d = (call or B.call)("POST", "/images", body={"data": base64.b64encode(data).decode("ascii")})
    if not ok:
        return False, d
    key = str(d.get("id") or "")
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        return False, "the board didn't keep it"
    return True, f"b:{key}"
