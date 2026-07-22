package freq

import (
	"context"
	"errors"
	"io"
	"reflect"
	"strings"
	"testing"
)

func TestWords(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name string
		line string
		want []string
	}{
		{"lowercases and splits on punctuation", "Hello, hello world!", []string{"hello", "hello", "world"}},
		{"digits count as word characters", "port 8080 open", []string{"port", "8080", "open"}},
		{"empty line yields no words", "  \t ", nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			got := Words(tt.line)
			if len(got) == 0 {
				got = nil
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("Words(%q) = %v, want %v", tt.line, got, tt.want)
			}
		})
	}
}

func TestCount(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name    string
		input   string
		want    map[string]int
		wantErr error
	}{
		{"counts across lines", "go go\ngo run", map[string]int{"go": 3, "run": 1}, nil},
		{"empty input is a sentinel error", "\n\n", nil, ErrEmptyInput},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			got, err := Count(context.Background(), strings.NewReader(tt.input))
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("Count() error = %v, want %v", err, tt.wantErr)
			}
			if tt.wantErr == nil && !reflect.DeepEqual(got, tt.want) {
				t.Errorf("Count() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestCountHonorsCancellation(t *testing.T) {
	t.Parallel()
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // cancelled before the first line is processed
	_, err := Count(ctx, strings.NewReader("some words\n"))
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("Count() error = %v, want context.Canceled", err)
	}
}

type failingReader struct{}

func (failingReader) Read([]byte) (int, error) { return 0, io.ErrUnexpectedEOF }

func TestCountWrapsReaderErrors(t *testing.T) {
	t.Parallel()
	_, err := Count(context.Background(), failingReader{})
	if !errors.Is(err, io.ErrUnexpectedEOF) {
		t.Fatalf("Count() error = %v, want wrapped io.ErrUnexpectedEOF", err)
	}
	if !strings.Contains(err.Error(), "scanning input") {
		t.Errorf("Count() error lacks context: %v", err)
	}
}

func TestTop(t *testing.T) {
	t.Parallel()
	counts := map[string]int{"b": 2, "a": 2, "z": 5, "q": 1}
	tests := []struct {
		name string
		n    int
		want []Entry
	}{
		{"orders count desc then word asc", 3, []Entry{{"z", 5}, {"a", 2}, {"b", 2}}},
		{"n larger than distinct words returns all", 10, []Entry{{"z", 5}, {"a", 2}, {"b", 2}, {"q", 1}}},
		{"n zero returns empty", 0, []Entry{}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			if got := Top(counts, tt.n); !reflect.DeepEqual(got, tt.want) {
				t.Errorf("Top(n=%d) = %v, want %v", tt.n, got, tt.want)
			}
		})
	}
}
