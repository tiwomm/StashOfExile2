"""2.89.2: never let personal details out. Error logs, problem reports and bug reports name files by their path, and
on Windows a path holds your user name (C:\\Users\\<you>\\...). scrub() swaps your home folder and user name for
neutral words before anything is written to a log or leaves the computer."""
import getpass
import os
import re


def _names():
    out = set()
    try:
        out.add(getpass.getuser())
    except Exception:
        pass
    for k in ("USERNAME", "USER", "LOGNAME"):
        if os.environ.get(k):
            out.add(os.environ[k])
    home = os.path.expanduser("~")
    if home and home != "~":
        out.add(os.path.basename(home.rstrip("\\/")))
    return {n for n in out if n and len(n) >= 2 and n.lower() not in ("root", "user", "admin", "public", "default")}


def scrub(text):
    """-> text with your home folder as ~ and your user name as <you> (any case, either slash)."""
    if not text:
        return text
    s = str(text)
    home = os.path.expanduser("~")
    for h in {home, home.replace("\\", "/"), home.replace("/", "\\")}:
        if h and h not in ("~", "/", "\\"):
            s = re.sub(re.escape(h), "~", s, flags=re.I)
    s = re.sub(r"([\\/](?:Users|home|Documents and Settings)[\\/])[^\\/\r\n\"']+", r"\1<you>", s, flags=re.I)
    for n in _names():
        s = re.sub(r"(?<![A-Za-z0-9])" + re.escape(n) + r"(?![A-Za-z0-9])", "<you>", s, flags=re.I)
    return s
