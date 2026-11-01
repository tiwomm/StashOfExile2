"""Mod book › Manual feed (2.51.0). The user: "take the information from an already expensive tablet, paste it into the
program with the price, and the program learns that as an expensive tablet - manual feed the learning system on top
of the way it already works."

How it learns: the Mod book works out which mods matter from the listings the price checks see (market.Market.stats:
the median price of listings WITH a mod vs. WITHOUT it, per base). A fed item becomes listings at its price - like
a sale (save_sale) - so it joins that same sum. How much it counts is yours to pick (1-10 listings; the Mod book needs
a mod on 8 before it decides). You can also rate its mods High straight away (your own rules always win). Everything
fed is listed, can be forgotten (undone), and exported as CSV. Before / after numbers show exactly what changed."""
import csv
import io
import time
import tkinter as tk
from tkinter import filedialog, ttk

from .config import SETTINGS
from .market import MARKET
from .mods import MIN_WITH, HIGH_LIFT, SCOPED_CATS, norm, rule_key, sid_for_line
from .pricefmt import parse_price
from .style import C, Tooltip


def _st_text(st):
    if not st:
        return "not seen yet"
    lift = "-" if st.get("lift") is None else f"×{st['lift']:.1f}"
    return f"{st['n']} listings, median {st['med']:.2f}d, {lift}" + (" · HIGH" if st.get("tier") == "high" else
                                                                    "" if st.get("decided") else
                                                                    f" · needs {max(0, MIN_WITH - st['n'])} more")


