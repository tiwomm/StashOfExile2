"""2.84.0: Price Checks ↳ Favorites (feedback: "a favorites (bookmark) tracker that you can paste a trade link into
... loads an item view similar to the new price checks section + the trade site options for that item ... 'Add to
favorites' next to 'Open on trade site' ... reorganize, give a name to it, edit/delete/etc, fully context menu aware").

Left: your favorites in groups (drag to reorder or move between groups; right-click for everything; F2 renames,
Alt+↑/↓ moves, Delete removes, Ctrl+Z undoes). Middle: the item card with every filter (an item from Price Checks) or
the pasted search's filters (a trade link). Right: the trade site's listings, as on Price Checks.
GGG ToS: trade-site searches within its limits; nothing is bought, listed or whispered."""
import copy
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import simpledialog, ttk
from urllib.parse import quote

from . import buglog
from . import favorites as FV
from .config import SETTINGS
from .style import over_app
from .style import C

KEY = "favorites"
GROUP_PRE = "grp:"
FILTER_NAMES = {"type_filters": "Type", "equipment_filters": "Equipment", "req_filters": "Requirements",
                "misc_filters": "Miscellaneous", "trade_filters": "Trade", "map_filters": "Waystone",
                "socket_filters": "Sockets", "weapon_filters": "Weapon", "armour_filters": "Armour"}
GROUP_TYPES = {"and": "All of these", "not": "None of these", "if": "If present", "count": "At least {n} of these",
               "weight": "Weighted sum ≥ {n}", "weight2": "Weighted sum ≥ {n}"}


def _ago(ts):
    if not ts:
        return ""
    s = max(0, time.time() - ts)
    return "just now" if s < 60 else f"{int(s // 60)}m ago" if s < 3600 else f"{int(s // 3600)}h ago" \
        if s < 86400 else f"{int(s // 86400)}d ago"


def _pretty(key):
    return key.replace("_", " ").strip().capitalize()


