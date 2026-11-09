"""2.117.0: every one-time change to your settings and data in one ordered list (they were spread over app.py,
config.py and market.py, each with its own "done" flag).

A step runs once per PC, in order, at its stage:
  * "settings" - when settings.json is loaded (config.py), before any window
  * "app"      - when the app starts, after your data is loaded and before the windows are built
Done steps are listed in SETTINGS["migrations_done"]. A step that was done before 2.117.0 under its old flag
(`legacy`) counts as done - the flag is kept, so an older build put back on the PC doesn't run it again. A step that
fails goes to the app's log and is tried again next start, at most TRIES times; then it's left (and logged).
Settings are saved once, after the stage.

Adding one: a function at the end of STEPS - ("short_id", "version", "stage", fn, legacy flag or None). fn returns
nothing; it changes SETTINGS (and saves its own data files). Never reorder or rename one that has shipped.

The data files' own format upgrades (ledger.json, moneymakers, mod rule keys) stay with the code that reads them -
they run on every load and change nothing once a file is up to date. The overlay's own settings (overlay.json) keep
their steps in tracker_page.py / overlay.py."""
from . import buglog

TRIES = 3


# ---------------------------------------------------------------- the steps (oldest first)
def _rules_scoped(S):
    """2.6.0: waystone / relic rules set from Regex move to their own names (mods.migrate_scoped_rules)."""
    from . import regex as R
    from .config import save_json
    from .mods import RULES, migrate_scoped_rules

    def lines(kind):
        return [ln for m in R.mods(kind) for ln in (m.get("lines") or [m["line"]])]
    if migrate_scoped_rules(lines("waystone"), lines("relic")):
        save_json("mod_rules.json", RULES)


def _status_ib(S):
    """2.79.2 (feedback): the default seller is Instant Buyout."""
    S["status"] = "Instant Buyout"


def _copy_hotkey_only(S):
    """2.98.3: One-key copy and "Other ways of copying" are gone - Bulk Pricing adds only your own Ctrl+Alt+C."""
    S["quick_copy_key"] = ""
    S["hotkey_only"] = True


def _gear_plus(S):
    """2.99.0: gear rules lose their leading "+" (Mod book › Gear rules lists lines without one)."""
    from .config import save_json
    from .gearbook import migrate_plus
    from .mods import RULES, TIERS
    if migrate_plus(RULES, TIERS):
        save_json("mod_rules.json", RULES)
        save_json("mod_tiers.json", TIERS)


def _tier_only(S):
    """2.114.0: one rating - a tier you gave decides High / Normal (S / A = High, B-D = Normal)."""
    from .config import save_json
    from .mods import RULES, TIERS, migrate_tier_only
    if migrate_tier_only():
        save_json("mod_rules.json", RULES)
        save_json("mod_tiers.json", TIERS)


def _modbook_import(S):
    """1.x mod book (modbook.json) into the market's database, once."""
    from .config import MODBOOK
    from .market import MARKET
    if MODBOOK:
        MARKET.import_old_modbook(MODBOOK, float(S.get("good_div", 0.5)))


def _ux_2119(S):
    """2.119.0 (UX pass): settings that are gone - Pace (always the old Balanced), Accent color and Text size (a theme
    keeps its own look), the start-up screen switch (always shown), "The overlay only while Path of Exile 2 is in
    front" (always) and Expedition's Auto switch and key (always Auto)."""
    for k in ("pace", "accent", "ui_scale", "splash", "overlay_game_only"):
        S.pop(k, None)
    rm = S.get("remnant")
    if isinstance(rm, dict):
        rm.pop("auto", None)
        rm.pop("key", None)


def _no_recap_2124(S):
    """2.124.0: the joke Death Recap card is gone; the lines over the bar are part of the overlay now (no Dock
    switch, no spot of their own)."""
    S.pop("recap_seen", None)
    t = S.get("tracker")
    if isinstance(t, dict):
        t.pop("goal_dock", None)
        t.pop("goal_pos", None)


def _cols_2125(S):
    """2.125.3: Bulk Pricing shows every column (Columns ▾ turns them off); the old "extra columns on" list goes, and
    the Item column's remembered width (it hid the columns after it)."""
    S.pop("bulk_cols", None)
    cw = S.get("col_widths")
    if isinstance(cw, dict):
        cw.pop("name", None)


def _pc_settings_2125(S):
    """2.125.5 (feedback): Price checking lost Valuable mods (the app's amount again), Skip cheap items (gone) and the
    two "in the app" choices of Where the price shows but Here (the app comes to the front)."""
    from .config import DEFAULTS
    S["good_div"] = DEFAULTS["good_div"]                 # (still read - the app's own amount, no setting)
    S.pop("floor", None)
    S["pc_front"] = True


def _shortcuts_2126(S):
    """2.125.6 (feedback): Bulk Pricing's shortcuts (skip a search the Mod Book agrees on; the model prices by itself)
    are gone - every item is searched."""
    S.pop("memory_shortcut", None)
    S.pop("model_shortcut", None)


STEPS = (
    ("modbook_import", "1.x", "app", _modbook_import, "modbook_imported"),
    ("rules_scoped", "2.6.0", "app", _rules_scoped, "rules_scoped_26"),
    ("status_ib", "2.79.2", "settings", _status_ib, "status_ib_2792"),
    ("copy_hotkey_only", "2.98.3", "app", _copy_hotkey_only, "copy_2983"),
    ("gear_plus", "2.99.0", "app", _gear_plus, "gear_plus_299"),
    ("tier_only", "2.114.0", "app", _tier_only, "tier_only_2114"),
    ("ux_2119", "2.119.0", "settings", _ux_2119, None),
    ("no_recap_2124", "2.124.0", "settings", _no_recap_2124, None),
    ("cols_2125", "2.125.3", "settings", _cols_2125, None),
    ("pc_settings_2125", "2.125.5", "settings", _pc_settings_2125, None),
    ("shortcuts_2126", "2.125.6", "settings", _shortcuts_2126, None),
)


# ---------------------------------------------------------------- the runner
def pending(S, stage=None):
    """The steps not done yet (of one stage, or all)."""
    done = set(S.get("migrations_done") or [])
    return [s for s in STEPS if s[0] not in done and not (s[4] and S.get(s[4])) and (stage is None or s[2] == stage)]


def run(S, stage, save=None):
    """Run this stage's steps not done yet, in order. -> [ids done now]. Never raises."""
    done_now = []
    try:
        todo = pending(S, stage)
    except Exception:
        buglog.record("error", "migrations: reading what's done", exc=True)
        return done_now
    if not todo:
        return done_now
    done = list(S.get("migrations_done") or [])
    tries = dict(S.get("migrations_tries") or {})
    for sid, ver, _stage, fn, legacy in todo:
        try:
            fn(S)
        except Exception:
            tries[sid] = tries.get(sid, 0) + 1
            gave_up = tries[sid] >= TRIES
            buglog.record("error", f"settings update {sid} ({ver})" + (" - tried 3 times, left" if gave_up else ""),
                          exc=True)
            if not gave_up:
                continue
        done.append(sid)
        done_now.append(sid)
        tries.pop(sid, None)
        if legacy:
            S[legacy] = True                    # (an older build put back on this PC skips it too)
    S["migrations_done"] = done
    if tries:
        S["migrations_tries"] = tries
    else:
        S.pop("migrations_tries", None)
    if save is not None:
        try:
            save()
        except Exception:
            buglog.record("error", "migrations: saving settings", exc=True)
    return done_now
