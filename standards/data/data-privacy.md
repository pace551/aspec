---
id: DATA-PRIVACY
title: Privacy & PII
family: DATA
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - pii
  - privacy
  - personal data
  - email address
  - user data
  - anonymize
  - gdpr
  - signup
  - user account
requires: []
verification:
  - cmd: "sh -c 'grep -q \"pii_inventory\" GOVERNANCE.md'"
    expect: "exit 0 — GOVERNANCE.md carries a pii_inventory key (`pii_inventory: none` counts)"
    layer: G
    rules: [DATA-PRIVACY-01]
    tiers: [T3, T4]
  - cmd: "attest: every PII field collected is needed by a specific live feature, not stored speculatively"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-PRIVACY-02]
  - cmd: "attest: no PII appears in logs, error reports, or test fixtures (emails included)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-PRIVACY-03]
  - cmd: "attest: every PII field that enters an LLM prompt is noted as such in the PII inventory"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-PRIVACY-04]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Privacy & PII (DATA-PRIVACY)

## Abstract

Retires the failure mode where personal data spreads beyond where anyone decided it should
be: into logs, fixtures, error reports, or LLM prompts. Compliance in one breath: at T3+
`GOVERNANCE.md` carries a `pii_inventory` (or the explicit answer `none`), every field
collected is needed by a live feature, and PII never leaks into observability output, test
data, or prompts without an inventory entry. At T1/T2 James's own and household data is
personal data hygiene, not compliance theater — the carve-out relaxes the ceremony, never
the no-logs/no-fixtures rules. Email addresses are PII. The oracle anonymization pattern is
the house example of PII-safe LLM use.

## Normative Rules

### DATA-PRIVACY-01 — A PII inventory MUST exist in `GOVERNANCE.md` at T3+

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G

`GOVERNANCE.md` carries a `pii_inventory` key listing, per field: `field`, `store` (where it
lives), `purpose` (the feature that needs it), `retention` (cross-ref `DATA-RETENTION`).
`pii_inventory: none` is a valid and common answer — the point is that "we hold no PII" is a
recorded claim, not an assumption. PII means anything identifying a natural person: names,
email addresses, phone numbers, physical addresses, IPs tied to accounts, government IDs,
payment details. Email addresses are always PII, including in mailing-list-only projects.

### DATA-PRIVACY-02 — Collect only what the feature needs

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Data minimization is the default design stance: a field is collected because a specific
live feature reads it, not because it might be useful later. "We might want it for
analytics someday" is a reason to *not* collect — add it when the feature exists. Every
inventory entry's `purpose` names that feature; an entry with no purpose is a deletion
candidate, not a keeper.

### DATA-PRIVACY-03 — PII MUST NOT appear in logs, error reports, or test fixtures

**Tiers**: all required — **Layer**: A (attestation)

This is the one privacy rule with no household discount, because logs and fixtures outlive
intentions: they get committed, shipped to CloudWatch, pasted into debugging sessions.
Loggers reference users by opaque ID, never by email or name (`OPS-OBS` carries the
structured-logging detail); exception reporters scrub request bodies; test fixtures use
obviously-fake generated identities (`user-0001@example.com`), never production exports
(`TST-FIXTURES` governs fixture sourcing). A prod-data debugging copy is a temporary,
gitignored, deleted-after artifact — never a fixture.

### DATA-PRIVACY-04 — PII MUST NOT enter LLM prompts unless noted in the PII inventory

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Sending a field to any LLM (including Claude Code sub-agents) is disclosure to a third
party and gets flagged on that field's inventory entry (`llm: true` plus which provider).
Prefer the oracle pattern — the house example of doing this right: `llm-statement-analyst`
anonymizes SEC financials (strips issuer names, tickers, dates) before the prompt, so the
model grades numbers, not identities. Anonymize or pseudonymize before prompting whenever
the task allows; when it doesn't, the inventory says so explicitly. Secrets in prompts are
separately banned by `SEC-SECRETS-04`.

### DATA-PRIVACY-05 — Household data at T1/T2 MAY skip inventory ceremony

**Tiers**: T1–T2 advisory · T3–T4 n/a — **Layer**: A

James's own data and household data (mortgage figures, personal finance, family calendars)
at T1/T2 is personal data hygiene, not compliance theater: no inventory, no purpose
audit required. The carve-out ends at the rubric line — the moment a project holds a
third party's PII beyond an email address it is T4 territory (`tiers.md` line 1), and
DATA-PRIVACY-03 binds inside the carve-out regardless: household data still never lands in
logs or fixtures.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `grep -q "pii_inventory" GOVERNANCE.md` (T3+) | key present, even as `none` | DATA-PRIVACY-01 |
| 2 | attest: every field needed by a live feature | explicit yes | DATA-PRIVACY-02 |
| 3 | attest: no PII in logs/errors/fixtures | explicit yes | DATA-PRIVACY-03 |
| 4 | attest: LLM-prompted fields flagged in inventory (T3+) | explicit yes | DATA-PRIVACY-04 |

**Remediation:** missing key → add `pii_inventory:` block (or `none`) to GOVERNANCE.md ·
PII found in a log line → redact at the logger, ship the fix, treat existing log data per
`DATA-RETENTION` · production data in a fixture → replace with generated fakes and rotate
any co-leaked credentials.

## Worked Example

`GOVERNANCE.md` fragment for a T4 product with two PII fields, one LLM-adjacent:

```yaml
pii_inventory:
  - field: email
    store: postgres users.email
    purpose: login + transactional mail (UX-EMAIL)
    retention: life of account + 30d (DATA-RETENTION)
  - field: uploaded_statement_pdf
    store: s3://app-uploads/
    purpose: statement analysis feature
    retention: 90d after processing
    llm: anthropic — anonymized first (issuer/name/date stripped, oracle pattern)
```

And the matching log discipline — opaque IDs only:

```python
log.info("statement_processed", user_id=user.id, pages=n)   # ok
log.info(f"processed for {user.email}")                      # DATA-PRIVACY-03 violation
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Logging full request bodies "for debugging" | Every signup logs an email; logs replicate to places the DB never goes | Log opaque IDs + field names, not values |
| Prod DB dump as `tests/fixtures/users.json` | PII enters git history forever | Generated fakes (`user-0001@example.com`) |
| Collecting phone "for future 2FA" | Speculative PII is pure liability, zero feature value | Collect when the 2FA feature ships |
| Pasting a user record into an LLM chat to debug | Undisclosed third-party processing | Anonymize first; flag the field in the inventory |
| Treating email as "not really PII" | It is the canonical direct identifier | Inventory it, redact it in logs |
| `pii_inventory` absent because "we have no PII" | Unrecorded claims drift silently | Write `pii_inventory: none` — it's a valid answer |

## References

- oracle `llm-statement-analyst` — the house anonymize-before-prompt implementation
  DATA-PRIVACY-04 generalizes.
- GDPR Art. 5(1)(c) data minimisation — the principle behind DATA-PRIVACY-02, applied at
  personal scale without the bureaucracy.
- OWASP Logging Cheat Sheet ("what not to log") — source for the log-redaction stance in
  DATA-PRIVACY-03.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
