---
id: STK-DDB
title: DynamoDB
family: STK
version: 1.0.1
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [dynamodb]
triggers:
  - dynamodb
  - dynamo
  - single-table
  - single table design
  - gsi
  - access pattern
  - on-demand capacity
  - dynamodb local
requires: []
verification:
  - cmd: "sh -c '[ -f docs/access-patterns.md ] || [ -f access-patterns.md ]'"
    expect: "exit 0 — the access-pattern table exists in the repo (docs/access-patterns.md)"
    layer: G
    rules: [STK-DDB-01]
  - cmd: "sh -c '! grep -rniIE \"billing_mode[^a-z]+provisioned|provisionedthroughput\" --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.terraform . 2>/dev/null | grep -q .'"
    expect: "exit 0 — no provisioned-capacity billing declared in IaC/code"
    layer: G
    rules: [STK-DDB-02]
  - cmd: "sh -c '! grep -rnIE \"[.]scan[(]|ScanCommand\" src app lib 2>/dev/null | grep -q .'"
    expect: "exit 0 — no table scans in production code paths (admin/offline scripts live outside src/)"
    layer: G
    rules: [STK-DDB-03]
    tiers: [T3, T4]
  - cmd: "attest: multi-item invariants use TransactWriteItems/BatchWriteItem and writes that must be once-only carry condition expressions"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-DDB-04]
  - cmd: "attest: data with a natural expiry has a ttl attribute enabled on the table"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-DDB-05]
  - cmd: "attest: integration tests run against dynamodb local (docker), not hand-written marshalling mocks"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-DDB-06]
    tiers: [T2, T3, T4]
  - cmd: "attest: no item can approach 400KB — large payloads live in S3 with a pointer item"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-DDB-07]
last_review: 2026-07-22
---

# DynamoDB (STK-DDB)

## Abstract

DynamoDB rewards upfront design and punishes improvisation: you cannot add query
flexibility later the way you add an index in Postgres. So the load-bearing rule is
sequencing — enumerate access patterns *before* the table exists, derive a single-table
key design from them, and treat GSIs as the only query escape hatch (scans are a design
failure). On-demand billing until usage proves otherwise (OPS-FINOPS), conditional
writes for idempotency (ARC-IDEMPOTENCY), TTL for expiring data (DATA-RETENTION),
DynamoDB Local for tests. Scaffold fragment: `templates/scaffolds/data/dynamodb/`
(compose + access-pattern skeleton + example table definition).

## Normative Rules

### STK-DDB-01 — Access patterns MUST be enumerated before the table exists, and the key design derived from them

**Tiers**: all required — **Layer**: G

`docs/access-patterns.md` (skeleton in the scaffold fragment) lists every read/write
pattern as a row — *before* any table is created: pattern, operation
(GetItem/Query/write), key condition. The partition/sort key schema and any GSIs are
derived from that table; a query need with no row is a design change, not an ad-hoc
scan. Default to single-table design (entities share one table via `PK`/`SK`
prefixes); multiple tables are fine when access patterns genuinely don't interleave.
If access patterns can't be listed yet, that is the signal the project wants SQLite or
Postgres, not DynamoDB (STK-SQLITE-01).

### STK-DDB-02 — Billing MUST be on-demand until sustained usage proves provisioned capacity cheaper

**Tiers**: all required — **Layer**: G

`PAY_PER_REQUEST` in every table definition. Provisioned capacity (and autoscaling
around it) enters only with months of usage data showing a stable load where reserved
throughput wins — that is an OPS-FINOPS decision with numbers attached, recorded in
`GOVERNANCE.md`. New AWS spend needs a budget alarm first (Constitution C6).

### STK-DDB-03 — Scan MUST NOT appear in production code paths

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G

`Scan` reads and bills the whole table to answer any question — at T3+ it is a design
failure per STK-DDB-01 (a missing access pattern). Production reads are `GetItem`,
`Query` on the table, or `Query` on a GSI. Legitimate scans (one-off backfills,
offline analytics, admin audits) live in `scripts/`, not `src/`, so the grep gate
stays honest. A GSI is the sanctioned escape hatch when a new pattern appears —
add the row to `docs/access-patterns.md` first, then the GSI (base-table attributes
can be backfilled; on-demand GSIs cost nothing at rest).

### STK-DDB-04 — Multi-item invariants MUST use transactions/batches, and once-only writes MUST carry condition expressions

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Two items that must change together (e.g. order + counter) go through
`TransactWriteItems`; bulk loads use `BatchWriteItem` with unprocessed-item retries.
Creates that must not clobber use `attribute_not_exists(PK)`; state transitions
condition on the expected prior state. Conditional writes are DynamoDB's native
dedup/idempotency primitive — the request-level idempotency contract they implement is
ARC-IDEMPOTENCY.

### STK-DDB-05 — Data with a natural expiry SHOULD use TTL

**Tiers**: all advisory — **Layer**: A (attestation)

Sessions, cache rows, idempotency keys, soft-locks: set an epoch-seconds `expires_at`
attribute and enable TTL on the table — free deletion instead of paid sweeps. TTL
deletion lags expiry by up to ~48h, so readers still filter on the timestamp; anything
deleted to satisfy a retention *promise* follows DATA-RETENTION (TTL is a mechanism,
not a policy).

