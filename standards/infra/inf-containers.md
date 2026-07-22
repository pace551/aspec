---
id: INF-CONTAINERS
title: Containers & ECS
family: INF
version: 1.0.1
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: [containers]
triggers:
  - docker
  - dockerfile
  - container
  - image
  - ecs
  - fargate
  - ecr
  - task definition
  - docker compose
  - containerize
requires: []
verification:
  - cmd: "bash ~/Dev/claude-code/governance/checks/inf-container-scan.sh"
    expect: "exit 0 — hadolint + trivy config clean when installed; built-in pin/USER checks otherwise"
    layer: G
    rules: [INF-CONTAINERS-01, INF-CONTAINERS-02, INF-CONTAINERS-03, INF-CONTAINERS-05]
  - cmd: "sh -c 'f=$(git ls-files | grep -E \"(^|/)Dockerfile\" || true); [ -z \"$f\" ] || ! echo \"$f\" | xargs grep -Li \"^USER \" | grep -q .'"
    expect: "exit 0 — every tracked Dockerfile sets a USER"
    layer: G
    rules: [INF-CONTAINERS-02]
  - cmd: "sh -c '! git ls-files | grep -qE \"(^|/)Dockerfile\" || [ -f .dockerignore ]'"
    expect: "exit 0 — a project with a Dockerfile has a .dockerignore"
    layer: G
    rules: [INF-CONTAINERS-04]
  - cmd: "attest: every external base image in every FROM is pinned tag@sha256 digest"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-CONTAINERS-03]
    tiers: [T3, T4]
  - cmd: "attest: each container runs one process and defines a healthcheck (Dockerfile or task-def)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-CONTAINERS-06]
  - cmd: "attest: containers run on ECS Fargate with deliberately chosen cpu/memory, not EC2 container hosts"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-CONTAINERS-07]
    tiers: [T3, T4]
  - cmd: "attest: each service has its own task role scoped to exactly the AWS actions it uses"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-CONTAINERS-08]
    tiers: [T3, T4]
  - cmd: "attest: task-def secrets come via the secrets block from SSM — nothing sensitive in environment"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-CONTAINERS-09]
    tiers: [T3, T4]
  - cmd: "attest: container logs flow to CloudWatch via the awslogs driver with a set retention"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-CONTAINERS-10]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Containers & ECS (INF-CONTAINERS)

## Abstract

Container rules from `docker build` to running on ECS Fargate, the house runtime.
Compliance in one breath: multi-stage Dockerfiles whose runtime stage is a pinned slim
base plus artifacts, running one process as a non-root user with a healthcheck; a
`.dockerignore` that keeps secrets, git, and dependency dirs out of the build context;
images scanned (ECR scan-on-push or trivy); and task definitions that inject secrets
from SSM via the `secrets` block, log via `awslogs`, and carry deliberate cpu/memory
sizes under a per-service least-privilege task role. Build hygiene applies whenever a
Dockerfile exists; the ECS rules bind at T3+ where things actually deploy. Scaffold:
`templates/scaffolds/containers/`.

## Normative Rules

### INF-CONTAINERS-01 — Images MUST be built multi-stage: build tooling never ships in the runtime stage

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G (inf-container-scan.sh)

Stage one holds compilers, package managers, and source; the runtime stage is the slim
base plus copied artifacts (`/venv`, `dist/`). Smaller attack surface, smaller pull,
and no `pip`/`npm` in the running container for an attacker to use. The scaffold
Dockerfiles are the canonical shapes for python and node.

### INF-CONTAINERS-02 — Containers MUST NOT run as root: every Dockerfile sets a non-root `USER`

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

