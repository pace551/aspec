#!/usr/bin/env bash
# pre-push.sh — this repo's own push checks, run by the pre-push hook after the test gate:
# each pushed branch is one conventional commit, and feat/fix/breaking changes add to
# CHANGELOG.md's Unreleased section (checks/pr-hygiene.py; the CI pr-hygiene job runs the
# same check).
#   From the hook (args: remote name and URL; stdin: one line per pushed ref) it checks
#   every branch being pushed. Run it by hand with no arguments to check HEAD.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/venv.sh

hygiene() { .venv/bin/python checks/pr-hygiene.py --base origin/main --head "$1"; }

if [ $# -eq 0 ] || [ -t 0 ]; then # by hand (even with the hook's args from a terminal)
  hygiene HEAD
  exit
fi

status=0
# Each line: <local ref> <local sha> <remote ref> <remote sha>. The local ref can be HEAD
# or a bare sha (`git push origin HEAD`), so the remote ref decides what is pushed.
while read -r _local_ref local_sha remote_ref _remote_sha; do
  case "${remote_ref:-}" in refs/heads/*) ;; *) continue ;; esac # branches, not tags
  case "$local_sha" in *[!0]*) ;; *) continue ;; esac       # all zeros: a deletion
  echo "pre-push: ${remote_ref#refs/heads/}"
  hygiene "$local_sha" || status=1
done
# No ref lines (an up-to-date push still runs the hook): nothing is pushed, nothing to check.
exit "$status"
