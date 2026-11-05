"""Scan stash (stashread.GLYPHS): rebuild the digit shapes from your own stash shots.

Usage: python tools/stash_glyphs.py counts.json currency=cur.png abyss=aby.png ...
counts.json: {"currency": {"Chaos Orb": 4685, ...}, ...} - the real stack sizes (Ctrl+C) of the shots.
Each shot: the panel's inside from a 1440p game, like tools/stash_slots.py. Prints a GLYPHS block to paste into
stashread.py. Your shots and counts are wealth data: keep them on your PC, never commit them."""
import base64
import json
import sys

import cv2
import numpy as np

sys.path.insert(0, ".")
from soe2.stashlayouts import TABS  # noqa: E402
from soe2.stashread import feature  # noqa: E402


def samples(counts, shots):
    got = {str(d): [] for d in range(10)}
    for tab, path in shots.items():
        im = cv2.imread(path)
        for name, (x, y, _w, _h) in TABS[tab]["slots"]:
            n = counts.get(tab, {}).get(name)
            if not n:
                continue
            raw = im[y:y + 24, x:x + 62]
            m = (raw.min(axis=2) > 170).astype(np.uint8)
            band = feature(raw)
            _k, _lab, st, _c = cv2.connectedComponentsWithStats(m, connectivity=8)
            cs = sorted([s for s in st[1:] if 11 <= s[3] <= 18 and s[1] <= 10 and s[2] <= 12 and s[4] >= 20],
                        key=lambda s: s[0])[:len(str(n))]
            if len(cs) != len(str(n)) or any(cs[i + 1][0] - cs[i][0] > 13 for i in range(len(cs) - 1)):
                continue                                    # touching digits: skip this one
            for d, s in zip(str(n), cs):
                got[d].append(band[4:23, s[0] - 1:s[0] + s[2] + 1])
    return got


if __name__ == "__main__":
    counts = json.load(open(sys.argv[1], encoding="utf-8"))
    shots = dict(a.split("=", 1) for a in sys.argv[2:])
    print("GLYPHS = {")
    for d, v in samples(counts, shots).items():
        if not v:
            print(f"    # {d}: no clean sample")
            continue
        g = np.mean(np.stack([x for x in v if x.shape == v[0].shape]).astype(np.float32), axis=0)
        q = np.clip(np.round((g + 1) * 127.5), 0, 255).astype(np.uint8)
        print(f'    "{d}": ({q.shape[1]}, {q.shape[0]}, "{base64.b64encode(q.tobytes()).decode()}"),')
    print("}")
