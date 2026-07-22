package {{package}}

import "testing"

// Replace with real table-driven tests (STK-GO-03); Constitution C3 requires
// test-first core logic.
func TestVersion(t *testing.T) {
	t.Parallel()
	if Version == "" {
		t.Fatal("Version must be non-empty")
	}
}
