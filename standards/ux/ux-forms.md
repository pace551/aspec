---
id: UX-FORMS
title: Forms, Validation & Feedback States
family: UX
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: [web]
triggers:
  - form
  - validation
  - submit
  - loading state
  - empty state
  - error state
  - spinner
  - skeleton
  - feedback
  - toast
  - optimistic ui
  - double submit
requires: []
verification:
  - cmd: "attest: every async surface has designed loading, empty, and error states (the three-state rule)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-FORMS-01]
  - cmd: "attest: validation fires on blur/submit with errors adjacent to their fields, never on first keystroke"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-FORMS-02]
  - cmd: "attest: submit controls are disabled while a submission is in flight"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-FORMS-03]
  - cmd: "attest: user-entered values are preserved when a submission fails"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-FORMS-04]
  - cmd: "attest: optimistic UI updates roll back visibly on failure"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-FORMS-05]
  - cmd: "attest: every user action produces perceivable feedback within ~100ms"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-FORMS-06]
last_review: 2026-07-22
---

# Forms, Validation & Feedback States (UX-FORMS)

## Abstract

The load-bearing UX standard: most perceived quality lives in how an app behaves while
waiting, when there's nothing to show, and when things fail. Compliance in one breath:
every async surface ships all three of loading/empty/error by design (the three-state
rule); validation fires on blur/submit with errors next to their fields; submit is disabled
while in flight; a failed form never loses the user's input; optimistic updates roll back;
and every action acknowledges within ~100ms. Advisory at T1/T2, MUST at T3+ — these are
exactly the seams strangers hit first.

## Normative Rules

### UX-FORMS-01 — Every async surface MUST have designed loading, empty, and error states

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

The three-state rule. Anything that fetches or submits ships all three, designed — not
whatever the framework happens to render:

- **Loading**: skeleton (preferred for content) or spinner (for actions), with the
  triggering control disabled (UX-FORMS-03). No layoutless flash, no frozen UI.
- **Empty**: "no items yet" plus what to do about it (a CTA or one-line explanation).
  A blank region is indistinguishable from a bug — to the user *and* to future James.
- **Error**: what happened and how to recover (retry, edit input, contact route). Never a
  raw exception, stack trace, or bare status code — `ARC-ERRORS` owns the mapping from
  internal errors to safe user-facing messages; this rule owns that a designed surface for
  them exists. Announce errors to assistive tech (`role="alert"`, per UX-A11Y-05).

The success state makes four; it's the only one that designs itself. SwiftUI analogue:
model the trio explicitly (an enum of `loading/empty/error/loaded`), render all cases.

