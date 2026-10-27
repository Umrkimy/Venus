import type { MetadataRoute } from "next";

// Plain file in the portfolio demo too.
export const dynamic = "force-static";

// Lets the browser install Venus as its own app window (Install app / Add to Home Screen).
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Venus",
    short_name: "Venus",
    description: "Your personal assistant",
    start_url: "/",
    display: "standalone",
    background_color: "#09090b",
    theme_color: "#09090b",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
