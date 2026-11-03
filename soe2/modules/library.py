from . import Module


class Library(Module):
    key, title, short, icon, kind = "library", "Under the hood", "Under the hood", "⚙", "tool"
    blurb = "How the price checker reads an item and what it compares it with (opened from Price checks)."
    parent = "pricecheck"              # 2.33.0: a child tool (was hidden); 2.80.0: under Price Checks
    advanced = True                    # 2.74.0: only with Settings › Advanced › Show Under the hood

    def build(self, body):
        self.app.build_library_page(body)

    def on_show(self):
        self.app.refresh_library(True)
