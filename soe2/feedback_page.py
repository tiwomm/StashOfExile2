"""The update badge and Report a bug (2.48.0), both on the taskbar so they're there whatever window you're in.
2.74.2: a new version shows in the sidebar instead, above Toolkit and Settings (the taskbar badge is for no sidebar).

Update badge: a quiet look at GitHub's latest release a little after start and every hour. A newer version puts
"⬆ Update x.y.z" on the taskbar; clicking it is the same as Settings > Updates > Check for updates (asks before
downloading). It never downloads by itself (that's still the Settings option).

Report a bug: a small form - what happened, how to make it happen, what you expected - and, if you tick it, the app's
log (2.115.0: buglog.diagnostics - the last crash / freeze / slow report and the newest errors, cleaned).
You see exactly what will be sent. It goes to the community board server (board/), which opens a GitHub issue with
its own token (the app holds none) and tells Discord. If the board can't take it, GitHub's
"new issue" page opens in your browser with everything filled in."""
import platform
import threading
import tkinter as tk
import urllib.parse
import webbrowser
from tkinter import ttk

from . import buglog
from . import board as B
from .config import APP_VERSION, SETTINGS
from .style import C, over_app

REPO = "tiwomm/StashOfExile2"
UPDATE_EVERY = 3600                 # 2.79.1 (feedback): every hour (was 6 h)


