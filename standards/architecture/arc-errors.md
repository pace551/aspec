---
id: ARC-ERRORS
title: Error Handling & Resilience
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
  - error handling
  - exception
  - retry
  - timeout
  - resilience
  - backoff
  - circuit breaker
  - failure
  - try except
  - crash
  - degradation
requires: []
verification:
  - cmd: "python3 ~/Dev/claude-code/governance/checks/silent-swallow.py"
    expect: "exit 0 — no catch-all handler silently swallows; deliberate swallows carry `swallow-ok: <reason>`"
    layer: G
    rules: [ARC-ERRORS-01]
    tiers: [T2, T3, T4]
  - cmd: "attest: every external call (http, db, subprocess, queue, llm) has an explicit timeout"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-ERRORS-02]
  - cmd: "attest: inputs are validated at the boundary; invalid input fails fast, before partial work"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-ERRORS-03]
  - cmd: "attest: retries exist only on idempotent operations, with exponential backoff, jitter, and an attempt budget"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-ERRORS-04]
  - cmd: "attest: each dependency has a defined degraded-mode behavior when it is down"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-ERRORS-05]
    tiers: [T3, T4]
  - cmd: "attest: user-facing errors say what happened and what to do; no stack traces or internals shown"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-ERRORS-06]
  - cmd: "attest: errors are logged once, with context, at the layer that handles them"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-ERRORS-07]
last_review: 2026-07-22
---

# Error Handling & Resilience (ARC-ERRORS)

## Abstract

Failures are loud, bounded, and informative. Loud: no silent swallowing — the canonical
sin is `except Exception: pass`, and `checks/silent-swallow.py` hunts it. Bounded: every
external call has a timeout; retries touch only idempotent operations, with backoff,
jitter, and a budget; T3+ services define a degraded mode per dependency. Informative:
users learn what happened and what to do (never a stack trace), and every error is logged
once with context per `OPS-OBS`. T1 gets the same habits advisory; T2+ makes them
required because a swallowed exception in an analysis pipeline silently corrupts
conclusions.

## Normative Rules

### ARC-ERRORS-01 — Exceptions MUST NOT be silently swallowed

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G (checks/silent-swallow.py)

The canonical violation is `except Exception: pass` (and its cousins: bare `except:`,
empty `catch {}`). A handler does exactly one of: **handle** (recover, with the error
recorded), **translate** (`raise DomainError(...) from exc`), or **let it propagate**.
Catch the narrowest type that the recovery logic actually understands. The checker flags
catch-all handlers whose body is only `pass`/`...`/`continue`; a genuinely intended
swallow carries `# swallow-ok: <reason>` on the except line — the written reason is what
makes it reviewable.

### ARC-ERRORS-02 — Every external call MUST carry an explicit timeout

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

HTTP requests, DB queries, subprocesses, queue receives, LLM calls — all of them. Library
defaults are treated as absent: set the value at construction
(`httpx.Client(timeout=10.0)`, `subprocess.run(..., timeout=60)`, DB driver
`connect_timeout`/statement timeout) and note why that number where the client is built.
A call without a timeout is a hang scheduled for the worst possible night; under launchd
it also blocks the next scheduled run (`ARC-CONCURRENCY-02`).

### ARC-ERRORS-03 — Boundaries MUST fail fast on invalid input

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Parse, don't limp: request bodies, config (`ARC-CONFIG-02`), CLI args, and file inputs
are validated into typed objects (pydantic/zod) at the edge, so interior code never
defends against half-valid data. Reject before side effects begin — a crash at the
boundary costs a retry; a crash mid-way costs cleanup (`ARC-IDEMPOTENCY` limits the
damage, but not creating the mess beats surviving it).

### ARC-ERRORS-04 — Retries MUST be limited to idempotent operations, with backoff, jitter, and a budget

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Retry only what is safe to repeat (`ARC-IDEMPOTENCY-01`); retrying a non-idempotent POST
is how double charges happen. Mechanics: exponential backoff with full jitter
(`sleep(min(cap, base * 2**attempt) * random())`), a hard attempt budget (3–4 total), and
no retry on 4xx except 408/429 — honoring `Retry-After` when present. A retry storm
against a struggling dependency is a self-inflicted outage.

### ARC-ERRORS-05 — T3+ services MUST define a degraded mode per dependency

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

