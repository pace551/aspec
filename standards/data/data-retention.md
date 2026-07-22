---
id: DATA-RETENTION
title: Retention & Lifecycle
family: DATA
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - retention
  - delete
  - deletion
  - lifecycle
  - purge
  - archive
  - ttl
  - expiry
  - log retention
requires: []
verification:
  - cmd: "sh -c 'grep -qi \"retention\" GOVERNANCE.md'"
    expect: "exit 0 — retention decisions written down in GOVERNANCE.md"
    layer: G
    rules: [DATA-RETENTION-01]
    tiers: [T3, T4]
  - cmd: "attest: every data category (user data, logs, backups, analytics, uploads) has a written retention line — 'forever' included"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-RETENTION-01]
  - cmd: "attest: log groups have an explicit retention period set — none are never-expire"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-RETENTION-02]
    tiers: [T3, T4]
  - cmd: "attest: backup retention/lifecycle rules exist and match the written policy"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-RETENTION-03]
    tiers: [T3, T4]
  - cmd: "attest: user-data deletion on request works end-to-end and the backup strategy note covers backup copies"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DATA-RETENTION-04]
    tiers: [T4]
last_review: 2026-07-22
---

# Retention & Lifecycle (DATA-RETENTION)

## Abstract

Every data category gets a retention answer — "forever" is a decision, not a default.
Compliance in one breath: at T3+ `GOVERNANCE.md` records how long each category lives (user
data, logs, backups, analytics, uploads), log groups have explicit expiry instead of
never-expire, backup lifecycle matches the written policy, and at T4 deletion-on-request
actually works end-to-end, backups included via a written strategy note. At T1/T2,
cheap-storage hoarding of James's own data is fine — the rule is that at T3+ the choice is
written down, not that hoarding stops.

## Normative Rules

### DATA-RETENTION-01 — Every data category MUST have a written retention decision

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G + A (attestation)

`GOVERNANCE.md` carries a retention note per category: user data (tie each `pii_inventory`
entry's `retention` field here — `DATA-PRIVACY`), logs, backups, analytics/derived data,
uploads/artifacts. "Forever" and "until the disk fills" are acceptable answers when
consciously chosen and written; only the *unwritten* default is a violation. Carve-out:
hoarding James's own data at T1/T2 on cheap storage is explicitly sanctioned — the
obligation is the writing-down, and it starts at T3.

### DATA-RETENTION-02 — Log retention MUST be explicitly set, never never-expire

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

CloudWatch log groups default to never-expire; every group gets `put-retention-policy`
(house default: 30–90 days; `OPS-OBS` owns what gets logged, this rule owns how long it
lives). Same for local log files (logrotate) and third-party log sinks. Logs are the
category most likely to hold accidental PII (`DATA-PRIVACY-03`), which makes unbounded log
retention a liability multiplier, not a safety net.

### DATA-RETENTION-03 — Backup retention MUST follow a lifecycle, not accumulate

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Backup cadence and restore testing belong to `OPS-BACKUP`; this rule requires that backup
*expiry* is configured (S3 lifecycle rules, snapshot retention counts) and matches the
written policy from DATA-RETENTION-01. An unbounded pile of daily snapshots is both a cost
leak (`OPS-FINOPS`) and a retention claim the privacy policy has to be honest about.

### DATA-RETENTION-04 — At T4, deletion on request MUST actually work end-to-end

**Tiers**: T1–T3 n/a · T4 required — **Layer**: A (attestation)

"We delete your data on request" must be executable, not aspirational: a documented,
tested procedure that removes the user's rows (hard-delete or anonymize — a soft-deleted
row is not deleted, `DATA-MODELING-06`), their uploads, and their presence in derived
stores. Backups get a written strategy note in `GOVERNANCE.md`: the house-acceptable
pattern is "backups expire within N days per lifecycle; deletion completes when the last
containing backup ages out; restores replay the deletion list." The privacy policy
(`LEG-COMMERCIAL`) must describe what the procedure actually does.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `grep -qi "retention" GOVERNANCE.md` (T3+) | retention notes present | DATA-RETENTION-01 |
| 2 | attest: all categories have a written retention line | explicit yes | DATA-RETENTION-01 |
| 3 | attest: no never-expire log groups (T3+) | explicit yes | DATA-RETENTION-02 |
| 4 | attest: backup lifecycle configured per policy (T3+) | explicit yes | DATA-RETENTION-03 |
| 5 | attest: deletion works end-to-end incl. backup note (T4) | explicit yes | DATA-RETENTION-04 |

**Remediation:** no retention notes → write the category table into GOVERNANCE.md (copy the
worked example) · never-expire group → `aws logs put-retention-policy --log-group-name X
--retention-in-days 90` · snapshots accumulating → add an S3 lifecycle/retention rule ·
deletion procedure untested → run it against a staging account before attesting.

## Worked Example

`GOVERNANCE.md` retention block for a T3 web app:

```yaml
retention:
  user_data: life of account + 30d          # matches pii_inventory entries
  logs: 90d                                  # CloudWatch put-retention-policy applied
  backups: daily, expire after 35d           # S3 lifecycle rule backup-expire-35d
  analytics: aggregates only, forever        # conscious decision — no row-level PII
  uploads: 90d after processing
```

The matching one-liner that makes the logs line true:

```bash
aws logs put-retention-policy --log-group-name /app/prod --retention-in-days 90
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Never-expire CloudWatch groups (the default) | Unbounded cost + unbounded accidental-PII liability | Set retention on every group (DATA-RETENTION-02) |
| "We delete on request" backed by no procedure | Policy lies; first real request becomes an incident | Tested end-to-end procedure + backup note (DATA-RETENTION-04) |
| Soft-delete counted as deletion | Row still exists, still retained, still discoverable | Hard-delete or anonymize for retention purposes |
| Retention policy that ignores backups | Deleted user restored by next month's restore | Backup aging strategy written into the note |
| Forcing T1 hobby data through retention ceremony | Weight with no risk retired; breeds framework resentment | Hoard freely at T1/T2; write it down from T3 |
| "Forever" chosen silently by never deciding | Nobody can defend it later | "Forever" written down — it's a valid decision |

## References

- AWS CloudWatch Logs `put-retention-policy` docs — never-expire is the default, which is
  why DATA-RETENTION-02 exists.
- S3 lifecycle configuration docs — the mechanism backing DATA-RETENTION-03.
- GDPR Art. 17 (erasure) — the shape of the T4 deletion obligation DATA-RETENTION-04
  encodes at personal-product scale.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
