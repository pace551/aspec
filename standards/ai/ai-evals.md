---
id: AI-EVALS
title: LLM and Agent Evaluations
family: AI
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [llm]
triggers:
  - eval
  - evals
  - evaluation
  - agent
  - agentic
  - tool use
  - trajectory
  - transcript
  - llm-as-judge
  - grader
  - red team
  - pass@k
  - eval-ratchet
requires: []
verification:
  - cmd: '"$GOVERNANCE_DIR/.venv/bin/python" "$GOVERNANCE_DIR/checks/eval-ratchet.py" --check --tier T1'
    expect: "exit 0 — stamped evals/results.json with ≥10 cases and every safety suite at 1.0 (staleness and baseline drops only warn at T1)"
    layer: G
    rules: [AI-EVALS-01, AI-EVALS-06]
    tiers: [T1]
  - cmd: '"$GOVERNANCE_DIR/.venv/bin/python" "$GOVERNANCE_DIR/checks/eval-ratchet.py" --check --tier T2'
    expect: "exit 0 — results fresh for evals/inputs, ≥3 trials, safety suites at 1.0, no suite missing or below .eval-baseline beyond the noise band"
    layer: G
    rules: [AI-EVALS-01, AI-EVALS-03, AI-EVALS-05, AI-EVALS-06]
    tiers: [T2, T3, T4]
  - cmd: "attest: the eval set is built from real inputs (happy path, edge cases, known failures, should-not-trigger cases), each case has a reference solution, and every production failure becomes a case"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-EVALS-01]
  - cmd: "attest: agent evals grade the final outcome first, and check transcripts for forbidden calls and step/token budgets rather than exact tool sequences"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-EVALS-02]
    tiers: [T2, T3, T4]
  - cmd: "attest: every trial starts from a clean, isolated environment, and the reported metric (pass@k or pass^k) is the one the suite's purpose calls for"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-EVALS-03]
    tiers: [T2, T3, T4]
  - cmd: "attest: graders are deterministic where possible; every LLM judge has a written rubric, a pinned model, and a recorded agreement rate against human-labeled cases"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-EVALS-04]
    tiers: [T2, T3, T4]
  - cmd: "attest: evals/inputs covers the prompts, model config and tool definitions, and the recorded results are the first complete run after the latest change (no rerunning until it passes)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-EVALS-05]
    tiers: [T2, T3, T4]
  - cmd: "attest: an agent with side-effecting tools has safety cases for every untrusted input channel and every gated tool"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-EVALS-06]
  - cmd: "attest: a held-out split is never used for prompt iteration, eval cases hold no live PII, and no case is copied into a prompt or few-shot example"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-EVALS-07]
    tiers: [T2, T3, T4]
  - cmd: "attest: production traces are sampled and reviewed, failures become eval cases, and online task-success and escalation rates are tracked"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-EVALS-08]
    tiers: [T3, T4]
last_review: 2026-11-06
---

# LLM and Agent Evaluations (AI-EVALS)

## Abstract

What makes "the agent works" a measured claim instead of an anecdote. Applies to any
project on the `llm` stack (ADR-0006). Each LLM task or agent has an in-repo eval set.
Agents are graded on the outcome first, with transcript checks second, over repeated,
isolated trials. LLM judges are calibrated against humans. Safety suites probe injection
and gated tools and must pass every time. `checks/eval-ratchet.py` fails verification
when the recorded results are stale for the current prompts, or when a suite drops below
its committed baseline by more than noise. At T1 that means a small stamped eval set plus
safety cases; the full discipline applies at T2+; production feedback at T3+.

## Normative Rules

### AI-EVALS-01 — Every LLM task and agent MUST have an in-repo eval set built from real inputs

**Tiers**: all required — **Layer**: G

Cases live under `evals/` and cover the happy path, edge cases, known failures, and the
cases where a behavior should *not* trigger (an agent that searches on every question is
as broken as one that never does). Start with the real failures you already know about:
20–50 is a good first set, and fewer than 10 cases in total fails the gate. Each case
has a reference solution that passes its graders, which proves the case is solvable: a
case nobody ever passes is usually a broken case, not a weak model. Every production
failure becomes a case before it is fixed (Constitution C3, applied to prompts).

### AI-EVALS-02 — Agent evals MUST grade the outcome first and the transcript second

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

The primary grade is the final state the agent leaves behind, checked by deterministic
code: the row in the database, the file on disk, the message in the outbox. Transcript
checks come second and assert properties, not paths: no forbidden tool was called,
arguments validated, the run stayed within its step and token budget. Asserting an exact
tool-call sequence fails agents that find a valid different route and makes every
prompt change look like a regression. The transcript is also where you find out whether
a passing score is real (AI-EVALS-04).

### AI-EVALS-03 — Each case MUST run at least three isolated trials at T2+

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

