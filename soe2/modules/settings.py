from . import Module


class Settings(Module):
    key, title, icon, kind = "settings", "Settings", "⚙", "core"
    blurb = "League, search pace, always on top, wallpaper, updates."

    def build(self, body):
        self.app.build_settings(body)
