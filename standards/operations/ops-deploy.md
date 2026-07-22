---
id: OPS-DEPLOY
title: Deployment Pipelines
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
  - deploy
  - deployment
  - pipeline
  - rollback
  - staging
  - promote
  - ship
  - release to prod
  - github actions
  - migration
  - ecs
  - lambda
requires: []
verification:
  - cmd: "attest: production deploys run from CI only — no laptop has deployed to prod"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-DEPLOY-01]
    tiers: [T3, T4]
  - cmd: "attest: main is deployable right now; staging received and passed this change before prod"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-DEPLOY-02]
    tiers: [T3, T4]
  - cmd: "attest: a documented one-command rollback exists and the previous version/image is retained"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-DEPLOY-03]
    tiers: [T3, T4]
  - cmd: "attest: every deploy path is a script or make target — no memorized command sequences"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-DEPLOY-04]
  - cmd: "attest: the running version is identifiable — git sha exposed in /health or logged at startup"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-DEPLOY-05]
    tiers: [T3, T4]
  - cmd: "attest: db migrations are ordered before the code that needs them and are backward compatible one release back"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-DEPLOY-06]
    tiers: [T2, T3, T4]
last_review: 2026-07-22
---

# Deployment Pipelines (OPS-DEPLOY)

## Abstract

Makes shipping boring and reversal instant. T3+ compliance in one breath: only CI
deploys to prod, `main` is always deployable, every change lands on staging first and
promotes only past a healthcheck gate, rollback is one documented command against a
retained previous version, the running SHA is visible, and migrations precede the code
that needs them. T1/T2 discount: no staging or CI required — but even a laptop deploy is
a script target, never a memorized incantation.

## Normative Rules

### OPS-DEPLOY-01 — T3+ production deploys MUST run from CI only

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

No laptop deploys to prod: the GitHub Actions workflow is the only path, authenticated
via GitHub OIDC → AWS role (`SEC-SECRETS-06` — no long-lived keys on the laptop or in
repo secrets). This makes every deploy logged, reproducible, and tied to a commit, and
means a lost/compromised laptop cannot ship code. Emergency exception: a manual deploy
during an incident is allowed once, recorded in the incident note (`OPS-INCIDENT`), and
the gap that required it gets fixed.

### OPS-DEPLOY-02 — main MUST stay deployable; staging MUST receive every deploy first, promotion healthcheck-gated

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

`main` green means shippable this minute — half-done work lives on branches or behind
flags, never as a known-broken `main` (C4 already bans direct pushes at T3+). A staging
environment exists (cheap is fine: a second Lambda alias, a second ECS service at
min-capacity, per `INF-ENVS`), gets the artifact first, and promotion to prod happens
only after the staging healthcheck (`OPS-ALERTS-04` shape) passes — automated in the
workflow, not eyeballed.

### OPS-DEPLOY-03 — Rollback MUST be one documented command; the previous version stays retained

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

The rollback command is written in the project `RUNBOOK.md`/`CLAUDE.md` *before* the
first prod deploy, and the previous image/package/version is always retained (ECR keeps
≥ 2 tags, Lambda keeps the prior published version, previous git tag deployable).
Rolling back must not require a rebuild — rebuilds can fail, and rollback is exercised
precisely when things are failing. Migrations constrain this: see OPS-DEPLOY-06.

### OPS-DEPLOY-04 — Every deploy path MUST be scripted, never a memorized sequence

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

At T1/T2 a `make deploy` or `scripts/deploy.sh` running from the laptop is fully
compliant — the rule is *scripted-not-manual*, not *CI-or-nothing*. A deploy that lives
in shell history is undocumented, unrepeatable by an agent, and one typo from disaster.
The script is idempotent and safe to re-run.

### OPS-DEPLOY-05 — Deploys MUST be traceable: git SHA visible in /health or a startup log line

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Inject the SHA at build time (env var or baked file); expose it in the `/health`
response and/or log it as the first structured event on boot (`OPS-OBS`). Deploy events
themselves get a log line or CloudWatch event ("deployed {sha} to {env}"). "What is
actually running right now?" must be answerable in one request during an incident —
release tagging conventions live in `OPS-RELEASE`.

