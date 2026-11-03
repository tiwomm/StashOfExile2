"""2.84.0: Favorites - items and trade-site searches you come back to (feedback: "a favorites (bookmark) tracker that
you can paste a trade link into ... an 'Add to favorites' button" on Price Checks).

Two kinds:
  * item  - added from Price Checks: the item with your filters as you left them (it searches the same way).
  * link  - a pasted trade-site link: its search (what the site shows for that link), with every filter editable.
Kept in favorites.json in the app's data folder (groups in your order, favorites in your order).
GGG ToS: reads the trade site's searches within its limits; nothing is bought, listed or whispered."""
import base64
import copy
import gzip
import json
import re
import time
from urllib.parse import quote, unquote, urlparse

from .config import load_json, save_json

FILE = "favorites.json"
LINK_RE = re.compile(r"/trade2?/search/poe2/([^/?#]+)/([^/?#\s]+)")


def is_link(text):
    return bool(LINK_RE.search(str(text or "")))


def split_link(link):
    """A trade-site search link -> (league, code) or (None, None). code: the short id (Ab3dE5fG) or the long
    gzip+base64 search (H4sI...)."""
    link = str(link or "").strip()
    m = LINK_RE.search(urlparse(link).path if "://" in link else link)
    if not m:
        return None, None
    return unquote(m.group(1)), m.group(2)


def decode_long(code):
    """The long form (the search itself in the link) -> {"query", "sort"} or None."""
    if not str(code).startswith("H4sI"):
        return None
    try:
        raw = base64.urlsafe_b64decode(code + "=" * (-len(code) % 4))
        q = json.loads(gzip.decompress(raw))
    except Exception:
        return None
    return q if isinstance(q, dict) else None


def read_link(link, call=None, base=None):
    """A pasted link -> ({"league", "query", "sort", "qid"}, None) or (None, plain-English reason). A short link is
    looked up on the trade site (one request: the search behind that id)."""
    league, code = split_link(link)
    if not code:
        return None, "That doesn't look like a Path of Exile 2 trade-site search link."
    data = decode_long(code)
    qid = None
    if data is None:
        if call is None:
            from .net import call
        if base is None:
            from .config import BASE as base
        try:
            data = call("GET", f"{base}/search/poe2/{quote(league)}/{code}")
        except Exception as ex:
            msg = str(ex)
            if msg.startswith("404"):
                return None, "The trade site doesn't know that search any more (old links expire). Open it on the " \
                             "site, change any filter and copy the address again."
            return None, f"Couldn't read that link from the trade site ({msg[:80]})."
        qid = code
    q = data.get("query") if isinstance(data, dict) else None
    if not isinstance(q, dict):
        return None, "The trade site sent no search for that link."
    return {"league": league, "query": q, "sort": data.get("sort") or {"price": "asc"}, "qid": qid}, None


def link_name(q):
    """A first name for a pasted search: the item's name / base / text, else its category."""
    q = q or {}
    for k in ("name", "type", "term"):
        v = q.get(k)
        if isinstance(v, dict):
            v = v.get("option") or v.get("discriminator")
        if isinstance(v, str) and v.strip():
            return v.strip()
    cat = ((((q.get("filters") or {}).get("type_filters") or {}).get("filters") or {}).get("category") or {})
    opt = str(cat.get("option") or "")
    if opt:
        return opt.split(".")[-1].replace("_", " ").title() + " search"
    return "Trade search"


def clean_query(q):
    """The search as the trade site should get it: filters and groups switched off are left out."""
    q = copy.deepcopy(q or {})
    stats = []
    for g in q.get("stats") or []:
        if g.get("disabled"):
            continue
        g["filters"] = [f for f in g.get("filters") or [] if not f.get("disabled")]
        g.pop("disabled", None)
        for f in g["filters"]:
            f.pop("disabled", None)
        if g["filters"] or g.get("type") == "and":
            stats.append(g)
    if "stats" in q:
        q["stats"] = stats
    for gname, grp in list((q.get("filters") or {}).items()):
        if not isinstance(grp, dict):
            continue
        if grp.get("disabled"):
            q["filters"].pop(gname)
            continue
        fl = grp.get("filters") or {}
        for k in [k for k, v in fl.items() if isinstance(v, dict) and v.get("disabled")]:
            fl.pop(k)
    return q


def pack_item(item):
    """A record's item -> JSON (mod flags are sets in the app)."""
    it = copy.deepcopy(item)
    it["mods"] = [{**m, "flags": sorted(m.get("flags") or [])} for m in it.get("mods") or []]
    return it


def unpack_item(item):
    it = copy.deepcopy(item)
    for m in it.get("mods") or []:
        m["flags"] = set(m.get("flags") or [])
    return it


