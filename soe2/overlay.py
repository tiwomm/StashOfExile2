"""Chat commands & notes (2.0): the POE2 Overlay AutoHotkey script, rebuilt inside StashOfExile2.

  - A key that types /hideout into PoE2's chat (F1 by default), and up to 8 more keys for your own chat commands
    (/leave, /dnd, /invite Name ...). They only act while Path of Exile 2 is the active window; anywhere else the key
    does what it normally does. One key press = one chat command, like the "thanks for the trade" chat macro
    GGG staff have long allowed (and Sidekick's hideout key).
  - Sticky notes: a small always-on-top note window over the game (F6 shows / hides it). Drag it by its header,
    resize it from the corner, set its colors, opacity and font size. It saves itself, and hides while the game
    is closed.

Settings live in settings.json ("overlay"). On first use, your POE2 Overlay config (%APPDATA%/POE2Overlay/config.ini)
is read in, so notes, commands and colors carry over."""
import configparser
import os
import re
import sys
import threading
import time
import tkinter as tk

POE_TITLE = "Path of Exile 2"

DEFAULTS = {
    "chat_enabled": False, "notes_enabled": False, "hideout_key": "F1", "notes_key": "F6", "poe_title": POE_TITLE,
    "commands": [],                                  # [{"name", "key", "cmd"}], up to 8
    "notes_visible": True, "notes_locked": False, "notes_text": "Your notes here...", "notes_x": 50, "notes_y": 50, "notes_w": 300,
    "notes_h": 220, "notes_bg": "1A1A2E", "notes_fg": "E2C97E", "notes_opacity": 215, "notes_font": 11,
    "imported_ahk": False,
}
MAX_COMMANDS = 8
NOTE_MIN_W, NOTE_MIN_H = 140, 80

