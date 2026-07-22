#!/usr/bin/env bash
# inf-container-scan.sh — Dockerfile lint + misconfiguration scan. Backs
# INF-CONTAINERS-01/-02/-03/-05 (layer G). Finds every Dockerfile (Dockerfile,
# Dockerfile.*, *.Dockerfile) and runs:
#
#   hadolint      if installed (brew install hadolint) — Dockerfile best-practice lint
#   trivy config  if installed (brew install trivy) — IaC misconfig scan, no image
#                 build or daemon needed (image scanning proper happens at the
#                 registry: ECR scan-on-push, per INF-CONTAINERS-05)
#
# When neither is installed the script degrades to a built-in high-signal check
# (secret-scan.sh pattern) so the gate never silently disappears:
#   - FROM pinned to :latest, or untagged            -> FAIL (INF-CONTAINERS-03)
#   - no USER instruction (container runs as root)   -> FAIL (INF-CONTAINERS-02)
#   - Dockerfile present but no .dockerignore        -> WARN (INF-CONTAINERS-04 has
#                                                       its own G check)
#
# Usage: inf-container-scan.sh [--project DIR]
# Exit 0 = pass (possibly with warnings), 1 = findings, 2 = usage/environment error.
set -euo pipefail

PROJECT="."
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?--project needs a directory}"; shift 2 ;;
    *) echo "inf-container-scan: unknown argument: $1 (usage: inf-container-scan.sh [--project DIR])" >&2; exit 2 ;;
  esac
done
cd "$PROJECT" 2>/dev/null || { echo "inf-container-scan: cannot cd to '$PROJECT'" >&2; exit 2; }

DOCKERFILES=$(find . \( -name 'Dockerfile' -o -name 'Dockerfile.*' -o -name '*.Dockerfile' \) \
    -not -path './.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' | sort)
if [[ -z "$DOCKERFILES" ]]; then
  echo "inf-container-scan: no Dockerfiles found — nothing to scan"
  exit 0
fi
echo "inf-container-scan: scanning:" $DOCKERFILES

FAIL=0
WARN=0
RAN_LINTER=0

warn() { echo "inf-container-scan: WARNING — $*" >&2; WARN=1; }

# ---- hadolint -----------------------------------------------------------------------
if command -v hadolint >/dev/null 2>&1; then
  RAN_LINTER=1
  for f in $DOCKERFILES; do
    if ! hadolint "$f"; then
      echo "inf-container-scan: FAIL — hadolint findings in $f" >&2
      FAIL=1
    fi
  done
else
  warn "hadolint not installed; skipping best-practice lint (brew install hadolint)"
fi

# ---- trivy config (misconfig scan; does not need a built image) ---------------------
if command -v trivy >/dev/null 2>&1; then
  RAN_LINTER=1
  for f in $DOCKERFILES; do
    if ! trivy config --exit-code 1 --quiet "$f"; then
      echo "inf-container-scan: FAIL — trivy misconfiguration findings in $f" >&2
      FAIL=1
    fi
  done
else
  warn "trivy not installed; skipping misconfig scan (brew install trivy)"
fi

# ---- built-in fallback: only when no real linter ran --------------------------------
if [[ $RAN_LINTER -eq 0 ]]; then
  echo "inf-container-scan: no scanner installed — using built-in fallback checks" >&2
  for f in $DOCKERFILES; do
    # collect stage names so `FROM <stage>` refs aren't flagged as untagged images
    STAGES=$(awk 'toupper($1)=="FROM" { for (i=1;i<NF;i++) if (toupper($i)=="AS") print $(i+1) }' "$f")
    while read -r image; do
      [[ -z "$image" ]] && continue
      if echo "$STAGES" | grep -qx "$image"; then continue; fi           # stage ref
      if [[ "$image" == *":latest" || "$image" != *":"* ]]; then
        echo "inf-container-scan: FAIL — $f: base image '$image' is unpinned (tag it; digest-pin at T3+, INF-CONTAINERS-03)" >&2
        FAIL=1
      fi
    done < <(awk 'toupper($1)=="FROM" { print $2 }' "$f")
    if ! grep -qiE '^USER[[:space:]]' "$f"; then
      echo "inf-container-scan: FAIL — $f: no USER instruction; container runs as root (INF-CONTAINERS-02)" >&2
      FAIL=1
    fi
  done
fi

if [[ ! -f .dockerignore ]]; then
  warn "no .dockerignore at project root (INF-CONTAINERS-04; scaffold: templates/scaffolds/containers/)"
fi

if [[ $FAIL -eq 0 ]]; then
  [[ $WARN -eq 1 ]] && echo "inf-container-scan: pass (with warnings above — install hadolint/trivy for full coverage)" \
                    || echo "inf-container-scan: clean"
fi
exit $FAIL
