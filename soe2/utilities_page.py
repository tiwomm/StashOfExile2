"""The utility windows (2.0 beta 7): Chat commands and Notes (the POE2 Overlay, rebuilt, now two separate utilities)
(the Delirium alert lives in the Session tracker since 2.10.0: alerts_page.py)."""
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from . import buglog
from .config import save_json, SETTINGS
from .overlay import MAX_COMMANDS, Overlay, parse_key
from .style import C, CAPTURING
from .utilities import DELIRIUM


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
            buglog.caught()
        try:
            if self.pc_close_hotkey(vk, ctrl, alt, shift):    # 2.121.1: the price check card's close key (Esc)
                return True
        except Exception:
            buglog.caught()
        from . import features as FEAT
        if not FEAT.on("overlay"):                     # 2.131.0: the Game Overlay is off - its keys do nothing
            return False
        try:                                           # 2.132.6: Regex keys (were one Regex key that copied)
            i = self.rx_key_hit(vk, ctrl, alt, shift)
            if i is not None:
                from .overlay import game_active, POE_TITLE
                if game_active((getattr(self, "overlay", None) and self.overlay.cfg.get("poe_title")) or POE_TITLE):
                    self.ui_q.put(("regexkey", i))
                    return True
        except Exception:
            buglog.caught()
        try:                                           # 2.131.1: the Top Up key - copies the item to teach it
            if self.topup_hotkey(vk, ctrl, alt, shift):
                return True
        except Exception:
            buglog.caught()
        try:                                           # 2.12.0: the poe2db key - in game or in the app only
            k = parse_key(SETTINGS.get("poe2db_key") or "")
            if k and k == (vk, ctrl, alt, shift):
                from .overlay import game_active, POE_TITLE
                if game_active((getattr(self, "overlay", None) and self.overlay.cfg.get("poe_title")) or POE_TITLE) \
                        or self.app_in_front():
                    self.ui_q.put(("quicklink", "poe2db"))
                    return True
        except Exception:
            buglog.caught()
        try:
            if self.tracker_on_key(vk, ctrl, alt, shift):
                return True
        except Exception:
            buglog.caught()
        return self.overlay.on_key(vk, ctrl, alt, shift)

    def ev_regexkey(self, i):
        self.rx_key_press(i)

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
            buglog.caught()

    def pc_hotkey(self, vk, ctrl, alt, shift):
        """2.83.1: the price check key (Ctrl+D) in game -> the game's own Ctrl+Alt+C once (one key press, one item
        copied, with its mod tiers); the copy goes to Price Checks, not Bulk Pricing."""
        from .overlay import parse_key, game_active, send_copy, POE_TITLE
        from .pricecheck_page import pc_key_is_copy
        from . import features as FEAT
        if not FEAT.on("price"):                           # 2.131.0: Price checking is off - the key is the game's
            return False
        if not SETTINGS.get("pc_ctrl_c", True) or pc_key_is_copy():
            return False                                   # Ctrl+C: the game copies, the app only listens
        k = parse_key(SETTINGS.get("pc_key") or "")
        if not k or k != (vk, ctrl, alt, shift):
            return False
        if not game_active((getattr(self, "overlay", None) and self.overlay.cfg.get("poe_title")) or POE_TITLE):
            return False                                   # outside the game the key does its usual job
        def go():
            self.keys.pc_time = self.keys.sent_copy = time.time()
            send_copy()
        threading.Thread(target=go, daemon=True).start()
        return True

    def topup_hotkey(self, vk, ctrl, alt, shift):
        """2.131.1 (feedback: "using price check key on top up items causes the item's card to stay stuck on screen,
        we need a different key"): Top Up's own key (F7) in game -> the game's copy once; the copy only teaches Top
        Up (never priced, never Bulk Pricing)."""
        from .overlay import parse_key, game_active, send_copy, POE_TITLE
        from . import topup as TU
        k = parse_key(SETTINGS.get("topup_key") or "")
        if not k or k != (vk, ctrl, alt, shift) or not TU.cfg().get("on") or self.topup_key_is_copy():
            return False                                   # (Ctrl+C: the game copies by itself - nothing to send)
        if not game_active((getattr(self, "overlay", None) and self.overlay.cfg.get("poe_title")) or POE_TITLE):
            return False

        def go():
            self.keys.tu_time = self.keys.sent_copy = time.time()
            send_copy()
        threading.Thread(target=go, daemon=True).start()
        return True

    def open_utilities(self, key="notes"):
        """The ⚙ on the note: bring the app up with the Notes window in front."""
        try:
            self.root.deiconify()
            self.root.lift()
        except Exception:
            buglog.caught()
        self.shell.open(key)

    def stop_utilities(self):
        try:
            self.overlay.close()
        except Exception:
            buglog.caught()
        DELIRIUM.stop()                                  # only if the app started it
        try:
            from .utilities import RITUAL                # 2.14.0
            RITUAL.stop()
        except Exception:
            buglog.caught()

    # ---------------- shared bits

    def _card(self, body, title, expand=False):
        P2 = C["panel2"]
        f = tk.Frame(body, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
        f.pack(fill="both" if expand else "x", expand=expand, padx=8, pady=(0, 8))
        if title:
            tk.Label(f, text=title, bg=P2, fg=C["accent"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        return f

    # ---------------- the Chat commands window
    def build_chat_window(self, body):
        """Settings › Keybinds › Chat commands (2.116.0, P10: was its own tab). body: the section's frame. Only the rows
        in use show; + Add a command shows the next (no eight empty rows)."""
        P2 = C["panel2"]
        ov = self._ensure_overlay().cfg
        self.ov_vars = getattr(self, "ov_vars", None) or {}
        self.chat_on = tk.BooleanVar(value=bool(ov.get("chat_enabled")))
        top = tk.Frame(body, bg=P2)
        top.pack(fill="x")
        ttk.Checkbutton(top, text="Type chat commands into the game with a key", variable=self.chat_on,
                        command=self.chat_toggle).pack(side="left")
        self.chat_st = tk.Label(top, text="", bg=P2, fg=C["muted"], anchor="w", font=("Segoe UI", 9, "bold"))
        self.chat_st.pack(side="left", padx=12)
        if "poe_title" not in self.ov_vars:                   # (the game window title: Settings › General › Game)
            self.ov_vars["poe_title"] = tk.StringVar(value=ov.get("poe_title", "") or "Path of Exile 2")
        from .style import KeyCapture
        cg = tk.Frame(body, bg=P2)
        cg.pack(fill="x", pady=(8, 0))
        for col, t in enumerate(("Name", "Key", "Command (e.g. /leave  /dnd  /invite Name)")):
            tk.Label(cg, text=t, bg=P2, fg=C["muted"], font=("Segoe UI", 9, "bold"), anchor="w").grid(row=0, column=col,
                                                                                                   sticky="w")
        self.ov_vars["hideout_key"] = tk.StringVar(value=ov.get("hideout_key", ""))
        self.chat_keys_lbl = tk.Label(cg, text="Go to hideout", bg=P2, fg=C["text"], anchor="w")
        self.chat_keys_lbl.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=1)
        self.chat_hideout_kc = KeyCapture(cg, self.ov_vars["hideout_key"], width=12,
                                          on_change=lambda t: self.root.after(10, self.chat_key_set))
        self.chat_hideout_kc.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=1)
        tk.Label(cg, text="/hideout", bg=P2, fg=C["muted"], anchor="w", font=("Segoe UI", 9)).grid(row=1, column=2,
                                                                                                sticky="w")
        cmds = ov.get("commands", [])
        self.ov_cmd_vars, self.chat_key_boxes, self.chat_rows = [], [], []
        for i in range(MAX_COMMANDS):
            c = cmds[i] if i < len(cmds) else {}
            row, widgets = [], []
            for col, (k, w) in enumerate((("name", 14), ("key", 8), ("cmd", 34))):
                v = tk.StringVar(value=c.get(k, ""))
                if k == "key":
                    kc = KeyCapture(cg, v, width=12, on_change=lambda t: self.root.after(10, self.chat_key_set))
                    kc.grid(row=i + 2, column=col, sticky="w", padx=(0, 8), pady=1)
                    self.chat_key_boxes.append(kc)
                    widgets.append(kc)
                    row.append(v)
                    continue
                e = tk.Entry(cg, textvariable=v, width=w, bg=C["odd"], fg=C["text"], insertbackground=C["text"],
                             relief="flat", highlightthickness=1, highlightbackground=C["line"])
                e.grid(row=i + 2, column=col, sticky="w", padx=(0, 8), pady=1)
                widgets.append(e)
                v.trace_add("write", lambda *_a: self.ov_save_soon())       # 2.59.0: saves as you type
                row.append(v)
            self.ov_cmd_vars.append(row)
            self.chat_rows.append(widgets)
        brow = tk.Frame(body, bg=P2)
        brow.pack(fill="x", pady=(8, 0))
        self.chat_add_btn = ttk.Button(brow, text="+ Add a command", style="Quiet.TButton", command=self.chat_add_row)
        self.chat_add_btn.pack(side="left")
        self.ov_msg = tk.Label(brow, text="Changes save by themselves.", bg=P2, fg=C["muted"], anchor="w")
        self.ov_msg.pack(side="left", fill="x", expand=True, padx=8)
        self._chat_shown = max([i + 1 for i, r in enumerate(self.ov_cmd_vars) if any(v.get().strip() for v in r)] or [0])
        self._chat_rows_paint()
        self._chat_keys_text()
        self.root.after(50, self.chat_key_marks)

    def _chat_rows_paint(self):
        """Show the rows in use (and any added); hide the rest."""
        for i, widgets in enumerate(getattr(self, "chat_rows", [])):
            for w in widgets:
                (w.grid if i < self._chat_shown else w.grid_remove)()
        try:
            self.chat_add_btn.state(["disabled"] if self._chat_shown >= len(self.chat_rows) else ["!disabled"])
        except (AttributeError, tk.TclError):
            pass

    def chat_add_row(self):
        """+ Add a command: the next empty row shows, its name box focused."""
        self._chat_shown = min(len(self.chat_rows), self._chat_shown + 1)
        self._chat_rows_paint()
        try:
            self.chat_rows[self._chat_shown - 1][0].focus_set()
        except (IndexError, tk.TclError):
            pass

    def chat_key_set(self):
        """2.61.1: a chat key was set in a box here - save, keep Settings › Keybinds in step, warn about clashes."""
        self.ov_save()
        if hasattr(self, "hk_frame"):
            try:
                self.fill_hotkeys()
            except Exception:
                buglog.caught()
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
        name = {"Hotkeys": "Keybinds", "Chat commands": "Keybinds", "Keys": "Keybinds"}.get(name, name)  # 2.127.0: Keybinds
        self.shell.open("settings")
        try:
            self.set_nb.select(self.set_nb.titles.index(name))
        except (AttributeError, ValueError):
            pass

    # ---------------- chat commands & notes
    def chat_toggle(self):
        self.overlay.set_chat(self.chat_on.get())
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

    def notes_open(self):
        """2.114.0 (P9: opening Notes landed on Overlay › Overlay Settings with no word about the note): the note itself, over
        the game, and where it lives. Switched off: Overlay › Overlay Settings, saying which switch."""
        ov = getattr(self, "overlay", None)
        if ov is None or not ov.cfg.get("notes_enabled"):
            self.ovh_open("Settings")
            self._say("Notes is switched off: Overlay › Overlay Settings › On the overlay › Notes.", 10)
            return False
        ov.show_notes()
        self._say("Notes is on the overlay bar (Notes ▾) and shows while the game is in front. Double-click a tab to "
                  "rename it; right-click for more.", 10)
        return True

    def notes_status(self):
        cfg = self.overlay.cfg if getattr(self, "overlay", None) else {}
        return bool(cfg.get("notes_enabled"))

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
