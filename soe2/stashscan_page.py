"""2.102.0 Wealth › Scan stash (beta) - the card over the game and the check-before-saving window.

The card asks for one tab at a time ("Open your Currency tab" - [Start reading]), reads it (stashread.scan, in a
thread: one picture, kept in memory, then dropped) and moves on. At the end - or Finish at any time - a window in the
app lists what was read; fix any number (double-click), drop rows (Delete), then Save sets them in Wealth › Counted by
hand, like Count currency's Finish does. Nothing is saved before you press Save.
The card is left out of screen captures (so it never covers what's read) and never takes the keyboard from the game."""
import threading
import tkinter as tk
from tkinter import simpledialog, ttk

from . import stashread as SR
from .config import SETTINGS
from .stashlayouts import ORDER, TABS
from .style import C


def _cls(name):
    if name.startswith("Omen of"):
        return "Omen"
    if name in ("Simulacrum", "Raven's Reflection", "Breachstone", "Kulemak's Invitation"):
        return "Map Fragments"
    return "Stackable Currency"


class StashScanPage:
    # ---------------------------------------------------------------- start / stop
    def stash_scan_start(self):
        why = SR.available()
        if why:
            self._w_tell(f"Scan stash can't run here: {why}.")
            return
        if getattr(self, "ss", None):
            self.stash_scan_card()
            return
        self.ss = {"i": 0, "got": {}, "unread": {}, "busy": False, "note": "", "kind": ""}
        self.stash_scan_card()

    def stash_scan_cancel(self):
        self.ss = None
        self._ss_close()

    def _ss_close(self):
        w = getattr(self, "ss_win", None)
        self.ss_win = None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def stash_scan_skip(self):
        if not self.ss or self.ss["busy"]:
            return
        self.ss["note"], self.ss["kind"] = f"Skipped {TABS[ORDER[self.ss['i']]]['label']}.", ""
        self._ss_next()

    def _ss_next(self):
        self.ss["i"] += 1
        if self.ss["i"] >= len(ORDER):
            return self.stash_scan_finish()
        self.stash_scan_card()

    def stash_scan_finish(self):
        ss = self.ss
        self.stash_scan_cancel()
        if ss and (ss["got"] or ss["unread"]):
            self.stash_scan_review(ss)
        elif ss is not None:
            self._w_tell("Scan stash: nothing was read.", "ok")

    # ---------------------------------------------------------------- reading
    def stash_scan_read(self):
        ss = self.ss
        if not ss or ss["busy"]:
            return
        ss["busy"] = True
        tab = ORDER[ss["i"]]
        self.stash_scan_card()
        from .alerts_page import game_rect
        g = game_rect()
        rect = (g[0], g[1], g[0] + g[2], g[1] + g[3]) if g else (0, 0, self.root.winfo_screenwidth(),
                                                                  self.root.winfo_screenheight())

        def work():
            try:
                res = SR.scan(rect, tab)
            except Exception as e:
                res = {"ok": False, "why": f"Couldn't read: {e.__class__.__name__}.", "items": [], "unread": []}
                self.log_error("Scan stash")
            self.ui_q.put(("stash_scan_done", tab, res))
        threading.Thread(target=work, daemon=True).start()

    def ev_stash_scan_done(self, tab, res):
        ss = self.ss
        if not ss or ORDER[ss["i"]] != tab:
            return
        ss["busy"] = False
        if not res.get("ok"):
            ss["note"], ss["kind"] = res.get("why") or "Couldn't read that.", "bad"
            return self.stash_scan_card()
        ss["got"][tab] = list(res["items"])
        ss["unread"][tab] = list(res["unread"])
        n = len(res["items"])
        miss = f" · {len(res['unread'])} couldn't be read" if res["unread"] else ""
        ss["note"], ss["kind"] = f"{TABS[tab]['label']}: read {n} stack{'s' if n != 1 else ''}{miss}.", "ok"
        self._ss_next()

    # ---------------------------------------------------------------- the card over the game
    def stash_scan_card(self):
        self._ss_close()
        ss = self.ss
        if not ss:
            return
        tab = ORDER[ss["i"]]
        t = TABS[tab]
        from .overlaywin import pal, skinned
        P = pal()
        BG, TXT, MUT = (P["bg"], P["text"], P["muted"]) if skinned() else ("#101826", "#e8eefc", "#9aa6bd")
        EDGE_ = P["leather"] if skinned() else "#5b77ad"
        w = tk.Toplevel(self.root)
        w.withdraw()
        w.overrideredirect(True)
        try:
            w.attributes("-topmost", True)
        except tk.TclError:
            pass
        box = tk.Frame(w, bg=BG, highlightthickness=1, highlightbackground=EDGE_, padx=16, pady=8)
        box.pack()
        head = tk.Frame(box, bg=BG)
        head.pack(fill="x")
        tk.Label(head, text="Scan stash", bg=BG, fg=TXT, font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(head, text=" BETA · may not work ", bg=C.get("accent", "#e8812c"), fg="#101010",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 0))
        x = tk.Label(head, text="✕", bg=BG, fg=MUT, cursor="hand2", font=("Segoe UI", 10))
        x.pack(side="right")
        x.bind("<Button-1>", lambda _e: self.stash_scan_cancel())
        tk.Label(box, text=f"Tab {ss['i'] + 1} of {len(ORDER)}", bg=BG, fg=MUT, font=("Segoe UI", 9),
                 anchor="w").pack(fill="x", pady=(8, 0))
        page = f" ({t['page']} page)" if t.get("page") else ""
        tk.Label(box, text=f"Open your {t['label']} tab{page}", bg=BG, fg=TXT, font=("Segoe UI", 12, "bold"),
                 anchor="w").pack(fill="x")
        if ss["note"]:
            col = {"ok": C.get("good", "#7fd17f"), "bad": C.get("red", "#e06c6c")}.get(ss["kind"], MUT)
            tk.Label(box, text=ss["note"], bg=BG, fg=col, font=("Segoe UI", 9), anchor="w", justify="left",
                     wraplength=320).pack(fill="x", pady=(4, 0))
        row = tk.Frame(box, bg=BG)
        row.pack(fill="x", pady=(8, 0))
        if ss["busy"]:
            tk.Label(row, text="Reading…", bg=BG, fg=TXT, font=("Segoe UI", 10)).pack(side="left")
        else:
            ttk.Button(row, text="Start reading", style="Primary.TButton",
                       command=self.stash_scan_read).pack(side="left")
            ttk.Button(row, text="Skip tab", command=self.stash_scan_skip).pack(side="left", padx=(8, 0))
            done = sum(len(v) for v in ss["got"].values())
            ttk.Button(row, text=f"Finish ({done})" if done else "Finish",
                       command=self.stash_scan_finish).pack(side="left", padx=(8, 0))
        tk.Label(box, text="Only looks at the screen: no keys, no clicks. Nothing is saved until you check it.",
                 bg=BG, fg=MUT, font=("Segoe UI", 9), anchor="w", justify="left",
                 wraplength=320).pack(fill="x", pady=(8, 0))
        w.update_idletasks()
        from .alerts_page import game_rect
        g = game_rect()
        if g:
            gx, gy, gw, gh = g
        else:
            gx, gy, gw, gh = 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        px = gx + min(int(gh * 0.66), max(0, gw - w.winfo_reqwidth() - 20))    # right of the stash panel
        py = gy + int(gh * 0.16)
        w.geometry(f"+{int(px)}+{int(py)}")
        w.deiconify()
        try:
            from .alerts_page import force_topmost
            from .toasts import no_activate
            no_activate(w)                           # clickable, but the game keeps the keyboard (and its stash)
            force_topmost(w)
        except Exception:
            pass
        from .remnant_page import no_capture
        no_capture(w)                                # never in the picture it takes
        self.ss_win = w

    # ---------------------------------------------------------------- check before saving
    def stash_scan_review(self, ss):
        rows = [(tab, n, q) for tab in ORDER for n, q in ss["got"].get(tab, [])]
        unread = [(tab, n) for tab in ORDER for n in ss["unread"].get(tab, [])]
        par = self.dlg_parent()
        dlg = tk.Toplevel(par)
        dlg.title("Scan stash (beta) - check the numbers")
        dlg.configure(bg=C["panel2"], padx=16, pady=12)
        dlg.transient(par)
        tk.Label(dlg, text="Check what was read. Double-click a number to fix it; Delete drops a row. Save sets these "
                           "in Wealth › Counted by hand (it replaces their counts; everything else is kept).",
                 bg=C["panel2"], fg=C["text"], justify="left", anchor="w", wraplength=520).pack(fill="x")
        f = tk.Frame(dlg, bg=C["panel2"])
        f.pack(fill="both", expand=True, pady=(8, 0))
        tv = ttk.Treeview(f, columns=("item", "qty", "tab"), show="headings", height=min(18, max(6, len(rows))),
                          selectmode="extended")
        for cid, title, wd, anc in (("item", "Item", 280, "w"), ("qty", "Count", 90, "e"), ("tab", "Tab", 100, "w")):
            tv.heading(cid, text=title)
            tv.column(cid, width=wd, anchor=anc, stretch=cid == "item")
        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        for tab, n, q in rows:
            tv.insert("", "end", values=(n, f"{q:,}", TABS[tab]["label"]))
        for tab, n in unread:
            tv.insert("", "end", values=(n, "?", TABS[tab]["label"]), tags=("unread",))
        tv.tag_configure("unread", foreground=C.get("red", "#e06c6c"))
        if unread:
            tk.Label(dlg, text=f"{len(unread)} slot{'s' if len(unread) != 1 else ''} had something but the number "
                               "couldn't be read (?): double-click to type it, or leave it out.",
                     bg=C["panel2"], fg=C["muted"], justify="left", anchor="w", wraplength=520).pack(fill="x",
                                                                                                   pady=(8, 0))

        def edit(_e=None):
            iid = tv.focus()
            if not iid:
                return
            name, q, tabl = tv.item(iid, "values")
            cur = int(str(q).replace(",", "")) if str(q).replace(",", "").isdigit() else None
            n = simpledialog.askinteger("Count", f"How many {name}?", parent=dlg, initialvalue=cur, minvalue=0)
            if n is not None:
                tv.item(iid, values=(name, f"{n:,}", tabl), tags=())

        def drop(_e=None):
            for iid in tv.selection():
                tv.delete(iid)

        def save():
            got = []
            for iid in tv.get_children():
                name, q, _t = tv.item(iid, "values")
                q = str(q).replace(",", "")
                if q.isdigit() and int(q) > 0:
                    got.append((name, int(q)))
            dlg.destroy()
            self.stash_scan_save(got)
        tv.bind("<Double-1>", edit)
        tv.bind("<Delete>", drop)
        btns = tk.Frame(dlg, bg=C["panel2"])
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Save", style="Primary.TButton", command=save).pack(side="right")
        ttk.Button(btns, text="Discard", command=dlg.destroy).pack(side="right", padx=(0, 8))
        dlg.bind("<Escape>", lambda _e: dlg.destroy())
        self.ss_review = dlg

    def stash_scan_save(self, got):
        from .wealth import WEALTH
        total = {}                                   # 2.114.2: one item in two tabs (Breach Splinter in Breach and
        for name, q in got:                          # in Fragments) - the two counts add up, not the last one
            total[name] = total.get(name, 0) + q
        got = list(total.items())
        for name, q in got:
            WEALTH.set_holding(name, q, _cls(name), src="scanned")
        if got:
            self._w_tell(f"Scan stash: saved {len(got)} stack count{'s' if len(got) != 1 else ''}.", "ok")
            lg = SETTINGS.get("league")
            if lg:
                threading.Thread(target=self._w_prices_then_snapshot, args=(lg, "scanned"), daemon=True).start()
        self.refresh_wealth(force=True)
