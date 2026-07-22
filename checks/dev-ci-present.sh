#!/usr/bin/env bash
# dev-ci-present.sh — DEV-CI gate: verify .github/workflows/ declares the required job
# set for a tier. Grep-based and graceful: a job counts as present when any workflow file
# (a) is named after it (fragment copied as-is, e.g. lint.yml), (b) declares a job key
# with that exact name, (c) `uses:` a reusable workflow file named after it, or
# (d) has a `name:` exactly matching it.
#
# Usage: dev-ci-present.sh --tier T1|T2|T3|T4 [--project DIR]
# Exit 0 = pass, 1 = required jobs missing, 2 = usage/environment error.
set -euo pipefail

usage() { echo "usage: dev-ci-present.sh --tier T1|T2|T3|T4 [--project DIR]" >&2; }

TIER=""
PROJECT="."
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tier)    TIER="${2:-}"; shift 2 ;;
    --project) PROJECT="${2:-}"; shift 2 ;;
    *) usage; exit 2 ;;
  esac
done
[[ -n "$TIER" ]] || { usage; exit 2; }
cd "$PROJECT" 2>/dev/null || { echo "dev-ci-present: cannot cd to $PROJECT" >&2; exit 2; }

case "$TIER" in
  T1)
    echo "dev-ci-present: T1 — CI not required; git hooks carry the gates (DEV-CI-02)"
    exit 0 ;;
  T2)
    if [[ -d .github/workflows ]]; then
      echo "dev-ci-present: T2 — CI present (optional at this tier); hooks remain mandatory"
    else
      echo "dev-ci-present: T2 — no CI (optional at this tier); hooks carry the gates"
    fi
    exit 0 ;;
  T3) required=(lint typecheck test coverage-ratchet gitleaks sast sca) ;;
  T4) required=(lint typecheck test coverage-ratchet gitleaks sast sca license-audit) ;;
  *) usage; exit 2 ;;
esac

WF=".github/workflows"
if [[ ! -d "$WF" ]]; then
  echo "dev-ci-present: FAIL — $WF/ missing (CI is mandatory at $TIER)" >&2
  exit 1
fi

shopt -s nullglob
files=("$WF"/*.yml "$WF"/*.yaml)
if [[ ${#files[@]} -eq 0 ]]; then
  echo "dev-ci-present: FAIL — no workflow files in $WF/" >&2
  exit 1
fi

missing=()
for job in "${required[@]}"; do
  found=0
  for f in "${files[@]}"; do
    base="$(basename "$f")"
    if [[ "$base" == "$job.yml" || "$base" == "$job.yaml" ]]; then
      found=1; break
    fi
    if grep -qiE "(^[[:space:]]*${job}:[[:space:]]*$)|(uses:.*[/[:space:]\"']${job}\.ya?ml)|(^[[:space:]]*name:[[:space:]]*[\"']?${job}[\"']?[[:space:]]*$)" "$f"; then
      found=1; break
    fi
  done
  [[ $found -eq 1 ]] || missing+=("$job")
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "dev-ci-present: FAIL — $TIER requires CI job(s) not found: ${missing[*]}" >&2
  echo "dev-ci-present: compose them from templates/ci/_fragments/ (DEV-CI-01)" >&2
  exit 1
fi
echo "dev-ci-present: $TIER job set present (${required[*]})"
