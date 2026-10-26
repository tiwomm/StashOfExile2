from . import Module


class Rates(Module):
    key, title, short, icon, kind = "rates", "Exchange rates", "Rates", "💱", "tool"
    blurb = "What each currency is worth in divines (poe.ninja), and a converter."

    def build(self, body):
        self.app.build_rates_window(body)

    def on_show(self):
        self.app.draw_rates()

    def status(self):
        return self.app.rates_status_dot()
