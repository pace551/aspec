#!/usr/bin/env bash
# install.sh — install the governance framework's global surfaces.
#
#   checks/install.sh              install/refresh skills into ~/.claude/skills (safe, default)
#   checks/install.sh --global-claude   also write ~/.claude/CLAUDE.md governance pointer
#   checks/install.sh --hooks      also wire hooks into ~/.claude/settings.json
#                                  (BLOCKING secret-scan hook — run only with explicit
#                                  user consent; makes a timestamped settings backup)
#
# Idempotent; canonical sources stay in this repo (edit here, re-run to propagate).
set -euo pipefail

GOV="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DST="$HOME/.claude/skills"
DO_CLAUDE=false
DO_HOOKS=false
for arg in "$@"; do
  case "$arg" in
    --global-claude) DO_CLAUDE=true ;;
    --hooks) DO_HOOKS=true ;;
    *) echo "install.sh: unknown flag $arg" >&2; exit 2 ;;
  esac
done

# --- skills ---
mkdir -p "$SKILLS_DST"
for skill in govern bootstrap-repo verify-compliance harvest-learnings evolve-standards; do
  mkdir -p "$SKILLS_DST/$skill"
  cp "$GOV/skills/$skill/SKILL.md" "$SKILLS_DST/$skill/SKILL.md"
  echo "installed skill: /$skill"
done

# --- global CLAUDE.md ---
if $DO_CLAUDE; then
  TARGET="$HOME/.claude/CLAUDE.md"
  if [ -f "$TARGET" ] && ! grep -q "governance framework" "$TARGET"; then
    echo "install.sh: $TARGET exists and is not governance-managed — not overwriting" >&2
  else
    cat > "$TARGET" <<'EOF'
# Global rules — governance framework

Every task is governed by the personal governance framework at
`~/Dev/claude-code/governance/` (this file is its only always-on pointer).

1. The Constitution applies to every task, every tier: read
   `~/Dev/claude-code/governance/constitution/CONSTITUTION.md` before substantive work.
2. Before any chunky task (multi-file change, new project, deploy, anything with side
   effects): run `/govern` to classify the tier and load the applicable standards.
3. Work is DONE only when `/verify-compliance` passes for the project's tier
   (Constitution C2). Never declare done while it fails.
4. In a repo with a `GOVERNANCE.md`, honor its pins, waivers, and approvals.
5. Governance friction (missing/wrong/heavy rule) → `/harvest-learnings`, never ad-hoc
   standard edits.
EOF
    echo "wrote $TARGET"
  fi
fi

# --- hooks ---
if $DO_HOOKS; then
  SETTINGS="$HOME/.claude/settings.json"
  BACKUP="$SETTINGS.bak.$(date +%Y%m%d%H%M%S)"
  cp "$SETTINGS" "$BACKUP"
  python3 - "$SETTINGS" "$GOV" <<'EOF'
import json, sys
path, gov = sys.argv[1], sys.argv[2]
with open(path) as f:
    s = json.load(f)
hooks = s.setdefault("hooks", {})

def ensure(event, matcher, cmd, timeout=10):
    entries = hooks.setdefault(event, [])
    for e in entries:
        for h in e.get("hooks", []):
            if h.get("command") == cmd:
                return
    entry = {"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]}
    if matcher is not None:
        entry["matcher"] = matcher
    entries.append(entry)

ensure("PreToolUse", "Write|Edit", f"bash {gov}/hooks/pre-write-secret-scan.sh")
ensure("SessionStart", None, f"bash {gov}/hooks/session-start-banner.sh")
with open(path, "w") as f:
    json.dump(s, f, indent=2)
    f.write("\n")
print(f"hooks wired into {path}")
EOF
  echo "settings backup: $BACKUP"
fi

echo "install.sh: done"
