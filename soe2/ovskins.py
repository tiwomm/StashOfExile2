"""Ornate overlay styles (2.110.0, wave 1 - from the mockups the user picked): Herald, Gilded, Warbanner, Verdant
and Gloom; 2.111.0, wave 2: Totem, Hellfire, Psionic and Guildhall. Each is a skin over the Slate layout (ovlight.py): its own colours, bundled fonts (fonts.py), frame,
corner marks, title band and tab-like switches. The windows over the game (Notes, Calc, Regex favorites, Rates,
cards) take the same skin through overlaywin.pal() -> App.ov_palette().

  herald     lacquered crimson title plates, a gilt line, brushed-iron tabs (amber when on)
  gilded     sunlit white marble, a gold-leaf frame, umber text
  warbanner  a heavy bevelled gold frame with corner caps, royal-blue title bands, gold lettering
  verdant    deep forest green, a double aged-bronze line, parchment text
  gloom      smoky slate, pewter hairlines, ghost-pale small caps
  (2.111.0, wave 2)
  totem      a war camp: timber frame, red war-banner title bands, hide tabs (red when on)
  hellfire   rusted iron, rivets, ember-gold gothic lettering
  psionic    curved gold over deep-blue glass, cyan crystal light
  guildhall  honey oak and brass, a hanging shop-sign title, parchment tabs

GGG ToS: looks only - windows of the app's own; nothing here touches the game."""
from .fonts import family
from .overlaywin import _P

ORNATE = ("herald", "gilded", "warbanner", "verdant", "gloom", "totem", "hellfire", "psionic", "guildhall")
NAMES = {"herald": "Herald", "gilded": "Gilded", "warbanner": "Warbanner", "verdant": "Verdant", "gloom": "Gloom",
         "totem": "Totem", "hellfire": "Hellfire", "psionic": "Psionic", "guildhall": "Guildhall"}

