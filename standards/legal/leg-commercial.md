---
id: LEG-COMMERCIAL
title: Commercial Baseline
family: LEG
version: 1.0.0
status: active
tiers:
  T1: n/a
  T2: n/a
  T3: advisory
  T4: required
stacks: all
triggers:
  - launch
  - public launch
  - terms of service
  - privacy policy
  - payments
  - stripe
  - refund
  - dmarc
  - commercial
  - sell
  - customer
requires: []
verification:
  - cmd: "attest: ToS and privacy policy exist and describe the actual data practices in the GOVERNANCE.md pii_inventory"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [LEG-COMMERCIAL-01]
    tiers: [T3, T4]
  - cmd: "attest: a monitored support/contact email exists and is published"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [LEG-COMMERCIAL-02]
    tiers: [T3, T4]
  - cmd: "attest: if payments are taken, a refund policy is published"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [LEG-COMMERCIAL-03]
    tiers: [T4]
  - cmd: "attest: the business-entity and payments-provider questions were raised to James and his answers recorded"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [LEG-COMMERCIAL-04]
    tiers: [T4]
  - cmd: "attest: SPF, DKIM, and DMARC are configured on the sending domain"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [LEG-COMMERCIAL-05]
    tiers: [T3, T4]
  - cmd: "attest: MFA is enabled on every account in the product's path (registrar, DNS, cloud, payments, email, GitHub)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [LEG-COMMERCIAL-06]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Commercial Baseline (LEG-COMMERCIAL)

## Abstract

The pre-launch checklist for anything T4: the minimum a paying stranger is owed before
money or PII changes hands. Compliance in one breath: ToS and privacy policy exist and
tell the truth about the `pii_inventory`, a monitored support email is published, a refund
policy exists if payments do, the business-entity and payments-provider questions were put
to James (the framework raises them, never answers them), the sending domain has
SPF/DKIM/DMARC, and MFA is on every account in the product's path. Nearly all attestation
— this is a gate walked once before launch and re-attested at each verify.

## Normative Rules

### LEG-COMMERCIAL-01 — ToS and privacy policy MUST exist and reflect actual practice

**Tiers**: T1–T2 n/a · T3 advisory · T4 required — **Layer**: A (attestation)

Before public launch: Terms of Service and a privacy policy, linked from the product.
Template-derived is fine; what is not fine is fiction — the privacy policy must describe
the *actual* data practices recorded in the `GOVERNANCE.md` `pii_inventory`
(`DATA-PRIVACY-01`), including retention (`DATA-RETENTION-01`), deletion
(`DATA-RETENTION-04`), and any LLM processing (`DATA-PRIVACY-04`). A policy that lies is
worse than none: it converts an oversight into a documented misrepresentation. When
practice changes, the policy changes in the same release.

### LEG-COMMERCIAL-02 — A monitored support contact MUST exist

**Tiers**: T1–T2 n/a · T3 advisory · T4 required — **Layer**: A (attestation)

A support/contact email published on the product (and in the ToS), routed somewhere James
actually reads — forwarding to the personal inbox is fine; an unmonitored
`support@` black hole is not. This address is also the deletion-request intake
(`DATA-RETENTION-04`) and the security-report channel, which is why "monitored" is the
load-bearing word.

### LEG-COMMERCIAL-03 — Payments MUST come with a published refund policy

**Tiers**: T1–T3 n/a · T4 required — **Layer**: A (attestation)

If money is taken, the refund policy is written and published before the first charge —
what qualifies, the window, how to ask (the LEG-COMMERCIAL-02 address). Card networks and
payment providers require one anyway; deciding it before the first dispute means the
first dispute is procedure, not improvisation. n/a below T4 because taking payment *is*
the T4 rubric line.

### LEG-COMMERCIAL-04 — Entity and payments-provider questions MUST be raised to James, not answered by the framework

**Tiers**: T1–T3 n/a · T4 required — **Layer**: A (attestation)

Before first payment, put two questions to James and record his answers in
`GOVERNANCE.md`: (1) operate as sole proprietor or form an entity (LLC) — liability and
tax territory; (2) which payments provider, on what terms. The framework's job is that
these are asked *before* revenue exists, and that no agent answers them autonomously —
they are legal/financial decisions outside any standard's authority (and outside Claude
Code's: raise, stop, wait).

