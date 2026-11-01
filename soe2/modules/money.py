from . import Module


class MoneyMakers(Module):
    key, title, short, icon, kind = "money", "Money Makers", "Money", "🪙", "module"
    blurb = "Farming strats from the community, rated by effort (Thoughts per Click, Clicks per hour), and a run tracker."

    def build(self, body):
        self.app.build_money_window(body)

    def on_show(self):
        self.app.mm_on_show()
