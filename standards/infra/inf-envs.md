---
id: INF-ENVS
title: Environments & Promotion
family: INF
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: [aws]
triggers:
  - environment
  - staging
  - prod
  - promotion
  - promote
  - deploy to prod
  - oidc
  - aws credentials
  - github actions aws
  - deploy role
  - dev environment
requires: []
verification:
  - cmd: "sh -c '[ ! -d .github/workflows ] || ! grep -rqE \"aws-secret-access-key|AWS_SECRET_ACCESS_KEY\" .github/workflows'"
    expect: "exit 0 — no workflow references long-lived AWS keys"
    layer: G
    rules: [INF-ENVS-03]
  - cmd: "sh -c '[ ! -d .github/workflows ] || { f=$(grep -rl \"configure-aws-credentials\" .github/workflows || true); [ -z \"$f\" ] || ! echo \"$f\" | xargs grep -L \"role-to-assume\" | grep -q .; }'"
    expect: "exit 0 — every configure-aws-credentials step assumes an OIDC role"
    layer: G
    rules: [INF-ENVS-03]
  - cmd: "attest: the environment set matches the tier ladder (t1 local only, t3 staging+prod, t4 isolated account or strictly separated resource sets)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-ENVS-01]
  - cmd: "attest: prod only ever received an artifact that already ran in staging — promoted, not rebuilt"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-ENVS-02]
    tiers: [T3, T4]
  - cmd: "attest: each environment has its own deploy role scoped to that environment's resources"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-ENVS-04]
    tiers: [T3, T4]
  - cmd: "attest: no prod change since last verification bypassed the pipeline"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-ENVS-05]
    tiers: [T4]
  - cmd: "attest: staging is prod-shaped — same modules and topology, smaller sizes; differences are listed in governance.md"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-ENVS-06]
    tiers: [T3, T4]
  - cmd: "attest: env files and env vars encode only which environment this is (env name) — no per-environment behavior flags"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-ENVS-07]
last_review: 2026-07-22
---

# Environments & Promotion (INF-ENVS)

## Abstract

How many environments exist, how change flows between them, and how CI is allowed to
touch AWS. The ladder scales with tier: T1 runs locally, T3 runs staging+prod minimum,
T4 adds hard isolation. Change moves one way — dev → staging → prod — by promoting the
artifact that already passed, never rebuilding. The load-bearing rule is
authentication: CI reaches AWS only through GitHub OIDC federation into short-lived,
per-environment, least-privilege roles; long-lived AWS keys in GitHub secrets are
banned outright and greppably enforced. Environment identity is one `ENV` name;
behavior differences live in per-env config, not in code branching on environment.

## Normative Rules

### INF-ENVS-01 — The environment set MUST match the tier ladder

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

- **T1**: local only. No AWS environments to manage; a personal always-on stack is a
  single "prod" and that is fine.
- **T2**: local + whatever the analysis needs; reproducibility comes from pinned
  environments (STK rules), not deploy targets.
- **T3**: staging + prod minimum, as separate INF-TF roots (`envs/staging`,
  `envs/prod`) with separate state.
- **T4**: prod isolated in its own AWS account (Organizations, free) — the strongest
  blast wall. Falling back to one account requires strictly separated resource sets:
  per-env roles, no shared data stores, no wildcard cross-env IAM.

More environments than the tier needs is unowned spend (C6): tear down what nothing
uses.

### INF-ENVS-02 — Change MUST flow one way, promoting the same artifact — never rebuilding per environment

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

dev → staging → prod, no skips, no sideways hotfixes (a prod fix lands in dev/staging
first, then promotes). The artifact is immutable and identified — an image digest, a
zip checksum — and prod receives *the bytes staging tested*, not a fresh build of the
same commit (rebuilds pull moved tags and updated dependencies; "same source" is not
"same artifact"). Images are tagged by git SHA and promoted by retag; `latest` is not a
deployable reference. Pipeline mechanics live in OPS-DEPLOY; this rule owns the
artifact-identity invariant.

### INF-ENVS-03 — CI MUST reach AWS via GitHub OIDC federation; long-lived AWS keys in GitHub secrets are banned

**Tiers**: all required — **Layer**: G

The load-bearing rule. No `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` repository
secrets — a static key in CI is a standing credential that leaks in logs, forks, and
compromised actions, and it never expires on its own. Instead: one
`aws_iam_openid_connect_provider` for `token.actions.githubusercontent.com`, and
deploy roles whose trust policy pins the exact repo (and environment/branch) in the
`sub` claim — wildcards like `repo:owner/*` are a confused-deputy invitation. Tokens
are minutes-lived and scoped by the role, which is SEC-SECRETS-06 made concrete. Both
G checks grep workflows: no key material, and every `configure-aws-credentials` step
carries `role-to-assume`.

### INF-ENVS-04 — Each environment MUST have its own least-privilege deploy role

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

`{project}-staging-deploy` cannot touch prod ARNs; `{project}-prod-deploy` cannot
touch staging. Scope each role to the actions the pipeline actually performs on that
environment's resources (name- or tag-scoped ARNs, no `"Resource": "*"` beyond
API-level necessities). A staging pipeline compromise then costs staging, not prod —
and the prod role's trust policy can additionally require the pipeline's protected
`environment: prod` context.

