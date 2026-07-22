---
id: UX-I18N
title: Internationalization
family: UX
version: 1.0.0
status: active
tiers:
  T1: n/a
  T2: n/a
  T3: n/a
  T4: required
stacks: [web]
triggers:
  - i18n
  - internationalization
  - localization
  - locale
  - translation
  - currency
  - timezone
  - date format
  - rtl
requires: []
verification:
  - cmd: "attest: user-facing strings are externalized as templates with named placeholders, never concatenated"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-I18N-01]
    tiers: [T4]
  - cmd: "attest: dates, numbers, and currency render via Intl APIs with an explicit locale"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-I18N-02]
    tiers: [T4]
  - cmd: "attest: timestamps are stored in UTC and converted to the user's timezone only at display"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-I18N-03]
    tiers: [T4]
  - cmd: "attest: RTL rendering has been assessed (and implemented with logical properties) for target markets"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-I18N-04]
    tiers: [T4]
last_review: 2026-07-22
---

# Internationalization (UX-I18N)

## Abstract

T4-only, and deliberately dormant until then: this standard triggers when the first
non-English market becomes a real commercial decision — not speculatively. Building locale
infrastructure for hypothetical users is pure carrying cost (n/a at T1–T3 is honest, not
lazy). Once triggered: user-facing strings live in externalized templates with named
placeholders (word order varies by language), dates/numbers/currency render through `Intl`
with an explicit locale, storage stays UTC with display-time conversion, and RTL is
assessed for the actual target markets. What is *not* deferred at any tier: UTC storage and
aware datetimes, which `STK-PY` already requires for correctness reasons.

## Normative Rules

### UX-I18N-01 — User-facing strings MUST be externalized as templates with named placeholders

**Tiers**: T1–T3 n/a · T4 required — **Layer**: A (attestation)

All user-visible copy lives in locale resource files (ICU MessageFormat, `next-intl`
messages, Xcode String Catalogs for SwiftUI), keyed and looked up — never inline literals
once this standard is active. Concatenation (`"Added " + n + " items"`) is prohibited: word
order differs across languages, so templates use named placeholders
(`{count} items added`) that translators can reorder freely. Pluralization goes through
the library's plural rules (ICU `{count, plural, …}`), not `count === 1 ? … : …` — many
languages have more than two plural forms.

### UX-I18N-02 — Dates, numbers, and currency MUST render via Intl APIs with an explicit locale

**Tiers**: T1–T3 n/a · T4 required — **Layer**: A (attestation)

`Intl.DateTimeFormat`, `Intl.NumberFormat` (with `style: "currency"` and the ISO 4217
code), and `Intl.RelativeTimeFormat` — never hand-rolled `MM/DD/YYYY` strings or
`toFixed(2) + "€"`. The locale is passed explicitly from the user's resolved preference,
not inherited from the server's runtime default (a server in us-east-1 formatting for a
German user is the classic bug). Currency amounts store as integer minor units plus
currency code; formatting is display-only.

### UX-I18N-03 — Timestamps MUST be stored in UTC and converted to the user's timezone only at display

**Tiers**: T1–T3 n/a · T4 required — **Layer**: A (attestation)

Storage, APIs, and logs speak UTC (ISO 8601 with offset); the user's timezone applies at
the last render step. This restates `STK-PY`'s aware-datetime rule (naive datetimes are
ARC-level bugs) from the display side: the tier tag here governs the *localization* layer —
the UTC-storage half is already required at every tier by the stack standard. Future-dated
human events (appointments) additionally record the intended IANA zone, since offsets
change under governments' feet.

### UX-I18N-04 — RTL rendering SHOULD be implemented with logical properties when target markets need it

**Tiers**: T1–T3 n/a · T4 advisory — **Layer**: A (attestation)

If target markets include RTL languages (Arabic, Hebrew), layouts use CSS logical
properties (`margin-inline-start`, `padding-inline-end`, `text-align: start`) instead of
physical left/right, and `dir="rtl"` is set per locale. If no RTL market is targeted,
attest exactly that — but prefer logical properties in new CSS regardless; they cost
nothing and keep the door open.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1–4 | attestation checklist, T4 only (one entry per rule) | explicit yes recorded in GOVERNANCE.md | UX-I18N-01…04 |

Quick self-audit before attesting UX-I18N-01: grep components for quoted sentence-like
literals and string `+` involving user-visible text; hits are either keys or violations.

**Remediation:** concatenated strings → convert to keyed ICU templates with named
placeholders · hardcoded formats → `Intl.*` with the user's locale · timezone bugs →
push conversion to the render edge, store UTC (`STK-PY`).

## Worked Example

```jsonc
// locales/en.json
{ "cart.added": "{count, plural, one {# item} other {# items}} added to your cart" }
// locales/de.json — translator reorders freely; plural rules differ
{ "cart.added": "{count, plural, one {# Artikel} other {# Artikel}} zum Warenkorb hinzugefügt" }
```

```ts
t("cart.added", { count: 3 });                                   // not "Added " + 3 + "…"
new Intl.NumberFormat(locale, { style: "currency", currency: "EUR" }).format(cents / 100);
new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: userTz })
  .format(new Date(utcIso));                                     // UTC in, local out
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Building i18n before a non-English market exists | Carrying cost, stale catalogs, no user benefit | Trigger on the market decision (this standard's tiers) |
| `"Added " + n + " items"` | Word order and plural rules vary by language | Named-placeholder ICU template (UX-I18N-01) |
| `count === 1 ? "item" : "items"` | Slavic/Arabic plural systems have 3–6 forms | ICU plural rules (UX-I18N-01) |
| Server-default locale formatting | Formats for the datacenter, not the user | Explicit locale from user preference (UX-I18N-02) |
| Storing local times or naive datetimes | Unanswerable "when" once zones/DST shift | UTC storage, display-edge conversion (UX-I18N-03, `STK-PY`) |
| `margin-left` in new CSS | Mirrors wrong under RTL | Logical properties (UX-I18N-04) |
| Machine-translating the catalog and shipping | Reads as broken to native speakers; brand damage | Human review per launched locale (`LEG-COMMERCIAL` for legal copy) |

## References

- ICU MessageFormat docs — the plural/placeholder syntax UX-I18N-01 mandates.
- MDN `Intl` reference — `DateTimeFormat`/`NumberFormat`/`RelativeTimeFormat` APIs
  (UX-I18N-02).
- W3C "Structural markup and right-to-left text in HTML" + MDN CSS logical properties —
  the RTL implementation path (UX-I18N-04).
- `STK-PY` dates rule — the always-on UTC/aware-datetime floor this standard's display
  layer sits on.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
