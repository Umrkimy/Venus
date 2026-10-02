"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState, type ReactNode } from "react";

import { TooltipProvider } from "@/components/ui/tooltip";

export default function Providers({ children }: { children: ReactNode }) {
  // useState keeps one client for the life of the page, not one per render.
  const [queryClient] = useState(() => new QueryClient());
  return (
    // Light, dark or follow Windows; saved in this browser and set as a
    // class on <html> before the page draws, so it never flashes.
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryClientProvider client={queryClient}>
        {/* The sidebar shows tooltips when it is folded to icons. */}
        <TooltipProvider>{children}</TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
