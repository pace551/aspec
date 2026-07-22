// Package freq counts word frequencies. cmd/wordfreq stays thin over it (STK-GO-08).
package freq

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"sort"
	"strings"
	"unicode"
)

// ErrEmptyInput is the sentinel callers branch on with errors.Is (STK-GO-04).
var ErrEmptyInput = errors.New("no words in input")

// Entry is one word with its total count.
type Entry struct {
	Word  string
	Count int
}

// Words splits a line into lowercase words; anything that isn't a letter or digit
// separates words.
func Words(line string) []string {
	return strings.FieldsFunc(strings.ToLower(line), func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	})
}

// Count tallies normalized words from r. ctx is first because reading r can block
// (STK-GO-05); cancellation is honored between lines.
func Count(ctx context.Context, r io.Reader) (map[string]int, error) {
	counts := make(map[string]int)
	scanner := bufio.NewScanner(r)
	for scanner.Scan() {
		if err := ctx.Err(); err != nil {
			return nil, fmt.Errorf("counting words: %w", err)
		}
		for _, w := range Words(scanner.Text()) {
			counts[w]++
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("scanning input: %w", err)
	}
	if len(counts) == 0 {
		return nil, fmt.Errorf("counting words: %w", ErrEmptyInput)
	}
	return counts, nil
}

// Top returns the n highest-count entries, ordered by count desc then word asc.
func Top(counts map[string]int, n int) []Entry {
	entries := make([]Entry, 0, len(counts))
	for w, c := range counts {
		entries = append(entries, Entry{Word: w, Count: c})
	}
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].Count != entries[j].Count {
			return entries[i].Count > entries[j].Count
		}
		return entries[i].Word < entries[j].Word
	})
	if n < len(entries) {
		entries = entries[:n]
	}
	return entries
}
