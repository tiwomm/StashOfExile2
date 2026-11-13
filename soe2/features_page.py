"""2.131.0 the Feature Picker (features.py has the groups): one popup asked once - which features you use, whether to
share anonymous data (only if you never answered) and where your data lives (only the first time) - and the same
feature switches in Settings › General › Features."""
import os
import tkinter as tk
from tkinter import filedialog, ttk

from . import buglog
from . import features as FEAT
from .config import SETTINGS, save_json
from .style import C, Tooltip


def shown_path(d):
    """A folder without your Windows user name on screen."""
    d = str(d)
    for env in ("APPDATA", "LOCALAPPDATA"):
        v = os.environ.get(env)
        if v and d.lower().startswith(v.lower()):
            return f"%{env}%" + d[len(v):]
    home = os.path.expanduser("~")
    return "~" + d[len(home):] if home and d.lower().startswith(home.lower()) else d


class FeaturesPage:
    # ---------------------------------------------------------------- applying
    def features_set(self, key, value):
        FEAT.set_on(key, value)
        save_json("settings.json", SETTINGS)
        self.features_apply()

    def features_apply(self):
        """Pages leave / come back to the menu; the overlay and its helpers follow the Game Overlay switch."""
        try:
            self.shell.features_changed()
        except Exception:
            buglog.caught()
        for fn in ("merged_build", "remnant_auto_sync", "favours_sync"):
            try:
                getattr(self, fn)()
            except Exception:
                buglog.caught()
        if not FEAT.on("overlay"):
            try:
                self.breach_dismiss()
                self.ws_stop()
            except Exception:
                buglog.caught()
        else:
            self.topup_start()                              # 2.131.0: Top Up (it stops itself when off)
            self.hover_start()                              # 2.132.1/2.132.3: Temple Helper, Ritual Identifier
            if self.temple_fast_on():
                self.temple_fast_start()                    # 2.138.1: Fast Beacon Read (opt-in)
        if FEAT.on("overlay") and self.ritual_cfg().get("on"):
            try:
                self.ritual_start()
            except Exception:
                buglog.caught()
        try:
            self.features_paint()
        except Exception:
            buglog.caught()

    # ---------------------------------------------------------------- the switches (popup and Settings)
    def features_rows(self, parent, bg, live=False, two=False):
        """Each group: a switch, its name, what it does and its key; then the Beta cluster. live=True: a change
        applies at once (Settings); else the popup's Save applies them. two=True: groups left, Beta right (the popup
        fits a 1080p screen). -> {key: BooleanVar}."""
        sm, bold = ("Segoe UI", 9), ("Segoe UI", 10, "bold")
        vars_ = {}

        def row(g, box):
            r = tk.Frame(box, bg=bg)
            r.pack(fill="x", pady=(0, 8))
            v = tk.BooleanVar(value=FEAT.on(g["key"]))
            vars_[g["key"]] = v
            cb = ttk.Checkbutton(r, text=g["name"], variable=v, style="Card.TCheckbutton",
                                 command=(lambda k=g["key"], v=v: self.features_set(k, v.get())) if live else None)
            cb.pack(anchor="w")
            keys = g.get("keys")
            if keys == "pc_key":
                from .overlay import key_label
                keys = key_label(SETTINGS.get("pc_key") or "") or ""
            tk.Label(r, text=g["what"] + (f"  Key: {keys}." if keys else ""), bg=bg, fg=C["muted"], font=sm,
                     anchor="w", justify="left", wraplength=360 if two else 520).pack(fill="x", padx=(24, 0))
        left = right = parent
        if two:
            cols = tk.Frame(parent, bg=bg)
            cols.pack(fill="x")
            left, right = tk.Frame(cols, bg=bg), tk.Frame(cols, bg=bg)
            left.pack(side="left", fill="y", anchor="n")
            right.pack(side="left", fill="y", anchor="n", padx=(24, 0))
        for g in FEAT.GROUPS:
            row(g, left)
        parent = right
        head = tk.Frame(parent, bg=bg)
        head.pack(fill="x", pady=(0 if two else 8, 4))
        tk.Label(head, text="Beta", bg=bg, fg=C["text"], font=bold).pack(side="left")
        tk.Label(head, text="BETA", bg=bg, fg=C["accent"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=8)
        bi = tk.Label(head, text="ⓘ", bg=bg, fg=C["muted"], font=sm, cursor="question_arrow")
        bi.pack(side="left")
        Tooltip(bi, "Features still being tried out: they work, but may change a lot or have rough edges.")
        for g in FEAT.BETA:
            row(g, parent)
        return vars_

    def features_paint(self):
        vs = getattr(self, "feat_vars", None) or {}
        for k, v in vs.items():
            try:
                if v.get() != FEAT.on(k):
                    v.set(FEAT.on(k))
            except tk.TclError:
                pass

    # ---------------------------------------------------------------- the popup, asked once
    def features_maybe(self):
        """At start-up: the picker, unless answered (or Never ask again) - after the welcome / What's new card."""
        if FEAT.asked() in ("done", "never"):
            return None
        from .config import APP_VERSION
        if SETTINGS.get("seen_version") != APP_VERSION:          # 2.131.1 (feedback: it opened under What's new and
            self.root.after(1500, self.features_maybe)         # got lost): What's new / the quick start first -
            return None                                        # closing it brings the picker (close_whatsnew)
        wn = getattr(self, "_whatsnew", None)
        try:
            if wn is not None and wn.winfo_exists():
                self.root.after(1500, self.features_maybe)
                return None
        except tk.TclError:
            pass
        return self.features_picker()

    def features_picker(self):
        old = getattr(self, "feat_win", None)
        try:
            if old is not None and old.winfo_exists():
                old.lift()
                return old
        except tk.TclError:
            pass
        P1, P2 = C["panel"], C["panel2"]
        w = tk.Toplevel(self.root, bg=C["accent"], padx=1, pady=1)
        w.title("Feature Picker")
        try:
            w.transient(self.root)
        except tk.TclError:
            pass
        w.protocol("WM_DELETE_WINDOW", lambda: self.features_close(w))      # (×: asked again next start)
        w.bind("<Escape>", lambda _e: self.features_close(w))
        self.feat_win = w
        inner = tk.Frame(w, bg=P2, padx=16, pady=16)
        inner.pack(fill="both", expand=True)
        top = tk.Frame(inner, bg=P2)
        top.pack(fill="x")
        tk.Label(top, text="What do you want to use?", bg=P2, fg=C["text"], font=("Segoe UI", 16, "bold"),
                 anchor="w").pack(side="left")
        tip = tk.Label(top, text="ⓘ", bg=P2, fg=C["muted"], cursor="question_arrow")
        tip.pack(side="left", padx=8)
        Tooltip(tip, "Your data is kept while a feature is off. Change these any time: Settings › General › Features.")
        tk.Label(inner, text="Turn off what you don't need - it leaves the menu and its keys do nothing.", bg=P2,
                 fg=C["muted"], anchor="w").pack(fill="x", pady=(2, 8))
        pvars = self.features_rows(inner, P2, two=True)
        share_v = None
        if not SETTINGS.get("share_asked"):                     # only if you never answered (a "no" is final)
            tk.Frame(inner, bg=C["line"], height=1).pack(fill="x", pady=(8, 8))
            sh = tk.Frame(inner, bg=P2)
            sh.pack(fill="x")
            share_v = tk.BooleanVar(value=False)
            ttk.Checkbutton(sh, text="Share anonymous data with the community", variable=share_v,
                            style="Card.TCheckbutton").pack(anchor="w")
            tk.Label(sh, text="Off until you turn it on. Price summaries and your ratings - never your name, "
                              "characters or wealth. You get everyone's data either way.", bg=P2, fg=C["muted"],
                     font=("Segoe UI", 9), anchor="w", justify="left", wraplength=760).pack(fill="x", padx=(24, 0))
            # 2.131.1 (feedback: say why a name is asked next): the Leaderboards need a community name
            tk.Label(sh, text="To show your times on the Leaderboards, pick a community name (asked next).", bg=P2,
                     fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left", wraplength=760).pack(
                fill="x", padx=(24, 0))
        err_v = None
        if not SETTINGS.get("error_asked"):                     # 2.137.0: asked once, next to data sharing
            from . import errorreports as ER
            tk.Frame(inner, bg=C["line"], height=1).pack(fill="x", pady=(8, 8))
            er = tk.Frame(inner, bg=P2)
            er.pack(fill="x")
            err_v = tk.BooleanVar(value=False)
            ttk.Checkbutton(er, text="Send error reports", variable=err_v, style="Card.TCheckbutton").pack(anchor="w")
            tk.Label(er, text=ER.WHAT, bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left",
                     wraplength=760).pack(fill="x", padx=(24, 0))
        ask_v = None
        if not SETTINGS.get("ask_unrated_asked"):               # 2.131.2: the same switch as Settings, asked once
            tk.Frame(inner, bg=C["line"], height=1).pack(fill="x", pady=(8, 8))
            ar = tk.Frame(inner, bg=P2)
            ar.pack(fill="x")
            ask_v = tk.BooleanVar(value=bool(SETTINGS.get("ask_unrated")))
            ttk.Checkbutton(ar, text="Ask me about mods I haven't rated", variable=ask_v,
                            style="Card.TCheckbutton").pack(anchor="w")
            tk.Label(ar, text="Your ratings tune your price checks. Change it later in Settings › Price checking.",
                     bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=(24, 0))
        folder = {"new": None}
        if not SETTINGS.get("data_dir_asked"):                  # the first time only (later: Settings › Advanced)
            from .config import DATA_DIR
            tk.Frame(inner, bg=C["line"], height=1).pack(fill="x", pady=(8, 8))
            fr = tk.Frame(inner, bg=P2)
            fr.pack(fill="x")
            tk.Label(fr, text="Data folder:", bg=P2, fg=C["text"], font=("Segoe UI", 10, "bold")).pack(side="left")
            where = tk.Label(fr, text=shown_path(DATA_DIR), bg=P2, fg=C["text"], font=("Consolas", 9))
            where.pack(side="left", padx=8)

            def pick():
                d = filedialog.askdirectory(parent=w, title="Where should StashOfExile2 keep your data?")
                if d:
                    folder["new"] = d
                    where.config(text=shown_path(d) + "  (after Save)")
            ttk.Button(fr, text="Choose…", command=pick).pack(side="left")
            tk.Label(inner, text="Settings, lists and history live here. Keep the usual place, or pick one - a USB "
                                 "stick or the app's own folder for a portable copy.", bg=P2, fg=C["muted"],
                     font=("Segoe UI", 9), anchor="w", justify="left", wraplength=760).pack(fill="x")
        foot = tk.Frame(inner, bg=P2)
        foot.pack(fill="x", pady=(16, 0))

        def save(all_on=False):
            for k, v in pvars.items():
                FEAT.set_on(k, True if all_on else v.get())
            SETTINGS["features_asked"] = "done"
            SETTINGS["data_dir_asked"] = True
            if ask_v is not None:
                self.ask_unrated_set(bool(ask_v.get()))
            if err_v is not None:
                self.er_set(bool(err_v.get()), say=False)
            save_json("settings.json", SETTINGS)
            if share_v is not None:
                self.cm_set_sharing(bool(share_v.get()), say=False)
                if share_v.get():
                    self.root.after(200, self.cm_name_ask)      # (a community name for the Leaderboards)
            elif self.cm_sharing():                             # 2.131.1: sharing from before, still no name
                self.root.after(200, self.cm_name_ask)          # (asked once; it checks for itself)
            self.features_apply()
            note = None
            if folder["new"]:
                from .config import move_data
                ok, note = move_data(folder["new"])
                if ok:
                    self.root.after(300, self.features_restart_ask)
            self.features_close(w, answered=True)
            self._say(note or "Saved. Change these any time: Settings › General › Features.", 8)

        def never():
            SETTINGS["features_asked"] = "never"
            save_json("settings.json", SETTINGS)
            self.features_close(w, answered=True)
        sv = ttk.Button(foot, text="Save", style="Primary.TButton", command=save)
        sv.pack(side="right")
        ttk.Button(foot, text="Turn all on", command=lambda: save(True)).pack(side="right", padx=(0, 8))
        ttk.Button(foot, text="Never ask again", style="Quiet.TButton", command=never).pack(side="left")
        w.feat_save, w.feat_vars, w.feat_share, w.feat_folder, w.feat_never = save, pvars, share_v, folder, never
        w.feat_err = err_v
        try:
            from .style import center_over
            center_over(w, self.root)
        except Exception:
            buglog.caught()
        self.popup_over_app(w)
        return w

    def ask_unrated_set(self, on):
        """2.131.2: Ask me about mods I haven't rated - one switch (Settings › Price checking; the picker asks once)."""
        SETTINGS["ask_unrated"] = bool(on)
        SETTINGS["ask_unrated_asked"] = True
        save_json("settings.json", SETTINGS)
        v = getattr(self, "ask_unrated_var", None)
        if v is not None and bool(v.get()) != bool(on):
            v.set(bool(on))
        rec = getattr(self, "shown_rec", None)
        if rec is not None:
            try:
                self.show_detail(rec)
            except Exception:
                buglog.caught()

    def popup_over_app(self, w):
        """2.131.1 (feedback: the picker got lost behind the app): Windows itself keeps it above the app's window, and
        it's on top when the app is (Settings › Always on top) - like the app's own pages."""
        try:
            from .shell import DeskWindow
            w.shell = self.shell
            DeskWindow.own_by_app(w)
            DeskWindow.follow_on_top(w)
            w.lift()
            w.focus_force()
        except Exception:
            buglog.caught()

    def features_close(self, w, answered=False):
        try:
            if w.winfo_exists():
                w.destroy()
        except tk.TclError:
            pass
        self.feat_win = None

    def features_restart_ask(self):
        from tkinter import messagebox
        if messagebox.askyesno("Restart now?", "Your data was copied to the new folder. Restart the app to use it?",
                               parent=self.root):
            self.restart_app()

    # ---------------------------------------------------------------- Settings › Advanced › Data folder: Change…
    def data_dir_change(self):
        from tkinter import messagebox
        d = filedialog.askdirectory(parent=self.dlg_parent(), title="Where should StashOfExile2 keep your data?")
        if not d:
            return None
        from .config import move_data
        ok, note = move_data(d)
        self._say(note, 10)
        if ok and messagebox.askyesno("Restart now?", note + "\n\nRestart now?", parent=self.dlg_parent()):
            self.restart_app()
        return ok