class FavoritesPage:
    # ---------------------------------------------------------------- the page
    def favs(self):
        if getattr(self, "fav_store", None) is None:
            self.fav_store = FV.FavStore()
        return self.fav_store

    def build_favorites(self, body):
        from .pricecheck_page import PCView
        P1, P2 = C["panel"], C["panel2"]
        self.fav_sel, self.fav_res, self.fav_busy = None, {}, set()
        bar = tk.Frame(body, bg=P1, padx=8, pady=8)
        bar.pack(fill="x")
        self.fav_link_var = tk.StringVar()
        tk.Label(bar, text="Trade link", bg=P1, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(4, 8))
        ent = ttk.Entry(bar, textvariable=self.fav_link_var)
        ent.pack(side="left", fill="x", expand=True)
        self._fav_hint(ent)                               # P2 (2.104.0): a hint in the empty box
        ent.bind("<Return>", lambda e: self.fav_add_link())
        self.fav_link_entry = ent
        ttk.Button(bar, text="Add trade link", style="Primary.TButton", command=self.fav_add_link).pack(
            side="left", padx=(8, 0))
        ttk.Button(bar, text="New group", command=self.fav_new_group).pack(side="left", padx=(8, 0))
        self.undo_button(bar, KEY, side="left", padx=(8, 0))     # P2: only while there's something to undo
        self.fav_msg = tk.Label(body, text="Right-click a favorite for everything you can do; drag to reorder.",
                                bg=P1, fg=C["muted"], anchor="w", justify="left", padx=12)
        self.fav_msg.pack(fill="x")
        wrap = tk.Frame(body, bg=P2)
        self.limit_banner(body, wrap)                     # 2.103.3 (feedback): the "Staying under the limits" line
        wrap.pack(fill="both", expand=True, pady=(8, 0))
        # ---- your favorites
        lf = tk.Frame(wrap, bg=P1, width=300)             # P2: narrower list, wider card
        lf.pack(side="left", fill="y")
        lf.pack_propagate(False)
        tv = ttk.Treeview(lf, columns=("price", "when"), show="tree headings", selectmode="extended")
        tv.heading("#0", text="Name")
        tv.heading("price", text="Price")
        tv.heading("when", text="Checked")
        tv.column("#0", width=110, minwidth=80, stretch=True)
        tv.column("price", width=72, anchor="e", stretch=False)
        tv.column("when", width=78, anchor="e", stretch=False)
        sb = ttk.Scrollbar(lf, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tv.pack(fill="both", expand=True)
        tv.tag_configure("group", font=("Segoe UI", 9, "bold"), foreground=C["accent"])
        self.fav_tv = tv
        self.list_register(KEY, tv, delete=self.fav_delete)
        tv.menu_actions = self.fav_menu_actions
        tv.bind("<<TreeviewSelect>>", lambda e: self.fav_selected())
        tv.bind("<Double-1>", self.fav_double)
        tv.bind("<Return>", lambda e: (self.fav_search(), "break")[-1])
        tv.bind("<F2>", lambda e: (self.fav_rename(), "break")[-1])
        tv.bind("<Alt-Up>", lambda e: (self.fav_step(-1), "break")[-1])
        tv.bind("<Alt-Down>", lambda e: (self.fav_step(1), "break")[-1])
        tv.bind("<Control-v>", lambda e: (self.fav_paste(), "break")[-1])
        tv.bind("<ButtonPress-1>", self.fav_drag_start, add="+")
        tv.bind("<B1-Motion>", self.fav_drag_move, add="+")
        tv.bind("<ButtonRelease-1>", self.fav_drag_end, add="+")
        tv.bind("<<TreeviewOpen>>", lambda e: self.fav_group_open(True))
        tv.bind("<<TreeviewClose>>", lambda e: self.fav_group_open(False))
        from .chrome import EmptyState                    # 2.120.0: one empty look everywhere
        self.fav_empty = EmptyState(lf, "★", "No favorites yet\nPress ☆ Add to favorites on a price check, or paste "
                                              "a trade-site link above.",
                                    button=("Open Price Checks", lambda: self.shell.open("pricecheck")))
        # ---- the card
        mid = tk.Frame(wrap, bg=P2, width=480)
        mid.pack(side="left", fill="y")
        mid.pack_propagate(False)
        lcanvas, left = self._pc_scroller(mid, padx=12)
        # ---- the listings
        right = tk.Frame(wrap, bg=P1)
        right.pack(side="left", fill="both", expand=True)
        head = tk.Frame(right, bg=P1, padx=12, pady=8)
        head.pack(fill="x")
        count = tk.Label(head, text="", bg=P1, fg=C["text"], font=("Segoe UI", 10, "bold"))
        count.pack(side="left")
        ob = ttk.Button(head, text="Trade Site", command=self.fav_open_trade, state="disabled")
        rcanvas, lst = self._pc_scroller(right, padx=12, bg_key="panel")
        self.favv = PCView(left, lcanvas, lst, rcanvas, count, ob)
        self.favv.rid = None
        self.favv.redraw = lambda: self.fav_show()
        self.favv.recard = lambda: self.fav_show(card_only=True)
        self.favv.search_btn = None
        self.favv.head_open = ob                            # P2: the card's own button replaces it while shown
        self.pcv_fit(self.favv, wrap, mid, lo=460, share=0.42)   # 2.97.0: scale to fit; P2: a wider card
        self.fav_fill()
        self.fav_show()

    # ---------------------------------------------------------------- the list
    def fav_fill(self, select=None):
        tv = getattr(self, "fav_tv", None)
        if tv is None:
            return
        st = self.favs()
        keep = list(select) if select is not None else list(tv.selection())
        want = [("", f["id"]) for f in st.in_group("")] + [x for g in st.groups for x in
                [("", GROUP_PRE + g["id"])] + [(GROUP_PRE + g["id"], f["id"]) for f in st.in_group(g["id"])]]
        have = [x for c in tv.get_children("") for x in [("", c)] + [(c, i) for i in tv.get_children(c)]]
        if want == have:
            self._fav_empty_show(st)
            self._fav_fill_same(st)                   # 2.103.4 (feedback: Favorites still flickered): same rows -
            if select is not None:                    # their words change in place, nothing is built again
                keep = [i for i in keep if tv.exists(i)]
                if keep and list(tv.selection()) != keep:
                    tv.selection_set(keep)
                    tv.see(keep[0])
            return
        tv.delete(*tv.get_children())
        for f in st.in_group(""):
            self._fav_row("", f)
        for g in st.groups:
            n = len(st.in_group(g["id"]))
            tv.insert("", "end", iid=GROUP_PRE + g["id"], text=f"{g['name']}  ({n})", open=g.get("open", True),
                      values=("", ""), tags=("group",))
            for f in st.in_group(g["id"]):
                self._fav_row(GROUP_PRE + g["id"], f)
        keep = [i for i in keep if tv.exists(i)]
        if keep:
            tv.selection_set(keep)
            tv.see(keep[0])
        self._fav_empty_show(st)

    def _fav_empty_show(self, st):
        if st.items or st.groups:
            self.fav_empty.place_forget()
        else:
            self.fav_empty.place(relx=0.5, rely=0.3, anchor="center")

    def _fav_hint(self, ent):
        """P2: "Paste a trade-site search link here" in grey while the box is empty and not being typed in."""
        hint = "Paste a trade-site search link here"
        lab = tk.Label(ent, text=hint, bg=C["odd"], fg=C["muted"],
                       font=("Segoe UI", 9), anchor="w", cursor="xterm")

        def show(_e=None):
            if not self.fav_link_var.get() and self.root.focus_get() is not ent:
                lab.place(x=6, rely=0.5, anchor="w")
            else:
                lab.place_forget()
        lab.bind("<Button-1>", lambda e: (lab.place_forget(), ent.focus_set()))
        ent.bind("<FocusIn>", show, add="+")
        ent.bind("<FocusOut>", show, add="+")
        self.fav_link_var.trace_add("write", lambda *a: show())
        self.root.after(50, show)

    def _fav_fill_same(self, st):
        tv = self.fav_tv
        for f in st.items:
            last = f.get("last") or {}
            text = ("🔗 " if f.get("kind") == "link" else "◆ ") + f["name"]
            vals = (last.get("price") or "", _ago(last.get("ts")))
            if tv.item(f["id"], "text") != text or tuple(str(x) for x in tv.item(f["id"], "values")) != vals:
                tv.item(f["id"], text=text, values=vals)
        for g in st.groups:
            text = f"{g['name']}  ({len(st.in_group(g['id']))})"
            if tv.item(GROUP_PRE + g["id"], "text") != text:
                tv.item(GROUP_PRE + g["id"], text=text)
            if bool(tv.item(GROUP_PRE + g["id"], "open")) != bool(g.get("open", True)):
                tv.item(GROUP_PRE + g["id"], open=g.get("open", True))

    def _fav_row(self, parent, f):
        last = f.get("last") or {}
        icon = "🔗 " if f.get("kind") == "link" else "◆ "
        self.fav_tv.insert(parent, "end", iid=f["id"], text=icon + f["name"],
                           values=(last.get("price") or "", _ago(last.get("ts"))))

    def fav_changed(self, select=None):
        self.favs().save()
        self.fav_fill(select)

    def _fav_ids(self, sel=None):
        sel = self.fav_tv.selection() if sel is None else sel
        return [i for i in sel if not str(i).startswith(GROUP_PRE)]

    def _fav_groups_sel(self, sel=None):
        sel = self.fav_tv.selection() if sel is None else sel
        return [i[len(GROUP_PRE):] for i in sel if str(i).startswith(GROUP_PRE)]

    def fav_say(self, text, col=None):
        if hasattr(self, "fav_msg"):
            self.fav_msg.config(text=text, fg=col or C["muted"])

    def fav_menu_actions(self, sel):
        ids, gids = self._fav_ids(sel), self._fav_groups_sel(sel)
        one = len(ids) == 1 and not gids
        acts = []
        if one:
            acts += [("Search now", self.fav_search, True, "Enter"),
                     ("Trade Site", self.fav_open_trade, True),
                     ("Copy trade link", self.fav_copy_link, True), None,
                     ("Rename…", self.fav_rename, True, "F2"),
                     ("Edit…", self.fav_edit, True),
                     ("Duplicate", self.fav_duplicate, True), None,
                     ("Move up", lambda: self.fav_step(-1), True, "Alt+↑"),
                     ("Move down", lambda: self.fav_step(1), True, "Alt+↓")]
        if ids:
            acts += [(f"Move {len(ids)} to group…" if len(ids) > 1 else "Move to group…", self.fav_move_to, True)]
        if len(gids) == 1 and not ids:
            acts += [("Rename group…", self.fav_rename, True, "F2"),
                     ("Move group up", lambda: self.fav_step(-1), True, "Alt+↑"),
                     ("Move group down", lambda: self.fav_step(1), True, "Alt+↓"),
                     ("Search every favorite in it", lambda: self.fav_search_group(gids[0]), True)]
        acts += [None, ("New group…", self.fav_new_group, True), ("Paste a trade link", self.fav_paste, True, "Ctrl+V")]
        return acts

    # ---------------------------------------------------------------- adding
    def pc_add_fav(self):
        """☆ Add to favorites on Price Checks: this item with your filters."""
        rec = self.records.get(getattr(self, "pc_rid", None))
        if not rec:
            return
        st = self.favs()
        if rec.get("fav") and st.get(rec["fav"]):
            self.shell.open(KEY)
            return self.fav_pick(rec["fav"])
        f = st.add_item(rec)
        rec["fav"] = f["id"]
        self.fav_store_last(f, rec)
        self.fav_changed([f["id"]])
        self.pc_fav_state(rec)
        try:
            self.app_toast(f"\"{f['name']}\" is in Price Checks ↳ Favorites.", title="Added to favorites",
                           kind="success", actions=(("Open", lambda: (self.shell.open(KEY), self.fav_pick(f["id"]))),
                                                    ("Rename", lambda: (self.shell.open(KEY), self.fav_pick(f["id"]),
                                                                        self.fav_rename()))))
        except Exception:
            buglog.caught()

    def pc_fav_state(self, rec):
        b = getattr(self, "pc_fav_btn", None)
        if b is None:
            return
        on = bool(rec and rec.get("fav") and self.favs().get(rec["fav"]))
        b.config(text="★ In favorites" if on else "☆ Add to favorites", state="normal" if rec else "disabled")

    def fav_paste(self):
        try:
            t = self.root.clipboard_get()
        except tk.TclError:
            t = ""
        if not FV.is_link(t):
            return self.fav_say("The clipboard has no trade-site link. Copy the address of a trade search first.",
                                C["red"])
        self.fav_link_var.set(t.strip())
        self.fav_add_link()

    def fav_add_link(self, url=None, group=None):
        url = (url or self.fav_link_var.get()).strip()
        if not FV.is_link(url):
            return self.fav_say("That doesn't look like a Path of Exile 2 trade-site search link "
                                "(https://www.pathofexile.com/trade2/search/poe2/...).", C["red"])
        if group is None:
            gids = self._fav_groups_sel()
            f0 = self.favs().get((self._fav_ids() or [None])[0])
            group = gids[0] if gids else (f0.get("group", "") if f0 else "")
        self.fav_say("Reading the link…")

        def work():
            info, err = FV.read_link(url)
            self.ui_q.put(("fav_link_read", url, info, err, group))
        threading.Thread(target=work, daemon=True).start()

    def ev_fav_link_read(self, url, info, err, group):
        if err:
            return self.fav_say(err, C["red"])
        name = simpledialog.askstring("Name this bookmark", "Name:", initialvalue=FV.link_name(info["query"]),
                                      parent=self.root)     # 2.103.3 (feedback): a name when it's added
        if name is None:
            return self.fav_say("Not added.")
        f = self.favs().add_link(url, info, name=name.strip() or None, group=group or "")
        self.fav_link_var.set("")
        self.fav_changed([f["id"]])
        self.fav_say(f"Added \"{f['name']}\".", C["green"])
        self.fav_pick(f["id"])

    def fav_new_group(self):
        name = simpledialog.askstring("New group", "Name of the group:", parent=self.root)
        if not name or not name.strip():
            return
        g = self.favs().add_group(name.strip())
        ids = self._fav_ids()
        if ids:                                           # the selected favorites go into it
            self.favs().move(ids, g["id"])
        self.fav_changed([GROUP_PRE + g["id"]])

    # ---------------------------------------------------------------- organizing
    def fav_rename(self):
        ids, gids = self._fav_ids(), self._fav_groups_sel()
        st = self.favs()
        if len(ids) == 1:
            f = st.get(ids[0])
            name = simpledialog.askstring("Rename favorite", "Name:", initialvalue=f["name"], parent=self.root)
            if name and name.strip():
                f["name"] = name.strip()
                self.fav_changed()
                self.fav_show()
        elif len(gids) == 1:
            g = st.group(gids[0])
            name = simpledialog.askstring("Rename group", "Name:", initialvalue=g["name"], parent=self.root)
            if name and name.strip():
                g["name"] = name.strip()
                self.fav_changed()

    def fav_step(self, d):
        ids, gids, st = self._fav_ids(), self._fav_groups_sel(), self.favs()
        if len(ids) == 1 and st.step(ids[0], d):
            self.fav_changed()
        elif len(gids) == 1 and not ids and st.step_group(gids[0], d):
            self.fav_changed()

    def fav_duplicate(self):
        ids = self._fav_ids()
        if len(ids) == 1:
            c = self.favs().duplicate(ids[0])
            if c:
                self.fav_changed([c["id"]])

    def fav_group_choice(self, title, current=""):
        """A small window: pick a group (or none, or a new one) -> group id, "" or None (cancelled)."""
        st = self.favs()
        names = ["(no group)"] + [g["name"] for g in st.groups] + ["New group…"]
        dlg = tk.Toplevel(self.root)
        over_app(dlg, self.dlg_parent())               # 2.114.3: over the app, on its monitor
        dlg.title(title)
        dlg.configure(bg=C["panel2"], padx=16, pady=12)
        dlg.transient(self.root)
        tk.Label(dlg, text="Group:", bg=C["panel2"], fg=C["text"]).pack(anchor="w")
        cur = st.group(current)
        var = tk.StringVar(value=cur["name"] if cur else names[0])
        cb = ttk.Combobox(dlg, textvariable=var, values=names, state="readonly", width=32)
        cb.pack(fill="x", pady=(4, 8))
        out = {"v": None}

        def ok():
            out["v"] = var.get()
            dlg.destroy()
        row = tk.Frame(dlg, bg=C["panel2"])
        row.pack(fill="x")
        ttk.Button(row, text="OK", style="Primary.TButton", command=ok).pack(side="right")
        ttk.Button(row, text="Cancel", command=dlg.destroy).pack(side="right", padx=(0, 8))
        dlg.bind("<Return>", lambda e: ok())
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        cb.focus_set()
        try:
            dlg.grab_set()
        except tk.TclError:
            pass
        self.root.wait_window(dlg)
        v = out["v"]
        if v is None:
            return None
        if v == "(no group)":
            return ""
        if v == "New group…":
            name = simpledialog.askstring("New group", "Name of the group:", parent=self.root)
            return st.add_group(name.strip())["id"] if name and name.strip() else None
        return next((g["id"] for g in st.groups if g["name"] == v), "")

    def fav_move_to(self):
        ids = self._fav_ids()
        if not ids:
            return
        cur = self.favs().get(ids[0]).get("group", "")
        gid = self.fav_group_choice("Move to group", cur)
        if gid is None:
            return
        self.favs().move(ids, gid)
        self.fav_changed(ids)

    def fav_group_open(self, on):
        f = self.fav_tv.focus()
        if str(f).startswith(GROUP_PRE):
            g = self.favs().group(f[len(GROUP_PRE):])
            if g:
                g["open"] = on
                self.favs().save()

    def fav_delete(self, rows):
        st = self.favs()
        ids, gids = self._fav_ids(rows), self._fav_groups_sel(rows)
        undo = []
        names = [st.get(i)["name"] for i in ids if st.get(i)]
        if ids:
            _gone, restore = st.remove(ids)
            undo.append(restore)
            for rid, rec in list(self.records.items()):        # their open cards go too
                if rec.get("src") == "fav" and rec.get("fav") in ids:
                    self.records.pop(rid, None)
        for g in gids:
            r = st.remove_group(g)
            if r:
                undo.append(r)
        if not undo:
            return
        label = (f"\"{names[0]}\"" if len(names) == 1 and not gids else
                 f"{len(ids)} favorite{'s' if len(ids) != 1 else ''}" + (f" and {len(gids)} group"
                                                                          f"{'s' if len(gids) != 1 else ''}" if gids else ""))

        def restore_all():
            for r in reversed(undo):
                r()
            self.fav_changed()
        self.push_undo(KEY, label, restore_all)
        if self.fav_sel in ids:
            self.fav_sel = None
        self.fav_changed([])
        self.fav_show()
        self.fav_say(f"Removed {label}" + (" (their favorites stay, ungrouped)" if gids else "") +
                     ". Ctrl+Z puts it back.")

    # ---- drag and drop
    def fav_drag_start(self, e):
        self._fav_drag = {"row": self.fav_tv.identify_row(e.y), "y": e.y, "on": False}

    def fav_drag_move(self, e):
        d = getattr(self, "_fav_drag", None)
        if d and d["row"] and abs(e.y - d["y"]) > 6:
            d["on"] = True
            self.fav_tv.configure(cursor="fleur")

    def fav_drag_end(self, e):
        d, self._fav_drag = getattr(self, "_fav_drag", None), None
        tv = self.fav_tv
        tv.configure(cursor="")
        if not d or not d["on"]:
            return
        target = tv.identify_row(e.y)
        self.fav_drop(d["row"], target, e.y)

    def fav_drop(self, row, target, y=None):
        """Drop `row` (with the other selected rows) on `target`: on a group = into it; on a favorite = before it (or
        after it, lower half of the row); on empty space = ungrouped, at the end."""
        st, tv = self.favs(), self.fav_tv
        if str(row).startswith(GROUP_PRE):                        # a group: reorder the groups
            if str(target).startswith(GROUP_PRE):
                st.move_group(row[len(GROUP_PRE):], target[len(GROUP_PRE):])
            elif target and st.get(target) and st.get(target).get("group"):
                st.move_group(row[len(GROUP_PRE):], st.get(target)["group"])
            else:
                st.move_group(row[len(GROUP_PRE):], None)
            return self.fav_changed([row])
        sel = set(tv.selection())
        ids = self._fav_ids(sel if row in sel else {row})          # dragging a row outside the selection: just it
        ids = [f["id"] for f in st.items if f["id"] in ids]
        if target in ids:
            return
        if not target:
            st.move(ids, "")
        elif str(target).startswith(GROUP_PRE):
            st.move(ids, target[len(GROUP_PRE):])
        else:
            t = st.get(target)
            before = target
            if y is not None:
                bb = tv.bbox(target)
                if bb and y > bb[1] + bb[3] / 2:                   # lower half: after it
                    sib = st.in_group(t.get("group", ""))
                    i = sib.index(t)
                    nxt = next((s for s in sib[i + 1:] if s["id"] not in ids), None)
                    before = nxt["id"] if nxt else None
            st.move(ids, t.get("group", ""), before)
        self.fav_changed(ids)

    # ---------------------------------------------------------------- edit
    def fav_edit(self):
        ids = self._fav_ids()
        if len(ids) != 1:
            return
        st = self.favs()
        f = st.get(ids[0])
        dlg = tk.Toplevel(self.root)
        over_app(dlg, self.dlg_parent())               # 2.114.3: over the app, on its monitor
        dlg.title("Edit favorite")
        P2 = C["panel2"]
        dlg.configure(bg=P2, padx=16, pady=12)
        dlg.transient(self.root)
        vars_ = {}
        rows = [("name", "Name", f["name"]), ("note", "Note", f.get("note") or "")]
        if f.get("kind") == "link":
            rows.append(("url", "Trade link", f.get("url") or ""))
        for key, label, val in rows:
            tk.Label(dlg, text=label, bg=P2, fg=C["text"]).pack(anchor="w")
            v = tk.StringVar(value=val)
            ttk.Entry(dlg, textvariable=v, width=60).pack(fill="x", pady=(2, 8))
            vars_[key] = v
        tk.Label(dlg, text="Group", bg=P2, fg=C["text"]).pack(anchor="w")
        gnames = ["(no group)"] + [g["name"] for g in st.groups]
        cur = st.group(f.get("group", ""))
        gv = tk.StringVar(value=cur["name"] if cur else gnames[0])
        ttk.Combobox(dlg, textvariable=gv, values=gnames, state="readonly").pack(fill="x", pady=(2, 8))
        msg = tk.Label(dlg, text="", bg=P2, fg=C["red"], anchor="w")
        msg.pack(fill="x")

        def save():
            name = vars_["name"].get().strip()
            if not name:
                return msg.config(text="It needs a name.")
            f["name"], f["note"] = name, vars_["note"].get().strip()
            gid = next((g["id"] for g in st.groups if g["name"] == gv.get()), "")
            if gid != f.get("group", ""):
                st.move([f["id"]], gid)
            new_url = vars_.get("url").get().strip() if "url" in vars_ else None
            dlg.destroy()
            if new_url and new_url != f.get("url"):
                if not FV.is_link(new_url):
                    self.fav_say("That isn't a trade-site link - the old search is kept.", C["red"])
                else:
                    self.fav_relink(f["id"], new_url)
            self.fav_changed([f["id"]])
            self.fav_show()
        row = tk.Frame(dlg, bg=P2)
        row.pack(fill="x")
        ttk.Button(row, text="Save", style="Primary.TButton", command=save).pack(side="right")
        ttk.Button(row, text="Cancel", command=dlg.destroy).pack(side="right", padx=(0, 8))
        dlg.bind("<Return>", lambda e: save())
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        try:
            dlg.grab_set()
        except tk.TclError:
            pass

    def fav_relink(self, fid, url):
        self.fav_say("Reading the link…")

        def work():
            info, err = FV.read_link(url)
            self.ui_q.put(("fav_relinked", fid, url, info, err))
        threading.Thread(target=work, daemon=True).start()

    def ev_fav_relinked(self, fid, url, info, err):
        f = self.favs().get(fid)
        if f is None:
            return
        if err:
            return self.fav_say(err, C["red"])
        f.update(url=url, league=info.get("league") or "", query=info["query"], sort=info.get("sort"),
                 qid=info.get("qid"))
        self.fav_res.pop(fid, None)
        self.fav_changed([fid])
        self.fav_say(f"\"{f['name']}\" now uses the new link.", C["green"])
        if self.fav_sel == fid:
            self.fav_search()

    # ---------------------------------------------------------------- open / search
    def fav_pick(self, fid):
        tv = getattr(self, "fav_tv", None)
        if tv is not None and tv.exists(fid):
            parent = tv.parent(fid)
            if parent:
                tv.item(parent, open=True)
            tv.selection_set(fid)
            tv.focus(fid)
            tv.see(fid)
        self.fav_selected()

    def fav_double(self, e):
        row = self.fav_tv.identify_row(e.y)
        if row and not str(row).startswith(GROUP_PRE):
            self.fav_search()
            return "break"
        return None

    def fav_selected(self):
        ids = self._fav_ids()
        fid = ids[0] if len(ids) == 1 and len(self.fav_tv.selection()) == 1 else None
        if fid == self.fav_sel:
            return
        self.fav_sel = fid
        self.fav_show(first=True)

    def fav_rec(self, f, make=True):
        """An item favorite's live record (made the first time it's opened)."""
        rid = next((r["id"] for r in self.records.values() if r.get("src") == "fav" and r.get("fav") == f["id"]), None)
        if rid is not None or not make:
            return self.records.get(rid)
        rid = self.next_id
        self.next_id += 1
        self.records[rid] = {"id": rid, "item": FV.unpack_item(f["item"]), "state": "queued", "label": "", "total": 0,
                             "prices": [], "est": None, "qid": None, "time": time.time(),
                             "resolved": bool(f.get("resolved")), "mark": "new", "raw": f.get("raw") or "",
                             "src": "fav", "fav": f["id"], "opts": copy.deepcopy(f.get("opts") or {})}
        self.dirty = True
        return self.records[rid]

    def fav_show(self, first=False, card_only=False):
        """Draw the selected favorite (first: it was just picked - search it if it hasn't been this session).
        2.103.3 (feedback: every action flickered): the card is built out of sight and swapped in at once, and
        card_only keeps the listings as they are."""
        v = getattr(self, "favv", None)
        if v is None:
            return
        f = self.favs().get(self.fav_sel) if self.fav_sel else None
        keep = card_only and f is not None and f.get("kind") == "item" and v.rid is not None
        real, old = v.left, list(v.left.winfo_children())
        top = v.lcanvas.yview()[0] if keep else 0
        holder = tk.Frame(real, bg=C["panel2"])
        v.left = holder
        try:
            self._fav_show_into(v, f, first, keep)
        finally:
            v.left = real
            for w in old:
                w.destroy()
            holder.pack(fill="both", expand=True)
            v.lcanvas.update_idletasks()
            v.lcanvas.yview_moveto(top)

    def _fav_show_into(self, v, f, first, keep):
        rid0 = v.rid
        v.rid = None
        v.search_btn = None
        v.open_btn = v.head_open                            # (the old card's button is gone with the old card)
        if f is None:
            n = len(self._fav_ids()) if hasattr(self, "fav_tv") else 0
            if not (self.favs().items or self.favs().groups):
                v.open_btn.config(state="disabled")             # P2: the empty list says what to do
                return self.pcv_entries(v, None, 0, 0, "")
            tk.Label(v.left, text=f"{n} favorites selected" if n > 1 else "Pick a favorite on the left.",
                     bg=C["panel2"], fg=C["muted"], font=("Segoe UI", 10), anchor="nw", justify="left").pack(
                fill="x", pady=12)
            v.open_btn.config(state="disabled")
            return self.pcv_entries(v, None, 0, 0, "")
        if f.get("kind") == "item":
            rec = self.fav_rec(f)
            v.rid = rec["id"]
            _card, v.search_btn = self.pcv_card(v, rec)
            self._fav_note(v, f)
            if not (keep and rid0 == rec["id"]):
                self.pcv_list(v, rec)
            if first and not rec.get("fav_searched"):
                rec["fav_searched"] = True
                self.reprice([rec["id"]])
            return
        self.fav_link_card(v, f)
        self._fav_note(v, f)
        res = self.fav_res.get(f["id"])
        v.open_btn.config(state="normal")
        if f["id"] in self.fav_busy:
            self.pcv_entries(v, None, 0, 0, "Searching the trade site…")
        elif res is None:
            self.pcv_entries(v, None, 0, 0, "")
            if first:
                self.fav_search()
        elif res.get("err"):
            self.pcv_entries(v, None, 0, 0, "Couldn't search: " + res["err"][:90])
        else:
            from .trade import RAW_LISTINGS
            ids = res.get("ids") or []
            self.pcv_entries(v, [RAW_LISTINGS[i] for i in ids if i in RAW_LISTINGS], res.get("total", 0), len(ids))

    def _fav_note(self, v, f):
        if f.get("note"):
            tk.Label(v.left, text=f["note"], bg=C["panel2"], fg=C["muted"], font=("Segoe UI", 9, "italic"),
                     anchor="w", justify="left", wraplength=440).pack(fill="x", pady=(8, 0))

    def fav_rec_changed(self, rec, redraw=True, card_only=False):
        """Price Checks' card machinery changed an item favorite (a filter, a search): keep it, redraw it.
        2.103.3: redraw=False - a tick painted in place; card_only - the listings stay."""
        f = self.favs().get(rec.get("fav"))
        if f is not None:
            f["item"], f["opts"] = FV.pack_item(rec["item"]), copy.deepcopy(rec.get("opts") or {})
            f["resolved"] = bool(rec.get("resolved"))
            if rec.get("state") == "done":
                self.fav_store_last(f, rec)
            self._fav_save_soon()
        v = getattr(self, "favv", None)
        if redraw and v is not None and v.rid == rec["id"]:
            self.fav_show(card_only=card_only)

    def fav_store_last(self, f, rec):
        from .pricefmt import fmt_div, fmt_price
        if rec.get("state") != "done":
            return
        price = fmt_div(rec["est"]) if rec.get("est") is not None else fmt_price(rec["prices"][0]) \
            if rec.get("prices") else ("-" if not rec.get("total") else "")    # P2: "-" (was "none")
        f["last"] = {"price": price, "total": rec.get("total") or 0, "ts": time.time()}

    def _fav_save_soon(self):
        if getattr(self, "_fav_save_job", None) is None:
            def go():
                self._fav_save_job = None
                self.fav_changed()
            self._fav_save_job = self.root.after(400, go)

    def fav_search(self):
        f = self.favs().get(self.fav_sel) if self.fav_sel else None
        if f is None:
            ids = self._fav_ids()
            f = self.favs().get(ids[0]) if len(ids) == 1 else None
        if f is None:
            return
        if f.get("kind") == "item":
            rec = self.fav_rec(f)
            rec["fav_searched"] = True
            return self.reprice([rec["id"]])
        self.fav_search_link(f)

    def fav_search_group(self, gid):
        for f in self.favs().in_group(gid):
            if f.get("kind") == "item":
                rec = self.fav_rec(f)
                rec["fav_searched"] = True
                self.reprice([rec["id"]])
            else:
                self.fav_search_link(f)

    @staticmethod
    def fav_status(f):
        """2.105.1 (feedback: a link favorite searched "Any"): Seller follows your Seller setting (Settings) unless
        you picked one on this card - a trade link's own status (the site's default) doesn't count."""
        from .trade import STATUS_CHOICES
        q = f.setdefault("query", {})
        st = q.setdefault("status", {"option": "securable"})
        if not f.get("status_own"):
            st["option"] = dict(STATUS_CHOICES).get(SETTINGS.get("status"), "securable")
        return st

    def fav_search_link(self, f):
        if f["id"] in self.fav_busy:
            return
        self.fav_status(f)
        self.fav_busy.add(f["id"])
        league = SETTINGS.get("league") or f.get("league") or "Standard"
        body = {"query": FV.clean_query(f.get("query")), "sort": f.get("sort") or {"price": "asc"}}
        if self.fav_sel == f["id"]:
            self.fav_show()

        def work():
            try:
                from .config import BASE
                from .net import call
                from .trade import collapse_sellers, fetch_rich
                res = call("POST", f"{BASE}/search/poe2/{quote(league)}", json=body)
                ids = (res.get("result") or [])[:10]
                if ids:                                             # (keeps each listing for the cards; 2.113.0:
                    ids = [r["id"] for r in collapse_sellers(fetch_rich(res.get("id"), ids))] or ids   # one per seller)
                from .trade import RAW_LISTINGS
                first = next((((RAW_LISTINGS.get(i) or {}).get("listing") or {}).get("price") for i in ids
                              if (((RAW_LISTINGS.get(i) or {}).get("listing") or {}).get("price"))), None)
                out = {"total": res.get("total", 0), "ids": ids, "qid": res.get("id"), "league": league,
                       "first": (first["amount"], first["currency"]) if first else None}
            except Exception as ex:
                out = {"err": str(ex)}
            self.ui_q.put(("fav_link_done", f["id"], out))
        threading.Thread(target=work, daemon=True).start()

    def ev_fav_link_done(self, fid, out):
        self.fav_busy.discard(fid)
        self.fav_res[fid] = out
        f = self.favs().get(fid)
        if f is not None and not out.get("err"):
            p = out.get("first")
            amt = (int(p[0]) if float(p[0]).is_integer() else p[0]) if p else None
            f["last"] = {"price": f"{amt} {p[1]}" if p else "none", "total": out.get("total", 0), "ts": time.time()}
            self.fav_changed()
        if self.fav_sel == fid:
            self.fav_show()

    def _fav_url(self, f):
        if f.get("kind") == "item":
            rec = self.fav_rec(f, make=False)
            qid = rec.get("qid") if rec else None
            return f"https://www.pathofexile.com/trade2/search/poe2/{quote(SETTINGS['league'])}/{qid}" if qid else None
        # 2.105.1 (feedback: it opened without the mods ticked on the card): the search as the card has it now -
        # the trade site takes it in the link (?q=), so nothing is searched from here
        import json
        self.fav_status(f)
        league = SETTINGS.get("league") or f.get("league") or "Standard"
        body = {"query": FV.clean_query(f.get("query")), "sort": f.get("sort") or {"price": "asc"}}
        return (f"https://www.pathofexile.com/trade2/search/poe2/{quote(league)}?q="
                + quote(json.dumps(body, separators=(",", ":"))))

    def _fav_one(self):
        ids = self._fav_ids()
        return self.favs().get(ids[0]) if len(ids) == 1 else (self.favs().get(self.fav_sel) if self.fav_sel else None)

    def fav_open_trade(self):
        f = self._fav_one()
        if f and f.get("kind") == "item":                   # 2.105.1: changes on the card are searched first
            rec = self.fav_rec(f, make=False)
            if rec is not None and (rec.get("changed") or rec.get("qid")):
                return self.open_rec_trade(rec)
        url = self._fav_url(f) if f else None
        if url:
            webbrowser.open(url)
        elif f:
            self.fav_say("Search it first (Enter) - then it opens on the trade site.")    # (an item not searched yet)

    def fav_copy_link(self):
        f = self._fav_one()
        url = self._fav_url(f) if f else None
        if not url:
            return self.fav_say("Search it first (Enter) - then its link can be copied.")
        self.ignore_clip(url)
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        self.fav_say("Copied the trade-site link.", C["green"])

    # ---------------------------------------------------------------- a pasted search's filters
    def fav_link_card(self, v, f):
        """The search behind a trade link, as a card: every stat and filter with its switch and Min / Max. Changes
        are kept with the favorite; Search (Enter) runs it again."""
        from .mods import SIDTEXT
        from .trade import STATUS_CHOICES
        P2, bg = C["panel2"], C["odd"]
        q = f.setdefault("query", {})
        card = tk.Frame(v.left, bg=bg, highlightthickness=1, highlightbackground=C["line"], padx=8, pady=8)
        card.pack(fill="x")
        tk.Label(card, text=f["name"], bg=bg, fg=C["accent"], font=("Segoe UI", 12, "bold"), wraplength=320,
                 justify="center").pack(fill="x")
        what = [x for x in (FV.link_name(q) if FV.link_name(q) != f["name"] else "",
                            f"searches {SETTINGS.get('league') or f.get('league') or ''}") if x]
        tk.Label(card, text="  ·  ".join(what), bg=bg, fg=C["muted"], font=("Segoe UI", 9)).pack(fill="x")

        def section(title):
            tk.Label(card, text=title, bg=bg, fg=C["accent"], font=("Segoe UI", 9, "bold"), anchor="w").pack(
                fill="x", pady=(8, 2))

        def changed(_e=None):
            self._fav_save_soon()

        def vbox(row, holder, key, width=5):
            val = holder.get(key)
            e = tk.Entry(row, width=width, bg=C["panel"], fg=C["text"], insertbackground=C["text"], relief="flat",
                         highlightthickness=1, highlightbackground=C["line"], highlightcolor=C["accent"],
                         font=("Segoe UI", 9), justify="center")
            e.insert(0, "" if val is None else f"{val:g}" if isinstance(val, (int, float)) else str(val))

            def keep(_e=None):
                t = e.get().strip().replace(",", ".")
                if not t:
                    holder.pop(key, None)
                else:
                    try:
                        holder[key] = int(float(t)) if float(t).is_integer() else float(t)
                    except ValueError:
                        return e.config(highlightbackground=C["red"])
                e.config(highlightbackground=C["line"])
                changed()
            e.bind("<KeyRelease>", keep)
            e.bind("<Return>", lambda _e: (keep(), self.fav_search(), "break")[-1])
            return e

        def switch(row, holder, text, fg=C["text"], group=None):
            var = tk.BooleanVar(value=not holder.get("disabled"))

            def flip():
                if var.get():
                    holder.pop("disabled", None)
                    if group is not None and group[0].get("disabled"):    # 2.105.1 (feedback: ticked legacies
                        group[0].pop("disabled", None)                     # weren't searched - their group was
                        group[1].set(True)                                 # off): a ticked stat turns it on
                else:
                    holder["disabled"] = True
                changed()
            cb = tk.Checkbutton(row, variable=var, command=flip, bg=bg, activebackground=bg, selectcolor=C["panel"],
                                fg=fg, activeforeground=fg, text=text, anchor="w", justify="left", wraplength=210,
                                font=("Segoe UI", 9), highlightthickness=0, bd=0)
            cb.pack(side="left", fill="x", expand=True)
            cb.var = var
            return cb
        # ---- what it searches for
        item_rows = [(k, q.get(k)) for k in ("name", "type", "term") if q.get(k)]
        if item_rows:
            section("ITEM")
            for k, val in item_rows:
                if isinstance(val, dict):
                    val = val.get("option") or val.get("discriminator") or ""
                row = tk.Frame(card, bg=bg)
                row.pack(fill="x")
                tk.Label(row, text={"term": "Text"}.get(k, k.capitalize()), bg=bg, fg=C["muted"], width=8,
                         anchor="w", font=("Segoe UI", 9)).pack(side="left")
                tk.Label(row, text=str(val), bg=bg, fg=C["text"], anchor="w", font=("Segoe UI", 9)).pack(side="left")
        # ---- stats
        for gi, g in enumerate(q.get("stats") or []):
            fl = g.get("filters") or []
            if not fl and g.get("type") == "and":
                continue
            n = (g.get("value") or {}).get("min")
            title = GROUP_TYPES.get(g.get("type"), str(g.get("type") or "").upper()).format(n=n if n is not None else "?")
            section(f"STATS  ·  {title.upper()}")
            row = tk.Frame(card, bg=bg)
            row.pack(fill="x")
            gcb = switch(row, g, "this whole group", C["muted"])
            if g.get("type") in ("count", "weight", "weight2"):
                g.setdefault("value", {})
                tk.Label(row, text="min", bg=bg, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left")
                vbox(row, g["value"], "min", 4).pack(side="left", padx=(2, 0))
            for flt in fl:
                row = tk.Frame(card, bg=bg)
                row.pack(fill="x", pady=1)
                sid = str(flt.get("id") or "")
                text = SIDTEXT.get(sid) or sid
                text = text[:1].upper() + text[1:]
                kind = sid.split(".")[0] if "." in sid else ""
                if kind and kind not in ("explicit",):
                    text = f"{text}  ({kind})"
                switch(row, flt, text, group=(g, gcb.var))
                flt.setdefault("value", {})
                if isinstance(flt["value"], dict) and "option" not in flt["value"]:
                    vbox(row, flt["value"], "max").pack(side="right", padx=(2, 0))
                    vbox(row, flt["value"], "min").pack(side="right")
                elif isinstance(flt["value"], dict):
                    tk.Label(row, text=str(flt["value"].get("option")), bg=bg, fg=C["muted"],
                             font=("Segoe UI", 9)).pack(side="right")
        # ---- the other filters
        for gname, grp in (q.get("filters") or {}).items():
            if not isinstance(grp, dict) or not grp.get("filters"):
                continue
            section(FILTER_NAMES.get(gname, _pretty(gname)).upper())
            for key, val in grp["filters"].items():
                if not isinstance(val, dict):
                    continue
                row = tk.Frame(card, bg=bg)
                row.pack(fill="x", pady=1)
                if "option" in val:
                    opt = val.get("option")
                    if key == "category":
                        opt = str(opt).split(".")[-1].replace("_", " ").title()
                    switch(row, val, f"{_pretty(key)}: {opt}")
                elif key == "account":
                    switch(row, val, f"Seller: {val.get('input') or ''}")
                else:
                    switch(row, val, _pretty(key))
                    vbox(row, val, "max").pack(side="right", padx=(2, 0))
                    vbox(row, val, "min").pack(side="right")
                    if key == "price" and val.get("option"):
                        tk.Label(row, text=str(val["option"]), bg=bg, fg=C["muted"], font=("Segoe UI", 9)).pack(
                            side="right", padx=(0, 4))
        # ---- seller
        section("SELLER")
        st = self.fav_status(f)
        names = [n for n, _v in STATUS_CHOICES]
        var = tk.StringVar(value=next((n for n, val in STATUS_CHOICES if val == st.get("option")), names[0]))
        cb = ttk.Combobox(card, textvariable=var, values=names, state="readonly")
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>", lambda e: (st.__setitem__("option", dict(STATUS_CHOICES)[var.get()]),
                                                   f.__setitem__("status_own", True), changed()))
        btns = tk.Frame(v.left, bg=P2)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Search", style="Primary.TButton", command=self.fav_search).pack(
            side="left", fill="x", expand=True)
        ob = ttk.Button(btns, text="Trade Site", command=self.fav_open_trade)   # P2: under the card
        ob.pack(side="left", padx=(8, 0))
        v.open_btn = ob
        v.lcanvas.yview_moveto(0)
