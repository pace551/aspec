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
#   Package.swift / *.xcodeproj / *.xcworkspace
#                             -> osv-scanner on each SwiftPM Package.resolved that
#                                pins packages (the package's and Xcode's); remote
#                                packages that no lockfile pins, or a CocoaPods/Carthage
#                                lockfile, can't be audited (swift-project.py finds them)
#
# Degradation contract (same tier-aware pattern as sec-sast.sh):
#   default / --tier T1|T2 : missing scanner -> documented warning, exit 0
#   --tier T3|T4           : missing required scanner -> clear error, exit 1
#
# Usage: sec-sca.sh [--project DIR] [--tier T1|T2|T3|T4]
# Exit 0 = pass (or documented lenient skip), 1 = findings or missing required scanner
# at a strict tier, 2 = usage/environment error or an unreadable lockfile. Read-only: audits, never upgrades.
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
GOV="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT" 2>/dev/null || { echo "sec-sca: cannot cd to '$PROJECT'" >&2; exit 2; }

FAIL=0
RAN=0
SKIPPED=0 # a stack was found but its scan skipped (lenient tier)

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
    SKIPPED=1
  fi
}

gap() { # $1 = why a dependency set can't be audited
  if [[ $STRICT -eq 1 ]]; then
    echo "sec-sca: FAIL — $1 (tier $TIER; SEC-SUPPLY-01)" >&2
    FAIL=1
  else
    echo "sec-sca: WARNING — $1 (lenient at tier $TIER)" >&2
    SKIPPED=1
  fi
}

# Swift: Package.swift, an Xcode project, or a workspace (Tuist and modular apps keep their
# projects in subdirectories). What the check needs to know about one comes from
# swift-project.py, shared with sec-sast.sh.
swift_project() {
  [[ -f Package.swift ]] || compgen -G './*.xcodeproj' >/dev/null || compgen -G './*.xcworkspace' >/dev/null
}
swift_helper() { # $1 = sca|codeql
  local py="$GOV/.venv/bin/python"
  [[ -x "$py" ]] || { echo "sec-sca: $py missing — run checks/install.sh" >&2; exit 2; }
  "$py" "$GOV/checks/swift-project.py" "$1"
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

# ---- Swift: osv-scanner on SwiftPM lockfiles (v2.4.0+ reads Package.resolved) ----
if swift_project; then
  SWIFT_OUT=$(swift_helper sca) || { echo "sec-sca: Swift dependencies unreadable — scan incomplete" >&2; exit 2; }
  SWIFT_LOCKS=()
  while read -r kind path; do
    case "$kind" in
      lock) SWIFT_LOCKS+=("$path") ;;
      unpinned) gap "$path declares remote packages but no Package.resolved pins anything: resolve the package or workspace (swift package resolve, or open it in Xcode) and commit its Package.resolved" ;;
      unaudited) gap "$path: no scanner here audits CocoaPods/Carthage lockfiles; move those dependencies to SwiftPM, or audit them by hand and record a waiver" ;;
    esac
  done <<<"$SWIFT_OUT"
  if [[ ${#SWIFT_LOCKS[@]} -gt 0 ]]; then
    if command -v osv-scanner >/dev/null 2>&1; then
      for lock in "${SWIFT_LOCKS[@]}"; do
        run osv-scanner scan source --lockfile "$lock"
      done
    else
      missing "osv-scanner" "brew install osv-scanner (v2.4.0+ reads Package.resolved)"
    fi
  elif [[ -z "$SWIFT_OUT" ]]; then
    echo "sec-sca: Swift project with no pinned dependencies — nothing to audit"
    RAN=1
  fi
fi

if [[ $RAN -eq 0 && $FAIL -eq 0 && $SKIPPED -eq 0 ]]; then
  echo "sec-sca: no recognized manifest (pyproject.toml/package.json/go.mod/Cargo.toml/Package.swift) — nothing audited" >&2
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
