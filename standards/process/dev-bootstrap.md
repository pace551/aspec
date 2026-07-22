---
id: DEV-BOOTSTRAP
title: Repository Bootstrap
family: DEV
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - new repo
  - new project
  - bootstrap
  - scaffold
  - git init
  - readme
  - claude.md
  - governance.md
  - gitignore
  - license
  - git hooks
requires: [SEC-SECRETS]
verification:
  - cmd: "sh -c 'git rev-parse --is-inside-work-tree >/dev/null && { git symbolic-ref --short -q HEAD | grep -qx main || git show-ref --verify --quiet refs/heads/main; }'"
    expect: "exit 0 — inside a git repo that has (or is on unborn) main"
    layer: G
    rules: [DEV-BOOTSTRAP-01]
  - cmd: "sh -c '[ -s README.md ]'"
    expect: "exit 0 — non-empty README.md at repo root"
    layer: G
    rules: [DEV-BOOTSTRAP-02]
  - cmd: "sh -c '[ -s CLAUDE.md ]'"
    expect: "exit 0 — non-empty CLAUDE.md at repo root"
    layer: G
    rules: [DEV-BOOTSTRAP-03]
  - cmd: "sh -c '[ -s GOVERNANCE.md ]'"
    expect: "exit 0 — non-empty GOVERNANCE.md at repo root"
    layer: G
    rules: [DEV-BOOTSTRAP-04]
  - cmd: "sh -c '[ -s .gitignore ]'"
    expect: "exit 0 — non-empty .gitignore at repo root"
    layer: G
    rules: [DEV-BOOTSTRAP-05]
  - cmd: "sh -c '[ -x .git/hooks/pre-commit ] && [ -x .git/hooks/pre-push ]'"
    expect: "exit 0 — both hooks installed and executable"
    layer: G
    rules: [DEV-BOOTSTRAP-06]
  - cmd: "sh -c '[ -f .coverage-baseline ]'"
    expect: "exit 0 — committed coverage baseline exists"
    layer: G
    rules: [DEV-BOOTSTRAP-07]
    tiers: [T2, T3, T4]
  - cmd: "attest: if the repo is public (or about to be pushed public), a license file exists at the root"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [DEV-BOOTSTRAP-08]
last_review: 2026-07-22
---

# Repository Bootstrap (DEV-BOOTSTRAP)

## Abstract

Defines what every repository has from day one — the contract `/bootstrap-repo` implements
and `/verify-compliance` audits. A repo missing any required item is **unbootstrapped**,
and the compliance report says exactly that. In one breath: git with `main` as default
branch, README, `CLAUDE.md`, `GOVERNANCE.md`, stack-appropriate `.gitignore`,
`.env.example` whenever a credential exists (SEC-SECRETS), hooks installed from
`templates/scaffolds/_common/`, `.coverage-baseline` at T2+, license file for anything
public. Bootstrap is one skill run and retrofit is the same skill run — there is never a
good reason to stay unbootstrapped.

## Normative Rules

### DEV-BOOTSTRAP-01 — Every project MUST live in a git repository whose default branch is `main`

**Tiers**: all required — **Layer**: G

`git init` happens before the first file is written, not after the code "settles" —
history from line one is what makes secret-scan hooks and the coverage ratchet meaningful.
`main` is the default branch name everywhere (no `master`, no per-repo variation), so
scripts, CI fragments, and branch protection templates never special-case. Working from a
feature branch is fine; `main` just has to exist or be the unborn HEAD.

### DEV-BOOTSTRAP-02 — A README MUST exist from the first commit, answering what / why / run

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

Three sections minimum: what this is, why it exists, how to run it. The content bar and
"how to test / where config lives" requirements are DEV-DOCS-01's job; this rule ensures
the file exists non-empty from day one so it accretes instead of being backfilled.

### DEV-BOOTSTRAP-03 — A `CLAUDE.md` MUST exist describing structure, runnable commands, and gotchas

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