### OPS-DEPLOY-06 — DB migrations MUST run before the code that needs them, and stay compatible one release back

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Pipeline order: migrate, then roll code. Migrations are expand-then-contract: additive
change ships first (new column nullable/defaulted), code switches over, destructive
cleanup ships a release later — so the *previous* code version still runs against the
*new* schema, which is what keeps OPS-DEPLOY-03's rollback one command instead of a
restore. Schema/migration tooling and design rules live in `DATA-MODELING`.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1-3 | attestation checklist (T3+) | explicit yes recorded | OPS-DEPLOY-01…03 |
| 4 | attestation — scripted deploys (T2+) | explicit yes recorded | OPS-DEPLOY-04 |
| 5 | attestation — SHA traceability (T3+) | explicit yes recorded | OPS-DEPLOY-05 |
| 6 | attestation — migration ordering (T2+) | explicit yes recorded | OPS-DEPLOY-06 |

**Remediation:** laptop deploying to prod → move the script into a workflow with OIDC
role auth · no staging → cheapest same-shape copy (Lambda alias / min-size service) ·
no rollback path → pin previous image tag + write the command in RUNBOOK.md now ·
untraceable version → pass `GIT_SHA` as build arg, return it from `/health` ·
destructive migration in the same release as the code → split into expand/contract.

## Worked Example

T1: `Makefile` deploy target (scripted, OPS-DEPLOY-04 compliant):

```make
deploy:  ## deploy to personal lambda
	GIT_SHA=$$(git rev-parse --short HEAD) ./scripts/deploy.sh
```

T3: GitHub Actions promotion with healthcheck gate and one-command rollback:

```yaml
jobs:
  deploy:
    permissions: { id-token: write, contents: read }   # OIDC, no static keys
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with: { role-to-assume: "arn:aws:iam::123456789012:role/mytool-deploy" }
      - run: ./scripts/migrate.sh staging && ./scripts/deploy.sh staging $GITHUB_SHA
      - run: |   # healthcheck gate: staging must report the new SHA, healthy
          for i in $(seq 1 12); do
            out=$(curl -fsS https://staging.mytool.dev/health) &&
            echo "$out" | grep -q "\"version\":\"${GITHUB_SHA::7}\"" && exit 0
            sleep 10
          done; exit 1
      - run: ./scripts/migrate.sh prod && ./scripts/deploy.sh prod $GITHUB_SHA
```

Rollback (documented in `RUNBOOK.md`): `./scripts/deploy.sh prod <previous-sha>` —
previous image retained in ECR by lifecycle policy (keep last 5).

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `aws s3 sync` / `kubectl apply` from the laptop to prod | Untracked, unrepeatable, credential sprawl | CI-only path with OIDC (OPS-DEPLOY-01) |
| "Staging is basically prod, skip it this once" | The once is always the breaking one | Healthcheck-gated promotion, automated (OPS-DEPLOY-02) |
| Rollback = "revert the commit and redeploy" | Rebuild can fail exactly when you need it not to | Redeploy retained previous artifact (OPS-DEPLOY-03) |
| ECR lifecycle policy "keep only latest" | Deletes the rollback target | Keep last N images (OPS-DEPLOY-03) |
| Deploy steps in a README as prose | Drifts from reality; agents can't run prose | Script/make target, README points at it (OPS-DEPLOY-04) |
| Dropping a column in the same release that stops using it | Previous version can't run; rollback = restore | Expand-then-contract (OPS-DEPLOY-06) |

## References

- GitHub Actions OIDC → AWS docs — the keyless CI auth OPS-DEPLOY-01 mandates.
- 12-Factor App, factor V "Build, release, run" — artifact/config separation behind
  redeploy-not-rebuild rollback.
- "Evolutionary Database Design" (Fowler) — expand/contract migration pattern in
  OPS-DEPLOY-06.
- AWS ECR lifecycle policy docs — retention config that keeps rollback targets alive.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
