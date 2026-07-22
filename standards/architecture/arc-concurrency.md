---
id: ARC-CONCURRENCY
title: Concurrency & Background Jobs
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
  - background job
  - cron
  - launchd
  - scheduler
  - scheduled task
  - queue
  - sqs
  - worker
  - lock
  - race condition
  - async
  - concurrency
  - dlq
requires: [ARC-IDEMPOTENCY]
verification:
  - cmd: "attest: scheduled work at T1/T2 is launchd/cron invoking a plain script; no in-process scheduler daemons"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-CONCURRENCY-01]
  - cmd: "attest: every job is idempotent and holds a lock (lockfile/flock) so runs never overlap"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-CONCURRENCY-02]
  - cmd: "attest: every job logs start, end, and outcome"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-CONCURRENCY-03]
  - cmd: "attest: no check-then-act on shared state without a lock, transaction, or single atomic operation"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-CONCURRENCY-04]
  - cmd: "attest: T3+ background work runs on a queue with a DLQ and a visibility timeout above worst-case job duration"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-CONCURRENCY-05]
    tiers: [T3, T4]
  - cmd: "attest: async code paths contain no blocking calls (sync http/db/sleep/cpu-heavy work)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-CONCURRENCY-06]
last_review: 2026-07-22
---

# Concurrency & Background Jobs (ARC-CONCURRENCY)

## Abstract

Background work stays boring: at T1/T2 the sanctioned scheduler is launchd/cron invoking
a plain script — the pattern proven by the mortgage-payment-scheduler — never a resident
in-process scheduler. Every job is idempotent (`ARC-IDEMPOTENCY`), locked against
overlapping runs (lockfile or `flock`), and logs start/end/outcome so silent-not-running
is detectable (`OPS-OBS`). Race hygiene applies everywhere: no check-then-act on shared
state without atomicity, no blocking calls inside async contexts. T3+ escalates to a real
queue (SQS) with DLQ and a visibility timeout tuned above worst-case job duration.

## Normative Rules

### ARC-CONCURRENCY-01 — Scheduled work at T1/T2 SHOULD be launchd/cron invoking a plain script

**Tiers**: all advisory — **Layer**: A (attestation)

The house pattern: a launchd plist (or crontab line) fires a script that runs, logs, and
exits. No APScheduler daemons, no Celery beat, no `while True: sleep()` processes for
personal-scale work — resident schedulers add a process to babysit and die silently on
reboot, while launchd restarts on schedule for free. Scripts invoke tools by absolute
venv path (`STK-PY-08` — the exact lesson the mortgage-scheduler launchd debugging paid
for). Escalation beyond this pattern is `ARC-PATTERNS-03`'s call, not a default.

### ARC-CONCURRENCY-02 — Jobs MUST be idempotent and MUST NOT overlap: lock or skip

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Idempotent because schedulers redeliver — crash-and-rerun, wake-from-sleep double-fires,
manual re-runs (`ARC-IDEMPOTENCY-01/02`). Non-overlap via a lock taken at entry:
canonical forms are a lockfile (atomic `mkdir`, works everywhere including macOS, which
ships no `flock(1)`) or `flock` (Linux/CI; `fcntl.flock` from Python on macOS). A run
that finds the lock held logs a SKIP and exits cleanly — queueing behind a stuck
predecessor turns one hang into a pileup. Stale-lock policy: the trap/finally releases
it; a lock older than N× the schedule interval is logged as an incident, not silently
stolen.

### ARC-CONCURRENCY-03 — Every job MUST log start, end, and outcome

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Minimum three lines per run: timestamped START, timestamped END with ok/fail and
duration, and on failure the reason (`ARC-ERRORS-07`). Format and destination follow
`OPS-OBS`; under launchd, `StandardOutPath`/`StandardErrorPath` point somewhere durable.
The failure this retires: a job that has silently not run for six weeks is
indistinguishable from a healthy quiet one unless absence of the START line is visible.

### ARC-CONCURRENCY-04 — Check-then-act on shared state MUST be atomic

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Any "look, then modify" against state another process can touch is a race. Sanctioned
replacements: SELECT-then-INSERT → `INSERT ... ON CONFLICT` / unique constraint;
read-modify-write a file → write temp + atomic `rename`; "create if absent" against an
API → attempt the create and handle AlreadyExists; counters → atomic
increment/transaction. If no atomic primitive exists, take the rule-02 lock around the
whole sequence. `if not path.exists(): path.write_text(...)` is the canonical violation.

### ARC-CONCURRENCY-05 — T3+ background work MUST run on a real queue with DLQ and a tuned visibility timeout

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

