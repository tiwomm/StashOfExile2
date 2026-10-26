from . import Module


class Wealth(Module):
    key, title, icon = "wealth", "Wealth", "💰"
    labs = True
    blurb = "What your stash is worth, tab by tab."

    def build(self, body):
        self.app.build_wealth_page(body)

    def on_show(self):
        self.app.refresh_wealth(True)