### STK-DDB-06 — Tests MUST run against DynamoDB Local, never hand-mocked marshalling

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Hand-written mocks of the AttributeValue wire format test your guess about DynamoDB,
not DynamoDB — key-condition syntax, marshalling, and conditional-write failures are
exactly what mocks get wrong. Run `amazon/dynamodb-local` via the scaffold's compose
file (in-memory, sub-second startup), point the SDK at
`DYNAMODB_ENDPOINT_URL=http://localhost:8000`, create tables in a fixture. Test scope
and layering rules live in TST-INTEG.

### STK-DDB-07 — Items MUST stay well under the 400KB limit; large payloads go to S3 with a pointer

**Tiers**: all required — **Layer**: A (attestation)

400KB is a hard API limit, and reads/writes bill by item size long before that.
Anything that can grow unbounded (documents, images, raw payloads, big JSON) is stored
in S3 and referenced by an item attribute (`s3://bucket/key`); the item keeps the
queryable metadata. Unbounded lists inside one item (append-forever arrays) are the
same bug in disguise — model them as separate items under the same `PK`.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `[ -f docs/access-patterns.md ] \|\| [ -f access-patterns.md ]` | the access-pattern table exists | STK-DDB-01 |
| 2 | negative grep for `billing_mode…provisioned` / `provisionedthroughput` | no provisioned capacity declared | STK-DDB-02 |
| 3 | `! grep -rnIE "[.]scan[(]\|ScanCommand" src app lib` (T3+) | no scans in production paths | STK-DDB-03 |
| 4–7 | attestation checklist (one per rule; -06 at T2+) | explicit yes recorded | STK-DDB-04, -05, -06, -07 |

**Remediation:** missing access-patterns doc → copy the skeleton from
`templates/scaffolds/data/dynamodb/access-patterns.md` and fill it from the code's
actual queries · provisioned grep hit → switch the table to `PAY_PER_REQUEST` (or
record the FinOps justification and waive per C9) · scan in `src/` → add the pattern
row, create a GSI, rewrite as `Query`; move genuine one-offs to `scripts/`.

## Worked Example

The doc's worked example *is* the access-pattern table → key design step
(STK-DDB-01). For a small orders app:

| # | Access pattern | Operation | Key condition |
|---|---|---|---|
| 1 | Get user profile | GetItem | `PK=USER#<id>`, `SK=PROFILE` |
| 2 | List a user's orders, newest first | Query | `PK=USER#<id>`, `SK begins_with ORDER#`, `ScanIndexForward=false` |
| 3 | Get one order by order id alone | Query GSI1 | `GSI1PK=ORDER#<id>` |
| 4 | List orders by status per day (ops) | Query GSI2 | `GSI2PK=STATUS#<s>#<yyyy-mm-dd>` |

Derived design — one table, `PK`/`SK` strings; order items carry
`GSI1PK=ORDER#<id>` and `GSI2PK=STATUS#<status>#<date>`, `SK=ORDER#<created_iso>` so
pattern 2 sorts lexicographically by time. Every row above maps to exactly one
GetItem/Query — nothing scans. The matching Terraform (on-demand, TTL, GSIs) is
`templates/scaffolds/data/dynamodb/table.example.tf`; local-dev compose and env
fragment sit beside it.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Designing the table first, queries later | Patterns that don't fit keys → scans and rewrites | Access-pattern table first (STK-DDB-01) |
| Relational modelling (one table per entity, "joins" in code) | N round trips per screen; no transactions across your "join" | Single-table, item collections under one `PK` |
| `Scan` + filter expression as "query" | Reads/bills entire table; filters after paying | Query on key or GSI (STK-DDB-03) |
| Provisioned capacity "to be safe" | Pay 24/7 for peak; throttle at spikes anyway | On-demand until data says otherwise (STK-DDB-02) |
| Read-modify-write without conditions | Lost updates, duplicate creates on retry | Condition expressions (STK-DDB-04) |
| Cron job deleting expired rows | Paid, throttling-prone, lags anyway | Table TTL (STK-DDB-05) |
| Hand-mocked `{"S": …}` marshalling in tests | Tests pass, prod marshals differently | DynamoDB Local (STK-DDB-06) |
| Growing JSON blob inside one item | Hits 400KB wall; every read pays full size | S3 pointer / split into items (STK-DDB-07) |

## References

- Alex DeBrie, *The DynamoDB Book* / dynamodbbook.com — the access-patterns-first and
  single-table methodology STK-DDB-01 encodes.
- AWS DynamoDB developer guide: on-demand vs provisioned — cost model behind STK-DDB-02.
- AWS docs: condition expressions & `TransactWriteItems` — the idempotency primitives
  (STK-DDB-04).
- AWS docs: TTL — the ~48h deletion-lag caveat in STK-DDB-05.
- AWS service quotas: 400KB item size — the hard limit behind STK-DDB-07.
- `amazon/dynamodb-local` image docs — the test backend for STK-DDB-06.

## Changelog

- **1.0.1** (2026-07-22) — Selection fix: `stacks` narrowed to this standard's own key so auxiliary keys (web/typescript/aws) don't cross-select it into unrelated projects (Phase-4 budget test finding).

- **1.0.0** (2026-07-22) — Initial version.
