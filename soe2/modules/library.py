from . import Module


class Library(Module):
    key, title, short, icon, kind = "library", "Under the hood", "Under the hood", "⚙", "tool"
    blurb = "How the price checker reads an item and what it compares it with (opened from Price checks)."
    hidden = True                      # 2.0 beta 14: part of Price checks, not a tool of its own

    def build(self, body):
        self.app.build_library_page(body)

    def on_show(self):
        self.app.refresh_library(True)
