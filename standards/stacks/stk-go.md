---
id: STK-GO
title: Go Stack
family: STK
version: 1.0.0
status: active
tiers:
  T1: required
  T2: required
  T3: required
  T4: required
stacks: [go]
triggers:
  - go
  - golang
  - go.mod
  - gofmt
  - goroutine
  - go test
  - staticcheck
  - golangci-lint
requires: [SEC-SECRETS]
verification:
  - cmd: "sh -c 'test -z \"$(gofmt -l .)\"'"
    expect: "exit 0 — no file needs reformatting"
    layer: G
    rules: [STK-GO-01]
  - cmd: "go vet ./..."
    expect: "exit 0"
    layer: G
    rules: [STK-GO-02]
  - cmd: "scripts/lint.sh"
    expect: "exit 0 — gofmt + go vet + golangci-lint (staticcheck fallback when golangci-lint absent; degrade is loud, never silent)"
    layer: G
    rules: [STK-GO-02]
  - cmd: "go test ./..."
    expect: "exit 0 — packages with no test files pass trivially (fresh scaffold tolerated; TST-POLICY governs test existence)"
    layer: G
    rules: [STK-GO-03]
  - cmd: "sh -c 'go test ./... -coverprofile=coverage.out >/dev/null 2>&1; python3 ~/Dev/claude-code/governance/checks/coverage-ratchet.py --check'"
    expect: "coverage ≥ committed .coverage-baseline (read-only check; coverage.out is gitignored output)"
    layer: G
    rules: [STK-GO-03]
    tiers: [T2, T3, T4]
  - cmd: "go mod tidy -diff"
    expect: "exit 0 — go.mod/go.sum already tidy (prints the diff otherwise, changes nothing)"
    layer: G
    rules: [STK-GO-06]
  - cmd: "sh -c 'if command -v govulncheck >/dev/null 2>&1; then govulncheck ./...; else go run golang.org/x/vuln/cmd/govulncheck@latest ./...; fi'"
    expect: "exit 0 (per-CVE waivers handled by /verify-compliance)"
    layer: G
    rules: [STK-GO-07]
    tiers: [T2, T3, T4]
  - cmd: "attest: errors are wrapped with %w and matched with errors.Is/As against sentinel or typed errors — never string matching"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-GO-04]
  - cmd: "attest: every blocking or cancellable function takes context.Context as its first parameter"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-GO-05]
  - cmd: "attest: layout follows cmd/ + internal/ with exported surface deliberate"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [STK-GO-08]
last_review: 2026-07-22
---

# Go Stack (STK-GO)

## Abstract

House rules for every Go project: gofmt/goimports formatting is non-negotiable, `go vet`
+ staticcheck must pass with golangci-lint as the house runner, tests are table-driven on
the stdlib `testing` package with `-coverprofile` feeding the coverage ratchet, errors
wrap with `%w` and match with `errors.Is`, anything blocking takes `context.Context`
first, `go.mod`/`go.sum` stay tidy and committed, govulncheck is the SCA gate. Identical
toolchain at every tier — tier scales test depth and CI, not tool choice. Scaffold:
`templates/scaffolds/go/` · CI: `templates/ci/go.yml` · worked example: `examples/go/`.

## Normative Rules

### STK-GO-01 — Code MUST be gofmt/goimports clean; formatting is not a discussion

**Tiers**: all required — **Layer**: G

`gofmt -l .` reports nothing, ever; goimports ordering (stdlib / external / module groups)
is enforced through golangci-lint's formatters. There is no house style beyond the tools'
output — no line-length debates, no custom import grouping. Generated files carry the
standard `// Code generated … DO NOT EDIT.` header and are excluded from hand-edit
expectations but still formatted.

### STK-GO-02 — `go vet` and staticcheck MUST pass; golangci-lint is the house runner

**Tiers**: all required — **Layer**: G

`scripts/lint.sh` runs gofmt + `go vet` always, then golangci-lint (config:
`.golangci.yml` from the scaffold — `version: "2"`, standard default linters which
include staticcheck and errcheck, plus gosec; gofmt/goimports as formatters). When
golangci-lint isn't installed locally the script degrades loudly to standalone
staticcheck, and to gofmt+vet only as the floor — it never silently passes. Suppressions
are inline `//nolint:<linter> // reason`, never config-file exclusion lists added to make
a gate green. errcheck findings mean handling the error, not `_ =` discards without a
reason comment.

### STK-GO-03 — Tests MUST use the stdlib `testing` package, table-driven, with the coverage ratchet

**Tiers**: all required — **Layer**: G

No assertion/test frameworks (testify et al.) — table-driven tests with subtests
(`t.Run`) and plain `got`/`want` comparisons (`go-cmp` MAY be used for deep diffs).
"`go test ./...` green" is required at every tier; at T2+ coverage from
`go test -coverprofile=coverage.out` feeds `checks/coverage-ratchet.py` (it reads
`coverage.out` via `go tool cover -func`) and the committed `.coverage-baseline` only
moves up. Parallel-safe tests call `t.Parallel()`; anything touching the filesystem uses
`t.TempDir()`.

### STK-GO-04 — Errors MUST be wrapped with `%w` and matched with `errors.Is`/`errors.As`

**Tiers**: all required — **Layer**: A (attestation)

Every error crossing a function boundary adds context:
`fmt.Errorf("loading config %s: %w", path, err)`. Errors callers are expected to branch
on are exported sentinels (`var ErrNotFound = errors.New(…)`) or typed errors, matched
with `errors.Is`/`errors.As` — never `strings.Contains(err.Error(), …)`. Errors are
handled once: either wrapped-and-returned or logged-and-handled, not both (double-logging
is the Go log-spam anti-pattern).

