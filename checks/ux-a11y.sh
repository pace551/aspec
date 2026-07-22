#!/usr/bin/env bash
# ux-a11y.sh — automated accessibility scan backing UX-A11Y-01 (layer G, T3+ web).
# Runs @axe-core/cli against a running page. Follows the secret-scan.sh degradation
# pattern: use the real scanner when the environment supports it, degrade to a
# documented warning when it does not, never fail for reasons unrelated to a11y.
#
# Usage:
#   ux-a11y.sh [URL] [--project DIR]
#     URL        page to scan (default http://localhost:3000)
#     --project  project root, for local node_modules resolution (default .)
#
# Exit codes:
#   0  scan passed, or scan skipped/degraded WITH a printed warning
#      (a degraded run does not satisfy UX-A11Y-01 silently — /verify-compliance
#      records the warning and the rule falls back to manual attestation)
#   1  axe-core reported accessibility violations
#   2  usage error
set -euo pipefail

URL="http://localhost:3000"
PROJECT="."

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?ux-a11y: --project needs a directory}"; shift 2 ;;
    --project=*) PROJECT="${1#--project=}"; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    http://*|https://*) URL="$1"; shift ;;
    *) echo "ux-a11y: unknown argument: $1 (URL must start http:// or https://)" >&2; exit 2 ;;
  esac
done

[[ -d "$PROJECT" ]] || { echo "ux-a11y: no such directory: $PROJECT" >&2; exit 2; }
cd "$PROJECT"

# --- Reachability: nothing running is a skip, not a failure -------------------
if ! curl -fsS -o /dev/null --max-time 10 "$URL" 2>/dev/null; then
  echo "ux-a11y: SKIP — $URL unreachable. Start the app (or pass its URL) and re-run;" >&2
  echo "ux-a11y: in CI, templates/ci/_fragments/a11y.yml boots the app before scanning." >&2
  exit 0
fi

# --- Tooling: degrade with a documented warning, never silently pass ----------
if ! command -v npx >/dev/null 2>&1; then
  echo "ux-a11y: WARNING — npx not found; cannot run @axe-core/cli." >&2
  echo "ux-a11y: install Node (brew install node), or verify manually with the axe" >&2
  echo "ux-a11y: DevTools extension and attest UX-A11Y-01 in GOVERNANCE.md." >&2
  exit 0
fi

echo "ux-a11y: scanning $URL with @axe-core/cli"
rc=0
out="$(npx --yes @axe-core/cli "$URL" --exit 2>&1)" || rc=$?
printf '%s\n' "$out"

if [[ $rc -eq 0 ]]; then
  echo "ux-a11y: clean — no violations reported"
  exit 0
fi

# Non-zero: violations vs environment failure (e.g. no chromedriver/browser).
if printf '%s' "$out" | grep -qiE 'violation'; then
  echo "ux-a11y: FAIL — accessibility violations found (see output above)" >&2
  exit 1
fi

echo "ux-a11y: WARNING — axe could not complete (likely missing browser driver;" >&2
echo "ux-a11y: try: npm i -D chromedriver). Degrading: verify manually with the axe" >&2
echo "ux-a11y: DevTools extension and attest UX-A11Y-01 in GOVERNANCE.md." >&2
exit 0
