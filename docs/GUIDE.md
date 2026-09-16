# Developer Guide — ASPEC

**Agent Safety, Performance, Enforcement & Compliance**

ASPEC makes every Claude Code deliverable secure, tested, observable, and maintainable
**by rule rather than by mood** — scaled to how much the project matters. This guide is
the human walkthrough. The README is the elevator pitch; this is how you actually live
with it.

---

## 1. The mental model (five pieces)

```
CONSTITUTION  ──►  always applies, every task (10 articles, ~2 pages)
TIERS         ──►  how much governance this project gets (T1→T4)
STANDARDS     ──►  67 rulebooks; only the relevant ones load (selection)
GOVERNANCE.md ──►  per-project manifest: tier, pinned standards, waivers, attestations
ENFORCEMENT   ──►  H hooks block actions · G gates block "done" · A attestations record drift
```

1. **The Constitution** (`constitution/CONSTITUTION.md`) is ten invariants — secrets
   never touch git, done means verified, test-first for core logic and bugfixes, spend
   requires consent, deviations are visible. It applies to a 10-line script and a
   commercial product equally. Read it once; it's short on purpose.

2. **Tiers** (`constitution/tiers.md`) scale everything else:

   | Tier | What it is | Governance weight |
   |---|---|---|
   | T1 | Personal tool, only you run it | Constitution + secrets + git hygiene hard; rest advisory. No CI. |
   | T2 | Research/analysis informing decisions | + test-first analytical core, reproducibility, leakage guards |
   | T3 | Deployed / has users, no revenue | Full SEC/OPS/UX; CI mandatory; staging; a11y+perf gates |
   | T4 | Money, third-party PII, public launch | + legal, retention, tested restores, license audit, MFA, DMARC |

   Classification is a **first-match rubric**, not a judgment call: payments/PII → T4;
   deployed-with-reach or other users → T3; output-is-analysis → T2; else T1. Ambiguity
   costs exactly one question — never a silent guess.

3. **Standards** live in `standards/` — 11 families (security, testing, architecture,
   stacks, infra, operations, process, UX, data, AI, legal). Each has RFC-2119 rules
   with permanent IDs (`SEC-SECRETS-01`), per-tier applicability, executable
   verification commands, a worked example, and an anti-patterns table. You never read
   all 67 — selection (below) picks the handful that apply.

4. **GOVERNANCE.md** in each project is the contract: its tier, the standard versions it
   is pinned to, waivers, external-action approvals, attestations, `last_verified`.
   Machine-written by the skills, human-readable, hand-editable.

5. **Enforcement is layered** — nothing is advisory-and-invisible:
   - **H (hard)**: git pre-commit/pre-push hooks, Claude Code hooks. Block the action.
   - **G (gate)**: CI jobs and `/verify-compliance` commands. Block "done".
   - **A (attestation)**: an explicit yes/no self-report per advisory rule, written into
     GOVERNANCE.md. Doesn't block — makes drift visible instead.

---

## 2. The five skills (your entire interface)

You interact with the framework almost exclusively through slash commands:

| Skill | When | What it does |
|---|---|---|
| **/govern** | Start of any chunky task; project created or re-scoped | Classifies tier, detects stacks, selects standards, writes/updates GOVERNANCE.md, emits a compliance brief |
| **/bootstrap-repo** | New repo, or retrofitting an ungoverned one | Stack scaffold + git hooks + tier-appropriate CI + seeded CLAUDE.md/GOVERNANCE.md/.env.example; proves its own gates fire before handover |
| **/verify-compliance** | Before anything is called done | Runs every pinned standard's verification commands; pass/fail table; collects attestations; stamps `last_verified` |
| **/harvest-learnings** | End of a governed task, or when a rule felt wrong | Governance retro → structured candidate note in the Obsidian vault Inbox |
| **/evolve-standards** | Quarterly; monthly fast-lane for AI/deps; ad hoc | Promotes vault candidates into versioned standard diffs (you approve each), staleness sweep, self-lint |

