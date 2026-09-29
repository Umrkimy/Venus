import type { NextConfig } from "next";

const coreUrl = process.env.CORE_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${coreUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;