---
id: UX-DESIGN
title: Design System
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
  - design system
  - design tokens
  - css variables
  - color palette
  - spacing
  - typography
  - dark mode
  - theme
  - icons
  - fonts
  - hover
  - styling
requires: []
verification:
  - cmd: "attest: color/spacing/type come from CSS custom-property tokens; no hardcoded hex scattered in components"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-DESIGN-01]
  - cmd: "attest: spacing values sit on the 4/8px scale"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-DESIGN-02]
  - cmd: "attest: dark mode honors prefers-color-scheme with a data-theme override that wins in both directions"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-DESIGN-03]
  - cmd: "attest: one icon set per project; system font stack unless a webfont was deliberately chosen"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-DESIGN-04]
  - cmd: "attest: hover/focus/active/disabled states are designed for interactive components, not browser defaults"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-DESIGN-05]
  - cmd: "attest: every chart/dashboard surface was built following the /dataviz skill"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-DESIGN-06]
last_review: 2026-07-22
---

# Design System (UX-DESIGN)

## Abstract

Retires visual entropy: the fifth slightly-different gray, the 13px-here-15px-there
spacing, the dark mode that half the components ignore. Compliance in one breath: every
color, spacing step, and type size is a CSS custom-property token defined once; spacing
sits on a 4/8px scale; dark mode works via `prefers-color-scheme` with a `data-theme`
override that wins both ways; one icon set; system fonts by default; interactive states
designed, not left to browser defaults. Data visualization is explicitly delegated to the
`/dataviz` skill. Advisory at T1/T2, required at T3+ where strangers judge the surface.

## Normative Rules

### UX-DESIGN-01 — Color, spacing, and type MUST be design tokens, not values scattered in components

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

CSS custom properties on `:root` (or the framework's token layer — Tailwind theme config
counts) are the single source: `--color-*`, `--space-*`, `--text-*`. Components reference
tokens; a raw hex/rgb in a component file is the violation. This is what makes theming,
dark mode (UX-DESIGN-03), and contrast fixes (UX-A11Y-04) one-line changes instead of
greps. Semantic names (`--color-surface`, `--color-danger`) over literal ones
(`--gray-100`), so meaning survives a palette swap. SwiftUI analogue: asset-catalog Colors
and shared constants, never inline `Color(red:green:blue:)` in views.

### UX-DESIGN-02 — Spacing SHOULD sit on a 4/8px scale

**Tiers**: all advisory — **Layer**: A (attestation)

Margins, padding, and gaps come from a fixed ladder (4, 8, 12, 16, 24, 32, 48, 64px —
expressed in rem in the tokens). Arbitrary values (`margin: 13px`) are how visual rhythm
dies one component at a time. One-off optical adjustments MAY deviate with a comment;
unexplained magic numbers may not.

### UX-DESIGN-03 — Dark mode at T3+ MUST honor `prefers-color-scheme` with a `data-theme` override, and both directions MUST win

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Default theme follows the OS via `@media (prefers-color-scheme: dark)`; an explicit user
toggle stamps `data-theme="dark"` or `"light"` on the root element and MUST override the
media query in **both** directions — light-OS user choosing dark, and dark-OS user choosing
light. The classic bug is implementing only the media query, so the toggle silently loses
for one half of users. Because tokens (UX-DESIGN-01) are the only color source, dark mode
is a token redefinition, not a component rewrite. Contrast (UX-A11Y-04) must hold in both
themes.

### UX-DESIGN-04 — One icon set per project; system font stack unless a webfont is a deliberate choice

**Tiers**: all advisory — **Layer**: A (attestation)

Pick one icon library (Lucide, Heroicons, SF Symbols for SwiftUI) and never mix — mixed
sets differ in stroke weight and optical size and read as sloppy instantly. Default
typography is the system stack (`font-family: system-ui, -apple-system, sans-serif`): zero
bytes, zero FOUT, native feel. A webfont is allowed as a deliberate brand decision — self-
hosted with `font-display: swap`, subsetted, budgeted under `OPS-PERF`.

