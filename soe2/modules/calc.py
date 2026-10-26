from . import Module


class Calculator(Module):
    key, title, short, icon, kind = "calc", "Calculator", "Calculator", "🧮", "tool"
    blurb = "A quick calculator: type a sum and press Enter (12k = 12,000)."

    def build(self, body):
        self.app.build_calc_window(body)

    def on_show(self):
        try:
            self.app.calc_entry.focus_set()
        except Exception:
            pass
