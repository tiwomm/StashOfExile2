"""The UX rules a program can check (2.126.0). It opens every page, tab and Settings section of the app in a fresh,
empty data folder (nothing of yours is read or written; nothing is sent) and looks at what is on screen.

Checked (a miss fails the run):
  * One orange (primary) button per screen.
  * Beta = one BETA chip: a page marked BETA says so once.
Listed for UX round 2 (shown as "to do", they don't fail the run yet - set ENFORCE to make one fail):
  * Every icon-only button has a tooltip.
  * Every list page: the search box top left, first in the toolbar.
  * A button that needs a selection is grayed out until there is one.
Page names in Title Case and one name per feature: tools/check_names.py. A removed feature: tools/check_removed.py.

Needs a screen (on Linux, a virtual one is fine: xvfb-run python tools/check_ux.py) and the app's packages.
Run: python tools/check_ux.py   (exit 1 lists each miss, by page)."""
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENFORCE = {"orange", "beta"}
NEEDS_PICK = re.compile(r"^(Remove|Delete|Edit|Rename|Duplicate|Move)( selected)?(…|\.\.\.)?$")   # (acts on a pick)
WORD = re.compile(r"[A-Za-z0-9]")
OFFLINE = "http://127.0.0.1:9"                          # (nothing listens there: every request fails at once)


def setup_home():
    home = tempfile.mkdtemp(prefix="soe2-ux-")
    for k in ("HOME", "APPDATA", "USERPROFILE"):
        os.environ[k] = home
    os.environ["SOE2_TRADE_API"] = OFFLINE + "/api/trade2"
    os.environ["SOE2_NINJA"] = OFFLINE
    sys.path.insert(0, ROOT)
    from soe2 import __version__
    data = os.path.join(home, "StashOfExile2") if sys.platform == "win32" else os.path.join(home, ".stashofexile2")
    os.makedirs(data, exist_ok=True)
    seen = {"labs": True, "seen_version": __version__, "quickstart_done": True, "share_asked": True,
            "board_name_asked": True, "lb_name_asked": True, "wealth_setup_seen": True, "check_updates": False,
            "league": "Standard", "desecrate": {"asked": True}, "tracker": {"chips_asked": True}}
    json.dump(seen, open(os.path.join(data, "settings.json"), "w"))
    return home


def walk(w):
    yield w
    for c in w.winfo_children():
        yield from walk(c)


def shown(w):
    try:
        return bool(w.winfo_viewable())
    except Exception:
        return False


def text_of(w):
    try:
        return str(w.cget("text"))
    except Exception:
        return ""


def clickable(w, tk, ttk):
    if isinstance(w, (ttk.Button, tk.Button, ttk.Checkbutton, ttk.Menubutton, tk.Menubutton)):
        return True
    if isinstance(w, tk.Label):
        try:
            return bool(w.bind("<Button-1>")) or bool(w.bind("<ButtonRelease-1>"))
        except Exception:
            return False
    return False


def has_tip(w):
    return getattr(w, "_tip", None) is not None          # (style.Tooltip marks the widget it's on)


def look(screen, top, tk, ttk, out):
    """Every rule on one screen (a page, a tab, a Settings section)."""
    ws = [w for w in walk(top) if shown(w)]
    orange = [text_of(w) or "(icon)" for w in ws if isinstance(w, ttk.Button)
              and re.search(r"Primary|Accent", str(w.cget("style")))]
    if len(orange) > 1:
        out.append(("orange", screen, f"{len(orange)} orange buttons: {orange}"))
    beta = [w for w in ws if text_of(w).strip() in ("BETA", "(BETA)") or text_of(w).rstrip().endswith("(BETA)")]
    if len(beta) > 1:
        out.append(("beta", screen, f"{len(beta)} BETA chips"))
    for w in ws:
        if clickable(w, tk, ttk):
            t = text_of(w).strip()
            img = ""
            try:
                img = str(w.cget("image"))
            except Exception:
                pass
            if (t and not WORD.search(t) or (not t and img)) and not has_tip(w):
                out.append(("tips", screen, f"icon button {t or '(picture)'!r} has no tooltip"))
    trees = [w for w in ws if isinstance(w, ttk.Treeview)]
    if trees:
        ctrls = [w for w in ws if isinstance(w, (ttk.Entry, tk.Entry, ttk.Combobox, ttk.Button, tk.Button))]
        if ctrls:
            first = min(ctrls, key=lambda w: (w.winfo_rooty() // 12, w.winfo_rootx()))
            if not isinstance(first, (ttk.Entry, tk.Entry)) or isinstance(first, ttk.Combobox):
                out.append(("search", screen, f"list page: first in the toolbar is {text_of(first) or type(first).__name__!r}, "
                                              "not the search box"))
        if not any(t.selection() for t in trees):
            for w in ws:
                if isinstance(w, (ttk.Button, tk.Button)) and NEEDS_PICK.search(text_of(w).strip()):
                    if str(w.cget("state")) != "disabled":
                        out.append(("pick", screen, f"{text_of(w).strip()!r} is on with nothing picked"))


def main():
    setup_home()
    import tkinter as tk
    from tkinter import ttk
    from soe2.app import App
    root = tk.Tk()
    app = App(root)
    root.geometry("1500x1000+0+0")
    out = []

    def pump(n=8):
        for _ in range(n):
            root.update()

    def run():
        pump(20)
        sh = app.shell
        for key in list(sh.modules):
            if key == "settings":
                continue
            try:
                sh.open(key)
            except Exception as ex:
                out.append(("open", key, f"didn't open: {ex!r}"))
                continue
            for t in [None] + list(sh.tab_titles(key) or []):
                if t:
                    sh.open_tab(key, t)
                pump()
                look(f"{sh.modules[key].title}" + (f" › {t}" if t else ""), sh.windows[key], tk, ttk, out)
        for t in list(getattr(app, "settings_pages", {}) or []):
            sh.open("settings")
            app.open_settings_tab(t)
            pump()
            look(f"Settings › {t}", app.settings_pages[t][1], tk, ttk, out)
        root.after(50, root.destroy)

    root.after(1500, run)
    root.mainloop()
    seen = set()
    fail = 0
    for rule, screen, what in out:
        if (rule, screen, what) in seen:
            continue
        seen.add((rule, screen, what))
        on = rule in ENFORCE or rule == "open"
        fail += on
        print(("" if on else "to do: ") + f"{screen}: {what}")
    rules = {r for r, _s, _w in seen}
    print(f"check_ux: {fail} to fix" + (f", {len(seen) - fail} for UX round 2 ({', '.join(sorted(rules - ENFORCE))})"
                                         if len(seen) > fail else ""))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
