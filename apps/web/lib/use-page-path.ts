"use client";

import { usePathname } from "next/navigation";

// The page's path without a trailing slash: the demo's plain files load as
// "/settings/voice/", the app as "/settings/voice". Compare paths with this.
export function pagePath(pathname: string): string {
  return pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
}

export function usePagePath(): string {
  return pagePath(usePathname());
}
