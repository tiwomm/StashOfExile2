from . import Module


class Delirium(Module):
    key, title, short, icon, kind = "delirium", "Delirium alert", "Delirium", "⏳", "utility"
    blurb = "A big END DELIRIUM banner when you finish a map with Delirium still running."

    def build(self, body):
        self.app.build_delirium_window(body)

    def on_show(self):
        self.app.util_refresh()

    def status(self):
        return self.app.delirium_status()