class FavStore:
    """favorites.json: {"groups": [{id, name, open}], "items": [{id, name, group, kind, ...}]} - lists in your order."""

    def __init__(self, name=FILE):
        self.name = name
        d = load_json(name, {})
        self.groups = [g for g in d.get("groups") or [] if isinstance(g, dict) and g.get("id")]
        self.items = [f for f in d.get("items") or [] if isinstance(f, dict) and f.get("id")]
        self.next = int(d.get("next") or 1)
        gids = {g["id"] for g in self.groups}
        for f in self.items:
            if f.get("group") not in gids:
                f["group"] = ""

    def save(self):
        return save_json(self.name, {"version": 1, "next": self.next, "groups": self.groups, "items": self.items})

    def new_id(self, pre):
        self.next += 1
        return f"{pre}{self.next - 1}"

    def get(self, fid):
        return next((f for f in self.items if f["id"] == fid), None)

    def group(self, gid):
        return next((g for g in self.groups if g["id"] == gid), None)

    def in_group(self, gid):
        return [f for f in self.items if f.get("group", "") == gid]

    # ---- adding
    def add_item(self, rec, name=None, group=""):
        it = rec["item"]
        f = {"id": self.new_id("f"), "kind": "item", "name": name or it.get("name") or it.get("base") or "Item",
             "group": group, "added": time.time(), "item": pack_item(it), "raw": rec.get("raw") or "",
             "opts": copy.deepcopy(rec.get("opts") or {}), "resolved": bool(rec.get("resolved")), "note": ""}
        self.items.append(f)
        return f

    def add_link(self, url, info, name=None, group=""):
        f = {"id": self.new_id("f"), "kind": "link", "name": name or link_name(info["query"]), "group": group,
             "added": time.time(), "url": url, "league": info.get("league") or "", "query": info["query"],
             "sort": info.get("sort") or {"price": "asc"}, "qid": info.get("qid"), "note": ""}
        self.items.append(f)
        return f

    def add_group(self, name):
        g = {"id": self.new_id("g"), "name": name, "open": True}
        self.groups.append(g)
        return g

    def duplicate(self, fid):
        f = self.get(fid)
        if not f:
            return None
        c = copy.deepcopy(f)
        c["id"], c["name"], c["added"] = self.new_id("f"), f"{f['name']} (copy)", time.time()
        c.pop("last", None)
        self.items.insert(self.items.index(f) + 1, c)
        return c

    # ---- order
    def move(self, fids, group, before=None):
        """Move these favorites into `group`, before the favorite `before` (None: at the group's end), in the order
        they are listed now."""
        moving = [f for f in self.items if f["id"] in set(fids)]
        if not moving:
            return
        rest = [f for f in self.items if f["id"] not in set(fids)]
        for f in moving:
            f["group"] = group
        at = next((i for i, f in enumerate(rest) if f["id"] == before), None)
        if at is None:
            idx = [i for i, f in enumerate(rest) if f.get("group", "") == group]
            at = (idx[-1] + 1) if idx else len(rest)
        self.items = rest[:at] + moving + rest[at:]

    def step(self, fid, d):
        """One place up (-1) or down (+1) within its group."""
        f = self.get(fid)
        if not f:
            return False
        sib = self.in_group(f.get("group", ""))
        i = sib.index(f)
        j = i + d
        if not 0 <= j < len(sib):
            return False
        a, b = self.items.index(f), self.items.index(sib[j])
        self.items[a], self.items[b] = self.items[b], self.items[a]
        return True

    def step_group(self, gid, d):
        g = self.group(gid)
        if not g:
            return False
        i = self.groups.index(g)
        j = i + d
        if not 0 <= j < len(self.groups):
            return False
        self.groups[i], self.groups[j] = self.groups[j], self.groups[i]
        return True

    def move_group(self, gid, before):
        g = self.group(gid)
        if not g or gid == before:
            return
        self.groups.remove(g)
        at = next((i for i, x in enumerate(self.groups) if x["id"] == before), len(self.groups))
        self.groups.insert(at, g)

    # ---- removing (-> what puts it back)
    def remove(self, fids):
        gone = [(i, f) for i, f in enumerate(self.items) if f["id"] in set(fids)]
        self.items = [f for f in self.items if f["id"] not in set(fids)]

        def restore():
            for i, f in gone:
                self.items.insert(min(i, len(self.items)), f)
        return gone, restore

    def remove_group(self, gid):
        """The group goes; its favorites stay (ungrouped)."""
        g = self.group(gid)
        if not g:
            return None
        gi = self.groups.index(g)
        kept = [f["id"] for f in self.in_group(gid)]
        self.groups.remove(g)
        for f in self.items:
            if f["id"] in kept:
                f["group"] = ""

        def restore():
            self.groups.insert(min(gi, len(self.groups)), g)
            for f in self.items:
                if f["id"] in kept:
                    f["group"] = gid
        return restore
