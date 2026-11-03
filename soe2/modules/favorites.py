from . import Module


class Favorites(Module):
    """2.84.0: items and trade-site searches you come back to - each opens like Price Checks."""
    key, title, short, icon, kind = "favorites", "Favorites", "Favorites", "★", "tool"
    parent = "pricecheck"
    blurb = "Items from Price Checks and pasted trade links you come back to, in your own groups and order."

    def build(self, body):
        self.app.build_favorites(body)

    def on_show(self):
        self.app.fav_fill()