SQS is the house queue (boring, free tier, no broker to run). Non-negotiables: a
dead-letter queue with `maxReceiveCount` 3–5 and an alarm on DLQ depth (`OPS-OBS`) so
poison messages park visibly instead of looping; visibility timeout set **above
worst-case job duration** (plus retry budget, `ARC-ERRORS-04`) — below it, SQS redelivers
mid-run and the consumer races itself; consumers idempotent per `ARC-IDEMPOTENCY-02/03`,
because standard queues are at-least-once by contract.

### ARC-CONCURRENCY-06 — Async code MUST NOT block the event loop

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Inside `async def`: no `time.sleep` (→ `asyncio.sleep`), no `requests` or sync DB drivers
(→ `httpx.AsyncClient`, async driver), no unbounded CPU work (→ `asyncio.to_thread`).
One blocking call freezes every coroutine sharing the loop — under FastAPI that is every
in-flight request. If most of a codebase's IO is sync, the honest fix is not sprinkling
`async` — plain sync code with threads is sanctioned and simpler (`ARC-PATTERNS-01`);
async is for genuinely concurrent IO.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1–4 | attestation checklist (one entry per rule) | explicit yes recorded | ARC-CONCURRENCY-01…04 |
| 5 | attestation, T3+ only | explicit yes recorded | ARC-CONCURRENCY-05 |
| 6 | attestation checklist | explicit yes recorded | ARC-CONCURRENCY-06 |

**Remediation:** overlapping runs observed → add the mkdir-lock wrapper below · SQS
duplicates mid-run → raise visibility timeout above worst-case duration · DLQ filling →
fix or quarantine the poison message; never raise `maxReceiveCount` to hide it ·
`time.sleep` in async → `await asyncio.sleep`; sync client in async → async client or
`asyncio.to_thread`.

## Worked Example

The house launchd entry point (rules 01, 02, 03) — macOS-safe mkdir lock:

```bash
#!/usr/bin/env bash
# run_scheduled.sh — invoked by com.jafinch.myjob.plist (ARC-CONCURRENCY-01)
set -euo pipefail
LOCK="${TMPDIR:-/tmp}/myjob.lock"

if ! mkdir "$LOCK" 2>/dev/null; then                     # atomic take (ARC-CONCURRENCY-02)
  echo "$(date -Iseconds) myjob SKIP — lock held ($LOCK)" >&2
  exit 0                                                  # skip, don't queue
fi
trap 'rmdir "$LOCK"' EXIT

echo "$(date -Iseconds) myjob START"                      # (ARC-CONCURRENCY-03)
"$HOME/Dev/myproj/.venv/bin/python" -m myproj.job         # venv path, STK-PY-08;
echo "$(date -Iseconds) myjob END ok"                     # job idempotent, ARC-IDEMPOTENCY
```

The plist's `StandardOutPath`/`StandardErrorPath` capture these lines durably; a
monitoring pass greps for missing START lines.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `while True: sleep(3600)` daemon under launchd | Dies silently; survives nothing; launchd already is the scheduler | Plist fires a script (ARC-CONCURRENCY-01) |
| Celery/beat for one nightly job | A broker + workers to babysit for personal scale | launchd + script; escalate per ARC-PATTERNS-03 |
| Cron job with no lock | Slow run + next tick = overlap; DST double-fire corrupts state | mkdir lock or flock (ARC-CONCURRENCY-02) |
| Queueing behind a held lock | One hang becomes a pileup of stale runs | Log SKIP and exit |
| Visibility timeout < job duration | SQS redelivers mid-run; consumer races its own duplicate | Timeout > worst case (ARC-CONCURRENCY-05) |
| No DLQ | Poison message redelivers forever, starving the queue | DLQ + depth alarm (ARC-CONCURRENCY-05) |
| `if not exists: create` on shared file/row | TOCTOU race — both processes pass the check | Atomic op or lock (ARC-CONCURRENCY-04) |
| `time.sleep`/`requests` inside `async def` | Freezes every coroutine on the loop | `asyncio.sleep` / async client (ARC-CONCURRENCY-06) |

## References

- mortgage-payment-scheduler launchd work (in-house) — the proven plist + script + venv
  path pattern rules 01/02 codify.
- Apple launchd documentation (`StartCalendarInterval`, `StandardOutPath`) — the T1
  scheduler's actual contract, including wake-from-sleep behavior.
- AWS SQS developer guide, visibility timeout & DLQ sections — the numbers behind
  ARC-CONCURRENCY-05.
- Python asyncio docs, "Developing with asyncio" — the blocking-call guidance behind
  ARC-CONCURRENCY-06.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
