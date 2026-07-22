#!/usr/bin/env bash
# lint.sh — STK-GO-01/-02 gate. The pre-commit hook and the CI lint job run this same
# script (scripts contract, _common/README.md). golangci-lint is the house runner;
# absence degrades LOUDLY (staticcheck, then gofmt+vet floor) — never silently.
set -euo pipefail
cd "$(dirname "$0")/.."

unformatted=$(gofmt -l .)
if [ -n "$unformatted" ]; then
  echo "gofmt: needs formatting (run: gofmt -w .):" >&2
  echo "$unformatted" >&2
  exit 1
fi

go vet ./...

if command -v golangci-lint >/dev/null 2>&1; then
  golangci-lint run
elif command -v staticcheck >/dev/null 2>&1; then
  echo "lint.sh: golangci-lint not installed — staticcheck fallback (brew install golangci-lint for the house set)" >&2
  staticcheck ./...
else
  echo "lint.sh: golangci-lint/staticcheck not installed — gofmt+vet floor only (brew install golangci-lint)" >&2
fi
