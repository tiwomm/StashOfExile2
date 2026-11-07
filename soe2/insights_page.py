"""Market Insights (2.12.1; was Top value, 2.1.0, a Labs tool): the most valuable things the app has seen, per kind of item - your own priced items
(Price checks), the mods worth the most (what the Mod book learned from listings) and the dearest listings it looked
at on the trade site. Nothing is searched for this window: it only shows what earlier price checks found."""
import re
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from .config import SETTINGS, save_json
from .market import MARKET
from .valuelog import VALUE_LOG, sig_of
from .mods import impact_key, JEWEL_BASE, norm, SIDTEXT
from .pricefmt import fmt_div
from .style import C, SegBar
from .chrome import SectionBar, Viewport, section as chrome_section

KINDS = ["All", "Gear", "Tablets", "Waystones", "Jewels", "Relics"]     # P2 (2.104.0): All and Gear (gear showed nowhere)
ONE = {"All": "item", "Gear": "gear", "Tablets": "tablet", "Waystones": "waystone", "Jewels": "jewel", "Relics": "relic"}


# 2.105.0 (feedback): Gear and Tablets get a second choice - the slot / the kind of tablet (the full list, always)
GEAR_SUBS = [("Helmets", ("helmet",)), ("Body Armours", ("body_armour",)), ("Gloves", ("gloves",)),
             ("Boots", ("boots",)), ("Belts", ("belt",)), ("Amulets", ("amulet",)), ("Rings", ("ring",)),
             ("One-hand weapons", ("one_hand_axe", "one_hand_mace", "one_hand_sword", "dagger", "claw", "wand",
                                   "sceptre", "flail", "spear")),
             ("Two-hand weapons", ("two_hand_axe", "two_hand_mace", "two_hand_sword", "quarterstaff", "staff")),
             ("Bows & Crossbows", ("bow", "crossbow")), ("Shields & Bucklers", ("shield", "buckler")),
             ("Foci", ("focus",)), ("Quivers", ("quiver",)), ("Flasks", ("flask",)), ("Charms", ("charm",)),
             ("Talismans", ("talisman",))]
TABLET_SUBS = ["Abyss", "Breach", "Delirium", "Expedition", "Irradiated", "Overseer", "Ritual", "Temple"]
ALL_SUB = "All"


def subs_for(kind):
    if kind == "Gear":
        return [ALL_SUB] + [n for n, _c in GEAR_SUBS]
    if kind == "Tablets":
        return [ALL_SUB] + [f"{t} Tablets" for t in TABLET_SUBS]
    return []


def sub_match(kind, sub, base, cls=""):
    """Is this base in the picked slot / tablet kind?"""
    if not sub or sub == ALL_SUB or kind not in ("Gear", "Tablets"):
        return True
    b = str(base or "")
    if kind == "Tablets":
        return b.startswith(sub.replace(" Tablets", "") + " ")
    from . import gamedata
    info = gamedata.base(b) or {}
    c = info.get("class") or ""
    if not c and cls:
        txt = str(cls).lower().rstrip("s").replace(" ", "_")
        c = next((k for _n, ks in GEAR_SUBS for k in ks if k == txt or txt.startswith(k)), "")
    return c in dict(GEAR_SUBS).get(sub, ())


def kind_of(base, cls=""):
    b, c = str(base or ""), str(cls or "").lower()
    if b.endswith("Tablet") or "tablet" in c:
        return "Tablets"
    if b.startswith("Waystone") or "waystone" in c:
        return "Waystones"
    if JEWEL_BASE.search(b) or c.startswith("jewel"):
        return "Jewels"
    if "Relic" in b or "relic" in c:
        return "Relics"
    return None


def kind_match(kind):
    """P2: a kind_fn for this tab - All takes everything, Gear what isn't a tablet, waystone, jewel or relic."""
    return lambda base, cls="": kind if kind == "All" or (kind_of(base, cls) or "Gear") == kind else None


def _mod_text(sid):
    t = SIDTEXT.get(sid, sid)
    return re.sub(r"\s+(found )?in map$", "", t)


