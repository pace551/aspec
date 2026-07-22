# Scaffold `_common/`

Files every stack scaffold receives from `/bootstrap-repo`, regardless of stack:

| File | Destination | Purpose |
|---|---|---|
| `gitignore-base` | appended into the stack's `.gitignore` | env files, OS noise, editor dirs |
| `env.example.seed` | `.env.example` | header comment + placeholder discipline (SEC-SECRETS) |
| `CLAUDE.md.seed` | `CLAUDE.md` | project doc skeleton — `{{…}}` slots filled at bootstrap |
| `GOVERNANCE.md.seed` | `GOVERNANCE.md` | manifest skeleton — `/govern` fills the YAML |
| `githooks/pre-commit` | `.githooks/pre-commit` | format+lint (`scripts/lint.sh`) + staged secret scan |
| `githooks/pre-push` | `.githooks/pre-push` | tests + coverage ratchet (`scripts/test.sh`) |
| `install-git-hooks.sh` | run once by bootstrap | sets `core.hooksPath=.githooks`, vendors `.governance/` |

**The scripts contract** (what makes hooks, CI, and /verify-compliance agree): every
scaffold provides `scripts/lint.sh` (format check + lint) and `scripts/test.sh` (tests +
coverage emit). Hooks call the scripts; CI fragments run the same commands; nothing
defines "passing" twice. `.governance/` in each project holds vendored copies of
`coverage-ratchet.py` and `secret-scan.sh` so hooks and CI work without the governance
repo present (re-vendored by `/bootstrap-repo` on upgrade).
