from . import Module


class MapLibrary(Module):
    key, title, short, icon, kind = "maps", "Map library", "Maps", "🗺", "tool"
    parent = "tracker"
    blurb = "Every map, tower, citadel and pinnacle fight - rank them S to D or Avoid, share your ranks, see the community's."

    def build(self, body):
        self.app.build_map_library(body).pack(fill="both", expand=True, padx=8, pady=8)

    def on_show(self):
        self.app.ml_fill()
