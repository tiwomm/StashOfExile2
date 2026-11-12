"""2.131.0 Top Up Reminders - the watcher, teaching an item, the reminder card and the Items list (topup.py reads the
pictures). Overlay ↳ Overlay Settings › Helpers has its switch. Off until you turn it on; looks only while the game is in front."""
import time
import tkinter as tk
from tkinter import ttk

from . import buglog
from . import topup as TU
from .config import SETTINGS, save_json
from .style import C, Tooltip

EVERY_MS = 1500                     # how often it looks for the inventory
MOVING = "moving"
HIST_SECS = 20                      # 2.131.2: recent looks kept to find the taught cell without the hover glow
REFINE_SAME = TU.SAME * 3       # (the glow changes it this much at most)
TEACH_SECS = 3                      # the Top Up key counts as teaching within this of the last look
CARD_COLOR = "#8ec5ff"
PC_CARD_SECS = 8                    # 2.131.5: a price check's card may cover the inventory this long


class TopUpPage:
    """Mixed into App."""

    # ---------------------------------------------------------------- on / off
    def topup_on(self):
        from . import features as FEAT
        return bool(TU.cfg().get("on")) and FEAT.on("overlay") and FEAT.on("topup")      # (2.132.2: BETA)

    def topup_set(self, on):
        TU.cfg()["on"] = bool(on)
        from . import features as FEAT
        FEAT.beta_on("topup", bool(on))
        save_json("settings.json", SETTINGS)
        if on:
            self.topup_start()
            if getattr(self, "br_reader", None) is None:        # (the log says when you're in a hideout / town)
                try:
                    self.breach_start()
                except Exception:
                    buglog.caught()

    def topup_looking(self):
        """2.132.0: the inventory looks run for Top Up Reminders or Map profit."""
        try:
            return self.topup_on() or self.mp_on()
        except Exception:
            return self.topup_on()

    def topup_start(self):
        if getattr(self, "_tu_ticking", False) or not self.topup_looking():
            return
        self._tu_ticking = True
        self.root.after(EVERY_MS, self.topup_tick)

    # ---------------------------------------------------------------- looking
    def topup_tick(self):
        if not self.topup_looking():
            self._tu_ticking = False
            return
        try:
            self.topup_look()
        except Exception:
            self.log_error("Top Up Reminders")
        self.root.after(EVERY_MS, self.topup_tick)

    def topup_look(self, force=False):
        """One look (on a background thread): is the inventory open, and if so what's in it."""
        if getattr(self, "_tu_busy", False):
            return None
        from .alerts_page import game_rect
        g = game_rect()
        if not force:
            try:
                from .overlaywin import foreground_ok
                if not foreground_ok():
                    return None
            except Exception:
                buglog.caught()
        if not g:
            return None
        self._tu_busy = True
        prev = getattr(self, "tu_last", None)
        try:
            p0 = self.root.winfo_pointerxy()               # (2.131.2: where the mouse was as the look began)
        except tk.TclError:
            p0 = None

        def work():
            from .remnant import grab
            gx, gy, gw, gh = g
            game = (gx, gy, gw, gh)
            if not TU.is_open(grab(TU.banner_rect(game)), gh):
                return {"open": False}
            rect = TU.grid_rect(game)
            img = grab(rect)
            if prev and prev.get("open") and prev.get("thumb") == _thumb(img):
                cells = prev["cells"]                      # (nothing moved: no need to read it again)
            else:
                cells = TU.scan(img)
            return {"open": True, "cells": cells, "img": img, "rect": rect, "game": game, "thumb": _thumb(img)}

        def done(res):
            self._tu_busy = False
            if res is not None:
                res["p0"] = p0
            self.topup_seen(res)

        try:
            self.run_bg(work, done)
        except Exception:
            self._tu_busy = False
            raise
        return True

    def topup_seen(self, res):
        if res is None:
            return
        was = bool((getattr(self, "tu_last", None) or {}).get("open"))
        res["t"] = time.time()
        self.tu_last = res
        if res.get("open"):
            res["hover"] = self._tu_hover(res)
            hist = [h for h in getattr(self, "tu_hist", []) if res["t"] - h["t"] <= HIST_SECS]
            self.tu_hist = (hist + [res])[-8:]
            try:
                self.topup_refine(res)
            except Exception:
                buglog.caught()
            # 2.131.5 (feedback: "if the game's text box blocks the currency item, it drops down to seen 0"): a look
            # with the mouse over the inventory (the game's item box may cover cells) or one of the app's own
            # windows over it (a price card) doesn't count - Seen keeps the last clear look, and the reminder
            # waits for one
            res["covered"] = self._tu_covered(res) or self._tu_hidden(res)
            if not was:
                self.tu_open_reminded = False
            if not res["covered"]:
                self.tu_good = res
            else:
                good = getattr(self, "tu_good", None)
                if good is not None and good.get("cells") is not None:
                    res["cells_use"] = good["cells"]
            self.topup_paint_seen()
            try:
                self.mp_seen(res)                            # 2.132.0: Map profit reads the same look (2.132.2: a
            except Exception:                                # covered one too - see mp_seen)
                self.log_error("Map profit")
            if not res["covered"] and not getattr(self, "tu_open_reminded", False) and self.topup_on():
                self.tu_open_reminded = True
                self.topup_remind()

    def _tu_hover(self, res):
        """The inventory cell under the mouse in this look, None (off the grid), or MOVING when the mouse moved
        while it looked (its picture may hold a glow anywhere - not used to learn from)."""
        try:
            p1 = self.root.winfo_pointerxy()
        except tk.TclError:
            return MOVING
        p0 = res.get("p0", p1)
        if p0 is None or abs(p0[0] - p1[0]) > 2 or abs(p0[1] - p1[1]) > 2:
            return MOVING
        l_, t, r, _b = res["rect"]
        cs = (r - l_) / TU.COLS
        rc = (int((p1[1] - t) // cs), int((p1[0] - l_) // cs))
        return rc if 0 <= rc[0] < TU.ROWS and 0 <= rc[1] < TU.COLS else None

    def _tu_covered(self, res):
        """2.131.5: True when this look may not show the inventory as it is - the mouse over the inventory panel
        (the game's item box shows by it), or a price check just made (its card may be over the grid)."""
        l_, t, r, b = res["rect"]
        cs = (r - l_) / TU.COLS
        gy = (res.get("game") or (0, t, 0, 0))[1]
        try:
            px, py = self.root.winfo_pointerxy()
        except tk.TclError:
            return True
        if l_ - cs <= px <= r + cs and gy <= py <= b + cs:
            return True
        keys = getattr(self, "keys", None)                   # the price check key (Ctrl+D): its card shows over
        try:                                                 # the game for a while
            if keys is not None and keys.pc_recent(PC_CARD_SECS):
                return True
        except Exception:
            buglog.caught()
        return False

    def _tu_hidden(self, res):
        """2.132.2 (feedback: "chat window blocks currency for the top up and prompts me to restock everything"):
        an item you had is gone, but the cells it was in still hold something this look can't name - something is
        over them (the chat box, another window). Not a clear look."""
        good = getattr(self, "tu_good", None)
        if not good or not good.get("cells") or not res.get("cells"):
            return False
        refs = TU.learned()
        if not refs:
            return False
        was = {}
        for c in good["cells"]:
            name = TU.which(c["sig"], refs)
            if name is not None:
                was.setdefault(name, []).append(c["cell"])
        now = {c["cell"]: c for c in res["cells"]}
        have = {TU.which(c["sig"], refs) for c in res["cells"]}
        for name, cells in was.items():
            if name in have:
                continue
            if any(rc in now and TU.which(now[rc]["sig"], refs) is None for rc in cells):
                return True
        return False

    def _tu_plain(self, rc, s0, looks):
        """A picture of cell rc without the hover glow, from these looks (the mouse elsewhere, the same item there),
        newest first; or None."""
        for look in reversed(looks):
            if not look.get("open") or look.get("hover") in (rc, MOVING) or look.get("img") is None:
                continue
            cell = TU.split(look["img"]).get(rc)
            if cell is not None and not TU.empty(cell) and TU.dist(TU.sig(cell), s0) <= REFINE_SAME:
                return cell
        return None

    def topup_refine(self, res):
        """2.131.1 (feedback: "it didn't detect the quantities in my inventory" - 0 of an item you hold): teaching
        happens with the mouse on the item, so the picture it learned had the game's hover glow. 2.131.2 (feedback:
        still 0): a look from just before (the mouse elsewhere) is used at once; else the next look with the mouse
        off it, however much later - it's remembered in topup.json, closing the inventory or the app included."""
        pend = TU.pending()
        if not pend:
            return False
        done = False
        for name, (rc, s0) in pend.items():
            if res.get("hover") in (rc, MOVING):
                continue                                   # (still on it, or moving: the glow may be there)
            cell = TU.split(res["img"]).get(rc)
            TU.pending_set(name)
            if cell is None or TU.empty(cell) or TU.dist(TU.sig(cell), s0) > REFINE_SAME:
                continue                                   # (moved or gone: keep what it learned)
            done = TU.learn(name, cell) or done
        if done:
            buglog.debug("Top Up", "learned again without the hover glow")
        return done

    def topup_totals(self):
        last = getattr(self, "tu_last", None) or {}
        if not last.get("open"):
            return {}
        return TU.totals(last.get("cells_use") or last.get("cells") or [], TU.learned())

    # ---------------------------------------------------------------- the reminder
    def topup_visit(self):
        """Back from a map in a hideout or town (alerts_page.breach_area; 2.131.5: not any new area): the next
        inventory look may remind again."""
        self.tu_visit = getattr(self, "tu_visit", 0) + 1

    def topup_remind(self, force=False):
        """The inventory just opened: in your hideout or a town, once a visit, a card if something's under its
        keep. force (Test): now, wherever you are (a sample if nothing is low)."""
        items = TU.cfg()["items"]
        lows = TU.low(self.topup_totals(), items)
        if not force:
            if not lows or getattr(self, "br_area", None) not in ("hideout", "town"):
                return None
            if getattr(self, "tu_reminded", None) == getattr(self, "tu_visit", 0):
                return None
            self.tu_reminded = getattr(self, "tu_visit", 0)
        sub = TU.card_text(lows) if lows else ("Nothing is low" if items else "A sample - teach items first")
        from . import alertcard
        from .alerts_page import game_rect
        self.tu_win = alertcard.show(self.root, "Top up before your next map", sub, color=CARD_COLOR, mark="▼",
                                     secs=10, game=game_rect(), tag="Top Up", rank=3)
        buglog.debug("Top Up", f"reminded: {len(lows)} low")
        return lows

    # ---------------------------------------------------------------- teaching (the Top Up key, Ctrl+C)
    def topup_copy_learn(self, text):
        """The Top Up key (2.131.4: the game's Ctrl+C by default) on an item while your inventory was just seen: learn its picture under
        the mouse, add it to your list (keep = a full stack). -> True if learned."""
        last = getattr(self, "tu_last", None) or {}
        if not TU.cfg().get("on") or not last.get("open") or time.time() - last.get("t", 0) > TEACH_SECS:
            return False
        got = TU.item_name(text)
        if not got:
            return False
        name, count = got
        try:
            mx, my = self.root.winfo_pointerxy()
        except tk.TclError:
            return False
        l_, t, r, b = last["rect"]
        cs = (r - l_) / TU.COLS
        c, row = int((mx - l_) // cs), int((my - t) // cs)
        if not (0 <= row < TU.ROWS and 0 <= c < TU.COLS):
            return False
        cell = TU.split(last["img"])[(row, c)]
        if not TU.learn(name, cell):
            return False
        s0 = TU.sig(cell)
        plain = self._tu_plain((row, c), s0, [h for h in getattr(self, "tu_hist", [])
                                              if time.time() - h.get("t", 0) <= HIST_SECS])
        if plain is not None:
            TU.learn(name, plain)                          # (2.131.2: from a look just before - no glow)
        else:
            TU.pending_set(name, (row, c), s0)             # (the next look with the mouse off it - topup_refine)
        if count:
            try:
                TU.learn_digits(cell, count)
            except Exception:
                buglog.caught()
        items = TU.cfg()["items"]
        if not any(it.get("name") == name for it in items):
            items.append({"name": name, "keep": TU.full_stack(text) or 1})
        save_json("settings.json", SETTINGS)
        self.tu_last = dict(last, thumb=None)          # (read it again with this item known)
        self.status_text, self.status_until = (f"Top Up: learned {name} - set how many to keep in Items…" +
                                               ("" if plain is not None else " (move the mouse off it for a moment)")), \
            time.time() + 8
        self.topup_paint_list()
        return True

    def topup_take_supplies(self):
        """2.131.2 (request: move League Plan's map supplies into Top Up): the supplies you listed there join your
        Top Up items (Keep 0 until you set it; teach each once with the Top Up key). Once; League Plan's list goes.
        -> the names added."""
        try:
            from . import focus as F
            names = F.supplies_out()
        except Exception:
            buglog.caught()
            return []
        items = TU.cfg()["items"]
        have = {str(it.get("name") or "").lower() for it in items}
        added = []
        for n in names:
            if n.lower() not in have:
                items.append({"name": n, "keep": 0})
                have.add(n.lower())
                added.append(n)
        if names:
            save_json("settings.json", SETTINGS)
            self.status_text, self.status_until = (f"League Plan's map supplies are in Top Up Reminders now "
                                                   f"({len(names)}) - Overlay › Overlay Settings › Helpers › Items…"), \
                time.time() + 12
            self.topup_paint_list()
        return added

    def topup_wants(self, text):
        """2.131.4 (feedback: F7 did nothing - its copy was turned away as "not your Ctrl+Alt+C"): a copy for Top Up -
        Top Up on, an item, and your Top Up key just pressed (Ctrl+C, the game's own copy, by default)."""
        if not TU.cfg().get("on") or not str(text).lstrip().startswith("Item Class:"):
            return False
        keys = getattr(self, "keys", None)
        if keys is None:
            return False
        if self.topup_key_is_copy():
            return bool(keys.copy_recent() and not keys.combo_recent() and not keys.pc_recent())
        return bool(getattr(keys, "tu_recent", None) and keys.tu_recent())

    def topup_key_is_copy(self):
        k = str(SETTINGS.get("topup_key") or "").replace(" ", "").lower()
        return k in ("ctrl+c", "")

    def topup_take(self, text):
        """The copy teaches Top Up -> True (taken). Ctrl+C on anything else (not over your open inventory) -> False:
        the copy goes on as usual. Your own key and nothing learned: says why, and it's taken."""
        try:
            if self.topup_copy_learn(text):
                return True
        except Exception:
            buglog.caught()
            return False
        if self.topup_key_is_copy():
            return False
        self.status_text, self.status_until = ("Top Up: open your inventory and hover the item, then press the key "
                                               "again"), time.time() + 6
        return True

    def topup_key_text(self):
        from .overlay import key_label
        k = SETTINGS.get("topup_key") or "Ctrl+C"
        return key_label(k)

    # ---------------------------------------------------------------- Overlay ↳ Overlay Settings › Helpers: its row
    def topup_row(self, box, bg, CB):
        sm = ("Segoe UI", 9)
        row = tk.Frame(box, bg=bg)
        row.pack(fill="x", pady=(8, 0))
        self.al_topup = tk.BooleanVar(value=bool(TU.cfg()["on"]))
        cb = ttk.Checkbutton(row, text="Top Up Reminders (BETA)", variable=self.al_topup, style=CB,
                             command=lambda: self.topup_set(bool(self.al_topup.get())))
        cb.pack(side="left")
        ib = ttk.Button(row, text="Items…", command=self.topup_items)
        ib.pack(side="left", padx=(8, 0))
        tb = ttk.Button(row, text="Test", width=6, command=lambda: self.topup_remind(force=True))
        tb.pack(side="left", padx=(8, 0))
        info = tk.Label(row, text="ⓘ", bg=bg, fg=C["muted"], font=sm, cursor="question_arrow")
        info.pack(side="left", padx=(8, 0))
        tk.Label(box, text="Says what's running low when you open your inventory in your hideout or a town.", bg=bg,
                 fg=C["muted"], font=sm, anchor="w").pack(fill="x")
        Tooltip(cb, "Looks only while your inventory is open and the game is in front. Off until you turn it on.")
        Tooltip(ib, "Your items and how many of each to keep.")
        Tooltip(tb, "Shows the reminder now, with what it last saw.")
        Tooltip(info, f"Hover an item in your inventory and press {self.topup_key_text()} to track it.")

    # ---------------------------------------------------------------- the Items list
    def topup_add_open(self):
        """+ Add more: a row to add an item by its name (the game's name; it counts once you teach it)."""
        box = getattr(self, "tu_add", None)
        if box is None:
            return None
        for ch in box.winfo_children():
            ch.destroy()
        P2 = C["panel2"]
        tk.Label(box, text="Item", bg=P2, fg=C["text"]).pack(side="left")
        have = {it["name"] for it in TU.cfg()["items"]}
        self.tu_add_var = tk.StringVar()
        cb = ttk.Combobox(box, textvariable=self.tu_add_var, width=26,
                          values=[n for n in TU.SUGGEST if n not in have])
        cb.pack(side="left", padx=8)
        cb.focus_set()
        tk.Label(box, text="Keep", bg=P2, fg=C["text"]).pack(side="left")
        self.tu_add_keep = tk.StringVar(value="10")
        ttk.Spinbox(box, from_=0, to=9999, textvariable=self.tu_add_keep, width=5).pack(side="left", padx=(8, 8))
        ok = ttk.Button(box, text="Add", state="disabled", command=lambda: self.topup_add(self.tu_add_var.get(),
                                                                                       self.tu_add_keep.get()))
        ok.pack(side="left")
        self.tu_add_var.trace_add("write", lambda *_a: ok.config(state="normal" if self.tu_add_var.get().strip()
                                                                 else "disabled"))
        cb.bind("<Return>", lambda _e: self.topup_add(self.tu_add_var.get(), self.tu_add_keep.get()))
        return box

    def topup_add(self, name, keep):
        """Add one item by name -> True (already there: its Keep changes). Seen says "teach it" until taught."""
        name = str(name or "").strip()
        if not name:
            return False
        try:
            k = max(0, int(str(keep).strip() or 0))
        except ValueError:
            k = 0
        items = TU.cfg()["items"]
        old = next((it for it in items if it["name"].lower() == name.lower()), None)
        if old is not None:
            old["keep"] = k
        else:
            items.append({"name": name, "keep": k})
        save_json("settings.json", SETTINGS)
        try:
            self.tu_add_var.set("")
        except (AttributeError, tk.TclError):
            pass
        self.topup_paint_list()
        self.topup_below_paint()
        return True

    def topup_below_set(self, text):
        for b in TU.BELOW_STEPS:
            if TU.below_text(b) == text:
                TU.cfg()["below"] = b
                save_json("settings.json", SETTINGS)
        self.topup_below_paint()
        self.topup_paint_list()

    def topup_below_paint(self):
        """The line beside Remind when: how the number is worked out, with your first item."""
        lbl = getattr(self, "tu_below_note", None)
        if lbl is None:
            return
        items = TU.cfg()["items"]
        b = TU.cfg().get("below", 0.3)
        if items and int(items[0].get("keep") or 0) > 0:
            k = int(items[0]["keep"])
            at = TU.remind_at(k, b)
            n = int(at) if at == int(at) else int(at) + 1
            txt = f"your Keep - e.g. Keep {k}: a card under {n}" if b else "your Keep - a card as soon as you're under it"
        else:
            txt = "your Keep"
        try:
            lbl.config(text=txt)
        except tk.TclError:
            pass

    def topup_items(self):
        old = getattr(self, "tu_items_win", None)
        try:
            if old is not None and old.winfo_exists():
                old.lift()
                return old
        except tk.TclError:
            pass
        P2 = C["panel2"]
        w = tk.Toplevel(self.root, bg=C["accent"], padx=1, pady=1)
        w.title("Top Up Reminders")
        try:
            w.transient(self.root)
        except tk.TclError:
            pass
        w.bind("<Escape>", lambda _e: w.destroy())
        self.tu_items_win = w
        inner = tk.Frame(w, bg=P2, padx=16, pady=12)
        inner.pack(fill="both", expand=True)
        top = tk.Frame(inner, bg=P2)
        top.pack(fill="x")
        tk.Label(top, text="Your items", bg=P2, fg=C["text"], font=("Segoe UI", 12, "bold")).pack(side="left")
        tip = tk.Label(top, text="ⓘ", bg=P2, fg=C["muted"], cursor="question_arrow")
        tip.pack(side="left", padx=8)
        Tooltip(tip, "In hideout or town, opening your inventory with less than Keep (minus Remind when) shows one "
                     "card. Seen: what your inventory held the last time it was open (every stack added up).")
        tk.Label(inner, text="Keep at least this many of each in your inventory.", bg=P2, fg=C["muted"],
                 anchor="w").pack(fill="x", pady=(2, 8))
        # 2.131.2: Remind when - "30% below" Keep, like the price checks' "10% below"
        rw = tk.Frame(inner, bg=P2)
        rw.pack(fill="x", pady=(0, 8))
        tk.Label(rw, text="Remind when", bg=P2, fg=C["text"]).pack(side="left")
        self.tu_below_var = tk.StringVar(value=TU.below_text(TU.cfg().get("below", 0.3)))
        bcb = ttk.Combobox(rw, textvariable=self.tu_below_var, state="readonly", width=12,
                           values=[TU.below_text(b) for b in TU.BELOW_STEPS])
        bcb.pack(side="left", padx=8)
        bcb.bind("<<ComboboxSelected>>", lambda _e: self.topup_below_set(self.tu_below_var.get()))
        self.tu_below_note = tk.Label(rw, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9))
        self.tu_below_note.pack(side="left")
        self.topup_below_paint()
        self.tu_list = tk.Frame(inner, bg=P2)
        self.tu_list.pack(fill="both", expand=True)
        # 2.131.4 (feedback: "go back to the Items... button and add new items to the list on top of what they
        # have"): + Add more - a name now (taught later with Ctrl+C), or teach it in game
        self.tu_add = tk.Frame(inner, bg=P2)
        self.tu_add.pack(fill="x", pady=(8, 0))
        foot = tk.Frame(inner, bg=P2)
        foot.pack(fill="x", pady=(8, 0))
        ttk.Button(foot, text="Done", style="Primary.TButton", command=w.destroy).pack(side="right")
        ab = ttk.Button(foot, text="+ Add more", command=self.topup_add_open)
        ab.pack(side="left")
        Tooltip(ab, "Add an item by its name, or in game: open your inventory, hover it and press "
                    f"{self.topup_key_text()}.")
        self.topup_paint_list()
        try:
            from .style import center_over
            center_over(w, self.root)
        except Exception:
            buglog.caught()
        return w

    def topup_paint_list(self):
        box = getattr(self, "tu_list", None)
        try:
            if box is None or not box.winfo_exists():
                return
        except tk.TclError:
            return
        for ch in box.winfo_children():
            ch.destroy()
        P2 = C["panel2"]
        items = TU.cfg()["items"]
        self.tu_keep_vars, self.tu_seen_labels, self.tu_icons = {}, {}, []
        if not items:
            tk.Label(box, text="No items yet. In game: open your inventory, hover an item and press "
                               f"{self.topup_key_text()} - or + Add more below.", bg=P2, fg=C["text"], wraplength=420,
                     justify="left", anchor="w").pack(fill="x")
            return
        head = tk.Frame(box, bg=P2)
        head.pack(fill="x")
        for txt, wd in (("", 5), ("Item", 26), ("Keep", 8), ("Seen", 8), ("", 3)):
            tk.Label(head, text=txt, bg=P2, fg=C["muted"], font=("Segoe UI", 9, "bold"), width=wd,
                     anchor="w").pack(side="left")
        tot = self.topup_totals()
        for it in items:
            name = it["name"]
            r = tk.Frame(box, bg=P2)
            r.pack(fill="x", pady=2)
            ic = TU.icon_b64(name)
            img = None
            if ic:
                try:
                    img = tk.PhotoImage(data=ic)
                    self.tu_icons.append(img)
                except tk.TclError:
                    img = None
            tk.Label(r, image=img, bg=P2, width=40, height=40).pack(side="left", padx=(0, 8)) if img else \
                tk.Label(r, text="", bg=P2, width=5).pack(side="left")
            tk.Label(r, text=name, bg=P2, fg=C["text"], width=26, anchor="w").pack(side="left")
            v = tk.StringVar(value=str(it.get("keep", 1)))
            sp = ttk.Spinbox(r, from_=0, to=9999, textvariable=v, width=6,
                             command=lambda n=name, v=v: self.topup_keep(n, v.get()))
            sp.pack(side="left", padx=(0, 16))
            sp.bind("<FocusOut>", lambda _e, n=name, v=v: self.topup_keep(n, v.get()))
            sp.bind("<Return>", lambda _e, n=name, v=v: self.topup_keep(n, v.get()))
            self.tu_keep_vars[name] = v
            seen = tk.Label(r, text=_seen(tot, name), bg=P2, fg=C["text"], width=8, anchor="w")
            seen.pack(side="left")
            if name not in TU.learned():
                Tooltip(seen, f"Not taught yet: open your inventory, hover it and press {self.topup_key_text()}.")
            self.tu_seen_labels[name] = seen
            x = ttk.Button(r, text="✕", width=3, command=lambda n=name: self.topup_forget(n))
            x.pack(side="left")
            Tooltip(x, f"Remove {name}")

    def topup_paint_seen(self):
        labels = getattr(self, "tu_seen_labels", None) or {}
        if not labels:
            return
        tot = self.topup_totals()
        for name, lab in labels.items():
            try:
                lab.config(text=_seen(tot, name))
            except tk.TclError:
                pass

    def topup_keep(self, name, value):
        try:
            n = max(0, int(str(value).strip() or 0))
        except ValueError:
            return
        for it in TU.cfg()["items"]:
            if it.get("name") == name:
                it["keep"] = n
        save_json("settings.json", SETTINGS)
        self.topup_below_paint()

    def topup_forget(self, name):
        TU.cfg()["items"] = [it for it in TU.cfg()["items"] if it.get("name") != name]
        save_json("settings.json", SETTINGS)
        TU.forget(name)
        self.topup_paint_list()


def _seen(tot, name):
    if name not in TU.learned():
        return "teach it"                               # (2.131.2: from League Plan - never taught yet)
    if name not in tot:
        return "-"
    n, sure = tot[name]
    return f"{n}" if sure else f"{n}+ ?"


def _thumb(img):
    return img.convert("L").resize((48, 20)).tobytes()

