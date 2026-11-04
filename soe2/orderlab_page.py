"""2.88.0: Under the hood ↳ Listing order lab (admins only) - see orderlab.py for what it's for and how a round goes."""
import threading
import time
import tkinter as tk
from tkinter import ttk

from . import orderlab as OL
from .style import C


class OrderLabPage:
    def build_orderlab(self, body):
        P1 = C["panel"]
        self.ol = OL.Lab()
        self.ol_round, self.ol_walking, self.ol_last = None, False, []
        tk.Label(body, text="For working out the trade site's listing order. 1) Paste the trade-site link of your public "
                            "tab and press Read. 2) Press Start walking, then Ctrl+Alt+C each item in game in the order "
                            "you go through the tab. 3) The table and the numbers below show which order the site's "
                            "list follows. Do a few tabs; Export CSV keeps every round. Most telling: a tab of 1x1 items "
                            "(no big items to blur the place), walked down each column from the top, then the next "
                            "column to the right.",
                 bg=P1, fg=C["muted"], anchor="w", justify="left", wraplength=1100, padx=8, pady=8).pack(fill="x")
        bar = tk.Frame(body, bg=P1, padx=8, pady=4)
        bar.pack(fill="x")
        self.ol_link = tk.StringVar()
        ttk.Entry(bar, textvariable=self.ol_link).pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text="Read", style="Primary.TButton", command=self.ol_read).pack(side="left", padx=(8, 0))
        self.ol_walk_btn = ttk.Button(bar, text="Start walking", command=self.ol_walk_toggle, state="disabled")
        self.ol_walk_btn.pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="Undo last", style="Quiet.TButton", command=self.ol_undo).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="Export CSV", style="Quiet.TButton", command=self.ol_export).pack(side="left", padx=(8, 0))
        self.ol_msg = tk.Label(body, text="", bg=P1, fg=C["muted"], anchor="w", padx=8)
        self.ol_msg.pack(fill="x")
        cols = (("walk", "Walk", 50), ("site", "Site #", 55), ("newest", "Newest #", 70), ("place", "Place", 70),
                ("size", "Size", 50),                                                  # 2.92.1
                ("indexed", "Indexed", 150), ("name", "Item", 260), ("price", "Price", 90), ("id", "Listing id", 160))
        tv = ttk.Treeview(body, columns=[c[0] for c in cols], show="headings", selectmode="browse", height=16)
        for cid, t, w in cols:
            tv.heading(cid, text=t, command=lambda c=cid: self.ol_fill(sort=c))
            tv.column(cid, width=w, anchor="w" if cid in ("name", "indexed", "id") else "center", stretch=cid == "name")
        tv.tag_configure("walked", foreground=C["green"])
        tv.tag_configure("last", foreground="#ffd25a")
        tv.pack(fill="both", expand=True, padx=8)
        self.ol_tv = tv
        self.ol_out = tk.Label(body, text="", bg=P1, fg=C["text"], anchor="w", justify="left", font=("Consolas", 9),
                               padx=8, pady=8)
        self.ol_out.pack(fill="x")
        self.ol_sort = "site"

    # ---------------------------------------------------------------- read
    def _ol_bg(self, work, done):
        threading.Thread(target=lambda: self.ui_q.put(("ol_done", done, work())), daemon=True).start()

    def ev_ol_done(self, done, res):
        done(res)

    def ol_read(self, link=None, call=None):
        from . import favorites as FV
        link = (link or self.ol_link.get()).strip()
        if not FV.is_link(link):
            return self.ol_msg.config(text="Paste a trade-site search link (of your public tab).", fg=C["red"])
        self.ol_msg.config(text="Reading the listings…", fg=C["muted"])

        def work():
            from urllib.parse import quote
            from .config import BASE
            from .net import call as net_call
            c = call or net_call
            info, err = FV.read_link(link, call=c, base=BASE)
            if err:
                return None, err
            league = info["league"]
            res = c("POST", f"{BASE}/search/poe2/{quote(league)}", json={"query": info["query"],
                                                                         "sort": info.get("sort") or {"price": "asc"}})
            ids = list(res.get("result") or [])[:100]
            newest = c("POST", f"{BASE}/search/poe2/{quote(league)}", json={"query": info["query"],
                                                                            "sort": {"indexed": "desc"}})
            listings = []
            for i in range(0, len(ids), 10):
                got = c("GET", f"{BASE}/fetch/{','.join(ids[i:i + 10])}", params={"query": res.get("id")})
                for e in got.get("result") or []:
                    if e:
                        listings.append(OL.entry(e, len(listings) + 1))
            return {"listings": listings, "newest": list(newest.get("result") or [])[:100],
                    "total": res.get("total", len(ids))}, None

        def safe():
            try:
                return work()
            except Exception as ex:
                return None, f"Couldn't read it ({str(ex)[:120]})"

        def done(res):
            data, err = res
            if err:
                return self.ol_msg.config(text=err, fg=C["red"])
            self.ol_round = self.ol.new_round(link, data["listings"], data["newest"])
            n = len(data["listings"])
            self.ol_msg.config(text=f"Read {n} listing{'s' if n != 1 else ''}" + (f" (the search has {data['total']}; the "
                               "site gives the first 100)" if data["total"] > n else "") + ". Press Start walking.",
                               fg=C["muted"])
            self.ol_walk_btn.config(state="normal")
            self.ol_fill()
        self._ol_bg(safe, done)

    # ---------------------------------------------------------------- walk
    def ol_walk_toggle(self):
        self.ol_walking = not self.ol_walking
        self.ol_walk_btn.config(text="Stop walking" if self.ol_walking else "Start walking")
        self.ol_msg.config(text="Walking: Ctrl+Alt+C each item in game, in your order (copies don't go to Bulk Pricing "
                                "meanwhile)." if self.ol_walking else "Stopped.", fg=C["muted"])

    def ol_wants(self, text):
        return bool(self.ol_walking and self.ol_round and str(text).lstrip().startswith("Item Class:"))

    def ol_take(self, text):
        L = OL.match(self.ol_round["listings"], text)
        if L is None:
            OL.log_unmatched(text)                                   # 2.92.1: on this PC only, to fix the matching
            self.ol_msg.config(text="That copy didn't match a listing that's left (already walked, or not in this "
                                    "search).", fg=C["red"])
            return None
        L["walk"] = 1 + max([x["walk"] for x in self.ol_round["listings"] if x.get("walk") is not None] or [0])
        self.ol_last.append(L)
        self.ol.save()
        n = sum(1 for x in self.ol_round["listings"] if x.get("walk") is not None)
        self.ol_msg.config(text=f"Walked {n} of {len(self.ol_round['listings'])}: {L['name']} (site #{L['rank']}).",
                           fg=C["green"])
        self.ol_fill()
        return L

    def ol_undo(self):
        if self.ol_last:
            L = self.ol_last.pop()
            L["walk"] = None
            self.ol.save()
            self.ol_fill()

    # ---------------------------------------------------------------- show
    def ol_fill(self, sort=None):
        if sort:
            self.ol_sort = sort
        tv = self.ol_tv
        tv.delete(*tv.get_children())
        r = self.ol_round
        if not r:
            return
        npos = {i: k + 1 for k, i in enumerate(r.get("newest") or [])}
        rows = []
        for L in r["listings"]:
            place = f"C{L['x'] + 1} R{L['y'] + 1}" if isinstance(L.get("x"), int) and isinstance(L.get("y"), int) else "?"
            rows.append((L, {"walk": L.get("walk") or 10 ** 6, "site": L["rank"], "newest": npos.get(L["id"], 10 ** 6),
                             "place": (L.get("x") or 0, L.get("y") or 0), "size": (L.get("w") or 0) * (L.get("h") or 0),
                             "indexed": str(L.get("indexed") or ""),
                             "name": L["name"].lower(), "price": L.get("price") or "", "id": str(L["id"])}, place))
        rows.sort(key=lambda t: t[1][self.ol_sort])
        last = self.ol_last[-1] if self.ol_last else None
        for L, _k, place in rows:
            tags = ("last",) if L is last else ("walked",) if L.get("walk") is not None else ()
            size = f"{L['w']}x{L['h']}" if L.get("w") and L.get("h") else "?"
            tv.insert("", "end", values=(L.get("walk") or "", L["rank"], npos.get(L["id"], ""), place, size,
                                         L.get("indexed") or "", L["name"] + ("  (corrupted)" if L.get("corrupted") else ""),
                                         L.get("price") or "", L["id"]), tags=tags)
        res = OL.compare(r["listings"], r.get("newest"))
        fmt = lambda v: "   -  " if v is None else f"{v:+.2f}"  # noqa: E731
        lines = ["order                    vs your walk   vs the site's order   (1 = same order, 0 = unrelated)"]
        lines += [f"{n:<24} {fmt(w):>12}   {fmt(s):>16}" for n, w, s in res]
        self.ol_out.config(text="\n".join(lines))

    def ol_export(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="listing_order.csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            OL.to_csv(self.ol.rounds, path)
            self._say(f"Saved {len(self.ol.rounds)} round(s) to {path}.", 8)
