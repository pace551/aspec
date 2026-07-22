---
id: OPS-OBS
title: Observability
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
  - logging
  - logs
  - structured logs
  - observability
  - tracing
  - opentelemetry
  - cloudwatch
  - log retention
  - correlation id
  - request id
  - debug output
requires: []
verification:
  - cmd: "sh -c '! git ls-files | grep -qE \"\\.log$\"'"
    expect: "exit 0 — no tracked *.log files (git is not a log sink)"
    layer: G
    rules: [OPS-OBS-06]
  - cmd: "attest: no log line contains a secret, credential, token, or (at T4) unredacted PII"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-OBS-01]
  - cmd: "attest: service logs are structured JSON with a consistent field set"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-OBS-02]
    tiers: [T3, T4]
  - cmd: "attest: every log line carries timestamp, level, event, and the relevant context ids"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-OBS-03]
    tiers: [T3, T4]
  - cmd: "attest: logging sits at boundaries and failure paths, not sprinkled through every function"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-OBS-04]
  - cmd: "attest: request/correlation ids propagate end-to-end; request-shaped systems emit OTel traces"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-OBS-05]
    tiers: [T3, T4]
  - cmd: "attest: logs land in the designated sink with an explicit finite retention period"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-OBS-06]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Observability (OPS-OBS)

## Abstract

Makes production behavior diagnosable without a debugger and without leaking anything.
Compliance in one breath: logs never contain secrets or PII; T3+ services emit structured
JSON where every line has timestamp, level, event, and context ids; logging happens at
boundaries and failures, not per-function; correlation ids propagate and request-shaped
T3+ systems carry OpenTelemetry traces; CloudWatch is the AWS sink with finite retention.
T1/T2 discount: human-readable prints are fine, structure is advisory — but the
no-secrets rule has no discount at any tier.

## Normative Rules

### OPS-OBS-01 — Logs MUST NOT contain secrets, and at T4 MUST NOT contain unredacted PII

**Tiers**: all required — **Layer**: A (attestation)

Never log: `Authorization`, `Cookie`/`Set-Cookie`, `X-Api-Key` or any auth header, API
keys/tokens in any field, full environment dumps, or wholesale request bodies. Redact by
field name at the logger layer, not by hoping call sites behave. At T4, email addresses
and other person-identifiers are PII — log opaque user ids and keep the mapping in the
datastore (`DATA-PRIVACY`). This rule is the logging face of `SEC-SECRETS-04`; a secret
that reached a log is exposed and gets rotated per `SEC-SECRETS-05` / `OPS-INCIDENT`.

### OPS-OBS-02 — T3+ services MUST log structured JSON; T1/T2 MAY log human-readable text

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

One JSON object per line to stdout/stderr (12-factor: the process never manages log
files or rotation — the runtime does). Human-readable output is the right call for T1
scripts and T2 notebooks; the moment logs are consumed by machines (CloudWatch Insights
queries, alarms) they must be parseable without regex archaeology.

### OPS-OBS-03 — Every log line MUST carry timestamp, level, event name, and context ids

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Minimum field set: `ts` (ISO-8601 UTC), `level`, `event` (a stable snake_case name, not
prose), plus the ids that scope the work — `request_id`, `job_id`, `user_id` (opaque),
whatever identifies the unit. Free-text `message` is allowed as a supplementary field;
it is never the only content. Stable event names are what make
`event = "payment_failed"` queryable a year later.

### OPS-OBS-04 — Log at boundaries and failures, not every function

**Tiers**: all advisory — **Layer**: A (attestation)

Log where state crosses a boundary (request in/out, job start/end with outcome and
duration, external API calls, retries) and where things fail (every caught exception
with stack trace, exactly once — log-or-rethrow, never both at each level). Interior
function tracing is what debuggers and OTel spans are for; per-function `logger.debug`
noise buries the signal and bloats CloudWatch cost.

