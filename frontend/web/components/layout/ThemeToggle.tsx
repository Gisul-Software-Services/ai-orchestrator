"use client";

import { MoonStar } from "lucide-react";

// Admin console is dark-mode only.
// This component renders a static dark mode badge instead of a toggle.
export function ThemeToggle() {
  return (
    <div
      className="flex h-8 items-center gap-1.5 rounded-lg border border-zinc-800/60 bg-zinc-900/60 px-2.5 text-xs text-zinc-500"
      title="Dark mode (admin console)"
    >
      <MoonStar className="h-3.5 w-3.5" />
      <span className="hidden sm:inline">Dark</span>
    </div>
  );
}
