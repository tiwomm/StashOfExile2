"""StashOfExile2 icon (2.60.0): a stash chest whose lid is a toolbox - carry handle on top, hex-nut lock."""
from PIL import Image, ImageDraw, ImageFilter
import sys
K = 4
S = 256 * K


def P(*v):
    return [int(x * K) for x in v]


def vgrad(size, top, bot):
    w, h = size
    g = Image.new("RGBA", size)
    d = ImageDraw.Draw(g)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bot)) + (255,))
    return g


def paste_shape(img, shape_fn, fill_img, box):
    m = Image.new("L", img.size, 0)
    shape_fn(ImageDraw.Draw(m))
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    layer.paste(fill_img, box)
    img.paste(layer, (0, 0), Image.composite(m, Image.new("L", img.size, 0), m))


img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
# soft shadow
sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(sh).ellipse(P(30, 214, 226, 246), fill=(0, 0, 0, 120))
img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8 * K)))
d = ImageDraw.Draw(img)

OUT = (24, 16, 10, 255)
# ---- handle (behind the lid): a steel carry arch
d.rounded_rectangle(P(80, 26, 176, 62), radius=16 * K, fill=OUT)
d.rounded_rectangle(P(88, 34, 168, 58), radius=10 * K, fill=(0, 0, 0, 0))
inner = Image.new("RGBA", (S, S), (0, 0, 0, 0))
di = ImageDraw.Draw(inner)
di.rounded_rectangle(P(84, 30, 172, 60), radius=14 * K, fill=(150, 162, 176, 255))
di.rounded_rectangle(P(92, 38, 164, 62), radius=8 * K, fill=(0, 0, 0, 0))
di.line(P(98, 33, 158, 33), fill=(214, 224, 234, 255), width=3 * K)
img.alpha_composite(inner)
d = ImageDraw.Draw(img)
for x in (84, 152):                                   # brackets
    d.rounded_rectangle(P(x, 52, x + 20, 80), radius=4 * K, fill=OUT)
    d.rounded_rectangle(P(x + 3, 55, x + 17, 78), radius=3 * K, fill=(88, 98, 110, 255))

# ---- chest body (wood)
d.rounded_rectangle(P(22, 108, 234, 230), radius=14 * K, fill=OUT)
paste_shape(img, lambda m: m.rounded_rectangle(P(28, 112, 228, 224), radius=10 * K, fill=255),
            vgrad((S, P(0, 120)[1]), (150, 92, 46), (92, 52, 24)), (0, P(0, 108)[1]))
d = ImageDraw.Draw(img)
for y in (146, 182):                                  # planks
    d.line(P(30, y, 226, y), fill=(62, 34, 14, 255), width=3 * K)
    d.line(P(30, y + 2, 226, y + 2), fill=(176, 112, 60, 255), width=1 * K)
# iron corner bands
for x0 in (28, 200):
    d.rectangle(P(x0, 112, x0 + 28, 224), fill=(52, 58, 66, 255))
    d.line(P(x0 + 2, 114, x0 + 2, 222), fill=(112, 122, 134, 255), width=2 * K)
    for y in (126, 168, 208):
        d.ellipse(P(x0 + 9, y - 5, x0 + 19, y + 5), fill=(30, 33, 38, 255))
        d.ellipse(P(x0 + 11, y - 4, x0 + 15, y), fill=(160, 170, 182, 255))

# ---- toolbox lid (dark iron, bevelled)
d.rounded_rectangle(P(16, 70, 240, 120), radius=12 * K, fill=OUT)
paste_shape(img, lambda m: m.rounded_rectangle(P(22, 75, 234, 114), radius=8 * K, fill=255),
            vgrad((S, P(0, 42)[1]), (104, 114, 126), (46, 52, 60)), (0, P(0, 74)[1]))
d = ImageDraw.Draw(img)
d.line(P(30, 78, 226, 78), fill=(176, 188, 200, 255), width=2 * K)       # top light edge
d.line(P(24, 100, 232, 100), fill=(30, 34, 40, 255), width=2 * K)         # the tray seam
# ember-gold trim under the lid
d.rectangle(P(22, 114, 234, 119), fill=(228, 150, 58, 255))
d.line(P(22, 114, 234, 114), fill=(255, 206, 128, 255), width=1 * K)

# ---- hex-nut lock (gold) with a keyhole
import math
cx, cy, r = 128, 128, 30
hexp = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(30, 390, 60)]
d.polygon([tuple(int(v * K) for v in p) for p in [(x, y + 2) for x, y in hexp]], fill=OUT)
d.polygon([tuple(int(v * K) for v in p) for p in hexp], fill=(214, 156, 52, 255))
r2 = r - 7
hex2 = [(cx + r2 * math.cos(math.radians(a)), cy + r2 * math.sin(math.radians(a))) for a in range(30, 390, 60)]
d.polygon([tuple(int(v * K) for v in p) for p in hex2], fill=(246, 196, 92, 255))
d.line([tuple(int(v * K) for v in p) for p in hexp[3:6]], fill=(255, 232, 170, 255), width=2 * K)   # light top edges
d.polygon([tuple(int(v * K) for v in p) for p in hexp], outline=OUT, width=3 * K)
d.ellipse(P(cx - 7, cy - 12, cx + 7, cy + 2), fill=(40, 22, 8, 255))
d.polygon(P(cx - 4, cy - 2, cx + 4, cy - 2, cx + 6, cy + 14, cx - 6, cy + 14), fill=(40, 22, 8, 255))

out = img.resize((256, 256), Image.LANCZOS)
out.save(sys.argv[1] + "/icon256.png")
out.resize((96, 96), Image.LANCZOS).save(sys.argv[1] + "/icon96.png")
out.save(sys.argv[1] + "/stashofexile2.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
prev = Image.new("RGBA", (256 + 96 + 48 + 32 + 16 + 60, 256), (30, 30, 34, 255))
x = 0
for sz in (256, 96, 48, 32, 16):
    prev.alpha_composite(out.resize((sz, sz), Image.LANCZOS), (x, 0))
    x += sz + 12
prev.save(sys.argv[1] + "/preview.png")
