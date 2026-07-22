---
id: OPS-INCIDENT
title: Incident Response
family: OPS
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - incident
  - outage
  - postmortem
  - leak
  - leaked secret
  - exposed key
  - compromise
  - rotate
  - breach
  - root cause
  - filter-repo
requires: []
verification:
  - cmd: "attest: user-facing incidents have a note (what/impact/timeline/root cause/prevention) filed to the vault inbox"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-INCIDENT-01]
    tiers: [T3, T4]
  - cmd: "attest: any credential exposure ran the full secrets-leak playbook, rotation first"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-INCIDENT-02]
  - cmd: "attest: account-recovery paths for aws and github (mfa devices, recovery codes, root email access) are current"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-INCIDENT-03]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Incident Response (OPS-INCIDENT)

## Abstract

Proportionate incident handling for a solo operator. T1/T2: fix it, and if the failure
taught something, capture a note via `/harvest-learnings` — no ceremony. T3+:
user-facing incidents get a short blameless note (what/impact/timeline/root
cause/prevention) that feeds `/evolve-standards`. This doc also carries the full
secrets-leak playbook that `SEC-SECRETS-05` points at — rotation first, always — and the
escalation paths for AWS or GitHub account compromise. The framework absorbs any honest
failure (C9); the only unforgivable one is the silent kind.

## Normative Rules

### OPS-INCIDENT-01 — T3+ user-facing incidents MUST get a short, blameless incident note

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

"User-facing" = anyone other than James was blocked, served errors, or had data
exposed. The note is five headings, half a page: **what** happened, **impact** (who/how
long/how bad), **timeline** (detect → mitigate → resolve, with the detection source —
did `OPS-ALERTS` catch it or did a human?), **root cause**, **prevention** (concrete
change, owner = James, done-by date). Blameless is trivially true solo but still
binding on the write-up: causes are systemic ("no staging gate"), not character flaws
("was careless"). Notes land in the Obsidian vault inbox via `/harvest-learnings` so
`/evolve-standards` can promote recurring causes into standards (C10). T1/T2:
fix-and-move-on is correct; write a note only when the lesson is instructive.

### OPS-INCIDENT-02 — Any credential exposure MUST run the secrets-leak playbook, rotation first

**Tiers**: all required — **Layer**: A (attestation)

This is the playbook `SEC-SECRETS-05` mandates. Trigger: a secret seen in a tracked
file, pushed history, log output, terminal share, screenshot, or pasted LLM context.
Execute in order:

1. **Revoke/rotate at the provider — immediately, before anything else.** AWS: deactivate
   the access key in IAM, issue a new one, update stores. GitHub: revoke the
   PAT/deploy key. Anthropic/OpenAI: revoke in console. The old credential must be dead,
   not just superseded. Assume compromise from the moment of exposure — pushed secrets
   are scraped by bots within minutes.
2. **Assess the exposure window and scope.** How long was it live, where did it reach
   (public repo vs local log), and what could it access? Write down the window — step 4
   audits against it.
3. **Purge from history if feasible** — `git filter-repo --replace-text` (or
   `--invert-paths` for whole files), force-push, note that forks/clones/caches may
   retain it. Purging is hygiene, **never a substitute for step 1**: a rotated key in
   old history is inert; an unrotated key in "cleaned" history is still a live breach.
4. **Check provider audit logs for abuse during the window.** AWS: CloudTrail for calls
   by the key (unexpected regions, `RunInstances`, IAM changes) + Billing for spend
   spikes. GitHub: security log. Anthropic/OpenAI: usage dashboards. Abuse found →
   this escalates to account compromise (OPS-INCIDENT-03) and, at T4 with third-party
   data, `DATA-PRIVACY` notification duties.
5. **File a harvest-learnings note**: how the secret got out, and which guard
   (hook, scanner, habit) failed or was missing — that gap is the prevention item.

