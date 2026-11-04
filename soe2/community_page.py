"""2.94.0: Settings › Privacy & community - one place for what leaves your PC and who you are when it does
(feedback: the community name lived in Money Makers, though the Leaderboards use it too).

  1. What leaves your PC: nothing, unless you turn something on below.
  2. Data sharing: the switches, each saying what is sent, why and where (the full table: "What's shared, and why?").
  3. Your community name: why you'd want one, what's stored, and everything you can do with it - pick / change it,
     inbox, reviewing, admin, move it to another PC, leave and delete.
  4. Your rights.

Money Makers and the Leaderboards keep a small 👤 chip that opens it. Nobody is asked for a name at start any more:
only when they do something that needs one (post, vote, report, share leaderboard times).
GGG ToS: nothing here touches the game."""
import tkinter as tk
from tkinter import ttk

from . import board as B
from . import rep as R
from .config import SETTINGS, save_json
from .style import C

PAGE = "Privacy & community"
NAME_WHY = ("Other players see it on what you post, vote on or edit on Money Makers, and beside your times on the "
            "Leaderboards. You only need one for those - price checks, the overlay and everything else never use it.")
NAME_STORED = ("Stored: the name, and a key on this PC (board_session.json in your data folder) - no email, no "
               "password, never your account or character name. The board keeps a scrambled internet address for "
               "daily limits only, deleted the next day.")
KEY_WARN = ("This file works like a password: anyone who has it can post as you. Keep it to yourself - don't upload, "
            "share or screenshot it. On the other PC: Settings › Privacy & community › Use a key file.")


def chip_text(me=None):
    me = B.signed_in() if me is None else me
    if not me:
        return "👤 Community name"
    return f"👤 {me.get('name', '?')}" + (" (admin)" if me.get("admin") else " (reviewer)" if me.get("reviewer") else "")


