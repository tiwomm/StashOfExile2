"""2.115.0: one bug log for the whole app (feedback: "we need one global bug logging system", and Report a bug should
carry any crash).

Everything that goes wrong lands in app_log.txt in the data folder, one entry each:
  * error   - an error the app caught and lived through (log_error, a button, a background job, saving a file)
  * crash   - the app closed by itself last time (from hangwatch's crash_report.txt)
  * freeze  - the app stopped responding (hang_report.txt)
  * slow    - a theme change slower than 1.5 s (slow_report.txt)
  * net     - the trade site / poe.ninja said no (an HTTP error, a rate limit)
Uncaught errors anywhere - the main thread, a background thread, a Tk callback - come here too (install()).

Privacy, the same for every entry: scrubbed (privacy.scrub_names - your Windows user name, account and character
names), every file path cut to its file name, code locations and short fixed words only - never items, prices, chat,
whispers or anything you typed. The file is capped (LIMIT; the older half moves to app_log.old.txt). Nothing is
sent: Report a bug shows you diagnostics() word for word and sends it only if you tick it and press Send."""
import os
import re
import sys
import threading
import time
import traceback

LIMIT = 512 * 1024              # app_log.txt over this: it moves to app_log.old.txt and a new one starts
REPEAT = 30.0                   # the same error again within this many seconds: written once
SEND_MAX = 12000                # the most Report a bug adds (the board takes 20,000 characters in all)
KINDS = ("error", "crash", "freeze", "slow", "net")
_LOCK = threading.Lock()
_SEEN = {}
_VERSION = ["?"]
_PATH = re.compile(r'(?:[A-Za-z]:)?(?:[\\/][^\\/\r\n"\'<>|:*?]+)+[\\/]([^\\/\r\n"\'<>|:*?]+)')


def _p(name):
    from .config import P
    return P(name)


def clean(text):
    """No folders (a path keeps only its file name) and no names (privacy.scrub_names)."""
    s = _PATH.sub(r"\1", str(text or ""))         # (folders first - then a name left anywhere else)
    try:
        from .privacy import scrub_names
        s = scrub_names(s)
    except Exception:
        pass
    return s


def record(kind, where, detail="", exc=None):
    """Add one entry. kind: one of KINDS; where: short fixed words ("Scan stash", "saving settings.json"); detail:
    more text (cleaned); exc: an exception (or True for the one being handled) - its traceback is added. Never
    raises. -> True when written (False for a repeat within REPEAT seconds)."""
    try:
        tb = ""
        if exc is True:
            tb = traceback.format_exc()
        elif isinstance(exc, BaseException):
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        body = clean((str(detail).rstrip() + "\n" if detail else "") + tb).rstrip()
        sig = (kind, where, (body.splitlines() or [""])[-1])
        with _LOCK:
            now = time.time()
            if now - _SEEN.get(sig, 0) < REPEAT:
                return False
            _SEEN[sig] = now
            path = _p("app_log.txt")
            try:
                if os.path.getsize(path) > LIMIT:
                    os.replace(path, _p("app_log.old.txt"))
            except OSError:
                pass
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')}  v{_VERSION[0]}  [{kind}]  {clean(where)}\n"
                        + (body + "\n" if body else ""))
        return True
    except Exception:
        return False


def install(root=None, version=None):
    """Catch what nothing else catches: errors on the main thread, on any background thread, and in Tk callbacks
    (buttons, timers) - each goes to the log (Tk's are shown in the status line by the app as before)."""
    if version:
        _VERSION[0] = version
    old = sys.excepthook

    def main_hook(t, v, tb):
        record("error", "uncaught (main thread)", exc=v.with_traceback(tb) if v is not None else None)
        try:
            old(t, v, tb)
        except Exception:
            pass
    sys.excepthook = main_hook

    def thread_hook(args):
        if args.exc_type is SystemExit:
            return
        name = getattr(args.thread, "name", "") or "a background job"
        record("error", f"uncaught in {re.sub(r'[^A-Za-z _-]', '', name)[:40] or 'a background job'}",
               exc=args.exc_value)
    threading.excepthook = thread_hook
    if root is not None:
        def tk_hook(t, v, tb):
            record("error", "a click or timer", exc=v.with_traceback(tb) if v is not None else None)
        root.report_callback_exception = tk_hook


def entries(text):
    """app_log.txt text -> [(header, body)], oldest first."""
    out, cur = [], None
    for ln in text.splitlines():
        if ln.startswith("--- "):
            cur = [ln, []]
            out.append(cur)
        elif cur is not None:
            cur[1].append(ln)
    return [(h, "\n".join(b)) for h, b in out]


def _read(name, limit=None):
    try:
        with open(_p(name), encoding="utf-8", errors="replace") as f:
            return f.read() if limit is None else f.read()[-limit:]
    except OSError:
        return ""


def counts(days=7):
    """{kind: how many} in the last `days` days (for the Report a bug form's line)."""
    cut = time.time() - days * 86400
    n = {}
    for h, _b in entries(_read("app_log.txt")):
        m = re.match(r"--- (\S+ \S+)\s+\S+\s+\[(\w+)\]", h)
        if not m:
            continue
        try:
            if time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")) < cut:
                continue
        except ValueError:
            continue
        n[m.group(2)] = n.get(m.group(2), 0) + 1
    return n


def diagnostics(limit=SEND_MAX):
    """What Report a bug adds when you tick it: the newest crash / freeze / slow reports (if from the last week) and
    the last entries of app_log.txt, newest first, cleaned again, at most `limit` characters."""
    parts = []
    week = time.time() - 7 * 86400
    for name, label in (("crash_report.txt", "Last crash"), ("hang_report.txt", "Last freeze"),
                        ("slow_report.txt", "Last slow theme change")):
        try:
            if os.path.getmtime(_p(name)) < week:
                continue
        except OSError:
            continue
        txt = clean(_read(name)).strip()
        if txt:
            parts.append(f"**{label}** ({name})\n```\n{txt[:3000]}\n```")
    log = entries(_read("app_log.txt", 200000))
    room = limit - sum(len(p) for p in parts) - 200
    keep = []
    for h, b in reversed(log):
        e = clean(h + ("\n" + b if b else ""))
        if len(e) + 1 > room:
            break
        keep.append(e)
        room -= len(e) + 1
    if keep:
        parts.append(f"**App log** (app_log.txt, the last {len(keep)}, newest first)\n```\n" + "\n".join(keep) + "\n```")
    return "\n\n".join(parts)[:limit] if parts else ""