### OPS-INCIDENT-03 — Escalation paths for AWS/GitHub account compromise MUST be current

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Full account compromise (not just one key) is handled with provider recovery, and the
prerequisites must exist *before* the bad day. **AWS**: root email + MFA recoverable;
suspected compromise → rotate root password, rotate/delete all access keys, review IAM
for planted users/roles/trust policies, then AWS Support "Account & billing" case
(free tier includes account-compromise support; start at
`https://aws.amazon.com/support` or re:Post "potential account compromise" runbook).
**GitHub**: recovery codes stored offline (not in the account they recover); compromise →
rotate password, revoke all PATs/OAuth apps/SSH keys, check the security log, then
`https://support.github.com`. Verify annually (during `/evolve-standards`) that MFA
devices and recovery codes are current — T4 requires MFA on all accounts (tiers.md).

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attestation — incident notes filed (T3+) | explicit yes recorded | OPS-INCIDENT-01 |
| 2 | attestation — playbook run on any exposure (all tiers) | explicit yes recorded | OPS-INCIDENT-02 |
| 3 | attestation — recovery paths current (T3+) | explicit yes recorded | OPS-INCIDENT-03 |

**Remediation:** exposure handled by "deleted the commit" only → the key is still live:
run the playbook from step 1 now · incident closed without a note at T3+ → write it
while memory is fresh, backfill the timeline from logs/alerts · recovery codes location
unknown → regenerate and store offline today.

## Worked Example

Playbook run — Anthropic key committed to a public repo and pushed:

```bash
# 1. Rotate FIRST — console.anthropic.com → API keys → revoke old, create new
#    then update the .env / SSM entry that consumers read (SEC-SECRETS-03)
# 2. Window: pushed 14:02, noticed 14:31 → ~29 min public. Scope: API spend only.
# 3. Purge (hygiene, after rotation):
echo 'sk-ant-api03-OLDKEY==>[REMOVED]' > /tmp/replace.txt
git filter-repo --replace-text /tmp/replace.txt
git push --force-with-lease origin main    # solo repo; C4 shared-branch rule not violated
# 4. Audit: console.anthropic.com usage 14:00–14:35 → no unexpected calls
# 5. Harvest note: "pre-commit secret-scan hook missing in this repo" → prevention:
#    bootstrap hooks (SEC-SECRETS-01 layer H) — filed to vault inbox
```

Incident note skeleton (T3+, `docs/incidents/2026-07-22-api-outage.md`):

```markdown
# 2026-07-22 — API 5xx spike
What: /orders returned 500s after deploy of 3f2a91c
Impact: all users, 22 min, ~40 failed requests
Timeline: 14:02 deploy → 14:04 CloudWatch alarm (caught by OPS-ALERTS) →
  14:09 rollback started → 14:24 healthy
Root cause: migration ran after code, not before (OPS-DEPLOY-06 violation)
Prevention: migrate step moved ahead of deploy in workflow — done, PR #41
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Deleting the leaked secret and moving on | History/scrapers still have it; key is live | Rotate first — playbook step 1 (OPS-INCIDENT-02) |
| `git filter-repo` as the *whole* response | Cleans your copy, not clones/caches/scrapes | Purge only after rotation (OPS-INCIDENT-02) |
| Skipping the audit-log check ("rotated, done") | Misses abuse during the window; spend/IAM surprises later | CloudTrail + billing for the window (OPS-INCIDENT-02) |
| Postmortem theater at T1 (template, severity matrix) | Ceremony nobody reads; erodes the habit for real ones | Fix it; note it only if instructive (OPS-INCIDENT-01) |
| "Root cause: I was careless" | Not actionable; the same slip recurs | Name the missing guard, add it (OPS-INCIDENT-01) |
| Recovery codes stored in the account they recover | Lockout and recovery die together | Offline/second-store copy (OPS-INCIDENT-03) |
| Incident lessons living only in memory | Next session's agent repeats the mistake | Vault note → `/evolve-standards` (C10) |

## References

- git-filter-repo docs — the sanctioned history-purge tool (BFG's successor) for
  playbook step 3.
- AWS re:Post "What do I do if I notice unauthorized activity in my AWS account?" —
  the vendor runbook OPS-INCIDENT-03 summarizes.
- GitHub docs, "Reviewing your security log" + account recovery — GitHub-side audit and
  recovery paths.
- Google SRE Book, "Postmortem Culture" — blameless framing, scaled down to n=1 in
  OPS-INCIDENT-01.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
