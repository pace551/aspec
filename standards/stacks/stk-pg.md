---
id: STK-PG
title: PostgreSQL
family: STK
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [postgresql]
triggers:
  - postgres
  - postgresql
  - rds
  - neon
  - supabase
  - alembic
  - dbmate
  - drizzle
  - pgbouncer
  - connection pool
  - jsonb
requires: []
verification:
  - cmd: "sh -c '[ -f alembic.ini ] || [ -d migrations ] || [ -d db/migrations ] || [ -f drizzle.config.ts ]'"
    expect: "exit 0 — a real migration tool's directory/config exists in the repo"
    layer: G
    rules: [STK-PG-02]
    tiers: [T2, T3, T4]
  - cmd: "sh -c '! grep -rniIwE \"timestamp\" migrations db/migrations 2>/dev/null | grep -q .'"
    expect: "exit 0 — no bare `timestamp` column type in migrations (timestamptz only)"
    layer: G
    rules: [STK-PG-06]
  - cmd: "attest: production PostgreSQL is a managed service (RDS/Aurora/Neon/Supabase) — nothing self-managed serves prod"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-PG-01]
    tiers: [T3, T4]
  - cmd: "attest: a connection pool sits between the app and postgres, sized deliberately (serverless uses RDS Proxy or a pooled driver)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-PG-03]
  - cmd: "attest: every foreign key has an index, and each added index is justified by an EXPLAIN on a real query"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-PG-04]
  - cmd: "attest: the app connects as a least-privilege role, not superuser/owner (T4: migrations run under a separate role)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-PG-05]
    tiers: [T3, T4]
  - cmd: "attest: every JSONB column holds genuinely schemaless data — none is avoidance of a relational design decision"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-PG-07]
last_review: 2026-07-22
---

# PostgreSQL (STK-PG)

## Abstract

PostgreSQL is the step up when SQLite's single-writer model runs out (STK-SQLITE-01
lists the triggers). For a solo developer the rules are about not operating a database:
managed PG only in production, migrations through a real tool, pooling as a
non-negotiable, indexes justified by `EXPLAIN` rather than vibes, least-privilege
roles, `timestamptz` everywhere, and JSONB reserved for genuinely schemaless data. N+1
query patterns are the canonical performance sin (OPS-PERF). Local dev runs the compose
fragment in `templates/scaffolds/data/postgresql/`.

## Normative Rules

### STK-PG-01 — Production PostgreSQL MUST be a managed service

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

RDS/Aurora, Neon, or Supabase — whichever fits the project's platform; the point is
that a solo dev never self-manages prod PG (patching, HA, backups, and vacuum tuning
are a second job). Automated backups/PITR MUST be enabled on the managed instance
(OPS-BACKUP owns cadence and restore tests); spend needs a budget alarm first
(Constitution C6, OPS-FINOPS). Local dev and CI use the docker compose fragment —
self-managed is fine when it's disposable.

### STK-PG-02 — Schema changes MUST go through a real migration tool

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

One tool per repo, matched to the language: `alembic` (Python), `dbmate`
(language-neutral SQL), `drizzle-kit` (TypeScript). Migrations are committed, ordered,
and forward-only in prod (rollback = a new migration or a restore). No `psql` into prod
to "just add a column", no ORM `create_all()` beyond T1 — the migration history is the
schema's source of truth. Skeleton: `templates/scaffolds/data/postgresql/migrations/`.

### STK-PG-03 — Connection pooling is non-negotiable: a pool MUST sit between app and database

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Postgres connections are expensive processes; unpooled per-request connects fall over
at double-digit concurrency. Use the app-side pool (psycopg_pool, SQLAlchemy pool,
node-postgres `Pool`) sized deliberately (start `min 1 / max 10`; `max_connections` on
small managed instances is ~100 — leave headroom). Serverless compute multiplies
connections per concurrent instance and MUST use RDS Proxy, a pooled/HTTP driver
(Neon), or pgbouncer — detail in INF-SERVERLESS.

### STK-PG-04 — Every foreign key MUST be indexed; further indexes MUST be justified by EXPLAIN

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Postgres does not auto-index FK columns; an unindexed FK makes every parent
delete/update a sequential scan of the child table. Beyond FKs, an index is added
because `EXPLAIN (ANALYZE, BUFFERS)` on a real query showed the need — not because a
column "seems queried". The N+1 pattern (one query per row of a parent result) is the
canonical sin this rule pairs with: fix with joins/`selectinload`, not with more
indexes — thresholds and profiling live in OPS-PERF.

### STK-PG-05 — The application MUST connect as a least-privilege role

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

The app user is not superuser and not the schema owner: `GRANT SELECT/INSERT/UPDATE/
DELETE` on its tables, no DDL. At T4, migrations run under a separate role that owns
the schema, so a compromised app credential cannot alter structure or read beyond its
grant. Credentials themselves follow SEC-SECRETS (SSM/Secrets Manager at T3+; never in
the connection string in code).

