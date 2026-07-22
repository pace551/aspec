#!/usr/bin/env bash
# pre-write-secret-scan.sh — Claude Code PreToolUse hook (Write|Edit), layer H for
# SEC-SECRETS-01. Blocks writes whose new content matches high-confidence secret
# patterns. Deliberately NARROW (the only blocking global hook): patterns here must be
# near-zero false positive; breadth belongs to gitleaks at commit/CI time.
#
# Contract: reads the PreToolUse JSON on stdin; exit 0 = allow, exit 2 = block (stderr
# is shown to the model).
set -uo pipefail

INPUT=$(cat)

CONTENT=$(printf '%s' "$INPUT" | python3 -c '
import json, sys
d = json.load(sys.stdin)
ti = d.get("tool_input", {})
print(ti.get("content", "") or ti.get("new_string", ""))
' 2>/dev/null) || exit 0   # unparseable input: never block on hook malfunction

[ -z "$CONTENT" ] && exit 0

# Allow obvious fakes/placeholders through (docs, fixtures, examples).
STRIPPED=$(printf '%s' "$CONTENT" | grep -viE 'EXAMPLE|PLACEHOLDER|YOUR[_-]|XXXX|TEST' || true)
[ -z "$STRIPPED" ] && exit 0

PATTERNS=(
  'AKIA[0-9A-Z]{16}'
  '-----BEGIN (RSA|EC|OPENSSH|DSA|PGP) ?PRIVATE KEY-----'
  'ghp_[A-Za-z0-9]{36}'
  'github_pat_[A-Za-z0-9_]{22,}'
  'xox[baprs]-[A-Za-z0-9-]{10,}'
  'sk-ant-[A-Za-z0-9_-]{20,}'
  'sk-proj-[A-Za-z0-9_-]{20,}'
  'AIza[0-9A-Za-z_-]{35}'
)
REGEX=$(IFS='|'; echo "${PATTERNS[*]}")

if printf '%s' "$STRIPPED" | grep -qE "$REGEX"; then
  MATCH=$(printf '%s' "$STRIPPED" | grep -oE "$REGEX" | head -1 | cut -c1-12)
  echo "BLOCKED by governance hook (SEC-SECRETS-01): content matches a live secret pattern (${MATCH}…). Real secrets belong in .env or a vault — reference them by variable name. If this is a fixture, make it an obvious fake (e.g. contain 'EXAMPLE'). If it leaked from a real source, rotate it now (SEC-SECRETS-05)." >&2
  exit 2
fi
exit 0