### UX-FORMS-02 — Validation MUST fire on blur or submit — never on first keystroke — with errors adjacent to their fields

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Yelling "invalid email" at the second character punishes the user for typing. Validate a
field when it loses focus or on submit; once a field has erred, it MAY re-validate per
keystroke so the error clears the moment it's fixed (late validation, eager
re-validation). The message renders adjacent to the field it concerns — not only in a
toast or summary at the top — states the constraint concretely ("must include a decimal
point", not "invalid input"), and is programmatically associated
(`aria-describedby` + `aria-invalid`). Server-side validation remains authoritative
(client checks are UX, not security — `SEC` families own that boundary); server rejections
render through the same per-field surface.

### UX-FORMS-03 — Submit MUST be disabled while a submission is in flight

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Double-submit is the canonical bug of this standard: a slow response, an impatient second
click, two orders/emails/records. Disable the control on dispatch, show in-flight state on
the button itself ("Saving…"), re-enable on settle. Client-side disabling is the UX half —
the server MUST still be idempotent against retries and races (`ARC-IDEMPOTENCY`,
idempotency keys); the two halves back each other, neither substitutes for the other.
Also intercept duplicate Enter-key submits and route-away-and-back resubmission.

### UX-FORMS-04 — A failed submission MUST preserve the user's entered values

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Never clear a failed form. The user's input survives validation failures, server errors,
and full page redisplays (server-rendered flows re-populate from the submitted values —
minus passwords/card numbers, which are legitimately dropped). Wiping ten fields over one
bad one converts a recoverable error into abandonment. For long forms, drafts SHOULD
survive accidental navigation (local persistence or a leave-confirmation).

### UX-FORMS-05 — Optimistic UI MAY be used only with visible rollback on failure

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Updating the UI before the server confirms is sanctioned for low-stakes, high-frequency,
likely-to-succeed actions (toggles, likes, reorderings). The contract: on failure the
change visibly reverts *and* the user is told why — silent rollback makes the app look
haunted, no rollback makes it a liar. Never optimistic for payments, deletions, sends, or
anything crossing C7's external-side-effect line: those wait for confirmation
(UX-FORMS-03's in-flight state covers the gap).

### UX-FORMS-06 — Every user action MUST produce perceivable feedback within ~100ms

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

100ms is the perceived-instant threshold: within it, acknowledge — pressed state, disabled
control, spinner, skeleton, optimistic update. The acknowledgment must be perceived, not
merely dispatched. Beyond ~1s of actual work, show determinate progress or a staged
message. Success confirmation is explicit (inline state change or toast) but never
interrupts flow with a dismissal-requiring dialog for routine saves. Backend latency
budgets live in `OPS-PERF`; this rule is about never leaving a click unacknowledged,
however fast the server.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1–6 | attestation checklist (one entry per rule) | explicit yes recorded in GOVERNANCE.md | UX-FORMS-01…06 |

Attestation walkthrough for UX-FORMS-01: for each async surface, force all three states —
throttle the network (loading), point at an empty dataset (empty), kill the API (error) —
and confirm each renders its designed state. DevTools network throttling + an
unreachable-API env var make this a five-minute pass.

**Remediation:** missing empty state → add a "no items yet" component with the next-step
CTA · raw exception on screen → route through the `ARC-ERRORS` user-message mapping ·
double-submit found → disable-on-dispatch client-side and idempotency key server-side ·
form clears on error → re-render with submitted values bound.

## Worked Example

```tsx
function InviteForm() {
  const [status, setStatus] = useState<"idle" | "submitting" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");           // survives failure (04)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("submitting");                        // instant feedback (06)
    try {
      await api.invite({ email }, { idempotencyKey: formId }); // ARC-IDEMPOTENCY
      setStatus("idle"); toast("Invite sent");      // explicit success (06)
    } catch (err) {
      setError(userMessageFor(err));                // ARC-ERRORS mapping, not err.message
      setStatus("error");                           // email state untouched (04)
    }
  }

  return (
    <form onSubmit={onSubmit}>
      <label htmlFor="email">Email</label>
      <input id="email" value={email} onChange={(e) => setEmail(e.target.value)}
             onBlur={validateEmail} aria-invalid={!!error} aria-describedby="email-err" />
      {error && <p id="email-err" role="alert">{error}</p>}   {/* adjacent (02) */}
      <button disabled={status === "submitting"}>            {/* no double-submit (03) */}
        {status === "submitting" ? "Sending…" : "Send invite"}
      </button>
    </form>
  );
}
```

The list this form feeds renders `loading` (skeleton), `empty` ("No invites yet — send
your first above"), and `error` (retry button) as explicit branches.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Only the happy path designed | Blank/frozen/broken at exactly the moments trust is set | Three-state rule (UX-FORMS-01) |
| `err.message` rendered to the user | Leaks internals; unactionable; sometimes sensitive | `ARC-ERRORS` user-message mapping |
| Validating on first keystroke | Errors before the user could possibly be done | Blur/submit; eager re-validation after (UX-FORMS-02) |
| Toast-only errors for field problems | User can't find which field; toast expires | Adjacent inline errors (UX-FORMS-02) |
| Clickable submit during in-flight request | Double orders/sends; the canonical bug | Disable + in-flight label (UX-FORMS-03) + `ARC-IDEMPOTENCY` |
| Clearing the form on failure | One bad field costs all ten; abandonment | Preserve values (UX-FORMS-04) |
| Optimistic delete with no rollback | UI lies; data reappears on refresh | Rollback + notice, or wait for confirm (UX-FORMS-05) |
| Empty region rendered as nothing | Indistinguishable from a bug | "No items yet" + CTA (UX-FORMS-01) |

## References

- Nielsen Norman Group, "Response Times: The 3 Important Limits" — source of the
  100ms/1s/10s thresholds behind UX-FORMS-06.
- NN/g "How to Report Errors in Forms" — inline-adjacent placement and constraint-stating
  wording (UX-FORMS-02).
- Stripe API idempotency-keys docs — the server-side half of the double-submit fix
  referenced by UX-FORMS-03 (detail in `ARC-IDEMPOTENCY`).
- WAI "Forms" tutorial (W3C) — `aria-describedby`/`aria-invalid`/`role="alert"` wiring
  used in the worked example.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
