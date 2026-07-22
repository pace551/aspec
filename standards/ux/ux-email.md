---
id: UX-EMAIL
title: Transactional Email & Notifications
family: UX
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: all
triggers:
  - email
  - transactional email
  - notification
  - ses
  - smtp
  - dkim
  - spf
  - dmarc
  - unsubscribe
  - email template
  - mailer
  - alert
requires: []
verification:
  - cmd: "attest: outbound email goes through SES (or a deliberately chosen, recorded alternative)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-EMAIL-01]
  - cmd: "attest: the sending domain has SPF, DKIM, and DMARC records at the tier's policy level"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-EMAIL-02]
    tiers: [T3, T4]
  - cmd: "attest: automated mail is transactional only; anything marketing-ish has explicit opt-in"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-EMAIL-03]
    tiers: [T3, T4]
  - cmd: "attest: every automated email has a plain-text part, a working unsubscribe/mute for non-critical mail, and a monitored reply-to"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-EMAIL-04]
    tiers: [T3, T4]
  - cmd: "attest: email templates are versioned in-repo, not edited live in a console"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-EMAIL-05]
  - cmd: "attest: send failures are logged and retried idempotently — no double-sends possible"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-EMAIL-06]
  - cmd: "attest: dev/staging cannot email real users — dry-run or a capture sandbox is the default"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-EMAIL-07]
last_review: 2026-07-22
---

# Transactional Email & Notifications (UX-EMAIL)

## Abstract

Email is the one UI that renders in someone else's inbox and the easiest external side
effect to fire by accident. Compliance in one breath: SES as the house sender; the domain
authenticated with SPF + DKIM + DMARC; transactional-only unless someone explicitly opted
into more; every automated mail carries a plain-text part, a working unsubscribe for
non-critical sends, and a monitored reply-to; templates live in the repo; failures log and
retry idempotently; and dev/staging can never email a real user. James-only notification
mail at T1/T2 skips the ceremony — but not C7's first-send approval, and never the
no-real-users rule.

## Normative Rules

### UX-EMAIL-01 — Outbound email SHOULD go through AWS SES

**Tiers**: all advisory — **Layer**: A (attestation)

SES is the house default: pennies per thousand, IAM-scoped credentials (`SEC-SECRETS`),
CloudWatch metrics, and configuration-set event destinations for bounce/complaint tracking
— all inside the existing AWS account (C6: no new SaaS spend). Start in sandbox mode
(verified recipients only — a free safety rail for T1/T2); request production access only
when a real product needs it. A different provider is fine as a deliberate, recorded choice
— what is not sanctioned is ad-hoc SMTP through a personal Gmail from application code.

### UX-EMAIL-02 — The sending domain MUST have SPF, DKIM, and DMARC; p=none monitoring at T3, p=quarantine or stricter at T4

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

All three DNS records exist before the first production send: SPF including SES
(`include:amazonses.com`), DKIM via SES Easy DKIM (three CNAMEs), and a DMARC record. T3
runs `p=none` with `rua=` reports to a monitored address — visibility into spoofing and
alignment failures without breakage risk. T4 moves to `p=quarantine` or `p=reject` once
reports show clean alignment; mailbox providers now require DMARC from bulk senders, and a
commercial domain that can be spoofed is a liability (`LEG-COMMERCIAL`). Check:
`dig +short TXT _dmarc.<domain>`.

### UX-EMAIL-03 — Automated email MUST be transactional only, unless the recipient explicitly opted into more

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Transactional = triggered by the recipient's own action or account state (receipt, reset,
alert they configured). Anything marketing-ish — newsletters, announcements, "we miss you",
tips — requires explicit opt-in (unchecked-by-default box, or better double opt-in),
recorded with a timestamp. A transactional footer never smuggles promotion, and a
transactional list is never repurposed for campaigns: that converts CAN-SPAM/GDPR
compliance questions from trivial to real (`LEG-COMMERCIAL`) and burns the domain
reputation UX-EMAIL-02 protects.

### UX-EMAIL-04 — Every automated email MUST have a plain-text part, a working unsubscribe/mute for non-critical mail, and a monitored reply-to

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

`multipart/alternative` with a real plain-text part (not an empty stub) — spam filters
score its absence and some clients prefer it. Non-critical mail (digests, activity
notifications) carries a working one-click unsubscribe or per-category mute, honored
immediately, plus `List-Unsubscribe`/`List-Unsubscribe-Post` headers; security-critical
mail (resets, receipts, breach notices) is exempt. `Reply-To` reaches a mailbox somebody
reads — `noreply@` is telling users their response is unwelcome while support requests
bounce into the void. **James-only exemption**: T1/T2 automation that mails only James
(cron reports, alerts to breathemoto@gmail.com) skips this rule's ceremony entirely — but
not C7's one-time first-send approval, and never UX-EMAIL-07.

### UX-EMAIL-05 — Email templates MUST be versioned in-repo

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Templates (HTML + text parts) live in the repository and go through the same review/test
loop as code — never edited live in the SES console or a provider dashboard, which is
untracked production mutation invisible to git history (C4). Template rendering is
unit-testable: given fixture data, snapshot both parts; broken merge fields
(`Hello {first_name},` sent literally) are the canonical embarrassment this catches.
Which template version a send used is resolvable from logs (UX-EMAIL-06).

