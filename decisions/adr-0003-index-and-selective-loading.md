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
`requires`, two hops max). Budget: constitution + index + typical selected set ≤ ~15k
tokens, enforced by a Phase-4 measurement. The generator refuses to index content changes
without a version bump, making the index double as the evolution gate.

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
