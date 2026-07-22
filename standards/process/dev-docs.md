---
id: DEV-DOCS
title: Documentation & ADRs
family: DEV
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - readme
  - documentation
  - docs
  - adr
  - decision record
  - claude.md
  - comments
  - onboarding
requires: []
verification:
  - cmd: "attest: README covers what it is, how to run, how to test, and where config lives"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-DOCS-01]
  - cmd: "attest: CLAUDE.md commands run verbatim as written, and structure/gotchas match the current code"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-DOCS-02]
  - cmd: "attest: every hard-to-reverse decision made this cycle has an ADR from templates/adr-template.md"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-DOCS-03]
    tiers: [T2, T3, T4]
  - cmd: "attest: all project documentation lives in the repo — no external wikis or docs silos"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-DOCS-04]
  - cmd: "attest: comments added this cycle explain constraints and why, not what the code does"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-DOCS-05]
last_review: 2026-07-22
---

# Documentation & ADRs (DEV-DOCS)

## Abstract

Documentation here serves two readers: future-James and the implementing agent. The
README answers what/run/test/config in one screen; `CLAUDE.md` is the agent's operating
manual and staying true is part of "done"; hard-to-reverse decisions get an ADR at T2+
(the test: *would future-me ask why?*); everything lives in the repo, versioned with the
code it describes; comments explain constraints and why, never narrate what. File
*existence* is DEV-BOOTSTRAP's job — this standard owns content and currency.

## Normative Rules

### DEV-DOCS-01 — The README MUST cover: what it is, how to run, how to test, where config lives

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Minimum viable README, in one screen: one paragraph of what and why; the run command(s),
copy-pasteable; the test command; where configuration lives (`settings.yaml`, env vars
via `.env.example`). Anything beyond that is optional. The audience is future-James six
months out, who remembers nothing — if he'd have to open source files to answer one of
the four questions, the README is below minimum.

### DEV-DOCS-02 — `CLAUDE.md` MUST stay true to the project, as part of "done"

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Contents: project structure, every routine command in directly-runnable form
(`.venv/bin/pytest -q`, exact flags — STK-PY-08), and gotchas (things that look wrong but
are right, things that look right but break). Currency rule: a change that renames a
directory, alters a command, or adds a gotcha updates `CLAUDE.md` *in the same PR* —
Constitution C2's "done" includes it. A stale `CLAUDE.md` is worse than none: the agent
trusts it verbatim.

### DEV-DOCS-03 — Hard-to-reverse decisions MUST be recorded as ADRs at T2+

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Use `templates/adr-template.md`, numbered sequentially in `decisions/`
(`adr-0001-{slug}.md`). Triggering decisions: storage choice, auth approach, framework,
hosting — anything where switching later means migration, not refactoring. The
admission test is **"would future-me ask why?"**: if yes, write the ADR *when deciding*,
while the rejected alternatives are still fresh. An ADR is 20 minutes; re-deriving the
reasoning a year later is a day. Reversals don't edit old ADRs — they add a superseding
one.

### DEV-DOCS-04 — Documentation MUST live in the repo, not external wikis

**Tiers**: all required — **Layer**: A (attestation)

Docs version with the code they describe: a checkout at any commit carries the docs that
were true then, greppable by agent and human alike. Notion/Confluence/Google-Docs silos
drift invisibly and are dark to Claude Code. The Obsidian vault is for cross-project
*learnings and captures* (Constitution C10), never for project documentation. GitHub
rendering of in-repo markdown is the only "wiki" needed.

### DEV-DOCS-05 — Comments SHOULD explain constraints and why — never what

**Tiers**: all advisory — **Layer**: A (attestation)

House style: the code says what; comments carry what the code cannot — constraints
("numba lacks 3.14 wheels, keep this pure-python"), non-obvious why ("naive datetimes
compare false here, see ADR-0003"), and warnings ("order matters: the API rate-limits
after 5 calls"). A comment restating the line below it (`# increment counter`) is noise
to delete on sight. Docstrings on public functions state contract and units, same rule.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attestation: README covers what/run/test/config | explicit yes | DEV-DOCS-01 |
| 2 | attestation: CLAUDE.md commands run verbatim; content current | explicit yes | DEV-DOCS-02 |
| 3 | attestation: this cycle's hard-to-reverse decisions have ADRs (T2+) | explicit yes | DEV-DOCS-03 |
| 4 | attestation: no external doc silos | explicit yes | DEV-DOCS-04 |
| 5 | attestation: new comments are why-comments | explicit yes | DEV-DOCS-05 |

**Remediation:** README gap → add the missing section now; it is four headings, not a
project · stale CLAUDE.md command → run every listed command, fix the ones that fail ·
undocumented past decision that keeps generating "why?" → write the ADR retroactively,
dated today, noting it is a reconstruction · external doc discovered → move the content
into the repo, leave a tombstone link.

## Worked Example

Minimum-viable README and the matching CLAUDE.md core, for a T2 analysis tool:

```markdown
# rate-watch
Tracks FRED mortgage-rate series and flags refinance windows (research input, T2).

## Run     — `.venv/bin/python -m rate_watch --config settings.yaml`
## Test    — `.venv/bin/pytest -q`
## Config  — `settings.yaml` (thresholds, series ids) · secrets: see `.env.example`
```

```markdown
# CLAUDE.md
## Commands
- `.venv/bin/pytest -q` — full suite
- `.venv/bin/ruff check . && .venv/bin/ruff format --check .` — lint gate
## Structure
- `src/rate_watch/signal.py` — analytical core (review at T2 rung, DEV-REVIEW-01)
## Gotchas
- FRED returns "." for missing observations — parsed as NaN, not zero (ADR-0002)
```

Decision log: `decisions/adr-0002-treat-fred-dots-as-nan.md` — a storage-format decision
future-me would absolutely ask about.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| README as aspirational spec ("will support…") | Reader can't tell built from imagined | Document what exists; specs live in SPEC-*.md |
| Updating CLAUDE.md "in a follow-up PR" | The follow-up never comes; agent now misled | Same-PR updates; it's part of done (DEV-DOCS-02) |
| ADR written only after the decision bites | Alternatives forgotten; ADR becomes fiction | Write at decision time, 20 minutes |
| Editing an old ADR to match the new choice | History lies; "why did we switch" unanswerable | New superseding ADR, link both ways |
| Project runbook in Notion | Invisible to agent, unversioned, drifts | In-repo markdown (DEV-DOCS-04) |
| `# loop over rows` | Restates the code; rots on first edit | Delete; comment the constraint, not the mechanics |
| Commands documented with "activate the venv first" | Breaks agents, launchd, CI (STK-PY-08) | Verbatim-runnable `.venv/bin/…` form |

## References

- `templates/adr-template.md` — the required ADR format.
- Michael Nygard, "Documenting Architecture Decisions" — the ADR practice DEV-DOCS-03
  adapts; the future-me test is its solo-scale reduction.
- Constitution C2 — why doc currency is part of "done", not a follow-up.
- DEV-BOOTSTRAP — owns file existence; this standard assumes the files are there.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