Model output varies between runs, so a single pass proves little. Every trial starts
from a clean environment: no shared files, caches, git history, or rate-limit state left
by an earlier trial, which can make failures correlated or scores inflated. Report the
metric the suite's purpose calls for and say which it is: pass@k (at least one of k
succeeds) for tools where one success is enough, pass^k (all k succeed) for agents users
rely on every time. The runner records model ID, sampling parameters and seed with the
results (`AI-ARCH-05`); the gate checks `trials ≥ 3` at T2+.

### AI-EVALS-04 — Graders MUST be deterministic where possible, and LLM judges MUST be calibrated

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Use code graders (exact match, schema checks, state assertions) wherever the answer is
checkable. An LLM judge is for what code can't check, and then it gets a written rubric,
a pinned model (`AI-MODELS-04`), one dimension per judge call, and an explicit "unknown"
option, so it isn't forced to guess. Before a judge's scores gate anything, measure its
agreement against human-labeled cases and record the rate next to the rubric. Read a
sample of transcripts whenever a score moves: until someone has read them, a score could
be measuring a grader bug.

### AI-EVALS-05 — Prompt, model and tool changes MUST NOT ship on stale or regressed results

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

`evals/inputs` lists everything the results depend on: prompts, model config, tool
definitions, cases. `eval-ratchet.py --stamp` hashes the tracked files under them into
the runner's fresh `evals/results.json`, and any later change to those files makes the
results stale. Stamping refuses results that are already stamped, an entry that matches
no tracked file, and untracked files under an entry, so every clone computes the same
hash. Each suite is compared with the committed `.eval-baseline`, which records its
kind, pass rate, cases and runs (cases × trials). A drop counts only beyond a noise band
sized by the baseline's runs, so a 20 × 3 suite at 1.0 still passes at 58/60. Raising
the baseline is a deliberate `--update-baseline` and commit. Lowering a suite, removing
it, cutting its cases or runs, or relabelling a safety suite needs `--allow-lower` and a
waiver (C9), as for `TST-RATCHET-03`. The recorded run is the first complete run after
the change. Rerunning until the noise lands on a pass, or stripping the stamp to re-stamp
old results, defeats the gate, and only this attestation covers it.

### AI-EVALS-06 — Agents with side-effecting tools MUST have safety suites that pass every trial

**Tiers**: all required — **Layer**: G

When an agent can send, delete, post, pay or deploy, a `kind: safety` suite holds
injection cases for every channel that brings untrusted content into the prompt (web,
email, documents, tool results) and cases that try to reach each gated tool without
approval. These are the tests for `AI-SECURITY-01/02`. A safety suite has no noise band:
one gated action in any trial is a real finding, so the gate requires a pass rate of
exactly 1.0 at every tier. An agent with read-only tools may have none.

### AI-EVALS-07 — Eval sets MUST stay clean: held-out cases, no live PII, no leakage into prompts

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Keep a held-out split that is never looked at while iterating on a prompt, and
re-score on it before shipping. A prompt tuned against every case it is scored on will
overfit to them. Cases are fixtures: synthetic or scrubbed, never live personal data
(`DATA-PRIVACY-03`). No eval case is pasted into a prompt or used as a few-shot example,
because that scores the model on the answers it was shown.

### AI-EVALS-08 — Production traffic MUST feed the eval set at T3+

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Offline evals only cover the inputs someone thought of. Sample and review production
traces on a schedule, turn each failure into a case (AI-EVALS-01), and track online
task-success and escalation or retry rates in the standard logs (`OPS-OBS`). If online
success drops while the offline evals stay green, the eval set no longer matches real
usage. That is a finding about the evals, not noise.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `eval-ratchet.py --check --tier T1` (T1) | stamped results, ≥10 cases, safety at 1.0 | AI-EVALS-01, -06 |
| 2 | `eval-ratchet.py --check --tier T2` (T2+) | fresh, ≥3 trials, safety at 1.0, no drop beyond noise, no missing suite | AI-EVALS-01, -03, -05, -06 |
| 3 | attest: real-input cases, reference solutions | explicit yes | AI-EVALS-01 |
| 4 | attest: outcome-first grading (T2+) | explicit yes | AI-EVALS-02 |
| 5 | attest: isolated trials, stated metric (T2+) | explicit yes | AI-EVALS-03 |
| 6 | attest: deterministic graders, calibrated judges (T2+) | explicit yes | AI-EVALS-04 |
| 7 | attest: inputs complete, first run recorded (T2+) | explicit yes | AI-EVALS-05 |
| 8 | attest: safety cases per channel and gated tool | explicit yes | AI-EVALS-06 |
| 9 | attest: held-out split, no PII, no leakage (T2+) | explicit yes | AI-EVALS-07 |
| 10 | attest: production feedback loop (T3+) | explicit yes | AI-EVALS-08 |

Exit 1 is a finding; exit 2 means the gate couldn't read an input (an incomplete scan,
never a pass).

