"""Scan stash (stashlayouts.py): print the filled slots of a stash-tab screenshot, to add a new tab's layout.

Usage: python tools/stash_slots.py shot.png
The shot: the stash panel's inside only, from a 1440p game (847 x 847 or so). Filled slots show their dark-blue
backing and are found here; empty ones aren't - add those by hand from the rows' spacing. Paste the boxes into
stashlayouts.py in reading order (left to right, top to bottom). Keep your shot local: it shows your wealth."""
import sys

import cv2
import numpy as np


def boxes(path):
    im = cv2.imread(path).astype(int)
    b, g, r = im[..., 0], im[..., 1], im[..., 2]
    m = ((b > r + 12) & (b > g + 8) & (b < 140) & (r < 70)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    _n, _lab, st, _c = cv2.connectedComponentsWithStats(m)
    out = [tuple(int(v) for v in s[:4]) for s in st[1:] if s[4] > 800 and 50 < s[2] < 200 and 50 < s[3] < 300]
    return sorted(out, key=lambda q: (q[1] // 20, q[0]))


if __name__ == "__main__":
    for bx in boxes(sys.argv[1]):
        print(bx)