A dedicated uid (`useradd --uid 10001 app`, or the node image's built-in `node` user)
set before `CMD`. Root in the container is root against the kernel if anything escapes,
and it invites "fix it with chmod" images. Anything needing privileged setup does it in
earlier layers, then drops. Pair with `readonlyRootFilesystem: true` in the task def —
a process that can't write its own image is a much duller weapon.

### INF-CONTAINERS-03 — Base images MUST be version-pinned; at T3+ pinned by digest

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G (scan) + A (digest attestation)

`FROM python:3.14-slim` at minimum — never `:latest`, never untagged (the scan fails
both). At T3+ pin tag *plus* digest (`python:3.14-slim@sha256:…`) so builds are
byte-reproducible and a poisoned tag push upstream can't reach prod; the tag stays for
human readability. Digest bumps arrive as reviewed diffs (DEV-DEPS cadence).

### INF-CONTAINERS-04 — Every Dockerfile MUST have a `.dockerignore`; secrets, git, and dependency dirs never enter the context

**Tiers**: all required — **Layer**: G

Minimum exclusions: `.git`, `.env*`, key material globs, `.venv`/`node_modules`,
`__pycache__`/`dist` (scaffold `dockerignore` is the template). The build context is
copyable by any instruction and cached in layers — `COPY . .` with no ignore file has
shipped `.env` files to registries too many times (SEC-SECRETS-01 class). This binds at
every tier because `docker build` happens on laptops long before anything deploys.

### INF-CONTAINERS-05 — Images MUST be vulnerability-scanned before they run in a deployed environment

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G

House default: ECR `scan_on_push` (free, zero setup) on every repository, findings
triaged before first task launch. Locally and in CI, `checks/inf-container-scan.sh`
runs hadolint + `trivy config` when installed and degrades to built-in pin/USER checks
with a warning when not. Critical findings are fixed by base bump or waived per-CVE in
`GOVERNANCE.md` (same discipline as STK-PY-05).

### INF-CONTAINERS-06 — One process per container, with a defined healthcheck

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

The container runs the server — not the server plus nginx plus cron under supervisord.
Sidecar needs become separate containers in the same task. A healthcheck (Dockerfile
`HEALTHCHECK` locally, task-def `healthCheck` on ECS) hits a real endpoint (`/healthz`)
so orchestrators replace wedged tasks instead of routing to them; OPS-OBS consumes the
same endpoint.

### INF-CONTAINERS-07 — ECS Fargate MUST be the container runtime; no EC2 container hosts

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

A solo dev patching, right-sizing, and draining EC2 container instances is undiluted
toil with no upside at this scale. Fargate task sizes are chosen deliberately — start
at 0.25 vCPU/512 MB (ARM64/Graviton for the better price-performance) and resize on
observed usage; oversizing is a silent recurring cost (OPS-FINOPS). Scale-to-zero,
event-shaped work belongs on Lambda instead (INF-SERVERLESS-01). Deviating to EC2
hosts (GPU, special AMI) is a cost decision escalated to James (C6).

### INF-CONTAINERS-08 — Each service MUST have its own least-privilege task role

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

Task role (the app's AWS identity) is distinct from the execution role (ECS's
image-pull/log identity) and scoped to exactly the actions and resource ARNs the
service uses — no `*` actions, no shared "app-role" across services (SEC-AUTHZ).
One role per service keeps blast radius and revocation surgical.

### INF-CONTAINERS-09 — Task secrets MUST use the `secrets` block from SSM, never `environment`

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

`environment` values are plaintext to anyone with `ecs:DescribeTaskDefinition` and in
every console view; `secrets` holds only an SSM/Secrets Manager ARN that ECS resolves
at task start (SEC-SECRETS-03). `environment` is for genuinely non-sensitive config —
by convention little more than `ENV` (INF-ENVS-07). Never bake secrets into the image;
layers are effectively public.

### INF-CONTAINERS-10 — Container logs MUST flow to CloudWatch via the `awslogs` driver

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

App logs to stdout/stderr as structured JSON (OPS-OBS); the task def's
`logConfiguration` uses `awslogs` with group `/ecs/{project}-{env}` and an explicit
retention (never the default never-expire — log storage is a classic silent AWS cost).
No log files inside containers: they die with the task.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `bash ~/Dev/claude-code/governance/checks/inf-container-scan.sh` | exit 0 — scanners clean, or fallback checks pass with warning | INF-CONTAINERS-01, -02, -03, -05 |
| 2 | tracked Dockerfiles all contain `^USER ` | exit 0 | INF-CONTAINERS-02 |
| 3 | tracked Dockerfile ⇒ `.dockerignore` exists | exit 0 | INF-CONTAINERS-04 |
| 4-9 | attestation checklist (one per rule; ECS entries T3+) | explicit yes recorded | INF-CONTAINERS-03, -06, -07, -08, -09, -10 |

**Remediation:** no USER → add `USER app` after a `useradd` (copy the scaffold) ·
`:latest`/untagged FROM → pin the tag; at T3+ add `@sha256:` digest · no
`.dockerignore` → copy `templates/scaffolds/containers/dockerignore` · trivy/hadolint
findings → fix or annotate an inline ignore with a reason · secret in `environment` →
move value to SSM SecureString, reference its ARN from `secrets`, rotate the exposed
value (SEC-SECRETS-05).

## Worked Example

`templates/scaffolds/containers/` carries the canonical files: `Dockerfile.python` and
`Dockerfile.node` (multi-stage, non-root, healthcheck, pin comments),
`dockerignore`, and `ecs-task-def.snippet.json` — a Fargate task definition showing the
load-bearing distinction:

```json
"environment": [ { "name": "ENV", "value": "prod" } ],
"secrets": [ { "name": "ANTHROPIC_API_KEY",
               "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/myproj/prod/anthropic-api-key" } ]
```

plus `awslogs` logConfiguration, `readonlyRootFilesystem`, a `healthCheck`, and
0.25 vCPU/512 MB ARM64 sizing as the starting point.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Single-stage image with build tools in prod | Bloated, larger CVE surface, attacker gets pip/npm | Multi-stage (INF-CONTAINERS-01) |
| No `USER` ("it's just a container") | Container escape lands as root; bad habits calcify | Non-root uid in every Dockerfile (-02) |
| `FROM python:latest` | Unreproducible; upstream push changes prod under you | Tag pin; digest pin at T3+ (-03) |
| `COPY . .` without `.dockerignore` | `.env`, `.git`, keys shipped inside published layers | Scaffold dockerignore first (-04) |
| Secrets in task-def `environment` | Plaintext to any DescribeTaskDefinition caller | `secrets` block → SSM ARN (-09) |
| supervisord running app+worker+cron | Opaque restarts; one wedged process hides | One process per container; sidecars (-06) |
| Self-managed EC2 container hosts | Patch/drain/right-size toil for a solo dev | Fargate; escalate exceptions (-07) |
| One fat IAM role shared by all services | Any compromise is a full compromise | Per-service task role (-08) |
| Log-group retention left at "never expire" | CloudWatch storage grows as silent cost forever | Explicit retention (-10, OPS-FINOPS) |

## References

- Docker docs, multi-stage builds + Dockerfile best practices — basis for -01/-03/-06.
- hadolint (github.com/hadolint/hadolint) and trivy (aquasecurity/trivy) — the scanners
  `inf-container-scan.sh` runs; trivy `config` mode needs no image build.
- AWS ECS task definition `secrets` docs — the SSM-ARN injection mechanism -09 mandates.
- AWS Fargate pricing + Graviton price-performance notes — why -07 defaults ARM64 and
  small sizes.

## Changelog

- **1.0.1** (2026-07-22) — Selection fix: `stacks` narrowed to this standard's own key so auxiliary keys (web/typescript/aws) don't cross-select it into unrelated projects (Phase-4 budget test finding).

- **1.0.0** (2026-07-22) — Initial version.