**Remediation:** `stale` → rerun the evals (the runner writes a fresh, unstamped file),
then `eval-ratchet.py --stamp` · `untracked files` / `matches no tracked file` → commit,
gitignore or fix the path in `evals/inputs` · `fewer than its baseline` or `was a safety
suite` → restore the suite, or accept it with `--update-baseline --allow-lower` and a
waiver · `is a symlink` → make `evals/`, `evals/results.json` and `.eval-baseline`
regular files · `below
baseline` → read the failing transcripts, then fix the prompt or roll it back. Lower the
baseline only with a waiver · `missing from results.json` → restore the suite, or drop
it with `--update-baseline --allow-lower` and a waiver · `trials < 3` → raise the
runner's repeat count · `safety` below 1.0 → treat as an injection finding
(`AI-SECURITY`), not a flaky test · `no evals/inputs` → list the prompt, model-config
and tool-definition paths, one per line.

## Worked Example

```text
prompts/triage.md            # AI-ARCH-01 prompt file
config/model.toml            # pinned model id and sampling params
tools/schema.json            # tool definitions the agent sees
evals/inputs                 # what the results depend on (committed)
evals/cases/triage.jsonl     # regression cases (from real inbox failures)
evals/cases/injection.jsonl  # safety cases: hostile email bodies, gated-tool bait
evals/run.py                 # the project's runner: writes evals/results.json
evals/results.json           # written by the runner, stamped by eval-ratchet.py
.eval-baseline               # committed; changed only by --update-baseline
```

```text
# evals/inputs
prompts/
config/model.toml
tools/
evals/cases/
```

```json
{"schema": 1, "model": "{pinned model id}",
 "suites": {
   "triage":    {"kind": "regression", "cases": 24, "trials": 3, "pass_rate": 0.986},
   "injection": {"kind": "safety",     "cases": 12, "trials": 3, "pass_rate": 1.0},
   "drafting":  {"kind": "capability", "cases": 15, "trials": 3, "pass_rate": 0.42}},
 "inputs_sha256": "…written by --stamp…"}
```

```python
# one injection case, graded on outcome and transcript, never on the exact path
def grade(trial) -> bool:
    outbox_untouched = trial.env.outbox() == []          # outcome: nothing was sent
    no_gated_call = "send_email" not in trial.tool_names() # transcript: property, not order
    return outbox_untouched and no_gated_call
```

```bash
.venv/bin/python evals/run.py --trials 3            # project runner
"$GOVERNANCE_DIR/.venv/bin/python" "$GOVERNANCE_DIR/checks/eval-ratchet.py" --stamp
"$GOVERNANCE_DIR/.venv/bin/python" "$GOVERNANCE_DIR/checks/eval-ratchet.py" --check --tier T2
# after a reviewed improvement:
"$GOVERNANCE_DIR/.venv/bin/python" "$GOVERNANCE_DIR/checks/eval-ratchet.py" --update-baseline
git add evals/results.json .eval-baseline
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| "Tried it on three prompts, looks better" | An anecdote against a regression across the set | Stamped suite before and after (AI-EVALS-05) |
| Asserting the exact tool-call sequence | Fails valid alternate routes; every prompt edit "regresses" | Grade outcome, assert transcript properties (AI-EVALS-02) |
| One trial per case | Nondeterminism reads as signal | ≥3 isolated trials, stated pass@k/pass^k (AI-EVALS-03) |
| Trials share a sandbox or git history | Correlated failures; the agent reads earlier trials' answers | Clean environment per trial |
| Uncalibrated LLM judge as the only grader | Measures the judge's taste, not the task | Rubric, pinned model, agreement vs humans (AI-EVALS-04) |
| Rerun the evals until the score clears the band | Selects on noise; the gate passes a real regression | Record the first complete run; add trials instead |
| Deleting the suite that started failing | Hides the regression | Missing suites fail; removal needs a waiver |
| Treating a 29/30 safety suite as flaky | One gated action is one exfiltration | Safety suites at 1.0, every trial (AI-EVALS-06) |
| Eval cases reused as few-shot examples | Scores the model on answers it was shown | Held-out split, no leakage (AI-EVALS-07) |
| Offline evals as the only signal after launch | Real usage drifts from the cases | Production traces feed the set (AI-EVALS-08) |

## References

- Anthropic, "Demystifying evals for AI agents" (2026-01-09) — the vocabulary used
  here (task, trial, grader, transcript, outcome), outcome-first grading,
  capability vs regression suites, pass@k vs pass^k, isolated trials, and reading
  transcripts. Re-read it at review time (Constitution C8).
- OWASP Top 10 for LLM Applications and the OWASP Agentic Top 10 — threat lists that
  AI-EVALS-06 safety suites turn into test cases (via `AI-SECURITY-05`).
- ADR-0006 — the `llm` stack key, the `evals/results.json` contract, the hash algorithm,
  and the noise band `eval-ratchet.py` implements.

## Changelog

- **1.0.0** (2026-11-06) — Initial version (ADR-0006).
