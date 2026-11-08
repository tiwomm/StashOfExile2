-- StashOfExile2 community board (D1 / SQLite). Safe to run again: everything is IF NOT EXISTS.
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,                -- made by the board (no login: one per install)
  name TEXT NOT NULL,
  admin INTEGER NOT NULL DEFAULT 0,   -- set by entering ADMIN_KEY in the app
  banned INTEGER NOT NULL DEFAULT 0,
  created INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  hash TEXT PRIMARY KEY,              -- sha256 of the token the app keeps
  user_id TEXT NOT NULL,
  created INTEGER NOT NULL,
  expires INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS joins (    -- new accounts per internet address per day (stops vote stuffing)
  ip TEXT NOT NULL,                   -- sha256 of the address + the day, never the address itself
  n INTEGER NOT NULL,
  day TEXT NOT NULL,
  PRIMARY KEY (ip)
);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,                 -- 'strat' or 'one'
  author_id TEXT NOT NULL,
  data TEXT NOT NULL,                 -- the strat / one-liner JSON (the standard layout)
  search TEXT NOT NULL,               -- lower-case text for search
  category TEXT, type TEXT, tags TEXT,
  score INTEGER NOT NULL DEFAULT 0,
  reports INTEGER NOT NULL DEFAULT 0,
  hidden INTEGER NOT NULL DEFAULT 0,
  promoted INTEGER NOT NULL DEFAULT 0,
  created INTEGER NOT NULL,
  updated INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS posts_list ON posts (kind, hidden, score, created);
CREATE TABLE IF NOT EXISTS votes (
  post_id INTEGER NOT NULL, user_id TEXT NOT NULL, created INTEGER NOT NULL,
  PRIMARY KEY (post_id, user_id)
);
CREATE TABLE IF NOT EXISTS reports (
  post_id INTEGER NOT NULL, user_id TEXT NOT NULL, reason TEXT, created INTEGER NOT NULL,
  PRIMARY KEY (post_id, user_id)
);
-- 2.31.0: the community Mod book. Each install sends, at most once an hour, a summary of the listings its price
-- checks saw: per (base, mod) how many and their median price. Kept as a weighted mean of log prices, so one
-- install can't swing a price (its weight per batch is capped) and nothing about the listing or player is stored.
CREATE TABLE IF NOT EXISTS mod_prices (
  league TEXT NOT NULL, base TEXT NOT NULL, sid TEXT NOT NULL,
  n INTEGER NOT NULL DEFAULT 0,       -- listings behind it
  w REAL NOT NULL DEFAULT 0,          -- total weight
  slog REAL NOT NULL DEFAULT 0,       -- sum of weight * ln(median)
  batches INTEGER NOT NULL DEFAULT 0, -- how many summaries (roughly: how many players / hours)
  updated INTEGER NOT NULL,
  PRIMARY KEY (league, base, sid)
);
CREATE TABLE IF NOT EXISTS base_prices (
  league TEXT NOT NULL, base TEXT NOT NULL,
  n INTEGER NOT NULL DEFAULT 0, w REAL NOT NULL DEFAULT 0, slog REAL NOT NULL DEFAULT 0,
  batches INTEGER NOT NULL DEFAULT 0, updated INTEGER NOT NULL,
  PRIMARY KEY (league, base)
);
CREATE TABLE IF NOT EXISTS mod_votes (  -- a player's own Mod book rules (High / Normal / Ignore) count as their vote
  key TEXT NOT NULL, cid TEXT NOT NULL, value TEXT NOT NULL, updated INTEGER NOT NULL,
  PRIMARY KEY (key, cid)
);
CREATE TABLE IF NOT EXISTS contributors (
  cid TEXT PRIMARY KEY,               -- sha256 of the install's random id
  last INTEGER NOT NULL, batches INTEGER NOT NULL DEFAULT 0
);
-- 2.32.0: map ranks (Session tracker > Map library). A player's own ranks count as their vote.
CREATE TABLE IF NOT EXISTS map_votes (
  name TEXT NOT NULL, cid TEXT NOT NULL, rank TEXT NOT NULL, updated INTEGER NOT NULL,
  PRIMARY KEY (name, cid)
);

