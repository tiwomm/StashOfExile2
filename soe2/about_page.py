"""Settings > About (2.10.0) and the first-start quick start guide.

About: version, what's new in this version, the GitHub page, the Discord (feedback and help), the license and credits.
Quick start: a few short pages shown once, the first time the app starts (Settings > About brings it back)."""
import tkinter as tk
import webbrowser
from tkinter import ttk

from .config import APP_VERSION, pretty_version, save_json, SETTINGS
from .style import C, FONT_TITLE
from .updates import REPO

GITHUB_URL = f"https://github.com/{REPO}"
DISCORD_URL = "https://discord.gg/Ta8EVnxx4T"
DISCORD = "#5865F2"

# (title, lines). Plain words: what it's for, then how to start.
THEME_PAGE = "Pick your look"
QUICKSTART = [
    (THEME_PAGE, [
        "Choose how the app looks - click one and it changes right away. You can change it any time in "
        "Settings › Appearance.",
    ]),
    ("Welcome to StashOfExile2", [
        "A free toolkit that runs next to Path of Exile 2: it prices your items, keeps track of your maps and warns "
        "you about things that are easy to miss in game.",
        "It only reads what's yours: your clipboard, the game's own log file and your screen. It never touches the "
        "game itself, and every key does one thing.",
    ]),
    ("Price an item", [
        "Hover an item in game and press Ctrl+D. Price Checks shows what it's worth, every filter to tweak, and the "
        "trade site's listings beside it.",
        "Pricing lots of items? Press Ctrl+Alt+C on each: they're listed in Bulk Pricing with what they're worth and "
        "what to list them for.",
        "It works best on tablets, jewels and waystones. Got a whole tab of them? Bulk Pricing > Add items from > "
        "Stash tab reads it in one go.",
    ]),
    ("Find your way around", [
        "The bar on the left opens every tool. Each one is its own window: move it, resize it, keep several open.",
        "Mod book: rate the mods you care about. Regex: build stash searches. Exchange rates: what currency is "
        "worth right now.",
    ]),
    ("While you map", [
        "Overlay: time, maps and deaths per session, with a small timer over the game. Ctrl+Alt+S starts and stops "
        "it in game; F6 hides or shows the whole overlay.",
        "Overlay › Mechanic Helper can warn you when your Hiveblood is almost full (Breach) and when you finish a map with "
        "Delirium still on.",
    ]),
    ("Pick your league and say hi", [
        "Prices come from your league. The newest one is picked for you; change it here or any time in Settings.",
        "Questions, ideas or something broken? Join the Discord. Settings > About has the link, this guide and "
        "what's new.",
    ]),
]


def open_link(url):
    try:
        webbrowser.open(url)
    except Exception:
        pass


# 2.98.3: who we thank, and their GitHub pages (README › Credits says the same)
CREDITS = (
    ("RePoE (repoe-fork)", "the game data behind the mod lists, Regex, Game search and tiers - exported from Path of "
                           "Exile 2's own files.", "https://github.com/repoe-fork/repoe-fork"),
    ("poe.ninja (rasmuskl)", "the economy data: Exchange rates, the rates window over the game, Remnant prices and "
                             "currency values.", "https://github.com/rasmuskl"),
    ("Exiled Exchange 2 (Kvan7)", "general ideas, and the base types, mod wordings, trade-site stat ids and "
                                  "pseudo-total rules in gamedata.json, from its data files under its MIT license. "
                                  "Nothing else of it is used.", "https://github.com/Kvan7/Exiled-Exchange-2"),
    ("Sidekick", "general ideas. None of its code is used.", "https://github.com/Sidekick-Poe/Sidekick"),
    ("hypr-exiled (gfsd3v)", "the idea for the Trade Whisper Watcher - ours is built from scratch, none of its code "
                             "is used.", "https://github.com/gfsd3v/hypr-exiled"),
    ("Path of Building PoE2", "the anoint recipes.", "https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2"),
    ("Cinzel (Natanael Gama)", "a font of the ornate overlay styles. SIL Open Font License.",
     "https://github.com/NDISCOVER/Cinzel"),
    ("EB Garamond (Georg Duffner, Octavio Pardo)", "a font of the ornate overlay styles. SIL Open Font License.",
     "https://github.com/octaviopardo/EBGaramond12"),
    ("Cormorant (Christian Thalmann)", "the fonts of the Gloom overlay style. SIL Open Font License.",
     "https://github.com/CatharsisFonts/Cormorant"),
    ("Marcellus SC (Brian J. Bonislawsky, Astigmatic)", "the font of the Warbanner overlay style. SIL Open Font "
                                                        "License.", "https://github.com/google/fonts/tree/main/ofl/marcellussc"),
    ("Marcellus (Brian J. Bonislawsky, Astigmatic)", "the Psionic overlay style's text. SIL Open Font License.",
     "https://github.com/google/fonts/tree/main/ofl/marcellus"),
    ("Metamorphous (Sorkin Type)", "the font of the Hellfire overlay style. SIL Open Font License.",
     "https://github.com/google/fonts/tree/main/ofl/metamorphous"),
    ("IM FELL English SC (Igino Marini)", "the font of the Guildhall overlay style. SIL Open Font License.",
     "https://github.com/google/fonts/tree/main/ofl/imfellenglishsc"),
)


