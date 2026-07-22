import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // STK-NEXT-09: self-contained server output for container deploys.
  output: "standalone",
};

export default nextConfig;
