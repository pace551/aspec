package main

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"example.com/wordfreq/internal/freq"
)

func TestRunReadsFileAndPrintsTop(t *testing.T) {
	t.Parallel()
	path := filepath.Join(t.TempDir(), "in.txt")
	if err := os.WriteFile(path, []byte("go go go\nrust rust\nzig\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	var out strings.Builder
	if err := run(context.Background(), []string{"-top", "2", path}, nil, &out); err != nil {
		t.Fatalf("run() error = %v", err)
	}
	if got, want := out.String(), "go 3\nrust 2\n"; got != want {
		t.Errorf("run() output = %q, want %q", got, want)
	}
}

func TestRunReadsStdinWhenNoFile(t *testing.T) {
	t.Parallel()
	var out strings.Builder
	err := run(context.Background(), nil, strings.NewReader("a b a\n"), &out)
	if err != nil {
		t.Fatalf("run() error = %v", err)
	}
	if got, want := out.String(), "a 2\nb 1\n"; got != want {
		t.Errorf("run() output = %q, want %q", got, want)
	}
}

func TestRunPropagatesSentinelForEmptyInput(t *testing.T) {
	t.Parallel()
	var out strings.Builder
	err := run(context.Background(), nil, strings.NewReader(""), &out)
	if !errors.Is(err, freq.ErrEmptyInput) {
		t.Fatalf("run() error = %v, want freq.ErrEmptyInput", err)
	}
}

func TestRunFailsOnMissingFile(t *testing.T) {
	t.Parallel()
	var out strings.Builder
	err := run(context.Background(), []string{filepath.Join(t.TempDir(), "nope.txt")}, nil, &out)
	if err == nil || !strings.Contains(err.Error(), "opening input") {
		t.Fatalf("run() error = %v, want wrapped opening-input error", err)
	}
}
