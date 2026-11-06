#!/usr/bin/env bash
# coverage.sh — coverage for the ratchet (TST-RATCHET), run by scripts/test.sh. Runs the tests
# with code coverage and exports lcov.info, the format checks/coverage-ratchet.py reads
# (profdata itself isn't one). Needs the full Xcode toolchain, as on GitHub's macOS
# runners: Command Line Tools alone lack the Testing/XCTest modules.
set -euo pipefail
cd "$(dirname "$0")/.."

swift test --enable-code-coverage
BIN=$(swift build --show-bin-path)
XCTEST=$(find "$BIN" -maxdepth 1 -name '*PackageTests.xctest' | head -n 1)
if [ -z "$XCTEST" ]; then
  echo "coverage.sh: no *PackageTests.xctest under $BIN" >&2
  exit 2
fi
xcrun llvm-cov export -format=lcov \
  -instr-profile "$BIN/codecov/default.profdata" \
  -ignore-filename-regex '(/\.build/|/Tests/)' \
  "$XCTEST/Contents/MacOS/$(basename "$XCTEST" .xctest)" > lcov.info
echo "coverage.sh: wrote lcov.info"
