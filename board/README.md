# Money Makers Community board

> **GGG ToS safety check - read first.** One key press = one action, only when you press it · nothing acts in the game by itself (watchers only look and show) · never touch the game's memory, code or traffic · the mouse is never moved or clicked for you · it reads only your clipboard, Client.txt, screen pixels, the trade site (within its limits) and poe.ninja. Every change must pass all of [TOS.md](../TOS.md) (`tools/check_tos.py` checks the code on every PR).

The server behind **Money Makers › Community** (2.30.0). Players post strats and one-liners, upvote them and report
them, with no login: the first time someone posts, votes or reports, the app asks for a display name and the board
gives that install its own key. At most 5 new accounts a day are allowed per internet address, so votes can't be
stuffed.

Posts are live at once. Admins type the admin key once in the app (5 wrong tries a day per account). They can then
hide, delete, ban and **promote**, and promoted posts join everyone's **Official** list.

Since 2.85.0 posts are protected against vandalism and bad data:
- **Only the author edits a post** (an admin can hide or delete it). Every change keeps the version before it:
  **History** shows each version field by field, and the author can roll back.
- **Suggest an edit:** anyone else sends their version with a note; the author accepts or declines it.
- **Reviewers** (opt-in; the account must be 14 days old with a post or 10 upvotes given; an admin can take it away):
  a change to an **Official** post, a suggestion the author accepted on one, and suggestions on posts whose author has
  been away 30 days wait in the **Review queue**. Two reviewers (or one admin) decide; nobody reviews their own post
  or version.
- **Reports** from accounts younger than 7 days don't count. 3 counted reports hide a normal post; an Official post
  is only hidden by 2 reviewers or an admin. Reviewers see the reasons and can hide a post or keep it (clearing its
  reports).
- **Field checks:** money within ±100,000, items (≤ 30; count 1-1000, lasts 1-100), the author's numbers, text
  lengths and line counts, sources, dates; a post's screenshot must be its author's own upload.
- **Names are unique**, change once every 7 days, and (2.86.1) slurs and hate words are refused - also spelled with
  look-alike letters, numbers, repeats or spaces (the open-source `obscenity` list plus our own). A name from before
  the filter is reset to `Player-...` on its next visit (its owner picks a new one at once); `POST /admin/names/sweep`
  (admins) resets them all. Daily limits on edits (30), suggestions (10), reports (20),
  votes (200) and reviews (100).

