---
id: ARC-MODULARITY
title: Modularity & Boundaries
family: ARC
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - module
  - package structure
  - imports
  - circular import
  - boundaries
  - layering
  - project layout
  - coupling
  - code organization
  - refactor
  - shared code
requires: []
verification:
  - cmd: "python3 ~/Dev/claude-code/governance/checks/import-cycles.py"
    expect: "exit 0 — first-party import graph is acyclic (no-op when no Python package present)"
    layer: G
    rules: [ARC-MODULARITY-01]
    tiers: [T2, T3, T4]
  - cmd: "attest: dependencies point one way — domain logic imports no IO/framework code"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-MODULARITY-02]
  - cmd: "attest: packages expose an explicit surface (__all__/index.ts); consumers import from it, not deep paths"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-MODULARITY-03]
  - cmd: "attest: shared code was extracted only on a third identical-semantics use"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-MODULARITY-04]
  - cmd: "attest: files past ~500 lines were inspected for a seam (split or consciously kept)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-MODULARITY-05]
  - cmd: "attest: code is organized by vertical slice (feature), not by layer alone"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [ARC-MODULARITY-06]
last_review: 2026-07-22
---

# Modularity & Boundaries (ARC-MODULARITY)

## Abstract

Keeps codebases navigable by an agent with finite context and a human with finite
patience: `src`-layout packages (`STK-PY-01`) whose import graph is acyclic — the
canonical check is `checks/import-cycles.py` hunting circular imports — with dependencies
pointing one way (domain logic imports nothing from IO or frameworks). Modules expose
small explicit surfaces (`__all__` / `index.ts`); shared code is extracted only on the
third use; a file passing ~500 lines gets inspected for a seam; and at T1/T2, code is
organized by vertical slice, not by layer. Structure is advisory at T1, load-bearing from
T2 up.

## Normative Rules

### ARC-MODULARITY-01 — The first-party import graph MUST be acyclic

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G (checks/import-cycles.py)

A circular import is the detection, not the disease: it means two modules each need the
other, i.e. the boundary between them is fictional. `checks/import-cycles.py` parses
`src/` and reports cycles (`if TYPE_CHECKING:` imports excluded — type-only edges cannot
bite at runtime). Fix by inverting the dependency: move the shared piece into a module
both import, or pass the dependency in — never by hiding the import inside a function,
which keeps the cycle and removes the evidence. TypeScript projects run
`npx madge --circular src` as the equivalent check.

### ARC-MODULARITY-02 — Dependencies MUST point one way: domain logic imports no IO or framework code

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Three rings: **domain** (pure logic + typed models) ← **adapters** (HTTP handlers, DB
access, API clients, file IO) ← **entrypoints** (CLI/app wiring, `ARC-CONFIG` loading).
Domain modules import stdlib, each other, and model classes — never `fastapi`, `httpx`,
`boto3`, or an ORM session. The payoff is concrete: the analytical core tests as plain
functions with no mocks (`TST-*` leverage — the discipline that keeps the oracle suite's
leakage guards testable), and swapping an adapter touches one ring.

### ARC-MODULARITY-03 — Packages SHOULD expose a small explicit surface

**Tiers**: all advisory — **Layer**: A (attestation)

