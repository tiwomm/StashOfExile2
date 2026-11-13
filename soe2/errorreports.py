"""2.137.0: Error reports (feedback: "have error log data sent to the cloudflare server so we can automatically handle
bugs/issues ... debug stuff/errors/trade errors should go with it").

Off until you say yes - its own switch (Settings › Privacy & community › Error reports, "error_reports"; asked once
in the Feature Picker or, if that's done, once at start: "error_asked"). A no is final and never asked again.

Once an hour the app reads its own log (app_log.txt, already cleaned by buglog: no folders, no names) and sends the
community board one line per KIND of error, with how many times it happened since the last send:
  * kind   - error / crash / freeze / slow / net (trade site and other web errors) / caught / debug
  * place  - where in the code (file:function:line) or the log's short fixed words ("HTTP 400 trade search")
  * etype  - the error's type (ValueError) - never its message
  * frames - up to 6 code places (file:function:line) it passed through
  * msg    - trade site errors only: the site's short answer ("Unknown stat provided: explicit.stat_123")
Every field must match a narrow pattern (letters, digits, a few marks) or the line isn't sent. Never sent: error
messages, items, prices, chat, your names, file paths, the web address asked. Nothing is sent while it's off."""
import re
import threading

from .config import SETTINGS, load_json, save_json

STATE = "error_sent.json"        # {"last": newest log time sent, "sent": n}
EVERY = 3600
MAX_ITEMS = 50
KINDS = ("error", "crash", "freeze", "slow", "net", "caught", "debug")
_PLACE = re.compile(r"^[A-Za-z0-9 _.:()/'#,-]{1,80}$")
_TYPE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{0,60}$")
_FRAME = re.compile(r"^[A-Za-z0-9_.-]{1,40}:[A-Za-z0-9_<>.-]{1,60}:\d{1,6}$")
_MSG = re.compile(r"^[A-Za-z0-9 _.:,'()#/-]{0,120}$")
_HEAD = re.compile(r"^--- (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s+v(\S+)\s+\[(\w+)\]\s+(.*)$")
_TB = re.compile(r'File "([^"]+)", line (\d+), in (\S+)')
_SHORT = re.compile(r"^\s+([A-Za-z0-9_.-]{1,40}):([A-Za-z0-9_<>.-]{1,60}):(\d{1,6})\s*$")
_LAST = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]{0,60})(?::|$)")
_SITE_MSG = re.compile(r'"message"\s*:\s*"([^"]{1,200})"')
_lock = threading.Lock()

# What Settings and the question say - keep it TRUE: every field sent gets a line here.
WHAT = ("Off until you say yes. Sends what went wrong in the app - where in the code and the error's type - so it can "
        "be fixed. No names, items, chat or files.")
DETAILS = (
    ("Errors the app hit", "where in the code (file and line) and the error's type, like ValueError - never its "
     "message", "finding and fixing bugs, most often before anyone reports them"),
    ("Freezes and crashes", "the same: where it happened", "the same"),
    ("Trade site errors", "the error number and the site's short answer, like \"Unknown stat provided\" - never "
     "your search or the address", "fixing searches and teaching the app new mods"),
    ("How many times", "a count per kind of error since the last send, the app version and Windows or Linux",
     "fixing what hits the most people first"),
)


def on():
    return bool(SETTINGS.get("error_reports", False)) and bool(SETTINGS.get("error_asked"))


def asked():
    return bool(SETTINGS.get("error_asked"))


def set_on(value):
    SETTINGS["error_reports"] = bool(value)
    SETTINGS["error_asked"] = True
    save_json("settings.json", SETTINGS)


def _name(path):
    return re.split(r"[\\/]", path or "?")[-1]


def _endpoint(note):
    """The web address -> a fixed word for what was asked (never the address itself)."""
    n = note or ""
    for key, word in (("/trade2/search", "trade search"), ("/trade2/fetch", "trade fetch"),
                      ("/trade2/exchange", "trade exchange"), ("/trade2/data", "trade data"), ("/trade", "trade site"),
                      ("poe.ninja", "poe.ninja"), ("github", "GitHub"), ("workers.dev", "community board")):
        if key in n:
            return word
    return "web"


