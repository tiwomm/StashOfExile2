// StashOfExile2 - Money Makers community board (2.30.0). A Cloudflare Worker with a D1 database.
//
// No logins: the first time a player posts, votes or reports, the app joins with a display name (POST /auth/join) and
// keeps the key it gets back. New accounts are limited per internet address per day (JOINS_PER_DAY) so votes can't be
// stuffed. Posts (strats and one-liners in the standard layout - checked with schema.json, written by
// tools/build_strats.py from the app's own rules) are live at once; enough reports hide one until an admin looks.
// Admins (anyone who entered the ADMIN_KEY secret in the app) hide, delete, ban and promote - promoted posts join the
// Official list.
//
// 2.31.0: also the community Mod book (/mods/*): hourly anonymous price summaries and Mod book rules as votes.
//
// 2.85.0 (feedback: "protections ... to only allow author + admin to make edits", "Suggest Edits", "moderation ...
// opt-in community handled ... protections against data poisoning"): every change keeps the old version (History,
// roll back); anyone can Suggest an edit, which the author accepts or declines; changes to an Official post (and
// accepted suggestions to one, and suggestions to posts whose author is gone 30 days) wait for reviewers - players
// who opted in with an account at least 14 days old and some activity; APPROVALS of them (or one admin) decide, never
// on their own work. Reports from accounts younger than 7 days don't count towards hiding; an Official post is only
// hidden by reviewers or an admin. Every field has limits; names are unique; edits, suggestions, reports, votes and
// admin-key tries have daily limits.
//
// Secrets / vars: ADMIN_KEY, ERRORS_KEY (2.137.0: reading Error reports), ERRORS_PER_DAY, REPORT_HIDE, POSTS_PER_DAY, JOINS_PER_DAY. Stored per player: a made-up id and the
// display name. Internet addresses are only kept as a hash with the day, to count new accounts.
import RULES from "./schema.json";
import { RegExpMatcher, englishDataset, englishRecommendedTransformers } from "obscenity";

const DAY = 86400;
const MAX_BODY = 24000;
const SESSION_DAYS = 180;
const NAME = /^[\p{L}\p{N} _.\-]{2,24}$/u;

// 2.86.1 (feedback: "deny inappropriate usernames, especially homophobic, transphobic, racist bigoted names, including
// variants with alternate spellings or misspellings"): the open-source "obscenity" filter's English list (slurs and
// profanity, with look-alike letters, number swaps and repeated letters handled), checked on the name as typed and
// with its spaces / _ . - taken out, plus our own list of hate terms it doesn't cover.
const MATCHER = new RegExpMatcher({ ...englishDataset.build(), ...englishRecommendedTransformers });
const LEET = { 0: "o", 1: "i", 2: "z", 3: "e", 4: "a", 5: "s", 6: "g", 7: "t", 8: "b", 9: "g", "@": "a", "$": "s", "|": "i", "!": "i" };
// (short or common-name words - nazi in Nazir, coon in Raccoon, spic in Spice, pedo in Torpedo, rapist in Therapist,
// Aryan, Lynch - are left out on purpose: they'd refuse real names)
const HATE = ["hitler", "heilhit", "siegheil", "1488", "kkk", "whitepower", "whitepride", "gaschamber", "holohoax",
  "jewrat", "wetback", "gook", "beaner", "raghead", "towelhead", "sandnig", "jigaboo", "porchmonk", "golliwog",
  "zipperhead", "slanteye", "niglet", "nigga", "negroid", "tranny", "trannie", "troon", "shemale", "ladyboy", "faggot",
  "fagot", "lesbo", "dyke", "homo", "paedo", "pedophil", "paedophil", "nonce", "molest", "genocide"];