Python packages declare `__all__` in `__init__.py`; TS directories re-export through
`index.ts`. Consumers import from the surface (`from myproj.ingest import run_ingest`),
never deep paths into another module's internals — anything unexported is private and
free to change without a repo-wide grep. A surface that needs more than ~5–10 names is a
hint the package holds two ideas (rule 05's seam test applies).

### ARC-MODULARITY-04 — Shared code SHOULD be extracted only on the third use

**Tiers**: all advisory — **Layer**: A (attestation)

The rule of three, operationalizing `ARC-PATTERNS`' DRY-before-3 anti-pattern: duplicate
at the second occurrence; extract at the third — and only when the semantics are
identical, not merely the shape. Two functions that look alike but change for different
reasons stay separate; unifying them welds unrelated futures together, and un-inlining a
wrong abstraction costs more than the duplication ever did.

### ARC-MODULARITY-05 — A file passing ~500 lines SHOULD be inspected for a seam

**Tiers**: all advisory — **Layer**: A (attestation)

A smell threshold, not a limit: a cohesive 600-line module may stand after inspection,
but the inspection happens and splits follow responsibility seams — never `utils2.py`.
Self-check one-liner: `find src -name '*.py' | xargs wc -l | sort -rn | head`. The same
threshold flags god objects (`ARC-PATTERNS` table): if every change touches this file,
the seam is overdue regardless of line count.

### ARC-MODULARITY-06 — T1/T2 code SHOULD be organized by vertical slice, not by layer alone

**Tiers**: all advisory — **Layer**: A (attestation)

Feature directories (`ingest/`, `report/`) each holding their own domain + adapters beat
top-level `models/` + `services/` + `controllers/` at personal scale: one feature change
touches one directory, and a slice can be deleted whole. Rule 02's direction discipline
applies *inside* each slice, so this is not a license for spaghetti — it is layers
rotated 90°, per slice. Layer-first trees earn their keep only when many slices share
heavy infrastructure (a T3+ concern).

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `python3 ~/Dev/claude-code/governance/checks/import-cycles.py` (T2+) | exit 0 — acyclic (or no Python package) | ARC-MODULARITY-01 |
| 2–6 | attestation checklist (one entry per rule) | explicit yes recorded | ARC-MODULARITY-02…06 |

**Remediation:** cycle reported → move the shared piece into a lower module both sides
import, or inject the dependency; never function-local imports to dodge the checker ·
domain importing an adapter → invert: define the interface in domain, implement in the
adapter · deep imports → add the name to the package surface or stop reaching in.

## Worked Example

Vertical slices with one-way dependencies (rules 01, 02, 03, 06):

```
src/myproj/
├── config.py            # ARC-CONFIG's single config module
├── ingest/              # vertical slice (ARC-MODULARITY-06)
│   ├── __init__.py      # __all__ = ["run_ingest"]          (ARC-MODULARITY-03)
│   ├── domain.py        # pure logic — stdlib + models only  (ARC-MODULARITY-02)
│   └── source_http.py   # httpx adapter; imports domain — never the reverse
└── report/
    ├── __init__.py      # __all__ = ["render_report"]
    ├── domain.py
    └── render.py        # jinja/file-IO adapter
```

Direction check: `source_http → domain` is legal; `domain → source_http` would put
`httpx` in the pure ring — rule 02 violation and, sooner or later, a cycle that
`python3 ~/Dev/claude-code/governance/checks/import-cycles.py` reports (rule 01).

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `utils.py` / `helpers.py` grab-bag | A god module every feature imports — maximum coupling, no meaning | Name modules for responsibilities (ARC-MODULARITY-05) |
| Function-local import to "fix" a cycle | Cycle remains, checker blinded, boundary still fictional | Invert the dependency (ARC-MODULARITY-01) |
| `from proj.report.render import _helper` | Couples to another module's private internals | Import the exported surface (ARC-MODULARITY-03) |
| Base class extracted at the second use | Wrong abstraction hardens; case three bends to fit it | Rule of three (ARC-MODULARITY-04) |
| `models/`+`services/`+`views/` for a 3-feature tool | One change scatters across the tree; nothing deletes cleanly | Vertical slices (ARC-MODULARITY-06) |
| Domain function taking an ORM session | Untestable without a DB; framework leaks into pure logic | Pass values in, return values out (ARC-MODULARITY-02) |
| 2,000-line module everyone fears | Merge conflicts with yourself; agents burn context loading it | Split at responsibility seams (ARC-MODULARITY-05) |

## References

- Alistair Cockburn, "Hexagonal Architecture (Ports & Adapters)" — the one-way direction
  rule 02 is the personal-scale distillation of.
- Sandi Metz, "The Wrong Abstraction" — the cost model justifying rule 04's third-use
  threshold.
- import-linter (PyPI) — contract-based import enforcement; the T3+ escalation when
  attested direction (rule 02) deserves a hard gate.
- madge (npm) — the TypeScript circular-import checker named in rule 01.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
