"""2.85.0: the community board's people side (feedback: "only allow author + admin to make edits", "Suggest Edits ->
change things, publish to community / moderation", "moderation ... opt-in community handled ... protections against
data poisoning", and "prompt a user once at startup for their chosen username ... permanent ... only be changed every
7 days").

  * Your community name: asked once at start-up (Money Makers, and anything else on the board, use it). It can change
    once every 7 days (the board checks).
  * Suggest an edit: someone else's strat opens in the editor; your version goes to its author with a note.
  * History: every version of a post - what changed (field by field), roll back (the author), withdraw (your own).
  * Inbox: suggestions waiting on your posts (Accept / Decline) and what became of yours.
  * Review queue (reviewers - opt in once your account is 14 days old with a post or 10 upvotes): changes to Official
    posts, suggestions whose author is away, reported posts with their reasons. Two reviewers (or an admin) decide.
Nothing here touches the game."""
import json
import threading
import time
import tkinter as tk

from .style import over_app
from tkinter import ttk

from . import board as B
from .config import SETTINGS, save_json
from .style import C

STATUS_WORDS = {"live": "live now", "old": "earlier version", "suggested": "suggested", "pending": "waiting for reviewers",
                "declined": "declined", "withdrawn": "withdrawn", "new": "new"}
FIELD_WORDS = {"thoughts_per_click": "Thinking", "clicks_per_hour": "Clicks per hour", "est_profit": "Est. profit / hour",
               "est_cost": "Est. cost / run", "waystone_tiers": "Waystone tiers", "craft_steps": "Craft steps",
               "setup": "Other setup", "atlas_image": "Atlas screenshot", "key_mods": "Key mods"}


def field_word(k):
    return FIELD_WORDS.get(k, k.replace("_", " ").capitalize())