### INF-ENVS-05 — Prod changes at T4 go only through the pipeline

**Tiers**: T1–T3 advisory · T4 required — **Layer**: A (attestation)

No laptop applies, no console edits, no "just this once" (drift per INF-TF-01;
apply-source per INF-TF-05). Break-glass exception: a genuine incident may act
directly, and the action is recorded in the incident notes and reconciled back into
code within a day (OPS-INCIDENT). At T3, laptop deploys with plan review are
sanctioned; the discipline still pays.

### INF-ENVS-06 — Staging MUST be prod-shaped: same topology, smaller sizes

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

Same INF-TF modules, same services, same wiring — different variable values (sizes,
counts, quotas). A staging that is "prod minus the queue" validates nothing about the
queue. Cost control comes from sizing (smallest Fargate tasks, minimal retention,
scale-to-zero) — never from omitting components. Deliberate gaps (e.g. no WAF in
staging, INF-EDGE-04) are listed in `GOVERNANCE.md` so everyone knows what staging
does not test.

### INF-ENVS-07 — Environment identity is one `ENV` name; per-environment behavior lives in config, not code

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

A deployable carries exactly one environment fact: `ENV=dev|staging|prod`. Code never
branches `if ENV == "prod": use_real_bucket()` — that hides prod-only paths staging
can't exercise. Differences are data, resolved per environment outside the code:
tofu variables per env root, SSM parameters under `/{project}/{env}/…`, task-def
values. `.env` files hold the ENV name and local-only overrides, never a second
environment-switching mechanism (ARC-CONFIG owns config layering).

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | workflows grep: no `aws-secret-access-key` / `AWS_SECRET_ACCESS_KEY` | exit 0 | INF-ENVS-03 |
| 2 | workflows grep: every `configure-aws-credentials` has `role-to-assume` | exit 0 | INF-ENVS-03 |
| 3-8 | attestation checklist (one per rule; tier-scoped as listed) | explicit yes recorded | INF-ENVS-01, -02, -04, -05, -06, -07 |

**Remediation:** static AWS keys in workflows → stand up the OIDC provider + role
(worked example below), switch the workflow to `role-to-assume`, then **delete and
revoke the IAM user keys** (rotation, not removal — SEC-SECRETS-05) ·
`configure-aws-credentials` without `role-to-assume` → same fix · prod hotfixed
sideways → port the change back through dev/staging now, note it as a deviation (C9).

## Worked Example

GitHub OIDC federation, the -03 mechanism end to end. Tofu (in `envs/prod/`):

```hcl
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_policy_document" "gha_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      # Pin repo AND the protected environment — never repo:owner/* (INF-ENVS-03)
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:jafinch/myproj:environment:prod"]
    }
  }
}

resource "aws_iam_role" "deploy_prod" {
  name                 = "myproj-prod-deploy"
  assume_role_policy   = data.aws_iam_policy_document.gha_trust.json
  max_session_duration = 3600
  # attach a policy scoped to prod ARNs only (INF-ENVS-04)
}
```

Workflow (`.github/workflows/deploy.yml`), promoting the staging-tested image by digest
(INF-ENVS-02):

```yaml
permissions:
  id-token: write   # mint the OIDC token
  contents: read
jobs:
  deploy-prod:
    environment: prod   # matches the sub claim pinned above
    runs-on: ubuntu-latest
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/myproj-prod-deploy
          aws-region: us-east-1
      - run: ./scripts/promote.sh "$IMAGE_DIGEST"   # retag staging's digest for prod
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `AWS_SECRET_ACCESS_KEY` in GitHub secrets | Standing credential; leaks via logs/forks; never expires | OIDC role federation (-03) |
| Trust policy `sub` of `repo:owner/*` | Any repo you own — or fork with actions — can assume prod | Pin repo + environment (-03) |
| Rebuilding the image for prod "from the same tag" | Moved tags/deps ⇒ prod runs untested bytes | Promote the digest staging ran (-02) |
| One `deploy-role` shared by all envs | Staging compromise = prod compromise | Per-env scoped roles (-04) |
| Hotfix applied straight to prod | Next promotion silently reverts it | Fix flows dev→staging→prod (-05) |
| Staging missing "expensive" components | The untested component is where prod breaks | Prod-shaped, smaller (-06) |
| `if ENV == "prod":` behavior branches | Prod-only code paths staging never executes | Same code, per-env config data (-07) |
| Third "hotfix" environment nothing uses | Idle spend + a promotion path nobody trusts | Ladder-sized env set (-01) |

## References

- GitHub Docs, "Configuring OpenID Connect in Amazon Web Services" — the -03 mechanism
  and `sub` claim formats.
- aws-actions/configure-aws-credentials README — `role-to-assume` usage the G check
  greps for.
- AWS Organizations docs — free account-level isolation behind the T4 rung of -01.
- 12-Factor App, factors I/V/X — build-release-run separation and dev/prod parity
  underlying -02 and -06.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
