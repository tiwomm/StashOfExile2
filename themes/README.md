# Theme packs (2.60.0)

GGG ToS check: themes only change how the app's own windows look. Nothing here touches the game.

Every `.json` here is one theme in **Settings › Appearance**. The app also reads `%APPDATA%\StashOfExile2\themes\`,
so you can add your own without touching the app. A pack lists only what it changes: missing keys come from
`"extends"` (another pack's id) and then from `DEFAULTS` in `soe2/themes.py`.

| key | what |
|---|---|
| `schema` | always `1` |
| `id`, `name`, `order`, `description` | the file is named `<id>.json`; `order` sorts the cards; the description is the card's tooltip |
| `extends` | id of a pack to start from (e.g. a recolor of `emberforge`) |
| `light` | `true` for a light theme (text darker than the windows) |
| `colors` | roles: chassis (desktop), surface (windows), surface_raised (cards), surface_sunken (lists, boxes), surface_high, border, border_light, border_dark, text, text_muted, text_strong, accent, selection, selection_text, stripe, good, warn, bad, money, link. Optional: purple, orange, rare, magic, unique. A value may name another role. |
| `fonts.head` | families for title bars and the item card, first one installed wins |
| `bars.title` / `bars.title_off` | window title bars (active / not): `fill` gradient `[[stop, color], ...]` (the same stop twice = a hard gloss edge), `top` / `top2` / `bottom` / `bottom2` lines, `text`, `texture` (none, brushed, stone, scanline, fronds, veins, embers, glyphs, ash) + `texture_color` |
| `bars.section` | the header strip over a part of a page (the list, the item panel): same keys as `bars.title` (2.63.0) |
| `panels.viewport` | the sunken frame around a list: `edges` = `[[top-left, bottom-right], ...]`, outside in (2.63.0) |
| `buttons.normal` / `primary` / `heading` | bevelled faces: `fill` / `hover` / `pressed` gradients, `border`, `hover_border`, `inner` (the light top edge), `radius`, `text`, `text_hover`. Primary / danger are made from the accent / red when a pack leaves them out. |
| `card` | the item card in Price checks: `header` (plate, glass, ornate, notch, stepped, rite), `border`, `sep` |
| `meter` | trade limits and mod rolls: `style` (segments, bar, runes, ticks, orbs), `on`, `off`, `lcd_bg` |

Rules: the app's icons and layout are the same in every theme (no per-theme icons); rarity colors stay the game's
on dark themes; `tools/check_contrast.py` must pass (WCAG AA 4.5 : 1) for every pack with every accent.
