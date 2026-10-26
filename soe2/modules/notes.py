from . import Module


class Notes(Module):
    key, title, short, icon, kind = "notes", "Notes", "Notes", "📝", "utility"
    blurb = "A sticky note over the game, shown and hidden with a key."

    def build(self, body):
        self.app.build_notes_window(body)

    def on_show(self):
        self.app.util_refresh()

    def status(self):
        return self.app.notes_status()
