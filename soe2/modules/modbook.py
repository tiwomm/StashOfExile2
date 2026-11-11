from . import Module


class ModBook(Module):
    key, title, icon = "modbook", "Mod Book", "📖"
    blurb = "What the app learned about mod prices, and your tablet / jewel mod rules."
    parent = "library"                 # 2.74.0: inside Under the hood (was a child of Price checks)
    advanced = True                    # only with Settings › Advanced › Show Under the hood

    def build(self, body):
        self.app.build_modbook(body)

    def on_show(self):
        self.app.refresh_rules()
        self.app.refresh_memory(True)
