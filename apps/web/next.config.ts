import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { parseEnv } from "node:util";
import type { NextConfig } from "next";

const coreUrl = process.env.CORE_URL ?? "http://127.0.0.1:8000";
// The portfolio demo (npm run build:demo) is plain files: no server, so no
// /api forwarding, redirects or headers (the host sets those).
const demo = process.env.NEXT_PUBLIC_VENUS_DEMO === "1";

// Your own domain (README "Your own domain") is set in the repository
// root .env. Only VENUS_DOMAIN is read, not the other values there.
function ownDomain(): string[] {
  const file = join(process.cwd(), "..", "..", ".env");
  if (!existsSync(file)) return [];
  const domain = parseEnv(readFileSync(file, "utf8")).VENUS_DOMAIN;
  return domain ? [domain] : [];
}

// Headers, redirects and /api forwarding need the Next server.
const serverOnly: Partial<NextConfig> = {
  // Same headers on every page and /api answer. The CSP only blocks framing,
  // plugins and odd form or base targets, so Next's own scripts still run.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: "frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'",
          },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" },
          // The mic is for talking to Venus; nothing else needs the camera or location.
          { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self)" },
          // Browsers ignore this over plain http (localhost), so only HTTPS visits
          // (phone over Tailscale, your own domain) are told to stay on HTTPS.
          { key: "Strict-Transport-Security", value: "max-age=31536000" },
        ],
      },
    ];
  },
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

const nextConfig: NextConfig = {
  // The Docker image (server mode) runs a small standalone server. Local
  // `next build` + `next start` stay as they are.
  output: demo ? "export" : process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  // Demo pages as <page>/index.html, which every static host serves as is.
  trailingSlash: demo,
  // Dev mode only: let the phone open it through Tailscale
  // (scripts/phone-access.ps1) or your own domain (scripts/domain-access.ps1).
  allowedDevOrigins: ["*.ts.net", ...ownDomain()],
  experimental: {
    // /api passes requests on to Core but cuts bodies at 10 MB by default.
    // 3D models (Settings upload) are bigger; Core itself refuses over 100 MB.
    proxyClientMaxBodySize: "110mb",
  },
  // Only when a server runs (not the demo's plain files).
  ...(demo ? {} : serverOnly),
};

export default nextConfig;
