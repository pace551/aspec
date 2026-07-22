---
id: OPS-FINOPS
title: Cost Management
family: OPS
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - cost
  - budget
  - billing
  - spend
  - aws budgets
  - free tier
  - nat gateway
  - llm cost
  - api spend
  - tags
  - pricing
requires: []
verification:
  - cmd: "attest: an aws budgets alarm existed before the first deploy of anything that can bill"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-FINOPS-01]
  - cmd: "attest: llm api spend is capped provider-side and the per-project monthly cap is noted in governance.md"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-FINOPS-02]
  - cmd: "attest: all aws resources carry cost-allocation tags with project = repo name"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-FINOPS-03]
    tiers: [T3, T4]
  - cmd: "attest: a cost review happened within the last month across active billing projects"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-FINOPS-04]
  - cmd: "attest: architecture is serverless/free-tier-first and contains no canonical money leaks (nat gateway, always-on rds) without justification"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-FINOPS-05]
last_review: 2026-07-22
---

# Cost Management (OPS-FINOPS)

## Abstract

Keeps personal-scale projects from billing like enterprises. The hard rule (Constitution
C6, no tier discount): an AWS Budgets alarm exists *before* the first deploy of anything
that can bill. LLM API spend gets the same treatment — provider-side caps plus a
per-project monthly cap noted in GOVERNANCE.md. All AWS resources carry cost-allocation
tags (project = repo name); a monthly cost review rides the `/evolve-standards` rhythm;
architecture defaults to serverless/free-tier, and the canonical money leaks — NAT
gateways and always-on RDS for toys — are named and banned.

## Normative Rules

### OPS-FINOPS-01 — An AWS Budgets alarm MUST exist before the first deploy of anything that can bill

**Tiers**: all required — **Layer**: A (attestation; the C6 spend-consent gate is H at deploy time)

Sequencing is the rule: budget first, deploy second — never "add monitoring later".
Minimum: one AWS Budget with actual + forecast email alerts at 80%/100% of a threshold
appropriate to the project. Defaults (override with a note in GOVERNANCE.md): **$10/mo**
for a T1/T2 experiment, **$25/mo** T3, T4 set per revenue model. One account-wide
catch-all budget also exists as backstop, but per-project budgets (via tags,
OPS-FINOPS-03) are what make the alert actionable. A budget alert is a symptom alert
and routes like any page (`OPS-ALERTS-01`).

### OPS-FINOPS-02 — LLM API spend MUST be capped provider-side, with the cap noted in GOVERNANCE.md

**Tiers**: all required — **Layer**: A (attestation)

The LLM analogue of the budget alarm: before the first paid-API call ships in any
automation, set the provider-side limit (Anthropic console spend limit; equivalent per
provider) and write the per-project monthly cap in GOVERNANCE.md notes. A runaway loop
in a scheduled job can burn a month's budget overnight — the cap converts that into a
capped failure plus an alert. Retry/backoff discipline that prevents the loop in the
first place is `ARC-CONCURRENCY`; current pricing is always looked up live (C8), never
assumed.

### OPS-FINOPS-03 — All AWS resources MUST carry cost-allocation tags; project tag = repo name

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Minimum tag set: `project` (exactly the GitHub repo name) and `env` (`prod`/`staging`).
Applied via Terraform `default_tags` (`INF-TF`) so it is impossible to forget, and
`project` is activated as a cost-allocation tag in the billing console. This is what
turns the monthly bill from a number into an answer — per-project spend, and orphaned
untagged resources become visible as the anomaly line.

### OPS-FINOPS-04 — A monthly cost review MUST happen, riding the /evolve-standards rhythm

**Tiers**: all required — **Layer**: A (attestation)

The fast-lane monthly pass (with the quarterly `/evolve-standards` sweep as the full
review): open Cost Explorer grouped by the `project` tag plus each LLM provider's usage
dashboard, and answer three questions — anything unexpected? anything orphaned (billing
but no longer used → destroy it)? any budget threshold now wrong (adjust with a
GOVERNANCE.md note)? Ten minutes; also the moment `OPS-ALERTS-03` noisy-alert review
happens. Findings that generalize get harvested (C10).

### OPS-FINOPS-05 — Architecture SHOULD be serverless/free-tier-first; canonical money leaks are banned for toys

**Tiers**: all advisory — **Layer**: A (attestation)

