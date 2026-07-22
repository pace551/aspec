---
id: INF-SERVERLESS
title: Serverless (Lambda + API Gateway)
family: INF
version: 1.0.1
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: [serverless]
triggers:
  - lambda
  - serverless
  - api gateway
  - function
  - event-driven
  - cron job aws
  - eventbridge
  - sqs
  - webhook handler
  - cold start
requires: [INF-TF]
verification:
  - cmd: "sh -c '! git ls-files | grep -qE \"^(samconfig\\.toml|template\\.ya?ml|cdk\\.json|serverless\\.ya?ml)$\"'"
    expect: "exit 0 — no parallel SAM/CDK/Serverless-Framework stack alongside tofu"
    layer: G
    rules: [INF-SERVERLESS-02]
  - cmd: "sh -c 'f=$(git grep -l \"resource \\\"aws_lambda_function\\\"\" -- \"*.tf\" 2>/dev/null || true); [ -z \"$f\" ] || { ! echo \"$f\" | xargs grep -L \"memory_size\" | grep -q . && ! echo \"$f\" | xargs grep -L \"timeout\" | grep -q .; }'"
    expect: "exit 0 — every .tf file defining a Lambda sets memory_size and timeout"
    layer: G
    rules: [INF-SERVERLESS-04]
  - cmd: "sh -c '! git grep -q \"aws_lambda_provisioned_concurrency_config\" -- \"*.tf\"'"
    expect: "exit 0 — no provisioned concurrency; presence requires James's recorded consent (waiver)"
    layer: G
    rules: [INF-SERVERLESS-07]
  - cmd: "attest: each function does one job; any lambdalith is a framework adapter (e.g. FastAPI+Mangum), not an ad-hoc router"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-SERVERLESS-03]
    tiers: [T3, T4]
  - cmd: "attest: every async-invoked function has a DLQ or on_failure destination, and it is monitored"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-SERVERLESS-05]
  - cmd: "attest: handlers are idempotent — a duplicate delivery of the same event cannot double-apply an effect"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-SERVERLESS-06]
  - cmd: "attest: function config comes from SSM (runtime fetch or deploy-time injection); secrets are never plaintext lambda env values"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-SERVERLESS-08]
  - cmd: "attest: handlers emit structured JSON logs with the request/correlation id"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-SERVERLESS-09]
  - cmd: "attest: public endpoints use HTTP API (or a justified REST API) with throttling configured"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-SERVERLESS-10]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Serverless (Lambda + API Gateway) (INF-SERVERLESS)

## Abstract

Lambda is the house default for event-shaped and low-traffic HTTP work because
scale-to-zero is the FinOps posture that matches a solo dev's traffic. Compliance in
one breath: functions are declared in tofu (no second SAM/CDK stack), each does one
job, memory and timeout are chosen not defaulted, async paths have failure
destinations, handlers tolerate duplicate delivery, config comes from SSM, logs are
structured JSON, and public endpoints sit behind a throttled HTTP API. Provisioned
concurrency is a recurring cost and needs James's explicit consent. Architecture
defaults are advisory; the safety rules (failure destinations, idempotency, deliberate
limits) harden at T2+.

## Normative Rules

### INF-SERVERLESS-01 — Lambda SHOULD be the first choice for event-shaped and low-traffic HTTP workloads

**Tiers**: all advisory — **Layer**: A

Webhooks, queue/schedule consumers, S3-event processors, and APIs under sustained ~10
req/s default to Lambda: scale-to-zero means idle costs nothing, and there is no
instance to patch. Choose Fargate (INF-CONTAINERS) instead when work is long-running
(>10 min), needs steady warm throughput, or fights the 250 MB/10 GB packaging limits.
Advisory because it is an architecture default, not a safety property — but deviations
get a one-line reason in `GOVERNANCE.md`.

### INF-SERVERLESS-02 — Serverless resources MUST be deployed via OpenTofu, not a parallel SAM/CDK/Serverless-Framework stack

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

One IaC tool for everything (INF-TF): Lambda, API Gateway, queues, and the S3 bucket
next to them live in the same `envs/*` roots, state, and pipeline. Honest tradeoff:
SAM/CDK offer nicer function-local ergonomics (`sam local`, construct libraries) and
giving them up costs some polish — but two IaC stacks mean two state models, two
pipelines, and drift at every seam, which is a worse trade for one person. Local
iteration gap is covered by unit-testing handlers as plain functions (TST-POLICY) and
fast dev-env applies.

