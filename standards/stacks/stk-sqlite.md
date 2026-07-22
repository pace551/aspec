---
id: STK-SQLITE
title: SQLite
family: STK
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [sqlite]
triggers:
  - sqlite
  - sqlite3
  - litestream
  - wal
  - local database
  - embedded database
  - db file
  - schema_migrations
requires: []
verification:
  - cmd: "sh -c 'grep -rqiIE \"journal_mode *= *.?wal\" --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=.git . && grep -rqiIE \"foreign_keys *= *(on|1|true)\" --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=.git . && grep -rqiI \"busy_timeout\" --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=.git .'"
    expect: "exit 0 — canonical pragma block (WAL + foreign_keys + busy_timeout) present in the tree"
    layer: G
    rules: [STK-SQLITE-02]
  - cmd: "bash ~/Dev/claude-code/governance/checks/sec-sast.sh"
    expect: "exit 0 — no string-built SQL (bandit B608 / semgrep; shared gate with SEC-SAST)"
    layer: G
    rules: [STK-SQLITE-03]
  - cmd: "sh -c '[ ! -d migrations ] || ls migrations | grep -qE \"^[0-9]+_.+[.]sql$\"'"
    expect: "exit 0 — migrations/ (when present) contains numbered NNNN_name.sql files"
    layer: G
    rules: [STK-SQLITE-04]
    tiers: [T2, T3, T4]
  - cmd: "attest: the datastore choice followed STK-SQLITE-01 (SQLite by default; a server database only with a stated workload reason)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-SQLITE-01]
  - cmd: "attest: no connection object is shared across threads or concurrent async tasks"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-SQLITE-05]
  - cmd: "attest: backups use the backup API or Litestream — no file-copy of a live database anywhere in scripts or cron"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-SQLITE-06]
  - cmd: "attest: tables created in this project's migrations are STRICT (or the deviation is noted)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-SQLITE-07]
last_review: 2026-07-22
---

# SQLite (STK-SQLITE)

## Abstract

SQLite is the house default datastore: T1/T2 almost always, and single-writer T3 web
apps ship on it with Litestream replication instead of reflexively reaching for a server
database. This standard pins what makes that safe: the canonical pragma init block (WAL,
`foreign_keys`, `busy_timeout`), parameterized queries only, numbered `.sql` migrations
tracked in `schema_migrations`, one connection per thread/task, backups via the backup
API or Litestream (never file-copy of a live db), and STRICT tables on new schemas.
Worked example: `examples/python/` · scaffold fragment:
`templates/scaffolds/data/sqlite/`.

## Normative Rules

### STK-SQLITE-01 — SQLite SHOULD be the default datastore until the workload proves otherwise

**Tiers**: all advisory — **Layer**: A (attestation)

T1/T2: SQLite unless there is a concrete blocker — zero ops, one file, trivially
testable and backed up. T3: still right for single-writer web apps (one app process;
WAL readers are unlimited) when paired with Litestream continuous replication
(STK-SQLITE-06, OPS-BACKUP). Reach for PostgreSQL (STK-PG) when any of these hold:
multiple concurrently-writing services or nodes, sustained concurrent write throughput,
need for database-level roles/row security, or a managed-HA requirement. Choosing
Postgres at T1 needs a stated reason; choosing SQLite for a deployed T3 app needs
Litestream. Never both stores in one project for the same data.

### STK-SQLITE-02 — Every connection MUST apply the canonical pragma init block

**Tiers**: all required — **Layer**: G

The block, verbatim (also shipped as `templates/scaffolds/data/sqlite/pragmas.sql`):

```sql
PRAGMA journal_mode = WAL;      -- readers never block the writer
PRAGMA foreign_keys = ON;       -- per-connection; OFF is the (wrong) default
PRAGMA busy_timeout = 5000;     -- wait, don't throw, on writer contention
PRAGMA synchronous = NORMAL;    -- the sanctioned pairing with WAL
```

`journal_mode` is persistent but is set anyway so a fresh file is correct;
`foreign_keys` and `busy_timeout` are per-connection and therefore MUST live in the one
connect helper every caller uses — not in a migration, not scattered per call site.

### STK-SQLITE-03 — SQL MUST be parameterized; string-built SQL is forbidden

**Tiers**: all required — **Layer**: G

Values travel via placeholders (`?` or `:name`), never f-strings/concatenation — the
general injection rule is SEC-INPUT; the machine gate is the shared SAST scan
(`checks/sec-sast.sh`, bandit B608 for Python — SEC-SAST). Identifiers (table/column
names) cannot be parameterized: if they must vary, select them from a hardcoded
allowlist, never from input.

### STK-SQLITE-04 — Schema changes MUST ship as numbered `.sql` migrations recorded in `schema_migrations`

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

`migrations/NNNN_name.sql`, applied in filename order, each inside one transaction that
also inserts its version row into `schema_migrations(version, applied_at)`.
Forward-only: no down migrations — going back is a restore (STK-SQLITE-06). The runner
is ~20 lines: `templates/scaffolds/data/sqlite/migrate.sh` (shell) or the Python
variant in `examples/python/`. ORM "auto-create tables on startup" is acceptable only
at T1.

