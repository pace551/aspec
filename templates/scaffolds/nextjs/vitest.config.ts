import { defineConfig } from "vitest/config";

export default defineConfig({
  // tsconfig has "jsx": "preserve" for Next; without this, vitest 4 cannot parse
  // untested .tsx files and silently drops them from coverage.
  oxc: { jsx: { runtime: "automatic" } },
  test: {
    include: ["tests/unit/**/*.test.ts"],
    passWithNoTests: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary"],
      include: ["app/**", "lib/**"],
    },
  },
});