### STK-PG-06 — Timestamps MUST be `timestamptz`, and stored values MUST be UTC

**Tiers**: all required — **Layer**: G

House style is the short form `timestamptz` (the grep gate flags any bare word
`timestamp` in migrations, including the spelled-out `timestamp with/without time
zone`). Application code produces timezone-aware UTC datetimes (naive datetimes are
flagged by STK-PY's conventions); rendering into local time is a display concern.
`now()`/`DEFAULT now()` are fine — they are timezone-aware server-side.

### STK-PG-07 — JSONB is for genuinely schemaless data only

**Tiers**: all advisory — **Layer**: A (attestation)

Sanctioned: third-party payloads you don't control (webhook bodies, API responses),
sparse user-defined attributes. Not sanctioned: entities whose keys you enumerate in
code — that's a table wearing a disguise, unqueryable by constraint and un-migratable
by tooling. If code reads `data->>'status'` in more than one place, `status` is a
column. Index JSONB with GIN only after STK-PG-04's EXPLAIN test.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `[ -f alembic.ini ] \|\| [ -d migrations ] \|\| [ -d db/migrations ] \|\| [ -f drizzle.config.ts ]` (T2+) | a migration tool is set up | STK-PG-02 |
| 2 | `! grep -rniIwE "timestamp" migrations db/migrations 2>/dev/null \| grep -q .` | no bare `timestamp` type in migrations (`timestamptz` passes — different word) | STK-PG-06 |
| 3–7 | attestation checklist (one per rule; -01/-05 at T3+) | explicit yes recorded | STK-PG-01, -03, -04, -05, -07 |

**Remediation:** no migration tool → adopt dbmate (zero-dependency SQL) and baseline
the current schema as migration 0001 · bare `timestamp` flagged → change the column
type to `timestamptz` in a new migration (`ALTER TABLE … TYPE timestamptz USING … AT
TIME ZONE 'UTC'`) · pool exhaustion errors → check for connection leaks (missing
context manager) before raising `max` · slow FK deletes → `CREATE INDEX CONCURRENTLY`
on the child FK column.

## Worked Example

Local dev via `templates/scaffolds/data/postgresql/` (compose + env fragment +
migration skeleton). The canonical app-side shape (Python; TS mirrors it with
`pg.Pool`):

```python
import os
from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    os.environ["DATABASE_URL"],          # SEC-SECRETS: from env, no fallback
    min_size=1, max_size=10,             # STK-PG-03: sized, not defaulted
)

def get_order(order_id: int) -> dict | None:
    with pool.connection() as conn:      # returned to pool on exit
        row = conn.execute(
            "SELECT id, status, created_at FROM orders WHERE id = %s",
            (order_id,),                 # parameterized — SEC-INPUT
        ).fetchone()
        return dict(row) if row else None
```

Matching migration (`migrations/0001_init.sql`, dbmate-style):

```sql
-- migrate:up
CREATE TABLE orders (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users (id),
    status      TEXT NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX orders_user_id_idx ON orders (user_id);  -- STK-PG-04: FK indexed

-- migrate:down
DROP TABLE orders;
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Self-managed prod PG on EC2 "to save money" | Unpatched, unbacked-up, one-person pager | Managed PG; SQLite if cost matters (STK-PG-01) |
| `psql` straight into prod for schema tweaks | Untracked drift; envs diverge silently | Migration tool, committed files (STK-PG-02) |
| New connection per request, no pool | Connection storm; `too many clients` at modest load | App pool / RDS Proxy (STK-PG-03) |
| Lambda → direct PG connections | Each concurrent instance holds a connection | RDS Proxy or pooled driver (INF-SERVERLESS) |
| Query-per-row loops (N+1) | 1 request = hundreds of round trips | Join or batched `IN` query; see OPS-PERF |
| Indexing every column "for speed" | Write amplification, bloated cache, no wins | EXPLAIN-justified indexes only (STK-PG-04) |
| App connects as `postgres` superuser | Any injection = total compromise | Least-privilege role (STK-PG-05) |
| `timestamp` (no tz) + local-time writes | Ambiguous instants; DST corruption | `timestamptz`, UTC in app code (STK-PG-06) |
| JSONB "user" blob with fixed keys | Un-constrained, un-indexed, un-migrated schema | Real columns; JSONB for true schemaless (STK-PG-07) |

## References

- PostgreSQL docs: `EXPLAIN`/`ANALYZE` and index types — the evidence standard behind
  STK-PG-04.
- PostgreSQL wiki "Don't Do This" — source for the bare-`timestamp` and superuser-app
  prohibitions.
- pgbouncer / RDS Proxy docs — why external pooling exists and when app-side pools are
  insufficient (serverless fan-out).
- dbmate / alembic / drizzle-kit docs — the sanctioned per-language migration tools.
- Neon & Supabase connection docs — pooled connection strings for serverless drivers.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
