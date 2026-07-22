import { defineConfig } from "@playwright/test";

// STK-NEXT-08: the T3+ smoke gate. Builds and serves the real app, then drives it.
// With output:"standalone" (STK-NEXT-09) the app is served the way a container would:
// node .next/standalone/server.js, with static assets copied in ("next start" refuses
// standalone builds).
export default defineConfig({
  testDir: "tests/e2e",
  use: { baseURL: "http://localhost:3000" },
  webServer: {
    command:
      "npm run build && rm -rf .next/standalone/.next/static && cp -r .next/static .next/standalone/.next/static && node .next/standalone/server.js",
    url: "http://localhost:3000",
    reuseExistingServer: false,
    timeout: 240_000,
  },
});