export function nameProblem(name) {
  const raw = String(name || "").normalize("NFKC");
  const flat = raw.toLowerCase().replace(/[\s_.\-]+/g, "");
  if (MATCHER.hasMatch(raw) || MATCHER.hasMatch(flat)) return "That name isn't allowed - pick another.";
  const plain = [...flat].map((c) => LEET[c] ?? c).join("").replace(/(.)\1+/g, "$1");
  const plain2 = [...flat].map((c) => LEET[c] ?? c).join("");
  const hit = (w) => {                                      // as typed, with number swaps, and with repeats squeezed
    const sq = w.replace(/(.)\1+/g, "$1");
    return flat.includes(w) || plain2.includes(w) || (sq.length >= 4 && plain.includes(sq));
  };
  if (HATE.some(hit)) return "That name isn't allowed - pick another.";
  return null;
}
const APPROVALS = 2, REVIEWER_DAYS = 14, REPORTER_DAYS = 7, AWAY_DAYS = 30;
const PER_DAY = { edit: 30, suggest: 10, report: 20, vote: 200, admin_key: 5, admin_key_ip: 20, review: 100 };
const MAX_MONEY = 100000, MAX_LINES = 60, MAX_LINE = 500;
const TEXT_MAX = { name: 80, summary: 300, patch: 20, regex: 250, author: 40, type: 60, category: 60 };
const ITEM_KINDS = ["tablet", "waystone", "other", "item"];
const LEDGER_FIELDS = ["runs", "minutes", "cost_per_run_div", "loot_per_run_div", "profit_per_run_div", "div_per_hour"];
const TAG_OK = /^[A-Za-z0-9][A-Za-z0-9 '&+\-]{1,39}$/;     // a Content tag the shared file added after this deploy

// ------------------------------------------------------------------ the standard layout (same rules as the app)
const slug = (t) => String(t).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "strat";

function amountProblems(d) {
  if (d === undefined || d === null) return [];
  if (typeof d !== "object" || Array.isArray(d)) return ["must be an object"];
  const out = [];
  if (!RULES.units.includes(d.unit ?? "div")) out.push(`unit must be one of ${RULES.units.join(", ")}`);
  for (const k of ["low", "high", "amount"]) {
    if (k in d && d[k] !== null && typeof d[k] !== "number") out.push(`${k} must be a number`);
    else if (typeof d[k] === "number" && !(isFinite(d[k]) && Math.abs(d[k]) <= MAX_MONEY)) out.push(`${k} must be within ±${MAX_MONEY}`);
  }
  if (typeof d.low === "number" && typeof d.high === "number" && d.low > d.high) out.push("low is bigger than high");
  return out;
}

export function validateStrat(s) {
  if (!s || typeof s !== "object" || Array.isArray(s)) return ["a strat must be an object"];
  const out = RULES.required.filter((k) => s[k] === undefined || s[k] === null || s[k] === "" ||
    (Array.isArray(s[k]) && !s[k].length)).map((k) => `missing "${k}"`);
  if (s.id && s.id !== slug(s.id)) out.push("id: lower-case letters, digits and dashes only");
  if (s.category && !(s.category in RULES.taxonomy)) out.push(`category must be one of ${Object.keys(RULES.taxonomy).join(", ")}`);
  else if (s.type && !RULES.taxonomy[s.category].includes(s.type)) out.push(`type for ${s.category} must be one of ${RULES.taxonomy[s.category].join(", ")}`);
  const t = s.thoughts_per_click;
  if (t !== undefined && !(Number.isInteger(t) && t >= 1 && t <= 5)) out.push("thoughts_per_click must be 1-5");
  if (s.clicks_per_hour !== undefined && !RULES.clicks.includes(s.clicks_per_hour)) out.push(`clicks_per_hour must be one of ${RULES.clicks.join(", ")}`);
  if (s.updated && !/^\d{4}-\d{2}-\d{2}$/.test(String(s.updated))) out.push("updated must be YYYY-MM-DD");
  else if (s.updated && Date.parse(s.updated) > Date.now() + 2 * DAY * 1000) out.push("updated is in the future");
  for (const [k, n] of Object.entries(TEXT_MAX)) if (typeof s[k] === "string" && s[k].length > n) out.push(`${k}: ${n} characters at most`);
  for (const k of RULES.lists) {
    const v = s[k];
    if (v !== undefined && (!Array.isArray(v) || !v.every((x) => typeof x === "string"))) out.push(`${k} must be a list of text lines`);
    else if (Array.isArray(v) && (v.length > MAX_LINES || v.some((x) => x.length > MAX_LINE)))
      out.push(`${k}: ${MAX_LINES} lines of ${MAX_LINE} characters at most`);
  }
  if (Array.isArray(s.tags)) for (const x of s.tags) if (!RULES.tags.includes(x) && !TAG_OK.test(String(x))) out.push(`tags: "${x}" is not in the tag list`);
  if (s.items !== undefined) {
    const it = s.items;
    const okItem = (x) => x && typeof x === "object" && !Array.isArray(x) && typeof x.base === "string" && x.base && x.base.length <= 80 &&
      (x.name === undefined || (typeof x.name === "string" && x.name.length <= 80)) &&
      (x.kind === undefined || ITEM_KINDS.includes(x.kind)) &&
      (x.count === undefined || (Number.isInteger(x.count) && x.count >= 1 && x.count <= 1000)) &&
      (x.lasts === undefined || (Number.isInteger(x.lasts) && x.lasts >= 1 && x.lasts <= 100)) &&
      (x.key_mods === undefined || (Array.isArray(x.key_mods) && x.key_mods.length <= 12 && x.key_mods.every((m) => typeof m === "string" && m.length <= 200))) &&
      Object.keys(x).every((k) => ["kind", "base", "name", "count", "lasts", "key_mods"].includes(k));
    if (!Array.isArray(it) || it.length > 30 || !it.every(okItem))
      out.push('items must be up to 30 of {"kind", "base", "name", "count" 1-1000, "lasts" 1-100, "key_mods"}');
  }
  if (s.ledger !== undefined) {
    const lg = s.ledger;
    if (!lg || typeof lg !== "object" || Array.isArray(lg) || !Object.entries(lg).every(([k, v]) =>
      LEDGER_FIELDS.includes(k) && typeof v === "number" && isFinite(v) && Math.abs(v) <= 1e6 && (k !== "runs" || (Number.isInteger(v) && v >= 0))))
      out.push("ledger must be numbers: " + LEDGER_FIELDS.join(", "));
  }
  for (const k of ["est_profit", "est_cost"]) for (const p of amountProblems(s[k])) out.push(`${k}: ${p}`);
  const wt = s.waystone_tiers;
  if (wt !== undefined) {
    const ok = wt && Number.isInteger(wt.min) && Number.isInteger(wt.max) && wt.min >= 1 && wt.max <= 16 && wt.min <= wt.max;
    if (!ok) out.push('waystone_tiers must be {"min": 1-16, "max": 1-16} with min <= max');
  }
  if (s.sources !== undefined && (!Array.isArray(s.sources) || s.sources.length > 10 || !s.sources.every((x) => x && typeof x.url === "string" &&
    /^https?:\/\//.test(x.url) && x.url.length <= 300 && String(x.title ?? "").length <= 120)))
    out.push('sources must be a list of {"title", "url"} with http(s) links');
  if (s.atlas_image !== undefined && !/^b:[0-9a-f]{32}$/.test(String(s.atlas_image)))  // 2.78.0: uploaded first
    out.push('atlas_image must be "b:<id>" (upload the screenshot first)');
  const unknown = Object.keys(s).filter((k) => !RULES.order.includes(k));
  if (unknown.length) out.push("unknown field(s): " + unknown.sort().join(", "));
  return out;
}

export function validateOne(o) {
  if (!o || typeof o !== "object" || Array.isArray(o)) return ["must be an object"];
  const out = ["text"].filter((k) => !o[k]).map((k) => `missing "${k}"`);
  if (String(o.text ?? "").length > 300) out.push("text: keep it to one line (300 characters at most)");
  for (const x of o.tags ?? []) if (!RULES.tags.includes(x)) out.push(`tags: "${x}" is not in the tag list`);
  if (o.category && !(o.category in RULES.taxonomy)) out.push("category is not in the list");
  else if (o.type && !(RULES.taxonomy[o.category] ?? []).includes(o.type)) out.push("type does not belong to that category");
  const unknown = Object.keys(o).filter((k) => !RULES.one_order.includes(k));
  if (unknown.length) out.push("unknown field(s): " + unknown.sort().join(", "));
  return out;
}

// 2.132.6: shared Regex favorites and trade-site Favorites (feedback: "allow people to publish their regex to the
// database, as well as favorites from the trade site section")
export const KINDS = ["strat", "one", "regex", "trade"];
export const REGEX_FOR = ["tablet", "waystone", "relic", "jewel", "gear"];
const REGEX_ORDER = ["id", "name", "for", "search", "state", "author", "updated", "tags"];
const TRADE_ORDER = ["id", "name", "item", "query", "sort", "author", "updated", "tags"];
const tagsOk = (o, out) => { for (const x of o.tags ?? []) if (!RULES.tags.includes(x)) out.push(`tags: "${x}" is not in the tag list`); };
const unknownOk = (o, order, out) => {
  const unknown = Object.keys(o).filter((k) => !order.includes(k));
  if (unknown.length) out.push("unknown field(s): " + unknown.sort().join(", "));
};

export function validateRegex(o) {
  if (!o || typeof o !== "object" || Array.isArray(o)) return ["must be an object"];
  const out = ["name", "for", "search"].filter((k) => !o[k]).map((k) => `missing "${k}"`);
  if (String(o.name ?? "").length > 60) out.push("name: 60 characters at most");
  if (o.for && !REGEX_FOR.includes(o.for)) out.push("for: not a kind of item");
  if (String(o.search ?? "").length > 250) out.push("search: 250 characters at most (the game's limit)");
  if (o.state !== undefined && (typeof o.state !== "object" || JSON.stringify(o.state).length > 4000)) out.push("state: too big");
  tagsOk(o, out);
  unknownOk(o, REGEX_ORDER, out);
  return out;
}

// a trade search keeps only its filters - never an account (the seller filter is dropped)
export function cleanTradeQuery(q) {
  if (!q || typeof q !== "object" || Array.isArray(q)) return null;
  const c = JSON.parse(JSON.stringify(q));
  delete c.status;
  const tf = c?.filters?.trade_filters?.filters;
  if (tf) { delete tf.account; delete tf.seller; }
  return c;
}

export function validateTrade(o) {
  if (!o || typeof o !== "object" || Array.isArray(o)) return ["must be an object"];
  const out = ["name", "query"].filter((k) => !o[k]).map((k) => `missing "${k}"`);
  if (String(o.name ?? "").length > 60) out.push("name: 60 characters at most");
  if (String(o.item ?? "").length > 80) out.push("item: 80 characters at most");
  if (o.query !== undefined && (typeof o.query !== "object" || JSON.stringify(o.query).length > 6000)) out.push("query: too big");
  if (o.sort !== undefined && (typeof o.sort !== "object" || JSON.stringify(o.sort).length > 200)) out.push("sort: too big");
  tagsOk(o, out);
  unknownOk(o, TRADE_ORDER, out);
  return out;
}

const tidy = (o, order) => Object.fromEntries(order.filter((k) => o[k] !== undefined && o[k] !== null && o[k] !== "" &&
  !(Array.isArray(o[k]) && !o[k].length)).map((k) => [k, o[k]]));

// ------------------------------------------------------------------ helpers
const now = () => Math.floor(Date.now() / 1000);
const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});
const fail = (status, error) => json({ error }, status);
const page = (title, text) => new Response(`<!doctype html><meta charset="utf-8"><title>${title}</title>
<body style="font-family:Segoe UI,sans-serif;background:#0f1a2c;color:#e8eefc;display:grid;place-items:center;height:90vh">
<div style="text-align:center"><h2>${title}</h2><p>${text}</p></div></body>`, { headers: { "content-type": "text/html; charset=utf-8" } });

async function sha256(text) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
// 2.89.3: an internet address is never stored. What is kept (for daily limits) is a KEYED hash of it with the day and
// what it's for: HMAC-SHA256 with the IP_PEPPER secret (or, until that is set, a random key kept in the database) - a
// leaked table alone can't be turned back into addresses, and every row is gone the next day.
async function metaGet(env, k) {
  const row = await env.DB.prepare("SELECT v FROM meta WHERE k = ?").bind(k).first();
  return row ? row.v : null;
}
async function metaSet(env, k, v) {
  await env.DB.prepare("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v").bind(k, String(v)).run();
}
async function ipKey(req, env, purpose) {
  let pepper = env.IP_PEPPER;
  if (!pepper) {
    pepper = await metaGet(env, "pepper");
    if (!pepper) { pepper = randomHex(32); await metaSet(env, "pepper", pepper); }
  }
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(String(pepper)), { name: "HMAC", hash: "SHA-256" },
    false, ["sign"]);
  const ip = req.headers.get("cf-connecting-ip") || "local";
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${ip}|${purpose}|${today()}`));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// 2.89.3: once a day - yesterday's limits, expired sessions, and pictures no post uses any more go
async function housekeeping(env) {
  const day = today();
  if ((await metaGet(env, "swept")) === day) return;
  await metaSet(env, "swept", day);
  await env.DB.batch([
    env.DB.prepare("DELETE FROM limits WHERE day <> ?").bind(day),
    env.DB.prepare("DELETE FROM joins WHERE day <> ?").bind(day),
    env.DB.prepare("DELETE FROM bug_limits WHERE day <> ?").bind(day),
    env.DB.prepare("DELETE FROM sessions WHERE expires < ?").bind(now()),
    env.DB.prepare("DELETE FROM app_error_installs WHERE last < ?").bind(now() - 30 * 86400),     // 2.137.0
    env.DB.prepare(`DELETE FROM images WHERE created < ? AND NOT EXISTS (SELECT 1 FROM posts p WHERE instr(p.data, '"b:' || images.key || '"') > 0)
      AND NOT EXISTS (SELECT 1 FROM revisions r WHERE instr(r.data, '"b:' || images.key || '"') > 0)`).bind(now() - 3600),
  ]);
}

const randomHex = (n) => [...crypto.getRandomValues(new Uint8Array(n))].map((b) => b.toString(16).padStart(2, "0")).join("");
function sameText(a, b) {                  // constant-time compare for the admin key
  a = String(a); b = String(b);
  let d = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) d |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return d === 0;
}

// 2.85.0: new columns and tables on an existing database (each statement fails harmlessly once it's done)
let migrated = false;
const MIGRATIONS = [
  "ALTER TABLE users ADD COLUMN reviewer INTEGER NOT NULL DEFAULT 0",     // 1 = reviews; -1 = an admin took it away
  "ALTER TABLE users ADD COLUMN last_seen INTEGER NOT NULL DEFAULT 0",
  "ALTER TABLE posts ADD COLUMN based_on INTEGER",
  "ALTER TABLE users ADD COLUMN renamed INTEGER NOT NULL DEFAULT 0",       // last name change (once every 7 days)
  "ALTER TABLE users ADD COLUMN name_reset INTEGER NOT NULL DEFAULT 0",    // 2.86.1: the filter reset the name                         // a copy of another post (credited)
  `CREATE TABLE IF NOT EXISTS revisions (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER NOT NULL,
    author_id TEXT NOT NULL, data TEXT NOT NULL, status TEXT NOT NULL, note TEXT NOT NULL DEFAULT '',
    created INTEGER NOT NULL, decided INTEGER, decided_by TEXT, why TEXT)`,
  "CREATE INDEX IF NOT EXISTS revisions_post ON revisions (post_id, status)",
  `CREATE TABLE IF NOT EXISTS reviews (target TEXT NOT NULL, user_id TEXT NOT NULL, vote TEXT NOT NULL,
    created INTEGER NOT NULL, PRIMARY KEY (target, user_id))`,
  "CREATE TABLE IF NOT EXISTS limits (key TEXT PRIMARY KEY, n INTEGER NOT NULL, day TEXT NOT NULL)",
  // 2.86.0: global leaderboards - one row per account / board / key / league / class: its best time
  `CREATE TABLE IF NOT EXISTS lb (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, cat TEXT NOT NULL,
    key TEXT NOT NULL, league TEXT NOT NULL, cls TEXT NOT NULL DEFAULT '', secs REAL NOT NULL, level INTEGER NOT NULL DEFAULT 0,
    deaths INTEGER NOT NULL DEFAULT 0, at INTEGER NOT NULL, sent INTEGER NOT NULL, reports INTEGER NOT NULL DEFAULT 0,
    hidden INTEGER NOT NULL DEFAULT 0, UNIQUE (user_id, cat, key, league, cls))`,
  "CREATE INDEX IF NOT EXISTS lb_board ON lb (cat, key, league, hidden, secs)",
  // 2.87.0: Simulacrum of Delusion is a pinnacle fight (2.86.0 filed it under Trials) - a time already sent moves
  // (unless the same player already has one under Bosses: then the faster stays and the Trials copy goes)
  "UPDATE OR IGNORE lb SET cat = 'boss' WHERE cat = 'trial' AND key = 'Simulacrum of Delusion'",
  "DELETE FROM lb WHERE cat = 'trial' AND key = 'Simulacrum of Delusion'",
  `CREATE TABLE IF NOT EXISTS lb_reports (lb_id INTEGER NOT NULL, user_id TEXT NOT NULL, reason TEXT, created INTEGER NOT NULL,
    PRIMARY KEY (lb_id, user_id))`,
  // 2.89.3: privacy - a key table for the server's own secrets / markers; pictures get unguessable keys; leaderboard
  // times keep only the day (not the second you played); admin rights are tied to the admin key they came from
  "CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)",
  "ALTER TABLE images ADD COLUMN key TEXT",
  "UPDATE images SET key = lower(hex(randomblob(16))) WHERE key IS NULL",
  "CREATE UNIQUE INDEX IF NOT EXISTS images_key ON images (key)",
  "UPDATE lb SET at = (at / 86400) * 86400 WHERE at % 86400 <> 0",
  "ALTER TABLE users ADD COLUMN admin_key TEXT NOT NULL DEFAULT ''",
  // 2.118.0: rep is gone - its table and the two account columns it used (rep_hidden, cid_link: an install's link to a
  // name, only there to count ratings toward rep) are deleted. (2.95.0 made them; nothing reads them any more.)
  "DROP TABLE IF EXISTS rep",
  "ALTER TABLE users DROP COLUMN rep_hidden",
  "ALTER TABLE users DROP COLUMN cid_link",
  // 2.132.0: gem prices pooled (runeshape / book gems) - the latest price players' searches found, per league
  `CREATE TABLE IF NOT EXISTS gem_prices (league TEXT NOT NULL, kind TEXT NOT NULL, level INTEGER NOT NULL,
    name TEXT NOT NULL, div REAL NOT NULL, n INTEGER NOT NULL DEFAULT 1, updated INTEGER NOT NULL,
    PRIMARY KEY (league, kind, level, name))`,
  // 2.137.0: Error reports (opt-in, its own switch) - one row per kind of error, counted; which installs saw it only
  // as a hashed install id (for "how many installs"), kept 30 days
  `CREATE TABLE IF NOT EXISTS app_errors (sig TEXT PRIMARY KEY, kind TEXT NOT NULL, place TEXT NOT NULL,
    etype TEXT NOT NULL DEFAULT '', frames TEXT NOT NULL DEFAULT '', msg TEXT NOT NULL DEFAULT '', first_v TEXT NOT NULL,
    last_v TEXT NOT NULL, os TEXT NOT NULL DEFAULT '', first INTEGER NOT NULL, last INTEGER NOT NULL, n INTEGER NOT NULL)`,
  `CREATE TABLE IF NOT EXISTS app_error_installs (sig TEXT NOT NULL, cid TEXT NOT NULL, last INTEGER NOT NULL,
    PRIMARY KEY (sig, cid))`,
];
async function migrate(env) {
  if (migrated) return;
  for (const sql of MIGRATIONS) {
    try { await env.DB.prepare(sql).run(); } catch (_e) { /* already there */ }
  }
  try { await imageKeys(env); } catch (_e) { /* next time */ }
  migrated = true;
}

// 2.89.3, once: posts and versions that named a picture by its old counting number ("b:12") name it by its key
async function imageKeys(env) {
  if (await metaGet(env, "image_keys")) return;
  const rows = await env.DB.prepare("SELECT id, key FROM images").all();
  for (const r of rows.results) {
    const from = `"b:${r.id}"`, to = `"b:${r.key}"`;
    await env.DB.batch([
      env.DB.prepare("UPDATE posts SET data = replace(data, ?1, ?2) WHERE instr(data, ?1) > 0").bind(from, to),
      env.DB.prepare("UPDATE revisions SET data = replace(data, ?1, ?2) WHERE instr(data, ?1) > 0").bind(from, to),
    ]);
  }
  await metaSet(env, "image_keys", "1");
}

const today = () => new Date().toISOString().slice(0, 10);
// a daily allowance: false when `who` already did `what` `max` times today
async function allowance(env, what, whoId, max, count = true) {
  const day = today(), key = await sha256(`${what}|${whoId}|${day}`);
  await env.DB.prepare("DELETE FROM limits WHERE day <> ?").bind(day).run();
  const row = await env.DB.prepare("SELECT n FROM limits WHERE key = ?").bind(key).first();
  if (row && row.n >= max) return false;
  if (count) await env.DB.prepare("INSERT INTO limits (key, n, day) VALUES (?, 1, ?) ON CONFLICT(key) DO UPDATE SET n = n + 1").bind(key, day).run();
  return true;
}
const limitFor = (env, what) => Number(env[`${what.toUpperCase()}_PER_DAY`] || PER_DAY[what]);

async function who(req, env) {
  const m = /^Bearer\s+([a-f0-9]{64})$/i.exec(req.headers.get("authorization") || "");
  if (!m) return null;
  const row = await env.DB.prepare(
    `SELECT u.id, u.name, u.admin, u.admin_key, u.banned, u.reviewer, u.last_seen, u.created, u.renamed, u.name_reset
     FROM sessions s JOIN users u ON u.id = s.user_id
     WHERE s.hash = ? AND s.expires > ?`,
  ).bind(await sha256(m[1]), now()).first();
  if (!row) return null;
  if (now() - (row.last_seen || 0) > 3600) await env.DB.prepare("UPDATE users SET last_seen = ? WHERE id = ?").bind(now(), row.id).run();
  if (nameProblem(row.name)) {                                  // 2.86.1: a name from before the filter: reset it
    row.name = await resetName(env, row.id);
    row.renamed = 0;
    row.name_reset = 1;
  }
  // 2.89.3: admin only while the server's ADMIN_KEY is the one it was granted with - a new key takes it away from everyone
  const admin = !!row.admin && !!env.ADMIN_KEY && row.admin_key === (await sha256("admin|" + env.ADMIN_KEY)).slice(0, 16);
  delete row.admin_key;
  return { ...row, admin, banned: !!row.banned, reviewer: row.reviewer === 1 && !row.banned, reviewer_state: row.reviewer };
}

// can this account opt in as a reviewer? (14 days old, and a post or 10 upvotes given; not banned / taken away)
async function reviewerCheck(env, me) {
  if (me.banned) return "This account can't review.";
  if (me.reviewer_state === -1) return "An admin took reviewing away from this account.";
  const days = Number(env.REVIEWER_DAYS ?? REVIEWER_DAYS);
  if (now() - me.created < days * DAY) return `Accounts can review once they're ${days} days old.`;
  const posts = (await env.DB.prepare("SELECT COUNT(*) AS n FROM posts WHERE author_id = ? AND hidden = 0").bind(me.id).first()).n;
  const votes = (await env.DB.prepare("SELECT COUNT(*) AS n FROM votes WHERE user_id = ?").bind(me.id).first()).n;
  if (posts < 1 && votes < 10) return "Post a strat or upvote 10 first - then you can review.";
  return null;
}
const canReview = (me) => !!me && !me.banned && (me.admin || me.reviewer === true || me.reviewer === 1);
const userOut = (me) => ({ id: me.id, name: me.name, admin: !!me.admin, reviewer: me.reviewer === true || me.reviewer === 1,
  next_rename: me.renamed ? me.renamed + 7 * DAY : 0, name_reset: !!me.name_reset });

async function readBody(req) {
  const text = await req.text();
  if (text.length > MAX_BODY) throw new Error("too big");
  return text ? JSON.parse(text) : {};
}

function present(row, me) {
  return {
    id: row.id, kind: row.kind, data: { ...JSON.parse(row.data), author: row.author_name }, score: row.score, created: row.created,
    updated: row.updated, promoted: !!row.promoted, hidden: !!row.hidden,
    reports: canReview(me) ? row.reports : undefined,
    // 2.89.3: account ids only for admins (they ban); the name is always today's (a rename reaches old posts)
    author: { id: me?.admin ? row.author_id : undefined, name: row.author_name }, voted: !!row.voted,
    mine: !!me && me.id === row.author_id,
    based_on: row.based_on ? { id: row.based_on, name: row.based_name || null } : null,          // 2.85.0
    suggestions: me && me.id === row.author_id ? row.suggested ?? 0 : undefined,
    pending: row.pending ?? 0,
  };
}

const SELECT = `SELECT p.*, u.name AS author_name, %VOTED% AS voted,
  (SELECT json_extract(b.data, '$.name') FROM posts b WHERE b.id = p.based_on) AS based_name,
  (SELECT COUNT(*) FROM revisions r WHERE r.post_id = p.id AND r.status = 'suggested') AS suggested,
  (SELECT COUNT(*) FROM revisions r WHERE r.post_id = p.id AND r.status = 'pending') AS pending
  FROM posts p JOIN users u ON u.id = p.author_id`;
const selectFor = (me) => SELECT.replace("%VOTED%", me
  ? "EXISTS(SELECT 1 FROM votes v WHERE v.post_id = p.id AND v.user_id = ?1)" : "0");

// ------------------------------------------------------------------ joining (no login)
async function join(req, env) {
  const { name } = await readBody(req);
  const clean = String(name || "").trim();
  if (!NAME.test(clean)) return fail(400, "Pick a name of 2-24 letters, numbers, spaces, _ . or -.");
  if (nameProblem(clean)) return fail(400, nameProblem(clean));
  const day = today();
  const ip = await ipKey(req, env, "join");
  await env.DB.prepare("DELETE FROM joins WHERE day <> ?").bind(day).run();
  const seen = await env.DB.prepare("SELECT n FROM joins WHERE ip = ?").bind(ip).first();
  if (seen && seen.n >= Number(env.JOINS_PER_DAY || 5)) return fail(429, "Too many new board accounts from here today - try tomorrow.");
  if (await nameTaken(env, clean)) return fail(409, "Someone on the board already has that name - pick another.");
  await env.DB.prepare("INSERT INTO joins (ip, n, day) VALUES (?, 1, ?) ON CONFLICT(ip) DO UPDATE SET n = n + 1").bind(ip, day).run();
  const id = "u" + randomHex(8), token = randomHex(32);
  await env.DB.batch([
    env.DB.prepare("INSERT INTO users (id, name, created, renamed) VALUES (?, ?, ?, ?)").bind(id, clean, now(), now()),
    env.DB.prepare("INSERT INTO sessions (hash, user_id, created, expires) VALUES (?, ?, ?, ?)")
      .bind(await sha256(token), id, now(), now() + SESSION_DAYS * DAY),
  ]);
  return json({ token, user: { id, name: clean, admin: false, reviewer: false } }, 201);
}

// 2.86.1: a name the filter refuses becomes "Player-<id>"; its owner may pick a new one at once (no 7-day wait)
async function resetName(env, id) {
  const name = "Player-" + id.slice(1, 7);
  await env.DB.prepare("UPDATE users SET name = ?, renamed = 0, name_reset = 1 WHERE id = ?").bind(name, id).run();
  return name;
}

async function sweepNames(env, me) {
  if (!me.admin) return fail(403, "admins only");
  const rows = await env.DB.prepare("SELECT id, name FROM users").all();
  const reset = [];
  for (const r of rows.results) if (nameProblem(r.name)) { await resetName(env, r.id); reset.push(r.id); }
  return json({ checked: rows.results.length, reset: reset.length });
}

async function nameTaken(env, name, exceptId = "") {
  return !!(await env.DB.prepare("SELECT 1 AS x FROM users WHERE lower(name) = lower(?) AND id <> ?").bind(name, exceptId).first());
}

async function rename(req, env, me) {
  if (me.banned) return fail(403, "This account can't post on the board.");
  const { name } = await readBody(req);
  const clean = String(name || "").trim();
  if (!NAME.test(clean)) return fail(400, "Pick a name of 2-24 letters, numbers, spaces, _ . or -.");
  if (nameProblem(clean)) return fail(400, nameProblem(clean));
  if (await nameTaken(env, clean, me.id)) return fail(409, "Someone on the board already has that name - pick another.");
  // 2.85.0 (feedback): your name is permanent - it can change once every RENAME_DAYS days
  const row = await env.DB.prepare("SELECT renamed FROM users WHERE id = ?").bind(me.id).first();
  const wait = (row?.renamed || 0) + Number(env.RENAME_DAYS ?? 7) * DAY - now();
  if (wait > 0 && !me.admin) return fail(429, `You can change your name again on ${new Date((now() + wait) * 1000).toISOString().slice(0, 10)}.`);
  await env.DB.batch([
    env.DB.prepare("UPDATE users SET name = ?, renamed = ?, name_reset = 0 WHERE id = ?").bind(clean, now(), me.id),
    // 2.89.3: the old name leaves every copy the board kept of your posts (a rename really hides the old name)
    env.DB.prepare("UPDATE posts SET data = json_set(data, '$.author', ?) WHERE author_id = ?").bind(clean, me.id),
    env.DB.prepare(`UPDATE revisions SET data = json_set(data, '$.author', ?) WHERE post_id IN
      (SELECT id FROM posts WHERE author_id = ?)`).bind(clean, me.id),
  ]);
  return json({ user: userOut({ ...me, name: clean, renamed: now(), name_reset: 0 }) });
}

async function becomeAdmin(req, env, me) {
  const ip = await ipKey(req, env, "admin");
  const max = limitFor(env, "admin_key"), maxIp = limitFor(env, "admin_key_ip");   // wrong tries a day
  if (!(await allowance(env, "admin_key", ip, maxIp, false)) || !(await allowance(env, "admin_key_user", me.id, max, false)))
    return fail(429, "Too many tries today - try tomorrow.");
  const { key } = await readBody(req);
  if (env.ADMIN_KEY && String(env.ADMIN_KEY).length < 32)                    // 2.89.3: 32+ characters, or nobody gets in
    return fail(503, "The board's admin key is too short - set a new one of 32+ random characters.");
  if (!env.ADMIN_KEY || !sameText(key, env.ADMIN_KEY)) {
    await allowance(env, "admin_key", ip, maxIp + 1);
    await allowance(env, "admin_key_user", me.id, max + 1);
    return fail(403, "That isn't the admin key.");
  }
  await env.DB.prepare("UPDATE users SET admin = 1, admin_key = ? WHERE id = ?")
    .bind((await sha256("admin|" + env.ADMIN_KEY)).slice(0, 16), me.id).run();
  return json({ user: userOut({ ...me, admin: true }) });
}

// 2.85.0: opt in / out as a reviewer
async function setReviewer(req, env, me) {
  const { on } = await readBody(req);
  if (on === false) {
    if (me.reviewer) await env.DB.prepare("UPDATE users SET reviewer = 0 WHERE id = ?").bind(me.id).run();
    return json({ user: userOut({ ...me, reviewer: 0 }) });
  }
  const why = await reviewerCheck(env, me);
  if (why) return fail(403, why);
  await env.DB.prepare("UPDATE users SET reviewer = 1 WHERE id = ?").bind(me.id).run();
  return json({ user: userOut({ ...me, reviewer: 1 }) });
}

async function adminReviewer(req, env, me, userId) {
  if (!me.admin) return fail(403, "admins only");
  const { on } = await readBody(req);
  await env.DB.prepare("UPDATE users SET reviewer = ? WHERE id = ?").bind(on === false ? -1 : 1, userId).run();
  return json({ ok: true });
}

// ------------------------------------------------------------------ posts
async function listPosts(url, env, me) {
  const p = url.searchParams;
  const kind = KINDS.includes(p.get("kind")) ? p.get("kind") : "strat";
  const where = ["p.kind = ?2"], args = [me?.id ?? null, kind];
  if (!(me?.admin && p.get("hidden") === "1")) where.push("p.hidden = 0");
  if (me?.admin && p.get("reported") === "1") where.push("p.reports > 0");
  if (p.get("mine") === "1" && me) { where.push(`p.author_id = ?${args.length + 1}`); args.push(me.id); }
  for (const [key, col] of [["category", "category"], ["type", "type"]]) {
    if (p.get(key)) { where.push(`p.${col} = ?${args.length + 1}`); args.push(p.get(key)); }
  }
  if (p.get("tag")) { where.push(`(p.tags LIKE ?${args.length + 1} OR p.type = ?${args.length + 2})`); args.push(`%|${p.get("tag")}|%`, p.get("tag")); }
  if (p.get("q")) { where.push(`p.search LIKE ?${args.length + 1}`); args.push(`%${p.get("q").toLowerCase()}%`); }
  const order = p.get("sort") === "new" ? "p.created DESC" : "p.score DESC, p.created DESC";
  const limit = Math.min(100, Math.max(1, Number(p.get("limit")) || 50)), offset = Math.max(0, Number(p.get("offset")) || 0);
  const sql = `${selectFor(me)} WHERE ${where.join(" AND ")} ORDER BY ${order} LIMIT ${limit} OFFSET ${offset}`;
  const rows = await env.DB.prepare(sql).bind(...args).all();
  const total = await env.DB.prepare(`SELECT COUNT(*) AS n FROM posts p WHERE ${where.join(" AND ")}`).bind(...args).first();
  return json({ posts: rows.results.map((r) => present(r, me)), total: total.n });
}

async function getPost(env, me, id) {
  return env.DB.prepare(`${selectFor(me)} WHERE p.id = ?2`).bind(me?.id ?? null, id).first();
}

function prepare(kind, data, user, id) {
  const base = { ...data };
  if (kind === "strat") {
    base.author = user.name;
    base.id = `board-${id ?? "new"}`;
    if (!base.updated) base.updated = new Date().toISOString().slice(0, 10);
    const probs = validateStrat(base);
    return probs.length ? { probs } : { data: tidy(base, RULES.order) };
  }
  base.author = user.name;
  base.id = `board-${id ?? "new"}`;
  if (kind === "regex") {
    if (!base.updated) base.updated = new Date().toISOString().slice(0, 10);
    const probs = validateRegex(base);
    return probs.length ? { probs } : { data: tidy(base, REGEX_ORDER) };
  }
  if (kind === "trade") {
    if (!base.updated) base.updated = new Date().toISOString().slice(0, 10);
    base.query = cleanTradeQuery(base.query);
    const probs = validateTrade(base);
    return probs.length ? { probs } : { data: tidy(base, TRADE_ORDER) };
  }
  const probs = validateOne(base);
  return probs.length ? { probs } : { data: tidy(base, RULES.one_order) };
}

const searchText = (d) => [d.name, d.summary, d.text, d.type, d.category, d.item, d.for, ...(d.tags ?? []), ...(d.steps ?? [])]
  .filter(Boolean).join(" ").toLowerCase();

// a screenshot a post names must be the poster's own upload, or the one the post already had (2.85.0)
async function imageOk(env, data, me, keep = null) {
  const ref = data?.atlas_image;
  if (!ref || ref === keep) return true;
  const row = await env.DB.prepare("SELECT author_id FROM images WHERE key = ?").bind(String(ref).slice(2)).first();
  return !!row && (row.author_id === me.id || me.admin);
}

async function createPost(req, env, me) {
  const body = await readBody(req);
  const kind = KINDS.includes(body.kind) ? body.kind : "strat";
  const today = await env.DB.prepare("SELECT COUNT(*) AS n FROM posts WHERE author_id = ? AND created > ?").bind(me.id, now() - DAY).first();
  if (today.n >= Number(env.POSTS_PER_DAY || 10) && !me.admin) return fail(429, "That's enough posts for today - try again tomorrow.");
  const r = prepare(kind, body.data ?? {}, me, null);
  if (r.probs) return json({ error: "Not in the standard layout: " + r.probs[0], problems: r.probs }, 400);
  if (!(await imageOk(env, r.data, me))) return fail(400, "That atlas screenshot belongs to another post - upload your own.");
  let basedOn = Number(body.based_on) || null;                     // 2.85.0: a copy credits the post it came from
  if (basedOn && !(await env.DB.prepare("SELECT 1 AS x FROM posts WHERE id = ?").bind(basedOn).first())) basedOn = null;
  const t = now();
  const res = await env.DB.prepare(`INSERT INTO posts (kind, author_id, data, search, category, type, tags, created, updated, based_on)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).bind(kind, me.id, JSON.stringify(r.data), searchText(r.data), r.data.category ?? null,
    r.data.type ?? null, "|" + (r.data.tags ?? []).join("|") + "|", t, t, basedOn).run();
  const id = res.meta.last_row_id;
  r.data.id = `board-${id}`;
  await env.DB.batch([
    env.DB.prepare("UPDATE posts SET data = ? WHERE id = ?").bind(JSON.stringify(r.data), id),
    env.DB.prepare("INSERT INTO revisions (post_id, author_id, data, status, note, created) VALUES (?, ?, ?, 'live', 'first version', ?)")
      .bind(id, me.id, JSON.stringify(r.data), t),
  ]);
  return json({ post: present(await getPost(env, me, id), me) }, 201);
}

// ---- 2.85.0: versions. A post's live version is in posts.data; every version (old, suggested, pending ...) in revisions.
async function ensureFirstRevision(env, row) {
  const has = await env.DB.prepare("SELECT 1 AS x FROM revisions WHERE post_id = ? AND status IN ('live', 'old')").bind(row.id).first();
  if (!has) await env.DB.prepare("INSERT INTO revisions (post_id, author_id, data, status, note, created) VALUES (?, ?, ?, 'live', 'first version', ?)")
    .bind(row.id, row.author_id, row.data, row.created).run();
}

// make a version live: the one live now becomes old; the post shows the new one
async function goLive(env, row, revId, data, deciderId) {
  const t = now();
  const rv = await env.DB.prepare("SELECT author_id FROM revisions WHERE id = ?").bind(revId).first();
  await env.DB.batch([
    env.DB.prepare("UPDATE revisions SET status = 'old' WHERE post_id = ? AND status = 'live'").bind(row.id),
    env.DB.prepare("UPDATE revisions SET status = 'live', decided = ?, decided_by = ? WHERE id = ?").bind(t, deciderId, revId),
    env.DB.prepare("UPDATE posts SET data = ?, search = ?, category = ?, type = ?, tags = ?, updated = ? WHERE id = ?")
      .bind(JSON.stringify(data), searchText(data), data.category ?? null, data.type ?? null,
        "|" + (data.tags ?? []).join("|") + "|", t, row.id),
  ]);
}

async function addRevision(env, row, authorId, data, status, note) {
  const res = await env.DB.prepare("INSERT INTO revisions (post_id, author_id, data, status, note, created) VALUES (?, ?, ?, ?, ?, ?)")
    .bind(row.id, authorId, JSON.stringify(data), status, String(note || "").slice(0, 300), now()).run();
  return res.meta.last_row_id;
}

const authorName = async (env, row) => row.author_name ??
  (await env.DB.prepare("SELECT name FROM users WHERE id = ?").bind(row.author_id).first())?.name;

// the post's own author keeps the author field, whoever writes the version
async function prepareFor(env, row, data) {
  return prepare(row.kind, data ?? {}, { name: await authorName(env, row) }, row.id);
}

async function updatePost(req, env, me, id) {
  const row = await getPost(env, me, id);
  if (!row) return fail(404, "not found");
  if (row.author_id !== me.id) return fail(403, "only its author can change it - use Suggest an edit");
  if (!(await allowance(env, "edit", me.id, limitFor(env, "edit")))) return fail(429, "That's enough edits for today.");
  const body = await readBody(req);
  const r = await prepareFor(env, row, body.data);
  if (r.probs) return json({ error: "Not in the standard layout: " + r.probs[0], problems: r.probs }, 400);
  const old = JSON.parse(row.data);
  if (!(await imageOk(env, r.data, me, old.atlas_image))) return fail(400, "That atlas screenshot belongs to another post - upload your own.");
  await ensureFirstRevision(env, row);
  if (row.promoted && !me.admin) {                                 // an Official post: reviewers look first
    await env.DB.prepare("UPDATE revisions SET status = 'withdrawn', decided = ? WHERE post_id = ? AND author_id = ? AND status = 'pending'")
      .bind(now(), id, me.id).run();
    const rid = await addRevision(env, row, me.id, r.data, "pending", body.note);
    return json({ post: present(await getPost(env, me, id), me), pending: rid }, 202);
  }
  const rid = await addRevision(env, row, me.id, r.data, "new", body.note);
  await goLive(env, row, rid, r.data, me.id);
  return json({ post: present(await getPost(env, me, id), me) });
}

// anyone (not the author): a suggested version, for the author to accept or decline
async function suggest(req, env, me, id) {
  const row = await getPost(env, me, id);
  if (!row || row.hidden) return fail(404, "not found");
  if (row.author_id === me.id) return fail(400, "It's your post - just edit it.");
  if (!(await allowance(env, "suggest", me.id, limitFor(env, "suggest")))) return fail(429, "That's enough suggestions for today.");
  const open = await env.DB.prepare("SELECT COUNT(*) AS n FROM revisions WHERE post_id = ? AND author_id = ? AND status = 'suggested'").bind(id, me.id).first();
  if (open.n >= 3) return fail(429, "You have 3 suggestions waiting on this post already.");
  const body = await readBody(req);
  const note = String(body.note || "").trim();
  if (note.length < 3) return fail(400, "Say in a few words what you changed and why.");
  const r = await prepareFor(env, row, body.data);
  if (r.probs) return json({ error: "Not in the standard layout: " + r.probs[0], problems: r.probs }, 400);
  const old = JSON.parse(row.data);
  if (!(await imageOk(env, r.data, me, old.atlas_image))) return fail(400, "That atlas screenshot belongs to another post - upload your own.");
  if (JSON.stringify(r.data) === JSON.stringify(old)) return fail(400, "Nothing changed.");
  await ensureFirstRevision(env, row);
  const rid = await addRevision(env, row, me.id, r.data, "suggested", note);
  return json({ revision: rid }, 201);
}

function revOut(r, me) {
  return {
    id: r.id, post_id: r.post_id, status: r.status, note: r.note, created: r.created, decided: r.decided, why: r.why || "",
    author: { id: me?.admin ? r.author_id : undefined, name: r.author_name },
    data: JSON.parse(r.data), mine: !!me && me.id === r.author_id,
    approvals: r.approvals ?? 0, rejections: r.rejections ?? 0, my_vote: r.my_vote ?? null,
    post_name: r.post_name ?? undefined, post_author: r.post_author ?? undefined,
  };
}
const REV_SELECT = `SELECT r.*, u.name AS author_name,
  (SELECT COUNT(*) FROM reviews v WHERE v.target = 'rev:' || r.id AND v.vote = 'approve') AS approvals,
  (SELECT COUNT(*) FROM reviews v WHERE v.target = 'rev:' || r.id AND v.vote = 'reject') AS rejections,
  (SELECT v.vote FROM reviews v WHERE v.target = 'rev:' || r.id AND v.user_id = ?1) AS my_vote,
  json_extract(p.data, '$.name') AS post_name, pu.name AS post_author
  FROM revisions r JOIN users u ON u.id = r.author_id JOIN posts p ON p.id = r.post_id JOIN users pu ON pu.id = p.author_id`;

async function revisions(env, me, id) {
  const row = await getPost(env, me, id);
  if (!row || (row.hidden && !canReview(me) && row.author_id !== me?.id)) return fail(404, "not found");
  const all = me && (me.id === row.author_id || canReview(me));
  const rows = await env.DB.prepare(`${REV_SELECT} WHERE r.post_id = ?2 ORDER BY r.id DESC LIMIT 100`).bind(me?.id ?? null, id).all();
  const out = rows.results.filter((r) => all || ["live", "old"].includes(r.status) || r.author_id === me?.id).map((r) => revOut(r, me));
  return json({ revisions: out, live: present(row, me) });
}

// your inbox: suggestions waiting on your posts, and what became of your own suggestions / pending edits
async function inbox(env, me) {
  const forMe = await env.DB.prepare(`${REV_SELECT} WHERE p.author_id = ?2 AND r.status = 'suggested' ORDER BY r.id DESC LIMIT 100`)
    .bind(me.id, me.id).all();
  const mine = await env.DB.prepare(`${REV_SELECT} WHERE r.author_id = ?2 AND r.status IN ('suggested', 'pending', 'declined', 'live', 'old', 'withdrawn')
    AND r.note <> 'first version' AND (r.status IN ('suggested', 'pending') OR r.decided > ?3) ORDER BY r.id DESC LIMIT 100`)
    .bind(me.id, me.id, now() - 30 * DAY).all();
  return json({ suggestions: forMe.results.map((r) => revOut(r, me)), mine: mine.results.filter((r) => r.post_id && r.author_id === me.id)
    .map((r) => revOut(r, me)) });
}

async function getRev(env, me, rid) {
  return env.DB.prepare(`${REV_SELECT} WHERE r.id = ?2`).bind(me?.id ?? null, rid).first();
}

// the author (or an admin) answers a suggestion; the author rolls back to an old version; the writer withdraws
async function revAction(req, env, me, rid) {
  const rev = await getRev(env, me, rid);
  if (!rev) return fail(404, "not found");
  const row = await getPost(env, me, rev.post_id);
  if (!row) return fail(404, "not found");
  const { action, why } = await readBody(req);
  const owner = row.author_id === me.id || me.admin;
  const t = now();
  if (action === "withdraw") {
    if (rev.author_id !== me.id || !["suggested", "pending"].includes(rev.status)) return fail(400, "Only your own waiting version can be withdrawn.");
    await env.DB.prepare("UPDATE revisions SET status = 'withdrawn', decided = ? WHERE id = ?").bind(t, rid).run();
    return json({ ok: true });
  }
  if (action === "decline") {
    if (!owner || !["suggested", "pending"].includes(rev.status)) return fail(403, "Only the post's author or an admin can decline it.");
    await env.DB.prepare("UPDATE revisions SET status = 'declined', decided = ?, decided_by = ?, why = ? WHERE id = ?")
      .bind(t, me.id, String(why || "").slice(0, 200), rid).run();
    return json({ ok: true, status: "declined" });
  }
  if (action === "accept" || action === "rollback") {
    if (!owner) return fail(403, "Only the post's author or an admin can do that.");
    if (action === "accept" && rev.status !== "suggested") return fail(400, "That isn't a waiting suggestion.");
    if (action === "rollback" && rev.status !== "old") return fail(400, "Only an earlier version can be brought back.");
    let rid2 = rid;
    if (action === "rollback") rid2 = await addRevision(env, row, me.id, JSON.parse(rev.data), "new", `back to the version of ${new Date(rev.created * 1000).toISOString().slice(0, 10)}`);
    if (row.promoted && !me.admin) {                              // an Official post: reviewers look first
      await env.DB.prepare("UPDATE revisions SET status = 'pending', decided = NULL WHERE id = ?").bind(rid2).run();
      return json({ ok: true, status: "pending" }, 202);
    }
    await goLive(env, row, rid2, JSON.parse(rev.data), me.id);
    return json({ ok: true, status: "live" });
  }
  return fail(400, "action: accept, decline, rollback or withdraw");
}

// what reviewers can decide: Official edits waiting, suggestions whose author is away, reported posts
async function reviewQueue(env, me) {
  if (!canReview(me)) return fail(403, "Reviewers only - opt in from your board name's menu.");
  const away = now() - Number(env.AWAY_DAYS ?? AWAY_DAYS) * DAY;
  const revs = await env.DB.prepare(`${REV_SELECT} JOIN users au ON au.id = p.author_id WHERE (r.status = 'pending'
    OR (r.status = 'suggested' AND au.last_seen < ?2 AND p.updated < ?2)) ORDER BY r.id LIMIT 100`).bind(me.id, away).all();
  const reported = await env.DB.prepare(`${selectFor(me)} WHERE p.reports > 0 ORDER BY p.reports DESC LIMIT 100`).bind(me.id).all();
  const reasons = {};
  for (const p of reported.results) {
    const rs = await env.DB.prepare("SELECT reason, created FROM reports WHERE post_id = ? ORDER BY created DESC LIMIT 20").bind(p.id).all();
    reasons[p.id] = rs.results.map((x) => x.reason).filter(Boolean);
  }
  const votes = {};
  for (const p of reported.results) {
    const v = await env.DB.prepare("SELECT vote, COUNT(*) AS n FROM reviews WHERE target = ? GROUP BY vote").bind(`post:${p.id}`).all();
    const mine = await env.DB.prepare("SELECT vote FROM reviews WHERE target = ? AND user_id = ?").bind(`post:${p.id}`, me.id).first();
    votes[p.id] = { ...Object.fromEntries(v.results.map((x) => [x.vote, x.n])), mine: mine?.vote ?? null };
  }
  return json({
    revisions: revs.results.filter((r) => r.author_id !== me.id).map((r) => ({ ...revOut(r, me), live: null })),
    reported: reported.results.filter((p) => p.author_id !== me.id).map((p) => ({ ...present(p, me), reasons: reasons[p.id], votes: votes[p.id] })),
  });
}

// a reviewer's vote: approve / reject a version; hide / keep a reported post. APPROVALS votes (or one admin) decide.
async function review(req, env, me, target, id) {
  if (!canReview(me)) return fail(403, "Reviewers only.");
  if (!(await allowance(env, "review", me.id, limitFor(env, "review")))) return fail(429, "That's enough reviews for today.");
  const { vote: v } = await readBody(req);
  const t = now();
  if (target === "rev") {
    const rev = await getRev(env, me, id);
    if (!rev) return fail(404, "not found");
    const row = await getPost(env, me, rev.post_id);
    if (rev.author_id === me.id || row.author_id === me.id) return fail(403, "Not on your own post or your own version.");
    const away = now() - Number(env.AWAY_DAYS ?? AWAY_DAYS) * DAY;
    const authorSeen = (await env.DB.prepare("SELECT last_seen FROM users WHERE id = ?").bind(row.author_id).first())?.last_seen ?? 0;
    const open = rev.status === "pending" || (rev.status === "suggested" && authorSeen < away && row.updated < away);
    if (!open) return fail(400, "That version isn't waiting for reviewers.");
    if (!["approve", "reject"].includes(v)) return fail(400, "vote: approve or reject");
    await env.DB.prepare(`INSERT INTO reviews (target, user_id, vote, created) VALUES (?, ?, ?, ?)
      ON CONFLICT(target, user_id) DO UPDATE SET vote = excluded.vote, created = excluded.created`).bind(`rev:${id}`, me.id, v, t).run();
    const c = Object.fromEntries((await env.DB.prepare("SELECT vote, COUNT(*) AS n FROM reviews WHERE target = ? GROUP BY vote")
      .bind(`rev:${id}`).all()).results.map((x) => [x.vote, x.n]));
    if ((c.approve ?? 0) >= APPROVALS || (me.admin && v === "approve")) {
      await goLive(env, row, id, JSON.parse(rev.data), me.id);
      return json({ ok: true, status: "live" });
    }
    if ((c.reject ?? 0) >= APPROVALS || (me.admin && v === "reject")) {
      await env.DB.prepare("UPDATE revisions SET status = 'declined', decided = ?, decided_by = ?, why = 'reviewers said no' WHERE id = ?").bind(t, me.id, id).run();
      return json({ ok: true, status: "declined" });
    }
    return json({ ok: true, status: rev.status, approvals: c.approve ?? 0, rejections: c.reject ?? 0 });
  }
  const row = await getPost(env, me, id);
  if (!row) return fail(404, "not found");
  if (row.author_id === me.id) return fail(403, "Not on your own post.");
  if (!["hide", "keep"].includes(v)) return fail(400, "vote: hide or keep");
  await env.DB.prepare(`INSERT INTO reviews (target, user_id, vote, created) VALUES (?, ?, ?, ?)
    ON CONFLICT(target, user_id) DO UPDATE SET vote = excluded.vote, created = excluded.created`).bind(`post:${id}`, me.id, v, t).run();
  const c = Object.fromEntries((await env.DB.prepare("SELECT vote, COUNT(*) AS n FROM reviews WHERE target = ? GROUP BY vote")
    .bind(`post:${id}`).all()).results.map((x) => [x.vote, x.n]));
  if ((c.hide ?? 0) >= APPROVALS || (me.admin && v === "hide")) {
    await env.DB.prepare("UPDATE posts SET hidden = 1 WHERE id = ?").bind(id).run();
    return json({ ok: true, hidden: true });
  }
  if ((c.keep ?? 0) >= APPROVALS || (me.admin && v === "keep")) {
    await env.DB.batch([
      env.DB.prepare("UPDATE posts SET hidden = 0, reports = 0 WHERE id = ?").bind(id),
      env.DB.prepare("DELETE FROM reports WHERE post_id = ?").bind(id),
      env.DB.prepare("DELETE FROM reviews WHERE target = ?").bind(`post:${id}`),
    ]);
    return json({ ok: true, hidden: false });
  }
  return json({ ok: true, hide: c.hide ?? 0, keep: c.keep ?? 0 });
}

async function deletePost(env, me, id) {
  const row = await getPost(env, me, id);
  if (!row) return fail(404, "not found");
  if (row.author_id !== me.id && !me.admin) return fail(403, "only its author or an admin can delete it");
  const keys = await postImages(env, id);
  await env.DB.batch([
    env.DB.prepare("DELETE FROM posts WHERE id = ?").bind(id),
    env.DB.prepare("DELETE FROM votes WHERE post_id = ?").bind(id),
    env.DB.prepare("DELETE FROM reports WHERE post_id = ?").bind(id),
    env.DB.prepare("DELETE FROM revisions WHERE post_id = ?").bind(id),
    env.DB.prepare("DELETE FROM reviews WHERE target = ?").bind(`post:${id}`),
    ...keys.map((k) => env.DB.prepare("DELETE FROM images WHERE key = ?").bind(k)),   // 2.89.3: its pictures go too
  ]);
  return json({ ok: true });
}

// the picture keys a post and its versions name
async function postImages(env, id) {
  const rows = await env.DB.prepare(`SELECT json_extract(data, '$.atlas_image') AS ref FROM posts WHERE id = ?1
    UNION SELECT json_extract(data, '$.atlas_image') FROM revisions WHERE post_id = ?1`).bind(id).all();
  return [...new Set(rows.results.map((r) => String(r.ref || "")).filter((r) => /^b:[0-9a-f]{32}$/.test(r)).map((r) => r.slice(2)))];
}

// 2.89.3: DELETE /me - leave the board and take everything with you: your name, posts (and their pictures, votes,
// versions), your suggestions, votes, reports, reviews, leaderboard times and sessions. Nothing of yours stays.
async function deleteMe(env, me) {
  const posts = (await env.DB.prepare("SELECT id FROM posts WHERE author_id = ?").bind(me.id).all()).results.map((r) => r.id);
  for (const id of posts) {
    const keys = await postImages(env, id);
    await env.DB.batch([
      env.DB.prepare("DELETE FROM votes WHERE post_id = ?").bind(id),
      env.DB.prepare("DELETE FROM reports WHERE post_id = ?").bind(id),
      env.DB.prepare("DELETE FROM reviews WHERE target = ? OR target IN (SELECT 'rev:' || id FROM revisions WHERE post_id = ?)")
        .bind(`post:${id}`, id),
      env.DB.prepare("DELETE FROM revisions WHERE post_id = ?").bind(id),
      ...keys.map((k) => env.DB.prepare("DELETE FROM images WHERE key = ?").bind(k)),
    ]);
  }
  await env.DB.batch([
    env.DB.prepare("DELETE FROM posts WHERE author_id = ?").bind(me.id),
    env.DB.prepare("DELETE FROM revisions WHERE author_id = ?").bind(me.id),
    env.DB.prepare("DELETE FROM images WHERE author_id = ?").bind(me.id),
    env.DB.prepare("DELETE FROM votes WHERE user_id = ?").bind(me.id),
    env.DB.prepare("DELETE FROM reports WHERE user_id = ?").bind(me.id),
    env.DB.prepare("DELETE FROM reviews WHERE user_id = ?").bind(me.id),
    env.DB.prepare("DELETE FROM lb_reports WHERE user_id = ? OR lb_id IN (SELECT id FROM lb WHERE user_id = ?)").bind(me.id, me.id),
    env.DB.prepare("DELETE FROM lb WHERE user_id = ?").bind(me.id),
    env.DB.prepare("DELETE FROM sessions WHERE user_id = ?").bind(me.id),
    env.DB.prepare("DELETE FROM users WHERE id = ?").bind(me.id),
  ]);
  await env.DB.prepare("UPDATE posts SET score = (SELECT COUNT(*) FROM votes v WHERE v.post_id = posts.id)").run();
  return json({ ok: true, deleted: true });
}

async function vote(req, env, me, id) {
  if (!(await allowance(env, "vote", me.id, limitFor(env, "vote")))) return fail(429, "That's enough votes for today.");
  const body = await readBody(req);
  const row = await getPost(env, me, id);
  if (!row || (row.hidden && !me.admin)) return fail(404, "not found");
  if (body.up === false) {
    await env.DB.prepare("DELETE FROM votes WHERE post_id = ? AND user_id = ?").bind(id, me.id).run();
  } else {
    await env.DB.prepare("INSERT OR IGNORE INTO votes (post_id, user_id, created) VALUES (?, ?, ?)").bind(id, me.id, now()).run();
  }
  await env.DB.prepare("UPDATE posts SET score = (SELECT COUNT(*) FROM votes WHERE post_id = ?1) WHERE id = ?1").bind(id).run();
  return json({ post: present(await getPost(env, me, id), me) });
}

async function report(req, env, me, id) {
  const body = await readBody(req);
  const row = await getPost(env, me, id);
  if (!row) return fail(404, "not found");
  if (row.author_id === me.id) return fail(400, "That's your own post.");
  if (!(await allowance(env, "report", me.id, limitFor(env, "report")))) return fail(429, "That's enough reports for today.");
  await env.DB.prepare("INSERT OR IGNORE INTO reports (post_id, user_id, reason, created) VALUES (?, ?, ?, ?)")
    .bind(id, me.id, String(body.reason || "").slice(0, 200), now()).run();
  const n = (await env.DB.prepare("SELECT COUNT(*) AS n FROM reports WHERE post_id = ?").bind(id).first()).n;
  // 2.85.0: only reports from accounts at least REPORTER_DAYS old count towards hiding, and an Official post is only
  // hidden by reviewers or an admin (three new accounts could hide anything before)
  const counted = (await env.DB.prepare(`SELECT COUNT(*) AS n FROM reports r JOIN users u ON u.id = r.user_id
    WHERE r.post_id = ? AND u.created <= ? AND u.banned = 0`).bind(id, now() - Number(env.REPORTER_DAYS ?? REPORTER_DAYS) * DAY).first()).n;
  const hide = !row.promoted && counted >= Number(env.REPORT_HIDE || 3) ? 1 : row.hidden;
  await env.DB.prepare("UPDATE posts SET reports = ?, hidden = ? WHERE id = ?").bind(n, hide, id).run();
  return json({ ok: true, hidden: !!hide });
}

async function adminPost(req, env, me, id) {
  if (!me.admin) return fail(403, "admins only");
  const { action } = await readBody(req);
  const set = { hide: "hidden = 1", unhide: "hidden = 0, reports = 0", promote: "promoted = 1", unpromote: "promoted = 0" }[action];
  if (!set) return fail(400, "action: hide, unhide, promote or unpromote");
  if (action === "unhide") await env.DB.batch([env.DB.prepare("DELETE FROM reports WHERE post_id = ?").bind(id),
    env.DB.prepare("DELETE FROM reviews WHERE target = ?").bind(`post:${id}`)]);
  await env.DB.prepare(`UPDATE posts SET ${set} WHERE id = ?`).bind(id).run();
  const row = await getPost(env, me, id);
  return row ? json({ post: present(row, me) }) : fail(404, "not found");
}

async function ban(req, env, me, userId) {
  if (!me.admin) return fail(403, "admins only");
  const { banned } = await readBody(req);
  await env.DB.prepare("UPDATE users SET banned = ?, reviewer = CASE WHEN ? = 1 THEN 0 ELSE reviewer END WHERE id = ?")
    .bind(banned === false ? 0 : 1, banned === false ? 0 : 1, userId).run();
  if (banned !== false) {
    await env.DB.batch([
      env.DB.prepare("UPDATE posts SET hidden = 1 WHERE author_id = ?").bind(userId),
      env.DB.prepare("UPDATE revisions SET status = 'withdrawn', decided = ? WHERE author_id = ? AND status IN ('suggested', 'pending')").bind(now(), userId),
    ]);
  } else await env.DB.prepare("UPDATE posts SET hidden = 0 WHERE author_id = ? AND reports = 0").bind(userId).run();
  return json({ ok: true });
}

async function official(env) {
  const rows = await env.DB.prepare(`SELECT p.*, u.name AS author_name, 0 AS voted FROM posts p JOIN users u ON u.id = p.author_id
    WHERE p.promoted = 1 AND p.hidden = 0 ORDER BY p.score DESC`).all();
  const out = { strats: [], oneliners: [], regex: [], trade: [] };
  const into = { one: out.oneliners, regex: out.regex, trade: out.trade };
  for (const r of rows.results) (into[r.kind] ?? out.strats).push(JSON.parse(r.data));
  return json(out);
}

// ------------------------------------------------------------------ 2.86.0: global leaderboards
// POST /lb {entries: [{cat, key, secs, league, cls, level, deaths, at}]} - your best times (the app sends each board's
// best; it keeps the faster of old and new). Times come from the game's log, so they're self-reported: impossible
// ones are refused (LB_FLOOR / LB_CEIL); reports from accounts 7+ days old, reviewers and admins hide them.
// 2.124.0: "zone" - one campaign zone, from entering it to leaving it (its name is the key)
const LB_CATS = ["campaign", "zone", "map", "boss", "trial"];
const LB_FLOOR = { campaign: 120, zone: 10, map: 30, boss: 10, trial: 60 };
const LB_CEIL = { campaign: 48 * 3600, zone: 3 * 3600, map: 3 * 3600, boss: 3600, trial: 3 * 3600 };
const LB_EVERY = 10 * 60;

async function lbSend(req, env, me) {
  const body = await readBody(req);
  const last = await env.DB.prepare("SELECT MAX(sent) AS t FROM lb WHERE user_id = ?").bind(me.id).first();
  if (last?.t && now() - last.t < Number(env.LB_EVERY ?? LB_EVERY) && !me.admin) return fail(429, "too soon");
  const t = now(), stmts = [];
  let ok = 0, bad = 0;
  for (const e of (Array.isArray(body.entries) ? body.entries : []).slice(0, 400)) {
    const cat = String(e?.cat), key = String(e?.key ?? "").trim(), league = String(e?.league ?? "").trim();
    const cls = String(e?.cls ?? "").trim(), secs = Number(e?.secs);
    if (!LB_CATS.includes(cat) || !key || key.length > 80 || !league || league.length > 60 || cls.length > 40 ||
        !isFinite(secs) || secs < LB_FLOOR[cat] || secs > LB_CEIL[cat]) { bad++; continue; }
    const level = Math.max(0, Math.min(100, Math.floor(Number(e.level) || 0)));
    const deaths = Math.max(0, Math.min(999, Math.floor(Number(e.deaths) || 0)));
    // 2.89.3: only the day is kept - the exact second would show when (and in which time zone) someone plays
    const at = Math.floor(Math.min(t, Math.max(0, Math.floor(Number(e.at) || t))) / DAY) * DAY;
    stmts.push(env.DB.prepare(`INSERT INTO lb (user_id, cat, key, league, cls, secs, level, deaths, at, sent)
      VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10) ON CONFLICT(user_id, cat, key, league, cls) DO UPDATE SET
      secs = MIN(secs, ?6), level = CASE WHEN ?6 < secs THEN ?7 ELSE level END,
      deaths = CASE WHEN ?6 < secs THEN ?8 ELSE deaths END, at = CASE WHEN ?6 < secs THEN ?9 ELSE at END, sent = ?10`)
      .bind(me.id, cat, key, league, cls, secs, level, deaths, at, t));
    ok++;
  }
  if (!ok) stmts.push(env.DB.prepare("UPDATE lb SET sent = ? WHERE user_id = ?").bind(t, me.id));
  for (let i = 0; i < stmts.length; i += 50) await env.DB.batch(stmts.slice(i, i + 50));
  return json({ ok: true, kept: ok, refused: bad });
}

// GET /lb?cat=&key=&league=&cls=&limit= -> the board (fastest first, one row per account); without key: the keys
async function lbList(url, env, me) {
  const p = url.searchParams, cat = p.get("cat") || "map";
  if (!LB_CATS.includes(cat)) return fail(400, "cat: " + LB_CATS.join(", "));
  const where = ["l.cat = ?1", canReview(me) && p.get("hidden") === "1" ? "1 = 1" : "l.hidden = 0", "u.banned = 0"];
  const args = [cat];
  if (p.get("league")) { where.push(`l.league = ?${args.length + 1}`); args.push(p.get("league")); }
  if (p.get("cls")) { where.push(`l.cls = ?${args.length + 1}`); args.push(p.get("cls")); }
  if (!p.get("key")) {
    const rows = await env.DB.prepare(`SELECT l.key, COUNT(DISTINCT l.user_id) AS players, MIN(l.secs) AS best FROM lb l
      JOIN users u ON u.id = l.user_id WHERE ${where.join(" AND ")} GROUP BY l.key ORDER BY players DESC LIMIT 500`).bind(...args).all();
    const cls = await env.DB.prepare(`SELECT DISTINCT l.cls FROM lb l JOIN users u ON u.id = l.user_id WHERE l.cat = ?1 AND l.cls <> ''`)
      .bind(cat).all();
    const leagues = await env.DB.prepare("SELECT DISTINCT league FROM lb WHERE cat = ?").bind(cat).all();
    // 2.131.0 (feedback: other players seemed missing - they were in another league): players per league, so
    // League ▾ can say where the times are (counts only)
    const lp = await env.DB.prepare(`SELECT l.league, COUNT(DISTINCT l.user_id) AS n FROM lb l JOIN users u ON u.id = l.user_id
      WHERE l.cat = ? AND l.hidden = 0 AND u.banned = 0 GROUP BY l.league`).bind(cat).all();
    return json({ keys: rows.results, classes: cls.results.map((r) => r.cls), leagues: leagues.results.map((r) => r.league),
      league_players: Object.fromEntries(lp.results.map((r) => [r.league, r.n])) });
  }
  where.push(`l.key = ?${args.length + 1}`);
  args.push(p.get("key"));
  const limit = Math.min(200, Math.max(1, Number(p.get("limit")) || 100));
  // one row per account: its fastest (over the chosen leagues / classes)
  const rows = await env.DB.prepare(`SELECT l.*, u.name FROM lb l JOIN users u ON u.id = l.user_id
    WHERE ${where.join(" AND ")} AND l.secs = (SELECT MIN(x.secs) FROM lb x WHERE x.user_id = l.user_id AND x.cat = l.cat
    AND x.key = l.key AND x.hidden = 0 ${p.get("league") ? "AND x.league = l.league" : ""} ${p.get("cls") ? "AND x.cls = l.cls" : ""})
    GROUP BY l.user_id ORDER BY l.secs, l.id LIMIT ${limit}`).bind(...args).all();
  return json({ rows: rows.results.map((r) => ({ id: r.id, name: r.name, secs: r.secs, cls: r.cls, league: r.league,
    level: r.level, deaths: r.deaths, at: Math.floor(r.at / DAY) * DAY, mine: !!me && me.id === r.user_id, hidden: !!r.hidden,
    reports: canReview(me) ? r.reports : undefined })) });
}

async function lbReport(req, env, me, id) {
  const row = await env.DB.prepare("SELECT * FROM lb WHERE id = ?").bind(id).first();
  if (!row) return fail(404, "not found");
  if (row.user_id === me.id) return fail(400, "That's your own time.");
  if (!(await allowance(env, "report", me.id, limitFor(env, "report")))) return fail(429, "That's enough reports for today.");
  const { reason } = await readBody(req);
  await env.DB.prepare("INSERT OR IGNORE INTO lb_reports (lb_id, user_id, reason, created) VALUES (?, ?, ?, ?)")
    .bind(id, me.id, String(reason || "").slice(0, 200), now()).run();
  const n = (await env.DB.prepare("SELECT COUNT(*) AS n FROM lb_reports WHERE lb_id = ?").bind(id).first()).n;
  const counted = (await env.DB.prepare(`SELECT COUNT(*) AS n FROM lb_reports r JOIN users u ON u.id = r.user_id
    WHERE r.lb_id = ? AND u.created <= ? AND u.banned = 0`).bind(id, now() - Number(env.REPORTER_DAYS ?? REPORTER_DAYS) * DAY).first()).n;
  const hide = counted >= Number(env.REPORT_HIDE || 3) ? 1 : row.hidden;
  await env.DB.prepare("UPDATE lb SET reports = ?, hidden = ? WHERE id = ?").bind(n, hide, id).run();
  return json({ ok: true, hidden: !!hide });
}

// reviewers vote hide / keep (two decide), an admin decides alone
async function lbReview(req, env, me, id) {
  if (!canReview(me)) return fail(403, "Reviewers only.");
  const row = await env.DB.prepare("SELECT * FROM lb WHERE id = ?").bind(id).first();
  if (!row) return fail(404, "not found");
  if (row.user_id === me.id) return fail(403, "Not on your own time.");
  const { vote: v } = await readBody(req);
  if (!["hide", "keep"].includes(v)) return fail(400, "vote: hide or keep");
  await env.DB.prepare(`INSERT INTO reviews (target, user_id, vote, created) VALUES (?, ?, ?, ?)
    ON CONFLICT(target, user_id) DO UPDATE SET vote = excluded.vote, created = excluded.created`).bind(`lb:${id}`, me.id, v, now()).run();
  const c = Object.fromEntries((await env.DB.prepare("SELECT vote, COUNT(*) AS n FROM reviews WHERE target = ? GROUP BY vote")
    .bind(`lb:${id}`).all()).results.map((x) => [x.vote, x.n]));
  if ((c.hide ?? 0) >= APPROVALS || (me.admin && v === "hide")) {
    await env.DB.prepare("UPDATE lb SET hidden = 1 WHERE id = ?").bind(id).run();
    return json({ ok: true, hidden: true });
  }
  if ((c.keep ?? 0) >= APPROVALS || (me.admin && v === "keep")) {
    await env.DB.batch([env.DB.prepare("UPDATE lb SET hidden = 0, reports = 0 WHERE id = ?").bind(id),
      env.DB.prepare("DELETE FROM lb_reports WHERE lb_id = ?").bind(id),
      env.DB.prepare("DELETE FROM reviews WHERE target = ?").bind(`lb:${id}`)]);
    return json({ ok: true, hidden: false });
  }
  return json({ ok: true, hide: c.hide ?? 0, keep: c.keep ?? 0 });
}

async function lbForget(env, me) {
  await env.DB.batch([env.DB.prepare("DELETE FROM lb_reports WHERE lb_id IN (SELECT id FROM lb WHERE user_id = ?)").bind(me.id),
    env.DB.prepare("DELETE FROM lb WHERE user_id = ?").bind(me.id)]);
  return json({ ok: true });
}

// ------------------------------------------------------------------ 2.31.0: the community Mod book
const BATCH_EVERY = 45 * 60;                 // one summary per install per 45 minutes at most (the app sends hourly)
const MAX_PAIRS = 600, MAX_VOTES = 400, W_CAP = 10;
const SID = /^[a-z_]+\.[A-Za-z0-9_.]{1,80}$/, KEY = /^.{2,200}$/s, VOTE = ["high", "normal", "ignore"];
const MAP_RANKS = ["S", "A", "B", "C", "D", "Avoid"];
const GEM_NAME = /^[a-z0-9' ,:-]{2,60}$/, GEM_KINDS = ["skill", "support", "spirit", "gem"];     // 2.132.0
const okPrice = (m) => typeof m === "number" && isFinite(m) && m > 0.0005 && m < 100000;
const ZONE_TEXT = /^[\p{L}\p{N} ',.\-]{1,80}$/u;
const UNMATCHED_TEXT = /^[\p{L}\p{N}_ #%+\-.,'():/]{3,100}$/u, BASE_TEXT = /^[\p{L}\p{N} ',.\-]{1,60}$/u;
const okText = (t, n = 80) => typeof t === "string" && t.length > 0 && t.length <= n;

async function modBatch(req, env) {
  const body = await readBody(req);
  const cidRaw = String(body.cid || "");
  if (!/^[a-f0-9]{32}$/.test(cidRaw)) return fail(400, "bad cid");
  // 2.89.3: made-up install ids can't flood it - BATCHES_PER_DAY batches and NEW_CIDS_PER_DAY new installs per address
  const ipk = await ipKey(req, env, "batch");
  if (!(await allowance(env, "batch_ip", ipk, Number(env.BATCHES_PER_DAY || 60)))) return fail(429, "too many today");
  const known = await env.DB.prepare("SELECT 1 AS x FROM contributors WHERE cid = ?").bind(await sha256(cidRaw)).first();
  if (!known && !(await allowance(env, "new_cid_ip", ipk, Number(env.NEW_CIDS_PER_DAY || 3)))) return fail(429, "too many new installs today");
  const league = String(body.league || "").slice(0, 60);
  const cid = await sha256(cidRaw), t = now();
  const seen = await env.DB.prepare("SELECT last FROM contributors WHERE cid = ?").bind(cid).first();
  if (seen && t - seen.last < BATCH_EVERY) return fail(429, "too soon");
  const stmts = [env.DB.prepare(`INSERT INTO contributors (cid, last, batches) VALUES (?1, ?2, 1)
    ON CONFLICT(cid) DO UPDATE SET last = ?2, batches = batches + 1`).bind(cid, t)];
  let used = 0;
  if (league) {
    for (const p of (Array.isArray(body.prices) ? body.prices : []).slice(0, MAX_PAIRS)) {
      if (!okText(p?.base) || !SID.test(String(p?.sid)) || !okPrice(p?.med) || !(p?.n >= 1)) continue;
      const w = Math.min(Number(p.n) || 1, W_CAP);
      stmts.push(env.DB.prepare(`INSERT INTO mod_prices (league, base, sid, n, w, slog, batches, updated)
        VALUES (?1, ?2, ?3, ?4, ?5, ?6, 1, ?7) ON CONFLICT(league, base, sid) DO UPDATE SET n = n + ?4, w = w + ?5,
        slog = slog + ?6, batches = batches + 1, updated = ?7`)
        .bind(league, p.base, p.sid, Math.min(Math.floor(p.n), 500), w, w * Math.log(p.med), t));
      used++;
    }
    for (const b of (Array.isArray(body.bases) ? body.bases : []).slice(0, 100)) {
      if (!okText(b?.base) || !okPrice(b?.med) || !(b?.n >= 1)) continue;
      const w = Math.min(Number(b.n) || 1, W_CAP * 3);
      stmts.push(env.DB.prepare(`INSERT INTO base_prices (league, base, n, w, slog, batches, updated)
        VALUES (?1, ?2, ?3, ?4, ?5, 1, ?6) ON CONFLICT(league, base) DO UPDATE SET n = n + ?3, w = w + ?4,
        slog = slog + ?5, batches = batches + 1, updated = ?6`)
        .bind(league, b.base, Math.min(Math.floor(b.n), 2000), w, w * Math.log(b.med), t));
    }
  }
  for (const v of (Array.isArray(body.maps) ? body.maps : []).slice(0, MAX_VOTES)) {   // 2.32.0: map ranks
    const name = String(v?.name ?? "").trim();
    if (!name || name.length > 80) continue;
    if (v.rank === null) stmts.push(env.DB.prepare("DELETE FROM map_votes WHERE name = ? AND cid = ?").bind(name, cid));
    else if (MAP_RANKS.includes(v.rank)) stmts.push(env.DB.prepare(`INSERT INTO map_votes (name, cid, rank, updated)
      VALUES (?1, ?2, ?3, ?4) ON CONFLICT(name, cid) DO UPDATE SET rank = ?3, updated = ?4`).bind(name, cid, v.rank, t));
  }
  for (const z of (Array.isArray(body.zones) ? body.zones : []).slice(0, 100)) {   // 2.77.0: campaign zones
    const act = String(z?.act ?? ""), zone = String(z?.zone ?? "").trim(), after = String(z?.after ?? "").trim();
    const level = Math.floor(Number(z?.level) || 0);
    // 2.89.3: a zone name is letters, digits, spaces and ' , . - only (it can reach the guide pack)
    if (!/^(\d|i\d)$/.test(act) || !okText(zone) || !ZONE_TEXT.test(zone) || (after && !ZONE_TEXT.test(after)) ||
        after.length > 80 || level < 0 || level > 100) continue;
    stmts.push(env.DB.prepare(`INSERT INTO campaign_zones (act, zone, cid, after, level, updated)
      VALUES (?1, ?2, ?3, ?4, ?5, ?6) ON CONFLICT(act, zone, cid) DO UPDATE SET after = ?4, level = ?5, updated = ?6`)
      .bind(act, zone, cid, after, level, t));
  }
  for (const u of (Array.isArray(body.unmatched) ? body.unmatched : []).slice(0, 100)) {   // 2.121.1
    const text = String(u?.text ?? "").trim(), base = String(u?.base ?? "").trim();
    if (!UNMATCHED_TEXT.test(text) || (base && !BASE_TEXT.test(base))) continue;
    stmts.push(env.DB.prepare(`INSERT INTO unmatched_mods (text, cid, base, updated) VALUES (?1, ?2, ?3, ?4)
      ON CONFLICT(text, cid) DO UPDATE SET base = ?3, updated = ?4`).bind(text, cid, base, t));
  }
  // 2.132.0 (feedback: "people are gonna get rate limited hard"): gem prices from players' own searches - the
  // newest one wins (a gem's price moves); a book's gems are then priced from here instead of the trade site
  if (league) {
    for (const g of (Array.isArray(body.gems) ? body.gems : []).slice(0, 200)) {
      const name = String(g?.name ?? "").trim().toLowerCase(), kind = String(g?.kind ?? "");
      const level = Math.floor(Number(g?.level) || 0);
      if (!GEM_NAME.test(name) || !GEM_KINDS.includes(kind) || level < 0 || level > 40 || !okPrice(g?.div)) continue;
      stmts.push(env.DB.prepare(`INSERT INTO gem_prices (league, kind, level, name, div, n, updated)
        VALUES (?1, ?2, ?3, ?4, ?5, 1, ?6) ON CONFLICT(league, kind, level, name) DO UPDATE SET div = ?5, n = n + 1,
        updated = ?6`).bind(league, kind, level, name, g.div, t));
    }
  }
  let votes = 0;
  for (const v of (Array.isArray(body.votes) ? body.votes : []).slice(0, MAX_VOTES)) {
    if (!KEY.test(String(v?.key ?? ""))) continue;
    if (v.value === null) stmts.push(env.DB.prepare("DELETE FROM mod_votes WHERE key = ? AND cid = ?").bind(v.key, cid));
    else if (VOTE.includes(v.value)) stmts.push(env.DB.prepare(`INSERT INTO mod_votes (key, cid, value, updated)
      VALUES (?1, ?2, ?3, ?4) ON CONFLICT(key, cid) DO UPDATE SET value = ?3, updated = ?4`).bind(v.key, cid, v.value, t));
    else continue;
    votes++;
  }
  await env.DB.batch(stmts);
  return json({ ok: true, prices: used, votes });
}

// 2.132.0: every gem price found in the last two weeks for a league (small: one row a gem and level)
async function gemPrices(url, env) {
  const league = String(url.searchParams.get("league") || "").slice(0, 60);
  const rows = await env.DB.prepare(`SELECT kind, level, name, div, updated, n FROM gem_prices WHERE league = ?
    AND updated > ?`).bind(league, now() - 14 * 86400).all();
  return json({ league, gems: rows.results.map((r) => [r.kind, r.level, r.name, r.div, r.updated, r.n]) });
}

async function modStats(url, env) {
  const league = String(url.searchParams.get("league") || "").slice(0, 60);
  const bases = await env.DB.prepare("SELECT base, n, w, slog, batches FROM base_prices WHERE league = ?").bind(league).all();
  // 2.133.0: "pool:" rows (gear, uniques, fallback searches) are kept for later study, not sent to every install
  const rows = await env.DB.prepare(`SELECT base, sid, n, w, slog, batches FROM mod_prices WHERE league = ? AND n >= 3
    AND base NOT LIKE 'pool:%'`)
    .bind(league).all();
  const typical = {};
  for (const b of bases.results) if (b.w > 0) typical[b.base] = b.slog / b.w;
  const out = rows.results.map((r) => {
    const lm = r.slog / r.w, base = typical[r.base];
    return [r.base, r.sid, r.n, Math.round(Math.exp(lm) * 1000) / 1000,
      base === undefined ? null : Math.round(Math.exp(lm - base) * 100) / 100, r.batches];
  });
  // 2.133.0: installs that sent a summary in the last 7 days (Community data sharing on) - a count, nothing else
  const active = (await env.DB.prepare("SELECT COUNT(*) AS n FROM contributors WHERE last >= ?").bind(now() - 7 * 86400).first()).n;
  return json({ league, stats: out, players: (await env.DB.prepare("SELECT COUNT(*) AS n FROM contributors").first()).n, active });
}

async function mapRatings(env) {
  const rows = await env.DB.prepare("SELECT name, rank, COUNT(*) AS n FROM map_votes GROUP BY name, rank").all();
  const by = {};
  for (const r of rows.results) (by[r.name] ??= {})[r.rank] = r.n;
  return json({ maps: Object.entries(by) });
}

// 2.77.0: zones players' logs showed that their guide pack didn't have - pooled for tools/build_guide.py
async function campaignZones(env) {
  const rows = await env.DB.prepare(`SELECT act, zone, COUNT(*) AS n, ROUND(AVG(level)) AS level FROM campaign_zones
    GROUP BY act, zone HAVING COUNT(*) >= 3`).all();
  const after = await env.DB.prepare(`SELECT act, zone, after, COUNT(*) AS n FROM campaign_zones GROUP BY act, zone, after
    ORDER BY n DESC`).all();
  const best = {};
  for (const a of after.results) best[a.act + "|" + a.zone] ??= a.after;
  return json({ zones: rows.results.map((r) => ({ act: r.act, zone: r.zone, n: r.n, level: r.level,
    after: best[r.act + "|" + r.zone] || "" })) });
}

// 2.121.1: the mod lines installs couldn't match, pooled (2 or more installs, last 90 days) - read by the weekly
// "Unmatched mods" workflow. Wording and base type only.
async function unmatchedMods(env) {
  const rows = await env.DB.prepare(`SELECT text, COUNT(*) AS n, MAX(base) AS base, MAX(updated) AS last
    FROM unmatched_mods WHERE updated > ?1 GROUP BY text HAVING COUNT(*) >= 2 ORDER BY n DESC LIMIT 1000`)
    .bind(now() - 90 * 86400).all();
  return json({ unmatched: rows.results.map((r) => ({ text: r.text, n: r.n, base: r.base, last: r.last })) });
}

async function modRatings(env) {
  const rows = await env.DB.prepare(`SELECT key, SUM(value = 'high') AS high, SUM(value = 'normal') AS normal,
    SUM(value = 'ignore') AS ignore FROM mod_votes GROUP BY key HAVING COUNT(*) >= 2`).all();
  return json({ ratings: rows.results.map((r) => [r.key, r.high, r.normal, r.ignore]) });
}

// ------------------------------------------------------------------ bug reports (2.48.0)
// The app's "Report a bug" posts here; the Worker opens a GitHub issue with its own token (the GITHUB_TOKEN secret -
// the app never holds one) and, with a DISCORD_WEBHOOK secret, tells Discord. No sign-in; BUGS_PER_DAY per address.
// 2.89.3: a public issue - an account name (Name#1234) or a Windows / Linux home path is masked here too
const scrubText = (t) => String(t).replace(/([\\/](?:Users|home)[\\/])[^\\/\s"']+/gi, "$1<you>")
  .replace(/[\p{L}\p{N}_]{2,40}#\d{4}\b/gu, "<account>").replace(/@(everyone|here)/gi, "@\u200b$1");
// ------------------------------------------------------------------ 2.137.0: Error reports (opt-in)
// POST /errors {cid, v, os, items: [{kind, place, etype, frames, msg, n}]} - what went wrong in the app: where in the
// code, the error's type, and (trade site errors) the site's short answer. No names, items, files or free text: every
// field must match a narrow pattern or the item is dropped. GET /errors needs the ERRORS_KEY secret (x-errors-key).
const ERR_KINDS = ["error", "crash", "freeze", "slow", "net", "caught", "debug"];
const ERR_PLACE = /^[A-Za-z0-9 _.:()\/'#,-]{1,80}$/;
const ERR_TYPE = /^[A-Za-z_][A-Za-z0-9_.]{0,60}$/;
const ERR_FRAME = /^[A-Za-z0-9_.-]{1,40}:[A-Za-z0-9_<>.-]{1,60}:\d{1,6}$/;
const ERR_MSG = /^[A-Za-z0-9 _.:,'()#/-]{0,120}$/;
async function errorBatch(req, env) {
  if (!/^application\/json/i.test(req.headers.get("content-type") || "") || req.headers.get("x-soe2") !== "1")
    return fail(400, "bad request");
  const body = await readBody(req);
  const cidRaw = String(body.cid || "");
  if (!/^[a-f0-9]{32}$/.test(cidRaw)) return fail(400, "bad cid");
  const ipk = await ipKey(req, env, "errors");
  if (!(await allowance(env, "errors_ip", ipk, Number(env.ERRORS_PER_DAY || 30)))) return fail(429, "too many today");
  if (!(await allowance(env, "errors_cid", cidRaw, 30))) return fail(429, "too many today");
  const v = /^[0-9][0-9.]{0,14}$/.test(String(body.v || "")) ? String(body.v) : "?";
  const os = /^(win|linux|mac)[0-9._-]{0,20}$/.test(String(body.os || "")) ? String(body.os) : "";
  const cid = await sha256(cidRaw), t = now();
  const stmts = [];
  let used = 0;
  for (const it of (Array.isArray(body.items) ? body.items : []).slice(0, 50)) {
    const kind = String(it?.kind || ""), place = String(it?.place || "").trim();
    const etype = String(it?.etype || ""), msg = String(it?.msg || "").trim();
    const frames = (Array.isArray(it?.frames) ? it.frames : []).slice(0, 6).map(String);
    const n = Math.min(Math.max(Math.floor(Number(it?.n) || 1), 1), 1000);
    if (!ERR_KINDS.includes(kind) || !ERR_PLACE.test(place) || (etype && !ERR_TYPE.test(etype)) ||
        !frames.every((f) => ERR_FRAME.test(f)) || !ERR_MSG.test(msg)) continue;
    const fr = frames.join(" < ");
    const sig = (await sha256(`${kind}|${place}|${etype}|${fr}|${msg}`)).slice(0, 32);
    stmts.push(env.DB.prepare(`INSERT INTO app_errors (sig, kind, place, etype, frames, msg, first_v, last_v, os, first, last, n)
      VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?7, ?8, ?9, ?9, ?10) ON CONFLICT(sig) DO UPDATE SET last_v = ?7, os = ?8,
      last = ?9, n = n + ?10`).bind(sig, kind, place, etype, fr, msg, v, os, t, n));
    stmts.push(env.DB.prepare(`INSERT INTO app_error_installs (sig, cid, last) VALUES (?1, ?2, ?3)
      ON CONFLICT(sig, cid) DO UPDATE SET last = ?3`).bind(sig, cid, t));
    used++;
  }
  if (stmts.length) await env.DB.batch(stmts);
  return json({ ok: true, used });
}

async function errorList(req, env, url) {
  if (!env.ERRORS_KEY || String(env.ERRORS_KEY).length < 32) return fail(503, "Error reports aren't set up on the board yet.");
  if (!sameText(req.headers.get("x-errors-key") || "", env.ERRORS_KEY)) return fail(403, "not allowed");
  const since = Math.max(0, Number(url.searchParams.get("since")) || 0);
  const rows = await env.DB.prepare(`SELECT e.*, (SELECT COUNT(*) FROM app_error_installs i WHERE i.sig = e.sig) AS installs
    FROM app_errors e WHERE e.last > ?1 ORDER BY installs DESC, e.n DESC LIMIT 500`).bind(since).all();
  return json({ errors: rows.results.map((r) => ({ kind: r.kind, place: r.place, type: r.etype, frames: r.frames,
    msg: r.msg, first_v: r.first_v, last_v: r.last_v, os: r.os, first: r.first, last: r.last, n: r.n, installs: r.installs })) });
}

async function bugReport(req, env) {
  // 2.89.3: only the app sends these - a web page can't (a JSON body and the app's own header force a check first)
  if (!/^application\/json/i.test(req.headers.get("content-type") || "") || req.headers.get("x-soe2") !== "1")
    return fail(400, "bad request");
  if (!env.GITHUB_TOKEN) return fail(503, "Bug reports aren't set up on the board yet.");
  const b = await readBody(req);
  const title = scrubText(String(b.title || "").trim().slice(0, 120));
  const text = scrubText(String(b.body || "").trim().slice(0, 20000));
  const version = String(b.version || "?").slice(0, 30);
  if (title.length < 4 || text.length < 10) return fail(400, "Say what happened (a title and a few words).");
  const day = today();
  const ip = await ipKey(req, env, "bug");
  await env.DB.prepare("DELETE FROM bug_limits WHERE day <> ?").bind(day).run();
  const seen = await env.DB.prepare("SELECT n FROM bug_limits WHERE ip = ?").bind(ip).first();
  if (seen && seen.n >= Number(env.BUGS_PER_DAY || 5)) return fail(429, "That's a lot of reports today - try tomorrow.");
  await env.DB.prepare("INSERT INTO bug_limits (ip, n, day) VALUES (?, 1, ?) ON CONFLICT(ip) DO UPDATE SET n = n + 1").bind(ip, day).run();
  const repo = env.GITHUB_REPO || "tiwomm/StashOfExile2";
  const r = await fetch(`https://api.github.com/repos/${repo}/issues`, {
    method: "POST",
    headers: { authorization: `Bearer ${env.GITHUB_TOKEN}`, accept: "application/vnd.github+json",
      "user-agent": "soe2-board", "content-type": "application/json" },
    body: JSON.stringify({ title: `[Bug] ${title}`, labels: ["bug", "from the app"],
      body: `${text}\n\n---\nSent from StashOfExile2 ${version} (Report a bug).` }),
  });
  if (!r.ok) return fail(502, `GitHub said ${r.status}.`);
  const issue = await r.json();
  if (env.DISCORD_WEBHOOK) {
    await fetch(env.DISCORD_WEBHOOK, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ content: `🐞 New bug report #${issue.number} (v${version}): ${title}\n${issue.html_url}`,
        allowed_mentions: { parse: [] } }) })
      .catch(() => {});
  }
  return json({ number: issue.number, url: issue.html_url }, 201);
}