# ---------------------------------------------------------------- key names (AutoHotkey style)
VK = {**{f"f{i}": 0x6F + i for i in range(1, 25)},
      **{chr(c): c - 32 for c in range(ord("a"), ord("z") + 1)},
      **{str(d): 0x30 + d for d in range(10)},
      **{f"numpad{d}": 0x60 + d for d in range(10)},
      "enter": 0x0D, "space": 0x20, "tab": 0x09, "esc": 0x1B, "escape": 0x1B, "backspace": 0x08, "insert": 0x2D,
      "ins": 0x2D, "delete": 0x2E, "del": 0x2E, "home": 0x24, "end": 0x23, "pgup": 0x21, "pageup": 0x21,
      "pgdn": 0x22, "pagedown": 0x22, "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27, "`": 0xC0,
      "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD, ";": 0xBA, "'": 0xDE, ",": 0xBC, ".": 0xBE, "/": 0xBF, "\\": 0xDC,
      # mouse buttons (2.0 beta 17; AutoHotkey names, plus plain ones)
      "mbutton": 0x04, "xbutton1": 0x05, "xbutton2": 0x06, "middle": 0x04, "mouse4": 0x05, "mouse5": 0x06}
MOUSE_VKS = (0x04, 0x05, 0x06)
PRETTY = {0x04: "Middle mouse", 0x05: "Mouse 4", 0x06: "Mouse 5"}
MODS = {"^": "ctrl", "!": "alt", "+": "shift"}


def parse_key(text):
    """'F1' / '^h' (Ctrl+H) / '!h' (Alt+H) / '+F5' (Shift+F5) -> (vk, ctrl, alt, shift), or None if not understood."""
    t = (text or "").strip()
    mods = {"ctrl": False, "alt": False, "shift": False}
    while len(t) > 1 and t[0] in MODS:
        mods[MODS[t[0]]] = True
        t = t[1:]
    m = re.fullmatch(r"(?i)(ctrl|alt|shift)\s*\+\s*(.+)", t)        # also 'Ctrl+H'
    while m:
        mods[m.group(1).lower()] = True
        t = m.group(2)
        m = re.fullmatch(r"(?i)(ctrl|alt|shift)\s*\+\s*(.+)", t)
    vk = VK.get(t.lower())
    if vk is None:
        return None
    return vk, mods["ctrl"], mods["alt"], mods["shift"]


def key_label(text):
    k = parse_key(text)
    if not k:
        return text
    if k[0] in PRETTY:
        return "+".join([m for m, on in zip(("Ctrl", "Alt", "Shift"), k[1:]) if on] + [PRETTY[k[0]]])
    name = next((n for n, v in VK.items() if v == k[0]), "?")
    return "+".join([m for m, on in zip(("Ctrl", "Alt", "Shift"), k[1:]) if on] + [name.upper() if len(name) > 1 else name.upper()])


# ---------------------------------------------------------------- the game window
def game_active(title=POE_TITLE):
    """Is Path of Exile 2 the window you are typing into?"""
    if sys.platform != "win32":
        if sys.platform.startswith("linux"):         # 2.10.0: Hyprland only; False elsewhere
            from .linsys import game_active as _ga
            return _ga(title)
        return False
    import ctypes
    u = ctypes.windll.user32
    hwnd = u.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(hwnd, buf, 256)
    cls = ctypes.create_unicode_buffer(64)
    u.GetClassNameW(hwnd, cls, 64)
    return title.lower() in buf.value.lower() or cls.value == "POEWindowClass"


def game_open(title=POE_TITLE):
    """Is the game running (a visible Path of Exile 2 window)? Window titles only - nothing else is looked at."""
    if sys.platform != "win32":
        return True
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if not u.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(hwnd, buf, 256)
        cls = ctypes.create_unicode_buffer(64)
        u.GetClassNameW(hwnd, cls, 64)
        if buf.value.strip().lower() == title.lower() or cls.value == "POEWindowClass":
            found.append(hwnd)
            return False
        return True
    u.EnumWindows(cb, 0)
    return bool(found)


# ---------------------------------------------------------------- typing a chat command
def _send_keys(events):
    """events: [(vk or None, char or None, up)] -> one SendInput call per event (Windows)."""
    import ctypes
    from ctypes import wintypes
    ULONG_PTR = ctypes.c_size_t

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class _U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _U)]
    for vk, ch, up in events:
        ki = KEYBDINPUT(vk or 0, ord(ch) if ch else 0, (0x4 if ch else 0) | (0x2 if up else 0), 0, 0)   # 0x4 = UNICODE
        inp = INPUT(1, _U(ki=ki))
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_copy(sender=None):
    """One-key copy (2.0 beta 15): press the game's own Ctrl+Alt+C once for you - one key press, one item copied (the
    same thing Sidekick's price-check key does). Nothing is clicked, moved or sent to the game's servers."""
    send = sender or _send_keys
    send([(0x10, None, True),                                                       # Shift up (it changes the copy)
          (0x11, None, False), (0x12, None, False), (0x43, None, False), (0x43, None, True),
          (0x12, None, True), (0x11, None, True)])


CLIP_HOOK = [None]          # the app sets this: fn(text) -> "ignore this clipboard text for a moment"


def type_chat(cmd, sender=None, sleep=time.sleep, clip=None):
    """Send a chat command the way Sidekick does (2.0 beta 8): put it on the clipboard, then in one quick burst press
    Enter (open chat), Ctrl+A + Backspace (clear it), Ctrl+V (paste), Enter (send). Nothing is typed letter by letter,
    so the chat box only flashes for a moment. Your clipboard is put back afterwards.
    Modifier keys you are still holding are released first, so Ctrl+H doesn't turn into shortcuts."""
    send = sender or _send_keys
    if clip is None:
        from .clipboard import read_clipboard_text, write_clipboard_text
        clip = (read_clipboard_text, write_clipboard_text)
    read, write = clip
    old = read()
    hook = CLIP_HOOK[0]
    if hook:
        hook(cmd)
        if old:
            hook(old)
    pasted = write(cmd)
    keys = [(0x11, None, True), (0x12, None, True), (0x10, None, True),             # let go of Ctrl / Alt / Shift
            (0x0D, None, False), (0x0D, None, True),                                # Enter: open chat
            (0x11, None, False), (0x41, None, False), (0x41, None, True), (0x11, None, True),   # Ctrl+A
            (0x08, None, False), (0x08, None, True)]                                # Backspace
    if pasted:
        keys += [(0x11, None, False), (0x56, None, False), (0x56, None, True), (0x11, None, True)]   # Ctrl+V
    else:                                                                           # no clipboard: type it instead
        keys += [e for ch in cmd for e in ((None, ch, False), (None, ch, True))]
    keys += [(0x0D, None, False), (0x0D, None, True)]                               # Enter: send
    send(keys)
    if pasted and old:
        sleep(0.15)                                    # let the game read the clipboard before putting yours back
        write(old)


# ---------------------------------------------------------------- the old AutoHotkey settings
def ahk_config_path():
    return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "POE2Overlay", "config.ini")


def read_ahk_config(path=None):
    """POE2 Overlay's config.ini -> overlay settings (only what it holds). AutoHotkey writes it as UTF-16."""
    path = path or ahk_config_path()
    if not os.path.isfile(path):
        return {}
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    for enc in ("utf-16", "utf-8-sig", "mbcs", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                cp.read_string(f.read())
            break
        except Exception:
            continue
    else:
        return {}

    def get(sec, key, default=None):
        try:
            return cp.get(sec, key)
        except Exception:
            return default
    out = {}
    for sec, key, name, conv in (("Hotkeys", "Hideout", "hideout_key", str), ("Hotkeys", "Notes", "notes_key", str),
                                 ("General", "PoeTitle", "poe_title", str), ("Notes", "X", "notes_x", int),
                                 ("Notes", "Y", "notes_y", int), ("Notes", "W", "notes_w", int), ("Notes", "H", "notes_h", int),
                                 ("Notes", "BgColor", "notes_bg", str), ("Notes", "FgColor", "notes_fg", str),
                                 ("Notes", "Opacity", "notes_opacity", int), ("Notes", "FontSize", "notes_font", int),
                                 ("Notes", "Content", "notes_text", str), ("Notes", "Visible", "notes_visible", lambda v: v == "1")):
        v = get(sec, key)
        if v is not None:
            try:
                out[name] = conv(v)
            except Exception:
                pass
    if "notes_text" in out:
        out["notes_text"] = out["notes_text"].replace("`n", "\n")        # AutoHotkey writes new lines as `n
    cmds = []
    try:
        n = int(get("Commands", "Count", "0") or 0)
    except ValueError:
        n = 0
    for i in range(1, n + 1):
        k, c = get("Commands", f"Key{i}", ""), get("Commands", f"Cmd{i}", "")
        if k and c:
            cmds.append({"name": get("Commands", f"Name{i}", "") or "", "key": k, "cmd": c})
    if cmds:
        out["commands"] = cmds[:MAX_COMMANDS]
    return out


# ---------------------------------------------------------------- the overlay itself
class Overlay:
    """Lives in the app's window thread. Key presses arrive from the app's keyboard watcher (another thread)
    through on_key(), which only decides and queues; everything else runs on the window thread."""

    def __init__(self, root, settings, save, open_settings=None):
        self.root, self.S, self.save_settings, self.open_settings = root, settings, save, open_settings
        self.cfg = self.S.setdefault("overlay", {})
        for k, v in DEFAULTS.items():
            self.cfg.setdefault(k, v if not isinstance(v, list) else list(v))
        if "enabled" in self.cfg:              # 2.0 beta 7: one switch became two (chat commands / notes)
            on = bool(self.cfg.pop("enabled"))
            self.cfg["chat_enabled"] = self.cfg["notes_enabled"] = on
        if not self.cfg.get("imported_ahk"):
            old = read_ahk_config()
            if old:
                self.cfg.update(old)
                self.imported = True
            self.cfg["imported_ahk"] = True
            self.save_settings()
        self.notes = None
        self._save_job = None
        self._game_was_open = None
        self.pending = []                      # chat commands waiting for the window thread
        self.lock_listener = None              # told when the note is locked / unlocked from its title bar
        self.bindings = {}
        self.rebind()
        self.root.after(500, self._tick)

    # ---- keys
    def rebind(self):
        """(vk, ctrl, alt, shift) -> what to do."""
        b = {}
        if self.cfg.get("notes_enabled"):
            k = parse_key(self.cfg.get("notes_key"))
            if k:
                b[k] = ("notes",)
        if self.cfg.get("chat_enabled"):
            k = parse_key(self.cfg.get("hideout_key"))
            if k:
                b[k] = ("chat", "/hideout")
            for c in self.cfg.get("commands", [])[:MAX_COMMANDS]:
                k = parse_key(c.get("key"))
                if k and c.get("cmd"):
                    b[k] = ("chat", c["cmd"])
        self.bindings = b

    def on_key(self, vk, ctrl, alt, shift):
        """Called by the keyboard watcher for every key you press. -> True to swallow the key (it did something)."""
        action = self.bindings.get((vk, ctrl, alt, shift))
        if not action:
            return False
        if action[0] == "chat":
            if not game_active(self.cfg.get("poe_title") or POE_TITLE):
                return False                   # not in the game: the key does what it normally does
            threading.Thread(target=type_chat, args=(action[1],), daemon=True).start()
            return True
        self.pending.append(action)
        return True

    # ---- notes window
    def show_notes(self):
        c = self.cfg
        if self.notes is None or not self.notes.winfo_exists():
            self._build_notes()
        self.notes.show()                      # 2.0 beta 15: only while the game (or the app) is in front
        c["notes_visible"] = True
        self.save_settings()

    def hide_notes(self, remember=True):
        if self.notes is not None and self.notes.winfo_exists():
            self._store_geometry()
            self.notes.hide()
        if remember:
            self.cfg["notes_visible"] = False
            self.save_settings()

    def toggle_notes(self):
        if self.notes_shown():
            self.hide_notes()
        else:
            self.show_notes()

    def notes_shown(self):
        """Switched on (it may still be out of sight while the game isn't in front)."""
        return self.notes is not None and self.notes.winfo_exists() and getattr(self.notes, "wanted", True)

    def note_colours(self):
        """(background, text): the remnant book's parchment (2.43.0), or your own colors with the Classic look."""
        from .overlaywin import pal, skinned
        if skinned():                                     # 2.47.0: every PoE2 look: its own page colours
            return pal()["field"], pal()["text"]
        return self._colour("notes_bg", "1A1A2E"), self._colour("notes_fg", "E2C97E")

    def _colour(self, key, default):
        v = str(self.cfg.get(key) or default).lstrip("#")
        return "#" + v if re.fullmatch(r"[0-9A-Fa-f]{6}", v) else "#" + default

    def _build_notes(self):
        """The sticky note: the shared over-the-game window (overlaywin.py) with your colors inside it."""
        from .overlaywin import OverlayWindow, pal, skinned
        c = self.cfg
        bg, fg = self.note_colours()

        def moved(x, y, ww, hh):
            c.update(notes_x=x, notes_y=y, notes_w=ww, notes_h=hh)
            self.save_settings()
        w = OverlayWindow(self.root, "Notes", "📌",
                          (c["notes_x"], c["notes_y"], c["notes_w"], c["notes_h"]),
                          opacity=int(c.get("notes_opacity", 215)), locked=bool(c.get("notes_locked")), body_bg=bg,
                          min_size=(NOTE_MIN_W, NOTE_MIN_H), on_close=self.hide_notes, on_lock=self.set_locked,
                          on_moved=moved, follow_game=True)
        w.withdraw()                           # show_notes() shows it
        host = w.body
        if w.parch:                            # 2.47.0: a page on the skin's background (the parchment shows round it)
            cv = w.canvas_body()
            host = tk.Frame(cv, bg=bg)
            win_id = cv.create_window(8, 4, window=host, anchor="nw")
            cv.bind("<Configure>", lambda e: cv.itemconfigure(win_id, width=max(40, e.width - 16),
                                                              height=max(30, e.height - 12)), add="+")
            if not c.get("notes_locked"):
                w.draggable(cv)
        # 2.23.0: tabs - several pages on one note (click a tab, + adds one, double-click renames, right-click deletes)
        self.notes_tabbar = tk.Frame(host, bg=bg)
        self.notes_tabbar.pack(fill="x")
        text = tk.Text(host, bg=bg, fg=fg, insertbackground=fg, relief="flat", highlightthickness=0, wrap="word",
                       font=(pal()["font"] if skinned() else "Consolas", int(c.get("notes_font", 11))), padx=8, pady=4,
                       spacing1=2, spacing3=2)
        text.pack(fill="both", expand=True)
        tabs, i = self.note_tabs(), self.note_index()
        text.insert("1.0", tabs[i]["text"])
        text.edit_modified(False)
        text.bind("<<Modified>>", self._text_changed)
        self.notes, self.notes_text = w, text
        self._paint_tabs()

    # ---- 2.23.0: note tabs
    def note_tabs(self):
        """[{"name", "text"}] - made from the single note of older versions the first time."""
        c = self.cfg
        tabs = c.get("notes_tabs")
        if not isinstance(tabs, list) or not tabs:
            tabs = c["notes_tabs"] = [{"name": "Note 1", "text": c.get("notes_text", "")}]
        return tabs

    def note_index(self):
        i = self.cfg.get("notes_tab", 0)
        return i if isinstance(i, int) and 0 <= i < len(self.note_tabs()) else 0

    def _keep_text(self):
        """What's typed on the note -> its tab (and notes_text, which older versions read)."""
        try:
            t = self.notes_text.get("1.0", "end-1c")
        except Exception:
            return
        self.note_tabs()[self.note_index()]["text"] = t
        self.cfg["notes_text"] = t

    def _paint_tabs(self):
        bar = getattr(self, "notes_tabbar", None)
        if bar is None or not bar.winfo_exists():
            return
        for w_ in bar.winfo_children():
            w_.destroy()
        bg, fg = self.note_colours()
        cur = self.note_index()
        for i, t in enumerate(self.note_tabs()):
            on = i == cur
            lab = tk.Label(bar, text=t["name"][:18], bg=fg if on else bg, fg=bg if on else fg, padx=8, pady=1,
                           cursor="hand2", font=("Segoe UI", 9, "bold" if on else "normal"),
                           highlightthickness=1, highlightbackground=fg)
            lab.pack(side="left", padx=(0, 2), pady=(0, 2))
            lab.bind("<Button-1>", lambda e, i=i: self.switch_tab(i))
            lab.bind("<Double-1>", lambda e, i=i: self.rename_tab(i))
            lab.bind("<Button-3>", lambda e, i=i: self.delete_tab(i))
        add = tk.Label(bar, text="+", bg=bg, fg=fg, padx=8, cursor="hand2", font=("Segoe UI", 9, "bold"))
        add.pack(side="left", pady=(0, 2))
        add.bind("<Button-1>", lambda e: self.add_tab())

    def switch_tab(self, i):
        if not 0 <= i < len(self.note_tabs()):
            return
        self._keep_text()
        self.cfg["notes_tab"] = i
        self.notes_text.delete("1.0", "end")
        self.notes_text.insert("1.0", self.note_tabs()[i]["text"])
        self.notes_text.edit_modified(False)
        self.cfg["notes_text"] = self.note_tabs()[i]["text"]
        self.save_settings()
        self._paint_tabs()

    def add_tab(self, name=None):
        tabs = self.note_tabs()
        if len(tabs) >= 12:
            return None
        n = len(tabs) + 1
        while any(t["name"] == f"Note {n}" for t in tabs):
            n += 1
        tabs.append({"name": name or f"Note {n}", "text": ""})
        self.switch_tab(len(tabs) - 1)
        return len(tabs) - 1

    def rename_tab(self, i, name=None):
        if name is None:
            from tkinter import simpledialog
            name = simpledialog.askstring("Rename note", "Name:", initialvalue=self.note_tabs()[i]["name"],
                                          parent=self.notes)
        if name and name.strip():
            self.note_tabs()[i]["name"] = name.strip()[:30]
            self.save_settings()
            self._paint_tabs()

    def delete_tab(self, i, ask=True):
        tabs = self.note_tabs()
        if len(tabs) <= 1 or not 0 <= i < len(tabs):
            return False
        self._keep_text()
        if ask and tabs[i]["text"].strip():
            from tkinter import messagebox
            if not messagebox.askyesno("Delete note", f"Delete \"{tabs[i]['name']}\" and what's on it?", parent=self.notes):
                return False
        del tabs[i]
        cur = self.note_index()
        self.cfg["notes_tab"] = min(cur if cur < i else max(0, cur - 1), len(tabs) - 1)
        self.notes_text.delete("1.0", "end")
        self.notes_text.insert("1.0", tabs[self.note_index()]["text"])
        self.notes_text.edit_modified(False)
        self.save_settings()
        self._paint_tabs()
        return True

    def set_locked(self, on):
        """The lock on the note's title bar (or the Notes window): no moving or resizing while locked."""
        self.cfg["notes_locked"] = bool(on)
        self.save_settings()
        self.restyle()
        if self.lock_listener:
            self.lock_listener(bool(on))

    def _text_changed(self, _e=None):
        try:
            self.notes_text.edit_modified(False)
        except Exception:
            return
        if self._save_job:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(2000, self._autosave)       # like the original: 2 s after you stop typing

    def _autosave(self):
        self._save_job = None
        self._keep_text()
        self.save_settings()

    def _store_geometry(self):
        try:
            w = self.notes
            if w.winfo_width() > 1 and w.winfo_ismapped():         # a note that isn't laid out yet reports 1x1 at 0,0
                self.cfg.update(notes_x=w.winfo_x(), notes_y=w.winfo_y(), notes_w=w.winfo_width(), notes_h=w.winfo_height())
            self._keep_text()
        except Exception:
            pass

    def restyle(self, store=True):
        """Colors / opacity / font / size changed in the Notes window: rebuild the note (where it is, unless the new
        place and size are already in the settings: store=False)."""
        vis = self.notes_shown()
        if self.notes is not None and self.notes.winfo_exists():
            if store:
                self._store_geometry()
            self.notes.destroy()
        self.notes = None
        if vis:
            self.show_notes()

    # ---- every half second on the window thread
    def _tick(self):
        try:
            from . import overlaywin
            overlaywin.GAME_TITLE[0] = self.cfg.get("poe_title") or POE_TITLE
            overlaywin.GAME_ONLY[0] = bool(self.S.get("overlay_game_only", True))
            while self.pending:
                action = self.pending.pop(0)
                if action[0] == "notes":
                    self.toggle_notes()
            if self.cfg.get("notes_enabled"):
                now_open = game_open(self.cfg.get("poe_title") or POE_TITLE) if int(time.time()) % 5 == 0 or \
                    self._game_was_open is None else self._game_was_open
                if now_open != self._game_was_open:
                    if now_open and self.cfg.get("notes_visible"):
                        self.show_notes()
                    elif not now_open:
                        self.hide_notes(remember=False)              # back when the game is
                    self._game_was_open = now_open
        except Exception:
            pass
        self.root.after(500, self._tick)

    def set_chat(self, on):
        self.cfg["chat_enabled"] = bool(on)
        self.rebind()
        self.save_settings()

    def set_notes(self, on):
        self.cfg["notes_enabled"] = bool(on)
        self.rebind()
        self._game_was_open = None
        if not on:
            self.hide_notes(remember=False)
        elif self.cfg.get("notes_visible"):
            self.show_notes()
        self.save_settings()

    def set_enabled(self, on):
        """Both at once (kept for older callers)."""
        self.set_chat(on)
        self.set_notes(on)

    def close(self):
        if self.notes is not None:
            try:
                self._store_geometry()
            except Exception:
                pass
        self.save_settings()
