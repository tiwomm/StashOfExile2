"""Builds soe2/ritual_glyphs.json: reference shapes of the digits 0 - 4 for the Ritual counter reader.

    py tools/build_ritual_glyphs.py [screenshot.png ...]

Shapes come from common sans-serif fonts (the counter uses a plain sans) at many sizes, plus the real glyphs cut out
of in-game screenshots given on the command line - full 2560x1440 screenshots or small cut-outs around the counter,
named with what they show, like "snip_1of3.png" - those count three times."""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from soe2 import ritual_alert as R  # noqa: E402

FONTS = ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSansCondensed.ttf", "FreeSans.ttf", "FreeSansBold.ttf",
         "Carlito-Regular.ttf", "Carlito-Bold.ttf", "Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf",
         "OpenSans-Regular.ttf", "Roboto-Regular.ttf", "arial.ttf", "segoeui.ttf"]


def font_paths():
    found = {}
    for root in ("/usr/share/fonts", os.path.expanduser("~/.fonts"), r"C:\Windows\Fonts"):
        for f in glob.glob(os.path.join(root, "**", "*.*tf"), recursive=True):
            found.setdefault(os.path.basename(f), f)
    return [found[n] for n in FONTS if n in found]


def glyph(img, thr=150):
    m = np.asarray(img) > thr
    ys, xs = np.nonzero(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def main(shots):
    out = []
    for f in font_paths():
        for size in range(13, 42, 3):
            ft = ImageFont.truetype(f, size)
            for d in range(5):
                im = Image.new("L", (size * 2, size * 2), 0)
                ImageDraw.Draw(im).text((size // 3, size // 4), str(d), fill=235, font=ft)
                g = glyph(im)
                v, a = R.glyph_vector(g)
                out.append([d, [round(x, 3) for x in v.flatten()], round(a, 3)])
    for path in shots:                                 # real ones: name the file like "anything_2of3.png"
        import re
        m = re.search(r"(\d)of(\d)", os.path.basename(path))
        img = np.asarray(Image.open(path).convert("L"))
        if img.shape[1] < 600:                          # a small cut-out around the counter (Snipping Tool, Capture)
            area = img
        else:
            x, y, w, h = R.search_rect(img.shape[1], img.shape[0], 0, 0)
            area = img[y:y + h, x:x + w]
        import cv2
        tpl = cv2.imread(os.path.join(os.path.dirname(R.__file__), "templates", "ritual_icon.png"), 0)
        ui = 1.0 if img.shape[1] < 600 else img.shape[0] / R.BASE_H
        hit = R.find_icon(area, tpl, ui)
        if not hit or not m:
            print("skipped", path)
            continue
        ix, iy, _s = hit
        box = area[iy + int(R.TEXT_BOX[2] * ui):iy + int(R.TEXT_BOX[3] * ui),
                   ix + int(R.TEXT_BOX[0] * ui):ix + int(R.TEXT_BOX[1] * ui)]
        spans = []
        for thr in (150, 175, 200, 125):                # the same tries as the reader
            mask = box > thr
            band = R.text_band(mask)
            if band is None:
                continue
            mask = mask[band[0]:band[1] + 1]
            spans = [sp for sp in R.glyph_spans(mask) if mask[:, sp[0]:sp[1] + 1].sum() >= 4]
            if len(spans) == 3 and R._is_slash(mask[:, spans[1][0]:spans[1][1] + 1]):
                break
        if len(spans) != 3:
            print("skipped (glyphs)", path)
            continue
        for digit, (a0, a1) in zip((int(m.group(1)), int(m.group(2))), (spans[0], spans[2])):
            v, a = R.glyph_vector(mask[:, a0:a1 + 1])
            for _ in range(3):
                out.append([digit, [round(x, 3) for x in v.flatten()], round(a, 3)])
    dest = os.path.join(os.path.dirname(R.__file__), "ritual_glyphs.json")
    with open(dest, "w") as f:
        json.dump({"grid": list(R.GRID), "glyphs": out}, f, separators=(",", ":"))
    print(len(out), "shapes ->", dest)


if __name__ == "__main__":
    main(sys.argv[1:])
