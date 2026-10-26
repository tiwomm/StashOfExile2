from . import Module


class Regex(Module):
    key, title, icon, kind = "regex", "Regex", "✱", "tool"
    blurb = "Stash search patterns for waystones, relics and tablets (like poe2.re)."

    def build(self, body):
        self.app.build_regex_page(body)