`write-spec` and `implement-spec` are wired in: specs get a `## Governance` section from
a `/govern` run, scaffolding delegates to `/bootstrap-repo`, and `implement-spec`
**cannot declare done while `/verify-compliance` fails**.

---

## 3. Lifecycle walkthroughs

### 3a. New project, full flow

```
/write-spec mytool          # Phase 0 runs /govern → tier + standards land in the spec
/implement-spec mytool      # scaffolds via /bootstrap-repo, builds, then MUST pass /verify-compliance
```

What you'll see along the way:

1. `/govern` states the tier and *why* (which rubric line fired), lists the hard rule
   IDs for the task, and writes GOVERNANCE.md. If tier is ambiguous you get one
   question.
2. `/bootstrap-repo` copies `templates/scaffolds/{stack}/`, installs `.githooks/`
   (pre-commit: secret scan + lint · pre-push: tests + coverage ratchet), vendors the
   check scripts into `.governance/`, composes CI from fragments (T3+ only — T1 gets
   hooks, no CI), then **proves the gates bite** (a canary secret commit must be
   rejected) before stopping for your review.
3. Implementation proceeds normally — the standards you'd care about are in context.
4. `/verify-compliance` at the end: every H/G command runs, the table must be all
   PASS/WAIVED, attestations get recorded, `last_verified` is stamped.

### 3b. Chunky task in an existing governed repo

```
/govern        # re-confirms tier, diffs pins, briefs the session (cheap — one script call)
…do the work…
/verify-compliance
```

### 3c. Retrofitting an existing ungoverned repo

`/bootstrap-repo` in retrofit mode: adds only what's missing (never overwrites), reports
every file touched. Then `/govern` + `/verify-compliance` as usual.

### 3d. The project's exposure changes

A T1 tool gets a URL. A notebook becomes a dashboard. A product takes its first payment.
**Re-run `/govern`** — that's the escalation mechanism. It re-classifies, swaps the pin
set, and `/bootstrap-repo` can retrofit the newly required CI/hooks. Operating at the
old tier because re-governing feels like ceremony is the one move the framework forbids.

---

## 4. Reading GOVERNANCE.md

```yaml
tier: T2                          # classification (+ tier_override if you overruled it)
classified: 2026-07-22
stacks: [python, sqlite]
standards:                        # THE PIN SET — versions this project is governed by
  - {id: SEC-SECRETS, version: 1.0.1}
  - {id: STK-PY, version: 1.0.1}
waivers:                          # rule-scoped exemptions, expiry MANDATORY (≤180d)
  - {rule_id: STK-PY-05, reason: "CVE unreachable…", expires: 2026-10-01, granted_by: James}
external_action_approvals:        # your consent record for emails/deploys/API calls (C7)
pii_inventory: n/a                # T3+: what personal data lives where
last_verified: 2026-07-22         # stamped by a fully-green /verify-compliance
attestations:                     # advisory-rule self-reports, honest ones
  - {rule_id: STK-PY-07, followed: true, date: 2026-07-22}
```

Two things worth internalizing:

- **Pins make evolution non-breaking.** Standards move forward in this repo; your
  project stays on its pinned versions until a `/govern` run offers the upgrade and you
  take it. A `WARN` about pin drift in the verify table is that offer, not an error.
- **Enforcement is wider than context.** `/govern` only *loads* the standards relevant
  to today's task (token budget), but `/verify-compliance` runs **everything pinned**.
  You can't dodge a rule by not reading it.

## 5. Waivers, attestations, and honest drift

- **A required check fails and you disagree with the rule** → don't weaken the check
  (no lowering baselines, no lint-ignores, no deleting jobs). Draft a waiver — one
  rule ID, one reason, an expiry — and approve it yourself in GOVERNANCE.md. Expired
  waivers fail the gate; renewal is a fresh decision.
