---
id: OPS-BACKUP
title: Backup & Disaster Recovery
family: OPS
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - backup
  - restore
  - disaster recovery
  - snapshot
  - litestream
  - rpo
  - rto
  - time machine
  - data loss
  - sqlite
  - rds
requires: []
verification:
  - cmd: "sh -c 'git remote | grep -q .'"
    expect: "exit 0 — at least one git remote configured (the code-backup floor)"
    layer: G
    rules: [OPS-BACKUP-01]
  - cmd: "attest: source is pushed to its remote; at t1, time machine + git remote is the accepted whole answer"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-BACKUP-01]
  - cmd: "attest: raw data inputs are cached or re-downloadable — results are reproducible from source + inputs"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-BACKUP-02]
    tiers: [T2, T3, T4]
  - cmd: "attest: every stateful store has automated backups on a schedule"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-BACKUP-03]
    tiers: [T3, T4]
  - cmd: "attest: rpo and rto are stated in governance.md notes and backup config matches them"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-BACKUP-04]
    tiers: [T3, T4]
  - cmd: "attest: a restore was performed successfully within the scheduled window and the runbook matches reality"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-BACKUP-05]
    tiers: [T4]
last_review: 2026-07-22
---

# Backup & Disaster Recovery (OPS-BACKUP)

## Abstract

Ensures nothing of value exists in exactly one place, proportionate to what losing it
costs. T1: Time Machine plus a pushed git remote is explicitly the whole answer. T2:
source *and data inputs* reproducible — raw data cached or re-downloadable. T3: every
stateful store backed up automatically (RDS snapshots, SQLite → S3 via Litestream or
scheduled copy) with RPO/RTO stated in GOVERNANCE.md. T4: restores actually tested on a
schedule with a runbook — an untested backup is not a backup.

## Normative Rules

### OPS-BACKUP-01 — Source MUST live on a git remote; at T1 that plus Time Machine is sufficient

**Tiers**: all required — **Layer**: G + A

Every project has a remote (GitHub) and work is pushed at least at every stopping point
— an unpushed repo is one disk failure from gone. At T1 this rule is deliberately the
ceiling, not the floor: Time Machine covering the working directory plus the pushed
remote **is fine** — no snapshots, no S3, no scripts. Do not build backup machinery for
throwaway tools; that is exactly the enterprise ceremony the tier model exists to
prevent.

### OPS-BACKUP-02 — T2+: data inputs MUST be reproducible — cached or re-downloadable

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

A T2 conclusion is only as durable as its inputs: every raw dataset is either cached
locally under a data directory covered by backup (and its acquisition scripted), or
re-downloadable by a committed script pinned to source, version/date-range, and format.
Record which — provenance and fixture handling per `TST-FIXTURES`. Derived artifacts
(features, model outputs) don't need backup if regenerating them is one command; the
raw inputs and the code are the recovery set (the oracle suite's cached free-data
pattern).

### OPS-BACKUP-03 — T3+: every stateful store MUST have automated, scheduled backups

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Anything holding state users would miss: RDS/Aurora → automated snapshots with ≥ 7-day
retention; DynamoDB → PITR enabled; SQLite in production → Litestream continuous
replication to S3 (default; near-zero cost) or at minimum a scheduled
`sqlite3 ".backup"` + S3 copy; S3 buckets holding primary data → versioning enabled.
"Automated" means no human in the loop and failure of the backup job itself alerts
(`OPS-ALERTS-05`). Manual `pg_dump` when-I-remember is not compliance.

### OPS-BACKUP-04 — T3+: RPO and RTO MUST be stated in GOVERNANCE.md notes

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

