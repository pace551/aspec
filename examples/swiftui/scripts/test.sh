#!/usr/bin/env bash
# test.sh — scripts contract (tests + coverage). For an SPM package with the full Xcode
# toolchain it runs scripts/coverage.sh: swift test with code coverage, exported as
# lcov.info for the coverage ratchet (TST-RATCHET), the same as the CI test job.
# Otherwise it delegates to the governance verify script (STK-SWIFT-06): xcodebuild test
# for an app project, or a documented degrade where Command Line Tools lack the
# Testing/XCTest modules (plain swift test without the governance repo).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f Package.swift ] && xcrun --find xctest >/dev/null 2>&1; then
  exec scripts/coverage.sh
fi
# No coverage this run. Deleting an old lcov.info would make the pre-push ratchet block
# every push here, so say so instead: CI (macOS, full Xcode) recomputes and enforces it.
if [ -f lcov.info ]; then
  echo "test.sh: WARNING — no fresh coverage on this toolchain; lcov.info is from an earlier run (CI checks the real number)" >&2
fi

GOV="${GOVERNANCE_DIR:-}"
if [ -z "$GOV" ]; then
  GOV=$(python3 -c "import json, os.path; print(json.load(open(os.path.expanduser('~/.claude/aspec.json'))).get('governance_repo', ''))" 2>/dev/null || true)
fi
VERIFY="$GOV/checks/stk-swift-verify.sh"
if [ -n "$GOV" ] && [ -f "$VERIFY" ]; then
  bash "$VERIFY" --project .
else
  swift test
fi
