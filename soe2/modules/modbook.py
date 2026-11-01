from . import Module


class ModBook(Module):
    key, title, icon = "modbook", "Mod book", "📖"
    blurb = "What the app learned about mod prices, and your tablet / jewel mod rules."
    parent = "checks"                  # 2.33.0: a child tool of Price checks (was hidden; Settings > Advanced opens it too)

    def build(self, body):
        self.app.build_modbook(body)

    def on_show(self):
        self.app.refresh_rules()
        self.app.refresh_memory(True)