class AboutPage:
    """Mixed into App."""

    # ================================================================ Settings > About
    def build_about(self, wrap):
        from .whatsnew import notes_between, plain_lines
        P1, P2 = C["panel"], C["panel2"]
        head = tk.Frame(wrap, bg="#1a2a4c", padx=16, pady=16, highlightthickness=1, highlightbackground=C["line"])
        head.pack(fill="x", pady=(0, 8))
        tk.Label(head, text="StashOfExile2", bg="#1a2a4c", fg="#ffffff", font=(FONT_TITLE, 18, "bold"),
                 anchor="w").pack(fill="x")
        from .config import TAGLINE
        tk.Label(head, text=TAGLINE, bg="#1a2a4c", fg="#ffd9a8", font=(FONT_TITLE, 12, "italic"),
                 anchor="w").pack(fill="x")                                               # 2.73.2
        tk.Label(head, text=f"Version {pretty_version()}  ·  a toolkit for Path of Exile 2  ·  free and open source "
                            "(GPL-3.0)", bg="#1a2a4c", fg="#9fb6dd", anchor="w").pack(fill="x")
        btns = tk.Frame(head, bg="#1a2a4c")
        btns.pack(fill="x", pady=(8, 0))
        self.about_discord = tk.Label(btns, text="  💬  Join the Discord  ", bg=DISCORD, fg="#ffffff", cursor="hand2",
                                      font=("Segoe UI", 12, "bold"), padx=8, pady=8)
        self.about_discord.pack(side="left")
        self.about_discord.bind("<Button-1>", lambda e: open_link(DISCORD_URL))
        self.about_discord.bind("<Enter>", lambda e: self.about_discord.config(bg="#4752c4"))
        self.about_discord.bind("<Leave>", lambda e: self.about_discord.config(bg=DISCORD))
        ttk.Button(btns, text="GitHub page", command=lambda: open_link(GITHUB_URL), style="Quiet.TButton").pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Quick start guide", command=lambda: self.show_quickstart(force=True)).pack(side="left",
                                                                                                      padx=(8, 0))
        tk.Label(wrap, text="The Discord is the place for questions, ideas and bug reports. Code, releases and the "
                            "roadmap are on GitHub.", bg=P1, fg=C["muted"], font=("Segoe UI", 9), anchor="w",
                 justify="left", wraplength=620).pack(fill="x", pady=(0, 8))

        box = tk.Frame(wrap, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
        box.pack(fill="x", pady=(0, 8))
        tk.Label(box, text=f"What's new in {pretty_version()}", bg=P2, fg=C["accent"], font=("Segoe UI", 12, "bold"),
                 anchor="w").pack(fill="x")
        notes = plain_lines(dict(notes_between(None, APP_VERSION)).get(APP_VERSION) or ["(nothing listed)"])
        for line in notes:
            tk.Label(box, text="•  " + line, bg=P2, fg=C["text"], anchor="w", justify="left", wraplength=600,
                     font=("Segoe UI", 9)).pack(fill="x", pady=(4, 0))
        more = tk.Label(box, text="Every version's notes", bg=P2, fg=C["accent"], cursor="hand2",
                        font=("Segoe UI", 9, "underline"), anchor="w")
        more.pack(fill="x", pady=(8, 0))
        more.bind("<Button-1>", lambda e: self.show_whatsnew(True))

        box = tk.Frame(wrap, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
        box.pack(fill="x", pady=(0, 8))
        tk.Label(box, text="About this app", bg=P2, fg=C["accent"], font=("Segoe UI", 12, "bold"),
                 anchor="w").pack(fill="x")
        for line in (
                "Written with AI (Claude), and open about it. Anyone may use it, change it and share it under the "
                "GPL-3.0 license.",
                "It only reads your clipboard, the game's log file (Client.txt) and your screen - never the game's "
                "memory - and it respects the trade site's limits. One key press = one action.",
                "Prices come from the official trade site and poe.ninja. Not affiliated with or endorsed by Grinding "
                "Gear Games."):
            tk.Label(box, text=line, bg=P2, fg=C["text"], anchor="w", justify="left", wraplength=600,
                     font=("Segoe UI", 9)).pack(fill="x", pady=(4, 0))
        # 2.98.3 (feedback): credit where it's due - each with a link to its developers' GitHub page
        box = tk.Frame(wrap, bg=P2, padx=16, pady=8, highlightthickness=1, highlightbackground=C["line"])
        box.pack(fill="x", pady=(0, 8))
        tk.Label(box, text="Credits - thank you!", bg=P2, fg=C["accent"], font=("Segoe UI", 12, "bold"),
                 anchor="w").pack(fill="x")
        from .remnant import CREDIT_NAME, CREDIT_URL
        for name, what, url in CREDITS + ((CREDIT_NAME, "the idea for the Expedition Remnant Price Checker. None of "
                                                        "its code is used (it isn't open source).", CREDIT_URL),):
            row = tk.Frame(box, bg=P2)
            row.pack(fill="x", pady=(8, 0))
            ln = tk.Label(row, text=name + " ›", bg=P2, fg=C["blue"], anchor="w", font=("Segoe UI", 9, "bold"),
                          cursor="hand2")
            ln.pack(anchor="w")
            ln.bind("<Button-1>", lambda e, u=url: open_link(u))
            tk.Label(row, text=what, bg=P2, fg=C["text"], anchor="w", justify="left", wraplength=600,
                     font=("Segoe UI", 9)).pack(fill="x")

    # ================================================================ quick start (first start)
    def show_quickstart(self, force=False):
        """-> True if it was shown. Once, on a fresh install (no seen_version yet), or when asked."""
        if not force and (SETTINGS.get("quickstart_done") or SETTINGS.get("seen_version")):
            return False
        old = getattr(self, "_whatsnew", None)
        if old is not None and old.winfo_exists():
            old.destroy()
        P1, P2 = C["panel"], C["panel2"]
        card = tk.Toplevel(self.root, bg=C["accent"], padx=2, pady=2)
        card.overrideredirect(True)
        try:
            card.transient(self.root)
        except tk.TclError:
            pass
        self._whatsnew = card                   # same place / follow / keep-on-top as the what's new card
        self._wn_h = 420
        self.whatsnew_follow()
        inner = tk.Frame(card, bg=P1)
        inner.pack(fill="both", expand=True)
        head = tk.Frame(inner, bg="#1a2a4c", padx=16, pady=12)
        head.pack(fill="x")
        self.qs_title = tk.Label(head, text="", bg="#1a2a4c", fg="#ffffff", font=(FONT_TITLE, 16, "bold"), anchor="w")
        self.qs_title.pack(fill="x")
        self.qs_step = tk.Label(head, text="", bg="#1a2a4c", fg="#9fb6dd", anchor="w")
        self.qs_step.pack(fill="x")
        foot = tk.Frame(inner, bg=P1, padx=16, pady=8)
        foot.pack(fill="x", side="bottom")
        self.qs_next = ttk.Button(foot, text="Next", style="Primary.TButton", command=lambda: self.quickstart_go(1))
        self.qs_next.pack(side="right")
        self.qs_back = ttk.Button(foot, text="Back", command=lambda: self.quickstart_go(-1), style="Quiet.TButton")
        self.qs_back.pack(side="right", padx=8)
        ttk.Button(foot, text="Skip", command=self.quickstart_done, style="Quiet.TButton").pack(side="left")
        self.qs_body = tk.Frame(inner, bg=P2, padx=16, pady=16, highlightthickness=1, highlightbackground=C["line"])
        self.qs_body.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        self.qs_i = 0
        self.quickstart_go(0)
        card.lift()
        return True

    def quickstart_go(self, step):
        n = len(QUICKSTART)
        if step > 0 and self.qs_i == n - 1:
            return self.quickstart_done()
        self.qs_i = max(0, min(n - 1, self.qs_i + step))
        title, lines = QUICKSTART[self.qs_i]
        self.qs_title.config(text=title)
        self.qs_step.config(text=f"Quick start  ·  {self.qs_i + 1} of {n}  ·  version {pretty_version()}")
        P2 = C["panel2"]
        for w in self.qs_body.winfo_children():
            w.destroy()
        for line in lines:
            tk.Label(self.qs_body, text=line, bg=P2, fg=C["text"], anchor="w", justify="left", wraplength=560,
                     font=("Segoe UI", 10)).pack(fill="x", pady=(0, 8))
        want_h = 600 if title == THEME_PAGE else 420             # 2.61.0: the theme cards need more room
        if getattr(self, "_wn_h", None) != want_h:
            self._wn_h = want_h
            self.whatsnew_follow()
        if title == THEME_PAGE:                                  # 2.61.0: a fresh install starts by picking a theme
            self.theme_cards(self.qs_body, "quickstart", cols=4, scale=0.78)
        if self.qs_i == n - 1:
            row = tk.Frame(self.qs_body, bg=P2)
            row.pack(fill="x", pady=(8, 0))
            tk.Label(row, text="League", bg=P2, fg=C["accent"], font=("Segoe UI", 12, "bold")).pack(side="left")
            self.wn_league = self.league_link(row, P2)          # 2.59.0: set in Settings › General
            self.wn_league.pack(side="left", padx=8)
            tk.Label(row, text="(click to change)", bg=P2, fg=C["muted"], font=("Segoe UI", 9)).pack(side="left")
            d = tk.Label(self.qs_body, text="  💬  Join the Discord  ", bg=DISCORD, fg="#ffffff", cursor="hand2",
                         font=("Segoe UI", 12, "bold"), pady=8)
            d.pack(anchor="w", pady=(16, 0))
            d.bind("<Button-1>", lambda e: open_link(DISCORD_URL))
        self.qs_back.config(state="normal" if self.qs_i else "disabled")
        self.qs_next.config(text="Done" if self.qs_i == n - 1 else "Next")

    def quickstart_done(self):
        SETTINGS["quickstart_done"] = True
        save_json("settings.json", SETTINGS)
        self.close_whatsnew()
