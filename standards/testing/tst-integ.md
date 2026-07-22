---
id: TST-INTEG
title: Integration & E2E Testing
family: TST
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - integration test
  - e2e
  - end-to-end
  - playwright
  - testcontainers
  - smoke test
  - contract test
  - mock
  - fixture recording
  - critical path
requires: []
verification:
  - cmd: "attest: every critical path (auth, payment, primary user action, data-loss-risk operations) has integration or E2E coverage"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-INTEG-01]
    tiers: [T3, T4]
  - cmd: "attest: the E2E smoke suite is ≤ ~10 flows and runs in CI"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-INTEG-02]
    tiers: [T3, T4]
  - cmd: "attest: external API contract points are tested against recorded fixtures, never live calls"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-INTEG-03]
  - cmd: "attest: integration tests run against real lightweight backends (real SQLite, testcontainers, httptest), not deep mocks"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-INTEG-04]
  - cmd: "attest: integration/E2E tooling comes from the house table or the deviation has a stated reason"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-INTEG-05]
last_review: 2026-07-22
---

# Integration & E2E Testing (TST-INTEG)

## Abstract

Unit tests prove the pieces; this standard makes sure the assembled system is proven where
failure actually hurts. At T3+ every critical path — auth, payment, the product's primary
user action, and any operation that can lose data — gets integration or E2E coverage. The
E2E layer stays deliberately small (a smoke suite of at most ~10 stable flows, run in CI),
integration tests run against real lightweight backends instead of mock stacks, and
external API boundaries are tested with recorded fixtures, never live calls. T1/T2:
advisory, because there is usually no deployed assembly to protect.

## Normative Rules

### TST-INTEG-01 — Every critical path MUST have integration or E2E coverage

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

**Critical path** = any of: authentication/session flows; payment or money movement; the
primary user action (the one thing the product exists to do — post the listing, generate
the report, send the schedule); and data-loss-risk operations (delete, overwrite, migrate,
sync). Each gets at least one test that exercises the real assembly — real router, real
DB, real serialization — from the outside in. Unit tests on the pieces do not satisfy
this rule: the classic integration failure is two individually-correct components wired
together wrong.

### TST-INTEG-02 — The E2E suite MUST stay few and stable, and run in CI at T3+

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

E2E tests are expensive, slow, and the top source of flakiness — so the browser/full-stack
layer is capped at a smoke suite of roughly ten flows, one per critical path, asserting
outcomes ("payment recorded, receipt visible") not pixels or DOM details. New regression
tests go to the unit or integration layer, not E2E. The smoke suite runs on every PR in CI
(`DEV-CI` owns the wiring); a flow that flakes gets quarantined per `TST-FIXTURES-05`,
not retried until green.

### TST-INTEG-03 — External API contract points MUST be tested against recorded fixtures, never live calls

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Tests never call third-party APIs (Anthropic, Stripe, SEC EDGAR, banks): live calls are
flaky, rate-limited, cost money (C6), and need real credentials in CI (SEC-SECRETS
violation waiting to happen). Instead, record the real response once with respx/vcrpy
(Python), msw (TypeScript), or go-vcr/httptest (Go); commit the scrubbed cassette
(credentials and PII removed — `SEC-SECRETS`, `TST-FIXTURES-01`); re-record deliberately
when the provider's contract changes. The recorded fixture *is* the contract: when the
provider breaks it, the re-record diff shows exactly what moved.

### TST-INTEG-04 — Integration tests SHOULD run against real lightweight backends, not deep mocks

**Tiers**: all advisory — **Layer**: A (attestation)

Mocking your own database or filesystem tests the mock. Use the real thing in its cheapest
form: SQLite in a temp file (or the actual engine if the app ships on SQLite), Postgres or
Redis via testcontainers when the production engine's behavior matters (upserts, JSON
operators, expiry), `httptest` servers in Go, an in-process app instance for HTTP layers.
Mocks are for the *other side* of a boundary you don't own — which TST-INTEG-03 already
covers with recordings.