### LEG-COMMERCIAL-05 — The sending domain MUST have SPF, DKIM, and DMARC

**Tiers**: T1–T2 n/a · T3 advisory · T4 required — **Layer**: A (attestation)

Any domain a T4 product sends mail from (transactional or otherwise) publishes SPF and
DKIM, plus a DMARC record — start at `p=none` with reports, move to `p=quarantine` once
aligned. Without them, mail lands in spam (Gmail/Yahoo require DMARC from bulk senders)
and the domain is spoofable in phishing against your own users. `UX-EMAIL` owns
deliverability mechanics and sending practice; this rule owns the DNS records existing.

### LEG-COMMERCIAL-06 — MFA MUST be enabled on every account in the product's path

**Tiers**: T1–T3 advisory · T4 required — **Layer**: A (attestation)

Enumerate the accounts whose compromise is product compromise — registrar, DNS, AWS root
and IAM users, GitHub, payments provider, support mailbox, LLM provider console — and
enable MFA on each (authenticator app or hardware key; SMS only when nothing better is
offered). `SEC-AUTHN` governs authentication *inside* the product; this rule covers the
operator accounts *around* it, which is where solo-operator products actually get taken
over.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attest: ToS + truthful privacy policy published | explicit yes | LEG-COMMERCIAL-01 |
| 2 | attest: monitored support email published | explicit yes | LEG-COMMERCIAL-02 |
| 3 | attest: refund policy published (if payments) | explicit yes | LEG-COMMERCIAL-03 |
| 4 | attest: entity + provider questions raised to James | explicit yes | LEG-COMMERCIAL-04 |
| 5 | attest: SPF/DKIM/DMARC on sending domain | explicit yes | LEG-COMMERCIAL-05 |
| 6 | attest: MFA on all operator accounts | explicit yes | LEG-COMMERCIAL-06 |

**Remediation:** policy drifted from practice → update the policy in the next release, note
the change date in it · unmonitored support@ → forward to the personal inbox and test it ·
missing DMARC → publish `v=DMARC1; p=none; rua=mailto:…`, tighten after a clean reporting
cycle · MFA gaps → close registrar/DNS/cloud first (they can seize everything else).

## Worked Example

`GOVERNANCE.md` launch-gate block for a T4 product, filled in during the pre-launch walk:

```yaml
commercial_baseline:   # LEG-COMMERCIAL — walked 2026-07-22, re-attested each verify
  tos_url: https://app.example.com/terms          # template-derived, reviewed
  privacy_policy_url: https://app.example.com/privacy   # matches pii_inventory v1.2
  support_email: support@example.com               # forwards to personal inbox, tested
  refund_policy: 14-day, no questions — /refunds
  entity_decision: {asked: 2026-07-20, answer: "sole prop for now, revisit at $1k MRR"}
  payments_provider: {asked: 2026-07-20, answer: "stripe"}
  email_auth: {spf: pass, dkim: pass, dmarc: "p=quarantine since 2026-07-15"}
  mfa_accounts: [registrar, route53/aws, github, stripe, google-workspace, anthropic]
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Copy-pasted privacy policy claiming "we never share data" while prompts hit an LLM API | Documented misrepresentation — worse than no policy | Derive the policy from the pii_inventory (LEG-COMMERCIAL-01) |
| Launch first, "legal stuff" later | The baseline exists for the first angry stranger, who arrives on day one | Walk the checklist before the URL is public |
| `support@` that nobody reads | Deletion requests and security reports rot; card disputes auto-lose | Forward + test it (LEG-COMMERCIAL-02) |
| Framework/agent picks the LLC answer | Legal decision made without authority | Raise to James, record, stop (LEG-COMMERCIAL-04) |
| No DMARC because "we barely send email" | Domain spoofable; the little mail sent goes to spam | `p=none` + reports today, tighten later |
| MFA on the app but not the registrar | Attacker moves DNS, owns everything downstream | Operator accounts first (LEG-COMMERCIAL-06) |

## References

- Stripe / payment-network rules on refund and dispute policies — why LEG-COMMERCIAL-03
  precedes the first charge.
- Google/Yahoo bulk-sender requirements (2024-) — DMARC as a delivery prerequisite, not
  just an anti-spoofing nicety (LEG-COMMERCIAL-05).
- RFC 7489 (DMARC) — the record format and `p=` escalation path.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
