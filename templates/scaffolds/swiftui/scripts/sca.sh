#!/usr/bin/env bash
# sca.sh — scripts contract (SEC-SUPPLY-01, the CI job `sca`). Runs osv-scanner on every
# SwiftPM lockfile: ./Package.resolved (a package) and the ones Xcode keeps under
# *.xcodeproj/ and *.xcworkspace/ (an app); none means no pinned dependencies. That
# remote dependencies have a committed, current lockfile at all is
# scripts/lockfile-check.py's job (the typecheck CI job). osv-scanner v2.4.0+ reads
# Package.resolved (OSV's SwiftURL advisories).
set -euo pipefail
cd "$(dirname "$0")/.."
shopt -s nullglob

locks=()
[ -f Package.resolved ] && locks+=("./Package.resolved")
for f in ./*.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved \
         ./*.xcworkspace/xcshareddata/swiftpm/Package.resolved; do
  locks+=("$f")
done

if [ ${#locks[@]} -eq 0 ]; then
  echo "sca: no Package.resolved, so no pinned dependencies to audit"
  exit 0
fi

status=0
for lock in "${locks[@]}"; do
  echo "sca: osv-scanner on $lock"
  osv-scanner scan source --lockfile "$lock" || status=1
done
exit "$status"
