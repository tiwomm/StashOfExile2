from . import Module


class Insights(Module):
    key, title, short, icon, kind = "insights", "Market Insights", "Insights", "💎", "tool"
    labs = True
    parent = "checks"                  # 2.33.0: built on your price checks - a child tool of Price checks
    blurb = "The most valuable tablets, waystones and jewels your price checks found, and the mods worth the most."

    def build(self, body):
        self.app.build_insights_window(body)

    def on_show(self):
        self.app.refresh_insights()
