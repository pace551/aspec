---
id: DATA-MODELING
title: Data Modeling & Migrations
family: DATA
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - migration
  - schema
  - database
  - table
  - column
  - alembic
  - dbmate
  - drizzle
  - backfill
  - alter table
requires: []
verification:
  - cmd: "attest: every schema change since last verify shipped as a numbered, committed, forward-only migration"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-MODELING-01]
  - cmd: "attest: each migration was applied to a copy of production data before production"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-MODELING-02]
    tiers: [T3, T4]
  - cmd: "attest: live-table changes followed expand → migrate data → contract; no in-place rename/type-change on a serving column"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-MODELING-03]
    tiers: [T3, T4]
  - cmd: "attest: every table has a primary key and created_at/updated_at"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-MODELING-04]
  - cmd: "attest: production schema equals migrations replayed from zero — no console/ad-hoc DDL drift"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-MODELING-05]
    tiers: [T3, T4]
  - cmd: "attest: delete semantics (soft vs hard) were chosen consciously per table and recorded"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-MODELING-06]
  - cmd: "attest: backfills ran as committed, idempotent, resumable migration scripts"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-MODELING-07]
last_review: 2026-07-22
---

# Data Modeling & Migrations (DATA-MODELING)

## Abstract

Schema is versioned code. This standard retires the two classic database failures: a
production schema nobody can reproduce (ad-hoc DDL drift) and a migration that takes the
product down (rename-in-place on a live table). Compliance in one breath: every schema
change is a numbered, committed, forward-only migration; at T3+ each is rehearsed on a
copy of prod and live changes follow expand → migrate → contract; every table has a primary
key and timestamps; delete semantics are a conscious choice; backfills are migrations too.
Tool choice (alembic, dbmate, drizzle-kit) belongs to the stack standards — this one
governs the discipline, not the tool.

## Normative Rules

### DATA-MODELING-01 — Schema changes MUST ship as forward-only, numbered, committed migrations

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

One migration per change, monotonically numbered (or timestamped), committed in the same
PR as the code that needs it. Forward-only: recovery from a bad migration is a new forward
migration, not a `down` script — down migrations lie under data loss and are not
maintained. The tool is per-stack (alembic for Python/Postgres, dbmate or raw SQL for
SQLite, drizzle-kit for TypeScript — see `STK-PG` / `STK-SQLITE`); the discipline is
identical. Editing an already-applied migration file is a violation — append a new one.

### DATA-MODELING-02 — Every migration MUST be tested against a copy of production data before production

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

A migration that succeeds on an empty dev database proves almost nothing. At T3+, run it
against a restored backup or snapshot copy first (this doubles as the restore drill
`OPS-BACKUP` wants) and note the runtime — a 40-minute `ALTER TABLE` discovered in prod is
an outage, discovered on the copy it's a plan. At T1/T2, `cp app.db app.db.bak` before
migrating is the advisory version of the same idea.

### DATA-MODELING-03 — Live-table changes MUST use expand → migrate data → contract

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

Never rename-in-place, retype-in-place, or drop-then-recreate a column the running code
reads. Sequence: **expand** (add the new column/table, nullable or defaulted; deploy code
that writes both, reads old), **migrate data** (backfill per DATA-MODELING-07), **contract**
(deploy code reading the new column; later, a separate migration drops the old). Each step
is independently deployable and independently revertible by rolling code forward. n/a at
T1/T2 because with no other users there is no live traffic to protect — stop the app,
migrate, restart.

### DATA-MODELING-04 — Every table MUST have a primary key and created_at/updated_at

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Primary key always (surrogate or natural — chosen, not defaulted). `created_at` and
`updated_at` (UTC, set by the database or a single write path) on every table: they cost
nothing at creation time and are the difference between answering "when did this row go
bad" and guessing. Exceptions (append-only event logs may skip `updated_at`, pure junction
tables may use a composite key) are fine — noted in the schema comment, not silently.

### DATA-MODELING-05 — Production schema MUST equal the migrations replayed

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

No ad-hoc schema drift: nothing reaches the prod schema except the migration runner — no
console `ALTER TABLE`, no ORM `create_all()` against prod, no "quick manual index". If an
emergency forced a manual change, the follow-up is immediate: capture it as a numbered
migration marked applied, so replay-from-zero still reproduces reality. Drift found during
verify is remediated the same way.

