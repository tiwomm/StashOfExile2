# Money Makers Community board

The server behind **Money Makers › Community** (2.30.0): players sign in with Discord, post strats and one-liners,
upvote and report. Posts are live at once; 3 reports hide one until an admin looks at it. Admins can hide, delete,
ban and **promote**, and promoted posts join everyone's **Official** list.

It is a Cloudflare Worker (`src/index.js`) with a D1 database (`schema.sql`). The free plan covers it
(100,000 requests a day). It stores only a player's Discord id, name and avatar.

## One-time setup (about 15 minutes)

1. **Cloudflare account.** Sign up free at <https://dash.cloudflare.com>. Open **Workers & Pages** once and
   pick your `workers.dev` subdomain. Your board will live at `https://soe2-board.<subdomain>.workers.dev`.
2. **Database.** In the dashboard, go to **Storage & Databases › D1 › Create**, name it `soe2-board`, and
   copy its **Database ID**.
3. **API token.** Go to **My Profile › API Tokens › Create Token** and use the **Edit Cloudflare Workers**
   template. Add the permission **Account › D1 › Edit**, create the token, and copy it. Also copy your
   **Account ID** (it's on the Workers & Pages overview, on the right).
4. **Discord app.** At <https://discord.com/developers/applications>, click **New Application** and name it
   `StashOfExile2`. Then, under **OAuth2**:
   - Copy the **Client ID**.
   - Click **Reset Secret** and copy the **Client Secret**.
   - Under **Redirects**, add `https://soe2-board.<subdomain>.workers.dev/auth/callback`.
5. **Your Discord id (to be admin).** In Discord, turn on **Settings › Advanced › Developer Mode**, then
   right-click your own name and choose **Copy User ID**.
6. **GitHub secrets.** In the repo, go to **Settings › Secrets and variables › Actions › New repository secret**
   and add each of these:

   | Name | Value |
   |---|---|
   | `CLOUDFLARE_API_TOKEN` | the token from step 3 |
   | `CLOUDFLARE_ACCOUNT_ID` | the Account ID from step 3 |
   | `D1_ID` | the Database ID from step 2 |
   | `DISCORD_CLIENT_ID` | from step 4 |
   | `DISCORD_CLIENT_SECRET` | from step 4 |
   | `ADMIN_IDS` | your Discord user id. For more admins, separate ids with commas. |

7. **Deploy.** Go to **Actions › Deploy community board › Run workflow**. After that it redeploys by itself
   whenever `board/` changes on main.
8. **Switch it on in the app.** Put the address (`https://soe2-board.<subdomain>.workers.dev`) in
   `board/url.txt`, run `py tools/build_strats.py`, and merge to main. Every app picks it up within 12 hours,
   with no new release needed.

## Running it locally (for testing)

```
cd board
npm ci
npx wrangler d1 execute soe2-board --local --file schema.sql
npx wrangler dev
```

Put test values in `board/.dev.vars` (`DISCORD_CLIENT_ID=...`, `DISCORD_CLIENT_SECRET=...`, `ADMIN_IDS=...`).
`DISCORD_API=http://127.0.0.1:5299` points sign-in at a fake Discord for the app's tests.

## API (what the app calls)

| Call | What |
|---|---|
| `GET /auth/start?state=…` → Discord → `/auth/callback` | sign in; the app polls `GET /auth/poll?state=…` for its token |
| `GET /posts?kind=strat\|one&sort=top\|new&category&type&tag&q&limit&offset` | the board |
| `POST /posts` `{kind, data}` | post (10 a day each) |
| `PUT` / `DELETE /posts/{id}` | change or delete your own post |
| `POST /posts/{id}/vote` `{up}` · `POST /posts/{id}/report` `{reason}` | upvote, report |
| `POST /posts/{id}/admin` `{action: hide\|unhide\|promote\|unpromote}` · `POST /users/{id}/ban` | admins |
| `GET /official` | promoted posts (part of the Official list) |

Posts are checked against the same standard layout as the app (`src/schema.json`, written by
`tools/build_strats.py`).
