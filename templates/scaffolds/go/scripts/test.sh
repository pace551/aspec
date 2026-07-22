#!/usr/bin/env bash
# test.sh — STK-GO-03 gate: go test + coverage.out (the format coverage-ratchet.py
# reads via `go tool cover -func`). The pre-push hook and the CI test job run this
# same script. Packages without tests pass trivially — TST-POLICY governs test
# existence, not this script.
set -euo pipefail
cd "$(dirname "$0")/.."

go test ./... -coverprofile=coverage.out -covermode=atomic
go tool cover -func=coverage.out | tail -1
