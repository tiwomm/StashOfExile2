# Money Makers strats

Each strat is **one JSON file** in this folder, in the layout below. `tools/build_strats.py` checks every file and
builds `moneymakers.json`, which ships with the app **and** is fetched from `main` by the app (at most every 12 h), so a
merged strat reaches everyone without a new release.

**Add a strat:** open a [Strategy issue](https://github.com/tiwomm/StashOfExile2/issues/new?template=strategy.yml)
(or press **Share** on your own strat in the app - it fills the form in), or send a PR with a new file copied from
`_template.json`. Files starting with `_` are ignored.

| Field | Need | What |
|---|---|---|
| `id` | yes | lower-case-with-dashes, same as the file name |
| `name`, `author`, `summary` | yes | text; summary = one line |
| `updated` | yes | `YYYY-MM-DD` |
| `patch` | yes | game version, e.g. `0.4` |
| `category` | yes | Mapping, Breach, Delirium, Ritual, Expedition, Abyss, Bossing, Crafting, Trading, Other |
| `thoughts_per_click` | yes | 1-5, fewer = easier: 1 Autopilot, 2 Light, 3 Moderate, 4 Heavy, 5 Big brain |
| `clicks_per_hour` | yes | every click and key press an hour takes. Bands: Chill < 300, Steady < 900, Busy < 1800, Frantic |
| `steps` | yes | list of lines, in order |
| `profit_per_hour` | no | `{"low", "high", "unit"}` - unit `div`, `ex` or `chaos`; leave out when unknown |
| `investment` | no | `{"amount", "unit"}` |
| `league_start` | no | `true` if it works with no budget |
| `tags`, `requirements`, `setup`, `loot`, `tips`, `risks` | no | lists of lines (`loot` = item names to sell) |
| `regex` | no | a stash search string |
| `sources` | no | `[{"title", "url"}]` |

The tag `example` marks a sample strat. Check your file with `py tools/build_strats.py --check`.