### DATA-MODELING-06 — Delete semantics MUST be a conscious per-table choice

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Soft-delete (`deleted_at` timestamp) vs hard-delete is decided per table when the table is
born, recorded in a schema comment or the project `CLAUDE.md`. Soft-delete keeps history
and referential integrity but every query must filter it and the rows still count as
retained data; hard-delete is clean but unrecoverable. `DATA-RETENTION` owns how long
either variant may live — a soft-deleted PII row is not deleted for retention purposes.

### DATA-MODELING-07 — Backfills MUST be idempotent, resumable migrations

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

A backfill is a migration with a long runtime, not a one-off script pasted into a REPL:
committed, batched (bounded transactions, not one giant `UPDATE`), idempotent (safe to
rerun after dying at row 400k — `WHERE new_col IS NULL` style predicates), and resumable
from where it stopped. `ARC-IDEMPOTENCY` carries the general pattern; the migration runner
records completion so it never double-runs.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attest: changes shipped as numbered forward-only migrations | explicit yes | DATA-MODELING-01 |
| 2 | attest: migrations rehearsed on a prod copy (T3+) | explicit yes | DATA-MODELING-02 |
| 3 | attest: expand/migrate/contract on live tables (T3+) | explicit yes | DATA-MODELING-03 |
| 4 | attest: PK + timestamps on every table | explicit yes | DATA-MODELING-04 |
| 5 | attest: no schema drift vs replayed migrations (T3+) | explicit yes | DATA-MODELING-05 |
| 6 | attest: delete semantics chosen and recorded | explicit yes | DATA-MODELING-06 |
| 7 | attest: backfills idempotent + resumable | explicit yes | DATA-MODELING-07 |

**Remediation:** drift detected → diff prod schema against replayed migrations, capture the
delta as a new migration marked applied · slow migration found in rehearsal → batch it or
schedule a window · edited historical migration → revert the edit, append a new migration.

## Worked Example

Renaming `users.name` → `users.full_name` on a live T3 Postgres table, dbmate-style:

```sql
-- db/migrations/20260722100000_expand_full_name.sql
ALTER TABLE users ADD COLUMN full_name text;            -- expand (code now writes both)

-- db/migrations/20260722110000_backfill_full_name.sql   -- idempotent backfill
UPDATE users SET full_name = name
WHERE full_name IS NULL AND id IN (
  SELECT id FROM users WHERE full_name IS NULL LIMIT 10000);  -- rerun until 0 rows

-- db/migrations/20260801100000_contract_drop_name.sql   -- after code reads full_name
ALTER TABLE users DROP COLUMN name;
```

Three migrations, three deploys, zero downtime — versus one `ALTER TABLE users RENAME
COLUMN`, which breaks every running replica the instant it commits.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `RENAME COLUMN` on a serving table | Old code errors instantly; no gradual path | Expand → migrate → contract (DATA-MODELING-03) |
| Editing an applied migration file | Replayed-from-zero schema diverges from prod | Append a new migration (DATA-MODELING-01) |
| Maintaining `down` migrations | Untested, lossy, false confidence | Forward-only; fix forward |
| Console DDL "just this once" | Prod becomes unreproducible; next migration fails oddly | Migration runner only (DATA-MODELING-05) |
| One-transaction `UPDATE` over 10M rows | Lock storm, replication lag, unkillable | Batched idempotent backfill (DATA-MODELING-07) |
| ORM `create_all()` as prod schema management | No history, no rehearsal, silent drift | Real migrations from day one |
| Soft-delete "to be safe" everywhere | Every query grows a filter; retention obligations persist | Per-table conscious choice (DATA-MODELING-06) |

## References

- Braintree/PayPal "PostgreSQL at Scale: Database Schema Changes Without Downtime" — the
  canonical expand/contract write-up DATA-MODELING-03 condenses.
- dbmate and alembic docs — the two house migration runners; both enforce
  numbered-and-recorded application (DATA-MODELING-01, -05).
- Stripe engineering on online migrations (dual-write pattern) — source for the
  backfill batching/idempotency guidance in DATA-MODELING-07.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
