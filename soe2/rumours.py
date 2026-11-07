"""2.83.0: Island Rumours helper (Expedition) - the world map's "Uncharted Waters" card lists up to three rumours;
each gets a tag with the island it leads to and your Map library rank for it (feedback: "use our Map library to build
an add-on ... that operates the rumor helper").

Which rumour leads where: the two newest guides agree (epoe.io's Expedition guide, reviewed for 0.5.5e, and aoeah's
0.5 tier list). Ranks are yours - set them in the Map library (the suggested ones are in the 2.83.0 notes).
On screen: the card is the one large light parchment patch (found on a small copy of the screen), then only that
part is read (Windows' text reader). Only while you're in your hideout (Client.txt). GGG ToS: it looks and shows."""
import difflib
import re

# rumour as the card words it -> the island (its name in the Map library)
RUMOURS = [
    ("Fallen stars...", "Moor of Fallen Skies"),
    ("Crazed Chieftain...", "The Jade Isles"),
    ("Nothin' to drink...", "Stagnant Basin"),
    ("Cold as ice...", "Frigid Bluffs"),
    ("Stardrinker...", "Secluded Temple"),
    ("Sulphite!", "Scorched Cay"),
    ("Endless cliffs...", "Craggy Peninsula"),
    ("All that glitters...", "Castaway"),
    ("Almost paradise.", "Untainted Paradise"),
    ("Reflective waters...", "The Fractured Lake"),
    ("A good fellow...", "Moment of Zen"),
    ("It's dry at least...", "Sloughed Gully"),
    ("Wild roaming free...", "Lush Isle"),
    ("Origin of the fall...", "Obscure Island"),
    ("Unknown ruins...", "Exhumed Ruins"),
    ("Warm but risky...", "Grazed Prairie"),
    ("Somethin' fishy...", "Barren Atoll"),
    ("Bleak and awful...", "Bleached Shoals"),
    ("End of the circle...", "Sprawling Jungle"),
    ("The last to fall...", "Mournful Cliffside"),
]
MATCH = 0.72
WHOLE_MATCH = 0.8              # 2.113.1: in the card's whole text (stricter - more to match against)
SCALE = 8                       # the screen is searched at 1/8 size
MIN_AREA = 0.02                 # the card's parchment, as a share of (game height)^2


def squash(text):
    """Lower case, letters only (the card's handwriting reads as "Endless clif fs..." - spaces can't be trusted)."""
    return re.sub(r"[^a-z]", "", str(text or "").lower())


# 2.113.2 (rumours_read.txt: "Nothin' to drink..." read as "Wodviw' to c(riwkv.."): Windows' reader swaps letters
# that look alike in the card's handwriting - n / w / u / v / h / m, t / d / c / l, o / a. Compared by shape too:
# rumours score 0.88+ that way, the card's other lines 0.56 or less, two rumours never above 0.64.
SHAPE = str.maketrans({**{c: "n" for c in "nwuvhm"}, **{c: "t" for c in "tdcl"}, **{c: "i" for c in "ij"},
                       **{c: "o" for c in "oaq"}})


def shape(text):
    return squash(text).translate(SHAPE)


_KEYS = [(squash(r), r, i) for r, i in RUMOURS]
_SHAPES = {i: shape(r) for r, i in RUMOURS}


def _score(s, k):
    """How well line s holds rumour k: the whole line, or (2.113.0) its best stretch of about k's length - a rumour
    read on one line with the "Island Rumours" heading above it ("islandrumourswarmbutrisky") didn't match."""
    best = difflib.SequenceMatcher(None, s, k).ratio()
    if len(s) > len(k) + 3:
        for n in (len(k) - 2, len(k), len(k) + 2):
            if n < 4:
                continue
            for a in range(0, len(s) - n + 1):
                sc = difflib.SequenceMatcher(None, s[a:a + n], k).ratio()
                if sc > best:
                    best = sc
    return best


