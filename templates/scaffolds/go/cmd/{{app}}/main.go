// {{app}} — thin main over run() so the binary is testable (STK-GO-08).
package main

import (
	"context"
	"fmt"
	"io"
	"os"

	"{{MODULE_PATH}}/internal/{{package}}"
)

func main() {
	if err := run(context.Background(), os.Args[1:], os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "{{app}}:", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, args []string, out io.Writer) error {
	_ = ctx // pass ctx into anything blocking (STK-GO-05)
	_ = args
	_, err := fmt.Fprintln(out, {{package}}.Version)
	return err
}