class CommunityPage:
    """Mixed into App."""

    def community_open(self):
        """The 👤 chips (Money Makers, Leaderboards) and every "pick a name" hint lead here."""
        self.open_settings_tab(PAGE)
        self.cy_paint()
        if B.configured() and B.signed_in():                     # 2.95.0: today's rep
            self._bm_bg(B.me, lambda _r: self.cy_paint())

    def build_privacy_community(self, section):
        P2 = C["panel2"]
        row = section(PAGE, "What leaves your PC", "Nothing, unless you turn something on below. Your wealth, items, "
                                                   "stash, account and character names never leave it.")
        ttk.Button(row, text="What's shared, and why?", style="Quiet.TButton",
                   command=lambda: self.cm_ask(info=True)).pack(side="left")
        # ---- data sharing
        from .communitymods import WHAT as CM_WHAT
        row = section(PAGE, "Data sharing", CM_WHAT + " You always get everyone else's data, sharing or not.")
        g = tk.Frame(row, bg=P2)
        g.pack(fill="x")
        self.cm_share_var = tk.BooleanVar(value=self.cm_sharing())
        self.cy_lb_var = tk.BooleanVar(value=bool(SETTINGS.get("lb_share", True)))
        items = ((self.cm_share_var, "Share anonymous data with the community", self.cm_share_changed,
                  "Mod prices and ratings, map ranks, campaign zones the guide doesn't know - to the StashOfExile2 "
                  "community server, for better prices and guides for everyone."),
                 (self.cy_lb_var, "Leaderboard times", self.cy_lb_switch,
                  "Your best map, boss, trial and act times (the day, not the time) under your community name - needs "
                  "data sharing on and a community name."))
        self.cy_rows = {}
        for i, (var, label, cmd, what) in enumerate(items):
            cb = ttk.Checkbutton(g, text=label, variable=var, command=cmd)
            cb.grid(row=i, column=0, sticky="nw", pady=2)
            tk.Label(g, text=what, bg=P2, fg=C["muted"], font=("Segoe UI", 9), justify="left", wraplength=520,
                     anchor="w").grid(row=i, column=1, sticky="w", padx=(12, 0), pady=2)
            self.cy_rows[label] = cb
        tk.Label(row, text="Coming later, off until you turn it on: the community FAQ.", bg=P2, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(8, 0))
        hr = tk.Frame(row, bg=P2)                                                               # 2.96.0
        hr.pack(fill="x", pady=(8, 0))
        ttk.Button(hr, text="Help rate mods…", command=lambda: self.rm_open()).pack(side="left")
        tk.Label(hr, text="One mod at a time - tunes your price checks, and earns rep when it matches everyone's.",
                 bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(8, 0))
        # ---- your community name
        row = section(PAGE, "Your community name", NAME_WHY)
        box = tk.Frame(row, bg=P2)
        box.pack(fill="x")
        self.cy_name_lbl = tk.Label(box, text="", bg=P2, fg=C["text"], font=("Segoe UI", 12, "bold"), anchor="w")
        self.cy_name_lbl.pack(fill="x")
        # 2.95.0: your rep and where it came from
        self.cy_rep_lbl = tk.Label(box, text="", bg=P2, fg=C["text"], font=("Segoe UI", 9), anchor="w", justify="left",
                                   wraplength=640)
        self.cy_rep_lbl.pack(fill="x", pady=(2, 0))
        self.cy_rep_sw = tk.Frame(box, bg=P2)
        self.cy_rep_sw.pack(fill="x", pady=(4, 0))
        tk.Label(box, text=NAME_STORED, bg=P2, fg=C["muted"], font=("Segoe UI", 9), justify="left", wraplength=640,
                 anchor="w").pack(fill="x", pady=(2, 8))
        self.cy_btns = tk.Frame(box, bg=P2)
        self.cy_btns.pack(fill="x")
        self.cy_msg = tk.Label(box, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left",
                               wraplength=640)
        self.cy_msg.pack(fill="x", pady=(8, 0))
        # ---- your rights
        row = section(PAGE, "Your rights", "Turn any switch off at any time: your leaderboard times come off at once. "
                                           "Leave and delete my data removes everything of yours from the board - "
                                           "name, strats, pictures, votes, suggestions and times.")
        tk.Label(row, text="The full privacy notes: TOS.md and README.md in the app's GitHub repository.", bg=P2,
                 fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(side="left")
        self.cy_paint()

    # ---------------------------------------------------------------- the name part
    def cy_paint(self):
        """Redraw the name, its buttons and every 👤 chip."""
        for b in (getattr(self, "mm_acct", None), getattr(self, "lb_acct", None)):
            if b is not None:
                try:
                    b.config(text=chip_text() + " ▾")
                except tk.TclError:
                    pass
        box = getattr(self, "cy_btns", None)
        if box is None:
            return
        try:
            for w in box.winfo_children():
                w.destroy()
        except tk.TclError:
            return
        me = B.signed_in()
        if not B.configured():
            self.cy_name_lbl.config(text="The community board isn't set up yet.")
            return
        self.cy_name_lbl.config(text=(f"You're {me.get('name', '?')}" + (" - admin" if me.get("admin") else
                                                                         " - reviewer" if me.get("reviewer") else ""))
                                if me else "No community name on this PC")
        self.cy_buttons = {}
        self.cy_rep_paint(me)

        def btn(text, cmd, primary=False, state="normal"):
            b = ttk.Button(box, text=text, command=cmd, style="Primary.TButton" if primary else "TButton")
            b.pack(side="left", padx=(0, 8), pady=2)
            if state != "normal":
                b.state(["disabled"])
            self.cy_buttons[text] = b
            return b
        if not me:
            btn("Pick a name…", lambda: self.mm_join("join the community board"), primary=True)
            btn("Use a key file…", self.cy_import_key)
            return
        nxt = self.bm_next_rename()
        btn("Change name…" + (f" (from {nxt})" if nxt else ""), self.mm_rename,
            state="disabled" if nxt and not me.get("admin") else "normal")
        btn("Inbox…", self.bm_inbox)
        if me.get("reviewer") or me.get("admin"):
            btn("Review queue…", self.bm_review_queue)
        if me.get("reviewer"):
            btn("Stop reviewing", lambda: self.bm_reviewer(False))
        elif not me.get("admin"):
            btn("Become a reviewer", self.bm_reviewer)
        if not me.get("admin"):
            btn("Become admin…", self.mm_admin_key)
        else:
            btn("Thank someone with rep…", self.cy_admin_rep)                    # 2.95.0: e.g. a fixed bug report
        btn("Move to another PC…", self.cy_export_key)
        btn("Leave and delete my data…", self.mm_leave)

    # ---------------------------------------------------------------- 2.95.0: rep
    def cy_rep_paint(self, me=None):
        me = B.signed_in() if me is None else me
        lbl, sw = getattr(self, "cy_rep_lbl", None), getattr(self, "cy_rep_sw", None)
        if lbl is None:
            return
        try:
            for w in sw.winfo_children():
                w.destroy()
        except tk.TclError:
            return
        if not me:
            lbl.config(text="Rep: karma-style points for helping - upvotes on your strats, accepted edits, reviews, "
                            "ratings that match the community. It shows as a small icon beside your name. Nothing "
                            "is locked behind it.")
            return
        rep = int(me.get("rep") or 0)
        t = R.tier(rep)
        f = me.get("rep_from") or {}
        parts = [f"{f[k]} {w}" for k, w in (("upvotes", "upvotes"), ("edits", "accepted edits"), ("reviews", "reviews"),
                                            ("ratings", "matching ratings"), ("bugs", "fixed bugs")) if f.get(k)]
        lbl.config(text=f"{'◆ ' if t else ''}{rep:,} rep" + (f" - from {', '.join(parts)}" if parts else
                   " - upvotes on your strats, accepted edits, reviews and ratings that match the community earn it."),
                   fg=t[1] if t else C["text"])
        self.cy_rep_show = tk.BooleanVar(value=not me.get("rep_hidden"))
        self.cy_rep_link = tk.BooleanVar(value=bool(me.get("rep_linked")))
        ttk.Checkbutton(sw, text="Show my contributor icon and card", variable=self.cy_rep_show,
                        command=lambda: self.cy_rep_set(hidden=not self.cy_rep_show.get())).pack(side="left")
        ttk.Checkbutton(sw, text="Count my mod ratings and map ranks", variable=self.cy_rep_link,
                        command=lambda: self.cy_rep_set(link=self.cy_rep_link.get())).pack(side="left", padx=(16, 0))
        tk.Label(sw, text="(ties this PC's anonymous ratings to your name on the server, only to count the ones that "
                          "match the community - never shown one by one)", bg=C["panel2"], fg=C["muted"],
                 font=("Segoe UI", 9), wraplength=320, justify="left").pack(side="left", padx=(8, 0))

    def cy_rep_set(self, hidden=None, link=None):
        from .communitymods import cid

        def work():
            if link is not None:
                return B.set_rep(link=cid() if link else None, unlink=not link)
            return B.set_rep(hidden=hidden)

        def done(res):
            ok, d = res
            if not ok:
                self.cy_say(d if isinstance(d, str) else "Couldn't save that.")
            R.forget()
            self.cy_paint()
        self._bm_bg(work, done)

    def cy_admin_rep(self, name=None, pts=None):
        from tkinter import simpledialog
        name = name or simpledialog.askstring("Thank someone with rep", "Their community name:", parent=self.root)
        if not name:
            return None
        pts = pts or simpledialog.askinteger("Thank someone with rep", "How much rep (1-50)? A fixed bug report: 10.",
                                             parent=self.root, minvalue=1, maxvalue=50, initialvalue=10)
        if not pts:
            return None

        def done(res):
            ok, d = res
            self.cy_say(f"Thanks sent: {name} has {d.get('rep', 0):,} rep now." if ok else d)
            R.forget()
        self._bm_bg(lambda: B.admin_rep(name, pts), done)
        return True

    # the icon beside a name: hover = the contributor card
    def rep_tree_hover(self, tv, name_of):
        """A Treeview whose first (#0) column holds the icon: hovering it shows that contributor's card."""
        def motion(e):
            name = name_of(tv.identify_row(e.y)) if tv.identify_column(e.x) == "#0" else None
            if not name:
                return self.rep_tip_hide()
            if getattr(self, "_rep_tip_name", None) != name:
                self.rep_tip_show(name, e.x_root + 14, e.y_root + 10)
        tv.bind("<Motion>", motion, add="+")
        tv.bind("<Leave>", lambda e: self.rep_tip_hide(), add="+")

    def rep_text_mark(self, t, author, base_tag):
        """In a Text: ◆ in the tier's color before a name (nothing when there's no rep, or it's hidden)."""
        tr = R.tier((author or {}).get("rep"))
        if not tr or not author.get("name"):
            return False
        tag = "rep_" + tr[0]
        t.tag_configure(tag, foreground=tr[1])
        name = author["name"]
        t.insert("end", "◆ ", (base_tag, tag, "rep_mark"))
        t.tag_bind(tag, "<Enter>", lambda e: self.rep_tip_show(name, e.x_root + 14, e.y_root + 10))
        t.tag_bind(tag, "<Leave>", lambda e: self.rep_tip_hide())
        return True

    def rep_tip_show(self, name, x, y):
        self.rep_tip_hide()
        self._rep_tip_name = name
        w = tk.Toplevel(self.root, bg=C["line"])
        w.overrideredirect(True)
        try:
            w.attributes("-topmost", True)
        except tk.TclError:
            pass
        lbl = tk.Label(w, text="Loading…", bg=C["panel2"], fg=C["text"], font=("Segoe UI", 9), justify="left",
                       padx=8, pady=8)
        lbl.pack(padx=1, pady=1)
        w.geometry(f"+{x}+{y}")
        self._rep_tip = w

        def done(ok, d):
            def paint():
                if getattr(self, "_rep_tip", None) is w and getattr(self, "_rep_tip_name", None) == name:
                    try:
                        lbl.config(text=R.card_text(d) if ok else str(d))
                    except tk.TclError:
                        pass
            try:
                self.root.after(0, paint)
            except (RuntimeError, tk.TclError):
                pass
        R.card(name, done, sync=bool(getattr(self, "mm_sync", False)))
        return w

    def rep_tip_hide(self):
        w, self._rep_tip, self._rep_tip_name = getattr(self, "_rep_tip", None), None, None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def cy_lb_switch(self):
        """Leaderboard times on / off (the same switch as Leaderboards › Share my times)."""
        on = bool(self.cy_lb_var.get())
        v = getattr(self, "lb_share_var", None)
        if v is not None and bool(v.get()) != on:
            v.set(on)
        if hasattr(self, "lb_share_switch") and v is not None:
            return self.lb_share_switch()
        SETTINGS["lb_share"] = on
        save_json("settings.json", SETTINGS)

    def cy_export_key(self, path=None):
        from tkinter import filedialog, messagebox
        if path is None:
            if not messagebox.askokcancel("Move to another PC", KEY_WARN, parent=self.root):
                return False
            path = filedialog.asksaveasfilename(parent=self.root, title="Save your community key",
                                                initialfile="soe2-community-key.json", defaultextension=".json",
                                                filetypes=[("Key file", "*.json")])
            if not path:
                return False
        ok, why = B.export_key(path)
        self.cy_say("Saved. Keep that file to yourself; delete it once the other PC uses it." if ok else why)
        return ok

    def cy_import_key(self, path=None):
        from tkinter import filedialog
        if path is None:
            path = filedialog.askopenfilename(parent=self.root, title="Your community key file",
                                              filetypes=[("Key file", "*.json")])
            if not path:
                return False

        def done(res):
            ok, d = res
            self.cy_say(f"This PC is {d.get('name', '?')} now." if ok else d)
            self.cy_paint()
            if hasattr(self, "mm_board_fetch") and ok:
                self.mm_board_fetch()
        self._bm_bg(lambda: B.import_key(path), done)
        return True

    def cy_say(self, text):
        m = getattr(self, "cy_msg", None)
        if m is not None:
            try:
                m.config(text=text)
            except tk.TclError:
                pass
        self._say(text, 6)
