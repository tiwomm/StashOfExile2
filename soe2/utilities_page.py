"""The utility windows (2.0 beta 7): Chat commands and Notes (the POE2 Overlay, rebuilt, now two separate utilities)
(the Delirium alert lives in the Session tracker since 2.10.0: alerts_page.py)."""
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

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
            self.overlay.merged_host = self              # 2.55.0: Notes can sit inside the one overlay window
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
        self.alerts_init()                               # 2.10.0: the Breach alert starts here if it's on
        self.root.after(1500, self.tracker_helpers_sync)  # 2.49.0: the Mechanic Helper bar, if its switch is on
        self.root.after(2000, self.util_refresh)

    def on_any_key(self, vk, ctrl, alt, shift):
        """Every key you press (keyboard watcher thread). -> True if one of the utilities used it."""
        if CAPTURING[0] is not None:                   # a hotkey box is waiting: the key (or button) goes to it
            self.ui_q.put(("keycap", vk, ctrl, alt, shift))
            return True
        try:
            if self.pc_hotkey(vk, ctrl, alt, shift):
                return True
        except Exception:
            pass
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
        try:                                           # 2.12.0: the poe2db key - in game or in the app only
            k = parse_key(SETTINGS.get("poe2db_key") or "")
            if k and k == (vk, ctrl, alt, shift):
                from .overlay import game_active, POE_TITLE
                if game_active((getattr(self, "overlay", None) and self.overlay.cfg.get("poe_title")) or POE_TITLE) \
                        or self.app_in_front():
                    self.ui_q.put(("quicklink", "poe2db"))
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

    def pc_hotkey(self, vk, ctrl, alt, shift):
        """2.83.1: the price check key (Ctrl+D) in game -> the game's own Ctrl+Alt+C once (one key press, one item
        copied, with its mod tiers); the copy goes to Price Checks, not Bulk Pricing."""
        from .overlay import parse_key, game_active, send_copy, POE_TITLE
        from .pricecheck_page import pc_key_is_copy
        if not SETTINGS.get("pc_ctrl_c", True) or pc_key_is_copy():
            return False                                   # Ctrl+C: the game copies, the app only listens
        k = parse_key(SETTINGS.get("pc_key") or "")
        if not k or k != (vk, ctrl, alt, shift):
            return False
        if not game_active((getattr(self, "overlay", None) and self.overlay.cfg.get("poe_title")) or POE_TITLE):
            return False                                   # outside the game the key does its usual job
        def go():
            self.keys.pc_time = time.time()
            send_copy()
        threading.Thread(target=go, daemon=True).start()
        return True

    def quick_copy_key(self, vk, ctrl, alt, shift):
        """Price checks' one-key copy (2.0 beta 15) - 2.98.3: gone (not a viable way to copy). Never acts."""
        return False
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
        try:
            from .utilities import RITUAL                # 2.14.0
            RITUAL.stop()
        except Exception:
            pass

    # ---------------- shared bits
    def _util_head(self, body, title_var, label, command, text):
        P2 = C["panel2"]
        top = tk.Frame(body, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
        top.pack(fill="x", padx=8, pady=(8, 8))
        ttk.Checkbutton(top, text=label, variable=title_var, command=command).pack(side="left")
        st = tk.Label(top, text="", bg=P2, fg=C["muted"], anchor="w", font=("Segoe UI", 10, "bold"))
        st.pack(side="left", padx=12)
        tk.Label(body, text=text, bg=C["panel"], fg=C["muted"], anchor="w", justify="left", wraplength=600,
                 font=("Segoe UI", 9)).pack(fill="x", padx=12, pady=(0, 8))
        return st

    def _card(self, body, title, expand=False):
        P2 = C["panel2"]
        f = tk.Frame(body, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
        f.pack(fill="both" if expand else "x", expand=expand, padx=8, pady=(0, 8))
        if title:
            tk.Label(f, text=title, bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        return f

    def _ov_entry(self, parent, key, row, col, width=12):
        ov = self.overlay.cfg
        v = tk.StringVar(value=ov.get(key, ""))
        self.ov_vars[key] = v
        if key.endswith("_key"):                       # 2.0 beta 16: click and press the key
            KeyCapture(parent, v, width=width + 4, on_change=lambda t: self.root.after(10, self.ov_save)).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=2)
            return v
        tk.Entry(parent, textvariable=v, width=width, bg=C["odd"], fg=C["text"], insertbackground=C["text"],
                 relief="flat", highlightthickness=1, highlightbackground=C["line"]).grid(
            row=row, column=col, sticky="w", padx=(0, 8), pady=2)
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
        # 2.59.0: the game window title is set in Settings › General › Game
        self.ov_vars["poe_title"] = tk.StringVar(value=ov.get("poe_title", "") or "Path of Exile 2")
        # 2.61.1: the keys are set right here again (click the box, press the key) - and in Settings › Hotkeys;
        # a key that something else already uses turns red and says what has it
        from .style import KeyCapture
        self.ov_vars["hideout_key"] = tk.StringVar(value=ov.get("hideout_key", ""))
        self.chat_keys_lbl = tk.Label(g, text="Go to hideout", bg=P2, fg=C["text"], anchor="w")
        self.chat_keys_lbl.grid(row=1, column=0, sticky="w", pady=(4, 0), padx=(0, 8))
        self.chat_hideout_kc = KeyCapture(g, self.ov_vars["hideout_key"], width=14,
                                          on_change=lambda t: self.root.after(10, self.chat_key_set))
        self.chat_hideout_kc.grid(row=1, column=1, sticky="w", pady=(4, 0))
        tk.Label(g, text="Click a key box and press the key; right-click clears it. All keys: Settings › Hotkeys.",
                 bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w").grid(row=2, column=0, columnspan=3,
                                                                              sticky="w", pady=(4, 0))
        c2 = self._card(body, "Your chat commands", expand=True)
        cg = tk.Frame(c2, bg=P2)
        cg.pack(fill="x", pady=(4, 0))
        for col, t in enumerate(("Name", "Key", "Command (e.g. /leave  /dnd  /invite Name)")):
            tk.Label(cg, text=t, bg=P2, fg=C["muted"], font=("Segoe UI", 9, "bold"), anchor="w").grid(row=0, column=col, sticky="w")
        cmds = ov.get("commands", [])
        self.ov_cmd_vars, self.chat_key_boxes = [], []
        for i in range(MAX_COMMANDS):
            c = cmds[i] if i < len(cmds) else {}
            row = []
            for col, (k, w) in enumerate((("name", 14), ("key", 8), ("cmd", 34))):
                v = tk.StringVar(value=c.get(k, ""))
                if k == "key":                          # 2.61.1: set here (or in Settings › Hotkeys)
                    kc = KeyCapture(cg, v, width=12, on_change=lambda t: self.root.after(10, self.chat_key_set))
                    kc.grid(row=i + 1, column=col, sticky="w", padx=(0, 8), pady=1)
                    self.chat_key_boxes.append(kc)
                    row.append(v)
                    continue
                tk.Entry(cg, textvariable=v, width=w, bg=C["odd"], fg=C["text"], insertbackground=C["text"], relief="flat",
                         highlightthickness=1, highlightbackground=C["line"]).grid(row=i + 1, column=col, sticky="w",
                                                                                  padx=(0, 8), pady=1)
                v.trace_add("write", lambda *_a: self.ov_save_soon())   # 2.59.0: saves as you type
                row.append(v)
            self.ov_cmd_vars.append(row)
        brow = tk.Frame(body, bg=C["panel"])
        brow.pack(fill="x", padx=8, pady=(0, 8))
        self.ov_msg = tk.Label(brow, text="Changes save by themselves.", bg=C["panel"], fg=C["muted"], anchor="w")
        self.ov_msg.pack(side="left", fill="x", expand=True, padx=8)
        self._chat_keys_text()
        self.root.after(50, self.chat_key_marks)

    def chat_key_set(self):
        """2.61.1: a chat key was set in a box here - save, keep Settings › Hotkeys in step, warn about clashes."""
        self.ov_save()
        if hasattr(self, "hk_frame"):
            try:
                self.fill_hotkeys()
            except Exception:
                pass
        self.chat_key_marks()

    def chat_key_marks(self):
        """Paint a key box red when another hotkey uses the same key, and say which one has it."""
        from .overlay import key_label, parse_key
        uses = {}
        for what, key, _w, kid in self.all_hotkeys():
            k = parse_key(key) if key and key != "Ctrl+Alt+C" else ((0x43, True, True, False) if key == "Ctrl+Alt+C" else None)
            if k:
                uses.setdefault(k, []).append((what, kid))
        boxes = [("overlay:hideout_key", getattr(self, "chat_hideout_kc", None), self.ov_vars.get("hideout_key"))]
        boxes += [(f"cmd:{i}", kc, self.ov_cmd_vars[i][1]) for i, kc in enumerate(getattr(self, "chat_key_boxes", []))]
        msgs = []
        for kid, kc, var in boxes:
            if kc is None or not kc.winfo_exists():
                continue
            k = parse_key(var.get()) if var.get().strip() else None
            others = [w for w, oid in uses.get(k, []) if oid != kid] if k else []
            if others and not kc.waiting:
                kc.config(fg=C["red"], highlightbackground=C["red"])
                msgs.append(f"{key_label(var.get())} is already used by \"{others[0]}\"")
        if msgs and getattr(self, "ov_msg", None) is not None:
            self.ov_msg.config(text="⚠ " + "; ".join(msgs) + " - pick another key, or right-click one to clear it.",
                               fg=C["red"])
        return msgs

    def _chat_keys_text(self):
        ov = self.overlay.cfg
        k = ov.get("hideout_key", "")
        self.ov_vars["hideout_key"].set(k)
        for n, c in enumerate(ov.get("commands", []) or []):
            if n < len(getattr(self, "ov_cmd_vars", [])):
                self.ov_cmd_vars[n][1].set(c.get("key", ""))
        if getattr(self, "chat_hideout_kc", None) is not None:
            self.root.after(20, self.chat_key_marks)

    def open_settings_tab(self, name):
        self.shell.open("settings")
        try:
            self.set_nb.select(self.set_nb.titles.index(name))
        except (AttributeError, ValueError):
            pass

    # ---------------- chat commands & notes
    def chat_toggle(self):
        self.overlay.set_chat(self.chat_on.get())
        self.util_refresh()

    def ov_toggle(self):
        """Both on / off (2.0 beta 6 had one switch)."""
        on = bool(getattr(self, "ov_on", None) and self.ov_on.get())
        self.chat_on.set(on)
        self.overlay.set_enabled(on)
        self.util_refresh()

    def ov_save(self):
        cfg, bad = self.overlay.cfg, []
        for key in ("hideout_key",):
            k = self.ov_vars[key].get().strip()
            if k and not parse_key(k):
                bad.append(k)
            cfg[key] = k
        cfg["poe_title"] = self.ov_vars["poe_title"].get().strip() or "Path of Exile 2"
        cmds = []
        for name, key, cmd in self.ov_cmd_vars:            # 2.61.1: every row keeps its place (row n = command n,
            n_, k, c = name.get().strip(), key.get().strip(), cmd.get().strip()   # the Hotkeys page's cmd:n), and a
            if k and not parse_key(k):                     # command is kept before it has a key
                bad.append(k)
            cmds.append({"name": n_, "key": k, "cmd": c})
        while cmds and not any(cmds[-1].values()):
            cmds.pop()
        cfg["commands"] = cmds
        self.overlay._store_geometry()                      # what you dragged / typed on the note so far
        if hasattr(self, "note_geo"):
            for key, v in self.note_geo.items():
                try:
                    n = int(float(v.get().strip()))
                except ValueError:
                    bad.append(f"{key[6:]} '{v.get()}'")
                    continue
                cfg[key] = max(140 if key == "notes_w" else 80 if key == "notes_h" else -10000, n)
        self.overlay.rebind()
        self.overlay.restyle(store=False)
        self.overlay.save_settings()
        DELIRIUM.set_title(cfg["poe_title"])
        for lbl in (self.ov_msg,):
            lbl.config(text=("Saved. Not understood: " + ", ".join(bad)) if bad else "Saved.",
                       fg=C["red"] if bad else C["green"])
        self.util_refresh()

    def ov_save_soon(self):
        """2.59.0: no Save & apply - a chat command saves a moment after you stop typing."""
        if getattr(self, "_ov_save_job", None):
            try:
                self.root.after_cancel(self._ov_save_job)
            except tk.TclError:
                pass
        self._ov_save_job = self.root.after(700, self._ov_save_now)

    def _ov_save_now(self):
        self._ov_save_job = None
        if len(getattr(self, "ov_cmd_vars", [])) == MAX_COMMANDS:
            self.ov_save()

    def app_in_front(self):
        """Is one of the app's own windows the one in front? (keyboard watcher thread: Win32 only, no Tk calls)"""
        if sys.platform != "win32":
            return False
        try:
            import ctypes
            u = ctypes.windll.user32
            pid = ctypes.c_ulong()
            u.GetWindowThreadProcessId(u.GetForegroundWindow(), ctypes.byref(pid))
            return pid.value == os.getpid()
        except Exception:
            return False

    def ev_quicklink(self, which):
        from .listkit import open_poe2db
        if which == "poe2db" and open_poe2db():
            self._say("Opened poe2db's modifier list in your browser.", 5)

    # ---------------- delirium alert (2.10.0: no window of its own - Session tracker > Alerts switches it)
    def dl_do_start(self):
        """-> None, or why it couldn't start."""
        err = DELIRIUM.start()
        self.root.after(1200, self.util_refresh)
        return err

    def dl_do_stop(self):
        err = DELIRIUM.stop()
        self.root.after(200, self.util_refresh)
        return err

    def dl_do_test(self):
        return DELIRIUM.test_alert()

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
        if getattr(self, "_util_job", None):
            self.root.after_cancel(self._util_job)
        self._util_job = self.root.after(2000, self.util_refresh)
        refresh = getattr(self, "alerts_refresh", None)          # 2.10.0: the Alerts panel in the Session tracker
        if refresh:
            refresh()
        if not hasattr(self, "chat_st"):
            return
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
        self.chat_on.set(bool(cfg.get("chat_enabled")))
