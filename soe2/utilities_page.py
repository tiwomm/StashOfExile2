"""The utility windows (2.0 beta 7): Chat commands and Notes (the POE2 Overlay, rebuilt, now two separate utilities)
and the Delirium alert (built in: see utilities.py / delirium_runner.py)."""
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import colorchooser, ttk

from .config import DATA_DIR, save_json, SETTINGS
from .overlay import MAX_COMMANDS, Overlay, parse_key
from .style import C, CAPTURING, KeyCapture
from .utilities import DELIRIUM, STATES


class UtilitiesPage:
    """Mixed into App."""

    def _ensure_overlay(self):
        if getattr(self, "overlay", None) is None:
            self.overlay = Overlay(self.root, SETTINGS, lambda: save_json("settings.json", SETTINGS),
                                   open_settings=self.open_utilities)
            self.overlay.lock_listener = lambda on: getattr(self, "note_lock", None) is not None and self.note_lock.set(on)
        return self.overlay

    def start_utilities(self):
        """Called once at start-up: chat commands and notes listen to the keyboard watcher; the Delirium alert may
        start too."""
        self._ensure_overlay()
        self.keys.listener = self.on_any_key         # 2.0 beta 9: the session tracker's keys come first
        from . import style as _st
        _st.CAPTURE_HOOK[0] = lambda waiting: (self.update_mouse_watch(True) if waiting else
                                               self.root.after(400, self.update_mouse_watch))
        self.update_mouse_watch()
        from . import overlay as _ov
        _ov.CLIP_HOOK[0] = self.ignore_clip              # chat commands paste through the clipboard (2.0 beta 8)
        if self.overlay.cfg.get("notes_enabled") and self.overlay.cfg.get("notes_visible"):
            self.root.after(800, self.overlay.show_notes)
        if SETTINGS.get("util_delirium_autostart"):
            self.root.after(1500, self.dl_do_start)
        self.root.after(2000, self.util_refresh)

    def on_any_key(self, vk, ctrl, alt, shift):
        """Every key you press (keyboard watcher thread). -> True if one of the utilities used it."""
        if CAPTURING[0] is not None:                   # a hotkey box is waiting: the key (or button) goes to it
            self.ui_q.put(("keycap", vk, ctrl, alt, shift))
            return True
        try:
            if self.quick_copy_key(vk, ctrl, alt, shift):
                return True
        except Exception:
            pass
        try:                                           # 2.2.0: the Regex key
            k = parse_key(SETTINGS.get("regex_key") or "")
            if k and k == (vk, ctrl, alt, shift):
                from .overlay import game_active, POE_TITLE
                if game_active((getattr(self, "overlay", None) and self.overlay.cfg.get("poe_title")) or POE_TITLE):
                    self.ui_q.put(("regexcopy",))
                    return True
        except Exception:
            pass
        try:
            if self.tracker_on_key(vk, ctrl, alt, shift):
                return True
        except Exception:
            pass
        return self.overlay.on_key(vk, ctrl, alt, shift)

    def ev_regexcopy(self):
        self.rx_hotkey_copy()

    def ev_keycap(self, vk, ctrl, alt, shift):
        box = CAPTURING[0]
        if box is not None:
            try:
                box.take(vk, ctrl, alt, shift)
            except tk.TclError:
                CAPTURING[0] = None

    def mouse_hotkeys_used(self):
        from .overlay import MOUSE_VKS
        for _what, key, _w, _id in self.all_hotkeys():
            k = parse_key(key) if key and key != "Ctrl+Alt+C" else None
            if k and k[0] in MOUSE_VKS:
                return True
        return False

    def update_mouse_watch(self, waiting=False):
        """The mouse hook is only on while a hotkey uses a mouse button, or a key box is waiting (2.0 beta 17)."""
        keys = getattr(self, "keys", None)
        if keys is None:
            return
        try:
            keys.set_mouse(waiting or self.mouse_hotkeys_used())
        except Exception:
            pass

    def quick_copy_key(self, vk, ctrl, alt, shift):
        """Price checks' one-key copy (2.0 beta 15): your key -> the game's Ctrl+Alt+C on the item under the mouse."""
        from .overlay import parse_key, game_active, send_copy, POE_TITLE
        k = parse_key(SETTINGS.get("quick_copy_key") or "")
        if not k or k != (vk, ctrl, alt, shift):
            return False
        if not game_active((getattr(self, "overlay", None) and self.overlay.cfg.get("poe_title")) or POE_TITLE):
            return False                                   # outside the game the key does its usual job
        def go():
            self.keys.combo_time = time.time()             # counts as your own Ctrl+Alt+C ("Ctrl+Alt+C only")
            send_copy()
        threading.Thread(target=go, daemon=True).start()
        return True

    def open_utilities(self, key="notes"):
        """The ⚙ on the note: bring the app up with the Notes window in front."""
        try:
            self.root.deiconify()
            self.root.lift()
        except Exception:
            pass
        self.shell.open(key)

    def stop_utilities(self):
        try:
            self.overlay.close()
        except Exception:
            pass
        DELIRIUM.stop()                                  # only if the app started it

    # ---------------- shared bits
    def _util_head(self, body, title_var, label, command, text):
        P2 = C["panel2"]
        top = tk.Frame(body, bg=P2, padx=14, pady=10, highlightthickness=1, highlightbackground=C["line"])
        top.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Checkbutton(top, text=label, variable=title_var, command=command).pack(side="left")
        st = tk.Label(top, text="", bg=P2, fg=C["muted"], anchor="w", font=("Segoe UI", 10, "bold"))
        st.pack(side="left", padx=12)
        tk.Label(body, text=text, bg=C["panel"], fg=C["muted"], anchor="w", justify="left", wraplength=600,
                 font=("Segoe UI", 9)).pack(fill="x", padx=12, pady=(0, 6))
        return st

    def _card(self, body, title, expand=False):
        P2 = C["panel2"]
        f = tk.Frame(body, bg=P2, padx=14, pady=10, highlightthickness=1, highlightbackground=C["line"])
        f.pack(fill="both" if expand else "x", expand=expand, padx=10, pady=(0, 8))
        if title:
            tk.Label(f, text=title, bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        return f

    def _ov_entry(self, parent, key, row, col, width=12):
        ov = self.overlay.cfg
        v = tk.StringVar(value=ov.get(key, ""))
        self.ov_vars[key] = v
        if key.endswith("_key"):                       # 2.0 beta 16: click and press the key
            KeyCapture(parent, v, width=width + 4, on_change=lambda t: self.root.after(10, self.ov_save)).grid(row=row, column=col, sticky="w", padx=(0, 10), pady=2)
            return v
        tk.Entry(parent, textvariable=v, width=width, bg=C["odd"], fg=C["text"], insertbackground=C["text"],
                 relief="flat", highlightthickness=1, highlightbackground=C["line"]).grid(
            row=row, column=col, sticky="w", padx=(0, 10), pady=2)
        return v

    # ---------------- the Chat commands window
    def build_chat_window(self, body):
        P2 = C["panel2"]
        ov = self._ensure_overlay().cfg
        self.ov_vars = getattr(self, "ov_vars", {})
        self.chat_on = tk.BooleanVar(value=bool(ov.get("chat_enabled")))
        self.chat_st = self._util_head(
            body, self.chat_on, "On", self.chat_toggle,
            "Keys that type a chat command into Path of Exile 2 - only while the game is the active window; anywhere "
            "else the key does what it normally does. Your POE2 Overlay (AutoHotkey) settings were read in the first "
            "time: close that script so both don't type the same command.")
        c1 = self._card(body, "Keys")
        g = tk.Frame(c1, bg=P2)
        g.pack(fill="x", pady=(4, 0))
        for r, (label, key) in enumerate((("Go to hideout", "hideout_key"), ("Game window title", "poe_title"))):
            tk.Label(g, text=label, bg=P2, fg=C["text"], anchor="w").grid(row=r, column=0, sticky="w", padx=(0, 10))
            self._ov_entry(g, key, r, 1, 18 if key == "poe_title" else 10)
        tk.Label(g, text="Click a key box and press the key you want (with Ctrl / Alt / Shift if you like). "
                         "Esc keeps the old one; Backspace or right-click clears it.", bg=P2, fg=C["muted"], font=("Segoe UI", 8)).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(2, 0))
        c2 = self._card(body, "Your chat commands", expand=True)
        cg = tk.Frame(c2, bg=P2)
        cg.pack(fill="x", pady=(4, 0))
        for col, t in enumerate(("Name", "Key", "Command (e.g. /leave  /dnd  /invite Name)")):
            tk.Label(cg, text=t, bg=P2, fg=C["muted"], font=("Segoe UI", 8, "bold"), anchor="w").grid(row=0, column=col, sticky="w")
        cmds = ov.get("commands", [])
        self.ov_cmd_vars = []
        for i in range(MAX_COMMANDS):
            c = cmds[i] if i < len(cmds) else {}
            row = []
            for col, (k, w) in enumerate((("name", 14), ("key", 8), ("cmd", 34))):
                v = tk.StringVar(value=c.get(k, ""))
                if k == "key":
                    KeyCapture(cg, v, width=12, on_change=lambda t: self.root.after(10, self.ov_save)).grid(row=i + 1, column=col, sticky="w", padx=(0, 8), pady=1)
                    row.append(v)
                    continue
                tk.Entry(cg, textvariable=v, width=w, bg=C["odd"], fg=C["text"], insertbackground=C["text"], relief="flat",
                         highlightthickness=1, highlightbackground=C["line"]).grid(row=i + 1, column=col, sticky="w",
                                                                                  padx=(0, 8), pady=1)
                row.append(v)
            self.ov_cmd_vars.append(row)
        brow = tk.Frame(body, bg=C["panel"])
        brow.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(brow, text="Save & apply", style="Accent.TButton", command=self.ov_save).pack(side="left")
        self.ov_msg = tk.Label(brow, text="", bg=C["panel"], fg=C["muted"], anchor="w")
        self.ov_msg.pack(side="left", fill="x", expand=True, padx=10)

    # ---------------- the Notes window
    def build_notes_window(self, body):
        P2 = C["panel2"]
        ov = self._ensure_overlay().cfg
        self.ov_vars = getattr(self, "ov_vars", {})
        self.notes_on = tk.BooleanVar(value=bool(ov.get("notes_enabled")))
        self.notes_st = self._util_head(
            body, self.notes_on, "On", self.notes_toggle,
            "A sticky note over the game. Show / hide it with its key (in game) or the button below. It hides while "
            "the game is closed and comes back with it. Drag it by its top bar and resize it from any edge, or type "
            "its place and size below. What you type on it is saved by itself; every option is here.")
        c1 = self._card(body, "Key")
        g = tk.Frame(c1, bg=P2)
        g.pack(fill="x", pady=(4, 0))
        tk.Label(g, text="Show / hide notes", bg=P2, fg=C["text"], anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self._ov_entry(g, "notes_key", 0, 1, 10)
        ttk.Button(g, text="Show / hide now", command=lambda: self.overlay.toggle_notes()).grid(row=0, column=2, sticky="w")
        c2 = self._card(body, "Look")
        self.build_notes_look(c2)
        c3 = self._card(body, "Position")
        lrow = tk.Frame(c3, bg=P2)
        lrow.pack(fill="x", pady=(4, 0))
        self.note_lock = tk.BooleanVar(value=bool(ov.get("notes_locked")))
        ttk.Checkbutton(lrow, text="Lock it (can't be moved or resized by accident)", variable=self.note_lock,
                        command=lambda: self.overlay.set_locked(self.note_lock.get())).pack(side="left")
        ttk.Button(lrow, text="Put it back in the corner", command=self.note_reset).pack(side="right")
        tk.Label(c3, text="Drag the note by its top bar and resize it from any edge; it remembers where you leave it.",
                 bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(6, 0))
        brow = tk.Frame(body, bg=C["panel"])
        brow.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(brow, text="Save & apply", style="Accent.TButton", command=self.ov_save).pack(side="left")
        self.ov_msg2 = tk.Label(brow, text="", bg=C["panel"], fg=C["muted"], anchor="w")
        self.ov_msg2.pack(side="left", fill="x", expand=True, padx=10)

    def build_notes_look(self, parent):
        """The note's colours, opacity and font size (in the Notes window; Save & apply puts them on the note)."""
        P2 = C["panel2"]
        ov = self._ensure_overlay().cfg
        self.ov_vars = getattr(self, "ov_vars", {})
        ng = tk.Frame(parent, bg=P2)
        ng.pack(fill="x", pady=(2, 0))
        self.ov_swatch = {}
        for r, (label, key, default) in enumerate((("Background", "notes_bg", "1A1A2E"), ("Text colour", "notes_fg", "E2C97E"))):
            tk.Label(ng, text=label, bg=P2, fg=C["text"], anchor="w").grid(row=r, column=0, sticky="w", padx=(0, 10), pady=2)
            sw = tk.Label(ng, text="", width=3, bg=self.overlay._colour(key, default), relief="flat",
                          highlightthickness=1, highlightbackground=C["line"])
            sw.grid(row=r, column=1, sticky="w")
            self.ov_swatch[key] = sw
            v = self._ov_entry(ng, key, r, 2, 8)
            v.trace_add("write", lambda *_a, k=key: self._ov_swatch(k))
            ttk.Button(ng, text="Pick…", command=lambda k=key: self.ov_pick(k)).grid(row=r, column=3, sticky="w")
        tk.Label(ng, text="Opacity", bg=P2, fg=C["text"], anchor="w").grid(row=2, column=0, sticky="w", pady=2)
        self.ov_opacity = tk.IntVar(value=int(ov.get("notes_opacity", 215)))
        ttk.Scale(ng, from_=40, to=255, variable=self.ov_opacity, orient="horizontal", length=150).grid(
            row=2, column=1, columnspan=3, sticky="w")
        tk.Label(ng, text="Font size", bg=P2, fg=C["text"], anchor="w").grid(row=3, column=0, sticky="w", pady=2)
        self.ov_font = tk.IntVar(value=int(ov.get("notes_font", 11)))
        ttk.Spinbox(ng, from_=8, to=24, textvariable=self.ov_font, width=5).grid(row=3, column=1, columnspan=2, sticky="w")

    def open_settings_tab(self, name):
        self.shell.open("settings")
        try:
            self.set_nb.select(self.set_nb.titles.index(name))
        except (AttributeError, ValueError):
            pass

    # ---------------- the Delirium alert window
    def build_delirium_window(self, body):
        P2 = C["panel2"]
        self.dl_on = tk.BooleanVar(value=False)
        self.dl_status = self._util_head(
            body, self.dl_on, "On", lambda: self.dl_do_start() if self.dl_on.get() else self.dl_do_stop(),
            "Shows a big flashing END DELIRIUM when you complete a map while the Delirium fast-forward arrows are on "
            "screen. It only looks at your screen (no input, no game files). Run the game in Windowed Fullscreen / "
            "Borderless. It runs next to the app as its own process, so it never slows the price checker down.")
        c1 = self._card(body, "Controls")
        drow = tk.Frame(c1, bg=P2)
        drow.pack(fill="x", pady=(6, 0))
        self.dl_start = ttk.Button(drow, text="Start", style="Accent.TButton", command=self.dl_do_start)
        self.dl_start.pack(side="left")
        self.dl_stop = ttk.Button(drow, text="Stop", command=self.dl_do_stop)
        self.dl_stop.pack(side="left", padx=6)
        ttk.Button(drow, text="Test alert (5 s)", command=self.dl_do_test).pack(side="left")
        prow = tk.Frame(c1, bg=P2)
        prow.pack(fill="x", pady=(8, 0))
        self.dl_move = ttk.Button(prow, text="Move the splinter", command=lambda: self.dl_send("move", "Drag the splinter "
                                  "where you want it, then click it to drop it."))
        self.dl_move.pack(side="left")
        self.dl_reset = ttk.Button(prow, text="Reset its position", command=lambda: self.dl_send("reset_pos", "Splinter back "
                                   "in its default place."))
        self.dl_reset.pack(side="left", padx=6)
        c2 = self._card(body, "Options")
        self.dl_auto = tk.BooleanVar(value=bool(SETTINGS.get("util_delirium_autostart")))
        ttk.Checkbutton(c2, text="Start it with StashOfExile2", variable=self.dl_auto,
                        command=lambda: (SETTINGS.__setitem__("util_delirium_autostart", bool(self.dl_auto.get())),
                                         save_json("settings.json", SETTINGS))).pack(anchor="w", pady=(6, 0))
        self.dl_sound = tk.BooleanVar(value=DELIRIUM.get_sound())
        ttk.Checkbutton(c2, text="Sound (once per map)", variable=self.dl_sound, command=self.dl_set_sound).pack(anchor="w")
        self.dl_ind = tk.BooleanVar(value=DELIRIUM.get_indicator())
        ttk.Checkbutton(c2, text="Show the splinter on screen (its colour shows what it sees)", variable=self.dl_ind,
                        command=self.dl_set_indicator).pack(anchor="w")
        c3 = self._card(body, "", expand=True)
        self.dl_msg = tk.Label(c3, text="", bg=P2, fg=C["muted"], anchor="nw", justify="left", wraplength=560,
                               font=("Segoe UI", 9))
        self.dl_msg.pack(fill="both", expand=True)
        tk.Label(c3, text="Log: " + os.path.join(DATA_DIR, "delirium", "delirium_log.txt"), bg=P2, fg=C["steel"],
                 anchor="w", font=("Segoe UI", 8)).pack(fill="x", side="bottom")
        self.util_refresh()

    # ---------------- chat commands & notes
    def chat_toggle(self):
        self.overlay.set_chat(self.chat_on.get())
        self.util_refresh()

    def notes_toggle(self):
        self.overlay.set_notes(self.notes_on.get())
        self.util_refresh()

    def ov_toggle(self):
        """Both on / off (2.0 beta 6 had one switch)."""
        on = bool(getattr(self, "ov_on", None) and self.ov_on.get())
        self.chat_on.set(on)
        self.notes_on.set(on)
        self.overlay.set_enabled(on)
        self.util_refresh()

    def ov_save(self):
        cfg, bad = self.overlay.cfg, []
        for key in ("hideout_key", "notes_key"):
            k = self.ov_vars[key].get().strip()
            if k and not parse_key(k):
                bad.append(k)
            cfg[key] = k
        cfg["poe_title"] = self.ov_vars["poe_title"].get().strip() or "Path of Exile 2"
        cmds = []
        for name, key, cmd in self.ov_cmd_vars:
            k, c = key.get().strip(), cmd.get().strip()
            if k and c:
                if not parse_key(k):
                    bad.append(k)
                cmds.append({"name": name.get().strip(), "key": k, "cmd": c})
        cfg["commands"] = cmds
        for key in ("notes_bg", "notes_fg"):
            cfg[key] = self.ov_vars[key].get().strip().lstrip("#") or cfg.get(key)
        cfg["notes_opacity"] = int(self.ov_opacity.get())
        try:
            cfg["notes_font"] = max(8, min(24, int(self.ov_font.get())))
        except (ValueError, tk.TclError):
            pass
        self.overlay._store_geometry()                      # what you dragged / typed on the note so far
        if hasattr(self, "note_geo"):
            for key, v in self.note_geo.items():
                try:
                    n = int(float(v.get().strip()))
                except ValueError:
                    bad.append(f"{key[6:]} '{v.get()}'")
                    continue
                cfg[key] = max(140 if key == "notes_w" else 80 if key == "notes_h" else -10000, n)
        if hasattr(self, "note_lock"):
            cfg["notes_locked"] = bool(self.note_lock.get())
        self.overlay.rebind()
        self.overlay.restyle(store=False)
        self.overlay.save_settings()
        DELIRIUM.set_title(cfg["poe_title"])
        for lbl in (self.ov_msg, self.ov_msg2):
            lbl.config(text=("Saved. Not understood: " + ", ".join(bad)) if bad else "Saved and applied.",
                       fg=C["red"] if bad else C["green"])
        self.util_refresh()

    def note_reset(self):
        """2.0.0: no pixel boxes any more - put the note back at the top left, at its first size."""
        self.overlay.cfg.update(notes_x=50, notes_y=50, notes_w=300, notes_h=200)
        self.overlay.restyle(store=False)
        self.overlay.save_settings()
        self.ov_msg2.config(text="The note is back at the top left.", fg=C["green"])

    def _note_geo_refresh(self):
        """Show where the note is now (you may have dragged it), unless you are typing in those boxes."""
        try:
            focus = str(self.root.focus_get() or "")
        except Exception:
            focus = ""
        if not hasattr(self, "note_geo") or "entry" in focus.lower():
            return
        self.overlay._store_geometry() if self.overlay.notes_shown() else None
        for key, v in self.note_geo.items():
            if v.get() != str(self.overlay.cfg.get(key, "")):
                v.set(str(self.overlay.cfg.get(key, "")))

    def _ov_swatch(self, key):
        v = self.ov_vars[key].get().strip().lstrip("#")
        if len(v) == 6:
            try:
                self.ov_swatch[key].config(bg="#" + v)
            except tk.TclError:
                pass

    def ov_pick(self, key):
        cur = "#" + (self.ov_vars[key].get().strip().lstrip("#") or "000000")
        try:
            _rgb, hexv = colorchooser.askcolor(color=cur, parent=self.root, title="Pick a colour")
        except tk.TclError:
            hexv = None
        if hexv:
            self.ov_vars[key].set(hexv.lstrip("#").upper())

    # ---------------- delirium alert
    def dl_do_start(self):
        err = DELIRIUM.start()
        self.dl_msg.config(text=err or "Starting… the splinter shows on screen once it is watching.",
                           fg=C["red"] if err else C["green"])
        self.root.after(1200, self.util_refresh)

    def dl_do_stop(self):
        err = DELIRIUM.stop()
        self.dl_msg.config(text=err or "Stopped.", fg=C["red"] if err else C["muted"])
        self.util_refresh()

    def dl_do_test(self):
        err = DELIRIUM.test_alert()
        self.dl_msg.config(text=err or "The END DELIRIUM banner shows for 5 seconds.", fg=C["red"] if err else C["muted"])

    def dl_send(self, cmd, ok):
        if DELIRIUM.send(cmd):
            self.dl_msg.config(text=ok, fg=C["muted"])
        else:
            self.dl_msg.config(text="Start it first.", fg=C["muted"])

    def dl_set_sound(self):
        DELIRIUM.set_sound(self.dl_sound.get())
        self.dl_msg.config(text="Saved.", fg=C["muted"])

    def dl_set_indicator(self):
        DELIRIUM.set_indicator(self.dl_ind.get())
        self.dl_msg.config(text="Saved.", fg=C["muted"])

    # ---------------- status (dots on the dock / taskbar, and the windows), every 2 s
    def chat_status(self):
        cfg = self.overlay.cfg if getattr(self, "overlay", None) else {}
        if not cfg.get("chat_enabled"):
            return False
        keys = getattr(self, "keys", None)
        return True if (sys.platform != "win32" or (keys is not None and keys.active)) else "warn"

    def notes_status(self):
        cfg = self.overlay.cfg if getattr(self, "overlay", None) else {}
        return bool(cfg.get("notes_enabled"))

    def delirium_status(self):
        r = DELIRIUM.running()
        if not r:
            return False
        return "warn" if r == "mine" and DELIRIUM.state in ("alert", "error") else True

    def util_refresh(self):
        if not hasattr(self, "dl_status") or not hasattr(self, "chat_st"):
            return
        state = DELIRIUM.running()
        cmd, why = DELIRIUM.locate()
        if state == "other":
            text, col = "Running (the standalone PoE2DeliriumAlert.exe)", C["green"]
        elif state == "mine":
            text = STATES.get(DELIRIUM.state, DELIRIUM.state)
            col = C["red"] if DELIRIUM.state in ("alert", "error") else C["good"] if DELIRIUM.state == "nogame" else C["green"]
            last = DELIRIUM.last_message()
            if last and self.dl_msg.cget("fg") != C["red"]:
                self.dl_msg.config(text=last, fg=C["muted"])
        elif cmd is None:
            text, col = "Can't run here", C["red"]
            self.dl_msg.config(text=why, fg=C["red"])
        else:
            text, col = "Off", C["muted"]
            if DELIRIUM.lines and DELIRIUM.lines[-1].startswith("error"):
                self.dl_msg.config(text="It stopped: " + DELIRIUM.lines[-1][6:], fg=C["red"])
        self.dl_status.config(text=text, fg=col)
        self.dl_on.set(bool(state))
        self.dl_start.config(state="disabled" if state or cmd is None else "normal")
        self.dl_stop.config(state="normal" if state == "mine" else "disabled")
        for b in (self.dl_move, self.dl_reset):
            b.config(state="normal" if state == "mine" else "disabled")
        cfg = self.overlay.cfg
        if not cfg.get("chat_enabled"):
            st, col = "Off", C["muted"]
        elif sys.platform != "win32":
            st, col = "On (keys work on Windows only)", C["good"]
        elif getattr(self, "keys", None) is None or not self.keys.active:
            keys = getattr(self, "keys", None)
            st, col = ("Starting…", C["muted"]) if keys is None or keys.err is None else \
                ("On, but the keyboard watcher isn't running: " + (keys.err or "unknown reason"), C["red"])
        else:
            n = sum(1 for a in self.overlay.bindings.values() if a[0] == "chat")
            st, col = f"On: {n} key{'s' if n != 1 else ''} active", C["green"]
        self.chat_st.config(text=st, fg=col)
        if not cfg.get("notes_enabled"):
            st, col = "Off", C["muted"]
        else:
            vis = self.overlay.notes_shown()
            st, col = ("On: showing over the game" if vis else "On: hidden (its key brings it back)"), C["green"]
        self.notes_st.config(text=st, fg=col)
        self._note_geo_refresh()
        self.chat_on.set(bool(cfg.get("chat_enabled")))
        self.notes_on.set(bool(cfg.get("notes_enabled")))
        if getattr(self, "_util_job", None):
            self.root.after_cancel(self._util_job)
        self._util_job = self.root.after(2000, self.util_refresh)
