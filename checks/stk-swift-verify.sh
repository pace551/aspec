#!/usr/bin/env bash
# stk-swift-verify.sh — runs the Swift test suite backing STK-SWIFT-06 (layer G).
# Deliberate design trim: the SwiftUI stack has no hosted CI workflow — this script IS
# the verification, run locally. Follows the secret-scan.sh degradation pattern: use the
# real toolchain when present, degrade to a documented warning when it is not, never
# silently pass.
#
# Behavior:
#   - Package.swift present  -> swift test            (works with Command Line Tools alone)
#   - *.xcodeproj/*.xcworkspace -> xcodebuild test    (requires full Xcode)
#   - toolchain absent/unusable -> exit 0 WITH a printed warning; the degraded run does
#     not satisfy STK-SWIFT-06 silently — /verify-compliance records the warning and the
#     rule falls back to manual attestation in GOVERNANCE.md.
#
# Usage:
#   stk-swift-verify.sh [--project DIR] [--scheme NAME]
#     --project  project root (default .)
#     --scheme   xcodebuild scheme (default: first scheme xcodebuild -list reports)
#
# Exit codes: 0 pass or documented degrade · 1 test failure · 2 usage error.
# Note: swift test writes build products to .build/ (gitignored) — no tracked file is
# ever mutated.
set -euo pipefail

PROJECT="."
SCHEME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?stk-swift-verify: --project needs a directory}"; shift 2 ;;
    --project=*) PROJECT="${1#--project=}"; shift ;;
    --scheme) SCHEME="${2:?stk-swift-verify: --scheme needs a name}"; shift 2 ;;
    --scheme=*) SCHEME="${1#--scheme=}"; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "stk-swift-verify: unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -d "$PROJECT" ]] || { echo "stk-swift-verify: no such directory: $PROJECT" >&2; exit 2; }
cd "$PROJECT"

# --- SPM package: swift test (CLT is enough) ---------------------------------
if [[ -f Package.swift ]]; then
  if ! command -v swift >/dev/null 2>&1; then
    echo "stk-swift-verify: WARNING — Package.swift found but no swift toolchain." >&2
    echo "stk-swift-verify: install Xcode or Command Line Tools (xcode-select --install)," >&2
    echo "stk-swift-verify: run tests on a machine that has them, and attest STK-SWIFT-06" >&2
    echo "stk-swift-verify: in GOVERNANCE.md. Degrading (exit 0), NOT passing." >&2
    exit 0
  fi
  echo "stk-swift-verify: Package.swift found — running swift test"
  rc=0
  out="$(swift test 2>&1)" || rc=$?
  printf '%s\n' "$out"
  if [[ $rc -eq 0 ]]; then
    echo "stk-swift-verify: swift test green"
    exit 0
  fi
  # Toolchain failure vs test failure: Command Line Tools ship the compiler but not
  # the XCTest/Testing modules (those come with Xcode). That is an environment
  # degrade, not a red suite — same contract as checks/ux-a11y.sh.
  if printf '%s' "$out" | grep -qE "no such module '(Testing|XCTest)'"; then
    echo "stk-swift-verify: WARNING — the toolchain has no test frameworks (Command" >&2
    echo "stk-swift-verify: Line Tools without Xcode). Install Xcode and select it" >&2
    echo "stk-swift-verify: (sudo xcode-select -s /Applications/Xcode.app), run tests" >&2
    echo "stk-swift-verify: there, and attest STK-SWIFT-06 in GOVERNANCE.md." >&2
    echo "stk-swift-verify: Degrading (exit 0), NOT passing." >&2
    exit 0
  fi
  echo "stk-swift-verify: FAIL — swift test reported failures (see output above)" >&2
  exit 1
fi

# --- Xcode project/workspace: xcodebuild test (full Xcode required) ----------
shopt -s nullglob
WORKSPACES=(*.xcworkspace)
PROJECTS=(*.xcodeproj)
shopt -u nullglob

if [[ ${#WORKSPACES[@]} -gt 0 || ${#PROJECTS[@]} -gt 0 ]]; then
  if ! command -v xcodebuild >/dev/null 2>&1 || ! xcodebuild -version >/dev/null 2>&1; then
    echo "stk-swift-verify: WARNING — Xcode project found but xcodebuild is unusable" >&2
    echo "stk-swift-verify: (missing Xcode, or active developer dir is Command Line Tools:" >&2
    echo "stk-swift-verify:  fix with: sudo xcode-select -s /Applications/Xcode.app)." >&2
    echo "stk-swift-verify: Run tests in Xcode on a capable machine and attest STK-SWIFT-06" >&2
    echo "stk-swift-verify: in GOVERNANCE.md. Degrading (exit 0), NOT passing." >&2
    exit 0
  fi
  if [[ ${#WORKSPACES[@]} -gt 0 ]]; then
    CONTAINER=(-workspace "${WORKSPACES[0]}")
  else
    CONTAINER=(-project "${PROJECTS[0]}")
  fi
  if [[ -z "$SCHEME" ]]; then
    SCHEME=$(xcodebuild "${CONTAINER[@]}" -list 2>/dev/null \
      | awk '/Schemes:/{flag=1; next} flag && NF {print $1; exit}')
  fi
  [[ -n "$SCHEME" ]] || { echo "stk-swift-verify: no scheme found; pass --scheme" >&2; exit 2; }
  echo "stk-swift-verify: running xcodebuild test -scheme $SCHEME (destination platform=macOS)"
  xcodebuild test "${CONTAINER[@]}" -scheme "$SCHEME" -destination 'platform=macOS' -quiet
  echo "stk-swift-verify: xcodebuild test green"
  exit 0
fi

echo "stk-swift-verify: no Package.swift, .xcodeproj, or .xcworkspace here — nothing to test" >&2
echo "stk-swift-verify: (run from the project root, or pass --project DIR)" >&2
exit 2
