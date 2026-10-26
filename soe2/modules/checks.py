from . import Module
from ..config import PAGE_CHECKS


class PriceChecks(Module):
    key, title, icon = "checks", PAGE_CHECKS, "⚖"
    blurb = "Copy an item in game with Ctrl+Alt+C: it is listed and priced here."

    def build(self, body):
        self.app.build_checks(body)