### INF-SERVERLESS-03 — One function, one purpose; no lambdalith at T3+ unless it is a framework adapter

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

A function maps to one event source and one job, so timeout/memory/IAM fit that job and
a poison event can't take down unrelated paths. Sanctioned exception: a small API
served as one FastAPI (+Mangum) or Hono function — a framework with real routing,
middleware, and local testability. What stays banned is the ad-hoc lambdalith: one
handler dispatching on `event["action"]` strings, which is a router without a framework.

### INF-SERVERLESS-04 — Timeout and memory MUST be set deliberately, never left at defaults

**Tiers**: all required — **Layer**: G

Every `aws_lambda_function` declares `timeout` and `memory_size` with a comment or
commit rationale. The 3 s default timeout kills real work; a reflexive 15 min timeout
turns a hung dependency into 15 minutes of billed hang × concurrency. Memory is the
CPU dial: 128 MB starves CPU-bound handlers, 1024 MB is the sane starting point for
anything doing real work, then tune on observed duration (billed ms often *drops* with
more memory).

### INF-SERVERLESS-05 — Async invocations MUST have a DLQ or failure destination

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Async (EventBridge, S3 events, SNS) retries twice, then discards the event silently —
that is data loss by default. Every async function gets an `on_failure` destination
(SQS queue preferred; carries richer context than a plain DLQ) with an alarm on queue
depth (OPS-ALERTS). SQS-sourced functions instead set a `redrive_policy` with a bounded
`maxReceiveCount`. Failure handling detail beyond infra wiring lives in ARC-ERRORS.

### INF-SERVERLESS-06 — Handlers MUST be idempotent: at-least-once delivery is the contract

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Every async source can and will deliver duplicates. Handlers key side effects on a
stable event/business id (conditional writes, upsert semantics, dedup table per
ARC-IDEMPOTENCY) so a retry is a no-op, not a double-charge or double-email. "It
hasn't duplicated yet" is not a design.

### INF-SERVERLESS-07 — Provisioned concurrency MUST NOT be enabled without James's recorded consent

**Tiers**: all required — **Layer**: G

Provisioned concurrency bills per hour whether or not requests arrive — it silently
converts scale-to-zero into an always-on cost (C6). Cold starts on small Python/Node
functions are typically well under a second; live with them until measured latency
says otherwise, then escalate with numbers (p95 cold-start, expected monthly cost).
The G check fails when the resource appears, forcing a consent-bearing waiver in
`GOVERNANCE.md`.

### INF-SERVERLESS-08 — Function config MUST come from SSM, secrets never as plaintext env values

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Non-secret config: SSM parameters injected at deploy time by tofu (`data
"aws_ssm_parameter"` → `environment`), or fetched at runtime for values that change
without redeploys. Secrets: runtime fetch of a SecureString via the function role (or
the Parameters/Secrets Lambda extension) — Lambda plaintext env vars are readable by
anyone with `lambda:GetFunctionConfiguration` (SEC-SECRETS-03). Cache fetched values
outside the handler for warm invocations.

### INF-SERVERLESS-09 — Handlers MUST emit structured JSON logs

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

One JSON object per line to stdout with at least `level`, `event`, and the
`aws_request_id` (OPS-OBS field set); powertools/pino or a 10-line wrapper both
qualify. Set the log group's retention explicitly — Lambda's auto-created groups
default to never-expire (OPS-FINOPS). CloudWatch Logs Insights over JSON is the whole
debugging story for Lambda; printf logs forfeit it.

### INF-SERVERLESS-10 — Public HTTP endpoints use HTTP API over REST API, with throttling configured

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

