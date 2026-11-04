"""2.95.0: rep - karma-style points for helping the community, and the small contributor icon beside a name.

Rep comes from the board (board/src/index.js, "rep"): an upvote on your strat +1, an edit of yours that's accepted +3
(declined -1), a review that matched what was decided +1, a mod rating or map rank that matches what the community
settled on +1 each (only if you turn that on), a fixed bug from your report (an admin's thank-you); a post removed for
breaking the rules -2. Never below 0. Nothing is unlocked by it - everything stays open to everyone.

The icon steps up in color like item rarity: white, blue, yellow, orange. Hover it: the contributor card.
GGG ToS: nothing here touches the game."""
import threading
import time
import tkinter as tk

TIERS = ((1000, "unique", "#af6025"), (250, "rare", "#e8d24a"), (50, "magic", "#8888ff"), (1, "normal", "#c8c8c8"))
CARD_TTL = 600                       # a card is fetched again after 10 minutes
_cards = {}                          # name (lower) -> (time, (ok, data))
_icons = {}


def tier(rep):
    """-> (key, color) for this much rep, or None (no rep yet, or hidden: no icon)."""
    try:
        r = int(rep)
    except (TypeError, ValueError):
        return None
    for floor, key, col in TIERS:
        if r >= floor:
            return key, col
    return None


def icon(root, rep, size=11):
    """A small diamond in the tier's color (a PhotoImage, kept), or None."""
    t = tier(rep)
    if t is None:
        return None
    k = (t[0], size)
    if k in _icons:
        return _icons[k]
    img = tk.PhotoImage(master=root, width=size, height=size)
    c, half = t[1], size // 2
    for y in range(size):
        w = half - abs(y - half)
        if w >= 0:
            img.put(c, to=(half - w, y, half + w + 1, y + 1))
    _icons[k] = img
    return img


def card_text(d):
    """The contributor card as lines (from GET /people/<name>)."""
    if not d:
        return "Couldn't load this contributor."
    if d.get("hidden"):
        return f"{d.get('name', '?')} keeps their contributor card private."
    f = d.get("from") or {}
    parts = [f"{f[k]} {label}" for k, label in (("upvotes", "upvotes on their strats"), ("edits", "accepted edits"),
                                               ("reviews", "reviews"), ("ratings", "ratings that matched the community"),
                                               ("bugs", "fixed bug reports")) if f.get(k)]
    return "\n".join([f"{d.get('name', '?')} - community contributor", f"{d.get('rep', 0):,} rep",
                      *(["From: " + ", ".join(parts)] if parts else []),
                      f"Member since {d.get('since', '?')}"])


def card(name, done, sync=False):
    """Fetch someone's card (cached) and call done(ok, data) - on this thread when sync, else from a worker thread."""
    from . import board as B
    k = str(name).lower()
    hit = _cards.get(k)
    if hit and time.time() - hit[0] < CARD_TTL:
        return done(*hit[1])

    def work():
        res = B.person(name)
        _cards[k] = (time.time(), res)
        done(*res)
    if sync:
        return work()
    threading.Thread(target=work, daemon=True).start()
    return None


def forget():
    _cards.clear()
