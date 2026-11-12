"""2.132.6 Shared lists (feedback: "allow people to publish their regex to the database, as well as favorites from the
trade site section ... similar to the one-liners"; "sorting for Official | Community | Mine"): the board side of Regex
favorites and trade-site Favorites - the three views, each copy once, Post, Upvote and Tags. Posting needs Community
data sharing and a community name, like strats."""
import tkinter as tk
from tkinter import ttk

from . import board as B
from . import buglog
from .config import load_json
from .style import C

VIEWS = ("Official", "Community", "Mine")
OFFICIAL_KEY = {"regex": "regex", "trade": "trade"}


def view_rows(view, mine, posts, official, key):
    """-> the rows for one view, each copy once: [{"data", "origin" ("mine" / "board" / "official"), "_post", "_i"}].
    mine: your local items; posts: board posts ({"data", ...}); official: the Official list's data; key(data) -> the
    text that makes two copies the same."""
    if view == "Official":
        pool = [{"data": p["data"], "origin": "board", "_post": p} for p in posts if p.get("promoted")] + \
               [{"data": d, "origin": "official"} for d in official]
    elif view == "Community":
        pool = [{"data": p["data"], "origin": "board", "_post": p} for p in posts if not p.get("promoted")]
    else:
        pool = [{"data": d, "origin": "mine", "_i": i} for i, d in enumerate(mine)] + \
               [{"data": p["data"], "origin": "board", "_post": p} for p in posts if p.get("mine")]
    seen, out = set(), []
    for r in pool:
        k = key(r["data"])
        if k and k not in seen:
            seen.add(k)
            out.append(r)
    return out


class SharePage:
    """Mixed into App."""

    def share_posts(self, kind):
        return (getattr(self, "_share_posts", {}) or {}).get(kind, [])

    def share_official(self, kind):
        d = getattr(self, "mm_official", None)
        if not isinstance(d, dict) or not d:
            d = load_json("board_official.json", {}) or {}
        return [x for x in d.get(OFFICIAL_KEY[kind]) or [] if isinstance(x, dict)]

    def share_fetch(self, kind, done=None):
        """The board's posts of this kind (in the background), then done()."""
        if not B.configured():
            return False

        def got(res):
            ok, d = res
            if ok and isinstance(d, dict):
                self._share_posts = dict(getattr(self, "_share_posts", {}) or {})
                self._share_posts[kind] = [p for p in d.get("posts") or [] if isinstance(p.get("data"), dict)]
            if done:
                done()
        self.run_bg(lambda: B.posts(kind, "top", limit=100), got)
        return True

    def share_post(self, kind, data, done=None):
        """Post one of yours (asks for sharing and a name first, as strats do)."""
        if not self.cm_need_sharing(lambda: self.share_post(kind, data, done)) or self.mm_need_login("post"):
            return None
        self.run_bg(lambda: B.post(kind, data), lambda r: self._share_result(r, kind, "Posted to the Community board.",
                                                                              done))
        return True

    def share_vote(self, kind, post, done=None):
        if not post:
            self._say("Upvotes are for Community posts.", 5)
            return None
        if self.mm_need_login("upvote"):
            return None
        self.run_bg(lambda: B.vote(post["id"], not post.get("voted")), lambda r: self._share_result(r, kind, None, done))
        return True

    def share_report(self, kind, post, done=None):
        from tkinter import simpledialog
        if not post or self.mm_need_login("report"):
            return None
        why = simpledialog.askstring("Report", "What's wrong with it?", parent=self.root)
        if why is not None:
            self.run_bg(lambda: B.report(post["id"], why), lambda r: self._share_result(r, kind, "Reported - thanks.",
                                                                                       done))

    def share_delete(self, kind, post, done=None):
        self.run_bg(lambda: B.delete(post["id"]), lambda r: self._share_result(r, kind, "Deleted.", done))

    def _share_result(self, res, kind, text, done):
        ok, d = res
        if not ok:
            self.app_toast(d, "Community")
            return False
        if text:
            self._say(text, 6)
        self.share_fetch(kind, done)
        return True

    def share_tags(self, title, tags, on_save):
        """A window of tag checkboxes (the strats' tag groups) -> on_save([tags])."""
        from . import moneymakers as MM
        w = tk.Toplevel(self.root)
        w.title("Tags")
        w.configure(bg=C["panel"])
        w.transient(self.root)
        P1 = C["panel"]
        tk.Label(w, text=title[:90], bg=P1, fg=C["text"], wraplength=420, justify="left",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(12, 8))
        have, picks = set(tags or []), {}
        box = tk.Frame(w, bg=P1)
        box.pack(fill="both", padx=12, pady=8)
        try:
            groups = MM.tag_groups()
        except Exception:
            buglog.caught()
            groups = dict(MM.TAG_GROUPS)
        for col, (g, names) in enumerate(groups.items()):
            f = tk.Frame(box, bg=P1)
            f.grid(row=0, column=col, sticky="nw", padx=(0, 16))
            tk.Label(f, text=g.upper(), bg=P1, fg=C["muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
            for t in names:
                v = tk.BooleanVar(value=t in have)
                picks[t] = v
                ttk.Checkbutton(f, text=t, variable=v).pack(anchor="w")

        def save():
            w.destroy()
            on_save([t for t, v in picks.items() if v.get()])
        btns = tk.Frame(w, bg=P1)
        btns.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(btns, text="Save", style="Primary.TButton", command=save).pack(side="right")
        ttk.Button(btns, text="Cancel", command=w.destroy).pack(side="right", padx=(0, 8))
        self.share_tags_win = w
        return w
