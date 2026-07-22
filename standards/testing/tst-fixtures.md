---
id: TST-FIXTURES
title: Test Data & Fixtures
family: TST
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - fixture
  - test data
  - factory
  - faker
  - seed
  - flaky
  - freezegun
  - fake timers
  - deterministic
  - mock data
requires: []
verification:
  - cmd: "bash ~/Dev/claude-code/governance/checks/secret-scan.sh"
    expect: "exit 0 — no real secret patterns in fixtures or cassettes"
    layer: G
    rules: [TST-FIXTURES-01]
  - cmd: "attest: fixtures and cassettes contain no production data or third-party PII; all embedded secrets are obviously fake"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-FIXTURES-01]
  - cmd: "attest: tests are deterministic — randomness is seeded, time is frozen where asserted, no ordering dependence"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-FIXTURES-02]
  - cmd: "attest: the default test run makes no network calls; network-dependent tests are opt-in behind an excluded marker"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-FIXTURES-03]
  - cmd: "attest: test data is built by factories/builders rather than shared mutable fixtures"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-FIXTURES-04]
  - cmd: "attest: any flaky test was quarantined with a filed issue the same day it flaked, not retried until green"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [TST-FIXTURES-05]
last_review: 2026-07-22
---

# Test Data & Fixtures (TST-FIXTURES)

## Abstract