### UX-EMAIL-06 — Send failures MUST be logged and retried idempotently — double-sends are prohibited

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Every send attempt logs message id, template + version, recipient, and outcome
(`OPS-OBS`). Transient failures (throttling, 5xx) retry with backoff, but each logical
message carries an idempotency key (e.g. `order-1234-receipt`) checked before dispatch —
"the SES call timed out so we sent it again, twice" is this rule's canonical bug, and email
cannot be unsent. Mechanics live in `ARC-IDEMPOTENCY`. Bounces and complaints feed back:
hard-bounced and complaining addresses are suppressed from future non-critical sends
(SES account-level suppression at minimum).

### UX-EMAIL-07 — Dev and staging MUST NOT email real users; dry-run or a capture sandbox is the default

**Tiers**: all required — **Layer**: A (attestation)

Non-production environments either dry-run (log the fully rendered message, send nothing)
or deliver to a capture sandbox (Mailtrap, MailHog, SES sandbox with only test addresses
verified) — enforced structurally: production credentials and verified prod identities are
absent from dev/staging config (`INF-ENVS`, `SEC-SECRETS`), not guarded by an `if (env)`
someone can forget. This is Constitution C7 applied to email — sending is an external side
effect gated on explicit human approval, and dry-run is the default until that approval is
recorded in `GOVERNANCE.md`. Required at every tier: "test" scripts emailing real people
is the classic own-goal, and seeding a test loop with real addresses at T1 is how it
happens.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1–7 | attestation checklist (one entry per rule; 02–04 at T3+) | explicit yes recorded in GOVERNANCE.md | UX-EMAIL-01…07 |

Attestation aids: `dig +short TXT <domain>` (SPF), `dig +short TXT _dmarc.<domain>`
(DMARC policy level), `aws sesv2 get-email-identity --email-identity <domain>` (DKIM
status) · grep non-prod config for production sender identities — should be empty.

**Remediation:** no DMARC → publish `v=DMARC1; p=none; rua=mailto:…` today, tighten at T4
after clean reports · double-sends observed → add the idempotency-key check before the SES
call (`ARC-IDEMPOTENCY`) · console-edited template → copy back into the repo, redeploy
from source, treat the console as read-only · staging emailed a user → incident, not
oops: rotate to sandbox creds and record in `GOVERNANCE.md` (C9).

## Worked Example

```python
# send.py — idempotent transactional send (T3 product, SES)
import boto3, structlog

log = structlog.get_logger()
ses = boto3.client("sesv2")

def send_receipt(order):
    key = f"order-{order.id}-receipt"          # logical message identity
    if sends_table.seen(key):                  # UX-EMAIL-06: no double-sends
        log.info("email.skip_duplicate", key=key)
        return
    html, text = render("receipt", order=order)  # templates/ in-repo (UX-EMAIL-05)
    resp = ses.send_email(
        FromEmailAddress="Acme <receipts@acme.dev>",   # DKIM-aligned domain (02)
        ReplyToAddresses=["support@acme.dev"],         # monitored (04)
        Destination={"ToAddresses": [order.email]},
        Content={"Simple": {
            "Subject": {"Data": f"Receipt for order {order.id}"},
            "Body": {"Html": {"Data": html}, "Text": {"Data": text}},  # both parts (04)
        }},
    )
    sends_table.record(key, resp["MessageId"], template="receipt@1.3.0")
```

Dev config: `EMAIL_MODE=dry-run` renders and logs both parts; no SES credentials exist in
that environment (UX-EMAIL-07). A T1 cron report to James: SES sandbox, own address
verified, one-line C7 approval in `GOVERNANCE.md` — nothing more.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Sending before SPF/DKIM/DMARC exist | Spam-foldered; domain spoofable; Gmail/Yahoo reject bulk | DNS first, then first send (UX-EMAIL-02) |
| Marketing blast to the transactional list | No consent; legal exposure; reputation burn | Explicit opt-in list only (UX-EMAIL-03) |
| `noreply@` with unmonitored inbox | Replies (and problems) vanish; trust erodes | Monitored reply-to (UX-EMAIL-04) |
| HTML-only messages | Spam-scored; broken in text-preferring clients | `multipart/alternative` (UX-EMAIL-04) |
| Editing templates in the SES/provider console | Untracked prod mutation; git lies about reality | In-repo templates, deploy from source (UX-EMAIL-05) |
| Retry loop without idempotency key | Timeout ≠ failure → duplicate sends, unrecallable | Key checked before dispatch (UX-EMAIL-06) |
| Real user emails seeded in staging fixtures | One test run emails strangers | Sandbox/dry-run; prod identities absent (UX-EMAIL-07) |
| Ignoring bounces/complaints | SES reputation sinks; account paused | Suppression list fed by SES events (UX-EMAIL-06) |

## References

- AWS SES docs: Easy DKIM, configuration sets, account-level suppression, sandbox — the
  mechanics behind rules 01, 02, 06, 07.
- Google & Yahoo bulk-sender requirements (2024–) — DMARC + one-click unsubscribe are now
  delivery requirements, not niceties (rules 02, 04).
- RFC 8058 (`List-Unsubscribe-Post`) — the one-click unsubscribe header pair UX-EMAIL-04
  names.
- FTC CAN-SPAM compliance guide — the transactional/commercial line and unsubscribe
  obligations behind UX-EMAIL-03 (`LEG-COMMERCIAL` carries the legal detail).

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
