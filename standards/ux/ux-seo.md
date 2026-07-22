---
id: UX-SEO
title: SEO & Web Metadata
family: UX
version: 1.0.0
status: active
tiers:
  T1: n/a
  T2: n/a
  T3: required
  T4: required
stacks: [web]
triggers:
  - seo
  - metadata
  - meta description
  - open graph
  - og tags
  - sitemap
  - robots.txt
  - canonical
  - structured data
  - json-ld
  - search ranking
  - indexing
requires: []
verification:
  - cmd: "attest: every public page has a unique title and meta description"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-SEO-01]
    tiers: [T3, T4]
  - cmd: "attest: shareable pages carry Open Graph/Twitter card tags and a canonical URL"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-SEO-02]
    tiers: [T3, T4]
  - cmd: "attest: sitemap.xml and robots.txt are served and reflect the intended index surface"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-SEO-03]
    tiers: [T3, T4]
  - cmd: "attest: each page has exactly one h1 and a semantic, non-skipping heading hierarchy"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-SEO-04]
    tiers: [T3, T4]
  - cmd: "attest: JSON-LD structured data is present where a schema.org type fits the content"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-SEO-05]
    tiers: [T3, T4]
  - cmd: "attest: content that must index is server-rendered or prerendered, verified with JS disabled"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [UX-SEO-06]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# SEO & Web Metadata (UX-SEO)

## Abstract

Retires the invisible-product failure: real pages that search engines can't rank and shared
links that unfurl as blank cards. Scope is **publicly indexable T3+ pages** — n/a below T3
because nothing public exists; auth-walled apps need only the robots.txt posture. Compliance
in one breath: unique title and description per page, OG/Twitter cards and a canonical URL,
served sitemap.xml and robots.txt, one h1 atop a semantic heading tree, JSON-LD where a
schema.org type fits, and indexable content present in server-rendered or prerendered HTML.
Core Web Vitals are a ranking factor; their budgets live in `OPS-PERF`, not here.

## Normative Rules

### UX-SEO-01 — Every public page MUST have a unique title and meta description

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

`<title>` ≈ ≤60 chars, page-specific-first ("Pricing — Acme", not "Acme — the best…" ×
every page); `<meta name="description">` ≈ 150–160 chars of copy that earns the click — it
is the search-result ad text. Unique per page: duplicated titles make pages compete with
each other and read as boilerplate to crawlers. Template pages generate these from content
(e.g. `{item.name} — Acme`). Auth-walled and utility pages (login, 404) still get titles
for tabs and history, but are out of indexing scope.

### UX-SEO-02 — Shareable pages MUST carry Open Graph/Twitter card tags and a canonical URL

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

`og:title`, `og:description`, `og:image` (1200×630, absolute URL), `og:url`, plus
`twitter:card` (`summary_large_image`) make links unfurl properly in Slack/iMessage/social —
the first impression most people ever get of the page. `<link rel="canonical">` names the
one true URL per page so `?utm_…`, trailing-slash, and www/apex variants don't split
ranking signal; canonicals are absolute and self-referential on the primary URL.

### UX-SEO-03 — The site MUST serve sitemap.xml and robots.txt reflecting the intended index surface

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

`robots.txt` at the origin root: allow the public surface, `Disallow` private/utility
paths, and point `Sitemap:` at the sitemap URL. `sitemap.xml` lists every canonical
indexable URL — generated at build/request time (`next-sitemap`, framework route
introspection), never hand-maintained into staleness. Staging and preview deployments are
the inverse: `noindex` everywhere (header or meta), so half-built content never enters the
index — `INF-ENVS` owns environment separation. Note robots.txt is crawl control, not
access control: anything truly private sits behind auth (`SEC` families), not a Disallow
line that helpfully advertises the path.

### UX-SEO-04 — Each page MUST have exactly one h1 and a semantic, non-skipping heading hierarchy

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