def item(header, body):
    """One app_log.txt entry -> (time, {kind, place, etype, frames, msg}) safe to send, or None."""
    m = _HEAD.match(header or "")
    if not m:
        return None
    when, kind, place = m.group(1), m.group(3), m.group(4).strip()
    if kind not in KINDS:
        return None
    lines = (body or "").splitlines()
    etype, frames, msg = "", [], ""
    if kind == "net":
        status = re.match(r"(HTTP \d{3}|rate limit)", place)
        place = (status.group(1) if status else "web") + " " + _endpoint(body)
        sm = _SITE_MSG.search(body or "")
        if sm:
            msg = re.sub(r"\s+", " ", sm.group(1)).strip()[:120]
            if not _MSG.match(msg):
                msg = ""
    elif kind == "debug":
        pass                                            # the place only: a debug entry's detail can hold anything
    else:
        for ln in lines:
            tm = _TB.search(ln)
            if tm:
                frames.append(f"{_name(tm.group(1))}:{tm.group(3)}:{tm.group(2)}")
                continue
            sm = _SHORT.match(ln)
            if sm:
                frames.append(f"{sm.group(1)}:{sm.group(2)}:{sm.group(3)}")
        for ln in reversed([x.strip() for x in lines if x.strip()]):
            if ln.startswith(("File ", "Traceback")) or _SHORT.match(" " + ln):
                continue
            lm = _LAST.match(ln)
            if lm and lm.group(1).split(".")[-1][:1].isupper():
                etype = lm.group(1)
            break
        frames = frames[-6:]
    it = {"kind": kind, "place": place[:80], "etype": etype, "frames": frames, "msg": msg}
    if not _PLACE.match(it["place"]) or (etype and not _TYPE.match(etype)) or not all(_FRAME.match(f) for f in frames):
        return None
    return when, it


def collect(text, since=""):
    """app_log.txt text -> (items to send, newest time) - one per kind of error, counted, newer than `since`."""
    from .buglog import entries
    pooled, newest = {}, since
    for h, b in entries(text or ""):
        hm = _HEAD.match(h or "")
        if not hm or (since and hm.group(1) <= since):
            continue
        newest = max(newest, hm.group(1))
        got = item(h, b)
        if not got:
            continue
        _when, it = got
        key = (it["kind"], it["place"], it["etype"], tuple(it["frames"]), it["msg"])
        if key in pooled:
            pooled[key]["n"] += 1
        else:
            pooled[key] = dict(it, n=1)
    return list(pooled.values())[:MAX_ITEMS], newest


def _os():
    import sys
    if sys.platform == "win32":
        import platform
        return "win" + re.sub(r"[^0-9.]", "", platform.release() or "")[:10]
    return "linux" if sys.platform.startswith("linux") else "mac"


def send(post=None):
    """One send (on a background thread). -> how many kinds were sent, or None when nothing went."""
    if not on():
        return None
    from . import board as B
    from . import buglog
    from .communitymods import cid
    if not B.configured():
        return None
    with _lock:
        st = load_json(STATE, {}) or {}
        items, newest = collect(buglog._read("app_log.txt", 400000), st.get("last", ""))
        if not items:
            return 0
        from .config import APP_VERSION
        body = {"cid": cid(), "v": str(APP_VERSION), "os": _os(), "items": items}
        ok, _res = (post or B.call)("POST", "/errors", body=body)
        if not ok:
            return None
        st["last"], st["sent"] = newest, int(st.get("sent", 0)) + len(items)
        save_json(STATE, st)
        return len(items)


def preview():
    """What the next send would carry, as text - Settings › What's sent shows this word for word."""
    from . import buglog
    st = load_json(STATE, {}) or {}
    items, _n = collect(buglog._read("app_log.txt", 400000), st.get("last", ""))
    if not items:
        return "Nothing to send - no new errors since the last send."
    out = []
    for it in items:
        bits = [f"[{it['kind']}] {it['place']}"]
        if it["etype"]:
            bits.append(it["etype"])
        if it["msg"]:
            bits.append(f"\"{it['msg']}\"")
        if it["frames"]:
            bits.append("< " + " < ".join(it["frames"]))
        out.append("  ".join(bits) + f"  x{it['n']}")
    return "\n".join(out)

