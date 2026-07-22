#!/usr/bin/env bash
# lint.sh — scripts contract (format check + lint). Uses swiftformat/swiftlint when
# installed; degrades with a documented warning otherwise (secret-scan.sh pattern:
# never a silent pass — /verify-compliance records the warning).
set -euo pipefail
cd "$(dirname "$0")/.."

ran=0
if command -v swiftformat >/dev/null 2>&1; then
  swiftformat --lint Sources Tests
  ran=1
fi
if command -v swiftlint >/dev/null 2>&1; then
  swiftlint --strict
  ran=1
fi
if [ "$ran" -eq 0 ]; then
  echo "lint.sh: WARNING — neither swiftformat nor swiftlint installed" >&2
  echo "lint.sh: (brew install swiftformat swiftlint). Lint gate degraded, NOT passed." >&2
fi
