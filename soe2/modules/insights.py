from . import Module


class Insights(Module):
    key, title, short, icon, kind = "insights", "Top value", "Top value", "💎", "tool"
    labs = True
    blurb = "The most valuable tablets, waystones and jewels your price checks found, and the mods worth the most."

    def build(self, body):
        self.app.build_insights_window(body)

    def on_show(self):
        self.app.refresh_insights()
