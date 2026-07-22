# ADR-0003: Generated index.json + selective loading as the consumption model

- **Status**: accepted
- **Date**: 2026-07-22
- **Deciders**: James

## Context

67 standards total far exceeds what any agent should load per task; context is the scarce
resource. The framework is only real if standards actually reach the agent's context at the
right moment, cheaply and deterministically.

## Decision

We will generate `index.json` from standards frontmatter (`checks/build-index.py`) and make
it `/govern`'s sole entry point: constitution always loads; standards load only when the
index filter matches the task's tier, detected stacks, or trigger keywords (plus transitive
`requires`, two hops max). `/govern` never reads `index.json` wholesale — at 67 standards
the raw index alone is ~10k+ tokens — it filters it with `checks/select-standards.py`.
The tool has two modes: **pins** (everything applicable at the tier → GOVERNANCE.md;
all of it enforced by /verify-compliance) and **brief** (the in-context subset: parsed
rule-level detail only for stack-scoped matches, trigger matches, their requires
closure, and a small always-on core — everything else as id+title one-liners, loaded on
demand while working in that area). Enforcement scope is deliberately wider than context
scope: the gate runs what the context never saw. Budget: constitution + brief-mode JSON
≤ ~15k tokens, enforced by a Phase-4 measurement (measured worst case ≈ 10.8k at T4
full-stack). The generator refuses to index content changes without a version
bump, making the index double as the evolution gate.

## Alternatives considered

- **Load everything always** — blows the context budget ~10x; degrades task performance.
- **Let the agent browse standards/ ad hoc** — non-deterministic selection; the same task
  would get different rules on different days.
- **Hand-maintained INDEX.md** — guaranteed to drift from frontmatter; generation makes
  frontmatter the single source of truth.

## Consequences

Frontmatter quality (esp. `triggers`) is load-bearing and linted; index regeneration is a
mandatory post-edit step (self-gate makes forgetting loud); `GOVERNANCE.md` pins give
projects a stable view while the index moves forward.
