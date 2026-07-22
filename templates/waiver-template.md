# Waiver Template

A waiver exempts one rule in one project for a bounded time. It lives in the project's
`GOVERNANCE.md` `waivers:` list — this file documents the entry format and the policy.

```yaml
waivers:
  - rule_id: SEC-SAST-02          # exact rule ID, never a whole standard
    reason: >
      One concrete sentence: why compliance is wrong or impossible right now,
      and what would unblock it.
    expires: 2026-10-01           # mandatory; ≤180 days out
    granted: 2026-07-22
    granted_by: James             # waivers are a human decision, never self-granted by an agent
```

Policy:

1. **Rule-scoped** — waive `SEC-SAST-02`, not `SEC-SAST`. If you need to waive a whole
   standard, the tier classification is probably wrong; re-run `/govern`.
2. **Expiry mandatory, ≤180 days.** `/verify-compliance` fails on expired waivers and warns
   within 14 days of expiry. Renewal is allowed but is a fresh human decision.
3. **Human-granted.** An agent MAY draft a waiver and MUST stop for approval before adding
   it (Constitution C9).
4. **Waivers are data.** `/harvest-learnings` treats recurring waivers of the same rule as a
   signal the rule is miscalibrated — that feeds `/evolve-standards`, which fixes the rule
   instead of accumulating exemptions.
