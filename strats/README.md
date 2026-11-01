# Money Makers strats

Each strat is **one file** in this folder, in the standard layout below: a `.json` file, or the plain-text `.txt`
layout the app saves with **⬇ Download Format** (opens in Notepad). One-liners for **Lucrative Strats** go in
`oneliners.json`. `tools/build_strats.py` checks every file and builds `moneymakers.json`, which ships with the app
**and** is fetched from `main` by the app (at most every 12 h), so a merged strat reaches everyone without a new release.

**Sharing:** players post straight from the app to the **Community** board (no login - just a name), upvote and
report there - see `board/README.md`. Admins **promote** the best posts and they join the Official list. Strats in
this folder are the hand-curated part of the Official list: copy `_template.json` (or fill in the app's
**Download Format** `.txt`) and send a PR. Files starting with `_` are ignored.

**What a strat is** = one **Category** and one **Type** inside it. Breach farming is `Mapping` › `Breach`: the
type is the main thing you farm, the category is how you do it. Everything else goes in **tags**.

| Category | Types |
|---|---|
| Mapping | Breach, Delirium, Ritual, Expedition, Abyss, Essence, Strongbox, Rogue Exiles, Shrines, Overseer, Temple, Juiced mapping, Alch & go |
| Bossing | Pinnacle bosses, Map bosses, Simulacrum, Trial of the Sekhemas, Trial of Chaos |
| Crafting | Tablet crafting, Waystone crafting, Gear crafting, Jewel crafting, Flask & charm crafting |
| Trading | Currency flipping, Bulk selling, Buy low, sell high, Services |
| Other | Vendor recipes, Gold, Other |

| Tag group | Tags (any number) |
|---|---|
| Also uses | Abyss, Breach, Delirium, Ritual, Expedition, Essence, Strongbox, Rogue Exiles, Shrines, Overseer, Temple |
| Farm type | City area farm, Sacred Bloom farm, Juiced maps, Low-tier maps, Campaign zones |
| Budget | League start, Low budget, Mid budget, High budget |
| Play style | SSF friendly, Trade league, Party play, Hardcore safe |

Searching a tag finds both: `Breach` finds Mapping › Breach and strats tagged "Also uses: Breach".

| Field | Need | What |
|---|---|---|
| `id` | yes | lower-case-with-dashes, same as the file name |
| `name`, `author`, `summary` | yes | text; summary = one line |
| `updated` | yes | `YYYY-MM-DD` |
| `patch` | yes | game version, e.g. `0.4` |
| `category`, `type` | yes | from the table above |
| `thoughts_per_click` | yes | Thinking, 1-5: 1 Autopilot, 2 Easy, 3 Moderate, 4 Hard, 5 Big brain |
| `clicks_per_hour` | yes | `Chill`, `Steady`, `Busy` or `Frantic` |
| `steps` | yes | list of lines, in order |
| `tags` | no | from the tag table |
| `waystone_tiers` | no | `{"min": 1-16, "max": 1-16}` |
| `est_cost` | no | `{"amount", "unit"}` - unit `div`, `ex` or `chaos` |
| `est_profit` | no | per hour: `{"low", "high", "unit"}` |
| `tablets`, `waystones`, `atlas`, `craft_steps` | no | lists of lines: tablets / waystones used, atlas and master setup, crafting steps |
| `requirements`, `setup`, `loot`, `tips`, `risks` | no | lists of lines (`loot` = item names to sell) |
| `regex` | no | a stash search string |
| `sources` | no | `[{"title", "url"}]` |

One-liner (`oneliners.json`): `{"id", "text", "author"}` + optional `category`, `type`, `tags`, `updated`.
The tag `example` marks a sample strat. Check your files with `py tools/build_strats.py --check`.
