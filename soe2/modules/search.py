from . import Module


class Search(Module):
    key, title, short, icon, kind = "search", "Game search", "Search", "🔎", "tool"
    labs = True
    blurb = "Search every skill, support, unique, base, currency, rune, modifier and keyword."

    def build(self, body):
        self.app.build_search_window(body)

    def on_show(self):
        self.app.gs_entry.focus_set()
