-- 0001: summary runs. One row per csvsum invocation that persisted results.
CREATE TABLE runs (
    id         INTEGER PRIMARY KEY,
    source     TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
