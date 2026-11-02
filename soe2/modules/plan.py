from . import Module


class GamePlan(Module):
    key, title, short, icon, kind = "plan", "Game Plan", "Plan", "🎯", "tool"
    parent = "tracker"
    blurb = ("League Focus: your goals by phase, a stockpile to buy while it's cheap, your farm plan and a build lock - "
             "set it once, the overlay brings it back when it matters.")

    def build(self, body):
        self.app.build_game_plan(body).pack(fill="both", expand=True)

    def on_show(self):
        self.app.gp_fill()
