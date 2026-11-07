"""2.112.1: when the app stops responding, write down where - so a freeze that only happens on one PC can be fixed.

A tick on the Tk thread every half second; a watcher thread checks it. If the app hasn't ticked for 8 seconds, the
watcher looks at what the main thread is doing three times, two seconds apart, and writes it to hang_report.txt in
the app's data folder (one report, replaced by the next).

Privacy: only the app's own code locations are written - file NAME (no folders), function and line number, plus the
app version and the last few things the app was doing ("theme change", "overlay rebuild"). No user names, paths,
items, character names, chat or anything typed. Nothing is sent anywhere; you choose whether to share the file.
GGG ToS: reads nothing from the game."""
import os
import sys
import threading
import time

STALL = 8.0
_ST = {"tick": time.time(), "steps": [], "root": None, "written": 0.0}
_LOCK = threading.Lock()


def step(what):
    """Mark what the app is doing now (short, fixed words - never user data). Kept: the last 12."""
    with _LOCK:
        _ST["steps"].append((time.time(), str(what)[:60]))
        del _ST["steps"][:-12]
        _crash_steps()


def _tick():
    _ST["tick"] = time.time()
    root = _ST["root"]
    if root is not None:
        try:
            root.after(500, _tick)
        except Exception:
            pass


def _where(frame):
    """The main thread's stack, innermost last: 'file.py:function:line' - folders dropped."""
    out = []
    while frame is not None:
        co = frame.f_code
        out.append(f"{os.path.basename(co.co_filename)}:{co.co_name}:{frame.f_lineno}")
        frame = frame.f_back
    return list(reversed(out))[-25:]


def _watch(main_id, path, version):
    while True:
        time.sleep(1.0)
        stalled = time.time() - _ST["tick"]
        if stalled < STALL or time.time() - _ST["written"] < 60:
            continue
        samples = []
        for _ in range(3):
            fr = sys._current_frames().get(main_id)
            samples.append((round(time.time() - _ST["tick"], 1), _where(fr) if fr is not None else []))
            time.sleep(2.0)
        with _LOCK:
            steps = list(_ST["steps"])
        lines = [f"StashOfExile2 {version} - not responding report (code locations only)",
                 f"written {time.strftime('%Y-%m-%d %H:%M:%S')}", "", "Last things it was doing:"]
        lines += [f"  {time.strftime('%H:%M:%S', time.localtime(t))}  {w}" for t, w in steps] or ["  (none)"]
        for i, (secs, stack) in enumerate(samples, 1):
            lines += ["", f"Sample {i} - stuck for {secs} s:"] + [f"  {x}" for x in stack]
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except OSError:
            pass
        _log("freeze", "not responding", "\n".join(lines[2:]))        # 2.115.0: the one log too
        _ST["written"] = time.time()


# ---------------------------------------------------------------- 2.114.3: when the app closes by itself
# (feedback: switching to a theme closed the app on a friend's PC, and no file was written - the hang report only
# covers freezes). Python's faulthandler writes where it was when the process dies (Windows' "access violation" in
# Tk, an abort) to crash_raw.tmp; the next start turns that into crash_report.txt with file NAMES only (no folders,
# so no Windows user name), function and line, plus the last things the app was doing - then removes the raw file.
_CRASH = {"fh": None, "steps": None}
_FRAME = __import__("re").compile(r'File "(?P<f>[^"]+)", line (?P<l>\d+) in (?P<fn>[\w<>.]+)')


def _log(kind, where, text):
    """2.115.0: the same report in the app's one log (buglog) - Report a bug sends it from there."""
    try:
        from . import buglog
        buglog.record(kind, where, detail=text)
    except Exception:
        pass


