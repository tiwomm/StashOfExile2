from . import Module
from ..config import PAGE_CHECKS


class PriceChecks(Module):
    key, title, icon = "checks", PAGE_CHECKS, "⚖"
    parent = "pricecheck"              # 2.80.0 (feedback): a child of Price Checks, like Market Insights
    blurb = "Copy items in game with Ctrl+Alt+C (or read a stash tab): they are listed and priced here, many at once."

    def build(self, body):
        self.app.build_checks(body)
