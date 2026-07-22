"""SQLite persistence: stdlib sqlite3, parameterized queries, numbered migrations.

Migrations pattern (the house SQLite pattern):
- `migrations/` holds numbered files `NNNN_description.sql`, applied in filename order.
- Applied migrations are tracked by name in `schema_migrations`; re-running is a no-op.
- Schema changes are new files, never edits to already-applied files.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from csvsum.summarize import ColumnStats

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a connection with foreign keys enforced."""
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def apply_migrations(con: sqlite3.Connection, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending numbered migrations in order; return the names newly applied."""
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    applied = {row[0] for row in con.execute("SELECT name FROM schema_migrations")}
    newly_applied: list[str] = []
    for path in sorted(migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        if path.name in applied:
            continue
        con.executescript(path.read_text(encoding="utf-8"))
        con.execute("INSERT INTO schema_migrations (name) VALUES (?)", (path.name,))
        newly_applied.append(path.name)
    con.commit()
    return newly_applied


def record_run(con: sqlite3.Connection, source: str, stats: list[ColumnStats]) -> int:
    """Persist one summary run. Parameterized queries only — never f-strings into SQL."""
    cur = con.execute("INSERT INTO runs (source) VALUES (?)", (source,))
    run_id = cur.lastrowid
    if run_id is None:  # sqlite3 sets lastrowid after INSERT; guard for type-safety
        raise RuntimeError("INSERT INTO runs returned no row id")
    con.executemany(
        """
        INSERT INTO column_stats (run_id, name, count, numeric, minimum, maximum, mean)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [(run_id, s.name, s.count, int(s.numeric), s.minimum, s.maximum, s.mean) for s in stats],
    )
    con.commit()
    return run_id


def fetch_run(con: sqlite3.Connection, run_id: int) -> list[ColumnStats]:
    """Load the column stats recorded for a run."""
    rows = con.execute(
        """
        SELECT name, count, numeric, minimum, maximum, mean
        FROM column_stats WHERE run_id = ? ORDER BY id
        """,
        (run_id,),
    ).fetchall()
    return [
        ColumnStats(
            name=name,
            count=count,
            numeric=bool(numeric),
            minimum=minimum,
            maximum=maximum,
            mean=mean,
        )
        for name, count, numeric, minimum, maximum, mean in rows
    ]