# per skin: colours, fonts, frame, title band and switch (tab) colours
SKINS = {
    "herald": dict(bg="#141210", band="#6a0a0e", band_grad=("#9a1418", "#7a0e12", "#8a1014", "#5e080c", "#3e0508"),
                   head="#f2e2bc", text="#ece4d4", big="#f2e2bc", muted="#b8ae9c", accent="#e8a44a", line="#5a4a32",
                   leather="#141210", edge="#000000", border=2, frame2="#c9a86a", corners="#e6c88a", field="#0c0a09",
                   on_bg="#3a3632", on_fg="#e8a44a", off_bg="#1a1816", off_fg="#a8a29a", font="Cinzel",
                   body="EB Garamond"),
    "gilded": dict(bg="#efe6d2", band="#f6efe0", band_grad=None, head="#7a4a0a", text="#2a1c0c", big="#4a2a04",
                   muted="#5a4a30", accent="#7a4a0a", line="#c8b48a", leather="#b8862a", edge="#6a4a14", border=3,
                   frame2="#fff4d0", corners=None, field="#fffaf0", on_bg="#d8a83e", on_fg="#2a1404",
                   off_bg="#e4d6b8", off_fg="#6a5a40", font="Cinzel", body="EB Garamond", light=True),
    "warbanner": dict(bg="#1c1f25", band="#1c3e8a", band_grad=("#2a5ac0", "#2450b0", "#1c3e8a", "#14306e"),
                      head="#ffd34a", text="#f2efe6", big="#ffd34a", muted="#b4b8b0", accent="#ffd34a",
                      line="#3a3e46", leather="#d8a840", edge="#2a1a04", border=4, frame2="#5a3a0c",
                      corners="#f2d06a", field="#0a0b0d", on_bg="#30343c", on_fg="#ffd34a", off_bg="#16181d",
                      off_fg="#a8acb4", font="Marcellus SC", body="EB Garamond"),
    "verdant": dict(bg="#1c2418", band="#26301f", band_grad=None, head="#e8dca8", text="#ece6cc", big="#e8dca8",
                    muted="#a8ae98", accent="#d8cc8a", line="#4a5032", leather="#6a5a32", edge="#000000", border=2,
                    frame2="#a8925a", corners=None, field="#0a0d09", on_bg="#c8d48a", on_fg="#11150f",
                    off_bg="#161c13", off_fg="#9a9e8c", font="Cinzel", body="EB Garamond"),
    "gloom": dict(bg="#14191c", band="#1a2024", band_grad=None, head="#d8e2e4", text="#d0d8da", big="#e8f0f2",
                  muted="#8a969c", accent="#c8d8dc", line="#3a4448", leather="#6a767c", edge="#0e1214", border=1,
                  frame2="#3a4448", corners=None, field="#0e1214", on_bg="#2a3236", on_fg="#eef6f8",
                  off_bg="#14191c", off_fg="#7a868c", font="Cormorant SC SemiBold", body="Cormorant Garamond"),
    "totem": dict(bg="#161c13", band="#7a1410", band_grad=("#9a1a14", "#8a1812", "#7a1410", "#5a0a08"),
                  head="#f2e8d4", text="#ece4d0", big="#f2e8d4", muted="#a89a84", accent="#e8b878", line="#4a3a26",
                  leather="#6a4426", edge="#1a0e06", border=5, frame2="#3a2414", corners=None, field="#0c0f0a",
                  on_bg="#8a1a14", on_fg="#fff2d8", off_bg="#2a2016", off_fg="#a89a84", font="Marcellus SC",
                  body="EB Garamond"),
    "hellfire": dict(bg="#110b08", band="#1e100a", band_grad=("#2a160c", "#22120a", "#1a0e08", "#140b07"),
                     head="#ffc84a", text="#ecdcc8", big="#ffc84a", muted="#a8968a", accent="#ff8a2a",
                     line="#4a2a16", leather="#6a3a20", edge="#000000", border=3, frame2="#a0562a",
                     corners="#d08a5a", field="#0a0706", on_bg="#3a1a0c", on_fg="#ffc84a", off_bg="#160e09",
                     off_fg="#8a7a6c", font="Metamorphous", body="EB Garamond"),
    "psionic": dict(bg="#08122a", band="#12285a", band_grad=("#1a3a6e", "#16326a", "#12285a", "#0c1a36"),
                    head="#f2d68a", text="#e8fbff", big="#e8fbff", muted="#8aa0b8", accent="#3ad8ff", line="#23406e",
                    leather="#c8962e", edge="#2a1a04", border=3, frame2="#3ad8ff", corners="#f6dc8a",
                    field="#060c1c", on_bg="#14305a", on_fg="#e8fbff", off_bg="#0a1428", off_fg="#7a8aa0",
                    font="Marcellus SC", body="Marcellus"),
    "guildhall": dict(bg="#3e2a18", band="#2c1d0f", band_grad=("#3a2614", "#30200f", "#2a1b0c", "#24170a"),
                      head="#f2d68a", text="#f2e8d4", big="#f2d68a", muted="#d0bc98", accent="#f2d68a",
                      line="#2a1a0c", leather="#7a5630", edge="#1a0e06", border=3, frame2="#c89a3a",
                      corners="#e8c060", field="#24170a", on_bg="#e8d8b0", on_fg="#2a1a0c", off_bg="#2e1e10",
                      off_fg="#c8b894", font="IM FELL English SC", body="EB Garamond"),
}


def keep_colors():
    """The skins keep their own colours in every app theme."""
    from . import themes as _th
    for s in SKINS.values():
        for v in s.values():
            if isinstance(v, str) and _th.is_hex(v):
                _th.KEEP.add(v.lower())
            elif isinstance(v, tuple):
                _th.KEEP.update(x.lower() for x in v if _th.is_hex(x))
    _th.KEEP.difference_update({"#000000", "#ffffff"})


keep_colors()


def palette(style):
    """The full palette of an ornate skin - for the bar (ovlight) and every window over the game (overlaywin)."""
    s = SKINS[style]
    font = family(s["font"])
    return dict(_P, leather=s["leather"], edge=s["edge"], border=s["border"], frame2=s["frame2"], corners=s["corners"],
                bg=s["bg"], band=s["band"], band_grad=s["band_grad"], field=s["field"], box=s["bg"], head=s["head"],
                accent=s["accent"], text=s["text"], big=s["big"], icon=s["big"], sub=s["text"], muted=s["muted"],
                line=s["line"], on=s["accent"], off=s["muted"], warn="#e0a352", cell_bg=s["field"],
                cell_line=s["line"], rim=s["line"], rim_hi=s["line"], rim_lo=s["line"], bg_top=s["bg"], font=font,
                hfont=font, body=family(s["body"]), title_size=10, caps=False, align="center", on_icon="◆",
                off_icon="◇", halo=None, boxless=False, look=style, skin=style, on_bg=s["on_bg"],
                on_fg=s["on_fg"], on_line=s["accent"], off_bg=s["off_bg"], off_fg=s["off_fg"], light=bool(s.get("light")))
