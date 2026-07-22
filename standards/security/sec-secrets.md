---
id: SEC-SECRETS
title: Secrets Management
family: SEC
version: 1.0.1
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: all
triggers:
  - secret
  - credential
  - api key
  - token
  - password
  - .env
  - keychain
  - vault
  - private key
requires: []
verification:
  - cmd: "bash ~/Dev/claude-code/governance/checks/secret-scan.sh"
    expect: "exit 0 — no secret patterns in tracked files"
    layer: G
    rules: [SEC-SECRETS-01]
  - cmd: "sh -c '! git ls-files | grep -qx \".env\"' && sh -c '[ ! -f .env ] || git check-ignore -q .env'"
    expect: "exit 0 — .env never tracked and ignored if present"
    layer: G
    rules: [SEC-SECRETS-02]
  - cmd: "sh -c '[ ! -f .env ] || [ -f .env.example ]'"
    expect: "exit 0 — a project using .env ships .env.example"
    layer: G
    rules: [SEC-SECRETS-02]
  - cmd: "attest: secret storage matches the tier ladder (.env → Keychain/1Password → SSM/Secrets Manager)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-SECRETS-03]
  - cmd: "attest: no secret has appeared in logs, error output, crash reports, or LLM prompts"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-SECRETS-04]
  - cmd: "attest: any secret ever exposed (git, logs, pasted context) has been rotated"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-SECRETS-05]
  - cmd: "attest: credentials are minimally scoped; OIDC/roles used over static keys where available"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [SEC-SECRETS-06]
    tiers: [T3, T4]
last_review: 2026-07-22
---

# Secrets Management (SEC-SECRETS)

## Abstract

Retires the highest-frequency catastrophic failure: credentials reaching git, logs, build
artifacts, or LLM context. Compliance in one breath: real secrets live only in the
tier-appropriate store (`.env` → Keychain/1Password → AWS SSM/Secrets Manager), tracked
files carry only `.env.example` placeholders, a pre-write hook and gitleaks-backed scans
block leaks before they land, and an exposed secret is rotated the moment it is noticed.
Identical at every tier — this is the one family where T1 gets no discount, because a
leaked personal AWS key costs real money within hours.

## Normative Rules

### SEC-SECRETS-01 — No secret MUST ever be written to a tracked file

**Tiers**: all required — **Layer**: H (pre-write hook + pre-commit) + G (CI scan)

Applies to source, config, docs, fixtures, notebooks, and commit messages. "Secret" means
anything granting access: API keys, tokens, passwords, private keys, session cookies,
signed URLs with long expiry. Test fixtures use obviously-fake values (`sk-ant-TEST…`,
`AKIAIOSFODNN7EXAMPLE`). A secret that was committed and then deleted is still leaked —
history retains it; see SEC-SECRETS-05.

### SEC-SECRETS-02 — Projects using local credentials MUST keep them in `.env` (gitignored) and ship `.env.example`

**Tiers**: all required — **Layer**: G

`.env` is listed in `.gitignore` before the first credential exists. `.env.example` mirrors
every variable name with placeholder values and a one-line comment on where each value
comes from. Code reads secrets from the environment only — never from a hardcoded fallback
default (`os.getenv("KEY", "sk-…")` is a violation of SEC-SECRETS-01).

### SEC-SECRETS-03 — Secret storage MUST match the tier ladder

**Tiers**: all required — **Layer**: A (attestation)

- **T1/T2**: `.env` file per project, or macOS Keychain / 1Password CLI for shared or
  long-lived credentials.
- **T3/T4**: a managed store — AWS SSM Parameter Store (SecureString) or Secrets Manager —
  injected at runtime (task role, Lambda env from SSM). Secrets MUST NOT be baked into
  container images, AMIs, build artifacts, or frontend bundles (anything shipped to a
  browser is public by definition).
- **T4**: access to production secrets is MFA-protected and auditable.

### SEC-SECRETS-04 — Secrets MUST NOT appear in logs, error messages, crash reports, or LLM prompts

**Tiers**: all required — **Layer**: A (attestation)

Exception handlers and loggers never echo environment variables or request headers
wholesale (`Authorization`, `Cookie`, `X-Api-Key` are redacted — `OPS-OBS` carries the
logging rules). Prompts sent to any LLM, including Claude Code sub-agents, reference
secrets by variable name, never by value.