Since 2.31.0 it also pools the **community Mod book**: once an hour each app sends a summary of the mod prices its
price checks saw (per base and mod: how many listings and their median, nothing else), plus the Mod book rules the
player set, which count as votes. These are keyed by a random install id, which the board only stores hashed.
Since 2.69.1 this is opt-in ("Community data sharing" in the app's Settings, asked once on first run): an app
sends nothing, and posts no strats, until its player says yes.

It is a Cloudflare Worker (`src/index.js`) with a D1 database (`schema.sql`), and the free plan covers it. It stores a
made-up player id and the display name. Internet addresses are only kept as a hash with the date, to count new
accounts.

## One-time setup

1. **Cloudflare account** (free). Open **Workers & Pages** once and pick your `workers.dev` subdomain.
2. **Database.** Go to **Storage & Databases › D1 › Create**, name it `soe2-board`, and copy the Database ID.
3. **API token.** Go to **My Profile › API Tokens › Create Token** and use the **Edit Cloudflare Workers** template.
   Add the permission **Account › D1 › Edit**. Set Account Resources to your account and Zone Resources to all zones.
   Copy the token, and copy your **Account ID** (Workers & Pages overview, on the right).
4. **GitHub secrets.** Go to **Settings › Secrets and variables › Actions** and add:

   | Name | Value |
   |---|---|
   | `CLOUDFLARE_API_TOKEN` | the token from step 3 |
   | `CLOUDFLARE_ACCOUNT_ID` | the Account ID from step 3 |
   | `D1_ID` | the Database ID from step 2 |
   | `ADMIN_KEY` | a long password you make up (at least 8 characters). In the app, use 👤 › Become admin. |
   | `BUGS_GITHUB_TOKEN` | 2.48.0, optional: lets the app's **🐞 Report a bug** open GitHub issues. GitHub › Settings › Developer settings › Personal access tokens › **Fine-grained** › Generate: only this repository, permission **Issues: Read and write**, nothing else. Without it, Report a bug opens GitHub's new-issue page in the player's browser instead. |
   | `DISCORD_WEBHOOK` | 2.48.0, optional: tells your Discord about every new issue (from the app or opened on GitHub). Discord › Server Settings › Integrations › Webhooks › New Webhook › pick the channel › **Copy Webhook URL**. |

5. **Deploy.** It runs by itself when `board/` changes on main. To run it by hand, go to
   **Actions › Deploy community board › Run workflow**.
6. **The address** goes in `board/url.txt` (then run `py tools/build_strats.py` and merge). Apps pick it up within
   12 hours.

## Running it locally (for testing)

```
cd board
npm ci
npx wrangler d1 execute soe2-board --local --file schema.sql
npx wrangler dev
```

Put test values in `board/.dev.vars`, e.g. `ADMIN_KEY=...`, `REPORT_HIDE=2`, `JOINS_PER_DAY=50`, and (2.85.0, so tests
needn't wait days) `REVIEWER_DAYS=0`, `REPORTER_DAYS=0`, `ADMIN_KEY_IP_PER_DAY=1000`. New columns and tables reach an
existing database by themselves (the Worker adds them on first use).

## API (what the app calls)

| Call | What |
|---|---|
| `POST /bugs` `{title, body, version}` | 2.48.0: a bug report → a GitHub issue `{number, url}` (needs the `GITHUB_TOKEN` Worker secret; 5 a day per address) |
| `POST /auth/join` `{name}` | a new board account → `{token, user}`. Send `Authorization: Bearer <token>` after that. |
| `POST /auth/rename` `{name}` · `POST /auth/admin` `{key}` · `POST /auth/logout` | your account (2.85.0: names are unique; a rename once every 7 days) |
| `GET /me` | 2.85.0: your account, and whether you can opt in as a reviewer (`can_review`, `why_not`) |
| `POST /auth/reviewer` `{on}` · `POST /users/{id}/reviewer` `{on}` | 2.85.0: opt in / out as a reviewer; an admin gives or takes it away |
| `POST /posts/{id}/suggest` `{data, note}` | 2.85.0: suggest an edit to someone else's post |
| `GET /posts/{id}/revisions` | 2.85.0: History (everyone: live and earlier versions; the author and reviewers: waiting ones too) |
| `GET /me/inbox` | 2.85.0: suggestions waiting on your posts, and what became of yours |
| `POST /revisions/{id}` `{action: accept\|decline\|rollback\|withdraw, why}` | 2.85.0: the author answers a suggestion or rolls back; the writer withdraws |
| `GET /review` · `POST /revisions/{id}/review` `{vote: approve\|reject}` · `POST /posts/{id}/review` `{vote: hide\|keep}` | 2.85.0: reviewers |
| `GET /posts?kind=strat\|one&sort=top\|new&category&type&tag&q&limit&offset` | the board |
| `POST /posts` `{kind, data, based_on}` | post (10 a day each); `based_on`: the post it's a copy of (credited) |
| `PUT` / `DELETE /posts/{id}` | change (`{data, note}`; an Official post's change waits for reviewers: 202 + `pending`) or delete your own post |
| `POST /posts/{id}/vote` `{up}` · `POST /posts/{id}/report` `{reason}` | upvote, report |
| `POST /posts/{id}/admin` `{action: hide\|unhide\|promote\|unpromote}` · `POST /users/{id}/ban` | admins |
| `GET /official` | promoted posts (part of the Official list) |
| `POST /lb` `{entries: [{cat, key, secs, league, cls, level, deaths, at}]}` | 2.86.0: your best times (campaign / map / boss / trial); one batch per 10 min; the faster time stays; impossible times refused |
| `GET /lb?cat&league&cls` · `GET /lb?cat&key&league&cls&limit` | 2.86.0: the boards (keys, players, best) · one board, fastest first, one row per account |
| `POST /lb/{id}/report` `{reason}` · `POST /lb/{id}/review` `{vote: hide\|keep}` · `DELETE /lb/mine` | 2.86.0: report a time; reviewers / admins hide or keep; forget all your times |
| `POST /mods/batch` `{cid, league, prices, bases, votes}` | 2.31.0: an install's hourly summary (per base / mod: count + median) and its Mod book rule changes. One per 45 min. 2.77.0: `zones` - campaign zones the app's guide pack didn't know (`{act, zone, after, level}`). |
| `POST /images` `{data}` | 2.78.0: an atlas screenshot (base64 JPEG, 320 KB at most; joined users, 20 a day) -> `{id}`. A strat names it `"atlas_image": "b:<id>"`. |
| `GET /images/<id>` | 2.78.0: that JPEG (cached for good). |
| `GET /campaign/zones` | 2.77.0: those zones, pooled (seen by 2 or more installs): `{act, zone, n, level, after}` - read by `tools/build_guide.py`. |
| `GET /mods/stats?league=` · `GET /mods/ratings` | the pooled prices (median, lift, summaries) and how players rate each mod |
| `GET /maps/ratings` | 2.32.0: how players rank each map (`maps` in the batch = a player's map ranks) |
