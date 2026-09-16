#!/usr/bin/env bash
# install.sh — install ASPEC (Agent Safety, Performance, Enforcement & Compliance).
#
#   checks/install.sh              install/refresh skills into ~/.claude/skills (safe, default)
#   checks/install.sh --global-claude   also write ~/.claude/CLAUDE.md governance pointer
#   checks/install.sh --hooks      also wire hooks into ~/.claude/settings.json
#                                  (BLOCKING secret-scan hook — run only with explicit
#                                  user consent; makes a timestamped settings backup)
#
# On first run, writes ~/.claude/aspec.json with resolved paths (governance repo,
# Obsidian vault). Skills are templated with these paths at install time so the
# canonical sources in skills/ stay portable.
#
# Idempotent; canonical sources stay in this repo (edit here, re-run to propagate).
set -euo pipefail

GOV="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DST="$HOME/.claude/skills"
CONFIG="$HOME/.claude/aspec.json"
DO_CLAUDE=false
DO_HOOKS=false
for arg in "$@"; do
  case "$arg" in
    --global-claude) DO_CLAUDE=true ;;
    --hooks) DO_HOOKS=true ;;
    *) echo "install.sh: unknown flag $arg" >&2; exit 2 ;;
  esac
done

# --- config (first run or paths changed) ---
VAULT_PATH=""
if [ -f "$CONFIG" ]; then
  VAULT_PATH=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('obsidian_vault',''))" 2>/dev/null || true)
fi

if [ -z "$VAULT_PATH" ] || [ ! -d "$VAULT_PATH" ]; then
  DEFAULT_VAULT="$HOME/Documents/Obsidian/Personal"
  echo "ASPEC needs your Obsidian vault path for /harvest-learnings and /evolve-standards."
  echo "  (leave blank to use: $DEFAULT_VAULT)"
  echo "  (enter 'none' if you don't use Obsidian — learnings capture will be skipped)"
  printf "  Vault path: "
  read -r VAULT_INPUT
  if [ "$VAULT_INPUT" = "none" ]; then
    VAULT_PATH="none"
  elif [ -n "$VAULT_INPUT" ]; then
    VAULT_PATH="$VAULT_INPUT"
  else
    VAULT_PATH="$DEFAULT_VAULT"
  fi
fi

python3 - "$CONFIG" "$GOV" "$VAULT_PATH" <<'PYEOF'
import json, sys
path, gov, vault = sys.argv[1], sys.argv[2], sys.argv[3]
config = {"governance_repo": gov, "obsidian_vault": vault}
with open(path, "w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")
print(f"wrote {path}")
PYEOF

# --- skills (templated with resolved paths) ---
mkdir -p "$SKILLS_DST"
INBOX="$VAULT_PATH/Inbox"
for skill in govern bootstrap-repo verify-compliance harvest-learnings evolve-standards; do
  mkdir -p "$SKILLS_DST/$skill"
  sed \
    -e "s|\\\$GOV|$GOV|g" \
    -e "s|\\\$VAULT|$VAULT_PATH|g" \
    -e "s|\\\$INBOX|$INBOX|g" \
    "$GOV/skills/$skill/SKILL.md" > "$SKILLS_DST/$skill/SKILL.md"
  echo "installed skill: /$skill"
done

# --- global CLAUDE.md ---
if $DO_CLAUDE; then
  TARGET="$HOME/.claude/CLAUDE.md"
  if [ -f "$TARGET" ] && ! grep -q "ASPEC\|governance framework" "$TARGET"; then
    echo "install.sh: $TARGET exists and is not governance-managed — not overwriting" >&2
  else
    cat > "$TARGET" <<EOFCLAUDE
# Global rules — ASPEC (Agent Safety, Performance, Enforcement & Compliance)

Every task is governed by ASPEC at
\`$GOV\` (this file is its only always-on pointer).

1. The Constitution applies to every task, every tier: read
   \`$GOV/constitution/CONSTITUTION.md\` before substantive work.
2. Before any chunky task (multi-file change, new project, deploy, anything with side
   effects): run \`/govern\` to classify the tier and load the applicable standards.
3. Work is DONE only when \`/verify-compliance\` passes for the project's tier
   (Constitution C2). Never declare done while it fails.
4. In a repo with a \`GOVERNANCE.md\`, honor its pins, waivers, and approvals.
5. Governance friction (missing/wrong/heavy rule) → \`/harvest-learnings\`, never ad-hoc
   standard edits.
EOFCLAUDE
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
