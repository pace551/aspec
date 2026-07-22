# CLAUDE.md — wordfreq

Word-frequency CLI. Worked example for STK-GO: `cmd/` + `internal/` layout, table-driven
stdlib tests, sentinel errors wrapped with `%w`, `context.Context` first on the blocking
path, coverage.out feeding the ratchet.

Governed project — tier and applicable standards in `GOVERNANCE.md`; run
`/verify-compliance` before calling any work done (Constitution C2).

## Structure

```
examples/go/
├── go.mod                        # module + go directive, tidy (STK-GO-06)
├── .golangci.yml                 # house lint config (v2: standard set + gosec)
├── cmd/wordfreq/
│   ├── main.go                   # thin main → run(ctx, args, stdin, out) error
│   └── main_test.go              # e2e: file, stdin, sentinel, missing file
└── internal/freq/
    ├── freq.go                   # Count/Top/Words; ErrEmptyInput sentinel
    └── freq_test.go              # table-driven with t.Run subtests
```

## Commands

All commands runnable verbatim from repo root:

```bash
scripts/lint.sh                       # gofmt + go vet + golangci-lint (same gate as hook and CI)
scripts/test.sh                       # go test -coverprofile=coverage.out (same gate as hook and CI)
go run ./cmd/wordfreq -top 5 FILE     # run the thing (reads stdin without FILE)
```

## Gotchas

- `#nosec G304` on `os.Open` in main.go is justified inline: opening the user-named
  file is the program's purpose (STK-GO-02 requires the trailing reason).
- `scripts/lint.sh` degrades loudly when golangci-lint is missing; install the house
  runner with `brew install golangci-lint` for the full gate locally.
