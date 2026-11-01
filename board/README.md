# Money Makers Community board

The server behind **Money Makers › Community** (2.30.0). Players post strats and one-liners, upvote them and report
them, with no login: the first time someone posts, votes or reports, the app asks for a display name and the board
gives that install its own key. At most 5 new accounts a day are allowed per internet address, so votes can't be
stuffed.

Posts are live at once; 3 reports hide one until an admin looks at it. Admins type the admin key once in the app.
They can then hide, delete, ban and **promote**, and promoted posts join everyone's **Official** list.

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

Put test values in `board/.dev.vars`, e.g. `ADMIN_KEY=...`, `REPORT_HIDE=2`, `JOINS_PER_DAY=50`.

## API (what the app calls)

| Call | What |
|---|---|
| `POST /auth/join` `{name}` | a new board account → `{token, user}`. Send `Authorization: Bearer <token>` after that. |
| `POST /auth/rename` `{name}` · `POST /auth/admin` `{key}` · `POST /auth/logout` | your account |
| `GET /posts?kind=strat\|one&sort=top\|new&category&type&tag&q&limit&offset` | the board |
| `POST /posts` `{kind, data}` | post (10 a day each) |
| `PUT` / `DELETE /posts/{id}` | change or delete your own post |
| `POST /posts/{id}/vote` `{up}` · `POST /posts/{id}/report` `{reason}` | upvote, report |
| `POST /posts/{id}/admin` `{action: hide\|unhide\|promote\|unpromote}` · `POST /users/{id}/ban` | admins |
| `GET /official` | promoted posts (part of the Official list) |
