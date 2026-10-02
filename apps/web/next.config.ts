import type { NextConfig } from "next";

const coreUrl = process.env.CORE_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // /settings has no page of its own; open the first page in its menu.
  async redirects() {
    return [
      {
        source: "/settings",
        destination: "/settings/general",
        permanent: false,
      },
    ];
  },
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