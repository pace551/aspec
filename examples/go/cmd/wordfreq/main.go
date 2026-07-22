// wordfreq prints the most frequent words in a file (or stdin).
// Thin main over run() so the binary is testable (STK-GO-08).
package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"os"

	"example.com/wordfreq/internal/freq"
)

func main() {
	if err := run(context.Background(), os.Args[1:], os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "wordfreq:", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, args []string, stdin io.Reader, out io.Writer) error {
	fs := flag.NewFlagSet("wordfreq", flag.ContinueOnError)
	fs.SetOutput(out)
	topN := fs.Int("top", 10, "number of words to print")
	if err := fs.Parse(args); err != nil {
		return fmt.Errorf("parsing flags: %w", err)
	}

	input := stdin
	if fs.NArg() > 0 {
		path := fs.Arg(0)
		f, err := os.Open(path) // #nosec G304 -- reading the user-named file is the program's purpose
		if err != nil {
			return fmt.Errorf("opening input: %w", err)
		}
		defer f.Close() //nolint:errcheck // read-only file; close error is uninteresting
		input = f
	}

	counts, err := freq.Count(ctx, input)
	if err != nil {
		return err
	}
	for _, e := range freq.Top(counts, *topN) {
		if _, err := fmt.Fprintf(out, "%s %d\n", e.Word, e.Count); err != nil {
			return fmt.Errorf("writing output: %w", err)
		}
	}
	return nil
}