// ------------------------------------------------------------------ 2.78.0: atlas screenshots for strats
// POST /images {data: base64 JPEG} (joined users; IMAGES_PER_DAY each) -> {id}; GET /images/<id> -> the JPEG.
const MAX_IMAGE = 320 * 1024;
async function postImage(req, env, me) {
  const text = await req.text();
  if (text.length > MAX_IMAGE * 1.4 + 100) return fail(413, "That picture is too big.");
  const body = JSON.parse(text || "{}");
  let bytes;
  try {
    bytes = Uint8Array.from(atob(String(body.data || "")), (c) => c.charCodeAt(0));
  } catch (_e) {
    return fail(400, "bad picture");
  }
  if (bytes.length < 100 || bytes.length > MAX_IMAGE || bytes[0] !== 0xff || bytes[1] !== 0xd8) return fail(400, "Send a JPEG of 320 KB or less.");
  const today = await env.DB.prepare("SELECT COUNT(*) AS n FROM images WHERE author_id = ? AND created > ?").bind(me.id, now() - DAY).first();
  if (today.n >= Number(env.IMAGES_PER_DAY || 20) && !me.admin) return fail(429, "That's enough pictures for today - try again tomorrow.");
  const key = randomHex(16);                         // 2.89.3: an unguessable key, not a counting number
  await env.DB.prepare("INSERT INTO images (author_id, data, created, key) VALUES (?, ?, ?, ?)").bind(me.id, bytes, now(), key).run();
  return json({ id: key }, 201);
}