class FeedPage:
    """Mixed into App."""

    def build_feed(self, tab):
        P1, P2 = C["panel"], C["panel2"]
        top = tk.Frame(tab, bg=P1, padx=12, pady=8)
        top.pack(fill="x")
        tk.Label(top, text="Teach the Mod book a price", bg=P1, fg=C["accent"], font=("Segoe UI", 12, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(top, text="Know what an item is worth - an expensive tablet you saw sell, one the trade site hardly "
                           "shows? Ctrl+Alt+C it in game (or paste it), type its price and Feed it. It joins the "
                           "listings the Mod book learns from, like a sale; the numbers below show what changed.",
                 bg=P1, fg=C["muted"], font=("Segoe UI", 9), wraplength=720, justify="left", anchor="w").pack(fill="x")
        body = tk.Frame(tab, bg=P1, padx=12)
        body.pack(fill="both", expand=True)
        left = tk.Frame(body, bg=P2, padx=12, pady=8, highlightthickness=1, highlightbackground=C["line"])
        left.pack(side="left", fill="y", pady=(0, 8))
        tk.Label(left, text="The item", bg=P2, fg=C["text"], anchor="w").pack(fill="x")
        self.fd_text = tk.Text(left, width=44, height=12, bg=C["panel"], fg=C["text"], insertbackground=C["text"],
                               relief="flat", wrap="none", font=("Consolas", 9), highlightthickness=1,
                               highlightbackground=C["line"])
        self.fd_text.pack(fill="both", expand=True, pady=(2, 4))
        self.fd_text.bind("<<Modified>>", self._fd_typed)
        self.fd_text.bind("<Tab>", lambda e: (e.widget.tk_focusNext().focus_set(), "break")[1])
        ttk.Button(left, text="Paste from clipboard", command=self.fd_paste, style="Quiet.TButton").pack(anchor="w")
        g = tk.Frame(left, bg=P2)
        g.pack(fill="x", pady=(8, 0))
        tk.Label(g, text="Price", bg=P2, fg=C["text"]).grid(row=0, column=0, sticky="w", pady=2)
        self.fd_price = tk.StringVar()
        pe = ttk.Entry(g, textvariable=self.fd_price, width=12)
        pe.grid(row=0, column=1, sticky="w", padx=(8, 8))
        Tooltip(pe, "8, 8 div, 35c, 2 ex, 1 div 50 chaos - a bare number is divines")
        self.fd_price_lbl = tk.Label(g, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9))
        self.fd_price_lbl.grid(row=0, column=2, sticky="w")
        self.fd_price.trace_add("write", lambda *a: self._fd_price_show())
        tk.Label(g, text="Counts as", bg=P2, fg=C["text"]).grid(row=1, column=0, sticky="w", pady=2)
        self.fd_copies = tk.StringVar(value=str(SETTINGS.get("feed_copies", 3)))
        sp = ttk.Spinbox(g, from_=1, to=MARKET.FEED_MAX, textvariable=self.fd_copies, width=4)
        sp.grid(row=1, column=1, sticky="w", padx=(8, 8))
        tk.Label(g, text="listings", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).grid(row=1, column=2, sticky="w")
        Tooltip(sp, f"How much it counts. A mod needs {MIN_WITH} listings before the Mod book decides about it; a price "
                    "you trust can count for a few. 1 = like any one listing.")
        tk.Label(g, text="Note", bg=P2, fg=C["text"]).grid(row=2, column=0, sticky="w", pady=2)
        self.fd_note = tk.StringVar()
        ttk.Entry(g, textvariable=self.fd_note, width=26).grid(row=2, column=1, columnspan=2, sticky="w", padx=(8, 0))
        self.fd_rate = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="Also rate the ticked mods High in my Mod book", variable=self.fd_rate).pack(
            anchor="w", pady=(8, 0))
        b = tk.Frame(left, bg=P2)
        b.pack(fill="x", pady=(8, 0))
        self.fd_btn = ttk.Button(b, text="Feed it", style="Primary.TButton", command=self.fd_feed)
        self.fd_btn.pack(side="left")
        ttk.Button(b, text="Clear", style="Quiet.TButton", command=self.fd_clear).pack(side="left", padx=(8, 0))
        self.fd_msg = tk.Label(left, text="", bg=P2, fg=C["muted"], font=("Segoe UI", 9), wraplength=320,
                               justify="left", anchor="w")
        self.fd_msg.pack(fill="x", pady=(8, 0))
        # ---- right: its mods (before / after), then everything fed
        right = tk.Frame(body, bg=P1)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        tk.Label(right, text="Its mods - click ☐ to pick the ones to rate High", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9), anchor="w").pack(fill="x")
        cols = (("rate", "High", 50, "center"), ("mod", "Mod", 300, "w"), ("before", "Mod book now", 230, "w"),
                ("after", "After feeding", 230, "w"))
        self.fd_tv = ttk.Treeview(right, columns=[c[0] for c in cols], show="headings", height=7, selectmode="browse")
        for cid, title, w, a in cols:
            self.fd_tv.heading(cid, text=title)
            self.fd_tv.column(cid, width=w, anchor=a, stretch=cid in ("mod", "before", "after"))
        self.fd_tv.pack(fill="x")
        self.fd_tv.tag_configure("unknown", foreground=C["muted"])
        self.fd_tv.tag_configure("up", foreground=C["green"])
        self.fd_tv.bind("<Button-1>", self._fd_click)
        h = tk.Frame(right, bg=P1)
        h.pack(fill="x", pady=(12, 2))
        tk.Label(h, text="Fed so far (this league)", bg=P1, fg=C["accent"], font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(h, text="Export CSV", command=self.fd_export, style="Quiet.TButton").pack(side="right")
        ttk.Button(h, text="Forget selected", command=self.fd_forget, style="Danger.TButton").pack(side="right",
                                                                                                padx=(0, 8))
        fcols = (("when", "When", 110, "w"), ("item", "Item", 200, "w"), ("price", "Price", 80, "e"),
                 ("copies", "Counts", 60, "center"), ("mods", "Mods", 340, "w"))
        self.fd_list = ttk.Treeview(right, columns=[c[0] for c in fcols], show="headings", height=8)
        for cid, title, w, a in fcols:
            self.fd_list.heading(cid, text=title)
            self.fd_list.column(cid, width=w, anchor=a, stretch=cid == "mods")
        self.fd_list.pack(fill="both", expand=True)
        self.fd_list.bind("<Delete>", lambda e: self.fd_forget())
        self.fd_item, self.fd_rows, self._fd_job = None, [], None
        self.fd_fill_list()

    # ---------------------------------------------------------------- reading the item
    def fd_capturing(self):
        """Ctrl+Alt+C goes into the Manual feed box while its tab is showing."""
        try:
            return (hasattr(self, "fd_text") and self.fd_text.winfo_viewable()
                    and self.mb_nb.titles[self.mb_nb.cur] == "Manual feed")
        except Exception:
            return False

    def fd_take_clip(self, text):
        self.fd_text.delete("1.0", "end")
        self.fd_text.insert("1.0", text.strip())
        self.fd_read()
        self._say("Manual feed: item read - type its price and press Feed it.", 5)

    def fd_paste(self):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            text = ""
        self.fd_take_clip(text)

    def _fd_typed(self, _e=None):
        if not self.fd_text.edit_modified():
            return
        self.fd_text.edit_modified(False)
        if self._fd_job:
            self.root.after_cancel(self._fd_job)
        self._fd_job = self.root.after(300, self.fd_read)

    def _fd_price_show(self):
        t = self.fd_price.get().strip()
        d = parse_price(t) if t else None
        self.fd_price_lbl.config(text="" if not t else f"= {d:.2f} div" if d is not None else "can't read that",
                                 fg=C["muted"] if d is not None or not t else C["red"])

    def fd_read(self):
        """The text -> the item and its mods, each with what the Mod book thinks of it now."""
        self._fd_job = None
        text = self.fd_text.get("1.0", "end-1c")
        item = self.read_any(text) if text.strip() else None
        self.fd_item = item
        tv = self.fd_tv
        tv.delete(*tv.get_children())
        self.fd_rows = []
        if not item:
            self.fd_msg.config(text="" if not text.strip() else "That isn't an item the price checker reads "
                                                                 "(tablets, jewels, waystones, relics, gear).",
                               fg=C["red"])
            return None
        sids = []
        for m in item["mods"]:
            sid = m.get("sid") or sid_for_line(norm(m["text"]))
            sids.append(sid)
        now = MARKET.standing(item["base"], [s for s in sids if s])
        for i, (m, sid) in enumerate(zip(item["mods"], sids)):
            row = {"mod": m, "sid": sid, "rate": False, "before": now.get(sid) if sid else None}
            self.fd_rows.append(row)
            tv.insert("", "end", iid=str(i), values=("☐", m.get("shown") or m["text"],
                                                     _st_text(row["before"]) if sid else "the trade site doesn't know it",
                                                     ""), tags=() if sid else ("unknown",))
        known = sum(1 for s in sids if s)
        self.fd_msg.config(text=f"{item['name']} ({item['base']}): {len(sids)} mods, {known} the Mod book can learn.",
                           fg=C["muted"])
        return item

    def _fd_click(self, e):
        iid, col = self.fd_tv.identify_row(e.y), self.fd_tv.identify_column(e.x)
        if not iid or col != "#1":
            return
        r = self.fd_rows[int(iid)]
        r["rate"] = not r["rate"]
        self.fd_tv.set(iid, "rate", "☑" if r["rate"] else "☐")

    # ---------------------------------------------------------------- feeding
    def fd_feed(self):
        item = self.fd_item or self.fd_read()
        if not item:
            self.fd_msg.config(text="Paste or Ctrl+Alt+C an item first.", fg=C["red"])
            return None
        txt = self.fd_price.get().strip()
        div = parse_price(txt)
        if not div:
            self.fd_msg.config(text="Type its price (8, 8 div, 35c, 2 ex ...).", fg=C["red"])
            return None
        try:
            copies = max(1, min(MARKET.FEED_MAX, int(self.fd_copies.get())))
        except ValueError:
            copies = 3
        SETTINGS["feed_copies"] = copies
        sig = MARKET.feed(item, div, copies, txt, self.fd_note.get().strip())
        if not sig:
            self.fd_msg.config(text=f"Couldn't save it: {MARKET.last_error or MARKET.db_error}", fg=C["red"])
            return None
        rated = []
        if self.fd_rate.get():
            from .mods import mod_cat
            cat = "waystone" if item.get("waystone") else ("relic" if "relic" in (item.get("class") or "").lower()
                                                           else None)
            for r in self.fd_rows:
                if r["rate"]:
                    k = norm(r["mod"]["text"])
                    c = cat or mod_cat(k, item["base"])
                    rated.append(rule_key(c, k) if c in SCOPED_CATS else k)
            if rated:
                self.set_rules(rated, "high")
        after = MARKET.standing(item["base"], [r["sid"] for r in self.fd_rows if r["sid"]])
        up = 0
        for i, r in enumerate(self.fd_rows):
            if not r["sid"]:
                continue
            a = after.get(r["sid"])
            became_high = (a or {}).get("tier") == "high" and (r["before"] or {}).get("tier") != "high"
            up += became_high
            self.fd_tv.set(str(i), "after", _st_text(a) + ("  ▲ now High" if became_high else ""))
            if became_high:
                self.fd_tv.item(str(i), tags=("up",))
        self.fd_msg.config(text=f"Fed: {item['name']} at {div:.2f} div, counting as {copies} listing(s)."
                                + (f" {up} mod(s) became High." if up else "")
                                + (f" Rated High by you: {len(rated)}." if rated else "")
                                + ("" if up or rated else f" A mod becomes High with {MIN_WITH}+ listings, ×{HIGH_LIFT:g} "
                                                          "the price of the ones without it, and your valuable-mod "
                                                          "amount - or rate it High yourself."),
                           fg=C["green"])
        self.fd_fill_list()
        try:
            self.refresh_memory(True)
        except Exception:
            pass
        return sig

    def fd_clear(self):
        self.fd_text.delete("1.0", "end")
        self.fd_price.set("")
        self.fd_note.set("")
        self.fd_read()

    def fd_fill_list(self):
        tv = self.fd_list
        tv.delete(*tv.get_children())
        for f in MARKET.fed():
            tv.insert("", "end", iid=f["sig"], values=(time.strftime("%b %d %H:%M", time.localtime(f["ts"])), f["name"],
                                                       f"{f['div']:.2f}d", f["copies"], " · ".join(f["lines"])[:200]))

    def fd_forget(self):
        sel = self.fd_list.selection()
        for sig in sel:
            MARKET.unfeed(sig)
        if sel:
            self.fd_fill_list()
            self.fd_msg.config(text=f"Forgot {len(sel)} - the Mod book learned again without them.", fg=C["muted"])

    def fd_export(self, path=None):
        path = path or filedialog.asksaveasfilename(parent=self.dlg_parent(), defaultextension=".csv",
                                                    initialfile="manual_feed.csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return None
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(("when", "base", "item", "price_div", "price_typed", "counts_as", "note", "mods"))
        for f in MARKET.fed():
            w.writerow((time.strftime("%Y-%m-%d %H:%M", time.localtime(f["ts"])), f["base"], f["name"],
                        f"{f['div']:.4f}", f["price_txt"], f["copies"], f["note"] or "", "; ".join(f["lines"])))
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(buf.getvalue())
        self._say(f"Saved {path}", 6)
        return path