- **An advisory rule you consciously didn't follow** → attest `followed: false` with a
  note. That's allowed. Silent drift is the only unforgivable failure mode (C9).
- **The same rule keeps getting waived** → that's evidence the rule is miscalibrated.
  `/harvest-learnings` it; `/evolve-standards` fixes the rule instead of accumulating
  exemptions.

## 6. The evolution loop

```
friction in a session ──► /harvest-learnings ──► vault Inbox note (status: candidate)
                                                        │
   quarterly (or monthly fast-lane for AI/deps) ──► /evolve-standards
                                                        │
                              proposed diffs ──► YOU approve ──► version bump + changelog
                                                        │
                                        build-index regenerates · projects upgrade via /govern
```

Standards change **only** through this path (C10). The mechanical guarantee: 
`checks/build-index.py` hashes every standard and refuses to index a content change
without a version bump — you cannot silently edit a rule.

## 7. When things go wrong

| Symptom | What it means / do |
|---|---|
| `/verify-compliance` FAIL rows | Fix the code, not the check. Each standard's Verification section has remediation hints. Genuinely disagree → waiver (§5). |
| `run-verification: no GOVERNANCE.md` | Run `/govern` first. |
| `build-index: REFUSED … version still X` | You edited a standard without bumping `version` + changelog. Bump it — that's the C10 gate doing its job. |
| WARN: pinned 1.0.0, repo has 1.1.0 | Informational. Re-run `/govern` to upgrade deliberately, or stay pinned. |
| Pre-commit rejects a "secret" that's a fixture | Make it an obvious fake (contain `EXAMPLE`), or add a scoped `.gitleaksignore` entry with a comment. |
| Emergency bypass | `git commit --no-verify` exists and isn't blocked — but CI/verify will catch it, and the honest move is a waiver, not a bypass. |
| A scanner isn't installed | Checks degrade with a printed warning at T1/T2 and fail loud at T3+. `brew install gitleaks tflint checkov hadolint trivy` as needed. |

## 8. Repo map (where to look things up)

```
constitution/     CONSTITUTION.md · tiers.md · glossary.md (RFC-2119, H/G/A, ID scheme)
INDEX.md          human catalog of all 67 standards (generated — browse, don't edit)
standards/        the rulebooks; each ≤ ~300 lines, worked examples + anti-patterns
templates/        standard-template.md (format contract) · AUTHORING.md (how to write one)
                  · GOVERNANCE/adr/waiver templates · ci/ fragments · scaffolds/
skills/           canonical skill sources (installed copies live in ~/.claude/skills)
checks/           the machinery: select-standards.py · run-verification.py ·
                  build-index.py · lint-framework.py · secret-scan.sh · per-standard scripts
hooks/            Claude Code hook scripts (wired via checks/install.sh --hooks)
examples/         one verified-green project per stack + the noncompliant fixture
decisions/        ADRs for framework-shape choices (why a dedicated repo, why tiers, why the index)
```

**Maintenance commands** (run from this repo):

```bash
python3 checks/build-index.py      # regenerate catalog after standard edits
python3 checks/lint-framework.py   # full self-lint — must be clean before commit
checks/install.sh                  # refresh installed skills after editing skills/
checks/install.sh --hooks          # wire the global Claude Code hooks (asks nothing twice — idempotent)
```

## 9. Design commitments worth knowing (the "why")

- **Selective loading is the load-bearing wall** (ADR-0003): no agent ever loads the
  whole framework — constitution + a filtered brief ≤ ~15k tokens, measured.
- **Deterministic scripts verify; the LLM complies.** Every gate is a script with an
  exit code, never a vibe. The verify table is trustworthy because no model judgment
  sits between a check and its result.
- **T1 stays light by rubric, not by mood** — over-governing personal scripts is treated
  as a bug (harvest it if you feel it).
- **Rule IDs are permanent.** Waivers, attestations, and your memory can reference
  `SEC-SECRETS-05` forever; retirement keeps the number.
