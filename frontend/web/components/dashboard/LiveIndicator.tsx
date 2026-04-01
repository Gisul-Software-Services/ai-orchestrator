"use client";

import { cn } from "@/lib/utils";

export function LiveIndicator({
  ok,
  label,
}: {
  ok: boolean;
  label?: string;
}) {
  return (
    <div className="flex items-center gap-2 text-xs text-zinc-400">
      <span
        className={cn(
          "relative inline-flex h-2.5 w-2.5 rounded-full",
          ok ? "bg-emerald-400" : "bg-zinc-500"
        )}
      >
        {ok ? (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/60" />
        ) : null}
      </span>
      <span>{label ?? (ok ? "Live" : "Stale")}</span>
    </div>
  );
}

