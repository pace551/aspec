---
id: UX-A11Y
title: Accessibility
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
  - accessibility
  - a11y
  - wcag
  - aria
  - screen reader
  - keyboard
  - focus
  - contrast
  - alt text
  - semantic html
  - form label
requires: []
verification:
  - cmd: "bash ~/Dev/claude-code/governance/checks/ux-a11y.sh"
    expect: "exit 0 — axe-core scan clean (degrades to documented warning if npx/driver or app missing)"
    layer: G
    rules: [UX-A11Y-01]
    tiers: [T3, T4]
  - cmd: "attest: interactive elements are native semantic HTML (button/a/nav/main/label), ARIA only where no native element exists"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-A11Y-02]
  - cmd: "attest: every action is keyboard-reachable with visible focus and no traps"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-A11Y-03]
  - cmd: "attest: text contrast is at least 4.5:1 (3:1 for large text and UI components)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-A11Y-04]
  - cmd: "attest: every input has a programmatic label and every informative image has alt text (decorative images alt=\"\")"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-A11Y-05]
  - cmd: "attest: non-essential animation is disabled or reduced under prefers-reduced-motion"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-A11Y-06]
last_review: 2026-07-22
---

# Accessibility (UX-A11Y)

## Abstract

Retires the failure mode where a product works only for a mouse-wielding, well-sighted user
in ideal light. The bar is WCAG 2.2 AA at T3+: semantic HTML first, everything operable by
keyboard with visible focus, 4.5:1 text contrast, labeled inputs, alt text, and motion that
respects `prefers-reduced-motion`. An axe-core scan (`checks/ux-a11y.sh`, wired into CI via
`templates/ci/_fragments/a11y.yml`) gates the automatable ~40%; the attestations cover what
only a human can judge. Advisory at T1/T2 — but semantic HTML costs nothing, so write it
that way from the first div.

## Normative Rules

### UX-A11Y-01 — Web UI at T3+ MUST pass an axe-core automated scan with zero violations

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: G

`checks/ux-a11y.sh [URL]` (default `http://localhost:3000`) runs `@axe-core/cli` against
the running app; CI uses the `templates/ci/_fragments/a11y.yml` fragment, which boots the
app before scanning. Axe automates roughly the mechanical 40% of WCAG 2.2 AA — contrast,
missing labels/alt, ARIA misuse, landmark structure; a clean scan is necessary, not
sufficient (rules 02–06 cover the rest). Findings are fixed, not suppressed; a rule
exclusion requires a waiver in `GOVERNANCE.md` with reason and expiry (C9). The script
degrades with a printed warning when npx/driver is unavailable — a degraded run falls back
to manual verification plus attestation, never a silent pass.

### UX-A11Y-02 — Semantic HTML MUST be used before ARIA; div-soup is prohibited

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Buttons are `<button>`, links are `<a href>`, navigation is `<nav>`, page regions are
`<main>/<header>/<footer>`, lists are `<ul>/<ol>`, and form fields are real form elements.
A `<div onClick>` reimplements — badly — the focus, keyboard, and screen-reader behavior
the native element ships for free; this is the canonical anti-pattern of the family. ARIA
is for widgets with no native equivalent (tabs, comboboxes), and the first rule of ARIA
applies: prefer the native element. SwiftUI analogue: use native controls and
`.accessibilityLabel` — VoiceOver semantics come from the control, same principle.

### UX-A11Y-03 — Every action MUST be keyboard-operable, with visible focus and no traps

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Tab reaches everything interactive in a sensible order; Enter/Space activate; Escape closes
modals and menus; focus never gets trapped (except intentionally inside an open modal,
which returns focus on close). Focus is always visible — never `outline: none` without an
equal-or-better `:focus-visible` replacement. The five-minute test: unplug the mouse and
complete the app's core flow end to end.

