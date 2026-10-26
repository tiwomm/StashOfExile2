from . import Module


class ModBook(Module):
    key, title, icon = "modbook", "Mod book", "📖"
    blurb = "What the app learned about mod prices, and your tablet / jewel mod rules."
    hidden = True                      # 2.0 beta 21: works on its own; opened from Settings > Advanced

    def build(self, body):
        self.app.build_modbook(body)

    def on_show(self):
        self.app.refresh_rules()
        self.app.refresh_memory(True)
