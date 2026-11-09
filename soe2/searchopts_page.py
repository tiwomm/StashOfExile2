"""The item panel's "Search filters" box (2.4.1): narrow the trade searches for one item, like a trade site's own
filters - who's selling, what they price in, corrupted or not, and for gear item level, quality, sockets and whether
to compare with the same base only. Kept on the item (rec["opts"]); used by every search for it (trade.apply_opts).
"Search with these values" prices it again with them. Nothing changes for other items."""
import re


def default_opts(item):
    """What the searches use when you haven't changed anything (for showing it, and for Reset)."""
    st = "securable"                     # 2.79.2 (feedback): the item's search starts at Instant Buyout, always
    gear = bool(item.get("gear")) and not item.get("waystone")
    s = item.get("search") or {}
    out = {"status": st, "currency": None,
           "corrupted": ("yes" if item.get("corrupted") else "no") if item.get("gear") else "any"}
    if item.get("waystone") and item.get("tier"):        # 2.103.2: same tier, as the search always did
        out["tier"] = {"min": item["tier"], "max": item["tier"]}
    if gear:
        out.update(ilvl=None, quality=None, sockets=s.get("sockets_min"),
                   base="same" if s.get("type") else "class")
        if s.get("ilvl_max"):                            # 2.79.0: white / blue bases - what their search uses
            out.update(ilvl={"min": s["ilvl_min"], "max": s["ilvl_max"]},
                       quality={"min": s["quality_min"]} if s.get("quality_min") else None,
                       sockets={"min": s["sockets_min"]} if s.get("sockets_min") else None,
                       corrupted="no", fractured="no", sanctified="no")
    return out


REQ = re.compile(r"^Requires:\s*(.+)$", re.M)


def item_facts(rec):
    """2.79.0: what the item panel's filters need that the price check doesn't keep: requirements (Level, Str,
    Dex, Int) and the item's flags (corrupted, fractured, desecrated, sanctified, mirrored, unidentified)."""
    raw = (rec.get("raw") or "").replace("\r", "")
    req = {}
    m = REQ.search(raw)
    if m:
        for part in m.group(1).split(","):
            part = part.strip()
            lv = re.match(r"Level\s+(\d+)", part, re.I)
            if lv:
                req["lvl"] = int(lv.group(1))
                continue
            at = re.match(r"(\d+)\s+(Str|Dex|Int)", part, re.I)
            if at:
                req[at.group(2).lower()] = int(at.group(1))
    lines = {l.strip() for l in raw.split("\n")}
    flags = {k for k, line in (("corrupted", "Corrupted"), ("fractured", "Fractured Item"), ("sanctified", "Sanctified"),
                               ("mirrored", "Mirrored"), ("unidentified", "Unidentified")) if line in lines}
    if "(desecrated)" in raw.lower() or "desecrated" in " ".join(
            " ".join(sorted(m_.get("flags") or [])) for m_ in rec["item"].get("mods") or []):
        flags.add("desecrated")
    if rec["item"].get("corrupted"):
        flags.add("corrupted")
    return {"req": {k: req[k] for k in ("lvl", "str", "dex", "int") if k in req}, "flags": flags}


class SearchOptsPage:
    """Mixed into App."""

    def search_opt_set(self, rec, key, value, redraw=True):
        base = default_opts(rec["item"])
        o = dict(rec.get("opts") or {})
        if base.get(key) == value:
            o.pop(key, None)
        else:
            o[key] = value
        if o:
            rec["opts"] = o
        else:
            rec.pop("opts", None)
        self.dirty = True
        if redraw:
            self.show_detail(rec)

    def search_opts_reset(self, rec):
        rec.pop("opts", None)
        self.dirty = True
        self.show_detail(rec)