### UX-A11Y-04 — Text contrast MUST be ≥4.5:1; large text and UI components ≥3:1

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Applies to text over any background it can appear on, in both light and dark themes
(UX-DESIGN owns the theming mechanics; contrast must hold in each). Large text (≥24px, or
≥18.7px bold) and meaningful UI components/graphics may drop to 3:1. Axe (UX-A11Y-01)
catches computed-style violations; gradients, images-behind-text, and hover states need the
eyeball plus a contrast picker. Placeholder-gray-on-white is the classic offender.

### UX-A11Y-05 — Every input MUST have a programmatic label; every informative image MUST have alt text

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

`<label for>` or wrapping `<label>` for every field — placeholder text is not a label (it
vanishes on input and fails contrast). Icon-only buttons get `aria-label`. Informative
images get alt text describing their function, not their appearance ("Revenue chart:
March up 12%", not "chart"); decorative images get `alt=""` so screen readers skip them.
Error/status messages are announced (`role="alert"` or `aria-live="polite"`) — UX-FORMS
carries the placement rules.

### UX-A11Y-06 — Non-essential motion MUST be reduced when `prefers-reduced-motion` is set

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Decorative animation, parallax, auto-playing carousels, and large translate/scale
transitions are disabled or reduced to opacity fades under
`@media (prefers-reduced-motion: reduce)`. Essential motion (a progress spinner) may stay.
Cheapest implementation: define animations inside a
`@media (prefers-reduced-motion: no-preference)` block so reduction is the default.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `bash ~/Dev/claude-code/governance/checks/ux-a11y.sh` (T3+) | exit 0 — axe clean; skips with warning if app not running; degrades with warning if tooling missing | UX-A11Y-01 |
| 2–6 | attestation checklist (one entry per rule) | explicit yes recorded in GOVERNANCE.md | UX-A11Y-02…06 |

**Remediation:** axe `color-contrast` → fix the token in UX-DESIGN's palette, not the one
component · axe `label`/`button-name` → add `<label for>`/`aria-label` · axe
`region`/landmark findings → introduce `<main>/<nav>` structure · degraded script run →
`brew install node`, `npm i -D chromedriver`, or verify with the axe DevTools extension and
attest.

## Worked Example

```html
<!-- div-soup (violates 02, 03, 05) -->
<div class="btn" onclick="save()"><img src="disk.png"></div>

<!-- compliant -->
<button type="button" onclick="save()" aria-label="Save draft">
  <img src="disk.png" alt="" width="20" height="20" />
</button>
```

```css
:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
@media (prefers-reduced-motion: no-preference) {
  .card { transition: transform 150ms ease; }
}
```

Gate locally before pushing: `bash ~/Dev/claude-code/governance/checks/ux-a11y.sh
http://localhost:3000`.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `<div onClick>` as a button | No focus, no keyboard, invisible to screen readers | `<button>` (UX-A11Y-02) |
| `outline: none` "for aesthetics" | Keyboard users lose their place entirely | Styled `:focus-visible` (UX-A11Y-03) |
| Placeholder as the only label | Vanishes on input; fails contrast; unreadable to AT | `<label for>` + placeholder as example |
| `alt="image123.png"` or alt on decoration | Noise for screen readers either way | Function-describing alt, or `alt=""` |
| ARIA sprinkled to silence axe (`role="button"` on divs) | Announces behavior that doesn't exist | Native element first, ARIA last |
| Modal without focus trap/return | Tab escapes into the obscured page | Trap while open, restore on close |
| Fixing contrast per-component | Same failure reappears with every new component | Fix the design token (UX-DESIGN) |

## References

- WCAG 2.2 (W3C Recommendation) — the AA bar this standard names; SC 2.4.7 focus,
  1.4.3 contrast, 2.5.8 target size.
- axe-core rule descriptions (Deque) — what the automated gate does and does not cover;
  source of the "~40% automatable" honesty.
- MDN "ARIA: first rule of ARIA" — the native-element-first rationale for UX-A11Y-02.
- web.dev "prefers-reduced-motion" — implementation pattern for UX-A11Y-06.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
