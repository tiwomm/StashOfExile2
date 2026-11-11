"""2.132.3 Ritual Identifier - the alert card when you hover a Ritual Altar (ritualid.py reads; hover_page.py looks).
2.132.4 (feedback: "should be part of the Ritual Helper that can be toggled on/off"): an option of the Ritual helper
(Overlay ↳ Overlay Settings › Helpers › Ritual), on with it - not a helper of its own."""
import time

from . import buglog
from . import ritualid as RID
from .config import SETTINGS, save_json

AGAIN_SECS = 120                    # the same type hovered again within this: no second card


class RitualIdPage:
    """Mixed into App."""

    def ritid_on(self):
        from . import features as FEAT
        c = self.ritual_cfg()
        return bool(c.get("on")) and bool(c.get("identify", True)) and FEAT.on("overlay")

    def ritid_changed(self, on):
        self.ritual_cfg()["identify"] = bool(on)
        save_json("settings.json", SETTINGS)
        if on:
            self.hover_start()

    def ritid_seen(self, key, now=None):
        """A type read off an altar's tooltip (or None)."""
        if not key or key not in RID.TYPES:
            return None
        now = time.time() if now is None else now
        last = getattr(self, "rid_told", None)
        if last and last[0] == key and now - last[1] < AGAIN_SECS:
            return None
        self.rid_told = (key, now)
        buglog.debug("Ritual", f"altar type {key}")
        return self.ritid_alert(key)

    def ritid_alert(self, key="tainted", test=False):
        title, sub = RID.card_text(key)
        from . import alertcard
        from .alerts_page import game_rect
        self.rid_win = alertcard.show(self.root, title, sub, color="#e05a4f", mark="☠", secs=5 if test else 10,
                                      game=game_rect(), tag="Ritual type", rank=3)
        return self.rid_win