Default shapes for T1–T3 experiments: Lambda + API Gateway/Function URLs, DynamoDB
on-demand, S3, SQS, EventBridge — all scale-to-zero. The canonical leaks, banned
without a written justification in GOVERNANCE.md: **NAT gateways** (~$32/mo + data
before any value — put Lambdas outside the VPC or use VPC endpoints) and **always-on
RDS** for toy projects (SQLite + Litestream per `OPS-BACKUP-03`, or DynamoDB, or Aurora
Serverless v2 scaled to zero). "It's what production shops use" is not a justification
at personal scale — C6's free-by-default applies to architecture choices, not just
sign-ups.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attestation — budget alarm predates first deploy | explicit yes recorded | OPS-FINOPS-01 |
| 2 | attestation — LLM caps set + noted | explicit yes recorded | OPS-FINOPS-02 |
| 3 | attestation — cost tags (T3+) | explicit yes recorded | OPS-FINOPS-03 |
| 4 | attestation — monthly review done | explicit yes recorded | OPS-FINOPS-04 |
| 5 | attestation — no unjustified money leaks | explicit yes recorded | OPS-FINOPS-05 |

**Remediation:** deployed without a budget → stop, create the budget now, then note the
sequencing miss per C9 · no LLM cap → set the console spend limit before the next
scheduled run · untagged resources → add `default_tags` to the provider block, apply ·
NAT gateway on a toy → move Lambda out of the VPC or add gateway endpoints, destroy the
NAT · idle RDS instance → snapshot, destroy, migrate to SQLite/DynamoDB.

## Worked Example

Budget-before-deploy, scriptable (`budget.json` + one CLI call, run before the first
`terraform apply`):

```json
{"BudgetName": "mytool-monthly", "BudgetLimit": {"Amount": "10", "Unit": "USD"},
 "TimeUnit": "MONTHLY", "BudgetType": "COST",
 "CostFilters": {"TagKeyValue": ["user:project$mytool"]}}
```

```bash
aws budgets create-budget --account-id "$AWS_ACCOUNT_ID" --budget file://budget.json \
  --notifications-with-subscribers \
  '[{"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80},
     "Subscribers":[{"SubscriptionType":"EMAIL","Address":"'"$ALERT_EMAIL"'"}]},
    {"Notification":{"NotificationType":"FORECASTED","ComparisonOperator":"GREATER_THAN","Threshold":100},
     "Subscribers":[{"SubscriptionType":"EMAIL","Address":"'"$ALERT_EMAIL"'"}]}]'
```

Tags via Terraform, impossible to forget (`INF-TF`):

```hcl
provider "aws" {
  default_tags { tags = { project = "mytool", env = "prod" } }
}
```

GOVERNANCE.md notes block:

```markdown
## Cost notes (OPS-FINOPS)
- AWS budget: mytool-monthly, $10/mo (T1 default), created 2026-07-20 (pre-deploy)
- LLM cap: Anthropic $20/mo provider-side limit; project cap $15/mo
- Last cost review: 2026-07-01 — nothing unexpected
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| "Deploy first, add a budget when it matters" | It matters at the first surprise bill; too late | Budget precedes deploy — hard sequencing (OPS-FINOPS-01) |
| Client-side spend tracking as the only LLM cap | A crashed tracker or retry loop bills unbounded | Provider-side hard limit (OPS-FINOPS-02) |
| Tagging resources by hand per-resource | One forgotten resource breaks attribution | `default_tags` at the provider (OPS-FINOPS-03) |
| Default VPC-with-NAT wizard output for a Lambda toy | ~$32/mo before a single request | No-VPC Lambda or VPC endpoints (OPS-FINOPS-05) |
| db.t3.micro RDS "because it's small" for a T1 tool | Always-on billing for zero-traffic state | SQLite + Litestream / DynamoDB on-demand (OPS-FINOPS-05) |
| Pricing decisions from memory | Model/instance pricing shifts constantly | Live lookup at decision time (C8) |
| Ignoring the budget email as noise | The one symptom alert for money is now dead | Treat as a page: investigate same day (OPS-ALERTS-02) |

## References

- AWS Budgets docs (create-budget, notifications) — the exact mechanism OPS-FINOPS-01
  mandates; free for the first two budgets.
- AWS cost-allocation tags docs — activation step required before tags appear in Cost
  Explorer (OPS-FINOPS-03).
- Anthropic console spend-limits docs — the provider-side cap for OPS-FINOPS-02.
- AWS NAT gateway pricing page — the receipts behind the canonical-leak ban.
- Constitution C6 — the parent invariant: spend requires consent, budget before deploy.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
