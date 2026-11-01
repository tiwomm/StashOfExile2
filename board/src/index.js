// StashOfExile2 - Money Makers community board (2.30.0). A Cloudflare Worker with a D1 database.
//
// No logins: the first time a player posts, votes or reports, the app joins with a display name (POST /auth/join) and
// keeps the key it gets back. New accounts are limited per internet address per day (JOINS_PER_DAY) so votes can't be
// stuffed. Posts (strats and one-liners in the standard layout - checked with schema.json, written by
// tools/build_strats.py from the app's own rules) are live at once; enough reports hide one until an admin looks.
// Admins (anyone who entered the ADMIN_KEY secret in the app) hide, delete, ban and promote - promoted posts join the
// Official list.
//
// Secrets / vars: ADMIN_KEY, REPORT_HIDE, POSTS_PER_DAY, JOINS_PER_DAY. Stored per player: a made-up id and the
// display name. Internet addresses are only kept as a hash with the day, to count new accounts.
import RULES from "./schema.json";

const DAY = 86400;
const MAX_BODY = 24000;
const SESSION_DAYS = 180;
const NAME = /^[\p{L}\p{N} _.\-]{2,24}$/u;

// ------------------------------------------------------------------ the standard layout (same rules as the app)
const slug = (t) => String(t).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "strat";

