---
id: ARC-PATTERNS
title: Patterns & Anti-Patterns
family: ARC
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: advisory
  T4: advisory
stacks: all
triggers:
  - architecture
  - design
  - microservices
  - monolith
  - service extraction
  - refactor
  - rewrite
  - abstraction
  - queue
  - event-driven
  - framework choice
  - new project
  - tech choice
requires: []
verification:
  - cmd: "attest: technology choices default to boring; at most one innovation token spent, with its reason recorded"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-PATTERNS-01]
  - cmd: "attest: the system is a single deployable, or every extracted service has a recorded extraction trigger"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-PATTERNS-02]
  - cmd: "attest: no queue exists without observed (not projected) decoupling pain at T3+ volume"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-PATTERNS-03]
  - cmd: "attest: incomplete work ships behind feature flags; no branch has lived unmerged past a week"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-PATTERNS-04]
  - cmd: "attest: the design was checked against the anti-pattern table; matches were fixed or recorded as conscious deviations"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-PATTERNS-05]
last_review: 2026-07-22
---

# Patterns & Anti-Patterns (ARC-PATTERNS)

## Abstract

The tiebreaker standard. When two designs both "work", the tables here say which one the
house builds: boring technology, monolith-first, in-process calls until a queue earns its
keep, feature flags over long-lived branches, duplication until the third use. Advisory at
every tier — architecture is judgment, not a gate — but each rule passes through the
attestation checklist, so conscious deviations stay visible (C9). Other ARC standards cite
this document when preferences collide; the anti-pattern table is where the scar tissue
accumulates via `/evolve-standards`.

## Normative Rules

### ARC-PATTERNS-01 — Technology choices SHOULD default to boring

**Tiers**: all advisory — **Layer**: A (attestation)

Pick the tool with a decade of production scar tissue over the one with a good launch
video. Each project gets at most **one innovation token**: one deliberately novel choice
(new framework, new datastore, new runtime), made for a recorded reason in `GOVERNANCE.md`.
Everything else comes from the sanctioned-defaults table below or the relevant `STK-*`
canonical tables. Free/open tooling first per Constitution C6.

| Problem class | Sanctioned default | Escalate to | Only when |
|---|---|---|---|
| Web app / API backend | One deployable modular monolith (per `STK-*`) | Extracted service | ARC-PATTERNS-02 trigger recorded |
| Background / scheduled work | launchd/cron + plain script (`ARC-CONCURRENCY-01`) | SQS worker + DLQ | T3+ and jobs are lost or overlapping |
| Component-to-component calls | In-process function call | Queue / events | ARC-PATTERNS-03 pain observed |
| Persistence | SQLite (single writer) | PostgreSQL | Concurrent writers or >1 app instance |
| Incomplete / risky features | Feature flag in config (`ARC-CONFIG-04`) | — | Long-lived branches are never the escalation |
| Code reuse | Duplicate until the third use | Shared module (`ARC-MODULARITY-04`) | Third use with identical semantics |
| Caching | None — measure first | In-process dict → Redis | A measured hot path, with an invalidation story |

### ARC-PATTERNS-02 — Architecture SHOULD start monolith-first; services are extracted on demonstrated need, never presumed

**Tiers**: all advisory — **Layer**: A (attestation)

Valid extraction triggers, each recorded in `GOVERNANCE.md` when used: measured divergent
scaling (one component saturates while the rest idles), isolation of a failure domain that
has actually failed, or a hard security boundary (running untrusted code). "We might need
it later" is not a trigger. Team boundaries — the classic driver — do not exist for a solo
developer, which removes most of the case for microservices at any tier here.

### ARC-PATTERNS-03 — Queues SHOULD be introduced for decoupling only at T3+, against demonstrated scale pain

**Tiers**: all advisory — **Layer**: A (attestation)

Demonstrated means observed: request timeouts caused by inline work, a producer outrunning
its consumer, work lost on crash that buffering would have saved. Projections don't count.
Below that threshold the sanctioned mechanisms are a function call or a cron script
(`ARC-CONCURRENCY-01`). Once a queue is justified, its mechanics follow
`ARC-CONCURRENCY-05` and every consumer follows `ARC-IDEMPOTENCY`.

