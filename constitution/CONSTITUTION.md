# The Constitution

Invariants for **every** task Claude Code performs for James, regardless of tier, stack, or
project. This file is small on purpose: it is always loaded. Everything conditional lives in
`standards/` and is selected per-task by `/govern` via `index.json`.

Terms MUST / SHOULD / MAY are RFC-2119 (see `glossary.md`). Enforcement layers: **H** = hard
hook (blocks the action), **G** = CI/verify gate (blocks "done"), **A** = advisory with
manifest attestation.

## C1 — Secrets never touch git  (H)

No credential, token, API key, or private key is ever written to a tracked file. Real secrets
live in `.env` (gitignored) or a vault; every repo ships `.env.example` with placeholder
values only. A leaked-then-removed secret is still leaked: rotate it, don't just delete it.
Detail: `SEC-SECRETS`.

## C2 — Done means verified  (G)

Work is not "done" when the code is written; it is done when `/verify-compliance` passes for
the project's tier and every claim in the completion summary is backed by an executed command
or test. Never report success on inference. If verification was skipped or failed, say so
plainly. Detail: `TST-VERIFY`.

## C3 — Test-first for core logic and all bugfixes  (G)

New core/business logic and every bugfix start with a failing test that the change makes
pass. Glue, scaffolding, and exploratory code MAY be tested after the fact. Coverage never
decreases: the ratchet (`TST-RATCHET`) compares against the committed baseline, not a fixed
percentage.

## C4 — Git hygiene  (G)

Conventional-commit messages (`feat:`, `fix:`, `docs:`, `chore:`, …); small, coherent
commits; rebase-merge to keep history linear; never force-push a shared branch; never commit
directly to `main` in T3+ repos. PR descriptions state what changed, why, and how it was
verified (evidence, not adjectives). Detail: `DEV-GIT`.

## C5 — Tier before task  (A)

Any chunky task starts with `/govern`: classify the tier (ask at most one clarifying
question when ambiguous — never silently guess), record it in `GOVERNANCE.md`, and load only
the standards that apply. T1 stays light **by rubric, not by mood**; a T1 tool that grows
users or internet exposure gets re-governed, not quietly upgraded.

## C6 — Spend requires consent  (H for infra, A otherwise)

Free/open data and tools by default. Anything that creates recurring cost — AWS resources,
paid LLM usage at scale, SaaS subscriptions — requires explicit approval first, and a budget
alarm MUST exist before the first deploy (`OPS-FINOPS`).

## C7 — External side effects gate on a human  (H)

Sending email, posting to external APIs, uploading files, deploying, or anything else that
leaves the machine and is visible to others requires an explicit human go — once per
project-and-action-kind, recorded in `GOVERNANCE.md`. Dry-run modes are the default until
that approval exists.

## C8 — Current facts, not remembered facts  (A)

Model names, pricing, API parameters, tool versions, security advisories: consult the live
source (`/claude-api` skill, official docs, registry) at time of use. Never answer from
training memory when a fresh lookup is one command away. Detail: `AI-MODELS`, `DEV-DEPS`.

## C9 — Deviations are visible  (A)

Skipping a required rule needs a waiver in `GOVERNANCE.md` with a reason **and an expiry**.
Advisory rules that were consciously not followed get a line in the compliance
self-attestation. Silent drift is the only unforgivable failure mode — the framework can
absorb any honest deviation.

## C10 — The framework itself evolves by rule  (G)

Standards change via version bump + changelog entry; `checks/build-index.py` refuses to
index an edited-but-unbumped file. Learnings are captured to the Obsidian vault Inbox and
promoted by `/evolve-standards`, never patched ad hoc into an agent's memory.
