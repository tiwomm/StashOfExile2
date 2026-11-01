-- StashOfExile2 community board (D1 / SQLite). Safe to run again: everything is IF NOT EXISTS.
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,                -- Discord user id
  name TEXT NOT NULL,
  avatar TEXT,
  banned INTEGER NOT NULL DEFAULT 0,
  created INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  hash TEXT PRIMARY KEY,              -- sha256 of the token the app keeps
  user_id TEXT NOT NULL,
  created INTEGER NOT NULL,
  expires INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS logins (   -- a sign-in in progress: the app polls with its state until the token is here
  state TEXT PRIMARY KEY,
  token TEXT,
  user_id TEXT,
  created INTEGER NOT NULL
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
