"""Alerts while you play (2.10.0): the Delirium and Breach alerts, switched on and watched from one panel on the
Session tracker's main page. (2.9.0 had Breach in Session tracker > Options and Delirium in its own window.)

Breach: the game writes its Hiveblood warnings to its own log, Client.txt (seen in real PoE 2 logs, Oct 2026):
    : <brequelwarning>{Stored Hiveblood is almost at the maximum!}
    : <brequelwarning>{Cannot store any more Hiveblood! Go to the Genesis Tree to consume it.}
Both are easy to miss in the middle of a Breach. This follows Client.txt (only new lines, about once a second - the
same way the Session tracker does) and shows a banner over the game: an "almost full" one, and a stronger "full"
one. Nothing is read from the game itself and no keys are sent. A banner looks like the Delirium alert's END DELIRIUM (2.12.1): big flashing text over the game,
no box; clicks go through it. It goes after a few seconds, or as soon as you open the Genesis Tree.

Remnant (2.37.0): the Expedition Remnant Price Checker (remnant.py / remnant_page.py) - a key, not a watcher.

Delirium: the helper (utilities.DELIRIUM, delirium_runner.py) looks at your screen; its END DELIRIUM banner is its own.
This panel only starts / stops it, sets its sound and tests it. Its splinter icon is gone (2.10.0)."""
import sys
import time
import tkinter as tk
from tkinter import ttk

from .config import save_json, SETTINGS
from .gamelog import area_kind as gl_area_kind, find_log, LogReader
from .style import C, Tooltip

REPEAT_SECS = 45          # the game repeats a warning (twice in 2 s, then every ~15 s when full): one banner per level
RETRY_TICKS = 15          # Client.txt not found: look again every this many seconds
LEVELS = {
    "almost": ("HIVEBLOOD ALMOST FULL", "Spend it at the Genesis Tree  ·  click to close", "#2a0d10", "#ff3df0"),
    "full": ("CANNOT STORE ANY MORE HIVEBLOOD!", "Go to the Genesis Tree to consume it  ·  click to close", "#3a0606",
             "#ff2a2a"),
    # 2.11.0: you left a map after the game warned and haven't opened the Genesis Tree since
    "ritual": ("RITUALS NOT DONE", "Go back through your portal", "#2a0606", "#ff4a4a"),      # 2.14.0
    "leave": ("SPEND YOUR HIVEBLOOD", "It was almost full when you left the map: visit the Genesis Tree  ·  click to "
                                      "close", "#2a1a06", "#ffb347"),
}
DOT = {"on": "#5ee08a", "off": "#6b7690", "warn": "#ffb347"}
TRANSPARENT = "#010203"
BANNER_SECS = {"almost": 8, "full": 10, "leave": 8, "ritual": 8}       # 2.12.1: then it goes by itself (like END DELIRIUM)


def _hwnd(win):
    import ctypes
    u = ctypes.windll.user32
    u.GetParent.restype = ctypes.c_void_p
    u.GetParent.argtypes = [ctypes.c_void_p]
    return u.GetParent(win.winfo_id()) or win.winfo_id()


def click_through(win):
    """Clicks go through to the game and it never takes the keyboard (Windows) - as the Delirium alert does."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        u = ctypes.windll.user32
        u.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        u.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
        h = _hwnd(win)
        u.SetWindowLongW(h, -20, u.GetWindowLongW(h, -20) | 0x80000 | 0x20 | 0x80 | 0x08000000)
    except Exception:
        pass


def force_topmost(win):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        u = ctypes.windll.user32
        u.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_uint]
        u.SetWindowPos(_hwnd(win), ctypes.c_void_p(-1), 0, 0, 0, 0, 0x1 | 0x2 | 0x10)
    except Exception:
        pass


def game_rect(title="Path of Exile 2"):
    """-> (left, top, width, height) of the game window, or None (then the main screen is used)."""
    if sys.platform.startswith("linux"):
        from .linsys import game_rect as _gr
        return _gr(title)
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def cb(hwnd, _):
            if u.IsWindowVisible(hwnd):
                n = u.GetWindowTextLengthW(hwnd)
                if n:
                    buf = ctypes.create_unicode_buffer(n + 1)
                    u.GetWindowTextW(hwnd, buf, n + 1)
                    if buf.value.strip().lower() == title.lower():
                        r = wintypes.RECT()
                        u.GetWindowRect(hwnd, ctypes.byref(r))
                        found.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
                        return False
            return True
        u.EnumWindows(cb, 0)
        return found[0] if found and found[0][2] > 200 and found[0][3] > 200 else None
    except Exception:
        return None


def breach_level(text):
    """The game's warning text -> "full" or "almost"."""
    t = (text or "").lower()
    return "full" if "cannot store" in t or "any more" in t else "almost"


