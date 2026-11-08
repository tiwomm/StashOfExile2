from . import Module


class RateMods(Module):
    """2.120.0 (UX pass 2, feedback: the Rate mods window drew badly and sat in Privacy & community): its own page
    under Price Checks - the item kinds on the left, one mod at a time on the right."""
    key, title, short, icon, kind = "ratemods", "Rate Mods", "Rate Mods", "⭐", "tool"
    parent = "pricecheck"
    blurb = "Rate how much each mod matters to an item's price - your price checks use it at once."

    def build(self, body):
        self.app.build_ratemods_page(body)

    def on_show(self):
        self.app.rm_on_show()
