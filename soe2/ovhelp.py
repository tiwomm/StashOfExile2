"""2.73.4 - 2.117: what each switch on the overlay's bar was for (a hover tip, and a card the first time one was
switched on). 2.118.0: the bar has no helper switches any more (each helper is on or off in Overlay ↳ Overlay Settings ›
Helpers, where every row says what it does), so the tips and cards are gone; Overlay ↳ Overlay Settings › Options lost its
Feature tips switch with them. What's left: opening a helper's setup (the Focus line, Test / Open in Helpers).
GGG ToS: windows only - nothing is sent to the game."""


class OverlayHelp:
    """Mixed into App."""

    def ov_intro_setup(self, key):
        try:
            if key == "focus":
                self.shell.open("plan")
                self.gp_fill()
            elif key == "campaign":
                return self.camp_route_show()
            else:
                self.tracker_helpers_settings()
            self.root.deiconify()
            self.root.lift()
        except Exception:
            self.log_error(f"opening {key}'s settings")