def match(line):
    """An OCR'd line -> (rumour, island) or None: by its letters, or (2.113.2) by their shapes - the best of the two,
    with a clear lead over the next rumour."""
    s, sh = squash(line), shape(line)
    if len(s) < 4:
        return None
    scores = []
    for k, r, i in _KEYS:
        scores.append((max(_score(s, k), _score(sh, _SHAPES[i])), r, i))
    scores.sort(reverse=True)
    best = scores[0]
    lead = best[0] - (scores[1][0] if len(scores) > 1 else 0.0)
    return (best[1], best[2]) if best[0] >= MATCH and lead >= 0.15 else None


def find_card(img, game_h):
    """A picture of the game window -> the card's box (x0, y0, x1, y1) in its pixels, or None: the largest connected
    patch of the card's light parchment, when it's big enough."""
    import numpy as np
    w, h = img.size
    sw, sh = max(1, w // SCALE), max(1, h // SCALE)
    a = np.asarray(img.convert("RGB").resize((sw, sh), 4)).astype(np.int16)        # 4 = BOX: fast
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = ((r > 140) & (g > 130) & (b > 105) & (r - b >= 5) & (r - b <= 50) & (r - g <= 20)).ravel()
    seen = np.zeros(sw * sh, dtype=bool)
    best = (0, None)
    for start in np.flatnonzero(m):
        if seen[start]:
            continue
        seen[start] = True
        stack, n = [int(start)], 0
        x0 = y0 = 10 ** 9
        x1 = y1 = -1
        while stack:
            i = stack.pop()
            n += 1
            y, x = divmod(i, sw)
            x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
            for j in ((i - 1) if x > 0 else -1, (i + 1) if x < sw - 1 else -1, i - sw, i + sw):
                if 0 <= j < sw * sh and m[j] and not seen[j]:
                    seen[j] = True
                    stack.append(j)
        if n > best[0]:
            best = (n, (x0, y0, x1, y1))
    n, box = best
    if box is None or n * SCALE * SCALE / max(1, game_h * game_h) < MIN_AREA:
        return None
    x0, y0, x1, y1 = box
    return (x0 * SCALE, y0 * SCALE, (x1 + 1) * SCALE, (y1 + 1) * SCALE)


def rows(lines):
    """OCR lines of the card -> [(rumour, island, line box)] for the lines that are rumours (the header and the
    Requires line aren't). 2.113.1 (feedback: the middle one of three was missed): a rumour no single line matches is
    looked for in the card's whole text (Windows' reader can split a rumour over two lines or join it to the next),
    a little stricter there; its box is the line it starts on."""
    out, seen = [], set()
    for text, box in lines:
        hit = match(text)
        if hit and hit[1] not in seen:
            seen.add(hit[1])
            out.append((hit[0], hit[1], box))
    if len(out) < 3 and lines:
        parts = [(shape(t), b) for t, b in lines]           # (2.113.2: by shape - see SHAPE)
        full = "".join(p for p, _b in parts)
        starts, pos = [], 0
        for p, b in parts:
            starts.append((pos, b))
            pos += len(p)
        for _k, r, i in _KEYS:
            k = _SHAPES[i]
            if i in seen or len(k) < 6:
                continue
            best, at = 0.0, 0
            n = len(k)
            for a in range(0, max(1, len(full) - n + 1)):
                sc = difflib.SequenceMatcher(None, full[a:a + n], k).ratio()
                if sc > best:
                    best, at = sc, a
            if best >= WHOLE_MATCH:
                box = next((b for s, b in reversed(starts) if s <= at), lines[0][1])
                seen.add(i)
                out.append((r, i, box))
        out.sort(key=lambda x: (x[2][1], x[2][0]))
    return out


def tag_text(island, rank):
    return f"{island}  ·  {rank}" if rank else f"{island}  ·  not ranked"
