# ADR-0004: Enforce GOVERNANCE.md pins by semver level

- **Status**: accepted
- **Date**: 2026-10-27
- **Deciders**: the maintainer

## Context

`GOVERNANCE.md` pins each standard to an id + version, and ADR-0003 promised that pins
"give projects a stable view while the index moves forward". The verifier never honored
that: it ran the repo's current verification commands whatever the pin said, and only
printed a WARN on mismatch. New rules therefore reached every project silently under an
old pin, a green run reported a version that wasn't what ran, and a project pinned ahead
of a stale governance clone went unnoticed. Running the exact pinned content would need git
history plus per-version check scripts, which the repo doesn't have.

## Decision

`run-verification.py` enforces pins by the per-file semver level `/evolve-standards`
already defines (patch = wording/verification fix adding no requirement, minor = new rule
or tier change, major = breaking rework):

- **Same version** → run the checks.
- **Repo is a patch ahead** → WARN and run the current checks.
- **Repo is a minor or major ahead** → FAIL; that standard's checks are not run until
  `/govern` re-pins.
- **Pin is newer than the repo**, or either version isn't semver → FAIL; checks not run.

## Alternatives considered

- **Status quo (WARN only)** — silent upgrades; the pin is a label, not a contract.
- **FAIL on any mismatch** — strict but noisy: every wording or path fix (e.g. the
  portability change that patch-bumped 21 standards) would fail every project at once.
- **Run the pinned version from git history** — the only true "stable view", but check
  scripts aren't versioned per standard (a pinned 1.0.1 would still call today's
  scripts), and it requires a full clone with history.

## Consequences

Pins become an upgrade gate rather than a frozen view: a project can't "stay pinned" past a
minor or major release and still pass verification. The deliberate act is re-running
`/govern`, which re-pins and lists what changed; a new rule the project can't meet yet is
handled with a waiver (C9), as for any other rule. Patch bumps must not add requirements,
since they reach projects without a re-pin. Supersedes ADR-0003's "stable view"
consequence.
