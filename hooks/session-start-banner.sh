#!/usr/bin/env bash
# session-start-banner.sh — Claude Code SessionStart hook. One line of governance
# context when the cwd is a governed project; silent otherwise. Never blocks.
set -uo pipefail

[ -f GOVERNANCE.md ] || exit 0

TIER=$(grep -m1 -E '^tier: ' GOVERNANCE.md | awk '{print $2}' || true)
VERIFIED=$(grep -m1 -E '^last_verified: ' GOVERNANCE.md | awk '{print $2}' || true)
echo "Governed project: tier ${TIER:-?} · last_verified ${VERIFIED:-never} · done = /verify-compliance green (see GOVERNANCE.md)"
exit 0
