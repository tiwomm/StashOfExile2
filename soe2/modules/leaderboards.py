from . import Module


class Leaderboards(Module):
    """2.86.0: Overlay ↳ Leaderboards - campaign, maps, bosses and trials; yours and everyone's."""
    key, title, short, icon, kind = "leaderboards", "Leaderboards", "Leaderboards", "🏆", "tool"
    parent = "tracker"
    blurb = "Your fastest campaign acts, maps, pinnacle fights and trials - and everyone's (Community data sharing)."

    def build(self, body):
        self.app.build_leaderboards(body)

    def on_show(self):
        self.app.lb_refresh(send=True)
