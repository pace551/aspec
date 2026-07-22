---
id: OPS-PERF
title: Performance Budgets
family: OPS
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - performance
  - latency
  - p95
  - slow
  - optimize
  - lighthouse
  - core web vitals
  - load test
  - pagination
  - n+1
  - profiling
requires: []
verification:
  - cmd: "attest: performance budgets are written as explicit numbers in governance.md"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-PERF-01]
    tiers: [T3, T4]
  - cmd: "attest: every optimization this cycle was justified by a profile, trace, or measurement taken first"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-PERF-02]
  - cmd: "attest: lighthouse ci runs against key pages in ci for browser-facing surfaces"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-PERF-03]
    tiers: [T3, T4]
  - cmd: "attest: no n+1 query patterns and no unbounded result sets on served endpoints"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-PERF-04]
    tiers: [T2, T3, T4]
  - cmd: "attest: load testing exists exactly where real concurrency is expected, and nowhere else"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-PERF-05]
    tiers: [T4]
last_review: 2026-07-22
---

# Performance Budgets (OPS-PERF)

## Abstract

Performance is a number in GOVERNANCE.md, not a vibe. T3+ compliance in one breath:
explicit budgets exist (house defaults — API p95 < 500ms reads / < 2s writes at the
edge; Core Web Vitals "good": LCP < 2.5s, INP < 200ms, CLS < 0.1; Lighthouse
performance ≥ 90 on key pages), Lighthouse CI enforces the web numbers, and the two
canonical backend sins — N+1 queries and unbounded result sets — are absent. At every
tier: no optimization without a measurement first. Load testing exists only at T4 where
real concurrency is expected.

## Normative Rules

### OPS-PERF-01 — T3+ performance budgets MUST be explicit numbers in GOVERNANCE.md

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

House defaults, adopted verbatim unless a note overrides them: **API** p95 < 500ms for
reads, < 2s for writes, measured at the edge (what the user experiences, not
app-server-internal); **web** Core Web Vitals at "good" thresholds — LCP < 2.5s,
INP < 200ms, CLS < 0.1 — and Lighthouse performance ≥ 90 on key pages. A budget turns
"feels slow" into a pass/fail check and — equally important at personal scale — makes
*fast enough* a defined stopping point so optimization work has a finish line. Latency
SLO breaches alert per `OPS-ALERTS-01`.

### OPS-PERF-02 — No performance work without a profile, trace, or measurement first

**Tiers**: all required — **Layer**: A (attestation)

Measure, then optimize, then measure again — every perf change cites its before/after.
Acceptable evidence: a profiler run (`cProfile`/`py-spy`), an OTel trace (`OPS-OBS-05`),
an `EXPLAIN ANALYZE`, CloudWatch latency metrics, a Lighthouse report. Guessed
bottlenecks are wrong often enough that unmeasured "optimization" is just churn with
risk; conversely, if no budget (OPS-PERF-01) is breached, the correct amount of perf
work is zero.

### OPS-PERF-03 — T3+ browser-facing projects MUST run Lighthouse CI on key pages

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

`@lhci/cli` in the GitHub Actions pipeline (the standard CI fragment in `templates/ci/`)
with assertions encoding the OPS-PERF-01 numbers, run against the 2–4 pages users
actually land on — not every route. Failing the assertion fails the build, same as a
test. Accessibility assertions ride the same run but their thresholds belong to the UX
family (`UX-A11Y`). Applies to any `web`-stack surface; API-only services are exempt
from this rule (their budget is enforced via metrics + alarms).

### OPS-PERF-04 — N+1 queries and unbounded result sets MUST NOT ship

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

The two canonical backend sins, named because they cause most real slowness at this
scale. **N+1**: a query per row in a loop — fix with joins, `IN` batches, or eager
loading; detect by logging query counts per request in dev (`EXPLAIN` discipline and
indexing rules in `STK-PG`). **Unbounded result sets**: any endpoint or job that returns
or loads "all rows" — every list endpoint takes and enforces a limit (house default:
100, keyset pagination beyond) and every internal scan is chunked. Both are cheap to do
correctly at write time and expensive to retrofit at incident time.

### OPS-PERF-05 — Load-test only what has real concurrency expectations

**Tiers**: T1–T3 n/a · T4 required — **Layer**: A (attestation)

