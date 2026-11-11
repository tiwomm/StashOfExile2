"""2.116.0 (P10, feedback: the overlay styles had cards "for a visual indicator ... if you can figure out a better
system, go for it"): Settings › Appearance › Overlay style - the styles as a list of names (grouped: Classic, Light,
Ornate) beside a big live preview of the bar in the style under the mouse (or the one picked), with one line about it.
Hovering previews without changing anything; a click (or Enter / Space) picks it - the overlay over the game changes
at once, as the old dropdown did.
2.118.0 (feedback: some previews showed the wrong colors and shapes): the preview is the real bar - drawn by the same
code as over the game (App.ov_preview), with your Colors - not a mock-up. The list and preview are pickers.ListPreview,
shared with the theme picker.
GGG ToS: it only draws in the app's own window."""
from .pickers import ListPreview

GROUPS = (("Classic", ("classic",)), ("Light", ("hairline", "slate", "flanks", "micro")),
          ("Ornate", ("herald", "gilded", "warbanner", "verdant", "gloom", "totem", "hellfire", "psionic", "guildhall")))
ABOUT = {
    "classic": "Carved stone and bronze, like the game's own bar. Takes your app theme's colors.",
    "hairline": "No box - one thin line under plain text. The lightest on the game and on the PC.",
    "slate": "A flat, quiet box.",
    "flanks": "No box: the numbers sit by the life orb, the menus by the mana orb - the middle stays clear.",
    "micro": "The smallest: the times, the rank and the menus, only as wide as they are.",
    "herald": "Crimson plates with gilt bevels.",
    "gilded": "White marble and gold leaf, umber text.",
    "warbanner": "A gold frame and royal-blue bands.",
    "verdant": "Forest green and aged bronze.",
    "gloom": "Smoky slate and pewter, pale text.",
    "totem": "Timber and red war banners.",
    "hellfire": "Rusted iron and ember gold.",
    "psionic": "Gold over deep-blue glass, cyan light.",
    "guildhall": "Oak, brass and parchment.",
}
WIDTH = 700                       # the preview: a 1440p game's XP bar, scaled to this


class StylePicker(ListPreview):
    """The style names and the real bar. render(host, style) draws it (App.ov_preview); on_pick(style) on a click."""

    def __init__(self, parent, current, on_pick, render):
        from .ovlight import STYLES
        self.styles = STYLES
        groups = [(title, [(k, STYLES[k].split(" (")[0]) for k in keys if k in STYLES]) for title, keys in GROUPS]
        super().__init__(parent, groups, current, on_pick, lambda host, st: render(host, st, WIDTH),
                         about=lambda st: ABOUT.get(st, ""), cols=2, name_width=11, preview_width=WIDTH)
