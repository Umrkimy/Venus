import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { parseEnv } from "node:util";
import type { NextConfig } from "next";

const coreUrl = process.env.CORE_URL ?? "http://127.0.0.1:8000";

// Your own domain (README "Your own domain") is set in the repository
// root .env. Only VENUS_DOMAIN is read, not the other values there.
function ownDomain(): string[] {
  const file = join(process.cwd(), "..", "..", ".env");
  if (!existsSync(file)) return [];
  const domain = parseEnv(readFileSync(file, "utf8")).VENUS_DOMAIN;
  return domain ? [domain] : [];
}

const nextConfig: NextConfig = {
  // The Docker image (server mode) runs a small standalone server. Local
  // `next build` + `next start` stay as they are.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  // Dev mode only: let the phone open it through Tailscale
  // (scripts/phone-access.ps1) or your own domain (scripts/domain-access.ps1).
  allowedDevOrigins: ["*.ts.net", ...ownDomain()],
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