At T4, surfaces with genuine concurrent load (launch traffic, paying users, a known
event) get a load test (`k6` default) that validates the OPS-PERF-01 budgets at the
expected concurrency plus margin, re-run when the architecture changes. Everything else
is explicitly exempt — load-testing a five-user tool is ceremony, and serverless
defaults (`OPS-FINOPS-05`) make most scaling questions moot until the numbers say
otherwise.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attestation — budgets written (T3+) | explicit yes recorded | OPS-PERF-01 |
| 2 | attestation — measured before optimized (all tiers) | explicit yes recorded | OPS-PERF-02 |
| 3 | attestation — Lighthouse CI on key pages (T3+ web) | explicit yes recorded | OPS-PERF-03 |
| 4 | attestation — no N+1 / unbounded sets (T2+) | explicit yes recorded | OPS-PERF-04 |
| 5 | attestation — load tests scoped to real concurrency (T4) | explicit yes recorded | OPS-PERF-05 |

**Remediation:** no budgets at T3 → paste the house defaults into GOVERNANCE.md and
adjust with reasons · perf PR without numbers → measure first, attach before/after ·
web project without LHCI → add the CI fragment + `lighthouserc.json` · N+1 found →
eager-load/batch, add a query-count assertion in a test · unpaginated endpoint →
default + max limit, keyset pagination.

## Worked Example

GOVERNANCE.md budget block (T3 web app — house defaults, one override):

```markdown
## Performance budgets (OPS-PERF)
- API p95: reads < 500ms, writes < 2s (edge-measured, CloudWatch)
- Web: LCP < 2.5s · INP < 200ms · CLS < 0.1 · Lighthouse perf ≥ 90
- Override: /export p95 < 10s (bulk endpoint, async by design — note 2026-07-22)
```

`lighthouserc.json` asserting the budget on key pages:

```json
{
  "ci": {
    "collect": {"url": ["http://localhost:3000/", "http://localhost:3000/dashboard"],
                "numberOfRuns": 3},
    "assert": {"assertions": {
      "categories:performance": ["error", {"minScore": 0.9}],
      "largest-contentful-paint": ["error", {"maxNumericValue": 2500}],
      "cumulative-layout-shift": ["error", {"maxNumericValue": 0.1}]
    }}
  }
}
```

CI step (the `templates/ci/` fragment): `npx @lhci/cli autorun` after the build.

Bounded list endpoint (the OPS-PERF-04 shape):

```python
@app.get("/items")
def list_items(limit: int = Query(100, le=500), after: int | None = None):
    q = select(Item).order_by(Item.id).limit(limit)          # never unbounded
    if after is not None:
        q = q.where(Item.id > after)                          # keyset, not OFFSET
    return session.execute(q).scalars().all()
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| "Make it faster" work with no numbers | No target, no finish line, no evidence of gain | Budget + before/after measurement (OPS-PERF-01/02) |
| Optimizing the guessed hotspot | Guesses are usually wrong; real cost elsewhere | Profile first (OPS-PERF-02) |
| ORM lazy-loading relations inside a render loop | Classic N+1 — 1 + N queries per request | Eager load / batch fetch (OPS-PERF-04) |
| `SELECT *` with no LIMIT "because the table is small" | Tables grow; the endpoint fails at the worst time | Default + max limit from day one (OPS-PERF-04) |
| `OFFSET`-based pagination on large tables | O(offset) scans; page 1000 times out | Keyset pagination (OPS-PERF-04, `STK-PG`) |
| Measuring latency inside the app server only | Ignores TLS/network/cold-start users actually feel | Edge-measured budgets (OPS-PERF-01) |
| Load-testing a T1/T3 no-concurrency tool | Ceremony; answers a question nobody asked | Reserve for T4 real concurrency (OPS-PERF-05) |
| Lighthouse run once by hand at launch | Regressions arrive with the next PR | LHCI asserting in CI (OPS-PERF-03) |

## References

- web.dev Core Web Vitals — source of the LCP/INP/CLS "good" thresholds in OPS-PERF-01.
- Lighthouse CI docs (GoogleChrome/lighthouse-ci) — assertion config OPS-PERF-03 uses.
- Use The Index, Luke — keyset-pagination and index rationale behind OPS-PERF-04.
- k6 docs — the default T4 load-testing tool for OPS-PERF-05.
- Brendan Gregg, "Systems Performance" — measure-first methodology behind OPS-PERF-02.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
