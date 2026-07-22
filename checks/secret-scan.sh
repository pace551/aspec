#!/usr/bin/env bash
# secret-scan.sh — repo/staged secret scan. Backs SEC-SECRETS (layer H at commit time,
# layer G in CI). Uses gitleaks when installed; otherwise falls back to a built-in
# high-signal pattern scan so the gate never silently disappears.
#
# Usage:
#   secret-scan.sh            scan the working tree
#   secret-scan.sh --staged   scan staged changes only (pre-commit)
# Exit 0 clean, 1 findings, 2 usage/environment error.
set -euo pipefail

MODE="tree"
[[ "${1:-}" == "--staged" ]] && MODE="staged"

if command -v gitleaks >/dev/null 2>&1; then
  if [[ "$MODE" == "staged" ]]; then
    gitleaks protect --staged --no-banner --redact
  else
    gitleaks detect --no-banner --redact
  fi
  exit $?
fi

# ---- Fallback pattern scan (install gitleaks for full coverage: brew install gitleaks) ----
echo "secret-scan: gitleaks not found — using built-in pattern fallback (brew install gitleaks for full coverage)" >&2

PATTERNS=(
  'AKIA[0-9A-Z]{16}'                          # AWS access key id
  '-----BEGIN (RSA|EC|OPENSSH|DSA|PGP) ?PRIVATE KEY-----'
  'ghp_[A-Za-z0-9]{36}'                       # GitHub PAT
  'github_pat_[A-Za-z0-9_]{22,}'
  'xox[baprs]-[A-Za-z0-9-]{10,}'              # Slack
  'sk-ant-[A-Za-z0-9_-]{20,}'                 # Anthropic
  'sk-proj-[A-Za-z0-9_-]{20,}'                # OpenAI
  'AIza[0-9A-Za-z_-]{35}'                     # Google API key
  '(api[_-]?key|secret|token|passwd|password)["'"'"']?\s*[:=]\s*["'"'"'][A-Za-z0-9_/+=-]{16,}["'"'"']'
)
REGEX=$(IFS='|'; echo "${PATTERNS[*]}")

# Obvious fakes (docs, fixtures) are not findings — same policy as the pre-write hook.
FAKE_FILTER='EXAMPLE|PLACEHOLDER'

if [[ "$MODE" == "staged" ]]; then
  SOURCE=$(git diff --staged --unified=0 | grep -E '^\+' | grep -vE '^\+\+\+' \
    | grep -viE "$FAKE_FILTER" || true)
else
  SOURCE=$(git ls-files -z | xargs -0 grep -InE "$REGEX" \
    --exclude='*.example' --exclude='secret-scan.sh' 2>/dev/null \
    | grep -viE "$FAKE_FILTER" || true)
  if [[ -n "$SOURCE" ]]; then
    echo "secret-scan: potential secrets found:" >&2
    echo "$SOURCE" | sed 's/\(.\{120\}\).*/\1…/' >&2
    exit 1
  fi
  echo "secret-scan: clean (fallback scan)"
  exit 0
fi

if echo "$SOURCE" | grep -qE "$REGEX"; then
  echo "secret-scan: potential secret in staged changes:" >&2
  echo "$SOURCE" | grep -E "$REGEX" | sed 's/\(.\{120\}\).*/\1…/' >&2
  exit 1
fi
echo "secret-scan: staged changes clean (fallback scan)"
