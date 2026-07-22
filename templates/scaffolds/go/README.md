# Scaffold: go (STK-GO)

Copied by `/bootstrap-repo` for new Go projects. On copy, bootstrap:

1. Fills `{{MODULE_PATH}}` in `go.mod`, renames `cmd/{{app}}/` and
   `internal/{{package}}/` to real names, and fixes the import in `main.go`.
2. Layers in `_common/` (CLAUDE.md.seed → `CLAUDE.md`, GOVERNANCE.md.seed →
   `GOVERNANCE.md`, appends `gitignore-base` to `.gitignore`, installs git hooks via
   `install-git-hooks.sh`).
3. Runs `go mod tidy` (commit `go.mod` + `go.sum` — STK-GO-06).

Scripts contract (`_common/README.md`): hooks, CI (`templates/ci/go.yml`), and
`/verify-compliance` all run `scripts/lint.sh` and `scripts/test.sh`. The house lint
runner is golangci-lint (`brew install golangci-lint`); `scripts/lint.sh` degrades
loudly to staticcheck, then to gofmt+vet, when it is missing (STK-GO-02).

Worked example built from this scaffold: `examples/go/`.