### OPS-OBS-05 — Correlation ids MUST propagate; request-shaped T3+ systems MUST emit OpenTelemetry traces

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Accept an inbound `X-Request-Id`/`traceparent` or generate one at the edge, attach it to
every log line for that unit of work, and forward it on outbound calls. Request-shaped
systems (HTTP APIs, queue consumers) instrument with OpenTelemetry SDK auto-instrumentation;
export to CloudWatch via the ADOT collector or X-Ray. Batch/cron jobs are exempt from
traces but still carry a `job_id` through their logs.

### OPS-OBS-06 — Logs MUST land in CloudWatch (AWS default) with explicit, finite retention

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G + A

On AWS, CloudWatch Logs is the sink (Lambda/ECS get it for free via stdout); set
`retention_in_days` explicitly on every log group — 30–90 days is the house default,
never the "Never expire" default and never zero. Retention obligations and deletion
duties live in `DATA-RETENTION`. Git is not a log sink: `*.log` files are never tracked
(that is infinite retention in the worst possible store — the G check enforces it).
T1 launchd jobs write to `~/Library/Logs/{tool}/` with a dated filename.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `! git ls-files \| grep -qE "\.log$"` | no tracked log files | OPS-OBS-06 |
| 2-7 | attestation checklist (one per rule; T3+ entries tier-scoped) | explicit yes recorded | OPS-OBS-01…06 |

**Remediation:** tracked `.log` → `git rm --cached`, add `*.log` to `.gitignore` · secret
found in a log → rotate first (`OPS-INCIDENT` playbook), then fix the logger ·
unparseable logs at T3 → wrap the stdlib logger with a JSON formatter (see Worked
Example) · log group with infinite retention → set `retention_in_days` in Terraform
(`INF-TF`).

## Worked Example

Structured JSON logging in stdlib Python, no dependency needed:

```python
import json, logging, sys, time, uuid

class JsonFormatter(logging.Formatter):
    REDACT = {"authorization", "cookie", "x-api-key", "api_key", "token", "password"}
    def format(self, record):
        base = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
                "level": record.levelname, "event": record.getMessage()}
        extra = {k: ("[REDACTED]" if k.lower() in self.REDACT else v)
                 for k, v in getattr(record, "ctx", {}).items()}
        return json.dumps(base | extra)

logger = logging.getLogger("mytool")
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.handlers[0].setFormatter(JsonFormatter())
logger.setLevel(logging.INFO)

request_id = str(uuid.uuid4())
logger.info("job_started", extra={"ctx": {"request_id": request_id, "job": "nightly-sync"}})
```

Terraform retention (the `INF-TF`-conformant sink):

```hcl
resource "aws_cloudwatch_log_group" "app" {
  name              = "/mytool/prod"
  retention_in_days = 30
}
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `logger.error(f"auth failed: {headers}")` | Dumps `Authorization`/`Cookie` into logs | Log event + request_id; redact headers (OPS-OBS-01) |
| `print(f"done {row}")` in a T3 service | Unqueryable; no level, ts, or ids | JSON formatter (OPS-OBS-02/03) |
| Log-and-rethrow at every stack level | Same error appears 5×; alarms overcount | Log once where handled (OPS-OBS-04) |
| `logger.debug` in every function "for visibility" | Noise buries failures; CloudWatch ingest bills grow | Boundaries + failures only (OPS-OBS-04) |
| New uuid per log line instead of per request | Lines can't be joined into one story | Generate once at the edge, propagate (OPS-OBS-05) |
| Log group left on "Never expire" | Unbounded cost + `DATA-RETENTION` violation | Explicit `retention_in_days` (OPS-OBS-06) |
| Committing `debug.log` to show a failure | Infinite retention in git; may embed secrets | Paste the relevant lines into the issue/PR |

## References

- 12-Factor App, factor XI "Logs" — logs as event streams to stdout; the runtime owns
  routing/rotation (basis of OPS-OBS-02/06).
- OpenTelemetry docs (traces + `traceparent` propagation) — the T3+ tracing contract in
  OPS-OBS-05.
- AWS CloudWatch Logs pricing/retention docs — why finite retention is both a cost and a
  compliance control.
- OWASP Logging Cheat Sheet — the redaction list rationale for OPS-OBS-01.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
