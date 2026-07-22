#!/usr/bin/env bash
# inf-tf-scan.sh — IaC format/validate/lint/security scan. Backs INF-TF-04 (layer G);
# the CI fragment templates/ci/_fragments/iac-scan.yml runs the same gates with pinned
# actions. Finds every directory containing *.tf (skipping .terraform/ caches) and runs:
#
#   fmt -check   via tofu (house default per INF-TF-01), falling back to terraform when
#                only it is installed (the two are format-compatible)
#   validate     in a temporary COPY of the project tree — `init -backend=false` writes
#                .terraform/ and can write .terraform.lock.hcl, and verification must be
#                read-only, so the working tree is never touched
#   tflint       if installed (brew install tflint)
#   checkov      if installed (pipx install checkov)
#
# Missing tools degrade to documented warnings (secret-scan.sh pattern): the gate reports
# what it could not run instead of silently passing. An init failure (offline, provider
# mirror unreachable, unsupported core version) downgrades validate to a warning — CI,
# where iac-scan.yml always has the tools and the network, remains the strict backstop.
#
# Usage: inf-tf-scan.sh [--project DIR]
# Exit 0 = pass (possibly with warnings), 1 = findings, 2 = usage/environment error.
set -euo pipefail

PROJECT="."
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?--project needs a directory}"; shift 2 ;;
    *) echo "inf-tf-scan: unknown argument: $1 (usage: inf-tf-scan.sh [--project DIR])" >&2; exit 2 ;;
  esac
done
cd "$PROJECT" 2>/dev/null || { echo "inf-tf-scan: cannot cd to '$PROJECT'" >&2; exit 2; }

# ---- discover *.tf directories -----------------------------------------------------
TF_DIRS=$(find . -name '*.tf' \
    -not -path '*/.terraform/*' -not -path './.git/*' \
    -not -path '*/node_modules/*' -not -path '*/.venv/*' \
    -exec dirname {} \; | sort -u)
if [[ -z "$TF_DIRS" ]]; then
  echo "inf-tf-scan: no *.tf files found — nothing to scan"
  exit 0
fi
echo "inf-tf-scan: scanning:" $TF_DIRS

FAIL=0
WARN=0

warn() { echo "inf-tf-scan: WARNING — $*" >&2; WARN=1; }

# ---- pick the CLI: tofu is the house default, terraform an accepted stand-in --------
TF=""
if command -v tofu >/dev/null 2>&1; then
  TF="tofu"
elif command -v terraform >/dev/null 2>&1; then
  TF="terraform"
  warn "tofu not installed; using terraform for fmt/validate (house default is OpenTofu: brew install opentofu)"
else
  warn "neither tofu nor terraform installed — fmt/validate skipped (brew install opentofu)"
fi

# ---- fmt -check + validate ----------------------------------------------------------
if [[ -n "$TF" ]]; then
  for d in $TF_DIRS; do
    if ! (cd "$d" && "$TF" fmt -check >/dev/null); then
      echo "inf-tf-scan: FAIL — $d is not '$TF fmt' formatted (run: $TF fmt $d)" >&2
      FAIL=1
    fi
  done

  # validate needs init; copy the tree so ../../modules refs resolve and the working
  # tree stays untouched (read-only contract).
  TMP=$(mktemp -d "${TMPDIR:-/tmp}/inf-tf-scan.XXXXXX")
  trap 'rm -rf "$TMP"' EXIT
  tar --exclude .git --exclude .terraform --exclude node_modules --exclude .venv \
      -cf - . 2>/dev/null | (cd "$TMP" && tar -xf -)
  for d in $TF_DIRS; do
    if (cd "$TMP/$d" && "$TF" init -backend=false -input=false >/dev/null 2>&1); then
      if ! (cd "$TMP/$d" && "$TF" validate -no-color); then
        echo "inf-tf-scan: FAIL — $TF validate failed in $d" >&2
        FAIL=1
      fi
    else
      warn "validate skipped for $d — '$TF init -backend=false' failed (offline, provider download blocked, or core version mismatch); CI iac-scan remains the strict gate"
    fi
  done
fi

# ---- tflint -------------------------------------------------------------------------
if command -v tflint >/dev/null 2>&1; then
  for d in $TF_DIRS; do
    if ! tflint --chdir "$d"; then
      echo "inf-tf-scan: FAIL — tflint findings in $d" >&2
      FAIL=1
    fi
  done
else
  warn "tflint not installed; skipping (brew install tflint)"
fi

# ---- checkov ------------------------------------------------------------------------
if command -v checkov >/dev/null 2>&1; then
  for d in $TF_DIRS; do
    if ! checkov -d "$d" --framework terraform --quiet --compact; then
      echo "inf-tf-scan: FAIL — checkov findings in $d" >&2
      FAIL=1
    fi
  done
else
  warn "checkov not installed; skipping (pipx install checkov)"
fi

if [[ $FAIL -eq 0 ]]; then
  [[ $WARN -eq 1 ]] && echo "inf-tf-scan: pass (with warnings above — install missing tools for full coverage)" \
                    || echo "inf-tf-scan: clean"
fi
exit $FAIL
