from . import Module


class Tracker(Module):
    key, title, short, icon, kind = "tracker", "Session tracker", "Session", "⏱", "utility"
    labs = True
    blurb = "Time, maps and profit per session, with a timer over the game."

    def build(self, body):
        self.app.build_tracker_window(body)

    def on_show(self):
        self.app.tracker_fill_history()

    def status(self):
        return self.app.tracker_status()