### STK-GO-05 — `context.Context` MUST be the first parameter of anything blocking or cancellable

**Tiers**: all required — **Layer**: A (attestation)

Any function doing I/O, sleeping, looping unboundedly, or calling something that does
takes `ctx context.Context` first and honors cancellation (`ctx.Err()` checks in loops,
`req.WithContext`/context-aware APIs elsewhere). Contexts are passed, never stored in
structs; `context.Background()` appears only in `main`, tests, and service init.
`context.TODO()` in committed code is a tracked TODO, not a resting state.

### STK-GO-06 — `go.mod` and `go.sum` MUST be tidy and committed

**Tiers**: all required — **Layer**: G

`go mod tidy -diff` reports no changes on every commit — dependencies the code doesn't
use don't linger, and nothing used is missing. `go.sum` is committed always (it is the
integrity lockfile). The `go` directive pins the toolchain line the project targets;
upgrades are deliberate commits, not side effects (cadence in `DEV-DEPS`).

### STK-GO-07 — govulncheck MUST be clean, or findings waived per-CVE

**Tiers**: T1 advisory · T2–T4 required — **Layer**: G

`govulncheck ./...` is the SCA gate — chosen over generic scanners because it is
call-graph aware: it only fails on vulnerable *symbols actually reached*, so findings are
near-zero-noise and each one is real. Fix by upgrade first; waive per-CVE in
`GOVERNANCE.md` (`{rule_id: STK-GO-07, reason, expires}`) only with an unreachability
argument govulncheck itself couldn't see.

### STK-GO-08 — Layout SHOULD follow `cmd/` + `internal/`, with exported surface deliberate

**Tiers**: all advisory — **Layer**: A (attestation)

Binaries live in `cmd/{app}/main.go` (thin: flag parsing, wiring, exit codes); logic
lives in `internal/{pkg}/` where the compiler enforces privacy. `pkg/` is reserved for
code deliberately published for outside import — a solo-scale repo usually has none. No
`util`/`common`/`helpers` packages: name packages by what they provide. `main.go`
delegates to a `run(ctx, args, stdout) error` function so the binary itself is testable.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `test -z "$(gofmt -l .)"` | no files listed | STK-GO-01 |
| 2 | `go vet ./...` | exit 0 | STK-GO-02 |
| 3 | `scripts/lint.sh` | exit 0 (golangci-lint; loud staticcheck/vet fallback) | STK-GO-02 |
| 4 | `go test ./...` | exit 0 | STK-GO-03 |
| 5 | coverprofile → `coverage-ratchet.py --check` (T2+) | ≥ `.coverage-baseline` | STK-GO-03 |
| 6 | `go mod tidy -diff` | exit 0, empty diff | STK-GO-06 |
| 7 | `govulncheck ./...` (T2+; `go run …@latest` if not installed) | exit 0 / per-CVE waivers | STK-GO-07 |
| 8-10 | attestation checklist (one per rule) | explicit yes | STK-GO-04, -05, -08 |

**Remediation:** gofmt fail → `gofmt -w .` · errcheck finding → handle the error or
`_ = f() // reason` · staticcheck SA-class finding → it's a bug, fix it ·
`go mod tidy -diff` fail → run `go mod tidy` and commit · govulncheck hit →
`go get module@fixed && go mod tidy` · ratchet fail → add tests for the new code, don't
lower the baseline.

## Worked Example

`examples/go/` is the living example (a word-frequency CLI). Minimal shape:

```
myproj/
├── go.mod                  # module path + go directive (go.sum once deps exist)
├── .golangci.yml           # house config (v2: standard set + gosec; gofmt/goimports)
├── .coverage-baseline      # written by first ratchet run, committed
├── .env.example            # per SEC-SECRETS
├── cmd/myproj/main.go      # thin main → run(ctx, args, stdout) error
├── internal/freq/freq.go   # logic; errors wrapped, ctx first
└── internal/freq/freq_test.go  # table-driven, t.Run subtests
```

```go
// internal/freq/freq.go — the idioms in five lines
var ErrEmptyInput = errors.New("empty input")

func Count(ctx context.Context, r io.Reader) (map[string]int, error) {  // ctx first (STK-GO-05)
    // ...
    return nil, fmt.Errorf("scanning input: %w", err)  // wrap with %w (STK-GO-04)
}
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `err.Error()` string matching | Breaks on any wording change; unwrappable | Sentinels + `errors.Is` (STK-GO-04) |
| `fmt.Errorf("...: %v", err)` when callers branch | `%v` severs the chain; `errors.Is` stops working | `%w` (STK-GO-04) |
| Storing `ctx` in a struct field | Lifetime confusion; cancellation stops propagating | Pass ctx per call (STK-GO-05) |
| testify/assert everywhere | Framework dialect over language; obscures failures | Table-driven stdlib tests (STK-GO-03) |
| `panic` for expected failure paths | Crashes callers who could have handled it | Return errors; panic only for programmer bugs |
| Log-and-return the same error | Every layer logs it; grep shows 5 copies | Handle once: wrap-and-return or log-and-handle |
| `util`/`common` package | Becomes an unprincipled dumping ground | Package named for what it provides (STK-GO-08) |
| Ignoring goroutine lifetimes (`go f()` fire-and-forget) | Leaks; errors vanish | errgroup / explicit done-channels, ctx-aware |

## References

- Effective Go + Google Go Style Guide — source of the layout/naming/error idioms.
- staticcheck docs (SA checks) — the bug-class catalog behind STK-GO-02.
- golangci-lint v2 docs — house runner and `.golangci.yml` schema.
- `go.dev/blog/vuln` (govulncheck) — call-graph-aware SCA rationale for STK-GO-07.
- Go blog "Contexts and structs" — rationale for STK-GO-05's pass-don't-store rule.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
