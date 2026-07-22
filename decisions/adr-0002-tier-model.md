# ADR-0002: Four-tier applicability model with first-match rubric

- **Status**: accepted
- **Date**: 2026-07-22
- **Deciders**: James

## Context

One rulebook for both a 50-line personal script and a commercial product either
over-burdens the former or under-protects the latter. Governance weight must scale with
blast radius, and the scaling must be a rubric an agent can apply deterministically — not a
judgment call made fresh each session.

## Decision

We will use four tiers — T1 personal, T2 research, T3 product, T4 commercial — defined in
`constitution/tiers.md` with a top-down first-match rubric keyed on payments/PII, internet
exposure/other users, and analysis-as-output. Every standard declares
`required/advisory/n-a` per tier in frontmatter. Ambiguity costs exactly one
AskUserQuestion; silent guessing is banned.

## Alternatives considered

- **Two tiers (personal/serious)** — loses the research tier, whose failure mode
  (wrong conclusions) needs different rules (leakage, provenance) than uptime-style rigor.
- **Continuous risk score** — not deterministic; two sessions would score the same project
  differently.
- **Per-project bespoke rule sets** — that's the status quo this framework replaces.

## Consequences

Every standard must think through four applicability answers (forcing function for tier
honesty); classification is cheap and auditable; escalation triggers (T1 tool gets
deployed) are re-classification events, recorded in GOVERNANCE.md.
