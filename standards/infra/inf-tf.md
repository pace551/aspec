---
id: INF-TF
title: Terraform/OpenTofu on AWS
family: INF
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: [terraform, aws]
triggers:
  - terraform
  - opentofu
  - tofu
  - iac
  - infrastructure as code
  - provision
  - tfstate
  - hcl
  - tflint
  - checkov
  - aws resources
  - state bucket
requires: []
verification:
  - cmd: "bash ~/Dev/claude-code/governance/checks/inf-tf-scan.sh"
    expect: "exit 0 — fmt/validate clean; tflint+checkov clean when installed (warns when absent)"
    layer: G
    rules: [INF-TF-04]
  - cmd: "sh -c '! git ls-files | grep -qE \"\\.tfstate(\\.backup)?$\"'"
    expect: "exit 0 — no state file has ever been tracked"
    layer: G
    rules: [INF-TF-02]
  - cmd: "sh -c '! git ls-files \"*.tf\" | grep -q . || git ls-files | grep -q \"\\.terraform\\.lock\\.hcl$\"'"
    expect: "exit 0 — repos with .tf files commit a provider lockfile (tolerated absent before first init)"
    layer: G
    rules: [INF-TF-08]
  - cmd: "sh -c '! git ls-files \"*.tf\" | grep -q . || git grep -q \"backend \\\"s3\\\"\" -- \"*.tf\"'"
    expect: "exit 0 — a backend \"s3\" block exists somewhere in the tracked .tf files"
    layer: G
    rules: [INF-TF-03]
    tiers: [T3, T4]
  - cmd: "sh -c '! git ls-files \"*.tf\" | grep -q . || git grep -q \"default_tags\" -- \"*.tf\"'"
    expect: "exit 0 — provider blocks carry default_tags"
    layer: G
    rules: [INF-TF-06]
    tiers: [T2, T3, T4]
  - cmd: "attest: infra layout is one root module per environment (envs/dev, envs/prod) composing modules/, applied with tofu"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-TF-01]
  - cmd: "attest: every apply followed a read plan; prod applies at T4 ran from CI, never a laptop"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-TF-05]
  - cmd: "attest: no .tf or .tfvars file contains a secret value — secrets reach resources via SSM/Secrets Manager data sources"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-TF-07]
  - cmd: "attest: every stateful resource (data stores, state buckets, queues with unprocessed data) has prevent_destroy or deletion_protection"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-TF-09]
last_review: 2026-07-22
---

# Terraform/OpenTofu on AWS (INF-TF)

## Abstract

Every AWS resource James operates is declared in code and applied with OpenTofu — no
ClickOps beyond the two hand-made bootstrap objects (state bucket, budget alarm).
Compliance in one breath: `envs/dev` and `envs/prod` root modules compose shared
`modules/`, state lives in S3 with the native lockfile and never in git, providers are
pinned with a committed lockfile, every resource carries the Project/Env/ManagedBy tags,
secrets arrive via SSM data sources, and nothing is applied without a read plan. Tier
scaling: remote state and CI-driven applies harden at T3/T4; the git-hygiene rules
(state and secrets never tracked) bind at every tier.

## Normative Rules

### INF-TF-01 — AWS infrastructure MUST be declared as code with OpenTofu, one root module per environment

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

House tool is OpenTofu (`tofu` CLI) — open license (MPL-2.0), Terraform-compatible HCL;
plain `terraform` is an accepted stand-in on machines that only have it. Layout:
`envs/dev/` and `envs/prod/` are separate root modules with separate state, composing
shared `modules/`. Environment separation by directory, not `terraform workspace` —
workspaces share one backend config and make "which env am I in" a hidden mode.
Console-only changes are drift; the two sanctioned manual objects are the state bucket
and the OPS-FINOPS budget alarm, which must exist before the first apply (C6).

### INF-TF-02 — State files MUST NOT be committed to git, at any tier, ever

**Tiers**: all required — **Layer**: G (ls-files scan) + H (scaffold gitignore)