`CLAUDE.md` is the implementing agent's operating manual: project structure, every
routine command in directly-runnable form (`.venv/bin/pytest -q`, never "activate then
run" — STK-PY-08), and known gotchas. Currency ("kept true as part of done") is
DEV-DOCS-02; existence is bootstrap.

### DEV-BOOTSTRAP-04 — A `GOVERNANCE.md` MUST exist, produced by `/govern`, before feature work starts

**Tiers**: all required — **Layer**: G

The manifest records tier, stacks, pinned standard versions, waivers, and attestations
(Constitution C5). Without it `/verify-compliance` cannot even determine which rules
apply, so it is required at every tier — a one-line `tier: T1` manifest is a valid
manifest. Never written retroactively at verification time.

### DEV-BOOTSTRAP-05 — A stack-appropriate `.gitignore` MUST exist before the first commit

**Tiers**: all required — **Layer**: G

Taken from the stack scaffold (`templates/scaffolds/{stack}/`), covering at minimum:
`.env`, virtualenv/node_modules-class directories, build artifacts, and editor droppings.
The `.env` line exists *before* the first credential does; the paired `.env.example`
requirement and its verification live in SEC-SECRETS-02 — bootstrap's job is that the
ignore file is in place so that rule can never be violated by accident.

### DEV-BOOTSTRAP-06 — Git hooks MUST be installed from `templates/scaffolds/_common/`

**Tiers**: all required — **Layer**: G

Pre-commit runs format + lint + secret scan (`checks/secret-scan.sh --staged`); pre-push
runs tests + coverage ratchet. Hooks are the *only* gate T1 repos have (DEV-CI-02), which
is why this rule gets no T1 discount. Install by copying from
`templates/scaffolds/_common/` and marking executable. `--no-verify` is an emergency
lever, not a workflow: using it requires a stated reason in the commit body (C9 —
deviations are visible).

### DEV-BOOTSTRAP-07 — A `.coverage-baseline` MUST be committed at T2+

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

Written by the first ratchet run (`checks/coverage-ratchet.py`) and committed; from then
on coverage only moves up (TST-RATCHET, Constitution C3). Bootstrap creates it even when
the initial number is low — the ratchet needs a floor to exist before it can hold.

### DEV-BOOTSTRAP-08 — Anything public MUST carry a license file

**Tiers**: all required — **Layer**: A (attestation)

"Public" means the GitHub repo is or is about to become public, regardless of tier — a T1
dotfiles repo pushed public needs a license just like a T4 product. No license means
default copyright: nobody can legally use the code, which is never the intent of
publishing. House default is MIT unless LEG-LICENSING says otherwise for the project.
Private repos satisfy this rule trivially.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | git repo present, `main` is default/unborn branch | exit 0 | DEV-BOOTSTRAP-01 |
| 2 | `[ -s README.md ]` | non-empty file | DEV-BOOTSTRAP-02 |
| 3 | `[ -s CLAUDE.md ]` | non-empty file | DEV-BOOTSTRAP-03 |
| 4 | `[ -s GOVERNANCE.md ]` | non-empty file | DEV-BOOTSTRAP-04 |
| 5 | `[ -s .gitignore ]` | non-empty file | DEV-BOOTSTRAP-05 |
| 6 | `[ -x .git/hooks/pre-commit ] && [ -x .git/hooks/pre-push ]` | both executable | DEV-BOOTSTRAP-06 |
| 7 | `[ -f .coverage-baseline ]` (T2+) | file committed | DEV-BOOTSTRAP-07 |
| 8 | attestation: public ⇒ license file | explicit yes | DEV-BOOTSTRAP-08 |

**Remediation:** any missing item → run `/bootstrap-repo` (idempotent; it retrofits
without touching existing content) · `master` default → `git branch -m master main` and
update the GitHub default branch · hooks present but not executable → `chmod +x
.git/hooks/pre-commit .git/hooks/pre-push`.

## Worked Example

A freshly bootstrapped T2 Python repo, in full:

```
myproj/
├── .git/hooks/pre-commit    # from templates/scaffolds/_common/, executable
├── .git/hooks/pre-push      # from templates/scaffolds/_common/, executable
├── .gitignore               # .env, .venv/, __pycache__/, dist/, .DS_Store
├── .env.example             # only if a credential exists (SEC-SECRETS-02)
├── .coverage-baseline       # written by first ratchet run, committed
├── README.md                # what / why / run
├── CLAUDE.md                # structure, .venv/bin commands, gotchas
├── GOVERNANCE.md            # tier: T2, stacks, attestations (via /govern)
└── src/ + tests/            # per STK-PY-01
```

Hook install (what `/bootstrap-repo` runs):

```bash
cp ~/Dev/claude-code/governance/templates/scaffolds/_common/pre-commit .git/hooks/pre-commit
cp ~/Dev/claude-code/governance/templates/scaffolds/_common/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-commit .git/hooks/pre-push
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| "I'll `git init` once it works" | Pre-history secrets and dead ends are unrecoverable; hooks never ran | Bootstrap first, code second |
| README containing only the project name | Future-you re-derives what/why/run from source | Three honest sentences now; grow later |
| Writing GOVERNANCE.md at verify time | Tier was never actually classified; standards never loaded | `/govern` before feature work (C5) |
| Hooks "installed" but not executable | Git silently skips them; gates vanish without a trace | `chmod +x`; verification catches this |
| Habitual `git commit --no-verify` | Reintroduces every failure class the hooks retire | Fix the failure; reason in commit body if truly urgent |
| Public push, license "later" | Default copyright; contributors/users in legal limbo from day one | License file in the bootstrap commit |
| Copying another repo's `.gitignore` wholesale | Misses stack-specific artifacts; ignores nothing that matters here | Stack scaffold's ignore file |

## References

- `templates/scaffolds/_common/` — canonical hook sources this standard mandates.
- GitHub docs, "About the default branch" — `main` as the assumed default everywhere.
- choosealicense.com — the 5-minute license decision DEV-BOOTSTRAP-08 asks for.
- SEC-SECRETS, TST-RATCHET, DEV-DOCS, DEV-CI — the standards whose enforcement the
  bootstrap artifacts (.gitignore, baseline, hooks, docs) make possible.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