def _show(v):
    if v is None or v == "" or v == []:
        return "(empty)"
    if isinstance(v, list):
        return "\n".join("• " + (x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def diff(old, new):
    """Two versions of a post -> [(field, before, after)] for the fields that differ (id / author / updated left out)."""
    old, new = old or {}, new or {}
    out = []
    for k in list(dict.fromkeys(list(old) + list(new))):
        if k in ("id", "author", "updated"):
            continue
        if old.get(k) != new.get(k):
            out.append((k, old.get(k), new.get(k)))
    return out


class BoardModPage:
    # ---------------------------------------------------------------- your community name (asked once)
    def board_name_check(self):
        """2.86.1: start-up, with a board name: the board may have reset it (a name its filter refuses) - then ask for
        a new one. The answer comes back through the app's event queue."""
        if not (B.configured() and B.signed_in()):
            return None                       # 2.94.0: no name asked at start - only when you do something that needs one
        threading.Thread(target=lambda: self.ui_q.put(("bm_me", B.me())), daemon=True).start()

    def ev_bm_me(self, res):
        ok, d = res
        if ok and hasattr(self, "cy_paint"):
            self.cy_paint()                                      # 2.95.0: your rep, fresh
        if ok and (d.get("user") or {}).get("name_reset"):
            self.board_name_prompt(force=True, reset=True)

    def board_name_prompt(self, force=False, reset=False):
        """Start-up: no community name yet - ask once (it's the name on Money Makers and any board feature).
        reset=True (2.86.1): the board reset a name its filter refuses - pick a new one (no 7-day wait)."""
        if not force and (SETTINGS.get("board_name_asked") or B.signed_in() or not B.configured()):
            return None
        SETTINGS["board_name_asked"] = True
        save_json("settings.json", SETTINGS)
        P2 = C["panel2"]
        win = tk.Toplevel(self.root, bg=P2, padx=16, pady=16)
        over_app(win, self.dlg_parent())               # 2.114.3: over the app, on its monitor
        win.title("Your community name")
        win.transient(self.root)
        self.bn_win = win
        tk.Label(win, text="Pick a new community name" if reset else "Pick your community name", bg=P2, fg=C["accent"],
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(win, text=("Your old name isn't allowed on the community board (slurs and hate words aren't), so it "
                            "was reset. Pick a new one - you can do it now." if reset else
                            "Other players see it on Money Makers strats, upvotes and edits. It's yours alone, and it "
                            "can change once every 7 days. No account or password - this PC keeps a key. Slurs and "
                            "hate words aren't allowed. Don't use your account or character name - keep the board "
                            "apart from who you are in game."),
                 bg=P2, fg=C["muted"], wraplength=380, justify="left", anchor="w").pack(fill="x", pady=(4, 8))
        var = tk.StringVar()
        ent = ttk.Entry(win, textvariable=var, width=30)
        ent.pack(fill="x")
        msg = tk.Label(win, text="2-24 letters, numbers, spaces, _ . or -", bg=P2, fg=C["muted"], anchor="w")
        msg.pack(fill="x", pady=(4, 8))
        row = tk.Frame(win, bg=P2)
        row.pack(fill="x")
        self.bn_var, self.bn_msg = var, msg

        def done(res):
            ok, d = res
            if not win.winfo_exists():
                return
            if ok:
                win.destroy()
                self._say(f"You're on the community board as {d.get('name', var.get())}.", 6)
                if hasattr(self, "mm_account_paint"):
                    self.mm_account_paint()
            else:
                msg.config(text=d, fg=C["red"])
                btn.state(["!disabled"])

        def save():
            name = var.get().strip()
            if len(name) < 2:
                return msg.config(text="At least 2 characters.", fg=C["red"])
            btn.state(["disabled"])
            msg.config(text="Saving…", fg=C["muted"])
            self._bm_bg(lambda: B.rename(name) if reset else B.join(name), done)
        btn = ttk.Button(row, text="Save my name", style="Primary.TButton", command=save)
        btn.pack(side="right")
        ttk.Button(row, text="Later", style="Quiet.TButton", command=win.destroy).pack(side="right", padx=(0, 8))
        ent.bind("<Return>", lambda e: save())
        win.bind("<Escape>", lambda e: win.destroy())
        self.bn_save = save
        ent.focus_set()
        return win

    def _bm_bg(self, work, done):
        """Network off the window thread (mm_sync = do it now, for tests)."""
        self.run_bg(work, done)

    def bm_next_rename(self):
        nxt = (B.signed_in() or {}).get("next_rename") or 0
        return time.strftime("%Y-%m-%d", time.localtime(nxt)) if nxt > time.time() else ""

    # ---------------------------------------------------------------- one small window with a list and a reading pane
    def _bm_window(self, title, key):
        old = getattr(self, key, None)
        if old is not None:
            try:
                old.destroy()
            except tk.TclError:
                pass
        P1 = C["panel"]
        win = tk.Toplevel(self.root, bg=P1)
        over_app(win, self.dlg_parent())               # 2.114.3: over the app, on its monitor
        win.title(title)
        win.transient(self.root)
        win.geometry("980x620")
        setattr(self, key, win)
        return win

    def _bm_text(self, parent):
        t = tk.Text(parent, bg=C["panel2"], fg=C["text"], relief="flat", wrap="word", font=("Segoe UI", 9),
                    padx=8, pady=8, highlightthickness=0)
        t.tag_configure("h", foreground=C["accent"], font=("Segoe UI", 9, "bold"), spacing1=8)
        t.tag_configure("old", foreground=C["red"])
        t.tag_configure("new", foreground=C["green"])
        t.tag_configure("muted", foreground=C["muted"])
        return t

    def bm_diff_into(self, t, old, new, head=""):
        t.config(state="normal")
        t.delete("1.0", "end")
        if head:
            t.insert("end", head + "\n", "muted")
        ch = diff(old, new)
        if not ch:
            t.insert("end", "\nNo differences from the version shown now.", "muted")
        for k, a, b in ch:
            t.insert("end", field_word(k) + "\n", "h")
            t.insert("end", "− " + _show(a).replace("\n", "\n  ") + "\n", "old")
            t.insert("end", "+ " + _show(b).replace("\n", "\n  ") + "\n", "new")
        t.config(state="disabled")
        return ch

    # ---------------------------------------------------------------- Suggest an edit
    def mm_suggest(self):
        s = self.mm_current() if hasattr(self, "mm_current") else None
        post = (s or {}).get("_post")
        if not post or post.get("mine") or self.mm_need_login("suggest an edit"):
            return None
        return self.mm_form(dict(s), suggest=True)

    def bm_send_suggestion(self, post, data, note):
        ok, d = B.suggest(post["id"], data, note)
        if ok:
            self._say(f"Sent to {post.get('author', {}).get('name', 'its author')} - they'll accept or decline it "
                      "(Inbox shows what happens).", 10)
        return ok, d

    # ---------------------------------------------------------------- History
    def bm_history(self, post=None):
        s = self.mm_current() if post is None and hasattr(self, "mm_current") else None
        post = post or (s or {}).get("_post")
        if not post:
            return None
        win = self._bm_window(f"History · {post['data'].get('name', '')}", "bm_hist_win")
        P1 = C["panel"]
        top = tk.Frame(win, bg=P1, padx=8, pady=8)
        top.pack(fill="x")
        msg = tk.Label(top, text="Loading…", bg=P1, fg=C["muted"], anchor="w")
        msg.pack(side="left", fill="x", expand=True)
        pw = tk.PanedWindow(win, orient="horizontal", bg=P1, sashwidth=4)
        pw.pack(fill="both", expand=True)
        left = tk.Frame(pw, bg=P1)
        tv = ttk.Treeview(left, columns=("when", "by", "status"), show="headings", selectmode="browse")
        for c, w, txt in (("when", 110, "When"), ("by", 110, "By"), ("status", 140, "Status")):
            tv.heading(c, text=txt)
            tv.column(c, width=w, stretch=c == "status")
        tv.pack(fill="both", expand=True)
        pw.add(left, width=380)
        right = tk.Frame(pw, bg=P1)
        t = self._bm_text(right)
        t.pack(fill="both", expand=True)
        btns = tk.Frame(right, bg=P1, padx=8, pady=8)
        btns.pack(fill="x")
        pw.add(right)
        self.bm_hist_tv, self.bm_hist_text, self.bm_hist_msg = tv, t, msg
        state = {"revs": [], "live": post}

        def fill(res):
            ok, d = res
            if not ok:
                return msg.config(text=d, fg=C["red"])
            state["revs"], state["live"] = d.get("revisions") or [], d.get("live") or post
            tv.delete(*tv.get_children())
            for r in state["revs"]:
                tv.insert("", "end", iid=str(r["id"]), values=(time.strftime("%Y-%m-%d %H:%M", time.localtime(r["created"])),
                                                               r["author"]["name"], STATUS_WORDS.get(r["status"], r["status"])))
            msg.config(text=f"{len(state['revs'])} version{'s' if len(state['revs']) != 1 else ''}. Pick one to see what "
                            "it changes compared with the live version.", fg=C["muted"])
            if state["revs"]:
                tv.selection_set(str(state["revs"][0]["id"]))

        def picked(_e=None):
            sel = tv.selection()
            r = next((x for x in state["revs"] if str(x["id"]) == (sel[0] if sel else "")), None)
            for w in btns.winfo_children():
                w.destroy()
            if not r:
                return
            self.bm_diff_into(t, state["live"]["data"], r["data"],
                              f"{STATUS_WORDS.get(r['status'], r['status'])} · by {r['author']['name']}"
                              + (f" · “{r['note']}”" if r.get("note") else "") + (f" · why: {r['why']}" if r.get("why") else ""))
            mine_post = state["live"].get("mine") or (B.signed_in() or {}).get("admin")
            acts = []
            if r["status"] == "old" and mine_post:
                acts.append(("Roll back to this version", "rollback"))
            if r["status"] == "suggested" and mine_post:
                acts += [("Accept", "accept"), ("Decline", "decline")]
            if r["status"] in ("suggested", "pending") and r.get("mine"):
                acts.append(("Withdraw", "withdraw"))
            for label, act in acts:
                ttk.Button(btns, text=label, style="Primary.TButton" if act in ("accept", "rollback") else "TButton",
                           command=lambda a=act, rr=r: self.bm_rev_act(rr, a, after=lambda: self._bm_bg(
                               lambda: B.revisions(post["id"]), fill))).pack(side="left", padx=(0, 8))
        tv.bind("<<TreeviewSelect>>", picked)
        self.bm_hist_pick = picked
        self._bm_bg(lambda: B.revisions(post["id"]), fill)
        return win

    def bm_rev_act(self, rev, action, after=None, why=""):
        if action == "decline" and not why:
            from tkinter import simpledialog
            why = simpledialog.askstring("Decline", "Why? (optional - the one who suggested it sees this)",
                                         parent=self.root) or ""

        def done(res):
            ok, d = res
            if not ok:
                return self.app_toast(d, "Community")
            st = d.get("status")
            self._say({"live": "Done - it's live now.", "pending": "Done - it waits for 2 reviewers (it's an Official "
                       "post).", "declined": "Declined."}.get(st, "Done."), 8)
            if hasattr(self, "mm_board_fetch"):
                self.mm_board_fetch()
            if after:
                after()
        self._bm_bg(lambda: B.rev_action(rev["id"], action, why), done)

    # ---------------------------------------------------------------- Inbox
    def bm_inbox(self):
        if self.mm_need_login("see your inbox"):
            return None
        win = self._bm_window("Community inbox", "bm_inbox_win")
        P1 = C["panel"]
        msg = tk.Label(win, text="Loading…", bg=P1, fg=C["muted"], anchor="w", padx=8, pady=8)
        msg.pack(fill="x")
        pw = tk.PanedWindow(win, orient="horizontal", bg=P1, sashwidth=4)
        pw.pack(fill="both", expand=True)
        left = tk.Frame(pw, bg=P1)
        tv = ttk.Treeview(left, columns=("strat", "who", "status"), show="tree headings", selectmode="browse")
        tv.heading("#0", text="")
        tv.column("#0", width=150)
        for c, w, txt in (("strat", 170, "Strat"), ("who", 100, "By"), ("status", 120, "Status")):
            tv.heading(c, text=txt)
            tv.column(c, width=w)
        tv.pack(fill="both", expand=True)
        pw.add(left, width=520)
        right = tk.Frame(pw, bg=P1)
        t = self._bm_text(right)
        t.pack(fill="both", expand=True)
        btns = tk.Frame(right, bg=P1, padx=8, pady=8)
        btns.pack(fill="x")
        pw.add(right)
        self.bm_inbox_tv, self.bm_inbox_text = tv, t
        state = {"rows": {}, "live": {}}

        def fill(res):
            ok, d = res
            if not ok:
                return msg.config(text=d, fg=C["red"])
            tv.delete(*tv.get_children())
            state["rows"].clear()
            a = tv.insert("", "end", iid="sug", text="On your posts", open=True)
            b = tv.insert("", "end", iid="mine", text="Yours", open=True)
            for r in d.get("suggestions") or []:
                state["rows"][f"s{r['id']}"] = r
                tv.insert(a, "end", iid=f"s{r['id']}", values=(r.get("post_name") or "?", r["author"]["name"], "waiting for you"))
            for r in d.get("mine") or []:
                state["rows"][f"m{r['id']}"] = r
                tv.insert(b, "end", iid=f"m{r['id']}", values=(r.get("post_name") or "?", r.get("post_author") or "",
                                                               STATUS_WORDS.get(r["status"], r["status"])))
            n = len(d.get("suggestions") or [])
            msg.config(text=f"{n} suggestion{'s' if n != 1 else ''} waiting on your posts." if n else
                       "Nothing waiting on your posts.", fg=C["muted"])
            self.bm_inbox_n = n

        def picked(_e=None):
            sel = tv.selection()
            r = state["rows"].get(sel[0] if sel else "")
            for w in btns.winfo_children():
                w.destroy()
            if not r:
                return

            def show(res):
                ok, d = res
                live = (d.get("post") or {}).get("data") if ok else {}
                self.bm_diff_into(t, live, r["data"], f"{r.get('post_name')} · by {r['author']['name']}"
                                  + (f" · “{r['note']}”" if r.get("note") else "") + (f" · why: {r['why']}" if r.get("why") else ""))
            self._bm_bg(lambda: B.call("GET", f"/posts/{r['post_id']}"), show)
            reload = lambda: self._bm_bg(B.inbox, fill)  # noqa: E731
            if sel[0].startswith("s"):
                ttk.Button(btns, text="Accept", style="Primary.TButton",
                           command=lambda: self.bm_rev_act(r, "accept", reload)).pack(side="left", padx=(0, 8))
                ttk.Button(btns, text="Decline", command=lambda: self.bm_rev_act(r, "decline", reload)).pack(side="left")
            elif r["status"] in ("suggested", "pending"):
                ttk.Button(btns, text="Withdraw", command=lambda: self.bm_rev_act(r, "withdraw", reload)).pack(side="left")
        tv.bind("<<TreeviewSelect>>", picked)
        self.bm_inbox_fill = fill
        self._bm_bg(B.inbox, fill)
        return win

    # ---------------------------------------------------------------- reviewers
    def bm_reviewer(self, on=True):
        if self.mm_need_login("review"):
            return None

        def done(res):
            ok, d = res
            if not ok:
                return self.app_toast(d, "Community")
            self._say("You're a reviewer now - the Review queue: Settings › Privacy & community." if on else
                      "You've stopped reviewing.", 8)
            self.mm_account_paint()
        self._bm_bg(lambda: B.set_reviewer(on), done)

    def bm_review_queue(self):
        me = B.signed_in() or {}
        if not (me.get("reviewer") or me.get("admin")):
            return self.app_toast("Become a reviewer first: Settings › Privacy & community.", "Community")
        win = self._bm_window("Review queue", "bm_rq_win")
        P1 = C["panel"]
        msg = tk.Label(win, text="Loading…", bg=P1, fg=C["muted"], anchor="w", padx=8, pady=8, justify="left")
        msg.pack(fill="x")
        pw = tk.PanedWindow(win, orient="horizontal", bg=P1, sashwidth=4)
        pw.pack(fill="both", expand=True)
        left = tk.Frame(pw, bg=P1)
        tv = ttk.Treeview(left, columns=("what", "by", "votes"), show="tree headings", selectmode="browse")
        tv.heading("#0", text="")
        tv.column("#0", width=140)
        for c, w, txt in (("what", 200, "Strat"), ("by", 100, "By"), ("votes", 90, "Votes")):
            tv.heading(c, text=txt)
            tv.column(c, width=w)
        tv.pack(fill="both", expand=True)
        pw.add(left, width=540)
        right = tk.Frame(pw, bg=P1)
        t = self._bm_text(right)
        t.pack(fill="both", expand=True)
        btns = tk.Frame(right, bg=P1, padx=8, pady=8)
        btns.pack(fill="x")
        pw.add(right)
        self.bm_rq_tv, self.bm_rq_text = tv, t
        state = {"rows": {}}

        def fill(res):
            ok, d = res
            if not ok:
                return msg.config(text=d, fg=C["red"])
            tv.delete(*tv.get_children())
            state["rows"].clear()
            a = tv.insert("", "end", iid="revs", text="Changes", open=True)
            b = tv.insert("", "end", iid="reps", text="Reported", open=True)
            for r in d.get("revisions") or []:
                state["rows"][f"r{r['id']}"] = ("rev", r)
                tv.insert(a, "end", iid=f"r{r['id']}", values=(r.get("post_name") or "?", r["author"]["name"],
                                                               f"✔{r['approvals']} ✖{r['rejections']}"))
            for p in d.get("reported") or []:
                state["rows"][f"p{p['id']}"] = ("post", p)
                v = p.get("votes") or {}
                tv.insert(b, "end", iid=f"p{p['id']}", values=(p["data"].get("name", "?"), p["author"]["name"],
                                                               f"⚑{p.get('reports', 0)} hide {v.get('hide', 0)} keep {v.get('keep', 0)}"))
            msg.config(text="Two reviewers (or an admin) decide each one. Never your own posts or versions. Check the "
                            "numbers and steps: does the change make the strat better and true?", fg=C["muted"])

        def picked(_e=None):
            sel = tv.selection()
            row = state["rows"].get(sel[0] if sel else "")
            for w in btns.winfo_children():
                w.destroy()
            if not row:
                return
            kind, r = row
            reload = lambda: self._bm_bg(B.review_queue, fill)  # noqa: E731
            if kind == "rev":
                def show(res):
                    ok, d = res
                    live = (d.get("post") or {}).get("data") if ok else {}
                    self.bm_diff_into(t, live, r["data"], f"{r.get('post_name')} (by {r.get('post_author')}) · change by "
                                      f"{r['author']['name']}" + (f" · “{r['note']}”" if r.get("note") else ""))
                self._bm_bg(lambda: B.call("GET", f"/posts/{r['post_id']}"), show)
                for label, v in (("Approve", "approve"), ("Reject", "reject")):
                    ttk.Button(btns, text=label, style="Primary.TButton" if v == "approve" else "TButton",
                               command=lambda v=v: self._bm_bg(lambda: B.review_rev(r["id"], v),
                                                               lambda res: (self.bm_vote_said(res), reload()))).pack(
                        side="left", padx=(0, 8))
            else:
                t.config(state="normal")
                t.delete("1.0", "end")
                t.insert("end", f"{r['data'].get('name')} by {r['author']['name']}\n", "h")
                t.insert("end", "Reasons given:\n", "muted")
                for why in r.get("reasons") or ["(none written)"]:
                    t.insert("end", "• " + why + "\n")
                t.insert("end", "\n" + (r["data"].get("summary") or "") + "\n")
                t.config(state="disabled")
                for label, v in (("Hide it", "hide"), ("Keep it (clear the reports)", "keep")):
                    ttk.Button(btns, text=label, command=lambda v=v: self._bm_bg(lambda: B.review_post(r["id"], v),
                                                                                lambda res: (self.bm_vote_said(res), reload()))).pack(
                        side="left", padx=(0, 8))
        tv.bind("<<TreeviewSelect>>", picked)
        self.bm_rq_fill = fill
        self._bm_bg(B.review_queue, fill)
        return win

    def bm_vote_said(self, res):
        ok, d = res
        if not ok:
            return self.app_toast(d, "Community")
        st = d.get("status")
        if st == "live":
            self._say("Approved - the change is live.", 6)
        elif st == "declined":
            self._say("Rejected.", 6)
        elif "hidden" in d:
            self._say("Hidden." if d["hidden"] else "Kept - its reports were cleared.", 6)
        else:
            self._say("Your vote is in - one more reviewer decides it.", 6)
        if hasattr(self, "mm_board_fetch"):
            self.mm_board_fetch()