API Gateway HTTP API costs roughly a third of REST API per million requests and covers
JWT auth, CORS, and proxy routes — the common cases. REST API is justified only by a
needed feature (usage plans/API keys, request-body validation, WAF-on-stage, private
endpoints); record the reason. Either way, stage `throttling_burst_limit` /
`throttling_rate_limit` are set to realistic numbers so a scraper burns pennies, not
the C6 budget (SEC-WEB rate-limit posture).

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | no tracked `samconfig.toml` / `template.y(a)ml` / `cdk.json` / `serverless.y(a)ml` at root | exit 0 | INF-SERVERLESS-02 |
| 2 | every `.tf` defining `aws_lambda_function` sets `memory_size` + `timeout` | exit 0 | INF-SERVERLESS-04 |
| 3 | `aws_lambda_provisioned_concurrency_config` absent from `.tf` | exit 0 (presence ⇒ consent waiver) | INF-SERVERLESS-07 |
| 4-9 | attestation checklist (one per rule) | explicit yes recorded | INF-SERVERLESS-03, -05, -06, -08, -09, -10 |

**Remediation:** parallel SAM/CDK stack → port to the tofu roots (INF-TF), delete the
second stack; a root `template.yml` that is not SAM → rename it (or waive with reason)
· missing timeout/memory → set explicit values with a sizing comment · provisioned
concurrency check fails → either remove the resource or record James's consent as a
waiver with the monthly cost · no failure destination → add
`aws_lambda_function_event_invoke_config` with an SQS `on_failure` + depth alarm.

## Worked Example

Minimal compliant function in an INF-TF env root (`envs/prod/`):

```hcl
resource "aws_lambda_function" "ingest" {
  function_name = "${var.project}-prod-ingest"
  role          = aws_iam_role.ingest.arn # per-function least privilege (SEC-AUTHZ)
  runtime       = "python3.14"
  handler       = "ingest.handler"
  filename      = "${path.module}/../../build/ingest.zip"

  memory_size = 1024 # CPU scales with memory; tuned from observed p95 duration
  timeout     = 30   # webhook job finishes in ~2s; 30s bounds a hung dependency

  environment {
    variables = { ENV = "prod" } # non-secrets only (INF-SERVERLESS-08)
  }
}

resource "aws_lambda_function_event_invoke_config" "ingest" {
  function_name          = aws_lambda_function.ingest.function_name
  maximum_retry_attempts = 2
  destination_config {
    on_failure { destination = aws_sqs_queue.ingest_failures.arn } # INF-SERVERLESS-05
  }
}

resource "aws_apigatewayv2_stage" "api" {
  api_id      = aws_apigatewayv2_api.api.id # protocol_type = "HTTP" (INF-SERVERLESS-10)
  name        = "$default"
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit = 50
    throttling_rate_limit  = 25
  }
}
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| SAM for functions + tofu for "real infra" | Two states, two pipelines, drift at the seam | Everything in the tofu roots (-02) |
| `event["action"]` dispatch lambdalith | One timeout/IAM/poison-event blast radius for all jobs | One function per job, or a real framework adapter (-03) |
| Default 3 s timeout in prod | Kills legitimate slow calls, looks like flaky infra | Deliberate timeout with rationale (-04) |
| Reflexive 15 min timeout | Hung dependency bills 15 min × every retry | Bound to realistic worst case (-04) |
| Async function with no failure destination | Two retries, then silent event loss | SQS `on_failure` + depth alarm (-05) |
| "Runs once" assumption on S3/EventBridge events | At-least-once delivery double-applies effects | Idempotency keys (-06) |
| Provisioned concurrency "to fix cold starts" | Always-on hourly bill nobody approved | Measure first; escalate with numbers (-07) |
| Secrets in Lambda env vars | Readable via GetFunctionConfiguration | Runtime SSM fetch via role (-08) |
| REST API chosen by tutorial inertia | ~3× the per-request cost, unused features | HTTP API unless a feature forces REST (-10) |

## References

- AWS Lambda docs: async invocation & destinations — retry/discard behavior behind -05.
- AWS Lambda power tuning (aws-samples) — memory-as-CPU-dial evidence for -04.
- API Gateway pricing, HTTP vs REST — the ~3× delta behind -10.
- AWS Lambda Powertools (Python) — reference implementation for -09 structured logging
  and -06 idempotency utilities.

## Changelog

- **1.0.1** (2026-07-22) — Selection fix: `stacks` narrowed to this standard's own key so auxiliary keys (web/typescript/aws) don't cross-select it into unrelated projects (Phase-4 budget test finding).

- **1.0.0** (2026-07-22) — Initial version.