function amountProblems(d) {
  if (d === undefined || d === null) return [];
  if (typeof d !== "object" || Array.isArray(d)) return ["must be an object"];
  const out = [];
  if (!RULES.units.includes(d.unit ?? "div")) out.push(`unit must be one of ${RULES.units.join(", ")}`);
  for (const k of ["low", "high", "amount"]) if (k in d && d[k] !== null && typeof d[k] !== "number") out.push(`${k} must be a number`);
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
  for (const k of RULES.lists) {
    const v = s[k];
    if (v !== undefined && (!Array.isArray(v) || !v.every((x) => typeof x === "string"))) out.push(`${k} must be a list of text lines`);
  }
  if (Array.isArray(s.tags)) for (const x of s.tags) if (!RULES.tags.includes(x)) out.push(`tags: "${x}" is not in the tag list`);
  for (const k of ["est_profit", "est_cost"]) for (const p of amountProblems(s[k])) out.push(`${k}: ${p}`);
  const wt = s.waystone_tiers;
  if (wt !== undefined) {
    const ok = wt && Number.isInteger(wt.min) && Number.isInteger(wt.max) && wt.min >= 1 && wt.max <= 16 && wt.min <= wt.max;
    if (!ok) out.push('waystone_tiers must be {"min": 1-16, "max": 1-16} with min <= max');
  }
  if (s.sources !== undefined && (!Array.isArray(s.sources) || !s.sources.every((x) => x && typeof x.url === "string" && /^https?:\/\//.test(x.url))))
    out.push('sources must be a list of {"title", "url"} with http(s) links');
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
const randomHex = (n) => [...crypto.getRandomValues(new Uint8Array(n))].map((b) => b.toString(16).padStart(2, "0")).join("");
function sameText(a, b) {                  // constant-time compare for the admin key
  a = String(a); b = String(b);
  let d = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) d |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return d === 0;
}

async function who(req, env) {
  const m = /^Bearer\s+([a-f0-9]{64})$/i.exec(req.headers.get("authorization") || "");
  if (!m) return null;
  const row = await env.DB.prepare(
    "SELECT u.id, u.name, u.admin, u.banned FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.hash = ? AND s.expires > ?",
  ).bind(await sha256(m[1]), now()).first();
  if (!row) return null;
  return { ...row, admin: !!row.admin, banned: !!row.banned };
}

async function readBody(req) {
  const text = await req.text();
  if (text.length > MAX_BODY) throw new Error("too big");
  return text ? JSON.parse(text) : {};
}

function present(row, me) {
  return {
    id: row.id, kind: row.kind, data: JSON.parse(row.data), score: row.score, created: row.created,
    updated: row.updated, promoted: !!row.promoted, hidden: !!row.hidden, reports: me?.admin ? row.reports : undefined,
    author: { id: row.author_id, name: row.author_name }, voted: !!row.voted, mine: !!me && me.id === row.author_id,
  };
}

const SELECT = `SELECT p.*, u.name AS author_name, %VOTED% AS voted FROM posts p JOIN users u ON u.id = p.author_id`;
const selectFor = (me) => SELECT.replace("%VOTED%", me
  ? "EXISTS(SELECT 1 FROM votes v WHERE v.post_id = p.id AND v.user_id = ?1)" : "0");

// ------------------------------------------------------------------ joining (no login)
async function join(req, env) {
  const { name } = await readBody(req);
  const clean = String(name || "").trim();
  if (!NAME.test(clean)) return fail(400, "Pick a name of 2-24 letters, numbers, spaces, _ . or -.");
  const day = new Date().toISOString().slice(0, 10);
  const ip = await sha256((req.headers.get("cf-connecting-ip") || "local") + "|" + day);
  await env.DB.prepare("DELETE FROM joins WHERE day <> ?").bind(day).run();
  const seen = await env.DB.prepare("SELECT n FROM joins WHERE ip = ?").bind(ip).first();
  if (seen && seen.n >= Number(env.JOINS_PER_DAY || 5)) return fail(429, "Too many new board accounts from here today - try tomorrow.");
  await env.DB.prepare("INSERT INTO joins (ip, n, day) VALUES (?, 1, ?) ON CONFLICT(ip) DO UPDATE SET n = n + 1").bind(ip, day).run();
  const id = "u" + randomHex(8), token = randomHex(32);
  await env.DB.batch([
    env.DB.prepare("INSERT INTO users (id, name, created) VALUES (?, ?, ?)").bind(id, clean, now()),
    env.DB.prepare("INSERT INTO sessions (hash, user_id, created, expires) VALUES (?, ?, ?, ?)")
      .bind(await sha256(token), id, now(), now() + SESSION_DAYS * DAY),
  ]);
  return json({ token, user: { id, name: clean, admin: false } }, 201);
}

async function rename(req, env, me) {
  const { name } = await readBody(req);
  const clean = String(name || "").trim();
  if (!NAME.test(clean)) return fail(400, "Pick a name of 2-24 letters, numbers, spaces, _ . or -.");
  await env.DB.prepare("UPDATE users SET name = ? WHERE id = ?").bind(clean, me.id).run();
  return json({ user: { id: me.id, name: clean, admin: me.admin } });
}

async function becomeAdmin(req, env, me) {
  const { key } = await readBody(req);
  if (!env.ADMIN_KEY || String(env.ADMIN_KEY).length < 8 || !sameText(key, env.ADMIN_KEY))
    return fail(403, "That isn't the admin key.");
  await env.DB.prepare("UPDATE users SET admin = 1 WHERE id = ?").bind(me.id).run();
  return json({ user: { id: me.id, name: me.name, admin: true } });
}

// ------------------------------------------------------------------ posts
async function listPosts(url, env, me) {
  const p = url.searchParams;
  const kind = p.get("kind") === "one" ? "one" : "strat";
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
  const probs = validateOne(base);
  return probs.length ? { probs } : { data: tidy(base, RULES.one_order) };
}

const searchText = (d) => [d.name, d.summary, d.text, d.type, d.category, ...(d.tags ?? []), ...(d.steps ?? [])]
  .filter(Boolean).join(" ").toLowerCase();

async function createPost(req, env, me) {
  const body = await readBody(req);
  const kind = body.kind === "one" ? "one" : "strat";
  const today = await env.DB.prepare("SELECT COUNT(*) AS n FROM posts WHERE author_id = ? AND created > ?").bind(me.id, now() - DAY).first();
  if (today.n >= Number(env.POSTS_PER_DAY || 10) && !me.admin) return fail(429, "That's enough posts for today - try again tomorrow.");
  const r = prepare(kind, body.data ?? {}, me, null);
  if (r.probs) return json({ error: "Not in the standard layout: " + r.probs[0], problems: r.probs }, 400);
  const t = now();
  const res = await env.DB.prepare(`INSERT INTO posts (kind, author_id, data, search, category, type, tags, created, updated)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`).bind(kind, me.id, JSON.stringify(r.data), searchText(r.data), r.data.category ?? null,
    r.data.type ?? null, "|" + (r.data.tags ?? []).join("|") + "|", t, t).run();
  const id = res.meta.last_row_id;
  r.data.id = `board-${id}`;
  await env.DB.prepare("UPDATE posts SET data = ? WHERE id = ?").bind(JSON.stringify(r.data), id).run();
  return json({ post: present(await getPost(env, me, id), me) }, 201);
}

async function updatePost(req, env, me, id) {
  const row = await getPost(env, me, id);
  if (!row) return fail(404, "not found");
  if (row.author_id !== me.id) return fail(403, "only its author can change it");
  const body = await readBody(req);
  const r = prepare(row.kind, body.data ?? {}, me, id);
  if (r.probs) return json({ error: "Not in the standard layout: " + r.probs[0], problems: r.probs }, 400);
  await env.DB.prepare("UPDATE posts SET data = ?, search = ?, category = ?, type = ?, tags = ?, updated = ? WHERE id = ?")
    .bind(JSON.stringify(r.data), searchText(r.data), r.data.category ?? null, r.data.type ?? null,
      "|" + (r.data.tags ?? []).join("|") + "|", now(), id).run();
  return json({ post: present(await getPost(env, me, id), me) });
}

async function deletePost(env, me, id) {
  const row = await getPost(env, me, id);
  if (!row) return fail(404, "not found");
  if (row.author_id !== me.id && !me.admin) return fail(403, "only its author or an admin can delete it");
  await env.DB.batch([
    env.DB.prepare("DELETE FROM posts WHERE id = ?").bind(id),
    env.DB.prepare("DELETE FROM votes WHERE post_id = ?").bind(id),
    env.DB.prepare("DELETE FROM reports WHERE post_id = ?").bind(id),
  ]);
  return json({ ok: true });
}

async function vote(req, env, me, id) {
  const body = await readBody(req);
  const row = await getPost(env, me, id);
  if (!row || (row.hidden && !me.admin)) return fail(404, "not found");
  if (body.up === false) await env.DB.prepare("DELETE FROM votes WHERE post_id = ? AND user_id = ?").bind(id, me.id).run();
  else await env.DB.prepare("INSERT OR IGNORE INTO votes (post_id, user_id, created) VALUES (?, ?, ?)").bind(id, me.id, now()).run();
  await env.DB.prepare("UPDATE posts SET score = (SELECT COUNT(*) FROM votes WHERE post_id = ?1) WHERE id = ?1").bind(id).run();
  return json({ post: present(await getPost(env, me, id), me) });
}

async function report(req, env, me, id) {
  const body = await readBody(req);
  const row = await getPost(env, me, id);
  if (!row) return fail(404, "not found");
  await env.DB.prepare("INSERT OR IGNORE INTO reports (post_id, user_id, reason, created) VALUES (?, ?, ?, ?)")
    .bind(id, me.id, String(body.reason || "").slice(0, 200), now()).run();
  const n = (await env.DB.prepare("SELECT COUNT(*) AS n FROM reports WHERE post_id = ?").bind(id).first()).n;
  const hide = n >= Number(env.REPORT_HIDE || 3) ? 1 : row.hidden;
  await env.DB.prepare("UPDATE posts SET reports = ?, hidden = ? WHERE id = ?").bind(n, hide, id).run();
  return json({ ok: true, hidden: !!hide });
}

async function adminPost(req, env, me, id) {
  if (!me.admin) return fail(403, "admins only");
  const { action } = await readBody(req);
  const set = { hide: "hidden = 1", unhide: "hidden = 0, reports = 0", promote: "promoted = 1", unpromote: "promoted = 0" }[action];
  if (!set) return fail(400, "action: hide, unhide, promote or unpromote");
  if (action === "unhide") await env.DB.prepare("DELETE FROM reports WHERE post_id = ?").bind(id).run();
  await env.DB.prepare(`UPDATE posts SET ${set} WHERE id = ?`).bind(id).run();
  const row = await getPost(env, me, id);
  return row ? json({ post: present(row, me) }) : fail(404, "not found");
}

async function ban(req, env, me, userId) {
  if (!me.admin) return fail(403, "admins only");
  const { banned } = await readBody(req);
  await env.DB.prepare("UPDATE users SET banned = ? WHERE id = ?").bind(banned === false ? 0 : 1, userId).run();
  if (banned !== false) await env.DB.prepare("UPDATE posts SET hidden = 1 WHERE author_id = ?").bind(userId).run();
  return json({ ok: true });
}

async function official(env) {
  const rows = await env.DB.prepare(`SELECT p.*, u.name AS author_name, 0 AS voted FROM posts p JOIN users u ON u.id = p.author_id
    WHERE p.promoted = 1 AND p.hidden = 0 ORDER BY p.score DESC`).all();
  const out = { strats: [], oneliners: [] };
  for (const r of rows.results) (r.kind === "one" ? out.oneliners : out.strats).push(JSON.parse(r.data));
  return json(out);
}

// ------------------------------------------------------------------ routing
export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const m = /^\/posts\/(\d+)(?:\/(vote|report|admin))?$/.exec(path);
    try {
      if (path === "/" || path === "/health") return json({ ok: true, schema: RULES.schema });
      if (path === "/auth/join" && req.method === "POST") return join(req, env);
      if (path === "/official") return official(env);
      const me = await who(req, env);
      if (path === "/me") return me ? json({ user: me }) : fail(401, "sign in first");
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
      if (path === "/auth/admin" && req.method === "POST") return becomeAdmin(req, env, me);
      if (me.banned) return fail(403, "This account can't post on the board.");
      if (path === "/posts" && req.method === "POST") return createPost(req, env, me);
      if (m && !m[2] && req.method === "PUT") return updatePost(req, env, me, Number(m[1]));
      if (m && !m[2] && req.method === "DELETE") return deletePost(env, me, Number(m[1]));
      if (m && m[2] === "vote" && req.method === "POST") return vote(req, env, me, Number(m[1]));
      if (m && m[2] === "report" && req.method === "POST") return report(req, env, me, Number(m[1]));
      if (m && m[2] === "admin" && req.method === "POST") return adminPost(req, env, me, Number(m[1]));
      const b = /^\/users\/([a-z0-9]{1,40})\/ban$/.exec(path);
      if (b && req.method === "POST") return ban(req, env, me, b[1]);
      return fail(404, "not found");
    } catch (e) {
      if (e instanceof SyntaxError || e.message === "too big") return fail(400, "bad request");
      return fail(500, "server error");
    }
  },
};
