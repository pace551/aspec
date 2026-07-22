// STK-TS-04: json-summary emits coverage/coverage-summary.json for the ratchet.
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/**/*.test.ts"],
    coverage: {
      provider: "v8",
      include: ["src/**"],
      reporter: ["text", "json-summary"],
    },
  },
});
