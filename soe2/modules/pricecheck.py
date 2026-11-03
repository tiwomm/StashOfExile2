from . import Module
from ..config import PAGE_PC


class PriceCheck(Module):
    """2.80.0: one item at a time - its card with every filter, and the trade site's listings beside it."""
    key, title, icon = "pricecheck", PAGE_PC, "🔍"
    blurb = "Hover an item in game and press Ctrl+C: its price and the trade site's listings show here."

    def build(self, body):
        self.app.build_pc(body)
