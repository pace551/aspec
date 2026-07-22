-- 0002: per-column statistics, one row per column per run.
-- Later schema changes are NEW numbered files, never edits to this one.
CREATE TABLE column_stats (
    id      INTEGER PRIMARY KEY,
    run_id  INTEGER NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    name    TEXT NOT NULL,
    count   INTEGER NOT NULL,
    numeric INTEGER NOT NULL,  -- 0/1 boolean
    minimum REAL,
    maximum REAL,
    mean    REAL
);

CREATE INDEX idx_column_stats_run_id ON column_stats (run_id);
