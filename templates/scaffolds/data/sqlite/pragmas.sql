-- Canonical SQLite init block (STK-SQLITE-02). Apply on EVERY new connection,
-- from the single connect helper — foreign_keys and busy_timeout are per-connection.
PRAGMA journal_mode = WAL;      -- readers never block the writer
PRAGMA foreign_keys = ON;       -- per-connection; OFF is the (wrong) default
PRAGMA busy_timeout = 5000;     -- wait, don't throw, on writer contention
PRAGMA synchronous = NORMAL;    -- the sanctioned pairing with WAL
