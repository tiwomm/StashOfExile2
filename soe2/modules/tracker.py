from . import Module


class Tracker(Module):
    # 2.44.0: "Overlays" (was Session tracker) - the Session timer, the Mechanic Helper, Notes and their Look in one
    # window. The key stays "tracker" (saved window places, older settings).
    key, title, short, icon, kind = "tracker", "Overlays", "Overlays", "⏱", "utility"
    blurb = "Over the game: the Session timer (time, maps, profit), the Mechanic Helper, Notes - and how they look."

    def build(self, body):
        self.app.build_overlays_hub(body)

    def on_show(self):
        self.app.tracker_fill_history()

    def status(self):
        return self.app.tracker_status()
