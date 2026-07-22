-- 0001_init — schema baseline. No BEGIN/COMMIT here: migrate.sh wraps each file
-- in a transaction. New tables are STRICT (STK-SQLITE-07); money is integer cents.
CREATE TABLE example (
  id         INTEGER PRIMARY KEY,
  name       TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
) STRICT;