One `<h1>` stating what the page is; `<h2>`/`<h3>` nest without skipping levels; headings
are chosen for structure, never for font size (that's a CSS class — UX-DESIGN tokens).
Crawlers and screen readers consume the same outline, so this rule is double-billed with
UX-A11Y (axe flags heading-order violations as a free side check). The heading tree read
alone should summarize the page.

### UX-SEO-05 — Pages SHOULD emit JSON-LD structured data where a schema.org type fits the content

**Tiers**: T1–T2 n/a · T3–T4 advisory — **Layer**: A (attestation)

Where the content matches a schema.org type — `Article`, `Product` (price/availability),
`FAQPage`, `SoftwareApplication`, `BreadcrumbList` — emit it as JSON-LD in a
`<script type="application/ld+json">` block; it powers rich results (stars, prices, FAQs)
that lift click-through beyond position. Only claim what the page visibly shows (fabricated
review stars draw manual penalties), and validate with Google's Rich Results Test. Skip it
where no type fits — generic `WebPage` markup is ceremony.

### UX-SEO-06 — Content that must index MUST be server-rendered or prerendered

**Tiers**: T1–T2 n/a · T3–T4 required — **Layer**: A (attestation)

Anything that should rank must be present in the HTML response itself, not assembled
client-side after a JS bundle executes — client-only rendering gets deferred, partial, or
absent indexing. Marketing pages, docs, and product/listing pages use SSR/SSG (`STK-NEXT`)
or server-rendered HTML with progressive enhancement (`STK-HTMX`); the app-behind-login can
stay a client-side SPA — it isn't in the index surface. Verification is empirical: view
source (or fetch with JS disabled) and confirm the content is in the payload. Core Web
Vitals also feed ranking; budgets and measurement live in `OPS-PERF`.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1–6 | attestation checklist, T3+ (one entry per rule) | explicit yes recorded in GOVERNANCE.md | UX-SEO-01…06 |

Attestation aids: `curl -s https://site/robots.txt` and `/sitemap.xml` return 200 with
expected content · `curl -s URL | grep -c '<h1'` returns 1 · view-source shows title, meta
description, OG tags, and the indexable copy without JS.

**Remediation:** duplicate titles → template them from page content · blank link unfurls →
add OG tags with an absolute `og:image` · stale sitemap → generate at build, delete the
hand-edited file · content missing with JS off → move the route to SSR/SSG or prerender ·
staging indexed → add `noindex` header + remove from sitemap, then request removal in
Search Console.

## Worked Example

```html
<head>
  <title>Mortgage Payoff Calculator — Acme Tools</title>
  <meta name="description" content="See how extra payments shorten a 30-year mortgage. Free calculator with amortization schedule and payoff date." />
  <link rel="canonical" href="https://tools.acme.dev/mortgage-payoff" />
  <meta property="og:title" content="Mortgage Payoff Calculator" />
  <meta property="og:description" content="See how extra payments shorten a 30-year mortgage." />
  <meta property="og:image" content="https://tools.acme.dev/og/mortgage-payoff.png" />
  <meta property="og:url" content="https://tools.acme.dev/mortgage-payoff" />
  <meta name="twitter:card" content="summary_large_image" />
  <script type="application/ld+json">
  { "@context": "https://schema.org", "@type": "SoftwareApplication",
    "name": "Mortgage Payoff Calculator", "applicationCategory": "FinanceApplication",
    "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" } }
  </script>
</head>
```

```
# robots.txt
User-agent: *
Disallow: /api/
Disallow: /account/
Sitemap: https://tools.acme.dev/sitemap.xml
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Same title/description on every page | Pages compete; crawlers see boilerplate | Unique, templated from content (UX-SEO-01) |
| No OG tags "because we're not on social" | Slack/iMessage unfurls decide clicks too | Full OG/Twitter set (UX-SEO-02) |
| Hand-maintained sitemap.xml | Stale within weeks; worse than none | Generate at build (UX-SEO-03) |
| Staging site indexable | Duplicate/broken content enters the index | `noindex` all non-prod (UX-SEO-03, `INF-ENVS`) |
| Hiding private paths via robots.txt | Publicly advertises them; blocks nothing | Auth-wall them; robots is crawl control only |
| Multiple h1s / headings picked for size | Outline garbage for crawlers and screen readers | One h1, CSS for size (UX-SEO-04) |
| Review stars in JSON-LD with no reviews shown | Manual-action penalty territory | Mark up only visible content (UX-SEO-05) |
| Client-rendered marketing pages | Content invisible or late to crawlers | SSR/SSG (UX-SEO-06, `STK-NEXT`/`STK-HTMX`) |

## References

- Google Search Central, "SEO Starter Guide" + "JavaScript SEO basics" — titles/
  descriptions guidance and the rendering-pipeline rationale behind UX-SEO-06.
- The Open Graph protocol (ogp.me) — the tag set UX-SEO-02 requires.
- sitemaps.org protocol + Google robots.txt docs — the crawl-surface contract (UX-SEO-03).
- schema.org + Google Rich Results Test — types and validation for UX-SEO-05.
- `OPS-PERF` — Core Web Vitals thresholds; a ranking input deliberately not duplicated
  here.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