For each external dependency, decide at design time what happens when it is down:
circuit-break (stop calling after repeated failures, probe periodically), serve stale
cache, or switch the dependent feature off with an honest message (ARC-ERRORS-06). The
non-answer — every request waiting out its full timeout-and-retry budget — is a cascade.
At T1/T2, "the script exits nonzero and the log says why" is the sanctioned degraded mode.

### ARC-ERRORS-06 — User-facing errors MUST say what happened and what to do — never internals

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Two clauses per message: what failed, in the user's vocabulary, and their next action
("try again", "check the file path", "contact support with code X"). Stack traces, ORM
errors, and file paths never reach a user — they leak internals (`SEC-*`) and help nobody.
Wire format for APIs is `ARC-API-03`; form-field presentation is `UX-FORMS`. Show the
correlation id so a report can be matched to logs.

### ARC-ERRORS-07 — Errors SHOULD be logged once, with context, at the layer that handles them

**Tiers**: all advisory — **Layer**: A (attestation)

The handler that decides (recovers, translates, or reports) writes the log entry —
operation, inputs summary, correlation id, and the exception with traceback — in the
format `OPS-OBS` owns. Log-and-rethrow at every layer buries the signal under N copies of
the same traceback; intermediate layers add context via `raise ... from exc` instead of
logging.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `python3 ~/Dev/claude-code/governance/checks/silent-swallow.py` (T2+) | exit 0 — no unmarked catch-all swallow | ARC-ERRORS-01 |
| 2–4 | attestation checklist (one entry per rule) | explicit yes recorded | ARC-ERRORS-02…04 |
| 5 | attestation, T3+ only | explicit yes recorded | ARC-ERRORS-05 |
| 6–7 | attestation checklist | explicit yes recorded | ARC-ERRORS-06…07 |

**Remediation:** silent-swallow hit → narrow the except, translate with `from exc`, or add
`# swallow-ok: <reason>` if genuinely intentional · missing timeouts → set at client
construction, not per call site · retry on non-idempotent op → make the operation
idempotent first (`ARC-IDEMPOTENCY-03`), then retry.

## Worked Example

A bounded, jittered retry around an idempotent GET (rules 01, 02, 04):

```python
import random, time
import httpx

client = httpx.Client(timeout=10.0)          # explicit timeout (ARC-ERRORS-02)

def fetch_prices(url: str) -> dict:
    for attempt in range(4):                 # attempt budget (ARC-ERRORS-04)
        try:
            r = client.get(url)              # GET — idempotent, safe to retry
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in (429, 502, 503) or attempt == 3:
                raise PriceFeedError(f"price fetch failed (try {attempt + 1})") from exc
        except httpx.TimeoutException as exc:
            if attempt == 3:
                raise PriceFeedError("price feed timed out 4x") from exc
        time.sleep(min(30, 2 ** attempt) * random.random())   # expo backoff, full jitter
```

Translate (`from exc`), never swallow; the caller logs `PriceFeedError` once
(ARC-ERRORS-07) and the user sees "Price feed unavailable — using yesterday's close"
(ARC-ERRORS-05/06).

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `except Exception: pass` | The error still happened — now it's invisible and the state is undefined | Handle, translate, or propagate (ARC-ERRORS-01) |
| Blanket retry wrapper around all calls | Replays non-idempotent ops → double charges, duplicate emails | Retry idempotent only (ARC-ERRORS-04) |
| `timeout=None` / library default trusted | One slow dependency hangs the process (and the next launchd run) | Explicit timeout at construction (ARC-ERRORS-02) |
| Returning `None`/`-1` on failure | In-band errors get computed with; failures propagate as wrong answers | Raise; parse at boundaries (ARC-ERRORS-03) |
| Log-and-rethrow at every layer | N tracebacks for one failure; the real signal drowns | Log once at the handler (ARC-ERRORS-07) |
| Traceback rendered to the end user | Leaks internals; user has no next action | Two-clause message + correlation id (ARC-ERRORS-06) |
| Retry without jitter | Synchronized thundering herd re-kills the recovering service | Full jitter (ARC-ERRORS-04) |

## References

- Marc Brooker (AWS), "Exponential Backoff and Jitter" — why full jitter beats plain
  backoff; the formula in ARC-ERRORS-04.
- Michael Nygard, *Release It!* — circuit breakers, timeouts, and cascading-failure
  patterns behind rules 02 and 05.
- Google SRE Book, "Handling Overload" — retry budgets and the client-side duty not to
  melt a struggling server.
- RFC 9457 — the wire shape user-safe API errors take (via `ARC-API-03`).

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