`terraform.tfstate` contains every attribute of every resource — including generated
passwords, connection strings, and key material — in plaintext. The scaffold gitignore
covers `*.tfstate*`; the G check fails if one was ever tracked. A committed state file
is a secret leak: rotate what it contained (SEC-SECRETS-05), don't just delete it.

### INF-TF-03 — Deployed environments MUST use remote state: S3 backend with the native lockfile

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G

Default backend: S3 with `encrypt = true` and `use_lockfile = true` (native S3 locking,
OpenTofu/Terraform ≥ 1.10 — no DynamoDB table to run or pay for). Fallback for older
CLIs: a DynamoDB lock table (`dynamodb_table`). One state key per environment
(`{project}/{env}/terraform.tfstate`), state bucket versioned. Local state is tolerable
only for T1/T2 experiments that nothing depends on — anything a running system depends
on gets remote state, because a laptop-only state file is a single point of total loss.

### INF-TF-04 — `tofu fmt`, `tofu validate`, tflint, and checkov MUST be green

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G (inf-tf-scan.sh locally, iac-scan.yml in CI)

`checks/inf-tf-scan.sh` runs all four, degrading with documented warnings where tools
are missing locally; CI (`templates/ci/_fragments/iac-scan.yml`) always has them and is
the strict gate. Checkov findings are fixed or skipped inline
(`#checkov:skip=CKV_AWS_x: reason`) — a skip without a reason is a finding.

### INF-TF-05 — Every apply MUST follow a read plan; T4 prod applies run from CI only

**Tiers**: all required — **Layer**: A (attestation)

`tofu plan` output is read before `tofu apply` — specifically the destroy/replace lines,
which is where data loss hides. At T3, laptop applies are allowed after plan review; at
T4, prod applies run only from the CI pipeline (OIDC role per INF-ENVS-03) with the plan
surfaced in the run log. `-auto-approve` is only ever paired with a previously saved and
reviewed plan file (`tofu apply plan.tfplan`), never with a fresh implicit plan.

### INF-TF-06 — Every resource MUST carry the mandatory tag set via provider `default_tags`

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

Minimum set: `Project`, `Env`, `ManagedBy = "tofu"`, declared once in the provider's
`default_tags` block (scaffold does this) so individual resources can't forget it.
These tags are how OPS-FINOPS cost allocation answers "what is this $9 line item" —
untagged spend is unattributable spend. Per-resource `tags` add to, never replace, the
defaults.

### INF-TF-07 — Secret values MUST NOT appear in `.tf` or `.tfvars` files

**Tiers**: all required — **Layer**: A (attestation)

Secrets reach resources by reference: `data "aws_ssm_parameter"` /
`data "aws_secretsmanager_secret_version"` lookups, or ARN pass-through into task-def
`secrets` blocks (values then never transit state). Non-example `*.tfvars` files are
gitignored by the scaffold because they attract secrets. The gitleaks-backed
SEC-SECRETS scans cover tracked `.tf` files mechanically; this attestation covers what
patterns can't catch. Mark secret-bearing variables `sensitive = true`, and remember
state can still contain resolved values — which is why INF-TF-02/-03 treat state itself
as a secret.

### INF-TF-08 — Provider versions MUST be pinned and `.terraform.lock.hcl` committed

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

`required_providers` uses pessimistic constraints (`~> 6.0`), `required_version` pins
the core floor, and the lockfile generated by `tofu init` is committed so every machine
and CI run resolves identical provider builds. An unpinned provider is an unreviewed
infra change on next init.

