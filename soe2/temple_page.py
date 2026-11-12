"""2.132.1 Temple Helper - the watcher (a look round the mouse in maps, for the Vaal Beacon's tooltip), the crystals
on the line above the bar (2.132.2, with Ritual's - the bar had no room) and the alert card when they're full; its row in Overlay ↳ Overlay Settings › Helpers (temple.py reads)."""
from . import buglog
from . import temple as TM
from .config import SETTINGS, save_json


class TemplePage:
    """Mixed into App."""

    def temple_on(self):
        from . import features as FEAT
        return bool(TM.cfg().get("on")) and FEAT.on("overlay") and FEAT.on("temple")     # (2.132.2: BETA)

    def temple_set(self, on):
        TM.cfg()["on"] = bool(on)
        from . import features as FEAT
        FEAT.beta_on("temple", bool(on))
        save_json("settings.json", SETTINGS)
        if on:
            self.temple_start()
            if getattr(self, "br_reader", None) is None:    # (the game's log says when you're in a map)
                try:
                    self.breach_start()
                except Exception:
                    buglog.caught()
        try:
            self.merged_build()                             # (the bar's crystals part comes / goes)
        except Exception:
            buglog.caught()

    def temple_start(self):
        self.hover_start()                                  # 2.132.3: one look round the mouse feeds every reader

    def temple_look(self, force=False):
        return self.hover_look(force)

    def temple_seen(self, got):
        """A read (have, most) or None (no tooltip there)."""
        if not got:
            return None
        old = TM.state()
        st = TM.state_set(*got)
        if not old or (old["have"], old["most"]) != got:
            buglog.debug("Temple", f"crystals {got[0]}/{got[1]}")
            try:
                self.ritual_readout_sync()
            except Exception:
                buglog.caught()
        if TM.full(st) and not (old and TM.full(old) and getattr(self, "tm_told", False)):
            self.temple_alert(st)
        elif not TM.full(st):
            self.tm_told = False
        return st

    def temple_alert(self, st=None, test=False):
        """Crystals full: a vital alert card (red words)."""
        st = st or TM.state() or {"have": 60, "most": 60}
        self.tm_told = True
        from . import alertcard
        from .alerts_page import game_rect
        self.tm_win = alertcard.show(self.root, "Crystals full", f"Energised Beacons {st['have']}/{st['most']} "
                                     f"({TM.runs(st)} runs). Placed rooms stay until destabilized.", color="#d9a441", mark="◆", secs=5 if test else 10,
                                     game=game_rect(), tag="Temple", rank=1, vital=True)
        return self.tm_win
