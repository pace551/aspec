# Tier Model

Every project has exactly one tier, recorded in its `GOVERNANCE.md`. Tiers scale governance
weight so T1 stays light by design and T4 is defensible to an outside party. Standards
declare per-tier applicability (`required` / `advisory` / `n/a`) in frontmatter; a rule's
tier tags override nothing in the Constitution, which always applies.

## The tiers

| Tier | Name | Definition | Failure cost | Posture |
|---|---|---|---|---|
| **T1** | Personal | Only James runs it; localhost or local files | Minutes of annoyance | Constitution + secrets + git hygiene hard; everything else advisory. Git hooks; CI not required. |
| **T2** | Research | Outputs inform real decisions (money, health, publication); conclusion-correctness matters more than uptime | A wrong decision made on bad analysis | T1 + test-first analytical core, data provenance, leakage guards, reproducibility (pinned deps, seeds, recorded data versions). |
| **T3** | Product | Internet-exposed and/or has users other than James; no revenue | Other people blocked, data exposed, reputation | Full SEC/OPS/UX required; CI mandatory; staging environment; a11y and performance gates. |
| **T4** | Commercial | Money changes hands, third-party PII is held, or it's publicly launched as a product | Legal/financial liability | T3 + legal baseline, retention/deletion, tested-restore DR, license audit, MFA on all accounts, DMARC. |

## Classification rubric

Apply top-down; **first match wins**:

1. Takes payment, is sold, or stores PII of people outside the household beyond an email
   address → **T4**
2. Runs as a **deployed service** beyond localhost with internet reach, OR people other
   than James use the running system → **T3**
3. Primary output is analysis, a model, a report, or a decision input → **T2**
4. Otherwise → **T1**

Carve-out — **published libraries/packages** (code others run, no service James operates):
classify by rubric lines 3-4 as usual, but supply-chain families (SEC, TST, DEV, LEG
licensing) apply at T3 weight. Service-only standards (staging, a11y, perf budgets,
observability) don't apply — there is no deployment to govern.

Rules of application:

- **Ambiguity → ask.** One `AskUserQuestion`, options being the two candidate tiers with the
  rubric line that triggered each. Never silently guess upward or downward.
- **User override wins** but is logged in `GOVERNANCE.md` as a waiver-style note
  (`tier_override: {from, to, reason, date}`).
- **The tier is a property of the deployment, not the code.** The same script is T1 on a
  laptop and T3 behind a public URL.

## Escalation triggers

Re-run `/govern` (which will re-classify and diff the standard set) when any of these happen:

- A T1 tool gets a URL, a second user, or starts acting on external parties (emails
  someone other than James, posts to third-party systems) → likely T3. A cron job whose
  outputs stay with James (e.g. a report emailed to himself) stays T1/T2 — automation
  alone doesn't escalate; audience does.
- A T2 analysis becomes a dashboard or scheduled report someone else consumes → T3
- A T3 product takes its first payment or stores its first third-party record → T4
- Tier *decreases* (product retired to personal use) — downgrade is allowed but must be explicit

Escalation is cheap on purpose: `/govern` re-emits the standard set and `/bootstrap-repo`
can retrofit missing CI/hooks. What is not allowed is operating at the old tier because
re-governing feels like ceremony.

## What tiers do NOT change

- The Constitution (all ten articles apply at every tier).
- Secret handling (C1 is hard everywhere).
- Honesty of verification reporting (C2) — a T1 "it works" still requires having run it.
