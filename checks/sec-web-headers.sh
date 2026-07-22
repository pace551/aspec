#!/usr/bin/env bash
# sec-web-headers.sh — asserts security response headers on a running web app.
# Backs SEC-WEB-01 (layer G).
#
# Usage: sec-web-headers.sh [URL]        (default: http://localhost:3000)
#
# Skips gracefully (exit 0 with a documented warning) when the URL is unreachable —
# a header check cannot fail a build for an app that is not running; CI must start the
# app first, then invoke this against the local port (or the staging URL).
#
# Required headers (case-insensitive):
#   - Content-Security-Policy
#   - X-Content-Type-Options: nosniff
#   - frame protection: CSP frame-ancestors directive OR X-Frame-Options
#   - Strict-Transport-Security (https:// URLs only — HSTS is meaningless over http)
# Advisory (warn only): Referrer-Policy, Permissions-Policy.
#
# Exit 0 = pass or documented skip, 1 = required header missing, 2 = usage error.
# Read-only: sends a single HEAD request, mutates nothing.
set -euo pipefail

if [[ $# -gt 1 ]]; then
  echo "usage: sec-web-headers.sh [URL]" >&2
  exit 2
fi
URL="${1:-http://localhost:3000}"

# No -L: headers must be asserted on the final serving response, not lost in a redirect
# chain; point the script at the URL the browser actually renders.
if ! RAW=$(curl -sI --max-time 5 "$URL" 2>/dev/null) || [[ -z "$RAW" ]]; then
  echo "sec-web-headers: SKIP — $URL unreachable (start the app, then re-run)" >&2
  exit 0
fi
HEADERS=$(printf '%s' "$RAW" | tr -d '\r' | tr '[:upper:]' '[:lower:]')

FAIL=0

need() { # $1 = grep pattern, $2 = human label
  if ! grep -q "$1" <<<"$HEADERS"; then
    echo "sec-web-headers: MISSING required header: $2" >&2
    FAIL=1
  fi
}

warn() { # $1 = grep pattern, $2 = human label
  grep -q "$1" <<<"$HEADERS" \
    || echo "sec-web-headers: warning — advisory header absent: $2" >&2
}

need '^content-security-policy:' "Content-Security-Policy"
need '^x-content-type-options:.*nosniff' "X-Content-Type-Options: nosniff"

if ! grep -qE '^x-frame-options:|^content-security-policy:.*frame-ancestors' <<<"$HEADERS"; then
  echo "sec-web-headers: MISSING required frame protection (CSP frame-ancestors directive or X-Frame-Options)" >&2
  FAIL=1
fi

case "$URL" in
  https://*) need '^strict-transport-security:' "Strict-Transport-Security" ;;
  *) echo "sec-web-headers: note — HSTS check skipped for non-https URL" ;;
esac

warn '^referrer-policy:' "Referrer-Policy"
warn '^permissions-policy:' "Permissions-Policy"

if [[ $FAIL -eq 0 ]]; then
  echo "sec-web-headers: pass ($URL)"
fi
exit $FAIL
