"""Tests for the SQLite layer: migrations pattern + parameterized round-trip."""

from csvsum.db import apply_migrations, connect, fetch_run, record_run
from csvsum.summarize import ColumnStats

STATS = [
    ColumnStats(name="price", count=3, numeric=True, minimum=1.0, maximum=9.0, mean=5.0),
    ColumnStats(name="city", count=3, numeric=False, minimum=None, maximum=None, mean=None),
]


def test_migrations_apply_in_order_and_are_tracked(tmp_path):
    con = connect(tmp_path / "t.db")
    applied = apply_migrations(con)
    assert applied == ["0001_create_runs.sql", "0002_create_column_stats.sql"]
    tracked = [r[0] for r in con.execute("SELECT name FROM schema_migrations ORDER BY name")]
    assert tracked == applied
    con.close()


def test_migrations_are_idempotent(tmp_path):
    con = connect(tmp_path / "t.db")
    apply_migrations(con)
    assert apply_migrations(con) == []  # second run applies nothing
    con.close()


def test_record_and_fetch_run_round_trip(tmp_path):
    con = connect(tmp_path / "t.db")
    apply_migrations(con)
    run_id = record_run(con, "data.csv", STATS)
    assert fetch_run(con, run_id) == STATS
    (source,) = con.execute("SELECT source FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert source == "data.csv"
    con.close()


def test_malicious_source_is_inert_data(tmp_path):
    """Parameterized queries treat hostile input as data, not SQL."""
    con = connect(tmp_path / "t.db")
    apply_migrations(con)
    evil = "x'); DROP TABLE runs; --"
    run_id = record_run(con, evil, [])
    (source,) = con.execute("SELECT source FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert source == evil  # stored verbatim; runs table still exists
    con.close()
