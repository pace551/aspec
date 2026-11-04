# ADR-0005: Apply T3 weight to published packages per standard

- **Status**: accepted
- **Date**: 2026-11-04
- **Deciders**: the maintainer

## Context

`tiers.md` has a carve-out for published libraries and packages (code others install, no
service the user operates): classify by the normal rubric, but the supply-chain families
(SEC, TST, DEV, LEG licensing) apply at T3 weight. No tooling implements it. The tier is
a single value, so a published T1 package either keeps tier T1, where the stricter
standards are never selected and their T3-scoped checks are skipped
(`run-verification.py` drops checks whose `tiers:` excludes the project's tier), or sets
tier T3 and inherits service-only standards (staging, observability, backups, UX). The
families are also too coarse: SEC-AUTHN or SEC-WEB guard a running service and say
nothing about a package. This repo is the first case (its own `GOVERNANCE.md` records the
gap), and any library governed by ASPEC is the next.

## Decision

Each standard declares whether its risk travels with a published package, and a project
manifest declares whether it is one:

- **Manifest**: `published_package: true | false` (default false) in `GOVERNANCE.md`. The
  tier stays what the rubric says.
- **Standard frontmatter**: `published: required | advisory | n/a`. It is required on
  every SEC, TST, DEV and LEG standard, so no standard is left unclassified by omission,
  and optional elsewhere (absent = `n/a`).
- **Effect**: for a published package, a standard marked `required` or `advisory` is
  selected with that applicability, and its checks run at an effective tier of
  max(project tier, T3). Every other standard follows the project tier as today.
- **Test**: a standard is `required` when the risk it guards ships to the people who
  install the package (dependencies, licensing, code flaws, supply-chain integrity,
  change control), and `n/a` when it guards a running service or a business.

Initial classification, to be applied in the implementation PR:

| `published` | Standards |
|---|---|
| required | SEC-SUPPLY, SEC-SAST, SEC-INPUT, SEC-CRYPTO, SEC-SECRETS, DEV-DEPS, DEV-CI, DEV-REVIEW, DEV-GIT, DEV-BOOTSTRAP, LEG-LICENSING, TST-RATCHET, TST-POLICY, TST-VERIFY, TST-FIXTURES |
| advisory | SEC-THREAT, DEV-DOCS, TST-INTEG |
| n/a | SEC-AUTHN, SEC-AUTHZ, SEC-WEB, LEG-COMMERCIAL |

## Alternatives considered

- **Family-wide uplift with exceptions** — pulls in service-only standards (SEC-AUTHN,
  SEC-WEB), and waivers must expire, which doesn't fit a rule that never applies.
- **`tier_override` to T3** — drags in staging, observability, backups and UX standards.
- **A central list of uplifted standards** — the classification would live apart from the
  standard it describes and drift when standards change.
- **Status quo** — the carve-out stays prose; a green run doesn't mean what the rulebook
  says it should.

## Consequences

Adding the `published` key patch-bumps the 22 standards above. That is safe under ADR-0004
because no project can carry `published_package` yet, so no pinned project's requirements
change. From then on, changing a standard's `published` value is a minor bump, like any
applicability change. The implementation touches `select-standards.py` and
`run-verification.py` (effective tier), `lint-framework.py` (key required for the four
families), the GOVERNANCE and standard templates, `AUTHORING.md`, `tiers.md` (the
carve-out points at the flag), and `/govern`, which must ask whether a project is
published. This repo then sets the flag, re-pins, and fixes or records whatever fails,
which replaces the "known gap" note in its `GOVERNANCE.md`.