### UX-DESIGN-05 — Interactive states MUST be designed, not defaulted

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Every interactive component defines hover, focus-visible, active, and disabled states
(plus loading where async — UX-FORMS owns that trio). Browser defaults across these are
inconsistent and often invisible; an unstyled disabled state that still looks clickable
generates dead clicks and support noise. Focus styling must satisfy UX-A11Y-03; disabled
styling must still pass contrast for its label where the control conveys information.

### UX-DESIGN-06 — Charts and dashboards MUST follow the `/dataviz` skill; this standard defers to it

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Data visualization is explicitly **delegated**: before writing any chart, graph, KPI tile,
or dashboard — in any library or medium — load and follow the existing `/dataviz` skill
(form heuristics, palette formula with validator, mark specs, interaction rules).
UX-DESIGN's tokens still supply the surrounding chrome (page background, headings,
spacing); the skill governs everything inside the plot area, including its own validated
palette. Required from T2 up because charts inform real decisions there; do not restate or
fork the skill's rules into project CSS.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1–6 | attestation checklist (one entry per rule) | explicit yes recorded in GOVERNANCE.md | UX-DESIGN-01…06 |

A quick self-audit before attesting UX-DESIGN-01:
`grep -rn --include='*.css' --include='*.tsx' -E '#[0-9a-fA-F]{3,8}\b' src/ | grep -v tokens`
should return (near-)nothing — hits are either token definitions or violations.

**Remediation:** scattered hex → hoist into `:root` tokens, replace usages with
`var(--…)` · toggle loses to OS theme → ensure `[data-theme]` selectors come after (or are
more specific than) the media-query block for both themes · mixed icons → pick the set with
majority usage, replace the rest in one commit.

## Worked Example

```css
:root {
  --color-bg: #ffffff;      --color-text: #1a1a1a;
  --color-accent: #2563eb;  --color-danger: #b91c1c;
  --space-1: 0.25rem; --space-2: 0.5rem; --space-3: 1rem; --space-4: 1.5rem;
  --text-body: 1rem; --text-lg: 1.25rem;
  color-scheme: light dark;
}
/* OS preference is the default… */
@media (prefers-color-scheme: dark) {
  :root { --color-bg: #111418; --color-text: #e6e6e6; --color-accent: #60a5fa; }
}
/* …explicit choice wins in BOTH directions */
:root[data-theme="light"] { --color-bg: #ffffff; --color-text: #1a1a1a; --color-accent: #2563eb; }
:root[data-theme="dark"]  { --color-bg: #111418; --color-text: #e6e6e6; --color-accent: #60a5fa; }

.button {
  background: var(--color-accent); padding: var(--space-2) var(--space-3);
}
.button:hover { filter: brightness(1.08); }
.button:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
.button:disabled { opacity: 0.5; cursor: not-allowed; }
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Hex values pasted per component | Palette drift; dark mode becomes a rewrite | Tokens on `:root` (UX-DESIGN-01) |
| Literal token names (`--blue-500`) as the component API | Renaming the palette touches every file | Semantic tokens (`--color-accent`) |
| Dark mode via media query only | User's explicit toggle loses on mismatched OS theme | `data-theme` override, both directions (UX-DESIGN-03) |
| `margin: 13px` eyeballed per screen | Rhythm decays; every screen subtly different | 4/8px ladder tokens (UX-DESIGN-02) |
| Two icon sets "temporarily" | Stroke/size mismatch reads as broken | One set, swept in one commit (UX-DESIGN-04) |
| Disabled button styled like enabled | Dead clicks, confused users | Designed disabled state (UX-DESIGN-05) |
| Hand-rolling chart colors in project CSS | Forks and drifts from the validated dataviz system | Follow `/dataviz` (UX-DESIGN-06) |

## References

- CSS Custom Properties (MDN) — the token mechanism; cascade behavior is what makes the
  `data-theme` override pattern work.
- web.dev "Building a color scheme" — the prefers-color-scheme + override pattern
  UX-DESIGN-03 encodes, including `color-scheme` for native form controls.
- Refactoring UI (Wathan/Schoger) — the 4/8px spacing-scale and designed-states rationale.
- `/dataviz` skill (house) — the delegated authority for all visualization decisions
  (UX-DESIGN-06); its `references/palette.md` carries the validated chart palette.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
