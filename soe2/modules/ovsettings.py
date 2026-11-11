from . import Module


class OverlaySettings(Module):
    """2.82.0 (feedback): the overlay's options on their own page, Overlay ↳ Overlay Settings (was a tab beside the maps)."""
    key, title, short, icon, kind = "ovset", "Overlay Settings", "Overlay Settings", "⚙", "tool"
    parent = "tracker"
    blurb = "What the overlay shows and does: its bar, features, the Campaign Helper, behavior and the Mechanic Helper."

    def build(self, body):
        self.app.build_ov_settings(body)
