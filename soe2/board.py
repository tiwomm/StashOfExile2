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


def image(iid, get=None):
    """2.78.0: a strat's atlas screenshot -> (True, JPEG bytes) / (False, why)."""
    if not configured():
        return False, "The community board isn't set up yet."
    import requests
    try:
        r = (get or requests.get)(f"{url()}/images/{int(iid)}", headers={"User-Agent": "StashOfExile2-board"},
                                  timeout=TIMEOUT)
    except Exception as e:
        return False, f"Couldn't reach the community board ({e.__class__.__name__})."
    if r.status_code != 200 or not r.content[:2] == b"\xff\xd8":
        return False, f"The board answered {r.status_code}."
    return True, r.content


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


def post(kind, data, based_on=None):
    body = {"kind": kind, "data": data}
    if based_on:
        body["based_on"] = int(based_on)                 # 2.85.0: a copy of another post credits it
    return call("POST", "/posts", body=body)


def update(pid, data, note=""):
    """Your own post. -> (True, {"post", "pending"?}): an Official post's change waits for reviewers (pending)."""
    return call("PUT", f"/posts/{pid}", body={"data": data, "note": note})


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


# ---------------------------------------------------------------- 2.85.0: versions, suggestions, reviewers
def me():
    return _keep_user(call("GET", "/me"))


def suggest(pid, data, note):
    """Suggest an edit to someone else's post: the author accepts or declines it."""
    return call("POST", f"/posts/{pid}/suggest", body={"data": data, "note": note})


def revisions(pid):
    """A post's History (its author and reviewers see suggested / waiting versions too)."""
    return call("GET", f"/posts/{pid}/revisions")


def inbox():
    """Suggestions waiting on your posts, and what became of yours."""
    return call("GET", "/me/inbox")


def rev_action(rid, action, why=""):
    """accept / decline (your post's suggestion), rollback (an old version of your post), withdraw (your own)."""
    return call("POST", f"/revisions/{rid}", body={"action": action, "why": why})


def review_queue():
    return call("GET", "/review")


def review_rev(rid, vote):
    return call("POST", f"/revisions/{rid}/review", body={"vote": vote})


def review_post(pid, vote):
    return call("POST", f"/posts/{pid}/review", body={"vote": vote})


def set_reviewer(on=True):
    return _keep_user(call("POST", "/auth/reviewer", body={"on": bool(on)}))


def admin_reviewer(user_id, on):
    return call("POST", f"/users/{user_id}/reviewer", body={"on": bool(on)})
