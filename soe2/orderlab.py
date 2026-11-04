"""2.88.0: Listing order lab (Under the hood, admins only) - working out in what order the trade site lists a public
stash tab's items, so a tab read can be worked down in the same order as the stash.

How a round goes (feedback: "the tool reads the trade site link and then I go one time through each item manually and
you try and decipher the listing order. We'll maybe have to do a few of them to get enough listing data"):
  1. Read: a trade-site link of your public tab -> the listings in the order the site returns them (and the same
     search sorted by newest, to compare), each with what the site says about it: its place in the tab (x / y),
     when it was indexed, its listing id.
  2. Walk: go through the tab in game in your own order and Ctrl+Alt+C each item; each copy is matched to its listing.
  3. Compare: how closely each candidate order (the site's, newest first, by place down columns / across rows, by
     id) follows your walk and the site's order (rank correlation, 1 = the same order).
Rounds are kept in orderlab.json (Export CSV for a spreadsheet), so several tabs can be compared.
GGG ToS: trade-site searches within its limits, and your own copies; nothing is sent to the game."""
import re
import time

from .config import load_json, save_json

FILE = "orderlab.json"


def _norm_line(s, numbers=True):
    s = re.sub(r"\[[^\]|]*\|([^\]]*)\]|\[([^\]]*)\]", lambda m: m.group(1) or m.group(2) or "", str(s))
    s = re.sub(r"\([^)]*\)", "", s)                       # (implicit) (crafted) ...
    if not numbers:
        s = re.sub(r"[-+]?\d+(?:\.\d+)?", "#", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def text_key(text):
    """A copied item -> (name lines, its other lines as written, the same with numbers as #) for matching. The name
    lines are the (up to two) lines right after "Rarity:"."""
    lines = [l.strip() for l in str(text or "").splitlines() if l.strip() and not l.startswith("--")]
    head, rest, after = [], [], False
    for l in lines:
        if l.startswith("Item Class:"):
            continue
        if l.startswith("Rarity:"):
            after = True
            continue
        if after and len(head) < 2 and ":" not in l:
            head.append(l.lower())
            continue
        after = False
        rest.append(l)
    exact = {_norm_line(l) for l in rest if _norm_line(l)}
    shape = {_norm_line(l, False) for l in rest if _norm_line(l, False)}
    return tuple(head), exact, shape


def entry(e, rank):
    """One fetched listing (the site's own entry) -> what the lab keeps."""
    from .wealth import item_text
    it, lst = (e or {}).get("item") or {}, (e or {}).get("listing") or {}
    st = lst.get("stash") or {}
    try:
        text = item_text(it)
    except Exception:
        text = f"{it.get('name') or ''}\n{it.get('typeLine') or ''}"
    p = lst.get("price") or {}
    return {"id": (e or {}).get("id"), "rank": rank, "name": " ".join(x for x in (it.get("name"), it.get("typeLine")) if x),
            "x": st.get("x"), "y": st.get("y"), "stash": st.get("name"), "indexed": lst.get("indexed"),
            "price": f"{p.get('amount')} {p.get('currency')}" if p else "", "text": text, "walk": None}


def match(listings, text):
    """A copied item -> the listing it is (not walked yet; the best line overlap among those with the same name)."""
    head, exact, shape = text_key(text)
    best, score = None, float("-inf")
    for L in listings:
        if L.get("walk") is not None:
            continue
        h, ex, sh = text_key(L["text"])
        if head and h and h != head:
            continue
        sc = 2 * len(exact & ex) + len(shape & sh) - 0.1 * len(shape ^ sh)
        if sc > score:
            best, score = L, sc
    return best


def ranks(values):
    """Values -> their ranks (ties share the average rank)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2
        i = j + 1
    return out


def spearman(a, b):
    """Rank correlation of two equally long lists: 1 = the same order, -1 = reversed, 0 = no relation."""
    n = len(a)
    if n < 3:
        return None
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra) ** 0.5
    vb = sum((y - mb) ** 2 for y in rb) ** 0.5
    return round(cov / (va * vb), 3) if va and vb else None


def orders(listings, newest=None):
    """{name: [key per listing]} - every candidate order (lower = earlier)."""
    out = {"the site's order": [L["rank"] for L in listings]}
    if newest:
        pos = {i: n for n, i in enumerate(newest)}
        out["newest first (site)"] = [pos.get(L["id"], 10 ** 6) for L in listings]
    if all(isinstance(L.get("x"), int) and isinstance(L.get("y"), int) for L in listings):
        out["place, down columns"] = [L["x"] * 1000 + L["y"] for L in listings]
        out["place, across rows"] = [L["y"] * 1000 + L["x"] for L in listings]
    if all(L.get("indexed") for L in listings):
        out["indexed time"] = [str(L["indexed"]) for L in listings]
    out["listing id"] = [str(L["id"]) for L in listings]
    return out


def compare(listings, newest=None):
    """-> [(order name, vs your walk, vs the site's order)] (None where it can't be worked out)."""
    os_ = orders(listings, newest)
    walked = [L for L in listings if L.get("walk") is not None]
    out = []
    for name, keys in os_.items():
        by_id = {L["id"]: k for L, k in zip(listings, keys)}
        vs_walk = spearman([L["walk"] for L in walked], [by_id[L["id"]] for L in walked]) if len(walked) >= 3 else None
        vs_site = spearman(os_["the site's order"], keys) if name != "the site's order" else 1.0
        out.append((name, vs_walk, vs_site))
    return out


class Lab:
    """orderlab.json: {"rounds": [{when, link, listings, newest}]}"""

    def __init__(self):
        d = load_json(FILE, {})
        self.rounds = d.get("rounds") if isinstance(d.get("rounds"), list) else []

    def save(self):
        return save_json(FILE, {"version": 1, "rounds": self.rounds[-50:]})

    def new_round(self, link, listings, newest):
        r = {"when": time.time(), "link": link, "listings": listings, "newest": newest}
        self.rounds.append(r)
        self.save()
        return r


def to_csv(rounds, path):
    import csv
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["round", "when", "site_rank", "newest_rank", "walk", "x", "y", "indexed", "id", "name", "price"])
        for n, r in enumerate(rounds, 1):
            pos = {i: k for k, i in enumerate(r.get("newest") or [])}
            for L in r["listings"]:
                w.writerow([n, time.strftime("%Y-%m-%d %H:%M", time.localtime(r["when"])), L["rank"],
                            pos.get(L["id"], ""), "" if L.get("walk") is None else L["walk"], L.get("x"), L.get("y"),
                            L.get("indexed"), L["id"], L["name"], L.get("price")])
