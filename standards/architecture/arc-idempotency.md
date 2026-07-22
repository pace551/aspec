---
id: ARC-IDEMPOTENCY
title: Idempotency
family: ARC
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - idempotency
  - idempotent
  - webhook
  - retry
  - queue consumer
  - dedup
  - replay
  - at-least-once
  - exactly-once
  - payment
  - cron job
  - redelivery
requires: []
verification:
  - cmd: "attest: every retriable/replayable operation (webhook, consumer, job, mutating call) is idempotent"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-IDEMPOTENCY-01]
  - cmd: "attest: every queue/webhook/scheduled surface is designed for at-least-once delivery"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-IDEMPOTENCY-02]
  - cmd: "attest: non-naturally-idempotent operations persist a dedup key in the same transaction as the side effect"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-IDEMPOTENCY-03]
  - cmd: "attest: outbound mutating calls send an idempotency key wherever the provider supports one"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-IDEMPOTENCY-04]
  - cmd: "attest: replay safety is proven by a test that delivers the same event twice"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-IDEMPOTENCY-05]
last_review: 2026-07-22
---

# Idempotency (ARC-IDEMPOTENCY)

## Abstract

Anything that can be retried or replayed — webhooks, queue consumers, scheduled jobs,
payment calls — must produce the same terminal state no matter how many times it runs.
The design assumption everywhere is at-least-once delivery: exactly-once is a lie vendors
tell, so redelivery is planned for, not hoped against. Prefer naturally idempotent
operations (absolute writes, UPSERTs); otherwise persist a dedup key in the same
transaction as the side effect. Applies T2+ wherever such surfaces exist; T1 advisory.
`ARC-ERRORS-04` (what may be retried) and `ARC-CONCURRENCY-02` (job re-runs) both lean on
this standard.

## Normative Rules

### ARC-IDEMPOTENCY-01 — Retriable or replayable operations MUST be idempotent

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

In scope: webhook handlers, queue consumers, scheduled jobs, and any mutating call a
retry policy (`ARC-ERRORS-04`) or human ("just run it again") might repeat. Idempotent
means processing the same input N times yields the same terminal state and exactly one
set of external side effects — one email, one charge, one row. If an operation cannot be
made idempotent, it MUST NOT be retried automatically, and that exclusion is recorded.

### ARC-IDEMPOTENCY-02 — At-least-once delivery MUST be the design assumption; exactly-once is a lie

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

SQS standard queues redeliver; webhook providers redeliver on any timeout (including
"handler succeeded but responded slowly"); launchd/cron re-run after crashes and
wake-from-sleep; a human replays events from a dashboard. "Exactly-once delivery" cannot
exist between distributed parties — what exists is at-least-once delivery plus
idempotent processing, which yields effectively-once *effects*. Design every consuming
surface for the duplicate that will eventually arrive.

### ARC-IDEMPOTENCY-03 — Prefer natural idempotency; otherwise persist a dedup key with the outcome

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Natural first: absolute writes ("set status to paid", not "increment balance"), UPSERTs,
unique constraints, deterministic filenames. Where the operation is inherently one-shot
(send email, charge card), record a dedup key — the event id or client-supplied
idempotency token — **in the same transaction/atomic step as the side effect's commit**,
and store the outcome so a replay can return the original result (`ARC-API-05`). Dedup
records are durable (table, not process memory) and outlive the provider's redelivery
window.

### ARC-IDEMPOTENCY-04 — Outbound mutating calls MUST send an idempotency key where the provider supports one

**Tiers**: T1–T3 advisory · T4 required — **Layer**: A (attestation)

Stripe, most payment APIs, and many AWS mutation APIs accept an idempotency key/client
token — send it on every create/charge/transfer. Derive the key from the business
operation (`order-1234-charge`), never a fresh UUID per attempt: a per-attempt key makes
every retry a new charge, which is the exact failure the header exists to prevent.
Required at T4 because that is where money moves; strongly advised the moment any
irreversible external effect exists.

### ARC-IDEMPOTENCY-05 — Replay safety SHOULD be proven by a duplicate-delivery test

**Tiers**: all advisory — **Layer**: A (attestation)

The cheapest honest evidence: a test that delivers the same event/message/run twice and
asserts one side effect and an unchanged terminal state. Test placement and depth follow
`TST-*` policy; this rule only says the duplicate case is on the list, because it is the
branch manual testing never exercises — production redelivery finds it instead.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1–5 | attestation checklist (one entry per rule) | explicit yes recorded | ARC-IDEMPOTENCY-01…05 |

**Remediation:** relative update in a consumer → rewrite as absolute write or UPSERT ·
dedup in a dict/set in memory → move to a table with a unique constraint · dedup written
in a second transaction → merge into the side effect's transaction (the crash between the
two is the duplicate window) · per-attempt UUID key → derive from the business operation.

## Worked Example

Webhook consumer with a persisted dedup key (SQLite), rules 02 and 03:

```python
# schema: CREATE TABLE processed_events (event_id TEXT PRIMARY KEY,
#                                        processed_at TEXT NOT NULL);

def handle_event(db, event: dict) -> None:
    """At-least-once delivery assumed (ARC-IDEMPOTENCY-02): replays are normal."""
    with db:  # one transaction: dedup mark + side effect commit together (-03)
        claimed = db.execute(
            "INSERT INTO processed_events (event_id, processed_at) "
            "VALUES (?, datetime('now')) ON CONFLICT (event_id) DO NOTHING",
            (event["id"],),
        )
        if claimed.rowcount == 0:
            return                      # duplicate delivery — already handled
        apply_change(db, event)         # absolute writes only inside
```

The duplicate-delivery test (rule 05): call `handle_event` twice with the same payload,
assert `apply_change`'s effect occurred exactly once.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `balance += amount` in a consumer | Every redelivery moves money again | Absolute write from source of truth (ARC-IDEMPOTENCY-03) |
| In-memory `seen_ids` set | Lost on restart — exactly when redeliveries spike | Durable dedup table with unique constraint |
| Dedup insert in a separate transaction after the side effect | Crash between the two = permanent duplicate window | Same transaction (ARC-IDEMPOTENCY-03) |
| Fresh `uuid4()` as the idempotency key each retry | Provider sees N distinct operations — N charges | Key derived from the business op (ARC-IDEMPOTENCY-04) |
| Trusting a vendor's "exactly-once" checkbox | It means "at-least-once + their dedup, terms apply"; edges still duplicate | Idempotent consumer regardless (ARC-IDEMPOTENCY-02) |
| Webhook 200-then-process | Crash after ack loses the event; the inverse orders a redelivery you must survive anyway | Process-then-ack + dedup key |
| "It only runs once a day, it's fine" | launchd re-runs on wake/crash; humans re-run by hand | Idempotent jobs (ARC-CONCURRENCY-02) |

## References

- Stripe idempotency documentation — the canonical key-derivation and stored-response
  semantics behind rules 03/04.
- AWS SQS developer guide, standard queues — the at-least-once contract rule 02 assumes.
- Tyler Treat, "You Cannot Have Exactly-Once Delivery" — the impossibility argument;
  effects, not delivery, are what get made once.
- Pat Helland, "Idempotence Is Not a Medical Condition" (ACM Queue) — dedup-key design
  for messaging systems.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