class FeedbackPage:
    """Mixed into App."""

    # ================================================================ taskbar
    def build_feedback(self):
        tb = "#111b30"
        self.upd_badge = tk.Label(self.shell.task_right, text="", bg=C["accent"], fg="#1a1206", padx=8, pady=4,
                                  cursor="hand2", font=("Segoe UI", 9, "bold"))
        self.upd_badge.bind("<Button-1>", lambda e: self.check_updates("ask"))
        self.bug_btn = tk.Label(self.shell.task_right, text="🐞 Report a bug", bg=tb, fg="#cfdaf0", padx=8, pady=4,
                                cursor="hand2", font=("Segoe UI", 9), highlightthickness=1,
                                highlightbackground="#3d5582")
        self.bug_btn.pack(in_=self.shell.task_right, side="left", padx=4, before=self.league_chip)
        self.bug_btn.bind("<Button-1>", lambda e: self.bug_report_open())
        self.upd_latest = None
        self.root.after(15000, self.quiet_update_check)

    def quiet_update_check(self):
        """Every hour: is there a newer release? Shows the badge. 2.100.0 (feedback): it follows Preview builds (it
        only ever looked at full releases, so with previews on it never found one), and with Settings' update
        switches on, a newer version also gets a card - Install now, or it installs when the app next starts."""
        from .config import SETTINGS

        def work():
            from .updates import latest_release
            try:
                kind, data = latest_release(preview=bool(SETTINGS.get("update_preview")))
            except Exception:
                kind, data = "error", {}
            self.ui_q.put(("update_badge", data.get("tag_name") if kind == "ok" else None))
        threading.Thread(target=work, daemon=True).start()
        self.root.after(UPDATE_EVERY * 1000, self.quiet_update_check)

    def update_found(self, tag):
        """A check during the session found a newer version: a card once per version (when an update switch is on)."""
        from .config import SETTINGS, pretty_version
        if getattr(self, "_upd_told", None) == tag or getattr(self, "_upd_busy", False):
            return False
        if not (SETTINGS.get("auto_update") or SETTINGS.get("auto_check_updates")):
            return False
        self._upd_told = tag
        later = "Later" if not SETTINGS.get("auto_update") else "When I next start the app"
        self.info_card(f"Version {pretty_version(tag)} is out (you have {pretty_version()}).",
                       [("Install now", lambda: self.check_updates("ask")), (later, lambda: None)], secs=120)
        return True

    def ev_update_badge(self, tag):
        from .updates import is_newer
        from .config import pretty_version
        sb = getattr(self.shell, "sidebar", None)
        if tag and is_newer(tag, APP_VERSION):
            self.upd_latest = tag
            try:
                self.update_found(tag)
            except Exception:
                buglog.caught()
            self.upd_badge.config(text=f"⬆ Update {pretty_version(tag)}")
            if sb is not None:                               # 2.74.2: in the sidebar, above Toolkit and Settings
                sb.redraw()
                return
            if not self.upd_badge.winfo_ismapped():
                self.upd_badge.pack(in_=self.shell.task_right, side="left", padx=4, before=self.bug_btn)
            from .style import Tooltip
            Tooltip(self.upd_badge, f"Version {pretty_version(tag)} is out (you have {pretty_version()}). Click: see "
                                    "what's new and update (it asks first).")
        else:
            self.upd_latest = None
            self.upd_badge.pack_forget()
            if sb is not None:
                sb.redraw()

    # ================================================================ Report a bug
    def bug_report_text(self, what, steps, expected, contact, with_log):
        """Exactly what is sent (shown in the form before you send it)."""
        from .privacy import public_league, scrub_names
        try:
            sh = self.root.winfo_screenheight()
        except tk.TclError:
            sh = 0
        parts = [f"**What happened**\n{what.strip()}"]
        if steps.strip():
            parts.append(f"**How to make it happen**\n{steps.strip()}")
        if expected.strip():
            parts.append(f"**What I expected**\n{expected.strip()}")
        # 2.89.3: no exact Windows build or screen size (they help pick one person out); a private league's name stays here
        res = "4K" if sh >= 2000 else "1440p" if sh >= 1400 else "1080p" if sh >= 1000 else "under 1080p" if sh else "?"
        parts.append(f"**App** {APP_VERSION} · {platform.system()} {platform.release()} · {res} · "
                     f"league {public_league(SETTINGS.get('league')) or '?'}")
        if with_log:                                 # 2.115.0: the one log - the last crash / freeze / slow report and
            from . import buglog                     # the newest entries of app_log.txt, cleaned, capped
            parts.append(buglog.diagnostics() or "**App log**\n(nothing logged - no errors, crashes or freezes)")
        return scrub_names("\n\n".join(parts))      # 2.89.3: every word - your names / paths never reach the issue

    def bug_report_open(self, title="", what=""):
        """title / what (2.115.0): filled in for you - the "app closed by itself" message's Report it."""
        P1, P2 = C["panel"], C["panel2"]
        if getattr(self, "bug_win", None) is not None:
            try:
                self.bug_win.lift()
                return self.bug_win
            except tk.TclError:
                pass
        win = tk.Toplevel(self.root)
        over_app(win, self.dlg_parent())               # 2.114.3: over the app, on its monitor
        win.title("Report a bug")
        win.configure(bg=P1)
        win.transient(self.root)
        win.geometry("640x660")
        win.minsize(520, 560)
        self.bug_win = win
        win.protocol("WM_DELETE_WINDOW", self._bug_close)
        f = tk.Frame(win, bg=P1, padx=16, pady=12)
        f.pack(fill="both", expand=True)
        tk.Label(f, text="Report a bug", bg=P1, fg=C["accent"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(f, text="It becomes an issue on GitHub (tiwomm/StashOfExile2), and the developer is told on Discord. "
                         "Your account and character names and your Windows user name are taken out - below is exactly "
                         "what goes, word for word. It's public: don't paste whispers or chat.", bg=P1,
                 fg=C["muted"], font=("Segoe UI", 9), wraplength=600, justify="left", anchor="w").pack(fill="x",
                                                                                                       pady=(2, 8))
        self.bug_vars = {}

        def field(key, label, h=0):
            tk.Label(f, text=label, bg=P1, fg=C["text"], anchor="w").pack(fill="x", pady=(4, 2))
            if h:
                t = tk.Text(f, height=h, bg=P2, fg=C["text"], insertbackground=C["text"], relief="flat",
                            highlightthickness=1, highlightbackground=C["line"], wrap="word", font=("Segoe UI", 9))
                t.pack(fill="x")
                t.bind("<KeyRelease>", lambda e: self._bug_preview())
                # 2.50.0: Tab moves on to the next box (in a text box it typed a tab character)
                t.bind("<Tab>", lambda e: (e.widget.tk_focusNext().focus_set(), "break")[1])
                t.bind("<Shift-Tab>", lambda e: (e.widget.tk_focusPrev().focus_set(), "break")[1])
                self.bug_vars[key] = t
            else:
                v = tk.StringVar()
                ttk.Entry(f, textvariable=v).pack(fill="x")
                v.trace_add("write", lambda *a: self._bug_preview())
                self.bug_vars[key] = v
        field("title", "In a few words (the title)")
        field("what", "What happened?", 3)
        field("steps", "How can it be made to happen? (steps - optional)", 3)
        field("expected", "What did you expect? (optional)", 2)
        self.bug_log = tk.BooleanVar(value=True)
        from . import buglog                         # 2.115.0: what the log holds, said plainly
        n = buglog.counts()
        seen = ", ".join(f"{v} {k}{'es' if k == 'crash' and v != 1 else 's' if v != 1 else ''}"
                         for k, v in sorted(n.items()) if v) or "nothing"
        ttk.Checkbutton(f, text="Add the app's log: errors, crashes, freezes - code locations only (helps a lot)",
                        variable=self.bug_log, command=self._bug_preview).pack(anchor="w", pady=(8, 0))
        tk.Label(f, text=f"In the last week: {seen}.", bg=P1, fg=C["muted"], font=("Segoe UI", 9),
                 anchor="w").pack(fill="x", padx=(24, 0), pady=(0, 4))
        b = tk.Frame(f, bg=P1)                   # 2.50.0: the buttons first, at the bottom - never cut off
        b.pack(side="bottom", fill="x", pady=(8, 0))
        tk.Label(f, text="What will be sent", bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(fill="x")
        self.bug_prev = tk.Text(f, height=6, bg=C["bg"], fg=C["muted"], relief="flat", wrap="word",
                                font=("Consolas", 9), highlightthickness=1, highlightbackground=C["line"],
                                takefocus=0)
        self.bug_prev.pack(fill="both", expand=True)
        self.bug_msg = tk.Label(b, text="", bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left",
                                wraplength=380)
        self.bug_msg.pack(side="left", fill="x", expand=True)
        self.bug_send_btn = ttk.Button(b, text="Send", style="Primary.TButton", command=self.bug_send)
        self.bug_send_btn.pack(side="right")
        ttk.Button(b, text="Cancel", style="Quiet.TButton", command=self._bug_close).pack(side="right", padx=(0, 8))
        if title:
            self.bug_vars["title"].set(title)
        if what:
            self.bug_vars["what"].insert("1.0", what)
        self._bug_preview()
        return win

    def _bug_close(self):
        w, self.bug_win = getattr(self, "bug_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def _bug_val(self, key):
        v = self.bug_vars[key]
        return v.get("1.0", "end-1c") if isinstance(v, tk.Text) else v.get()

    def _bug_preview(self):
        if getattr(self, "bug_win", None) is None:
            return
        text = self.bug_report_text(self._bug_val("what"), self._bug_val("steps"), self._bug_val("expected"), "",
                                    self.bug_log.get())
        self.bug_prev.config(state="normal")
        self.bug_prev.delete("1.0", "end")
        self.bug_prev.insert("1.0", f"[Bug] {self._bug_val('title').strip()}\n\n{text}")
        self.bug_prev.config(state="disabled")

    def bug_send(self):
        title, what = self._bug_val("title").strip(), self._bug_val("what").strip()
        if len(title) < 4 or len(what) < 10:
            self.bug_msg.config(text="A title and a few words about what happened, please.", fg=C["red"])
            return None
        body = self.bug_report_text(what, self._bug_val("steps"), self._bug_val("expected"), "", self.bug_log.get())
        self.bug_send_btn.config(state="disabled")
        self.bug_msg.config(text="Sending…", fg=C["muted"])

        def work():
            from .privacy import scrub_names
            return B.call("POST", "/bugs", body={"title": scrub_names(title), "body": body, "version": APP_VERSION})

        def done(res):
            ok, data = res
            if ok and isinstance(data, dict) and data.get("url"):
                self.app_toast(f"Thanks! Your report is issue #{data.get('number')} on GitHub.", "Report a bug",
                               kind="success") if hasattr(self, "app_toast") else None
                self.bug_last = data
                self._bug_close()
                return
            self.bug_browser(title, body, why=data if isinstance(data, str) else "")
        self.run_bg(work, done)

    def bug_browser(self, title, body, why=""):
        """The board couldn't take it: GitHub's new-issue page, filled in (you sign in to GitHub to send it)."""
        url = (f"https://github.com/{REPO}/issues/new?labels=bug&title=" + urllib.parse.quote(f"[Bug] {title}")
               + "&body=" + urllib.parse.quote(body[:6000]))
        self.bug_last = {"url": url, "browser": True}
        try:
            webbrowser.open(url)
        except Exception:
            buglog.caught()
        if getattr(self, "bug_win", None) is not None:
            self.bug_send_btn.config(state="normal")
            self.bug_msg.config(text=("The board couldn't take it" + (f" ({why})" if why else "") + " - GitHub's new "
                                      "issue page opened in your browser with everything filled in: press Submit "
                                      "there."), fg=C["orange"])
        return url
