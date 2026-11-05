#!/usr/bin/env bash
# secret-scan.sh — repo/staged secret scan. Backs SEC-SECRETS (layer H at commit time,
# layer G in CI). Uses gitleaks when installed; otherwise falls back to a built-in
# high-signal pattern scan so the gate never silently disappears.
#
# Usage:
#   secret-scan.sh            scan the working tree
#   secret-scan.sh --staged   scan staged changes only (pre-commit)
# Exit 0 clean, 1 findings, 2 usage/environment error or an incomplete scan.
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
# LC_ALL=C for every grep below: their error text is matched, and no locale's encoding
# rules may turn a text line into a "binary file matches" message (or drop it).
export LC_ALL=C
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
  # grep's errors used to go to /dev/null, so a file it couldn't read passed unscanned.
  # They go to a temp file instead; anything but a tracked file deleted from the work tree
  # (ENOENT) makes the scan incomplete.
  ERRS=$(mktemp "${TMPDIR:-/tmp}/secret-scan.XXXXXX")
  trap 'rm -f "$ERRS"' EXIT
  SOURCE=$(git ls-files -z | xargs -0 grep -d skip -InE "$REGEX" \
    --exclude='*.example' --exclude='secret-scan.sh' 2>"$ERRS" \
    | grep -viE "$FAKE_FILTER" || true)
  # captured rather than piped to `grep -q`, whose early exit would SIGPIPE the producer
  # and (with pipefail) make a long error list look like none
  BAD=$(grep -v ': No such file or directory$' "$ERRS" || true)
  if [[ -n "$BAD" ]]; then
    echo "secret-scan: could not read every tracked file — scan incomplete:" >&2
    printf '%s\n' "$BAD" >&2
    exit 2
  fi
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
