---
id: AI-ARCH
title: LLM Application Architecture
family: AI
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - prompt
  - llm
  - eval
  - agent
  - context window
  - token budget
  - structured output
  - rag
  - completion
  - temperature
requires: []
verification:
  - cmd: "attest: every production prompt lives as a versioned in-repo file; no prompt string literals scattered in code"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-ARCH-01]
  - cmd: "attest: a graded eval set exists and was run before and after the latest prompt/model change"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-ARCH-02]
    tiers: [T2, T3, T4]
  - cmd: "attest: prompt context is assembled deliberately with a measured, capped token budget"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-ARCH-03]
    tiers: [T3, T4]
  - cmd: "attest: every LLM output is parsed and validated by deterministic code before use"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-ARCH-04]
    tiers: [T2, T3, T4]
  - cmd: "attest: temperature, seed (where supported), and model id are recorded alongside reproducibility-sensitive results"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-ARCH-05]
    tiers: [T2]
  - cmd: "attest: fallback behavior is defined and tested for LLM timeout, refusal, and malformed output"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-ARCH-06]
    tiers: [T2, T3, T4]
  - cmd: "attest: per-call token usage and cost are logged"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [AI-ARCH-07]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# LLM Application Architecture (AI-ARCH)

## Abstract

House architecture for anything that calls an LLM: prompts are versioned in-repo artifacts,
changes to them are gated by a small graded eval set (T2+), context is assembled under a
measured token budget, and every model call is wrapped in a deterministic harness that
validates, parses, and retries — the LLM reasons, deterministic code decides. Temperature,
seed, and model ID are recorded for reproducibility-sensitive work; failure behavior
(timeout, refusal, malformed output) is designed, not discovered; per-call costs are
logged at T3+. The oracle suite's in-session-LLM-vs-baseline grading is the house example
of the eval discipline.

## Normative Rules

### AI-ARCH-01 — Prompts MUST be versioned in-repo artifacts, not scattered string literals

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Every production prompt (system prompt, templates, few-shot examples) lives in a dedicated
file — `prompts/extract_v2.md`, `prompts/system.txt` — loaded by code, so a prompt change
is a reviewable diff with history, revertible like any other code change. Inline f-strings
may *interpolate variables into* a loaded template; they must not *be* the prompt.
Multi-variant experiments keep each variant as its own named file, so eval results
(AI-ARCH-02) attach to an identifiable artifact.

### AI-ARCH-02 — Prompt and model changes MUST pass the eval set before shipping

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Each LLM task gets a small graded eval set — 10–50 input/expected-output cases with a
scoring rule — run before and after any prompt or model change; the change ships only if
the score doesn't regress. "Looks better on the one example I tried" is not evidence
(Constitution C2 applies to prompts too). The house example is oracle's
in-session-LLM-vs-baseline grading: the LLM signal is scored against a dumb baseline on
held-out cases, so an "improvement" has to beat something real. Eval cases are fixtures —
no live PII in them (`DATA-PRIVACY-03`).

### AI-ARCH-03 — Context MUST be assembled deliberately under a measured token budget

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Every call site has a stated budget (prompt + retrieved context + expected output ≤ N
tokens), the assembly code measures actual usage (the API returns token counts — log them,
AI-ARCH-07), and retrieval/history is truncated by explicit policy (most-relevant first,
oldest dropped) rather than by whatever happens to fit. "Stuff everything in and let the
window sort it out" fails twice: cost scales with waste, and models attend worse to
bloated context.

### AI-ARCH-04 — LLM calls MUST be wrapped in a deterministic harness

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

The LLM reasons; deterministic code decides. Structure outputs via tool-use/JSON schema
where the provider supports it, then validate at the boundary with pydantic (Python) or
zod (TypeScript) — `SEC-INPUT`'s validate-at-the-boundary rule applies to LLM output
exactly as to user input. On validation failure: bounded retry (with the error fed back),
then the defined fallback (AI-ARCH-06) — never `except: pass` around a model call, never
raw `json.loads` straight into business logic. Free-text outputs get their own
deterministic acceptance checks (length, format, allowed values).

### AI-ARCH-05 — Temperature, seed, and model ID MUST be recorded for reproducibility-sensitive work

**Tiers**: T1 advisory · T2 required · T3–T4 advisory — **Layer**: A (attestation)

T2 research conclusions must be re-derivable: every run that feeds a result records model
ID, temperature, seed (where the provider supports it), and prompt file version alongside
the output — the LLM-call analog of T2's pinned-deps-and-seeds posture (`tiers.md`).
Sampling parameters are set explicitly, never left to provider defaults, which change.
Advisory at T3/T4 because product paths care about regression (AI-ARCH-02), not
re-derivation.

