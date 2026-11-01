"""The Money Makers window (2.28.0): community strats in one standard layout (left: the list, right: the strat) and a
simple run tracker of its own. Data and the layout check live in moneymakers.py."""
import json
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, ttk

from . import moneymakers as MM
from .config import SETTINGS, save_json
from .style import C, MONO, SegBar, place_near

ORIGIN = {"community": "Community", "mine": "Mine", "example": "Example"}


def _hms(secs):
    secs = int(max(0, secs))
    h, rest = divmod(secs, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class MoneyMakersPage:
    """Mixed into App."""

    def build_money_window(self, body):
        P1 = C["panel"]
        self.mm_strats, self.mm_sel, self.mm_sort = [], None, ("thoughts_per_click", False)
        self.mm_run = None                                   # {"strat", "start"} while a run is going
        self.mm_page = SegBar(body, ["Strats", "Run tracker"], command=lambda v: self.mm_show_page(), size=10,
                              pad=(16, 5))
        self.mm_page.pack(anchor="w", padx=10, pady=(8, 0))
        self.mm_strat_page = tk.Frame(body, bg=P1)
        self.mm_run_page = tk.Frame(body, bg=P1)
        self.mm_build_strats(self.mm_strat_page)
        self.mm_build_runs(self.mm_run_page)
        self.mm_strat_page.pack(fill="both", expand=True)
        self.mm_reload()

    def mm_show_page(self):
        strats = self.mm_page.value == "Strats"
        (self.mm_run_page if strats else self.mm_strat_page).pack_forget()
        (self.mm_strat_page if strats else self.mm_run_page).pack(fill="both", expand=True)
        if not strats:
            self.mm_runs_refresh()

    # ---------------- the strats list
    def mm_build_strats(self, page):
        P1, P2 = C["panel"], C["panel2"]
        bar = tk.Frame(page, bg=P1, padx=10, pady=8)
        bar.pack(fill="x")
        tk.Label(bar, text="Search", bg=P1, fg=C["muted"]).pack(side="left", padx=(0, 6))
        self.mm_q = tk.StringVar()
        self.mm_q.trace_add("write", lambda *_a: self.root.after_idle(self.mm_fill))
        ttk.Entry(bar, textvariable=self.mm_q, width=22).pack(side="left")
        tk.Label(bar, text="Category", bg=P1, fg=C["muted"]).pack(side="left", padx=(14, 6))
        self.mm_cat = tk.StringVar(value="All")
        cb = ttk.Combobox(bar, textvariable=self.mm_cat, values=("All",) + MM.CATEGORIES, state="readonly", width=12)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: (self.mm_fill(), self.root.after(20, self.root.focus_set)))
        tk.Label(bar, text="Thoughts per Click at most", bg=P1, fg=C["muted"]).pack(side="left", padx=(14, 6))
        self.mm_max = tk.StringVar(value="5")
        mx = ttk.Combobox(bar, textvariable=self.mm_max, values=("1", "2", "3", "4", "5"), state="readonly", width=3)
        mx.pack(side="left")
        mx.bind("<<ComboboxSelected>>", lambda e: (self.mm_fill(), self.root.after(20, self.root.focus_set)))
        ttk.Button(bar, text="↻ Check for new strats", command=lambda: self.mm_check_live(force=True)).pack(side="right")
        self.mm_live_lbl = tk.Label(bar, text="", bg=P1, fg=C["muted"], font=("Segoe UI", 9))
        self.mm_live_lbl.pack(side="right", padx=8)

        bar2 = tk.Frame(page, bg=P1, padx=10)
        bar2.pack(fill="x", pady=(0, 6))
        for text, cmd in (("Import file…", self.mm_import), ("+ Add my own", self.mm_add)):
            ttk.Button(bar2, text=text, command=cmd).pack(side="right", padx=(6, 0))
        leg = tk.Label(bar2, text="🧠 Thoughts per Click = how much thinking (1 Autopilot … 5 Big brain)    "
                                  "🖱 Clicks per hour = how busy your hands are (Chill · Steady · Busy · Frantic)",
                       bg=P1, fg="#ffd9a8", font=("Segoe UI", 9), anchor="w", justify="left")
        leg.pack(side="left", fill="x", expand=True)
        leg.bind("<Configure>", lambda e: leg.config(wraplength=max(200, e.width - 4)))

        pane = ttk.PanedWindow(page, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        left = tk.Frame(pane, bg=P1)
        pane.add(left, weight=3)
        self.mm_pane = pane
        cols = (("name", "Strat", 170, "w"), ("category", "Category", 78, "w"),
                ("thoughts_per_click", "🧠 Thoughts", 84, "center"), ("clicks_per_hour", "🖱 Clicks/h", 104, "center"),
                ("profit", "Profit / h", 84, "center"), ("origin", "From", 74, "center"))
        self.mm_tree = ttk.Treeview(left, columns=[c[0] for c in cols], show="headings", selectmode="browse")
        for cid, title, w, anchor in cols:
            self.mm_tree.heading(cid, text=title, command=lambda c=cid: self.mm_sort_by(c))
            self.mm_tree.column(cid, width=w, minwidth=56, anchor=anchor, stretch=cid == "name")
        self.mm_tree.tag_configure("mine", foreground=C["green"])
        self.mm_tree.tag_configure("example", foreground=C["muted"])
        sb = ttk.Scrollbar(left, orient="vertical", command=self.mm_tree.yview)
        self.mm_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.mm_tree.pack(side="left", fill="both", expand=True)
        self.mm_tree.bind("<<TreeviewSelect>>", lambda e: self.mm_pick())
        self.mm_tree.bind("<Button-3>", self.mm_menu)
        self.mm_empty = tk.Label(left, text="", bg=C["panel"], fg=C["muted"], font=("Segoe UI", 10))

        right = tk.Frame(pane, bg=P2, highlightthickness=1, highlightbackground=C["line"])
        pane.add(right, weight=2)
        acts = tk.Frame(right, bg=P2, padx=10, pady=8)
        acts.pack(fill="x")
        self.mm_btns = {}
        for key, text, cmd, style in (("track", "▶ Track runs", self.mm_track, "Accent.TButton"),
                                      ("regex", "Copy regex", self.mm_copy_regex, "TButton"),
                                      ("share", "Share…", self.mm_share, "TButton"),
                                      ("more", "⋯ More", self.mm_more, "TButton")):
            self.mm_btns[key] = ttk.Button(acts, text=text, command=cmd, style=style)
        self.mm_detail = tk.Text(right, bg=P2, fg=C["text"], relief="flat", wrap="word", padx=12, pady=6,
                                 font=("Segoe UI", 10), highlightthickness=0, cursor="arrow")
        dsb = ttk.Scrollbar(right, orient="vertical", command=self.mm_detail.yview)
        self.mm_detail.configure(yscrollcommand=dsb.set)
        dsb.pack(side="right", fill="y")
        self.mm_detail.pack(fill="both", expand=True)
        t = self.mm_detail
        t.tag_configure("title", font=("Segoe UI", 14, "bold"), foreground=C["text"], spacing3=2)
        t.tag_configure("meta", foreground=C["muted"], font=("Segoe UI", 9))
        t.tag_configure("summary", font=("Segoe UI", 10, "italic"), spacing1=6, spacing3=6)
        t.tag_configure("h", font=("Segoe UI", 10, "bold"), foreground=C["accent"], spacing1=10, spacing3=2)
        t.tag_configure("stat", font=("Segoe UI", 10, "bold"), foreground="#ffd9a8")
        t.tag_configure("li", lmargin1=10, lmargin2=26)
        t.tag_configure("mono", font=(MONO, 9), foreground=C["good"])
        t.tag_configure("link", foreground="#8fc4ff", underline=True)
        t.tag_bind("link", "<Enter>", lambda e: t.config(cursor="hand2"))
        t.tag_bind("link", "<Leave>", lambda e: t.config(cursor="arrow"))
        self.mm_show_detail(None)
        pane.bind("<Map>", lambda e: self.root.after(50, self.mm_sash), add="+")

    def mm_sash(self):
        try:
            w = self.mm_pane.winfo_width()
            if w > 200 and not getattr(self, "_mm_sash_set", False):
                self._mm_sash_set = True
                self.mm_pane.sashpos(0, max(int(w * 0.55), min(620, w - 300)))
        except tk.TclError:
            pass

    def mm_reload(self, keep=None):
        self.mm_strats = MM.all_strats()
        self.mm_fill(keep)

    def mm_rows(self):
        q = self.mm_q.get().strip().lower()
        cat, mx = self.mm_cat.get(), int(self.mm_max.get() or 5)
        out = []
        for s in self.mm_strats:
            if cat != "All" and s.get("category") != cat:
                continue
            if s.get("thoughts_per_click", 5) > mx:
                continue
            if q and q not in json.dumps(s, ensure_ascii=False).lower():
                continue
            out.append(s)
        key, rev = self.mm_sort
        num = key in ("thoughts_per_click", "clicks_per_hour", "profit")

        def k(s):
            if key == "profit":
                p = s.get("profit_per_hour") or {}
                return p.get("high") or p.get("low") or -1
            return s.get(key, 0) if num else str(s.get(key, "")).lower()
        return sorted(out, key=k, reverse=rev)

    def mm_fill(self, keep=None):
        keep = keep or self.mm_sel
        tv = self.mm_tree
        tv.delete(*tv.get_children())
        rows = self.mm_rows()
        for s in rows:
            tpc = s.get("thoughts_per_click", 0)
            cph = s.get("clicks_per_hour", 0)
            tv.insert("", "end", iid=s["id"] + "|" + s["origin"], tags=(s["origin"],),
                      values=(s["name"], s.get("category", ""), f"{'●' * tpc}{'○' * (5 - tpc)} {tpc}",
                              f"{cph:,} · {MM.click_band(cph)}", MM.money_text(s.get("profit_per_hour")),
                              ORIGIN.get(s["origin"], "")))
        if rows:
            self.mm_empty.place_forget()
        else:
            self.mm_empty.config(text="No strats match." if self.mm_strats else
                                 "No strats yet. Press ↻ Check for new strats, or + Add my own.")
            self.mm_empty.place(relx=0.5, rely=0.3, anchor="center")
        if keep and tv.exists(keep):
            tv.selection_set(keep)
            tv.see(keep)
        elif rows:
            tv.selection_set(tv.get_children()[0])
        else:
            self.mm_show_detail(None)

    def mm_sort_by(self, col):
        key = "thoughts_per_click" if col == "thoughts_per_click" else col
        cur, rev = self.mm_sort
        self.mm_sort = (key, not rev if cur == key else key in ("profit",))
        self.mm_fill()

    def mm_current(self):
        sel = self.mm_tree.selection()
        if not sel:
            return None
        return next((s for s in self.mm_strats if s["id"] + "|" + s["origin"] == sel[0]), None)

    def mm_pick(self):
        s = self.mm_current()
        self.mm_sel = self.mm_tree.selection()[0] if s else None
        self.mm_show_detail(s)

    def mm_show_detail(self, s):
        t = self.mm_detail
        t.config(state="normal")
        t.delete("1.0", "end")
        for b in self.mm_btns.values():
            b.pack_forget()
        if not s:
            t.insert("end", "Pick a strat on the left.", "meta")
            t.config(state="disabled")
            return
        show = ["track"] + (["regex"] if s.get("regex") else []) + ["share", "more"]
        for key in show:
            self.mm_btns[key].pack(side="left", padx=(0, 6))
        t.insert("end", s["name"] + "\n", "title")
        t.insert("end", f"{s.get('category', '')} · by {s.get('author', '?')} · game {s.get('patch', '?')} · "
                        f"updated {s.get('updated', '?')} · {ORIGIN.get(s['origin'], '')}"
                        + (" · works at league start" if s.get("league_start") else "") + "\n", "meta")
        t.insert("end", s.get("summary", "") + "\n", "summary")
        tpc, cph = s.get("thoughts_per_click", 0), s.get("clicks_per_hour", 0)
        t.insert("end", "🧠 Thoughts per Click  ", "h")
        t.insert("end", f"{tpc} - {MM.THOUGHTS.get(tpc, '')}\n", "stat")
        t.insert("end", "🖱 Clicks per hour  ", "h")
        t.insert("end", f"{cph:,} ({MM.click_band(cph)})\n", "stat")
        t.insert("end", "Profit per hour  ", "h")
        t.insert("end", MM.money_text(s.get("profit_per_hour"), " / h") + "     ", "stat")
        t.insert("end", "Investment  ", "h")
        t.insert("end", MM.money_text(s.get("investment")) + "\n", "stat")
        mine = MM.stats(MM.runs(), s["id"])
        if mine["runs"]:
            pph = mine["profit_per_hour"]
            t.insert("end", "Your runs  ", "h")
            t.insert("end", f"{mine['runs']} runs, {_hms(mine['avg_secs'])} each"
                            + (f", {pph:.1f} div / h" if pph is not None else "") + "\n", "stat")
        for key, title in (("requirements", "Requirements"), ("setup", "Setup"), ("steps", "Steps"),
                           ("loot", "Loot to sell"), ("tips", "Tips"), ("risks", "Risks")):
            items = s.get(key) or []
            if not items:
                continue
            t.insert("end", title + "\n", "h")
            for i, line in enumerate(items, 1):
                t.insert("end", (f"{i}. " if key == "steps" else "• ") + line + "\n", "li")
        if s.get("regex"):
            t.insert("end", "Stash regex\n", "h")
            t.insert("end", s["regex"] + "\n", "mono")
        if s.get("tags"):
            t.insert("end", "Tags  ", "h")
            t.insert("end", ", ".join(s["tags"]) + "\n", "meta")
        if s.get("sources"):
            t.insert("end", "Sources\n", "h")
            for i, src in enumerate(s["sources"]):
                tag = f"src{i}"
                t.insert("end", "• ", "li")
                t.insert("end", (src.get("title") or src["url"]) + "\n", ("li", "link", tag))
                t.tag_bind(tag, "<Button-1>", lambda e, u=src["url"]: webbrowser.open(u))
        t.config(state="disabled")

    def mm_more(self):
        b = self.mm_btns["more"]
        self.mm_menu(None, b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())

    def mm_menu(self, e, x=None, y=None):
        """Right-click a strat (or ⋯ More): everything you can do with it."""
        if e is not None:
            row = self.mm_tree.identify_row(e.y)
            if not row:
                return
            self.mm_tree.selection_set(row)
            x, y = e.x_root, e.y_root
        s = self.mm_current()
        if not s:
            return
        m = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["text"], activebackground="#2c4a84")
        m.add_command(label="▶ Track runs", command=self.mm_track)
        if s and s.get("regex"):
            m.add_command(label="Copy regex", command=self.mm_copy_regex)
        m.add_command(label="Share…", command=self.mm_share)
        m.add_command(label="Export…", command=self.mm_export)
        if s and s["origin"] == "mine":
            m.add_separator()
            m.add_command(label="Edit", command=self.mm_edit)
            m.add_command(label="Delete", command=self.mm_delete)
        m.tk_popup(x, y)

    # ---------------- live updates from GitHub
    def mm_on_show(self):
        self.mm_check_live(force=False)

    def mm_check_live(self, force=False):
        if getattr(self, "_mm_checking", False):
            return
        self._mm_checking = True
        if force:
            self.mm_live_lbl.config(text="Checking GitHub…", fg=C["muted"])

        def work():
            res = MM.fetch_live(force=force)
            self.root.after(0, lambda: self.mm_live_done(res, force))
        threading.Thread(target=work, daemon=True).start()

    def mm_live_done(self, res, force):
        self._mm_checking = False
        what, info = res
        if what != "skip":
            save_json("settings.json", SETTINGS)
        if what == "new":
            self.mm_reload()
            self.mm_live_lbl.config(text=f"New strats: {info} in the shared list.", fg=C["green"])
        elif what == "same" and force:
            self.mm_live_lbl.config(text="Up to date.", fg=C["muted"])
        elif what == "error" and force:
            self.mm_live_lbl.config(text=info, fg=C["red"])

    # ---------------- actions
    def mm_copy_regex(self):
        s = self.mm_current()
        if s and s.get("regex"):
            self.root.clipboard_clear()
            self.root.clipboard_append(s["regex"])
            self.own_clip = s["regex"]
            self._say("Copied the strat's stash search. In game: Ctrl+F, Ctrl+V.", 6)

    def mm_share(self):
        s = self.mm_current()
        if s:
            webbrowser.open(MM.issue_link(s))
            self._say("Opened a GitHub issue with the strat filled in - check it and press Submit.", 8)

    def mm_export(self):
        s = self.mm_current()
        if not s:
            return
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".json", initialfile=s["id"] + ".json",
                                            filetypes=[("Strat", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(MM.tidy(s), f, indent=2, ensure_ascii=False)
            self._say(f"Saved {path}", 6)

    def mm_import(self, path=None):
        path = path or filedialog.askopenfilename(parent=self.root, filetypes=[("Strat", "*.json")])
        if not path:
            return None
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:
            self.app_toast(f"Couldn't read that file ({e.__class__.__name__}).", "Import strat")
            return None
        items = d.get("strats") if isinstance(d, dict) and "strats" in d else d if isinstance(d, list) else [d]
        mine = MM.mine()
        added, bad = 0, []
        for s in items:
            if isinstance(s, dict):
                s = {k: v for k, v in s.items() if k != "origin"}
            probs = MM.validate(s)
            if probs:
                bad.append(f"{(s or {}).get('name', '?') if isinstance(s, dict) else '?'}: {probs[0]}")
                continue
            mine = [m for m in mine if m["id"] != s["id"]] + [s]
            added += 1
        MM.save_mine(mine)
        self.mm_reload()
        msg = f"Added {added} strat{'s' if added != 1 else ''} to Mine."
        if bad:
            msg += "\nLeft out (not in the standard layout): " + "; ".join(bad[:3])
        self.app_toast(msg, "Import strat")
        return added

    def mm_delete(self):
        s = self.mm_current()
        if s and s["origin"] == "mine":
            MM.save_mine([m for m in MM.mine() if m["id"] != s["id"]])
            self.mm_sel = None
            self.mm_reload()

    def mm_add(self):
        self.mm_form(MM.new_strat())

    def mm_edit(self):
        s = self.mm_current()
        if s and s["origin"] == "mine":
            self.mm_form(dict(s))

    def mm_form(self, s):
        """Add / edit one of your strats - the same fields as the shared layout."""
        P1, P2 = C["panel"], C["panel2"]
        win = tk.Toplevel(self.root, bg=P1)
        win.title("Your strat")
        win.transient(self.root)
        self.mm_form_win = win
        f = tk.Frame(win, bg=P1, padx=14, pady=10)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)
        v = {}
        r = 0

        def entry(key, label, value, width=40):
            nonlocal r
            tk.Label(f, text=label, bg=P1, fg=C["text"], anchor="w").grid(row=r, column=0, sticky="w", pady=2)
            v[key] = tk.StringVar(value=value)
            ttk.Entry(f, textvariable=v[key], width=width).grid(row=r, column=1, sticky="we", pady=2)
            r += 1

        def combo(key, label, values, value):
            nonlocal r
            tk.Label(f, text=label, bg=P1, fg=C["text"], anchor="w").grid(row=r, column=0, sticky="w", pady=2)
            v[key] = tk.StringVar(value=value)
            ttk.Combobox(f, textvariable=v[key], values=values, state="readonly", width=40).grid(
                row=r, column=1, sticky="w", pady=2)
            r += 1

        def lines(key, label, h=3):
            nonlocal r
            tk.Label(f, text=label, bg=P1, fg=C["text"], anchor="nw").grid(row=r, column=0, sticky="nw", pady=2)
            t = tk.Text(f, height=h, width=60, bg=C["odd"], fg=C["text"], insertbackground=C["text"], relief="flat",
                        highlightthickness=1, highlightbackground=C["line"], font=("Segoe UI", 9), wrap="word")
            t.insert("1.0", "\n".join(s.get(key) or []))
            t.grid(row=r, column=1, sticky="we", pady=2)
            v[key] = t
            r += 1

        p, inv = s.get("profit_per_hour") or {}, s.get("investment") or {}
        entry("name", "Name", s.get("name", ""))
        combo("category", "Category", MM.CATEGORIES, s.get("category", "Mapping"))
        entry("summary", "Summary (one line)", s.get("summary", ""))
        entry("patch", "Game version", s.get("patch", ""), 10)
        combo("tpc", "🧠 Thoughts per Click", [f"{k} - {t}" for k, t in MM.THOUGHTS.items()],
              f"{s.get('thoughts_per_click', 2)} - {MM.THOUGHTS[s.get('thoughts_per_click', 2)]}")
        entry("cph", "🖱 Clicks per hour", str(s.get("clicks_per_hour", 600)), 10)
        entry("profit", "Profit per hour (div, e.g. 5-10)",
              "" if not p else f"{p.get('low', '')}-{p.get('high', '')}".strip("-"), 10)
        entry("inv", "Investment (div)", "" if not inv else f"{inv.get('amount', '')}", 10)
        lines("requirements", "Requirements")
        lines("setup", "Setup")
        lines("steps", "Steps (one per line)", 5)
        lines("loot", "Loot to sell")
        lines("tips", "Tips")
        lines("risks", "Risks")
        entry("regex", "Stash regex", s.get("regex", ""))
        entry("sources", "Source link", (s.get("sources") or [{}])[0].get("url", ""))
        msg = tk.Label(f, text="One line per item in the boxes. Only Name, Summary and Steps are needed.", bg=P1,
                       fg=C["muted"], anchor="w", font=("Segoe UI", 9))
        msg.grid(row=r, column=0, columnspan=2, sticky="we", pady=(6, 0))
        r += 1

        def num(text):
            text = text.strip()
            return float(text) if text else None

        def save():
            out = dict(s)
            out.pop("origin", None)
            for k in ("name", "category", "summary", "patch", "regex"):
                out[k] = v[k].get().strip()
            for k in ("requirements", "setup", "steps", "loot", "tips", "risks"):
                out[k] = [ln.strip() for ln in v[k].get("1.0", "end").split("\n") if ln.strip()]
            try:
                out["thoughts_per_click"] = int(v["tpc"].get().split(" ")[0])
                out["clicks_per_hour"] = int(float(v["cph"].get().replace(",", "") or 0))
                pr = v["profit"].get().replace(" ", "")
                if pr:
                    lo, _, hi = pr.partition("-")
                    out["profit_per_hour"] = {"low": num(lo), "high": num(hi or lo), "unit": "div"}
                else:
                    out.pop("profit_per_hour", None)
                amt = num(v["inv"].get())
                if amt is not None:
                    out["investment"] = {"amount": amt, "unit": "div"}
                else:
                    out.pop("investment", None)
            except ValueError:
                msg.config(text="Numbers only in Clicks per hour, Profit and Investment.", fg=C["red"])
                return
            url = v["sources"].get().strip()
            out["sources"] = [{"title": url, "url": url}] if url else []
            out["patch"] = out["patch"] or "?"
            out["updated"] = time.strftime("%Y-%m-%d")
            if not s.get("name"):
                out["id"] = MM.slug("my-" + out["name"])
            out = MM.tidy(out)
            probs = MM.validate(out)
            if probs:
                msg.config(text="Not saved: " + probs[0], fg=C["red"])
                return
            mine = [m for m in MM.mine() if m["id"] not in (s.get("id"), out["id"])] + [out]
            MM.save_mine(mine)
            win.destroy()
            self.mm_reload(keep=out["id"] + "|mine")

        btns = tk.Frame(f, bg=P1)
        btns.grid(row=r, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="Save", style="Accent.TButton", command=save).pack(side="right")
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right", padx=6)
        win.bind("<Escape>", lambda e: win.destroy())
        self.mm_form_save = save
        self.mm_form_vars = v
        place_near(self.root, win, self.root.winfo_pointerx() - 200, self.root.winfo_pointery() - 200)
        return win

    # ---------------- the run tracker (its own, simple)
    def mm_build_runs(self, page):
        P1, P2 = C["panel"], C["panel2"]
        top = tk.Frame(page, bg=P2, padx=14, pady=12, highlightthickness=1, highlightbackground=C["line"])
        top.pack(fill="x", padx=10, pady=(10, 8))
        tk.Label(top, text="Strat", bg=P2, fg=C["muted"]).grid(row=0, column=0, sticky="w")
        self.mm_run_strat = tk.StringVar(value="(no strat)")
        self.mm_run_box = ttk.Combobox(top, textvariable=self.mm_run_strat, state="readonly", width=40)
        self.mm_run_box.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.mm_run_box.bind("<<ComboboxSelected>>", lambda e: (self.mm_runs_refresh(),
                                                               self.root.after(20, self.root.focus_set)))
        self.mm_clock = tk.Label(top, text="0:00", bg=P2, fg=C["text"], font=(MONO, 28, "bold"))
        self.mm_clock.grid(row=0, column=2, rowspan=2, padx=24)
        self.mm_go = ttk.Button(top, text="▶ Start run", style="Accent.TButton", command=self.mm_run_toggle)
        self.mm_go.grid(row=0, column=3, rowspan=2, sticky="ns")
        tk.Label(top, text="Profit this run (div)", bg=P2, fg=C["muted"]).grid(row=1, column=0, sticky="w",
                                                                                pady=(8, 0))
        self.mm_profit = tk.StringVar()
        ttk.Entry(top, textvariable=self.mm_profit, width=10).grid(row=1, column=1, sticky="w", padx=(8, 0),
                                                                    pady=(8, 0))
        tk.Label(top, text="Start when you enter the map (or start the block), end when you're done and have sold or "
                           "counted the loot. Type the profit any time before you end the run - or leave it empty.",
                 bg=P2, fg=C["muted"], font=("Segoe UI", 9), wraplength=700, justify="left").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))

        self.mm_summary = tk.Label(page, text="", bg=P1, fg="#ffd9a8", font=("Segoe UI", 11, "bold"), anchor="w")
        self.mm_summary.pack(fill="x", padx=12, pady=(0, 6))
        box = tk.Frame(page, bg=P1)
        box.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        cols = (("when", "When", 140, "w"), ("strat", "Strat", 220, "w"), ("time", "Time", 80, "center"),
                ("profit", "Profit", 90, "center"))
        self.mm_runs_tree = ttk.Treeview(box, columns=[c[0] for c in cols], show="headings", selectmode="extended")
        for cid, title, w, anchor in cols:
            self.mm_runs_tree.heading(cid, text=title)
            self.mm_runs_tree.column(cid, width=w, anchor=anchor, stretch=cid == "strat")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.mm_runs_tree.yview)
        self.mm_runs_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.mm_runs_tree.pack(side="left", fill="both", expand=True)
        self.mm_runs_tree.bind("<Delete>", lambda e: self.mm_runs_delete())
        bot = tk.Frame(page, bg=P1)
        bot.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(bot, text="Delete selected runs", command=self.mm_runs_delete).pack(side="left")

    def mm_run_names(self):
        names = {s["id"]: s["name"] for s in MM.all_strats()}
        return names

    def mm_runs_refresh(self):
        names = self.mm_run_names()
        self.mm_run_ids = {"(no strat)": None}
        for sid, name in sorted(names.items(), key=lambda kv: kv[1].lower()):
            self.mm_run_ids[name] = sid
        self.mm_run_box.config(values=list(self.mm_run_ids))
        if self.mm_run_strat.get() not in self.mm_run_ids:
            self.mm_run_strat.set("(no strat)")
        items = MM.runs()
        sid = self.mm_run_ids.get(self.mm_run_strat.get())
        tv = self.mm_runs_tree
        tv.delete(*tv.get_children())
        for i, rr in reversed(list(enumerate(items))):
            if sid and rr.get("strat") != sid:
                continue
            p = rr.get("profit")
            tv.insert("", "end", iid=str(i), values=(time.strftime("%Y-%m-%d %H:%M", time.localtime(rr["start"])),
                                                     names.get(rr.get("strat"), "(no strat)"),
                                                     _hms(rr["end"] - rr["start"]),
                                                     "" if p is None else f"{p:g} div"))
        st = MM.stats(items, sid)
        if st["runs"]:
            pph = st["profit_per_hour"]
            text = (f"{st['runs']} runs · {_hms(st['avg_secs'])} each · {st['per_hour']:.1f} runs / hour"
                    + (f" · {st['profit']:g} div total · {pph:.1f} div / hour" if pph is not None else ""))
        else:
            text = "No runs yet - press ▶ Start run."
        self.mm_summary.config(text=text)

    def mm_run_toggle(self):
        if self.mm_run is None:
            sid = getattr(self, "mm_run_ids", {}).get(self.mm_run_strat.get())
            self.mm_run = {"strat": sid, "start": time.time()}
            self.mm_go.config(text="■ End run")
            self.mm_tick()
            return
        txt = self.mm_profit.get().strip().replace(",", ".")
        try:
            profit = float(txt) if txt else None
        except ValueError:
            self._say("Profit: a number of divines (e.g. 2.5), or leave it empty.", 6)
            return
        items = MM.runs()
        items.append({"strat": self.mm_run["strat"], "start": self.mm_run["start"], "end": time.time(),
                      "profit": profit})
        MM.save_runs(items)
        self.mm_run = None
        self.mm_profit.set("")
        self.mm_go.config(text="▶ Start run")
        self.mm_clock.config(text="0:00")
        self.mm_runs_refresh()

    def mm_tick(self):
        if self.mm_run is None:
            return
        self.mm_clock.config(text=_hms(time.time() - self.mm_run["start"]))
        self.root.after(1000, self.mm_tick)

    def mm_runs_delete(self):
        sel = {int(i) for i in self.mm_runs_tree.selection()}
        if sel:
            MM.save_runs([r for i, r in enumerate(MM.runs()) if i not in sel])
            self.mm_runs_refresh()

    def mm_track(self):
        s = self.mm_current()
        self.mm_page.pick("Run tracker", notify=False)
        self.mm_show_page()
        if s:
            self.mm_runs_refresh()
            name = next((n for n, i in self.mm_run_ids.items() if i == s["id"]), None)
            if name and self.mm_run is None:
                self.mm_run_strat.set(name)
                self.mm_runs_refresh()
