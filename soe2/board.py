"""The Money Makers community board (2.30.0): talks to the board server (board/ - a Cloudflare Worker).

No logins: the first time you post, vote or report, the app joins the board with a display name and keeps the key
it gets back (board_session.json in the data folder), sent as "Authorization: Bearer ...". Admins type the board's
admin key once (Become admin).
Every call returns (ok, data or error text) and never raises, so a server that's down never breaks the window."""
import time

from .config import SETTINGS, load_json, save_json

# The live board's address normally comes from the shared strat file (board/url.txt -> moneymakers.json).
BOARD_URL = ""
SESSION = "board_session.json"
TIMEOUT = 15


def url():
    """Settings "board_url" (tests / your own server) > the address in the shared strat file (board/url.txt on
    GitHub - so the board can be switched on or moved without a new release) > BOARD_URL."""
    if "board_url" in SETTINGS:
        return (SETTINGS.get("board_url") or "").rstrip("/")
    try:
        from .moneymakers import shared
        live = shared().get("board_url") or ""
    except Exception:
        live = ""
    return (live or BOARD_URL or "").rstrip("/")


def configured():
    return bool(url())


def session():
    d = load_json(SESSION, {})
    return d if isinstance(d, dict) and d.get("token") else {}


def signed_in():
    return session().get("user")


def sign_out():
    s = session()
    if s:
        call("POST", "/auth/logout")
    save_json(SESSION, {})


def call(method, path, params=None, body=None, get=None):
    """-> (True, json) or (False, "why it didn't work")."""
    if not configured():
        return False, "The community board isn't set up yet."
    import requests
    tok = session().get("token")
    headers = {"User-Agent": "StashOfExile2-board"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    try:
        r = (get or requests.request)(method, url() + path, params=params, json=body, headers=headers, timeout=TIMEOUT)
    except Exception as e:
        return False, f"Couldn't reach the community board ({e.__class__.__name__}). Check your internet."
    try:
        data = r.json()
    except Exception:
        data = {}
    if r.status_code == 401 and tok and path != "/auth/logout":
        save_json(SESSION, {})                                # the key stopped working (expired / banned)
        return False, "Your board account isn't valid any more - join again with a name."
    if r.status_code >= 400:
        return False, data.get("error") or f"The board answered {r.status_code}."
    return True, data


# ---------------------------------------------------------------- joining (no login)
def join(name):
    """-> (True, user) or (False, why). Keeps the key the board hands out."""
    ok, d = call("POST", "/auth/join", body={"name": name})
    if ok and d.get("token"):
        save_json(SESSION, {"token": d["token"], "user": d.get("user") or {}, "since": time.time()})
        return True, d.get("user") or {}
    return False, d if not ok else "The board didn't answer."


def _keep_user(res):
    ok, d = res
    if ok and d.get("user"):
        s = session()
        s["user"] = d["user"]
        save_json(SESSION, s)
    return res


def rename(name):
    return _keep_user(call("POST", "/auth/rename", body={"name": name}))


def become_admin(key):
    return _keep_user(call("POST", "/auth/admin", body={"key": key}))


# ---------------------------------------------------------------- posts
def posts(kind="strat", sort="top", **filters):
    params = {"kind": kind, "sort": sort}
    params.update({k: v for k, v in filters.items() if v not in (None, "", "Any", "All", False)})
    for k in ("hidden", "reported", "mine"):
        if filters.get(k):
            params[k] = "1"
    return call("GET", "/posts", params)


def post(kind, data):
    return call("POST", "/posts", body={"kind": kind, "data": data})


def update(pid, data):
    return call("PUT", f"/posts/{pid}", body={"data": data})


def delete(pid):
    return call("DELETE", f"/posts/{pid}")


def vote(pid, up=True):
    return call("POST", f"/posts/{pid}/vote", body={"up": bool(up)})


def report(pid, reason=""):
    return call("POST", f"/posts/{pid}/report", body={"reason": reason})


def admin(pid, action):
    return call("POST", f"/posts/{pid}/admin", body={"action": action})


def ban(user_id, banned=True):
    return call("POST", f"/users/{user_id}/ban", body={"banned": bool(banned)})


def official():
    """Posts an admin promoted - they join the Official list."""
    return call("GET", "/official")