### INF-TF-09 — Stateful resources MUST have destroy protection

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Anything holding data that can't be regenerated — S3 buckets with content, RDS/DynamoDB,
the state bucket itself, queues with unprocessed messages — gets `lifecycle {
prevent_destroy = true }` and, where the service offers it, `deletion_protection = true`.
Destroying one becomes a deliberate two-step (remove the guard, plan, apply), never a
side effect of a refactor rename. Pair renames with `moved {}` blocks so the plan shows
a move, not a destroy/create.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `bash ~/Dev/claude-code/governance/checks/inf-tf-scan.sh` | exit 0 — fmt/validate/tflint/checkov clean (documented warnings when tools absent) | INF-TF-04 |
| 2 | `! git ls-files \| grep -qE "\.tfstate(\.backup)?$"` | no tracked state files | INF-TF-02 |
| 3 | tracked `.tf` files ⇒ tracked `.terraform.lock.hcl` | lockfile committed | INF-TF-08 |
| 4 | tracked `.tf` files ⇒ `backend "s3"` present (T3+) | remote state configured | INF-TF-03 |
| 5 | tracked `.tf` files ⇒ `default_tags` present (T2+) | mandatory tags wired | INF-TF-06 |
| 6-9 | attestation checklist (one per rule) | explicit yes recorded | INF-TF-01, -05, -07, -09 |

**Remediation:** fmt fail → `tofu fmt` the listed dirs · tracked tfstate → `git rm
--cached`, gitignore, rotate everything the state contained (SEC-SECRETS-05) · missing
lockfile → `tofu init -backend=false` in each env dir, commit the lockfile · no
`backend "s3"` at T3+ → copy `backend.tf.example` from the scaffold, create the state
bucket, `tofu init` (state auto-migrates with prompt) · missing `default_tags` → add to
the provider block in `versions.tf`, then `tofu apply` retags in place.

## Worked Example

`templates/scaffolds/terraform/` is the living example — `envs/{dev,prod}` roots with
pinned providers, `default_tags`, an S3-native-lockfile `backend.tf.example`, and a
`modules/s3-private-bucket` module demonstrating `prevent_destroy`. The one pattern not
in the scaffold, secret pass-through (INF-TF-07):

```hcl
# Reference, not value: the secret never appears in .tf files, and as an ARN
# pass-through it never transits state either.
data "aws_ssm_parameter" "api_key" {
  name = "/myproj/prod/anthropic-api-key"
}

# ECS task definition receives the ARN; ECS resolves the value at task start.
# container_definitions secrets block:
#   { "name": "ANTHROPIC_API_KEY", "valueFrom": data.aws_ssm_parameter.api_key.arn }
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Committing `terraform.tfstate` "so CI has it" | State is a plaintext secrets dump | S3 backend (INF-TF-03); rotate if it happened |
| `terraform workspace` for dev/prod | One backend, hidden mode switch, easy cross-env apply | Directory-per-env roots (INF-TF-01) |
| `apply -auto-approve` on a fresh plan | The destroy you didn't read is the data you lost | Read the plan; saved-plan applies only (INF-TF-05) |
| Fixing drift in the AWS console | Next apply reverts it or errors; code no longer truth | Change the .tf, apply; import if it must live |
| DynamoDB lock table by default in 2026 | Pays monthly for what S3 lockfile does free | `use_lockfile = true`; DynamoDB only for old CLIs |
| Secrets in `terraform.tfvars` | tfvars leak via git and shoulder-surfing | SSM data sources (INF-TF-07); tfvars gitignored |
| Unpinned `provider "aws"` | Next `init` silently jumps a major version | `~>` constraint + committed lockfile (INF-TF-08) |
| Refactor-renaming a stateful resource | Plan shows destroy/create; data gone | `moved {}` block + prevent_destroy (INF-TF-09) |

## References

- OpenTofu docs (opentofu.org) — house default; MPL-2.0 license is why it wins over
  BUSL-licensed Terraform for C6's free/open preference.
- OpenTofu/Terraform S3 backend docs, `use_lockfile` — native S3 locking (≥ 1.10) that
  retires the DynamoDB lock-table cost.
- tflint (github.com/terraform-linters/tflint) and checkov (checkov.io) — the two
  scanners INF-TF-04 and `iac-scan.yml` run.
- AWS "Best practices for tagging AWS resources" — basis for the INF-TF-06 tag set and
  cost-allocation activation.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
