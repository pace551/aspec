# ADR-0006: Detect LLM projects with an `llm` stack key and gate their evals

- **Status**: proposed
- **Date**: 2026-11-05
- **Deciders**: the maintainer

## Context

ASPEC's only eval rule is AI-ARCH-02: run a 10–50 case eval set before and after a prompt
or model change. It is attested, not checked, and advisory at T1. Nothing covers what goes
wrong in agents: wrong tool calls, nondeterminism (one passing run proves little),
uncalibrated LLM-as-judge graders, untested injection resistance, eval cases leaking into
prompts, and suites that go stale after a prompt edit. Selection is the second gap. No
stack key marks a project as an LLM application, so the AI family is `stacks: all`:
AI-SECURITY is pinned on every project at every tier, and AI-ARCH and AI-MODELS on every
T2+ project, whether or not it calls a model. At T1, AI-ARCH and AI-MODELS are pinned only
when a trigger word happens to be in the brief (`select-standards.py`: an advisory
standard needs a trigger even when its stack matches). A personal agent whose brief says
"inbox triage" gets no eval rules.

## Decision

We will add an `llm` stack key, a new standard AI-EVALS scoped to it, and a gate,
`checks/eval-ratchet.py`, that checks recorded eval results are fresh for the current
inputs and not below a committed baseline. The gate never calls a model.

- **Detection.** `/govern` sets `llm` when the dependencies name an LLM SDK by exact
  package name: `anthropic`, `@anthropic-ai/sdk`, `claude-agent-sdk`,
  `@anthropic-ai/claude-agent-sdk`, `openai`, `langchain`, `langchain-*`, `@langchain/*`,
  `langgraph`, `llama-index`, `litellm`, `pydantic-ai`, `dspy`, `ai` (Vercel AI SDK, exact
  name only), `google-genai`, `mistralai`, `ollama`. Otherwise it asks, for example when a
  project calls a model over raw HTTP. A `prompts/` directory alone is not a signal.
- **AI-EVALS** has `stacks: [llm]` and is `required` at every tier, so detection alone
  pins it at T1. Per-rule tier tags keep T1 small: an eval set of at least 10 cases, plus
  injection cases when the agent has side-effecting tools. The other rules (outcome-first
  grading with transcript checks, repeated isolated trials, grader calibration, held-out
  splits, the regression gate) are advisory at T1 and required at T2+. A production
  feedback loop is required at T3+.
- **Contract.** The project's runner writes `evals/results.json`:
  `{schema: 1, model, suites: {name: {kind: capability|regression|safety, cases, trials,
  pass_rate}}}`. Then `eval-ratchet.py --stamp` adds `inputs_sha256`, so runners never
  implement the hash. The inputs are the paths listed in the committed `evals/inputs`
  file (one per line: prompts, model config, tool definitions, cases). The list must
  include `prompts/` when that directory exists. The hash is SHA-256 over the sorted
  output of `git ls-files -z --cached --others --exclude-standard -- <inputs>`, as
  `path NUL sha256(working-tree bytes) LF` per file. `evals/results.json` and
  `.eval-baseline` are always excluded.
- **Gate.** `/verify-compliance` runs it read-only. It exits 1 in any of these cases:
  - `results.json` is missing (a C9 waiver covers an early prototype)
  - the hash is stale
  - a `safety` suite is below 1.0
  - `trials < 3` at T2+
  - a suite falls below its `.eval-baseline` value by more than a noise band of
    max(0.02, 2·√(2·p̂(1−p̂)/n)). Here n = cases × trials and p̂ = (baseline·n + 1)/(n + 2).
    This is a two-sample bound, because the baseline is itself a noisy run, and it is
    smoothed so that a baseline of 1.0 still gets a band. A 20 × 3 suite with a 1.0
    baseline still passes at 58/60 (band 0.046); a 10 × 1 suite with a 0.9 baseline
    still passes at 6/10 (band 0.33).
    Safety suites get no band: one gated action in any trial fails.
  - a suite in `.eval-baseline` is missing from `results.json`, so deleting or renaming
    a suite can't hide a regression
- **Baseline.** The gate never raises the baseline itself. A developer runs
  `--update-baseline` after a reviewed eval run and commits the result. Lowering a suite
  or removing one (a rename counts as a removal) needs a waiver, as for TST-RATCHET-03.
- **AI-ARCH-02** gains a see-also sentence pointing at AI-EVALS. It is a patch bump (no
  new requirement, per ADR-0004). Its tiering and attestation don't change: the
  attestation runs only at T2+. At T1 the rule is advisory, and AI-ARCH is pinned only
  by a trigger.

## Alternatives considered

- **Extend AI-ARCH**: AI-ARCH turns into a grab-bag, and its minor bump would fail every
  pinned project at once (ADR-0004).
- **A manifest flag (`llm_app: true`)**: it needs new selection code and a new `/govern`
  question. A stack key reuses stack intersection and dependency detection.
- **AI-EVALS advisory at T1**: stack matching alone would not pin it.
- **Attestation only**: a stale suite would look identical to a fresh one.
- **The runner declares inputs and computes the hash**: the runner could cover nothing,
  and every framework would have to reimplement the hash exactly.
- **Auto-ratchet up like coverage**: one lucky run on a small, nondeterministic suite
  would lock in a baseline that normal runs then fail.
- **Run evals in the verifier or CI**: every run would cost money (C6) and be
  nondeterministic.
- **Re-scope the AI family to `[llm]` now**: if detection misses a project, it silently
  loses AI-SECURITY.

## Consequences

LLM projects pick up AI-EVALS only when `/govern` re-runs and records `llm`; existing pins
are unaffected. A detected project fails `/verify-compliance` until it has an eval set
and stamped results, or a waiver. That is the intended T1 cost. The band trades sensitivity for
stability: a small suite catches only large drops, and the way to catch smaller ones is
more cases or trials, not a tighter band. Because the gate reads a single recorded run, a
developer could rerun the evals until one passes. AI-EVALS will require the recorded run
to be the first complete run after the change, which can only be attested. The gate only proves
freshness for the paths in `evals/inputs`. Whether that list covers the model config and
tool definitions is attested under AI-EVALS. Only `prompts/` is enforced. The gate runs
only from the governance venv, so project CI can't run it until it is vendored like
`coverage-ratchet.py`. The implementation PR adds:
- `standards/ai/ai-evals.md`
- `checks/eval-ratchet.py` and its tests
- `llm` in `checks/stack-keys.json` and in the stack-keys vocabulary of
  `templates/AUTHORING.md` (a test requires both lists to match)
- the `/govern` detection line
- selection tests
- the AI-ARCH see-also
- updated standard counts in `README.md` and `CLAUDE.md`

That PR also flips this ADR to accepted. Follow-ups, each needing its own ADR where the
framework's shape changes:
- eval sets for ASPEC's own skills
- vendoring the gate and adding a CI fragment for T3+
- re-scoping the AI family to `[llm]`