class AlertsPage:
    """Mixed into App."""

    # ================================================================ settings
    def breach_cfg(self):
        c = SETTINGS.setdefault("breach_alert", {})
        c.setdefault("on", False)
        c.setdefault("sound", True)
        c.setdefault("leave_reminder", True)       # 2.11.0
        c.setdefault("pending", None)              # 2.11.0: "almost" / "full" since the last warning, until the tree
        return c

    def ritual_cfg(self):
        """2.14.0: the Ritual watcher (ritual_alert.py, its own helper process)."""
        c = SETTINGS.setdefault("ritual_alert", {})
        c.setdefault("on", False)
        c.setdefault("sound", True)
        c.setdefault("leave_reminder", True)
        return c

    def log_wanted(self):
        """Client.txt is followed while Breach or Ritual needs it (Ritual: to know when you leave a map)."""
        return bool(self.breach_cfg().get("on") or self.ritual_cfg().get("on")
                    or (hasattr(self, "fl_counting") and self.fl_counting()))     # 2.45.0: the Farm Ledger's runs

    def alerts_init(self):
        """At start-up (start_utilities): the Breach watcher runs whether or not the tracker window was opened."""
        if getattr(self, "_alerts_ready", False):
            return
        self._alerts_ready = True
        self.br_reader, self.br_last, self.br_win, self.br_level = None, {}, None, None
        self.br_ticks, self._br_ticking, self.br_note = 0, False, ""
        self.br_area = None                        # 2.11.0: "map" / "hideout" / "town" / "other" - where you are
        self.rt_map = None                         # 2.14.0: the last Ritual count seen in this map (done, total)
        if self.log_wanted():
            self.root.after(1500, self.breach_start)
        if self.ritual_cfg().get("on"):
            self.root.after(2500, self.ritual_start)
        if self.remnant_cfg().get("on"):                 # 2.37.0: the Remnant Auto watcher
            self.root.after(3000, self.remnant_auto_sync)

    # ================================================================ the panel (Session tracker, main page)
    def build_alerts_panel(self, parent):
        self.alerts_init()
        P2 = C["panel2"]
        box = tk.Frame(parent, bg=P2, padx=12, pady=8, highlightthickness=1, highlightbackground=C["line"])
        head = tk.Frame(box, bg=P2)
        head.pack(fill="x")
        tk.Label(head, text="Alerts while you play", bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(head, text="they work over the game whenever the app runs, session or not", bg=P2, fg=C["muted"],
                 font=("Segoe UI", 9)).pack(side="left", padx=8)
        self.al_bar = tk.BooleanVar(value=bool(self.tracker_cfg().get("alerts_bar", True)))
        ttk.Checkbutton(head, text="Mechanic Helper bar (with the timer)", variable=self.al_bar,
                        command=self.alerts_bar_changed).pack(side="right")
        self.al_rows = {}
        for key, name, what, test in (
                ("delirium", "Delirium", "END DELIRIUM when you finish a map with Delirium still on (reads your screen)",
                 self.alerts_test_delirium),
                ("breach", "Breach", "a banner when your stored Hiveblood is almost full, and when it's full "
                                     "(reads Client.txt)", lambda: self.breach_alert(test=True)),
                ("ritual", "Ritual", "reads the Ritual counter (0/3 ...) from your screen; reminds you if you leave a "
                                     "map after starting its rituals but not finishing them", self.alerts_test_ritual),
                ("remnant", "Remnant", "Expedition Remnant Price Checker: each reward in a remnant's book gets its "
                                       "poe.ninja price, by itself (Auto) or with its key", self.alerts_test_remnant)):
            row = tk.Frame(box, bg=P2)
            row.pack(fill="x", pady=(8, 0))
            dot = tk.Label(row, text="●", bg=P2, fg=DOT["off"], font=("Segoe UI", 10))
            dot.pack(side="left")
            on = tk.BooleanVar(value=False)
            nb = ttk.Checkbutton(row, text=name, variable=on, width=9, command=lambda k=key: self.alerts_toggle(k))
            nb.pack(side="left", padx=(4, 0))
            Tooltip(nb, what)                       # 2.37.0: what it does - the line under a row shows only while on
            snd = tk.BooleanVar(value=True)
            if key != "remnant":                   # 2.39.0: the Remnant price tags make no sound
                ttk.Checkbutton(row, text="Sound", variable=snd,
                                command=lambda k=key: self.alerts_sound(k)).pack(side="left")
            ttk.Button(row, text="Test", command=test, width=6).pack(side="right")
            if key == "breach":                    # 2.11.0
                self.al_leave = tk.BooleanVar(value=bool(self.breach_cfg().get("leave_reminder", True)))
                ttk.Checkbutton(row, text="Remind me when I leave the map", variable=self.al_leave,
                                command=self.alerts_leave_changed).pack(side="left", padx=(4, 0))
            if key == "remnant":                   # 2.37.0: Auto - the list is found and priced by itself
                self.al_rauto = tk.BooleanVar(value=bool(self.remnant_cfg().get("auto")))
                ab = ttk.Checkbutton(row, text="Auto (no key needed)", variable=self.al_rauto,
                                     command=lambda: self.remnant_auto_changed(self.al_rauto.get()))
                ab.pack(side="left", padx=(4, 0))
                self.al_rtips = tk.BooleanVar(value=bool(self.remnant_cfg().get("tips", True)))      # 2.40.0
                tb_ = ttk.Checkbutton(row, text="Runeshape tips", variable=self.al_rtips,
                                      command=lambda: self.remnant_tips_changed(self.al_rtips.get()))
                tb_.pack(side="left", padx=(4, 0))
                Tooltip(tb_, "A small list next to the prices: the runeshapes players rate best for loot (S and A "
                             "tier). It shows and goes with the prices.")
                Tooltip(ab, "Prices show by themselves when a remnant's reward book opens: the app watches the spot "
                            "where it opens (scaled to your resolution, like the Delirium watcher) - no box to draw. "
                            "Off: only the key prices it.")
            if key == "ritual":                    # 2.14.0
                self.al_rleave = tk.BooleanVar(value=bool(self.ritual_cfg().get("leave_reminder", True)))
                ttk.Checkbutton(row, text="Remind me when I leave the map", variable=self.al_rleave,
                                command=self.alerts_ritual_leave_changed).pack(side="left", padx=(4, 0))
            st = tk.Label(box, text=what, bg=P2, fg=C["muted"], anchor="w", justify="left", font=("Segoe UI", 9))
            st.pack(fill="x", padx=(24, 8))                   # 2.11.0: its own line, so it never gets cut off
            st.bind("<Configure>", lambda e, l=st: l.config(wraplength=max(200, e.width - 10)))
            self.al_rows[key] = {"dot": dot, "on": on, "sound": snd, "status": st, "what": what, "note": "", "row": row}
        self.al_rows["breach"]["on"].set(bool(self.breach_cfg().get("on")))
        self.al_rows["breach"]["sound"].set(bool(self.breach_cfg().get("sound", True)))
        self.al_rows["ritual"]["on"].set(bool(self.ritual_cfg().get("on")))
        self.al_rows["ritual"]["sound"].set(bool(self.ritual_cfg().get("sound", True)))
        self.al_rows["remnant"]["on"].set(bool(self.remnant_cfg().get("on")))          # 2.37.0
        try:
            from .utilities import DELIRIUM
            self.al_rows["delirium"]["sound"].set(bool(DELIRIUM.get_sound()))
        except Exception:
            pass
        self.alerts_refresh()
        return box

    def alerts_toggle(self, key, want=None):
        """On / off for one helper. want=None: what its box in the Alerts panel says. 2.26.0: the timer's Helpers bar
        switches them too (the panel may not even be built then)."""
        rows = getattr(self, "al_rows", None) or {}

        class _Box:                                           # the panel's box, or a stand-in when it isn't built
            def __init__(self, v):
                self.v = v

            def get(self):
                return self.v

            def set(self, v):
                self.v = v
        r = rows.get(key) or {"on": _Box(bool(want)), "note": ""}
        if want is None:
            want = bool(r["on"].get())
        else:
            r["on"].set(bool(want))
        if key == "breach":
            self.breach_cfg()["on"] = want
            save_json("settings.json", SETTINGS)
            if want:
                self.breach_start()
            else:
                self.breach_stop()
        elif key == "ritual":
            self.ritual_cfg()["on"] = want
            save_json("settings.json", SETTINGS)
            err = self.ritual_start() if want else self.ritual_stop()
            r["note"] = err or ""
            if err and want:
                r["on"].set(False)
                self.ritual_cfg()["on"] = False
                save_json("settings.json", SETTINGS)
        elif key == "remnant":                                # 2.37.0
            err = self.remnant_toggle(want)
            r["note"] = err or ""
        else:
            SETTINGS["util_delirium_autostart"] = want       # on = it also starts with the app next time
            save_json("settings.json", SETTINGS)
            err = self.dl_do_start() if want else self.dl_do_stop()
            r["note"] = err or ""
            if err and want:
                r["on"].set(False)
        if rows:
            self.alerts_refresh()
        self.alerts_overlay_redraw()

    def alerts_sound(self, key):
        r = self.al_rows[key]
        if key in ("breach", "ritual"):
            cfg = {"breach": self.breach_cfg, "ritual": self.ritual_cfg}[key]()
            cfg["sound"] = bool(r["sound"].get())
            save_json("settings.json", SETTINGS)
        else:
            from .utilities import DELIRIUM
            DELIRIUM.set_sound(bool(r["sound"].get()))

    def alerts_leave_changed(self):
        self.breach_cfg()["leave_reminder"] = bool(self.al_leave.get())
        save_json("settings.json", SETTINGS)

    def alerts_ritual_leave_changed(self):
        self.ritual_cfg()["leave_reminder"] = bool(self.al_rleave.get())
        save_json("settings.json", SETTINGS)

    def alerts_test_remnant(self):
        r = self.al_rows["remnant"]
        r["note"] = self.remnant_test()
        self.alerts_refresh()

    def alerts_test_ritual(self):
        self.breach_alert(test=True, level="ritual", sub="1 of 3 done (a test)")

    # ---- Ritual helper
    def ritual_start(self):
        from .utilities import RITUAL
        err = RITUAL.start()
        if not err and self.br_reader is None:
            self.breach_start()                         # to see you leave a map
        self.root.after(1500, self.alerts_refresh)
        return err

    def ritual_stop(self):
        from .utilities import RITUAL
        RITUAL.stop()
        self.rt_map = None
        if not self.log_wanted():
            self.br_reader = None
        self.alerts_refresh()
        return None

    def ritual_status(self):
        from .utilities import RITUAL
        if not self.ritual_cfg().get("on"):
            return "off"
        if not RITUAL.running() or RITUAL.state == "error":
            return "warn"
        return "on"

    def alerts_bar_changed(self):
        self.tracker_cfg()["alerts_bar"] = bool(self.al_bar.get())
        self.tracker_save()
        if getattr(self, "tk_overlay", None) is not None:          # 2.38.0: just the Helpers bar's own window
            self.tracker_helpers_build()
            self.tracker_overlay_draw(self.tracker_numbers())

    def alerts_test_delirium(self):
        err = self.dl_do_test()
        r = self.al_rows["delirium"]
        r["note"] = err or "The END DELIRIUM banner shows for 5 seconds."
        self.alerts_refresh()

    def alert_states(self):
        """{"delirium": "on" | "off" | "warn", "breach": ...}: the panel's dots and the timer's bar.
        warn = switched on but not working (the Delirium helper hit an error; Client.txt not found)."""
        try:
            from .utilities import DELIRIUM
            run = DELIRIUM.running()
            d = "off" if not run else "warn" if run == "mine" and DELIRIUM.state == "error" else "on"
        except Exception:
            d = "off"
        b = self.breach_status()
        return {"delirium": d, "breach": "off" if b is False else "warn" if b == "warn" and self.br_reader is None
                else "on", "ritual": self.ritual_status(), "remnant": self.remnant_status()}

    def alerts_refresh(self):
        """Every 2 s (util_refresh) and after a change: dots, checkboxes and status lines."""
        rows = getattr(self, "al_rows", None)
        if not rows:
            return
        states = self.alert_states()
        try:
            from .utilities import DELIRIUM, STATES
            run = DELIRIUM.running()
            rows["delirium"]["on"].set(bool(run))
            if run == "other":
                dtxt = "On (the standalone PoE2DeliriumAlert.exe)"
            elif run == "mine":
                dtxt = "On - " + STATES.get(DELIRIUM.state, DELIRIUM.state or "starting…")
            elif DELIRIUM.lines and DELIRIUM.lines[-1].startswith("error"):
                dtxt = "It stopped: " + DELIRIUM.lines[-1][6:]
            else:
                dtxt = rows["delirium"]["what"]
        except Exception:
            dtxt = rows["delirium"]["what"]
        if rows["delirium"]["note"]:
            dtxt, rows["delirium"]["note"] = rows["delirium"]["note"], ""
        if not self.breach_cfg().get("on"):
            btxt = rows["breach"]["what"]
        elif self.br_reader is None:
            btxt = self.br_note or "On - looking for Client.txt…"
        elif self.br_win is not None:
            btxt = f"Warned at {time.strftime('%H:%M', time.localtime(max(self.br_last.values() or [time.time()])))}"
        elif self.breach_cfg().get("pending"):
            btxt = ("On - Hiveblood is waiting to be spent" + (": you'll be reminded when you leave the map"
                                                              if self.breach_cfg().get("leave_reminder", True) else ""))
        else:
            btxt = "On - watching for the game's Hiveblood warnings"
        rtxt = self.ritual_text(rows["ritual"])
        mtxt = rows["remnant"]["note"] or self.remnant_text(rows["remnant"])
        rows["remnant"]["note"] = ""
        rows["remnant"]["on"].set(bool(self.remnant_cfg().get("on")))
        for k, txt in (("delirium", dtxt), ("breach", btxt), ("ritual", rtxt), ("remnant", mtxt)):
            st = states[k]
            lbl = rows[k]["status"]                 # 2.37.0: a helper that's off (and has nothing to say) takes one line
            show = st != "off" or txt != rows[k]["what"]
            try:
                if show and not lbl.winfo_manager():
                    lbl.pack(fill="x", padx=(24, 8), after=rows[k]["row"])
                elif not show and lbl.winfo_manager():
                    lbl.pack_forget()
            except tk.TclError:
                pass
            rows[k]["dot"].config(fg=DOT[st])
            rows[k]["status"].config(text=txt, fg=C["red"] if st == "warn" else C["green"] if st == "on" else C["muted"])

    def ritual_text(self, row):
        from .utilities import RITUAL
        if row["note"]:
            txt, row["note"] = row["note"], ""
            return txt
        if not self.ritual_cfg().get("on"):
            return row["what"]
        if not RITUAL.running():
            last = RITUAL.lines[-1] if RITUAL.lines else ""
            return "It stopped" + (": " + last[6:] if last.startswith("error") else "") + " - switch it off and on."
        if RITUAL.state == "nogame":
            return "On - waiting for the game window"
        if RITUAL.state == "error":
            return "Screen capture problem: " + (RITUAL.lines[-1] if RITUAL.lines else "")
        if RITUAL.seen == "ok" and RITUAL.count:
            d, t = RITUAL.count
            return f"On - this map: {d} of {t} rituals done" + (" ✔" if d >= t else "")
        if RITUAL.seen == "unread":
            return ("On - the Ritual counter is on screen but couldn't be read. Make a problem report "
                    "(Settings > Advanced) while it shows so it can be fixed.")
        return "On - watching for the Ritual counter (it shows in maps with Ritual)"

    def ritual_seen(self):
        """Every second: remember the counter while you're in a map."""
        from .utilities import RITUAL
        if RITUAL.seen == "ok" and RITUAL.count and self.br_area in ("map", None):
            self.rt_map = RITUAL.count

    def alerts_overlay_redraw(self):
        if getattr(self, "tk_overlay", None) is not None:
            try:
                self.tracker_overlay_draw(self.tracker_numbers())
            except Exception:
                pass

    # ================================================================ Breach: following Client.txt
    def breach_start(self):
        """Follow Client.txt from its end (the Session tracker's file, or the one picked there)."""
        self.alerts_init()
        tc = getattr(self, "tracker_cfg", None)
        path = find_log(tc().get("log_path") if tc else None)
        if not path:
            self.br_reader = None
            self.br_note = ("On - but Client.txt wasn't found. Right-click the log line at the top of the Session "
                            "tracker to pick it.")
        else:
            self.br_reader = LogReader(path)
            self.br_reader.start()                    # only what the game writes from now on
            self.br_note = ""
        if not self._br_ticking:
            self._br_ticking = True
            self.root.after(1000, self.breach_tick)
        self.alerts_refresh()

    def breach_stop(self):
        if not self.log_wanted():
            self.br_reader = None
        self.breach_dismiss()
        self.alerts_refresh()

    def breach_tick(self):
        try:
            if self.ritual_cfg().get("on"):
                self.ritual_seen()
            if self.log_wanted():
                if self.br_reader is None:
                    self.br_ticks += 1
                    if self.br_ticks % RETRY_TICKS == 0:
                        self.breach_start()
                else:
                    for kind, _ts, data in self.br_reader.poll():
                        if kind == "breach" and "hiveblood" in data["text"].lower() and \
                                self.breach_cfg().get("on"):
                            self.breach_set_pending(breach_level(data["text"]))
                            self.breach_alert(text=data["text"])
                        elif kind == "brequel_tree":
                            self.breach_set_pending(None)          # spent (the tree was opened)
                            self.breach_dismiss()
                        elif kind == "area":
                            self.breach_area(gl_area_kind(data.get("area"), data.get("seed"), data.get("level", 0)),
                                             (data.get("area"), data.get("seed")))
        except Exception:
            self.log_error("breach alert")
        if self.log_wanted():
            self.root.after(1000, self.breach_tick)
        else:
            self._br_ticking = False

    def breach_set_pending(self, level):
        cfg = self.breach_cfg()
        if level == "almost" and cfg.get("pending") == "full":
            return
        if cfg.get("pending") != level:
            cfg["pending"] = level
            save_json("settings.json", SETTINGS)

    def breach_area(self, kind, where=None):
        """2.11.0: leaving a map (to your hideout or a town) with Hiveblood still waiting -> one reminder per exit,
        every exit, until the Genesis Tree has been opened."""
        before, self.br_area = self.br_area, kind
        try:
            self.fl_area(kind, where, before)                # 2.45.0: the Farm Ledger counts its runs
        except Exception:
            self.log_error("Farm Ledger run counting")
        cfg = self.breach_cfg()
        left = before == "map" and kind in ("hideout", "town")
        if left and cfg.get("on") and cfg.get("pending") and cfg.get("leave_reminder", True):
            self.breach_alert(level="leave")
        rc, got = self.ritual_cfg(), self.rt_map            # 2.14.0: rituals left undone in the map you just left
        # only when you started them (2.15.0: 0 done = you chose to skip Ritual in this map)
        if left and rc.get("on") and rc.get("leave_reminder", True) and got and 0 < got[0] < got[1]:
            self.root.after(9000 if cfg.get("on") and cfg.get("pending") else 0,
                            lambda g=got: self.breach_alert(level="ritual", sub=f"{g[0]} of {g[1]} done - go back "
                                                                                 f"through your portal"))
        if kind == "map" and before != "map":
            # a new map: its own count. 2.40.0: back into the SAME map (same area and seed - through your portal)
            # keeps it, so a quick in-and-out still reminds you
            if where is None or where != getattr(self, "rt_where", None):
                self.rt_map = None
            self.rt_where = where

    # ================================================================ Breach: the banner
    def breach_alert(self, text="Stored Hiveblood is almost at the maximum!", test=False, level=None, sub=None):
        self.alerts_init()
        level = level or breach_level(text)
        now = time.time()
        if not test:
            if level not in ("leave", "ritual") and now - self.br_last.get(level, 0) < REPEAT_SECS:
                return
            try:
                from .overlaywin import foreground_ok        # only over the game (Settings: "only while it's in front")
                if not foreground_ok():
                    return
            except Exception:
                pass
        self.br_last[level] = now
        if level == "full":
            self.br_last["almost"] = now                     # "almost" right after "full" adds nothing
        self.breach_dismiss()
        big_txt, small_txt, _bg, fg = LEVELS[level]
        small_txt = sub or small_txt
        win = tk.Toplevel(self.root)                   # 2.12.1: the Delirium alert's look - big flashing text straight
        win.overrideredirect(True)                     # over the game, no box, clicks go through to the game
        win.attributes("-topmost", True)
        win.configure(bg=TRANSPARENT)
        try:
            win.attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass
        ox, oy, sw, sh = game_rect() or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        ui = max(0.5, sh / 1440.0)
        big = tk.Label(win, text=big_txt, fg=fg, bg=TRANSPARENT, font=("Segoe UI Black", -int(80 * ui), "bold"))
        big.pack(fill="x")
        small = tk.Label(win, text=small_txt.split("  ·  ")[0], fg="#ffffff", bg=TRANSPARENT,
                         font=("Segoe UI Black", -int(30 * ui), "bold"))
        small.pack(fill="x")
        size = int(80 * ui)
        win.update_idletasks()
        while big.winfo_reqwidth() > sw * 0.94 and size > 24:      # always fits the game window, whatever the font
            size -= 4
            big.config(font=("Segoe UI Black", -size, "bold"))
            win.update_idletasks()
        w = max(big.winfo_reqwidth(), small.winfo_reqwidth()) + 40
        h = big.winfo_reqheight() + small.winfo_reqheight() + 10
        win.geometry(f"{w}x{h}+{ox + (sw - w) // 2}+{oy + int(sh * 0.22)}")
        win.update_idletasks()
        click_through(win)
        force_topmost(win)
        win.big, win.small = big, small
        self.br_win, self.br_level = win, level
        self._breach_flash(big, fg, True)
        if (self.ritual_cfg() if level == "ritual" else self.breach_cfg()).get("sound", True):
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONHAND if level == "full" else winsound.MB_ICONEXCLAMATION)
            except Exception:
                self.root.bell()
        self.alerts_refresh()
        self.alerts_overlay_redraw()
        secs = 5 if test else BANNER_SECS.get(level, 8)
        self.root.after(secs * 1000, lambda: self.br_win is win and self.breach_dismiss())

    def _breach_flash(self, lbl, fg, on):
        if self.br_win is None:
            return
        try:
            lbl.config(fg=fg if on else "#ffffff")
        except tk.TclError:
            return
        self.root.after(350, lambda: self._breach_flash(lbl, fg, not on))

    def breach_dismiss(self):
        w, self.br_win = getattr(self, "br_win", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass
            self.alerts_refresh()

    def breach_status(self):
        """False = off, True = watching, "warn" = a banner is up or Client.txt isn't found."""
        if not self.breach_cfg().get("on"):
            return False
        if getattr(self, "br_win", None) is not None or getattr(self, "br_reader", None) is None:
            return "warn"
        return True
