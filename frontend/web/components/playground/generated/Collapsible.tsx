"use client";

import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export function Collapsible({
  title,
  icon,
  defaultOpen = false,
  className,
  contentClassName,
  children,
}: {
  title: string;
  icon?: ReactNode;
  defaultOpen?: boolean;
  className?: string;
  /** Extra classes for the inner content wrapper */
  contentClassName?: string;
  children: ReactNode;
}) {
  return (
    <details
      className={cn(
        "group overflow-hidden rounded-xl border border-zinc-800/90 bg-zinc-950/50 shadow-sm [&_summary::-webkit-details-marker]:hidden",
        className
      )}
      open={defaultOpen}
    >
      <summary
        className={cn(
          "flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 text-sm font-medium text-zinc-200",
          "transition-colors hover:bg-zinc-900/70"
        )}
      >
        <ChevronDown
          className="h-4 w-4 shrink-0 text-zinc-500 transition-transform duration-200 group-open:rotate-180"
          strokeWidth={2}
        />
        {icon != null && (
          <span className="flex shrink-0 text-console-accent [&_svg]:h-4 [&_svg]:w-4">
            {icon}
          </span>
        )}
        <span className="min-w-0 flex-1">{title}</span>
      </summary>
      <div
        className={cn(
          "border-t border-zinc-800/80 bg-zinc-950/30 px-3 py-3 sm:px-4 sm:py-4",
          contentClassName
        )}
      >
        {children}
      </div>
    </details>
  );
}