// 2.89.3: a picture is only handed out while a post people can see uses it (or to its uploader / reviewers);
// a deleted or hidden post's picture is gone, and nothing caches it for long
async function getImage(env, me, key) {
  const row = await env.DB.prepare("SELECT data, author_id FROM images WHERE key = ?").bind(key).first();
  if (!row) return fail(404, "not found");
  const ref = `"b:${key}"`;
  const shown = await env.DB.prepare("SELECT 1 AS x FROM posts WHERE hidden = 0 AND instr(data, ?) > 0 LIMIT 1").bind(ref).first();
  const own = me && (me.id === row.author_id || canReview(me));
  if (!shown && !own) return fail(404, "not found");
  return new Response(new Uint8Array(row.data), { headers: { "content-type": "image/jpeg",
    "cache-control": "private, max-age=3600" } });
}

// ------------------------------------------------------------------ routing
export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const m = /^\/posts\/(\d+)(?:\/(vote|report|admin|suggest|revisions|review))?$/.exec(path);
    const rv = /^\/revisions\/(\d+)(?:\/(review))?$/.exec(path);
    try {
      await migrate(env);
      try { await housekeeping(env); } catch (_e) { /* next request */ }
      if (path === "/" || path === "/health") return json({ ok: true, schema: RULES.schema });
      if (path === "/auth/join" && req.method === "POST") return join(req, env);
      if (path === "/official") return official(env);
      if (path === "/mods/batch" && req.method === "POST") return modBatch(req, env);
      if (path === "/mods/stats") return modStats(url, env);
      if (path === "/gems") return gemPrices(url, env);
      if (path === "/mods/ratings") return modRatings(env);
      if (path === "/mods/unmatched") return unmatchedMods(env);
      if (path === "/maps/ratings") return mapRatings(env);
      if (path === "/campaign/zones") return campaignZones(env);
      if (path === "/bugs" && req.method === "POST") return bugReport(req, env);
      if (path === "/errors" && req.method === "POST") return errorBatch(req, env);       // 2.137.0
      if (path === "/errors" && req.method === "GET") return errorList(req, env, url);
      const me = await who(req, env);
      const im = /^\/images\/([0-9a-f]{32})$/.exec(path);
      if (im && req.method === "GET") return getImage(env, me, im[1]);
      if (path === "/me" && req.method === "GET") {
        if (!me) return fail(401, "sign in first");
        const why = canReview(me) ? null : await reviewerCheck(env, me);
        return json({ user: { ...userOut(me), can_review: !why, why_not: why } });
      }
      if (m && m[2] === "revisions" && req.method === "GET") return revisions(env, me, Number(m[1]));
      if (path === "/lb" && req.method === "GET") return lbList(url, env, me);
      if (path === "/auth/logout" && req.method === "POST") {
        const t = /^Bearer\s+(\S+)$/i.exec(req.headers.get("authorization") || "");
        if (t) await env.DB.prepare("DELETE FROM sessions WHERE hash = ?").bind(await sha256(t[1])).run();
        return json({ ok: true });
      }
      if (path === "/posts" && req.method === "GET") return listPosts(url, env, me);
      if (m && req.method === "GET" && !m[2]) {
        const row = await getPost(env, me, Number(m[1]));
        return row && (!row.hidden || me?.admin || row.author_id === me?.id) ? json({ post: present(row, me) }) : fail(404, "not found");
      }
      if (!me) return fail(401, "Join the board first.");
      if (path === "/auth/rename" && req.method === "POST") return rename(req, env, me);
      if (path === "/me" && req.method === "DELETE") return deleteMe(env, me);
      if (path === "/auth/admin" && req.method === "POST") return becomeAdmin(req, env, me);
      if (path === "/me/inbox" && req.method === "GET") return inbox(env, me);
      if (path === "/admin/names/sweep" && req.method === "POST") return sweepNames(env, me);
      if (path === "/review" && req.method === "GET") return reviewQueue(env, me);
      if (me.banned) return fail(403, "This account can't post on the board.");
      if (path === "/posts" && req.method === "POST") return createPost(req, env, me);
      if (path === "/images" && req.method === "POST") return postImage(req, env, me);
      if (m && !m[2] && req.method === "PUT") return updatePost(req, env, me, Number(m[1]));
      if (m && !m[2] && req.method === "DELETE") return deletePost(env, me, Number(m[1]));
      if (m && m[2] === "vote" && req.method === "POST") return vote(req, env, me, Number(m[1]));
      if (m && m[2] === "report" && req.method === "POST") return report(req, env, me, Number(m[1]));
      if (m && m[2] === "admin" && req.method === "POST") return adminPost(req, env, me, Number(m[1]));
      if (m && m[2] === "suggest" && req.method === "POST") return suggest(req, env, me, Number(m[1]));
      if (m && m[2] === "review" && req.method === "POST") return review(req, env, me, "post", Number(m[1]));
      if (rv && rv[2] === "review" && req.method === "POST") return review(req, env, me, "rev", Number(rv[1]));
      if (rv && !rv[2] && req.method === "POST") return revAction(req, env, me, Number(rv[1]));
      if (path === "/auth/reviewer" && req.method === "POST") return setReviewer(req, env, me);
      if (path === "/lb" && req.method === "POST") return lbSend(req, env, me);
      if (path === "/lb/mine" && req.method === "DELETE") return lbForget(env, me);
      const lbm = /^\/lb\/(\d+)\/(report|review)$/.exec(path);
      if (lbm && lbm[2] === "report" && req.method === "POST") return lbReport(req, env, me, Number(lbm[1]));
      if (lbm && lbm[2] === "review" && req.method === "POST") return lbReview(req, env, me, Number(lbm[1]));
      const b = /^\/users\/([a-z0-9]{1,40})\/(ban|reviewer)$/.exec(path);
      if (b && b[2] === "ban" && req.method === "POST") return ban(req, env, me, b[1]);
      if (b && b[2] === "reviewer" && req.method === "POST") return adminReviewer(req, env, me, b[1]);
      return fail(404, "not found");
    } catch (e) {
      if (e instanceof SyntaxError || e.message === "too big") return fail(400, "bad request");
      return fail(500, "server error");
    }
  },
};
