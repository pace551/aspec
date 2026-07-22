---
id: OPS-ALERTS
title: Monitoring & Alerting
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
  - alert
  - alarm
  - monitoring
  - uptime
  - healthcheck
  - health check
  - sns
  - launchd
  - cron
  - scheduled job
  - silent failure
  - synthetics
  - on-call
requires: []
verification:
  - cmd: "attest: every configured alert fires on a user-facing symptom (availability, errors, latency, budget), not an internal cause"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-ALERTS-01]
    tiers: [T3, T4]
  - cmd: "attest: every alert has a documented first-response note (what to check first)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-ALERTS-02]
    tiers: [T3, T4]
  - cmd: "attest: no alert has fired weekly without action — noisy alerts were fixed or deleted"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-ALERTS-03]
    tiers: [T3, T4]
  - cmd: "attest: a healthcheck endpoint exists and an external uptime monitor plus CloudWatch alarm → SNS → email path is live"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-ALERTS-04]
    tiers: [T3, T4]
  - cmd: "attest: every scheduled job (launchd/cron/EventBridge) notifies on failure rather than dying silently"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [OPS-ALERTS-05]
    tiers: [T2, T3, T4]
last_review: 2026-07-22
---

# Monitoring & Alerting (OPS-ALERTS)

## Abstract

Solo-dev alerting: every alert is a page to James's phone or inbox, so the bar is high
and the set is small. Alert only on user-facing symptoms — availability, error rate,
latency SLO breach, budget — never on internal causes. Every alert is actionable and
carries a "check this first" note; anything that fires weekly without action gets fixed
or deleted. T3+ systems need a healthcheck endpoint, an external uptime monitor, and a
CloudWatch → SNS → email path. At every tier, scheduled jobs must announce their own
failure — the mortgage-scheduler silent-launchd-death lesson.

## Normative Rules

### OPS-ALERTS-01 — Alerts MUST fire on user-facing symptoms, not internal causes

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Alert-worthy: the service is down (uptime probe fails), error rate above threshold,
latency SLO breach (`OPS-PERF` budgets), and budget/spend alarms (`OPS-FINOPS`).
Not alert-worthy: CPU%, memory%, disk-nearly-full, queue depth, a single retry — these
are *causes*; if they matter, they surface as a symptom. Cause-level signals belong on a
dashboard consulted during diagnosis, not in the pager path. There is no on-call rota to
absorb noise: one person receives everything, so everything must deserve interruption.

### OPS-ALERTS-02 — Every alert MUST be actionable and documented

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

An alert exists only if there is an action James would take on receiving it. Each alert
definition carries (in the alarm description or a `RUNBOOK.md` entry) one or two lines
of "check first": the dashboard link, the log query, the likely culprits. Writing that
note at creation time is the test — if nothing concrete can be written, the alert is a
dashboard metric, not an alert.

### OPS-ALERTS-03 — Alerting MUST stay quiet by default; a noisy alert gets fixed or deleted

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

An alert that fires weekly (or more) without triggering action is a defect: either the
threshold is wrong (tune it), the underlying issue is real (fix it), or the signal is
worthless (delete it). Ignored alerts train the only responder to ignore all alerts —
alert fatigue at n=1 is total. Review the firing history as part of the `OPS-FINOPS`
monthly sweep.

### OPS-ALERTS-04 — T3+ services MUST have a healthcheck endpoint, an external uptime monitor, and an alarm→email path

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

`/health` returns 200 with `{status, version (git SHA — OPS-DEPLOY), checks}` and
exercises real dependencies shallowly (DB ping, not a full query). An *external* probe —
UptimeRobot free tier or CloudWatch Synthetics — hits it on schedule, because a service
cannot report its own network death. In-AWS signals route CloudWatch alarm → SNS topic →
email subscription (free, no PagerDuty at this scale). T4 adds a second channel
(SMS via SNS) for availability alarms.

### OPS-ALERTS-05 — Scheduled jobs MUST notify on failure, never die silently

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

The mortgage-scheduler lesson: a launchd job died for weeks and nothing said so. Every
launchd/cron/EventBridge job runs through a wrapper that (a) captures exit status,
(b) on failure sends a notification James actually sees (email or macOS notification),
and (c) logs the outcome either way (`OPS-OBS`). For jobs whose *absence* is the failure
mode, prefer a dead-man's switch (healthchecks.io free tier: job pings on success; the
service alerts on silence). Concurrency/overlap discipline for the jobs themselves is
`ARC-CONCURRENCY`.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1-4 | attestation checklist (T3+) | explicit yes recorded | OPS-ALERTS-01…04 |
| 5 | attestation — scheduled-job failure notification (T2+) | explicit yes recorded | OPS-ALERTS-05 |

**Remediation:** cause-based alarm (CPU etc.) → move to dashboard, alert on the symptom
it predicts · alert with no runbook note → write the two lines or delete the alert ·
weekly-firing alert → tune, fix, or delete this session · launchd job with no failure
path → wrap it (Worked Example) · no external probe → add UptimeRobot monitor (5 min).

## Worked Example

T1/T2 launchd wrapper (`run_wrapped.sh`) — the pattern that would have caught the
mortgage-scheduler death:

```bash
#!/usr/bin/env bash
set -uo pipefail
LOG_DIR="$HOME/Library/Logs/mytool"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/run-$(date +%F).log"

"$HOME/Dev/mytool/.venv/bin/python" -m mytool >>"$LOG" 2>&1
rc=$?
if [ $rc -ne 0 ]; then
  osascript -e 'display notification "mytool scheduled run FAILED — see logs" with title "launchd"'
  # dead-man's switch variant: only ping on success; silence itself alerts
else
  curl -fsS -m 10 "https://hc-ping.com/$HC_UUID" >/dev/null || true
fi
exit $rc
```

T3 CloudWatch alarm → SNS → email (Terraform):

```hcl
resource "aws_cloudwatch_metric_alarm" "error_rate" {
  alarm_name          = "mytool-5xx-rate"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 5
  comparison_operator = "GreaterThanThreshold"
  alarm_description   = "Check first: /mytool/prod logs, filter level=ERROR since alarm time"
  alarm_actions       = [aws_sns_topic.alerts.arn]   # topic has email subscription
}
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| CPU > 80% alarm on a T3 toy service | Cause, not symptom; fires on every deploy | Alarm on 5xx rate / probe failure (OPS-ALERTS-01) |
| Alert email filtered to a folder "to reduce noise" | The pager path now ends in a bin | Fix or delete the alert itself (OPS-ALERTS-03) |
| Service self-reports uptime from inside itself | Network/host death takes the reporter down too | External probe (OPS-ALERTS-04) |
| launchd `.plist` with no failure handling | Job dies silently for weeks (mortgage-scheduler) | Wrapper + notification or dead-man ping (OPS-ALERTS-05) |
| Cron job "alerts" by writing to a log nobody reads | A log line is not a notification | Push channel: email/notification (OPS-ALERTS-05) |
| Alerting on every WARN log line | Logs are diagnosis, alarms are symptoms | Alarm on user-facing metrics only (OPS-ALERTS-01) |

## References

- Google SRE Book, "Monitoring Distributed Systems" — symptom-vs-cause alerting and the
  page-worthiness bar OPS-ALERTS-01/02 adapt to n=1.
- Rob Ewaschuk, "My Philosophy on Alerting" — origin of "every page must be actionable".
- healthchecks.io / UptimeRobot docs — the free-tier dead-man's switch and external
  probe used at T1–T3.
- AWS CloudWatch Alarms + SNS docs — the zero-cost alarm→email path in OPS-ALERTS-04.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
