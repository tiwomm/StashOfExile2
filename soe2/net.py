"""Talking to the trade site: the rate limiter and call().

Part of StashOfExile2. Split out of the single-file app in 1.37 (see the launcher's VERSION HISTORY)."""

import collections
import math
import requests
import threading
import time
from datetime import datetime
from .config import APP_VERSION, HEADERS, load_json, P, save_json, SETTINGS


# ------------------------------------------------------------------ networking + rate limiting
# The trade site tells us its limits and how much of them we have used in the response headers:
#   X-Rate-Limit-Rules: Ip,Account       X-Rate-Limit-Ip: 30:300:600  (max hits : seconds : penalty seconds)
#   X-Rate-Limit-Ip-State: 12:300:0      (hits so far : seconds : seconds still restricted)
# The limiter keeps a list of recent hits per kind of request (search / fetch / other) and waits
# BEFORE a request would go over any limit, so we never trigger the 5-10 minute penalties.
PACES = {
    # margin: fraction of every limit we keep unused; gap: minimum seconds between two searches
    # cap300: most searches (and most fetches) we allow ourselves per 5 minutes - real 429s came at 10-15 even though
    #         the site reports 30, so this is deliberately lower. Every penalty lowers it by 1 (never below 3).
    # learn_cap: only learn mods in the background while usage is below this (None = never learn)
    "Fast":     {"margin": 0.05, "gap": 1.5,  "cap300": 10, "learn_cap": 0.60},
    "Balanced": {"margin": 0.15, "gap": 4.0,  "cap300": 8,  "learn_cap": 0.40},
    "Gentle":   {"margin": 0.25, "gap": 10.0, "cap300": 6,  "learn_cap": None},
}


DEFAULT_RULES = {   # used until the first response tells us the real numbers (values from the live site)
    "search": [(5, 10, 60), (15, 60, 300), (30, 300, 600), (600, 21600, 3600)],
    "fetch":  [(12, 4, 10), (16, 12, 60), (50, 300, 600), (1000, 21600, 3600)],
    "other":  [(4, 10, 60), (10, 60, 300)],
}


COOLDOWN_AFTER_PENALTY = 900   # after a 429, stay extra careful for 15 minutes


def per_text(p):
    return f"{p}s" if p < 60 else f"{p // 60} min" if p < 3600 else f"{p // 3600} h"


def fmt_stamp(ts):
    """'Oct 11, 3:42 PM' in your local time."""
    if not ts:
        return ""
    d = datetime.fromtimestamp(ts)
    h = d.hour % 12 or 12
    return f"{d.strftime('%b')} {d.day}, {h}:{d.minute:02d} {'AM' if d.hour < 12 else 'PM'}"


