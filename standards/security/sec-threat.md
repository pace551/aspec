---
id: SEC-THREAT
title: Threat Modeling
family: SEC
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - threat model
  - stride
  - attack surface
  - trust boundary
  - abuse case
  - public endpoint
  - webhook
  - third-party integration
  - security design
requires: []
verification:
  - cmd: "attest: a STRIDE-lite threat model exists in project docs covering entry points, assets, and trust boundaries"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-THREAT-01]
    tiers: [T3, T4]
  - cmd: "attest: the threat model was reviewed after the most recent attack-surface change (new entry point, integration, or data category)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-THREAT-02]
    tiers: [T3, T4]
  - cmd: "attest: abuse cases and third-party data flows are documented alongside the threat model"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-THREAT-03]
    tiers: [T4]
  - cmd: "attest: a 'what can go wrong' paragraph was written before building anything with an external input or side effect"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-THREAT-04]
    tiers: [T1, T2]
last_review: 2026-07-22
---

# Threat Modeling (SEC-THREAT)

## Abstract

Most security failures are design failures: the dangerous path nobody enumerated. This
standard makes "what can go wrong" an explicit, proportionate step — a five-minute
paragraph at T1/T2, a STRIDE-lite table (entry points, assets, trust boundaries) kept in
project docs at T3, plus abuse cases and third-party data-flow mapping at T4. The model is
revisited when the attack surface changes, not on a calendar. Verification is
attestation-based: the artifact exists and matches the deployed reality, or the checklist
fails. Threats identified here map to the SEC-* sibling that mitigates them — this
standard finds the risks; the others retire them.

## Normative Rules

### SEC-THREAT-01 — T3+ projects MUST maintain a STRIDE-lite threat model in project docs

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

One table in the repo (`docs/threat-model.md`, or a Threat Model section in the project
README) covering three columns of reality: **entry points** (routes, webhooks, queue
consumers, file inputs, scheduled jobs, admin scripts), **assets** (what is worth
stealing or corrupting — credentials, PII, financial records, the write path to
anything), and **trust boundaries** (browser↔API, API↔database, app↔third party,
CI↔cloud). Each identified threat gets a STRIDE category and either a mitigation
(referencing the SEC standard or code that provides it) or an explicit accepted-risk
note. Budget 30–60 minutes, not days — an honest one-pager beats an abandoned wiki.

### SEC-THREAT-02 — The threat model MUST be revisited when the attack surface changes

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Triggering events: a new entry point (route, webhook, upload, cron), a new third-party
integration, any authn/authz change, a new category of stored data, or a tier
escalation (`/govern` re-run). The update is diff-sized — add the new rows, adjust
affected mitigations — not a rewrite. No calendar cadence is imposed; a model that only
changes when the system changes stays honest, one refreshed by schedule goes stale
between reviews anyway.

### SEC-THREAT-03 — T4 projects MUST additionally document abuse cases and third-party data flows

**Tiers**: T1–T3 advisory · T4 required — **Layer**: A (attestation)

**Abuse cases**: ways a legitimate feature is misused at scale or in bad faith —
free-tier farming, scraping, spam relay through transactional email, payment fraud,
LLM-prompt abuse of any AI feature. **Third-party data flows**: every external processor
(payments, email, analytics, LLM APIs, error tracking) with exactly which data crosses
the boundary and why. This inventory is the input to retention and processor obligations
(`DATA-PRIVACY`) and to what must be redacted from telemetry (`OPS-OBS`).

### SEC-THREAT-04 — T1/T2 work SHOULD start with a five-minute "what can go wrong" paragraph

**Tiers**: T1–T2 advisory · T3–T4 n/a — **Layer**: A (attestation)

Before building anything that takes external input or performs a side effect: one
paragraph in the task notes or PR description naming what is exposed, the worst
plausible outcome, and one sentence per risk on why it is acceptable or which standard
mitigates it. A scraper that only reads public data and writes local files earns one
honest sentence; a script holding an AWS key earns three. At T3 this graduates into the
SEC-THREAT-01 table — n/a above T2 means superseded, not waived.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attest: STRIDE-lite model in project docs (T3+) | explicit yes recorded | SEC-THREAT-01 |
| 2 | attest: model reviewed after latest surface change (T3+) | explicit yes recorded | SEC-THREAT-02 |
| 3 | attest: abuse cases + third-party data flows (T4) | explicit yes recorded | SEC-THREAT-03 |
| 4 | attest: "what can go wrong" paragraph written (T1/T2) | explicit yes recorded | SEC-THREAT-04 |

**Remediation:** no model exists → run the 30-minute exercise in the Worked Example and
commit the table · model predates the last new endpoint/integration → add rows for the
new surface before attesting · attestation feels like a lie → it is one; C9 says record
the deviation, don't paper over it.

## Worked Example

STRIDE-lite table for a T3 personal-finance dashboard (web UI + one webhook + SQLite):

```markdown
## Threat Model (last revisited: 2026-07-22, after adding /webhook/plaid)

| # | Element (entry point) | Boundary | STRIDE | Threat | Mitigation / accepted risk |
|---|---|---|---|---|---|
| 1 | POST /login | browser → API | S | credential stuffing | SEC-AUTHN-05 throttling + SEC-AUTHN-04 MFA |
| 2 | GET /statements/{id} | browser → API | E | IDOR: another user's id | SEC-AUTHZ-03 ownership check, 404 on miss |
| 3 | POST /webhook/plaid | third party → API | T | forged webhook payload | HMAC signature verify before parse |
| 4 | statement upload | browser → API | D, T | oversized/malicious file | SEC-INPUT-05 size/type/name limits |
| 5 | SQLite file on disk | app → disk | I | laptop/backup theft | SQLCipher at rest (SEC-CRYPTO-04) |
| 6 | GitHub Actions deploy | CI → AWS | E | exfiltrated CI credential | OIDC role, no static keys (SEC-SECRETS-06) |

Assets: session tokens, linked-account credentials (held by Plaid, not us), transaction
history (PII), the deploy path. Trust boundaries: browser↔API, API↔SQLite, API↔Plaid,
CI↔AWS.
```

Six rows, one hour, and every row points at an enforceable control — that is full T3
compliance.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| 40-page enterprise threat model for a solo app | Never updated after week one; ceremony, not security | Proportionate one-pager (SEC-THREAT-01) |
| Model written at kickoff, never touched again | New webhook/integration ships unmodeled — the exact gap attackers find | Revisit on surface change (SEC-THREAT-02) |
| Modeling only the browser-facing happy path | Cron jobs, admin scripts, webhooks, and CI are entry points too | Enumerate *all* entry points, not just UI |
| Threats listed without mitigation mapping | A list of fears is not a model; nothing becomes actionable | Every row → mitigation or accepted-risk note |
| "We use HTTPS and hash passwords" as the model | Names two controls, zero threats; backwards | Start from what can go wrong, then map controls |
| Skipping the T1 paragraph because "it's just a script" | The script holds an AWS key and runs on cron — that's an asset and an entry point | Five minutes of SEC-THREAT-04 honesty |

## References

- Shostack, *Threat Modeling* — the Four Question Framework ("what are we building /
  what can go wrong / what will we do / did we do a good job") is the shape of this
  entire standard.
- OWASP Threat Modeling Cheat Sheet — source for the proportionate, iterative posture
  (model as living artifact, not deliverable).
- Microsoft STRIDE documentation — the six-category mnemonic the T3 table uses.
- OWASP API Security Top 10 — checklist used when enumerating API entry points (BOLA/
  IDOR at #1 justifies SEC-AUTHZ's prominence in every model).

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