### AI-ARCH-06 — Fallback behavior MUST be defined for LLM failure

**Tiers**: T1 advisory · T2–T4 required — **Layer**: A (attestation)

Timeouts, refusals, rate limits, and still-malformed-after-retry outputs are normal
operating conditions, not exceptions. Each call site declares its policy per `ARC-ERRORS`:
retry budget, then one of — degrade (rule-based fallback, cached last-good), queue for
later, or fail loudly to the user. The one banned behavior is silently treating a failed
call as an empty-but-valid answer; in research pipelines a failed call is a missing data
point, recorded as such, never a zero.

### AI-ARCH-07 — Per-call token usage and cost MUST be logged at T3+

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Every production call logs model ID, input/output token counts, computed cost, latency,
and a call-site tag — into the standard structured logs (`OPS-OBS`), so cost per feature
is a query, not a reconstruction. This is the per-call ground truth the `OPS-FINOPS`
spend caps (`AI-MODELS-06`) alarm against; without it the first sign of a runaway retry
loop is the monthly invoice.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | attest: prompts are versioned in-repo files | explicit yes | AI-ARCH-01 |
| 2 | attest: eval set run before/after latest change (T2+) | explicit yes | AI-ARCH-02 |
| 3 | attest: context measured + capped (T3+) | explicit yes | AI-ARCH-03 |
| 4 | attest: outputs validated by deterministic harness (T2+) | explicit yes | AI-ARCH-04 |
| 5 | attest: temp/seed/model recorded for results (T2) | explicit yes | AI-ARCH-05 |
| 6 | attest: fallbacks defined for timeout/refusal/malformed (T2+) | explicit yes | AI-ARCH-06 |
| 7 | attest: per-call cost logged (T3+) | explicit yes | AI-ARCH-07 |

**Remediation:** prompt literals in code → extract to `prompts/`, load by path · no eval
set → write 10 cases from real inputs before the next prompt change · unvalidated output →
add a pydantic/zod model at the call boundary with bounded retry · silent failure path →
decide degrade/queue/fail-loud and implement it.

## Worked Example

Minimal deterministic harness (Python, pattern from the oracle suite):

```python
from pydantic import BaseModel, ValidationError

class Verdict(BaseModel):
    direction: str          # checked against {"up", "down", "flat"} below
    confidence: float       # 0..1

PROMPT = (PROMPTS_DIR / "verdict_v3.md").read_text()   # AI-ARCH-01

def call_llm(fields: dict) -> Verdict | None:
    for attempt in range(2):                            # bounded retry
        raw = client.structured(PROMPT, fields, schema=Verdict)   # tool-use/JSON schema
        log.info("llm_call", model=MODEL_ID, in_tok=raw.usage.input,
                 out_tok=raw.usage.output, cost=raw.cost, site="verdict")  # AI-ARCH-07
        try:
            v = Verdict.model_validate(raw.content)     # AI-ARCH-04 boundary
            if v.direction in {"up", "down", "flat"} and 0 <= v.confidence <= 1:
                return v
        except ValidationError as e:
            fields = {**fields, "prior_error": str(e)}  # feed error back, retry once
    return None                                         # AI-ARCH-06: missing data point,
                                                        # recorded — never a fake "flat"
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Prompt as a 60-line f-string inside a function | Unreviewable, undiffable, untestable | In-repo prompt file + interpolation (AI-ARCH-01) |
| "The new prompt seems better" → ship | One anecdote vs a regression across the case set | Run the eval set before/after (AI-ARCH-02) |
| `json.loads(response)` into business logic | Malformed/adversarial output executes downstream | Schema-validated boundary + retry (AI-ARCH-04) |
| `except Exception: return ""` around the call | Failure becomes a plausible empty answer | Defined fallback; missing ≠ empty (AI-ARCH-06) |
| Provider-default temperature in research runs | Defaults drift; results stop reproducing | Explicit params, recorded (AI-ARCH-05) |
| Dumping the whole document store into context | Cost × waste, degraded attention | Budgeted, ranked assembly (AI-ARCH-03) |
| Cost discovered on the monthly invoice | No per-call attribution, no early warning | Log usage per call (AI-ARCH-07) |

## References

- oracle `llm-statement-analyst` — house implementation of prompt files, structured
  outputs, and LLM-vs-baseline eval grading (AI-ARCH-01/-02/-04).
- Anthropic tool-use / structured-output docs (consulted via `/claude-api`, per
  `AI-MODELS-01`) — the mechanism AI-ARCH-04 builds on.
- pydantic v2 / zod — the boundary validators named in AI-ARCH-04, matching `STK-PY`'s
  canonical-library table.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
