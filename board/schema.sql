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