One line each: RPO (max acceptable data loss window) and RTO (max acceptable time to
restored service), plus what backs them ("RPO 24h via nightly RDS snapshot; RTO 4h via
snapshot restore + DNS"). The point is honesty, not ambition — "RPO 24h" consciously
chosen beats an implicit "whatever the defaults do". Backup config that contradicts the
stated numbers is a finding.

### OPS-BACKUP-05 — T4: restores MUST be tested on a schedule; a runbook MUST exist

**Tiers**: T1–T3 advisory · T4 required — **Layer**: A (attestation)

The rule with teeth: an untested backup is not a backup — it is a hope. At least
quarterly (calendar reminder or scheduled agent), perform an actual restore to a scratch
target: restore the snapshot / `litestream restore` to a temp path, run the app's
integrity check against it, tear down. The runbook (`RUNBOOK.md`) records exact
commands, expected duration (validating RTO), and the date + outcome of the last test.
A restore that fails or exceeds RTO is an incident-grade finding (`OPS-INCIDENT`).

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `git remote \| grep -q .` | a remote is configured | OPS-BACKUP-01 |
| 2 | attestation — pushed remote / T1 sufficiency | explicit yes recorded | OPS-BACKUP-01 |
| 3 | attestation — reproducible inputs (T2+) | explicit yes recorded | OPS-BACKUP-02 |
| 4-5 | attestation — automated backups, RPO/RTO (T3+) | explicit yes recorded | OPS-BACKUP-03, -04 |
| 6 | attestation — tested restore + runbook (T4) | explicit yes recorded | OPS-BACKUP-05 |

**Remediation:** no remote → create the GitHub repo and push now · irreplaceable raw
data sitting only in `/tmp` or a laptop download dir → move under the project data dir,
script the acquisition · prod SQLite with no replication → add Litestream (one config
file + supervisor) · RPO/RTO unstated → write the two lines in GOVERNANCE.md ·
never-tested T4 restore → schedule the first one this week.

## Worked Example

T3 SQLite service — Litestream sidecar config (`litestream.yml`):

```yaml
dbs:
  - path: /data/app.db
    replicas:
      - url: s3://mytool-backups/app-db
        retention: 168h        # 7 days — matches stated RPO in GOVERNANCE.md
```

GOVERNANCE.md notes block:

```markdown
## DR notes (OPS-BACKUP)
- RPO: ~1min (Litestream continuous WAL replication to s3://mytool-backups)
- RTO: 30min (litestream restore + redeploy; see RUNBOOK.md "Restore")
- Last restore test: 2026-07-10 — OK, 12min end-to-end   # T4: quarterly
```

Restore test (the T4 quarterly drill, run against a scratch path):

```bash
litestream restore -o /tmp/restore-test.db s3://mytool-backups/app-db
sqlite3 /tmp/restore-test.db "PRAGMA integrity_check; SELECT count(*) FROM users;"
rm /tmp/restore-test.db
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Building S3 backup scripts for a T1 toy | Ceremony with no risk retired | Time Machine + pushed remote — done (OPS-BACKUP-01) |
| Weeks of unpushed local commits | One disk failure loses the work despite "using git" | Push at every stopping point (OPS-BACKUP-01) |
| T2 raw dataset only in `~/Downloads` | Analysis irreproducible after cleanup day | Cache under project data dir + scripted fetch (OPS-BACKUP-02) |
| Backup = manual dump "when I remember" | Recall-based schedules have 100% eventual failure | Automated + failure-alerting job (OPS-BACKUP-03) |
| Backups and primary in the same blast radius (same disk/account root) | One compromise/failure takes both | Separate bucket, restricted principal (OPS-BACKUP-03) |
| "Backups are green" as restore evidence | Write success ≠ readable, complete, restorable | Scheduled restore drill (OPS-BACKUP-05) |
| Stated RPO 1h, nightly snapshot config | The number in GOVERNANCE.md is fiction | Align config to statement or statement to config (OPS-BACKUP-04) |

## References

- Litestream docs (litestream.io) — the near-free SQLite→S3 continuous replication that
  makes OPS-BACKUP-03 cheap at T3.
- AWS RDS automated backups + PITR docs — snapshot retention and restore mechanics.
- Google SRE Workbook, "Data Integrity" — origin of "the backup you haven't restored
  doesn't exist" behind OPS-BACKUP-05.
- AWS S3 Versioning docs — the one-checkbox backup for bucket-resident primary data.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