-- 2.48.0: bug reports from the app (POST /bugs) - only a per-address count per day, to stop floods
CREATE TABLE IF NOT EXISTS bug_limits (ip TEXT PRIMARY KEY, n INTEGER NOT NULL, day TEXT NOT NULL);

-- 2.77.0: campaign zones a player's guide pack didn't know (POST /mods/batch "zones"); GET /campaign/zones pools them
CREATE TABLE IF NOT EXISTS campaign_zones (
  act TEXT NOT NULL, zone TEXT NOT NULL, cid TEXT NOT NULL, after TEXT NOT NULL DEFAULT '', level INTEGER NOT NULL DEFAULT 0,
  updated INTEGER NOT NULL,
  PRIMARY KEY (act, zone, cid)
);

-- 2.121.1: mod lines an install's price checks couldn't match (POST /mods/batch "unmatched": wording with numbers as #,
-- and the base type - nothing else); GET /mods/unmatched pools those seen by 2 or more installs
CREATE TABLE IF NOT EXISTS unmatched_mods (
  text TEXT NOT NULL, cid TEXT NOT NULL, base TEXT NOT NULL DEFAULT '', updated INTEGER NOT NULL,
  PRIMARY KEY (text, cid)
);

-- 2.78.0: atlas screenshots for strats (POST /images, GET /images/<id>) - small JPEGs, a strat names one "b:<id>"
CREATE TABLE IF NOT EXISTS images (
  id INTEGER PRIMARY KEY AUTOINCREMENT, author_id TEXT NOT NULL, data BLOB NOT NULL, created INTEGER NOT NULL
);

-- 2.85.0: edits with history, Suggest an edit, reviewers. (New columns on users / posts are added by the Worker
-- itself on first use - ALTER TABLE ... ADD COLUMN, see migrate() in src/index.js - so old databases keep working.)
CREATE TABLE IF NOT EXISTS revisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id INTEGER NOT NULL,
  author_id TEXT NOT NULL,            -- who wrote this version (the post's author, or whoever suggested it)
  data TEXT NOT NULL,                 -- the whole strat / one-liner at this version
  status TEXT NOT NULL,               -- live, old (was live), suggested, pending (waits for reviewers), declined, withdrawn
  note TEXT NOT NULL DEFAULT '',      -- what changed and why (from the one who wrote it)
  created INTEGER NOT NULL,
  decided INTEGER, decided_by TEXT, why TEXT
);
CREATE INDEX IF NOT EXISTS revisions_post ON revisions (post_id, status);
CREATE TABLE IF NOT EXISTS reviews (  -- a reviewer's vote on a pending / suggested version or on a reported post
  target TEXT NOT NULL,               -- "rev:<id>" or "post:<id>"
  user_id TEXT NOT NULL, vote TEXT NOT NULL, created INTEGER NOT NULL,
  PRIMARY KEY (target, user_id)
);
CREATE TABLE IF NOT EXISTS limits (   -- per-day counters (edits, suggestions, reports, admin-key tries ...)
  key TEXT PRIMARY KEY, n INTEGER NOT NULL, day TEXT NOT NULL
);

-- 2.86.0: global leaderboards (the Worker also creates these itself on first use)
CREATE TABLE IF NOT EXISTS lb (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
  cat TEXT NOT NULL,                  -- campaign, map, boss, trial
  key TEXT NOT NULL,                  -- the act / map / fight
  league TEXT NOT NULL, cls TEXT NOT NULL DEFAULT '',
  secs REAL NOT NULL,                 -- the best time (self-reported, from the game's log)
  level INTEGER NOT NULL DEFAULT 0, deaths INTEGER NOT NULL DEFAULT 0,
  at INTEGER NOT NULL, sent INTEGER NOT NULL,
  reports INTEGER NOT NULL DEFAULT 0, hidden INTEGER NOT NULL DEFAULT 0,
  UNIQUE (user_id, cat, key, league, cls)
);
CREATE INDEX IF NOT EXISTS lb_board ON lb (cat, key, league, hidden, secs);
CREATE TABLE IF NOT EXISTS lb_reports (
  lb_id INTEGER NOT NULL, user_id TEXT NOT NULL, reason TEXT, created INTEGER NOT NULL,
  PRIMARY KEY (lb_id, user_id)
);
