#!/usr/bin/env bash
# sec-sca.sh — cross-stack software-composition-analysis (dependency CVE) runner.
# Backs SEC-SUPPLY-01 (layer G).
#
# Detects the project type from its manifest and runs the required scanner if installed:
#   pyproject.toml / setup.py -> pip-audit        (.venv/bin/pip-audit preferred)
#   package.json              -> npm audit --audit-level=high (needs package-lock.json);
#                                osv-scanner as the fallback for pnpm/yarn/bun lockfiles
#   go.mod                    -> govulncheck; osv-scanner as fallback
#   Cargo.toml                -> cargo audit (cargo-audit)
#
# Degradation contract (same tier-aware pattern as sec-sast.sh):
#   default / --tier T1|T2 : missing scanner -> documented warning, exit 0
#   --tier T3|T4           : missing required scanner -> clear error, exit 1
#
# Usage: sec-sca.sh [--project DIR] [--tier T1|T2|T3|T4]
# Exit 0 = pass (or documented lenient skip), 1 = findings or missing required scanner
# at a strict tier, 2 = usage/environment error. Read-only: audits, never upgrades.
set -euo pipefail

PROJECT="."
TIER="T1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?--project needs a directory}"; shift 2 ;;
    --tier)    TIER="${2:?--tier needs T1|T2|T3|T4}"; shift 2 ;;
    *) echo "sec-sca: unknown argument: $1 (usage: sec-sca.sh [--project DIR] [--tier T1..T4])" >&2; exit 2 ;;
  esac
done
case "$TIER" in
  T1|T2) STRICT=0 ;;
  T3|T4) STRICT=1 ;;
  *) echo "sec-sca: bad tier '$TIER' (expected T1..T4)" >&2; exit 2 ;;
esac
cd "$PROJECT" 2>/dev/null || { echo "sec-sca: cannot cd to '$PROJECT'" >&2; exit 2; }

FAIL=0
RAN=0

run() {
  echo "sec-sca: running: $*"
  "$@" || FAIL=1
  RAN=1
}

missing() { # $1 = scanner name, $2 = install hint
  if [[ $STRICT -eq 1 ]]; then
    echo "sec-sca: FAIL — required scanner '$1' not installed (tier $TIER; SEC-SUPPLY-01)." >&2
    echo "sec-sca: install: $2" >&2
    FAIL=1
  else
    echo "sec-sca: WARNING — '$1' not installed; skipping (lenient at tier $TIER). Install: $2" >&2
  fi
}

# ---- Python: pip-audit ----
if [[ -f pyproject.toml || -f setup.py ]]; then
  PIP_AUDIT=""
  [[ -x .venv/bin/pip-audit ]] && PIP_AUDIT=".venv/bin/pip-audit"
  [[ -z "$PIP_AUDIT" ]] && command -v pip-audit >/dev/null 2>&1 && PIP_AUDIT="pip-audit"
  if [[ -n "$PIP_AUDIT" ]]; then
    run "$PIP_AUDIT"
  else
    missing "pip-audit" "add pip-audit to the project's [dev] extras (STK-PY) or: pipx install pip-audit"
  fi
fi

# ---- Node: npm audit, osv-scanner for non-npm lockfiles ----
if [[ -f package.json ]]; then
  if [[ -f package-lock.json ]] && command -v npm >/dev/null 2>&1; then
    run npm audit --audit-level=high
  elif command -v osv-scanner >/dev/null 2>&1; then
    # v1 syntax; on osv-scanner v2 the default subcommand ('scan source') accepts it too
    run osv-scanner -r .
  elif [[ ! -f package-lock.json ]]; then
    echo "sec-sca: NOTE — package.json without package-lock.json; commit a lockfile (SEC-SUPPLY-02)" >&2
    missing "osv-scanner" "brew install osv-scanner (audits pnpm/yarn/bun lockfiles)"
  else
    missing "npm" "Node toolchain (brew install node)"
  fi
fi

# ---- Go: govulncheck, osv-scanner fallback ----
if [[ -f go.mod ]]; then
  if command -v govulncheck >/dev/null 2>&1; then
    run govulncheck ./...
  elif command -v osv-scanner >/dev/null 2>&1; then
    run osv-scanner -r .
  else
    missing "govulncheck" "go install golang.org/x/vuln/cmd/govulncheck@latest"
  fi
fi

# ---- Rust: cargo-audit ----
if [[ -f Cargo.toml ]]; then
  if command -v cargo-audit >/dev/null 2>&1; then
    run cargo audit
  else
    missing "cargo-audit" "cargo install cargo-audit"
  fi
fi

if [[ $RAN -eq 0 && $FAIL -eq 0 ]]; then
  echo "sec-sca: no recognized manifest (pyproject.toml/package.json/go.mod/Cargo.toml) — nothing audited" >&2
  if [[ $STRICT -eq 1 ]]; then
    echo "sec-sca: FAIL — tier $TIER requires dependency auditing; add the stack's scanner (SEC-SUPPLY-01)" >&2
    exit 1
  fi
  exit 0
fi

if [[ $FAIL -eq 0 ]]; then
  echo "sec-sca: clean"
fi
exit $FAIL
