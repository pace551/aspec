# CLAUDE.md — csvsum

CSV-to-summary CLI with SQLite persistence. Worked example for STK-PY and the house
SQLite pattern (stdlib `sqlite3`, parameterized queries, numbered `.sql` migrations
tracked in `schema_migrations`).

Governed project — tier and applicable standards in `GOVERNANCE.md`; run
`/verify-compliance` before calling any work done (Constitution C2).

## Structure

```
examples/python/
├── pyproject.toml            # single config home (STK-PY-01)
├── src/csvsum/
│   ├── cli.py                # argparse entry point
│   ├── summarize.py          # pure column-stats logic (no I/O)
│   ├── db.py                 # sqlite3 + migrations runner
│   └── migrations/           # 0001_…​.sql, 0002_…​.sql — applied in order, never edited
├── tests/                    # summarize / db / cli tests
└── scripts/                  # lint.sh + test.sh (scripts contract)
```

## Commands

All commands runnable verbatim from repo root (no activation, no cd — STK-PY-08):

```bash
scripts/lint.sh                            # ruff format --check + ruff check (same gate as hook and CI)
scripts/test.sh                            # pytest + coverage.json (same gate as hook and CI)
.venv/bin/csvsum data.csv --db runs.db     # run the thing
```

Setup once: `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`

## Gotchas

- Migrations are append-only: schema changes are a new `NNNN_name.sql` file, never an
  edit to an applied one (`schema_migrations` tracks by filename).
- bandit runs with no skips — SQL is parameterized everywhere; keep it that way (B608
  findings are fixed, never suppressed, per STK-PY-04).
