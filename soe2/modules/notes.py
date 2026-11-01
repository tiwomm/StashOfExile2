from . import Module


class Notes(Module):
    key, title, short, icon, kind = "notes", "Notes", "Notes", "📝", "utility"
    blurb = "A sticky note over the game, shown and hidden with a key."
    hidden = True       # 2.44.0: a tab of Overlays now - opening "notes" opens Overlays › Notes (shell.open)

    def build(self, body):
        pass

    def on_show(self):
        self.app.util_refresh()

    def status(self):
        return self.app.notes_status()