def rl_log(text):
    try:
        with open(P("rate_limit_log.txt"), "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass


class Limiter:
    def __init__(self):
        self.lock = threading.RLock()
        self.rules = {k: list(v) for k, v in DEFAULT_RULES.items()}
        self.hits = {k: [] for k in DEFAULT_RULES}
        self.last = {k: 0.0 for k in DEFAULT_RULES}
        self.blocked_until = 0.0
        self.cooldown_until = 0.0
        self.wait_until, self.wait_reason = 0.0, ""
        self.penalties = 0
        self.extra_margin = 0.0                      # grows with every penalty and never shrinks during a session
        self.seen_rules = {}
        self.recent = collections.deque(maxlen=40)   # last requests with what the server said - dumped on a 429
        self.saved_at = 0.0
        self.last_penalty = 0.0
        self.started = time.time()
        self.sent_total = 0
        self._load()

    # ---- remember the request history and penalty clock across restarts (rate_state.json)
    def _load(self):
        d = load_json("rate_state.json", {})
        now = time.time()
        try:
            for cls in self.hits:
                self.hits[cls] = [t for t in d.get("hits", {}).get(cls, []) if now - t < 21600]
            self.blocked_until = float(d.get("blocked_until", 0))
            self.cooldown_until = float(d.get("cooldown_until", 0))
            self.last_penalty = float(d.get("last_penalty", 0))
            self.penalties = int(d.get("penalties", 0)) if now - self.last_penalty < 86400 else 0
            self.extra_margin = float(d.get("extra_margin", 0)) if now - self.last_penalty < 86400 else 0.0
            for cls in self.hits:
                if self.hits[cls]:
                    self.last[cls] = max(self.hits[cls])
        except Exception:
            pass

    def _save(self, force=False):
        now = time.time()
        if not force and now - self.saved_at < 5:
            return
        self.saved_at = now
        with self.lock:
            data = {"hits": {k: [t for t in v if now - t < 21600] for k, v in self.hits.items()},
                    "blocked_until": self.blocked_until, "cooldown_until": self.cooldown_until,
                    "penalties": self.penalties, "extra_margin": self.extra_margin, "last_penalty": self.last_penalty}
        save_json("rate_state.json", data)

    @staticmethod
    def cls_of(method, url):
        return "search" if "/search/" in url else "fetch" if "/fetch/" in url else "other"

    def _pace(self):
        pc = dict(PACES.get(SETTINGS.get("pace"), PACES["Balanced"]))
        pc["margin"] += self.extra_margin
        if time.time() < self.cooldown_until:           # recently penalised: slower and with a bigger safety margin
            pc["margin"] += 0.15
            pc["gap"] *= 2
        pc["margin"] = min(0.6, pc["margin"])
        pc["cap300"] = max(3, pc["cap300"] - self.penalties)
        return pc

    def _window(self, cls, period, now):
        return sorted(t for t in self.hits[cls] if now - t < period)

    def _need_wait(self, cls, now):
        pc = self._pace()
        gap = pc["gap"] if cls == "search" else 1.0
        wait, why = self.last[cls] + gap - now, "pacing"
        for mx, period, _pen in self.rules[cls]:
            allowed = max(1, mx - max(1, math.ceil(mx * pc["margin"])))
            if period == 300 and cls in ("search", "fetch"):
                allowed = min(allowed, pc["cap300"])
            win = self._window(cls, period, now)
            if len(win) + 1 > allowed:
                need = len(win) - allowed + 1
                w = win[need - 1] + period - now + 0.3
                if w > wait:
                    wait, why = w, f"{cls} limit {len(win)}/{mx} per {per_text(period)}"
        return wait, why

    def acquire(self, cls):
        """Block until one more request of this kind is safe, then reserve it."""
        while True:
            with self.lock:
                now = time.time()
                if now < self.blocked_until:
                    wait, why = self.blocked_until - now, "the trade site asked us to slow down"
                else:
                    wait, why = self._need_wait(cls, now)
                if wait <= 0:
                    self.hits[cls].append(now)
                    self.sent_total += 1
                    self.last[cls] = now
                    self._save()
                    self.wait_until, self.wait_reason = 0.0, ""
                    cut = now - 21700
                    self.hits[cls] = [t for t in self.hits[cls] if t > cut]
                    return
                self.wait_until, self.wait_reason = now + wait, why
            time.sleep(min(wait, 0.5))

    def update(self, cls, headers):
        """Learn the real limits and how much has been used from the response headers."""
        try:
            names = [x.strip() for x in headers.get("X-Rate-Limit-Rules", "").split(",") if x.strip()]
            if not names:
                return
            now = time.time()
            rules, states = {}, {}
            for n in names:
                for part in headers.get(f"X-Rate-Limit-{n}", "").split(","):
                    if part.count(":") == 2:
                        mx, per, pen = (int(x) for x in part.split(":"))
                        if per not in rules or mx < rules[per][0]:
                            rules[per] = (mx, per, pen)
                for part in headers.get(f"X-Rate-Limit-{n}-State", "").split(","):
                    if part.count(":") == 2:
                        cur, per, restricted = (int(x) for x in part.split(":"))
                        states[per] = max(states.get(per, (0, 0))[0], cur), max(states.get(per, (0, 0))[1], restricted)
            with self.lock:
                self.recent.append((now, cls, {k: v for k, v in headers.items() if k.lower().startswith("x-rate-limit")}))
                if rules:
                    self.rules[cls] = sorted(rules.values(), key=lambda r: r[1])
                    if self.seen_rules.get(cls) != self.rules[cls]:
                        self.seen_rules[cls] = list(self.rules[cls])
                        rl_log(f"limits the site reports for {cls}: " + ", ".join(f"{mx} per {per}s (penalty {pen}s)" for mx, per, pen in self.rules[cls]))
                prev = 0
                for per in sorted(states):
                    cur, restricted = states[per]
                    if restricted > 0:
                        self.blocked_until = max(self.blocked_until, now + restricted + 1)
                    own = len(self._window(cls, per, now))
                    if cur > own:       # hits we didn't make (another tool, an earlier session) - add as phantoms
                        stamp = now if prev == 0 else now - prev - 1
                        self.hits[cls].extend([stamp] * (cur - own))
                    prev = per
        except Exception:
            pass

    def log_429(self, cls, url, headers, retry_after, body=""):
        """Write down everything needed to see why we were limited: what we thought we'd used vs what the server said."""
        try:
            with self.lock:
                now = time.time()
                lines = [f"=== {time.strftime('%Y-%m-%d %H:%M:%S')}  429 on {cls}  ({url.split('/api/')[-1][:60]})  Retry-After {retry_after}s  [v{APP_VERSION}]",
                         f"    pace {SETTINGS.get('pace')}, extra margin {self.extra_margin:.2f}, penalties so far {self.penalties}",
                         f"    app running for {int(time.time() - self.started)}s, sent {self.sent_total} requests since it started; "
                         f"in the last 300s: search {len(self._window('search', 300, time.time()))}, fetch {len(self._window('fetch', 300, time.time()))}, other {len(self._window('other', 300, time.time()))}",
                         "    our own count per rule (hits/max per seconds): " +
                         ", ".join(f"{h}/{mx} per {per}s" for h, mx, per in self.usage(cls)),
                         "    ALL headers on the 429: " + "; ".join(f"{k}={v}" for k, v in headers.items()),
                         "    body on the 429: " + (body or "").replace("\n", " ")[:300]]
                for t, c, hd in list(self.recent)[-12:]:
                    st = "; ".join(f"{k}={v}" for k, v in hd.items() if k.lower().endswith("state"))
                    lines.append(f"    {now - t:6.1f}s ago  {c:6} {st}")
            rl_log("\n".join(lines))
        except Exception:
            pass

    def penalized(self, retry_after):
        with self.lock:
            self.extra_margin = min(0.4, self.extra_margin + 0.10)
            now = time.time()
            self.blocked_until = max(self.blocked_until, now + retry_after + 1)
            self.cooldown_until = self.blocked_until + COOLDOWN_AFTER_PENALTY
            self.penalties += 1
            self.last_penalty = now
        self._save(force=True)

    def usage(self, cls):
        """[(hits in window, max, period)] for every rule of this kind of request."""
        now = time.time()
        with self.lock:
            return [(len(self._window(cls, per, now)), mx, per) for mx, per, _ in self.rules[cls]]

    def usage_ratio(self, cls="search"):
        return max((h / mx for h, mx, _ in self.usage(cls)), default=0)

    def learn_ok(self):
        cap = PACES.get(SETTINGS.get("pace"), PACES["Balanced"])["learn_cap"]
        return bool(SETTINGS["learn"] and cap is not None and time.time() >= self.cooldown_until
                    and self.usage_ratio("search") < cap)

    def state(self):
        now = time.time()
        with self.lock:
            return {"blocked": max(0, self.blocked_until - now), "wait": max(0, self.wait_until - now),
                    "why": self.wait_reason, "cooldown": max(0, self.cooldown_until - now),
                    "penalties": self.penalties}


LIMITER = Limiter()


_STATUS_HOOK = [lambda s: None]     # the window puts its own function here


def STATUS(s):
    _STATUS_HOOK[0](s)


def call(method, url, **kw):
    cls = LIMITER.cls_of(method, url)
    for _ in range(6):
        LIMITER.acquire(cls)
        r = requests.request(method, url, headers=HEADERS, timeout=25, allow_redirects=False, **kw)
        hops = 0
        while r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location") and hops < 3:
            hops += 1                                   # follow redirects ourselves, KEEPING the method (POST must stay POST)
            url = requests.compat.urljoin(url, r.headers["Location"])
            r = requests.request(method, url, headers=HEADERS, timeout=25, allow_redirects=False, **kw)
        LIMITER.update(cls, r.headers)
        if r.status_code == 429:
            try:
                retry = int(r.headers.get("Retry-After", "60"))
            except ValueError:
                retry = 60
            LIMITER.log_429(cls, url, r.headers, retry, r.text)
            LIMITER.penalized(retry)
            STATUS(f"The trade site rate-limited {cls} requests (wait {retry}s) - pausing; details in rate_limit_log.txt")
            continue
        if r.status_code >= 400:
            note = f"{r.status_code} for {method} {url}  | server said: {r.text[:200].strip()!r}"
            try:
                with open(P("http_error_log.txt"), "a", encoding="utf-8") as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + note + f"  | headers: {dict(r.headers)}\n")
            except Exception:
                pass
            raise RuntimeError(note)
        return r.json()
    raise RuntimeError("Still rate limited - try again later.")