What goes into tests and how it behaves. Fixtures never contain production data, PII, or
real secrets — embedded credentials are obviously fake per `SEC-SECRETS`. Test data is
built by factories with per-test overrides, not shared mutable fixtures. Tests are
deterministic: seeded randomness, frozen time, and network-free by default (the oracle
suite's fully-offline test runs are the house example). A flaky test is quarantined with a
filed issue the same day — retry-until-green is banned because it converts a signal into
a habit. The no-production-data rule gets no tier discount; determinism rules are
advisory at T1.

## Normative Rules

### TST-FIXTURES-01 — Fixtures MUST NOT contain production data, third-party PII, or real secrets

**Tiers**: all required — **Layer**: G (secret scan) + A (attestation)

Applies to fixture files, factory defaults, recorded cassettes (`TST-INTEG-03`), seed
scripts, and inline literals. A prod DB dump is never a fixture: it leaks PII into git
history forever and couples tests to data that drifts. Build synthetic records that match
the schema; when realism matters, generate it (faker with a fixed seed). Embedded
credentials use obviously-fake values per `SEC-SECRETS-01` (`sk-ant-TEST…`,
`AKIAIOSFODNN7EXAMPLE`) so the secret scanner and human readers both recognize them as
inert. Cassettes are scrubbed of auth headers and identifying payloads before commit.

### TST-FIXTURES-02 — Tests MUST be deterministic

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Same code, same result, every run, any machine. Concretely: randomness flows through an
injected, seeded generator (`random.Random(1337)`, `np.random.default_rng(seed)` — the
oracle convention), never module-level global randomness; time is frozen where behavior
depends on it (freezegun in Python, `vi.useFakeTimers()` in vitest, injected clocks in
Go) so `datetime.now()` never appears in an assertion path; tests pass in any order (no
state smuggled between tests); synchronization waits on conditions, never on
`sleep(n)`. At T2 determinism is what makes analysis reproducible — a seed that isn't
pinned is a result that can't be reproduced.

### TST-FIXTURES-03 — Tests MUST be network-free by default

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

The default test command completes with the network cable conceptually unplugged —
external boundaries are covered by recorded fixtures (`TST-INTEG-03`). The oracle suite
is the house example: `backtest-rigor`'s entire test run executes offline; data
acquisition is exercised against recorded responses. Genuinely network-dependent tests
(live smoke checks) are opt-in behind a marker excluded by default
(`@pytest.mark.network` + `-m "not network"` in config) and never run in CI's required
jobs. This is also what keeps tests runnable in launchd jobs and sandboxed sub-agent
shells.

### TST-FIXTURES-04 — Test data SHOULD be built by factories/builders, not shared mutable fixtures

**Tiers**: all advisory — **Layer**: A (attestation)

A factory (`make_payment(**overrides)`) gives every test a fresh object and makes the
*relevant* fields explicit at the call site — the test that cares about currency passes
`currency="EUR"` and inherits the rest. Shared fixtures (module-level dicts, one
`conftest.py` mega-fixture, a `fixtures.json` all tests read) create action-at-a-distance:
one test mutates, another fails, and every new field change fans out across the suite.
Shared *immutable* constants (an enum of valid states) are fine; it's shared mutable
state that's the trap.

### TST-FIXTURES-05 — A flaky test MUST be quarantined with a filed issue the same day, never retried until green

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

A test that passes on retry has found a real nondeterminism — in the test or in the code —
and "re-run the job" discards that signal. Same day it flakes: quarantine it with a skip
that names its issue (`@pytest.mark.skip(reason="flaky: #123")`, `test.skip` with a
comment) and file the issue with the failure output attached. Auto-retry mechanisms
(pytest-rerunfailures, CI job retries on test steps) MUST NOT be used to mask flakiness.
A quarantined test is a debt with a ticket; a retried-green test is a lie with a
green checkmark.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `bash ~/Dev/claude-code/governance/checks/secret-scan.sh` | exit 0 — no real secrets in fixtures | TST-FIXTURES-01 |
| 2 | attest: no prod data / PII; fake secrets | explicit yes recorded | TST-FIXTURES-01 |
| 3 | attest: deterministic (seeds, frozen time) | explicit yes recorded | TST-FIXTURES-02 |
| 4 | attest: network-free default run | explicit yes recorded | TST-FIXTURES-03 |
| 5 | attest: factories over shared mutable fixtures | explicit yes recorded | TST-FIXTURES-04 |
| 6 | attest: flaky → quarantined same day with issue | explicit yes recorded | TST-FIXTURES-05 |

**Remediation:** scan hit in a cassette → rotate the real credential (`SEC-SECRETS-05`),
re-record scrubbed · nondeterministic failure → seed or freeze the input that varies;
if it's the code, that's the bug (TST-POLICY-01: repro first) · live call found in
default run → move behind the `network` marker and add a recorded-fixture version ·
retry plugin found in CI → remove it, quarantine whatever starts failing honestly.

## Worked Example

Factory + frozen time + seeded randomness (Python, `STK-PY` conventions):

```python
# tests/factories.py
from datetime import date
def make_payment(**overrides):
    base = dict(id="pay_TEST0001", amount_cents=12_500,
                currency="USD", due=date(2026, 3, 31))
    return Payment(**{**base, **overrides})

# tests/test_late_fees.py
import random
from freezegun import freeze_time

@freeze_time("2026-04-02")                      # two days past due — always
def test_late_fee_applied_after_due_date():
    p = make_payment()                          # fresh object, defaults explicit
    fee = late_fee(p, rng=random.Random(1337))  # jitter is seeded, injected
    assert fee == 250
```

```toml
# pyproject.toml — network tests opt-in, excluded by default
[tool.pytest.ini_options]
markers = ["network: talks to real services (excluded by default)"]
addopts = "-m 'not network'"
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Prod DB dump as `fixtures/seed.sql` | PII in git forever; tests coupled to drifting data | Synthetic schema-matching records (TST-FIXTURES-01) |
| Module-level `PAYMENT = {...}` mutated across tests | Order-dependent failures, action at a distance | Factory returning fresh objects (TST-FIXTURES-04) |
| `datetime.now()` / `Date.now()` in test or assertion path | Passes today, fails at month-end/DST/midnight | Freeze time; inject clocks (TST-FIXTURES-02) |
| Unseeded `random`/`np.random` in tests | Irreproducible failures nobody can debug | Injected seeded generator (TST-FIXTURES-02) |
| CI "retry failed jobs: 3" on test steps | Institutionalized flakiness; signal destroyed | Quarantine + issue, same day (TST-FIXTURES-05) |
| `time.sleep(2)` to await async work | Slow and flaky simultaneously | Poll/await the condition with a deadline |
| Real API key inside a recorded cassette | Committed secret (C1) | Scrub on record; rotate if it landed (SEC-SECRETS) |

## References

- `SEC-SECRETS` — obviously-fake credential values and the rotation playbook when a real
  one slips into a fixture.
- Martin Fowler, "Eradicating Non-Determinism in Tests" — the taxonomy behind
  TST-FIXTURES-02/-05 (time, randomness, async waits, resource leaks).
- Google Testing Blog, "Flaky Tests at Google and How We Mitigate Them" — evidence that
  retries entrench flakiness; quarantine-with-owner is the working alternative.
- freezegun / vitest fake-timers docs — the sanctioned time-freezing mechanisms.
- oracle `backtest-rigor` test suite — the house example of a fully network-free,
  seeded, reproducible run.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