### STK-SQLITE-05 — Connections MUST NOT be shared across threads or concurrent async tasks

**Tiers**: all required — **Layer**: A (attestation)

One connection per thread (leave `check_same_thread=True`); in async code, one
connection per task or a wrapper that serializes access (e.g. `aiosqlite`, which queues
internally). Web apps: connection-per-request is correct and cheap — with WAL +
`busy_timeout`, writer contention resolves by waiting, not by sharing. Keep write
transactions short; a long-lived open transaction blocks WAL checkpointing and grows
the `-wal` file without bound.

### STK-SQLITE-06 — Live databases MUST be backed up via the backup API or Litestream — never file-copy

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

`cp`/`rsync` of a live WAL database races the `-wal`/`-shm` files and yields a corrupt
or stale copy. Sanctioned mechanisms: `sqlite3 app.db ".backup backup.db"`,
`VACUUM INTO`, or Litestream streaming to S3 (the default for deployed T3+ apps — it is
also the replication story that keeps SQLite viable at T3, per STK-SQLITE-01). Cadence,
retention and restore-testing requirements live in OPS-BACKUP.

### STK-SQLITE-07 — New schemas SHOULD declare STRICT tables

**Tiers**: all advisory — **Layer**: A (attestation)

`CREATE TABLE … ( … ) STRICT;` makes SQLite reject type-mismatched inserts instead of
silently coercing via type affinity (requires SQLite ≥ 3.37, universal on current
platforms). Applies to newly created tables; retrofitting existing tables is not
required. Money is integer cents in a STRICT `INTEGER` column, never `REAL`.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | chained grep for `journal_mode…WAL`, `foreign_keys…ON`, `busy_timeout` | all three patterns found in the tree | STK-SQLITE-02 |
| 2 | `bash ~/Dev/claude-code/governance/checks/sec-sast.sh` | exit 0 — no string-built SQL findings | STK-SQLITE-03 |
| 3 | `[ ! -d migrations ] \|\| ls migrations \| grep -qE "^[0-9]+_.+[.]sql$"` (T2+) | migrations dir absent, or contains numbered files | STK-SQLITE-04 |
| 4–7 | attestation checklist (one per rule) | explicit yes recorded | STK-SQLITE-01, -05, -06, -07 |

**Remediation:** pragma grep fails → copy `templates/scaffolds/data/sqlite/pragmas.sql`
into the single connect helper · B608 finding → replace f-string SQL with `?`
placeholders · unnumbered migration files → rename to `NNNN_description.sql` (next free
number, never reuse) · live-db `cp` found in a script → switch to `.backup`/`VACUUM
INTO`; if the copy already happened, treat the copy as suspect and re-take it properly.

## Worked Example

`examples/python/` carries the full living example (connect helper, migration runner,
parameterized queries) — the SQLite usage there is this standard in code. The
load-bearing fragment:

```python
import sqlite3

def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=5)  # seconds; belt to busy_timeout's braces
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.row_factory = sqlite3.Row
    return conn
```

Scaffold fragment (`templates/scaffolds/data/sqlite/`): `pragmas.sql`, `migrate.sh`,
`migrations/0001_init.sql` — merged into a backend scaffold by `/bootstrap-repo`.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| f-string / concatenated SQL | Injection; bandit B608 | Placeholders (STK-SQLITE-03) |
| `cp app.db backup/` on a live db | Races `-wal`/`-shm`; corrupt copy | `.backup`, `VACUUM INTO`, Litestream (STK-SQLITE-06) |
| One global connection used by all threads | `ProgrammingError` or silent races | Connection per thread/request (STK-SQLITE-05) |
| Skipping `busy_timeout` | Random `database is locked` errors under write load | Canonical pragma block (STK-SQLITE-02) |
| Default rollback journal (no WAL) | Writers block readers; needless contention | WAL mode (STK-SQLITE-02) |
| ORM auto-migrate on startup at T2+ | No history, no review, drift between envs | Numbered `.sql` + `schema_migrations` (STK-SQLITE-04) |
| Relying on type affinity ("it stores anyway") | Silent coercion, strings in number columns | STRICT tables (STK-SQLITE-07) |
| Postgres "because it's more real" at T1 | Ops burden with zero payoff | SQLite until the workload objects (STK-SQLITE-01) |

## References

- SQLite WAL documentation (sqlite.org/wal.html) — why WAL + `synchronous=NORMAL` is
  the sanctioned pairing and what checkpointing implies for long transactions.
- SQLite backup docs (sqlite.org/backup.html) + `VACUUM INTO` — why file-copy of a live
  db is unsafe and what the supported copies are.
- SQLite STRICT tables (sqlite.org/stricttables.html) — the opt-in that retires the
  type-affinity footgun class.
- Litestream docs (litestream.io) — continuous S3 replication; the T3 story for SQLite.
- SQLite "Appropriate Uses" (sqlite.org/whentouse.html) — the basis for
  STK-SQLITE-01's "default until proven otherwise" stance.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
