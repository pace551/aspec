#!/usr/bin/env bash
# test.sh — scripts contract (tests). Delegates to the governance verify script
# (STK-SWIFT-06), which picks swift test vs xcodebuild test and degrades gracefully
# when Xcode tooling is absent. Falls back to plain swift test without the governance
# repo. (No coverage ratchet for this stack — profdata is not a ratchet format.)
set -euo pipefail
cd "$(dirname "$0")/.."

VERIFY="${GOVERNANCE_DIR:-$HOME/Dev/claude-code/governance}/checks/stk-swift-verify.sh"
if [ -f "$VERIFY" ]; then
  bash "$VERIFY" --project .
else
  swift test
fi
