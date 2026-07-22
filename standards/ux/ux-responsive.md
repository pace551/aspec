---
id: UX-RESPONSIVE
title: Responsive Design
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
  - responsive
  - mobile
  - viewport
  - breakpoint
  - layout
  - media query
  - flexbox
  - grid
  - touch target
  - horizontal scroll
  - css
requires: []
verification:
  - cmd: "attest: layout verified at 375px, 768px, and 1280px widths with no broken composition"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-RESPONSIVE-01]
  - cmd: "attest: page body never scrolls horizontally; wide tables/code scroll inside their own container"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-RESPONSIVE-02]
  - cmd: "attest: every interactive target is at least 44x44 CSS px including padding"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-RESPONSIVE-03]
  - cmd: "attest: layout dimensions use relative units and flexbox/grid, not fixed pixel widths"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-RESPONSIVE-04]
  - cmd: "attest: images declare max-width:100% plus explicit intrinsic width/height"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-RESPONSIVE-05]
last_review: 2026-07-22
---

# Responsive Design (UX-RESPONSIVE)

## Abstract

Retires the "looks fine on my MacBook" failure: layouts that break, clip, or force
horizontal scrolling on the phone where real users actually are. Compliance in one breath:
CSS is written mobile-first, every layout is eyeballed at 375/768/1280px before "done", the
body never scrolls sideways (wide content scrolls inside its own container), touch targets
are ≥44px, dimensions are relative units on flexbox/grid, and images reserve their space.
Advisory at T1/T2 where James is the only viewer; required at T3+ where a phone-first
stranger is the first impression.

## Normative Rules

### UX-RESPONSIVE-01 — CSS MUST be mobile-first and layouts MUST be verified at 375px, 768px, and 1280px minimum

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Base styles target the narrow viewport; wider layouts are layered on with `min-width` media
queries — never the reverse (`max-width` override pyramids rot fast). Every page ships
`<meta name="viewport" content="width=device-width, initial-scale=1">`. The three widths are
the floor (iPhone SE-class, tablet, laptop), checked in DevTools responsive mode before any
completion claim; add project-specific breakpoints where content demands them, not at
device-catalog boundaries. SwiftUI analogue: layouts are adaptive by default — the
equivalent verification is largest Dynamic Type size plus both orientations.

### UX-RESPONSIVE-02 — The page body MUST NOT scroll horizontally at any supported width

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

No horizontal scroll ever, at any width down to 375px. Content that is legitimately wide —
data tables, code blocks, diagrams, wide charts — scrolls inside its own
`overflow-x: auto` container while the page itself stays put. Common causes to hunt when it
appears: fixed-width elements, unwrapped `<pre>`, absolute-positioned decoration, and
`100vw` (which ignores the scrollbar — use `100%`).

### UX-RESPONSIVE-03 — Interactive touch targets MUST be at least 44×44 CSS pixels

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Applies to buttons, links acting as buttons, form controls, and custom widgets. Padding
counts toward the target; the visible glyph may be smaller than the hit area. Adjacent
targets get enough spacing that a thumb cannot hit two at once. Dense desktop-only tables
MAY drop below 44px for pointer input, but any surface reachable from a phone does not.
This is Apple's HIG minimum — it applies to SwiftUI directly (44pt).

### UX-RESPONSIVE-04 — Layout dimensions SHOULD use relative units and flexbox/grid, not fixed pixels

**Tiers**: all advisory — **Layer**: A (attestation)

`rem`/`em` for type and spacing, `%`/`fr`/`minmax()`/`clamp()` for widths, `gap` for
gutters. Flexbox and grid absorb viewport variance that fixed-pixel layouts convert into
overflow bugs (see UX-RESPONSIVE-02). Fixed pixels remain fine for borders, icons, and
minimum constraints (`max-width: 65ch` for prose measure is encouraged). `rem`-based type
also respects the user's browser font-size setting, which is an accessibility input
(UX-A11Y).

### UX-RESPONSIVE-05 — Images MUST declare `max-width: 100%` and explicit intrinsic dimensions

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

`max-width: 100%; height: auto` prevents overflow; explicit `width`/`height` attributes (or
`aspect-ratio`) let the browser reserve space before the image loads, preventing layout
shift. CLS is measured and budgeted in `OPS-PERF` — this rule is the layout-side half of
that budget. Framework image components (`next/image`) satisfy this by construction when
given dimensions.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1–5 | attestation checklist (one entry per rule) | explicit yes recorded in GOVERNANCE.md | UX-RESPONSIVE-01…05 |

All five checks are visual-judgment attestations — no automated proxy currently exists that
is not noisier than it is worth at personal scale. The axe scan in UX-A11Y catches a subset
(viewport meta, some target-size issues) as a free side effect.

**Remediation:** horizontal scroll at 375px → find the fixed-width offender in DevTools
(`* { outline: 1px solid red }` sweep), wrap wide content in `overflow-x: auto` · cramped
touch targets → add padding, not margin (padding extends the hit area) · CLS from images →
add `width`/`height` attributes or `aspect-ratio`.

## Worked Example

```css
/* Mobile-first: base = 375px-class, enhancements layered upward */
.cards { display: grid; grid-template-columns: 1fr; gap: 1rem; }
@media (min-width: 768px)  { .cards { grid-template-columns: repeat(2, 1fr); } }
@media (min-width: 1280px) { .cards { grid-template-columns: repeat(3, 1fr); } }

/* Wide content scrolls in its own box — the body never does */
.table-wrap { overflow-x: auto; }

/* Images: no overflow, no layout shift */
img { max-width: 100%; height: auto; }

/* 44px touch target around a small glyph */
.icon-btn { padding: 0.75rem; } /* 20px icon + 12px padding each side = 44px */
```

```html
<meta name="viewport" content="width=device-width, initial-scale=1" />
<div class="table-wrap"><table>…</table></div>
<img src="/chart.png" width="1200" height="630" alt="Revenue by month" />
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Desktop-first CSS with `max-width` overrides | Every new feature re-breaks mobile; override pyramid grows | Mobile-first base + `min-width` layers (UX-RESPONSIVE-01) |
| `width: 100vw` on full-bleed sections | Ignores scrollbar width → permanent horizontal scroll | `width: 100%` on a full-width parent |
| Letting a wide `<table>` size the page | Body scrolls sideways; nav/header drift off-screen | Wrap in `overflow-x: auto` container (UX-RESPONSIVE-02) |
| 24px icon buttons with no padding | Unusable on touch; misses count as user error | Pad to ≥44px hit area (UX-RESPONSIVE-03) |
| Pixel-perfect fixed layouts (`width: 940px`) | Breaks at every width except the author's | Grid/flex + relative units (UX-RESPONSIVE-04) |
| Images without dimensions | Content jumps as they load; CLS penalty | Explicit `width`/`height` (UX-RESPONSIVE-05, `OPS-PERF`) |
| Testing only by resizing the browser a bit | Misses 375px reality and touch behavior | DevTools device mode at the three floor widths |

## References

- MDN "Responsive design" — the mobile-first + media-query model UX-RESPONSIVE-01 encodes.
- Apple Human Interface Guidelines, "Layout > Hit targets" — the 44pt source for
  UX-RESPONSIVE-03, applicable to web and SwiftUI alike.
- web.dev "Cumulative Layout Shift" — why explicit image dimensions matter; the metric
  itself is budgeted in `OPS-PERF`.
- WCAG 2.2 SC 2.5.8 "Target Size (Minimum)" — the accessibility floor that overlaps
  UX-RESPONSIVE-03 (UX-A11Y carries the WCAG gate).

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