### TST-INTEG-05 — Integration/E2E tooling SHOULD come from the house table

**Tiers**: all advisory — **Layer**: A (attestation)

| Stack | Integration | E2E | Contract recording |
|---|---|---|---|
| Python (`STK-PY`) | pytest + real SQLite / testcontainers | playwright (browser) or pytest driving the real CLI | respx (httpx) / vcrpy |
| TypeScript (`STK-TS`) | vitest + testcontainers | playwright | msw |
| Go (`STK-GO`) | `testing` + `httptest` | `testing` against the built binary | go-vcr / httptest |

One idiom per repo; deviating is fine with a stated reason (that's SHOULD). Performance
and load testing are out of scope here — `OPS-PERF` owns those budgets.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attest: critical paths covered (T3+) | explicit yes recorded | TST-INTEG-01 |
| 2 | attest: smoke suite ≤ ~10 flows, in CI (T3+) | explicit yes recorded | TST-INTEG-02 |
| 3 | attest: contract points use recorded fixtures | explicit yes recorded | TST-INTEG-03 |
| 4 | attest: real backends over deep mocks | explicit yes recorded | TST-INTEG-04 |
| 5 | attest: tooling from the house table | explicit yes recorded | TST-INTEG-05 |

**Remediation:** critical path uncovered → add one outside-in test for it before the next
deploy · E2E suite past ~10 flows → demote the extras to integration tests · live API call
found in tests → record a cassette, scrub it, point the test at it · flaky E2E flow →
quarantine with issue (`TST-FIXTURES-05`), fix the wait/selector, then restore.

## Worked Example

Integration test against the real SQLite engine plus a recorded external contract
(Python; the pattern the oracle suite uses for network-free tests):

```python
# tests/integration/test_ledger.py
def test_transfer_is_atomic(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")        # real SQLite, real schema
    ledger.deposit("A", 100_00)
    with pytest.raises(InsufficientFunds):
        ledger.transfer("A", "B", 200_00)
    assert ledger.balance("A") == 100_00           # rolled back, not half-applied

# tests/integration/test_edgar_client.py
@respx.mock
def test_filing_fetch_parses_recorded_response(respx_mock):
    respx_mock.get(url__regex=r".*edgar.*").respond(
        200, json=json.loads(FIXTURES.joinpath("edgar_10k.json").read_text())
    )
    filing = EdgarClient().latest_10k("0000320193")  # no network, no live SEC call
    assert filing.fiscal_year == 2025
```

`edgar_10k.json` was recorded once from the real API, scrubbed, and committed;
re-recording is a deliberate act with a diff review.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| "Integration" test with the DB layer mocked | Tests the mock's opinion of SQL, not SQL | Real SQLite/testcontainers (TST-INTEG-04) |
| A new E2E test per bug report | Suite bloats, slows, flakes; CI becomes a lottery | Repro at the unit/integration layer (TST-POLICY-01) |
| Live third-party calls in CI | Flaky, rate-limited, needs secrets, costs money | Recorded fixtures (TST-INTEG-03) |
| E2E asserting DOM structure/pixels | Breaks on every restyle; tests nothing a user sees | Assert outcomes and visible text |
| `sleep(5)` to let the app settle | Slow when passing, flaky when loaded | Explicit waits on conditions (playwright auto-wait) |
| Cassettes recorded with live credentials inside | Secret committed to git (C1) | Scrub before commit; obviously-fake tokens (SEC-SECRETS) |
| Skipping integration because "units all pass" | Wiring bugs live exactly between passing units | Cover the assembly on critical paths (TST-INTEG-01) |

## References

- Martin Fowler, "The Practical Test Pyramid" — the few-E2E/many-unit shape
  TST-INTEG-02 enforces.
- playwright docs (auto-waiting, trace viewer) — the sanctioned E2E driver; auto-wait is
  the antidote to sleep-based flakiness.
- testcontainers docs — real engines as throwaway containers for TST-INTEG-04.
- vcrpy / respx / msw docs — record-replay tooling for TST-INTEG-03.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
