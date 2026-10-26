"""What you've priced, kept in the background (2.4.0) - so Top value still knows your most valuable items after you
clear the Price checks list (clearing it when you're done is how that list is meant to be used).

value_log.json in the app's data folder: one entry per item (the same item priced again updates its entry), the newest
VALUE_LOG_MAX kept. Each entry: when, league, name, base, class, estimate, confidence, how it was priced, its mods and
the item text (to open it again in Price checks), and listed / removed when you mark it."""
import hashlib
import threading
import time

from .config import load_json, save_json

FILE = "value_log.json"
VALUE_LOG_MAX = 3000


def sig_of(raw):
    return hashlib.sha1((raw or "").strip().encode("utf-8", "replace")).hexdigest()[:16]


class ValueLog:
    def __init__(self):
        d = load_json(FILE, {}) or {}
        self.items = d.get("items", {}) if isinstance(d.get("items"), dict) else {}
        self.lock = threading.Lock()
        self._save_job = None

    def save(self):
        with self.lock:
            if len(self.items) > VALUE_LOG_MAX:
                keep = sorted(self.items.items(), key=lambda kv: -kv[1].get("ts", 0))[:VALUE_LOG_MAX]
                self.items = dict(keep)
            data = {"version": 1, "items": dict(self.items)}
        return save_json(FILE, data)

    def add(self, rec, league):
        """A finished price check. -> the entry (or None when there's nothing worth keeping)."""
        if rec.get("est") is None or rec.get("skip") or not rec.get("raw"):
            return None
        it = rec.get("item") or {}
        sig = sig_of(rec["raw"])
        with self.lock:
            old = self.items.get(sig) or {}
            e = {"sig": sig, "ts": time.time(), "league": league, "name": it.get("name") or "", "base": it.get("base") or "",
                 "class": it.get("class") or "", "est": rec["est"], "conf": rec.get("conf") or "",
                 "label": (rec.get("label") or "")[:200], "mods": [m.get("text") for m in it.get("mods", [])][:12],
                 "raw": rec["raw"], "mark": rec.get("mark") or old.get("mark") or "new"}
            self.items[sig] = e
        return e

    def mark(self, rec):
        sig = sig_of(rec.get("raw"))
        with self.lock:
            if sig in self.items:
                self.items[sig]["mark"] = rec.get("mark") or "new"
                return True
        return False

    def remove(self, sigs):
        with self.lock:
            gone = {s: self.items.pop(s) for s in list(sigs) if s in self.items}
        return gone

    def restore(self, gone):
        with self.lock:
            self.items.update(gone)

    def top(self, league, kind_fn, kind, limit=50):
        with self.lock:
            rows = [e for e in self.items.values() if e.get("league") == league and kind_fn(e["base"], e["class"]) == kind]
        rows.sort(key=lambda e: -(e.get("est") or 0))
        return rows[:limit]


VALUE_LOG = ValueLog()
