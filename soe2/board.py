"""The Money Makers community board (2.30.0): talks to the board server (board/ - a Cloudflare Worker).

No logins: the first time you post, vote or report, the app joins the board with a display name and keeps the key
it gets back (board_session.json in the data folder), sent as "Authorization: Bearer ...". Admins type the board's
admin key once (Become admin).
Every call returns (ok, data or error text) and never raises, so a server that's down never breaks the window."""
import re
import time

from .config import APP_UA, SETTINGS, load_json, save_json

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


ANON = ("/mods/", "/maps/", "/campaign/", "/bugs")      # 2.89.3: these never carry your board key - anonymous by design


def call(method, path, params=None, body=None, get=None):
    """-> (True, json) or (False, "why it didn't work")."""
    if not configured():
        return False, "The community board isn't set up yet."
    import requests
    tok = None if path.startswith(ANON) else session().get("token")
    headers = {"User-Agent": APP_UA, "X-SOE2": "1"}
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
        iid = str(iid)
        if not re.fullmatch(r"[0-9a-f]{32}", iid):           # 2.89.3: pictures have unguessable keys
            return False, "not a board picture"
        hd = {"User-Agent": APP_UA}
        tok = session().get("token")
        if tok:                                               # (your own / a reviewer's not-yet-shown picture)
            hd["Authorization"] = f"Bearer {tok}"
        r = (get or requests.get)(f"{url()}/images/{iid}", headers=hd, timeout=TIMEOUT)
    except Exception as e:
        return False, f"Couldn't reach the community board ({e.__class__.__name__})."
    if r.status_code != 200 or not r.content[:2] == b"\xff\xd8":
        return False, f"The board answered {r.status_code}."
    return True, r.content


# ---------------------------------------------------------------- joining (no login)
def join(name):
    """-> (True, user) or (False, why). Keeps the key the board hands out."""
    from .privacy import name_problem
    if name_problem(name):                                     # 2.89.3: never your account / a character's name
        return False, name_problem(name)
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
    from .privacy import name_problem
    if name_problem(name):                                     # 2.89.3
        return False, name_problem(name)
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


# ---------------------------------------------------------------- 2.86.0: global leaderboards
def lb_send(entries):
    """Your best times (leaderboard.payload). -> (True, {"kept", "refused"}); the board takes one batch per 10 min."""
    return call("POST", "/lb", body={"entries": entries})


def lb_keys(cat, league="", cls=""):
    return call("GET", "/lb", {k: v for k, v in (("cat", cat), ("league", league), ("cls", cls)) if v})


def lb_board(cat, key, league="", cls="", limit=100):
    return call("GET", "/lb", {k: v for k, v in (("cat", cat), ("key", key), ("league", league), ("cls", cls),
                                                  ("limit", limit)) if v})


def lb_report(lid, reason=""):
    return call("POST", f"/lb/{lid}/report", body={"reason": reason})


def lb_review(lid, vote):
    return call("POST", f"/lb/{lid}/review", body={"vote": vote})


def lb_forget():
    return call("DELETE", "/lb/mine")


KEY_KIND = "soe2-community-key"


def export_key(path):
    """2.94.0: this PC's board key to a file (to move your community name to another PC). -> (ok, why)."""
    import json
    s = session()
    if not s.get("token"):
        return False, "There's no community name on this PC yet."
    data = {"kind": KEY_KIND, "token": s["token"], "name": (s.get("user") or {}).get("name", "")}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError as e:
        return False, f"Couldn't write the file ({e.strerror or e})."
    return True, ""


def import_key(path):
    """2.94.0: a key file from export_key -> this PC uses that community name. -> (ok, user or why)."""
    import json
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False, "That isn't a community key file."
    tok = data.get("token") if isinstance(data, dict) else None
    if not (isinstance(data, dict) and data.get("kind") == KEY_KIND and isinstance(tok, str)
            and re.fullmatch(r"[A-Za-z0-9_\-]{20,200}", tok)):
        return False, "That isn't a community key file."
    old = load_json(SESSION, {})
    save_json(SESSION, {"token": tok, "user": {"name": str(data.get("name") or "")[:24]}, "since": time.time()})
    ok, d = me()
    if not ok:
        save_json(SESSION, old if isinstance(old, dict) else {})         # the board doesn't know that key: keep yours
        return False, d if isinstance(d, str) else "The board doesn't know that key."
    return True, session().get("user") or {}


def person(name):
    """2.95.0: someone's contributor card -> (ok, {name, rep, from, since} or {name, hidden})."""
    from urllib.parse import quote
    return call("GET", "/people/" + quote(str(name), safe=""))


def set_rep(hidden=None, link=None, unlink=False):
    """2.95.0: show / hide your contributor icon; count this install's ratings toward your rep (link = its id) or stop."""
    body = {}
    if hidden is not None:
        body["hidden"] = bool(hidden)
    if unlink:
        body["link"] = None
    elif link:
        body["link"] = link
    res = call("POST", "/me/rep", body=body)
    if res[0]:
        me()                                                   # (keeps the saved user's rep fields fresh)
    return res


def admin_rep(name, pts):
    """2.95.0: an admin thanks someone with rep (a bug report that got fixed)."""
    return call("POST", "/admin/rep", body={"name": name, "pts": int(pts)})


def delete_me():
    """2.89.3: leave the board and delete everything of yours on it (name, posts, pictures, votes, times). -> (ok, d)"""
    ok, d = call("DELETE", "/me")
    if ok:
        save_json(SESSION, {})
    return ok, d