### ARC-PATTERNS-04 — Incomplete or risky work SHOULD ship dark behind feature flags, not sit on long-lived branches

**Tiers**: all advisory — **Layer**: A (attestation)

A branch approaching a week unmerged gets merged behind a flag instead of aging further —
integration pain grows with divergence, not with feature size. Flags are config
(`ARC-CONFIG-04`), default-off, and deleted once fully on; a flag older than a quarter is
a branch with extra steps. Branch mechanics themselves belong to `DEV-GIT`.

### ARC-PATTERNS-05 — Design conflicts SHOULD be resolved against this standard's tables, with deviations recorded

**Tiers**: all advisory — **Layer**: A (attestation)

When two standards, a stack doc, or an agent's instinct disagree about a design, the
sanctioned-defaults table and the anti-pattern table are the tiebreaker. Deviating is
legitimate with a recorded reason (C9) — silent drift is not. New scar tissue is promoted
into these tables through `/evolve-standards` (C10), never patched into an agent's memory.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1–5 | attestation checklist (one entry per rule) | explicit yes recorded | ARC-PATTERNS-01…05 |

**Remediation:** attestation "no" on 01/02/03 → either simplify to the sanctioned default
or record the trigger/reason and re-attest · "no" on 04 → merge behind a default-off flag
this session · "no" on 05 → add the deviation note to `GOVERNANCE.md`; if the deviation
keeps recurring, propose a table change via `/evolve-standards` instead of re-attesting
around it.

## Worked Example

Decision trace for a T1→T3 candidate (the shape ARC-PATTERNS-02/03 expect in
`GOVERNANCE.md`):

```markdown
## Architecture decisions — ai-news-aggregator
- 2026-07-22 Scheduled fetching + summarization needed.
  Considered: SQS + Lambda pipeline. Rejected — no observed queue pain (ARC-PATTERNS-03).
  Chosen: launchd + script + SQLite (pattern table rows 2 and 4).
  Innovation token: none spent.
- 2026-07-22 Digest UI behind flag `enable_email_digest` (ARC-PATTERNS-04), default off.
```

## Anti-Patterns

The master table. Other ARC standards reference these by name.

| Anti-pattern | Smell | Why it fails | Do instead |
|---|---|---|---|
| Premature microservices | Network boundary where a function call worked; N repos for one product | Distributed failure modes, deploy orchestration, and latency bought with zero benefit at solo scale | Monolith-first (ARC-PATTERNS-02) |
| Premature abstraction / DRY-before-3 | Base class or `utils` helper extracted at the second (or first) use | The wrong abstraction hardens and every future case gets bent to fit it | Rule of three (`ARC-MODULARITY-04`) |
| God object | One class/module that knows everything; every change touches it; 500+ lines | Unreviewable diffs, test setup requiring the world, change amplification | Split along responsibility seams (`ARC-MODULARITY-05`) |
| Distributed monolith | Services that must deploy together or share a database | All microservice costs, none of the independence | Real boundaries or one deployable — never the middle |
| Resume-driven architecture | Tech chosen for novelty (Kubernetes for a cron job) | The ops burden outlives the excitement; solo dev pages himself | Boring default; one recorded innovation token (ARC-PATTERNS-01) |
| Clever-over-clear | Dense one-liners, metaprogramming, implicit magic | The next reader — future James or an agent — burns context deciphering instead of building | Explicit, boring code; cleverness goes in the tests |

## References

- Dan McKinley, "Choose Boring Technology" — source of the innovation-token framing in
  ARC-PATTERNS-01.
- Martin Fowler, "MonolithFirst" bliki — the evidence base for ARC-PATTERNS-02: successful
  microservice systems almost all started as monoliths.
- Sandi Metz, "The Wrong Abstraction" — why duplication is cheaper than the wrong
  abstraction (DRY-before-3 row).
- Fowler, "Yagni" bliki — the general form of the "demonstrated need, not projected need"
  test used in rules 02 and 03.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
