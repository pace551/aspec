import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // STK-NEXT-09: self-contained server output for container deploys.
  // Serve with: node .next/standalone/server.js (after copying .next/static in);
  // "next start" refuses standalone builds. Remove only if deploying to Vercel.
  output: "standalone",
};

export default nextConfig;