def crash_scrub(raw, steps, version):
    """The raw faulthandler text -> the report's lines (code locations only), or [] when there's nothing to say."""
    import re
    lines, head = [], ""
    for ln in raw.splitlines():
        t = ln.strip()
        m = _FRAME.search(t)
        if m:
            name = re.split(r"[\\/]", m.group("f"))[-1]          # (either slash: no folder, no user name)
            lines.append(f"  {name}:{m.group('fn')}:{m.group('l')}")
        elif re.match(r"^(Windows fatal exception|Fatal Python error)\b", t) and not head:
            head = re.sub(r"[A-Za-z]:\\[^ ]*|/[^ ]*", "", t)[:120]       # (never a path)
        elif t.startswith(("Current thread", "Thread ")):
            lines.append("  " + ("main thread:" if "most recent call first" in t and not lines else "another thread:"))
    if not lines and not head:
        return []
    out = [f"StashOfExile2 {version} - the app closed by itself (code locations only)",
           f"written {time.strftime('%Y-%m-%d %H:%M:%S')}", "", head or "(no reason given)", "", "Last things it was doing:"]
    out += [f"  {s_}" for s_ in steps] or ["  (none)"]
    out += ["", "Where it was (innermost first):"] + lines
    return out


def crash_start(folder, version):
    """Turn a crash from last time into crash_report.txt (-> True when there was one), then start catching this
    run's. Never raises."""
    raw_p, steps_p = os.path.join(folder, "crash_raw.tmp"), os.path.join(folder, "crash_steps.tmp")
    was = False
    try:
        raw = open(raw_p, encoding="utf-8", errors="replace").read() if os.path.exists(raw_p) else ""
        steps = open(steps_p, encoding="utf-8").read().splitlines() if os.path.exists(steps_p) else []
        rep = crash_scrub(raw, steps, version) if raw.strip() else []
        if rep:
            with open(os.path.join(folder, "crash_report.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(rep) + "\n")
            _log("crash", "closed by itself last time", "\n".join(rep[3:]))
            was = True
    except Exception:
        pass
    try:
        import faulthandler
        _CRASH["fh"] = open(raw_p, "w", encoding="utf-8")
        faulthandler.enable(file=_CRASH["fh"], all_threads=True)
        _CRASH["steps"] = steps_p
        open(steps_p, "w", encoding="utf-8").close()
    except Exception:
        pass
    return was


def _crash_steps():
    """The last steps, on disk (a crash can't write them itself)."""
    p = _CRASH["steps"]
    if not p:
        return
    try:
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(f"{time.strftime('%H:%M:%S', time.localtime(t))}  {w}" for t, w in _ST["steps"]))
    except OSError:
        pass


def start(root, path, version):
    """Start watching (once). path: where the report goes (the data folder)."""
    if _ST["root"] is not None:
        return
    _ST["root"] = root
    _tick()
    t = threading.Thread(target=_watch, args=(threading.main_thread().ident, path, version), daemon=True,
                         name="hangwatch")
    t.start()


def profiled(label, fn, path, version, slow=1.5):
    """2.112.3: run fn(); if it takes longer than `slow` seconds, write where the time went to slow_report.txt (the
    data folder) - the 30 biggest steps as file NAME:function:line, how often and how long. Same privacy as the hang
    report: code locations only, nothing personal, never sent."""
    import cProfile
    import pstats
    pr = cProfile.Profile()
    t0 = time.time()
    pr.enable()
    try:
        return fn()
    finally:
        pr.disable()
        secs = time.time() - t0
        if secs >= slow:
            try:
                st = pstats.Stats(pr).stats
                rows = sorted(((ct, nc, f) for f, (_cc, nc, _tt, ct, _c) in st.items()), reverse=True)[:30]
                lines = [f"StashOfExile2 {version} - slow {label}: {secs:.1f} s (code locations only)",
                         f"written {time.strftime('%Y-%m-%d %H:%M:%S')}", "", "  seconds   calls  where"]
                for ct, nc, (fname, line, func) in rows:
                    lines.append(f"  {ct:7.2f} {nc:7d}  {os.path.basename(fname)}:{func}:{line}")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                _log("slow", f"slow {label} ({secs:.1f} s)", "\n".join(lines[3:15]))
            except Exception:
                pass
