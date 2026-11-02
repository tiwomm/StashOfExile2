"""The toolkit's modules and utilities (2.0 beta 7). Each one is a small class in its own file here:

    key     - its id (window layout is saved under it)
    title   - shown on its window, the dock tooltip and the Toolkit menu
    icon    - one character / emoji for the dock, taskbar and menu
    kind    - "module" (a big tool you work in: Price checks, Mod book ...), "tool" (a quick helper that only does
              something while its window is open: Regex, Exchange rates, Game search), "utility" (keeps working in or
              over the game while its window is closed, with an on/off dot: chat commands, notes,
              session tracker) or "core" (Settings: not on the dock)
    hidden  - True: not on the dock, the Toolkit menu or the desktop; opened from inside another window only
              (2.0 beta 14: Under the hood, opened from Price checks)
    labs    - True for an experimental (Labs) one: only shown when Labs is on in Settings, tagged BETA
    beta    - True to tag it BETA but show it always (2.38.0: Money Makers)
    blurb   - one line about it (dock tooltip, menu search)
    build(body)  - draw its content into its window's body (called once at start-up; windows that are closed are
                   only hidden, so a module is always there for the rest of the app)
    on_show()    - its window was opened or brought back
    status()     - utilities: True (on) / False (off) / "warn" (needs attention) -> the dots on the dock and taskbar

Who we build for (2.47.0, the user): Path of Exile players are utilitarian - data, information, problem solving,
creative thinking. Show the numbers and how they were worked out; sort / filter / compare / export (CSV); keep the
depth one click away; plain words; the player decides.

How the app is organized (2.33.0 - the rule for every module, see ROADMAP.md):
  * top level (dock, desktop, Toolkit menu): things you open on their own;
  * a child tool (parent = "<key>") is built on ONE module's data and used while working in it. It is never on the
    dock; it is a button in the parent window's title bar, sits indented under the parent in the Toolkit menu, and
    its window is titled "Parent › Child";
  * tabs inside a window are for views of the same thing that fit in one window; anything that needs its own lists
    and actions becomes a child tool.
  hidden = True is only for windows that are opened from inside another window and belong nowhere else.

The shell (shell.py) hosts them; to add one, write a file here and add its class to MODULES."""


class Module:
    key = ""
    title = ""
    short = ""
    icon = "•"
    kind = "module"
    blurb = ""
    hidden = False
    beta = False        # 2.38.0: tagged BETA, still shown (labs: hidden unless Labs is on)
    parent = None       # 2.33.0: a child tool's parent module (see "How the app is organised" below)

    def __init__(self, app):
        self.app = app
        self.body = None

    def build(self, body):
        pass

    def on_show(self):
        pass

    def status(self):
        return None


def load(app):
    from .checks import PriceChecks
    from .wealth import Wealth
    from .modbook import ModBook
    from .library import Library
    from .regex import Regex
    from .notes import Notes
    from .rates import Rates
    from .tracker import Tracker
    from .search import Search
    from .settings import Settings
    from .calc import Calculator
    from .insights import Insights
    from .money import MoneyMakers
    from .maps import MapLibrary
    return [cls(app) for cls in (PriceChecks, Wealth, ModBook, Library, Regex, Search, Tracker, Notes,
                                 Rates, Calculator, Insights, MoneyMakers, MapLibrary, Settings)]
