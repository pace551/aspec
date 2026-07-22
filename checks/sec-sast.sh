#!/usr/bin/env bash
# sec-sast.sh — cross-stack SAST runner. Backs SEC-SAST-01 (layer G) and, via the same
# scan, the machine-checkable injection/crypto rules SEC-INPUT-02/-03 and SEC-CRYPTO-02
# (bandit/semgrep flag string-built SQL, shell=True, and weak hashes).
#
# Detects the project type from its manifest and runs the required scanner if installed:
#   pyproject.toml / setup.py -> bandit          (.venv/bin/bandit preferred)
#   package.json              -> semgrep         (eslint security plugins run inside the
#                                                 project's own lint; semgrep is the
#                                                 runnable cross-checked gate here)
#   go.mod                    -> go vet + gosec
#   Cargo.toml                -> cargo clippy -D warnings
#                                (cargo-audit belongs to SEC-SUPPLY / sec-sca.sh, not here)
#
# Degradation contract (same spirit as secret-scan.sh, but tier-aware):
#   default / --tier T1|T2 : missing scanner -> documented warning, exit 0 (fallback is
#                            explicitly sanctioned at these tiers by SEC-SAST-01)
#   --tier T3|T4           : missing required scanner -> clear error, exit 1 — the gate
#                            may never silently disappear on an internet-facing project.
#
# Usage: sec-sast.sh [--project DIR] [--tier T1|T2|T3|T4]
# Exit 0 = pass (or documented lenient skip), 1 = findings or missing required scanner
# at a strict tier, 2 = usage/environment error. Read-only: scans, never fixes.
set -euo pipefail

PROJECT="."
TIER="T1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?--project needs a directory}"; shift 2 ;;
    --tier)    TIER="${2:?--tier needs T1|T2|T3|T4}"; shift 2 ;;
    *) echo "sec-sast: unknown argument: $1 (usage: sec-sast.sh [--project DIR] [--tier T1..T4])" >&2; exit 2 ;;
  esac
done
case "$TIER" in
  T1|T2) STRICT=0 ;;
  T3|T4) STRICT=1 ;;
  *) echo "sec-sast: bad tier '$TIER' (expected T1..T4)" >&2; exit 2 ;;
esac
cd "$PROJECT" 2>/dev/null || { echo "sec-sast: cannot cd to '$PROJECT'" >&2; exit 2; }

FAIL=0
RAN=0

run() {
  echo "sec-sast: running: $*"
  "$@" || FAIL=1
  RAN=1
}

missing() { # $1 = scanner name, $2 = install hint
  if [[ $STRICT -eq 1 ]]; then
    echo "sec-sast: FAIL — required scanner '$1' not installed (tier $TIER; SEC-SAST-01)." >&2
    echo "sec-sast: install: $2" >&2
    FAIL=1
  else
    echo "sec-sast: WARNING — '$1' not installed; skipping (lenient at tier $TIER). Install: $2" >&2
  fi
}

# ---- Python: bandit ----
if [[ -f pyproject.toml || -f setup.py ]]; then
  BANDIT=""
  [[ -x .venv/bin/bandit ]] && BANDIT=".venv/bin/bandit"
  [[ -z "$BANDIT" ]] && command -v bandit >/dev/null 2>&1 && BANDIT="bandit"
  if [[ -n "$BANDIT" ]]; then
    TARGET="."
    [[ -d src ]] && TARGET="src"
    run "$BANDIT" -r "$TARGET" -q
  else
    missing "bandit" "add bandit to the project's [dev] extras (STK-PY) or: pipx install bandit"
  fi
fi

# ---- TypeScript / JavaScript: semgrep ----
if [[ -f package.json ]]; then
  if command -v semgrep >/dev/null 2>&1; then
    run semgrep scan --quiet --error --metrics=off --config p/security-audit .
  else
    missing "semgrep" "brew install semgrep (eslint security plugins still run via the project's own lint)"
  fi
fi

# ---- Go: go vet + gosec ----
if [[ -f go.mod ]]; then
  if command -v go >/dev/null 2>&1; then
    run go vet ./...
  else
    missing "go" "the Go toolchain itself (brew install go)"
  fi
  if command -v gosec >/dev/null 2>&1; then
    run gosec -quiet ./...
  else
    missing "gosec" "go install github.com/securego/gosec/v2/cmd/gosec@latest"
  fi
fi

# ---- Rust: clippy ----
if [[ -f Cargo.toml ]]; then
  if command -v cargo >/dev/null 2>&1; then
    run cargo clippy --quiet -- -D warnings
  else
    missing "cargo" "rustup (https://rustup.rs)"
  fi
fi

if [[ $RAN -eq 0 && $FAIL -eq 0 ]]; then
  echo "sec-sast: no recognized manifest (pyproject.toml/package.json/go.mod/Cargo.toml) — nothing scanned" >&2
  if [[ $STRICT -eq 1 ]]; then
    echo "sec-sast: FAIL — tier $TIER requires a SAST scan; add the stack's scanner (SEC-SAST-01)" >&2
    exit 1
  fi
  exit 0
fi

if [[ $FAIL -eq 0 ]]; then
  echo "sec-sast: clean"
fi
exit $FAIL