class InsightsPage:
    """Mixed into App."""

    def build_insights_window(self, body):
        P1, P2 = C["panel"], C["panel2"]
        top = tk.Frame(body, bg=P1, padx=12, pady=8)     # P2 (2.104.0): the breadcrumb names the page; no Refresh
        top.pack(fill="x")                               # (it fills in on open and after each price)
        self.ins_kind = SegBar(top, KINDS, command=lambda v: self.ins_kind_changed(), size=9, pad=(12, 4))
        self.ins_kind.pack(side="left")
        self.ins_sub = tk.StringVar(value=ALL_SUB)          # 2.105.0: Gear / Tablets - which slot / kind
        self.ins_sub_box = ttk.Combobox(top, textvariable=self.ins_sub, state="readonly", width=18)
        self.ins_sub_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_insights())
        tk.Label(top, text="Your price checks, this league - nothing is searched here", bg=P1, fg=C["muted"],
                 font=("Segoe UI", 9)).pack(side="right")
        # 2.73.2: the picked row's item in a panel at the side (like Price checks) - it was a pop-up at the mouse
        main = tk.Frame(body, bg=P1)
        main.pack(fill="both", expand=True, padx=8, pady=(8, 8))
        deto, det = chrome_section(main, "Item", padx=12, pady=8)
        deto.pack(side="right", fill="y", padx=(4, 4), pady=4)
        deto.configure(width=360)
        deto.pack_propagate(False)
        dbar = tk.Frame(det, bg=P2)                          # P2: under the card (toasts covered it at the bottom)
        self.ins_det_btns = {
            "open": ttk.Button(dbar, text="Show in Bulk Pricing", command=self.ins_open_record),
            "again": ttk.Button(dbar, text="Price it again", command=self.ins_price_again),
            "trade": ttk.Button(dbar, text="Trade Site", command=self.ins_open_search),
            "remove": ttk.Button(dbar, text="Remove", command=self.ins_remove_picked, style="Quiet.TButton")}
        self.undo_button(dbar, "insights", side="bottom", pady=(8, 0))   # P2: only with something to undo
        self.ins_card = tk.Frame(det, bg=P2)
        self.ins_card.pack(fill="x")
        dbar.pack(fill="x", pady=(8, 0))
        self.ins_det = tk.Label(det, text="Pick a row to see its item here.", bg=P2, fg=C["muted"], anchor="nw",
                                justify="left", font=("Segoe UI", 9), wraplength=320)
        self.ins_det.pack(fill="both", expand=True, pady=(8, 0))
        self.ins_pick = None
        grid = tk.Frame(main, bg=P1)
        grid.pack(side="left", fill="both", expand=True)
        grid.columnconfigure(0, weight=1, uniform="g")
        grid.columnconfigure(1, weight=1, uniform="g")
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)
        self.ins_tables = {}

        def table(r, c, key, title, hint, cols, colspan=1):
            fo, f = chrome_section(grid, title, padx=8, pady=8)                # 2.69.0
            fo.grid(row=r, column=c, columnspan=colspan, sticky="nsew", padx=4, pady=4)
            tk.Label(f, text=hint, bg=P2, fg=C["muted"], font=("Segoe UI", 9), anchor="w", justify="left",
                     wraplength=240).pack(fill="x")                      # (2.98.0: wraps to its width)
            box = tk.Frame(f, bg=P2)
            box.pack(fill="both", expand=True, pady=(4, 0))
            tv = ttk.Treeview(box, columns=[k for k, *_ in cols], show="headings", height=5)
            for cid, t, w, a in cols:
                tv.heading(cid, text=t)
                tv.column(cid, width=w, anchor=a, stretch=(cid in ("name", "mod", "mods")))
            sb = ttk.Scrollbar(box, orient="vertical", command=tv.yview)
            tv.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            tv.pack(fill="both", expand=True)
            tv.tag_configure("star", foreground="#ffd9a8")
            empty = tk.Label(box, text="", bg=C["panel"], fg=C["muted"], font=("Segoe UI", 9), justify="center")
            self.ins_tables[key] = (tv, empty)
            tv.bind("<<TreeviewSelect>>", lambda e, k=key: self.ins_show(k))
            return tv
        mine = table(0, 0, "mine", "Your most valuable", "Everything you've priced. Delete hides a row here; Ctrl+Z "
                                                         "brings it back.",
                     (("name", "Item", 120, "w"), ("base", "Type", 110, "w"), ("est", "Worth", 72, "e")))
        mine.bind("<Double-1>", lambda e: self.ins_open_record())
        self.list_register("insights", mine, delete=self.ins_forget)
        mine.menu_actions = lambda sel: [("Show in Bulk Pricing", lambda: (self.ins_show("mine"), self.ins_open_record())),
                                         ("Price it again", lambda: (self.ins_show("mine"), self.ins_price_again())),
                                         ("Remove", lambda: self.ins_forget(sel), bool(sel), "Del")]
        table(0, 1, "mods", "Mods worth the most", "What the Mod book learned: the typical asking price of listings "
                                                    "with this mod. ★ = valuable in your Mod book.",
              (("mod", "Mod", 120, "w"), ("base", "On", 76, "w"), ("med", "Typical", 76, "e"), ("n", "Seen", 52, "e")))
        table(1, 0, "seen", "Most expensive listings seen", "The priciest listings your checks came across on the "
                                                     "trade site.",
              (("price", "Asking", 90, "e"), ("name", "Item", 200, "w"), ("mods", "Mods", 360, "w"),
               ("when", "Seen", 70, "w")), colspan=2)
        self.list_register("insights", self.ins_tables["seen"][0], delete=self.ins_forget_seen)    # 2.73.2: Delete
        self.ins_tables["seen"][0].menu_actions = lambda sel: [            # 2.36.0
            ("Trade Site", lambda: (self.ins_show("seen"), self.ins_open_search())),
            ("Remove", lambda: self.ins_forget_seen(sel), bool(sel), "Del")]
        body.bind("<Unmap>", lambda e: self.ins_preview_close(), add="+")
        self.list_register("insights", self.ins_tables["mods"][0], delete=self.ins_forget_mods)   # 2.73.2: Delete
        self.ins_tables["mods"][0].menu_actions = lambda sel: [
            ("Remove", lambda: self.ins_forget_mods(sel), bool(sel), "Del")]
        self.ins_modmap = {}
        self.ins_rowmap, self.ins_seenmap = {}, {}
        self.refresh_insights()

    def ins_kind_changed(self):
        """Gear / Tablets show the slot / tablet kind box (All at first); the other tabs hide it."""
        subs = subs_for(self.ins_kind.get())
        self.ins_sub.set(ALL_SUB)
        if subs:
            self.ins_sub_box.config(values=subs)
            if not self.ins_sub_box.winfo_ismapped():
                self.ins_sub_box.pack(side="left", padx=(12, 0))
        else:
            self.ins_sub_box.pack_forget()
        self.refresh_insights()

    def ins_kind_fn(self, kind):
        """kind_match plus the picked slot / tablet kind."""
        km, sub = kind_match(kind), self.ins_sub.get() if hasattr(self, "ins_sub") else ALL_SUB
        return lambda base, cls="": km(base, cls) if km(base, cls) == kind and sub_match(kind, sub, base, cls) else None

    def refresh_insights(self):
        if not hasattr(self, "ins_tables"):
            return
        kind = self.ins_kind.get()
        # ---- your own priced items
        tv, empty = self.ins_tables["mine"]
        tv.delete(*tv.get_children())
        self.ins_rowmap = {}
        league = SETTINGS.get("league")
        added = False
        for r in self.records.values():                      # (what's in Price checks now goes in the log too)
            if r.get("state") == "done" and r.get("est") is not None and sig_of(r.get("raw")) not in VALUE_LOG.items:
                added = VALUE_LOG.add(r, league) or added
        if added:
            VALUE_LOG.save()
        recs = VALUE_LOG.top(league, self.ins_kind_fn(kind), kind)
        for e in recs:                                     # 2.105.0: no Status column (listing marks are gone)
            iid = tv.insert("", "end", values=(e["name"], e["base"], fmt_div(e["est"])))
            self.ins_rowmap[iid] = e
        self._ins_empty(empty, not recs, f"No priced {ONE[kind]}s yet.\nPrice some with Ctrl+Alt+C or Bulk Pricing.")
        # ---- mods worth the most (the Mod book's data)
        tv, empty = self.ins_tables["mods"]
        tv.delete(*tv.get_children())
        if kind in ("Waystones", "Relics"):                 # 2.6.0: your ★ rules for these (nothing is learned)
            self._ins_rated_mods(tv, empty, kind)
            return self._ins_fill_seen(kind)
        stats = MARKET.cached_stats()
        hid = set(SETTINGS.get("ins_hidden_mods") or [])           # 2.73.2: removed by you
        rows = [(base, sid, st) for (base, sid), st in stats.items()
                if self.ins_kind_fn(kind)(base) == kind and st.get("n", 0) >= 3 and st.get("med") is not None
                and f"{base}|{sid}" not in hid]
        self.ins_modmap = {}
        rows.sort(key=lambda r: -r[2]["med"])
        for base, sid, st in rows[:50]:
            text = _mod_text(sid)
            star = impact_key(norm(text)) == "high"
            iid = tv.insert("", "end", values=(("★ " if star else "") + text[:1].upper() + text[1:],
                                               base.replace(" Tablet", ""), fmt_div(st["med"]), st["n"]),
                            tags=("star",) if star else ())
            self.ins_modmap[iid] = f"{base}|{sid}"
        why = (f"Nothing learned about {ONE[kind]} mods yet.\nPrice a few {ONE[kind]}s (Ctrl+Alt+C or Bulk Pricing) -\n"
               f"each one teaches the Mod book.")
        self._ins_empty(empty, not rows, why)
        self._ins_fill_seen(kind)

    def _ins_rated_mods(self, tv, empty, kind):
        """Waystones / Relics: the mods you rate ★ in the Mod book, and the best one you've priced with each."""
        from . import regex as R
        from .mods import impact_key, rule_key
        cat = "waystone" if kind == "Waystones" else "relic"
        league = SETTINGS.get("league")
        priced = VALUE_LOG.top(league, kind_match(kind), kind, limit=3000)
        have = [({norm(t) for t in e.get("mods") or []}, e) for e in priced]
        rows = []
        for m in R.mods(cat):
            lines = m.get("lines") or [m["line"]]
            keys = [norm(l) for l in lines]
            if not any(impact_key(rule_key(cat, k)) == "high" for k in keys):
                continue
            with_it = [e for ks, e in have if any(k in ks for k in keys)]
            best = max((e["est"] for e in with_it if e.get("est") is not None), default=None)
            text = " / ".join(l[:1].upper() + l[1:] for l in lines)
            rows.append((best if best is not None else -1, text, len(with_it), best))
        rows.sort(key=lambda r: (-r[0], r[1]))
        for _o, text, n, best in rows:
            tv.insert("", "end", values=("★ " + text, kind[:-1], fmt_div(best) if best is not None else "-",
                                         n or "-"), tags=("star",))
        self._ins_empty(empty, not rows, f"No ★ {kind[:-1].lower()} mods yet.\nRate them in Mod book > "
                                         f"{kind[:-1]} rules,\nor right-click a mod in Regex.")

    def _ins_fill_seen(self, kind):
        # ---- most expensive listings seen
        tv, empty = self.ins_tables["seen"]
        tv.delete(*tv.get_children())
        # 2.18.0: rows with neither mod lines nor stat ids (saved by an older version) say nothing: left out
        hidden = set(SETTINGS.get("ins_hidden") or [])           # 2.73.2: removed by you
        seen = [x for x in MARKET.top_listings(detail=True) if self.ins_kind_fn(kind)(x["base"]) == kind
                and (x.get("lines") or x.get("sids")) and self.ins_seen_key(x) not in hidden][:50]
        now = time.time()
        self.ins_seenmap = {}
        for x in seen:
            mods = "  ·  ".join(l[:48] for l in self.ins_listing_mods(x)[:4])
            ts = x["seen"]
            age = now - (ts or now)
            when = "today" if age < 86400 else datetime.fromtimestamp(ts).strftime("%b %d")
            name = x["name"] or x["base"]
            iid = tv.insert("", "end", values=(x["price"] or fmt_div(x["div"]), name, mods, when))
            self.ins_seenmap[iid] = x
        self._ins_empty(empty, not seen, "Nothing seen yet.\nIt fills in as your price checks find listings."
                        if kind != "Relics" else "Relics aren't price-checked yet.")

    @staticmethod
    def ins_listing_mods(x):
        """A listing's mods as the trade site wrote them; older rows only kept the stat ids (and the first number)."""
        if x.get("lines"):
            return [l for l in x["lines"] if l.strip()]
        out = []
        for sid in x.get("sids") or []:
            t = _mod_text(sid)
            v = (x.get("vals") or {}).get(sid)
            if v is not None and "#" in t:
                t = t.replace("#", f"{v:g}", 1)
            out.append(t[:1].upper() + t[1:])
        return out

    def ins_show(self, key):
        """Details of the row picked in one of the lists."""
        tv = self.ins_tables[key][0]
        sel = tv.selection()
        for k, (other, _e) in self.ins_tables.items():      # one list at a time
            if k != key and other.selection():
                other.selection_remove(*other.selection())
        for b in self.ins_det_btns.values():
            b.pack_forget()
        for w in self.ins_card.winfo_children():
            w.destroy()
        if not sel:
            self.ins_det.config(text="Pick a row to see its item here.", fg=C["muted"])
            return
        if key == "mine":
            e = self.ins_rowmap.get(sel[0])
            if not e:
                return
            self.ins_pick = ("mine", e)
            here = any(sig_of(r.get("raw")) == e["sig"] for r in self.records.values())
            when = datetime.fromtimestamp(e["ts"]).strftime("%b %d %H:%M")
            mods = "\n".join("  " + m for m in e.get("mods") or [])
            txt = (f"{e['name']}  ({e['base']})  -  worth about {fmt_div(e['est'])}"
                   + (f", {e['conf']} confidence" if e.get("conf") and e["conf"] != "-" else "") + f"\nPriced {when}"
                   + ("" if here else " · no longer in your Bulk Pricing list") + (f"\n{mods}" if mods else ""))
            self.ins_draw_card(self.ins_card, "mine", e)          # 2.73.2: the item, in the panel
            self.ins_det.config(text="" if here else "Priced earlier - no longer in your Bulk Pricing list.", fg=C["muted"])
            for k in ("open", "again"):                       # P2: the one that fits is the main button
                self.ins_det_btns[k].config(style="Primary.TButton")
            (self.ins_det_btns["open"] if here else self.ins_det_btns["again"]).pack(fill="x")
            self.ins_det_btns["remove"].pack(fill="x", pady=(8, 0))
        elif key == "seen":
            x = self.ins_seenmap.get(sel[0])
            if not x:
                return
            self.ins_pick = ("seen", x)
            when = datetime.fromtimestamp(x["seen"]).strftime("%b %d %H:%M") if x.get("seen") else "?"
            txt = f"Seen {when} while pricing a {x['base']}."      # (2.105.0: the card shows the rest)
            self.ins_draw_card(self.ins_card, "seen", x)          # 2.73.2
            self.ins_det.config(text=txt, fg=C["text"])
            if x.get("qid"):
                self.ins_det_btns["trade"].config(style="Primary.TButton")
                self.ins_det_btns["trade"].pack(fill="x")
            self.ins_det_btns["remove"].pack(fill="x", pady=(8, 0))
        else:
            self.ins_pick = None
            vals = tv.item(sel[0], "values")
            if self.ins_kind.get() in ("Waystones", "Relics"):
                self.ins_det.config(fg=C["text"], text=(
                    f"{vals[0]}  - rated valuable in your Mod book. "
                    + (f"You've priced {vals[3]} with it; the best was worth {vals[2]}." if vals[3] != "-" else
                       "None priced with it yet.")))
            else:
                self.ins_det.config(text=f"{vals[0]}  on {vals[1]}: listings with this mod typically ask {vals[2]} "
                                         f"({vals[3]} seen).", fg=C["text"])

    # ---------------- 2.18.0: click a row -> the item, drawn like the game's tooltip
    RARITY_FG = {"Unique": "#af6025", "Rare": "#ffff77", "Magic": "#8888ff", "Normal": "#c8c8c8"}

    def ins_preview_item(self, key, obj):
        """-> (name lines, rarity, mod lines, price text, footnote) for a row of Your most valuable / listings seen,
        or (2.53.0, key "pc") a Price checks row."""
        if key == "pc":
            est, it = obj.get("est"), obj.get("item") or {}
            if obj.get("nomatch"):
                price = "No match on the trade site"
            elif obj.get("manual"):
                price = "Check it by hand"
            elif est is not None:
                price = f"Worth about {fmt_div(est)}" + (f"  ·  {obj['conf']} confidence"
                                                        if obj.get("conf") and obj["conf"] != "-" else "")
            else:
                price = obj.get("label") or ("Pricing…" if obj.get("state") != "done" else "No listings")
            fake = {"raw": obj.get("raw") or "", "name": it.get("name"), "base": it.get("base")}
            head, rar, mods, _p, _f = self.ins_preview_item("mine", fake)
            rar = it.get("rarity") or rar
            n = len(obj.get("prices") or [])
            when = datetime.fromtimestamp(obj["time"]).strftime("%b %d %H:%M") if obj.get("time") else ""
            foot = "  ·  ".join(x for x in (f"Added {when}" if when else "",
                                            f"{n} listing{'s' * (n != 1)} seen" if n else "") if x)
            return head, rar, mods, price, foot
        if key == "mine":
            raw = obj.get("raw") or ""
            lines = [l.strip() for l in raw.splitlines()]
            rar = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("Rarity:")), "Rare")
            secs, cur = [], []
            for l in lines:
                if l.startswith("--------"):
                    secs.append(cur)
                    cur = []
                elif l:
                    cur.append(l)
            secs.append(cur)
            head = [l for l in (secs[0] if secs else []) if not l.startswith(("Item Class:", "Rarity:"))]
            mods = [l for l in (obj.get("mods") or []) if l] or \
                   [l for s in secs[1:] for l in s if not re.match(r"^(Item Level|Requires|Quality|Note|Sockets|"
                                                                    r"Corrupted|Unidentified|Map Tier|Waystone Tier)", l)]
            mods = [self.ins_with_value(m, lines) for m in mods]          # 2.25.3: the real numbers
            # 2.53.0: an advanced copy (Ctrl+Alt+C) has "{ Prefix Modifier ... }" lines and (min-max) ranges: as in game
            mods = [re.sub(r"\(-?\d+(?:\.\d+)?--?\d+(?:\.\d+)?\)", "", m) for m in mods if not m.startswith("{")]
            if not head:
                head = [obj.get("name") or "", obj.get("base") or ""]
            price = f"Worth about {fmt_div(obj.get('est'))}" + (f"  ·  {obj['conf']} confidence"
                                                               if obj.get("conf") and obj["conf"] != "-" else "")
            when = datetime.fromtimestamp(obj["ts"]).strftime("%b %d %H:%M") if obj.get("ts") else ""
            return [h for h in head if h], rar, mods, price, (f"Priced {when}" if when else "")
        name = obj.get("name") or obj.get("base") or ""
        base = obj.get("base") or ""
        head = [name[:-len(base)].strip(), base] if base and name.endswith(base) and name != base else [name]
        rar = "Rare" if len(head) > 1 else "Magic"
        when = datetime.fromtimestamp(obj["seen"]).strftime("%b %d %H:%M") if obj.get("seen") else ""
        price = f"Asking {obj.get('price') or fmt_div(obj.get('div'))}" + (f"  (≈ {fmt_div(obj['div'])})"
                                                                          if obj.get("price") else "")
        return [h for h in head if h], rar, self.ins_listing_mods(obj), price, (f"Seen on the trade site {when}"
                                                                                if when else "")

    def ins_facts(self, key, obj):
        """2.105.0: a row of Your most valuable / listings seen -> what the trade-site style card shows."""
        head, rar, mods, price, foot = self.ins_preview_item(key, obj)
        name = head[0] if head else (obj.get("name") or "")
        base = head[1] if len(head) > 1 else (obj.get("base") or name)
        parts, ilvl, req, rows = [], None, "", []
        raw = obj.get("raw") or "" if key == "mine" else ""
        if raw:
            from . import gamedata
            secs, cur = [], []
            for l in raw.splitlines():
                l = l.strip()
                if l.startswith("--------"):
                    secs.append(cur)
                    cur = []
                elif l:
                    cur.append(l)
            secs.append(cur)
            for sec in secs[1:]:
                if any(l.startswith(("{", "Item Level:")) for l in sec):
                    break
                for l in sec:
                    if l.startswith("Requires"):
                        req = l
                    elif ":" in l and not l.startswith("Note:"):
                        lab, val = l.split(":", 1)
                        aug = "(augmented)" in val
                        parts.append((lab.strip(), val.replace("(augmented)", "").strip(), aug))
            try:
                g = gamedata.read_item(raw)
            except Exception:
                g = None
            if g:
                ilvl = g.get("ilvl")
                for m in g.get("mods") or []:
                    k = m.get("kind") or "explicit"
                    t = m.get("tier")
                    tier = (("P" if k == "prefix" else "S" if k == "suffix" else "") + str(t)) if t and \
                        k in ("prefix", "suffix") else ""
                    text = re.sub(r"\(-?\d+(?:\.\d+)?--?\d+(?:\.\d+)?\)", "", m["text"])
                    rows.append((tier, text, m.get("source") or (k if k in ("implicit", "rune", "enchant") else
                                                                "explicit")))
        if not rows:
            rows = [("", m, "explicit") for m in mods]
        from .pricecheck_page import icons
        return {"name": name, "base": base, "rarity": rar, "parts": parts, "ilvl": ilvl, "req": req, "mods": rows,
                "price": price, "foot": foot, "icon": icons().get(obj.get("base") or base) or ""}

    def ins_draw_card(self, parent, key, obj, w=330):
        """2.105.0 (feedback): the item laid out like the trade site's cards (Price Checks' listings) - its picture,
        the name band, properties, item level, the mods with their tiers - and what it's worth at the foot."""
        from tkinter import font as tkfont
        from . import themes as _th
        from .pricecheck_page import ART_PX, RARITY_COL
        from .style import MOD_COL
        f = self.ins_facts(key, obj)
        t = _th.ST.theme
        bg, panel = C["odd"], C["panel2"]
        rk = RARITY_COL.get(f["rarity"])
        col = t.c("unique", "#af6025") if rk == "unique" else (C[rk] if rk else C["text"])
        cv = tk.Canvas(parent, width=w, height=200, bg=panel, highlightthickness=0, bd=0)
        cv.pack(fill="x")
        blue, red = "#8888ff", "#d26e5e"
        cx, y = w // 2, 0
        with _th.raw():
            img = self.pc_art(f["icon"]) if f["icon"] and SETTINGS.get("pc_art", True) else None
            if img is not None:
                cv.create_image(cx, 4, image=img, anchor="n")
                cv._art = img
                y = ART_PX + 10
            elif f["icon"]:
                cv._art_url = f["icon"]
            top = y
            box = cv.create_rectangle(0, top, w - 1, top + 10, fill=bg,
                                      outline=t.c(t.part("card", "border", default="border_light")))
            two = bool(f["name"]) and f["name"] != f["base"]
            hh = 46 if two else 30
            name_c = _th.card_header(cv, 2, top + 2, w - 3, top + hh, col, bg)
            if two:
                cv.create_text(cx, top + 14, text=f["name"], fill=name_c, font=(_th.head_font(), 11, "bold"))
                cv.create_text(cx, top + 33, text=f["base"], fill=name_c, font=(_th.head_font(), 10, "bold"))
            else:
                cv.create_text(cx, top + hh // 2 + 1, text=f["base"] or f["name"], fill=name_c,
                               font=(_th.head_font(), 11, "bold"))
            font = ("Segoe UI", 9)
            tw = w - 48
            y = top + hh + 10
            fm = tkfont.Font(root=cv, family="Segoe UI", size=9)

            def sep():
                nonlocal y
                y += 1
                cv.create_line(cx - 110, y, cx + 110, y, fill=C["line"])
                y += 8

            def line(text, fill, bold=False):
                nonlocal y
                tid = cv.create_text(cx, y, text=text, fill=fill, font=("Segoe UI", 9, "bold") if bold else font,
                                     width=tw, justify="center", anchor="n")
                bb = cv.bbox(tid)
                y = (bb[3] if bb else y + 14) + 1

            def pair(label, value, aug):
                nonlocal y
                if not value:
                    return line(label, C["muted"])
                a = label + ": "
                x0 = cx - (fm.measure(a) + fm.measure(value)) // 2
                cv.create_text(x0, y, text=a, fill=C["muted"], font=font, anchor="nw")
                cv.create_text(x0 + fm.measure(a), y, text=value, fill=blue if aug else C["text"], font=font,
                               anchor="nw")
                y += 15
            for p in f["parts"]:
                pair(*p)
            if f["ilvl"] or f["req"]:
                if f["parts"]:
                    sep()
                if f["ilvl"]:
                    pair("Item Level", str(f["ilvl"]), False)
                if f["req"]:
                    line(f["req"], C["muted"])
            kc = {"implicit": MOD_COL["implicit"], "rune": MOD_COL["rune"], "enchant": MOD_COL["enchant"],
                  "fractured": MOD_COL["fractured"], "desecrated": MOD_COL["desecrated"], "crafted": MOD_COL["enchant"]}
            first = [m for m in f["mods"] if m[2] in ("enchant", "implicit", "rune")]
            rest = [m for m in f["mods"] if m not in first]
            for group in (first, rest):
                if not group:
                    continue
                sep()
                for tier, text, kind in group:
                    if tier:
                        cv.create_text(8, y, text=tier, anchor="nw", font=("Segoe UI", 8, "bold"),
                                       fill=red if tier[:1] == "P" else blue)
                    line(text, kc.get(kind, MOD_COL["explicit"]))
            if not f["mods"]:
                sep()
                line("(no mods saved)", C["muted"])
            sep()
            line(f["price"], C["good"], bold=True)
            if f["foot"]:
                line(f["foot"], C["muted"])
            y += 8
            cv.coords(box, 0, top, w - 1, y)
            cv.configure(height=y + 1)
        cv._facts = f
        return cv

    def ins_remove_picked(self):
        if not self.ins_pick:
            return None
        key = self.ins_pick[0]
        tv = self.ins_tables[key][0]
        return self.ins_forget(tv.selection()) if key == "mine" else self.ins_forget_seen(tv.selection())

    def ins_forget_seen(self, rows):
        """2.73.2: Delete in Most expensive listings seen: hide those listings here (the Mod book keeps them)."""
        xs = [self.ins_seenmap[r] for r in rows if r in self.ins_seenmap]
        if not xs:
            return None
        hidden = SETTINGS.setdefault("ins_hidden", [])
        keys = [self.ins_seen_key(x) for x in xs]
        hidden.extend(k for k in keys if k not in hidden)
        save_json("settings.json", SETTINGS)
        label = f"{len(xs)} listing{'s' if len(xs) != 1 else ''}"

        def restore():
            for k in keys:
                if k in SETTINGS.get("ins_hidden", []):
                    SETTINGS["ins_hidden"].remove(k)
            save_json("settings.json", SETTINGS)
            self.refresh_insights()
        self.push_undo("insights", label, restore)
        self._say(f"Removed {label} from Market Insights. Ctrl+Z (or Undo) puts them back.", 8)
        self.refresh_insights()
        return len(xs)

    def ins_forget_mods(self, rows):
        """2.73.2: Delete in Mods worth the most: hide those mods here (the Mod book keeps what it learned)."""
        keys = [self.ins_modmap[r] for r in rows if r in getattr(self, "ins_modmap", {})]
        if not keys:
            return None
        hidden = SETTINGS.setdefault("ins_hidden_mods", [])
        hidden.extend(k for k in keys if k not in hidden)
        save_json("settings.json", SETTINGS)

        def restore():
            for k in keys:
                if k in SETTINGS.get("ins_hidden_mods", []):
                    SETTINGS["ins_hidden_mods"].remove(k)
            save_json("settings.json", SETTINGS)
            self.refresh_insights()
        label = f"{len(keys)} mod{'s' if len(keys) != 1 else ''}"
        self.push_undo("insights", label, restore)
        self._say(f"Removed {label} from Market Insights. Ctrl+Z (or Undo) puts them back.", 8)
        self.refresh_insights()
        return len(keys)

    @staticmethod
    def ins_seen_key(x):
        return f"{x.get('name') or x.get('base')}|{x.get('div')}|{x.get('seen')}"

    def ins_preview_at(self, key, e):
        tv = self.ins_tables[key][0]
        iid = tv.identify_row(e.y)
        obj = (self.ins_rowmap if key == "mine" else self.ins_seenmap).get(iid)
        if not obj or self.ins_pop_toggled_off(obj):
            return self.ins_preview_close()
        self.ins_preview(key, obj, e.x_root + 18, e.y_root + 10)

    @staticmethod
    def ins_with_value(text, lines):
        """2.25.3: a saved mod line with # (waystones keep their numbers as "Pack Size: #%") -> the same line from the
        copied item, with its real value ("Monster Pack Size: +32%"). Unchanged when the item text hasn't got it."""
        if "#" not in text:
            return text
        num = r"[+-]?\d+(?:\.\d+)?(?:\([^)]*\))?"           # 17 or 17(15-19) (an advanced copy)
        rx = re.compile(re.escape(text).replace(r"\#", num).replace("#", num), re.I)
        for l in lines:
            if rx.search(l):
                return l
        return text

    def ins_preview(self, key, obj, x, y):
        self.ins_preview_close()
        head, rar, mods, price, foot = self.ins_preview_item(key, obj)
        fg = self.RARITY_FG.get(rar, "#c8c8c8")
        w = tk.Toplevel(self.root)
        w.withdraw()
        w.overrideredirect(True)
        try:
            w.attributes("-topmost", True)
        except tk.TclError:
            pass
        box = tk.Frame(w, bg=C["panel"], highlightthickness=2, highlightbackground=C["accent"])
        box.pack()
        top = tk.Frame(box, bg=C["panel2"], padx=16, pady=8)
        top.pack(fill="x")
        for h in head:
            tk.Label(top, text=h, bg=C["panel2"], fg=fg, font=("Fontin SmallCaps", 13, "bold")).pack()
        body = tk.Frame(box, bg=C["panel"], padx=16, pady=8)
        body.pack(fill="x")
        for m in mods or ["(no mods saved)"]:
            tk.Label(body, text=m, bg=C["panel"], fg=C["magic"] if mods else C["muted"], font=("Segoe UI", 10),
                     wraplength=420, justify="center").pack()
        tk.Frame(box, bg=C["line"], height=1).pack(fill="x", padx=12)
        tk.Label(box, text=price, bg=C["panel"], fg=C["good"], font=("Segoe UI", 10, "bold"), pady=8).pack()
        if foot:
            tk.Label(box, text=foot, bg=C["panel"], fg=C["muted"], font=("Segoe UI", 9)).pack(pady=(0, 8))
        from .style import place_near                  # 2.25.2: on the monitor the mouse is on, not the main one
        place_near(self.root, w, x, y)
        w.deiconify()
        # (2.55.1: a click ON the box keeps it - Esc, Space or a click anywhere else closes it)
        w.bind("<Escape>", lambda e: self.ins_preview_close())
        w.bind("<space>", lambda e: self.ins_preview_close())
        self.ins_pop = w
        self.ins_pop_for = id(obj)
        self._ins_pop_hooks()
        self.ins_pop_job = self.root.after(20000, self.ins_preview_close)   # never left lying around

    def _ins_pop_hooks(self):
        """2.55.1: the item box goes away with Esc or Space, or a click anywhere that isn't on it. Set up
        once, on every window; they do nothing while no box shows (Esc then minimizes as before: app.hk_esc)."""
        if getattr(self, "_ins_hooked", False):
            return
        self._ins_hooked = True

        def key(_e):
            return "break" if self.ins_preview_dismiss() else None

        def click(e):
            w = getattr(self, "ins_pop", None)
            if w is None:
                return
            try:
                inside = str(e.widget).startswith(str(w))
            except Exception:
                inside = False
            if not inside:
                self._ins_just_closed = (getattr(self, "ins_pop_for", None), time.time())
                self.ins_preview_close()
        self.root.bind_all("<KeyPress-space>", key, add="+")
        self.root.bind_all("<ButtonPress-1>", click, add="+")
        self.root.bind_all("<ButtonPress-3>", click, add="+")

    def ins_pop_toggled_off(self, obj):
        """The click that just closed the box was on the same item: leave it closed (a second click hides it)."""
        last, self._ins_just_closed = getattr(self, "_ins_just_closed", None), None
        return bool(last) and last[0] == id(obj) and time.time() - last[1] < 0.6

    def ins_preview_dismiss(self):
        """Close the item box if one shows. -> True when it did (so the key that did it does nothing else)."""
        if getattr(self, "ins_pop", None) is None:
            return False
        self.ins_preview_close()
        return True

    def ins_preview_close(self):
        job, self.__dict__["ins_pop_job"] = getattr(self, "ins_pop_job", None), None
        if job:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        w, self.__dict__["ins_pop"] = getattr(self, "ins_pop", None), None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def ins_forget(self, rows):
        """Delete in Your most valuable: forget those items here (not in Price checks)."""
        sigs = [self.ins_rowmap[r]["sig"] for r in rows if r in self.ins_rowmap]
        gone = VALUE_LOG.remove(sigs)
        if not gone:
            return
        VALUE_LOG.save()
        label = f"{len(gone)} item{'s' if len(gone) != 1 else ''}"

        def restore():
            VALUE_LOG.restore(gone)
            VALUE_LOG.save()
            self.refresh_insights()
        self.push_undo("insights", label, restore)
        self._say(f"Removed {label} from Market Insights. Ctrl+Z (or Undo) puts them back.", 8)
        self.refresh_insights()

    def ins_price_again(self):
        if not self.ins_pick or self.ins_pick[0] != "mine":
            return
        raw = self.ins_pick[1].get("raw")
        if not raw:
            return
        old = SETTINGS.get("listen", True)
        SETTINGS["listen"] = True
        try:
            self.accept_clip(raw)
        finally:
            SETTINGS["listen"] = old
        self.shell.open("checks")

    def ins_open_search(self):
        if not self.ins_pick or self.ins_pick[0] != "seen" or not self.ins_pick[1].get("qid"):
            return
        import webbrowser
        from .wealth import wealth_trade_url
        webbrowser.open(wealth_trade_url(SETTINGS.get("league", ""), self.ins_pick[1]["qid"]))

    @staticmethod
    def _ins_empty(lbl, show, text):
        if show:
            lbl.config(text=text)
            lbl.place(relx=0.5, rely=0.5, anchor="center")
        else:
            lbl.place_forget()

    def ins_open_record(self):
        tv = self.ins_tables["mine"][0]
        sel = tv.selection()
        e = self.ins_rowmap.get(sel[0]) if sel else None
        rid = next((r["id"] for r in self.records.values() if e and sig_of(r.get("raw")) == e["sig"]), None)
        if rid is None:
            return self.ins_price_again() if e else None
        self.shell.open("checks")
        if not self.tree.exists(str(rid)):
            self.cat_reset()
            if hasattr(self, "view_var"):
                from .config import SETTINGS
                SETTINGS["view"] = "All"
                self.view_var.set("All")
            self.rebuild_tree()
        if self.tree.exists(str(rid)):
            self.tree.selection_set(str(rid))
            self.tree.see(str(rid))
            self.on_select()