### SEC-SECRETS-05 — An exposed secret MUST be rotated immediately; deletion is not remediation

**Tiers**: all required — **Layer**: A (attestation)

The moment a secret is seen in a tracked file, log, terminal share, or pasted context:
revoke and reissue it first, clean up second. History rewriting (`git filter-repo`) is
optional hygiene afterwards; rotation is the remediation. The step-by-step playbook lives
in `OPS-INCIDENT`.

### SEC-SECRETS-06 — Credentials SHOULD be minimally scoped and short-lived

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Prefer role assumption and OIDC federation over long-lived static keys (CI uses GitHub
OIDC → AWS role, not stored `AWS_SECRET_ACCESS_KEY` — detail in `INF-ENVS`). Tokens get
the narrowest scopes the task allows and expiries where the provider supports them. One
credential per consumer, so revocation is surgical.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `bash ~/Dev/claude-code/governance/checks/secret-scan.sh` | exit 0 (gitleaks, or built-in pattern fallback) | SEC-SECRETS-01 |
| 2 | `! git ls-files \| grep -qx ".env"` and `git check-ignore -q .env` (if present) | `.env` untracked + ignored | SEC-SECRETS-02 |
| 3 | `[ ! -f .env ] \|\| [ -f .env.example ]` | example file exists alongside `.env` | SEC-SECRETS-02 |
| 4-7 | attestation checklist (one entry per rule) | explicit yes recorded | SEC-SECRETS-03…06 |

**Remediation:** scan hit on a real secret → rotate now (SEC-SECRETS-05), then remove and
recommit · scan hit on a fixture → rename value to an obvious fake or add a scoped gitleaks
allowlist entry with a comment · `.env` tracked → `git rm --cached .env`, add to
`.gitignore`, rotate everything it contained.

## Worked Example

A T1 Python tool that calls the Anthropic API:

```
mytool/
├── .gitignore          # contains: .env
├── .env                # ANTHROPIC_API_KEY=sk-ant-…   (never committed)
├── .env.example        # ANTHROPIC_API_KEY=            # console.anthropic.com → API keys
└── src/mytool/config.py
```

```python
# src/mytool/config.py
import os

API_KEY = os.environ["ANTHROPIC_API_KEY"]  # KeyError > silent fallback (SEC-SECRETS-02)
```

The same tool promoted to T3 on ECS: delete `.env` from the deploy path, store the key as
an SSM SecureString `/mytool/prod/anthropic-api-key`, and inject via the task definition's
`secrets` block — the container image never contains it (SEC-SECRETS-03).

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `os.getenv("KEY", "sk-real…")` fallback | Hardcoded secret with extra steps | Fail loudly: `os.environ["KEY"]` |
| Deleting a committed secret in a follow-up commit | History still serves it; scrapers watch pushes | Rotate first (SEC-SECRETS-05) |
| Secrets in ECS task definition plain `environment` | Visible in console/`describe-tasks` to any reader | `secrets` block → SSM/Secrets Manager |
| `NEXT_PUBLIC_`/`VITE_`-prefixed secret vars | Bundled into public JS | Server-side env only; proxy the call |
| Sharing one API key across tools | Revocation breaks everything at once | One key per consumer (SEC-SECRETS-06) |
| Pasting `.env` contents into an LLM chat to debug | Third-party retention of live credentials | Reference names, not values (SEC-SECRETS-04) |

## References

- gitleaks (https://github.com/gitleaks/gitleaks) — the H/G scanner both hook and CI use.
- 12-Factor App, factor III "Config" — the env-var discipline SEC-SECRETS-02 encodes.
- AWS SSM Parameter Store vs Secrets Manager docs — the T3+ rung of the ladder
  (Secrets Manager when rotation-by-lambda is needed; SSM SecureString otherwise, free).
- OWASP Secrets Management Cheat Sheet — scoping and rotation rationale.

## Changelog

- **1.0.1** (2026-07-22) — Format-review fixes: attestations split to one entry per rule;
  SEC-SECRETS-06 entry tier-scoped to T3+.
- **1.0.0** (2026-07-22) — Initial version (pilot standard; calibrates the corpus format).
